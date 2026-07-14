"""Build the star schema and readiness scoring from the raw StatFin json-stat2.

Outputs:
  data/industry.db          — SQLite star schema
  data/powerbi/*.csv        — the same tables for Power BI Service
  data/scores.json          — sector composites (read by ai_summary.py)

Scoring (all documented in powerbi/MODEL.md):
  1. Pull latest non-null raw value per (sector, metric).
  2. Sum economic metrics from constituent TOL classes up to the 9 sectors.
  3. Min-max normalise each metric across the 9 sectors to 0–100.
  4. Weighted mean of normalised metrics -> two composites (0–100).
  5. Split each composite at its cross-sector mean -> a 2×2 priority quadrant.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from math import prod
from pathlib import Path

from config import (
    AXIS_ATTRACTIVENESS, AXIS_READINESS, ECONOMY_METRICS, ECONOMY_YEAR,
    READINESS_METRICS, READINESS_YEARS, SECTORS,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
CSV_DIR = DATA_DIR / "powerbi"
DB_PATH = DATA_DIR / "industry.db"
SCORES_PATH = DATA_DIR / "scores.json"


# --- json-stat2 access ---------------------------------------------------
class JsonStat:
    def __init__(self, payload: dict):
        self.ids = payload["id"]
        self.size = payload["size"]
        self.value = payload["value"]
        self.index = {
            dim: payload["dimension"][dim]["category"]["index"]
            for dim in self.ids
        }
        # strides for row-major flat array (last dim fastest)
        self.stride = [prod(self.size[i + 1:]) for i in range(len(self.size))]

    def get(self, coords: dict[str, str]):
        pos = 0
        for i, dim in enumerate(self.ids):
            pos += self.index[dim][coords[dim]] * self.stride[i]
        return self.value[pos]


def latest_nonnull(js: JsonStat, sector_code: str, metric_code: str, years: list[str]):
    """Return (value, year) for the newest year with a non-null value."""
    for year in years:  # years listed newest-first in config
        v = js.get({
            "toimiala_79_20180101": sector_code,
            "contentscode": metric_code,
            "timeperiod_y": year,
        })
        if v is not None:
            return float(v), year
    return None, None


# --- extraction ----------------------------------------------------------
def extract_readiness() -> dict:
    js = JsonStat(json.loads((RAW_DIR / "readiness.json").read_text()))
    out = {}
    for s in SECTORS:
        for code, _label, _w in READINESS_METRICS:
            val, year = latest_nonnull(js, s["code"], code, READINESS_YEARS)
            out[(s["id"], code)] = (val if val is not None else 0.0, year)
    return out


def extract_economy() -> dict:
    js = JsonStat(json.loads((RAW_DIR / "economy.json").read_text()))
    out = {}
    for s in SECTORS:
        for code, _label, _w in ECONOMY_METRICS:
            total = 0.0
            for econ in s["econ_codes"]:
                v = js.get({
                    "toimiala_79_20180101": econ,
                    "contentscode": code,
                    "timeperiod_y": ECONOMY_YEAR,
                })
                total += float(v) if v is not None else 0.0
            out[(s["id"], code)] = (total, ECONOMY_YEAR)
    return out


# --- scoring -------------------------------------------------------------
def minmax(values: dict[int, float]) -> dict[int, float]:
    lo, hi = min(values.values()), max(values.values())
    span = hi - lo
    return {k: (100.0 * (v - lo) / span if span else 50.0) for k, v in values.items()}


def composite(norm_by_metric: dict[str, dict[int, float]], metrics) -> dict[int, float]:
    scores = {s["id"]: 0.0 for s in SECTORS}
    total_w = sum(w for _c, _l, w in metrics)
    for code, _label, w in metrics:
        for sid, ns in norm_by_metric[code].items():
            scores[sid] += ns * w / total_w
    return scores


def quadrant(attr: float, ready: float, attr_mid: float, ready_mid: float) -> str:
    hi_a, hi_r = attr >= attr_mid, ready >= ready_mid
    if hi_a and hi_r:
        return "Lead — go-to-market now"
    if hi_a and not hi_r:
        return "Develop — high-value, needs enablement"
    if not hi_a and hi_r:
        return "Selective — quick wins"
    return "Monitor"


# --- build ---------------------------------------------------------------
def build():
    readiness = extract_readiness()
    economy = extract_economy()

    # dim_metric ---------------------------------------------------------
    dim_metric = []  # (metric_id, metric_code, name, axis, unit, weight)
    mid = 1
    code_to_mid = {}
    for code, label, w in READINESS_METRICS:
        dim_metric.append((mid, code, label, AXIS_READINESS, "% of enterprises", w))
        code_to_mid[code] = mid
        mid += 1
    for code, label, w in ECONOMY_METRICS:
        unit = "€1,000" if code == "yri_Liikevaihto" else (
            "staff-years" if code == "yri_Henkmaara" else "enterprises")
        dim_metric.append((mid, code, label, AXIS_ATTRACTIVENESS, unit, w))
        code_to_mid[code] = mid
        mid += 1

    # fact_metric (raw) --------------------------------------------------
    raw = {}  # code -> {sid: value}
    fact_rows = []  # (sector_id, metric_id, year, raw_value)
    for (sid, code), (val, year) in {**readiness, **economy}.items():
        raw.setdefault(code, {})[sid] = val
        fact_rows.append((sid, code_to_mid[code], year, val))

    # normalise ----------------------------------------------------------
    norm = {code: minmax(vals) for code, vals in raw.items()}
    fact_full = []  # (sector_id, metric_id, year, raw_value, norm_score)
    for sid, metric_id, year, val in fact_rows:
        code = next(c for c, m in code_to_mid.items() if m == metric_id)
        fact_full.append((sid, metric_id, year, round(val, 2), round(norm[code][sid], 1)))

    # composites ---------------------------------------------------------
    attr = composite(norm, ECONOMY_METRICS)
    ready = composite(norm, READINESS_METRICS)
    attr_mid = sum(attr.values()) / len(attr)
    ready_mid = sum(ready.values()) / len(ready)

    scored = []
    for s in SECTORS:
        a, r = attr[s["id"]], ready[s["id"]]
        scored.append({
            "sector_id": s["id"], "code": s["code"], "name": s["name"],
            "short": s["short"], "industrial": int(s["industrial"]),
            "attractiveness": round(a, 1), "readiness": round(r, 1),
            "combined": round((a + r) / 2, 1),
            "priority": quadrant(a, r, attr_mid, ready_mid),
        })
    scored.sort(key=lambda x: x["combined"], reverse=True)
    for rank, row in enumerate(scored, 1):
        row["rank"] = rank

    write_sqlite(dim_metric, fact_full, scored)
    write_csvs(dim_metric, fact_full, scored)
    SCORES_PATH.write_text(json.dumps(
        {"attr_mid": round(attr_mid, 1), "ready_mid": round(ready_mid, 1),
         "economy_year": ECONOMY_YEAR, "sectors": scored},
        ensure_ascii=False, indent=2))
    print(f"  scores.json: {len(scored)} sectors "
          f"(midlines attr={attr_mid:.0f}, ready={ready_mid:.0f})")
    top = ", ".join(f"{r['short']}" for r in scored[:3])
    print(f"  Top-3 priority sectors: {top}")


def write_sqlite(dim_metric, fact_full, scored):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS fact_metric;
        DROP TABLE IF EXISTS dim_sector;
        DROP TABLE IF EXISTS dim_metric;
        DROP TABLE IF EXISTS sector_score;
        CREATE TABLE dim_sector (
            sector_id INTEGER PRIMARY KEY, code TEXT, name TEXT,
            short TEXT, industrial INTEGER);
        CREATE TABLE dim_metric (
            metric_id INTEGER PRIMARY KEY, metric_code TEXT, name TEXT,
            axis TEXT, unit TEXT, weight REAL);
        CREATE TABLE fact_metric (
            sector_id INTEGER REFERENCES dim_sector(sector_id),
            metric_id INTEGER REFERENCES dim_metric(metric_id),
            year TEXT, raw_value REAL, norm_score REAL);
        CREATE TABLE sector_score (
            sector_id INTEGER REFERENCES dim_sector(sector_id),
            attractiveness REAL, readiness REAL, combined REAL,
            priority TEXT, rank INTEGER);
    """)
    cur.executemany("INSERT INTO dim_metric VALUES (?,?,?,?,?,?)", dim_metric)
    cur.executemany("INSERT INTO dim_sector VALUES (?,?,?,?,?)",
                    [(s["id"], s["code"], s["name"], s["short"], int(s["industrial"]))
                     for s in SECTORS])
    cur.executemany("INSERT INTO fact_metric VALUES (?,?,?,?,?)", fact_full)
    cur.executemany("INSERT INTO sector_score VALUES (?,?,?,?,?,?)",
                    [(r["sector_id"], r["attractiveness"], r["readiness"],
                      r["combined"], r["priority"], r["rank"]) for r in scored])
    con.commit()
    con.close()
    print(f"  SQLite: {DB_PATH.name} ({len(fact_full)} fact rows)")


def write_csvs(dim_metric, fact_full, scored):
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    tables = {
        "dim_sector": (["sector_id", "code", "name", "short", "industrial"],
                       [(s["id"], s["code"], s["name"], s["short"], int(s["industrial"]))
                        for s in SECTORS]),
        "dim_metric": (["metric_id", "metric_code", "name", "axis", "unit", "weight"],
                       dim_metric),
        "fact_metric": (["sector_id", "metric_id", "year", "raw_value", "norm_score"],
                        fact_full),
        "sector_score": (["sector_id", "attractiveness", "readiness", "combined",
                          "priority", "rank"],
                         [(r["sector_id"], r["attractiveness"], r["readiness"],
                           r["combined"], r["priority"], r["rank"]) for r in scored]),
    }
    for name, (header, rows) in tables.items():
        path = CSV_DIR / f"{name}.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        print(f"  CSV: {path.name} ({len(rows)} rows)")


def main():
    if not (RAW_DIR / "readiness.json").exists():
        raise SystemExit("Raw data missing — run ingest.py first.")
    print("Building star schema + readiness scores...")
    build()


if __name__ == "__main__":
    main()
