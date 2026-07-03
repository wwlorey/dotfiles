# Anatomy of an Akathist

An akathist is a fixed-form hymn of praise. Knowing the skeleton lets you
segment the fetched text correctly and map each part onto a template macro.

## The fixed skeleton

- **Title / dedication.** "Akathist to <Saint / Feast>", often a commemoration
  date or epithet. → `\akatitle` / `\akasubtitle`.
- **Introductory / usual-beginning prayers.** Some sources print the opening
  prayers (Trisagion, Psalm 50, etc.) before Kontakion 1; many omit them and
  begin directly. Include exactly what the source page contains — do not add
  prayers it does not print.
- **Body: 13 Kontakia and 12 Ikoi, strictly alternating.**
  Kontakion 1 → Ikos 1 → Kontakion 2 → Ikos 2 → … → Ikos 12 → Kontakion 13.
  - A **Kontakion** is a short stanza. Kontakia 2–13 close with the refrain
    **"Alleluia!"** Kontakion 1 closes with the same refrain as the Ikoi.
  - An **Ikos** is a longer stanza: a lead paragraph, then a run of
    **Chairetismoi** — salutations each beginning "Rejoice, …!" — closing with
    a fixed **refrain** ("Rejoice, O holy N.N., …!"). The refrain is identical
    across every Ikos and after Kontakion 1.
- **Repeat.** After Kontakion 13 (often rubricated "said thrice"), the source
  usually repeats **Ikos 1** and then **Kontakion 1**.
- **Closing.** One or more prayers to the saint, sometimes a dismissal.

## Mapping the source HTML to macros

`source.html` — not a plain-text copy — is the ground truth, because the source
carries its formatting in **HTML elements and CSS classes**, and plain text
throws that away. Map each element to a macro, and take emphasis (bold / italic)
**only** from what the source marks:

| Source HTML | Macro / rendering |
|-------------|-------------------|
| `<h1>` (page title) | `\akatitle{…}` |
| `<h2>` / `<h3>` ("Kontakion N", "Ikos N") | `\heading{…}` |
| `<p>…</p>` (stanza prose, incl. a refrain the source runs inline) | plain paragraph |
| `<p>a<br>b<br>c</p>` (salutations + their closing refrain) | ONE plain paragraph, lines joined with `\\` |
| `<p class="italic">…</p>` (a rubric the source italicizes) | `\rubric{…}` |
| `<strong>`/`<b>` or a `font-bold` class, mid-text | `\textbf{…}` |
| `<em>`/`<i>` or an `italic` class, mid-text | `\textit{…}` |

## Formatting fidelity rules (match the source exactly)

- **Emphasis is source-driven.** Bold only where the source uses a bold element
  or a bold class; italic only where the source uses an italic element or
  `class="italic"`. **Never add weight or slant the source lacks** — a refrain,
  a salutation, or an "Alleluia" that the source sets as plain paragraph text
  stays plain. (Headings are the one built-in emphasis, and they earn it: the
  source marks them as `<h1>`/`<h3>`.)
- **Emphasis lives in classes too, not just tags.** Grep for `class="…italic…"`
  and `class="…font-bold…"` (and `<strong>`/`<em>`), not only `<b>`/`<i>` — this
  source page carries all its italics via a CSS class.
- **Mirror the block structure.** One source element → one booklet block, in
  document order. `<br>` inside a `<p>` is a single-spaced line break (`\\`), not
  a paragraph break — keep salutations tight, as the source has them.
- **A source page footnote about color:** rubrics may be colored (e.g. rose/red)
  in the source. The booklet is monochrome by default; italic carries the rubric
  distinction. Note this as an intended divergence rather than a fidelity bug.

## Text fidelity rules (the words must be exact)

- Transcribe the akathist text **verbatim**: every word, in source order, with
  the source's spelling, capitalization, and punctuation. Do not paraphrase,
  modernize, correct, reorder, or drop anything.
- Only matter that is NOT the akathist — website navigation, ads, share buttons,
  site footers — is excluded. When in doubt whether a line is part of the
  prayer, keep it.
- Preserve refrains in full every time they occur; do not abbreviate a repeated
  refrain to "(as above)" unless the source itself does.
- LaTeX-escape special characters (`&` → `\&`, `%` → `\%`, `#` → `\#`,
  `_` → `\_`, `$` → `\$`). These escapes do not count as text changes — the
  verifier normalizes them away.
- The exact-text QA gate (`scripts/verify`) is non-negotiable: the words in the
  built PDF must match the text projected from `source.html` exactly — every
  word, its case, and its punctuation. It runs after every build.
