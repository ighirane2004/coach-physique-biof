import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import os
import matplotlib.pyplot as plt
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Coach Physique-Chimie", page_icon="⚛️", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("Erreur : Clé API manquante.")
    st.stop()

# --- 2. LE PROGRAMME (Correspond à vos dossiers GitHub) ---
PROGRAMME = {
    "2bac": {
        "Physique_1_Ondes": [
            "1_Ondes_progressives.pdf",
            "2_Ondes_periodiques.pdf",
            "3_Ondes_lumineuses.pdf"
        ],
        "Physique_2_Nucleaire": [
            "1_Decroissance_radioactive.pdf",
            "2_Noyau_masse_energie.pdf"
        ],
        "Physique_3_Electricite": [
            "1_Dipole_RC.pdf",
            "2_Dipole_RL.pdf",
            "3_Oscillations_RLC_serie.pdf",
            "4_Modulation_amplitude.pdf"
        ],
        "Physique_4_Mecanique": [
            "1_Lois_de_Newton.pdf",
            "2_Chute_verticale.pdf",
            "3_Mouvements_plans.pdf",
            "4_Satellites_et_planetes.pdf",
            "5_Rotation_solide.pdf",
            "6_Systemes_oscillants.pdf",
            "7_Aspects_energetiques.pdf",
            "8_Atome_et_mecanique_Newton.pdf"
        ],
        "Chimie_1_Lentes_Rapides": [
            "1_Transformations_lentes_rapides.pdf",
            "2_Suivi_temporel.pdf"
        ],
        "Chimie_2_Transformations_Incompletes": [
            "1_Equilibre_chimique.pdf",
            "2_Reactions_acido_basiques.pdf",
            "3_Dosage_acido_basique.pdf"
        ],
        "Chimie_3_Sens_Evolution": [
            "1_Evolution_spontanee.pdf",
            "2_Piles_et_energie.pdf",
            "3_Transformations_forcees.pdf"
        ],
        "Chimie_4_Organique": [
            "1_Esterification_hydrolyse.pdf",
            "2_Controle_evolution.pdf"
        ]
    },
    "1bac": {
        "Physique_1_Travail_Energie": [
            "1_Rotation_solide_axe_fixe.pdf",
            "2_Travail_puissance_force.pdf",
            "3_Travail_energie_cinetique.pdf",
            "4_Energie_potentielle_mecanique.pdf"
        ],
        "Physique_2_Electricite_Magnetisme": [
            "5_Energie_electrique_recepteur.pdf",
            "6_Comportement_global_circuit.pdf",
            "7_Champ_magnetique.pdf",
            "8_Champ_magnetique_courant.pdf",
            "9_Forces_Laplace.pdf"
        ],
        "Physique_3_Optique": [
            "10_Visibilite_objet.pdf",
            "11_Images_miroir_plan.pdf",
            "12_Lentille_mince_convergente.pdf"
        ],
        "Chimie_1_Mesures": [
            "1_Importance_mesure.pdf",
            "2_Grandeurs_physiques.pdf",
            "3_Solutions_electrolytiques.pdf",
            "4_Suivi_transformation.pdf",
            "5_Conductimetrie.pdf",
            "6_Reactions_acido_basiques.pdf",
            "7_Reactions_oxydoreduction.pdf",
            "8_Dosages_directs.pdf"
        ],
        "Chimie_2_Organique": [
            "1_Extension_chimie_orga.pdf",
            "2_Lecture_formule_chimique.pdf",
            "3_Molecules_organiques.pdf",
            "4_Squelette_carbone.pdf",
            "5_Groupes_caracteristiques.pdf"
        ]
    },
    "tronc_commun": {
        "Physique_1_Mecanique": [
            "1_Gravitation_universelle.pdf",
            "2_Actions_mecaniques.pdf",
            "3_Mouvement.pdf",
            "4_Principe_inertie.pdf",
            "5_Equilibre_deux_forces.pdf",
            "6_Equilibre_trois_forces.pdf",
            "7_Equilibre_rotation_axe.pdf"
        ],
        "Physique_2_Electricite": [
            "8_Courant_electrique.pdf",
            "9_Tension_electrique.pdf",
            "10_Associations_conducteurs.pdf",
            "11_Dipoles_passifs.pdf",
            "12_Dipoles_actifs.pdf",
            "13_Point_fonctionnement.pdf",
            "14_Transistor.pdf",
            "15_Amplificateur_operationnel.pdf"
        ],
        "Chimie_1_Autour_de_nous": [
            "1_Especes_chimiques.pdf",
            "2_Extraction_separation.pdf",
            "3_Synthese_especes.pdf"
        ],
        "Chimie_2_Constitution_matiere": [
            "4_Modele_atomique.pdf",
            "5_Geometrie_molecules.pdf",
            "6_Classification_periodique.pdf"
        ],
        "Chimie_3_Transformations": [
            "7_Quantite_matiere.pdf",
            "8_Concentration_molaire.pdf",
            "9_Avancement_reaction.pdf"
        ]
    }
}

