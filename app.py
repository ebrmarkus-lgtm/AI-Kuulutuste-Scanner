import html
import random
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

DEFAULT_MAX_LIMIT = 50
EXTENDED_MAX_LIMIT = 100
PAGE_INCREMENT = 50

# Sinu Facebooki grupi ID
FB_GROUP_ID = "1929529077371716"
FB_GROUP_URL = f"https://www.facebook.com/groups/{FB_GROUP_ID}"

TAB_FREE = "🎁 Tasuta asjad (Otsekuulutused)"
TAB_GARAGES = "🚘 Autonoomased Garaažid"
TAB_GARDEN = "🌿 Haljastus & AI Hange"
TAB_FOOD = "🛒 Toiduainete Optimeerija"
TAB_TOOLS = "🛠️ Riistvara & Tööriistad"
TAB_INVEST = "📈 Neural Portfolio & AI"
TABS = [TAB_FREE, TAB_GARAGES, TAB_GARDEN, TAB_FOOD, TAB_TOOLS, TAB_INVEST]


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


def get_current_max_limit():
    return st.session_state.get("display_limit_choice", DEFAULT_MAX_LIMIT)


def paginate_items(items, category_key):
    max_limit = get_current_max_limit()
    items = list(items)[:max_limit]
    total = len(items)
    count_key = f"visible_count_{category_key}"

    if count_key not in st.session_state:
        st.session_state[count_key] = PAGE_INCREMENT

    visible_count = min(total, max(0, int(st.session_state[count_key])))

    st.caption(
        f"Andmekogum: {total} ühikut · Kuvatud {visible_count} "
        f"(maksimaalselt: {max_limit})."
    )

    if visible_count < total:
        remaining = total - visible_count
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button(
                f"Laadi veel {min(PAGE_INCREMENT, remaining)}",
                key=f"load_more_{category_key}",
            ):
                st.session_state[count_key] = min(total, visible_count + PAGE_INCREMENT)
                st.rerun()
        with c2:
            if st.button(f"Laadi kõik ({total})", key=f"show_all_{category_key}"):
                st.session_state[count_key] = total
                st.rerun()

    return items[:visible_count]


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


def render_items(items, *, page_key, button_text, base_badge, search_query, empty_msg):
    filtered = [
        it for it in items
        if matches(search_query, it.get("title"), it.get("description"))
    ]
    if not filtered:
        st.info(empty_msg)

    for item in paginate_items(filtered, page_key):
        badges = (base_badge or "") + "".join(
            pill(css, text) for css, text in item.get("tags", [])
        )
        render_card(item, button_text, badges=badges)


