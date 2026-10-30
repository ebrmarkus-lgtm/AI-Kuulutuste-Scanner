import streamlit as st
import urllib.request
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from datetime import datetime, timedelta, timezone

# Set page config
st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")

# Title
st.title("⚡ AI Kuulutuste Skänner (Tallinn & Harjumaa)")

# Tabs
tab_fb, tab_kv24 = st.tabs(["📌 Facebook: Tasuta asjad", "🏠 Kinnisvara24: Garaažid Harjumaal"])

def clean_text(text):
    """Eemaldab HTML märgised ja puhastab teksti."""
    if not text:
        return ""
    # Eemalda CDATA
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    clean_soup = BeautifulSoup(text, 'html.parser')
    return clean_soup.get_text(strip=True)

def extract_price(text):
    """Leiab hinnad tekstist."""
    if not text:
        return "Hind puudub"
    
    # Proovi leida hind kujul XXX € või XXX EUR
    match = re.search(r'(\d[\d\s\.]*)\s*(?:€|EUR)(?:\s*/\s*[a-zA-ZäöüõÄÖÜÕ]+)?', text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    
    # Proovi leida hind pärast sõna 'hind:'
    match_label = re.search(r'(?:hind|hind:)\s*(\d[\d\s\.]*)', text, re.IGNORECASE)
    if match_label:
        return f"{match_label.group(1).strip()} €"
        
    # Üldine muster
    match_generic = re.search(r'(\d[\d\s]{2,})\s*(?:eur|euro|eurot)', text, re.IGNORECASE)
    if match_generic:
        return f"{match_generic.group(1).strip()} €"

    return "Hind kokkuleppel / puudub"

def get_kv24_search_link(title):
    """Loob pealkirja põhjal töötava Kinnisvara24 otsingu lingi."""
    base_url = "https://kinnisvara24.ee/kinnisvara-otsing?deal_type=1&property_type=4&search_type=area&county=Harju+maakond"
    if title and title != "Garaaž Kinnisvara24-st":
        query = title.split(',')[0].strip()
        encoded_query = urllib.parse.quote(query)
        return f"https://kinnisvara24.ee/kinnisvara-otsing?deal_type=1&property_type=4&search_type=area&county=Harju+maakond&keyword={encoded_query}"
    return base_url

def fetch_kv24_garages():
    """Võtab garaaži kuulutused Kinnisvara24-st, kasutades robustsemat meetodit."""
    url = "https://kinnisvara24.ee/kinnisvara-otsing?deal_type=1&property_type=4&search_type=area&county=Harju+maakond"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Kui 404, proovime teist URL-i / API-t
        if response.status_code == 404:
            api_url = "https://kinnisvara24.ee/api/v1/search?deal_type=1&property_type=4&county=Harju+maakond"
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get('items', []):
                    title = item.get('title', 'Pealkiri puudub')
                    href = item.get('url', '')
                    price = item.get('price', 'Hind puudub')
                    
                    if href and not href.startswith('http'):
                        full_url = f"https://kinnisvara24.ee{href}"
                    else:
                        full_url = href
                    
                    results.append({
                        'title': title,
                        'url': full_url,
                        'price': price
                    })
                return results
            else:
                return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        listings = soup.find_all('a', href=re.compile(r'/kinnisvara/'))
        
        for item in listings:
            title_tag = item.find_parent(['div', 'li']) or item.parent
            if not title_tag:
                continue
                
            title = item.get_text(strip=True)
            href = item.get('href')
            
            if href and not href.startswith('http'):
                full_url = f"https://kinnisvara24.ee{href}"
            else:
                full_url = href
            
            price_text = title_tag.get_text()
            price = extract_price(price_text)
            
            results.append({
                'title': title,
                'url': full_url,
                'price': price
            })
            
        return results
    except Exception as e:
        st.error(f"Viga andmete laadimisel: {e}")
        return []


# --- 1. FACEBOOK TABI LOOGIKA ---
with tab_fb:
    st.write("Skännitakse viimase 1 kuu tasuta kuulutusi FB grupist (uuemad eespool)...")
    
    rss_url_fb = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
    fb_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    results_fb = []
    try:
        req = urllib.request.Request(rss_url_fb, headers=fb_headers)
        xml_data = urllib.request.urlopen(req).read()
        soup = BeautifulSoup(xml_data, 'html.parser')
        
        items = soup.find_all(['item', 'entry'])
        one_month_ago_timestamp = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
        
        for item in items:
            title_raw = item.find('title').text if item.find('title') else "Tasuta ese FB grupis"
            title = clean_text(title_raw)
            
            desc_raw = item.find('description') or item.find('summary')
            description = clean_text(desc_raw.text) if desc_raw else ""
            
            if len(description) > 200:
                description = description[:200] + "..."
                
            link_elem = item.find('link')
            link = "https://www.facebook.com/groups/442569942509759"
            if link_elem:
                if link_elem.get('href'):
                    link = link_elem.get('href')
                elif link_elem.text.strip():
                    link = link_elem.get_text(strip=True)
            
            pub_date_elem = item.find('pubDate') or item.find('updated')
            pub_date_str = pub_date_elem.text if pub_date_elem else ""
            
            timestamp = 0
            if pub_date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    parsed_date = parsedate_to_datetime(pub_date_str)
                    timestamp = parsed_date.timestamp()
                except:
                    try:
                        timestamp = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00')).timestamp()
                    except:
                        timestamp = 0

            if timestamp > 0 and timestamp < one_month_ago_timestamp:
                continue

            image_url = None
            enclosure = item.find('enclosure')
            if enclosure and enclosure.get('url'):
                image_url = enclosure.get('url')
            elif desc_raw:
                img_tag = BeautifulSoup(desc_raw.text, 'html.parser').find('img')
                if img_tag and img_tag.get('src'):
                    image_url = img_tag.get('src')
            
            results_fb.append({
                "title": title,
                "description": description,
                "price": "Tasuta",
                "location": "Haapsalu / Tallinn",
                "link": link,
                "image": image_url,
                "timestamp": timestamp
            })
            
        results_fb = sorted(results_fb, key=lambda x: x["timestamp"], reverse=True)

    except Exception as e:
        print(f"Viga Facebooki RSS skännimisel: {e}")

    if not results_fb:
        results_fb = [
            {
                "title": "Ootame uusi postitusi grupis.",
                "description": "Siia ilmuvad uued tasuta asjad.",
                "price": "0 €",
                "location": "Tallinn",
                "link": "https://www.facebook.com/groups/442569942509759",
                "image": None,
                "timestamp": 0
            }
        ]

    for item in results_fb:
        with st.container():
            if item.get("image"):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(item["image"], use_container_width=True)
                with col2:
                    st.subheader(item.get("title", "Kuulutus ilma pealkirjata"))
                    if item.get("description"):
                        st.write(item.get("description"))
                    st.write(f"**Hind:** {item.get('price', 'Tasuta')} | **Asukoht:** {item.get('location', 'Tallinn')}")
            else:
                st.subheader(item.get("title", "Kuulutus ilma pealkirjata"))
                if item.get("description"):
                    st.write(item.get("description"))
                st.write(f"**Hind:** {item.get('price', 'Tasuta')} | **Asukoht:** {item.get('location', 'Tallinn')}")
            
            link = item.get("link", "#")
            if link != "#":
                st.markdown(f'<a href="{link}" target="_blank">👉 Vaata kuulutust originaalportaalis</a>', unsafe_allow_html=True)
        st.divider()


# --- 2. KINNISVARA24 TABI LOOGIKA ---
with tab_kv24:
    st.header("Garaažid Harjumaalt")
    
    if st.button("Laadi uued kuulutused"):
        with st.spinner('Otsin Kinnisvara24-st...'):
            kv24_data = fetch_kv24_garages()
            
        if not kv24_data:
            st.warning("Andmeid ei leitud või ilmnes ühenduse viga.")
        else:
            st.success(f"Leiti {len(kv24_data)} garaaži kuulutust!")
            
            for item in kv24_data:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**[{item['title']}]({item['url']})**")
                
                with col2:
                    st.metric("Hind", item['price'])
                    
                with col3:
                    st.markdown(f"[Ava link →]({item['url']})")
                    
                st.divider()
    else:
        st.info("Vajuta nuppu 'Laadi uued kuulutused', et skaneerida.")
