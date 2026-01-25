import streamlit as st
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import time
import json
import os
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Coach Sciences", page_icon="⚛️", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Clé API manquante.")
    st.stop()

# --- 2. DONNÉES ---
PROGRAMME = {
    "2bac": {
        "Physique_1_Ondes": ["1_Ondes_progressives.pdf"],
        # Ajoutez vos autres leçons ici
    }
}

def charger_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

SCENARIOS = charger_json("scenarios.json")
VIDEOS = charger_json("videos.json")

# --- 3. FONCTIONS DE SIMULATION (Remplacent Flash) ---
def generer_simulation_corde():
    """Génère le code pour l'onde transversale"""
    code = """
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 10, 500)
t = 0  # Instant initial
y = 0.5 * np.exp(-(x - 2)**2 * 5) # Forme d'une impulsion (bosse)

plt.figure(figsize=(10, 4))
plt.plot(x, y, 'b-', linewidth=2, label="Corde")
# Le point rouge (Matière)
idx_point = 250 # Milieu de corde
plt.plot(x[idx_point], y[idx_point], 'ro', markersize=10, label="Point M (Matière)")
plt.arrow(x[idx_point], y[idx_point], 0, 0.3, head_width=0.1, head_length=0.1, fc='r', ec='r')

plt.title("Simulation Onde Transversale (La corde monte, l'onde avance)")
plt.xlabel("Position x (m)")
plt.ylabel("Élongation y (m)")
plt.legend()
plt.grid(True)
plt.show()
"""
    return code

def generer_simulation_retard():
    """Génère le code pour expliquer le retard Tau"""
    code = """
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 10, 500)
# Onde à l'instant t
y1 = np.exp(-(x - 2)**2 * 5) 
# Onde à l'instant t' (décalée)
y2 = np.exp(-(x - 5)**2 * 5)

plt.figure(figsize=(10, 4))
plt.plot(x, y1, 'b--', label="Instant t (Point M)")
plt.plot(x, y2, 'r-', label="Instant t' (Point M')")

plt.annotate('', xy=(2, 1.1), xytext=(5, 1.1), arrowprops=dict(arrowstyle='<->'))
plt.text(3.5, 1.15, "Distance d = v * Tau", ha='center')

plt.title("Illustration du Retard Temporel Tau")
plt.legend()
plt.grid(True)
plt.show()
"""
    return code

# --- 4. INTERFACE & LOGIQUE ---
if "auth" not in st.session_state: st.session_state.auth = False

def login():
    code = st.session_state.input_code.strip()
    try: users = st.secrets["auth"]["users"]
    except: return
    if code in users:
        st.session_state.auth = True
        st.session_state.user_id = code
        st.session_state.user_level = users[code]

if not st.session_state.auth:
    st.title("🔐 Accès")
    st.text_input("Code:", key="input_code", type="password", on_change=login)
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("📚 Mon Cours")
    niveau = "2bac"
    partie = st.selectbox("Chapitre", list(PROGRAMME[niveau].keys()))
    lecon = st.selectbox("Leçon", PROGRAMME[niveau][partie])
    
    st.divider()
    if st.button("🔄 Recommencer la leçon"):
        st.session_state.messages = []
        st.session_state.etape_active = 0
        st.rerun()

# --- CERVEAU DU SCÉNARIO ---
st.title(lecon.replace(".pdf", ""))

if "messages" not in st.session_state: st.session_state.messages = []
if "etape_active" not in st.session_state: st.session_state.etape_active = 0

# Récupération du scénario de la leçon choisie
scenario_data = SCENARIOS.get(lecon, None)

# AFFICHAGE CHAT
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "code" in msg:
            try:
                exec(msg["code"], {"plt": plt, "np": np})
                st.pyplot(plt.gcf())
                plt.clf()
            except: pass

# INPUT UTILISATEUR
prompt = st.chat_input("Ta réponse...")

# DÉCLENCHEMENT AUTOMATIQUE (Démarrage)
trigger = False
if len(st.session_state.messages) == 0:
    trigger = True

if prompt or trigger:
    # 1. Gestion du message utilisateur
    user_text = prompt if prompt else "Bonjour !"
    if not trigger:
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"): st.markdown(user_text)

    # 2. Récupération de l'étape en cours
    if scenario_data and st.session_state.etape_active < len(scenario_data["etapes"]):
        step = scenario_data["etapes"][st.session_state.etape_active]
        
        # Préparation des outils pour l'étape
        code_a_afficher = None
        if step["action_ia"] == "PYTHON_CORDE":
            code_a_afficher = generer_simulation_corde()
        elif step["action_ia"] == "PYTHON_RETARD":
            code_a_afficher = generer_simulation_retard()
        
        # Instruction pour Gemini : Jouer le rôle du prof pour CETTE étape
        system_instruction = f"""
        Tu es un Professeur de Physique.
        CONTEXTE : Tu suis un plan de cours strict.
        ÉTAPE ACTUELLE : {step['titre']}
        
        TA MISSION : 
        1. Lis la consigne prof : "{step['consigne_prof']}"
        2. Pose la question à l'élève : "{step['question_cle']}"
        3. Si l'élève a donné la bonne réponse ("{step['reponse_attendue']}"), félicite-le et dis que tu passes à la suite.
        4. Si l'élève a faux, guide-le sans donner la réponse.
        
        IMPORTANT : Si l'élève vient juste de dire "Bonjour", commence directement par poser la question de l'étape.
        """
        
        # Génération réponse
        with st.chat_message("assistant"):
            with st.spinner("..."):
                model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system_instruction)
                response = model.generate_content(user_text)
                text_resp = response.text
                
                st.markdown(text_resp)
                if code_a_afficher:
                    st.pyplot(plt.gcf()) # Affiche le graphe généré par la fonction interne
                    # On exécute le code pour l'affichage immédiat
                    exec(code_a_afficher, {"plt": plt, "np": np})
                    st.pyplot(plt.gcf())
                    plt.clf()

                # Sauvegarde
                msg_data = {"role": "assistant", "content": text_resp}
                if code_a_afficher: msg_data["code"] = code_a_afficher
                st.session_state.messages.append(msg_data)

        # Logique de passage à l'étape suivante (Simplifiée pour l'exemple : on avance à chaque tour, 
        # mais idéalement on devrait vérifier si la réponse est bonne avec l'IA)
        # Pour l'instant, l'élève avance manuellement ou l'IA gère la validation dans le texte.
        # Pour rendre ça auto, on incrémentera "etape_active" seulement si l'IA détecte "Bonne réponse".
        st.session_state.etape_active += 1 

    else:
        st.info("Leçon terminée ! Bravo.")
