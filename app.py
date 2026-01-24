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

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Clé API manquante.")
    st.stop()

FICHIER_COURS = "cours_reference.pdf"
DOSSIER_SCHEMAS = "schémas"

st.set_page_config(page_title="Coach Physique", page_icon="⚛️")

# --- 2. FONCTIONS ---
@st.cache_resource
def load_knowledge_base(): return os.path.exists(FICHIER_COURS)

def get_images():
    if not os.path.exists(DOSSIER_SCHEMAS): return []
    return [f for f in os.listdir(DOSSIER_SCHEMAS) if f.lower().endswith(('.png','.jpg'))]

def executer_code_python(code):
    try:
        local_vars = {}
        # On définit une taille de figure standard pour éviter les déformations
        plt.figure(figsize=(10, 6))
        exec(code, {"plt": plt, "np": np, "st": st}, local_vars)
        fig = plt.gcf()
        st.pyplot(fig)
        plt.close(fig) # Important : fermer la figure pour libérer la mémoire
    except Exception as e:
        st.error(f"Erreur graphe : {e}")

# --- 3. PROMPT PÉDAGOGIQUE (renforcé) ---
txt_images = ", ".join(get_images())

SYSTEM_PROMPT = """
Tu es un professeur de Physique-Chimie expert et rigoureux (Niveau Bac).

RÈGLES ABSOLUES (A respecter sous peine de pénalité) :
1. INVISIBLE : L'élève ne voit PAS tes documents internes. Ne dis JAMAIS "comme le montre le document" ou "voir figure ci-contre" sauf si tu affiches l'image toi-même.
2. CODE CACHÉ : Ne montre JAMAIS le code Python. L'élève ne doit voir que le graphique final.
3. PEDAGOGIE : Ne donne pas la réponse directement. Guide l'élève pas à pas.
4. COURBES : Si l'élève demande un tracé, génère le code Python entre ```python ... ```.
   - Pour la MODULATION D'AMPLITUDE : Trace toujours l'enveloppe (signal modulant + composante continue) en rouge pointillé 'r--' par dessus le signal modulé bleu.
   - Ajoute toujours une grille, un titre et les légendes des axes.

Images disponibles (utilise [[AFFICHER:nom_image]] pour les montrer) : {images}
""".format(images=txt_images)

# --- 4. INTERFACE ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Mot de passe", type="password") == "BAC2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

st.title("⚛️ Coach Physique BIOF")
st.caption("Assistant IA - Version Pro")

# --- 5. MOTEUR DE CHAT ---
client = genai.Client(api_key=API_KEY)

if "messages" not in st.session_state: st.session_state.messages = []

# Affichage historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display_text"])
        if "figure_code" in msg: executer_code_python(msg["figure_code"])
        if "img_path" in msg: st.image(msg["img_path"])

if prompt := st.chat_input("Pose ta question..."):
    # User message
    st.session_state.messages.append({"role": "user", "display_text": prompt, "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Context
    api_content = []
    if load_knowledge_base():
        try:
            f = client.files.upload(file=FICHIER_COURS)
            api_content.append(types.Content(role="user", parts=[types.Part.from_uri(file_uri=f.uri, mime_type="application/pdf")]))
        except: pass
    
    for m in st.session_state.messages:
        api_content.append(types.Content(role="model" if m["role"]=="assistant" else "user", parts=[types.Part.from_text(text=m["content"])]))
    
    # Réponse
    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("Analyse approfondie..."):
            try:
                # CHANGEMENT MAJEUR ICI : Modèle 1.5 Pro + Température basse
                resp = client.models.generate_content(
                    model="gemini-1.5-pro", # Le cerveau le plus intelligent
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.3, # Rigueur maximale (moins de fantaisie)
                    ),
                    contents=api_content
                )
                raw_text = resp.text
                text_to_display = raw_text
                code_found = None
                image_found = None

                # Nettoyage Code Python
                if "```python" in raw_text:
                    parts = raw_text.split("```python")
                    code_part = parts[1].split("```")[0]
                    # On reconstruit le texte sans le code
                    text_to_display = parts[0] + (parts[1].split("```")[1] if len(parts[1].split("```")) > 1 else "")
                    code_found = code_part

                # Nettoyage Images
                if "[[AFFICHER:" in text_to_display:
                    match = re.search(r"\[\[AFFICHER:(.*?)\]\]", text_to_display)
                    if match:
                        nom = match.group(1)
                        path = os.path.join(DOSSIER_SCHEMAS, nom)
                        if os.path.exists(path): image_found = path
                        text_to_display = text_to_display.replace(match.group(0), "")

                placeholder.markdown(text_to_display)
                if image_found: st.image(image_found)
                if code_found: executer_code_python(code_found)

                # Audio
                try:
                    tts = gTTS(text=text_to_display.replace("*", ""), lang='fr')
                    audio = io.BytesIO()
                    tts.write_to_fp(audio)
                    st.audio(audio, format='audio/mp3')
                except: pass

                # Sauvegarde
                msg = {"role": "assistant", "content": raw_text, "display_text": text_to_display}
                if code_found: msg["figure_code"] = code_found
                if image_found: msg["img_path"] = image_found
                st.session_state.messages.append(msg)

            except Exception as e:
                st.error(f"Erreur : {e}")
