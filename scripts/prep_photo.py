#!/usr/bin/env python3
"""
Prep a photo for ASCII conversion.

  python scripts/prep_photo.py source-photo.png

Steps:
  1. Cut the subject out of the background (rembg).
  2. Find the face and frame a head-and-shoulders crop around it, at the
     exact aspect ratio of the character grid, so the README columns line
     up no matter what the source photo's dimensions were.
  3. Composite onto BLACK and keep the alpha channel.

That last step is the one that matters. The card this art sits on is dark,
so a dense glyph reads as *light*. Compositing on black means the removed
background maps to the blank end of the ramp and the lit face is what
glows - the opposite of what you'd do for a light-background portrait.

Writes source-prepped.png (RGBA). Run once per photo.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

OUT = Path("source-prepped.png")

# Character grid aspect, must match make_ascii_svg.py
GRID_ASPECT = (100 * 9.0 * 0.60) / (66 * 9.0 * 1.10)

# Framing, in multiples of the detected face height
ABOVE = 0.39            # headroom above the face box
BELOW = 1.19            # down to collar and shoulders

MAX_SIDE = 900
REMBG_MODEL = "u2netp"  # the default model is ~1GB; this one is ~5MB


def cutout(path: Path) -> Image.Image:
    from rembg import new_session, remove

    src = Image.open(path).convert("RGBA")
    if max(src.size) > MAX_SIDE:
        src.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    return remove(src, session=new_session(REMBG_MODEL))


def face_box(img: Image.Image):
    gray = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(gray, 1.1, 5)
    if len(faces) == 0:
        return None
    return max(faces, key=lambda f: f[2] * f[3])   # the largest face


def frame(img: Image.Image) -> Image.Image:
    box = face_box(img)

    if box is None:
        print("no face found - falling back to the subject's bounding box")
        alpha = np.array(img)[:, :, 3]
        ys, xs = np.where(alpha > 40)
        top, bot = int(ys.min()), int(ys.min() + (ys.max() - ys.min()) * 0.55)
        cx = int((xs.min() + xs.max()) / 2)
    else:
        fx, fy, fw, fh = box
        top = int(fy - fh * ABOVE)
        bot = int(fy + fh * BELOW)
        cx = int(fx + fw / 2)

    h = bot - top
    w = int(h * GRID_ASPECT)
    return img.crop((cx - w // 2, top, cx - w // 2 + w, bot))


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/prep_photo.py <photo>")

    src = Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"no such file: {src}")

    img = frame(cutout(src))

    black = Image.new("RGBA", img.size, (0, 0, 0, 255))
    black.alpha_composite(img)
    black.putalpha(img.getchannel("A"))          # keep the mask for the ramp
    black.save(OUT)
    print(f"wrote {OUT}  ({black.width}x{black.height})")


if __name__ == "__main__":
    main()
