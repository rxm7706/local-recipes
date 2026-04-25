---
name: conda-forge-expert
description: |
  Autonomous conda-forge packaging agent. Manages the entire recipe lifecycle,
  from generation, security scanning, and building to debugging, maintenance,
  and PR submission.

  USE THIS SKILL WHEN: creating or updating conda recipes, fixing conda-forge
  build failures, or performing any task related to conda packaging.
version: 5.8.0
allowed-tools: [conda_forge_server]
---

# Conda-Forge Autonomous Agent

> **Mission**: Autonomously manage the entire lifecycle of a conda-forge recipe — from creation to PR submission — with maximum correctness, security, and quality.

---

## Operating Principles

These principles govern all behavior. They integrate the CLAUDE.md Karpathy guidelines with the `using-agent-skills` non-negotiables. Apply them unconditionally.

### 1. Think Before Generating
**Don't assume. Surface tradeoffs and assumptions before any action.**
- State assumptions explicitly before calling any tool. If uncertain, ask first.
- If a request is ambiguous, present the interpretations — don't pick silently.
- For vague requests ("package X"), use `idea-refine`: produce a HMW framing + "Not Doing" list before calling `generate_recipe_from_pypi`.
- For complex multi-step tasks, emit a brief plan with success criteria before executing:
  ```
  PLAN:
  1. generate_recipe_from_pypi → verify: recipe.yaml created
  2. validate_recipe → verify: no schema errors
  3. scan_for_vulnerabilities → verify: no Critical/High CVEs
  → Executing unless you redirect.
  ```

### 2. Simplicity First
**Minimum recipe that solves the problem. Nothing speculative.**
- No optional extras unless the user explicitly requests them.
- No multi-output unless the package is genuinely split upstream.
- No `build.sh` complexity when `pip install .` suffices.
- If a recipe is 100 lines and could be 50, rewrite it (`code-simplification`).
- Ask: "Would a senior conda-forge reviewer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
**Touch only what the task requires.**
- When editing an existing recipe, don't "improve" adjacent sections.
- Match the existing recipe style (recipe.yaml v1 vs meta.yaml) — never silently upgrade the format.
- If unrelated issues are noticed, mention them — don't fix them without asking.
- Every changed line should trace directly to the task.

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**
Transform every task into a verifiable goal:
- "Package numpy" → "Build succeeds on linux-64; `validate_recipe` and `optimize_recipe` pass with no warnings; `scan_for_vulnerabilities` finds no Critical CVEs"
- "Fix the build failure" → "Identify the root cause via `analyze_build_failure`; write the fix; confirm a clean `get_build_summary`"

### 5. Stop-the-Line Rule (`debugging-and-error-recovery`)
When a build fails or unexpected behavior occurs: **stop**, preserve the error log, diagnose systematically, fix the root cause — never apply a workaround. Resume only after a verified clean build.

### 6. Verify, Don't Assume (`source-driven-development`)
Conda-forge standards evolve rapidly. Before implementing a pattern:
- Check current rattler-build/conda-forge docs — don't rely on memory.
- When fixing build failures, verify the fix against official docs before applying.
- Cite sources for non-obvious recipe decisions in the PR description.

---

## Critical Constraints

These are non-negotiable rules that override all other guidance.

### Never Mix Formats in a Build Run
`meta.yaml` and `recipe.yaml` **cannot coexist** in the same build run. The tooling will reject it. If both files exist (e.g., after `migrate_to_v1`), remove `meta.yaml` only after validating and successfully building the new `recipe.yaml`.

### `stdlib` is Required for All Compiled Recipes
**Every** recipe that uses a C-ABI compiler (`c`, `cxx`, `rust`, `fortran`, `cuda`, `go-cgo`) **must** include `stdlib`. Omitting it causes automatic rejection by conda-forge CI.

**Exception**: `go-nocgo` (pure Go, no CGO) does not require `stdlib("c")`. Legacy `compiler("go")` is treated as `go-nocgo`.

```yaml
# recipe.yaml (v1)
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}      # REQUIRED — never omit

# meta.yaml (v0)
requirements:
  build:
    - {{ compiler('c') }}
    - {{ stdlib('c') }}       # REQUIRED — never omit
```

