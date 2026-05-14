---
doc_type: architecture
part_id: conda-forge-expert
display_name: conda-forge-expert skill
project_type_id: library
date: 2026-05-12
source_pin: 'conda-forge-expert v8.0.0'
---

# Architecture: conda-forge-expert (Part 1)

The `conda-forge-expert` skill is **the heart of the system** — a Claude Code skill that encodes every conda-forge packaging decision so an AI agent can author, validate, build, and submit recipes that pass conda-forge review on first land. Parts 2 (`cf_atlas`) and 3 (`mcp-server`) are extensions of this part: Part 2 is the data pipeline encoded in this skill's `scripts/`, and Part 3 is the MCP wire format over this skill's `scripts/`. Part 4 (BMAD) is independent infrastructure that invokes this skill per the integration rules in `CLAUDE.md`.

---

## Mission

> **Autonomously manage the entire lifecycle of a conda-forge recipe — from creation to PR submission — with maximum correctness, security, and quality.** (SKILL.md, line 16)

Operationalized: when Claude Code receives a conda-forge task, it activates this skill, which then drives a 10-step autonomous loop (`generate → validate → edit → scan → optimize → trigger_build → get_build_summary → analyze_build_failure → prepare_submission_branch → submit_pr`) with one human-gated checkpoint at step 8b.

---

## Operating Principles (SKILL.md § Operating Principles)

These six principles govern all skill behavior. They override the BMAD agent persona when conflicts arise.

| # | Principle | Mechanism |
|---|---|---|
| 1 | **Think Before Generating** | Surface assumptions; if ambiguous, present interpretations; for vague requests use `idea-refine`; emit a brief PLAN before executing |
| 2 | **Simplicity First** | Minimum recipe that solves the problem; no speculative extras; ask "would a senior reviewer call this overcomplicated?" |
| 3 | **Surgical Changes** | Touch only what the task requires; match existing format; mention but don't fix unrelated issues |
| 4 | **Goal-Driven Execution** | Transform every task into a verifiable goal with explicit success criteria; loop until verified |
| 5 | **Stop-the-Line Rule** (`debugging-and-error-recovery`) | On unexpected behavior: stop, preserve logs, diagnose, fix root cause — never apply workarounds |
| 6 | **Verify, Don't Assume** (`source-driven-development`) | Check current docs before implementing; cite sources for non-obvious decisions |

---

## Critical Constraints (SKILL.md § Critical Constraints)

Non-negotiable rules that override all other guidance. These exist because each maps to an automatic rejection or a longstanding-painful incident.

1. **Never mix formats in a build run** — `meta.yaml` and `recipe.yaml` cannot coexist; remove `meta.yaml` after a successful v1 build, not before.
2. **`stdlib` is required for all compiled recipes** — any `compiler("c"/"cxx"/"rust"/"fortran"/"cuda"/"go-cgo")` requires `stdlib("c")` in `requirements.build`. Exception: `go-nocgo` (pure Go) is exempt. Auto-rejection trigger if missing (lint code **STD-001**).
3. **Python version floor: `3.10`** — tracks `conda-forge-pinning-feedstock`; never downgrade in a new submission.
4. **PyPI `source.url` must use the `pypi.org/packages/...` pattern** — not `files.pythonhosted.org/...` (which bypasses standard JFrog PyPI Remote Repository proxies, per `docs/enterprise-deployment.md` § 3).
5. **`build.bat` must `call` every `.cmd` shim** — bare `pnpm --version` / `npm --version` / `yarn --version` silently terminates the parent script. Always prefix with `call`.

The `JFROG_API_KEY` cross-host leak (per `docs/enterprise-deployment.md` § 2 → "Cross-host credential leak") is technically a Critical Constraint at the integration layer (Part 1+2+3 share `_http.py`), but its mitigation lives in deployment-guide.md.

---

