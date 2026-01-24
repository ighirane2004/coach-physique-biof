import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import os
import matplotlib.pyplot as plt
import numpy as np
import re

# --- 1. CONFIGURATION ROBUSTE ---
st.set_page_config(page_title="Coach Physique-Chimie", page_icon="⚛️", layout="wide")

# Vérification silencieuse de la clé API
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Erreur technique : Clé API non détectée.")
    st.stop()

# --- 2. STRUCTURE DU PROGRAMME (Votre Base de Données) ---
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

# --- 3. SYSTÈME D'AUTHENTIFICATION INTELLIGENT ---
if "auth" not in st.session_state: 
    st.session_state.auth = False
    st.session_state.user_level = None

def login():
    code_entre = st.session_state.input_code.strip()
    try:
        users_db = st.secrets["auth"]["users"]
    except:
        st.error("Erreur de configuration des accès.")
        return

    if code_entre in users_db:
        st.session_state.auth = True
        st.session_state.user_id = code_entre
        st.session_state.user_level = users_db[code_entre]
        st.toast(f"✅ Connecté : {st.session_state.user_level}")
    else:
        st.error("⛔ Code non reconnu.")

if not st.session_state.auth:
    st.title("🔐 Espace Sciences")
    st.markdown("Bienvenue sur votre plateforme de révision intelligente.")
    st.text_input("Entrez votre code d'accès :", key="input_code", type="password", on_change=login)
    st.stop()

# --- 4. NAVIGATION CONTEXTUELLE ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user_id}")
    st.caption(f"Profil : {st.session_state.user_level}")
    st.divider()
    
    user_lvl = st.session_state.user_level
    
    # Filtrage strict des niveaux
    if user_lvl == "admin":
        options_niveau = list(PROGRAMME.keys())
    elif user_lvl in PROGRAMME:
        options_niveau = [user_lvl]
    else:
        st.error(f"Configuration profil invalide ({user_lvl}).")
        st.stop()
            
    niveau = st.selectbox("1. Niveau", options_niveau)
    
    # Menus dynamiques
    parties_dispo = list(PROGRAMME[niveau].keys()) if niveau in PROGRAMME else []
    partie = st.selectbox("2. Chapitre", parties_dispo)
    
    lecons_dispo = PROGRAMME[niveau][partie] if partie in PROGRAMME[niveau] else []
    lecon = st.selectbox("3. Leçon", lecons_dispo)
    
    st.divider()
    mode = st.radio("Mode d'assistance", ["🎓 Professeur (Explications)", "🏋️ Coach (Entraînement)"])
    
    st.divider()
    if st.button("Se déconnecter"):
        st.session_state.auth = False
        st.rerun()

# --- 5. CERVEAU : INSTRUCTION "TOUT-EN-UN" ---
# C'est ici que nous définissons toutes les capacités scientifiques

if mode == "🎓 Professeur":
    ROLE = "Tu es un Professeur de Physique-Chimie expert et pédagogue."
    TON = "Explique les concepts clairement, donne des exemples, et détaille les étapes."
else:
    ROLE = "Tu es un Coach d'examen exigeant."
    TON = "Ne donne pas la réponse finale tout de suite. Guide l'élève pas à pas. Vérifie chaque étape."

SYSTEM_PROMPT = f"""
{ROLE}
TON : {TON}
CONTEXTE : Programme Marocain (BIOF), Niveau {niveau}, Chapitre {partie}.

RÈGLES ABSOLUES ET OUTILS OBLIGATOIRES :

1. **SILENCE TECHNIQUE (Vital)** : 
   - Ne dis JAMAIS "Voici le code Python" ou "J'utilise matplotlib".
   - L'élève ne doit voir que le résultat (courbe, image, tableau).
   - Contente-toi de dire : "Voici la représentation demandée :" ou "Voici le schéma :".

2. **FORMULES & MATHS (LaTeX)** :
   - TOUTES les expressions mathématiques doivent être en LaTeX.
   - Utilise toujours les balises dollars $.
   - Exemples : $\\vec{{P}} = m \\cdot \\vec{{g}}$, $pH = -\\log[H_3O^+]$, $\\int_{{t_1}}^{{t_2}} i(t) dt$.
   - Pour les vecteurs : Utilise toujours `\\vec{{}}`.

3. **COURBES & GRAPHIQUES (Python Matplotlib)** :
   - Si la question implique une évolution temporelle, une courbe (ex: $u_C(t)$, titrage pH, modulation), TU DOIS générer un graphique.
   - Génère le code Python silencieusement dans un bloc ```python.
   - Assure-toi que les axes sont nommés (xlabel, ylabel) et qu'il y a un titre.

4. **CHIMIE ORGANIQUE & MOLÉCULES** :
   - Pour les formules développées/semi-développées, utilise soit du LaTeX (chimie), soit une représentation texte claire alignée.
   - Pour les tableaux d'avancement : Utilise le format Markdown standard pour créer un tableau clair.

5. **NON-REPONSE** :
   - Si la question est hors du programme de Physique-Chimie (ex: SVT, Philosophie, Sport), réponds poliment que tu es spécialisé uniquement en Sciences Physiques.
"""

