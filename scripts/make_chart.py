"""Render the sector priority matrix as a standalone SVG (no dependencies).

x = AI & 5G readiness, y = market attractiveness, bubble size = combined score,
colour = industrial (asset-heavy, primary private-5G target) vs. the rest.

Output: assets/priority-matrix.svg  — used in the README and the portfolio site.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCORES = ROOT / "data" / "scores.json"
OUT = ROOT / "assets" / "priority-matrix.svg"

W, H = 780, 600
M = {"l": 70, "r": 30, "t": 64, "b": 64}
PW, PH = W - M["l"] - M["r"], H - M["t"] - M["b"]

INK = "#1f2933"
MUTED = "#7b8794"
GRID = "#e4e7eb"
INDUSTRIAL = "#d97706"   # amber — asset-heavy 5G targets
OTHER = "#0f766e"        # teal — the rest


def esc(t):  # escape text for XML content
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def x(v):  # readiness 0..100 -> px
    return M["l"] + PW * v / 100
def y(v):  # attractiveness 0..100 -> px (inverted)
    return M["t"] + PH * (1 - v / 100)


def declutter(points):
    """Nudge label y-positions so close bubbles don't overlap text."""
    order = sorted(range(len(points)), key=lambda i: points[i]["ly"])
    min_gap = 16
    for k in range(1, len(order)):
        a, b = order[k - 1], order[k]
        if points[b]["ly"] - points[a]["ly"] < min_gap:
            points[b]["ly"] = points[a]["ly"] + min_gap
    return points


def main():
    data = json.loads(SCORES.read_text())
    sectors = data["sectors"]
    am, rm = data["attr_mid"], data["ready_mid"]

    pts = []
    for s in sectors:
        px, r = x(s["readiness"]), 10 + s["combined"] / 5.5
        left = px > M["l"] + PW * 0.68   # flip label left near the right edge
        pts.append({
            "s": s, "px": px, "py": y(s["attractiveness"]), "r": r,
            "left": left,
            "lx": px - (12 + r) if left else px + (12 + r),
            "ly": y(s["attractiveness"]),
        })
    pts = declutter(pts)

    e = []
    e.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'font-family="-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">')
    e.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    # title
    e.append(f'<text x="{M["l"]}" y="30" font-size="19" font-weight="700" '
             f'fill="{INK}">Finnish industry: private-5G &amp; AI priority matrix</text>')
    e.append(f'<text x="{M["l"]}" y="49" font-size="12" fill="{MUTED}">'
             f'Bubble size = combined score · amber = asset-heavy (primary private-5G target) '
             f'· source: Statistics Finland</text>')

    # quadrant tints
    e.append(f'<rect x="{x(rm)}" y="{M["t"]}" width="{x(100)-x(rm)}" height="{y(am)-M["t"]}" '
             f'fill="#ecfdf5"/>')  # top-right lead
    e.append(f'<rect x="{M["l"]}" y="{M["t"]}" width="{x(rm)-M["l"]}" height="{y(am)-M["t"]}" '
             f'fill="#fffbeb"/>')  # top-left develop
    # plot border + grid
    e.append(f'<rect x="{M["l"]}" y="{M["t"]}" width="{PW}" height="{PH}" '
             f'fill="none" stroke="{GRID}"/>')
    for g in (25, 50, 75):
        e.append(f'<line x1="{x(g)}" y1="{M["t"]}" x2="{x(g)}" y2="{M["t"]+PH}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
        e.append(f'<line x1="{M["l"]}" y1="{y(g)}" x2="{M["l"]+PW}" y2="{y(g)}" '
                 f'stroke="{GRID}" stroke-width="1"/>')
    # midlines
    e.append(f'<line x1="{x(rm)}" y1="{M["t"]}" x2="{x(rm)}" y2="{M["t"]+PH}" '
             f'stroke="{MUTED}" stroke-width="1.3" stroke-dasharray="5 4"/>')
    e.append(f'<line x1="{M["l"]}" y1="{y(am)}" x2="{M["l"]+PW}" y2="{y(am)}" '
             f'stroke="{MUTED}" stroke-width="1.3" stroke-dasharray="5 4"/>')
    # quadrant captions
    e.append(f'<text x="{x(100)-8}" y="{M["t"]+16}" text-anchor="end" font-size="11" '
             f'font-weight="700" fill="#047857">LEAD</text>')
    e.append(f'<text x="{M["l"]+8}" y="{M["t"]+16}" font-size="11" '
             f'font-weight="700" fill="#b45309">DEVELOP / ENABLE</text>')

    # axes labels
    e.append(f'<text x="{M["l"]+PW/2}" y="{H-22}" text-anchor="middle" font-size="13" '
             f'font-weight="600" fill="{INK}">AI &amp; 5G readiness  →</text>')
    e.append(f'<text transform="translate(22,{M["t"]+PH/2}) rotate(-90)" text-anchor="middle" '
             f'font-size="13" font-weight="600" fill="{INK}">Market attractiveness  →</text>')

    # bubbles + labels
    for p in pts:
        s = p["s"]
        col = INDUSTRIAL if s["industrial"] else OTHER
        e.append(f'<circle cx="{p["px"]:.1f}" cy="{p["py"]:.1f}" r="{p["r"]:.1f}" '
                 f'fill="{col}" fill-opacity="0.20" stroke="{col}" stroke-width="1.8"/>')
        e.append(f'<circle cx="{p["px"]:.1f}" cy="{p["py"]:.1f}" r="3" fill="{col}"/>')
        anchor = "end" if p["left"] else "start"
        tie = p["lx"] + (4 if p["left"] else -4)
        e.append(f'<line x1="{p["px"]:.1f}" y1="{p["py"]:.1f}" x2="{tie:.1f}" '
                 f'y2="{p["ly"]:.1f}" stroke="{col}" stroke-width="0.8" stroke-opacity="0.5"/>')
        e.append(f'<text x="{p["lx"]:.1f}" y="{p["ly"]+4:.1f}" text-anchor="{anchor}" '
                 f'font-size="11.5" font-weight="600" fill="{INK}">{esc(s["short"])}</text>')

    e.append('</svg>')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(e))
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
