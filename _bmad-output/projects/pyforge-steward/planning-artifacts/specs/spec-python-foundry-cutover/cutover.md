---
companion-of: spec-python-foundry-cutover
updated: "2026-09-04"
---

# Cutover — phases, target tree, faces, order

Promoted 2026-09-04 out of `docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md`
§ *One working tree*, where Story 43.1 had filed it under "do not build". The living
Dream § *Cutover to `python-foundry`* carries the same table; this file is the
contract's copy and adds the tree, the faces and the do-not-carry list.

## The flag and the plan (iteration 2)

`pyforge.cutover_root` in `src/platform/config/flags.json` is the root of record; the transition point is its flip, after 44.5 today, and flipping back is the rollback. `steward cutover plan --regenerate` rebuilds the manifest from scratch; `--append` folds in the delta since its recorded `source_sha`; both keep `moved` rows. `steward cutover apply --phase <n>` replays a phase into foundry as often as the plan changes. Until the flip, `local-recipes` evolves normally.

## Phases → stories

| Phase | CAP | Story | Do | Done when | Gate |
|---|---|---|---|---|---|
| — | CAP-2 input | 44.1 move-list manifest | every tracked path → target-tree destination, `stays`, or `dies`, derived from the spec-surface map | 100 % of tracked files resolve to one destination; source SHA recorded | — |
| — | Constraints | 44.2 document fixes | R-23 `readOnlyRootFilesystem` + Windows / free-threading claims aligned to the Containerfile and `pixi.toml` platforms; R-24 Keycloak `26.4.0` pinned once; R-25 "no station-domain models on `django-<station>`"; `stack.md` / `convergence.md` floor `3.12.*` → `3.14.*` | edits land; `DW-RT-2026-09-02-7/-8/-9` resolved | — |
| 0 — Open foundry | CAP-1 | 44.3 | create `rxm7706/python-foundry`, workspace `pyforge`, empty of recipes, lean `pixi.toml`, estate-only CI; env export automated or not carried (R-17a) | clone exists; CI green on the empty estate | **outward** — `blocked` until the operator flips |
| 1a — Fold the packages | CAP-2 | 44.4 | `src/shared/packages/` → `src/packages/`; a `pixi.toml` per `django-*`; drop `sys.path` inserts and Containerfile `COPY` of django src; `five_tier.py` `_packages_root` retargeted; package fold only | station envs solve; host boots in foundry | deps 44.1, 44.3 |
| 1b — Move the estate | CAP-2 | 44.5 | skills → `skills/` (`stations/`, `personas/`, `domain/`) with `.claude/skills/` + `.cursor/skills/` as symlink adapters; BMAD, decks, dreams | adapters are symlinks; the BMAD chain resolves in foundry | deps 44.4; never blended with 44.4 |
| 2 — CFE comes home | CAP-3 | 44.6 | authoritative skill / scripts / tools → `skills/domain/conda-forge-expert`; retros land in foundry; `pyforge/mason/resolve.py` chain (flag → `MASON_CFE_ROOT` → cwd walk) retargeted | no `MASON_CFE_ROOT` resolves to `local-recipes`; CFE surface + rebuild guards pass | **Mason** (Rules 1 + 2); deps 44.5 |
| 3 — Factory island | CAP-4 | 44.7 | `factory/pixi.toml` + own lock; `factory/recipes/`, `build-locally.py`, `.ci_support/`, `conda-forge.yml`; recipes-only CI on `paths: factory/**` (R-17b) | `mason recipe build factory/recipes/<r>` matches today's CFE wrap; `DW-RT-2026-09-02-1` resolved | deps 44.3 |
| 4 — Working set | CAP-5 | 44.8 | move in-flight + sole-maintainer recipes only | `factory/recipes/` is the working set; universe not copied (count ceiling asserted) | deps 44.7 |
| 5 — Mason → conda-forge | CAP-6 | 44.9 | `submit` → staged-recipes or bot fork; `update` → feedstock maintainer-edit | an agent PR never opens `local-recipes` (asserted on the submit path) | **outward + Mason**; deps 44.6, 44.8 |
| — | CAP-1..3 | 44.11 Windows-native estate | generated per-machine links (junctions on Windows), long-path preflight, no shell-only tasks, win-64 CI leg, `var/` state home | link check and detectors green on a Windows runner; a stock Windows clone runs recipes and station CLIs | deps 44.3 |
| — | CAP-8 | 44.12 cutover flag + replay harness | `pyforge.cutover_root` flag + `pyforge-core` reader; `steward cutover plan --regenerate\|--append` and `apply --phase` | both modes preserve `moved` rows; apply is idempotent; the flip switches ledger, Mason targets, loop homes | deps 44.1 |
| 6 — Archive | CAP-7 | 44.10 | README superseded; disable Azure; pin last SHA; keep history; retire the worktree residue (268 registered; 85 GB under `.claude/worktrees/`) | default clone is foundry; `.steward` has one git root | **outward, irreversible**; deps all |

