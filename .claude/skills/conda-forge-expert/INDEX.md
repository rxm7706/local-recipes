# conda-forge-expert — Task-Based Navigator

Find the tool, CLI, doc, or section for a specific task. **Start here**
when you have a goal but don't know which file to read.

For the full skill behavior contract, read `SKILL.md`. For the version
history, read `CHANGELOG.md` (latest entry has a TL;DR at the top).

---

## I want to: author / edit a recipe

| Task | Tool / CLI / Doc |
|---|---|
| Generate a new recipe from PyPI | MCP `generate_recipe_from_pypi` · CLI `generate-recipe` |
| Generate from CRAN / CPAN / LuaRocks / npm | CLI `generate-cran` / `generate-cpan` / `generate-luarocks` / `generate-npm` |
| Validate / lint a recipe | MCP `validate_recipe` · MCP `optimize_recipe` · CLI `validate` · CLI `lint-optimize` |
| Edit a recipe field programmatically | MCP `edit_recipe` (preferred over manual file edits) |
| Migrate `meta.yaml` → `recipe.yaml` | MCP `migrate_to_v1` · guide `guides/migration.md` |
| Build a recipe locally | MCP `trigger_build` · CLI `recipe-build` (native) / `recipe-build-docker` |
| Diagnose a build failure | MCP `analyze_build_failure` · guide `guides/ci-troubleshooting.md` |
| Update a recipe to a new upstream version | MCP `update_recipe` (PyPI) · MCP `update_recipe_from_github` |
| Submit to conda-forge | MCP `submit_pr` (always `dry_run=True` first) |
| Look up the recipe-yaml schema | reference `reference/recipe-yaml-reference.md` |
| Look up meta.yaml syntax | reference `reference/meta-yaml-reference.md` |
| Look up Jinja functions | reference `reference/jinja-functions.md` |
| Look up version-pinning rules | reference `reference/pinning-reference.md` |
| Look up platform selectors | reference `reference/selectors-reference.md` |
| Look up `python_min` policy | reference `reference/python-min-policy.md` |
| Find a sdist-missing-license workaround | guide `guides/sdist-missing-license.md` |

The 9-step authoring workflow is documented in
`SKILL.md` § "Primary Workflow: The Autonomous Loop".

---

## I want to: query the cf_atlas (intelligence layer)

The atlas is at `.claude/data/conda-forge-expert/cf_atlas.db` (SQLite).
All queries below are **offline-safe**. Phase G's *fresh* vuln data
needs the `vuln-db` env; cached counts work everywhere.

| Question | Tool / CLI |
|---|---|
| Show me one package's full health card | MCP `package_health` · CLI `detail-cf-atlas <pkg>` |
| List all my feedstocks | MCP `my_feedstocks` · CLI `staleness-report --maintainer X` (also surfaces stalest) |
| What should I work on this week? (triage) | MCP `staleness_report --by_risk` · CLI `staleness-report --maintainer X --by-risk` |
| Which feedstocks have stuck bots? | MCP `feedstock_health filter_kind="stuck"` · CLI `feedstock-health --filter stuck` |
| Which feedstocks have failing CI on default branch? | MCP `feedstock_health filter_kind="ci-red"` (requires Phase N data) |
| Which feedstocks have open issues / human PRs? | MCP `feedstock_health filter_kind="open-issues"` / `"open-prs-human"` |
| Which feedstocks are behind upstream? | MCP `behind_upstream` · CLI `behind-upstream --maintainer X` |
| What CVEs landed this week? | MCP `cve_watcher` · CLI `cve-watcher --maintainer X --severity C --only-increases` |
| Who depends on my package? | MCP `whodepends reverse=True` · CLI `whodepends <pkg> --reverse` |
| What does my package depend on? | MCP `whodepends` · CLI `whodepends <pkg>` |
| Per-version download breakdown | MCP `version_downloads` · CLI `version-downloads <pkg>` |
| Is this package's release cadence accelerating or slowing? | MCP `release_cadence` · CLI `release-cadence --package <pkg>` |
| Is this package mature / declining / silent? | MCP `adoption_stage` · CLI `adoption-stage --package <pkg>` |
| Suggest a maintained alternative for an archived package | MCP `find_alternative` · CLI `find-alternative <pkg>` |
| Generic SQL escape hatch | MCP `query_atlas` (read-only, write-keywords blocked) |
| Catalog of every actionable signal by persona | reference `reference/atlas-actionable-intelligence.md` |
| Per-phase overview (data source, purpose, intel each stage produces) | reference `reference/atlas-phases-overview.md` |

---

## I want to: scan a project / image / SBOM / live env

The unified scanner is `scan-project` (CLI) / `scan_project` (MCP). It
auto-discovers manifests under a path AND accepts ~12 specific input
modes for non-path sources.

| Input | Flag |
|---|---|
| Project tree (auto-discovers manifests) | `<path>` (default cwd) |
| GitHub repo | `--github <owner>/<repo>` |
| Container image (single) | `--image <ref>` (uses syft → trivy) |
| Container image (multiple) | `--image alpine:3.19,nginx:1.25` or repeated `--image` |
| OCI archive | `--oci-archive <path.tar>` |
| OCI manifest probe (no SBOM) | `--oci-manifest <ref>` |
| SBOM file (CycloneDX/SPDX/syft/trivy, JSON or XML) | `--sbom-in <file>` |
| Live conda env directory | `--conda-env <env-path>` |
| Live Python venv directory | `--venv <venv-path>` |
| Live Kubernetes cluster | `--kubectl-all` (or `--kubectl-context X`) |
| Helm chart (rendered) | `--helm-chart <path>` `--helm-values <values.yaml>` |
| Kustomize overlay (built) | `--kustomize <dir>` |
| Argo CD `Application` CR | `--argo-app <cr.yaml>` |
| Flux CD `HelmRelease` / `Kustomization` CR | `--flux-cr <cr.yaml>` |

