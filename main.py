import cloudscraper
from bs4 import BeautifulSoup
import sqlite3
import time
import schedule
import os
from dotenv import load_dotenv

# --- CONFIGURATION & SECRETS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(ENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print(f"ERROR: Could not load secrets from {ENV_PATH}")
    exit(1)

DB_FILE = os.path.join(BASE_DIR, 'seen_properties.db')

# URLs
URL_PROPERTYPAL = "https://www.propertypal.com/property-to-rent/bt7/bedrooms-4-4/price-1800"
URL_UNI_AREA = "https://www.university-area-properties.com/grid/property-for-rent/bt7/bedrooms-4-4/price-1800"


# --- DATABASE FUNCTIONS ---
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


def is_seen(property_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM properties WHERE id=?", (property_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists


def save_property(property_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO properties (id) VALUES (?)", (property_id,))
    conn.commit()
    conn.close()


# --- TELEGRAM FUNCTIONS ---
def send_telegram_alert(message):
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Fail: {e}")


# NEW: Plain Text Formatter (No Emojis)
def format_message(source_name, info_text, link):
    return (
        f"<b>NEW RENTAL FOUND</b>\n"
        f"Source: {source_name}\n\n"
        f"{info_text}\n\n"
        f"<a href='{link}'>View Listing</a>"
    )


# --- TEXT CLEANER ---
def clean_text(text):
    junk = ["Hide", "Save", "Email", "Call", "Contact", "More Details"]
    for word in junk:
        text = text.replace(word, "")
    return " ".join(text.split())


# --- SCRAPER 1: PROPERTYPAL ---
def scrape_propertypal(scraper):
    print(f"  --> Scanning PropertyPal...")
    try:
        response = scraper.get(URL_PROPERTYPAL)
        if response.status_code != 200:
            print(f"  Error {response.status_code}")
            return 0

        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all(class_='pp-property-box')

        count = 0
        for listing in listings:
            try:
                link_tag = listing.find('a')
                if not link_tag: continue

                rel_link = link_tag['href']
                full_link = "https://www.propertypal.com" + rel_link
                p_id = rel_link.split('/')[-1]

                info = clean_text(link_tag.get_text(separator=' ', strip=True))

                if not is_seen(p_id):
                    print(f"    Found New (PP): {p_id}")

                    msg = format_message("PropertyPal", info, full_link)

                    send_telegram_alert(msg)
                    save_property(p_id)
                    count += 1
                    time.sleep(2)
            except:
                continue
        return count
    except Exception as e:
        print(f"  PropertyPal Error: {e}")
        return 0


# --- SCRAPER 2: UNIVERSITY AREA PROPERTIES ---
def scrape_uni_area(scraper):
    print(f"  --> Scanning University Area Properties...")
    try:
        response = scraper.get(URL_UNI_AREA)
        if response.status_code != 200:
            print(f"  Error {response.status_code}")
            return 0

        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all(class_='list-item')

        count = 0
        for listing in listings:
            try:
                link_tag = listing.find('a')
                if not link_tag: continue

                rel_link = link_tag['href']
                if "http" in rel_link:
                    full_link = rel_link
                else:
                    full_link = "https://www.university-area-properties.com" + rel_link

                p_id = full_link
                info = clean_text(listing.get_text(separator=' ', strip=True))

                if not is_seen(p_id):
                    print(f"    Found New (UAP): {p_id}")

                    msg = format_message("Uni Area Properties", info, full_link)

                    send_telegram_alert(msg)
                    save_property(p_id)
                    count += 1
                    time.sleep(2)
            except:
                continue
        return count
    except Exception as e:
        print(f"  Uni Area Error: {e}")
        return 0


# --- MAIN CONTROLLER ---
def job():
    print("\nStarting scan cycle...")
    scraper = cloudscraper.create_scraper()

    pp_count = scrape_propertypal(scraper)
    uni_count = scrape_uni_area(scraper)

    print(f"Cycle complete. New: {pp_count} (PP) | {uni_count} (UAP)")


if __name__ == "__main__":
    init_db()
    print("Bot started (Universal Mode)...")
    print(f"Looking for .env in: {BASE_DIR}")

    # Run once immediately
    job()

    # Schedule every 60 mins
    schedule.every(60).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)