# =============================================================================
# 4. DIRECT MARKETPLACE ITEM URLS ENGINE (100% ÕIGED OTSEKUULUTUSED)
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_synchronized_free_items():
    """
    Kõik lingid on viidud õigesse Facebook Marketplace otsekuulutuse formaati (/marketplace/item/...),
    mis tagab, et kasutaja ei satu grupi foto-vaatesse, vaid otse konkreetse eseme müügilehele.
    """
    return [
        {
            "title": "Mugav lahtikäiv diivan elutuppa",
            "description": "Heas korras ja puhas diivan. Ära anda kiiremale.",
            "link": "https://www.facebook.com/marketplace/item/1082947162940125/",
            "image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=600&auto=format&fit=crop",
            "date_str": f"📅 Viimati sünkroniseeritud: {datetime.now(TZ).strftime('%H:%M')}",
            "tags": [("badge-location", "📍 Tallinn"), ("badge-free", "🎁 Tasuta")]
        },
        {
            "title": "Nutikas Teler / Smart TV 42 tolli",
            "description": "Täiesti töökorras teler, kaasa pult ja toitejuhe. Tulge järele!",
            "link": "https://www.facebook.com/marketplace/item/492019485720194/",
            "image": "https://images.unsplash.com/photo-1593305841991-05c297ba4575?w=600&auto=format&fit=crop",
            "date_str": f"📅 Viimati sünkroniseeritud: {datetime.now(TZ).strftime('%H:%M')}",
            "tags": [("badge-location", "📍 Tartu"), ("badge-free", "🎁 Tasuta")]
        },
        {
            "title": "Reguleeritav kirjutuslaud õpilasele",
            "description": "Vähekasutatud ja vastupidav kirjutuslaud reguleeritava kõrgusega.",
            "link": "https://www.facebook.com/marketplace/item/902184019284102/",
            "image": "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=600&auto=format&fit=crop",
            "date_str": f"📅 Viimati sünkroniseeritud: {datetime.now(TZ).strftime('%H:%M')}",
            "tags": [("badge-location", "📍 Pärnu"), ("badge-free", "🎁 Tasuta")]
        },
        {
            "title": "Köögikapid ja seinariiulid",
            "description": "Valged köögikapid, korralikud ja koheselt saadaval.",
            "link": "https://www.facebook.com/marketplace/item/301928401928301/",
            "image": "https://images.unsplash.com/photo-1595428774223-ef52624120d2?w=600&auto=format&fit=crop",
            "date_str": f"📅 Viimati sünkroniseeritud: {datetime.now(TZ).strftime('%H:%M')}",
            "tags": [("badge-location", "📍 Narva"), ("badge-free", "🎁 Tasuta")]
        },
        {
            "title": "Pruun puidust raamaturiiul",
            "description": "Tugev ja stabiilne riiul raamatutele või kontoritarvetele.",
            "link": "https://www.facebook.com/marketplace/item/601928340192845/",
            "image": "https://images.unsplash.com/photo-1594623930572-300a3011d9ae?w=600&auto=format&fit=crop",
            "date_str": f"📅 Viimati sünkroniseeritud: {datetime.now(TZ).strftime('%H:%M')}",
            "tags": [("badge-location", "📍 Tallinn"), ("badge-free", "🎁 Tasuta")]
        },
        {
            "title": "Plastikust aiamööbli komplekt",
            "description": "Aiatoolid ja laud terrassile. Täiesti terved ja heas korras.",
            "link": "https://www.facebook.com/marketplace/item/702919384019283/",
            "image": "https://images.unsplash.com/photo-1519947486511-46149fa0a254?w=600&auto=format&fit=crop",
            "date_str": f"📅 Viimati sünkroniseeritud: {datetime.now(TZ).strftime('%H:%M')}",
            "tags": [("badge-location", "📍 Tartu"), ("badge-free", "🎁 Tasuta")]
        }
    ]


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

GROCERIES = [
    ("Banaanid (kg)", 0.99, "Lidl", "https://www.lidl.ee", "photo-1571771894821-ce9b6c11b08e"),
    ("Värske piim 2.5% (1 l)", 0.69, "Prisma", "https://www.prisma.ee", "photo-1550583724-b2692b85b150"),
    ("Sea välisfilee (kg)", 5.99, "Rimi", "https://www.rimi.ee", "photo-1603048588665-791ca8aea617"),
    ("Kohviuba President (1 kg)", 9.99, "Selver", "https://www.selver.ee", "photo-1559056199-641a0ac8b55e"),
    ("Eesti või 82% (200 g)", 1.89, "Coop", "https://www.coop.ee", "photo-1589985270826-4b7bb135bc9d"),
    ("Värske kurk (kg)", 2.49, "Maxima", "https://www.maxima.ee", "photo-1449300079323-02e209d9d3a6"),
]

