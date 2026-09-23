"""Páginas de la app. Los textos se arman con los datos para que sigan siendo ciertos cada mes."""

import numpy as np
import pandas as pd
import streamlit as st

from app import charts, data
from app.data import MODEL_LABELS, month_label, num, pct

REPO = "https://github.com/MartinZapanaBerrospi/bcrp-inflation-forecast"
DOCS = f"{REPO}/blob/main/docs"
PLOT_CONFIG = {"displayModeBar": False, "locale": "es"}


def _plot(fig):
    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)


def _streak_outside(panel: pd.DataFrame) -> str | None:
    """Primer mes de la racha actual fuera del rango meta (None si hoy está dentro)."""
    outside = (panel["inflacion_12m"] > panel["meta_max"]) | (panel["inflacion_12m"] < panel["meta_min"])
    if not outside.iloc[-1]:
        return None
    start = len(outside) - 1
    while start > 0 and outside.iloc[start - 1]:
        start -= 1
    return panel["periodo"].iloc[start]


# ---------------------------------------------------------------------------------------------
def inflacion_hoy():
    panel = data.panel()
    last, prev = panel.iloc[-1], panel.iloc[-2]
    st.title("Inflación en Lima Metropolitana")
    st.caption(f"IPC publicado por el BCRP hasta {month_label(last['periodo'], long=True)}.")

    c = st.columns(4)
    c[0].metric("Inflación 12 meses", pct(last["inflacion_12m"]),
                f"{num(last['inflacion_12m'] - prev['inflacion_12m'])} pp en el mes", delta_color="inverse")
    c[1].metric("Sin alimentos y energía", pct(last["sae_12m"]),
                f"{num(last['sae_12m'] - prev['sae_12m'])} pp", delta_color="inverse")
    c[2].metric("Expectativa a 12 meses", pct(last["expectativa_12m"]), help="Encuesta de expectativas del BCRP")
    c[3].metric("Tasa de referencia", pct(last["tasa_referencia"]))

    start = _streak_outside(panel)
    low, high = last["meta_min"], last["meta_max"]
    if start:
        st.warning(f"**Fuera del rango meta** ({pct(low, 0)}–{pct(high, 0)}) desde {month_label(start, long=True)}.",
                   icon=":material/warning:")
    else:
        st.success(f"Dentro del rango meta ({pct(low, 0)}–{pct(high, 0)}).", icon=":material/check_circle:")

    st.subheader("Inflación de 12 meses, 2003–hoy")
    _plot(charts.history_chart(panel))

    left, right = st.columns(2)
    with left:
        st.subheader("Variación mensual frente a un mes normal")
        _plot(charts.monthly_bars(panel))
        recent = panel.tail(12)
        top = recent.loc[recent["ipc_var_mensual"].idxmax()]
        ref = panel[(panel["periodo"] >= "2007-01") & (panel["periodo"] <= "2025-12")]
        normal = ref[pd.PeriodIndex(ref["periodo"], freq="M").month == pd.Period(top["periodo"], "M").month][
            "ipc_var_mensual"].mean()
        st.caption(f"El mes más inflacionario del último año fue {month_label(top['periodo'], long=True)}: "
                   f"{pct(top['ipc_var_mensual'])}, frente a {pct(normal)} de un mes igual en promedio (2007–2025). "
                   "Ese mes seguirá pesando en la inflación de 12 meses hasta que salga de la ventana.")
    with right:
        st.subheader("Transables y no transables, 12 meses")
        _plot(charts.components_chart(panel))
        st.caption("Transables: bienes cuyo precio depende del mercado internacional. No transables: servicios y "
                   "bienes de precio local.")


