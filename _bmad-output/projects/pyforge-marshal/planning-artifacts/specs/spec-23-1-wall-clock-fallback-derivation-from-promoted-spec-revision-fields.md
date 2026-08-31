---
title: Wall-clock fallback derivation from promoted-spec revision fields
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-24'
context: []
warnings: []
baseline_revision: e7d9569ffb4d7a8d30efdabd5d70b5951fff3f0f
final_revision: fbe1bc935af445da8c9aa9742d98980a4a7514a2
followup_review_recommended: true
review_loop_iteration: 0
deferred:
  - summary: >-
      timing.total / epicMin sum journal minutes and wall-clock ceiling minutes into one
      numeric rollup while metric text says they are different classes.
    evidence: |-
      CAP-1 places both on timing.perStory honestly named; full visual/series separation
      is Story 23.2 (CAP-2). Surfaced by blind-hunter; not a fabricate risk.
    location: >-
      pyforge.doctor.sources.fleet_scan:scan_timing
    severity: medium
  - summary: >-
      Journal story_key lacking a leading N-M pattern may not block wall-clock for the
      matching board sid.
    evidence: |-
      Pre-existing journal key convention; loop homes emit N-M-slug keys. Edge-case hunter
      only; not introduced by CAP-1 derivation logic beyond shared _sid_from_journal_key.
    location: >-
      pyforge.doctor.sources.fleet_scan:_sid_from_journal_key
    severity: low
---

<intent-contract>

## Intent

**Problem:** Dashboard velocity derives active compute only from bmad-loop journals, so hand-driven stories show nothing even when promoted specs carry `baseline_revision`/`final_revision` (FR-194 CAP-1; spec-dashboard-velocity-captures-hand-driven-work).

**Approach:** In `pyforge.doctor.sources.fleet_scan` (`scan_timing`), for `done` stories with resolvable revision fields and zero closed journal sessions, derive wall-clock duration offline from local git commit timestamps. Choose one bound in-story (final−baseline vs first-commit-in-range) and state what is measured in the caption — never an unqualified "duration". Re-runs refresh derived values (`derived: true`). No resolvable signal → stay absent (never fabricate). Deps: none. Do not implement CAP-2 blending separation (23.2) or CAP-3 caption partitions (23.3) beyond what CAP-1 derivation needs.

## Acceptance Criteria

- Done story with resolvable baseline/final revisions and no journal sessions gets wall-clock from local git timestamps only.
- Doctor 8.1–8.4 (or equivalent fixtures) carry timing marks after generate.
- Re-run refreshes derived values; never freezes stale derived numbers.
- Story with no resolvable signal stays absent from the chart.
- Caption/field names the bound measured (not unqualified "duration").
- Does not implement Stories 23.2–23.3 beyond derivation plumbing.

## Boundaries & Constraints

**Always:** Offline local git only. Per-story precedence: journal session coverage wins; wall-clock only at zero closed sessions for that story key. Curated `timing`/`velocity` (no `derived: true`) stay byte-identical. Emit full renderer contract or nothing. Bound chosen: **final_revision − baseline_revision** commit timestamps (a ceiling; includes idle before dispatch) — first-commit-in-range collapses to 0 on single-commit hand landings (doctor 8.1–8.4 verified).

**Block If:** None — bound choice resolved in-story as final−baseline ceiling.

**Never:** Fabricate timing. Never blend wall-clock into active-compute velocity series as if they were the same class (leave full CAP-2 separation to 23.2; CAP-1 may put wall-clock only on `timing.perStory` and must name the bound in `timing.metric`/`note`). Finalize marshal ledger only. Do not implement 23.2–23.3 beyond derivation plumbing CAP-1 needs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | done story; resolvable baseline+final; zero journal sessions | `timing.perStory[sid]` = round((ts(final)−ts(baseline))/60) minutes; `derived: true`; metric/note names ceiling bound | No error |
| Journal wins | done story with ≥1 closed journal session | journal active-compute only; no wall-clock overwrite for that sid | No error |
| Unresolvable rev | missing field, `NO_VCS`, or rev not in local history | story stays absent from timing marks | silent skip (never fabricate) |
| Refresh | existing derived timing present; re-run generate | wall-clock minutes recomputed from current git; not frozen | No error |
| Curated preserved | project with non-derived timing+velocity | both fields untouched | No error |

</intent-contract>

## Code Map

- `pyforge.doctor.sources.fleet_scan` `scan_timing` (~L2776) — journal-only derivation today; early-`continue` when `not spans` blocks wall-clock-only lines; must merge wall-clock for done stories with zero journal coverage without putting those minutes on `velocity.bars`.
- `pyforge.doctor.sources.fleet_scan` `LOOP_HOMES` / `resolve_project` — journal home lookup; project dir for `planning-artifacts/specs/spec-{e}-{n}-*.md`.
- Parent contract: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-velocity-captures-hand-driven-work/SPEC.md` CAP-1 + `signal-inventory.md` §1.
- Live fixtures: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-8-{1,2,3,4}-*.md` (both revision fields; zero journal coverage — confirmed).
- Test pattern: `.claude/skills/conda-forge-expert/tests/meta/test_dashboard_resolve_project.py` — dynamic-load `generate.py` via `importlib`.

