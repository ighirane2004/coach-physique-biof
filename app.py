import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from gtts import gTTS
import io
import os
import re

# --- 1. CONFIGURATION & SÉCURITÉ ---
# C'est la ligne magique pour le Cloud.
# Elle va chercher la clé dans les "Secrets" du serveur, pas dans le code.
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # Ce message s'affichera si vous lancez l'app sans configurer le coffre-fort
    st.warning("⚠️ Clé API introuvable. Si vous êtes sur votre PC, c'est normal.")
    st.stop()

# Configuration des fichiers
FICHIER_COURS = "cours_reference.pdf"  # Votre fichier PDF
DOSSIER_SCHEMAS = "schemas"            # Votre dossier d'images

st.set_page_config(page_title="Tuteur Physique BIOF", page_icon="⚛️", layout="centered")

# --- 2. FONCTIONS UTILITAIRES ---

@st.cache_resource
def load_knowledge_base():
    # Vérifie juste si le fichier est présent
    if os.path.exists(FICHIER_COURS):
        return True
    return False

def get_available_images():
    # Scanne le dossier schemas pour lister les images disponibles
    if not os.path.exists(DOSSIER_SCHEMAS):
        return []
    return [f for f in os.listdir(DOSSIER_SCHEMAS) if f.endswith(('.png', '.jpg', '.jpeg'))]

# --- 3. MOT DE PASSE (Accès Élève/Prof) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Accès Restreint BIOF")
    mdp = st.text_input("Entrez le code d'accès :", type="password")
    if mdp == "BAC2026":
        st.session_state.authenticated = True
        st.rerun()
    elif mdp:
        st.error("Code incorrect.")
    st.stop()

# --- 4. LE CERVEAU (VOS INSTRUCTIONS) ---
client = genai.Client(api_key=API_KEY)

# On prépare la liste des images pour le prompt
liste_images = get_available_images()
txt_liste_images = ", ".join(liste_images)

USER_PROMPT = """
# MISSION ET PERSONA
Tu es un tuteur expert en Physique-Chimie pour le niveau Deuxième Bac (Maroc, Option Français). Ton objectif est d'aider les élèves à maîtriser la modulation et la démodulation d'amplitude en utilisant la méthode du "Guided Learning" (apprentissage guidé).

# RÈGLES D'OR DU GUIDED LEARNING
1. NE DONNE JAMAIS LA SOLUTION COMPLÈTE d'un exercice immédiatement.
2. Pose UNE SEULE question à la fois pour guider l'élève.
3. Si l'élève bloque, donne un indice conceptuel ou une formule, mais pas le résultat numérique.
4. Félicite l'élève lorsqu'il valide une étape avant de passer à la suivante.

# ANALYSE VISUELLE (COURBES ET MONTAGES) - PRIORITÉ CRITIQUE
Tu dois accorder une importance prioritaire aux documents visuels fournis par l'élève (photos d'exercices, schémas, oscillogrammes) :
- Analyse systématique des axes : Si une courbe est fournie, identifie les échelles (V/div et ms/div).
- Analyse des signaux : Sur un signal modulé, aide l'élève à mesurer graphiquement Smax et Smin pour calculer le taux de modulation m.
- Si l'élève t'envoie une image illisible, floue, ou qui n'est pas un exercice de physique-chimie, ne tente pas de répondre au hasard. Dis-lui poliment : 'Je n'arrive pas à lire ton image. Peux-tu reprendre une photo plus nette en t'assurant qu'il y a assez de lumière ?'.

# EXPERTISE MÉTIER : MODULATION D'AMPLITUDE
Guide l'élève spécifiquement sur ces points clés :
1. Modulation : Identification de la porteuse, du signal modulant et de U0.
2. Condition de bonne modulation : m < 1 et Fp >> Fs.
3. Démodulation : Détection d'enveloppe (diode + RC //) et filtrage (RC série).
4. Circuit Bouchon : Sélection de la station.

# TON ET LANGAGE
- Utilise le vocabulaire officiel (ex: "enveloppe", "taux de modulation").
- Sois encourageant, patient et pédagogique.
- Langue : STRICTEMENT le Français.
- Si l'élève parle une autre langue ou dialecte, rappelle-lui gentiment de parler français.

# GESTION DES FICHIERS DE CONNAISSANCES
- Utilise le PDF fourni comme référence intellectuelle (formules, définitions).
- Ne mentionne jamais explicitement "D'après le PDF...".

# GESTION TECHNIQUE DES IMAGES (Important)
Tu as accès à une bibliothèque d'images : {images_dispo}
SI ET SEULEMENT SI ton explication nécessite un de ces schémas pour être claire, ajoute à la fin de ta réponse ce code exact :
[[AFFICHER:nom_du_fichier.png]]
N'invente pas de nom de fichier.

# PROTOCOLE GRAPHIQUE PYTHON
Pour les courbes mathématiques (sinusoïdes, modulation théorique), ne cherche pas d'image. Explique par le texte ou propose un code Python si l'élève le demande explicitement.
""".format(images_dispo=txt_liste_images)

