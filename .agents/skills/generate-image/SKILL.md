---
name: generate-image
description: Generating an image from a description, or transforming a reference image into a new style. Consult whenever the user asks to make, draw, render, produce, or generate any kind of image — photo, illustration, render, logo, icon, sketch — even when "image" is never said ("draw me a poster of X", "make a watercolor of this photo"). Also use when the user supplies a reference image and asks to edit or restyle it.
---

# Generate Image

Use OpenAI's GPT Image models to turn a rough request into a finished image. Default to `gpt-image-2` for text-to-image generation and `gpt-image-1.5` for image-to-image editing. Iterate at low quality until the user is happy, then ask before spending on a high-quality final.

## Workflow

1. **Interpret the request.** If the user gave a clear subject, proceed. If not, ask one short question to pin down what they want.
2. **Engineer the prompt.** Rewrite the user's idea into an optimized prompt (see *Prompt Engineering* below). Show the engineered prompt to the user before generating.
3. **Infer parameters.** Pick size from subject:
   - Landscapes, scenes, wide shots → `1536x1024`
   - Portraits, tall subjects, mobile → `1024x1536`
   - Icons, logos, symmetric subjects → `1024x1024`
   - The user can override with explicit dimensions.
4. **Generate at `low`.** Call the API via curl (see *API Calls* below). Every call in the iteration loop runs at `low`. Never raise the quality without explicit user permission for that specific output.
5. **Save and open.** Save to `./YYYY-MM-DD-HH:MM:SS-short-description.png`, then call `mcp__unsandboxed-runner__open_file` with the absolute path so the user sees it immediately. (MEMENTO's surface-files rule handles printing the clickable URL.) Use the MCP wrapper — never call `open` via Bash. The in-sandbox Bash subprocess intermittently fails with `Error -600 procNotFound: no eligible process` (Launch Services can't reach the GUI session); the MCP runs outside the sandbox and avoids the issue entirely.
6. **Iterate at `low`.** Ask for feedback. When the user requests changes, regenerate (or use edit — see below) at `low`. Stay at `low` for every iteration including quality-feeling tweaks ("make it crisper", "sharpen it"). Only after the user has approved a specific image ("ship it", "I like that one") may you ask whether they want a `medium` or `high` final — and only after they say yes does the higher-quality call happen.
7. **Finalize via `/edits` on the approved file.** When the user authorizes a `medium`/`high` final, pass the approved low-quality file to `/images/edits` rather than calling `/images/generations` again. Use `gpt-image-1.5` with `input_fidelity="high"` — the user picked this exact composition, so preservation matters more than freedom. Quality is the parameter being changed; everything else stays as-is. Some detail will still reroll (see the Edit section).

## API Calls

### Generate (text to image)

For creating from scratch.

```bash
RESP="$TMPDIR/img-response.json"
REQ_SIZE="<WxH>"
REQ_QUALITY="low"
REQ_PROMPT='<ENGINEERED_PROMPT>'

for attempt in 1 2 3; do
  PAYLOAD=$(jq -n --arg p "$REQ_PROMPT" --arg s "$REQ_SIZE" --arg q "$REQ_QUALITY" \
    '{model:"gpt-image-2", prompt:$p, n:1, size:$s, quality:$q, output_format:"png"}')
  curl -s --http1.1 -X POST "https://api.openai.com/v1/images/generations" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" -o "$RESP"

  img_tokens=$(jq -r '.usage.input_tokens_details.image_tokens // 0' "$RESP")
  ret_size=$(jq -r '.size // ""' "$RESP")
  ret_quality=$(jq -r '.quality // ""' "$RESP")
  if [ "$img_tokens" -eq 0 ] && [ "$ret_size" = "$REQ_SIZE" ] && [ "$ret_quality" = "$REQ_QUALITY" ]; then
    break
  fi
  echo "gpt-image-2 silent coercion (attempt $attempt): image_tokens=$img_tokens size=$ret_size quality=$ret_quality — retrying" >&2
done

b64_len=$(jq -r '.data[0].b64_json // empty' "$RESP" | wc -c | tr -d ' ')
if [ "$b64_len" -lt 100 ]; then
  echo "Image generation failed. Response:"; jq '.error // .' "$RESP"
else
  jq -r '.data[0].b64_json' "$RESP" | base64 --decode > "<OUTPUT_PATH>"
fi
```

### Edit (image to image)

