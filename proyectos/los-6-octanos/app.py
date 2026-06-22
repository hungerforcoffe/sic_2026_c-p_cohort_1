"""
app.py — Punto de entrada de la app multipágina (Mapa + Dashboard).

Ejecutar:
    pip install -r requirements.txt
    streamlit run app.py
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
/* === 1. FUENTES === */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;700&display=swap');
        
        /* Aplicar Inter suavemente al contenedor principal sin romper los iconos nativos de Streamlit */
        .stApp {
            font-family: 'Inter', sans-serif;
        }

        /* === 2. IDENTIDAD: PATRÓN DE FONDO (Dot Grid) === */
        /* Esto le da textura de 'dashboard técnico' al fondo azul oscuro */
        .stApp > header {
            background-color: transparent !important;
        }
        .stApp {
            background-color: #111827;
            background-image: radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px);
            background-size: 24px 24px;
        }

        /* Títulos y Métricas con Space Grotesk */
        h1, h2, h3, h4, h5, h6, [data-testid="stMetricValue"] {
            font-family: 'Space Grotesk', sans-serif !important;
        }

        /* === 3. TARJETAS CON IDENTIDAD ECO-DRIVE === */
        [data-testid="stMetric"] {
            background-color: #1F2937;
            /* Le agregamos una barra lateral de acento para darle más estructura */
            border-left: 4px solid #10B981; 
            border-radius: 8px;
            padding: 16px 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: all 0.2s ease;
        }
        
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-left-color: #34D399; /* Un verde más brillante al pasar el mouse */
        }

        [data-testid="stMetricValue"] {
            color: #F9FAFB !important;
            font-size: 2.2rem !important;
        }

        /* === 4. CHATBOT Y ESTRUCTURA === */
        header[data-testid="stHeader"] button:not([data-testid="stStatusWidget"] *),
        header[data-testid="stHeader"] a:not([data-testid="stStatusWidget"] *) { opacity: 0; transition: opacity 0.3s ease-in-out; }
        header[data-testid="stHeader"]:hover button:not([data-testid="stStatusWidget"] *),
        header[data-testid="stHeader"]:hover a:not([data-testid="stStatusWidget"] *) { opacity: 1; }
        
        .block-container { padding-top: 2rem !important; }
        
        div[data-testid="stColumn"]:has(#chatbot-anchor) { position: sticky; top: 1rem; align-self: flex-start; }
        
        div[data-testid="stColumn"]:has(#chatbot-anchor) > div {
            background-color: #1F2937;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
   
    /* === 3. EL NUEVO HERO BANNER === */
        .hero-banner {
            /* Degradado de fondo oscuro a un tono un poco más claro */
            background: linear-gradient(135deg, #111827 0%, #1F2937 100%);
            border: 1px solid #374151; /* Borde gris sutil */
            border-left: 5px solid #10B981; /* Acento verde grueso a la izquierda */
            border-radius: 16px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            position: relative;
            overflow: hidden;
            /* AQUÍ ESTÁ LA SOMBRA INTERNA (inset) + sombra externa suave */
            box-shadow: inset 0 4px 15px rgba(0, 0, 0, 0.4), 0 10px 20px -5px rgba(0, 0, 0, 0.3);
        }

        # /* Textura de líneas diagonales para darle un aire técnico/dashboard */
        # .hero-banner::before {
        #     content: "";
        #     position: absolute;
        #     top: 0; left: 0; right: 0; bottom: 0;
        #     background: repeating-linear-gradient(
        #         45deg,
        #         rgba(16, 185, 129, 0.02),
        #         rgba(16, 185, 129, 0.02) 2px,
        #         transparent 2px,
        #         transparent 12px
        #     );
        #     pointer-events: none; /* Para que no bloquee el texto */
        # }

        /* Resplandor verde suave en la esquina superior derecha */
        .hero-banner::after {
            content: "";
            position: absolute;
            top: -50px; right: -50px;
            width: 200px; height: 200px;
            background: radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        }

        /* Estilos del texto dentro del banner */
        .hero-content {
            position: relative;
            z-index: 1; /* Asegura que el texto esté por encima de las texturas */
        }

        .hero-badge {
            display: inline-block;
            background-color: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            margin-bottom: 1rem;
            text-transform: uppercase;
        }

        .hero-banner h1 {
            font-size: 2.6rem !important;
            font-weight: 700 !important;
            color: #FFFFFF !important;
            margin: 0 0 0.5rem 0 !important;
            line-height: 1.2 !important;
            letter-spacing: -0.04em !important;
        }

        .hero-banner p {
            font-size: 1.05rem !important;
            color: #9CA3AF !important;
            margin: 0 !important;
            max-width: 800px;
            line-height: 1.6 !important;
        }

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
}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 🏛️ RENDERIZADO DEL HEADER DISTINTIVO
# ==========================================
st.markdown(
    """
    <div class="hero-banner">
        <div class="hero-content">
            <div class="hero-badge">Monitoreo Territorial Diario</div>
            <h1>Precios de Combustibles en Chile</h1>
            <p>Una herramienta diseñada para explorar precios por distribuidor, región y comuna. 
            Analiza el mercado en tiempo real, toma decisiones informadas y protege tu economía familiar.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

pagina_mapa = st.Page("paginas/mapa.py", title="Mapa", icon="🗺️", default=True)
pagina_dashboard = st.Page("paginas/dashboard.py", title="Dashboard", icon="📊")

navegacion = st.navigation([pagina_mapa, pagina_dashboard])
navegacion.run()
