import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from gtts import gTTS
import io
import os
import re
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATION ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Clé API manquante.")
    st.stop()

FICHIER_COURS = "cours_reference.pdf"
DOSSIER_SCHEMAS = "schémas"

st.set_page_config(page_title="Tuteur Physique", page_icon="⚛️")

# --- FONCTIONS ---
@st.cache_resource
def load_knowledge_base(): return os.path.exists(FICHIER_COURS)

def get_images():
    if not os.path.exists(DOSSIER_SCHEMAS): return []
    return [f for f in os.listdir(DOSSIER_SCHEMAS) if f.lower().endswith(('.png','.jpg'))]

def executer_code_python(code):
    try:
        exec(code, {"plt": plt, "np": np, "st": st}, {})
        st.pyplot(plt.gcf())
        plt.clf()
    except Exception as e: st.error(f"Erreur graphe: {e}")

# --- IA SETUP ---
client = genai.Client(api_key=API_KEY)
txt_images = ", ".join(get_images())

# --- LE PROMPT (La partie qui posait problème) ---
# J'ai simplifié les guillemets ici pour éviter le bug
SYSTEM_PROMPT = "Tu es un prof de physique. "
SYSTEM_PROMPT += "Si l'élève veut un graphe, génère du code Python entre ```python ... ``` avec matplotlib. "
SYSTEM_PROMPT += "N'utilise pas plt.show(). "
SYSTEM_PROMPT += f"Si besoin, affiche une image parmi : {txt_images} avec le tag [[AFFICHER:nom_image]]."

# --- INTERFACE ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Mot de passe", type="password") == "BAC2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

st.title("⚛️ Coach Physique BIOF")
with st.sidebar:
    if load_knowledge_base(): st.success("Cours chargé")

# --- CHAT ---
if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "figure" in msg: executer_code_python(msg["figure"])
        if "img_path" in msg: st.image(msg["img_path"])

if prompt := st.chat_input("Votre question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Préparation
    api_content = []
    if load_knowledge_base():
        try:
            f = client.files.upload(file=FICHIER_COURS)
            api_content.append(types.Content(role="user", parts=[types.Part.from_uri(file_uri=f.uri, mime_type="application/pdf")]))
        except: pass
    
    # Historique
    for m in st.session_state.messages:
        api_content.append(types.Content(role="model" if m["role"]=="assistant" else "user", parts=[types.Part.from_text(text=m["content"])]))
    
    # Réponse
    with st.chat_message("assistant"):
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                contents=api_content
            )
            text = resp.text
            
            # Gestion Code
            code = None
            if "```python" in text:
                try:
                    code = text.split("```python")[1].split("```")[0].strip()
                except: pass
            
            # Gestion Image
            img_show = None
            if "[[AFFICHER:" in text:
                try:
                    nom = text.split("[[AFFICHER:")[1].split("]]")[0].strip()
                    if os.path.exists(f"{DOSSIER_SCHEMAS}/{nom}"):
                        img_show = f"{DOSSIER_SCHEMAS}/{nom}"
                        text = text.replace(f"[[AFFICHER:{nom}]]", "")
                except: pass

            st.markdown(text)
            if img_show: st.image(img_show)
            if code: executer_code_python(code)

            # Audio
            try:
                tts = gTTS(text=text.replace("*", ""), lang='fr')
                audio = io.BytesIO()
                tts.write_to_fp(audio)
                st.audio(audio, format='audio/mp3')
            except: pass

            msg = {"role": "assistant", "content": text}
            if img_show: msg["img_path"] = img_show
            if code: msg["figure"] = code
            st.session_state.messages.append(msg)

        except Exception as e:
            st.error(f"Erreur : {e}")
