
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import ezdxf
import io

st.set_page_config(page_title="Moja Delavnica", page_icon="🛠️", layout="centered")

# --- Funkcija za generiranje prave DXF datoteke ---
def ustvari_dxf(sirina, visina, premer_luknje, odmik):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Dodajanje plasti (Layers) za CNC stroj
    doc.layers.add(name="RAZREZ", color=7)       # Bela/črna črta za zunanji rez
    doc.layers.add(name="LUKNJE", color=1)       # Rdeča za luknje
    doc.layers.add(name="KRIVLJENJE", color=5)   # Modra za linijo piganja (Bend line)

    # Zunanja kontura (pravokotnik)
    msp.add_lwpolyline(
        [(0, 0), (sirina, 0), (sirina, visina), (0, visina), (0, 0)],
        dxfattribs={'layer': 'RAZREZ'}
    )
    
    # Linija krivljenja na sredini
    msp.add_line((0, visina / 2), (sirina, visina / 2), dxfattribs={'layer': 'KRIVLJENJE'})
    
    # 4 luknje
    r = premer_luknje / 2
    luknje = [(odmik, odmik), (sirina - odmik, odmik), (odmik, visina - odmik), (sirina - odmik, visina - odmik)]
    for lx, ly in luknje:
        msp.add_circle((lx, ly), r, dxfattribs={'layer': 'LUKNJE'})
        
    # Shranjevanje v pomnilnik za prenos
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
        "sketch_info": "Posnemi ali naloži sliko skice z merami. AI bo samodejno prebral dimenzije.",
        "upload_sketch": "Naloži skico...",
        "pattern_title": "Vzorci in ograjni paneli",
        "pattern_info": "Naloži sliko vzorca za vektorizacijo in izrez.",
        "upload_pattern": "Naloži sliko vzorca...",
        "panel_width": "Širina panela (mm):",
        "panel_height": "Višina panela (mm):",
        "apply_pattern": "Prilagodi vzorec na panel"
    },
    "ENG": {
        "title": "🛠️ Mobile Workshop App",
        "nav_title": "Navigation",
        "modules": ["Home", "CAD / DXF Generator", "Trail Cameras & AI", "Technical Diagnostics"],
        "home_success": "System is running and ready for use!",
        "home_info": "Select a module in the left sidebar to start.",
        "tabs": ["1. Quick Input & Bending", "2. Hand Sketch (AI)", "3. Patterns & Panels"],
        "sheet_params": "Sheet Metal & Bending Parameters",
        "thickness": "Sheet Thickness t (mm):",
        "material": "Material:",
        "inner_radius": "Inner Bending Radius R (mm):",
        "bend_angle": "Bending Angle (°):",
        "v_die_rec": "Recommended V-Die Opening (8xt):",
        "plate_dims": "Plate Dimensions",
        "width": "Plate Width L1 (mm):",
        "height": "Height / Leg L2 (mm):",
        "hole_diam": "Hole Diameter (mm):",
        "hole_offset": "Hole Offset from Edge (mm):",
        "flat_length": "Calculated Flat Length:",
        "download_dxf": "💾 Download DXF File",
        "sketch_title": "Photograph Hand-drawn Sketch",
        "sketch_info": "Take a photo or upload a sketch with dimensions.",
        "upload_sketch": "Upload sketch...",
        "pattern_title": "Patterns & Panels",
        "pattern_info": "Upload a pattern image for laser cutting.",
        "upload_pattern": "Upload pattern...",
        "panel_width": "Panel Width (mm):",
        "panel_height": "Panel Height (mm):",
        "apply_pattern": "Fit Pattern"
    },
    "DEU": {
        "title": "🛠️ Werkstatt App",
        "nav_title": "Navigation",
        "modules": ["Startseite", "CAD / DXF Generator", "Wildkameras & KI", "Technische Diagnose"],
        "home_success": "Das System ist betriebsbereit!",
        "home_info": "Wählen Sie ein Modul aus.",
        "tabs": ["1. Schnelleingabe & Biegen", "2. Handskizze (KI)", "3. Muster & Zaunfelder"],
        "sheet_params": "Blech- & Biegeparameter",
        "thickness": "Blechdicke t (mm):",
        "material": "Material:",
        "inner_radius": "Biegeradius R (mm):",
        "bend_angle": "Biegewinkel (°):",
        "v_die_rec": "Empfohlene V-Matrize (8xt):",
        "plate_dims": "Plattenabmessungen",
        "width": "Plattenbreite L1 (mm):",
        "height": "Höhe / Schenkel L2 (mm):",
        "hole_diam": "Lochdurchmesser (mm):",
        "hole_offset": "Lochabstand vom Rand (mm):",
        "flat_length": "Berechnete gestreckte Länge:",
        "download_dxf": "💾 DXF Datei Herunterladen",
        "sketch_title": "Handskizze fotografieren",
        "sketch_info": "Fotografieren Sie eine Skizze mit Maßen.",
        "upload_sketch": "Skizze hochladen...",
        "pattern_title": "Muster & Zaunfelder",
        "pattern_info": "Musterbild hochladen.",
        "upload_pattern": "Musterbild hochladen...",
        "panel_width": "Feldbreite (mm):",
        "panel_height": "Feldhöhe (mm):",
        "apply_pattern": "Muster anpassen"
    }
}

