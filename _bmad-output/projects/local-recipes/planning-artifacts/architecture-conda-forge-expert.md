---
doc_type: architecture
part_id: conda-forge-expert
display_name: conda-forge-expert skill
project_type_id: library
date: 2026-07-25
source_pin: 'conda-forge-expert v8.79.1'
---

# Architecture: conda-forge-expert (Part 1)

> **Re-verified 2026-07-25** (source_pin → **v8.79.1**; reconciler pass per SYNC-RUNBOOK). **The skill's behavioural contract barely moved** since the 2026-07-06 re-ground — this pass is mostly count correction, not rewriting.
>
> **Changed since the last pass:** one new governance binding — the skill's own files are now the declared `surface:` of the brownfield Spec `spec-packaging-factory`, policed by `scripts/spec_surface_check.py` with a **CHANGELOG sentinel** (v8.79.1, § *Spec-surface governance* below); one new meta-test (`tests/meta/test_spec_surface_check.py`, 9 meta tests now); `reference/atlas-phase-engineering.md` § 14 (v8.79.0); gotcha **G106** (v8.78.0) and **G100–G105** (v8.77.0), so the catalog is **G1–G106** contiguous.
>
> **Corrected in this pass** (numbers carried forward unchecked since 2026-07-06 or earlier, all re-counted live): scripts 54 → **66** (41,410 LOC); wrapper layer 46 → **60 entries** (57 `.py`); test suite 82 files → **100 `.py`** (98 `test_*.py`, 1,186 test functions); pixi tasks ~30 → **106**; lint codes 17 → **23**; `reference/` 17 → **15**; SKILL.md 2,569 → **3,887 lines**; INDEX.md 178 → **180**; install.py ~150 → **238**; Critical Constraints 5 → **10**; the loop's "10 steps" → **12 gated stages**; the `no_task_allowlist` roster; the `tests/fixtures/error_logs/` directory (**does not exist**); and the meta.yaml/recipe.yaml corpus split.
>
> **Re-verified unchanged:** three-tier architecture and the three-place rule; the 6 Operating Principles; the Build Failure / Migration / Security-boundary protocols; step 8b as the sole human gate; the 13-ecosystem template tree (41 templates); the mapping subsystem's two coexisting halves; the portability story (`MANIFEST.yaml` + `install.py`).
>
> **Live defect recorded, not propagated:** `SKILL.md` frontmatter and `MANIFEST.yaml` both still declare `version: 7.0.0` while `config/skill-config.yaml` + `CHANGELOG.md` say **8.79.1** — see § *Drift Detection*.


The `conda-forge-expert` skill is **the heart of the system** — a Claude Code skill that encodes every conda-forge packaging decision so an AI agent can author, validate, build, and submit recipes that pass conda-forge review on first land. Parts 2 (`cf_atlas`) and 3 (`mcp-server`) are extensions of this part: Part 2 is the data pipeline encoded in this skill's `scripts/`, and Part 3 is the MCP wire format over this skill's `scripts/`. Part 4 (BMAD) is independent infrastructure that invokes this skill per the integration rules in `CLAUDE.md`.

---

## Mission

> **Autonomously manage the entire lifecycle of a conda-forge recipe — from creation to PR submission — with maximum correctness, security, and quality.** (SKILL.md, line 16)

Operationalized: when Claude Code receives a conda-forge task, it activates this skill, which then drives the autonomous loop under `## Primary Workflow: The Autonomous Loop` — **12 gated stages** (`1 · 1b · 2 · 3 · 4 · 5 · 6 · 7a · 7b · 8 · 8b · 9`) with one human-gated checkpoint at step 8b.

> **Numbering discrepancy, unresolved (verified 2026-07-25).** `CLAUDE.md` calls this "the 10-step loop"; SKILL.md's own workflow enumerates **9 numbered steps plus 3 lettered sub-steps** (`1b` feedstock-aware enrichment, `7a` native build / `7b` Docker build, `8b` prepare submission branch) = 12 entries, plus a `### Sub-workflow: Updating an existing recipe (diff-before-apply)`. Both numbers are in live files; neither is authoritative over the other. **This doc uses 12 gated stages** and flags the discrepancy rather than asserting a single number — reconciling `CLAUDE.md`'s wording against SKILL.md is a genuine open item.

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

Non-negotiable rules that override all other guidance. These exist because each maps to an automatic rejection or a longstanding-painful incident. **`## Critical Constraints` carries 10 `###` subsections** (re-counted live 2026-07-25; the doc previously listed only the founding five):

1. **Never mix formats in a build run** — `meta.yaml` and `recipe.yaml` cannot coexist; remove `meta.yaml` after a successful v1 build, not before.
2. **`stdlib` is required for all compiled recipes** — any `compiler("c"/"cxx"/"rust"/"fortran"/"cuda"/"go-cgo")` requires `stdlib("c")` in `requirements.build`. Exception: `go-nocgo` (pure Go) is exempt. Auto-rejection trigger if missing (lint code **STD-001**).
3. **Python version floor: `3.10`** — tracks `conda-forge-pinning-feedstock`; never downgrade in a new submission.
4. **PyPI `source.url` must use the `pypi.org/packages/...` pattern** — not `files.pythonhosted.org/...` (which bypasses standard JFrog PyPI Remote Repository proxies, per `docs/enterprise-deployment.md` § 3).
5. **`build.bat` must `call` every `.cmd` shim** — bare `pnpm --version` / `npm --version` / `yarn --version` silently terminates the parent script. Always prefix with `call`.
6. **Every v1 recipe must declare the schema header** — the `# yaml-language-server: $schema=…` line. Enforced by `tests/meta/test_recipe_yaml_schema_header.py`. *(Scope note: this is a **local-recipes-only** house rule, not a conda-forge-wide requirement — reviewers upstream do not block on its absence.)*
7. **Never add AI comments inline — park them in the bottom `# CFE comments` block** — agent-authored rationale goes at the end of the file for human triage; existing human/upstream comments stay in the body. Carries a `#### CFE metadata AND comments` sub-subsection covering the `extra.cfe-*` internal-metadata schema.
8. **Canonical test block for `noarch: python` recipes** — `pip_check: true` + `python_version: [${{ python_min }}.*, "*"]`; `pip_check: false` only with a factual blocker + reason code.
9. **Canonical license-file placement.**
10. **Rust recipe standards** (CLI binaries — the conda-forge 2026 canonical pattern).