# --- 3. SÉCURITÉ ---
if "auth" not in st.session_state: st.session_state.auth = False

def login():
    code = st.session_state.input_code.strip()
    try:
        if code in st.secrets["auth"]["codes_valides"]:
            st.session_state.auth = True
            st.session_state.user_id = code
            st.toast("✅ Connexion réussie")
        else:
            st.error("⛔ Code invalide")
    except:
        st.error("Erreur de configuration")

if not st.session_state.auth:
    st.title("🔐 Espace Sciences")
    st.info("Veuillez entrer votre code d'accès élève.")
    st.text_input("Code :", key="input_code", type="password", on_change=login)
    st.stop()

# --- 4. NAVIGATION ---
with st.sidebar:
    st.header(f"👤 {st.session_state.user_id}")
    st.divider()
    
    # Menus déroulants intelligents
    niveau = st.selectbox("1. Niveau :", list(PROGRAMME.keys()))
    
    parties_dispo = list(PROGRAMME[niveau].keys())
    partie = st.selectbox("2. Partie :", parties_dispo)
    
    lecons_dispo = PROGRAMME[niveau][partie]
    lecon = st.selectbox("3. Leçon :", lecons_dispo)
    
    mode = st.radio("4. Mode :", ["🎓 Professeur", "🏋️ Coach"])
    
    # Vérification fichier
    chemin_fichier = os.path.join("contenu", niveau, partie, lecon)
    if os.path.exists(chemin_fichier):
        st.caption("✅ Support de cours actif")
    else:
        st.caption("⚠️ Support en cours de création")

    st.divider()
    if st.button("Déconnexion"):
        st.session_state.auth = False
        st.rerun()

# --- 5. INTELLIGENCE ARTIFICIELLE ---
if mode == "🎓 Professeur":
    ROLE = "Tu es un Professeur de Physique-Chimie pédagogue."
    TON = "Calme, détaillé, explicatif."
else:
    ROLE = "Tu es un Coach d'examen exigeant."
    TON = "Direct, pose des questions, vérifie les acquis."

SYSTEM_PROMPT = f"""
{ROLE}
TON : {TON}
SUJET : Niveau {niveau}, Partie {partie}, Leçon : {lecon}.
RÈGLES :
1. Tu es expert en Physique-Chimie (Programme Marocain).
2. Refuse tout sujet hors-programme (SVT, Philo...).
3. Pour les graphiques, génère le code Python Matplotlib sans l'afficher.
"""

# --- 6. CHAT ---
st.title(lecon.replace(".pdf", "").replace("_", " "))
st.subheader(f"{partie.replace('_', ' ')}")

# Historique
if "messages" not in st.session_state: st.session_state.messages = []
if "current_lecon" not in st.session_state: st.session_state.current_lecon = lecon

if st.session_state.current_lecon != lecon:
    st.session_state.messages = []
    st.session_state.current_lecon = lecon
    st.toast("Nouveau cours chargé !")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display_text"])
        if "figure_code" in msg:
            try:
                exec(msg["figure_code"], {"plt": plt, "np": np, "st": st})
                st.pyplot(plt.gcf())
                plt.close()
            except: pass

prompt = st.chat_input("Pose ta question...")

if prompt:
    st.session_state.messages.append({"role": "user", "display_text": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("..."):
            try:
                # CORRECTION ICI : On utilise "gemini-1.5-flash" tout court
                model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)
                
                response = model.generate_content(prompt)
                text = response.text
                
                code = None
                if "```python" in text:
                    parts = text.split("```python")
                    code = parts[1].split("```")[0]
                    text = parts[0] + parts[1].split("```")[1]

                st.markdown(text)
                if code:
                    try:
                        exec(code, {"plt": plt, "np": np, "st": st})
                        st.pyplot(plt.gcf())
                        plt.close()
                    except: pass

                st.session_state.messages.append({"role": "assistant", "display_text": text, "figure_code": code})
                
                try:
                    tts = gTTS(text.replace("*",""), lang='fr')
                    bio = io.BytesIO()
                    tts.write_to_fp(bio)
                    st.audio(bio, format='audio/mp3')
                except: pass

            except Exception as e:
                st.error(f"Erreur : {e}")
