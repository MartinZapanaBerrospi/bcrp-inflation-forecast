# Fase 1 — Adquisición

> Estado: **cerrada** (2026-09-23).

```bash
python -m src.extract
```

- Descarga las 13 series de [`src/config.py`](../src/config.py) desde BCRPData, de enero de 2003
  hasta el último mes publicado.
- Guarda cada respuesta sin modificar en `data/raw/{código}.json`.
- Escribe `data/raw/manifest.csv` con la URL, el número de meses, el primer y último mes, el hash
  SHA-256 y la hora de descarga.

## Decisiones

- **Se descarga todo cada vez.** A diferencia de archivos mensuales sueltos, una serie del BCRP
  es un solo recurso que crece cada mes. Bajarla entera cuesta 13 peticiones y permite detectar
  revisiones: si el hash de una serie cambia sin que cambie su último mes, el BCRP corrigió un
  dato anterior.
- **Los JSON crudos se versionan.** Pesan unos 200 KB en total y permiten reproducir el proyecto
  exacto aunque el BCRP revise una serie después.
- **Se valida que la respuesta sea JSON.** Una respuesta que no se puede leer (una página de error,
  por ejemplo) se reintenta hasta 3 veces y, si persiste, detiene el pipeline.
- **Pausa de 0,3 s entre series** e identificación del proyecto en el `User-Agent`.

## Resultado de la descarga del 2026-09-23

| Series | Meses | Periodo |
|---|---|---|
| 12 | 284 | ene-2003 → ago-2026 |
| Tasa de referencia | 276 | sep-2003 → ago-2026 |
