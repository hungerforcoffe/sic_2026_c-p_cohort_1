"""
comun_app.py — Lógica y componentes compartidos entre las páginas de la app
multipágina (paginas/mapa.py y paginas/dashboard.py). No se ejecuta solo.
"""
import os
import logging
import textwrap
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import folium
import branca.colormap as bcm
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from geopy.distance import geodesic
from google import genai
from google.genai import types

COMBUSTIBLES = {
    "Gasolina 93": "93",
    "Gasolina 95": "95",
    "Gasolina 97": "97",
    "Diésel": "DI",
    "GLP vehicular": "GLP",
    "GNC": "GNC",
    "Kerosene": "KE",
}

FONDOS_MAPA = {
    "Google Maps":    ("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", "Google Maps"),
    "Google Satélite":("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", "Google Satellite"),
    "Google Híbrido": ("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", "Google Hybrid"),
    "OpenStreetMap":  (None, "OpenStreetMap"),
}

# Paleta Eco-Drive adaptada para el mapa de calor (verde menta a rojo)
GRADIENT_COLORS = [
    "#10B981", "#34D399", "#A7F3D0", "#FDE68A",
    "#FBBF24", "#F59E0B", "#EF4444", "#B91C1C",
]

# ═══════════════════════════════════════════════════════════════════
# Utilidades generales
# ═══════════════════════════════════════════════════════════════════

def obtener_gmaps_key():
    try:
        return st.secrets["GoogleMapsAPI"]
    except Exception:
        return os.environ.get("GoogleMapsAPI")

def obtener_google_api_key():
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        return os.environ.get("GOOGLE_API_KEY")

def pesos(x):
    try:
        return f"${x:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "N/A"

def estilizar_barra_precio(fig, valores, padding_frac=0.12, min_padding=15):
    vmin, vmax = float(min(valores)), float(max(valores))
    pad = max((vmax - vmin) * padding_frac, min_padding)
    fig.update_traces(texttemplate="$%{x:,.0f}", textposition="outside", cliponaxis=False, textfont=dict(color="#F9FAFB"))
    fig.update_xaxes(range=[max(0, vmin - pad), vmax + pad], tickprefix="$", tickformat=",.0f", gridcolor="#374151")
    fig.update_yaxes(gridcolor="#374151")
    return fig

def decode_polyline(encoded):
    coords = []
    index, lat, lng = 0, 0, 0
    n = len(encoded)
    try:
        while index < n:
            shift, result = 0, 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            lat += (~result >> 1) if (result & 1) else (result >> 1)

            shift, result = 0, 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            lng += (~result >> 1) if (result & 1) else (result >> 1)
            coords.append((lat * 1e-5, lng * 1e-5))
    except (IndexError, TypeError):
        pass
    return coords


# ═══════════════════════════════════════════════════════════════════
# Carga de datos (cacheada) — dataset local
# ═══════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Cargando estaciones desde el dataset local...")
def cargar_datos():
    csv_path = "data/dataset_limpio.csv"
    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), "data", "dataset_limpio.csv")

    df_raw = pd.read_csv(csv_path, encoding="utf-8-sig")
    df_raw.columns = df_raw.columns.str.replace("^+", "", regex=True)

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
        "Autoservicio Kerosene": "Kerosene",
    }

    df_raw["combustible_estandar"] = df_raw["nombre_combustible"].map(mapa_combustibles)
    df_raw = df_raw.dropna(subset=["combustible_estandar"])

    for col in ("latitud", "longitud", "precio"):
        df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")

    df_raw = df_raw[
        (df_raw["precio"] >= 400)
        & (df_raw["precio"] <= 3000)
        & df_raw["latitud"].between(-56, -17)
        & df_raw["longitud"].between(-110, -66)
    ]

    df_price = (
        df_raw.pivot_table(
            index=["codigo_estacion", "distribuidor", "region", "comuna",
                   "direccion", "latitud", "longitud"],
            columns="combustible_estandar",
            values="precio",
            aggfunc="min",
        )
        .reset_index()
        .rename(columns={"distribuidor": "marca", "latitud": "lat", "longitud": "lon"})
    )
    return df_price

