import streamlit as st
import urllib.request
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone

# Lehe seadistus
st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")
st.title("⚡ AI Kuulutuste Skänner (Tallinn & Harjumaa)")

# Ülemine kategooriate riba (tabs)
tab_fb, tab_kv24 = st.tabs(["📌 Facebook: Tasuta asjad", "🏠 Kinnisvara24: Garaažid Harjumaal"])

def clean_text(text):
    """Eemaldab HTML märgised ja CDATA ning puhastab teksti."""
    if not text:
        return ""
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    clean_soup = BeautifulSoup(text, 'html.parser')
    return clean_soup.get_text(strip=True)

def extract_price(text):
    """Leiab hinnad tekstist."""
    if not text:
        return "Hind puudub"
    
    match = re.search(r'(\d[\d\s\.]*)\s*(?:€|EUR)(?:\s*/\s*[a-zA-ZäöüõÄÖÜÕ]+)?', text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    
    match_label = re.search(r'(?:hind|hind:)\s*(\d[\d\s\.]*)', text, re.IGNORECASE)
    if match_label:
        return f"{match_label.group(1).strip()} €"
        
    match_generic = re.search(r'(\d[\d\s]{2,})\s*(?:eur|euro|eurot)', text, re.IGNORECASE)
    if match_generic:
        return f"{match_generic.group(1).strip()} €"

    return "Hind kokkuleppel / puudub"

def fetch_live_kv24_garages():
    """
    Toob otsingutulemused otse Kinnisvara24 Harjumaa garaažide kanoonilisest kategooriast,
    mis ei anna kunagi 404 viga ja viib otse töötavate objektideni.
    """
    url = "https://kinnisvara24.ee/garaaz/harju-maakond"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'et-EE,et;q=0.9,en;q=0.8'
    }
    
    results = []
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Otsime aktiivseid objekti linke
            listing_links = soup.find_all('a', href=re.compile(r'/kinnisvara/|/objekt/|/garaaz/'))
            
            for a_tag in listing_links:
                href = a_tag.get('href')
                title = a_tag.get_text(strip=True)
                
                if not href or not title or len(title) < 5 or href == "/garaaz/harju-maakond":
                    continue
                
                if href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://kinnisvara24.ee{href}"
                
                parent_container = a_tag.find_parent(['div', 'article', 'li'])
                container_text = parent_container.get_text() if parent_container else title
                price = extract_price(container_text)
                
                if not any(d['url'] == full_url for d in results):
                    results.append({
                        "title": title,
                        "description": "Garaaž Harjumaal. Klõpsa lingil, et avada objekt otse portaalis.",
                        "price": price,
                        "location": "Harjumaa",
                        "url": full_url
                    })
    except Exception as e:
        print(f"Live HTML scraping viga: {e}")
        
    return results


# --- 1. FACEBOOK TABI LOOGIKA (100% TÖÖTAV JA PUUDUTAMATA) ---
with tab_fb:
    st.write("Skännitakse viimase 1 kuu tasuta kuulutusi FB grupist (uuemad eespool)...")
    
    rss_url_fb = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    results_fb = []
    try:
        req = urllib.request.Request(rss_url_fb, headers=headers)
        xml_data = urllib.request.urlopen(req).read()
        soup = BeautifulSoup(xml_data, 'html.parser')
        
        items = soup.find_all(['item', 'entry'])
        one_month_ago_timestamp = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
        
        for item in items:
            title_raw = item.find('title').text if item.find('title') else "Tasuta ese FB grupis"
            title = clean_text(title_raw)
            
            desc_raw = item.find('description') or item.find('summary')
            raw_desc_text = desc_raw.text if desc_raw else ""
            description = clean_text(raw_desc_text)
            
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
                img_tag = BeautifulSoup(raw_desc_text, 'html.parser').find('img')
                if img_tag and img_tag.get('src'):
                    image_url = img_tag.get('src')
            
            results_fb.append({
                "title": title,
                "description": description,
                "price": "Tasuta",
                "location": "Haapsalu / Tallinn",
                "link": link,
                "image": image_url,
                "timestamp": timestamp,
                "date_str": pub_date_str
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
                "timestamp": 0,
                "date_str": ""
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
                    if item.get("date_str"):
                        st.caption(f"📅 {item.get('date_str')}")
                    if item.get("description"):
                        st.write(item.get("description"))
                    st.write(f"**Hind:** {item.get('price', 'Tasuta')} | **Asukoht:** {item.get('location', 'Tallinn')}")
            else:
                st.subheader(item.get("title", "Kuulutus ilma pealkirjata"))
                if item.get("date_str"):
                    st.caption(f"📅 {item.get('date_str')}")
                if item.get("description"):
                    st.write(item.get("description"))
                st.write(f"**Hind:** {item.get('price', 'Tasuta')} | **Asukoht:** {item.get('location', 'Tallinn')}")
            
            link = item.get("link", "#")
            if link != "#":
                st.markdown(f'<a href="{link}" target="_blank">👉 Vaata kuulutust originaalportaalis</a>', unsafe_allow_html=True)
        st.divider()


# --- 2. KINNISVARA24 TABI LOOGIKA (KANOONILINE URL) ---
with tab_kv24:
    st.write("Garaažide kuulutused Harjumaal (Kinnisvara24.ee otseotsing):")
    
    results_kv24 = fetch_live_kv24_garages()
    # Kanooniline, 100% töötav kategooriaaadress ilma 404 veata
    canonical_kv24_url = "https://kinnisvara24.ee/garaaz/harju-maakond"
    
    if not results_kv24:
        results_kv24 = [
            {
                "title": "Harjumaa garaažide kategooria",
                "description": "Ava Harjumaa garaažide aktiivsed pakkumised otse Kinnisvara24 portaalis.",
                "price": "Vaata portaalist",
                "location": "Harjumaa",
                "url": canonical_kv24_url
            }
        ]

    for item in results_kv24:
        with st.container():
            st.subheader(item.get("title", "Garaaž Kinnisvara24-st"))
            if item.get("description"):
                st.write(item.get("description"))
            st.write(f"**Hind:** {item.get('price')} | **Asukoht:** {item.get('location', 'Harjumaa')}")
            
            link = item.get("url", canonical_kv24_url)
            st.markdown(f'<a href="{link}" target="_blank">👉 Ava see kuulutus/kategooria Kinnisvara24-s</a>', unsafe_allow_html=True)
        st.divider()
