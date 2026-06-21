"""Página: Dashboard — KPIs, mapa de decisión precio/distancia y comparativa por distribuidor."""
import streamlit as st

import comun_app as comun

st.title("📊 Dashboard de Análisis")
st.caption("Datos locales (18-06-2026) · dataset_limpio.csv")

gmaps_key = comun.obtener_gmaps_key()

try:
    df = comun.cargar_datos()
except Exception as exc:
    st.error(f"No se pudieron cargar los datos: {exc}")
    st.stop()

filtros = comun.render_filtros_sidebar(df, gmaps_key)
combustible = filtros["combustible"]
contexto_lugar = filtros["contexto_lugar"]
d = filtros["d"]
d_filtros = filtros["d_filtros"]
user_lat = filtros["user_lat"]
user_lon = filtros["user_lon"]

if d.empty:
    st.warning("No hay estaciones con ese combustible en la selección geográfica actual.")
    st.stop()

col_viz, col_chat = st.columns([7, 3], gap="large")

with col_viz:
    st.subheader(f"Análisis de {combustible} {contexto_lugar}")
    comun.render_kpis(d, combustible)

    st.divider()
    comun.render_scatter_pareto(d, combustible, contexto_lugar, user_lat, user_lon)

    st.divider()
    comun.render_comparativa_distribuidor(d, combustible, contexto_lugar)

    st.divider()
    st.caption("Fuente: Comisión Nacional de Energía (CNE) · Proyecto SIC Coding & Programming")

with col_chat:
    comun.render_chatbot(d_filtros, contexto_lugar)
