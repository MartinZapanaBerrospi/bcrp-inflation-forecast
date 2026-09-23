"""Fase 5 — Backtesting de origen móvil (ventana expansiva).

Para cada mes de origen t entre 2013-01 y el último mes publicado, cada modelo se reestima solo
con datos hasta t y pronostica la inflación de 12 meses de t+1 a t+12. El último origen es el
pronóstico vigente: sus valores reales todavía no existen.

Salida: reports/backtest/predicciones.csv (origen, horizonte, mes objetivo, modelo, pronóstico, real).

Uso:
    python -m src.backtest            # ~10 minutos: SARIMA y gradient boosting se reestiman 164 veces
"""

import time

import pandas as pd

from src import config
from src.features import load_panel
from src.models import MODELS, SARIMA_FALLBACKS, Context

FIRST_ORIGIN = pd.Period("2013-01", "M")
OUT = config.REPORTS / "backtest"


def run() -> pd.DataFrame:
    panel = load_panel()
    ctx = Context(panel)
    origins = pd.period_range(FIRST_ORIGIN, panel.index[-1], freq="M")
    actual = panel["inflacion_12m"]
    rows = []
    started = time.time()
    for i, t in enumerate(origins, 1):
        for name, model in MODELS.items():
            preds = model(ctx, t)
            for h, p in enumerate(preds, start=1):
                target = t + h
                rows.append((str(t), h, str(target), name, p, actual.get(target)))
        if i % 12 == 0 or i == len(origins):
            print(f"  {i}/{len(origins)} orígenes ({time.time() - started:.0f} s)", flush=True)
    return pd.DataFrame(rows, columns=["origen", "h", "objetivo", "modelo", "pronostico", "real"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    preds = run()
    preds.to_csv(OUT / "predicciones.csv", index=False, float_format="%.6f")
    (OUT / "sarima_sin_convergencia.txt").write_text("\n".join(SARIMA_FALLBACKS) + "\n", encoding="utf-8")
    print(f"{len(preds)} filas en {OUT.relative_to(config.ROOT)}; SARIMA sin convergencia en "
          f"{len(SARIMA_FALLBACKS)} orígenes: {SARIMA_FALLBACKS}")


if __name__ == "__main__":
    main()
