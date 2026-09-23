# Fase 2 — Calidad de los datos

> Estado: **cerrada** (2026-09-23).

```bash
python -m src.dataset   # construye data/processed/panel.csv y escribe reports/calidad_datos.csv
```

Si una regla no se cumple, el pipeline se detiene antes de escribir el panel.

## Reglas

| Regla | Qué comprueba | Resultado |
|---|---|---|
| Q1 | 284 meses consecutivos, sin huecos | ✅ |
| Q2 | Ningún vacío ni "n.d." en las series | ✅ 0 vacíos |
| Q3 | La tasa de referencia empieza en sep-2003 | ✅ Es la fecha en que el BCRP adoptó la tasa de referencia como instrumento |
| Q4 | Inflación de 12 meses publicada = calculada desde el índice | ✅ diferencia máxima 0,000000 pp |
| Q5 | Variación mensual publicada = calculada desde el índice | ✅ 0,000000 pp |
| Q6 | Inflación de 12 meses = composición de las 12 variaciones mensuales | ✅ 0,000000 pp |
| Q7 | Lo mismo para la inflación sin alimentos y energía | ✅ 0,000000 pp |
| Q8 | Precios, tipo de cambio e índice positivos | ✅ |

**Q6 es la regla que sostiene el modelado.** Confirma que la inflación de 12 meses es exactamente
la composición de las variaciones mensuales, sin redondeos ni rupturas de base. Eso permite
separar cualquier pronóstico en una parte ya conocida (los meses que siguen en la ventana) y una
parte por pronosticar (ver [Fase 3](03_variables.md)).

## Lo que muestran los datos

**Estacionalidad fuerte.** Marzo concentra la mayor inflación del año: 0,78 % en promedio entre
2007 y 2025, frente a 0,12 %–0,42 % del resto de meses. Un modelo que no la considere confunde
estacionalidad con tendencia.

| Mes | Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Set | Oct | Nov | Dic |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Variación mensual promedio 2007–2025 (%) | 0,17 | 0,27 | **0,78** | 0,22 | 0,16 | 0,20 | 0,42 | 0,29 | 0,18 | 0,12 | 0,12 | 0,31 |

**Un choque sin precedentes en marzo de 2026.** El IPC subió 2,38 %, la mayor variación mensual
de la serie (las siguientes: 1,48 % en mar-2022 y 1,30 % en mar-2017). La inflación sin alimentos y
energía también saltó (2,07 %, su máximo), y la de no transables pasó de 3,11 % a 4,76 % a 12 meses.
Fue un aumento generalizado, no de alimentos o combustibles.

**Decisión: el choque no se trata como dato atípico.** Es un dato oficial y es real. Quitarlo
haría que el backtest subestime la incertidumbre, y además es justamente lo que el pronóstico
actual necesita manejar: ese mes seguirá dentro de la inflación de 12 meses hasta febrero de
2027 y saldrá en marzo de 2027.

**Dos regímenes de meta.** El rango meta cambió en enero de 2007. `panel.csv` lleva el rango
vigente de cada mes en `meta_min` y `meta_max`.
