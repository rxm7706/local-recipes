<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Tri-state, individually addressable checks (FR-2)'
type: 'feature'
created: '2026-07-30'
status: 'done'
baseline_revision: '1ed5f5e37203963ec04a621142eaab70030f9aec'
final_revision: '28b991ff0a260d0ded33a17ff2c2967757c1b2d5'
review_loop_iteration: 0
followup_review_recommended: false
context: [
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py',
  '{project-root}/src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py',
  '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
  '{project-root}/_bmad-output/implementation-artifacts/deferred-work.md',
]
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `doctor check`'s only check source (Story 1.2's warden wrapper) has no way to enumerate its named checks without running them, and no way to run one check in isolation — FR-2 requires both an introspection capability and per-check filtering, neither of which exists yet.

**Approach:** Add `doctor.checks.registry`, a pure library module with a static `CheckSpec` catalog (`list_checks()`, no execution) and a filter-after-run helper (`gather_one()`, proven identical to running the full suite and filtering). CLI flag wiring (`--list`, `--engines <name>`) is Story 1.5's job, per epic-1-context's Cross-Story Dependencies — this story delivers the model Story 1.5 wires in.

## Boundaries & Constraints

**Always:**
- `list_checks(category=None) -> tuple[CheckSpec, ...]` is pure and static — it never calls `sources.warden.gather()`, `run_doctor_checks`, or any subprocess; a test proves this by making the underlying call raise if invoked.
- `gather_one(category, name, target) -> Finding | None` runs the named category's real gather (e.g. `sources.warden.gather(target)`) and returns the `Finding` whose `check == name`, or `None` if no such check ran — literally a filter over the full-suite result (AC3's equivalence), never a separate/duplicated lookup path.
- The static "engines" catalog (`deptry`, `osv-scanner`, `osv-db`, `kev-feed`, `epss-feed`, `endoflife-feed` — `pyforge.warden.engines.run_doctor_checks`'s own documented fixed order) is cross-checked by a test that calls the real, unmocked `sources.warden.gather()` once and asserts the name sets match — catching future drift instead of silently going stale.
- Every `CheckSpec`/`Finding` this module touches stays inside the existing closed `DoctorStatus`/`Source` contract (Story 1.1) — no new `Source` or `DoctorStatus` member.

**Block If:** `pyforge.warden.engines.run_doctor_checks`'s documented fixed check order/names (deptry, osv-scanner, osv-db, kev-feed, epss-feed, endoflife-feed) have changed since this spec's investigation — re-verify against the live function body before implementing; if it no longer matches, HALT and name the mismatch.

**Never:**
- Never modify `sources/warden.py`'s `gather()` OK/FAIL mapping or promote any warden check to `WARN` — resolved design decision (see Design Notes): out of scope for this story.
- Never modify `doctor.models`, `doctor.verdict`, or the `DoctorReport` schema — Story 1.1 froze that contract; this story is a producer only.
- Never add the `--list`/`--engines <name>` CLI flags or any `argparse` dispatch — out of scope, Story 1.5's job (epic-1-context.md Cross-Story Dependencies).
- Never let `list_checks()` execute a real check to build its catalog — introspection must be free of side effects (FR-2's explicit "without running them").

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| List all checks | `list_checks()` | Returns the 6 known `engines`-category `CheckSpec`s, in `run_doctor_checks`' documented order | No error; underlying gather never invoked |
| List filtered by known category | `list_checks(category="engines")` | Same 6 entries as unfiltered (today's only category) | No error expected |
| List filtered by unknown category | `list_checks(category="env")` | Empty tuple — `env` has no registered checks until Story 1.4 lands | No error; not an exception |
| Run one named check | `gather_one("engines", "osv-scanner", target)` | Equals the `check == "osv-scanner"` `Finding` from a full `sources.warden.gather(target)` call | No error expected |
| Run an unknown check name | `gather_one("engines", "not-a-real-check", target)` | `None` | No exception, no fabricated `Finding` |
| Run with an unknown category | `gather_one("bogus", "x", target)` | Raises `ValueError` naming the unsupported category | Caller (Story 1.5's CLI) turns this into a usage error later |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py` -- `gather(target)`, the only existing check-producing source; `gather_one`'s "engines" category delegates here.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` (`run_doctor_checks` -- cited by name; the earlier line-number citations rotted twice) -- source of the 6 fixed check names this story's static catalog mirrors; re-verify the order/names against this before writing the catalog (this spec's Block If).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- `Finding`, `DoctorStatus` -- the already-frozen contract `gather_one` returns against, unchanged.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_warden.py` -- the monkeypatch-`run_doctor_checks` idiom and the "live equivalence" real-call idiom to mirror for this story's tests.
- `_bmad-output/implementation-artifacts/deferred-work.md` (spec-1-2 entry, "Warden's ok-with-caveat...") -- the WARN-promotion question this story explicitly scopes out (see Design Notes).

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/__init__.py` -- new empty package marker (mirrors `sources/__init__.py`).
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py` -- `CheckSpec(category: str, name: str)` frozen dataclass; `list_checks(category: str | None = None) -> tuple[CheckSpec, ...]` returning the static "engines" catalog (optionally filtered, empty tuple for an unknown category); `gather_one(category: str, name: str, target: Path) -> Finding | None` dispatching to `sources.warden.gather(target)` for `category == "engines"` and filtering by `finding.check == name`, raising `ValueError` for any other category.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_checks_registry.py` -- covers the full I/O matrix: list all/filtered/unknown-category, the no-execution proof (monkeypatch `run_doctor_checks` to raise, assert `list_checks()` still succeeds), `gather_one` found/not-found/unknown-category-raises, and the live drift-detection cross-check (real, unmocked `sources.warden.gather()` call compared against the static catalog's names).

**Acceptance Criteria:**
- Given `list_checks()`, when called, then it returns exactly the 6 known "engines" `CheckSpec`s without invoking `sources.warden.gather()` or any subprocess.
- Given `gather_one("engines", "osv-scanner", target)`, when called, then its result equals the `check == "osv-scanner"` `Finding` filtered from a full `sources.warden.gather(target)` call under the same conditions.
- Given `gather_one("engines", "not-a-real-check", target)`, when called, then it returns `None` with no exception.
- Given `gather_one("bogus-category", "x", target)`, when called, then it raises `ValueError` naming the unsupported category.
- Given the static "engines" catalog, when cross-checked against a live (unmocked) `sources.warden.gather()` call, then the two check-name sets are identical.
- Given any `Finding` this module returns, when inspected, then its `status` is one of the existing closed `DoctorStatus` members (Story 1.1's contract) — no new status/source introduced by this story.

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 1: (high 0, medium 1, low 0)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `low` `patch` `gather_one`'s docstring illustrated its filter-equivalence with `next(f for f in ... if f.check == name), None)` — a stray unmatched paren that isn't valid Python if copy-pasted. Fixed to `next((f for f in ... if f.check == name), None)`.
  - `low` `patch` The comment above `_ENGINE_CHECK_NAMES` cited `engines.py` lines "706-786" for `run_doctor_checks`, but the function actually spans 706-794 (786 lands mid-way through the endoflife-feed check, not the function's end) — corrected the citation.
  - `medium` `patch` No test exercised `gather_one` against a degraded (single-sentinel) `sources.warden.gather()` result — the realistic scenario of an operator running one named check while warden itself is broken had zero coverage. Added `test_gather_one_returns_none_when_gather_degrades_to_sentinel_finding`, pinning today's actual, spec-mandated (AC3 filter-semantics) `None` return.
  - `medium` `patch` `gather_one`'s category guard (`if category != "engines"`) and `_CATALOG`'s registered keys had no enforced relationship — a future category added to `_CATALOG` (Story 1.4's `"env"`) without a matching dispatch branch here would silently misroute to `warden_source.gather()` if the guard were naively changed to check `_CATALOG` membership instead (a fix considered and rejected as worse than the status quo). Added an explanatory comment making the non-derivation deliberate and documented, so a future implementer isn't surprised and doesn't "fix" it into a silent misroute.
  - `low` `patch` The live drift-detection test compared `set`s of check names, so a same-names-different-order drift (a reorder without a rename) would pass despite the module's own docstring claiming to mirror `run_doctor_checks`'s documented FIXED order. Strengthened to an order-preserving tuple comparison.
  - `medium` `defer` `gather_one` returns bare `None` when the whole category's gather degrades to one sentinel failure `Finding`, rather than surfacing that sentinel's reason — spec-compliant (AC3's literal filter semantics) but a real UX gap for whichever story renders this to an operator. Logged in `deferred-work.md` for Story 1.5's CLI-wiring pass to decide.
  - `low` `reject` (x7, noise/speculative/already-settled, dropped silently): the drift test's inability to distinguish "warden renamed a check" from "warden not installed" if the `pyforge-warden` path-dependency coupling ever loosens is speculative and matches `test_sources_warden.py`'s own accepted live-equivalence pattern; `gather_one` paying the full check-suite cost even for a non-matching name is exactly what this spec's Always clause mandates ("never a separate/duplicated lookup path") — the suggested early-exit-via-catalog "fix" would violate that constraint; the tri-state/WARN-reachability critique re-litigates this spec's own explicit, already-documented Design Notes resolution (Story 1.4 is the designated live WARN producer); `CheckSpec` omitting a `Source` field is speculative scope creep with no current consumer (deliberately thin, per the code's own docstring rationale); no caching/memoization discussion is speculative with no repeated-call consumer yet (Story 1.5 doesn't exist); the "PURE and STATIC" claim being "under-proven" by one negative test is unfounded — the function has no other I/O surface to test against; `list_checks()` raising `TypeError` for an unhashable (type-contract-violating) `category` argument tests a caller already violating the documented `str | None` signature, with no precedent for defensive runtime type-guarding elsewhere in this codebase.

### 2026-07-30 — Review pass (follow-up, fresh pass on `done` spec)
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 2, low 9)
- defer: 1: (high 0, medium 1, low 0)
- reject: 1: (high 0, medium 0, low 1)
- addressed_findings:
  - `medium` `patch` The addressable-name and listed-name sets disagree in the direction the first pass never covered: `gather_one("engines", "pyforge-warden", target)` returns the degradation sentinel — a name `list_checks()` never advertises — with zero tests or docs acknowledging it (both reviewers flagged this independently). Pinned with `test_gather_one_can_address_the_degradation_sentinel_by_name` and documented in `gather_one`'s docstring; the Story 1.5 CLI-exposure decision went to the ledger (see defer).
  - `medium` `patch` The `_CATALOG`↔`gather_one`-dispatch coherence invariant was enforced by a comment, not a test (both reviewers). Added `test_every_cataloged_category_is_dispatchable_by_gather_one` — Story 1.4 registering "env" without a dispatch branch now fails a test instead of relying on the implementer reading prose.
  - `low` `patch` `test_gather_one_unknown_category_raises_value_error` ran with the real `run_doctor_checks` unpatched (a gather-first refactor would silently start real subprocesses in a unit test) and its `match` accepted any ValueError echoing the input. Added the `_boom` monkeypatch and tightened the match to the message shape.
  - `low` `patch` The module docstring claimed the drift test "diffs the two check-name sets" while promising rename/REORDER detection — the set-diff mechanism can't catch a reorder; the test is actually an order-preserving tuple comparison (first pass strengthened the test but not the prose). Docstring corrected.
  - `low` `patch` When the drift test fails because warden degraded in the test environment, its assertion diff read exactly like catalog drift (both reviewers). Added a sentinel pre-check that `pytest.fail`s with the sentinel's own message, separating the two diagnoses.
  - `low` `patch` The rot-prone cross-package line citation ("engines.py lines 706-794") was baked in again after already rotting once this story, and the spec's Code Map still carried the stale "706-786". Both now cite `run_doctor_checks` by name only.
  - `low` `patch` Two tests duplicated the expected-specs derivation verbatim; extracted a single `_EXPECTED_ENGINE_SPECS` constant (the test file's own copy of the six names is deliberately kept — see reject).
  - `low` `patch` `test_list_checks_unknown_category_returns_empty_tuple_no_exception` asserting `list_checks("env") == ()` was an unannounced time bomb for Story 1.4's implementer. Labeled as a deliberate tripwire pointing at the dispatch-coherence test.
  - `low` `patch` `gather_one` had zero live (unmocked) coverage — AC2's filter equivalence was proven only under monkeypatch. Added `test_live_gather_one_equivalence_with_real_gather`, mirroring the sibling file's established live-equivalence idiom.
  - `low` `patch` The ValueError said "unknown check category" for `env` — a category this module's own docstring names as known-but-unregistered — and named no supported category, forcing Story 1.5 to hardcode the valid set again. Reworded to `unsupported check category: {category!r} (categories with a wired gather: 'engines')`, matching the spec matrix's own "unsupported" wording.
  - `low` `patch` `gather_one`'s `target` parameter was semantically undocumented (what it means, whether it affects check names). Docstring now states it's forwarded verbatim and never affects which names exist.
- deferred: `medium` — Story 1.5 must decide `--engines <name>` validation semantics given the sentinel name is gatherable but unlisted (complement of the first pass's degraded-to-`None` entry); appended to `deferred-work.md` as a NEW entry per the orchestrator's constraint.
- rejected: `low` — "the six check names exist as three hand-maintained copies": the test file's copy is deliberate independence pinning (importing registry's tuple would make the catalog tests tautologies — now stated in a comment), and the registry copy IS the design (hand-maintained mirror, per Design Notes); only the verbatim assertion-body duplication was real, and was patched above.

## Design Notes

**Resolved: WARN-promotion for warden checks is out of scope here.** `deferred-work.md`'s spec-1-2 entry asks whether warden's ok-with-caveat states (stale-but-optional feeds, air-gapped) deserve `WARN` promotion before the report contract hardens, naming it "Story 1.3's tri-state design decision." Story 1.3's own epics.md ACs, however, only require the tri-state *model* (introspection + per-check filtering) — they don't mandate a specific status re-mapping for any source. Story 1.4's own AC already names `status=warn_or_fail` for the new env-hygiene check, making Story 1.4 — not this one — the epic's designated live `WARN` producer. Touching Story 1.2's already-shipped, three-times-reviewed `gather()` mapping here would be unrequested scope creep against a hardened file; left untouched.

**Why the catalog is hand-maintained, not queried:** no warden API returns check names without running them, and AD-1's import allowlist sanctions only `run_doctor_checks` itself (no metadata-only sibling function exists to import instead). The static list is therefore Doctor's own duplicate of `run_doctor_checks`'s documented order, safety-netted by a test that calls the real function once and diffs the name sets — any future warden rename/reorder fails that test loudly rather than letting `--list` silently drift.

```python
_ENGINE_CHECKS: tuple[CheckSpec, ...] = tuple(
    CheckSpec(category="engines", name=n)
    for n in ("deptry", "osv-scanner", "osv-db", "kev-feed", "epss-feed", "endoflife-feed")
)

def gather_one(category: str, name: str, target: Path) -> Finding | None:
    if category != "engines":
        raise ValueError(f"unknown check category: {category!r}")
    return next((f for f in warden_source.gather(target) if f.check == name), None)
```

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: full unit + meta suite passes (this worktree's path is well under the pixi-build-python panic threshold recorded in `deferred-work.md`, per Story 1.2's identical successful run).
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src:src/shared/packages/pyforge-warden/src python3 -m pytest src/shared/packages/pyforge-doctor/tests -q` -- expected: full suite green, substitute verification if the pixi task cannot run.

**Actual results (2026-07-30):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- **115 passed** (pre-review), **116 passed** (post-review, one new test added). No `pixi-build-python` panic; this worktree's root is well under the recorded threshold.
- Follow-up review pass (same day): **119 passed** after the three review-driven tests landed (sentinel addressability pin, catalog-dispatch coherence tripwire, live `gather_one` equivalence).

## Auto Run Result

**Run 2 (2026-07-30, fresh follow-up review pass on a `done` spec):**

- **Summary:** No new implementation — this run re-reviewed Story 1.3's already-shipped registry (commit `cc0da9d847`) with fresh Blind Hunter + Edge Case Hunter passes and applied 11 hardening patches (2 medium, 9 low), all confined to `checks/registry.py` docs/messages and its test file. The only behavior-visible change is the unsupported-category `ValueError` message text; everything else is documentation, comments, and 3 new tests.
- **Files changed:**
  - `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py` — docstring corrections (drift-test mechanism, `target` semantics, sentinel-addressability asymmetry), rot-proof citation, reworded `ValueError` naming the supported category.
  - `src/shared/packages/pyforge-doctor/tests/unit/test_checks_registry.py` — 3 new tests (sentinel-name addressability pin, catalog↔dispatch coherence tripwire, live `gather_one` equivalence), `_boom`-guarded + shape-matched unknown-category test, drift-test degradation guard, `_EXPECTED_ENGINE_SPECS` dedup, tripwire comments.
  - `deferred-work.md` — one NEW entry appended (Story 1.5's `--engines` name-validation decision); no existing entries touched, per the orchestrator's constraint.
- **Review breakdown:** 15 raw findings (12 adversarial + 3 edge-case) deduplicated to 13: 11 patched, 1 deferred (medium — the sentinel-name CLI-exposure decision, complement of the first pass's degraded-to-`None` entry), 1 rejected (the "three copies of the six names" framing — two of the copies are deliberate). 0 intent_gap, 0 bad_spec.
- **Follow-up review recommendation:** false — the pass's changes are review-driven test/doc hardening plus one error-message string; no API, contract, or behavior change worth an independent pass.
- **Verification:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` → **119 passed** (was 116), no `pixi-build-python` panic.
- **Residual risks:** the catalog-dispatch coherence tripwire will intentionally go red when Story 1.4 registers `"env"` (as will the labeled env-empty-tuple tripwire) — both now carry comments directing that implementer; the live tests still assume two consecutive live gathers agree (the sibling file's established idiom).

