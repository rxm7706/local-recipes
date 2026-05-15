---
name: conda-forge-expert
description: |
  Autonomous conda-forge packaging agent. Manages the entire recipe lifecycle,
  from generation, security scanning, and building to debugging, maintenance,
  and PR submission.

  USE THIS SKILL WHEN: creating or updating conda recipes, fixing conda-forge
  build failures, or performing any task related to conda packaging.
version: 7.0.0
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

### PyPI `source.url` Must Use the `pypi.org/packages/...` Pattern
Recipe `source.url:` for PyPI artifacts **must** route through `https://pypi.org/packages/...`, never `https://files.pythonhosted.org/packages/<hash>/...`. The hashed `files.pythonhosted.org` URL is what PyPI's JSON API returns and what `grayskull` historically emitted, but it bypasses standard JFrog Artifactory PyPI Remote Repository proxies in air-gapped corporate environments.

**Sdist (preferred):**
```yaml
source:
  url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
```
For sdist filenames that use underscores instead of hyphens (e.g. `litellm_proxy_extras-0.4.69.tar.gz` for project `litellm-proxy-extras`), hard-code the underscore form:
```yaml
  url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/litellm_proxy_extras-${{ version }}.tar.gz
```

**Wheel (only when no sdist exists upstream):**
```yaml
source:
  url: https://pypi.org/packages/${{ py_tag }}/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}-${{ py_tag }}-none-any.whl
```
where `${{ py_tag }}` is the wheel's Python tag (`py3`, `py2.py3`, `cp310`, …). The `<py-tag>` segment is upstream-specific and may change on a version bump — flag this with a recipe comment.

The `recipe-generator.py` script emits these patterns automatically from the upstream filename; manual edits and recipe reviews must enforce the same form. See `docs/enterprise-deployment.md` §3 for the full proxy rationale.

### `build.bat` Must `call` Every `.cmd` Shim (pnpm/npm/yarn)
On Windows, `pnpm`, `npm`, `yarn`, `npx`, and similar tools ship as `.cmd` wrappers. Invoking a `.cmd` from a `.bat` **without `call`** causes cmd.exe to **transfer control** to the shim — when it returns, the parent script terminates with exit 0 instead of continuing. The build appears to succeed but later steps never run, and rattler-build emits misleading errors like `× No license files were copied`.

```bat
:: WRONG — script silently terminates after pnpm returns
pnpm --version || exit /b 1
cargo --version || exit /b 1   :: never runs

:: RIGHT — `call` recurses and returns control to the parent
call pnpm --version
if errorlevel 1 exit /b 1
cargo --version
if errorlevel 1 exit /b 1
```

`call` is harmless on real `.exe` (`node.exe`, `cargo.exe`, `rustc.exe`); when in doubt, add it. See `guides/ci-troubleshooting.md` § "Silent build.bat Termination".

---

## Primary Workflow: The Autonomous Loop

When asked to create or update a recipe, execute these steps in order. Each step has a success criterion — do not advance until it is met.

1.  **Generate Recipe** — `generate_recipe_from_pypi(package_name="<name>")`
    - Success: `recipe.yaml` created in `recipes/<name>/`
    - Before calling: surface assumptions (pure Python? noarch? license compatible?)
    - > *Skills: [`spec-driven-development`] — define requirements and "Not Doing" list; [`source-driven-development`] — verify PyPI metadata against official docs; [`idea-refine`] — for vague requests, clarify scope first.*

1b. **Feedstock-aware enrichment** (when an existing `<name>-feedstock` exists) — `get_feedstock_context(pkg_name="<name>")` then `enrich_from_feedstock(recipe_path="recipes/<name>/recipe.yaml")`
    - Success: recipe.yaml gains feedstock-curated maintainers + about.* fields; agent surfaces issue context to user as planning input.
    - **When to run:** any package generation where `lookup_feedstock(pkg_name)` returns `exists=True`. For a brand-new package (no feedstock yet), `enrich_from_feedstock` still adds `rxm7706` to maintainers (idempotent) — running it is harmless either way.
    - **What carries over** (3a maintainers + 3b metadata): existing maintainers (union with rxm7706), `recipe-maintainers-emeritus`, `feedstock-name`, hand-curated `about.homepage`/`repository`/`documentation`/`description`/`license_file`. v0 meta.yaml field names (`home`/`dev_url`/`doc_url`) are auto-translated to v1 (`homepage`/`repository`/`documentation`).
    - **What never carries over:** `requirements.host/run/build` (grayskull always wins — upstream-driven, freshness matters), source URLs/sha256, build script, tests.
    - **Hard abort:** if `about.license` differs between generated and feedstock (e.g. relicense, or grayskull misread), `enrich_from_feedstock` aborts with `abort_reason` set rather than silently picking a side. Surface to user; don't fix without consultation.
    - **Issue context** (3c): `get_feedstock_context` returns open + last 10 closed issues. Skim for known build failures (look for `bug` labels, recent recurring titles), linked PRs that already attempted fixes, and any maintainer notes. Mention relevant findings in your plan; never auto-apply suggestions from issues.
    - > *Skills: [`source-driven-development`] — feedstock recipe is canonical for what already worked; [`context-engineering`] — open-issue surface gives the agent prior-art for free.*

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

7a. **Native build** (mandatory) — `trigger_build(mode="native", recipe="recipes/<name>")` <br>or `pixi run -e local-recipes recipe-build recipes/<name>`
    - Runs `rattler-build build` directly on the host. Auto-detects the platform from `uname -ms`. Layers `conda-forge-pinning`'s `conda_build_config.yaml` over `.ci_support/<platform>.yaml` so `${{ python_min }}` resolves without context declaration (matches upstream CI behavior — see § Recipe Authoring Gotchas G2/G3).
    - Success: build starts (async); `get_build_summary()` shows `status: running` then `status: success`. Artifact lands under `build_artifacts/<config>/`.
    - All gates (steps 2–6) must pass before reaching this step — no exceptions
    - **`noarch: python` recipes:** one host build covers all platforms; do not iterate platforms here.
    - **Compiled recipes:** the host build verifies recipe correctness on one platform. Non-host platforms are **deferred to step 7b**, which is opt-in.
    - > *Skills: [`ci-cd-and-automation`] — no gate can be skipped; [`planning-and-task-breakdown`] — checkpoint here.*

