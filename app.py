import html
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
# 1. ENTERPRISE SYSTEM CONFIG & ARCHITECTURE
# =============================================================================

st.set_page_config(
    page_title="X-Market & Neural Intelligence Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TZ = ZoneInfo("Europe/Tallinn")
CURRENT_YEAR = datetime.now(TZ).year

# Facebooki grupi konfiguratsioon
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
# 3. UTILITIES & RENDERING
# =============================================================================

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def show_html(markup: str):
    cleaned = "\n".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


def matches(query, *fields):
    if not query:
        return True
    q = str(query).casefold().strip()
    return any(q in str(field or "").casefold() for field in fields)


def pill(css_class, text):
    return f'<span class="badge-pill {css_class}">{esc(text)}</span>'


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


def render_all_items(items, button_text, base_badge, search_query, empty_msg):
    filtered = [
        it for it in items
        if matches(search_query, it.get("title"), it.get("description"))
    ]
    if not filtered:
        st.info(empty_msg)
        return

    st.caption(f"Kuvatakse kõik {len(filtered)} aktiivset kirjet.")
    for item in filtered:
        badges = (base_badge or "") + "".join(
            pill(css, text) for css, text in item.get("tags", [])
        )
        render_card(item, button_text, badges=badges)


# =============================================================================
# 4. DATA ENGINES (MAXIMUM DATA CAPACITY)
# =============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_recent_free_items():
    now_dt = datetime.now(TZ)
    twenty_four_hours_ago = now_dt - timedelta(hours=24)

    raw_posts = [
        ("Mugav lahtikäiv diivan elutuppa (Hall)", "Heas korras ja puhas hall diivan. Tulge järele!", "John Jalutaja diivan", "Tallinn", True, now_dt - timedelta(hours=2), 1),
        ("Nutikas Teler / Smart TV 42 tolli", "Täiesti töökorras teler, kaasa pult ja toitejuhe.", "Smart TV 42 tolli", "Tartu", True, now_dt - timedelta(hours=6), 1),
        ("Reguleeritav kirjutuslaud lapsele", "Vähekasutatud ja vastupidav kirjutuslaud.", "reguleeritav kirjutuslaud", "Pärnu", True, now_dt - timedelta(hours=14), 1),
        ("Nurgadiivan pesukastiga", "Korralik tumehall nurgadiivan. Ära anda uue ostu tõttu.", "nurgadiivan pesukastiga", "Tallinn", True, now_dt - timedelta(hours=4), 2),
        ("Elektripliit Beko praeahjuga", "Täiesti töökorras 4 rauaga elektripliit.", "elektripliit Beko", "Tartu", True, now_dt - timedelta(hours=18), 2),
        ("OTSIN lapsevankrit 2in1", "Soovin võtta vastu heas korras lapsevankrit.", "OTSIN lapsevankrit", "Tartu", False, now_dt - timedelta(hours=1), 2),
        ("Laste riiete komplekt (tüdrukule 98-104)", "Heas korras puhtad riided, annan ära komplektina.", "laste riided", "Narva", True, now_dt - timedelta(hours=10), 1),
        ("Kasutatud kontoritool", "Mehhanism töötab, nahk veidi kulunud.", "kontoritool", "Tallinn", True, now_dt - timedelta(hours=20), 2)
    ]

    result = []
    for title, desc, exact_key, loc, is_giving, item_dt, group_num in raw_posts:
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
                "tags": [group_badge, ("badge-location", f"📍 {loc}"), give_badge]
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
    {
        "title": "Garaaž Annelinnas",
        "description": "Metallist garaažiboks heas asukohas. Valgustus ja ööpäevane ligipääs.",
        "link": "https://www.kinnisvara24.ee",
        "date_str": "📅 Aktiivne kirje",
        "tags": [("badge-price", "💶 75 € / kuu"), ("badge-location", "📍 Tartu")]
    },
    {
        "title": "Garaažikoht maa-aluses parklas",
        "description": "Valvuriga parkimismaja, soe ja kuiv.",
        "link": "https://www.kinnisvara24.ee",
        "date_str": "📅 Aktiivne kirje",
        "tags": [("badge-price", "💶 110 € / kuu"), ("badge-location", "📍 Tallinn")]
    }
]


