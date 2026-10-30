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
        soup = BeautifulSoup(xml_data, 'html.parser')
        
        # RSS.app kasutab tavaliselt <item> või <entry> elemente
        items = soup.find_all(['item', 'entry'])
        
        for item in items[:15]:
            # Otsime pealkirja või kirjelduse sisu
            title_elem = item.find('title')
            desc_elem = item.find('description') or item.find('summary')
            link_elem = item.find('link')
            
            # Kui pealkiri puudub, võtame esimese rea kirjeldusest
            if title_elem and title_elem.text.strip():
                title = title_elem.get_text(strip=True)
            elif desc_elem and desc_elem.text.strip():
                title = desc_elem.get_text(strip=True)[:80] + "..."
            else:
                title = "Tasuta ese FB grupis"
                
            # Lingi leidmine (RSS.app-is võib link olla ka attribuudina või eraldi elemendina)
            link = "https://www.facebook.com/groups/442569942509759"
            if link_elem:
                if link_elem.get('href'):
                    link = link_elem.get('href')
                elif link_elem.text.strip():
                    link = link_elem.get_text(strip=True)
            
            results.append({
                "title": title,
                "price": "Tasuta",
                "location": "Haapsalu / Tallinn",
                "link": link
            })
    except Exception as e:
        print(f"Viga RSS skännimisel: {e}")

    if not results:
        results = [
            {
                "title": "Ootame uusi postitusi grupis.",
                "price": "0 €",
                "location": "Tallinn",
                "link": "https://www.facebook.com/groups/442569942509759"
            }
        ]

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scrape_fb_group_rss()
