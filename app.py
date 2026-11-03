import html as html_lib
import json
import os
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -----------------------------------------------------------------------------
# 1. RAKENDUSE SEADISTUS JA TUME (DARK MODE) DISAINISÜSTEEM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Kuulutuste Skänner Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# An active browser session reruns hourly. Cached source functions below ensure
# these reruns refresh upstream data at most once per hour.
st_autorefresh(interval=60 * 60 * 1000, key="hourly_data_refresh")

DARK_MODE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .stApp { background-color: #0b0f19; color: #f8fafc; }

    .hero-container { padding: 0.5rem 0 1.25rem 0; border-bottom: 1px solid #1e293b; margin-bottom: 1.5rem; }
    .main-title { font-size: 2.2rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.025em; margin-bottom: 0.25rem; }
    .sub-title { font-size: 0.95rem; color: #94a3b8; font-weight: 400; }

    .pro-card {
        background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 24px;
        margin-bottom: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); transition: all 0.2s ease;
    }
    .pro-card:hover { transform: translateY(-2px); border-color: #374151; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }

    .card-row { display: flex; gap: 22px; align-items: flex-start; }
    .card-img { flex: 0 0 280px; max-width: 280px; }
    .card-img img { width: 100%; border-radius: 12px; display: block; object-fit: cover; aspect-ratio: 4 / 3; background-color: #1f2937; }
    .card-body { flex: 1; min-width: 0; }
    @media (max-width: 700px) {
        .card-row { flex-direction: column; }
        .card-img { flex: none; max-width: 100%; width: 100%; }
    }

    .card-title { font-size: 1.2rem; font-weight: 700; color: #f8fafc; line-height: 1.4; margin-bottom: 6px; }
    .card-date { font-size: 0.8rem; font-weight: 500; color: #94a3b8; margin-bottom: 12px; }
    .card-desc { font-size: 0.95rem; color: #cbd5e1; line-height: 1.6; margin-bottom: 18px; }
    .card-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }

    .badge-pill { padding: 5px 12px; border-radius: 20px; font-size: 0.775rem; font-weight: 600; }
    .badge-free { background-color: rgba(5,150,105,0.15); color: #34d399; border: 1px solid rgba(5,150,105,0.3); }
    .badge-price { background-color: rgba(37,99,235,0.15); color: #60a5fa; border: 1px solid rgba(37,99,235,0.3); }
    .badge-location { background-color: rgba(71,85,105,0.2); color: #94a3b8; border: 1px solid rgba(71,85,105,0.4); }
    .badge-yellow { background-color: rgba(234,179,8,0.2); color: #facc15; border: 1px solid rgba(234,179,8,0.4); }
    .badge-gardening { background-color: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4); }

    .pro-btn {
        display: inline-flex; align-items: center; justify-content: center; width: 100%;
        padding: 11px 18px; background: #2563eb; color: #ffffff !important; font-size: 0.9rem;
        font-weight: 600; border-radius: 10px; text-decoration: none !important; transition: all 0.2s ease;
    }
    .pro-btn:hover { background: #1d4ed8; box-shadow: 0 4px 15px rgba(37,99,235,0.4); }
    .pro-btn.secondary { background: #1f2937; border: 1px solid #374151; margin-top: 8px; }
    .pro-btn.secondary:hover { background: #273449; }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

st.markdown(
    '<div class="hero-container">'
    '<div class="main-title">⚡ AI Kuulutuste Skänner Pro</div>'
    '<div class="sub-title">Facebooki tasuta kuulutused, Hange.ee aiatööd, KV24 ja Renault 5 E-Tech · toidupakkumised on näidised</div>'
    "</div>",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 2. ABIFUNKTSIOONID
# -----------------------------------------------------------------------------
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

def esc(value) -> str:
    text = html_lib.escape(str(value if value is not None else ""), quote=True)
    return text.replace("$", "&#36;")

def safe_http_url(value, fallback=None):
    """Return an absolute HTTP(S) URL, or a safe fallback for untrusted values."""
    if not isinstance(value, str):
        return fallback
    candidate = value.strip()
    try:
        parsed = urllib.parse.urlsplit(candidate)
    except ValueError:
        return fallback
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return fallback
    return candidate

def html_block(markup: str) -> str:
    return "".join(line.strip() for line in markup.splitlines() if line.strip())

def show_html(markup: str):
    st.markdown(html_block(markup), unsafe_allow_html=True)

def get_robust_session():
    session = requests.Session()
    retries = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def translate_to_estonian(text):
    if not text or not re.search(r"[\u0400-\u04FF]", text):
        return text
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single?client=gtx&sl=ru&tl=et&dt=t&q="
            + urllib.parse.quote(text)
        )
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if response.status_code == 200:
            data = response.json()
            translated = "".join(item[0] for item in data[0] if item[0])
            return translated or text
    except Exception:
        pass
    return text

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)

def extract_price(text):
    if not text:
        return "Hind kokkuleppel"
    m = re.search(r"(\d[\d\s\.]*)\s*(?:€|EUR)(?:\s*/\s*[a-zA-ZäöüõÄÖÜÕ]+)?", text, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    return "Hind kokkuleppel"

def matches(query, *fields):
    if not query:
        return True
    q = str(query).casefold().strip()
    return any(q in str(field or "").casefold() for field in fields)


PAGE_INCREMENT = 25


def paginate_items(items, category_key, filters=None):
    """Show an expandable slice of the filtered list, with session-safe state."""
    items = list(items)
    total = len(items)
    count_key = f"visible_count_{category_key}"
    filter_key = f"visible_filter_{category_key}"
    filter_signature = json.dumps(filters, ensure_ascii=False, sort_keys=True, default=str)

    if st.session_state.get(filter_key) != filter_signature:
        st.session_state[filter_key] = filter_signature
        st.session_state[count_key] = PAGE_INCREMENT

    visible_count = min(total, max(PAGE_INCREMENT, int(st.session_state.get(count_key, PAGE_INCREMENT))))
    st.caption(f"Leitud {total} tulemust · Näitan {visible_count}.")

    if visible_count < total:
        remaining = total - visible_count
        load_more, show_all, _ = st.columns([1, 1, 4])
        with load_more:
            if st.button(
                f"Näita veel {min(PAGE_INCREMENT, remaining)}",
                key=f"load_more_{category_key}",
            ):
                st.session_state[count_key] = min(total, visible_count + PAGE_INCREMENT)
                st.rerun()
        with show_all:
            if st.button("Näita kõiki", key=f"show_all_{category_key}"):
                st.session_state[count_key] = total
                st.rerun()

    return items[:visible_count]

def render_card(item, key, button_text, badges="", link=None, secondary=None):
    link = safe_http_url(link or item.get("link") or item.get("url"))
    img_url = safe_http_url(
        item.get("image"),
        fallback="https://picsum.photos/seed/hangeval/600/450",
    )

    img_html = (
        f'<div class="card-img"><img src="{esc(img_url)}" loading="lazy" '
        f'referrerpolicy="no-referrer" alt="" onerror="this.onerror=null;this.src=\'https://picsum.photos/seed/fallback/600/450\';"></div>'
    )
    
    date_html = f'<div class="card-date">{esc(item["date_str"])}</div>' if item.get("date_str") else ""
    tags_html = f'<div class="card-tags">{badges}</div>' if badges else ""
    sec_html = ""
    if secondary:
        secondary_url = safe_http_url(secondary[1])
        if secondary_url:
            sec_html = (
                f'<a href="{esc(secondary_url)}" target="_blank" rel="noopener noreferrer" '
                f'class="pro-btn secondary">{esc(secondary[0])}</a>'
            )
    primary_html = (
        f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer" class="pro-btn">'
        f"{esc(button_text)}</a>"
        if link
        else '<span class="pro-btn secondary" aria-disabled="true">Link puudub</span>'
    )
    show_html(
        f'<div class="pro-card"><div class="card-row">{img_html}<div class="card-body">'
        f'<div class="card-title">{esc(item.get("title") or item.get("store"))}</div>'
        f"{date_html}"
        f'<div class="card-desc">{esc(item.get("description") or item.get("desc"))}</div>'
        f"{tags_html}"
        f"{primary_html}"
        f"{sec_html}"
        f"</div></div></div>"
    )

# -----------------------------------------------------------------------------
# 3. ANDMEKORJE LOOGIKA (HANGE.EE ROHKEM PAKKUMISI)
# -----------------------------------------------------------------------------
HANGE_BASE_URL = "https://www.hange.ee"
HANGE_ACTIVE_LIST_URL = f"{HANGE_BASE_URL}/hanked/?filter=all-active"
HANGE_OFFER_PATH = re.compile(r"^/\d+/[^/]+/?$")
HANGE_GARDENING_KEYWORDS = (
    "aia", "aiamaja", "aiatöö", "aed", "haljast", "muru", "muruniit",
    "hekk", "heki", "viljapuu", "põõsa", "puude langet", "langet",
    "raie", "õue", "lehtede äravedu", "kiviparkett", "lillepeenar",
)


def normalize_hange_offer_url(value):
    """Accept only Hange.ee's individual offer URLs, never its home/list page."""
    absolute_url = safe_http_url(urllib.parse.urljoin(HANGE_BASE_URL, value))
    if not absolute_url:
        return None

    parsed = urllib.parse.urlsplit(absolute_url)
    if parsed.hostname not in {"hange.ee", "www.hange.ee"}:
        return None
    if not HANGE_OFFER_PATH.fullmatch(parsed.path):
        return None

    path = parsed.path.rstrip("/") + "/"
    return urllib.parse.urlunsplit(("https", "www.hange.ee", path, "", ""))


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_hange_gardening():
    """Fetch active Hange.ee offers and keep gardening-related real listings."""
    session = get_robust_session()
    headers = {"User-Agent": UA, "Accept-Language": "et-EE,et;q=0.9,en;q=0.8"}
    first_response = session.get(HANGE_ACTIVE_LIST_URL, headers=headers, timeout=15)
    first_response.raise_for_status()
    first_soup = BeautifulSoup(first_response.content, "html.parser")

    # Follow only page numbers advertised by the provider and fetch each once.
    page_numbers = {1}
    for anchor in first_soup.select('a[href*="page="]'):
        page_url = urllib.parse.urljoin(HANGE_BASE_URL, anchor.get("href", ""))
        page_query = urllib.parse.parse_qs(urllib.parse.urlsplit(page_url).query)
        try:
            page_number = int(page_query.get("page", ["1"])[0])
        except (TypeError, ValueError):
            continue
        if page_query.get("filter", [""])[0] == "all-active" and page_number > 1:
            page_numbers.add(page_number)

    results, seen_urls = [], set()
    for page_number in sorted(page_numbers):
        if page_number == 1:
            soup = first_soup
        else:
            page_url = f"{HANGE_ACTIVE_LIST_URL}&page={page_number}"
            response = session.get(page_url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

        for row in soup.select("table.table_hanked tbody tr"):
            title_link = row.select_one("h2 a.border-link[href]")
            if not title_link:
                continue

            offer_url = normalize_hange_offer_url(title_link.get("href", ""))
            if not offer_url or offer_url in seen_urls:
                continue

            title = title_link.get_text(" ", strip=True)
            detail = row.select_one(".table-txt p")
            description = detail.get_text(" ", strip=True) if detail else ""
            searchable_text = f"{title} {description}".casefold()
            if not any(keyword in searchable_text for keyword in HANGE_GARDENING_KEYWORDS):
                continue

            seen_urls.add(offer_url)
            location_match = re.search(
                r"Asukoht:\s*(.*?)(?:\s+Hanke etapp:|\s+Hanke korraldaja:|$)",
                description,
                flags=re.IGNORECASE,
            )
            location = location_match.group(1).strip() if location_match else "Eesti"

            image = row.select_one(".table-img img")
            image_url = ""
            if image:
                image_url = image.get("data-src") or image.get("src") or ""
            if not image_url:
                image_source = row.select_one(".table-img source[data-srcset]")
                if image_source:
                    image_url = image_source.get("data-srcset", "").split()[0]
            image_url = safe_http_url(
                urllib.parse.urljoin(HANGE_BASE_URL, image_url),
                fallback="https://picsum.photos/seed/hange/600/450",
            )

            cells = row.find_all("td", recursive=False)
            added_date = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
            results.append(
                {
                    "title": title,
                    "description": description or "Aktiivne hange Hange.ee-s.",
                    "price": "Vaata Hange.ee-st",
                    "location": location,
                    "url": offer_url,
                    "link": offer_url,
                    "date_str": f"📅 Lisatud {added_date}" if added_date else "",
                    "image": image_url,
                }
            )

    return results

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_kv24_garages():
    url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    headers = {"User-Agent": UA, "Accept-Language": "et-EE,et;q=0.9,en;q=0.8"}
    results, seen = [], set()
    response = get_robust_session().get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for a_tag in soup.find_all("a", href=re.compile(r"/kinnisvara/|/objekt/|/garaaz/")):
        href = a_tag.get("href")
        title = a_tag.get_text(" ", strip=True)
        if not href or len(title) < 5 or href in ("/garaaz/muuk/harju-maakond", "/garaaz/harju-maakond"):
            continue
        full_url = safe_http_url(urllib.parse.urljoin("https://kinnisvara24.ee", href))
        if not full_url or full_url in seen:
            continue
        seen.add(full_url)
        parent = a_tag.find_parent(["div", "article", "li"])
        price = extract_price(parent.get_text(" ", strip=True) if parent else title)
        results.append(
            {
                "title": title,
                "description": "Aktiivne garaaži või boksi müügipakkumine Harju maakonnas.",
                "price": price,
                "location": "Harju maakond",
                "url": full_url,
                "image": "https://picsum.photos/seed/kv24gar/600/450",
            }
        )
    return results

# ---- Renault 5 E-Tech (AutoScout24) -------------------
AS24_BASE = "https://www.autoscout24.com"
AS24_YELLOW_URL = f"{AS24_BASE}/lst/renault/r-5/bc_yellow"

COUNTRY_NAMES = {
    "D": "Saksamaa", "DE": "Saksamaa", "A": "Austria", "AT": "Austria", "B": "Belgia", "BE": "Belgia",
    "E": "Hispaania", "ES": "Hispaania", "F": "Prantsusmaa", "FR": "Prantsusmaa", "I": "Itaalia",
    "IT": "Itaalia", "L": "Luksemburg", "LU": "Luksemburg", "NL": "Holland",
}

VARIANTS = {
    "Kõik variandid": None,
    "Evolution 120 (Urban Range, 40 kWh)": ("evolution",),
    "Techno (120 Urban / 150 Comfort)": ("techno",),
    "Iconic Five 150 (Comfort Range, 52 kWh)": ("iconic",),
}

def _dig(obj, *path, default=None):
    for key in path:
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        elif isinstance(obj, list) and isinstance(key, int) and -len(obj) <= key < len(obj):
            obj = obj[key]
        else:
            return default
    return obj

def _price_to_int(text):
    m = re.search(r"(\d{1,3}(?:[,\.\s]\d{3})+|\d{3,6})", str(text or ""))
    if not m:
        return None
    try:
        return int(re.sub(r"\D", "", m.group(1)))
    except ValueError:
        return None

def _fmt_price(value):
    return f"{value:,}".replace(",", " ") + " €" if value else "Hind puudub"

def _battery_from_title(title):
    t = title.lower()
    if "urban" in t or "evolution" in t or "40 kwh" in t or "120" in t:
        return "40 kWh (~300 km)"
    if "comfort" in t or "iconic" in t or "52" in t or "150" in t:
        return "52 kWh (~400 km)"
    return ""

def _clean_img(url):
    if not url:
        return None
    url = url.strip().split(" ")[0]
    return url if url.startswith("http") else None

def _is_r5_electric(title, url, text):
    t = f"{title} {text}".lower()
    if not ("renault-r-5" in url.lower() or re.search(r"\br\s?-?5\b", t) or "renault 5" in t):
        return False
    has_electric = bool(re.search(r"electric|elektr|électrique|elettric|eléctric|e-tech", t))
    if re.search(r"gasoline|petrol|benzin|essence|diesel", t) and not has_electric:
        return False
    reg = re.search(r"\b(?:0[1-9]|1[0-2])[/-](19\d{2}|20\d{2})\b", text)
    if reg and int(reg.group(1)) < 2023:
        return False
    return has_electric or bool(re.search(r"evolution|iconic|techno|comfort range|urban range", t))

def _parse_as24_next_data(soup):
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not (tag.string or tag.text):
        return []
    try:
        data = json.loads(tag.string or tag.text)
    except Exception:
        return []
    listings = _dig(data, "props", "pageProps", "listings", default=[]) or []
    out = []
    for raw in listings:
        if not isinstance(raw, dict):
            continue
        vehicle = raw.get("vehicle") or {}
        version = vehicle.get("modelVersionInput") or vehicle.get("variant") or ""
        model = str(vehicle.get("model", ""))
        title = f"Renault {model} {version}".strip()
        url = raw.get("url") or ""
        url = urllib.parse.urljoin(AS24_BASE, url.split("?")[0]) if url else ""
        blob = json.dumps(raw, ensure_ascii=False)
        if not url or not _is_r5_electric(title, url, blob):
            continue
        price = _price_to_int(
            _dig(raw, "price", "priceRaw") or _dig(raw, "prices", "public", "priceRaw")
            or _dig(raw, "price", "priceFormatted") or _dig(raw, "tracking", "price")
        )
        loc = raw.get("location") or {}
        cc = str(loc.get("countryCode", "")).upper()
        images = raw.get("images") or []
        image = _clean_img(images[0]) if images and isinstance(images[0], str) else "https://picsum.photos/seed/r5car/600/450"
        km = _dig(raw, "tracking", "mileage") or vehicle.get("mileageInKm") or ""
        reg = _dig(raw, "tracking", "firstRegistration") or ""
        seller = _dig(raw, "seller", "companyName") or ""
        out.append(
            {
                "title": title, "price_val": price, "link": url, "image": image,
                "location": ", ".join(x for x in (loc.get("city"), COUNTRY_NAMES.get(cc, cc)) if x) or "Euroopa",
                "km": f"{km} km" if km else "", "reg": str(reg), "seller": seller,
            }
        )
    return out

def _parse_as24_html(soup):
    offer_re = re.compile(r"/offers/")
    out, seen = [], set()
    for a in soup.find_all("a", href=offer_re):
        url = urllib.parse.urljoin(AS24_BASE, a["href"].split("?")[0])
        if url in seen:
            continue
        card, hops = a, 0
        while card is not None and hops < 10 and not (card.find("h2") and "€" in card.get_text(" ")):
            card, hops = card.parent, hops + 1
        if card is None or hops >= 10:
            continue
        distinct = {x["href"].split("?")[0] for x in card.find_all("a", href=offer_re)}
        if len(distinct) > 2:
            continue
        seen.add(url)
        text = card.get_text(" ", strip=True)
        h2 = card.find("h2")
        title = h2.get_text(" ", strip=True) if h2 else ""
        if not _is_r5_electric(title, url, text):
            continue
        price = _price_to_int(re.search(r"€\s*([\d,\.]+)", text).group(1)) if re.search(r"€\s*([\d,\.]+)", text) else None
        img = card.find("img", src=re.compile(r"listing-images")) or card.find("img", attrs={"data-src": True})
        image = "https://picsum.photos/seed/r5car/600/450"
        if img:
            image = _clean_img(img.get("src") or img.get("data-src") or (img.get("srcset") or "").split(",")[0]) or image
        km = re.search(r"([\d,\.]+)\s*km\b", text)
        reg = re.search(r"\b(\d{2}/\d{4})\b", text)
        loc = re.search(r"(DE|AT|BE|ES|FR|IT|LU|NL)-(\d{3,5}(?:\s[A-Z]{2}\b)?)\s*([^\d\n]{0,30})", text)
        location = "Euroopa"
        if loc:
            location = f"{COUNTRY_NAMES.get(loc.group(1), loc.group(1))}, {loc.group(2)} {loc.group(3)}".strip(" ,")
        out.append(
            {
                "title": title or "Renault 5", "price_val": price, "link": url, "image": image,
                "location": location, "km": f"{km.group(1)} km" if km else "",
                "reg": reg.group(1) if reg else "", "seller": "",
            }
        )
    return out

def _fetch_as24_page(page, session=None):
    session = session or get_robust_session()
    headers = {"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9", "Accept": "text/html,application/xhtml+xml"}
    last_status = None
    for params in (f"?sort=price&desc=0&page={page}", f"?page={page}"):
        try:
            r = session.get(AS24_YELLOW_URL + params, headers=headers, timeout=15)
            last_status = r.status_code
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            items = _parse_as24_next_data(soup)
            method = "next_data"
            if not items:
                items = _parse_as24_html(soup)
                method = "html"
            if items:
                return items, method, 200
        except Exception as e:
            last_status = f"viga: {type(e).__name__}"
    return [], "-", last_status

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_renault_5_yellow_ev():
    all_items, report, seen = [], [], set()
    session = get_robust_session()
    page = 1
    while True:
        items, method, status = _fetch_as24_page(page, session=session)
        report.append(f"leht {page}: {len(items)} tk ({method}, HTTP {status})")
        if not items:
            break

        new_items = [item for item in items if item["link"] not in seen]
        if not new_items:
            break
        for item in new_items:
            seen.add(item["link"])
            all_items.append(item)
        page += 1
    if not all_items:
        raise RuntimeError("AutoScout24 ei andnud kuulutusi. " + "; ".join(report[:3]))

    result = []
    for it in all_items:
        title = re.sub(r"\s+", " ", it["title"]).strip()
        parts = [p for p in (it["reg"] and f"Esmane reg. {it['reg']}", it["km"], it["seller"] and f"Müüja: {it['seller']}") if p]
        result.append(
            {
                "title": title,
                "description": " · ".join(parts) or "Kollane Renault 5 E-Tech elektriauto.",
                "price": _fmt_price(it["price_val"]),
                "price_val": it["price_val"] or 10**9,
                "battery": _battery_from_title(title),
                "location": it["location"],
                "image": it["image"],
                "link": it["link"],
            }
        )
    result.sort(key=lambda x: x["price_val"])
    return {"items": result, "report": report}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_free_items(rss_url):
    results = []
    resp = get_robust_session().get(rss_url, headers={"User-Agent": UA}, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "xml")
    one_month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    sold_keywords = ["broneeritud", "läinud", "ära antud", "annatud", "läks", "müüdud", "bron"]

    for item in soup.find_all(["item", "entry"]):
        link = "https://www.facebook.com/groups/1929529077371716"
        link_elem = item.find("link")
        if link_elem:
            link = link_elem.get("href") or link_elem.get_text(strip=True) or link

        title_elem = item.find("title")
        title = translate_to_estonian(clean_text(title_elem.text if title_elem else "Tasuta ese"))
        desc_elem = item.find("description") or item.find("summary")
        raw_desc = desc_elem.text if desc_elem else ""
        description = translate_to_estonian(clean_text(raw_desc))

        combined = (title + " " + description).lower()
        if any(k in combined for k in sold_keywords):
            continue

        free_keywords = (
            "tasuta", "ära anda", "annan ära", "annab ära", "free",
            "give away", "giving away", "võib ära viia", "kingin",
        )
        if not any(k in combined for k in free_keywords):
            continue
        if re.search(r"\d[\d\s,.]*\s*(?:€|eur|eurot)", combined):
            continue
        if len(description) > 180:
            description = description[:180] + "..."

        date_elem = item.find("pubDate") or item.find("updated")
        date_str = date_elem.text if date_elem else ""
        ts = 0
        if date_str:
            try:
                ts = parsedate_to_datetime(date_str).timestamp()
            except Exception:
                try:
                    ts = datetime.fromisoformat(date_str.replace("Z", "+00:00")).timestamp()
                except Exception:
                    ts = 0
        if 0 < ts < one_month_ago:
            continue

        image_url = "https://picsum.photos/seed/fbfree/600/450"
        enclosure = item.find("enclosure")
        if enclosure and enclosure.get("url"):
            image_url = enclosure.get("url")
        elif raw_desc:
            img = BeautifulSoup(raw_desc, "html.parser").find("img")
            if img and img.get("src"):
                image_url = img.get("src")

        results.append(
            {
                "title": title, "description": description, "price": "Tasuta",
                "location": "Tallinn / Harjumaa", "link": link, "image": image_url,
                "timestamp": ts, "date_str": f"📅 {date_str}" if date_str else "",
            }
        )
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results


def _capture_source(fetcher, *args):
    """Return source data or a safe error type without breaking other sources."""
    try:
        return {"data": fetcher(*args), "error": None}
    except Exception as error:
        return {"data": None, "error": type(error).__name__}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_hourly_source_snapshot(rss_url):
    """Refresh every configured live source together, at most once per hour."""
    snapshot = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "free": (
            _capture_source(fetch_free_items, rss_url)
            if rss_url
            else {"data": [], "error": "RSS_URL_NOT_CONFIGURED"}
        ),
        "kv24": _capture_source(fetch_live_kv24_garages),
        "hange": _capture_source(fetch_live_hange_gardening),
        "renault": _capture_source(fetch_renault_5_yellow_ev),
    }
    return snapshot

# -----------------------------------------------------------------------------
# 4. OTSINGURIBA JA SEKTSIOONID
# -----------------------------------------------------------------------------
def get_secret_value(name):
    """Read a setting from environment variables or Streamlit secrets."""
    value = os.getenv(name, "")
    if value:
        return value.strip()
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


rss_url = get_secret_value("FACEBOOK_GROUP_RSS_URL")
with st.spinner("Värskendan tunnipõhiseid andmeallikaid..."):
    source_snapshot = fetch_hourly_source_snapshot(rss_url)

checked_at = datetime.fromisoformat(source_snapshot["checked_at"]).astimezone(timezone.utc)
st.caption(
    "Viimane allikate kontroll: "
    f"{checked_at:%d.%m.%Y %H:%M} UTC · automaatne uuendus kord tunnis, kui rakendus on avatud."
)
source_labels = {
    "free": "Facebook RSS",
    "kv24": "Kinnisvara24",
    "hange": "Hange.ee",
    "renault": "AutoScout24",
}
source_errors = [
    label
    for key, label in source_labels.items()
    if (key != "free" or rss_url) and source_snapshot[key]["error"]
]
if source_errors:
    st.caption("Allikate tõrge: " + ", ".join(source_errors) + ". Vastav vaade näitab lisateavet.")

search_query = st.text_input(
    "🔍 Otsi märksõna järgi...",
    placeholder="nt vaip, diivan, tool, jalgratas...",
)

selected_tab = st.radio(
    "Vali vaade:",
    [
        "🎁 Tasuta asjad", "🏢 Kinnisvara objektid", "🌱 Aiatööd Hange.ee",
        "⚡ Renault 5 EV", "🛒 Toidu sooduspakkumised", "🚗 Kütusehinnad & Parkimine",
        "📈 Eesti reitingud",
    ],
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# --- 1. SEKTSIOON: TASUTA ASJAD ---
if selected_tab == "🎁 Tasuta asjad":
    facebook_group_url = "https://www.facebook.com/groups/1929529077371716"
    st.markdown(
        f"**Allikas:** [Facebooki grupp – tasuta asjad]({facebook_group_url})"
    )
    if not rss_url:
        st.warning(
            "Facebooki grupi postituste automaatseks kuvamiseks lisa selle grupi RSS-kanali "
            "aadress Streamlit Secrets väärtusena `FACEBOOK_GROUP_RSS_URL`."
        )
        st.markdown(
            f'<a class="pro-btn" href="{facebook_group_url}" target="_blank" '
            'rel="noopener">👉 Ava Facebooki grupp</a>',
            unsafe_allow_html=True,
        )
        free_items = []
    else:
        free_result = source_snapshot["free"]
        if free_result["error"]:
            st.error(
                "Facebooki RSS-kanali laadimine ebaõnnestus "
                f"({free_result['error']}). Kontrolli RSS-aadressi ja proovi hiljem uuesti."
            )
            free_items = []
        else:
            free_items = free_result["data"] or []

    filtered_free_items = [
        i for i in free_items
        if matches(search_query, i["title"], i["description"])
    ]
    visible_free_items = paginate_items(
        filtered_free_items,
        "free",
        filters=(search_query, bool(rss_url)),
    )
    for idx, item in enumerate(visible_free_items):
        badges = (
            '<span class="badge-pill badge-free">Tasuta</span>'
            f'<span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
        )
        render_card(item, f"fav_fb_{idx}", "👉 Vaata kuulutust Facebookis", badges)

# --- 2. SEKTSIOON: KINNISVARA OBJEKTID ---
elif selected_tab == "🏢 Kinnisvara objektid":
    canonical_kv24_url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    kv24_result = source_snapshot["kv24"]
    if kv24_result["error"]:
        st.error(f"Kinnisvara24 andmete laadimine ebaõnnestus ({kv24_result['error']}).")
        st.link_button("Ava garaažipakkumised Kinnisvara24-s", canonical_kv24_url)
    else:
        kv24_items = kv24_result["data"] or []
        filtered_kv24_items = [
            item for item in kv24_items
            if matches(search_query, item["title"], item["description"], item["location"])
        ]
        visible_kv24_items = paginate_items(
            filtered_kv24_items,
            "kv24",
            filters=search_query,
        )
        if not filtered_kv24_items:
            st.info("Selle otsinguga aktiivseid garaažipakkumisi ei leitud.")
            st.link_button("Ava garaažipakkumised Kinnisvara24-s", canonical_kv24_url)
        for idx, item in enumerate(visible_kv24_items):
            badges = (
                f'<span class="badge-pill badge-price">{esc(item["price"])}</span>'
                f'<span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
            )
            render_card(
                item,
                f"fav_kv24_{idx}",
                "👉 Ava pakkumine Kinnisvara24-s",
                badges,
                link=item.get("url", canonical_kv24_url),
            )

# --- 3. SEKTSIOON: AIATÖÖD HANGE.EE ---
elif selected_tab == "🌱 Aiatööd Hange.ee":
    st.markdown("### 🌱 Aktiivsed aiatööde hanked Hange.ee-s")
    st.info(
        "Kuulutused laaditakse Hange.ee aktiivsete hangete nimekirjast. "
        "Iga nupp avab konkreetse hanke Hange.ee-s."
    )

    hange_result = source_snapshot["hange"]

    if hange_result["error"]:
        st.error(
            "Hange.ee kuulutusi ei saanud praegu laadida. "
            "Ava nende aktiivsete hangete nimekiri otse:"
        )
        st.link_button(
            "Ava Hange.ee aktiivsed hanked",
            HANGE_ACTIVE_LIST_URL,
            use_container_width=True,
        )
    else:
        hange_items = hange_result["data"] or []
        visible_items = [
            item for item in hange_items
            if matches(search_query, item["title"], item["description"], item["location"])
        ]
        visible_items = paginate_items(
            visible_items,
            "hange",
            filters=search_query,
        )
        if not visible_items:
            st.info("Praegu ei leitud aktiivseid aiatööde hankeid, mis vastaksid otsingule.")
            st.link_button(
                "Ava Hange.ee aktiivsed hanked",
                HANGE_ACTIVE_LIST_URL,
                use_container_width=True,
            )
        else:
            for idx, item in enumerate(visible_items):
                badges = (
                    '<span class="badge-pill badge-gardening">🌱 Hange.ee</span>'
                    f'<span class="badge-pill badge-price">{esc(item["price"])}</span>'
                    f'<span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
                )
                render_card(
                    item,
                    f"hange_live_{idx}",
                    "👉 Ava see hange Hange.ee-s",
                    badges,
                    link=item["url"],
                )

# --- 4. SEKTSIOON: RENAULT 5 EV ---
elif selected_tab == "⚡ Renault 5 EV":
    st.markdown("### ⚡ Renault 5 E-Tech (kollane) – päris kuulutused Euroopast")
    st.info(
        "Ainult elektriline Renault 5 kollases värvitoonis, kõik müüjad kogu Euroopas "
        "(DE, AT, BE, ES, FR, IT, LU, NL). Andmed tulevad otse AutoScout24-st ja neid kontrollitakse kord tunnis."
    )

    c_var, c_sort = st.columns([2, 1])
    with c_var:
        variant_label = st.selectbox("Variant", list(VARIANTS.keys()))
    with c_sort:
        sort_label = st.selectbox("Järjekord", ["Odavaim ees", "Kallim ees"])

    r5_result = source_snapshot["renault"]
    if not r5_result["error"] and r5_result["data"]:
        r5_data = r5_result["data"]
        keys = VARIANTS[variant_label]
        r5_items = [
            d for d in r5_data["items"]
            if (keys is None or any(k in d["title"].lower() for k in keys))
            and matches(search_query, d["title"], d["description"], d["location"])
        ]
        if sort_label == "Kallim ees":
            r5_items = list(reversed(r5_items))
        r5_items = paginate_items(
            r5_items,
            "renault",
            filters=(search_query, variant_label, sort_label),
        )
        if not r5_items:
            st.warning("Valitud filtritega kuulutusi ei leitud. Proovi variant 'Kõik variandid'.")
        for idx, deal in enumerate(r5_items):
            badges = (
                f'<span class="badge-pill badge-yellow">{esc(deal["price"])}</span>'
                '<span class="badge-pill badge-price">🟡 Kollane</span>'
                + (f'<span class="badge-pill badge-price">🔋 {esc(deal["battery"])}</span>' if deal["battery"] else "")
                + f'<span class="badge-pill badge-location">📍 {esc(deal["location"])}</span>'
            )
            render_card(
                deal, f"fav_r5_{idx}", "👉 Ava kuulutus AutoScout24-s", badges,
                secondary=("🌐 Ava eestikeelsena (Google Translate)",
                           "https://translate.google.com/translate?sl=auto&tl=et&u=" + urllib.parse.quote(deal["link"], safe="")),
            )
    else:
        if r5_result["error"]:
            st.warning(
                "Automaatne otsing ei saanud praegu AutoScout24-st andmeid "
                f"({r5_result['error']})."
            )
        else:
            st.warning("AutoScout24-st ei leitud selle otsinguga kuulutusi.")
        render_card(
            {"title": "Kollane Renault 5 E-Tech – kõik pakkumised Euroopas",
             "description": "Otsing AutoScout24-s: Renault R 5, värv kollane, hind odavaimast kallimani.",
             "image": "https://picsum.photos/seed/r5fallback/600/450"},
            "noop_r5", "👉 Ava AutoScout24 otsing", '<span class="badge-pill badge-yellow">🟡 Kollane</span>',
            link=AS24_YELLOW_URL + "?sort=price&desc=0",
        )

# --- 5. SEKTSIOON: TOIDU SOODUSPAKKUMISED ---
elif selected_tab == "🛒 Toidu sooduspakkumised":
    st.markdown("### 🛒 Toidupakkumised")
    st.warning(
        "Allpool on staatilised näidispakkumised. Hinnad võivad olla aegunud; "
        "kontrolli kehtivat hinda poe veebilehelt."
    )
    food_deals = [
        {"store": "Selver", "title": "Banaani kg", "price": "0.99 €", "desc": "Soodushind kampaaniakirja alusel.", "link": "https://www.selver.ee", "image": "https://picsum.photos/seed/banaan/600/450"},
        {"store": "Rimi", "title": "Kohupiimamaius Karums 45g", "price": "0.39 €", "desc": "Erinevad maitsed igapäevaselt parima hinnaga.", "link": "https://www.rimi.ee", "image": "https://picsum.photos/seed/karums/600/450"}
    ]
    filtered_food_deals = [
        item for item in food_deals
        if matches(search_query, item["store"], item["title"], item["desc"])
    ]
    visible_food_deals = paginate_items(
        filtered_food_deals,
        "food",
        filters=search_query,
    )
    for idx, item in enumerate(visible_food_deals):
        badges = f'<span class="badge-pill badge-price">{esc(item["price"])}</span>'
        render_card(item, f"food_{idx}", f"👉 Vaata {esc(item['store'])} e-poest", badges, link=item["link"])

# --- 6. SEKTSIOON: KÜTUSEHINNAD & PARKIMINE ---
elif selected_tab == "🚗 Kütusehinnad & Parkimine":
    st.markdown("### 🚗 Kütusehinnad ja parkimine")
    st.info(
        "Selle vaate reaalajas andmeallikas pole veel ühendatud, seega "
        "kütusehindu ega parkimisinfot siin praegu ei kuvata."
    )

# --- 7. SEKTSIOON: EESTI REITINGUD ---
elif selected_tab == "📈 Eesti reitingud":
    st.markdown("### 📈 Eesti erakondade ja ühiskonna reitingud")
    st.info(
        "Reitingute interaktiivsed graafikud avanevad väljaandja lehel. "
        "See väldib kolmanda osapoole HTML-i käivitamist rakenduse sees."
    )
    st.link_button(
        "Ava Eesti reitingud",
        "https://reitingud.ee/reitingud/",
        use_container_width=True,
    )