# --- 5. L'INTERFACE ---
st.title("⚛️ Coach Physique & Chimie")
st.caption("Pose ta question, dicte-la (micro clavier 🎙️) ou envoie une photo 📸.")

# Menu latéral (Infos techniques cachées)
with st.sidebar:
    st.header("État du système")
    pdf_ok = load_knowledge_base()
    if pdf_ok:
        st.success(f"📘 Cours chargé")
    else:
        st.warning("Aucun cours PDF détecté")
    st.info(f"🖼️ {len(liste_images)} schémas en stock")

# Zone Caméra / Upload
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        camera_input = st.camera_input("📸 Photo directe")
    with col2:
        upload_input = st.file_uploader("📂 Importer image", type=["jpg", "png", "jpeg"])

    # Priorité à la caméra
    user_image = None
    if camera_input:
        user_image = Image.open(camera_input)
    elif upload_input:
        user_image = Image.open(upload_input)

    if user_image:
        st.success("Image prête à l'analyse !")

# --- 6. LE CHAT ET L'IA ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage de l'historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "image_path" in msg and msg["image_path"]:
            st.image(msg["image_path"])

# Zone de saisie
if prompt := st.chat_input("Écris ou dicte ta question..."):
    
    # 1. AFFICHER MESSAGE ÉLÈVE
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        if user_image:
            st.image(user_image, width=200)

    # 2. PRÉPARER L'ENVOI À GOOGLE
    content_parts = [prompt]
    if user_image:
        content_parts.append(user_image)
    
    # Ajout du PDF (si présent)
    if pdf_ok:
        try:
            path_pdf = os.path.abspath(FICHIER_COURS)
            with open(path_pdf, "rb") as f:
                pdf_upload = client.files.upload(file=path_pdf)
                content_parts.append(types.Part.from_uri(file_uri=pdf_upload.uri, mime_type="application/pdf"))
        except Exception as e:
            print(f"Erreur PDF: {e}")

    # 3. GÉNÉRATION DE LA RÉPONSE
    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("Analyse en cours..."):
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=USER_PROMPT),
                    contents=content_parts
                )
                
                full_text = response.text
                image_to_show = None

                # Détection du tag [[AFFICHER:image.png]]
                match = re.search(r"\[\[AFFICHER:(.*?)\]\]", full_text)
                if match:
                    nom_img = match.group(1)
                    chemin_img = os.path.join(DOSSIER_SCHEMAS, nom_img)
                    if os.path.exists(chemin_img):
                        image_to_show = chemin_img
                        # On retire le tag du texte visible
                        full_text = full_text.replace(match.group(0), "")

                # Affichage Texte
                placeholder.markdown(full_text)
                
                # Affichage Image (Schéma)
                if image_to_show:
                    st.image(image_to_show, caption="Schéma d'aide")

                # 4. GÉNÉRATION VOCALE (Audio)
                try:
                    # Nettoyage pour la lecture (enlève les étoiles du gras et les dollars du LaTeX)
                    clean_text = full_text.replace("*", "").replace("$", "")
                    tts = gTTS(text=clean_text, lang='fr', slow=False)
                    audio_io = io.BytesIO()
                    tts.write_to_fp(audio_io)
                    st.audio(audio_io, format='audio/mp3')
                except Exception as e:
                    pass # Pas grave si le son échoue

                # Sauvegarde en mémoire
                msg_data = {"role": "assistant", "content": full_text}
                if image_to_show:
                    msg_data["image_path"] = image_to_show
                st.session_state.messages.append(msg_data)

            except Exception as e:
                st.error(f"Erreur de connexion : {e}")