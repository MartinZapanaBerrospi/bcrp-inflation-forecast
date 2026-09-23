"""Parámetros del proyecto: series del BCRP, periodo, horizonte y rutas."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"

# Inicio del periodo: la meta explícita de inflación rige desde 2002 y las series completas
# del BCRP empiezan en 2003. El fin es el último mes publicado al momento de descargar.
START = "2003-1"

BCRP_URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{code}/json/{start}/{end}"

# código BCRPData -> (nombre en el proyecto, descripción)
SERIES = {
    "PN38705PM": ("ipc_indice", "IPC Lima Metropolitana, índice dic-2021 = 100"),
    "PN01271PM": ("ipc_var_mensual", "IPC, variación % mensual"),
    "PN01273PM": ("inflacion_12m", "IPC, variación % 12 meses (variable objetivo)"),
    "PN01276PM": ("sae_var_mensual", "IPC sin alimentos y energía, variación % mensual"),
    "PN01277PM": ("sae_12m", "IPC sin alimentos y energía, variación % 12 meses"),
    "PN01281PM": ("transables_12m", "IPC transables, variación % 12 meses"),
    "PN01283PM": ("no_transables_12m", "IPC no transables, variación % 12 meses"),
    "PN01287PM": ("mayorista_12m", "Índice de precios al por mayor, variación % 12 meses"),
    "PD12912AM": ("expectativa_12m", "Expectativa de inflación a 12 meses (encuesta BCRP)"),
    "PD04722MM": ("tasa_referencia", "Tasa de referencia de la política monetaria (%)"),
    "PN01210PM": ("tipo_cambio", "Tipo de cambio bancario promedio (S/ por US$)"),
    "PN01660XM": ("petroleo_wti", "Petróleo WTI, promedio del periodo (US$ por barril)"),
    "PN01661XM": ("trigo", "Trigo EE. UU., promedio del periodo (US$ por tonelada)"),
}

TARGET = "inflacion_12m"
HORIZON = 12  # meses hacia adelante

# Rango meta del BCRP: 2,5 % ± 1 hasta dic-2006; 2 % ± 1 desde ene-2007
TARGET_RANGES = [("2003-01", "2006-12", 1.5, 3.5), ("2007-01", "2100-12", 1.0, 3.0)]

USER_AGENT = "bcrp-inflation-forecast/1.0 (+https://github.com/MartinZapanaBerrospi/bcrp-inflation-forecast)"
