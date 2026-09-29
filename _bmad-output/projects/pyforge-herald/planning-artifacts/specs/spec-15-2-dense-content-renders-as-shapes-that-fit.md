---
title: 'Dense content renders as shapes that fit'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: '585d1799199bb7e29c9a3134bc373f13ce5632db'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pptx-deck-generation/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pptx-custom-shapes/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-15-1-template-parse-then-fill-produces-a-genuinely-editable-deck.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 15.1's template-parse-then-fill pipeline can only fill text into placeholders a `.pptx` template already anticipates. The six-act deck framework's dense content -- persona cards, metric boxes, tables, section labels -- has no matching placeholder, and hand-authoring OOXML or guessing a font size is exactly what this whole pipeline exists to avoid.

**Approach:** Add four directly-callable shape functions (`add_card`/`add_metric_box`/`add_table`/`add_section_label`) to `pptx_pipeline.py` that render real, editable python-pptx objects at caller-given EMU geometry, sized by a new Pillow-`ImageFont`-measured autofit engine (wrap, shrink, orphan rebalancing) instead of a guess. `content_plan.json`'s existing per-slide schema gains an optional `"shapes"` list so the existing `herald deck pptx-fill` command reaches them -- no new CLI surface, no new dependency (Pillow and python-pptx are both already direct `pyforge-herald` dependencies).

## Boundaries & Constraints

**Always:**
- Render every shape via python-pptx's high-level object model only (`add_shape`/`add_textbox`/`add_table`, `text_frame`/`run`/`paragraph`) -- never hand-written or hand-edited OOXML/XML strings, the same discipline as Story 15.1.
- Every shape's fill and text color reference a theme color (`MSO_THEME_COLOR`), never a hardcoded RGB hex value -- color comes from the repo's own template, never an external brand's.
- Font size and line-wrap decisions come from Pillow `ImageFont` measurement of the exact text that gets written to the run -- never a hardcoded/guessed size, and never left to PowerPoint's own auto-fit-at-open-time behavior (a substituted font could silently re-wrap a carefully measured break).
- Validate every shape entry in `content_plan.json` (type, required fields, positive geometry) before any slide is materialized -- preserves `fill_template`'s existing "no file written on a bad plan" invariant.
- Coexist with, never modify, Story 15.1's existing placeholder-fill behavior -- the `"shapes"` key is optional and additive to each slide entry.

