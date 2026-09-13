# Install-class playbook — the eight that are not CAP-3 modules

Companion to `spec-bmad-suite-install-class-wiring` CAP-1. Native commands
and hazard flags are **cited from** `../spec-bmad-suite-channel-product/install-matrix.md`
(CAP-4 dual-path contract, verified 2026-08-22 against upstream READMEs) —
never invented here. The npm collision denylist travels with that matrix:
never install `bmad-dashboard` (caionormando), `bmad-skills` (bacoco), or
`bmad-method-ui` (lorenzogm) expecting the suite.

WDS stays the parent skip (deprecated → `bmad-ux`). The CAP-3 four
(`bmb`, `tea`, `cis`, `utility-skills`) stay on `steward provision
--module`; manticore graduated to the studio row below (46.6). This page
does not reopen those decisions.

`wired-or-not` (CAP-2) is the class predicate in the rightmost column —
not a boolean only `--module` targets can satisfy.

| Piece | Install class | Pixi / PATH | Native wire (cited) | Steward surface | wired-or-not predicate |
|---|---|---|---|---|---|
| **bmad-method** | Core / npm CLI installer | conda-forge canonical; SelfExplainML refresh-parity | `npx bmad-method install` (matrix: README L16; bins `bmad`, `bmad-method`) | Epic 14 upgrade + prove-landed; **not** `--module` | installer tree: `_bmad/core` + BMM present; Genesis must never write there |
| **bmad-loop** | uv-from-git tool / orchestrator | pixi pin (+ optional `uv tool install …@git`) | `uv tool install "bmad-loop[tui] @ git+https://github.com/bmad-code-org/bmad-loop.git@v0.11.1"` (matrix: README) — not on PyPI | existing `steward provision --runner bmad-loop --env …`; **not** `--module` | runner home / worktree provisionable |
| **bmad-module-skill-forge** (skf) | Own npx installer (+ module into `_bmad`) | pixi pin (suite pixi gap closed 2026-08-22) | `npx bmad-module-skill-forge install` (matrix: README § Install; Node ≥22, Python ≥3.10, uv) | channel pin + native install; **`--module skf` refused** (Spec non-goal) | skf skills present via its own installer |
| **bmad-labs-skills** | Claude plugin / `skills add` marketplace | optional pixi package | `npx skills add bmad-labs/skills` (matrix: README "Recommended") or `/plugin marketplace add …` | channel pin + CAP-4 matrix spot-check; **not** `--module`; documented native path (46.5): `steward provision --plugin labs --skill <name>`, consent list of exactly four — `mcp-builder`, `slides-generator`, `multi-repo-git-ops`, `release-please` | plugin path documented; enabled only with operator consent |
| **bmad-dashboard** / **mybmad-dashboard** | Build / self-host app | pixi `bmad-ui` feature | dashboard: Node 22+, `corepack prepare pnpm@10.26.2`, `pnpm install && pnpm build` (matrix: README); mybmad wielded path: estate Postgres `?schema=mybmad` + `COMPONENT_OIDC_*` (launcher `pg_ctl` + Better Auth is DEV FALLBACK ONLY) | Kedro-Viz via `steward deploy dashboard` (operator console is Lane 1 `/console/`; Guildhall generator retired). mybmad is a consume sidecar shown from django-pyforge chrome after the same OIDC session — **not** `/console/`, **not** `--module` | install task runnable (Kedro-Viz / `steward deploy dashboard`; mybmad sidecar process) |
| **bmad-module-template** | GitHub template scaffold | channel mirror (optional) | GitHub **template repo** — "Use this template" beside `bmad-builder`; not an installable package (matrix) | authoring tool only; **never** `steward provision --module` into `.claude/skills/` | scaffold N/A unless creating a new module repo |
| **bmad-eval-quality** (joined 2026-09-05, Story 45.1) | Bare CLI — no wiring target | pixi pin `bmad-eval-quality >=0.2.0.dev0` in `feature.local-recipes` (2026-09-05, after the SelfExplainML upload; `bin/eval-quality`) | `npm i -g eval-quality` (README § Install) — conda recipe pins the unreleased 0.2.0 line, npm 0.1.0 lacks `score` | channel pin only; **not** `--module`; the twin-run pilot (Story 45.2) is a consumer of the bin, not a wire | `eval-quality` executable on PATH → `runnable`; else `missing` (`INSTALL_CLASS_CLI`) |
| **bmad-manticore** (graduated 2026-09-07, Story 46.6) | module (`--custom-source`) — studio, not `--module` | optional pixi package (conda skills unused by the adopted path) | `npx bmad-method install --directory $PYFORGE_STUDIO_ROOT --custom-source https://github.com/bmad-code-org/bmad-manticore --yes --tools <full tool-id list>` (register row 9; both `--directory` and `--yes --tools <ids>` are REQUIRED for a non-interactive run — the bare command hangs on an unanswerable `Installation directory:` prompt, proven across 3 attempts; full command in `docs/reference/manticore-studio.md`) | documented native path (46.6); **not** `--module` for the adopted mechanism; `steward provision --module manticore` remains registered but unused | AD-3 declaration + studio `mc-*` census — `INSTALL_CLASS_STUDIO_MODULE`'s live probe (46.9, already landed) checks `$PYFORGE_STUDIO_ROOT`'s own `_bmad/` + a `mc-*` skill dir; reports `wired` now that 46.6 completed the studio install for real |

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

