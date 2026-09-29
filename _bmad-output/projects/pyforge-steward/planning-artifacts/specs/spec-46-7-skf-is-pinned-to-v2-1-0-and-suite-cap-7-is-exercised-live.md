---
title: "Story 46.7: skf is pinned to v2.1.0 and CAP-7 is exercised live"
type: 'chore'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
baseline_revision: '4526db1028fc8ad2e10e71d3e780def56efb66c0'
context: []
warnings: []
deferred:
  - "sprint-status-ledger.yaml still lists 46-7 as backlog — deferred to step 11 (PR-landing ledger sync)."
  - "No test proves the real 6.12.0.yaml catalog's skf pin actually reaches apply_bmad_core_upgrade's real installer argv end-to-end (target_version=\"6.12.0\"); every existing test uses either a synthetic fixture catalog or the real catalog with a fake installer. Deferred to Story 14.9, which already owns the injected-runner argv-assertion tests for the --no-shims apply and explicitly names the CAP-7/skf-pin interaction."
---

<intent-contract>

## Intent

**Problem:** `bmad_core_releases/6.12.0.yaml`'s `custom_modules[skf].pin` reads `null` even
though its own comment already records the 2026-09-06 verification (npm 2.1.0 tarball `src/`
== GitHub tag `v2.1.0`, 337 files, `diff -rq` empty) that settles the Spec's open question
(Q3/Q5). The generic pin→argv mechanism (`upgrade.py`'s `pins = [f"{module.name}={module.pin}"
for module in installed_custom_defs if module.pin]`) already exists and is already covered by
an existing unit test (`test_apply_custom_module_catalog_pin_lands_on_core_argv`) using
literal `skf`/`v2.1.0` fixture values — but that test uses a synthetic fixture catalog, never
the real `6.12.0.yaml` file, so nothing currently proves the REAL catalog's pin field is
actually set.

**Approach:** Flip the catalog's `pin: null` → `pin: v2.1.0`. Add one new unit test that loads
the real `bmad_core_releases/6.12.0.yaml` file and asserts its `skf` custom-module entry's
`pin` field equals `"v2.1.0"` — closing the gap the existing generic-mechanism test leaves
(that test proves the mechanism works once a pin exists; it does not prove the real catalog
sets one). Record the pin decision in the core-upgrade memlog.

## Boundaries & Constraints

**Always:**
- Only change the `pin:` field's value in `6.12.0.yaml`; do not touch any other field in the
  `skf` `custom_modules` entry (its `own_installer`, `config_paths`, `packaged_source`, or
  `notes` fields) without a found discrepancy.
- The new test must load the actual packaged catalog file (not a synthetic fixture) so a
  future accidental revert of the YAML value is caught.
- Do not perform the actual live `--no-shims` apply here — that is a later step in this
  session's sequence (Session 2 step 9 / Story 14.9's execution), which this story's own text
  explicitly defers to.

**Never:**
- Do not touch `test_apply_custom_module_catalog_pin_lands_on_core_argv` — it already covers
  the generic mechanism correctly and should stay unchanged (its skf/v2.1.0 literals were
  written to model the target state, not to be broken by this story's own change).
- Do not remove or reword the catalog's own 2026-09-06 verification comment — it is the
  evidentiary record for this exact decision; the pin flip should sit alongside it, not
  replace it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Catalog pin | `6.12.0.yaml`'s `custom_modules[skf].pin` | Reads `v2.1.0` (was `null`) | N/A |
| Real-catalog test | New unit test loading `6.12.0.yaml` | Asserts `pin == "v2.1.0"` for the `skf` entry | If the field is ever reverted, this test reds |
| Existing mechanism test | `test_apply_custom_module_catalog_pin_lands_on_core_argv` | Still passes unchanged (synthetic fixture, unaffected by the catalog edit) | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.12.0.yaml`
  — line ~130, `custom_modules[skf].pin: null` → `pin: v2.1.0`.
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py` — add ONE new test
  (near the existing `test_apply_custom_module_catalog_pin_lands_on_core_argv`, ~line 1081)
  that loads the real `bmad_core_releases/6.12.0.yaml` (via whatever loader function this
  module already uses elsewhere for the real catalog — check `load_custom_modules` /
  `load_release_catalog`-style helpers already imported in this test file) and asserts the
  `skf` entry's `pin` equals `"v2.1.0"`.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/.memlog.md`
  — append a dated note recording the pin decision (mirroring the catalog's own comment).

## Tasks & Acceptance

**Execution:**
- `6.12.0.yaml` -- flip `pin: null` -> `pin: v2.1.0` -- closes the Spec's open Q3/Q5 per the
  already-recorded 2026-09-06 verification.
- `test_upgrade_apply.py` -- add a real-catalog pin assertion -- proves the production config,
  not just the generic mechanism, is correct.
- core-upgrade memlog -- record the decision -- keeps the spec's own change history current.

**Acceptance Criteria:**
- Given `6.12.0.yaml` after this story, when `custom_modules[skf].pin` is read, then it equals
  `"v2.1.0"`.
- Given the new unit test, when it runs against the real catalog file, then it passes.
- Given `test_apply_custom_module_catalog_pin_lands_on_core_argv` (pre-existing), when re-run,
  then it still passes unchanged.
- Given `pixi run -e pyforge-steward pyforge-steward-test`, when run after this story, then it
  is green.

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass (Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Intent Alignment Auditor)
- verdicts: 8 findings — high 0, medium 0, low 5, false 1, maybe-false 0; 1 combined VG+IA finding deferred
- findings:
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (independent, same finding): `6.12.0.yaml`'s comment directly above `custom_modules[skf].pin` still read "The `--pin skf=v2.1.0` question stays open (customization-inventory.md § 4: is the conda-packaged 2.1.0 == cached `main` == tag v2.1.0?)" even after the pin flip landed — verified true. Fixed: reworded the comment to record the resolution and its evidence (npm 2.1.0 tarball `src/` == GitHub tag `v2.1.0`, 337 files, `diff -rq` empty).
  - `[low]` `[patch]` Blind Hunter: `customization-inventory.md` rows C6 and C19 and § 3 step 4 and § 4's open-question bullet all still described the skf pin as unresolved ("verify before pinning" / "stays open" / "whether the tag matches the packaged source is unverified") — verified true across all four locations. Fixed: all four reworded to close the question with the same evidence, cross-referencing Story 46.7.
  - `[low]` `[patch]` Blind Hunter: `spec-bmad-method-core-upgrade`'s own spec-surface baseline was stale (its `customization-inventory.md` companion's hash had drifted since an earlier edit was never re-stamped) — verified true via direct sha1 comparison (`da6a33f5...` current vs. `b5629f66...` baseline). Fixed: added a memlog note and re-stamped scoped (`--write-baseline --spec pyforge-steward/spec-bmad-method-core-upgrade`); this story's own two follow-up edits (the YAML comment + customization-inventory.md's four spots) then re-drifted `spec-pyforge-steward`'s own hash for `6.12.0.yaml`, which is re-stamped in the same pass (see Auto Run Result).
  - `[low]` `[defer]` Blind Hunter: `sprint-status-ledger.yaml` still lists `46-7-...` as `backlog` — verified true; deferred to step 11 (PR-landing), which syncs all touched stories' ledger rows together.
  - `[low]` `[defer]` Blind Hunter: `epics.md`'s Story 46.7 block has no `**Status:** done` / Outcome block yet — verified true; deferred to step 11, which adds each story's Outcome note as part of PR landing.
  - `[false]` `[reject]` Blind Hunter: the new `test_real_catalog_pins_skf_v2_1_0` is largely redundant with `test_catalog_ships_612_custom_modules` (both assert the same pin field on the same file) — refuted: the two tests assert against different code paths (`load_release_catalog`/`load_custom_modules`, the CAP-7 apply-time loader, vs. the pre-flight's own raw-dict + dataclass parse), so they guard against different regressions (a break in either loader path) even though today they'd fail together. Kept both, no change.
  - `[medium via combined VG+IA]` `[defer]` Verification Gap Reviewer + Intent Alignment Auditor (combined, same underlying gap): no test proves the REAL `6.12.0.yaml` catalog's `skf` pin actually reaches `apply_bmad_core_upgrade`'s real installer argv end-to-end with `target_version="6.12.0"` — every existing test (including this story's new one) either loads the real catalog and stops at the dataclass, or drives `apply_bmad_core_upgrade` with a synthetic fixture catalog. Confirmed via grep: no existing test passes `target_version="6.12.0"` to `apply_bmad_core_upgrade`. Deferred to Story 14.9 (the `--no-shims` apply implementation), whose own epics.md text already requires "the argv assertion... each have a unit test with an injected runner" and explicitly names the CAP-7/skf-pin interaction — the natural, non-duplicative home for this exact real-catalog + target-6.12.0 + fake-installer integration test, rather than adding a one-off here that Story 14.9 would likely have to touch again anyway.

## Design Notes

This story's live-apply half ("CAP-7 is exercised live") is explicitly Session 2 step 9
(Story 14.9's execution), not this story — this story only sets up the pin so that later apply
has the right value to exercise. The epic-context compile step was skipped as disproportionate
overhead for an XS, single-field chore fully specified by its own story text plus a direct
read of the existing mechanism and its test coverage.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pytest tests/unit/test_upgrade_apply.py -q` -- expected: all
  pass, including the new test.
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: green.
- `pixi run -e local-recipes detectors-ci` -- expected: clean (or unchanged pre-existing
  findings only).

## Auto Run Result

**Summary:** Flipped `6.12.0.yaml`'s `custom_modules[skf].pin` from `null` to `v2.1.0`, closing
the Spec's open Q3/Q5 per the 2026-09-06 verification already recorded in the catalog's own
comment (npm 2.1.0 tarball `src/` byte-identical to GitHub tag `v2.1.0`, 337 files, `diff -rq`
empty). Added `test_real_catalog_pins_skf_v2_1_0`, which loads the real packaged catalog via
`load_release_catalog("6.12.0")` and asserts the `skf` entry's pin — closing the gap the
pre-existing synthetic-fixture mechanism test leaves. Updated `test_upgrade_preflight.py`'s
`test_catalog_ships_612_custom_modules` to match the new pin value (a necessary consequence of
the catalog change, not a new assertion). Review pass found and fixed 3 low-severity
documentation-currency gaps (a stale "question stays open" comment in the catalog itself, 4
stale open-question mentions across `customization-inventory.md`, and one genuinely stale
spec-surface baseline on the sibling `spec-bmad-method-core-upgrade` spec); deferred 2 low items
to step 11 (ledger/epics.md sync) and 1 combined finding to Story 14.9 (the real-catalog +
target-6.12.0 + fake-installer argv integration test, which that story already owns).

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.12.0.yaml`
  — `pin: null` -> `pin: v2.1.0`; comment reworded to record resolution.
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py` — new
  `test_real_catalog_pins_skf_v2_1_0`.
- `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_preflight.py` —
  `test_catalog_ships_612_custom_modules` updated to assert `pin == "v2.1.0"`.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/.memlog.md`
  — pin-decision note.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-method-core-upgrade/customization-inventory.md`
  — rows C6/C19, § 3 step 4, § 4 open-question bullet reworded to close the question.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`
  — two notes (surface reconcile + review-fix follow-up).
- `scripts/.spec-surface-baseline.json` — re-stamped scoped for both
  `pyforge-steward/spec-bmad-method-core-upgrade` and `pyforge-steward/spec-pyforge-steward`.

**Review findings breakdown:** 8 findings (7 distinct after 2 independent duplicates merged) —
3 patched (all low), 1 rejected as false, 2 deferred (both low, to step 11), 1 deferred (medium
via combined VG+IA, to Story 14.9).

**Follow-up review recommendation:** `false` — 0 high-verdict patches, 0 medium-verdict
patches (the one medium-severity finding was deferred, not patched); well under the 2+ medium
patch threshold.

**Verification performed:**
- `pixi run -e pyforge-steward pytest tests/unit/test_upgrade_apply.py tests/unit/test_upgrade_preflight.py -q` — 94 passed.
- `pixi run -e pyforge-steward pyforge-steward-test` — 1091 passed.
- `pixi run -e local-recipes python -m pyforge.doctor.sources spec-surface` — clean, no drift.
- `pixi run -e local-recipes detectors-ci` — 17/18 clean (pre-existing `dream-chain` finding
  only, unrelated to this story — a marshal-owned Dream lacking a Spec).

**Residual risks:** none beyond the deferrals recorded above. The live `--no-shims` apply that
actually exercises this pin against a real CAP-7 own-installer run is Session 2 step 9 / Story
14.9, not this story, per this story's own stated boundary.
