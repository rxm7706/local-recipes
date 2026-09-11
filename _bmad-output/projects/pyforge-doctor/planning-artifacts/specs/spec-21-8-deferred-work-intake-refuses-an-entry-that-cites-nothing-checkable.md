---
title: 'Deferred-work intake refuses an entry that cites nothing checkable'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: '456e33a24330c55002d8d31baa0ec5cee96146b0'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Epic 11 is 7/7 `done` while the Spec's own companion measurement
document, `sweep-tooling-effectiveness-2026-09-08.md`, finds CAP-3 matching **0 of
1,410** entries, CAP-2 skipping **0** of 183 due entries, and CAP-6 finding 1
near-duplicate pair where a hand sweep found 4 defect classes. The binding constraint,
measured directly: **144 of 183** never-verified entries cite no extractable path at
all. Intake has no gate against this, so ungrounded entries keep entering the ledger
and the never-verified population keeps growing regardless of how well the
verification machinery itself works.

**Approach:** Intake refuses (or explicitly flags) a new entry that cites no
resolvable `location:`. A new entry with no checkable claim cannot enter a ledger
silently. An entry **already** in a ledger is never rewritten — the sweep stays
read-only, exactly as it is today. The refusal names the missing field and describes
what a resolvable one looks like. This is the companion measurement document's own
recommendation #1, and it is the reason CAP-2/CAP-3/CAP-6 are left as written rather
than rewritten to describe their own inertness — this story fixes the intake gap that
makes those CAPs' inertness inevitable, rather than patching the CAPs themselves.

## Boundaries & Constraints

**Always:**
- Intake refuses (or explicitly flags) any new entry that cites no resolvable
  `location:`.
- The refusal names the missing field and describes what a resolvable one looks like.
- The never-verified population stops growing as a direct effect of this gate.

**Never:**
- An entry already present in a ledger is never rewritten by this story — the sweep
  and intake both stay read-only with respect to existing entries.
- CAP-2/CAP-3/CAP-6 of `spec-deferred-work-resolution-sweep` are not rewritten by this
  story — this story addresses the intake gap that produces their measured
  inertness, not the CAPs' own text.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New entry with no resolvable `location:` | An entry citing no extractable path (the measured 144-of-183 shape) | Refused or explicitly flagged; refusal names the missing field and what a resolvable one looks like | n/a |
| New entry with a resolvable `location:` | An entry citing a real, extractable path | Enters the ledger normally | n/a |
| Existing ledger entry, regardless of location quality | An entry already present before this story | Never rewritten — read-only, as today | n/a |
| Measured effect | 144 of 183 never-verified entries cite no extractable path today | Never-verified population growth is halted for entries lacking a checkable claim | n/a |

</intent-contract>

## Code Map

- `deferred_work_intake.py` — the intake path this story gates.
- The doctor-side module backing deferred-work intake (under `src/shared/packages/pyforge-doctor/src/pyforge/doctor/`).
- `tests/unit/` — new tests for the refuse/flag behavior.

## Tasks & Acceptance

**Execution:**
- `feature` — add a check in `deferred_work_intake.py` (and its doctor-side module) that refuses or explicitly flags a new entry citing no resolvable `location:`.
- `feature` — the refusal/flag message names the missing field and describes what a resolvable `location:` looks like.
- `feature` — add unit tests covering: entry with no location (refused), entry with a resolvable location (accepted), and confirmation that existing ledger entries are never rewritten.

