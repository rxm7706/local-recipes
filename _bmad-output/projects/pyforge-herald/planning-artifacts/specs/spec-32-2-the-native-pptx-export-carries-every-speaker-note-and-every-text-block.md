---
title: '32.2: The native pptx export carries every speaker note and every text block'
type: 'fix'
created: '2026-10-08'
status: 'done'
difficulty: 'medium'
baseline_revision: '063fecf553893b0b6d63524558b74ba65674bb54'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-32-1-a-deck-exports-as-a-native-editable-pptx-through-pptxgenjs-plus.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_native.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/node/pptx_native.mjs
  - src/shared/packages/pyforge-herald/tests/unit/test_pptx_native.py
  - src/shared/packages/pyforge-herald/tests/integration/test_pptx_native_render.py
  - presentations/agentic-sdlc/src/marp/agentic-sdlc-deck-2026-08-01.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `herald deck pptx-native` (Story 32.1, CAP-57, FR-10.6) drops every multi-line speaker note and most of a
slide's text. FR-10.6 says the export carries a deck's notes, and the PRD's § Currency reconciliation — 2026-10-08
recorded the gap and left it for a fix story.

- **Notes.** In `src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_native.py`, `_extract_notes_and_body`
  (`:96-109`) treats a line as a note only when the stripped line both starts with `<!--` and ends with `-->` (`:101`).
  A `<!--` alone on its line opens a block whose lines go to the body. `_MARP_DIRECTIVE_COMMENT` (`:26`, used at
  `:102`) skips only single-line, `_`-prefixed directives.
- **Body text.** The body loop in `parse_slide_chunk` (`:121-143`) keeps images (`:123-129`), the first heading as the
  title (`:130-134`), a table (`:135-139`, the last one wins: `table = parsed`) and `- `/`* ` bullets (`:140-142`).
  Every other line, including a paragraph, a numbered item, a later heading, a fenced code line, a blockquote or the
  lines of a multi-line comment, is dropped at `:143`.
- **No place to put it.** `SlideModel` (`:35-41`) has only `title`, `bullets`, `table`, `notes` and `images`, and the
  driver (`node/pptx_native.mjs:24-57`) draws only those.
- **Measured on `8a2da2c010` (2026-10-08)** with the parser itself (`find_current_deck_marp` + `parse_marp_deck`) over
  the 15 current Marp decks (`presentations/<slug>/src/marp/<slug>-deck-<date>.md`, 263 slides):
  - 101 note comments: 51 single-line and 50 multi-line, all 50 in `agentic-sdlc`. 49 slides carry a note. Every
    `agentic-sdlc` slide loses its note (0 of 50 carried; `agentic-sdlc-deck-2026-08-01.md:29-31` is the first).
  - Body lines dropped, classified by line shape: 410 paragraph lines, 26 numbered-list lines, 109 headings after a
    slide's first, 12 fenced code blocks and 10 inline-HTML lines.
  - In these decks today: no slide has two tables, no bullet is nested, no `+` bullet is used and no un-prefixed
    directive comment is used. No note text leaks into a body field.
- **What is NOT the problem.** The verb, its flag (`pyforge.herald.deck_export_native`), the dated kind and
  `retire_superseded` are right, and so are the plugin, the Node call and `NODE_PATH`. Images already become picture
  shapes.

**Approach:** the parser keeps every note and every text block, in source order, and the driver draws each one as
native text.

- **Notes.** An HTML comment on a slide is a note unless it is a Marp directive comment. A directive comment is one
  where every non-empty line is `key: value` and every key is a Marp directive, global or local, with or without the
  `_` prefix:
  - global: `theme`, `style`, `headingDivider`, `size`, `math`, `title`, `description`, `author`, `image`,
    `keywords`, `url`, `marp`, `lang`;
  - local: `paginate`, `header`, `footer`, `class`, `backgroundColor`, `backgroundImage`, `backgroundPosition`,
    `backgroundRepeat`, `backgroundSize`, `color`.

  A comment may open and close on any lines. A note keeps its inner text with its line breaks, trimmed at both ends.
  Two or more notes on one slide join in source order, separated by a blank line. Nothing inside a comment, note or
  directive ever reaches the body: a `|` or a `- ` inside a note is not a table row or a bullet.
- **Text blocks.** After the title, the slide model carries one ordered sequence of body blocks in source order:
  - *heading*: every heading after the first, with its level;
  - *paragraph*: consecutive non-blank text lines, joined;
  - *bullet list*: `-`, `*` and `+` items, with their nesting depth;
  - *numbered list*: items, keeping their numbers;
  - *table*: every table, not only the last;
  - *code*: a fenced block's lines, verbatim, without the fence markers;
  - *quote*: a `>` block's text.

  Inline HTML tags are stripped and their text is kept; a line that is only tags carries nothing. Inline Markdown
  emphasis stays raw text, as Story 32.1 renders bullets today. Rich-text runs are not this story. The title rule does
  not change: the first heading, as Story 32.1's contract says. Images stay as they are.
