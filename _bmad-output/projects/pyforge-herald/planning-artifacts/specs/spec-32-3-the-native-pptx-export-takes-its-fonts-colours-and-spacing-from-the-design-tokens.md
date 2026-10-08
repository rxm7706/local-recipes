---
title: '32.3: The native pptx export takes its fonts, colours and spacing from the design tokens'
type: 'fix'
created: '2026-10-08'
status: 'ready-for-dev'
difficulty: 'medium'
baseline_revision: '063fecf553893b0b6d63524558b74ba65674bb54'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-32-1-a-deck-exports-as-a-native-editable-pptx-through-pptxgenjs-plus.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-32-2-the-native-pptx-export-carries-every-speaker-note-and-every-text-block.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_native.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/node/pptx_native.mjs
  - src/shared/packages/pyforge-herald/src/pyforge/herald/transport/base.py
  - presentations/_design-systems/modernist/theme.json
  - presentations/_design-systems/modernist/styles.css
  - presentations/_design-systems/modernist/templates/deck/index.html
  - presentations/_design-systems/modernist/readme.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the native `.pptx` export (Story 32.1, CAP-57) reads no design token. The spine's AD-5 (Modernist design
tokens as the single authority) and its PPTX Generation invariant (`ARCHITECTURE-SPINE.md:311`: "All fonts, colors,
spacing from design-tokens.json, never hardcoded") say otherwise. The spine's § Currency reconciliation — 2026-10-08
recorded this gap and left it for a fix story.

- **The driver hardcodes its look.** In `src/shared/packages/pyforge-herald/src/pyforge/herald/node/pptx_native.mjs`:
  - `pres.layout = "LAYOUT_16x9"` (`:22`);
  - the title at `x: 0.5, y: 0.4, w: 9, h: 0.8`, `fontSize: 32`, bold (`:28-35`);
  - bullets at `w: 9, h: 4`, `fontSize: 18` (`:40`), with a fixed `0.35` line step (`:41`);
  - tables at `w: 8.5`, `fontSize: 14`, a 1 pt border (`:45`);
  - images at `x: 6.5, y: 1.2, w: 3, h: 2.2` (`:50`).

  It sets no `fontFace` and no `color` anywhere, so pptxgenjs-plus's default face and colours apply.
  `pptx_native.py` passes it no token (`slide_model_to_json`, `:160-169`).
- **The file the spine names does not exist.** No tracked file is called `design-tokens.json`, and `git log --all --
  '*design-tokens*'` is empty. The tokens AD-5 means are the Modernist design system herald binds every deck to
  (`MODERNIST_DESIGN_SYSTEM_ID`, `transport/base.py:113`, used at `deck_pipeline.py:256`). Story 23.2 tracks them under
  `presentations/_design-systems/modernist/`:
  - `theme.json`: the palette (`bg` `#f3f2f2`, `surface` `#eae9e9`, `text` `#201e1d`, `accent` `#ec3013`) and the
    font families (`fonts.heading.family` and `fonts.body.family`, both `Archivo`);
  - `styles.css`: the same colours as `--color-*` (`:5-10`) and `--font-heading-weight: 800` (`:45`);
  - `templates/deck/index.html:16-26`: the deck's type scale and padding, on the 1920×1080 design canvas
    (`templates/deck/deck-stage.js:108-109`). The values are `--type-title` 64px, `--type-subtitle` 40px,
    `--type-body` 34px, `--type-small` 28px, `--type-kicker` 24px, `--pad-x` 120px, `--pad-top` 96px,
    `--pad-bottom` 120px and `--baseline` 48px. The template's own comment says to change one number there to re-size
    the whole deck.
- **What is NOT the problem.** The other two PPTX producers are not this story: `marp --pptx` and the python-pptx fill
  (`pptx_pipeline.py`, on its bundled Office template). Neither are the slide model's content (Story 32.2) or the verb
  and its flag.

**Approach:** `pptx_native.py` resolves the Modernist tokens once per export and hands them to the driver in the
model JSON. The driver takes every face, size, colour and offset from them.

- **The reader.** A stdlib reader in `pyforge.herald.pptx_native` (no new dependency) loads, under
  `<repo_root>/presentations/_design-systems/modernist/`:
  - `theme.json` for the palette and the heading and body families;
  - the `--font-heading-weight` declaration in `styles.css`;
  - the `--type-*`, `--pad-*` and `--baseline` declarations in `templates/deck/index.html`, read as `--name: <n>px;`.

  The design-system directory is one named constant, the system herald binds decks to. A missing file, or a missing
  or unparsable key, raises `HeraldError` naming the path and the key. Then the verb exits 1, writes no `.pptx` and
  retires nothing. It never falls back to a built-in default, because that would bring back the hardcoded values.
- **The scale.** The tokens are px on a 1920×1080 canvas. The driver's slide stays 16:9, and one factor maps the
  canvas to it: slide width ÷ 1920. Font sizes become points (px × slide width in pt ÷ 1920), and offsets become
  inches. The factor is computed once from the layout the driver declares, never written as a separate constant.
- **The mapping.**

  | Element | Face | Size | Colour |
  |---|---|---|---|
  | slide background | — | — | `palette.bg` |
  | title | heading family, bold when `--font-heading-weight` ≥ 600 | `--type-title` | `palette.text` |
  | headings after the title (Story 32.2) | heading family | `--type-subtitle` | `palette.text` |
  | paragraphs, bullets, numbered items and quotes | body family | `--type-body` | `palette.text` |
  | tables and code | body family | `--type-small` | `palette.text`; header-row fill `palette.surface`; rules `palette.text` |
  | margins | — | left and right `--pad-x`, top `--pad-top`, bottom `--pad-bottom` | — |
  | gaps between blocks and the line step | — | `--baseline` | — |
  | images | placed inside the padded area | — | — |

  The Modernist tokens carry no monospace family, so code takes the body family. A mono face is not invented here.
- **The model JSON.** `slide_model_to_json` gains one `tokens` block with resolved values: faces, `#rrggbb` colours,
  sizes in px with the canvas size. The driver reads only that block for every face, size, colour and offset.
- **Tests.**
  - `tests/unit/test_pptx_native.py`: the reader on the live Modernist files returns the values listed above, and on
    a fixture directory with a missing file, a missing `--type-title` or a malformed `theme.json` it raises
    `HeraldError` naming the path and the key.
  - `tests/integration/test_pptx_native_render.py`: render a fixture deck with the live tokens and read it back with
    python-pptx. The title runs use the heading family, at `--type-title` scaled, in `palette.text`. The body runs use
    the body family at `--type-body` scaled. Table cells are at `--type-small` scaled. The slide background is
    `palette.bg`, and the title box's left offset is `--pad-x` scaled (to within one EMU of rounding). Then render it
    again with a mutated copy of the token directory: a different accent and text colour, `Courier New` as the body
    family, a doubled `--type-title` and a doubled `--pad-x`. Each of those read-back values changes to the mutated
    one.
  - `tests/meta/test_pptx_native_driver_has_no_literals.py` (new): the driver source has no hex colour literal, no
    string literal for `fontFace`, and no numeric literal assigned to `fontSize`, `x`, `y`, `w`, `h` or `margin`.

Ledger key: `32-3-the-native-pptx-export-takes-its-fonts-colours-and-spacing-from-the-design-tokens`.
Type / Effort / Deps: fix / M / S-32.2.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-herald` CAP-57 (FR-10.6; D7): the native `.pptx` producer that Story 32.1
  shipped in Epic 32. A producer that ignores the design tokens breaks AD-5 and the PPTX Generation invariant, which
  bind every PPTX. That is a defect of shipped behaviour, so this story mints no CAP and registers no FR.
- **Architecture.** AD-5 (Modernist design tokens as single authority: "Templates consume tokens declaratively, never
  hardcode values"); § Invariants by Slice, PPTX Generation; AD-3 as amended. No AD is amended. The spine names the
  token file `design-tokens.json`, which does not exist. This story reads the tracked Modernist files and does not
  mint a `design-tokens.json`, because a second copy of the values would be a second authority, which AD-5 forbids.
  The name divergence is recorded on the Spec memlog for the next chain-currency cascade.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. The verb stays behind
  `pyforge.herald.deck_export_native`, unchanged.
- **Origin.** The spine's § Currency reconciliation — 2026-10-08 ("One divergence, recorded and not repaired (the PPTX
  Generation invariants)"); the station Dream's 2026-10-08 (native pptx tokens) entry.

## Acceptance Criteria

- Given the live Modernist files When the reader runs Then it returns the heading and body families `Archivo`, the
  palette `bg` `#f3f2f2`, `surface` `#eae9e9`, `text` `#201e1d` and `accent` `#ec3013`, the heading weight 800, and
  the px values of `--type-title` (64), `--type-subtitle` (40), `--type-body` (34), `--type-small` (28),
  `--pad-x` (120), `--pad-top` (96), `--pad-bottom` (120) and `--baseline` (48), all read from the files, none
  restated in code.
- Given a fixture deck rendered with the live tokens When python-pptx reads it back Then:
  - every title run's font name is the heading family, at `--type-title` × (slide width in pt ÷ 1920), in
    `palette.text`;
  - every body run's font name is the body family, at `--type-body` scaled;
  - table cells are at `--type-small` scaled;
  - each slide's background fill is `palette.bg`;
  - the title box's left offset is `--pad-x` scaled, to within one EMU.
- Given a mutated copy of the token directory (colours, body family, `--type-title` and `--pad-x` changed) When the
  same deck renders Then each of those read-back values equals the mutated token, not the original.
- Given a token directory missing `theme.json`, or a template missing `--type-title` When `herald deck pptx-native`
  runs (flag on) Then it exits 1 with a message naming the path and the key, writes no `.pptx`, and leaves an older
  `-deck-native-` version in place.
- Given `node/pptx_native.mjs` When the new meta test scans it Then it finds no hex colour literal, no `fontFace`
  string literal and no numeric literal for `fontSize`, `x`, `y`, `w`, `h` or `margin`.
- Given the change When `git diff` is read Then no file under `presentations/` changed, and `pptx_pipeline.py`,
  `scripts/deck_export.py`, `exporters.py`, `deck_versions.py` and the flag key are unchanged.
- Given the story lands When `pixi run --frozen -e pyforge-herald pyforge-herald-test` runs Then it passes, including
  Story 32.1's and 32.2's tests, with the render tests run and not skipped.

## Boundaries & Constraints

**Always:**
- Read every face, size, colour and offset from the Modernist files at export time, and fail loudly when one is
  missing.
- Keep Story 32.2's ordering and completeness: every note and every block still reaches the slide.
- Reconcile every Spec `spec-surface-check` names, then stamp each one scoped (AGENTS.md pre-PR item 5). Expect
  `spec-pyforge-herald`. Never run a bare `--write-baseline`.
- The PR carries the `maintenance` label.

**Never:**
- Never write a `design-tokens.json` or any other second copy of the token values, and never edit a file under
  `presentations/_design-systems/`. Those files are Design's, kept by the design-sync loop (Epic 23).
- Never hardcode a fallback face, colour or size in the driver or the reader.
- Never change `marp --pptx`, the python-pptx fill, `exporters.py`, `deck_versions.py`, the verb's arguments, its exit
  codes or its flag.
- Never commit a generated `.pptx`, and never edit a Marp source under `presentations/`.
- Never add a dependency or touch `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Never edit the PRD, the spine or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| live tokens | the tracked Modernist files | Archivo, the Modernist palette, sizes and padding scaled to the slide | — |
| mutated tokens | a fixture copy with changed values | the export follows the fixture | — |
| `theme.json` missing | no file | no export | `HeraldError` naming the path; verb exits 1; nothing retired |
| key missing | template without `--type-title` | no export | `HeraldError` naming the key and the path |
| malformed value | `--pad-x: wide;` | no export | `HeraldError` naming the key |
| heading weight below 600 | `--font-heading-weight: 400` in a fixture | title not bold | — |
| code block | a fenced block (Story 32.2) | the body family at `--type-small` | no invented mono face |
| other design systems | `broadsheet/`, `nocturne/` | not read | out of scope (decks bind to Modernist) |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-08 (native pptx tokens) entry.
- Epic: Epic 32 (`spec-pyforge-herald` CAP-57). The fix joins the epic that shipped the behaviour. `epic-32`
  re-opens to `in-progress` with Story 32.2 in the same change.
- Ledger key: `32-3-the-native-pptx-export-takes-its-fonts-colours-and-spacing-from-the-design-tokens`.
- Ledger status at mint: `backlog`.
- Deps: S-32.2. Both stories change `pptx_native.py` and the driver; this one themes the blocks 32.2 adds.
- Spec: `spec-pyforge-herald/.memlog.md` records the mint and the `design-tokens.json` name divergence. No contract
  change; `SPEC.md` is untouched.
- Dispatch note: Epic 32's `[epic_surfaces]` entry already admits the herald package and its tests and
  `presentations/**`, which this story only reads. `scripts/.spec-surface-baseline.json` and every Spec memlog are
  admitted too. No widening.
- Minted 2026-10-08 in one chain commit with Stories 31.3 and 32.2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`),
  including the token read-back, the mutation render and the driver-literal scan.

**Manual checks (not a dispatch gate):**
- Export a deck into a scratch clone: `git clone <worktree> <scratch>`, then from the worktree root run
  `PYFORGE_ENVIRONMENT=dev pixi run --frozen -e pyforge-guild herald deck pptx-native pyforge-herald --repo-root
  <scratch>` — expected: exit 0. Open the `.pptx` and confirm Archivo text in `#201e1d` on `#f3f2f2`.
- `pixi run --frozen -e pyforge-herald pytest -rs src/shared/packages/pyforge-herald/tests/integration/test_pptx_native_render.py`
  — expected: pass, no skip.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped stamps.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
