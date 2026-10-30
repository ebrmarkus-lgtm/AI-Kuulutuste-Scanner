import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")
st.title("⚡ AI Kuulutuste Skänner (Harjumaa)")

tab_fb, tab_kv24 = st.tabs(["📌 Facebook: Tasuta asjad", "🏠 Kinnisvara24: Garaažid Harjumaal"])

RSS_URL_FB = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
FB_GROUP_URL = "https://www.facebook.com/groups/442569942509759"
KV24_HARJU_URL = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
# Uuendamise intervallid. TTL on veidi lühem kui run_every, et vahemälu
# oleks automaatse uuenduse hetkel kindlasti aegunud.
FB_REFRESH_SEC = 60 * 60            # Facebook: iga 1 h
KV24_REFRESH_SEC = 24 * 60 * 60     # Kinnisvara24: iga 24 h
FB_CACHE_TTL = FB_REFRESH_SEC - 60
KV24_CACHE_TTL = KV24_REFRESH_SEC - 60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


# ---------- Abifunktsioonid ----------
def clean_text(text):
    """Eemaldab HTML märgised ja puhastab teksti."""
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def local(tag):
    """Tagi nimi ilma namespace'ita."""
    return tag.split("}")[-1].lower() if isinstance(tag, str) else ""


def child_text(item, name):
    for ch in item:
        if local(ch.tag) == name:
            return (ch.text or "").strip()
    return ""


def normalize_fb_link(link):
    """
    Teeb lingi täpseks sihtlingiks:
    - Marketplace'i kuulutus -> https://www.facebook.com/marketplace/item/<ID>/
    - grupipostitus -> sama link ilma jälgimisparameetriteta
    - permalink.php jätab alles story_fbid ja id
    """
    if not link:
        return FB_GROUP_URL, "group"

    m = re.search(r"/marketplace/item/(\d+)", link)
    if m:
        return f"https://www.facebook.com/marketplace/item/{m.group(1)}/", "marketplace"

    parsed = urllib.parse.urlparse(link)
    if "facebook.com" in parsed.netloc:
        if "permalink.php" in parsed.path:
            q = urllib.parse.parse_qs(parsed.query)
            keep = {k: v[0] for k, v in q.items() if k in ("story_fbid", "id")}
            return (
                f"https://www.facebook.com{parsed.path}?{urllib.parse.urlencode(keep)}",
                "group",
            )
        return f"https://www.facebook.com{parsed.path}", "group"

    return link, "other"


def get_tz():
    if ZoneInfo:
        try:
            return ZoneInfo("Europe/Tallinn")
        except Exception:
            pass
    return timezone(timedelta(hours=2))


def now_str():
    return datetime.now(get_tz()).strftime("%d.%m.%Y %H:%M")


def fmt_date(ts):
    """Ajatempel -> '30.10.2026 14:00' Tallinna aja järgi."""
    return datetime.fromtimestamp(ts, get_tz()).strftime("%d.%m.%Y %H:%M")


def time_ago(ts):
    """Ajatempel -> '5 min tagasi', '3 h tagasi', '2 päeva tagasi'."""
    diff = max(0, int(datetime.now(timezone.utc).timestamp() - ts))
    if diff < 3600:
        return f"{max(1, diff // 60)} min tagasi"
    if diff < 86400:
        return f"{diff // 3600} h tagasi"
    days = diff // 86400
    return f"{days} {'päev' if days == 1 else 'päeva'} tagasi"


def parse_date(s):
    if not s:
        return 0
    try:
        return parsedate_to_datetime(s).timestamp()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0


