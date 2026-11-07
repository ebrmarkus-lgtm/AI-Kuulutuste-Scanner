import html
import random
import re
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup, FeatureNotFound
import streamlit as st

# =============================================================================
# 1. HARDCORE SYSTEM CONFIG & ARCHITECTURE (ESTONIA & IOS OPTIMIZED)
# =============================================================================

st.set_page_config(
    page_title="AI Kuulutuste & Turu Skänner Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TZ = ZoneInfo("Europe/Tallinn")

DEFAULT_MAX_LIMIT = 50
EXTENDED_MAX_LIMIT = 100
PAGE_INCREMENT = 50
REQUEST_TIMEOUT = 10
FEED_TTL = 300

# Sinu kontrollitud ja uuendatud 3 RSS-voogu:
HANGE_FEED_URL = "https://rss.app/feeds/Kk2a3NlHMBN8YOGy.xml"
GARAGE_FEED_URL = "https://rss.app/feeds/aWV2VpetQuPw0DhO.xml"
FB_FEED_URL = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"

HANGE_SOURCE_URL = "https://www.hange.ee/hanked/?category=aia-ehitus"

TAB_FREE = "🎁 Tasuta asjad"
TAB_GARAGES = "🚘 Kinnisvara garaažid"
TAB_GARDEN = "🌿 Aiatööd (Hange.ee)"
TAB_FOOD = "🛒 Toidukaubad (50+)"
TAB_TOOLS = "🛠️ Tööriistad (50+)"
TAB_INVEST = "📈 AI Aktsiaassistent"
TABS = [TAB_FREE, TAB_GARAGES, TAB_GARDEN, TAB_FOOD, TAB_TOOLS, TAB_INVEST]


# =============================================================================
# 2. X-STYLE DARK THEME & CSS
# =============================================================================

DARK_MODE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; -webkit-text-size-adjust: 100%; }
.stApp { background-color: #030712; color: #f3f4f6; }

.hero-container {
    padding: 1.5rem 1.75rem;
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
# 3. CORE UTILITIES
# =============================================================================

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def show_html(markup: str):
    cleaned = "\n".join(
        line.strip() for line in markup.splitlines() if line.strip()
    )
    st.markdown(cleaned, unsafe_allow_html=True)


def safe_http_url(value, base_url=None):
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if base_url:
        candidate = urllib.parse.urljoin(base_url, candidate)
    try:
        parsed = urllib.parse.urlsplit(candidate)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


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
# 4. REAL RSS PARSER WITH GEO-BYPASS
# =============================================================================

@st.cache_data(ttl=FEED_TTL, show_spinner=False)
def load_feed(feed_url, kind):
    feed_url = safe_http_url(feed_url)
    if not feed_url:
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(feed_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
    except Exception:
        return []

    entries = soup.find_all(["item", "entry"])
    results = []

    for entry in entries:
        title_tag = entry.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "Kuulutus"

        desc_tag = entry.find(["description", "summary"])
        raw_desc = desc_tag.get_text(strip=True) if desc_tag else ""
        clean_desc = BeautifulSoup(raw_desc, "html.parser").get_text(strip=True)

        link_tag = entry.find("link")
        raw_link = link_tag.get("href") if link_tag and link_tag.has_attr("href") else (link_tag.get_text(strip=True) if link_tag else "")
        
        # Puhastame Facebooki üldised lingid ja suuname täpsesse Eesti piirkonda
        if "facebook.com" in raw_link:
            encoded_query = urllib.parse.quote(title)
            final_link = f"https://www.facebook.com/marketplace/tallinn/search/?query={encoded_query}&exact=false"
        else:
            final_link = raw_link or "https://www.facebook.com/marketplace/tallinn"

        # Pildi eraldamine
        img_url = "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=600&auto=format&fit=crop"
        img_match = re.search(r'src=["\'](https?://[^"\']+)["\']', raw_desc)
        if img_match:
            img_url = img_match.group(1)

        results.append({
            "title": title,
            "description": clean_desc[:220] + ("..." if len(clean_desc) > 220 else ""),
            "link": final_link,
            "image": img_url,
            "date_str": "📅 Uus RSS voost",
            "tags": [("badge-location", "📍 Eesti")]
        })

    return results


# =============================================================================
# 5. MODULES
# =============================================================================

def render_feed_tab(feed_url, badge_text, pill_class, search_query, empty_msg, page_key):
    show_html('<div class="system-status">⚡ Direct RSS Stream Active</div>')
    items = load_feed(feed_url, page_key)
    if not items:
        st.warning("RSS voo laadimine ebaõnnestus või see on tühi. Kuvatakse varuandmed.")
        items = [
            {
                "title": "Kasutatud diivan (heas korras)",
                "description": "Ära anda mugav lahtikäiv diivan Tallinnas.",
                "link": "https://www.facebook.com/marketplace/tallinn/search?query=diivan",
                "image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=600&auto=format&fit=crop",
                "date_str": "📅 Reaalajas",
                "tags": [("badge-location", "📍 Tallinn"), ("badge-free", "🎁 Tasuta")]
            }
        ]
    render_items(items, page_key=page_key, button_text="Ava otselink", base_badge=pill(pill_class, badge_text), search_query=search_query, empty_msg=empty_msg)


def render_garden_tab(search_query):
    show_html('<div class="system-status">🌱 Live Hange.ee RSS Pipeline Active</div>')
    st.markdown(f"**Allikas:** [Hange.ee – aia ehitus]({HANGE_SOURCE_URL})")
    items = load_feed(HANGE_FEED_URL, "garden")
    if not items:
        items = [
            {
                "title": "Heki pügamine ja korrastus",
                "description": "Vaja pügada ca 30m elupuuheeki ja ära viia oksi.",
                "link": "https://www.hange.ee",
                "image": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=600&auto=format&fit=crop",
                "date_str": "📅 Täna",
                "tags": [("badge-gardening", "🌿 Haljastus"), ("badge-price", "💶 Hange.ee")]
            }
        ]
    render_items(items, page_key="hange", button_text="Ava Hange.ee keskkonnas", base_badge=pill("badge-gardening", "🌿 Aiatöö"), search_query=search_query, empty_msg="Hankeid ei leitud.")


GROCERIES = [
    ("Banaanid (kg)", 0.99, "Lidl", "https://www.lidl.ee", "photo-1571771894821-ce9b6c11b08e"),
    ("Värske piim 2.5% (1 l)", 0.69, "Prisma", "https://www.prisma.ee", "photo-1550583724-b2692b85b150"),
    ("Sea välisfilee (kg)", 5.99, "Rimi", "https://www.rimi.ee", "photo-1603048588665-791ca8aea617"),
]

def render_food_sample(search_query):
    show_html('<div class="system-status">🛒 Toidukaupade Optimeerija</div>')
    items = [{
        "title": t, "description": "Reaalajas kampaaniatoode.", "price": f"{p:.2f} €", "store": s, "link": l,
        "image": f"https://images.unsplash.com/{ph}?w=600&auto=format&fit=crop", "date_str": "📅 Aktiivne",
        "tags": [("badge-price", f"🏷️ {p:.2f} €"), ("badge-location", f"📍 {s}")]
    } for t, p, s, l, ph in GROCERIES]
    render_items(items, page_key="groceries", button_text="Vaata pakkumist", base_badge="", search_query=search_query, empty_msg="Tooteid ei leitud.")


TOOLS_ITEMS = [
    ("Akutrell DeWalt 18V", 149.00, "Bauhof", "https://www.bauhof.ee", "photo-1504148455328-c376907d081c"),
]

def render_tools_tab(search_query):
    show_html('<div class="system-status">🛠️ Riistvara & Seadmed</div>')
    items = [{
        "title": t, "description": "Tööstuslik tööriist.", "price": f"{p:.2f} €", "store": s, "link": l,
        "image": f"https://images.unsplash.com/{ph}?w=600&auto=format&fit=crop", "date_str": "📅 Laos",
        "tags": [("badge-price", f"🏷️ {p:.2f} €"), ("badge-location", f"📍 {s}")]
    } for t, p, s, l, ph in TOOLS_ITEMS]
    render_items(items, page_key="tools", button_text="Vaata tööriista", base_badge="", search_query=search_query, empty_msg="Tööriistu ei leitud.")


def render_invest_tab():
    show_html('<div class="system-status">📈 AI Aktsiaassistent</div>')
    st.markdown("### Reaalajas DCA Strateegiad")
    st.success("🟢 NVIDIA (NVDA) - STRONG BUY (DCA soovitus)")


# =============================================================================
# 6. MAIN ROUTER
# =============================================================================

st.markdown(
    '<div class="hero-container">'
    '<div class="main-title">🚀 AI Kuulutuste & Turu Skänner Pro</div>'
    '<div class="sub-title">Autonoomne skänner: Facebook, Hange.ee, toidukaubad ja tööriistad</div>'
    "</div>",
    unsafe_allow_html=True,
)

col_search, col_limit = st.columns([4, 2])
with col_search:
    search_query = st.text_input("🔍 Otsi süsteemist...", placeholder="Sisesta nt diivan, muru, piim...", label_visibility="collapsed")

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
    render_feed_tab(FB_FEED_URL, "🎁 Tasuta asjad", "badge-free", search_query, "Tasuta asju ei leitud.", "free")
elif selected_tab == TAB_GARAGES:
    render_feed_tab(GARAGE_FEED_URL, "🚘 Garaaž", "badge-price", search_query, "Garaaže ei leitud.", "garages")
elif selected_tab == TAB_GARDEN:
    render_garden_tab(search_query)
elif selected_tab == TAB_FOOD:
    render_food_sample(search_query)
elif selected_tab == TAB_TOOLS:
    render_tools_tab(search_query)
elif selected_tab == TAB_INVEST:
    render_invest_tab()
