"""AI Kuulutuste Skänner Pro

Sõltuvused (requirements.txt):
    streamlit
    streamlit-autorefresh
    requests
    beautifulsoup4
    lxml
    pandas
    tzdata
"""

import csv
import html
import io
import json
import os
import re
import urllib.parse
from collections import Counter
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
from packaging.version import Version
from bs4 import BeautifulSoup, FeatureNotFound
from streamlit_autorefresh import st_autorefresh


# =============================================================================
# 1. SEADISTUS
# =============================================================================

st.set_page_config(
    page_title="AI Kuulutuste Skänner Pro",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Leht uuendub iga 60 sekundi järel (andmed tulevad vahemälust, vt TTL-id).
st_autorefresh(interval=60_000, key="smart_live_refresh")

TZ = ZoneInfo("Europe/Tallinn")

# Uuemates Streamliti versioonides on `use_container_width` aegunud ja asendatud
# `width="stretch"`-iga. See valib sobiva variandi paigaldatud versiooni järgi.
try:
    STRETCH = (
        {"width": "stretch"}
        if Version(st.__version__) >= Version("1.50")
        else {"use_container_width": True}
    )
except Exception:
    STRETCH = {"use_container_width": True}

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*",
}

MAX_LIMIT = 50
PAGE_INCREMENT = 25
REQUEST_TIMEOUT = 15
FEED_TTL = 900   # RSS-voogude vahemälu (sekundit)
PRICE_TTL = 300  # hindade vahemälu (sekundit)

FB_FEED_URL = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
GARAGE_FEED_URL = "https://rss.app/feeds/MjiyNEAjjPzTGkVZ.xml"
# Hange.ee kategooria "aia-ehitus" (https://www.hange.ee/hanked/?category=aia-ehitus).
HANGE_FEED_URL = "https://rss.app/feeds/Kk2a3NlHMBN8YOGy.xml"
HANGE_SOURCE_URL = "https://www.hange.ee/hanked/?category=aia-ehitus"

PORTFOLIO_FILE = Path(__file__).with_name("portfell.json")

TAB_FREE = "🎁 Tasuta asjad"
TAB_GARAGES = "🚘 Kinnisvara garaažid"
TAB_GARDEN = "🌿 Aiatööd (Hange.ee)"
TAB_FOOD = "🛒 Toidukaubad"
TAB_INVEST = "📈 Lightyear Investeeringud"
TABS = [TAB_FREE, TAB_GARAGES, TAB_GARDEN, TAB_FOOD, TAB_INVEST]


def stem_regex(stems):
    """Regex, mis sobib sõna ALGUSEGA ('aia' leiab 'aiatööd', aga mitte 'kaiaga')."""
    return re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(s) for s in stems) + ")",
        re.IGNORECASE,
    )


# Hange.ee kategooriad, mis loetakse aiatöödeks (kontrollitakse esimesena).
GARDEN_CATEGORY_RE = stem_regex([
    "aia", "haljast", "muru", "maastik", "puude", "puuhooldus",
    "raie", "õuealad", "territoorium", "piirde", "sillut",
])
# Märksõnad pealkirjas/kirjelduses, kui kategooria ei ütle midagi.
GARDEN_KEYWORD_RE = stem_regex([
    "aia", "haljast", "muru", "hekk", "heki", "viljapuu", "istut",
    "lillepeenar", "trimmer", "lehte", "multš", "freesi", "põõsa",
    "raie", "raiu", "võsa", "kiviparkett", "terrass", "õue",
    "puu lõik", "puude", "kasvuhoone", "piirdeaed",
])
# Välistavad märksõnad (kontrollitakse ainult pealkirjast ja kategooriast).
GARDEN_FORBIDDEN_RE = stem_regex([
    "veearvesti", "termostaat", "mullivann", "vannituba", "vannitoa",
    "sanitaartehn", "katus", "vundament", "torutöö", "elektritöö",
    "siseviimistlus", "plaatimine", "maalritöö", "fassaad", "betoon",
    "korteri", "pesumasin", "külmkapp", "pliit", "köögi", "kipsi",
])


def is_garden(title, description, category):
    if category and GARDEN_CATEGORY_RE.search(category):
        return True
    if GARDEN_FORBIDDEN_RE.search(f"{title} {category}"):
        return False
    return bool(GARDEN_KEYWORD_RE.search(f"{title} {description}"))


