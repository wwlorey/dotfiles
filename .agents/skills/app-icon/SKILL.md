---
name: app-icon
description: Producing a macOS app icon with the correct squircle shape and transparent corners — applying Apple's mask to a square image, or cleaning up an existing icon with dark/black baked-in corners. Consult whenever the user mentions an app icon, .icns file, squircle, AppIcon.appiconset, or wants a square image reshaped to look native on macOS. Even one-off "round the corners of this PNG into a macOS icon shape" counts.
---

# macOS App Icon

Apply Apple's actual squircle mask to a square image so it renders correctly in the Dock, Launchpad, and Finder. GPT Image 2 (and other generators) can't produce transparent backgrounds, so the squircle has to be applied as a post-processing step.

Two starting points, two workflows.

## Starting point: from scratch (preferred)

1. **Get a square icon with sharp 90° corners and the background extended to the edges.** If you need to generate one, use the `generate-image` skill — request a 1024×1024 square design, then come back here. If the user supplies a rounded icon, ask the generator to extend the background to the edges with sharp 90-degree corners.
2. **Apply Apple's icon mask.** The mask's alpha channel defines the squircle (alpha=255 inside, alpha=0 in corners, anti-aliased edges).

```python
from PIL import Image
import numpy as np

icon = Image.open('<SQUARE_ICON_PATH>').convert('RGBA')
mask = Image.open(
    '/System/Library/CoreServices/IconsetResources.bundle'
    '/Contents/Resources/AppIconMask_448@2x.png'
).convert('RGBA')

mask = mask.resize(icon.size, Image.LANCZOS)

icon_data = np.array(icon)
icon_data[:,:,3] = np.array(mask)[:,:,3]

Image.fromarray(icon_data).save('<OUTPUT_PATH>')
```

## Starting point: existing icon with dark/black corners

If the icon already has dark rounded corners baked in, you can't just threshold — anti-aliased edge pixels are a blend of dark + background and a hard threshold leaves visible artifacts. Instead:

1. **Flood-fill from image edges** to find dark pixels connected to the border (corners only, not interior darks like shadows or dark UI elements).
2. **Dilate + blur** the corner mask to cover anti-aliased transition pixels.
3. **Composite** the interior onto a clean background-colored canvas.
4. **Apply the macOS squircle mask.**

```python
from PIL import Image, ImageFilter
import numpy as np
from collections import deque

icon = Image.open('<ICON_PATH>').convert('RGBA')
w, h = icon.size
data = np.array(icon, dtype=np.float64)

# Sample background color from the icon (e.g., middle of top edge).
# Avoid hardcoding — different icons have different backgrounds.
bg_sample = data[20, w // 2, :].copy()
bg_sample[3] = 255  # ensure full alpha
bg = bg_sample

r, g, b = data[:,:,0], data[:,:,1], data[:,:,2]
lum = 0.299 * r + 0.587 * g + 0.114 * b
dark = lum < 80

# BFS flood fill from all dark border pixels
corner_region = np.zeros((h, w), dtype=bool)
queue = deque()
for x in range(w):
    for y in [0, h-1]:
        if dark[y, x]: queue.append((y, x)); corner_region[y, x] = True
for y in range(h):
    for x in [0, w-1]:
        if dark[y, x] and not corner_region[y, x]:
            queue.append((y, x)); corner_region[y, x] = True

while queue:
    cy, cx = queue.popleft()
    for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
        ny, nx = cy+dy, cx+dx
        if 0 <= ny < h and 0 <= nx < w and dark[ny, nx] and not corner_region[ny, nx]:
            corner_region[ny, nx] = True
            queue.append((ny, nx))

# Dilate to catch anti-aliased transition pixels, then blur for soft edge
corner_img = Image.fromarray((corner_region * 255).astype(np.uint8))
for _ in range(6):
    corner_img = corner_img.filter(ImageFilter.MaxFilter(3))
corner_img = corner_img.filter(ImageFilter.GaussianBlur(2.0))
corner_soft = np.array(corner_img).astype(np.float64) / 255.0
interior_alpha = 1.0 - corner_soft

# Composite interior over clean background canvas
canvas = np.full_like(data, bg)
for c in range(4):
    canvas[:,:,c] = interior_alpha * data[:,:,c] + (1.0 - interior_alpha) * bg[c]

# Apply macOS squircle mask
mask = Image.open(
    '/System/Library/CoreServices/IconsetResources.bundle'
    '/Contents/Resources/AppIconMask_448@2x.png'
).convert('RGBA')
mask = mask.resize((w, h), Image.LANCZOS)
canvas[:,:,3] = np.array(mask)[:,:,3].astype(np.float64)

Image.fromarray(canvas.astype(np.uint8)).save('<OUTPUT_PATH>')
```

The dark-corner sample point (`data[20, w // 2, :]`) reads from the middle of the top edge to grab the background color. If the icon has a dark top, pick a different sample point.

## Why this approach

- GPT Image 2 doesn't support `"background": "transparent"` on either endpoint.
- Chroma keying (e.g. lime-green background) leaves anti-aliasing fringe.
- Superellipse approximations (`|x|^n + |y|^n = 1`) don't match Apple's exact curve.
- Simple luminance thresholding can't distinguish dark corners from intentionally dark interior elements.
- Flood-filling from edges + dilation correctly isolates only the corner regions and their anti-aliased boundaries.

## Notes

- The mask path is macOS-specific — `/System/Library/CoreServices/IconsetResources.bundle/...`. Won't exist on Linux.
- Output a single PNG. If the user wants a full `.icns` or `.appiconset`, generate the squircled PNG first, then call `iconutil` or `sips` to package — they didn't ask for that automatically.
