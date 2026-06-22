"""
<<<<<<< HEAD
app_multipage.py — Punto de entrada de la app multipágina (Mapa + Dashboard).

Ejecutar:
    pip install -r requirements.txt
    streamlit run app_multipage.py
=======
app.py — Punto de entrada de la app multipágina (Mapa + Dashboard).

Ejecutar:
    pip install -r requirements.txt
    streamlit run app.py
>>>>>>> 9f24672bf716d9fb0f9e39ebb6885322a400d615
"""
import streamlit as st

st.set_page_config(
    page_title="BenciMap · Chile",
    page_icon="⛽",
    layout="wide",
)

st.markdown(
    """
    <style>
<<<<<<< HEAD
=======
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
            max-width: 1200px;
            line-height: 1.6 !important;
        }

>>>>>>> 9f24672bf716d9fb0f9e39ebb6885322a400d615
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
<<<<<<< HEAD
=======
        
     /* === INDICADOR DE CARGA: "REACTOR NEÓN" + OVERLAY DESENFOCADO === */
        
        /* 1. Transformamos el widget base en un cristal oscuro a pantalla completa */
        div[data-testid="stStatusWidget"] {
            visibility: visible !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            /* Usamos el azul oscuro de nuestra paleta Eco-Drive con 85% de opacidad */
            background-color: rgba(17, 24, 39, 0.85) !important; 
            backdrop-filter: blur(6px) !important;
            -webkit-backdrop-filter: blur(6px) !important;
            z-index: 999998 !important;
            color: transparent !important; /* Oculta el texto nativo "Running..." */
        }
        
        /* Ocultamos los íconos por defecto de Streamlit dentro del widget */
        div[data-testid="stStatusWidget"] img, 
        div[data-testid="stStatusWidget"] svg,
        div[data-testid="stStatusWidget"] span {
            display: none !important;
        }

        /* 2. El Spinner Neón Centrado */
        div[data-testid="stStatusWidget"]::before {
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            margin-top: -30px;
            margin-left: -30px;
            width: 60px;
            height: 60px;
            border: 4px solid rgba(16, 185, 129, 0.1);
            border-top: 4px solid #10B981;
            border-right: 4px solid #3B82F6;
            border-radius: 50%;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.6), inset 0 0 15px rgba(59, 130, 246, 0.4);
            animation: spinReactor 1s linear infinite;
            z-index: 999999;
        }

        /* 3. Texto palpitante debajo del spinner */
        div[data-testid="stStatusWidget"]::after {
            content: "Sincronizando...";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, 50px);
            color: #10B981;
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
            text-shadow: 0 0 10px rgba(16, 185, 129, 0.7);
            animation: pulseNeonText 1.5s ease-in-out infinite;
            z-index: 999999;
            white-space: nowrap;
        }

        /* 4. Las animaciones */
        @keyframes spinReactor {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @keyframes pulseNeonText {
            0%, 100% { opacity: 0.5; text-shadow: 0 0 5px rgba(16, 185, 129, 0.4); }
            50% { opacity: 1; text-shadow: 0 0 15px rgba(16, 185, 129, 0.9); }
        }

>>>>>>> 9f24672bf716d9fb0f9e39ebb6885322a400d615
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
<<<<<<< HEAD
=======
}
>>>>>>> 9f24672bf716d9fb0f9e39ebb6885322a400d615
    </style>
    """,
    unsafe_allow_html=True,
)

<<<<<<< HEAD
pagina_mapa = st.Page("paginas/mapa.py", title="Mapa", icon="🗺️", default=True)
pagina_dashboard = st.Page("paginas/dashboard.py", title="Dashboard", icon="📊")
=======
# ==========================================
# 🏛️ RENDERIZADO DEL HEADER DISTINTIVO
# ==========================================
st.markdown(
    """
    <div class="hero-banner">
        <div class="hero-content">
            <div class="hero-badge">Monitoreo Territorial Diario</div>
            <h1>BenciMap · Chile</h1>
            <p>Explora y evalúa los precios de las casi 2.000 estaciones de servicio que hay en todo el país. Una plataforma inteligente que cruza los datos reales y geolocalización para ayudarte a conocer el mercado, comparar opciones al instante y tomar las mejores decisiones que protejan tu economía..</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

pagina_mapa = st.Page("paginas/mapa.py", title="Mapa", icon="🗺️", default=True)
pagina_dashboard = st.Page("paginas/dashboard.py", title="Panel Estadístico", icon="📊")
>>>>>>> 9f24672bf716d9fb0f9e39ebb6885322a400d615

navegacion = st.navigation([pagina_mapa, pagina_dashboard])
navegacion.run()
