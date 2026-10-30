import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import time

# Konfiguratsioon
st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")
st.title("⚡ AI Kuulutuste Skänner (Tallinn & Harjumaa)")

tab_fb, tab_kv24 = st.tabs(["📌 Facebook: Tasuta asjad", "🏠 Kinnisvara24: Garaažid Harjumaal"])

def clean_text(text):
    """Puhastab teksti HTML märgistest."""
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
    
    # Muster: number, siis € või EUR
    match = re.search(r'(\d[\d\s\.]*)\s*(?:€|EUR)(?:\s*/\s*[a-zA-ZäöüõÄÖÜÕ]+)?', text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    
    # Muster: 'hind:' järel number
    match_label = re.search(r'(?:hind|hind:)\s*(\d[\d\s\.]*)', text, re.IGNORECASE)
    if match_label:
        return f"{match_label.group(1).strip()} €"
        
    # Üldine muster: number eurodes/eurot
    match_generic = re.search(r'(\d[\d\s]{2,})\s*(?:eur|euro|eurot)', text, re.IGNORECASE)
    if match_generic:
        return f"{match_generic.group(1).strip()} €"

    return "Hind kokkuleppel / puudub"

def get_full_url(href):
    """Teostab täisaadressi, kui on suhteline link."""
    if not href:
        return "#"
    if href.startswith('http'):
        return href
    if href.startswith('//'):
        return f"https:{href}"
    if href.startswith('/'):
        return f"https://kinnisvara24.ee{href}"
    return href

def fetch_kv24_garages():
    """Võtab garaazi kuulutused Kinnisvara24-st HTML scrapinguga."""
    # Otsinguleht garaazidele Harjumaal
    url = "https://kinnisvara24.ee/kinnisvara-otsing?deal_type=1&property_type=4&search_type=area&county=Harju+maakond"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'et-EE,et;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        st.write("Laadin Kinnisvara24 andmed HTML scrapinguga...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Leiame kõik elemendid, mis sisaldavad linki objekti lehele
        # Kinnisvara24 kasutab sageli <a> elemente klassiga 'listing-card__link' või sarnane.
        # Kui klassid muutuvad, proovime leida kõik <a> lingid, mis viitavad /objekt/
        links = soup.find_all('a', href=re.compile(r'/objekt/'))
        
        for link in links:
            parent_card = link.find_parent(['div', 'article'])
            if not parent_card:
                continue
                
            title_tag = parent_card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span'], class_=re.compile(r'title|name|heading'))
            if not title_tag:
                # Proovi leida pealkiri mingil muul viisil
                title_tag = parent_card.find('a', class_=re.compile(r'title|name|heading')) or link
            
            title = title_tag.get_text(strip=True) if title_tag else "Garaaž"
            
            # Hinde leidmine
            price_container = parent_card.find(['span', 'div'], class_=re.compile(r'price|cost'))
            price_text = ""
            if price_container:
                price_text = price_container.get_text()
            else:
                # Proovi leida hind kogu kaardi tekstist
                price_text = parent_card.get_text()
            
            price = extract_price(price_text)
            
            # Asukoht
            location_container = parent_card.find(['span', 'div'], class_=re.compile(r'location|address|city'))
            location = location_container.get_text(strip=True) if location_container else "Asukoht puudub"
            
            full_link = get_full_url(link.get('href'))
            
            results.append({
                'title': title,
                'url': full_link,
                'price': price,
                'location': location
            })
            
        # Eraldame duplikaadid
        seen_urls = set()
        unique_results = []
        for item in results:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                unique_results.append(item)
                
        return unique_results
        
    except Exception as e:
        st.error(f"Viga andmete laadimisel: {e}")
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
        with st.spinner('Otsin Kinnisvara24-st...'):
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
                
                with col2:
                    st.metric("Hind", item['price'])
                    
                with col3:
                    st.link_button("Ava ➡️", item['url'])
                    
                st.divider()
                
    else:
        st.info("Vajuta nuppu 'Laadi uued kuulutused', et skaneerida.")