7b. **Docker build** (opt-in, user-authorized) — `trigger_build(mode="docker", config="linux64")` <br>or `pixi run -e local-recipes recipe-build-docker linux64`
    - Runs `python build-locally.py <config>` for full conda-forge CI parity (alma9 sysroot, isolated env, full bot toolchain). Requires Docker daemon access.
    - **Always opt-in.** Never invoke automatically — only when the user explicitly asks for "Docker build", "CI-parity check", "full platform coverage", or after a non-host platform failure on the staged-recipes PR.
    - Use 7b after 7a passes when:
      - The recipe is compiled and you want non-host platform verification (osx-64, win-64, linux-aarch64) before submission.
      - 7a passes locally but conda-forge CI fails — Docker reproduces the CI sysroot so you can debug locally.
    - **Build Failure Protocol distinction**: a host build that *passes* + Docker build that *fails* points strongly at sysroot/CDT mismatch (the host's glibc differs from cos7/alma9). The host build that *fails* points at the recipe itself; fix the recipe first before invoking 7b.

8.  **Monitor Build** — poll `get_build_summary()` until `status` is `success` or `failed`
    - Success: `status: success`
    - If `status: failed`: proceed to [Build Failure Protocol](#build-failure-protocol)
    - **False-negative caveat**: `get_build_summary` occasionally returns `status: "unknown"` with the message `"No build summary found — build may have crashed"` even when the build actually succeeded — its summary-file detection is brittle. **Before trusting "crashed," check `build_artifacts/<config>/<subdir>/` for `<name>-<version>-*.conda` files; if they exist with mtime newer than the build start, the build succeeded.** For deeper diagnosis, the per-build log lives at `build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log`.
    - > *Skills: [`ci-cd-and-automation`] — a failed build blocks the pipeline; fix before proceeding.*

8b. **Prepare Submission Branch** — `prepare_submission_branch(recipe_name="<name>", dry_run=True)` → verify → `prepare_submission_branch(recipe_name="<name>")`
    - Success: `fork_branch_url` returned; branch `add-recipe-<name>` exists on `<your-user>/staged-recipes` with the recipe committed; **no PR yet**
    - This is the **inspection checkpoint** between a green local build and the PR. Open `fork_branch_url` in a browser, run `gh pr diff` against an imagined PR, or pull the fork locally and review the diff before authorizing step 9.
    - Idempotent — if the remote branch's tree already matches the local HEAD, the push is skipped (`pushed: false` in the result). Force-push uses `--force-with-lease` so a divergent remote errors instead of being clobbered. The result also reports `synced_commits` (how many commits the fork's main was behind upstream — useful drift signal).
    - **Skip when**: you're submitting via `submit_pr` end-to-end and don't need an inspection point (e.g., a trivial recipe re-submission). `submit_pr` calls this internally; running it standalone first is the human-in-the-loop variant.
    - **Optional add-on**: drop a `conda-forge.yml` next to `recipe.yaml` to override staged-recipes defaults for this recipe. The most common opt-ins: `azure: { store_build_artifacts: true }` (Azure saves built `.conda` files as downloadable pipeline artifacts; default is `false`), `os_version: { linux_64: alma9 }` (newer glibc), and `noarch_platforms` (extra CI matrix for noarch:python). Full reference: [`reference/conda-forge-yml-reference.md`](reference/conda-forge-yml-reference.md). Starter template: [`templates/conda-forge-yml/staged-recipes/conda-forge.yml`](templates/conda-forge-yml/staged-recipes/conda-forge.yml).
    - > *Skills: [`shipping-and-launch`] — staged rollout; [`git-workflow-and-versioning`] — branch-then-PR pattern.*

9.  **Submit PR** — `submit_pr(recipe_name="<name>", dry_run=True)` → verify → `submit_pr(recipe_name="<name>")`
    - Success: `pr_url` returned; PR opens on conda-forge/staged-recipes
    - Run `dry_run=True` first — it checks `gh auth`, fork presence, and branch state
    - When step 8b already pushed the branch, `submit_pr`'s prep phase no-ops (idempotency check) and proceeds straight to opening the PR
    - If PR creation fails after a successful push, the result includes `branch` + `fork_branch_url` + a `hint` to retry just the PR step — no need to re-push
    - See [Pre-PR Quality Gate Checklist](#pre-pr-quality-gate-checklist) before calling
    - > *Skills: [`shipping-and-launch`] — complete pre-submit checklist; [`git-workflow-and-versioning`] — atomic commit (`feat: add <name> recipe`); [`documentation-and-adrs`] — PR description must explain WHY.*

---

## Atlas Intelligence Layer (v8.1.0)

The skill carries a SQLite-backed cross-channel package map at
`.claude/data/conda-forge-expert/cf_atlas.db`, populated by 15 pipeline
phases (B → N) and exposed through 17 CLIs + 12 MCP tools. The atlas is
**offline-safe** for all read paths once built; only Phase G's *fresh*
vuln data needs the heavy `vuln-db` env (cached counts work everywhere).

Schema v21 (v8.0.0) ships a `v_actionable_packages` view encoding the
canonical persona-filter triplet `conda_name IS NOT NULL AND
latest_status='active' AND COALESCE(feedstock_archived,0)=0`. Seven
phase selectors read from the view, and a structural-enforcement
meta-test (`tests/meta/test_actionable_scope.py`) prevents future drift.
Phase H's eligible-rows gate is also serial-aware in v21 — warm-daily
Phase H drops from ~5 min to ~30 s on a typical day.

### Build the atlas

```bash
# Recommended (v8.0.0+) — persona-aware preset bundle. `maintainer` is
# the documented default for the most common operator.
pixi run -e local-recipes bootstrap-data --profile maintainer
pixi run -e local-recipes bootstrap-data --profile admin      # channel-wide
pixi run -e local-recipes bootstrap-data --profile consumer   # air-gapped

# Legacy invocations still work (explicit env wins over profile):
pixi run -e local-recipes build-cf-atlas             # default phases
PHASE_E_ENABLED=1 pixi run -e local-recipes build-cf-atlas  # incl. cf-graph
PHASE_N_ENABLED=1 PHASE_N_MAINTAINER=rxm7706 ...     # add live GitHub data
```

See `reference/atlas-phases-overview.md` § "Profile Reference (v8.0.0)"
for the full per-phase profile matrix and auto-detection details.

### Daily-use CLIs (all offline; all support `--json`)

| CLI | What it answers |
|---|---|
| `detail-cf-atlas <pkg>` | Full health card — version, downloads, vulns, upstream comparison, deps, bot/CI/issue status |
| `staleness-report [--maintainer X] [--by-risk] [--has-vulns] [--bot-stuck]` | Triage queue: stalest / riskiest / stuck-bot feedstocks |
| `feedstock-health [--filter stuck\|bad\|open-pr\|ci-red\|open-issues\|open-prs-human\|all]` | Maintenance dashboard |
| `whodepends <pkg> [--reverse] [--type build\|host\|run\|test]` | Dependency graph queries (Phase J) |
| `behind-upstream [--maintainer X]` | Multi-source upstream-of-record comparison |
| `cve-watcher [--since-days N] [--severity C\|H\|K\|T]` | CVE-count delta vs prior snapshot |
| `version-downloads <pkg> [--by-downloads]` | Per-version adoption (Phase I) |
| `release-cadence [--package <pkg>] [--maintainer X]` | Trend classifier (accelerating/stable/decelerating/silent) |
| `find-alternative <archived-pkg>` | Suggest healthier replacements |
| `adoption-stage [--package <pkg>] [--maintainer X]` | Lifecycle classifier (bleeding-edge/stable/mature/declining/silent) |
| `scan-project [PATH \| --image <ref> \| --sbom-in <file> \| --conda-env <path> \| --venv <path> \| --helm-chart <path> \| --kustomize <dir> \| --argo-app <file> \| --flux-cr <file>] [--license-check] [--sbom cyclonedx]` | Unified scanner — manifests, container images, SBOMs (8+ formats), live envs, GitOps |

### MCP exposure

All twelve atlas read-tools are wrapped as MCP tools in
`.claude/tools/conda_forge_server.py` — see
`reference/mcp-tools.md` for the full index and selection cheatsheet.

### When to invoke the atlas

The atlas exists to answer "what should I work on?" / "is this safe?" /
"what depends on this?" — questions the per-recipe authoring workflow
can't easily answer. Recommended triggers:

- **Quarterly maintainer review**: `staleness-report --maintainer X --by-risk`
- **Before merging a bot PR**: `whodepends <pkg> --reverse` to see blast radius
- **CVE response**: `cve-watcher --maintainer X --severity C --only-increases`
- **Deciding to archive**: combine `adoption-stage` + `find-alternative` to confirm
  there's a viable migration path
- **Pre-deployment scan**: `scan-project --image <prod-image>` or
  `scan-project --sbom-in <cyclonedx.json>` for env audits

### Persona-mapped catalog

Full reference: `reference/atlas-actionable-intelligence.md`
— every shipped signal mapped to (persona, goal, action, outcome). For
the phase-indexed companion (data source / purpose / actionable
intelligence per pipeline stage), see
`reference/atlas-phases-overview.md`.

### Format coverage for `scan-project`

Full reference: `reference/dependency-input-formats.md` — comprehensive
support matrix for ~30 input formats (manifests, lock files, SBOMs,
container images, live envs, GitOps).

### Phase engineering patterns

Full reference: `reference/atlas-phase-engineering.md` — default rule
book for writing or refactoring `conda_forge_atlas.py` pipeline phases.
Nine sections covering per-host secondary rate limits, GraphQL batching
vs REST fanout, `Retry-After` parsing with hard cap + ±25% jitter,
per-registry concurrency caps, atomic file writes, incremental commits
with idempotent SQL, streaming tarfiles from disk, page-level
checkpoints via `save_phase_checkpoint`, and the `<HOST>_BASE_URL`
enterprise-routing convention. Consult before adding a new phase or
touching HTTP fanout / batch writes / cache IO in an existing one.

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
- [ ] `prepare_submission_branch(dry_run=True)` passes; then real call lands branch on `<your-user>/staged-recipes` and `fork_branch_url` was inspected
- [ ] (Optional) per-recipe `conda-forge.yml` ships `azure.store_build_artifacts: true` if you want the upstream PR's Azure run to retain downloadable `.conda` artifacts
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
6. **Recipes do NOT need `python_min` in context unless overriding the default** — the May 2026 upstream sync removed `python_min: '3.10'` and `python: 3.12.* *_cpython` from `.ci_support/linux64.yaml` and `linux_aarch64.yaml`, but those defaults still come from **`conda-forge-pinning`** (the canonical source upstream CI has always used). Recipes at the default `3.10` floor can — and should — write `${{ python_min }}` references throughout the CFEP-25 triad **without** declaring `python_min` in `context:`. Only override in `context:` when upstream `python_requires` demands a higher floor.

   **Local rattler-build implication.** When invoking rattler-build directly (outside conda-forge CI), pass conda-forge-pinning as an additional variant config so `${{ python_min }}` resolves to its default:

   ```bash
   pixi run -e local-recipes rattler-build build \
     --recipe recipes/<name>/recipe.yaml \
     --variant-config .ci_support/linux64.yaml \
     --variant-config .pixi/envs/local-recipes/conda_build_config.yaml
   ```

   The `local-recipes` pixi env already installs `conda-forge-pinning`; its `conda_build_config.yaml` lands at `.pixi/envs/local-recipes/conda_build_config.yaml`. Without the second `--variant-config`, recipes referencing `${{ python_min }}` will fail to render with `Template rendering failed: undefined value`.

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
| `generate_recipe_from_pypi` | Creates a new recipe from a PyPI package via grayskull, with conda-forge post-processing (rewrites `tests[].python.python_version` to the `[python_min, "*"]` list form per [staged-recipes#32857 r3039190932](https://github.com/conda-forge/staged-recipes/pull/32857#discussion_r3039190932)) | `generate_recipe_from_pypi(package_name="numpy")` |
| `generate_recipe_from_npm` | **Canonical npm pattern** (npm pack + npm install --global + pnpm-licenses). Handles scoped packages (`@openai/codex` → conda name `codex`). Flags: `--source-mode {npm,github,auto}`, `--prepare-fix`, `--test-mode`, `--inline-build`, `--with-build-bat`, `--no-bin-links`, `--no-third-party-licenses`, `--validate`. Pixi: `pixi run -e local-recipes generate-npm -- husky` | `recipe-generator.py npm husky` |
| `generate_recipe_from_cran` | R package from CRAN via rattler-build | `recipe-generator.py cran ggplot2` |
| `generate_recipe_from_cpan` | Perl package from CPAN via rattler-build | `recipe-generator.py cpan Moose` |
| `generate_recipe_from_luarocks` | Lua package via rattler-build | `recipe-generator.py luarocks lua-cjson` |
| `edit_recipe` | **Primary editing tool.** Structured actions: update, add, remove. Never edit YAML directly. | `edit_recipe('recipes/numpy/recipe.yaml', [{"action": "update", "path": "context.version", "value": "2.0.0"}])` |
| `get_conda_name` | Resolves a PyPI package name to its conda-forge equivalent (cache-first) | `get_conda_name(pypi_name="python-dateutil")` |

### Validation & Quality
| Tool | Description | Example |
|---|---|---|
| `validate_recipe` | Schema, license, checksums + `rattler-build lint` pass | `validate_recipe(recipe_path="recipes/numpy")` |
| `check_dependencies` | Verifies all deps exist on conda-forge. Batch repodata.json — fast, air-gapped-friendly, JFrog Artifactory-compatible | `check_dependencies(recipe_path="recipes/numpy")` |
| `optimize_recipe` | 16 check codes — **critical** (STD-001: compiler without stdlib; STD-002: format mixing), **security** (SEC-001: no sha256), **completeness** (MAINT-001: no maintainers; TEST-001: no tests; TEST-002: noarch:python tests pinned to a single Python version instead of `[python_min, "*"]` ([staged-recipes#32857 r3039190932](https://github.com/conda-forge/staged-recipes/pull/32857#discussion_r3039190932)); ABT-001: no license_file; ABT-002: v0 about-fields in v1 recipe), **quality** (DEP-001/002, PIN-001, SCRIPT-001/002, SEL-001/002/003) | `optimize_recipe(recipe_path="recipes/numpy")` |

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
| `update_recipe_from_npm` | **Autotick Bot (npm).** Auto-detects the npm name from `source.url`; handles scoped packages; skips pre-releases by default. Pixi: `pixi run -e local-recipes autotick-npm -- recipes/husky --dry-run` | `npm_updater.py recipes/husky --dry-run` |
| `check_github_version` | Read-only GitHub version check — returns latest tag without modifying | `check_github_version(recipe_path="recipes/apple-fm-sdk")` |
| `update_mapping_cache` | Updates PyPI-to-Conda name mapping cache from Grayskull. Run when `get_conda_name` misses | `update_mapping_cache(force=True)` |
| `migrate_to_v1` | **meta.yaml → recipe.yaml.** Converts v0 to v1 via feedrattler. Preserves original. | `migrate_to_v1(recipe_path="recipes/numpy")` |
| `prepare_submission_branch` | **Step 8b.** Stage the recipe on a branch in your staged-recipes fork — no PR yet. Idempotent (`--force-with-lease`); reports `synced_commits` (fork drift). Use as inspection checkpoint before authorizing `submit_pr`. | `prepare_submission_branch(recipe_name="numpy", dry_run=True)` |
| `submit_pr` | **Step 9.** Calls `prepare_submission_branch` then opens the PR against conda-forge/staged-recipes. Idempotent prep — when step 8b already pushed, the prep no-ops and only the PR is created. Always `dry_run=True` first. | `submit_pr(recipe_name="numpy", dry_run=True)` |
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

*Sourced from conda-forge.org/docs/maintainer/infrastructure/ and conda-forge news (Apr 2026).*

### Platform Assignments

| Platform | Default CI Provider | Notes |
|----------|---------------------|-------|
| Linux x86_64 | **Azure Pipelines** | Default; opt-in to GitHub Actions via conda-smithy 3.57.1+ (March 2026) |
| Linux aarch64 (ARM) | Azure Pipelines (emulated) | Cirun for native runners on selected feedstocks |
| Linux ppc64le (Power8+) | Azure Pipelines (emulated) | |
| macOS x86_64 / arm64 | Azure Pipelines | GitHub Actions not yet available |
| Windows x86_64 | Azure Pipelines | GitHub Actions not yet available |
| Windows ARM64 | Azure Pipelines | Python 3.14 cross-builds added 2025 |
| Rerendering / automerge | **GitHub Actions** | Always — CI config updates and bot services |

**GitHub Actions for Linux builds (opt-in, Mar 8, 2026)**: rerender after upgrading to conda-smithy ≥ 3.57.1 and set the provider in `conda-forge.yml`:

```yaml
# conda-forge.yml — opt the Linux native build into GitHub Actions
provider:
  linux_64: github_actions
```

Use this only when Azure capacity is constrained or your build needs the larger GA concurrency limits. Windows and macOS builds remain on Azure.

**Build time limit**: 6 hours on Azure Pipelines (and matching limits on GitHub Actions). Builds exceeding this are killed with no artifacts.

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

### Community Channels

| Channel | Status | Use For |
|---------|--------|---------|
| **Zulip** (`conda-forge.zulipchat.com`) | **Primary** | Real-time questions, troubleshooting, announcements |
| GitHub Discussions / Issues | Active | Recipe bugs, feedstock-specific issues |
| Discourse (`conda.discourse.group`) | **Read-only** since Oct 15, 2025 | Search archive only — do not post |
| Gitter | Decommissioned | Replaced by Zulip |

When asking for help, link the failing PR/feedstock and the rendered build log — never paste large logs into chat.

---

## Ecosystem Updates (May 2026)

Recent conda-forge changes that affect recipe authoring. Cite the relevant entry in PR descriptions when applying these patterns.

### Build Tooling
- **rattler-build v0.64.1 (May 4, 2026)** — Sharded repodata 501-error handling. Bug fix only.
- **rattler-build v0.64.0 (Apr 28, 2026)** — Experimental V3 packages behind `--v3` flag: optional dependency `extras:` groups, `when:` conditional dependencies (e.g. `scipy [when="python>=3.10"]`), and variant-selection `flags:`. **Opt-in only**; recipes without `--v3` are unaffected.
- **rattler-build v0.63.0 (Apr 22, 2026)** — Multi-output recipes no longer auto-discover per-output `build.sh`/`build.bat`. Each output that needs a script must declare `script: <name>` explicitly. Top-level (single-output) recipes are unchanged.
- **rattler-build v0.62.0 (Apr 13, 2026)** — Three-mode `--env-isolation` flag: `strict` (default; remaps `$HOME`), `conda-build`, `none`. Build scripts that rely on inherited env vars must declare them in `build.script.env`.
- **rattler-build v0.61.0 (Mar 19, 2026)** — `--debug` flag removed; use the dedicated `rattler-build debug` subcommand.

### Platform & Toolchain
- **macOS minimum is 11.0** (Feb 2026). `MACOSX_DEPLOYMENT_TARGET=10.x` builds will be rejected.
- **macOS SDK directory**: `/opt/conda-sdks` since conda-smithy 3.54.0 (Dec 2025). Local builders must export `OSX_SDK_DIR=/opt/conda-sdks`.
- **macOS Accelerate Framework** (Jul 2025) — new BLAS/LAPACK provider on macOS 13.3+ via shim library; switch with `conda install libblas=*=*_newaccelerate`.
- **CUDA matrix** — active variants are **12.9** and **13.0** as of May 2026. CUDA 11.8 was removed Jun 2025; the previous opt-back instruction (copy `cuda118.yaml` to `.ci_support/migrations/`) **no longer works** — that file was removed from staged-recipes upstream. New explicit per-CUDA variant configs landed: `.ci_support/linux64_cuda129.yaml` + `linux64_cuda130.yaml`. NVIDIA Tegra (linux-aarch64 SOC) builds are supported on CUDA 12.9; CUDA 13.0+ uses SBSA so Tegra-specific builds are unnecessary.
- **`osx-arm64` is now a first-class variant** (May 2026) — new `.ci_support/osx_arm64.yaml` exists alongside `osx_64.yaml`. Use `target_platform: osx-arm64` in recipes that need explicit ARM Mac handling. macOS deployment target remains 11.0.
- **MPI external label** (Jan 29, 2026) — external MPI builds were moved to `conda-forge/label/mpi-external`. Old external MPI packages on `main` were marked broken.

### Policy
- **CFEP-25** — `python_min` floor for `noarch: python` recipes; conda-forge floor is `"3.10"` since Aug 2025 (Python 3.9 dropped).
- **CFEP-26** — Guidelines for (re)naming packages (newly accepted). Consult before renaming a package or filing a name dispute.
- **License identifiers must be SPDX** — case-sensitive (e.g., `Apache-2.0`, not `APACHE 2.0`); compound licenses use SPDX expressions (`Apache-2.0 WITH LLVM-exception`).
- **Bundled-language licensing** (Rust, Go) — use `cargo-bundle-licenses` / `go-licenses` and ship a `THIRDPARTY.yml` alongside `LICENSE` (already encoded in the maturin and Go templates).

---

## Recipe Authoring Gotchas

Patterns that look right but fail silently or produce broken recipes. Each entry includes the symptom, why it happens, and the correct form. Case studies cited where relevant.

### G1. `script:` list entries run in separate shells — env vars do NOT carry across entries

**Symptom**: an `export FOO=bar` in one script entry has no effect in the next entry. `pip install` later in the script doesn't see `CFLAGS` you set earlier.

**Why**: rattler-build evaluates each top-level item under `build.script:` (when given as a YAML list) as an independent shell invocation. Shell state — env vars, `cd`, function definitions — does not survive between entries.

**Fix**: choose one of three patterns:

```yaml
# (a) Single multi-line entry — exports persist into the same shell
build:
  script:
    - if: unix
      then: |
        export CFLAGS="${CFLAGS:-} -D_BSD_SOURCE -D_DEFAULT_SOURCE"
        cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
        ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```

```yaml
# (b) script.env: static map — works when the value is fixed (no shell expansion)
build:
  script:
    env:
      CARGO_PROFILE_RELEASE_STRIP: symbols
      CARGO_PROFILE_RELEASE_LTO: fat
    content:
      - cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
      - ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```

```yaml
# (c) Dedicated build.sh / build.bat — for complex logic
build:
  script:
    file: build.sh        # relative to recipe directory
```

**`script.env:` does NOT shell-expand `${VAR}`** — values are treated as literal strings. To append to an existing env var, use pattern (a) or (c).

**Case study**: cocoindex PR #33231 (May 2026). The recipe needed `CFLAGS=-D_BSD_SOURCE -D_DEFAULT_SOURCE` to compile tree-sitter under GCC 14 + glibc 2.17 sysroot (`le16toh`/`be16toh` implicit declaration). First attempt put `export` in a separate script entry; it did not reach `pip install`. Fixed by collapsing into one multi-line `then: |` block.

### G2. v0/meta.yaml field names in v1 recipe.yaml are silently ignored

**Symptom**: rattler-build builds the package without warning, but `about.dev_url`, `about.doc_url`, `about.home`, or `about.license_family` is missing from the resulting metadata. Users see incomplete project links on conda-forge.org.

**Why**: rattler-build's recipe-format schema only recognizes the v1 names (`repository`, `documentation`, `homepage`). Unknown keys under `about:` are accepted but discarded — no schema-validation error.

**Fix**: use the v1 names in any file with `schema_version: 1`. Reference: `reference/recipe-yaml-reference.md` and the [v0 ↔ v1 about-field mapping memory](../../memory/reference_v0_v1_about_fields.md). The optimizer's **ABT-002** check flags this in v1 recipes.

| v0 (meta.yaml) | v1 (recipe.yaml) |
|---|---|
| `home` | `homepage` |
| `dev_url` | `repository` |
| `doc_url` | `documentation` |
| `license_family` | *(removed; no replacement)* |

### G3. `py < N` skip selectors do nothing in v1 recipe.yaml

**Symptom**: `build.skip: - py < 311` is in the recipe, but conda-forge CI builds Python 3.10 anyway and pip rejects with `requires a different Python: 3.10.X not in '>=3.11'`.

**Why**: `py < N` is conda-build/meta.yaml v0 selector syntax. rattler-build does not auto-inject the integer `py` variable from the `python` variant string in staged-recipes-style builds, so the condition evaluates against an undefined symbol and never fires.

**Fix**: use `match(python, "<3.11")`. The optimizer's **SEL-003** check flags v0-style `py < N` in v1 recipes.

```yaml
build:
  skip:
    - match(python, "<3.11")     # CORRECT in v1
    # - py < 311                 # WRONG — silently ignored
```

**Case study**: cocoindex PR #33231 (May 2026). All three platform builds (linux/osx/win) failed because `py < 311` did not skip the Python 3.10 matrix entry.

### G4. Sdist may omit LICENSE — `pip install` succeeds, build fails with "No license files were copied"

**Symptom**: `validate_recipe` and the Rust/wheel build both succeed, but rattler-build then fails at `Copying license files` with `No license files were copied`. The PyPI sdist has no `LICENSE` file at the root.

**Why**: PEP 517 sdists are not required to include a LICENSE. Some build backends (notably maturin, hatchling with non-default config) emit metadata-rich sdists that ship `THIRD_PARTY_NOTICES.html` or similar, but not the project's own LICENSE. conda-forge requires the LICENSE to be packaged.

**Fix**: add a secondary `source:` block fetching the LICENSE from the upstream GitHub tag. See [`guides/sdist-missing-license.md`](guides/sdist-missing-license.md) for the full pattern.

```yaml
source:
  - url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
    sha256: <sdist hash>
  - url: https://raw.githubusercontent.com/<org>/<repo>/v${{ version }}/LICENSE
    sha256: <license hash>
    file_name: LICENSE
```

**Case study**: cocoindex PR #33231 (May 2026). cocoindex's PyPI sdist shipped only `THIRD_PARTY_NOTICES.html`. Fix added a secondary `source:` from `raw.githubusercontent.com`.

### G5. tree-sitter PyPI sdists inconsistently strip `src/tree_sitter/*.h` headers — default to GitHub source

**Symptom**: native build of a `tree-sitter-<lang>` recipe sourced from the PyPI sdist fails at the very first compile step with:

```
src/parser.c:1:10: fatal error: tree_sitter/parser.h: No such file or directory
    1 | #include "tree_sitter/parser.h"
      |          ^~~~~~~~~~~~~~~~~~~~~~
```

The recipe is otherwise correct — `compiler('c')` + `stdlib('c')` are present, `pip install .` reaches the `build_ext` stage, and `grayskull` happily produced the recipe from the sdist.

**Why**: many `tree-sitter-grammars/*` and `tree-sitter/*` Python bindings **ship `src/tree_sitter/parser.h`, `array.h`, and `alloc.h` in the GitHub tag tarball but omit them from the PyPI sdist** that their upstream wheel-build pipeline uploads. The wheels published to PyPI work because the headers are in the build container's filesystem; the sdist on its own cannot compile.

The omission is **per-release inconsistent** — not a clean version-based cutoff. In staged-recipes PR #33308 (May 2026) the bug hit 8 of 11 PyPI-sourced recipes (v0.23.1, v0.23.2, v0.23.4, v0.23.5, v0.24.2, v0.26.0, v1.1.0, v1.2.0) while three PyPI sources at v0.25.0 and v0.7.2 happened to ship the headers. Don't trust the version; trust the listing.

**Fix**: default `tree-sitter-<lang>` recipes to GitHub-tag source rather than PyPI sdist. This matches the conda-forge `tree-sitter-python-feedstock` pattern and avoids the entire class of bug:

```yaml
# tree-sitter PyPI sdists inconsistently strip src/tree_sitter/*.h headers
# needed for the C build; default to the GitHub tag (see SKILL.md G5).
source:
  url: https://github.com/<org>/${{ name }}/archive/refs/tags/v${{ version }}.tar.gz
  sha256: <sha256 of the GitHub tarball>
```

Common upstream orgs: `tree-sitter` (most grammars), `tree-sitter-grammars` (community-maintained: kotlin, luau, ...), `alex-pinkus` (swift), other forks. Confirm by checking the package's `Project URLs` / `Homepage` on PyPI.

**How to verify before trusting `generate_recipe_from_pypi`**: list the sdist contents (`tar tzf <sdist>.tar.gz | grep 'tree_sitter/parser.h'`). If the listing is empty, switch to GitHub source.

**Case study**: staged-recipes PR #33308 (May 2026) — 12-recipe bundle for `repowise` prerequisites. First-pass build had 7 PyPI-sourced recipes fail with this exact error (cpp 0.23.4, java 0.23.5, typescript 0.23.2, ruby 0.23.1, rust 0.24.2, scala 0.26.0, plus luau and kotlin proactively switched ahead of time). All resolved by switching to GitHub source. Three other PyPI sources passed (go 0.25.0, javascript 0.25.0, swift 0.7.2). The same-bundle tree-sitter-php had a *different* issue — its GitHub source pyproject.toml had `license = "LICENSE"`, which modern setuptools rejects as an invalid SPDX identifier; fixed via a downstream `0001-fix-invalid-pep621-license-field.patch` in the recipe's `patches/` directory that rewrites the line to `license = "MIT"`.

---

## Skill Automation

A quarterly live-doc audit keeps this skill aligned with upstream conda-forge changes. It runs as a remote Claude Code routine (registered at `claude.ai/code/routines`) but the prompt and runner are committed under [`automation/`](automation/) so the job is reproducible from this repo.

| | |
|---|---|
| Routine ID | `trig_015z9XF8ExDJuN9qsZYGYKcu` |
| Cron | `0 14 1 */3 *` — Jan/Apr/Jul/Oct 1, 14:00 UTC (= 9am Chicago in CDT) |
| Repo | `rxm7706/local-recipes` |
| Prompt | [`automation/quarterly-audit.prompt.md`](automation/quarterly-audit.prompt.md) |
| Local runner | [`automation/run-audit-local.sh`](automation/run-audit-local.sh) |
| Manage | https://claude.ai/code/routines/trig_015z9XF8ExDJuN9qsZYGYKcu |

To run an off-cycle audit locally: `.claude/skills/conda-forge-expert/automation/run-audit-local.sh`. See [`automation/README.md`](automation/README.md) for cron / systemd scheduling and instructions to recreate the remote routine if it's ever deleted.

---

## Manual CLI Commands

| Command | Description |
|---|---|
| `pixi run -e local-recipes health-check` | Full diagnostic on the environment |
| `pixi run -e local-recipes sync-upstream-conda-forge` | Sync fork with `conda-forge/staged-recipes` |
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

- **v8.1.0** (May 15, 2026): PyPI intelligence layer — 5 new pipeline phases (O/P/Q/R/S) + new `pypi-intelligence` CLI + MCP tool + persona-profile integration. Architecture preserves `pypi_universe` as reference-data only (3 columns); all enrichment lands in a new `pypi_intelligence` side table (35 columns across 5 tiers) joined on `pypi_name`. Schema v22 adds `pypi_intelligence`, `pypi_universe_serial_snapshots` (90-day rolling history), and `v_pypi_candidates` view. **Phase O** ships activity_band classification from daily snapshot deltas (no HTTP; default-on under maintainer/admin profiles); **Phase P** adds BigQuery `pypi.file_downloads` ingest for 30/90-day download counts (opt-in admin-tier; needs `google-cloud-bigquery` + `GOOGLE_APPLICATION_CREDENTIALS`); **Phase Q** adds cross-channel `in_<channel>` BOOLs from bulk repodata for bioconda/pytorch/nvidia/robostack (homebrew/nixpkgs/spack/debian/fedora columns exist but bulk-index implementations deferred to v8.2.0); **Phase R** ships per-project `pypi.org/pypi/<name>/json` enrichment bounded to top-N candidate slice (default 5000) with deterministic `_classify_packaging_shape` (pure-python/cython/c-extension/rust-pyo3/unknown) + `_normalize_license_to_spdx`; **Phase S** computes `conda_forge_readiness` (0-100 composite via 6-component weighted formula) + `recommended_template` (full template path for direct conda-forge-expert invocation). Persona profile integration: admin enables all 5; maintainer enables O+Q only (no BQ/JSON-fetch cost); consumer enables O only (air-gap preserved). New `pypi-intelligence` CLI surfaces ranked candidates with rich filters (`--score-min`, `--activity`, `--license-ok`, `--noarch-python-candidate`, `--in-bioconda`, `--sort-by score|downloads|serial`); wrapped as `pypi_intelligence` MCP tool. **All 8 spec open questions pre-resolved before BMAD intake**: notes column added for operator overrides; project-level BQ aggregation only; full-path recommended_template; URL-pointer heuristic for non-PyPI ecosystems; staged-recipes fallback chain; 90 d snapshot retention; raw-weight readiness scoring; PRD v1.2.0 → v1.3.0 (MINOR additive). 51 new unit tests (10 Phase O + 16 Phase P/Q + 18 Phase R + 13 Phase S + 10 CLI + meta-test SCRIPTS update). Suite: 1,064 passing. Two-PR ship: PR #1 = Waves A+B (schema + reference-data enrichment); PR #2 = Waves C+D+E (per-project + UX + closeout). Updated `config/skill-config.yaml` to 8.1.0.

- **v8.0.2** (May 14, 2026): First live bootstrap-data --profile maintainer run against the post-v21-migration atlas surfaced two follow-up bugs in v8.0.1's profile plumbing. Step 4 (cf_atlas build) completed correctly: Phase H stamped 19,386 rows in ~12.6 min, Phase N fetched 722 feedstocks for rxm7706, full atlas reached steady state (Phase H eligibility dropped 19,442 → 4). But Step 6 (Phase N redundant re-invocation) crashed at the atlas's Phase H dispatcher with `ValueError: PHASE_H_SOURCE='auto' is not one of pypi-json, cf-graph`. Root cause: PROFILES had `PHASE_H_SOURCE="auto"` (a bootstrap-data CLI concept), `os.environ.setdefault` injected it, and Step 6's subprocess inherited the value because Step 6 didn't explicitly override PHASE_H_SOURCE in env_overrides (it had no reason to — Phase H wasn't its goal). Also caught: Step 6 was redundant under profile invocations because the profile's `PHASE_N_ENABLED=1` env-var inheritance already triggered Phase N inside Step 4. Fixes: (1) PROFILES for maintainer + admin no longer set PHASE_H_SOURCE (atlas defaults to pypi-json; CLI --phase-h-source flag still resolves "auto" correctly in Step 4's env_overrides); consumer keeps PHASE_H_SOURCE=cf-graph (atlas-valid). (2) Step 6 now checks `phase_n_ran_in_step4` (truthy PHASE_N_ENABLED in env + Step 4 actually ran) and prints a skip message instead of re-invoking build-cf-atlas. New regression test `test_maintainer_and_admin_omit_phase_h_source`. Updated `config/skill-config.yaml` to 8.0.2.

- **v8.0.1** (May 14, 2026): D1+D2 live-DB verification PATCH. (1) `_auto_detect_phase_l_sources` SQL fix — the helper joined `package_maintainers` directly on `handle`, but the production schema requires a 3-table join (`pm ON pm.conda_name = p.conda_name JOIN maintainers m ON m.id = pm.maintainer_id WHERE LOWER(m.handle) = LOWER(?)`). Test fixture used a 2-table simplification that masked the bug. Caught by live-DB verification: helper was always returning `None` for any maintainer regardless of their populated registries. (2) Phase H serial-gate NULL-handling fix — `pypi_last_serial != pypi_version_serial_at_fetch` evaluates to NULL (falsy) when serial-at-fetch is NULL, so the entire post-v20→v21-migration working set (~9,800 rows) would have been silently skipped from condition 2. Replaced with `IS NOT` (NULL-safe inequality). Test added covering the post-migration scenario. (3) Phase H stat-split shipped — v8.0.0 specced `eligible_never_fetched / eligible_serial_moved / eligible_safety_recheck` but never landed it. New `_phase_h_eligibility_stats(conn)` helper returns the three branch counts; both pypi-json and cf-graph paths print the breakdown and include it in the return dict. 5 new tests (2 stats + 1 post-migration regression + 1 case-insensitive handle match + 1 fixture-shape fix). Live-DB verification against the real 32,053-row v21 atlas: 9,654 never_fetched + 9,788 serial_moved + 0 safety_recheck = 19,442 eligible (matches eligible-rows count exactly). Updated `config/skill-config.yaml` to 8.0.1.

- **v8.0.0** (May 13, 2026): Structural enforcement + persona profiles. Bundle closes 3 of 4 v7.9.0 follow-ups (A3, A4, A5); A6 (vuln_total drop) deferred after the planned drop discovered 4 actual consumers. **MAJOR** because `bootstrap-data --profile maintainer` is the new documented default (no invocations break; legacy no-flag runs print an end-of-run advisory). **Wave A** ships schema v21's `v_actionable_packages` view encoding the canonical persona-filter triplet, refactors 7 phase selectors to read from it, and adds `tests/meta/test_actionable_scope.py` which asserts every `SELECT ... FROM packages WHERE ...` either reads the view or carries a `# scope:` justification comment — preventing the drift v7.9.0 had to fix by hand. **Wave B** adds `pypi_version_serial_at_fetch INTEGER` and makes Phase H eligible-rows serial-aware (never-fetched OR serial-moved OR 30 d safety re-check); warm-daily Phase H drops ~5 min → ~30 s on a typical day. **Wave D** ships `bootstrap_data.py`'s `PROFILES` dict + `--profile {maintainer,admin,consumer}` argparse flag + `_auto_detect_gh_user()` (5 s timeout, graceful degradation) + `_auto_detect_phase_l_sources(maintainer, db_path)` (queries `v_actionable_packages JOIN package_maintainers` for populated registries in scope) + `_print_no_profile_advisory()`. Explicit env vars and CLI flags always win over profile defaults (`os.environ.setdefault` semantics). Maintainer profile auto-derives `PHASE_N_MAINTAINER` from `gh api user --jq .login` and auto-restricts `PHASE_L_SOURCES`; admin runs channel-wide Phase N; consumer uses `PHASE_F_SOURCE=s3-parquet` + `PHASE_H_SOURCE=cf-graph` + skips Phase N + `PHASE_D_UNIVERSE_DISABLED=1` for air-gap friendliness. 5 previously 📋-open Phase-N-gated catalog rows flip to ✅ shipped (`feedstock-health --filter open-prs-human`, `--filter open-issues`, `--filter ci-red`, abandonment composite SQL, maintainer-last-active SQL). New `## Profile Reference (v8.0.0)` appendix in `atlas-phases-overview.md`; per-phase "Profile defaults" lines on D / E / F / H / L / N; `atlas-operations.md` quickstart + cron snippets rewritten for `--profile`. 24 new unit tests (19 persona profiles + 5 Phase H serial-gate). Schema v20 → v21 migration is idempotent and self-healing on next `init_schema`. Updated `config/skill-config.yaml` to 8.0.0.

- **v7.9.0** (May 13, 2026): Actionable-scope audit closure — bundled phase-by-phase fix landing as schema v20 + 29 new unit tests + a new `pypi-only-candidates` CLI. (1) Phase H 56× denominator cut (`_phase_h_eligible_pypi_names` now applies the canonical persona-filter triplet `conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0`; denominator drops ~672k → ~12k). (2) Phase D split into daily-lean (`pypi_last_serial` UPDATE on conda-linked rows) + TTL-gated universe upsert (new `_phase_d_upsert_universe` writing into the schema-v20 `pypi_universe` side table). (3) Schema v20: `pypi_universe(pypi_name TEXT PRIMARY KEY, last_serial INTEGER, fetched_at INTEGER)` side table + self-healing migration that moves existing `relationship='pypi_only'` rows out of `packages` into the new table in a single transaction (idempotent — re-running `init_schema` is a no-op). `SELECT COUNT(*) FROM packages` finally returns an honest ~32k working-set count. (4) Phases J + M archived-feedstock filter at the write site (Phase J builds an `inactive_feedstocks` skip-set from `packages` before opening the cf-graph tarball; Phase M's `rows_to_process` SELECT gains the canonical triplet) — closes the v19 bug where archived feedstocks polluted `whodepends --reverse` results. (5) New `pypi-only-candidates` CLI + MCP tool: surfaces admin "what's on PyPI but not on conda-forge" candidates ordered by `last_serial DESC`. Three-place rule applied (canonical impl + thin wrapper + pixi task + meta-test SCRIPTS entry). 29 new unit tests across 5 test files; 432 total passing. The 📋-open SQL-only "what's on PyPI but not on conda-forge?" row flips to ✅ shipped in `reference/atlas-actionable-intelligence.md`. Updated `config/skill-config.yaml` to 7.9.0.

- **v7.8.1** (May 12, 2026): Audit close-out pass — every remaining HIGH / MEDIUM / LOW finding from the v7.8.0 deep audit is now addressed or explicitly justified as intentional. (1) Phase H rate-limit safety: default `PHASE_H_CONCURRENCY` 8→3, `Retry-After` parsing via the shared `_parse_retry_after` helper (capped at 60s), ±25% jitter on exponential backoff — closed the last HIGH item. (2) OSV air-gap parity: new `OSV_API_BASE_URL` env (vulnerability_scanner) + `OSV_VULNS_BUCKET_URL` env (cve_manager) with public-host fallback + per-call URL resolution. (3) Three new API resolvers in `_http.py` — `resolve_github_api_urls` / `resolve_gitlab_api_urls` / `resolve_codeberg_api_urls` (path-suffix arg, list return, mirror the Maven pattern). `GITHUB_API_BASE_URL=https://<ghes>/api` covers GHES REST + GraphQL under one env var. `_phase_k_fetch_one` and `_phase_k_github_graphql_batch` wired. (4) Phase E cf-graph cache TTL is env-tunable via `ATLAS_CFGRAPH_TTL_DAYS` (default 1.0, float-parseable) — closes the weekly-cron 150MB re-download pain. (5) Phase N rate-limit detection: new `_is_gh_rate_limit_stderr` parses `gh api graphql` stderr for primary / secondary / abuse-detection wording; `_phase_n_query_batch` retries up to 3x with 30s/60s base + ±25% jitter on rate-limit hits (more patient than Phase F/H since secondary-limit windows are minutes). (6) Phase C incremental commits every 500 entries (was monolithic BEGIN/COMMIT around 12k UPDATEs). (7) Phase B6 and Phase J left as monolithic transactions with documentation comments — both are intentional designs (B6 = 3 bulk UPDATEs in <1s; J = full-snapshot semantics via `DELETE FROM dependencies` at txn start). (8) New `_http.fetch_to_file_resumable(target, urls, ...)` helper: streams body to a `.part` sibling, uses `Range: bytes=<size>-` to resume, handles 206/200/416 correctly, atomic-renames on success. (9) `cve_manager.fetch_and_unzip` rewired to use it: 4 GB OSV `all.zip` streams to disk in 4 MB chunks and decompresses from the cached file — RAM drops from ~4 GB to ~4 MB; dropped connection at 95% no longer restarts from byte 0. (10) `inventory_channel.py` left in-memory with a comment pointing future callers (artifacts >500 MB) at the resumable helper — the 24h cache TTL bounds the failure mode. 44 new unit tests, 403 total passing. Updated `config/skill-config.yaml` to 7.8.1.

- **v7.8.0** (May 12, 2026): Atlas hardening pass after the v7.7.2 4,400-row Phase K rate-limit incident. Five waves: (1) `_http.py` gains 7 new registry resolvers (CRAN/CPAN/LuaRocks/crates/RubyGems/Maven/NuGet) + `auth_headers_for` (shared by urllib and `requests` callers) + atomic-write utilities (`atomic_writer` ctx manager + `atomic_write_bytes` / `atomic_write_text`). (2) Phase K: REST fanout against `api.github.com/repos/...` replaced with batched GraphQL (`_phase_k_github_graphql_batch`) — 4,400 repos → ~44 POSTs instead of ~14,000; per-alias errors map via `path[0]` to preserve downstream branching. (3) Phase F: default `PHASE_F_CONCURRENCY` lowered 8→3; new `_parse_retry_after` honors `Retry-After` header (delta-seconds OR HTTP-date) capped at 60s; ±25% jitter on exponential backoff prevents synchronized retry storms; new `ANACONDA_API_BASE_URL` env override. (4) Phase L: 8-worker × 7-registry storm (up to 56 concurrent reqs at startup) replaced with **sequential across registries** + **per-registry concurrency caps** (crates=rubygems=1, cran=cpan=luarocks=maven=2, npm=nuget=4) reflecting documented rate limits. 7 `_resolve_*` functions rewired through the new resolvers. (5) Phases B5/E/E5/M resumability: replaced monolithic BEGIN/COMMIT with incremental commits + idempotent SQL; Phase E now streams the cf-graph tarball directly from disk (saves ~150MB RAM) and atomic-writes the download cache; Phase E5 saves a `save_phase_checkpoint(cursor=...)` per GraphQL page. Also purged hardcoded `registry.npmjs.org` from `npm_updater.py` + `recipe-generator.py:fetch_npm_info` + latent fix in `recipe-generator.py:fetch_pypi_info`. Atomic JSON writes wired into `cve_manager.py`, `mapping_manager.py`, `inventory_channel.py` (HTTP cache + `--sbom-out`). New `reference/atlas-phase-engineering.md` captures the 9 patterns (per-host rate limits, GraphQL batching, Retry-After+jitter, per-registry concurrency, atomic writes, incremental commits + idempotent SQL, streaming tarfiles, page-level checkpoints, `<HOST>_BASE_URL` enterprise routing convention) as the default rule book for any new phase or phase refactor. 39 new unit tests; 368 total passing across the CFE suite. Breaking change: Phase L return-dict field rename `concurrency` → `per_source_workers` (no internal consumers; external dashboards may need an update). Updated `config/skill-config.yaml` to 7.8.0.

- **v5.9.0**: Second live documentation pass against conda-forge.org and github.com/conda-forge (Apr 25, 2026). Also added `automation/` directory: `quarterly-audit.prompt.md` (canonical prompt, kept in sync with the cloud routine `trig_015z9XF8ExDJuN9qsZYGYKcu`), `run-audit-local.sh` (local-CLI runner that strips frontmatter and invokes `claude -p`), and `README.md` documenting cloud vs local invocation, cron/systemd scheduling, and recreation instructions. Linked from a new `## Skill Automation` section in SKILL.md. Project `CLAUDE.md` references section expanded into a structured `## Conda-Forge Ecosystem Reference` mapping 25+ repos and docs across conda-forge and prefix-dev (Local Tooling, Submission Pipeline, Automation/Bots/Backend, Post-Submission, Documentation, Community Channels). Added new `## Ecosystem Updates (Apr 2026)` section to SKILL.md covering build-tooling, platform/toolchain, and policy changes since v5.8.0. Updated CI Infrastructure: GitHub Actions is now an opt-in build provider for `linux_64` (conda-smithy 3.57.1+, Mar 8, 2026) — no longer "rerendering only"; added a `provider:` configuration example. Added Community Channels table: Zulip is primary; Discourse is read-only since Oct 15, 2025; Gitter is decommissioned. `reference/recipe-yaml-reference.md` updated with rattler-build v0.61/v0.62/v0.63 sections (debug subcommand, three-mode env-isolation, multi-output script-discovery removal); macOS SDK directory corrected to `/opt/conda-sdks` (was `$PIXI_PROJECT_ROOT/.pixi/macOS-SDKs`); new macOS Accelerate BLAS/LAPACK section. `reference/pinning-reference.md` adds NVIDIA Tegra notes (CUDA 12.9 SOC builds) and the new `conda-forge/label/mpi-external` MPI variant label. `reference/selectors-reference.md` and `reference/recipe-yaml-reference.md` updated to clarify `py < 310` is a no-op (build matrix already starts at 3.10) — examples now use `py < 311`. Templates `python/compiled-recipe.yaml`, `python/maturin-{recipe,meta}.yaml`, and `examples/python-compiled/recipe.yaml` no longer carry the obsolete `py < 39` skip. `templates/multi-output/lib-python-recipe.yaml` annotated with v0.63 explicit-script note. Updated `config/skill-config.yaml` to v5.9.0.
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
