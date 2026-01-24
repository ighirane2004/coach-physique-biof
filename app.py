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

st.set_page_config(page_title="Coach Physique Pro", page_icon="⚛️")

# --- 2. FONCTIONS ---
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

# --- 3. PROMPT PÉDAGOGIQUE ---
txt_images = ", ".join(get_images())

SYSTEM_PROMPT = """
Tu es un professeur de Physique-Chimie expert (Niveau Bac).

RÈGLES D'OR :
1. INPUT : Tu peux recevoir du texte, des images (exercices) ou de l'audio (questions orales). Analyse-les précisément.
2. INVISIBLE : L'élève ne voit PAS tes documents internes. Ne dis jamais "voir document ci-joint" sauf si tu l'affiches.
3. CODE CACHÉ : Ne montre JAMAIS le code Python.
4. COURBES : Pour tracer, génère du code entre ```python ... ```.
   - Modulation AM : Trace l'enveloppe en rouge pointillé 'r--'.
   - Ajoute toujours : plt.grid(True), titres et légendes.

Images stockées (si besoin) : {images} (tag [[AFFICHER:nom]] pour montrer).
""".format(images=txt_images)

# --- 4. INTERFACE ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Mot de passe", type="password") == "BAC2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

st.title("⚛️ Coach Physique & Chimie")

# --- 5. ZONE MULTIMÉDIA (La nouveauté) ---
with st.expander("📸 Envoyer une Image ou un Audio (Cliquez pour ouvrir)", expanded=True):
    tab1, tab2, tab3 = st.tabs(["📁 Importer Image", "📷 Photo", "🎤 Micro"])
    
    user_image = None
    user_audio = None
    
    with tab1:
        uploaded_file = st.file_uploader("Scan ou photo d'exercice", type=["jpg", "png", "jpeg"])
        if uploaded_file: user_image = Image.open(uploaded_file)
    
    with tab2:
        camera_shot = st.camera_input("Prendre une photo")
        if camera_shot: user_image = Image.open(camera_shot)

    with tab3:
        # Note : st.audio_input est disponible sur les versions récentes de Streamlit Cloud
        audio_val = st.audio_input("Enregistrez votre question")
        if audio_val: user_audio = audio_val

# --- 6. MOTEUR DE CHAT ---
client = genai.Client(api_key=API_KEY)

if "messages" not in st.session_state: st.session_state.messages = []

# Affichage historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display_text"])
        if "figure_code" in msg: executer_code_python(msg["figure_code"])
        if "img_path" in msg: st.image(msg["img_path"])
        # On affiche une petite icône si le message contenait de l'audio ou image
        if msg.get("has_audio"): st.caption("🎤 *Message vocal envoyé*")
        if msg.get("has_image"): st.caption("🖼️ *Image envoyée*")

# Gestion de l'envoi (Texte OU Audio OU Image)
# On déclenche si l'utilisateur tape texte OU s'il y a un audio/image en attente
prompt_text = st.chat_input("Votre message...")

if prompt_text or user_audio or user_image:
    
    # 1. Définir le contenu du message utilisateur
    # Si pas de texte mais de l'audio/image, on met un texte par défaut
    display_msg = prompt_text if prompt_text else ""
    if user_audio and not prompt_text: display_msg = "🎤 [Message Vocal]"
    if user_image and not prompt_text: display_msg = "🖼️ [Image envoyée]"
    
    st.session_state.messages.append({
        "role": "user", 
        "display_text": display_msg, 
        "content": display_msg if display_msg else "Analyse ce document/audio.",
        "has_audio": user_audio is not None,
        "has_image": user_image is not None
    })
    
    with st.chat_message("user"):
        st.markdown(display_msg)
        if user_image: st.image(user_image, width=200)

    # 2. Préparation API (Le gros morceau Multimodal)
    api_content = []
    
    # A. Le PDF de cours (Contexte)
    if load_knowledge_base():
        try:
            f = client.files.upload(file=FICHIER_COURS)
            api_content.append(types.Content(role="user", parts=[types.Part.from_uri(file_uri=f.uri, mime_type="application/pdf")]))
        except: pass
    
    # B. Historique (Texte seulement pour économiser)
    for m in st.session_state.messages[:-1]:
        api_content.append(types.Content(role="model" if m["role"]=="assistant" else "user", parts=[types.Part.from_text(text=m["content"])]))
    
    # C. Le Message Actuel (Texte + Image + Audio)
    current_parts = []
    
    # Texte
    if prompt_text: 
        current_parts.append(types.Part.from_text(text=prompt_text))
    elif not user_audio: # Si ni texte ni audio, on demande d'analyser l'image
        current_parts.append(types.Part.from_text(text="Analyse cette image ou réponds à cet audio."))

    # Image
    if user_image:
        current_parts.append(types.Part.from_image(image=user_image))
    
    # Audio
    if user_audio:
        # Lecture des octets audio
        audio_bytes = user_audio.read()
        current_parts.append(types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"))

    api_content.append(types.Content(role="user", parts=current_parts))

    # 3. Réponse Assistant
    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("Analyse multimodale..."):
            try:
                resp = client.models.generate_content(
                    model="gemini-1.5-pro",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.3,
                    ),
                    contents=api_content
                )
                raw_text = resp.text
                text_to_display = raw_text
                code_found = None
                image_found = None

                # Nettoyage Code
                if "```python" in raw_text:
                    parts = raw_text.split("```python")
                    code_part = parts[1].split("```")[0]
                    text_to_display = parts[0] + (parts[1].split("```")[1] if len(parts[1].split("```")) > 1 else "")
                    code_found = code_part

                # Nettoyage Image
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

                # Lecture vocale de la réponse
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
