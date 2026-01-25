import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import matplotlib.pyplot as plt
import numpy as np
import math
import re
import json

# --- IMPORTS CHIMIE (Optionnel) ---
try:
    from rdkit import Chem
    from rdkit.Chem import Draw
    from rdkit.Chem import rdDepictor
    from rdkit.Chem.Draw import rdMolDraw2D
except ImportError:
    pass

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Coach Physique-Chimie", page_icon="⚛️", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Erreur : Clé API non configurée.")
    st.stop()

# --- 2. LE PROGRAMME ---
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

# --- 4. MÉMOIRE ---
DB_FILE = "memoire_eleves.json"
def charger_memoire():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {}
def sauvegarder_position(user_id, niveau, partie, lecon):
    data = charger_memoire()
    data[user_id] = {"niveau": niveau, "partie": partie, "lecon": lecon}
    with open(DB_FILE, "w") as f: json.dump(data, f)

# --- 5. AUTH ---
if "auth" not in st.session_state: st.session_state.auth = False
def login():
    code = st.session_state.input_code.strip()
    try: users_db = st.secrets["auth"]["users"]
    except: st.error("Erreur secrets"); return
    if code in users_db:
        st.session_state.auth = True
        st.session_state.user_id = code
        st.session_state.user_level = users_db[code]
        st.toast(f"✅ Bonjour {code}")
    else: st.error("Code incorrect")

if not st.session_state.auth:
    st.title("🔐 Espace Sciences")
    st.text_input("Code :", key="input_code", type="password", on_change=login)
    st.stop()

# --- 6. NAV ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user_id}")
    user_lvl = st.session_state.user_level
    memoire = charger_memoire()
    last_pos = memoire.get(st.session_state.user_id, {})
    
    if user_lvl == "admin": options_niveau = list(PROGRAMME.keys())
    elif user_lvl in PROGRAMME: options_niveau = [user_lvl]
    else: st.stop()
    
    def get_index(l, v):
        try: return l.index(v)
        except: return 0

    idx_niv = get_index(options_niveau, last_pos.get("niveau"))
    niveau = st.selectbox("1. Niveau", options_niveau, index=idx_niv)
    
    parties = list(PROGRAMME[niveau].keys()) if niveau in PROGRAMME else []
    idx_part = get_index(parties, last_pos.get("partie"))
    partie = st.selectbox("2. Chapitre", parties, index=idx_part)
    
    lecons = PROGRAMME[niveau][partie] if partie in PROGRAMME[niveau] else []
    idx_lec = get_index(lecons, last_pos.get("lecon"))
    lecon = st.selectbox("3. Leçon", lecons, index=idx_lec)
    
    sauvegarder_position(st.session_state.user_id, niveau, partie, lecon)
    st.divider()
    mode = st.radio("Mode", ["🎓 Professeur", "🏋️ Coach Exercices"])
    
    st.markdown("### 🎤 Vocal")
    audio_val = st.audio_input("Parler")
    
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- 7. CERVEAU (CORRECTION ANTI-HALLUCINATION) ---

# On prépare l'info vidéo pour l'IA
lien_video = VIDEOS_COURS.get(lecon, "")
if lien_video:
    info_video_prompt = f"UNE VIDÉO EST DISPONIBLE ICI : {lien_video}. Tu DOIS la proposer."
else:
    info_video_prompt = "AUCUNE VIDÉO DISPONIBLE pour cette leçon. NE PAS inventer de lien. Saute l'étape vidéo."

if mode == "🎓 Professeur":
    ROLE = "Tu es un Professeur Expert, pédagogue et concret."
    CONSIGNE = f"""
    🎯 TA MÉTHODE : "SENS -> OBSERVATION -> MODÈLE"
    
    {info_video_prompt}

    ### RÈGLES STRICTES (ANTI-HALLUCINATION) :
    1. **PAS DE LIENS INVENTÉS** : Si je t'ai dit "AUCUNE VIDÉO", ne donne AUCUN lien YouTube. Passe directement à une description ou une simulation.
    2. **PYTHON AUTOMATIQUE** : Ne demande JAMAIS "Veux-tu une simulation ?". Ne demande JAMAIS "Connais-tu Python ?".
       - Si tu dois illustrer un phénomène dynamique (Onde, RC, Trajectoire), **GÉNÈRE LE CODE DIRECTEMENT** entre des balises ```python.
       - Ne donne JAMAIS de lien vers Imgur ou des sites externes pour les images. Utilise UNIQUEMENT le code Python (`matplotlib`).
    
    ### DÉROULEMENT DU COURS :
    1. **Accroche** : Situation problème du quotidien.
    2. **Observation** : Vidéo (si dispo) OU Expérience de pensée.
    3. **Simulation (OBLIGATOIRE si dynamique)** : Tu écris le code Python, le système l'affichera. Dis : "Voici la simulation :" et mets le bloc de code.
    4. **Formalisation** : Ensuite seulement, tu donnes les formules.
    """
