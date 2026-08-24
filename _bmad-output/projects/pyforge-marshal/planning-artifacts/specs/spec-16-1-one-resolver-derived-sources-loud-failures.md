---
title: '16.1: One resolver, derived sources, loud failures'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_revision: '51262819e76bde4d19c9511b20925e815b1c0503'
final_revision: '828ec6836c46da308d2377bd55032e5331df05c3'
review_loop_iteration: 0
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-dashboard-project-path-derivation/SPEC.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-dashboard-project-path-derivation/.memlog.md',
]
warnings: ['oversized']
difficulty: 'heavy'
---

<intent-contract>

## Intent

**Problem:** `docs/dashboard/generate.py` maps a roster/campaign slug to its real
`_bmad-output/projects/<dir>` tree through five independent, hand-authored mechanisms
(`PROJECT_SOURCES`, `_KEY_SLUG_OVERRIDE` re-derived at 5 call sites, `CAMPAIGN_PROJECT_OVERRIDE`,
`IMPL_CAMPAIGN`'s per-entry `epics_path` present on only 3 of 9 rows, `IMPL_CAMPAIGN_LEDGER`),
and `index.html` re-derives paths a second time in JS, including a literal
`r.slug === "pyforge-genesis"` special case. Two real bugs already shipped from exactly this
"slug == directory" assumption.

**Approach:** Consolidate all five mechanisms into one `resolve_project(slug)` function backed
by one override table (dissolved/absorbed divergences only); derive `PROJECT_SOURCES` from it
at module load instead of hand-declaring it; ship every roster/campaign row's resolved path
fields into `data.js` so `index.html` never re-derives; make an unresolvable slug exit non-zero
naming itself.

## Boundaries & Constraints

**Always:**
- One Python function + one override table is the sole place any code turns a slug into an
  `_bmad-output/projects/...` path; no other call site in `generate.py` or `index.html` builds
  that path by string concatenation.
- `PROJECT_SOURCES`, `_KEY_SLUG_OVERRIDE`, `_DERIVE_EXCLUDE` remain present as module-level
  attributes on `generate.py` with equivalent shape/values to today — `pyforge-doctor`'s
  `src/pyforge/doctor/sources/board.py` dynamically `exec_module`s this file and reads them by
  name (`gen.PROJECT_SOURCES`, `gen._KEY_SLUG_OVERRIDE`, `gen._DERIVE_EXCLUDE`); that consumer
  is out of this story's surface.
- Project discovery (the CI-safe basis) reuses `scan_projects()`'s existing tracked-`epics.md`
  glob — never requires the gitignored Tier-3 `sprint-status.yaml` to exist.
- Newly discovered project directories resolve with zero override-table edits; absorbed
  satellites resolve to the owning Smith's tree including non-default artifact filenames
  (table data); the dissolved case (`pyforge-genesis`) is its own data shape
  (`project_dir: None` + explicit redirect), never force-fit into the absorbed-satellite shape,
  and its `have` stays all-False.
- Rendered dashboard output for the current fleet is unchanged except the genesis redirect now
  reads from shipped data instead of a JS literal.

**Block If:** the byte-identical-output constraint appears to require renaming or removing an
existing `data.js` field that something outside `docs/dashboard/` and the two test files named
in this spec's Code Map might depend on — HALT and report before renaming/removing.

**Never:**
- Edit `src/shared/packages/pyforge-doctor/` (out of surface) — only verify its existing pin
  test still passes.
- Touch the separate, named-non-goal `GUILD_DREAMS`/`DREAM_STATUSES` duplication (owned
  elsewhere) or `station_order`/`station_info` hardcoding in `scan_command_center`.
- Unify `_discover_loop_homes()`'s independent slug normalization into this resolver — it
  resolves paths under `~/.bmad-loops` (outside the repo), a different domain; stays separate.
- Change dashboard content/semantics for the current fleet beyond the genesis redirect fix.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Bare-key happy path | `resolve_project("marshal")` | `project_dir="pyforge-marshal"`, default epics/sprint-status/ledger paths | No error |
| Slug≠directory override | `resolve_project("presenton-pixi-image")` | `project_dir="pyforge-mason"`, explicit `epics_path` pointing at `epics-presenton-pixi-image.md` — proves the divergence mechanism | No error |
| Dissolved, no tree | `resolve_project("pyforge-genesis")` | `project_dir=None`, `redirect="docs/governance"`, no epics/sprint-status/ledger paths | No error |
| New station, zero edits | A new `_bmad-output/projects/pyforge-<x>/planning-artifacts/epics.md` appears, no table edit | Resolves via discovery with default paths | No error |
| Unresolvable slug | A roster/campaign slug with no override and no matching `_bmad-output/projects/<dir>` | Generation halts | Exits non-zero, message names the offending slug (FR-143) |

</intent-contract>

## Code Map

- `docs/dashboard/generate.py:44-66` -- hand-authored `PROJECT_SOURCES` + its `TODO`; becomes a
  derived view over `resolve_project()`.
- `docs/dashboard/generate.py:184,212,291,594,641,2052` -- `_KEY_SLUG_OVERRIDE` and its five
  independent `f"pyforge-{key}"`-fallback call sites (`scan_projects`, `check_project_coverage`,
  `apply_tracked_ledger`, `build_fleet_progress`, `scan_readiness`); collapse onto the resolver.
- `docs/dashboard/generate.py:1046-1050,1062` -- `CAMPAIGN_PROJECT_OVERRIDE`, folds into the one
  table.
- `docs/dashboard/generate.py:1089-1119` -- `IMPL_CAMPAIGN`'s per-entry `epics_path` (only 3 of
  9 rows today); every row must carry a resolver-computed value (possibly `None`).
