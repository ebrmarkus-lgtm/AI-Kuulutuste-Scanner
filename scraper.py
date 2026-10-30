import json
import urllib.request
from bs4 import BeautifulSoup

def scrape_fb_group_rss():
    rss_url = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    results = []
    try:
        req = urllib.request.Request(rss_url, headers=headers)
        xml_data = urllib.request.urlopen(req).read()
        # Kasutame html.parser'it, et ei oleks vaja lxml teeki
        soup = BeautifulSoup(xml_data, 'html.parser')
        
        items = soup.find_all('item')
        
        for item in items[:15]:
            title = item.find('title').get_text(strip=True) if item.find('title') else "Tasuta ese FB grupis"
            link = item.find('link').get_text(strip=True) if item.find('link') else "https://facebook.com"
            
            results.append({
                "title": title,
                "price": "Tasuta",
                "location": "Tallinn (FB Grupp)",
                "link": link
            })
    except Exception as e:
        print(f"Viga RSS skännimisel: {e}")

    # Tagavara, kui andmeid ei leita
    if not results:
        results = [
            {
                "title": "FB skänner seadistatud! Ootame uusi postitusi grupis.",
                "price": "0 €",
                "location": "Tallinn",
                "link": "https://www.facebook.com/groups/442569942509759"
            }
        ]

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scrape_fb_group_rss()
