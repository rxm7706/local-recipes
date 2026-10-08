---
title: '67.5: The estate points at the SBOM'
type: 'docs'
created: '2026-09-25'
status: 'done'
baseline_revision: 'ad5d6cdb1c6e196dea8441655f0e78bf26164ffb'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Nineteen tracked pages still teach `pixi install` / `-e local-recipes` for everyday work (`grep -rl 'pixi install\|-e local-recipes' README.md CLAUDE.md docs .claude/skills`, 2026-09-25); `docs/reference/developer-guide.md` is not one of them.

**Approach:** Derive the surface with that grep at dispatch, then name `pixi install -e pyforge-foundry-full` as the laptop install on every page it lists, in `AGENTS.md` (through `bmad-project-context`) and the CFE / steward skill docs; keep `local-recipes` for recipe-factory work at scale.

## Boundaries & Constraints

**Always:**
- Derive the page list at dispatch; the epic's list is the 2026-09-25 snapshot.
- CFE files: invoke `conda-forge-expert` (Rule 1) and land its retro + `CHANGELOG.md` entry (Rule 2).
- `docs/reference/library-llms-full.md` is regenerated, never hand-edited.
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per named Spec, re-run the check and read its exit code; never a bare stamp.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not change the managed block by hand.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| doc names an install | any page the grep lists | `pyforge-foundry-full` for laptops | fix in the same change |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-12`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `67-5-the-estate-points-at-the-sbom`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-67-5-the-estate-points-at-the-sbom.md`.

## Epic excerpt

**Type:** docs • **Effort:** S • **Deps:** S-67.2 • **FR/AD:** fnd:CAP-12 • Dream 2026-09-25 (campaign phase 4)
**Surface:** every page that teaches an install or names `-e local-recipes` for everyday work — derived at dispatch with `grep -rl 'pixi install\|-e local-recipes' README.md CLAUDE.md docs .claude/skills`, which on 2026-09-25 lists `CLAUDE.md`, `docs/tutorials/getting-started.md`, `docs/tutorials/local-platform-development.md`, `docs/how-to/pixi-tasks.md`, `docs/how-to/recipe-testing-and-builds.md`, `docs/how-to/configure-your-coding-agent.md`, `docs/how-to/launch-a-cost-saving-interactive-session.md`, `docs/how-to/troubleshooting-recipe-builds.md`, `docs/how-to/feedstock-platform-expansion.md`, `docs/how-to/presentation-deck.md`, `docs/how-to/ocp-cluster-bringup.md`, `docs/how-to/ai-engine-operations.md`, `docs/reference/station-cheat-sheet.md`, `docs/reference/container-base-layer-convention.md`, `docs/reference/library-llms-full.md` (regenerated, not hand-edited), `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` (Rule 1: invoke `conda-forge-expert`; Rule 2: the CFE retro and `CHANGELOG.md` entry land with it) and `.claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md` (+ its `active/` twin); `AGENTS.md` (managed-block lines through `bmad-project-context`). `docs/reference/developer-guide.md` carries no install line today.
**Given** the laptop gate is green on `main`
**When** this story lands
**Then** each surface names `pyforge-foundry-full` as the laptop install and `local-recipes` only for recipe-factory work at scale; `governance-currency` and scribe's parity meta-test stay green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `grep -rl 'pixi install -e local-recipes' README.md CLAUDE.md docs .claude/skills` — expected: no page teaches it as the laptop install.
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (`governance-currency`).
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (parity meta-test).

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (self-review of delta; estate doc surfaces were already on branch HEAD from prior landing work)

## Auto Run Result

Status: done

Summary: Closed the remaining 67.5 gap — CFE Rule-2 retro (v8.92.0) naming `pyforge-foundry-full` as the laptop install, generator intros for `docs/how-to/pixi-tasks.md` and `docs/reference/environments.md`, and spec-surface memlogs on cutover, steward, and mason Specs. Branch HEAD already carried the epic-listed doc/tutorial/how-to/steward-skill/`library-llms-full.md` prose from earlier work on this line.

Files changed (this delta):
- `.claude/skills/conda-forge-expert/*` — install policy + cheatsheet callout + semver bump
- `scripts/docs_pixi_tasks.py`, `scripts/docs_environments.py` — laptop SBOM intro paragraphs
- `docs/how-to/pixi-tasks.md`, `docs/reference/environments.md`, `docs/map.yaml` — regenerated stamps
- Spec memlogs: `spec-python-foundry-cutover`, `spec-pyforge-steward`, `spec-pyforge-mason`

Verification:
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile
- `pixi run -e pyforge-guild llms-full-check` — clean
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — pass after sanctioned `retro:` commit (CFE guard)
- Manual: `grep -rl 'pixi install -e local-recipes' …` hits only pages that pair it with `pyforge-foundry-full` as factory add-on, not as sole laptop install

Follow-up review recommended: false
