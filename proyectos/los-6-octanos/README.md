# ⛽ Precios de Combustibles en Chile

Dashboard interactivo que muestra los precios de combustibles en las ~2.000
estaciones de servicio del país, usando datos **en vivo** de la
[Comisión Nacional de Energía (CNE)](https://api.cne.cl).

Proyecto desarrollado para el curso **Coding & Programming** del
**Samsung Innovation Campus (SIC)**.

## ¿Qué responde?

¿Dónde está el combustible más barato? El dashboard permite explorar precios
por combustible, región, comuna y distribuidor.

## Visualizaciones

1. **Mapa de precios** — cada estación coloreada según su precio (verde = barato).
2. **Ranking de comunas** — las comunas más baratas o más caras.
3. **Comparación por distribuidor** — precio promedio por marca (Copec, Shell, etc.).

Más KPIs: cantidad de estaciones, precio promedio, mínimo y máximo.

## Datos

- **Fuente:** API de Combustibles de la CNE (`https://api.cne.cl/api/v4/estaciones`).
- **Autenticación:** login con email + clave (`/api/login`) que entrega un token JWT
  (válido ~1 hora), enviado luego como header `Authorization: Bearer`.
- Catálogo completo de endpoints: https://apidocs.cne.cl

## Módulos del curso usados

- **pandas:** descarga, aplanado de JSON anidado (`json_normalize`), limpieza,
  conversión de tipos y agregaciones (promedios por comuna y por marca).
- **algoritmos:** rankings, normalización y agregación de los datos.

## Cómo ejecutarlo

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar credenciales
#    Copia .streamlit/secrets.toml.example  ->  .streamlit/secrets.toml
#    y pon tu correo y clave de api.cne.cl

# 3. Ejecutar
streamlit run app.py
```

## Equipo

- (Integrante 1)
- (Integrante 2)
- (Integrante 3)

---
Fuente de datos: Comisión Nacional de Energía (CNE), Chile.
