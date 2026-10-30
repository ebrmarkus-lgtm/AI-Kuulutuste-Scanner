import streamlit as st
import json
import os

st.set_page_config(page_title="AI Kuulutuste Skänner", page_icon="⚡", layout="wide")

st.title("⚡ AI Kuulutuste Skänner (Tallinn)")
st.write("Skännitakse viimaseid tasuta kuulutusi SOOV.ee portaalist ja FB grupist...")

json_file = "results.json"

if os.path.exists(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if data:
            for item in data:
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        if item.get("image"):
                            st.image(item.get("image"), use_container_width=True)
                        else:
                            st.write("🖼️ *Pilt puudub*")
                            
                    with col2:
                        st.subheader(item.get("title", "Kuulutus ilma pealkirjata"))
                        st.write(f"**Hind:** {item.get('price', 'Tasuta')}")
                        st.write(f"**Asukoht:** {item.get('location', 'Tallinn')}")
                        
                        link = item.get("link", "#")
                        if link != "#":
                            st.markdown(f"[👉 Vaata kuulutust originaalportaalis]({link})")
                st.divider()
        else:
            st.info("Hetkel ühtegi uut kuulutust ei leitud. Kontrollime uuesti järgmisel tunnil!")
    except Exception as e:
        st.error(f"Viga andmete lugemisel: {e}")
else:
    st.warning("Andmeid alles kogutakse. Tule mõne aja pärast tagasi!")