## Fresh-clone class-path (CAP-3) — recorded proof

A fresh clone of this repo already carries method core and skill-forge
skills in git. Follow this page — never a chat transcript that drives npm
`Installer` classes. Native commands below are **cited** from
`install-matrix.md`. Recorded proof: `steward provision --prove-class-path`
(CI job `pyforge-steward-fresh-clone`).

Operator console after 30.2: Lane 1 `/console/`. Kedro-Viz lives under
`docs/dashboard/kedro-viz/` and publishes with `steward deploy dashboard`.
The Guildhall generator and its four local-recipes pixi tasks (gen / watch /
check / drift-check) are deleted — do not resurrect them.

1. **bmad-method** — installer tree `_bmad/core` + `_bmad/bmm` (present on
   clone). First-install native (not steward): `npx bmad-method install`.
   Steward Epic 14 only upgrades an already-installed core.
2. **bmad-loop** — native `uv tool install "bmad-loop[tui] @ git+https://github.com/bmad-code-org/bmad-loop.git@v0.11.1"`.
   Steward wrap is `steward provision --runner bmad-loop` (flag stays; Story
   5.1 reports rather than materializes). Provisionable predicate: runner
   home `scripts/bmad-loop-worktree`.
3. **bmad-module-skill-forge** — own installer native
   `npx bmad-module-skill-forge install` (skills under `_bmad/skf` /
   `.claude/skills/skf-*`). Never a `--module` target.
4. **bmad-labs-skills** — plugin path documented:
   `npx skills add bmad-labs/skills`. Enable only with operator consent.
   The documented native path is `steward provision --plugin labs --skill
   <name>` (46.5) — the operator's 2026-09-06 consent list of exactly four:
   `mcp-builder`, `slides-generator`, `multi-repo-git-ops`, `release-please`.
5. **dashboards** — runnable class path is `steward deploy dashboard`
   (Kedro-Viz). Suite UI build-from-source remains
   `corepack prepare pnpm@10.26.2` and `pnpm install && pnpm build`
   (matrix). Not Guildhall `generate.py`.
6. **bmad-module-template** — GitHub **Use this template**. Scaffold N/A
   in this monorepo; do not provision the template into the tree.
7. **bmad-manticore** — native, entirely outside this repo:
   `npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-manticore`
   (matrix), plus the flags proven required for a non-interactive run
   (`--directory $PYFORGE_STUDIO_ROOT --yes --tools <ids>`; studio root
   `$PYFORGE_STUDIO_ROOT`, default `~/pyforge-studio/` — AD-3). Never
   `--module manticore` for the adopted mechanism (that backend stays
   registered, unused). Full command, prerequisites, and the isolation
   proof: `docs/reference/manticore-studio.md` (46.6).
