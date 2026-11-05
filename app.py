"""AI Kuulutuste Skänner Pro

Sõltuvused (requirements.txt):
    streamlit
    streamlit-autorefresh
    requests
    beautifulsoup4
    lxml
    tzdata
"""

import html
import re
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from bs4 import BeautifulSoup
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

# Leht uuendub iga 60 sekundi järel (andmed tulevad vahemälust, vt TTL).
st_autorefresh(interval=60_000, key="smart_live_refresh")

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
FEED_TTL = 900  # sekundit

FB_FEED_URL = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
GARAGE_FEED_URL = "https://rss.app/feeds/MjiyNEAjjPzTGkVZ.xml"
HANGE_FEED_URL = "https://rss.app/feeds/4QE7Z3yfpulhchLA.xml"

TAB_FREE = "🎁 Tasuta asjad"
TAB_GARAGES = "🚘 Kinnisvara garaažid"
TAB_GARDEN = "🌿 Aiatööd (Hange.ee)"
TAB_FOOD = "🛒 Toidukaubad"
TAB_INVEST = "📈 Lightyear Investeeringud"
TABS = [TAB_FREE, TAB_GARAGES, TAB_GARDEN, TAB_FOOD, TAB_INVEST]

GARDEN_REQUIRED = [
    "aia", "aiatöö", "haljast", "muru", "hekk", "heki",
    "viljapuu", "istut", "lillepeenar", "trimmer", "lehte",
    "multš", "freesi", "põõsa", "raie", "võsa",
    "kiviparkett", "terrass", "õue", "puu lõik",
]
GARDEN_FORBIDDEN = [
    "veearvesti", "termostaat", "mullivann", "vannituba",
    "sanitaartehn", "katus", "vundament", "torutöö",
    "elektritöö", "siseviimistlus", "plaatimine",
    "maalritöö", "fassaad", "betoon", "korteris",
    "korteri", "pesumasin", "külmkapp", "pliit",
]

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
.asset-row {
    display: flex; justify-content: space-between; align-items: center;
    gap: 12px; padding: 14px 0; border-bottom: 1px solid #1f2937;
}
.asset-row:last-child { border-bottom: none; }
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
    """HTML-escape kasutajale kuvatava teksti jaoks."""
    return html.escape(str(value if value is not None else ""), quote=True)


def show_html(markup: str):
    """Renderda HTML Streamlitis.

    Markdown tõlgendab 4+ tühikuga taandatud ridu koodiplokina ja tühi rida
    lõpetab HTML-ploki. Seepärast eemaldame taanded ja tühjad read.
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


def pill(css_class, text):
    return f'<span class="badge-pill {css_class}">{esc(text)}</span>'


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
              <div class="card-desc">{esc(item.get("description", ""))}</div>
              {tags_html}
              {button_html}
            </div>
          </div>
        </div>
        """
    )


def render_image_diagnostics(items, category_name):
    """Arenduse abivaade: näitab, kust iga RSS-kirje pildi sai."""
    with st.expander(f"🔎 Piltide diagnostika – {category_name}"):
        if not items:
            st.caption("Diagnostikaks pole kirjeid.")
            return
        for index, item in enumerate(items, start=1):
            title = item.get("title", "Pealkirjata")
            if item.get("image"):
                st.markdown(
                    f"**{index}. {title}** · allikas: `{item.get('image_source', 'teadmata')}`"
                )
                st.code(item["image"], language=None)
            else:
                st.markdown(f"**{index}. {title}** · pilt puudub")


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
    """Tagastab srcset-ist suurima laiusega URL-i."""
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
    if not variants:
        return None
    return max(variants, key=lambda v: v[0])[1]


def extract_real_image_details(entry, base_url=None):
    """Leia pilt ainult selle konkreetse RSS-kirje seest.

    Järjekord: media:content (pilt) -> media:thumbnail -> enclosure ->
    <img> kirjelduse HTML-ist. Kanalitaseme pilte ei kasutata.
    """
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
    # Atom: <link href="..."/>; RSS: <link>...</link>
    href = link_tag.get("href")
    if href:
        return safe_http_url(href, base_url=base_url)
    return safe_http_url(link_tag.get_text(" ", strip=True), base_url=base_url)


def extract_entry_text(entry, tag_names):
    for tag in entry.find_all(True):
        if local_name(tag) in tag_names:
            raw = "".join(str(child) for child in tag.contents) or tag.get_text(" ", strip=True)
            return BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    return ""


