"""
appV3.py — Dashboard de Precios de Combustibles en Chile
Google Maps de fondo (Folium) + Ruta trazada + Pines SVG + Leyenda externa
"""

import os
import logging
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
import folium
import branca.colormap as bcm
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from geopy.distance import geodesic

# ═══════════════════════════════════════════════════════════════════
# Configuración de página
# ═══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Precios de Combustibles · Chile",
    page_icon="⛽",
    layout="wide",
)

st.markdown(
    """
    <style>
        /* Hacer transparente el header base */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
        }
        
        /* Ocultar botones y menús del header por defecto, revelar al pasar el mouse (excepto lo que esté dentro de stStatusWidget) */
        header[data-testid="stHeader"] button:not([data-testid="stStatusWidget"] *),
        header[data-testid="stHeader"] a:not([data-testid="stStatusWidget"] *) {
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }
        header[data-testid="stHeader"]:hover button:not([data-testid="stStatusWidget"] *),
        header[data-testid="stHeader"]:hover a:not([data-testid="stStatusWidget"] *) {
            opacity: 1;
        }

        /* Cuando el status widget (Running) está activo, crear un fondo difuminado en toda la pantalla */
        div[data-testid="stStatusWidget"]::before {
            content: "" !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            background-color: rgba(0, 0, 0, 0.25) !important; /* tono gris oscuro */
            backdrop-filter: blur(2px) !important;
            z-index: -99999 !important; /* se coloca detrás del indicador y del header, pero cubre el resto del body */
            pointer-events: none !important;
        }

        /* Ajustar margen del contenido para ganar espacio vertical */
        .block-container {
            padding-top: 2rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

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

# Paleta RdYlGn_r — verde=barato → rojo=caro
GRADIENT_COLORS = [
    "#1a9850", "#66bd63", "#a6d96a", "#d9ef8b",
    "#fee08b", "#fdae61", "#f46d43", "#d73027",
]


# ═══════════════════════════════════════════════════════════════════
# Utilidades generales
# ═══════════════════════════════════════════════════════════════════

def obtener_gmaps_key():
    try:
        return st.secrets["GoogleMapsAPI"]
    except Exception:
        return os.environ.get("GoogleMapsAPI")


def pesos(x):
    try:
        return f"${x:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "N/A"


def decode_polyline(encoded):
    """Decodifica la polilínea codificada de Google Maps → lista de (lat, lon)."""
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


def svg_pin_html(stroke="#15803d", fill="rgba(255,255,255,0.18)", w=30, h=44):
    """Retorna el HTML de un pin SVG tipo teardrop (punta abajo)."""
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 30 44" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<path d="M15 0C6.716 0 0 6.716 0 15c0 11.25 15 29 15 29S30 26.25 30 15C30 6.716 23.284 0 15 0z" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="3"/>'
        f'<circle cx="15" cy="15" r="5" fill="{stroke}"/>'
        f'</svg>'
    )


# ═══════════════════════════════════════════════════════════════════
# Carga de datos (cacheada)
# ═══════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Cargando estaciones desde el dataset local...")
def cargar_datos():
    csv_path = "data/dataset_limpio.csv"
    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), "data", "dataset_limpio.csv")

    df_raw = pd.read_csv(csv_path, encoding="utf-8-sig")
    df_raw.columns = df_raw.columns.str.replace("^\ufeff+", "", regex=True)

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
# API: Geocodificación
# ═══════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner="Geocodificando dirección...")
def geocode_address_v3(address, api_key):
    """Retorna (lat, lon, error_msg, error_code). Función pura — sin st.*."""
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


# ═══════════════════════════════════════════════════════════════════
# API: Matriz de rutas (para seleccionar mejor opción)
# ═══════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner="Calculando tiempos de viaje...")
def get_route_matrix_v3(origin_lat, origin_lon, destinations, api_key):
    """Retorna respuesta JSON de computeRouteMatrix o None."""
    url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status",
    }
    origins = [
        {"waypoint": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lon}}}}
    ]
    dests = [
        {"waypoint": {"location": {"latLng": {"latitude": la, "longitude": lo}}}}
        for la, lo in destinations[:25]
    ]
    try:
        r = requests.post(
            url,
            json={"origins": origins, "destinations": dests, "travelMode": "DRIVE"},
            headers=headers, timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logging.warning("Route matrix failed: %s", exc)
        return None


# ═══════════════════════════════════════════════════════════════════
# API: Ruta con polilínea + ETA con tráfico
# ═══════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner="Trazando ruta con tráfico...")
def get_route_polyline_v3(origin_lat, origin_lon, dest_lat, dest_lon, api_key):
    """
    Llama a computeRoutes y retorna (coords, dur_min, dist_km, error_msg).
    Usa TRAFFIC_AWARE para ETA real; cae a DRIVE_UNSPECIFIED si falla.
    """
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "routes.polyline.encodedPolyline,"
            "routes.duration,"
            "routes.distanceMeters"
        ),
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
# HTML: Popup de marcador
# ═══════════════════════════════════════════════════════════════════

def make_popup_html(row, combustible, tag=None,
                    user_lat=None, user_lon=None,
                    tiempo_min=None, distancia_km=None, traffic_label=""):
    precio_str = pesos(row.get(combustible, 0))

    tag_html = ""
    if tag == "best":
        tag_html = (
            '<div style="background:#15803d;color:#fff;padding:4px 10px;border-radius:5px;'
            'font-weight:700;font-size:12px;margin-bottom:8px;text-align:center;">'
            '🌟 Mejor Opción</div>'
        )
    elif tag == "second":
        tag_html = (
            '<div style="background:#dc2626;color:#fff;padding:4px 10px;border-radius:5px;'
            'font-weight:700;font-size:12px;margin-bottom:8px;text-align:center;">'
            '⭐ Segunda Opción</div>'
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
            trip_info = (
                f'<div style="font-size:11px;color:#555;margin-top:5px;text-align:center;">'
                f"{d_str}~{int(tiempo_min)} min ({traffic_label})</div>"
            )
        route_html = f"""
        {trip_info}
        <div style="margin-top:7px;text-align:center;">
            <a href="{gm_url}" target="_blank"
               style="display:inline-block;background:#4285f4;color:#fff;
                      padding:6px 14px;border-radius:6px;text-decoration:none;
                      font-size:12px;font-weight:600;">
                📍 Abrir ruta en Google Maps
            </a>
        </div>"""

    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;min-width:240px;padding:3px;">
        {tag_html}
        <h4 style="margin:0 0 8px 0;color:#111;font-size:15px;">{row.get("marca","N/A")}</h4>
        <table style="font-size:13px;line-height:1.75;width:100%;border-collapse:collapse;">
            <tr>
                <td style="font-weight:600;color:#555;padding-right:10px;white-space:nowrap;">
                    Comuna:</td>
                <td style="color:#111;">{row.get("comuna","N/A")}</td>
            </tr>
            <tr>
                <td style="font-weight:600;color:#555;padding-right:10px;white-space:nowrap;">
                    Dirección:</td>
                <td style="color:#111;">{row.get("direccion","N/A")}</td>
            </tr>
            <tr>
                <td style="font-weight:600;color:#555;padding-right:10px;white-space:nowrap;">
                    Precio:</td>
                <td style="font-weight:700;font-size:14px;color:#111;">{precio_str}</td>
            </tr>
        </table>
        {route_html}
    </div>"""


# ═══════════════════════════════════════════════════════════════════
# HTML: Leyenda lateral externa
# ═══════════════════════════════════════════════════════════════════

def make_legend_html(vmin, vmax, combustible, has_user):
    # Gradiente de colores — rojo arriba (caro) → verde abajo (barato)
    grad = ", ".join(reversed(GRADIENT_COLORS))

    # Mini ícono SVG para pines en la leyenda
    def mini_circle_svg(stroke):
        return (
            f'<svg width="14" height="14" viewBox="0 0 14 14" xmlns="http://www.w3.org/2000/svg">'
            f'<circle cx="7" cy="7" r="6" fill="transparent" stroke="{stroke}" stroke-width="2"/>'
            f'</svg>'
        )

    # Íconos de marcadores (solo se muestran si hay ubicación activa)
    markers_html = ""
    if has_user:
        user_icon = (
            '<svg width="14" height="14" viewBox="0 0 14 14" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="7" cy="7" r="6" fill="#00C0FF" stroke="black" stroke-width="2"/>'
            '</svg>'
        )
        markers_html = f"""
        <div style="margin-top:18px;border-top:1px solid #ddd;padding-top:12px;">
            <p style="font-weight:700;font-size:11px;margin:0 0 10px 0;
                      color:#333;text-transform:uppercase;letter-spacing:.5px;">
                Marcadores
            </p>
            <div style="display:flex;align-items:center;gap:7px;margin-bottom:9px;">
                {user_icon}
                <span style="font-size:11px;color:#333;line-height:1.2;">Tu<br>Ubicación</span>
            </div>
            <div style="display:flex;align-items:center;gap:7px;margin-bottom:9px;">
                {mini_circle_svg("#15803d")}
                <span style="font-size:11px;color:#333;line-height:1.2;">Mejor<br>Opción</span>
            </div>
            <div style="display:flex;align-items:center;gap:7px;">
                {mini_circle_svg("#dc2626")}
                <span style="font-size:11px;color:#333;line-height:1.2;">Segunda<br>Opción</span>
            </div>
        </div>"""

    import textwrap
    return textwrap.dedent(f"""
    <div style="
        font-family:'Segoe UI',Arial,sans-serif;
        padding:14px 10px;
        background:#fafafa;
        border:1px solid #e0e0e0;
        border-radius:10px;
        height:620px;
        box-sizing:border-box;
        display:flex;
        flex-direction:column;
    ">
        <p style="font-weight:700;font-size:12px;margin:0 0 10px 0;
                  color:#222;text-transform:uppercase;letter-spacing:.5px;">
            Precio<br>{combustible}
        </p>

        <!-- Barra de gradiente + etiquetas -->
        <div style="display:flex;align-items:stretch;gap:7px;flex:1;min-height:0;">
            <div style="
                width:20px;
                border-radius:6px;
                background:linear-gradient(to bottom, {grad});
                flex-shrink:0;
            "></div>
            <div style="
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                font-size:10px;
                color:#444;
                padding:2px 0;
            ">
                <div style="font-weight:700;line-height:1.3;color:#c0392b;">
                    {pesos(vmax)}<br>
                    <span style="font-weight:400;font-size:9px;">más caro</span>
                </div>
                <div style="font-weight:700;line-height:1.3;color:#1a9850;">
                    {pesos(vmin)}<br>
                    <span style="font-weight:400;font-size:9px;">más barato</span>
                </div>
            </div>
        </div>

        {markers_html}
    </div>""")


# ═══════════════════════════════════════════════════════════════════
# INTERFAZ PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

st.title("⛽ Precios de Combustibles en Chile")
st.caption("Datos locales (18-06-2026) · dataset_limpio.csv")

gmaps_key = obtener_gmaps_key()
if not gmaps_key:
    st.warning(
        "Falta `GoogleMapsAPI` en `.streamlit/secrets.toml`. "
        "Las funciones de ruteo y recomendación estarán deshabilitadas."
    )

try:
    df = cargar_datos()
except Exception as exc:
    st.error(f"No se pudieron cargar los datos: {exc}")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────
st.sidebar.header("Filtros")
combustible = st.sidebar.selectbox("Combustible", list(COMBUSTIBLES.keys()))

st.sidebar.divider()
st.sidebar.subheader("📍 Tu Ubicación")

with st.sidebar:
    col_gps, col_text = st.columns([1, 4])
    with col_gps:
        location = streamlit_geolocation()
    with col_text:
        address_input = st.text_input(
            "Dirección",
            label_visibility="collapsed",
            placeholder="Escribe dirección...",
        )

# ── Geocodificación ──────────────────────────────────────────────
user_lat, user_lon = None, None

if address_input and gmaps_key:
    lat, lon, err_msg, err_code = geocode_address_v3(address_input, gmaps_key)
    if err_msg:
        st.warning(f"⚠️ {err_msg}")
        if err_code == "REQUEST_DENIED":
            st.info(
                "💡 Activa la **Geocoding API**:\n"
                "👉 https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com"
            )
    else:
        user_lat, user_lon = lat, lon
elif location and location.get("latitude") and location.get("longitude"):
    user_lat = location["latitude"]
    user_lon = location["longitude"]

# ── Filtrar por combustible ──────────────────────────────────────
d = df.dropna(subset=[combustible]).copy()

# ── Lógica de mejores opciones ───────────────────────────────────
best_option   = None
second_best   = None
route_coords  = []
route_dur_min = None
route_dist_km = None
route_label   = ""

if user_lat and user_lon and gmaps_key:
    d["distancia_km"] = d.apply(
        lambda row: geodesic((user_lat, user_lon), (row["lat"], row["lon"])).km, axis=1
    )
    d_cercanas = d.nsmallest(20, "distancia_km").copy()
    destinations = [(row["lat"], row["lon"]) for _, row in d_cercanas.iterrows()]
    matrix = get_route_matrix_v3(user_lat, user_lon, destinations, gmaps_key)

    tiempos, distancias_reales = [], []

    # Validar respuesta de la matriz
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

    d_cercanas["tiempo_viaje_min"]   = tiempos
    d_cercanas["distancia_real_km"] = distancias_reales

    # Puntaje = precio + tiempo * penalización
    tiempos_est = []
    for _, row in d_cercanas.iterrows():
        t = row["tiempo_viaje_min"]
        if t == float("inf"):
            t = row["distancia_km"] * 2.0
        tiempos_est.append(t)

    d_cercanas["puntaje"] = d_cercanas[combustible] + (
        pd.Series(tiempos_est, index=d_cercanas.index) * 15
    )
    d_cercanas = d_cercanas.sort_values("puntaje")

    if len(d_cercanas) >= 1:
        best_option = d_cercanas.iloc[0].copy()
        if best_option["tiempo_viaje_min"] == float("inf"):
            best_option["tiempo_viaje_min"] = best_option["distancia_km"] * 2.0

    if len(d_cercanas) >= 2:
        second_best = d_cercanas.iloc[1].copy()
        if second_best["tiempo_viaje_min"] == float("inf"):
            second_best["tiempo_viaje_min"] = second_best["distancia_km"] * 2.0

    # Obtener polilínea real + ETA con tráfico para la mejor opción
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
    regiones = sorted(df["region"].dropna().unique())
    sel_regiones = st.sidebar.multiselect("Región", regiones, default=regiones)
    d = d[d["region"].isin(sel_regiones)].copy()

    zoom_level = 5
    center_lat = d["lat"].mean() if not d.empty else -33.45
    center_lon = d["lon"].mean() if not d.empty else -70.65

with st.sidebar.expander("🗺️ Fondo del mapa", expanded=False):
    fondo_mapa = st.selectbox(
        "Fondo del mapa", list(FONDOS_MAPA.keys()), index=0, label_visibility="collapsed"
    )

if d.empty:
    st.warning("No hay estaciones con ese combustible en la selección.")
    st.stop()

has_user     = user_lat is not None and user_lon is not None
best_codigo  = best_option["codigo_estacion"]  if best_option  is not None else None
second_codigo= second_best["codigo_estacion"] if second_best   is not None else None

# ── KPIs ─────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Estaciones en vista", f"{len(d):,}".replace(",", "."))
c2.metric("Precio promedio",     pesos(d[combustible].mean()))
c3.metric("Más barato",          pesos(d[combustible].min()))
c4.metric("Más caro",            pesos(d[combustible].max()))

# ── Recomendaciones ──────────────────────────────────────────────
if best_option is not None:
    # ETA preferida: la de la polilínea (con tráfico); fallback a la del matrix
    if route_dur_min is not None:
        eta_str = f"~{int(route_dur_min)} min ({route_label})"
        if route_dist_km:
            eta_str = f"~{int(route_dur_min)} min · {route_dist_km:.1f} km ({route_label})"
    else:
        eta_str = f"~{int(best_option['tiempo_viaje_min'])} min (estimado)"

    st.success(
        f"**🌟 Mejor Opción:** {best_option['marca']} — {best_option['direccion']} "
        f"| {pesos(best_option[combustible])} | {eta_str}"
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
        f"| {pesos(second_best[combustible])} "
        f"| ~{int(second_best['tiempo_viaje_min'])} min (estimado)"
    )

st.divider()

# ═══════════════════════════════════════════════════════════════════
# MAPA + LEYENDA LATERAL
# ═══════════════════════════════════════════════════════════════════
st.subheader(f"🗺️ Mapa de precios · {combustible}")

vmin = float(d[combustible].min())
vmax = float(d[combustible].max())

map_col, legend_col = st.columns([5, 1])

# ── Leyenda lateral (derecha) ────────────────────────────────────
with legend_col:
    st.components.v1.html(
        make_legend_html(vmin, vmax, combustible, has_user),
        height=640,
    )

# ── Mapa Folium (izquierda) ──────────────────────────────────────
with map_col:
    tiles_url, tiles_attr = FONDOS_MAPA[fondo_mapa]
    if tiles_url is None:
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_level,
            tiles="OpenStreetMap",
        )
    else:
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_level,
            tiles=None,
        )
        folium.TileLayer(
            tiles=tiles_url,
            attr=tiles_attr,
            name=fondo_mapa,
        ).add_to(m)

    # ── Ajustar Zoom Dinámico (fit_bounds) ────────────────────────
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

    # Colormap para asignar colores a los círculos
    colormap = bcm.LinearColormap(
        colors=GRADIENT_COLORS, vmin=vmin, vmax=vmax
    )

    # ── Ruta trazada (polilínea azul) ────────────────────────────
    if route_coords:
        folium.PolyLine(
            locations=route_coords,
            color="#4285f4",
            weight=5,
            opacity=0.82,
            tooltip=f"Ruta · {eta_str if best_option is not None else ''}",
        ).add_to(m)

    # ── Marcadores de estaciones ─────────────────────────────────
    for _, row in d.iterrows():
        precio = row[combustible]
        codigo = row.get("codigo_estacion")
        fill_color = colormap(precio)

        if codigo == best_codigo:
            # Círculo verde relleno del color de su precio (más grande)
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=11,
                color="#15803d",
                weight=3,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.95,
                popup=folium.Popup(
                    make_popup_html(
                        row, combustible, tag="best",
                        user_lat=user_lat, user_lon=user_lon,
                        tiempo_min=route_dur_min if route_dur_min else best_option.get("tiempo_viaje_min"),
                        distancia_km=route_dist_km if route_dist_km else best_option.get("distancia_real_km"),
                        traffic_label=route_label or "estimado",
                    ),
                    max_width=320,
                ),
                tooltip=f"🌟 {row['marca']} — {pesos(precio)}",
            ).add_to(m)

        elif codigo == second_codigo:
            # Círculo rojo relleno del color de su precio (mediano)
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=8,
                color="#dc2626",
                weight=2.5,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.85,
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
                tooltip=f"⭐ {row['marca']} — {pesos(precio)}",
            ).add_to(m)

        else:
            # CircleMarker para estaciones regulares (más eficiente que DivIcon para 1000+ pts)
            r_size   = 4  if has_user else 5
            f_opac   = 0.35 if has_user else 0.75
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=r_size,
                color="#222",
                weight=1,
                fill=True,
                fill_color=fill_color,
                fill_opacity=f_opac,
                popup=folium.Popup(
                    make_popup_html(
                        row, combustible,
                        user_lat=user_lat, user_lon=user_lon,
                    ),
                    max_width=300,
                ),
                tooltip=f"{row['marca']} — {pesos(precio)}",
            ).add_to(m)

    # ── Marcador de ubicación del usuario ────────────────────────
    if has_user:
        folium.Marker(
            location=[user_lat, user_lon],
            icon=folium.DivIcon(
                html=(
                    '<div style="'
                    "background:#00C0FF;"
                    "width:18px;height:18px;"
                    "border-radius:50%;"
                    "border:3px solid black;"
                    "box-shadow:0 0 8px rgba(0,0,0,0.45);"
                    '"></div>'
                ),
                icon_size=(24, 24),
                icon_anchor=(12, 12),
            ),
            tooltip="📍 Tu Ubicación",
        ).add_to(m)

    st_folium(
        m,
        use_container_width=True,
        height=620,
        returned_objects=[],
    )

