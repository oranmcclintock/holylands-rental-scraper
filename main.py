import cloudscraper # NEW LIBRARY
from bs4 import BeautifulSoup
import sqlite3
import time
import schedule
import os

# --- CONFIGURATION ---
# (Your existing token/chat_id are fine, just ensure they are correct here)
TELEGRAM_BOT_TOKEN = "7758788320:AAEwO3bpiwbz40nayJyxt7QAGuwpxVzyuNU"
TELEGRAM_CHAT_ID = "6896869768"
URL_TO_SCRAPE = "https://www.propertypal.com/property-to-rent/bt7/bedrooms-4-4/price-1800"
DB_FILE = "/home/house-scraper/seen_properties.db" # USE FULL PATH FOR SERVER SAFETY

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
    # Note: We use the standard requests library for Telegram API, that's fine.
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

# --- TEXT CLEANER ---
def clean_property_text(text):
    junk_words = ["Hide", "Save", "Email", "Call", "Contact"]
    for word in junk_words:
        text = text.replace(word, "")
    return " ".join(text.split())

# --- SCRAPING LOGIC ---
def check_for_rentals():
    print(f"Checking {URL_TO_SCRAPE}...")
    try:
        # --- NEW: ANTI-BLOCKING REQUEST ---
        scraper = cloudscraper.create_scraper() 
        response = scraper.get(URL_TO_SCRAPE)
        # ----------------------------------
        
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all(class_='pp-property-box')
        
        new_count = 0
        
        for listing in listings:
            try:
                link_tag = listing.find('a')
                if not link_tag: continue

                relative_link = link_tag['href']
                full_link = "https://www.propertypal.com" + relative_link
                property_id = relative_link.split('/')[-1]
                
                raw_text = link_tag.get_text(separator=' ', strip=True)
                clean_info = clean_property_text(raw_text)

                if not is_seen(property_id):
                    print(f"Found new property: {property_id}")
                    msg = (
                        f"<b>NEW RENTAL FOUND</b>\n\n"
                        f"{clean_info}\n\n"
                        f"<b>Link:</b> {full_link}"
                    )
                    send_telegram_alert(msg)
                    save_property(property_id)
                    new_count += 1
                    time.sleep(2) # Slower sleep to be safer

            except Exception as e:
                continue

        print(f"Check complete. Found {new_count} new properties.")

    except Exception as e:
        print(f"Scraping error: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    init_db()
    print("Bot started...")
    
    # Run once immediately
    check_for_rentals()
    
    # Schedule to run every 60 minutes (Safer interval for servers)
    schedule.every(60).minutes.do(check_for_rentals)

    while True:
        schedule.run_pending()
        time.sleep(1)
