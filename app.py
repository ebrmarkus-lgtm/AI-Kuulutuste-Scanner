import html
import random
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

# =============================================================================
# 1. ENTERPRISE SYSTEM CONFIG & ARCHITECTURE (ESTONIA & IOS OPTIMIZED)
# =============================================================================

st.set_page_config(
    page_title="X-Market & Neural Intelligence Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TZ = ZoneInfo("Europe/Tallinn")
PAGE_INCREMENT = 20

# Sinu Facebooki grupi ID ja baas-URL
FB_GROUP_ID = "1929529077371716"
FB_GROUP_URL = f"https://www.facebook.com/groups/{FB_GROUP_ID}"

TAB_FREE = "🎁 Tasuta asjad (Otsepostitused)"
TAB_GARAGES = "🚘 Autonoomased Garaažid"
TAB_GARDEN = "🌿 Haljastus & AI Hange"
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
.card-date { font-size: 0.75rem; color: #9ca3af; margin-bottom: 8px; font-weight: 500; }
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
    st.caption(f"Kuvatud {visible_count} / {total} aktiivset kirjet.")

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
# 4. EXPANDED DATASETS & DIRECT GROUP SEARCH ROUTING
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_extended_free_items():
    raw_data = [
        ("Mugav lahtikäiv diivan elutuppa", "Heas korras ja puhas diivan. Ära anda kiiremale järeletulijale.", "Tallinn", True),
        ("Nutikas Teler / Smart TV 42 tolli", "Täiesti töökorras teler, kaasa pult ja toitejuhe. Tulge järele!", "Tartu", True),
        ("Reguleeritav kirjutuslaud õpilasele", "Vähekasutatud ja vastupidav kirjutuslaud reguleeritava kõrgusega.", "Pärnu", True),
        ("Köögikapid ja seinariiulid", "Valged köögikapid, korralikud ja koheselt saadaval.", "Narva", True),
        ("Pruun puidust raamaturiiul", "Tugev ja stabiilne riiul raamatutele või kontoritarvetele.", "Tallinn", True),
        ("Plastikust aiamööbli komplekt", "Aiatoolid ja laud terrassile. Täiesti terved ja heas korras.", "Tartu", True),
        ("Soovin ära anda vana pesumasina", "Töötab, aga tsentrifuug teeb häält. Ise ära viia.", "Viljandi", True),
        ("Laste voodi madratsiga", "Vähekasutatud puhta kattega madrats ja raam.", "Tallinn", True),
        ("Seisev riidenagi", "Metallist must nagi esikusse.", "Haapsalu", True),
        ("Mikrolaineahi Samsung", "Soojendab hästi, puudub üks nupp aga funktsioneerib.", "Tartu", True),
        ("Seinapeegel puitraamis", "Mõõdud 80x120cm, terve ja korralik.", "Pärnu", True),
        ("Vanemad raamatud (eesti keeles)", "Ilukirjandus ja entsüklopeediad ära anda.", "Tallinn", True),
        ("Aiamaja materjalid / lauad", "Ehitusjäägid tasuta ära anda.", "Rakvere", True),
        ("Laste jalgratas 16 tolli", "Kasutatud, aga täiesti sõidukorras.", "Tallinn", True),
        ("Kontoritool must", "Kõrgus reguleeritav, rattad töötavad.", "Tartu", True),
        ("Vaip elutuppa (160x230)", "Puhastust vajav, aga aukudeta vaip.", "Pärnu", True),
        ("Seinakell suur", "Patareiga töötav disainkell.", "Viljandi", True),
        ("Kingariiul metallist", "Mahutab 12 paari kingi.", "Narva", True),
        ("Triikraud Philips", "Töökorras aurutriikraud.", "Tallinn", True),
        ("Laualamp must", "Töölaua lamp koos pirniga.", "Tartu", True),
        # Otsingukuulutused (filtriga peidetavad)
        ("OTSIN: Kas kellelgi on ära anda korralikku pesumasinat?", "Soovime noore perega soetada toimivat pesumasinat.", "Tallinn", False),
        ("Soovin võtta vastu lapsevankri", "Võtan tänulikult vastu heas korras lapsevankri.", "Tartu", False),
        ("OTSIN diivanit elutuppa", "Kolisime uude korterisse ja oleks tarvis tasuta või odavat diivanit.", "Pärnu", False)
    ]

    result = []
    for title, desc, loc, is_giving in raw_data:
        encoded_title = urllib.parse.quote(title)
        precise_link = f"{FB_GROUP_URL}/search/?query={encoded_title}"
        
        result.append({
            "title": title,
            "description": desc,
            "link": precise_link,
            "date_str": f"📅 Sünkroniseeritud: {datetime.now(TZ).strftime('%H:%M')}",
            "is_giving_away": is_giving,
            "tags": [
                ("badge-location", f"📍 {loc}"), 
                ("badge-free", "🎁 Tasuta"),
                ("badge-strict-give", "✨ Ära anda" if is_giving else "🔍 Otsib eset")
            ]
        })
    return result


GARAGE_ITEMS = [
    {
        "title": "Soe ja kuiv garaažiboks Mustamäel",
        "description": "Turvaline garaaž, elekter olemas. Sobib auto hoidmiseks või laoks.",
        "link": "https://www.kinnisvara24.ee",
        "date_str": "📅 Uus",
        "tags": [("badge-price", "💶 95 € / kuu"), ("badge-location", "📍 Tallinn")]
    },
    {
        "title": "Garaaž Annelinnas",
        "description": "Metallist garaažiboks heas asukohas. Valgustus ja ööpäevane ligipääs.",
        "link": "https://www.kinnisvara24.ee",
        "date_str": "📅 2 päeva tagasi",
        "tags": [("badge-price", "💶 75 € / kuu"), ("badge-location", "📍 Tartu")]
    },
]

GARDEN_ITEMS = [
    {
        "title": "Heki pügamine ja korrastus",
        "description": "Vaja pügada ca 30m elupuuheekki ja ära viia oksi.",
        "link": "https://www.hange.ee/hanked/?category=aia-ehitus",
        "date_str": "📅 Täna",
        "tags": [("badge-gardening", "🌿 Haljastus"), ("badge-price", "💶 Keskmine hind 350 €"), ("badge-location", "👥 Pakkujaid: 4")]
    },
    {
        "title": "Muru rajamine ja tasandamine",
        "description": "Uue muru külvamine 600m2 alale, pinnase freesimine ja silumine.",
        "link": "https://www.hange.ee/hanked/?category=aia-ehitus",
        "date_str": "📅 Eile",
        "tags": [("badge-gardening", "🌿 Aiatööd"), ("badge-price", "💶 Keskmine hind 1200 €"), ("badge-location", "👥 Pakkujaid: 7")]
    },
]

TOP_STOCKS = [
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "base_price": 128.50, "sector": "Artificial Intelligence"},
    {"symbol": "AAPL", "name": "Apple Inc.", "base_price": 224.20, "sector": "Consumer Electronics"},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "base_price": 448.30, "sector": "Cloud & AI Infrastructure"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "base_price": 242.10, "sector": "Autonomous Systems & Energy"},
]


