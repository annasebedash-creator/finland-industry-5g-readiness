"""Generate an executive brief from the scored sectors — the "so what" layer.

Reads data/scores.json + the star schema, computes supporting evidence with SQL,
then:
  - with OPENAI_API_KEY set: asks the model to write a consulting-style brief
  - without a key: writes a structured brief straight from the numbers

Output: data/executive_brief.md  (English — matches the DNA working language)
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "industry.db"
SCORES_PATH = DATA_DIR / "scores.json"
OUT_PATH = DATA_DIR / "executive_brief.md"

EVIDENCE_SQL = """
SELECT s.short AS sector, m.name AS metric, f.raw_value AS value, f.year
FROM fact_metric f
JOIN dim_sector s ON s.sector_id = f.sector_id
JOIN dim_metric m ON m.metric_id = f.metric_id
WHERE m.axis = 'AI & 5G readiness'
ORDER BY s.short, m.metric_id
"""

PROMPT = """You are a strategy & market-intelligence analyst advising a Finnish
telecom operator's enterprise business on where to prioritise industrial 5G and
AI-powered automation offerings. Write a concise executive brief (max 220 words)
for senior leadership, based ONLY on the data below.

Structure:
- One-sentence headline recommendation.
- 3 short bullets naming the priority sectors and WHY (cite the numbers).
- One "watch-out" bullet: a sector with strong 5G use-case fit (physical, asset-heavy)
  but low CURRENT digital adoption — an enablement opportunity, not a reason to walk away.
- Close with the single most important next step.

Scored sectors (0–100 composites, plus priority quadrant):
{scores}

Underlying AI/robotics/IoT adoption, % of enterprises (Statistics Finland):
{evidence}
"""


def load_context():
    scores = json.loads(SCORES_PATH.read_text())
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    evidence = [dict(r) for r in con.execute(EVIDENCE_SQL).fetchall()]
    con.close()
    return scores, evidence


def llm_brief(prompt: str, api_key: str) -> str:
    body = json.dumps({
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
    }).encode()
    req = Request(
        "https://api.openai.com/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urlopen(req, timeout=60) as resp:
        return json.load(resp)["choices"][0]["message"]["content"].strip()


def fallback_brief(scores: dict) -> str:
    sectors = scores["sectors"]
    lead = [s for s in sectors if s["priority"].startswith("Lead")]
    develop = [s for s in sectors if s["priority"].startswith("Develop")]
    top = sectors[0]
    lines = [
        "# Executive brief — Finnish industry: private-5G & AI prioritisation",
        "",
        f"**Recommendation.** Lead with **{top['short']}** — the largest economic "
        f"prize (attractiveness {top['attractiveness']}/100) and the highest current "
        f"industrial-AI adoption (readiness {top['readiness']}/100).",
        "",
        "**Priority sectors (highest combined score):**",
    ]
    for s in sectors[:3]:
        lines.append(f"- **{s['short']}** — attractiveness {s['attractiveness']}, "
                     f"readiness {s['readiness']} → _{s['priority']}_")
    lines.append("")
    if develop:
        d = develop[0]
        lines += [
            f"**Watch-out / enablement play.** **{d['short']}** scores high on market "
            f"value but low on current adoption (readiness {d['readiness']}) — an "
            f"asset-heavy sector where 5G use-cases (automation, connected sites) are "
            f"strong but digital maturity lags. Treat as develop-and-enable, not walk-away.",
            "",
        ]
    lines += [
        "**Next step.** Validate the top-2 sectors with 4–6 enterprise interviews and "
        "one site visit each, then size 2–3 concrete private-5G use cases per sector.",
        "",
        "_(Generated without an LLM key — set OPENAI_API_KEY for the narrative version.)_",
    ]
    return "\n".join(lines)


def main():
    if not SCORES_PATH.exists():
        raise SystemExit("data/scores.json missing — run transform.py first.")
    scores, evidence = load_context()
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        prompt = PROMPT.format(
            scores=json.dumps(scores["sectors"], ensure_ascii=False, indent=2),
            evidence=json.dumps(evidence, ensure_ascii=False))
        text = ("# Executive brief — Finnish industry: private-5G & AI prioritisation\n\n"
                + llm_brief(prompt, api_key))
    else:
        text = fallback_brief(scores)
    OUT_PATH.write_text(text + "\n")
    print(f"Wrote {OUT_PATH.name}\n")
    print(text)


if __name__ == "__main__":
    main()
