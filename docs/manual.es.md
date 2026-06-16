<!-- markdownlint-disable MD013 MD033 -->

# PhysioFlow — Manual de Operación del Sistema

> Versión del manual: 1.0 (alineada con la aplicación 1.x)
> Idioma de referencia: Portugués (canónico). Espejos en [`manual.pt.md`](manual.pt.md) (canónico) y [`manual.en.md`](manual.en.md) (inglés).

---

## Resumen Extendido

*Traducción pendiente. Vea la versión canónica en portugués: [`manual.pt.md`](manual.pt.md) (Resumen extendido) o la versión en inglés [`manual.en.md`](manual.en.md) (Extended Abstract).*

---

## Tabla de contenido

1. [Introducción](#1-introducción)
2. Instalación y primera ejecución
3. Cargando sus datos
4. Pipeline de limpieza
5. Filtros globales
6. Análisis Exploratorio de Datos (EDA)
7. Regresión bivariada
8. Modelado predictivo
9. Análisis espacial
10. Serie temporal
11. Comparación por grupos
12. Estadística Experimental (diseños)
13. Glosario estadístico
14. Solución de problemas (FAQ)
15. Referencias
16. Contribuyendo

---

## 1. Introducción

*Traducción pendiente. Vea [`manual.pt.md` §1](manual.pt.md#1-apresentação).*

## 2. Instalación y primera ejecución

*Traducción pendiente. Vea [`manual.pt.md` §2](manual.pt.md#2-instalação-e-primeira-execução).*

## 3. Cargando sus datos

*Traducción pendiente. Vea [`manual.pt.md` §3](manual.pt.md#3-carregando-seus-dados).*

## 4. Pipeline de limpieza

*Traducción pendiente. Vea [`manual.pt.md` §4](manual.pt.md#4-pipeline-de-limpeza).*

## 5. Filtros globales

*Traducción pendiente. Vea [`manual.pt.md` §5](manual.pt.md#5-filtros-globais).*

## 6. Análisis Exploratorio de Datos (EDA)

*Traducción pendiente. Vea [`manual.pt.md` §6](manual.pt.md#6-análise-exploratória-eda).*

## 7. Regresión bivariada

*Traducción pendiente. Vea [`manual.pt.md` §7](manual.pt.md#7-regressão-bivariada).*

## 8. Modelado predictivo

> Página **Modelado** en el menú lateral.

Entrena y compara varios modelos `scikit-learn` con validación cruzada y métricas de holdout. Un selector **Tipo de tarea** alterna entre **Regresión** (objetivo numérico — ej. predecir la fotosíntesis `A`) y **Clasificación** (objetivo categórico — ej. predecir la especie/cultivo).

* **Regresión** — Regresión Lineal, Ridge, Random Forest, Gradient Boosting, HistGradientBoosting, Árbol de Decisión, KNN; reporta R²/MAE/RMSE de holdout y R² de validación cruzada, gráfico predicho-vs-observado e importancias. Un **GroupKFold** opcional (agrupando por sitio, ej. *finca + punto*) mitiga la pseudoreplicación.
* **Clasificación** — Regresión Logística, Random Forest, Árbol de Decisión, Gradient Boosting, HistGradientBoosting, KNN, SVM, Naive Bayes; reporta exactitud/F1/precisión/recall, matriz de confusión e importancias, con selector de escalado opcional y GroupKFold.

Para el detalle sobre GroupKFold e interpretación de importancias, vea [`manual.pt.md` §8](manual.pt.md#8-modelagem-preditiva).

## 9. Análisis espacial

*Traducción pendiente. Vea [`manual.pt.md` §9](manual.pt.md#9-análise-espacial).*

## 10. Serie temporal

*Traducción pendiente. Vea [`manual.pt.md` §10](manual.pt.md#10-série-temporal).*

## 11. Comparación por grupos

*Traducción pendiente. Vea [`manual.pt.md` §11](manual.pt.md#11-comparação-por-grupos).*

## 12. Estadística Experimental (diseños)

> Página **Estadística Experimental** en el menú lateral.

Herramienta **genérica** de análisis de diseños experimentales — funciona con cualquier dataset, no solo fisiología. Usted mapea las columnas a *roles* (respuesta, tratamiento, bloque, factores) y la herramienta infiere el diseño, ajusta el ANOVA, prueba los supuestos y compara las medias. Inspirada en el flujo de *Estatística Experimental no Rbio* (Bhering & Teodoro).

> **Validación:** los análisis fueron verificados **número a número contra R** (`aov`, `car::Anova` tipo II, `emmeans`, paquete `ScottKnott`). Vea [`docs/validacao_externa.md`](validacao_externa.md).

Tres modos (selector arriba):

**12.1 Modo Diseño (ANOVA).** Mapee *respuesta* (numérica), *tratamiento* (factor), *bloque* opcional, *2º/3º factor* y *covariable*. El diseño se detecta automáticamente: tratamiento → **DCA**; + bloque → **DBCA**; + 2º/3º factor → **factorial** (con interacciones); + fila y columna → **Cuadrado Latino**. Un expander dedicado maneja los **diseños de error compuesto** — **parcelas subdivididas**, **franjas** y **jerárquico** — cada uno con sus términos de error y pruebas F contra el denominador correcto. Pestañas de resultado: **ANOVA** (gl, SC, CM, F, p, CV% experimental), **Supuestos** (Shapiro–Wilk, Levene, QQ-plot), **Comparación de medias** (Tukey, Scott-Knott, Duncan, Scheffé, LSD, o **Dunnett** vs. un control; ANCOVA usa medias ajustadas por la covariable) y **Reproducibilidad** (descarga el script Python que reproduce el análisis).

**12.2 Regresión de dosis.** Ajuste polinomial (lineal/cuadrático/cúbico) para un factor cuantitativo (dosis de fertilizante, lámina de riego…), con R², R² ajustado y significancia del término de mayor grado.

**12.3 Correlación.** Matriz de Pearson/Spearman (heatmap + valores-p) y correlación parcial controlando por covariables.

## 13. Glosario estadístico

*Traducción pendiente. Vea [`manual.pt.md` §13](manual.pt.md#13-glossário-estatístico).*

## 14. Solución de problemas (FAQ)

*Traducción pendiente. Vea [`manual.pt.md` §14](manual.pt.md#14-solução-de-problemas-faq).*

## 15. Referencias

*Bibliografía idéntica a la edición portuguesa — vea [`manual.pt.md` §15](manual.pt.md#15-referências).*

## 16. Contribuyendo

¿Encontró un error, tiene una sugerencia de mejora o quiere agregar un análisis nuevo?

* **Errores o pedidos de funcionalidad:** abra una issue en el repositorio del proyecto en GitHub.
* **Contribuir con código o documentación:** vea [`docs/contributing.md`](contributing.md) para el flujo de PRs, estándares de prueba y cómo agregar traducciones.
* **Generar este manual en PDF:** ejecute `scripts/build_manual_pdf.sh --lang es`. Vea [`manual.pt.md` §16.3](manual.pt.md#163-gerando-este-manual-em-pdf) para los pre-requisitos.

---

*Fin del manual. Versión 1.0 — alineada con la aplicación 1.x.*
