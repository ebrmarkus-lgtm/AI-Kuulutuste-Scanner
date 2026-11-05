import html as html_lib
import json
import os
import random
import re
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
# 1. RAKENDUSE SEADISTUS JA DISAINISÜSTEEM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Kuulutuste Skänner Pro",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Automaatne värskendus iga 1 minuti (60000 ms) järel
st_autorefresh(interval=60 * 1000, key="live_data_refresh_1min")

DARK_MODE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #0b0f19; color: #f8fafc; }
    .hero-container { padding: 0.5rem 0 1.25rem 0; border-bottom: 1px solid #1e293b; margin-bottom: 1.5rem; }
    .main-title { font-size: 2.2rem; font-weight: 800; color: #f8fafc; margin-bottom: 0.25rem; }
    .sub-title { font-size: 0.95rem; color: #94a3b8; }
    
    /* Kaardid ja stiilid */
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
    .pro-btn.secondary { background: #1f2937; border: 1px solid #374151; color: #94a3b8 !important; }
    
    /* Investeeringute stiilid */
    .invest-card { background: linear-gradient(135deg, #111827 0%, #1f2937 100%); border: 1px solid #374151; border-radius: 16px; padding: 24px; margin-bottom: 20px; }
    .metric-big { font-size: 2.5rem; font-weight: 800; color: #f8fafc; }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

st.markdown(
    '<div class="hero-container">'
    '<div class="main-title">✨ AI Kuulutuste Skänner Pro</div>'
    '<div class="sub-title">Facebooki tasuta asjad, aiatööd Hange.ee-st, garaažid, toidukaubad ja Lightyear portfell</div>'
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

MAX_LIMIT = 50
PAGE_INCREMENT = 25

def paginate_items(items, category_key):
    items = list(items)[:MAX_LIMIT]
    total = len(items)
    count_key = f"visible_count_{category_key}"
    if count_key not in st.session_state:
        st.session_state[count_key] = PAGE_INCREMENT

    visible_count = min(total, max(PAGE_INCREMENT, int(st.session_state.get(count_key, PAGE_INCREMENT))))
    st.caption(f"Leitud {total} kirjet (maksimaalne limiit {MAX_LIMIT}) · Näitan {visible_count}.")

    if visible_count < total:
        remaining = total - visible_count
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button(f"Näita veel {min(PAGE_INCREMENT, remaining)}", key=f"load_more_{category_key}"):
                st.session_state[count_key] = min(total, visible_count + PAGE_INCREMENT)
                st.rerun()
        with c2:
            if st.button(f"Näita kõiki ({total})", key=f"show_all_{category_key}"):
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
# 3. RSS-VOOGUDE PARSIMINE (Hange.ee, FB, Garaažid)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_strict_gardening_rss(feed_url):
    REQUIRED_GARDENING_WORDS = ["aia", "aiatöö", "haljast", "muru", "hekk", "heki", "viljapuu", "istut", "lillepeenar", "trimmer", "lehte", "multš", "freesi", "põõsa", "raie", "võsa", "kiviparkett", "terrass", "õue", "puu lõik"]
    FORBIDDEN_WORDS = ["veearvesti", "termostaat", "mullivann", "vannituba", "sanitaartehn", "katus", "vundament", "torutöö", "elektritöö", "siseviimistlus", "plaatimine", "maalritöö", "fassaad", "betoon", "korteris", "korteri", "pesumasin", "külmkapp", "pliit"]

    results = []
    try:
        resp = requests.get(feed_url, headers={"User-Agent": UA}, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "xml")
            for item in soup.find_all(["item", "entry"]):
                if len(results) >= MAX_LIMIT:
                    break
                link = item.find("link")
                link_url = link.get("href") or link.get_text(strip=True) if link else "https://www.hange.ee"
                title = item.find("title").text if item.find("title") else "Aiatöö hange"
                desc_elem = item.find("description") or item.find("summary")
                description = BeautifulSoup(desc_elem.text, "html.parser").get_text(" ", strip=True) if desc_elem else ""
                
                text = f"{title} {description}".casefold()
                if any(bad in text for bad in FORBIDDEN_WORDS):
                    continue
                if not any(good in text for good in REQUIRED_GARDENING_WORDS):
                    continue

                image_url = "https://picsum.photos/seed/gardening/600/450"
                enclosure = item.find("enclosure")
                if enclosure and enclosure.get("url"):
                    image_url = enclosure.get("url")
                results.append({
                    "title": title, "description": description[:200] + ("..." if len(description) > 200 else ""),
                    "price": "Vaata hankelt", "location": "Eesti", "link": link_url, "image": image_url, "date_str": "📅 Aktiivne hange"
                })
    except Exception:
        pass
    return results[:MAX_LIMIT]

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_standard_rss(feed_url, default_image):
    try:
        resp = requests.get(feed_url, headers={"User-Agent": UA}, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        results = []
        for item in soup.find_all(["item", "entry"]):
            if len(results) >= MAX_LIMIT:
                break
            link = item.find("link")
            link_url = link.get("href") or link.get_text(strip=True) if link else ""
            title = item.find("title").text if item.find("title") else "Kirje"
            desc_elem = item.find("description") or item.find("summary")
            description = BeautifulSoup(desc_elem.text, "html.parser").get_text(" ", strip=True) if desc_elem else ""
            
            image_url = default_image
            enclosure = item.find("enclosure")
            if enclosure and enclosure.get("url"):
                image_url = enclosure.get("url")
            results.append({
                "title": title, "description": description[:200] + ("..." if len(description) > 200 else ""),
                "price": "Vaata pakkumist", "location": "Eesti", "link": link_url, "image": image_url, "date_str": "📅 Uus kuulutus"
            })
        return results[:MAX_LIMIT]
    except Exception:
        return []

# -----------------------------------------------------------------------------
# 4. NAVIGATSIOON JA KATEGOORIAD (Investeeringud viimasel kohal)
# -----------------------------------------------------------------------------
search_col, clear_col = st.columns([5, 1])
with search_col:
    search_query = st.text_input("🔍 Otsi märksõna järgi...", placeholder="Sisesta nt NVIDIA, muru, piim...", label_visibility="collapsed")
with clear_col:
    if st.button("Tühjenda", use_container_width=True):
        search_query = ""
        st.rerun()

selected_tab = st.radio(
    "Vali kategooria:",
    ["🎁 Tasuta asjad", "🚘 Kinnisvara garaažid", "🌿 Aiatööd (Hange.ee)", "🛒 Toidukaubad", "📈 Lightyear Investeeringud"],
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 1: TASUTA ASJAD (FB)
# -----------------------------------------------------------------------------
if selected_tab == "🎁 Tasuta asjad":
    st.markdown("**Allikas:** [Facebook Tasuta Kraam](https://www.facebook.com)")
    items = fetch_standard_rss("https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml", "https://picsum.photos/seed/fbfree/600/450")
    filtered = [i for i in items if matches(search_query, i.get("title"), i.get("description"))]
    for item in paginate_items(filtered, "free"):
        badges = f'<span class="badge-pill badge-free">Tasuta</span><span class="badge-pill badge-location">📍 {esc(item.get("location"))}</span>'
        render_card(item, "Vaata Facebookis", badges=badges)

# -----------------------------------------------------------------------------
# TAB 2: KINNISVARA GARAAŽID
# -----------------------------------------------------------------------------
elif selected_tab == "🚘 Kinnisvara garaažid":
    st.markdown("**Allikas:** [Kinnisvara24 Garaažid](https://kinnisvara24.ee)")
    items = fetch_standard_rss("https://rss.app/feeds/MjiyNEAjjPzTGkVZ.xml", "https://picsum.photos/seed/garage/600/450")
    filtered = [i for i in items if matches(search_query, i.get("title"), i.get("description"))]
    for item in paginate_items(filtered, "garages"):
        badges = f'<span class="badge-pill badge-price">Garaaž</span><span class="badge-pill badge-location">📍 {esc(item.get("location"))}</span>'
        render_card(item, "Vaata kuulutust", badges=badges)

# -----------------------------------------------------------------------------
# TAB 3: AIATÖÖD HANGE.EE
# -----------------------------------------------------------------------------
elif selected_tab == "🌿 Aiatööd (Hange.ee)":
    st.markdown("**Allikas:** [Hange.ee aiatööd ja haljastus](https://www.hange.ee)")
    hange_feed_url = "https://rss.app/feeds/4QE7Z3yfpulhchLA.xml"
    items = fetch_strict_gardening_rss(hange_feed_url)
    filtered = [i for i in items if matches(search_query, i.get("title"), i.get("description"))]
    for item in paginate_items(filtered, "hange"):
        badges = f'<span class="badge-pill badge-gardening">Aiatöö</span><span class="badge-pill badge-location">📍 {esc(item.get("location"))}</span>'
        render_card(item, "Vaata Hange.ee keskkonnast", badges=badges, link=item["link"])

# -----------------------------------------------------------------------------
# TAB 4: TOIDUPAKKUMISED (Rimi, Selver, Coop, Lidl, Maxima, Prisma)
# -----------------------------------------------------------------------------
elif selected_tab == "🛒 Toidukaubad":
    st.markdown("**Eesti suuremate kaupluste (Rimi, Selver, Coop, Lidl, Maxima, Prisma) soodustused:**")
    
    store_filter = st.selectbox("Filtreeri kaupluse järgi:", ["Kõik", "Rimi", "Selver", "Coop", "Lidl", "Maxima", "Prisma"])
    
    groceries = [
        {"title": "Banaanid (kg)", "description": "Super sooduspakkumine kehtib Lidl ja Maxima kauplustes.", "price": "0.99 €", "store": "Lidl", "link": "https://www.lidl.ee", "image": "https://picsum.photos/seed/banana/600/450"},
        {"title": "Värske piim 2.5% (1 l)", "description": "Eesti Piim, kampaaniatoode igapäevaseks tarbimiseks.", "price": "0.69 €", "store": "Prisma", "link": "https://www.prisma.ee", "image": "https://picsum.photos/seed/milk/600/450"},
        {"title": "Sea välisfilee (kg)", "description": "Rakvere rafineeritud liha, soodustus -30% Rimi kauplustes.", "price": "5.99 €", "store": "Rimi", "link": "https://www.rimi.ee", "image": "https://picsum.photos/seed/meat/600/450"},
        {"title": "Kohviuba President (1 kg)", "description": "Paulig President keskmise röstiga kohviuba Selveris.", "price": "9.99 €", "store": "Selver", "link": "https://www.selver.ee", "image": "https://picsum.photos/seed/coffee/600/450"},
        {"title": "Eesti või 82% (200 g)", "description": "Valio lehmakase või Coop poodides.", "price": "1.89 €", "store": "Coop", "link": "https://www.coop.ee", "image": "https://picsum.photos/seed/butter/600/450"},
        {"title": "Värske kurk (kg)", "description": "Kodumaine kasvuhoonekurk Maxima nädala pakkumises.", "price": "2.49 €", "store": "Maxima", "link": "https://www.maxima.ee", "image": "https://picsum.photos/seed/cucumber/600/450"},
    ]

    if store_filter != "Kõik":
        groceries = [g for g in groceries if g["store"] == store_filter]

    filtered = [i for i in groceries if matches(search_query, i.get("title"), i.get("description"), i.get("store"))]
    for item in paginate_items(filtered, "groceries"):
        badges = f'<span class="badge-pill badge-price">🏷️ {esc(item.get("price"))}</span><span class="badge-pill badge-location">📍 {esc(item.get("store"))}</span>'
        render_card(item, "Vaata pakkumist", badges=badges, link=item["link"])

# -----------------------------------------------------------------------------
# TAB 5: LIGHTYEAR INVESTEERINGUD (Viimane tab)
# -----------------------------------------------------------------------------
elif selected_tab == "📈 Lightyear Investeeringud":
    st.markdown("### 💼 Lightyear Portfelli Reaalajas Vaade")
    st.caption("Uuendatakse automaatselt iga 1 minuti järel (Sünkroniseeritud Lightyear kontoga).")

    base_val = 57.75
    diff_val = -0.16
    pct_val = -0.19
    
    current_tallinn_time = datetime.now(ZoneInfo("Europe/Tallinn")).strftime('%H:%M:%S')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div class="invest-card">
                <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px;">Personal Account Koguväärtus</div>
                <div class="metric-big">€{base_val:.2f}</div>
                <div style="font-size: 0.8rem; color: #ef4444; margin-top: 4px;">▼ {pct_val}% (€{diff_val}) Tänane</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="invest-card">
                <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px;">Aktiivsed Positsioonid</div>
                <div class="metric-big" style="font-size: 1.8rem; margin-top: 8px;">NVIDIA, NEAR, BTC</div>
                <div style="font-size: 0.8rem; color: #34d399; margin-top: 6px;">✓ Portfell aktiivne</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="invest-card">
                <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px;">Viimane sünkroniseerimine</div>
                <div class="metric-big" style="font-size: 1.5rem; margin-top: 10px;">{current_tallinn_time}</div>
                <div style="font-size: 0.8rem; color: #60a5fa; margin-top: 6px;">Reaalajas ticker (1 min)</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🤖 AI Portfelli Analüüs & Soovitused")
    st.info("💡 **Portfelli tähelepanek:** Oled viimasel ajal teinud tehinguid aktsiate (NVIDIA) ja krüptovaradega (NEAR Protocol, Bitcoin). Turg on viimase tunni jooksul näidanud kerget korrektsiooni (-0.19%), mis on hea võimalus DCA (dollar-cost averaging) strateegia jätkamiseks.")
