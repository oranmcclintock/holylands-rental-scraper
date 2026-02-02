import requests
from bs4 import BeautifulSoup
from collections import Counter

URL = "https://www.propertypal.com/property-to-rent/belfast"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def analyze_page():
    print(f"Fetching {URL}...")
    response = requests.get(URL, headers=HEADERS)

    if response.status_code != 200:
        print("Failed to load page.")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all 'li' and 'div' tags with classes
    classes = []
    for tag in soup.find_all(['li', 'div']):
        if tag.get('class'):
            classes.extend(tag.get('class'))

    # Count the most common classes
    print("\n--- Most Common Classes Found ---")
    print("(The 'house' class usually appears 20-30 times)")
    for cls, count in Counter(classes).most_common(20):
        print(f"Class: '{cls}'  |  Count: {count}")


if __name__ == "__main__":
    analyze_page()