# Fase 6 — La app

> Estado: **cerrada** (2026-09-23). Código: [`streamlit_app.py`](../streamlit_app.py) y [`app/`](../app/).

## Diseño

La app **no calcula nada**: lee lo que el pipeline dejó en `data/processed/` y
`reports/backtest/`. Así carga en segundos, no depende de que la API del BCRP responda en ese
momento y muestra exactamente las cifras que están versionadas y probadas.

| Página | Pregunta | Qué muestra |
|---|---|---|
| **Inflación hoy** | P1 | Inflación total y sin alimentos y energía desde 2003 sobre el rango meta; variación mensual frente a un mes normal; transables y no transables |
| **Pronóstico** | P2, P3 | Gráfico de abanico a 12 meses con intervalos de 80 % y 95 %; probabilidad de estar en el rango meta; mes de retorno bajo 3 %; descomposición del efecto base; tabla mensual. Permite cambiar de modelo |
| **Validación** | P4 | Error por horizonte de todos los modelos y referencias; mejora frente al ingenuo con su prueba de Diebold-Mariano; cobertura de intervalos; error por etapa; *máquina del tiempo* para ver qué se habría pronosticado en cualquier mes desde 2015 |
| **Qué lo mueve** | P5 | Aporte de cada variable al pronóstico de la Ridge a 12 meses |
| **Cómo se hizo** | — | Las fases del proyecto con enlace a cada documento, las reglas de calidad y los límites |

**Los textos se arman con los datos.** Frases como "vuelve bajo 3 % en …" o "fuera del rango
meta desde …" se calculan al cargar la página, para que sigan siendo ciertas después de cada
actualización mensual.

**Gráficos.**
- Un solo eje por gráfico: dos medidas con distinta unidad van en gráficos separados.
- El color sigue a la serie: la inflación observada siempre es azul y el pronóstico siempre naranja.
- El rango meta es una banda gris neutra, nunca un color de serie.
- La paleta categórica viene validada para daltonismo.

## Despliegue

Streamlit Community Cloud, desde la rama `main` de este repositorio, con `streamlit_app.py` como
archivo principal y Python 3.12. Las dependencias de la app están en `requirements.txt`
(streamlit, pandas, numpy, plotly); las del pipeline, en `requirements-pipeline.txt`, para que la
app despliegue liviana.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