**Block If:** None identified -- the two open implementation choices (title/value height-budget caps, table's single-global-font-size rule) are resolved directly below (Design Notes), not blockers.

**Never:**
- Do not implement chart or SmartArt rendering, or dynamic data binding -- explicit `spec-pptx-custom-shapes` non-goals.
- Do not build a general-purpose drawing library beyond the four named shape types.
- Do not add a new CLI subcommand -- the existing `pptx-fill` content_plan.json path is the only entrypoint.
- Do not add a new runtime dependency or bundle/reference an external font file -- Pillow's own bundled scalable default font is the measurement source.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Card shape | content_plan slide with a `"shapes": [{"type": "card", ...}]` entry | New slide with a real autoshape: bold title + body paragraph, real `<a:t>` runs, theme-color fill | n/a |
| Metric box shape | `{"type": "metric_box", "value": ..., "label": ...}` | Autoshape with a large value line + small label line, both real text runs | n/a |
| Table shape | `{"type": "table", "rows": [[...], ...]}` | Real `GraphicFrame` table, one consistent font size across every cell, header row visually distinct | n/a |
| Section label shape | `{"type": "section_label", "text": ...}` | Textbox with a single autofit-sized, theme-colored run | n/a |
| Dense real content | The 4 real Warden-deck Appendix persona strings (~90-140 chars each) packed into 2.15in x 3.0in cards | Autofit shrinks/wraps each card's title and body independently; the returned font size and line count, re-measured, stay within the card's height | No error expected |
| Extreme overflow | Text so long even the shape type's minimum font size still overflows the box | Renders at the minimum size anyway (best effort -- a slide must always render something) | No error, no crash |
| Unknown shape type | `{"type": "chart", ...}` | No file written | `InvalidContentPlanError`, exit 1 |
| Missing required field | `{"type": "card", "title": "x"}` (no `"body"`) | No file written | `InvalidContentPlanError`, exit 1 |
| Non-positive geometry | `"width": 0` or a negative `"height"` | No file written | `InvalidContentPlanError`, exit 1 |
| No `"shapes"` key | An existing Story 15.1-shaped content_plan entry (placeholders only) | Unchanged: behaves exactly as before this story | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/pptx_pipeline.py` -- EXTEND (does not become a new package module, so `test_bridge.py`'s determinism-sweep exclusion set at `test_bridge.py:353` needs no change):
  - Autofit engine: `FittedText` dataclass (`font_size_pt: int`, `lines: tuple[str, ...]`); `fit_text(text, width_emu, height_emu, *, max_pt, min_pt) -> FittedText` using `PIL.ImageFont.load_default(size=N)` (Pillow >=10.1's bundled scalable Aileron font -- real glyph metrics, zero new dependency, zero font-file-path resolution); private `_wrap_words`/`_rebalance_orphan`/`_fits_at_size` helpers.
  - Shape dataclasses: `CardShape`/`MetricBoxShape`/`TableShape`/`SectionLabelShape` (frozen, geometry + type-specific fields) -- content_plan.json's internal representation, mirroring `TemplatePlaceholder`'s existing style (`pptx_pipeline.py:57-70`).
  - Public shape API: `add_card`/`add_metric_box`/`add_table`/`add_section_label(slide, left, top, width, height, ...)` -- the epics-named functions, operating directly on a python-pptx `Slide` (the "reachable enough" hook Story 15.1 deliberately left, per its own Design Notes).
  - `_resolve_shapes`/`_resolve_one_shape`/`_resolve_shape_geometry` -- validate a slide entry's `"shapes"` list, following `_resolve_placeholder_values`'s existing validate-before-materialize style (`pptx_pipeline.py:197-246`).
  - `_add_shapes(slide, shapes)` -- dispatches resolved shapes to the four `add_*` functions.
  - `fill_template` -- extend the existing two-phase loop (`pptx_pipeline.py:262-301`) to resolve + carry `shapes` alongside `placeholder_values`, then call `_add_shapes` after `_set_placeholder_text`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- extend `InvalidContentPlanError`'s docstring (`errors.py:153-160`) to note it also covers Story 15.2 shape validation; no new exception class.
- `src/shared/packages/pyforge-herald/tests/test_pptx_pipeline.py` -- extend (flat `test_<module>.py` convention): autofit engine unit tests, one test per shape function, the extended content_plan I/O matrix above, and the Warden-appendix dense-content acceptance case (source text below).
- `presentations/pyforge-warden/src/marp/pyforge-warden-deck-2026-07-15.md:413-419` -- READ-ONLY source of the 4 real Appendix persona strings used as the acceptance test's dense-content fixture (the only `## Appendix` slide in any station deck in this repo today).

## Tasks & Acceptance

**Execution:**
- `pptx_pipeline.py` -- add the autofit engine (`fit_text` + private helpers) -- the pure text-measurement core every shape function depends on.
- `pptx_pipeline.py` -- add the four shape dataclasses + `_resolve_shapes`/`_resolve_one_shape`/`_resolve_shape_geometry` -- validates `content_plan.json`'s new optional `"shapes"` list before any slide materializes.
- `pptx_pipeline.py` -- add `add_card`/`add_metric_box`/`add_table`/`add_section_label` + `_add_shapes` dispatch -- the named shape API.
- `pptx_pipeline.py` -- wire `_resolve_shapes`/`_add_shapes` into `fill_template`'s existing resolve-then-materialize loop -- content_plan-driven shapes reach `herald deck pptx-fill` with zero new CLI surface.
- `errors.py` -- extend `InvalidContentPlanError`'s docstring -- documents the reused exception's expanded scope.
- `tests/test_pptx_pipeline.py` -- unit-test the I/O matrix above, including the Warden-appendix acceptance case -- proves the story's success criterion.

**Acceptance Criteria:**
- Given a `content_plan.json` with a `"shapes"` list on a slide entry, when `run_fill` is invoked, then the output `.pptx`'s slide XML contains real `<a:t>` text runs for every shape's text (no `<p:pic>` covering them), and every shape's fill/text color is a theme color reference (`<a:schemeClr>`), never a hardcoded hex value.
- Given the four real Warden-deck Appendix persona strings packed into four 2.15in x 3.0in card shapes on one slide, when `add_card` computes their autofit, then every card's `FittedText` (font size + line count), re-measured with the same Pillow font, keeps the text block height within the card's height.
- Given a shape entry with an unknown `"type"` or a missing required field for its type, when `run_fill` is invoked, then it raises `InvalidContentPlanError` and writes no output file.
- Given an existing Story 15.1-shaped content_plan (placeholders only, no `"shapes"` key), when this story's changes land, then `fill_template`'s behavior for it is unchanged.

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 0, low 9)
- defer: 0
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[low]` `[patch]` `_reset_margins` zeroed text-frame margins but not per-paragraph `space_before`/`space_after`/`line_spacing` on the card/metric-box two-paragraph shapes, so `fit_text`'s 1.2x-line-height height budget implicitly relied on theme-inherited spacing being zero rather than guaranteeing it. Fixed: paragraphs written via `_write_fitted_lines` now explicitly zero all three.
  - `[low]` `[patch]` `_resolve_table_rows`'s rejection branches (non-list `"rows"`, empty `"rows"`, non-rectangular rows, non-string cell) had zero test coverage through the actual validated `fill_template`/`run_fill` JSON path -- the one core validation boundary in this diff with no regression test. Fixed: added parametrized tests mirroring the existing `test_fill_template_non_positive_shape_geometry_raises` pattern.
  - `[low]` `[patch]` A shape entry missing the `"type"` key produced the identical error message as an entry with an unrecognized `"type"` value (`"unknown shape type None"`), confusing for an author who simply omitted the field. Fixed: distinct messages for missing vs. unrecognized.
  - `[low]` `[patch]` No regression test for `_resolve_shape_geometry`'s explicit `bool`-rejection branch, despite its own docstring calling it out as a deliberate discipline choice. Fixed: added a direct test.
  - `[low]` `[patch]` Only the `card` type's missing-required-field path was tested; `metric_box` (missing `value`/`label`) and `section_label` (missing `text`) had no equivalent test. Fixed: added the missing cases.
  - `[low]` `[patch]` No CLI-level test proved a malformed `"shapes"` entry exits 1 and writes nothing via `cli.main` -- only the shapes-bearing success path was CLI-tested. Fixed: added one, mirroring the existing placeholder-idx CLI error test.
  - `[low]` `[patch]` No test for `_resolve_one_shape` rejecting a non-mapping shape entry (bare string/number). Fixed: added a test.
  - `[low]` `[patch]` No test for `_table_font_size`'s fallback-to-`_MIN_PT` path when no candidate size fits every cell. Fixed: added a test.
  - `[low]` `[patch]` `add_table` did not set `text_frame.word_wrap = True` on its cells, inconsistent with `add_card`/`add_metric_box`/`add_section_label` (currently harmless since lines are pre-wrapped, but an inconsistency worth reconciling). Fixed: set it for consistency.

Rejected findings (independently verified, not merely disbelieved): `_wrap_words` collapsing embedded newlines/repeated whitespace via `text.split()` (correct word-wrap behavior for prose title/body/value/label/text fields -- not a bug, no consumer harmed); the direct Python API (`add_card`/`add_metric_box`/`add_table`/`add_section_label`/`fit_text`) not re-validating its own arguments (empty/ragged `rows`, non-string text, non-positive geometry, non-positive point sizes) -- a deliberate internal-trust boundary matching this codebase's existing pattern (`fill_template`'s pure functions don't re-validate what their only real caller, `_resolve_*`, already validated) and this project's "trust internal code, validate at system boundaries" principle; the content_plan.json JSON path is the actual untrusted boundary and is the one covered rigorously; `_table_font_size`'s sizing search not calling `_rebalance_orphan` before the render loop does, claimed to risk the two passes disagreeing on line count -- refuted by re-tracing `_rebalance_orphan`'s own code: every branch (no-op and merge) returns a list of the exact same length as its input, so total line count is a `_rebalance_orphan`-invariant and the sizing pass's line count is always still valid after the render pass's rebalancing; the Warden-appendix acceptance test hardcoding a transcription of the source deck's persona text with no automated tie-back assertion -- matches Story 15.1's own established, accepted precedent exactly (its round-trip test also hardcodes a transcription from a real deck file, cited by a comment, with no automated tie-back), not a gap introduced by this story.

### 2026-08-22 — Review pass (verification-repair session)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 1, low 6)
- defer: 0
- reject: 11: (high 0, medium 0, low 11)
- addressed_findings:
  - `[low]` `[patch]` `_add_shapes`'s dispatch fell through to `add_section_label` in a bare `else` for any unmatched `ResolvedShape`, so a future 5th shape variant would silently mis-render instead of failing loudly. Fixed: explicit `elif isinstance(shape, SectionLabelShape)` + `else: raise AssertionError(...)`.
  - `[low]` `[patch]` `InvalidContentPlanError`'s docstring enumerated three shape-validation failure modes but omitted two this diff actually added (`"shapes"` not a JSON array; a shape entry not a JSON object). Fixed: docstring now enumerates all five.
  - `[low]` `[patch]` `_write_fitted_lines`'s docstring claimed literal line breaks are used "never relying on" PowerPoint's re-flow, while every `add_*` function still sets `word_wrap = True` -- an absolute claim inconsistent with Design Notes' own "passive safety net only" framing. Fixed: softened the docstring to match.
  - `[medium]` `[patch]` `_reset_margins` (zeroing a text-frame's margins so `fit_text`'s EMU budget matches the shape's real usable area) was asserted by no test anywhere -- a regression dropping/mistyping one of its four assignments would ship a shape whose measured-to-fit text visually overflows in real PowerPoint with the whole suite green. Fixed: added `margin_left/right/top/bottom == 0` assertions to the `add_card`/`add_metric_box`/`add_section_label` tests and to `add_table`'s body-cell test.
  - `[low]` `[patch]` `add_card`/`add_metric_box`'s per-role styling (bold title vs. plain body; bold `ACCENT_1` value vs. plain `TEXT_1` label) was unchecked -- swapping the `bold`/`theme_color` arguments between either function's two `_write_fitted_lines` calls would still pass every existing test. Fixed: added precise per-run `bold`/`theme_color` assertions to both tests.
  - `[low]` `[patch]` The I/O matrix's "Missing required field" and "Non-positive geometry" rows both specify "no file written, exit 1," but (unlike the unknown-shape-type row) neither had a test proving the full CLI-level surface -- only that `fill_template` raises in-memory. Fixed: added `test_deck_pptx_fill_missing_required_field_exits_1_and_writes_nothing` and `test_deck_pptx_fill_non_positive_shape_geometry_exits_1_and_writes_nothing`, mirroring the existing unknown-shape-type CLI test.
  - `[low]` `[patch]` No test constructed a single slide entry with both a real `"placeholders"` mapping and a real `"shapes"` list, so the additive/coexistence claim in Boundaries & Constraints was untested in combination, only in isolation. Fixed: added `test_fill_template_placeholders_and_shapes_coexist_on_the_same_slide`.

Rejected findings (independently verified, not merely disbelieved): a repeat of the prior pass's already-rejected "direct Python API doesn't re-validate its own arguments" finding, now phrased as five separate direct-call edge cases (`add_table` with empty/zero-column/ragged rows, `fit_text` with `min_pt <= 0`) -- re-verified the premise still holds: `_resolve_table_rows` rejects empty/ragged/non-string rows and `_resolve_shape_geometry` rejects non-positive width/height before any `add_*` call, and `min_pt` is never externally controlled (every call site passes the internal `_MIN_PT = 6` constant), so the content_plan.json boundary remains the only reachable path and it is validated rigorously; a repeat of the prior pass's already-rejected `_table_font_size`/render-loop two-pass-agreement finding -- premise re-checked against the unchanged code, still refuted by the same `_rebalance_orphan` length-invariant; `_resolve_shape_geometry` not bound-checking a shape's position against the slide's actual dimensions -- Boundaries & Constraints explicitly enumerates what to validate ("type, required fields, positive geometry"), and in-bounds placement is conspicuously absent from that list, the same intent-authored scope line as the "no general-purpose drawing library" Never-rule; no user-facing docs/CHANGELOG for the new `"shapes"` schema -- not in the Code Map or Tasks & Acceptance, which enumerate every file this story touches; `spec-pptx-custom-shapes/SPEC.md` still `status: ready` with no memlog entry for this implementation -- checked the sibling `spec-pptx-deck-generation/SPEC.md` (Story 15.1's own capability spec): identical `status: ready`, `surface: []`, no post-implementation memlog entry, confirming this is the project's established convention for Dream-derived capability specs (completion tracked at the story level, not the capability-spec level), not a gap this story introduced; the Warden-appendix acceptance test not laying out all four cards on one slide via a real content_plan.json -- the matrix row's literal expected behavior only requires each card's independently-measured fit to stay within its own height, which four isolated `add_card` calls fully prove; the same test's re-measurement using `fit_text`'s own formula rather than an independent method -- proves the write matches the decision (the actual risk surface), and an independently-implemented measurement path is disproportionate for this feature; reliance on Pillow's bundled Aileron font requiring FreeType support -- conda-forge's `pillow` package always ships with FreeType compiled in, so this is not a reachable risk in this repo's pinned environment; this diff bundling an unrelated `pyforge-marshal` spec-surface reconciliation alongside the Herald 15.2 work -- necessary to clear a repo-wide verification gate blocking every in-flight story (documented in both specs' memlogs), and an independent concurrent session hit and fixed the identical drift the same way, confirming this is expected cross-station maintenance, not scope creep; no test for a shape's geometry overlapping an existing named template placeholder -- z-order/visual-overlap avoidance is a content-plan-authoring responsibility for any absolute-positioning API, not a validation Boundaries & Constraints calls for; `_require_str_field` accepting an empty string as a valid title/body/value/label/text -- checked `_resolve_placeholder_values` (Story 15.1): it has the identical non-strictness (any `str`, including empty, is accepted), so this matches established precedent rather than introducing a new gap.

### 2026-08-22 — Review pass (follow-up review)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 3, low 6)
- defer: 0
- reject: 15: (high 0, medium 0, low 15)
- addressed_findings:
  - `[medium]` `[patch]` `fit_text`'s accept predicate was **height-only** (`len(lines) * pt * 1.2 <= height_budget`), but `_wrap_words` deliberately leaves a word wider than the box alone on its own line -- so a single unbreakable token (a long metric value, URL, or hash) cleared the height budget at near-maximum size while running straight past the shape's right edge. Verified live before the fix: `fit_text("1,247,392", width_emu=300_000, height_emu=300_000, max_pt=54, min_pt=6)` returned **17pt measuring 78.0pt of width in a 23.6pt box** -- a 3.3x horizontal overflow reported as a fit, in the one story whose title is "shapes that fit". Fixed: extracted `_wrapped_fits`, which requires the wrapped lines to clear BOTH the width and height budgets; the best-effort `min_pt` fallback (I/O matrix "Extreme overflow") is untouched. Same predicate now also governs `_table_font_size`, which shares `_wrapped_fits`.
  - `[medium]` `[patch]` The `_FIT_SAFETY` cushion was applied to the height budget only -- `width_pt = width_emu / 12700` was raw -- while card titles, metric values, and table headers are written `bold=True` yet measured with Pillow's regular Aileron face, which is narrower. A measured-to-fit bold line therefore had zero horizontal cushion against both boldness and PowerPoint's font substitution. Independently corroborated: an intent-alignment audit rendered the Warden acceptance fixture through `soffice` and observed the renderer re-wrapping the measured breaks (card 1's 4-line body rendering as 6). Fixed: the same 10% cushion now applies to the width axis in both `fit_text` and `_table_font_size`, and `add_table`'s render loop uses the identical cushioned budget its sizing pass measured against (it previously wrapped at the raw width).
  - `[medium]` `[patch]` A card's title could render **smaller than its own body**, inverting the visual hierarchy on exactly the long titles the Warden persona case is built from: the title search is capped at 45% of card height while the body was capped only by `_CARD_BODY_MAX_PT`, with nothing enforcing `title >= body`. Verified live before the fix: `add_card(slide, 0, 0, 2_000_000, 1_500_000, "A Title Here That Is Long Enough To Wrap Nicely", "short body")` produced a **13pt bold title over a 14pt body**. `add_metric_box` had the same unguarded shape (a 9pt value under a 14pt label at 600_000 x 900_000 EMU). Fixed: the body/label search ceiling is now clamped to the size the title/value settled on.
  - `[low]` `[patch]` A shape's paragraphs disagreed on alignment: python-pptx's autoshape template ships `algn="ctr"` on paragraph 0 while the body/label paragraph added after it carries no `algn` and inherits the theme default -- verified live as `title algn: CENTER | body algn: None`, i.e. a centred title over a left-aligned body. The module already pins margins and paragraph spacing rather than inheriting them, so alignment was an inconsistent omission. Fixed: `_write_fitted_lines` takes a required `alignment` and pins it (LEFT for card/table/section-label, CENTER for metric box).
  - `[low]` `[patch]` `_write_fitted_lines`'s `space_before`/`space_after`/`line_spacing` pins -- the reason `fit_text`'s 1.2x height budget is true on the rendered slide at all -- were asserted by no test anywhere; deleting all three left the whole suite green, while the sibling defense with the identical rationale (`_reset_margins`) is asserted in four tests. Fixed: added `test_every_written_paragraph_pins_spacing_and_alignment`, covering all four shape types.
  - `[low]` `[patch]` The table header's readability is a *contrast pair* (BACKGROUND_1 text on an ACCENT_1 fill), but the only colour-shaped assertion was `"schemeClr" in header_cell._tc.xml` -- which matches for any theme colour, because the run's own `rPr/solidFill` already puts that substring in the cell XML. Collapsing every row to `TEXT_1` *and* deleting the header fill entirely left the suite green. Fixed: the header test now asserts `theme_color` by identity on the header run, the body run, and `header_cell.fill.fore_color`.
  - `[low]` `[patch]` `add_table`'s own `cell_height_emu = height / num_rows` row-budget derivation was untested -- changing it to `= height` left the suite green, while on a realistic 5x3 table it swings the chosen size from 12pt to 18pt (a 43.2pt text block in a 31.5pt row). The one table-sizing test bypasses `add_table` and calls `_table_font_size` with hand-passed budgets. Fixed: added `test_add_table_shrinks_to_its_own_per_row_height_budget`, asserting every cell's block against both the row budget and the width budget.
  - `[low]` `[patch]` `add_metric_box`'s adaptive split had no direct fit assertion (the card has one) -- it was protected only incidentally, by literal text-substring assertions that stop matching once the label re-wraps. `add_section_label`'s `bold=True` was likewise unasserted. Fixed: added `test_add_metric_box_label_fits_the_height_left_by_its_value` and a bold assertion to the section-label test.
  - `[low]` `[patch]` Both `pptx_pipeline.py`'s module docstring and `InvalidContentPlanError`'s docstring cited this work as "Story 15.2, CAP-2, spec-pptx-custom-shapes". Verified against the spec: in `spec-pptx-custom-shapes` this is **CAP-1**; CAP-2 is `spec-pptx-deck-generation`'s forwarding pointer *to* it, so a reader following the citation into the named spec finds no CAP-2. Fixed: both now read `spec-pptx-custom-shapes CAP-1`.

Each new or amended assertion was mutation-tested: seven independent mutations (drop the width predicate, drop the alignment pin, drop the three spacing pins, drop the card body clamp, drop the metric label clamp, retarget the table row budget to the whole table height, collapse the header text colour) were each applied to the source and the suite re-run -- all seven now fail at least one test, where six of the seven left the pre-patch suite fully green. The first metric-box clamp fixture did NOT catch its mutation and was replaced with one that does (600_000 x 900_000 EMU, which renders a 9pt value under a 14pt label unclamped).

Rejected findings (independently verified, not merely disbelieved): the direct Python API (`add_card`/`add_table`/`fit_text`) not re-validating its own arguments -- third repetition across three passes, premise re-checked and still holding, the content_plan.json boundary remains the only reachable path and is validated; shape geometry not bound-checked against the slide canvas, and no EMU-ceiling check -- Boundaries & Constraints enumerates exactly "type, required fields, positive geometry", and in-bounds placement is conspicuously absent from that list (intent is the only admissible scope authority here, and it excludes this); `FittedText` carrying no `fits: bool` so a best-effort floor render is indistinguishable from a genuine fit -- the I/O matrix's "Extreme overflow" row explicitly specifies "renders at the minimum size anyway... No error, no crash", so intent settles it (the downstream `audit_overflow` gate that wants this classification lives in `spec-deck-visual-qa`, a different contract); `spec.json`/`TemplateSpec` not extended with the `"shapes"` vocabulary, and no README/CHANGELOG/`docs/cli-runbooks.md` entry -- repeat of a prior-pass rejection, neither is in the Code Map or Tasks & Acceptance; `cli.py`'s `pptx-fill` help text still citing "Story 15.1, CAP-1" -- same rejection, `cli.py` is not a file this story's Code Map touches; `spec-pptx-custom-shapes/SPEC.md` still `status: ready` with no memlog entry -- re-verified the prior pass's finding that the sibling `spec-pptx-deck-generation` (for shipped Story 15.1) is identically `status: ready` with `surface: []`, confirming project convention, not a gap; `_wrap_words` collapsing embedded `\n` via `str.split()` -- repeat of a prior-pass rejection, correct prose word-wrap for these fields; CJK/Cyrillic/emoji mis-measurement against Aileron's `.notdef` metrics -- no non-Latin deck content exists in this repo and none is in scope; `_require_str_field` accepting an empty string -- repeat, matches `_resolve_placeholder_values`'s identical non-strictness; the bundled marshal memlog entry's first-person voice and its coupling of marshal's baseline stamp to herald's branch -- the bundling itself was verified as necessary cross-station gate maintenance in the prior pass, and two reviewers independently re-verified the stamp this pass (all five sha1 entries reproduce, exactly one marshal commit in range); `ruff format` drift in the two changed files -- verified NOT gated anywhere in this repo (no `.pre-commit-config.yaml`, no pixi task, no CI workflow runs it, and `ruff check` already reports 59 pre-existing errors package-wide), so this is cosmetic; the Warden fixture's `...2026-07-15.md:413-419` citation being "stale" against the personas at 415-418 -- 413-419 encloses the whole Appendix block including its `## Appendix` heading, a deliberate superset, not a wrong pointer; `_add_shapes`'s `else: raise AssertionError` being untested and escaping `dispatch`'s `HeraldError`-only catch -- that branch was deliberately added by the immediately-prior review pass as a loud-failure guard and is unreachable by construction; missing `match=` assertions on error messages, no test for `"shapes": []`, and no second-slide/second-shape index test -- index formatting is exercised by the six existing validation tests and no consumer depends on the message text; `pyproject.toml`'s per-story dependency rationale not recording that `pptx_pipeline.py` now imports `PIL.ImageFont` -- `pyproject.toml` is not in this story's Code Map and the existing `pillow>=12.3.0` floor already satisfies the `load_default(size=...)` requirement; the acceptance test placing four cards at the same origin rather than packed across a real slide -- repeat of a prior-pass rejection on the matrix row's literal wording (per-card fit), and a real four-across render was performed manually this pass instead (screenshot inspected, see Auto Run Result).

