import streamlit as st
import json
import os

st.set_page_config(page_title="AI Tasuta Kuulutused", layout="wide")
st.title("⚡ AI Kuulutuste Skanner (Tallinn)")

if os.path.exists("results.json"):
    with open("results.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        st.info("Hetkel uusi kuulutusi pole.")
    
    for item in data:
        with st.container():
            col1, col2 = st.columns([1, 3])
            
            with col1:
                if item["image"]:
                    st.image(item["image"], use_container_width=True)
                else:
                    st.write("📷 Pilt puudub")
            
            with col2:
                st.subheader(item["title"])
                st.write(f"📍 **Asukoht:** {item['location']} | 👀 **Vaatamisi:** {item['views']} | 🕒 **Leitud:** {item['time']}")
                st.link_button("👉 Ava kuulutus ja võta ühendust", item["link"])
            st.divider()
else:
    st.warning("Andmeid alles kogutakse. Tule mõne aja pärast tagasi!")
