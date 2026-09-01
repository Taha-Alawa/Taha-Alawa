#!/usr/bin/env python3
"""
Render data/contributions.json as four stacked calendar years.

  python scripts/render_heatmap_svg.py
  STATIC=1 python scripts/render_heatmap_svg.py   # frozen frame

Writes contrib-heatmap.svg. Boxes slide down on a diagonal stagger, play
once on load, then freeze. CSS keyframes live inside the SVG, which is
the only kind of animation GitHub will run in a README.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path

SRC = Path("data/contributions.json")
OUT = Path("contrib-heatmap.svg")
STATIC = os.environ.get("STATIC") == "1"

# Palette: none -> brightest. Level 5 is the neon top end.
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

BG = "#0d1117"
BORDER = "#21262d"
TEXT = "#c9d1d9"
DIM = "#8b949e"
ACCENT = "#39d353"

# Layout -----------------------------------------------------------------
BOX = 11
GAP = 2.8
PITCH = BOX + GAP
PAD = 22
LABEL_L = 44           # room for the year label
LABEL_T = 18           # room for month names, on the top row only
ROW_GAP = 16           # space between one year and the next
LABEL_R = 52           # room for each year's total on the right
FOOT = 44              # legend + stats row

# Timing -----------------------------------------------------------------
WAVE = 0.019           # per diagonal step
YEAR_LAG = 0.28        # each year starts after the one above it
DUR = 0.42
START = 0.2
# ------------------------------------------------------------------------

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load() -> dict:
    if not SRC.exists():
        raise SystemExit("run scripts/fetch_contributions.py first")
    data = json.loads(SRC.read_text(encoding="utf-8"))
    if "years" not in data:
        raise SystemExit("stale contributions.json - re-run fetch_contributions.py")
    return data


def to_grid(days: list[dict]) -> list[list[dict | None]]:
    """Bucket days into columns of 7, Sunday first, like GitHub does."""
    first = date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7          # Python: Mon=0; GitHub: Sun=0

    cells: list[dict | None] = [None] * lead + list(days)
    while len(cells) % 7:
        cells.append(None)

    return [cells[i : i + 7] for i in range(0, len(cells), 7)]


def month_labels(grid, ox: float, y: float) -> list[str]:
    out, seen, last_x = [], None, -999.0
    for wi, col in enumerate(grid):
        first = next((c for c in col if c), None)
        if not first:
            continue
        m = int(first["date"][5:7])
        if m == seen:
            continue
        seen = m
        x = ox + wi * PITCH
        if wi >= len(grid) - 1 or x - last_x < 28:
            continue
        last_x = x
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" class="lbl">{MONTHS[m - 1]}</text>')
    return out


def build(data: dict) -> str:
    years = data["years"]
    today = date.today().isoformat()

    grids = [(y, to_grid(y["days"])) for y in years]
    weeks = max(len(g) for _, g in grids)

    grid_w = weeks * PITCH - GAP
    grid_h = 7 * PITCH - GAP
    band = grid_h + ROW_GAP

    ox = PAD + LABEL_L
    oy = PAD + LABEL_T

    w = PAD * 2 + LABEL_L + grid_w + LABEL_R
    h = oy + len(grids) * band - ROW_GAP + FOOT + PAD

    parts: list[str] = []

    # month names only above the first band, otherwise it's noise
    parts += month_labels(grids[0][1], ox, oy - 6)

    for yi, (year, grid) in enumerate(grids):
        top = oy + yi * band

        parts.append(
            f'<text x="{PAD:.1f}" y="{top + grid_h / 2 + 4:.1f}" class="yr">'
            f'{year["year"]}</text>'
        )

        for wi, col in enumerate(grid):
            for di, cell in enumerate(col):
                if not cell or cell["date"] > today:
                    continue
                x = ox + wi * PITCH
                y = top + di * PITCH
                fill = PALETTE[min(cell["level"], len(PALETTE) - 1)]
                delay = START + yi * YEAR_LAG + (wi + di * 2.2) * WAVE
                style = "" if STATIC else f' style="animation-delay:{delay:.2f}s"'
                cls = "box" if STATIC else "box anim"
                n = cell["count"]
                label = f'{n} contribution{"" if n == 1 else "s"} on {cell["date"]}'
                parts.append(
                    f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" '
                    f'width="{BOX}" height="{BOX}" rx="2.5" fill="{fill}"{style}>'
                    f"<title>{label}</title></rect>"
                )

        parts.append(
            f'<text x="{ox + grid_w + 6:.1f}" y="{top + grid_h / 2 + 4:.1f}" '
            f'class="yrtot">{year["total"]:,}</text>'
        )

    # footer
    fy = oy + len(grids) * band - ROW_GAP + 24
    s = data["stats"]
    parts.append(
        f'<text x="{PAD:.1f}" y="{fy + 10:.1f}" class="stat">'
        f'<tspan fill="{ACCENT}" font-weight="700">{data["total"]:,}</tspan>'
        f'<tspan fill="{DIM}"> contributions since {years[-1]["year"]}</tspan>'
        f'<tspan fill="{BORDER}">   |   </tspan>'
        f'<tspan fill="{TEXT}">{s["active_days"]:,}</tspan>'
        f'<tspan fill="{DIM}"> active days</tspan>'
        f'<tspan fill="{BORDER}">   |   </tspan>'
        f'<tspan fill="{TEXT}">{s["longest_streak"]}</tspan>'
        f'<tspan fill="{DIM}"> day best streak</tspan>'
        f"</text>"
    )

    lx = w - PAD - (len(PALETTE) * PITCH) - 74
    parts.append(f'<text x="{lx:.1f}" y="{fy + 10:.1f}" class="lbl">Less</text>')
    for i, c in enumerate(PALETTE):
        parts.append(
            f'<rect x="{lx + 32 + i * PITCH:.1f}" y="{fy:.1f}" '
            f'width="{BOX}" height="{BOX}" rx="2.5" fill="{c}"/>'
        )
    parts.append(
        f'<text x="{lx + 32 + len(PALETTE) * PITCH + 4:.1f}" y="{fy + 10:.1f}" '
        f'class="lbl">More</text>'
    )

    css = "" if STATIC else f"""
    @keyframes drop {{
      from {{ opacity: 0; transform: translateY(-6px) scale(.7); }}
      to   {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    .anim {{
      opacity: 0;
      transform-box: fill-box;
      transform-origin: center;
      animation: drop {DUR}s cubic-bezier(.2,.85,.3,1) both;
    }}
    @media (prefers-reduced-motion: reduce) {{
      .anim {{ animation: none; opacity: 1; }}
    }}"""

    stamp = datetime.fromisoformat(
        data["generated_at"].replace("Z", "+00:00")
    ).strftime("%d %b %Y")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="Contribution heatmap">
  <style>
    text {{
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    }}
    .lbl   {{ font-size: 10px; fill: {DIM}; }}
    .yr    {{ font-size: 11.5px; fill: {TEXT}; font-weight: 700; }}
    .yrtot {{ font-size: 10px; fill: {DIM}; }}
    .stat  {{ font-size: 12.5px; }}
    .meta  {{ font-size: 10px; fill: #30363d; }}{css}
  </style>
  <rect width="100%" height="100%" rx="10" fill="{BG}" stroke="{BORDER}"/>
  <text x="{w - PAD:.0f}" y="{PAD - 8:.0f}" class="meta" text-anchor="end">updated {stamp}</text>
  {chr(10) + '  '.join(parts)}
</svg>
"""


if __name__ == "__main__":
    OUT.write_text(build(load()), encoding="utf-8")
    print(f"wrote {OUT}{'  [static]' if STATIC else ''}")
