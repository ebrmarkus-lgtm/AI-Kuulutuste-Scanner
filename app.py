import streamlit as st
import streamlit.components.v1 as components
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone

# -----------------------------------------------------------------------------
# 1. LEHE KONFIGURATSIOON & PROFESSIONAALNE DISAIN (UI/UX)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Kuulutuste Skänner", 
    page_icon="⚡", 
    layout="wide"
)

CUSTOM_CSS = """
<style>
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .app-header {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #1e293b;
    }
    .card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .card-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 6px;
    }
    .card-meta {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 12px;
    }
    .card-desc {
        font-size: 0.95rem;
        color: #334155;
        line-height: 1.5;
        margin-bottom: 14px;
    }
    .card-badge {
        display: inline-block;
        background-color: #f1f5f9;
        color: #475569;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
        margin-right: 8px;
    }
    .card-price {
        font-weight: 700;
        color: #0284c7;
    }
    .btn-link {
        display: inline-block;
        background-color: #0f172a;
        color: #ffffff !important;
        font-size: 0.875rem;
        font-weight: 500;
        padding: 8px 16px;
        border-radius: 8px;
        text-decoration: none !important;
        transition: background-color 0.2s ease;
    }
    .btn-link:hover {
        background-color: #334155;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.markdown('<div class="app-header">⚡ AI Kuulutuste Skänner</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. OXFORD-TASEME SEADISTUS & KATKISTE LINKIDE KONTROLL
# -----------------------------------------------------------------------------
def get_http_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

@st.cache_data(ttl=3600, show_spinner=False)
def is_link_valid(url):
    """
    Kontrollib reaalajas, kas URL on ligipääsetav (ei anna 404, 403, 500 jne).
    Tagastab True, kui link on töökorras, ja False, kui link on katki.
    """
    if not url or url == "#" or not url.startswith("http"):
        return False
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        session = get_http_session()
        # Kasutame ensüümina HEAD päringut kiiruse huvides; kui server ei toeta, proovime GET
        response = session.head(url, headers=headers, timeout=5, allow_redirects=True)
        if response.status_code >= 400:
            response = session.get(url, headers=headers, timeout=5, allow_redirects=True)
        
        return 200 <= response.status_code < 400
    except Exception:
        return False

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

# -----------------------------------------------------------------------------
# 3. ANDMEKORJE JA FILTRIMINE
# -----------------------------------------------------------------------------
@st.cache_data(ttl=86400)
def fetch_live_kv24_garages():
    url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'et-EE,et;q=0.9,en;q=0.8'
    }
    
    results = []
    try:
        session = get_http_session()
        response = session.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            listing_links = soup.find_all('a', href=re.compile(r'/kinnisvara/|/objekt/|/garaaz/'))
            
            for a_tag in listing_links:
                href = a_tag.get('href')
                title = a_tag.get_text(strip=True)
                
                if not href or not title or len(title) < 5 or href in ["/garaaz/muuk/harju-maakond", "/garaaz/harju-maakond"]:
                    continue
                
                full_url = href if href.startswith('http') else f"https://kinnisvara24.ee{href}"
                
                # Kontrollime reaalajas, kas objektilink on töökorras enne lisamist
                if not is_link_valid(full_url):
                    continue
                
                parent_container = a_tag.find_parent(['div', 'article', 'li'])
                container_text = parent_container.get_text() if parent_container else title
                price = extract_price(container_text)
                
                if not any(d['url'] == full_url for d in results):
                    results.append({
                        "title": title,
                        "description": "Aktiivne garaaži/boksi müügipakkumine Harjumaal.",
                        "price": price,
                        "location": "Harju maakond",
                        "url": full_url
                    })
    except Exception as e:
        print(f"KV24 viga: {e}")
        
    return results

@st.cache_data(ttl=86400)
def fetch_reitingud_html():
    url = "https://reitingud.ee/reitingud/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        session = get_http_session()
        res = session.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            html = res.text
            html = re.sub(r'Norstat', 'Eesti reitingud globaalselt', html, flags=re.IGNORECASE)
            html = html.replace('<head>', '<head><base href="https://reitingud.ee/">')
            return html
    except Exception as e:
        print(f"Reitingud laadimise viga: {e}")
    return None

# -----------------------------------------------------------------------------
# 4. RAKENDUSE VAHELEHED (TABS)
# -----------------------------------------------------------------------------
tab_fb, tab_kv24, tab_reitingud = st.tabs([
    "📌 Facebook: Tasuta asjad", 
    "🏠 Kinnisvara24: Garaažid",
    "📊 Reitingud"
])

# --- TAB 1: FACEBOOK MARKETPLACE (KATKISTE LINKIDE FILTRIMISEGA) ---
with tab_fb:
    rss_url_fb = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    results_fb = []
    try:
        session = get_http_session()
        resp = session.get(rss_url_fb, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'xml')
            items = soup.find_all(['item', 'entry'])
            one_month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
            
            for item in items:
                link_elem = item.find('link')
                link = "https://www.facebook.com/groups/442569942509759"
                if link_elem:
                    link = link_elem.get('href') or link_elem.get_text(strip=True) or link
                
                # [OXFORD SPESIAALNE KONTROLL] - Eemaldame automaatselt postitused, mille lingid on katki
                if not is_link_valid(link):
                    continue
                
                title_raw = item.find('title').text if item.find('title') else "Tasuta ese"
                title = clean_text(title_raw)
                
                desc_raw = item.find('description') or item.find('summary')
                raw_desc_text = desc_raw.text if desc_raw else ""
                description = clean_text(raw_desc_text)
                
                if len(description) > 180:
                    description = description[:180] + "..."
                
                pub_date_elem = item.find('pubDate') or item.find('updated')
                pub_date_str = pub_date_elem.text if pub_date_elem else ""
                
                timestamp = 0
                if pub_date_str:
                    try:
                        from email.utils import parsedate_to_datetime
                        timestamp = parsedate_to_datetime(pub_date_str).timestamp()
                    except:
                        try:
                            timestamp = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00')).timestamp()
                        except:
                            timestamp = 0

                if timestamp > 0 and timestamp < one_month_ago:
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
                    "location": "Tallinn / Harjumaa",
                    "link": link,
                    "image": image_url,
                    "timestamp": timestamp,
                    "date_str": pub_date_str
                })
                
            results_fb = sorted(results_fb, key=lambda x: x["timestamp"], reverse=True)

    except Exception as e:
        print(f"Viga Facebooki RSS skännimisel: {e}")

    if not results_fb:
        st.info("Hetkel ei ole aktiivseid ja töötavate linkidega kuulutusi.")
    else:
        for item in results_fb:
            with st.container():
                meta_text = f"📅 {item['date_str']}" if item.get('date_str') else ""
                card_html = f"""
                    <div class="card">
                        <div class="card-title">{item['title']}</div>
                        <div class="card-meta">{meta_text}</div>
                        <div class="card-desc">{item['description']}</div>
                        <div>
                            <span class="card-badge card-price">Tasuta</span>
                            <span class="card-badge">📍 {item['location']}</span>
                        </div>
                        <br>
                        <a href="{item['link']}" target="_blank" class="btn-link">👉 Vaata kuulutust</a>
                    </div>
                """
                if item.get("image"):
                    col_img, col_content = st.columns([1, 3])
                    with col_img:
                        st.image(item["image"], use_container_width=True)
                    with col_content:
                        st.markdown(card_html, unsafe_allow_html=True)
                else:
                    st.markdown(card_html, unsafe_allow_html=True)


# --- TAB 2: KINNISVARA24 (AUTOMAATSELT KONTROLLITUD JA TÖÖTAVAD LINGID) ---
with tab_kv24:
    with st.spinner("Laen ja kontrollin Kinnisvara24 aktiivseid linke..."):
        kv24_items = fetch_live_kv24_garages()
    
    canonical_kv24_url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    
    if not kv24_items:
        kv24_items = [
            {
                "title": "Garaažide müügipakkumised Harju maakonnas",
                "description": "Ava Harjumaa ja Tallinna garaažibokside reaalajas avalikud pakkumised Kinnisvara24 portaalis.",
                "price": "Vaata portaalist",
                "location": "Harju maakond",
                "url": canonical_kv24_url
            }
        ]

    for item in kv24_items:
        target_link = item.get("url", canonical_kv24_url)
        st.markdown(f"""
            <div class="card">
                <div class="card-title">{item['title']}</div>
                <div class="card-desc">{item['description']}</div>
                <div>
                    <span class="card-badge card-price">{item['price']}</span>
                    <span class="card-badge">📍 {item['location']}</span>
                </div>
                <br>
                <a href="{target_link}" target="_blank" class="btn-link">👉 Ava see pakkumine Kinnisvara24 portaalis</a>
            </div>
        """, unsafe_allow_html=True)


# --- TAB 3: REITINGUD ---
with tab_reitingud:
    st.markdown("### Eesti reitingud reaalajas praegu")
    st.markdown("---")
    
    reitingud_html = fetch_reitingud_html()
    
    if reitingud_html:
        components.html(reitingud_html, height=850, scrolling=True)
    else:
        components.iframe("https://reitingud.ee/reitingud/", height=850, scrolling=True)
