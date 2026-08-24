---
title: Wall-clock is never blended with active-compute
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: 2febf3bda5b404d0fe4a6c2f39df817b8d604611
final_revision: 6488062c317909e9b69c869f0b347ccb49b9600d
review_loop_iteration: 0
followup_review_recommended: true
deferred:
  - summary: >-
      Velocity panel `sub` still lumps unmeasured stories under "predate loop
      instrumentation"; full absence-class partitioning is Story 23.3 (CAP-3).
    evidence: |-
      CAP-2 only requires wall-clock vs active-compute class labels. Intent
      explicitly defers 23.3. Surfaced by blind-hunter + intent-alignment.
    location: >-
      docs/dashboard/generate.py:scan_timing velocity.sub
    severity: medium
  - summary: >-
      No runtime render fixture asserts emitted chip class HTML against mixed
      DASHBOARD_DATA; coverage is generator unit tests + static HTML needles.
    evidence: |-
      verification-gap review; check_render.js is no-throw only. Acceptable for
      CAP-2 land; strengthen later if chip regressions recur.
    location: >-
      docs/dashboard/index.html
    severity: low
---

<intent-contract>

## Intent

**Problem:** Wall-clock fallback (23.1) must not appear as active agent-compute on the velocity chart — readers need to tell metric classes apart from chart/caption alone (FR-194 CAP-2).

