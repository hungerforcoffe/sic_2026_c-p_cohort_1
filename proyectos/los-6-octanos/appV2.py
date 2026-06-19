"""
appV2.py — Dashboard de Precios de Combustibles en Chile con Google Maps Routing
"""

import os
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
import googlemaps
from geopy.distance import geodesic
from streamlit_geolocation import streamlit_geolocation

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
BASE = "https://api.cne.cl"
LOGIN_URL = f"{BASE}/api/login"
ESTACIONES_URL = f"{BASE}/api/v4/estaciones"

COMBUSTIBLES = {
    "Gasolina 93": "93",
    "Gasolina 95": "95",
    "Gasolina 97": "97",
    "Diésel": "DI",
    "GLP vehicular": "GLP",
    "GNC": "GNC",
    "Kerosene": "KE",
}

st.set_page_config(
    page_title="Precios de Combustibles · Chile",
    page_icon="⛽",
    layout="wide",
)

def obtener_gmaps_key():
    try:
        return st.secrets["GoogleMapsAPI"]
    except Exception:
        return os.environ.get("GoogleMapsAPI")

@st.cache_data(show_spinner="Cargando estaciones desde el dataset local...")
def cargar_datos():
    csv_path = "data/dataset_limpio.csv"
    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), "data", "dataset_limpio.csv")
    
    # Cargar usando codificación UTF-8 para corregir acentos y "ñ"
    df_raw = pd.read_csv(csv_path, encoding="utf-8-sig")
    
    # Limpiar posibles caracteres BOM en las columnas
    df_raw.columns = df_raw.columns.str.replace('^[ï»¿\ufeff]+', '', regex=True)
    
    # Mapeo de nombres de combustible en el CSV a los nombres estándar del diccionario COMBUSTIBLES
    mapa_combustibles = {
        "Gasolina 93": "Gasolina 93",
        "Autoservicio Gasolina 93": "Gasolina 93",
        "Gasolina 95": "Gasolina 95",
        "Autoservicio Gasolina 95": "Gasolina 95",
        "Gasolina 97": "Gasolina 97",
        "Autoservicio Gasolina 97": "Gasolina 97",
        "Petróleo Diesel": "Diésel",
        "Autoservicio Petróleo Diesel": "Diésel",
        "GLP": "GLP vehicular",
        "GNC": "GNC",
        "Kerosene": "Kerosene",
        "Autoservicio Kerosene": "Kerosene"
    }
    
    # Crear columna estandarizada
    df_raw["combustible_estandar"] = df_raw["nombre_combustible"].map(mapa_combustibles)
    df_raw = df_raw.dropna(subset=["combustible_estandar"])
    
    # Convertir lat/lon/precio a números
    df_raw["latitud"] = pd.to_numeric(df_raw["latitud"], errors="coerce")
    df_raw["longitud"] = pd.to_numeric(df_raw["longitud"], errors="coerce")
    df_raw["precio"] = pd.to_numeric(df_raw["precio"], errors="coerce")
    
    # Filtrar precios válidos (entre 400 y 3000 CLP para remover errores/outliers como el 15700.0)
    df_raw = df_raw[(df_raw["precio"] >= 400) & (df_raw["precio"] <= 3000)]
    
    # Filtrar coordenadas de Chile continental
    df_raw = df_raw[df_raw["latitud"].between(-56, -17) & df_raw["longitud"].between(-110, -66)]
    
    # Agrupar por estación (nos quedamos con el precio mínimo/mejor precio de cada tipo)
    df_price = df_raw.pivot_table(
        index=["codigo_estacion", "distribuidor", "region", "comuna", "direccion", "latitud", "longitud"],
        columns="combustible_estandar",
        values="precio",
        aggfunc="min"
    ).reset_index()
    
    # También obtenemos la fecha más reciente de actualización
    df_date = df_raw.pivot_table(
        index=["codigo_estacion", "distribuidor", "region", "comuna", "direccion", "latitud", "longitud"],
        columns="combustible_estandar",
        values="fecha_actualizacion",
        aggfunc="max"
    ).reset_index()
    
    # Renombrar columnas de fecha
    unique_standards = set(mapa_combustibles.values())
    date_cols = {col: f"_fecha_{col}" for col in unique_standards if col in df_date.columns}
    df_date = df_date.rename(columns=date_cols)
    
    # Combinar precio y fecha
    df_pivoted = pd.merge(df_price, df_date, on=["codigo_estacion", "distribuidor", "region", "comuna", "direccion", "latitud", "longitud"])
    
    # Renombrar columnas para compatibilidad
    df_pivoted = df_pivoted.rename(columns={
        "distribuidor": "marca",
        "latitud": "lat",
        "longitud": "lon"
    })
    
    return df_pivoted

