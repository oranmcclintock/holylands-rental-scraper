# Holylands Rental Scraper

This project is a Python-based web scraper designed to monitor various letting agent websites for rental properties in specific areas (e.g., Belfast's Holylands/BT7 area). It identifies new listings, filters them based on user-defined criteria (price, number of bedrooms, location keywords), and sends real-time alerts to a Telegram chat.

The scraper is built to handle common anti-bot measures using `cloudscraper` and uses `BeautifulSoup` for parsing HTML. Property data is stored in a SQLite database to prevent duplicate alerts.

<img width="1278" height="903" alt="image" src="https://github.com/user-attachments/assets/d1b6516e-188e-4e22-a1d6-dcd325e959b4" />

## Features

-   **Automated Scraping:** Periodically scans multiple letting agent websites for new property listings.
-   **Configurable Filters:** Define minimum bedrooms, maximum price, and location keywords to narrow down relevant properties.
-   **Duplicate Prevention:** Uses a SQLite database to track already seen properties, ensuring only new listings trigger alerts.
-   **Telegram Notifications:** Sends detailed alerts for new properties directly to a specified Telegram chat, including property text and a direct link.
-   **Cloudflare Bypassing:** Integrates `cloudscraper` to navigate websites protected by Cloudflare's anti-bot measures.
-   **Site Analysis Tool:** Includes a utility script (`inspect_new_site.py`) to assist in onboarding new agent websites by analyzing their structure.
-   **Telegram Connection Tester:** A utility (`testBot.py`) to verify the Telegram bot's connectivity.

## Setup

### Prerequisites

-   Python 3.x
-   `pip` (Python package installer)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/holylands-rental-scraper.git
    cd holylands-rental-scraper
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file is assumed. If it doesn't exist, you'll need to create one with `cloudscraper`, `beautifulsoup4`, `python-dotenv`, `schedule`, `requests` listed.)*

3.  **Create a `.env` file:**
    Create a file named `.env` in the root directory of the project. This file will store your sensitive Telegram API keys.
    ```
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
    ```
    -   **`TELEGRAM_BOT_TOKEN`**: Obtain this by creating a new bot with BotFather on Telegram.
    -   **`TELEGRAM_CHAT_ID`**: Get this by sending a message to your new bot and then visiting `https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/getUpdates`. Look for the `id` field under `chat`.

### Configuration (`config.py`)

Open `config.py` to customize the scraping parameters:

-   `MIN_BEDS`: Minimum number of bedrooms required for a property.
-   `MAX_PRICE`: Maximum monthly rental price.
-   `LOCATION_CODE`: A geographical code or keyword relevant to your desired location (e.g., "bt7").
-   `DB_FILE`: The name of the SQLite database file to store seen properties.
-   `CHECK_INTERVAL_MINUTES`: How often the scraper should run (in minutes).
-   `PROPBOX_AGENTS`: A dictionary of agent names and URLs for sites that use a common "PropBox" HTML structure.
-   `CUSTOM_AGENTS`: A dictionary of agent names and URLs for sites that might require more specific scraping logic.

## Usage

### Running the Scraper

To start the scraper, run `main.py`:

```bash
python main.py
```

The script will initialize the database (if it doesn't exist), perform an initial scan, and then run periodically based on the `CHECK_INTERVAL_MINUTES` defined in `config.py`. New properties matching your criteria will be sent as Telegram messages.

### Debug Mode

To run the scraper without sending Telegram messages (e.g., for testing new configurations), set `DEBUG_MODE = True` at the top of `main.py`. This will print new properties to the console instead.

## Utilities

### Inspecting New Sites (`inspect_new_site.py`)

If you want to add a new letting agent website to the scraper, you can use `inspect_new_site.py` to help understand its structure. Modify the `all_agents` dictionary in `inspect_new_site.py` or directly call `analyze_site` with the new URL.

```bash
python inspect_new_site.py
```

This script will print common CSS classes and sample links, which can help you determine if the site fits the "PropBox" structure or requires custom scraping logic.

### Testing Telegram Connection (`testBot.py`)

To ensure your Telegram bot token and chat ID are correctly configured and working, run `testBot.py`:

```bash
python testBot.py
```

This will attempt to send a test message to your Telegram chat.

## Technologies Used

-   Python 3
-   `cloudscraper`: To bypass Cloudflare and other anti-bot measures.
-   `BeautifulSoup4`: For parsing HTML and extracting data.
-   `sqlite3`: For the local property database.
-   `python-dotenv`: To manage environment variables securely.
-   `schedule`: For scheduling periodic tasks.
-   `requests`: For making HTTP requests (especially for Telegram API).

---
