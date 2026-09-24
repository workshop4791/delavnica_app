
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

MAPA_VZORCEV = "shranjeni_vzorci"
if not os.path.exists(MAPA_VZORCEV):
    os.makedirs(MAPA_VZORCEV)

# --- Iniciacija seznama lukenj v stanju aplikacije (session_state) ---
if 'seznami_lukenj' not in st.session_state:
    st.session_state.seznami_lukenj = []

# --- Funkcija za generiranje DXF ---
def ustvari_dxf_z_vzorcem(sirina, visina, konture_vzorca=None, luknje=None):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    doc.layers.add(name="RAZREZ", color=7)
    doc.layers.add(name="VZOREC", color=1)
    doc.layers.add(name="LUKNJE", color=3)

    # Zunanji rob plošče
    msp.add_lwpolyline(
        [(0, 0), (sirina, 0), (sirina, visina), (0, visina), (0, 0)],
        dxfattribs={'layer': 'RAZREZ'}
    )
    
    # Prepis vzorca
    if konture_vzorca is not None:
        for kontura in konture_vzorca:
            tacke = []
            for pt in kontura:
                tacke.append((float(pt[0][0]), float(pt[0][1])))
            if len(tacke) > 2:
                tacke.append(tacke[0])
                msp.add_lwpolyline(tacke, dxfattribs={'layer': 'VZOREC'})
                
    # Prepis ročno dodanih lukenj
    if luknje:
        for l in luknje:
            if l['tip'] == 'Okrogla':
                msp.add_circle((l['x'], l['y']), l['r'], dxfattribs={'layer': 'LUKNJE'})
            elif l['tip'] == 'Štirikotna':
                w, h = l['w'], l['h']
                x, y = l['x'] - w/2, l['y'] - h/2
                msp.add_lwpolyline([(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)], dxfattribs={'layer': 'LUKNJE'})
            elif l['tip'] == 'Ovalna (utor)':
                w, h = l['w'], l['h']
                # Poenostavljen izris utora kot pravokotnik z radiji ali elipsa
                msp.add_ellipse((l['x'], l['y']), major_axis=(w/2, 0), ratio=h/w, dxfattribs={'layer': 'LUKNJE'})

    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue()

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
        "sketch_title": "Fotografiraj ali naloži ročno skico",
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
            col_s1, col_s2 = st.columns([1, 1])
            with col_s1:
                st.image(slika_skice, caption="Naložena ročna skica", use_container_width=True)
            
            with col_s2:
                st.markdown("### ⚙️ Osnovne mere plošče")
                skica_sirina = st.number_input("Širina plošče L1 (mm)", value=1500, step=50, key="skica_w")
                skica_visina = st.number_input("Višina plošče L2 (mm)", value=1000, step=50, key="skica_h")
                
                # Avtomatske vogalne luknje
                if st.checkbox("Dodaj 4 vogalne luknje", value=False):
                    if st.button("Generiraj 4 vogalne luknje"):
                        st.session_state.seznami_lukenj = [
                            {'tip': 'Okrogla', 'x': 30, 'y': 30, 'r': 5},
                            {'tip': 'Okrogla', 'x': skica_sirina - 30, 'y': 30, 'r': 5},
                            {'tip': 'Okrogla', 'x': 30, 'y': skica_visina - 30, 'r': 5},
                            {'tip': 'Okrogla', 'x': skica_sirina - 30, 'y': skica_visina - 30, 'r': 5}
                        ]
                        st.rerun()

            st.markdown("---")
            st.markdown("### ➕ Ročno dodajanje in urejanje lukenj / izrezov")
            
            c_l1, c_l2, c_l3 = st.columns([2, 2, 1])
            with c_l1:
                tip_l = st.selectbox("Tip izreza:", ["Okrogla", "Štirikotna", "Ovalna (utor)"])
                pos_x_l = st.number_input("X pozicija (mm od leve)", value=float(skica_sirina/2), step=10.0)
                pos_y_l = st.number_input("Y pozicija (mm od spodaj)", value=float(skica_visina/2), step=10.0)
            
            with c_l2:
                if tip_l == "Okrogla":
                    premer_l = st.number_input("Premer ø (mm)", value=20.0, step=2.0)
                    r_l = premer_l / 2.0
                    w_l, h_l = premer_l, premer_l
                else:
                    w_l = st.number_input("Širina izreza (mm)", value=50.0, step=5.0)
                    h_l = st.number_input("Višina izreza (mm)", value=30.0, step=5.0)
                    r_l = min(w_l, h_l) / 2.0
            
            with c_l3:
                st.write(" ")
                st.write(" ")
                if st.button("➕ Dodaj luknjo"):
                    st.session_state.seznami_lukenj.append({
                        'tip': tip_l, 'x': pos_x_l, 'y': pos_y_l, 'r': r_l, 'w': w_l, 'h': h_l
                    })
                    st.rerun()

            # Prikaz in brisanje obstoječih lukenj
            if st.session_state.seznami_lukenj:
                st.write("**Seznam obstoječih lukenj:**")
                for idx, l in enumerate(st.session_state.seznami_lukenj):
                    col_b1, col_b2 = st.columns([4, 1])
                    with col_b1:
                        st.caption(f"{idx+1}. {l['tip']} | X: {l['x']}mm, Y: {l['y']}mm")
                    with col_b2:
                        if st.button(f"🗑️ Izbriši #{idx+1}", key=f"del_{idx}"):
                            st.session_state.seznami_lukenj.pop(idx)
                            st.rerun()

            st.markdown("---")
            dodaj_vzorec = st.checkbox("✨ Uredi ali dodaj vzorec", value=True)
            
            skalirane_konture_skica = None
            if dodaj_vzorec:
                st.markdown("### 🎨 Natančne nastavitve vzorca")
                shranjene_datoteke = [f for f in os.listdir(MAPA_VZORCEV) if f.endswith(('.png', '.jpg', '.jpeg'))]
                izbira_vzorca = st.radio("Vir vzorca:", ["Izberi shranjen vzorec iz zbirke", "Naloži novo sliko"], key="radio_skica")
                
                slika_objekt_skica = None
                if izbira_vzorca == "Izberi shranjen vzorec iz zbirke":
                    if shranjene_datoteke:
                        izbran_fajl = st.selectbox("Izberi vzorec:", shranjene_datoteke, key="sel_skica")
                        slika_objekt_skica = Image.open(os.path.join(MAPA_VZORCEV, izbran_fajl)).convert('RGB')
                else:
                    slika_v = st.file_uploader("Naloži sliko vzorca...", type=["jpg", "jpeg", "png"], key="up_skica")
                    if slika_v:
                        slika_objekt_skica = Image.open(slika_v).convert('RGB')

                if slika_objekt_skica is not None:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**Dimenzije in odmiki vzorca:**")
                        v_sirina = st.number_input("Širina vzorca (mm)", value=float(skica_sirina - 200), min_value=1.0, max_value=float(skica_sirina), step=10.0, key="sw")
                        v_visina = st.number_input("Višina vzorca (mm)", value=float(skica_visina - 200), min_value=1.0, max_value=float(skica_visina), step=10.0, key="sh")
                        pos_x = st.number_input("Odmik X od levega roba (mm)", value=float((skica_sirina - v_sirina)/2), min_value=0.0, max_value=float(skica_sirina - v_sirina), step=5.0, key="sx")
                        pos_y = st.number_input("Odmik Y od spodnjega roba (mm)", value=float((skica_visina - v_visina)/2), min_value=0.0, max_value=float(skica_visina - v_visina), step=5.0, key="sy")
                    with c2:
                        st.write("**Čiščenje slike vzorca:**")
                        thresh_val = st.slider("Threshold (Občutljivost)", 0, 255, 127, key="sthr")
                        min_area = st.slider("Odstrani smeti (Minimalna površina)", 10, 5000, 200, key="smin")
                        obrni_barve = st.checkbox("Invertiraj barve vzorca", key="sinv")

                    img_np = np.array(slika_objekt_skica)
                    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                    mode = cv2.THRESH_BINARY_INV if not obrni_barve else cv2.THRESH_BINARY
                    _, thresh = cv2.threshold(gray, thresh_val, 255, mode)
                    konture, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                    
                    h_img, w_img = gray.shape
                    skalirane_konture_skica = []
                    for k in konture:
                        if cv2.contourArea(k) >= min_area:
                            k_scaled = k.astype(np.float32)
                            k_scaled[:, 0, 0] = pos_x + (k_scaled[:, 0, 0] / w_img) * v_sirina
                            k_scaled[:, 0, 1] = pos_y + ((h_img - k_scaled[:, 0, 1]) / h_img) * v_visina
                            skalirane_konture_skica.append(k_scaled)

            st.markdown("---")
            st.markdown("### 📐 CAD Predogled v realnem času")
            
            fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
            rect = patches.Rectangle((0, 0), skica_sirina, skica_visina, linewidth=2, edgecolor='black', facecolor='#e6f2ff')
            ax.add_patch(rect)
            
            # Izris ročnih lukenj
            for l in st.session_state.seznami_lukenj:
                if l['tip'] == 'Okrogla':
                    patch = patches.Circle((l['x'], l['y']), l['r'], edgecolor='green', facecolor='white', linewidth=1.5)
                elif l['tip'] == 'Štirikotna':
                    patch = patches.Rectangle((l['x'] - l['w']/2, l['y'] - l['h']/2), l['w'], l['h'], edgecolor='green', facecolor='white', linewidth=1.5)
                elif l['tip'] == 'Ovalna (utor)':
                    patch = patches.Ellipse((l['x'], l['y']), l['w'], l['h'], edgecolor='green', facecolor='white', linewidth=1.5)
                ax.add_patch(patch)
            
            # Izris vzorca
            if skalirane_konture_skica is not None:
                for kontura in skalirane_konture_skica:
                    pts = kontura.reshape(-1, 2)
                    ax.plot(pts[:, 0], pts[:, 1], color='red', linewidth=1.2)
            
            # Kotirne črte
            ax.annotate('', xy=(0, -30), xytext=(skica_sirina, -30), arrowprops=dict(arrowstyle='<->', color='blue', lw=1.5))
            ax.text(skica_sirina / 2, -70, f"{int(skica_sirina)} mm", ha='center', color='blue', fontsize=12, fontweight='bold')
            
            ax.annotate('', xy=(-30, 0), xytext=(-30, skica_visina), arrowprops=dict(arrowstyle='<->', color='blue', lw=1.5))
            ax.text(-70, skica_visina / 2, f"{int(skica_visina)} mm", va='center', rotation='vertical', color='blue', fontsize=12, fontweight='bold')
            
            ax.set_xlim(-150, skica_sirina + 100)
            ax.set_ylim(-150, skica_visina + 100)
            ax.set_xlabel("X (mm)")
            ax.set_ylabel("Y (mm)")
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.set_aspect('equal')
            
            st.pyplot(fig, use_container_width=True)
            
            # DXF Izvoz
            dxf_skica = ustvari_dxf_z_vzorcem(skica_sirina, skica_visina, skalirane_konture_skica, st.session_state.seznami_lukenj)
            st.download_button(
                label=f"💾 Prenesi končni DXF za razrez ({int(skica_sirina)}x{int(skica_visina)} mm)",
                data=dxf_skica,
                file_name=f"razrez_{int(skica_sirina)}x{int(skica_visina)}mm.dxf",
                mime="application/dxf"
            )

elif modul == t["modules"][2]:
    st.header("🦌 " + t["modules"][2])
elif modul == t["modules"][3]:
    st.header("🔧 " + t["modules"][3])
