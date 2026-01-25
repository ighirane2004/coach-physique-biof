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

# --- 2. LE PROGRAMME (Vos PDF) ---
PROGRAMME = {
    "2bac": {
        "Physique_1_Ondes": ["1_Ondes_progressives.pdf", "2_Ondes_periodiques.pdf", "3_Ondes_lumineuses.pdf"],
        "Physique_2_Nucleaire": ["1_Decroissance_radioactive.pdf", "2_Noyau_masse_energie.pdf"],
        "Physique_3_Electricite": ["1_Dipole_RC.pdf", "2_Dipole_RL.pdf", "3_Oscillations_RLC_serie.pdf", "4_Modulation_amplitude.pdf"],
        "Physique_4_Mecanique": ["1_Lois_de_Newton.pdf", "2_Chute_verticale.pdf", "3_Mouvements_plans.pdf", "4_Satellites_et_planetes.pdf", "5_Rotation_solide.pdf", "6_Systemes_oscillants.pdf", "7_Aspects_energetiques.pdf", "8_Atome_et_mecanique_Newton.pdf"],
        "Chimie_1_Lentes_Rapides": ["1_Transformations_lentes_rapides.pdf", "2_Suivi_temporel.pdf"],
        "Chimie_2_Transformations_Incompletes": ["1_Equilibre_chimique.pdf", "2_Reactions_acido_basiques.pdf", "3_Dosage_acido_basique.pdf"],
        "Chimie_3_Sens_Evolution": ["1_Evolution_spontanee.pdf", "2_Piles_et_energie.pdf", "3_Transformations_forcees.pdf"],
        "Chimie_4_Organique": ["1_Esterification_hydrolyse.pdf", "2_Controle_evolution.pdf"]
    },
    "1bac": {
        "Physique_1_Travail_Energie": ["1_Rotation_solide_axe_fixe.pdf", "2_Travail_puissance_force.pdf", "3_Travail_energie_cinetique.pdf", "4_Energie_potentielle_mecanique.pdf"],
        "Physique_2_Electricite_Magnetisme": ["5_Energie_electrique_recepteur.pdf", "6_Comportement_global_circuit.pdf", "7_Champ_magnetique.pdf", "8_Champ_magnetique_courant.pdf", "9_Forces_Laplace.pdf"],
        "Physique_3_Optique": ["10_Visibilite_objet.pdf", "11_Images_miroir_plan.pdf", "12_Lentille_mince_convergente.pdf"],
        "Chimie_1_Mesures": ["1_Importance_mesure.pdf", "2_Grandeurs_physiques.pdf", "3_Solutions_electrolytiques.pdf", "4_Suivi_transformation.pdf", "5_Conductimetrie.pdf", "6_Reactions_acido_basiques.pdf", "7_Reactions_oxydoreduction.pdf", "8_Dosages_directs.pdf"],
        "Chimie_2_Organique": ["1_Extension_chimie_orga.pdf", "2_Lecture_formule_chimique.pdf", "3_Molecules_organiques.pdf", "4_Squelette_carbone.pdf", "5_Groupes_caracteristiques.pdf"]
    },
    "tronc_commun": {
        "Physique_1_Mecanique": ["1_Gravitation_universelle.pdf", "2_Actions_mecaniques.pdf", "3_Mouvement.pdf", "4_Principe_inertie.pdf", "5_Equilibre_deux_forces.pdf", "6_Equilibre_trois_forces.pdf", "7_Equilibre_rotation_axe.pdf"],
        "Physique_2_Electricite": ["8_Courant_electrique.pdf", "9_Tension_electrique.pdf", "10_Associations_conducteurs.pdf", "11_Dipoles_passifs.pdf", "12_Dipoles_actifs.pdf", "13_Point_fonctionnement.pdf", "14_Transistor.pdf", "15_Amplificateur_operationnel.pdf"],
        "Chimie_1_Autour_de_nous": ["1_Especes_chimiques.pdf", "2_Extraction_separation.pdf", "3_Synthese_especes.pdf"],
        "Chimie_2_Constitution_matiere": ["4_Modele_atomique.pdf", "5_Geometrie_molecules.pdf", "6_Classification_periodique.pdf"],
        "Chimie_3_Transformations": ["7_Quantite_matiere.pdf", "8_Concentration_molaire.pdf", "9_Avancement_reaction.pdf"]
    }
}

