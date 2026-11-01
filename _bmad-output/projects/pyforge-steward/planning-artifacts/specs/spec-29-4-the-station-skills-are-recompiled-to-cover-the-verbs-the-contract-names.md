---
title: "29.4: The station skills are recompiled to cover the verbs the contract names"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md
  - .claude/skills/pyforge-marshal/skill-brief.yaml
  - .claude/skills/pyforge-steward/skill-brief.yaml
  - .claude/skills/pyforge-scribe/skill-brief.yaml
  - .claude/skills/pyforge-atlas/skill-brief.yaml
  - .claude/skills/skf-update-skill/SKILL.md
  - .claude/skills/skf-export-skill/SKILL.md
  - AGENTS.md
---

<intent-contract>

## Intent

**Problem:** AGENTS.md makes each station's `SKILL.md` the grammar reference ("read `.claude/skills/pyforge-<station>/SKILL.md` before touching" a station; "use the CLI grammar"), so a verb the skill omits reads as absent. The station skills Story 29.1 built are compiles of `865b95dc951`, and their `skill-brief.yaml` scopes list only the first CLI modules: marshal `cli/main.py`, `status.py`, `check.py`, `init.py`, `seed.py`; steward `cli.py`; scribe `capture.py`, `compile.py`, `recall.py`; atlas `mcp/tools.py`. So the skills miss commands AGENTS.md tells agents to run — marshal `factory dispatch`/`spin`, `context advisory`, `challenge`; steward `estate`, `ci`, `preflight`; scribe `catalog` (finding RUL-C3, cluster RUL-CL2). The atlas skill names `mcp/tools.py` functions (`run_pipeline`, `read_dataset`, …) as MCP tools instead of the tools `mcp/server.py` registers, and no skill says how to reach a station's `POST /stations/<s>/mcp` (finding RUL-D7, cluster RUL-CL13). The AGENTS.md SKF block's root path cannot point at each skill's `active/` root (`snippet_skill_root_override` gives one root for all), the skill half of RUL-CL1.

**Approach:** Widen each brief's `scope.include` to the modules that now carry the verbs, run `skf-update-skill` once per skill (MANUAL blocks preserved), then one `skf-export-skill` run, which regenerates the AGENTS.md SKF block and carries the snippet template, skill lines and atlas tool names of RUL-CL1, RUL-CL3 and RUL-CL13. Add a per-skill root pointer outside the SKF markers (or change the export layout). Each MANUAL block cites the station-MCP how-to the same PR writes as a doc. Re-check and close DW-FU-42-2-11 and DW-steward-75-1-2. One story, under done Epic 29 (Story 29.1 built these skills), and it runs last among the PR's code changes (operator ruling 2026-11-01).

Ledger key: `29-4-the-station-skills-are-recompiled-to-cover-the-verbs-the-contract-names`.
Type / Effort / Deps: fix / M / S-29.1.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-15** — "Every station teaches an agent its own work"; it governs the station skill files (canopy:FR-37, canopy:AD-17, as Story 29.1). A fix: no new CAP, no FR, no AD moves.

## Acceptance Criteria

