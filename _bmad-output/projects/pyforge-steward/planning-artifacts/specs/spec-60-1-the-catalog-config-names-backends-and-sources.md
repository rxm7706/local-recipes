---
title: '60.1: The catalog config names backends and sources'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred: []
declared_low_risk: false
baseline_revision: 'f843ba9137758782c8b626f3708b00716c58166a'
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
- Given the story lands, when `git status` is inspected, then no file outside `src/shared/packages/pyforge-steward/**`, the steward specs dir, `scripts/.spec-surface-baseline.json`, and the co-governor `spec-pyforge-core/.memlog.md` (one dated reconcile line) changed, no Epic 44 ledger key moved, and no GitHub repository was created.

## Spec Change Log

- 2026-09-19 (dev): `slots` is read as *every declared backend/source whose `state` is not `on`* — the Code Map's "declared-but-unbound off/available entries" and the AC's exact list (`object-storage`, `git-bundle`, `public-bmad-catalog`, `claude-skill-registry`) only agree that way, since `ObjectStorageBackend`/`GitBundleBackend` are default plugins and therefore bound. Each `backends[]`/`sources[]` row carries `bound` so the unbound subset is still one filter away. `slot-unbound` stays exactly as specified (only `state: on` naming an unregistered plugin).
- 2026-09-19 (dev): `state` accepts bare YAML `on`/`off` (YAML 1.1 booleans) and normalizes them to the words; the shipped `catalog.yaml` quotes them anyway.
- 2026-09-19 (dev): `EstateListingsSource` also enforces the file-level `source:` (must be `estate-listings`, else a `config-source` finding) so a mis-sourced registry with `modules: []` is not a silent green; the per-row mismatch is `listing-source-mismatch` as specified. A module listing whose `repository` is not a GitHub `owner/repo` is omitted from the Claude manifest (its `github` source form cannot express it) — not a finding in this story.
- 2026-09-19 (dev): three pre-existing steward tests were fixed in the same sitting (team memory `pre-existing-findings-fix-now-is-the-default`): `test_track.py` `_SCHEMA` path (`_PKG.parents[1]` → `_PKG.parent`, latent under `importorskip("jsonschema")`), and the two "missing share" provision tests now pin `CONDA_PREFIX` to an empty tmp env so a fat ambient env (pyforge-guild ships the tea/labs share trees) cannot make them red. Named in the memlog entry.
- 2026-09-19 (dev): `pyforge-marshal/spec-pyforge-core` co-governs `src/shared/packages/pyforge-steward/src/**` and reports drift on `catalog.py`/`cli.py`; its memlog is outside this story's surface (AC 7 / dispatch gate), so that reconcile (`.memlog.md` entry + `--write-baseline --spec pyforge-marshal/spec-pyforge-core`) is left for the landing pass, as PR #1511 did.
- 2026-09-19 (verify, supersedes the line above): the co-governor reconcile was done in this dispatch after all — `marshal/core/policy.py` `DEFAULT_POLICY["scope_violation_mode"]` is `warn` and steward's `marshal-policy.toml` does not override it, so one out-of-surface memlog line is a WARN advisory, not a gate failure, and team memory says fix-now is the default. Appended the dated co-governor line to `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` (imports stay inside `pyforge.steward`; one `ValueError` subclass at the config boundary; no django/marshal/network/subprocess) and re-stamped `--spec pyforge-marshal/spec-pyforge-core`; `python -m pyforge.doctor.sources spec-surface` is now `ok`. AC 7 amended to admit exactly that one file. KEEP: the reconcile belongs in the story that causes the drift, not on `main` after merge.

## Review Triage Log

### 2026-09-19 — Review pass