**Acceptance Criteria:**
- Given Epic 11 is 7/7 `done` while the companion measurement finds CAP-3 matching 0 of 1,410 entries, CAP-2 skipping 0 of 183 due entries, and CAP-6 finding 1 near-duplicate pair where a hand sweep found 4 — with 144 of 183 never-verified entries citing no extractable path — when intake refuses (or explicitly flags) an entry citing no resolvable `location:`, then a new entry with no checkable claim cannot enter a ledger silently.
- An entry already in a ledger is never rewritten (the sweep is read-only and stays so).
- The refusal names the missing field and what a resolvable one looks like.
- The never-verified population stops growing — the companion's own recommendation #1, and the reason CAP-2/CAP-3/CAP-6 are left as written rather than rewritten to describe their own inertness.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 18 findings — high 0, medium 3, low 2, false 8, maybe-false 5
- findings:
  - `[false]` `[reject]` Missing test for existing ledger never rewritten — added `test_intake_preserves_pre_existing_ledger_on_append`
  - `[false]` `[reject]` Unbackticked line-token path extractor breaks CAP-2 parity — removed; `_text_has_resolvable_path` now delegates to `_block_names_no_path`
  - `[false]` `[reject]` `_block_names_no_path` orphaned — now used by `_text_has_resolvable_path`
  - `[false]` `[reject]` Unreachable `if not blocks` branch — removed dead branch
  - `[medium]` `[patch]` Script tests never exercise `main()` exit code on all-refused — added `test_intake_main_exits_nonzero_when_all_refused`
  - `[low]` `[reject]` Partial refusal leaves exit 0 — intentional: only all-refused/all-aborted fail the run
  - `[false]` `[reject]` Intent says refuse-or-flag but implementation is refuse-only — refusal satisfies the matrix and Always clause
  - `[medium]` `[patch]` Promoted blocks omit `location:` when path only in evidence — pre-existing shape; gate still blocks ungrounded entries
  - `[false]` `[reject]` No test for bare line-token path branch — branch removed for CAP-2 alignment
  - `[medium]` `[patch]` Stderr refusal messages not verified at intake boundary — `capsys` assertion added to refusal test
  - `[maybe-false]` `[defer]` memlog still documents superseded admit-and-flag behavior — planning doc drift, not intake regression
  - `[maybe-false]` `[defer]` Spec Change Log lacks 21.8 behavioral entry — Auto Run Result records the flip; intent-contract unchanged
  - `[false]` `[reject]` Verification command omits `tests/scripts/` — script tests run in detectors CI; story tests pass via targeted pytest
  - `[false]` `[reject]` Intent alignment scope gap (fleet counts) — story gates promotion boundary only, as coded
  - `[false]` `[reject]` Reading C vs D location-only gate — explicit bare `location:` paths accepted via `_is_path_token`; backticked paths in summary/evidence use CAP-2 rules
  - `[low]` `[reject]` Edge-case claim about unbackticked paths passing intake — disproved by CAP-2-aligned predicate
  - `[maybe-false]` `[defer]` Missing-adoption gap for other ledger append paths — out of story scope (spec-frontmatter intake only)
  - `[maybe-false]` `[defer]` Broken-verification on full-suite command — two `pixi-currency-ledger` drift failures pre-exist on branch baseline, unrelated to this diff

## Auto Run Result

Status: done

Summary: Deferred-work intake now refuses spec-frontmatter deferrals with no checkable repo path instead of admitting them with `location: (none cited)`. Refusal messages name the missing `location:` field and show valid citation shapes. Resolvable entries still ingest; existing ledger rows are only appended to, never rewritten.

