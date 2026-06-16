# Overlay JSON Schema

`scripts/overlay.py` takes a face image plus a JSON file of observations and produces an annotated PNG.

## Invocation

```bash
python3 scripts/overlay.py <input_image> <observations.json> <output_image>
```

## JSON schema

Integer pixel coordinates, origin top-left.

```json
{
  "title": "Optional caption rendered at the bottom of the overlay",
  "zones": {
    "upper": [x1, y1, x2, y2],
    "middle": [x1, y1, x2, y2],
    "lower": [x1, y1, x2, y2]
  },
  "lines": [
    {"label": "jaw", "points": [[x1, y1], [x2, y2], [x3, y3]], "color": "red"},
    {"label": "brow arch", "points": [[x1, y1], [x2, y2], [x3, y3]], "color": "blue"}
  ],
  "markers": [
    {"label": "L canthus", "x": 412, "y": 380, "color": "lime"},
    {"label": "philtrum top", "x": 500, "y": 620, "color": "yellow"}
  ]
}
```

All top-level fields are optional.

## Field semantics

- **`zones`** — the **facial thirds** (Prosopa's framework — upper / middle / lower). Drawn as translucent boxes with labels. Use the same horizontal extents (`x1`, `x2`) so they stack cleanly.
- **`lines`** — open polylines. Use for jaw line, brow arch, profile slope, side-profile curvature (the "bow of melancholy" curve if visible). Two or more points.
- **`markers`** — single labeled dots. Use for canthus landmarks (inner + outer corners), philtrum endpoints, nostril width, chin tip, gonial vertex, hairline center, midline points.

## Recommended palette

- `lime` — eye landmarks (canthus)
- `red` — jaw line
- `blue` — eyebrow / forehead
- `yellow` — philtrum / mouth landmarks
- `cyan` — nose landmarks
- `magenta` — midline / asymmetry axis
- `orange` — chin / lower face

## Coordinate-finding tips

- Anchor first: pupil centers, chin tip, hairline center. Build other coordinates relative to these.
- Thirds: upper = hairline to brow line, middle = brow line to nose tip, lower = nose tip to chin.
- Jaw: 3–5 points from ear-base through chin to other ear-base.
- Brow arch: 3 points per brow (inner, peak, outer).

## Minimum useful overlay

If short on time, draw just:
1. The three facial-thirds zones.
2. The jaw line.
3. Two canthal markers per eye (inner + outer corners).

That covers the temperament call, the dominant-zone call, and the canthal-tilt finding — the three most consequential moves.

## Example

```json
{
  "title": "Saturn over Mars, choleric with sanguine forehead",
  "zones": {
    "upper":  [180, 90, 820, 319],
    "middle": [180, 320, 820, 579],
    "lower":  [180, 580, 820, 880]
  },
  "lines": [
    {
      "label": "jaw",
      "points": [[200, 560], [260, 720], [400, 830], [500, 870], [600, 830], [740, 720], [800, 560]],
      "color": "red"
    },
    {
      "label": "brow line",
      "points": [[260, 320], [500, 305], [740, 320]],
      "color": "blue"
    }
  ],
  "markers": [
    {"label": "L canthus out", "x": 390, "y": 410, "color": "lime"},
    {"label": "L canthus in",  "x": 470, "y": 415, "color": "lime"},
    {"label": "R canthus in",  "x": 530, "y": 415, "color": "lime"},
    {"label": "R canthus out", "x": 610, "y": 410, "color": "lime"},
    {"label": "chin tip",      "x": 500, "y": 870, "color": "orange"},
    {"label": "philtrum",      "x": 500, "y": 660, "color": "yellow"}
  ]
}
```
