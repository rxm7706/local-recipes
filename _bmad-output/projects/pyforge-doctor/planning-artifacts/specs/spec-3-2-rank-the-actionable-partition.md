---
title: 'Rank the actionable partition'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-3-1-partition-findings-by-actionability.md',
  '{project-root}/.claude/skills/conda-forge-expert/scripts/behind_upstream.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py',
]
warnings: []
baseline_revision: 'HEAD at Story 3.2 start (after Story 3.1 landed)'
---

<intent-contract>

## Intent

**Problem:** Story 3.1's `partition()` sorts Findings into buckets but doesn't order the `ACTIONABLE` bucket — an operator staring at ten actionable Findings still has to manually decide what to fix first.

**Approach:** `pyforge.doctor.prescribe.rank(partitioned) -> tuple[RankedPrescription, ...]` — orders exactly the `ACTIONABLE` partition (BLOCKED/ACCEPTED_RISK are excluded from ranking entirely; Story 3.4's CLI layer still reports them, unranked) by a four-level sort key: severity, KEV flag, EPSS score, blast-radius tier (reusing `behind-upstream`'s own patch/minor/major classification, reimplemented as a pure function per AD-4 since `doctor.prescribe` cannot call out to it). Every `RankedPrescription` carries a `rank_factors` dict naming which signals fired — never a bare integer.

## Boundaries & Constraints

