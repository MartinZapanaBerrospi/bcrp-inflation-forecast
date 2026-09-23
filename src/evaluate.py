"""Fase 5 — Evaluación del backtest y pronóstico vigente.

Lee reports/backtest/predicciones.csv y produce:

- reports/backtest/metricas_horizonte.csv   error por modelo y horizonte, relativo al ingenuo
- reports/backtest/metricas_periodo.csv     error por etapa (estable, pandemia, choque, reciente)
- reports/backtest/diebold_mariano.csv      ¿la mejora frente al ingenuo es significativa?
- reports/backtest/cobertura.csv            cobertura real de los intervalos de 80 % y 95 %
- reports/backtest/intervalos.csv           intervalos que habría tenido cada pronóstico histórico
- data/processed/pronostico.csv             pronóstico vigente con intervalos y probabilidades
- data/processed/contribuciones.csv         qué mueve el pronóstico de la Ridge a 12 meses
- data/processed/resumen.json               cifras clave para la app y el README

Los intervalos son conformales: se construyen con los errores que el modelo ya había cometido en
ese mismo horizonte, y solo con errores cuyo mes objetivo ya se había observado en el origen.

Uso:
    python -m src.evaluate
"""

import json

import numpy as np
import pandas as pd
from scipy import stats

from src import config
from src.features import FEATURE_LABELS, load_panel
from src.models import ENSEMBLE, Context, _direct, make_ridge

BT = config.REPORTS / "backtest"
CANDIDATES = ["sarima", "ridge", "gbm", "ensamble"]
MIN_PAST_ERRORS = 24
PERIODS = [("Estable (2013–2019)", "2013-01", "2019-12"), ("Pandemia (2020–2021)", "2020-01", "2021-12"),
           ("Choque inflacionario (2022–2023)", "2022-01", "2023-12"), ("Reciente (2024–2026)", "2024-01", "2026-12")]


def load_predictions() -> pd.DataFrame:
    p = pd.read_csv(BT / "predicciones.csv")
    ens = (p[p["modelo"].isin(ENSEMBLE)].groupby(["origen", "h", "objetivo"], as_index=False)
           .agg(pronostico=("pronostico", "mean"), real=("real", "first")))
    ens["modelo"] = "ensamble"
    p = pd.concat([p, ens], ignore_index=True).dropna(subset=["pronostico"])
    p["error"] = p["pronostico"] - p["real"]
    return p


def horizon_metrics(p: pd.DataFrame) -> pd.DataFrame:
    ev = p.dropna(subset=["real"])
    naive = ev[ev["modelo"] == "ingenuo"].set_index(["origen", "h"])["error"].abs()
    rows = []
    for (model, h), g in ev.groupby(["modelo", "h"]):
        g = g.set_index(["origen", "h"])
        mae = g["error"].abs().mean()
        rows.append({"modelo": model, "h": h, "n": len(g), "mae": mae,
                     "rmse": np.sqrt((g["error"] ** 2).mean()),
                     "sesgo": g["error"].mean(),
                     "mae_relativo_ingenuo": mae / naive.loc[g.index].mean()})
    return pd.DataFrame(rows)


def period_metrics(p: pd.DataFrame) -> pd.DataFrame:
    ev = p.dropna(subset=["real"]).copy()
    ev["origen_p"] = pd.PeriodIndex(ev["origen"], freq="M")
    rows = []
    for label, a, b in PERIODS:
        sub = ev[(ev["origen_p"] >= pd.Period(a, "M")) & (ev["origen_p"] <= pd.Period(b, "M"))]
        for (model, h), g in sub[sub["h"].isin([3, 6, 12])].groupby(["modelo", "h"]):
            rows.append({"periodo": label, "modelo": model, "h": h, "n": len(g), "mae": g["error"].abs().mean()})
    return pd.DataFrame(rows)


