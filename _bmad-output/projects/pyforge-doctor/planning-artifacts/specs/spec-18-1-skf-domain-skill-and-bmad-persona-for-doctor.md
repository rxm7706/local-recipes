---
title: SKF domain skill and BMAD persona for doctor
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
baseline_revision: 865b95dc951c8a6de87d05bb10c8395a75da8008
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Doctor has no station-owned SKF skill or bmad-agent-doctor.

**Approach:** SKF from src/shared/packages/pyforge-doctor/ if missing. Persona uses only pyforge doctor … and POST /stations/doctor/mcp. Findings stay advisory — not a second PR gate. No CFE replace. No CLAUDE/AGENTS export.

## Acceptance Criteria

- Given steward 29 proved the shape, when this story completes, then .claude/skills/pyforge-doctor/ exists with provenance.
- Given bmad-agent-doctor, when inspected, then it consults that skill and forbids filesystem freelance and ad-hoc HTTP.
- Given findings, when the persona acts, then they remain advisory or Warden inputs — not a competing PR verdict.
- Given CFE and CLAUDE.md/AGENTS.md, when this PR lands, then they are unchanged.
- Given src/platform/, when scanned, then no new pyforge.* import.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-doctor/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-doctor` only — never `scripts/bmad-switch`. Ledger key `18-1-skf-skill-and-persona-for-doctor`.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Wave B pulse portal. Second PR gate. CFE replace. CLAUDE/AGENTS export.

</intent-contract>

## Code Map

- `.claude/skills/pyforge-doctor/`
- `.claude/skills/bmad-agent-doctor/`
- `src/shared/packages/pyforge-doctor/`

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated. Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 18.1 and the 2026-08-25 station-skill-portal SCP. Follow steward 29.1/29.2 for SKF+persona shape. Wave A stories must not edit `CLAUDE.md` / `AGENTS.md` except steward 33.1 via `skf-export-skill` after rebase if required.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight

## Review Triage Log

### 2026-08-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 8
- addressed_findings:
  - `[low]` `[patch]` checker now rejects CAP-15 consult of a non-skill file (README.md)

## Auto Run Result

Status: done

Summary: SKF content skill `.claude/skills/pyforge-doctor/` compiles from `src/shared/packages/pyforge-doctor/` with provenance. BMAD launcher `bmad-agent-doctor` consults that skill and may only emit FR-13 `pyforge doctor …` and FR-11 `POST /stations/doctor/mcp`. Findings stay advisory — not a second PR gate. Persona is not SKF-compiled. CFE, CLAUDE.md, and AGENTS.md unchanged. No `pyforge.*` under `src/platform/`.

Files:
- `.claude/skills/pyforge-doctor/` — SKF brief, version-nested package, `active` pointer
- `.claude/skills/bmad-agent-doctor/` — launcher SKILL.md, customize.toml, golden monitor transcript
- `src/shared/packages/pyforge-doctor/tests/meta/test_skf_domain_skill.py` — FR-37 / provenance / advisory / CFE / host-import gates
- `src/shared/packages/pyforge-doctor/tests/meta/test_station_persona.py` — FR-38 contract
- `planning-artifacts/specs/spec-18-1-….md` — tracked story spec

Review: 1 low patch applied; follow-up score 1 → false.

Verification: 19 passed on the new meta files; full doctor suite 1279 passed + 1 skipped after a cold-start flake on the existing 5s `doctor check` budget test (passed on retry). `git diff origin/main -- src/platform` empty of `pyforge` imports.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
