import html as html_lib
import json
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:  # valikuline: jäljendab Chrome'i TLS-i, mobile.de blokeerib tavalist 'requests' sagedamini
    from curl_cffi import requests as cffi_requests
except Exception:  # pragma: no cover
    cffi_requests = None

# -----------------------------------------------------------------------------
# 1. RAKENDUSE SEADISTUS JA TUME (DARK MODE) DISAINISÜSTEEM
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Kuulutuste Skänner Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
        margin-bottom: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); transition: all 0.2s ease;
    }
    .pro-card:hover { transform: translateY(-2px); border-color: #374151; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }

    .card-row { display: flex; gap: 22px; align-items: flex-start; }
    .card-img { flex: 0 0 280px; max-width: 280px; }
    .card-img img { width: 100%; border-radius: 12px; display: block; object-fit: cover; aspect-ratio: 4 / 3; }
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

if "favorites" not in st.session_state:
    st.session_state.favorites = []

st.markdown(
    '<div class="hero-container">'
    '<div class="main-title">⚡ AI Kuulutuste Skänner Pro</div>'
    '<div class="sub-title">FB Free, KV24, Renault 5 E-Tech (kollane) Euroopas, toidupakkumised &amp; kütusehinnad</div>'
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
    """HTML-i põgenemine. '$' asendatakse, et Streamlit ei tõlgendaks seda LaTeX-ina."""
    text = html_lib.escape(str(value if value is not None else ""), quote=True)
    return text.replace("$", "&#36;")


def html_block(markup: str) -> str:
    """
    Teeb HTML-ist ühe pideva rea (ilma tühjade ridade ja taandeta).
    See on KRIITILINE: Streamlit/Markdown muudab tühja rea järel taandatud HTML-i
    koodiplokiks ja kuvab toore '</div>' teksti.
    """
    return "".join(line.strip() for line in markup.splitlines() if line.strip())


def show_html(markup: str):
    st.markdown(html_block(markup), unsafe_allow_html=True)


def get_robust_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


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


def check_single_link(url):
    """Eemaldab ainult kindlalt kustutatud (404/410) lingid."""
    if not url or url == "#" or not url.startswith("http"):
        return True
    try:
        res = get_robust_session().head(url, headers={"User-Agent": UA}, timeout=3, allow_redirects=True)
        return res.status_code not in (404, 410)
    except Exception:
        return True


@st.cache_data(ttl=1800, show_spinner=False)
def filter_valid_items(items, link_key="link"):
    if not items:
        return []
    urls = [item.get(link_key) for item in items]
    with ThreadPoolExecutor(max_workers=5) as executor:
        statuses = list(executor.map(check_single_link, urls))
    return [item for item, ok in zip(items, statuses) if ok]


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.DOTALL)
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def extract_price(text):
    if not text:
        return "Hind puudub"
    m = re.search(r"(\d[\d\s\.]*)\s*(?:€|EUR)(?:\s*/\s*[a-zA-ZäöüõÄÖÜÕ]+)?", text, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    m = re.search(r"(?:hind|hind:)\s*(\d[\d\s\.]*)", text, re.IGNORECASE)
    if m:
        return f"{m.group(1).strip()} €"
    m = re.search(r"(\d[\d\s]{2,})\s*(?:eur|euro|eurot)", text, re.IGNORECASE)
    if m:
        return f"{m.group(1).strip()} €"
    return "Hind kokkuleppel"


def matches(query, *fields):
    if not query:
        return True
    q = query.lower()
    return any(q in str(f or "").lower() for f in fields)


def add_favorite(item):
    link = item.get("link") or item.get("url")
    if any((f.get("link") or f.get("url")) == link for f in st.session_state.favorites):
        st.toast("See on juba lemmikutes.")
        return
    st.session_state.favorites.append(item)
    st.toast("Salvestatud lemmikutesse! ⭐")


def render_card(item, key, button_text, badges="", link=None, secondary=None, fav_button=True):
    """Üks ühtne kaardi-renderdaja. HTML läheb alati ühe pideva reana (vt html_block)."""
    link = link or item.get("link") or item.get("url") or "#"
    img_html = ""
    if item.get("image"):
        img_html = (
            f'<div class="card-img"><img src="{esc(item["image"])}" loading="lazy" '
            f'referrerpolicy="no-referrer" alt=""></div>'
        )
    date_html = f'<div class="card-date">{esc(item["date_str"])}</div>' if item.get("date_str") else ""
    tags_html = f'<div class="card-tags">{badges}</div>' if badges else ""
    sec_html = ""
    if secondary:
        sec_html = (
            f'<a href="{esc(secondary[1])}" target="_blank" rel="noopener" '
            f'class="pro-btn secondary">{esc(secondary[0])}</a>'
        )
    show_html(
        f'<div class="pro-card"><div class="card-row">{img_html}<div class="card-body">'
        f'<div class="card-title">{esc(item.get("title") or item.get("store"))}</div>'
        f"{date_html}"
        f'<div class="card-desc">{esc(item.get("description") or item.get("desc"))}</div>'
        f"{tags_html}"
        f'<a href="{esc(link)}" target="_blank" rel="noopener" class="pro-btn">{esc(button_text)}</a>'
        f"{sec_html}"
        f"</div></div></div>"
    )
    if fav_button and st.button("⭐ Salvesta lemmikutesse", key=key):
        add_favorite(item)


# -----------------------------------------------------------------------------
# 3. ANDMEKORJE LOOGIKA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_live_kv24_garages():
    url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    headers = {"User-Agent": UA, "Accept-Language": "et-EE,et;q=0.9,en;q=0.8"}
    results, seen = [], set()
    try:
        response = get_robust_session().get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for a_tag in soup.find_all("a", href=re.compile(r"/kinnisvara/|/objekt/|/garaaz/")):
                href = a_tag.get("href")
                title = a_tag.get_text(strip=True)
                if not href or len(title) < 5 or href in ("/garaaz/muuk/harju-maakond", "/garaaz/harju-maakond"):
                    continue
                full_url = href if href.startswith("http") else f"https://kinnisvara24.ee{href}"
                if full_url in seen:
                    continue
                seen.add(full_url)
                parent = a_tag.find_parent(["div", "article", "li"])
                price = extract_price(parent.get_text() if parent else title)
                results.append(
                    {
                        "title": title,
                        "description": "Aktiivne garaaži või boksi müügipakkumine Harju maakonnas.",
                        "price": price,
                        "location": "Harju maakond",
                        "url": full_url,
                    }
                )
    except Exception as e:
        print(f"KV24 viga: {e}")
    return filter_valid_items(results, link_key="url")


# ---- Renault 5 E-Tech, KOLLANE, kogu Euroopa (AutoScout24) -------------------
# Kontrollitud aadress: mudel on AutoScout24-s "r-5", värvifilter "bc_yellow".
AS24_BASE = "https://www.autoscout24.com"
AS24_YELLOW_URL = f"{AS24_BASE}/lst/renault/r-5/bc_yellow"
AS24_MAX_PAGES = 8  # 20 kuulutust lehel

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
    """Ainult elektriline Renault 5 (välistab klassikalise bensiini-R5, mis on samuti 'r-5')."""
    t = f"{title} {text}".lower()
    if not ("renault-r-5" in url.lower() or re.search(r"\br\s?-?5\b", t) or "renault 5" in t):
        return False
    has_electric = bool(re.search(r"electric|elektr|électrique|elettric|eléctric|e-tech", t))
    if re.search(r"gasoline|petrol|benzin|essence|diesel", t) and not has_electric:
        return False
    reg = re.search(r"\b(?:0[1-9]|1[0-2])[/-](19\d{2}|20\d{2})\b", text)
    if reg and int(reg.group(1)) < 2023:  # R5 E-Tech müügil alates 2024
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
        image = _clean_img(images[0]) if images and isinstance(images[0], str) else None
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
    """Varuvariant: loeb kuulutused otse lehe HTML-ist (pealkiri, hind, pilt, link)."""
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
        if len(distinct) > 2:  # ronis liiga kõrgele - sisaldab mitut kuulutust
            continue
        seen.add(url)
        text = card.get_text(" ", strip=True)
        h2 = card.find("h2")
        title = h2.get_text(" ", strip=True) if h2 else ""
        if not _is_r5_electric(title, url, text):
            continue
        price = _price_to_int(re.search(r"€\s*([\d,\.]+)", text).group(1)) if re.search(r"€\s*([\d,\.]+)", text) else None
        img = card.find("img", src=re.compile(r"listing-images")) or card.find("img", attrs={"data-src": True})
        image = None
        if img:
            image = _clean_img(img.get("src") or img.get("data-src") or (img.get("srcset") or "").split(",")[0])
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


def _fetch_as24_page(page):
    headers = {"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9", "Accept": "text/html,application/xhtml+xml"}
    last_status = None
    for params in (f"?sort=price&desc=0&page={page}", f"?page={page}"):
        try:
            r = get_robust_session().get(AS24_YELLOW_URL + params, headers=headers, timeout=15)
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


def _collect_as24():
    """AutoScout24: tagastab (toorkuulutused, aruanne). Ebaõnnestumisel tühi list."""
    items, report, seen = [], [], set()
    with ThreadPoolExecutor(max_workers=4) as ex:
        for page, (page_items, method, status) in enumerate(ex.map(_fetch_as24_page, range(1, AS24_MAX_PAGES + 1)), 1):
            report.append(f"AutoScout24 leht {page}: {len(page_items)} tk ({method}, HTTP {status})")
            for it in page_items:
                if it["link"] not in seen:
                    seen.add(it["link"])
                    it["source"] = "AutoScout24"
                    items.append(it)
    return items, report


# ---- mobile.de ---------------------------------------------------------------
# Kontrollitud aadress: 'renault-gelb.html' = kõik kollased Renault'd (Außenfarbe: Gelb).
# 'renault-r-5-gelb.html' proovitakse esimesena (kui leht on olemas, sisaldab ainult kollast R5).
MOBILE_BASE = "https://suchen.mobile.de"
MOBILE_YELLOW_URLS = [
    f"{MOBILE_BASE}/auto/renault-r-5-gelb.html",
    f"{MOBILE_BASE}/auto/renault-gelb.html",
]
MOBILE_MAX_PAGES = 6
# Kui mobile.de blokeerib otsepäringu, proovitakse lugeda lehte avaliku r.jina.ai vahendaja kaudu.
# Seab False, kui sa seda ei soovi (siis läheb päring ainult otse mobile.de-sse).
MOBILE_USE_PROXY_FALLBACK = True

MOBILE_ID_RE = re.compile(r"(?:details\.html\?(?:[^\"'#]*&)?id=(\d+))|(?:/auto-inserat/[^\"'?#]*?/(\d+)\.html)")
BLOCK_MARKERS = ("access denied", "zugriff verweigert", "captcha", "pardon our interruption", "bot or not", "unusual traffic")


def _http_get(url, headers, timeout=15):
    """Esmalt Chrome-TLS (curl_cffi, kui paigaldatud), siis tavaline requests."""
    if cffi_requests is not None:
        try:
            r = cffi_requests.get(url, headers=headers, impersonate="chrome", timeout=timeout)
            return r.status_code, r.text
        except Exception:
            pass
    r = get_robust_session().get(url, headers=headers, timeout=timeout)
    return r.status_code, r.text


def _looks_blocked(status, text):
    if status in (401, 403, 429):
        return True
    head = (text or "")[:4000].lower()
    return any(m in head for m in BLOCK_MARKERS) and "<h2" not in (text or "").lower()


def _mobile_get(url):
    """Tagastab (html | None, märkus). 404 -> ('', '404') et kutsuja saaks järgmist URL-i proovida."""
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.7",
        "Referer": "https://www.mobile.de/",
    }
    note = ""
    try:
        status, text = _http_get(url, headers)
        if status == 404:
            return "", "404"
        if status == 200 and not _looks_blocked(status, text):
            return text, "otse"
        note = f"otse HTTP {status}{' (blokeeritud)' if _looks_blocked(status, text) else ''}"
    except Exception as e:
        note = f"otse viga: {type(e).__name__}"

    if MOBILE_USE_PROXY_FALLBACK:
        try:
            r = get_robust_session().get(
                "https://r.jina.ai/" + url,
                headers={"X-Return-Format": "html", "X-No-Cache": "true", "Accept": "text/html"},
                timeout=40,
            )
            if r.status_code == 200 and "<h2" in r.text.lower() and not _looks_blocked(200, r.text):
                return r.text, "vahendaja"
            note += f"; vahendaja HTTP {r.status_code}"
        except Exception as e:
            note += f"; vahendaja viga: {type(e).__name__}"
    return None, note


def _clean_mobile_title(raw):
    t = re.sub(r"\s+", " ", raw or "").strip()
    t = re.sub(r"^(?:(?:Gesponsert|Sponsored|NEU|NEW)\s*)+", "", t)
    t = re.sub(r"\b(R 5) 5 (?=E-Tech|Electric|Techno|Evolution|Iconic|Urban)", r"\1 ", t, flags=re.I)
    t = re.sub(r"^(Renault R 5)(?=[A-Z0-9])", r"\1 ", t)
    return t.strip()


def _parse_mobile_html(html_text):
    """Tagastab (R5 elektriautod, kaartide koguarv lehel). Jätab välja 'Andere Farbe' soovitused."""
    soup = BeautifulSoup(html_text, "html.parser")
    out, seen, total_cards = [], set(), 0
    for a in soup.find_all("a", href=True):
        m = MOBILE_ID_RE.search(a["href"])
        if not m:
            continue
        ad_id = m.group(1) or m.group(2)
        if ad_id in seen:
            continue
        card, hops = a, 0
        while card is not None and hops < 10 and not (card.find("h2") and "€" in card.get_text(" ")):
            card, hops = card.parent, hops + 1
        if card is None or hops >= 10:
            continue
        ids = set()
        for x in card.find_all("a", href=True):
            mm = MOBILE_ID_RE.search(x["href"])
            if mm:
                ids.add(mm.group(1) or mm.group(2))
        if len(ids) > 1:  # ronis liiga kõrgele - mitu kuulutust korraga
            continue
        seen.add(ad_id)
        total_cards += 1

        text = card.get_text(" ", strip=True)
        if re.search(r"Andere Farbe|Other colou?r", text, re.I):  # mobile.de lisab teise värvi soovitusi
            continue
        h2 = card.find("h2")
        title = _clean_mobile_title(h2.get_text(" ", strip=True) if h2 else "")
        if not re.search(r"\bR\s?5\b|Renault 5", title, re.I) or not re.search(r"Elektro|Electric", text, re.I):
            continue
        reg = re.search(r"\bEZ\s*(\d{2}/\d{4}|\d{4})\b", text)
        if reg and int(reg.group(1)[-4:]) < 2023:  # klassikaline R5
            continue

        price_m = re.search(r"(\d{1,3}(?:\.\d{3})+)\s*€", text)
        price = int(price_m.group(1).replace(".", "")) if price_m else None
        km = re.search(r"(\d{1,3}(?:\.\d{3})*)\s*km\b", text)
        flags = [w for w in ("Neuwagen", "Tageszulassung", "Vorführfahrzeug", "Unfallfrei") if w in text]

        seller, logo = "", card.find("img", alt=re.compile(r"^Logo "))
        if logo:
            seller = logo["alt"][5:].strip()
        loc_m = re.search(r"(AT|BE|ES|FR|IT|LU|NL|SI|PL|CZ|DK|DE)-(\d{3,5})\s+([^\d]{2,30})", text)
        de_m = re.search(r"(?<!\d)(\d{5})\s*([A-ZÄÖÜ][A-Za-zäöüÄÖÜß\-\./ ]{2,30})", text)
        location = "Saksamaa"
        if loc_m:
            city = re.sub(r"\s*(Ohne Bewertung|Kontakt|Parken|Sterne).*$", "", loc_m.group(3)).strip()
            location = f"{COUNTRY_NAMES.get(loc_m.group(1), loc_m.group(1))}, {loc_m.group(2)} {city}".strip()
        elif de_m:
            city = re.sub(r"\s*(Ohne Bewertung|Kontakt|Parken|Sterne).*$", "", de_m.group(2)).strip()
            location = f"Saksamaa, {de_m.group(1)} {city}".strip()

        image = None
        for img in card.find_all("img"):
            src = img.get("src") or img.get("data-src") or (img.get("srcset") or "").split(" ")[0]
            if src and "classistatic" in src and not (img.get("alt") or "").startswith("Logo"):
                image = _clean_img(src)
                break

        out.append(
            {
                "title": title, "price_val": price,
                "link": f"{MOBILE_BASE}/fahrzeuge/details.html?id={ad_id}",
                "image": image, "location": location,
                "km": f"{km.group(1).replace('.', ' ')} km" if km else "",
                "reg": reg.group(1) if reg else "", "seller": seller,
                "flags": flags, "source": "mobile.de",
            }
        )
    return out, total_cards


def _collect_mobile():
    """mobile.de: tagastab (kuulutused, aruanne). Ebaõnnestumisel tühi list - AutoScout24 töötab edasi."""
    report, items, seen = [], [], set()
    for base in MOBILE_YELLOW_URLS:
        name = base.rsplit("/", 1)[-1]
        html_text, note = _mobile_get(base)
        if html_text == "":  # 404 - proovi järgmist aadressi
            report.append(f"mobile.de {name}: lehte pole (404)")
            continue
        if not html_text:
            report.append(f"mobile.de {name}: ei õnnestunud ({note})")
            break  # blokeeritud - teised aadressid annavad sama tulemuse
        pages = {1: html_text}
        report.append(f"mobile.de {name} lk 1: laetud ({note})")

        def load(p, base=base):
            return p, _mobile_get(f"{base}?pageNumber={p}")

        with ThreadPoolExecutor(max_workers=3) as ex:
            for p, (h, n) in ex.map(load, range(2, MOBILE_MAX_PAGES + 1)):
                if h:
                    pages[p] = h
                else:
                    report.append(f"mobile.de {name} lk {p}: {n or 'tühi'}")

        for p in sorted(pages):
            page_items, cards = _parse_mobile_html(pages[p])
            new = [i for i in page_items if i["link"] not in seen]
            for i in new:
                seen.add(i["link"])
            items.extend(new)
            report.append(f"mobile.de {name} lk {p}: {cards} kaarti, {len(new)} uut kollast R5")
        if items:
            break
    return items, report


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def fetch_renault_5_yellow_ev():
    """Päris kuulutused: kollane Renault 5 elektriauto, Euroopa, kõik müüjad (AutoScout24 + mobile.de).
    Kui MÕLEMAD ebaõnnestuvad, viskab erandi, et tühja tulemust ei puhverdataks."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_as, f_mo = ex.submit(_collect_as24), ex.submit(_collect_mobile)
        try:
            as_items, as_report = f_as.result()
        except Exception as e:
            as_items, as_report = [], [f"AutoScout24 viga: {type(e).__name__}: {e}"]
        try:
            mo_items, mo_report = f_mo.result()
        except Exception as e:
            mo_items, mo_report = [], [f"mobile.de viga: {type(e).__name__}: {e}"]
    report = as_report + mo_report
    all_items = as_items + mo_items
    if not all_items:
        raise RuntimeError("Kumbki portaal ei andnud kuulutusi.\n" + "\n".join(report[:10]))

    result = []
    for it in all_items:
        title = re.sub(r"\s+", " ", it["title"]).strip()
        parts = [p for p in (
            it["reg"] and f"Esmane reg. {it['reg']}", it["km"],
            ", ".join(it.get("flags") or []), it["seller"] and f"Müüja: {it['seller']}",
        ) if p]
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
                "source": it.get("source", "AutoScout24"),
            }
        )
    result.sort(key=lambda x: x["price_val"])
    counts = {}
    for r in result:
        counts[r["source"]] = counts.get(r["source"], 0) + 1
    return {"items": result, "report": report, "counts": counts}


def r5_search_links():
    """Kontrollitud otselingid teistele portaalidele (kollane Renault 5)."""
    return [
        ("AutoScout24 – kollane Renault 5 (kogu Euroopa)", AS24_YELLOW_URL + "?sort=price&desc=0"),
        ("AutoScout24.de – Renault R 5 gelb", "https://www.autoscout24.de/lst/renault/r-5/bc_gelb"),
        ("Mobile.de – kollased Renault'd (otsi R 5)", "https://suchen.mobile.de/auto/renault-gelb.html"),
        ("Mobile.de – Renault R 5 E-Tech Evolution", "https://suchen.mobile.de/auto/renault-r-5-e-tech-evolution.html"),
        ("Das Parking – Renault R 5 gelb", "https://www.dasparking.de/gebrauchtwagen/renault-r-5-gelb.html"),
        ("AutoUncle – Renault 5 E-Tech", "https://www.autouncle.de/de/gebrauchtwagen/Renault/5%20E-Tech"),
    ]


@st.cache_data(ttl=86400)
def fetch_reitingud_html():
    url = "https://reitingud.ee/reitingud/"
    try:
        res = get_robust_session().get(url, headers={"User-Agent": UA}, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for selector in ["footer", ".newsletter", ".newsletter-form", ".footer-info", "#footer", ".site-footer", ".contact-info"]:
                for match in soup.select(selector):
                    match.decompose()
            for element in soup.find_all(["p", "div", "section"]):
                if getattr(element, "decomposed", False):
                    continue
                text_content = element.get_text()
                if "TELLI UUDISKIRI" in text_content or "MTÜ Ühiskonnauuringute Instituut" in text_content or "Uuringufirma" in text_content:
                    element.decompose()
            out = str(soup)
            out = re.sub(r"Norstat", "Eesti reitingud globaalselt", out, flags=re.IGNORECASE)
            return out.replace("<head>", '<head><base href="https://reitingud.ee/">', 1)
    except Exception as e:
        print(f"Reitingud laadimise viga: {e}")
    return None


@st.cache_data(ttl=900, show_spinner=False)
def fetch_free_items(rss_url):
    results = []
    resp = get_robust_session().get(rss_url, headers={"User-Agent": UA}, timeout=10)
    if resp.status_code != 200:
        return results
    soup = BeautifulSoup(resp.content, "xml")
    one_month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    sold_keywords = ["broneeritud", "läinud", "ära antud", "annatud", "läks", "müüdud", "bron"]

    for item in soup.find_all(["item", "entry"]):
        link = "https://www.facebook.com/groups/442569942509759"
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

        image_url = None
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
    return filter_valid_items(results, link_key="link")


# -----------------------------------------------------------------------------
# 4. OTSINGURIBA JA SEKTSIOONID
# -----------------------------------------------------------------------------
col_search, col_fav = st.columns([3, 1])
with col_search:
    search_query = st.text_input(
        "🔍 Otsi märksõna järgi kõigist kuulutustest...",
        placeholder="nt vaip, diivan, Renault, garaaž...",
    )
with col_fav:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    st.write(f"⭐ Salvestatud lemmikuid: **{len(st.session_state.favorites)}**")

selected_tab = st.radio(
    "Vali vaade:",
    [
        "🎁 Tasuta asjad", "🏢 Kinnisvara objektid", "⚡ Renault 5 EV",
        "🛒 Toidu sooduspakkumised", "🚗 Kütusehinnad & Parkimine",
        "📈 Eesti reitingud", "⭐ Minu lemmikud",
    ],
    horizontal=True,
    label_visibility="collapsed",
)
st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

# --- 1. SEKTSIOON: TASUTA ASJAD ---
if selected_tab == "🎁 Tasuta asjad":
    try:
        with st.spinner("Laen tasuta kuulutusi..."):
            free_items = fetch_free_items("https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml")
    except Exception as e:
        print(f"Viga Facebooki RSS skännimisel: {e}")
        free_items = []
    free_items = [i for i in free_items if matches(search_query, i["title"], i["description"])]
    if not free_items:
        st.info("Hetkel ei ole saadaval ühtegi aktiivset või otsingule vastavat tasuta kuulutust.")
    for idx, item in enumerate(free_items):
        badges = (
            '<span class="badge-pill badge-free">Tasuta</span>'
            f'<span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
        )
        render_card(item, f"fav_fb_{idx}", "👉 Vaata kuulutust Facebookis", badges)

# --- 2. SEKTSIOON: KINNISVARA OBJEKTID ---
elif selected_tab == "🏢 Kinnisvara objektid":
    with st.spinner("Skännin Kinnisvara24 aktiivseid garaažipakkumisi..."):
        kv24_items = fetch_live_kv24_garages()
    canonical_kv24_url = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    if not kv24_items:
        kv24_items = [{
            "title": "Garaažide müügipakkumised Harju maakonnas",
            "description": "Ava Harjumaa ja Tallinna garaažibokside reaalajas avalikud pakkumised Kinnisvara24 portaalis.",
            "price": "Vaata portaalist", "location": "Harju maakond", "url": canonical_kv24_url,
        }]
    for idx, item in enumerate(kv24_items):
        if not matches(search_query, item["title"], item["description"]):
            continue
        badges = (
            f'<span class="badge-pill badge-price">{esc(item["price"])}</span>'
            f'<span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
        )
        render_card(item, f"fav_kv24_{idx}", "👉 Ava pakkumine Kinnisvara24 portaalis", badges,
                    link=item.get("url", canonical_kv24_url))

# --- 3. SEKTSIOON: RENAULT 5 EV ---
elif selected_tab == "⚡ Renault 5 EV":
    st.markdown("### ⚡ Renault 5 E-Tech (kollane) – päris kuulutused Euroopast")
    st.info(
        "Ainult elektriline Renault 5 kollases värvitoonis, kõik müüjad kogu Euroopas "
        "(DE, AT, BE, ES, FR, IT, LU, NL). Andmed tulevad AutoScout24-st ja mobile.de-st ning uuenevad iga 6 tunni järel."
    )

    c_var, c_src, c_sort = st.columns([2, 1, 1])
    with c_var:
        variant_label = st.selectbox("Variant", list(VARIANTS.keys()))
    with c_src:
        source_label = st.selectbox("Allikas", ["Kõik allikad", "AutoScout24", "mobile.de"])
    with c_sort:
        sort_label = st.selectbox("Järjekord", ["Odavaim ees", "Kallim ees"])

    r5_data, r5_error = None, None
    try:
        with st.spinner("Otsin Euroopa kuulutustest kollast Renault 5 E-Techi..."):
            r5_data = fetch_renault_5_yellow_ev()
    except Exception as e:
        r5_error = str(e)

    if r5_data:
        keys = VARIANTS[variant_label]
        r5_items = [
            d for d in r5_data["items"]
            if (keys is None or any(k in d["title"].lower() for k in keys))
            and (source_label == "Kõik allikad" or d["source"] == source_label)
            and matches(search_query, d["title"], d["description"], d["location"])
        ]
        if sort_label == "Kallim ees":
            r5_items = list(reversed(r5_items))
        per_source = ", ".join(f"{k}: {v}" for k, v in r5_data["counts"].items())
        st.caption(f"Leitud {len(r5_items)} kuulutust (kokku {len(r5_data['items'])} kollast Renault 5 – {per_source}).")
        if "mobile.de" not in r5_data["counts"]:
            st.caption("ℹ️ mobile.de ei andnud praegu andmeid (portaal blokeerib serveripäringuid) – vaata 'Tehniline info'.")
        if not r5_items:
            st.warning("Valitud filtritega kuulutusi ei leitud. Proovi variant 'Kõik variandid'.")
        for idx, deal in enumerate(r5_items):
            badges = (
                f'<span class="badge-pill badge-yellow">{esc(deal["price"])}</span>'
                '<span class="badge-pill badge-price">🟡 Kollane</span>'
                + f'<span class="badge-pill badge-location">🌐 {esc(deal["source"])}</span>'
                + (f'<span class="badge-pill badge-price">🔋 {esc(deal["battery"])}</span>' if deal["battery"] else "")
                + f'<span class="badge-pill badge-location">📍 {esc(deal["location"])}</span>'
            )
            render_card(
                deal, f"fav_r5_{idx}", f"👉 Ava kuulutus {deal['source']}-s", badges,
                secondary=("🌐 Ava eestikeelsena (Google Translate)",
                           "https://translate.google.com/translate?sl=auto&tl=et&u=" + urllib.parse.quote(deal["link"], safe="")),
            )
    else:
        st.warning(
            "Automaatne otsing ei saanud praegu AutoScout24-st ega mobile.de-st andmeid (portaalid võivad päringuid blokeerida). "
            "Ava otsing otse allolevatest nuppudest – need on samad filtrid (Renault R 5, kollane)."
        )
        render_card(
            {"title": "Kollane Renault 5 E-Tech – kõik pakkumised Euroopas",
             "description": "Otsing AutoScout24-s: Renault R 5, värv kollane, hind odavaimast kallimani."},
            "noop_r5", "👉 Ava AutoScout24 otsing", '<span class="badge-pill badge-yellow">🟡 Kollane</span>',
            link=AS24_YELLOW_URL + "?sort=price&desc=0", fav_button=False,
        )
        render_card(
            {"title": "Kollased Renault'd mobile.de-s (otsi R 5)",
             "description": "mobile.de filter 'Außenfarbe: Gelb', Renault. Vali nimekirjast Renault R 5."},
            "noop_r5_mobile", "👉 Ava mobile.de otsing", '<span class="badge-pill badge-yellow">🟡 Kollane</span>',
            link=MOBILE_YELLOW_URLS[1], fav_button=False,
        )
        with st.expander("🛠 Tehniline info"):
            st.code(r5_error or "teadmata viga")

    with st.expander("🔗 Teised portaalid (kollane Renault 5)", expanded=False):
        for label, url in r5_search_links():
            st.markdown(f"- [{label}]({url})")
    if r5_data:
        with st.expander("🛠 Tehniline info"):
            st.code("\n".join(r5_data["report"]))

# --- 4. SEKTSIOON: TOIDU SOODUSPAKKUMISED ---
elif selected_tab == "🛒 Toidu sooduspakkumised":
    st.markdown("### 🛒 Toidupakkumised")
    st.info("Näidisandmed – hinnad ei uuendu automaatselt. Kehtivad pakkumised vaata poodide lehtedelt.")
    food_deals = [
        {"store": "Selver", "title": "Banaani kg", "price": "0.99 €", "desc": "Soodushind kampaaniakirja alusel.", "link": "https://www.selver.ee"},
        {"store": "Rimi", "title": "Kohupiimamaius Karums 45g", "price": "0.39 €", "desc": "Erinevad maitsed igapäevaselt parima hinnaga.", "link": "https://www.rimi.ee"},
        {"store": "Maxima", "title": "Jahutatud broilerifilee 1kg", "price": "4.99 €", "desc": "Värske kodumaine kanafilee.", "link": "https://www.maxima.ee"},
        {"store": "Coop", "title": "Eesti või 82% 200g", "price": "1.49 €", "desc": "Säästukaardiga tavapärase taseme tipphind.", "link": "https://www.coop.ee"},
    ]
    for idx, deal in enumerate(food_deals):
        if not matches(search_query, deal["title"], deal["store"]):
            continue
        item = {**deal, "title": f"{deal['store']}: {deal['title']}", "description": deal["desc"]}
        badges = (
            f'<span class="badge-pill badge-yellow">{esc(deal["price"])}</span>'
            '<span class="badge-pill badge-location">📍 Kõik kauplused</span>'
        )
        render_card(item, f"fav_deal_{idx}", "👉 Vaata e-poest", badges)

# --- 5. SEKTSIOON: KÜTUSEHINNAD & PARKIMINE ---
elif selected_tab == "🚗 Kütusehinnad & Parkimine":
    st.markdown("### 🚗 Kütusehinnad & tasuta parkimine")
    st.info("Hinnad on ligikaudsed näidised. Täpsed hinnad: Fuelo.")
    col1, col2 = st.columns(2)
    with col1:
        show_html("""
        <div class="pro-card">
            <div class="card-title">⛽ Ligikaudsed kütusehinnad Tallinnas</div>
            <div class="card-desc">
                • <b>Bensiin 95:</b> ~1.629 €/l<br>
                • <b>Bensiin 98:</b> ~1.679 €/l<br>
                • <b>Diislikütus:</b> ~1.549 €/l
            </div>
            <a href="https://fuelo.net/et/prices/country/Estonia" target="_blank" rel="noopener" class="pro-btn">👉 Vaata Fuelo kütusekaarti</a>
        </div>
        """)
    with col2:
        show_html("""
        <div class="pro-card">
            <div class="card-title">🅿️ Tasuta parkimine Harjumaal</div>
            <div class="card-desc">
                • <b>Kristiine Keskus:</b> 2h tasuta (parkimiskellaga)<br>
                • <b>Ülemiste Keskus:</b> väliparklas tasuta<br>
                • <b>Rocca al Mare:</b> parkimismajas tasuta
            </div>
            <a href="https://www.parkimine.ee" target="_blank" rel="noopener" class="pro-btn">👉 Vaata Parkimine.ee kaarti</a>
        </div>
        """)

# --- 6. SEKTSIOON: EESTI REITINGUD ---
elif selected_tab == "📈 Eesti reitingud":
    st.markdown("### Eesti reitingud reaalajas praegu")
    st.markdown("---")
    reitingud_html = fetch_reitingud_html()
    if reitingud_html:
        components.html(reitingud_html, height=850, scrolling=True)
    else:
        components.iframe("https://reitingud.ee/reitingud/", height=850, scrolling=True)

# --- 7. SEKTSIOON: SALVESTATUD LEMMIKUD ---
elif selected_tab == "⭐ Minu lemmikud":
    st.markdown("### ⭐ Sinu salvestatud kuulutused")
    if not st.session_state.favorites:
        st.info("Sa ei ole veel ühtegi kuulutust lemmikutesse salvestanud.")
    for idx, item in enumerate(list(st.session_state.favorites)):
        render_card(item, f"noop_fav_{idx}", "👉 Vaata originaalkuulutust", fav_button=False)
        if st.button("❌ Eemalda lemmikutest", key=f"remove_fav_{idx}"):
            st.session_state.favorites.pop(idx)
            st.rerun()
