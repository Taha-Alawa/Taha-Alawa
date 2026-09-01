#!/usr/bin/env python3
"""
Turn source-prepped.png into a self-typing ASCII portrait SVG.

  python scripts/make_ascii_svg.py                 # uses source-prepped.png
  STATIC=1 python scripts/make_ascii_svg.py        # frozen frame for previews
  python scripts/make_ascii_svg.py --placeholder   # generic silhouette

Writes me-ascii.svg. Each row is clipped by a rect that wipes
left-to-right on a stagger, with a block cursor riding the wipe edge,
so the portrait appears to type itself. It prints once and freezes.
All motion is SMIL inside the SVG, which is what GitHub will play.

Note the ramp runs bright-photo -> dense-glyph, not the other way round.
The card is dark, so ink density reads as light: the lit face has to be
the dense end or the portrait comes out as a negative.
"""

import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path("me-ascii.svg")
STATIC = os.environ.get("STATIC") == "1"   # frozen frame for local previews

# Layout -----------------------------------------------------------------
# The grid is fixed so the SVG is always the same size no matter what
# photo you feed it - that keeps the README columns aligned.
COLS = 100
ROWS = 66
FONT_SIZE = 9.0
CHAR_W = FONT_SIZE * 0.60
LINE_H = FONT_SIZE * 1.10
PAD = 18

# Look -------------------------------------------------------------------
INK = "#c9d1d9"          # single fill colour: monochrome beats rainbow
BG = "#0d1117"
BORDER = "#21262d"
CURSOR = "#39d353"

# sparse -> dense. On a dark card this runs shadow -> highlight.
RAMP = " .`:-=+*cs#%@"

# Tone window ------------------------------------------------------------
# Everything below LO collapses to blank, so a black suit drops out of the
# frame entirely and only the lit head is drawn.
LO = 48.0
HI = 200.0
GAMMA = 1.25
FLOOR = 0.055           # faintest ink inside the mask, keeps hair's outline

# Timing -----------------------------------------------------------------
ROW_DELAY = 0.045        # stagger between rows
ROW_DUR = 0.34           # how long one row takes to wipe in
START = 0.25
# ------------------------------------------------------------------------


def placeholder(size=(600, 720)) -> Image.Image:
    """A soft head-and-shoulders silhouette, so the README renders before
    you have a photo in place. Replace it with the real thing."""
    w, h = size
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    cx = w / 2
    d.ellipse([cx - w * 0.46, h * 0.72, cx + w * 0.46, h * 1.35], fill=255)
    d.rounded_rectangle(
        [cx - w * 0.09, h * 0.55, cx + w * 0.09, h * 0.78], radius=24, fill=255
    )
    d.ellipse([cx - w * 0.22, h * 0.10, cx + w * 0.22, h * 0.62], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(6))

    yy, xx = np.mgrid[0:h, 0:w]
    lit = np.clip(((xx / w) * 0.5 + (1 - yy / h) * 0.9) * 235, 0, 255)
    lum = (lit * (np.asarray(m) / 255.0)).astype(np.uint8)

    out = Image.merge("RGBA", (Image.fromarray(lum),) * 3 + (m,))
    return out


def to_rows(img: Image.Image) -> list[str]:
    """Downsample to the character grid, then grade.

    Order matters: grading first and averaging afterwards washes the face
    into one flat glyph. Averaging first keeps the tonal spread that the
    eyes, brows and jawline live in.
    """
    rgba = img.convert("RGBA")
    lum = np.asarray(rgba.convert("L"))
    alpha = np.asarray(rgba)[:, :, 3].astype(np.float32) / 255.0

    small = cv2.resize(lum, (COLS, ROWS), interpolation=cv2.INTER_AREA)
    mask = cv2.resize(alpha, (COLS, ROWS), interpolation=cv2.INTER_AREA)

    x = np.clip((small.astype(np.float32) - LO) / (HI - LO), 0, 1) ** GAMMA
    x = np.where(mask > 0.45, np.maximum(x, FLOOR), 0.0)

    top = len(RAMP) - 1
    return ["".join(RAMP[int(round(v * top))] for v in row) for row in x]