# ═══════════════════════════════════════════════════════════════════
# APIs de Google (Geocode, Matrix, Routes) ... (SIN CAMBIOS LÓGICOS)
# ═══════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner="Geocodificando dirección...")
def geocode_address_v3(address, api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        r = requests.get(url, params={"address": address + ", Chile", "key": api_key}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"], None, None
        msg = f"Geocodificación: {data.get('status')} — {data.get('error_message', '')}"
        return None, None, msg, data.get("status")
    except Exception as exc:
        return None, None, f"Error al conectar con Geocoding API: {exc}", "CONNECTION_ERROR"

@st.cache_data(ttl=3600, show_spinner="Calculando tiempos de viaje...")
def get_route_matrix_v3(origin_lat, origin_lon, destinations, api_key):
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status",
    }
    origins = [{"waypoint": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lon}}}}]
    dests = [{"waypoint": {"location": {"latLng": {"latitude": la, "longitude": lo}}}} for la, lo in destinations[:25]]
    try:
        r = requests.post(url, json={"origins": origins, "destinations": dests, "travelMode": "DRIVE"}, headers=headers, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logging.warning("Route matrix failed: %s", exc)
        return None

@st.cache_data(ttl=300, show_spinner="Trazando ruta con tráfico...")
def get_route_polyline_v3(origin_lat, origin_lon, dest_lat, dest_lon, api_key):
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.duration,routes.distanceMeters",
    }
    origin_wp = {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lon}}}
    dest_wp   = {"location": {"latLng": {"latitude": dest_lat,   "longitude": dest_lon}}}

    for routing_pref in ("TRAFFIC_AWARE", "TRAFFIC_UNAWARE"):
        payload = {
            "origin": {"location": origin_wp["location"]},
            "destination": {"location": dest_wp["location"]},
            "travelMode": "DRIVE",
            "routingPreference": routing_pref,
            "computeAlternativeRoutes": False,
            "languageCode": "es",
            "units": "METRIC",
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
            routes = data.get("routes", [])
            if routes:
                route = routes[0]
                encoded = route.get("polyline", {}).get("encodedPolyline", "")
                dur_s = route.get("duration", "0s")
                dist_m = route.get("distanceMeters", 0)
                try:
                    dur_min = float(str(dur_s).rstrip("s")) / 60.0
                except (ValueError, AttributeError):
                    dur_min = None
                dist_km = float(dist_m) / 1000.0 if dist_m else None
                coords = decode_polyline(encoded) if encoded else []
                traffic_label = "con tráfico" if routing_pref == "TRAFFIC_AWARE" else "estimado"
                return coords, dur_min, dist_km, None, traffic_label
        except Exception as exc:
            logging.warning("computeRoutes (%s) failed: %s", routing_pref, exc)
            continue

    return [], None, None, "No se pudo calcular la ruta", ""


# ═══════════════════════════════════════════════════════════════════
# HTML: Popup de marcador y leyenda lateral (REDISEÑADOS)
# ═══════════════════════════════════════════════════════════════════

def make_popup_html(row, combustible, tag=None, user_lat=None, user_lon=None, tiempo_min=None, distancia_km=None, traffic_label=""):
    precio_str = pesos(row.get(combustible, 0))

    tag_html = ""
    if tag == "best":
        tag_html = (
            '<div style="background:rgba(16, 185, 129, 0.15);color:#10B981;border: 1px solid rgba(16, 185, 129, 0.3);'
            'padding:4px 10px;border-radius:6px;font-weight:700;font-size:11px;margin-bottom:8px;text-align:center;text-transform:uppercase;">'
            'Mejor Opción Calculada</div>'
        )
    elif tag == "second":
        tag_html = (
            '<div style="background:rgba(59, 130, 246, 0.15);color:#3B82F6;border: 1px solid rgba(59, 130, 246, 0.3);'
            'padding:4px 10px;border-radius:6px;font-weight:700;font-size:11px;margin-bottom:8px;text-align:center;text-transform:uppercase;">'
            'Alternativa Cercana</div>'
        )

    route_html = ""
    if user_lat is not None and user_lon is not None:
        gm_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={user_lat},{user_lon}"
            f"&destination={row['lat']},{row['lon']}"
        )
        trip_info = ""
        if tiempo_min is not None and tiempo_min != float("inf"):
            d_str = f"{distancia_km:.1f} km · " if distancia_km else ""
            trip_info = f'<div style="font-size:11px;color:#6B7280;margin-top:5px;text-align:center;">{d_str}~{int(tiempo_min)} min ({traffic_label})</div>'
        
        # Botón estilo Eco-Drive Verde Menta
        route_html = f"""
        {trip_info}
        <div style="margin-top:10px;text-align:center;">
            <a href="{gm_url}" target="_blank"
               style="display:inline-block;background:#10B981;color:#ffffff;
                      padding:8px 16px;border-radius:8px;text-decoration:none;
                      font-size:13px;font-weight:600;box-shadow: 0 2px 4px rgba(16,185,129,0.3);">
                Abrir ruta en Google Maps
            </a>
        </div>"""

    return f"""
    <div style="font-family:'Inter',sans-serif;min-width:240px;padding:5px;">
        {tag_html}
        <h4 style="margin:0 0 10px 0;color:#111827;font-size:16px;font-family:'Space Grotesk',sans-serif;">{row.get("marca","N/A")}</h4>
        <table style="font-size:13px;line-height:1.8;width:100%;border-collapse:collapse;">
            <tr>
                <td style="font-weight:600;color:#6B7280;padding-right:10px;white-space:nowrap;">Comuna:</td>
                <td style="color:#111827;">{row.get("comuna","N/A")}</td>
            </tr>
            <tr>
                <td style="font-weight:600;color:#6B7280;padding-right:10px;white-space:nowrap;">Dirección:</td>
                <td style="color:#111827;">{row.get("direccion","N/A")}</td>
            </tr>
            <tr>
                <td style="font-weight:600;color:#6B7280;padding-right:10px;white-space:nowrap;">Precio:</td>
                <td style="font-weight:700;font-size:15px;color:#111827;font-family:'Space Grotesk',sans-serif;">{precio_str}</td>
            </tr>
        </table>
        {route_html}
    </div>"""


