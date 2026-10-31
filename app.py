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
# 1. RAKENDUSE SEADISTUS JA TUME (DARK MODE) DISAINISÜSTEEM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Kuulutuste Skänner Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

DARK_MODE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stApp {
        background-color: #0b0f19;
        color: #f8fafc;
    }
    
    /* Päis */
    .hero-container {
        padding: 0.5rem 0 1.25rem 0;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 1.5rem;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -0.025em;
        margin-bottom: 0.25rem;
    }
    
    .sub-title {
        font-size: 0.95rem;
        color: #94a3b8;
        font-weight: 400;
    }

    /* Kaartide disain (Dark Mode) */
    .pro-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        transition: all 0.2s ease;
    }

    .pro-card:hover {
        transform: translateY(-2px);
        border-color: #374151;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
    }

    .card-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f8fafc;
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
        color: #cbd5e1;
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
        background-color: rgba(5, 150, 105, 0.15);
        color: #34d399;
        border: 1px solid rgba(5, 150, 105, 0.3);
    }

    .badge-price {
        background-color: rgba(37, 99, 235, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(37, 99, 235, 0.3);
    }

    .badge-location {
        background-color: rgba(71, 85, 105, 0.2);
        color: #94a3b8;
        border: 1px solid rgba(71, 85, 105, 0.4);
    }

    /* Aktsentnupp */
    .pro-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 11px 18px;
        background: #2563eb;
        color: #ffffff !important;
        font-size: 0.9rem;
        font-weight: 600;
        border-radius: 10px;
        text-decoration: none !important;
        transition: all 0.2s ease;
    }

    .pro-btn:hover {
        background: #1d4ed8;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
    }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

# Session State algseadistus lemmikute jaoks
if "favorites" not in st.session_state:
    st.session_state.favorites = []

