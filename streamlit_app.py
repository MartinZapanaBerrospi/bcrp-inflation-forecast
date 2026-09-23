"""Pronóstico de inflación en Perú con datos del BCRP. Punto de entrada de Streamlit."""

import streamlit as st

from app import data, views
from app.data import month_label

st.set_page_config(page_title="Pronóstico de inflación · Perú", page_icon=":material/trending_up:", layout="wide")

pages = [
    st.Page(views.inflacion_hoy, title="Inflación hoy", icon=":material/monitoring:", url_path="hoy", default=True),
    st.Page(views.pronostico, title="Pronóstico", icon=":material/trending_up:", url_path="pronostico"),
    st.Page(views.validacion, title="Validación", icon=":material/fact_check:", url_path="validacion"),
    st.Page(views.que_lo_mueve, title="Qué lo mueve", icon=":material/tune:", url_path="que-lo-mueve"),
    st.Page(views.como_se_hizo, title="Cómo se hizo", icon=":material/construction:", url_path="como-se-hizo"),
]

with st.sidebar:
    s = data.summary()
    st.markdown("### Inflación en Perú")
    st.caption(f"Datos del BCRP hasta **{month_label(s['ultimo_mes'], long=True)}**. Se actualiza cada mes.")
    st.markdown(f"[Código y documentación]({views.REPO})  \n[Autor: Martín Zapana](https://www.martinzapana.com)")

st.navigation(pages).run()
