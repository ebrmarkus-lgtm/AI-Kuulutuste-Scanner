import requests
from bs4 import BeautifulSoup
import json
import time

URL = "https://soov.ee/574-ara-anda/listings.html"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def main():
    print("🔎 Skännin SOOV.ee tasuta kuulutusi...")
    res = requests.get(URL, headers=HEADERS)
    if res.status_code != 200:
        print("Ei saanud lehele ligi")
        return

    soup = BeautifulSoup(res.text, 'html.parser')
    items = soup.find_all('li', class_='item')
    
    results = []

    for item in items:
        try:
            title_tag = item.find('h2', class_='item-title').find('a')
            title = title_tag.text.strip()
            link = title_tag['href']

            location_tag = item.find('span', class_='item-location')
            location = location_tag.text.strip() if location_tag else "Tallinn"

            if "Tallinn" not in location:
                continue

            img_tag = item.find('img')
            img_url = img_tag['src'] if img_tag else ""

            views_tag = item.find('span', class_='item-views')
            views = views_tag.text.strip() if views_tag else "0"

            results.append({
                "title": title,
                "location": location,
                "views": views,
                "link": link,
                "image": img_url,
                "time": time.strftime("%H:%M")
            })
        except Exception:
            continue

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Salvestatud {len(results)} kuulutust!")

if __name__ == "__main__":
    main()
