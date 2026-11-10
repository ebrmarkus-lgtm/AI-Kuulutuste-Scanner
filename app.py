import streamlit as st
import feedparser

st.set_page_config(page_title="Tasuta Asjad Feed", page_icon="📦", layout="centered")

st.title("📦 Tasuta Asjad Harjumaal & Tallinnas")
st.write("Automaatne Facebooki grupi postituste voog.")

# Teie repositooriumi otselink feed.xml failile
RSS_URL = "https://raw.githubusercontent.com/ebrmarkus-lgtm/fb-rss-feed/main/feed.xml"

if st.button("🔄 Uuenda andmeid"):
    st.rerun()

try:
    feed = feedparser.parse(RSS_URL)
    
    if feed.entries:
        st.success(f"Leiti {len(feed.entries)} värsket postitust.")
        st.markdown("---")
        
        for entry in feed.entries:
            st.subheader(entry.get("title", "Pealkirjata"))
            
            published = entry.get("published", "Aeg teadmata")
            st.caption(f"🕒 Lisatud: {published}")
            
            description = entry.get("description", "Sisu puudub")
            st.write(description)
            
            link = entry.get("link")
            if link:
                st.markdown(f"[🔗 Ava Facebookis]({link})")
            
            st.markdown("---")
    else:
        st.info("Hetkel voog postitusi ei näita või voog on veel tühi.")

except Exception as e:
    st.error(f"Viga voo lugemisel: {e}")