def build_svg(rows: list[str]) -> str:
    grid_w = COLS * CHAR_W
    grid_h = len(rows) * LINE_H
    w = grid_w + PAD * 2
    h = grid_h + PAD * 2

    clips, lines = [], []

    for i, text in enumerate(rows):
        # trim the trailing blanks so the cursor stops at real content
        trimmed = text.rstrip()
        end = max(len(trimmed), 1) * CHAR_W
        begin = START + i * ROW_DELAY
        y = PAD + (i + 1) * LINE_H

        if STATIC:
            lines.append(
                f'<text x="{PAD:.1f}" y="{y:.1f}" xml:space="preserve" '
                f'textLength="{len(text) * CHAR_W:.1f}" lengthAdjust="spacing">'
                f"{escape(text)}</text>"
            )
            continue

        clips.append(
            f'<clipPath id="r{i}">'
            f'<rect x="{PAD:.1f}" y="{y - LINE_H:.1f}" '
            f'width="0" height="{LINE_H + 2:.1f}">'
            f'<animate attributeName="width" from="0" to="{end:.1f}" '
            f'begin="{begin:.2f}s" dur="{ROW_DUR}s" '
            f'calcMode="spline" keySplines="0.2 0.8 0.3 1" '
            f'fill="freeze"/>'
            f"</rect></clipPath>"
        )

        lines.append(
            # textLength pins each row to the grid, so the layout holds
            # whichever monospace face the viewer's machine resolves.
            f'<text x="{PAD:.1f}" y="{y:.1f}" clip-path="url(#r{i})" '
            f'xml:space="preserve" textLength="{len(text) * CHAR_W:.1f}" '
            f'lengthAdjust="spacing">{escape(text)}</text>'
        )

        if trimmed:
            lines.append(
                f'<rect class="cur" x="{PAD:.1f}" y="{y - LINE_H + 1.5:.1f}" '
                f'width="{CHAR_W:.1f}" height="{LINE_H - 1:.1f}" opacity="0">'
                f'<animate attributeName="opacity" values="0;0.85;0" '
                f'begin="{begin:.2f}s" dur="{ROW_DUR}s" fill="freeze"/>'
                f'<animate attributeName="x" from="{PAD:.1f}" '
                f'to="{PAD + end:.1f}" begin="{begin:.2f}s" dur="{ROW_DUR}s" '
                f'calcMode="spline" keySplines="0.2 0.8 0.3 1" '
                f'fill="freeze"/>'
                f"</rect>"
            )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="ASCII portrait">
  <defs>
    {''.join(clips)}
  </defs>
  <style>
    text {{
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
      font-size: {FONT_SIZE}px;
      fill: {INK};
      letter-spacing: 0;
    }}
    .cur {{ fill: {CURSOR}; }}
  </style>
  <rect width="100%" height="100%" rx="10" fill="{BG}" stroke="{BORDER}"/>
  {chr(10) + '  '.join(lines)}
</svg>
"""


def main() -> None:
    args = [a for a in sys.argv[1:]]

    if "--placeholder" in args:
        img = placeholder()
    else:
        src = Path(args[0]) if args else Path("source-prepped.png")
        if not src.exists():
            sys.exit(
                f"{src} not found.\n"
                "Run: python scripts/prep_photo.py <your-photo.jpg>\n"
                "Or:  python scripts/make_ascii_svg.py --placeholder"
            )
        img = Image.open(src)

    rows = to_rows(img)
    OUT.write_text(build_svg(rows), encoding="utf-8")
    print(f"wrote {OUT}  ({COLS}x{len(rows)} chars)")


if __name__ == "__main__":
    main()