## Design Notes

**Font measurement source.** `PIL.ImageFont.load_default(size=N)` (Pillow >=10.1) returns a `FreeTypeFont` backed by Pillow's own bundled Aileron font -- real glyph metrics, not a bitmap stub. Pillow is already a direct `pyforge-herald` dependency (Story 14.2, contact-sheet compositing), so this needs no new dependency and no font-file-path resolution that could differ between an installed wheel and a conda package.

**Unit conversion + safety margin.** Box geometry arrives in EMU; `pptx.util.Pt(1) == 12700` EMU gives the EMU->pt conversion. Pillow's font `size` is treated 1:1 with points (a standard 72dpi raster approximation). The fit search targets 90% of the box's converted height, absorbing the gap between Aileron's metrics and whatever font PowerPoint substitutes at open-time:

```python
def fit_text(text, width_emu, height_emu, *, max_pt, min_pt) -> FittedText:
    width_pt = width_emu / 12700
    height_budget_pt = (height_emu / 12700) * 0.9
    for pt in range(max_pt, min_pt - 1, -1):
        lines = _rebalance_orphan(_wrap_words(text, pt, width_pt), pt, width_pt)
        if len(lines) * pt * 1.2 <= height_budget_pt:
            return FittedText(pt, tuple(lines))
    return FittedText(min_pt, tuple(_rebalance_orphan(_wrap_words(text, min_pt, width_pt), min_pt, width_pt)))
```

