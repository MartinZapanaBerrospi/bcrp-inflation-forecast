"""Carga de los resultados del pipeline. La app no recalcula nada: lee lo que el pipeline dejó."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
BACKTEST = ROOT / "reports" / "backtest"

MODEL_LABELS = {
    "ingenuo": "Ingenuo",
    "estacional": "Estacional histórico",
    "encuesta": "Encuesta BCRP",
    "sarima": "SARIMA",
    "ridge": "Ridge",
    "gbm": "Gradient boosting",
    "ensamble": "Ensamble SARIMA + Ridge",
}
MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]


def month_label(period: str | pd.Period, long: bool = False) -> str:
    p = pd.Period(period, freq="M")
    names = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
             "octubre", "noviembre", "diciembre"] if long else MONTHS_ES
    return f"{names[p.month - 1]} {p.year}" if long else f"{names[p.month - 1]}-{str(p.year)[2:]}"


def pct(x: float, decimals: int = 2) -> str:
    return f"{x:,.{decimals}f} %".replace(",", "X").replace(".", ",").replace("X", ".")


def num(x: float, decimals: int = 2) -> str:
    return f"{x:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _periods(df: pd.DataFrame, *cols: str) -> pd.DataFrame:
    for c in cols:
        df[c] = pd.PeriodIndex(df[c], freq="M").to_timestamp(how="end").normalize()
    return df


@st.cache_data
def panel() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "panel.csv")
    df["fecha"] = pd.PeriodIndex(df["periodo"], freq="M").to_timestamp(how="end").normalize()
    return df


@st.cache_data
def forecast() -> pd.DataFrame:
    return _periods(pd.read_csv(PROCESSED / "pronostico.csv"), "objetivo")


@st.cache_data
def summary() -> dict:
    return json.loads((PROCESSED / "resumen.json").read_text(encoding="utf-8"))


@st.cache_data
def contributions() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "contribuciones.csv")


@st.cache_data
def backtest(name: str) -> pd.DataFrame:
    return pd.read_csv(BACKTEST / f"{name}.csv")


@st.cache_data
def quality() -> pd.DataFrame:
    return pd.read_csv(ROOT / "reports" / "calidad_datos.csv")
