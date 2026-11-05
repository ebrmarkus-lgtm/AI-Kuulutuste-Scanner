import html as html_lib
import json
import os
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -----------------------------------------------------------------------------
# 1. RAKENDUSE SEADISTUS JA DISAINISÜSTEEM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Kuulutuste Skänner Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st_autorefresh(interval=60 * 60 * 1000, key="hourly_data_refresh")

DARK_MODE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #0b0f19; color: #f8fafc; }
    .hero-container { padding: 0.5rem 0 1.25rem 0; border-bottom: 1px solid #1e293b; margin-bottom: 1.5rem; }
    .main-title { font-size: 2.2rem; font-weight: 800; color: #f8fafc; margin-bottom: 0.25rem; }
    .sub-title { font-size: 0.95rem; color: #94a3b8; }
    .pro-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 24px;
        margin-bottom: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); transition: all 0.2s ease;
    }
    .pro-card:hover { transform: translateY(-2px); border-color: #374151; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }
    .card-row { display: flex; gap: 22px; align-items: flex-start; }
    .card-img { flex: 0 0 280px; max-width: 280px; }
    .card-img img { width: 100%; border-radius: 12px; display: block; object-fit: cover; aspect-ratio: 4 / 3; background-color: #1f2937; }
    .card-body { flex: 1; min-width: 0; }
    @media (max-width: 700px) {
        .card-row { flex-direction: column; }
        .card-img { flex: none; width: 100%; }
    }
    .card-title { font-size: 1.2rem; font-weight: 700; color: #f8fafc; margin-bottom: 6px; }
    .card-date { font-size: 0.8rem; color: #94a3b8; margin-bottom: 12px; }
    .card-desc { font-size: 0.95rem; color: #cbd5e1; line-height: 1.6; margin-bottom: 18px; }
    .card-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
    .badge-pill { padding: 5px 12px; border-radius: 20px; font-size: 0.775rem; font-weight: 600; }
    .badge-free { background-color: rgba(5,150,105,0.15); color: #34d399; border: 1px solid rgba(5,150,105,0.3); }
    .badge-price { background-color: rgba(37,99,235,0.15); color: #60a5fa; border: 1px solid rgba(37,99,235,0.3); }
    .badge-location { background-color: rgba(71,85,105,0.2); color: #94a3b8; border: 1px solid rgba(71,85,105,0.4); }
    .badge-gardening { background-color: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4); }
    .pro-btn {
        display: inline-flex; align-items: center; justify-content: center; width: 100%;
        padding: 11px 18px; background: #2563eb; color: #ffffff !important; font-size: 0.9rem;
        font-weight: 600; border-radius: 10px; text-decoration: none !important; transition: all 0.2s ease;
    }
    .pro-btn:hover { background: #1d4ed8; box-shadow: 0 4px 15px rgba(37,99,235,0.4); }
    .pro-btn.secondary { background: #1f2937; border: 1px solid #374151; margin-top: 8px; }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

st.markdown(
    '<div class="hero-container">'
    '<div class="main-title">⚡ AI Kuulutuste Skänner Pro</div>'
    '<div class="sub-title">Facebooki tasuta asjad, Hange.ee aiatööd, Kinnisvara24 garaažid & Toidupakkumised</div>'
    "</div>",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 2. ÜHISED ABIFUNKTSIOONID
# -----------------------------------------------------------------------------
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def esc(value) -> str:
    return html_lib.escape(str(value if value is not None else ""), quote=True).replace("$", "&#36;")

def safe_http_url(value, fallback=None):
    if not isinstance(value, str):
        return fallback
    candidate = value.strip()
    try:
        parsed = urllib.parse.urlsplit(candidate)
    except ValueError:
        return fallback
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return fallback
    return candidate

def show_html(markup: str):
    st.markdown("".join(line.strip() for line in markup.splitlines() if line.strip()), unsafe_allow_html=True)

def get_robust_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504), allowed_methods=frozenset({"GET", "HEAD"}))
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

@st.cache_data(ttl=86400, show_spinner=False)
def translate_to_estonian(text):
    if not text or not re.search(r"[\u0400-\u04FF]", text):
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=ru&tl=et&dt=t&q=" + urllib.parse.quote(text)
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if response.status_code == 200:
            return "".join(item[0] for item in response.json()[0] if item[0]) or text
    except Exception:
        pass
    return text

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)

def extract_price(text):
    if not text:
        return "Hind kokkuleppel"
    m = re.search(r"(\d[\d\s\.]*)\s*(?:€|EUR)(?:\s*/\s*[a-zA-ZäöüõÄÖÜÕ]+)?", text, re.IGNORECASE)
    return m.group(0).strip() if m else "Hind kokkuleppel"

def matches(query, *fields):
    if not query:
        return True
    q = str(query).casefold().strip()
    return any(q in str(field or "").casefold() for field in fields)

PAGE_INCREMENT = 25

def paginate_items(items, category_key, filters=None):
    items = list(items)
    total = len(items)
    count_key = f"visible_count_{category_key}"
    filter_key = f"visible_filter_{category_key}"
    filter_signature = json.dumps(filters, ensure_ascii=False, sort_keys=True, default=str)

    if st.session_state.get(filter_key) != filter_signature:
        st.session_state[filter_key] = filter_signature
        st.session_state[count_key] = PAGE_INCREMENT

    visible_count = min(total, max(PAGE_INCREMENT, int(st.session_state.get(count_key, PAGE_INCREMENT))))
    st.caption(f"Leitud {total} tulemust · Näitan {visible_count}.")

    if visible_count < total:
        remaining = total - visible_count
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button(f"Näita veel {min(PAGE_INCREMENT, remaining)}", key=f"load_more_{category_key}"):
                st.session_state[count_key] = min(total, visible_count + PAGE_INCREMENT)
                st.rerun()
        with c2:
            if st.button("Näita kõiki", key=f"show_all_{category_key}"):
                st.session_state[count_key] = total
                st.rerun()

    return items[:visible_count]

def render_card(item, key, button_text, badges="", link=None, secondary=None):
    link = safe_http_url(link or item.get("link") or item.get("url"))
    img_url = safe_http_url(item.get("image"), fallback="https://picsum.photos/seed/hangeval/600/450")
    img_html = f'<div class="card-img"><img src="{esc(img_url)}" loading="lazy" alt="" onerror="this.onerror=null;this.src=\'https://picsum.photos/seed/fallback/600/450\';"></div>'
    date_html = f'<div class="card-date">{esc(item["date_str"])}</div>' if item.get("date_str") else ""
    tags_html = f'<div class="card-tags">{badges}</div>' if badges else ""
    
    sec_html = ""
    if secondary and (sec_url := safe_http_url(secondary[1])):
        sec_html = f'<a href="{esc(sec_url)}" target="_blank" rel="noopener noreferrer" class="pro-btn secondary">{esc(secondary[0])}</a>'
    
    primary_html = f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer" class="pro-btn">{esc(button_text)}</a>' if link else '<span class="pro-btn secondary">Link puudub</span>'
    
    show_html(f'<div class="pro-card"><div class="card-row">{img_html}<div class="card-body">'
              f'<div class="card-title">{esc(item.get("title") or item.get("store"))}</div>'
              f'{date_html}<div class="card-desc">{esc(item.get("description") or item.get("desc"))}</div>'
              f'{tags_html}{primary_html}{sec_html}</div></div></div>')

# -----------------------------------------------------------------------------
# 3. ANDMEKORJE MOODULID
# -----------------------------------------------------------------------------
HANGE_BASE_URL = "https://www.hange.ee"
HANGE_ACTIVE_LIST_URL = f"{HANGE_BASE_URL}/hanked/?filter=all-active"
HANGE_OFFER_PATH = re.compile(r"^/\d+/[^/]+/?$")
HANGE_GARDENING_KEYWORDS = ("aia", "aiamaja", "aiatöö", "aed", "haljast", "muru", "muruniit", "hekk", "heki", "viljapuu", "põõsa", "raie", "õue", "kiviparkett", "lillepeenar")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_hange_gardening():
    session = get_robust_session()
    headers = {"User-Agent": UA, "Accept-Language": "et-EE,et;q=0.9"}
    try:
        r = session.get(HANGE_ACTIVE_LIST_URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
    except Exception:
        return []

    results, seen_urls = [], set()
    for row in soup.select("table.table_hanked tbody tr"):
        if not (title_link := row.select_one("h2 a.border-link[href]")):
            continue
        offer_url = safe_http_url(urllib.parse.urljoin(HANGE_BASE_URL, title_link.get("href", "")))
        if not offer_url or offer_url in seen_urls or not HANGE_OFFER_PATH.fullmatch(urllib.parse.urlsplit(offer_url).path):
            continue
        
        title = title_link.get_text(" ", strip=True)
        detail = row.select_one(".table-txt p")
        description = detail.get_text(" ", strip=True) if detail else ""
        if not any(k in f"{title} {description}".casefold() for k in HANGE_GARDENING_KEYWORDS):
            continue

        seen_urls.add(offer_url)
        loc_match = re.search(r"Asukoht:\s*(.*?)(?:\s+Hanke etapp:|$)", description, re.IGNORECASE)
        location = loc_match.group(1).strip() if loc_match else "Eesti"
        
        img = row.select_one(".table-img img")
        img_url = safe_http_url(urllib.parse.urljoin(HANGE_BASE_URL, img.get("data-src") or img.get("src") if img else ""), fallback="https://picsum.photos/seed/hange/600/450")
        
        cells = row.find_all("td", recursive=False)
        added = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
        results.append({"title": title, "description": description or "Aktiivne hange.", "price": "Vaata Hange.ee-st", "location": location, "link": offer_url, "date_str": f"📅 Lisatud {added}" if added else "", "image": img_url})
    return results

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_kv24_garages():
    url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    headers = {"User-Agent": UA, "Accept-Language": "et-EE,et;q=0.9"}
    try:
        r = get_robust_session().get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return []

    results, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href or not any(sub in href for sub in ["/kinnisvara/", "/objekt/", "/garaaz/"]):
            continue
        
        title = a.get_text(" ", strip=True)
        if len(title) < 5 or href in ("/garaaz/muuk/harju-maakond", "/garaaz/harju-maakond"):
            continue
            
        full_url = safe_http_url(urllib.parse.urljoin("https://kinnisvara24.ee", href))
        if not full_url or full_url in seen:
            continue
        seen.add(full_url)
        
        parent = a.find_parent(["div", "article", "li", "section"])
        parent_text = parent.get_text(" ", strip=True) if parent else title
        price = extract_price(parent_text)
        
        img_url = "https://picsum.photos/seed/kv24gar/600/450"
        if parent:
            img_tag = parent.find("img")
            if img_tag:
                img_url = safe_http_url(img_tag.get("data-src") or img_tag.get("src"), fallback=img_url)

        results.append({
            "title": title, 
            "description": "Aktiivne garaaži või boksi pakkumine Harjumaal.",
            "price": price,
            "location": "Harju maakond", 
            "url": full_url, 
            "image": img_url
        })
    return results

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_free_items(rss_url):
    try:
        r = get_robust_session().get(rss_url, headers={"User-Agent": UA}, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "xml")
    except Exception:
        return []

    results, one_month_ago = [], (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    sold_keywords = ["broneeritud", "läinud", "ära antud", "annatud", "läks", "müüdud", "bron"]
    free_keywords = ("tasuta", "ära anda", "annan ära", "annab ära", "free", "give away", "võib ära viia", "kingin")

    for item in soup.find_all(["item", "entry"]):
        link = item.find("link")
        link_url = link.get("href") or link.get_text(strip=True) if link else "https://www.facebook.com"
        
        title = translate_to_estonian(clean_text(item.find("title").text if item.find("title") else "Tasuta ese"))
        raw_desc = item.find("description") or item.find("summary")
        description = translate_to_estonian(clean_text(raw_desc.text if raw_desc else ""))
        
        combined = (title + " " + description).lower()
        if any(k in combined for k in sold_keywords) or not any(k in combined for k in free_keywords) or re.search(r"\d[\d\s,.]*\s*(?:€|eur|eurot)", combined):
            continue

        if len(description) > 180:
            description = description[:180] + "..."

        date_elem = item.find("pubDate") or item.find("updated")
        date_str = date_elem.text if date_elem else ""
        ts = 0
        if date_str:
            try:
                ts = parsedate_to_datetime(date_str).timestamp()
            except Exception:
                try:
                    ts = datetime.fromisoformat(date_str.replace("Z", "+00:00")).timestamp()
                except Exception:
                    pass
        if 0 < ts < one_month_ago:
            continue

        image_url = "https://picsum.photos/seed/fbfree/600/450"
        if (enc := item.find("enclosure")) and enc.get("url"):
            image_url = enc.get("url")
        elif raw_desc and (img := BeautifulSoup(raw_desc.text, "html.parser").find("img")) and img.get("src"):
            image_url = img.get("src")

        results.append({
            "title": title, "description": description, "price": "Tasuta",
            "location": "Tallinn / Harjumaa", "link": link_url, "image": image_url,
            "timestamp": ts, "date_str": f"📅 {date_str}" if date_str else ""
        })
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results

def _capture_source(fetcher, *args):
    try:
        return {"data": fetcher(*args), "error": None}
    except Exception as error:
        return {"data": None, "error": type(error).__name__}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_hourly_source_snapshot(rss_url):
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "free": _capture_source(fetch_free_items, rss_url) if rss_url else {"data": [], "error": "RSS_URL_NOT_CONFIGURED"},
        "kv24": _capture_source(fetch_live_kv24_garages),
        "hange": _capture_source(fetch_live_hange_gardening),
    }

# -----------------------------------------------------------------------------
# 4. KASUTAJALIIDES JA NAVIGATSIOON
# -----------------------------------------------------------------------------
def get_secret_value(name):
    return os.getenv(name, "") or str(st.secrets.get(name, "")).strip()

rss_url = get_secret_value("FACEBOOK_GROUP_RSS_URL")
with st.spinner("Värskendan andmeallikaid..."):
    source_snapshot = fetch_hourly_source_snapshot(rss_url)

checked_at = datetime.fromisoformat(source_snapshot["checked_at"]).astimezone(timezone.utc)
st.caption(f"Viimane kontroll: {checked_at:%d.%m.%Y %H:%M} UTC")

search_query = st.text_input("🔍 Otsi märksõna järgi...", placeholder="nt vaip, diivan, garaaž...")

selected_tab = st.radio(
    "Vali vaade:",
    ["🎁 Tasuta asjad", "🏢 Kinnisvara", "🌱 Aiatööd Hange.ee", "🛒 Toidu sooduspakkumised"],
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# 1. TASUTA ASJAD
if selected_tab == "🎁 Tasuta asjad":
    fb_url = "https://www.facebook.com/groups/1929529077371716"
    st.markdown(f"**Allikas:** [Facebooki grupp]({fb_url})")
    if not rss_url:
        st.warning("Lisa Streamlit Secrets alla `FACEBOOK_GROUP_RSS_URL`, et näha grupi postitusi.")
        free_items = []
    else:
        res = source_snapshot["free"]
        free_items = res["data"] if not res["error"] else []

    filtered = [item for item in free_items if matches(search_query, item.get("title"), item.get("description"))]
    for item in paginate_items(filtered, "free_items"):
        badges = f'<span class="badge-pill badge-free">Tasuta</span><span class="badge-pill badge-location">{esc(item.get("location"))}</span>'
        render_card(item, key=item["link"], button_text="Vaata Facebookis", badges=badges)

# 2. KINNISVARA
elif selected_tab == "🏢 Kinnisvara":
    st.markdown("**Allikas:** [Kinnisvara24 Garaažid](https://kinnisvara24.ee/garaaz/muuk/harju-maakond)")
    res = source_snapshot["kv24"]
    items = res["data"] if not res["error"] else []
    filtered = [item for item in items if matches(search_query, item.get("title"), item.get("description"))]
    for item in paginate_items(filtered, "kv24_items"):
        badges = f'<span class="badge-pill badge-price">{esc(item.get("price"))}</span><span class="badge-pill badge-location">{esc(item.get("location"))}</span>'
        render_card(item, key=item["url"], button_text="Vaata Kinnisvara24-st", badges=badges, link=item["url"])

# 3. AIATÖÖD
elif selected_tab == "🌱 Aiatööd Hange.ee":
    st.markdown("**Allikas:** [Hange.ee](https://www.hange.ee)")
    res = source_snapshot["hange"]
    items = res["data"] if not res["error"] else []
    filtered = [item for item in items if matches(search_query, item.get("title"), item.get("description"))]
    for item in paginate_items(filtered, "hange_items"):
        badges = f'<span class="badge-pill badge-gardening">Aiatöö</span><span class="badge-pill badge-location">{esc(item.get("location"))}</span>'
        render_card(item, key=item["url"], button_text="Vaata hankel", badges=badges, link=item["url"])

# 4. TOIDUPAKKUMISED
elif selected_tab == "🛒 Toidu sooduspakkumised":
    st.markdown("**Näidispakkumised:** Eesti suuremate kaupluste soodustused.")
    sample_groceries = [
        {"title": "Banaanid (kg)", "desc": "Soodushind kehtib Lidl ja Maxima poodides.", "price": "0.99 €", "location": "Kõik kauplused", "link": "https://www.lidl.ee"},
        {"title": "Värske piim 2.5% (1L)", "desc": "Eesti Piim, kampaania toode.", "price": "0.69 €", "location": "Prisma", "link": "https://www.prisma.ee"},
    ]
    for item in sample_groceries:
        if matches(search_query, item["title"], item["desc"]):
            badges = f'<span class="badge-pill badge-price">{esc(item["price"])}</span><span class="badge-pill badge-location">{esc(item["location"])}</span>'
            render_card(item, key=item["link"], button_text="Vaata pakkumist", badges=badges, link=item["link"])