def make_legend_html(vmin, vmax, combustible, has_user):
    grad = ", ".join(reversed(GRADIENT_COLORS))

    def mini_circle_svg(fill, stroke):
        return (
            f'<svg width="14" height="14" viewBox="0 0 14 14" xmlns="http://www.w3.org/2000/svg">'
            f'<circle cx="7" cy="7" r="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
            f'</svg>'
        )

    markers_html = ""
    if has_user:
        # AQUÍ ESTÁN LOS COLORES CORREGIDOS:
        markers_html = f"""
        <div style="margin-top:18px;border-top:1px solid #374151;padding-top:16px;">
            <p style="font-weight:700;font-size:11px;margin:0 0 12px 0;
                      color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px;font-family:sans-serif;">
                Marcadores
            </p>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                {mini_circle_svg("#3B82F6", "#FFFFFF")}
                <span style="font-size:12px;color:#E5E7EB;line-height:1.2;">Tu Ubicación</span>
            </div>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                {mini_circle_svg("#10B981", "#FFFFFF")}
                <span style="font-size:12px;color:#E5E7EB;line-height:1.2;">Mejor Opción</span>
            </div>
            <div style="display:flex;align-items:center;gap:10px;">
                {mini_circle_svg("#FBBF24", "#FFFFFF")}
                <span style="font-size:12px;color:#E5E7EB;line-height:1.2;">Segunda Opción</span>
            </div>
        </div>"""

    # Fondo oscuro a juego con las tarjetas de la App
    return textwrap.dedent(f"""
    <div style="
        font-family:'Inter',sans-serif;
        padding:16px;
        background:#1F2937;
        border:1px solid #374151;
        border-radius:12px;
        height:620px;
        box-sizing:border-box;
        display:flex;
        flex-direction:column;
    ">
        <p style="font-weight:700;font-size:12px;margin:0 0 12px 0;
                  color:#F9FAFB;text-transform:uppercase;letter-spacing:.5px;font-family:'Space Grotesk',sans-serif;">
            Precio<br>{combustible}
        </p>

        <div style="display:flex;align-items:stretch;gap:10px;flex:1;min-height:0;">
            <div style="
                width:20px;
                border-radius:8px;
                background:linear-gradient(to bottom, {grad});
                flex-shrink:0;
            "></div>
            <div style="
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                font-size:11px;
                color:#D1D5DB;
                padding:2px 0;
            ">
                <div style="font-weight:700;line-height:1.3;color:#EF4444;font-family:'Space Grotesk',sans-serif;font-size:13px;">
                    {pesos(vmax)}<br>
                    <span style="font-weight:500;font-size:10px;color:#9CA3AF;font-family:'Inter',sans-serif;">más caro</span>
                </div>
                <div style="font-weight:700;line-height:1.3;color:#10B981;font-family:'Space Grotesk',sans-serif;font-size:13px;">
                    {pesos(vmin)}<br>
                    <span style="font-weight:500;font-size:10px;color:#9CA3AF;font-family:'Inter',sans-serif;">más barato</span>
                </div>
            </div>
        </div>

        {markers_html}
    </div>""")


# ═══════════════════════════════════════════════════════════════════
# Barra lateral compartida: Ubicación → Filtros en cascada → Fondo del mapa
# ═══════════════════════════════════════════════════════════════════

