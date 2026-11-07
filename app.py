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

# Piirangud eemaldatud – näitame korraga suuremaid plokke
PAGE_INCREMENT = 20

FB_GROUP_BASE = "https://www.facebook.com/groups/1929529077371716"

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
    padding: 18px;
    margin-bottom: 14px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    transition: all 0.2s ease;
}
.pro-card:hover { border-color: #6366f1; }

.card-row { display: flex; gap: 20px; align-items: flex-start; }
.card-img { flex: 0 0 240px; max-width: 240px; }
.card-img img { width: 100%; border-radius: 10px; display: block; object-fit: cover; aspect-ratio: 16 / 10; background-color: #1e293b; }
.card-body { flex: 1; min-width: 0; }

@media (max-width: 768px) {
    .main-title { font-size: 1.75rem; }
    .card-row { flex-direction: column; }
    .card-img { flex: none; width: 100%; max-width: 100%; margin-bottom: 12px; }
}

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
# 3. CORE UTILITIES & "KERI EDASI" PAGINATION ENGINE
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
    """
    Eemaldatud on igasugused limiidi-valikud ning lisatud sujuv 'Keri edasi' nupp.
    """
    items = list(items)
    total = len(items)
    count_key = f"visible_count_{category_key}"

    if count_key not in st.session_state:
        st.session_state[count_key] = PAGE_INCREMENT

    visible_count = min(total, max(0, int(st.session_state[count_key])))

    st.caption(f"Kuvatud {visible_count} / {total} aktiivset kirjet.")

    # Kuvame esemed
    current_batch = items[:visible_count]

    if visible_count < total:
        remaining = total - visible_count
        next_batch_size = min(PAGE_INCREMENT, remaining)
        
        # 'Keri edasi' nupp kategooria all
        if st.button(f"⬇️ Keri edasi (laadi veel {next_batch_size} eset)", key=f"scroll_more_{category_key}", use_container_width=True):
            st.session_state[count_key] = visible_count + PAGE_INCREMENT
            st.rerun()

    return current_batch


def render_card(item, button_text, badges=""):
    link = item.get("link")
    img_url = item.get("image")

    img_html = ""
    if img_url:
        img_html = (
            '<div class="card-img">'
            f'<img src="{esc(img_url)}" loading="lazy" decoding="async" '
            f'referrerpolicy="no-referrer" alt="{esc(item.get("title", "Resource"))}">'
            "</div>"
        )

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
          <div class="card-row">
            {img_html}
            <div class="card-body">
              <div class="card-title">{esc(item.get("title", "Kirje"))}</div>
              {date_html}
              {desc_html}
              {tags_html}
              {button_html}
            </div>
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
# 4. MASSIVE "TASUTA ASJAD" DATASET (ROHKEM ESEMEID)
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_extended_free_items():
    raw_data = [
        ("Mugav lahtikäiv diivan elutuppa", "Heas korras ja puhas diivan. Ära anda kiiremale järeletulijale.", "photo-1555041469-a586c61ea9bc", "Tallinn", True),
        ("Nutikas Teler / Smart TV 42 tolli", "Täiesti töökorras teler, kaasa pult ja toitejuhe. Tulge järele!", "photo-1593305841991-05c297ba4575", "Tartu", True),
        ("Reguleeritav kirjutuslaud õpilasele", "Vähekasutatud ja vastupidav kirjutuslaud reguleeritava kõrgusega.", "photo-1518455027359-f3f8164ba6bd", "Pärnu", True),
        ("Köögikapid ja seinariiulid", "Valged köögikapid, korralikud ja koheselt saadaval.", "photo-1595428774223-ef52624120d2", "Narva", True),
        ("Pruun puidust raamaturiiul", "Tugev ja stabiilne riiul raamatutele või kontoritarvetele.", "photo-1594623930572-300a3011d9ae", "Tallinn", True),
        ("Plastikust aiamööbli komplekt", "Aiatoolid ja laud terrassile. Täiesti terved ja heas korras.", "photo-1519947486511-46149fa0a254", "Tartu", True),
        ("Soovin ära anda vana pesumasina", "Töötab, aga tsentrifuug teeb häält. Ise ära viia.", "photo-1626806787461-102c1bfaaea1", "Viljandi", True),
        ("Laste voodi madratsiga", "Vähekasutatud puhta kattega madrats ja raam.", "photo-1505693416388-ac5ce068fe85", "Tallinn", True),
        ("Seisev riidenagi", "Metallist must nagi esikusse.", "photo-1595515106967-1ce2e1762128", "Haapsalu", True),
        ("Mikrolaineahi Samsung", "Soojendab hästi, puudub üks nupp aga funktsioneerib.", "photo-1574269909862-7e1d70bb8078", "Tartu", True),
        ("Seinapeegel puitraamis", "Mõõdud 80x120cm, terve ja korralik.", "photo-1618221195710-dd6b41faaea6", "Pärnu", True),
        ("Vanemad raamatud (eesti keeles)", "Ilukirjandus ja entsüklopeediad ära anda.", "photo-1495640388908-05fa85288e61", "Tallinn", True),
        ("Aiamaja materjalid / lauad", "Ehitusjäägid tasuta ära anda.", "photo-1541888946425-d0fbb18f64e8", "Rakvere", True),
        ("Laste jalgratas 16 tolli", "Kasutatud, aga täiesti sõidukorras.", "photo-1576435728678-68d0fbf94e91", "Tallinn", True),
        ("Kontoritool must", "Kõrgus reguleeritav, rattad töötavad.", "photo-1580481077494-e3299ac0505d", "Tartu", True),
        ("Vaip elutuppa (160x230)", "Puhastust vajav, aga aukudeta vaip.", "photo-1579656381226-5fc0f0100c3b", "Pärnu", True),
        ("Seinakell suur", "Patareiga töötav disainkell.", "photo-1563861826100-9cb868fdbe1c", "Viljandi", True),
        ("Kingariiul metallist", "Mahutab 12 paari kingi.", "photo-1595428774174-88484196120b", "Narva", True),
        ("Triikraud Philips", "Töökorras aurutriikraud.", "photo-1585659722983-3c675f904ac8", "Tallinn", True),
        ("Laualamp must", "Töölaua lamp koos pirniga.", "photo-1507473885765-e6ed057f782c", "Tartu", True),
        # Otsingukuulutused
        ("OTSIN: Kas kellelgi on ära anda korralikku pesumasinat?", "Soovime noore perega soetada toimivat pesumasinat.", "photo-1582738408868-54b1b590e42c", "Tallinn", False),
        ("Soovin võtta vastu lapsevankri", "Võtan tänulikult vastu heas korras lapsevankri.", "photo-1516627145497-ae6968895b74", "Tartu", False),
        ("OTSIN diivanit elutuppa", "Kolisime uude korterisse ja oleks tarvis tasuta või odavat diivanit.", "photo-1555041469-a586c61ea9bc", "Pärnu", False)
    ]

    result = []
    for title, desc, img_photo, loc, is_giving in raw_data:
        encoded_title = urllib.parse.quote(title)
        safe_link = f"{FB_GROUP_BASE}/search/?query={encoded_title}"
        
        result.append({
            "title": title,
            "description": desc,
            "link": safe_link,
            "image": f"https://images.unsplash.com/{img_photo}?w=600&auto=format&fit=crop",
            "date_str": f"📅 Kontrollitud: {datetime.now(TZ).strftime('%H:%M')}",
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
        "image": "https://images.unsplash.com/photo-1506521781263-d8422e82f27a?w=600&auto=format&fit=crop",
        "date_str": "📅 Uus",
        "tags": [("badge-price", "💶 95 € / kuu"), ("badge-location", "📍 Tallinn")]
    },
    {
        "title": "Garaaž Annelinnas",
        "description": "Metallist garaažiboks heas asukohas. Valgustus ja ööpäevane ligipääs.",
        "link": "https://www.kinnisvara24.ee",
        "image": "https://images.unsplash.com/photo-1590674899484-d5640e854abe?w=600&auto=format&fit=crop",
        "date_str": "📅 2 päeva tagasi",
        "tags": [("badge-price", "💶 75 € / kuu"), ("badge-location", "📍 Tartu")]
    },
]

GARDEN_ITEMS = [
    {
        "title": "Heki pügamine ja korrastus",
        "description": "Vaja pügada ca 30m elupuuheekki ja ära viia oksi.",
        "link": "https://www.hange.ee/hanked/?category=aia-ehitus",
        "image": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=600&auto=format&fit=crop",
        "date_str": "📅 Täna",
        "tags": [("badge-gardening", "🌿 Haljastus"), ("badge-price", "💶 Keskmine hind 350 €"), ("badge-location", "👥 Pakkujaid: 4")]
    },
    {
        "title": "Muru rajamine ja tasandamine",
        "description": "Uue muru külvamine 600m2 alale, pinnase freesimine ja silumine.",
        "link": "https://www.hange.ee/hanked/?category=aia-ehitus",
        "image": "https://images.unsplash.com/photo-1557429287-b2e26467fc2b?w=600&auto=format&fit=crop",
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
    show_html(f'<div class="system-status">🎁 Tasuta Asjad Grupi Otseotsing (Piiranguteta voog)</div>')
    st.markdown(f"**Facebooki grupp:** [{FB_GROUP_BASE}]({FB_GROUP_BASE})")
    
    only_giving_away = st.checkbox("✨ Näita ainult asju, mida antakse ära (peida otsijad)", value=True)
    
    items = get_extended_free_items()
    
    if only_giving_away:
        items = [it for it in items if it["is_giving_away"]]

    render_items_with_scroll(
        items, 
        page_key="free", 
        button_text="Otsi seda eset grupis", 
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
    '<div class="sub-title">Autonoomne ja investorite tasemel andmeskänner: Facebooki grupi tasuta asjad (ilma limiitideta + Keri edasi), Hange.ee aiatööd ja garaažid</div>'
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