For generating an image using an input image as a reference. The input guides the model but does not anchor specific pixels — `/edits` produces a freshly generated output, not a localized modification of the input. OpenAI staff have confirmed this is whole-image regeneration. The endpoint is misnamed: think "img2img steered by a prompt," not "Photoshop-style edit."

Default to `gpt-image-1.5` for /edits because it exposes `input_fidelity`, the only dial that controls how strongly the model anchors to the input subject:

- `input_fidelity="low"` — model has freedom to reroll the subject. Use whenever the user wants the subject to *change*: repose, swap outfit, change expression. Verified to actually move a figure that gpt-image-2's permanent high-fidelity refused to move. Cheap input cost.
- `input_fidelity="high"` — model treats the subject as anchored. Use to preserve recognizable FEATURES (faces, logos, distinctive marks) — NOT pixels. Roughly 20× the input token cost of `low` (e.g. 6531 vs 323 tokens for a 1536×1024 input), so don't reach for it unless preservation matters.

```bash
RESP="$TMPDIR/img-response.json"
REQ_SIZE="<WxH>"
REQ_QUALITY="low"
REQ_FIDELITY="low"   # "low" for subject change, "high" for subject preservation

for attempt in 1 2 3; do
  curl -s --http1.1 -X POST "https://api.openai.com/v1/images/edits" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -F "model=gpt-image-1.5" \
    -F "image=@<INPUT_IMAGE_PATH>" \
    -F "input_fidelity=$REQ_FIDELITY" \
    -F "prompt=<ENGINEERED_PROMPT>" \
    -F "n=1" \
    -F "size=$REQ_SIZE" \
    -F "quality=$REQ_QUALITY" \
    -F "output_format=png" -o "$RESP"

  img_tokens=$(jq -r '.usage.input_tokens_details.image_tokens // 0' "$RESP")
  ret_size=$(jq -r '.size // ""' "$RESP")
  ret_quality=$(jq -r '.quality // ""' "$RESP")
  if [ "$img_tokens" -gt 0 ] && [ "$ret_size" = "$REQ_SIZE" ] && [ "$ret_quality" = "$REQ_QUALITY" ]; then
    break
  fi
  echo "/edits anomaly (attempt $attempt): image_tokens=$img_tokens (need >0; 0 means input was silently dropped, try a shorter prompt) size=$ret_size quality=$ret_quality — retrying" >&2
done

b64_len=$(jq -r '.data[0].b64_json // empty' "$RESP" | wc -c | tr -d ' ')
if [ "$b64_len" -lt 100 ]; then
  echo "Image edit failed. Response:"; jq '.error // .' "$RESP"
else
  jq -r '.data[0].b64_json' "$RESP" | base64 --decode > "<OUTPUT_PATH>"
fi
```

- Accepts PNG, WEBP, JPG under 50MB. Convert other formats with `sips -s format png <input> --out <output.png>`.
- Optional `-F "mask=@<MASK_PATH>"` (PNG with alpha, same dimensions as input). The whole image still regenerates — OpenAI staff confirm a mask doesn't constrain output to that region. Treat the mask as a soft hint about where the model should focus, nothing stronger.
- The prompt describes the *desired transformation*, not the input ("Transform this photo into a watercolor painting", not "a person standing").
- **Use edit for:**
  - Style transfer ("make this photo into a watercolor"), photo-to-illustration, illustration-to-photo.
  - Subject *change* with `input_fidelity="low"`: repose, swap outfit, change expression, adjust props. Verified to move subjects that gpt-image-2 refused to budge.
  - Subject *preservation* with `input_fidelity="high"`: anchor faces, logos, distinctive marks. Preserves recognizable features — NOT pixels. Roughly 20× input token cost vs `low`.
  - Resubmitting an approved low-quality output to `/edits` at higher quality to render the same idea cleaner — accepting that everything will reroll, just hopefully closer to the original.
- **Do NOT use edit for:**
  - "Change just this region, leave the rest alone" — every `/edits` call regenerates the whole image; the rest will drift visibly. No model in the gpt-image-* family supports pixel-preserving inpainting today. Even with a mask, the whole image regenerates.
  - "Iterate on the composition I picked" — every `/edits` call rerolls. Treat each call as a fresh generation steered by the input's style, not as a refinement of the input.
- **Symptom note: same MD5 across multiple `/edits` calls is not a cache.** If you're using `gpt-image-2` (no fidelity knob, permanent high fidelity) and asking for a small subject modification, the model returns near-byte-identical reproductions of the input across prompt variations. Cache-busters don't help (pixel-nudging the input, prompt nonces, the `user=` field — all confirmed not to move the output). The fix is `gpt-image-1.5` with `input_fidelity="low"`, which is why the snippet above defaults to it.
- **Use generate when** no reference image, text description only, or exploring fresh options the user has not yet picked from.

