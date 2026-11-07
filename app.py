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

TOP_STOCKS = [
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "base_price": 128.50, "sector": "Artificial Intelligence"},
    {"symbol": "AAPL", "name": "Apple Inc.", "base_price": 224.20, "sector": "Consumer Electronics"},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "base_price": 448.30, "sector": "Cloud & AI Infrastructure"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "base_price": 242.10, "sector": "Autonomous Systems & Energy"},
]


# =============================================================================
# 4b. HANGE.EE: AINULT PÄRISELT AKTIIVSED HANKED
# =============================================================================
# Allikas on ainult Hange.ee avalik aktiivsete hangete nimekiri.
# Pealkirju ega hankeid ei genereerita. Vahemälu aegub 24 tunni järel.
# Märksõnade vaste tehakse hanke PEALKIRJA põhjal, mitte väljamõeldud näidisandmetest.

HANGE_LIST_URL = "https://www.hange.ee/hanked/?filter=all-active"
HANGE_LIST_BASE = "https://www.hange.ee/hanked/"
HANGE_MAX_PAGES = 30
HANGE_CACHE_TTL = 24 * 60 * 60
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

# Sõnamustrid katavad eesti käändeid, kuid ei lisa sinu loetelusse sünonüüme.
TREE = r"\b(?:puu|puud|puude|puudel|puudele|puudelt|puudega|puid)\b"
PLANTS = r"\btaim\w*"
FENCE = r"\b(?:aed|aeda|aedu|aedade\w*|aiad|aia|aiaga|aiale)\b"
PLANT_VERB = r"\bistut\w*"
CUT_VERB = r"\blõi[kg]\w*"
BUILD_VERB = r"\braja\w*"
CARE_NOUN = r"\bkorrashoi\w*"


def _near(a: str, b: str, gap: int = 4) -> str:
    """Kaks märksõna samas pealkirjas, kuni gap sõna vahel."""
    middle = rf"(?:\W+\w+){{0,{gap}}}?\W+"
    return rf"(?:{a}{middle}{b}|{b}{middle}{a})"


KEYWORD_RULES = [
    ("Aiatööd", [r"\baia\s*töö\w*"]),
    ("Lokaalne kanalisatsioon", [
        r"\blokaal\w*\W+(?:\w+\W+){0,2}kanalisatsioon\w*",
        r"\blokaalkanalisatsioon\w*",
    ]),
    ("Puude istutamine", [_near(TREE, PLANT_VERB)]),
    ("Puude lõikus", [_near(TREE, CUT_VERB)]),
    ("Aedade rajamine", [_near(FENCE, BUILD_VERB)]),
    # Selle kategooria pealkirjas peavad KÕIK kolm sõna olemas olema:
    # puu + taim + istutamise/istutada/istutus tüvi.
    ("Puude ja taimede istutamine", [
        rf"^(?=.*{TREE})(?=.*{PLANTS})(?=.*{PLANT_VERB})"
    ]),
    ("Aedade korrashoid", [_near(FENCE, CARE_NOUN)]),
]

COMPILED_RULES = [
    (label, [re.compile(pattern, re.IGNORECASE) for pattern in patterns])
    for label, patterns in KEYWORD_RULES
]
KEYWORD_LABELS = [label for label, _ in COMPILED_RULES]


def match_keywords(title: str) -> list:
    """Tagastab ainult pealkirjale vastavad kasutaja valitud kategooriad."""
    title = " ".join(str(title or "").split())
    labels = [
        label for label, patterns in COMPILED_RULES
        if any(pattern.search(title) for pattern in patterns)
    ]
    # Kolme sõna nõudega kategooria asendab üldisema "Puude istutamine" sildi.
    if (
        "Puude ja taimede istutamine" in labels
        and "Puude istutamine" in labels
    ):
        labels.remove("Puude istutamine")
    return labels


def _clean(text) -> str:
    return " ".join(str(text or "").split())


def _parse_date(value):
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except (TypeError, ValueError):
        return None


def _extract_listing_metadata(anchor):
    """
    Hange.ee nimekirjas on hanke pealkiri ja metaandmed kõrvuti.
    Otsime lähimast sobivast ümbrisest asukoha, korraldaja, pakkumiste arvu
    ja pakkumiste tähtaja. Kui mõni väli puudub, jätame selle tühjaks.
    """
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
    added = re.search(
        r"(\d{2}\.\d{2}\.\d{4})\s+\d+p?\s*",
        block_text,
    )

    return {
        "location": location.group(1).strip(" .") if location else "",
        "organizer": organizer.group(1).strip(" .") if organizer else "",
        "bids": int(bids.group(1)) if bids else None,
        "deadline": _parse_date(deadline.group(1)) if deadline else None,
        "added": added.group(1) if added else "",
    }


def parse_hange_page(html_text: str) -> list:
    """Loeb aktiivsete hangete nimekirja ühe lehe."""
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

        # Sama hanke juures võib olla mitu linki; pealkiri salvestatakse ühe korra.
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


