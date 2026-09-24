
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
import json
from google import genai

st.set_page_config(page_title="Moja Delavnica", page_icon="🛠️", layout="wide")

MAPA_VZORCEV = "shranjeni_vzorci"
if not os.path.exists(MAPA_VZORCEV):
    os.makedirs(MAPA_VZORCEV)

# --- Iniciacija stanja ---
if 'seznami_lukenj' not in st.session_state:
    st.session_state.seznami_lukenj = []

# --- AI Funkcija za prepoznavo skice (dimenzije in luknje) ---
def ai_analiza_skice_z_gemini(slika_pil, api_key):
    try:
        client = genai.Client(api_key=api_key)
        prompt = """
        Analiziraj to ročno narisano skico za laserski izrez plošče.
        Preberi vse dimenzije, napise in narisane luknje.
        
        Vrni IZKLJUČNO veljaven JSON v naslednjem formatu (brez dodatnega besedila ali markdowna):
        {
          "sirina_mm": 1500,
          "visina_mm": 1000,
          "luknje": [
            {
              "tip": "Okrogla",
              "premer_mm": 20,
              "x_mm": 150,
              "y_mm": 850
            }
          ]
        }
        Vse dimenzije pretvori v milimetre (mm). Če so v metrih (m), pomnoži s 1000.
        """
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[slika_pil, prompt]
            )
        except Exception:
            # Rezervni model, če primarni ni na voljo
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[slika_pil, prompt]
            )

        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Napaka pri AI analizi skice: {e}")
        return None

# --- AI Funkcija za segmentacijo vzorca ograje s terena ---
def ai_obdelava_vzorca_ograje(slika_pil, api_key):
    try:
        img_np = np.array(slika_pil.convert('L'))
        blurred = cv2.GaussianBlur(img_np, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        return thresh
    except Exception as e:
        st.error(f"Napaka pri obdelavi vzorca: {e}")
        return None

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

    if oblika in ["Pravokotna", "Skica s papirja (Slikaj z AI)"]:
        w, h = params.get('w', 1500), params.get('h', 1000)
        msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (0, h), (0, 0)], dxfattribs={'layer': 'RAZREZ'})
    elif oblika == "Okrogla":
        d = params.get('d', 1000)
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

    if konture_vzorca is not None:
        for kontura in konture_vzorca:
            tacke = [(float(pt[0][0]), float(pt[0][1])) for pt in kontura]
            if len(tacke) > 2:
                tacke.append(tacke[0])
                msp.add_lwpolyline(tacke, dxfattribs={'layer': 'VZOREC'})
                
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
st.title("🛠️ Moja Delavnica App - CAD & AI Generator")

st.sidebar.header("🔑 AI Nastavitve")
gemini_api_key = st.sidebar.text_input("Vnesite Gemini API ključ:", type="password")

modul = st.sidebar.radio("Navigacija:", ["Domača stran", "CAD / DXF Generator", "Lovske kamere & AI", "Tehnična diagnostika"])

if modul == "Domača stran":
    st.success("Sistem deluje in je pripravljen za uporabo!")