# ═══════════════════════════════════════════════════════════════════
# RANKING DE COMUNAS
# ═══════════════════════════════════════════════════════════════════
@st.fragment
def render_ranking_comunas(d_df, combustible_name):
    st.subheader(f"🏆 Ranking de comunas · {combustible_name}")
    col_a, col_b = st.columns(2)
    orden = col_a.radio("Mostrar", ["Más baratas", "Más caras"], horizontal=True)
    topn  = col_b.slider("Cantidad de comunas", 5, 30, 15)

    asc  = orden == "Más baratas"
    rank = (
        d_df.groupby("comuna")[combustible_name]
        .mean()
        .sort_values(ascending=asc)
        .head(topn)
        .reset_index()
    )
    fig_rank = px.bar(
        rank.sort_values(combustible_name, ascending=not asc),
        x=combustible_name, y="comuna", orientation="h",
        color=combustible_name, color_continuous_scale="RdYlGn_r",
        labels={combustible_name: "Precio Promedio", "comuna": "Comuna"},
        height=500,
    )
    fig_rank.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
        separators=",.",
        xaxis=dict(tickprefix="$", tickformat=",.0f"),
    )
    st.plotly_chart(fig_rank, use_container_width=True)

render_ranking_comunas(d, combustible)

st.divider()
st.caption("Fuente: Comisión Nacional de Energía (CNE) · Proyecto SIC Coding & Programming")
