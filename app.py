import streamlit as st
import google.generativeai as genai # On utilise la librairie stable
from PIL import Image
from gtts import gTTS
import io
import os
import re
import matplotlib.pyplot as plt
import numpy as np

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("Clé API manquante.")
    st.stop()

FICHIER_COURS = "cours_reference.pdf"
DOSSIER_SCHEMAS = "schémas"

st.set_page_config(page_title="Coach Physique Pro", page_icon="⚛️")

# --- 2. DIAGNOSTIC (La réponse à votre question) ---
# Ce bloc va chercher la liste réelle des modèles disponibles pour VOTRE clé
with st.sidebar:
    st.header("🔍 Diagnostic Modèles")
    try:
        my_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                my_models.append(m.name)
        
        st.success(f"{len(my_models)} modèles trouvés")
        modele_choisi = st.selectbox("Choisir le modèle :", my_models, index=0)
    except Exception as e:
        st.error(f"Erreur scan : {e}")
        modele_choisi = "models/gemini-1.5-flash" # Valeur par défaut

# --- 3. FONCTIONS ---
@st.cache_resource
def load_knowledge_base(): return os.path.exists(FICHIER_COURS)

def get_images():
    if not os.path.exists(DOSSIER_SCHEMAS): return []
    return [f for f in os.listdir(DOSSIER_SCHEMAS) if f.lower().endswith(('.png','.jpg'))]

def executer_code_python(code):
    try:
        local_vars = {}
        plt.figure(figsize=(10, 6))
        exec(code, {"plt": plt, "np": np, "st": st}, local_vars)
        fig = plt.gcf()
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"Erreur graphe : {e}")

# --- 4. PROMPT ---
txt_images = ", ".join(get_images())
SYSTEM_PROMPT = """
Tu es un professeur de Physique-Chimie expert.
RÈGLES :
1. Pédagogie active. Ne donne pas la réponse tout de suite.
2. Ne montre JAMAIS le code Python.
3. Si graphique demandé : trace-le avec matplotlib (code entre ```python ... ```).
4. Contexte : Tu as accès à ces schémas : {images}.
""".format(images=txt_images)

# --- 5. INTERFACE ---
st.title("⚛️ Coach Physique & Chimie")

# Zone Multimédia
with st.expander("📸 Zone Multimédia", expanded=True):
    tab1, tab2, tab3 = st.tabs(["Fichier", "Caméra", "Micro"])
    user_image = None
    user_audio = None
    
    with tab1:
        up = st.file_uploader("Image", type=["jpg","png"])
        if up: user_image = Image.open(up)
    with tab2:
        cam = st.camera_input("Photo")
        if cam: user_image = Image.open(cam)
    with tab3:
        # Note: st.audio_input nécessite Streamlit récent, sinon utiliser file_uploader
        aud = st.audio_input("Vocal")
        if aud: user_audio = aud

# --- 6. MOTEUR DE CHAT ---
if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display_text"])
        if "figure_code" in msg: executer_code_python(msg["figure_code"])
        if "img_path" in msg: st.image(msg["img_path"])

prompt = st.chat_input("Votre message...")

if prompt or user_audio or user_image:
    # Affichage User
    display_txt = prompt if prompt else ("🎤 Vocal" if user_audio else "🖼️ Image")
    st.session_state.messages.append({"role": "user", "display_text": display_txt, "content": "..."})
    with st.chat_message("user"):
        st.markdown(display_txt)
        if user_image: st.image(user_image, width=200)

    # Appel API
    with st.chat_message("assistant"):
        spin = st.empty()
        with st.spinner("Analyse..."):
            try:
                # Configuration du modèle choisi dans la sidebar
                model = genai.GenerativeModel(modele_choisi, system_instruction=SYSTEM_PROMPT)
                
                # Construction de la requête
                content_parts = []
                if prompt: content_parts.append(prompt)
                elif not user_audio: content_parts.append("Analyse ceci.")
                
                if user_image: content_parts.append(user_image)
                if user_audio: 
                    # Traitement audio spécifique pour la librairie standard
                    # (Nécessite souvent upload, ici on simplifie en texte si possible ou on gère l'audio brut)
                    # Pour simplifier et éviter les erreurs, on traite l'audio comme fichier
                    content_parts.append(user_audio) # Gemini gère l'audio direct maintenant

                # Génération
                response = model.generate_content(content_parts)
                text_out = response.text
                
                # Nettoyage (Code & Images)
                code_found = None
                if "```python" in text_out:
                    parts = text_out.split("```python")
                    code_found = parts[1].split("```")[0]
                    text_out = parts[0] + parts[1].split("```")[1]

                spin.markdown(text_out)
                if code_found: executer_code_python(code_found)
                
                # Audio TTS
                try:
                    tts = gTTS(text_out.replace("*",""), lang='fr')
                    audio_bio = io.BytesIO()
                    tts.write_to_fp(audio_bio)
                    st.audio(audio_bio, format='audio/mp3')
                except: pass

                st.session_state.messages.append({
                    "role": "assistant", 
                    "display_text": text_out, 
                    "figure_code": code_found
                })

            except Exception as e:
                st.error(f"Erreur : {e}")
