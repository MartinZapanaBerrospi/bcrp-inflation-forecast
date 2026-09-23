"""Fase 1 — Descarga las series mensuales de BCRPData.

Cada serie se guarda tal como la entrega la API (JSON) en data/raw/, y queda registrada en
data/raw/manifest.csv con la URL, el número de meses, el último mes publicado y el hash SHA-256.
Las series se vuelven a bajar siempre: el BCRP publica un mes nuevo cada mes y a veces revisa
datos anteriores. Si el hash de una serie cambia sin que cambie su último mes, hubo revisión.

Uso:
    python -m src.extract
"""

import csv
import hashlib
import json
import time
from datetime import date, datetime, timezone

import requests

from src import config

FIELDS = ["codigo", "nombre", "descripcion", "url", "meses", "primer_mes", "ultimo_mes", "sha256", "descargado_en"]


def fetch(session: requests.Session, url: str, retries: int = 3) -> bytes:
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
            json.loads(resp.content)  # una página de error no es JSON: se reintenta
            return resp.content
        except (requests.RequestException, ValueError):
            if attempt == retries:
                raise
            time.sleep(2 * attempt)


def main() -> None:
    config.RAW.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = config.USER_AGENT
    end = f"{date.today().year}-12"  # la API devuelve hasta el último mes disponible
    rows = []
    for code, (name, desc) in config.SERIES.items():
        url = config.BCRP_URL.format(code=code, start=config.START, end=end)
        content = fetch(session, url)
        (config.RAW / f"{code}.json").write_bytes(content)
        periods = json.loads(content)["periods"]
        rows.append({
            "codigo": code, "nombre": name, "descripcion": desc, "url": url, "meses": len(periods),
            "primer_mes": periods[0]["name"], "ultimo_mes": periods[-1]["name"],
            "sha256": hashlib.sha256(content).hexdigest(),
            "descargado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        print(f"  {code} {name:20s} {len(periods)} meses, {periods[0]['name']} → {periods[-1]['name']}")
        time.sleep(0.3)
    with (config.RAW / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
