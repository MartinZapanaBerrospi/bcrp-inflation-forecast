# Fase 4 — Modelos

> Estado: **cerrada** (2026-09-23). Código: [`src/models.py`](../src/models.py).

Todos los modelos reciben un mes de origen `t`, usan solo información hasta `t` y devuelven la
inflación de 12 meses para `t+1 … t+12`. Los que pronostican meses solo estiman la parte
desconocida; el efecto base se suma exacto ([Fase 3](03_variables.md)).

## Referencias a vencer

| Referencia | Regla | Por qué está |
|---|---|---|
| **Ingenuo** | La inflación de 12 meses se queda donde está | Es la referencia estándar en pronóstico de inflación y es difícil de vencer a horizontes cortos |
| **Estacional histórico** | Los próximos meses repiten su promedio de los últimos 5 años, más el efecto base exacto | Mide cuánto aporta un modelo por encima de "estacionalidad + aritmética de la ventana" |
| **Encuesta BCRP** | La expectativa de inflación a 12 meses de la encuesta del BCRP | Es lo que ya saben los agentes; solo se compara a 12 meses, su horizonte |

## Modelos

### SARIMA(1,0,0)(1,0,1)₁₂ sobre la variación mensual

Modela la variación mensual (log, en %) con un rezago mensual, un componente estacional
autorregresivo y uno de medias móviles, más una constante.

**Cómo se eligió el orden.** Se compararon 20 combinaciones por AIC, estimadas solo con
2003–2012, antes del primer origen del backtest:

| Orden | AIC | BIC |
|---|---|---|
| **(1,0,0)(1,0,1)₁₂** | **44,4** | 58,3 |
| (1,0,1)(1,0,1)₁₂ | 46,2 | 63,0 |
| (2,0,0)(1,0,1)₁₂ | 46,2 | 62,9 |
| (1,0,0) sin estacionalidad | 46,6 | 54,9 |

Se reestima en cada origen con L-BFGS. Si no converge, se reintenta con Powell; si tampoco, ese
origen usa el pronóstico estacional y queda registrado en
`reports/backtest/sarima_sin_convergencia.txt`.

### Ridge directa

Una regresión lineal con penalización L2 **por cada horizonte** (12 modelos). Pronostica la
inflación anualizada de los próximos `h` meses con las variables de la [Fase 3](03_variables.md),
estandarizadas. La penalización se elige en cada origen por validación cruzada generalizada
(`RidgeCV`, 30 valores entre 0,01 y 1 000).

Es lineal a propósito: con entre 89 y 263 observaciones de entrenamiento según el origen y el horizonte, un modelo
simple generaliza mejor, y su pronóstico se puede descomponer en el aporte de cada variable (ver
*Qué lo mueve* en la app).

### Gradient boosting directo

Mismas variables y mismo esquema directo, con `HistGradientBoostingRegressor` (profundidad 3,
200 árboles, tasa 0,05, mínimo 10 observaciones por hoja). Está para comprobar si relaciones no
lineales mejoran el pronóstico con tan pocos datos.

### Ensamble

Promedio simple de SARIMA y Ridge. **Se fijó antes de ver los resultados del backtest.** Elegir el
ensamble después, combinando los modelos que mejor salieron, sobreestimaría su desempeño.

## Cómo se elige el modelo que muestra la app

Entre SARIMA, Ridge, gradient boosting y ensamble, el de menor error absoluto medio promediado en
los 12 horizontes del backtest. La elección se recalcula en cada actualización mensual y se guarda
en `data/processed/resumen.json`. Los resultados están en la [Fase 5](05_evaluacion.md).
