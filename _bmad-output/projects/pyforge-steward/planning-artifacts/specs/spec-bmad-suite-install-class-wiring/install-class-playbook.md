# Install-class playbook — the six that are not CAP-3 modules

Companion to `spec-bmad-suite-install-class-wiring` CAP-1. Native commands
and hazard flags are **cited from** `../spec-bmad-suite-channel-product/install-matrix.md`
(CAP-4 dual-path contract, verified 2026-08-22 against upstream READMEs) —
never invented here. The npm collision denylist travels with that matrix:
never install `bmad-dashboard` (caionormando), `bmad-skills` (bacoco), or
`bmad-method-ui` (lorenzogm) expecting the suite.

WDS stays the parent skip (deprecated → `bmad-ux`). The CAP-3 five
(`bmb`, `tea`, `cis`, `utility-skills`, `manticore`) stay on
`steward provision --module`. This page does not reopen those decisions.

`wired-or-not` (CAP-2) is the class predicate in the rightmost column —
not a boolean only `--module` targets can satisfy.

| Piece | Install class | Pixi / PATH | Native wire (cited) | Steward surface | wired-or-not predicate |
|---|---|---|---|---|---|
| **bmad-method** | Core / npm CLI installer | conda-forge canonical; SelfExplainML refresh-parity | `npx bmad-method install` (matrix: README L16; bins `bmad`, `bmad-method`) | Epic 14 upgrade + prove-landed; **not** `--module` | installer tree: `_bmad/core` + BMM present; Genesis must never write there |
| **bmad-loop** | uv-from-git tool / orchestrator | pixi pin (+ optional `uv tool install …@git`) | `uv tool install "bmad-loop[tui] @ git+https://github.com/bmad-code-org/bmad-loop.git@v0.11.0"` (matrix: README) — not on PyPI | existing `steward provision --runner bmad-loop --env …`; **not** `--module` | runner home / worktree provisionable |
| **bmad-module-skill-forge** (skf) | Own npx installer (+ module into `_bmad`) | pixi pin (suite pixi gap closed 2026-08-22) | `npx bmad-module-skill-forge install` (matrix: README § Install; Node ≥22, Python ≥3.10, uv) | channel pin + native install; **`--module skf` refused** (Spec non-goal) | skf skills present via its own installer |
| **bmad-labs-skills** | Claude plugin / `skills add` marketplace | optional pixi package | `npx skills add bmad-labs/skills` (matrix: README "Recommended") or `/plugin marketplace add …` | channel pin + CAP-4 matrix spot-check; **not** `--module` | plugin path documented; enabled only with operator consent |
| **bmad-dashboard** / **mybmad-dashboard** | Build / self-host app | pixi `bmad-ui` feature | dashboard: Node 22+, `corepack prepare pnpm@10.26.2`, `pnpm install && pnpm build` (matrix: README); mybmad: `cd web && pnpm install`, `scripts/setup.sh` (web/README) | publish + pin + `pixi run bmad-dashboard-install` (VS Code); **not** `--module` | install task runnable (VS Code extension / web build) |
| **bmad-module-template** | GitHub template scaffold | channel mirror (optional) | GitHub **template repo** — "Use this template"; not an installable package (matrix) | channel completeness only; **no provision-into-repo** | scaffold N/A unless creating a new module repo |

## How then (operator path)

1. Read this playbook (`steward provision --help` points here once CAP-1
   lands). Cross-check native commands against `install-matrix.md` if a
   citation has moved.
2. Pixi-install the six pins the same way as the rest of the suite (parent
   dual-path contract). Do not add any of them to `_SUPPORTED_MODULES`.
3. Wire each class with the cited native command / steward verb above.
   Method first-install is the upstream installer, never steward; steward
   Epic 14 only upgrades an already-installed core.
4. Confirm `wired-or-not` per the class predicate (pipeline-truth CAP-1,
   class-correct per this Spec's CAP-2). Template reports N/A in this
   monorepo.

## Fresh-clone target (CAP-3)

Method core installed, loop runner provisionable via `--runner`, skf
skills present via its own installer, labs plugin path documented,
dashboard install task runnable, template N/A unless scaffolding — zero
improvised npm `Installer` class driving from a chat transcript.