## Three-Tier Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Tier 1: CANONICAL IMPLEMENTATION  (.claude/skills/conda-forge-expert/scripts/)
│  → Single source of truth for behavior. 42 Python modules.
│  → Tested by 41-file pytest suite. Imported by Tier 2 wrappers + Tier 3 MCP server.
│
├────────────────────────────────────────────────────────────────────────────┤
│  Tier 2: CLI WRAPPER LAYER  (.claude/scripts/conda-forge-expert/)
│  → 34 thin (~10-30 line) subprocess wrappers.
│  → Pixi tasks (~30 in pixi.toml) invoke these, NOT the Tier 1 modules directly.
│  → Some Tier 1 modules are internal-only and have no wrapper (`_http.py`,
│    `_cf_graph_versions.py`, `_parquet_cache.py`, `_sbom.py`, `mapping_manager.py`).
│
├────────────────────────────────────────────────────────────────────────────┤
│  Tier 3: DATA STATE  (.claude/data/conda-forge-expert/)
│  → Mutable runtime artifacts (gitignored).
│  → cf_atlas.db (Part 2 primary), vdb/ (vuln-db env), cve/, mapping caches.
│  → Created/refreshed by Tier 1 scripts; consumed by Tier 1 + Tier 2 + Part 3 MCP tools.
└────────────────────────────────────────────────────────────────────────────┘
```

**Why three tiers and not two:**
- Tier 1 scripts are imported by **multiple** entry points: Tier 2 CLI wrappers, Part 3 MCP server, pytest suite, and internally by other Tier 1 scripts. Inlining Tier 1 into Tier 2 would force every MCP tool to shell out — slow and error-prone.
- Tier 2 wrappers exist so pixi tasks can `cmd = "python .claude/scripts/conda-forge-expert/X.py"` without leaking the skill's internal layout. They're also the surface the meta-test enforces (`test_all_scripts_runnable.py` SCRIPTS list).

**Three-place rule for new scripts** (enforced by `tests/meta/test_all_scripts_runnable.py`):
1. Canonical impl: `.claude/skills/conda-forge-expert/scripts/<name>.py`
2. CLI wrapper: `.claude/scripts/conda-forge-expert/<name>.py` (delegates to #1 via subprocess) OR add to `no_task_allowlist` if internal-only
3. Pixi task: `[feature.local-recipes.tasks.<name>]` in `pixi.toml` + entry in meta-test `SCRIPTS` list

Missing any one breaks the meta-test.

---

## The 10-Step Autonomous Loop (SKILL.md § Primary Workflow)

```
┌────────────────────────────────────────────────────────────────────────┐
│  AUTONOMOUS LOOP  (driven by Claude Code when conda-forge-expert is active)
│                                                                          │
│  1.  generate_recipe_from_pypi  ──→  recipe.yaml drafted
│      │                                                                   │
│  2.  validate_recipe            ──→  rattler-build --render passes
│      │                                                                   │
│  3.  edit_recipe                ──→  structured-action fixes (version, sha, maintainer)
│      │                                                                   │
│  4.  scan_for_vulnerabilities   ──→  no Critical/High CVEs
│      │                                                                   │
│  5.  optimize_recipe            ──→  17 lint codes (STD/TEST/PIN/DEP/etc.) clean
│      │                                                                   │
│  6.  trigger_build              ──→  rattler-build linux-64 (Docker)
│      │                                                                   │
│  7.  get_build_summary          ──→  parse build_artifacts/ outcome
│      │                                                                   │
│  8.  analyze_build_failure      ──→  loop back to step 3 if failed
│      │  (no hard cap; 3 cycles without progress → escalate to user)     │
│  ──── (build green; ready to submit) ────────────────────────────────────│
│  8b. prepare_submission_branch  ──→  pushes to fork; returns fork_branch_url
│      │  ★ HUMAN CHECKPOINT — inspect branch in browser; submit_pr is ungated
│  9.  submit_pr(dry_run=True)    ──→  verify gh auth, fork, branch state
│      │                                                                   │
│  10. submit_pr()                ──→  PR opens on conda-forge/staged-recipes
└────────────────────────────────────────────────────────────────────────┘
```

**Step 8b is the only human-gated checkpoint.** It pushes the recipe to `<your-user>/staged-recipes` fork and returns `fork_branch_url` but does NOT open the PR. `submit_pr` is ungated and will proceed unprompted — the gate is the human inspecting the branch URL between 8b and 9. Inspection checklist: (a) `recipe.yaml` renders correctly post-jinja, (b) branch name matches `<recipe-name>-<version>`, (c) no `.claude/data/` leaked into the diff, (d) commit message matches `Add recipe for <name>`.

**Force pushes default to `--force-with-lease`** (errors on divergent remote instead of overwriting). Pass `force=False` for plain push.

**Build-failure loop has no hard cap.** Three cycles without progress should escalate to user — repeated identical failures indicate the diagnosis is wrong, not that another iteration will help.

---

## Tier 1: The 42 Canonical Scripts

Grouped by function (script names map 1:1 to `.claude/skills/conda-forge-expert/scripts/<name>.py`):

### Recipe lifecycle (18 modules — the core of Part 1)

| Module | Role | MCP tool counterpart |
|---|---|---|
| `recipe-generator.py` | Generate v1 `recipe.yaml` from PyPI / CRAN / npm / GitHub | `generate_recipe_from_pypi` |
| `recipe_editor.py` | Structured-action edit engine (version/sha/maintainer/dependency mutations) | `edit_recipe` |
| `recipe_optimizer.py` | 17 lint codes spanning DEP/PIN/ABT/SCRIPT/SEL/STD/TEST/MAINT/SEC/OPT families | `optimize_recipe` |
| `recipe_updater.py` | Version + SHA bump for existing recipes | `update_recipe` |
| `validate_recipe.py` | rattler-build --render dry-run + schema validation | `validate_recipe` |
| `local_builder.py` | rattler-build + Docker wrapper (build-locally.py bridge) | `trigger_build` |
| `failure_analyzer.py` | Parse build_artifacts/.../conda_build.log; pattern-match common failure modes | `analyze_build_failure` |
| `submit_pr.py` | **Split flow**: `prepare_submission_branch` (step 8b) + `submit_pr` (steps 9-10) | `prepare_submission_branch`, `submit_pr` |
| `github_updater.py` | Autotick for GitHub-only sources (no PyPI) | `update_recipe_from_github` |
| `github_version_checker.py` | Check upstream GitHub for newer tag | `check_github_version` |
| `npm_updater.py` | npm-ecosystem recipe handling (`npm pack` + `pnpm-licenses`) | (internal) |
| `feedstock-migrator.py` | v0→v1 migration via feedrattler | `migrate_to_v1` |
| `feedstock_context.py` | Get-context-for-feedstock helper | `get_feedstock_context` |
| `feedstock_enrich.py` | Enrich recipe fields from feedstock | `enrich_from_feedstock` |
| `feedstock_lookup.py` | Lookup feedstock by package name | `lookup_feedstock` |
| `license-checker.py` | Validate `license_file` + SPDX identifier | (internal validation step) |
| `dependency-checker.py` | PyPI→conda dep resolution + availability check | `check_dependencies` |
| `name_resolver.py` | PyPI→conda name resolution engine (backs `get_conda_name` MCP tool) | `get_conda_name` |

### cf_atlas pipeline orchestration (7 modules — Part 2 core, hosted in Part 1)

| Module | Role |
|---|---|
| `conda_forge_atlas.py` | **Orchestrator**: 17-phase pipeline B→N, PHASES registry, `run_single_phase()` |
| `_cf_graph_versions.py` | Phase H cf-graph offline backend (v7.7.0) |
| `_parquet_cache.py` | Phase F S3 parquet cache layer (v7.6.0) |
| `atlas_phase.py` | Single-phase CLI entrypoint (`pixi run atlas-phase <ID>`) |
| `bootstrap_data.py` | Full-pipeline orchestrator (mapping + CVE + vdb + cf_atlas + Phase N) |
| `detail_cf_atlas.py` | Query helpers (`detail-cf-atlas` CLI) |
| `inventory_channel.py` | Channel inventory cache for `scan_project` |

### Atlas-intelligence query CLIs (11 modules — Part 2 read side)

| Module | CLI command | Reads from |
|---|---|---|
| `staleness_report.py` | `staleness-report` | cf_atlas.db |
| `feedstock_health.py` | `feedstock-health` | cf_atlas.db + GitHub |
| `whodepends.py` | `whodepends` | cf_atlas.db (Phase D dep graph) |
| `behind_upstream.py` | `behind-upstream` | cf_atlas.db (Phase H upstream skew) |
| `version_downloads.py` | `version-downloads` | cf_atlas.db (Phase F downloads + parquet cache) |
| `release_cadence.py` | `release-cadence` | cf_atlas.db (Phase L cadence) |
| `find_alternative.py` | `find-alternative` | cf_atlas.db (similar packages) |
| `adoption_stage.py` | `adoption-stage` | cf_atlas.db (popularity tiers) |
| `pypi_only_candidates.py` | `pypi-only-candidates` | cf_atlas.db `pypi_universe` LEFT JOIN `packages` (Phase D, v7.9.0+) — admin candidate-list of unmatched PyPI projects ordered by `last_serial DESC` |
| `cve_watcher.py` | `cve-watcher` | vdb/ + cf_atlas.db (Phase G/G' CVE surface) |
| `cve_manager.py` | (no public CLI; backs `update_cve_database`) | cve/ feed cache |
| `vulnerability_scanner.py` | (no public CLI; backs `scan_for_vulnerabilities` MCP tool) | vdb/ + recipe |

### Project-scanning + health (3 modules)

| Module | Role | MCP tool counterpart |
|---|---|---|
| `scan_project.py` | Scan project for conda-forge intel (~28 input formats: manifests, lock files, SBOMs, container images, GitOps CRs, K8s manifests, OCI archives, OCI registry probes) | `scan_project` |
| `health_check.py` | System health check | `run_system_health_check` |
| `_sbom.py` | SBOM parsing helpers (CycloneDX / SPDX / Syft) — internal helper for scan_project | (internal) |

### Shared infrastructure (3 modules — used by all 4 parts)

| Module | Role |
|---|---|
| `_http.py` | ★ The canonical shared-utility module. Surfaces (v7.8.1): (1) truststore + JFrog/GitHub/.netrc auth chain — `auth_headers_for(url)` extracted in v7.8.0 so `requests`-based callers share the same auth resolution as urllib callers; (2) 14 `resolve_<host>_urls` resolvers — every external host the atlas + skill talks to is redirectable via a `<HOST>_BASE_URL` env var; (3) `atomic_writer` / `atomic_write_bytes` / `atomic_write_text` — `.tmp` + fsync + `os.replace` pattern; (4) `fetch_to_file_resumable(target, urls, ...)` — streaming Range/resume download with atomic finalize. **Contains the JFROG_API_KEY cross-host leak** (mitigated via env-var hygiene; see `deployment-guide.md`). Every outbound HTTP request from Parts 1+2+3 routes through here. |
| `mapping_manager.py` | PyPI→conda mapping refresh (`update_mapping_cache` MCP tool) |
| `test-skill.py` | Skill-internal smoke test runner |

---

## Tier 2: The 34 CLI Wrappers

`.claude/scripts/conda-forge-expert/*.py` — each is a ~10-30 line subprocess wrapper. Most names mirror Tier 1 scripts. One additional wrapper:

- **`prepare_pr.py`** — wraps `submit_pr.py --prepare-only` to expose the step-8b checkpoint as a separate pixi task (`pixi run -e local-recipes prepare-pr <recipe>`).

**Why this split exists** (per v7.2.0 retro): the original `submit_pr.py` was a monolithic fork→clone→sync→branch→copy→commit→push→`gh pr create` end-to-end run. The split lets the human inspect the branch on GitHub before reviewers pull it.

**Tier 1 modules WITHOUT a Tier 2 wrapper** (internal-only, in meta-test `no_task_allowlist`):
- `_http.py`, `_cf_graph_versions.py`, `_parquet_cache.py`, `_sbom.py`, `mapping_manager.py`, `recipe_editor.py`, `npm_updater.py`, `feedstock_context.py`, `feedstock_enrich.py`, `feedstock_lookup.py`, `name_resolver.py`, `test-skill.py`

---

## Templates Layer (41 templates / 13 ecosystems incl. conda-forge.yml starters)

`.claude/skills/conda-forge-expert/templates/`:

```
python/    noarch-recipe.yaml, noarch-meta.yaml, compiled-recipe.yaml, maturin-recipe.yaml, maturin-meta.yaml
rust/      library-recipe.yaml, cli-recipe.yaml, cli-meta.yaml
go/        pure-recipe.yaml, pure-meta.yaml, cgo-recipe.yaml, cgo-meta.yaml
c-cpp/     header-only-recipe.yaml, autotools-recipe.yaml, cmake-recipe.yaml, cmake-meta.yaml, meson-recipe.yaml
r/         cran-recipe.yaml, cran-meta.yaml, bioconductor-recipe.yaml
java/      maven-recipe.yaml, maven-meta.yaml, gradle-recipe.yaml
ruby/      gem-recipe.yaml, gem-meta.yaml
dotnet/    nuget-recipe.yaml, nuget-meta.yaml
fortran/   f90-recipe.yaml, f90-meta.yaml
conda-forge-yml/  staged-recipes/conda-forge.yml, feedstock/conda-forge.yml  (v7.3.0)
```

Templates ship **both v0 (meta.yaml) and v1 (recipe.yaml)** variants for most ecosystems — v1 is canonical for new recipes, v0 stays only for migration source material.

`recipe-generator.py` reads from these when a `--template <ecosystem>` flag is passed; otherwise grayskull auto-generates from PyPI metadata.

---

## Testing Layer (41 test files)

```
tests/
├── unit/         function-level tests (no network, no fixtures larger than necessary)
├── integration/  cross-module tests; some marked @pytest.mark.network or @slow
├── meta/         ★ enforces invariants ABOUT the codebase, not just behavior
│   ├── test_recipe_yaml_schema_header.py   (every recipes/*/recipe.yaml has the schema-validation header)
│   └── test_all_scripts_runnable.py        (Tier 1 + Tier 2 + pixi task three-place discipline)
└── fixtures/
    ├── recipes/          real recipe.yaml snippets for unit/integration
    ├── manifest_samples/ inputs for scan_project (~28 formats)
    ├── error_logs/       build-failure samples for failure_analyzer
    └── mocked_responses/ rare; suite uses real fixtures by default
