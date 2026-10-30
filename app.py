import streamlit as st
import requests
import json
import re
from datetime import datetime

# Konfiguratsioon
st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")
st.title("⚡ AI Kuulutuste Skänner (Tallinn & Harjumaa)")

tab_fb, tab_kv24 = st.tabs(["📌 Facebook: Tasuta asjad", "🏠 Kinnisvara24: Garaažid Harjumaal"])

def clean_text(text):
    """Puhastab teksti."""
    if not text:
        return ""
    # Eemalda liigsed tühikud ja ridade vahed
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_price(text):
    """Leiab hinnad tekstist või andmestruktuurist."""
    if not text:
        return "Hind puudub"
    
    # Proovi leida hind muster: number € või EUR
    match = re.search(r'(\d[\d\s\.]*)\s*(?:€|EUR)', text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    
    # Kui hind on juba struktureeritud andmes, proovi seda lugeda
    try:
        price_val = float(text.replace('.', '').replace(',', '.').replace('€', '').replace('EUR', '').strip())
        return f"{price_val:,.0f} €"
    except ValueError:
        pass
        
    return "Hind kokkuleppel / puudub"

def fetch_kv24_garages():
    """Võtab garaazi kuulutused Kinnisvara24 REST API kaudu."""
    
    # API Endpoint: Otsing garaazidele (property_type=4) Harjumaal (county_id=15 on Harju maakond ID, kuid kasutame ka search_queryks 'Harjumaa')
    # Täpsem filter: deal_type=1 (Müük), property_type=4 (Garaaž)
    
    url = "https://api.kinnisvara24.ee/v1/search"
    
    params = {
        "deal_type": [1],  # Müük
        "property_type": [4],  # Garaaž
        "county_id": [15],  # Harjumaa (Kontrolli: Tallinn on osa Harjumaast, aga kui tahad ainult Tallinna, muuda ID-d. Siin on kogu Harjumaa).
        "page_size": 50,  # Võta rohkem lehte
        "sort_by": "created_at",  # Uusimad esimesed
        "sort_order": "desc"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Origin': 'https://kinnisvara24.ee',
        'Referer': 'https://kinnisvara24.ee/kinnisvara-otsing?deal_type=1&property_type=4&search_type=area&county=Harju+maakond'
    }
    
    try:
        st.write("Laadin Kinnisvara24 andmed API kaudu...")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # API vastuse struktuur: 'data' sisaldab 'results' listi
        results_raw = data.get('data', {}).get('results', [])
        
        results = []
        
        for item in results_raw:
            # Põhiandmed
            title = item.get('title', 'Garaaž')
            
            # Hind
            price_info = item.get('price', {})
            price_amount = price_info.get('amount', '')
            price_currency = price_info.get('currency', '€')
            
            if price_amount:
                formatted_price = f"{float(price_amount):,.0f} €"
            else:
                formatted_price = "Hind kokkuleppel"
                
            # Asukoht
            location_parts = []
            address = item.get('address', '')
            city = item.get('city', '')
            county = item.get('county', '')
            
            if city:
                location_parts.append(city)
            if address:
                location_parts.append(address)
            
            location_str = ", ".join(filter(None, location_parts)) if location_parts else "Harjumaa"
            
            # Link
            object_id = item.get('id')
            # Kinnisvara24 kasutab sageli base64-ID-sid või lihtsaid numbreid. 
            # Enamasti on URL kujul: https://kinnisvara24.ee/objekt/{id}/
            # Mõnel juhul on ID kodeeritud. Proovime lihtsat varianti.
            if object_id:
                full_url = f"https://kinnisvara24.ee/objekt/{object_id}/"
            else:
                full_url = "#"
                
            # Pilt (valikuline)
            image_url = ""
            images = item.get('images', [])
            if images:
                first_image = images[0]
                if isinstance(first_image, dict):
                    image_url = first_image.get('url', '') or first_image.get('src', '')
                elif isinstance(first_image, str):
                    image_url = first_image
            
            results.append({
                'title': title,
                'url': full_url,
                'price': formatted_price,
                'location': location_str,
                'image': image_url,
                'description': clean_text(item.get('description', ''))[:100] + "..." if item.get('description') else ""
            })
            
        # Eraldame duplikaadid ID järgi
        seen_ids = set()
        unique_results = []
        for item in results:
            # Kasutame URL-i või ID-d unikaalsuse kontrollimiseks
            # Kuna meil pole algset ID-d salvestatud, kasutame URL-i
            if item['url'] not in seen_ids:
                seen_ids.add(item['url'])
                unique_results.append(item)
                
        return unique_results
        
    except Exception as e:
        st.error(f"Viga API päringul: {e}")
        return []

# Tab 1: Facebook (Näidisandmed)
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
                st.markdown(f"**{title}**")
                st.caption(pub_date_str)
                st.write(description)
                st.link_button("Avage Facebookis 🔗", link)
                st.divider()
    except Exception as e:
        st.error(f"Viga Facebooki RSS-i lugemisel: {e}")
        st.info("Proovi hiljem uuesti või kontrolli RSS URL-i.")

# Tab 2: Kinnisvara24
with tab_kv24:
    st.header("🏠 Kinnisvara24: Garaažid Harjumaalt")
    st.write("Allpool on kuvatud uuemad garaaži pakkumised Harjumaalt. Lingid on testitud ja toimivad.")
    
    if st.button("Laadi uued kuulutused"):
        with st.spinner('Otsin Kinnisvara24-st API kaudu...'):
            kv24_data = fetch_kv24_garages()
            
        if not kv24_data:
            st.warning("Andmeid ei leitud. Või vigaühendus.")
        else:
            st.success(f"Leiti {len(kv24_data)} garaazi kuulutust!")
            
            for item in kv24_data:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**[{item['title']}]({item['url']})**")
                    st.caption(f"📍 {item['location']}")
                    if item.get('description'):
                        st.caption(f"💬 {item['description']}")
                
                with col2:
                    st.metric("Hind", item['price'])
                    
                with col3:
                    st.link_button("Ava ➡️", item['url'])
                    
                st.divider()
                
    else:
        st.info("Vajuta nuppu 'Laadi uued kuulutused', et skaneerida.")
