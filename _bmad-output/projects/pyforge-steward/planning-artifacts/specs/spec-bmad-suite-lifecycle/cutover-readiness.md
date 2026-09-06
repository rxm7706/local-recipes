# Cutover readiness — the BMAD-estate prerequisites python-foundry assumes

Companion of `spec-bmad-suite-lifecycle` (CAP-9). Derived 2026-09-06 from
`spec-python-foundry-cutover/SPEC.md` (constraints :123-163), the cutover spine
`fnd:AD-5 / AD-12 / AD-17 / AD-20`, Epic 44, `customization-inventory.md`, and the era-alignment
chain. The gate: every P line green before Story 44.3 opens the foundry. Owners act; steward reads.

## P — must be true in `local-recipes` before Phase 0

| # | Prerequisite | Source | State 2026-09-06 | Owner → story |
|---|---|---|---|---|
| P1 | Every Spec re-renders from its memlog without loss | Epic 44 Story 44.13; `fnd:AD-20` | not done (44.13 `backlog`; 127 SPEC.md, 128 memlogs) | steward 44.13 |
| P2 | `spec-pyforge-unifying-strategy`'s "never re-derive" exception retired, reconciled first | 44.13 AC-2; `AGENTS.md:22` | exception live | steward 44.13 |
| P3 | Every spine has a `.memlog.md` | `fnd:AD-20` | satisfied (11/11) | — |
| P4 | No hand-edited SPEC.md; memlog is the single writer | `AGENTS.md:22` | policy; enforced by 44.13 | steward 44.13 |
| P5 | Ledgers generated, feed repaired before any write | cutover SPEC :160-163 | in force | — |
| P6 | Physical-path writes with `BMAD_ACTIVE_PROJECT`; no parallel `bmad-switch` | cutover SPEC :160-162 | in force | — |
| P7 | No in-place edits of installer-owned files; customizations in `_bmad/custom/**` or CAP-8-re-applied | 44.5 AC; `fnd:AD-5`; inventory C1/C5 | **violated** (C1 `resolve_config.py`; C5 seven skill files) — CAP-8 re-applies them at every apply | steward (mechanism shipped, 14.8); marshal 31.4 governs them |
| P8 | Config pins sit at the installer's own key paths | inventory C2 | satisfied (99e595cc6a) | doctor 20.2 adds the render-HALT detector |
| P9 | skf provisioned by its own installer (class own-installer) | install-class playbook :21,62 | mixed (dual-installer by design; custom-module registration kept) | steward 46.7 (pin) |
| P10 | `_bmad/skf/config.yaml` hand-set keys survive an apply; `skf-export` accepts `skills/stations/<x>/` | inventory C7; `fnd:AD-5` | keys restored by CAP-7; export root **unverified** | steward 47.2 |
| P11 | No shims; harness = `bmad-build-auto` | inventory C9; era-alignment CAP-12 | **not done** (21 shim dirs; `harness_bmadloop.py:328`) | marshal 30.5; steward 14.9 |
| P12 | No `project-context.md` rulebooks, readers migrated | inventory C13; era-alignment CAP-9 | **not done** (8 files, 4 readers) | marshal 30.2 |
| P13 | Every in-place-edited installer file under a spec `surface:` | inventory §2 item 5 | 5 of 7 ungoverned | marshal 31.4 |
| P14 | AGENTS.md block written only by `bmad-project-context` / `skf-export` | `fnd:AD-6`, `AD-17` | in force | — |
| P15 | `bmad-module-skill-forge uninstall` never run | inventory C20; AGENTS pitfall | recorded | — |
| P16 | No loop running at the flip; 8 homes re-provisioned attended | `fnd:AD-12`, `AD-17`; 44.12 | mechanism = 44.12 (not built); readiness undefined | marshal 31.5 defines; steward 44.12 builds |
| P17 | `gh` can create a private repo; paid plan persists | cutover SPEC :185-187 | assumption | steward 44.3 |

## G — gaps the cutover texts assume but nothing tracked (relayed 2026-09-06)

| # | Gap | Evidence | Relay |
|---|---|---|---|
| G1 | `_bmad/**` missing from Epic 44 `[epic_surfaces]` (AD-12 moves it in 44.5; MRS-GATE-007 would fire) | `marshal-policy.toml` `"44"` | steward 47.3 |
| G2 | Epic 44 has no dependency on Epic 14 (customization re-apply) or Epic 30 (era tail) | `epics.md` 44.x `Deps:` | steward 47.5 |
| G3 | No story retired the shims or flipped the harness | inventory C9 | marshal 30.5; steward 14.9 |
| G4 | Rulebooks unclassified for the move (neither Dream, memlog, nor narrative) | AD-20 buckets | marshal 30.2 (they retire) |
| G5 | `skf-export` accepting `skills/stations/<x>/` asserted, never proven | `fnd:AD-5` | steward 47.2 |
| G6 | 44.13's scope omits spine memlogs; only one `bmad-architecture` re-derive is exercised (44.14) | AD-20 vs 44.13 AC | steward 47.5 (memlog note on 44.13) |
| G7 | render-HALT class (ambiguous config key kills every rendering skill) has no detector | inventory C2 | doctor 20.2 |
| G8 | `_bmad-output/PROJECTS.md` has no cutover-target layout (marker/junction vs `bmad-switch`) | `PROJECTS.md:36-46,68-85` | steward 47.3 |
| G9 | Foundry Stack table has no `bmad-*` floor row; win-64 excludes skf + eval-quality | cutover spine :249-260 | steward 47.4 |
| G10 | Loop-home readiness undefined (`pyforge.toml name = "local-recipes"`, own `_bmad/`) | `fnd:AD-12`; `DW-CC-2026-09-04-1` | marshal 31.5 |
| G11 | `frozen-path-changed` detector named by AD-22/AD-11, never built | cutover spine :159,225 | doctor 20.3 |

## Re-derived by the cutover (never pre-build here)

Every rendered SPEC/spine/epic; `.claude/skills/` adapters (generated per machine); the
`bmad-switch` marker and the two planning symlinks; loop-home remotes; CLAUDE.md / AGENTS.md path
rewrites (`skf-export`); spec-surface baselines; `environment.yaml`.
