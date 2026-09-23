"""Pruebas de los resultados que lee la app y de la propia app."""

import json

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src import config

PAGES = ["inflacion_hoy", "pronostico", "validacion", "que_lo_mueve", "como_se_hizo"]


@pytest.fixture(scope="module")
def forecast():
    return pd.read_csv(config.PROCESSED / "pronostico.csv")


def test_forecast_has_12_horizons_per_model(forecast):
    counts = forecast.groupby("modelo")["h"].nunique()
    assert (counts.drop("encuesta", errors="ignore") == 12).all()


def test_intervals_are_nested_and_probabilities_valid(forecast):
    assert (forecast["p025"] <= forecast["p10"]).all()
    assert (forecast["p10"] <= forecast["p90"]).all()
    assert (forecast["p90"] <= forecast["p975"]).all()
    assert forecast["prob_en_rango"].between(0, 1).all()
    assert (forecast["prob_en_rango"] + forecast["prob_sobre_rango"] <= 1 + 1e-9).all()


def test_forecast_starts_the_month_after_the_last_observation(forecast):
    panel = pd.read_csv(config.PROCESSED / "panel.csv")
    last = pd.Period(panel["periodo"].iloc[-1], "M")
    assert forecast.loc[forecast["h"] == 1, "objetivo"].eq(str(last + 1)).all()


def test_conformal_intervals_only_use_past_errors():
    """Ningún intervalo histórico existe antes de tener 24 errores resueltos en su horizonte."""
    iv = pd.read_csv(config.REPORTS / "backtest" / "intervalos.csv")
    first = iv.groupby(["modelo", "h"])["origen"].min().reset_index()
    for _, r in first.iterrows():
        earliest = pd.Period("2013-01", "M") + (24 - 1) + r["h"]
        assert pd.Period(r["origen"], "M") >= earliest


def test_summary_points_to_a_real_model():
    s = json.loads((config.PROCESSED / "resumen.json").read_text(encoding="utf-8"))
    assert s["mejor_modelo"] in {"sarima", "ridge", "gbm", "ensamble"}


def _render(root: str, page: str):
    import sys

    sys.path.insert(0, root)
    from app import views

    getattr(views, page)()


def test_entry_point_renders_without_errors():
    at = AppTest.from_file(str(config.ROOT / "streamlit_app.py"), default_timeout=60)
    at.run()
    assert not at.exception, at.exception


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_errors(page):
    at = AppTest.from_function(_render, kwargs={"root": str(config.ROOT), "page": page}, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