**Order.** 44.1 ∥ 44.2 → operator flips 44.3 → 44.11 ∥ 44.12 → 44.4 → 44.5 → **flag flip** → 44.6 ∥ 44.7 → 44.8 →
operator flips 44.9 → operator flips 44.10. Every move before the flip is a replay (`fnd:AD-18`).

## Target tree

```text
python-foundry/                        # lasting git root (today: local-recipes)
├── pixi.toml                          # Workspace OS. Name: pyforge. No factory farm.
├── pixi.lock                          # Estate lock only. factory/pixi.lock is separate.
├── environment.yaml                   # Derived export — automated, or not carried.
├── AGENTS.md
├── factory/                           # Recipe island. Own lock. Not a platform.
│   ├── recipes/                       # Working set only
│   ├── pixi.toml + pixi.lock
│   ├── build-locally.py, .ci_support/
│   └── conda-forge.yml
├── .github/                           # Estate CI
├── config/                            # Deploy overlays. Secrets in env / cluster.
├── Containerfile
├── src/platform/                      # Foundry Platform. Never import pyforge.*.
├── src/packages/                      # TARGET. Not src/shared/packages/.
│   ├── pyforge-core/                  # python-cli-engine
│   ├── pyforge-<station>/             # × 8
│   ├── pyforge-atlas/                 # Only Kedro home + Vizro
│   ├── pyforge-testing-kit/
│   ├── django-pyforge/
│   └── django-<station>/
├── src/ides/  src/sentinel/  src/domains/<slug>/
├── templates/  presentations/pyforge-<station>/  docs/dreams/
├── skills/
│   ├── stations/<station>/SKILL.md    # × 7. Mason → domain/conda-forge-expert
│   ├── personas/<station>/SKILL.md
│   └── domain/conda-forge-expert/
├── .claude/skills/  (.cursor/skills/) # generated per-machine links, gitignored (fnd:AD-19)
├── var/                               # gitignored runtime state: atlas, cfe, worktrees
└── _bmad-output/projects/
```

## Five faces

| Face | Path |
|---|---|
| CLI | `src/packages/pyforge-<station>/` |
| UI | `src/packages/django-<station>/` |
| MCP | `POST /stations/<name>/mcp` on Foundry Platform |
| Skill | `skills/stations/<station>/` (mason: `skills/domain/conda-forge-expert`) |
| Agent | `skills/personas/<station>/` (`python-persona-engine` + harness) |

## Do not create / carry

`.claude/skills/pyforge-mason/` · lasting `src/shared/packages/` ·
`src/platform/compliance_face/` as the portal · `services/` or `:800x` · root
`docker-compose.yml` · `sys.path` for `django-*` · Containerfile `COPY` of django src ·
the `recipes/` universe · the 268 registered worktrees · `local-recipes` git history.

## Move-list manifest (44.1) — rules

- Source of truth is the spec-surface map (`scripts/spec_surface_check.py`): every
  tracked file already resolves to an owning Spec; the manifest adds a destination.
- One destination per path: a target-tree path, `stays` (archived with local-recipes),
  or `dies` (not carried). No path may resolve to two.
- Records the `local-recipes` source SHA the manifest was derived at; CAP-7 pins the
  final one.
