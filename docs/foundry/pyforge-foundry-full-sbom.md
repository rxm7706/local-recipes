# `pyforge-foundry-full` as the PyForge SBOM

**Status:** Phase 1 in this PR (env compose). Phases 2–4 are process/governance. **Phase 5 closes all conda-forge gaps** (SelfExplainML + pip + Node/`pnpm`/npm).
**Env:** `pixi install -e pyforge-foundry-full` (never the default session env).
**Not in scope:** the fat `local-recipes` feature (~200 library pins).

This environment is the estate **software bill of materials**: one solved, locked,
checkable closure for stations + CFE/Mason recipe generation + local build.

---

## Plan

### Phase 1 — Env = BoM (this PR)

Compose onto `pyforge-foundry-full`: `build` + `grayskull` + `crm` + `conda-smithy`

**Newly pulled:** `grayskull`, `conda-recipe-manager`, `feedrattler`, `conda-smithy`, plus build stack (`conda`, `conda-libmamba-solver`, `conda-index`, `conda-forge-pinning`, `conda-forge-ci-setup`, `networkx`, `frozendict`, `rattler-build-conda-compat`).

**Already present:** `conda-build` (warden), `rattler-build` / CFE floor (mason), **`nodejs`** (`feature.python`).

**Do not** duplicate those pins next to the feature list.

**Solve risk:** `crm`/`click` — refresh `pixi.lock` on a pixi machine (not in this PR).

### Phase 2 — Checkable SBOM

1. CI: `pixi install -e pyforge-foundry-full` on lock changes.
2. Export: `pixi list -e pyforge-foundry-full` (+ CycloneDX/SPDX optional).
3. Channel audit: tag every name `conda-forge` | `SelfExplainML` | `pypi` | `npm` | `path`; fail new non-CF without allowlist + **OpenTeams / Phase 5** ticket id.

### Phase 3 — OpenTeams triage issue list (tickets for everything)

**Done when every gap has an OpenTeams issue** — not when feedstocks land (that is Phase 5).

Phase 3 is the **issue board / tracking list**: one OpenTeams issue (or equivalent tracked ticket) for each row that Phase 2 surfaces or that Phase 5 already inventories. No silent gaps.

**Must have OpenTeams coverage for:**

| Bucket | Ticket IDs (from Phase 5 tables) |
|---|---|
| SelfExplainML → CF | CF-SEM-01 … CF-SEM-13 |
| Pip → CF | CF-PIP-01 (`sqlite-vec`) |
| Node tooling | CF-NODE-01 (`nodejs` — usually “already CF / keep”), CF-NODE-02 (`pnpm`) |
| npm → CF | CF-NPM-01 … CF-NPM-11 (atlas + herald) |
| Out-of-SBOM decisions | Explicit issues for anything left on fat `local-recipes` only (`codegraph`, `marp-cli`, `pptxgenjs`*, `vizro*`, `fastmcp*`, `kedro-mcp`, `bmad-suite`*, …) — either “promote later” or “never in foundry-full” |

**Phase 3 rules**

- One issue per package (or tightly coupled package set), linked from the channel audit.
- Issue states the current channel (`SelfExplainML` / `pypi` / `npm`), desired end state (`conda-forge`), and owner.
- Deferrals are still tickets (won’t-do / later) — not missing rows.
- **Closing** those issues by shipping CF packages = **Phase 5**, not Phase 3.

### Phase 4 — Point the estate at it

1. CFE / AGENTS / mason → **`pyforge-foundry-full`**, not fat `local-recipes`.
2. New deps must land in a feature foundry-full composes (or allowlist + **OpenTeams Phase 5** ticket).

### Phase 5 — Close all conda-forge gaps

**Execute the OpenTeams list from Phase 3.** One phase: everything the SBOM needs that is not yet on conda-forge gets a feedstock (or confirmed CF package) and is wired off SelfExplainML / pip / npm-only installs.

#### 5A. SelfExplainML → conda-forge

Already declared on foundry-full via guild/atlas (SEM channel). Need CF feedstocks, then drop SEM for these names.