- `docs/dashboard/generate.py:1134-1138` -- `IMPL_CAMPAIGN_LEDGER`, folds into the one table via
  a `ledger_path` field.
- `docs/dashboard/generate.py:2876-2883` -- `build_status()`'s hand-landed-attribution substring
  match against `PROJECT_SOURCES` keys; logic unchanged, now iterates the derived key set.
- `docs/dashboard/generate.py:2893` (`main`) -- top-level call sites that invoke the resolver
  over roster/campaign data must let an unresolvable-slug failure reach a non-zero exit.
- `docs/dashboard/index.html:1060-1097` -- the two JS special cases to remove: the
  `r.slug === "pyforge-genesis"` redirect (~1069-1071) and the `"epics_path" in r`
  fallback-concatenation (~1093-1094); both become pure reads of shipped data.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py:823-901` -- external
  read-only consumer of `PROJECT_SOURCES`/`_KEY_SLUG_OVERRIDE`/`_DERIVE_EXCLUDE`; do not edit.
- `.claude/skills/conda-forge-expert/tests/meta/test_dashboard_renders.py` -- existing
  render-smoke test; must keep passing.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_dashboard_drift.py:362`
  (`test_real_generate_py_loads_and_exposes_the_expected_attribute_surface`) -- external
  contract-pin test; must keep passing unmodified.

## Tasks & Acceptance

**Execution:**
- [x] `docs/dashboard/generate.py` -- add a `ProjectResolution` record + `resolve_project(slug)`
  + one `_PROJECT_OVERRIDES` table (dissolved/absorbed entries only) + a named exception for an
  unresolvable slug -- the one resolver, one override table (CAP-1).
- [x] `docs/dashboard/generate.py` -- replace the five `_KEY_SLUG_OVERRIDE` call sites (lines
  212, 291, 594, 641, 2052) with `resolve_project()` calls; compute `PROJECT_SOURCES` as a
  derived dict at module load (drop the hand-authored literal + its `TODO`) -- CAP-2, and keeps
  the attribute present for pyforge-doctor's dynamic read.
