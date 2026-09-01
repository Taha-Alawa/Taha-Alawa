#!/usr/bin/env python3
"""
Hand-authored neofetch-style info card.

  python scripts/make_info_card.py            # animated
  STATIC=1 python scripts/make_info_card.py   # frozen frame for previews

Writes info-card.svg. Edit CONTENT below when your details change; this
is the part the contribution graph can't tell anyone about, so keep it
to the story rather than the stats.
"""

import os
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path("info-card.svg")
STATIC = os.environ.get("STATIC") == "1"

# Palette ----------------------------------------------------------------
BG = "#0d1117"
BORDER = "#21262d"
KEY = "#58a6ff"
VAL = "#c9d1d9"
DIM = "#8b949e"
ACCENT = "#39d353"
RULE = "#30363d"

# Layout -----------------------------------------------------------------
W = 760
PAD_X = 26
PAD_Y = 24
FS = 14.5
LINE_H = 24.0
KEY_COL = 118          # x offset where values start
STAGGER = 0.06
DUR = 0.42
START = 0.35

# Content ----------------------------------------------------------------
USER = "taha"
HOST = "github"

CONTENT = [
    ("kv", "Now", "Frontend Engineer at Matrixs Group"),
    ("kv", "Prev", "Freelance Frontend Developer"),
    ("kv", "Uptime", "3 years in production"),
    ("kv", "Location", "Saudi Arabia"),
    ("kv", "Degree", "Diploma of Information Technology, JICC"),
    ("gap", "", ""),
    ("kv", "Core", "React, Next.js, Angular, TypeScript"),
    ("kv", "State", "Redux Toolkit, Zustand, TanStack Query"),
    ("kv", "UI", "Tailwind CSS, Sass, React Hook Form, Zod"),
    ("kv", "Data", "Firebase, REST APIs, SignalR"),
    ("kv", "Ship", "Git, Vercel, GitHub Actions"),
    ("gap", "", ""),
    ("head", "Shipped", ""),
    ("bullet", "", "ERP platform in Next.js: HR, CRM, projects, dashboards"),
    ("bullet", "", "Website builder with 22+ configurable components"),
    ("bullet", "", "Restaurant POS in Angular, ZATCA Phase 2, live deploys"),
    ("bullet", "", ".NET local printing service, replaced a paid vendor"),
    ("bullet", "", "Multi-tenant booking and clinic SaaS, Tap payments"),
    ("bullet", "", "Embeddable AI chatbot widget for WordPress and Salla"),
]

SWATCHES = ["#161b22", "#0e4429", "#006d32", "#26a641",
            "#39d353", "#69f0a0", "#58a6ff", "#c9d1d9"]
# ------------------------------------------------------------------------


def main() -> None:
    header = f"{USER}@{HOST}"
    rows: list[str] = []
    y = PAD_Y + LINE_H
    n = 0

    def at(i: int, *cls: str) -> str:
        """Build the class/style pair for one animated element."""
        names = list(cls)
        if STATIC:
            return f' class="{" ".join(names)}"' if names else ""
        names.append("ln")
        return (f' class="{" ".join(names)}"'
                f' style="animation-delay:{START + i * STAGGER:.2f}s"')

    # neofetch prints "user@host" then a rule of dashes
    rows.append(
        f'<text x="{PAD_X}" y="{y:.1f}"{at(n, "hdr")}>'
        f'<tspan fill="{ACCENT}">{escape(USER)}</tspan>'
        f'<tspan fill="{DIM}">@</tspan>'
        f'<tspan fill="{KEY}">{escape(HOST)}</tspan></text>'
    )
    n += 1
    y += 10
    rows.append(
        f'<line x1="{PAD_X}" y1="{y:.1f}" x2="{W - PAD_X}" y2="{y:.1f}" '
        f'stroke="{RULE}"{at(n)}/>'
    )
    n += 1
    y += LINE_H

    for kind, key, val in CONTENT:
        if kind == "gap":
            y += LINE_H * 0.45
            continue

        if kind == "head":
            rows.append(
                f'<text x="{PAD_X}" y="{y:.1f}"{at(n, "k")}>'
                f"{escape(key)}</text>"
            )
        elif kind == "kv":
            rows.append(
                f'<text x="{PAD_X}" y="{y:.1f}"{at(n, "k")}>'
                f"{escape(key)}</text>"
                f'<text x="{PAD_X + KEY_COL}" y="{y:.1f}"{at(n, "v")}>'
                f"{escape(val)}</text>"
            )
        else:  # bullet
            rows.append(
                f'<text x="{PAD_X + 14}" y="{y:.1f}"{at(n, "v")}>'
                f'<tspan fill="{ACCENT}">&#9642; </tspan>{escape(val)}</text>'
            )

        n += 1
        y += LINE_H

    # neofetch colour strip
    y += LINE_H * 0.35
    sw_w, sw_h = 30, 13
    for i, c in enumerate(SWATCHES):
        rows.append(
            f'<rect x="{PAD_X + i * (sw_w + 5)}" y="{y:.1f}" '
            f'width="{sw_w}" height="{sw_h}" rx="2.5" fill="{c}"{at(n)}/>'
        )
    n += 1
    y += sw_h + PAD_Y

    css_anim = "" if STATIC else f"""
    @keyframes ln {{
      from {{ opacity: 0; transform: translateX(-10px); }}
      to   {{ opacity: 1; transform: translateX(0); }}
    }}
    .ln {{ opacity: 0; animation: ln {DUR}s cubic-bezier(.2,.8,.3,1) both; }}
    @media (prefers-reduced-motion: reduce) {{
      .ln {{ animation: none; opacity: 1; }}
    }}"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{y:.0f}" viewBox="0 0 {W} {y:.0f}" role="img" aria-label="Info card">
  <style>
    text {{
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
      font-size: {FS}px;
      dominant-baseline: alphabetic;
    }}
    .hdr {{ font-size: {FS + 2.5}px; font-weight: 700; }}
    .k   {{ fill: {KEY}; font-weight: 600; }}
    .v   {{ fill: {VAL}; }}{css_anim}
  </style>
  <rect width="100%" height="100%" rx="10" fill="{BG}" stroke="{BORDER}"/>
  {chr(10) + '  '.join(rows)}
</svg>
"""
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT}  ({W}x{y:.0f}){'  [static]' if STATIC else ''}")


if __name__ == "__main__":
    main()
