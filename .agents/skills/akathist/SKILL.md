---
name: akathist
description: Turning a URL to an akathist into a printable, double-sided booklet PDF typeset in Janson Text LT Std and saved under ~/Documents/akathists/<name>/. Consult whenever the user supplies a link to an akathist (or a saint's/feast's akathist) and wants it made into a booklet, a printable, a PDF for printing, or "formatted like the canon"; whenever they ask to typeset, impose, or lay out an akathist for double-sided/saddle-stitch printing; or whenever an akathist needs its text verified word-for-word against its source. Even a bare "make a booklet from this akathist link" counts.
---

# Akathist Booklet

Take a URL to an akathist, capture its **HTML** as the ground truth (so the
source's formatting is preserved, not just its words), typeset it verbatim in
Janson Text LT Std at an 18pt body — mirroring the source's own emphasis, adding
none of its own — and impose it 2-up saddle-stitch for double-sided **long-edge**
printing. Every run ends with three gates, none skippable: a strict exact-text QA
gate (the built PDF's text must equal the source exactly — every word, its case,
and its punctuation), an imposition check (the booklet's geometry and page
rotation must be correct for booklet-mode printing), and an independent review (a
separate agent, given only the PDF and the original web page, re-confirms the two
match in both text and formatting).

Output lands in `~/Documents/akathists/<name>/`, where `<name>` is a kebab-case
slug for the saint or feast (e.g. `st-nectarios`, `theotokos-joy-of-all-who-sorrow`).

Read `references/structure.md` before transcribing — it is the anatomy of an
akathist (13 Kontakia + 12 Ikoi, Chairetismoi, refrains) and the macro map.

## Inputs

- **URL** (required) — the page hosting the akathist text.
- **name / slug** (optional) — if the user doesn't give one, derive it from the
  title.

## Preflight

- Font **Janson Text LT Std** must be installed: `fc-list | grep -F "Janson Text LT Std"`.
  If absent, stop and tell the user to drop the OTF into `~/Library/Fonts/`.
- `xelatex`, `pdfjam` (TeX Live / MacTeX), and `pdftotext` (poppler) must be on PATH.
- `python3` with the `pypdf` module — the build's long-edge imposition step
  needs it (`pip install pypdf` if missing).

## Procedure

1. **Fetch the source — as HTML.** The ground truth is the source's **HTML**,
   not a plain-text copy: the page carries its formatting in elements (`<h1>`,
   `<h3>`, `<p>`, `<br>`) and CSS classes (e.g. `class="italic"`,
   `class="…font-bold…"`), and plain text throws every bit of that away. Fetch
   the raw HTML — `curl -sL "<URL>"` is reliable (a summarizing `WebFetch` will
   drop the markup and may refuse to reproduce a full prayer). Keep only the
   prayer region: the title and the ordered run of headings and paragraphs; drop
   site chrome (nav, header logo, ads, share buttons, footer, scripts). If it
   looks truncated, re-fetch; never fill gaps from memory.

2. **Save `source.html` — the single source of truth.** Write the cleaned prayer
   HTML — every `<h1>`/`<h3>`/`<p>` in order, `<br>` line breaks preserved, and
   any emphasis element or class (`italic`, `font-bold`, `<strong>`, `<em>`)
   kept — to `~/Documents/akathists/<name>/source.html`. It holds both the words
   and the formatting; nothing else needs to be stored (the QA gate projects the
   text out of it directly). Prayer only: no site furniture, nothing you don't
   intend to include.

3. **Author `<name>.tex`.** Copy `references/template.tex` to
   `~/Documents/akathists/<name>/<name>.tex` and fill it from `source.html`,
   following `references/structure.md` for the element→macro mapping. Two
   fidelities, both required: **text** — every word, spelling, capitalization,
   punctuation, and order exactly as the source; and **formatting** — bold and
   italic **only where the source marks them** (headings from `<h1>`/`<h3>`,
   italics from `<em>`/`class="italic"`, bold from `<strong>`/`font-bold`), and
   nowhere else. Salutations and refrains the source renders as plain paragraph
   text stay plain. LaTeX-escape specials (`& % # _ $`); those escapes are
   normalized away by the QA gate and don't count as text changes.

4. **Build.** Run
   `~/.agents/skills/akathist/scripts/build ~/Documents/akathists/<name>/<name>.tex`.
   It preflights the font, runs XeLaTeX, imposes the booklet with pdfjam, and
   writes `<name>.pdf` (reading copy, letter portrait, 18pt body) and
   `<name>-booklet.pdf` (imposed, letter landscape, 2 pages/side, long-edge
   duplex). **Invoke it by this full path** —
   `akathist/scripts/*` is excluded from the sandbox in settings, so the
   command runs unsandboxed and may write the PDFs under `~/Documents` and let
   fontconfig rebuild its cache. A shorter relative path would not match the
   exclusion and would fail on those writes.

5. **QA gate — exact-text verification (non-negotiable).** Run, again by full path,
   `~/.agents/skills/akathist/scripts/verify ~/Documents/akathists/<name>/<name>.pdf ~/Documents/akathists/<name>/source.html`.
   It projects the text out of `source.html` and diffs it against the built PDF's
   text as a token stream with **case and punctuation preserved** — a changed
   capital, a dropped comma, or a missing colon fails. It folds away only genuine
   typographic equivalences and layout artifacts (curly↔straight quotes, dash
   variants, ligatures, reflowed line wrapping, footer page numbers), never
   content. It must print **`MATCH`**. On `MISMATCH` it prints a token-level diff
   (`<` = in the PDF only, `>` = in the source only) — reconcile every difference
   by fixing `<name>.tex` (a mis-transcription) or `source.html` (a stray
   non-prayer line or intended difference), rebuild (step 4), and re-verify. Do
   not report the booklet done until `verify` reports `MATCH`.

6. **Imposition check — booklet-mode correctness (non-negotiable).** Run, by full
   path,
   `~/.agents/skills/akathist/scripts/check-booklet ~/Documents/akathists/<name>/<name>-booklet.pdf ~/Documents/akathists/<name>/<name>.pdf`.
   It confirms the booklet is laid out so it will actually fold and read
   correctly: every sheet is letter-landscape, the sheets alternate 0°/180°
   rotation (long-edge duplex), and the imposed slot count is a multiple of four
   that covers all reading pages. It must print **`BOOKLET OK`**. On
   **`BOOKLET FAIL`** it lists each failed assertion — rebuild (step 4) and
   re-check; do not report done until it passes.

7. **Independent review — third-party text + formatting check (non-negotiable).**
   Steps 5–6 verify the PDF against your own transcription; this step re-derives
   the truth from the original web page with fresh eyes, checking both wording and
   emphasis. Following the `orchestrate` skill, spawn one subagent (the Agent tool)
   using the briefing in `references/reviewer-prompt.md`, substituting the reading
   PDF path (`~/Documents/akathists/<name>/<name>.pdf`) and the source URL. Hand
   the agent **only those two inputs** — never `source.html` or the `.tex` — so
   its judgement is independent and uncrowded. It returns **`VERDICT: EXACT
   MATCH`** or **`VERDICT: DISCREPANCIES FOUND`** with a list. On discrepancies,
   confirm each against the source, fix `<name>.tex` (and `source.html` if the
   transcription itself was wrong), rebuild (step 4), and re-run steps 5–7. Do not
   report the booklet done until the reviewer returns `EXACT MATCH`.

8. **Report.** Surface the artifacts as clickable links, one per line:

   ```
   booklet: file:///Users/william/Documents/akathists/<name>/<name>-booklet.pdf
   reading: file:///Users/william/Documents/akathists/<name>/<name>.pdf
   ```

   (URL-encode any `:` in the path as `%3A`.) Tell the user the booklet is the
   one to print double-sided (flip on **long** edge) and fold.

## Notes

- **`source.html` is the single source of truth.** It preserves the source's
  structure and emphasis (headings, `class="italic"` rubrics, any bold); the
  `.tex` mirrors that emphasis and adds none of its own, and the word-level QA
  gate (`verify`) projects the text out of the HTML directly — no separate
  `.txt` is stored. See `references/structure.md`.
- The booklet geometry: letter-portrait source pages scaled 2-up onto
  letter-landscape sheets, saddle-stitch page order, blank pages auto-padded to
  a multiple of four. `pdfjam --booklet true --landscape --paper letterpaper`
  produces this, then a `pypdf` pass rotates every back-side sheet 180° so the
  sheets alternate 0°/180° and print correctly with a **long-edge** duplex flip.
  `scripts/check-booklet` asserts all of this after every build.
- The body is set at 18pt on 24pt leading and the title at 24pt (see
  `references/template.tex`) — a large, open, readable devotional size, with
  `\parskip` opening the space between paragraphs.
- The body is **ragged-right** (`\RaggedRight`) with hyphenation off: even word
  spacing everywhere, no stretched gaps, and no word ever split across a line.
- Headings are kept with their stanza: `\heading` uses `\needspace` to push a
  heading to the next page when too few lines remain, so a "Kontakion N" / "Ikos
  N" label never dangles alone at the foot of a page.
- Bold headings and italic rubrics are synthesized (FakeBold/FakeSlant) from the
  single installed Janson "55 Roman" OTF — no other weights are needed.