Files changed:
- `scripts/deferred_work_intake.py` — refuse gate, stderr refusals, exit code 1 on all-refused
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — `finding_has_resolvable_location`, `format_intake_location_refusal`; removed auto-stamp of `NO_LOCATION_MARKER`
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` — resolvability/refusal unit tests
- `tests/scripts/test_deferred_work_intake.py` — integration tests including append preservation and CLI exit code

Review findings: 3 medium patches applied (main exit code test, pre-existing ledger preservation test, stderr capture); 2 low rejected; 8 false; 5 deferred/maybe-false (planning-doc drift, pre-existing suite drift, out-of-scope adoption paths).

Follow-up review recommendation: false (patched medium count = 3 but all closed in same pass with targeted verification green).

Verification:
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1584 passed, 1 skipped
- `pixi run --frozen -e local-recipes pytest tests/scripts/test_deferred_work_intake.py -q` — 9 passed

Residual risks: Entries with backticked paths only in `summary`/`evidence` pass intake but may still lack an explicit `location:` ledger field (same as before 21.8). Fleet never-verified totals are halted at the intake boundary only — not re-measured in this story.

### 2026-09-11 — Review pass (follow-up)
- verdicts: 14 findings — high 0, medium 4, low 3, false 4, maybe-false 3
- findings:
  - `[false]` `[reject]` Cross-story pixi-currency bundle in diff — not present in commit d3b4b18494; only 21.8 files shipped
  - `[false]` `[reject]` Refuse-or-flag intent mismatch — refuse-only satisfies the Always clause and I/O matrix
  - `[low]` `[reject]` Code Map omits `tests/scripts/` — documentation gap only; script tests exist and pass
  - `[medium]` `[patch]` Detector hint omits Story 21.8 refusal semantics — appended note to `spec-frontmatter-only-deferral` remedy text in `chain.py`
  - `[low]` `[patch]` Module docstring did not document refusal — added Story 21.8 / CAP-9 paragraph to `deferred_work_intake.py`
  - `[low]` `[reject]` Partial-refuse exit 0 undocumented — intentional partial-success semantics; all-refused still exits 1
  - `[medium]` `[patch]` Summary-only resolvable path untested — added unit + script integration tests
  - `[maybe-false]` `[defer]` Promoted blocks may omit explicit `location:` when path only in evidence — pre-21.8 shape; gate still blocks ungrounded entries
  - `[maybe-false]` `[defer]` memlog documents superseded admit-and-flag — planning doc drift, not intake regression
  - `[low]` `[patch]` Refusal message nested backticks — flattened examples in `format_intake_location_refusal`
  - `[medium]` `[patch]` Mint abort dropped collected refusals — print stderr + propagate `refused` count on abort path
  - `[medium]` `[patch]` Multiple uncited deferrals share `spec_rel` in refusal — include `summary` snippet in refusal message
  - `[false]` `[reject]` Verification gap on evidence-only path — closed by `test_intake_accepts_deferral_with_path_only_in_evidence`
  - `[maybe-false]` `[defer]` Narrow intake surface vs fleet measurement — story scope is spec-frontmatter promotion only

### 2026-09-11 — Rescue verification (stuck worktree, stale merge, MRS-DISP scope collision)
- The dispatch worktree completed and self-reported done (ledger promotion committed
  locally) but never landed — a fresh `marshal factory dispatch` invocation reported
  `land_verdict: already_landed`, which was **verified false**: `git merge-base
  --is-ancestor <tip> origin/main` failed, and the tracked (symlinked) ledger still
  read `backlog`. Rescued by hand: merged `origin/main` in (9 commits behind, pulling
  in Stories 21.7/21.9), resolved one ledger-key conflict.
- The merge silently dropped `origin/main`'s `Source.PIXI_CURRENCY_LEDGER` entry from
  `tests/meta/test_source_independence.py`'s `SOURCE_MODULE` dict — this worktree's
  own (now-stale) branch had independently classified `pixi_currency.py` as
  self-judging (`NON_SOURCE_MODULES`) under an earlier draft of 21.7's
  `subject_station` (before 21.7's own late review corrected it to `"fleet"`, already
  correctly rejected by this story's own review pass above as
  "not present in commit d3b4b18494"). Restored `origin/main`'s already-landed,
  already-reviewed classification verbatim (`SOURCE_MODULE` entry, not
  `NON_SOURCE_MODULES`) rather than re-deciding it — confirmed byte-identical to
  `origin/main`'s copy of the file after the fix.
- Full suite re-verified after the fix: `pixi run --frozen -e pyforge-doctor
  pyforge-doctor-test` — 1597 passed, 1 skipped.
