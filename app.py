import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import os
import matplotlib.pyplot as plt
import numpy as np
import re

# --- IMPORTS CHIMIE (Gestion silencieuse) ---
try:
    from rdkit import Chem
    from rdkit.Chem import Draw
except ImportError:
    pass

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Coach Physique-Chimie", page_icon="⚛️", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Erreur : Clé API non configurée dans les Secrets.")
    st.stop()

# --- 2. PROGRAMME SCOLAIRE ---
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

# --- 3. AUTHENTIFICATION ---
if "auth" not in st.session_state: 
    st.session_state.auth = False
    st.session_state.user_level = None

def login():
    code_entre = st.session_state.input_code.strip()
    try:
        users_db = st.secrets["auth"]["users"]
    except:
        st.error("Erreur de configuration (Secrets).")
        return

    if code_entre in users_db:
        st.session_state.auth = True
        st.session_state.user_id = code_entre
        st.session_state.user_level = users_db[code_entre]
        st.toast(f"✅ Connecté : {st.session_state.user_level}")
    else:
        st.error("⛔ Code incorrect")

if not st.session_state.auth:
    st.title("🔐 Espace Sciences")
    st.text_input("Code d'accès :", key="input_code", type="password", on_change=login)
    st.stop()

# --- 4. NAVIGATION ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user_id}")
    user_lvl = st.session_state.user_level
    
    if user_lvl == "admin": options_niveau = list(PROGRAMME.keys())
    elif user_lvl in PROGRAMME: options_niveau = [user_lvl]
    else: st.stop()
            
    niveau = st.selectbox("1. Niveau", options_niveau)
    parties_dispo = list(PROGRAMME[niveau].keys()) if niveau in PROGRAMME else []
    partie = st.selectbox("2. Chapitre", parties_dispo)
    lecons_dispo = PROGRAMME[niveau][partie] if partie in PROGRAMME[niveau] else []
    lecon = st.selectbox("3. Leçon", lecons_dispo)
    
    st.divider()
    mode = st.radio("Mode", ["🎓 Professeur", "🏋️ Coach"])
    
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- 5. CERVEAU (Instructions Système) ---
if mode == "🎓 Professeur":
    ROLE = "Tu es un Professeur expert et pédagogue."
else:
    ROLE = "Tu es un Coach. Tu guides l'élève pas à pas."

SYSTEM_PROMPT = f"""
{ROLE}
CONTEXTE : Programme Marocain, Niveau {niveau}, Chapitre {partie}.

RÈGLES D'ACTION :
1. **MODE EXÉCUTANT** : Si l'élève demande un schéma, une courbe ou une molécule, FAIS-LE immédiatement.
   - Ne demande pas "Voulez-vous le code ?".
   - Utilise Python silencieusement.

2. **CHIMIE ORGANIQUE** :
   - Pour dessiner : Utilise `rdkit`.
   - Code type : `from rdkit import Chem; from rdkit.Chem import Draw; mol = Chem.MolFromSmiles('SMILES'); img = Draw.MolToImage(mol); plt.imshow(img); plt.axis('off')`

3. **MATHS & LATEX** :
   - Écris les formules mathématiques en LaTeX entre dollars $.
   - Exemple : $E_c = \\frac{{1}}{{2}} m v^2$.

4. **SILENCE TECHNIQUE** :
   - Ne montre JAMAIS le code Python à l'élève. Affiche uniquement le résultat visuel.
"""

# --- 6. CHAT & INTERFACE ---
st.title(lecon.replace(".pdf", "").replace("_", " "))

# Zone d'upload
with st.expander("📸 Envoyer une image", expanded=False):
    tab_cam, tab_upl = st.tabs(["Caméra", "Fichier"])
    img_file = None
    with tab_cam:
        c = st.camera_input("Photo")
        if c: img_file = c
    with tab_upl:
        u = st.file_uploader("Upload", type=['png', 'jpg', 'jpeg'])
        if u: img_file = u