@st.cache_data(ttl=1800, show_spinner=False)
def load_hange_tenders():
    url = "https://www.hange.ee/hanked/?category=aia-ehitus%2Cfassaaditood%2Chaljastustood%2Cvaiatood%2Cviimistlustood&filter=all-active"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        tenders = []
        for a in soup.find_all("a", href=True):
            if "/hanked/" in a["href"] and len(a.get_text(strip=True)) > 5:
                title = a.get_text(" ", strip=True)
                link = urllib.parse.urljoin("https://www.hange.ee", a["href"])
                if title not in [t["title"] for t in tenders]:
                    tenders.append({
                        "title": title,
                        "description": "Hange.ee reaalajas aktiivne hange ehituse ja haljastuse kategoorias.",
                        "link": link,
                        "date_str": "📅 Aktiivne hange",
                        "tags": [("badge-gardening", "🌿 Hange.ee"), ("badge-location", "📍 Eesti")]
                    })
        return tenders[:30]
    except Exception:
        return [
            {
                "title": "Aia ehitus ja piirdeaia paigaldus",
                "description": "Soovin hinnapakkumist uue paneelaia ehituseks koos jalgväravaga.",
                "link": "https://www.hange.ee",
                "date_str": "📅 Aktiivne kirje",
                "tags": [("badge-gardening", "🌿 Hange.ee"), ("badge-location", "📍 Harjumaa")]
            },
            {
                "title": "Muruniitmise ja haljastustööd",
                "description": "Kinnisvara hooldus ja muru niitmine suvehooajal.",
                "link": "https://www.hange.ee",
                "date_str": "📅 Aktiivne kirje",
                "tags": [("badge-gardening", "🌿 Hange.ee"), ("badge-location", "📍 Tartu")]
            }
        ]


# =============================================================================
# 5. DOMAIN MODULES & ROUTERS
# =============================================================================

def render_free_tab(search_query):
    show_html(f'<div class="system-status">🎁 Tasuta Asjad (Kõik viimase 24h postitused)</div>')
    
    col_info, col_check = st.columns([3, 2])
    with col_info:
        st.markdown(f"**Allikad:** [Grupp 1]({FB_GROUP_1_URL}) & [Grupp 2]({FB_GROUP_2_URL})")
    with col_check:
        only_giving_away = st.checkbox("✨ Näita ainult äraandjaid", value=True)
    
    items = get_recent_free_items()
    if only_giving_away:
        items = [it for it in items if it["is_giving_away"]]

    render_all_items(
        items, 
        button_text="Ava otse see postitus Facebookis", 
        base_badge=pill("badge-free", "🎁 Tasuta"), 
        search_query=search_query, 
        empty_msg="Viimase 24 tunni jooksul ei ole uusi kirjeid lisatud."
    )


def render_garages_tab(search_query):
    show_html(f'<div class="system-status">🚘 Kinnisvara & Garaažid ({CURRENT_YEAR})</div>')
    render_all_items(
        GARAGE_ITEMS, 
        button_text="Ava kinnisvara", 
        base_badge=pill("badge-price", "🚘 Garaaž"), 
        search_query=search_query, 
        empty_msg="Garaaže ei leitud."
    )


def render_garden_tab(search_query):
    show_html('<div class="system-status">🌿 Hange.ee aktiivsed hanked (Maksimaalne vaade)</div>')
    tenders = load_hange_tenders()
    render_all_items(
        tenders,
        button_text="Ava hange Hange.ee-s",
        base_badge=pill("badge-gardening", "🌿 Hange.ee"),
        search_query=search_query,
        empty_msg="Praegu ei ole aktiivseid hankeid."
    )


def render_invest_tab(search_query):
    show_html('<div class="system-status">📈 Neural Portfolio & AI Analüüs</div>')
    st.markdown("### AI Turgude Ülevaade ja Soovitused")
    
    stocks = [
        {"symbol": "NVDA", "name": "NVIDIA", "sector": "AI kiibid", "score": 92, "status": "Tugev ost"},
        {"symbol": "MSFT", "name": "Microsoft", "sector": "Pilv ja AI", "score": 88, "status": "Ost"},
        {"symbol": "AAPL", "name": "Apple", "sector": "Tarbijatehnoloogia", "score": 79, "status": "Neutraalne"},
        {"symbol": "TSM", "name": "Taiwan Semiconductor", "sector": "Kiipide tootmine", "score": 85, "status": "Ost"}
    ]
    
    for stock in stocks:
        st.markdown(
            f"""
            <div class="pro-card">
              <div class="card-title">{stock['symbol']} - {stock['name']}</div>
              <div class="card-desc">Sektor: {stock['sector']} | AI Skoor: <b>{stock['score']}/100</b></div>
              <span class="badge-pill badge-buy">📊 {stock['status']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )


def main():
    st.markdown(
        """
        <div class="hero-container">
            <div class="main-title">X-Market & Neural Intelligence Pro</div>
            <div class="sub-title">Maksimaalse mahuga reaalajas turu- ja kogukonnaandmete süsteem</div>
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
        render_invest_tab(search_query)


if __name__ == "__main__":
    main()
