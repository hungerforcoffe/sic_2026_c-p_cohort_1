# ⛽ Precios de Combustibles en Chile

Dashboard interactivo que muestra los precios de combustibles en las ~2.000 estaciones de servicio del país, utilizando datos reales. 

Proyecto desarrollado para el curso **Código y Programación** del **Samsung Innovation Campus (SIC) Chile 2026 - Cohort 1**.

---
## Equipo
* Laura Díaz (GitHub: @lau-diaz-c)
* Nicolás Torres (GitHub: @NicolasTorresSSNA)
* Noemi Calabuig (GitHub: @noemicalabuig)
* Pablo Rojas (GitHub: @hungerforcoffe)
* Vicente Yunusic (GitHub: @vyunus)
* Nicol Sandoval (GitHub: @nicolsandovalu)

---
## ⚙️ Datos
* **Fuente de Datos:** 

[API Oficial de Combustibles de la CNE](https://api.cne.cl/api/v4/estaciones). *(Catálogo completo: https://apidocs.cne.cl)*

Filas: 7.436  |  Columnas: 21  |  Licencia: "Acceso completo y gratuito" - [Datos de Gobierno](datos.gob.cl): Creative Commons Zero (CC0)

[Google Maps Platform - Google Cloud API](https://console.cloud.google.com/google/maps-apis/). 

En particular Routes API y Geocoding API |  Licencia: Licencia propietaria comercial (pay-as-you-go / suscripción)

---
## 🎯 Pregunta de análisis
**¿Dónde está el combustible más barato y cómo podemos ayudar al conductor a tomar decisiones informadas?**
Este tablero permite a cualquier usuario, sin conocimientos técnicos, explorar precios por tipo de combustible, región, comuna y distribuidor para cuidar su bolsillo frente a las fluctuaciones del mercado.


## 🚀 Aplicación en Vivo
Puedes probar nuestro Dashboard interactivo aquí: 

👉 **[BenciMap - Streamlit Cloud](https://bencimap.streamlit.app/)**

---

## 📊 Hallazgos, Visualizaciones y Funcionalidades
**Hallazgo principal**

Existe una brecha de precios significativa entre distribuidores de una misma localidad, lo que convierte a este dashboard interactivo y a su asistente con IA en herramientas clave para que los conductores identifiquen ahorros inmediatos en tiempo real antes de cargar combustible.

* **Mapa Dinámico de Precios:** Cada estación está geolocalizada y coloreada según su precio (tonos verdes para las opciones más económicas).
* **Comparación por Distribuidor:** Análisis del precio promedio por marca (Copec, Shell, Petrobras, etc.).
* **Asistente Virtual (IA):** Chatbot integrado con Gemini 2.5 Flash para responder dudas frecuentes y recomendar estaciones al instante.
* **KPIs:** Métricas destacadas con la cantidad de estaciones, precio promedio, mínimo y máximo de la zona seleccionada.

---

## ⚙️ Tecnología
* **Módulos y Librerías:**
  * `pandas`: Descarga, aplanado de JSON anidado (`json_normalize`), limpieza de datos nulos, conversión de tipos numéricos y agregaciones.
  * `plotly`: Renderizado de mapas y gráficos interactivos y responsivos.
  * `streamlit`: Construcción de toda la interfaz web interactiva, filtros en cascada y sistema de caché para optimizar el rendimiento.
  * `google-genai`: Integración del modelo de lenguaje (LLM) con Zero-Shot Prompting para el asistente virtual inteligente.
  * `requests`: Consumo y consulta de la API Rest oficial de la Comisión Nacional de Energía (CNE) para la extracción de precios actualizados.
  * `folium` y `streamlit-folium`: Creación e integración bidireccional de mapas interactivos con geolocalización y marcadores agrupados para las estaciones de servicio.
  * `streamlit-geolocation`: Obtención en tiempo real de la ubicación actual del usuario desde el navegador mediante APIs del lado del cliente.
  * `geopy`: Medición y cálculo de distancias terrestres y geodésicas para encontrar las estaciones de servicio más cercanas al conductor.
  * `branca`: Creación de leyendas HTML/CSS personalizadas y paletas de colores dinámicas integradas en los mapas interactivos.

* **Algoritmos aplicados:** Ordenamiento (rankings), normalización de campos categóricos, cortafuegos de tokens (optimización de prompts) y cruce/distancias de datos espaciales.

