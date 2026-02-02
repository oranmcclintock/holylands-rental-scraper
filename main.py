import cloudscraper
from bs4 import BeautifulSoup
import sqlite3
import time
import schedule
import os
import re
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

# --- URLs (Updated with your BT7 Filters) ---
URL_PROPERTYPAL = "https://www.propertypal.com/property-to-rent/bt7/bedrooms-4-4/price-1800"
URL_UNI_AREA = "https://www.university-area-properties.com/grid/property-for-rent/bt7/bedrooms-4-4/price-1800"
URL_PROPERTYNEWS = "https://www.propertynews.com/property-to-rent/bt7/bedrooms-4-4/price-1800"


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


# --- HELPER FUNCTIONS ---
def create_fingerprint(address_text):
    """
    Creates a unique ID from the address to stop duplicates.
    Example: "29 Carmel Street, Belfast" -> "29carmel"
    """
    clean = address_text.lower()
    for word in ["belfast", "bt7", "street", "st", "road", "rd", "avenue", "ave", ",", "."]:
        clean = clean.replace(word, "")
    clean = "".join(c for c in clean if c.isalnum())
    return clean[:15]


def clean_text(text):
    junk = ["Hide", "Save", "Email", "Call", "Contact", "More Details", "Property", "Added"]
    for word in junk:
        text = text.replace(word, "")
    return " ".join(text.split())


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


def format_message(source_name, info_text, link):
    return (
        f"<b>NEW RENTAL FOUND</b>\n"
        f"Source: {source_name}\n\n"
        f"{info_text}\n\n"
        f"<a href='{link}'>View Listing</a>"
    )


# --- SCRAPER 1: PROPERTYPAL ---
def scrape_propertypal(scraper):
    print(f"  --> Scanning PropertyPal...")
    try:
        response = scraper.get(URL_PROPERTYPAL)
        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all(class_='pp-property-box')
        count = 0
        for listing in listings:
            try:
                link_tag = listing.find('a')
                if not link_tag: continue

                full_link = "https://www.propertypal.com" + link_tag['href']
                info = clean_text(link_tag.get_text(separator=' ', strip=True))

                fingerprint = create_fingerprint(info)

                if not is_seen(fingerprint):
                    print(f"    Found New (PP): {fingerprint}")
                    msg = format_message("PropertyPal", info, full_link)
                    send_telegram_alert(msg)
                    save_property(fingerprint)
                    count += 1
                    time.sleep(2)
            except:
                continue
        return count
    except Exception as e:
        print(f"  PropertyPal Error: {e}")
        return 0


# --- SCRAPER 2: UNIVERSITY AREA ---
def scrape_uni_area(scraper):
    print(f"  --> Scanning Uni Area...")
    try:
        response = scraper.get(URL_UNI_AREA)
        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all(class_='list-item')
        count = 0
        for listing in listings:
            try:
                link_tag = listing.find('a')
                if not link_tag: continue

                rel_link = link_tag['href']
                full_link = rel_link if "http" in rel_link else "https://www.university-area-properties.com" + rel_link
                info = clean_text(listing.get_text(separator=' ', strip=True))

                fingerprint = create_fingerprint(info)

                if not is_seen(fingerprint):
                    print(f"    Found New (UAP): {fingerprint}")
                    msg = format_message("Uni Area Properties", info, full_link)
                    send_telegram_alert(msg)
                    save_property(fingerprint)
                    count += 1
                    time.sleep(2)
            except:
                continue
        return count
    except Exception as e:
        print(f"  Uni Area Error: {e}")
        return 0


# --- SCRAPER 3: PROPERTYNEWS (FIXED) ---
def scrape_propertynews(scraper):
    print(f"  --> Scanning PropertyNews...")
    try:
        response = scraper.get(URL_PROPERTYNEWS)
        soup = BeautifulSoup(response.text, 'html.parser')

        # New Logic: Find ALL links
        links = soup.find_all('a', href=True)

        count = 0
        for link in links:
            try:
                href = link['href']
                # Clean up the link
                href = href.strip()

                # Logic: Is the last part of the URL a number? (e.g. /1056665)
                # Split by '/' and take the last part that isn't empty
                parts = [p for p in href.split('/') if p]
                if not parts: continue

                last_part = parts[-1]

                # CHECK: Is it a number? (The ID) AND NOT a search price (e.g. price-1800)
                if last_part.isdigit() and len(last_part) > 5:

                    full_link = href if "http" in href else "https://www.propertynews.com" + href
                    info = clean_text(link.get_text(separator=' ', strip=True))

                    # Safety: Ensure the link text isn't empty
                    if len(info) < 10: continue

                    fingerprint = create_fingerprint(info)

                    if not is_seen(fingerprint):
                        print(f"    Found New (PN): {fingerprint}")
                        msg = format_message("PropertyNews", info, full_link)
                        send_telegram_alert(msg)
                        save_property(fingerprint)
                        count += 1
                        time.sleep(2)
            except:
                continue
        return count
    except Exception as e:
        print(f"  PropertyNews Error: {e}")
        return 0


# --- MAIN CONTROLLER ---
def job():
    print("\nStarting scan cycle...")
    scraper = cloudscraper.create_scraper()

    pp = scrape_propertypal(scraper)
    uap = scrape_uni_area(scraper)
    pn = scrape_propertynews(scraper)

    print(f"Cycle complete. New: {pp} (PP) | {uap} (UAP) | {pn} (PN)")


if __name__ == "__main__":
    init_db()
    print("Bot started (Triple Scraper Mode)...")
    print(f"Looking for .env in: {BASE_DIR}")

    # Run once on startup
    job()

    # Schedule every 15 mins
    schedule.every(15).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)