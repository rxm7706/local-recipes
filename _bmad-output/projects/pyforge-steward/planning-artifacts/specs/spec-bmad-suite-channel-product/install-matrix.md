# Dual-path install matrix — the tracked contract (CAP-4)

Verified 2026-08-22 against upstream READMEs (citations = the repo README
section named); **re-verified 2026-09-05** against
`pixi run -e pyforge-steward pyforge steward suite pipeline-truth --json`
(13/13 recipe = channel = installed). The version columns are a dated
snapshot — that command is the live source. Pixi path: `pixi add <name>` /
the existing pixi.toml pin, resolving from SelfExplainML (bmad-method from
conda-forge). One native path per class is spot-checked by the upgrade
verification gate.

| Package | Pixi (channel) | Native method (cited) | Hazards |
|---|---|---|---|
| bmad-method | conda-forge (canonical) 6.12.0; SelfExplainML refresh-parity 6.12.0 | `npx bmad-method install` (README L16; bins `bmad`, `bmad-method`) | npm current |
| bmad-loop | SelfExplainML 0.11.1 | `uv tool install "bmad-loop[tui] @ git+https://github.com/bmad-code-org/bmad-loop.git@v0.11.1"` (README) — NOT on PyPI | npm-invisible |
| TEA | SelfExplainML 1.24.0 | `npx bmad-method install` → select "Test Architect (TEA)" (README § Install); headless bin `tea-test-review` | npm current (the v1.23.3 tagged-unreleased watch closed 2026-09-05: 1.24.0 released) |
| bmad-builder | SelfExplainML 2.2.2 | `npx bmad-method install` → select "BMad Builder" | npm STALE (1.1.0, 2026-03) — GitHub canonical |
| creative-intelligence-suite | SelfExplainML 0.3.2 | `npx bmad-method install` → select CIS (README § Installation) | npm STALE (0.1.9) — GitHub canonical |
| bmad-module-skill-forge | SelfExplainML 2.1.0 (pixi pin landed 2026-08-22, linux-64 only — the one gap, closed) | `npx bmad-module-skill-forge install` (README § Install; needs Node ≥22, Python ≥3.10, uv) | npm current |
| bmad-eval-quality | PrivateChannel 1.4.1, BOTH noarch variants (`__unix` h07402fc_0 + `__win` h2fd06db_0) — tag-sourced (joined 2026-09-05 at 0.2.0.dev0 @ 3172162f, Story 45.1; class `cli`) | `npm i -g eval-quality` (README § Install) — npm is CURRENT (1.4.1, re-checked 2026-09-09); the long-standing 0.1.0-without-`score` staleness is resolved, so npm and GitHub agree | bare CLI, nothing wires into `_bmad`. The commit pin is retired — the recipe follows tags (CFE G109), so the "exact commit pin is load-bearing" caveat no longer applies. **Windows: CLOSED (mason Story 14.1, 2026-09-09).** The `__win` variant is built on a GitHub Actions windows-2022 runner and `__unix` on a macos-14 runner, because a staged-recipes PR builds the `__win` variant and then discards it (CFE G115); both are confirmed in the SERVED repodata, the `pixi.toml` pin left the unix-only target tables for the shared table, and a win-64 solve resolves `h2fd06db_0`. `steward suite pipeline-truth` reports `drifts: -` — upstream, recipe, channel and installed all 1.4.1 |
| bmad-utility-skills | SelfExplainML 2.0.0 @ HEAD | Claude plugin: `/plugin marketplace add https://github.com/bmad-code-org/bmad-utility-skills` → enable → `/reload-plugins` (README § Install) | npm-invisible; no tags ever |
| bmad-labs-skills | SelfExplainML 1.0.0.dev0 @ HEAD | `npx skills add bmad-labs/skills` (README "Recommended") or plugin marketplace | npm-invisible; `bmad-skills` on npm is UNRELATED (bacoco) |
| bmad-module-template | SelfExplainML 0.1.0 @ HEAD | GitHub **template repo** — "Use this template"; not an installable package | npm-invisible; dormant since 2026-04 |
| bmad-manticore | SelfExplainML 3.1.0.dev0 @ c9bcf759 | `npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-manticore` (README § Install) | npm-invisible; upstream renumbered past 2.0.0 untagged (G109) |
| bmad-dashboard | SelfExplainML 1.2.2.dev0 (bmad-ui env) | build from source: Node 22+, `corepack prepare pnpm@10.26.2`, `pnpm install && pnpm build` (README) | npm `bmad-dashboard` (1.0.19) is UNRELATED (caionormando) |
| mybmad-dashboard | SelfExplainML 0.1.0.dev0 (bmad-ui env) | self-host: `cd web && pnpm install`, `scripts/setup.sh`, PostgreSQL + migrations (web/README) | npm-invisible (`my-bmad` 404) |


