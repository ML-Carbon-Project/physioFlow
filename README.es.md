# Fisiología Vegetal - Goiás Verde

> Una plataforma web open-source interactiva para el análisis exploratorio de datos, modelado espacial y aprendizaje automático de parámetros ecofisiológicos de cultivos agrícolas (soja y caña de azúcar).

[English](./README.md) | [Português](./README.pt.md) | [Español](./README.es.md)

**Versión:** 1.0  
**Iniciativa:** Proyecto Goiás Verde (*Instituto Federal Goiano – Campus Rio Verde* & *Centro de Excelencia en Agricultura Exponencial – CEAGRE*)

---

> ### 📖 [**Manual de Operación del Sistema →**](./docs/manual.pt.md)
>
> Guía paso a paso completa: instalación, carga de datos, pipeline de limpieza, EDA, modelado, análisis espacial, serie temporal, comparación por grupos, glosario estadístico y FAQ. **15 capítulos, 26 capturas de pantalla.**
> *Actualmente disponible en portugués; se planean traducciones al inglés y al español.*

---

## 📋 Visión General

Este repositorio contiene la aplicación Streamlit desarrollada para consolidar el flujo de tratamiento, análisis descriptivo, modelado predictivo y geoespacial de datos de **Fisiología Vegetal**. El aplicativo valida planillas de campo que contienen datos recolectados por analizadores de fotosíntesis (IRGA), clorofilómetros y ceptómetros, aplicando un pipeline automatizado de limpieza y análisis avanzado.

La herramienta es agnóstica respecto a los archivos, siempre que las columnas de la planilla correspondan al diccionario de datos (ej.: tasa de fotosíntesis `A`, transpiración `E`, conductancia estomática `gs`, clorofilas, índice de área foliar `LAI/IAF`, etc.).

---

## 🛠️ Características Principales

1.  **Carga y Validación de Esquema** — Ingesta de archivos Excel (`.xlsx`, `.xls`) o CSV con validación en tiempo real contra el esquema de 31 columnas fisiológicas organizadas por niveles de importancia (*Requeridas*, *Recomendadas*, *Opcionales*). Realiza verificación de tipos y validación de límites geográficos.
2.  **Pipeline de Limpieza** — Aplicación transparente de filtros reactivos: eliminación de variables no deseadas, descarte de registros sin metadatos obligatorios, eliminación de puntos de grilla vacíos y **5 modos de tratamiento de réplicas** (promedio aritmético de las réplicas, desdoblamiento de las réplicas en filas independientes mediante `melt`, o selección de réplicas específicas).
3.  **Análisis Exploratorio de Datos (EDA)** — Estadísticas descriptivas completas, control de datos faltantes, histogramas, diagramas de caja (boxplots), mapas de calor de correlación (Pearson, Spearman, Kendall), distribución de categorías, pruebas de normalidad (Shapiro-Wilk, Anderson-Darling, D'Agostino-Pearson), multicolinealidad (VIF), rankings de hotspots y auditoría de outliers usando consenso de 5 métodos de Machine Learning.
4.  **Regresión** — Ajuste de modelos de regresión bivariada con presets comunes en fisiología vegetal (ej.: *gs vs. A*, *Ci vs. A*, *gs vs. E*) con soporte para intervalos de confianza y segmentación (facet).
5.  **Modelado Predictivo** — Entrenamiento y comparación de modelos de Machine Learning (Regresión Lineal, Random Forest, Gradient Boosting, Decision Tree, KNN) para estimar la tasa fotosintética `A` a partir de los demás parámetros, con métricas de validación cruzada, holdout y gráficos de importancia de atributos.
6.  **Análisis Espacial** — Interpolación por Inverso de la Distancia (IDW), autocorrelación espacial por Moran's I global y LISA local (mapas de clusters significativos), estadísticas Getis-Ord Gi*, agregación en grilla UTM regular, interpolación por Kriging ordinario con semivariograma esférico y mapa de puntos ploteado sobre los límites geográficos de Rio Verde, GO (a través de la biblioteca `geobr`).
7.  **Serie Temporal** — Agregación diaria y descomposición de series temporales STL (Tendencia, Estacionalidad y Residuos).
8.  **Comparación por Grupos** — Pruebas estadísticas de Mann-Whitney U, regresión log-lineal por grupo y curvas acumulativas horarias.

---

## 📂 Estructura del Proyecto

```
fisiologia-streamlit/
├── app.py                      # Punto de entrada de la aplicación
├── requirements.txt            # Dependencias de producción
├── pyproject.toml              # Configuraciones de pytest
├── src/
│   ├── auth.py                 # Integración de inicio de sesión (Supabase)
│   ├── state.py                # Gestión del estado de la sesión
│   ├── schema.py               # Validador de columnas y límites
│   ├── pipeline.py             # Algoritmo de limpieza y réplicas
│   ├── components/             # Componentes visuales (Sidebar, Filtros Globales)
│   │   ├── sidebar.py
│   │   └── filters.py
│   ├── config/
│   │   └── settings.py         # Configuración de estilos (CSS) y variables por defecto
│   ├── i18n/                   # Internacionalización (PT, EN, ES)
│   └── pages/                  # Módulos de interfaz de cada pestaña
├── tests/                      # Pruebas automatizadas (pytest)
└── docs/                       # Documentación (Arquitectura, Diccionario de datos)
```

---

## 🚀 Cómo Ejecutar Localmente

### 1. Crear y Activar Ambiente Virtual
```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

### 2. Instalar Dependencias
```bash
pip install -U pip wheel
pip install -r requirements.txt
```

### 3. Ejecutar Streamlit
```bash
python -m streamlit run app.py
```
La aplicación se abrirá en su navegador predeterminado en la dirección `http://localhost:8501`.

---

## 🧪 Ejecutando las Pruebas Unitarias

La suite de pruebas valida la integridad del pipeline de datos y las reglas de validación del esquema:
```bash
PYTHONPATH=. .venv/bin/pytest tests/
```

---

## 👥 Soporte y Agradecimientos

Este proyecto fue desarrollado con el apoyo y financiamiento de CNPq, CAPES, FAPEG, el Instituto Federal Goiano (IF Goiano – Campus Rio Verde) y el Centro de Excelencia en Agricultura Exponencial (CEAGRE).