# ---------------------------------------------------------------------------------------------
def pronostico():
    panel, fc_all, s = data.panel(), data.forecast(), data.summary()
    st.title("Pronóstico a 12 meses")
    models = ["ensamble", "sarima", "ridge", "gbm", "estacional", "ingenuo"]
    best = s["mejor_modelo"]
    choice = st.segmented_control("Modelo", models, default=best, format_func=lambda m: MODEL_LABELS[m])
    choice = choice or best
    if choice == best:
        st.caption(f"{MODEL_LABELS[best]}: el de menor error promedio en el backtest (ver *Validación*).")

    fc = fc_all[fc_all["modelo"] == choice].sort_values("h")
    last12 = fc.iloc[-1]
    back = fc[fc["pronostico"] <= 3.0]
    dec = fc[fc["objetivo"].dt.month == 12]

    c = st.columns(4)
    c[0].metric(f"Inflación a {month_label(fc['objetivo'].iloc[-1].to_period('M'))}", pct(last12["pronostico"]),
                help=f"Intervalo 80 %: {pct(last12['p10'])} a {pct(last12['p90'])}")
    c[1].metric("Prob. en rango meta", pct(last12["prob_en_rango"] * 100, 0),
                help=f"En {month_label(fc['objetivo'].iloc[-1].to_period('M'), long=True)}, entre 1 % y 3 %")
    c[2].metric("Vuelve bajo 3 %", month_label(back["objetivo"].iloc[0].to_period("M")) if len(back) else "Sin retorno",
                help="Primer mes en que el pronóstico central queda en 3 % o menos")
    if len(dec):
        c[3].metric(f"Cierre de {dec['objetivo'].iloc[0].year}", pct(dec["pronostico"].iloc[0]))

    _plot(charts.fan_chart(panel, fc))
    st.caption("Bandas: intervalos de 80 % y 95 % construidos con los errores que el modelo cometió en el backtest "
               "en cada horizonte. Zona gris: rango meta del BCRP.")

    st.subheader("Por qué baja: el efecto base")
    left, right = st.columns([3, 2])
    with left:
        _plot(charts.base_effect_chart(fc, [month_label(d.to_period("M")) for d in fc["objetivo"]]))
    with right:
        drop = fc.set_index("h")["piso_meses_conocidos"].diff()
        h_drop = int(drop.idxmin())
        month_drop = fc.set_index("h").loc[h_drop, "objetivo"].to_period("M")
        exits = month_drop - 12
        st.markdown(
            "La inflación de 12 meses es la suma de los últimos 12 meses. Cada mes que pasa, entra un mes nuevo "
            "y **sale uno viejo**, y lo que sale ya se conoce.\n\n"
            f"La barra azul es la inflación que quedaría **si los precios no subieran nada** desde hoy: lo que "
            f"aportan los meses ya observados que siguen dentro de la ventana. Cae con fuerza en "
            f"**{month_label(month_drop, long=True)}** ({num(drop.min())} pp), cuando sale de la ventana "
            f"{month_label(exits, long=True)}.\n\n"
            "La barra naranja es lo único que el modelo tiene que pronosticar: la inflación de los meses por venir.")

    st.subheader("Detalle mensual")
    table = pd.DataFrame({
        "Mes": [month_label(d.to_period("M"), long=True) for d in fc["objetivo"]],
        "Pronóstico": fc["pronostico"].map(pct),
        "Intervalo 80 %": [f"{pct(a)} a {pct(b)}" for a, b in zip(fc["p10"], fc["p90"])],
        "Intervalo 95 %": [f"{pct(a)} a {pct(b)}" for a, b in zip(fc["p025"], fc["p975"])],
        "Prob. en rango meta": (fc["prob_en_rango"] * 100).map(lambda v: pct(v, 0)),
        "Prob. sobre 3 %": (fc["prob_sobre_rango"] * 100).map(lambda v: pct(v, 0)),
    })
    st.dataframe(table, hide_index=True, use_container_width=True, height=35 * (len(table) + 1) + 3)


