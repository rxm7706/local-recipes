---
title: 'Safe upgrade-path recommendation -- `Prescription.safe_upgrade_target` (FR-13, AD-10)'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md',
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py',
  '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-3-2-rank-the-actionable-partition.md',
]
warnings: [
  'The architecture spine (AD-10) names this field `next_safe_version`; the epics.md Story 4.4 AC text (identical wording repeated in the task brief that drove this implementation pass) names it `safe_upgrade_target`. This story follows epics.md''s literal AC wording as the more specific, story-level authority -- see Design Notes for the full reasoning and the deviation record.',
  'No current Source producer''s evidence carries an `upstream_version`/`pypi_current_version` field (same gap `_classify_blast_radius`, Story 3.2, already documented) -- this resolves to `(None, ...)` for every Finding gathered by today''s live axes. Directly testable with synthetic evidence; not a bug.',
]
baseline_revision: 'HEAD at Story 4.4 start (after Stories 4.1/4.2/4.3 landed in the same pass)'
---

<intent-contract>

## Intent

**Problem:** A Prescription today ranks and names a root cause, but stops short of naming a concrete next version -- "here's a ranked problem" instead of "update to X.Y.Z."

**Approach:** `pyforge.doctor.prescribe.recommend_safe_upgrade(finding)` -- a pure function (AD-4/AD-10 preserved: zero new subprocess/MCP calls, no new imports) reading ONLY `finding.evidence`'s already-gathered version fields (the SAME `upstream_version`/`pypi_current_version`/`latest_conda_version` keys Story 3.2's `_classify_blast_radius` already reads). Returns `(target, reason)`: a version string when confidently known (patch/minor bump, no breaking-change signal), else `None` with a reason ALWAYS populated. Single-hop only -- reuses `_classify_blast_radius`'s existing patch/minor/major/unknown/current classification rather than inventing a second heuristic; a `"major"` jump is explicitly not confidently safe. Wired into `__main__._build_prescriptions` for every Prescription.

## Boundaries & Constraints

**Always:**
- `safe_upgrade_target`/`safe_upgrade_reason` are BOTH always present as keys in the serialized Prescription (schema `required`), `reason` populated even when `target` is `null` -- mirrors `rank`/`rank_factors`'s own paired value+explanation convention.
- Single-hop: this Finding's OWN next version only -- reuses `_classify_blast_radius`, never a second traversal or a multi-package graph walk.
- `prescribe.py` stays a pure function over already-gathered data (AD-4) -- no new imports added to the module (confirmed by the unchanged `test_prescribe_pure_function.py` sanctioned-import-set assertion).