Output options: `--brief` (summary card) · `--json` (machine-readable)
· `--sbom cyclonedx` / `--sbom spdx` (emit SBOM) · `--sbom-out <file>` ·
`--enrich-vulns-from-atlas` (cf_atlas Phase G annotations on emitted
SBOM, no vuln-db env required) · `--license-check --target-license <X>`
(license compatibility table).

| Question about scan support | Doc |
|---|---|
| Which manifest / lock-file / SBOM formats are supported? | reference `reference/dependency-input-formats.md` |
| What VEX statements does a CycloneDX 1.5+ SBOM carry? | rendered automatically when present in `--sbom-in` input |
| How to scan an air-gapped registry | `--oci-manifest <ref>` (manifest-only); full SBOM extraction needs syft/trivy in env |

---

## I want to: build / refresh the cf_atlas database

```bash
# Default phases (B/B.5/B.6/C/C.5/D/F/G/J/L/M)
pixi run -e local-recipes build-cf-atlas

# Add cf-graph enrichment (Phase E ~150 MB tarball)
PHASE_E_ENABLED=1 pixi run -e local-recipes build-cf-atlas

# Add per-version vuln scoring (Phase G' — needs vuln-db env)
PHASE_GP_ENABLED=1 pixi run -e vuln-db build-cf-atlas

# Add live GitHub data (Phase N — needs gh auth)
PHASE_N_ENABLED=1 PHASE_N_MAINTAINER=<handle> \
    pixi run -e local-recipes build-cf-atlas

# Refresh just the vdb (vulnerability database) for fresh vdb scans
pixi run -e vuln-db vdb-refresh
```

Phase reference: B (conda repodata), B.5 (feedstock-outputs),
B.6 (active/inactive transition), C (parselmouth join), C.5 (folded
into E), D (PyPI Simple), E (cf-graph node_attrs enrichment), E.5
(archived feedstocks via GraphQL), F (anaconda.org downloads),
G (vdb risk summary on latest version), G' (per-version vuln scoring),
H (PyPI current version), J (dependency graph), K (VCS upstream —
GitHub/GitLab/Codeberg), L (npm/CRAN/CPAN/LuaRocks/crates/RubyGems/
NuGet/Maven), M (cf-graph pr_info → bot health), N (live GitHub
CI/issues/PRs).

---

## I want to: understand how the skill works

| Topic | Doc |
|---|---|
| Skill behavior + the 9-step autonomous loop | `SKILL.md` |
| Operating principles (think / simplicity / surgical / goal-driven) | `SKILL.md` § "Operating Principles" |
| Critical constraints (never mix formats, stdlib required, etc.) | `SKILL.md` § "Critical Constraints" |
| Recipe security boundaries | `SKILL.md` § "Recipe Security Boundaries" |
| What changed between versions | `CHANGELOG.md` (TL;DR at top) |
| Skill-level config knobs | `config/skill-config.yaml` |
| Conda-forge ecosystem overview | reference `reference/conda-forge-ecosystem.md` |
| MCP tool catalog | reference `reference/mcp-tools.md` |
| Get started with conda-forge | guide `guides/getting-started.md` |
| Maintain a feedstock | guide `guides/feedstock-maintenance.md` |
| Cross-compile / non-host platforms | guide `guides/cross-compilation.md` |
| Test recipes | guide `guides/testing-recipes.md` |
| CI failures | guide `guides/ci-troubleshooting.md` |
| Bot commands (PR comments) | quickref `quickref/bot-commands.md` |
| Shell command cheatsheet | quickref `quickref/commands-cheatsheet.md` |

---

## I want to: drive the skill from another tool

| Surface | Path |
|---|---|
| MCP server (FastMCP, 30+ tools) | `.claude/tools/conda_forge_server.py` |
| Canonical Python implementations | `.claude/skills/conda-forge-expert/scripts/` |
| Public CLI wrapper layer | `.claude/scripts/conda-forge-expert/` |
| Pixi tasks (preferred shell entrypoint) | repo `pixi.toml` § `[feature.local-recipes.tasks.*]` and `[feature.vuln-db.tasks.*]` |
| Mutable runtime data (gitignored) | `.claude/data/conda-forge-expert/` |

---

## Doc taxonomy reminder

- **`SKILL.md`** = behavior contract + workflow — read end-to-end when first using the skill.
- **`reference/`** = deep API/format documentation — query for a specific symbol or rule.
- **`guides/`** = task walkthroughs — read top-to-bottom when learning a procedure.
- **`quickref/`** = commands cheatsheet — lookup by exact command name.
- **`automation/`** = repeatable prompts (e.g., quarterly audit).
- **`templates/`** = recipe scaffolds.
- **`examples/`** = end-to-end worked examples.

When in doubt: search this INDEX.md by Ctrl-F for the noun in your task
("CVE" / "alternative" / "Argo" / "venv" / etc.), then follow the link.
