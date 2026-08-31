---
title: Five-tier check
type: chore
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: 0f1ebeb94bc241249972d3c615b6d4c080145fab
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - src/shared/packages/pyforge-steward/tests/meta/test_station_persona.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** "Done" can still mean CLI-only. FR-39 requires 03 completeness to be mechanically verifiable across eight stations × five tiers (denominator 40), failing only when an 03 station is *declared* complete with fewer than five.

**Approach:** Land a pytest/CI check in `pyforge.steward` that always reports the 8×5 matrix and fails on false-complete 03 declarations. 01/02 fixtures (spec+script or spec+skill) stay outside the denominator and do not fail. Do not mint the missing personas/skills for the other seven stations.

## Acceptance Criteria

- Given all eight 03 stations, when the check runs, then it reports each of CLI, portal, service, skill, persona (8 × 5 = 40 cells).
- Given an 03 station declared complete with fewer than five tiers, when the check runs, then it fails.
- Given 01/02 fixtures that are only spec+script or spec+skill (even if marked complete), when the check runs, then it does not fail.
- Given the check module is removed, when the meta tests collect or run, then they fail.
- Given `src/platform/`, when this story's diff is scanned, then no `pyforge.*` is added.

## Boundaries & Constraints

**Always:** Write specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`. Reuse filesystem probes already proven by 19.2 / 21.4 / 22.1 / 29.1 / 29.2. Report missing tiers; do not invent them.

**Block If:** A change would put `pyforge.*` under `src/platform/`, start Story 30.1, or declare all eight stations complete without the five tiers existing.

**Never:** Minting personas/skills for all eight. Failing live CI solely because a station still lacks a persona. Treating 01/02 work as 03. A second check in Doctor. A ninth station. Importing Django in the steward check.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live matrix | Repo root, eight roster stations | Report 8 stations × 5 tiers; denominator 40 | Missing tiers are reported, not a fail by themselves |
| False complete | 03 station in `DECLARED_COMPLETE` with a missing tier | `FiveTierCompleteError` | Test fails if the check accepts |
| 01 spec+script | Extra work_class 01, spec.md + script.py, declared complete | Check passes | Fail the test if it errors |
| 02 spec+skill | Extra work_class 02, spec.md + SKILL.md, declared complete | Check passes | Fail the test if it errors |
| Check removed | `five_tier.py` absent or `check` missing | Meta tests fail collection or assertion | That failure *is* the signal |
| Host import | Diff of `src/platform/` vs baseline | No new `pyforge.*` | Any such import fails |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py` — **new** FR-39 check: `TIERS`, `STATIONS`, `DECLARED_COMPLETE`, `detect_tiers`, `report`, `check`, `FiveTierCompleteError`
- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` — **read-only** `script_map_from_packages_root` for the CLI cell
- `src/shared/packages/django-{station}/` — **read-only** portal tree; warden is `django_warden_fabric`
- `src/shared/packages/django-scribe/src/django_scribe_portal/apps.py` — **read-only** real `mcp_asgi_app` (service cell pattern)
- `.claude/skills/pyforge-scribe/` — **read-only** CAP-15 skill cell (29.1)
- `.claude/skills/bmad-agent-scribe/` — **read-only** CAP-16 persona cell (29.2)
- `src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py` — **new** I/O matrix + fail-if-removed
- `src/platform/` — do not add `pyforge.*`

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py` — add the report+fail-on-false-complete check — FR-39 / canopy AD-14
- `src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py` — cover the I/O matrix; fail if the module is gone

**Acceptance Criteria:**
- Given all eight 03 stations, when the check runs, then it reports CLI, portal, service, skill, persona.
- Given an 03 station declared complete with fewer than five, when the check runs, then it fails.
- Given 01/02 fixtures (spec+script or spec+skill only), when the check runs, then they do not fail.

## Design Notes

Live roster stations are always work_class 03. None are declared complete in this chore (`DECLARED_COMPLETE` is empty): 29.1/29.2 proved scribe skill+persona only. The check *reports* the holes (mason has `conda-forge-expert`, not `pyforge-mason`; seven stations lack `bmad-agent-<station>`).

`declared complete` is the Python frozenset `DECLARED_COMPLETE` in `five_tier.py`. Tests monkeypatch it. 01/02 work is passed as `extra` `WorkItem`s and never counted in the 40.

CLI = token in `script_map_from_packages_root`. Portal = `django-<station>` package dir. Service = `mcp_asgi_app` in portal `apps.py` whose body is not solely `return None`. Skill = any `SKILL.md` under `.claude/skills/pyforge-<station>/`. Persona = `.claude/skills/bmad-agent-<station>/SKILL.md`.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 0
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` add path-filtered GitHub Actions job so false-complete can fail CI
  - `[low]` `[patch]` treat async `mcp_asgi_app` as a service cell
  - `[low]` `[patch]` 03 fixture with all five tiers declared complete must pass; skip `origin/main` platform diff when the ref is absent

## Auto Run Result

Status: done

Summary: Steward five-tier check reports the eight 03 stations × five tiers (denominator 40) and fails only when an 03 station is declared complete with fewer than five. 01/02 fixtures do not fail. No personas/skills minted for the other seven stations. No `pyforge.*` under `src/platform/`. Lean CI job runs the meta tests.

Files:
- `src/pyforge/steward/five_tier.py` — report + fail-on-false-complete
- `tests/meta/test_five_tier_check.py` — I/O matrix
- `.github/workflows/pyforge-steward-five-tier.yml` — CI gate
- `planning-artifacts/specs/spec-29-3-five-tier-check.md` — tracked story spec

Review: 3 patches applied; follow-up score 1×medium + 2×low = 5 → true.

Verification: 28 passed (`test_five_tier_check` + `test_station_persona` + `test_skf_domain_skills`).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