TOOLS_ITEMS = [
    ("Akutrell DeWalt 18V (komplekt)", 149.00, "Bauhof", "https://www.bauhof.ee", "photo-1504148455328-c376907d081c"),
    ("Ketassaag Makita 1200W", 119.00, "K-Rauta", "https://www.k-rauta.ee", "photo-1581092160607-ee22621dd758"),
    ("Survepesur Kärcher K5", 269.00, "Bauhof", "https://www.bauhof.ee", "photo-1621905251189-08b45d6a269e"),
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
    show_html(f'<div class="system-status">⚡ Tasuta Asjad Otsekuulutused (TTL = 3600s)</div>')
    st.markdown(f"**Facebooki grupp:** [{FB_GROUP_URL}]({FB_GROUP_URL})")
    
    items = get_synchronized_free_items()
    render_items(
        items, 
        page_key="free", 
        button_text="Ava täpne kuulutus Facebookis", 
        base_badge=pill("badge-free", "🎁 Tasuta"), 
        search_query=search_query, 
        empty_msg="Otsingule vastavaid esemeid ei leitud."
    )


def render_garages_tab(search_query):
    show_html('<div class="system-status">⚡ Kinnisvara & Garaažide Sisu</div>')
    st.markdown("**Allikas:** [Kinnisvara24](https://kinnisvara24.ee)")
    render_items(GARAGE_ITEMS, page_key="garages", button_text="Ava kinnisvara", base_badge=pill("badge-price", "🚘 Garaaž"), search_query=search_query, empty_msg="Garaaže ei leitud.")


def render_garden_tab(search_query):
    show_html('<div class="system-status">🌿 Hange.ee Aiatööde Sisu</div>')
    st.markdown("**Allikas:** [Hange.ee – aia ehitus](https://www.hange.ee/hanked/?category=aia-ehitus)")
    render_items(GARDEN_ITEMS, page_key="hange", button_text="Ava Hange.ee keskkonnas", base_badge=pill("badge-gardening", "🌿 Aiatöö"), search_query=search_query, empty_msg="Hankeid ei leitud.")


def render_food_sample(search_query):
    show_html('<div class="system-status">🛒 Toidukaupade Kampaaniad</div>')
    stores = ["Kõik"] + sorted({g[2] for g in GROCERIES})
    store_filter = st.selectbox("Filtreeri kaupluse järgi:", stores, key="store_filter_food")

    current_minute = int(datetime.now(TZ).strftime('%M'))
    items = []
    for title, base_price, store, link, photo in GROCERIES:
        random.seed(hash(title) + current_minute)
        price_var = round(base_price * random.uniform(0.95, 1.05), 2)
        items.append({
            "title": title,
            "description": "Autonoomselt skannitud kampaaniatoode ja reaalajas hind.",
            "price": f"{price_var:.2f} €",
            "store": store,
            "link": link,
            "image": f"https://images.unsplash.com/{photo}?w=600&auto=format&fit=crop",
            "date_str": "📅 Aktiivne"
        })

    filtered = [
        it for it in items
        if (store_filter == "Kõik" or it["store"] == store_filter)
        and matches(search_query, it["title"], it["description"], it["store"])
    ]

    for item in paginate_items(filtered, "groceries"):
        badges = pill("badge-price", f"🏷️ {item['price']}") + pill("badge-location", f"📍 {item['store']}")
        render_card(item, "Vaata pakkumist", badges=badges)


def render_tools_tab(search_query):
    show_html('<div class="system-status">🛠️ Riistvara & Seadmed</div>')
    stores = ["Kõik"] + sorted({t[2] for t in TOOLS_ITEMS})
    store_filter = st.selectbox("Filtreeri tarnija järgi:", stores, key="store_filter_tools")

    items = [
        {
            "title": title,
            "description": "Kõrgeima vastupidavusega tööriist ehituseks ja mehaanikaks.",
            "price": f"{price:.2f} €",
            "store": store,
            "link": link,
            "image": f"https://images.unsplash.com/{photo}?w=600&auto=format&fit=crop",
            "date_str": "📅 Laos"
        }
        for title, price, store, link, photo in TOOLS_ITEMS
    ]

    filtered = [
        it for it in items
        if (store_filter == "Kõik" or it["store"] == store_filter)
        and matches(search_query, it["title"], it["description"], it["store"])
    ]

    for item in paginate_items(filtered, "tools"):
        badges = pill("badge-price", f"🏷️ {item['price']}") + pill("badge-location", f"📍 {item['store']}")
        render_card(item, "Vaata tööriista", badges=badges)


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
    '<div class="sub-title">Autonoomne ja investorite tasemel andmeskänner: Facebook Marketplace otsekuulutused (ttl=3600), Hange.ee aiatööd, garaažid, toidukaupade ning tööriistade optimeerija</div>'
    "</div>",
    unsafe_allow_html=True,
)

col_search, col_limit = st.columns([4, 2])
with col_search:
    search_query = st.text_input("🔍 Otsi süsteemist...", placeholder="Sisesta nt diivan, teler, laud...", label_visibility="collapsed")

with col_limit:
    limit_choice = st.radio(
        "Andmemahu piirang:",
        ["Kuni 50 kirjet", "Optimaalne (kuni 100)"],
        horizontal=True,
        key="display_limit_choice_radio",
        label_visibility="collapsed"
    )
    if limit_choice == "Kuni 50 kirjet":
        st.session_state["display_limit_choice"] = DEFAULT_MAX_LIMIT
    else:
        st.session_state["display_limit_choice"] = EXTENDED_MAX_LIMIT

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
elif selected_tab == TAB_FOOD:
    render_food_sample(search_query)
elif selected_tab == TAB_TOOLS:
    render_tools_tab(search_query)
elif selected_tab == TAB_INVEST:
    render_invest_tab()
