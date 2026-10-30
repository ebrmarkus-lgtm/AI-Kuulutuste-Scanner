import streamlit as st
import json
import os
import urllib.request
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")

st.title("⚡ AI Kuulutuste Skänner (Tallinn & Harjumaa)")

# Ülemine kategooriate riba (tabs)
tab_fb, tab_kv24 = st.tabs(["📌 Facebook: Tasuta asjad", "🏠 Kinnisvara24: Eraldi kinnistul garaažid"])

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    clean_soup = BeautifulSoup(text, 'html.parser')
    return clean_soup.get_text(strip=True)

def extract_price(text):
    if not text:
        return "Hind ebaselge"
    # Otsime mustrit nagu "15000 €", "15 000€" vms
    match = re.search(r'(\d[\d\s]*)\s*(?:€|EUR)', text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return "Vaata hinda portaalist"

# --- 1. FACEBOOK TABI LOOGIKA ---
with tab_fb:
    st.write("Skännitakse viimase 1 kuu tasuta kuulutusi FB grupist (uuemad eespool)...")
    
    rss_url_fb = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
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
                st.markdown(f"[👉 Vaata kuulutust originaalportaalis]({link})")
        st.divider()


# --- 2. KINNISVARA24 TABI LOOGIKA ---
with tab_kv24:
    st.write("Garaažid eraldi kinnistutel Harjumaal (Kinnisvara24.ee, uuemad eespool):")
    
    rss_url_kv24 = "https://rss.app/feeds/aWV2VpetQuPw0DhO.xml"
    
    results_kv24 = []
    try:
        req = urllib.request.Request(rss_url_kv24, headers=headers)
        xml_data = urllib.request.urlopen(req).read()
        soup = BeautifulSoup(xml_data, 'html.parser')
        
        items = soup.find_all(['item', 'entry'])
        one_month_ago_timestamp = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
        
        for item in items:
            title_raw = item.find('title').text if item.find('title') else "Garaaž Kinnisvara24-st"
            title = clean_text(title_raw)
            
            desc_raw = item.find('description') or item.find('summary')
            description = clean_text(desc_raw.text) if desc_raw else ""
            
            # --- FILTREERIMINE: Ainult garaažid eraldi kinnistutel ---
            full_text = (title + " " + description).lower()
            is_garage = "garaaž" in full_text or "garaaz" in full_text
            is_separate_property = any(word in full_text for word in ["eraldi", "omaette", "kinnistul", "kinnistu"])
            
            if not (is_garage and is_separate_property):
                continue  # Jäta vahele, kui ei vasta tingimusele
            
            price = extract_price(title + " " + description)
            
            if len(description) > 200:
                description = description[:200] + "..."
                
            link_elem = item.find('link')
            link = "https://kinnisvara24.ee"
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
            
            results_kv24.append({
                "title": title,
                "description": description,
                "price": price,
                "location": "Harjumaa",
                "link": link,
                "image": image_url,
                "timestamp": timestamp
            })
            
        results_kv24 = sorted(results_kv24, key=lambda x: x["timestamp"], reverse=True)

    except Exception as e:
        print(f"Viga Kinnisvara24 RSS skännimisel: {e}")

    if not results_kv24:
        results_kv24 = [
            {
                "title": "Sobivaid kuulutusi ei leitud.",
                "description": "Hetkel ei ole RSS-voos ühtegi garaaži, mis mainiks eraldi kinnistut.",
                "price": "-",
                "location": "Harjumaa",
                "link": "https://kinnisvara24.ee",
                "image": None,
                "timestamp": 0
            }
        ]

    for item in results_kv24:
        with st.container():
            if item.get("image"):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(item["image"], use_container_width=True)
                with col2:
                    st.subheader(item.get("title", "Kuulutus ilma pealkirjata"))
                    if item.get("description"):
                        st.write(item.get("description"))
                    st.write(f"**Hind:** {item.get('price')} | **Asukoht:** {item.get('location', 'Harjumaa')}")
            else:
                st.subheader(item.get("title", "Kuulutus ilma pealkirjata"))
                if item.get("description"):
                    st.write(item.get("description"))
                st.write(f"**Hind:** {item.get('price')} | **Asukoht:** {item.get('location', 'Harjumaa')}")
            
            link = item.get("link", "#")
            if link != "#":
                st.markdown(f"[👉 Vaata kuulutust Kinnisvara24 portaalis]({link})")
        st.divider()
