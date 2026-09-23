"""Fase 4 — Modelos de pronóstico.

Todos los modelos reciben el panel completo y un mes de origen t, usan solo información hasta t y
devuelven la inflación de 12 meses pronosticada para t+1 … t+12 (en %).

- Referencias: ingenuo (la inflación se queda donde está), estacional (los próximos meses repiten
  su promedio de los últimos 5 años) y encuesta (expectativa a 12 meses del BCRP, solo h = 12).
- SARIMA sobre la variación mensual.
- Ridge directa: una regresión por horizonte con las variables de src/features.py.
- Gradient boosting directo, con las mismas variables.
- Ensamble: promedio de SARIMA y Ridge, fijado antes de ver los resultados del backtest.

Los modelos que pronostican meses solo estiman la parte desconocida de la ventana; la parte
conocida (efecto base) se suma de forma exacta (ver src/features.py).
"""

import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX

from src import config
from src.features import build_features, future_sum, known_part, monthly_log, seasonal_sum, to_pi12

H = config.HORIZON
# Elegido por AIC entre 20 combinaciones, estimadas solo con 2003–2012 (antes del primer origen)
SARIMA_ORDER = (1, 0, 0)
SARIMA_SEASONAL = (1, 0, 1, 12)
FIRST_TRAIN = pd.Period("2004-09", "M")  # primer mes con todas las variables (cambio de tasa a 12 m)


class Context:
    """Precalcula lo que comparten los modelos para no repetirlo en cada origen."""

    def __init__(self, panel: pd.DataFrame):
        self.panel = panel
        self.l = monthly_log(panel)
        self.features = build_features(panel)
        self.known = {h: known_part(self.l, h) for h in range(1, H + 1)}
        self.future = {h: future_sum(self.l, h) for h in range(1, H + 1)}
        # Estacionalidad de los próximos h meses vista desde cada origen (solo usa datos hasta él)
        start = panel.index[0] + 12
        self.seasonal_sums = pd.DataFrame(
            [[seasonal_sum(self.l, t, h) for h in range(1, H + 1)] for t in panel.index[panel.index >= start]],
            index=panel.index[panel.index >= start], columns=range(1, H + 1))
        months = pd.DataFrame({f"mes_{m:02d}": (panel.index.month == m).astype(float) for m in range(2, 13)},
                              index=panel.index)
        self.designs = {}
        for h in range(1, H + 1):
            d = self.features.join(months)
            d["estacional"] = self.seasonal_sums[h] * 1200 / h  # anualizada, en %
            self.designs[h] = d

    def seasonal(self, t: pd.Period, h: int) -> float:
        return float(self.seasonal_sums.loc[t, h])

    def pi12_from_future(self, t: pd.Period, futures: list[float]) -> np.ndarray:
        return np.array([to_pi12(self.known[h].loc[t], futures[h - 1]) for h in range(1, H + 1)])

    def design(self, t: pd.Period, h: int) -> pd.Series:
        return self.designs[h].loc[t]


# --- Referencias -------------------------------------------------------------------------------

def naive(ctx: Context, t: pd.Period) -> np.ndarray:
    return np.repeat(ctx.panel.loc[t, "inflacion_12m"], H)


def seasonal(ctx: Context, t: pd.Period) -> np.ndarray:
    return ctx.pi12_from_future(t, [ctx.seasonal(t, h) for h in range(1, H + 1)])


def survey(ctx: Context, t: pd.Period) -> np.ndarray:
    out = np.full(H, np.nan)
    out[H - 1] = ctx.panel.loc[t, "expectativa_12m"]
    return out


# --- SARIMA ------------------------------------------------------------------------------------

SARIMA_FALLBACKS: list[str] = []  # orígenes en que el optimizador no convergió


def sarima(ctx: Context, t: pd.Period) -> np.ndarray:
    y = (ctx.l.loc[:t] * 100).to_numpy()
    model = SARIMAX(y, order=SARIMA_ORDER, seasonal_order=SARIMA_SEASONAL, trend="c")
    for method in ("lbfgs", "powell"):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = model.fit(disp=False, maxiter=300, method=method)
            path = res.forecast(H) / 100
            if np.all(np.isfinite(path)):
                return ctx.pi12_from_future(t, list(np.cumsum(path)))
        except (np.linalg.LinAlgError, ValueError):
            continue
    # Si ningún optimizador converge, se usa el perfil estacional y se deja constancia
    SARIMA_FALLBACKS.append(str(t))
    return seasonal(ctx, t)


# --- Modelos directos por horizonte ------------------------------------------------------------

def _training(ctx: Context, t: pd.Period, h: int) -> tuple[pd.DataFrame, pd.Series]:
    """Orígenes s con FIRST_TRAIN ≤ s ≤ t − h: su objetivo ya se observó en t."""
    origins = pd.period_range(FIRST_TRAIN, t - h, freq="M")
    X = ctx.designs[h].loc[origins]
    y = ctx.future[h].loc[origins] * 1200 / h  # inflación de los próximos h meses, anualizada
    return X, y


def _direct(ctx: Context, t: pd.Period, make_model) -> tuple[np.ndarray, dict]:
    futures, fitted = [], {}
    for h in range(1, H + 1):
        X, y = _training(ctx, t, h)
        model = make_model().fit(X, y)
        x_t = ctx.design(t, h).to_frame().T[X.columns]
        futures.append(float(model.predict(x_t)[0]) * h / 1200)
        fitted[h] = (model, X.columns)
    return ctx.pi12_from_future(t, futures), fitted


def make_ridge():
    return make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 30)))


def make_gbm():
    return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200,
                                         min_samples_leaf=10, random_state=0)


def ridge(ctx: Context, t: pd.Period) -> np.ndarray:
    return _direct(ctx, t, make_ridge)[0]


def gbm(ctx: Context, t: pd.Period) -> np.ndarray:
    return _direct(ctx, t, make_gbm)[0]


MODELS = {
    "ingenuo": naive,
    "estacional": seasonal,
    "encuesta": survey,
    "sarima": sarima,
    "ridge": ridge,
    "gbm": gbm,
}

ENSEMBLE = ("sarima", "ridge")

MODEL_LABELS = {
    "ingenuo": "Ingenuo (se mantiene)",
    "estacional": "Estacional histórico",
    "encuesta": "Encuesta de expectativas BCRP",
    "sarima": "SARIMA",
    "ridge": "Ridge directa",
    "gbm": "Gradient boosting",
    "ensamble": "Ensamble SARIMA + Ridge",
}
