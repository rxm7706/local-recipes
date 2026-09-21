# `pyforge-foundry-full` as the PyForge SBOM

**Status:** Phase 1 in this PR (env compose). Phases 2–4 are follow-on.
**Env:** `pixi install -e pyforge-foundry-full` (never the default session env).
**Not in scope:** the fat `local-recipes` feature (~200 library pins).

This environment is the estate **software bill of materials**: one solved, locked,
checkable closure for stations + CFE/Mason recipe generation + local build.

---

## Four-phase plan

### Phase 1 — Env = BoM (this PR)

Compose existing features onto `pyforge-foundry-full`:

`build` + `grayskull` + `crm` + `conda-smithy`

**Newly pulled conda packages** (not previously in the station union):

| Package | Feature | Role |
|---|---|---|
| `grayskull` | `grayskull` | PyPI/CRAN → recipe |
| `conda-recipe-manager` | `crm` | lint / migrate v0↔v1 |
| `feedrattler` | `crm` | feedstock → rattler-build (v1) |
| `conda-smithy` | `conda-smithy` | feedstock gen + lint |
| `conda` | `build` | solver; smithy CalVer needs it |
| `conda-libmamba-solver` | `build` | fast solve |
| `conda-index` | `build` | local repodata |
| `conda-forge-pinning` | `build` | global pins |
| `conda-forge-ci-setup` | `build` | CI-parity bootstrap |
| `networkx` | `build` | `.ci_support/build_all.py` |
| `frozendict` | `build` | build transitive |
| `rattler-build-conda-compat` | `build` | rattler ↔ conda-build shims |

**Already present:** `conda-build` (via `pyforge-warden`), `rattler-build` / CFE floor via `pyforge-mason`, `nodejs` via `python`.

**Optional later (not in this PR):** `pnpm` for `generate-npm` only.

**Do not** also paste those package pins next to the feature list — the features *are* the adds.

**Known solve risk:** `crm` historically isolated an exact `click` pin; refresh the lock on a pixi-capable machine and fix if the union fails. This PR does **not** refresh `pixi.lock`.

### Phase 2 — Checkable SBOM

1. CI: `pixi install -e pyforge-foundry-full` must succeed on lock changes.
2. Export inventory: `pixi list -e pyforge-foundry-full` (plus CycloneDX/SPDX if desired).
3. Channel audit: tag every name `conda-forge` | `SelfExplainML` | `pypi` | `npm` | `path`; warn/fail on new non-CF without allowlist + ticket id.

### Phase 3 — Feedstock / coverage backlog

Composing features does **not** put SelfExplainML / pip / npm onto conda-forge.
These tickets close the **channel** gaps for names already (or deliberately) in the SBOM.

#### A. SelfExplainML → conda-forge

Already declared on `pyforge-foundry-full` via guild/atlas (SEM channel). Need CF feedstocks, then drop SEM for these names.

| ID | Package | Declared in | Notes |
|---|---|---|
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

#### B. Pip → conda-forge

| ID | Package | Declared in | Notes |
|---|---|---|
| CF-PIP-01 | `sqlite-vec` | `feature.pyforge-guild` `[pypi-dependencies]` | headroom-ai proxy extra; new CF feedstock; move to conda deps; remove pip pin |

#### C. npm layer (herald / atlas) — policy, not pixi compose

| ID | Package(s) | Manifest | Decision |
|---|---|---|
| NPM-01 | `@duckdb/duckdb-wasm`, `esbuild` | `src/shared/packages/pyforge-atlas/wasm/package.json` | Keep npm SBOM layer (lockfile) **or** later CF; `esbuild` exists on CF but wasm stack is npm today |
| NPM-02 | `react`, `react-dom` | `src/shared/packages/pyforge-herald/web/package.json` | Same — npm layer vs CF packaging |
| NPM-03 | `vite`, `vitest`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/*` | herald `devDependencies` | Dev/tooling; usually stay npm |

`pnpm` alone does **not** put these on conda-forge; it only helps the optional `generate-npm` recipe path.

#### D. Explicitly out of foundry SBOM (unless later promoted)

`local-recipes`-only today: `codegraph`, `marp-cli`, `pptxgenjs` / `pptxgenjs-plus`, `vizro*`, `fastmcp*`, `kedro-mcp`, `bmad-suite` / `bmad-suite-full`, etc. Do not pull into foundry-full without an explicit SBOM decision.

### Phase 4 — Point the estate at it

1. CFE skill / AGENTS / mason docs: recipe gen + local build → **`pyforge-foundry-full`**, not fat `local-recipes`.
2. Governance: no new station/tool dep lands unless it is in a feature foundry-full composes (or allowlisted with a Phase 3 ticket id).

---

## Success criteria

- [ ] `pixi install -e pyforge-foundry-full` solves; lock is the BoM artifact.
- [ ] Channel audit lists only known Phase 3 gaps (or empty).
- [ ] CFE/Mason docs name this env.
- [ ] SelfExplainML / `sqlite-vec` / npm policy tickets closed or explicitly deferred.

## Mental model

```
pyforge-foundry-full  =  SBOM env (what must solve together)
         │
         ├─ Phase 1: + build/grayskull/crm/conda-smithy
         ├─ Already: guild/stations (includes SEM + pip sqlite-vec)
         └─ Phase 3: feedstock work → same names, conda-forge channel
                    + npm policy → lockfiles / optional CF pkgs
```
