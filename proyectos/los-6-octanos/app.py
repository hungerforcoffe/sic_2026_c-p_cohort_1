"""
app.py — Dashboard de Precios de Combustibles en Chile
Datos en vivo de la Comisión Nacional de Energía (https://api.cne.cl).

Ejecutar:
    pip install -r requirements.txt
    streamlit run app.py

Credenciales: ver README (archivo .streamlit/secrets.toml).
"""
import os
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai
from google.genai import types

# --------------------------------------------------------------------------
# Configuración Inicial
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

# --------------------------------------------------------------------------
# Funciones de Conexión y Datos
# --------------------------------------------------------------------------
def obtener_credenciales():
    try:
        return st.secrets["CNE_EMAIL"], st.secrets["CNE_PASSWORD"]
    except Exception:
        return os.environ.get("CNE_EMAIL"), os.environ.get("CNE_PASSWORD")

def _login(email, password):
    r = requests.post(LOGIN_URL, data={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    datos = r.json()
    for k in ("token", "access_token", "jwt"):
        if isinstance(datos, dict):
            if k in datos:
                return datos[k]
            if isinstance(datos.get("data"), dict) and k in datos["data"]:
                return datos["data"][k]
    raise RuntimeError("No se pudo obtener el token desde /api/login.")

def _col(df, c):
    return df[c] if c in df.columns else pd.Series([pd.NA] * len(df), index=df.index)

@st.cache_data(ttl=1800, show_spinner="Cargando estaciones desde la CNE…")
def cargar_datos(email, password):
    token = _login(email, password)
    r = requests.get(ESTACIONES_URL, headers={"Authorization": f"Bearer {token}"}, timeout=120)
    r.raise_for_status()
    payload = r.json()
    lista = payload["data"] if isinstance(payload, dict) and "data" in payload else payload

    df = pd.json_normalize(lista)

    out = pd.DataFrame(index=df.index)
    out["marca"] = _col(df, "distribuidor.marca")
    out["region"] = _col(df, "ubicacion.nombre_region")
    out["comuna"] = _col(df, "ubicacion.nombre_comuna")
    out["direccion"] = _col(df, "ubicacion.direccion")
    out["lat"] = pd.to_numeric(_col(df, "ubicacion.latitud"), errors="coerce")
    out["lon"] = pd.to_numeric(_col(df, "ubicacion.longitud"), errors="coerce")

    for nombre, code in COMBUSTIBLES.items():
        out[nombre] = pd.to_numeric(_col(df, f"precios.{code}.precio"), errors="coerce")
        out[f"_fecha_{nombre}"] = _col(df, f"precios.{code}.fecha_actualizacion")

    out = out[out["lat"].between(-56, -17) & out["lon"].between(-110, -66)]
    return out.reset_index(drop=True)

def fig_mapa(d, combustible):
    kwargs = dict(
        lat="lat", lon="lon", color=combustible, hover_name="marca",
        hover_data={"comuna": True, "direccion": True,
                    combustible: ":$,.0f", "lat": False, "lon": False},
        color_continuous_scale="RdYlGn_r", zoom=3, height=600,
    )
    if hasattr(px, "scatter_map"):
        fig = px.scatter_map(d, map_style="open-street-map", **kwargs)
    else:
        fig = px.scatter_mapbox(d, **kwargs)
        fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), coloraxis_colorbar_title="Precio")
    return fig

def pesos(x):
    if pd.isna(x): return "$0"
    return f"${x:,.0f}".replace(",", ".")

# --------------------------------------------------------------------------
# Interfaz Principal y Autenticación
# --------------------------------------------------------------------------
st.title("⛽ Precios de Combustibles en Chile")
st.caption("Datos en vivo de la Comisión Nacional de Energía · api.cne.cl")
                    
email, password = obtener_credenciales()
if not email or not password:
    st.error(
        "Faltan las credenciales. Crea el archivo `.streamlit/secrets.toml` con:\n\n"
        '```\nCNE_EMAIL = "tu_correo"\nCNE_PASSWORD = "tu_clave"\n```'
    )
    st.stop()

try:
    df = cargar_datos(email, password)
except Exception as e:
    st.error(f"No se pudieron cargar los datos: {e}")
    st.stop()

# ==========================================================================
# 🎛️ BARRA LATERAL: UI/UX PREMIUM Y FILTROS EN CASCADA
# ==========================================================================
st.sidebar.markdown("### 🗺️ PANEL DE CONTROL")
st.sidebar.markdown("Usa estos filtros para explorar el mercado:")

# 1. Región
regiones = ["Todas las Regiones"] + sorted(df['region'].dropna().unique().tolist())
region_sel = st.sidebar.selectbox("📍 Selecciona una Región:", regiones)

if region_sel != "Todas las Regiones":
    df_region = df[df['region'] == region_sel]
else:
    df_region = df

# 2. Comuna
comunas = ["Todas las Comunas"] + sorted(df_region['comuna'].dropna().unique().tolist())
comuna_sel = st.sidebar.selectbox("🏙️ Selecciona una Comuna:", comunas)

