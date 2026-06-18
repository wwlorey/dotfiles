#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "mediapipe",
#   "pillow",
#   "numpy",
# ]
# ///
"""Render left-left and right-right composites of a face.

Mirrors each half of a face across the vertical midline so the user sees
what the person would look like if both sides matched the left half, and
if both sides matched the right half. Prosopa's asymmetry doctrine:
LEFT = inner / private / felt self; RIGHT = outer / public / presented self.

LEFT and RIGHT here are anatomical — the subject's own left and right.
On a front-facing photo the subject's left side sits on the IMAGE-right
half and the subject's right side sits on the IMAGE-left half (mirror
convention). This script accounts for that, so the labels track anatomy
rather than image coordinates.

Usage:
    python3 halves.py <input_image> <output_dir> [--midline X]

The midline is the integer pixel x-coordinate of the vertical face
midline (centerline through the iris midpoint / nose tip / philtrum /
chin tip). When `--midline` is omitted, the script auto-detects it via
MediaPipe FaceMesh (iris midpoint, refine_landmarks=True). If MediaPipe
isn't installed or no face is detected, falls back to the image
horizontal center and warns on stderr. Pass `--midline X` to override
the detector for hard cases (heavy off-axis tilt, partial occlusion).

The midline actually used is printed to stdout on the first line as
`midline=<int>` so callers can cite it.

Outputs three files in <output_dir>:
- halves-left.png   : subject's left half mirrored to make a symmetric face
- halves-right.png  : subject's right half mirrored to make a symmetric face
- halves-side-by-side.png : the two composites stacked horizontally with labels
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_CACHE = Path.home() / ".cache" / "face-reading" / "face_landmarker.task"


def _ensure_landmarker_model():
    """Download the FaceLandmarker .task model on first use, cache under ~/.cache."""
    if MODEL_CACHE.exists():
        return str(MODEL_CACHE)
    import urllib.request
    MODEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    print(f"halves.py: downloading face_landmarker model to {MODEL_CACHE}",
          file=sys.stderr)
    urllib.request.urlretrieve(MODEL_URL, MODEL_CACHE)
    return str(MODEL_CACHE)


def detect_midline(img):
    """Return the face midline x-coordinate via MediaPipe FaceLandmarker, or None.

    Uses the iris-midpoint landmark pair (478-landmark topology, indices
    468 and 473) as the primary signal — robust to small head tilt and
    beard / chin occlusion. Returns None if MediaPipe is not installed,
    the .task model can't be downloaded, or no face is detected.

    Uses the new MediaPipe Tasks API rather than the legacy `solutions`
    namespace, because the macOS arm64 wheel ships Tasks only.
    """
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
    except ImportError:
        print(
            "halves.py: mediapipe not installed; "
            "install with `pip3 install mediapipe` for auto-detect",
            file=sys.stderr,
        )
        return None

    import numpy as np

    arr = np.array(img)
    h, w = arr.shape[:2]

    try:
        model_path = _ensure_landmarker_model()
    except Exception as e:
        print(f"halves.py: failed to obtain landmarker model: {e}",
              file=sys.stderr)
        return None

    options = mp_vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        num_faces=1,
    )
    with mp_vision.FaceLandmarker.create_from_options(options) as detector:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
        result = detector.detect(mp_image)

    if not result.face_landmarks:
        print("halves.py: no face detected; falling back to image center",
              file=sys.stderr)
        return None

    lm = result.face_landmarks[0]
    iris_r = lm[468]
    iris_l = lm[473]
    midline_norm = (iris_r.x + iris_l.x) / 2
    return int(round(midline_norm * w))


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

    `side` is anatomical (subject's perspective):
      'left'  = subject's left side, which sits on the IMAGE-right half
                (x >= midline_x). That half is kept in place and mirrored
                across the midline to fill the image-left half.
      'right' = subject's right side, which sits on the IMAGE-left half
                (x <  midline_x). Kept in place, mirrored to image-right.

    Each output preserves the original photo's orientation — the kept half
    stays where it was, the mirror takes over the other side. That way the
    composite reads as "this is what the face would look like if both sides
    matched the {anatomical-side} half" without flipping the viewer's frame.
    """
    w, h = img.size
    if side == "left":
        half = img.crop((midline_x, 0, w, h))
        mirrored = ImageOps.mirror(half)
        rw = w - midline_x
        out = Image.new(img.mode, (rw * 2, h))
        out.paste(mirrored, (0, 0))
        out.paste(half, (rw, 0))
    elif side == "right":
        half = img.crop((0, 0, midline_x, h))
        mirrored = ImageOps.mirror(half)
        out = Image.new(img.mode, (midline_x * 2, h))
        out.paste(half, (0, 0))
        out.paste(mirrored, (midline_x, 0))
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
    parser = argparse.ArgumentParser(
        prog="halves.py",
        description="Render left-left and right-right mirror composites of a face.",
    )
    parser.add_argument("input_image")
    parser.add_argument("output_dir")
    parser.add_argument(
        "-m", "--midline", type=int, default=None,
        help="Override the auto-detected face midline x-coordinate (pixels).",
    )
    args = parser.parse_args()

    in_path = args.input_image
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(in_path).convert("RGB")
    w, h = img.size

    if args.midline is not None:
        midline_x = args.midline
        source = "manual override"
    else:
        detected = detect_midline(img)
        if detected is not None:
            midline_x = detected
            source = "mediapipe iris midpoint"
        else:
            midline_x = w // 2
            source = "image center fallback"

    margin = max(1, w // 10)
    if not (margin < midline_x < w - margin):
        print(
            f"midline={midline_x} ({source}) is too close to the image edge "
            f"(image width {w}, require {margin} < midline < {w - margin})",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"halves.py: midline={midline_x} ({source})", file=sys.stderr)

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

    print(f"midline={midline_x}")
    for p in (left_path, right_path, sbs_path):
        print(p)


if __name__ == "__main__":
    main()
