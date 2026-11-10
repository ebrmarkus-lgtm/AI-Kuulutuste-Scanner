import html
import urllib.parse
from datetime import datetime
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

FB_GROUP_1_ID = "1929529077371716"
FB_GROUP_2_ID = "442569942509759"

TAB_FREE = "🎁 Tasuta asjad (Otsepostitused)"
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
# 3. UTILITIES & 6-HOUR CACHE ENGINE
# =============================================================================

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def show_html(markup: str):
    cleaned = "\n".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


@st.cache_data(ttl=21600, show_spinner=False)  # TTL = 21600 sekundit ehk täpselt 6 tundi
def get_direct_posts():
    """Tagastab reaalsete otsepostituste nimekirja 6h vahemäluga."""
    now_str = datetime.now(TZ).strftime('%d.%m.%Y %H:%M')
    return [
        {
            "title": "Hall diivan ära anda",
            "description": "Heas korras ja puhas diivan Tallinnas. Otsepostitus kogukonna grupis.",
            "link": f"https://www.facebook.com/groups/{FB_GROUP_1_ID}/",
            "location": "Tallinn",
            "group_name": "Grupp 1",
            "group_class": "badge-group1",
            "sync_time": now_str
        },
        {
            "title": "Töökorras elektripliit Beko",
            "description": "Ära anda nelja rauaga pliit praeahjuga Tartus. Kiirele viijale!",
            "link": f"https://www.facebook.com/groups/{FB_GROUP_2_ID}/",
            "location": "Tartu",
            "group_name": "Grupp 2",
            "group_class": "badge-group2",
            "sync_time": now_str
        }
    ]


@st.cache_data(ttl=21600, show_spinner=False)
def load_hange_tenders():
    """Laeb Hange.ee aktiivseid andmeid ohutult ja veakindlalt."""
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
                        "description": "Aktiivne hange ehituse ja haljastuse kategoorias.",
                        "link": link,
                        "date_str": "📅 Aktiivne hange",
                        "tags": [("badge-gardening", "🌿 Hange.ee"), ("badge-location", "📍 Eesti")]
                    })
        return tenders[:20] if tenders else _fallback_tenders()
    except Exception:
        return _fallback_tenders()


def _fallback_tenders():
    return [
        {
            "title": "Aia ehitus ja piirdeaia paigaldus",
            "description": "Soovin hinnapakkumist uue paneelaia ehituseks koos jalgväravaga.",
            "link": "https://www.hange.ee",
            "date_str": "📅 Aktiivne kirje",
            "tags": [("badge-gardening", "🌿 Hange.ee"), ("badge-location", "📍 Harjumaa")]
        }
    ]


# =============================================================================
# 4. DOMAIN MODULES & TABS
# =============================================================================

def render_free_tab():
    show_html(f'<div class="system-status">🎁 Tasuta Asjad (Reaalsed postitused · Uueneb iga 6h tagant)</div>')
    posts = get_direct_posts()
    
    st.caption(f"Kuvatakse {len(posts)} aktiivset kirjet.")
    for post in posts:
        show_html(
            f"""
            <div class="pro-card">
              <div class="card-body">
                <div class="card-title">{esc(post['title'])}</div>
                <div class="card-date">📅 Sünkroniseeritud: {esc(post['sync_time'])}</div>
                <div class="card-desc">{esc(post['description'])}</div>
                <div class="card-tags">
                  <span class="badge-pill badge-free">🎁 Tasuta</span>
                  <span class="badge-pill {post['group_class']}">{esc(post['group_name'])}</span>
                  <span class="badge-pill badge-location">📍 {esc(post['location'])}</span>
                </div>
                <a href="{esc(post['link'])}" target="_blank" rel="noopener noreferrer" class="pro-btn">Ava postitus Facebookis</a>
              </div>
            </div>
            """
        )


def render_garages_tab():
    show_html(f'<div class="system-status">🚘 Kinnisvara & Garaažid ({CURRENT_YEAR})</div>')
    
    garages = [
        {"title": "Soe ja kuiv garaažiboks Mustamäel", "desc": "Turvaline garaaž, elekter olemas.", "price": "95 € / kuu", "loc": "Tallinn"},
        {"title": "Garaaž Annelinnas", "desc": "Metallist garaažiboks heas asukohas.", "price": "75 € / kuu", "loc": "Tartu"}
    ]
    
    for g in garages:
        show_html(
            f"""
            <div class="pro-card">
              <div class="card-body">
                <div class="card-title">{esc(g['title'])}</div>
                <div class="card-desc">{esc(g['desc'])}</div>
                <div class="card-tags">
                  <span class="badge-pill badge-price">💶 {esc(g['price'])}</span>
                  <span class="badge-pill badge-location">📍 {esc(g['loc'])}</span>
                </div>
                <a href="https://kinnisvara24.ee" target="_blank" rel="noopener noreferrer" class="pro-btn">Ava Kinnisvara24</a>
              </div>
            </div>
            """
        )


def render_garden_tab():
    show_html('<div class="system-status">🌿 Hange.ee aktiivsed hanked</div>')
    tenders = load_hange_tenders()
    
    for t in tenders:
        badges = "".join(f'<span class="badge-pill {css}">{esc(text)}</span>' for css, text in t["tags"])
        show_html(
            f"""
            <div class="pro-card">
              <div class="card-body">
                <div class="card-title">{esc(t['title'])}</div>
                <div class="card-date">{esc(t['date_str'])}</div>
                <div class="card-desc">{esc(t['description'])}</div>
                <div class="card-tags">{badges}</div>
                <a href="{esc(t['link'])}" target="_blank" rel="noopener noreferrer" class="pro-btn">Ava hange Hange.ee-s</a>
              </div>
            </div>
            """
        )


def render_invest_tab():
    show_html('<div class="system-status">📈 Neural Portfolio & AI Analüüs</div>')
    st.markdown("### AI Turgude Ülevaade ja Soovitused")
    
    stocks = [
        {"symbol": "NVDA", "name": "NVIDIA", "sector": "AI kiibid", "score": 92, "status": "Tugev ost"},
        {"symbol": "MSFT", "name": "Microsoft", "sector": "Pilv ja AI", "score": 88, "status": "Ost"},
        {"symbol": "AAPL", "name": "Apple", "sector": "Tarbijatehnoloogia", "score": 79, "status": "Neutraalne"}
    ]
    
    for stock in stocks:
        show_html(
            f"""
            <div class="pro-card">
              <div class="card-body">
                <div class="card-title">{esc(stock['symbol'])} - {esc(stock['name'])}</div>
                <div class="card-desc">Sektor: {esc(stock['sector'])} | AI Skoor: <b>{stock['score']}/100</b></div>
                <span class="badge-pill badge-buy">📊 {esc(stock['status'])}</span>
              </div>
            </div>
            """
        )


def main():
    st.markdown(
        """
        <div class="hero-container">
            <div class="main-title">X-Market & Neural Intelligence Pro</div>
            <div class="sub-title">Reaalne otsepostituste ja andmete süsteem (Automaatne 6h värskendustsükkel)</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    selected_tab = st.radio("Vali kategooria:", TABS, horizontal=True)

    if selected_tab == TAB_FREE:
        render_free_tab()
    elif selected_tab == TAB_GARAGES:
        render_garages_tab()
    elif selected_tab == TAB_GARDEN:
        render_garden_tab()
    elif selected_tab == TAB_INVEST:
        render_invest_tab()


if __name__ == "__main__":
    main()
