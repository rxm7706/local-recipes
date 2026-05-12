---
doc_type: epics-and-stories
project_name: local-recipes
date: 2026-05-12
version: '1.0.0'
status: draft
source_pin: 'conda-forge-expert v7.7'
total_epics: 13
total_stories: 193
waves: 5
xl_stories_remaining: 0
tentative_decisions_applied: 7
input_docs:
  - planning-artifacts/PRD.md
  - planning-artifacts/architecture.md
---

# Epics & Stories: `local-recipes` Rebuild

This document breaks the rebuild into **13 epics organized into 5 dependency-ordered waves**, with story-level detail under each epic. Stories include: title, scope, acceptance criteria, complexity (S/M/L/XL), and dependencies on prior stories.

Build order follows `architecture.md` § 9 (Build Order). Wave 1 is foundational; later waves depend on earlier ones.

---

## Wave Summary

| Wave | Theme | Epics | Stories | Estimated complexity |
|---|---|---|---|---|
| **Wave 1** | Foundation: pixi monorepo + BMAD installer + auth chain | 3 epics | 27 stories | Foundational, must-be-correct |
| **Wave 2** | Part 1 core: conda-forge-expert skill (Tier 1 + 2 + docs) | 3 epics | 38 stories | Largest wave; the heart of the system |
| **Wave 3** | Part 2: cf_atlas data pipeline (17 phases + schema + CLIs) | 3 epics | 40 stories | Most complex single component |
| **Wave 4** | Parts 3+4 surfaces: MCP server + multi-project + integration | 2 epics | 21 stories | Smaller code but high-coupling |
| **Wave 5** | Hardening: tests + docs + air-gap validation + deployment | 2 epics | 16 stories | Validation + readiness |

**Total: 13 epics, 142 stories.** Estimates assume an experienced operator with Claude Code assistance.

---

# Wave 1: Foundation

Stories in Wave 1 establish the substrate every other Wave depends on. Until Wave 1 completes, nothing else can be built or tested.

---

## Epic 1: Pixi Monorepo Bootstrap

**Goal**: Establish the pixi-managed Python 3.12 monorepo with 8 envs and core dependencies. No code yet — just the substrate.

**Owner part**: cross-cutting (`pixi.toml`, `pyproject.toml`)

**Acceptance**: `pixi install -e local-recipes` succeeds; `pixi run health-check` placeholder returns success.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E1.S1 | Initialize repo + LICENSE + README | git init; BSD-3-Clause LICENSE; minimal README pointing at PRD; root `.gitignore` covering pixi/rattler/output dirs | LICENSE valid; README exists; root `.gitignore` covers `.pixi/`, `build_artifacts/`, `output/`, `.claude/data/`, plus `_bmad-output/projects/<slug>/implementation-artifacts/` content (gitignored) and per-project gitignored config files (`.bmad-config.user.toml`, `.active-project`) | S |
| E1.S2 | Author `pixi.toml` core | requires-pixi >=0.67.2; declare 8 envs (`linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`); set `# default-env: local-recipes` directive | `pixi info` shows 8 envs; default-env resolves correctly | M |
| E1.S3 | Add Python + build feature deps | `[feature.python]` with Python 3.12, conda, conda-libmamba-solver; `[feature.build]` with rattler-build, conda-build, conda-index, conda-forge-pinning, etc. | `pixi install -e python` resolves; `rattler-build --version` runs | M |
| E1.S4 | Add grayskull + conda-smithy + shellcheck features | Per-feature deps; matches existing pixi.toml | `pixi run -e grayskull pypi --help` works; `pixi run -e conda-smithy lint --help` works | S |
| E1.S5 | Add local-recipes feature (default env composite) | Composite env: `["python", "build", "grayskull", "conda-smithy", "local-recipes"]`; activation hooks. **Depends on E1.S3 (python+build features), E1.S4 (grayskull+conda-smithy features), AND E1.S2 (`[environments]` table exists).** Cannot start until all three are merged. | Default `pixi run` activates the right env; `pixi install -e local-recipes` resolves without error; activation hooks execute | M |
| E1.S6 | Add vuln-db feature with AppThreat | `[feature.vuln-db.pypi-dependencies]` with `appthreat-vulnerability-db`; `VDB_HOME` activation hook | `pixi install -e vuln-db` succeeds; `VDB_HOME` set on activation | M |
| E1.S7 | Add cross-platform features (linux, osx, win) | Per-platform feature dependencies; activation hooks for cross-compile env vars | `pixi install -e <platform>` works for each | M |
| E1.S8 | Add `scripts/load-env.sh` + `scripts/bmad-switch` STUB (real impl in E2.S5) | (a) `scripts/load-env.sh`: real impl — parses `# default-env:` directive from pixi.toml top of `[environments]` and activates that env. (b) `scripts/bmad-switch`: **stub only** — a 5-line Python script with `print('bmad-switch stub; full impl in E2.S5')` for `--list`/`--current`/`--clear`/`<slug>` that returns exit 2. **Contract with E2.S5**: same file path, same CLI subcommand surface; E2.S5 replaces the stub body with the real implementation. Reason for the stub: E1.S10 verify-env task needs `bmad-switch` to exist as a file even before E2.S5 lands. | `scripts/load-env.sh` activates correct env (real impl); `scripts/bmad-switch --list` returns exit code 2 with stub message (stub impl); file exists and is executable | S |
| E1.S9 | Create empty directory scaffolding | `.claude/{skills,scripts,tools,data,docs}/`; `recipes/`; `docs/`; `_bmad-output/projects/`; `build_artifacts/` (gitignored) | `find -type d` shows expected structure | S |
| E1.S10 | Verify-env pixi task (LAST in Epic 1) | `pixi run verify-env` validates pixi.toml integrity + env count + default-env directive presence + `scripts/bmad-switch` exists (even as stub) + `scripts/load-env.sh` activates default env. **Depends on E1.S2 (pixi.toml `[environments]` table) + E1.S5 (composite env) + E1.S8 (bmad-switch stub + load-env.sh).** Run this story LAST in Epic 1 ordering. | Task runs without error; reports 8 envs (`linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`); default-env resolves to `local-recipes`; bmad-switch present (stub or real) | S |

**Epic 1 total: 10 stories, complexity ~M average.**

---

## Epic 2: BMAD Installer + Multi-Project Layout

**Goal**: Install BMAD-METHOD; set up six-layer config merge; create per-project layout; implement active-project resolution.

**Owner part**: Part 4 (BMAD infrastructure)

