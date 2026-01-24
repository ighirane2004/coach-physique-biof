import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import os
import matplotlib.pyplot as plt
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Plateforme Physique-Chimie", page_icon="⚛️", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("Erreur critique : Clé API manquante.")
    st.stop()

# --- 2. PROGRAMME (PC) ---
PROGRAMME = {
    "Tronc Commun": {
        "Physique - Gravitation": "contenu/tronc_commun/mecanique_gravitation.pdf",
        "Chimie - Espèces Chimiques": "contenu/tronc_commun/chimie_especes.pdf"
    },
    "1ère Bac": {
        "Physique - Travail & Énergie": "contenu/1bac/phy_travail_energie.pdf",
        "Chimie - Mesures": "contenu/1bac/chi_mesures.pdf"
    },
    "2ème Bac": {
        "Physique - Ondes": "contenu/2bac/phy_ondes.pdf",
        "Physique - Nucléaire": "contenu/2bac/phy_nucleaire.pdf",
        "Physique - Modulation d'Amplitude": "contenu/2bac/phy_modulation.pdf",
        "Physique - Électricité (RLC)": "contenu/2bac/phy_electricite_rlc.pdf",
        "Chimie - Cinétique": "contenu/2bac/chi_cinetique.pdf"
    }
}

# --- 3. SÉCURITÉ ---
if "auth" not in st.session_state: st.session_state.auth = False

def login():
    code = st.session_state.input_code.strip()
    try:
        if code in st.secrets["auth"]["codes_valides"]:
            st.session_state.auth = True
            st.session_state.user_id = code
        else:
            st.error("Code non reconnu.")
    except: st.error("Erreur technique.")

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔐 Espace BIOF")
        st.text_input("Code d'accès :", key="input_code", type="password", on_change=login)
    st.stop()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user_id}")
    st.divider()
    
    niveau_choisi = st.selectbox("1. Niveau :", list(PROGRAMME.keys()))
    cours_dispo = list(PROGRAMME[niveau_choisi].keys())
    chapitre_choisi = st.selectbox("2. Chapitre :", cours_dispo)
    mode_choisi = st.radio("3. Mode :", ["🎓 Professeur", "🏋️ Coach"], index=1)
    
    chemin_pdf = PROGRAMME[niveau_choisi][chapitre_choisi]
    if os.path.exists(chemin_pdf): st.caption("✅ Cours chargé")
    
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- 5. CERVEAU & RÈGLES STRICTES ---

# Définition du rôle
if "Professeur" in mode_choisi:
    ROLE = "Tu es un Professeur de Physique-Chimie pédagogue."
    TON = "Calme, explicatif, patient."
else:
    ROLE = "Tu es un Coach d'examen impitoyable mais juste."
    TON = "Direct, bref, motivant."

# LE BLINDAGE EST ICI (Lisez bien cette partie)
SYSTEM_PROMPT = f"""
{ROLE}
TON : {TON}
CONTEXTE : Programme marocain, Niveau {niveau_choisi}, Chapitre : {chapitre_choisi}.

⛔ PROTOCOLE DE SÉCURITÉ (OBLIGATOIRE) :
1. DOMAINE STRICT : Tu es EXCLUSIVEMENT un expert en PHYSIQUE et CHIMIE.
2. INTERDICTION FORMELLE : Si l'utilisateur pose une question sur la BIOLOGIE (SVT, Chlorophylle, Corps humain...), l'Histoire, la Philo ou l'Informatique :
   -> TU DOIS REFUSER DE RÉPONDRE.
   -> Réponds exactement : "🚫 Hors Sujet. Je suis ton coach de Physique-Chimie uniquement. Concentre-toi."
3. Ne sois pas gentil si c'est hors sujet. Bloque la conversation.

INSTRUCTIONS PÉDAGOGIQUES :
- Si on parle de Modulation d'Amplitude : Trace l'enveloppe en rouge si demandé.
- Ne montre jamais le code Python.
- Utilise Matplotlib pour les graphes.
"""

# --- 6. FONCTIONS ---
def executer_code_python(code):
    try:
        local_vars = {}
        plt.figure(figsize=(8, 5))
        exec(code, {"plt": plt, "np": np, "st": st}, local_vars)
        st.pyplot(plt.gcf())
        plt.close()
    except: st.error("Erreur tracé.")

def get_images():
    if not os.path.exists("schémas"): return []
    return [f for f in os.listdir("schémas") if f.lower().endswith(('.png','.jpg'))]

# --- 7. CHAT ---
st.title(f"{chapitre_choisi}")

# Upload Photo/Audio
with st.expander("📸 Zone Multimédia"):
    tab1, tab2 = st.tabs(["📷 Photo", "🎤 Micro"])
    user_img = None
    user_audio = None
    with tab1:
        cam = st.camera_input("Photo")
        if cam: user_img = Image.open(cam)
    with tab2:
        aud = st.audio_input("Vocal")
        if aud: user_audio = aud

# Gestion message
if "messages" not in st.session_state: st.session_state.messages = []
if "current_chap" not in st.session_state: st.session_state.current_chap = chapitre_choisi

# Reset si changement de chapitre
if st.session_state.current_chap != chapitre_choisi:
    st.session_state.messages = []
    st.session_state.current_chap = chapitre_choisi
    st.toast("Nouveau chapitre !")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display_text"])
        if "figure_code" in msg: executer_code_python(msg["figure_code"])

prompt = st.chat_input("Ta question...")

if prompt or user_audio or user_img:
    user_txt = prompt if prompt else ("🎤 [Audio]" if user_audio else "🖼️ [Image]")
    st.session_state.messages.append({"role": "user", "display_text": user_txt})
    
    with st.chat_message("user"):
        st.markdown(user_txt)
        if user_img: st.image(user_img, width=200)

    with st.chat_message("assistant"):
        with st.spinner("Analyse..."):
            try:
                model = genai.GenerativeModel("models/gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)
                
                parts = []
                if prompt: parts.append(prompt)
                elif not user_audio: parts.append("Analyse ceci.")
                if user_img: parts.append(user_img)
                if user_audio: parts.append({"mime_type": user_audio.type, "data": user_audio.getvalue()})

                resp = model.generate_content(parts)
                text = resp.text
                
                code = None
                if "```python" in text:
                    seg = text.split("```python")
                    code = seg[1].split("```")[0]
                    text = seg[0] + seg[1].split("```")[1]

                st.markdown(text)
                if code: executer_code_python(code)
                
                try:
                    tts = gTTS(text.replace("*",""), lang='fr')
                    bio = io.BytesIO()
                    tts.write_to_fp(bio)
                    st.audio(bio, format='audio/mp3')
                except: pass

                st.session_state.messages.append({"role": "assistant", "display_text": text, "figure_code": code})
            
            except Exception as e:
                st.error(f"Erreur : {e}")