# --- 3. CHARGEMENT VIDÉOS ---
def charger_videos():
    fichier_videos = "videos.json"
    if os.path.exists(fichier_videos):
        with open(fichier_videos, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

VIDEOS_COURS = charger_videos()

# --- 4. AUTHENTIFICATION ---
if "auth" not in st.session_state: st.session_state.auth = False

def login():
    code = st.session_state.input_code.strip()
    try: users = st.secrets["auth"]["users"]
    except: st.error("Secrets non configurés"); return
    
    if code in users:
        st.session_state.auth = True
        st.session_state.user_id = code
        st.session_state.user_level = users[code]
    else:
        st.error("Code incorrect")

if not st.session_state.auth:
    st.title("🔐 Espace Sciences")
    st.text_input("Code d'accès :", key="input_code", type="password", on_change=login)
    st.stop()

# --- 5. NAVIGATION ---
with st.sidebar:
    st.header(f"Prof. {st.session_state.user_id}")
    
    # Sélecteurs simples
    niveau_options = list(PROGRAMME.keys())
    niveau = st.selectbox("1. Niveau", niveau_options)
    
    chapitre_options = list(PROGRAMME[niveau].keys())
    partie = st.selectbox("2. Chapitre", chapitre_options)
    
    lecon_options = PROGRAMME[niveau][partie]
    lecon = st.selectbox("3. Leçon", lecon_options)
    
    st.divider()
    mode = st.radio("Mode", ["🎓 Professeur", "🏋️ Coach Exercices"])
    
    if st.button("🗑️ Reset Chat"):
        st.session_state.messages = []
        st.rerun()
    
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- 6. LE CERVEAU (Prompt Pédagogique Validé) ---

# Vérification présence vidéo
lien_video = VIDEOS_COURS.get(lecon, "")
instruction_video = ""
if lien_video:
    instruction_video = f"""
    - UNE VIDÉO EST DISPO : {lien_video}.
    - Tu DOIS proposer ce lien à l'élève dans la phase d'observation.
    """
else:
    instruction_video = """
    - PAS DE VIDÉO DISPO. Ne donne pas de lien YouTube.
    - Utilise une description ou propose de générer un graphique Python.
    """

if mode == "🎓 Professeur":
    ROLE = "Tu es un Professeur Expert, pédagogue et bienveillant."
    CONSIGNE = f"""
    🎯 TA MÉTHODE : "SENS -> OBSERVATION -> MODÉLISATION"
    
    Tu dois construire le savoir avec l'élève. Ne donne pas tout le cours d'un bloc.

    1. **PHASE 1 : L'ACCROCHE (Situation Problème)**
       - Commence toujours par "Bonjour".
       - Pose une question simple sur le quotidien liée au sujet (ex: vagues, électricité maison).
       - ATTENDS la réponse de l'élève.

    2. **PHASE 2 : L'OBSERVATION**
       {instruction_video}
       - Demande ce que l'élève observe.

    3. **PHASE 3 : LA PASSERELLE MATHS (Crucial)**
       - AIDE l'élève à faire le lien Maths <-> Physique.
       - Si c'est une droite : rappelle y=ax.
       - Si c'est une courbe (exp, log) : donne l'outil mathématique simple.

    4. **PHASE 4 : PYTHON (Visualisation)**
       - Si le phénomène est complexe, GÉNÈRE LE CODE PYTHON (matplotlib) pour tracer la courbe.
       - Ne demande pas la permission, fais-le si c'est utile.

    RÈGLE : Sois concis. Une étape à la fois.
    """
else:
    ROLE = "Coach Socratique."
    CONSIGNE = "Ne donne jamais la solution. Pose des questions pour guider l'élève."

SYSTEM_PROMPT = f"""
{ROLE}
CONTEXTE : Niveau {niveau}, Chapitre {partie}, Leçon {lecon}.
{CONSIGNE}
RÈGLES TECHNIQUES :
- Maths en LaTeX.
- Python via `matplotlib` uniquement (pas d'animation complexe, juste des graphes).
"""

# --- 7. INTERFACE CHAT ---
st.title(lecon.replace(".pdf", "").replace("_", " "))

if "messages" not in st.session_state: st.session_state.messages = []

# Affichage historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "code" in msg:
            try:
                exec(msg["code"], {"plt": plt, "np": np, "math": math, "st": st})
                st.pyplot(plt.gcf())
                plt.clf()
            except: pass

# Zone de saisie
prompt = st.chat_input("Votre message...")

# Déclencheur automatique (Bouton invisible si chat vide)
start_cours = False
if mode == "🎓 Professeur" and len(st.session_state.messages) == 0:
    # Lancement auto ou via bouton si besoin
    if st.button("🚀 Commencer le cours"):
        start_cours = True

if prompt or start_cours:
    user_text = prompt if prompt else "Bonjour Professeur, je suis prêt."
    
    if not start_cours:
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

    # Réponse IA
    with st.chat_message("assistant"):
        with st.spinner("Réflexion..."):
            # Historique pour le contexte
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
            full_prompt = f"HISTORIQUE:\n{history_text}\n\nUSER: {user_text}"
            
            try:
                model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=SYSTEM_PROMPT)
                response = model.generate_content(full_prompt)
                text_resp = response.text
                
                # Extraction Code Python
                code_match = re.search(r'```python(.*?)```', text_resp, re.DOTALL)
                code_exec = None
                
                clean_text = re.sub(r'```python.*?```', '', text_resp, flags=re.DOTALL)
                
                st.markdown(clean_text)
                
                if code_match:
                    code_exec = code_match.group(1)
                    try:
                        exec(code_exec, {"plt": plt, "np": np, "math": math, "st": st})
                        st.pyplot(plt.gcf())
                        plt.clf()
                    except Exception as e:
                        st.error(f"Erreur graphe : {e}")
                
                msg_data = {"role": "assistant", "content": clean_text}
                if code_exec: msg_data["code"] = code_exec
                st.session_state.messages.append(msg_data)
                
            except Exception as e:
                st.error(f"Erreur connexion : {e}")