| ID | Package | Declared in | Notes |
|---|---|---|---|
| CF-SEM-01 | `bmad-builder` | `feature.pyforge-guild` | BMAD suite |
| CF-SEM-02 | `bmad-creative-intelligence-suite` | `pyforge-guild` | |
| CF-SEM-03 | `bmad-dashboard` | `pyforge-guild` | |
| CF-SEM-04 | `bmad-eval-quality` | `pyforge-guild` (+ steward) | |
| CF-SEM-05 | `bmad-labs-skills` | `pyforge-guild` | |
| CF-SEM-06 | `bmad-manticore` | `pyforge-guild` | |
| CF-SEM-07 | `bmad-method-test-architecture-enterprise` | `pyforge-guild` | |
| CF-SEM-08 | `bmad-module-template` | `pyforge-guild` | |
| CF-SEM-09 | `bmad-utility-skills` | `pyforge-guild` | |
| CF-SEM-10 | `bmad-module-skill-forge` | `pyforge-guild` `target.linux-64` | |
| CF-SEM-11 | `caveman` | `pyforge-guild` `target.linux-64` | token-compression skill |
| CF-SEM-12 | `kedro-skills` | `feature.pyforge-atlas` | |
| CF-SEM-13 | `boring-semantic-layer` | `pyforge-atlas` | verify channel; include if non-CF |

#### 5B. Pip → conda-forge

| ID | Package | Declared in | Notes |
|---|---|---|---|
| CF-PIP-01 | `sqlite-vec` | `feature.pyforge-guild` `[pypi-dependencies]` | new CF feedstock; move to conda deps; drop pip pin |

#### 5C. Node / `pnpm` / npm → conda-forge

**Goal:** every Node tool and npm package the SBOM needs is **on conda-forge** (then consumed from the solve), not only via registry.npmjs.org.

**Tooling**

| ID | Package | Today | Action |
|---|---|---|---|
| CF-NODE-01 | `nodejs` | Already on foundry-full via `feature.python` (CF) | Keep |
| CF-NODE-02 | `pnpm` | On CF; pinned only under fat `local-recipes` (`>=12.4.1`) | Thin feature on foundry-full (no new feedstock if CF pin suffices) |

**Atlas wasm** — `src/shared/packages/pyforge-atlas/wasm/package.json`

| ID | npm name | Action |
|---|---|---|
| CF-NPM-01 | `@duckdb/duckdb-wasm` | CF feedstock (or equivalent conda name) |
| CF-NPM-02 | `esbuild` | Verify CF; feedstock if missing/too old |

**Herald web** — `src/shared/packages/pyforge-herald/web/package.json`

| ID | npm name | Action |
|---|---|---|
| CF-NPM-03 | `react` | CF feedstock or confirm existing |
| CF-NPM-04 | `react-dom` | CF feedstock or confirm existing |
| CF-NPM-05 | `vite` | CF feedstock or confirm existing |
| CF-NPM-06 | `vitest` | CF feedstock or confirm existing |
| CF-NPM-07 | `@vitejs/plugin-react` | CF feedstock |
| CF-NPM-08 | `jsdom` | CF feedstock or confirm existing |
| CF-NPM-09 | `@testing-library/react` | CF feedstock |
| CF-NPM-10 | `@testing-library/jest-dom` | CF feedstock |
| CF-NPM-11 | `@testing-library/user-event` | CF feedstock |

**Phase 5 done when:** every Phase 3 OpenTeams issue is closed by shipping CF (or an explicit won’t-do), and the channel audit no longer shows those names as SEM/pip/npm-only for the SBOM surface.

---

## Success criteria

- [ ] Phase 1 env solves; lock is the BoM artifact.
- [ ] Phase 2 CI + channel audit green.
- [ ] **Phase 3:** OpenTeams has a ticket for every CF-SEM / CF-PIP / CF-NODE / CF-NPM row (+ out-of-SBOM decisions).
- [ ] Phase 4 docs point at foundry-full.
- [ ] **Phase 5** closes those OpenTeams issues via conda-forge (or explicit deferral).

## Mental model

```
Phase 1–2  = make the SBOM env real and checkable
Phase 3    = OpenTeams issue list for EVERY gap (triage complete)
Phase 4    = point the estate at the env
Phase 5    = close those issues on conda-forge (SEM + pip + nodejs/pnpm/npm)
```