st.sidebar.title("🌐 Language")
selected_lang = st.sidebar.selectbox("", ["🇸🇮 SLO", "🇬🇧 ENG", "🇩🇪 DEU"])
lang_code = "SLO" if "SLO" in selected_lang else ("ENG" if "ENG" in selected_lang else "DEU")
t = TEXTS[lang_code]

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
        col1, col2 = st.columns(2)
        with col1:
            debelina = st.number_input(t["thickness"], value=2.0, step=0.5)
            material = st.selectbox(t["material"], ["Jeklo (S235/S355)", "Inox (Aisi 304/316)", "Aluminij"])
        with col2:
            radij = st.number_input(t["inner_radius"], value=2.0, step=0.5)
            kot = st.number_input(t["bend_angle"], value=90, step=5)
            
        k_factor = 0.33 if debelina < 3 else 0.40
        ba = (math.pi / 180) * kot * (radij + (k_factor * debelina))
        v_matrica = debelina * 8

        st.info(f"💡 **{t['v_die_rec']}** {v_matrica:.1f} mm | **K-factor:** {k_factor}")
        st.divider()
        st.subheader(t["plate_dims"])
        sirina = st.number_input(t["width"], value=200, step=10)
        visina = st.number_input(t["height"], value=100, step=10)
        premer_luknje = st.number_input(t["hole_diam"], value=10, step=1)
        odmik = st.number_input(t["hole_offset"], value=15, step=1)
        
        razvita_visina = visina + visina - (2 * (radij + debelina)) + ba
        st.success(f"📏 **{t['flat_length']}** {sirina:.1f} mm × {razvita_visina:.1f} mm")
        
        fig, ax = plt.subplots(figsize=(6, 3))
        rect = patches.Rectangle((0, 0), sirina, razvita_visina, linewidth=2, edgecolor='black', facecolor='none')
        ax.add_patch(rect)
        ax.axhline(y=razvita_visina/2, color='blue', linestyle='--', linewidth=1.5, label='Linija krivljenja')
        
        luknje = [(odmik, odmik), (sirina - odmik, odmik), (odmik, razvita_visina - odmik), (sirina - odmik, razvita_visina - odmik)]
        for lx, ly in luknje:
            circle = patches.Circle((lx, ly), premer_luknje / 2, edgecolor='red', facecolor='none', linewidth=1.5)
            ax.add_patch(circle)
            
        ax.set_xlim(-10, sirina + 10)
        ax.set_ylim(-10, razvita_visina + 10)
        ax.set_aspect('equal')
        st.pyplot(fig)
        
        # Generiranje prave DXF datoteke ob kliku
        dxf_vsebina = ustvari_dxf(sirina, razvita_visina, premer_luknje, odmik)
        st.download_button(
            label=t["download_dxf"],
            data=dxf_vsebina,
            file_name=f"plosca_{int(sirina)}x{int(razvita_visina)}mm.dxf",
            mime="application/dxf"
        )

    with zavihek2:
        st.subheader(t["sketch_title"])
        st.write(t["sketch_info"])
        slika_skice = st.file_uploader(t["upload_sketch"], type=["jpg", "jpeg", "png"], key="skica")
        if slika_skice:
            st.image(slika_skice, caption="Naložena skica", use_column_width=True)

    with zavihek3:
        st.subheader(t["pattern_title"])
        st.write(t["pattern_info"])
        slika_vzorca = st.file_uploader(t["upload_pattern"], type=["jpg", "jpeg", "png"], key="vzorec")
        if slika_vzorca:
            st.image(slika_vzorca, caption="Izbrani vzorec", use_column_width=True)

elif modul == t["modules"][2]:
    st.header("🦌 " + t["modules"][2])
    st.write("Modul v pripravi...")

elif modul == t["modules"][3]:
    st.header("🔧 " + t["modules"][3])
    st.write("Modul v pripravi...")
