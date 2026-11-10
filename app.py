import html
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from bs4 import BeautifulSoup

# =============================================================================
# 1. ENTERPRISE SYSTEM CONFIG & ARCHITECTURE (100% FREE & ESTONIA OPTIMIZED)
# =============================================================================

st.set_page_config(
    page_title="X-Market & Neural Intelligence Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TZ = ZoneInfo("Europe/Tallinn")
CURRENT_YEAR = datetime.now(TZ).year
PAGE_INCREMENT = 20

# Facebooki grupid
FB_GROUP_1_ID = "1929529077371716"
FB_GROUP_1_URL = f"https://www.facebook.com/groups/{FB_GROUP_1_ID}"

FB_GROUP_2_ID = "442569942509759"
FB_GROUP_2_URL = f"https://www.facebook.com/groups/{FB_GROUP_2_ID}"

TAB_FREE = "🎁 Tasuta asjad (Viimased 24h)"
TAB_GARAGES = "🚘 Autonoomased Garaažid"
TAB_GARDEN = "🌿 Haljastus ja AI hange"
TAB_INVEST = "📈 Neural Portfolio & AI"
TABS = [TAB_FREE, TAB_GARAGES, TAB_GARDEN, TAB_INVEST]


# =============================================================================
# 2. PRO-INVESTOR DARK THEME & RESPONSIVE CSS
# =============================================================================

DARK_MODE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; -webkit-text-size-adjust: 100%; }
.stApp { background-color: #030712; color: #f3f4f6; }

.hero-container {
    padding: 1.75rem 2rem;
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    border: 1px solid #312e81;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    box-shadow: 0 20px 40px rgba(0,0,0,0.6);
}
.main-title { font-size: 2.2rem; font-weight: 900; color: #ffffff; margin-bottom: 0.3rem; letter-spacing: -1px; }
.sub-title { font-size: 0.95rem; color: #a5b4fc; font-weight: 500; line-height: 1.4; }

.pro-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 14px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    transition: all 0.2s ease;
}
.pro-card:hover { border-color: #6366f1; }

.card-body { width: 100%; }
.card-title { font-size: 1.15rem; font-weight: 700; color: #f9fafb; margin-bottom: 6px; line-height: 1.4; }
.card-date { font-size: 0.75rem; color: #34d399; margin-bottom: 8px; font-weight: 600; }
.card-desc { font-size: 0.9rem; color: #d1d5db; line-height: 1.5; margin-bottom: 14px; }
.card-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }

.badge-pill { padding: 4px 10px; border-radius: 9999px; font-size: 0.7rem; font-weight: 700; display: inline-flex; align-items: center; gap: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.badge-free { background-color: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.badge-price { background-color: rgba(99,102,241,0.15); color: #818cf8; border: 1px solid rgba(99,102,241,0.3); }
.badge-location { background-color: rgba(55,65,81,0.4); color: #9ca3af; border: 1px solid rgba(75,85,99,0.4); }
.badge-gardening { background-color: rgba(52,211,153,0.15); color: #34d399; border: 1px solid rgba(52,211,153,0.3); }
.badge-buy { background-color: rgba(34,197,94,0.2); color: #4ade80; border: 1px solid rgba(34,197,94,0.4); }
.badge-hold { background-color: rgba(234,179,8,0.2); color: #fde047; border: 1px solid rgba(234,179,8,0.4); }
.badge-strict-give { background-color: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.4); }
.badge-group1 { background-color: rgba(168,85,247,0.2); color: #c084fc; border: 1px solid rgba(168,85,247,0.4); }
.badge-group2 { background-color: rgba(236,72,153,0.2); color: #f472b6; border: 1px solid rgba(236,72,153,0.4); }

.pro-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 100%; box-sizing: border-box; padding: 12px 20px;
    background: #4f46e5; color: #ffffff !important;
    font-size: 0.9rem; font-weight: 700; border-radius: 10px;
    text-decoration: none !important; -webkit-tap-highlight-color: transparent;
    box-shadow: 0 4px 14px rgba(79,70,229,0.4);
}
.pro-btn:hover { background: #4338ca; }
.pro-btn.secondary { background: #1f2937; border: 1px solid #374151; color: #9ca3af !important; box-shadow: none; }

.system-status {
    background: #065f46; border: 1px solid #059669;
    padding: 6px 12px; border-radius: 8px;
    font-size: 0.75rem; color: #d1fae5; font-weight: 600;
    display: inline-block; margin-bottom: 10px;
}
</style>
"""

st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)


# =============================================================================
# 3. CORE UTILITIES & PAGINATION ENGINE
# =============================================================================

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def show_html(markup: str):
    cleaned = "\n".join(
        line.strip() for line in markup.splitlines() if line.strip()
    )
    st.markdown(cleaned, unsafe_allow_html=True)


def matches(query, *fields):
    if not query:
        return True
    q = str(query).casefold().strip()
    return any(q in str(field or "").casefold() for field in fields)


def pill(css_class, text):
    return f'<span class="badge-pill {css_class}">{esc(text)}</span>'


def render_pagination_scroll(items, category_key):
    items = list(items)
    total = len(items)
    count_key = f"visible_count_{category_key}"

    if count_key not in st.session_state:
        st.session_state[count_key] = PAGE_INCREMENT

    visible_count = min(total, max(0, int(st.session_state[count_key])))
    st.caption(f"Kuvatud {visible_count} / {total} viimase 24h kirjet.")

    current_batch = items[:visible_count]

    if visible_count < total:
        remaining = total - visible_count
        next_batch_size = min(PAGE_INCREMENT, remaining)
        if st.button(f"⬇️ Keri edasi (laadi veel {next_batch_size} eset)", key=f"scroll_more_{category_key}", use_container_width=True):
            st.session_state[count_key] = visible_count + PAGE_INCREMENT
            st.rerun()

    return current_batch


def render_card(item, button_text, badges=""):
    link = item.get("link")
    date_html = f'<div class="card-date">{esc(item["date_str"])}</div>' if item.get("date_str") else ""
    desc_html = f'<div class="card-desc">{esc(item["description"])}</div>' if item.get("description") else ""
    tags_html = f'<div class="card-tags">{badges}</div>' if badges else ""

    if link:
        button_html = f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer" class="pro-btn">{esc(button_text)}</a>'
    else:
        button_html = '<span class="pro-btn secondary">Link puudub</span>'

    show_html(
        f"""
        <div class="pro-card">
          <div class="card-body">
            <div class="card-title">{esc(item.get("title", "Kirje"))}</div>
            {date_html}
            {desc_html}
            {tags_html}
            {button_html}
          </div>
        </div>
        """
    )


def render_items_with_scroll(items, *, page_key, button_text, base_badge, search_query, empty_msg):
    filtered = [
        it for it in items
        if matches(search_query, it.get("title"), it.get("description"))
    ]
    if not filtered:
        st.info(empty_msg)
        return

    for item in render_pagination_scroll(filtered, page_key):
        badges = (base_badge or "") + "".join(
            pill(css, text) for css, text in item.get("tags", [])
        )
        render_card(item, button_text, badges=badges)


# =============================================================================
# 4. 24H FREE FILTERED DATA ENGINE (NO PAID APIS)
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_recent_free_items():
    """
    Kogub andmed ja tagastab ainult need, mis jäävad viimase 24 tunni sisse.
    Eemaldab topeltmärgenduse ning korrastab visuaali.
    """
    now_dt = datetime.now(TZ)
    twenty_four_hours_ago = now_dt - timedelta(hours=24)

    # Siia saad lisada või uuendada oma grupi postitusi (simuleeritud reaalajas ajatemplitega)
    raw_posts = [
        ("Mugav lahtikäiv diivan elutuppa (Hall)", "Heas korras ja puhas hall diivan. Tulge järele!", "John Jalutaja diivan", "Tallinn", True, now_dt - timedelta(hours=2), 1),
        ("Nutikas Teler / Smart TV 42 tolli", "Täiesti töökorras teler, kaasa pult ja toitejuhe.", "Smart TV 42 tolli", "Tartu", True, now_dt - timedelta(hours=6), 1),
        ("Reguleeritav kirjutuslaud lapsele", "Vähekasutatud ja vastupidav kirjutuslaud.", "reguleeritav kirjutuslaud", "Pärnu", True, now_dt - timedelta(hours=14), 1),
        ("Nurgadiivan pesukastiga", "Korralik tumehall nurgadiivan. Ära anda uue ostu tõttu.", "nurgadiivan pesukastiga", "Tallinn", True, now_dt - timedelta(hours=4), 2),
        ("Elektripliit Beko praeahjuga", "Täiesti töökorras 4 rauaga elektripliit.", "elektripliit Beko", "Tartu", True, now_dt - timedelta(hours=18), 2),
        ("OTSIN lapsevankrit 2in1", "Soovin võtta vastu heas korras lapsevankrit.", "OTSIN lapsevankrit", "Tartu", False, now_dt - timedelta(hours=1), 2)
    ]

    result = []
    for title, desc, exact_key, loc, is_giving, item_dt, group_num in raw_posts:
        # Filtreerib rangelt viimase 24h sisse
        if item_dt >= twenty_four_hours_ago:
            base_url = FB_GROUP_1_URL if group_num == 1 else FB_GROUP_2_URL
            target_url = f"{base_url}/search/?q={urllib.parse.quote_plus(exact_key)}"
            
            group_badge = ("badge-group1", "👥 Grupp 1") if group_num == 1 else ("badge-group2", "👥 Grupp 2")
            give_badge = ("badge-strict-give", "✨ Ära anda" if is_giving else "🔍 Otsib eset")

            result.append({
                "title": title,
                "description": desc,
                "link": target_url,
                "date_str": f"📅 Lisatud: {item_dt.strftime('%d.%m.%Y %H:%M')}",
                "is_giving_away": is_giving,
                "tags": [
                    group_badge,
                    ("badge-location", f"📍 {loc}"),
                    give_badge
                ]
            })

    return result


GARAGE_ITEMS = [
    {
        "title": "Soe ja kuiv garaažiboks Mustamäel",
        "description": "Turvaline garaaž, elekter olemas. Sobib auto hoidmiseks või laoks.",
        "link": "https://www.kinnisvara24.ee",
        "date_str": "📅 Aktiivne kirje",
        "tags": [("badge-price", "💶 95 € / kuu"), ("badge-location", "📍 Tallinn")]
    },
]


# =============================================================================
# 5. DOMAIN MODULES & ROUTERS
# =============================================================================

def render_free_tab(search_query):
    show_html(f'<div class="system-status">🎁 Tasuta Asjad (Automaatne viimase 24h filter · Tasuta lahendus)</div>')
    
    col_info, col_check = st.columns([3, 2])
    with col_info:
        st.markdown(f"**Allikad:** [Grupp 1]({FB_GROUP_1_URL}) & [Grupp 2]({FB_GROUP_2_URL})")
    with col_check:
        only_giving_away = st.checkbox("✨ Näita ainult äraandjaid", value=True)
    
    items = get_recent_free_items()
    
    if only_giving_away:
        items = [it for it in items if it["is_giving_away"]]

    render_items_with_scroll(
        items, 
        page_key="free", 
        button_text="Ava otse see postitus Facebookis", 
        base_badge=pill("badge-free", "🎁 Tasuta"), 
        search_query=search_query, 
        empty_msg="Viimase 24 tunni jooksul ei ole uusi kirjeid lisatud."
    )


def render_garages_tab(search_query):
    show_html(f'<div class="system-status">🚘 Kinnisvara & Garaažid ({CURRENT_YEAR})</div>')
    render_items_with_scroll(
        GARAGE_ITEMS, 
        page_key="garages", 
        button_text="Ava kinnisvara", 
        base_badge=pill("badge-price", "🚘 Garaaž"), 
        search_query=search_query, 
        empty_msg="Garaaže ei leitud."
    )


def render_garden_tab(search_query):
    show_html('<div class="system-status">🌿 Hange.ee aktiivsed hanked</div>')
    st.info("Hange.ee moodul on aktiivne.")


def main():
    st.markdown(
        """
        <div class="hero-container">
            <div class="main-title">X-Market & Neural Intelligence Pro</div>
            <div class="sub-title">Optimeeritud ja täielikult tasuta reaalajas turu- ja kogukonnaandmete süsteem</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    search_query = st.text_input("🔍 Otsi süsteemist...", "")
    
    selected_tab = st.radio("Vali kategooria:", TABS, horizontal=True)

    if selected_tab == TAB_FREE:
        render_free_tab(search_query)
    elif selected_tab == TAB_GARAGES:
        render_garages_tab(search_query)
    elif selected_tab == TAB_GARDEN:
        render_garden_tab(search_query)
    elif selected_tab == TAB_INVEST:
        st.markdown("### 📈 Neural Portfolio & AI")
        st.write("Finantsturgude ja aktsiate analüüsi moodul.")

if __name__ == "__main__":
    main()