The `JFROG_API_KEY` cross-host leak (per `docs/enterprise-deployment.md` § 2 → "Cross-host credential leak") is technically a Critical Constraint at the integration layer (Part 1+2+3 share `_http.py`), but its mitigation lives in deployment-guide.md.

---

## Three-Tier Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Tier 1: CANONICAL IMPLEMENTATION  (.claude/skills/conda-forge-expert/scripts/)
│  → Single source of truth for behavior. 66 Python modules / 41,410 LOC.
│  → Tested by a 100-file pytest suite (98 test_*.py, 1,186 test functions,
│    22,318 LOC). Imported by Tier 2 wrappers + Part 3's MCP server.
│
├────────────────────────────────────────────────────────────────────────────┤
│  Tier 2: CLI WRAPPER LAYER  (.claude/scripts/conda-forge-expert/)
│  → 60 entries = 57 thin (~10-30 line) Python subprocess wrappers
│    + native-build.sh + cross-build.sh + README.md.
│  → Pixi tasks (106 under [feature.local-recipes.tasks.*]) invoke these,
│    NOT the Tier 1 modules directly.
│  → 10 Tier 1 modules are internal-only and have no wrapper (list below).
│
├────────────────────────────────────────────────────────────────────────────┤
│  Tier 3: DATA STATE  (.claude/data/conda-forge-expert/)
│  → Mutable runtime artifacts (gitignored).
│  → cf_atlas.db (Part 2 primary), vdb/ (vuln-db env), cve/, mapping caches.
│  → Created/refreshed by Tier 1 scripts; consumed by Tier 1 + Tier 2 + Part 3's
│    46 MCP tools.
│  → ⚠ ABSENT in this checkout (2026-07-25): `.claude/data/` does not exist —
│    the atlas has never been built here. Every Tier-3 runtime claim in Parts
│    1-2 is therefore source-derived, not observed.
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

## The Autonomous Loop — 12 Gated Stages (SKILL.md § Primary Workflow)

```
┌────────────────────────────────────────────────────────────────────────┐
│  AUTONOMOUS LOOP  (driven by Claude Code when conda-forge-expert is active)
│                                                                          │
│  1.  generate_recipe_from_pypi  ──→  recipe.yaml drafted
│      │                                                                   │
│  1b. get_feedstock_context      ──→  when an existing <name>-feedstock exists:
│      + enrich_from_feedstock         pull maintainers + curated about-fields
│      │                                                                   │
│  2.  validate_recipe            ──→  rattler-build --render passes
│      │                                                                   │
│  3.  edit_recipe                ──→  structured-action fixes (version, sha, maintainer)
│      │                                                                   │
│  4.  scan_for_vulnerabilities   ──→  no Critical/High CVEs
│      │                                                                   │
│  5.  optimize_recipe            ──→  23 lint codes (STD/TEST/PIN/DEP/etc.) clean
│      │                                                                   │
│  6.  check_dependencies         ──→  PyPI→conda dep resolution + availability
│      │                                                                   │
│  7a. trigger_build(mode=native) ──→  MANDATORY native build
│      │                               (or pixi run recipe-build)          │
│  7b. trigger_build(mode=docker) ──→  OPT-IN, user-authorized              │
│      │                               (or pixi run recipe-build-docker)   │
│  8.  get_build_summary          ──→  poll until success | failed;
│      │                               analyze_build_failure → back to 3    │
│      │  (no hard cap; 3 cycles without progress → escalate to user)     │
│  ──── (build green; ready to submit) ────────────────────────────────────│
│  8b. prepare_submission_branch  ──→  pushes to fork; returns fork_branch_url
│      │  ★ HUMAN CHECKPOINT — inspect branch in browser; submit_pr is ungated
│  9.  submit_pr(dry_run=True) → submit_pr()
│                                 ──→  PR opens on conda-forge/staged-recipes
└────────────────────────────────────────────────────────────────────────┘
```

Plus `### Sub-workflow: Updating an existing recipe (diff-before-apply)` — an
8-step stash → regenerate → enrich → diff → **3-bucket categorization** →
present-to-user → restore-base-and-apply → re-run-2-through-7 procedure. Its
categorization table is itself an inspection checkpoint.

**Step 8b is the only human-gated checkpoint.** It pushes the recipe to `<your-user>/staged-recipes` fork and returns `fork_branch_url` but does NOT open the PR. `submit_pr` is ungated and will proceed unprompted — the gate is the human inspecting the branch URL between 8b and 9. Inspection checklist: (a) `recipe.yaml` renders correctly post-jinja, (b) branch name matches `add-recipe-<name>` (CFE convention), (c) no `.claude/data/` leaked into the diff, (d) commit message matches `Add recipe for <name>`.

**Force pushes default to `--force-with-lease`** (errors on divergent remote instead of overwriting). Pass `force=False` for plain push.

**Build-failure loop has no hard cap.** Three cycles without progress should escalate to user — repeated identical failures indicate the diagnosis is wrong, not that another iteration will help.

---

## Tier 1: The 66 Canonical Scripts

**66 `.py` / 41,410 LOC** (re-counted 2026-07-25; was 54 at the last pass). Largest modules: `conda_forge_atlas.py` 8,902 · `scan_project.py` 3,703 · `recipe-generator.py` 2,653 · `inventory_match.py` 1,742 · `detail_cf_atlas.py` 1,210 · `recipe_optimizer.py` 1,115 · `bootstrap_data.py` 1,094 · `library_futures.py` 1,074 · `failure_analyzer.py` 1,026 · `_http.py` 1,024. Two modules (`conda_forge_atlas.py` + `scan_project.py`) are 30% of the tier by line count.

The 12 modules added since the 54-module tables below were written: `export_purls.py`, `mapping_gap.py`, `universe_sbom.py`, `inventory_match.py`, `add_handoff.py`, `library_futures.py`, `recommend_2027.py` (the cyclonedx-universe-inventory suite), `lts_registry_gap.py`, `cwe_seed_gap.py`, `spdx_schema_gap.py`, `license_map_gap.py` (the four read-only seed-gap suggesters), and `_cfy_template.py` (the universal `conda-forge.yml` pre-seed emitter, v8.61.0).