@st.cache_data(ttl=3600, show_spinner="Geocodificando dirección...")
def geocode_address_v2(address, api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address + ", Chile",
        "key": api_key
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "OK":
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"], None, None
        else:
            msg = f"Error de geocodificación: {data.get('status')} - {data.get('error_message', '')}"
            return None, None, msg, data.get("status")
    except Exception as e:
        msg = f"Error al conectar con la API de Geocoding: {e}"
        return None, None, msg, "CONNECTION_ERROR"

@st.cache_data(ttl=3600, show_spinner="Calculando rutas...")
def get_routes_v2(origin_lat, origin_lon, destinations, api_key):
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status"
    }
    
    origins_payload = [
        {
            "waypoint": {
                "location": {
                    "latLng": {
                        "latitude": origin_lat,
                        "longitude": origin_lon
                    }
                }
            }
        }
    ]
    
    destinations_payload = []
    for lat, lon in destinations[:25]:
        destinations_payload.append({
            "waypoint": {
                "location": {
                    "latLng": {
                        "latitude": lat,
                        "longitude": lon
                    }
                }
            }
        })
        
    payload = {
        "origins": origins_payload,
        "destinations": destinations_payload,
        "travelMode": "DRIVE"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        import logging
        logging.warning(f"Google Maps Routes API request failed: {e}")
        return None

def pesos(x):
    return f"${x:,.0f}".replace(",", ".")

# --------------------------------------------------------------------------
# Interfaz principal
# --------------------------------------------------------------------------
st.title("⛽ Precios de Combustibles en Chile")
st.caption("Datos locales (18-06-2026) · dataset_limpio.csv")

gmaps_key = obtener_gmaps_key()

if not gmaps_key:
    st.warning("Falta GoogleMapsAPI en `.streamlit/secrets.toml`. Las funciones de ruteo y recomendación estarán deshabilitadas.")

try:
    df = cargar_datos()
except Exception as e:
    st.error(f"No se pudieron cargar los datos desde el archivo local: {e}")
    st.stop()

# ---- Sidebar ----
st.sidebar.header("Filtros")
combustible = st.sidebar.selectbox("Combustible", list(COMBUSTIBLES.keys()))

st.sidebar.divider()
st.sidebar.subheader("📍 Tu Ubicación")

# Botón GPS e Input de Dirección lado a lado
with st.sidebar:
    col_gps, col_text = st.columns([1, 4])
    with col_gps:
        location = streamlit_geolocation()
    with col_text:
        address_input = st.text_input("Dirección", label_visibility="collapsed", placeholder="Escribe dirección...")

user_lat, user_lon = None, None
if address_input and gmaps_key:
    lat, lon, err_msg, status_code = geocode_address_v2(address_input, gmaps_key)
    if err_msg:
        st.error(err_msg)
        if status_code == "REQUEST_DENIED":
            st.info("💡 Por favor, asegúrate de activar la **Geocoding API** en tu consola de Google Cloud:\n"
                    "👉 https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com")
    else:
        user_lat, user_lon = lat, lon
elif location and location.get('latitude') and location.get('longitude'):
    user_lat = location['latitude']
    user_lon = location['longitude']

d = df.dropna(subset=[combustible]).copy()

# ---- Lógica de mejores opciones ----
best_option = None
second_best = None

if user_lat and user_lon and gmaps_key:
    d["distancia_km"] = d.apply(lambda row: geodesic((user_lat, user_lon), (row["lat"], row["lon"])).km, axis=1)
    # Tomar las 20 más cercanas para calcular ETA
    d_cercanas = d.nsmallest(20, "distancia_km").copy()
    
    destinations = [(row["lat"], row["lon"]) for _, row in d_cercanas.iterrows()]
    matrix = get_routes_v2(user_lat, user_lon, destinations, gmaps_key)
    
    tiempos = []
    distancias_reales = []
    
    # Procesar la respuesta de la Routes API
    if matrix and isinstance(matrix, list):
        # Si la API devolvió un error a nivel de proyecto (por ejemplo, permiso denegado)
        if len(matrix) > 0 and "error" in matrix[0]:
            st.warning(f"⚠️ Nota: Google Maps Routes API no está activa o permitida en tu cuenta de Google Cloud. Se utilizaron distancias aéreas estimadas de respaldo.")
            st.info("💡 Puedes activar la **Routes API** en tu consola desde este enlace:\n👉 https://console.developers.google.com/apis/api/routes.googleapis.com/overview")
            matrix = None
            
    if matrix and isinstance(matrix, list):
        results = {}
        for elem in matrix:
            dest_idx = elem.get("destinationIndex", 0)
            status = elem.get("status", {})
            if status and status.get("code") is not None:
                duration = float('inf')
                distance = float('inf')
            else:
                dur_str = elem.get("duration", "0s")
                try:
                    duration = float(dur_str.rstrip("s")) / 60.0
                except ValueError:
                    duration = float('inf')
                
                dist_m = elem.get("distanceMeters", 0)
                distance = float(dist_m) / 1000.0
            
            results[dest_idx] = (duration, distance)
            
        for i in range(len(destinations)):
            duration, distance = results.get(i, (float('inf'), float('inf')))
            tiempos.append(duration)
            distancias_reales.append(distance)
    else:
        # Fallback a distancias geodésicas si la API falla o no está activada
        st.warning("⚠️ Nota: Google Maps Routes API no está activa o permitida en tu cuenta. Se utilizaron distancias aéreas de respaldo para calcular las mejores opciones.")
        st.info("💡 Puedes activar la **Routes API** en tu consola de Google Cloud:\n👉 https://console.developers.google.com/apis/api/routes.googleapis.com/overview")
        tiempos = [float('inf')] * len(destinations)
        distancias_reales = [row["distancia_km"] for _, row in d_cercanas.iterrows()]
            
    d_cercanas["tiempo_viaje_min"] = tiempos
    d_cercanas["distancia_real_km"] = distancias_reales
    
    # Puntaje: precio + (tiempo_viaje * penalización)
    # Si no hay tiempo real disponible (es inf), usamos distancia geodésica * 2 minutos/km como estimación
    tiempos_estimados = []
    for _, row in d_cercanas.iterrows():
        t = row["tiempo_viaje_min"]
        if t == float('inf'):
            # Estimar 2 minutos por km
            t = row["distancia_km"] * 2.0
        tiempos_estimados.append(t)
    
    penalizacion_por_minuto = 15 # Valor arbitrario por minuto
    d_cercanas["puntaje"] = d_cercanas[combustible] + (pd.Series(tiempos_estimados, index=d_cercanas.index) * penalizacion_por_minuto)
    
    d_cercanas = d_cercanas.sort_values("puntaje")
    
    if len(d_cercanas) >= 1:
        best_option = d_cercanas.iloc[0]
        # Si el tiempo real es inf, re-escribir con la estimación para mostrar en la interfaz
        if best_option["tiempo_viaje_min"] == float('inf'):
            best_option = best_option.copy()
            best_option["tiempo_viaje_min"] = best_option["distancia_km"] * 2.0
            
    if len(d_cercanas) >= 2:
        second_best = d_cercanas.iloc[1]
        if second_best["tiempo_viaje_min"] == float('inf'):
            second_best = second_best.copy()
            second_best["tiempo_viaje_min"] = second_best["distancia_km"] * 2.0
        
    d["opacidad"] = 0.1
    d["tamano"] = 3
    d["categoria"] = "Otras"
    
    if best_option is not None:
        d.loc[best_option.name, "opacidad"] = 1.0
        d.loc[best_option.name, "tamano"] = 12
        d.loc[best_option.name, "categoria"] = "🌟 Mejor Opción"
    if second_best is not None:
        d.loc[second_best.name, "opacidad"] = 0.6
        d.loc[second_best.name, "tamano"] = 9
        d.loc[second_best.name, "categoria"] = "⭐ Segunda Opción"
        
    zoom_level = 13
    center_lat, center_lon = user_lat, user_lon
else:
    # Si no hay ubicación, aplicamos filtro de región y valores base
    regiones = sorted(df["region"].dropna().unique())
    sel_regiones = st.sidebar.multiselect("Región (opcional si no das ubicación)", regiones, default=regiones)
    d = d[d["region"].isin(sel_regiones)].copy()
    
    d["opacidad"] = 0.8
    d["tamano"] = 5
    d["categoria"] = "Estaciones"
    zoom_level = 3
    center_lat, center_lon = d["lat"].mean(), d["lon"].mean()

if d.empty:
    st.warning("No hay estaciones con ese combustible en la selección.")
    st.stop()

# ---- KPIs ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Estaciones en vista", f"{len(d):,}".replace(",", "."))
c2.metric("Precio promedio", pesos(d[combustible].mean()))
c3.metric("Más barato", pesos(d[combustible].min()))
c4.metric("Más caro", pesos(d[combustible].max()))

# Opciones recomendadas
if best_option is not None:
    st.success(f"**🌟 Mejor Opción:** {best_option['marca']} en {best_option['direccion']} | Precio: {pesos(best_option[combustible])} | Tiempo: {int(best_option['tiempo_viaje_min'])} min")
    url = f"https://www.google.com/maps/dir/?api=1&origin={user_lat},{user_lon}&destination={best_option['lat']},{best_option['lon']}"
    st.markdown(f"[📍 Ir a Google Maps para iniciar ruta]({url})")

if second_best is not None:
    st.info(f"**⭐ Segunda Opción:** {second_best['marca']} en {second_best['direccion']} | Precio: {pesos(second_best[combustible])} | Tiempo: {int(second_best['tiempo_viaje_min'])} min")

st.divider()

# ---- Mapa ----
st.subheader(f"🗺️ Mapa de precios · {combustible}")

hover_data = {
    "comuna": True,
    "direccion": True,
    combustible: ":$,.0f",
    "lat": False,
    "lon": False,
    "categoria": False,
}

labels = {
    "comuna": "Comuna",
    "direccion": "Dirección",
    combustible: "Precio",
    "marca": "Marca"
}

size_max_val = 12 if (user_lat and user_lon) else 5

# Plotly >= 5.24 scatter_map support
if hasattr(px, "scatter_map"):
    fig = px.scatter_map(d, lat="lat", lon="lon", color=combustible,
                         hover_name="marca", hover_data=hover_data,
                         color_continuous_scale="RdYlGn_r", size="tamano",
                         labels=labels, size_max=size_max_val,
                         zoom=zoom_level, height=600, center=dict(lat=center_lat, lon=center_lon))
    fig.update_layout(
        map_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        separators=",.",
        coloraxis_colorbar=dict(
            title="Precio",
            tickprefix="$",
            tickformat=",.0f"
        )
    )
    if user_lat and user_lon:
        # Contorno negro para la ubicación del usuario
        fig.add_scattermap(lat=[user_lat], lon=[user_lon], mode="markers",
                           marker=dict(size=16, color="black"),
                           showlegend=False, hoverinfo="skip")
        # Relleno color cian para la ubicación del usuario
        fig.add_scattermap(lat=[user_lat], lon=[user_lon], mode="markers+text",
                           marker=dict(size=11, color="#00C0FF"),
                           name="Tu Ubicación (círculo con contorno negro)", text=["📍 Tu Ubicación"], textposition="top right")
else:
    fig = px.scatter_mapbox(d, lat="lat", lon="lon", color=combustible,
                            hover_name="marca", hover_data=hover_data,
                            color_continuous_scale="RdYlGn_r", size="tamano",
                            labels=labels, size_max=size_max_val,
                            zoom=zoom_level, height=600, center=dict(lat=center_lat, lon=center_lon))
    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        separators=",.",
        coloraxis_colorbar=dict(
            title="Precio",
            tickprefix="$",
            tickformat=",.0f"
        )
    )
    if user_lat and user_lon:
        # Contorno negro para la ubicación del usuario
        fig.add_scattermapbox(lat=[user_lat], lon=[user_lon], mode="markers",
                               marker=dict(size=16, color="black"),
                               showlegend=False, hoverinfo="skip")
        # Relleno color cian para la ubicación del usuario
        fig.add_scattermapbox(lat=[user_lat], lon=[user_lon], mode="markers+text",
                               marker=dict(size=11, color="#00C0FF"),
                               name="Tu Ubicación (círculo con contorno negro)", text=["📍 Tu Ubicación"], textposition="top right")