else:
    ROLE = "Tu es un Coach Socratique."
    CONSIGNE = "Aide l'élève sans donner la réponse. Pose des questions guides."

SYSTEM_PROMPT = f"""
{ROLE}
CONTEXTE : {niveau}, {partie}, {lecon}.
{CONSIGNE}
RÈGLES TECHNIQUES :
- Maths en LaTeX.
- Réponses courtes (Max 3 phrases).
- Si tu génères du Python, utilise `matplotlib`.
"""

# --- 8. INTERFACE ---
st.title(lecon.replace(".pdf", "").replace("_", " "))

with st.expander("📸 Envoyer image"):
    c = st.camera_input("Photo")
    u = st.file_uploader("Upload")
    img_file = c if c else u

if "messages" not in st.session_state: st.session_state.messages = []
if "curr_lec" not in st.session_state: st.session_state.curr_lec = lecon
if st.session_state.curr_lec != lecon:
    st.session_state.messages = []
    st.session_state.curr_lec = lecon

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img" in msg and msg["img"]: st.image(msg["img"], width=300)
        if "code" in msg:
            for c in msg["code"]:
                try:
                    exec_globals = {"plt":plt, "np":np, "math":math, "st":st}
                    exec(c, exec_globals)
                    st.pyplot(plt.gcf())
                    plt.close()
                except: pass

# --- INPUT ---
prompt = st.chat_input("...")
start_cours = False
if mode == "🎓 Professeur" and len(st.session_state.messages) == 0:
    if st.button("🚀 Commencer le cours"): start_cours = True

# --- TRAITEMENT ---
if prompt or start_cours or audio_val or img_file:
    # User Input
    txt = prompt if prompt else "..."
    if start_cours: txt = "Bonjour Professeur ! Je suis prêt, de quoi parle-t-on ?"
    if audio_val and not prompt: txt = "🎤 [Audio]"
    
    # Affichage User (sauf si audio seul déjà géré)
    if not (audio_val and not prompt and not start_cours):
        with st.chat_message("user"):
            st.markdown(txt)
            if img_file: st.image(img_file, width=300)
            if audio_val: st.audio(audio_val)
    
    st.session_state.messages.append({"role":"user", "content":txt, "img":img_file})

    # AI Response
    with st.chat_message("assistant"):
        with st.spinner("Réflexion..."):
            user_content = [txt]
            if img_file: user_content.append(Image.open(img_file))
            if audio_val: user_content.append({"mime_type": "audio/wav", "data": audio_val.getvalue()})
            
            # Context History
            hist = "HISTORIQUE:\n" + "\n".join([f"{m['role']}:{m['content']}" for m in st.session_state.messages[-10:]])
            user_content[0] = f"{hist}\nACTUEL: {txt}"

            try:
                model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=SYSTEM_PROMPT)
                resp = model.generate_content(user_content)
                
                # Extraction Code
                codes = re.findall(r'```python(.*?)```', resp.text, re.DOTALL)
                clean_text = re.sub(r'```python.*?```', '', resp.text, flags=re.DOTALL)
                
                st.markdown(clean_text)
                
                # Exécution Code
                for code in codes:
                    try:
                        exec_globals = {"plt":plt, "np":np, "math":math, "st":st}
                        # Imports Chimie si dispo
                        try:
                            exec_globals.update({"Chem":Chem, "Draw":Draw, "rdDepictor":rdDepictor, "rdMolDraw2D":rdMolDraw2D})
                        except: pass
                        
                        exec(code, exec_globals)
                        st.pyplot(plt.gcf())
                        plt.clf(); plt.close()
                    except Exception as e: st.error(f"Erreur graphe: {e}")

                st.session_state.messages.append({"role":"assistant", "content":clean_text, "code":codes})
            except Exception as e: st.error(f"Erreur: {e}")
