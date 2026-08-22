# Dual-path install matrix — the tracked contract (CAP-4)

Verified 2026-08-22 against upstream READMEs (citations = the repo README
section named). Pixi path: `pixi add <name>` / the existing pixi.toml pin,
resolving from SelfExplainML (bmad-method from conda-forge). One native path
per class is spot-checked by the upgrade verification gate.

| Package | Pixi (channel) | Native method (cited) | Hazards |
|---|---|---|---|
| bmad-method | conda-forge (canonical); SelfExplainML refresh-parity | `npx bmad-method install` (README L16; bins `bmad`, `bmad-method`) | npm current |
| bmad-loop | SelfExplainML 0.11.0 | `uv tool install "bmad-loop[tui] @ git+https://github.com/bmad-code-org/bmad-loop.git@v0.11.0"` (README) — NOT on PyPI | npm-invisible |
| TEA | SelfExplainML 1.23.2 | `npx bmad-method install` → select "Test Architect (TEA)" (README § Install); headless bin `tea-test-review` | v1.23.3 tagged-unreleased (watch) |
| bmad-builder | SelfExplainML 2.2.1 | `npx bmad-method install` → select "BMad Builder" | npm STALE (1.1.0, 2026-03) — GitHub canonical |
| creative-intelligence-suite | SelfExplainML 0.3.1 | `npx bmad-method install` → select CIS (README § Installation) | npm STALE (0.1.9) — GitHub canonical |
| bmad-module-skill-forge | SelfExplainML 2.1.0 — **pixi pin to add** (the one gap) | `npx bmad-module-skill-forge install` (README § Install; needs Node ≥22, Python ≥3.10, uv) | npm current |
| wds-expansion | SelfExplainML 0.4.3 | via `npx bmad-method install` (README: installer places `_bmad/wds/`) | npm names stale (`bmad-wds` 0.3.1 / `whiteport-design-studio` 0.3.4); DEPRECATED upstream — skip wiring |
| bmad-utility-skills | SelfExplainML 2.0.0 @ HEAD | Claude plugin: `/plugin marketplace add https://github.com/bmad-code-org/bmad-utility-skills` → enable → `/reload-plugins` (README § Install) | npm-invisible; no tags ever |
| bmad-labs-skills | SelfExplainML 1.0.0.dev0 @ HEAD | `npx skills add bmad-labs/skills` (README "Recommended") or plugin marketplace | npm-invisible; `bmad-skills` on npm is UNRELATED (bacoco) |
| bmad-module-template | SelfExplainML 0.1.0 @ HEAD | GitHub **template repo** — "Use this template"; not an installable package | npm-invisible; dormant since 2026-04 |
| bmad-manticore | SelfExplainML 3.1.0.dev0 @ c9bcf759 | `npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-manticore` (README § Install) | npm-invisible; upstream renumbered past 2.0.0 untagged (G109) |
| bmad-dashboard | SelfExplainML 1.2.2.dev0 (bmad-ui env) | build from source: Node 22+, `corepack prepare pnpm@10.26.2`, `pnpm install && pnpm build` (README) | npm `bmad-dashboard` (1.0.19) is UNRELATED (caionormando) |
| mybmad-dashboard | SelfExplainML 0.1.0.dev0 (bmad-ui env) | self-host: `cd web && pnpm install`, `scripts/setup.sh`, PostgreSQL + migrations (web/README) | npm-invisible (`my-bmad` 404) |

**Class → gate spot-check candidates (one per class):** npm CLI → `npx
bmad-method --version`; own-npx → `npx bmad-module-skill-forge --help`;
installer-selection → TEA via `bmad-tea-install` (conda parity of the same
flow); custom-source → manticore dry-run; plugin-marketplace → labs
`npx skills add --help`; uv-from-git → `uv tool install --dry-run bmad-loop@git+…`;
build-from-source → dashboards excluded from the gate (build cost), listed
check-by-doc.

**Name-collision denylist (never install these expecting the suite):**
`bmad-dashboard` (caionormando), `bmad-skills` (bacoco), `bmad-method-ui`
(lorenzogm).