def diebold_mariano(e1: np.ndarray, e2: np.ndarray, h: int) -> tuple[float, float]:
    """DM con pérdida absoluta, varianza HAC (h−1 rezagos) y corrección de Harvey-Leybourne-Newbold.

    Estadístico negativo: el modelo 1 tiene menor error que el 2.
    """
    d = np.abs(e1) - np.abs(e2)
    n = len(d)
    mean = d.mean()
    dc = d - mean
    gamma = [np.dot(dc[k:], dc[:n - k]) / n for k in range(h)]
    var = gamma[0] + 2 * sum((1 - k / h) * gamma[k] for k in range(1, h))
    dm = mean / np.sqrt(var / n)
    correction = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    stat = dm * correction
    return float(stat), float(2 * stats.t.sf(abs(stat), df=n - 1))


def dm_tests(p: pd.DataFrame) -> pd.DataFrame:
    ev = p.dropna(subset=["real"])
    naive = ev[ev["modelo"] == "ingenuo"].set_index(["origen", "h"])["error"]
    rows = []
    for (model, h), g in ev[ev["modelo"] != "ingenuo"].groupby(["modelo", "h"]):
        g = g.set_index(["origen", "h"]).sort_index()
        stat, pval = diebold_mariano(g["error"].to_numpy(), naive.loc[g.index].to_numpy(), h)
        rows.append({"modelo": model, "h": h, "n": len(g), "dm": stat, "p_valor": pval,
                     "mejor_que_ingenuo_5pct": bool(stat < 0 and pval < 0.05)})
    return pd.DataFrame(rows)


def conformal(p: pd.DataFrame) -> pd.DataFrame:
    """Intervalo de cada pronóstico histórico con los errores ya resueltos en su origen."""
    out = []
    for (model, h), g in p.groupby(["modelo", "h"]):
        g = g.sort_values("origen")
        resolved = g.dropna(subset=["real"])[["objetivo", "error"]]
        for _, r in g.iterrows():
            past = resolved.loc[resolved["objetivo"] <= r["origen"], "error"].to_numpy()
            if len(past) < MIN_PAST_ERRORS:
                continue
            q = np.quantile(past, [0.025, 0.10, 0.90, 0.975])
            out.append({"origen": r["origen"], "h": h, "objetivo": r["objetivo"], "modelo": model,
                        "pronostico": r["pronostico"], "real": r["real"],
                        "p025": r["pronostico"] - q[3], "p10": r["pronostico"] - q[2],
                        "p90": r["pronostico"] - q[1], "p975": r["pronostico"] - q[0]})
    return pd.DataFrame(out)


def coverage(intervals: pd.DataFrame) -> pd.DataFrame:
    ev = intervals.dropna(subset=["real"])
    ev = ev.assign(en80=(ev["real"] >= ev["p10"]) & (ev["real"] <= ev["p90"]),
                   en95=(ev["real"] >= ev["p025"]) & (ev["real"] <= ev["p975"]))
    return (ev.groupby(["modelo", "h"], as_index=False)
            .agg(n=("en80", "size"), cobertura_80=("en80", "mean"), cobertura_95=("en95", "mean")))


