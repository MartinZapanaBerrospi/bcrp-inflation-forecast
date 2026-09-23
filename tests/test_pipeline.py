"""Pruebas del pipeline: calidad de datos, identidad del efecto base y ausencia de fuga de información."""

import numpy as np
import pandas as pd
import pytest

from src import dataset
from src.evaluate import diebold_mariano
from src.features import future_sum, known_part, load_panel, monthly_log, to_pi12
from src.models import Context, naive, ridge, sarima, seasonal


@pytest.fixture(scope="module")
def panel():
    return load_panel()


def test_quality_rules_pass_on_raw_data():
    report = dataset.checks(dataset.build_panel())
    assert report["cumple"].all(), report[~report["cumple"]]


@pytest.mark.parametrize("h", [1, 6, 11, 12])
def test_known_plus_future_rebuilds_12m_inflation(panel, h):
    """El pronóstico perfecto de los meses futuros, más el efecto base, da la inflación real."""
    l = monthly_log(panel)
    known, future = known_part(l, h), future_sum(l, h)
    origins = panel.index[12:-h]
    rebuilt = [to_pi12(known.loc[t], future.loc[t]) for t in origins]
    actual = panel["inflacion_12m"].loc[[t + h for t in origins]].to_numpy()
    assert np.allclose(rebuilt, actual, atol=1e-6)


@pytest.mark.parametrize("model", [naive, seasonal, ridge, sarima])
def test_no_look_ahead(panel, model):
    """Alterar los datos posteriores al origen no puede cambiar el pronóstico hecho en el origen."""
    t = pd.Period("2019-06", "M")
    before = model(Context(panel), t)
    shocked = panel.copy()
    after = shocked.index > t
    numeric = shocked.columns.difference(["meta_min", "meta_max"])
    shocked.loc[after, numeric] = shocked.loc[after, numeric] * 3 + 5
    assert np.allclose(before, model(Context(shocked), t), atol=1e-9)


def test_forecasts_are_reasonable(panel):
    ctx = Context(panel)
    t = panel.index[-1]
    for model in (seasonal, ridge, sarima):
        preds = model(ctx, t)
        assert preds.shape == (12,)
        assert np.all(np.isfinite(preds)) and np.all((preds > -5) & (preds < 20))


def test_diebold_mariano_is_antisymmetric():
    """Intercambiar los modelos cambia el signo del estadístico y deja igual el p-valor."""
    rng = np.random.default_rng(0)
    a, b = rng.normal(0, 1.0, 120), rng.normal(0, 1.2, 120)
    s1, p1 = diebold_mariano(a, b, h=3)
    s2, p2 = diebold_mariano(b, a, h=3)
    assert s1 == pytest.approx(-s2) and p1 == pytest.approx(p2)


def test_diebold_mariano_detects_a_clearly_better_model():
    rng = np.random.default_rng(1)
    good, bad = rng.normal(0, 0.5, 200), rng.normal(0, 2.0, 200)
    stat, p = diebold_mariano(good, bad, h=1)
    assert stat < 0 and p < 0.01
