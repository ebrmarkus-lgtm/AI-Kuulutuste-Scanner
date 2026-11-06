import html
import json
import os
import random
import re
import urllib.parse
from collections import Counter
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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

st_autorefresh(interval=60_000, key="smart_live_refresh")

TZ = ZoneInfo("Europe/Tallinn")

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
FEED_TTL = 900

FB_FEED_URL = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
GARAGE_FEED_URL = "https://rss.app/feeds/MjiyNEAjjPzTGkVZ.xml"
HANGE_FEED_URL = "https://rss.app/feeds/Kk2a3NlHMBN8YOGy.xml"
HANGE_SOURCE_URL = "https://www.hange.ee/hanked/?category=aia-ehitus"

TAB_FREE = "🎁 Tasuta asjad"
TAB_GARAGES = "🚘 Kinnisvara garaažid"
TAB_GARDEN = "🌿 Aiatööd (Hange.ee)"
TAB_FOOD = "🛒 Toidukaubad"
TAB_INVEST = "📈 AI Aktsia- ja Portfelliassistent"
TABS = [TAB_FREE, TAB_GARAGES, TAB_GARDEN, TAB_FOOD, TAB_INVEST]


def stem_regex(stems):
    return re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(s) for s in stems) + ")",
        re.IGNORECASE,
    )


GARDEN_CATEGORY_RE = stem_regex([
    "aia", "haljast", "muru", "maastik", "puude", "puuhooldus",
    "raie", "õuealad", "territoorium", "piirde", "sillut",
])
GARDEN_KEYWORD_RE = stem_regex([
    "aia", "haljast", "muru", "hekk", "heki", "viljapuu", "istut",
    "lillepeenar", "trimmer", "lehte", "multš", "freesi", "põõsa",
    "raie", "raiu", "võsa", "kiviparkett", "terrass", "õue",
    "puu lõik", "puude", "kasvuhoone", "piirdeaed",
])
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
.badge-buy { background-color: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4); }
.badge-hold { background-color: rgba(234,179,8,0.2); color: #facc15; border: 1px solid rgba(234,179,8,0.4); }
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
.metric-big { font-size: 2.2rem; font-weight: 800; color: #f8fafc; letter-spacing: -1px; }
.asset-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #1f2937; }
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
        or (local_name(tag) == "content" and not tag.get("url"))
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
    href = link_tag.get("href")
    if href:
        return safe_http_url(href, base_url=base_url)
    return safe_http_url(link_tag.get_text(" ", strip=True), base_url=base_url)


def extract_entry_text(entry, tag_names):
    for tag in entry.find_all(True):
        if local_name(tag) in tag_names:
            raw = "".join(str(child) for child in tag.contents) or tag.get_text(" ", strip=True)
            text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
            return " ".join(text.split())
    return ""


def extract_entry_date(entry):
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


HANGE_META_RE = re.compile(
    r"Keskmine hind\s+(?P<price>[\d\s.,]*?)\s*€\s*pakkujaid\s+(?P<bids>\d+)\."
    r"\s*(?:(?P<category>[^:]{2,80}?):)?\s*(?P<text>.*)",
    re.DOTALL,
)
HANGE_TRAILER_RE = re.compile(r"\s*Vaata kõiki pakkumisi ja hindu meie keskkonnas\.?\s*$")


@st.cache_data(ttl=FEED_TTL, show_spinner=False)
def load_feed(feed_url, kind):
    feed_url = safe_http_url(feed_url)
    if not feed_url:
        raise ValueError("Vigane RSS-voo URL.")

    response = requests.get(feed_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    try:
        soup = BeautifulSoup(response.content, "xml")
    except FeatureNotFound:
        raise RuntimeError("XML-parser puudub.") from None

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
    empty = {"items": [], "meta": {"channel_title": "", "total": 0, "kept": 0, "categories": {}}}
    try:
        return load_feed(feed_url, kind)
    except requests.RequestException as exc:
        st.warning(f"RSS-voo laadimine ebaõnnestus: {exc}")
    except Exception as exc:
        st.warning(f"RSS-andmete töötlemisel tekkis viga: {exc}")
    return empty


# =============================================================================
# 4. KUULUTUSTE VAATED JA TOIDUKAUBAD
# =============================================================================

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


def render_feed_tab(*, feed_url, source_md, badge_text, pill_class, button_text, empty_msg, page_key, search_query):
    show_html('<div class="refresh-badge">⏱️ Leht uuendub iga 1 min</div>')
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
    show_html('<div class="refresh-badge">ℹ️ Toidukaupade sooduspakkumised</div>')
    stores = ["Kõik"] + sorted({g[2] for g in GROCERIES})
    store_filter = st.selectbox("Filtreeri kaupluse järgi:", stores)

    items = [
        {
            "title": title,
            "description": "Kampaaniatoode igapäevaseks tarbimiseks.",
            "price": f"{price} €",
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

    for item in paginate_items(filtered, "groceries"):
        badges = pill("badge-price", f"🏷️ {item['price']}") + pill("badge-location", f"📍 {item['store']}")
        render_card(item, "Va
