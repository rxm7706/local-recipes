---
title: 'Story 7.3: The detector sees anonymous Tier-3 entries'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '257094dcc2cf99a95c8553b6c05ae3cc09fe876f'
final_revision: 'cc92bedfa6352cbb8c7ec4a4996ae84e3b3035e7'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-7-context.md'
  - '{project-root}/scripts/deferred_work_baseline.py'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `chain.py::_anonymous()` already parses the "no `## DW-<id>` heading" shape and
already runs against the tracked ledger, but never against a project's gitignored Tier-3 file —
so hundreds of anonymous Tier-3 deferrals stay invisible to a check that claims "every Tier-3
deferral has a tracked twin." Story 7.2 stamped `scripts/.deferred-work-baseline.json` (a
per-project count) precisely so this gap could close without redding every pre-existing entry.

**Approach:** Extend `gather_deferred_work`'s per-project pass to also run `_anonymous()` against
the Tier-3 file, load the committed baseline once, and report only entries positioned past each
project's stamped count (`_anonymous(t3_path)[baseline.get(proj, 0):]`) as a new FAIL finding kind.

## Boundaries & Constraints

**Always:** Reuse `_anonymous()`/`_ENTRY_RE`/`_ANON_RE` unchanged — extend the call sites in
`chain.py`, never rewrite the parser. Reuse `Source.DEFERRED_WORK`; no new `Source` member. Read
`scripts/.deferred-work-baseline.json` read-only — this story consumes the baseline Story 7.2
produces, never stamps or rewrites it. A missing or malformed baseline degrades to exactly one
named finding, never to treating every project's count as 0 (which would flood every pre-existing
anonymous Tier-3 entry as a fresh FAIL — the exact regression the baseline exists to prevent).
Every change to `chain.py` is governed by `spec-pyforge-doctor`'s surface glob: append a dated
`.memlog.md` entry naming the changed paths and re-stamp
`python scripts/spec_surface_check.py --write-baseline --spec spec-pyforge-doctor` before landing
(the repeated S-13.7 convention every prior Epic 6/7 story on this Spec already follows).

**Block If:** None — this is a scoped extension of an existing, hardened parser against an
already-designed, already-committed baseline shape; no undecided design question remains.