- verdicts: 49 findings — high 0, medium 9, low 35, false 5, maybe-false 0 (Blind Hunter 13, Edge Case Hunter 23, Verification Gap 4, Intent Alignment 9; BH12 is one finding logged as two rows, BH12a/BH12b, because its two halves route differently)
- findings:
  - `[medium]` `[defer]` BH1 committed manifest bakes recipe `version`/`description`; a recipe-only PR (no steward CI trigger) leaves `main` with `manifest-drift`, surfacing red on the next unrelated steward PR — real (VG2 reproduced it by patching `read_recipe_version` → drift fires); the in-contract closure is CI wiring (`recipes/bmad-*/**` + `docs/foundry/frames/**` on the steward trigger, or `steward catalog render --check` in `detectors-ci`) and a render gate before 60.3 ships a snapshot — both outside this story's surface; recorded in `deferred:`
  - `[medium]` `[patch]` BH2 duplicate listing names across sources are not a finding → two same-named plugins in the manifest — real (`_collect` never compares names); patched: `listing-duplicate` finding keyed on `(kind, name)` naming both producing sources
  - `[low]` `[patch]` BH3 `TRUST_TIERS` declared, never enforced; `bmad-certifed` reaches the manifest as a tag — real; patched: `EstateListingsSource` raises `CatalogConfigError` (→ `config-source`) for a tier outside `TRUST_TIERS`
  - `[medium]` `[patch]` BH4 `_github_owner_repo` accepts `git@github.com:acme/x.git` → invalid `source.repo` — real (verified by execution: returns `git@github.com:acme/x`); patched: exactly two `[A-Za-z0-9_.-]+` segments, everything else → `None`
  - `[low]` `[patch]` BH5 `path` is catalog-relative for `estate-listings` and repo-relative for `estate-frames`, undocumented — real; patched: anchor stated on both `catalog.yaml` rows and in both plugin docstrings
  - `[low]` `[patch]` BH6 "empty slot" not representable: `plugin` is mandatory even for `off`/`available` rows — real (`_parse_decls` raises without `plugin`); patched: `plugin` optional when `state` is not `on`, `claude-skill-registry` shipped as `plugin: null` with `skillsctl` named in a comment
  - `[low]` `[patch]` BH7 misspelled top-level sections load as zero backends/sources; `edit_store.kind: svn` accepted — real; patched: unknown top-level keys and `kind != "git"` are named `CatalogConfigError`s
  - `[low]` `[patch]` BH8 estate.yaml header advertises upstream fields the loader ignores and omits the keys it reads — real (docs); patched: header documents the accepted row keys and which reach the manifest; pass-through of `author`/`license` to the manifest is an enhancement, not a defect, and was not added
  - `[low]` `[patch]` BH9 a module listing without a GitHub `owner/repo` is silently dropped from the Claude manifest with no record — real; patched: non-GitHub git URLs render with Claude's documented `{"source":"url","url":…}` plugin-source form, and a module row with no repository is a `listing-no-repository` finding
  - `[low]` `[patch]` BH10 memlog says "landed" while the story is in review and counts 41 tests vs 43 — real; patched: reworded to "dispatched (in review; lands with its PR)" with the final count, scoped stamp re-taken
  - `[low]` `[patch]` BH11 estate.yaml header "must equal" vs code "if present" for the file-level `source:` — real inconsistency; patched: header softened to "when present, must equal; absent means `estate-listings`" (rows already default to it, so absence is not a mis-sourced file)
  - `[low]` `[defer]` BH12a `.claude/skills/pyforge-steward/…/SKILL.md` "Registered duties" roster lacks `catalog` (already lacked `cutover`, `ledger-query`) — real but it is an SKF-managed agent-context file outside this story's surface; recorded in `deferred:`
  - `[low]` `[patch]` BH12b `--catalog DIR` only works before the verb and nothing says so — real (`steward catalog check --catalog DIR` exits 2, verified); patched with ECH20/21: `--catalog`/`--json` accepted on both parser levels (`default=argparse.SUPPRESS` on the verb level)
  - `[low]` `[patch]` BH13 a bare `on:` key under `backends:`/`sources:` becomes a declaration named `"True"` — real (YAML 1.1); patched: non-string or empty declaration keys are a named `CatalogConfigError`
  - `[low]` `[patch]` ECH1 a source raising anything but `CatalogConfigError` aborts the whole check (backends already guard `Exception`) — real (`_collect` catches only `CatalogConfigError`); patched: `Exception` → `config-source` finding, remaining sources still run
  - `[false]` `[reject]` ECH2 frames listed although preflight "returned early" on a count mismatch — `frames.py:171-235` never returns early: the `count` finding is recorded with `path=root` and every doc is still parsed and validated per-doc, and the catalog skips docs with per-doc findings; the premise is false
  - `[low]` `[patch]` ECH3 a non-UTF-8 `*.frame.md` raises `UnicodeDecodeError` out of `_collect` — real (`preflight_frames` uses `read_text`); same defect as ECH1, closed by the same `Exception` guard
  - `[low]` `[reject]` ECH4 a committed manifest that is not valid UTF-8 escapes `drift()`'s `OSError` guard — real but the file is generated by `render` as UTF-8 and committed; nobody meets this in everyday use and the fix adds a guard
  - `[medium]` `[patch]` ECH5 `render`/`render --check` use `listings()` which discards collect findings: a broken `estate.yaml` renders manifests missing its rows and `render --check` says "in sync" — real (VG3 reproduced with `modules: 3`); patched: collect findings fail `render`/`render --check` with nothing written
  - `[low]` `[patch]` ECH6 rows with empty/mismatched `source` are still rendered (tag `source:`) — real; same root cause as ECH5, closed by excluding flagged rows from the render
  - `[medium]` `[patch]` ECH7 `_github_owner_repo` also passes `o/r#readme` — real (verified); same defect as BH4, one regex fix
  - `[low]` `[patch]` ECH8 `trust_tier` unvalidated — same defect as BH3
  - `[low]` `[patch]` ECH9 estate `version: 1.10` becomes `"1.1"` — real (`str(1.1)`); patched: mirror `read_recipe_version` (str, non-bool int, else `None`)
  - `[low]` `[patch]` ECH10 absent file-level `source:` accepted despite the header's "must" — same defect as BH11 (header patched)
  - `[medium]` `[patch]` ECH11 duplicate listing names — same defect as BH2
  - `[low]` `[reject]` ECH12 duplicate keys inside `catalog.yaml` silently last-wins — real (PyYAML), but the fix is a `SafeLoader` subclass and a duplicated declaration key is not an everyday edit; the real-tree test pins the exact declared sets, so the shipped file cannot drift this way unnoticed
  - `[low]` `[patch]` ECH13 non-string declaration key → `"True"` — same defect as BH13
  - `[low]` `[patch]` ECH14 `dedicated_repo` accepts any non-empty string although the error text promises `owner/repo` — real; patched: rejected unless `_github_owner_repo(value) == value`
  - `[low]` `[patch]` ECH15 `edit_store.kind` not pinned to `git` — same defect as BH7's second half (patched)
  - `[low]` `[patch]` ECH16 `display_name: ""` renders Codex `displayName` as `""` — real; patched: empty stripped value falls back to `name`
  - `[low]` `[patch]` ECH17 an option present as YAML null yields `conda://None/…` or a path named `None` — real (`dict.get` default does not apply to a present null); patched: null treated as absent in the three backends and both source `path` lookups
  - `[low]` `[patch]` ECH18 printed `--custom-source` / `/plugin marketplace add` commands are not shell-quoted — real; patched: `shlex.quote` on the path
  - `[low]` `[patch]` ECH19 a crash at the duty boundary emits plain text under `--json` — real; patched: JSON `{"ok": false, "findings": [{"code": "internal", …}]}` when `--json`
  - `[low]` `[patch]` ECH20 `steward catalog --json` (default verb) exits 2 — real (verified); patched with BH12b/ECH21
  - `[low]` `[patch]` ECH21 `--catalog` after the verb exits 2 — same defect as BH12b
  - `[false]` `[reject]` ECH22 `slots` lists bound-but-off backends — by design: this spec's AC 1 names `object-storage` and `git-bundle` as slots, the report carries `bound` per row, and the reading is recorded in the Spec Change Log; a fix would be a spec-wording edit, which triage does not route
  - `[low]` `[patch]` ECH23 "all `--json`" but the verb-less default path has no `--json` — same defect as ECH20
  - `[low]` `[defer]` VG1 (gap, filed `defer`) the `test_track.py` `_SCHEMA` fix is never executed in either CI lane — `jsonschema` is not in the `pyforge-steward` env, so `importorskip` skips the test there (verified: `SKIPPED … could not import 'jsonschema'`); closing it means a `pixi.toml` dep change (shared-surface rule) outside this story; recorded in `deferred:`
  - `[medium]` `[defer]` VG2 (gap, filed `defer`) committed manifests and real-tree pins depend on inputs (`recipes/bmad-*`, `docs/foundry/frames/**`) that never trigger the steward CI job — same root cause as BH1; recorded in `deferred:`
  - `[medium]` `[patch]` VG3 `render` exits 0 dropping a broken source's rows and `render --check` blesses it — same defect as ECH5
  - `[medium]` `[patch]` VG4 SSH remote accepted by `_github_owner_repo` — same defect as BH4
  - `[low]` `[reject]` IA-a "plugin, not a rewrite" is proven at the engine surface; a third-party source still needs a line in `default_sources()` (no discovery hook) — accurate, but the intent's "not a rewrite" is met by an additive class + registration (R3a), this spec's AC 6 names the engine registry as the extension point, and an entry-point/import-path discovery mechanism is new public surface for a consumer that does not exist yet
  - `[false]` `[reject]` IA-b the I/O row says "Error Handling: n/a" but `slot-unbound` errors — the row's scenario (add a declared source) yields a slot with no error exactly as implemented for `off`/`available`; `slot-unbound` is a different state (`on` naming nothing runnable), defined by this spec's AC 6
  - `[low]` `[patch]` IA-c "empty slot" cannot be expressed as empty — same defect as BH6
  - `[false]` `[reject]` IA-d `slots` semantics re-derived by the dev — same refutation as ECH22
  - `[low]` `[reject]` IA-e operator confirm is recorded (`dedicated_repo: null`, pointers note) rather than surfaced as a decision — an unattended run cannot ask; the pending decision is named under `## Auto Run Result` § Residual risks, which is the surfacing this run has
  - `[low]` `[patch]` IA-f `kind` not constrained to `git`; trackedness untested — `kind` pin is the same defect as ECH15 (patched); trackedness is evidenced by the spec-surface baseline (built from `git ls-files`) and its coverage detector, so no separate test was added
  - `[low]` `[patch]` IA-g `pointers` never run on the real tree; the repo-relative `directory` path is unasserted — real test gap; patched: real-tree test asserts `source.path == src/shared/packages/pyforge-steward/catalog` and `dedicated_repo: null`
  - `[false]` `[reject]` IA-h pre-existing test fixes, the co-governor memlog line, and the AC 7 amendment have no anchor in the contract — descriptive, no bad outcome claimed: the fixes follow team memory (fix-now), the reconcile follows the governed-surface rule, and each is logged in the Spec Change Log
  - `[low]` `[patch]` IA-i real-tree tests hard-code `13` and `9` — real coupling; patched: derived from `frames.EXPECTED_COUNT` and the module-class `SUITE_PACKAGES` rows so a tenth frame fails in `frames.py` first

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
