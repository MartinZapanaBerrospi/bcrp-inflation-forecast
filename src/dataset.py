"""Fases 2 y 3 — Del JSON de BCRPData a un panel mensual validado.

Construye data/processed/panel.csv: una fila por mes y una columna por serie, con los nombres
de src/config.py, y corre las validaciones de calidad antes de escribirlo.

Uso:
    python -m src.dataset
"""

import json
import sys

import numpy as np
import pandas as pd

from src import config

MONTHS = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8,
          "Sep": 9, "Set": 9, "Oct": 10, "Nov": 11, "Dic": 12}


def parse_period(name: str) -> pd.Period:
    month, year = name.split(".")
    return pd.Period(f"{year}-{MONTHS[month]:02d}", freq="M")


def read_series(code: str) -> pd.Series:
    payload = json.loads((config.RAW / f"{code}.json").read_text(encoding="utf-8"))
    idx = [parse_period(p["name"]) for p in payload["periods"]]
    # La API marca los meses sin dato como "n.d."; se leen como vacío
    values = pd.to_numeric([p["values"][0] for p in payload["periods"]], errors="coerce")
    return pd.Series(values, index=pd.PeriodIndex(idx, freq="M"))


def build_panel() -> pd.DataFrame:
    panel = pd.DataFrame({name: read_series(code) for code, (name, _) in config.SERIES.items()})
    full = pd.period_range(panel.index.min(), panel.index.max(), freq="M")
    panel = panel.reindex(full)
    panel.index.name = "periodo"
    return panel


def target_range(period: pd.Period) -> tuple[float, float]:
    for start, end, low, high in config.TARGET_RANGES:
        if pd.Period(start, "M") <= period <= pd.Period(end, "M"):
            return low, high
    raise ValueError(period)


def checks(panel: pd.DataFrame) -> pd.DataFrame:
    """Reglas de calidad. Cada una compara el dato con algo que debería cumplir por definición."""
    out = []

    def add(rule, detail, ok, value):
        out.append({"regla": rule, "detalle": detail, "cumple": bool(ok), "valor": value})

    idx = panel.index
    add("Q1", "Meses consecutivos, sin huecos", len(idx) == (idx.max() - idx.min()).n + 1, len(idx))

    missing = panel.drop(columns="tasa_referencia").isna().sum().sum()
    add("Q2", "Sin vacíos en las series (salvo tasa de referencia antes de sep-2003)", missing == 0, int(missing))

    first_rate = panel["tasa_referencia"].first_valid_index()
    add("Q3", "La tasa de referencia empieza en sep-2003 (inicio del instrumento)",
        first_rate == pd.Period("2003-09", "M"), str(first_rate))

    calc12 = (panel["ipc_indice"] / panel["ipc_indice"].shift(12) - 1) * 100
    diff12 = (calc12 - panel["inflacion_12m"]).abs().max()
    add("Q4", "Inflación 12 m publicada = calculada desde el índice (pp)", diff12 < 0.01, round(float(diff12), 6))

    calc1 = (panel["ipc_indice"] / panel["ipc_indice"].shift(1) - 1) * 100
    diff1 = (calc1 - panel["ipc_var_mensual"]).abs().max()
    add("Q5", "Variación mensual publicada = calculada desde el índice (pp)", diff1 < 0.01, round(float(diff1), 6))

    # La inflación de 12 meses es el producto de las 12 variaciones mensuales
    log_m = np.log1p(panel["ipc_var_mensual"] / 100)
    comp = (np.expm1(log_m.rolling(12).sum()) * 100 - panel["inflacion_12m"]).abs().max()
    add("Q6", "Inflación 12 m = composición de las 12 variaciones mensuales (pp)", comp < 0.01, round(float(comp), 6))

    sae_comp = (np.expm1(np.log1p(panel["sae_var_mensual"] / 100).rolling(12).sum()) * 100 - panel["sae_12m"]).abs().max()
    add("Q7", "Inflación sin alimentos y energía 12 m = composición de sus variaciones mensuales (pp)",
        sae_comp < 0.01, round(float(sae_comp), 6))

    ranges_ok = (panel[["tipo_cambio", "petroleo_wti", "trigo", "ipc_indice"]] > 0).all().all()
    add("Q8", "Precios, tipo de cambio e índice estrictamente positivos", ranges_ok, "")
    return pd.DataFrame(out)


def main() -> None:
    panel = build_panel()
    report = checks(panel)
    config.REPORTS.mkdir(exist_ok=True)
    report.to_csv(config.REPORTS / "calidad_datos.csv", index=False, lineterminator="\n")
    with pd.option_context("display.width", 200, "display.max_colwidth", 100):
        print(report.to_string(index=False))
    if not report["cumple"].all():
        sys.exit("Hay reglas de calidad que no se cumplen")

    low_high = [target_range(p) for p in panel.index]
    panel["meta_min"] = [lo for lo, _ in low_high]
    panel["meta_max"] = [hi for _, hi in low_high]
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    out = panel.copy()
    out.index = out.index.astype(str)
    # LF explícito: el archivo debe ser idéntico se genere en Windows o en Linux
    out.to_csv(config.PROCESSED / "panel.csv", float_format="%.6f", lineterminator="\n")
    print(f"panel: {len(out)} meses, {out.index[0]} → {out.index[-1]}")


if __name__ == "__main__":
    main()
