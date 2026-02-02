import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import schedule
import os
from dotenv import load_dotenv

load_dotenv()
# Get secrets from the hidden file
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- CONFIGURATION ---
URL_TO_SCRAPE = "https://www.propertypal.com/property-to-rent/bt7/bedrooms-4-4/price-1800"
DB_FILE = "seen_properties.db"

# Headers to make the bot look like a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# --- DATABASE FUNCTIONS ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS properties (id TEXT PRIMARY KEY)''')
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

# --- TELEGRAM FUNCTION ---
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("  -> Telegram message sent!")
        else:
            print(f"  -> Telegram Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  -> Failed to send Telegram message: {e}")

# --- TEXT CLEANER ---
def clean_property_text(text):
    """Removes junk words that get scraped from buttons."""
    junk_words = ["Hide", "Save", "Email", "Call", "Contact"]

    # 1. Replace junk words with nothing
    for word in junk_words:
        text = text.replace(word, "")

    # 2. Remove extra spaces created by the removal
    return " ".join(text.split())

# --- SCRAPING LOGIC ---
def check_for_rentals():
    print(f"Checking {URL_TO_SCRAPE}...")
    try:
        response = requests.get(URL_TO_SCRAPE, headers=HEADERS)
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all(class_='pp-property-box')

        new_count = 0

        for listing in listings:
            try:
                # 1. Extract Link and ID
                link_tag = listing.find('a')
                if not link_tag: continue

                relative_link = link_tag['href']
                full_link = "https://www.propertypal.com" + relative_link
                property_id = relative_link.split('/')[-1]

                # 2. Extract & Clean Info
                # separator=' ' prevents "month29" mashups
                raw_text = link_tag.get_text(separator=' ', strip=True)
                clean_info = clean_property_text(raw_text)

                # 3. Check Database
                if not is_seen(property_id):
                    print(f"Found new property: {property_id}")

                    # New Clean Message Format
                    msg = (
                        f"<b>NEW RENTAL FOUND</b>\n\n"
                        f"{clean_info}\n\n"
                        f"<b>Link:</b> {full_link}"
                    )

                    send_telegram_alert(msg)
                    save_property(property_id)
                    new_count += 1

                    time.sleep(1)

            except Exception as e:
                print(f"Error parsing item: {e}")
                continue

        print(f"Check complete. Found {new_count} new properties.")

    except Exception as e:
        print(f"Scraping error: {e}")

# --- MAIN EXaECUTION ---
if __name__ == "__main__":
    init_db()
    print("Bot started...")

    # Run once immediately
    check_for_rentals()

    # Schedule to run every 30 minutes
    schedule.every(30).minutes.do(check_for_rentals)

    while True:
        schedule.run_pending()
        time.sleep(1)