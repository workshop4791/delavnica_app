
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import ezdxf
import io
import cv2
import numpy as np
from PIL import Image
import os

st.set_page_config(page_title="Moja Delavnica", page_icon="🛠️", layout="wide")

# Map za trajno shranjevanje vzorcev
MAPA_VZORCEV = "shranjeni_vzorci"
if not os.path.exists(MAPA_VZORCEV):
    os.makedirs(MAPA_VZORCEV)

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
    
    # Prepis kontur vzorca v DXF linije
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
        "plate_dims": "Dimenzije plošče",
        "width": "Širina plošče L1 (mm):",
        "height": "Višina / Krak L2 (mm):",
        "download_dxf": "💾 Prenesi pravi DXF za razrez",
        "sketch_title": "Fotografiraj ročno skico",
        "upload_sketch": "Naloži skico...",
        "pattern_title": "Vzorci in ograjni paneli",
        "pattern_info": "Naloži ali izberi vzorec za izrez na ploščo.",
        "panel_width": "Širina plošče (mm):",
        "panel_height": "Višina plošče (mm):"
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
        
        st.markdown("### 1. Dimenzije osnovne plošče")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_sirina = st.number_input(t["panel_width"], value=1000, step=50)
        with col_p2:
            p_visina = st.number_input(t["panel_height"], value=500, step=50)
            
        st.markdown("---")
        st.markdown("### 2. Izbor ali nalaganje vzorca")
        
        # Pridobivanje shranjenih vzorcev
        shranjene_datoteke = [f for f in os.listdir(MAPA_VZORCEV) if f.endswith(('.png', '.jpg', '.jpeg'))]
        
        izbira_vzorca = st.radio("Kako želiš izbrati vzorec?", ["Naloži novo sliko", "Izberi shranjen vzorec iz zbirke"])
        
        slika_objekt = None
        
        if izbira_vzorca == "Naloži novo sliko":
            slika_vzorca = st.file_uploader("Naloži sliko vzorca...", type=["jpg", "jpeg", "png"], key="vzorec_upload")
            if slika_vzorca:
                slika_objekt = Image.open(slika_vzorca).convert('RGB')
                
                # Možnost za shranjevanje v zbirko
                col_s1, col_s2 = st.columns([2, 1])
                with col_s1:
                    novo_ime = st.text_input("Ime vzorca za shranjevanje (npr. 'roža_v1'):", "")
                with col_s2:
                    st.write(" ")
                    st.write(" ")
                    if st.button("💾 Shrani v zbirko") and novo_ime:
                        pot_shranjevanja = os.path.join(MAPA_VZORCEV, f"{novo_ime}.png")
                        slika_objekt.save(pot_shranjevanja)
                        st.success(f"Vzorec '{novo_ime}' shranjen!")
                        st.rerun()
                    
        else:
            if shranjene_datoteke:
                col_z1, col_z2 = st.columns([3, 1])
                with col_z1:
                    izbran_fajl = st.selectbox("Izberi vzorec iz zbirke:", shranjene_datoteke)
                with col_z2:
                    st.write(" ")
                    st.write(" ")
                    if st.button("🗑️ Izbriši ta vzorec"):
                        pot_za_bris = os.path.join(MAPA_VZORCEV, izbran_fajl)
                        if os.path.exists(pot_za_bris):
                            os.remove(pot_za_bris)
                            st.warning(f"Vzorec '{izbran_fajl}' je bil izbrisan!")
                            st.rerun()
                
                if izbran_fajl:
                    pot = os.path.join(MAPA_VZORCEV, izbran_fajl)
                    slika_objekt = Image.open(pot).convert('RGB')
            else:
                st.info("V zbirki še nimaš shranjenih vzorcev. Najprej naloži novo sliko.")

        if slika_objekt is not None:
            st.markdown("---")
            st.markdown("### 3. Nastavitve velikosti, položaja in čiščenja vzorca")
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Dimenzije in položaj vzorca na plošči:**")
                v_sirina = st.number_input("Širina vzorca (mm)", value=float(p_sirina - 100), min_value=1.0, max_value=float(p_sirina), step=10.0)
                v_visina = st.number_input("Višina vzorca (mm)", value=float(p_visina - 100), min_value=1.0, max_value=float(p_visina), step=10.0)
                
                sredina_x = (p_sirina - v_sirina) / 2.0
                sredina_y = (p_visina - v_visina) / 2.0
                
                pos_x = st.number_input("Odmik vzorca od levega roba X (mm)", value=float(sredina_x), min_value=0.0, max_value=float(p_sirina - v_sirina), step=5.0)
                pos_y = st.number_input("Odmik vzorca od spodnjega roba Y (mm)", value=float(sredina_y), min_value=0.0, max_value=float(p_visina - v_visina), step=5.0)

            with c2:
                st.write("**Čiščenje nečistoč na sliki:**")
                thresh_val = st.slider("Občutljivost zaznavanja (Threshold)", 0, 255, 127)
                min_area = st.slider("Odstrani majhne smeti (Minimalna površina)", 10, 5000, 200)
                obrni_barve = st.checkbox("Obrni barve (Invertiraj vzorec)")

            # Pretvorba v sivinsko sliko
            img_np = np.array(slika_objekt)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            
            # Razločevanje ozadja in vzorca
            mode = cv2.THRESH_BINARY_INV if not obrni_barve else cv2.THRESH_BINARY
            _, thresh = cv2.threshold(gray, thresh_val, 255, mode)
            
            konture, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filtriranje in prilagoditev merilu/položaju
            h_img, w_img = gray.shape
            
            skalirane_konture = []
            for k in konture:
                if cv2.contourArea(k) >= min_area:
                    k_scaled = k.astype(np.float32)
                    k_scaled[:, 0, 0] = pos_x + (k_scaled[:, 0, 0] / w_img) * v_sirina
                    k_scaled[:, 0, 1] = pos_y + ((h_img - k_scaled[:, 0, 1]) / h_img) * v_visina
                    skalirane_konture.append(k_scaled)

            st.markdown("---")
            st.markdown("### 4. Povečan predogled izreza")
            
            # Povečan predogled
            fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
            
            # Zunanja plošča
            rect = patches.Rectangle((0, 0), p_sirina, p_visina, linewidth=2, edgecolor='black', facecolor='#f0f0f0')
            ax.add_patch(rect)
            
            # Risanje vzorca
            for kontura in skalirane_konture:
                pts = kontura.reshape(-1, 2)
                ax.plot(pts[:, 0], pts[:, 1], color='red', linewidth=1.2)
                
            ax.set_xlim(-50, p_sirina + 50)
            ax.set_ylim(-50, p_visina + 50)
            ax.set_xlabel("X (mm)")
            ax.set_ylabel("Y (mm)")
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.set_aspect('equal')
            
            st.pyplot(fig, use_container_width=True)
            
            # Prenos DXF
            dxf_vzorec = ustvari_dxf_z_vzorcem(p_sirina, p_visina, skalirane_konture)
            st.download_button(
                label="💾 Prenesi očiščen DXF z merami",
                data=dxf_vzorec,
                file_name=f"panel_{int(p_sirina)}x{int(p_visina)}mm.dxf",
                mime="application/dxf"
            )

elif modul == t["modules"][2]:
    st.header("🦌 " + t["modules"][2])
elif modul == t["modules"][3]:
    st.header("🔧 " + t["modules"][3])