# Initialisation
if "messages" not in st.session_state: st.session_state.messages = []
if "current_lecon" not in st.session_state: st.session_state.current_lecon = lecon

if st.session_state.current_lecon != lecon:
    st.session_state.messages = []
    st.session_state.current_lecon = lecon
    st.toast("Nouveau cours chargé.", icon="📚")

# Affichage de l'historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display_text"])
        if "image_data" in msg and msg["image_data"]: 
            st.image(msg["image_data"], width=300)
        if "figure_code" in msg and msg["figure_code"]:
            try:
                exec_globals = {"plt": plt, "np": np, "st": st}
                try: 
                    from rdkit import Chem
                    from rdkit.Chem import Draw
                    exec_globals["Chem"] = Chem
                    exec_globals["Draw"] = Draw
                except: pass
                
                exec(msg["figure_code"], exec_globals)
                st.pyplot(plt.gcf())
                plt.close()
            except: pass

# --- ZONE DE SAISIE AVEC MÉMOIRE ---
prompt = st.chat_input("Pose ta question ou demande un dessin...")

if prompt or img_file:
    user_content = []
    
    # 1. Construction du contexte (Mémoire)
    display_txt = prompt if prompt else "Analyse image..."
    
    if prompt:
        # On récupère les 6 derniers messages pour la mémoire
        history_context = "CONTEXTE (Discussion précédente) :\n"
        recent_msgs = st.session_state.messages[-6:] 
        for msg in recent_msgs:
            role_label = "ÉLÈVE" if msg["role"] == "user" else "PROF"
            # Nettoyage du code technique pour la mémoire
            clean_msg = msg["display_text"].replace("```python", "[Code Graphique]").replace("```", "")
            history_context += f"- {role_label} : {clean_msg}\n"
        
        # On injecte le rappel avant la question actuelle
        final_prompt_text = f"{history_context}\n\nQUESTION ACTUELLE : {prompt}"
        user_content.append(final_prompt_text)
    
    img_data = None
    if img_file:
        img_data = Image.open(img_file)
        user_content.append(img_data)
        if not prompt: user_content.append("Analyse ceci en tenant compte de la discussion.")

    # 2. Affichage immédiat
    st.session_state.messages.append({"role": "user", "display_text": display_txt, "image_data": img_data})
    with st.chat_message("user"):
        st.markdown(display_txt)
        if img_data: st.image(img_data, width=300)

    # 3. Réponse IA
    with st.chat_message("assistant"):
        with st.spinner("Réflexion..."):
            try:
                model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=SYSTEM_PROMPT)
                
                response = model.generate_content(user_content)
                text = response.text
                
                # Extraction et Nettoyage du Code
                code = None
                if "```python" in text:
                    match = re.search(r'```python(.*?)```', text, re.DOTALL)
                    if match:
                        code = match.group(1)
                        # On retire le code de l'affichage texte
                        text = text.replace(match.group(0), "")
                
                st.markdown(text)
                
                # Exécution du Graphique / Molécule
                if code:
                    try:
                        exec_globals = {"plt": plt, "np": np, "st": st}
                        try: 
                            from rdkit import Chem
                            from rdkit.Chem import Draw
                            exec_globals["Chem"] = Chem
                            exec_globals["Draw"] = Draw
                        except: pass
                        
                        exec(code, exec_globals)
                        st.pyplot(plt.gcf())
                        plt.close()
                    except Exception as e:
                        st.warning(f"Erreur d'affichage graphique : {e}")

                # Sauvegarde
                st.session_state.messages.append({"role": "assistant", "display_text": text, "figure_code": code})
                
                # Audio (TTS)
                try:
                    clean_text = text.replace("*","").replace("$", "")
                    tts = gTTS(clean_text, lang='fr')
                    bio = io.BytesIO()
                    tts.write_to_fp(bio)
                    st.audio(bio, format='audio/mp3')
                except: pass

            except Exception as e:
                st.error(f"Erreur de connexion : {e}")
