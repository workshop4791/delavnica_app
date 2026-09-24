
import streamlit as st
import google.generativeai as genai
from PIL import Image

# Nastavitev strani
st.set_page_config(page_title="Analizator Skic", layout="centered")

st.title("📐 Analizator Skic in Tlorisov z AI")
st.write("Naložite sliko ali skico tlorisa in pridobite AI analizo.")

# 1. Pridobivanje API ključa (najprej iz Streamlit Secrets, sicer preko vnosnega polja)
api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    api_key = st.sidebar.text_input("Vnesite Gemini API ključ:", type="password")

# 2. Nalaganje datoteke
uploaded_file = st.file_uploader("Izberite sliko ali skico (PNG, JPG, JPEG):", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Prikaz naložene slike
    image = Image.open(uploaded_file)
    st.image(image, caption="Naložena skica", use_column_width=True)

    # Gumb za analizo
    if st.button("🤖 Analiziraj skico z AI"):
        if not api_key:
            st.error("Prosimo, vnesite Gemini API ključ v stranski vrstici ali ga shranite v Streamlit Secrets!")
        else:
            try:
                with st.spinner("AI analizira vašo skico..."):
                    # Konfiguracija Gemini API
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')

                    # Poziv (prompt) za AI
                    prompt = (
                        "Analiziraj to skico ali tloris. "
                        "Prepoznaj prostore, dimenzije (če so razvidne) in predlagaj morebitne izboljšave ali opombe. "
                        "Odgovori v slovenskem jeziku, jasno in strukturno."
                    )

                    # Generiranje odgovora
                    response = model.generate_content([prompt, image])

                    st.success("Analiza je končana!")
                    st.markdown("### 📋 Rezultat analize:")
                    st.write(response.text)

            except Exception as e:
                st.error(f"Prišlo je do napake pri analizi: {e}")