### Shared

- Auth: `$OPENAI_API_KEY` from env. If unset, tell the user before calling.
- Response is always base64. Pipe through `jq` and `base64 --decode`.
- Always check `b64_json` length before decoding. A malformed or empty response otherwise produces a 0-byte PNG and no error surfaces — surface the response body to the user instead.
- **Always pass `--http1.1` to curl.** The sandbox's HTTPS proxy (`HTTPS_PROXY=http://localhost:61610`) mangles HTTP/2 long downloads — large image responses fail mid-stream with `LibreSSL SSL_read: bad record mac, errno 0` and curl writes no response file. Downgrading to HTTP/1.1 fixes it without any sandbox bypass. The bug isn't in OpenAI or curl, it's the proxy. `--http1.1` is in both snippets above.
- **The snippets above retry on silent coercion** (generations). gpt-image-2 non-deterministically routes some text-to-image calls through a multi-pass "Thinking mode" path that silently overrides `quality` (e.g. low → high, billed at high) and `size`, and can return abstract stylized art instead of the requested style. The fingerprint on `/v1/images/generations` is `usage.input_tokens_details.image_tokens > 0` on a text-only call; the returned `quality` or `size` not matching the request is also a tell. The loop retries up to 3 times before giving up. OpenAI exposes no parameter to disable this path.
- **The snippets above retry on silent input drop** (edits). Empirically observed on `gpt-image-2` /edits — prompts above roughly 150 text tokens cause the API to silently ignore the attached image. The fingerprint is `usage.input_tokens_details.image_tokens == 0` in the response (the opposite of the generations fingerprint: on edits an image SHOULD be processed). The edit snippet retries on this. The threshold is unverified on `gpt-image-1.5`, so keep edit prompts under ~75 words defensively.
- **Quality is `low` unless the user explicitly authorizes higher.** Every generation, every edit, every iteration runs at `low` — including iterations that *feel* like quality bumps ("make it sharper", "crisper", "cleaner"). Only call at `medium` or `high` after asking the user and getting an explicit yes, and only for the specific image they greenlit.
  - `low` — cheapest, fast drafts. Default for every call.
  - `medium` — balanced, ~5–10x cost of low.
  - `high` — best detail, ~35x cost of low.
- Sizing: any `WxH` divisible by 16, max edge 3840px, max aspect ratio 3:1.

## Output

- **Path:** `./YYYY-MM-DD-HH:MM:SS-short-description.png`
  - Timestamp is generation time.
  - `short-description` is a 2-4 word kebab-case slug (e.g. `golden-retriever-field`, `neon-city-street`, `logo-concept`).
- **Auto-open:** always call `mcp__unsandboxed-runner__open_file` with the absolute path after saving. Do not call `open` via Bash — the in-sandbox subprocess can't reliably reach Launch Services and intermittently errors with `Error -600 procNotFound`.
- Surface the file per MEMENTO's rule (`image: file:///…` with `:` encoded as `%3A`).

## Prompt Engineering

Transform the user's rough idea into an optimized prompt. Follow this structure, including only what's relevant:

```
[Subject with specific details] + [Action/Pose] + [Setting/Environment] + [Style/Medium] + [Lighting] + [Camera/Composition] + [Mood/Atmosphere]
```

### Principles

- **Be specific.** "A golden retriever puppy with wet fur, tongue out, wearing a red bandana" beats "a dog."
- **Natural language.** GPT Image models respond to descriptive sentences, not keyword stacks.
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
- **No model in the gpt-image-* family supports pixel-preserving / localized edits today.** gpt-image-1, gpt-image-1-mini, gpt-image-1.5, gpt-image-2, and chatgpt-image-latest all regenerate the whole image when given an input via `/edits`. OpenAI staff have publicly stated they plan to add "precise in-painting" with no committed timeline. (The legacy dall-e-2 model historically supported pixel-level masking, but it's outside the gpt-image-* family.) The closest knob is `gpt-image-1.5`'s `input_fidelity`: `high` minimizes drift on what should stay; `low` frees the model to actually change the subject when that's the ask.

## Related

- **macOS app icon (squircle, transparent corners):** the model can't produce transparent backgrounds. Generate a square icon here, then hand off to the `app-icon` skill to apply the macOS squircle mask.