**Always:**
- `rank()` stays pure (AD-4) — no new imports beyond the already-sanctioned surface plus `re` (stdlib; see Design Notes for why not `packaging`).
- Sort precedence, highest priority first: (1) severity (`FAIL` > `WARN` > `OK`), (2) KEV flag, (3) EPSS score, (4) blast-radius tier with `patch` ranking ABOVE `minor` ABOVE `major` (Story 3.2 AC3's own explicit ordering — a smaller/quicker fix wins the tiebreak, not a bigger one).
- `rank_factors` is always a dict with exactly the keys `{"kev", "epss", "blast_radius"}` — `epss` is `None` when no evidence carries a numeric EPSS score (never coerced to `0.0` in the visible factor, even though `0.0` is what's used internally for sorting a missing score).
- Ranks are 1-based and dense (`1, 2, 3, ...`, no gaps) over exactly the actionable subset's size.
- Sorting NEVER compares two `Finding` objects directly (`Finding` is a frozen dataclass with no `__lt__`) — only their derived numeric sort keys are compared; ties fall back to Python's stable-sort input order.

**Never:**
- Never rank `BLOCKED`/`ACCEPTED_RISK` Findings — ranking implies "what to fix first," which is meaningless for something not actionable today.
- Never import `packaging` — it is not a declared `pyforge-doctor` dependency (confirmed against `pyproject.toml`'s own `dependencies` list); blast-radius classification uses a small stdlib `re`-based dotted-numeric parser instead.
- Never let a tie between two Findings with identical sort keys raise — sorting must use a `key=` function, never embed the `Finding` in the compared tuple itself.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| One KEV-flagged, one not, equal severity | `evidence={"kev": True}` vs. `{}` | KEV-flagged ranks first | No error |
| Two equal-severity CVE Findings, differing EPSS | `evidence={"epss": 0.62}` vs. `{"epss": 0.1}` | Higher EPSS ranks first | No error |
| KEV vs. high-EPSS-but-not-KEV | Both present | KEV wins (checked before EPSS) | No error |
| Three Findings tied on severity/KEV/EPSS, differing blast radius | `latest_conda_version`/`upstream_version` pairs implying patch/minor/major | `patch` first, then `minor`, then `major` | No error |
| Severity differs, KEV/EPSS favor the lower-severity one | `FAIL` plain vs. `WARN` w/ KEV+high-EPSS | The `FAIL` one still ranks first — severity dominates | No error |
| Missing EPSS evidence | No `epss` key | `rank_factors["epss"] is None`, sorts as if `0.0` internally | No error |
| `cve_watcher` Finding, `severity="K"`, `now_v > 0`, no explicit `kev` key | Real-data KEV inference | `rank_factors["kev"] is True` | No error |
| Same, `now_v == 0` | No longer affected | `rank_factors["kev"] is False` | No error |
| Mixed partitions in | `ACTIONABLE` + `BLOCKED` + `ACCEPTED_RISK` | Only the `ACTIONABLE` ones appear in the ranked output | No error |
| Empty actionable partition | All Findings BLOCKED/ACCEPTED_RISK | `()` | No error |
| Every rank_factors object | Any ranked output | Always `{"kev": bool, "epss": float\|None, "blast_radius": str}` | Never a bare integer |
| Multiple Findings tied on every signal | Identical sort keys | No `TypeError` — stable order, all present | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py` — EDIT (additive). New: `RankedPrescription` (frozen dataclass), `_SEVERITY_RANK`, `_BLAST_RADIUS_TIEBREAK`, `_leading_numeric_release`, `_classify_blast_radius`, `_is_kev`, `_epss_score`, `_rank_factors_and_sort_key`, `rank()`. New stdlib `re` import (module docstring updated to document why, not `packaging`).
- `src/shared/packages/pyforge-doctor/tests/meta/test_prescribe_pure_function.py` — EDIT (one-line). `_SANCTIONED_IMPORTS` gains `"re"`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_rank.py` — NEW. Full I/O matrix (14 tests): KEV precedence, EPSS precedence, KEV-beats-EPSS, blast-radius tiebreak ordering, severity dominance, missing-EPSS handling, real-data KEV inference (both the positive and negative case), 1-based dense ranking, partition filtering, empty-actionable, `rank_factors` shape, and a regression guard for the tie-comparison bug caught during self-review (see Review Triage Log).

## Design Notes

**Why blast-radius classification is a stdlib `re` reimplementation, not a `packaging` import:** the first draft imported `packaging.version.parse` (mirroring `behind_upstream.py`'s own real implementation almost verbatim). Before running any test, cross-checked `pyforge-doctor`'s `pyproject.toml` `dependencies` list — `packaging` is NOT declared there; it happens to be importable inside the shared `pyforge-doctor` pixi env today only because it's a transitive dependency of something else in that env (confirmed via a direct `python3 -c "import packaging"` probe), which is not a reliable contract for an installed `pyforge-doctor` wheel outside this monorepo's shared env. Replaced with `_leading_numeric_release`, a small `re`-based dotted-numeric extractor that handles the actual live cases (simple `X.Y.Z` conda/PyPI versions) without a hidden undeclared dependency — `re` is stdlib, always available. Full PEP 440 semantics (pre/post/dev/local segments) are deliberately not reproduced: the classification degrades to `"unknown"` for anything it can't parse, which is already the DOCUMENTED steady state for every live axis today (see below), so the fidelity gap has no live-data impact.

**Why blast-radius resolves to `"unknown"` for every Finding gathered by today's live axes:** no current Source producer's evidence carries BOTH a "current" version and a "target/upstream" version field in the same Finding — `staleness`'s evidence has only `latest_conda_version` (no upstream target it's being compared against), and `cve_watcher`'s evidence has no version-pair at all. This is expected, not a defect: the AC's own wording says the classification "reuses `behind-upstream`'s existing lag classification" as a TIEBREAKER, and a tiebreaker that never fires on the current 3 axes is architecturally honest about where Doctor's version-lag DATA actually lives (Source.BEHIND_UPSTREAM is a declared-but-not-yet-produced `Source` enum member — no story in Epics 1-3 wires a producer for it). The classification is fully exercised and correct today via synthetic evidence (this story's own unit tests); it activates for real data automatically whenever a future Finding's evidence happens to carry both version fields, without further code changes.

**Why the sort avoids ever comparing `Finding` objects (self-review finding):** an earlier implementation draft built `sorted((sort_key, finding) for ...)` — a tuple whose SECOND element is the `Finding` itself. Python's `sorted()`/tuple comparison falls through to comparing the second element whenever the first elements tie, and `Finding` (a `@dataclass(frozen=True)` with no `order=True`) has no `__lt__`, so any tie would raise `TypeError: '<' not supported between instances of 'Finding' and 'Finding'`. Caught during self-review, before the test suite ever ran against it (see Review Triage Log) — fixed by switching to `list.sort(key=lambda item: item[1])`, which extracts and compares ONLY the numeric sort key, never touching the `Finding` for comparison; ties resolve via Python's stable-sort input order. A dedicated regression test (`test_ties_do_not_raise_a_type_error_comparing_findings`) proves three fully-tied Findings rank without error.

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src python3 -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_rank.py src/shared/packages/pyforge-doctor/tests/meta/test_prescribe_pure_function.py -q`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — **313 passed** (297 baseline from Story 3.1 + 14 new tests from `test_prescribe_rank.py`; the meta-test file's own count is unchanged, one line edited).
- Isolated run: 24 passed (14 rank + 10 meta).

## Review Triage Log

### 2026-08-07 -- Self-review pass (adversarial re-read of the diff, before running the test suite)

- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 1, medium 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `high` `patch` **Tie-comparison `TypeError`.** The first draft's `rank()` embedded the `Finding` itself as the second element of each sorted tuple (`sorted((sort_key, finding) for ...)`), which raises `TypeError` on any tie (`Finding` has no `__lt__`). Fixed by switching to `list.sort(key=lambda item: item[1])`, extracting the sort key ONLY — see this spec's own Design Notes for the full explanation. New test: `test_ties_do_not_raise_a_type_error_comparing_findings`.
  - `medium` `patch` **Undeclared `packaging` dependency.** The first draft imported `packaging.version.parse` for blast-radius classification, mirroring `behind_upstream.py`'s own real implementation. Cross-checked `pyproject.toml` — `packaging` is not a declared `pyforge-doctor` dependency; it only worked by transitive accident inside the shared pixi env. Replaced with a small stdlib `re`-based `_leading_numeric_release` extractor (see Design Notes). No behavior change for any currently-live Finding (blast radius was already resolving to `"unknown"` in all real cases either way); the fix only affects the previously-untested synthetic-evidence path this story's own unit tests exercise.

Checked specifically for (beyond the two findings above): exception handling (no new exceptions raised anywhere in `rank()`'s call graph — `evidence.get(...)` never raises, `_leading_numeric_release`'s `re.match` never raises on a str input); resource leaks (none, no I/O); silent failures (an unparseable/missing version pair degrades loudly and correctly to `("unknown", ...)`, never silently mis-ranked as `"current"`); docstring-vs-behavior drift (re-read `rank()`'s docstring's four-level sort-precedence claim against `_rank_factors_and_sort_key`'s actual tuple construction -- matches).

**Follow-up review recommendation: false** -- both findings were caught and fixed before the test suite ever ran, each with a dedicated regression test; no residual risk identified.


### 2026-08-07 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, Epic 2+3 batch)

Dispatched with the diff file path only, no shared context. Two findings landed here:

- `high` `patch` **Clean (`DoctorStatus.OK`) Findings were ranked alongside real problems.** `_partition_one` classifies a clean Finding as `ACTIONABLE` ("nothing to do" is trivially actionable), but `rank()`'s own `actionable` list comprehension only filtered on `partition is ACTIONABLE`, not on `status`, so a clean Finding got a real 1-based rank/rank_factors as if it needed prioritizing. Fixed: `rank()` now also excludes any `ACTIONABLE` Finding whose `status is DoctorStatus.OK`. New test: `test_clean_ok_finding_is_excluded_from_ranking_even_though_actionable`. (The companion CLI-layer half of this same finding -- the rendered `action` text -- is recorded in Story 3.4's own spec.)
- `low` `patch` **`_is_kev`'s `now_v` check missed the `bool`-is-an-`int`-subclass guard its own sibling `_epss_score` already has.** `now_v=True` would satisfy `isinstance(now_v, (int, float)) and now_v > 0` and count as a spurious positive KEV signal. Not reachable from real `cve_watcher` rows today, but cheap to close. Fixed: added the same `not isinstance(now_v, bool)` guard. New test: `test_severity_k_with_boolean_now_v_is_not_kev`.

**Re-verification (2026-08-07, after both patches):** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- **336 passed** (full suite).

**Follow-up review recommendation (updated): false** -- both findings are narrow, each covered by a dedicated regression test.

</intent-contract>
