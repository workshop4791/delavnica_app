
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import ezdxf
import io
import cv2
from PIL import Image
import os
import math

st.set_page_config(page_title="Moja Delavnica", page_icon="🛠️", layout="wide")

MAPA_VZORCEV = "shranjeni_vzorci"
if not os.path.exists(MAPA_VZORCEV):
    os.makedirs(MAPA_VZORCEV)

# --- Iniciacija seznama lukenj ---
if 'seznami_lukenj' not in st.session_state:
    st.session_state.seznami_lukenj = []

# --- Pomožna funkcija za oglišča N-kotnika ---
def get_polygon_vertices(cx, cy, r, n_sides, angle_deg=0):
    vertices = []
    angle_rad = math.radians(angle_deg)
    for i in range(n_sides):
        a = angle_rad + i * (2 * math.pi / n_sides)
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        vertices.append((x, y))
    return vertices

# --- Funkcija za generiranje DXF ---
def ustvari_dxf(oblika, params, kontura_skice_plosce=None, konture_vzorca=None, luknje=None):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    doc.layers.add(name="RAZREZ", color=7)
    doc.layers.add(name="VZOREC", color=1)
    doc.layers.add(name="LUKNJE", color=3)

    # 1. Zunanji rob plošče
    if oblika == "Pravokotna":
        w, h = params['w'], params['h']
        msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (0, h), (0, 0)], dxfattribs={'layer': 'RAZREZ'})
    elif oblika == "Okrogla":
        d = params['d']
        msp.add_circle((d/2, d/2), d/2, dxfattribs={'layer': 'RAZREZ'})
    elif oblika == "Trapezasta":
        w1, w2, h, x_offset = params['w1'], params['w2'], params['h'], params['x_offset']
        tacke_trapez = [(0, 0), (w1, 0), (x_offset + w2, h), (x_offset, h), (0, 0)]
        msp.add_lwpolyline(tacke_trapez, dxfattribs={'layer': 'RAZREZ'})
    elif oblika == "Stopniščna (pod kotom)":
        w, h, kot = params['w'], params['h'], params['kot']
        dx = h * math.tan(math.radians(kot))
        tacke_stopnic = [(0, 0), (w, 0), (w + dx, h), (dx, h), (0, 0)]
        msp.add_lwpolyline(tacke_stopnic, dxfattribs={'layer': 'RAZREZ'})
    elif oblika == "Skica s papirja (Slikaj ali Naloži)" and kontura_skice_plosce is not None:
        tacke = []
        for pt in kontura_skice_plosce:
            tacke.append((float(pt[0][0]), float(pt[0][1])))
        if len(tacke) > 2:
            tacke.append(tacke[0])
            msp.add_lwpolyline(tacke, dxfattribs={'layer': 'RAZREZ'})

    # 2. Vzorec
    if konture_vzorca is not None:
        for kontura in konture_vzorca:
            tacke = []
            for pt in kontura:
                tacke.append((float(pt[0][0]), float(pt[0][1])))
            if len(tacke) > 2:
                tacke.append(tacke[0])
                msp.add_lwpolyline(tacke, dxfattribs={'layer': 'VZOREC'})
                
    # 3. Ročne luknje
    if luknje:
        for l in luknje:
            tip = l['tip']
            x, y = l['x'], l['y']
            kot = l.get('kot', 0)
            
            if tip == 'Okrogla':
                msp.add_circle((x, y), l['r'], dxfattribs={'layer': 'LUKNJE'})
            elif tip == 'Štirikotna':
                w_l, h_l = l['w'], l['h']
                rad = math.radians(kot)
                hw, hh = w_l / 2.0, h_l / 2.0
                pts = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
                rot_pts = [
                    (x + px * math.cos(rad) - py * math.sin(rad),
                     y + px * math.sin(rad) + py * math.cos(rad))
                    for px, py in pts
                ]
                rot_pts.append(rot_pts[0])
                msp.add_lwpolyline(rot_pts, dxfattribs={'layer': 'LUKNJE'})
            elif tip == 'Ovalna (utor)':
                w_l, h_l = l['w'], l['h']
                msp.add_ellipse((x, y), major_axis=(w_l/2, 0), ratio=h_l/w_l, dxfattribs={'layer': 'LUKNJE'})
            elif tip in ['Trikotna', 'Šestkotna', 'Osemkotna', 'Poljuben N-kotnik']:
                n_stranic = l.get('n_stranic', 6)
                pts = get_polygon_vertices(x, y, l['r'], n_stranic, kot)
                pts.append(pts[0])
                msp.add_lwpolyline(pts, dxfattribs={'layer': 'LUKNJE'})

    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue()

# --- Main UI ---
st.title("🛠️ Moja Delavnica App - CAD Generator")

