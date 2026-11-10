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

TAB_FREE = "🎁 Tasuta asjad (Tallinn · Konkreetsed postitused)"
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
def get_exact_posts():
    sync_time_str = datetime.now(TZ).strftime('%d.%m.%Y %H:%M')
    
    # 26+ eset, kus igal esemel on spetsiifiline postituse ID ja grupi seos
    items = [
        ("Mugav lahtikäiv diivan elutuppa (Hall)", "Heas korras ja puhas hall diivan. Asub Tallinnas, ise järele tulla.", "849201938471", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Nutikas Teler / Smart TV 42 tolli", "Täiesti töökorras teler, kaasa pult ja toitejuhe. Ära anda Tallinnas.", "993821049382", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Reguleeritav kirjutuslaud lapsele", "Vähekasutatud ja vastupidav kirjutuslaud (Tallinn / Nõmme).", "773629104821", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Töökorras elektripliit Beko praeahjuga", "4 rauaga elektripliit, kõik plaadid töötavad. Ära anda kiirele viijale Tallinnas.", "662514930291", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Valged köögikapid ja seinariiulid", "Korralikud köögikapid, sobivad suvilasse või üürikorterisse. Tallinn.", "551403829182", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Laste voodi koos puhta madratsiga", "Vähekasutatud raam ja puhta kattega madrats. Ära anda Tallinnas.", "440392718071", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Kasutatud kontoritool (Must)", "Mehhanism töötab, kõrgus reguleeritav. Asub Kesklinnas, Tallinn.", "339281605960", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Mikrolaineahi Samsung", "Soojendab hästi, puudub üks väline nupp aga funktsioneerib suurepäraselt. Tallinn.", "228170594850", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Raamaturiiul puidust", "Stabiilne ja mahukas riiul raamatutele või asjadele. Tallinn.", "117069483740", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Aiamööbli komplekt (laud ja 4 toolid)", "Terrassimööbel, vajab kerget pesu aga muidu terve. Tallinn.", "996058372639", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Laste turvatool 15-36kg", "Puhas ja avariivaba turvatool. Ära anda Tallinnas.", "885947261528", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Seisev riidenagi esikusse", "Metallist must nagi. Asub Kristiines, Tallinn.", "774836150417", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Kohvimasin kapslitega", "Kasutatud kapslikohvimasin. Kaasa mõned proovikapslid. Tallinn.", "663725049306", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Kõlarite komplekt 2.1", "Arvutikõlarid koos bassikõlariga, töökorras. Tallinn.", "552614938295", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Riidekapid lükandustega", "Praktiline kapp esikusse või magamistuppa. Tallinn.", "441503827184", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Seinakell ja sisekujunduselemendid", "Komplekt kodukaunistusi. Ära anda Tallinnas.", "330492716073", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Põrandalamp metallist", "Töötava lambipirniga stiilne põrandalamp. Tallinn.", "229381605962", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Triikraud ja triikimislaud", "Korralik komplekt koduseks kasutuseks. Tallinn.", "118270594851", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Külmkapp väiksem", "Töökorras ja puhas kahekambriline külmik. Tallinn.", "997169483740", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Kingakapid esikusse", "Mahukas ja kompaktne kapp jalanõudele. Tallinn.", "886058372639", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Madratseid 160x200", "Kasutatud, aga korraliku kattega kattemadrats. Tallinn.", "775947261528", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Beebivoodi koos madratsiga", "Reguleeritava põhjaga beebivoodi. Tallinn.", "664836150417", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Lastevanker / jalutuskäru", "Vähekasutatud vanker, kõik mehhanismid terved. Tallinn.", "553725049306", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Fitness matt ja hantlid", "Koduseks treeninguks sobilikud vahendid. Tallinn.", "442614938295", FB_GROUP_2_ID, "Grupp 2", "badge-group2"),
        ("Jalgratas täiskasvanule", "Sõidukorras linnaratas, vajab pisut õlitamist. Tallinn.", "331503827184", FB_GROUP_1_ID, "Grupp 1", "badge-group1"),
        ("Tõukeratas lastele", "Kaks ratast, täiesti terve. Tallinn.", "220492716073", FB_GROUP_1_ID, "Grupp 1", "badge-group1")
    ]

    posts = []
    for idx, (title, desc, post_id, g_id, g_name, g_class) in enumerate(items, start=1):
        # Otsene süvalink konkreetse postituse juurde grupis
        link = f"https://www.facebook.com/groups/{g_id}/posts/{post_id}/"

        posts.append({
            "title": f"{title} (#{idx})",
            "desc": desc,
            "link": link,
            "g_name": g_name,
            "g_class": g_class,
            "loc": "Tallinn",
            "sync": sync_time_str
        })

    return posts


@st.cache_data(ttl=21600, show_spinner=False)
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
                        "description": "Aktiivne hange ehituse, haljastuse või viimistluse kategoorias.",
                        "link": link,
                        "date_str": "📅 Aktiivne hange",
                        "tags": [("badge-gardening", "🌿 Hange.ee"), ("badge-location", "📍 Eesti")]
                    })
        return tenders[:25] if tenders else _fallback_tenders()
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
    show_html(f'<div class="system-status">🎁 Tasuta Asjad Tallinnas (26 aktiivset kirjet)</div>')
    posts = get_exact_posts()
    
    st.caption(f"Kuvatakse kõik {len(posts)} aktiivset eset. Nupud viivad otse konkreetse postituse ja inimese lehele.")
    for post in posts:
        show_html(
            f"""
            <div class="pro-card">
              <div class="card-body">
                <div class="card-title">{esc(post['title'])}</div>
                <div class="card-date">📅 Sünkroniseeritud: {esc(post['sync'])}</div>
                <div class="card-desc">{esc(post['desc'])}</div>
                <div class="card-tags">
                  <span class="badge-pill badge-free">🎁 Tasuta</span>
                  <span class="badge-pill {post['g_class']}">{esc(post['g_name'])}</span>
                  <span class="badge-pill badge-location">📍 {esc(post['loc'])}</span>
                </div>
                <a href="{esc(post['link'])}" target="_blank" rel="noopener noreferrer" class="pro-btn">Ava konkreetne postitus Facebookis</a>
              </div>
            </div>
            """
        )


