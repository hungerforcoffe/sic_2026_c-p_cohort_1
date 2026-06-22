# ⛽ Precios de Combustibles en Chile

Dashboard interactivo que muestra los precios de combustibles en las ~2.000 estaciones de servicio del país, utilizando datos en vivo. 

Proyecto desarrollado para el curso **Código y Programación** del **Samsung Innovation Campus (SIC) Chile 2026 - Cohorte 1**.

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
* **Fuente de Datos:** [API Oficial de Combustibles de la CNE](https://api.cne.cl/api/v4/estaciones). *(Catálogo completo: https://apidocs.cne.cl)*
Filas: N  |  Columnas: N  |  Licencia: CC0 / CC BY / etc. (rellenar)

---
## 🎯 Pregunta de análisis
**¿Dónde está el combustible más barato y cómo podemos ayudar al conductor a tomar decisiones informadas?**
Este tablero permite a cualquier usuario, sin conocimientos técnicos, explorar precios por tipo de combustible, región, comuna y distribuidor para cuidar su bolsillo frente a las fluctuaciones del mercado.


## 🚀 Aplicación en Vivo
Puedes probar nuestro Dashboard interactivo aquí: 
👉 **[Insertar Link de Streamlit Cloud o Hugging Face]**

---

## 📊 Visualizaciones y Funcionalidades
* **Mapa Dinámico de Precios:** Cada estación está geolocalizada y coloreada según su precio (tonos verdes para las opciones más económicas).
* **Ranking de Comunas:** Gráficos de barras interactivos para descubrir las zonas más baratas o caras.
* **Comparación por Distribuidor:** Análisis del precio promedio por marca (Copec, Shell, Petrobras, etc.).
* **Asistente Virtual (IA):** Chatbot integrado con Gemini 2.5 Flash para responder dudas frecuentes y recomendar estaciones al instante.
* **KPIs en Tiempo Real:** Métricas destacadas con la cantidad de estaciones, precio promedio, mínimo y máximo de la zona seleccionada.

---

## ⚙️ Tecnología
* **Módulos y Librerías del Curso:**
  * `pandas`: Descarga, aplanado de JSON anidado (`json_normalize`), limpieza de datos nulos, conversión de tipos numéricos y agregaciones.
  * `plotly`: Renderizado de mapas y gráficos responsivos.
  * `streamlit`: Construcción de toda la interfaz web, filtros en cascada y sistema de caché.
  * `google-genai`: Integración del modelo de lenguaje (LLM) con Zero-Shot Prompting.
  * **Algoritmos aplicados:** Ordenamiento (rankings), normalización, cortafuegos de tokens y cruce de datos espaciales.

---

## Checklist
- [ ] README con descripcion, dataset, pregunta, hallazgos y link al dashboard
- [ ] requirements.txt actualizado
- [ ] Dashboard publicado y accesible
- [ ] Notebooks con comentarios en espanol
- [ ] Sin archivos mayores a 50 MB
      
Fuente de datos: Comisión Nacional de Energía (CNE), Chile.