- [x] `docs/dashboard/generate.py` -- fold `CAMPAIGN_PROJECT_OVERRIDE`, `IMPL_CAMPAIGN`'s ad hoc
  `epics_path` entries, and `IMPL_CAMPAIGN_LEDGER` into `_PROJECT_OVERRIDES`; campaign-row
  builders call `resolve_project()` instead -- collapses the remaining override surfaces (CAP-1).
- [x] `docs/dashboard/generate.py` -- emit each row's resolved `epics_path`/`redirect` (and the
  existing `planning_project`-shaped field where applicable) into every roster/campaign entry
  written to `data.js`, for all rows, not just the 3 that have it today -- CAP-3.
- [x] `docs/dashboard/index.html` -- remove the `r.slug === "pyforge-genesis"` special case and
  the `"epics_path" in r` fallback-concatenation; read the resolved fields shipped in `data.js`
  directly -- CAP-3, JS never re-derives.
- [x] `docs/dashboard/generate.py` -- let an unresolvable-slug exception from `resolve_project()`
  propagate to a non-zero `main()` exit that prints the offending slug -- FR-143.
- [x] New unit tests for `resolve_project()` covering every I/O Matrix scenario above (bare-key,
  slug≠directory override, dissolved/no-tree, newly-discovered directory, unresolvable slug).
- [x] Verify `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_dashboard_drift.py`
  still passes unmodified (confirms the backward-compat attribute contract holds).

**Acceptance Criteria:**
- Given the override table, when a hypothetical dissolved/absorbed slug is added to it and
  nothing else, then `have` detection, its link, and sprint-status reads are correct across
  every dashboard section on the next `dashboard-gen` run.
- Given `generate.py` and `index.html`, when grepped for `_bmad-output/projects/` path
  construction, then exactly one place in `generate.py` (the resolver) constructs the path, and
  `index.html` contains zero slug→path special cases.
- Given the current fleet, when `dashboard-gen` runs before and after this change, then
  `data.js`'s content is unchanged except the genesis-redirect plumbing now being data-driven.