**Acceptance**: `_bmad/scripts/resolve_config.py --key core` returns merged config; `scripts/bmad-switch --current` returns `local-recipes` after setting marker.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E2.S1 | Install BMAD-METHOD v6.6.0 | **Exact command**: `pixi add --pypi bmad-method==6.6.0` (adds to `local-recipes` pypi-dependencies), then `pixi run bmad install` (or equivalent installer entry point) which generates `_bmad/config.toml` (layer 1) + `_bmad/config.user.toml` (layer 2) + `_bmad/bmm/` module + `_bmad/core/` + `_bmad/scripts/{resolve_config.py,resolve_customization.py}` + installs **42 BMAD-installer skills** under `.claude/skills/bmad-*/`. Exact breakdown (sums to 42): **6 personas** (`bmad-agent-{analyst,architect,dev,pm,tech-writer,ux-designer}`) + **9 planning** (`bmad-create-{prd,architecture,epics-and-stories,story,ux-design}`, `bmad-edit-prd`, `bmad-validate-prd`, `bmad-product-brief`, `bmad-prfaq`) + **3 discovery** (`bmad-document-project`, `bmad-generate-project-context`, `bmad-customize`) + **3 research** (`bmad-domain-research`, `bmad-market-research`, `bmad-technical-research`) + **2 implementation** (`bmad-quick-dev`, `bmad-dev-story`) + **4 sprint/retro** (`bmad-sprint-planning`, `bmad-sprint-status`, `bmad-correct-course`, `bmad-retrospective`) + **5 review** (`bmad-code-review`, `bmad-review-adversarial-general`, `bmad-review-edge-case-hunter`, `bmad-editorial-review-prose`, `bmad-editorial-review-structure`) + **10 process/facilitation** (`bmad-advanced-elicitation`, `bmad-brainstorming`, `bmad-check-implementation-readiness`, `bmad-checkpoint-preview`, `bmad-distillator`, `bmad-help`, `bmad-index-docs`, `bmad-party-mode`, `bmad-qa-generate-e2e-tests`, `bmad-shard-doc`). If `pixi add --pypi bmad-method` fails on the operator's network, fall back to `pip install bmad-method==6.6.0` in the local-recipes env. | `_bmad/` exists with config + bmm/ + core/ + scripts/; `ls .claude/skills/bmad-* | wc -l` returns **exactly 42**; `python3 _bmad/scripts/resolve_config.py --project-root . --key core` returns valid JSON | M |
| E2.S2 | Implement `_bmad/scripts/resolve_config.py` | Six-layer TOML merge; Python 3.11+ stdlib `tomllib`; active-project resolution priority (CLI > env > marker > none); merge rules: **(a) scalars override (higher layer wins); (b) tables deep-merge recursively; (c) arrays of tables KEYED by `code` or `id` — matching entries replace by key, new entries append (e.g. `[[agents]]` arrays merged by `code`); (d) all other arrays append (cumulative).** Provide a fixture at `_bmad/scripts/tests/fixtures/merge/` with 6 input TOMLs (one per layer) + expected merged JSON output, exercising all 4 merge rules. Unit tests live in **this story** (not E2.S11). | `resolve_config.py --key agents` returns valid JSON on the fixture; fixture roundtrip test passes for each of the 4 merge rules; `resolve_config.py --project <slug> --key <foo>` correctly applies layers 5+6 | L |
| E2.S3 | Implement `_bmad/scripts/resolve_customization.py` | Per-skill customization resolver; reads `customize.toml` from skill root + `_bmad/custom/<skill>.toml` + `_bmad/custom/<skill>.user.toml`; same merge rules as global | `resolve_customization.py --skill <path> --key workflow` returns valid JSON | M |
| E2.S4 | Create `_bmad/custom/` directory + empty config | Empty `config.toml` (layer 3) + empty `config.user.toml` (layer 4); `.active-project` file gitignored but stub exists | `_bmad/custom/` exists; layers 3+4 resolve to empty | S |
| E2.S5 | Implement `scripts/bmad-switch` CLI (replaces E1.S8 stub) | Python script with full impl; `--list` / `--current` / `--clear` / `<slug>` subcommands; slug validation (`^[a-z0-9][a-z0-9_-]*$`); writes `_bmad/custom/.active-project` marker file. **Contract with E1.S8 stub**: same file path (`scripts/bmad-switch`), same CLI surface — this story replaces the stub body with the real implementation. Stub printouts go away; real subcommand outputs land. | All subcommands work against the actual `_bmad-output/projects/` directory; bad slug rejected with exit 2; non-existent project rejected with exit 2; marker file written at `_bmad/custom/.active-project`; `--current` reads the marker | M |
| E2.S6 | Create `_bmad-output/projects/local-recipes/` | Project subdirectory; empty `planning-artifacts/` + `implementation-artifacts/`; placeholder `.bmad-config.toml` (layer 5) | Directory exists; `bmad-switch local-recipes && --current` returns `local-recipes` | S |
| E2.S7 | Create `_bmad-output/projects/deckcraft/` + `presenton-pixi-image/` stubs | Same layout as local-recipes; gitignored content stubs | `bmad-switch --list` returns 3 project names | S |
| E2.S8 | Author `_bmad-output/PROJECTS.md` | Multi-project index with config layering table + active-project switching docs | File exists; renders cleanly | S |
| E2.S9 | Add engineering-practice skills | Copy or author **21 skills** under `.claude/skills/`: `api-and-interface-design`, `browser-testing-with-devtools`, `ci-cd-and-automation`, `code-review-and-quality`, `code-simplification`, `context-engineering`, `debugging-and-error-recovery`, `deprecation-and-migration`, `documentation-and-adrs`, `frontend-ui-engineering`, `git-workflow-and-versioning`, `idea-refine`, `incremental-implementation`, `performance-optimization`, `planning-and-task-breakdown`, `security-and-hardening`, `shipping-and-launch`, `source-driven-development`, `spec-driven-development`, `test-driven-development`, `using-agent-skills`. Source: copy from upstream BMAD-METHOD repo's published skills set, OR author from scratch using the BMAD skill format. | After this story (still pre-Wave-2): `ls .claude/skills/ | wc -l` returns **63** (42 from E2.S1 + 21 from this story). After Wave 2 lands the `conda-forge-expert` skill (E4.S1+): total becomes **64**. Note: the existing repo state shows 65 entries because `.claude/skills/data/` is a stray directory (no SKILL.md inside; contains only a `conda-forge-expert/` subdir with stale content); the rebuild does NOT recreate this stray. Target count for rebuild completion = 64 real skills. | M |
| E2.S10 | Authoring auto-memory entries (initial set) | `~/.claude/projects/<repo-slug>/memory/`: BMAD multi-project pattern, skill disambiguation defaults, BMAD-uses-CFE rule, CFE retro contract, three-place rule | MEMORY.md index lists all entries; each file has frontmatter + content | M |
| E2.S11 | E2 acceptance test: round-trip resolve | Test: set active project via CLI → env var → marker → none; `resolve_config.py` returns correct merged config in each case | All 4 priority cases pass | S |

**Epic 2 total: 11 stories, complexity ~M-L average.**

---

## Epic 3: Cross-Cutting Auth Chain + Permission Gates

**Goal**: Author `_http.py`, set up Claude Code permission gates, establish JFROG_API_KEY mitigation patterns in documentation.