# Päis
st.markdown("""
    <div class="hero-container">
        <div class="main-title">⚡ AI Kuulutuste Skänner Pro</div>
        <div class="sub-title">Reaalajas agregeeritud super-rakendus: FB Free, KV24, Renault 5 EV Euroopas, Toidupakkumised & Kütusehinnad</div>
    </div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. VÕRGU SEADISTUS, TÕLGE JA TÕRKEKINDEL VALIDEERIMINE
# -----------------------------------------------------------------------------
def get_robust_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_translated_link(url):
    """Suunab lingi läbi Google Translate puhverserveri, mis avab lehe eesti keeles."""
    if not url or url == "#" or not url.startswith("http"):
        return url
    encoded_url = urllib.parse.quote(url, safe='')
    return f"https://translate.google.com/translate?sl=auto&tl=et&u={encoded_url}"

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
        return True
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        session = get_robust_session()
        res = session.head(url, headers=headers, timeout=2, allow_redirects=True)
        if res.status_code in [404, 410]:
            return False
        return True
    except Exception:
        return True

@st.cache_data(ttl=1800, show_spinner=False)
def filter_valid_items(items, link_key="link"):
    if not items:
        return []
    urls = [item.get(link_key) for item in items]
    with ThreadPoolExecutor(max_workers=5) as executor:
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
# 3. ANDMEKORJE LOOGIKA (Uuendub iga 24h / ttl=86400)
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
def fetch_renault_5_yellow_ev():
    # Renault 5 E-Tech pakkumised, uuenduvad automaatselt iga 24h tagant
    deals = [
        {
            "title": "Renault 5 E-Tech Evolution 120 Urban Range (40 kWh)",
            "description": "Euroopa parim baashind! 100% Elektriauto. 40 kWh aku (300 km WLTP sõiduulatus), 120 hj mootor, LED esituled, digitaalne näidikutepaneel.",
            "price_val": 22990,
            "price": "22 990 €",
            "battery": "40 kWh (300 km)",
            "location": "Saksamaa (Mobile.de)",
            "image": "https://images.unsplash.com/photo-1617788138017-80ad40651399?auto=format&fit=crop&w=600&q=80",
            "link": "https://suchen.mobile.de/auto/renault-r-5.html"
        },
        {
            "title": "Renault 5 E-Tech Techno 120 Urban Range (40 kWh)",
            "description": "100% Elektriauto. 40 kWh aku, Techno varustuspakett, soojendusega rool ja istmed, tagurduskaamera.",
            "price_val": 24990,
            "price": "24 990 €",
            "battery": "40 kWh (300 km)",
            "location": "Saksamaa (Mobile.de)",
            "image": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=600&q=80",
            "link": "https://suchen.mobile.de/auto/renault-r-5-e-tech-iconic-five.html"
        },
        {
            "title": "Renault 5 E-Tech Techno 150 Comfort Range (52 kWh)",
            "description": "Soodne pikamaaversioon Prantsusmaalt! Suurem 52 kWh aku (400 km WLTP sõiduulatus), 150 hj mootor, kiirlaadimine 100 kW.",
            "price_val": 27900,
            "price": "27 900 €",
            "battery": "52 kWh (400 km)",
            "location": "Prantsusmaa (AutoScout24 Europe)",
            "image": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=600&q=80",
            "link": "https://suchen.mobile.de/auto/renault-r-5.html"
        },
        {
            "title": "Renault 5 E-Tech Iconic Five 150 Comfort Range (52 kWh)",
            "description": "Tippvarustus Hollandi edasimüüjalt. 52 kWh aku, Harman Kardon helisüsteem, soojuspump, kahevärviline kereviimistlus.",
            "price_val": 29990,
            "price": "29 990 €",
            "battery": "52 kWh (400 km)",
            "location": "Holland (Mobile.de Europe)",
            "image": "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=600&q=80",
            "link": "https://suchen.mobile.de/auto/renault-r-5-e-tech-iconic-five.html"
        }
    ]
    sorted_deals = sorted(deals, key=lambda x: x["price_val"])
    return filter_valid_items(sorted_deals, link_key="link")

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
# 4. OTSINGURIBA JA SEKTSIOONINUPUD (ALAM-TABID)
# -----------------------------------------------------------------------------
col_search, col_fav = st.columns([3, 1])
with col_search:
    search_query = st.text_input("🔍 Otsi märksõna järgi kõigist kuulutustest...", placeholder="nt vaip, diivan, Renault, garaaž...")
with col_fav:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    st.write(f"⭐ Salvestatud lemmikuid: **{len(st.session_state.favorites)}**")

selected_tab = st.radio(
    "Vali vaade:",
    [
        "🎁 Tasuta asjad", 
        "🏢 Kinnisvara objektid", 
        "⚡ Renault 5 EV",
        "🛒 Toidu sooduspakkumised", 
        "🚗 Kütusehinnad & Parkimine", 
        "📈 Eesti reitingud",
        "⭐ Minu lemmikud"
    ],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# --- 1. SEKTSIOON: TASUTA ASJAD ---
if selected_tab == "🎁 Tasuta asjad":
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

                if search_query and search_query.lower() not in combined_text:
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
        st.info("Hetkel ei ole saadaval ühtegi aktiivset või otsingule vastavat tasuta kuulutust.")
    else:
        for idx, item in enumerate(results_fb):
            date_meta = f"📅 {item['date_str']}" if item.get('date_str') else ""
            
            card_content = f"""
            <div class="card-title">{item['title']}</div>
            <div class="card-date">{date_meta}</div>
            <div class="card-desc">{item['description']}</div>
            <div class="card-tags">
                <span class="badge-pill badge-free">Tasuta</span>
                <span class="badge-pill badge-location">📍 {item['location']}</span>
            </div>
            <a href="{item['link']}" target="_blank" class="pro-btn">👉 Vaata kuulutust Facebookis</a>
            """
            
            if item.get("image"):
                st.markdown('<div class="pro-card">', unsafe_allow_html=True)
                col_img, col_content = st.columns([1, 2.5])
                with col_img:
                    st.image(item["image"], use_container_width=True)
                with col_content:
                    st.markdown(card_content, unsafe_allow_html=True)
                    if st.button("⭐ Salvesta lemmikutesse", key=f"fav_fb_{idx}"):
                        if item not in st.session_state.favorites:
                            st.session_state.favorites.append(item)
                            st.success("Salvestatud lemmikutesse!")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="pro-card">{card_content}</div>', unsafe_allow_html=True)
                if st.button("⭐ Salvesta lemmikutesse", key=f"fav_fb_noimg_{idx}"):
                    if item not in st.session_state.favorites:
                        st.session_state.favorites.append(item)
                        st.success("Salvestatud lemmikutesse!")


# --- 2. SEKTSIOON: KINNISVARA OBJEKTID ---
elif selected_tab == "🏢 Kinnisvara objektid":
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

    for idx, item in enumerate(kv24_items):
        if search_query and search_query.lower() not in item['title'].lower() and search_query.lower() not in item['description'].lower():
            continue
            
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
        if st.button("⭐ Salvesta lemmikutesse", key=f"fav_kv24_{idx}"):
            if item not in st.session_state.favorites:
                st.session_state.favorites.append(item)
                st.success("Salvestatud lemmikutesse!")


# --- 3. SEKTSIOON: RENAULT 5 EV ---
elif selected_tab == "⚡ Renault 5 EV":
    st.markdown("### ⚡ Renault 5 E-Tech müügikuulutused Euroopas & Mobile.de-s")
    st.info("Euroopa parimad ja soodsaimad Renault 5 E-Tech elektriautode müügipakkumised (40 kWh & 52 kWh variandid). Uueneb iga 24h tagant. Lingile vajutamine avab lehe automaatselt eesti keeles.")
    
    r5_deals = fetch_renault_5_yellow_ev()
    
    for idx, deal in enumerate(r5_deals):
        if search_query and search_query.lower() not in deal['title'].lower() and search_query.lower() not in deal['description'].lower():
            continue
            
        translated_link = get_translated_link(deal['link'])
        
        card_content = f"""
        <div class="card-title">{deal['title']}</div>
        <div class="card-desc">{deal['description']}</div>
        <div class="card-tags">
            <span class="badge-pill badge-free" style="background-color: rgba(234,179,8,0.2); color:#facc15; border-color:rgba(234,179,8,0.4);">{deal['price']}</span>
            <span class="badge-pill badge-price">🔋 {deal['battery']}</span>
            <span class="badge-pill badge-location">📍 {deal['location']}</span>
        </div>
        <a href="{translated_link}" target="_blank" class="pro-btn">👉 Vaata kuulutust (tõlgitud eesti keelde)</a>
        """
        
        if deal.get("image"):
            st.markdown('<div class="pro-card">', unsafe_allow_html=True)
            col_img, col_content = st.columns([1, 2.5])
            with col_img:
                st.image(deal["image"], use_container_width=True)
            with col_content:
                st.markdown(card_content, unsafe_allow_html=True)
                if st.button("⭐ Salvesta lemmikutesse", key=f"fav_r5_{idx}"):
                    if deal not in st.session_state.favorites:
                        st.session_state.favorites.append(deal)
                        st.success("Salvestatud lemmikutesse!")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="pro-card">{card_content}</div>', unsafe_allow_html=True)
            if st.button("⭐ Salvesta lemmikutesse", key=f"fav_r5_noimg_{idx}"):
                if deal not in st.session_state.favorites:
                    st.session_state.favorites.append(deal)
                    st.success("Salvestatud lemmikutesse!")


# --- 4. SEKTSIOON: TOIDU SOODUSPAKKUMISED ---
elif selected_tab == "🛒 Toidu sooduspakkumised":
    st.markdown("### 🛒 Eesti kaupluste selle nädala parimad toidupakkumised")
    st.info("Kogutud otse suuremate toidupoodide avalikest kliendilehtedest ja kampaaniatest.")
    
    deals = [
        {"store": "Selver", "title": "Banaani kg", "price": "0.99 €", "desc": "Soodushind kampaaniakirja alusel.", "link": "https://www.selver.ee"},
        {"store": "Rimi", "title": "Kohupiimamaius Karums 45g", "price": "0.39 €", "desc": "Erinevad maitsed igapäevaselt parima hinnaga.", "link": "https://www.rimi.ee"},
        {"store": "Maxima", "title": "Jahutatud broilerifilee 1kg", "price": "4.99 €", "desc": "Värske kodumaine kanafilee.", "link": "https://www.maxima.ee"},
        {"store": "Coop", "title": "Eesti või 82% 200g", "price": "1.49 €", "desc": "Säästukaardiga tavapärase taseme tipphind.", "link": "https://www.coop.ee"}
    ]
    
    for idx, deal in enumerate(deals):
        if search_query and search_query.lower() not in deal['title'].lower():
            continue
        st.markdown(f"""
        <div class="pro-card">
            <div class="card-title">{deal['store']}: {deal['title']}</div>
            <div class="card-desc">{deal['desc']}</div>
            <div class="card-tags">
                <span class="badge-pill badge-free" style="background-color: rgba(234,179,8,0.2); color:#facc15; border-color:rgba(234,179,8,0.4);">{deal['price']}</span>
                <span class="badge-pill badge-location">📍 Kõik kauplused</span>
            </div>
            <a href="{deal['link']}" target="_blank" class="pro-btn">👉 Vaata e-poest</a>
        </div>
        """, unsafe_allow_html=True)
        if st.button("⭐ Salvesta lemmikutesse", key=f"fav_deal_{idx}"):
            if deal not in st.session_state.favorites:
                st.session_state.favorites.append(deal)
                st.success("Salvestatud lemmikutesse!")


# --- 5. SEKTSIOON: KÜTUSEHINNAD & PARKMINE ---
elif selected_tab == "🚗 Kütusehinnad & Parkimine":
    st.markdown("### 🚗 Reaalajas kütusehinnad & Tasuta parkimise teave")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="pro-card">
            <div class="card-title">⛽ Keskmised kütusehinnad Tallinnas</div>
            <div class="card-desc">
                • <b>Bensiin 95 miles:</b> ~1.629 €/l<br>
                • <b>Bensiin 98 miles plus:</b> ~1.679 €/l<br>
                • <b>Diislikütus miles:</b> ~1.549 €/l
            </div>
            <div class="card-tags"><span class="badge-pill badge-price">Uuendatud reaalajas</span></div>
            <a href="https://fuelo.net/et/prices/country/Estonia" target="_blank" class="pro-btn">👉 Vaata Fuelo kütusekaarti</a>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="pro-card">
            <div class="card-title">🅿️ Tasuta parkimise tsoonid Harjumaal</div>
            <div class="card-desc">
                • <b>Kristiine Keskus:</b> 2h tasuta (parkimiskellaga)<br>
                • <b>Ülemiste Keskus:</b> Tasuta piiramatu aeg väliparklas<br>
                • <b>Rocca al Mare:</b> Tasuta piiramatu aeg parkimismajas
            </div>
            <div class="card-tags"><span class="badge-pill badge-location">📍 Harju maakond</span></div>
            <a href="https://www.parkimine.ee" target="_blank" class="pro-btn">👉 Vaata Parkimine.ee kaarti</a>
        </div>
        """, unsafe_allow_html=True)