# Aplicar opacidades dinámicas y generar el contorno negro para las estaciones
if len(fig.data) > 0:
    # 1. Aplicar opacidades dinámicas al trace de color principal
    fig.data[0].marker.opacity = d["opacidad"].tolist()
    
    # 2. Duplicar el trace para crear el contorno negro por detrás
    import copy
    trace_border = copy.deepcopy(fig.data[0])
    
    # Eliminar mapeos de escala de color en ambas estructuras posibles
    if hasattr(trace_border, "coloraxis"):
        trace_border.coloraxis = None
    if hasattr(trace_border.marker, "coloraxis"):
        trace_border.marker.coloraxis = None
        
    trace_border.marker.color = "black"
    
    # Agrandar los marcadores negros 2px más que los de color para simular el borde de 1px
    if trace_border.marker.size is not None:
        if hasattr(trace_border.marker.size, "tolist"):
            sizes = trace_border.marker.size.tolist()
        else:
            sizes = list(trace_border.marker.size)
        trace_border.marker.size = [s + 2 for s in sizes]
        
    trace_border.hoverinfo = "skip"
    trace_border.hovertemplate = None
    trace_border.showlegend = False
    
    # Agregar el trace a la figura (se añade al final)
    fig.add_trace(trace_border)
    
    # Reordenar los traces moviendo el de contorno (el último) al primer lugar
    fig.data = (fig.data[-1],) + fig.data[:-1]

st.plotly_chart(fig, use_container_width=True)

# ---- Ranking ----
st.subheader(f"🏆 Ranking de comunas · {combustible}")
col_a, col_b = st.columns(2)
orden = col_a.radio("Mostrar", ["Más baratas", "Más caras"], horizontal=True)
topn = col_b.slider("Cantidad de comunas", 5, 30, 15)

asc = orden == "Más baratas"
rank = (d.groupby("comuna")[combustible].mean()
          .sort_values(ascending=asc).head(topn).reset_index())
fig_rank = px.bar(
    rank.sort_values(combustible, ascending=not asc),
    x=combustible, y="comuna", orientation="h",
    color=combustible, color_continuous_scale="RdYlGn_r",
    labels={combustible: "Precio Promedio", "comuna": "Comuna"}, height=500,
)
fig_rank.update_layout(
    coloraxis_showscale=False,
    margin=dict(l=0, r=0, t=10, b=0),
    separators=",.",
    xaxis=dict(
        tickprefix="$",
        tickformat=",.0f"
    )
)
st.plotly_chart(fig_rank, use_container_width=True)

st.divider()
st.caption("Fuente: Comisión Nacional de Energía (CNE) · Proyecto SIC Coding & Programming")