@st.cache_data(ttl=FB_CACHE_TTL, show_spinner=False)
def fetch_fb_items():
    """
    Loeb RSS-i (RSS 2.0 ja Atom). Tulemus on vahemälus 1 h.
    Vea korral visatakse erand (seda ei vahemälutata, nii et järgmine
    katse proovib uuesti).
    """
    results = []
    resp = requests.get(RSS_URL_FB, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()

    for item in root.iter():
        if local(item.tag) not in ("item", "entry"):
            continue

        title = clean_text(child_text(item, "title")) or "Tasuta ese FB grupis"

        raw_desc = child_text(item, "description") or child_text(item, "summary") \
            or child_text(item, "content")
        full = clean_text(raw_desc)
        base = title.rstrip(".… ")
        # Kui kirjeldus algab pealkirjaga, ära korda seda
        if base and full.startswith(base):
            description = full[len(base):].lstrip(" .,:;-–—\n")
        else:
            description = full
        # Liiga lühike pealkiri ("Tere!", "TASUTA") -> võta pealkiri kirjeldusest
        if len(title) < 15 and len(full) > len(title):
            cut = full[:70].rsplit(" ", 1)[0] if len(full) > 70 else full
            title = cut + ("…" if len(full) > len(cut) else "")
            description = full[len(cut):].lstrip(" .,:;-–—\n")
        if len(description) > 250:
            description = description[:250].rsplit(" ", 1)[0] + "…"

        link = ""
        for ch in item:
            if local(ch.tag) == "link":
                link = ch.get("href") or (ch.text or "").strip()
                if link:
                    break

        date_str = child_text(item, "pubdate") or child_text(item, "updated") \
            or child_text(item, "published")
        timestamp = parse_date(date_str)
        if 0 < timestamp < month_ago:
            continue

        image_url = None
        for ch in item:
            if local(ch.tag) in ("enclosure", "content", "thumbnail") and ch.get("url"):
                image_url = ch.get("url")
                break
        if not image_url and raw_desc:
            img = BeautifulSoup(raw_desc, "html.parser").find("img")
            if img and img.get("src"):
                image_url = img.get("src")

        final_link, link_type = normalize_fb_link(link)

        results.append({
            "title": title,
            "description": description,
            "link": final_link,
            "link_type": link_type,
            "image": image_url,
            "timestamp": timestamp,
            "date_str": date_str,
        })

    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results, now_str()


# ---------- 1. FACEBOOK ----------
PAGE_SIZE = 10


@st.fragment(run_every=FB_REFRESH_SEC)
def render_facebook():
    st.write("Viimase 1 kuu tasuta kuulutused FB grupist (uuemad eespool).")

    try:
        results_fb, updated_at = fetch_fb_items()
        fb_error = None
    except Exception as e:
        results_fb, updated_at = [], None
        fb_error = f"Facebooki RSS-i lugemine ebaõnnestus: {e}"

    if fb_error:
        st.warning(fb_error)
    else:
        st.caption(f"🔄 Viimati uuendatud: {updated_at} (uueneb automaatselt iga 1 h)")

    if not results_fb:
        st.info("Ootame uusi postitusi grupis.")
        st.link_button("👉 Ava Facebooki grupp", FB_GROUP_URL)
        return

    # --- Otsing ja filter ---
    col_q, col_new = st.columns([3, 1])
    query = col_q.text_input(
        "🔎 Otsi kuulutusi", placeholder="nt külmik, диван, aknad", key="fb_query"
    )
    only_new = col_new.checkbox("🆕 Ainult viimased 24 h", key="fb_only_new")

    now_ts = datetime.now(timezone.utc).timestamp()
    filtered = []
    for r in results_fb:
        if query and query.lower().strip() not in f"{r['title']} {r['description']}".lower():
            continue
        if only_new and not (r["timestamp"] and now_ts - r["timestamp"] < 86400):
            continue
        filtered.append(r)

    if not filtered:
        st.info("Otsingule ei leitud ühtegi kuulutust.")
        return

    if "fb_limit" not in st.session_state:
        st.session_state["fb_limit"] = PAGE_SIZE
    shown = filtered[: st.session_state["fb_limit"]]
    st.caption(f"Näitan {len(shown)} / {len(filtered)} kuulutust")

    # --- Kiirnavigatsioon ---
    with st.expander(f"⏬ Hüppa kuulutuse juurde ({len(shown)})"):
        nav = "".join(
            f'<div><a href="#fb-{i}" target="_self">{i + 1}. {html.escape(r["title"][:70])}</a></div>'
            for i, r in enumerate(shown)
        )
        st.markdown(nav, unsafe_allow_html=True)

    # --- Kuulutuste kaardid ---
    for i, item in enumerate(shown):
        st.markdown(f'<div id="fb-{i}"></div>', unsafe_allow_html=True)
        is_new = bool(item["timestamp"]) and now_ts - item["timestamp"] < 86400

        with st.container(border=True):
            def render_text():
                st.subheader(("🆕 " if is_new else "") + item["title"])
                if item["timestamp"]:
                    st.caption(
                        f"📅 {fmt_date(item['timestamp'])} · {time_ago(item['timestamp'])} · 💚 Tasuta"
                    )
                else:
                    st.caption("💚 Tasuta")
                if item["description"]:
                    st.write(item["description"])
                label = (
                    "Ava Marketplace'i kuulutus"
                    if item["link_type"] == "marketplace"
                    else "Ava postitus Facebookis"
                )
                st.link_button(f"👉 {label}", item["link"])

            if item["image"]:
                col_img, col_txt = st.columns([1, 4])
                with col_img:
                    st.image(item["image"], width=180)
                with col_txt:
                    render_text()
            else:
                render_text()

    # --- Näita rohkem ---
    if len(shown) < len(filtered):
        if st.button(f"⬇️ Näita rohkem ({len(filtered) - len(shown)} veel)"):
            st.session_state["fb_limit"] += PAGE_SIZE
            st.rerun(scope="fragment")
    st.markdown('<a href="#fb-0" target="_self">⬆️ Tagasi üles</a>', unsafe_allow_html=True)


with tab_fb:
    render_facebook()


# ---------- 2. KINNISVARA24 (ainult Harjumaa) ----------
@st.cache_data(ttl=KV24_CACHE_TTL, show_spinner=False)
def fetch_kv24_info():
    """
    Tõmbab Harjumaa garaažide lehe iga 24 h tagant ja proovib leida
    kuulutuste arvu. Vea korral visatakse erand (ei vahemälutata).
    """
    resp = requests.get(KV24_HARJU_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    text = BeautifulSoup(resp.text, "html.parser").get_text(" ", strip=True)
    m = re.search(r"(\d[\d\s]*)\s*(?:kuulutust|kuulutus|tulemust|tulemus|objekti|objekt)", text, re.IGNORECASE)
    count = re.sub(r"\s+", "", m.group(1)) if m else None
    return {"count": count}, now_str()


@st.fragment(run_every=KV24_REFRESH_SEC)
def render_kv24():
    st.write("Garaažide müügipakkumised Harjumaal (Kinnisvara24.ee).")

    info, updated_at = {"count": None}, None
    try:
        info, updated_at = fetch_kv24_info()
    except Exception as e:
        st.warning(f"Kinnisvara24 lehe lugemine ebaõnnestus: {e}")

    if updated_at:
        st.caption(f"🔄 Viimati uuendatud: {updated_at} (uueneb automaatselt iga 24 h)")

    with st.container(border=True):
        st.subheader("🏠 Garaažid Harju maakonnas, müük")
        st.write("Aktiivsed garaažide müügipakkumised ja boksid Harjumaal.")
        st.caption("📍 Harjumaa")
        if info.get("count"):
            st.write(f"**Leitud kuulutusi lehel:** {info['count']}")
        st.link_button("👉 Ava Harjumaa garaažid Kinnisvara24 portaalis", KV24_HARJU_URL)


with tab_kv24:
    render_kv24()