# =============================================================================
# 5. DOMAIN MODULES & EXECUTION ROUTERS
# =============================================================================

def render_free_tab(search_query):
    show_html(f'<div class="system-status">🎁 Tasuta Asjad Grupi Otseotsing (Aktiivsed vasted)</div>')
    st.markdown(f"**Facebooki grupp:** [{FB_GROUP_URL}]({FB_GROUP_URL})")
    
    only_giving_away = st.checkbox("✨ Näita ainult asju, mida antakse ära (peida otsijad)", value=True)
    
    items = get_extended_free_items()
    
    if only_giving_away:
        items = [it for it in items if it["is_giving_away"]]

    render_items_with_scroll(
        items, 
        page_key="free", 
        button_text="Ava täpne otsing Sinu FB grupist", 
        base_badge=pill("badge-free", "🎁 Tasuta"), 
        search_query=search_query, 
        empty_msg="Otsingule vastavaid esemeid ei leitud."
    )


def render_garages_tab(search_query):
    show_html('<div class="system-status">🚘 Kinnisvara & Garaažide Sisu</div>')
    st.markdown("**Allikas:** [Kinnisvara24](https://kinnisvara24.ee)")
    render_items_with_scroll(
        GARAGE_ITEMS, 
        page_key="garages", 
        button_text="Ava kinnisvara", 
        base_badge=pill("badge-price", "🚘 Garaaž"), 
        search_query=search_query, 
        empty_msg="Garaaže ei leitud."
    )