@st.cache_data(ttl=FEED_TTL, show_spinner=False)
def load_feed(feed_url, kind):
    """Loeb RSS/Atom voo. kind: 'standard' või 'gardening'.

    Vea korral visatakse erand, mistõttu ebaõnnestunud päringut ei cache'ita.
    """
    feed_url = safe_http_url(feed_url)
    if not feed_url:
        raise ValueError("Vigane RSS-voo URL.")

    response = requests.get(feed_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "xml")

    results = []
    for entry in soup.find_all(["item", "entry"]):
        if len(results) >= MAX_LIMIT:
            break

        title = extract_entry_text(entry, {"title"}) or "Kirje"
        description = extract_entry_text(entry, {"description", "summary", "encoded"})

        if kind == "gardening":
            text = f"{title} {description}".casefold()
            if any(w in text for w in GARDEN_FORBIDDEN):
                continue
            if not any(w in text for w in GARDEN_REQUIRED):
                continue

        link = extract_entry_link(entry, base_url=feed_url)
        image = extract_real_image_details(entry, base_url=link or feed_url)

        results.append(
            {
                "title": title,
                "description": description[:200] + ("..." if len(description) > 200 else ""),
                "location": "Eesti",
                "link": link,
                "image": image["url"],
                "image_source": image["source"],
                "date_str": "📅 Aiatöö hange" if kind == "gardening" else "📅 RSS-kuulutus",
            }
        )
    return results


# =============================================================================
# 4. KATEGOORIATE VAATED
# =============================================================================

def render_feed_tab(*, feed_url, kind, source_md, badge_text, pill_class,
                    button_text, empty_msg, diag_name, page_key, search_query,
                    refresh_note):
    show_html(f'<div class="refresh-badge">{esc(refresh_note)}</div>')
    st.markdown(f"**Allikas:** {source_md}")

    try:
        items = load_feed(feed_url, kind)
    except requests.RequestException as exc:
        st.warning(f"RSS-voo laadimine ebaõnnestus: {exc}")
        items = []
    except Exception as exc:
        st.warning(f"RSS-andmete töötlemisel tekkis viga: {exc}")
        items = []

    filtered = [
        it for it in items
        if matches(search_query, it.get("title"), it.get("description"))
    ]
    render_image_diagnostics(filtered, diag_name)

    if not filtered:
        st.info(empty_msg)

    for item in paginate_items(filtered, page_key):
        badges = pill(pill_class, badge_text) + pill(
            "badge-location", f"📍 {item.get('location', '')}"
        )
        render_card(item, button_text, badges=badges)


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


