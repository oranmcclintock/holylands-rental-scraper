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
DEBUG_MODE = False  # Set to False to send Telegram messages

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
    """Finds bedroom count like '4 bed' or '5 bedrooms'"""
    # Look for a number followed by 'bed'
    match = re.search(r'(\d+)\s*bed', text.lower())
    if match:
        return int(match.group(1))
    return 0


def is_valid_house(text, href):
    """The Master Filter: Checks Junk, Location, Price, Beds"""
    text_lower = text.lower()

    # 1. REMOVE JUNK
    junk_words = ['instagram', 'login', 'register', 'landlord', 'valuation', 'latest news', 'student rental',
                  'view details']
    if any(w in text_lower for w in junk_words): return False
    if "let agreed" in text_lower or "agreed" in text_lower: return False

    # 2. CHECK LOCATION (Must be BT7/Student Zone)
    # Exceptions: We ban "Ballygawley" or "Antrim Road"
    if any(w in text_lower for w in ['ballygawley', 'antrim', 'dungannon', 'bt15', 'bt11']): return False

    valid_locs = ['bt7', 'university', 'holyland', 'stranmillis', 'botanic', 'ormeau', 'fitzroy', 'rugby', 'palestine',
                  'damascus', 'carmel', 'cairo']
    if not any(w in text_lower for w in valid_locs): return False

    # 3. CHECK BEDROOMS (From Config)
    # If text mentions beds, verify count. If no mention, we let it pass (safest).
    beds_found = extract_beds(text)
    if beds_found > 0 and beds_found < config.MIN_BEDS:
        return False  # Too small

    # 4. CHECK PRICE (From Config)
    # If text mentions price, verify it.
    price_found = extract_price(text)
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
        except Exception as e:
            print(f"   -> Telegram Fail: {e}")


# --- SCRAPER 1: PROPBOX SITES ---
def scrape_propbox_site(name, url, scraper):
    print(f"  --> Scanning {name}...")
    try:
        resp = scraper.get(url, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.find_all(class_='PropBox-content')

        for item in items:
            link_tag = item.find('a')
            if not link_tag: continue

            text = " ".join(item.get_text().split())
            href = link_tag['href']

            if len(text) < 10: continue

            if is_valid_house(text, href):
                full_link = fix_link(url, href)
                fingerprint = create_fingerprint(text)

                if not is_seen(fingerprint):
                    handle_new_property(name, text, full_link)
                    save_property(fingerprint)
    except Exception as e:
        print(f"    ❌ Error: {e}")


# --- SCRAPER 2: CUSTOM SITES ---
def scrape_custom_site(name, url, scraper):
    print(f"  --> Scanning {name}...")
    try:
        resp = scraper.get(url, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')

        special_cards = soup.find_all(class_=['addr', 'eqh', 'property_row'])
        links = soup.find_all('a', href=True)

        candidates = []
        for card in special_cards:
            link = card.find('a') if card.name != 'a' else card
            if link and link.has_attr('href'): candidates.append(link)
        for link in links: candidates.append(link)

        seen_hrefs = set()

        for link in candidates:
            href = link['href']
            if href in seen_hrefs: continue

            text = " ".join(link.get_text().split())
            if len(text) < 10: continue

            # Basic URL Check first
            is_standard_url = any(
                w in href for w in ['/property/', '/details/', '/to-rent/', '/id/', 'gpm', 'properties'])
            clean_href = href.rstrip('/')
            is_id_url = clean_href and clean_href[-1].isdigit()

            if (is_standard_url or is_id_url):
                if is_valid_house(text, href):
                    seen_hrefs.add(href)
                    full_link = fix_link(url, href)
                    fingerprint = create_fingerprint(text)

                    if not is_seen(fingerprint):
                        handle_new_property(name, text, full_link)
                        save_property(fingerprint)

    except Exception as e:
        print(f"    ❌ Error: {e}")


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