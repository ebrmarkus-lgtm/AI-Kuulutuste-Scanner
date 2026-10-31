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

# -----------------------------------------------------------------------------
# 1. SEADISTUS JA DISAIN
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
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .stApp { background-color: #0b0f19; color: #f8fafc; }
    .hero-container { padding: 0.5rem 0 1.25rem 0; border-bottom: 1px solid #1e293b; margin-bottom: 1.5rem; }
    .main-title { font-size: 2.2rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.025em; margin-bottom: 0.25rem; }
    .sub-title { font-size: 0.95rem; color: #94a3b8; font-weight: 400; }

    .pro-card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 24px;
                margin-bottom: 8px; box-shadow: 0 4px 20px rgba(0,0,0,.4); transition: all .2s ease; }
    .pro-card:hover { transform: translateY(-2px); border-color: #374151; box-shadow: 0 10px 30px rgba(0,0,0,.6); }
    .card-row { display: flex; gap: 22px; align-items: flex-start; }
    .card-img { flex: 0 0 280px; max-width: 280px; }
    .card-img img { width: 100%; border-radius: 12px; display: block; object-fit: cover; aspect-ratio: 4/3; }
    .card-body { flex: 1; min-width: 0; }
    @media (max-width: 700px) { .card-row { flex-direction: column; } .card-img { flex: none; max-width: 100%; width: 100%; } }

    .card-title { font-size: 1.2rem; font-weight: 700; color: #f8fafc; line-height: 1.4; margin-bottom: 6px; }
    .card-date { font-size: .8rem; font-weight: 500; color: #94a3b8; margin-bottom: 12px; }
    .card-desc { font-size: .95rem; color: #cbd5e1; line-height: 1.6; margin-bottom: 18px; }
    .card-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
    .badge-pill { padding: 5px 12px; border-radius: 20px; font-size: .775rem; font-weight: 600; }
    .badge-free { background: rgba(5,150,105,.15); color: #34d399; border: 1px solid rgba(5,150,105,.3); }
    .badge-price { background: rgba(37,99,235,.15); color: #60a5fa; border: 1px solid rgba(37,99,235,.3); }
    .badge-location { background: rgba(71,85,105,.2); color: #94a3b8; border: 1px solid rgba(71,85,105,.4); }
    .badge-yellow { background: rgba(234,179,8,.2); color: #facc15; border: 1px solid rgba(234,179,8,.4); }
    .pro-btn { display: inline-flex; align-items: center; justify-content: center; width: 100%; padding: 11px 18px;
               background: #2563eb; color: #fff !important; font-size: .9rem; font-weight: 600; border-radius: 10px;
               text-decoration: none !important; transition: all .2s ease; }
    .pro-btn:hover { background: #1d4ed8; box-shadow: 0 4px 15px rgba(37,99,235,.4); }
    .pro-btn.secondary { background: #1f2937; border: 1px solid #374151; margin-top: 8px; }
    .pro-btn.secondary:hover { background: #273449; }
</style>
"""
st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

if "favorites" not in st.session_state:
    st.session_state.favorites = []

st.markdown(
    """
    <div class="hero-container">
        <div class="main-title">⚡ AI Kuulutuste Skänner Pro</div>
        <div class="sub-title">FB Free, KV24, Renault 5 E-Tech (kollane) Euroopas, toidupakkumised &amp; kütusehinnad</div>
    </div>
    """,
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
    """HTML-i põgenemine, et kuulutuste tekst ei lõhuks lehte."""
    return html_lib.escape(str(value if value is not None else ""), quote=True)


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
        res = get_robust_session().head(
            url, headers={"User-Agent": UA}, timeout=3, allow_redirects=True
        )
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


def add_favorite(item):
    link = item.get("link") or item.get("url")
    if any((f.get("link") or f.get("url")) == link for f in st.session_state.favorites):
        st.toast("See on juba lemmikutes.")
        return
    st.session_state.favorites.append(item)
    st.toast("Salvestatud lemmikutesse! ⭐")


def render_card(item, key, button_text, badges, link=None, secondary=None):
    """Üks ühtne kaardi-renderdaja (parandab varasema katkise HTML-i, kus pilt jäi kaardist välja)."""
    link = link or item.get("link") or item.get("url") or "#"
    img_html = ""
    if item.get("image"):
        img_html = f'<div class="card-img"><img src="{esc(item["image"])}" loading="lazy" referrerpolicy="no-referrer" alt=""></div>'
    date_html = f'<div class="card-date">{esc(item["date_str"])}</div>' if item.get("date_str") else ""
    sec_html = (
        f'<a href="{esc(secondary[1])}" target="_blank" rel="noopener" class="pro-btn secondary">{esc(secondary[0])}</a>'
        if secondary
        else ""
    )
    st.markdown(
        f"""
        <div class="pro-card"><div class="card-row">
            {img_html}
            <div class="card-body">
                <div class="card-title">{esc(item.get('title'))}</div>
                {date_html}
                <div class="card-desc">{esc(item.get('description') or item.get('desc'))}</div>
                <div class="card-tags">{badges}</div>
                <a href="{esc(link)}" target="_blank" rel="noopener" class="pro-btn">{esc(button_text)}</a>
                {sec_html}
            </div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("⭐ Salvesta lemmikutesse", key=key):
        add_favorite(item)


def matches(query, *fields):
    if not query:
        return True
    q = query.lower()
    return any(q in str(f or "").lower() for f in fields)


# -----------------------------------------------------------------------------
# 3. ANDMEKORJE
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


# ---- Renault 5 E-Tech, kollane, kogu Euroopa ---------------------------------
AS24_BASE = "https://www.autoscout24.com"
# Riigid: DE, AT, BE, ES, FR, IT, LU, NL
AS24_COUNTRIES = "D,A,B,E,F,I,L,NL"
AS24_SEARCH = (
    AS24_BASE + "/lst/renault/5?atype=C&fuel=E&cy=" + urllib.parse.quote(AS24_COUNTRIES, safe="")
    + "&sort=price&desc=0&ustate=N%2CU"
)
YELLOW_RE = re.compile(
    r"\b(yellow|gelb|jaune|geel|giallo|amarillo|gul|keltainen|kollane|pop\s*yellow|jaune\s*pop)\b",
    re.IGNORECASE,
)
COUNTRY_NAMES = {
    "D": "Saksamaa", "DE": "Saksamaa", "A": "Austria", "AT": "Austria", "B": "Belgia", "BE": "Belgia",
    "E": "Hispaania", "ES": "Hispaania", "F": "Prantsusmaa", "FR": "Prantsusmaa", "I": "Itaalia",
    "IT": "Itaalia", "L": "Luksemburg", "LU": "Luksemburg", "NL": "Holland",
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


def _next_data(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        return json.loads(tag.string)
    except Exception:
        return None


def _clean_img(url):
    if not url:
        return None
    url = re.sub(r"/\{?\d+x\d+\}?(\.\w+)?$", "", url)  # eemalda suuruse-lõpp
    url = url.replace("{width}", "800").replace("{height}", "600")
    return url if url.startswith("http") else None


def _parse_as24_listing(raw):
    vehicle = raw.get("vehicle") or {}
    make = str(vehicle.get("make", "")).lower()
    model = str(vehicle.get("model", "")).strip().lower()
    if make != "renault" or model not in ("5", "5 e-tech", "r5"):
        return None

    version = vehicle.get("modelVersionInput") or vehicle.get("variant") or ""
    title = f"Renault 5 {version}".strip()

    price_raw = _dig(raw, "price", "priceRaw") or _dig(raw, "prices", "public", "priceRaw")
    price_txt = _dig(raw, "price", "priceFormatted") or _dig(raw, "prices", "public", "priceFormatted")
    if not price_txt and price_raw:
        price_txt = f"{int(price_raw):,} €".replace(",", " ")
    try:
        price_val = int(price_raw) if price_raw else 10**9
    except (TypeError, ValueError):
        price_val = 10**9

    loc = raw.get("location") or {}
    cc = str(loc.get("countryCode", "")).upper()
    city = loc.get("city", "")
    location = ", ".join(x for x in (city, COUNTRY_NAMES.get(cc, cc)) if x) or "Euroopa"

    images = raw.get("images") or []
    image = _clean_img(images[0]) if images and isinstance(images[0], str) else None

    km = _dig(raw, "tracking", "mileage") or vehicle.get("mileageInKm") or ""
    seller = _dig(raw, "seller", "companyName") or _dig(raw, "seller", "type") or ""
    url = raw.get("url") or ""
    if url.startswith("/"):
        url = AS24_BASE + url

    return {
        "title": title,
        "description": " · ".join(
            x for x in (
                vehicle.get("subtitle") or "",
                f"{km} km" if km else "",
                f"Müüja: {seller}" if seller else "",
            ) if x
        ) or "Renault 5 E-Tech elektriauto.",
        "price": price_txt or "Hind puudub",
        "price_val": price_val,
        "location": location,
        "link": url,
        "image": image,
        "_blob": json.dumps(raw, ensure_ascii=False).lower(),
    }


def _fetch_as24_page(page):
    try:
        r = get_robust_session().get(
            f"{AS24_SEARCH}&page={page}",
            headers={"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"},
            timeout=12,
        )
        if r.status_code != 200:
            return [], f"AutoScout24 vastas koodiga {r.status_code}"
        data = _next_data(r.text)
        listings = _dig(data, "props", "pageProps", "listings", default=[]) if data else []
        return listings or [], None
    except Exception as e:
        return [], str(e)


def _detail_is_yellow(item):
    """Avab kuulutuse lehe ja kontrollib auto värvi (kui otsingu andmetes värvi pole)."""
    if YELLOW_RE.search(item["_blob"]) or YELLOW_RE.search(item["title"]):
        return True
    try:
        r = get_robust_session().get(item["link"], headers={"User-Agent": UA}, timeout=10)
        if r.status_code != 200:
            return False
        data = _next_data(r.text)
        blob = json.dumps(_dig(data, "props", "pageProps", default={}), ensure_ascii=False)
        # Otsime ainult värvivälju, et mitte tabada suvalist teksti
        for m in re.finditer(r'"(?:bodyColor|manufacturerColor|color|colour)[A-Za-z]*"\s*:\s*"([^"]+)"', blob, re.IGNORECASE):
            if YELLOW_RE.search(m.group(1)):
                return True
        soup = BeautifulSoup(r.text, "html.parser")
        for dt in soup.find_all(["dt", "span", "div"]):
            t = dt.get_text(strip=True).lower()
            if t in ("colour", "color", "farbe", "couleur", "body colour", "body color", "manufacturer colour", "manufacturer color"):
                sib = dt.find_next(["dd", "span", "div"])
                if sib and YELLOW_RE.search(sib.get_text(" ", strip=True)):
                    return True
    except Exception:
        pass
    return False


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def fetch_renault_5_yellow_ev(max_pages=4):
    """Päris kuulutused: Renault 5 E-Tech elektriauto, kollane, Euroopa (AutoScout24)."""
    raw_all, errors = [], []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for listings, err in ex.map(_fetch_as24_page, range(1, max_pages + 1)):
            raw_all.extend(listings)
            if err:
                errors.append(err)

    parsed, seen = [], set()
    for raw in raw_all:
        item = _parse_as24_listing(raw)
        if item and item["link"] and item["link"] not in seen:
            seen.add(item["link"])
            parsed.append(item)

    with ThreadPoolExecutor(max_workers=6) as ex:
        flags = list(ex.map(_detail_is_yellow, parsed))
    yellow = [it for it, ok in zip(parsed, flags) if ok]
    for it in yellow:
        it.pop("_blob", None)
    yellow.sort(key=lambda x: x["price_val"])
    return {"items": yellow, "total_r5": len(parsed), "errors": errors[:2]}


def r5_search_links():
    """Otselingid sama filtriga teistele portaalidele (kui automaatne otsing midagi ei leia)."""
    return [
        ("AutoScout24 (Euroopa, odavaim ees)", AS24_SEARCH),
        ("Mobile.de – Renault 5 elektriline", "https://suchen.mobile.de/fahrzeuge/search.html?isSearchRequest=true&makeModelVariant1.makeId=19000&makeModelVariant1.modelDescription=5&fuel=ELECTRICITY&sortOption.sortBy=searchNetGrossPrice&sortOption.sortOrder=ASCENDING"),
        ("La Centrale (Prantsusmaa)", "https://www.lacentrale.fr/listing?makesModelsCommercialNames=RENAULT%3A5&energies=elec&sortBy=priceAsc"),
        ("Marktplaats (Holland)", "https://www.marktplaats.nl/q/renault+5+e-tech+geel/"),
        ("Autoscout24.de – Renault 5 gelb", "https://www.autoscout24.de/lst/renault/5?fuel=E&sort=price&desc=0"),
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
                if element.decomposed:
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
# 4. OTSING JA SEKTSIOONID
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

# --- 1. TASUTA ASJAD ---
if selected_tab == "🎁 Tasuta asjad":
    try:
        with st.spinner("Laen tasuta kuulutusi..."):
            items = fetch_free_items("https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml")
    except Exception as e:
        print(f"Viga Facebooki RSS skännimisel: {e}")
        items = []
    items = [i for i in items if matches(search_query, i["title"], i["description"])]
    if not items:
        st.info("Hetkel ei ole saadaval ühtegi aktiivset või otsingule vastavat tasuta kuulutust.")
    for idx, item in enumerate(items):
        badges = (
            '<span class="badge-pill badge-free">Tasuta</span>'
            f'<span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
        )
        render_card(item, f"fav_fb_{idx}", "👉 Vaata kuulutust Facebookis", badges)

# --- 2. KINNISVARA ---
elif selected_tab == "🏢 Kinnisvara objektid":
    with st.spinner("Skännin Kinnisvara24 aktiivseid garaažipakkumisi..."):
        kv24_items = fetch_live_kv24_garages()
    canonical = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
    if not kv24_items:
        kv24_items = [{
            "title": "Garaažide müügipakkumised Harju maakonnas",
            "description": "Ava Harjumaa ja Tallinna garaažibokside avalikud pakkumised Kinnisvara24 portaalis.",
            "price": "Vaata portaalist", "location": "Harju maakond", "url": canonical,
        }]
    for idx, item in enumerate(kv24_items):
        if not matches(search_query, item["title"], item["description"]):
            continue
        badges = (
            f'<span class="badge-pill badge-price">{esc(item["price"])}</span>'
            f'<span class="badge-pill badge-location">📍 {esc(item["location"])}</span>'
        )
        render_card(item, f"fav_kv24_{idx}", "👉 Ava pakkumine Kinnisvara24 portaalis", badges, link=item.get("url", canonical))

# --- 3. RENAULT 5 EV ---
elif selected_tab == "⚡ Renault 5 EV":
    st.markdown("### ⚡ Renault 5 E-Tech (kollane) – päris kuulutused Euroopast")
    st.info(
        "Otsitakse ainult elektrilist Renault 5 mudelit kollases värvitoonis, kõigilt müüjatelt "
        "(DE, AT, BE, ES, FR, IT, LU, NL). Hinna järgi odavaim ees. Uueneb iga 6 tunni järel."
    )
    with st.spinner("Otsin Euroopa kuulutustest kollast Renault 5 E-Techi..."):
        data = fetch_renault_5_yellow_ev()

    items = [d for d in data["items"] if matches(search_query, d["title"], d["description"], d["location"])]

    if items:
        st.caption(f"Leitud {len(items)} kollast Renault 5 (kokku vaadatud {data['total_r5']} Renault 5 kuulutust).")
    else:
        st.warning(
            "Automaatne otsing ei leidnud praegu ühtegi kollast Renault 5 kuulutust"
            + (f" ({'; '.join(data['errors'])})" if data["errors"] else "")
            + ". Portaal võib päringut blokeerida või kuulutusi pole. Kasuta allolevaid otselinke."
        )

    for idx, deal in enumerate(items):
        badges = (
            f'<span class="badge-pill badge-yellow">{esc(deal["price"])}</span>'
            '<span class="badge-pill badge-price">🟡 Kollane</span>'
            f'<span class="badge-pill badge-location">📍 {esc(deal["location"])}</span>'
        )
        render_card(
            deal, f"fav_r5_{idx}", "👉 Ava kuulutus", badges,
            secondary=("🌐 Ava eestikeelsena (Google Translate)",
                       "https://translate.google.com/translate?sl=auto&tl=et&u=" + urllib.parse.quote(deal["link"], safe="")),
        )

    with st.expander("🔗 Otsi ise teistel portaalidel (eelfiltreeritud)", expanded=not items):
        for label, url in r5_search_links():
            st.markdown(f"- [{label}]({url})")
        st.caption("Värvi filtreeri portaalis käsitsi: Colour/Farbe → Yellow/Gelb.")

# --- 4. TOIDUPAKKUMISED ---
elif selected_tab == "🛒 Toidu sooduspakkumised":
    st.markdown("### 🛒 Toidupakkumised")
    st.info("Näidisandmed – hinnad ei uuendu automaatselt. Kehtivad pakkumised vaata poodide lehtedelt.")
    deals = [
        {"store": "Selver", "title": "Banaani kg", "price": "0.99 €", "desc": "Soodushind kampaaniakirja alusel.", "link": "https://www.selver.ee"},
        {"store": "Rimi", "title": "Kohupiimamaius Karums 45g", "price": "0.39 €", "desc": "Erinevad maitsed.", "link": "https://www.rimi.ee"},
        {"store": "Maxima", "title": "Jahutatud broilerifilee 1kg", "price": "4.99 €", "desc": "Värske kodumaine kanafilee.", "link": "https://www.maxima.ee"},
        {"store": "Coop", "title": "Eesti või 82% 200g", "price": "1.49 €", "desc": "Säästukaardiga hind.", "link": "https://www.coop.ee"},
    ]
    for idx, deal in enumerate(deals):
        if not matches(search_query, deal["title"], deal["store"]):
            continue
        deal = {**deal, "title": f"{deal['store']}: {deal['title']}"}
        badges = (
            f'<span class="badge-pill badge-yellow">{esc(deal["price"])}</span>'
            '<span class="badge-pill badge-location">📍 Kõik kauplused</span>'
        )
        render_card(deal, f"fav_deal_{idx}", "👉 Vaata e-poest", badges)

# --- 5. KÜTUS & PARKIMINE ---
elif selected_tab == "🚗 Kütusehinnad & Parkimine":
    st.markdown("### 🚗 Kütusehinnad & tasuta parkimine")
    st.info("Hinnad on ligikaudsed näidised. Täpsed hinnad: Fuelo.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """<div class="pro-card"><div class="card-title">⛽ Ligikaudsed kütusehinnad Tallinnas</div>
            <div class="card-desc">• <b>Bensiin 95:</b> ~1.629 €/l<br>• <b>Bensiin 98:</b> ~1.679 €/l<br>• <b>Diislikütus:</b> ~1.549 €/l</div>
            <a href="https://fuelo.net/et/prices/country/Estonia" target="_blank" rel="noopener" class="pro-btn">👉 Vaata Fuelo kütusekaarti</a></div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """<div class="pro-card"><div class="card-title">🅿️ Tasuta parkimine Harjumaal</div>
            <div class="card-desc">• <b>Kristiine Keskus:</b> 2h tasuta (parkimiskellaga)<br>• <b>Ülemiste Keskus:</b> väliparklas tasuta<br>• <b>Rocca al Mare:</b> parkimismajas tasuta</div>
            <a href="https://www.parkimine.ee" target="_blank" rel="noopener" class="pro-btn">👉 Vaata Parkimine.ee kaarti</a></div>""",
            unsafe_allow_html=True,
        )

# --- 6. REITINGUD ---
elif selected_tab == "📈 Eesti reitingud":
    st.markdown("### Eesti reitingud")
    st.markdown("---")
    reitingud_html = fetch_reitingud_html()
    if reitingud_html:
        components.html(reitingud_html, height=850, scrolling=True)
    else:
        components.iframe("https://reitingud.ee/reitingud/", height=850, scrolling=True)

# --- 7. LEMMIKUD ---
elif selected_tab == "⭐ Minu lemmikud":
    st.markdown("### ⭐ Sinu salvestatud kuulutused")
    if not st.session_state.favorites:
        st.info("Sa ei ole veel ühtegi kuulutust lemmikutesse salvestanud.")
    for idx, item in enumerate(list(st.session_state.favorites)):
        link = item.get("link") or item.get("url") or "#"
        img_html = (
            f'<div class="card-img"><img src="{esc(item["image"])}" alt=""></div>' if item.get("image") else ""
        )
        st.markdown(
            f"""<div class="pro-card"><div class="card-row">{img_html}<div class="card-body">
            <div class="card-title">{esc(item.get('title', item.get('store', 'Lemmik')))}</div>
            <div class="card-desc">{esc(item.get('description') or item.get('desc'))}</div>
            <a href="{esc(link)}" target="_blank" rel="noopener" class="pro-btn">👉 Vaata originaalkuulutust</a>
            </div></div></div>""",
            unsafe_allow_html=True,
        )
        if st.button("❌ Eemalda lemmikutest", key=f"remove_fav_{idx}"):
            st.session_state.favorites.pop(idx)
            st.rerun()