def render_filtros_sidebar(df, gmaps_key):
    st.sidebar.markdown("### :material/tune: PANEL DE CONTROL")
    st.sidebar.markdown("Usa estos filtros para explorar el mercado:")

    st.sidebar.subheader(":material/my_location: Tu Ubicación")
    with st.sidebar:
        col_gps, col_text = st.columns([1, 4])
        with col_gps:
            location = streamlit_geolocation()
        with col_text:
            direccion_guardada = st.session_state.get("direccion_actual", "")
            address_input = st.text_input(
                "Dirección",
                value=direccion_guardada,
                label_visibility="collapsed",
                placeholder="Escribe dirección...",
            )
            st.session_state["direccion_actual"] = address_input

    user_lat, user_lon = None, None

    if address_input and gmaps_key:
        lat, lon, err_msg, err_code = geocode_address_v3(address_input, gmaps_key)
        if err_msg:
            st.sidebar.warning(f"⚠️ {err_msg}")
            if err_code == "REQUEST_DENIED":
                st.sidebar.info(
                    "💡 Activa la **Geocoding API**:\n"
                    "👉 https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com"
                )
        else:
            user_lat, user_lon = lat, lon
    elif location and location.get("latitude") and location.get("longitude"):
        user_lat = location["latitude"]
        user_lon = location["longitude"]

    if user_lat is not None and user_lon is not None:
        st.session_state["user_lat_actual"] = user_lat
        st.session_state["user_lon_actual"] = user_lon
    elif not address_input:
        user_lat = st.session_state.get("user_lat_actual")
        user_lon = st.session_state.get("user_lon_actual")

    region_actual = st.session_state.get("region_actual", "Todas las Regiones")
    comuna_actual = st.session_state.get("comuna_actual", "Todas las Comunas")

    if user_lat is not None and user_lon is not None:
        clave_ubicacion = (round(user_lat, 4), round(user_lon, 4))
        if st.session_state.get("_ubicacion_autofiltrada") != clave_ubicacion:
            dist2 = (df["lat"] - user_lat) ** 2 + (df["lon"] - user_lon) ** 2
            fila_cercana = df.loc[dist2.idxmin()]
            region_actual = fila_cercana["region"]
            comuna_actual = fila_cercana["comuna"]
            st.session_state["_ubicacion_autofiltrada"] = clave_ubicacion

    st.sidebar.divider()

    regiones = ["Todas las Regiones"] + sorted(df["region"].dropna().unique().tolist())
    idx_region = regiones.index(region_actual) if region_actual in regiones else 0
    region_sel = st.sidebar.selectbox(":material/map: Selecciona una Región:", regiones, index=idx_region)
    st.session_state["region_actual"] = region_sel

    if region_sel != "Todas las Regiones":
        df_region = df[df["region"] == region_sel]
    else:
        df_region = df

    comunas = ["Todas las Comunas"] + sorted(df_region["comuna"].dropna().unique().tolist())
    if comuna_actual not in comunas:
        comuna_actual = "Todas las Comunas"
    idx_comuna = comunas.index(comuna_actual)
    comuna_sel = st.sidebar.selectbox(":material/location_city: Selecciona una Comuna:", comunas, index=idx_comuna)
    st.session_state["comuna_actual"] = comuna_sel

    if user_lat is not None and user_lon is not None:
        st.sidebar.caption("📍 Región y comuna sugeridas según tu ubicación — puedes cambiarlas.")

    if region_sel != "Todas las Regiones" and comuna_sel == "Todas las Comunas":
        d_filtros = df[df["region"] == region_sel].copy()
        contexto_lugar = f"en la {region_sel}"
    elif comuna_sel != "Todas las Comunas":
        d_filtros = df_region[df_region["comuna"] == comuna_sel].copy()
        contexto_lugar = f"en {comuna_sel}"
    else:
        d_filtros = df.copy()
        contexto_lugar = "a Nivel Nacional"

    st.sidebar.divider()

    lista_combustibles = list(COMBUSTIBLES.keys())
    combustible_actual = st.session_state.get("combustible_actual", lista_combustibles[0])
    idx_combustible = lista_combustibles.index(combustible_actual) if combustible_actual in lista_combustibles else 0
    combustible = st.sidebar.selectbox(
        ":material/local_gas_station: Combustible a analizar:", lista_combustibles, index=idx_combustible
    )
    st.session_state["combustible_actual"] = combustible
    st.sidebar.info(f"Análisis actual: **{combustible}** {contexto_lugar}")

    st.sidebar.divider()

    with st.sidebar.expander(":material/layers: Fondo del mapa", expanded=False):
        fondos = list(FONDOS_MAPA.keys())
        fondo_actual = st.session_state.get("fondo_mapa_actual", fondos[0])
        idx_fondo = fondos.index(fondo_actual) if fondo_actual in fondos else 0
        fondo_mapa = st.selectbox(
            "Fondo del mapa", fondos, index=idx_fondo, label_visibility="collapsed"
        )
        st.session_state["fondo_mapa_actual"] = fondo_mapa

    d = d_filtros.dropna(subset=[combustible]).copy()

    return {
        "region_sel": region_sel,
        "comuna_sel": comuna_sel,
        "combustible": combustible,
        "contexto_lugar": contexto_lugar,
        "user_lat": user_lat,
        "user_lon": user_lon,
        "fondo_mapa": fondo_mapa,
        "d_filtros": d_filtros,
        "d": d,
    }


