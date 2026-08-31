---
title: Test architecture stays current as stories land
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: e63750bebb71fa4f520b88ff674c6f582f5d2e20
deferred:
  - summary: >-
      Wire `tea-playwright-check` into a CI / detectors job so the CAP-5 gate
      runs without an operator opt-in (intent allowed CI or CLI; this story
      shipped the CLI).
    evidence: |-
      pixi task exists; no .github/workflows reference in the 19.4 diff.
      Approach said "detectable (fail or report)"; original AC allowed CI or CLI.
    location: >-
      pixi.toml / .github/workflows
    severity: medium
  - summary: >-
      Atlas-style epic headers `### Story A1 (2.1): …` are not parsed by
      `_STORY_HEADER`, so lettered stories never enter the --check expected set.
    evidence: |-
      Pre-existing 19.1 generator limitation surfaced by verification-gap review;
      live atlas check reports only numeric ids.
    location: >-
      _bmad/scripts/bmad_tea_playwright.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Station `test-architecture.md` files freeze at generation time; a story that ships without an updated coverage-table row is a silent gap (FR-193 / testing-charter CAP-5).

**Approach:** Re-running S-19.1's generator (`scripts/bmad_tea_playwright.py` or successor) against a station's own epics regenerates its story-coverage table without hand-editing. Drift between shipped stories and the table is detectable (fail or report), not silent — so Herald's and Marshal's real documents do not freeze at their generation snapshot.

## Boundaries & Constraints

**Always:** Drift is detected against the on-disk Story Coverage Matrix vs stories parsed from that station's epics. Re-run remains idempotent. TBD in output remains a hard fail. Use physical `_bmad-output/projects/<slug>/` paths; `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`.

**Block If:** None known for this story.

**Never:** Implement 20.x baseline-drift / intent-gap stories. Never `scripts/bmad-switch`. Do not touch steward 15-3 ledgers or PR. Do not claim coordinator lock.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_CHECK | On-disk matrix contains every epic story id | `--check` exits 0; prints OK per station | No error expected |
| MISSING_ROW | Epic has story 1.3; on-disk matrix lacks 1.3 | `--check` exits 1; names station + missing id(s) | Non-zero exit; stderr lists drift |
| REGEN_FILLS | Same drifted tree; run generate (no `--check`) | Coverage table gains 1.3; subsequent `--check` exits 0 | Write path unchanged from 19.1 |
| IDEMPOTENT | Unchanged tree; generate twice | Byte-identical documents | No error expected |
| MISSING_DOC | Station has epics but no `test-architecture.md` | `--check` exits 1 naming missing file | Non-zero exit |

</intent-contract>

## Code Map

- `_bmad/scripts/bmad_tea_playwright.py` — `--check` drift gate; TBD on-disk hard-fail; guarded reads; resilient `check_all`; `GENERATOR_VERSION` `2.1.0`
- `src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_drift.py` — I/O matrix + missing_matrix + TBD + `--all --check` fleet fixture + Herald/Marshal smoke
- `src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_generator.py` — 19.1 contracts unchanged
- `pixi.toml` — `tea-playwright-check` → `--all --check`

## Tasks & Acceptance

**Execution:**
- `_bmad/scripts/bmad_tea_playwright.py` -- add `--check` (with `--all` / `--project`); exit 1 when any epic story id is absent from the on-disk Story Coverage Matrix, or the doc/matrix is missing, or TBD is present; exit 0 when all stations covered -- CAP-5 detectable drift
- `src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_drift.py` -- fixture-cover I/O matrix + fleet `--all --check` + TBD/missing-matrix -- proof
- `pixi.toml` -- wire `tea-playwright-check` → `python _bmad/scripts/bmad_tea_playwright.py --all --check` -- operator CLI gate

**Acceptance Criteria:**
- Given a station whose epics list stories, when `--check` runs and the on-disk Story Coverage Matrix includes every parsed story id, then the command exits 0.
- Given an epic story id absent from the on-disk matrix, when `--check` runs, then it exits non-zero and names the station and missing id(s).
- Given that drifted fixture, when the 19.1 generator is re-run for the station, then the coverage table gains the missing row and a subsequent `--check` exits 0 (no hand-edit).
- Given unchanged inputs, when generate runs twice, then output is byte-identical; Herald and Marshal docs remain regenerable (dry-run / render without TBD).
- Given this story's scope, when reviewing the change, then no Epic 20 baseline-drift / intent-gap code is present.

## Spec Change Log

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 2, medium 3, low 2)
- defer: 2: (high 0, medium 2, low 0)
- reject: 12
- addressed_findings:
  - `[high]` `[patch]` Enforce TBD hard-fail on `--check` for on-disk docs
  - `[high]` `[patch]` Add `--all --check` / fleet fixture test (monkeypatch STATIONS)
  - `[medium]` `[patch]` Guard `read_text` for OSError / UnicodeDecodeError
  - `[medium]` `[patch]` Per-station try/except in `check_all` so one failure does not abort the fleet
  - `[medium]` `[patch]` Test missing Story Coverage Matrix section
  - `[low]` `[patch]` Usage docstring includes `--project … --check`
  - `[low]` `[patch]` MISSING_ROW asserts `DRIFT … missing story id(s)` message shape

## Design Notes

Primary gate compares **story ids** in the committed Story Coverage Matrix to stories parsed from epics — not full-document byte equality. Full-doc equality fails whenever tests are added without regen (observed live on marshal/doctor/steward after 19.2/19.3) and is inventory noise, not CAP-5's "missing coverage row" signal.

```text
# Drift: epic stories − matrix ids
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-marshal --check
# Cure: regenerate table from epics
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-marshal
```

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: Shipped CAP-5 / FR-193 story-id drift gate on the 19.1 TEA generator — `--check` compares epic story ids to the on-disk Story Coverage Matrix (plus TBD / missing-doc / missing-matrix), pixi `tea-playwright-check`, and meta fixtures including fleet `--all --check`. Review patches hardened TBD-on-check, read errors, and fleet aggregation.

Files changed:
- `_bmad/scripts/bmad_tea_playwright.py` — `--check`, CheckResult, parse_matrix_story_ids, check_station/check_all (v2.1.0)
- `tests/meta/test_tea_architecture_drift.py` — new I/O + fleet + TBD/matrix tests
- `pixi.toml` — `tea-playwright-check`
- story spec — planned, reviewed, done

Review findings: 7 patches applied (2 high → followup_review_recommended true; score from highs); 2 deferred; 12 rejected (noise / Reading-A scope). Follow-up review recommended: true (2 high patches).

Verification: 17 meta tests passed; `tea-playwright-check` exit 0 (8 stations); Herald/Marshal dry-run OK.

Residual risks: gate is CLI-opt-in until CI wiring (deferred); atlas lettered story headers still invisible to the expected set (deferred).
