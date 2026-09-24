
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import ezdxf
import io
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="Moja Delavnica", page_icon="🛠️", layout="centered")

# --- Funkcija za generiranje DXF z vzorcem ---
def ustvari_dxf_z_vzorcem(sirina, visina, konture_vzorca=None):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    doc.layers.add(name="RAZREZ", color=7)
    doc.layers.add(name="VZOREC", color=1)

    # Zunanji rob plošče
    msp.add_lwpolyline(
        [(0, 0), (sirina, 0), (sirina, visina), (0, visina), (0, 0)],
        dxfattribs={'layer': 'RAZREZ'}
    )
    
    # Če imamo izrisane konture vzorca, jih pretvorimo v DXF linije
    if konture_vzorca is not None:
        for kontura in konture_vzorca:
            tacke = []
            for pt in kontura:
                tacke.append((float(pt[0][0]), float(pt[0][1])))
            if len(tacke) > 2:
                tacke.append(tacke[0]) # Zapri konturo
                msp.add_lwpolyline(tacke, dxfattribs={'layer': 'VZOREC'})
                
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue()

# --- Slovar prevodov ---
TEXTS = {
    "SLO": {
        "title": "🛠️ Moja Delavnica App",
        "nav_title": "Navigacija",
        "modules": ["Domača stran", "CAD / DXF Generator", "Lovske kamere & AI", "Tehnična diagnostika"],
        "home_success": "Sistem deluje in je pripravljen za uporabo!",
        "home_info": "Izberi modul v levem meniju za začetek dela.",
        "tabs": ["1. Hitri vnos & Piganje", "2. Ročna skica (AI)", "3. Vzorci & Paneli"],
        "sheet_params": "Parametri pločevine in krivljenja",
        "thickness": "Debelina pločevine t (mm):",
        "material": "Material:",
        "inner_radius": "Notranji radij krivljenja R (mm):",
        "bend_angle": "Kot upogiba (°):",
        "v_die_rec": "Priporočena V-matrica (8xt):",
        "plate_dims": "Dimenzije plošče",
        "width": "Širina plošče L1 (mm):",
        "height": "Višina / Krak L2 (mm):",
        "hole_diam": "Premer lukenj (mm):",
        "hole_offset": "Odmik lukenj od roba (mm):",
        "flat_length": "Dodatek za krivljenje / Razvita dolžina:",
        "download_dxf": "💾 Prenesi pravi DXF za razrez",
        "sketch_title": "Fotografiraj ročno skico",
        "sketch_info": "Posnemi ali naloži sliko skice z merami.",
        "upload_sketch": "Naloži skico...",
        "pattern_title": "Vzorci in ograjni paneli",
        "pattern_info": "Naloži sliko vzorca za vektorizacijo in izrez na ploščo.",
        "upload_pattern": "Naloži sliko vzorca...",
        "panel_width": "Širina panela (mm):",
        "panel_height": "Višina panela (mm):",
        "apply_pattern": "Združi vzorec in ploščo"
    }
}

st.sidebar.title("🌐 Language")
t = TEXTS["SLO"]

st.title(t["title"])
modul = st.sidebar.radio(t["nav_title"] + ":", t["modules"])

if modul == t["modules"][0]:
    st.success(t["home_success"])
    st.info(t["home_info"])

elif modul == t["modules"][1]:
    st.header("📐 " + t["modules"][1])
    zavihek1, zavihek2, zavihek3 = st.tabs(t["tabs"])
    
    with zavihek1:
        st.subheader(t["sheet_params"])
        debelina = st.number_input(t["thickness"], value=2.0, step=0.5)
        material = st.selectbox(t["material"], ["Jeklo (S235/S355)", "Inox", "Aluminij"])
        radij = st.number_input(t["inner_radius"], value=2.0, step=0.5)
        kot = st.number_input(t["bend_angle"], value=90, step=5)
        
        st.subheader(t["plate_dims"])
        sirina = st.number_input(t["width"], value=200, step=10)
        visina = st.number_input(t["height"], value=100, step=10)
        
        dxf_vsebina = ustvari_dxf_z_vzorcem(sirina, visina)
        st.download_button(label=t["download_dxf"], data=dxf_vsebina, file_name="plosca.dxf", mime="application/dxf")

    with zavihek2:
        st.subheader(t["sketch_title"])
        slika_skice = st.file_uploader(t["upload_sketch"], type=["jpg", "jpeg", "png"], key="skica")
        if slika_skice:
            st.image(slika_skice, caption="Naložena skica", use_container_width=True)

    with zavihek3:
        st.subheader(t["pattern_title"])
        st.write(t["pattern_info"])
        
        col1, col2 = st.columns(2)
        with col1:
            p_sirina = st.number_input(t["panel_width"], value=1000, step=50)
        with col2:
            p_visina = st.number_input(t["panel_height"], value=500, step=50)
            
        slika_vzorca = st.file_uploader(t["upload_pattern"], type=["jpg", "jpeg", "png"], key="vzorec")
        
        if slika_vzorca:
            # Pretvorba slike v numpy matriko za OpenCV processing
            img = Image.open(slika_vzorca).convert('RGB')
            img_np = np.array(img)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            
            # Pragovna detekcija (threshold)
            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            konture, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            # Prilagoditev dimenzij kontur na velikost panela
            h_img, w_img = gray.shape
            skalirane_konture = []
            for k in konture:
                k_scaled = k.astype(np.float32)
                k_scaled[:, 0, 0] = (k_scaled[:, 0, 0] / w_img) * p_sirina
                k_scaled[:, 0, 1] = ((h_img - k_scaled[:, 0, 1]) / h_img) * p_visina # Obrnjena Y os
                skalirane_konture.append(k_scaled)

            st.success("✅ Vzorec uspešno prepoznan in preračunan na dimenzije plošče!")
            
            # Prikaz predogleda
            fig, ax = plt.subplots(figsize=(6, 3))
            rect = patches.Rectangle((0, 0), p_sirina, p_visina, linewidth=2, edgecolor='black', facecolor='none')
            ax.add_patch(rect)
            
            for kontura in skalirane_konture:
                pts = kontura.reshape(-1, 2)
                ax.plot(pts[:, 0], pts[:, 1], color='red', linewidth=1)
                
            ax.set_xlim(-20, p_sirina + 20)
            ax.set_ylim(-20, p_visina + 20)
            ax.set_aspect('equal')
            st.pyplot(fig)
            
            # DXF prenos
            dxf_vzorec = ustvari_dxf_z_vzorcem(p_sirina, p_visina, skalirane_konture)
            st.download_button(
                label="💾 Prenesi DXF z integriranim vzorcem",
                data=dxf_vzorec,
                file_name=f"panel_z_vzorcem_{int(p_sirina)}x{int(p_visina)}mm.dxf",
                mime="application/dxf"
            )

elif modul == t["modules"][2]:
    st.header("🦌 " + t["modules"][2])
elif modul == t["modules"][3]:
    st.header("🔧 " + t["modules"][3])
