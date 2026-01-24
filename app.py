import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from gtts import gTTS
import io
import os
import re
import matplotlib.pyplot as plt
import numpy as np

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.warning("⚠️ Clé API introuvable.")
    st.stop()

FICHIER_COURS = "cours_reference.pdf"
DOSSIER_SCHEMAS = "schémas"

st.set_page_config(page_title="Tuteur Physique BIOF", page_icon="⚛️")

# --- 2. FONCTIONS ---
@st.cache_resource
def load_knowledge_base():
    return os.path.exists(FICHIER_COURS)

def get_images():
    if not os.path.exists(DOSSIER_SCHEMAS): return []
    return [f for f in os.listdir(DOSSIER_SCHEMAS) if f.lower().endswith(('.png','.jpg'))]

def executer_code_python(code):
    try:
        local_vars = {}
        exec(code, {"plt": plt, "np": np, "st": st}, local_vars)
        st.pyplot(plt.gcf()) 
        plt.clf()
    except Exception as e:
        st.error(f"Erreur dans le tracé : {e}")

# --- 3. SÉCURITÉ ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 Accès Professeur")
    mdp = st.text_input("Mot de passe :", type="password")
    if mdp == "BAC2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- 4. IA & PROMPT ---
client = genai.Client(api_key=API_KEY)
liste_imgs = get_images()
txt_images = ", ".join(liste_imgs)

# --- ATTENTION : C'est ici que l'erreur se produisait ---
SYSTEM_PROMPT = """
Tu es un professeur de Physique-Chimie expert (Niveau Bac).

RÈGLES D'INTERACTION :
1. Pédagogie : Ne donne pas la réponse sèche. Guide l'élève.
2. Schémas : Si besoin, utilise [[AFFICHER:nom_image.png]] parmi : {images}.

MODE "TRACEUR DE COURBES" :
Si l'élève demande de tracer une courbe, génère un code Python entre ```python ... ```.
Utilise 'numpy' (np) et 'matplotlib.pyplot' (plt).
Exemple :
```python
t = np.linspace(0, 0.01, 500)
u = 5 * np.cos(2*np.pi*100*t)
plt.plot(t, u)
plt.title("Tension")
