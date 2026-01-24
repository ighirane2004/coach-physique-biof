import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Diagnostic", page_icon="🛠️")
st.title("🕵️‍♂️ Diagnostic des Modèles Google")

try:
    # 1. Connexion
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    st.success("✅ Clé API connectée.")

    # 2. Lister les modèles
    st.write("🔍 Recherche des modèles disponibles pour votre compte...")
    
    models = list(genai.list_models())
    
    trouve = False
    for m in models:
        # On affiche uniquement les modèles qui génèrent du texte (generateContent)
        if "generateContent" in m.supported_generation_methods:
            st.code(f"Nom exact : {m.name}")
            if "flash" in m.name:
                st.success(f"⚡ J'ai trouvé celui-ci : {m.name}")
                trouve = True
            if "pro" in m.name:
                st.info(f"🧠 J'ai trouvé celui-ci : {m.name}")

    if not trouve:
        st.error("❌ Aucun modèle 'Flash' trouvé. Nous devrons utiliser un autre nom.")

except Exception as e:
    st.error(f"Erreur grave : {e}")
