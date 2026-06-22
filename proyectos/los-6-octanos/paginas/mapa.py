"""Página: Mapa — mapa Folium con geolocalización, ruteo y mejor opción."""
import streamlit as st
from streamlit_folium import st_folium

import comun_app as comun

st.title("🗺️ Mapa de Precios")
st.caption("Datos locales (18-06-2026) · dataset_limpio.csv")

gmaps_key = comun.obtener_gmaps_key()
if not gmaps_key:
    st.warning(
        "Falta `GoogleMapsAPI` en `.streamlit/secrets.toml`. "
        "Las funciones de ruteo y recomendación estarán deshabilitadas."
    )

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

opcion = comun.calcular_mejor_opcion(
    d, combustible, user_lat, user_lon, gmaps_key,
    filtros["region_sel"], filtros["comuna_sel"],
)

col_viz, col_chat = st.columns([7, 3], gap="large")

with col_viz:
    st.subheader(f"Análisis de {combustible} {contexto_lugar}")
    comun.render_kpis(d, combustible)

    best_option = opcion["best_option"]
    second_best = opcion["second_best"]

    if best_option is not None:
        st.success(
            f"**🌟 Mejor Opción:** {best_option['marca']} — {best_option['direccion']} "
            f"| {comun.pesos(best_option[combustible])} | {opcion['eta_str']}"
        )
        gm_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={user_lat},{user_lon}"
            f"&destination={best_option['lat']},{best_option['lon']}"
        )
        st.markdown(f"[📍 Abrir ruta completa en Google Maps]({gm_url})")

    if second_best is not None:
        st.info(
            f"**⭐ Segunda Opción:** {second_best['marca']} — {second_best['direccion']} "
            f"| {comun.pesos(second_best[combustible])} "
            f"| ~{int(second_best['tiempo_viaje_min'])} min (estimado)"
        )

    st.divider()

    st.subheader(f"🗺️ Mapa de Precios de {combustible} {contexto_lugar}")

    m, vmin, vmax = comun.construir_mapa_folium(
        d, combustible, filtros["fondo_mapa"], user_lat, user_lon, opcion
    )

    map_col, legend_col = st.columns([5, 1])
    with legend_col:
        st.components.v1.html(
            comun.make_legend_html(vmin, vmax, combustible, opcion["has_user"]),
            height=640,
        )
    with map_col:
        st_folium(m, use_container_width=True, height=620, returned_objects=[])

    st.divider()
    st.caption("Fuente: Comisión Nacional de Energía (CNE) · Proyecto SIC Coding & Programming")

with col_chat:
    comun.render_chatbot(d_filtros, contexto_lugar)
