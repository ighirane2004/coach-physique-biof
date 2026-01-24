import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import os
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

# --- 2. DIAGNOSTIC MODÈLES (Pour trouver le bon) ---
with st.sidebar:
    st.header("🔍 Diagnostic")
    try:
        my_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        st.success(f"{len(my_models)} modèles détectés")
        modele_choisi = st.selectbox("Modèle actif :", my_models, index=0)
    except:
        st.warning("Scan échoué, utilisation défaut")
        modele_choisi = "models/gemini-1.5-flash"

# --- 3. FONCTIONS ---
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

def get_images():
    if not os.path.exists(DOSSIER_SCHEMAS): return []
    return [f for f in os.listdir(DOSSIER_SCHEMAS) if f.lower().endswith(('.png','.jpg'))]

# --- 4. PROMPT ---
SYSTEM_PROMPT = f"""
Tu es un professeur de Physique-Chimie expert.
RÈGLES :
1. Pédagogie active. Ne donne pas la solution sèche.
2. Ne montre JAMAIS le code Python.
3. Si graphique demandé : trace-le avec matplotlib (code entre ```python ... ```).
4. Images dispo : {", ".join(get_images())}.
"""

# --- 5. INTERFACE ---
st.title("⚛️ Coach Physique & Chimie")

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
        # Compatible Streamlit récent
        aud = st.audio_input("Vocal")
        if aud: user_audio = aud

# --- 6. MOTEUR ---
if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display_text"])
        if "figure_code" in msg: executer_code_python(msg["figure_code"])

prompt = st.chat_input("Message...")

if prompt or user_audio or user_image:
    # 1. Affichage User
    txt_user = prompt if prompt else ("🎤 [Audio]" if user_audio else "🖼️ [Image]")
    st.session_state.messages.append({"role": "user", "display_text": txt_user})
    with st.chat_message("user"):
        st.markdown(txt_user)
        if user_image: st.image(user_image, width=200)

    # 2. Appel API
    with st.chat_message("assistant"):
        spin = st.empty()
        with st.spinner("Analyse..."):
            try:
                model = genai.GenerativeModel(modele_choisi, system_instruction=SYSTEM_PROMPT)
                
                content_parts = []
                if prompt: content_parts.append(prompt)
                elif not user_audio: content_parts.append("Analyse ceci.")
                
                if user_image: content_parts.append(user_image)
                
                # --- CORRECTION AUDIO ---
                if user_audio:
                    audio_bytes = user_audio.getvalue() # On récupère les octets
                    audio_blob = {
                        "mime_type": user_audio.type, # ex: audio/wav
                        "data": audio_bytes
                    }
                    content_parts.append(audio_blob)

                response = model.generate_content(content_parts)
                text_out = response.text
                
                # Extraction Code
                code_found = None
                if "```python" in text_out:
                    parts = text_out.split("```python")
                    code_found = parts[1].split("```")[0]
                    text_out = parts[0] + parts[1].split("```")[1]

                spin.markdown(text_out)
                if code_found: executer_code_python(code_found)
                
                # Audio TTS
                try:
                    tts = gTTS(text=text_out.replace("*",""), lang='fr')
                    bio = io.BytesIO()
                    tts.write_to_fp(bio)
                    st.audio(bio, format='audio/mp3')
                except: pass

                st.session_state.messages.append({
                    "role": "assistant", 
                    "display_text": text_out,
                    "figure_code": code_found
                })

            except Exception as e:
                st.error(f"Erreur : {e}")
