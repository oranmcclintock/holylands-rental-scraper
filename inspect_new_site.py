import cloudscraper
from bs4 import BeautifulSoup
from collections import Counter
import config  # Imports your new config file


def analyze_site(name, url):
    print(f"\n🔵 --- Analysing: {name} ---")
    print(f"🔗 URL: {url}")

    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to load (Status: {response.status_code})")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Count Classes to identify the layout
        classes = []
        for tag in soup.find_all(['li', 'div', 'article', 'a']):
            if tag.get('class'):
                classes.extend(tag.get('class'))

        print("📊 Top 5 Classes:")
        for cls, count in Counter(classes).most_common(5):
            print(f"   - {cls}: {count}")

        # 2. Extract Links to check format
        print("🔎 Sample Links:")
        links = soup.find_all('a', href=True)
        found_count = 0
        for link in links:
            href = link['href']
            # Look for common property URL patterns
            if any(x in href for x in ['/property/', '/details/', '/to-rent/', '/id/', 'show']):
                # Clean up relative links
                if not href.startswith("http"):
                    href = "/" + href.lstrip("/")
                print(f"   -> {href[:50]}...")
                found_count += 1
                if found_count >= 3: break

        if found_count == 0:
            print("   ⚠️ No obvious property links found (might need custom logic).")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Combine all groups from config.py for this test
    all_agents = {
        **config.PROPBOX_AGENTS,
        **config.LIST_AGENTS,
        **config.CUSTOM_AGENTS
    }

    print(f"🚀 Inspecting {len(all_agents)} direct agent sites...\n")

    for name, url in all_agents.items():
        analyze_site(name, url)