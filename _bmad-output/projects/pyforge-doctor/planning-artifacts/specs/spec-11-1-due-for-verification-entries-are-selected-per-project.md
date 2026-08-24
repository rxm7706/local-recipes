---
title: 'Due-for-verification entries are selected, per project'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: '415595ef93c6c67dc07d41a788f483aedcb02ca3'
context: []
warnings: ['oversized']
baseline_revision: 'd682235b1f44cdd2245eae6e7273cb45318613ff'
---

<intent-contract>

## Intent

**Problem:** Tracked `deferred-work-ledger.md` entries are claims about code truth at authoring
time; nobody currently has a way to ask "which entries have never been re-checked, or were
re-checked too long ago" without enumerating ~400+ entries across 8 projects by hand.

**Approach:** Add a selector, `gather_due_for_verification`, that walks every project's tracked
ledger and returns exactly the `## DW-<id>`-headed entries with no `verified:` line, or a
`verified:` date older than a staleness threshold — one `Finding` per due entry, each tagged
with its owning project, mirroring `chain.py`'s existing `gather_deferred_work` shape exactly.

## Boundaries & Constraints

**Always:** Consider every ID'd entry regardless of `status:` (closed/done entries are not
exempt — the 2026-07-30 precedent found regressions among them too). Reuse `chain.TRACKED_REL`
and `chain._ENTRY_RE` rather than re-deriving the ledger path or heading regex. Tolerate a
missing per-project ledger silently (zero findings, not an error); isolate one project's read
failure from every other project's already-computed findings, same shape as
`_deferred_work_findings`. Accept an injectable "as of" date on the testable inner helper so
tests never depend on wall-clock `today()`. Every `Finding.evidence` carries a `project` key —
that is what "batched per project" means here. Status is always `WARN`, never `FAIL` — this
selector informs, it never gates.

