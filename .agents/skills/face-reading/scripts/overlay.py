#!/usr/bin/env python3
"""Annotate a face photo with the observations a reading is based on.

Usage:
    python3 overlay.py <input_image> <observations.json> <output_image>

The observations JSON schema is documented in references/overlay-schema.md.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ZONE_FILL = {
    "upper":  (60, 130, 220, 60),
    "middle": (60, 200, 130, 60),
    "lower":  (200, 130, 60, 60),
}
ZONE_OUTLINE = {
    "upper":  (60, 130, 220, 200),
    "middle": (60, 200, 130, 200),
    "lower":  (200, 130, 60, 200),
}

KNOWN_FIELDS = {"title", "zones", "lines", "markers"}


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


def _draw_label(draw, xy, text, font, fill, canvas_size, margin=4):
    cw, ch = canvas_size
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font, stroke_width=2)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    if tw >= cw:
        x = margin
    elif bbox[2] > cw:
        x -= (bbox[2] - cw)
    if bbox[0] < 0:
        x -= bbox[0]
    if th >= ch:
        y = margin
    elif bbox[3] > ch:
        y -= (bbox[3] - ch)
    if bbox[1] < 0:
        y -= bbox[1]
    draw.text((x, y), text, fill=fill, font=font,
              stroke_width=2, stroke_fill=(0, 0, 0))


def draw_zones(img, draw, zones, font):
    w, h = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    normalized = {}
    for name in ("upper", "middle", "lower"):
        if name not in zones:
            continue
        x1, y1, x2, y2 = zones[name]
        if x1 > x2 or y1 > y2:
            print(f"warning: zone {name!r} has reversed coords; normalizing",
                  file=sys.stderr)
            x1, x2 = sorted((x1, x2))
            y1, y2 = sorted((y1, y2))
        cx1 = max(0, min(w, x1))
        cy1 = max(0, min(h, y1))
        cx2 = max(0, min(w, x2))
        cy2 = max(0, min(h, y2))
        if cx2 <= cx1 or cy2 <= cy1:
            print(f"warning: zone {name!r} is outside image bounds; skipping",
                  file=sys.stderr)
            continue
        normalized[name] = (cx1, cy1, cx2, cy2)
        odraw.rectangle([cx1, cy1, cx2, cy2],
                        fill=ZONE_FILL[name], outline=ZONE_OUTLINE[name], width=3)
    img.alpha_composite(overlay)
    for name, (x1, y1, _, _) in normalized.items():
        label = name.capitalize() + " third"
        _draw_label(draw, (x1 + 8, y1 + 6), label, font, (255, 255, 255), img.size)


def draw_lines(img, draw, lines, font):
    for line in lines:
        points = [tuple(p) for p in line.get("points", [])]
        if len(points) < 2:
            continue
        color = line.get("color", "red")
        draw.line(points, fill=color, width=4, joint="curve")
        label = line.get("label")
        if label:
            lx, ly = points[len(points) // 2]
            _draw_label(draw, (lx + 8, ly - 10), label, font, color, img.size)


def draw_markers(img, draw, markers, font, radius=7):
    for i, marker in enumerate(markers):
        if "x" not in marker or "y" not in marker:
            ident = marker.get("label", f"index {i}")
            print(f"warning: marker {ident!r} missing x/y; skipping",
                  file=sys.stderr)
            continue
        x, y = marker["x"], marker["y"]
        color = marker.get("color", "lime")
        draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                     outline=color, width=3, fill=(0, 0, 0, 80))
        label = marker.get("label")
        if label:
            _draw_label(draw, (x + radius + 4, y - radius - 2), label, font,
                        color, img.size)


def extend_with_title(img, title, font):
    """Return a new image with a solid title bar appended BELOW the photo.

    Appending (rather than compositing over the bottom strip) avoids burying
    annotations or features that fall near the bottom of the frame.
    """
    if not title:
        return img
    margin = 14
    probe = ImageDraw.Draw(img)
    text_bbox = probe.textbbox((0, 0), title, font=font)
    tw = text_bbox[2] - text_bbox[0]
    th = text_bbox[3] - text_bbox[1]
    box_h = th + margin * 2
    canvas = Image.new("RGBA", (img.width, img.height + box_h), (0, 0, 0, 255))
    canvas.paste(img, (0, 0))
    cdraw = ImageDraw.Draw(canvas)
    cdraw.text(((img.width - tw) // 2, img.height + margin),
               title, fill=(255, 255, 255), font=font)
    return canvas


def main():
    if len(sys.argv) != 4:
        print("usage: overlay.py <input_image> <observations.json> <output_image>",
              file=sys.stderr)
        sys.exit(2)

    in_path, obs_path, out_path = sys.argv[1:]
    with open(obs_path, "r", encoding="utf-8") as f:
        obs = json.load(f)

    unknown = [k for k in obs if k not in KNOWN_FIELDS]
    if unknown:
        print(f"warning: unknown fields ignored: {', '.join(sorted(unknown))}",
              file=sys.stderr)

    img = Image.open(in_path).convert("RGBA")
    long_edge = max(img.size)
    label_size = max(12, long_edge // 60)
    title_size = max(16, long_edge // 45)
    label_font = load_font(label_size)
    title_font = load_font(title_size)

    draw = ImageDraw.Draw(img, "RGBA")

    if "zones" in obs:
        draw_zones(img, draw, obs["zones"], label_font)
    if "lines" in obs:
        draw_lines(img, draw, obs["lines"], label_font)
    if "markers" in obs:
        draw_markers(img, draw, obs["markers"], label_font)
    if obs.get("title"):
        img = extend_with_title(img, obs["title"], title_font)

    img.convert("RGB").save(out_path)
    print(out_path)


if __name__ == "__main__":
    main()