# ═══════════════════════════════════════════════════════════════════
# Mejor opción + ruteo ... (SIN CAMBIOS LÓGICOS)
# ═══════════════════════════════════════════════════════════════════
def calcular_mejor_opcion(d, combustible, user_lat, user_lon, gmaps_key, region_sel, comuna_sel):
    best_option   = None
    second_best   = None
    route_coords  = []
    route_dur_min = None
    route_dist_km = None
    route_label   = ""
    eta_str       = ""

    if user_lat and user_lon and gmaps_key:
        d["distancia_km"] = d.apply(
            lambda row: geodesic((user_lat, user_lon), (row["lat"], row["lon"])).km, axis=1
        )
        d_cercanas = d.nsmallest(20, "distancia_km").copy()
        destinations = [(row["lat"], row["lon"]) for _, row in d_cercanas.iterrows()]
        matrix = get_route_matrix_v3(user_lat, user_lon, destinations, gmaps_key)

        tiempos, distancias_reales = [], []

        if matrix and isinstance(matrix, list):
            if len(matrix) > 0 and "error" in matrix[0]:
                matrix = None

        if matrix and isinstance(matrix, list):
            results = {}
            for elem in matrix:
                dest_idx = elem.get("destinationIndex", 0)
                st_obj = elem.get("status", {})
                if st_obj and st_obj.get("code") is not None:
                    dur, dist = float("inf"), float("inf")
                else:
                    dur_s = elem.get("duration", "0s")
                    try:
                        dur = float(str(dur_s).rstrip("s")) / 60.0
                    except ValueError:
                        dur = float("inf")
                    dist = float(elem.get("distanceMeters", 0)) / 1000.0
                results[dest_idx] = (dur, dist)
            for i in range(len(destinations)):
                dur, dist = results.get(i, (float("inf"), float("inf")))
                tiempos.append(dur)
                distancias_reales.append(dist)
        else:
            st.warning("⚠️ Google Maps Routes API no disponible. Usando distancias aéreas de respaldo.")
            st.info(
                "💡 Activa la **Routes API**:\n"
                "👉 https://console.developers.google.com/apis/api/routes.googleapis.com/overview"
            )
            tiempos = [float("inf")] * len(destinations)
            distancias_reales = [row["distancia_km"] for _, row in d_cercanas.iterrows()]

        d_cercanas["tiempo_viaje_min"] = tiempos
        d_cercanas["distancia_real_km"] = distancias_reales

        tiempos_est = []
        for _, row in d_cercanas.iterrows():
            t = row["tiempo_viaje_min"]
            if t == float("inf"):
                t = row["distancia_km"] * 2.0
            tiempos_est.append(t)

        d_cercanas["puntaje"] = d_cercanas[combustible] + (pd.Series(tiempos_est, index=d_cercanas.index) * 15)
        d_cercanas = d_cercanas.sort_values("puntaje")

        if len(d_cercanas) >= 1:
            best_option = d_cercanas.iloc[0].copy()
            if best_option["tiempo_viaje_min"] == float("inf"):
                best_option["tiempo_viaje_min"] = best_option["distancia_km"] * 2.0

        if len(d_cercanas) >= 2:
            second_best = d_cercanas.iloc[1].copy()
            if second_best["tiempo_viaje_min"] == float("inf"):
                second_best["tiempo_viaje_min"] = second_best["distancia_km"] * 2.0

        if best_option is not None:
            coords, dur, dist, route_err, route_label = get_route_polyline_v3(
                user_lat, user_lon,
                float(best_option["lat"]), float(best_option["lon"]),
                gmaps_key,
            )
            if coords:
                route_coords  = coords
                route_dur_min = dur
                route_dist_km = dist
            elif route_err:
                logging.info("Polyline unavailable: %s", route_err)

        zoom_level = 13
        center_lat, center_lon = user_lat, user_lon
    else:
        if comuna_sel != "Todas las Comunas":
            zoom_level = 11
        elif region_sel != "Todas las Regiones":
            zoom_level = 7
        else:
            zoom_level = 5
        center_lat = d["lat"].mean() if not d.empty else -33.45
        center_lon = d["lon"].mean() if not d.empty else -70.65

    if best_option is not None:
        if route_dur_min is not None:
            eta_str = f"~{int(route_dur_min)} min ({route_label})"
            if route_dist_km:
                eta_str = f"~{int(route_dur_min)} min · {route_dist_km:.1f} km ({route_label})"
        else:
            eta_str = f"~{int(best_option['tiempo_viaje_min'])} min (estimado)"

    return {
        "best_option": best_option,
        "second_best": second_best,
        "route_coords": route_coords,
        "route_dur_min": route_dur_min,
        "route_dist_km": route_dist_km,
        "route_label": route_label,
        "eta_str": eta_str,
        "zoom_level": zoom_level,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "has_user": user_lat is not None and user_lon is not None,
        "best_codigo": best_option["codigo_estacion"] if best_option is not None else None,
        "second_codigo": second_best["codigo_estacion"] if second_best is not None else None,
    }