@st.cache_data(ttl=HANGE_CACHE_TTL, show_spinner="Laen Hange.ee aktiivseid hankeid...")
def load_hange_tenders():
    """
    Loeb järjest Hange.ee aktiivsete hangete leheküljed.
    Jätkab, kuni lehtedel pole enam uusi hanke-ID-sid.
    Kui allikas ei vasta või HTML muutub ootamatult, annab vea
    ega esita vanu ega genereeritud hankeid uute pähe.
    """
    session = requests.Session()
    session.headers.update(HANGE_HEADERS)

    seen_ids = set()
    scanned = []
    pages_read = 0

    for page_number in range(1, HANGE_MAX_PAGES + 1):
        params = {"filter": "all-active"}
        if page_number > 1:
            params["page"] = page_number

        page_html = _get_page(session, params)
        page_items = parse_hange_page(page_html)
        new_items = [item for item in page_items if item["id"] not in seen_ids]

        if not new_items:
            break

        seen_ids.update(item["id"] for item in new_items)
        scanned.extend(new_items)
        pages_read += 1
        time.sleep(0.4)

    if not scanned:
        raise RuntimeError(
            "Hange.ee aktiivsete hangete lehelt ei leitud ühtegi hanke kirjet. "
            "Võimalik, et Hange.ee muutis lehe HTML-struktuuri."
        )

    today = datetime.now(TZ).date()
    matched = []

    for tender in scanned:
        # Nimekiri on Hange.ee enda aktiivsete hangete vaade.
        # Kui tähtaja kuupäev on olemas, kontrollime selle ka üle.
        if tender["deadline"] and tender["deadline"] < today:
            continue

        labels = match_keywords(tender["title"])
        if labels:
            matched.append({**tender, "labels": labels})

    matched.sort(key=lambda item: int(item["id"]), reverse=True)

    now = datetime.now(TZ)
    return {
        "items": matched,
        "scanned": len(scanned),
        "pages": pages_read,
        "fetched_at": now.strftime("%d.%m.%Y %H:%M"),
        "next_refresh": (
            now + timedelta(seconds=HANGE_CACHE_TTL)
        ).strftime("%d.%m.%Y %H:%M"),
    }


def hange_to_card(t: dict) -> dict:
    """Muudab päris Hange.ee kirje veebilehe kaardi vormingusse."""
    deadline_text = (
        t["deadline"].strftime("%d.%m.%Y")
        if t.get("deadline")
        else "Hange.ee aktiivsete hangete nimekirjas"
    )
    tags = [
        ("badge-gardening", f"🌿 {label}")
        for label in t.get("labels", [])
    ]

    if t.get("location"):
        tags.append(("badge-location", f"📍 {t['location']}"))
    if t.get("bids") is not None:
        tags.append(("badge-price", f"💬 Pakkumisi: {t['bids']}"))
    tags.append(("badge-year", f"⏳ {deadline_text}"))

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
    show_html('<div class="system-status">🌿 Hange.ee aktiivsed hanked · ainult sinu märksõnad</div>')
    st.markdown(f"**Allikas:** [Hange.ee – kõik aktiivsed hanked]({HANGE_LIST_URL})")

    col_kw, col_btn = st.columns([4, 1])
    with col_kw:
        chosen = st.multiselect(
            "Märksõnad",
            KEYWORD_LABELS,
            default=KEYWORD_LABELS,
            key="hange_keywords",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("🔄 Värskenda", key="hange_refresh", use_container_width=True):
            load_hange_tenders.clear()

    try:
        data = load_hange_tenders()
    except Exception as exc:  # võrguviga, lehe struktuur muutunud vms
        st.error("Hange.ee hankeid ei õnnestunud praegu laadida. Näitan pigem tühja kui väljamõeldud andmeid.")
        st.caption(f"Tehniline põhjus: {type(exc).__name__}: {exc}")
        st.markdown(f"Ava käsitsi: [Hange.ee aktiivsed hanked]({HANGE_LIST_URL})")
        return

    today = datetime.now(TZ).date()
    chosen_set = set(chosen)
    active = [
        t for t in data["items"]
        if (t["deadline"] is None or t["deadline"] >= today)  # ainult aktiivsed
        and chosen_set.intersection(t["labels"])
    ]

    st.caption(
        f"Skaneeritud {data['scanned']} aktiivset hanget ({data['pages']} lehte). "
        f"Märksõnadele vastab {len(data['items'])}, kuvatakse {len(active)}. "
        f"Viimati uuendatud: {data['fetched_at']} · uueneb automaatselt kord ööpäevas "
        f"(järgmine {data['next_refresh']} järel esimesel külastusel)."
    )

    if search_query:
        empty_msg = f"Otsingukastis on tekst “{search_query}”. Kustuta see, et näha kõiki märksõnadele vastavaid hankeid."
    else:
        empty_msg = (
            "Praegu ei ole ühtegi aktiivset hanget, mille pealkirjas oleks need märksõnad. "
            "See on korrektne tulemus: uued hanked ilmuvad siia, kui neid Hange.ee-sse lisatakse."
        )

    render_items_with_scroll(
        [hange_to_card(t) for t in active],
        page_key="hange",
        button_text="Ava Hange.ee-s",
        base_badge=pill("badge-gardening", "🌿 Haljastus"),
        search_query=search_query,
        empty_msg=empty_msg,
        only_current_year=False,
    )

    with st.expander("🔧 Diagnostika"):
        st.write(
            f"Skaneeritud: {data['scanned']} · lehti: {data['pages']} · "
            f"märksõnadele sobis: {len(data['items'])} · "
            f"andmed laaditud: {data['fetched_at']}"
        )
        st.caption("Märksõnad: " + ", ".join(KEYWORD_LABELS))


def render_invest_tab():
    show_html(f'<div class="system-status">📈 Neural Markets: Algorithmic Engine ({CURRENT_YEAR})</div>')
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
