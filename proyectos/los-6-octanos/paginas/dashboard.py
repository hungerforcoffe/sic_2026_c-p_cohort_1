"""Página: Dashboard — KPIs, mapa de decisión precio/distancia y comparativa por distribuidor."""
import streamlit as st
import comun_app as comun

# st.title("📊 Dashboard de Análisis") # Eliminado para mantener consistencia visual
st.caption("Datos locales (18-06-2026) · dataset_limpio.csv")

# === ESTILOS ESPECÍFICOS PARA EL DASHBOARD ===
st.markdown("""
    <style>
        /* Ajuste de las métricas para el Dashboard */
        [data-testid="stMetric"] {
            background-color: #1F2937;
            border-left: 4px solid #10B981; 
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }
        [data-testid="stMetricValue"] {
            font-family: 'Space Grotesk', sans-serif !important;
            color: #FFFFFF !important;
        }
    </style>
""", unsafe_allow_html=True)

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
    # Usando Material Symbols nativos
    st.subheader(f":material/analytics: Análisis de {combustible} {contexto_lugar}")
    comun.render_kpis(d, combustible)

    st.divider()
    
    # Pareto Scatter
    comun.render_scatter_pareto(d, combustible, contexto_lugar, user_lat, user_lon)

    st.divider()
    
    # Comparativa
    comun.render_comparativa_distribuidor(d, combustible, contexto_lugar)

    st.divider()
    st.caption("Fuente: Comisión Nacional de Energía (CNE) · Proyecto SIC Coding & Programming")

with col_chat:
    comun.render_chatbot(d_filtros, contexto_lugar)