**Literal line breaks, not `word_wrap` reliance.** `fit_text` returns the literal wrapped lines. Each is materialized as its own run inside one paragraph, joined by `paragraph.add_line_break()` -- deliberately not relying on PowerPoint's own re-flow at open-time, since a substituted font could re-wrap our measured breaks differently. `word_wrap = True` stays set as a passive safety net only.

**Orphan rebalancing.** When the last computed line is a single word and the prior line has more than one, pull that prior line's last word down onto the orphaned line -- only when the merge still fits the width. Deterministic, directly unit-tested.

**Card / metric-box adaptive split.** The title (card) / value (metric box) gets a height-budget *cap* -- 45% of the shape height for a card title, 75% for a metric value -- so it can never starve the body/label of space, but only consumes what it actually needs below that cap; the remainder goes to the body/label's own `fit_text` call.

**Table: one global size.** All cells share one font size: the largest size at which every cell's own column-width/row-height budget (`width / num_cols`, `height / num_rows`) fits, found by the same descending search. Row 0 is always the header (bold, `ACCENT_1` fill) when more than one row is given. Keeps the table visually consistent instead of a per-cell size jumble.

**Theme-relative color only.** `MSO_THEME_COLOR.ACCENT_1`/`BACKGROUND_1`/`BACKGROUND_2`/`TEXT_1` throughout, never a hardcoded RGB -- holds even if a future PyForge-branded template replaces the interim default (Story 15.1's own template-genericity principle, extended to color).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Open the Warden-appendix acceptance output in real PowerPoint at least once during review and confirm every persona card's text is visible with no visual overflow or clipping -- the Pillow-based measurement is a strong proxy but not a substitute for the real target application (mirrors Story 15.1's own documented caveat).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `7a698babbb` (2026-09-11, "pyforge-mason Story 15.2: advance brief_mirrored_through to 90537c2391"); also `ea75f98fb1` (2026-09-11, "pyforge-mason Story 15.2: append review triage log and finalize spec"); also `4a69168555` (2026-09-11, "pyforge-mason Story 15.2: advance brief_mirrored_through to 2fca30c6b0"). Ledger row `15-2-dense-content-renders-as-shapes-that-fit: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
