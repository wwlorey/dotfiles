# Independent reviewer briefing

Spawn one subagent with the Agent tool (Claude Code primitive; any harness with a
subagent spawn works). Substitute `<PDF_PATH>` and `<URL>`, then pass the block
below verbatim as the prompt. Hand the worker **only these two inputs** — never
`source.html`, the `.tex`, or your own transcription — so its verdict is reached
independently and is not anchored to the same text the booklet was built from.

```
Goal: Independently confirm that the akathist typeset in a built PDF matches its
original web source EXACTLY — in BOTH text (every word, its capitalization, its
punctuation) AND formatting (what is bold, italic, or a heading) — and report any
discrepancy.

You are given exactly two things, and nothing else:
- PDF (the typeset reading copy):  <PDF_PATH>
- SOURCE URL (the page it was transcribed from):  <URL>

Do NOT look for or read any other file — no source.html, no .tex, no notes. Your
judgement must rest only on the PDF and the live web page, so it is not biased by
any intermediate transcription.

Scope: READ-ONLY. Do not edit anything. Work under $TMPDIR for any temp files.

Method:
- Extract the PDF text:  pdftotext -nopgbrk "<PDF_PATH>" -   (and open the PDF
  itself to SEE which lines are bold / italic / centered headings).
- Fetch the page's RAW HTML with  curl -sL "<URL>"  — do not rely on a
  summarizing fetch, which discards the markup you need. The source conveys
  emphasis through HTML elements AND CSS classes: `<h1>`/`<h3>` headings,
  `<strong>`/`<b>` or a `font-bold` class for bold, `<em>`/`<i>` or
  `class="italic"` for italic. Inspect the tags and class attributes, not just
  the visible text. Ignore site furniture (nav, ads, share buttons, footers) and
  page numbers.
- Compare TEXT: the title, every Kontakion (1-13), every Ikos (1-12), every
  "Rejoice…" salutation, every refrain, and any opening/closing prayer — wording,
  order, capitalization (including divine pronouns Thou / Thee / Thy / Who), and
  punctuation.
- Compare FORMATTING: for each element, does the PDF's emphasis match the
  source's? Headings bold in both; a rubric the source italicizes (e.g.
  `class="italic"`) italic in the PDF; and — critically — anything the source
  renders as plain paragraph text (salutations, refrains, "Alleluia") must NOT be
  bold or italic in the PDF. Flag any emphasis the booklet ADDS or DROPS. (Color
  is out of scope — the booklet is monochrome by design.)

Return format (text only):
VERDICT: EXACT MATCH
  — or —
VERDICT: DISCREPANCIES FOUND
  - <location, e.g. "Ikos 5, salutation 3">: <text or formatting discrepancy — PDF has … | source has …>
  - …one line per discrepancy…
Then a one-sentence summary.

You are a worker, not an orchestrator. Return text only. Do NOT produce spoken or
audio output of any kind (the orchestrator handles voice). Do NOT spawn further
workers via the Agent tool. Your final text reply IS the deliverable: return raw
content, not a human-facing message.
```
