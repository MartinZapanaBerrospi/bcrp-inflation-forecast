"""Fase 3 — Variables del modelo y descomposición de la inflación de 12 meses.

La inflación de 12 meses es la composición de las 12 últimas variaciones mensuales. En logaritmos
es una suma, y eso permite separar lo que ya se sabe de lo que hay que pronosticar:

    log(1 + π12[t+h]) = Σ l[k], k = t+h-11 … t      (conocido en t: los meses que siguen en la ventana)
                      + Σ l[k], k = t+1 … t+h         (desconocido: lo único que se pronostica)

con l[k] = log(1 + variación mensual). El primer término es el efecto base: cuando un mes de
inflación alta sale de la ventana, la inflación de 12 meses baja aunque no pase nada nuevo.
"""

import numpy as np
import pandas as pd

from src import config


def load_panel() -> pd.DataFrame:
    panel = pd.read_csv(config.PROCESSED / "panel.csv", index_col="periodo")
    panel.index = pd.PeriodIndex(panel.index, freq="M")
    return panel


def monthly_log(panel: pd.DataFrame) -> pd.Series:
    return np.log1p(panel["ipc_var_mensual"] / 100)


def known_part(l: pd.Series, h: int) -> pd.Series:
    """Σ l[k] para k = t+h-11 … t: los 12-h meses que siguen en la ventana en t+h."""
    if h >= 12:
        return pd.Series(0.0, index=l.index)
    return l.rolling(12 - h).sum()


def future_sum(l: pd.Series, h: int) -> pd.Series:
    """Σ l[k] para k = t+1 … t+h: el objetivo de los modelos que pronostican meses."""
    return l.rolling(h).sum().shift(-h)


def to_pi12(known: float, future: float) -> float:
    return float(np.expm1(known + future) * 100)


def seasonal_profile(l: pd.Series, t: pd.Period, years: int = 5) -> pd.Series:
    """Variación mensual promedio (log) por mes calendario en los últimos `years` años hasta t."""
    window = l.loc[t - 12 * years + 1: t]
    return window.groupby(window.index.month).mean()


def seasonal_sum(l: pd.Series, t: pd.Period, h: int, years: int = 5) -> float:
    """Suma de los perfiles estacionales de los h meses siguientes a t."""
    prof = seasonal_profile(l, t, years)
    return float(sum(prof[(t + j).month] for j in range(1, h + 1)))


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Variables conocidas al cierre de cada mes t, en unidades interpretables (% o pp)."""
    l = monthly_log(panel)
    sae_l = np.log1p(panel["sae_var_mensual"] / 100)
    f = pd.DataFrame(index=panel.index)
    f["inflacion_12m"] = panel["inflacion_12m"]
    f["inflacion_3m_anualizada"] = l.rolling(3).mean() * 1200
    f["inflacion_6m_anualizada"] = l.rolling(6).mean() * 1200
    f["sae_12m"] = panel["sae_12m"]
    f["sae_3m_anualizada"] = sae_l.rolling(3).mean() * 1200
    f["no_transables_12m"] = panel["no_transables_12m"]
    f["transables_12m"] = panel["transables_12m"]
    f["mayorista_12m"] = panel["mayorista_12m"]
    f["expectativa_12m"] = panel["expectativa_12m"]
    f["tasa_referencia"] = panel["tasa_referencia"]
    f["tasa_var_12m_pp"] = panel["tasa_referencia"].diff(12)
    f["tipo_cambio_var_12m"] = panel["tipo_cambio"].pct_change(12) * 100
    f["petroleo_var_12m"] = panel["petroleo_wti"].pct_change(12) * 100
    f["trigo_var_12m"] = panel["trigo"].pct_change(12) * 100
    return f


FEATURE_LABELS = {
    "inflacion_12m": "Inflación 12 meses",
    "inflacion_3m_anualizada": "Inflación 3 meses (anualizada)",
    "inflacion_6m_anualizada": "Inflación 6 meses (anualizada)",
    "sae_12m": "Inflación sin alimentos y energía 12 m",
    "sae_3m_anualizada": "Sin alimentos y energía 3 m (anualizada)",
    "no_transables_12m": "Inflación no transables 12 m",
    "transables_12m": "Inflación transables 12 m",
    "mayorista_12m": "Precios al por mayor 12 m",
    "expectativa_12m": "Expectativa de inflación (encuesta)",
    "tasa_referencia": "Tasa de referencia",
    "tasa_var_12m_pp": "Cambio de la tasa de referencia 12 m",
    "tipo_cambio_var_12m": "Tipo de cambio, variación 12 m",
    "petroleo_var_12m": "Petróleo WTI, variación 12 m",
    "trigo_var_12m": "Trigo, variación 12 m",
    "estacional": "Estacionalidad de los próximos meses",
}