def current_forecast(p: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    last = p["origen"].max()
    ctx = Context(panel)
    t = pd.Period(last, "M")
    rows = []
    for (model, h), g in p.groupby(["modelo", "h"]):
        now = g[g["origen"] == last]
        if now.empty:
            continue
        pred = float(now["pronostico"].iloc[0])
        errors = g.dropna(subset=["real"])["error"].to_numpy()
        sims = pred - errors  # distribución predictiva empírica
        target = pd.Period(last, "M") + h
        low, high = 1.0, 3.0
        known = float(ctx.known[h].loc[t])
        rows.append({"modelo": model, "h": h, "objetivo": str(target), "pronostico": pred,
                     # Inflación de 12 meses si los precios no se movieran en los próximos h meses:
                     # lo que ya aportan los meses observados que siguen dentro de la ventana
                     "piso_meses_conocidos": float(np.expm1(known) * 100),
                     "aporte_meses_futuros_pp": float((np.log1p(pred / 100) - known) * 100),
                     "p025": np.quantile(sims, 0.025), "p10": np.quantile(sims, 0.10),
                     "p90": np.quantile(sims, 0.90), "p975": np.quantile(sims, 0.975),
                     "prob_en_rango": float(np.mean((sims >= low) & (sims <= high))),
                     "prob_sobre_rango": float(np.mean(sims > high)),
                     "n_errores": len(errors)})
    return pd.DataFrame(rows)


def ridge_contributions(panel: pd.DataFrame, h: int = 12) -> pd.DataFrame:
    """Aporte de cada variable al pronóstico Ridge a h meses (en pp de inflación anualizada)."""
    ctx = Context(panel)
    t = panel.index[-1]
    _, fitted = _direct(ctx, t, make_ridge)
    model, cols = fitted[h]
    scaler, reg = model.named_steps["standardscaler"], model.named_steps["ridgecv"]
    x = ctx.design(t, h)[cols].to_numpy(dtype=float)
    z = (x - scaler.mean_) / scaler.scale_
    contrib = reg.coef_ * z
    df = pd.DataFrame({"variable": cols, "valor_actual": x, "promedio_historico": scaler.mean_,
                       "aporte_pp": contrib})
    months = df["variable"].str.startswith("mes_")
    season = pd.DataFrame([{"variable": "mes_calendario", "valor_actual": np.nan, "promedio_historico": np.nan,
                            "aporte_pp": df.loc[months, "aporte_pp"].sum()}])
    df = pd.concat([df[~months], season], ignore_index=True)
    labels = FEATURE_LABELS | {"mes_calendario": "Mes del año del pronóstico"}
    df["etiqueta"] = df["variable"].map(labels)
    df.attrs["base"] = float(reg.intercept_)
    df.attrs["alpha"] = float(reg.alpha_)
    return df.sort_values("aporte_pp", key=np.abs, ascending=False)


def main() -> None:
    panel = load_panel()
    p = load_predictions()

    hm = horizon_metrics(p)
    pm = period_metrics(p)
    dm = dm_tests(p)
    intervals = conformal(p)
    cov = coverage(intervals)
    fc = current_forecast(p, panel)
    contrib = ridge_contributions(panel)

    for name, df in [("metricas_horizonte", hm), ("metricas_periodo", pm), ("diebold_mariano", dm),
                     ("cobertura", cov), ("intervalos", intervals)]:
        df.to_csv(BT / f"{name}.csv", index=False, float_format="%.5f", lineterminator="\n")
    fc.to_csv(config.PROCESSED / "pronostico.csv", index=False, float_format="%.5f", lineterminator="\n")
    contrib.to_csv(config.PROCESSED / "contribuciones.csv", index=False, float_format="%.5f", lineterminator="\n")

    avg = hm[hm["modelo"].isin(CANDIDATES)].groupby("modelo")["mae"].mean().sort_values()
    best = avg.index[0]
    best_fc = fc[fc["modelo"] == best].sort_values("h")
    back = best_fc[best_fc["pronostico"] <= 3.0]
    last = panel.index[-1]
    summary = {
        "ultimo_mes": str(last),
        "inflacion_actual": float(panel.loc[last, "inflacion_12m"]),
        "sae_actual": float(panel.loc[last, "sae_12m"]),
        "expectativa_actual": float(panel.loc[last, "expectativa_12m"]),
        "tasa_referencia": float(panel.loc[last, "tasa_referencia"]),
        "mejor_modelo": best,
        "mae_promedio": {k: float(v) for k, v in avg.items()},
        "retorno_al_rango": back["objetivo"].iloc[0] if len(back) else None,
        "pronostico_12m": float(best_fc["pronostico"].iloc[-1]),
        "prob_en_rango_12m": float(best_fc["prob_en_rango"].iloc[-1]),
        "ridge_base_12m": contrib.attrs["base"],
        "ridge_alpha_12m": contrib.attrs["alpha"],
    }
    (config.PROCESSED / "resumen.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                                                  encoding="utf-8", newline="\n")

    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(hm.pivot(index="h", columns="modelo", values="mae").round(3))
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
