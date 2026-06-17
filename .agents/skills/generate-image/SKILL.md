---
name: generate-image
description: Generating an image from a description, or transforming a reference image into a new style. Consult whenever the user asks to make, draw, render, produce, or generate any kind of image — photo, illustration, render, logo, icon, sketch — even when "image" is never said ("draw me a poster of X", "make a watercolor of this photo"). Also use when the user supplies a reference image and asks to edit or restyle it.
---

# Generate Image

Use OpenAI's GPT Image 2 to turn a rough request into a finished image. Iterate at low quality until the user is happy, then ask before spending on a high-quality final.

## Workflow

1. **Interpret the request.** If the user gave a clear subject, proceed. If not, ask one short question to pin down what they want.
2. **Engineer the prompt.** Rewrite the user's idea into an optimized prompt (see *Prompt Engineering* below). Show the engineered prompt to the user before generating.
3. **Infer parameters.** Pick size from subject:
   - Landscapes, scenes, wide shots → `1536x1024`
   - Portraits, tall subjects, mobile → `1024x1536`
   - Icons, logos, symmetric subjects → `1024x1024`
   - The user can override with explicit dimensions.
4. **Generate at `low`.** Call the API via curl (see *API Calls* below). Every call in the iteration loop runs at `low`. Never raise the quality without explicit user permission for that specific output.
5. **Save and open.** Save to `./YYYY-MM-DD-HH:MM:SS-short-description.png` and run `open <path>` so the user sees it immediately. (MEMENTO's surface-files rule handles printing the clickable URL.)
6. **Iterate at `low`.** Ask for feedback. When the user requests changes, regenerate (or use edit — see below) at `low`. Stay at `low` for every iteration including quality-feeling tweaks ("make it crisper", "sharpen it"). Only after the user has approved a specific image ("ship it", "I like that one") may you ask whether they want a `medium` or `high` final — and only after they say yes does the higher-quality call happen.
7. **Finalize via `/edits` on the approved file.** When the user authorizes a `medium`/`high` final, do NOT call `/images/generations` with a fresh text prompt — that re-rolls the composition the user already approved. Instead, pass the approved low-quality file to `/images/edits` with a "refine this to high quality, preserve exact composition" prompt. The approved image is the input; quality is the parameter being changed.

## API Calls

### Generate (text to image)

For creating from scratch.

```bash
RESP="$TMPDIR/img-response.json"
curl -s -X POST "https://api.openai.com/v1/images/generations" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "<ENGINEERED_PROMPT>",
    "n": 1,
    "size": "<WxH>",
    "quality": "low",
    "output_format": "png"
  }' -o "$RESP"

b64_len=$(jq -r '.data[0].b64_json // empty' "$RESP" | wc -c | tr -d ' ')
if [ "$b64_len" -lt 100 ]; then
  echo "Image generation failed. Response:"; jq '.error // .' "$RESP"
else
  jq -r '.data[0].b64_json' "$RESP" | base64 --decode > "<OUTPUT_PATH>"
fi
```

### Edit (image to image)

For transforming a reference image — style transfer, photo-to-illustration, modifying an existing image.

```bash
RESP="$TMPDIR/img-response.json"
curl -s -X POST "https://api.openai.com/v1/images/edits" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F "model=gpt-image-2" \
  -F "image=@<INPUT_IMAGE_PATH>" \
  -F "prompt=<ENGINEERED_PROMPT>" \
  -F "n=1" \
  -F "size=<WxH>" \
  -F "quality=low" \
  -F "output_format=png" -o "$RESP"

b64_len=$(jq -r '.data[0].b64_json // empty' "$RESP" | wc -c | tr -d ' ')
if [ "$b64_len" -lt 100 ]; then
  echo "Image edit failed. Response:"; jq '.error // .' "$RESP"
else
  jq -r '.data[0].b64_json' "$RESP" | base64 --decode > "<OUTPUT_PATH>"
fi
```

- Accepts PNG, WEBP, JPG under 50MB. Convert other formats with `sips -s format png <input> --out <output.png>`.
- Optional `-F "mask=@<MASK_PATH>"` (PNG with alpha) to constrain edits to transparent regions. Mask must match source dimensions.
- The prompt describes the *desired transformation*, not the input ("Transform this photo into a watercolor painting", not "a person standing").
- **Use edit when:**
  - The user provides a photo/image to base output on.
  - You need to preserve likeness from a source.
  - The user says "make this look like..." / "convert this to...".
  - The user picked a specific prior generation and is requesting refinements ("make it thicker", "fix the amplitude", "bump quality", "do the same but X"). Passing the picked file to `/edits` preserves the composition the user approved — regenerating from a tweaked text prompt re-rolls every detail and loses what they liked.
- **Use generate when:** no reference image, text description only, or exploring fresh options the user has not yet picked from.

### Shared

- Auth: `$OPENAI_API_KEY` from env. If unset, tell the user before calling.
- Response is always base64. Pipe through `jq` and `base64 --decode`.
- Always check `b64_json` length before decoding. A malformed or empty response otherwise produces a 0-byte PNG and no error surfaces — surface the response body to the user instead.
- **Quality is `low` unless the user explicitly authorizes higher.** Every generation, every edit, every iteration runs at `low` — including iterations that *feel* like quality bumps ("make it sharper", "crisper", "cleaner"). Only call at `medium` or `high` after asking the user and getting an explicit yes, and only for the specific image they greenlit.
  - `low` — cheapest, fast drafts. Default for every call.
  - `medium` — balanced, ~5–10x cost of low.
  - `high` — best detail, ~35x cost of low.
- Sizing: any `WxH` divisible by 16, max edge 3840px, max aspect ratio 3:1.

## Output

- **Path:** `./YYYY-MM-DD-HH:MM:SS-short-description.png`
  - Timestamp is generation time.
  - `short-description` is a 2-4 word kebab-case slug (e.g. `golden-retriever-field`, `neon-city-street`, `logo-concept`).
- **Auto-open:** always `open <path>` after saving.
- Surface the file per MEMENTO's rule (`image: file:///…` with `:` encoded as `%3A`).

## Prompt Engineering

Transform the user's rough idea into an optimized prompt. Follow this structure, including only what's relevant:

```
[Subject with specific details] + [Action/Pose] + [Setting/Environment] + [Style/Medium] + [Lighting] + [Camera/Composition] + [Mood/Atmosphere]
```

### Principles

- **Be specific.** "A golden retriever puppy with wet fur, tongue out, wearing a red bandana" beats "a dog."
- **Natural language.** GPT Image 2 responds to descriptive sentences, not keyword stacks.
- **State exclusions positively.** No negative-prompt parameter exists. Say "clean background with no text" instead of trying to negate.
- **Don't overload.** Under ~75 words. Prioritize what matters most.
- **No contradictory styles.** Don't mix "photorealistic watercolor".

### Style keywords

- **Photo:** "photorealistic", "DSLR photograph", "shot on Canon EOS R5", "35mm film"
- **Illustration:** "digital illustration", "concept art", "oil painting", "watercolor", "ink drawing"
- **3D:** "3D render", "octane render", "unreal engine 5"
- **Design:** "flat design", "vector illustration", "minimalist", "art deco"

### Lighting

"golden hour", "soft diffused light", "dramatic chiaroscuro", "rim lighting", "backlit", "neon-lit", "volumetric lighting", "studio softbox"

### Composition

- **Lens:** "85mm portrait lens", "wide angle 24mm", "macro lens", "tilt-shift"
- **Angle:** "bird's eye view", "low angle", "eye level", "dutch angle"
- **Depth:** "shallow depth of field", "bokeh background", "f/1.4"
- **Framing:** "rule of thirds", "centered composition", "negative space", "close-up", "full body"

### Quality boosters

"highly detailed", "sharp focus", "8K resolution", "professional photography"

## Notes

- For text in images, put the exact text in quotes: `a sign that reads "OPEN 24 HOURS"`.
- Hands and complex poses are weak — suggest simpler poses if results are bad.
- If the API errors, show the user the error message before retrying.
- **Don't raise quality on your own.** "Make it better" / "sharper" / "cleaner" are still iteration requests — keep them at `low`. Only words like "high quality please", "ship it at high", or an explicit yes after you asked authorize `medium`/`high`.
- **Don't regenerate when iterating on an approved image.** If the user picked something and wants small changes, hand the picked file to `/edits`. Re-generating from text discards composition they already greenlit.

## Related

- **macOS app icon (squircle, transparent corners):** the model can't produce transparent backgrounds. Generate a square icon here, then hand off to the `app-icon` skill to apply the macOS squircle mask.