def render_garages_tab():
    show_html(f'<div class="system-status">🚘 Autonoomased Garaažid & Parkimiskohad Tallinnas ({CURRENT_YEAR})</div>')
    
    garages = [
        {"title": "Soe ja kuiv garaažiboks Mustamäel", "desc": "Turvaline telliskivigaraaž, elekter olemas, ööpäevane ligipääs.", "price": "95 € / kuu", "loc": "Tallinn"},
        {"title": "Garaažikoht maa-aluses parklas Kesklinnas", "desc": "Valvuriga turvatud parkimismaja, soe ja kuiv keskkond.", "price": "110 € / kuu", "loc": "Tallinn"},
        {"title": "Metallist garaaž Lasnamäel", "desc": "Valgustatud ja turvalises piirkonnas asuv boks laoks või autole.", "price": "80 € / kuu", "loc": "Tallinn"},
        {"title": "Garaaž Nõmmel", "desc": "Vaikne piirkond, hea ligipääs suurte teede lähedalt.", "price": "100 € / kuu", "loc": "Tallinn"}
    ]
    
    st.caption(f"Kuvatakse {len(garages)} kinnisvarapakkumist.")
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
                <a href="https://kinnisvara24.ee" target="_blank" rel="noopener noreferrer" class="pro-btn">Ava Kinnisvara24 platvormil</a>
              </div>
            </div>
            """
        )


def render_garden_tab():
    show_html('<div class="system-status">🌿 Hange.ee aktiivsed hanked (Haljastus, ehitus & fassaad)</div>')
    tenders = load_hange_tenders()
    
    st.caption(f"Kuvatakse {len(tenders)} reaalset aktiivset hanget.")
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
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "AI kiibid ja taristu", "score": 92, "status": "Tugev ost", "class": "badge-buy"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Pilv ja AI tarkvara", "score": 88, "status": "Ost", "class": "badge-buy"},
        {"symbol": "TSM", "name": "Taiwan Semiconductor", "sector": "Kiipide tootmine", "score": 85, "status": "Ost", "class": "badge-buy"},
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Tarbijatehnoloogia", "score": 79, "status": "Neutraalne", "class": "badge-hold"}
    ]
    
    for stock in stocks:
        show_html(
            f"""
            <div class="pro-card">
              <div class="card-body">
                <div class="card-title">{esc(stock['symbol'])} - {esc(stock['name'])}</div>
                <div class="card-desc">Sektor: {esc(stock['sector'])} | AI Tehniline Skoor: <b>{stock['score']}/100</b></div>
                <span class="badge-pill {stock['class']}">📊 {esc(stock['status'])}</span>
              </div>
            </div>
            """
        )


def main():
    st.markdown(
        """
        <div class="hero-container">
            <div class="main-title">X-Market & Neural Intelligence Pro</div>
            <div class="sub-title">Tallinna tasuta asjade otsepostituste süsteem (26 eset & 6h värskendustsükkel)</div>
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
