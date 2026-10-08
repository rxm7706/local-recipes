---
title: "19.3: The environment craft skill teaches mason environment lock and check"
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: '25ca417bb3478a91008d79fbbdc5cd4f2fa2c3b6'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-19-2-the-package-craft-skill-teaches-mason-package-build-and-ship.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `mason environment lock` and `mason environment check` are Mason's other native craft (CAP-4): mixed conda
and pip dependency sets resolved into one lockfile by an engine, and a CI check that exits non-zero when the lockfile has
gone stale. How to drive them — manifest discovery, explicit paths, repeatable platforms, the engine's provenance — is
not written anywhere an agent loads. The operator ruled on 2026-09-28 that it becomes a Mason skill
(`spec-pyforge-mason` CAP-29, question 2c).

**Approach:** author `.claude/skills/mason-environment/SKILL.md` with `bmad-workflow-builder`, the same way Story 19.2
authored `mason-package` — a hand-authored operating-procedure skill, not SKF output. It walks
`pyforge mason environment lock` (manifests discovered and listed before solving; explicit manifest paths override
discovery; `--platform` takes comma-separated platforms and the engine's default is reported when none is given; the
lockfile path; the engine's name and version in the output and in the lockfile's provenance where the format allows) and
`pyforge mason environment check` (the existing lockfile verified, not written; non-zero when stale; `--format json` for
CI). Solving is the engine's alone — the skill states no resolution rule — and the verbs run with the CFE machinery absent,
so the skill needs no CFE step; it still links `conda-forge-expert` for anything that turns into recipe work, and links the
station skill `pyforge-mason` for the full grammar. `test_mason_skills.py` gains the `mason-environment` row;
`docs/reference/skills-catalog.md` is regenerated; `docs/reference/agent-instruction-notes.md` § *Skill Reference* gains
one row.

Ledger key: `19-3-the-environment-craft-skill-teaches-mason-environment-lock-and-check`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-19.2.

### Living CAP citations

- `spec-pyforge-mason` CAP-29 (FR-51); CAP-4 (dependency binding); AD-1; canopy:AD-17.

## Acceptance Criteria

- Given `.claude/skills/mason-environment/SKILL.md` When it is read Then its frontmatter carries `name: mason-environment` and a `description:`, and its body names `pyforge mason environment lock`, `pyforge mason environment check`, manifest discovery with explicit-path override, `--platform`, and the engine provenance
- Given the skill When it describes solving Then it leaves resolution to the engine and states no resolution rule of its own
- Given `test_mason_skills.py` When it runs Then its table holds `mason-package` and `mason-environment`, both pass, and the planted-heading check still fails a copy
- Given `docs/reference/skills-catalog.md` When `docs-skills-catalog -- --check` runs Then it exits 0

## Boundaries & Constraints

**Always:**
- Document what `cli.py` and `environment.py` do today; the flag names are read from the parser, not remembered.
- Keep the skill CFE-independent in what it asks an agent to run, as the verbs are (CAP-4).

**Never:**
- Do not change Mason's code or the CFE surface.
- Do not SKF-compile this skill or nest it under `.claude/skills/pyforge-mason/`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| skill read | `mason-environment/SKILL.md` | both verbs, discovery, `--platform`, provenance | missing item fails the meta-test |
| gotcha copied | a `### G<n>.` heading | meta-test fails | — |
| table | `mason-package` + `mason-environment` | both checked | a row whose skill is missing fails |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-29 (FR-51).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-27 — Proposed: Mason has its own skills, and `conda-forge-expert` is one of them*.
Ledger key: `19-3-the-environment-craft-skill-teaches-mason-environment-lock-and-check`.
Ledger status at mint: `backlog`.
Deps: S-19.2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild docs-skills-catalog -- --check` — expected: exit 0 after regeneration.

## Review Triage Log