**Never:**
- Never a guessed version standing in for missing confidence -- a `"major"` version jump, an explicit `evidence["breaking_change"]` signal, or missing/unparseable version evidence all resolve to `(None, <reason>)`.
- Never a new evidence vocabulary -- reads only keys `_classify_blast_radius` already reads.
- Never trigger a new fetch inside `prescribe` itself.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No `upstream_version`/`pypi_current_version` in evidence | Today's live default | `(None, "no upstream target version available...")` | No error |
| Patch bump, no breaking-change signal | `1.2.3 -> 1.2.4` | `("1.2.4", "patch version bump, no known breaking-change signal")` | No error |
| Minor bump, no breaking-change signal | `1.2.3 -> 1.3.0` | `("1.3.0", "minor version bump, ...")` | No error |
| Major version jump | `1.2.3 -> 2.0.0` | `(None, "...major-version jump...spans too much ground...")` | No error |
| Explicit `breaking_change` signal | Any bump size | `(None, "a breaking-change signal is present...")` -- overrides even a small bump | No error |
| Unparseable version strings | `"not-a-version"` | `(None, "no single confidently-known next-safe version...")` | No error |
| `diagnose --prescribe --json` | Any run | Every prescription carries `safe_upgrade_target`/`safe_upgrade_reason` keys, schema-valid | Self-validated before stdout |
| Human-readable `--prescribe` render | Any run | A "safe upgrade: X (reason)" or "safe upgrade: none -- reason" line per prescription | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py` -- EDIT. New `recommend_safe_upgrade(finding)` function, appended after `name_root_cause` -- no new imports.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- EDIT. `Prescription` gains `safe_upgrade_target: str | None = None`/`safe_upgrade_reason: str | None = None` (defaulted, so every pre-Epic-4 construction site keeps working unchanged); `to_json_dict` always emits both keys.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` -- EDIT. `#/$defs/prescription`'s `required` list + `properties` gain both fields.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- EDIT. `_build_prescriptions` calls `prescribe.recommend_safe_upgrade` per Finding; `_emit_text`'s prescription-section render gains a "safe upgrade" line per FR-9 parity.
- `src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_safe_upgrade.py` -- NEW. Full AC matrix, pure-function level.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_diagnose.py` -- EDIT. CLI-level wiring proof (confidently-known + null cases), schema-validated.
- `src/shared/packages/pyforge-doctor/tests/unit/test_models.py` -- EDIT. `test_prescription_to_json_dict_shape` updated for the two new keys (default `None`); two new dedicated tests for default-backward-compat and round-trip.

## Design Notes

**The field-name deviation (the one genuinely non-obvious call in this story):** the architecture spine's AD-10 text (written 2026-08-02, before Stories 4.1-4.4 were fleshed out into full ACs) says the field is `next_safe_version`. The subsequently-authored epics.md Story 4.4 AC text -- the more specific, story-level decomposition, and the exact wording repeated verbatim in the task brief driving this implementation pass -- says `safe_upgrade_target`. These two authoritative-looking sources disagree on a bare naming choice (the SEMANTICS are identical in both). Resolved by following epics.md/the task brief (`safe_upgrade_target`) as the more specific and more recently-authored authority for a story-level implementation detail, treating AD-10's `next_safe_version` as an early placeholder name superseded by the story's own AC text -- the architecture spine itself explicitly defers "exact member naming" to "epics/stories" for its OTHER Epic 4 additions (AD-9's Source member name, AD-8's exact CLI surface), so treating AD-10's field name the same way is consistent with the spine's own stated deferral pattern, not an unreviewed departure from it. Flagged explicitly in this spec's `warnings` for visibility.

**Why `recommend_safe_upgrade` reuses `_classify_blast_radius` rather than a second heuristic:** Story 3.2 already built and tested a patch/minor/major/unknown/current classifier over the exact same evidence shape this story needs. AC2's "spans multiple major-version jumps" scenario maps directly onto `_classify_blast_radius`'s own `"major"` label -- reusing it keeps ONE version-comparison heuristic in the module instead of two subtly-different ones that could drift apart.

**Why an explicit `breaking_change` evidence key overrides even a small (patch/minor) bump:** a small version-number delta is a WEAK proxy for "safe" -- semantic versioning is a convention, not a guarantee, and a Finding's own evidence may carry a more direct signal than the version numbers alone. No current live producer sets this key (same "forward-compatible hook, not yet live" framing `partition()`'s own `waived`/`fix_available` hooks already use) but it's directly testable with synthetic evidence and becomes live the moment a future producer starts setting it.

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`

**Actual results (2026-08-07):** full suite green (403 total after all four Epic 4 stories). 8 new `test_prescribe_safe_upgrade.py` tests + 2 new CLI-level tests + 2 new/updated `test_models.py` tests all pass; `test_prescribe_pure_function.py`'s sanctioned-import-set assertion still passes unchanged (no new imports added to `prescribe.py`).

## Review Triage Log

### 2026-08-07 -- Self-review pass (adversarial re-read of the diff)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 1 (the AD-10/epics.md field-name conflict -- resolved per Design Notes above, not deferred, but recorded here since it is a genuine documentation inconsistency the next architecture-doc sync pass should reconcile: either AD-10 should be updated to `safe_upgrade_target`, or a note added cross-referencing the story-level override)

Checked specifically for: exception handling (`recommend_safe_upgrade` has zero exception surface -- pure `dict.get`/string comparisons over already-validated `Finding.evidence`, delegates version parsing entirely to the already-reviewed `_classify_blast_radius`/`_leading_numeric_release`, which themselves return `None`/`"unknown"` rather than raising on unparseable input); silent drops (N/A -- this function has no collection to iterate, it's a per-Finding computation); docstring-vs-behavior drift (re-read the docstring's own three-condition "confidently known" list against the code -- matches: concrete target present, no breaking_change signal, blast_label in {patch, minor}); AD-4 purity (confirmed via `git diff prescribe.py` -- zero new import lines; `test_prescribe_pure_function.py`'s sanctioned-set assertion passes unchanged, proving no accidental import crept in); backward compatibility (confirmed every pre-Epic-4 `Prescription(...)` construction site in the existing test suite -- `test_prescribe_partition.py`/`test_prescribe_rank.py`/`test_prescribe_root_cause.py` never construct `Prescription` directly, only `test_models.py` and `__main__.py` do, both updated).

**Follow-up review recommendation: false** -- the field-name deviation is the one open item, and it's a documentation-sync note for a future pass, not a code defect; behavior is fully tested both at the pure-function and CLI-wiring layers.

</intent-contract>