**Block If:** None — the one open decision (CAP-1's staleness-threshold number) is resolved
below in Design Notes, not deferred to an execution-time halt.

**Never:** Select anonymous (heading-less) entries — that parser fix is a sibling Spec's
territory (`spec-deferred-work-visibility`'s CAP-4..7). Add a row to
`scripts/detectors.py`'s `_DOCTOR_SOURCE_TASKS` (closed-by-design to the ten Story-6.9
script-migration origins) or wire into `doctor check`'s self-check axis — both out of this
story's surface. Mutate a ledger file. Emit a `FAIL` status.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Never verified | Entry has no `verified:` line | One `Finding`, `evidence.reason="never-verified"` | No error expected |
| Stale | `verified:` date older than the threshold | One `Finding`, `evidence.reason="stale"`, `days_stale` set | No error expected |
| Fresh | `verified:` date within the threshold | No `Finding` for this entry | No error expected |
| Anonymous entry | Heading-less bullet entry | Ignored — never selected | No error expected |
| Closed/done entry | `status: done`, no `verified:` line | Selected same as an open entry | No error expected |
| No ledger for a project | `planning-artifacts/deferred-work-ledger.md` absent | Zero findings for that project | No error, no exception |
| Unreadable ledger | Project ledger raises on read | One isolated WARN finding for that project only | Other projects' findings unaffected |
| No projects tree | `_bmad-output/projects/` absent under target | One WARN "cannot be evaluated here" | Mirrors `gather_deferred_work`'s vacuous-target Finding |
| Fleet-wide none due | Every entry fresh or absent | One vacuous OK finding, never an empty tuple | No error expected |
| Malformed `verified:` date | Unparseable date text | Treated as `reason="never-verified"` | Never raises |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py:99` -- `Source` enum
  (closed taxonomy, extended by each new gather); add `DUE_FOR_VERIFICATION` here, mirroring
  `DEFERRED_WORK`'s own comment block.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:1335` (`TRACKED_REL`),
  `:1348` (`_ENTRY_RE`), `:1362` (`_entries`, the boundary-walk shape to mirror, not modify),
  `:2221` (`_deferred_work_findings`, the per-project isolation shape to mirror), `:2291`
  (`gather_deferred_work`, the DISPATCH-facing wrapper shape to mirror) -- new code lands
  alongside these.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py:149` (`REGISTRY`
  tuple), `:258` (`DEFERRED_WORK`'s row -- same `subject_station="marshal"` to mirror).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py:54` (`DISPATCH`
  dict).
- `pixi.toml:534` (`deferred-work-check` task -- the two-line pattern to mirror).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- the
  tmp_path real-file fixture pattern (`_write_tracked`, no mocks) to mirror in a new sibling
  test file.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- add
  `Source.DUE_FOR_VERIFICATION = "due-for-verification"` with a short comment naming Epic
  11/CAP-1 -- registers the closed-taxonomy member every file below keys off.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- add
  `DUE_FOR_VERIFICATION_STALENESS_DAYS`, a `_VERIFIED_RE` pattern, a `_verification(path)`
  boundary-walk helper mirroring `_entries()`, `_due_for_verification_findings(target, *,
  today=None)`, `_due_for_verification_message(item)`, and `gather_due_for_verification(target)`
  -- the selector itself, mirroring `gather_deferred_work`'s shape end to end.
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- add one
  `REGISTRY` row (`scope="repo"`, `subject_station="marshal"`, `owning_station="doctor"`) --
  mandatory for `Source`<->`REGISTRY` set-equality (`test_sources_registry.py`).
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` -- add
  `Source.DUE_FOR_VERIFICATION.value: chain.gather_due_for_verification` to `DISPATCH` --
  makes the selector independently runnable via `python -m pyforge.doctor.sources
  due-for-verification`.
- [x] `pixi.toml` -- add `[feature.local-recipes.tasks.due-for-verification-check]` mirroring
  `deferred-work-check`'s two-line shape -- the entrypoint named in Verification below.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py`
  -- new file, one test per I/O matrix row above, using the same tmp_path real-file fixture
  pattern as `test_sources_chain_deferred_work.py`.
- [x] (unplanned, required by closed-taxonomy invariant tests) `tests/unit/test_models.py`,
  `tests/unit/test_sources_dispatch.py`, `tests/meta/test_source_independence.py`,
  `src/pyforge/doctor/data/report-schema.json` -- updated the four pre-existing tests/schema
  that exhaustively pin the `Source` taxonomy in both directions, the same update every prior
  `Source` addition (6.4-6.8) required.

**Acceptance Criteria:**
- Given a tracked ledger entry with no `verified:` line, when the selector runs, then it returns
  exactly one `Finding` for that entry with `evidence.reason == "never-verified"`.
- Given a tracked ledger entry whose `verified:` date is more than
  `DUE_FOR_VERIFICATION_STALENESS_DAYS` days before the "as of" date, when the selector runs,
  then it returns exactly one `Finding` with `evidence.reason == "stale"` and the correct
  `evidence.days_stale`.
- Given a tracked ledger entry verified within the threshold, when the selector runs, then no
  `Finding` is returned for it.
- Given two projects, one with due entries and one fully fresh, when the selector runs, then
  only the due project's entries appear, each `Finding.evidence["project"]` naming its own
  project.
- Given a project with no `deferred-work-ledger.md` at all, when the selector runs, then that
  project contributes zero findings and no exception propagates.
- Given `_bmad-output/projects/` does not exist under target, when the selector runs, then it
  returns exactly one WARN `Finding` stating evaluation is impossible here.

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 1, medium 0, low 2)
- defer: 1: (high 0, medium 1, low 0)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[high]` `[patch]` Both Blind Hunter and Edge Case Hunter independently found that `_verification()` matched only the FIRST `verified:` line in an entry's span via `.search()`; since reconciliation appends a fresh `verified:` line rather than replacing the old one, an entry's staleness was pinned to its OLDEST re-check forever. Fixed to take the LAST match via `finditer()`; added a regression test (`test_entry_with_two_verified_lines_uses_the_most_recent_one`).
  - `[low]` `[patch]` The `due-for-verification-check` pixi task description hardcoded the literal number "30" for the staleness threshold, which would silently desync from `DUE_FOR_VERIFICATION_STALENESS_DAYS` if retuned later. Reworded to reference the constant by name instead of repeating its value.
  - `[low]` `[patch]` The Design Notes' and code comment's staleness-threshold rationale claimed "double the closest analog (14)" but 14×2=28, not 30 -- an arithmetic inconsistency in the stated reasoning (the chosen value of 30 itself was not wrong). Corrected to "roughly double ... rounded to a full month" in both the spec Design Notes and the mirrored `chain.py` comment.
  - `[medium]` `[defer]` No sanity bound on a far-future `verified:` date (e.g. a typo'd year) lets it parse cleanly and read as permanently fresh, silently exempting that entry from the sweep forever -- outside CAP-1's stated contract (only unparseable dates were in scope). Minted `DW-FU-11-1` in `deferred-work.md`.
  - `[low]` `[reject]` (x8) Eight findings (loose `verified:` regex anchoring; one `check` value covering two incompatible `evidence` shapes; a directory-shaped ledger path silently producing zero findings same as a missing one; speculative mid-loop-isolation test gap with no realistic trigger path; `projects_scanned`'s double-walk/undercount semantics; `subject_station="marshal"` on a fleet-wide check; `chmod(0o000)`-based unreadability tests; no visible dashboard/report-renderer update) were each verified against the mirrored `gather_deferred_work` precedent (or, for the dashboard finding, against Story 11.7's explicit ownership of that surface in the epic) and found to be either byte-identical inherited behavior this story was directed to mirror, or explicitly out of this story's scope by epic design -- not new defects introduced here.

### 2026-08-15 — Review pass (repair pass: deterministic-verification-gate fix)
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 0
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[low]` `[patch]` The `pixi.toml` `due-for-verification-check` task's description cited `Contract: spec-11-1-due-for-verification-entries-are-selected-per-project` -- unlike every other `Contract:` line in `pixi.toml`, which names something that resolves on disk today, this one named the story's own gitignored Tier-3 `implementation-artifacts/` draft spec, not yet promoted into a tracked `planning-artifacts/specs/` directory. Corrected to `Contract: spec-deferred-work-resolution-sweep CAP-1`, the real owning capability spec.
  - `[low]` `[patch]` This repair pass's own draft addition to `spec-pyforge-doctor/.memlog.md` mischaracterized `sources/__main__.py`'s docstring fix as "correction from 'ten' to no-longer-pinning-a-number" -- the docstring's opening sentence does drop "the ten", but a new second sentence still pins a live count ("Eleven total today"). Corrected the memlog prose to describe the count as relocated, not eliminated.
  - `[low]` `[reject]` (x7) A claimed dangling `DW-FU-11-1` deferred-work id (verified FALSE on direct inspection -- the id exists, fully written, in this project's Tier-3 `implementation-artifacts/deferred-work.md`; the reviewer's search evidently missed the symlinked/gitignored file) plus six documentation-quality nitpicks (unverifiable bidirectional cross-memlog references, subjective precedent-language framing, a pixi.toml content claim already independently verified accurate by this session, a misread "nine governed paths" undercount that in fact correctly scopes to this spec's own files, an unitemized "22 tests" count, and a true-but-non-actionable observation that the mechanical `spec_surface_reconcile.py` gate does not itself vouch for prose accuracy) were each checked directly against the live repo and found to be noise, not real defects.

## Design Notes

- **Staleness threshold, resolved.** No fleet precedent judges "code-claim re-verification
  cadence" (checked: warden's `DEFAULT_FEED_MAX_AGE_DAYS=7`, `DB_MAX_AGE_DAYS=7`,
  `_REGISTRY_MAX_AGE_DAYS=180`, `waiver_default_expiry_days=14` — none fits). The Spec's own
  Open Questions leave the number undecided; resolved here as
  `DUE_FOR_VERIFICATION_STALENESS_DAYS = 30`, a named `chain.py` constant — roughly double the
  closest human-judgment analog (`waiver_default_expiry_days=14`), rounded to a full month,
  since re-verifying 400+ entries fleet-wide is heavier than one waiver review. Retune later
  without touching call sites.
