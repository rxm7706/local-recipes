---
title: SKF domain skills from station packages
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - .claude/skills/skf-create-skill/SKILL.md
  - .claude/skills/skf-export-skill/SKILL.md
  - src/shared/packages/pyforge-scribe/
warnings: []
---

<intent-contract>

## Intent

**Problem:** Eight **03** stations owe a CAP-15 domain skill. The estate has an atlas-adjacent SKF skill (`cf-atlas-legacy`) and no `pyforge-<station>` skill compiled from `src/shared/packages/pyforge-<station>/`. canopy:FR-37 forbids proving the pattern on a station that already has a skill.

**Approach:** Compile one agentskills.io-compliant, version-pinned, provenance-backed content skill from a station package that has **no** skill today (`pyforge-scribe` — smallest CLI-complete station, no `.claude/skills/pyforge-scribe/`). Use the existing SKF module (`_bmad/skf/`, `.claude/skills/skf-*`, `skf-extract-public-api` / `skf-validate-frontmatter` / `skf-validate-output`). Do not invent a second compiler. Do not compile CAP-16 personas. Do not replace `conda-forge-expert`. Do not write `CLAUDE.md` / `AGENTS.md` except via `skf-export-skill` (this story skips export).

## Acceptance Criteria

- Given a station that has no skill today (`scribe`), when SKF compiles from `src/shared/packages/pyforge-<station>/`, then an agent loads `.claude/skills/pyforge-scribe/` (version-nested, `active` pointer) and the skill's instructions cover that station's core CLI task (`scribe capture` / `graph compile` / `recall`).
- Given the compiled package, when SKF validators run, then frontmatter is agentskills.io-compliant and `provenance-map.json` pins a git commit with `entries[]` citing `src/shared/packages/pyforge-scribe/`.
- Given `skf-create-skill` / SKF helper scripts are removed, when the steward meta suite runs, then those tests fail.
- Given `CLAUDE.md` and `AGENTS.md`, when this story lands, then they are unchanged (no export) **or** only `skf-export-skill` managed-section markers exist.
- Given `conda-forge-expert`, when this story lands, then it remains a flat hand-authored operating skill (not an SKF-compiled `pyforge-*` station skill; no SKF `metadata.json` `generated_by: create-skill` beside it).
- Given `src/platform/`, when scanned, then no `import pyforge` / `from pyforge` appears.

## Boundaries & Constraints

**Always:** Write specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`. Source is `src/shared/packages/pyforge-scribe/` (CLI package). Portal (`django-scribe/`) is out of this proof unless the skill claims portal coverage — it does not.

**Block If:** A second skill compiler is added; `conda-forge-expert` is regenerated or moved into SKF version layout; personas (`bmad-agent-*` station launchers) are authored; `pyforge.*` is imported under `src/platform/`.

**Never:** Story 29.2 personas. Story 29.3 five-tier CI check. Compiling all eight stations. Replacing CFE. Exporting into `CLAUDE.md`/`AGENTS.md` by hand. Draining other stations' stories.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Proof station | No `.claude/skills/pyforge-scribe/` on `origin/main` | Versioned skill + `active` symlink + brief | Atlas `cf-atlas-legacy` is not the proof |
| SKF compile | Brief `source_repo` = scribe package | `generated_by: create-skill`, provenance commit pin | Missing SKF scripts fail meta tests |
| Agent core task | Skill description + Quick Start | `scribe capture` / `scribe graph compile` / `scribe recall` documented with SRC cites | Do not tell agents to import `pyforge.scribe` internals (AD-7) |
| Export skipped | CLAUDE.md / AGENTS.md | Byte-identical to base (no SKF managed section) | Hand-edits of those files fail the meta test |
| CFE exception | `.claude/skills/conda-forge-expert/SKILL.md` | Still present, not version-nested SKF station skill | Adding `metadata.json` generated_by create-skill there fails the test |
| Host import | `src/platform/**/*.py` | No `pyforge` imports | Any `import pyforge` / `from pyforge` fails |

</intent-contract>

## Code Map

- `.claude/skills/pyforge-scribe/skill-brief.yaml` — SKF brief (create-skill input contract)
- `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/` — agentskills.io package (`SKILL.md`, `context-snippet.md`, `metadata.json`, `provenance-map.json`)
- `.claude/skills/pyforge-scribe/active` — symlink to `0.1.0` (same shape as `cfe-recipe-generation` / `cf-atlas-legacy`)
- `.claude/skills/skf-create-skill/` + `_bmad/skf/skf-create-skill/` — existing compiler (read-only)
- `.claude/skills/shared/scripts/skf-extract-public-api.py` — extraction used at compile
- `.claude/skills/shared/scripts/skf-validate-frontmatter.py` / `skf-validate-output.py` — validators tests invoke
- `src/shared/packages/pyforge-steward/tests/meta/test_skf_domain_skills.py` — canopy:FR-37 / canopy:AD-17 gates
- `src/shared/packages/pyforge-scribe/` — compile source (read-only)
- `.claude/skills/conda-forge-expert/` — must remain hand-authored (read-only)

## Tasks & Acceptance

**Execution:**
- Author SKF brief for `pyforge-scribe` from `src/shared/packages/pyforge-scribe/`
- Compile Quick-tier skill via SKF extract + create-skill artifact shape; pin commit
- Land version-nested package under `.claude/skills/pyforge-scribe/`
- Add steward meta tests for validators, provenance, SKF path presence, CFE untouched, no CLAUDE/AGENTS mutation, no `pyforge.*` under `src/platform/`

**Acceptance Criteria:**
- Given scribe had no skill, when the compiled skill is loaded, then Quick Start follows `scribe` CLI core tasks.
- Given SKF validate-frontmatter / validate-output, when run on the package, then high-severity issues are empty.
- Given SKF compile helpers are missing, when meta tests run, then they fail.
- Given CFE and context files, when this PR is reviewed, then CFE is unchanged and CLAUDE.md/AGENTS.md are not hand-edited.

## Design Notes

Proof station is **scribe**, not atlas (`cf-atlas-legacy` already exists) and not a persona. Public contract is the `scribe` CLI (package AD-7): `__init__.py` exports only `__version__`. SKF extract of `__init__.py` + `cli.py` yields `capture_cmd`, `graph_compile`, `recall_cmd`, `main`.

Export is optional this story: canopy:AD-17 says export is the **only** allowed write into CLAUDE.md/AGENTS.md; skipping export keeps those files clean.

Personas (CAP-16) consult this content skill later; they are BMAD launcher skills, not SKF output.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `ddafd7c6d8` (2026-08-25, "Merge pull request #796 from rxm7706/steward/29-1-ledger-finalize"); also `3069aed1ea` (2026-08-25, "Merge pull request #795 from rxm7706/steward/29-1-skf-domain-skills-from-station-packages"). Ledger row `29-1-skf-domain-skills-from-station-packages: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.cursor/pyforge-fleet-drain/queues.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready` → `done` (ledger row `29-1-skf-domain-skills-from-station-packages: done`).
- `## Auto Run Result` reconstructed from git (none survived).