**Approach:** In `docs/dashboard/generate.py` + `index.html`, keep wall-clock-derived stories out of the active-compute bar series (or mark with a distinct class/series). Caption/legend makes the class readable without inspecting raw data. Preserve warden/atlas curated numbers byte-identical. Deps: 23.1 done (PR #711). Do not implement CAP-3 caption partitions (23.3) beyond what CAP-2 needs for class labeling.

## Acceptance Criteria

- No wall-clock number is rendered as if it were active agent-compute.
- Reader can tell each story's metric class from chart/caption alone.
- Warden/atlas curated timing values are byte-identical before and after.
- Does not implement Story 23.3 full absence-class partitioning (beyond class labels CAP-2 needs).

## Boundaries & Constraints

**Never:** Mix wall-clock into the active-compute bar series without a distinct class. Finalize marshal ledger only. maintenance label (docs/dashboard).

</intent-contract>

## I/O & Edge-Case Matrix (planning)

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mixed line | journal + wall-clock sids on one project | `perStoryClass` labels both; `velocity.bars` journal-only; dual `totalLabel`; `epicMin` journal-only; `epicMinWallClock` wall-only; `total` = journal minutes | No error |
| Journal only | closed journal sessions, no wall-clock | `perStoryClass` all `active-compute`; single active `totalLabel`; no `epicMinWallClock` | No error |
| Wall-clock only | wall-clock sids, zero journals | no velocity bars (or empty); `perStoryClass` all `wall-clock-ceiling`; `epicMin` empty; `epicMinWallClock` filled | No error |
| Curated preserved | warden/atlas non-derived timing (+ warden velocity) | byte-identical before/after generate | No error |
| Render wiring | `index.html` + mixed `perStoryClass` | story chips classed; mixed legend; velocity bars `data-metric="active-compute"` | No error |


## Code Map

- Parent: `spec-dashboard-velocity-captures-hand-driven-work/SPEC.md` (CAP-2); 23.1 deferred medium finding on blended `total`/`epicMin`.
- `docs/dashboard/generate.py` `scan_timing` — emit `perStoryClass`, split `epicMin` / `epicMinWallClock`, dual `totalLabel`, keep wall-clock off `velocity.bars`.
- `docs/dashboard/index.html` — `.stime`/`.etime` class styles, `timingClassLegend`, chip titles, velocity `data-metric="active-compute"`.
- Tests: `.claude/skills/conda-forge-expert/tests/meta/test_dashboard_scan_timing_wall_clock.py` (23.1 matrix + CAP-2 rows).
- Curated fixtures live in committed `docs/dashboard/data.js` (`projects.warden` / `projects.atlas`).

## Tasks & Acceptance

**Execution:**
- `docs/dashboard/generate.py` -- CAP-2 class map + unblended rollups; wall-clock never on velocity bars.
- `docs/dashboard/index.html` -- class-visible chips, mixed legend, velocity bar metric attribute.
- `.claude/skills/conda-forge-expert/tests/meta/test_dashboard_scan_timing_wall_clock.py` -- cover every I/O matrix row.
- `docs/dashboard/data.js` -- regenerate; assert warden/atlas curated timing byte-identical.

**Acceptance Criteria:**
- Given a mixed line, when generate runs, then wall-clock sids are absent from `velocity.bars` and carry `wall-clock-ceiling` in `perStoryClass`.
- Given mixed timing, when reading `totalLabel`/legend/chip titles, then both metric classes are named without a blended active-compute total.
- Given warden/atlas curated timing, when generate re-runs, then those blobs are byte-identical.
- Given `index.html`, when inspecting render wiring, then class CSS + legend + `data-metric="active-compute"` are present.

## Design Notes

Render surface = timing-strip class labels (not a second velocity series). Velocity stays journal-only with `data-metric="active-compute"`. Wall-clock chips use italic slate; active-compute chips use `--done`. Epic chips stay neutral when no `perStoryClass` (curated atlas must not be mislabeled active-compute).

## Verification

**Commands:**
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_dashboard_scan_timing_wall_clock.py .claude/skills/conda-forge-expert/tests/meta/test_dashboard_renders.py .claude/skills/conda-forge-expert/tests/meta/test_dashboard_resolve_project.py -q` -- expected: all PASS
- `python docs/dashboard/generate.py --source git` -- expected: doctor dual totalLabel; no wall-clock sids on velocity bars; warden/atlas curated timing unchanged

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 1, medium 2, low 2)
- defer: 2: (medium 1, low 1)
- reject: 9
- addressed_findings:
  - `[high]` `[patch]` Committed data.js still had blended "combined marks" / no perStoryClass — regenerated via dashboard-gen; warden/atlas curated timing byte-identical
  - `[medium]` `[patch]` epicMin blended journal+wall-clock — epicMin journal-only; epicMinWallClock + dual epic chips in index.html
  - `[medium]` `[patch]` timing.total blended both classes — total is primary class only (journal when present)
  - `[low]` `[patch]` totalLabel said "active" not "active compute" — restored vocabulary
  - `[low]` `[patch]` Invalid perStoryClass tokens could become CSS classes — whitelist in index.html

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/714
Merge: 6488062c317909e9b69c869f0b347ccb49b9600d
Merge policy: admin merge () — GitHub Actions billing blocks CI; local tests green before merge.
Summary: CAP-2 metric-class separation — wall-clock stays off velocity.bars; perStoryClass + chip/legend styling; split totalLabel; unblended epicMin / epicMinWallClock; data.js regenerated. Warden/atlas curated timing byte-identical.
Files:
- docs/dashboard/generate.py — perStoryClass, split rollups/labels, helpers
- docs/dashboard/index.html — chip CSS/titles, mixed legend, epic dual chips, data-metric
- docs/dashboard/data.js — regenerated (CAP-2 fields on derived lines)
- .claude/skills/conda-forge-expert/tests/meta/test_dashboard_scan_timing_wall_clock.py — CAP-2 assertions
Review findings: 5 patches applied; 2 deferred (CAP-3 sub caption; runtime DOM fixture); 9 rejected.
Follow-up review recommendation: true (patched high=1; score 3×2 medium + 2 low = 8 ≥ 5)
Verification:
- pixi run -e local-recipes pytest meta test_dashboard_scan_timing_wall_clock.py + test_dashboard_renders.py — 19 passed
- pixi run -e local-recipes dashboard-gen — doctor dual totalLabel; no combined marks; curated warden/atlas timing unchanged
Finalize: ledger key 23-2-wall-clock-is-never-blended-with-active-compute → done (this chore).