DARK_MODE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
.stApp { background-color: #0b0f19; color: #f8fafc; }
.hero-container {
    padding: 1.5rem 2rem;
    background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
    border: 1px solid #374151;
    border-radius: 20px;
    margin-bottom: 2rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.main-title { font-size: 2.4rem; font-weight: 800; color: #f8fafc; margin-bottom: 0.3rem; letter-spacing: -0.5px; }
.sub-title { font-size: 1rem; color: #94a3b8; font-weight: 500; }
.pro-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 18px;
    box-shadow: 0 6px 24px rgba(0,0,0,0.4);
    transition: all 0.25s ease;
}
.pro-card:hover { transform: translateY(-3px); border-color: #4b5563; box-shadow: 0 12px 35px rgba(0,0,0,0.6); }
.card-row { display: flex; gap: 24px; align-items: flex-start; }
.card-img { flex: 0 0 280px; max-width: 280px; }
.card-img img { width: 100%; border-radius: 14px; display: block; object-fit: cover; aspect-ratio: 4 / 3; background-color: #1f2937; }
.card-body { flex: 1; min-width: 0; }
@media (max-width: 768px) {
    .card-row { flex-direction: column; }
    .card-img { flex: none; width: 100%; max-width: 100%; }
}
.card-title { font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin-bottom: 8px; line-height: 1.4; }
.card-date { font-size: 0.825rem; color: #94a3b8; margin-bottom: 12px; font-weight: 500; }
.card-desc { font-size: 0.975rem; color: #cbd5e1; line-height: 1.6; margin-bottom: 20px; }
.card-tags { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
.badge-pill { padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }
.badge-free { background-color: rgba(5,150,105,0.15); color: #34d399; border: 1px solid rgba(5,150,105,0.3); }
.badge-price { background-color: rgba(37,99,235,0.15); color: #60a5fa; border: 1px solid rgba(37,99,235,0.3); }
.badge-location { background-color: rgba(71,85,105,0.2); color: #94a3b8; border: 1px solid rgba(71,85,105,0.4); }
.badge-gardening { background-color: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4); }
.pro-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 100%; box-sizing: border-box; padding: 12px 20px;
    background: #2563eb; color: #ffffff !important;
    font-size: 0.95rem; font-weight: 600; border-radius: 12px;
    text-decoration: none !important; transition: all 0.2s ease;
    box-shadow: 0 4px 12px rgba(37,99,235,0.3);
}
.pro-btn:hover { background: #1d4ed8; box-shadow: 0 6px 20px rgba(37,99,235,0.5); transform: translateY(-1px); }
.pro-btn.secondary { background: #1f2937; border: 1px solid #374151; color: #94a3b8 !important; box-shadow: none; }
.invest-card {
    background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
    border: 1px solid #374151; border-radius: 18px;
    padding: 24px; margin-bottom: 20px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.4);
}
.metric-big { font-size: 2.5rem; font-weight: 800; color: #f8fafc; letter-spacing: -1px; }
.refresh-badge {
    background: #1e293b; border: 1px solid #334155;
    padding: 8px 14px; border-radius: 10px;
    font-size: 0.85rem; color: #94a3b8;
    display: inline-block; margin-bottom: 15px;
}
</style>
"""


# =============================================================================
# 2. ÜLDISED ABIFUNKTSIOONID
# =============================================================================

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def show_html(markup: str):
    """Renderda HTML Streamlitis.

    Markdown tõlgendab 4+ tühikuga taandatud ridu koodiplokina ja tühi rida
    lõpetab HTML-ploki, seepärast eemaldame taanded ja tühjad read.
    """
    cleaned = "\n".join(
        line.strip() for line in markup.splitlines() if line.strip()
    )
    st.markdown(cleaned, unsafe_allow_html=True)


def safe_http_url(value, base_url=None):
    """Tagastab ainult korrektse HTTP/HTTPS URL-i."""
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


def to_float(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if number != number else number  # NaN -> 0


def pill(css_class, text):
    return f'<span class="badge-pill {css_class}">{esc(text)}</span>'


def paginate_items(items, category_key):
    items = list(items)[:MAX_LIMIT]
    total = len(items)
    count_key = f"visible_count_{category_key}"

    if count_key not in st.session_state:
        st.session_state[count_key] = PAGE_INCREMENT

    visible_count = min(total, max(0, int(st.session_state[count_key])))

    st.caption(
        f"Leitud {total} kirjet · Näitan praegu {visible_count} "
        f"(maksimaalselt {MAX_LIMIT})."
    )

    if visible_count < total:
        remaining = total - visible_count
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button(
                f"Näita veel {min(PAGE_INCREMENT, remaining)}",
                key=f"load_more_{category_key}",
            ):
                st.session_state[count_key] = min(total, visible_count + PAGE_INCREMENT)
                st.rerun()
        with c2:
            if st.button(f"Näita kõiki ({total})", key=f"show_all_{category_key}"):
                st.session_state[count_key] = total
                st.rerun()

    return items[:visible_count]


def render_card(item, button_text, badges=""):
    link = safe_http_url(item.get("link"))
    img_url = safe_http_url(item.get("image"))

    img_html = ""
    if img_url:
        img_html = (
            '<div class="card-img">'
            f'<img src="{esc(img_url)}" loading="lazy" decoding="async" '
            f'referrerpolicy="no-referrer" alt="{esc(item.get("title", "Kuulutuse pilt"))}">'
            "</div>"
        )

    date_html = (
        f'<div class="card-date">{esc(item["date_str"])}</div>'
        if item.get("date_str")
        else ""
    )
    desc_html = (
        f'<div class="card-desc">{esc(item["description"])}</div>'
        if item.get("description")
        else ""
    )
    tags_html = f'<div class="card-tags">{badges}</div>' if badges else ""

    if link:
        button_html = (
            f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer" '
            f'class="pro-btn">{esc(button_text)}</a>'
        )
    else:
        button_html = '<span class="pro-btn secondary">Link puudub</span>'

    show_html(
        f"""
        <div class="pro-card">
          <div class="card-row">
            {img_html}
            <div class="card-body">
              <div class="card-title">{esc(item.get("title", "Kuulutus"))}</div>
              {date_html}
              {desc_html}
              {tags_html}
              {button_html}
            </div>
          </div>
        </div>
        """
    )


# =============================================================================
# 3. RSS-I PARSIMINE
# =============================================================================

def local_name(tag):
    """'media:thumbnail' -> 'thumbnail'."""
    return (getattr(tag, "name", "") or "").split(":")[-1].lower()


BLOCKED_URL_PARTS = (
    "pixel", "tracking", "spacer", "blank", "transparent.gif",
    "placeholder", "default-avatar", "favicon", "logo.svg",
)
BLOCKED_PATH_PARTS = ("/avatar/", "/avatars/", "/icons/")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp")


def usable_image_url(value, base_url=None, allow_extensionless=False):
    url = safe_http_url(value, base_url=base_url)
    if not url:
        return None
    lower_url = url.lower()
    path = urllib.parse.urlsplit(url).path.lower()
    if any(part in lower_url for part in BLOCKED_URL_PARTS):
        return None
    if any(part in path for part in BLOCKED_PATH_PARTS):
        return None
    if path.endswith(IMAGE_EXTENSIONS) or allow_extensionless:
        return url
    return None


def best_srcset_url(srcset):
    variants = []
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        width = 0
        if len(bits) > 1:
            m = re.search(r"(\d+)w", bits[1])
            if m:
                width = int(m.group(1))
        variants.append((width, bits[0]))
    return max(variants, key=lambda v: v[0])[1] if variants else None


def extract_real_image_details(entry, base_url=None):
    """Leia pilt ainult selle konkreetse RSS-kirje seest."""
    candidates = []
    seen = set()

    def add(url, source, allow_extensionless=False):
        resolved = usable_image_url(url, base_url, allow_extensionless)
        if resolved and resolved not in seen:
            seen.add(resolved)
            candidates.append({"url": resolved, "source": source})

    all_tags = entry.find_all(True)

    for tag in all_tags:
        if local_name(tag) != "content" or (tag.name or "").lower() == "content:encoded":
            continue
        mime = str(tag.get("type", "")).lower().strip()
        medium = str(tag.get("medium", "")).lower().strip()
        if mime.startswith("image/") or medium == "image":
            add(tag.get("url"), "media:content", allow_extensionless=True)

    for tag in all_tags:
        if local_name(tag) == "thumbnail":
            add(tag.get("url"), "media:thumbnail", allow_extensionless=True)

    for tag in all_tags:
        if local_name(tag) != "enclosure":
            continue
        mime = str(tag.get("type", "")).lower().strip()
        if mime.startswith("image/"):
            add(tag.get("url"), "image enclosure", allow_extensionless=True)
        elif not mime:
            add(tag.get("url"), "image enclosure")

    html_tags = [
        tag for tag in all_tags
        if local_name(tag) in {"description", "summary", "encoded"}
        or (local_name(tag) == "content" and not tag.get("url"))  # Atom <content>
    ]
    for tag in html_tags:
        raw_html = "".join(str(child) for child in tag.contents) or tag.get_text("")
        for img in BeautifulSoup(raw_html, "html.parser").find_all("img"):
            src = (
                img.get("data-original")
                or img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("src")
            )
            add(src, "description img", allow_extensionless=True)
            srcset = img.get("data-srcset") or img.get("srcset") or ""
            if srcset:
                add(best_srcset_url(srcset), "description srcset", allow_extensionless=True)

    return candidates[0] if candidates else {"url": None, "source": "puudub"}


def extract_entry_link(entry, base_url=None):
    link_tag = entry.find("link")
    if not link_tag:
        return None
    href = link_tag.get("href")  # Atom
    if href:
        return safe_http_url(href, base_url=base_url)
    return safe_http_url(link_tag.get_text(" ", strip=True), base_url=base_url)  # RSS


def extract_entry_text(entry, tag_names):
    for tag in entry.find_all(True):
        if local_name(tag) in tag_names:
            raw = "".join(str(child) for child in tag.contents) or tag.get_text(" ", strip=True)
            text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
            return " ".join(text.split())
    return ""


def extract_entry_date(entry):
    """Tagastab kuupäeva Eesti ajas (või tühja stringi)."""
    for tag in entry.find_all(True):
        if local_name(tag) not in {"pubdate", "published", "updated", "date"}:
            continue
        text = tag.get_text(strip=True)
        if not text:
            continue
        try:
            dt = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        midnight = dt.hour == 0 and dt.minute == 0 and dt.second == 0
        local = dt.astimezone(TZ)
        return local.strftime("%d.%m.%Y") if midnight else local.strftime("%d.%m.%Y %H:%M")
    return ""


# Hange.ee voo kirjeldus on kujul:
# "Keskmine hind 6 500€ pakkujaid 1. Vannitubade remont: tekst... Vaata kõiki ..."
HANGE_META_RE = re.compile(
    r"Keskmine hind\s+(?P<price>[\d\s.,]*?)\s*€\s*pakkujaid\s+(?P<bids>\d+)\."
    r"\s*(?:(?P<category>[^:]{2,80}?):)?\s*(?P<text>.*)",
    re.DOTALL,
)
HANGE_TRAILER_RE = re.compile(r"\s*Vaata kõiki pakkumisi ja hindu meie keskkonnas\.?\s*$")


@st.cache_data(ttl=FEED_TTL, show_spinner=False)
def load_feed(feed_url, kind):
    """Loeb RSS/Atom voo.

    kind: 'standard' (ilma filtrita) või 'gardening' (aiatööde filter).
    Vea korral visatakse erand, seega ebaõnnestunud päringut ei cache'ita.
    Tagastab {'items': [...], 'meta': {...}}.
    """
    feed_url = safe_http_url(feed_url)
    if not feed_url:
        raise ValueError("Vigane RSS-voo URL.")

    response = requests.get(feed_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    try:
        soup = BeautifulSoup(response.content, "xml")
    except FeatureNotFound:
        raise RuntimeError(
            "XML-parser puudub. Paigalda lxml: `python -m pip install lxml` "
            "(Streamlit Cloudis lisa `lxml` faili requirements.txt) ja käivita "
            "rakendus uuesti."
        ) from None

    container = soup.find("channel") or soup.find("feed")
    channel_title = ""
    if container:
        title_tag = container.find("title", recursive=False)
        channel_title = title_tag.get_text(" ", strip=True) if title_tag else ""

    entries = soup.find_all(["item", "entry"])
    categories = Counter()
    results = []
    seen_links = set()

    for entry in entries:
        title = extract_entry_text(entry, {"title"}) or "Kirje"
        description = extract_entry_text(entry, {"description", "summary", "encoded"})

        category = ""
        tags = []
        meta = HANGE_META_RE.match(description)
        if meta:
            category = (meta["category"] or "").strip()
            description = HANGE_TRAILER_RE.sub("", meta["text"]).strip()
            price = re.sub(r"\s+", " ", meta["price"]).strip()
            if category:
                tags.append(("badge-location", f"🏷️ {category}"))
            if price and price != "0":
                tags.append(("badge-price", f"💶 Keskmine hind {price} €"))
            tags.append(("badge-location", f"👥 Pakkujaid: {int(meta['bids'])}"))

        categories[category or "(kategooriat ei tuvastatud)"] += 1

        if kind == "gardening" and not is_garden(title, description, category):
            continue
        if len(results) >= MAX_LIMIT:
            continue

        link = extract_entry_link(entry, base_url=feed_url)
        if link and link in seen_links:
            continue
        if link:
            seen_links.add(link)

        image = extract_real_image_details(entry, base_url=link or feed_url)
        date = extract_entry_date(entry)

        results.append(
            {
                "title": title,
                "description": description[:200] + ("..." if len(description) > 200 else ""),
                "link": link,
                "image": image["url"],
                "image_source": image["source"],
                "date_str": f"📅 {date}" if date else "",
                "tags": tags,
            }
        )

    return {
        "items": results,
        "meta": {
            "channel_title": channel_title,
            "total": len(entries),
            "kept": len(results),
            "categories": dict(categories),
        },
    }


def get_feed(feed_url, kind):
    """Laeb voo ja näitab vea korral hoiatuse. Tagastab alati sõnastiku."""
    empty = {"items": [], "meta": {"channel_title": "", "total": 0, "kept": 0, "categories": {}}}
    try:
        return load_feed(feed_url, kind)
    except requests.RequestException as exc:
        st.warning(f"RSS-voo laadimine ebaõnnestus: {exc}")
    except Exception as exc:
        st.warning(f"RSS-andmete töötlemisel tekkis viga: {exc}")
    return empty


# =============================================================================
# 4. KUULUTUSTE VAATED
# =============================================================================

def render_items(items, *, page_key, button_text, base_badge, search_query,
                 empty_msg):
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


def render_feed_tab(*, feed_url, source_md, badge_text, pill_class, button_text,
                    empty_msg, page_key, search_query):
    show_html(
        '<div class="refresh-badge">⏱️ Leht uuendub iga 1 min, '
        "voo andmed vahemälus 15 min</div>"
    )
    st.markdown(f"**Allikas:** {source_md}")

    data = get_feed(feed_url, "standard")
    render_items(
        data["items"], page_key=page_key, button_text=button_text,
        base_badge=pill(pill_class, badge_text), search_query=search_query,
        empty_msg=empty_msg,
    )


def render_garden_tab(search_query):
    show_html('<div class="refresh-badge">⏱️ Aiatööde voog: vahemälu 15 min</div>')
    st.markdown(f"**Allikas:** [Hange.ee – aia ehitus]({HANGE_SOURCE_URL})")

    data = get_feed(HANGE_FEED_URL, "gardening")
    meta = data["meta"]

    if meta["total"] > 0 and meta["kept"] == 0:
        st.warning(
            f"Voos on {meta['total']} kirjet, aga ükski ei ole aiatöö. "
            "Kontrolli, et HANGE_FEED_URL viitab Hange.ee aiatööde kategooria voole."
        )
    elif meta["total"] == 0:
        st.info("Voos ei ole ühtegi kirjet.")

    render_items(
        data["items"], page_key="hange", button_text="Vaata Hange.ee keskkonnas",
        base_badge=pill("badge-gardening", "🌿 Aiatöö / Haljastus"),
        search_query=search_query,
        empty_msg="Sobivaid aiatööde hankeid praegu ei leitud.",
    )


GROCERIES = [
    ("Banaanid (kg)", "0.99", "Lidl", "https://www.lidl.ee", "photo-1571771894821-ce9b6c11b08e"),
    ("Värske piim 2.5% (1 l)", "0.69", "Prisma", "https://www.prisma.ee", "photo-1550583724-b2692b85b150"),
    ("Sea välisfilee (kg)", "5.99", "Rimi", "https://www.rimi.ee", "photo-1603048588665-791ca8aea617"),
    ("Kohviuba President (1 kg)", "9.99", "Selver", "https://www.selver.ee", "photo-1559056199-641a0ac8b55e"),
    ("Eesti või 82% (200 g)", "1.89", "Coop", "https://www.coop.ee", "photo-1589985270826-4b7bb135bc9d"),
    ("Värske kurk (kg)", "2.49", "Maxima", "https://www.maxima.ee", "photo-1449300079323-02e209d9d3a6"),
    ("Hapukoor 20% (500 g)", "0.95", "Rimi", "https://www.rimi.ee", "photo-1488477181946-6428a0291777"),
    ("Broilerifilee (kg)", "6.49", "Selver", "https://www.selver.ee", "photo-1604503468506-a8da13d82791"),
    ("Juust Edam (400 g)", "3.29", "Coop", "https://www.coop.ee", "photo-1486297678162-eb2a19b0a32d"),
    ("Kartul (5 kg kott)", "2.99", "Lidl", "https://www.lidl.ee", "photo-1518977676601-b53f82aba655"),
    ("Muna M (10 tk)", "1.79", "Prisma", "https://www.prisma.ee", "photo-1516448620398-c5f44bf9f441"),
    ("Apelsinimahl 100% (1.5 l)", "1.99", "Maxima", "https://www.maxima.ee", "photo-1613478223719-2ab802602423"),
]


def render_food_sample(search_query):
    show_html('<div class="refresh-badge">ℹ️ Näidisandmed – mitte reaalajas poehinnad</div>')
    st.warning(
        "Allolevad hinnad ja pakkumised on näidisandmed. "
        "Neid ei tohi käsitleda kaupluste täna kinnitatud hindadena."
    )
    st.info(
        "Päris hindade (Selver, Rimi) jaoks lisa Streamlit Cloudis "
        "Manage app → Settings → Secrets rida `APIFY_TOKEN = \"...\"`."
    )

    stores = ["Kõik"] + sorted({g[2] for g in GROCERIES})
    store_filter = st.selectbox("Filtreeri kaupluse järgi:", stores)

    items = [
        {
            "title": title,
            "description": "Näidistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": f"{price} € (näidis)",
            "store": store,
            "link": link,
            "image": f"https://images.unsplash.com/{photo}?w=600&auto=format&fit=crop",
        }
        for title, price, store, link, photo in GROCERIES
    ]

    filtered = [
        it for it in items
        if (store_filter == "Kõik" or it["store"] == store_filter)
        and matches(search_query, it["title"], it["description"], it["store"])
    ]

    if not filtered:
        st.info("Sobivaid tooteid ei leitud.")

    for item in paginate_items(filtered, "groceries"):
        badges = pill("badge-price", f"🏷️ {item['price']}") + pill(
            "badge-location", f"📍 {item['store']}"
        )
        render_card(item, "Ava kaupluse veebileht", badges=badges)


# --- Päris poehinnad -------------------------------------------------------
# Eesti kauplusteketid ei paku avalikku hinna-API-t. Siin kasutatakse kolmanda
# osapoole skraperit Apify platvormil (tasuline, vt aktori lehte). Vajalik on
# Apify API token, mis tuleb panna Streamlit Cloudi Secrets'isse (APIFY_TOKEN)
# või keskkonnamuutujasse; tokenit ei tohi GitHubi panna.

GROCERY_TTL = 3600       # sekundit; sama otsing ei maksa uuesti
GROCERY_PER_STORE = 20   # tulemusi poe kohta
APIFY_RUN_URL = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"

APIFY_ACTORS = {
    "Selver": {
        "actor": "studio-amba~selver-ee-scraper",
        "build_input": lambda q, n: {
            "searchQuery": q, "maxResults": n, "language": "et",
        },
    },
    "Rimi": {
        "actor": "studio-amba~rimi-ee-scraper",
        "build_input": lambda q, n: {
            "searchQuery": q, "maxResults": n,
            "proxyConfiguration": {"useApifyProxy": True},
        },
    },
}


def get_apify_token():
    try:
        token = st.secrets.get("APIFY_TOKEN")
    except Exception:  # secrets-faili pole
        token = None
    return token or os.environ.get("APIFY_TOKEN")


def parse_price(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"\d+(?:[.,]\d+)?", value)
        if match:
            return float(match.group(0).replace(",", "."))
    return None


def normalize_product(raw, store):
    """Teisendab skraperi kirje rakenduse kaardi kujule."""
    name = str(raw.get("name") or "").strip()
    price = parse_price(raw.get("price"))
    if not name or price is None:
        return None

    tags = [("badge-price", f"💶 {price:.2f} €")]

    original = parse_price(raw.get("originalPrice"))
    if original and original > price:
        discount = str(raw.get("discount") or "").strip()
        tags.append(
            ("badge-free", f"🔻 Oli {original:.2f} €" + (f" ({discount})" if discount else ""))
        )

    unit = raw.get("pricePerUnit") or raw.get("unitPrice")
    if isinstance(unit, (int, float)) and not isinstance(unit, bool):
        unit_text = f"{float(unit):.2f} €"  # Selver ei anna ühikut eraldi
    else:
        unit_text = str(unit or "").strip()
    if unit_text:
        tags.append(("badge-location", f"⚖️ Võrdlushind {unit_text}"))

    tags.append(("badge-location", f"📍 {store}"))
    if raw.get("inStock") is False:
        tags.append(("badge-location", "❌ Otsas"))

    details = [str(raw.get(k) or "").strip() for k in ("brand", "packSize", "countryOfOrigin")]

    date_str = ""
    scraped = str(raw.get("scrapedAt") or "")
    if scraped:
        try:
            dt = datetime.fromisoformat(scraped.replace("Z", "+00:00"))
            date_str = "📅 Hind seisuga " + dt.astimezone(TZ).strftime("%d.%m.%Y %H:%M")
        except ValueError:
            pass

    return {
        "title": name,
        "description": " · ".join(d for d in details if d),
        "price": price,
        "store": store,
        "link": raw.get("url"),
        "image": raw.get("imageUrl"),
        "date_str": date_str,
        "tags": tags,
    }


@st.cache_data(ttl=GROCERY_TTL, show_spinner=False)
def fetch_store_products(store, query, limit):
    """Käivitab poe skraperi ja ootab tulemust. Vea korral ei cache'ita."""
    token = get_apify_token()
    if not token:
        raise RuntimeError("APIFY_TOKEN puudub.")

    cfg = APIFY_ACTORS[store]
    response = requests.post(
        APIFY_RUN_URL.format(actor=cfg["actor"]),
        params={"timeout": 120, "maxTotalChargeUsd": 0.25},
        json=cfg["build_input"](query, limit),
        headers={"Authorization": f"Bearer {token}"},
        timeout=150,
    )
    if response.status_code in (401, 403):
        raise RuntimeError("Apify lükkas päringu tagasi, kontrolli APIFY_TOKEN-it.")
    response.raise_for_status()

    rows = response.json()
    if not isinstance(rows, list):
        raise RuntimeError("Apify andis ootamatu vastuse.")
    products = (normalize_product(r, store) for r in rows if isinstance(r, dict))
    return [p for p in products if p]


def render_food_live():
    show_html(
        '<div class="refresh-badge">ℹ️ Päris hinnad Selverist ja Rimist · '
        "vahemälu 1 h</div>"
    )
    st.caption(
        "Andmed tulevad kolmanda osapoole skraperitest (Apify), mitte kaupluste "
        "ametlikest API-dest. Iga uus otsing on tasuline (paar senti poe kohta) "
        "ja võib hilineda või katkeda. Coop, Maxima, Lidl ja Prisma ei ole kaetud."
    )

    with st.form("grocery_search"):
        typed = st.text_input(
            "Toote nimi (eesti keeles)",
            value=st.session_state.get("grocery_query", ""),
            placeholder="nt piim, leib, juust, kohv",
        )
        submitted = st.form_submit_button("🔎 Otsi hindu")
    if submitted:
        st.session_state["grocery_query"] = typed.strip()
        st.session_state.pop("visible_count_groceries", None)
    query = st.session_state.get("grocery_query", "")

    col_store, col_sort = st.columns(2)
    with col_store:
        store_filter = st.selectbox("Kauplus:", ["Kõik"] + list(APIFY_ACTORS))
    with col_sort:
        sort_by = st.selectbox("Järjesta:", ["Hind: odavam enne", "Hind: kallim enne"])

    if len(query) < 3:
        st.info("Sisesta toote nimi (vähemalt 3 tähte) ja vajuta „Otsi hindu“.")
        return

    stores = list(APIFY_ACTORS) if store_filter == "Kõik" else [store_filter]
    products, errors = [], []
    with st.spinner("Laen hindu..."):
        for store in stores:
            try:
                products += fetch_store_products(store, query, GROCERY_PER_STORE)
            except Exception as exc:
                errors.append(f"{store}: {exc}")

    for message in errors:
        st.warning(message)

    if not products and not errors:
        st.info(f"Otsingule „{query}“ ei leitud tooteid.")

    products.sort(key=lambda p: p["price"], reverse=(sort_by == "Hind: kallim enne"))
    for item in paginate_items(products, "groceries"):
        badges = "".join(pill(css, text) for css, text in item["tags"])
        render_card(item, "Ava toote leht", badges=badges)


def render_food_tab(search_query):
    if get_apify_token():
        render_food_live()
    else:
        render_food_sample(search_query)


# =============================================================================
# 5. PORTFELL (OMA POSITSIOONID + AVALIKUD HINNAD)
# =============================================================================
# Lightyearil ei ole teadaolevalt avalikku arendaja-API-t, mille kaudu rakendus
# saaks sinu kontolt andmeid lugeda. Seepärast sisestad positsioonid ise, hinnad
# tulevad avalikest allikatest: CoinGecko (krüpto), Stooq (aktsiad/ETF-id) ja
# Frankfurter (USD→EUR kurss).

HOLDING_COLUMNS = ["Nimi", "Tüüp", "Sümbol", "Valuuta", "Kogus", "Investeeritud (€)"]
DEFAULT_HOLDINGS = [
    {"Nimi": "NVIDIA", "Tüüp": "Aktsia/ETF", "Sümbol": "nvda.us", "Valuuta": "USD", "Kogus": 0.0, "Investeeritud (€)": 0.0},
    {"Nimi": "NEAR Protocol", "Tüüp": "Krüpto", "Sümbol": "near", "Valuuta": "EUR", "Kogus": 0.0, "Investeeritud (€)": 0.0},
    {"Nimi": "Bitcoin", "Tüüp": "Krüpto", "Sümbol": "bitcoin", "Valuuta": "EUR", "Kogus": 0.0, "Investeeritud (€)": 0.0},
]


def load_holdings():
    try:
        data = json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return pd.DataFrame(data).reindex(columns=HOLDING_COLUMNS)
    except (OSError, ValueError):
        pass
    return pd.DataFrame(DEFAULT_HOLDINGS, columns=HOLDING_COLUMNS)


def save_holdings(df):
    records = df.reindex(columns=HOLDING_COLUMNS).fillna("").to_dict("records")
    PORTFOLIO_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@st.cache_data(ttl=PRICE_TTL, show_spinner=False)
def fetch_crypto_eur(coin_ids):
    """CoinGecko id-de (nt 'bitcoin', 'near') hinnad eurodes."""
    response = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": ",".join(coin_ids), "vs_currencies": "eur"},
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return {cid: float(v["eur"]) for cid, v in response.json().items() if "eur" in v}


@st.cache_data(ttl=PRICE_TTL, show_spinner=False)
def fetch_stooq_close(symbol):
    """Viimane sulgemishind Stoopist (nt 'nvda.us', 'vwce.de')."""
    url = f"https://stooq.com/q/l/?s={urllib.parse.quote(symbol)}&f=sd2t2c&h&e=csv"
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(response.text)))
    raw = (rows[0].get("Close") or "").strip() if rows else ""
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"Stooq ei leidnud hinda sümbolile '{symbol}'.") from None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_usd_eur():
    last_exc = None
    for url in (
        "https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR",
        "https://api.frankfurter.app/latest?from=USD&to=EUR",
    ):
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return float(response.json()["rates"]["EUR"])
        except (requests.RequestException, KeyError, ValueError) as exc:
            last_exc = exc
    raise RuntimeError(f"USD→EUR kursi laadimine ebaõnnestus: {last_exc}")


def value_holdings(df):
    rows, errors = [], []

    crypto_ids = tuple(sorted({
        str(r.get("Sümbol") or "").strip().lower()
        for r in df.to_dict("records")
        if r.get("Tüüp") == "Krüpto" and str(r.get("Sümbol") or "").strip()
    }))
    crypto_prices = {}
    if crypto_ids:
        try:
            crypto_prices = fetch_crypto_eur(crypto_ids)
        except Exception as exc:
            errors.append(f"Krüptohindade laadimine ebaõnnestus: {exc}")

    usd_eur = None
    for rec in df.to_dict("records"):
        name = str(rec.get("Nimi") or "").strip()
        symbol = str(rec.get("Sümbol") or "").strip().lower()
        if not name and not symbol:
            continue

        qty = to_float(rec.get("Kogus"))
        invested = to_float(rec.get("Investeeritud (€)"))
        kind = rec.get("Tüüp") or "Aktsia/ETF"
        currency = rec.get("Valuuta") or "EUR"

        price_eur = None
        try:
            if not symbol:
                raise ValueError("sümbol puudub")
            if kind == "Krüpto":
                price_eur = crypto_prices.get(symbol)
                if price_eur is None:
                    raise ValueError(f"CoinGecko ei leidnud id-d '{symbol}'")
            else:
                price = fetch_stooq_close(symbol)
                if currency == "USD":
                    if usd_eur is None:
                        usd_eur = fetch_usd_eur()
                    price_eur = price * usd_eur
                else:
                    price_eur = price
        except Exception as exc:
            errors.append(f"{name or symbol}: {exc}")

        value = qty * price_eur if price_eur is not None else None
        rows.append(
            {
                "Nimi": name or symbol,
                "Kogus": qty,
                "Hind (€)": price_eur,
                "Väärtus (€)": value,
                "Investeeritud (€)": invested,
                "Tulem (€)": (value - invested) if value is not None else None,
                "Tulem (%)": (
                    (value - invested) / invested * 100
                    if value is not None and invested > 0
                    else None
                ),
            }
        )
    return rows, errors


def render_invest_tab():
    show_html(
        '<div class="refresh-badge">ℹ️ Hinnad avalikest allikatest, '
        "vahemälu 5 min</div>"
    )
    st.markdown("### 💼 Portfelli vaade")
    st.info(
        "Lightyearil ei ole teadaolevalt avalikku arendaja-API-t, seega see rakendus "
        "ei saa sinu kontolt andmeid lugeda. Sisesta oma positsioonid (kogus ja "
        "investeeritud summa Lightyeari rakendusest) allolevasse tabelisse. Hinnad "
        "tulevad avalikest allikatest ja võivad Lightyeari kuvatavast erineda."
    )

    if "holdings_base" not in st.session_state:
        st.session_state["holdings_base"] = load_holdings()

    all_zero = (
        st.session_state["holdings_base"]["Kogus"].fillna(0).astype(float).sum() == 0
    )
    with st.expander("✏️ Muuda positsioone", expanded=all_zero):
        st.caption(
            "Aktsia/ETF: sümbol Stoopi formaadis (nt `nvda.us`, `vwce.de`) ja valuuta "
            "(USD/EUR). Krüpto: CoinGecko id (nt `bitcoin`, `near`). "
            "Muudatused säilivad pärast „Salvesta“ vajutamist."
        )
        edited = st.data_editor(
            st.session_state["holdings_base"],
            num_rows="dynamic",
            **STRETCH,
            hide_index=True,
            key="holdings_editor",
            column_config={
                "Tüüp": st.column_config.SelectboxColumn(
                    "Tüüp", options=["Aktsia/ETF", "Krüpto"], required=True
                ),
                "Valuuta": st.column_config.SelectboxColumn(
                    "Valuuta", options=["EUR", "USD"], required=True
                ),
                "Kogus": st.column_config.NumberColumn(
                    "Kogus", min_value=0.0, format="%.6f"
                ),
                "Investeeritud (€)": st.column_config.NumberColumn(
                    "Investeeritud (€)", min_value=0.0, format="%.2f"
                ),
            },
        )
        if st.button("💾 Salvesta portfell"):
            try:
                save_holdings(edited)
                st.success(f"Salvestatud faili {PORTFOLIO_FILE.name}.")
            except OSError as exc:
                st.error(f"Salvestamine ebaõnnestus: {exc}")

    rows, errors = value_holdings(edited)
    priced = [r for r in rows if r["Väärtus (€)"] is not None]
    total_value = sum(r["Väärtus (€)"] for r in priced)
    invested_priced = sum(r["Investeeritud (€)"] for r in priced)
    pl = total_value - invested_priced
    pl_pct = pl / invested_priced * 100 if invested_priced > 0 else None
    pl_color = "#34d399" if pl >= 0 else "#ef4444"
    pl_arrow = "▲" if pl >= 0 else "▼"
    now = datetime.now(TZ).strftime("%H:%M:%S")

    col1, col2, col3 = st.columns(3)
    with col1:
        value_text = f"€{total_value:,.2f}" if priced else "—"
        show_html(
            f"""
            <div class="invest-card">
              <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:4px;">Portfelli väärtus</div>
              <div class="metric-big">{value_text}</div>
              <div style="font-size:0.8rem;color:#94a3b8;margin-top:4px;">
                Investeeritud (hinnaga positsioonid): €{invested_priced:,.2f}
              </div>
            </div>
            """
        )
    with col2:
        if priced and pl_pct is not None:
            pl_html = (
                f'<div class="metric-big" style="font-size:1.8rem;margin-top:8px;color:{pl_color};">'
                f"{pl_arrow} €{pl:,.2f}</div>"
                f'<div style="font-size:0.8rem;color:{pl_color};margin-top:6px;">{pl_pct:+.2f}%</div>'
            )
        else:
            pl_html = (
                '<div class="metric-big" style="font-size:1.8rem;margin-top:8px;">—</div>'
                '<div style="font-size:0.8rem;color:#94a3b8;margin-top:6px;">'
                "Sisesta kogus ja investeeritud summa</div>"
            )
        show_html(
            f"""
            <div class="invest-card">
              <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:4px;">Kasum / kahjum</div>
              {pl_html}
            </div>
            """
        )
    with col3:
        show_html(
            f"""
            <div class="invest-card">
              <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:4px;">Lehe viimase laadimise aeg</div>
              <div class="metric-big" style="font-size:1.5rem;margin-top:10px;">{now}</div>
              <div style="font-size:0.8rem;color:#60a5fa;margin-top:6px;">Eesti aeg</div>
            </div>
            """
        )

    for message in errors:
        st.warning(message)

    if rows:
        st.markdown("#### 📊 Positsioonid")
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            **STRETCH,
            column_config={
                "Kogus": st.column_config.NumberColumn(format="%.6f"),
                "Hind (€)": st.column_config.NumberColumn(format="%.4f"),
                "Väärtus (€)": st.column_config.NumberColumn(format="%.2f"),
                "Investeeritud (€)": st.column_config.NumberColumn(format="%.2f"),
                "Tulem (€)": st.column_config.NumberColumn(format="%+.2f"),
                "Tulem (%)": st.column_config.NumberColumn(format="%+.2f%%"),
            },
        )

    st.caption(
        "Allikad: CoinGecko, Stooq, Frankfurter (EKP kurss). See ei ole "
        "investeerimissoovitus. Enne otsuseid kontrolli tegelikke hindu ja "
        "positsioone Lightyearis."
    )


# =============================================================================
# 6. PEAVOOG
# =============================================================================

def clear_search():
    # Callback käivitub enne vidina uuesti loomist, seega on muutmine lubatud.
    st.session_state["global_search"] = ""


show_html(DARK_MODE_CSS)
show_html(
    """
    <div class="hero-container">
      <div class="main-title">✨ AI Kuulutuste Skänner Pro</div>
      <div class="sub-title">
        Facebooki tasuta esemed, Hange.ee aiatööd, garaažid, toidukaubad ja portfell
      </div>
    </div>
    """
)

search_col, clear_col = st.columns([5, 1])
with search_col:
    search_query = st.text_input(
        "🔍 Otsi märksõna järgi...",
        placeholder="Sisesta nt NVIDIA, muru, piim, banaan...",
        label_visibility="collapsed",
        key="global_search",
    )
with clear_col:
    st.button("Tühjenda", **STRETCH, on_click=clear_search)

# Uus otsing -> alusta lehitsemist algusest.
if st.session_state.get("_last_query") != search_query:
    for key in [k for k in st.session_state if k.startswith("visible_count_")]:
        del st.session_state[key]
    st.session_state["_last_query"] = search_query

selected_tab = st.radio(
    "Vali kategooria:", TABS, horizontal=True, label_visibility="collapsed"
)
st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

if selected_tab == TAB_FREE:
    render_feed_tab(
        feed_url=FB_FEED_URL,
        source_md="[Facebooki tasuta asjade voog](https://www.facebook.com)",
        badge_text="🎁 Tasuta", pill_class="badge-free",
        button_text="Vaata Facebookis",
        empty_msg="Ühtegi sobivat kuulutust ei leitud. Kontrolli RSS-voogu või proovi teist otsingusõna.",
        page_key="free", search_query=search_query,
    )
elif selected_tab == TAB_GARAGES:
    render_feed_tab(
        feed_url=GARAGE_FEED_URL,
        source_md="[Kinnisvara24](https://kinnisvara24.ee)",
        badge_text="🚘 Garaaž", pill_class="badge-price",
        button_text="Vaata kuulutust",
        empty_msg="Garaažide RSS-voost ei leitud praegu sobivaid kuulutusi.",
        page_key="garages",
        search_query=search_query,
    )
elif selected_tab == TAB_GARDEN:
    render_garden_tab(search_query)
elif selected_tab == TAB_FOOD:
    render_food_tab(search_query)
elif selected_tab == TAB_INVEST:
    render_invest_tab()


# =============================================================================
# 7. JALUS
# =============================================================================

st.markdown("---")
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.caption(
        "AI Kuulutuste Skänner Pro · RSS-andmete kuvamine sõltub väliste "
        "andmevoogude kättesaadavusest."
    )
with footer_col2:
    if st.button("🔄 Tühjenda vahemälu", **STRETCH):
        st.cache_data.clear()
        st.rerun()
