import streamlit as st

st.set_page_config(page_title="Moja Delavnica", page_icon="🛠️")

st.title("🛠️ Moja Delavnica App")
st.write("Dobrodošel v tvoji osebni aplikaciji za delavnico in teren!")

# Stranski meni za izbiro modulov
modul = st.sidebar.radio("Izberi modul:", ["Domov", "CAD / DXF", "Diagnostika", "Lovske kamere"])

if modul == "Domov":
    st.success("Sistem deluje in je pripravljen za uporabo!")
    st.info("Tukaj bova postopoma dodajala tvoja orodja.")

elif modul == "CAD / DXF":
    st.header("📐 CAD / DXF Generator")
    st.write("Modul za pretvorbo skic in risanje.")

elif modul == "Diagnostika":
    st.header("🔍 Tehnična Diagnostika")
    st.write("Modul za analizo napak in izbiro materialov.")

elif modul == "Lovske kamere":
    st.header("🦌 Lovske Kamere & AI")
    st.write("Modul za pregled fotografij in pametno filtriranje.")