def construir_mapa_folium(d, combustible, fondo_mapa, user_lat, user_lon, opcion):
    vmin = float(d[combustible].min())
    vmax = float(d[combustible].max())

    tiles_url, tiles_attr = FONDOS_MAPA[fondo_mapa]
    if tiles_url is None:
        m = folium.Map(location=[opcion["center_lat"], opcion["center_lon"]],
                        zoom_start=opcion["zoom_level"], tiles="OpenStreetMap")
    else:
        m = folium.Map(location=[opcion["center_lat"], opcion["center_lon"]],
                        zoom_start=opcion["zoom_level"], tiles=None)
        folium.TileLayer(tiles=tiles_url, attr=tiles_attr, name=fondo_mapa).add_to(m)

    best_option = opcion["best_option"]
    second_best = opcion["second_best"]
    has_user = opcion["has_user"]

    if has_user:
        coords_to_fit = [[user_lat, user_lon]]
        if best_option is not None:
            coords_to_fit.append([float(best_option["lat"]), float(best_option["lon"])])
        if second_best is not None:
            coords_to_fit.append([float(second_best["lat"]), float(second_best["lon"])])
        if len(coords_to_fit) > 1:
            lats = [c[0] for c in coords_to_fit]
            lons = [c[1] for c in coords_to_fit]
            bbox = [[min(lats), min(lons)], [max(lats), max(lons)]]
            m.fit_bounds(bbox, padding_top_left=[40, 40], padding_bottom_right=[40, 40])

    colormap = bcm.LinearColormap(colors=GRADIENT_COLORS, vmin=vmin, vmax=vmax)

    if opcion["route_coords"]:
        folium.PolyLine(
            locations=opcion["route_coords"],
            color="#3B82F6", weight=5, opacity=0.82,
            tooltip=f"Ruta · {opcion['eta_str']}",
        ).add_to(m)

    best_codigo = opcion["best_codigo"]
    second_codigo = opcion["second_codigo"]

    for _, row in d.iterrows():
        precio = row[combustible]
        codigo = row.get("codigo_estacion")
        
        # Color basado en el gradiente de precios
        fill_color = colormap(precio)

        if codigo == best_codigo:
            # VERDE para la mejor opción (Ahorro)
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=11, color="#10B981", weight=3,
                fill=True, fill_color="#10B981", fill_opacity=0.95,
                popup=folium.Popup(
                    make_popup_html(
                        row, combustible, tag="best",
                        user_lat=user_lat, user_lon=user_lon,
                        tiempo_min=opcion["route_dur_min"] if opcion["route_dur_min"] else best_option.get("tiempo_viaje_min"),
                        distancia_km=opcion["route_dist_km"] if opcion["route_dist_km"] else best_option.get("distancia_real_km"),
                        traffic_label=opcion["route_label"] or "estimado",
                    ),
                    max_width=320,
                ),
                tooltip=f"Mejor Opción: {row['marca']} — {pesos(precio)}",
            ).add_to(m)
            
        elif codigo == second_codigo:
            # AMARILLO/ÁMBAR para la segunda opción (Alternativa)
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=10, color="#FBBF24", weight=3,
                fill=True, fill_color="#FBBF24", fill_opacity=0.95,
                popup=folium.Popup(
                    make_popup_html(
                        row, combustible, tag="second",
                        user_lat=user_lat, user_lon=user_lon,
                        tiempo_min=second_best.get("tiempo_viaje_min"),
                        distancia_km=second_best.get("distancia_real_km"),
                        traffic_label="estimado",
                    ),
                    max_width=320,
                ),
                tooltip=f"Segunda Opción: {row['marca']} — {pesos(precio)}",
            ).add_to(m)
            
        else:
            # Estaciones normales siguen el gradiente de precios
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=5, color="#374151", weight=1,
                fill=True, fill_color=fill_color, fill_opacity=0.6,
                popup=folium.Popup(
                    make_popup_html(row, combustible, user_lat=user_lat, user_lon=user_lon),
                    max_width=300,
                ),
                tooltip=f"{row['marca']} — {pesos(precio)}",
            ).add_to(m)

    if has_user:
        folium.Marker(
            location=[user_lat, user_lon],
            icon=folium.DivIcon(
                html=(
                    '<div style="background:#3B82F6;width:18px;height:18px;'
                    'border-radius:50%;border:3px solid #FFFFFF;'
                    'box-shadow:0 0 8px rgba(0,0,0,0.45);"></div>'
                ),
                icon_size=(24, 24),
                icon_anchor=(12, 12),
            ),
            tooltip="Tu Ubicación",
        ).add_to(m)

    return m, vmin, vmax


# ═══════════════════════════════════════════════════════════════════
# KPIs
# ═══════════════════════════════════════════════════════════════════

def render_kpis(d, combustible):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estaciones Encontradas", f"{len(d):,}".replace(",", "."))
    c2.metric("Precio Promedio", pesos(d[combustible].mean()))
    c3.metric("Precio Mínimo", pesos(d[combustible].min()))
    c4.metric("Precio Máximo", pesos(d[combustible].max()))


# ═══════════════════════════════════════════════════════════════════
# Mapa de decisión: Precio vs. Distancia + frontera de Pareto
# ═══════════════════════════════════════════════════════════════════

def calcular_frontera_pareto(d, combustible, user_lat, user_lon):
    dd = d.dropna(subset=[combustible]).copy()
    dd["distancia_km"] = dd.apply(
        lambda row: geodesic((user_lat, user_lon), (row["lat"], row["lon"])).km, axis=1
    )
    dd = dd.sort_values(["distancia_km", combustible]).reset_index(drop=True)

    min_precio = float("inf")
    en_frontera = []
    for precio in dd[combustible]:
        if precio < min_precio:
            en_frontera.append(True)
            min_precio = precio
        else:
            en_frontera.append(False)
    dd["en_frontera"] = en_frontera
    return dd

