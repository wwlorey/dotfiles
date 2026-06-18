#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "mediapipe",
#   "pillow",
#   "numpy",
# ]
# ///
"""Rotate a front-facing face photo so the inter-iris line is horizontal.

Front-facing portrait pre-processing for face reading. Mirror halves
and feature-by-feature comparisons assume a vertical face midline;
head tilt breaks both. This script detects the iris pair via MediaPipe
FaceLandmarker (478-landmark topology), computes the eye-line angle
from horizontal, and rotates the image so the eyes are level.

The canvas stays the same dimensions as the input (Pillow rotate with
expand=False). Bare corners at the rotation edges are filled by
sampling the original image's edge pixels — no black bars, no JPEG
re-encoding artifacts in the face region. The face sits in the middle
and is unaffected by any corner clipping at practical tilt angles.

Front-facing photos only. Side-profile or extreme three-quarter
angles have unreliable iris detection — when the detector finds no
face, or the measured tilt exceeds --max-angle, the script copies the
input through unchanged so downstream steps can proceed.

Usage:
    level.py <input_image> <output_image> [--max-angle DEG]

Prints `angle=<float>` to stdout (CCW degrees applied to level the
image — 0 if skipped). Diagnostic detail goes to stderr.
"""

import argparse
import math
import shutil
import sys
import urllib.request
from pathlib import Path

from PIL import Image

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_CACHE = Path.home() / ".cache" / "face-reading" / "face_landmarker.task"


def _ensure_landmarker_model():
    if MODEL_CACHE.exists():
        return str(MODEL_CACHE)
    MODEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    print(f"level.py: downloading face_landmarker model to {MODEL_CACHE}",
          file=sys.stderr)
    urllib.request.urlretrieve(MODEL_URL, MODEL_CACHE)
    return str(MODEL_CACHE)


def _edge_fill_color(img):
    """Median color of the input's outer-pixel ring.

    Used as the rotation fill color so the corners exposed by rotating
    with expand=False blend into the existing background instead of
    cutting in as black bars.
    """
    import numpy as np
    arr = np.array(img)
    if arr.ndim != 3 or arr.shape[2] < 3:
        return (0, 0, 0)
    h, w = arr.shape[:2]
    ring = np.concatenate([
        arr[0, :, :3].reshape(-1, 3),
        arr[h - 1, :, :3].reshape(-1, 3),
        arr[:, 0, :3].reshape(-1, 3),
        arr[:, w - 1, :3].reshape(-1, 3),
    ])
    return tuple(int(c) for c in np.median(ring, axis=0))


def detect_iris_pair(img):
    """Return ((rx, ry), (lx, ly)) iris-center pixel coords, or None.

    `r` is the subject's anatomical right iris (sitting in the
    image-left half of a front-facing photo). `l` is anatomical left.
    """
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
    except ImportError as e:
        print(f"level.py: mediapipe import failed: {e}", file=sys.stderr)
        return None

    import numpy as np
    arr = np.array(img)
    h, w = arr.shape[:2]

    try:
        model_path = _ensure_landmarker_model()
    except Exception as e:
        print(f"level.py: model download failed: {e}", file=sys.stderr)
        return None

    options = mp_vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        num_faces=1,
    )
    with mp_vision.FaceLandmarker.create_from_options(options) as detector:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
        result = detector.detect(mp_image)

    if not result.face_landmarks:
        return None

    lm = result.face_landmarks[0]
    iris_r = (lm[468].x * w, lm[468].y * h)
    iris_l = (lm[473].x * w, lm[473].y * h)
    return iris_r, iris_l


def main():
    parser = argparse.ArgumentParser(
        prog="level.py",
        description="Rotate a front-facing portrait so the eyes are level.",
    )
    parser.add_argument("input_image")
    parser.add_argument("output_image")
    parser.add_argument(
        "--max-angle", type=float, default=25.0,
        help="Refuse to rotate beyond this absolute angle (degrees, "
             "default 25). Past this the photo is probably not a "
             "front-facing shot and the iris detection is suspect.",
    )
    args = parser.parse_args()

    img = Image.open(args.input_image).convert("RGB")
    pair = detect_iris_pair(img)
    if pair is None:
        print("level.py: no face detected; passing input through unchanged",
              file=sys.stderr)
        shutil.copyfile(args.input_image, args.output_image)
        print("angle=0 (skipped: no face detected)")
        return

    (rx, ry), (lx, ly) = pair
    dx = lx - rx
    dy = ly - ry
    # Image coords have y pointing down; the eye-line angle from
    # horizontal is atan2(dy, dx). Pillow's `rotate(angle)` rotates
    # the image counter-clockwise visually by `angle` degrees, which
    # — combined with image-y-down — directly undoes a positive
    # eye-line tilt (right iris higher than left, in image coords).
    angle_deg = math.degrees(math.atan2(dy, dx))

    if abs(angle_deg) > args.max_angle:
        print(
            f"level.py: detected angle {angle_deg:.2f}° exceeds max "
            f"{args.max_angle:.1f}°; likely not a front-facing shot. "
            "Passing input through unchanged.",
            file=sys.stderr,
        )
        shutil.copyfile(args.input_image, args.output_image)
        print(f"angle=0 (skipped: |{angle_deg:.2f}°| > max {args.max_angle:.1f}°)")
        return

    rotated = img.rotate(
        angle_deg,
        resample=Image.BICUBIC,
        expand=False,
        fillcolor=_edge_fill_color(img),
    )
    save_kwargs = {}
    if Path(args.output_image).suffix.lower() in {".jpg", ".jpeg"}:
        save_kwargs["quality"] = 95
        save_kwargs["subsampling"] = 0
    rotated.save(args.output_image, **save_kwargs)
    print(f"level.py: applied {angle_deg:.2f}° rotation; "
          f"output {rotated.size[0]}x{rotated.size[1]}",
          file=sys.stderr)
    print(f"angle={angle_deg:.2f}")


if __name__ == "__main__":
    main()
