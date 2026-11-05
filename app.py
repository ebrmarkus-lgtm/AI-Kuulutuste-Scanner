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
# 1. RAKENDUSE SEADISTUS
# =============================================================================

st.set_page_config(
    page_title="AI Kuulutuste SkÃ¤nner Pro",
    page_icon="âœ¨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Automaatne Streamliti uuendus iga 60 sekundi jÃ¤rel.
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

DARK_MODE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.stApp {
    background-color: #0b0f19;
    color: #f8fafc;
}
.hero-container {
    padding: 1.5rem 2rem;
    background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
    border: 1px solid #374151;
    border-radius: 20px;
    margin-bottom: 2rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.main-title {
    font-size: 2.4rem;
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 0.3rem;
    letter-spacing: -0.5px;
}
.sub-title {
    font-size: 1rem;
    color: #94a3b8;
    font-weight: 500;
}
.pro-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 18px;
    box-shadow: 0 6px 24px rgba(0,0,0,0.4);
    transition: all 0.25s ease;
}
.pro-card:hover {
    transform: translateY(-3px);
    border-color: #4b5563;
    box-shadow: 0 12px 35px rgba(0,0,0,0.6);
}
.card-row {
    display: flex;
    gap: 24px;
    align-items: flex-start;
}
.card-img {
    flex: 0 0 280px;
    max-width: 280px;
}
.card-img img {
    width: 100%;
    border-radius: 14px;
    display: block;
    object-fit: cover;
    aspect-ratio: 4 / 3;
    background-color: #1f2937;
}
.card-body {
    flex: 1;
    min-width: 0;
}
@media (max-width: 768px) {
    .card-row {
        flex-direction: column;
    }
    .card-img {
        flex: none;
        width: 100%;
        max-width: 100%;
    }
}
.card-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 8px;
    line-height: 1.4;
}
.card-date {
    font-size: 0.825rem;
    color: #94a3b8;
    margin-bottom: 12px;
    font-weight: 500;
}
.card-desc {
    font-size: 0.975rem;
    color: #cbd5e1;
    line-height: 1.6;
    margin-bottom: 20px;
}
.card-tags {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 20px;
}
.badge-pill {
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
.badge-free {
    background-color: rgba(5,150,105,0.15);
    color: #34d399;
    border: 1px solid rgba(5,150,105,0.3);
}
.badge-price {
    background-color: rgba(37,99,235,0.15);
    color: #60a5fa;
    border: 1px solid rgba(37,99,235,0.3);
}
.badge-location {
    background-color: rgba(71,85,105,0.2);
    color: #94a3b8;
    border: 1px solid rgba(71,85,105,0.4);
}
.badge-gardening {
    background-color: rgba(16,185,129,0.2);
    color: #34d399;
    border: 1px solid rgba(16,185,129,0.4);
}
.pro-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    box-sizing: border-box;
    padding: 12px 20px;
    background: #2563eb;
    color: #ffffff !important;
    font-size: 0.95rem;
    font-weight: 600;
    border-radius: 12px;
    text-decoration: none !important;
    transition: all 0.2s ease;
    box-shadow: 0 4px 12px rgba(37,99,235,0.3);
}
.pro-btn:hover {
    background: #1d4ed8;
    box-shadow: 0 6px 20px rgba(37,99,235,0.5);
    transform: translateY(-1px);
}
.pro-btn.secondary {
    background: #1f2937;
    border: 1px solid #374151;
    color: #94a3b8 !important;
    box-shadow: none;
}
.invest-card {
    background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
    border: 1px solid #374151;
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.4);
}
.metric-big {
    font-size: 2.5rem;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -1px;
}
.asset-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 14px 0;
    border-bottom: 1px solid #1f2937;
}
.refresh-badge {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 8px 14px;
    border-radius: 10px;
    font-size: 0.85rem;
    color: #94a3b8;
    display: inline-block;
    margin-bottom: 15px;
}
</style>
"""

st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero-container">
        <div class="main-title">âœ¨ AI Kuulutuste SkÃ¤nner Pro</div>
        <div class="sub-title">
            Facebooki tasuta esemed, Hange.ee aiatÃ¶Ã¶d, garaaÅ¾id,
            toidukaubad ja Lightyear portfell
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# 2. ÃœLDISED ABIFUNKTSIOONID
# =============================================================================

def esc(value) -> str:
    """HTML-escape kasutajale kuvatava teksti jaoks."""
    return html.escape(str(value if value is not None else ""), quote=True)


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

    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None

    return candidate


def show_html(markup: str):
    st.markdown(markup, unsafe_allow_html=True)


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

    visible_count = min(
        total,
        max(0, int(st.session_state.get(count_key, PAGE_INCREMENT))),
    )

    st.caption(
        f"Leitud {total} kirjet Â· NÃ¤itan praegu {visible_count} "
        f"(maksimaalselt {MAX_LIMIT})."
    )

    if visible_count < total:
        remaining = total - visible_count
        c1, c2, _ = st.columns([1, 1, 4])

        with c1:
            if st.button(
                f"NÃ¤ita veel {min(PAGE_INCREMENT, remaining)}",
                key=f"load_more_{category_key}",
            ):
                st.session_state[count_key] = min(
                    total, visible_count + PAGE_INCREMENT
                )
                st.rerun()

        with c2:
            if st.button(
                f"NÃ¤ita kÃµiki ({total})",
                key=f"show_all_{category_key}",
            ):
                st.session_state[count_key] = total
                st.rerun()

    return items[:visible_count]


def render_card(item, button_text, badges="", link=None):
    link = safe_http_url(link or item.get("link") or item.get("url"))
    img_url = safe_http_url(item.get("image"))

    # Ã„ra asenda puuduvat pilti juhusliku pildiga.
    if img_url:
        img_html = f"""
        <div class="card-img">
            <img
                src="{esc(img_url)}"
                loading="lazy"
                decoding="async"
                referrerpolicy="no-referrer"
                alt="{esc(item.get('title', 'Kuulutuse pilt'))}"
                onerror="this.parentElement.style.display='none';"
            >
        </div>
        """
    else:
        img_html = ""

    date_html = (
        f'<div class="card-date">{esc(item.get("date_str"))}</div>'
        if item.get("date_str")
        else ""
    )
    tags_html = f'<div class="card-tags">{badges}</div>' if badges else ""

    if link:
        primary_html = (
            f'<a href="{esc(link)}" target="_blank" '
            f'rel="noopener noreferrer" class="pro-btn">'
            f"{esc(button_text)}</a>"
        )
    else:
        primary_html = (
            '<span class="pro-btn secondary">Link puudub</span>'
        )

    show_html(
        f"""
        <div class="pro-card">
            <div class="card-row">
                {img_html}
                <div class="card-body">
                    <div class="card-title">
                        {esc(item.get("title", "Kuulutus"))}
                    </div>
                    {date_html}
                    <div class="card-desc">
                        {esc(item.get("description", ""))}
                    </div>
                    {tags_html}
                    {primary_html}
                </div>
            </div>
        </div>
        """
    )


def render_image_diagnostics(items, category_name):
    """Arenduse abivaade: nÃ¤itab, kust iga RSS-kirje pildi sai."""
    with st.expander(f"ðŸ”Ž Piltide diagnostika â€“ {category_name}"):
        if not items:
            st.caption("Diagnostikaks pole kirjeid.")
            return
        for index, item in enumerate(items, start=1):
            image_url = item.get("image")
            source = item.get("image_source", "teadmata")
            title = item.get("title", "Pealkirjata")
            if image_url:
                st.markdown(f"**{index}. {esc(title)}** Â· allikas: `{esc(source)}`")
                st.code(image_url, language=None)
            else:
                st.markdown(f"**{index}. {esc(title)}** Â· pilt puudub")


# =============================================================================
# 3. RSS-PILTIDE JA KIRJETE PARSIMINE
# =============================================================================

def _local_tag_name(tag):
    """Toetab nii media:thumbnail kui ka nimeruumiga XML-silte."""
    name = getattr(tag, "name", "") or ""
    return name.split(":")[-1].lower()


def _image_url_is_usable(value, base_url=None, allow_extensionless=False):
    """Kontrollib URL-i kuju; ei tee oletust pelgalt suvalise URL-i pÃµhjal."""
    if not isinstance(value, str) or not value.strip():
        return None

    url = safe_http_url(value.strip(), base_url=base_url)
    if not url:
        return None

    parsed = urllib.parse.urlsplit(url)
    path = parsed.path.lower()
    lower_url = url.lower()

    blocked = (
        "pixel", "tracking", "spacer", "blank", "transparent.gif",
        "placeholder", "default-avatar", "favicon", "logo.svg",
    )
    if any(part in lower_url for part in blocked):
        return None

    if any(part in path for part in ("/avatar/", "/avatars/", "/icons/")):
        return None

    extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp")
    if path.endswith(extensions) or allow_extensionless:
        return url
    return None


def extract_real_image_details(item_soup, base_url=None):
    """Leia ainult konkreetse RSS-kirje sees deklareeritud pildid.

    Eelistab Media RSS-i pildisisu, seejÃ¤rel pisipilti, image-MIME enclosure'i
    ja lÃµpuks sama kirje HTML-kirjelduse img-elemente. Ei kasuta kanalitaseme
    pilte ega teise kirje andmeid.
    """
    candidates = []
    seen = set()

    def add(url, source, allow_extensionless=False):
        resolved = _image_url_is_usable(
            url, base_url=base_url, allow_extensionless=allow_extensionless
        )
        if resolved and resolved not in seen:
            seen.add(resolved)
            candidates.append({"url": resolved, "source": source})

    def local_name(tag):
        name = getattr(tag, "name", "") or ""
        return name.split(":")[-1].lower()

    # Esmalt media:content, mis on mÃ¤rgitud pildiks. Ignoreeri video/audio.
    for tag in item_soup.find_all(True):
        if local_name(tag) != "content":
            continue
        # content:encoded on kirjeldus, mitte Media RSS-i media:content.
        full_name = (getattr(tag, "name", "") or "").lower()
        if full_name == "content:encoded":
            continue
        mime = str(tag.get("type", "")).lower().strip()
        medium = str(tag.get("medium", "")).lower().strip()
        if mime.startswith("image/") or medium == "image":
            add(tag.get("url"), "media:content", allow_extensionless=True)

    # media:thumbnail on kirje enda esinduspilt.
    for tag in item_soup.find_all(True):
        if local_name(tag) == "thumbnail":
            add(tag.get("url"), "media:thumbnail", allow_extensionless=True)

    # RSS enclosure on pilt ainult siis, kui MIME vÃµi faililaiend seda kinnitab.
    for tag in item_soup.find_all(True):
        if local_name(tag) != "enclosure":
            continue
        mime = str(tag.get("type", "")).lower().strip()
        if mime.startswith("image/"):
            add(tag.get("url"), "image enclosure", allow_extensionless=True)
        else:
            add(tag.get("url"), "image enclosure")

    # Otsi ainult selle item'i description/summary/content:encoded HTML-i seest.
    description_tags = []
    for tag in item_soup.find_all(True):
        full_name = (getattr(tag, "name", "") or "").lower()
        if local_name(tag) in {"description", "summary", "encoded"}:
            description_tags.append(tag)

    for desc_tag in description_tags:
        # XML-is HTML vÃµib paikneda CDATA vÃµi tekstisÃµlmes.
        raw_parts = []
        for child in desc_tag.contents:
            raw_parts.append(str(child))
        raw_html = "".join(raw_parts) or desc_tag.get_text("", strip=False)
        html_soup = BeautifulSoup(raw_html, "html.parser")

        for img in html_soup.find_all("img"):
            # RSS-i laisklaadimise atribuudid enne tavalist src-i:
            # src vÃµib olla pisike placeholder, data-src tegelik foto.
            src = (
                img.get("data-original")
                or img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("src")
            )
            add(src, "description img", allow_extensionless=True)

            srcset = img.get("data-srcset") or img.get("srcset") or ""
            if srcset:
                variants = []
                for part in srcset.split(","):
                    bits = part.strip().split()
                    if not bits:
                        continue
                    width = 0
                    if len(bits) > 1:
                        match = re.search(r"(\d+)w", bits[1])
                        if match:
                            width = int(match.group(1))
                    variants.append((width, bits[0]))
                if variants:
                    variants.sort(key=lambda item: item[0], reverse=True)
                    add(variants[0][1], "description srcset", allow_extensionless=True)

    if candidates:
        return candidates[0]
    return {"url": None, "source": "puudub"}


def extract_real_image(item_soup, base_url=None):
    """Ãœhilduvusfunktsioon: tagastab ainult pildi URL-i vÃµi None."""
    return extract_real_image_details(item_soup, base_url=base_url)["url"]

def extract_entry_link(entry, base_url=None):
    link_tag = entry.find("link")
    if not link_tag:
        return None

    # Atom: <link href="..."/>; RSS: <link>...</link>
    href = link_tag.get("href")
    if href:
        return safe_http_url(href, base_url=base_url)

    return safe_http_url(
        link_tag.get_text(" ", strip=True),
        base_url=base_url,
    )


def extract_entry_text(entry, tag_names):
    for tag in entry.find_all(True):
        if _local_tag_name(tag) in tag_names:
            # XML-i CDATA/HTML sisu puhastamine.
            raw = "".join(str(child) for child in tag.contents)
            if not raw:
                raw = tag.get_text(" ", strip=True)

            parsed = BeautifulSoup(raw, "html.parser")
            return parsed.get_text(" ", strip=True)

    return ""


@st.cache_data(ttl=900, show_spinner=False)
def fetch_standard_rss(feed_url):
    """Loeb RSS/Atom voo ning seob pildi ainult vastava kirjega."""
    feed_url = safe_http_url(feed_url)
    if not feed_url:
        return []

    results = []

    try:
        response = requests.get(
            feed_url,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "xml")
        entries = soup.find_all(["item", "entry"])

        for entry in entries:
            if len(results) >= MAX_LIMIT:
                break

            title = extract_entry_text(entry, {"title"}) or "Kirje"
            description = extract_entry_text(
                entry, {"description", "summary", "encoded"}
            )
            link = extract_entry_link(entry, base_url=feed_url)
            image_info = extract_real_image_details(entry, base_url=link or feed_url)
            image_url = image_info["url"]

            results.append(
                {
                    "title": title,
                    "description": (
                        description[:200] + ("..." if len(description) > 200 else "")
                    ),
                    "price": "Vaata pakkumist",
                    "location": "Eesti",
                    "link": link,
                    "image": image_url,
                    "image_source": image_info["source"],
                    "date_str": "ðŸ“… RSS-kuulutus",
                }
            )

    except requests.RequestException as exc:
        st.warning(f"RSS-voo laadimine ebaÃµnnestus: {exc}")
    except Exception as exc:
        st.warning(f"RSS-andmete tÃ¶Ã¶tlemisel tekkis viga: {exc}")

    return results[:MAX_LIMIT]


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_strict_gardening_rss(feed_url):
    required_gardening_words = [
        "aia", "aiatÃ¶Ã¶", "haljast", "muru", "hekk", "heki",
        "viljapuu", "istut", "lillepeenar", "trimmer", "lehte",
        "multÅ¡", "freesi", "pÃµÃµsa", "raie", "vÃµsa",
        "kiviparkett", "terrass", "Ãµue", "puu lÃµik",
    ]

    forbidden_words = [
        "veearvesti", "termostaat", "mullivann", "vannituba",
        "sanitaartehn", "katus", "vundament", "torutÃ¶Ã¶",
        "elektritÃ¶Ã¶", "siseviimistlus", "plaatimine",
        "maalritÃ¶Ã¶", "fassaad", "betoon", "korteris",
        "korteri", "pesumasin", "kÃ¼lmkapp", "pliit",
    ]

    feed_url = safe_http_url(feed_url)
    if not feed_url:
        return []

    results = []

    try:
        response = requests.get(
            feed_url,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "xml")

        for entry in soup.find_all(["item", "entry"]):
            if len(results) >= MAX_LIMIT:
                break

            title = extract_entry_text(entry, {"title"}) or "AiatÃ¶Ã¶ hange"
            description = extract_entry_text(
                entry, {"description", "summary", "encoded"}
            )

            searchable_text = f"{title} {description}".casefold()

            if any(word in searchable_text for word in forbidden_words):
                continue

            if not any(
                word in searchable_text for word in required_gardening_words
            ):
                continue

            link = extract_entry_link(entry, base_url=feed_url)
            image_info = extract_real_image_details(entry, base_url=link or feed_url)
            image_url = image_info["url"]

            results.append(
                {
                    "title": title,
                    "description": (
                        description[:200] + ("..." if len(description) > 200 else "")
                    ),
                    "price": "Vaata hankelt",
                    "location": "Eesti",
                    "link": link,
                    "image": image_url,
                    "image_source": image_info["source"],
                    "date_str": "ðŸ“… AiatÃ¶Ã¶ hange",
                }
            )

    except requests.RequestException as exc:
        st.warning(f"Hange.ee RSS-voo laadimine ebaÃµnnestus: {exc}")
    except Exception as exc:
        st.warning(f"AiatÃ¶Ã¶de andmete tÃ¶Ã¶tlemisel tekkis viga: {exc}")

    return results[:MAX_LIMIT]


# =============================================================================
# 4. NAVIGATSIOON JA ÃœLDINE OTSING
# =============================================================================

search_col, clear_col = st.columns([5, 1])

with search_col:
    search_query = st.text_input(
        "ðŸ” Otsi mÃ¤rksÃµna jÃ¤rgi...",
        placeholder="Sisesta nt NVIDIA, muru, piim, banaan...",
        label_visibility="collapsed",
        key="global_search",
    )

with clear_col:
    if st.button("TÃ¼hjenda", use_container_width=True):
        st.session_state["global_search"] = ""
        st.rerun()

selected_tab = st.radio(
    "Vali kategooria:",
    [
        "ðŸŽ Tasuta asjad",
        "ðŸš˜ Kinnisvara garaaÅ¾id",
        "ðŸŒ¿ AiatÃ¶Ã¶d (Hange.ee)",
        "ðŸ›’ Toidukaubad",
        "ðŸ“ˆ Lightyear Investeeringud",
    ],
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)


# =============================================================================
# 5. TASUTA ASJAD â€“ FACEBOOKI RSS
# =============================================================================

if selected_tab == "ðŸŽ Tasuta asjad":
    st.markdown(
        '<div class="refresh-badge">â±ï¸ Automaatne rakenduse uuendus: iga 1 min jÃ¤rel</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "**Allikas:** [Facebooki tasuta asjade voog](https://www.facebook.com)"
    )

    fb_feed_url = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
    items = fetch_standard_rss(fb_feed_url)

    filtered = [
        item for item in items
        if matches(search_query, item.get("title"), item.get("description"))
    ]
    render_image_diagnostics(filtered, "Facebook")

    if not filtered:
        st.info(
            "Ãœhtegi sobivat kuulutust ei leitud. Kontrolli RSS-voogu "
            "vÃµi proovi teist otsingusÃµna."
        )

    for item in paginate_items(filtered, "free"):
        badges = (
            '<span class="badge-pill badge-free">ðŸŽ Tasuta</span>'
            f'<span class="badge-pill badge-location">ðŸ“ {esc(item.get("location"))}</span>'
        )
        render_card(item, "Vaata Facebookis", badges=badges)


# =============================================================================
# 6. GARAAÅ½ID â€“ KINNISVARA24 RSS
# =============================================================================

elif selected_tab == "ðŸš˜ Kinnisvara garaaÅ¾id":
    st.markdown(
        '<div class="refresh-badge">â±ï¸ Automaatne rakenduse uuendus: iga 1 min jÃ¤rel</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "**Allikas:** [Kinnisvara24](https://kinnisvara24.ee)"
    )

    garage_feed_url = "https://rss.app/feeds/MjiyNEAjjPzTGkVZ.xml"
    items = fetch_standard_rss(garage_feed_url)

    filtered = [
        item for item in items
        if matches(search_query, item.get("title"), item.get("description"))
    ]
    render_image_diagnostics(filtered, "Kinnisvara24 garaaÅ¾id")

    if not filtered:
        st.info("GaraaÅ¾ide RSS-voost ei leitud praegu sobivaid kuulutusi.")

    for item in paginate_items(filtered, "garages"):
        badges = (
            '<span class="badge-pill badge-price">ðŸš˜ GaraaÅ¾</span>'
            f'<span class="badge-pill badge-location">ðŸ“ {esc(item.get("location"))}</span>'
        )
        render_card(item, "Vaata kuulutust", badges=badges)


# =============================================================================
# 7. AIATÃ–Ã–D â€“ HANGE.EE RSS
# =============================================================================

elif selected_tab == "ðŸŒ¿ AiatÃ¶Ã¶d (Hange.ee)":
    st.markdown(
        '<div class="refresh-badge">â±ï¸ AiatÃ¶Ã¶de voog: vahemÃ¤lu 30 min</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "**Allikas:** [Hange.ee](https://www.hange.ee)"
    )

    hange_feed_url = "https://rss.app/feeds/4QE7Z3yfpulhchLA.xml"
    items = fetch_strict_gardening_rss(hange_feed_url)

    filtered = [
        item for item in items
        if matches(search_query, item.get("title"), item.get("description"))
    ]
    render_image_diagnostics(filtered, "Hange.ee aiatÃ¶Ã¶d")

    if not filtered:
        st.info("Sobivaid aiatÃ¶Ã¶de hankeid praegu ei leitud.")

    for item in paginate_items(filtered, "hange"):
        badges = (
            '<span class="badge-pill badge-gardening">ðŸŒ¿ AiatÃ¶Ã¶ / Haljastus</span>'
            f'<span class="badge-pill badge-location">ðŸ“ {esc(item.get("location"))}</span>'
        )
        render_card(
            item,
            "Vaata Hange.ee keskkonnas",
            badges=badges,
            link=item.get("link"),
        )


# =============================================================================
# 8. TOIDUKAUBAD â€“ NÃ„IDISANDMED
# =============================================================================

elif selected_tab == "ðŸ›’ Toidukaubad":
    st.markdown(
        '<div class="refresh-badge">â„¹ï¸ NÃ¤idisandmed â€“ mitte reaalajas poehinnad</div>',
        unsafe_allow_html=True,
    )
    st.warning(
        "Allolevad hinnad ja pakkumised on nÃ¤idisandmed. "
        "Neid ei tohi kÃ¤sitleda kaupluste tÃ¤naste kinnitatud hindadena."
    )

    store_filter = st.selectbox(
        "Filtreeri kaupluse jÃ¤rgi:",
        ["KÃµik", "Rimi", "Selver", "Coop", "Lidl", "Maxima", "Prisma"],
    )

    groceries = [
        {
            "title": "Banaanid (kg)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "0.99 â‚¬ (nÃ¤idis)",
            "store": "Lidl",
            "link": "https://www.lidl.ee",
            "image": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=600&auto=format&fit=crop",
        },
        {
            "title": "VÃ¤rske piim 2.5% (1 l)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "0.69 â‚¬ (nÃ¤idis)",
            "store": "Prisma",
            "link": "https://www.prisma.ee",
            "image": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=600&auto=format&fit=crop",
        },
        {
            "title": "Sea vÃ¤lisfilee (kg)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "5.99 â‚¬ (nÃ¤idis)",
            "store": "Rimi",
            "link": "https://www.rimi.ee",
            "image": "https://images.unsplash.com/photo-1603048588665-791ca8aea617?w=600&auto=format&fit=crop",
        },
        {
            "title": "Kohviuba President (1 kg)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "9.99 â‚¬ (nÃ¤idis)",
            "store": "Selver",
            "link": "https://www.selver.ee",
            "image": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=600&auto=format&fit=crop",
        },
        {
            "title": "Eesti vÃµi 82% (200 g)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "1.89 â‚¬ (nÃ¤idis)",
            "store": "Coop",
            "link": "https://www.coop.ee",
            "image": "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=600&auto=format&fit=crop",
        },
        {
            "title": "VÃ¤rske kurk (kg)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "2.49 â‚¬ (nÃ¤idis)",
            "store": "Maxima",
            "link": "https://www.maxima.ee",
            "image": "https://images.unsplash.com/photo-1449300079323-02e209d9d3a6?w=600&auto=format&fit=crop",
        },
        {
            "title": "Hapukoor 20% (500 g)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "0.95 â‚¬ (nÃ¤idis)",
            "store": "Rimi",
            "link": "https://www.rimi.ee",
            "image": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600&auto=format&fit=crop",
        },
        {
            "title": "Broilerifilee (kg)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "6.49 â‚¬ (nÃ¤idis)",
            "store": "Selver",
            "link": "https://www.selver.ee",
            "image": "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=600&auto=format&fit=crop",
        },
        {
            "title": "Juust Edam (400 g)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "3.29 â‚¬ (nÃ¤idis)",
            "store": "Coop",
            "link": "https://www.coop.ee",
            "image": "https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=600&auto=format&fit=crop",
        },
        {
            "title": "Kartul (5 kg kott)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "2.99 â‚¬ (nÃ¤idis)",
            "store": "Lidl",
            "link": "https://www.lidl.ee",
            "image": "https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=600&auto=format&fit=crop",
        },
        {
            "title": "Muna M (10 tk)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "1.79 â‚¬ (nÃ¤idis)",
            "store": "Prisma",
            "link": "https://www.prisma.ee",
            "image": "https://images.unsplash.com/photo-1516448620398-c5f44bf9f441?w=600&auto=format&fit=crop",
        },
        {
            "title": "Apelsinimahl 100% (1.5 l)",
            "description": "NÃ¤idistoode. Kontrolli hinda kaupluse veebilehelt.",
            "price": "1.99 â‚¬ (nÃ¤idis)",
            "store": "Maxima",
            "link": "https://www.maxima.ee",
            "image": "https://images.unsplash.com/photo-1613478223719-2ab802602423?w=600&auto=format&fit=crop",
        },
    ]

    if store_filter != "KÃµik":
        groceries = [
            item for item in groceries
            if item["store"] == store_filter
        ]

    filtered = [
        item for item in groceries
        if matches(
            search_query,
            item.get("title"),
            item.get("description"),
            item.get("store"),
        )
    ]

    for item in paginate_items(filtered, "groceries"):
        badges = (
            f'<span class="badge-pill badge-price">ðŸ·ï¸ {esc(item.get("price"))}</span>'
            f'<span class="badge-pill badge-location">ðŸ“ {esc(item.get("store"))}</span>'
        )
        render_card(
            item,
            "Ava kaupluse veebileht",
            badges=badges,
            link=item.get("link"),
        )


# =============================================================================
# 9. LIGHTYEAR â€“ KÃ„SITSI SISESTATUD NÃ„IDISPORTFELL
# =============================================================================

elif selected_tab == "ðŸ“ˆ Lightyear Investeeringud":
    st.markdown(
        '<div class="refresh-badge">â„¹ï¸ Portfelli nÃ¤idisvaade</div>',
        unsafe_allow_html=True,
    )
    st.markdown("### ðŸ’¼ Lightyeari portfelli vaade")
    st.warning(
        "See vaade ei ole Lightyeariga Ã¼hendatud ega saa kontolt reaalajas andmeid. "
        "Allolevad summad on koodis olevad nÃ¤idisvÃ¤Ã¤rtused."
    )

    base_val = 57.75
    diff_val = -0.16
    pct_val = -0.19

    current_tallinn_time = datetime.now(
        ZoneInfo("Europe/Tallinn")
    ).strftime("%H:%M:%S")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="invest-card">
                <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:4px;">
                    Portfelli nÃ¤idisvÃ¤Ã¤rtus
                </div>
                <div class="metric-big">â‚¬{base_val:.2f}</div>
                <div style="font-size:0.8rem;color:#ef4444;margin-top:4px;">
                    â–¼ {pct_val}% (â‚¬{diff_val:.2f}) nÃ¤idismuutus
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="invest-card">
                <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:4px;">
                    NÃ¤idispositsioonid
                </div>
                <div class="metric-big" style="font-size:1.8rem;margin-top:8px;">
                    NVIDIA, NEAR, BTC
                </div>
                <div style="font-size:0.8rem;color:#34d399;margin-top:6px;">
                    NÃ¤idisportfell
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="invest-card">
                <div style="font-size:0.85rem;color:#94a3b8;margin-bottom:4px;">
                    Lehe viimase laadimise aeg
                </div>
                <div class="metric-big" style="font-size:1.5rem;margin-top:10px;">
                    {current_tallinn_time}
                </div>
                <div style="font-size:0.8rem;color:#60a5fa;margin-top:6px;">
                    Eesti aeg
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### ðŸ“Š Varade jaotus â€“ nÃ¤idis")
        st.markdown(
            """
            <div class="pro-card">
                <div class="asset-row">
                    <span style="font-weight:700;color:#f8fafc;">ðŸŸ¢ NVIDIA Corp. (NVDA)</span>
                    <span style="color:#34d399;font-weight:600;">â‚¬20.00</span>
                </div>
                <div class="asset-row">
                    <span style="font-weight:700;color:#f8fafc;">ðŸŸ¢ NEAR Protocol (NEAR)</span>
                    <span style="color:#34d399;font-weight:600;">â‚¬20.00</span>
                </div>
                <div class="asset-row">
                    <span style="font-weight:700;color:#f8fafc;">ðŸŸ  Bitcoin (BTC)</span>
                    <span style="color:#34d399;font-weight:600;">â‚¬20.00</span>
                </div>
                <div class="asset-row" style="border-bottom:none;">
                    <span style="font-weight:700;color:#94a3b8;">ðŸ’µ EUR / sularaha</span>
                    <span style="color:#94a3b8;font-weight:600;">â‚¬0.00</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown("#### ðŸ•’ Tehingud â€“ nÃ¤idis")
        st.markdown(
            """
            <div class="pro-card">
                <div class="asset-row">
                    <span style="color:#f8fafc;font-weight:600;">Buy NVIDIA</span>
                    <span style="color:#ef4444;font-weight:700;">-â‚¬20.00</span>
                </div>
                <div class="asset-row">
                    <span style="color:#f8fafc;font-weight:600;">Withdrawal to bank</span>
                    <span style="color:#ef4444;font-weight:700;">-â‚¬22.31</span>
                </div>
                <div class="asset-row">
                    <span style="color:#f8fafc;font-weight:600;">Buy NEAR Protocol</span>
                    <span style="color:#ef4444;font-weight:700;">-â‚¬20.00</span>
                </div>
                <div class="asset-row">
                    <span style="color:#f8fafc;font-weight:600;">EUR to USD exchange</span>
                    <span style="color:#34d399;font-weight:700;">+USD equivalent</span>
                </div>
                <div class="asset-row" style="border-bottom:none;">
                    <span style="color:#f8fafc;font-weight:600;">Deposit from card</span>
                    <span style="color:#34d399;font-weight:700;">+â‚¬80.00</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### ðŸ¤– Portfelli tÃ¤helepanek")
    st.info(
        "NÃ¤idisportfell on jaotatud kolme vara vahel. See ei ole reaalajas "
        "turuanalÃ¼Ã¼s ega personaalne investeerimissoovitus. Enne otsuseid "
        "kontrolli oma tegelikke positsioone, hindu ja riske Lightyearis."
    )


# =============================================================================
# 10. JALUS JA VAHEMÃ„LU HALDUS
# =============================================================================

st.markdown("---")

footer_col1, footer_col2 = st.columns([3, 1])

with footer_col1:
    st.caption(
        "AI Kuulutuste SkÃ¤nner Pro Â· RSS-andmete kuvamine sÃµltub vÃ¤liste "
        "andmevoogude kÃ¤ttesaadavusest."
    )

with footer_col2:
    if st.button("ðŸ”„ TÃ¼hjenda RSS-vahemÃ¤lu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
