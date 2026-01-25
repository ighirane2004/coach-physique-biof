import streamlit as st
import google.generativeai as genai
import matplotlib.pyplot as plt
import numpy as np
import time
import json
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Coach Sciences", page_icon="⚛️", layout="centered") # Centered pour focus

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
    }
}

def charger_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

SCENARIOS = charger_json("scenarios.json")

# --- 3. MOTEUR D'ANIMATION (Le secret est ici) ---
def generer_animation_corde():
    """Crée une boucle d'animation pour Streamlit"""
    code = """
import numpy as np
import matplotlib.pyplot as plt
import time

# On crée un conteneur vide dans Streamlit qui va se mettre à jour
placeholder = st.empty()

# Boucle d'animation (50 images)
x = np.linspace(0, 10, 200)
point_M_idx = 100 # Le point rouge au milieu

for t in np.linspace(0, 5, 50):
    # L'équation de l'onde qui avance (x - vt)
    y = 0.5 * np.exp(-(x - 2.5 * t + 2)**2 * 2) 
    
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(x, y, 'b-', linewidth=2, label="Corde")
    
    # Le point rouge (Matière)
    ax.plot(x[point_M_idx], y[point_M_idx], 'ro', markersize=12, label="Point M")
    
    # Flèche pour montrer le mouvement vertical du point
    if y[point_M_idx] > 0.05:
        ax.arrow(x[point_M_idx], y[point_M_idx], 0, 0.2, head_width=0.1, color='red')

    ax.set_ylim(-0.5, 1)
    ax.set_title(f"Animation : La vague avance, le point rouge monte/descend")
    ax.grid(True)
    ax.legend(loc='upper right')
    
    # Affichage dans le conteneur Streamlit
    placeholder.pyplot(fig)
    plt.close(fig)
    time.sleep(0.05) # Vitesse de l'animation
"""
    return code

def generer_animation_ressort():
    """Animation simple pour le ressort (Traits verticaux qui se rapprochent)"""
    code = """
import numpy as np
import matplotlib.pyplot as plt
import time

placeholder = st.empty()

# Position des spires au repos
x_base = np.linspace(0, 10, 20) 

for t in np.linspace(0, 10, 40):
    # Perturbation qui avance
    deplacement = 0.4 * np.exp(-(x_base - 0.5 * t + 1)**2 * 2)
    x_actuel = x_base + deplacement # Déplacement Longitudinal
    
    fig, ax = plt.subplots(figsize=(8, 2))
    # On dessine les spires comme des lignes verticales
    for pos in x_actuel:
        ax.vlines(pos, -1, 1, colors='k', linewidth=2)
    
    ax.set_xlim(0, 10)
    ax.set_ylim(-2, 2)
    ax.set_title("Onde Longitudinale (Compression)")
    ax.get_yaxis().set_visible(False)
    
    placeholder.pyplot(fig)
    plt.close(fig)
    time.sleep(0.05)
"""
    return code

# --- 4. INTERFACE ---
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

with st.sidebar:
    st.header("📚 Cours")
    niveau = "2bac"
    partie = st.selectbox("Chapitre", list(PROGRAMME[niveau].keys()))
    lecon = st.selectbox("Leçon", PROGRAMME[niveau][partie])
    st.divider()
    if st.button("🔄 Recommencer la leçon"):
        st.session_state.messages = []
        st.session_state.etape_active = 0
        st.rerun()

# --- CERVEAU ---
st.title(lecon.replace(".pdf", ""))

if "messages" not in st.session_state: st.session_state.messages = []
if "etape_active" not in st.session_state: st.session_state.etape_active = 0

scenario_data = SCENARIOS.get(lecon, None)

# Affiche historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Note : On ne rejoue pas l'animation dans l'historique pour ne pas surcharger,
        # on pourrait afficher une image fixe ici, mais restons simple.

# Input
prompt = st.chat_input("Ta réponse...")

# Trigger Démarrage
trigger = False
if len(st.session_state.messages) == 0:
    trigger = True

if prompt or trigger:
    user_text = prompt if prompt else "Bonjour Professeur."
    
    if not trigger:
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"): st.markdown(user_text)

    # Logique Scénario
    if scenario_data and st.session_state.etape_active < len(scenario_data["etapes"]):
        step = scenario_data["etapes"][st.session_state.etape_active]
        
        # Sélection Animation
        code_anim = None
        if step["action_ia"] == "PYTHON_CORDE":
            code_anim = generer_animation_corde()
        elif step["action_ia"] == "PYTHON_RESSORT":
            code_anim = generer_animation_ressort()
        
        # PROMPT RENFORCÉ (INTRO OBLIGATOIRE)
        system_instruction = f"""
        Tu es le Professeur.
        SCÉNARIO : {step['titre']}
        CONSIGNE : {step['consigne_prof']}
        
        RÈGLE IMPÉRATIVE :
        - Si c'est l'Étape 1 (Situation Problème) : Tu DOIS dire "Bonjour", annoncer le Titre, puis poser la situation problème. N'affiche RIEN d'autre.
        - Si c'est une étape suivante : Valide la réponse précédente de l'élève, puis pose la nouvelle question : "{step['question_cle']}".
        """
        
        with st.chat_message("assistant"):
            with st.spinner("..."):
                model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system_instruction)
                response = model.generate_content(user_text)
                text_resp = response.text
                
                st.markdown(text_resp)
                
                # Exécution de l'animation SI présente
                if code_anim:
                    st.caption("📺 *Génération de l'animation en cours...*")
                    # On exécute le code qui contient la boucle d'animation
                    exec(code_anim, {"plt": plt, "np": np, "st": st, "time": time})

                st.session_state.messages.append({"role": "assistant", "content": text_resp})

        # Passage étape suivante
        st.session_state.etape_active += 1 

    else:
        st.success("Leçon terminée ! As-tu des questions ?")
