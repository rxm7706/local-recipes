---
title: 'Root-cause naming'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-3-2-rank-the-actionable-partition.md',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py',
]
warnings: []
baseline_revision: 'HEAD at Story 3.3 start (after Story 3.2 landed)'
---

<intent-contract>

## Intent

**Problem:** A `Prescription` that only repeats a Finding's own `message`/`check` doesn't tell an operator WHY the problem exists — the difference between "a CVE with no fix" and "a CVE whose fix already shipped upstream, just not adopted" changes what action is worth taking.

**Approach:** `pyforge.doctor.prescribe.name_root_cause(finding, all_findings) -> str` — a pure function (AD-4) with a `Source.CVE_WATCHER`-specific path that correlates against a same-`check` `Source.STALENESS_REPORT` Finding IN THE SAME GATHER BATCH (`all_findings`) when one exists, naming the staleness lag explicitly; every other Source templates its root cause from its OWN `evidence` field, falling back to the Finding's own `message` verbatim when `evidence` is empty (Story 1.2's own documented shape for today's live `warden-doctor` Findings).

## Boundaries & Constraints

**Always:**
- `name_root_cause` takes BOTH the target `finding` and the full `all_findings` batch it was gathered alongside — root-cause naming for a CVE requires cross-referencing a sibling Finding, so a single-Finding signature would be insufficient (a deliberate signature difference from `partition()`/`rank()`, which operate purely per-Finding or over one already-filtered list).
- Every returned root-cause string is non-empty (proven for all 7 `Source` members with empty evidence — the universal floor is the Finding's own `message`, which is itself already human-readable, never a placeholder).
- The CVE-to-staleness correlation matches on `check` (the feedstock/package identifier) and `Source.STALENESS_REPORT`, and NEVER treats a Finding as correlated with itself (an `is not finding` identity guard, not merely an equality check — two structurally-identical-but-distinct Findings for different runs must not accidentally short-circuit this).
- The engine-missing/evidence-templating path (AC2) applies UNIFORMLY to every non-CVE Source, not only the AC's own named "engine-missing" example — the templating rule itself (`join evidence key:value pairs, prefixed by message`) is Source-agnostic, so there's no reason to special-case just one Source.
- `name_root_cause` stays inside `doctor.prescribe`'s existing AD-4 purity boundary — no new imports, no subprocess/MCP calls (already covered by the Story 3.1 meta-test; no new sanctioned-surface entry needed since this story adds zero new imports).

**Never:**
- Never fabricate a root cause with an NLP/inference layer — every branch reads only structured `evidence`/`message` fields Epic 1/2 already produced (AC2's own explicit constraint).
- Never let the staleness correlation match on anything other than `check` + `Source.STALENESS_REPORT` — matching on `message` similarity or fuzzy package-name comparison would be exactly the kind of inference layer this story explicitly rules out.
- Never drop the Finding's own `message` when evidence IS present — the templated root cause is `message` PLUS the evidence clause, not evidence alone (an operator who already reads the message for context should not lose it).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CVE Finding + same-`check` staleness Finding in the batch | Correlated | Root cause names the staleness lag (age_days, version), not only the CVE | No error |
| CVE Finding, no correlated staleness Finding | Uncorrelated | Root cause still names the package + delta/severity, notes no correlation | No error |
| CVE Finding + staleness Finding for a DIFFERENT package | Uncorrelated (wrong `check`) | Staleness data never leaks into the wrong Finding's root cause | No error |
| Engine-missing / env-hygiene Finding with non-empty evidence | Templated | Root cause includes every evidence key:value AND the original message | No error |
| Any Finding with empty evidence (e.g. live `warden-doctor`) | Fallback | Root cause == the Finding's own `message`, verbatim | No error |
| Every `Source` member, empty evidence | Universal floor | Root cause always non-empty | No error |
| A CVE Finding passed alongside only itself | Self-correlation guard | Never treated as correlated with itself even if it happens to carry staleness-shaped evidence keys | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py` — EDIT (additive). New: `_find_correlated_staleness`, `_cve_root_cause`, `_templated_root_cause`, `name_root_cause()`. No new imports.
- `src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_root_cause.py` — NEW. Full I/O matrix (7 tests): staleness correlation (positive, negative-uncorrelated, negative-wrong-package), evidence templating (env-hygiene example carrying file/line/var_name), empty-evidence fallback to message verbatim, universal non-empty floor across all 7 `Source` members, self-correlation guard.

## Design Notes

**Why the templating rule is Source-agnostic rather than special-cased per Source:** Story 3.3 AC2 names exactly one example ("an engine-missing Finding... templated from that Finding's own evidence field"), but the underlying mechanism it describes — "read structured evidence Epic 1/2 already produced, no new NLP/inference layer" — has no Source-specific content. Writing five near-identical per-Source templating functions (one each for `warden-doctor`, `staleness-report`, `feedstock-health`, `release-cadence`, `env-hygiene`) would duplicate the same "join evidence, prefix with message" logic five times for zero behavioral difference. One shared `_templated_root_cause` covers all of them; only `Source.CVE_WATCHER` genuinely needs its own path, because it's the only Source whose root cause requires CROSS-Finding correlation rather than templating its own evidence.

**Why the self-correlation guard uses `is not finding` (identity) rather than `!=` (equality):** two independently-constructed `Finding`s can be VALUE-equal (same source/check/status/message/evidence) without being the same object — e.g. a test constructing two structurally-identical fixtures, or (hypothetically) a future gather path that emits a duplicate row. An equality-based guard would silently exclude a legitimately-distinct second Finding just because it happens to match the first byte-for-byte; identity is the correct "don't correlate with myself" semantics.

**Why an uncorrelated CVE root cause still names something useful rather than just "no known cause":** the AC only specifies the CORRELATED case's exact wording; for the uncorrelated case, silence or a bare "unknown" would waste the CVE evidence Doctor DOES have (package name, severity, delta, current count). The chosen wording ("no correlated staleness signal for this package in the same run, so this may be a newly-disclosed CVE with no upstream fix yet rather than an adoption lag") explicitly frames the absence of correlation as itself informative — it tells the operator this is NOT a known-adoption-lag case, which is a real signal, not a non-answer.

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src python3 -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_root_cause.py -q`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — **320 passed** (313 baseline from Story 3.2 + 7 new tests).
- Isolated run: 7 passed.

## Review Triage Log

### 2026-08-07 -- Self-review pass (adversarial re-read of the diff)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0

Checked specifically for: exception handling (none needed -- `_find_correlated_staleness` iterates a plain sequence and returns `None` on no match, never raises; `.get(...)` calls never raise); resource leaks (none, no I/O); silent failures ("no root cause" is not a representable state -- the universal `message`-fallback floor guarantees a non-empty string for every `Source`, proven directly by `test_root_cause_is_never_empty`'s all-7-Sources loop); MCP/CLI equivalence (N/A, AD-4 module); docstring-vs-behavior drift (re-read `name_root_cause`'s and `_cve_root_cause`'s docstrings against the actual branch logic -- both match: the CVE dispatch is the only Source-specific path, everything else templates uniformly as documented).

**Follow-up review recommendation: false** -- no findings.


### 2026-08-07 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, Epic 2+3 batch)

Dispatched with the diff file path only, no shared context.

- `medium` `patch` **False correlation between two unrelated packages both missing a feedstock name.** `sources/atlas.py::_row_check_name` normalizes ANY row missing every name field to the same literal placeholder, `"<unknown feedstock>"`. `_find_correlated_staleness` matched purely on `other.check == finding.check`, so a CVE row and an unrelated staleness row that both hit that fallback would match and be reported as correlated -- a confidently wrong root cause ("correlated with a staleness signal ... pinned at {unrelated package's version}") rather than the honest "no correlated staleness signal" fallback. Fixed: `_find_correlated_staleness` now refuses to match when `finding.check` is that placeholder (a new `_UNKNOWN_FEEDSTOCK_CHECK` module constant, duplicated from `sources/atlas.py`'s own literal since `prescribe.py`'s AD-4 import-surface guard forbids importing `sources.atlas` directly). New test: `test_does_not_correlate_two_unrelated_findings_both_missing_a_feedstock_name`.

**Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- **336 passed** (full suite).

**Follow-up review recommendation (updated): false** -- narrow fix, covered by a dedicated regression test.

</intent-contract>