- `_entries()` stays untouched — a verbatim port with a stable contract. The new
  `_verification()` helper duplicates its ~10-line boundary-walk shape rather than extracting a
  shared primitive from a function documented as "verbatim from the original."
- A malformed `verified:` date is treated as `"never-verified"` (fail toward re-checking, never
  a crash) — one bad date must not sink that project's other findings.
- `DISPATCH`'s docstring frames itself as "the ten ported Doctor sources" (Story 6.9's set).
  This addition is the first genuinely new (non-ported) member, same `Callable[[Path],
  tuple[Finding, ...]]` shape — extending `DISPATCH` is correct reuse, not scope creep; update
  the now-stale "ten" in its docstring alongside the new entry.

## Verification

**Commands:**
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py -v`
  -- expected: all new tests pass.
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py -v`
  -- expected: still passes (REGISTRY/Source set-equality holds with the new member).
- `pixi run -e local-recipes due-for-verification-check` -- expected: runs against this repo's
  live 8 project ledgers, prints one WARN line per due entry, exits 0.

## Auto Run Result

**Summary.** The prior dev-auto session's implementation (commit `d682235b1f`) and its own
review pass were already complete and correct -- `gather_due_for_verification` shipped, code
review found and fixed one high-severity bug, all tasks were marked `[x]`. What failed was
bmad-loop's own repo-wide deterministic post-review verify gate, `python
scripts/spec_surface_reconcile.py`: nine `pyforge-doctor`-governed files plus one
`pyforge-steward`-governed file (`pixi.toml`) had changed without their owning specs'
`.memlog.md` moving to name them, and the `.spec-surface-baseline.json` had not been re-stamped.
This resume session repaired exactly that gap, then ran a full review pass over the repair
itself, without touching the intent contract or any production/test code.

**Files changed, this session:**
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`
  -- new entry naming all nine doctor-governed paths this story changed, plus a repair-pass
  review addendum.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md`
  -- cross-package reconciliation entry naming `pixi.toml`'s change (a doctor story touching a
  steward-governed file), plus a repair-pass review addendum.
- `pixi.toml` -- one-line fix: the new `due-for-verification-check` task's `Contract:` reference
  corrected from a not-yet-promoted Tier-3 spec path to the real owning capability spec,
  `spec-deferred-work-resolution-sweep CAP-1`. No dependency or behavior change;
  `environment.yaml` re-diffed byte-identical.
- `scripts/.spec-surface-baseline.json` -- re-stamped scoped to exactly the two affected specs
  (`--write-baseline --spec pyforge-doctor/spec-pyforge-doctor --spec
  pyforge-steward/spec-python-agent-platform`), twice (once for the memlog reconciliation, once
  more after the review-pass `pixi.toml` fix). Verified both times: only the two intended keys
  changed, memlog hash moved on both, exactly the expected file hashes updated, zero unrelated
  keys touched.

**Review findings.** Two review passes total (see Review Triage Log): the original story's own
pass (patch 3 / defer 1 / reject 8, already landed in `d682235b1f`) and this session's
repair-pass review (patch 2 / defer 0 / reject 7). Both patches from this pass were applied: the
`pixi.toml` `Contract:` reference fix above, and a correction to this session's own draft memlog
prose (a docstring-fix description that was itself slightly inaccurate). One reviewer-claimed
defect (a dangling `DW-FU-11-1` deferred-work id) was directly verified FALSE -- the id exists,
fully written, in the project's gitignored Tier-3 `implementation-artifacts/deferred-work.md`;
the reviewing subagent's search evidently missed the symlinked file. No new `defer` items were
minted.

**Verification performed (this session, all green):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 955 passed, 2 skipped (run twice,
  before and after the review-pass patches; unchanged both times -- no production/test code was
  touched this session).
- `python scripts/spec_surface_reconcile.py`: `OK: every tracked file governed or allowlisted;
  no drift.` (rc=0; was rc=1/FINDINGS(10) at session start).
- `pixi run -e local-recipes pytest .../test_sources_chain_due_for_verification.py -v`: 22
  passed.
- `pixi run -e local-recipes pytest .../test_sources_registry.py -v`: 18 passed.
- `pixi run -e local-recipes due-for-verification-check`: rc=0, 310 lines of WARN output across
  the fleet's 8 project ledgers (never FAIL, per the selector's own contract).
- `pixi project export conda-environment -e build` re-diffed against committed
  `environment.yaml`: byte-identical (the `pixi.toml` edit is a comment-only fix, adds no
  dependency).

**Residual risk.** None identified. This was a bookkeeping/reconciliation repair plus one
comment-only `pixi.toml` correction; the story's own production code, tests, and intent
contract are byte-identical to the prior session's landed and reviewed state.

