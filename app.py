import streamlit as st
import streamlit.components.v1 as components
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

# -----------------------------------------------------------------------------
# 1. LEHE KONTSEPTSIOON JA KOHANDATUD PREMIUM CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Kuulutuste Skänner Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

PREMIUM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stApp {
        background-color: #f8fafc;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #0f172a 0%, #2563eb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    
    .sub-title {
        font-size: 0.95rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #e2e8f0;
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 8px 8px 0 0;
        padding: 0 20px;
        font-weight: 600;
        color: #64748b;
        background-color: transparent;
        transition: all 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        color: #2563eb !important;
        background-color: #ffffff !important;
        border-bottom: 2px solid #2563eb !important;
    }

    .custom-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .custom-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        border-color: #cbd5e1;
    }

    .card-header-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.4;
        margin-bottom: 8px;
    }

    .card-date {
        font-size: 0.825rem;
        font-weight: 500;
        color: #94a3b8;
        display: flex;
        align-items: center;
        gap: 4px;
        margin-bottom: 12px;
    }

    .card-body-text {
        font-size: 0.95rem;
        color: #334155;
        line-height: 1.6;
        margin-bottom: 16px;
    }

    .card-footer-tags {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 18px;
    }

    .badge {
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }

    .badge-price {
        background-color: #eff6ff;
        color: #2563eb;
        border: 1px solid #bfdbfe;
    }

    .badge-location {
        background-color: #f8fafc;
        color: #475569;
        border: 1px solid #e2e8f0;
    }

    .btn-action {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 10px 20px;
        background: #0f172a;
        color: #ffffff !important;
        font-size: 0.9rem;
        font-weight: 600;
        border-radius: 10px;
        text-decoration: none !important;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    .btn-action:hover {
        background: #2563eb;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
    }
</style>
"""
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

st.markdown('<div class="main-title">⚡ AI Kuulutuste Skänner</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Reaalajas agregeeritud voog: Facebook Free & Kinnisvara24 Harjumaal</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. HTTP SESSIOON & MULTITHREAD LINGIKONTROLL
# -----------------------------------------------------------------------------
def get_robust_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def check_single_link(url):
    if not url or url == "#" or not url.startswith("http"):
        return False
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        session = get_robust_session()
        res = session.head(url, headers=headers, timeout=4, allow_redirects=True)
        if res.status_code >= 400:
            res = session.get(url, headers=headers, timeout=4, allow_redirects=True)
        return 200 <= res.status_code < 400
    except Exception:
        return False

@st.cache_data(ttl=1800, show_spinner=False)
def filter_valid_items(items, link_key="link"):
    if not items:
        return []
    
    urls = [item.get(link_key) for item in items]
    with ThreadPoolExecutor(max_workers=10) as executor:
        valid_statuses = list(executor.map(check_single_link, urls))
        
    return [item for item, is_valid in zip(items, valid_statuses) if is_valid]

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
    return "Hind kokkuleppel"

# -----------------------------------------------------------------------------
# 3. KORJE JA POOL-AUTOMAATNE SALVESTAMINE
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_live_kv24_garages():
    url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'et-EE,et;q=0.9,en;q=0.8'
    }
    
    results = []
    try:
        session = get_robust_session()
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            listing_links = soup.find_all('a', href=re.compile(r'/kinnisvara/|/objekt/|/garaaz/'))
            
            for a_tag in listing_links:
                href = a_tag.get('href')
                title = a_tag.get_text(strip=True)
                
                if not href or not title or len(title) < 5 or href in ["/garaaz/muuk/harju-maakond", "/garaaz/harju-maakond"]:
                    continue
                
                full_url = href if href.startswith('http') else f"https://kinnisvara24.ee{href}"
                
                parent_container = a_tag.find_parent(['div', 'article', 'li'])
                container_text = parent_container.get_text() if parent_container else title
                price = extract_price(container_text)
                
                if not any(d['url'] == full_url for d in results):
                    results.append({
                        "title": title,
                        "description": "Aktiivne garaaži/boksi müügipakkumine Harju maakonnas.",
                        "price": price,
                        "location": "Harju maakond",
                        "url": full_url
                    })
    except Exception as e:
        print(f"KV24 viga: {e}")
        
    return filter_valid_items(results, link_key="url")

@st.cache_data(ttl=86400)
def fetch_reitingud_html():
    """Laeb reitingud.ee sisu, puhastab üleliigse teksti ja asendab viited."""
    url = "https://reitingud.ee/reitingud/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        session = get_robust_session()
        res = session.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Eemaldame üleliigsed tekstiblokid, uudiskirja vormid ja kontaktiosad
            for selector in ['footer', '.newsletter', '.newsletter-form', '.footer-info', '#footer', '.site-footer', '.contact-info']:
                for match in soup.select(selector):
                    match.decompose()
                    
            # Eemaldame spetsiifiliselt otsitud tekstielemendid
            for element in soup.find_all(['p', 'div', 'section']):
                text_content = element.get_text()
                if "TELLI UUDISKIRI" in text_content or "MTÜ Ühiskonnauuringute Instituut" in text_content or "Uuringufirma" in text_content:
                    element.decompose()
            
            html = str(soup)
            html = re.sub(r'Norstat', 'Eesti reitingud globaalselt', html, flags=re.IGNORECASE)
            html = html.replace('<head>', '<head><base href="https://reitingud.ee/">')
            return html
    except Exception as e:
        print(f"Reitingud laadimise viga: {e}")
    return None

# -----------------------------------------------------------------------------
# 4. TAB-IDE KUVAMISE LOOGIKA
# -----------------------------------------------------------------------------
tab_fb, tab_kv24, tab_reitingud = st.tabs([
    "📌 Facebook: Tasuta asjad", 
    "🏠 Kinnisvara24: Garaažid",
    "📊 Reitingud"
])

# --- TAB 1: FACEBOOK MARKETPLACE ---
with tab_fb:
    rss_url_fb = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    results_fb = []
    try:
        session = get_robust_session()
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
            results_fb = filter_valid_items(results_fb, link_key="link")

    except Exception as e:
        print(f"Viga Facebooki RSS skännimisel: {e}")

    if not results_fb:
        st.info("Hetkel ei ole saadaval ühtegi aktiivse lingiga tasuta kuulutust.")
    else:
        for item in results_fb:
            date_meta = f"📅 {item['date_str']}" if item.get('date_str') else ""
            
            card_html = f"""
            <div class="custom-card">
                <div>
                    <div class="card-header-title">{item['title']}</div>
                    <div class="card-date">{date_meta}</div>
                    <div class="card-body-text">{item['description']}</div>
                </div>
                <div>
                    <div class="card-footer-tags">
                        <span class="badge badge-price">Tasuta</span>
                        <span class="badge badge-location">📍 {item['location']}</span>
                    </div>
                    <a href="{item['link']}" target="_blank" class="btn-action">👉 Vaata kuulutust</a>
                </div>
            </div>
            """
            
            if item.get("image"):
                col_img, col_content = st.columns([1, 2.8])
                with col_img:
                    st.image(item["image"], use_container_width=True)
                with col_content:
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.markdown(card_html, unsafe_allow_html=True)


# --- TAB 2: KINNISVARA24 ---
with tab_kv24:
    with st.spinner("Skännin Kinnisvara24 aktiivseid garaažipakkumisi..."):
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
        <div class="custom-card">
            <div>
                <div class="card-header-title">{item['title']}</div>
                <div class="card-body-text">{item['description']}</div>
            </div>
            <div>
                <div class="card-footer-tags">
                    <span class="badge badge-price">{item['price']}</span>
                    <span class="badge badge-location">📍 {item['location']}</span>
                </div>
                <a href="{target_link}" target="_blank" class="btn-action">👉 Ava pakkumine Kinnisvara24 portaalis</a>
            </div>
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