modul = st.sidebar.radio("Navigacija:", ["Domača stran", "CAD / DXF Generator", "Lovske kamere & AI", "Tehnična diagnostika"])

if modul == "Domača stran":
    st.success("Sistem deluje in je pripravljen za uporabo!")
    st.info("Izberi 'CAD / DXF Generator' v levem meniju za začetek dela z ploščami in skicami.")

elif modul == "CAD / DXF Generator":
    st.header("📐 Konstrukcija in razrez plošče")
    
    col_o1, col_o2 = st.columns([1, 2])
    
    kontura_skice_plosce = None
    mejna_sirina, mejna_visina = 1000.0, 1000.0
    
    with col_o1:
        st.subheader("1. Oblika in dimenzije plošče")
        oblika_plosce = st.selectbox("Izberi obliko plošče:", [
            "Pravokotna", 
            "Okrogla", 
            "Trapezasta", 
            "Stopniščna (pod kotom)",
            "Skica s papirja (Slikaj ali Naloži)"
        ])
        
        params = {}
        if oblika_plosce == "Pravokotna":
            params['w'] = st.number_input("Širina L1 (mm):", value=1500.0, step=50.0)
            params['h'] = st.number_input("Višina L2 (mm):", value=1000.0, step=50.0)
            mejna_sirina, mejna_visina = params['w'], params['h']
            
        elif oblika_plosce == "Okrogla":
            params['d'] = st.number_input("Premer plošče D (mm):", value=1000.0, step=50.0)
            mejna_sirina, mejna_visina = params['d'], params['d']
            
        elif oblika_plosce == "Trapezasta":
            params['w1'] = st.number_input("Spodnja širina W1 (mm):", value=1500.0, step=50.0)
            params['w2'] = st.number_input("Zgornja širina W2 (mm):", value=1000.0, step=50.0)
            params['h'] = st.number_input("Višina H (mm):", value=800.0, step=50.0)
            params['x_offset'] = st.number_input("Odmik zgornjega robova X (mm):", value=250.0, step=25.0)
            mejna_sirina = max(params['w1'], params['x_offset'] + params['w2'])
            mejna_visina = params['h']

        elif oblika_plosce == "Stopniščna (pod kotom)":
            params['w'] = st.number_input("Širina plošče W (mm):", value=1200.0, step=50.0)
            params['h'] = st.number_input("Višina plošče H (mm):", value=900.0, step=50.0)
            params['kot'] = st.slider("Kot naklona (° stopinje):", min_value=-60.0, max_value=60.0, value=35.0, step=0.5)
            dx = params['h'] * math.tan(math.radians(params['kot']))
            mejna_sirina = params['w'] + abs(dx)
            mejna_visina = params['h']

        elif oblika_plosce == "Skica s papirja (Slikaj ali Naloži)":
            st.info("👇 Kliknite spodaj za slikanje s kamero ali nalaganje fotke zunanje skice plošče:")
            
            fajl_plosce = st.file_uploader("📷 Slikaj / Naloži skico plošče...", type=["jpg", "jpeg", "png"], key="up_plosca")
            
            if fajl_plosce is not None:
                slika_plosce_obj = Image.open(fajl_plosce).convert('RGB')
                st.success("Slika plošče uspel naložena!")
                
                zaznana_w = st.number_input("Širina plošče v mm (kalibracija):", value=1000.0, step=50.0)
                zaznana_h = st.number_input("Višina plošče v mm (kalibracija):", value=800.0, step=50.0)
                mejna_sirina, mejna_visina = zaznana_w, zaznana_h
                
                thresh_p = st.slider("Občutljivost zaznavanja roba", 0, 255, 127)
                
                img_np = np.array(slika_plosce_obj)
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                _, thresh = cv2.threshold(gray, thresh_p, 255, cv2.THRESH_BINARY_INV)
                konture, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if konture:
                    najvecja = max(konture, key=cv2.contourArea)
                    h_img, w_img = gray.shape
                    k_scaled = najvecja.astype(np.float32)
                    k_scaled[:, 0, 0] = (k_scaled[:, 0, 0] / w_img) * zaznana_w
                    k_scaled[:, 0, 1] = ((h_img - k_scaled[:, 0, 1]) / h_img) * zaznana_h
                    kontura_skice_plosce = k_scaled

    with col_o2:
        st.subheader("2. Dodajanje in urejanje lukenj")
        c_l1, c_l2, c_l3 = st.columns([2, 2, 1])
        with c_l1:
            tip_l = st.selectbox("Tip izreza:", [
                "Okrogla", "Štirikotna", "Ovalna (utor)", 
                "Trikotna", "Šestkotna", "Osemkotna", "Poljuben N-kotnik"
            ])
            pos_x_l = st.number_input("X pozicija (mm)", value=float(mejna_sirina/2), step=10.0)
            pos_y_l = st.number_input("Y pozicija (mm)", value=float(mejna_visina/2), step=10.0)
            kot_rotacije = st.number_input("Kot rotacije (°)", value=0.0, step=5.0)
        
        with c_l2:
            n_stranic = 6
            if tip_l == "Okrogla":
                premer_l = st.number_input("Premer ø (mm)", value=20.0, step=2.0)
                r_l = premer_l / 2.0
                w_l, h_l = premer_l, premer_l
            elif tip_l in ["Štirikotna", "Ovalna (utor)"]:
                w_l = st.number_input("Širina izreza (mm)", value=50.0, step=5.0)
                h_l = st.number_input("Višina izreza (mm)", value=30.0, step=5.0)
                r_l = min(w_l, h_l) / 2.0
            else:
                if tip_l == "Trikotna": n_stranic = 3
                elif tip_l == "Šestkotna": n_stranic = 6
                elif tip_l == "Osemkotna": n_stranic = 8
                elif tip_l == "Poljuben N-kotnik":
                    n_stranic = st.number_input("Število oglišč N", min_value=3, max_value=20, value=5)
                
                r_l = st.number_input("Polmer R (mm)", value=25.0, step=2.5)
                w_l, h_l = r_l * 2, r_l * 2

        with c_l3:
            st.write(" ")
            st.write(" ")
            if st.button("➕ Dodaj luknjo"):
                st.session_state.seznami_lukenj.append({
                    'tip': tip_l, 'x': pos_x_l, 'y': pos_y_l, 
                    'r': r_l, 'w': w_l, 'h': h_l,
                    'kot': kot_rotacije, 'n_stranic': n_stranic
                })
                st.rerun()

        if st.session_state.seznami_lukenj:
            st.write("**Dodane luknje:**")
            col_clear, _ = st.columns([1, 3])
            with col_clear:
                if st.button("🗑️ Počisti vse luknje"):
                    st.session_state.seznami_lukenj = []
                    st.rerun()
                    
            for idx, l in enumerate(st.session_state.seznami_lukenj):
                col_b1, col_b2 = st.columns([4, 1])
                with col_b1:
                    st.caption(f"**#{idx+1}** | {l['tip']} | X: {l['x']}mm, Y: {l['y']}mm | Kot: {l.get('kot', 0)}°")
                with col_b2:
                    if st.button(f"🗑️ Briši #{idx+1}", key=f"del_{idx}"):
                        st.session_state.seznami_lukenj.pop(idx)
                        st.rerun()

    st.markdown("---")
    st.subheader("3. Dodajanje notranjega vzorca (opcijsko)")
    dodaj_vzorec = st.checkbox("Dodaj vzorec na površino plošče", value=False)
    
    skalirane_konture = None
    if dodaj_vzorec:
        shranjene_datoteke = [f for f in os.listdir(MAPA_VZORCEV) if f.endswith(('.png', '.jpg', '.jpeg'))]
        izbira_vzorca = st.radio("Vir vzorca:", ["📷 Slikaj / Naloži sliko", "💾 Izberi shranjeno"], key="vir_vzorca_option")
        
        slika_objekt = None
        if izbira_vzorca == "📷 Slikaj / Naloži sliko":
            slika_v = st.file_uploader("📷 Slikaj ali naloži sliko vzorca...", type=["jpg", "jpeg", "png"], key="upload_vzorec")
            if slika_v:
                slika_objekt = Image.open(slika_v).convert('RGB')
        elif izbira_vzorca == "💾 Izberi shranjeno" and shranjene_datoteke:
            izbran_fajl = st.selectbox("Izberi vzorec:", shranjene_datoteke)
            slika_objekt = Image.open(os.path.join(MAPA_VZORCEV, izbran_fajl)).convert('RGB')

        if slika_objekt is not None:
            c_v1, c_v2 = st.columns(2)
            with c_v1:
                v_sirina = st.number_input("Širina vzorca (mm)", value=float(mejna_sirina * 0.8), step=10.0)
                v_visina = st.number_input("Višina vzorca (mm)", value=float(mejna_visina * 0.8), step=10.0)
                pos_x = st.number_input("Odmik X (mm)", value=float((mejna_sirina - v_sirina)/2), step=5.0)
                pos_y = st.number_input("Odmik Y (mm)", value=float((mejna_visina - v_visina)/2), step=5.0)
            with c_v2:
                thresh_val = st.slider("Občutljivost vzorca", 0, 255, 127)
                min_area = st.slider("Min. površina", 10, 5000, 200)
                obrni_barve = st.checkbox("Invertiraj barve")

            img_np = np.array(slika_objekt)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            mode = cv2.THRESH_BINARY_INV if not obrni_barve else cv2.THRESH_BINARY
            _, thresh = cv2.threshold(gray, thresh_val, 255, mode)
            konture, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            h_img, w_img = gray.shape
            skalirane_konture = []
            for k in konture:
                if cv2.contourArea(k) >= min_area:
                    k_scaled = k.astype(np.float32)
                    k_scaled[:, 0, 0] = pos_x + (k_scaled[:, 0, 0] / w_img) * v_sirina
                    k_scaled[:, 0, 1] = pos_y + ((h_img - k_scaled[:, 0, 1]) / h_img) * v_visina
                    skalirane_konture.append(k_scaled)

    st.markdown("---")
    st.subheader("4. CAD Predogled v realnem času")
    
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    
    # Izris zunanjega roba plošče
    if oblika_plosce == "Pravokotna":
        zunanji_lik = patches.Rectangle((0, 0), params['w'], params['h'], linewidth=2, edgecolor='black', facecolor='#e6f2ff')
        ax.add_patch(zunanji_lik)
    elif oblika_plosce == "Okrogla":
        zunanji_lik = patches.Circle((params['d']/2, params['d']/2), params['d']/2, linewidth=2, edgecolor='black', facecolor='#e6f2ff')
        ax.add_patch(zunanji_lik)
    elif oblika_plosce == "Trapezasta":
        tacke = [[0, 0], [params['w1'], 0], [params['x_offset'] + params['w2'], params['h']], [params['x_offset'], params['h']]]
        zunanji_lik = patches.Polygon(tacke, closed=True, linewidth=2, edgecolor='black', facecolor='#e6f2ff')
        ax.add_patch(zunanji_lik)
    elif oblika_plosce == "Stopniščna (pod kotom)":
        dx = params['h'] * math.tan(math.radians(params['kot']))
        tacke = [[0, 0], [params['w'], 0], [params['w'] + dx, params['h']], [dx, params['h']]]
        zunanji_lik = patches.Polygon(tacke, closed=True, linewidth=2, edgecolor='black', facecolor='#e6f2ff')
        ax.add_patch(zunanji_lik)
    elif oblika_plosce == "Skica s papirja (Slikaj ali Naloži)" and kontura_skice_plosce is not None:
        pts = kontura_skice_plosce.reshape(-1, 2)
        ax.plot(pts[:, 0], pts[:, 1], color='black', linewidth=2)

    # Izris lukenj
    for idx, l in enumerate(st.session_state.seznami_lukenj):
        tip, x, y, kot = l['tip'], l['x'], l['y'], l.get('kot', 0)
        
        if tip == 'Okrogla':
            p = patches.Circle((x, y), l['r'], edgecolor='green', facecolor='white', linewidth=1.5)
            ax.add_patch(p)
        elif tip == 'Štirikotna':
            p = patches.Rectangle((x - l['w']/2, y - l['h']/2), l['w'], l['h'], edgecolor='green', facecolor='white', linewidth=1.5)
            p.set_transform(patches.transforms.Affine2D().rotate_deg_around(x, y, kot) + ax.transData)
            ax.add_patch(p)
        elif tip == 'Ovalna (utor)':
            p = patches.Ellipse((x, y), l['w'], l['h'], angle=kot, edgecolor='green', facecolor='white', linewidth=1.5)
            ax.add_patch(p)
        elif tip in ['Trikotna', 'Šestkotna', 'Osemkotna', 'Poljuben N-kotnik']:
            pts = get_polygon_vertices(x, y, l['r'], l.get('n_stranic', 6), kot)
            p = patches.Polygon(pts, closed=True, edgecolor='green', facecolor='white', linewidth=1.5)
            ax.add_patch(p)

        ax.text(x, y, f"#{idx+1}", color='blue', fontsize=10, fontweight='bold', ha='center', va='center')

    # Izris vzorca
    if skalirane_konture is not None:
        for kontura in skalirane_konture:
            pts = kontura.reshape(-1, 2)
            ax.plot(pts[:, 0], pts[:, 1], color='red', linewidth=1.2)

    ax.set_xlim(-100, mejna_sirina + 100)
    ax.set_ylim(-100, mejna_visina + 100)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.set_aspect('equal')
    
    st.pyplot(fig, use_container_width=True)

    # Izvoz DXF
    dxf_data = ustvari_dxf(oblika_plosce, params, kontura_skice_plosce, skalirane_konture, st.session_state.seznami_lukenj)
    st.download_button(
        label=f"💾 Prenesi DXF datoteko ({oblika_plosce})",
        data=dxf_data,
        file_name="plosca_skica.dxf",
        mime="application/dxf"
    )

elif modul == "Lovske kamere & AI":
    st.header("🦌 Modul za lovske kamere")
elif modul == "Tehnična diagnostika":
    st.header("🔧 Modul za diagnostiko")