# Filtro de datos maestros (d)
if region_sel != "Todas las Regiones" and comuna_sel == "Todas las Comunas":
    d = df[df['region'] == region_sel].copy()
    contexto_lugar = f"en la {region_sel}"
elif comuna_sel != "Todas las Comunas":
    d = df_region[df_region['comuna'] == comuna_sel].copy()
    contexto_lugar = f"en {comuna_sel}"
else:
    d = df.copy()
    contexto_lugar = "a Nivel Nacional"

st.sidebar.divider()

# 3. Combustible
lista_combustibles = list(COMBUSTIBLES.keys())
combustible = st.sidebar.selectbox("⛽ Combustible a analizar:", lista_combustibles)

st.sidebar.info(f"Análisis actual: **{combustible}** {contexto_lugar}")

# Dataset limpio solo para gráficos
d_graficos = d.dropna(subset=[combustible]).copy()

if d_graficos.empty:
    st.warning("No hay estaciones con ese combustible en la selección geográfica actual.")
    st.stop()

# ==========================================================================
# 📊 ESTRUCTURA PRINCIPAL: GRÁFICOS (IZQ) Y CHATBOT (DER)
# ==========================================================================
col_viz, col_chat = st.columns([7, 3], gap="large")

with col_viz:
    st.title(f"Análisis de {combustible}")
    st.markdown(f"Visualizando datos actualizados de los servicentros **{contexto_lugar}**.")
    
    fechas = pd.to_datetime(d_graficos[f"_fecha_{combustible}"], errors="coerce")
    if fechas.notna().any():
        st.caption(f"Última actualización de precios en la selección: **{fechas.max().date()}**")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estaciones Encontradas", f"{len(d_graficos):,}".replace(",", "."))
    c2.metric("Precio Promedio", pesos(d_graficos[combustible].mean()))
    c3.metric("Precio Mínimo", pesos(d_graficos[combustible].min()))
    c4.metric("Precio Máximo", pesos(d_graficos[combustible].max()))

    st.divider()

    st.subheader(f"🗺️ Mapa de Precios de {combustible} {contexto_lugar}")
    st.plotly_chart(fig_mapa(d_graficos, combustible), use_container_width=True)

    st.divider()

    col_a, col_b = st.columns(2)
    orden = col_a.radio("Criterio de orden:", ["Más baratas", "Más caras"], horizontal=True)
    topn = col_b.slider("Cantidad de registros a mostrar:", 5, 20, 10)
    asc = orden == "Más baratas"

    if comuna_sel == "Todas las Comunas":
        st.subheader(f"🏆 Comunas con {combustible} {orden} {contexto_lugar}")
        rank = (d_graficos.groupby("comuna")[combustible].mean()
                  .sort_values(ascending=asc).head(topn).reset_index())
        
        fig_rank = px.bar(
            rank.sort_values(combustible, ascending=not asc),
            x=combustible, y="comuna", orientation="h",
            color=combustible, color_continuous_scale="RdYlGn_r" if asc else "RdYlGn",
            labels={combustible: "Precio promedio ($)", "comuna": ""}, height=400,
        )
        fig_rank.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_rank, use_container_width=True)
            
    else:
        st.subheader(f"⛽ Servicentros {orden} en {comuna_sel} ({combustible})")
        rank_estaciones = d_graficos.sort_values(by=combustible, ascending=asc).head(topn).copy()
        rank_estaciones['etiqueta'] = rank_estaciones['marca'] + " - " + rank_estaciones['direccion']
        
        fig_estaciones = px.bar(
            rank_estaciones.sort_values(combustible, ascending=not asc),
            x=combustible, y="etiqueta", orientation="h",
            color=combustible, color_continuous_scale="RdYlGn_r" if asc else "RdYlGn",
            labels={combustible: "Precio exacto ($)", "etiqueta": ""}, height=400,
        )
        fig_estaciones.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_estaciones, use_container_width=True)

    st.divider()

    st.subheader(f"🏷️ Comparativa por Distribuidor {contexto_lugar}")
    marca = (d_graficos.groupby("marca")[combustible]
               .agg(precio="mean", estaciones="count").reset_index())
    limite_estaciones = 3 if len(d_graficos) > 20 else 1
    marca = marca[marca["estaciones"] >= limite_estaciones].sort_values("precio")
    
    if not marca.empty:
        fig_marca = px.bar(
            marca, x="precio", y="marca", orientation="h",
            color="precio", color_continuous_scale="RdYlGn_r",
            hover_data={"estaciones": True, "precio": ":$,.0f"},
            labels={"precio": "Precio promedio ($)", "marca": ""}, height=350,
        )
        fig_marca.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_marca, use_container_width=True)
        if limite_estaciones > 1:
            st.caption(f"*Mostrando marcas con {limite_estaciones} o más estaciones en la zona filtrada.")