```

**No network mocking by default.** The suite uses real fixtures + `@pytest.mark.network` / `@pytest.mark.slow` markers. Offline subset: `pixi run -e local-recipes test`. Full suite: same, with markers enabled.

This is the project-context's "Mocking the network in `.claude/skills/conda-forge-expert/tests/`" anti-pattern in negative form — mocking is what NOT to do.

---

## Documentation Layer

Three doc layers, each loaded by the agent under different conditions:

### `SKILL.md` (always loaded on activation)

914-line primary spine. Sections (in source order):
- Operating Principles (6)
- Critical Constraints (5 + cross-cutting JFROG note)
- Primary Workflow: The Autonomous Loop (10 steps + step 8b detail)
- Atlas Intelligence Layer (v8.0.0)
- Recipe Security Boundaries (Always Do / Ask First / Never Do)
- Build Failure Protocol
- Pre-PR Quality Gate Checklist
- Migration Protocol (meta.yaml → recipe.yaml)
- Python Version Policy
- Recipe Formats Quick Reference (v1 + v0)
- Core Tools Reference (categorized by function)
- Complementary Skills (which BMAD/practice skills compose with this one)
- CI Infrastructure Reference (platform assignments, OS versions, compiler pins, bot commands)
- Ecosystem Updates (May 2026)
- Recipe Authoring Gotchas (G1-G5 in SKILL.md; G6 still in CHANGELOG v7.7.1, not yet promoted to SKILL.md "Gotchas" section)

### `INDEX.md` (task→tool navigator)

178 lines mapping common tasks to the right canonical script + MCP tool + reference file. Read by the agent when "where do I find X?" arises.

### `CHANGELOG.md` (drift-detection source)

Release history with a TL;DR section at the top. Every MINOR-version bump triggers a project-context.md re-sync (per the drift contract in `_bmad-output/projects/local-recipes/project-context.md` frontmatter `last_synced_skill_version`).

### `reference/` (12 deep-reference files — loaded on demand)

| File | When loaded |
|---|---|
| `recipe-yaml-reference.md` | v1 recipe authoring questions |
| `meta-yaml-reference.md` | v0 migration source |
| `mcp-tools.md` | Tool signature questions |
| `python-min-policy.md` | CFEP-25 + python_min triad |
| `conda-forge-yml-reference.md` | Per-recipe or feedstock-root `conda-forge.yml` overrides (v7.3.0) |
| `pinning-reference.md` | Global pin rules from `conda-forge-pinning-feedstock` |
| `selectors-reference.md` | rattler-build selector syntax |
| `jinja-functions.md` | `${{ compiler() / stdlib() / pin_subpackage() / cdt() }}` |
| `dependency-input-formats.md` | scan_project input matrix (~28 formats) |
| `atlas-actionable-intelligence.md` | Persona-mapped atlas signal index (renamed from `actionable-intelligence-catalog.md`) |
| `atlas-phases-overview.md` | Phase-indexed companion to the persona catalog: per pipeline stage (B → N), data source, purpose, what gets written, and the actionable intelligence (CLIs / MCP tools / SQL) it unlocks. |
| `conda-forge-ecosystem.md` | Ecosystem overview (bot, smithy, repodata-patches) |
| `atlas-phase-engineering.md` | **Added in v7.8.0.** Rule book for authoring or refactoring `conda_forge_atlas.py` pipeline phases. 9 patterns: per-host rate limits, GraphQL batching, Retry-After + jitter, per-registry concurrency, atomic writes, incremental commits + idempotent SQL, streaming tarfiles, page-level checkpoints, `<HOST>_BASE_URL` routing convention. |

### `guides/` (8 workflow guides — loaded on demand)

- `getting-started.md`, `migration.md`, `ci-troubleshooting.md`, `cross-compilation.md`, `feedstock-maintenance.md`, `testing-recipes.md`, `sdist-missing-license.md`, `atlas-operations.md`

### `quickref/` (2 quick-reference files — loaded on demand)

- `commands-cheatsheet.md` — pixi tasks + raw CLIs (canonical command reference)
- `bot-commands.md` — `@conda-forge-admin` slash commands

---

## Recipe Authoring Gotchas (SKILL.md § Recipe Authoring Gotchas)

Non-obvious failures that have bitten enough times to be enumerated:

| Code | Description | Lives where |
|---|---|---|
| **G1** | `script:` list entries run in separate shells — env vars do NOT carry across entries | SKILL.md |
| **G2** | v0/meta.yaml field names in v1 recipe.yaml are silently ignored | SKILL.md |
| **G3** | `py < N` skip selectors do nothing in v1 recipe.yaml | SKILL.md |
| **G4** | Sdist may omit LICENSE — `pip install` succeeds, build fails with "No license files were copied" | SKILL.md + `guides/sdist-missing-license.md` |
| **G5** | tree-sitter PyPI sdists inconsistently strip parser headers — default to GitHub source for `tree-sitter-<lang>` (narrowed from initial framing in v7.7.1 retro) | SKILL.md |
| **G6** | `get_build_summary` false negatives — read `conda_build.log` directly | CHANGELOG v7.7.1 (not yet promoted to SKILL.md "Gotchas" section — known doc drift) |

---

## Recipe Security Boundaries (SKILL.md § Recipe Security Boundaries)

Three-tier permission model:

- **Always Do** — verify SHA256 from PyPI JSON / sha256sum (never paste upstream's claimed hash); use `dry_run=True` for `submit_pr`; check for known CVEs with `scan_for_vulnerabilities`
- **Ask First** — adding new compiler-toolchain deps; loosening pins below `conda-forge-pinning-feedstock`; committing patches that touch security-sensitive code paths
- **Never Do** — paste upstream's claimed SHA256 without re-fetching; submit a recipe with unresolved Critical/High CVEs; force-push without `--force-with-lease`; mix v0 and v1 in a build run; commit secrets to any recipe; use the `JFROG_API_KEY` env var in a shell that touches external hosts (see `deployment-guide.md`)

---

## Build Failure Protocol (SKILL.md § Build Failure Protocol)

When `get_build_summary` reports failure (or false negative — see G6):

1. **STOP** the autonomous loop. Do not retry without diagnosis.
2. **Preserve the log**: `build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log` (resolve `<id>` with `ls -t build_artifacts/*/bld/rattler-build_<name>_*/work/conda_build.log | head -1`).
3. **Run `analyze_build_failure`** to pattern-match the failure mode against `tests/fixtures/error_logs/`.
4. **Root-cause** the fix (never workaround). Common root causes:
   - Missing `stdlib("c")` — see Critical Constraint #2
   - Missing license file — see G4
   - Cross-compile selector misuse — see `guides/cross-compilation.md`
   - Sdist missing parser headers — see G5
   - Environment-variable carry-over assumption — see G1
5. **Apply the fix via `edit_recipe`** (structured action) or hand-edit YAML if the action set doesn't cover.
6. **Re-trigger build**. If 3 cycles pass without progress, escalate to user — repeated identical failures mean the diagnosis is wrong.

---

## Migration Protocol (SKILL.md § Migration Protocol)

**Strangler pattern: migrate v0 in the same PR that touches the recipe.**

1. Existing recipe has `meta.yaml`. New work needs to touch it.
2. `migrate_to_v1` invokes feedrattler to produce `recipe.yaml`.
3. `validate_recipe` on the new file.
4. Build green on linux-64.
5. **Then** `git rm meta.yaml` and commit both in one PR.

The Critical Constraint ("never mix formats in a build run") means `meta.yaml` must be deleted before commit; the strangler pattern ensures the migration is atomic with the value-adding change so reviewers see one coherent diff.

---

## Atlas Intelligence Integration (SKILL.md § Atlas Intelligence Layer)

Part 2 (cf_atlas) is owned conceptually by Part 1 — its scripts live in `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` and its phase-CLI entrypoints share the wrapper layer. The skill exposes the atlas via:

- **Build**: `pixi run -e local-recipes bootstrap-data --fresh` (full) or `pixi run -e local-recipes atlas-phase <ID>` (single phase)
- **Daily-use CLIs**: `staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`, `cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`, `scan-project`, `detail-cf-atlas`, `pypi-only-candidates`
- **MCP exposure**: every CLI has an MCP-tool counterpart for in-session Claude Code use
- **When to invoke**: before any recipe-authoring decision that depends on package metadata (version skew, CVE surface, alternative packages, popularity tier) — see `reference/atlas-actionable-intelligence.md` for the persona-mapped catalog and `reference/atlas-phases-overview.md` for the phase-indexed companion

Full Part 2 detail: `architecture-cf-atlas.md`.

---

## Portability: MANIFEST.yaml + install.py

The skill is designed to be **standalone-portable**. `MANIFEST.yaml` (line 11: `type: standalone-portable`) declares:
- skill canonical paths (`skill_root: .claude/skills/conda-forge-expert`)
- required external tools (pixi, rattler-build, gh, etc.)
- pixi tasks to inject into the host repo
- MCP server placement
- runtime data directory location

`install.py` (~150 lines) bootstraps the skill into a new host repo:
1. Move `.claude/skills/conda-forge-expert/` into target's `.claude/skills/`
2. Run `python install.py` from inside the moved directory
3. The installer writes the wrapper layer (Tier 2), optionally copies the MCP server (Part 3) to `.claude/tools/`, and offers to inject pixi tasks into the host's `pixi.toml`

**Implication for rebuild:** the skill is **not coupled** to `local-recipes` specifically. A rebuild could start by installing the skill via `install.py` into an empty repo, then layering the BMAD installer + recipe corpus.

---

## Mapping Subsystem

PyPI ↔ conda name mapping is a longstanding pain point. The skill has two coexisting subsystems (legacy + current):

| Subsystem | Location | Content | Reader |
|---|---|---|---|
| Legacy (single YAML) | `mappings/pypi-conda.yaml` | curated one-to-one mappings | `name_resolver.py` fallback |
| Current (multi-file) | `pypi_conda_mappings/` — `custom.yaml`, `different_names.json`, `stats.json` | user overrides + auto-generated table + coverage stats | `name_resolver.py` primary |

Runtime cache: `.claude/data/conda-forge-expert/pypi_conda_map.json` — refreshed by `update_mapping_cache` (Tier 1: `mapping_manager.py`; no Tier 2 wrapper; MCP-only).

This subsystem feeds:
- `dependency-checker.py` / `check_dependencies` MCP tool
- `recipe-generator.py` (resolves PyPI deps in generated recipe.yaml)
- `scan_project.py` (resolves PyPI deps in scanned manifests)

---

## Activation Lifecycle (how Claude Code loads this skill)

1. **Session boot**: Claude Code starts the FastMCP server at `.claude/tools/conda_forge_server.py` (Part 3); the 35 MCP tools become available.
2. **Task entry**: when the user prompt or BMAD agent mentions "conda recipe / conda-forge / packaging / build failure," Claude Code activates this skill.
3. **Skill load order** (frontmatter says `allowed-tools: [conda_forge_server]`):
   - Load `SKILL.md` fully (always)
   - Load `INDEX.md` for navigation (always)
   - Load `reference/<topic>.md` on demand (when the task mentions the topic)
   - Load `guides/<workflow>.md` on demand (when the task matches the guide's scope)
   - Load `quickref/commands-cheatsheet.md` when generating shell-command suggestions
4. **Per-task autonomous loop**: 10 steps + step 8b human checkpoint (see above).
5. **Per-effort retro** (per `CLAUDE.md` § BMAD ↔ conda-forge-expert integration, Rule 2): on closeout of any BMAD effort that touched conda-forge work, `bmad-retrospective` updates SKILL.md / reference / guides / CHANGELOG.

---

## Drift Detection

The skill version is the **source of truth** for what rules apply. Two version surfaces:

- `MANIFEST.yaml: version: 7.0.0` — the "schema/portability version" (rarely changes; bumps only when the install protocol changes)
- `CHANGELOG.md` TL;DR — the **release version** (v8.0.0 as of 2026-05-13)

Project-context.md pins to MINOR (`last_synced_skill_version: 'conda-forge-expert v8.0.0'`). When CHANGELOG's MINOR exceeds the pin, re-verify volatile sections (Recipe Format, MCP Lifecycle, Anti-Patterns). PATCH bumps don't require re-sync.

The pin discipline is the rebuild target's drift-control mechanism. A rebuilt repo without this pin will silently diverge.

---

## Integration Points (recap)

See `integration-architecture.md` for the cross-part contracts. Summary:

- **→ Part 2 (cf_atlas)**: Part 2's pipeline lives in this skill's `scripts/`. Shared data dir: `.claude/data/conda-forge-expert/`.
- **→ Part 3 (MCP server)**: each MCP tool in `conda_forge_server.py` imports from this skill's `scripts/<module>.py`. Part 3 is the wire format; Part 1's scripts are the implementation.
- **→ Part 4 (BMAD)**: every BMAD agent doing conda-forge work invokes this skill (`Skill: conda-forge-expert`) per CLAUDE.md Rule 1. Every effort closeout runs a retro that updates this skill per CLAUDE.md Rule 2.
- **→ Enterprise layer**: every outbound HTTP request from any Part routes through `scripts/_http.py`. The JFROG_API_KEY cross-host leak is mitigated at the deployment layer, not within the skill.
- **→ vuln-db env**: Part 1's `scan_for_vulnerabilities` + Part 2's Phase G/G' require the `vuln-db` pixi env (AppThreat vdb importable).

---

## Rebuild checklist for Part 1

To rebuild this part faithfully on a clean repo:

1. **Bootstrap**: install pixi; create `pixi.toml` with `python`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db` features and envs.
2. **Skill scaffolding**: copy `.claude/skills/conda-forge-expert/` from this repo OR generate fresh from SKILL.md template.
3. **Tier 1 scripts** (42 modules): authored in dependency order — `_http.py` first (every other module imports it), then `name_resolver.py` + `mapping_manager.py` (foundational helpers), then recipe-lifecycle, then atlas-pipeline.
4. **Tier 2 wrappers** (34 modules): thin subprocess wrappers; auto-generatable from a manifest if all Tier 1 modules expose a `main()`.
5. **Pixi tasks**: ~30 entries under `[feature.local-recipes.tasks.*]` matching the Tier 2 wrapper names.
6. **Meta-test**: `tests/meta/test_all_scripts_runnable.py` with SCRIPTS list + no_task_allowlist enforcing the three-place rule.
7. **Templates**: 41 starter recipes across 13 ecosystems (12 language + 1 conda-forge.yml config-template subdir with 2 starter files).
8. **Documentation**: SKILL.md + INDEX.md + CHANGELOG.md + reference/* (12 files, incl. `atlas-phase-engineering.md` since v7.8.0) + guides/* (8 files) + quickref/* (2 files).
9. **MANIFEST.yaml + install.py** for portability (skill should be installable into other repos).
10. **Mapping subsystem**: seed `pypi_conda_mappings/different_names.json` from public data; `custom.yaml` starts empty.

Rebuild order matters: Part 1 must exist before Parts 2 and 3 (which extend it) and before Part 4's BMAD↔CFE integration rules become enforceable.
