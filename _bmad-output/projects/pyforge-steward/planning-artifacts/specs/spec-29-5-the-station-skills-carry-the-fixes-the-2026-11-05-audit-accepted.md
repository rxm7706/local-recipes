---
title: "29.5: The station skills carry the fixes the 2026-11-05 audit accepted"
type: 'fix'
created: '2026-11-05'
status: 'backlog'
baseline_revision: '836a2ee286'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-4-the-station-skills-are-recompiled-to-cover-the-verbs-the-contract-names.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The audit of 2026-11-05 accepted 20 findings against the compiled station skills. The skills lag the code: marshal's
says `--audit` reads whole files, steward's omits exit code 3, mason's hides its JSON contract and ship states, and warden's and
herald's give no exit codes. Two skills inherit their errors from source text, so a recompile alone reproduces them: herald's CAP
citations from `cli.py`, and scribe's staleness rule from `models.py` and `compile.py`.

**Approach:** Correct the source text first. Then put each fix in the `skill-brief.yaml` scope or the MANUAL region, and recompile
through `skf-update-skill`, as Story 29.4 did. The seven deferred skill findings ride the same pass.

Ledger key: `29-5-the-station-skills-carry-the-fixes-the-2026-11-05-audit-accepted`. Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-15** — the station skills are SKF compiles of the station packages (canopy:FR-37).

## Acceptance Criteria

- **AC1 — Source first.** herald's `pull` and `status` help strings cite the right capability, and scribe's `models.py` and `compile.py` docstrings say `compiled_at`.
- **AC2 — The skills.** Each accepted and carried finding named in the Story's FR/AD line is fixed in its skill, and no `SKILL.md` is hand-edited outside a MANUAL region.
- **AC3 — The MCP runner.** Each skill says what its station's MCP runner does and does not run, after the operator rules on `DW-steward-egm-2026-11-05-1`.
- **AC4 — The gates.** `pyforge-steward-test`, `governance-currency` and the instruction-surface parity test exit 0, and the owning Specs' memlogs name the recompiled paths.

## Boundaries & Constraints

- Parked at `backlog` by the session owner on 2026-11-05: a recompile pass is its own review.

**Never:**
- Never hand-edit a compiled `SKILL.md` outside a MANUAL region; never run `bmad-module-skill-forge uninstall`.

</intent-contract>

## Binding

Parent: `spec-pyforge-unifying-strategy` CAP-15

- Findings: the station research files `research/egm-audit-2026-11-05.md`.
- Epic: Epic 29.

## Verification

- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0.

## Spec Change Log

- 2026-11-05: minted at `backlog` by marshal Story 113.18.