# --- 6. MOTEUR DE CHAT ET D'AFFICHAGE ---
st.title(lecon.replace(".pdf", "").replace("_", " "))
st.caption(f"Chapitre : {partie.replace('_', ' ')}")

# Zone d'upload (Image d'exercice)
with st.expander("📸 Analyser un exercice (Photo/Image)", expanded=False):
    tab_cam, tab_upl = st.tabs(["📸 Caméra", "📂 Fichier"])
    img_file = None
    with tab_cam:
        cam_img = st.camera_input("Prendre une photo")
        if cam_img: img_file = cam_img
    with tab_upl:
        upl_img = st.file_uploader("Importer une image", type=['png', 'jpg', 'jpeg'])
        if upl_img: img_file = upl_img

# Initialisation Historique
if "messages" not in st.session_state: st.session_state.messages = []
if "current_lecon" not in st.session_state: st.session_state.current_lecon = lecon

# Reset si changement de leçon
if st.session_state.current_lecon != lecon:
    st.session_state.messages = []
    st.session_state.current_lecon = lecon
    st.toast("Support de cours chargé.", icon="📚")

# Affichage de l'historique de conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display_text"])
        
        # Ré-affichage sécurisé de l'image si elle existe
        if "image_data" in msg and msg["image_data"] is not None:
            st.image(msg["image_data"], width=300)
        
        # Ré-exécution du graphique si présent
        if "figure_code" in msg and msg["figure_code"]:
            try:
                # Création d'un contexte propre pour chaque figure
                exec(msg["figure_code"], {"plt": plt, "np": np, "st": st})
                st.pyplot(plt.gcf())
                plt.close()
            except: pass

# --- TRAITEMENT DE LA QUESTION ---
prompt = st.chat_input("Posez votre question, demandez une courbe, ou envoyez une photo...")

if prompt or img_file:
    # 1. Préparation du contenu utilisateur
    user_content = []
    display_txt = prompt if prompt else "Analyse de l'exercice ci-joint."
    
    if prompt: 
        user_content.append(prompt)
    
    img_data_for_history = None
    if img_file:
        try:
            image = Image.open(img_file)
            user_content.append(image)
            img_data_for_history = image
            if not prompt: 
                user_content.append("Résous cet exercice en détaillant les étapes (Tableau d'avancement, Graphique ou Calculs si nécessaire).")
        except:
            st.error("Erreur de lecture de l'image.")

    # 2. Sauvegarde message utilisateur
    st.session_state.messages.append({
        "role": "user", 
        "display_text": display_txt, 
        "image_data": img_data_for_history
    })
    
    with st.chat_message("user"):
        st.markdown(display_txt)
        if img_data_for_history: st.image(img_data_for_history, width=300)

    # 3. Génération Réponse IA
    with st.chat_message("assistant"):
        with st.spinner("Analyse scientifique en cours..."):
            try:
                # Appel au modèle le plus performant (Gemini 2.0 Flash)
                model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=SYSTEM_PROMPT)
                response = model.generate_content(user_content)
                text = response.text
                
                # --- FILTRE ET NETTOYAGE DU CODE ---
                code = None
                if "```python" in text:
                    match = re.search(r'```python(.*?)```', text, re.DOTALL)
                    if match:
                        code = match.group(1)
                        # On retire le code de la réponse visible pour l'élève
                        text = text.replace(match.group(0), "") 
                
                # Affichage du texte (Formules LaTeX, Tableaux Markdown rendus automatiquement)
                st.markdown(text)
                
                # Exécution et Affichage du Graphique
                if code:
                    try:
                        exec(code, {"plt": plt, "np": np, "st": st})
                        st.pyplot(plt.gcf())
                        plt.close()
                    except Exception as e:
                        st.warning("Note : Le tracé graphique n'a pas pu être généré pour cette question spécifique.")

                # Sauvegarde dans l'historique
                st.session_state.messages.append({
                    "role": "assistant", 
                    "display_text": text, 
                    "figure_code": code
                })
                
                # Synthèse Vocale (Optionnelle)
                try:
                    # On nettoie le texte pour l'audio (retrait du LaTeX complexe)
                    clean_text = text.replace("*","").replace("$", "")
                    tts = gTTS(clean_text, lang='fr')
                    bio = io.BytesIO()
                    tts.write_to_fp(bio)
                    st.audio(bio, format='audio/mp3')
                except: pass

            except Exception as e:
                st.error("Une erreur de connexion est survenue. Veuillez réessayer.")
