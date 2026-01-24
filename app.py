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
        # On exécute le code dans un environnement sécurisé
        local_vars = {}
        exec(code, {"plt": plt, "np": np, "st": st}, local_vars)
        
        # On récupère la figure pour l'afficher proprement
        fig = plt.gcf()
        st.pyplot(fig)
        plt.clf() # Nettoyage après affichage
    except Exception as e:
        st.error(f"Erreur graphe : {e}")

# --- 3. PROMPT PÉDAGOGIQUE ---
txt_images = ", ".join(get_images())

# Consignes strictes pour le robot
SYSTEM_PROMPT = "Tu es un professeur de Physique-Chimie expert. "
SYSTEM_PROMPT += "Règle 1 : Ne montre JAMAIS le code Python à l'élève. "
SYSTEM_PROMPT += "Règle 2 : Si l'élève veut un graphe, génère le code entre ```python ... ```. "
SYSTEM_PROMPT += "Règle 3 : Pour la MODULATION D'AMPLITUDE, trace toujours l'enveloppe (le signal modulant + composante continue) en rouge pointillé ('r--') par dessus le signal modulé bleu. "
SYSTEM_PROMPT += "Règle 4 : Ajoute toujours : plt.grid(True), plt.xlabel('Temps (s)'), plt.legend(). "
SYSTEM_PROMPT += f"Images disponibles (si besoin) : {txt_images} (utilise [[AFFICHER:nom]]). "

# --- 4. INTERFACE ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Mot de passe", type="password") == "BAC2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

st.title("⚛️ Coach Physique BIOF")
st.caption("Assistant IA pour la Physique-Chimie")

# --- 5. MOTEUR DE CHAT ---
client = genai.Client(api_key=API_KEY)

if "messages" not in st.session_state: st.session_state.messages = []

# Affichage de l'historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # On n'affiche que le texte nettoyé (sans le code caché)
        st.markdown(msg["display_text"])
        
        # Si le message contenait un graphe, on le ré-affiche
        if "figure_code" in msg:
            executer_code_python(msg["figure_code"])
            
        # Si le message contenait une image
        if "img_path" in msg and msg["img_path"]:
            st.image(msg["img_path"])

# Zone de saisie
if prompt := st.chat_input("Pose ta question..."):
    # 1. Message Utilisateur
    st.session_state.messages.append({
        "role": "user", 
        "display_text": prompt, 
        "content": prompt
    })
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Préparation Context (PDF + Historique)
    api_content = []
    if load_knowledge_base():
        try:
            f = client.files.upload(file=FICHIER_COURS)
            api_content.append(types.Content(role="user", parts=[types.Part.from_uri(file_uri=f.uri, mime_type="application/pdf")]))
        except: pass
    
    for m in st.session_state.messages:
        api_content.append(types.Content(role="model" if m["role"]=="assistant" else "user", parts=[types.Part.from_text(text=m["content"])]))
    
    # 3. Réponse Assistant
    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("Réflexion..."):
            try:
                resp = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                    contents=api_content
                )
                raw_text = resp.text
                text_to_display = raw_text # Par défaut, on affiche tout
                code_found = None
                image_found = None

                # A. DÉTECTION ET NETTOYAGE DU CODE PYTHON (Le correctif est ici)
                if "```python" in raw_text:
                    parts = raw_text.split("```python")
                    text_before = parts[0] # Texte avant le code
                    code_part = parts[1].split("```")[0] # Le code lui-même
                    text_after = parts[1].split("```")[1] if len(parts[1].split("```")) > 1 else ""
                    
                    code_found = code_part
                    text_to_display = text_before + text_after # On cache le code !

                # B. DÉTECTION IMAGES
                if "[[AFFICHER:" in text_to_display:
                    match = re.search(r"\[\[AFFICHER:(.*?)\]\]", text_to_display)
                    if match:
                        nom = match.group(1)
                        path = os.path.join(DOSSIER_SCHEMAS, nom)
                        if os.path.exists(path):
                            image_found = path
                        text_to_display = text_to_display.replace(match.group(0), "")

                # C. AFFICHAGE FINAL
                placeholder.markdown(text_to_display)
                
                if image_found:
                    st.image(image_found)
                
                if code_found:
                    executer_code_python(code_found) # On exécute le code caché

                # Audio
                try:
                    tts = gTTS(text=text_to_display.replace("*", ""), lang='fr')
                    audio = io.BytesIO()
                    tts.write_to_fp(audio)
                    st.audio(audio, format='audio/mp3')
                except: pass

                # Sauvegarde en mémoire
                msg_data = {
                    "role": "assistant", 
                    "content": raw_text,        # On garde tout pour la mémoire de l'IA
                    "display_text": text_to_display # On garde le propre pour l'affichage
                }
                if code_found: msg_data["figure_code"] = code_found
                if image_found: msg_data["img_path"] = image_found
                
                st.session_state.messages.append(msg_data)

            except Exception as e:
                st.error(f"Erreur : {e}")
