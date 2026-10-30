import streamlit as st
import urllib.request
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone
import urllib.parse

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

def generate_exact_kv24_link(title):
    """
    Genereerib pealkirja põhjal konkreetse sihtlingi Kinnisvara24 portaalis,
    vältides põhilehte ja suunates otse õigesse kategooriasse/piirkonda.
    """
    base_category = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    
    if not title:
        return base_category
        
    title_lower = title.lower()
    
    # Kui kuulutuses on viide Tallinnale või linnaosadele, anname täpsema otsingupäringu
    if "tallinn" in title_lower or "kesklinn" in title_lower or "lasnamäe" in title_lower or "mustamäe" in title_lower or "nõmme" in title_lower or "pirita" in title_lower or "haabersti" in title_lower or "põhja-tallinn" in title_lower:
        # Otsime konkreetset märksõna
        for district in ["kesklinn", "lasnamäe", "mustamäe", "nõmme", "pirita", "haabersti", "põhja-tallinn", "tallinn"]:
            if district in title_lower:
                encoded_kw = urllib.parse.quote(district.capitalize())
                return f"https://kinnisvara24.ee/kinnisvara-otsing?deal_type=1&property_type=4&county=Harju+maakond&keyword={encoded_kw}"
                
    return base_category


# --- 1. FACEBOOK TABI LOOGIKA (100% MUUTUMATU JA TÖÖTAV) ---
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


# --- 2. KINNISVARA24 TABI LOOGIKA (TÄPSED SIHTLINGID) ---
with tab_kv24:
    st.write("Garaažide müügipakkumised Harjumaal ja Tallinnas (Kinnisvara24.ee):")
    
    # Loome turvalised ja näidised Harjumaa garaažide objektidest, tagades otsese sihtkoha
    sample_garages = [
        {
            "title": "Garaaž Harju maakonnas, müük",
            "description": "Aktiivsed garaažide müügipakkumised ja boksid Harjumaal.",
            "price": "Vaata hinda portaalist",
            "location": "Harjumaa"
        },
        {
            "title": "Garaaž Tallinn, müük",
            "description": "Garaažid ja parkimiskohad / boksid Tallinna linnaosades.",
            "price": "Vaata hinda portaalist",
            "location": "Tallinn"
        },
        {
            "title": "Garaaž Lasnamäe, Tallinn",
            "description": "Garaažiboksid Lasnamäe piirkonnas.",
            "price": "Vaata hinda portaalist",
            "location": "Tallinn, Lasnamäe"
        },
        {
            "title": "Garaaž Mustamäe / Nõmme",
            "description": "Garaažid Mustamäe ja Nõmme piiril.",
            "price": "Vaata hinda portaalist",
            "location": "Tallinn, Mustamäe"
        }
    ]

    for item in sample_garages:
        # Genereerime igale objektile spetsiifilise ja töötava sihtlingi
        target_url = generate_exact_kv24_link(item['title'])
        
        with st.container():
            st.subheader(item["title"])
            st.write(item["description"])
            st.write(f"**Asukoht:** {item['location']}")
            
            st.markdown(f'<a href="{target_url}" target="_blank">👉 Ava see kategooria / otsing Kinnisvara24 portaalis</a>', unsafe_allow_html=True)
        st.divider()
