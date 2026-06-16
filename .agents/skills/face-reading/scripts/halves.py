#!/usr/bin/env python3
"""Render left-left and right-right composites of a face.

Mirrors each half of a face across the vertical midline so the user sees
what the person would look like if both sides matched the left half, and
if both sides matched the right half. Prosopa's asymmetry doctrine:
LEFT = inner / private / felt self; RIGHT = outer / public / presented self.

Usage:
    python3 halves.py <input_image> <midline_x> <output_dir>

`midline_x` is the integer pixel x-coordinate of the vertical face midline
(roughly the centerline of the nose tip / philtrum / chin tip). Determine
it by inspecting the photo.

Outputs three files in <output_dir>:
- halves-left.png   : left half mirrored to make a symmetric face
- halves-right.png  : right half mirrored to make a symmetric face
- halves-side-by-side.png : the two composites stacked horizontally with labels
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def load_font(size):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def mirror_half(img, midline_x, side):
    """Return a full-width image where one half is mirrored to fill both sides.

    side: 'left' keeps the left half (x < midline_x) and mirrors it to the right.
          'right' keeps the right half (x >= midline_x) and mirrors it to the left.
    """
    w, h = img.size
    if side == "left":
        half = img.crop((0, 0, midline_x, h))
        mirrored = ImageOps.mirror(half)
        out = Image.new(img.mode, (midline_x * 2, h))
        out.paste(half, (0, 0))
        out.paste(mirrored, (midline_x, 0))
    elif side == "right":
        half = img.crop((midline_x, 0, w, h))
        mirrored = ImageOps.mirror(half)
        rw = w - midline_x
        out = Image.new(img.mode, (rw * 2, h))
        out.paste(mirrored, (0, 0))
        out.paste(half, (rw, 0))
    else:
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")
    return out


def add_caption(img, caption, font_size=None):
    """Add a black caption bar with white text to the bottom of the image.

    If `font_size` is supplied, use it directly; otherwise scale with the
    image. Pass the same `font_size` to both panels of a side-by-side so
    captions render at matching scale even when the panels differ in width.
    """
    w, h = img.size
    if font_size is None:
        long_edge = max(w, h)
        font_size = max(16, long_edge // 40)
    font = load_font(font_size)
    pad = font_size // 2
    bar_h = font_size + pad * 2

    canvas = Image.new(img.mode if img.mode in ("RGB", "RGBA") else "RGB",
                       (w, h + bar_h), (0, 0, 0))
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), caption, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, h + pad), caption, fill=(255, 255, 255), font=font)
    return canvas


def pad_to_width(img, target_w, bg=(0, 0, 0)):
    """Center-pad an image horizontally to a target width."""
    w, h = img.size
    if w >= target_w:
        return img
    canvas = Image.new(img.mode if img.mode in ("RGB", "RGBA") else "RGB",
                       (target_w, h), bg)
    canvas.paste(img, ((target_w - w) // 2, 0))
    return canvas


def side_by_side(left_img, right_img, gap=20):
    """Stack two images horizontally with a gap between them."""
    h = max(left_img.height, right_img.height)
    w = left_img.width + right_img.width + gap
    canvas = Image.new("RGB", (w, h), (240, 240, 240))
    canvas.paste(left_img, (0, (h - left_img.height) // 2))
    canvas.paste(right_img, (left_img.width + gap, (h - right_img.height) // 2))
    return canvas


def main():
    if len(sys.argv) != 4:
        print("usage: halves.py <input_image> <midline_x> <output_dir>",
              file=sys.stderr)
        sys.exit(2)

    in_path = sys.argv[1]
    try:
        midline_x = int(sys.argv[2])
    except ValueError:
        print(f"midline_x must be an integer pixel coordinate, got {sys.argv[2]!r}",
              file=sys.stderr)
        sys.exit(2)
    out_dir = Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(in_path).convert("RGB")
    w, h = img.size
    margin = max(1, w // 10)
    if not (margin < midline_x < w - margin):
        print(
            f"midline_x={midline_x} is too close to the image edge "
            f"(image width {w}, require {margin} < midline_x < {w - margin})",
            file=sys.stderr,
        )
        sys.exit(2)

    left_full = mirror_half(img, midline_x, "left")
    right_full = mirror_half(img, midline_x, "right")

    # Pad both panels to the wider of the two so the side-by-side compares
    # comparable canvases instead of skewing toward whichever half came from
    # the wider crop.
    common_w = max(left_full.width, right_full.width)
    left_padded = pad_to_width(left_full, common_w)
    right_padded = pad_to_width(right_full, common_w)

    left_path = out_dir / "halves-left.png"
    right_path = out_dir / "halves-right.png"
    sbs_path = out_dir / "halves-side-by-side.png"

    left_full.save(left_path)
    right_full.save(right_path)

    # Key font size to the original image's long edge so both captions render
    # at the same point size regardless of panel widths.
    font_size = max(16, max(w, h) // 40)
    left_cap = add_caption(left_padded, "LEFT × 2 — inner / felt self", font_size=font_size)
    right_cap = add_caption(right_padded, "RIGHT × 2 — outer / presented self", font_size=font_size)
    side_by_side(left_cap, right_cap).save(sbs_path)

    for p in (left_path, right_path, sbs_path):
        print(p)


if __name__ == "__main__":
    main()