**Retired from the matrix 2026-09-05:** `wds-expansion` (SelfExplainML 0.4.3; via `npx bmad-method install` → `_bmad/wds/`) — upstream `bmad-modules.yaml` marks it `deprecated: true`, folded into BMM as the `bmad-ux` skill; `--module wds` stays skip-decided in `steward provision`. Its recipe remains in-repo under `suite-members.yaml` `deprecated: true`; it is no longer a metapackage run dep. The roster stays at 13 — `bmad-eval-quality` took the seat.
**Greenfield one-pin (CAP-4).** The row-by-row table above is the per-package
reference; a fresh install of the *whole* suite does not need it. This repo's
`pixi.toml` carries an opt-in `feature.bmad-suite-full` that depends on the
published `bmad-suite` metapackage (SelfExplainML) instead of the ~11+
individual `bmad-*` pins:

```
pixi install -e bmad-suite-full
# or, from a project that only wants the feature added to its own manifest
# (that project's own pixi.toml must also list the SelfExplainML channel):
pixi add --feature bmad-suite-full bmad-suite
```

`bmad-method` stays **conda-forge canonical** (see the table's first row)
even inside the bundle — it is not a separate pixi pin when installing via
`feature.bmad-suite-full`; the metapackage's own `bmad-method >=6.12.0` run
dependency resolves it from conda-forge. `feature.bmad-ui`'s own install
surfaces (the VS Code extension registration via `bmad-dashboard-install`,
and the self-hosted MyBMAD web app via `mybmad`) remain a separate opt-in
feature that this bundle never wires. Note `bmad-suite` pulls **all 13**
active suite members by design (this metapackage's own success signal), so
the underlying `bmad-dashboard` / `mybmad-dashboard` conda packages do land
in the environment either way — this bundle just never sets up their
VS Code / web launch surfaces on its own.

This is the greenfield path only: this repo's own factory default
(`local-recipes` environment) keeps every explicit `bmad-*` pin from the
table above for pipeline-truth / doctor drift granularity and does **not**
compose `bmad-suite-full`.

**Class → gate spot-check candidates (one per class):** npm CLI → `npx
bmad-method --version`; bare npm CLI (`cli`, eval-quality) → `eval-quality --help`;
own-npx → `npx bmad-module-skill-forge --help`;
installer-selection → TEA via `bmad-tea-install` (conda parity of the same
flow); custom-source → manticore dry-run; plugin-marketplace → labs
`npx skills add --help`; uv-from-git → `uv tool install --help` (the native `uv tool install "bmad-loop[tui] @ git+https://github.com/bmad-code-org/bmad-loop.git@v0.11.1"` resolves over the network and `uv tool install` has no `--dry-run`, so the executable probe is the command family; 2026-09-06);
build-from-source → dashboards excluded from the gate (build cost), listed
check-by-doc.

**Name-collision denylist (never install these expecting the suite):**
`bmad-dashboard` (caionormando), `bmad-skills` (bacoco), `bmad-method-ui`
(lorenzogm).
