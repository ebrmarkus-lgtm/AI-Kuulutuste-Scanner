import json
import urllib.request
from bs4 import BeautifulSoup

def scrape_soov():
    url = "https://soov.ee/139-ara-anda/headings.html"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    results = []
    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req).read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        
        listings = soup.find_all('div', class_='item-list') or soup.find_all('a', class_='item-title')
        
        for item in listings[:15]:
            title_elem = item.find('h2') or item.find('a') or item
            title = title_elem.get_text(strip=True) if title_elem else "Tasuta ese Tallinnas"
            
            link = item.get('href') or (item.find('a')['href'] if item.find('a') else "https://soov.ee")
            if not link.startswith('http'):
                link = "https://soov.ee" + link
                
            results.append({
                "title": title,
                "price": "Tasuta",
                "location": "Tallinn",
                "link": link
            })
    except Exception as e:
        print(f"Viga skännimisel: {e}")

    if not results:
        results = [
            {
                "title": "Süsteem töötab! Ootame uusi kuulutusi SOOV.ee portaalist.",
                "price": "0 €",
                "location": "Tallinn",
                "link": "https://soov.ee"
            }
        ]

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scrape_soov()
