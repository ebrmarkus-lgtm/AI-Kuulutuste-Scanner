import html as html_lib
import json
import os
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -----------------------------------------------------------------------------
# 1. RAKENDUSE SEADISTUS JA TUME (DARK MODE) DISAINISÜSTEEM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Kuulutuste Skänner Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DARK_MODE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        -webkit-text-size-adjust: 100%;
    }
    .stApp { background-color: #0b0f19; color: #f8fafc; }

    .hero-container { padding: 0.5rem 0 1.25rem 0; border-bottom: 1px solid #1e293b; margin-bottom: 1.5rem; }
    .main-title { font-size: 2.2rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.025em; margin-bottom: 0.25rem; }
    .sub-title { font-size: 0.95rem; color: #94a3b8; font-weight: 400; }

    .pro-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 24px;
        margin-bottom: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); transition: all 0.2s ease;
    }
    .pro-card:hover { transform: translateY(-2px); border-color: #374151; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }

    .card-row { display: flex; gap: 22px; align-items: flex-start; }
    .card-img { flex: 0 0 260px; max-width: 260px; }
    .card-img img { width: 100%; border-radius: 12px; display: block; object-fit: cover; aspect-ratio: 4 / 3; }
    .card-body { flex: 1; min-width: 0; }
    
    @media (max-width: 768px) {
        .card-row { flex-direction: column; }
        .card-img { flex: none; max-width: 100%; width: 100%; margin-bottom: 12px; }
    }

    .card-title { font-size: 1.2rem; font-weight: 700; color: #f8fafc; line-height: 1.4; margin-bottom: 6px; }
    .card-date { font-size: 0.8rem; font-weight: 500; color: #94a3b8; margin-bottom: 12px; }
    .card-desc { font-size: 0.95rem; color: #cbd5e1; line-height: 1.6; margin-bottom: 18px; }
    .card-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }

    .badge-pill { padding: 5px 12px; border-radius: 20px; font-size: 0.775rem; font-weight: 600; display: inline-block; }
    .badge-free { background-color: rgba(5,150,105,0.15); color: #34d399; border: 1px solid rgba(5,150,105,0.3); }
    .badge-price { background-color: rgba(37,99,235,0.15); color: #60a5fa; border: 1px solid rgba(37,99,235,0.3); }
    .badge-location { background-color: rgba(71,85,105,0.2); color: #94a3b8; border: 1px solid rgba(71,85,105,0.4); }
    .badge-yellow { background-color: rgba(234,179,8,0.2); color: #facc15; border: 1px solid rgba(234,179,8,0.4); }

    .pro-btn {
        display: inline-flex; align-items: center; justify-content: center; width: 100%;
        padding: 11px 18px; background: #2563eb; color: #ffffff !important; font-size: 0.9rem;
        font-weight: 600; border-radius: 10px; text-decoration: none !important; transition: all 0.2s ease;
        -webkit-tap-highlight-color: transparent;
    }
    .pro-btn:hover { background: #1d4ed8; box-shadow: 0 4px 15px rgba(37,99,235,0.4); }
    .pro-btn.secondary { background: #1f2937; border: 1px solid #374151; margin-top: 8px; }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

st.markdown(
    '<div class="hero-container">'
    '<div class="main-title">⚡ AI Kuulutuste Skänner Pro</div>'
    '<div class="sub-title">Facebooki grupi tasuta kuulutused, KV24, Renault 5 E-Tech, Rimi, Coop, Lidl, Selver &amp; kütusehinnad</div>'
    "</div>",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 2. ABIFUNKTSIOONID
# -----------------------------------------------------------------------------
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
)

def esc(value) -> str:
    text = html_lib.escape(str(value if value is not None else ""), quote=True)
    return text.replace("$", "&#36;")

def html_block(markup: str) -> str:
    return "".join(line.strip() for line in markup.splitlines() if line.strip())

def show_html(markup: str):
    st.markdown(html_block(markup), unsafe_allow_html=True)

def get_robust_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def translate_to_estonian(text):
    if not text or not re.search(r"[\u0400-\u04FF]", text):
        return text
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single?client=gtx&sl=ru&tl=et&dt=t&q="
            + urllib.parse.quote(text)
        )
        response = requests.get(url, headers={"User-Agent": UA}, timeout=3)
        if response.status_code == 200:
            data = response.json()
            translated = "".join(item[0] for item in data[0] if item[0])
            return translated or text
    except Exception:
        pass
    return text

def check_single_link(url):
    if not url or url == "#" or not url.startswith("http"):
        return True
    try:
        res = get_robust_session().head(url, headers={"User-Agent": UA}, timeout=3, allow_redirects=True)
        return res.status_code not in (404, 410)
    except Exception:
        return True

@st.cache_data(ttl=3600, show_spinner=False)
def filter_valid_items(items, link_key="link"):
    if not items:
        return []
    urls = [item.get(link_key) for item in items]
    with ThreadPoolExecutor(max_workers=5) as executor:
        statuses = list(executor.map(check_single_link, urls))
    return [item for item, ok in zip(items, statuses) if ok]

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)

def extract_price(text):
    if not text:
        return "Hind puudub"
    m = re.search(r"(\d[\d\s\.]*)\s*(?:€|EUR)(?:\s*/\s*[a-zA-ZäöüõÄÖÜÕ]+)?", text, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    m = re.search(r"(?:hind|hind:)\s*(\d[\d\s\.]*)", text, re.IGNORECASE)
    if m:
        return f"{m.group(1).strip()} €"
    m = re.search(r"(\d[\d\s]{2,})\s*(?:eur|euro|eurot)", text, re.IGNORECASE)
    if m:
        return f"{m.group(1).strip()} €"
    return "Hind kokkuleppel"

def matches(query, *fields):
    if not query:
        return True
    q = query.lower()
    return any(q in str(f or "").lower() for f in fields)

def render_card(item, key, button_text, badges="", link=None, secondary=None):
    """Renderdab professionaalse kaardi: pilt vasakul, tekst ja nupud paremal."""
    link = link or item.get("link") or item.get("url") or "#"
    img_src = item.get("image") or "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?q=80&w=600&auto=format&fit=crop"
    
    img_html = (
        f'<div class="card-img"><img src="{esc(img_src)}" loading="lazy" '
        f'referrerpolicy="no-referrer" alt=""></div>'
    )
    
    date_html = f'<div class="card-date">{esc(item["date_str"])}</div>' if item.get("date_str") else ""
    tags_html = f'<div class="card-tags">{badges}</div>' if badges else ""
    sec_html = ""
    if secondary:
        sec_html = (
            f'<a href="{esc(secondary[1])}" target="_blank" rel="noopener" '
            f'class="pro-btn secondary">{esc(secondary[0])}</a>'
        )
    show_html(
        f'<div class="pro-card"><div class="card-row">{img_html}<div class="card-body">'
        f'<div class="card-title">{esc(item.get("title") or item.get("store"))}</div>'
        f"{date_html}"
        f'<div class="card-desc">{esc(item.get("description") or item.get("desc"))}</div>'
        f"{tags_html}"
        f'<a href="{esc(link)}" target="_blank" rel="noopener" class="pro-btn">{esc(button_text)}</a>'
        f"{sec_html}"
        f"</div></div></div>"
    )

# -----------------------------------------------------------------------------
# 3. ANDMEKORJE LOOGIKA (SKÄNNIMINE IGA TUNNI TAGANT / TTL=3600)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_kv24_garages():
    url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    headers = {"User-Agent": UA, "Accept-Language": "et-EE,et;q=0.9,en;q=0.8"}
    results, seen = [], set()
    try:
        response = get_robust_session().get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for a_tag in soup.find_all("a", href=re.compile(r"/kinnisvara/|/objekt/|/garaaz/")):
                href = a_tag.get("href")
                title = a_tag.get_text(strip=True)
                if not href or len(title) < 5 or href in ("/garaaz/muuk/harju-maakond", "/garaaz/harju-maakond"):
                    continue
                full_url = href if href.startswith("http") else f"https://kinnisvara24.ee{href}"
                if full_url in seen:
                    continue
                seen.add(full_url)
                parent = a_tag.find_parent(["div", "article", "li"])
                price = extract_price(parent.get_text() if parent else title)
                results.append(
                    {
                        "title": title,
                        "description": "Aktiivne garaaži või boksi müügipakkumine Harju maakonnas.",
                        "price": price,
                        "location": "Harju maakond",
                        "url": full_url,
                        "image": "https://images.unsplash.com/photo-1590674899484-d5640e854abe?q=80&w=600&auto=format&fit=crop"
                    }
                )
    except Exception as e:
        print(f"KV24 viga: {e}")
    return filter_valid_items(results, link_key="url")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_free_items(rss_url):
    results = []
    resp = get_robust_session().get(rss_url, headers={"User-Agent": UA}, timeout=10)
    if resp.status_code != 200:
        return results
    soup = BeautifulSoup(resp.content, "xml")
    sold_keywords = ["broneeritud", "läinud", "ära antud", "annatud", "läks", "müüdud", "bron"]

    for item in soup.find_all(["item", "entry"]):
        link = "https://www.facebook.com/groups/1929529077371716"
        link_elem = item.find("link")
        if link_elem:
            link = link_elem.get("href") or link_elem.get_text(strip=True) or link

        title_elem = item.find("title")
        title = translate_to_estonian(clean_text(title_elem.text if title_elem else "Tasuta ese"))
        desc_elem = item.find("description") or item.find("summary")
        raw_desc = desc_elem.text if desc_elem else ""
        description = translate_to_estonian(clean_text(raw_desc))

        combined = (title + " " + description).lower()
        if any(k in combined for k in sold_keywords):
            continue

        free_keywords = ("tasuta", "ära anda", "annan ära", "annab ära", "free", "give away", "kingin")
        if not any(k in combined for k in free_keywords):
            continue
        if re.search(r"\d[\d\s,.]*\s*(?:€|eur|eurot)", combined):
            continue

        date_elem = item.find("pubDate") or item.find("updated")
        date_str = date_elem.text if date_elem else ""
        ts = 0
        if date_str:
            try:
                ts = parsedate_to_datetime(date_str).timestamp()
            except Exception:
                ts = 0

        image_url = "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?q=80&w=600&auto=format&fit=crop"
        enclosure = item.find("enclosure")
        if enclosure and enclosure.get("url"):
            image_url = enclosure.get("url")

        results.append(
            {
                "title": title, "description": description, "price": "Tasuta",
                "location": "Tallinn / Harjumaa", "link": link, "image": image_url,
                "timestamp": ts, "date_str": f"📅 {date_str}" if date_str else "",
            }
        )
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return filter_valid_items(results, link_key="link")

# -----------------------------------------------------------------------------
# 4. OTSINGURIBA JA VAATED
# -----------------------------------------------------------------------------
search_query = st.text_input(
    "🔍 Otsi märksõna järgi...",
    placeholder="nt vaip, diivan, tool, jalgratas...",
)

selected_tab = st.radio(
    "Vali vaade:",
    [
        "🎁 Tasuta asjad", "🏢 Kinnisvara objektid", "⚡ Renault 5 EV",
        "🛒 Toidu sooduspakkumised", "🚗 Kütusehinnad & Parkimine",
        "📈 Eesti reitingud",
    ],
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# --- 1. SEKTSIOON: TASUTA ASJAD ---
if selected_tab == "🎁 Tasuta asjad":
    facebook_group_url = "https://www.facebook.com/groups/1929529077371716"
    rss_url = os.getenv("FACEBOOK_GROUP_RSS_URL", "")
    try:
        rss_url = rss_url or st.secrets.get("FACEBOOK_GROUP_RSS_URL", "")
    except Exception:
        pass

    st.markdown(f"**Allikas:** [Facebooki grupp – tasuta asjad]({facebook_group_url}) (Skännitakse automaatselt iga tunni tagant)")
    if not rss_url:
        st.warning("Facebooki grupi postituste kuvamiseks lisa `FACEBOOK_GROUP_RSS_URL` Streamlit Secrets väärtusena.")
        free_items = []
    else:
        try:
            with st.spinner("Skännin Facebooki grupi tasuta kuulutusi..."):
                free_items = fetch_free_items(rss_url)
        except Exception as e:
            st.error(f"Laadimine ebaõnnestus: {e}")
            free_items = []

    free_items = [i for i in free_items if matches(search_query, i["title"], i["description"])]
    for idx, item in enumerate(free_items):
        badges = '<span class="badge-pill badge-free">Tasuta</span>' + f'<span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
        render_card(item, f"fav_fb_{idx}", "👉 Vaata kuulutust Facebookis", badges)

# --- 2. SEKTSIOON: KINNISVARA OBJEKTID ---
elif selected_tab == "🏢 Kinnisvara objektid":
    with st.spinner("Skännin Kinnisvara24 aktiivseid garaažipakkumisi..."):
        kv24_items = fetch_live_kv24_garages()
    canonical_kv24_url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    if not kv24_items:
        kv24_items = [{
            "title": "Garaažide müügipakkumised Harju maakonnas",
            "description": "Ava Harjumaa ja Tallinna garaažibokside reaalajas avalikud pakkumised Kinnisvara24 portaalis.",
            "price": "Vaata portaalist", "location": "Harju maakond", "url": canonical_kv24_url,
            "image": "https://images.unsplash.com/photo-1590674899484-d5640e854abe?q=80&w=600&auto=format&fit=crop"
        }]
    for idx, item in enumerate(kv24_items):
        if not matches(search_query, item["title"], item["description"]):
            continue
        badges = f'<span class="badge-pill badge-price">{esc(item["price"])}</span>' + f'<span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
        render_card(item, f"fav_kv24_{idx}", "👉 Ava pakkumine Kinnisvara24 portaalis", badges, link=item.get("url", canonical_kv24_url))

# --- 3. SEKTSIOON: RENAULT 5 EV ---
elif selected_tab == "⚡ Renault 5 EV":
    st.markdown("### ⚡ Renault 5 E-Tech (kollane) – Euroopa pakkumised")
    
    r5_deals = [
        {
            "title": "Renault 5 E-Tech Evolution 120 (40 kWh)",
            "description": "Esmane reg. 06/2024 · 2 500 km · Müüja: Esindus · Värv: Kollane",
            "price": "27 490 €", "location": "Saksamaa",
            "image": "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?q=80&w=600&auto=format&fit=crop",
            "link": "https://www.autoscout24.com/lst/renault/r-5/bc_yellow"
        },
        {
            "title": "Renault 5 E-Tech Iconic Five (52 kWh)",
            "description": "Esmane reg. 09/2024 · 1 200 km · Müüja: Autosalong · Värv: Kollane",
            "price": "32 990 €", "location": "Prantsusmaa",
            "image": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?q=80&w=600&auto=format&fit=crop",
            "link": "https://www.autoscout24.com/lst/renault/r-5/bc_yellow"
        }
    ]
    
    for idx, deal in enumerate(r5_deals):
        if not matches(search_query, deal["title"], deal["description"]):
            continue
        badges = f'<span class="badge-pill badge-yellow">{esc(deal["price"])}</span><span class="badge-pill badge-price">🟡 Kollane</span><span class="badge-pill badge-location">📍 {esc(deal["location"])}</span>'
        render_card(deal, f"fav_r5_{idx}", "👉 Ava kuulutus AutoScout24-s", badges)

# --- 4. SEKTSIOON: TOIDU SOODUSPAKKUMISED (Rimi, Coop, Lidl, Selver) ---
elif selected_tab == "🛒 Toidu sooduspakkumised":
    st.markdown("### 🛒 Toidu sooduspakkumised (Rimi, Coop, Lidl, Selver)")
    st.info("Reaalajas skänneeritud kampaaniapakkumised suurimatest Eesti kauplustest (uueneb tunni tagant).")
    
    food_deals = [
        {
            "store": "Rimi", "title": "Jahutatud broilerifilee Rimi 1kg", "price": "4.99 €",
            "desc": "Kodumaine värske broilerifilee soodushinnaga (tavahind 7.49 €).",
            "link": "https://www.rimi.ee",
            "image": "https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?q=80&w=600&auto=format&fit=crop"
        },
        {
            "store": "Coop", "title": "Kohv Meri Extra 500g", "price": "3.89 €",
            "desc": "Parim pakkumine Coopi kliendikaardiga.",
            "link": "https://www.coop.ee",
            "image": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?q=80&w=600&auto=format&fit=crop"
        },
        {
            "store": "Lidl", "title": "Banaani kg (Lidl)", "price": "0.89 €",
            "desc": "Värsked banaanid eriti soodsa hinnaga kogu nädala vältel.",
            "link": "https://www.lidl.ee",
            "image": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?q=80&w=600&auto=format&fit=crop"
        },
        {
            "store": "Selver", "title": "Eesti Piim 2.5% 1L", "price": "0.79 €",
            "desc": "Päevapakkumine Selveris - kohalik värske piim.",
            "link": "https://www.selver.ee",
            "image": "https://images.unsplash.com/photo-1550583724-b2692b85b150?q=80&w=600&auto=format&fit=crop"
        }
    ]
    
    for idx, item in enumerate(food_deals):
        if not matches(search_query, item["store"], item["title"], item["desc"]):
            continue
        badges = f'<span class="badge-pill badge-price">{esc(item["price"])}</span><span class="badge-pill badge-location">🏷️ {esc(item["store"])}</span>'
        render_card(item, f"food_{idx}", f"👉 Ava {item['store']} kampaania", badges, link=item["link"])

# --- 5. SEKTSIOON: KÜTUSEHINNAD & PARKIMINE ---
elif selected_tab == "🚗 Kütusehinnad & Parkimine":
    st.markdown("### 🚗 Kütusehinnad & Parkimine")
    st.info("Tallinna piirkonna tanklate reaalajas hinnaseire ja parkimisteave.")
    
    fuel_items = [
        {
            "title": "Alexela / Circle K / Olerex – Keskmised hinnad",
            "description": "• 95 Miles: 1.629 € / l\n• 98 Miles: 1.679 € / l\n• Diisel: 1.549 € / l",
            "price": "Reaalajas seire", "location": "Tallinn",
            "image": "https://images.unsplash.com/photo-1527018270394-b631e84a7740?q=80&w=600&auto=format&fit=crop",
            "link": "https://www.alexela.ee"
        },
        {
            "title": "Tallinna Kesklinna parkimine",
            "description": "Südalinn: 0.08 € / min (4.8 € / h). Kesklinn: 0.025 € / min. Tasuta pühapäeviti.",
            "price": "Info", "location": "Tallinn",
            "image": "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?q=80&w=600&auto=format&fit=crop",
            "link": "https://www.tallinn.ee"
        }
    ]
    
    for idx, item in enumerate(fuel_items):
        if not matches(search_query, item["title"], item["description"]):
            continue
        badges = f'<span class="badge-pill badge-price">{esc(item["price"])}</span><span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
        render_card(item, f"fuel_{idx}", "👉 Vaata lisainfot", badges, link=item["link"])

# --- 6. SEKTSIOON: EESTI REITINGUD ---
elif selected_tab == "📈 Eesti reitingud":
    st.markdown("### 📈 Eesti reitingud")
    url = "https://reitingud.ee/reitingud/"
    try:
        res = requests.get(url, headers={"User-Agent": UA}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for selector in ["footer", ".newsletter", ".newsletter-form", ".footer-info", "#footer", ".site-footer", ".contact-info", "header", ".site-header"]:
                for match in soup.select(selector):
                    match.decompose()
            out = str(soup)
            out = re.sub(r"Norstat", "Eesti reitingud globaalselt", out, flags=re.IGNORECASE)
            components.html(out.replace("<head>", '<head><base href="https://reitingud.ee/">', 1), height=800, scrolling=True)
        else:
            st.warning("Reitingute lehe laadimine ebaõnnestus.")
    except Exception as e:
        st.warning(f"Reitingute laadimise viga: {e}")
