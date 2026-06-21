"""
app_multipage.py — Punto de entrada de la app multipágina (Mapa + Dashboard).

Ejecutar:
    pip install -r requirements.txt
    streamlit run app_multipage.py
"""
import streamlit as st

st.set_page_config(
    page_title="Precios de Combustibles · Chile",
    page_icon="⛽",
    layout="wide",
)

st.markdown(
    """
    <style>
        header[data-testid="stHeader"] {
            background-color: transparent !important;
        }
        header[data-testid="stHeader"] button:not([data-testid="stStatusWidget"] *),
        header[data-testid="stHeader"] a:not([data-testid="stStatusWidget"] *) {
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }
        header[data-testid="stHeader"]:hover button:not([data-testid="stStatusWidget"] *),
        header[data-testid="stHeader"]:hover a:not([data-testid="stStatusWidget"] *) {
            opacity: 1;
        }
        div[data-testid="stStatusWidget"]::before {
            content: "" !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            background-color: rgba(0, 0, 0, 0.25) !important;
            backdrop-filter: blur(2px) !important;
            z-index: -99999 !important;
            pointer-events: none !important;
        }
        .block-container {
            padding-top: 2rem !important;
        }
        /* Columna del chatbot: queda fija al hacer scroll en vez de desaparecer
           dejando el espacio vacío. Solo afecta a la columna que contiene el
           ancla #chatbot-anchor (ver comun_app.render_chatbot). */
        div[data-testid="stColumn"]:has(#chatbot-anchor) {
            position: sticky;
            top: 1rem;
            align-self: flex-start;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

pagina_mapa = st.Page("paginas/mapa.py", title="Mapa", icon="🗺️", default=True)
pagina_dashboard = st.Page("paginas/dashboard.py", title="Dashboard", icon="📊")

navegacion = st.navigation([pagina_mapa, pagina_dashboard])
navegacion.run()
