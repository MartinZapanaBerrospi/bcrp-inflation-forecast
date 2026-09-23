# Fase 5 — Evaluación

> Estado: **cerrada** (2026-09-23), con datos hasta agosto de 2026.
> Código: [`src/backtest.py`](../src/backtest.py) y [`src/evaluate.py`](../src/evaluate.py).
> Tablas completas: [`reports/backtest/`](../reports/backtest/).

```bash
python -m src.backtest    # ~10 minutos
python -m src.evaluate
```

## Diseño del backtest

- **Origen móvil con ventana expansiva.** Para cada mes de origen entre enero de 2013 y agosto de
  2026 (164 orígenes), cada modelo se reestima solo con los datos hasta ese mes y pronostica los
  12 meses siguientes: 11 808 pronósticos en total.
- **152 a 163 comparaciones por horizonte.** A 12 meses, el último pronóstico con dato real es el
  hecho en agosto de 2025.
- **Error:** inflación de 12 meses pronosticada menos observada, en puntos porcentuales (pp).
- **Etapas:** estable (2013–2019), pandemia (2020–2021), choque inflacionario (2022–2023) y
  reciente (2024–2026).

## Error por horizonte

Error absoluto medio en pp. En negrita, el menor de cada fila.

| Horizonte | Ingenuo | Estacional | SARIMA | Ridge | Boosting | Ensamble | Encuesta BCRP |
|---|---|---|---|---|---|---|---|
| 1 mes | 0,29 | 0,25 | 0,22 | 0,22 | 0,23 | **0,21** | — |
| 3 meses | 0,60 | 0,59 | 0,51 | 0,52 | 0,53 | **0,49** | — |
| 6 meses | 0,97 | 1,01 | **0,88** | 0,98 | 1,00 | 0,89 | — |
| 9 meses | 1,33 | 1,36 | **1,18** | 1,46 | 1,51 | 1,21 | — |
| 12 meses | 1,64 | 1,71 | 1,47 | 2,26 | 1,71 | 1,63 | **1,41** |
| **Promedio 1–12** | 1,01 | 1,03 | **0,90** | 1,11 | 1,07 | 0,92 | — |

**El SARIMA es el mejor modelo en promedio** (0,90 pp) y es el que muestra la app. El ensamble,
fijado antes de ver los resultados, queda segundo (0,92 pp): la Ridge lo arrastra en los
horizontes largos.

**La Ridge y el gradient boosting rinden peor que el ingenuo en promedio.** Con entre 89 y 263
observaciones y 26 variables, aprenden relaciones de un periodo que no se repiten en el siguiente.
La Ridge es buena a 1–3 meses y se desploma a 12 (2,26 pp, con sesgo de −1,50 pp): subestimó la
inflación sobre todo cuando subió de golpe, con −7,1 pp de error medio en los pronósticos hechos en
2021 y −3,5 pp en los de 2022.

**A 12 meses, la encuesta de expectativas del BCRP es la más precisa** (1,41 pp frente a 1,47 del
SARIMA). Gana en el 51 % de los 152 meses comparados: la diferencia es pequeña, pero a ese
horizonte los agentes encuestados saben algo que los modelos no capturan.

## ¿La mejora es real o azar? Diebold-Mariano

Prueba de Diebold-Mariano contra el ingenuo, con pérdida absoluta, varianza HAC y corrección de
Harvey-Leybourne-Newbold. Se muestra el p-valor; menor que 0,05 es una mejora significativa.

| Modelo | 1 mes | 3 meses | 6 meses | 9 meses | 12 meses |
|---|---|---|---|---|---|
| Estacional | **0,012** | 0,95 | 0,81 | 0,93 | 0,85 |
| SARIMA | **< 0,001** | 0,10 | 0,54 | 0,55 | 0,60 |
| Ridge | **< 0,001** | 0,21 | 0,94 | 0,64 | 0,15 |
| Boosting | **0,001** | 0,25 | 0,86 | 0,48 | 0,87 |
| Ensamble | **< 0,001** | **0,047** | 0,55 | 0,63 | 0,97 |
| Encuesta BCRP | — | — | — | — | 0,43 |

**La mejora sobre el ingenuo solo es significativa a corto plazo:** a 1 mes para todos los modelos
y a 3 meses para el ensamble. **A 6 meses o más, ningún modelo, ni la encuesta, es
estadísticamente mejor que suponer que la inflación se queda donde está.** No es un defecto de
estos modelos en particular: que el pronóstico ingenuo sea difícil de vencer es un resultado
conocido en pronóstico de inflación (Atkeson y Ohanian, 2001, *Are Phillips Curves Useful for
Forecasting Inflation?*), y la app lo muestra en lugar de esconderlo.

## Error a 12 meses según la etapa

| Modelo | Estable (2013–2019) | Pandemia (2020–2021) | Choque (2022–2023) | Reciente (2024–2026) |
|---|---|---|---|---|
| Ingenuo | 0,85 | 3,02 | 3,34 | 1,31 |
| Estacional | 0,83 | 3,57 | 2,59 | 2,12 |
| SARIMA | 0,80 | 3,18 | 2,08 | 1,48 |
| Ridge | 1,56 | 4,31 | 2,71 | 2,15 |
| Boosting | 1,24 | **2,74** | 2,85 | 1,07 |
| Ensamble | 1,15 | 3,69 | 1,83 | **0,89** |
| Encuesta BCRP | **0,73** | 3,65 | **1,75** | 1,19 |

