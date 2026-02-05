import cloudscraper
from bs4 import BeautifulSoup
import sqlite3
import time
import schedule
import os
import re  # Added Regex for finding prices/numbers
import config
from dotenv import load_dotenv

# --- CONFIGURATION ---
DEBUG_MODE = True  # Set to False to send Telegram messages

# --- SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DB_FILE = os.path.join(BASE_DIR, config.DB_FILE)

if not DEBUG_MODE and (not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID):
    print("❌ ERROR: Secrets missing in .env")
    exit(1)


# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS properties
                 (
                     id
                     TEXT
                     PRIMARY
                     KEY
                 )''')
    conn.commit()
    conn.close()


def is_seen(fingerprint):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM properties WHERE id=?", (fingerprint,))
    exists = c.fetchone() is not None
    conn.close()
    return exists


def save_property(fingerprint):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO properties (id) VALUES (?)", (fingerprint,))
    conn.commit()
    conn.close()


# --- HELPERS ---
def create_fingerprint(address_text):
    clean = address_text.lower()
    for word in ["belfast", "bt7", "street", "st", "road", "rd", "ave", "avenue", ",", ".", "property"]:
        clean = clean.replace(word, "")
    clean = "".join(c for c in clean if c.isalnum())
    return clean[:15]


def fix_link(base_url, href):
    if href.startswith("http"): return href
    parts = base_url.split("/")
    domain = f"{parts[0]}//{parts[2]}"
    if not href.startswith("/"): href = "/" + href
    return domain + href


def extract_price(text):
    """Finds price like £1,200 or 1200 in text"""
    # Look for £ followed by numbers, allowing for commas
    match = re.search(r'£([\d,]+)', text)
    if match:
        return int(match.group(1).replace(',', ''))
    return 0


def extract_beds(text):
    """Finds bedroom count. Handles '4 bed' AND 'Double Room' (counts as 1)"""
    text_lower = text.lower()

    # 1. Explicit number found (e.g., "4 bed", "5 bedrooms")
    match = re.search(r'(\d+)\s*bed', text_lower)
    if match:
        return int(match.group(1))

    # 2. Implicit single room (e.g., "Double Room", "Room 1") -> Count as 1
    # This ensures your MIN_BEDS filter (e.g. 3) will correctly REJECT these.
    if "double room" in text_lower or "single room" in text_lower or "room for rent" in text_lower:
        return 1

    return 0


def is_valid_house(text, href):
    """The Master Filter: Checks Junk, Location, Price, Beds"""
    text_lower = text.lower()
    href_lower = href.lower()

    # 1. REMOVE JUNK & BAD LINKS
    # Added: 'mailto', 'info@', 'privacy', 'cookie' to stop the email link false positive
    junk_words = ['instagram', 'login', 'register', 'landlord', 'valuation',
                  'latest news', 'student rental', 'view details', 'info@',
                  'privacy policy', 'cookie', 'marketing preferences']

    if any(w in text_lower for w in junk_words): return False

    # Check for non-property links (mailto:, tel:, javascript:)
    if href_lower.startswith(("mailto:", "tel:", "javascript:")): return False

    # 2. EXCLUDE "AGREED" / "RESERVED"
    if "let agreed" in text_lower or "agreed" in text_lower or "reserved" in text_lower:
        return False

    # 3. CHECK LOCATION (Must be BT7/Student Zone)
    # Exceptions: We ban "Ballygawley", "Antrim", etc.
    if any(w in text_lower for w in ['ballygawley', 'antrim', 'dungannon', 'bt15', 'bt11']): return False

    valid_locs = ['bt7', 'university', 'holyland', 'stranmillis', 'botanic',
                  'ormeau', 'fitzroy', 'rugby', 'palestine', 'damascus', 'carmel', 'cairo']
    if not any(w in text_lower for w in valid_locs): return False

    # 4. CHECK BEDROOMS (From Config)
    # Now that extract_beds returns '1' for single rooms, this will filter them out.
    beds_found = extract_beds(text)
    if beds_found > 0 and beds_found < config.MIN_BEDS:
        return False  # Too small

    # 5. CHECK PRICE (From Config)
    price_found = extract_price(text)

    # Filter out £0 listings if you want (often means error or POA)
    # if price_found == 0: return False

    if price_found > config.MAX_PRICE:
        return False  # Too expensive

    return True

# --- ALERT HANDLER ---
def handle_new_property(agent, text, link):
    if DEBUG_MODE:
        print("-" * 50)
        print(f"[NEW] Agent: {agent}")
        print(f"🏠 {text}")
        print(f"🔗 {link}")
        print("-" * 50)
    else:
        msg = (
            f"<b>🆕 DIRECT AGENT LISTING</b>\n"
            f"🏢 <b>{agent}</b>\n\n"
            f"🏠 {text}\n\n"
            f"🔗 <a href='{link}'>View on Agent Site</a>"
        )
        import requests
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})
            print(f"   -> Sent Telegram: {text[:30]}...")

            # --- ADDED DELAY HERE ---
            # Sleep for 3 seconds to be nice to the API
            time.sleep(3)

        except Exception as e:
            print(f"   -> Telegram Fail: {e}")

# --- SCRAPER 1: PROPBOX SITES ---
# --- SCRAPER 1: PROPBOX SITES (Now with Pagination) ---
def scrape_propbox_site(name, base_url, scraper):
    print(f"  --> Scanning {name}...")

    # We will check the first 3 pages to ensure we don't miss listings
    # pushed down by "Featured" items.
    MAX_PAGES = 3

    for page in range(1, MAX_PAGES + 1):
        try:
            # --- URL CONSTRUCTION ---
            if page == 1:
                url = base_url
            else:
                # If URL has '?', we append with '&page=x', else '?page=x'
                separator = "&" if "?" in base_url else "?"
                url = f"{base_url}{separator}page={page}"

            # --- FETCHING ---
            resp = scraper.get(url, timeout=20)

            # If the page doesn't exist (404) or redirects to home, stop looping
            if resp.status_code != 200:
                if DEBUG_MODE: print(f"    [Page {page}] Status {resp.status_code} - Stopping.")
                break

            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.find_all(class_='PropBox-content')

            # If no items found on this page, we've reached the end
            if not items:
                if DEBUG_MODE: print(f"    [Page {page}] No items found - Stopping.")
                break

            if DEBUG_MODE: print(f"    [Page {page}] Found {len(items)} items...")

            # --- PROCESSING ITEMS ---
            for item in items:
                link_tag = item.find('a')
                if not link_tag: continue

                text = " ".join(item.get_text().split())
                href = link_tag['href']

                if len(text) < 10: continue

                if is_valid_house(text, href):
                    full_link = fix_link(base_url, href)
                    fingerprint = create_fingerprint(text)

                    if not is_seen(fingerprint):
                        handle_new_property(name, text, full_link)
                        save_property(fingerprint)

            # Small politeness delay between pages
            time.sleep(1)

        except Exception as e:
            print(f"    ❌ Error on page {page}: {e}")
            break


# --- SCRAPER 2: CUSTOM SITES (Now with Pagination) ---
def scrape_custom_site(name, base_url, scraper):
    print(f"  --> Scanning {name}...")

    # Check first 3 pages
    MAX_PAGES = 3

    for page in range(1, MAX_PAGES + 1):
        try:
            # --- URL CONSTRUCTION ---
            if page == 1:
                url = base_url
            else:
                # Add pagination param
                separator = "&" if "?" in base_url else "?"
                url = f"{base_url}{separator}page={page}"

            # --- FETCHING ---
            resp = scraper.get(url, timeout=20)
            if resp.status_code != 200:
                if DEBUG_MODE: print(f"    [Page {page}] Status {resp.status_code} - Stopping.")
                break

            soup = BeautifulSoup(resp.text, 'html.parser')

            # --- EXTRACTION ---
            # 1. Find explicit property cards
            special_cards = soup.find_all(class_=['addr', 'eqh', 'property_row', 'prop-list-item', 'featured-property'])

            # 2. Find ALL links (Backup method)
            links = soup.find_all('a', href=True)

            candidates = []

            # Prioritize cards
            for card in special_cards:
                link = card.find('a') if card.name != 'a' else card
                if link and link.has_attr('href'): candidates.append(link)

            # Add general links
            for link in links: candidates.append(link)

            # If no candidates found, likely end of pagination
            if not candidates:
                if DEBUG_MODE: print(f"    [Page {page}] No links found - Stopping.")
                break

            if DEBUG_MODE: print(f"    [Page {page}] Scanning {len(candidates)} links...")

            seen_hrefs = set()

            for link in candidates:
                href = link['href']
                if href in seen_hrefs: continue

                # Clean text
                text = " ".join(link.get_text().split())
                if len(text) < 10: continue

                # Basic URL filters
                is_standard_url = any(
                    w in href for w in ['/property/', '/details/', '/to-rent/', '/id/', 'gpm', 'properties'])
                clean_href = href.rstrip('/')
                is_id_url = clean_href and clean_href[-1].isdigit()

                if (is_standard_url or is_id_url):
                    if is_valid_house(text, href):
                        seen_hrefs.add(href)
                        full_link = fix_link(base_url, href)
                        fingerprint = create_fingerprint(text)

                        if not is_seen(fingerprint):
                            handle_new_property(name, text, full_link)
                            save_property(fingerprint)

            time.sleep(1)  # Be polite

        except Exception as e:
            print(f"    ❌ Error on page {page}: {e}")
            break

# --- MAIN CONTROLLER ---
def job():
    print(f"\nStarting Cycle (Debug={DEBUG_MODE})...")
    scraper = cloudscraper.create_scraper()

    # 1. PropBox
    for name, url in config.PROPBOX_AGENTS.items():
        scrape_propbox_site(name, url, scraper)
        time.sleep(1)

    # 2. Custom Sites
    for name, url in config.CUSTOM_AGENTS.items():
        scrape_custom_site(name, url, scraper)
        time.sleep(1)

    print("Cycle Complete.")


if __name__ == "__main__":
    init_db()
    print("🚀 Direct Agent Bot Started")
    job()
    schedule.every(config.CHECK_INTERVAL_MINUTES).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)