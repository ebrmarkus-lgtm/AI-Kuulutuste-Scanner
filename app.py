import html
import random
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

# =============================================================================
# 1. HARDCORE SYSTEM CONFIG & ARCHITECTURE (IOS & MOBILE OPTIMIZED)
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

TAB_FREE = "🎁 Tasuta asjad"
TAB_GARAGES = "🚘 Kinnisvara garaažid"
TAB_GARDEN = "🌿 Aiatööd (Hange.ee)"
TAB_FOOD = "🛒 Toidukaubad (50+)"
TAB_TOOLS = "🛠️ Tööriistad (50+)"
TAB_INVEST = "📈 AI Aktsiaassistent"
TABS = [TAB_FREE, TAB_GARAGES, TAB_GARDEN, TAB_FOOD, TAB_TOOLS, TAB_INVEST]


# =============================================================================
# 2. X-STYLE DARK THEME & RESPONSIVE CSS
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
# 4. RIKKALIKUD JA SÕLTUMATUD ANDMEBAASID
# =============================================================================

FREE_ITEMS = [
    {
        "title": "Kasutatud diivan (heas korras)",
        "description": "Ära anda mugav lahtikäiv diivan Tallinnas. Ise äraviimisega.",
        "link": "https://www.facebook.com/marketplace/tallinn/search?query=diivan",
        "image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=600&auto=format&fit=crop",
        "date_str": "📅 Täna 12:30",
        "tags": [("badge-location", "📍 Tallinn"), ("badge-free", "🎁 Tasuta")]
    },
    {
        "title": "Laste kirjutuslaud ja tool",
        "description": "Vähekasutatud reguleeritav kirjutuslaud koolijütsile. Tasuta!",
        "link": "https://www.facebook.com/marketplace/tartu/search?query=kirjutuslaud",
        "image": "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=600&auto=format&fit=crop",
        "date_str": "📅 Täna 10:15",
        "tags": [("badge-location", "📍 Tartu"), ("badge-free", "🎁 Tasuta")]
    },
    {
        "title": "Ehitusjäägid / Puitmaterjal",
        "description": "Küttepuudeks või meisterdamiseks sobilikud puidujäägid ja lauad.",
        "link": "https://www.facebook.com/marketplace/parnu/search?query=ehitusjaagid",
        "image": "https://images.unsplash.com/photo-1541888946425-d0fbb18f64e8?w=600&auto=format&fit=crop",
        "date_str": "📅 Eile",
        "tags": [("badge-location", "📍 Pärnu"), ("badge-free", "🎁 Tasuta")]
    },
    {
        "title": "Seinakapp ja köögiriistad",
        "description": "Valged köögikapid, vajavad kerget puhastust. Anna ära kiiremale.",
        "link": "https://www.facebook.com/marketplace/narva/search?query=seinakapp",
        "image": "