- **The driver.** `node/pptx_native.mjs` draws each body block in order as native text:
  - text boxes for headings, paragraphs and quotes;
  - bullet runs with their indent level;
  - numbered runs;
  - code as monospace text;
  - tables through `addTable`;
  - notes through `addNotes` with the full text.

  It never skips a block for lack of room. Blocks are laid out top to bottom, and text that does not fit shrinks or
  overflows; it is never dropped. No slide becomes an image.
- **The model's JSON.** `slide_model_to_json` and the driver change together, since they ship in one package. Story
  32.1's tests keep their assertions on title, bullets, table and notes. A test updated for a renamed field asserts
  the same facts, never fewer.
- **Tests.**
  - `tests/unit/test_pptx_native.py`: a fixture slide for each block kind, a multi-line note, two notes on one slide,
    a `_class` directive and a `paginate: false` directive (neither is a note), a note containing `|` and `- ` (no
    table row and no bullet), and a non-directive comment such as `<!-- todo: x -->` (a note).
  - `tests/integration/test_pptx_native_render.py`: render a fixture deck that carries every kind, then read it back
    with python-pptx. Per slide, the notes text equals the joined notes, compared after whitespace normalisation. Each
    block's text is found in a text frame or table cell on that slide, top to bottom in source order. No picture shape
    stands in for text.
  - `tests/meta/test_pptx_native_live_decks.py` (new, parse-only, no Node): the measure over the current Marp decks.
    For every slide of every `presentations/<slug>/src/marp/<slug>-deck-<date>.md` that `find_current_deck_marp`
    returns:
    - every non-directive comment's text is in the model's notes;
    - every non-blank body line's text is in the title or a block. Table separator rows, fence markers, image-only
      lines and tag-only HTML lines are excluded.

    It asserts zero misses and that the deck count equals the glob's (15 on 2026-10-08), and reports the counts. On
    `8a2da2c010` it would report 50 lost notes and several hundred lost lines.

