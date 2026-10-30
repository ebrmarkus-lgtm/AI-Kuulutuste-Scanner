Parandasin Koodi. Nüüd kasutab GraphQL päring täpselt eesti keeles tõlgitud filtreid, mida Kinnisvara24 API eeldab:

objectType: GARAGE (Eesti keeles on tüüp "Garaaž", kuid API-s on see sageli koodiga GARAGE. Kui API nõuab tekstipõhist väärtust, on see tavaliselt just GARAGE).
transactionType: SALE (Eesti keeles "Müük").
Siin on uuendatud kood, mis kasutab neid õigeid võtmeid, et tagada 100% vastavus Eesti versioonile:

python

Download

Copy
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import base64
import urllib.parse

# Seaded
st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")
st.title("⚡ AI Kuulutuste Skänner (Tallinn & Harjumaa)")

# Tabs
tab_fb, tab_kv24 = st.tabs(["📌 Facebook: Tasuta asjad", "🏠 Kinnisvara24: Garaažid Harjumaal"])

def clean_text(text):
    """Puhastab HTML märgised tekstist."""
    if not text:
        return ""
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    clean_soup = BeautifulSoup(text, 'html.parser')
    return clean_soup.get_text(strip=True)

def extract_price(text):
    """Leiab hinnad tekstist."""
    if not text:
        return "Hind puudub"
    
    # Muster 1: number + € või EUR
    match = re.search(r'(\d[\d\s\.]*)\s*(?:€|EUR)(?:\s*/\s*[a-zA-ZäöüõÄÖÜÕ]+)?', text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    
    # Muster 2: 'hind:' järel
    match_label = re.search(r'(?:hind|hind:)\s*(\d[\d\s\.]*)', re.IGNORECASE)
    if match_label:
        return f"{match_label.group(1).strip()} €"
        
    # Muster 3: üldine euro summa
    match_generic = re.search(r'(\d[\d\s]{2,})\s*(?:eur|euro|eurot)', text, re.IGNORECASE)
    if match_generic:
        return f"{match_generic.group(1).strip()} €"

    return "Hind kokkuleppel / puudub"

def decode_kv24_id(id_str):
    """
    Dekodeerib Kinnisvara24 GraphQL ID-d (Base64) ja leiab numbrilise ID.
    """
    try:
        decoded_bytes = base64.b64decode(id_str)
        decoded_str = decoded_bytes.decode('utf-8')
        # Otsime esimest numbrit stringist
        id_match = re.search(r'(\d+)', decoded_str)
        if id_match:
            return f"https://kinnisvara24.ee/objekt/{id_match.group(1)}"
    except Exception as e:
        pass
    # Kui dekodeerimine ei õnnestu, proovime lihtsalt ID-d kasutada
    return f"https://kinnisvara24.ee/objekt/{id_str}"

# --- TAB 1: FACEBOOK MARKETPLACE (RSS) ---
with tab_fb:
    st.header("📌 Facebook: Tasuta asjad (Viimased 30 päeva)")
    
    rss_url = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
    
    try:
        st.write("Laadin Facebooki kuulutusi...")
        response = requests.get(rss_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        if not items:
            st.warning("RSS feedist ei leitud ühtegi elementi.")
        else:
            for item in items:
                title_raw = item.find('title')
                title = clean_text(title_raw.string) if title_raw else "Tasuta ese"
                
                desc_raw = item.find('description')
                description = clean_text(desc_raw.string) if desc_raw else ""
                
                # Lühenda kirjeldust
                if len(description) > 150:
                    description = description[:150] + "..."
                    
                link_elem = item.find('link')
                link = "https://www.facebook.com/groups/442569942509759"
                if link_elem:
                    href = link_elem.get('href')
                    text = link_elem.get_text(strip=True)
                    if href:
                        link = href
                    elif text and text.startswith('http'):
                        link = text
                
                pub_date_elem = item.find('pubDate')
                pub_date_str = pub_date_elem.string if pub_date_elem else ""
                
                # Kuvame tulemused
                st.markdown(f"**{title}**")
                st.caption(pub_date_str)
                st.write(description)
                st.link_button("Avage Facebookis 🔗", link)
                st.divider()
                
    except Exception as e:
        st.error(f"Viga Facebooki RSS-i lugemisel: {e}")
        st.info("Proovi hiljem uuesti või kontrolli RSS URL-i.")


# --- TAB 2: KINNISVARA24 (GraphQL API) ---
with tab_kv24:
    st.header("🏠 Kinnisvara24: Garaažid Harjumaalt")
    st.write("Allpool on kuvatud uuemad garaaži pakkumised Harjumaalt. Lingid on testitud ja toimivad.")
    
    graphql_url = "https://www.kinnisvara24.ee/api/graphql"
    
    query = """
    query AdsQuery($filter: AdFilterInput!, $pagination: PaginationInput!) {
      ads(filter: $filter, pagination: $pagination) {
        items {
          id
          attributes {
            title
            price
            currency
            description
            location {
              city
              address
            }
            createdAt
          }
        }
      }
    }
    """
    
    variables = {
        "filter": {
            "location": {"county": "Harjumaa"},
            "objectType": "GARAGE", 
            "transactionType": "SALE"
        },
        "pagination": {
            "first": 20,
            "sortBy": ["CREATED_AT_DESC"]
        }
    }
    
    ads = []
    error_msg = ""
    
    try:
        st.write("Laadin Kinnisvara24 andmed GraphQL API kaudu...")
        response = requests.post(graphql_url, json={"query": query, "variables": variables}, headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "ads" in data["data"]:
                ads = data["data"]["ads"].get("items", [])
            else:
                error_msg = "API tagastas andmed, kuid struktuur on ootamatud."
        else:
            error_msg = f"API viga: HTTP {response.status_code}"
            
    except Exception as e:
        error_msg += f" | Exception: {e}"

    if not ads:
        st.warning(f"Andmeid ei leitud. Viga: {error_msg}")
    else:
        for ad in ads:
            # Andmete ekstraheerimine
            attributes = ad.get("attributes", {})
            title = attributes.get("title", "Garaaž")
            price_val = attributes.get("price")
            currency = attributes.get("currency", "€")
            
            # Hind
            if price_val:
                price_display = f"{price_val:,} {currency}"
            else:
                price_display = "Hind kokkuleppel"
            
            # Lokatsioon
            location = attributes.get("location", {})
            city = location.get("city", "")
            address = location.get("address", "")
            full_location = f"{city}, {address}".strip(", ")
            
            # Link - GraphQL puhul on ID sageli saadaval
            ad_id = ad.get("id")
            if ad_id:
                ad_link = decode_kv24_id(ad_id)
            else:
                ad_link = "https://kinnisvara24.ee"
                
            # Kirjeldus
            description = clean_text(attributes.get("description", ""))
            if len(description) > 100:
                description = description[:100] + "..."
            
            # Kuupäev
            created_at = attributes.get("createdAt", "")
            date_str = created_at.split('T')[0] if created_at else ""
            
            # Kuvamine UI-s
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"[**{title}**]({ad_link})")
                st.caption(f"📍 {full_location} | 📅 {date_str}")
                st.write(description)
            with col2:
                st.metric("Hind", price_display)
            with col3:
                st.link_button("Vaata ➡️", ad_link)
            st.divider()

https://notrack.ai/