# ---------------------------------------------------------------------------------------------
def validacion():
    hm, dm, cov, pm = (data.backtest(n) for n in ["metricas_horizonte", "diebold_mariano", "cobertura", "metricas_periodo"])
    iv = data.backtest("intervalos")
    panel = data.panel()
    st.title("¿Qué tan bueno es el pronóstico?")
    n_orig = hm[(hm["modelo"] == "ingenuo") & (hm["h"] == 1)]["n"].iloc[0]
    st.markdown(
        f"**Backtesting de origen móvil.** Desde enero de 2013, cada mes se reestimó cada modelo solo con los datos "
        f"que existían en esa fecha y se pronosticaron los 12 meses siguientes: hasta {n_orig} pronósticos por modelo "
        "y horizonte, comparados después con la inflación real.")

    show = st.multiselect("Modelos", list(MODEL_LABELS), default=["ingenuo", "estacional", "sarima", "ridge", "ensamble", "encuesta"],
                          format_func=lambda m: MODEL_LABELS[m])
    _plot(charts.mae_by_horizon(hm, MODEL_LABELS, show))
    st.caption("Error absoluto medio de la inflación de 12 meses pronosticada, en puntos porcentuales. "
               "La encuesta del BCRP solo se compara a 12 meses, su horizonte.")

    st.subheader("Resumen por horizonte")
    rows = []
    for m in ["estacional", "sarima", "ridge", "gbm", "ensamble", "encuesta"]:
        for h in [1, 3, 6, 12]:
            r = hm[(hm["modelo"] == m) & (hm["h"] == h)]
            if r.empty:
                continue
            d = dm[(dm["modelo"] == m) & (dm["h"] == h)]
            cv = cov[(cov["modelo"] == m) & (cov["h"] == h)]
            rows.append({"Modelo": MODEL_LABELS[m], "Horizonte": h, "Error medio (pp)": num(r["mae"].iloc[0]),
                         "vs. ingenuo": f"{num((r['mae_relativo_ingenuo'].iloc[0] - 1) * 100, 0)} %",
                         "Mejora significativa": "Sí" if d["mejor_que_ingenuo_5pct"].iloc[0] else "No",
                         "Cobertura 80 %": pct(cv["cobertura_80"].iloc[0] * 100, 0) if len(cv) else "—"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption("*vs. ingenuo*: diferencia de error frente a suponer que la inflación se queda donde está (negativo "
               "es mejor). *Mejora significativa*: prueba de Diebold-Mariano al 5 %. *Cobertura 80 %*: veces que el "
               "dato real cayó dentro del intervalo de 80 %.")

    st.subheader("Error a 12 meses según la etapa")
    p12 = pm[pm["h"] == 12].pivot(index="modelo", columns="periodo", values="mae")
    order = [p for p in ["Estable (2013–2019)", "Pandemia (2020–2021)", "Choque inflacionario (2022–2023)",
                         "Reciente (2024–2026)"] if p in p12.columns]
    p12 = p12[order].loc[[m for m in MODEL_LABELS if m in p12.index]]
    p12.index = [MODEL_LABELS[m] for m in p12.index]
    st.dataframe(p12.map(lambda v: num(v)), use_container_width=True)

    st.subheader("Máquina del tiempo")
    st.markdown("Elige una fecha y mira qué habría pronosticado el modelo con lo que se sabía ese mes.")
    model = st.selectbox("Modelo", ["ensamble", "sarima", "ridge", "gbm", "estacional", "ingenuo"],
                         format_func=lambda m: MODEL_LABELS[m], key="tm_model")
    sub = iv[iv["modelo"] == model]
    origins = sorted(sub["origen"].unique())
    default = "2022-01" if "2022-01" in origins else origins[len(origins) // 2]
    origin = st.select_slider("Mes de origen", options=origins, value=default,
                              format_func=lambda o: month_label(o, long=True))
    path = sub[sub["origen"] == origin].sort_values("h").copy()
    path["objetivo"] = pd.PeriodIndex(path["objetivo"], freq="M").to_timestamp(how="end").normalize()
    origin_ts = pd.Period(origin, "M").to_timestamp(how="end").normalize()
    _plot(charts.time_machine(panel, path, origin_ts))
    resolved = path.dropna(subset=["real"])
    if len(resolved):
        err = (resolved["pronostico"] - resolved["real"]).abs().mean()
        st.caption(f"Error medio de ese pronóstico en los {len(resolved)} meses ya observados: {num(err)} pp.")


# ---------------------------------------------------------------------------------------------
def que_lo_mueve():
    contrib, s = data.contributions(), data.summary()
    st.title("¿Qué mueve el pronóstico?")
    total = s["ridge_base_12m"] + contrib["aporte_pp"].sum()
    st.markdown(
        "La regresión Ridge es lineal: su pronóstico es un **valor base** (la inflación promedio de los próximos 12 "
        "meses en su historia de entrenamiento) más el **aporte de cada variable**, según qué tan lejos está hoy de "
        "su promedio y cuánto pesa en el modelo.\n\n"
        f"Valor base: **{pct(s['ridge_base_12m'])}**. Sumando los aportes de abajo se llega a {pct(total)} en escala "
        f"logarítmica, que equivale a una inflación de 12 meses de **{pct(float(np.expm1(total / 100) * 100))}**.")
    _plot(charts.contributions_chart(contrib))
    st.caption("Naranja: empuja el pronóstico hacia arriba. Azul: hacia abajo. Las variables se estandarizan antes de "
               "estimar, así que los aportes son comparables entre sí.")
    table = contrib.dropna(subset=["valor_actual"]).assign(
        Variable=lambda d: d["etiqueta"], Hoy=lambda d: d["valor_actual"].map(num),
        Promedio=lambda d: d["promedio_historico"].map(num), Aporte=lambda d: d["aporte_pp"].map(lambda v: f"{v:+.2f} pp".replace(".", ",")))
    st.dataframe(table[["Variable", "Hoy", "Promedio", "Aporte"]], hide_index=True, use_container_width=True)
    st.caption("Este desglose explica el modelo Ridge, que forma parte del ensamble. Describe asociaciones que el "
               "modelo aprendió en los datos, no efectos causales.")


# ---------------------------------------------------------------------------------------------
def como_se_hizo():
    st.title("Cómo se hizo")
    st.markdown(
        "Proyecto de ciencia de datos de punta a punta con **datos públicos del Banco Central de Reserva del Perú**. "
        f"Cada fase tiene su documento en el [repositorio]({REPO}).")
    phases = [
        ("0. Definición", "Pregunta, usuario, métricas y verificación de las fuentes", "00_definicion.md"),
        ("1. Adquisición", "13 series de BCRPData con manifiesto y hash SHA-256", "01_adquisicion.md"),
        ("2. Calidad", "8 reglas: huecos, vacíos y reconstrucción de la inflación desde el índice", "02_calidad.md"),
        ("3. Variables", "Descomposición de la inflación de 12 meses en efecto base y meses por venir", "03_variables.md"),
        ("4. Modelos", "3 referencias (ingenuo, estacional, encuesta) y 4 modelos (SARIMA, Ridge, boosting, ensamble)", "04_modelos.md"),
        ("5. Evaluación", "Backtest de origen móvil, Diebold-Mariano e intervalos conformales", "05_evaluacion.md"),
        ("6. App", "Esta aplicación, en Streamlit Community Cloud", "06_app.md"),
        ("8. Automatización", "Pruebas en cada cambio y actualización mensual de datos y pronóstico", "08_automatizacion.md"),
    ]
    for title, desc, doc in phases:
        st.markdown(f"**{title}** · {desc} · [documento]({DOCS}/{doc})")

    st.subheader("Reglas de calidad de los datos")
    q = data.quality().rename(columns={"regla": "Regla", "detalle": "Qué comprueba", "cumple": "Cumple", "valor": "Valor"})
    q["Cumple"] = q["Cumple"].map({True: "Sí", False: "No"})
    st.dataframe(q, hide_index=True, use_container_width=True)

    st.subheader("Límites")
    st.markdown(
        "- Son **pronósticos estadísticos**, no escenarios de política: no dicen qué pasaría si el BCRP moviera la tasa.\n"
        "- Los intervalos suponen que los errores futuros se parecerán a los del pasado. Un choque sin precedentes "
        "puede quedar fuera.\n"
        "- La encuesta de expectativas mide otra cosa (lo que esperan los agentes) y solo se compara a 12 meses.")