def render_scatter_pareto(d, combustible, contexto_lugar, user_lat, user_lon):
    st.subheader(f":material/radar: Mapa de decisión: {combustible} vs. distancia {contexto_lugar}")

    if user_lat is None or user_lon is None:
        # Usamos st.markdown pero con una estructura que Streamlit sí reconoce
        st.markdown("""
        <div style="
            background-color: #1F2937; 
            border: 1px solid #374151; 
            border-left: 5px solid #FBBF24; 
            border-radius: 12px; 
            padding: 20px;
            color: #E5E7EB;
            margin-bottom: 20px;
        ">
            <p style="margin: 0; font-size: 0.95rem; font-family: 'Inter', sans-serif;">
                Activa tu GPS o ingresa una dirección en el panel de la izquierda para ver qué estaciones realmente conviene considerar según precio y distancia.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    dd = calcular_frontera_pareto(d, combustible, user_lat, user_lon)
    dominadas = dd[~dd["en_frontera"]]
    frontera = dd[dd["en_frontera"]]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dominadas["distancia_km"], y=dominadas[combustible],
        mode="markers",
        marker=dict(color="#4B5563", size=7, opacity=0.45),
        name="Dominadas (hay otra más barata y más cerca)",
        customdata=dominadas[["marca", "direccion", "comuna"]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>%{customdata[1]}, %{customdata[2]}<br>"
            "Precio: $%{y:,.0f}<br>Distancia: %{x:.1f} km<extra></extra>"
        ),
    ))

    fig.add_trace(go.Scatter(
        x=frontera["distancia_km"], y=frontera[combustible],
        mode="lines+markers+text",
        line=dict(shape="spline", smoothing=1.0, color="#10B981", width=2, dash="dot"),
        marker=dict(color="#10B981", size=12, line=dict(color="#111827", width=2)),
        text=frontera["marca"], textposition="top center",
        name="Frontera de opciones convenientes",
        customdata=frontera[["marca", "direccion", "comuna"]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>%{customdata[1]}, %{customdata[2]}<br>"
            "Precio: $%{y:,.0f}<br>Distancia: %{x:.1f} km<extra></extra>"
        ),
    ))

    # Transparente para que adopte el fondo del dot grid
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB", family="Inter"),
        xaxis_title="Distancia desde tu ubicación (km)",
        yaxis_title=f"Precio {combustible} ($)",
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#374151"),
        xaxis=dict(gridcolor="#374151"),
        height=480,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.12),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"**{len(frontera)}** de {len(dd)} estaciones forman la frontera: ninguna otra es a la "
        "vez más barata y más cercana. El resto está \"dominado\" — siempre existe una mejor opción."
    )

def render_comparativa_distribuidor(d, combustible, contexto_lugar):
    st.subheader(f":material/storefront: Comparativa por Distribuidor {contexto_lugar}")
    marca = (d.groupby("marca")[combustible]
               .agg(precio="mean", estaciones="count").reset_index())
    limite_estaciones = 3 if len(d) > 20 else 1
    marca = marca[marca["estaciones"] >= limite_estaciones].sort_values("precio")

    if not marca.empty:
        fig_marca = px.bar(
            marca, x="precio", y="marca", orientation="h",
            color="precio", color_continuous_scale="RdYlGn_r",
            hover_data={"estaciones": True, "precio": ":$,.0f"},
            labels={"precio": "Precio promedio ($)", "marca": ""}, height=350,
        )
        fig_marca.update_layout(
            coloraxis_showscale=False, 
            margin=dict(l=0, r=60, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB", family="Inter")
        )
        estilizar_barra_precio(fig_marca, marca["precio"])
        st.plotly_chart(fig_marca, use_container_width=True)
        if limite_estaciones > 1:
            st.caption(f"*Mostrando marcas con {limite_estaciones} o más estaciones en la zona filtrada.")


# ═══════════════════════════════════════════════════════════════════
# Chatbot
# ═══════════════════════════════════════════════════════════════════

def render_chatbot(d_filtros, contexto_lugar):
    # CSS idéntico al Hero Banner, pero en Azul (#3B82F6)
    st.markdown("""
        <style>
            /* 1. Contenedor Base: Sombra interna (inset) y degradado oscuro */
            div[data-testid="stColumn"]:has(#chatbot-anchor) {
                background: linear-gradient(135deg, #111827 0%, #1F2937 100%);
                border: 1px solid #374151;
                border-left: 5px solid #3B82F6; /* Acento Azul */
                border-radius: 16px;
                padding: 1.5rem;
                /* Sombra interna para efecto "hundido" + sombra externa suave */
                box-shadow: inset 0 4px 15px rgba(0, 0, 0, 0.4), 0 10px 20px -5px rgba(0, 0, 0, 0.3);
                position: sticky;
                top: 1rem;
                align-self: flex-start;
                transition: all 0.2s ease;
                overflow: hidden; /* Esencial para que las texturas no se salgan */
                z-index: 1;
            }

            /* 3. Resplandor radial en la esquina superior derecha */
            div[data-testid="stColumn"]:has(#chatbot-anchor)::after {
                content: "";
                position: absolute;
                top: -50px; right: -50px;
                width: 200px; height: 200px;
                background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
                border-radius: 50%;
                pointer-events: none;
                z-index: -1;
            }
            
            /* 4. Efecto Hover: Intensifica el azul y la sombra externa */
            div[data-testid="stColumn"]:has(#chatbot-anchor):hover {
                border-left-color: #60A5FA;
                transform: translateY(-2px);
                box-shadow: inset 0 4px 15px rgba(0, 0, 0, 0.4), 0 15px 25px -5px rgba(0, 0, 0, 0.4);
            }
            
            div[data-testid="stChatMessage"] {
                font-family: 'Inter', sans-serif !important;
            }
        </style>
        <div id="chatbot-anchor"></div>
    """, unsafe_allow_html=True)

    st.subheader(":material/smart_toy: Asistente Virtual")
    st.markdown(
        f"<small style='color: #9CA3AF;'>Hablemos sobre los datos actuales **{contexto_lugar}**. ¡Pregúntame con confianza!</small>",
        unsafe_allow_html=True,
    )

    google_api_key = obtener_google_api_key()

    if not google_api_key:
        st.warning("Configura GOOGLE_API_KEY en secrets.toml")
        return

    cliente = genai.Client(api_key=google_api_key)

    if "mensajes_chat" not in st.session_state:
        st.session_state.mensajes_chat = []

    chat_container = st.container(height=400)

    with chat_container:
        for mensaje in st.session_state.mensajes_chat:
            with st.chat_message(mensaje["rol"]):
                st.markdown(mensaje["contenido"])

        st.write("")

        if len(st.session_state.mensajes_chat) == 0:
            with st.chat_message("assistant"):
                st.markdown("¡Hola! Te recomiendo **usar los filtros de la izquierda** primero para elegir tu zona. Luego, puedes escribirme o elegir una de estas preguntas frecuentes:")

        sugerencia = None

        if st.button(":material/local_gas_station: ¿Dónde están las bencinas más baratas? (93, 95 y 97)", use_container_width=True):
            sugerencia = "Dime cuál es el servicentro más barato para Gasolina 93, el más barato para 95 y el más barato para 97 en la zona seleccionada. Incluye dirección, marca y precio exacto."

        if st.button(":material/block: ¿Cuáles son las estaciones más caras para evitarlas?", use_container_width=True):
            sugerencia = "Revisa los datos actuales y hazme un Top 3 de los servicentros con los precios más altos en esta zona (considerando bencinas) para saber dónde NO ir."

        if st.button(":material/storefront: ¿Qué marca o distribuidor me conviene más por aquí?", use_container_width=True):
            sugerencia = "De forma breve, analiza la zona y dime qué marca (ej. Copec, Shell, Petrobras o Sin Bandera) tiene opciones más convenientes. Recomiéndame la mejor estación de esa marca."

        if st.button(":material/summarize: Hazme un resumen rápido de los precios", use_container_width=True):
            sugerencia = "Hazme un resumen rápido y amigable de cómo están los precios de los combustibles en esta zona específica: menciona el rango de precios y la opción más económica en general."

    pregunta_input = st.chat_input("O escribe tu propia pregunta aquí...")
    pregunta = sugerencia or pregunta_input

    if pregunta:
        st.session_state.mensajes_chat.append({"rol": "user", "contenido": pregunta})
        with chat_container.chat_message("user"):
            st.markdown(pregunta)

        with chat_container.chat_message("assistant"):
            LIMITE_FILAS = 600

            if len(d_filtros) > LIMITE_FILAS:
                msg_bloqueo = f"⚠️ Actualmente hay **{len(d_filtros)}** estaciones cargadas. Para evitar un consumo excesivo y darte una respuesta precisa, selecciona una **Región** o **Comuna** en la izquierda."
                st.warning(msg_bloqueo)
                st.session_state.mensajes_chat.append({"rol": "assistant", "contenido": msg_bloqueo})
            else:
                with st.spinner("Analizando estaciones de la zona..."):
                    try:
                        columnas_ia = ['region', 'comuna', 'direccion', 'marca', 'Gasolina 93', 'Gasolina 95', 'Gasolina 97', 'Diésel', 'Kerosene']
                        cols_validas = [c for c in columnas_ia if c in d_filtros.columns]

                        d_ia = d_filtros[cols_validas].copy()

                        combustibles_disp = [c for c in ['Gasolina 93', 'Gasolina 95', 'Gasolina 97', 'Diésel', 'Kerosene'] if c in d_ia.columns]
                        d_ia = d_ia.dropna(subset=combustibles_disp, how='all')

                        datos_texto = d_ia.fillna("").to_csv(index=False)

                        INSTRUCCIONES = f"""
                        Eres un asistente experto en combustibles de Chile.

                        BASE DE DATOS ACTUAL COHERENTE CON EL DASHBOARD ({contexto_lugar}):
                        {datos_texto}

                        REGLAS ESTRICTAS DE OPTIMIZACIÓN (CERO REPREGUNTAS):
                        1. IGNORA EL CONTEXTO PREVIO: Trata esta consulta como única y asume la zona geográfica entregada.
                        2. RESPUESTA EXHAUSTIVA Y ANTICIPATORIA: Si te preguntan por barato/caro, entrega de inmediato un TOP 3 en formato lista con marca, comuna, dirección y precio ($1.250).
                        3. DIRECTO AL GRANO: Sin introducciones robóticas ni explicaciones del código.
                        4. DICCIONARIO SEMÁNTICO:
                           - "bencina" = Gasolina. Si no especifican octanaje, entrega el Top 1 de la más económica para 93, 95 y 97 consecutivamente.
                           - "petróleo" = Diésel.
                           - "parafina" = Kerosene.
                        """

                        respuesta = cliente.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=pregunta,
                            config=types.GenerateContentConfig(
                                system_instruction=INSTRUCCIONES,
                                temperature=0.1
                            )
                        )

                        texto_final = respuesta.text
                        st.markdown(texto_final)
                        st.session_state.mensajes_chat.append({"rol": "assistant", "contenido": texto_final})

                    except Exception as e:
                        error_str = str(e)
                        if "503" in error_str or "high demand" in error_str.lower():
                            error_msg = "⏳ Las antenas de Google están bajo alta demanda en este instante. ¡Reintenta tu pregunta en unos segundos!"
                        elif "429" in error_str or "exhausted" in error_str.lower():
                            error_msg = "🛑 ¡Wow, vas muy rápido! El satélite necesita enfriarse un poco. Por favor, espera un minuto antes de hacer otra consulta."
                        else:
                            error_msg = f"Error técnico de enlace: `{e}`"

                        st.error(error_msg)
                        st.session_state.mensajes_chat.append({"rol": "assistant", "contenido": error_msg})