Grouped by function (script names map 1:1 to `.claude/skills/conda-forge-expert/scripts/<name>.py`):

### Recipe lifecycle (19 modules — the core of Part 1)

| Module | Role | MCP tool counterpart |
|---|---|---|
| `recipe-generator.py` | Generate v1 `recipe.yaml` from PyPI / CRAN / npm / GitHub | `generate_recipe_from_pypi` |
| `recipe_editor.py` | Structured-action edit engine (version/sha/maintainer/dependency mutations) | `edit_recipe` |
| `recipe_optimizer.py` | **23** lint codes (re-counted live 2026-07-25; was 17): ABT-001/2/3 · DEP-001/2 · FMT-001 · LIC-001 · MAINT-001 · OPT-000 · PIN-001 · SCHEMA-001 · SCRIPT-001/2 · SEC-001 · SEL-001/2/3/4 · STD-001/2 · TEST-001/2/3 | `optimize_recipe` |
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
| `pr_artifacts.py` | Download a staged-recipes / feedstock PR's build artifacts into a local channel (v8.14.0) | `download_pr_artifacts` |

### cf_atlas pipeline orchestration (7 modules — Part 2 core, hosted in Part 1)

| Module | Role |
|---|---|
| `conda_forge_atlas.py` | **Orchestrator**, **8,902 LOC** (the single largest module in the skill): **22 executable phases** — B/B.5/B.6/C/C.5/D/O/P/Q/R/S/E/E.5/F/G/G'/H/J/K/L/M/N (v8.1.0 added O/P/Q/R/S) — via the `PHASES` registry (`:8679`), plus `get_phase()` / `run_single_phase()`. Sole declaration of `SCHEMA_VERSION = 29` (`:139`). *A 23rd phase (I) is cataloged but has no runner; a drift-detector regex separately over-counts to 23 — see Part 2.* |
| `_cf_graph_versions.py` | Phase H cf-graph offline backend (v7.7.0) |
| `_parquet_cache.py` | Phase F S3 parquet cache layer (v7.6.0) |
| `atlas_phase.py` | Single-phase CLI entrypoint (`pixi run atlas-phase <ID>`) |
| `bootstrap_data.py` | Full-pipeline orchestrator (mapping + CVE + vdb + cf_atlas + Phase N) |
| `detail_cf_atlas.py` | Query helpers (`detail-cf-atlas` CLI) |
| `inventory_channel.py` | Channel inventory cache for `scan_project` |

### Atlas-intelligence query CLIs (31 modules — Part 2 read side)

