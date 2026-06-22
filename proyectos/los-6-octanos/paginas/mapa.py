"""Página: Mapa — mapa Folium con geolocalización, ruteo y mejor opción."""
import streamlit as st
from streamlit_folium import st_folium

import comun_app as comun

# st.title("🗺️ Mapa de Precios") # Eliminado para no competir con el Hero Banner
st.caption("Datos locales (18-06-2026) · dataset_limpio.csv")

# === INYECCIÓN CSS PARA LAS NUEVAS TARJETAS ===
# === INYECCIÓN CSS PARA LAS NUEVAS TARJETAS ===
st.markdown(
    """
    <style>
        /* 1. REPARACIÓN DE ICONOS MATERIAL SYMBOLS */
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');

        .material-symbols-outlined {
            font-family: 'Material Symbols Outlined' !important; /* El !important es clave aquí */
            font-weight: normal;
            font-style: normal;
            line-height: 1;
            letter-spacing: normal;
            text-transform: none;
            display: inline-block;
            white-space: nowrap;
            word-wrap: normal;
            direction: ltr;
            -webkit-font-smoothing: antialiased;
        }

        /* 2. TARJETAS DE RECOMENDACIÓN */
        .recommendation-card {
            background-color: #1F2937;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 16px;
            border: 1px solid #374151;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .best-option {
            border-left: 5px solid #10B981;
            background: linear-gradient(90deg, rgba(16, 185, 129, 0.08) 0%, transparent 100%);
        }
        .best-option .highlight { color: #10B981; font-weight: 600; font-family: 'Inter', sans-serif;}

        .second-option {
            border-left: 5px solid #3B82F6;
            background: linear-gradient(90deg, rgba(59, 130, 246, 0.05) 0%, transparent 100%);
        }
        .second-option .highlight { color: #3B82F6; font-weight: 600; font-family: 'Inter', sans-serif;}

        .card-content { display: flex; flex-direction: column; gap: 4px; }
        
        .card-content p {
            margin: 0;
            color: #E5E7EB;
            font-size: 0.95rem;
        }
        
        .card-content .station-name {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.1rem;
            color: #FFFFFF;
        }

        /* Botón de ruta limpio integrado en la tarjeta */
        .route-btn {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin-top: 8px; /* Separación del texto de arriba */
            color: #34D399 !important; /* Verde menta claro */
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
            transition: color 0.2s ease;
            width: fit-content;
        }
        .route-btn:hover { color: #10B981 !important; text-decoration: underline; }
        
        /* Variante azul para la segunda opción */
        .route-btn-blue { color: #60A5FA !important; }
        .route-btn-blue:hover { color: #3B82F6 !important; text-decoration: underline;
    </style>
    """,
    unsafe_allow_html=True
)

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
    # Usando Material Symbols nativos de Streamlit en vez de emojis
    st.subheader(f":material/analytics: Análisis de {combustible} {contexto_lugar}")
    comun.render_kpis(d, combustible)

    best_option = opcion["best_option"]
    second_best = opcion["second_best"]

   # === REDISEÑO DE MEJOR OPCIÓN ===
    if best_option is not None:
        gm_url_best = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={user_lat},{user_lon}"
            f"&destination={best_option['lat']},{best_option['lon']}"
        )
        
        html_mejor_opcion = f"""
        <div class="recommendation-card best-option">
            <span class="material-symbols-outlined" style="color: #10B981; font-size: 32px;">local_gas_station</span>
            <div class="card-content">
                <p class="highlight">Mejor Opción Calculada</p>
                <p><span class="station-name">{best_option['marca']} — {best_option['direccion']}</span> | {comun.pesos(best_option[combustible])} | {opcion['eta_str']}</p>
                <a href='{gm_url_best}' target='_blank' class='route-btn'><span class='material-symbols-outlined' style='font-size: 16px;'>directions_car</span> Abrir ruta en Google Maps</a>
            </div>
        </div>
        """
        st.markdown(html_mejor_opcion, unsafe_allow_html=True)

    # === REDISEÑO DE SEGUNDA OPCIÓN ===
    if second_best is not None:
        gm_url_second = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={user_lat},{user_lon}"
            f"&destination={second_best['lat']},{second_best['lon']}"
        )
        
        html_segunda_opcion = f"""
        <div class="recommendation-card second-option">
            <span class="material-symbols-outlined" style="color: #3B82F6; font-size: 32px;">ev_station</span>
            <div class="card-content">
                <p class="highlight">Alternativa Cercana</p>
                <p><span class="station-name">{second_best['marca']} — {second_best['direccion']}</span> | {comun.pesos(second_best[combustible])} | ~{int(second_best['tiempo_viaje_min'])} min (estimado)</p>
                <a href='{gm_url_second}' target='_blank' class='route-btn route-btn-blue'><span class='material-symbols-outlined' style='font-size: 16px;'>directions_car</span> Abrir ruta en Google Maps</a>
            </div>
        </div>
        """
        st.markdown(html_segunda_opcion, unsafe_allow_html=True)
        
    st.divider()

    # Otro Material Symbol para el mapa
    st.subheader(f":material/map: Mapa de Precios de {combustible} {contexto_lugar}")

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