**Owner part**: cross-cutting (lives in Part 1's `scripts/`)

**Acceptance**: `_http.py` handles all 4 auth modes; permission gates allow expected operations and deny `--force` push.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E3.S1 | Author `.claude/skills/conda-forge-expert/scripts/_http.py` skeleton | Module with `make_request(url, method='GET', **kwargs)` interface; truststore integration; **JFrog header injection on every outbound request unconditionally** (per ADR-010: documented constraint, host-aware refactor deferred to v2 — DO NOT add host scoping in this story); GitHub token detection; .netrc fallback. **The cross-host leak is intentional in v1; mitigation is operator env-var hygiene (documented in CLAUDE.md + project-context.md + docs/enterprise-deployment.md).** | Function returns response object; all 4 auth methods exercised in unit tests; JFrog header IS injected for every host (locked in by E3.S8 meta-test) | L |
| E3.S2 | Implement per-host `*_BASE_URL` resolution | Helpers: `resolve_conda_forge_urls()`, `resolve_pypi_url()`, `resolve_anaconda_api_url()`, `resolve_s3_parquet_url()`, `resolve_github_api_url()`; each prefers env-var override, falls through to public default | Each resolver returns env-var value if set, else default; unit tests pass | M |
| E3.S3 | Add `_http.py` unit tests | Tests for: truststore activation, JFROG_API_KEY header injection, GitHub token scoping, .netrc fallback, per-host BASE_URL resolution, request retry on 5xx | All tests pass; covers the 4-tier auth chain | L |
| E3.S4 | Document JFROG_API_KEY cross-host leak (CLAUDE.md) | Add Critical Constraint section to CLAUDE.md; cite mitigation pattern (subshell scoping) + reference deployment-guide.md | CLAUDE.md has the warning in a discoverable location | S |
| E3.S5 | Document JFROG leak (project-context.md § Air-Gapped) | Add to Air-Gapped/Enterprise section; enumerate external-host commands; unset-before-external pattern | project-context.md has the warning | S |
| E3.S6 | Document JFROG leak (docs/enterprise-deployment.md § 2) | Operational reference with subshell pattern + enumerated commands + per-shell discipline + direnv option | docs/enterprise-deployment.md has comprehensive coverage | M |
| E3.S7 | Author `.claude/settings.json` default permissions | Allow `Bash(rattler-build *)`, `Bash(pixi run *)`, `Bash(gh *)`, etc.; deny `Bash(git push --force *)` and variants; allow Skill(conda-forge-expert) | settings.json present with sensible defaults; `--force` push denied at permission layer | M |
| E3.S8 | Add `tests/meta/test_http_jfrog_scoping.py` (the v1→v2 trip-wire) | Meta-test verifying `_http.py` injects JFROG_API_KEY header unconditionally on every host (locks in the E3.S1 documented-constraint stance per ADR-010). **The test exists to BREAK when a future v2 refactor adds host-aware scoping — that's the refactor signal.** Until then, this test passes; after v2 refactor lands, this test is updated/replaced as part of the v2 effort (DW2). | Test runs and passes against E3.S1's `_http.py`; documents the v1 stance with a code-level assertion; test docstring cites ADR-010 + DW2 | S |

**Epic 3 total: 8 stories, complexity ~M-L average.**

**Wave 1 totals: 3 epics, 29 stories.**

---

# Wave 2: Part 1 — conda-forge-expert Skill

Wave 2 builds the heart of the system. Tier 1 canonical scripts, then Tier 2 wrappers, then documentation. After Wave 2, recipe authoring works end-to-end (modulo atlas-dependent features).

---

## Epic 4: Part 1 Tier 1 Canonical Scripts (Recipe Lifecycle)

**Goal**: Implement the 20-ish Tier 1 scripts that drive the recipe lifecycle (generate → validate → edit → scan → optimize → build → submit).

**Owner part**: Part 1 (canonical scripts)

**Acceptance**: All 20 Tier 1 scripts in `.claude/skills/conda-forge-expert/scripts/` accept `--json`, emit JSON, and have passing unit tests.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E4.S1 | `name_resolver.py` PyPI → conda name resolution | Read `pypi_conda_mappings/{custom.yaml,different_names.json}` + `mappings/pypi-conda.yaml`; resolve name with override priority | `python name_resolver.py --json --pypi-name requests` returns conda mapping | M |
| E4.S2 | `mapping_manager.py` mapping cache refresh | Fetch upstream mapping data; merge with custom overrides; write `pypi_conda_map.json` | `python mapping_manager.py --json` updates cache; `force=True` skips TTL check | M |
| E4.S3 | `recipe-generator.py` PyPI → recipe.yaml | grayskull subprocess invocation; post-process v1 schema header; CFEP-25 triad for noarch:python; license validation | Generates valid v1 recipe.yaml; passes validate_recipe | L |
| E4.S4 | `validate_recipe.py` schema + lint | rattler-build --render dry-run; license_file list validation; SPDX validation; schema_version=1 check | Returns valid/errors/warnings; matches schema | M |
| E4.S5 | `dependency-checker.py` PyPI → conda dep resolution | For each PyPI dep in recipe, resolve via name_resolver; check conda-forge availability; suggest alternatives | Returns dependency report with resolved/unresolved/alternative | M |
| E4.S6 | `recipe_editor.py` structured-action engine | Define action set: set-version, set-sha256, add-maintainer, add-dep, remove-dep, etc.; apply to recipe.yaml | Each action mutates correctly; round-trips through YAML parse | L |
| E4.S7a | `recipe_optimizer.py` skeleton + STD family | Module structure; STD-001 (missing stdlib), STD-002 (stdlib without compiler) | 2 codes flag correctly; module structure ready for additional families | M |
| E4.S7b | TEST family | TEST-001 (missing test commands), TEST-002 (single-string noarch:python python_version) | Both codes flag correctly on fixture recipes | S |
| E4.S7c | PIN + DEP + ABT families | PIN-001 (loose pins), DEP-001 (PyPI-only dep), DEP-002 (unavailable conda dep), ABT-001 (abandoned upstream signal), ABT-002 (archived feedstock dep) | All 5 codes flag correctly | M |
| E4.S7d | SCRIPT + SEL + MAINT + SEC + OPT families | SCRIPT-001 (bare pnpm/npm/yarn in build.bat), SCRIPT-002 (missing call prefix), SEL-001/2/3 (selector misuse), MAINT-001 (no maintainer), SEC-001 (Critical CVE unresolved), OPT-000 (generic optimizer warnings) | All 8 codes flag correctly | M |
| E4.S8 | `vulnerability_scanner.py` recipe → CVE | Read recipe.yaml; resolve to PyPI packages; query vdb (Phase G data) or OSV.dev; report Critical/High/etc. | Returns vulnerability report; integrates with vuln-db env | L |
| E4.S9 | `local_builder.py` rattler-build wrapper | Invoke rattler-build with right flags per platform; write `build_summary.json` on completion; write `build.pid` on start | Build runs; summary written; PID cleaned up | L |
| E4.S10 | `failure_analyzer.py` build log → diagnosis | Read conda_build.log; pattern-match against fixture error_logs/; suggest fix | Diagnoses common failures correctly on test fixtures | L |
| E4.S11 | `submit_pr.py` split flow | `prepare_branch()` (steps 1-6 of original) + `submit_pr()` (steps 7-8); --force-with-lease default; idempotent push | Both functions work; `--prepare-only` flag exposes prepare alone | L |
| E4.S12 | `github_updater.py` autotick for GitHub-only sources | Detect GitHub-only sources (no PyPI); fetch latest release; update version + SHA | Updates recipe; dry_run mode previews | M |
| E4.S13 | `github_version_checker.py` upstream version check | Hit api.github.com/repos/X/releases/latest; compare to recipe version | Returns ahead/behind/equal | S |
| E4.S14 | `npm_updater.py` npm-ecosystem recipe handling | `npm pack`; `pnpm-licenses` license capture; npm registry source URL | Generates valid npm recipe | M |
| E4.S15 | `feedstock-migrator.py` v0 → v1 migration | feedrattler subprocess; post-migration validation; cleanup | Migrates fixture v0 recipes to valid v1 | L |
| E4.S16 | `feedstock_context.py` get-context-for-feedstock | Query GitHub feedstock issues + PRs; format for AI agent consumption | Returns structured context dict | M |
| E4.S17 | `feedstock_enrich.py` recipe enrichment | Pull missing fields from feedstock metadata; merge into recipe.yaml | Enriches recipe; respects existing values | M |
| E4.S18 | `feedstock_lookup.py` lookup feedstock by name | Map package name → feedstock repo URL via cf-graph or conda-forge.org | Returns feedstock info | S |
| E4.S19 | `license-checker.py` license_file + SPDX validation | Verify license_file is a list; validate SPDX identifier; check license_file paths exist | Returns validation report | S |
| E4.S20 | `recipe_updater.py` version + SHA bump | Combined version update + SHA refresh; dry_run mode | Updates recipe; dry_run previews; round-trips cleanly | M |

**Epic 4 total: 23 stories** (was 20; +3 from E4.S7 split into S7a/b/c/d), complexity ~M-L average.

---

## Epic 5: Part 1 Tier 2 Wrappers + Pixi Tasks + Meta-Test

**Goal**: Implement the 34 CLI wrappers, the ~30 pixi tasks that drive them, and the meta-test that enforces the three-place rule.

**Owner part**: Part 1 (CLI wrapper layer)

**Acceptance**: `pixi run <task>` works for each Tier 2 wrapper; `tests/meta/test_all_scripts_runnable.py` passes.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E5.S1 | Author wrapper template for Tier 2 | Generic ~15-line subprocess wrapper that delegates to Tier 1 via `python <SCRIPTS_DIR>/<name>.py "$@"` | Template documented; copy-paste-ready | S |
| E5.S2 | Implement 18 recipe-lifecycle wrappers | For each Tier 1 in Epic 4 with a public CLI (skip the underscore-prefixed internals): create matching `.claude/scripts/conda-forge-expert/<name>.py` wrapper | All 18 wrappers exist; each runs `--help` without error | M |
| E5.S3 | Implement `prepare_pr.py` wrapper | Calls `submit_pr.py --prepare-only`; separate pixi task | `pixi run prepare-pr -- <recipe>` works; only pushes to fork | S |
| E5.S4 | Implement atlas + query wrappers (placeholder until Wave 3) | Stub wrappers for `atlas_phase.py`, `bootstrap_data.py`, `staleness_report.py`, `feedstock_health.py`, `whodepends.py`, `behind_upstream.py`, `version_downloads.py`, `release_cadence.py`, `find_alternative.py`, `adoption_stage.py`, `cve_watcher.py`, `health_check.py`, `scan_project.py`, `detail_cf_atlas.py`, `inventory_channel.py`, `cve_manager.py` (16 wrappers; some stubbed until Wave 3) | Each wrapper file exists; tests can subprocess them | M |
| E5.S5 | Define pixi tasks for all 34+ wrappers | Add `[feature.local-recipes.tasks.<name>]` for each wrapper with description; some args via `--` passthrough | `pixi task list` shows all tasks; each runs at least `--help` | M |
| E5.S6 | Implement `tests/meta/test_all_scripts_runnable.py` | SCRIPTS list of every Tier 1 + Tier 2; `no_task_allowlist` for internal-only; assert each script is reachable via pixi task OR allowed | Test passes; deliberate omission of a script causes failure | M |
| E5.S7 | Add docstrings + `--help` to every Tier 2 wrapper | argparse with description + per-arg help; docstring at module top | `pixi run <task> -- --help` returns sensible output for each | S |
| E5.S8 | E5 acceptance: full task surface enumeration | Document all tasks in `commands-cheatsheet.md` (placeholder; full content in Epic 6) | Each task listed in quickref | S |

**Epic 5 total: 8 stories, complexity ~S-M average.**

---

## Epic 6: Part 1 Documentation + Templates + Tests

**Goal**: Author SKILL.md, INDEX.md, CHANGELOG.md, 11 reference docs, 8 guides, 2 quickrefs, 41 templates (13 ecosystems), and the test suite.

**Owner part**: Part 1 (documentation + templates + tests)

**Acceptance**: All doc files exist with content; `pixi run test` passes; `tests/meta/test_recipe_yaml_schema_header.py` passes.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E6.S1a | Author SKILL.md Part A: principles + constraints | 6 Operating Principles + 5 Critical Constraints + frontmatter | Sections 1-2 of SKILL.md present (~150 lines) | M |
| E6.S1b | Author SKILL.md Part B: primary workflow | 10-step Autonomous Loop with step 8b human-gate detail | Section 3 present (~120 lines) | M |
| E6.S1c | Author SKILL.md Part C: atlas + security | Atlas Intelligence Layer + Recipe Security Boundaries (Always Do / Ask First / Never Do) | Sections 4-5 present (~150 lines) | M |
| E6.S1d | Author SKILL.md Part D: protocols | Build Failure Protocol + Pre-PR Quality Gate + Migration Protocol | Sections 6-8 present (~150 lines) | M |
| E6.S1e | Author SKILL.md Part E: policy + reference | Python Version Policy + Recipe Format Quick Ref + Core Tools Reference + Complementary Skills + CI Infrastructure Reference | Sections 9-13 present (~200 lines) | M |
| E6.S1f | Author SKILL.md Part F: gotchas + ecosystem | Recipe Authoring Gotchas G1-G6 (note: G6 promotion is Q-PRD-03 dependent) + Ecosystem Updates + Skill Automation + Manual CLI Commands + Version History pointer | Sections 14-16 present (~140 lines); SKILL.md total ~910 lines | M |
| E6.S2 | Author `INDEX.md` task→tool navigator | Maps "I want to do X" → "use tool Y, see reference Z" for ~50 common tasks | INDEX.md ~180 lines; all tools indexed | M |
| E6.S3 | Initialize `CHANGELOG.md` with TL;DR section | TL;DR section at top with v7.7.2 entry; chronological older entries (synthetic for v7.0.0 baseline + v7.7.0-7.7.2 detail) | CHANGELOG present; TL;DR matches current state | M |
| E6.S4 | Author `MANIFEST.yaml` + `install.py` | MANIFEST declares portability metadata; install.py bootstraps wrappers + MCP + pixi tasks into new repo | `python install.py` runs on a fresh repo and bootstraps correctly | L |
| E6.S5 | Author `reference/recipe-yaml-reference.md` | v1 schema deep-reference; field-by-field with examples | Reference complete; cross-checked vs. prefix-dev/recipe-format | L |
| E6.S6 | Author `reference/meta-yaml-reference.md` | v0 schema (legacy); migration source material | Reference present | M |
| E6.S7 | Author `reference/mcp-tools.md` | All 35 MCP tools enumerated with signature + use case + script counterpart | All 35 covered | M |
| E6.S8 | Author `reference/python-min-policy.md` | CFEP-25 + python_min triad + current floor + lint codes | Reference complete | S |
| E6.S9 | Author `reference/conda-forge-yml-reference.md` | Practical subset of conda-forge.yml keys | Reference complete | M |
| E6.S10 | Author `reference/pinning-reference.md` | Global pin rules + override patterns | Reference complete | S |
| E6.S11 | Author `reference/selectors-reference.md` | rattler-build selector syntax + common patterns | Reference complete | S |
| E6.S12 | Author `reference/jinja-functions.md` | `${{ compiler() / stdlib() / pin_subpackage() / cdt() }}` etc. | Reference complete | S |
| E6.S13 | Author `reference/dependency-input-formats.md` | scan_project's ~28 input formats matrix | Reference complete | M |
| E6.S14 | Author `reference/actionable-intelligence-catalog.md` | Persona-mapped atlas signal index | Reference complete | M |
| E6.S15 | Author `reference/conda-forge-ecosystem.md` | Ecosystem overview (bot, smithy, repodata-patches) | Reference complete | M |
| E6.S16 | Author all 8 `guides/*.md` | getting-started, migration, ci-troubleshooting, cross-compilation, feedstock-maintenance, testing-recipes, sdist-missing-license, atlas-operations | Each guide ~100-300 lines; complete | L |
| E6.S17 | Author `quickref/commands-cheatsheet.md` | All pixi tasks + raw CLIs + arg conventions | Cheatsheet complete | M |
| E6.S18 | Author `quickref/bot-commands.md` | `@conda-forge-admin` slash commands | Cheatsheet complete | S |
| E6.S19 | Author 41 recipe templates (13 ecosystems) | **12 language ecosystems**: python (noarch + compiled + maturin), rust (library + cli), go (pure + cgo), c-cpp (header-only + autotools + cmake + meson), r (cran + bioconductor), java (maven + gradle + cli), ruby (gem), dotnet (nuget), fortran (f90), **multi-output** (multi-output recipe patterns), **nodejs** (npm-ecosystem templates), **perl** (CPAN recipes); plus **1 config-template ecosystem**: conda-forge-yml (staged-recipes + feedstock `.yml` starters). Both v0 + v1 where applicable. | All 41 templates present across 13 ecosystem subdirs: 39 `.yaml` files (verified: `find templates -maxdepth 2 -name "*.yaml" \| wc -l`) + 2 `.yml` files in `conda-forge-yml/{staged-recipes,feedstock}/` | L |
| E6.S20 | Author 5 example recipes | c-library, multi-output, python-compiled, python-simple, rust-cli | Examples build green | M |
| E6.S21 | Author `config/skill-config.yaml` + `enterprise-config.yaml.template` | Skill internal config + enterprise template | Both present | S |
| E6.S22 | Author `automation/` quarterly-audit | quarterly-audit.prompt.md + run-audit-local.sh + README.md | Audit workflow runnable | M |
| E6.S23 | Set up `tests/{unit,integration,meta}/` + fixtures | Directory structure; `conftest.py`; pytest markers (network, slow); fixtures dir | Test infrastructure ready | M |
| E6.S24 | Author meta-test `test_recipe_yaml_schema_header.py` | Parametrize over `recipes/*/recipe.yaml`; assert line 1 is the schema-validation directive; skip if no `schema_version:` | Test passes (initially trivially since no recipes yet) | M |
| E6.S25a | Unit tests: recipe lifecycle modules | Test files for: recipe-generator, recipe_editor, recipe_optimizer, recipe_updater, validate_recipe, local_builder, failure_analyzer, submit_pr (~8-10 modules from Epic 4) | All recipe-lifecycle unit tests pass | L |
| E6.S25b | Unit tests: feedstock + GitHub modules | Test files for: github_updater, github_version_checker, feedstock-migrator, feedstock_context, feedstock_enrich, feedstock_lookup, license-checker, dependency-checker (~8 modules) | All feedstock + GitHub unit tests pass | M |
| E6.S25c | Unit tests: cf_atlas orchestration | Test files for: conda_forge_atlas (per-phase fixtures), _cf_graph_versions, _parquet_cache, atlas_phase, bootstrap_data, detail_cf_atlas, inventory_channel (~7 modules from Epic 7-9) | All atlas-orchestration unit tests pass | L |
| E6.S25d | Unit tests: atlas query CLIs | Test files for: staleness_report, feedstock_health, whodepends, behind_upstream, version_downloads, release_cadence, find_alternative, adoption_stage, cve_watcher, cve_manager, vulnerability_scanner (~11 modules from Epic 9) | All query-CLI unit tests pass | L |
| E6.S25e | Unit tests: scan + shared infrastructure | Test files for: scan_project (per format-family fixtures from Epic 9 split), _sbom, health_check, _http.py (E3.S3 already covers main paths), mapping_manager, name_resolver, npm_updater (~7 modules) | All scan + infrastructure unit tests pass | M |
| E6.S26 | Author integration tests | Cross-module flows: generate→validate→optimize; build→failure-analyze; submit dry-run | Integration tests pass with `@pytest.mark.network` where appropriate | L |

**Epic 6 total: 34 stories** (was 26; +5 from E6.S1 split into S1a-f, +4 from E6.S25 split into S25a-e), complexity ~M-L average; **no XL stories remaining**.

**Wave 2 totals: 3 epics, 54 stories.**

---

# Wave 3: Part 2 — cf_atlas Data Pipeline

Wave 3 builds the offline-tolerant package-intelligence layer. Atlas phases + schema + CLIs + air-gap backends.

---

## Epic 7: cf_atlas Schema + Phase B-E Pipeline

**Goal**: Implement the SQLite schema (v19) + the foundational phases (B, B.5, B.6, C, C.5, D, E, E.5).

**Owner part**: Part 2 (data pipeline foundation)

**Acceptance**: `atlas-phase B` populates `packages` table; `init_schema()` migrates additively; phases short-circuit cleanly on prerequisite-missing.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E7.S1 | Implement `conda_forge_atlas.py` skeleton | Module structure; `DB_PATH` constant; `SCHEMA_VERSION = 1` initially; `open_db()` with WAL mode; `init_schema()` placeholder | Module imports cleanly | M |
| E7.S2a | Schema baseline: 11 tables at v19 | Implement `init_schema()` that creates `packages` (60+ cols) + `maintainers` + `package_maintainers` + `meta` + `phase_state` + `dependencies` + `vuln_history` + `package_version_downloads` + `upstream_versions` + `upstream_versions_history` + `package_version_vulns` (all at v19 schema directly for greenfield rebuild) | All 11 tables created on fresh DB; row counts zero | M |
| E7.S2b | Schema indexes | Add all indexes from architecture-cf-atlas.md (relationship, match_source, pypi_name, conda_name, feedstock_name, license, dependencies source+target, pvd conda_name+upload, upstream name+source, uvh name+source+snap, pvv name+critical) | All indexes present; `PRAGMA index_list` returns expected set | S |
| E7.S2c | Schema migration idempotency | `init_schema()` on a v19 DB is no-op (safe to call on every connection open); meta table tracks current schema_version | Test: open + close 10 times in a row; no state change after first | S |
| E7.S2d | Schema migration test suite | Per-version migration tests (synthetic v17 → v18 → v19 path); confirms additive-only invariant; rerun-safety | Migration test passes; no data loss on simulated stale DBs | M |
| E7.S3 | Implement `phase_state` checkpoint table + helpers | `save_phase_checkpoint()`, `load_phase_checkpoint()`, status enum | Functions write/read correctly; status transitions valid | M |
| E7.S4 | Implement Phase B: conda enumeration | Fetch `current_repodata.json` for 5 subdirs via `_http.py`; parse + upsert into `packages` table; batched commit every 1k rows | `atlas-phase B` populates ~800k rows; checkpoint cursor advances; resume works | L |
| E7.S5 | Implement Phase B.5: feedstock outputs | Map conda-forge outputs to feedstocks via parselmouth CDN | `atlas-phase B.5` populates `feedstock_name` column on `packages` rows | M |
| E7.S6 | Implement Phase B.6: yanked detection | Detect packages removed from current_repodata since last run; update `latest_status` | `atlas-phase B.6` detects fixture yanked package | M |
| E7.S7 | Implement Phase C: parselmouth PyPI join | Join PyPI names via parselmouth CDN; update `pypi_name` + `relationship` + `match_source` | `atlas-phase C` joins fixture rows correctly | M |
| E7.S8 | Implement Phase C.5: source URL match | Fallback PyPI matching via recipe source URL parsing | `atlas-phase C.5` matches fixture rows where C missed | M |
| E7.S9 | Implement Phase D: PyPI enumeration | Fetch PyPI project index; upsert into `packages`; upgrade existing rows to coincidence relationship | `atlas-phase D` enumerates fixture PyPI projects | L |
| E7.S10 | Implement Phase E: cf-graph download + extract | Download `cf-graph-countyfair.tar.gz`; extract per-feedstock metadata | `atlas-phase E` populates `recipe_format` + ecosystem cross-refs | L |
| E7.S11 | Implement Phase E.5: archived feedstocks | Detect archived feedstocks from cf-graph metadata | `atlas-phase E.5` updates `feedstock_archived` + `archived_at` | S |
| E7.S12 | Implement `run_single_phase()` + `get_phase()` | Case-insensitive phase ID lookup; per-phase invocation | All Phase B-E.5 invocable via `run_single_phase` | S |
| E7.S13 | Author schema migration test | `test_schema_migration_v18_to_v19.py` (and intermediate) | Migration from v18 to v19 preserves all data | M |
| E7.S14 | Author checkpoint resume test | Kill Phase B mid-run; resume; verify only post-cursor rows processed | Test passes | M |

**Epic 7 total: 17 stories** (was 14; +3 from E7.S2 split into S2a/b/c/d), complexity ~M-L average; **no XL stories**.

---

## Epic 8: cf_atlas Phase F-N + Backends + TTL Gates

**Goal**: Implement the 9 remaining phases (F, G, G', H, J, K, L, M, N) with air-gap backends, TTL gates, and rate-limit awareness.

**Owner part**: Part 2 (data pipeline operational)

**Acceptance**: All 17 phases run; `PHASE_F_SOURCE` + `PHASE_H_SOURCE` backends work; TTL gates scope correctly; mid-run kill is cheap.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E8.S1 | Implement Phase F: downloads (api path) | api.anaconda.org/package/conda-forge/<name>/files; per-row fetch with TTL gate | `atlas-phase F` populates `total_downloads` + `latest_version_downloads` + `downloads_fetched_at` | L |
| E8.S2 | Implement Phase F: S3 parquet path | `_parquet_cache.py` for AWS S3 parquet download + cache; pyarrow read with pushdown filters | `PHASE_F_SOURCE=s3-parquet atlas-phase F` works; parquet cache populated | L |
| E8.S3 | Implement Phase F: auto dispatch | Probe api.anaconda.org once; fall through to S3 on failure; mid-run flip on >25% failure rate | `PHASE_F_SOURCE=auto atlas-phase F` selects right backend; `downloads_source` populated | M |
| E8.S4 | Implement TTL gate for Phase F | `downloads_fetched_at` scoped UPDATE with `conda_name IS NOT NULL` predicate | `atlas-phase F --reset-ttl` NULLs only eligible rows; meta-test verifies scope | M |
| E8.S5 | Implement Phase G: vdb summary | Read `.claude/data/conda-forge-expert/vdb/`; per-package CVE summary; requires `vuln-db` env | `atlas-phase G` populates `vuln_total` + `vuln_critical_affecting_current` + `vdb_scanned_at` | L |
| E8.S6 | Implement Phase G' (G-prime): per-version vulns | Per-version CVE scoring; writes `package_version_vulns` table | `atlas-phase G\'` populates per-version data | L |
| E8.S7 | Implement Phase H: pypi-json path | Per-row pypi.org JSON API; current version + yanked status | `PHASE_H_SOURCE=pypi-json atlas-phase H` works | L |
| E8.S8 | Implement Phase H: cf-graph offline path | `_cf_graph_versions.py`; bulk read from `cf-graph-countyfair.tar.gz`; project `new_version` onto pypi_name via feedstock_name | `PHASE_H_SOURCE=cf-graph atlas-phase H` works; 30 sec vs. pypi-json's 30 min | L |
| E8.S9 | Implement Phase H: auto dispatch (bootstrap-data) | `--phase-h-source auto`: cf-graph on `--fresh`, pypi-json otherwise | `bootstrap-data --fresh` selects cf-graph; `--resume` selects pypi-json | M |
| E8.S10 | Implement Phase J: dependency graph | Build `dependencies` table from cf-graph + Phase D PyPI deps | `atlas-phase J` populates `dependencies` table | L |
| E8.S11 | Implement Phase K: VCS version lookup | Per-feedstock GitHub/GitLab/Codeberg `releases/latest`; URL extraction regex (with v7.7.2 fix for multi-URL strings) | `atlas-phase K` populates `upstream_versions` rows; handles multi-URL `dev_url` correctly | L |
| E8.S12 | Implement Phase L: extra registries | CRAN, Maven, npm, RubyGems lookups; per-source row writes | `atlas-phase L` populates multi-source `upstream_versions` | L |
| E8.S13 | Implement Phase M: feedstock health | Compute health metrics from cf-graph + cached state | `atlas-phase M` populates `feedstock_bad` | M |
| E8.S14 | Implement Phase N: GitHub live | Batched GraphQL queries; default-branch CI status + open PRs/issues; cursor checkpointing | `atlas-phase N` populates `gh_*` columns; resume works | L |
| E8.S15 | Implement progress cadence + 60s heartbeat | `progress_every = min(max(N, len // 40), 2500)` + wall-clock heartbeat in all fan-out phases | No phase silences for >60 sec; progress visible | M |
| E8.S16 | Implement TTL gates for G, H, K (scoped UPDATE) | Per-phase predicate in `_TTL_GATED` dict; `--reset-ttl` scopes correctly | All TTL gates tested by `test_atlas_phase_reset_ttl.py` (4 cases) | M |
| E8.S17 | Phase K secondary-rate-limit backoff (per Q-PRD-04) | Detect HTTP 403 with `secondary rate limit` body in `_phase_k_fetch_one`; sleep 60s; retry once; if still 403, mark `github_version_last_error` and skip the row. Full exponential backoff deferred to v2 | Synthetic-fixture test passes both 403-then-success and 403-then-403 paths; phase doesn't stall on burst rate-limit | S |

**Epic 8 total: 17 stories, complexity ~M-L average.**

---

## Epic 9: cf_atlas Public CLIs + bootstrap-data + Performance

**Goal**: Implement the orchestrator + 15 query CLIs + performance tuning.

**Owner part**: Part 2 (CLI surface)

**Acceptance**: All 17 atlas CLIs work; `bootstrap-data --fresh` runs end-to-end in ≤90 min; `--status` and `--resume` operational.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E9.S1 | Implement `atlas_phase.py` Tier 1 + Tier 2 wrapper | Single-phase invocation; `--reset-ttl` (uses `_TTL_GATED`); `--list` enumerates phases; case-insensitive ID | All 17 phases invocable; `--list` works | S |
| E9.S2 | Implement `bootstrap_data.py` orchestrator | `--fresh` (with 5-sec countdown + `--yes` skip + `--reset-cache`), `--resume`, `--status`; per-step timeouts via `BOOTSTRAP_<STEP>_TIMEOUT`; chain: mapping → CVE → vdb → cf_atlas (B-N) → optional Phase N | Full bootstrap runs; mid-run kill resumes cleanly; status command works | L |
| E9.S3 | Implement `detail_cf_atlas.py` | "Show me everything about package X"; multi-table join; pretty-print | `detail-cf-atlas numpy` returns comprehensive view | M |
| E9.S4 | Implement `staleness_report.py` | Behind-upstream + unmaintained feedstocks filter; JSON + table output | `staleness-report` returns list with filters | M |
| E9.S5 | Implement `feedstock_health.py` | Per-feedstock health summary | `feedstock-health numpy` returns metrics | M |
| E9.S6 | Implement `whodepends.py` | Reverse dep query via `dependencies` table | `whodepends numpy` returns packages depending on numpy | M |
| E9.S7 | Implement `behind_upstream.py` | Compare `latest_conda_version` to `upstream_versions` | `behind-upstream` returns list | M |
| E9.S8 | Implement `version_downloads.py` | Per-version download trend from `package_version_downloads` | `version-downloads numpy` returns time series | M |
| E9.S9 | Implement `release_cadence.py` | Compute release cadence from `upstream_versions_history` | `release-cadence numpy` returns histogram | M |
| E9.S10 | Implement `find_alternative.py` | Similar packages via name/keyword/dep overlap | `find-alternative requests` returns alternatives | M |
| E9.S11 | Implement `adoption_stage.py` | Popularity tier from `total_downloads` + age | `adoption-stage requests` returns tier | S |
| E9.S12 | Implement `cve_watcher.py` | New CVEs for maintainer's feedstocks; reads `package_version_vulns` | `cve-watcher --maintainer rxm7706` returns recent CVEs | M |
| E9.S13 | Implement `inventory_channel.py` | Refresh channel inventory cache; consumed by scan_project | `inventory-channel` populates `inventory_cache/` | M |
| E9.S14a | scan_project: manifest formats | requirements.txt, environment.yaml/.yml, pyproject.toml (PEP 621 + Poetry + Hatch + PDM), Pipfile, setup.cfg, setup.py egg-info, package.json (npm), Cargo.toml + Cargo.lock, go.mod, conda meta.yaml + recipe.yaml | Each manifest format parsed correctly; 10-12 formats covered | L |
| E9.S14b | scan_project: lock file formats | requirements.txt with hashes, pip-tools .txt, poetry.lock, pipenv Pipfile.lock, uv.lock, conda-lock.yml/.toml, pixi.lock, npm package-lock.json, pnpm-lock.yaml | Each lock format parsed; ~9 formats covered | M |
| E9.S14c | scan_project: SBOM formats | `_sbom.py` helpers for CycloneDX (json + xml), SPDX (json + tag-value), Syft JSON | Each SBOM format parsed; 5 formats covered | L |
| E9.S14d | scan_project: container + OCI formats | Docker image inspect + OCI archive (tar) + OCI registry probe (read manifest without pull) | 3 container formats covered; auth via _http.py | M |
| E9.S14e | scan_project: GitOps + K8s | GitOps CR (Argo/Flux) with auto git-clone fallback, K8s manifest (Deployment/StatefulSet/CronJob image refs) | 2 GitOps formats + K8s manifest covered; ~28 total formats matches the spec | M |
| E9.S15 | Implement `health_check.py` | Validate pixi env, MCP server, atlas freshness, vuln-db env, JFrog config presence | `health-check` returns comprehensive status | M |
| E9.S16 | Implement `cve_manager.py` (`update_cve_database`) | Refresh CVE feed from configured source; integrate with vdb | `update-cve-db` works; async MCP tool wraps it | M |
| E9.S17 | Implement `query_atlas` generic interface | Generic SQL-ish query interface; or structured filter syntax | `query-atlas` returns parameterized results | M |
| E9.S18 | Implement `package_health` composite | Combines feedstock_health + atlas state + CVE surface into a single score | `package-health numpy` returns composite | M |
| E9.S19 | Implement `my_feedstocks` | Filter by GitHub maintainer login | `my-feedstocks rxm7706` returns list | S |
| E9.S20 | Author atlas operations guide (`guides/atlas-operations.md`) | Cron schedules + hard reset + air-gap operations | Guide complete | M |

**Epic 9 total: 24 stories** (was 20; +4 from E9.S14 split into S14a-e), complexity ~M-L average; **no XL stories remaining**.

**Wave 3 totals: 3 epics, 50 stories.**

---

# Wave 4: Part 3+4 Surfaces

Wave 4 brings the MCP wire format online and finalizes BMAD integration.

---

## Epic 10: Part 3 MCP Server + 35 Tools

**Goal**: Author the FastMCP server with all 35 tool registrations; auxiliary servers; auto-discovery.

**Owner part**: Part 3 (FastMCP server)

**Acceptance**: All 35 MCP tools callable via `mcp_call.py`; Claude Code auto-discovers the server; integration tests pass.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E10.S1 | Implement `conda_forge_server.py` skeleton | Module structure; `mcp = FastMCP("conda-forge-expert")`; SCRIPT_DIR constants; `_PYTHON = sys.executable`; `_run_script` helper | Server starts; tools/list returns 0 tools initially | M |
| E10.S2 | Implement `_run_script` helper with 3-tier error handling | FileNotFoundError, JSONDecodeError, TimeoutExpired, generic Exception → structured error dict | All error paths return JSON; tests pass | M |
| E10.S3 | Register recipe-authoring tools (17 tools) | `@mcp.tool()` decorators for: validate_recipe, check_dependencies, generate_recipe_from_pypi, scan_for_vulnerabilities, trigger_build (async), get_build_summary, lookup_feedstock, enrich_from_feedstock, get_feedstock_context, edit_recipe, analyze_build_failure, optimize_recipe, update_recipe, prepare_submission_branch, submit_pr, update_recipe_from_github, check_github_version, migrate_to_v1 | All 17 tools registered; each callable | L |
| E10.S4 | Register atlas-intelligence tools (16 tools) | staleness_report, feedstock_health, whodepends, behind_upstream, version_downloads, release_cadence, find_alternative, adoption_stage, cve_watcher, package_health, query_atlas, my_feedstocks, scan_project, update_cve_database (async), update_mapping_cache, get_conda_name | All 16 tools registered; each callable | L |
| E10.S5 | Register infrastructure tools (2 tools) | run_system_health_check, get_build_summary | Both registered; each callable | S |
| E10.S6 | Implement out-of-band state handlers | `build_summary.json` + `build.pid` at repo root; trigger_build writes them; get_build_summary reads them | Async build flow tested end-to-end | M |
| E10.S7 | Implement `mcp_call.py` JSON-RPC client | Initialize + tools/call messages; parse stdout response; 300-sec timeout | `mcp_call.py validate_recipe '{"recipe_path": "..."}'` works | M |
| E10.S8 | Implement `gemini_server.py` (optional aux) | FastMCP("gemini"); gemini_chat + gemini_list_models tools; uses GEMINI_API_KEY | Server starts if GEMINI_API_KEY set; tools functional | M |
| E10.S9 | Author `.mcp.json` registration (per Q-PRD-01 = include in v1) | Repo-root `.mcp.json` registering conda_forge_server and gemini_server | Claude Code discovers servers via `.mcp.json`; survives fresh installs | S |
| E10.S10 | Author `tests/integration/test_mcp_call.py` | Integration tests exercising MCP via mcp_call.py for ~5 representative tools | Tests pass; document false-negative gotchas | M |
| E10.S11 | Author `tests/meta/test_mcp_tool_coverage.py` | Meta-test: every Tier 1 script with a `main()` AND a public CLI must have an MCP tool wrapper OR be in `mcp_no_wrap_allowlist` | Test passes; catches drift if a script lacks a wrapper | M |

**Epic 10 total: 11 stories, complexity ~M-L average.**

---

## Epic 11: BMAD↔CFE Integration + project-context + auto-memory

**Goal**: Codify BMAD-CFE integration rules; author CLAUDE.md; author project-context.md with drift contract; seed auto-memory.

**Owner part**: Part 4 + cross-cutting

**Acceptance**: CLAUDE.md + project-context.md drive consistent agent behavior; auto-memory reinforces; first BMAD-driven recipe-authoring effort proceeds without violations.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E11.S1 | Author `CLAUDE.md` (repo-wide) | Behavioral guidelines + project overview + BMAD multi-project pattern + skill reference + BMAD↔CFE integration rules (Rule 1 + Rule 2) + project documentation reference | CLAUDE.md ~400 lines; all sections present | L |
| E11.S2 | Author `project-context.md` (foundational rules) | 14+ sections per `bmad-generate-project-context` template; `last_synced_skill_version` MINOR pin; per-section `(Sync: ...)` tags; rule_count metadata | project-context.md complete; sync tags point at correct upstream files | L |
| E11.S3 | Seed auto-memory: BMAD-uses-CFE rule | `~/.claude/projects/<repo-slug>/memory/feedback_bmad_uses_cfe_skill.md` | Entry written; MEMORY.md indexes it | S |
| E11.S4 | Seed auto-memory: CFE retro contract | `feedback_bmad_runs_cfe_retro.md` | Entry written; MEMORY.md indexes it | S |
| E11.S5 | Seed auto-memory: three-place rule | `feedback_cfe_new_script_three_places.md` | Entry written | S |
| E11.S6 | Seed auto-memory: BMAD multi-project pattern | `feedback_bmad_multi_project.md` | Entry written | S |
| E11.S7 | Seed auto-memory: skill disambiguation defaults | `feedback_skill_disambiguation.md` | Entry written | S |
| E11.S8 | Seed auto-memory: JFROG cross-host leak | `project_http_jfrog_unconditional_injection.md` | Entry written; reinforces 3-doc constraint | S |
| E11.S9 | Implement BMAD↔CFE retro template | New `bmad-retrospective` skill customization that auto-prompts for SKILL.md / reference/ / guides / CHANGELOG updates after conda-forge efforts | Retro template ready; tested on a sample effort | M |
| E11.S10 | E11 acceptance: end-to-end BMAD recipe authoring | Run a sample task: "package <pkg>" via `bmad-quick-dev`; verify Rule 1 (skill invoked) + Rule 2 (retro runs) | Both rules observed; CHANGELOG entry written by retro | M |

**Epic 11 total: 10 stories, complexity ~S-M average.**

**Wave 4 totals: 2 epics, 21 stories.**

---

# Wave 5: Hardening + Validation

Wave 5 brings tests + docs + deployment validation. After Wave 5, the rebuild is ready for production use.

---

## Epic 12: Test Suite Completeness + Meta-Tests

**Goal**: Achieve full test coverage; ensure all meta-tests pass; document test conventions.

**Owner part**: cross-cutting (`tests/`)

**Acceptance**: `pixi run test` (offline subset) passes 100%; `pixi run test-all` (full suite incl. network/slow) passes ≥98%; meta-tests enforce structural invariants.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E12.S1 | Complete unit test coverage to ≥80% | Author missing unit tests for any Tier 1 module < 80% | Coverage report shows ≥80% per module | L |
| E12.S2 | Author integration tests for atlas pipeline | Per-phase fixtures; multi-phase chained tests; resume tests | All integration tests pass | L |
| E12.S3 | Author meta-test: schema migration roundtrip | Migrate v1 → v2 → ... → v19; verify each intermediate is queryable | Test passes | M |
| E12.S4 | Author meta-test: drift-contract enforcement | Compare `project-context.md:last_synced_skill_version` to skill CHANGELOG MINOR; alert if drift > 0 MINOR | Test passes (initially); alerts trigger correctly | M |
| E12.S5 | Author meta-test: TTL-gate scoping | Per-phase `_TTL_GATED` scope predicate correctness | Test passes; matches Phase F/G/H/K eligibility SQL | M |
| E12.S6 | Author meta-test: MCP-tool coverage | Already in Epic 10 (`test_mcp_tool_coverage.py`) — verify it catches gaps | Test catches deliberate omission | S |
| E12.S7 | Author meta-test: bootstrap timeout sizing | `test_bootstrap_timeouts.py` (per BOOTSTRAP_<STEP>_TIMEOUT defaults + env-var overrides) | Test passes; documents the timeout-sizing rationale | S |
| E12.S8 | Set up pytest markers + CI integration | `network`, `slow` markers; `pixi run test` excludes both; `test-all` includes; CI runs `test-all` | Markers work; CI runs both flavors | S |
| E12.S9 | Author CI pipeline templates | `.azure-pipelines/recipe.yml.template`, `.github/workflows/*.template.yml`; operator customizes | Templates present; documented in `deployment-guide.md` | M |
| E12.S10 | Implement + test `test-skill.py` smoke test runner | Skill-internal smoke test harness (`.claude/skills/conda-forge-expert/scripts/test-skill.py`) that exercises the 10-step autonomous loop end-to-end on a fixture package; intended for post-install verification | `python .claude/skills/conda-forge-expert/scripts/test-skill.py` runs to completion on a clean DB + sample recipe; reports per-step outcome | M |

**Epic 12 total: 10 stories** (was 9; +1 E12.S10 covering `test-skill.py` per MF5), complexity ~M-L average.

---

## Epic 13: Documentation + Deployment Validation

**Goal**: Author `docs/*` operational references; validate air-gap deployment; sign-off.

**Owner part**: cross-cutting (docs + deployment)

**Acceptance**: All `docs/*.md` files complete; air-gap deployment validated against the deployment checklist; rebuild PRD signed off.

### Stories

| ID | Title | Scope | AC | Complexity |
|---|---|---|---|---|
| E13.S1 | Author `docs/mcp-server-architecture.md` | FastMCP server design; tool surface; auto-discovery; deferred `.mcp.json` if not chosen for v1 | Doc complete | M |
| E13.S2 | Author `docs/enterprise-deployment.md` | Air-gap + JFrog + CVE mirror + JFROG_API_KEY mitigation with subshell patterns | Doc complete (~400 lines) | L |
| E13.S3 | Author `docs/developer-guide.md` | Local testing + recipe development + debugging | Doc complete | M |
| E13.S4 | Author `docs/copilot-to-api.md` | 5 ways to drive Copilot subscription as local model backend | Doc complete | M |
| E13.S5 | Author `docs/bmad-setup-plan.md` | BMAD installation rationale + multi-project pattern | Doc complete | S |
| E13.S6 | Author `docs/pixi-config-jfrog.example.toml` | Drop-in `.pixi/config.toml` for JFrog | Template valid | S |
| E13.S7 | Author `docs/specs/*` (5 existing specs preserved as inputs) | Preserve the BMAD-consumable specs: atlas-phase-f-s3-backend, conda-forge-tracker, copilot-bridge, db-gpt-conda-forge, claude-team-memory | Specs preserved (no rebuild required; they're inputs) | S |
| E13.S8a | Air-gap dry-run setup | Configure `.pixi/config.toml` from `docs/pixi-config-jfrog.example.toml` template; export `*_BASE_URL` env vars to JFrog endpoints; verify corporate CA trust; `pixi install -e local-recipes` + `pixi install -e vuln-db` succeed | All pixi envs install via JFrog mirrors only; `pixi info` shows correct channels | M |
| E13.S8b | Air-gap atlas bootstrap | With `JFROG_API_KEY` set, run `pixi run -e local-recipes bootstrap-data --fresh`; verify Phase F uses S3 parquet backend + Phase H uses cf-graph backend (both reachable via JFrog or github.com mirror) | Full atlas built; `cf_atlas.db` populated; no public-host failures | L |
| E13.S8c | Air-gap recipe authoring + submission | With `JFROG_API_KEY` UNSET in subshell scope, run `pixi run generate-recipe -- <pkg>` → `validate` → `optimize` → `build-locally-docker` → `prepare-pr` → `submit-pr --dry-run`; verify recipe build green in Docker | Recipe authored end-to-end; build green; PR dry-run validates | M |
| E13.S8d | Air-gap audit + sign-off | Pull JFrog access logs + non-JFrog access logs (github.com, pypi.org, anaconda.org, AWS S3 via operator audit); verify zero `X-JFrog-Art-Api` headers in non-JFrog logs; document mitigation pattern adherence | Audit passes; PRD G4 success metric met; sign-off recorded | M |
| E13.S9 | Operator handoff documentation | Quick-start + first-recipe walkthrough + common errors + escalation paths | Documentation reviewed by operator | M |
| E13.S10 | Performance benchmark vs. PRD targets | Measure: bootstrap cold/warm times; MCP tool call overhead; build times; compare to PRD § 6 metrics | Benchmark report; gaps identified for follow-up | M |
| E13.S11 | Final retro: rebuild completion | Run `bmad-retrospective` on the entire rebuild effort; update skill files (if any drift found); CHANGELOG entry for v8.0.0 release if breaking, else v7.8.0 | Retro complete; CHANGELOG entry written | M |
| E13.S12 | PRD sign-off | Resolve Q-PRD-01 through Q-PRD-07; mark PRD as "approved" status; promote architecture + epics to "approved" | All PRD open questions resolved; status fields updated | M |
| E13.S13 | Rebuild release candidate | Tag a release; document version (v1.0.0 of rebuild = v7.8.0 / v8.0.0 of skill); produce release notes | Tag exists; release notes published | S |

**Epic 13 total: 16 stories** (was 13; +3 from E13.S8 split into S8a/b/c/d), complexity ~M-L average; **no XL stories remaining**.

**Wave 5 totals: 2 epics, 22 stories.**

---

# Total Effort Summary

| Wave | Epics | Stories | Complexity skew |
|---|---|---|---|
| Wave 1 (Foundation) | 3 | 29 | Mostly S-M; some L (resolvers, _http.py) |
| Wave 2 (Part 1 skill) | 3 | 65 | Mostly M-L (was 2 XL: SKILL.md split into 6, unit tests split into 5) |
| Wave 3 (cf_atlas) | 3 | 58 | Mostly M-L (was 1 XL: scan_project split into 5; +1 from Q-PRD-04 Phase K backoff) |
| Wave 4 (Parts 3+4) | 2 | 21 | Mostly S-M; some L (MCP tool registrations, CLAUDE.md) |
| Wave 5 (Hardening) | 2 | 26 | Mostly M-L (was 1 XL: air-gap deployment validation split into 4) |
| **Total** | **13** | **193** | **Mixed; weighted toward M-L; zero XL stories remaining** |

*(Story count expanded from 176 → 192 (XL splits + test-skill.py) → 193 (Q-PRD-04 Phase K backoff). Original 142 estimate → 193 post-validation + tentative-decisions revision.)*

---

## Implementation Strategy

### Phase 1: Wave 1 (Foundation) → ~2 sprint-weeks

Goal: every other Wave can start. End state: `pixi run health-check` works; BMAD-switch can switch projects; `_http.py` is the only HTTP path.

### Phase 2: Wave 2 (Part 1 skill) → ~6-8 sprint-weeks

Largest wave. Recipe authoring works end-to-end (minus atlas-dependent features). Critical milestone: first generated recipe.yaml passes `validate_recipe` + `optimize_recipe`.

### Phase 3: Wave 3 (cf_atlas) → ~4-6 sprint-weeks

Atlas pipeline. Most complex single component. Critical milestone: `bootstrap-data --fresh` runs end-to-end on a clean DB.

### Phase 4: Wave 4 (Parts 3+4 surfaces) → ~2 sprint-weeks

MCP server + BMAD integration. End state: BMAD agent can author a recipe via MCP.

### Phase 5: Wave 5 (Hardening) → ~2 sprint-weeks

Tests + docs + deployment validation + sign-off. End state: PRD approved; release candidate tagged.

**Total estimated calendar time: 16-20 sprint-weeks** (4-5 months at 1 sprint = 1 week).

(Calendar estimates assume one operator + Claude Code; AI-assisted development changes the math significantly.)

---

## Risk Concentration

Stories with the highest risk-to-effort ratio:

1. **E4.S7** (recipe_optimizer.py — 17 lint codes) — bug here means every PR fails review
2. **E7.S2** (schema v1-v19 migrations) — bug here corrupts the atlas
3. **E8.S2** (Phase F S3 parquet path) — bug here breaks air-gap operation
4. **E8.S8** (Phase H cf-graph offline path) — bug here means `--fresh` hangs again
5. **E10.S3+S4** (35 MCP tool registrations) — partial coverage breaks specific workflows silently
6. **E11.S1+S2** (CLAUDE.md + project-context.md) — wrong rules here cascade across every BMAD effort
7. **E13.S8** (air-gap deployment validation) — failure here means rebuild ships with broken enterprise support

These should get extra review (`bmad-code-review`, `bmad-review-adversarial-general`) before close.

---

## Acceptance Criteria for "Rebuild Complete"

All of:

- [ ] All 13 epics' acceptance criteria met
- [ ] PRD § 6 success metrics measured and within target
- [ ] PRD § 8 open questions resolved (or explicitly deferred to v2)
- [ ] All meta-tests passing
- [ ] Air-gap deployment validated (E13.S8)
- [ ] First sample BMAD-driven recipe authored end-to-end with retro closeout (E11.S10)
- [ ] Performance benchmark within PRD targets (E13.S10)
- [ ] Final retro completed (E13.S11)
- [ ] Release candidate tagged (E13.S13)

Until each box is checked, the rebuild is in-progress, not complete.

---

## References

- [PRD.md](./PRD.md) — product requirements (drives epic priorities)
- [architecture.md](./architecture.md) — unified architecture (drives build order)
- [index.md](./index.md) — navigator (orientation for new contributors)
- [project-context.md](../project-context.md) — foundational rules (must be re-authored by E11.S2)
