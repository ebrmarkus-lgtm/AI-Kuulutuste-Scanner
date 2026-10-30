import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

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
    """Leiab hinnad tekstist."""
    if not text:
        return "Hind puudub"
    
    # Proovi leida hind muster: number € või EUR
    match = re.search(r'(\d[\d\s\.]*)\s*(?:€|EUR)', text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
        
    return "Hind kokkuleppel / puudub"

def fetch_kv24_garages():
    """Võtab garaaži kuulutused Kinnisvara24-st HTML scrapingu kaudu."""
    url = "https://kinnisvara24.ee/kinnisvara-otsing?deal_type=1&property_type=4&search_type=area&county=Harju+maakond"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    try:
        st.write("Laadin Kinnisvara24 andmed HTML scrape'imisega...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        listings = soup.find_all('a', href=re.compile(r'/objekt/[a-zA-Z0-9]+'))
        
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
            
            location = title.split(',')[0] if ',' in title else "Harjumaa"
            
            results.append({
                'title': title,
                'url': full_url,
                'price': price,
                'location': location
            })
            
        seen_urls = set()
        unique_results = []
        for item in results:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                unique_results.append(item)
                
        return unique_results
        
    except Exception as e:
        st.error(f"Viga scrapingul: {e}")
        return []

# Tab 1: Facebook Marketplace (Tasuta asjad)
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
            count = 0
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
                
                count += 1
                if count >= 10:
                    break
                    
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
            st.success(f"Leiti {len(kv24_data)} garaaži kuulutust!")
            
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
