# Fase 3 — Variables y efecto base

> Estado: **cerrada** (2026-09-23). Código: [`src/features.py`](../src/features.py).

## La idea central: separar lo conocido de lo desconocido

La inflación de 12 meses es la composición de las 12 últimas variaciones mensuales. En
logaritmos es una suma, con `l[k] = log(1 + variación mensual de k)`:

```
log(1 + π12[t+h]) =  Σ l[k], k = t+h−11 … t     ← ya se conoce en t
                   +  Σ l[k], k = t+1 … t+h      ← lo único que hay que pronosticar
```

Para pronosticar la inflación de 12 meses dentro de `h` meses, 12 − `h` de sus meses ya
ocurrieron. Solo los `h` meses siguientes son inciertos. La primera suma es el **efecto base**:
cuando un mes de inflación alta sale de la ventana, la inflación de 12 meses baja aunque los
precios sigan subiendo al ritmo de siempre.

La regla de calidad Q6 ([Fase 2](02_calidad.md)) confirma que esta identidad se cumple con
diferencia cero en los 284 meses. La prueba `test_known_plus_future_rebuilds_12m_inflation`
verifica que, con un pronóstico perfecto de los meses futuros, la fórmula devuelve exactamente la
inflación publicada.

**Por qué importa ahora.** El IPC subió 2,38 % en marzo de 2026. Ese mes está dentro de la
inflación de 12 meses hasta febrero de 2027 y sale en marzo de 2027. Un modelo que pronostica la
inflación de 12 meses como una serie más no "sabe" cuándo sale ese mes. Uno que pronostica los
meses futuros y suma el efecto base, sí.

## Variables de los modelos directos

Todas se conocen al cierre del mes de origen `t`. Las tasas están en %, anualizadas cuando son
de menos de 12 meses.

| Grupo | Variable | Por qué |
|---|---|---|
| Inercia | Inflación 12 m; inflación 3 y 6 m anualizada | La inflación reciente es el mejor predictor de la próxima |
| Inflación de fondo | Sin alimentos y energía 12 m y 3 m anualizada | Separa la tendencia de los choques de alimentos y combustibles |
| Composición | Transables 12 m, no transables 12 m | Precios internacionales frente a servicios locales |
| Costos | Precios al por mayor 12 m | Presiones que llegan después al consumidor |
| Expectativas | Expectativa a 12 m (encuesta BCRP) | Lo que esperan empresas y analistas |
| Política monetaria | Tasa de referencia y su cambio en 12 m | Actúa con rezago sobre la demanda |
| Externas | Tipo de cambio, petróleo WTI y trigo: variación 12 m | Traspaso de precios importados |
| Estacionalidad | Suma del perfil estacional de los próximos `h` meses (promedio de cada mes calendario en los últimos 5 años) y mes del origen | Pronosticar desde febrero incluye un marzo; desde abril, no |

## Qué se hace para no mirar el futuro

- El perfil estacional de cada origen se calcula **solo con los 5 años anteriores** a ese origen.
- El objetivo de entrenamiento para el horizonte `h` es la inflación de los `h` meses siguientes.
  Un origen `s` solo entra al entrenamiento si `s + h ≤ t`, es decir, si su objetivo ya se había
  observado en `t`.
- La prueba `test_no_look_ahead` altera todos los datos posteriores a un origen (los triplica y
  les suma 5) y exige que el pronóstico hecho en ese origen no cambie. La pasan el ingenuo, el
  estacional, la Ridge y el SARIMA.
- El primer mes de entrenamiento es septiembre de 2004: desde ahí existen todas las variables (el
  cambio de la tasa en 12 meses necesita la tasa de septiembre de 2003, su primer dato).
