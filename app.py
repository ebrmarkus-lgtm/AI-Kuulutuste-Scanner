import streamlit as st
import json
import os
import urllib.request
from bs4 import BeautifulSoup

st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")

st.title("⚡ AI Kuulutuste Skänner (Tallinn)")
st.write("Skännitakse viimaseid tasuta kuulutusi FB grupist...")

# Skänneri funktsioon, mis tõmbab andmed ja salvestab need
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
            title_elem = item.find('title')
            desc_elem = item.find('description') or item.find('summary')
            link_elem = item.find('link')
            
            if title_elem and title_elem.text.strip():
                title = title_elem.get_text(strip=True)
            elif desc_elem and desc_elem.text.strip():
                title = desc_elem.get_text(strip=True)[:80] + "..."
            else:
                title = "Tasuta ese FB grupis"
                
            link = "https://www.facebook.com/groups/442569942509759"
            if link_elem:
                if link_elem.get('href'):
                    link = link_elem.get('href')
                elif link_elem.text.strip():
                    link = link_elem.get_text(strip=True)
            
            results.append({
                "title": title,
                "price": "Tasuta",
                "location": "Haapsalu / Tallinn",
                "link": link
            })
    except Exception as e:
        print(f"Viga RSS skännimisel: {e}")

    if not results:
        results = [
            {
                "title": "Ootame uusi postitusi grupis.",
                "price": "0 €",
                "location": "Tallinn",
                "link": "https://www.facebook.com/groups/442569942509759"
            }
        ]

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

# Käivitame skännimise kohe lehe laadimisel
scrape_fb_group_rss()

# Loeme tulemused failist ja kuvame ekraanil
json_file = "results.json"

if os.path.exists(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if data:
            for item in data:
                with st.container():
                    st.subheader(item.get("title", "Kuulutus ilma pealkirjata"))
                    st.write(f"**Hind:** {item.get('price', 'Tasuta')}")
                    st.write(f"**Asukoht:** {item.get('location', 'Tallinn')}")
                    
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