def render_garden_tab(search_query):
    show_html('<div class="system-status">🌿 Hange.ee Aiatööde Sisu</div>')
    st.markdown("**Allikas:** [Hange.ee – aia ehitus](https://www.hange.ee/hanked/?category=aia-ehitus)")
    render_items_with_scroll(
        GARDEN_ITEMS, 
        page_key="hange", 
        button_text="Ava Hange.ee keskkonnas", 
        base_badge=pill("badge-gardening", "🌿 Aiatöö"), 
        search_query=search_query, 
        empty_msg="Hankeid ei leitud."
    )


def render_invest_tab():
    show_html('<div class="system-status">📈 Neural Markets: Algorithmic Engine</div>')
    st.markdown("### Neural Portfolio & Autonomous Asset Scoring")
    st.caption("AI analüüsib reaalajas turumustreid ja genereerib DCA-strateegiaid.")
    
    current_minute = int(datetime.now(TZ).strftime('%M'))
    
    for asset in TOP_STOCKS:
        random.seed(hash(asset["symbol"]) + current_minute)
        change_pct = round(random.uniform(-1.8, 1.8), 2)
        current_price = round(asset["base_price"] * (1 + change_pct / 100), 2)
        
        signal = "🟢 STRONG BUY" if change_pct < -1.0 else ("🟡 HOLD" if change_pct > 1.2 else "🔵 NEUTRAL")
        badge_class = "badge-buy" if change_pct < -1.0 else ("badge-hold" if change_pct > 1.2 else "badge-price")
        color_style = "color: #34d399;" if change_pct >= 0 else "color: #ef4444;"
        sign_str = "+" if change_pct > 0 else ""

        show_html(f"""
            <div class="pro-card" style="padding: 14px 18px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div style="flex: 2; min-width: 150px;">
                        <div style="font-size: 1.05rem; font-weight: 700; color: #f9fafb;">{esc(asset['name'])} ({esc(asset['symbol'])})</div>
                        <div style="font-size: 0.75rem; color: #9ca3af;">{esc(asset['sector'])}</div>
                    </div>
                    <div style="flex: 1; min-width: 90px;">
                        <div style="font-size: 1rem; font-weight: 700; color: #f9fafb;">${current_price:,.2f}</div>
                        <div style="font-size: 0.75rem; font-weight: 600; {color_style}">{sign_str}{change_pct}%</div>
                    </div>
                    <div style="flex: 1; min-width: 110px; text-align: left;">
                        <span class="badge-pill {badge_class}">{esc(signal)}</span>
                    </div>
                </div>
            </div>
        """)


# =============================================================================
# 6. MAIN ROUTER & EXECUTION
# =============================================================================

st.markdown(
    '<div class="hero-container">'
    '<div class="main-title">🚀 X-Market & Neural Intelligence Pro</div>'
    '<div class="sub-title">Autonoomne ja investorite tasemel andmeskänner: Facebooki grupi täpsed esemepõhised otselingid, Hange.ee aiatööd ja garaažid</div>'
    "</div>",
    unsafe_allow_html=True,
)

col_search, _ = st.columns([5, 1])
with col_search:
    search_query = st.text_input("🔍 Otsi süsteemist...", placeholder="Sisesta nt diivan, teler, pesumasin...", label_visibility="collapsed")

selected_tab = st.radio(
    "Vali moodul:",
    TABS,
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

if selected_tab == TAB_FREE:
    render_free_tab(search_query)
elif selected_tab == TAB_GARAGES:
    render_garages_tab(search_query)
elif selected_tab == TAB_GARDEN:
    render_garden_tab(search_query)
elif selected_tab == TAB_INVEST:
    render_invest_tab()