with col_chat:
    # ==========================================================================
    # 🤖 MÓDULO DE IA: CHATBOT OPTIMIZADO CON BOTONES INTEGRADOS
    # ==========================================================================
    st.subheader("🤖 Asistente Virtual")
    st.markdown(f"<small>Hablemos sobre los datos actuales **{contexto_lugar}**. ¡Pregúntame con confianza!</small>", unsafe_allow_html=True)

    try:
        google_api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        google_api_key = os.environ.get("GOOGLE_API_KEY")

    if not google_api_key:
        st.warning("Configura GOOGLE_API_KEY en secrets.toml")
    else:
        cliente = genai.Client(api_key=google_api_key)

        if "mensajes_chat" not in st.session_state:
            st.session_state.mensajes_chat = []

        chat_container = st.container(height=400)

        # Usamos 'with' para que tanto los mensajes como los botones queden dentro del contenedor
        with chat_container:
            for mensaje in st.session_state.mensajes_chat:
                with st.chat_message(mensaje["rol"]):
                    st.markdown(mensaje["contenido"])

            # =================================================================
            # 💡 BOTONES INTEGRADOS (EN FILA) Y GUÍA DE UX
            # =================================================================
            st.write("") # Pequeño espacio visual
            
            # Si el chat está vacío, damos la bienvenida y educamos sobre los filtros
            if len(st.session_state.mensajes_chat) == 0:
                with st.chat_message("assistant"):
                    st.markdown("¡Hola! 👋 Te recomiendo **usar los filtros de la izquierda** primero para elegir tu zona. Luego, puedes escribirme o elegir una de estas preguntas frecuentes:")
            
            sugerencia = None
            
            # Al no usar 'st.columns', los botones se apilan naturalmente hacia abajo
# Botón 1: Ahorro transversal en Bencinas (93, 95 y 97)
            if st.button("⛽ ¿Dónde están las bencinas más baratas? (93, 95 y 97)", use_container_width=True):
                sugerencia = "Dime cuál es el servicentro más barato para Gasolina 93, el más barato para 95 y el más barato para 97 en la zona seleccionada. Incluye dirección, marca y precio exacto."
                
            # Botón 2: Alerta de bolsillo (Evitar las caras)
            if st.button("🛑 ¿Cuáles son las estaciones más caras para evitarlas?", use_container_width=True):
                sugerencia = "Revisa los datos actuales y hazme un Top 3 de los servicentros con los precios más altos en esta zona (considerando bencinas) para saber dónde NO ir."
                
            # Botón 3: Lealtad de marca / Distribuidores
            if st.button("🏪 ¿Qué marca o distribuidor me conviene más por aquí?", use_container_width=True):
                sugerencia = "De forma breve, analiza la zona y dime qué marca (ej. Copec, Shell, Petrobras o Sin Bandera) tiene opciones más convenientes. Recomiéndame la mejor estación de esa marca."
                
            # Botón 4: Panorama General (Ideal si el usuario selecciona una comuna nueva)
            if st.button("📍 Hazme un resumen rápido de los precios en esta zona", use_container_width=True):
                sugerencia = "Hazme un resumen rápido y amigable de cómo están los precios de los combustibles en esta zona específica: menciona el rango de precios y la opción más económica en general."
        # Input box anclado en la parte inferior
        pregunta_input = st.chat_input("O escribe tu propia pregunta aquí...")
        
        # Evaluamos qué activó el usuario (un botón o el texto)
        pregunta = sugerencia or pregunta_input

        if pregunta:
            st.session_state.mensajes_chat.append({"rol": "user", "contenido": pregunta})
            with chat_container.chat_message("user"):
                st.markdown(pregunta)

            with chat_container.chat_message("assistant"):
                
                LIMITE_FILAS = 600 
                
                if len(d) > LIMITE_FILAS:
                    msg_bloqueo = f"⚠️ Actualmente hay **{len(d)}** estaciones cargadas. Para evitar un consumo excesivo y darte una respuesta precisa, selecciona una **Región** o **Comuna** en la izquierda."
                    st.warning(msg_bloqueo)
                    st.session_state.mensajes_chat.append({"rol": "assistant", "contenido": msg_bloqueo})
                
                else:
                    with st.spinner("Analizando estaciones de la zona..."):
                        try:
                            columnas_ia = ['region', 'comuna', 'direccion', 'marca', 'Gasolina 93', 'Gasolina 95', 'Gasolina 97', 'Diésel', 'Kerosene']
                            cols_validas = [c for c in columnas_ia if c in d.columns]
                            
                            # ⚡ OPTIMIZACIÓN DE VELOCIDAD EXTREMA
                            d_ia = d[cols_validas].copy()
                            
                            # 1. Borramos estaciones fantasma
                            combustibles_disp = [c for c in ['Gasolina 93', 'Gasolina 95', 'Gasolina 97', 'Diésel', 'Kerosene'] if c in d_ia.columns]
                            d_ia = d_ia.dropna(subset=combustibles_disp, how='all')
                            
                            # 2. Reemplazamos los 'NaN' por celdas vacías
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