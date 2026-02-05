import os
import requests
from dotenv import load_dotenv

# 1. Load keys from your .env file
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("-" * 40)
print("📡 TELEGRAM CONNECTION TEST")
print("-" * 40)
print(f"🔑 Bot Token:   {TOKEN[:10]}...[HIDDEN]")
print(f"📢 Target Chat: {CHAT_ID}")

if not TOKEN or not CHAT_ID:
    print("\n❌ ERROR: Your .env file is missing variables.")
    exit(1)

# 2. Prepare the message
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "🚨 <b>TEST MESSAGE</b>\n\nIf you see this, the bot is working perfectly!",
    "parse_mode": "HTML"
}

# 3. Send it
try:
    print("\n🚀 Sending message...")
    response = requests.post(url, json=payload)
    
    # 4. Analyze result
    if response.status_code == 200:
        print("✅ SUCCESS: Message delivered.")
    else:
        print(f"❌ FAILED: Code {response.status_code}")
        print(f"⚠️ Telegram Error: {response.text}")

except Exception as e:
    print(f"❌ NETWORK ERROR: {e}")
