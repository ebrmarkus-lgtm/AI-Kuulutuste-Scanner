import streamlit as st
import streamlit.components.v1 as components
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import urllib.parse

# -----------------------------------------------------------------------------
# 1. RAKENDUSE SEADISTUS JA PERFEKTNE UI/UX DISAIN
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Kuulutuste Skänner Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

APP_THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }
    
    /* Päis */
    .hero-container {
        padding: 0.5rem 0 1.25rem 0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 1.5rem;
    }
    
    .main-title {
        font-size: 2rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.025em;
        margin-bottom: 0.25rem;
    }
    
    .sub-title {
        font-size: 0.95rem;
        color: #64748b;
        font-weight: 400;
    }

    /* Vahelehed (Tabs) - Tagab alati nähtava teksti */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 2px solid #e2e8f0;
        margin-bottom: 1.5rem;
        display: flex;
        gap: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 0.95rem;
        color: #475569;
        padding: 10px 16px;
        background-color: transparent;
        border-radius: 8px 8px 0 0;
    }

    .stTabs [aria-selected="true"] {
        color: #2563eb !important;
        background-color: #ffffff !important;
        border-bottom: 2px solid #2563eb !important;
    }

    /* Ühtne ja elegantne kaardi disain (nii pildiga kui ilma) */
    .pro-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        transition: all 0.2s ease;
    }

    .pro-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.06);
        border-color: #cbd5e1;
    }

    .card-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.4;
        margin-bottom: 6px;
    }

    .card-date {
        font-size: 0.8rem;
        font-weight: 500;
        color: #94a3b8;
        margin-bottom: 12px;
    }

    .card-desc {
        font-size: 0.95rem;
        color: #334155;
        line-height: 1.6;
        margin-bottom: 18px;
    }

    /* Märgised */
    .card-tags {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 18px;
    }

    .badge-pill {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.775rem;
        font-weight: 600;
    }

    .badge-free {
        background-color: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
    }

    .badge-price {
        background-color: #eff6ff;
        color: #2563eb;
        border: 1px solid #bfdbfe;
    }

    .badge-location {
        background-color: #f1f5f9;
        color: #475569;
        border: 1px solid #e2e8f0;
    }

    /* Aktsentnupp */
    .pro-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 11px 18px;
        background: #0f172a;
        color: #ffffff !important;
        font-size: 0.9rem;
        font-weight: 600;
        border-radius: 10px;
        text-decoration: none !important;
        transition: all 0.2s ease;
    }

    .pro-btn:hover {
        background: #2563eb;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
    }
</style>
"""
st.markdown(APP_THEME_CSS, unsafe_allow_html=True)

# Päise plokk
st.markdown("""
    <div class="hero-container">
        <div class="main-title">⚡ AI Kuulutuste Skänner</div>
        <div class="sub-title">Reaalajas agregeeritud voog: Facebook Marketplace & Kinnisvara24 Harjumaal</div>
    </div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. VÕRGU SEADISTUS, TÕLGE JA PARALLEELNE VALIDEERIMINE
# -----------------------------------------------------------------------------
def get_robust_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def translate_to_estonian(text):
    if not text:
        return text
    if not re.search(r'[\u0400-\u04FF]', text):
        return text
    try:
        encoded_text = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ru&tl=et&dt=t&q={encoded_text}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            data = response.json()
            translated_sentence = "".join([item[0] for item in data[0] if item[0]])
            return translated_sentence if translated_sentence else text
    except Exception:
        pass
    return text

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
# 3. ANDMEKORJE LOOGIKA (KINNISVARA24 & REITINGUD)
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
                        "description": "Aktiivne garaaži või boksi müügipakkumine Harju maakonnas.",
                        "price": price,
                        "location": "Harju maakond",
                        "url": full_url
                    })
    except Exception as e:
        print(f"KV24 viga: {e}")
        
    return filter_valid_items(results, link_key="url")

@st.cache_data(ttl=86400)
def fetch_reitingud_html():
    url = "https://reitingud.ee/reitingud/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        session = get_robust_session()
        res = session.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for selector in ['footer', '.newsletter', '.newsletter-form', '.footer-info', '#footer', '.site-footer', '.contact-info']:
                for match in soup.select(selector):
                    match.decompose()
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
# 4. VAHELEHED (TABS) - KORRALIKUD TEKSTID JA KLIKITAVAD PEALIRJAD
# -----------------------------------------------------------------------------
tab_fb, tab_kv24, tab_reitingud = st.tabs([
    "🎁 Tasuta asjad (Facebook)", 
    "Kinnisvara objektid",
    "Eesti erakondade reitingud"
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
            
            sold_keywords = ["broneeritud", "läinud", "ära antud", "annatud", "läks", "müüdud", "läinud!", "bron"]

            for item in items:
                link_elem = item.find('link')
                link = "https://www.facebook.com/groups/442569942509759"
                if link_elem:
                    link = link_elem.get('href') or link_elem.get_text(strip=True) or link
                
                title_raw = item.find('title').text if item.find('title') else "Tasuta ese"
                title = translate_to_estonian(clean_text(title_raw))
                
                desc_raw = item.find('description') or item.find('summary')
                raw_desc_text = desc_raw.text if desc_raw else ""
                description = translate_to_estonian(clean_text(raw_desc_text))
                
                combined_text = (title + " " + description).lower()
                if any(keyword in combined_text for keyword in sold_keywords):
                    continue

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
        st.info("Hetkel ei ole saadaval ühtegi aktiivset või vaba tasuta kuulutust.")
    else:
        for item in results_fb:
            date_meta = f"📅 {item['date_str']}" if item.get('date_str') else ""
            
            # Ühtne ja alati korrektselt joonitud kaardi struktuur (pro-card)
            card_content = f"""
            <div class="card-title">{item['title']}</div>
            <div class="card-date">{date_meta}</div>
            <div class="card-desc">{item['description']}</div>
            <div class="card-tags">
                <span class="badge-pill badge-free">Tasuta</span>
                <span class="badge-pill badge-location">📍 {item['location']}</span>
            </div>
            <a href="{item['link']}" target="_blank" class="pro-btn">👉 Vaata kuulutust</a>
            """
            
            if item.get("image"):
                # Kasutame Streamliti konteinerit ja veerge, et pilt ja sisu oleksid kaunilt raamitud
                with st.container():
                    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
                    col_img, col_content = st.columns([1, 2.5])
                    with col_img:
                        st.image(item["image"], use_container_width=True)
                    with col_content:
                        st.markdown(card_content, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                with st.container():
                    st.markdown(f'<div class="pro-card">{card_content}</div>', unsafe_allow_html=True)


# --- TAB 2: KINNISVARA OBJEKTID ---
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
        <div class="pro-card">
            <div class="card-title">{item['title']}</div>
            <div class="card-desc">{item['description']}</div>
            <div class="card-tags">
                <span class="badge-pill badge-price">{item['price']}</span>
                <span class="badge-pill badge-location">📍 {item['location']}</span>
            </div>
            <a href="{target_link}" target="_blank" class="pro-btn">👉 Ava pakkumine Kinnisvara24 portaalis</a>
        </div>
        """, unsafe_allow_html=True)


# --- TAB 3: EESTI ERAKONDADE REITINGUD ---
with tab_reitingud:
    st.markdown("### Eesti erakondade reitingud reaalajas")
    st.markdown("---")
    
    reitingud_html = fetch_reitingud_html()
    
    if reitingud_html:
        components.html(reitingud_html, height=850, scrolling=True)
    else:
        components.iframe("https://reitingud.ee/reitingud/", height=850, scrolling=True)
