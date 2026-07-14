"""Ingest Finnish industry data from Statistics Finland (StatFin PxWeb API).

Two open tables, no API key required:
  1. 14yc — Use of IT in enterprises, by industry  -> AI / robotics / IoT / cloud
  2. 13vy — Enterprises by industry                -> turnover / personnel / count

Raw json-stat2 responses land in data/raw/; transform.py builds the star schema.
Source: https://pxdata.stat.fi/PxWeb/  (CC BY 4.0, Statistics Finland)
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import (
    ECONOMY_METRICS, ECONOMY_TABLE, ECONOMY_YEAR,
    READINESS_METRICS, READINESS_TABLE, READINESS_YEARS, SECTORS,
)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
API = "https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/{folder}/{table}.px"


def post_query(folder: str, table: str, query: list[dict]) -> dict:
    body = json.dumps({"query": query, "response": {"format": "json-stat2"}}).encode()
    req = Request(
        API.format(folder=folder, table=table),
        data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "finland-industry-5g-readiness"},
    )
    with urlopen(req, timeout=60) as resp:
        return json.load(resp)


def save_raw(name: str, payload: dict) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def sel(code: str, values: list[str]) -> dict:
    return {"code": code, "selection": {"filter": "item", "values": values}}


def ingest_readiness() -> None:
    folder, table = READINESS_TABLE
    print(f"Fetching readiness (StatFin {table})...")
    query = [
        sel("toimiala_79_20180101", [s["code"] for s in SECTORS]),
        sel("contentscode", [m[0] for m in READINESS_METRICS]),
        sel("timeperiod_y", READINESS_YEARS),
    ]
    payload = post_query(folder, table, query)
    path = save_raw("readiness", payload)
    print(f"  OK: {len(payload['value'])} cells -> {path.name}")


def ingest_economy() -> None:
    folder, table = ECONOMY_TABLE
    print(f"Fetching economy (StatFin {table})...")
    econ_codes = sorted({c for s in SECTORS for c in s["econ_codes"]})
    query = [
        sel("toimiala_79_20180101", econ_codes),
        sel("contentscode", [m[0] for m in ECONOMY_METRICS]),
        sel("timeperiod_y", [ECONOMY_YEAR]),
    ]
    payload = post_query(folder, table, query)
    path = save_raw("economy", payload)
    print(f"  OK: {len(payload['value'])} cells -> {path.name}")


def main() -> None:
    try:
        ingest_readiness()
        ingest_economy()
    except (HTTPError, URLError) as e:
        raise SystemExit(f"StatFin fetch failed: {e}")
    print("Done. Next: python3 transform.py")


if __name__ == "__main__":
    main()
