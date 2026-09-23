"""Gráficos de la app (Plotly). Un eje por gráfico; el color sigue a la serie, no a su posición."""

import pandas as pd
import plotly.graph_objects as go

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#fcfcfb"
BAND = "rgba(138, 137, 132, 0.14)"  # rango meta: gris neutro, nunca un color de serie

# Paleta categórica validada (orden fijo)
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")

MODEL_COLORS = {
    "ingenuo": MUTED, "estacional": YELLOW, "encuesta": MAGENTA, "sarima": AQUA,
    "ridge": VIOLET, "gbm": GREEN, "ensamble": ORANGE,
}


def base_layout(fig: go.Figure, height: int = 380, y_title: str | None = "%", legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=16, b=8), plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color=INK2),
        hovermode="x unified", separators=",.",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=12)),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="outside", tickcolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=y_title, title_font=dict(size=12))
    return fig


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"]


def spanish_months(fig: go.Figure, start, end, step: int = 6) -> go.Figure:
    """Marcas del eje x en español (Plotly no trae el idioma dentro de Streamlit)."""
    months = pd.period_range(pd.Timestamp(start).to_period("M"), pd.Timestamp(end).to_period("M"), freq="M")
    ticks = [m for m in months if (m.month - 1) % step == 0]
    fig.update_xaxes(tickvals=[m.to_timestamp(how="end").normalize() for m in ticks],
                     ticktext=[f"{MESES[m.month - 1]}-{str(m.year)[2:]}" for m in ticks], hoverformat="%m/%Y")
    return fig


def spanish_years(fig: go.Figure) -> go.Figure:
    fig.update_xaxes(tickformat="%Y", dtick="M24", hoverformat="%m/%Y")
    return fig


def target_band(fig: go.Figure, panel: pd.DataFrame, start=None, end=None) -> None:
    """Sombrea el rango meta vigente en cada mes (cambió en enero de 2007)."""
    df = panel
    if start is not None:
        df = df[df["fecha"] >= start]
    if end is not None:
        df = df[df["fecha"] <= end]
    x = list(df["fecha"])
    lo, hi = list(df["meta_min"]), list(df["meta_max"])
    if end is not None and end > x[-1]:
        x.append(end)
        lo.append(lo[-1])
        hi.append(hi[-1])
    fig.add_trace(go.Scatter(x=x, y=hi, mode="lines", line=dict(width=0, shape="hv"), hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=lo, mode="lines", line=dict(width=0, shape="hv"), fill="tonexty",
                             fillcolor=BAND, name="Rango meta BCRP", hoverinfo="skip"))


def fan_chart(panel: pd.DataFrame, fc: pd.DataFrame, history_months: int = 36) -> go.Figure:
    hist = panel.tail(history_months)
    fig = go.Figure()
    target_band(fig, panel, start=hist["fecha"].iloc[0], end=fc["objetivo"].max())
    last = hist.iloc[-1]
    x = [last["fecha"]] + list(fc["objetivo"])

    def band(lo, hi, alpha, name):
        fig.add_trace(go.Scatter(x=x, y=[last["inflacion_12m"]] + list(fc[hi]), mode="lines",
                                 line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=[last["inflacion_12m"]] + list(fc[lo]), mode="lines",
                                 line=dict(width=0), fill="tonexty", fillcolor=f"rgba(235, 104, 52, {alpha})",
                                 name=name, hoverinfo="skip"))

    band("p025", "p975", 0.12, "Intervalo 95 %")
    band("p10", "p90", 0.25, "Intervalo 80 %")
    fig.add_trace(go.Scatter(x=hist["fecha"], y=hist["inflacion_12m"], mode="lines", name="Inflación observada",
                             line=dict(color=BLUE, width=2.5),
                             hovertemplate="%{y:.2f} %<extra>Observada</extra>"))
    fig.add_trace(go.Scatter(x=x, y=[last["inflacion_12m"]] + list(fc["pronostico"]), mode="lines+markers",
                             name="Pronóstico", line=dict(color=ORANGE, width=2.5, dash="dot"),
                             marker=dict(size=7, color=ORANGE, line=dict(color=SURFACE, width=2)),
                             hovertemplate="%{y:.2f} %<extra>Pronóstico</extra>"))
    spanish_months(fig, hist["fecha"].iloc[0], fc["objetivo"].max())
    return base_layout(fig, height=420)


