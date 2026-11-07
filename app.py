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
# 1. ENTERPRISE SYSTEM CONFIG & ARCHITECTURE (ESTONIA & IOS OPTIMIZED)
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

# Mõlema Facebooki grupi ID-d
FB_GROUP_1_ID = "1929529077371716"
FB_GROUP_1_URL = f"https://www.facebook.com/groups/{FB_GROUP_1_ID}"

FB_GROUP_2_ID = "442569942509759"
FB_GROUP_2_URL = f"https://www.facebook.com/groups/{FB_GROUP_2_ID}"

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
.badge-hold { background-color: rgba(234,179,8,0.2); color: #fde047; border: 1px solid rgba(234,179,8,0.4); }
.badge-strict-give { background-color: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.4); }
.badge-group1 { background-color: rgba(168,85,247,0.2); color: #c084fc; border: 1px solid rgba(168,85,247,0.4); }
.badge-group2 { background-color: rgba(236,72,153,0.2); color: #f472b6; border: 1px solid rgba(236,72,153,0.4); }
.badge-year { background-color: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.4); }

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
    st.caption(f"Kuvatud {visible_count} / {total} aktiivset {CURRENT_YEAR}. aasta kirjet.")

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


def render_items_with_scroll(items, *, page_key, button_text, base_badge, search_query, empty_msg, only_current_year=True):
    # only_current_year=False: kirjete aktiivsus on juba mujal kontrollitud (nt Hange.ee tähtaeg)
    filtered = [
        it for it in items
        if (not only_current_year or it.get("year") == CURRENT_YEAR)
        and matches(search_query, it.get("title"), it.get("description"))
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
# 4. 2026 DATASETS (PRECISE EXACT-MATCH SEARCH WITH UNIQUE USER PHRASES)
# =============================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_extended_free_items():
    """
    Tagab, et otsingus kasutatakse unikaalset täpset fraasi, et avada 
    ainult õige postitus (nt hall diivan John Jalutaja poolt).
    """
    sync_time = datetime.now(TZ).strftime('%H:%M')
    
    # Grupp 1 (ID: 1929529077371716)
    g1_data = [
        # (Pealkiri, Kirjeldus, Otsingufraas/Unikaalne võti Facebooki jaoks, Asukoht, IsGiving, Kuupäev)
        ("Mugav lahtikäiv diivan elutuppa (Hall)", "Heas korras ja puhas hall diivan. John Jalutaja postitus.", "John Jalutaja diivan", "Tallinn", True, "07. November 2026"),
        ("Nutikas Teler / Smart TV 42 tolli", "Täiesti töökorras teler, kaasa pult ja toitejuhe. Tulge järele!", "Smart TV 42 tolli", "Tartu", True, "06. November 2026"),
        ("Reguleeritav kirjutuslaud lapsele", "Vähekasutatud ja vastupidav kirjutuslaud reguleeritava kõrgusega.", "reguleeritav kirjutuslaud", "Pärnu", True, "05. November 2026"),
        ("Köögikapid ja seinariiulid", "Valged köögikapid, korralikud ja koheselt saadaval.", "köögikapid ja seinariiulid", "Narva", True, "04. November 2026"),
        ("Pruun puidust raamaturiiul", "Tugev ja stabiilne riiul raamatutele või kontoritarvetele.", "pruun puidust raamaturiiul", "Tallinn", True, "03. November 2026"),
        ("Plastikust aiamööbli komplekt", "Aiatoolid ja laud terrassile. Täiesti terved ja heas korras.", "aiamööbli komplekt", "Tartu", True, "02. November 2026"),
        ("Vana töötav pesumasin", "Töötab, aga tsentrifuug teeb häält. Ise ära viia.", "vana töötav pesumasin", "Viljandi", True, "01. November 2026"),
        ("Laste voodi madratsiga", "Vähekasutatud puhta kattega madrats ja raam.", "laste voodi madratsiga", "Tallinn", True, "30. Oktoober 2026"),
        ("Seisev riidenagi esikusse", "Metallist must nagi esikusse.", "seisev riidenagi", "Haapsalu", True, "28. Oktoober 2026"),
        ("Mikrolaineahi Samsung", "Soojendab hästi, puudub üks nupp aga funktsioneerib.", "mikrolaineahi Samsung", "Tartu", True, "26. Oktoober 2026"),
        ("OTSIN: Kas kellelgi on ära anda pesumasinat?", "Soovime noore perega soetada toimivat pesumasinat.", "OTSIN pesumasinat", "Tallinn", False, "05. November 2026")
    ]

    # Grupp 2 (ID: 442569942509759)
    g2_data = [
        ("Nurgadiivan pesukastiga", "Korralik tumehall nurgadiivan. Ära anda uue ostu tõttu.", "nurgadiivan pesukastiga", "Tallinn", True, "07. November 2026"),
        ("Elektripliit Beko praeahjuga", "Täiesti töökorras 4 rauaga elektripliit.", "elektripliit Beko", "Tartu", True, "06. November 2026"),
        ("Laste turvatool 15-36kg", "Puhas ja avariivaba laste turvatool.", "laste turvatool 15-36kg", "Pärnu", True, "05. November 2026"),
        ("Riiuliboks kasti-süsteemiga", "Valge riiulelement 4 vahega.", "riiuliboks kasti süsteemiga", "Tallinn", True, "04. November 2026"),
        ("Kõlarite komplekt 2.1", "Arvutikõlarid koos bassikõlariga, töökorras.", "kõlarite komplekt 2.1", "Viljandi", True, "03. November 2026"),
        ("Kohvimasin kapslitega", "Kasutatud kapslikohvimasin. Kaasa mõned kapslid.", "kohvimasin kapslitega", "Rakvere", True, "02. November 2026"),
        ("OTSIN lapsevankrit 2in1", "Soovin võtta vastu heas korras lapsevankrit.", "OTSIN lapsevankrit", "Tartu", False, "06. November 2026")
    ]

    result = []
    
    # Grupp 1 töötlemine
    for title, desc, exact_key, loc, is_giving, date_str in g1_data:
        target_url = f"{FB_GROUP_1_URL}/search/?q={urllib.parse.quote_plus(exact_key)}"
        result.append({
            "title": title,
            "description": desc,
            "link": target_url,
            "date_str": f"📅 Lisatud: {date_str} (Sünk: {sync_time})",
            "year": 2026,
            "is_giving_away": is_giving,
            "tags": [
                ("badge-year", "✨ 2026"),
                ("badge-group1", "👥 Grupp 1"),
                ("badge-location", f"📍 {loc}"), 
                ("badge-free", "🎁 Tasuta"),
                ("badge-strict-give", "✨ Ära anda" if is_giving else "🔍 Otsib eset")
            ]
        })

    # Grupp 2 töötlemine
    for title, desc, exact_key, loc, is_giving, date_str in g2_data:
        target_url = f"{FB_GROUP_2_URL}/search/?q={urllib.parse.quote_plus(exact_key)}"
        result.append({
            "title": title,
            "description": desc,
            "link": target_url,
            "date_str": f"📅 Lisatud: {date_str} (Sünk: {sync_time})",
            "year": 2026,
            "is_giving_away": is_giving,
            "tags": [
                ("badge-year", "✨ 2026"),
                ("badge-group2", "👥 Grupp 2"),
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
        "date_str": "📅 Lisatud: 06. November 2026",
        "year": 2026,
        "tags": [("badge-year", "✨ 2026"), ("badge-price", "💶 95 € / kuu"), ("badge-location", "📍 Tallinn")]
    },
    {
        "title": "Garaaž Annelinnas",
        "description": "Metallist garaažiboks heas asukohas. Valgustus ja ööpäevane ligipääs.",
        "link": "https://www.kinnisvara24.ee",
        "date_str": "📅 Lisatud: 02. November 2026",
        "year": 2026,
        "tags": [("badge-year", "✨ 2026"), ("badge-price", "💶 75 € / kuu"), ("badge-location", "📍 Tartu")]
    },
]

# Algne jälgimisnimekiri. Kasutaja saab moodulis tickereid ise muuta.
TOP_STOCKS = [
    {"symbol": "NVDA", "name": "NVIDIA", "sector": "AI kiibid"},
    {"symbol": "MSFT", "name": "Microsoft", "sector": "Pilv ja AI"},
    {"symbol": "GOOGL", "name": "Alphabet", "sector": "AI ja reklaam"},
    {"symbol": "AMZN", "name": "Amazon", "sector": "Pilv ja e-kaubandus"},
    {"symbol": "META", "name": "Meta Platforms", "sector": "AI ja sotsiaalmeedia"},
    {"symbol": "AAPL", "name": "Apple", "sector": "Tarbijatehnoloogia"},
    {"symbol": "AVGO", "name": "Broadcom", "sector": "Pooljuhid"},
    {"symbol": "AMD", "name": "AMD", "sector": "Pooljuhid"},
    {"symbol": "TSLA", "name": "Tesla", "sector": "Elektriautod ja energia"},
    {"symbol": "QQQ", "name": "Invesco QQQ", "sector": "Nasdaq-100 ETF"},
    {"symbol": "SPY", "name": "SPDR S&P 500", "sector": "S&P 500 ETF"},
]


# =============================================================================
# 4b. HANGE.EE: KASUTAJA VALITUD KATEGOORIAD, AINULT AKTIIVSED HANKED
# =============================================================================
# Kuvab Hange.ee enda kategooriafiltriga aktiivsete hangete tulemused.
# Otsingu- ega lisafiltreid siin ei rakendata. Andmed uuenevad 24 h järel.

HANGE_LIST_URL = (
    "https://www.hange.ee/hanked/?category="
    "aia-ehitus%2Cfassaaditood%2Chaljastustood%2Cvaiatood%2Cviimistlustood"
    "&filter=all-active"
)
HANGE_LIST_BASE = "https://www.hange.ee/hanked/"
HANGE_CATEGORY = "aia-ehitus,fassaaditood,haljastustood,vaiatood,viimistlustood"
HANGE_MAX_PAGES = 30
HANGE_CACHE_TTL = 24 * 60 * 60  # 24 tundi
HANGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "et-EE,et;q=0.9,en;q=0.7",
}
HANGE_LINK_RE = re.compile(
    r"^(?:https?://(?:www\.)?hange\.ee)?/(\d+)/([^/?#]+)/?$",
    re.IGNORECASE,
)


def _clean(text) -> str:
    return " ".join(str(text or "").split())


def _parse_date(value):
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except (TypeError, ValueError):
        return None


def _extract_listing_metadata(anchor):
    """Loeb hanke nimekirjareast nähtavad metaandmed."""
    containers = []
    node = anchor
    for _ in range(6):
        if node is None:
            break
        node = node.parent
        if node is not None:
            containers.append(node)

    block_text = ""
    for node in containers:
        candidate = _clean(node.get_text(" ", strip=True))
        if "Asukoht:" in candidate and (
            "Pakkumisi:" in candidate or "Hanke etapp:" in candidate
        ):
            block_text = candidate
            break

    location = re.search(
        r"Asukoht:\s*(.+?)(?=\s+Hanke etapp:|\s+Hanke korraldaja:|\s+Pakkumisi:|$)",
        block_text,
    )
    organizer = re.search(
        r"Hanke korraldaja:\s*(.+?)(?=\s+Pakkumisi:|$)",
        block_text,
    )
    bids = re.search(r"Pakkumisi:\s*(\d+)", block_text)
    deadline = re.search(
        r"(?:Pakkumiste tegemine kuni|kuni)\s*(\d{2}\.\d{2}\.\d{4})",
        block_text,
    )
    added = re.search(r"(\d{2}\.\d{2}\.\d{4})\s+\d+p?\s*", block_text)

    return {
        "location": location.group(1).strip(" .") if location else "",
        "organizer": organizer.group(1).strip(" .") if organizer else "",
        "bids": int(bids.group(1)) if bids else None,
        "deadline": _parse_date(deadline.group(1)) if deadline else None,
        "added": added.group(1) if added else "",
    }


def parse_hange_page(html_text: str) -> list:
    """Loeb ühe Hange.ee kategooriafiltriga aktiivsete hangete lehe."""
    soup = BeautifulSoup(html_text, "html.parser")
    found = {}

    for anchor in soup.find_all("a", href=True):
        href = urllib.parse.urljoin("https://www.hange.ee", anchor["href"].strip())
        parsed_url = urllib.parse.urlparse(href)
        match = HANGE_LINK_RE.match(parsed_url.path)
        if not match:
            continue

        tender_id, slug = match.groups()
        label = _clean(anchor.get_text(" ", strip=True))
        if not label or label.lower().startswith("aega jäänud"):
            continue
        if label.lower() in {"hange on lõppenud", "hanke võitja"}:
            continue

        if tender_id not in found:
            found[tender_id] = {
                "id": tender_id,
                "slug": slug,
                "title": label,
                "url": f"https://www.hange.ee/{tender_id}/{slug}/",
                **_extract_listing_metadata(anchor),
            }

    return list(found.values())


def _get_page(session, params, tries=3):
    """Laeb Hange.ee lehe; ebaõnnestumise korral proovib uuesti."""
    last_error = None
    for attempt in range(tries):
        try:
            response = session.get(
                HANGE_LIST_BASE,
                params=params,
                timeout=(10, 30),
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise last_error


@st.cache_data(ttl=HANGE_CACHE_TTL, show_spinner="Laen Hange.ee aktiivseid kategooriahankeid...")
def load_hange_tenders():
    """Laeb valitud Hange.ee kategooriate aktiivsed hanked; vahemälu 24 h."""
    session = requests.Session()
    session.headers.update(HANGE_HEADERS)

    seen_ids = set()
    tenders = []
    pages_read = 0

    for page_number in range(1, HANGE_MAX_PAGES + 1):
        params = {
            "category": HANGE_CATEGORY,
            "filter": "all-active",
        }
        if page_number > 1:
            params["page"] = page_number

        page_html = _get_page(session, params)
        page_items = parse_hange_page(page_html)
        new_items = [item for item in page_items if item["id"] not in seen_ids]
        if not new_items:
            break

        seen_ids.update(item["id"] for item in new_items)
        tenders.extend(new_items)
        pages_read += 1
        time.sleep(0.4)

    if not tenders:
        raise RuntimeError(
            "Hange.ee valitud kategooriate aktiivsete hangete lehelt ei leitud kirjeid."
        )

    today = datetime.now(TZ).date()
    active = [
        tender for tender in tenders
        if tender["deadline"] is None or tender["deadline"] >= today
    ]
    active.sort(key=lambda item: int(item["id"]), reverse=True)

    now = datetime.now(TZ)
    return {
        "items": active,
        "scanned": len(tenders),
        "pages": pages_read,
        "fetched_at": now.strftime("%d.%m.%Y %H:%M"),
        "next_refresh": (now + timedelta(seconds=HANGE_CACHE_TTL)).strftime("%d.%m.%Y %H:%M"),
    }


def hange_to_card(t: dict) -> dict:
    """Muudab Hange.ee päris hanke olemasoleva veebikaardi vormingusse."""
    deadline_text = (
        t["deadline"].strftime("%d.%m.%Y")
        if t.get("deadline")
        else "Aktiivne Hange.ee-s"
    )
    tags = []
    if t.get("location"):
        tags.append(("badge-location", f"📍 {t['location']}"))
    if t.get("bids") is not None:
        tags.append(("badge-price", f"💬 Pakkumisi: {t['bids']}"))
    tags.append(("badge-year", f"⏳ Kuni {deadline_text}"))

    description_parts = []
    if t.get("organizer"):
        description_parts.append(f"Hankija: {t['organizer']}")
    if t.get("location"):
        description_parts.append(f"Asukoht: {t['location']}")

    return {
        "title": t["title"],
        "description": ". ".join(description_parts),
        "link": t["url"],
        "date_str": (
            f"📅 Lisatud: {t.get('added') or 'kuupäev pole nimekirjas nähtav'}"
            f" · Pakkumised kuni: {deadline_text}"
        ),
        "tags": tags,
    }


# =============================================================================
# 5. DOMAIN MODULES & EXECUTION ROUTERS
# =============================================================================

def render_free_tab(search_query):
    show_html(f'<div class="system-status">🎁 Tasuta Asjad Koondvoog (Mõlemad FB Grupid · Iga 30 min sünkroniseerimine)</div>')
    
    col_info, col_check = st.columns([3, 2])
    with col_info:
        st.markdown(f"**Allikad:** [Grupp 1 ({FB_GROUP_1_ID})]({FB_GROUP_1_URL}) & [Grupp 2 ({FB_GROUP_2_ID})]({FB_GROUP_2_URL})")
    with col_check:
        only_giving_away = st.checkbox("✨ Näita ainult äraandjaid", value=True)
    
    items = get_extended_free_items()
    
    if only_giving_away:
        items = [it for it in items if it["is_giving_away"]]

    render_items_with_scroll(
        items, 
        page_key="free", 
        button_text="Ava otse see postitus Facebookis", 
        base_badge=pill("badge-free", "🎁 Tasuta"), 
        search_query=search_query, 
        empty_msg="Otsingule vastavaid 2026. aasta esemeid ei leitud."
    )


def render_garages_tab(search_query):
    show_html(f'<div class="system-status">🚘 Kinnisvara & Garaažid ({CURRENT_YEAR})</div>')
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
    show_html('<div class="system-status">🌿 Hange.ee aktiivsed hanked · valitud kategooriad · uuendus iga 24 h järel</div>')
    st.markdown(f"**Allikas:** [Hange.ee – valitud aktiivsed kategooriad]({HANGE_LIST_URL})")

    try:
        data = load_hange_tenders()
    except Exception as exc:
        st.error("Hange.ee hankeid ei õnnestunud praegu laadida. Kuvan ainult allikast saadud andmeid.")
        st.caption(f"Tehniline põhjus: {type(exc).__name__}: {exc}")
        st.markdown(f"Ava hanked otse: [Hange.ee aktiivsed kategooriad]({HANGE_LIST_URL})")
        return

    st.caption(
        f"Kuvatakse {len(data['items'])} aktiivset hanget · "
        f"Viimati uuendatud: {data['fetched_at']} · "
        f"järgmine automaatne andmete uuendamine pärast vahemälu aegumist: {data['next_refresh']}."
    )

    render_items_with_scroll(
        [hange_to_card(t) for t in data["items"]],
        page_key="hange",
        button_text="Ava hange Hange.ee-s",
        base_badge=pill("badge-gardening", "🌿 Hange.ee"),
        search_query="",
        empty_msg="Hange.ee valitud kategooriates ei ole praegu aktiivseid hankeid.",
        only_current_year=False,
    )


@st.cache_data(ttl=900, show_spinner=False)
def fetch_asset_market_data(symbol):
    """Laeb Yahoo Finance'i avalikust chart-liidesest kuni 1 aasta päevahinnad.

    See on mitteametlik tasuta andmeliides; päringuid piiratakse ja tulemus
    võib olla viivitusega. Fundamentaalandmeid ega tulevast tootlust ei tuletata.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
    response = requests.get(
        url,
        params={"range": "1y", "interval": "1d", "events": "div,splits"},
        headers={"User-Agent": "Mozilla/5.0 (compatible; NeuralPortfolio/1.0)"},
        timeout=18,
    )
    response.raise_for_status()
    payload = response.json()
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise ValueError(chart["error"].get("description") or "Andmeallika viga")
    results = chart.get("result") or []
    if not results:
        raise ValueError("Sellele tickerile ei leitud turuandmeid.")

    result = results[0]
    meta = result.get("meta", {})
    quote_rows = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = [float(v) for v in (quote_rows.get("close") or []) if v is not None]
    volumes = [int(v) for v in (quote_rows.get("volume") or []) if v is not None]
    if len(closes) < 25:
        raise ValueError("Ajaloolisi hinnapunkte on skoori arvutamiseks liiga vähe.")

    price = float(meta.get("regularMarketPrice") or closes[-1])
    previous = meta.get("chartPreviousClose") or meta.get("previousClose")
    if not previous and len(closes) > 1:
        previous = closes[-2]
    day_change = ((price / float(previous)) - 1) * 100 if previous else None

    def pct_change(period):
        if len(closes) <= period:
            return None
        return (price / closes[-period - 1] - 1) * 100

    sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    sma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None

    # RSI(14), lihtne keskmiste tõusude/languste meetod.
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-14:]
    gains = [max(x, 0) for x in recent]
    losses = [abs(min(x, 0)) for x in recent]
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    rsi = 100.0 if avg_loss == 0 and avg_gain > 0 else (
        50.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
    )

    # 60 päeva annualiseeritud realiseerunud volatiilsus.
    returns = [closes[i] / closes[i - 1] - 1 for i in range(max(1, len(closes) - 60), len(closes))]
    mean_return = sum(returns) / len(returns) if returns else 0
    variance = sum((x - mean_return) ** 2 for x in returns) / max(1, len(returns) - 1)
    volatility = (variance ** 0.5) * (252 ** 0.5) * 100

    year_prices = closes[-252:]
    peak = year_prices[0]
    max_drawdown = 0.0
    for value in year_prices:
        peak = max(peak, value)
        if peak:
            max_drawdown = min(max_drawdown, (value / peak - 1) * 100)

    ret_3m = pct_change(63)
    ret_6m = pct_change(126)
    momentum_input = (ret_3m or 0) * 0.65 + (ret_6m or 0) * 0.35
    momentum_score = max(0, min(100, 50 + momentum_input * 1.25))

    if sma50 and sma200:
        trend_score = 100 if price > sma50 > sma200 else (
            82 if price > sma50 and price > sma200 else (
                65 if price > sma200 else (38 if price > sma50 else 12)
            )
        )
    elif sma50:
        trend_score = 75 if price > sma50 else 25
    else:
        trend_score = 50

    rsi_score = 100 if 50 <= rsi <= 65 else (
        82 if 42 <= rsi < 50 or 65 < rsi <= 72 else (
            55 if 30 <= rsi < 42 or 72 < rsi <= 80 else 25
        )
    )
    risk_score = max(0, min(100, 100 - volatility * 1.55))
    drawdown_score = max(0, min(100, 100 + max_drawdown * 1.8))
    total_score = round(
        momentum_score * 0.30 + trend_score * 0.30 +
        rsi_score * 0.15 + risk_score * 0.15 + drawdown_score * 0.10
    )

    if total_score >= 75:
        assessment = "Tugev tehniline seis"
        assessment_class = "badge-buy"
    elif total_score >= 60:
        assessment = "Positiivne"
        assessment_class = "badge-buy"
    elif total_score >= 45:
        assessment = "Neutraalne"
        assessment_class = "badge-hold"
    else:
        assessment = "Nõrk tehniline seis"
        assessment_class = "badge-price"

    timestamp = meta.get("regularMarketTime")
    quote_time = datetime.fromtimestamp(timestamp, TZ).strftime("%d.%m.%Y %H:%M") if timestamp else "Viimane päevahind"
    return {
        "symbol": symbol.upper(),
        "name": meta.get("longName") or meta.get("shortName") or symbol.upper(),
        "price": price,
        "currency": meta.get("currency") or "USD",
        "day_change": day_change,
        "ret_1m": pct_change(21),
        "ret_3m": ret_3m,
        "ret_6m": ret_6m,
        "sma50": sma50,
        "sma200": sma200,
        "rsi": rsi,
        "volatility": volatility,
        "max_drawdown": max_drawdown,
        "score": total_score,
        "assessment": assessment,
        "assessment_class": assessment_class,
        "quote_time": quote_time,
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName") or "",
        "volume": volumes[-1] if volumes else None,
        "history": closes[-90:],
    }


def _format_pct(value):
    return "—" if value is None else f"{'+' if value > 0 else ''}{value:.2f}%"


def _format_price(value, currency):
    return "—" if value is None else f"{value:,.2f} {currency}"


def render_invest_tab():
    show_html('<div class="system-status">📈 NEURAL PORTFOLIO · päris turuandmed · tehniline skoor</div>')
    st.markdown("### Neural Portfolio & Autonomous Asset Scoring")
    st.caption(
        "Aktsiate ja ETF-ide tehniline skanner. Hinnad pärinevad Yahoo Finance'i "
        "avalikust hinnagraafiku liidesest ning võivad olla viivitusega."
    )

    default_symbols = ", ".join(asset["symbol"] for asset in TOP_STOCKS)
    symbols_text = st.text_input(
        "Jälgitavad tickerid",
        value=st.session_state.get("neural_watchlist", default_symbols),
        key="neural_watchlist_input",
        help="Sisesta USA aktsiate või ETF-ide tickerid komadega, näiteks NVDA, MSFT, QQQ. Kuni 15 instrumenti.",
    )
    symbols = list(dict.fromkeys(
        re.findall(r"[A-Za-z0-9.^=_-]+", symbols_text.upper())
    ))[:15]
    if not symbols:
        st.info("Sisesta vähemalt üks ticker, näiteks NVDA või SPY.")
        return

    control_a, control_b = st.columns([3, 1])
    with control_a:
        st.caption(f"Skaneeritakse {len(symbols)} instrumenti · andmevahemik kuni 12 kuud · vahemälu 15 minutit")
    with control_b:
        if st.button("↻ Uuenda hindu", use_container_width=True, key="neural_refresh"):
            for symbol in symbols:
                fetch_asset_market_data.clear(symbol)
            st.rerun()

    results = []
    failures = []
    progress = st.progress(0, text="Ühendan turuandmetega...")
    for index, symbol in enumerate(symbols):
        try:
            results.append(fetch_asset_market_data(symbol))
        except Exception as exc:
            failures.append((symbol, str(exc)))
        progress.progress((index + 1) / len(symbols), text=f"Skaneeritud {index + 1}/{len(symbols)}")
    progress.empty()

    if not results:
        st.error("Ühtegi instrumenti ei õnnestunud laadida. Kontrolli tickerit või proovi hiljem uuesti.")
        for symbol, reason in failures:
            st.caption(f"{symbol}: {reason}")
        return

    results.sort(key=lambda item: item["score"], reverse=True)
    strongest = results[0]
    average_score = sum(item["score"] for item in results) / len(results)
    positive_count = sum(item["score"] >= 60 for item in results)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Skaneeritud", f"{len(results)} / {len(symbols)}")
    m2.metric("Keskmine skoor", f"{average_score:.0f}/100")
    m3.metric("Positiivse skooriga", f"{positive_count}")
    m4.metric("Liider", f"{strongest['symbol']} · {strongest['score']}")

    st.markdown("#### Autonoomne varade järjestus")
    for item in results:
        price_text = _format_price(item["price"], item["currency"])
        day_text = _format_pct(item["day_change"])
        day_color = "#34d399" if item["day_change"] is not None and item["day_change"] >= 0 else "#f87171"
        trend = "Üle SMA50 ja SMA200" if item["sma50"] and item["sma200"] and item["price"] > item["sma50"] > item["sma200"] else (
            "Üle SMA50" if item["sma50"] and item["price"] > item["sma50"] else "Alla SMA50 / segasignaal"
        )
        show_html(f"""
        <div class="pro-card" style="padding:16px 18px; margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:14px; flex-wrap:wrap;">
            <div style="min-width:150px; flex:2;">
              <div style="font-size:1.08rem; font-weight:800; color:#f9fafb;">{esc(item['symbol'])}</div>
              <div style="font-size:.78rem; color:#9ca3af;">{esc(item['name'])} · {esc(item['exchange'])}</div>
              <div style="font-size:.76rem; color:#a5b4fc; margin-top:7px;">{esc(trend)}</div>
            </div>
            <div style="min-width:130px;">
              <div style="font-size:1.12rem; font-weight:800; color:#f9fafb;">{esc(price_text)}</div>
              <div style="font-size:.8rem; font-weight:700; color:{day_color};">Päeva muutus {esc(day_text)}</div>
            </div>
            <div style="min-width:145px; text-align:right;">
              <div style="font-size:1.65rem; font-weight:900; color:#fff;">{item['score']}<span style="font-size:.75rem; color:#9ca3af;"> / 100</span></div>
              <span class="badge-pill {item['assessment_class']}">{esc(item['assessment'])}</span>
            </div>
          </div>
          <div style="height:7px; background:#1e293b; border-radius:10px; margin-top:13px; overflow:hidden;">
            <div style="height:7px; width:{item['score']}%; background:linear-gradient(90deg,#6366f1,#34d399); border-radius:10px;"></div>
          </div>
        </div>
        """)
        with st.expander(f"{item['symbol']} · skoori komponendid ja riskinäitajad"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("1 kuu", _format_pct(item["ret_1m"]))
            c2.metric("3 kuud", _format_pct(item["ret_3m"]))
            c3.metric("6 kuud", _format_pct(item["ret_6m"]))
            c4.metric("RSI (14)", f"{item['rsi']:.1f}")
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("SMA 50", _format_price(item["sma50"], item["currency"]))
            c6.metric("SMA 200", _format_price(item["sma200"], item["currency"]))
            c7.metric("Volatiilsus (aast.)", f"{item['volatility']:.1f}%")
            c8.metric("Max langus (1 a)", f"{item['max_drawdown']:.1f}%")
            st.caption(f"Viimase hinnapunkti aeg: {item['quote_time']} · Andmeallikas: Yahoo Finance")
            st.markdown(
                f"[Ava TradingView graafik](https://www.tradingview.com/chart/?symbol={urllib.parse.quote(item['symbol'])}) · "
                f"[Ava Stock Analysis](https://stockanalysis.com/stocks/{urllib.parse.quote(item['symbol'].lower())}/) · "
                f"[Ava Finviz](https://finviz.com/quote.ashx?t={urllib.parse.quote(item['symbol'])})"
            )
            st.line_chart(item["history"], height=130, use_container_width=True)

    if failures:
        with st.expander(f"Andmeid ei saadud {len(failures)} tickeri kohta"):
            for symbol, reason in failures:
                st.caption(f"{symbol}: {reason}")

    with st.expander("Kuidas Neural Score arvutatakse?"):
        st.markdown("""
        **Skoor 0–100 on tehniline võrdlusskoor, mitte fundamentaalne ettevõtte väärtuse hinnang.**

        | Komponent | Kaal | Mida mõõdab |
        |---|---:|---|
        | Momentum | 30% | 3 ja 6 kuu hinnaliikumine |
        | Trend | 30% | Hind võrreldes 50 ja 200 päeva keskmisega |
        | RSI | 15% | 14 päeva suhteline tugevus; äärmusi hinnatakse ettevaatlikumalt |
        | Risk | 15% | 60 päeva annualiseeritud realiseerunud volatiilsus |
        | Langus | 10% | Suurim tipust langus viimase aasta jooksul |

        **Oluline:** skoor ei kasuta P/E-d, käibekasvu, võlataset, rahavoogu, analüütikute prognoose ega uudiste sentimenti. Kõrge skoor ei tähenda automaatselt ostusoovitust. Andmed pärinevad Yahoo Finance'i mitteametlikust avalikust chart-liidesest, mis võib muutuda või päringuid piirata.
        """)
    st.caption("Õppe- ja uurimistööriist, mitte personaalne investeerimisnõuanne. Kontrolli enne otsust algandmeid ja ettevõtte finantse.")


# =============================================================================
# 6. MAIN ROUTER & EXECUTION
# =============================================================================

st.markdown(
    f'<div class="hero-container">'
    f'<div class="main-title">🚀 X-Market & Neural Intelligence Pro ({CURRENT_YEAR})</div>'
    f'<div class="sub-title">Autonoomne ja investorite tasemel andmeskänner: Mõlema Facebooki grupi koondvoog, Hange.ee ja garaažid</div>'
    f'</div>',
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