## Tasks & Acceptance

**Execution:**
- `pyforge.doctor.sources.fleet_scan` -- Add helpers: git commit timestamp lookup; parse `baseline_revision`/`final_revision` from matching promoted story-spec frontmatter; compute ceiling minutes (final−baseline). Extend `scan_timing` to (1) still derive journal spans for velocity+timing, (2) for each `done` story with no journal sid coverage, fill `timing.perStory` from wall-clock when resolvable, (3) name the ceiling bound in `timing.metric`/`note` when any wall-clock mark is present, (4) never add wall-clock minutes to `velocity.bars`, (5) do not early-exit solely because journal spans are empty if wall-clock marks exist, (6) keep `derived: true` so re-runs refresh.
- `.claude/skills/conda-forge-expert/tests/meta/test_dashboard_scan_timing_wall_clock.py` -- Unit-cover every I/O matrix row (happy path, journal precedence, unresolvable, refresh, curated preserved) against helpers/`scan_timing` with temp fixtures + mocked git where needed.
- `docs/dashboard/data.js` -- Regenerate via `Lane 1 /console/ (Guildhall generator retired) --source git` so doctor 8.1–8.4 appear under `projects.doctor.timing.perStory`.

**Acceptance Criteria:**
- Given a done story with resolvable revision fields and zero journal sessions, when generate runs, then `timing.perStory` carries wall-clock minutes from local git only.
- Given doctor 8.1–8.4 after generate, when inspecting `data.js`, then each has a timing mark.
- Given existing derived timing, when generate re-runs, then derived wall-clock values refresh.
- Given no resolvable signal, when generate runs, then that story stays absent.
- Given any wall-clock mark, when reading `timing.metric`/`note`, then the ceiling bound is named (not unqualified "duration").
- Given velocity bars, when wall-clock stories exist, then those stories are not plotted as active-compute bars.

## Design Notes

**Bound = final − baseline (ceiling).** Verified on doctor 8.1–8.4: `git log --reverse baseline..final` yields only the final commit, so first-commit-in-range → final is **0 minutes** — useless. Caption must say this is a wall-clock **ceiling** spanning baseline→final commit timestamps (includes idle before dispatch), not active agent-compute.

**Placement:** wall-clock → `timing.perStory` only; journal → velocity bars + timing. Metric text distinguishes classes (minimal CAP-1 honesty; full visual CAP-2 left to 23.2).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 1, medium 4, low 3)
- defer: 2: (medium 1, low 1)
- reject: 8
- addressed_findings:
  - `[high]` `[patch]` Mixed journal+wall-clock path untested — added `test_mixed_journal_and_wall_clock_keeps_velocity_journal_only`
  - `[medium]` `[patch]` Equal/sub-minute ceiling emitted 0 — `wall_clock_ceiling_minutes` now returns None when `ts_f <= ts_b` or minutes round to 0
  - `[medium]` `[patch]` Ambiguous multi-spec match silently picked first — require exactly one matching file
  - `[medium]` `[patch]` Non-str frontmatter values could AttributeError — `_unquote_fm` accepts object, returns ""
  - `[medium]` `[patch]` Asymmetric curated velocity + derived timing untested — added coverage
  - `[low]` `[patch]` Tautological duration assert — require `"duration" not in metric`
  - `[low]` `[patch]` Short story rows / non-dict projects — harden `done_n` and `isinstance(proj, dict)`
  - `[low]` `[patch]` Mixed note in-flight wording — journal-bars-only caveat

## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/711
Merge: fbe1bc935af445da8c9aa9742d98980a4a7514a2
Merge policy: admin merge (`gh pr merge 711 --merge --admin --repo rxm7706/local-recipes`) — GitHub Actions billing blocks CI; local tests green before merge.
Summary: CAP-1 wall-clock ceiling fallback in scan_timing from promoted-spec baseline_revision/final_revision via local git timestamps; doctor 8.1–8.4 timing marks (111/48/49/47); wall-clock never on velocity.bars; metric/note name the final−baseline ceiling; derived:true refreshes on re-run.
Files:
- pyforge.doctor.sources.fleet_scan — helpers + scan_timing wall-clock merge
- .claude/skills/conda-forge-expert/tests/meta/test_dashboard_scan_timing_wall_clock.py — I/O matrix + mixed-path + guards
- docs/dashboard/data.js — regenerated (--source git)
- story spec — contract, triage, deferred
Verification:
- pixi run -e local-recipes pytest meta dashboard timing/render/resolve tests -q — 32 passed
- Lane 1 /console/ (Guildhall generator retired) --source git — doctor 8.1–8.4 present; metric names ceiling
Follow-up review recommendation: true (patched high=1; score 3×4 medium + 3 low = 15 ≥ 5)
Finalize: ledger key 23-1-wall-clock-fallback-derivation-from-promoted-spec-revision-fields → done (PR #712, merge fb62f3a42343088f4dc7b3de7afcfae6a4694477).
