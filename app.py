import streamlit as st
import json
import os
import urllib.request
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")

st.title("⚡ AI Kuulutuste Skänner (Tallinn)")
st.write("Skännitakse viimaseid tasuta kuulutusi FB grupist...")

# Funktsioon CDATA ja HTML siltide puhastamiseks
def clean_text(text):
    if not text:
        return ""
    # Eemaldame CDATA plokid
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    # Eemaldame HTML sildid kirjeldusest
    clean_soup = BeautifulSoup(text, 'html.parser')
    return clean_soup.get_text(strip=True)

def scrape_fb_group_rss():
    rss_url = "https://rss.app/feeds/7CQIQkCY12Cwc3Rn.xml"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    results = []
    try:
        req = urllib.request.Request(rss_url, headers=headers)
        xml_data = urllib.request.urlopen(req).read()
        soup = BeautifulSoup(xml_data, 'html.parser')
        
        items = soup.find_all(['item', 'entry'])
        
        for item in items[:15]:
            title_raw = item.find('title').text if item.find('title') else "Tasuta ese FB grupis"
            title = clean_text(title_raw)
            
            desc_raw = item.find('description') or item.find('summary')
            description = clean_text(desc_raw.text) if desc_raw else ""
            
            # Lühendame kirjelduse, et ei oleks liiga pikk
            if len(description) > 200:
                description = description[:200] + "..."
                
            link_elem = item.find('link')
            link = "https://www.facebook.com/groups/442569942509759"
            if link_elem:
                if link_elem.get('href'):
                    link = link_elem.get('href')
                elif link_elem.text.strip():
                    link = link_elem.get_text(strip=True)
            
            # Pildi otsimine RSS voost (enclosure, media:content või img tag kirjeldusest)
            image_url = None
            enclosure = item.find('enclosure')
            if enclosure and enclosure.get('url'):
                image_url = enclosure.get('url')
            elif desc_raw:
                img_tag = BeautifulSoup(desc_raw.text, 'html.parser').find('img')
                if img_tag and img_tag.get('src'):
                    image_url = img_tag.get('src')
            
            results.append({
                "title": title,
                "description": description,
                "price": "Tasuta",
                "location": "Haapsalu / Tallinn",
                "link": link,
                "image": image_url
            })
    except Exception as e:
        print(f"Viga RSS skännimisel: {e}")

    if not results:
        results = [
            {
                "title": "Ootame uusi postitusi grupis.",
                "description": "Siia ilmuvad gruusia uued tasuta asjad.",
                "price": "0 €",
                "location": "Tallinn",
                "link": "https://www.facebook.com/groups/442569942509759",
                "image": None
            }
        ]

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

# Käivitame skännimise
scrape_fb_group_rss()

# Kuvame tulemused lehel
json_file = "results.json"

if os.path.exists(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if data:
            for item in data:
                with st.container():
                    # Kasutame veerge, et pilt ja tekst mahuksid kõrvuti (kui pilt on olemas)
                    if item.get("image"):
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.image(item["image"], use_container_width=True)
                        with col2:
                            st.subheader(item.get("title", "Kuulutus ilma pealkirjata"))
                            if item.get("description"):
                                st.write(item.get("description"))
                            st.write(f"**Hind:** {item.get('price', 'Tasuta')} | **Asukoht:** {item.get('location', 'Tallinn')}")
                    else:
                        st.subheader(item.get("title", "Kuulutus ilma pealkirjata"))
                        if item.get("description"):
                            st.write(item.get("description"))
                        st.write(f"**Hind:** {item.get('price', 'Tasuta')} | **Asukoht:** {item.get('location', 'Tallinn')}")
                    
                    link = item.get("link", "#")
                    if link != "#":
                        st.markdown(f"[👉 Vaata kuulutust originaalportaalis]({link})")
                st.divider()
        else:
            st.info("Hetkel ühtegi uut kuulutust ei leitud.")
    except Exception as e:
        st.error(f"Viga andmete lugemisel: {e}")
else:
    st.warning("Andmeid alles kogutakse...")