def render_food_tab(search_query):
    show_html('<div class="refresh-badge">ℹ️ Näidisandmed – mitte reaalajas poehinnad</div>')
    st.warning(
        "Allolevad hinnad ja pakkumised on näidisandmed. "
        "Neid ei tohi käsitleda kaupluste täna kinnitatud hindadena."
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


def render_invest_tab():
    show_html('<div class="refresh-badge">ℹ️ Portfelli näidisvaade</div>')
    st.markdown("### 💼 Lightyeari portfelli vaade")
    st.warning(
        "See vaade ei ole Lightyeariga ühendatud ega saa kontolt reaalajas andmeid. "
        "Allolevad summad on koodis olevad näidisväärtused."
    )

    holdings = [
        ("🟢", "NVIDIA Corp. (NVDA)", 19.25),
        ("🟢", "NEAR Protocol (NEAR)", 19.25),
        ("🟠", "Bitcoin (BTC)", 19.25),
        ("💵", "EUR / sularaha", 0.00),
    ]
    total = sum(h[2] for h in holdings)
    diff = -0.16
    pct = diff / (total - diff) * 100 if total != diff else 0.0
    color = "#34d399" if diff >= 0 else "#ef4444"
    arrow = "▲" if diff >= 0 else "▼"
    now = datetime.now(ZoneInfo("Europe/Tallinn")).strftime("%H:%M:%S")

    col1, col2, col3 = st.columns(3)
    with col1:
        show_html(
            f"""
            <div class="invest-card">
              <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:4px;">Portfelli näidisväärtus</div>
              <div class="metric-big">€{total:.2f}</div>
              <div style="font-size:0.8rem;color:{color};margin-top:4px;">
                {arrow} {pct:.2f}% (€{diff:.2f}) näidismuutus
              </div>
            </div>
            """
        )
    with col2:
        show_html(
            """
            <div class="invest-card">
              <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:4px;">Näidispositsioonid</div>
              <div class="metric-big" style="font-size:1.8rem;margin-top:8px;">NVIDIA, NEAR, BTC</div>
              <div style="font-size:0.8rem;color:#34d399;margin-top:6px;">Näidisportfell</div>
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

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### 📊 Varade jaotus – näidis")
        rows = "".join(
            f'<div class="asset-row">'
            f'<span style="font-weight:700;color:#f8fafc;">{icon} {esc(name)}</span>'
            f'<span style="color:#34d399;font-weight:600;">€{value:.2f}</span>'
            f"</div>"
            for icon, name, value in holdings
        )
        show_html(f'<div class="pro-card">{rows}</div>')

    with col_right:
        st.markdown("#### 🕒 Tehingud – näidis")
        transactions = [
            ("Buy NVIDIA", "-€20.00", "#ef4444"),
            ("Withdrawal to bank", "-€22.31", "#ef4444"),
            ("Buy NEAR Protocol", "-€20.00", "#ef4444"),
            ("EUR to USD exchange", "+USD equivalent", "#34d399"),
            ("Deposit from card", "+€80.00", "#34d399"),
        ]
        rows = "".join(
            f'<div class="asset-row">'
            f'<span style="color:#f8fafc;font-weight:600;">{esc(label)}</span>'
            f'<span style="color:{c};font-weight:700;">{esc(amount)}</span>'
            f"</div>"
            for label, amount, c in transactions
        )
        show_html(f'<div class="pro-card">{rows}</div>')

    st.markdown("#### 🤖 Portfelli tähelepanek")
    st.info(
        "Näidisportfell on jaotatud kolme vara vahel. See ei ole reaalajas "
        "turuanalüüs ega personaalne investeerimissoovitus. Enne otsuseid "
        "kontrolli oma tegelikke positsioone, hindu ja riske Lightyearis."
    )


# =============================================================================
# 5. PEAVOOG
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
        Facebooki tasuta esemed, Hange.ee aiatööd, garaažid, toidukaubad ja Lightyear portfell
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
    st.button("Tühjenda", use_container_width=True, on_click=clear_search)

selected_tab = st.radio(
    "Vali kategooria:", TABS, horizontal=True, label_visibility="collapsed"
)
st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

REFRESH_NOTE = "⏱️ Leht uuendub iga 1 min, voo andmed vahemälus 15 min"

if selected_tab == TAB_FREE:
    render_feed_tab(
        feed_url=FB_FEED_URL, kind="standard",
        source_md="[Facebooki tasuta asjade voog](https://www.facebook.com)",
        badge_text="🎁 Tasuta", pill_class="badge-free",
        button_text="Vaata Facebookis",
        empty_msg="Ühtegi sobivat kuulutust ei leitud. Kontrolli RSS-voogu või proovi teist otsingusõna.",
        diag_name="Facebook", page_key="free",
        search_query=search_query, refresh_note=REFRESH_NOTE,
    )
elif selected_tab == TAB_GARAGES:
    render_feed_tab(
        feed_url=GARAGE_FEED_URL, kind="standard",
        source_md="[Kinnisvara24](https://kinnisvara24.ee)",
        badge_text="🚘 Garaaž", pill_class="badge-price",
        button_text="Vaata kuulutust",
        empty_msg="Garaažide RSS-voost ei leitud praegu sobivaid kuulutusi.",
        diag_name="Kinnisvara24 garaažid", page_key="garages",
        search_query=search_query, refresh_note=REFRESH_NOTE,
    )
elif selected_tab == TAB_GARDEN:
    render_feed_tab(
        feed_url=HANGE_FEED_URL, kind="gardening",
        source_md="[Hange.ee](https://www.hange.ee)",
        badge_text="🌿 Aiatöö / Haljastus", pill_class="badge-gardening",
        button_text="Vaata Hange.ee keskkonnas",
        empty_msg="Sobivaid aiatööde hankeid praegu ei leitud.",
        diag_name="Hange.ee aiatööd", page_key="hange",
        search_query=search_query,
        refresh_note="⏱️ Aiatööde voog: vahemälu 15 min",
    )
elif selected_tab == TAB_FOOD:
    render_food_tab(search_query)
elif selected_tab == TAB_INVEST:
    render_invest_tab()


# =============================================================================
# 6. JALUS
# =============================================================================

st.markdown("---")
footer_col1, footer_col2 = st.columns([3, 1])
with footer_col1:
    st.caption(
        "AI Kuulutuste Skänner Pro · RSS-andmete kuvamine sõltub väliste "
        "andmevoogude kättesaadavusest."
    )
with footer_col2:
    if st.button("🔄 Tühjenda RSS-vahemälu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
