import html as html_lib
import json
import os
import re
import urllib.parse
from datetime import datetime, timezone
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup

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
    '<div class="sub-title">Facebooki tasuta asjad, Aiatööd Hange.ee-st & Kinnisvara Garaažid</div>'
    "</div>",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 2. ABIFUNKTSIOONID
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

def matches(query, *fields):
    if not query:
        return True
    q = str(query).casefold().strip()
    return any(q in str(field or "").casefold() for field in fields)

PAGE_INCREMENT = 25

def paginate_items(items, category_key):
    items = list(items)
    total = len(items)
    count_key = f"visible_count_{category_key}"
    if count_key not in st.session_state:
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

def render_card(item, button_text, badges="", link=None):
    link = safe_http_url(link or item.get("link") or item.get("url"))
    img_url = safe_http_url(item.get("image"), fallback="https://picsum.photos/seed/fallback/600/450")
    img_html = f'<div class="card-img"><img src="{esc(img_url)}" loading="lazy" alt=""></div>'
    date_html = f'<div class="card-date">{esc(item.get("date_str", ""))}</div>' if item.get("date_str") else ""
    tags_html = f'<div class="card-tags">{badges}</div>' if badges else ""
    primary_html = f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer" class="pro-btn">{esc(button_text)}</a>' if link else '<span class="pro-btn secondary">Link puudub</span>'
    
    show_html(f'<div class="pro-card"><div class="card-row">{img_html}<div class="card-body">'
              f'<div class="card-title">{esc(item.get("title"))}</div>'
              f'{date_html}<div class="card-desc">{esc(item.get("description"))}</div>'
              f'{tags_html}{primary_html}</div></div></div>')

