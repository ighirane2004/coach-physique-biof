import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from gtts import gTTS
import io
import os
import re

# --- 1. CONFIGURATION & SÉCURITÉ ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.warning("⚠️ Clé API introuvable. Configurez les Secrets.")
    st.stop()

# CORRECTION 1 : Le nom exact du dossier avec l'accent
FICHIER_COURS = "cours_reference.pdf"
DOSSIER_SCHEMAS = "schémas"  # <-- Mis à jour avec l'accent

st.set_page_config(page_title="Tuteur Physique BIOF", page_icon="⚛️", layout="centered")

# --- 2. FONCTIONS ---
@st.cache_resource
def load_knowledge_base():
    if os.path.exists(FICHIER_COURS):
        return True
    return False

def get_available_images():
    if not os.path.exists(DOSSIER_SCHEMAS):
        return []
    # On accepte jpg, png, jpeg et on ignore la casse (Majuscule/minuscule)
    return [f for f in os.listdir(DOSSIER_SCHEMAS) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

# --- 3. SÉCURITÉ ---
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

# --- 4. CONFIGURATION IA ---
client = genai.Client(api_key=API_KEY)
liste_images = get_available_images()
txt_liste_images = ", ".join(liste_images)

SYSTEM_PROMPT = """
Tu es un tuteur expert en Physique-Chimie (2ème Bac Maroc).
MÉTHODE PÉDAGOGIQUE :
1. Ne donne JAMAIS la solution directe.
2. Pose UNE SEULE question à la fois et attends la réponse de l'élève.
3. Si l'élève répond juste, félicite-le et passe à l'étape suivante.
4. Si l'élève répond faux, donne un indice.

GESTION DES SCHÉMAS :
Tu as ces images en stock : {images}
Si un schéma aide à comprendre, ajoute ce code à la fin : [[AFFICHER:nom_du_fichier.png]]
""".format(images=txt_liste_images)

# --- 5. INTERFACE ---
st.title("⚛️ Coach Physique & Chimie")

# Sidebar
with st.sidebar:
    st.header("État du système")
    pdf_ok = load_knowledge_base()
    if pdf_ok:
        st.success("📘 Cours chargé")
    
    # Debug pour voir si le dossier est trouvé
    if os.path.exists(DOSSIER_SCHEMAS):
        st.info(f"📂 Dossier '{DOSSIER_SCHEMAS}' trouvé")
        st.caption(f"🖼️ {len(liste_images)} images dispo")
    else:
        st.error(f"❌ Dossier '{DOSSIER_SCHEMAS}' introuvable")

# Zone d'entrée
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        camera_input = st.camera_input("📸 Photo")
    with col2:
        upload_input = st.file_uploader("📂 Image", type=["jpg", "png", "jpeg"])

    user_image = None
    if camera_input: user_image = Image.open(camera_input)
    elif upload_input: user_image = Image.open(upload_input)

# --- 6. CHAT ET MÉMOIRE (CORRECTION IMPORTANTE) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Afficher l'historique
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "image_path" in msg:
            st.image(msg["image_path"])

if prompt := st.chat_input("Ta réponse ou question..."):
    
    # 1. Sauvegarder message élève
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        if user_image:
            st.image(user_image, width=200)

    # 2. CONSTRUIRE LA MÉMOIRE POUR L'IA
    contents_for_api = []
    
    # A. Ajouter le PDF au début (Context)
    if pdf_ok:
        try:
            path_pdf = os.path.abspath(FICHIER_COURS)
            pdf_upload = client.files.upload(file=path_pdf)
            contents_for_api.append(types.Content(
                role="user", 
                parts=[types.Part.from_uri(file_uri=pdf_upload.uri, mime_type="application/pdf")]
            ))
        except: pass

    # B. Ajouter l'historique de la conversation (Texte uniquement pour économiser)
    # On prend tous les messages SAUF le dernier (qui est le prompt actuel)
    for msg in st.session_state.messages[:-1]:
        role_api = "model" if msg["role"] == "assistant" else "user"
        contents_for_api.append(types.Content(
            role=role_api,
            parts=[types.Part.from_text(text=msg["content"])]
        ))
    
    # C. Ajouter le message ACTUEL (Texte + Image si présente)
    current_parts = [types.Part.from_text(text=prompt)]
    if user_image:
        current_parts.append(types.Part.from_image(image=user_image))
    
    contents_for_api.append(types.Content(role="user", parts=current_parts))

    # 3. GÉNÉRATION
    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("Réflexion..."):
            try:
                # On envoie TOUTE la mémoire (contents_for_api)
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                    contents=contents_for_api
                )
                
                full_text = response.text
                
                # Gestion Schémas [[AFFICHER:...]]
                image_to_show = None
                match = re.search(r"\[\[AFFICHER:(.*?)\]\]", full_text)
                if match:
                    nom_img = match.group(1).strip()
                    chemin_img = os.path.join(DOSSIER_SCHEMAS, nom_img)
                    if os.path.exists(chemin_img):
                        image_to_show = chemin_img
                        full_text = full_text.replace(match.group(0), "") # Enlever le tag

                placeholder.markdown(full_text)
                if image_to_show:
                    st.image(image_to_show)

                # Audio
                try:
                    clean_text = full_text.replace("*", "")
                    tts = gTTS(text=clean_text, lang='fr')
                    audio_io = io.BytesIO()
                    tts.write_to_fp(audio_io)
                    st.audio(audio_io, format='audio/mp3')
                except: pass

                # Sauvegarde réponse
                msg_data = {"role": "assistant", "content": full_text}
                if image_to_show: msg_data["image_path"] = image_to_show
                st.session_state.messages.append(msg_data)

            except Exception as e:
                st.error(f"Erreur : {e}")