**Never:** No triage of which anonymous entries are worth keeping (explicit epic non-goal). No
change to the emitter or to what a review pass defers (Story 7.1's job, done). No new `Source`
enum member or CLI verb. No import of `pyforge.doctor` from `scripts/deferred_work_baseline.py` —
it stays a standalone duplicate per 7.2's Design Notes; this story only touches the
`pyforge.doctor.sources.chain` side. No fleet-wide id-convention normalization.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New anonymous Tier-3 entry | project's Tier-3 file has N anonymous entries; baseline stamps count K<N | entries K+1..N each produce a `tier3-entry-unidentified` FAIL | No error expected |
| Grandfathered anonymous entry | Tier-3 file has exactly K anonymous entries; baseline stamps count K | zero `tier3-entry-unidentified` findings for this project | No error expected |
| CAP-2 mutation proof | a `## DW-x` entry whose `- source_spec:` field is claimed (no finding) has its id heading deleted | the entry becomes anonymous and beyond the baseline slice → FAIL fires | No error expected |
| Baseline file missing | `scripts/.deferred-work-baseline.json` absent | one `no-deferred-work-baseline` FAIL finding; no per-project `tier3-entry-unidentified` findings emitted anywhere (avoids flooding) | Handled, not raised |
| Baseline JSON malformed | file exists but is invalid JSON or the wrong top-level shape | same as missing: one `no-deferred-work-baseline` FAIL, Tier-3-anonymous check skipped repo-wide | Handled, not raised |
| Project absent from baseline | baseline valid, but this project's slug has no key | treated as count 0 — every current anonymous Tier-3 entry for that project is FAIL (never grandfathered) | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:1317-1551` -- add a
  `DEFERRED_WORK_BASELINE_REL` constant + `_load_deferred_work_baseline()` (mirrors
  `_drift_findings`'s `BASELINE_REL`/load-and-degrade pattern at lines 676, 985-1000); extend
  `_check_project_deferred_work` (L1376) to accept the loaded baseline and emit
  `tier3-entry-unidentified` findings from `_anonymous(t3_path)[count:]`; extend
  `_deferred_work_findings` (L1438) to load the baseline once before the per-project loop; add a
  message branch to `_deferred_work_message` (L1463).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- existing
  suite for this gather function; add the new finding-kind coverage and the CAP-2 mutation pair.
- `_bmad-output/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` -- append the dated
  landing entry naming the changed paths (spec-surface reconciliation).
- `scripts/.spec-surface-baseline.json` -- re-stamped by the write-baseline command below; not
  hand-edited.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- wire the
  Tier-3-anonymous check as described in Code Map -- closes CAP-2/CAP-3 for the detector side.
- [x] `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- cover
  every I/O matrix row, including the CAP-2 mutation pair (identified entry -> no finding; same
  entry with its id heading deleted -> FAIL) against real tmp-path fixtures -- proves the
  detector actually sees the shape it claims to check.
- [x] `_bmad-output/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` -- append a dated
  entry naming the changed paths -- required before `spec_surface_reconcile.py` will pass.
- [x] Run `python scripts/spec_surface_check.py --write-baseline --spec spec-pyforge-doctor` --
  re-stamps the governed-file baseline to match this story's diff.

**Acceptance Criteria:**
- Given a project's Tier-3 file with entries beyond the baseline-stamped count, when
  `gather_deferred_work` runs, then each such entry produces one `tier3-entry-unidentified` FAIL
  `Finding` with `source=Source.DEFERRED_WORK`.
- Given a project's Tier-3 file with anonymous entries entirely within the baseline-stamped
  count, when `gather_deferred_work` runs, then zero `tier3-entry-unidentified` findings are
  produced for that project.
- Given a real Tier-3 fixture entry with a claimed `- source_spec:` field, when its `## DW-<id>`
  heading is deleted and `gather_deferred_work` re-runs, then the detector reds where it was
  previously clean (the CAP-2 mutation proof, demonstrated as a permanent test pair).
- Given `scripts/.deferred-work-baseline.json` is missing or malformed, when
  `gather_deferred_work` runs, then exactly one `no-deferred-work-baseline` FAIL finding is
  produced and no project's Tier-3-anonymous entries are individually reported.
- Given the real repo state (baseline already committed by Story 7.2, unchanged since), when
  `python -m pyforge.doctor.sources deferred-work` runs, then no NEW `tier3-entry-unidentified`
  finding appears for pyforge-doctor (its live anonymous count already equals the stamped 72).

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 0, medium 0, low 7)
- defer: 1 (high 0, medium 0, low 1)
- reject: 4 (high 0, medium 0, low 4)
- addressed_findings:
  - `low` `patch` Both reviewers independently found `_load_deferred_work_baseline`'s shape guard's `isinstance(v, int)` accepts Python `bool` (an `int` subclass) and negative integers -- `{"proj": true}` would slice as `[1:]` and `{"proj": -1}` would slice via Python's negative-index semantics (tail-only), silently mis-slicing instead of being rejected as malformed. Fixed: guard now requires `isinstance(v, int) and not isinstance(v, bool) and v >= 0`. Pinned by two new tests.
  - `low` `patch` Edge Case Hunter found `_load_deferred_work_baseline` used stdlib `Path.is_file()` instead of this module's own `_is_file()`/`_probe()` convention, which exists because stdlib `is_file()` swallows `PermissionError` on an unreadable ancestor and lies `False` -- the identical failure class already documented and fixed elsewhere in this same function. Fixed: routed through `_is_file()`, with any exception it raises caught locally so the function still degrades to one named finding rather than propagating past `_deferred_work_findings`'s per-project isolation boundary.
  - `low` `patch` Blind Hunter found the `no-deferred-work-baseline` branch of `_deferred_work_message` used a defensive `item.get("detail", <default>)` fallback that can never fire (every producing branch always sets `detail`), inconsistent with every sibling branch's direct indexing. Fixed to `item["detail"]`.
  - `low` `patch` Blind Hunter found `scripts/.spec-surface-baseline.json`'s re-stamp for this spec incidentally refreshed `board.py`/`README.md`'s committed hashes -- pre-existing drift from earlier, already-landed commits that never re-stamped this spec's baseline, silently absorbed as a side effect of `--write-baseline --spec`'s whole-surface re-hash. Confirmed via `git log`/`git hash-object`: neither file is touched by this story's diff. Fixed: named the incidental fix and its cause in this Spec's `.memlog.md` rather than leaving it unexplained.
  - `low` `patch` Blind Hunter found no test pins the "baseline count exceeds live entry count" (shrinking) case -- Python slicing already degrades gracefully but nothing asserted it. Added `test_baseline_count_larger_than_live_entries_reports_nothing`.
  - `low` `patch` Blind Hunter found no test exercises a `bool`/negative baseline value directly (only implied by the shape-guard fix above). Added `test_baseline_bool_or_negative_value_degrades_like_missing`, parametrized over both.
  - `low` `patch` (rolled into the two items above) Blind Hunter also asked for a float-valued baseline-entry test; already correctly rejected by `isinstance(v, int)` -- folded into the same shape-guard test additions rather than a third near-duplicate case.
- Deferred (1): `low` The committed anonymous-Tier-3 baseline has no automated freshness check going forward, only this landing's one-off manual `deferred-work` CLI verification (Blind Hunter). Minted `DW-FU-7-3` in doctor's Tier-3 ledger; not patched here (a staleness-detection mechanism for the baseline itself is a distinct capability outside this story's CAP-2/CAP-3 scope, and the Never clause forbids backlog/baseline triage beyond consuming it read-only).
- Rejected (4): the new `tier3-entry-unidentified` check ignores `_SUBSTANTIVE_BYTES`, the boilerplate-noise floor its sibling `no-tracked-ledger` check respects -- investigated: that floor exists to distinguish "empty scratch file" from "a real backlog with zero tracked twin," an orthogonal, coarser-grained check; `tier3-entry-unidentified` is about one specific entry's shape, and the spec's own Never clause explicitly forbids suppressing which anonymous entries get reported -- a size floor here would hide small-but-real entries, the opposite of CAP-2's intent -- `[low]`, real-sounding but the premise doesn't hold once the two checks' distinct purposes are traced. The positional-slice comparison assumes strictly append-only Tier-3 edits and nothing re-verifies that invariant in this story -- Story 7.2's own Boundaries section already verified this discipline holds live and this story's Design Notes explicitly inherit that finding unchanged; re-litigating an already-settled cross-story design decision is out of this story's scope -- `[low]`. Hardcoded line-number citations in the new docstring (e.g. "chain.py:968-1000") will rot silently on a future edit -- matches this exact file's own pre-existing, endemic documentation convention throughout; not a new deviation this story introduced -- `[low]`. `tier3-entry-unidentified` and the pre-existing `ledger-entry-unidentified` share the same `"line {n}"` id shape, risking downstream conflation -- speculative, no evidence any consumer keys findings by `(project, id)` alone rather than `(project, check, id)`, and the pre-existing kind has used this exact shape without issue across 6+ prior stories -- `[low]`.

## Design Notes

**Why load the baseline once, not per-project.** `_drift_findings` (chain.py:968) already
establishes this exact shape for `.spec-surface-baseline.json`: one load before the per-spec
loop, one degrade-to-named-finding path on missing/malformed, then a plain dict read per item
inside the loop. This story's baseline is a single repo-root file too (`scripts/` sibling), so
the same structure applies without inventing a second pattern.

**Why a positional slice, not a lookup.** Story 7.2's Design Notes already settled this:
`_anonymous(path)` returns Tier-3 anonymous entries' line numbers in file order, and the file's
append-only discipline makes "beyond the stamped count" equivalent to "new." `_anonymous(t3_path)
[baseline.get(proj.name, 0):]` is the whole comparison — no new data structure needed.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- `git diff --stat` touches only `chain.py`, the test file, and `spec-pyforge-doctor/.memlog.md`
  -- no `pixi.toml`, no `models.py`, no `sources/__init__.py` registry change.

## Auto Run Result

Status: done

**Summary.** `gather_deferred_work` (`pyforge.doctor.sources.chain`) now runs the existing
`_anonymous()` parser against each project's gitignored Tier-3 file, not just the tracked ledger,
closing CAP-2. Entries beyond the Story 7.2 grandfather baseline (`scripts/.deferred-work-baseline.json`,
positional slice `_anonymous(t3_path)[count:]`) report `tier3-entry-unidentified` FAIL; a
missing/malformed baseline degrades to one `no-deferred-work-baseline` FAIL instead of flooding
every project, closing CAP-3.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- `DEFERRED_WORK_BASELINE_REL`,
  `_load_deferred_work_baseline()`, `_check_project_deferred_work`/`_deferred_work_findings`/
  `_deferred_work_message` extended for the two new finding kinds.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- 10 new
  tests (every I/O matrix row + the CAP-2 mutation pair + two review-pass additions).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` --
  dated Story 7.3 landing entry, S-13.7 spec-surface reconciliation.
- `scripts/.spec-surface-baseline.json` -- re-stamped for `pyforge-doctor/spec-pyforge-doctor`.
- `_bmad-output/projects/pyforge-doctor/implementation-artifacts/deferred-work.md` (Tier-3, not
  git-tracked) -- one new deferred entry, `DW-FU-7-3`.

**Review findings breakdown:** 12 total (0 intent_gap, 0 bad_spec) -- 7 patch (all low: `bool`/
negative baseline-value coercion, `_is_file()` house-convention alignment, a dead fallback branch,
an unnamed incidental baseline-hash refresh for two unrelated files, two missing test cases), 1
defer (low: no automated baseline-freshness check, `DW-FU-7-3`), 4 reject (a boilerplate-size-floor
critique that conflates two orthogonal checks, an already-settled cross-story design assumption,
an endemic pre-existing docstring convention, a speculative id-collision worry with no supporting
evidence).

**Verification performed:** `pixi run -e pyforge-doctor pyforge-doctor-test` -- 852 passed, 1
skipped (842 -> 852). `python scripts/spec_surface_reconcile.py` -- `OK: every tracked file
governed or allowlisted; no drift.` `pixi run -e pyforge-doctor python -m pyforge.doctor.sources
deferred-work` against this real repo -- the pre-existing `tier3-only-deferral` FAIL for
`pyforge-doctor/DW-FU-6-11` plus one new, expected `tier3-only-deferral` FAIL for the
just-minted `DW-FU-7-3` (an id present in Tier-3 pending promotion, the normal, correct shape for
any freshly-deferred entry) -- no `tier3-entry-unidentified` finding for any project, confirming
CAP-3's "green on an unchanged repo" claim holds live.

**Residual risks:** the deferred `DW-FU-7-3` item (baseline can drift stale over time with no
automated freshness signal) is real but explicitly out of this story's CAP-2/CAP-3 scope. Story
7.4 ("one severity, both sides") depends on this story's new `tier3-entry-unidentified` finding
kind existing, which it now does.