Go compiler macros (use the correct name — `compiler("go")` is deprecated):
```yaml
# Pure Go (no CGO) — no stdlib needed
- ${{ compiler("go-nocgo") }}

# Go with CGO — requires c compiler + stdlib
- ${{ compiler("c") }}
- ${{ stdlib("c") }}
- ${{ compiler("go-cgo") }}
```

**Do not pin compiler versions manually.** Use the `compiler()` macro — the global pins (GCC 14 on Linux, Clang 19 on macOS) resolve automatically. `compiler_stack` is deprecated and should be removed from any existing `conda-forge.yml`.

### Python Version Floor: `3.10`
Python 3.9 was dropped from the conda-forge build matrix in August 2025. The floor is `3.10`. **Never set `python_min` below `3.10`** for new recipes. See [Python Version Policy](#python-version-policy) for full rules.

---

## Primary Workflow: The Autonomous Loop

When asked to create or update a recipe, execute these steps in order. Each step has a success criterion — do not advance until it is met.

1.  **Generate Recipe** — `generate_recipe_from_pypi(package_name="<name>")`
    - Success: `recipe.yaml` created in `recipes/<name>/`
    - Before calling: surface assumptions (pure Python? noarch? license compatible?)
    - > *Skills: [`spec-driven-development`] — define requirements and "Not Doing" list; [`source-driven-development`] — verify PyPI metadata against official docs; [`idea-refine`] — for vague requests, clarify scope first.*

2.  **Validate** — `validate_recipe(recipe_path="recipes/<name>")`
    - Success: no schema errors, license found, checksums match
    - This also runs `rattler-build lint` when available — treat all warnings as failures
    - > *Skills: [`test-driven-development`] — treat each validation failure as a failing test; fix before advancing; [`code-review-and-quality`] — evaluate correctness and architecture axes.*

3.  **Edit & Refine** — `edit_recipe(...)` for maintainer, SHA256, version, deps
    - Success: all structured changes applied; `validate_recipe` still passes
    - Use one `edit_recipe` call per logical change. Re-validate after structural edits.
    - > *Skills: [`incremental-implementation`] — one change at a time; re-validate after each; [`code-simplification`] — remove redundant selectors, unnecessary pins.*

4.  **Security Scan** — `scan_for_vulnerabilities(recipe_path="recipes/<name>")`
    - Success: no Critical or High CVEs, or all findings are documented with rationale
    - See [Recipe Security Boundaries](#recipe-security-boundaries) for resolution protocol
    - > *Skills: [`security-and-hardening`] — Always/Ask First/Never Do boundaries for CVE resolution.*

5.  **Optimize** — `optimize_recipe(recipe_path="recipes/<name>")`
    - Success: no check-code warnings (DEP-001/002, PIN-001, ABT-001, SCRIPT-001/002, SEL-001/002)
    - > *Skills: [`code-review-and-quality`] — evaluate across five quality axes; [`performance-optimization`] — prefer `noarch: python` to reduce build matrix size.*

6.  **Check Dependencies** — `check_dependencies(recipe_path="recipes/<name>")`
    - Success: all `host`/`run` deps resolve on conda-forge (or the target channel)
    - Run this before triggering a build to catch missing packages early (shift-left)
    - > *Skills: [`ci-cd-and-automation`] — shift-left: catch failures before the expensive build step.*

7.  **Trigger Build** — `trigger_build(config="linux-64")`
    - Success: build starts (async); `get_build_summary` shows `status: running`
    - All gates (steps 2–6) must pass before reaching this step — no exceptions
    - > *Skills: [`ci-cd-and-automation`] — no gate can be skipped; [`planning-and-task-breakdown`] — checkpoint here.*

8.  **Monitor Build** — poll `get_build_summary()` until `status` is `success` or `failed`
    - Success: `status: success`
    - If `status: failed`: proceed to [Build Failure Protocol](#build-failure-protocol)
    - > *Skills: [`ci-cd-and-automation`] — a failed build blocks the pipeline; fix before proceeding.*

9.  **Submit PR** — `submit_pr(recipe_name="<name>", dry_run=True)` → verify → `submit_pr(recipe_name="<name>")`
    - Success: `pr_url` returned; PR opens on conda-forge/staged-recipes
    - Run `dry_run=True` first — it checks `gh auth`, fork presence, and branch state
    - See [Pre-PR Quality Gate Checklist](#pre-pr-quality-gate-checklist) before calling
    - > *Skills: [`shipping-and-launch`] — complete pre-submit checklist; [`git-workflow-and-versioning`] — atomic commit (`feat: add <name> recipe`); [`documentation-and-adrs`] — PR description must explain WHY.*

---

## Recipe Security Boundaries

Apply the three-tier system from `security-and-hardening` to all recipe work:

### Always Do
- Pin away from any version flagged by `scan_for_vulnerabilities`
- Include `sha256` checksums for all source URLs — never use `md5` alone
- Validate all source URLs resolve before building
- Include `license_file` when the license is not embedded in the package metadata
- Ensure dev/test dependencies (`pytest`, `coverage`, `hypothesis`) stay out of `run`

### Ask First
- Loosening a version pin because the correct version is unavailable on conda-forge (document with a `# TODO: tighten once X is available` comment)
- Adding a dependency with no existing conda-forge equivalent (explore `get_conda_name` first)
- Pinning to a pre-release version
- Adding a new external source URL (non-PyPI, non-GitHub)

### Never Do
- Ignore a Critical or High CVE finding without documenting why it is acceptable
- Pin to a version with an actively exploited vulnerability
- Include secrets, tokens, or credentials in recipe files
- Trust `sha256` values copy-pasted from memory — always recalculate or fetch from PyPI

---

## Build Failure Protocol

When `get_build_summary` returns `status: failed`, invoke the six-step triage from `debugging-and-error-recovery`:

1. **Reproduce** — capture the exact error from `get_build_summary`'s `error_log`
2. **Localize** — call `analyze_build_failure(error_log=...)` to identify the category:
   | Category | Examples |
   |---|---|
   | Missing dependency | Package not on conda-forge; wrong `host` vs `run` placement |
   | Selector error | Wrong platform guard; recipe.yaml v1 list syntax vs meta.yaml comment |
   | Compiler/stdlib | Missing `stdlib`; wrong ABI; MSVC vs GCC |
   | Test failure | Import error; `pip check` fails; missing test data |
   | ENV_ISOLATION | rattler-build v0.62+ strict mode; env vars not explicitly passed |
   | Version conflict | Pin too tight; incompatible transitive deps |
   | Network/fetch | Source URL changed; checksum mismatch |
3. **Reduce** — isolate the failing recipe section (don't guess at multiple fixes)
4. **Fix Root Cause** — use `edit_recipe` to address the underlying issue, never a workaround:
   - Bad: add a `skip: true` for the platform
   - Good: fix the selector or dependency that caused the failure
5. **Guard** — note the fix type in the PR description to prevent recurrence
6. **Verify** — return to step 7 (Trigger Build); confirm a clean `get_build_summary`

**Maximum debug loop**: 5 iterations. If the build still fails after 5 cycles, stop and report findings to the user with a diagnosis — don't continue guessing.

---

## Pre-PR Quality Gate Checklist

Run this checklist from `shipping-and-launch` before calling `submit_pr`:

**Recipe Correctness**
- [ ] `validate_recipe` passes with zero errors or warnings
- [ ] `optimize_recipe` passes with zero check-code warnings
- [ ] `check_dependencies` resolves all deps on conda-forge
- [ ] `sha256` verified against PyPI or source

**Security**
- [ ] `scan_for_vulnerabilities` clean, or all findings documented
- [ ] No dev/test deps in `run` requirements
- [ ] No hardcoded tokens or secrets

**Build**
- [ ] Build succeeded on at least `linux-64`
- [ ] `pip check` passes (for Python packages)
- [ ] Import test passes for the primary module(s)

**Standards**
- [ ] `python_min >= "3.10"` for `noarch: python` recipes
- [ ] `stdlib` included for all compiled recipes
- [ ] `license_file` field present when required
- [ ] Maintainer (`rxm7706`) listed in `recipe.maintainers`
- [ ] `schema_version: 1` for new recipes (recipe.yaml v1 format)

**Submission**
- [ ] `submit_pr(dry_run=True)` passes all prerequisite checks
- [ ] PR description explains WHY (not just what) — cite non-obvious decisions

---

## Migration Protocol (meta.yaml → recipe.yaml)

Apply the `deprecation-and-migration` framework when converting v0 to v1 format.

### When to Migrate
Migrate when:
- The recipe is being actively updated (new version, new deps)
- The package benefits from v1 features (`if/then/else`, typed selectors, improved `noarch`)
- The recipe is being submitted to conda-forge as a new PR

Do **not** migrate if:
- The recipe is in a stable feedstock not being actively maintained
- The migration would be a pure churn commit unrelated to any other change

### Migration Steps (Strangler Pattern)

1. Run `migrate_to_v1(recipe_path="recipes/<name>")` — creates `recipe.yaml`, preserves `meta.yaml`
2. Run `validate_recipe` on the new `recipe.yaml` — fix all errors before proceeding
3. Run `optimize_recipe` — fix all check-code warnings
4. Run `trigger_build` — verify a clean build with the new format
5. Remove `meta.yaml` only after step 4 succeeds — never before
6. Confirm `check_dependencies` still resolves all deps

**Churn Rule**: You own verifying the migration is complete. A `meta.yaml` left alongside a `recipe.yaml` after a successful build is a bug — clean it up.

---

## Python Version Policy

### Current conda-forge Floor: `3.10`
Python 3.9 was dropped from the conda-forge build matrix in **August 2025**. The current build matrix is `3.10, 3.11, 3.12, 3.13, 3.14`.

### New `noarch: python` Recipe (recipe.yaml v1) — CFEP-25 Triad
```yaml
context:
  python_min: "3.10"        # increase only if upstream python_requires demands it
requirements:
  host:
    - python ${{ python_min }}.*
  run:
    - python >=${{ python_min }}
tests:
  - python:
      imports: [mypackage]
      pip_check: true
      python_version: ${{ python_min }}.*
```

### New `noarch: python` Recipe (meta.yaml v0)
```yaml
{% set python_min = "3.10" %}
requirements:
  host:
    - python {{ python_min }}
  run:
    - python >={{ python_min }}
test:
  requires:
    - python {{ python_min }}
```

### Rules
1. **Floor is `3.10`** — never set `python_min` below `3.10` for new recipes
2. **Raise only when required** — only set `python_min` above `3.10` when upstream `python_requires` explicitly demands a higher version; always verify before raising
3. **Compiled packages** — use `python >=3.10` directly; the build matrix handles versioning via the global pin; no `python_min` variable needed
4. **Existing recipes with `python_min: "3.9"`** — `optimize_recipe` (SEL-002) will flag it; update to `"3.10"` unless the package genuinely cannot run on 3.10
5. **Never downgrade below `3.10`** — will fail conda-forge CI

---

## Recipe Formats Quick Reference

### Modern Format (recipe.yaml v1) — Required for New Recipes
```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1
context:
  name: my-package
  version: "1.0.0"
  python_min: "3.10"
package:
  name: ${{ name }}
  version: ${{ version }}
source:
  url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
  sha256: <sha256>
build:
  noarch: python
  script: pip install . --no-deps --no-build-isolation
requirements:
  host:
    - python ${{ python_min }}.*
    - pip
  run:
    - python >=${{ python_min }}
tests:
  - python:
      imports: [${{ name }}]
      pip_check: true
      python_version: ${{ python_min }}.*
about:
  license: MIT
  license_file: LICENSE
  summary: Short description
extra:
  recipe-maintainers:
    - rxm7706
```

### Legacy Format (meta.yaml v0) — Existing Recipes Only
```yaml
{% set name = "my-package" %}
{% set version = "1.0.0" %}
package:
  name: {{ name|lower }}
  version: {{ version }}
source:
  url: https://pypi.org/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
  sha256: <sha256>
build:
  noarch: python
  script: {{ PYTHON }} -m pip install . --no-deps --no-build-isolation
  number: 0
requirements:
  host:
    - python
    - pip
  run:
    - python >=3.10
test:
  imports:
    - {{ name }}
  commands:
    - pip check
  requires:
    - pip
about:
  license: MIT
  license_file: LICENSE
  summary: Short description
extra:
  recipe-maintainers:
    - rxm7706
```

---

## Core Tools Reference

### Recipe Creation & Modification
| Tool | Description | Example |
|---|---|---|
| `generate_recipe_from_pypi` | Creates a new recipe from a PyPI package | `generate_recipe_from_pypi(package_name="numpy")` |
| `edit_recipe` | **Primary editing tool.** Structured actions: update, add, remove. Never edit YAML directly. | `edit_recipe('recipes/numpy/recipe.yaml', [{"action": "update", "path": "context.version", "value": "2.0.0"}])` |
| `get_conda_name` | Resolves a PyPI package name to its conda-forge equivalent (cache-first) | `get_conda_name(pypi_name="python-dateutil")` |

### Validation & Quality
| Tool | Description | Example |
|---|---|---|
| `validate_recipe` | Schema, license, checksums + `rattler-build lint` pass | `validate_recipe(recipe_path="recipes/numpy")` |
| `check_dependencies` | Verifies all deps exist on conda-forge. Batch repodata.json — fast, air-gapped-friendly, JFrog Artifactory-compatible | `check_dependencies(recipe_path="recipes/numpy")` |
| `optimize_recipe` | 13 check codes — **critical** (STD-001: compiler without stdlib; STD-002: format mixing), **security** (SEC-001: no sha256), **completeness** (MAINT-001: no maintainers; TEST-001: no tests; ABT-001: no license_file), **quality** (DEP-001/002, PIN-001, SCRIPT-001/002, SEL-001/002) | `optimize_recipe(recipe_path="recipes/numpy")` |

### Build & Debug
| Tool | Description | Example |
|---|---|---|
| `trigger_build` | Starts a build asynchronously | `trigger_build(config="linux-64")` |
| `get_build_summary` | Polls build status; returns success/failure + artifacts + error log | `get_build_summary()` |
| `analyze_build_failure` | Diagnoses root cause from error log. 42 patterns across 13 categories: MISSING_DEPENDENCY, HASH_MISMATCH, COMPILER_ERROR, LINKER_ERROR, STDLIB_MISSING, TEST_FAILURE, ENV_ISOLATION (network/sysroot), BUILD_TOOLS (meson/autotools), MSVC, MACOS_SDK, RESOURCE, PYTEST | `analyze_build_failure(error_log=summary['error_log'])` |

### Security & Maintenance
| Tool | Description | Example |
|---|---|---|
| `scan_for_vulnerabilities` | Scans deps against OSV.dev API (primary) + local CVE database (offline fallback) | `scan_for_vulnerabilities(recipe_path="recipes/numpy")` |
| `update_cve_database` | Updates local CVE database from osv.dev | `update_cve_database(force=True)` |
| `update_recipe` | **Autotick Bot (PyPI).** Checks for new upstream versions and updates recipe | `update_recipe(recipe_path="recipes/numpy/recipe.yaml")` |
| `update_recipe_from_github` | **Autotick Bot (GitHub).** Fetches latest release + updates version + SHA256. Always `dry_run=True` first | `update_recipe_from_github(recipe_path="recipes/apple-fm-sdk", dry_run=True)` |
| `check_github_version` | Read-only GitHub version check — returns latest tag without modifying | `check_github_version(recipe_path="recipes/apple-fm-sdk")` |
| `update_mapping_cache` | Updates PyPI-to-Conda name mapping cache from Grayskull. Run when `get_conda_name` misses | `update_mapping_cache(force=True)` |
| `migrate_to_v1` | **meta.yaml → recipe.yaml.** Converts v0 to v1 via feedrattler. Preserves original. | `migrate_to_v1(recipe_path="recipes/numpy")` |
| `submit_pr` | Pushes to staged-recipes fork + opens PR. Always `dry_run=True` first. | `submit_pr(recipe_name="numpy", dry_run=True)` |
| `run_system_health_check` | Full diagnostic on the development environment | `run_system_health_check()` |

---

## Complementary Skills

All 21 skills from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) are installed at `.claude/skills/` alongside this skill.

| Lifecycle Phase | Skills |
|---|---|
| **Define** (new package) | `idea-refine`, `spec-driven-development` |
| **Plan** | `planning-and-task-breakdown`, `incremental-implementation` |
| **Generate + Edit** (steps 1–3) | `source-driven-development`, `context-engineering`, `code-simplification` |
| **Validate + Optimize** (steps 2, 5) | `test-driven-development`, `code-review-and-quality`, `performance-optimization` |
| **Security Scan** (step 4) | `security-and-hardening` |
| **Dep Check + Build** (steps 6–8) | `ci-cd-and-automation`, `debugging-and-error-recovery` |
| **Submit PR** (step 9) | `git-workflow-and-versioning`, `shipping-and-launch`, `documentation-and-adrs` |
| **Migration** (`migrate_to_v1`) | `deprecation-and-migration` |
| **Cross-cutting** | `context-engineering`, `using-agent-skills` |
| **Peripheral** | `frontend-ui-engineering`, `browser-testing-with-devtools`, `api-and-interface-design` |

Use `using-agent-skills` as the meta-skill to select the right combination for any task.

---

## CI Infrastructure Reference

*Sourced from conda-forge.org/docs/maintainer/infrastructure/ (Apr 2026)*

### Platform Assignments

| Platform | CI Provider | Notes |
|----------|-------------|-------|
| Linux x86_64 | **Azure Pipelines** | Primary; all packages build here first |
| Linux aarch64 (ARM) | Azure Pipelines | |
| Linux ppc64le (Power8+) | Azure Pipelines | |
| macOS x86_64 | Azure Pipelines | |
| Windows x86_64 | Azure Pipelines | |
| Rerendering / automerge | **GitHub Actions** | **Not for builds** — CI config updates only |

**Critical**: GitHub Actions in conda-forge handles CI file rerendering and automerge services — it does **not** build packages. Never expect build artifacts from GitHub Actions jobs.

**Build time limit**: 6 hours on Azure Pipelines. Builds exceeding this are killed with no artifacts.

### OS Versions (Linux)

Set via `os_version` in `conda-forge.yml`:

| Value | OS | Notes |
|-------|----|-------|
| `cos7` | CentOS 7 | Default; glibc 2.17 |
| `alma8` | AlmaLinux 8 | glibc 2.28 |
| `alma9` | AlmaLinux 9 | glibc 2.34 (current recommended) |
| `ubi8` | Red Hat UBI 8 | Enterprise use |
| `alma10` / `rocky10` | Next-gen | glibc 2.38+ |

```yaml
# conda-forge.yml — request a newer glibc
os_version:
  linux_64: alma9
```

### Current Compiler Versions (Global Pins)

These are resolved by the `compiler()` macro — never pin manually:

| Platform | C | C++ | Fortran |
|----------|---|-----|---------|
| Linux | GCC 14 | G++ 14 | GFortran 14 |
| macOS | Clang 19 | Clang++ 19 | GFortran 14 |
| Windows | MSVC 2022 | MSVC 2022 | Flang |

**Deprecated**: `compiler_stack` key in `conda-forge.yml` — remove it from any existing feedstock configs.

### Bot Commands (in PR comments)

```
@conda-forge-admin, please rerender
@conda-forge-admin, please restart ci
@conda-forge-admin, please lint
@conda-forge-admin, please close
@conda-forge-admin, please add user @username
```

### Bot Version Update Configuration

```yaml
# conda-forge.yml — exclude erroneous upstream tags
bot:
  automerge: true
  inspection: hint-all
  version_updates:
    exclude:
      - "1.0.0rc1"    # Skip pre-releases the bot incorrectly picks up
```

### Package Immutability

conda-forge packages are **immutable** — versions are never edited or deleted after upload. To fix a broken release:
- Use `conda-forge-admin` to **mark the package as broken** (not deleted)
- Issue a new release with an incremented build number

---

## Manual CLI Commands

| Command | Description |
|---|---|
| `pixi run -e local-recipes health-check` | Full diagnostic on the environment |
| `pixi run -e local-recipes sync-upstream` | Sync fork with `conda-forge/staged-recipes` |
| `pixi run -e local-recipes submit-pr <name>` | Submit a finished recipe to conda-forge |
| `pixi run -e local-recipes autotick <path>` | Manually run the autotick bot on a recipe |
| `pixi run -e local-recipes update-cve-db` | Refresh the local CVE database |
| `pixi run -e local-recipes update-mapping-cache` | Refresh the PyPI name mapping cache |
| `python build-locally.py linux-64` | Build for a specific platform (Docker on Linux) |
| `python build-locally.py --filter 'linux*'` | Build all matching platform configs |
| `pixi run -e conda-smithy lint recipes/<name>` | Lint a recipe with conda-smithy |
| `feedrattler recipes/<name>` | Convert meta.yaml to recipe.yaml manually |

---

## Version History

- **v5.8.0**: Live documentation pass against conda-forge.org + github.com/conda-forge (Apr 2026). Fixed Go compiler names: `compiler("go")` → `compiler("go-nocgo")` in pure-Go templates; `go-cgo` documented as requiring `stdlib("c")`. Updated STD-001 optimizer check to exclude `go-nocgo` + legacy `go` but correctly flag `go-cgo`. Updated SKILL.md Critical Constraints: listed `go-nocgo`/`go-cgo` distinction, deprecated `compiler_stack`. Added `## CI Infrastructure Reference` section: Azure Pipelines is primary (not GitHub Actions — GA is rerendering/automerge only), 6-hour build limit, OS version options (cos7/alma8/alma9/ubi8/alma10/rocky10), current compiler pins (GCC 14, Clang 19), bot version_updates.exclude configuration, immutability policy. Updated `reference/pinning-reference.md` with current global pins table (GCC 14, Clang 19, NumPy 2, CUDA 12.9, OpenSSL 3.5, Boost 1.88, PyTorch 2.9, Arrow 20–23) and fixed GCC version in ci_support example (12 → 14). Updated `config/skill-config.yaml` version to 5.8.0.
- **v5.7.0**: Major content upgrade synthesizing CLAUDE.md + all 21 agent-skills. Added: Operating Principles (Karpathy + using-agent-skills non-negotiables); Critical Constraints section (stdlib, format mixing, python_min floor); Recipe Security Boundaries (Always/Ask First/Never Do); Build Failure Protocol with six-step triage + category table + max-loop rule; Pre-PR Quality Gate Checklist; Migration Protocol (meta.yaml → recipe.yaml Strangler pattern); Python Version Policy (full rules + both format examples); Recipe Formats Quick Reference (complete template examples); enhanced all 9 workflow steps with explicit success criteria; added `check_dependencies` as step 6 (shift-left dep validation); aligned tool table with CLAUDE.md example-usage format.
- **v5.6.0**: Integrated all 21 skills from addyosmani/agent-skills. Added inline cross-references to each workflow step and `## Complementary Skills` lifecycle phase mapping table.
- **v5.5.0**: Standards alignment audit (conda-forge 2025/2026 changes). Fixed `generate_recipe_from_pypi` broken version argument. Fixed SEL-002 optimizer suggestion hardcoded `python_min: "3.9"` → `"3.10"`. Added `migrate_to_v1` MCP tool. Updated pinning reference (Python 3.10–3.14 matrix).
- **v5.4.0**: Documentation audit pass. Updated `check_dependencies` MCP tool with batch repodata.json / JFrog Artifactory docs.
- **v5.3.0**: Added `update_recipe_from_github` MCP tool for GitHub Releases autotick.
- **v5.2.0**: Added `check_github_version` MCP tool. Fixed `recipe_optimizer.py` CFEP-25 `python_min` check (SEL-002).
- **v5.1.0**: Added `submit_pr` MCP tool, completing the full autonomous loop.
- **v5.0.0**: Major architectural overhaul — full suite of autonomous tools, closed-loop build/debug system.
- **v4.2.1**: Removed `stdlib` local testing hack via automatic variant override.
- **v4.0.0**: Initial modular architecture.