elif modul == "CAD / DXF Generator":
    st.header("📐 Konstrukcija in razrez plošče")
    
    col_o1, col_o2 = st.columns([1, 2])
    
    with col_o1:
        st.subheader("1. Oblika in dimenzije plošče")
        oblika_plosce = st.selectbox("Izberi obliko plošče:", [
            "Pravokotna", 
            "Okrogla", 
            "Trapezasta", 
            "Stopniščna (pod kotom)",
            "Skica s papirja (Slikaj z AI)"
        ])
        
        params = {}
        if oblika_plosce in ["Pravokotna", "Skica s papirja (Slikaj z AI)"]:
            default_w = st.session_state.get('sirina_ai', 1500.0)
            default_h = st.session_state.get('visina_ai', 1000.0)
            params['w'] = st.number_input("Širina (mm):", value=default_w, step=10.0)
            params['h'] = st.number_input("Višina (mm):", value=default_h, step=10.0)
            mejna_sirina, mejna_visina = params['w'], params['h']
            
            if oblika_plosce == "Skica s papirja (Slikaj z AI)":
                fajl_plosce = st.file_uploader("📷 Slikaj / Naloži skico...", type=["jpg", "jpeg", "png"])
                if fajl_plosce and gemini_api_key:
                    slika_obj = Image.open(fajl_plosce).convert('RGB')
                    if st.button("🤖 Analiziraj skico z AI"):
                        with st.spinner("AI analizira dimenzije in luknje..."):
                            rez = ai_analiza_skice_z_gemini(slika_obj, gemini_api_key)
                            if rez:
                                st.session_state.sirina_ai = float(rez.get('sirina_mm', 1500))
                                st.session_state.visina_ai = float(rez.get('visina_mm', 1000))
                                st.session_state.seznami_lukenj = []
                                for l in rez.get('luknje', []):
                                    st.session_state.seznami_lukenj.append({
                                        'tip': l.get('tip', 'Okrogla'),
                                        'x': float(l.get('x_mm', 100)),
                                        'y': float(l.get('y_mm', 100)),
                                        'r': float(l.get('premer_mm', 20)) / 2.0,
                                        'w': float(l.get('premer_mm', 20)),
                                        'h': float(l.get('premer_mm', 20)),
                                        'kot': 0, 'n_stranic': 6
                                    })
                                st.success("AI uspešno prebral skico!")
                                st.rerun()

        elif oblika_plosce == "Okrogla":
            params['d'] = st.number_input("Premer plošče D (mm):", value=1000.0, step=10.0)
            mejna_sirina, mejna_visina = params['d'], params['d']

    with col_o2:
        st.subheader("2. Dodajanje in urejanje lukenj")
        c_l1, c_l2, c_l3 = st.columns([2, 2, 1])
        with c_l1:
            tip_l = st.selectbox("Tip izreza:", ["Okrogla", "Štirikotna", "Ovalna (utor)"])
            pos_x_l = st.number_input("X pozicija (mm)", value=float(mejna_sirina/2), step=1.0)
            pos_y_l = st.number_input("Y pozicija (mm)", value=float(mejna_visina/2), step=1.0)
        with c_l2:
            premer_l = st.number_input("Velikost/Premer (mm)", value=20.0, step=1.0)
        with c_l3:
            st.write(" ")
            if st.button("➕ Dodaj"):
                st.session_state.seznami_lukenj.append({
                    'tip': tip_l, 'x': pos_x_l, 'y': pos_y_l, 
                    'r': premer_l/2, 'w': premer_l, 'h': premer_l, 'kot': 0
                })
                st.rerun()

    st.markdown("---")
    st.subheader("3. Dodajanje vzorca ograje s terena (AI Prepoznava)")
    dodaj_vzorec = st.checkbox("Dodaj vzorec ograje s terena", value=False)
    
    skalirane_konture = None
    if dodaj_vzorec:
        slika_v = st.file_uploader("📷 Slikaj ograjo na terenu...", type=["jpg", "jpeg", "png"], key="ograj_up")
        if slika_v:
            slika_ograj_obj = Image.open(slika_v).convert('RGB')
            
            c_v1, c_v2 = st.columns(2)
            with c_v1:
                v_sirina = st.number_input("Širina vzorca na plošči (mm)", value=float(mejna_sirina * 0.8), step=1.0)
                v_visina = st.number_input("Višina vzorca na plošči (mm)", value=float(mejna_visina * 0.8), step=1.0)
            with c_v2:
                thresh_val = st.slider("Prag zaznavanja linij ograje", 0, 255, 120)

            img_np = np.array(slika_ograj_obj)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blurred, thresh_val, 255, cv2.THRESH_BINARY_INV)
            
            konture, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            h_img, w_img = gray.shape
            skalirane_konture = []
            pos_x = (mejna_sirina - v_sirina) / 2
            pos_y = (mejna_visina - v_visina) / 2
            
            for k in konture:
                if cv2.contourArea(k) > 150:
                    k_scaled = k.astype(np.float32)
                    k_scaled[:, 0, 0] = pos_x + (k_scaled[:, 0, 0] / w_img) * v_sirina
                    k_scaled[:, 0, 1] = pos_y + ((h_img - k_scaled[:, 0, 1]) / h_img) * v_visina
                    skalirane_konture.append(k_scaled)

    st.markdown("---")
    st.subheader("4. CAD Predogled v realnem času")
    
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    
    # Izris plošče
    zunanji_lik = patches.Rectangle((0, 0), params.get('w', 1500), params.get('h', 1000), linewidth=2, edgecolor='black', facecolor='#e6f2ff')
    ax.add_patch(zunanji_lik)

    # Izris lukenj
    for idx, l in enumerate(st.session_state.seznami_lukenj):
        ax.add_patch(patches.Circle((l['x'], l['y']), l['r'], edgecolor='green', facecolor='white', linewidth=1.5))
        ax.text(l['x'], l['y'], f"#{idx+1}", color='blue', fontsize=10, fontweight='bold', ha='center', va='center')

    # Izris vzorca ograje
    if skalirane_konture is not None:
        for kontura in skalirane_konture:
            pts = kontura.reshape(-1, 2)
            ax.plot(pts[:, 0], pts[:, 1], color='red', linewidth=1)

    ax.set_xlim(-100, mejna_sirina + 100)
    ax.set_ylim(-100, mejna_visina + 100)
    ax.set_aspect('equal')
    st.pyplot(fig, use_container_width=True)

    # DXF Izvoz
    dxf_data = ustvari_dxf(oblika_plosce, params, None, skalirane_konture, st.session_state.seznami_lukenj)
    st.download_button("💾 Prenesi DXF datoteko za razrez", data=dxf_data, file_name="ogreja_razrez.dxf", mime="application/dxf")
