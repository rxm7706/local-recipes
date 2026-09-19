---
title: '60.1: The catalog config names backends and sources'
type: 'feature'
created: '2026-09-16'
status: 'draft'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Listings have no estate home and no named source.

**Approach:** Git is the edit store and backends/sources are declared in config. A new backend or source is a plugin, not a rewrite. Creating a new GitHub catalog repo needs operator confirm at this story.

## Boundaries & Constraints

**Always:**
- Backends and sources are declared in config.
- A new backend or source is a plugin, not a rewrite.

**Never:**
- Do not mint a new GitHub catalog repo without operator confirm.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new source | add a declared source | plugin slot, no rewrite | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-self-hosted-bmad-marketplace CAP-1`.
Surface: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-self-hosted-bmad-marketplace/backends-and-sources.md; a config the installer and Claude/Codex extraKnownMarketplaces can point at..
Ledger key: `60-1-the-catalog-config-names-backends-and-sources`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-60-1-the-catalog-config-names-backends-and-sources.md`.

## Code Map

- `src/shared/packages/pyforge-steward/catalog/` -- NEW catalog home, tracked in git (the edit store). Lives inside the steward package tree because Epic 60 has no `[epic_surfaces]` entry, so the dispatch gate's default surface (`marshal/core/gate.py:360` `default_epic_surface`) admits only `src/shared/packages/pyforge-steward/**`, the tracked specs dir, and bookkeeping paths. Not shipped in the wheel (`pyproject.toml` `packages = ["src/pyforge"]`) -- git is the store.
  - `catalog.yaml` -- OUR config: `catalog.{name,owner,edit_store}`, `backends.<name>{plugin,state}`, `sources.<name>{plugin,state,…}`; `state` ∈ `on|off|available` (the three v1 defaults in `backends-and-sources.md`). `edit_store.dedicated_repo: null` records that no GitHub repo is minted (operator confirm pending).
  - `registry/estate.yaml` -- estate listings in the upstream file format (`bmad-plugins-marketplace` `registry/registry-schema.yaml`: `modules: [{name, display_name, description, repository, author, license, type, category, subcategory, trust_tier, …}]`), plus an optional row `source:` that must equal `estate-listings`. v1 ships `modules: []` (operator ruling 4: start with no community modules; 60.2 owns publish + review).
  - `.claude-plugin/marketplace.json` -- GENERATED (never hand-edited) Claude Code marketplace manifest; the same file the BMAD installer's discovery mode reads (`docs/customize/add-modules.md`: `--custom-source` "Source contains `.claude-plugin/marketplace.json` → lists all plugins"). Required keys `name`, `owner`, `plugins[]`; each plugin `{name, description, version, source:{source:"github",repo}, tags:["source:<name>","trust:<tier>"]}`. Only `kind: module` listings render here.
  - `.agents/plugins/marketplace.json` -- GENERATED Codex marketplace manifest (shape from `bmad-code-org/bmad-plugins`: `{name, interface:{displayName}, plugins:[{name, source:{source:"local",path}, policy, category}]}`). Codex plugins need a `.codex-plugin/plugin.json` dir, which no wielded module repo has, so a listing renders here only when it declares `codex_source`; v1 → `plugins: []`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py` -- NEW engine + duty. Copy `sprint_ledger_query.py:303-400` (ABC + in-module registries, dup → `ValueError`, engine self-registers defaults) and `sync.py:97-170` (`SyncConfigError`, frozen config dataclass, `yaml.safe_load` only, four named load failures). Duty shape from `restore.py:36-65` (`class CatalogDuty: name = "catalog"; run(ns) -> DutyResult`, `try/except Exception` at the duty boundary, never `sys.exit` — AD-8).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py:140` `SUITE_PACKAGES` / `:70` `INSTALL_CLASS_MODULE` / `:427` `read_recipe_version` -- the `wielded-suite` source derives its rows from entries with `install_class == "module"` (tea, bmad-builder, cis, bmad-utility-skills); description from `recipes/<name>/recipe.yaml` `about.summary` (fail-open like `read_recipe_version`).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/frames.py:171` `preflight_frames` / `:90` `FrameDoc` -- the `estate-frames` source maps each frame's `identifier`/`name`/`description`/`version` to a `kind: frame` listing (reuse, never a second frame parser).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py:42` `DUTIES`, `:64` `_HELP`, `:165-194` `build_parser` elif-chain, `:1070` `resolve_duty` -- the four registration touch-points (lazy import on purpose).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/bootstrap.py` `repo_root()` -- root resolution every duty uses.
- `src/shared/packages/pyforge-steward/tests/unit/test_cli.py:35` `test_there_are_exactly_nineteen_duties` (literal tuple), `:100-118` bare-invocation list (`main(["catalog"])` must exit 0 on the real tree) ; `tests/unit/test_duty_protocol.py:15` (generic conformance, no edit).
- `src/shared/packages/pyforge-steward/tests/unit/test_sprint_ledger_query.py:455,510,728` -- plugin-slot test idioms to mirror (register a custom source without editing the engine; duplicate name raises).
- READ-ONLY: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-self-hosted-bmad-marketplace/backends-and-sources.md` (the load-bearing tables — the config mirrors its rows and defaults verbatim); `.claude/settings.json` (NOT wired in this story — a wrong `extraKnownMarketplaces` form would break every session; the duty prints the snippet instead); `pixi.toml` (no new task — a `pixi.toml` change fires all eight station suites in CI).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` + `scripts/.spec-surface-baseline.json` -- `src/shared/packages/pyforge-steward/**` is a governed surface; append a dated memlog entry naming every moved path, then `python scripts/spec_surface_check.py --write-baseline --spec pyforge-steward/spec-pyforge-steward` (after `git add`, per team memory).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/catalog/catalog.yaml` -- create: the three backends (`conda-channel` on, `object-storage` off, `git-bundle` available) and five sources (`estate-listings` on, `wielded-suite` on, `public-bmad-catalog` off + `cite:` URL, `estate-frames` on + `path: docs/foundry/frames`, `claude-skill-registry` off, `plugin: skillsctl`), `edit_store: {kind: git, repo: rxm7706/local-recipes, path: …/catalog, dedicated_repo: null}` -- the config is the declaration; every row of `backends-and-sources.md` appears by name with its v1 default.
- `src/shared/packages/pyforge-steward/catalog/registry/estate.yaml` -- create with `modules: []` and a header citing the upstream schema URL and the `source:` rule -- the reviewed-listings file 60.2 appends to.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py` -- create: `CatalogConfigError`, frozen `BackendDecl`/`SourceDecl`/`CatalogConfig`, `load_config(path)`; `Listing` (frozen: `name, kind, source, trust_tier, description, repository, version, code, install_hint, link, codex_source`); `CatalogSourcePlugin(ABC)` (`name`, `listings(ctx) -> list[Listing]`), `ShipBackendPlugin(ABC)` (`name`, `snapshot_target(decl) -> str` — the shared snapshot interface; 60.3 adds `ship`); `SourceRegistry`/`BackendRegistry` (`register`, dup → `ValueError`, `get`, `names`); default plugins `EstateListingsSource`, `WieldedSuiteSource`, `EstateFramesSource`, `CondaChannelBackend`, `ObjectStorageBackend`, `GitBundleBackend`; `CatalogEngine(repo_root, config)` with `check() -> CatalogReport` (findings: `config-*`, `slot-unbound` only when `state: on` names an unregistered plugin, `listing-no-source`, `listing-source-mismatch`, `manifest-drift`; `slots` = declared-but-unbound off/available entries), `listings()`, `render(write=bool)`, `pointers()`; `CatalogDuty` verbs `check` (default) / `list` / `render [--check]` / `pointers`, all `--json` -- one module, ledger-query shape.
- `src/shared/packages/pyforge-steward/catalog/.claude-plugin/marketplace.json` + `.agents/plugins/marketplace.json` -- generate with `steward catalog render` and commit; `render --check` must then report no drift.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- register `catalog` in `DUTIES`, `_HELP`, `build_parser` (`_add_catalog_subparsers`: verb subparsers with `--json`; `render --check`), `resolve_duty` -- the four touch-points.
- `src/shared/packages/pyforge-steward/tests/unit/test_catalog.py` -- create: config load (missing file, malformed YAML, non-mapping, unknown `state`, missing `plugin`), I/O-matrix "new source" (register a custom `CatalogSourcePlugin` and a custom backend against a config that declares them → `check` ok, no engine edit; the same declaration `on` without the plugin → `slot-unbound`; `off` without plugin → listed under `slots`, ok), duplicate registration raises, every listing names a source (estate row with `source: other` → `listing-source-mismatch`), wielded rows derive from `SUITE_PACKAGES` module class only, frames rows come from `preflight_frames`, render writes both manifests with required keys and only `kind: module` rows in the Claude one, `render --check` drift, `pointers` names `--custom-source`, `extraKnownMarketplaces` `directory` form, `/plugin marketplace add`, and `codex plugin marketplace add`; real-tree test: `check` on the repo is ok and manifests are in sync.
- `src/shared/packages/pyforge-steward/tests/unit/test_cli.py` -- update the literal `DUTIES` tuple test (twenty duties) -- bare `main(["catalog"])` stays in the dispatch-and-succeed set.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md` + `scripts/.spec-surface-baseline.json` -- memlog entry naming every moved path; re-stamp the scoped baseline -- governed-surface discipline.

**Acceptance Criteria:**
- Given the committed tree, when `steward catalog check` runs from repo root, then it exits 0 and its `--json` names every backend and source of `backends-and-sources.md` with its declared `state`, and `slots` lists exactly `object-storage`, `git-bundle`, `public-bmad-catalog`, `claude-skill-registry`.
- Given the committed tree, when `steward catalog list --json` runs, then every listing carries a non-empty `source` naming a declared source, the wielded rows are exactly the `install_class == "module"` suite packages at `trust_tier: bmad-certified`, and the frame rows are the nine `docs/foundry/frames/**/*.frame.md` identifiers at `kind: frame`.
- Given the committed manifests, when `steward catalog render --check` runs, then it reports no drift; and when a listing changes without re-rendering, then `check` reports `manifest-drift` and exits 1.
- Given `catalog/.claude-plugin/marketplace.json`, when read as JSON, then it has `name`, `owner.name`, `plugins[]`, each plugin has `name`, `source.source == "github"`, `source.repo`, and a `source:<name>` tag -- the shape `bmad-method install --custom-source <catalog dir>` (discovery mode) and Claude `extraKnownMarketplaces` resolve.
- Given `steward catalog pointers`, when it runs, then stdout shows the `--custom-source <abs catalog path>` line, an `extraKnownMarketplaces` JSON block using the `directory` source with the repo-relative catalog path, and notes that the `github` form waits on `edit_store.dedicated_repo` (operator confirm) -- and `.claude/settings.json` is unchanged.
- Given a config that declares a new source `on` with `plugin: x` and no plugin `x` registered, when `check` runs, then the only finding is `slot-unbound` for that source and exit is 1; when a `CatalogSourcePlugin` named `x` is registered on the engine, then `check` is ok with no edit to `CatalogEngine` -- the I/O-matrix row.
- Given the story lands, when `git status` is inspected, then no file outside `src/shared/packages/pyforge-steward/**`, the steward specs dir, and `scripts/.spec-surface-baseline.json` changed, no Epic 44 ledger key moved, and no GitHub repository was created.

## Spec Change Log

## Review Triage Log

## Design Notes

- **Consumer facts, verified 2026-09-19 (not from memory):** the BMAD 6.12 installer flag is `--custom-source <url|path>` (`--custom-content` in the Spec is a paraphrase); it resolves a source by `.claude-plugin/marketplace.json` (discovery mode). Claude Code `extraKnownMarketplaces.<name>.source` forms: `github{repo}`, `git{url}`, `url{url}`, `file{path}`, `directory{path}` (relative paths resolve against the main checkout, worktree-safe), `settings{name,plugins}`. Codex: `codex plugin marketplace add <owner/repo>` reads `.agents/plugins/marketplace.json`. Upstream registry file format: `registry/registry-schema.yaml` in `bmad-code-org/bmad-plugins-marketplace` (`trust_tier` enum `unverified|community-reviewed|bmad-certified`).
- **Provenance in their format:** Claude's plugin entry already uses the key `source` for "where to fetch", so the producing source is carried as `tags: ["source:<name>", "trust:<tier>"]` (a documented entry field), never a foreign key.
- **Tiers:** wielded suite rows are `bmad-certified` (ruling 5: "already in the wielded suite"); frame rows are `unverified` (validator = frame preflight passed); promotion is a 60.2 review record, not a 60.1 guess.
- **Backends in 60.1 are declarations with the shared snapshot interface** (`snapshot_target`); the conda publish itself is 60.3's story — a backend plugin here never claims to ship.
- **Not wired into `.claude/settings.json`** and no dedicated GitHub repo: both are operator-confirm moments; the `pointers` verb makes the pointing trivial without touching either.

## Verification

**Commands:**
- `PYTHONPATH=src/shared/packages/pyforge-steward/src python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_catalog.py src/shared/packages/pyforge-steward/tests/unit/test_cli.py src/shared/packages/pyforge-steward/tests/unit/test_duty_protocol.py -q` -- expected: all pass.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: the station suite green (the dispatch's configured verify).
- `PYTHONPATH=src/shared/packages/pyforge-steward/src python -m pyforge.steward.cli catalog check && python -m pyforge.steward.cli catalog render --check` -- expected: exit 0, no drift.
- `python -m pyforge.doctor.sources spec-surface` -- expected: no drift finding for `pyforge-steward/spec-pyforge-steward` after the memlog entry + re-stamp.
- `pixi run -e pyforge-steward pyforge-steward-coverage-gate` -- expected: `catalog.py` ≥ 80% unit coverage.
