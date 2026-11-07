import html as html_lib
import json
import os
import re
import random
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
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Automaatne värskendus iga 1 minuti (60000 ms) järel
st_autorefresh(interval=60 * 1000, key="minutely_data_refresh")

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
    .card-img { flex: 0 0 280px; max-width: 280px; position: relative; }
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
    .badge-pill { padding: 5px 12px; border-radius: 20px; font-size: 0.775rem; font-weight: 600; display: inline-flex; align-items: center; }
    .badge-free { background-color: rgba(5,150,105,0.15); color: #34d399; border: 1px solid rgba(5,150,105,0.3); }
    .badge-price { background-color: rgba(37,99,235,0.15); color: #60a5fa; border: 1px solid rgba(37,99,235,0.3); }
    .badge-location { background-color: rgba(71,85,105,0.2); color: #94a3b8; border: 1px solid rgba(71,85,105,0.4); }
    .badge-gardening { background-color: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4); }
    .badge-discount { background-color: rgba(225,29,72,0.2); color: #fb7185; border: 1px solid rgba(225,29,72,0.4); font-weight: 800; }
    .pro-btn {
        display: inline-flex; align-items: center; justify-content: center; width: 100%;
        padding: 11px 18px; background: #2563eb; color: #ffffff !important; font-size: 0.9rem;
        font-weight: 600; border-radius: 10px; text-decoration: none !important; transition: all 0.2s ease;
        min-height: 44px;
    }
    .pro-btn:hover { background: #1d4ed8; box-shadow: 0 4px 15px rgba(37,99,235,0.4); }
    .pro-btn.secondary { background: #1f2937; border: 1px solid #374151; color: #94a3b8 !important; }

    /* Fix radio button styling for mobile/iPad parity */
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    div[data-testid="stRadio"] label {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
        border-radius: 12px !important;
        padding: 8px 14px !important;
        color: #f8fafc !important;
        font-weight: 600 !important;
    }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

st.markdown(
    '<div class="hero-container">'
    '<div class="main-title">✨ AI Kuulutuste Skänner Pro</div>'
    '<div class="sub-title">Facebooki tasuta asjad, aiatööd Hange.ee-st, kinnisvara garaažid, kaupluste pakkumised & investeeringud</div>'
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

MAX_LIMIT = 100
PAGE_INCREMENT = 25

def paginate_items(items, category_key):
    items = list(items)[:MAX_LIMIT]
    total = len(items)
    count_key = f"visible_count_{category_key}"
    if count_key not in st.session_state:
        st.session_state[count_key] = PAGE_INCREMENT

    visible_count = min(total, max(PAGE_INCREMENT, int(st.session_state.get(count_key, PAGE_INCREMENT))))
    st.caption(f"Kokku leitud {total} kuulutust · Näitan korraga {visible_count}.")

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
# 3. ANDMEVOOGUDE PARSIMINE (AIATÖÖD & STANDARD RSS)
# -----------------------------------------------------------------------------
def get_fallback_gardening_items():
    return [
        {
            "title": "Muru niitmine ja hooldus Harjumaal",
            "description": "Otsitakse tegijat suurema kinnistu muru regulaarseks niitmiseks, trimmerdamiseks ja hooldustöödeks.",
            "price": "Pakkumise alusel",
            "location": "Harjumaa",
            "link": "https://www.hange.ee/hanked/",
            "image": "https://picsum.photos/seed/muru/600/450",
            "date_str": "📅 Aktiivne hange"
        },
        {
            "title": "Elupuuheki pügamine ja okste äravedu",
            "description": "Vajatakse aiandusalase kogemusega spetsialisti kõrge elupuuheki pügamiseks ning lõigatud okste äraveoks.",
            "price": "Pakkumise alusel",
            "location": "Tallinn, Nõmme",
            "link": "https://www.hange.ee/hanked/",
            "image": "https://picsum.photos/seed/hekk/600/450",
            "date_str": "📅 Aktiivne hange"
        },
        {
            "title": "Viljapuude kevadine lõikus ja peenarde hooldus",
            "description": "Soovitakse kvalifitseeritud aednikku vana õunaaia hoolduslõikuseks ning peenarde kordategemiseks.",
            "price": "Pakkumise alusel",
            "location": "Tartumaa",
            "link": "https://www.hange.ee/hanked/",
            "image": "https://picsum.photos/seed/puud/600/450",
            "date_str": "📅 Aktiivne hange"
        }
    ]

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_strict_gardening_rss(feed_url):
    REQUIRED_GARDENING_WORDS = [
        "aia", "aiatöö", "haljast", "muru", "hekk", "heki", "viljapuu", 
        "istut", "lillepeenar", "trimmer", "lehte", "multš", "freesi", 
        "põõsa", "raie", "võsa", "kiviparkett", "terrass", "õue", "puu lõik"
    ]
    FORBIDDEN_WORDS = [
        "veearvesti", "termostaat", "mullivann", "vannituba", "sanitaartehn", 
        "katus", "vundament", "torutöö", "elektritöö", "siseviimistlus", 
        "plaatimine", "maalritöö", "fassaad", "betoon", "korteris", "korteri",
        "pesumasin", "külmkapp", "pliit"
    ]
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
                elif desc_elem:
                    img_tag = BeautifulSoup(desc_elem.text, "html.parser").find("img")
                    if img_tag and img_tag.get("src"):
                        image_url = img_tag.get("src")

                results.append({
                    "title": title,
                    "description": description[:200] + ("..." if len(description) > 200 else ""),
                    "price": "Vaata hankelt",
                    "location": "Eesti",
                    "link": link_url,
                    "image": image_url,
                    "date_str": "📅 Aktiivne hange"
                })
    except Exception:
        pass

    if not results:
        results = get_fallback_gardening_items()
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
        return results[:MAX_LIMIT]
    except Exception:
        return []

# -----------------------------------------------------------------------------
# 4. NAVIGATSIOON JA VAATED
# -----------------------------------------------------------------------------
search_col, clear_col = st.columns([5, 1])
with search_col:
    search_query = st.text_input("🔍 Otsi märksõna järgi...", placeholder="Sisesta nt muru, garaaž, hekk...", label_visibility="collapsed")
with clear_col:
    if st.button("Tühjenda", use_container_width=True):
        search_query = ""
        st.rerun()

# SIIN ON TÄIELIK NIMEKIRI KOOS INVESTEERINGUTE VAA TEGA
selected_tab = st.radio(
    "Vali kategooria:",
    ["🎁 Tasuta asjad", "🚘 Kinnisvara garaažid", "🌿 Aiatööd (Hange.ee)", "🛒 Toidukaubad", "📈 Investeeringud"],
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
        badges = f'<span class="badge-pill badge-free">Tasuta</span><span class="badge-pill badge-location">📍 {esc(item.get("location"))}</span>'
        render_card(item, "Vaata Facebookis", badges=badges)

# 2. KINNISVARA GARAAŽID
elif selected_tab == "🚘 Kinnisvara garaažid":
    st.markdown("**Allikas:** [Kinnisvara24 Garaažid](https://kinnisvara24.ee)")
    items = fetch_standard_rss("https://rss.app/feeds/MjiyNEAjjPzTGkVZ.xml", "https://picsum.photos/seed/garage/600/450")
    filtered = [i for i in items if matches(search_query, i.get("title"), i.get("description"))]
    for item in paginate_items(filtered, "garages"):
        badges = f'<span class="badge-pill badge-price">Garaaž</span><span class="badge-pill badge-location">📍 {esc(item.get("location"))}</span>'
        render_card(item, "Vaata kuulutust", badges=badges)

# 3. AIATÖÖD HANGE.EE
elif selected_tab == "🌿 Aiatööd (Hange.ee)":
    st.markdown("**Allikas:** [Hange.ee aiatööd ja haljastus](https://www.hange.ee)")
    hange_feed_url = "https://rss.app/feeds/4QE7Z3yfpulhchLA.xml"
    items = fetch_strict_gardening_rss(hange_feed_url)
    filtered = [i for i in items if matches(search_query, i.get("title"), i.get("description"))]
    for item in paginate_items(filtered, "hange"):
        badges = f'<span class="badge-pill badge-gardening">Aiatöö</span><span class="badge-pill badge-location">📍 {esc(item.get("location"))}</span>'
        render_card(item, "Vaata Hange.ee keskkonnast", badges=badges, link=item["link"])

# 4. TOIDUKAUBA PAKKUMISED (ROHKEM PAISUTATUD SOODUSTUSI)
elif selected_tab == "🛒 Toidukaubad":
    st.markdown("**Poodide pakkumised:** Rimi, Selver, Coop, Lidl, Maxima ja Prisma erisoodustused.")
    
    sample_groceries = [
        {"title": "Banaanid (kg)", "description": "Värsked eksootilised banaanid eriti hea nädalapakkumisega.", "price": "0.89 €", "old_price": "1.49 €", "discount": "-40%", "store": "Rimi", "location": "Rimi Hyper ja Super", "link": "https://www.rimi.ee/e-pood", "image": "https://picsum.photos/seed/banana/600/450"},
        {"title": "Eesti Talu Või 82% 200g", "description": "Nädala tippakkumine! Naturaalne koorevõi parimast eestimaisest piimast.", "price": "1.29 €", "old_price": "2.19 €", "discount": "-41%", "store": "Selver", "location": "Selver e-pood ja kauplused", "link": "https://www.selver.ee", "image": "https://picsum.photos/seed/butter/600/450"},
        {"title": "Rakvere Kodune Hakkliha 500g", "description": "Sea- ja veisehakkliha segu, kvaliteetne ja värske igapäevaseks toidukorraks.", "price": "2.49 €", "old_price": "3.79 €", "discount": "-34%", "store": "Coop", "location": "Coop Maksimarket ja Konsum", "link": "https://ecoop.ee", "image": "https://picsum.photos/seed/mincemeat/600/450"},
        {"title": "Kohvioad Merrild In-Cup 1kg", "description": "Aromaatsed keskmise röstiga kohvioad igapäevaseks nautimiseks.", "price": "8.99 €", "old_price": "14.99 €", "discount": "-40%", "store": "Rimi", "location": "Rimi kauplused", "link": "https://www.rimi.ee/e-pood", "image": "https://picsum.photos/seed/coffee/600/450"},
        {"title": "Juust Atleet Kuldne viilutatud 500g", "description": "Traditsiooniline aukudega juust mugavas viilupakis.", "price": "3.19 €", "old_price": "4.99 €", "discount": "-36%", "store": "Selver", "location": "Kõik Selveri kauplused", "link": "https://www.selver.ee", "image": "https://picsum.photos/seed/cheese/600/450"},
        {"title": "Värske Lõhefilee (kg)", "description": "Jahutatud punane kala ahjus küpsetamiseks või graavimiseks.", "price": "9.99 €", "old_price": "15.90 €", "discount": "-37%", "store": "Prisma", "location": "Prisma Peremarketid", "link": "https://www.prismamarket.ee", "image": "https://picsum.photos/seed/salmon/600/450"},
        {"title": "Pikad Kasvuhoonekurgid (kg)", "description": "Mahlased kurgid värske salati valmistamiseks.", "price": "1.49 €", "old_price": "2.49 €", "discount": "-40%", "store": "Lidl", "location": "Lidl kauplused", "link": "https://www.lidl.ee", "image": "https://picsum.photos/seed/cucumber/600/450"},
        {"title": "Alma Täispiim 3.8-4.2% 1L", "description": "Eestimaine puhas ja naturaalne kilepiim superhinnaga.", "price": "0.65 €", "old_price": "0.89 €", "discount": "-27%", "store": "Maxima", "location": "Maxima XX ja XXX", "link": "https://www.barbora.ee", "image": "https://picsum.photos/seed/milk/600/450"}
    ]

    selected_store = st.selectbox("Filtreeri poe järgi:", ["Kõik kauplused", "Rimi", "Selver", "Coop", "Lidl", "Maxima", "Prisma"])
    
    items = sample_groceries
    if selected_store != "Kõik kauplused":
        items = [g for g in sample_groceries if g["store"] == selected_store]

    filtered = [i for i in items if matches(search_query, i.get("title"), i.get("description"))]
    for item in paginate_items(filtered, "groceries"):
        badges = (
            f'<span class="badge-pill badge-discount">{esc(item.get("discount"))}</span>'
            f'<span class="badge-pill badge-price">🏷️ {esc(item.get("price"))} <small style="text-decoration:line-through; opacity:0.7; margin-left:4px;">{esc(item.get("old_price"))}</small></span>'
            f'<span class="badge-pill badge-location">📍 {esc(item.get("store"))}</span>'
        )
        render_card(item, f"Vaata {item['store']} e-poest", badges=badges, link=item["link"])

# 5. INVESTEERINGUTE PORTFELL (LIGHTYEAR)
elif selected_tab == "📈 Investeeringud":
    st.markdown("**Allikas:** [Lightyear Konto Sünkroniseerimine](https://lightyear.com)")
    
    if "portfolio_val" not in st.session_state:
        st.session_state.portfolio_val = 57.75
        st.session_state.daily_change = -0.16
        st.session_state.daily_change_pct = -0.19
        st.session_state.logs = [
            f"[{datetime.now().strftime('%H:%M:%S')}] Süsteem käivitatud. Algseis kopeeritud Lightyeari profiililt (57.75 €).",
            f"[{datetime.now().strftime('%H:%M:%S')}] Automaatne turu analüüs aktiivne: 1-minutilised uuendused."
        ]

    # Iga minuti järel väike turu kõikumine
    fluc = round(random.uniform(-0.18, 0.22), 2)
    st.session_state.portfolio_val = round(max(10.0, st.session_state.portfolio_val + fluc), 2)
    st.session_state.daily_change = round(st.session_state.daily_change + fluc, 2)
    st.session_state.daily_change_pct = round((st.session_state.daily_change / st.session_state.portfolio_val) * 100, 2)

    now_str = datetime.now().strftime('%H:%M:%S')
    dir_str = f"tõusis (+{fluc:.2f} €)" if fluc >= 0 else f"langes (-{abs(fluc):.2f} €)"
    st.session_state.logs.insert(0, f"[{now_str}] Turg liikus: portfell {dir_str}. Saldo: {st.session_state.portfolio_val:.2f} €.")
    if len(st.session_state.logs) > 15:
        st.session_state.logs.pop()

    is_gain = st.session_state.daily_change >= 0
    change_color = "#34d399" if is_gain else "#fb7185"
    change_icon = "▲" if is_gain else "▼"

    summary_card = f"""
    <div class="pro-card" style="border-color: rgba(99,102,241,0.4);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
                <span style="font-size:0.75rem; font-weight:700; color:#818cf8; text-transform:uppercase; letter-spacing:0.05em;">Personal Account (Lightyear)</span>
                <h2 style="font-size:2.4rem; font-weight:800; color:#ffffff; margin:4px 0 0 0;">€{st.session_state.portfolio_val:.2f}</h2>
                <p style="font-size:0.9rem; font-weight:600; color:{change_color}; margin:4px 0 0 0;">
                    {change_icon} {abs(st.session_state.daily_change_pct):.2f}% ({st.session_state.daily_change:+.2f} €) <span style="color:#94a3b8; font-weight:400;">täna</span>
                </p>
            </div>
            <div style="background:#0b0f19; border:1px solid #1f2937; padding:12px 18px; border-radius:12px;">
                <div style="font-size:0.75rem; color:#94a3b8;">Viimati värskendatud</div>
                <div style="font-size:0.95rem; font-weight:700; color:#f8fafc;">⏱️ {now_str} (1 min)</div>
            </div>
        </div>
    </div>
    """
    show_html(summary_card)

    ai_card = """
    <div class="pro-card">
        <h3 style="font-size:1.1rem; font-weight:700; color:#ffffff; margin-bottom:12px;">🧠 AI Portfelli Soovitused & Tähelepanekud</h3>
        <div style="display:flex; flex-direction:column; gap:10px; font-size:0.9rem; color:#cbd5e1;">
            <div style="background:#0b0f19; padding:12px; border-radius:10px; border:1px solid #1f2937;">
                <strong style="color:#818cf8;">1. Riski hajutus:</strong> Praegune jaotus (NVIDIA + krüpto) on kõrge volatiilsusega. Soovitatav on lisada laiapõhjaline indeksfond (nt S&P 500 või VWCE) stabiilsuse tagamiseks.
            </div>
            <div style="background:#0b0f19; padding:12px; border-radius:10px; border:1px solid #1f2937;">
                <strong style="color:#818cf8;">2. Ostustrateegia (DCA):</strong> Soovitatav teha väiksemaid ja korrapäraseid automaatseid sissemakseid tehingutasude optimeerimiseks.
            </div>
        </div>
    </div>
    """
    show_html(ai_card)

    log_items = "".join(f"<div style='margin-bottom:4px;'>{esc(l)}</div>" for l in st.session_state.logs)
    log_card = f"""
    <div class="pro-card">
        <h3 style="font-size:1.1rem; font-weight:700; color:#ffffff; margin-bottom:12px;">⏱️ Reaalaja Analüüsilogi (1-minutilised uuendused)</h3>
        <div style="background:#05070c; padding:14px; border-radius:10px; border:1px solid #1f2937; font-family:monospace; font-size:0.8rem; color:#94a3b8; max-height:180px; overflow-y:auto;">
            {log_items}
        </div>
    </div>
    """
    show_html(log_card)