*(The table below enumerates the founding 20. The 11 added since — `export_purls`, `mapping_gap`, `universe_sbom`, `inventory_match`, `add_handoff`, `library_futures`, `recommend_2027`, `lts_registry_gap`, `cwe_seed_gap`, `spdx_schema_gap`, `license_map_gap` — all read `cf_atlas.db` + the vendored `data/` maps and are covered in Part 2's CLI roster. Six of them are **CLI/pixi-only with no MCP tool**: `library_futures`, `add_handoff`, and the four seed-gap suggesters; `mapping_gap` likewise has none.)*

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
| `pypi_intelligence.py` | `pypi-intelligence` | cf_atlas.db `pypi_intelligence` side table (v8.1.0; activity_band / download counts / cross-channel BOOLs / packaging shape / conda-forge readiness score) |
| `my_feedstocks.py` | `my-feedstocks` (default = portfolio; `--triage` = ranked punch list) | cf_atlas.db `package_maintainers` JOIN + composite urgency score across Phase G/H/M/N (v8.5.0) |
| `platform_breakdown.py` | `platform-breakdown` | cf_atlas.db `package_platform_downloads` (Phase F+, v8.19.0; ARM/win/EOL share) |
| `pyver_breakdown.py` | `pyver-breakdown` | cf_atlas.db `package_python_downloads` (Phase F+, v8.19.0; `--policy-check` python_min bump-safe flags) |
| `channel_split.py` | `channel-split` | cf_atlas.db `package_channel_downloads` (Phase F+, v8.19.0; defaults-channel migration opportunities) |
| `cve_watcher.py` | `cve-watcher` | vdb/ + cf_atlas.db (Phase G/G' CVE surface) |
| `cve_manager.py` | (no public CLI; backs `update_cve_database`) | cve/ feed cache |
| `vulnerability_scanner.py` | (no public CLI; backs `scan_for_vulnerabilities` MCP tool) | vdb/ + recipe |
| `cisa_kev_fetcher.py` | (no public CLI; CVE-scoring feed) | CISA KEV → `cisa_kev` table |
| `cwe_catalog_fetcher.py` | (no public CLI; CVE-scoring feed) | MITRE CWE → `cwe_categories` table |
| `epss_fetcher.py` | (no public CLI; CVE-scoring feed) | FIRST EPSS → `epss_scores` table |

### Project-scanning + env-inspection + health (4 modules)

| Module | Role | MCP tool counterpart |
|---|---|---|
| `scan_project.py` | **3,703 LOC** — scan project for conda-forge intel across manifests, lock files, SBOMs, container images, GitOps CRs, K8s manifests, OCI archives, OCI registry probes. *(The long-carried "~28 input formats" figure is **not independently verifiable**: `reference/dependency-input-formats.md` is the canonical support matrix but states no total, and the fixture corpus has 29 `manifest_samples/` files, which is a sample count, not a format count. Treat "~28" as indicative.)* | `scan_project` |
| `env_inspect.py` | Inspect a pixi/conda env from 8 angles via flag dispatcher: default (graph roots) / `--audit` (manifest hygiene) / `--freshness` (env vs cf vs PyPI lag) / `--security` (CVE rollup) / `--bus-factor` (SPoF list) / `--licenses` (SPDX rollup + non-permissive flag) / `--sbom {cyclonedx,spdx}` / `--diff OTHER_ENV`. All modes share `--scope {roots,explicits,all}`. Atlas-join helper layer with stale-warning + live PyPI fetch (default-on, 6h disk cache). Renamed v8.5.1 (was `env_roots.py` v8.3.1) | `env_inspect` |
| `health_check.py` | System health check | `run_system_health_check` |
| `_sbom.py` | SBOM parsing helpers (CycloneDX / SPDX / Syft) — internal helper for scan_project + env_inspect SBOM mode | (internal) |

### Shared infrastructure (5 modules — used by all 4 parts)

| Module | Role |
|---|---|
| `_http.py` | ★ The canonical shared-utility module, **1,024 LOC**. Surfaces: (1) truststore + JFrog/GitHub/.netrc auth chain — `auth_headers_for(url)` extracted in v7.8.0 so `requests`-based callers share the same auth resolution as urllib callers; (2) **19** `resolve_<host>_urls` resolvers (re-counted 2026-07-25; was 14) backed by **21 `<HOST>_BASE_URL` env vars** — every external host the atlas + skill talks to is redirectable; (3) `atomic_writer` / `atomic_write_bytes` / `atomic_write_text` — `.tmp` + fsync + `os.replace` pattern; (4) `fetch_to_file_resumable(target, urls, ...)` — streaming Range/resume download with atomic finalize. **Contains the JFROG_API_KEY cross-host leak — still UNRESOLVED as of 2026-07-25** (mitigated only via env-var hygiene; see `deployment-guide.md`). Every outbound HTTP request from Parts 1+2+3 routes through here. |
| `mapping_manager.py` | PyPI→conda mapping refresh (`update_mapping_cache` MCP tool) |
| `_cfy_template.py` | Universal `conda-forge.yml` pre-seed emitter (v8.61.0) — every generator path emits a pre-seeded `conda-forge.yml` by default (G83) |
| `gen_yml_reference.py` | Generates the `conda-forge.yml` reference docs from the live schema |
| `test-skill.py` | Skill-internal smoke test runner |

---

## Tier 2: The Wrapper Layer (60 entries / 57 Python wrappers)

`.claude/scripts/conda-forge-expert/` holds **60 entries**: 57 `.py` subprocess wrappers (~10-30 lines each), plus `native-build.sh`, `cross-build.sh`, and `README.md`. Most `.py` names mirror Tier 1 scripts. One wrapper has no same-named Tier 1 counterpart:

- **`prepare_pr.py`** — wraps `submit_pr.py --prepare-only` to expose the step-8b checkpoint as a separate pixi task (`pixi run -e local-recipes prepare-pr <recipe>`).

**Why this split exists** (per v7.2.0 retro): the original `submit_pr.py` was a monolithic fork→clone→sync→branch→copy→commit→push→`gh pr create` end-to-end run. The split lets the human inspect the branch on GitHub before reviewers pull it.

**Tier 1 modules WITHOUT a Tier 2 wrapper — 10, re-derived by set-difference 2026-07-25** (internal-only; meta-test `no_task_allowlist`):
`_cf_graph_versions.py` · `_cfy_template.py` · `_http.py` · `_parquet_cache.py` · `_sbom.py` · `feedstock_context.py` · `feedstock_enrich.py` · `feedstock_lookup.py` · `recipe_editor.py` · `test-skill.py`

> **Corrected:** the prior roster was wrong in both directions. `mapping_manager.py`, `npm_updater.py`, and `name_resolver.py` were listed as wrapper-less but **all three now have Tier 2 wrappers**; `_cfy_template.py` was missing from the list entirely.

---

## Templates Layer (41 templates / 13 ecosystem dirs incl. conda-forge.yml starters)

`.claude/skills/conda-forge-expert/templates/` — **42 files = 41 templates + `README.md`**, across **13** subdirectories (verified 2026-07-25; the "41 / 13" headline was right, but the listing below was missing three whole ecosystems — `multi-output/`, `nodejs/`, `perl/` — and 10 files):

```
python/           noarch-recipe.yaml, noarch-meta.yaml, compiled-recipe.yaml, maturin-recipe.yaml, maturin-meta.yaml
rust/             library-recipe.yaml, cli-recipe.yaml, cli-meta.yaml
go/               pure-recipe.yaml, pure-meta.yaml, cgo-recipe.yaml, cgo-meta.yaml
c-cpp/            header-only-recipe.yaml, autotools-recipe.yaml, cmake-recipe.yaml, cmake-meta.yaml, meson-recipe.yaml
multi-output/     lib-python-recipe.yaml, lib-python-meta.yaml, lib-cli-recipe.yaml, cuda-variant-recipe.yaml, cuda-variant-meta.yaml
nodejs/           npm-recipe.yaml, npm-meta.yaml, native-recipe.yaml
r/                cran-recipe.yaml, cran-meta.yaml, bioconductor-recipe.yaml
java/             maven-recipe.yaml, maven-meta.yaml, gradle-recipe.yaml
perl/             cpan-recipe.yaml, cpan-meta.yaml
ruby/             gem-recipe.yaml, gem-meta.yaml
dotnet/           nuget-recipe.yaml, nuget-meta.yaml
fortran/          f90-recipe.yaml, f90-meta.yaml
conda-forge-yml/  staged-recipes/conda-forge.yml, feedstock/conda-forge.yml  (v7.3.0)
```

Templates ship **both v0 (meta.yaml) and v1 (recipe.yaml)** variants for most ecosystems — v1 is canonical for new recipes, v0 stays only for migration source material. Note: **Feature G45 Local-Only SPA packaging** is supported as a local-only workflow (`noarch:generic` + `nodejs` + python `http.server`), which is explicitly not submittable to upstream conda-forge.

`recipe-generator.py` reads from these when a `--template <ecosystem>` flag is passed; otherwise grayskull auto-generates from PyPI metadata.

---

## Testing Layer (100 `.py` — 98 test files, 1,186 test functions, 22,318 LOC)

```
tests/
├── conftest.py · pytest.ini · run_skill_suite.py
├── unit/         85 test_*.py — function-level tests (no network)
├── integration/  4 files — test_mcp_atlas_tools, test_workflow_generate_validate_optimize,
│                 test_workflow_npm, test_workflow_v0_to_v1_migration
├── meta/         ★ 9 files — enforces invariants ABOUT the codebase, not just behavior
│   ├── test_recipe_yaml_schema_header.py   (every recipes/*/recipe.yaml has the schema-validation header)
│   ├── test_recipe_yaml_parse_audit.py     (whole-corpus YAML parse gate)
│   ├── test_all_scripts_runnable.py        (Tier 1 + Tier 2 + pixi task three-place discipline)
│   ├── test_actionable_scope.py            (v_actionable_packages persona-filter discipline, Part 2)
│   ├── test_pypi_intelligence_scope.py     (ORPHAN_RULE validity discipline, Part 2)
│   ├── test_no_redundant_python_min.py     (no python_min at the default conda-forge floor)
│   ├── test_skill_md_consistency.py        (SKILL.md internal consistency)
│   ├── test_bmad_artifacts_in_sync.py      (★ integrity gate over THESE architecture docs)
│   └── test_spec_surface_check.py          (NEW in v8.79.1 — wraps scripts/spec_surface_check.py)
├── data/         2 vendored JSON schemas — bom-1.6.schema.json (190 KB), jsf-0.82.schema.json
└── fixtures/     39 files
    ├── recipes/          6 dirs — v1-noarch, v1-broken, v1-compiled, v1-multi-output,
    │                     v1-pinned-vulnerable, v0-noarch
    ├── manifest_samples/ 29 files — inputs for scan_project
    └── mocked_responses/ 4 JSON — github_release, pypi_release, osv_clean, osv_with_vuln
```

> **Corrected (wrong, not merely stale):** the prior tree listed a `fixtures/error_logs/` directory holding "build-failure samples for `failure_analyzer`". **No such directory exists** (verified 2026-07-25) — and the Build Failure Protocol below still pointed `analyze_build_failure` at it. `failure_analyzer.py`'s pattern catalog is in-module; its tests live under `tests/unit/`.

**No network mocking by default.** The suite uses real fixtures + `@pytest.mark.network` / `@pytest.mark.slow` markers. Offline subset: `pixi run -e local-recipes test`. Full suite: same, with markers enabled.

This is the project-context's "Mocking the network in `.claude/skills/conda-forge-expert/tests/`" anti-pattern in negative form — mocking is what NOT to do.

---

## Documentation Layer

Three doc layers, each loaded by the agent under different conditions:

### `SKILL.md` (always loaded on activation)

**3,887-line** primary spine (re-counted 2026-07-25; was 2,569). **18 `##` sections**, in source order:
1. Operating Principles (6 `###` subsections)
2. Critical Constraints (10 `###` subsections + cross-cutting JFROG note)
3. Primary Workflow: The Autonomous Loop (12 gated stages + the diff-before-apply sub-workflow)
4. Atlas Intelligence Layer (v8.1.0) — incl. § *Daily-use CLIs* (25) and § *MCP exposure*
5. Recipe Security Boundaries (Always Do / Ask First / Never Do)
6. Build Failure Protocol
7. Pre-PR Quality Gate Checklist
8. Migration Protocol (meta.yaml → recipe.yaml)
9. Python Version Policy
10. Recipe Formats Quick Reference (v1 + v0)
11. Core Tools Reference (categorized by function)
12. Complementary Skills (which BMAD/practice skills compose with this one)
13. CI Infrastructure Reference (platform assignments, OS versions, compiler pins, bot commands)
14. Ecosystem Updates (May 2026)
15. Recipe Authoring Gotchas — **G1–G106**, all inline in SKILL.md; latest **G106** (`hatch-build-scripts` `clean_artifacts` defaults `True` and deletes prebuilt artifacts *before* honoring a SKIP env var), added v8.78.0
16. Skill Automation
17. Manual CLI Commands
18. Version History

The universal `conda-forge.yml` pre-seed (v8.61.0, via `scripts/_cfy_template.py`; pre-seeds the feedstock per G83) is emitted by default on every generator path — a generator behavior, not a SKILL.md section.

### `INDEX.md` (task→tool navigator)

180 lines mapping common tasks to the right canonical script + MCP tool + reference file. Read by the agent when "where do I find X?" arises.

### `CHANGELOG.md` (drift-detection source)

Release history with a TL;DR section at the top. Every MINOR-version bump triggers a project-context.md re-sync (per the drift contract in `_bmad-output/projects/local-recipes/project-context.md` frontmatter `last_synced_skill_version`).

### `reference/` (15 deep-reference files — loaded on demand)

*(Re-counted 2026-07-25 — the header said 17; the table below has always listed exactly the 15 files that exist.)*

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
| `atlas-phases-overview.md` | Consolidated atlas intelligence reference (2026-07-02; absorbed `atlas-actionable-intelligence.md`): **Part A** persona-mapped signal catalog + **Part B** phase-indexed overview — per pipeline stage (B → S/N), data source, purpose, what gets written, and the actionable intelligence (CLIs / MCP tools / SQL) it unlocks. |
| `conda-forge-ecosystem.md` | Ecosystem overview (bot, smithy, repodata-patches) |
| `atlas-phase-engineering.md` | **Added in v7.8.0.** Rule book for authoring or refactoring `conda_forge_atlas.py` pipeline phases: per-host rate limits, GraphQL batching, Retry-After + jitter, per-registry concurrency, atomic writes, incremental commits + idempotent SQL, streaming tarfiles, page-level checkpoints, `<HOST>_BASE_URL` routing, volume-billed-API caps, per-day caches, dry-run preflight — plus **§ 13**, the Phase P cost model + operator playbook (absorbed `atlas-phase-p-cost-model.md`, 2026-07-02). |
| `recipe-yaml-reference-full.md` | Full v1 `recipe.yaml` schema reference (long-form companion to `recipe-yaml-reference.md`) |
| `conda-forge-yml-reference-full.md` | Full `conda-forge.yml` key reference (long-form companion) |
| `abi3-matrix-collapse.md` | abi3 / limited-API wheel build-matrix collapse pattern |

### `guides/` (9 workflow guides — loaded on demand)

- `getting-started.md`, `migration.md`, `ci-troubleshooting.md`, `cross-compilation.md`, `feedstock-maintenance.md`, `testing-recipes.md`, `sdist-missing-license.md`, `atlas-operations.md`, `feedstock-platform-expansion.md`

### `quickref/` (2 quick-reference files — loaded on demand)

- `commands-cheatsheet.md` — pixi tasks + raw CLIs (canonical command reference)
- `bot-commands.md` — `@conda-forge-admin` slash commands

---

## Recipe Authoring Gotchas (SKILL.md § Recipe Authoring Gotchas)

Non-obvious failures that have bitten enough times to be enumerated. The catalog spans **G1–G106**, **contiguous with no gaps** (verified 2026-07-25 against `^### G\d+` in SKILL.md — 106 headings, max 106). All are promoted into SKILL.md; the table below shows the founding six and a title-only roll-up of G7–G53 follows. Each carries a one-line symptom + fix in SKILL.md § Recipe Authoring Gotchas, which is authoritative.

Recent additions: **G100–G105** (v8.77.0 — npm CLIs must be per-arch; bun-native npm distributions; the staged-recipes win-64 leg builds noarch recipes; npm `engines` caps colliding with the nodejs run-export; strict-channel-priority local-channel shadowing; rattler python tests default `pip_check` to TRUE) and **G106** (v8.78.0 — `hatch-build-scripts`' `OneScriptConfig.clean_artifacts` defaults `True` and unlinks the hook's artifacts *before* honoring a SKIP env var, silently shipping an incomplete package that `imports:` + `pip_check` still pass).

| Code | Description | Lives where |
|---|---|---|
| **G1** | `script:` list entries run in separate shells — env vars do NOT carry across entries | SKILL.md |
| **G2** | v0/meta.yaml field names in v1 recipe.yaml are silently ignored | SKILL.md |
| **G3** | `py < N` skip selectors do nothing in v1 recipe.yaml | SKILL.md |
| **G4** | Sdist may omit LICENSE — `pip install` succeeds, build fails with "No license files were copied" | SKILL.md + `guides/sdist-missing-license.md` |
| **G5** | tree-sitter PyPI sdists inconsistently strip `src/tree_sitter/*.h` headers — default to GitHub source for `tree-sitter-<lang>` | SKILL.md |
| **G6** | npm packages with rich transitive deps ship `node_modules/.bin/` symlinks that fail noarch builds | SKILL.md |

**G7–G53** (all in SKILL.md; titles only — see SKILL.md for symptom + fix):
G7 grayskull import-name guess can be wrong · G8 redundant wheel/setuptools host deps for poetry-core · G9 monorepo with no per-language tag → pin LICENSE to a commit · G10 PyPI→conda name divergence (check four spellings) · G11 sdist symlinks fail hatchling on Windows · G12 platform-conditional noarch run deps need `noarch_platforms` · G13 CWD persists across `script:` entries / `(cmd)` not a subshell on cmd.exe · G14 autotick v0 bump trips linter float-parse · G15 same-version rebuild leaves repodata stale · G16 PyPI Varnish CDN degradation on source route · G17 pnpm `--ignore-scripts` doesn't suppress root lifecycle scripts · G18 unscoped `store_build_artifacts` crashes Windows Azure · G19 Windows pip UTF-8 stream error → `PYTHONUTF8: "1"` · G20 v0 jinja `{{ X }}` renders as literal text in v1 · G21 smithy mis-aligns `is_python_min` on upward override · G22 recipe-local CBC `*_cpython` crashes smithy py3.13+ · G23 inline sed+powershell escape hell · G24 conda label ≠ wheel dist-info version · G25 conda has no extras — flatten `pkg[extra]` into run · G26 loosening `==`→`>=` needs source patch under `pip_check` · G27 top-level import eagerly pulls a sibling's extra-only dep · G28 external dep's broken dist-info version breaks dependent `pip check` · G29 multi-output checkers are top-level-only · G30 cf `protobuf` ≠ `protoc` → Rust needs `libprotobuf` · G31 upward python_min override needs recipe-local CBC (v1) / `{% set %}` (v0) · G32 triaging autotick flake-vs-fix + push to bot branch · G33 don't pass `.ci_support` as variant config on local v1 feedstock build · G34 `pkg_resources.declare_namespace` breaks under setuptools 81+ · G35 noarch numpy env-marker selector collapse (refines G12) · G36 stale build wheel METADATA caps tighter than conda run dep · G37 `[tool.uv]` flags are NOT runtime deps · G38 single-Python compiled prereq blocks other-Python consumers · G39 setuptools_scm private-API `_version_helper` import break · G40 dep drops a Python version in a newer release (refines G38) · G41 hidden py3.11 floor via unconditional PEP-655 import · G42 verify CURRENT version's artifact shape before assuming compiled · G43 v1 inline list-item `# comment` trips comment-selector lint · G44 .NET/C# CLI tools have no source-build path — repackage release binaries · G45 browser SPA usually not cf-submittable — viability gate + local-only static-site fallback · G46 stale local `meta.yaml` `noarch: python` flag can be wrong for a genuinely-compiled package — current sdist is source of truth (sibling of G42) · G47 stale git-tracked recipe-dir `conda_build_config.yaml` (verbatim global-CBC copy) breaks build — lint errors + variant `duplicate entry` collision · G48 "Rust/Go upstream" ≠ heavy from-source compile — verify the PEP-517 backend before sizing build / adding `compiler('cxx')` · G49 per-Python compiled ≠ abi3 — verify `Cargo.toml`/setup.py before `version_independent`+`python-abi3`; per-Python artifact needs simple imports+pip_check test · G50 newer CPython dropping a private C-API symbol breaks a compiled build / host pin — cap python matrix with `match(python, ">=N")` (not `py<N`, per G3) · G53 a GitHub monorepo subdir may ship none of the release-time-generated assets — source the PyPI wheel instead or ship a broken empty package

---

## Recipe Security Boundaries (SKILL.md § Recipe Security Boundaries)

Three-tier permission model:

- **Always Do** — verify SHA256 from PyPI JSON / sha256sum (never paste upstream's claimed hash); use `dry_run=True` for `submit_pr`; check for known CVEs with `scan_for_vulnerabilities`
- **Ask First** — adding new compiler-toolchain deps; loosening pins below `conda-forge-pinning-feedstock`; committing patches that touch security-sensitive code paths
- **Never Do** — paste upstream's claimed SHA256 without re-fetching; submit a recipe with unresolved Critical/High CVEs; force-push without `--force-with-lease`; mix v0 and v1 in a build run; commit secrets to any recipe; use the `JFROG_API_KEY` env var in a shell that touches external hosts (see `deployment-guide.md`)

---

## Build Failure Protocol (SKILL.md § Build Failure Protocol)

When `get_build_summary` reports failure (read `conda_build.log` directly to confirm — `get_build_summary` can report a false negative):

1. **STOP** the autonomous loop. Do not retry without diagnosis.
2. **Preserve the log**: `build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log` (resolve `<id>` with `ls -t build_artifacts/*/bld/rattler-build_<name>_*/work/conda_build.log | head -1`).
3. **Run `analyze_build_failure`** to pattern-match the failure mode against `failure_analyzer.py`'s in-module signature catalog. *(Corrected 2026-07-25: this previously said "against `tests/fixtures/error_logs/`" — that fixture directory does not exist.)*
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

*Corpus state, re-counted 2026-07-25 and cross-checked against `bmad-drift-check` (was "1,602 output recipes — 718 `recipe.yaml` + 1,054 `meta.yaml`"): **1,667 recipe directories** under `recipes/`, holding **933 `recipe.yaml`** and **1,024 `meta.yaml`** files, with **300 directories carrying both**. Dual-format directories are not a violation of the "never mix formats" constraint — that constraint governs a **build run**, not a directory. They are the documented transitional shape when the upstream feedstock is still v0: pull and keep `meta.yaml`, author `recipe.yaml` alongside, and delete `meta.yaml` only after the feedstock completes its own v0→v1 switch. The mass migration is still underway; this corpus is churny and is deliberately **not** gated by the drift detector.*

---

## Atlas Intelligence Integration (SKILL.md § Atlas Intelligence Layer)

Part 2 (cf_atlas) is owned conceptually by Part 1 — its scripts live in `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` and its phase-CLI entrypoints share the wrapper layer. The skill exposes the atlas via:

- **Build**: `pixi run -e local-recipes bootstrap-data --fresh` (full) or `pixi run -e local-recipes atlas-phase <ID>` (single phase)
- **Daily-use CLIs — 25**, per SKILL.md § *Daily-use CLIs (all offline; all support `--json`)*: `detail-cf-atlas`, `staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`, `cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`, `platform-breakdown`, `pyver-breakdown`, `channel-split`, `scan-project`, `export-purls`, `mapping-gap`, `universe-sbom`, `inventory-match`, `add-handoff`, `library-futures`, `recommend-2027`, `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap`
- **MCP exposure**: **not** every CLI — 6 are CLI/pixi-only with no MCP tool (`library-futures`, `add-handoff`, and the four seed-gap suggesters), and `mapping-gap` likewise has none. Part 2 records a live conflict over the read-CLI total (25 here vs "28 read CLIs" asserted by the Kedro reimplementation).
- **When to invoke**: before any recipe-authoring decision that depends on package metadata (version skew, CVE surface, alternative packages, popularity tier) — see `reference/atlas-phases-overview.md`, which is now the single consolidated reference (**Part A** persona-mapped signal catalog + **Part B** phase-indexed overview). *Corrected: the former `reference/atlas-actionable-intelligence.md` was absorbed into it on 2026-07-02 and no longer exists.*

Full Part 2 detail: `architecture-cf-atlas.md`.

---

## Portability: MANIFEST.yaml + install.py

The skill is designed to be **standalone-portable**. `MANIFEST.yaml` (line 11: `type: standalone-portable`) declares:
- skill canonical paths (`skill_root: .claude/skills/conda-forge-expert`)
- required external tools (pixi, rattler-build, gh, etc.)
- pixi tasks to inject into the host repo
- MCP server placement
- runtime data directory location

`install.py` (238 lines) bootstraps the skill into a new host repo:
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

1. **Session boot**: Claude Code starts the FastMCP server at `.claude/tools/conda_forge_server.py` (Part 3) over **stdio**; the 46 MCP tools become available. *Registration is **global**, in `~/.claude.json` under `mcpServers.conda_forge_server` — not in the repo (there is no `.mcp.json` at repo root). See Part 3.*
2. **Task entry**: when the user prompt or BMAD agent mentions "conda recipe / conda-forge / packaging / build failure," Claude Code activates this skill.
3. **Skill load order** (frontmatter says `allowed-tools: [conda_forge_server]`):
   - Load `SKILL.md` fully (always)
   - Load `INDEX.md` for navigation (always)
   - Load `reference/<topic>.md` on demand (when the task mentions the topic)
   - Load `guides/<workflow>.md` on demand (when the task matches the guide's scope)
   - Load `quickref/commands-cheatsheet.md` when generating shell-command suggestions
4. **Per-task autonomous loop**: 12 gated stages, with step 8b as the sole human checkpoint (see above).
5. **Per-effort retro** (per `CLAUDE.md` § BMAD ↔ conda-forge-expert integration, Rule 2): on closeout of any BMAD effort that touched conda-forge work, `bmad-retrospective` updates SKILL.md / reference / guides / CHANGELOG.

---

## Spec-Surface Governance (new in v8.79.1)

Since v8.79.1 the skill's own files are a **governed surface** under the repo-wide regenerable-factory program. The brownfield Spec `spec-packaging-factory` (at `planning-artifacts/specs/spec-packaging-factory/`) declares:

```yaml
surface:
  - .claude/skills/conda-forge-expert/**
  - .claude/scripts/conda-forge-expert/**
  - .claude/tools/conda_forge_server.py
surface-drift: sentinel:.claude/skills/conda-forge-expert/CHANGELOG.md
```

The deterministic checker `scripts/spec_surface_check.py` (+ `spec_surface_allowlist.txt` + `.spec-surface-baseline.json`) enforces repo-wide coverage and drift over that surface. The **CHANGELOG sentinel** is the mechanism that matters architecturally: *a governed edit that moves neither the CHANGELOG nor the Spec memlog is a checker finding.* That mechanizes `CLAUDE.md` Rule 2 ("the retro is not optional") at the file level — the CHANGELOG moving is what proves the contract moved.

Notably, the Spec **does not restate** the skill's contract. It **adopts** `SKILL.md` and `CHANGELOG.md` as companions: SKILL.md *is* the operating contract, kept current by the Rule-2 retro loop and the drift-check sync loop. `recipes/**` is governed separately by the sibling Spec `spec-fleet-stewardship` (coverage-only, `surface-drift: exempt` — per-recipe change control remains the autonomous loop plus its gates).

v8.79.1 exists solely to record this binding: no operational guidance, gotcha, CLI, or schema changed, and no recipes were authored. Its one code artifact is `tests/meta/test_spec_surface_check.py`, joining the meta suite (now 9 files).

---

## Drift Detection

The skill version is the **source of truth** for what rules apply. As of 2026-07-25 there are **four** version surfaces and they **do not agree**:

| Surface | Declares | Status |
|---|---|---|
| `config/skill-config.yaml` → `skill.version` | **8.79.1** | ✅ canonical — bumped by every Rule-2 retro |
| `CHANGELOG.md` TL;DR | **v8.79.1** (Jul 23, 2026) | ✅ agrees with skill-config |
| `SKILL.md` frontmatter → `version:` | **7.0.0** | ❌ **stale — not bumped since May 2026** |
| `MANIFEST.yaml` → `skill.version` | **7.0.0** | ❌ **stale — not bumped since May 2026** |

> **⚠ LIVE DEFECT — recorded, not resolved.** `SKILL.md`'s frontmatter and `MANIFEST.yaml` have both been frozen at `7.0.0` across ~40 MINOR releases. `MANIFEST.yaml`'s 7.0.0 was *arguably* defensible under the older reading of it as a "schema/portability version" that bumps only when the install protocol changes — but `SKILL.md`'s frontmatter has no such excuse, and neither file says which reading applies. The gap is unpoliced: `tests/meta/test_skill_md_consistency.py` **does not assert version parity** between SKILL.md/MANIFEST.yaml and skill-config.yaml/CHANGELOG.md. Any consumer reading the skill version from SKILL.md frontmatter — the most obvious place to look — gets a number 40 releases out of date. This doc pins `source_pin: v8.79.1` from the canonical pair and does **not** pick a winner for the stale pair. Remedies (either is fine, pick one): bump both stale files and add a parity assertion to `test_skill_md_consistency.py`, or explicitly document the two-version model in `MANIFEST.yaml` and delete the `version:` key from SKILL.md's frontmatter.

Project-context.md re-syncs on MINOR bumps (current skill release **v8.79.1**; latest MINOR **v8.79.0**). When CHANGELOG's MINOR exceeds the last-synced version, re-verify volatile sections (Recipe Format, MCP Lifecycle, Anti-Patterns). PATCH bumps don't require re-sync.

The pin discipline is the rebuild target's drift-control mechanism. A rebuilt repo without this pin will silently diverge.

---

## Integration Points (recap)

See `integration-architecture.md` for the cross-part contracts. Summary:

- **→ Part 2 (cf_atlas)**: Part 2's pipeline lives in this skill's `scripts/`. Shared data dir: `.claude/data/conda-forge-expert/`.
- **→ Part 3 (MCP server)**: each MCP tool in `conda_forge_server.py` **subprocess-executes** this skill's `scripts/<module>.py` via `_run_script()` — it does *not* import them. Part 3 is the wire format; Part 1's scripts are the implementation. (Corrected 2026-07-25; the prior wording said "imports from", which contradicts Part 3's own § *Why subprocess and not direct import?*.)
- **→ Part 4 (BMAD)**: every BMAD agent doing conda-forge work invokes this skill (`Skill: conda-forge-expert`) per CLAUDE.md Rule 1. Every effort closeout runs a retro that updates this skill per CLAUDE.md Rule 2.
- **→ Enterprise layer**: every outbound HTTP request from any Part routes through `scripts/_http.py`. The JFROG_API_KEY cross-host leak is mitigated at the deployment layer, not within the skill.
- **→ vuln-db env**: Part 1's `scan_for_vulnerabilities` + Part 2's Phase G/G' require the `vuln-db` pixi env (AppThreat vdb importable).

---

## Rebuild checklist for Part 1

To rebuild this part faithfully on a clean repo:

1. **Bootstrap**: install pixi; create `pixi.toml`. The live repo defines **15 environments** — the six this part needs are `python`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`; the other nine (`linux`/`osx`/`win`, `gcloud`, `bmad-ui`, and the lean per-persona `pyforge-{warden,atlas,doctor,scribe,herald}` envs) belong to other parts.
2. **Skill scaffolding**: copy `.claude/skills/conda-forge-expert/` from this repo OR generate fresh from SKILL.md template.
3. **Tier 1 scripts** (66 modules / 41,410 LOC): authored in dependency order — `_http.py` first (every other module imports it), then `name_resolver.py` + `mapping_manager.py` (foundational helpers), then recipe-lifecycle, then atlas-pipeline, then the purl/BOM/gap suite.
4. **Tier 2 wrappers** (57 `.py` + 2 `.sh` + README = 60 entries): thin subprocess wrappers; auto-generatable from a manifest if all Tier 1 modules expose a `main()`.
5. **Pixi tasks**: **106** entries under `[feature.local-recipes.tasks.*]`, mostly matching the Tier 2 wrapper names.
6. **Meta-test**: `tests/meta/test_all_scripts_runnable.py` with SCRIPTS list + no_task_allowlist enforcing the three-place rule.
7. **Templates**: 41 starter recipes across 13 subdirs (12 language/shape + 1 conda-forge.yml config-template subdir with 2 starter files), plus `templates/README.md`.
8. **Documentation**: SKILL.md (3,887 lines) + INDEX.md (180) + CHANGELOG.md (1,841) + reference/* (**15** files, incl. `atlas-phase-engineering.md` since v7.8.0) + guides/* (9 files) + quickref/* (2 files) + data/* (3: `cwe_categories_seed.json`, `lts-registry.yaml`, `spdx.schema.json`) + config/* (2) + examples/ (6) + automation/ (3).
9. **MANIFEST.yaml + install.py** for portability (skill should be installable into other repos). Add the version-parity assertion the live repo is missing (see § Drift Detection).
10. **Mapping subsystem**: seed `pypi_conda_mappings/different_names.json` from public data; `custom.yaml` starts empty.
11. **Spec-surface binding** (v8.79.1): declare the skill tree as a Spec `surface:` with a `surface-drift: sentinel:` on its CHANGELOG, and wire `scripts/spec_surface_check.py` into the meta suite.

Rebuild order matters: Part 1 must exist before Parts 2 and 3 (which extend it) and before Part 4's BMAD↔CFE integration rules become enforceable.