# -----------------------------------------------------------------------------
# 3. RSS VOOGUDE LUGEMISE FUNKTSIOONID (AINULT VÄLISTUSED)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_rss_with_exclusions(feed_url, forbidden_words):
    """Loeb RSS voogu ja jätab vahele AINULT need kuulutused, mis sisaldavad välistatud sõnu."""
    try:
        resp = requests.get(feed_url, headers={"User-Agent": UA}, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        results = []
        
        for item in soup.find_all(["item", "entry"]):
            link = item.find("link")
            link_url = link.get("href") or link.get_text(strip=True) if link else ""
            title = item.find("title").text if item.find("title") else "Kirje"
            desc_elem = item.find("description") or item.find("summary")
            description = BeautifulSoup(desc_elem.text, "html.parser").get_text(" ", strip=True) if desc_elem else ""
            
            combined_text = f"{title} {description}".casefold()
            
            # AINULT VÄLISTUSTE KONTROLL: kui tekstis on mõni keelatud sõna, jäetakse kuulutus vahele
            if any(ex.casefold().strip() in combined_text for ex in forbidden_words):
                continue

            image_url = "https://picsum.photos/seed/gardening/600/450"
            enclosure = item.find("enclosure")
            if enclosure and enclosure.get("url"):
                image_url = enclosure.get("url")
            elif desc_elem:
                img_tag = BeautifulSoup(desc_elem.text, "html.parser").find("img")
                if img_tag and img_tag.get("src"):
                    image_url = img_tag.get("src")

            results.append({
                "title": title,
                "description": description[:200] + ("..." if len(description) > 200 else ""),
                "price": "Vaata hankel",
                "location": "Eesti",
                "link": link_url,
                "image": image_url,
                "date_str": "📅 Uus hange"
            })
        return results
    except Exception:
        return []

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_standard_rss(feed_url, default_image):
    try:
        resp = requests.get(feed_url, headers={"User-Agent": UA}, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        results = []
        for item in soup.find_all(["item", "entry"]):
            link = item.find("link")
            link_url = link.get("href") or link.get_text(strip=True) if link else ""
            title = item.find("title").text if item.find("title") else "Kirje"
            desc_elem = item.find("description") or item.find("summary")
            description = BeautifulSoup(desc_elem.text, "html.parser").get_text(" ", strip=True) if desc_elem else ""
            
            image_url = default_image
            enclosure = item.find("enclosure")
            if enclosure and enclosure.get("url"):
                image_url = enclosure.get("url")
            elif desc_elem:
                img_tag = BeautifulSoup(desc_elem.text, "html.parser").find("img")
                if img_tag and img_tag.get("src"):
                    image_url = img_tag.get("src")

            results.append({
                "title": title,
                "description": description[:200] + ("..." if len(description) > 200 else ""),
                "price": "Vaata pakkumist",
                "location": "Eesti",
                "link": link_url,
                "image": image_url,
                "date_str": "📅 Uus kuulutus"
            })
        return results
    except Exception:
        return []

# -----------------------------------------------------------------------------
# 4. NAVIGATSIOON JA VAATED
# -----------------------------------------------------------------------------
search_query = st.text_input("🔍 Otsi märksõna järgi...", placeholder="nt muru, garaaž, hekk...")

selected_tab = st.radio(
    "Vali vaade:",
    ["🎁 Tasuta asjad", "🚗 Kinnisvara Garaažid", "🌱 Aiatööd Hange.ee", "🛒 Toidu sooduspakkumised"],
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# 1. TASUTA ASJAD (FB)
if selected_tab == "🎁 Tasuta asjad":
    st.markdown("**Allikas:** [Facebook Tasuta Kraam](https://www.facebook.com)")
    items = fetch_standard_rss("https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml", "https://picsum.photos/seed/fbfree/600/450")
    filtered = [i for i in items if matches(search_query, i.get("title"), i.get("description"))]
    for item in paginate_items(filtered, "free"):
        badges = f'<span class="badge-pill badge-free">Tasuta</span><span class="badge-pill badge-location">{esc(item.get("location"))}</span>'
        render_card(item, "Vaata Facebookis", badges=badges)

# 2. KINNISVARA GARAAŽID
elif selected_tab == "🚗 Kinnisvara Garaažid":
    st.markdown("**Allikas:** [Kinnisvara Garaažid](https://kinnisvara24.ee)")
    items = fetch_standard_rss("https://rss.app/feeds/MjiyNEAjjPzTGkVZ.xml", "https://picsum.photos/seed/garage/600/450")
    filtered = [i for i in items if matches(search_query, i.get("title"), i.get("description"))]
    for item in paginate_items(filtered, "garages"):
        badges = f'<span class="badge-pill badge-price">Garaaž</span><span class="badge-pill badge-location">{esc(item.get("location"))}</span>'
        render_card(item, "Vaata pakkumist", badges=badges)

# 3. AIATÖÖD HANGE.EE (KASUTAB AINULT VÄLISTUSI)
elif selected_tab == "🌱 Aiatööd Hange.ee":
    st.markdown("**Allikas:** [Hange.ee aiatööd ja haljastus](https://www.hange.ee)")
    
    # Ainult välistatavad märksõnad (mittesoovitavad ehitus/siseviimistlustööd)
    forbidden_words = [
        "katus", "vundament", "torutöö", "elektritöö", "siseviimistlus", 
        "plaatimine", "maalritöö", "fassaad", "betoon"
    ]
    
    hange_feed_url = "https://rss.app/feeds/4QE7Z3yfpulhchLA.xml"
    items = fetch_rss_with_exclusions(hange_feed_url, forbidden_words)
    
    filtered = [i for i in items if matches(search_query, i.get("title"), i.get("description"))]
    for item in paginate_items(filtered, "hange"):
        badges = f'<span class="badge-pill badge-gardening">Hange</span><span class="badge-pill badge-location">{esc(item.get("location"))}</span>'
        render_card(item, "Vaata Hange.ee-st", badges=badges)

# 4. TOIDUPAKKUMISED
elif selected_tab == "🛒 Toidu sooduspakkumised":
    st.markdown("**Näidispakkumised:** Eesti suuremate kaupluste soodustused.")
    sample_groceries = [
        {"title": "Banaanid (kg)", "description": "Soodushind kehtib Lidl ja Maxima poodides.", "price": "0.99 €", "location": "Kõik kauplused", "link": "https://www.lidl.ee", "image": "https://picsum.photos/seed/banana/600/450"},
        {"title": "Värske piim 2.5% (1L)", "description": "Eesti Piim, kampaania toode.", "price": "0.69 €", "location": "Prisma", "link": "https://www.prisma.ee", "image": "https://picsum.photos/seed/milk/600/450"},
    ]
    filtered = [i for i in sample_groceries if matches(search_query, i.get("title"), i.get("description"))]
    for item in filtered:
        badges = f'<span class="badge-pill badge-price">{esc(item.get("price"))}</span><span class="badge-pill badge-location">{esc(item.get("location"))}</span>'
        render_card(item, "Vaata pakkumist", badges=badges, link=item["link"])