- **AC1 — Scopes widened.** `scope.include` gains: in `.claude/skills/pyforge-marshal/skill-brief.yaml`, `src/pyforge/marshal/cli/spin.py`, `src/pyforge/marshal/cli/dispatch.py` (where `factory dispatch` registers), `src/pyforge/marshal/cli/context.py` and `src/pyforge/marshal/cli/challenge.py`; in `.claude/skills/pyforge-steward/skill-brief.yaml`, `src/pyforge/steward/estate.py`, `src/pyforge/steward/ci.py` and `src/pyforge/steward/preflight_verify.py` (the duty modules `cli.py` resolves for `estate`, `ci` and `preflight`); in `.claude/skills/pyforge-scribe/skill-brief.yaml`, `src/pyforge/scribe/catalog.py`; in `.claude/skills/pyforge-atlas/skill-brief.yaml`, `src/pyforge/atlas/mcp/server.py`.
- **AC2 — Recompiled.** `skf-update-skill` runs once per skill and each `.claude/skills/pyforge-<station>/0.1.0/pyforge-<station>/SKILL.md` (marshal, steward, scribe, atlas) lists the verbs AGENTS.md names for its station; every `[MANUAL:…]` block survives byte-identical except the AC4 citation; `provenance-map.json` pins the compile commit.
- **AC3 — Atlas tools.** The atlas skill's Key API and its MCP section name the tools `mcp/server.py` registers (`run_<pipeline>_pipeline`, `read_atlas_dataset`, `list_atlas_pipelines`, `list_atlas_datasets`), not the `mcp/tools.py` function names.
- **AC4 — How to reach a station host.** Each station skill's MANUAL block cites the `docs/how-to/` page on reaching a station MCP endpoint (starting the host, authenticating, the request shape), which the same PR writes with its `docs/map.yaml` row.
- **AC5 — One export.** One `skf-export-skill` run regenerates the AGENTS.md SKF block (never a hand edit inside its markers); AGENTS.md carries a pointer to each skill's `active/` root outside the SKF markers, or the export layout changes so the block names it.
- **AC6 — DW closed.** DW-FU-42-2-11 (the steward skill card omits `revoke` and `restore`) and DW-steward-75-1-2 (the steward skill lists `keys` without `exec`) in `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` close after a re-check against the recompiled `SKILL.md`, or stay open with the reason named.
- **AC7 — Reconciled and green.** The `spec-pyforge-unifying-strategy` memlog carries the surface reconcile naming the recompiled `SKILL.md` paths, and the stamp is `--spec pyforge-steward/spec-pyforge-unifying-strategy`; chain-currency re-runs for steward; `pyforge-steward-test`, `governance-currency` and the instruction-surface parity test exit 0.

## Boundaries & Constraints

**Always:**
- Recompile through `skf-update-skill` and export through `skf-export-skill` only; preserve every MANUAL block.
- Run last among the PR's code changes, so the compile reads the final tree.

**Never:**
- Never hand-edit compiled skill text outside a MANUAL block, or AGENTS.md inside the SKF markers; never edit the `bmad:context` block; never touch `.claude/skills/conda-forge-expert/`; never run `bmad-module-skill-forge uninstall`; never add a second compiler.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-unifying-strategy` CAP-15.

Parent: `spec-pyforge-unifying-strategy` CAP-15

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry; the operator ruling of 2026-11-01 is the `(decision)` entry on `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md`.
- Epic: Epic 29 (done; Story 29.1 built these skills).
- Ledger key: `29-4-the-station-skills-are-recompiled-to-cover-the-verbs-the-contract-names`.
- Deps: S-29.1.
- Surface: `marshal-policy.toml` `[epic_surfaces]."29"` does not cover `.claude/skills/` or `AGENTS.md`; this story is hand-landed in the audit PR, not dispatched. Its files are the four `skill-brief.yaml` and four compiled `SKILL.md` paths of AC1 and AC2, `AGENTS.md`, and `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`.
- Audit: EGM audit 2026-11-01 findings RUL-C3 (cluster RUL-CL2) and RUL-D7 (cluster RUL-CL13), with the skill halves of RUL-CL1 and RUL-CL3 (findings RUL-Z5, RUL-D5 and RUL-C2 name this story as a co-carrier); residue `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (the rules stage).
- Minted 2026-11-01 by the EGM fleet audit landing (marshal Story 113.7); lands in that PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite, the SKF meta-tests included; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_skf_domain_skills.py src/shared/packages/pyforge-steward/tests/meta/test_skf_steward_skill.py src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py -q` — expected: pass.
- `grep -n 'factory dispatch' .claude/skills/pyforge-marshal/0.1.0/pyforge-marshal/SKILL.md`, `grep -n 'estate' .claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md`, `grep -n 'catalog' .claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md`, `grep -n 'read_atlas_dataset' .claude/skills/pyforge-atlas/0.1.0/pyforge-atlas/SKILL.md` — expected: exit 0 each.
- `pixi run -e pyforge-guild governance-currency` — expected: exit 0.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `deferred-work-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), clusters RUL-CL2 and RUL-CL13, under done Epic 29 per the operator ruling of the same date; in the audit landing PR.

## Review Triage Log

- (none yet)
