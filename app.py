import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")
st.title("⚡ AI Kuulutuste Skänner (Harjumaa)")

tab_fb, tab_kv24 = st.tabs(["📌 Facebook: Tasuta asjad", "🏠 Kinnisvara24: Garaažid Harjumaal"])

RSS_URL_FB = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
FB_GROUP_URL = "https://www.facebook.com/groups/442569942509759"
KV24_HARJU_URL = "https://kinnisvara24.ee/garaaz/muuk/harju-maakond"
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


@st.cache_data(ttl=300, show_spinner=False)
def fetch_fb_items():
    """Loeb RSS-i (RSS 2.0 ja Atom) ja tagastab (kuulutused, veateade)."""
    results = []
    try:
        resp = requests.get(RSS_URL_FB, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        return [], f"Facebooki RSS-i lugemine ebaõnnestus: {e}"

    month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()

    for item in root.iter():
        if local(item.tag) not in ("item", "entry"):
            continue

        title = clean_text(child_text(item, "title")) or "Tasuta ese FB grupis"

        raw_desc = child_text(item, "description") or child_text(item, "summary") \
            or child_text(item, "content")
        description = clean_text(raw_desc)
        if len(description) > 200:
            description = description[:200] + "..."

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
    return results, None


# ---------- 1. FACEBOOK ----------
with tab_fb:
    st.write("Skännitakse viimase 1 kuu tasuta kuulutusi FB grupist (uuemad eespool)...")

    results_fb, fb_error = fetch_fb_items()
    if fb_error:
        st.warning(fb_error)

    if not results_fb:
        st.info("Ootame uusi postitusi grupis.")
        st.markdown(
            f'<a href="{FB_GROUP_URL}" target="_blank" rel="noopener">👉 Ava Facebooki grupp</a>',
            unsafe_allow_html=True,
        )
    else:
        # Kiirnavigatsioon: klikk keerab leht automaatselt vastava kuulutuse juurde
        with st.expander(f"⏬ Hüppa kuulutuse juurde ({len(results_fb)})"):
            nav = "".join(
                f'<div><a href="#fb-{i}" target="_self">{i + 1}. {r["title"][:70]}</a></div>'
                for i, r in enumerate(results_fb)
            )
            st.markdown(nav, unsafe_allow_html=True)

        for i, item in enumerate(results_fb):
            st.markdown(f'<div id="fb-{i}"></div>', unsafe_allow_html=True)
            with st.container():
                def render_text():
                    st.subheader(item["title"])
                    if item["date_str"]:
                        st.caption(f"📅 {item['date_str']}")
                    if item["description"]:
                        st.write(item["description"])
                    st.write("**Hind:** Tasuta")

                if item["image"]:
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.image(item["image"], use_container_width=True)
                    with col2:
                        render_text()
                else:
                    render_text()

                label = (
                    "👉 Ava Marketplace'i kuulutus"
                    if item["link_type"] == "marketplace"
                    else "👉 Ava see postitus Facebookis"
                )
                st.markdown(
                    f'<a href="{item["link"]}" target="_blank" rel="noopener">{label}</a> '
                    f'&nbsp;|&nbsp; <a href="#fb-0" target="_self">⬆️ Üles</a>',
                    unsafe_allow_html=True,
                )
            st.divider()


# ---------- 2. KINNISVARA24 (ainult Harjumaa) ----------
with tab_kv24:
    st.write("Garaažide müügipakkumised Harjumaal (Kinnisvara24.ee):")

    with st.container():
        st.subheader("Garaažid Harju maakonnas, müük")
        st.write("Aktiivsed garaažide müügipakkumised ja boksid Harjumaal.")
        st.write("**Asukoht:** Harjumaa")
        st.markdown(
            f'<a href="{KV24_HARJU_URL}" target="_blank" rel="noopener">'
            "👉 Ava Harjumaa garaažid Kinnisvara24 portaalis</a>",
            unsafe_allow_html=True,
        )
    st.divider()