def history_chart(panel: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    target_band(fig, panel)
    fig.add_trace(go.Scatter(x=panel["fecha"], y=panel["inflacion_12m"], mode="lines", name="Inflación total",
                             line=dict(color=BLUE, width=2.2), hovertemplate="%{y:.2f} %<extra>Total</extra>"))
    fig.add_trace(go.Scatter(x=panel["fecha"], y=panel["sae_12m"], mode="lines",
                             name="Sin alimentos y energía", line=dict(color=ORANGE, width=1.6),
                             hovertemplate="%{y:.2f} %<extra>Sin alimentos y energía</extra>"))
    spanish_years(fig)
    return base_layout(fig, height=400)


def monthly_bars(panel: pd.DataFrame, months: int = 24) -> go.Figure:
    df = panel.tail(months).copy()
    ref = panel[(panel["periodo"] >= "2007-01") & (panel["periodo"] <= "2025-12")]
    seasonal = ref.groupby(pd.PeriodIndex(ref["periodo"], freq="M").month)["ipc_var_mensual"].mean()
    df["normal"] = [seasonal[pd.Period(p, "M").month] for p in df["periodo"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["fecha"], y=df["ipc_var_mensual"], name="Variación del mes",
                         marker=dict(color=BLUE, cornerradius=4), hovertemplate="%{y:.2f} %<extra>Del mes</extra>"))
    fig.add_trace(go.Scatter(x=df["fecha"], y=df["normal"], mode="markers", name="Promedio de ese mes 2007–2025",
                             marker=dict(symbol="line-ew", size=18, line=dict(color=INK, width=2.5)),
                             hovertemplate="%{y:.2f} %<extra>Promedio histórico</extra>"))
    fig.update_layout(bargap=0.25)
    spanish_months(fig, df["fecha"].iloc[0], df["fecha"].iloc[-1], step=3)
    return base_layout(fig, height=340)


def components_chart(panel: pd.DataFrame, months: int = 48) -> go.Figure:
    df = panel.tail(months)
    fig = go.Figure()
    for col, name, color in [("no_transables_12m", "No transables", VIOLET), ("transables_12m", "Transables", AQUA)]:
        fig.add_trace(go.Scatter(x=df["fecha"], y=df[col], mode="lines", name=name, line=dict(color=color, width=2),
                                 hovertemplate="%{y:.2f} %<extra>" + name + "</extra>"))
    spanish_months(fig, df["fecha"].iloc[0], df["fecha"].iloc[-1], step=12)
    return base_layout(fig, height=340)


def base_effect_chart(fc: pd.DataFrame, labels: list[str]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=fc["piso_meses_conocidos"], name="Ya asegurado por meses observados",
                         marker=dict(color=BLUE, cornerradius=4), hovertemplate="%{y:.2f} %<extra>Meses observados</extra>"))
    fig.add_trace(go.Bar(x=labels, y=fc["aporte_meses_futuros_pp"], name="Aporte de los meses por venir",
                         marker=dict(color=ORANGE, cornerradius=4), hovertemplate="%{y:.2f} pp<extra>Meses futuros</extra>"))
    fig.update_xaxes(type="category")
    fig.update_layout(barmode="stack", bargap=0.3)
    return base_layout(fig, height=360)


def mae_by_horizon(hm: pd.DataFrame, labels: dict, models: list[str]) -> go.Figure:
    fig = go.Figure()
    for m in models:
        d = hm[hm["modelo"] == m].sort_values("h")
        if m == "encuesta":
            fig.add_trace(go.Scatter(x=d["h"], y=d["mae"], mode="markers", name=labels[m],
                                     marker=dict(size=12, color=MODEL_COLORS[m], symbol="diamond",
                                                 line=dict(color=SURFACE, width=2)),
                                     hovertemplate="%{y:.2f} pp<extra>" + labels[m] + "</extra>"))
            continue
        fig.add_trace(go.Scatter(x=d["h"], y=d["mae"], mode="lines+markers", name=labels[m],
                                 line=dict(color=MODEL_COLORS[m], width=2.5 if m == "ensamble" else 2),
                                 marker=dict(size=8, line=dict(color=SURFACE, width=2)),
                                 hovertemplate="%{y:.2f} pp<extra>" + labels[m] + "</extra>"))
    fig.update_xaxes(title="Horizonte (meses)", dtick=1)
    return base_layout(fig, height=400, y_title="Error absoluto medio (pp)")


def time_machine(panel: pd.DataFrame, iv: pd.DataFrame, origin: pd.Timestamp) -> go.Figure:
    window = panel[(panel["fecha"] >= origin - pd.DateOffset(months=24)) &
                   (panel["fecha"] <= origin + pd.DateOffset(months=13))]
    fig = go.Figure()
    target_band(fig, panel, start=window["fecha"].iloc[0], end=window["fecha"].iloc[-1])
    x = list(iv["objetivo"])
    fig.add_trace(go.Scatter(x=x, y=list(iv["p90"]), mode="lines", line=dict(width=0), hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=list(iv["p10"]), mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(235, 104, 52, 0.22)", name="Intervalo 80 % de ese momento", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=window["fecha"], y=window["inflacion_12m"], mode="lines", name="Lo que pasó",
                             line=dict(color=BLUE, width=2.5), hovertemplate="%{y:.2f} %<extra>Observada</extra>"))
    fig.add_trace(go.Scatter(x=x, y=iv["pronostico"], mode="lines+markers", name="Lo que se pronosticó",
                             line=dict(color=ORANGE, width=2.5, dash="dot"),
                             marker=dict(size=7, line=dict(color=SURFACE, width=2)),
                             hovertemplate="%{y:.2f} %<extra>Pronóstico</extra>"))
    fig.add_vline(x=origin, line=dict(color=MUTED, width=1, dash="dash"))
    spanish_months(fig, window["fecha"].iloc[0], window["fecha"].iloc[-1])
    return base_layout(fig, height=380)


def contributions_chart(df: pd.DataFrame) -> go.Figure:
    d = df.sort_values("aporte_pp")
    colors = [ORANGE if v > 0 else BLUE for v in d["aporte_pp"]]
    fig = go.Figure(go.Bar(y=d["etiqueta"], x=d["aporte_pp"], orientation="h",
                           marker=dict(color=colors, cornerradius=4),
                           hovertemplate="%{x:+.2f} pp<extra>%{y}</extra>"))
    fig.update_xaxes(title="Aporte al pronóstico a 12 meses (pp)", zeroline=True, zerolinecolor=INK2)
    fig.update_yaxes(title=None, gridcolor="rgba(0,0,0,0)")
    return base_layout(fig, height=520, y_title=None, legend=False)
