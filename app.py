import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import matplotlib.pyplot as plt
import numpy as np
import math
import re
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Coach Sciences", page_icon="⚛️", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Clé API non configurée.")
    st.stop()

# --- 2. DONNÉES ---
PROGRAMME = {
    "2bac": {
        "Physique_1_Ondes": ["1_Ondes_progressives.pdf"],
        "Physique_3_Electricite": ["1_Dipole_RC.pdf", "2_Dipole_RL.pdf"],
    },
    # (Gardez votre liste complète ici, je l'abrège pour la lisibilité du code)
}

# Fonction de chargement sécurisée
def charger_videos():
    if os.path.exists("videos.json"):
        with open("videos.json", "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

VIDEOS_COURS = charger_videos()
DB_FILE = "memoire.json"

# --- 3. LOGIQUE MÉTIER ---
if "auth" not in st.session_state: st.session_state.auth = False
def login():
    code = st.session_state.input_code.strip()
    users = st.secrets["auth"]["users"]
    if code in users:
        st.session_state.auth = True
        st.session_state.user_id = code
        st.session_state.user_level = users[code]
    else: st.error("Code incorrect")

if not st.session_state.auth:
    st.title("🔐 Accès")
    st.text_input("Code:", key="input_code", type="password", on_change=login)
    st.stop()

# --- 4. NAVIGATION ---
with st.sidebar:
    st.header(f"Prof. {st.session_state.user_id}")
    # Sélection simplifiée pour l'exemple (remettez votre logique complète si besoin)
    niveau = "2bac"
    partie = st.selectbox("Chapitre", list(PROGRAMME[niveau].keys()))
    lecon = st.selectbox("Leçon", PROGRAMME[niveau][partie])
    
    st.divider()
    mode = st.radio("Mode", ["🎓 Professeur Interactif", "🏋️ Coach Exercices"])
    if st.button("Reset / Nouveau Cours"):
        st.session_state.messages = []
        st.rerun()

# --- 5. LE CERVEAU (MODE STRICT) ---

# Vérification rigoureuse de la vidéo AVANT le prompt
lien_video = VIDEOS_COURS.get(lecon, "")
if lien_video and len(lien_video) > 5:
    INSTRUCTION_VIDEO = f"""
    - UNE VIDÉO EST DISPONIBLE : {lien_video}.
    - À l'étape 2, tu DOIS dire "Regardons cette expérience :" et afficher le lien.
    """
else:
    INSTRUCTION_VIDEO = """
    - AUCUNE VIDÉO DISPONIBLE POUR CETTE LEÇON.
    - INTERDICTION FORMELLE de donner un lien YouTube inventé.
    - Saute l'étape vidéo et passe directement à l'observation théorique ou au graphique.
    """

if mode == "🎓 Professeur Interactif":
    ROLE = "Tu es un Professeur Expert qui construit le savoir PAS À PAS."
    CONSIGNE = f"""
    🛑 RÈGLE ABSOLUE : TU NE DOIS JAMAIS TOUT DIRE D'UN COUP.
    Tu dois attendre la réponse de l'élève entre chaque étape.
    
    {INSTRUCTION_VIDEO}

    ### TON SCÉNARIO (BOUCLE D'INTERACTION) :
    
    1. **ETAPE 1 : L'ACCROCHE (Seulement ça !)**
       - Dis Bonjour.
       - Pose une question concrète sur le quotidien liée au sujet (Situation Problème).
       - *STOP*. Attends la réponse de l'élève. NE FAIS RIEN D'AUTRE.

    2. **ETAPE 2 : L'OBSERVATION (Seulement après réponse de l'élève)**
       - Si vidéo dispo : Montre le lien.
       - Si pas de vidéo : Décris une expérience ou propose une visualisation graphique.
       - *STOP*. Demande "Qu'observes-tu ?" et Attends.

    3. **ETAPE 3 : LA VISUALISATION (Python)**
       - C'est ici que tu génères le code Python (`matplotlib`) pour tracer la courbe ou le phénomène.
       - Ne demande pas la permission. Fais-le.
       - Appelle ça "Visualisation Graphique" (pas simulation).
       - Aide l'élève à faire le lien Maths <-> Physique (y=ax, etc.).
       - *STOP*. Attends.

    4. **ETAPE 4 : CONCLUSION**
       - Donne la formule officielle.

    ⚠️ SI L'ÉLÈVE DIT JUSTE "BONJOUR", JOUE SEULEMENT L'ÉTAPE 1.
    """
else:
    ROLE = "Coach Socratique."
    CONSIGNE = "Ne donne jamais la réponse. Guide par des questions."

SYSTEM_PROMPT = f"""
{ROLE}
CONTEXTE : {lecon}
{CONSIGNE}
RÈGLES TECHNIQUES :
- Maths en LaTeX.
- Si tu génères du Python, utilise `matplotlib`.
- SOIS BREF.
"""

# --- 6. INTERFACE ---
st.title(lecon.replace(".pdf", ""))

if "messages" not in st.session_state: st.session_state.messages = []

# Affichage chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "code" in msg:
            for c in msg["code"]:
                try:
                    exec_globals = {"plt":plt, "np":np, "math":math, "st":st}
                    exec(c, exec_globals)
                    st.pyplot(plt.gcf())
                    plt.clf(); plt.close()
                except: pass

# Input
prompt = st.chat_input("Répondre au professeur...")

# Déclencheur automatique (Le bouton "Commencer" est caché, c'est auto si vide)
start_trigger = False
if mode == "🎓 Professeur Interactif" and len(st.session_state.messages) == 0:
    start_trigger = True

if prompt or start_trigger:
    txt = prompt if prompt else "Bonjour Professeur, je suis prêt."
    
    if not start_trigger:
        st.session_state.messages.append({"role":"user", "content":txt})
        with st.chat_message("user"): st.markdown(txt)

    with st.chat_message("assistant"):
        with st.spinner("..."):
            # Construction historique
            history = [f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]]
            full_prompt = f"HISTORIQUE:\n{history}\n\nACTUEL: {txt}"
            
            try:
                model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=SYSTEM_PROMPT)
                resp = model.generate_content(full_prompt)
                
                # Extraction
                clean_text = re.sub(r'```python.*?```', '', resp.text, flags=re.DOTALL)
                codes = re.findall(r'```python(.*?)```', resp.text, re.DOTALL)
                
                st.markdown(clean_text)
                for c in codes:
                    try:
                        exec_globals = {"plt":plt, "np":np, "math":math, "st":st}
                        exec(c, exec_globals)
                        st.pyplot(plt.gcf()) 
                        plt.clf(); plt.close()
                    except: pass
                
                st.session_state.messages.append({"role":"assistant", "content":clean_text, "code":codes})
            except Exception as e: st.error(str(e))