Ledger key: `32-2-the-native-pptx-export-carries-every-speaker-note-and-every-text-block`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-herald` CAP-57 (FR-10.6; D7): "a slide model (title, bullets, tables, speaker
  notes) … into native text boxes, tables and notes". Story 32.1 shipped it in Epic 32. A note or a text block the
  export drops is a defect of that shipped behaviour, so this story mints no CAP and registers no FR.
- **Architecture.** AD-3 as amended 2026-09-28 (night) and corrected 2026-10-08: the third PPTX producer,
  `pyforge.herald.pptx_native`. AD-4: the native kind and its retirement are unchanged. No AD is amended.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. The verb stays behind
  `pyforge.herald.deck_export_native`, unchanged.
- **Origin.** The PRD's § Currency reconciliation — 2026-10-08 ("One divergence, recorded and not repaired"); the
  station Dream's 2026-10-08 (native pptx notes) entry.

## Acceptance Criteria

- Given a fixture slide with a multi-line `<!--` note When `parse_marp_deck` runs Then the model's notes hold the full
  inner text with its line breaks. Given two notes on one slide Then both are kept, in order, separated by a blank
  line. Given `<!-- _class: lead -->` or `<!-- paginate: false -->` Then neither is a note. Given a note containing
  `|` or `- ` Then no table row or bullet appears in the body.
- Given a fixture slide with a paragraph, a numbered list, a second heading, a fenced code block, a blockquote, two
  tables and an inline-HTML line When it is parsed Then every one appears as a body block, in source order, and the
  title is still the first heading.
- Given the fixture deck rendered through the Node driver When python-pptx reads it back Then there is one slide per
  Marp slide. Each slide's notes text equals its joined notes after whitespace normalisation. Every block's text is in
  a text frame or table cell on its slide, in source order. No picture shape stands in for text. The render tests run
  and do not skip in `pyforge-herald-test`: `pytest -rs` lists no skip for them.
- Given the current Marp decks When `tests/meta/test_pptx_native_live_decks.py` runs Then it finds zero lost notes
  and zero lost text lines across every deck (15 decks and 263 slides on 2026-10-08).
- Given the change When `git diff` is read Then `pptx_pipeline.py`, the Marp export path (`scripts/deck_export.py`),
  `exporters.py`, `deck_versions.py`, the flag key and `src/platform/config/**` are unchanged, and no file under
  `presentations/` changes.
- Given the story lands When `pixi run --frozen -e pyforge-herald pyforge-herald-test` runs Then it passes.

## Boundaries & Constraints

**Always:**
- Change `pptx_native.py` and `node/pptx_native.mjs` together, and keep the model JSON in one shape both read.
- Keep Story 32.1's tests asserting what they assert today. A field rename updates a test; it never weakens one.
- Measure with the real parser (`find_current_deck_marp` + `parse_marp_deck`), never a parallel regex count, and
  report the counts in the Auto Run Result.
- Reconcile every Spec `spec-surface-check` names, then stamp each one scoped (AGENTS.md pre-PR item 5). Expect
  `spec-pyforge-herald`. Never run a bare `--write-baseline`.
- The PR carries the `maintenance` label.

**Never:**
- Never change `marp --pptx`, the python-pptx fill (`pptx_pipeline.py`), `exporters.py`, `deck_versions.py`, the verb's
  arguments, its exit codes or its flag.
- Never commit a generated `.pptx`, and never edit a file under `presentations/`.
- Never theme the output here. Fonts, colours and spacing from the design tokens are Story 32.3.
- Never add a dependency or touch `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Never edit the PRD, the spine or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| multi-line note | `<!--\nOpen here. …\n-->` | full text in the notes slide | — |
| single-line note | `<!-- notes for slide one -->` | in the notes slide (unchanged) | — |
| two notes | two comments on one slide | joined in order, blank line between | — |
| spot directive | `<!-- _class: lead -->` | not a note | — |
| local directive | `<!-- paginate: false -->` | not a note | — |
| non-directive key | `<!-- todo: fix the chart -->` | a note | — |
| note with markup | a note line `- a` or `a \| b` | stays in the note; no bullet or table row | — |
| paragraph | two adjacent text lines | one paragraph block | — |
| numbered list | `1. first` / `2. second` | a numbered block, numbers kept | — |
| second heading | `###### KICKER` then `## Real title` | title is `KICKER`; `Real title` is a heading block | — |
| two tables | two Markdown tables on a slide | both drawn (0 such slides today) | — |
| fenced code | a three-backtick block | its lines as monospace text, no fence markers | — |
| inline HTML | `<div class="x">Text</div>` | `Text` kept; a tag-only line carries nothing | — |
| overflowing slide | more blocks than fit | every block kept; text shrinks or overflows | never dropped |
| image | `![alt](img.png)` | picture shape (unchanged) | missing image skipped as today |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-08 (native pptx notes) entry.
- Epic: Epic 32 (`spec-pyforge-herald` CAP-57). The fix joins the epic that shipped the behaviour. `epic-32` was
  `done`; the new `backlog` story re-opens it to `in-progress` in the same change (doctor's
  `epic_reopened_by_new_story`).
- Ledger key: `32-2-the-native-pptx-export-carries-every-speaker-note-and-every-text-block`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 32.3 follows this story (`Deps: S-32.2`), because both change `pptx_native.py` and the driver.
- Spec: `spec-pyforge-herald/.memlog.md` records the mint. No contract change; `SPEC.md` is untouched.
- Dispatch note: Epic 32's `[epic_surfaces]` entry already admits the herald package and its tests,
  `scripts/.spec-surface-baseline.json` and every Spec memlog. No widening.
- Minted 2026-10-08 in one chain commit with Stories 31.3 and 32.3.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`),
  including the new live-deck measure and the render tests run, not skipped.

**Manual checks (not a dispatch gate):**
- Export the largest deck into a scratch clone: `git clone <worktree> <scratch>`, then from the worktree root run
  `PYFORGE_ENVIRONMENT=dev pixi run --frozen -e pyforge-guild herald deck pptx-native agentic-sdlc --repo-root
  <scratch>` — expected: exit 0. python-pptx then reads 50 slides and 50 non-empty notes from
  `<scratch>/presentations/agentic-sdlc/src/pptx/agentic-sdlc-deck-native-<date>.pptx`; on `8a2da2c010` it reads 0.
- Open that `.pptx` in PowerPoint or LibreOffice Impress, and confirm each slide's text is editable and in source
  order.
- `pixi run --frozen -e pyforge-herald pytest -rs src/shared/packages/pyforge-herald/tests/integration/test_pptx_native_render.py`
  — expected: pass, no skip.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped stamps.

## Spec Change Log

- No change yet.

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — implementation matches intent-contract; live-deck measure 0 lost notes / 0 lost body fragments across 15 decks and 263 slides)

## Auto Run Result

Status: done

Summary: Extended `pptx_native` parsing and the Node driver so multi-line Marp speaker notes, directive comments, and every body block kind (headings after the title, paragraphs, bullet and numbered lists, all tables, fenced code, blockquotes) serialize in source order and render as native PPTX text. Added a live-deck meta measure that reports zero note or body loss across all 15 current Marp decks (263 slides).

Files changed:
- `src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_native.py` — note/body parser and block model JSON
- `src/shared/packages/pyforge-herald/src/pyforge/herald/node/pptx_native.mjs` — ordered block rendering
- `src/shared/packages/pyforge-herald/tests/unit/test_pptx_native.py` — fixtures per block kind and note edge cases
- `src/shared/packages/pyforge-herald/tests/integration/test_pptx_native_render.py` — python-pptx read-back for every block kind
- `src/shared/packages/pyforge-herald/tests/meta/test_pptx_native_live_decks.py` — parse-only zero-loss gate on live decks
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md` — surface reconcile entry (Story 32.2)

Review: no patch/defer/intent_gap items.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — 1726 passed, 5 skipped (pptx render tests ran, not skipped)
- `python scripts/spec_surface_reconcile.py` — OK (no drift after memlog reconcile; no `--write-baseline`)

Residual risk: overflow layout relies on pptxgenjs shrink/overflow; no pixel-perfect ordering guarantee under extreme slide density (accepted per intent-contract).
