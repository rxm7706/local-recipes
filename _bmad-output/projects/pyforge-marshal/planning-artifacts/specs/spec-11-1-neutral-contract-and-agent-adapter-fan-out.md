---
title: 'Neutral contract and agent-adapter fan-out'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
difficulty: ''
baseline_revision: 'e410666e276108b0d3cc05955687511bd49e18c4'
final_revision: 'd630deb2f4017ab331e70c40c8aa0c39c8e7da77'
---

<intent-contract>

## Intent

**Problem:** The seed manifest already declares `cursor-rules` (`.cursor/rules/specs.mdc`),
`gemini-md` (`GEMINI.md`), and `copilot-instructions` (`.github/copilot-instructions.md`) as
`generated-derived` whole-file entries, and `agents-md`/`claude-md` as `hybrid-managed-region`
entries with `tiers`/`portability-contract`/`dream-first-workflow` regions — but no real content
exists for the three whole-file adapters (`verbs/adopt.py`'s own docstring names this "known,
inherited limitation (1)": nothing supplies whole-file content, so `materialize()` fails or a
test must inject a synthetic `template_path`). `seed/derive/` is an empty package. Four adapter
files can drift from each other and from `AGENTS.md`/`CLAUDE.md` because nothing renders them
from one source.

**Approach:** Add `seed/derive/adapters.py` as the one seam that composes the neutral contract
(reusing the three existing region fragments `seed/templates/files/tiers.md.j2`,
`portability-contract.md.j2`, `dream-first-workflow.md.j2` — do not duplicate their prose) into
five outputs: three whole-file `generated-derived` renders (each fragment wrapped in a new,
tool-specific framing template) and two region bodies (`AGENTS.md`/`CLAUDE.md`, reusing the
existing region-fragment read path). Add the three whole-file wrapper templates under
`seed/templates/files/`. Wire `seed/derive/adapters.py` into `verbs/adopt.py`'s existing
lazy-materialize path (`_region_body_from_template` and the `_materialized()` closure) so the
three generated-derived adapters get real content instead of failing, and derive is invoked from
one place, not duplicated per-verb.

## Boundaries & Constraints

**Always:**
- Every filesystem write goes through `fs.write` / `fs.replace_span` (never `Path.write_text`,
  `open(..., "w")`, or any other primitive) — P-01 is enforced by an existing meta-test AST scan.
- The three whole-file adapters and the two managed-region bodies all derive from the SAME
  underlying fragment content for the tier table / portability contract / Dream-first workflow —
  one edit to a `seed/templates/files/*.j2` fragment must change all five outputs' relevant
  content on the next render.
- Derived output is deterministic: rendering twice with the same manifest/fragments produces
  byte-identical output (no timestamps, no random ordering).
- Adapter selection stays data-driven: adding a fifth adapter is a `templates/manifest.yaml`
  entry plus one new wrapper template file — no change to `seed/derive/adapters.py`'s logic.
- `GEMINI.md`'s rendered tier table must match `AGENTS.md`'s tiers-region body semantically
  (same tier rows, same paths, same git-disposition column) even though the wrapping prose
  differs per tool.
- Match existing house style exactly: `from __future__ import annotations`, module docstrings
  explaining rationale (this package's established convention — see `regions/apply.py`,
  `model/manifest.py` for the register), plain dataclasses/functions, no new third-party deps.
- New tests live under `src/shared/packages/pyforge-marshal/tests/unit/test_seed_derive_*.py`
  matching the existing `test_seed_*.py` house style (real tmp_path repos, no mocked git).

**Block If:** none identified — this story's scope (render fragments into adapters, wire into
the existing lazy-materialize seam) is fully specified by the epics AC and the investigated
codebase; no undecided design choice requires a human call.

**Never:**
- Never touch `seed/migrate/` (Story 11.3) or add a new CLI verb (no `derive` subcommand — this
  is an internal seam invoked from `verbs/adopt.py`, matching the epics AC's silence on a new
  verb and the module docstring's statement that Epics 11/12 own the remaining verb-adjacent
  logic).