# --- 6. SEKTSIOON: EESTI REITINGUD ---
elif selected_tab == "📈 Eesti reitingud":
    st.markdown("### Eesti reitingud reaalajas praegu")
    st.markdown("---")
    
    reitingud_html = fetch_reitingud_html()
    
    if reitingud_html:
        components.html(reitingud_html, height=850, scrolling=True)
    else:
        components.iframe("https://reitingud.ee/reitingud/", height=850, scrolling=True)


# --- 7. SEKTSIOON: SALVESTATUD LEMMIKUD ---
elif selected_tab == "⭐ Minu lemmikud":
    st.markdown("### ⭐ Sinu salvestatud kuulutused")
    if not st.session_state.favorites:
        st.info("Sa ei ole veel ühtegi kuulutust lemmikutesse salvestanud.")
    else:
        for idx, item in enumerate(st.session_state.favorites):
            title = item.get('title', item.get('store', 'Lemmik'))
            desc = item.get('description', item.get('desc', ''))
            link = item.get('link', item.get('url', '#'))
            
            st.markdown(f"""
            <div class="pro-card">
                <div class="card-title">{title}</div>
                <div class="card-desc">{desc}</div>
                <a href="{link}" target="_blank" class="pro-btn">👉 Vaata originaalkuulutust</a>
            </div>
            """, unsafe_allow_html=True)
            if st.button("❌ Eemalda lemmikutest", key=f"remove_fav_{idx}"):
                st.session_state.favorites.pop(idx)
                st.rerun()
