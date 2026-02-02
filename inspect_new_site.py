import cloudscraper
from bs4 import BeautifulSoup
from collections import Counter

# We check both sites to see if they share the same structure
URLS = [
    "https://www.propertypal.com/property-to-rent/bt7/bedrooms-4-4",
    "https://www.university-area-properties.com/search?bedroom_min=4&bedroom_max=4&listing_type=let&view=list",
    "https://www.propertynews.com/property-to-rent/bt7/bedrooms-4-4/price-1800"
]


def analyze_site(url):
    print(f"\n--- Analysing: {url} ---")
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            print(f"❌ Failed to load (Status: {response.status_code})")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        # Count classes on <li> and <div> tags
        classes = []
        for tag in soup.find_all(['li', 'div', 'article']):
            if tag.get('class'):
                classes.extend(tag.get('class'))

        print("Most common classes (Look for 'prop', 'item', 'card'):")
        for cls, count in Counter(classes).most_common(15):
            print(f"  {cls}: {count}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    for url in URLS:
        analyze_site(url)