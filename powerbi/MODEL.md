# Power BI model & report build

Build the report from the CSVs in `data/powerbi/` using **Power BI Service in the
browser** (works on Mac — sign in with the Haaga-Helia Microsoft account).

## Fastest build (≈15 min, from the hosted CSV)

The repo is public, so the report-ready table is already online — no file upload needed.

1. **New report → Add data → CSV → "Link to file".** Paste this URL, leave
   Authentication = **Anonymous**, then **Next → Create**:
   ```
   https://raw.githubusercontent.com/annasebedash-creator/finland-industry-5g-readiness/main/data/powerbi/report_sectors.csv
   ```
   Columns: `Sector, Type, Attractiveness, Readiness, Combined, Rank, Priority`
   (Type = Industrial / Other; the composites and priority quadrant are pre-computed.)

2. **Three visuals on the canvas:**
   - **Priority matrix (scatter):** Visualizations → *Scatter chart*.
     X = **Readiness**, Y = **Attractiveness**, Legend = **Type**, Size = **Combined**,
     Values/Details = **Sector**. → the 2×2 matrix, Manufacturing & Energy top-right.
   - **Ranked table:** *Table* with **Rank, Sector, Attractiveness, Readiness, Priority**,
     sorted ascending by Rank.
   - **KPI card(s):** a *Card* on **Sector** filtered to `Rank = 1` (top target), and/or a
     *Card* counting sectors where `Priority` starts with "Lead".

3. **Title + save:** text box "Finnish Industry 5G & AI Readiness Index" → **File → Save**.

4. **Publish:** **File → Embed report → Publish to web (public)** → copy the link into the
   README and the portfolio "Live Report" button.
   > ⚠️ The Haaga-Helia tenant has **"Publish to web (public)" disabled** by admin policy
   > (confirmed 15.7.2026 — the option is absent from the report File menu). So a public
   > live-embed link is not available on that account. Options: (a) show a **screenshot**
   > of the report as portfolio proof; (b) rebuild the dataset under a **personal**
   > Microsoft account, where Publish to web is usually allowed; (c) export to PDF/PPT
   > via **File → Export** for a static shareable copy.

> This one flat table needs no relationships or DAX. For the fuller 4-page model
> (all readiness indicators, in-model DAX composites), use the four CSVs and the
> steps below.

## Import & model

1. Power BI Service → Workspace → **New → Semantic model** → upload the four CSVs:
   `dim_sector.csv`, `dim_metric.csv`, `fact_metric.csv`, `sector_score.csv`.
2. **Model view** → create relationships (all many-to-one, single direction):
   - `fact_metric[sector_id]` → `dim_sector[sector_id]`
   - `fact_metric[metric_id]` → `dim_metric[metric_id]`
   - `sector_score[sector_id]` → `dim_sector[sector_id]`

The composites in `sector_score` are already computed in `transform.py`, so the
report works with zero DAX. The measures below are optional — they reproduce the
composite **inside** the model to prove the scoring is transparent and re-runnable.

## DAX measures (optional but recommended)

```dax
-- Readiness composite, recomputed from the weighted metrics
Readiness Score =
DIVIDE(
    SUMX(
        FILTER(ALL(dim_metric), dim_metric[axis] = "AI & 5G readiness"),
        dim_metric[weight] * CALCULATE(AVERAGE(fact_metric[norm_score]))
    ),
    CALCULATE(SUM(dim_metric[weight]),
              FILTER(ALL(dim_metric), dim_metric[axis] = "AI & 5G readiness"))
)

-- Attractiveness composite (same pattern, other axis)
Attractiveness Score =
DIVIDE(
    SUMX(
        FILTER(ALL(dim_metric), dim_metric[axis] = "Market attractiveness"),
        dim_metric[weight] * CALCULATE(AVERAGE(fact_metric[norm_score]))
    ),
    CALCULATE(SUM(dim_metric[weight]),
              FILTER(ALL(dim_metric), dim_metric[axis] = "Market attractiveness"))
)

-- Priority quadrant vs. the cross-sector average of each composite
Priority Quadrant =
VAR a = [Attractiveness Score]
VAR r = [Readiness Score]
VAR aMid = AVERAGEX(ALL(dim_sector), [Attractiveness Score])
VAR rMid = AVERAGEX(ALL(dim_sector), [Readiness Score])
RETURN SWITCH(TRUE(),
    a >= aMid && r >= rMid, "Lead — go-to-market now",
    a >= aMid && r <  rMid, "Develop — needs enablement",
    a <  aMid && r >= rMid, "Selective — quick wins",
    "Monitor")

-- Rank by combined score (1 = top priority)
Priority Rank = RANKX(ALL(dim_sector), [Attractiveness Score] + [Readiness Score])
```

## Report pages

1. **The Recommendation (Overview)** — KPI cards (top sector, # sectors in "Lead",
   avg readiness); the **priority matrix** (scatter: X = `sector_score[readiness]`,
   Y = `sector_score[attractiveness]`, legend = `dim_sector[industrial]`, size =
   `sector_score[combined]`, detail = `dim_sector[short]`); ranked table with the
   `priority` column. Reference lines on both axes at the average.
2. **Readiness drivers** — matrix / bar of `fact_metric[raw_value]` (or `norm_score`)
   by `dim_sector[short]` × `dim_metric[name]`, filtered to the readiness axis. Shows
   *why* each sector scores as it does (AI use, autonomous robots, IoT, cloud…).
3. **Sector profile** — a slicer on `dim_sector[short]` drives a card: all seven
   readiness indicators + the three economic indicators for the selected sector.
4. **Executive brief** — a text/image page holding `data/executive_brief.md`
   (the AI-generated "so what") plus the `assets/priority-matrix.svg` snapshot.

## Publish

Report → **File → Embed report → Publish to web** → paste the public link into
`README.md` and the portfolio site. Screenshot each page into `powerbi/screenshots/`.

> Data years: readiness = latest non-null 2023–2025, economics = 2024
> (Statistics Finland tables 14yc & 13vy). Re-run `scripts/*.py` to refresh.
