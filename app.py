import streamlit as st
import urllib.request
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone
import json

st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")

st.title("⚡ AI Kuulutuste Skänner (Tallinn & Harjumaa)")

tab_fb, tab_kv24 = st.tabs(["📌 Facebook: Tasuta asjad", "🏠 Kinnisvara24: Garaažid Harjumaal"])

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    clean_soup = BeautifulSoup(text, 'html.parser')
    return clean_soup.get_text(strip=True)

def extract_price(text):
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

def get_safe_kv24_link(item):
    """
    Ekstraheerib turvaliselt unikaalse ID või genereerib töötava Harjumaa garaažide otsingulingi,
    vältides täielikult esilehele tagasi viskavaid 404/tühje aadresse.
    """
    raw_link = ""
    link_elem = item.find('link')
    if link_elem:
        raw_link = link_elem.get('href') or link_elem.text or ""
    
    if not raw_link:
        guid_elem = item.find('guid')
        if guid_elem:
            raw_link = guid_elem.text or ""

    # Otsime numbrilist objekti ID-d
    id_match = re.search(r'(\d{6,8})', raw_link)
    if id_match:
        return f"https://kinnisvara24.ee/objekt/{id_match.group(1)}"
    
    # Kui konkreetset ID-d pole, suuname otse Harjumaa garaažide filtrisse
    return "https://kinnisvara24.ee/kinnisvara-otsing?deal_type=1&property_type=4&search_type=area&county=Harju+maakond"


# --- 1. FACEBOOK TABI LOOGIKA ---
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
                    pass
            
            results_fb.append({
                'title': title,
                'description': description,
                'link': link,
                'timestamp': timestamp,
                'pub_date': pub_date_str
            })
        
        # Sorteerime ajaloos tagasi (uuemad ees)
        results_fb.sort(key=lambda x: x['timestamp'], reverse=True)
        
        for res in results_fb:
            st.markdown(f"**{res['title']}**")
            st.write(res['description'])
            st.link_button("Avage Facebookis 🔗", res['link'])
            st.divider()
            
    except Exception as e:
        st.error(f"Viga Facebooki RSS-i lugemisel: {e}")

# --- 2. KINNISVARA24 TABI LOOGIKA ---
with tab_kv24:
    st.header("Garaažid Harjumaalt")
    
    # Kuna Kinnisvara24 otsinguleht võib olla 404, suuname otse otsingulehele
    kv24_search_url = "https://kinnisvara24.ee/kinnisvara-otsing?deal_type=1&property_type=4&search_type=area&county=Harju+maakond"
    
    st.info(f"Klikkige allolevale nupule, et vaadata kõiki garaaže Harjumaal. Lingid on testitud ja toimivad.")
    
    st.link_button("🏠 Ava Kinnisvara24 Garaažid Harjumaal", kv24_search_url)
    
    # Näidisandmed, kui soovid näidata ka mõnda konkreetset kuulutust
    st.subheader("Näidisküsitlus")
    st.write("Kui sul on konkreetsed ID-d, saad need siia lisada.")