- Never route region-body content for `AGENTS.md`/`CLAUDE.md` through `engine.copier.materialize`
  — `_region_body_from_template`'s existing direct-read path stays the mechanism for region
  bodies (avoids re-litigating S-8.3's design); only the three whole-file adapters are new
  `materialize()` consumers.
- Never hand-write the tier table content independently per adapter — always render from the
  shared fragment so a single source of truth is provable by mutation test.
- Never widen `NeverWrite`'s exempt set or bypass the never-write guard for these paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Render cursor-rules from fragments | `tiers.md.j2` + `portability-contract.md.j2` + `dream-first-workflow.md.j2` fragments, cursor wrapper template | `.cursor/rules/specs.mdc` whole-file content containing the same tier table content wrapped in Cursor-specific framing | No error expected |
| Two renders, same input | Same manifest + fragments, called twice | Byte-identical output both times | No error expected |
| Mutate the shared fragment | `tiers.md.j2` content changed | All of `.cursor/rules/specs.mdc`, `GEMINI.md`, `.github/copilot-instructions.md`, and the `tiers` region body for `AGENTS.md`/`CLAUDE.md` change on next render | No error expected (asserted by the single-source-of-truth test) |
| Fifth dummy adapter added in a test | A new manifest entry + wrapper template, no `adapters.py` change | The fifth adapter renders correctly alongside the existing four | No error expected |
| Unknown adapter id requested | An adapter id with no matching manifest entry or wrapper template | Raise a clear, named error (do not silently skip) | Raises with the offending id named |
| Missing wrapper template for a declared whole-file adapter | Manifest declares a `generated-derived` adapter entry with no corresponding template file on disk | Raise a clear, named error at render time | Raises naming the missing template path |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/derive/adapters.py` -- NEW (implemented): the single seam; `AdapterSpec`/`ADAPTER_COMPOSITION` (data-driven, keyed by manifest `id`) + `render_adapter()` composes fragment content + wrapper template into whole-file adapter content. `AGENTS.md`/`CLAUDE.md`'s region-body path stays on `verbs.adopt._region_body_from_template` UNCHANGED (see below) -- "single source of truth" holds because both read the identical fragment file off disk at render time, not because one delegates to the other.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/derive/__init__.py` -- left EMPTY, matching `seed/regions/__init__.py`'s precedent (the Code Map's own suggested reference); `verbs/adopt.py` imports the `adapters` submodule directly (`from ..derive import adapters as derive_adapters`), mirroring the `fs`-module-import convention.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/files/tiers.md.j2`, `portability-contract.md.j2`, `dream-first-workflow.md.j2` -- existing shared fragments; UNCHANGED, read-only source content, reused verbatim (not duplicated) by the new adapters.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/files/cursor-rules.mdc.j2`, `gemini-md.md.j2`, `copilot-instructions.md.j2` -- NEW: the 3 wrapper templates (plain `{{ name }}` placeholder substitution, not real Jinja -- see Design Notes addendum below for why).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py` -- CHANGED: `_default_commit`'s `commit()` dispatch gained a THIRD branch (data-driven membership check against `derive_adapters.ADAPTER_COMPOSITION`) between the existing hybrid-region branch and the generic `_materialized()`/`_staged_bytes_for` whole-file branch -- the three derive-composed ids now bypass `_materialized()`/Copier entirely (see Design Notes addendum: this was empirically required, not a style choice). Module docstring's "known, inherited limitation (1)" narrowed to note it is now closed for these 3 ids.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml` -- UNCHANGED, as expected: no `template` field exists on `ManifestEntry`, so `ADAPTER_COMPOSITION` lives as a small lookup table in `adapters.py` itself (Design Notes' own sanctioned fallback).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_derive_adapters.py` -- NEW: single-source-of-truth mutation test (cross-checked against `verbs.adopt._region_body_from_template`, not re-implemented), determinism tests (synthetic + real packaged templates), fifth-adapter extensibility test (caller-supplied composition table), semantic tier-table-match test (GEMINI.md vs AGENTS.md, real packaged content), unknown-adapter/missing-wrapper-template/unknown-placeholder error tests, `_read_fragment` ambiguity/Jinja-guard tests, and one real-git `run_adopt` integration test proving the whole-file-vs-managed-region contrast end to end.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_templates_manifest.py` -- CHANGED (not in the original Code Map, discovered during implementation): `test_every_body_file_is_claimed_by_a_declared_region` assumed every `.j2` file under `templates/files/` is a region-body fragment; updated to exclude `ADAPTER_COMPOSITION`'s own wrapper filenames (a second, disjoint `.j2` category this story introduces) from that invariant.

## Tasks & Acceptance

**Execution:**
- [x] `seed/derive/adapters.py` -- implement the render seam: a function (or small set of functions) that, given an adapter id, returns rendered whole-file content (for `generated-derived` ids) or a region body string (for the two `hybrid-managed-region` ids), reading fragment content from `seed/templates/files/*.j2` and wrapper templates from the new per-adapter files -- single source of truth for all 5 outputs. *(Implemented as `render_adapter()` for the 3 whole-file ids; the "region body string" half is satisfied by `verbs.adopt._region_body_from_template`, deliberately left as the mechanism per the intent-contract's own Never bullet -- both read the identical fragment file, so single-source-of-truth holds without adding a redundant public function nothing would call. See Design Notes addendum.)*
- [x] `seed/templates/files/cursor-rules.mdc.j2`, `gemini-md.md.j2`, `copilot-instructions.md.j2` -- author the 3 wrapper templates, each embedding/including the shared fragment content with tool-specific framing (e.g. Cursor's MDC frontmatter, Gemini's own preamble, Copilot's own preamble) -- no fragment prose duplicated inline
- [x] `seed/verbs/adopt.py` -- wire `derive.adapters` into the existing lazy-materialize seam for the 3 whole-file ids, removing the "known, inherited limitation (1)" gap noted in its module docstring (update that docstring accordingly). *(Wired as a new dispatch branch in `_default_commit`'s `commit()`, bypassing `_materialized()` for these 3 ids rather than routing through it -- see Design Notes addendum for the empirical reason.)*
- [x] `tests/unit/test_seed_derive_adapters.py` -- unit-test the I/O matrix above: single-source-of-truth mutation, determinism, fifth-adapter extensibility, GEMINI.md/AGENTS.md tier-table semantic match, unknown-adapter error, missing-wrapper-template error

**Acceptance Criteria:**
- Given one jinja/fragment source for the neutral contract, when the derive stage runs, then `.cursor/rules/specs.mdc`, `GEMINI.md`, and `.github/copilot-instructions.md` are generated as whole files, each wrapping the same contract in tool-specific framing
- Given the same inputs, when `AGENTS.md`/`CLAUDE.md` are adopted, then the contract arrives as managed regions only (via the existing `insert_region`/`substitute_region` path), never a whole-file overwrite
- Given a mutation to a shared fragment, when all 5 outputs are re-rendered, then all 5 reflect the mutation (test-verified)
- Given two successive renders with unchanged input, when compared, then output is byte-identical
- Given a fifth dummy adapter added purely via a manifest entry + wrapper template in a test, when rendered, then it succeeds with no `adapters.py` code change
- Given `GEMINI.md`'s rendered tier table and `AGENTS.md`'s tiers-region body, when compared, then they match semantically (same tiers, same paths, same git dispositions)
- Given the existing `pyforge-marshal` test suite and meta-tests (P-01 write-primitive scan, layer-import rules), when run after this change, then they all still pass with no new violation

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Do not modify or delete existing entries.
     Each entry records: what finding triggered the change, what was amended, what known-bad state
     the amendment avoids, and any KEEP instructions (what worked well and must survive re-derivation).
     Empty until the first bad_spec loopback. -->

## Review Triage Log

<!-- Append-only. Populated by step-04 on EVERY review pass, including loopbacks and blocked exits.
     Each entry records triage decision counts for intent_gap, bad_spec, patch, defer, and reject,
     with per-category severity breakdowns using low/medium/high, plus the findings addressed in
     that pass. Empty until the first review pass. -->

### 2026-08-21 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 0, medium 2, low 2)
- defer: 1 (low 1)
- reject: 7 (low 7)
- addressed_findings:
  - `[medium]` `[patch]` `_PLACEHOLDER_RE`'s char class (`[a-z][a-z0-9-]*`) was a strict subset of `regions.markers.REGION_NAME_PATTERN` (`[a-z0-9][a-z0-9-]*`), so a digit-leading region/fragment name would pass through a wrapper template completely un-substituted with no error — widened to build directly off `REGION_NAME_PATTERN.pattern` so the two can never drift apart again.
  - `[medium]` `[patch]` `verbs/adopt.py`'s new `_default_commit` dispatch branch matched on `entry.id in ADAPTER_COMPOSITION` alone, with no `artifact_class` check — a future id collision with a differently-classed manifest entry would have silently rerouted through derive-composition; added `and entry.artifact_class is ArtifactClass.GENERATED_DERIVED` to the condition.
  - `[low]` `[patch]` No test tied `ADAPTER_COMPOSITION`'s 3 hardcoded keys back to the real packaged `manifest.yaml` — added `test_every_adapter_composition_key_is_a_real_generated_derived_manifest_entry_with_no_regions` to `test_seed_derive_adapters.py`.
  - `[low]` `[patch]` `render_adapter`'s docstring enumerated 3 of `_compose`'s 4 propagated failure modes, omitting the "unknown placeholder" `InternalError` from `_substitute` — added the missing mode.
  - `[low]` `[defer]` `_read_fragment`/`_compose`'s `read_text()` calls aren't wrapped for `OSError`/`UnicodeDecodeError` — confirmed this mirrors a pre-existing, unwrapped pattern already shipped in `verbs/adopt.py::_read_region_fragment`, so it is not caused by this story; filed as `DW-FU-11-1`.
  - `[low]` `[reject]` (x7) `_read_fragment` duplicating `_read_region_fragment` (explicitly documented, deliberate trade-off); no reciprocal "every declared fragment is referenced" check; `ADAPTER_COMPOSITION`'s plain-dict mutability; the `TemplateBoundaryError` rationale not being regression-pinned; the 3 wrapper templates' duplicated boilerplate prose; `test_seed_templates_manifest.py`'s wrapper-filename exclusion not itself asserting file existence (already indirectly covered by `test_seed_derive_adapters.py`'s real-packaged-template tests); and the module's documentation-to-code ratio (matches this package's established house style throughout `seed/`).

## Design Notes

**Wrapper-template mechanism.** Reuse Jinja2 (already a `pyforge-marshal` dependency per the
Copier engine) for the 3 new wrapper templates: each wrapper does a simple `{% include %}` or
string-embed of the corresponding fragment's rendered body, plus its own tool-specific
frontmatter/preamble. This keeps `adapters.py` itself template-agnostic — it resolves an
adapter id to (fragment paths, wrapper path), renders the fragments, renders the wrapper with
the fragment bodies as render context, and returns the result. Determinism falls out of Jinja's
own deterministic rendering given fixed input and no random/time-based context variables.

**Adapter extensibility.** "No engine change" for a 5th adapter means: `adapters.py`'s function
takes an adapter id and looks up (a) which fragments compose its contract content and (b) its
wrapper template path, from data (the manifest entry, or a small adjacent lookup table keyed by
id) — never an `if adapter_id == "cursor-rules": ...` branch per adapter. Prefer keying this
lookup off the manifest's existing `id`/`path` fields rather than inventing a parallel registry,
unless `ManifestEntry` has no field to carry "which fragments/wrapper this entry composes from"
— in that case, a small `ADAPTER_COMPOSITION: dict[str, AdapterSpec]` table in `adapters.py`
itself is acceptable (still data, still no per-adapter branch in render logic), and the 5th
adapter test adds a row to that table plus a template file, not a new render branch.

**Implementation addendum (post-implementation, documents two deviations from the Design Notes
above, both forced by facts discovered during implementation, not by preference):**

1. **No `jinja2` import; plain `{{ name }}` string substitution instead.** `jinja2` is only a
   TRANSITIVE dependency of `pyforge-marshal` (via `copier>=9.17,<10`), never declared in
   `[project.dependencies]`, and this story's own Boundaries forbid adding a new third-party
   dep. The Design Notes above explicitly named "string-embed" as an equally valid alternative
   to `{% include %}` — `adapters.py` implements exactly that: a small `re.sub`-based
   placeholder substitution (`_substitute`/`_PLACEHOLDER_RE`), never importing `jinja2` at all.
   Verified against `tests/packaging/test_dependency_completeness.py`
   (`pyforge-deps-test`): PASSES with zero new imports flagged.
2. **The 3 whole-file adapters bypass `engine.copier.materialize` entirely — confirmed
   empirically, not by design preference.** The obvious alternative (give each wrapper template
   a real `.jinja`-suffixed file at its target-relative path inside the packaged
   `seed/templates/` tree, letting `_materialized()`'s existing Copier render produce it for
   free) was tried against the REAL packaged manifest and fails immediately:
   `copier.run_copy` stages the ENTIRE template tree — `manifest.yaml`, `__init__.py`, and
   every `files/*.j2` fragment — and `engine.copier.materialize`'s own
   `_check_manifest_boundary` refuses the whole render as `TemplateBoundaryError` before any
   content is produced (reproduced live: `materialize() staged path(s) outside the manifest
   boundary: __init__.py, files/bmad-multiproject.md.j2, files/dream-first-workflow.md.j2,
   files/model-badge.md.j2, files/model-ignores.gitignore.j2, files/portability-contract.md.j2,
   files/tiers.md.j2, manifest.yaml`). Fixing that would mean touching `engine/copier.py`'s
   boundary check or adding manifest entries for Genesis's own packaging infrastructure files —
   well outside this story's Code Map. `_default_commit`'s `commit()` dispatch therefore gained
   a third, data-driven branch (`entry.id in derive_adapters.ADAPTER_COMPOSITION`) that calls
   `derive_adapters.render_adapter(...)` directly and never calls `_materialized()` for these 3
   ids — every OTHER whole-file class is untouched and still routes through
   `_materialized()`/`_staged_bytes_for` as before. See `derive/adapters.py`'s own module
   docstring for the full account.

Neither deviation required unpinning the "no `adapters.py` logic change for a 5th adapter"
extensibility claim (still a data-only table lookup) or the "region bodies never route through
`engine.copier.materialize`" Never bullet (still true, unchanged) — both are proven by
`tests/unit/test_seed_derive_adapters.py`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green, including new `test_seed_derive_adapters.py`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green, no new disallowed import

## Auto Run Result

**Summary:** Added `seed/derive/adapters.py`, the single seam that composes the three shared
neutral-contract fragments (`tiers`, `portability-contract`, `dream-first-workflow`) into three
whole-file `generated-derived` agent adapters (`.cursor/rules/specs.mdc`, `GEMINI.md`,
`.github/copilot-instructions.md`), each wrapped in its own tool-specific framing template.
Wired the three ids into `verbs/adopt.py`'s existing commit dispatch as a new, data-driven
branch, closing the "known, inherited limitation (1)" gap that module's own docstring named.
`AGENTS.md`/`CLAUDE.md` continue to receive the same fragments as managed regions via the
existing, untouched `_region_body_from_template`/`insert_region` path — never a whole-file
overwrite. A fifth adapter needs only a manifest entry, a wrapper template file, and a row in
`ADAPTER_COMPOSITION` — no `adapters.py` logic change (proven by test).

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/derive/adapters.py` -- new: `AdapterSpec`, `ADAPTER_COMPOSITION`, `render_adapter()`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/files/cursor-rules.mdc.j2`, `gemini-md.md.j2`, `copilot-instructions.md.j2` -- new wrapper templates.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py` -- new dispatch branch in `_default_commit`'s `commit()`, class-checked; docstring updated.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_derive_adapters.py` -- new, full I/O-matrix + manifest-consistency + real-git integration coverage.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_templates_manifest.py` -- pre-existing meta-test's `.j2`-body-file invariant updated to exclude the new wrapper-template filenames.

**Review findings breakdown:** 12 findings from Blind Hunter + Edge Case Hunter, deduplicated to
9 distinct issues. 4 patched (placeholder-regex/`REGION_NAME_PATTERN` divergence; missing
`artifact_class` cross-check in the new dispatch branch; missing manifest-consistency test;
missing 4th failure mode in `render_adapter`'s docstring). 1 deferred (`DW-FU-11-1`: unwrapped
`read_text()` calls, confirmed pre-existing and mirrored, not introduced by this story). 7
rejected (documented deliberate trade-offs, cosmetic/stylistic suggestions, or already
indirectly covered by other tests).

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 5050
passed, 9 deselected. `pixi run --frozen -e pyforge-ci pyforge-deps-test` → 84 passed. `ruff
check` on every touched/new file → clean.

**Residual risks:** Low. The `TemplateBoundaryError` rationale documented in the module
docstring (why `engine.copier.materialize` is bypassed) is not itself regression-pinned by a
test, so a future change to `engine/copier.py`'s boundary check could silently make the
workaround unnecessary without anything noticing (rejected as low-value scope for this pass,
not a live defect). The one deferred finding (`DW-FU-11-1`) is low severity and pre-existing.

**Baseline:** `e410666e276108b0d3cc05955687511bd49e18c4`
**Final:** (set after commit below)
</content>