- Given `pyforge-doctor`'s existing dynamic-load contract test, when it runs after this change,
  then it still passes unmodified.

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 3, low 2)
- defer: 2 (high 0, medium 1, low 1)
- reject: 3 (high 0, medium 0, low 3)
- addressed_findings:
  - `medium` `patch` Absorbed-satellite `_PROJECT_OVERRIDES` entries (`presenton-pixi-image`, `wasm-analytics-stack`, `unity-data-stack`) silently defaulted `sprint_status_path` to the *owning* project's own real feed instead of `None` — set explicitly to `None` on all three; added test assertions.
  - `medium` `patch` `_PROJECT_OVERRIDES` had no schema validation — a missing `project_dir` key, an unknown key, or `project_dir: None` without `redirect` all silently misbehaved instead of erroring. Added `_validate_project_overrides()` (runs at import, unit-tested directly with 4 tests).
  - `medium` `patch` Two discovered project directories stripping to the same bare board key would silently collide in the `PROJECT_SOURCES` dict comprehension (last one wins, no warning) — `_discovered_board_keys()` now raises `ValueError` naming both directories; unit-tested.
  - `low` `patch` `PROJECT_SOURCES`'s import-time construction can raise `UnresolvableProjectError` before `main()`'s own try/except runs, if a discovered directory ever violated the constitutive `pyforge-<key>` naming rule (Charter Identity & Vocabulary) — still a loud, non-zero-exit, slug-naming failure per FR-143 (via an uncaught traceback), just not the polished `[resolve] FAIL` message. Documented in place rather than code-changed: a real fix would need speculative round-trip repair for a repo state the Charter already forbids elsewhere.
  - `low` `patch` Dead `rel` loop variable in `scan_readiness()` (`for key, rel in sorted(PROJECT_SOURCES.items())`, `rel` unused) — dropped.
  - `medium` `defer` `pyforge-doctor`'s `board.py` independently re-derives a project directory via its own `_KEY_SLUG_OVERRIDE` fallback instead of calling `resolve_project()` — agrees today only because that dict is empty on both sides; a future `_PROJECT_OVERRIDES` entry could silently diverge from doctor's board. Pre-existing (doctor package untouched by this diff), out of this story's surface (`Never: edit src/shared/packages/pyforge-doctor/`) — logged to `deferred-work.md`.
  - `low` `defer` The canonical `spec-dashboard-project-path-derivation/SPEC.md`'s Constraints still names the retired `epics-genesis-installer.md`/`genesis-installer` slug as a live absorbed-satellite example; that slug was retired 2026-08-08, before this story. Pre-existing prose staleness this story didn't touch — logged to `deferred-work.md`.
  - `low` `reject` `check_project_coverage()`'s new `try/except UnresolvableProjectError` is unreachable in the current call graph — valid defensive style, not a flaw.
  - `low` `reject` A literal reading of the spec's "byte-identical... modulo genesis redirect" boundary against the raw `data.js` JSON (which gained `epics_path`/`redirect` fields on every row, per CAP-3) — the actual constraint is rendered/visible board content, independently verified unchanged.
  - `low` `reject` `data.js` regeneration bundles concurrent live-fleet-state noise (other stations' in-flight progress) alongside the schema change — inherent, documented behavior of a live-regenerating dashboard tool, not an artifact of this change.

## Design Notes

`ProjectResolution` needs four optional derived fields beyond `project_dir`, all defaultable
from `project_dir` when set (`epics_path`, `sprint_status_path`, `ledger_path`), plus `redirect`
for the no-tree case:

```python
@dataclass(frozen=True)
class ProjectResolution:
    project_dir: str | None        # e.g. "pyforge-marshal"; None = no tree
    epics_path: str | None
    sprint_status_path: str | None  # Tier-3 gitignored; existence checked lazily by callers
    ledger_path: str | None         # tracked planning-artifacts/sprint-status-ledger.yaml
    redirect: str | None            # explicit link target only when project_dir is None
```

Two implementer judgment calls this story settles (left open by planning): (1)
`_discover_loop_homes()` stays a separate mechanism — different resolution domain, outside the
repo; (2) `_DERIVE_EXCLUDE` stays present but empty (no active per-entry need today; kept only
for `pyforge-doctor`'s attribute-shape pin).

## Verification

**Commands:**
- `pixi run -e local-recipes dashboard-gen` -- expected: exits 0, per-project resolution/match
  summary prints, `data.js` regenerates with resolved fields on every row.
- `pixi run -e local-recipes dashboard-check` -- expected: renders clean, same line/dream/chain
  counts as before this change.
- New `resolve_project()` unit tests -- expected: all I/O Matrix scenarios pass, including the
  unresolvable-slug case exiting non-zero and naming the slug.
- `pixi run -e local-recipes test -- src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_dashboard_drift.py`
  -- expected: still green, unmodified.

**Manual checks (if no CLI):**
- Diff `docs/dashboard/data.js` before/after regeneration for the current fleet; confirm only
  the genesis-redirect-related fields differ.

## Auto Run Result

Status: done
Blocking condition: none

**Summary:** Consolidated five independent hand-authored slug->project-directory mechanisms
in `docs/dashboard/generate.py` into one `resolve_project(slug) -> ProjectResolution` function
backed by one `_PROJECT_OVERRIDES` table (CAP-1). `PROJECT_SOURCES` is now derived via the same
tracked-`epics.md` discovery `scan_projects()` uses, not hand-declared (CAP-2). Every
planning/build-campaign row now ships its resolver-computed `epics_path`/`redirect` fields in
`data.js`, and `index.html` lost both of its slug->path JS special cases (the `pyforge-genesis`
redirect literal and the `epics_path in r` fallback), reading the shipped fields directly
(CAP-3). An unresolvable roster/campaign slug now exits `generate.py` non-zero, naming itself
(CAP-4/FR-143). `PROJECT_SOURCES`/`_KEY_SLUG_OVERRIDE`/`_DERIVE_EXCLUDE` remain present as
module attributes with equivalent shape for `pyforge-doctor`'s dynamic-load consumer, which is
untouched and still 26/26 green.

**Files changed:**
- `docs/dashboard/generate.py` -- the resolver, override table, and every call-site consolidation.
- `docs/dashboard/index.html` -- removed both slug->path JS special cases.
- `docs/dashboard/data.js` -- regenerated (resolved fields on every row; rendered board content
  otherwise unchanged, verified by controlled before/after diff).
- `.claude/skills/conda-forge-expert/tests/meta/test_dashboard_resolve_project.py` -- new, 18
  tests covering the I/O Matrix plus the review-pass validation guards.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/{spec-dashboard-project-path-derivation,spec-pyforge-testing-charter,spec-sprint-status-auto-promote}/.memlog.md`
  + `scripts/.spec-surface-baseline.json` -- spec-surface reconciliation (this story's own spec
  SHIPPED entry, plus co-governed-touch notes on the two other specs governing the same file).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- 2 new entries (see below).

**Review findings breakdown** (Blind Hunter + Edge Case Hunter, no shared context, deduplicated
to 10 distinct findings): 5 `patch` (0 high, 3 medium, 2 low) -- all auto-fixed same pass; 2
`defer` (0 high, 1 medium, 1 low) -- logged as `DW-FU-16-1` (pyforge-doctor's `board.py` still
independently re-derives a project directory, bypassing the new resolver -- pre-existing,
out-of-surface) and `DW-FU-16-1-2` (the canonical Tier-2 SPEC.md's Constraints still name a
retired `epics-genesis-installer.md` example -- pre-existing prose staleness); 3 `reject` (noise
-- an unreachable-but-valid defensive `try/except`, a too-literal reading of "byte-identical"
against a JSON artifact when rendered content was verified unchanged, and `data.js` naturally
carrying concurrent live-fleet-state noise). 0 `intent_gap`, 0 `bad_spec`.

**Follow-up review recommendation:** false. The review-driven patches were localized, mechanical
hardening (explicit-None defaults, table-schema validation, a collision guard, a dead-variable
cleanup, and one documentation-only fix) within the same mechanism this story already introduced
and already tested -- no security, data-integrity, or API-surface impact.

**Verification performed:**
- `pixi run -e local-recipes dashboard-gen` -- exit 0, `[resolve] 18 slug(s) resolved (4 via
  override, 14 default)`.
- `pixi run -e local-recipes dashboard-check` -- renders clean.
- 18/18 new `resolve_project()`/`_validate_project_overrides()`/`_discovered_board_keys()` unit
  tests pass; 1/1 existing render-smoke test passes.
- `pyforge-doctor`'s `test_sources_board_dashboard_drift.py` -- 26/26 pass, package untouched.
- `data.js` diff independently inspected: the only content changes beyond the new resolved
  fields are the corrected `pyforge-genesis` redirect and ordinary concurrent-fleet live-state
  noise (confirmed via a controlled before/after regeneration seconds apart).
- `pixi run -e local-recipes spec-surface-check` -- exit 0 after the scoped, `--spec`-targeted
  re-stamp of the 3 co-governing specs (verified exactly those 3 keys changed in the baseline
  diff, both stamping passes).
- 6 unrelated pre-existing test failures (unconnected script `--help` checks, one
  `bmad-drift-check` doc-classification gap) confirmed via `git stash` against the clean
  baseline -- identical failures with or without this story's changes, no regression introduced.

**Residual risks:** the two deferred findings above; otherwise none identified beyond normal
code-review residue.
