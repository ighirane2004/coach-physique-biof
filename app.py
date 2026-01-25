import streamlit as st
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import time
import json
import os
import re

# --- 1. IMPORTATION DES ANIMATIONS (Le lien avec animations.py) ---
try:
    from animations import get_animation_code
except ImportError:
    st.warning("⚠️ Fichier 'animations.py' introuvable. Les simulations ne fonctionneront pas.")
    def get_animation_code(code): return None

# --- 2. CONFIGURATION ---
st.set_page_config(page_title="Coach Sciences", page_icon="⚛️", layout="centered")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

# --- 3. CHARGEMENT DES DONNÉES ---
def charger_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

SCENARIOS = charger_json("scenarios.json")
VIDEOS = charger_json("videos.json")

# VOTRE PROGRAMME (J'ai mis la version simplifiée, modifiez les noms si besoin)
PROGRAMME = {
    "2bac": {
        "Physique_Ondes": ["1.pdf", "2.pdf", "3.pdf"],
        "Physique_Nucleaire": ["4.pdf", "5.pdf"],
        "Chimie": ["6.pdf", "7.pdf"]
    }
}

# --- 4. AUTHENTIFICATION ---
if "auth" not in st.session_state: st.session_state.auth = False

def login():
    code = st.session_state.input_code.strip()
    try: users = st.secrets["auth"]["users"]
    except: return
    if code in users:
        st.session_state.auth = True
        st.session_state.user_id = code

if not st.session_state.auth:
    st.title("🔐 Accès Professeur")
    st.text_input("Code:", key="input_code", type="password", on_change=login)
    st.stop()

# --- 5. NAVIGATION ---
with st.sidebar:
    st.header("📚 Navigation")
    niveau = "2bac" # Vous pourrez remettre le sélecteur complet ici
    partie = st.selectbox("Chapitre", list(PROGRAMME[niveau].keys()))
    lecon = st.selectbox("Leçon", PROGRAMME[niveau][partie])
    
    st.divider()
    if st.button("🔄 Recommencer la leçon"):
        st.session_state.messages = []
        st.session_state.etape_active = 0
        st.rerun()

# --- 6. LE CERVEAU (MOTEUR DE SCÉNARIO) ---
st.title(lecon.replace(".pdf", ""))

if "messages" not in st.session_state: st.session_state.messages = []
if "etape_active" not in st.session_state: st.session_state.etape_active = 0

# On récupère le scénario et la vidéo
scenario_data = SCENARIOS.get(lecon, None)
lien_video = VIDEOS.get(lecon, None)

# Affichage de l'historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Zone de saisie
prompt = st.chat_input("Votre réponse...")
trigger = len(st.session_state.messages) == 0

if prompt or trigger:
    user_text = prompt if prompt else "Bonjour Professeur."
    
    if not trigger:
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"): st.markdown(user_text)

    # --- LOGIQUE INTELLIGENTE ---
    if scenario_data and st.session_state.etape_active < len(scenario_data["etapes"]):
        step = scenario_data["etapes"][st.session_state.etape_active]
        
        # 1. Gestion de l'Animation Python (Via animations.py)
        code_anim = None
        if step.get("action_ia") and step["action_ia"].startswith("ANIM_"):
            code_anim = get_animation_code(step["action_ia"])

        # 2. Gestion de la Vidéo (Lien Drive)
        msg_video = ""
        if step.get("action_ia") == "VIDEO" and lien_video:
            msg_video = f"\n\n📺 **Regarde cette vidéo :** [Cliquez ici pour voir]({lien_video})"

        # 3. Instruction à l'IA
        system_instruction = f"""
        Tu es le Professeur.
        CONTEXTE : Étape {step['id']} du cours.
        CONSIGNE PÉDAGOGIQUE : {step['consigne_prof']}
        
        RÈGLES :
        1. Si c'est l'étape 1 : Dis Bonjour, annonce le titre, et pose la situation problème.
        2. Si c'est une autre étape : Valide la réponse de l'élève (sois encourageant), puis enchaîne avec la consigne.
        3. N'invente PAS de liens vidéo.
        4. Ne parle pas de "code python", dis "Regardons cette simulation".
        """
        
        with st.chat_message("assistant"):
            with st.spinner("..."):
                model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system_instruction)
                response = model.generate_content(user_text)
                text_resp = response.text + msg_video
                
                st.markdown(text_resp)
                
                # Exécution de l'animation SI elle existe
                if code_anim:
                    st.caption("🖥️ *Lancement de la simulation...*")
                    try:
                        exec(code_anim, {"plt": plt, "np": np, "st": st, "time": time})
                    except Exception as e:
                        st.error(f"Erreur animation : {e}")

                st.session_state.messages.append({"role": "assistant", "content": text_resp})

        # On passe à l'étape suivante
        st.session_state.etape_active += 1 

    else:
        # Si pas de scénario ou fin du cours
        st.success("Leçon terminée ! Bravo.")