En la etapa estable, todos los errores rondan 0,7–0,9 pp. En la pandemia y el choque de 2022, el
error se multiplica por 3 o 4 en todos los modelos: ninguno anticipó que la inflación llegaría a
8,81 %. En enero de 2022, por ejemplo, el ensamble pronosticó que la inflación bajaría a 2,5 % en
un año; llegó a 8,7 % (se puede ver en la *máquina del tiempo* de la app).

## Intervalos: cobertura real

Porcentaje de meses en que el dato real cayó dentro del intervalo.

| Modelo | 80 % a 1 mes | 80 % a 6 meses | 80 % a 12 meses | 95 % a 12 meses |
|---|---|---|---|---|
| SARIMA | 74 % | 60 % | 48 % | 66 % |
| Ensamble | 73 % | 63 % | 53 % | 74 % |
| Ridge | 78 % | 72 % | 56 % | 68 % |

**Los intervalos cubren menos de lo que prometen**, y más a horizontes largos. La causa es el
cambio de régimen:

| SARIMA, intervalo 80 % | 1 mes | 3 meses | 6 meses | 12 meses |
|---|---|---|---|---|
| Estable (2013–2019) | 87 % | 79 % | 75 % | 63 % |
| Pandemia (2020–2021) | 38 % | 58 % | 54 % | 25 % |
| Choque (2022–2023) | 71 % | 42 % | 50 % | 46 % |
| Reciente (2024–2026) | 81 % | 59 % | 42 % | 40 % |

En la etapa estable, los intervalos a 1–6 meses funcionan casi como deben. Cuando llegan la
pandemia y el choque, los errores del pasado (todos de una etapa tranquila) no anticipaban errores
de ese tamaño. **Por eso el pronóstico vigente usa todos los errores del backtest, incluidos los
de 2020–2023,** y sus intervalos son anchos: con el choque de marzo de 2026 aún en curso, subestimar
la incertidumbre sería el error más caro.

## Pronóstico vigente (origen: agosto de 2026)

SARIMA, el modelo con menor error promedio:

| Mes | Pronóstico | Intervalo 80 % | Prob. en rango meta | Inflación "asegurada" por meses observados |
|---|---|---|---|---|
| Set 2026 | 4,51 % | 4,15 – 4,88 % | 0 % | 4,43 % |
| Dic 2026 | 4,78 % | 4,06 – 5,98 % | 1 % | 4,16 % |
| Feb 2027 | 4,46 % | 3,37 – 6,44 % | 3 % | 3,34 % |
| **Mar 2027** | **3,00 %** | 1,88 – 5,01 % | 54 % | **0,94 %** |
| Abr 2027 | 2,74 % | 1,50 – 5,20 % | 60 % | 0,42 % |
| Ago 2027 | 3,26 % | 1,59 – 7,01 % | 43 % | 0,00 % |

- **La inflación seguiría sobre el rango meta hasta febrero de 2027**, entre 4,5 % y 4,9 %.
- **En marzo de 2027 cae a 3,0 % por efecto base:** sale de la ventana el 2,38 % de marzo de 2026.
  La inflación "asegurada" por los meses observados baja 2,40 pp de un mes a otro.
- **A agosto de 2027, el pronóstico es 3,26 %**, con 43 % de probabilidad de estar en el rango
  meta y 55 % de estar por encima.

| Modelo | Agosto 2027 | Prob. en rango meta |
|---|---|---|
| SARIMA | 3,26 % | 43 % |
| Encuesta BCRP (expectativa a 12 meses) | 3,05 % | 45 % |
| Gradient boosting | 3,11 % | 38 % |
| Ensamble | 3,45 % | 26 % |
| Ridge | 3,65 % | 21 % |
| Estacional | 4,28 % | 22 % |
| Ingenuo | 4,44 % | 11 % |

SARIMA, boosting, ensamble y Ridge coinciden con la encuesta (3,05 %) en que la inflación baja de
4,4 % a entre 3,1 % y 3,7 % en un año. El ingenuo, que no sabe que marzo de 2026 saldrá de la ventana, se
queda en 4,44 %. El estacional sí suma el efecto base, pero su perfil de los últimos 5 años incluye
los meses altos de 2022–2023 y el propio marzo de 2026, y por eso queda en 4,28 %.

## Qué mueve el pronóstico (Ridge, 12 meses)

La Ridge descompone su pronóstico en un valor base (3,13 %) más el aporte de cada variable:

| Variable | Hoy | Promedio histórico | Aporte |
|---|---|---|---|
| Trigo, variación 12 m | +48,7 % | +6,7 % | **+0,87 pp** |
| Inflación 6 meses anualizada | 6,58 % | 3,08 % | +0,41 pp |
| Tipo de cambio, variación 12 m | −5,1 % | +0,5 % | **−0,34 pp** |
| Estacionalidad de los próximos meses | 4,19 % | 3,02 % | −0,20 pp |
| Inflación transables 12 m | 2,27 % | 2,93 % | −0,14 pp |

La subida del trigo (+49 % en 12 meses) es la mayor presión alcista. La apreciación del sol (−5 %)
la compensa en parte, porque abarata los importados. Son asociaciones aprendidas, no efectos
causales, y vienen del modelo con peor desempeño a 12 meses: sirven para leer el escenario, no para
decidir política.
