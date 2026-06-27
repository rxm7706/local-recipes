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
- **Pair quantitative claims with a verifiable source.** Cost, scan size, duration, and count claims in spec/code/docs MUST cite their source (dry-run preflight output, measured benchmark, `bq show` table stats) or carry a "verified $DATE" marker. **Live integration tests are load-bearing for quantitative claims; mocked unit tests cover code correctness but cannot find server-side caps, rate limits, response truncation, or quota walls.** Numerical claims decay silently — the 2026-06-12 BigQuery invoice surprise traced to a 2016 napkin number ("~30 GB scanned per query, within free tier") copied through the v8.1.0 spec, code docstring, CHANGELOG, three reference docs, and the quickref cheatsheet without anyone re-verifying. Real cost (verified 2026-06-12 via live dry-run preflight): ~9.5 TB per 90-day run (~$59), off by ~3,000×. The v8.14.3 hot-patch's *corrected* estimate of ~$15-25 was itself off by ~3-4× — the skill author estimated rather than running the preflight that v8.14.3 itself shipped. The v8.16.0 ClickHouse bucketed-pagination architecture passed all 13 mocked unit tests but failed in live testing (~95% HTTP 500 from rate limits + 1,000-row response cap not in feature docs); only live verification surfaced the architecture flaw. Same failure mode, different decade, different vendor. Treat quantitative claims as time-bounded; require a procedure future operators can re-run. See `reference/atlas-phase-p-cost-model.md` for the canonical application of this discipline.
- **Audit upstream renames across the full workspace, not just the runtime entry-point.** When an upstream dependency renames a module, class, or function (e.g. `conda-forge-metadata 0.16.x` renamed `autotick_bot` → `conda_forge_bot`), grep the entire skill workspace — **`scripts/` + `tests/` + `tools/` + project-level Python** — not just the script you observed failing. The v8.16.1 fix patched 2 sites (Phase C atlas + `update-mapping-cache` CLI — the call sites the failing `bootstrap-data` run exercised). v8.16.3 had to follow up after `pixi run test` surfaced 3 more errors in 2 missed sites (`name_resolver.py` Tier-2 fallback + `tests/conftest.py:stub_metadata_api` fixture). The discovery procedure (`pkgutil.iter_modules` to enumerate installed submodules) was correct; the *application scope* was too narrow because it was limited to "what the runtime entry-point hits", excluding rare-path fallbacks and test infrastructure. Apply the try-new-fallback-to-old import pattern at every grep hit at once; ship one PATCH, not three.

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

**Canonical 2026 shape** — `package.name` is the literal distribution name; `context:` carries only `version` (+ optional `python_min` override); the URL's path segments are literal and only `${{ version }}` interpolates. This is what current `grayskull` emits and what conda-forge reviewers expect:

```yaml
context:
  version: "1.0.0"

package:
  name: my-package
  version: ${{ version }}

source:
  url: https://pypi.org/packages/source/m/my-package/my-package-${{ version }}.tar.gz
```

For sdist filenames that use underscores instead of hyphens (e.g. `litellm_proxy_extras-0.4.69.tar.gz` for project `litellm-proxy-extras`, `py_yaml12-0.1.0.tar.gz` for `py-yaml12`), keep the path-2 segment hyphenated (distribution name) and the filename stem underscored:

```yaml
source:
  url: https://pypi.org/packages/source/l/litellm-proxy-extras/litellm_proxy_extras-${{ version }}.tar.gz
```

**Wheel (LAST resort — only when no *usable* sdist AND no GitHub source archive exist; see G54/G55 — a wheel-only PyPI package often still has source on GitHub, and many sdists are metadata-only/broken):**
```yaml
source:
  url: https://pypi.org/packages/<py-tag>/m/my-package/my-package-${{ version }}-<py-tag>-none-any.whl
```
where `<py-tag>` is the wheel's Python tag (`py3`, `py2.py3`, `cp310`, …). The `<py-tag>` segment is upstream-specific and may change on a version bump — flag this with a recipe comment.

**Why fully literal?** The older `${{ name[0] }}` / `${{ name }}` / `${{ name | replace("-", "_") }}` chain was a holdover from `context.name`-style recipes. Now that the distribution name lives only in `package.name`, the URL is just a path — write it as a path. Renames are rare, version bumps are common, and the literal form is more legible and removes a class of jinja-typo bugs.

The `recipe-generator.py` script emits this shape automatically; manual edits and recipe reviews must enforce the same form. See `docs/enterprise-deployment.md` §3 for the full proxy rationale.

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

### Every v1 Recipe Must Declare the Schema Header

Every `recipe.yaml` (v1 format) **must** start with these two lines verbatim — no blank line before them:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1
```

The comment drives editor schema validation (VS Code, Helix, Zed, IntelliJ); `schema_version: 1` flips rattler-build into the v1 parser. Build tooling treats v1 as implicit when the file is named `recipe.yaml`, so omitting either line is not a build error.

**Empirical adoption**: only 1 in 30 recent merged staged-recipes PRs (Apr–May 2026) carries the comment header; conda-forge reviewers do not block PRs that omit it. This is a **local-recipes repo convention**, enforced by the `tests/meta/test_recipe_yaml_schema_header.py` meta-test and by the optimizer's `SCHEMA-001` check — both written specifically for this repo so editor validation is on by default for every recipe under `recipes/`.

`recipe-generator.py` enforces this on all three v1 generation paths (PyPI/grayskull, rattler-generate for CRAN/CPAN/LuaRocks, npm). The `optimize_recipe` check **SCHEMA-001** flags any user-edited recipe.yaml that drops them.

`meta.yaml` (v0 format) does **not** use the schema header — it predates the prefix-dev schema. Only apply this rule to `recipe.yaml`.

### Never Add AI Comments Inline — Park Them in the Bottom `# CFE comments` Block

**The recipe body must stay free of CFE/Claude/agent-authored comments.** Do not scatter rationale, gotcha tags, or explanatory notes (`# G25 flatten`, `# load-bearing under pip_check`, `# license pattern 2`, `# python_min override because…`, `# BFP fix:…`, build-env explanations, etc.) inline through `requirements:`, `build:`, `tests:`, `about:`, or any other body section. This keeps the local `recipe.yaml` a clean copy-paste source into a feedstock / staged-recipes PR, and keeps submitted conda-forge recipes free of AI comment noise.

Two distinct comment classes — handle them differently:

1. **Existing human / upstream-feedstock comments** (already in the source recipe or on the conda-forge feedstock — e.g. `# Node.js build environment`, `# pnpm package manager`) → **LEAVE in the body verbatim.** Never remove or relocate them; the local recipe must stay a faithful mirror of the feedstock. Removing them is a defect.

2. **New comments the agent wants to add** (any rationale the agent generates) → **never inline.** Write them ONLY in the bottom `# CFE comments` block, organized by the recipe location they refer to. A **human** later curates — copying *up* into the body only the notes worth keeping in the submitted recipe.

The only comment that stays at the top of the body is the functional schema-header line (`# yaml-language-server: $schema=…`) — it's a directive, not an annotation.

**Canonical layout** (see `recipes/ironcalc/recipe.yaml` — the reference exemplar). In `extra:`, after `recipe-maintainers:` + a blank line. The `####` / `# CFE …` lines are YAML comments at column 0; the `cfe-*` keys are real YAML indented 2 spaces under `extra:`:

```yaml
extra:
  recipe-maintainers:
    - <handle>

#### CFE metadata AND comments
# CFE metadata
  cfe-conda-name: <name>
  cfe-upstream-registry: <pypi|npm|cargo|maven|cran|cpan|luarocks|golang|github>
  cfe-upstream-name: <name in that registry>
  cfe-purls:
    - pkg:conda/<name>@${{ version }}
    - pkg:<registry>/<upstream>@${{ version }}
  cfe-upstream-repo: <url>
  cfe-upstream-homepage: <url>
  cfe-import-names: [<top-level python import(s)>]
  cfe-source-kind: <pypi-sdist | pypi-wheel | github-tag | github-commit | github-release-binary>
  cfe-noarch: <python | generic | compiled>
  cfe-pip-check: <true | false:<reason-code>>
  cfe-on-conda-forge-status: <confirmed-on-conda-forge | pending-submission-to-conda-forge | pending-approval-on-conda-forge | blocked-pending-prerequisites | pypi-only | archived-on-conda-forge>
  cfe-on-conda-forge-feedstock: <feedstock-url | none>
  cfe-forge-recipe-updates-needed: <none | list>
  cfe-forge-blocker-list: []   # or a YAML list of blockers
  cfe-last-checked: <ISO-8601 UTC>
  cfe-generated-by-version: <ver>
  cfe-generated-at-datetime: <ISO-8601 UTC>
  cfe-local-build-status: <success | build-clean-test-blocked | failed | not-attempted>
  cfe-local-build-datetime: <ISO-8601 UTC | none>
  cfe-local-build-platform: <host subdir the build ran on, e.g. linux-64 | none>
  cfe-local-build-tool: <rattler-build | conda-build | none>
####
# CFE comments
# Header:
#    # <general / provenance notes the agent would have put at the top>
# build:
#  script:
#    env:
#      # <the note that would have been inline in build.script.env>
# context:
#    # <…>
#  host:
#    # <…>
#  run:
#    # <…>
####
```

The `# CFE comments` block mirrors the recipe's structure (location keys `build` / `context` / `host` / `run` / `requirements` / `about` / `tests`) so each parked note shows where it would belong if promoted. Both the `# CFE metadata` and `# CFE comments` sections are CFE-local-only and are **stripped before any push** (along with `extra.cfe-*` keys). `recipe-generator.py` must emit new rationale into this block, never inline.

**The 4 identity/decision fields are the cached "hard-won" answers** (added v8.37.0; from the 4-analyst deep-analysis synthesis, 2026-06-19). They sit at the end of the identity/upstream block (after `cfe-upstream-homepage`, before `cfe-on-conda-forge-status`). Each caches a value that authoring would otherwise have to recompute — and that a **regen** (`grayskull` / `recipe-generator.py` re-running over a version bump) would re-guess, possibly *wrong*. Value semantics:

- **`cfe-import-names`** — the **verified** top-level Python import name(s) — the names the CFEP-25 test `imports:` use. This **caches the G7/G10 divergence**: when the import name does NOT match the distribution name (`altk`, `OpenDsStar`, `pymilvus.model`, `ibm_boto3`, `baidubce`, `data_diff`), grayskull re-guesses it wrong on every regen and the import test breaks. With the verified value cached, a regen **restores** the correct import instead of re-deriving it from the sdist. This is the **single highest-frequency authoring recompute**, and is especially load-bearing for the feedstock-refresh effort (256 regens). Non-Python recipes: `[]`.
- **`cfe-source-kind`** — which artifact the recipe actually sources: `pypi-sdist`, `pypi-wheel`, `github-tag`, `github-commit`, or `github-release-binary` (a prebuilt single-file release binary that is repackaged rather than built — e.g. a self-contained .NET CLI, see [G44](#g44-net--c-cli-tools-have-no-source-build-path-on-conda-forge--repackage-the-self-contained-release-binaries-per-platform)). When a **non-PyPI** source was chosen *deliberately* (because the PyPI sdist re-trips a known gotcha), append the reason: `github-tag:pypi-sdist-strips-headers-G5`. This prevents a version bump from silently reverting to a PyPI sdist that re-trips G4 / G5 / G9 / G16. **Keep this field in sync with the actual `source:` block:** when you switch the source (wheel→sdist/github), UPDATE `cfe-source-kind` — it is the cached decision a regen reads back, and a stale value (e.g. `pypi-wheel` on a recipe already sourcing a GitHub tag) mis-routes the next regen *and* hides the recipe from the G54 retroactive wheel-sweep. Live miss: `pybase62` was switched to a GitHub tag archive but left `cfe-source-kind: pypi-wheel`.
- **`cfe-noarch`** — the build shape: `python` (noarch:python), `generic` (noarch:generic), or `compiled` (a per-arch / per-Python compiled build). Drives the build matrix and the per-Python prerequisite fan-out (G38 / G40). Per G42 it can **flip across versions** — verify the *current* version's artifact shape (e.g. milvus-lite 3.0 went C++-compiled → pure-Python), don't trust the older version's reputation.
- **`cfe-pip-check`** — whether `pip_check: true` is in effect. When it is intentionally **off**, record `false:<reason-code>` so the temporary external-bug waiver and its **revert obligation** (G24 / G26 / G28 / G36 — e.g. an upstream dep's poisoned wheel METADATA / `dist-info` version) is not silently lost on strip-before-push. The reason code names the blocking package so the waiver can be re-checked and revoked when the upstream is fixed.

**The `cfe-local-build-*` fields are the LOCAL-BUILD verification record** (added v8.36.0). They capture "does this recipe build locally?" — a **verified fact** — and are deliberately **separate** from `cfe-on-conda-forge-status`, which tracks "is it on / submittable to conda-forge?". The two are orthogonal: a recipe with `cfe-on-conda-forge-status: blocked-pending-prerequisites` may have built **perfectly** locally (green against the local channel) and is "blocked" only because a prerequisite isn't on conda-forge yet — `cfe-local-build-status: success` records that the recipe itself is sound. Always set `cfe-local-build-status` from the **actual** outcome of the last local build, never inferred from the cf-submission status.

`cfe-local-build-status` value semantics:

- **`success`** — build EXIT=0 **and** the import test **and** `pip_check` all pass; the artifact landed in `noarch/` (or `linux-64/` for arch builds). The recipe is fully verified locally.
- **`build-clean-test-blocked`** — the **build phase was clean** (the `.conda` was written) but the **test-env solve failed** on a missing / local-only / not-yet-on-conda-forge dependency (rattler-build quarantines the artifact to `broken/`). The recipe itself built fine; the block is a **prerequisite gap**, not a recipe defect. (Common in the langflow-closure class of multi-layer recursion.)
- **`failed`** — the **build phase itself** failed (compile / packaging error). The recipe is not yet sound.
- **`not-attempted`** — recipe authored but not built yet. This is the **default** the recipe-generator emits.

The companion fields are `none` until a build runs: `cfe-local-build-datetime` (ISO-8601 UTC of the build, else `none`), `cfe-local-build-platform` (the **host subdir** the build ran on, e.g. `linux-64`, `osx-arm64`, else `none`), and `cfe-local-build-tool` (`rattler-build` for v1 / `conda-build` for v0, else `none`). Like every `cfe-*` key, all four are **stripped before any push**.

**Recording the first build on a recipe that has no `cfe-*` block?** Add the **full** canonical block — identity + the four decision fields (`cfe-import-names` / `cfe-source-kind` / `cfe-noarch` / `cfe-pip-check`) + `cfe-on-conda-forge-status` + all four `cfe-local-build-*` fields — never a `cfe-local-build-*`-only stub. Older pre-convention recipes (e.g. `firecrawl-py`, `mem0ai`) often carry only `extra.recipe-maintainers`; recording their first local build means adding the **complete** block, not appending a six-field fragment under a bare `#### CFE metadata` header (the failure mode caught in local-recipes PR #24's first draft).

**cfe-* schema design principle** (from the 4-analyst deep-analysis synthesis, 2026-06-19). What earns a `cfe-*` field is governed by three rules:

1. **CACHE identity and hard-won decisions; READ volatile metrics live from the atlas.** A `cfe-*` field is justified only when it stores something **stable** that authoring would otherwise have to recompute — an identity fact (`cfe-conda-name`, `cfe-import-names`, `cfe-upstream-name`) or a hard-won decision (`cfe-source-kind`, `cfe-pip-check`, `cfe-on-conda-forge-status`). Volatile signals — CVE counts, download numbers, feedstock-health, adoption-stage, who-depends — are **NEVER cached**: read them live from the atlas at the moment they're needed. Caching a volatile metric **manufactures staleness** — the recipe ships a number that was true once and is wrong now.
2. **STAMP any cacheable-but-volatile field with `cfe-last-checked` as a hint, never ground truth.** A few fields (e.g. `cfe-on-conda-forge-status`) are stable enough to cache but can still drift. They carry `cfe-last-checked` so a reader knows the value is a **hint** with an age, not an authoritative fact — re-verify before relying on it for a decision.
3. **All `cfe-*` are stripped before any push.** Every `cfe-*` key (and both `# CFE …` comment blocks) is local-recipes-only and removed before the recipe is copied into a feedstock / staged-recipes PR. They exist to drive CFE/admin/maintainer tooling, never to ship.

The 2026-06-19 deep-analysis **disqualified** three previously-floated SBOM/security placeholders — none was ever encoded, and none should be: **`cfe-cpe`** (the CPE is syft-derived from the package name — recompute, don't cache), **`cfe-sbom-hash`** (the SBOM's home is `conda-meta/` per unratified CEP #127, not recipe `extra:`), and **`cfe-syft-ref`** (attestation lives in an external Sigstore bundle). None of the three reaches a tool from recipe `extra:`, so none earns a `cfe-*` field.

**Tier-2 orchestration fields are PLANNED** — they land *with* the feedstock-refresh effort (where they get populated), not before:

- **`cfe-feedstock-version`** + **`cfe-upstream-latest-version`** — the two cached legs of the `behind-upstream` triple (the third, the live-deployed feedstock version, is read live). Stamped-hint fields (carry `cfe-last-checked`).
- **`cfe-platforms-shipping`** / **`cfe-platforms-target`** — the feedstock's current vs. desired platform coverage (drives platform-expansion PRs).
- **`cfe-submission-pr-state`** — the open/merged/closed state of the PR named by the existing `cfe-submission-pr`, completing that field.

### Canonical Test Block for `noarch: python` Recipes

The canonical test for a `noarch: python` library recipe is the CFEP-25 triad:

```yaml
tests:
  - python:
      imports:
        - <top_level_module>
      pip_check: true
      python_version:
        - ${{ python_min }}.*
        - "*"
```

This is what conda-forge's web-service review (the post-merge linter) expects on every noarch:python recipe. A recipe that uses `package_contents.site_packages:` instead — even when the artifact is otherwise clean — **will be flagged** by the web service with the canonical hint:

> noarch: python recipes should usually follow the syntax in our documentation for specifying the Python version. For the `tests[].python.python_version` or `tests[].requirements.run` section of the recipe, you should usually use the pin `python_version: ${{ python_min }}.*` or `python ${{ python_min }}.*` for the python_version or python entry.

`conda-smithy lint` (the local linter the skill's `validate_recipe` runs) does **not** fire this; it's a web-service-only check. So a recipe can pass every local gate, build cleanly, install correctly — and still get a review comment from the web service.

**Escape hatch — when `package_contents.site_packages:` is permitted:**

Only when the test environment genuinely cannot exercise `python.imports`:

- **Django web apps** — `import myapp.<module>` raises `ImproperlyConfigured` without `DJANGO_SETTINGS_MODULE`, and the test env's solver can't resolve the 40+ transitive Django-plugin chain even if settings were configured.
- **ML benchmarks** with non-conda-forge deps (`mediapipe`, etc.) that the test env can't install.
- **C extensions shipped under a `noarch: python` recipe** (legacy grayskull-emitted pattern) where the ABI-specific `.so` won't match the test env's Python.

In these cases, document the reason **directly above the `tests:` block** with an inline comment whose first token is `# CFEP-25-justified:`:

```yaml
# CFEP-25-justified: Django web-app backend — import fails without
# DJANGO_SETTINGS_MODULE configured.
tests:
  - package_contents:
      site_packages:
        - <module>
```

The `recipe_optimizer` check **`TEST-003`** flags any noarch:python recipe missing both `python.imports:` AND the `# CFEP-25-justified:` comment. This catches the same drift that a web-service review would catch — before submission.

`recipe-generator.py` always emits the canonical CFEP-25 triad on the PyPI / grayskull path. Manual edits and remediation passes must not silently substitute `package_contents` without the justification comment.

### Canonical License-File Placement

Per [conda-forge.org/docs/maintainer/adding_pkgs/](https://conda-forge.org/docs/maintainer/adding_pkgs/) — "License files":

> The license should only be shipped along with the recipe if there is no license file in the downloaded archive. If there is a license file in the archive, please set `license_file` to the path of the license file in the archive.

This produces three patterns in order of preference:

1. **Upstream archive ships LICENSE** (the common case) — use `license_file: LICENSE` and let rattler-build pick it up from the extracted source tarball. No file in the recipe directory, no secondary source.
2. **Upstream archive does not ship LICENSE** — drop the `LICENSE` file **directly into `recipes/<name>/`** alongside `recipe.yaml`. Use `license_file: LICENSE`. rattler-build resolves the path relative to the recipe directory when the file is not found in the extracted source. Also notify the upstream developers that the license file is missing — shipping LICENSE in the recipe is a workaround, not a long-term solution.
3. **Secondary `source.url` fetching LICENSE from GitHub** (the pattern this skill used pre-v8.10.0) — works but is **non-canonical**. Adds a brittle commit-pin + sha256 maintenance burden and looks unusual to reviewers. Convert to pattern (2) when you encounter it.

When pattern (2) is used, ship the LICENSE in-recipe and remove the stale "upstream archive ships no LICENSE; secondary source pulled..." comment from `source:`. The `source:` block can return to its flat single-URL form.

Why this matters: the conda-forge web-service review accepts any of the three patterns, but reviewers occasionally flag (3) ("can this be simplified?"). (1) is invisible; (2) reads as deliberate and gets a free conversational checkpoint with reviewers ("ship LICENSE in-recipe because upstream archive omits it").

### Rust Recipe Standards (CLI binaries — conda-forge 2026 canonical pattern)

Every new Rust **CLI** recipe must adopt the canonical pattern documented at
[conda-forge.org/docs/maintainer/example_recipes/rust](https://conda-forge.org/docs/maintainer/example_recipes/rust/)
and used by 17/17 CLI Rust recipes merged to staged-recipes in Apr–May 2026.
The pattern is not optional — reviewers will request these five elements:

> **Source-of-truth note**: `rattler-build`'s own tutorial at
> <https://rattler-build.prefix.dev/latest/tutorials/rust/> shows plain
> `cargo install --locked --bins` (no `auditable`, no `--no-track`). That
> tutorial describes the tool, not the conda-forge style overlay. When the
> two diverge, conda-forge docs + the merged-PR sample (17/17) win for
> staged-recipes submissions.

1. **`cargo auditable install`** (not plain `cargo install`) — embeds dependency SBOM into the binary.
2. **`--locked --no-track --bins`** flags — reproducible, no `.crates.toml` in prefix, binary-only install.
3. **Unix/Win install root split** — `--root ${{ PREFIX }}` on unix, `--root %LIBRARY_PREFIX%` on win.
4. **`script.env` + `script.content` shape** — set `CARGO_PROFILE_RELEASE_STRIP: symbols` and `CARGO_PROFILE_RELEASE_LTO: fat` via the env map, then list commands under `content:`. Avoids the [G1 "exports don't carry across script entries"](#g1-script-list-entries-run-in-separate-shells--env-vars-do-not-carry-across-entries) trap.
5. **Both `cargo-bundle-licenses` and `cargo-auditable` in build deps** — both packages are required, not interchangeable.

Canonical CLI skeleton (see [`templates/rust/cli-recipe.yaml`](templates/rust/cli-recipe.yaml) for the full template):

```yaml
build:
  number: 0
  script:
    env:
      CARGO_PROFILE_RELEASE_STRIP: symbols
      CARGO_PROFILE_RELEASE_LTO: fat
    content:
      - if: unix
        then:
          - cargo auditable install --locked --no-track --bins --root ${{ PREFIX }} --path .
        else:
          - cargo auditable install --locked --no-track --bins --root %LIBRARY_PREFIX% --path .
      - cargo-bundle-licenses --format yaml --output ./THIRDPARTY.yml

requirements:
  build:
    - ${{ stdlib('c') }}
    - ${{ compiler('c') }}
    - ${{ compiler('rust') }}
    - cargo-bundle-licenses
    - cargo-auditable
```

**Exceptions** (different patterns are correct for these — do not force the CLI pattern):
- **pyo3/maturin Python extensions** — use `${{ PYTHON }} -m pip install . --no-deps --no-build-isolation` (the build is driven by maturin via pip; `cargo install` doesn't apply). Template: [`templates/python/maturin-recipe.yaml`](templates/python/maturin-recipe.yaml).
- **Rust libraries (cdylib/staticlib)** — no `cargo install`; build with `cargo build --release` and copy artifacts. Template: [`templates/rust/library-recipe.yaml`](templates/rust/library-recipe.yaml).
- **Rust compilers / non-trivial projects with custom build scripts** (e.g. inko) — keep upstream's build flow; still apply the env map for STRIP/LTO when possible.

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
    - **Follow-up commits on an existing PR branch**: `prepare_submission_branch` hardcodes the commit message to `"Add recipe for <name>"`, which is misleading for any commit other than the initial submission (CI fixes, reviewer feedback, version bumps). For follow-ups, fall back to direct git on the local fork checkout — `git -C <fork> checkout <pr-branch>`, copy updated files from `recipes/<name>/`, `git add` + `git commit -m "<descriptive message>"` + `git push origin <branch>`. The fork path is reported in step 8b's `dry_run=True` result (`fork_path`).
    - **Optional add-on**: drop a `conda-forge.yml` next to `recipe.yaml` to override staged-recipes defaults for this recipe. The most common opt-ins: `azure: { store_build_artifacts: true }` (Azure saves built `.conda` files as downloadable pipeline artifacts; default is `false`), `os_version: { linux_64: alma9 }` (newer glibc), and `noarch_platforms` (extra CI matrix for noarch:python — also required to silence `lint_noarch_selectors` when `requirements.run:` carries an `if: <platform> / then:` selector; see [G12](#g12-platform-conditional-run-deps-in-noarchpython-recipes-need-noarch_platforms-in-conda-forgeyml)). Full reference: [`reference/conda-forge-yml-reference.md`](reference/conda-forge-yml-reference.md). Starter template: [`templates/conda-forge-yml/staged-recipes/conda-forge.yml`](templates/conda-forge-yml/staged-recipes/conda-forge.yml).
    - > *Skills: [`shipping-and-launch`] — staged rollout; [`git-workflow-and-versioning`] — branch-then-PR pattern.*

9.  **Submit PR** — `submit_pr(recipe_name="<name>", dry_run=True)` → verify → `submit_pr(recipe_name="<name>")`
    - Success: `pr_url` returned; PR opens on conda-forge/staged-recipes
    - Run `dry_run=True` first — it checks `gh auth`, fork presence, and branch state
    - When step 8b already pushed the branch, `submit_pr`'s prep phase no-ops (idempotency check) and proceeds straight to opening the PR
    - **Post-edit rebuild discipline (v8.13.0)**: if the recipe was edited (e.g., a step-04 PATCH finding applied) AFTER the green build but BEFORE `prepare_submission_branch`, **re-run `trigger_build` first**. The fork branch should always reflect a verified-green state — pushing a recipe whose latest edit was never built leaves an unverified surface for conda-forge CI to discover. Same-package extension of G15; cheap insurance.
    - If PR creation fails after a successful push, the result includes `branch` + `fork_branch_url` + a `hint` to retry just the PR step — no need to re-push
    - See [Pre-PR Quality Gate Checklist](#pre-pr-quality-gate-checklist) before calling
    - **Feedstock updates branch off here.** `submit_pr` targets `conda-forge/staged-recipes` — correct for **new** package submissions. For updates to an **existing** feedstock (version bumps, dep fixes, CI fixes), the PR target is `conda-forge/<name>-feedstock` directly, not staged-recipes. `lookup_feedstock(pkg_name=<name>)` returning `exists=True` is the signal — when it does, skip steps 8b + 9 and instead: (a) clone the feedstock, (b) copy `recipes/<name>/recipe.yaml` over `recipe/recipe.yaml`, (c) bump `build.number` (or reset to 0 on version bump), (d) open a PR against the feedstock. Steps 1–8 (gates + native build) apply identically to both paths.
    - **Post-merge artifact fetch (v8.14.0)**: while monitoring the PR's Azure CI, use `download_pr_artifacts(pr_ref="...")` / `pixi run -e local-recipes pr-artifacts <pr>` to pull the `.conda` files CI just published into a local `file://` mamba channel — useful for reviewer smoke-tests ("install the artifact, not just read the diff"). Read-only, anonymous; manifest-cached so re-runs are no-ops. See [`guides/testing-recipes.md`](guides/testing-recipes.md) § "Downloading artifacts from a PR".
    - > *Skills: [`shipping-and-launch`] — complete pre-submit checklist; [`git-workflow-and-versioning`] — atomic commit (`feat: add <name> recipe`); [`documentation-and-adrs`] — PR description must explain WHY.*

**Retro→spec feed-forward (v8.13.0)**: when this skill area has a recent retro entry in `_bmad-output/projects/<project>/implementation-artifacts/retro-*.md`, pre-apply its known-gaps workarounds as Execution checklist items in the new recipe-authoring spec — do not assume the skill has been patched. The S1+S3 retros' C1 / C2 / R1 workarounds were pre-applied into S3's spec on 2026-06-11; result was zero step-04 PATCH iterations even before v8.13.0 landed the actual generator fixes. Verified pattern; treat retro entries as "expected workarounds until shipped" rather than "shipped fixes available."

### Sub-workflow: Updating an existing recipe (diff-before-apply)

When the task is **refreshing an existing local recipe** (version bump on a feedstock you maintain locally, applying a grayskull-canonical-pattern update, or re-validating an older recipe against current conventions), do **not** run `generate_recipe_from_pypi` straight into `recipes/<name>/` — grayskull happily drops critical hand-curated content (C-FFI deps, build workarounds, secondary sources, lint-justified comments). The autotick path (`update_recipe`) only handles version + sha256; anything structural needs a manual diff.

Use the **move-aside + fresh-generate + diff + selective-apply** pattern:

1. `mv recipes/<name> recipes/<name>.current` — stash the live recipe.
2. `generate_recipe_from_pypi(package_name=<name>, version=<new>)` — grayskull writes a fresh recipe into `recipes/<name>/`.
3. `enrich_from_feedstock(recipe_path=recipes/<name>/recipe.yaml)` — pulls maintainers + curated about-fields from the existing feedstock (idempotent).
4. `diff -u recipes/<name>.current/recipe.yaml recipes/<name>/recipe.yaml` — produce the full diff.
5. **Categorize each hunk into three buckets** before touching anything:
   - **Corrections to apply** — canonical pattern updates (v8.10.0 literal `package.name`/`source.url`, CFEP-25 test triad, PyPI-authoritative `about.*` metadata, dropped speculative pins). Grayskull and the current canonical patterns are the source of truth.
   - **Regressions to reject** — grayskull-dropped content the recipe needs (system C-libs like `pango`/`glib` that aren't on PyPI, workaround pins documented with comments, `pip check` test commands, secondary `source.url` entries, downstream patches).
   - **Stylistic (no change)** — equivalent formatting differences (block-scalar vs folded `description:`, maintainer ordering). Preserve current to minimize churn.
6. **Present the categorization to the user** in a 3-column table before applying — this is the inspection checkpoint. Surface the regressions explicitly with one-line justifications; the user is the final reviewer on whether grayskull dropping `glib` is genuinely safe.
7. On approval: `rm -rf recipes/<name> && mv recipes/<name>.current recipes/<name>` to restore the live recipe as the base, then apply only the approved corrections via `edit_recipe` or `Edit`. Restoring the base avoids accidentally inheriting any grayskull-emitted bug (e.g., the line-folded source URL caveat below) that wasn't on the categorization list.
8. Re-run steps 2–7 of the main loop (`validate_recipe` / `optimize_recipe` / `check_dependencies` / `scan_for_vulnerabilities` / build) on the merged result.

**Known grayskull-path emit drifts** to expect during step 4 (do not silently inherit):
- Long `source.url` line-folded across two lines by ruamel.yaml's default `width=80` — looks like `weasyprint-${{ version \n    }}.tar.gz`. Cosmetic only; recipe still builds. The v8.11.1 line-fold fix landed in `edit_recipe` but not in the grayskull subprocess emit path. Restore the clean single-line form.
- `python_min: "3.10"` emitted into `context:` even at the conda-forge default floor — per v8.8.0 design it should be omitted at the default; the fix didn't fully land in the grayskull path. Drop it unless overriding the floor.

**Special-case categorizations** to apply during the 3-bucket walk:

- **Test `requirements.run:` missing a `python` pin → ALWAYS a correction to apply**. When a test environment doesn't pin `python`, the solver resolves to the newest available cpython (the conda-forge default), bypassing `python_min` verification on the lowest-supported version. Symptom in CI logs: the resolution table shows `python 3.14.5 ... cp314` for a recipe whose `python_min` is `3.10`. Add `python ${{ python_min }}.*` to the script-test's `requirements.run:` (or use the CFEP-25 triad's `python_version: [${{ python_min }}.*, "*"]` for python-test-blocks). The optimizer's `SEL-002` only fires on the python-test-block form; it doesn't flag the missing `python` pin in a script-test's `requirements.run:` — this categorization must be done by hand during the diff walk.
- **Upstream's explicit `requires-python = "<X,>=Y"` upper bound → a correction to apply** when migrating from a speculative `<4.0`. Tightening to upstream's declared maximum (`<3.15` for `requires-python = "<3.15,>=3.10"`) matches what the wheel build matrix actually supports. The optimizer's `DEP-002` flags this as a hard upper bound in `run:` — acknowledge the trade-off in the categorization (upstream-explicit upper bounds are widely accepted by reviewers; the `DEP-002` suggestion to move it to `run_constrained` is for **speculative** upper bounds, not upstream-declared ones).
- **Upstream-declared upper bounds on `run:` deps are LOAD-BEARING when `pip_check: true` is in the test block.** `pip_check` reads each installed package's wheel-bundled `dist-info/METADATA` and enforces every dep's declared constraint per upstream's `pyproject.toml`. If the recipe's `run:` declares only lower bounds (`tree-sitter-julia >=0.23`), the conda solver picks the newest-compatible version (`0.25.0`), and `pip check` then sees upstream's `tree-sitter-julia<0.25,>=0.23` constraint inside the installed graphifyy wheel, compares against installed `0.25.0`, and **fails the test**. The CI failure is loud; the silent failure is worse — a maintainer who disables `pip_check` to "fix" it ships an install where pip-level deps disagree, and users hit ABI / API break at runtime instead. **Decision rule**: when dropping upper bounds, drop them only if they were speculative (added by an over-cautious generator). If they came from upstream's `pyproject.toml [project.dependencies]`, MIRROR them in the recipe's `run:`. `bot.run_deps_from_wheel: true` keeps these synced on autotick bumps with near-zero maintenance cost. Caught empirically on `conda-forge/graphifyy-feedstock#8` Wave F (Jun 2026) — lower-bound-only recipe shipped, `pip_check` failed in CI, restored upper bounds across all 26 tree-sitter-* run-deps.
- **Run dep lower-bound bumps where upstream's `pyproject.toml` advanced → a correction to apply, but check the dep's feedstock state first**. When upstream has bumped a transitive dep's lower bound (e.g. `ag-ui-a2ui-toolkit>=0.0.2` → `>=0.0.3`) and the new version isn't on conda-forge yet, the fix becomes 2-step: bump the prerequisite feedstock first, then the consumer. For local verification, build the prerequisite locally so v8.2.0's local-channel auto-inject can resolve it. See [G15](#g15-rebuilding-the-same-recipe-re-hashes-the-conda-artifact-but-leaves-repodatajson-stale) for the rebuild-hash-mismatch trap that surfaces during cross-package local fixes.

> *Skills: [`code-review-and-quality`] — categorize each hunk by axis (correctness/standards/style); [`source-driven-development`] — PyPI's `project_urls` is authoritative for `about.*`, the existing recipe is authoritative for system-lib deps grayskull can't see; [`incremental-implementation`] — restore-then-apply, not generate-then-merge.*

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

**Schema v25 (v8.6.0)** adds vulnerability-intelligence overlays
beyond Critical/High/KEV counts: `vuln_max_epss_score` +
`vuln_max_epss_percentile` (FIRST.org EPSS — exploitation probability)
+ `vuln_cwe_top` + `vuln_cwe_categories_json` (MITRE CWE Research
Concepts mapped to 7 cf_atlas categories: RCE / DoS / Info-Disclosure
/ Auth-Bypass / Memory-Safety / Traversal / Injection / Other) on
`packages` + `package_version_vulns`. Three new side tables:
`cisa_kev` (v23, populated by `fetch-cisa-kev`), `epss_scores` (v24,
`fetch-epss`), `cwe_categories` (v24, `fetch-cwe-catalog`). Phase G +
Phase G' overlay loops `OR` all three signals onto vdb's per-CVE
output via shared `_aggregate_v8_6_0_overlays`. Operators can triage
by exploitation probability (`staleness-report --by-epss`), by attack
category (`staleness-report --has-cwe RCE`), or by threshold
(`cve-watcher --epss-threshold 0.7`). v8.6.0 dropped the planned
Phase T (blint hardening) + Phase U (EPSS overlay phase) +
withdrawn-filter scope after verification — see CHANGELOG v8.6.0
narrative.

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
| `platform-breakdown <pkg> \| --top N --platform P \| --feedstock-roundup --maintainer X` | Per-platform 90d download breakdown (Phase F+ Wave 2 data); maintainer triage for ARM/win-64/aarch64 share questions |
| `pyver-breakdown <pkg> \| --policy-check [--maintainer X] [--threshold-pct N]` | Per-Python download breakdown; `--policy-check` **(headline value)** compares declared `python_min` against the empirical floor and flags bump-safe candidates, sorted bump-safe → aligned → aggressive |
| `channel-split <pkg> \| --defaults-share-min N --top M \| --migration-checklist --maintainer X` | Per-channel 90d download breakdown (conda-forge / defaults / bioconda / pytorch / ...); `--migration-checklist` emits paste-into-GitHub-issue markdown for defaults-heavy packages |
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

### Diagnostic chain for feedstock CI test failures

When an existing feedstock's CI fails on a **test phase** (build passed, package built, then test env import/script failed) — distinct from a build-phase failure — the failure is almost always a runtime-dep version mismatch between the recipe's declared lower bound and what upstream actually needs. Use this chain:

1. **Capture the exact ImportError / test command output** via `gh run view <run-id> --repo conda-forge/<name>-feedstock --log-failed | tail -200`. Look for `ImportError: cannot import name 'X' from 'Y'` — `Y` is the offending dep, `X` is the missing symbol.
2. **Cross-check upstream's `pyproject.toml` `[project.dependencies]`** via `WebFetch(https://pypi.org/pypi/<name>/json)` or by reading the sdist's `pyproject.toml` directly. Compare upstream's declared lower bound for `Y` against the recipe's `requirements.run:` lower bound — discrepancies are the prime suspect.
3. **Check the offending dep's feedstock state** via `lookup_feedstock(pkg_name=<Y>)`. If conda-forge is behind the required version, the fix has a prerequisite: bump `<Y>`'s feedstock first, then bump the consumer's pin. For local verification, build the prerequisite locally so v8.2.0's local-channel auto-inject can resolve it.
4. **Confirm the test environment's Python version** from the CI log (`Specs: ... ag-ui-langgraph ==0.0.41 pyhcf101f3_0` + `python 3.14.5 habeac84_100_cp314` in the resolution table). If the recipe's test `requirements.run:` lacks a `python` pin, the solver resolves to the newest available Python rather than `python_min` — verification on the lowest-supported version is silently skipped. Add `python ${{ python_min }}.*` to the test reqs (see [Sub-workflow: Updating an existing recipe](#sub-workflow-updating-an-existing-recipe-diff-before-apply) for the diff-before-apply pattern).
5. **Bump the recipe's lower bound** to match upstream's declared minimum. Don't tighten further than upstream — that's a different decision (security/compat).

Most "ImportError on CI" failures resolve at step 2 once the upstream pyproject is consulted. The chain failed on `conda-forge/ag-ui-langgraph-feedstock` PR #22 because the recipe pinned `ag-ui-a2ui-toolkit >=0.0.2` but upstream's `pyproject.toml` had been bumped to `>=0.0.3` (where the `A2UIGuidelines` symbol was added) — a one-line recipe edit, but the diagnosis needed the full chain.

### External conda-forge ecosystem version-skew (not a recipe defect)

When a **full-dependency-graph** test-env solve fails but **each conflicting sub-cluster solves in isolation on conda-forge**, the cause is **cross-feedstock pin skew**, not a defect in the consumer recipe. Do NOT churn trying to fix it in the consumer.

**Signature**: the consumer builds GREEN, but the test-env solve reports a version conflict that traces to **two or more already-published conda-forge feedstocks with mutually-incompatible pins** that neither the consumer nor you can reconcile. Examples:
- a cf `litellm` build baking `fastapi==0.124.4` while a consumer needs `fastapi>=0.135`;
- an observability cluster (`otel` / `traceloop-sdk` / `openinference-*` / `langchain`) with mutually-incompatible pins across its feedstocks.

**Diagnosis test**: drop the full env and solve each conflicting sub-cluster on conda-forge alone (`fastapi` + `litellm`; the otel/traceloop/openinference set; etc.). If each sub-cluster solves fine in isolation but the union does not, and the conflicting constraints come from **published feedstock pins you don't control**, it's external skew — resolution requires **feedstock-level pin convergence upstream**, which is out of scope for the consumer recipe.

**Action**: do NOT loosen, force, or work around the pins in the consumer recipe (that hides the skew and ships a recipe that can't actually install). Instead:
1. Record the conflicting packages **and their exact pins** in the recipe's `cfe-forge-blocker-list`.
2. Set `cfe-on-conda-forge-status: blocked-pending-prerequisites`.
3. **STOP** — report the blocker; the fix is an upstream feedstock pin bump, not a consumer edit.

**Case study**: langflow (Jun 19, 2026) — reached build-GREEN locally, but its full test-env solve was blocked by irreducible cf ecosystem skew across `lfx` / `litellm` / `traceloop` (fastapi + observability-cluster pin conflicts). Each sub-cluster solved in isolation; the union did not. Documented in `cfe-forge-blocker-list` and stopped — no consumer churn.

---

## Pre-PR Quality Gate Checklist

Run this checklist from `shipping-and-launch` before calling `submit_pr`:

**Recipe Correctness**
- [ ] `validate_recipe` passes with zero errors or warnings (fast pass; env conda-smithy is 3.62.0)
- [ ] **CI-parity lint clean**: `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/<name>` — the CURRENT conda-smithy the webservice uses; authoritative, never dismiss its lints ([G65](#g65-local-vs-ci-linter-parity--lint-with-the-current-conda-smithy-via-pixi-exec-and-run-the-linterpy-checks-conda-smithy-doesnt))
- [ ] `optimize_recipe` passes with zero check-code warnings
- [ ] `check_dependencies` resolves all deps on conda-forge; for **compiled** transitive deps, G40 per-subdir repodata check (host-only build won't catch osx/win-only gaps)
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
- [ ] **No `cfe-*` keys or `# CFE` blocks in the PUSHED recipe** — grep-verified on the fork branch, not assumed ([G62](#g62-never-ship-cfe-metadata--the-strip-is-mandatory-and-must-be-verified-on-the-pushed-artifact-verify-dont-assume))
- [ ] (Optional) per-recipe `conda-forge.yml` ships `azure.store_build_artifacts: true` if you want the upstream PR's Azure run to retain downloadable `.conda` artifacts
- [ ] `submit_pr(dry_run=True)` passes all prerequisite checks
- [ ] **PR body uses the conda-forge template with the checklist completed** — fetch the live `.github/pull_request_template.md`; a custom `--body` REPLACES the template ([G63](#g63-open-staged-recipes-prs-with-the-conda-forge-template--completed-checklist--body-replaces-the-template-it-does-not-merge))
- [ ] **After CI is all-green AND the PR is not a draft: request review exactly once** via the language team (`@conda-forge/help-python` for pure-Python noarch) — but **check first** and skip if the PR is a draft or already has the `review-requested` label ([G64](#g64-request-review-with-one-language-matched-ping-after-ci-is-all-green--and-check-the-prs-labels-first-the-bots-labels-are-the-dedup-signal))

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

**Local-mirror fidelity — keep the feedstock's `meta.yaml` until the feedstock itself migrates.** For a `recipes/<name>/` that mirrors an existing conda-forge feedstock still on v0: **pull the latest `meta.yaml` from the feedstock and KEEP it**, AND **author the v1 `recipe.yaml`** alongside it (our local v1 — built/tested locally, and the proposed migration). **Both files coexist** in `recipes/<name>/`: `meta.yaml` faithfully mirrors what's actually deployed; `recipe.yaml` is the v1 we maintain. **Delete `meta.yaml` only after the feedstock itself completes the v0→v1 switch** (its migration PR merges) — NOT when the local build succeeds. (Leave `meta.yaml` in place — build / test / lint / optimize by pointing explicitly at `recipe.yaml` (`rattler-build --recipe recipes/<name>/recipe.yaml`), which reads only that file and ignores `meta.yaml`. No stashing. `optimize_recipe`'s STD-002 "both meta.yaml and recipe.yaml present" is an expected, harmless warning for a v0-mirror — not a defect; don't delete `meta.yaml` to silence it.) The CFE metadata lives in the `recipe.yaml` (the `meta.yaml` stays a faithful, un-annotated upstream copy): for a still-v0 feedstock mirror the `recipe.yaml` carries `cfe-on-conda-forge-status: confirmed-on-conda-forge` (it IS published, just on v0), `cfe-forge-recipe-updates-needed:` including **`meta-yaml-to-recipe-yaml`** (the feedstock owes the migration), and a correct `cfe-forge-blocker-list:`. New recipes with no feedstock yet are v1 `recipe.yaml` only — nothing to mirror.

### Migration Steps (Strangler Pattern)

1. Run `migrate_to_v1(recipe_path="recipes/<name>")` — creates `recipe.yaml`, preserves `meta.yaml`
2. Run `validate_recipe` on the new `recipe.yaml` — fix all errors before proceeding
3. Run `optimize_recipe` — fix all check-code warnings
4. Run `trigger_build` — verify a clean build with the new format
5. Remove `meta.yaml` only after step 4 succeeds — never before
6. Confirm `check_dependencies` still resolves all deps

**Churn Rule**: You own verifying the migration is complete. A `meta.yaml` left alongside a `recipe.yaml` after a successful build is a bug — clean it up. **Exception**: a local mirror of a feedstock still on v0 deliberately keeps BOTH (`meta.yaml` = deployed state, `recipe.yaml` = our v1) until the feedstock migrates — see § When to Migrate's local-mirror fidelity rule.

### Migration Discipline

Five points learned the hard way from feedstock v0→v1 migrations. Full expansion in [`guides/migration.md`](guides/migration.md) § "Migration Discipline".

- **`package.name:` MUST match the feedstock identity, not the local folder name.** When migrating an existing feedstock, the conda-forge package on the channel is the canonical name (e.g. feedstock `python-confluent-kafka-feedstock` ships package `python-confluent-kafka`). The local-recipes folder often mirrors the upstream GitHub repo name (e.g. `recipes/confluent-kafka-python/` after the GitHub repo). The v1 `package.name:` MUST match the feedstock's existing package name — changing it during migration creates a parallel package and orphans existing users. Verify via `lookup_feedstock(pkg_name=<conda-forge-name>)` before pushing the fork branch.

- **Bump `build.number` on same-version v0→v1 swap.** When the migration ships against the same upstream version that's currently shipping (no version bump), `build.number` MUST increment (typically `0 → 1`). This keeps existing `<pkg> <ver> *_0` artifacts on a distinct hash from the v1-built `<pkg> <ver> *_1` and lets the conda solver pick the newer build. If the migration is bundled with an upstream version bump, the build number resets to 0 — the version bump itself provides the hash separation.

- **Stash `meta.yaml` aside during local validation, don't pre-delete.** `optimize_recipe` fires `STD-002` "Both meta.yaml and recipe.yaml exist in the same directory" while both files coexist, and some local-recipes pixi tasks get confused by mixed format. The practical pattern: `mv meta.yaml meta.yaml.bak` for the validate + build pass, then restore. Drop `meta.yaml` only when committing to the feedstock fork (where v0 is genuinely retired). Keeping the v0 copy locally is a useful pre-migration reference until the feedstock PR merges; delete from the local mirror at PR-merge time, not earlier.

- **`conda_build_tool: rattler-build` MUST ship paired with `conda_install_tool: pixi`.** Adding `conda_build_tool: rattler-build` to `conda-forge.yml` is required for CI to use the v1 parser; pair it with `conda_install_tool: pixi` (the canonical 2026 companion that tells CI to use pixi for env installs, faster than micromamba and matches conda-forge's 2026 standardization). Both keys land in the same PR that drops `meta.yaml`. The v0→v1 PR also requires `@conda-forge-admin, please rerender` — the CI scripts need regenerating to invoke rattler-build instead of conda-build.

- **`pip_check: true` on first-time enablement may surface "new" runtime deps.** Many older meta.yaml v0 recipes don't have `pip check` in `test:`; CFEP-25's v1 triad (and the canonical noarch:python test block) turns it on by default. When migrating, expect to discover transitive deps that upstream's PEP-508 markers introduced post-original-feedstock-creation. Fix by adding the missing deps to `requirements.run:` (preferring unconditional listing over PEP-508-marker-gated conda-forge selectors for single transitive deps — minor runtime overhead, simpler recipe). Case: python-confluent-kafka v0→v1 surfaced upstream's `typing-extensions ; python_version < "3.11"` marker; shipped `typing_extensions` unconditionally in `run:`.

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
  version: "1.0.0"
  # Omit python_min when the conda-forge floor (3.10) is fine; only declare
  # when upstream's python_requires demands a higher floor.
package:
  name: my-package
  version: ${{ version }}
source:
  # Path segments are literal; only ${{ version }} interpolates.
  url: https://pypi.org/packages/source/m/my-package/my-package-${{ version }}.tar.gz
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
      imports: [my_package]
      pip_check: true
      python_version:
        - ${{ python_min }}.*
        - "*"
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
| `edit_recipe` | **Primary editing tool.** Four supported actions (per `scripts/recipe_editor.py`): `update` (set or *insert* a scalar at any path; `set_nested_item` uses `setdefault` so intermediate keys are created and a missing leaf is added cleanly), `add_to_list` (append item to an existing list at path), `remove_from_list` (remove item from an existing list at path), `calculate_hash` (refresh `sha256` in a `source:` block). For arbitrary key deletions OR multi-line block-scalar inserts (e.g., a `description: \|` body), fall back to direct `Edit`. **There is no `add` action** — SKILL.md v8.11.1 incorrectly listed it; corrected in v8.13.0 after empirical retest. | `edit_recipe('recipes/numpy/recipe.yaml', [{"action": "update", "path": "about.description", "value": "Short text"}])` (insert), `[{"action": "add_to_list", "path": "about.license_file", "value": "LICENSE.txt"}]` (append) |
| `get_conda_name` | Resolves a PyPI package name to its conda-forge equivalent (cache-first) | `get_conda_name(pypi_name="python-dateutil")` |

### Validation & Quality
| Tool | Description | Example |
|---|---|---|
| `validate_recipe` | Schema, license, checksums + `rattler-build lint` pass | `validate_recipe(recipe_path="recipes/numpy")` |
| `check_dependencies` | Verifies all deps exist on conda-forge. Batch repodata.json — fast, air-gapped-friendly, JFrog Artifactory-compatible | `check_dependencies(recipe_path="recipes/numpy")` |
| `optimize_recipe` | 18 check codes — **critical** (STD-001: compiler without stdlib; STD-002: format mixing; SCHEMA-001: missing v1 schema header), **security** (SEC-001: no sha256), **completeness** (MAINT-001: no maintainers; TEST-001: no tests; TEST-002: noarch:python tests pinned to a single Python version instead of `[python_min, "*"]` ([staged-recipes#32857 r3039190932](https://github.com/conda-forge/staged-recipes/pull/32857#discussion_r3039190932)); TEST-003: package_contents substituted for python.imports without justification; ABT-001: no license_file; ABT-002: v0 about-fields in v1 recipe; **LIC-001: secondary-source LICENSE pattern (3) detected, convert to in-recipe pattern (2)** [v8.12.0]), **formatting** (**FMT-001: list items indented at parent-key depth instead of 2 spaces deeper** [v8.12.0]), **quality** (DEP-001/002, PIN-001, SCRIPT-001/002, SEL-001/002/003) | `optimize_recipe(recipe_path="recipes/numpy")` |

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
- **A valid SPDX identifier is NOT the same as conda-forge eligibility.** Source-available / non-OSI licenses — **BUSL-1.1** (Business Source License), **SSPL**, **Elastic-2.0** (Elastic License 2.0), and **Commons-Clause**-encumbered licenses — are valid SPDX strings but are **not conda-forge-distributable** (they're not OSI-approved open-source licenses). A clean *local* build does **not** imply cf-eligibility. Flag these at recipe-authoring time as a **submission blocker**: record the reasoning in the `cfe-on-conda-forge-status` field and the bottom `# CFE comments` block (e.g. `cfe-status: local-only-pending-submission-conda-forge` with a note that the license bars submission), and do not open a staged-recipes PR. Real case: ragstack-ai-knowledge-store (BUSL-1.1, Jun 19, 2026) — built clean locally but is not cf-eligible.
- **Bundled-language licensing** (Rust, Go) — use `cargo-bundle-licenses` / `go-licenses` and ship a `THIRDPARTY.yml` alongside `LICENSE` (already encoded in the maturin and Go templates).

---

## Recipe Authoring Gotchas

Patterns that look right but fail silently or produce broken recipes. Each entry includes the symptom, why it happens, and the correct form. Case studies cited where relevant.

### G1. `script:` list entries run in separate shells — env vars do NOT carry across entries

**Symptom**: an `export FOO=bar` in one script entry has no effect in the next entry. `pip install` later in the script doesn't see `CFLAGS` you set earlier.

**Why**: rattler-build evaluates each top-level item under `build.script:` (when given as a YAML list) as an independent shell invocation. Shell state — env vars and function definitions — does not survive between entries.

**Caveat — CWD specifically *does* persist across entries.** Env vars and shell functions don't carry, but the current working directory does. If entry 1 ends with CWD inside a subdirectory, entry 2 starts there too. See **G13** for the cross-platform CWD-isolation pattern (pushd/popd) and the Windows cmd.exe `(...)` -is-not-a-subshell trap that makes naive bash subshell patterns fail on Windows.

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

**Symptom**: rattler-build builds the package without warning, but `about.dev_url`, `about.doc_url`, or `about.home` is missing from the resulting metadata. Users see incomplete project links on conda-forge.org.

**Why**: rattler-build's recipe-format schema only recognizes the v1 names (`repository`, `documentation`, `homepage`). Unknown keys under `about:` are accepted but discarded — no schema-validation error.

**Fix**: use the v1 names in any file with `schema_version: 1`. Reference: `reference/recipe-yaml-reference.md` and the [v0 ↔ v1 about-field mapping memory](../../memory/reference_v0_v1_about_fields.md). The optimizer's **ABT-002** check flags this in v1 recipes.

| v0 (meta.yaml) | v1 (recipe.yaml) |
|---|---|
| `home` | `homepage` |
| `dev_url` | `repository` |
| `doc_url` | `documentation` |

**`license_family` is NOT removed and NOT a rename.** It is a valid v1 `about:`
field — the `prefix-dev/recipe-format` schema lists it (description: *"deprecated,
but still used in some recipes"*) and it keeps the same name in v0 and v1. It
passes both rattler-build schema validation **and** conda-smithy lint as long as
its value is a recognized family: `conda_build.license_family.ensure_valid_license_family`
raises only on an *unrecognized* value (allowed: AGPL, LGPL, GPL, GPL2, GPL3,
BSD, MIT, APACHE, PSF, CC, MOZILLA, PUBLIC-DOMAIN, PROPRIETARY, OTHER, NONE), and
conda-smithy's `lint_license_family_should_be_valid` fires only when `license_file`
is *absent* — never on the field's presence. **For modernization, omit it**: it's
deprecated, and neither the CFE generator (`recipe-generator.py`) nor current
grayskull emits it; dropping a valid one is safe and more modern, keeping a valid
one won't fail lint. The complete v1 `about:` set is the 9 fields in
[`reference/recipe-yaml-reference.md`](reference/recipe-yaml-reference.md). (Earlier
versions of this gotcha wrongly listed `license_family` as "removed.")

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

### G6. npm packages with rich transitive deps ship `node_modules/.bin/` symlinks that fail noarch builds

**Symptom**: a `noarch: generic` npm recipe built with the canonical `npm pack` + `npm install --global` pattern produces a `.conda` archive but rattler-build then aborts with:

```
Error:   × Package <name> contains symlinks which are not supported on most
  │ Windows systems:
  │   - lib/node_modules/<name>/node_modules/.bin/ejs
  │   - lib/node_modules/<name>/node_modules/.bin/jake
  │   - lib/node_modules/<name>/node_modules/.bin/semver
  │   …
  │ To allow symlinks, use the --allow-symlinks-on-windows flag.
```

**Why**: npm installs each transitive dependency's executable as a symlink under that dep's `node_modules/.bin/`. For minimal-dep packages (e.g. `copilot-api`, `openspec`) this is empty or near-empty. For packages with rich runtime deps — Yeoman generators, anything pulling `ejs` / `jake` / `semver` / `yosay` / `@octokit/*` — dozens of internal symlinks land in the artifact. rattler-build's noarch validator rejects them as non-portable on Windows after writing the archive.

**Fix**: strip the internal `.bin/` directories after `npm install --global` but before `pnpm-licenses` runs. These symlinks are only used by `npm exec` inside the package's own `node_modules/`; the package's top-level CLI shim at `${PREFIX}/bin/<name>` is unaffected. For Yeoman generators specifically, the top-level `yo` runtime is what discovers and dispatches to generators, so dropping the internal `.bin/` directories is fully safe.

```bash
# In recipes/<name>/build.sh, after npm install --global:
find "${PREFIX}/lib/node_modules/<name>" -type d -name .bin -exec rm -rf {} +
```

The `--allow-symlinks-on-windows` rattler-build flag is a local-build escape hatch only — conda-forge staged-recipes CI does not pass it, so the strip is the durable fix. `--no-bin-links` on `npm install` is an alternative but disables top-level bin creation too, which breaks the CLI; the post-install `find -delete` is more surgical.

**Case study**: `generator-code` (VS Code Yeoman generator) local build, May 2026. yeoman-generator's transitive deps install bin shims for `ejs` / `jake` / `node-which` / `rc` / `semver` / `yosay` / `cross-spawn`. First build wrote `generator-code-1.11.18-hccbf638_0.conda` and was then rejected at the symlink-check stage. `yo` itself (built in the same session) had no such issue — its dep tree doesn't ship executable scripts. Fixed with a one-line `find ... .bin -exec rm -rf` between `npm install --global` and `pnpm install`; rebuilt clean (`-h5e06de4_0.conda`, 0 symlinks).

### G7. Grayskull's inferred Python import name can be wrong — verify against the sdist

**Symptom**: a recipe generated by `generate_recipe_from_pypi` passes `validate_recipe` and `optimize_recipe` but its test phase fails at runtime with:

```
ModuleNotFoundError: No module named 'microsoft_kiota_bundle'
```

The recipe's `tests[].python.imports:` entry mirrors the PyPI distribution name (with hyphens converted to underscores) but the package actually publishes a different top-level import.

**Why**: grayskull defaults the import test to a name derived from the PyPI distribution name (`microsoft-kiota-bundle` → `microsoft_kiota_bundle`). This is correct in the typical case (`numpy` distributes `numpy`, `pandas` distributes `pandas`) but wrong whenever upstream namespaces packages differently — common patterns include:

- **Re-exported short names** under an umbrella org (`microsoft-kiota-*` → `kiota_*`, `microsoft-kiota-bundle` → `kiota_bundle`, `microsoft-kiota-http` → `kiota_http`).
- **Dotted namespace packages** (`azure-identity-broker` → `azure.identity.broker`, `google-cloud-storage` → `google.cloud.storage`).
- **Renamed-on-PyPI** packages (`PyYAML` → `yaml`, `beautifulsoup4` → `bs4`, `protobuf` → `google.protobuf`).

In every case the only authoritative source is the sdist's top-level `__init__.py`, not the distribution name.

**Fix**: before trusting the generated test, list the sdist contents and grep for the top-level `__init__.py`:

```bash
curl -sL "https://pypi.org/packages/source/<first-letter>/<name>/<name>-<version>.tar.gz" -o /tmp/sdist.tgz
tar tzf /tmp/sdist.tgz | grep -E '__init__\.py$' | head -3
```

The first matching path's middle segment (e.g. `microsoft_kiota_bundle-1.10.1/kiota_bundle/__init__.py` → `kiota_bundle`) is the correct import name. For dotted namespaces, list the deepest `__init__.py` chain (e.g. `azure_identity_broker-1.3.0/azure/identity/broker/__init__.py` → `azure.identity.broker`).

Then edit the recipe to match — `imports: [<correct_name>]` — and re-validate. `pip_check: true` in the same test block will additionally catch entrypoint / dependency mismatches that the import alone would miss.

**Case study**: staged-recipes Microsoft Agents bundle (May 2026). Grayskull generated `imports: [microsoft_kiota_bundle]` for `microsoft-kiota-bundle` v1.10.1; the actual top-level package is `kiota_bundle` (matching the convention of every other already-shipped `microsoft-kiota-*` feedstock). Confirmed via `tar tzf microsoft_kiota_bundle-1.10.1.tar.gz | grep '__init__.py$'`; recipe edited to `imports: [kiota_bundle]` and built clean.

### G8. Grayskull adds redundant `wheel` + `setuptools` host deps for poetry-core projects

**Symptom**: a generated recipe whose `pyproject.toml` declares `build-system: requires = ["poetry-core"]` carries a host section like:

```yaml
requirements:
  host:
    - python ${{ python_min }}.*
    - poetry-core
    - wheel              # ← redundant
    - setuptools >=42.0.0 # ← redundant
    - pip
```

The build still works, but `optimize_recipe` doesn't flag it (today), reviewers tend to ask for cleanup, and `pip check` in some downstream environments warns about uninvoked build backends.

**Why**: grayskull is conservative — when it can't conclusively prove a backend is the only one needed, it adds the legacy pair `wheel` + `setuptools` as belt-and-suspenders. For PEP 517 projects with a single declared backend (`poetry-core`, `hatchling`, `flit-core`, `pdm-backend`, `scikit-build-core`), only that backend + `pip` is needed in `host:`.

**Fix**: when the recipe is generated, immediately inspect the sdist's `pyproject.toml` `[build-system] requires` list and drop any host entries not present there:

```bash
tar -xzOf /tmp/sdist.tgz "*/pyproject.toml" | grep -A 5 '^\[build-system\]'
```

For `build-system: requires = ["poetry-core"]` keep only `poetry-core` + `pip` in `host:`. For `hatchling`, just `hatchling` + `pip`. The pattern generalizes — verify against the actual `[build-system]` table, don't trust grayskull.

**Case study**: Microsoft Agents bundle (May 2026). Both `microsoft-agents-m365copilot-core` and `microsoft-agents-m365copilot` got the redundant pair from grayskull despite their `pyproject.toml` declaring only `poetry-core`. The third sibling, `microsoft-kiota-bundle`, was emitted clean (just `poetry-core` + `pip`) — grayskull's behavior is non-deterministic across runs. Worth always inspecting.

### G9. Monorepo upstreams may have no per-language Git tag — pin the LICENSE to a commit hash

**Symptom**: an upstream Python sdist ships no LICENSE (G4 applies, secondary GitHub source needed) **and** the repo's Git tag scheme doesn't match the Python release. The typical `https://raw.githubusercontent.com/<org>/<repo>/v${{ version }}/LICENSE` pattern returns 404 because no `vN.M.K` tag was ever pushed — the project tags only its JavaScript / .NET / Java releases under different names.

**Why**: large polyglot monorepos (Microsoft / Azure SDKs, Google APIs, Apache Foundation projects) often have per-language release pipelines that publish to language-specific registries (PyPI / npm / NuGet / Maven) without crossing into Git tags. Examples:

- `microsoft/Agents-M365Copilot` tags only JS releases: `@microsoft/agents-m365copilot-v1.6.0`, `@microsoft/agents-m365copilot-v1.5.0`, …. The Python `microsoft-agents-m365copilot` v1.6.0 has no corresponding Git tag.
- `Azure/azure-sdk-for-python` tags as `azure-<package>_<version>` (e.g. `azure-identity_1.18.0`), which works with the right URL template but is not `v${{ version }}`.

**Fix**: pin the LICENSE secondary source to a specific commit SHA + sha256, not a tag:

```yaml
source:
  # Primary: PyPI sdist (does NOT ship LICENSE).
  - url: https://pypi.org/packages/source/m/<name>/<name>-${{ version }}.tar.gz
    sha256: <sdist-sha>
  # Secondary: pin to a specific commit because no per-Python tag exists.
  # Bump the commit + sha256 together with the version on every update.
  - url: https://raw.githubusercontent.com/<org>/<repo>/<40-char-commit-sha>/LICENSE
    sha256: <license-sha>
    file_name: LICENSE
```

Pick the commit deliberately: the current `main` HEAD at recipe-creation time is fine (the LICENSE almost never changes), or the commit that landed the Python release if it can be identified from the release notes. Document the choice in the recipe via a comment and in the PR description so reviewers understand it's deliberate, not lazy.

Add a maintenance note to the PR description: **"On every version bump, the bot must also refresh the LICENSE commit SHA + sha256 — there is no per-Python tag to auto-track."** The autotick bot does not handle this today; without the note, a future version bump may carry a stale LICENSE pin.

**Case study**: staged-recipes Microsoft Agents bundle (May 2026). `microsoft-agents-m365copilot` v1.6.0 has no `python/v1.6.0` or `v1.6.0` tag on `microsoft/Agents-M365Copilot` — only `@microsoft/agents-m365copilot-v1.6.0` (JS). Pinned LICENSE to commit `0376aa418345d7f719b7b75d6e784fa7a765d9d0` with sha256 `c2cfccb812fe482101a8f04597dfc5a9991a6b2748266c47ac91b6a5aae15383`. `microsoft-agents-m365copilot-core` v1.0.0 sdist *did* ship LICENSE, so no secondary source was needed there — even within a single monorepo, the per-package pattern varies.

### G10. PyPI → conda-forge name divergence — verify across four spellings before declaring a dep missing

**Symptom**: a recipe-generation flow declares a `requirements.run:` dep "missing" from conda-forge because a manual repodata search for the literal PyPI distribution name returns 0 hits across every platform. grayskull's emitted `requirements.run:` carries the PyPI name; the conda-forge feedstock actually exists under a name with a `-py` or `-python` suffix, or with an unexpected hyphen↔underscore form.

**Why**: when upstream PyPI publishes a Python distribution whose bare name collides with — or could collide with — a non-Python package, conda-forge convention disambiguates by suffixing the feedstock name. The PyPI distribution stays under the bare name; the conda-forge feedstock adds a discriminator. There is no algorithmic rule — the choice of `-py` vs `-python` vs underscore-preserved vs bare is a per-feedstock decision. The `get_conda_name` mapping cache doesn't always capture either suffix form.

| PyPI distribution | conda-forge feedstock | Pattern | Why the divergence |
|---|---|---|---|
| `wasmtime` | `wasmtime-py` | `-py` suffix | Disambiguates the pyo3 Python binding from the underlying Rust WASM runtime, in case the runtime is ever packaged separately. |
| `langfuse` | `langfuse-python` | `-python` suffix | Disambiguates from upstream's polyglot SDK family (langfuse-js, langfuse-go, etc.); `-python` names the Python distribution explicitly. |
| `tree_sitter` | `tree_sitter` | underscore preserved (no suffix) | Binding + native C library ship in the same feedstock; no disambiguation needed. PyPI's underscore form carries straight through. |

The `-py` and `-python` forms tend to appear when the upstream project has a multi-language SDK family or a native runtime that conda-forge wants room to package separately. The underscore-preserved form appears when the binding and the native code ship in a single combined feedstock. **None of these are predictable from the PyPI name alone — you have to check.**

**Fix — before declaring a dep missing**: check four name forms in order before concluding a dep isn't on conda-forge:

1. The PyPI distribution name exactly (`wasmtime`, `langfuse`).
2. The name with `-` ↔ `_` swapped (`tree-sitter` ↔ `tree_sitter`).
3. The name with a `-py` suffix (`wasmtime-py`).
4. The name with a `-python` suffix (`langfuse-python`).

`check_dependencies` does this lookup correctly via the grayskull mapping cache; manual repodata searches by literal name miss every suffix form. If a dep isn't on conda-forge after all four checks, then it's genuinely missing — at that point the scoping decision (package the prerequisite first vs. defer) is real.

**Fix — in the recipe**: edit `requirements.run:` to use the conda-forge feedstock spelling. grayskull emits the PyPI name (`wasmtime`, `langfuse`); the recipe must hand-edit to the feedstock spelling (`wasmtime-py`, `langfuse-python`). The optimizer doesn't catch this divergence today — closing that gap is open work (proposed `DEP-005` "PyPI name in run requirements has a `-py` or `-python` feedstock on conda-forge").

**Case study 1** (`-py` suffix): scoping pass for `simonw/micropython-wasm` (Jun 7, 2026). Initial manual repodata search for `wasmtime` across noarch + linux-64 + osx-64 + osx-arm64 + win-64 + linux-aarch64 + linux-ppc64le returned 0 hits in all 7 subdirs; concluded `wasmtime` was missing and proposed a two-recipe bundle. User pointed at `conda-forge/wasmtime-py-feedstock`; re-check by feedstock name confirmed 39 builds × 5 platforms at v45.0.0. The hand-edit `requirements.run: [..., wasmtime-py]` was the only change to grayskull's output.

**Case study 2** (`-python` suffix): suitenumerique build-report audit (Jun 7, 2026). The 2026-05-31 SUITENUMERIQUE_SUMMARY.md listed `langfuse` as a Wave-1b conda-forge-submission-ready recipe ("not on conda-forge — clean candidate"). Re-check on user prompt found `conda-forge/langfuse-python-feedstock` at v4.7.1 (matching PyPI `langfuse` 4.7.1; 61 noarch builds; recipe `source.url: pypi.org/packages/source/l/langfuse/langfuse-${{ version }}.tar.gz` confirms identity). The local-recipes `recipes/langfuse/` build was redundant for submission; Wave-1b count dropped 13 → 12.

Auto-memory `feedback_pypi_conda_mapping_unreliable.md` is the live cross-skill reference for this multi-form check; it carries all three confirmed patterns.

### G11. PyPI sdist symlinks fail hatchling's wheel build on Windows

**Symptom**: a `noarch: python` recipe builds cleanly on linux_64 + osx_64 but fails on win_64 during hatchling's wheel-build phase with:

```
OSError: [WinError 123] The filename, directory name, or volume label syntax is incorrect:
  'D:\bld\bld\rattler-build_<name>_<id>\work\<path>\conftest.py'
pip._internal.exceptions.MetadataGenerationFailed: metadata generation failed
```

The recipe is otherwise correct, deps resolve, build succeeds in isolation on Linux + macOS.

**Why**: the upstream PyPI sdist ships POSIX symlinks via tar's symlink record. Linux + macOS build agents extract them as real symlinks and `os.stat` follows them transparently. Windows Azure Pipelines runners lack `SeCreateSymbolicLinkPrivilege` by default, so tar's symlink-extraction falls back to writing a text stub containing the literal target path (e.g. `../../../some/path`). `os.stat` on that stub fails — Windows parses the content as a malformed path and returns `WinError 123 / ERROR_INVALID_NAME`. Hatchling iterates every included file during the wheel build and calls `os.stat` on each one, so the first symlink in iteration order triggers the failure.

This is distinct from **G6** (npm `node_modules/.bin/` symlinks): G6 fires at rattler-build's noarch-Windows-portability check *after* the wheel is built; G11 fires *during* hatchling's wheel build itself (pre-validation).

**Fix**: extend the recipe's downstream pyproject.toml patch with a `[tool.hatch.build.targets.wheel]` `exclude:` entry for the offending symlinked path:

```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -8,6 +8,7 @@
 # wheel ZIP).  By excluding here we ensure only force-include writes the files.
 exclude = [
     "python/<name>/env_templates/**",
+    "python/<name>/<offending>/conftest.py",
 ]
```

The symlink target file usually still ships under its real path elsewhere in the wheel, so test discovery for the target's tests still works. Exclude each symlinked path explicitly — broad `**/conftest.py` globs strip more than needed and break test discovery for unrelated test packages.

**How to detect upstream symlinks before pushing to CI**:

```bash
curl -sL "https://pypi.org/packages/source/<x>/<name>/<name>-<version>.tar.gz" \
  | tar tvz - | grep '^l'
```

`tar tvz` lists entries with their type — symlinks appear as `lrwxr-xr-x ... -> <target>`. Run on every new noarch:python recipe to flag the symlink risk before the staged-recipes push.

**Case study**: staged-recipes PR #33534 (xorq 0.3.26, Jun 7, 2026). Two consecutive CI runs (Azure buildId 1533937 + 1533940) failed at the same line of the same log with `OSError: [WinError 123] ... 'D:\bld\bld\rattler-build_xorq_<id>\work\python\xorq\common\utils\tests\conftest.py'`. Inspection via `tar tvzf` revealed exactly one symlink: `python/xorq/common/utils/tests/conftest.py` → `../../../backends/xorq_datafusion/tests/conftest.py`. The target file `python/xorq/backends/xorq_datafusion/tests/conftest.py` was a normal file in the same sdist. Patch added the symlinked path to the existing `[tool.hatch.build.targets.wheel]` exclude list (alongside `python/xorq/env_templates/**`); next CI run (Azure buildId 1533952) was win_64 GREEN. Target's tests still discoverable via the surviving target file.

### G12. Platform-conditional `run:` deps in noarch:python recipes need `noarch_platforms` in `conda-forge.yml`

**Symptom**: a `noarch: python` recipe uses the canonical rattler-build v1 `if: linux / then:` selector to gate a Linux-only runtime dep, and conda-smithy lint hard-fails on staged-recipes-linter with:

```
❌ noarch packages can't have selectors. If the selectors are necessary, please remove noarch: python.
```

rattler-build itself accepts the selector (`rattler_lint_ran: true` in `validate_recipe` returns clean) — this is purely a conda-smithy lint rule, code `R1-002` (`lint_noarch_selectors`).

**Why**: the lint rule exists to catch *build-time* selector mistakes in noarch recipes (selectors in `build.script:`, `build.skip:`, `requirements.host:`, `requirements.build:` produce broken artifacts because there's only one noarch build). But the rule fires on *runtime* selectors in `requirements.run:` too, even though those are evaluated at install time by the conda solver and are semantically correct.

The v1-specific implementation of the rule (`lint_recipe_v1_noarch_and_runtime_dependencies` in `conda-smithy/linter/`) has a documented escape hatch: when the recipe's `conda-forge.yml` declares `noarch_platforms` with **>=2 entries**, the lint gate flips from "no selectors allowed in noarch" to "selectors are OK because the author has tested cross-platform". This is the canonical design — *not* a `linter.skip` opt-out.

**Fix**: drop a `conda-forge.yml` next to `recipe.yaml` listing every platform you have verified the selector resolves correctly on:

```yaml
# recipes/<name>/conda-forge.yml
noarch_platforms:
  - linux_64
  - osx_64
  - win_64
```

The minimum for the gate flip is 2 platforms. List only what you've verified — adding `win_64` when the recipe has unresolved Windows issues will trigger CI on Windows and produce a different failure.

**When NOT to use this**: if your selectors are in build-time fields (`build.script:`, `build.skip:`, `requirements.host:`, `requirements.build:`), the noarch artifact really IS broken on at least one platform — the lint is correctly rejecting your recipe. Either remove `noarch: python` and produce per-platform builds, or restructure so the build is platform-independent.

**Case study**: staged-recipes PR #33534 (xorq 0.3.26, Jun 7, 2026). After landing G11's symlink patch and adding an `if: linux / then:` selector to gate `git-annex` (which has 139 conda-forge linux-64 builds + zero on every other platform), the next CI run fired R1-002 on the linter. Research subagent traced the rule to `conda_smithy/linter/lint_recipe.py` line 302 (`if "lint_noarch_selectors" not in lints_to_skip`) with the v1 path in `conda_recipe_v1_linter.py` → `lint_usage_of_selectors_for_noarch()` and message class `NoarchSelectorsV1`. Adding `recipes/xorq/conda-forge.yml` with `noarch_platforms: [linux_64, osx_64, win_64]` (all three because the symlink patch made Windows viable) flipped the lint on the subsequent push. Final CI run (head `0be2b938e4`) went all-green across linter + conda-forge-linter + linux_64 + osx_64 + win_64. Two-commit fix sequence on top of the existing PR head: `ffbe7aa174` (selector + symlink patch) → `0be2b938e4` (conda-forge.yml).

**Refinement (opik #33936, Jun 26 2026) — the `noarch_platforms` escape hatch does NOT reliably silence the `conda-forge-linter` *webservice*; PREFER eliminating the selector (G35).** opik (noarch) carried `if: not (linux and aarch64) then: [tree_sitter, tree-sitter-javascript, tree-sitter-typescript]` + a `conda-forge.yml` with `noarch_platforms` (5 platforms). `validate_recipe` flagged `noarch packages can't have selectors`; it was **wrongly dismissed as the G12 false-positive** (xorq pattern). On CI the GHA `linter` passed but the **`conda-forge-linter` webservice STILL flagged the selector** → red PR. Lessons:
- The `noarch_platforms` escape hatch is **not dependable for the conda-forge-linter webservice** (it worked for xorq's `if: linux`, not for opik's `if: not (...)`). **Do NOT treat `validate_recipe`'s "noarch … can't have selectors" as a guaranteed false-positive** — verify, don't assume.
- **Prefer ELIMINATING the selector (G35) over relying on `noarch_platforms`.** Most noarch run-selectors excluding a dep on `linux-aarch64` track the **upstream PyPI musllinux_aarch64 WHEEL gap**, not conda availability. Check per-subdir repodata (`curl -s conda.anaconda.org/conda-forge/<subdir>/repodata.json` — mind the `_`-vs-`-` conda name, [G10](#g10-pypi--conda-forge-name-divergence--verify-across-four-spellings-before-declaring-a-dep-missing)): if conda-forge ships the dep on **all** subdirs, make it **unconditional** and delete the `conda-forge.yml` → no selector → green on *both* linters, installable everywhere. Keep a noarch run-selector + `noarch_platforms` ONLY when the dep is **genuinely absent** on conda-forge for some platform. opik: all three tree-sitter pkgs are on every subdir incl. linux-aarch64 → dropped the selector, removed `conda-forge.yml` → both linters green.

**Why local gates "miss" issues the CI linter/builds catch** (answers the recurring "why didn't local lint/build catch this before I pushed?"): two distinct mechanisms — (1) `validate_recipe` runs conda-smithy lint and **does** catch noarch-selector / many lints; the opik miss was a **judgment error** (overriding a real lint as a false-positive), not a tooling gap — never dismiss a `validate_recipe` lint without proof. (2) Local `recipe-build` / `validate` run on the **HOST platform only** (linux), so **per-platform** problems can't surface locally — e.g. opik's osx-64 test-env solve failing because `litellm → fastuuid` ships no osx-64 py3.10 build ([G40](#g40-a-dependency-can-drop-a-python-version-in-a-newer-release--a-noarch-consumers-declared-floor-then-cant-resolve-the-deps-latest-build-refines-g38)/[G61](#g61-github-commit-archive-archivecommittargz-sha256-can-drift--github-re-gzips-breaking-the-recorded-checksum)). conda-forge CI builds every subdir, so it finds them. Mitigations: trust `validate_recipe` lints; and for any recipe whose deps include **compiled** transitive packages, run the G40 per-subdir repodata check (each platform has a `pyXY` build at the floor) BEFORE submitting rather than discovering it on CI.

### G13. CWD persists across `script:` list entries — and `(cmd)` is not a subshell on Windows cmd.exe

**Symptom**: a multi-entry `build.script:` list works on Linux + macOS but on Windows the second entry fails with `Directory '.' is not installable. Neither 'setup.py' nor 'pyproject.toml' found.` (or similar CWD-confused error). The first entry uses a `cd subdir && ...` pattern, sometimes wrapped in `(parens)` to "isolate" the change.

**Why** (two interlocking facts the skill didn't previously capture):

1. **rattler-build's script-list entries share CWD across entries.** G1 documents that environment variables don't carry across entries — but CWD specifically *does* carry. If entry 1 ends with CWD inside a subdirectory, entry 2 starts there. (Verified empirically on solvor PR #33647 buildId 1534140 Windows leg; also reproduced on local Linux builds.)

2. **On Windows cmd.exe, `(cmd1 && cmd2)` is command grouping, not a subshell.** On bash, `(cd dir && do_thing)` runs the entire group in a child process — the `cd` only affects that child, so when control returns to the parent shell, CWD is unchanged. On cmd.exe, `(...)` is purely syntactic grouping (parentheses associate the AND chain) — there is no child process, so the `cd` permanently changes the parent shell's CWD. The same recipe that "works" on Linux is broken on Windows.

**Fix**: use `pushd` / `popd`, which work identically in both bash AND cmd.exe — `pushd dir` changes CWD and pushes the previous CWD onto a stack; `popd` restores it. Both shells implement this the same way, and the recipe stays one source for all three platforms:

```yaml
build:
  script:
    # Cross-platform CWD isolation across script-list entries.
    - pushd subdir && some_tool --output ../result.yml && popd
    - ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```

Forward slashes in the relative output path (`../result.yml`) work on both shells; cmd.exe accepts `/` as a path separator in this context. No `if: unix / then / else:` block is needed.

**Alternative**: collapse the two entries into one long-form entry with a single shell invocation. This sidesteps CWD-persistence entirely (CWD changes are scoped to that one entry by definition):

```yaml
build:
  script:
    - if: unix
      then: |
        cd subdir
        some_tool --output ../result.yml
        cd ..
        ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
      else: |
        pushd subdir
        some_tool --output ../result.yml
        popd
        "%PYTHON%" -m pip install . -vv --no-deps --no-build-isolation
```

The pushd/popd form (preferred) is shorter and avoids platform forking. Use the collapsed-entry form only when entries need shell-specific syntax beyond CWD.

**When this comes up in practice**: any maturin/PyO3 recipe whose `[tool.maturin].manifest-path` points at a Cargo.toml in a subdirectory (e.g. solvor's `rust/Cargo.toml`). `cargo-bundle-licenses` does not have a `--manifest-path` flag — it operates on whichever directory it's invoked from. So the recipe must `pushd` to the Cargo.toml's directory before invoking, write `THIRDPARTY.yml` back up via `--output ../THIRDPARTY.yml`, and `popd` before the pip step.

**Case study**: staged-recipes PR #33647 (solvor 0.6.2, Jun 7, 2026). Initial fix to a `cargo-bundle-licenses` Cargo-not-found error used a bash-subshell pattern: `- (cd rust && cargo-bundle-licenses --format yaml --output ../THIRDPARTY.yml)`. Local Linux build succeeded; Windows CI buildId 1534140 failed at line 1106 of the log with `pip._internal.exceptions.InstallationError: Directory '.' is not installable. Neither 'setup.py' nor 'pyproject.toml' found.` (the cmd prompt visible in the log was `(base) %SRC_DIR%\rust>...`, confirming CWD had leaked into the pip step). Replaced with `pushd rust && cargo-bundle-licenses --format yaml --output ../THIRDPARTY.yml && popd`; subsequent CI run on `efd84c9ee6` went all-green across linter + linux_64 + osx_64 + win_64.

### G14. Autotick bot v0 version bumps can fail the conda-forge-linter `package.version` float-parse rule

**Symptom**: a `[bot-automerge] <pkg> vX.Y` PR from `regro-cf-autotick-bot` against a v0 (`meta.yaml`) feedstock fails the conda-forge-linter check with:

> ❌ `package.version has a value that is interpreted as a floating-point number. Please quote it (like "0.14" or "{{ var }}") to ensure that it is interpreted as string and preserved exactly.`

The Linux build itself passes; only the linter blocks. With `bot.automerge: true`, the bot still refuses to merge because lint=failed.

**Why**: the lint runs *after* jinja rendering. The autotick bot edits `{% set version = "0.14" %}` (correctly quoted at the jinja level) but does NOT change the YAML-level template:

```yaml
package:
  name: {{ name|lower }}
  version: {{ version }}     # ← renders to: version: 0.14
```

YAML then types the rendered value: `0.14` (bare) → float; `"0.14"` (quoted) → string. The lint correctly flags the float interpretation because PyPI versions like `1.0` could collapse to `1` (an integer) and lose precision in extreme cases. For most versions it's only a type-mismatch, but the rule fires either way.

This affects already-merged v0 recipes whose `package.version` was never quoted at the YAML level — the original submission may have passed because the lint rule was added later. The next autotick bump exposes the issue.

**Fix — minimal, keep v0**: quote `package.version` at the YAML level:

```yaml
package:
  name: {{ name|lower }}
  version: "{{ version }}"     # ← keeps the string type after rendering
```

The jinja `{% set version = "X.Y" %}` line stays unchanged. The double quotes around `{{ version }}` survive jinja and become YAML quotes, so the rendered value is `version: "0.14"`.

**Long-term fix — migrate to v1**: v1 recipe.yaml uses `${{ version }}` substitution and the v1 parser preserves the original string type by construction. The float-parse class of bugs simply doesn't exist on v1. If the maintainer is already touching the recipe to fix this lint, it's often the right moment to also do the v0 → v1 migration (per the Migration Protocol).

**Case study**: feedstock PR #8 on `conda-forge/wagtail-ab-testing-feedstock` (Jun 7, 2026) — autotick bot bumped `0.13` → `0.14` and the conda-forge-linter blocked with the float-parse message. v0.13 had presumably passed when the recipe was first submitted; the lint rule was added or tightened since. Local fix went straight to v1: wrote `recipe/recipe.yaml`, updated `conda-forge.yml` with `conda_build_tool: rattler-build`, deleted `recipe/meta.yaml` after a clean v1 build (`wagtail-ab-testing-0.14-pyhcf101f3_0.conda`, 148 KiB), and aligned `conda-forge.yml` with the python-cityhash template (`bot.check_solvable`, `bot.run_deps_from_wheel`, `conda_install_tool: pixi`). The float-parse issue can't recur on v1.

### G15. Rebuilding the same recipe re-hashes the `.conda` artifact but leaves `repodata.json` stale

**Symptom**: a downstream recipe's build (or test) fails with:

```
× failed to fetch <pkg>-<ver>-<build>.conda
  ├─▶ failed to interact with the package cache layer.
  ╰─▶ hash mismatch when extracting file:///.../build_artifacts/.../<pkg>-<ver>-<build>.conda:
      expected <SHA-A>, got <SHA-B>, total size NNNN bytes
```

The downstream recipe references the dep correctly; the artifact exists on disk at the expected path; nothing in the recipe is wrong. The mismatch is purely between the on-disk `.conda` file and the channel's `repodata.json` record.

**Why**: rattler-build embeds the build timestamp into the `.conda` zip's central directory. A second build of the *same recipe sources* on the same machine produces an artifact with **identical contents but different bytes** (the embedded timestamp differs), so its sha256 differs from the first build. rattler-build's normal write path is atomic — it writes the new artifact AND updates `repodata.json` to point at the new hash. But the failure mode appears when:

1. The first build produces `pkg-1.0.0-h00.conda` with sha256 A and writes A into `repodata.json`.
2. A second `rattler-build build` invocation on the same recipe overwrites the artifact with sha256 B but the `repodata.json` update path doesn't fire (rattler-build's internal index cache thinks A is current; or the index step is skipped because nothing's "changed").
3. A downstream build resolves the dep via repodata → expects A → reads the file → gets B → hash mismatch error.

The most common trigger in this skill's workflow is verifying a green build by re-running `pixi run -e local-recipes rattler-build build --recipe recipes/X/recipe.yaml ...` twice — once to capture the build summary, a second time to grep for `✔ all tests passed!`. The second run silently invalidates the channel for any other recipe depending on X.

**Fix**: delete the on-disk artifact, then rebuild — rattler-build writes the new artifact AND updates `repodata.json` atomically on a fresh build (vs. an idempotent re-run):

```bash
# Delete the stale artifact + force a fresh build that re-indexes
rm build_artifacts/<config>/noarch/<pkg>-<ver>-<build>.conda
pixi run -e local-recipes rattler-build build --recipe recipes/<pkg>/recipe.yaml \
  --variant-config .ci_support/<config>.yaml \
  --variant-config .pixi/envs/local-recipes/conda_build_config.yaml \
  --output-dir build_artifacts/<config>
```

The rebuild produces the same byte-equivalent artifact (modulo timestamp), but this time `repodata.json` is updated to match. The downstream build then resolves cleanly.

**Don't use** `pixi run rattler-index` — the task isn't bound in this skill's pixi env. `rattler-index fs <channel-path>` is a real subcommand but invoking it through the unconfigured pixi task just dumps the task list. The rebuild path above is the practical re-index.

**When this comes up in practice**: cross-package local fix workflows. v8.2.0 documented the `native-build.sh` auto-channel-injection feature — when recipe B has `run: A` and A was just built locally, the build of B auto-prepends `file://${REPO_ROOT}/build_artifacts/<config>` to `channel_sources`. The auto-inject is correct, but it relies on `repodata.json` being current. Rebuilding A invalidates this contract.

**Case study**: `ag-ui-langgraph 0.0.41` fix session, Jun 9, 2026. Bumped `ag-ui-a2ui-toolkit` 0.0.2 → 0.0.3, built it (first build wrote artifact + indexed). Then ran the same build command a second time to capture `✔ all tests passed!` in a grep-friendly form — that second build wrote new artifact bytes but the repodata still referenced the first build's hash. The `ag-ui-langgraph 0.0.41` build then failed at the test phase with the exact `hash mismatch when extracting file://.../ag-ui-a2ui-toolkit-0.0.3-pyhc364b38_0.conda: expected 85ea90d5..., got 766570d75...` error. Fix: `rm` the stale artifact, rebuild ag-ui-a2ui-toolkit — repodata refreshed in step. Downstream ag-ui-langgraph build then resolved 0.0.3 cleanly and tests passed.

### G16. PyPI Varnish CDN degradation on `/packages/source/<letter>/...` route

**Symptom**: rattler-build's source fetch fails with `HTTP status server error (503 Service Unavailable)` when downloading from `https://pypi.org/packages/source/<letter>/<name>/<sdist>` — the canonical URL pattern conda-forge mandates. The same artifact at `https://files.pythonhosted.org/packages/<2-char>/<2-char>/<long-hash>/<sdist>` returns 200. Sustained — observed >12 min on 2026-06-11 for `lyric-task` 0.1.7. PyPI's `Retry-After` header is `0` (suggesting transient cache miss) but reality is a sustained route degradation.

**Why**: `pypi.org/packages/source/...` goes through PyPI's Varnish CDN edge layer for cache + routing. `files.pythonhosted.org/packages/<hash>/...` is the backing CDN (Fastly historically) and serves the same bytes. When Varnish has cache-routing issues, the `pypi.org` route returns 503 while the backing CDN keeps serving.

**Workaround**: URL-swap the recipe's `source.url` temporarily for the local build only.

1. Edit `source.url` to the `https://files.pythonhosted.org/packages/<hash>/<sdist>` form. The sha256 stays unchanged (identical bytes); `validate_recipe` won't complain.
2. Build green via `recipe-build`.
3. **REVERT** `source.url` to the canonical `https://pypi.org/packages/source/<letter>/...` form before pushing the fork. The submitted recipe ships canonical; conda-forge CI uses its own infrastructure unaffected by today's Varnish issue.
4. Re-run `validate_recipe` + `optimize_recipe` post-revert to confirm the recipe is still clean.

**Risk**: forgetting to revert leaves the recipe with a non-canonical URL that bypasses JFrog Artifactory PyPI Remote Repository proxies in air-gapped environments (SKILL.md "PyPI `source.url` Must Use the `pypi.org/packages/...` Pattern" critical constraint). Always re-validate after the revert.

**Detection at scale**: `curl -sI 'https://pypi.org/packages/source/<letter>/<name>/<sdist>'` returns 503 while `curl -sI 'https://files.pythonhosted.org/packages/<hash>/<sdist>'` returns 200 → Varnish issue, not a bytes issue. PyPI status page (`status.python.org`) lags real outages by several minutes — trust the dual probe.

**Case study**: S3 `lyric-task 0.1.7` build (2026-06-11). PyPI `/packages/source/l/lyric-task/lyric_task-0.1.7.tar.gz` returned 503 for >12 min; backing CDN at `files.pythonhosted.org/packages/1d/ff/.../lyric_task-0.1.7.tar.gz` returned 200 throughout. URL-swap workaround applied; build green at 14.62 KiB; URL reverted; `validate_recipe` + `optimize_recipe` clean post-revert; fork pushed.

### G17. `pnpm install --ignore-scripts` doesn't suppress the root project's lifecycle scripts

**Symptom**: a Node-workspace recipe (pnpm monorepo with a custom `postinstall: node ./scripts/postinstall.mjs`) is set up with `pnpm install --ignore-scripts --filter '@org/<app>...'` to skip sibling-workspace builds — but the root `postinstall` runs anyway and fails. Typically the failure is that the upstream's `postinstall` script tries to build sibling workspaces whose dependencies the filtered install didn't fetch:

```
. postinstall$ node ./scripts/postinstall.mjs
. postinstall: > @org/sibling@X.Y.Z build /path/to/packages/sibling
. postinstall: > node ./esbuild.config.mjs && tsc -p tsconfig.json --emitDeclarationOnly
. postinstall: Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'esbuild' imported from /packages/sibling/esbuild.config.mjs
```

**Why**: pnpm's `--ignore-scripts` only suppresses **dependency** install scripts (i.e. `node_modules/<dep>/package.json` lifecycle scripts). The **root project's** own `pre*` / `post*` lifecycle scripts run regardless. This is documented but counter-intuitive — recipe authors often think `--ignore-scripts` is the global "no scripts" switch. It is not. The behavior is consistent with npm too; both tools draw the same dependency-vs-root distinction.

A common case: an upstream monorepo's root `postinstall` builds every workspace under `packages/*` + `tools/*` (electron-builder workflows, codegen for sibling apps, native-addon prebuilds). A recipe that only ships one app (`apps/<daemon>`) uses `--filter '@org/<daemon>...'` to skip the heavyweight sibling workspaces — but the root `postinstall` still tries to build them and fails because their deps weren't fetched.

**Fix**: strip the root project's `postinstall` from `package.json` **before** running `pnpm install`. A short Python snippet keeps the patch idempotent and avoids a downstream `patches/<name>.patch` to re-roll on every version bump:

```bash
# In build.sh, after `cd "${SRC_ROOT}"` and before `pnpm install`:
python -c "
import json, pathlib
p = pathlib.Path('package.json')
d = json.loads(p.read_text())
d.get('scripts', {}).pop('postinstall', None)
p.write_text(json.dumps(d, indent=2))
"

pnpm install \
  --frozen-lockfile \
  --strict-peer-dependencies=false \
  --ignore-scripts \
  --filter '@org/<daemon>...'
```

Keep the `--ignore-scripts` flag — it still does useful work on dependency-side install scripts (skips native compile scripts on packages we'll explicitly rebuild later via `pnpm --filter ... rebuild <native-dep>`).

**Why not patch via `patches/<name>.patch`**: a `patches/` patch is more visible to reviewers but requires re-rolling on every version bump (the JSON line numbers shift, hunks fuzz-fail). The Python `pop()` form is robust across upstream restructures and idempotent (no-ops if the script is already absent).

**Other root scripts to consider**: `preinstall`, `prepare`, `prepublish` — same root-vs-dependency distinction applies to all lifecycle scripts. Audit `package.json scripts:` for anything in install-phase scope that does work outside the recipe's surface.

**Case study**: `recipes/open-design/build.sh` (Jun 11, 2026). The recipe was authored at v0.2.0 with `--ignore-scripts` and a comment ("`--ignore-scripts` skips the root package's postinstall") that was empirically false — the recipe had never actually been built. Bumping to v0.9.0 surfaced the bug when upstream's `scripts/postinstall.mjs` `buildTargets` list grew from 4 to 13 (adding `packages/download`, `packages/host`, `packages/registry-protocol`, `packages/agui-adapter`, `packages/plugin-runtime`, `packages/diagnostics`, `tools/dev`, `tools/pack`, `tools/serve`). The newly-added `packages/download` workspace's build script needed `esbuild` which the `@open-design/daemon...` filter didn't fetch. Fix shipped as the Python-pop snippet above; build green at `open-design-0.9.0-h07aa61f_0.conda` (9.51 MiB).

### G18. `workflow_settings.store_build_artifacts: true` (unscoped) crashes Windows Azure builds via 7z + INetCache ACLs

**Symptom**: feedstock CI shows `Run Windows build: succeeded` (the recipe's actual rattler-build phase finishes cleanly and the `.conda` artifact is produced — visible in the archive listing) but the very next Azure task `Prepare conda build artifacts: failed` with:

```
D:\bld\bld\rattler-build_<pkg>_<id>\.work.pending-rm-<id>\AppData\Local\Microsoft\Windows\INetCache\Content.IE5 : Access is denied.
...
##[error]Cmd.exe exited with code '1'.
##[section]Finishing: Prepare conda build artifacts
```

The two follow-on Azure tasks `Store conda build artifacts` and `Store conda build environment artifacts` are reported `skipped` (gated on the prior task's success). The Azure leg is therefore marked `result=failed` on the timeline, the umbrella aggregator `<feedstock-name>` check goes red, and the PR can't advance to ready-for-review even though the build itself succeeded on every Python variant.

**Why**: when `workflow_settings.store_build_artifacts` is `true` (or the legacy `azure.store_build_artifacts: true`), conda-smithy rerender stamps `store_build_artifacts: true` per win matrix entry in `.azure-pipelines/azure-pipelines-win.yml`, which the `Prepare conda build artifacts` step's `condition: eq(variables.store_build_artifacts, true)` then activates. That step calls `conda-forge-ci-setup`'s `.scripts/create_conda_build_artifacts.bat`, whose 7z invocation is:

```bat
7z a "<archive>" "%CONDA_BLD_PATH%" -xr^^!.git/ -xr^^!_*_env*/ -xr^^!*_cache/ -bb
```

It archives the entire `D:\bld\` work directory with only `.git/`, `_*_env*/`, and `*_cache/` excluded. Rust-heavy builds — anything that compiles tree-sitter, hyper, tower, reqwest, rustls/webpki, etc. — invoke Windows winhttp/wininet during fetch and write entries to `AppData\Local\Microsoft\Windows\INetCache\Content.IE5` inside the build sandbox's redirected user profile. That directory has restricted Windows ACLs (only the SYSTEM account or owner can enumerate the contents); 7z fails with errorlevel 1, the bat exits 1, and the entire post-build archive task fails. Linux and macOS legs are unaffected — the AppData/INetCache hierarchy is Windows-specific.

**Fix**: scope `workflow_settings.store_build_artifacts` to non-Windows platforms via the conditional list form (per the v8.6+ conda-smithy schema — `ConditionalValue` supports `os` / `platform` / `provider` filters):

```yaml
workflow_settings:
  store_build_artifacts:
    - platform:
        - linux_64
        - linux_aarch64
        - osx_64
        - osx_arm64
      value: true
```

After rerender, the win Azure variants stamp `store_build_artifacts: false`, the `condition:` on the prepare task evaluates false, the entire failing task is skipped, and the leg goes green. Linux + osx still publish their `.conda` files as downloadable Azure artifacts — the v8.14.0 `pixi run -e local-recipes pr-artifacts <pr>` smoke-test workflow keeps working there.

**Upstream fix (out of feedstock scope)**: the durable fix is in `conda-forge-ci-setup`'s `.scripts/create_conda_build_artifacts.bat` — add `-xr^^!*INetCache*` and `-xr^^!AppData/` to the 7z exclude list. File a separate issue against `conda-forge/conda-forge-ci-setup` rather than ship the workaround in every Rust-heavy Windows feedstock.

**When this comes up in practice**: any recipe that fetches over HTTPS during the build phase on Windows can in principle hit this. Rust+PyO3 / tree-sitter recipes are the most common trigger because their crate dependency trees include many HTTPS-fetching crates (reqwest, hyper, tower, webpki, rustls). Pure-Python recipes don't typically trigger it (pip uses its own cache, not winhttp).

**Detection at scale**: search the Azure build timeline for the failure signature — a `Job` with `result=failed` whose `Run Windows build` sub-task is `result=succeeded` but `Prepare conda build artifacts` is `result=failed`. The timeline JSON is at `dev.azure.com/conda-forge/feedstock-builds/_apis/build/builds/<buildId>/timeline?api-version=7.0`.

**Case study**: cocoindex feedstock PR #9 (Jun 14, 2026; conda-forge/cocoindex-feedstock). Initial commit enabled unscoped `workflow_settings.store_build_artifacts: true` to enable the v8.14.0 PR-artifacts workflow. After rerender + first CI run: all 4 linux_64 + 4 linux_aarch64 + 4 osx_64 + 4 osx_arm64 + linter checks green; all 4 win_64 variants `result=failed` at the prepare step with the INetCache ACL error. Build phase (`Run Windows build`) succeeded on every win variant, `.conda` file produced (e.g. `win-64\cocoindex-1.0.10-py313hfbe8231_0.conda` visible in the 7z listing before the error). Fix: scope to `[linux_64, linux_aarch64, osx_64, osx_arm64]`. Subsequent rerender pushed `store_build_artifacts: false` to all win variants; next CI run all-green.

### G19. Windows pip-install fails `Error reading output: stream did not contain valid UTF-8` — set `PYTHONUTF8: "1"` (+ canonical Rust env block while you're there)

**Scope (v8.43.0): NOT Rust-specific.** This applies to ANY Windows build where Python reads a non-ASCII file with the default codec — most commonly a pure-**setuptools** recipe whose `setup.py` does `open('README.md')` (no `encoding=`) on a UTF-8 README. On win-64 the default codec is **cp1252**, which can't decode the UTF-8 bytes, so metadata generation dies with `UnicodeDecodeError: 'charmap' codec can't decode byte 0xNN` — a *different symptom* than the Rust "stream did not contain valid UTF-8", **same** `PYTHONUTF8: "1"` fix (PEP 540 forces Python's `open()` to default to UTF-8). Case: lomond 0.3.3 (staged-recipes #33889, Jun 25 2026) — `setup.py` reads its box-drawing-char README; win_64 (buildId 1543779) hit `charmap` byte 0x90 at metadata gen; `PYTHONUTF8: "1"` in `build.script.env` fixed it (no Rust env block needed for a pure-setuptools recipe).

**Symptom**: Rust+PyO3 (or any cargo+pip) recipe's Windows Azure CI fails inside the `Run Windows build` task at the `pip install . -vv --no-deps --no-build-isolation` step with:

```
[2026-06-14T17:58:27Z WARN  bundle_licenses_lib::found_license] ...
Using pip 26.1.2 from %PREFIX%\Lib\site-packages\pip (python 3.12)
...
Processing .\.
  Added file:///%SRC_DIR% to build tracker '...'
  Preparing metadata (pyproject.toml): started
  Running command Preparing metadata (pyproject.toml)
⚠ warning Error reading output: Custom { kind: InvalidData, error: "stream did not contain valid UTF-8" }
```

The build appears to abort mid-`pip install`; rattler-build emits the misleading warning and Windows variants fail. Linux + macOS unaffected (their console default is UTF-8). The recipe builds clean on every non-Windows platform.

**Why**: rattler-build captures the subprocess (cargo / maturin / pip) stdout+stderr and decodes them as UTF-8. Windows CI agents (`vmImage: windows-2022`) default to **cp1252** for the console codepage, NOT UTF-8. Modern Python's `sys.stdout` honors `sys.stdout.encoding` which respects locale; on Windows that resolves to `cp1252` unless explicitly overridden. When cargo/maturin/pip emit non-ASCII bytes — license filenames with accents (`LICENSE-ÉLECTRON-MIT`), package descriptions with em-dashes, paths with localized Windows component names, etc. — the resulting cp1252-encoded bytes can't be decoded as UTF-8 by rattler-build's reader. The reader gives up reading the stream, rattler-build flags the build as broken, and the Windows leg fails.

**Fix**: set `PYTHONUTF8: "1"` in `build.script.env` (PEP 540 — Python UTF-8 mode). This forces Python to use UTF-8 for `sys.stdout`/`sys.stderr` regardless of system locale. Pip then writes UTF-8, rattler-build decodes cleanly, the build completes.

**Apply the canonical Rust env block, not just the one-line PYTHONUTF8 fix.** When you're already editing `build.script.env`, also add the conda-forge canonical Rust optimization env vars per CFE skill v8.9.1 retro + [conda-forge.org/docs/maintainer/example_recipes/rust](https://conda-forge.org/docs/maintainer/example_recipes/rust/) — these are the default for every Rust feedstock, NOT optional:

```yaml
build:
  script:
    env:
      # Strip debug symbols from the produced .so / .pyd / .dll.
      # Conda-forge default for all Rust builds; reduces final binary
      # by 30–50%.
      CARGO_PROFILE_RELEASE_STRIP: symbols
      # CARGO_PROFILE_RELEASE_LTO: fat is intentionally NOT set — fat
      # LTO can blow past Azure's 6-hour timeout on Windows for Rust
      # packages with deep dep graphs (~600 crates is typical for
      # tree-sitter / hyper / tower / rustls / heed combos). Re-enable
      # only when the recipe's actual Windows build time stays well
      # under ~3h. The `# note time out issues` comment is institutional
      # knowledge from xorq-datafusion — leave it for the next maintainer.
      #CARGO_PROFILE_RELEASE_LTO: fat
      # PEP 540 — Python UTF-8 mode. THE Windows fix for this gotcha.
      PYTHONUTF8: "1"
    content:
      - if: unix
        then: |
          export CFLAGS="${CFLAGS:-} -D_BSD_SOURCE -D_DEFAULT_SOURCE"   # iff the recipe needs it
          cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
          ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
        else: |
          cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
          ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```

This is **the canonical Rust+PyO3 conda-forge env block**. Any new Rust+PyO3 recipe should start here. `recipes/cocoindex/recipe.yaml` and `conda-forge/xorq-datafusion-feedstock` both ship this shape.

**Why include STRIP even when only PYTHONUTF8 is the apparent fix**: a single-line PYTHONUTF8 patch is a scope mistake. STRIP is the conda-forge default for all Rust builds (CFE v8.9.1 retro shipped it into the maturin template; the canonical doc lists it as the first env var); commenting out LTO with the `# note time out issues` rationale preserves the institutional knowledge for the next maintainer (otherwise they'll re-enable LTO speculatively and discover the timeout the hard way). Matching the cited reference pattern fully is canonical-pattern application, not scope creep.

**When you'd opt INTO `CARGO_PROFILE_RELEASE_LTO: fat`**: only when (a) the recipe is a small-graph Rust binary (~100 crates or fewer), (b) Azure CI history shows <90 min Windows build time at the current STRIP-only shape, and (c) the binary-size win from LTO is meaningfully worth the extra build time. For 95% of Rust+PyO3 recipes, leave it commented.

**Edge case — the env block changes the `script:` shape from list to env+content**: if the recipe's current `build.script:` is a YAML list of strings, switching to `env:` + `content:` is a structural change (not just an env-var addition). Validate locally with `pixi run -e local-recipes validate recipes/<feedstock>` after the edit — schema parser is strict about this.

**Case study**: cocoindex 1.0.10 + xorq-datafusion 0.2.9 (both `rxm7706`-maintained). xorq-datafusion's recipe carries the canonical env block — `CARGO_PROFILE_RELEASE_STRIP: symbols` + `#CARGO_PROFILE_RELEASE_LTO: fat # note time out issues` + `PYTHONUTF8: "1"` — and ships clean on every platform. cocoindex 1.0.10's upstream recipe had been bot-automerged at v1.0.10 without the env block; Windows CI passed at the time but broke later when a rattler-build / pip / cargo update tightened UTF-8 decoding. PR #9 (Jun 14, 2026) added the full canonical env block — `STRIP` + commented `LTO` + `PYTHONUTF8` — bumping `build.number: 0 → 1`. Subsequent CI run: all Windows variants green.

**Detection at scale**: grep Azure win build logs for `Error reading output: ... stream did not contain valid UTF-8`. Affected recipes typically also have `Recovery (errors)` lines around the failure point indicating pip's metadata-preparation phase couldn't complete cleanly.

### G20. v0 jinja `{{ X }}` syntax in v1 recipe.yaml is silently rendered as literal text

**Symptom**: a v1 recipe (declares `schema_version: 1`) passes `validate_recipe` and `conda-smithy lint` cleanly, but the build fails with errors that look unrelated to syntax:

- `build.script:` containing `{{ PYTHON }} -m pip install . -vv …` → cmd.exe / bash treats `{{` as a literal command and emits `command not found: {{` or `'{{' is not recognized as an internal or external command`.
- `requirements.host:` / `requirements.run:` carrying `librdkafka >={{ version }}` → the conda solver parses `>={{ version }}` as a literal version constraint and aborts with `cannot parse spec '>={{ version }}'`.
- A patches list entry like `- 0001-Fix-setup-for-windows.patch  # [win]` — applies the patch on every platform because the comment selector is silently ignored (this is the cousin trap; see G3 for `py < N` and the `# [win]` selector both being silently ignored by v1).

**Why**: in v1 recipe.yaml, the substitution prefix is `${{ … }}` (minijinja); the bare `{{ … }}` form is the v0 conda-build jinja prefix. The v1 parser treats bare `{{ … }}` as a plain YAML scalar — well-formed YAML, so validators don't object — and emits it verbatim to the shell, the dep spec, or whatever consumer reads the rendered value. `validate_recipe`, `rattler-build lint`, and `conda-smithy lint` all pass; the failure surfaces at build / install time.

This is the third entry in a class of silent v0→v1 substitution traps:
- **G2** — v0-only about-field names (`home`, `dev_url`, `doc_url`) silently discarded (`license_family` is NOT one of these — it is a valid, if deprecated, v1 field).
- **G3** — v0 `py < N` skip selectors and v0 `# [unix]` / `# [win]` comment selectors silently ignored.
- **G20** — bare `{{ X }}` substitutions silently emitted as literal text.

**Fix**: in every v1 recipe.yaml, use `${{ X }}` for every substitution. Common sites where the bare form sneaks in when a recipe is hand-edited (or migrated from v0 without a full sweep):

- `build.script:` — `{{ PYTHON }}`, `{{ CFLAGS }}`, `{{ SRC_DIR }}`
- `requirements.host:` / `requirements.run:` / `requirements.build:` — `<pkg> >={{ version }}`, `<pkg> {{ version }}.*`
- `source.url:` — `https://…/{{ version }}/…`, `…/{{ name }}-{{ version }}.tar.gz`
- `package.name:` / `package.version:` — should be `${{ version }}` literals
- `about.*` scalars when templated (rare but possible)

**Detection — one-line grep**:

```bash
grep -nE '(^|[^$])\{\{[^}]+\}\}' recipes/<name>/recipe.yaml
```

Matches any `{{ X }}` not preceded by `$`. Any hit on a v1 recipe (`schema_version: 1`) is a silent-failure candidate. Run as a pre-submission check; zero matches is the canonical state.

A follow-up optimizer check **`JIN-001`** ("v0-style `{{ X }}` substitution in v1 recipe — silently emitted as literal text") would catch this at gate-time alongside SEL-003 (v0 selector) and ABT-002 (v0 about-field). Tracked as skill TODO; not yet shipped.

**Case study**: python-confluent-kafka v0→v1 migration (Jun 14, 2026; PR conda-forge/python-confluent-kafka-feedstock#127). Hand-rolled `recipes/confluent-kafka-python/recipe.yaml` (an in-flight v1 draft predating this gotcha) carried three distinct v0-jinja bugs that `validate_recipe` + `optimize_recipe` both passed cleanly:

1. `build.script:` last entry — `{{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation`. Would have failed at install with shell "command not found: `{{`".
2. `requirements.host:` `librdkafka >={{ version }}` and `requirements.run:` `librdkafka >={{ version }}`. Would have failed the solver with an unparseable spec.
3. `source.patches:` `- 0001-Fix-setup-for-windows.patch  # [win]`. The v0 comment selector would have been silently ignored; the Windows-only patch would have applied on every platform and broken the Linux/macOS build at `pip install` time.

All three were caught by manual SKILL.md-driven audit before the local build ran. Conversion to `${{ X }}` and `if: win / then:` produced a clean recipe; subsequent CI on PR #127 went 39/39 green across linux_64 / linux_aarch64 / linux_ppc64le / osx_64 / osx_arm64 / win_64 × 6 Python variants each + linter + aggregator.

The cost of the audit was ~5 minutes; the cost of *not* doing it would have been one CI iteration per bug (3 × ~20 min on the slowest emulated platform) plus reviewer churn.

### G21. conda-smithy mis-aligns the zip-keyed `is_python_min` flag when `python_min` is overridden upward

**Symptom**: a Rust+PyO3 (or other abi3-binary) recipe uses the canonical `skip: is_abi3 and not is_python_min` matrix-collapse rule + a recipe-local `conda_build_config.yaml` that overrides `python_min` above the conda-forge-pinning default (e.g. `python_min: "3.11"` for a `pyo3/abi3-py311` package while pinning's default is `'3.10'`). After conda-smithy rerender, the regenerated `.ci_support/<platform>_is_python_mintruepython3.10.____cpython.yaml` shows:

```yaml
is_abi3: [true]
is_python_min: [true]      # zip-keyed with python
python: [3.10.* *_cpython] # ← still py3.10 from pinning's first entry
python_min: ['3.11']       # ← honors the override
```

The build then runs against py3.10 (because variant `python` is `3.10.*`) and pip-install fails: `cocoindex requires Python >=3.11`. The `python` axis and `python_min` are now contradictory in the same `.ci_support` file.

**Why**: conda-smithy's `variant_algebra.variant_add` performs a UNION merge between pinning's `python` axis and the recipe-local CBC `python_min`. The override of `python_min` is honored, but `python`'s first entry is preserved unchanged (smithy doesn't infer that the new min should shift the zip-key's `true` position). The zip-key `is_python_min: [true, false, false, false]` remains aligned with pinning's `python: [3.10.*, 3.11.*, ...]`, so position 0 (py3.10) keeps `is_python_min=true` even though `python_min` now says `'3.11'`.

Attempts to also override `python:` in the recipe-local CBC hit G22 (wrong suffix syntax) or local-build `Zip key elements do not all have same length: is_python_min` errors.

**Fix**: use the rustworkx-pattern skip rule instead — it sidesteps the zip-key entirely:

```yaml
build:
  skip: not (match(python, python_min ~ ".*") and is_abi3)
  python:
    version_independent: ${{ is_abi3 }}
```

```yaml
# recipe/conda_build_config.yaml
python_min:
  - "3.11"
```

`match(python, python_min ~ ".*")` compares the variant's `python` value against `python_min ~ ".*"` (jinja string-concat, NOT regex — renders `"3.11" + ".*"` → `"3.11.*"`). For variants where `python` is `3.10.*`, the match fails and the variant is skipped. Only the variant whose `python` matches `python_min` survives. With `python_min: "3.11"`, the one surviving variant builds against py3.11 correctly.

Used by: `rustworkx-feedstock`, `cocoindex-feedstock`. The Variant A skip (`is_abi3 and not is_python_min`) used by tree-sitter-typescript etc. still works fine for recipes whose abi3 minimum matches pinning's default (currently 3.10); only switch to Variant B when overriding upward.

**Case study**: cocoindex PR #11 (https://github.com/conda-forge/cocoindex-feedstock/pull/11). Three iterations needed: (a) initial `is_abi3 and not is_python_min` + 4-entry CBC `python:` override crashed smithy rerender with G22; (b) simplified to CBC `python_min: "3.11"` only — smithy collapsed the matrix but mis-aligned `python: [3.10.*]`, builds failed with `requires Python >=3.11`; (c) switched to `not (match(python, python_min ~ ".*") and is_abi3)` — single py3.11 variant per platform, abi3audit clean (0 ABI version mismatches), all 8 CI legs green including win_64 fat-LTO in 9 min 45 s.

Full pattern + companion configs (`version_independent`, `python-abi3`, cross-Python test, `abi3audit` step) in [`reference/abi3-matrix-collapse.md`](reference/abi3-matrix-collapse.md).

### G22. Recipe-local CBC `python:` override using `*_cpython` suffix crashes smithy on py3.13+

**Symptom**: a recipe-local `conda_build_config.yaml` overrides the variant `python` axis with what looks like uniform syntax:

```yaml
python:
  - 3.11.* *_cpython
  - 3.12.* *_cpython
  - 3.13.* *_cpython    # ← wrong suffix
  - 3.14.* *_cpython    # ← wrong suffix
```

conda-smithy rerender crashes with:

```
File "conda_smithy/variant_algebra.py", line 63, in _version_order
    return ordering.index(v)
ValueError: '3.13.* *_cpython' is not in list
```

The rerender service marks itself failed; the regenerated `.ci_support/*.yaml` files don't update; subsequent CI runs against the OLD configs fail with whatever cascade follows.

**Why**: conda-forge-pinning's python axis uses **different suffix tags per Python version**:

| Python | Pinning suffix | Source |
|---|---|---|
| 3.10, 3.11, 3.12 | `*_cpython` | `conda_build_config.yaml` (base pinning) |
| 3.13 | `*_cp313` | `migrations/python313.yaml` |
| 3.13 freethreading | `*_cp313t` | `migrations/python313t.yaml` |
| 3.14 | `*_cp314` | `migrations/python314.yaml` |
| 3.14 freethreading | `*_cp314t` | `migrations/python314t.yaml` |

The `_version_order` helper builds an ordering list from these exact strings. An entry that doesn't match (`3.13.* *_cpython` is wrong; the pinning has `3.13.* *_cp313`) is rejected by `ordering.index(v)`.

**Fix — don't override `python:` axis**: for the abi3 matrix-collapse pattern, override **only** `python_min` and pick the right skip rule (G21):

```yaml
# recipe/conda_build_config.yaml — minimal override
python_min:
  - "3.11"
```

```yaml
# recipe.yaml — Variant B skip rule
build:
  skip: not (match(python, python_min ~ ".*") and is_abi3)
```

This delegates all python-axis bookkeeping to smithy + pinning. The match() rule filters at recipe-render time without requiring the recipe to know suffix syntax.

**Fix — if you must override `python:` axis**: use the canonical suffix per version:

```yaml
python:
  - 3.11.* *_cpython
  - 3.12.* *_cpython
  - 3.13.* *_cp313
  - 3.14.* *_cp314
is_python_min:
  - true
  - false
  - false
  - false
```

This works but is rarely needed — the abi3 collapse pattern doesn't require it. Live reference for the suffix-per-version convention: `conda-forge-pinning-feedstock`'s `recipe/migrations/python3{13,14}.yaml`.

**Detection**: any recipe-local `conda_build_config.yaml` that lists multiple python entries with uniform `*_cpython` is suspect when the list includes 3.13 or 3.14. One-line grep:

```bash
grep -nE '3\.(13|14)\..* \*_cpython' recipes/*/conda_build_config.yaml
```

A non-empty result is a smithy-rerender-crash candidate.

**Case study**: cocoindex PR #11 first push (https://github.com/conda-forge/cocoindex-feedstock/pull/11). The recipe-local CBC carried the wrong-suffix block above. Smithy rerender's run-task job crashed with the ValueError; all 20 build jobs (4 py × 5 platforms) ran against the stale `.ci_support/*.yaml` and failed cascade-style with `Jinja template error: undefined variable in condition 'is_abi3'`. Resolution: dropped the `python:` axis override entirely, kept only `python_min: "3.11"`, switched skip rule per G21. Rerender succeeded on the next push.

### G23. Inline `sed` + `powershell` in `build.script` hits cmd.exe escape hell — use `sed` (with `m2-sed` on Windows) for a single cross-platform line

**Symptom**: a recipe needs to rewrite something in upstream's source tree at build time (typically a pyproject.toml version field, a hardcoded path, or a build-system requires line). The author writes platform-conditional script entries — `sed -i ...` on Unix, `powershell -Command "(Get-Content X) -replace ..." | Set-Content X` on Windows. Unix passes; Windows fails with the regex either silently producing the wrong result OR crashing rattler-build's script runner with exit 255.

Inspecting the actual command cmd.exe ran reveals the mangle: a regex written as `^version = "[^\"]*"$` was passed to powershell as `^version = "[^"]*"$` (note the `^` from the character class is gone). The replacement string and outer pattern survived; only the `^` from `[^...]` was eaten.

**Why**: cmd.exe treats `^` as its **line-continuation / escape character** outside of double-quoted strings. The YAML literal-block `|` → cmd.exe `"..."` argument → PowerShell `-Command` body → PowerShell single-quoted regex string has FOUR layers of quoting/escaping. cmd's `^`-stripping happens during the cmd-to-powershell hand-off, BEFORE powershell sees the regex. The first `^version` (line-anchor at the start of the regex) survives because it's inside cmd's `"..."`. The second `^` (inside `[^"]`) is in a structurally-identical position but cmd interprets the surrounding `\"` escape differently and ends up outside its own quoted region for a moment — long enough to eat the `^`.

This isn't unique to powershell: any cmd command that passes a regex with `^` in a char class hits the same trap. Adding more backslashes to escape (`\\^`, `^^`) makes it worse on Unix.

**Fix — single cross-platform line via `sed`**:

```yaml
requirements:
  build:
    - if: win
      then: m2-sed   # conda-forge ships GNU sed on Windows as `m2-sed`
                    # (provides `sed.exe` in $PREFIX). On Unix the system sed
                    # is in the build container natively; no dep needed.

build:
  script:
    - sed -i 's/^version = .*/version = "${{ version }}"/' pyproject.toml
    - ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```

`sed -i` works identically on Linux, macOS, and Windows (with `m2-sed`). The `${{ version }}` is rendered by jinja before the shell ever sees it, so there's no shell-level templating to break.

`sed`'s `-i` flag is `-i` on GNU sed everywhere conda-forge ships it — including `m2-sed` on Windows. BSD sed (macOS system sed) requires `-i ''` or `-i.bak`, but the conda-forge build container uses GNU `sed` via the `sed` build dep on Unix too. If your recipe doesn't already pull a build-prefix sed, add `sed` (Unix) + `m2-sed` (Win) to be explicit.

**Fix — when sed isn't enough (multi-line, TOML structure, jinja loops)**: check a small Python helper file into the recipe directory and invoke it via `${{ PYTHON }} ${RECIPE_DIR}/helper.py` (Unix) + `"%PYTHON%" "%RECIPE_DIR%\helper.py"` (Win). $PKG_VERSION and $RECIPE_DIR are set on both platforms. The helper avoids inline-string quoting entirely. This is what `conda-forge/tree-sitter-swift-feedstock#5` ended up shipping after the inline powershell escape hell — a `recipe/fix_pyproject_version.py` with `os.environ["PKG_VERSION"]` + `re.sub`. Works but is more code than a single inline `sed` line.

**Anti-pattern — `powershell -Command "(...)-replace...regex with ^..."`**: avoid entirely. The cmd-to-powershell quoting boundary breaks in non-obvious ways. If you find yourself reaching for it, switch to `sed` + `m2-sed` build dep instead.

**Case study**: tree-sitter-swift-feedstock #5 (Jun 2026). Upstream `alex-pinkus/tree-sitter-swift` hardcodes `pyproject.toml [project].version = "0.0.1"` across all tagged releases, so the conda-built wheel ships `tree_sitter_swift-0.0.1.dist-info` which then breaks `pip check` for any downstream with an upper-bounded constraint like `tree-sitter-swift<0.9,>=0.7` (caught on `conda-forge/graphifyy-feedstock#8`). First-pass fix used inline `sed` (Unix) + `powershell` (Win) for the version rewrite; Azure buildId 1539671 win_64 failed with the cmd-ate-the-caret regex mangle. Second-pass used a checked-in Python helper which worked but bloated the recipe. Canonical pattern for next time: `sed` with `m2-sed` build dep, single inline line, no Python helper.

### G24. Conda label ≠ wheel `dist-info` version — when upstream's `pyproject.toml` hardcodes a placeholder, `pip check` fails downstream

**Symptom**: a recipe's `validate_recipe` + `build` + own `pip_check: true` test all pass locally. The conda artifact ships with the right version label (`<pkg>-<X.Y.Z>-*.conda`). **A downstream feedstock that pins this package** with an upper bound — e.g. `<pkg> >=0.7,<0.9` — then fails its own `pip check` test on conda-forge CI with:

```
<downstream-pkg> X.Y.Z has requirement <pkg><0.9,>=0.7, but you have <pkg> 0.0.1.
```

Even though `mamba list` in the downstream test env shows `<pkg> 0.7.3` per the conda metadata. The discrepancy is real, not a display bug: `pip check` reads each installed package's wheel-bundled `dist-info/METADATA` `Version:` line, NOT the conda repodata version. If the upstream `pyproject.toml`'s `[project].version` is a placeholder (commonly `"0.0.1"`) that was never bumped to match the tag scheme, the wheel ends up with `<pkg>-0.0.1.dist-info/` even though the conda package label is correctly `0.7.3`.

**Why**: many tree-sitter-grammars-style projects (alex-pinkus/tree-sitter-swift was the case-study example) maintain their version through Git tags + a release script that updates language-specific bindings (cargo, npm, gem) but doesn't touch `pyproject.toml`. PyPI is also stuck at the placeholder for the same reason. Anaconda's main channel + conda-forge's feedstock both ship the conda-label-correct package; only the bundled wheel metadata is stale.

**Detection**: after building (locally or on CI), extract `info/recipe/recipe.yaml` from any same-package downstream's failed-CI artifact and look at the actual error. Or proactively scan a built `.conda`:

```bash
python3 -c "
import zipfile, zstandard, tarfile, io, sys
with zipfile.ZipFile(sys.argv[1]) as z:
    data = z.read([n for n in z.namelist() if n.startswith('pkg-')][0])
    with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(data)) as r:
        with tarfile.open(fileobj=r, mode='r|') as tar:
            for m in tar:
                if 'dist-info/METADATA' in m.name:
                    f = tar.extractfile(m)
                    print(m.name.split('/')[-2])  # dist-info dir name
                    for line in f.read().decode().split('\n')[:5]:
                        print(' ', line)
                    break
" <pkg>-<X.Y.Z>-*.conda
```

Compare the printed `dist-info` dir name (e.g. `tree_sitter_swift-0.0.1.dist-info`) against the conda filename version (`tree-sitter-swift-0.7.3-...`). If they differ — even by one PATCH number — the package is poisoned for downstream `pip check`.

**Fix — downstream patch at the feedstock**: rewrite the `[project].version` field in upstream's `pyproject.toml` at build time using a `sed` substitution driven by `$PKG_VERSION` (per G23's canonical pattern):

```yaml
requirements:
  build:
    - if: win
      then: m2-sed

build:
  script:
    - sed -i 's/^version = .*/version = "${{ version }}"/' pyproject.toml
    - ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```

This is idempotent — if upstream ever resumes proper version bumping, the sed runs against the correct value and is a no-op. The fix is forward-compatible and self-healing.

**Also file an upstream issue** asking maintainers to bump `pyproject.toml [project].version` to track tag releases. Even if they fix it for the next release, the wheel-bundled metadata for already-tagged versions on PyPI stays broken, so the downstream patch stays relevant for any feedstock that pins to an existing version range.

**Scope**: this trap is most common in **tree-sitter language grammars** (parser.c is auto-generated from grammar.js; the Python binding is an afterthought to the C work and gets version-neglected), but applies to ANY conda recipe building a Python wheel from a source that has placeholder version metadata. Other ecosystems with the same risk profile: language-server-protocol implementations, generated-binding wrappers around C libraries, monorepo subpackages where only the parent is version-tracked.

**Survey approach for new tree-sitter-style recipes**: before submitting a recipe whose downstreams may pin upper bounds, scan ALL platforms' built artifacts' dist-info to confirm the version inside matches the conda label. The CFE skill's `tests/` could add a regression-test helper for this; today it's a manual check.

**Case study**: graphifyy 0.8.40 → `pip check` rejected `tree-sitter-swift 0.0.1 < 0.7` on `conda-forge/graphifyy-feedstock#8` even though conda-forge had shipped `tree-sitter-swift-0.7.3-*.conda` for weeks. Surveyed all 22 tree-sitter-* feedstocks rxm7706 maintains; **only `tree-sitter-swift` had the major mismatch** (one minor mismatch in `tree-sitter-powershell` 0.26.5/0.26.4 was within graphifyy's `>=0.26,<0.28` range so harmless). Fix shipped as `conda-forge/tree-sitter-swift-feedstock#5` (merged 2026-06-17) with the canonical pattern above + dynamic `tag: ${{ version }}-with-generated-files`. The dist-info trap had been latent on conda-forge for the entire `tree-sitter-swift 0.7.x` lifetime — only surfaced when a downstream with `pip_check: true` pinned to a version range upstream's placeholder excluded.

### G25. Conda has no "extras" — flatten every `pkg[extra]` upstream dep into `run:`, and resolve each extra to its *actual* conda packages (which may be renamed)

**Symptom**: a recipe whose upstream `pyproject.toml` declares a dependency with an extras marker — `dbgpt[client,cli,agent,code,...]`, `httpx[socks]`, `uvicorn[standard]`, `celery[redis]` — installs and its **own** `pip_check` passes locally, but imports fail at runtime with `ModuleNotFoundError` for something the extra was supposed to pull, or a **downstream** feedstock's `pip_check` fails with `<pkg> X has requirement <extra-dep>...; not satisfied`. The recipe's `run:` listed only the base package, or a guessed `<pkg>-<extra>` name that isn't on conda-forge.

**Why** (two interlocking facts):

1. **Conda has no extras mechanism.** PEP 508 extras (`pkg[extra]`) are pip-only: installing `pkg[extra]` pulls `pkg` *plus* the deps under `pkg`'s `[project.optional-dependencies].extra`. A conda `pkg` is built **once, without extras**, and the solver cannot activate an extra at install time. So every `pkg[extra]` in an upstream dep list must be **flattened** — the recipe carries `pkg` AND the union of that extra's deps directly in `requirements.run`. This bites hardest in **multi-output** recipes: output B may depend on `A[extra]` where A is a *sibling output in the same recipe*; A is built without extras, so **`${{ pin_subpackage('A', exact=True) }}` does NOT pull A's extra-deps** — B must list them itself.

2. **An extra's marker name ≠ the conda package it resolves to.** `httpx[socks]` does **not** pull a package called `httpx-socks` — it pulls whatever `httpx`'s `pyproject.toml` lists under `[project.optional-dependencies].socks`, which is `socksio`. The conda dep is `socksio`. Guessing `<pkg>-<extra>` is wrong twice: that's usually a *different* PyPI project, and it often isn't on conda-forge at all. Read the extra's actual contents, then map each dep to its conda name (G10's four-spelling rule applies).

`pip_check: true` is the enforcement mechanism: `pip check` reads the installed wheel's `METADATA` and sees `Requires-Dist: <dep>; extra == "socks"` for every extra the *consumer* requested, then fails if those deps aren't installed. A recipe that activates `pkg[extra]` but omits the flattened deps fails `pip check` — loudly in the building feedstock, or (worse) only in a **downstream** feedstock's CI, because the builder's own `pip_check` covers just the package being built, not its dependents (see G24 for the same downstream-only failure mode).

**Fix**:

1. For each `pkg[extra1,extra2,...]`, fetch upstream's `pyproject.toml` and read `[project.optional-dependencies]`. Union the base `[project.dependencies]` with every **activated** extra's list.
2. Map each resulting dep to its conda-forge name (G10 four-spelling check; watch for the extra→renamed-package trap like `httpx[socks]`→`socksio`).
3. Put the flattened union in `requirements.run`. In a multi-output recipe, expand each sibling's activated extras past the `pin_subpackage` — the pin alone is not enough.
4. **Drop any extra the recipe does not activate.** Don't ship deps for `pkg[gpu]` / `pkg[proxy_qianfan]` if no output requests them — over-listing bloats the run env and can pull packages that aren't on conda-forge for no reason.

**Detection** — before trusting a generated (especially multi-output) recipe, grep upstream's dep declarations for the extras-bracket and reconcile each against `run:`:

```bash
# Every pkg[extra] in the upstream pyproject(s)
grep -rEo '[A-Za-z0-9_.-]+\[[A-Za-z0-9_,-]+\]' packages/*/pyproject.toml
# What a given extra actually pulls:
python -c "import tomllib,sys,json; d=tomllib.load(open(sys.argv[1],'rb')); print(json.dumps(d['project'].get('optional-dependencies',{}),indent=2))" packages/<pkg>/pyproject.toml
# What an extra on an external dep resolves to (the httpx[socks]→socksio class):
curl -s https://pypi.org/pypi/httpx/json | python -c "import sys,json; print([r for r in json.load(sys.stdin)['info']['requires_dist'] if 'extra' in r and 'socks' in r])"
# → ['socksio==1.*; extra == \"socks\"']  (conda dep is socksio, NOT httpx-socks)
```

**Case study**: DB-GPT v0.8.0 multi-output spec audit (Jun 17, 2026; `docs/specs/db-gpt-conda-forge.md`). The `dbgpt-app` output depends on `dbgpt[client,cli,agent,simple_framework,framework,code,proxy_openai,proxy_tongyi,proxy_zhipuai]` + `dbgpt-ext[rag,storage_chromadb]`, where `dbgpt`/`dbgpt-ext` are *sibling outputs in the same recipe*, built without extras. The first-draft spec listed only `pin_subpackage` on the siblings + a handful of direct deps, missing ~50 of the flattened **68** external run-deps; `pip_check` would have failed at CI. Two extras-resolution traps surfaced: (a) `httpx[socks]` → the spec guessed `httpx-socks` (absent from conda-forge) when the real dep is `socksio` (present); (b) `qianfan` was listed as required but lives only in the **non-activated** `proxy_qianfan` extra — dropped. Reading every activated extra from the `dbgpt-core`/`dbgpt-ext` pyproject, deduping, and mapping to conda names produced the correct 68-dep set and caught both.

A follow-up optimizer check **`DEP-006`** ("upstream dep uses `pkg[extra]` — verify the extra's deps are flattened into `run:`, and that any sibling-output extra is expanded past its `pin_subpackage`") would catch this at gate-time alongside G10's proposed `DEP-005`. Tracked as a skill TODO; not yet shipped.

### G26. Loosening upstream `==` pins to `>=` requires patching the source pyproject when `pip_check: true` — the wheel METADATA bakes in the `==`

**Symptom**: a recipe follows the project's pin-loosening convention (rewrite every upstream `pkg==X` run-dep to `pkg >=X`); `validate_recipe` + `optimize_recipe` + `check_dependencies` are all clean and the package builds — then the test phase fails at `pip check`:

```
dbgpt 0.8.0 has requirement aiohttp==3.8.4, but you have aiohttp 3.14.1.
```

**Why**: loosening the *recipe's* `requirements.run` only changes what conda installs. It does NOT change the built wheel's `dist-info/METADATA`, which still carries upstream's `Requires-Dist: aiohttp==3.8.4` verbatim from `pyproject.toml`. `pip_check: true` reads that METADATA and enforces the `==`, so the loosened conda install (aiohttp 3.14.1) violates it. Worse, the pinned version usually isn't even on conda-forge (the reason you loosened), so there is no way to satisfy the `==`.

This is the **mirror image of G24 / the graphifyy upper-bound rule**: G24 says *mirror* upstream's load-bearing upper bounds in `run:`; G26 says when you *loosen* an upstream `==`, you must also loosen it in the wheel METADATA — i.e. patch the source — or `pip_check` rejects the build.

**poetry-core caveat — patch ALL THREE files; beware the local-vs-CI divergence (v8.43.0).** When the build backend is **poetry-core**, conda-forge's poetry-core builds the wheel METADATA from the sdist's bundled **`PKG-INFO`**, NOT from `pyproject.toml`. So a sed that patches only `pyproject.toml` **passes locally** (the local poetry-core happens to regenerate metadata from `pyproject.toml`) but **fails on staged-recipes CI** (CI's poetry-core reuses `PKG-INFO`'s `Requires-Dist`) — a green local `pip check` does NOT prove the CI wheel METADATA is loosened. A poetry sdist can carry the pin in **three** files — `pyproject.toml` (`pkg = "X"`), `setup.py` (`['pkg==X']`), and `PKG-INFO` (`Requires-Dist: pkg (==X)`) — so patch **all three** to be robust to whichever the backend reads:
```yaml
script: |
  sed -i -E 's/^pkg *= *"X"/pkg = ">=X"/' pyproject.toml
  sed -i -E 's/pkg \(==X\)/pkg (>=X)/' PKG-INFO
  sed -i -E 's/pkg==X/pkg>=X/g' setup.py
  ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```
And verify the *loosen* is runtime-safe (the newer version on cf must keep the API the consumer uses) — don't loosen blindly across a major bump. Case: pksuid 1.1.2 (staged-recipes #33895, Jun 25 2026) loosened `pybase62==0.4.3`→`>=0.4.3` (cf ships 1.0.0, which keeps `encodebytes`/`decodebytes`); the pyproject-only sed passed locally but failed CI `pip check` until `PKG-INFO` + `setup.py` were also patched.

**Fix**: rewrite the `==` pins to `>=` in the source `pyproject.toml` at build time, before `pip install`, so the wheel METADATA matches the loosened conda deps. A targeted regex that touches only PEP 508 version pins (`name==N`), leaving `<`/`<=` caps and `extra == "..."` / `python_version == "..."` markers untouched:

```yaml
build:
  script: |
    sed -i -E 's/([A-Za-z0-9])==([0-9])/\1>=\2/g' pyproject.toml
    ${{ PYTHON }} -m pip install . --no-deps --no-build-isolation -vv
```

The `([A-Za-z0-9])==([0-9])` guard is load-bearing: it matches `aiohttp==3.8.4` (alnum before `==`, digit after) but NOT `extra == "cli"` (space + quote) or `python_version=='3.9'` (quote after `==`). Verify on the real file (`grep -nE '[A-Za-z0-9]==[0-9]'` should be empty after; the file must still parse as TOML). For multi-line/structural rewrites use a checked-in Python helper instead (per G23). noarch:python builds run on one platform (linux), so a plain `sed` needs no `m2-sed`/Windows handling.

In a **multi-output** recipe, patch the pyproject of whichever output *originates* the pin, not just the one that fails: `pip_check` on output B (which requires `A[extra]`) reads A's wheel METADATA for the extra's deps, so loosening A's `pyproject.toml` (base + every extra) fixes both A's own test and B's.

**Case study**: DB-GPT v0.8.0 (Jun 17, 2026). The 7-output recipe loosened 13 `==` pins per the project convention, but the first build failed at the `dbgpt` (core) test with `pip check`: `aiohttp==3.8.4, but you have aiohttp 3.14.1` (+ chardet, importlib-resources). Fix: the `sed` above in the `dbgpt-core` + `dbgpt-ext` output build scripts (the only two carrying `==` pins; `dbgpt-app`/`dbgpt-client` read their loosened extras transitively via `pip check`). After the patch the wheel METADATA read `aiohttp>=3.8.4` / `psutil>=5.9.4; extra=='cli'` and pip_check passed. The spec's pin-loosening story (FR-2/S10) had assumed loosening the conda run-deps was sufficient — it wasn't.

### G27. A top-level `import` in a split package can eagerly pull a sibling's submodule whose deps are only declared under an extra

**Symptom**: a `noarch: python` recipe for one member of an upstream monorepo/workspace builds cleanly and `pip check` passes, but the import test fails — `ModuleNotFoundError: No module named 'bs4'` — with a traceback that walks *through a sibling package's submodule*:

```
import dbgpt_client → dbgpt_client.schema
  → from dbgpt_ext.rag.chunk_manager import ChunkParameters
  → from dbgpt.rag.knowledge.base import ...
  → from bs4 import BeautifulSoup        # ModuleNotFoundError
```

**Why**: `dbgpt-client`'s `__init__` eagerly imports a submodule that reaches into a sibling (`dbgpt_ext.rag`) which reaches into the core (`dbgpt.rag.knowledge`) which imports `bs4`. Upstream declares `bs4` only under `dbgpt-ext[rag]` (an optional extra `dbgpt-client` does not activate). The dep is a *hard* import for anything that touches that code path, but upstream's `[project.dependencies]` under-declares it. `import <bare core>` doesn't trip it (the bare `__init__` doesn't load the rag submodule), so only the *consumer's* import surfaces the gap — and only the import test catches it (`pip check` is happy because the wheel doesn't declare bs4).

**Fix**: find the exact import closure empirically, then add the missing dep(s) to the *importing* output's `run:`. Probe in the failed output's surviving `test_env` (rattler-build leaves it under `build_artifacts/<cfg>/test/test_<name>*/test_env`):

```python
# $TE/bin/python — iteratively import, install each missing module, repeat
import importlib, subprocess, sys
seen = set()
while True:
    try:
        importlib.import_module('dbgpt_client'); print('OK', sorted(seen)); break
    except ModuleNotFoundError as e:
        m = e.name.split('.')[0]
        if m in seen: print('STUCK on', m); break
        seen.add(m)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q',
                        {'bs4': 'beautifulsoup4', 'docx': 'python-docx'}.get(m, m)])
```

Add only what the closure actually needs (the DB-GPT case needed exactly `beautifulsoup4`, nothing more) — don't blanket-add the whole extra. Map import names to conda names (G7/G10). Put the dep on the output whose import fails; if several outputs import the same sibling submodule, the dep can go on the shared sibling's `run:` instead. Cheap pre-check: `grep '^\(from\|import\) ' <pkg>/src/<mod>/__init__.py` — a trivial `__init__` (only `from ._version import ...`) means the import test won't trip deep chains.

**Case study**: DB-GPT `dbgpt-client` (Jun 17, 2026). `import dbgpt_client` failed on `bs4`; the closure probe showed `beautifulsoup4` was the *only* missing module. Added it to `dbgpt-client`'s `run:` with a comment noting the under-declared transitive import. `dbgpt-app` already carried it via the `[rag]` flatten; the bare `dbgpt`/`dbgpt-ext`/`dbgpt-sandbox`/`dbgpt-app` import tests never tripped it (their `__init__` files import only `._version`).

### G28. An external dep's broken `dist-info` version (e.g. conda-forge `pdfminer.six` → 0.0.0) breaks `pip_check` for any dependent that pins it exactly

**Symptom**: `pip check` on an output fails with a mismatch you didn't introduce and can't fix by editing your recipe:

```
pdfplumber 0.11.9 has requirement pdfminer.six==20251230, but you have pdfminer-six 0.0.0.
```

The conda package's *own* version is correct (`conda-meta/*.json` shows `pdfminer.six 20251230`), but its bundled wheel `dist-info/METADATA` reports `Version: 0.0.0`. A *different* package (pdfplumber) pins `pdfminer.six==20251230` exactly, and `pip check` compares that against the bogus `0.0.0` string.

**Why**: a setuptools_scm-style fallback bug in the *external* feedstock (it built from a tarball without the git tag, so the wheel version resolved to `0.0.0`) — the same class as G24, but in a dependency you don't own. It is systemic across that package's builds, so no version pin of yours satisfies the exact-pinning dependent. The conda package functions correctly; only the metadata string is wrong, so the failure is a true false positive.

**Fix** (in priority order): (1) verify it's genuinely external and a false positive — compare the conda version (`conda-meta`) against the dist-info `Version:`, and confirm the dependent's exact pin is what trips it; (2) file an issue against the broken `<dep>-feedstock` (the durable fix is theirs — `sed` the real version into the wheel, per G24); (3) for *your* recipe, since there is no in-recipe fix, **disable `pip_check` on the single affected output** (not the whole recipe), with an inline comment citing the external bug, keeping `pip_check: true` everywhere else. Before disabling, run `pip check` manually in the test_env and confirm the broken-metadata line is the *only* failure — if the rest of the graph is consistent you lose almost nothing:

```yaml
tests:
  # pip_check disabled for THIS output only: conda-forge <dep> ships dist-info
  # Version 0.0.0 (feedstock metadata bug, issue #NNN) while the conda version
  # is correct; <other-dep> pins it exactly so pip check false-fails. Verified
  # the rest of the graph consistent. The other outputs keep pip_check.
  - python:
      imports: [<module>]
      pip_check: false
```

Dropping the offending dependent is the alternative, but if it's pulled via an activated extra you must *also* remove it from that extra's declaration (else `pip check` flags it as *missing*), and you lose functionality.

**Case study**: DB-GPT `dbgpt-app` (Jun 17, 2026). After fixing G26 + G27, the only remaining `pip_check` failure across the 78-package `dbgpt-app` graph was `pdfplumber … pdfminer.six==20251230, but you have pdfminer-six 0.0.0`. The conda `pdfminer.six` was correctly `20251230`; its dist-info said `0.0.0` across every build on the channel. With the rest of the graph manually verified consistent (a strong signal the G25 flatten + Q2 caps were right), `pip_check: false` was set on the `dbgpt-app` output only, documented inline; the other six outputs kept `pip_check: true`.

### G29. Multi-output recipe checkers are top-level-only — `optimize_recipe` TEST-001 and `check_dependencies` silently ignore `outputs[]`

**Symptom**: on a multi-output (`recipe:` + `outputs:`) recipe where every output has its own `tests:` and `requirements:`:
- `optimize_recipe` fires **TEST-001** ("Recipe has no tests section") and `validate_recipe` warns "No tests section defined", even though all outputs carry proper CFEP-25 test blocks.
- `check_dependencies` returns `{"found": [], "missing": []}` — it verified *nothing*.

**Why**: both checks read the *top-level* recipe keys (`tests:`, `requirements:`), which a multi-output recipe legitimately lacks (they live under each `outputs[i]`). The checkers don't traverse `outputs[]`. So TEST-001 is a **false positive** and `check_dependencies` is a **silent false-negative** — the dangerous kind, because "0 missing" reads as "all deps verified" when nothing was checked.

**Fix**: (1) **Trust conda-smithy + rattler lint** for multi-output structure — `validate_recipe`'s `conda-smithy lint: passed` + `rattler_lint_ran: true` are the real gates; the TEST-001 warning is noise when each output has tests. (2) To verify deps, **flatten every output's `run:` into a throwaway single-output recipe** and run `check_dependencies` on that:

```yaml
# /tmp/depcheck/recipe.yaml
schema_version: 1
package: { name: depcheck, version: "0.0.0" }
build: { noarch: python }
requirements:
  run: [ <every external dep from every output, version-stripped> ]
```

`check_dependencies` then resolves them via its batch-repodata path and suggests conda names for misses. In-flight prerequisite recipes from the same effort show as "missing" (not yet on conda-forge) — expected; the local channel covers them at build time. (3) The build's per-output test phase is the ultimate dep check (each test-env solve must succeed).

A follow-up: teach `optimize_recipe`/`check_dependencies` to walk `outputs[]` (tracked as a skill TODO alongside the proposed DEP-005/DEP-006).

**Case study**: DB-GPT 7-output recipe (Jun 17, 2026). `optimize_recipe` flagged TEST-001 despite all 7 outputs having CFEP-25 test blocks; `check_dependencies` returned empty/empty. Verified the 68 external deps by flattening them into `/tmp/dep-check/recipe.yaml` — all 67 conda-forge deps resolved (incl. renames `graphviz`→`python-graphviz`, `docker`→`docker-py`, `httpx[socks]`→`socksio`), and the 5 "missing" were exactly the in-flight prerequisites (auto-gpt-plugin-template + the 4 lyric-* recipes) the local channel supplied.

### G30. conda-forge `protobuf` is the Python bindings (no `protoc`) — Rust prost/tonic builds need `libprotobuf`; a stray host `protoc` masks it locally

**Symptom**: a Rust recipe whose build invokes `protoc` (a crate with a `build.rs` calling `tonic_build::compile_protos(...)` or `prost_build::compile_protos(...)`) builds **green locally** but fails on conda-forge CI — on every platform — at the cargo/wheel build:

```
error: failed to run custom build command for `<crate> (.../build.rs)`
Error: Could not find `protoc`. If `protoc` is installed, try setting the
`PROTOC` environment variable to the path of the `protoc` binary. ...
💥 maturin failed  /  × Building wheel for <pkg> did not run successfully.
```

**Why** (two interlocking facts):

1. **conda-forge's `protobuf` package is the Python bindings (`google.protobuf`) and ships NO `protoc` binary.** The `protoc` compiler lives in **`libprotobuf`** (`bin/protoc`). So `requirements.build: [protobuf]` does not put `protoc` on the build PATH — `prost-build`/`tonic-build` search PATH for `protoc` and find nothing. (`protobuf` as a *runtime* `run:` dep is correct and unrelated — the trap is only `protobuf`-as-a-build-dep-expecting-the-compiler.)
2. **Local builds mask it because a stray `protoc` leaks from the dev environment.** If a `libprotobuf` is installed in the developer's pixi/conda env, its `bin/protoc` is on PATH and leaks into the local `rattler-build` build, so the broken recipe builds green. conda-forge CI is hermetic — only the recipe's declared build deps are on PATH — so the gap surfaces only on CI. Classic "works locally, fails on hermetic CI."

**Fix**: use **`libprotobuf`** (not `protobuf`) in `requirements.build`. It provides `bin/protoc` on the build PATH on all platforms (`$BUILD_PREFIX/bin/protoc` on unix, `%BUILD_PREFIX%\Library\bin\protoc.exe` on win). `protoc` is a *build-platform* tool (it runs during the build to generate Rust), so it belongs in `build:` (not `host:`) — also correct for cross-compilation, where the protoc that *runs* must be the build platform's.

```yaml
requirements:
  build:
    - ${{ compiler("rust") }}
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    - libprotobuf        # provides bin/protoc for prost-build / tonic-build
```

If `protoc`-on-PATH still isn't found (rare), additionally `export PROTOC="$BUILD_PREFIX/bin/protoc"` inside the build script — not via `script.env:`, which does not shell-expand (G1).

**Hermetic local verification** — the general technique for any "works locally, fails on hermetic CI" tool gap is to hide the suspected stray host tool, then rebuild. The dev-env `protoc` is usually a *relative* symlink (`protoc -> protoc-NN.N.N`), so move the symlink aside (the real binary stays), confirm `command -v protoc` is empty, rebuild, then restore:

```bash
mv .pixi/envs/<env>/bin/protoc /tmp/protoc.bak     # the symlink; target binary remains
command -v protoc            # must print nothing
pixi run -e local-recipes recipe-build recipes/<name>   # must now build via the libprotobuf build dep
ln -sf protoc-NN.N.N .pixi/envs/<env>/bin/protoc   # restore (recreate the relative symlink)
```

If it builds green with the stray hidden, the build dep genuinely provides the tool. Watch the relative-symlink trap: `[ -e <moved-symlink> ]` reports it "missing" because its relative target no longer resolves from the new location — the binary itself never moved.

**Case study**: `lyric-py` / staged-recipes #33764 (Jun 17, 2026). `crates/lyric-rpc/build.rs` runs `tonic_build::compile_protos("proto/task.proto")`. The recipe listed `protobuf` in `build:`; CI failed on `linux_64` *and* `osx_64` with `Could not find protoc`. The local build had passed only because `.pixi/envs/local-recipes/bin/protoc` (a relative symlink → `protoc-33.5.0`, owned by `libprotobuf 6.33.5`) leaked onto the build PATH. Fix: `protobuf`→`libprotobuf`. Verified by hiding the stray protoc (`command -v protoc` → none) and rebuilding — all 4 py-variants built green sourcing `protoc` from the `libprotobuf` build dep.

### G31. Overriding `python_min` upward on an existing feedstock — v1 needs a recipe-local `conda_build_config.yaml` (+ rerender); v0 needs `{% set python_min %}`; `context.python_min` is silently ignored in v1

**Symptom**: an upstream version bump starts requiring a newer Python (e.g. `datetime.UTC` → 3.11+, `tomllib` → 3.11+, or an explicit `requires-python >=3.12`), so the `noarch: python` import/build test fails on the feedstock's default 3.10 floor. You raise `python_min` — and CI *still* builds and tests on 3.10.

**Why**: on an existing feedstock the build's Python floor comes from the **variant** `python_min` baked into `.ci_support/<cfg>.yaml` (default `3.10` from conda-forge-pinning), NOT from the recipe's `context:`.
- **v1 (`recipe.yaml`)**: adding `python_min: "3.11"` to `context:` does **not** propagate to `.ci_support` on rerender (verified: `conda-smithy rerender` leaves `.ci_support/*.yaml` `python_min` at `3.10`, empty diff). A local `rattler-build` that bypasses `.ci_support` *does* honor `context.python_min`, which masks the bug — the feedstock CI does not. You must add a recipe-local **`recipe/conda_build_config.yaml`** with `python_min: ["3.11"]`; conda-smithy reads the CBC and writes `3.11` into `.ci_support` on rerender.
- **v0 (`meta.yaml`)**: the jinja `{% set python_min = "3.11" %}` at the top of the recipe shadows the `.ci_support` variant at render time, so it overrides **directly** — no CBC, no rerender needed (`.ci_support` stays `3.10` but the build/test use 3.11).

**Fix**:
```yaml
# v1: recipe/conda_build_config.yaml  (then `@conda-forge-admin, please rerender`)
python_min:
  - "3.11"
```
```jinja
{# v0: top of recipe/meta.yaml #}
{% set python_min = "3.11" %}
```
Keep the `${{ python_min }}` / `{{ python_min }}` references in host/run/test; the override supplies the value. This is the existing-feedstock counterpart to the "declare `python_min` in `context:`" guidance in [Python Version Policy](#python-version-policy) — that context form is for fresh staged-recipes submissions; on a rendered feedstock the variant wins.

**Case study**: llms-py-feedstock #39 (Jun 2026) — `llms/main.py` imports `datetime.UTC` (3.11+); the 3.10 floor failed the import test. `context.python_min: "3.11"` left `.ci_support` at 3.10 after rerender; a recipe-local `conda_build_config.yaml` flipped it to 3.11 (built + tested green on 3.11). wagtail-sharing-feedstock #5 (v0) used `{% set python_min = "3.12" %}` for upstream's `requires-python >=3.12` and built on 3.12 with `.ci_support` still at 3.10.

### G32. Triaging autotick-bot version-bump PRs (flake vs. real fix) — and pushing the fix to the bot's branch

**Symptom**: a `[bot-automerge]` autotick PR has a red CI leg. Roughly half are transient infrastructure flakes (restart → green); half are real recipe defects (a restart reproduces them). And once you have a fix, a plain `git push` from a `gh pr checkout` clone lands a **stray branch on the canonical feedstock** instead of updating the PR.

**Transient FLAKE → `@conda-forge-admin, please restart ci`** (recipe is correct; no edit): the failure is *pre-build* (env-provisioning / source fetch) and other platforms/Pythons of the same run pass. Signatures:
- `failed to fetch <pkg>.conda … dispatch task is gone … runtime dropped the dispatch task` — pixi/CDN connection drop.
- `Fatal Python error: _Py_HashRandomization_Init: failed to get random numbers` — Windows agent entropy glitch.
- `Connection broken: IncompleteRead(... bytes read, ... more expected)` / `CondaMultiError` mid-download.
- `HTTP 503` / `error sending request for url` during base-env provisioning or source download.

**Real FIX (deterministic; a restart reproduces it)**: `ImportError: cannot import name 'X'` on a stdlib name → python floor (G31); `pip check` `<pkg> A has requirement B==X, but you have Y` → dep pin (mirror upstream, G24/G26); `BackendUnavailable: Cannot import 'hatchling.build'` → host build-backend dep wrong (upstream switched backend, e.g. poetry-core→hatchling under `--no-build-isolation`); `<pkg> does not exist` / `no candidates were found` → a dependency feedstock is behind/absent (blocked on *that* feedstock — see kiota/sqlglot below); linter `package.version … interpreted as a floating-point number` → quote `version:` (G14).

**Pushing the fix to the PR**: a `gh pr checkout <n>` clone's `origin` is the **upstream feedstock**, not the bot fork, so `git push` creates a stray branch on the canonical repo (delete it with `git push origin --delete <branch>`). Update the PR via a maintainer-edit push to the bot fork:
```bash
git push https://github.com/regro-cf-autotick-bot/<feedstock>.git HEAD:<pr-head-branch>
```
("Allow edits from maintainers" is on by default for bot PRs, so a base-repo maintainer can push.) Then `@conda-forge-admin, please rerender` per [the rerender-after-push rule](../../memory/feedback_always_request_rerender_after_feedstock_push.md), and always [build + test the fix locally first](../../memory/feedback_test_locally_before_push.md). When a fix is blocked on a prerequisite dependency feedstock (the dep version upstream pins isn't on conda-forge yet), don't loosen blindly — the clean path is to land the dep first; G26's source-patch loosen is the fallback when waiting isn't viable.

**Case study**: the 2026-06-17 batch — 12 autotick PRs triaged: 4 pure flakes (cocoindex/html-to-markdown/dlt/selectolax → restart), 6 real fixes pushed via maintainer-edit (python floor, dep bumps, backend swap, setuptools cap), 2 blocked on prerequisite dep feedstocks (microsoft-kiota-bundle on 5 sibling 1.10.3 bumps; collate-sqllineage on `sqlglot 29.0.1`).

### G33. Local rattler-build of a v1 feedstock recipe — don't pass `.ci_support` as a variant config; its strict `channel_sources` excludes the just-built package from its own test

**Symptom**: `rattler-build build --recipe recipe.yaml --variant-config .ci_support/linux_64_.yaml …` builds the package, then the **test** env solve fails with `<pkg> ==<ver> … excluded because due to strict channel priority not using this option from: 'file:///…/<out>/'` and/or `<dep> ==<X>, for which no candidates were found` — even when the dep is on conda-forge.

**Why**: `.ci_support/<cfg>.yaml` carries `channel_sources: [conda-forge]` (strict priority). rattler-build applies it to the *test* solve too, so the local output-dir channel (where the just-built package lives) is excluded by strict priority and the solve can't see the new package. On real CI, `build_steps.sh` wires the local channel correctly; the bare local invocation does not.

**Fix**: build with the conda-forge-pinning CBC (for `${{ python_min }}` resolution) and let rattler-build use its default channel + auto-added output-dir — do **not** pass `.ci_support` for a local test:
```bash
pixi run -e local-recipes rattler-build build --recipe recipe/recipe.yaml \
  --variant-config .pixi/envs/local-recipes/conda_build_config.yaml \
  --output-dir <out>
```
Distinguish this (a channel artifact of *your* invocation) from a genuine `no candidates` caused by a dependency feedstock being behind: re-check the dep's max version with `conda search -c conda-forge "<dep>==<X>"`. **Beware the misread**: conda search prints `  - <dep>==<X>` for a *not-found* spec (a `PackagesNotFoundError` listing) — easy to mistake for a match; a real hit prints a full `<name> <version> <build> <channel>` row.

**Case study**: collate-sqllineage-feedstock #33 (Jun 2026) — first local rattler-build with `.ci_support` failed with "strict channel priority" excluding the just-built package; re-running with only the pinning CBC removed that error and surfaced the *real* blocker — `sqlglot ==29.0.1` genuinely absent from conda-forge (max 28.10.1), initially misread as available from a not-found `  - sqlglot=29.0.1` listing.

### G34. `pkg_resources.declare_namespace` packages (e.g. `fs` / Pyfilesystem2) break under setuptools 81+ → `ModuleNotFoundError: No module named 'pkg_resources'`

**Symptom**: a recipe's import test fails at `import <X>` with `ModuleNotFoundError: No module named 'pkg_resources'`, and the traceback originates in a **dependency's** `__init__.py`, not the package being built. The dep imported fine until recently.

**Why**: setuptools 81 stopped vendoring `pkg_resources` by default and 82 removed it. Any installed dependency that runs `__import__("pkg_resources").declare_namespace(__name__)` at import time (legacy namespace packages — `fs` 2.4.16 / Pyfilesystem2 is the canonical case) then fails once the solver pulls setuptools ≥81, which it does by default because the dep declares only a bare, un-ceilinged `setuptools`.

**Fix**: the durable fix is in the *provider* feedstock (cap `setuptools <81` in its run deps, or drop `declare_namespace`). For the consumer recipe whose test is failing, cap it in `requirements.run` with a TODO:
```yaml
run:
  - <X>
  # <dep> calls pkg_resources.declare_namespace at import; setuptools 81+
  # removed pkg_resources. TODO: drop once <dep>-feedstock caps setuptools.
  - setuptools <81
```
**Case study**: fs.googledrivefs-feedstock #7 (Jun 2026) — `import fs` failed (`fs` 2.4.16 declares its namespace via pkg_resources) because the test env resolved setuptools 82.0.1. Capped `setuptools <81` in run; import + pip check passed.

### G35. noarch numpy env-marker selector collapse (a G12 refinement) — per-Python numpy run-dep selectors track numpy's *own* wheel-availability floor, not a package feature

**Symptom**: grayskull / AI emits a per-Python `numpy` run-dep selector on a `noarch: python` recipe, e.g.:
```yaml
run:
  - if: match(python, "<3.13")
    then: numpy >=1.26.4
    else: numpy >=2.1.0
```
This is a [G12](#g12-platform-conditional-run-deps-in-noarchpython-recipes-need-noarch_platforms-in-conda-forgeyml) violation — a noarch:python recipe carries **one** artifact, so per-Python `run:` selectors are invalid (the conda-smithy lint rejects them, and there is no single artifact for which a per-Python branch makes sense).

**Why**: the upstream PEP 508 markers `numpy>=1.26.4; python_version<"3.13"` / `numpy>=2.1.0; python_version>="3.13"` encode **numpy's own cp313 wheel-availability floor** — numpy 2.1.0 was the first release to ship cp313 wheels, so a project that wants to be installable on Python 3.13 has to floor numpy at 2.1.0 *there*. This is a property of numpy's release history, **not** a feature of the package that branches per Python version. There is no code path in the package that behaves differently on 3.12 vs 3.13.

**Fix**: collapse to the broadest floor — a single un-selectored `run:` dep:
```yaml
run:
  - numpy >=1.26.4
```
The install-time conda solver picks a numpy build compatible with the *installed* Python (on Python 3.13 it can only choose numpy ≥2.1, because that's the first cp313 numpy on conda-forge anyway), so the broad floor is correct on every Python. The noarch artifact stays valid; no `noarch_platforms`, no per-Python branch.

**Case study**: langchain-google-community 5.0.0 (Jun 19, 2026) — grayskull emitted the `match(python, "<3.13")` numpy split verbatim from upstream markers; collapsed to `numpy >=1.26.4` and the noarch recipe linted + built clean.

### G36. Stale conda-forge build whose wheel METADATA caps a dep tighter than its conda `run:` dep → `pip check` fails even though the conda solve succeeds

**Symptom**: a build's import test passes the conda solve, then `pip check` fails with `<outer-pkg> A has requirement <dep> !=…,<X,>=…, but you have <dep> Y` — for a dep whose conda `run:` constraint the solver *did* satisfy. The conda metadata and the wheel METADATA disagree.

**Why**: a single version of a package can have **two builds** on conda-forge — an older build whose conda `run:` dep was loosened (e.g. `mcp <2.0.0`) but whose **embedded wheel METADATA still bakes in the tighter upstream cap** (`mcp !=1.21.1,<1.23,>=1.19.0`), and a newer **metadata-patched** build whose conda dep was corrected to match. `pip check` reads the wheel METADATA, not the conda repodata. The solver, seeing only the loose conda `run:` dep on the stale build, is free to pick that stale build alongside a transitive dep that's too new for the wheel's *real* cap — so the conda solve succeeds but `pip check` fails.

**Fix**: raise the **outer** package's lower bound in *your* recipe so the solver is forced past the stale build to one whose wheel METADATA and conda dep agree:
```yaml
run:
  # >=2.14 forces past fastmcp's stale 2.13.3 build (loose conda dep,
  # tight wheel METADATA cap on mcp); 2.14's metadata-patched build agrees.
  - fastmcp >=2.14
```
This is a strict subset of upstream's intent (you're only excluding builds known to mis-declare), not a loosening. Distinguish from G24 (label≠dist-info on the *built* package) — G36 is a *transitive* dep's stale build poisoning *your* test.

**Case study**: toolguard (Jun 19, 2026) — `pip check` failed on `mcp` because the solver picked fastmcp's stale 2.13.3 build (conda `run: mcp <2.0.0`, wheel METADATA `mcp !=1.21.1,<1.23,>=1.19.0`). Floored `fastmcp >=2.14` to land on the metadata-patched build; pip check passed.

### G37. `[tool.uv]` no-build / source flags in an sdist are NOT runtime dependencies — read deps only from `[project.dependencies]`

**Symptom**: a recipe gains a phantom dependency (or a real dep gets misidentified) after reading a line like `apify-shared = false` from an sdist's `pyproject.toml` and treating it as a constraint.

**Why**: `[tool.uv]` (and `[tool.uv.sources]`, `[tool.uv.*]`) is **uv-tool-specific configuration**, not PEP 621 metadata. A line such as `apify-shared = false` under `[tool.uv]` is a uv no-build / source flag (e.g. "don't build this from source"), **not** a dependency declaration. The authoritative runtime dep list is PEP 621 `[project.dependencies]` (and `[project.optional-dependencies]`). Mistaking a uv flag for a dep both adds a non-existent blocker and **hides the real one**, because attention goes to the wrong line.

**Fix**: read deps exclusively from `[project.dependencies]` / `[project.optional-dependencies]`. Never source a dependency name or constraint from `[tool.uv.*]`, `[tool.hatch.*]`, `[tool.poetry.group.*.dependencies]` build-tool sections, or similar tool tables. When a dep looks odd, cross-check it against `[project.dependencies]` before adding it to the recipe.

**Case study**: apify-client 3.0.3 (Jun 19, 2026) — `apify-shared = false` under `[tool.uv]` was misread as a dependency constraint; the **real** blocker was `impit` (a genuine `[project.dependencies]` entry not yet on conda-forge). Ignoring the uv flag and re-reading `[project.dependencies]` surfaced `impit` as the actual prerequisite.

### G38. A compiled local-only prereq built for only ONE Python blocks consumers on other Python versions (compiled ≠ noarch)

**Symptom**: a consumer recipe's test-env solve fails to find a local-only dependency that you *did* build into the local channel — e.g. `impit ==0.13.0, for which no candidates were found`, even though `impit-0.13.0-py310...conda` is sitting in the output dir.

**Why**: a **compiled** prereq (Rust/PyO3, C-extension, anything not `noarch`) produces **one build per Python version** (`py310`, `py311`, …). A noarch dep ships a single artifact that satisfies every Python, but a compiled one does not — if you built `impit` only for `py310`, a consumer whose recipe requires `python >=3.11` (and whose test env therefore resolves 3.11+) cannot use the `py310` build. The solver correctly reports "no candidates" because there is no `py311` build of that compiled dep in the channel.

**Fix**: when a consumer's test-env solve fails on a compiled local-only dep, check the channel artifact's `py3XX` build-string segment against the consumer's `python_min` / required Python floor. Build the compiled prereq for **every** Python in the consumer's matrix (or at least the one the consumer's env will resolve) before building the consumer. Contrast with noarch local-only deps, where one build is enough.

**Case study**: apify-client (Jun 19, 2026, `python >=3.11`) — its test env couldn't resolve the channel's `impit-0.13.0-py310...` build (impit is a Rust/PyO3 compiled package, py310-only in the local channel). Rebuilding impit for py311 unblocked the apify-client solve.

### G39. setuptools_scm private-API `_version_helper` import breaks at metadata generation (cf ships setuptools_scm 8.x)

**Symptom**: the conda-forge build fails during metadata generation with `ImportError: cannot import name '_types'` (or `Configuration`, `fallbacks`, or anything under `version.*`) from `setuptools_scm`. The sdist wires its version via `[tool.setuptools.dynamic] version = {attr = ...}` pointing at a `_version_helper.py` / `_version.py` that imports **private** setuptools_scm internals.

**Why**: conda-forge ships `setuptools_scm` / `vcs_versioning` 8.x+, which **removed** the private internals (`_types`, `Configuration`, `fallbacks`, `version.*`) that older sdists reach into. The helper module was written against a pre-8.x private API that no longer exists, so importing it during `attr`-resolution explodes before any dependency even loads.

**Fix**: ship a checked-in, idempotent helper (e.g. `pin_version.py`) **in the recipe dir** that rewrites `pyproject.toml` to a **static** version (`$PKG_VERSION`) and strips the dynamic-version machinery (the `[tool.setuptools.dynamic]` block and the `_version_helper` reference). Run it as the **FIRST** build step. Then drop `setuptools-scm` / `gitpython` from `host` (no longer needed once the version is static). This sidesteps the broken private-API import entirely.

**Case study**: pymilvus-model 0.3.2 (Jun 19, 2026) — its `_version_helper.py` imported `_types` from `setuptools_scm`, which cf's 8.x lacks; a `pin_version.py` first-build-step rewrite to a static `$PKG_VERSION` + dropping `setuptools-scm`/`gitpython` from host fixed it.

### G40. A dependency can DROP a Python version in a newer release — a noarch consumer's declared floor then can't resolve the dep's latest build (refines G38)

**Symptom**: a `noarch: python` consumer with `python_min: "3.10"` fails its **py3.10 test leg** to resolve a dependency's latest build, even though the dep is on conda-forge — the dep's newest version raised its own Python floor and no py3.10 build exists for it.

**Why**: dependencies raise their Python floor between releases. ibm-watsonx-ai 1.5.x needs `python >=3.11`; 1.3.37 was the **last** py3.10-compatible line. A noarch consumer declaring `python_min 3.10` must resolve *every* hard dep on its py3.10 test env — if the only available build of a dep is py3.11+, the py3.10 leg has no candidate. This is G38's per-Python-build problem seen from the *version* axis rather than the *compile* axis: even a noarch dep can be effectively py3.11-only if its py3.10-compatible versions are all older than what the solver wants.

**Fix** — two correct responses:
- **(a)** ALSO build the dep's **last py3.10-compatible version** into the channel (e.g. ibm-watsonx-ai 1.3.37), so the consumer's py3.10 leg has a candidate; OR
- **(b)** recognize the consumer's **REAL floor is higher** and raise its `python_min` to match the dep's floor.

Always collapse the dep's per-Python env markers to the broadest floor (G35) so the consumer's *declared* floor stays valid — don't leave a per-Python selector that silently narrows resolution.

**Per-platform variant (compiled transitive dep).** The floor can also be forced by a **compiled** transitive dep that ships a Python version on *some* conda subdirs but not others. A `noarch` consumer must install on **every** platform at its declared floor, so a per-platform gap raises the **whole package's** honest floor (you cannot have a per-platform `python_min` on a single noarch artifact). Diagnose by querying each subdir's repodata for the dep's `pyXY` build strings: `curl -s conda.anaconda.org/conda-forge/<subdir>/repodata.json` and grep the dep at the pinned version. Fix per (b): raise `python_min` to the floor that holds on *every* platform.

**Run this check PROACTIVELY — before submitting, not after a red osx leg.** Every case study below is *reactive* (CI failed → diagnosed), but the cheap pre-submit check turns an opik-style red round-trip into a no-op. For each compiled transitive dep, parse every candidate build's `depends` for its `python` constraint, filter builds to the recipe's **pinned version range**, and confirm the consumer's floor (default py3.10) is covered on **every** target subdir (osx-64 + win-64 are the usual laggards; linux is already proven by the local build):
```python
# per (sub in osx-64, win-64): for builds of <dep> in [<lo>,<hi>), collect the python-minor each supports
import re; from packaging.version import Version
def pymin(depends):
    for d in depends:
        m=re.match(r'python\s+>=3\.(\d+)', d)
        if m: return '3.'+m.group(1)
cov={pymin(v['depends']) for v in pk.values() if v['name']=='<dep>' and Version('<lo>')<=Version(v['version'])<Version('<hi>')}
print('py3.10 covered?' , '3.10' in cov, sorted(c for c in cov if c))
```
If the floor is **not** covered on some subdir, raise `python_min` to the floor that holds everywhere (the opik fix). A clean result means the default floor is safe — submit without a bump (langchain-google-vertexai's pyarrow/bottleneck/numexpr all covered py3.10 → no bump, green first try). See also [G66](#g66-a-merged-staged-recipes-pr-is-not-immediately-installable--verify-the-prereq-is-live-on-the-cf-channel-before-submitting-its-dependent) for the verification-depth-by-dep-shape rule.

**Case study**: ibm-watsonx-ai / langchain-ibm / langflow (Jun 19, 2026) — langchain-ibm (noarch, py3.10) needed ibm-watsonx-ai, whose 1.5.x line dropped py3.10; resolved by building 1.3.37 (last py3.10 line) into the channel. **Per-platform case (Jun 26, 2026)**: langchain-litellm [#33917](https://github.com/conda-forge/staged-recipes/pull/33917) — noarch, declared py3.10, but its transitive **compiled** dep `fastuuid 0.14.0` (pulled via litellm) ships py3.10 on linux-64/win-64 yet only **py3.11+ on osx-64**, so the osx-64 py3.10 test leg had no candidate (osx-only failure). Real floor is 3.11; set `python_min: "3.11"`.

### G41. A hidden py3.11 floor via an unconditional PEP-655 / new-stdlib import overrides the consumer's declared `requires-python`

**Symptom**: a recipe declares `requires-python >=3.10` (and you set `python_min: "3.10"`), but the package genuinely cannot run on 3.10 — an `ImportError` for a stdlib symbol surfaces at import time on the py3.10 leg.

**Why**: a transitive hard dep imports a Python-version-gated stdlib symbol **unconditionally, with no fallback**. jsonquerylang imports `typing.NotRequired` (PEP 655, py3.11+) in **every** version, with no `try/except ImportError` or `typing_extensions` shim. That forces the *real* `python_min` of any consumer to 3.11+, regardless of the consumer's declared `requires-python >=3.10` — which is then aspirational / broken on 3.10. The upstream's stated lower bound is **not trustworthy** as the effective floor.

**Fix**: when a recipe's hard deps include a package with such an unconditional new-stdlib / PEP-655 import, set `python_min` to the **MAX of all transitive hard Python floors** — don't trust the upstream `requires-python` lower bound alone. Inspect the actual imports of hard deps when a declared floor looks suspiciously low.

**Case study**: langflow / langflow-base (Jun 19, 2026) — declared `>=3.10`, but its dep jsonquerylang unconditionally imports `typing.NotRequired` (py3.11+), making the genuine floor 3.11.

### G42. Verify the CURRENT version's artifact shape before assuming compiled — build shape can change across versions

**Symptom**: you reach for a compiled-package recipe template (stdlib, compiler, per-Python builds) based on a package's reputation as a binary wheel, but the latest version is actually pure-Python — or vice versa.

**Why**: a package's build shape can change across versions. milvus-lite was a C++ binary-wheel through 2.4 / 2.5, but **3.0 is a complete pure-Python rewrite** (faiss-cpu / pyarrow backend, `py3-none-any` wheel, `Root-Is-Purelib: true`, zero `.so`). Inferring "compiled" from an older version's reputation produces an over-complex recipe and may even make it look cf-unsubmittable when it isn't.

**Fix**: always inspect the **LATEST** version's actual sdist/wheel before choosing a template — check for `.so` / `.pyd` presence and `Root-Is-Purelib` in the wheel `WHEEL`/`RECORD`. The pure-Python path is simpler AND cf-submittable; don't pay the compiled-recipe complexity tax (or write off the package) based on a stale shape.

**Case study**: milvus-lite 3.0 (Jun 19, 2026) — assumed compiled (true for 2.4/2.5), but 3.0 ships a `py3-none-any` `Root-Is-Purelib: true` wheel with no `.so`; a noarch:python recipe is correct and cf-submittable.

### G43. v1 inline `# comment` on a list item trips conda-smithy's comment-selector lint — use a full-line comment ABOVE instead

**Symptom**: conda-smithy lint flags a comment-selector lint error on a `recipe.yaml` (v1) list item that carries a trailing `# comment` — even when the comment is plain prose inside the `extra:` block, not an actual selector.

**Why**: in recipe.yaml v1, conda-smithy parses a trailing `# comment` on a YAML **list item** as a potential selector and flags it. The selector heuristic doesn't distinguish "real selector" from "trailing prose", so any inline trailing comment on a list entry is a lint risk.

**Fix**: use a **FULL-LINE comment ABOVE** the item instead of a trailing one. This reinforces the comments-at-bottom convention (v8.31.0 / G31-equivalent): cfe rationale belongs in the bottom `# CFE comments` block, and any necessary list-item annotation that must stay in the body has to be a full line above the item, never trailing.

**Case study**: langflow recipe `cfe-*` block (Jun 19, 2026) — a trailing `# comment` on an `extra:` list item lint-failed under conda-smithy; relocating it to a full line above cleared the lint.

### G44. .NET / C# CLI tools have NO source-build path on conda-forge — repackage the self-contained release binaries per-platform

**Symptom**: asked to package a .NET (C#) CLI for conda-forge. None of the generators apply (it isn't PyPI / npm / CRAN / CPAN / LuaRocks), so `generate_recipe_from_pypi` & friends are useless. Attempting a from-source build is a dead end: there's no dotnet SDK to invoke, and even if there were, `dotnet restore` is a network operation that conda-forge's hermetic CI forbids.

**Why**: conda-forge has **no `dotnet-sdk` and no `dotnet-runtime` feedstock** (verified 2026-06-20 via `lookup_feedstock` — both `exists=False`), and the NuGet restore step is banned in the offline build sandbox. So a from-source .NET build cannot work on conda-forge today — fundamentally unlike **Rust** / **Go**, which DO have conda-forge toolchains plus a vendored-dependency story. Don't burn cycles trying to make `dotnet build` work; there is no toolchain to drive it.

**Fix**: repackage upstream's **self-contained, single-file release binaries** (one per platform/arch). .NET "self-contained" deployment **bundles the runtime into the executable**, so there is **NO run-dep on a dotnet runtime** — the binary runs standalone. This is also how Homebrew distributes these tools. Recipe shape (binary-repackage, NOT noarch):

```yaml
source:
  # One single-file source per conda subdir, gated by target-platform
  # selectors. file_name gives the download a stable name; no archive
  # extraction happens (the asset has no archive extension). sha256 per asset.
  - if: linux and x86_64
    then:
      url: https://github.com/<org>/<repo>/releases/download/v${{ version }}/<tool>-linux-x64
      sha256: <...>
      file_name: <tool>
  # ... linux/aarch64, osx/x86_64, osx/arm64, win ...
build:
  number: 0
  script:
    - if: unix
      then:
        - mkdir -p "${PREFIX}/bin"
        - cp <tool> "${PREFIX}/bin/<tool>"
        - chmod +x "${PREFIX}/bin/<tool>"
    - if: win
      then:
        - copy /Y <tool>.exe "%LIBRARY_BIN%\<tool>.exe"
tests:
  - script:
      - <tool> --version
```

Key points: **no `compiler()` / `stdlib()`** (nothing is compiled from source — STD-001 does not apply); **no `requirements`** in the simple case (runtime is bundled); **NOT `noarch`** (each artifact is a per-platform binary → `cfe-noarch: compiled`); **ship LICENSE in-recipe** (the bare binaries carry none — canonical License-File pattern (2)); set `cfe-source-kind: github-release-binary`.

**Caveats**:
- **Binary repackaging draws conda-forge reviewer scrutiny** (source-build is the standing preference). The "no .NET toolchain on conda-forge" justification is legitimate, but reviewers may still push back — decide **submit vs. local-only up front** with the user (per the "Ask First" boundary), and record the call in `cfe-on-conda-forge-status` + `cfe-forge-blocker-list`.
- **Upstream ships more arches than conda-forge has subdirs for** — `musl`, `linux-arm` (armv7), `win-x86`, `win-arm64` have no standard conda-forge subdir; the matchable set is the **standard 5** (linux-64, linux-aarch64, osx-64, osx-arm64, win-64). State the dropped arches explicitly.
- **.NET globalization may need system ICU and TLS may need OpenSSL at runtime.** The build host usually has system libs, so `<tool> --version` passes locally, but a clean conda env can fail at startup with `Couldn't find a valid ICU package installed on the system`. If that surfaces, add `icu` (and possibly `openssl`) to `run:`, or document `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1`. Leave `run:` minimal until real-world verification beyond the build host demands otherwise.
- **No upstream checksums file** is typical — compute each sha256 by streaming the asset (`curl -sSL <url> | sha256sum`), don't download-then-hash 5 × ~80 MB to disk.
- The same approach applies to any **prebuilt-single-binary** upstream where source-build is genuinely unavailable on conda-forge (some Go/Rust releases too) — but for Go/Rust prefer the real source build (toolchains + vendoring exist); reach for binary-repackage only when there's truly no toolchain, which is the *default* state for .NET.

**Case study**: cyclonedx-cli 0.32.0 (Jun 20, 2026) — `CycloneDX/cyclonedx-cli`, an Apache-2.0 **.NET 8** SBOM CLI. `dotnet-sdk` + `dotnet-runtime` both absent from conda-forge → no source path. Repackaged the 5 self-contained release binaries (linux-x64/arm64, osx-x64/arm64, win-x64) as a per-platform recipe with **zero run-deps**; dropped the upstream musl / linux-arm / win-x86 / win-arm64 assets (no cf subdir). linux-64 leg built GREEN and the packaged binary ran `cyclonedx --version` → `0.32.0` (exit 0); the other 4 legs were sha256-verified but not executed locally (cross-platform on a linux-64 host). Kept **local-only** (`cfe-on-conda-forge-status: pending-submission-to-conda-forge`) pending the binary-repackage submission decision.

### G45. A browser SPA (Vue/React/Svelte + Vite) is usually NOT conda-forge-submittable — run the viability gate first, then build local-only as a static-site + launcher

**Symptom**: asked to "package <web app> for conda-forge". The repo is a front-end single-page application — Vite/webpack + Vue/React/Svelte — that runs in a browser. None of the generators apply, and unlike a CLI/library there is nothing to `import` or run from a conda env. Forcing it onto staged-recipes is the wrong move; reviewers will (correctly) reject it.

**Why**: conda-forge packages **locally-runnable** CLIs, libraries, and apps built from a **published, versioned, downloadable** source. A browser SPA frequently fails several of those bars at once, and the failures are upstream facts you can't fix:

- **`"private": true`** in `package.json` — upstream explicitly forbids npm publication.
- **Not on the npm registry** (and no PyPI dist) — so the canonical npm recipe pattern (`npm pack` from the registry) has nothing to pull.
- **No GitHub releases/tags** — only a moving `main`; nothing stable to pin (conda-forge discourages commit-pinned sources for new submissions).
- **No `bin`** — it's a web SPA served by a web server, not a command. The right distribution is exactly what such projects already offer: a **hosted site** and/or a **Docker image**.

**Viability gate — run this BEFORE writing any recipe** (cheap, decisive):

```bash
PKG=$(curl -s "https://raw.githubusercontent.com/<org>/<repo>/main/package.json")
echo "$PKG" | python3 -c "import sys,json; d=json.load(sys.stdin); print('name',d.get('name'),'private',d.get('private'),'bin',d.get('bin'))"
NM=$(echo "$PKG" | python3 -c "import sys,json;print(json.load(sys.stdin).get('name',''))")
curl -s "https://registry.npmjs.org/${NM}" | python3 -c "import sys,json;d=json.load(sys.stdin);print('npm:', d.get('error','PUBLISHED'))"
curl -s "https://api.github.com/repos/<org>/<repo>/releases" | python3 -c "import sys,json;print('releases:',[r['tag_name'] for r in json.load(sys.stdin)])"
curl -s "https://api.github.com/repos/<org>/<repo>/tags"     | python3 -c "import sys,json;print('tags:',[t['name'] for t in json.load(sys.stdin)])"
```

If it's `private` / unpublished / untagged → **not conda-forge-submittable**. Tell the user, recommend the hosted site or Docker, and only build **local-only** if they still want it installable in their own channel.

**Local-only build pattern** (when the user opts in despite the above): build the static site and ship it + a launcher as a `noarch: generic` package.

- **`source`** — GitHub archive pinned to a `main` commit (no tag exists); `context.version` tracks `package.json`'s `version`, `context.commit` the SHA. On any "update", bump **both** together (no autotick path).
- **`build: noarch: generic`** + `script: { file: build.sh }`; **build dep `nodejs >=20`**.
- **build.sh**: `export BASE_URL=./` (relative asset paths so the site serves from any directory — most Vite configs read base from an env var), `npm ci` (lockfile present), then **`npx vite build`** — skip the upstream `vue-tsc -b` / `tsc` type-check step (dev-only; it doesn't change `dist/` and can break on a `main`-HEAD checkout). Copy `dist/.` to `$PREFIX/share/<name>/`, write a `$PREFIX/bin/<name>` launcher that serves it: `exec python -m http.server "${PORT}" --directory "$PREFIX/share/<name>"`. **run dep `python`** for the launcher.
- **`license_file: LICENSE`** resolves from the extracted GitHub archive (pattern 1).
- **`tests`**: `test -f .../index.html` + `test -x bin/<name>` + a `package_contents.files` check (the SPA itself can't be exercised headless).
- **cfe fields**: `cfe-source-kind: github-commit`, `cfe-noarch: generic`, `cfe-on-conda-forge-status: blocked-pending-prerequisites`, and a `cfe-forge-blocker-list` entry naming the upstream blockers (private / unreleased / not-on-npm / SPA).

**Caveats**:
- **The build runs `npm ci` (NETWORK).** Fine for a local build; conda-forge CI forbids it — another reason this is local-only, not submittable.
- The unix launcher is bash → **Windows not covered**; acceptable for a local-only linux/mac package. Verify the produced `index.html` references **relative** `./assets/...` paths (proves `BASE_URL=./` took effect) so the static server resolves them.
- Distinguish from **G6** (an npm *CLI* with a real `bin`, published to the registry — that uses the canonical `npm pack` pattern and can go to conda-forge). G45 is specifically the *private/unreleased browser-SPA* case with no CLI surface.

**Case study**: cyclonedx-bom-studio 0.9.2 (Jun 20, 2026) — `CycloneDX/cyclonedx-bom-studio`, an Apache-2.0 Vue 3 + Vite SBOM editor. `package.json` is `"private": true`, **not on npm**, **no releases/tags**, **no `bin`** — confirmed not submittable. Built **local-only**: pinned to `main` commit `f2a6d30b`, `npm ci` + `npx vite build` (`BASE_URL=./`) into a `noarch:generic` package shipping the 56-file static site under `share/cyclonedx-bom-studio/` + a `cyclonedx-bom-studio` launcher (`python -m http.server`). Built GREEN on linux-64; verified the packaged `index.html` used relative `./assets/` refs. `cfe-on-conda-forge-status: blocked-pending-prerequisites` with the upstream blockers recorded. Same session also mirrored + locally built the two *submittable* siblings already on conda-forge — `cyclonedx-python-lib` (multi-output) and `cyclonedx-bom` (PyPI `cyclonedx-bom`) — the contrast is the point: the Python lib/CLI belong on conda-forge; the browser SPA does not.

### G46. A stale local `meta.yaml`'s `noarch: python` flag can be WRONG for a genuinely-compiled package — the CURRENT sdist is the source of truth (the "local-meta-is-wrong" sibling of G42)

**Symptom**: a feedstock-refresh / regenerate pass copies the local mirror's old `meta.yaml` shape forward and emits a `noarch: python` recipe — but the package is actually a **compiled** C / Cython / C++ extension. The build then either fails (no compiler/`stdlib` declared) or, worse, "succeeds" as a noarch artifact that ships no native `.so` and is broken at import on every platform.

**Why**: an older `meta.yaml` in `recipes/<name>/` is a *historical* artifact — it may predate the package gaining a C extension, may have been authored noarch by mistake, or may reflect a different upstream era. Trusting its `noarch:` flag (or its absence of `compiler()`/`stdlib()`) when choosing the regenerated recipe's shape carries the stale mistake forward. This is the *complement* of [G42](#g42-verify-the-current-versions-artifact-shape-before-assuming-compiled--build-shape-can-change-across-versions): G42 warns against trusting a package's *reputation* (it was compiled once, assume it still is); G46 warns against trusting the *stale local meta.yaml* (it was authored noarch once, assume it still should be). Both resolve the same way — inspect the **current** version's actual artifact.

**Fix**: before fixing the build shape on a refresh, verify compiler / native-extension presence in the **current** sdist (don't trust the local meta's `noarch` flag):

```bash
curl -sL "https://pypi.org/packages/source/<x>/<name>/<name>-<version>.tar.gz" -o /tmp/s.tgz
tar tzf /tmp/s.tgz | grep -E '\.(c|cpp|cc|pyx|pxd|h|hpp|rs)$' | head   # any → compiled
tar -xzOf /tmp/s.tgz '*/setup.py' 2>/dev/null | grep -E 'Extension|cythonize|build_ext'  # setuptools C-extension markers
tar -xzOf /tmp/s.tgz '*/pyproject.toml' 2>/dev/null | grep -E 'cython|maturin|scikit-build|setuptools.*ext'  # build-backend markers
```

If the sdist carries `.c`/`.pyx`/`.cpp`/`.rs` sources or `setup.py` builds an `Extension`, the recipe is **compiled** (`cfe-noarch: compiled`) — drop `noarch: python`, add `compiler()` + `stdlib()`, and let the per-Python build matrix run. Update the cached `cfe-noarch` field to the verified shape so future regens don't relapse.

**Case study**: bulk sole-maintainer feedstock refresh (Jun 20, 2026) — the local `meta.yaml` for **hll** (a C extension whose import is `HLL`) and **skranger** (Cython/C++ wrapping the ranger random-forest library) both carried a stale `noarch: python` flag. The current sdists clearly ship native sources; both are genuinely compiled. The regenerated recipes were corrected to compiled (compiler + stdlib + per-Python matrix), not noarch.

### G47. A stale git-tracked recipe-dir `conda_build_config.yaml` (a verbatim copy of the global pinning CBC) breaks the build — lint errors + a variant `duplicate entry` collision; rattler-build auto-discovers it

**Symptom**: a compiled recipe in `recipes/<name>/` carries a **git-tracked** `conda_build_config.yaml` next to `recipe.yaml`, and:
- (a) `conda-smithy lint` fails with baseline-violation errors — `MACOSX_DEPLOYMENT_TARGET` / `c_stdlib_version` below the current conda-forge baseline (because the file is a *frozen* copy of an old global pinning CBC), and/or
- (b) the **build** hard-fails at variant rendering with `duplicate entry "<key>"` (e.g. `duplicate entry "libitk_devel"`) — the recipe-local CBC's keys collide with the pinning CBC that the local-build harness layers in.

**Why**: rattler-build (and conda-smithy) **auto-discover a `conda_build_config.yaml` adjacent to the recipe** and merge it into the variant config. A recipe-local CBC is meant to carry **recipe-specific** overrides only (e.g. `python_min`, a single pinned dep). When the file is instead a stale verbatim copy of the *global* `conda-forge-pinning` CBC (zero recipe-specific keys), every one of its hundreds of keys is re-declared on top of the real pinning the harness already supplies — producing duplicate-key collisions at build time — and its frozen baseline values (MACOSX_DEPLOYMENT_TARGET, c_stdlib_version) lint as below-baseline. The deployed conda-forge feedstocks carry **no** such recipe-dir CBC (the pinning comes from the rerender service), so the file is pure local cruft.

**Fix** (sanctioned): move it aside for the build, restore after, and flag the tracked file for deletion:

```bash
mv recipes/<name>/conda_build_config.yaml recipes/<name>/conda_build_config.yaml.bak
pixi run -e local-recipes recipe-build recipes/<name>     # builds clean against the real pinning
mv recipes/<name>/conda_build_config.yaml.bak recipes/<name>/conda_build_config.yaml   # restore for review
```

Then **flag the tracked CBC for deletion** in the refresh diff — it should not be committed (the deployed feedstock has none). Keep a recipe-local CBC **only** when it carries genuine recipe-specific keys (e.g. an upward `python_min` override per [G21](#g21-conda-smithy-mis-aligns-the-zip-keyed-is_python_min-flag-when-python_min-is-overridden-upward) / [G31](#g31-overriding-python_min-upward-on-an-existing-feedstock--v1-needs-a-recipe-local-conda_build_configyaml--rerender-v0-needs--set-python_min--contextpython_min-is-silently-ignored-in-v1)); a zero-override copy of the global CBC is always cruft.

**Detection**: a recipe-dir `conda_build_config.yaml` whose key set is a superset of (or identical to) the global pinning CBC, with no recipe-unique keys, is the signature. `diff <(sort recipes/<name>/conda_build_config.yaml) <(sort .pixi/envs/local-recipes/conda_build_config.yaml)` near-empty → cruft.

**Case study**: bulk sole-maintainer feedstock refresh (Jun 20, 2026) — **hll** and **jh2** both carried git-tracked recipe-dir `conda_build_config.yaml` files that were stale copies of the global pinning CBC. They triggered conda-smithy lint baseline errors (MACOSX_DEPLOYMENT_TARGET / c_stdlib_version) and a hard `duplicate entry "libitk_devel"` collision at build time. `mv …bak` for the build (clean), restored for review, flagged the tracked files for deletion (the deployed feedstocks have no such CBC).

### G48. "Rust / Go upstream" does NOT imply a heavy from-source compile — verify the actual PEP-517 build backend before sizing the build or adding `compiler('cxx')`

**Symptom**: a package's GitHub repo is dominated by Rust (or Go) code, so you reach for the full compiled-recipe apparatus — `compiler('rust')` / `compiler('cxx')`, `stdlib('c')`, a long build-time budget, maybe `cargo-bundle-licenses`. But the actual conda build is tiny and needs none of it; a speculative `compiler('cxx')` is dead weight.

**Why**: the language a project is *written in* on GitHub is not the same as what the **PyPI sdist's build backend does at install time**. Some "Rust" or "Go" Python packages ship a PEP-517 backend that **downloads a precompiled native artifact** at build time rather than compiling from source. The sdist has **no `Cargo.toml` / `.rs` / `.go`** — the backend fetches a prebuilt binary (e.g. a C-API shared lib) and wraps it. The build is fast (tens of seconds), needs no Rust/C++ toolchain in the recipe, and a `compiler('cxx')` you added "because it's Rust" never gets used.

**Fix**: inspect the **sdist's actual contents and build backend** before sizing the build or adding compilers:

```bash
tar tzf /tmp/sdist.tgz | grep -E 'Cargo\.toml|\.rs$|\.go$|go\.mod' | head   # empty → no from-source Rust/Go compile
tar -xzOf /tmp/sdist.tgz '*/pyproject.toml' | grep -A3 '\[build-system\]'    # what backend actually runs
```

No `Cargo.toml`/`.rs` in the sdist + a backend that fetches a binary → it's a **download-and-wrap** build: no `compiler('rust')`/`compiler('cxx')`, no `stdlib`, a short build. Add a compiler macro only when the sdist genuinely compiles native sources (G46's check). Drop any speculative `compiler('cxx')`. This pairs with [G42](#g42-verify-the-current-versions-artifact-shape-before-assuming-compiled--build-shape-can-change-across-versions)/[G46](#g46-a-stale-local-metayamls-noarch-python-flag-can-be-wrong-for-a-genuinely-compiled-package--the-current-sdist-is-the-source-of-truth-the-local-meta-is-wrong-sibling-of-g42) — always size the build from the sdist, never from reputation or the GitHub language bar.

**Case study**: wasmtime-py (Jun 20, 2026) — the repo is a Rust project, but the PyPI sdist ships **no `Cargo.toml` / `.rs`**: its PEP-517 backend **downloads a precompiled wasmtime C-API binary at build time** (build wall-clock ~46 s). A speculative `compiler('cxx')` was correctly dropped — the recipe needs no Rust/C++ toolchain at all.

### G49. Per-Python compiled ≠ abi3 — verify against `Cargo.toml` / setup.py before adding `version_independent` + `python-abi3`; a per-Python artifact needs a SIMPLE imports+pip_check test, not the CFEP-25 cross-version triad

**Symptom**: a stale Rust/PyO3 recipe carries `version_independent: ${{ is_abi3 }}` + a `python-abi3` host dep + matrix-collapse skip rule (and sometimes an `OPENSSL_DIR` hack), but the package's Cargo PyO3 features declare **no abi3** (`py_limited_api = false`). The recipe is treated as a single abi3 artifact when it's really a **per-Python** compiled build — so the CFEP-25 cross-version test triad (`python_version: [${{ python_min }}.*, "*"]`) is applied to it and the `"*"` (latest-Python) test leg can't load a `.so` built for a different Python.

**Why**: `version_independent` + `python-abi3` are correct **only** when upstream actually builds abi3 (`py_limited_api=True` / `pyo3/abi3-py3XX` Cargo feature) — one wheel covers all Pythons. When the Cargo PyO3 features carry **no abi3**, every Python gets its **own** compiled artifact, and there is no single artifact testable across Pythons. Applying the CFEP-25 triad to a per-Python artifact is a category error (a `py311` `.so` cannot be imported by the `"*"`-resolved newest Python). This is the build-shape sibling of [G38](#g38-a-compiled-local-only-prereq-built-for-only-one-python-blocks-consumers-on-other-python-versions-compiled--noarch): G38 is about *consumers* of a per-Python artifact; G49 is about *authoring* the per-Python recipe's test correctly.

**Fix**: verify abi3 vs per-Python from `Cargo.toml` / `setup.py`, mirror the deployed feedstock, and pick the matching test shape.

```bash
tar -xzOf /tmp/sdist.tgz '*/Cargo.toml' | grep -iE 'abi3|py_limited_api|pyo3.*features'   # abi3-* / py_limited_api=true → abi3
```

- **abi3 confirmed** (`pyo3/abi3-py3XX` or `py_limited_api=True`): keep `version_independent` + `python-abi3` + the matrix-collapse skip ([G21](#g21-conda-smithy-mis-aligns-the-zip-keyed-is_python_min-flag-when-python_min-is-overridden-upward) Variant B). One artifact → the CFEP-25 cross-version triad is appropriate.
- **No abi3 → per-Python build**: DROP `version_independent`, `python-abi3`, and any speculative `OPENSSL_DIR` hack. Use a **simple per-Python test** — `imports:` + `pip_check: true` with **no** `python_version` triad (or `python_version: ${{ python_min }}.*` only):

```yaml
tests:
  - python:
      imports: [<module>]
      pip_check: true
      # per-Python compiled artifact: no cross-version triad — a single
      # per-Python .so cannot be tested against a different Python.
```

**Case study**: json-stream-rs-tokenizer (Jun 20, 2026) — the stale recipe wrongly carried `version_independent` + `python-abi3` + an `OPENSSL_DIR` hack, but the Cargo PyO3 features declare **no abi3** (`py_limited_api=False`) → it's a per-Python compiled build. Fix: dropped all three, mirrored the deployed feedstock's per-Python shape, and used a simple imports+pip_check test (no CFEP-25 triad).

### G50. A newer CPython that drops a private C-API symbol breaks a compiled build / a host pin — cap the python matrix to upstream's supported range with `match(python, ">=N")` (NOT `py<N`, per G3)

**Symptom**: a compiled recipe builds fine on py3.10–3.12 but fails on **py3.13** (or whatever the newest matrix entry is) — either a C compile error (`error: '_PyInterpreterState_Get' undeclared` / a removed private C-API symbol) or a host-solve failure (a pinned dep has no wheel/build for the newest cpython, e.g. `numpy<2.0` with no cp313 build).

**Why**: each CPython release removes private/unstable C-API symbols and bumps the supported-numpy floor. A compiled extension (or a host `numpy<2.0` pin) that was valid through 3.12 can hard-fail on 3.13+ because the symbol is gone (C compile) or no compatible dependency build exists (host solve). conda-forge keeps adding newer Pythons to the matrix faster than every upstream supports them; the recipe must **mirror upstream's actually-published range**, not the full conda-forge matrix.

**Fix**: skip the unsupported Pythons with the **v1 `match()` form** — `build.skip: match(python, ">=N")` — never the v0 `py<N` form, which is silently ignored in v1 (see [G3](#g3-py--n-skip-selectors-do-nothing-in-v1-recipeyaml)):

```yaml
build:
  skip:
    - match(python, ">=3.13")   # upstream's private C-API / numpy<2.0 floor — drops cp313
```

Set the ceiling to match upstream's **published** wheel/Python range (check the latest sdist's `requires-python` upper bound and the actual PyPI wheel tags). When the cap is forced by a *host* dep (e.g. `numpy<2.0` with no cp313 wheel), document that in the cfe-comments block so a future numpy-2 migration can lift the skip.

**Case study**: bulk feedstock refresh (Jun 20, 2026) — **psycopg2-yugabytedb** failed the py3.13 C compile (`_PyInterpreterState_Get` removed in 3.13), and **datasketches** failed the py3.13 host solve (its `numpy<2.0` host pin has no numpy-1.x cp313 wheel). Both got `build.skip: match(python, ">=3.13")` mirroring upstream's supported range — not `py<313`, which v1 ignores.

### G51. A GitHub monorepo subdir may ship NONE of the release-time-generated assets — source the PyPI wheel instead, or you ship a broken empty package (a possibly-already-deployed REAL BUG)

**Symptom**: a recipe sourced from a GitHub tag/archive (per the usual G5/G16 "prefer GitHub source" instinct) builds to a tiny `.conda` (~15 KiB) that is **missing its runtime assets** — a web app's `www/` bundle, generated parsers, compiled protobufs, minified JS/CSS, etc. — and is broken at runtime, even though the build EXIT=0 and the import test (if shallow) passes.

**Why**: many monorepo Python packages **generate web/static assets at release time** (a build step that runs `npm run build` / `webpack` / a codegen pass) and ship the generated output **only in the published PyPI wheel**, never committing it to the GitHub repo. A from-source build of the GitHub subdir therefore packages an empty shell — the `www/` (or equivalent) directory simply isn't in the repo. This is the inverse of [G5](#g5-tree-sitter-pypi-sdists-inconsistently-strip-srctree_sitterh-headers--default-to-github-source) (where the *GitHub* source is the complete one and the *PyPI sdist* is stripped); here the **PyPI wheel** is the complete artifact and the GitHub source is incomplete. **Critically: the deployed conda-forge feedstock may already ship this broken empty package** — flag it prominently as a real bug, not just a local-refresh concern.

**Fix**: source the **PyPI wheel** (the artifact that actually contains the generated assets):

```yaml
source:
  # GitHub source ships none of the release-time-generated www/ assets;
  # they exist only in the published wheel. Source the wheel.
  url: https://pypi.org/packages/<py-tag>/<x>/<name>/<name>-${{ version }}-<py-tag>-none-any.whl
  sha256: <wheel sha256>
```

Verify before choosing the source — compare the GitHub archive's contents against the wheel's:

```bash
unzip -l <name>-<version>-*.whl | grep -iE 'www/|static/|dist/|\.min\.(js|css)$|assets/'   # generated assets present in wheel?
tar tzf <github-archive>.tar.gz | grep -iE 'www/|static/|assets/'                          # …absent from GitHub source?
```

Asset-bearing wheel + asset-free GitHub source → use the wheel. Set `cfe-source-kind: pypi-wheel`. If the deployed feedstock is sourcing GitHub and ships the empty package, that's a REAL BUG to fix at the feedstock.

**Case study**: h2o-lightwave-web (Jun 20, 2026) — the GitHub monorepo subdir ships **zero** `www/` web assets (generated at release time, present only in the PyPI wheel). A from-source GitHub build produced a broken empty ~15 KiB package; the **deployed feedstock likely ships this broken empty package** (flagged as a real bug to fix). Fix: source the PyPI wheel (1.8.9 is wheel-only). Adjacent to [G5](#g5-tree-sitter-pypi-sdists-inconsistently-strip-srctree_sitterh-headers--default-to-github-source)/[G16](#g16-pypi-varnish-cdn-degradation-on-packagessourceletter-route).

---

### G52. Bulk recipe sweeps poison a shared local channel — build each recipe into an ISOLATED per-recipe output dir

**Symptom**: during a multi-recipe sweep that builds every recipe into one shared `--output-dir`, a recipe's **test-env solve** fails on a dependency that demonstrably IS on conda-forge (e.g. `fixedint 0.1.6`), so it looks `build-clean-test-blocked` — but the recipe is fine.

**Why**: rattler-build treats the shared output dir as a local channel at higher priority than conda-forge. Once the sweep has built a NEWER version of some package (`fixedint 0.2.0`) into that channel, strict channel priority makes it SHADOW the OLDER conda-forge version (`fixedint 0.1.6`) a *different* recipe's transitive deps require → the solve picks the wrong local build and the test env fails. The contamination grows as the sweep fills the channel.

**Fix**: build each recipe into its OWN isolated output dir — `--output-dir build_artifacts/<sweep>/<recipe>` — so there is no cross-recipe shadowing. (These are independent, already-on-conda-forge feedstocks; their deps come from conda-forge, not from each other, so isolation is correct.) If a test-env solve fails on a dep that IS on conda-forge, suspect channel pollution BEFORE recording `build-clean-test-blocked` — rebuild isolated to confirm `success`.

**Case study**: azure-monitor-opentelemetry (Jun 21, 2026, co-maintainer total-coverage sweep) — its `azure-monitor-opentelemetry-exporter` dep needs `fixedint 0.1.6`, but the sweep's shared channel held a locally-built `fixedint 0.2.0` that shadowed it → false test block; an isolated `--output-dir` solved GREEN.

---

### G53. Refreshing an existing feedstock must RE-MERGE the deployed maintainer list — a regen emits only the invoker and silently drops co-maintainers

**Symptom**: regenerating `recipe.yaml` for an existing multi-maintainer feedstock (via grayskull / `generate_recipe_from_pypi`) produces an `extra.recipe-maintainers` list containing only YOUR handle — every other co-maintainer is gone. A stale local mirror may already carry this defect.

**Why**: the generator has no knowledge of the deployed feedstock's maintainer list; it emits only the invoking user. Shipping that as-is would (at submission) silently remove people who co-own the feedstock — a serious etiquette + governance defect.

**Fix**: ALWAYS fetch the deployed feedstock's `extra.recipe-maintainers` and ensure the local `recipe.yaml`'s list is a SUPERSET — re-merge every other handle (including team handles like `conda-forge/<team>`). Verify local set ⊇ deployed set before leaving any refreshed recipe. (Sole-maintainer feedstocks are trivially safe; this bites co-maintained / multi-maintainer ones.)

**Case study**: co-maintainer total-coverage sweep (Jun 21, 2026) — `airflow-code-editor` (dropped `xylar`) and `alang` (dropped `praeclarum`) both had stale local meta.yaml lists missing a co-maintainer; the re-merge rule caught + restored both. Drives `docs/specs/co-maintainer-feedstock-refresh.md`.

---

### G54. Source preference is `sdist > GitHub-source > wheel` — but the source must actually SHIP the module; verify before switching (existence ≠ usable)

**Symptom**: a recipe sources a PyPI **wheel** (`…-py3-none-any.whl`) and conda-forge's review nudges *"Detected pure Python wheel(s) in source … it's preferred to use a source distribution (sdist) if possible."* Reviewers prefer source builds. Conversely, naively switching a wheel recipe to "the sdist" can produce `ModuleNotFoundError` at the import test or a `0.0.0` version.

**Why**: conda-forge prefers building from source (sdist or VCS tag) over repackaging a wheel — source is auditable + reproducible. grayskull / `recipe-generator.py` falls back to a wheel when it can't find a PyPI sdist, but it **does NOT check the project's GitHub for a source tag archive**, and it does NOT verify the chosen source contains code. Two real failure modes:
- **Metadata-only / broken sdist.** Many PyPI sdists ship ONLY `pyproject.toml` + `PKG-INFO` (zero `.py` files) — the code lives only in the published wheel. `pip install .` builds an empty wheel → `ModuleNotFoundError` (e.g. `ibm-watsonx-orchestrate-core` 2.11.0 sdist has **0 `.py` files**; `jigsawstack` sdist omits a `requirements.txt` its build reads). For these the **wheel is correct** — document why.
- **Wheel-only on PyPI, but source IS on GitHub.** A package can publish only a wheel to PyPI yet keep source in a public repo/monorepo (e.g. `langflow-sdk` + `lfx-*` live in `langflow-ai/langflow` under `src/sdk`, `src/bundles/*`). The generator never checks GitHub and defaults to the wheel; the **GitHub tag archive is the preferred source**.

**Fix — the decision order** (verify each before accepting it):
1. **Usable PyPI sdist?** Confirm it ships the module: `curl -sL <sdist-url> | tar -tzf - | grep -c '\.py$'` — must be > 0. If yes, use the sdist (+ G55 backend).
2. **Else, GitHub source tag archive?** `https://github.com/<org>/<repo>/archive/refs/tags/v<tag>.tar.gz`, building the subdir for a monorepo — preferred over the wheel. **Monorepo wrinkle:** package version ≠ monorepo tag → carry a separate `monorepo_tag` context var and `pip install ./src/<sub>`:
   ```yaml
   context:
     version: "0.2.0"        # the package's own version
     monorepo_tag: "1.10.0"  # the repo tag that CONTAINS it — bump BOTH on update
   source:
     url: https://github.com/<org>/<repo>/archive/refs/tags/v${{ monorepo_tag }}.tar.gz
     sha256: <archive sha256>
   build:
     script: ${{ PYTHON }} -m pip install ./src/<sub> --no-deps --no-build-isolation
   ```
   Flag that **autotick cannot auto-bump this dual version** (it touches only one). Default to GitHub source; fall back to the wheel only when the monorepo download is prohibitive AND there's no standalone source repo.

   **Build the subdir from the FULL extraction, not an isolated copy:** a monorepo subdir's `pyproject.toml` can read its (dynamic) version from a file OUTSIDE the subdir via a relative path — e.g. hatchling `[tool.hatch.version] path = "../../src/<pkg>/__init__.py"`. `pip install ./packages/<sub>` run from the monorepo root resolves it; copying just the subdir elsewhere breaks the relative path → `0.0.0` / build error (G39). Verified: `ibm-watsonx-orchestrate-{core,clients}` read version from `../../src/ibm_watsonx_orchestrate/__init__.py`.
3. **Else (no usable sdist, no public source): the wheel is acceptable** for `noarch: python` / pure-Python — set `cfe-source-kind: pypi-wheel` + a comment ("sdist ships only metadata" / "wheel-only upstream, source not public"). The `<py-tag>` URL segment may change on a version bump.

**Always re-verify after a wheel→source switch**: the import test (right module name, G7), that the built version == `context.version` (dynamic-version sdists can build `0.0.0`, G39), and `pip_check`.

**Case study**: langflow closure (Jun 23, 2026) — `langflow-sdk` + the 4 `lfx-*` are wheel-only on PyPI but live in the `langflow-ai/langflow` v1.10.0 monorepo (`src/sdk`, `src/bundles/*`) → switched to the GitHub tag archive + subdir build (hatchling), GREEN. The generator had emitted wheels for all of them without checking GitHub — the gap this gotcha closes.

**Retroactive sweep** (Jun 24, 2026): recipes generated **before v8.42.0** predate this check, so they may sit on a wheel when a usable sdist / GitHub source exists. Audit with `grep -rl 'cfe-source-kind:\s*pypi-wheel' recipes/` and re-run the decision per recipe. The sweep migrated `jigsawstack` (sdist omits a `requirements.txt` its `setup.py` reads → GitHub tag, G55-note below) and `lfx` (→ monorepo `src/lfx`), and **overturned the initial `ibm-watsonx-orchestrate-{core,clients}` "keep the wheel" call**: their sdists are metadata-only, but the ADK monorepo ships the source at `packages/{core,clients}`, so both migrated to GitHub source — GREEN. **Lesson: "the sdist is empty" is NOT "there is no source" — always check GitHub before accepting the wheel.**

### G55. "No valid build backend found for Python recipe … using pip" → a SOURCE build needs an explicit build backend in `host` (wheel installs do NOT)

**Symptom**: build/metadata generation fails with *"No valid build backend found for Python recipe for package &lt;X&gt; using pip. Python recipes using pip need to explicitly specify a build backend in the host section … you likely should add setuptools to the host section."* — often **right after switching the source from a wheel to an sdist / GitHub source (G54)**.

**Why**: installing a **wheel** (`pip install <name>.whl`) unpacks a pre-built artifact and needs NO build backend — so wheel-sourced recipes carry only `host: [python, pip]`. Building from **source** (`pip install .` / `pip install ./src/<sub>`) runs the PEP 517 build, which **requires the backend named in the source's `[build-system]`** to be in `host`. The wheel recipe never needed it, so a wheel→source switch surfaces it immediately.

**Fix**: add the backend from the source's `pyproject.toml [build-system].requires` to `host`:
```bash
tar -xzOf <sdist>.tar.gz '*/pyproject.toml' | grep -A2 '\[build-system\]'   # or read the GitHub subdir's pyproject
```
| `[build-system].requires` | add to `host` |
|---|---|
| `setuptools` (+`wheel`) | `setuptools` (and `wheel` only if the build needs it; G8) |
| `hatchling` | `hatchling` |
| `flit-core` | `flit-core` |
| `poetry-core` | `poetry-core` |
| `pdm-backend` | `pdm-backend` |
| `scikit-build-core` | `scikit-build-core` |
| `maturin` | `maturin` (+ Rust toolchain) |
| `uv_build` | **`uv-build`** (conda name — hyphen, G10) |

Keep only the backend + `pip` (+ `python`); per **G8** don't re-add the legacy `wheel`+`setuptools` pair when a single PEP 517 backend is declared. `recipe-generator.py` should emit the backend automatically whenever it emits a **source** build — wheel-install recipes are the only ones that legitimately omit it.

**Case study**: langflow closure (Jun 23, 2026) — switching `langflow-sdk` (and the sdist attempt on `ibm-watsonx-orchestrate-*`) from wheel-install to source build hit this exact error; fixed by adding `hatchling` to `host` (the backend in `src/sdk/pyproject.toml`).

**Beyond the backend — the `setup_requires` / build-time network-fetch trap (source builds only).** A `setup.py` carrying `setup_requires=[...]` (legacy) — or any build step that reads the network — triggers an easy_install/pip **fetch during the build**. A **wheel** install never runs it, and a **local** source build **masks** it (the dev box has network); but conda-forge CI builds **offline**, so the fetch fails there. When switching wheel→source, strip legacy `setup_requires` (it only backs the deprecated `python setup.py test`; conda-forge runs the recipe's own `tests:`) with a build `sed`, or add the dep to `host`. Verified: `jigsawstack` — `sed -i.bak '/setup_requires/d' setup.py && rm -f setup.py.bak` dropped `setup_requires=["pytest-runner"]`. **Corollary of the live-verification principle: a clean LOCAL source build does NOT prove the recipe builds in conda-forge's offline CI** — reason about build-time network access explicitly.

### G56. Multi-output `noarch: python` build scripts must be cross-platform — bash `cd "$SRC_DIR/<sub>"` + `"$PYTHON"` fails on win-64; use `${{ PYTHON }} -m pip install ./<sub>`

**Symptom**: a multi-output recipe (N sdists → N outputs via a top-level `source:` list + `target_directory`) builds GREEN on linux + osx but the **win_64** leg fails at the build script:
```
(base) %SRC_DIR%>cd "$SRC_DIR/core_src"
The system cannot find the path specified.
(base) %SRC_DIR%>"$PYTHON" -m pip install . ...
'"$PYTHON"' is not recognized as an internal or external command
```

**Why**: `noarch: python` is built on **every** platform on staged-recipes (incl. win-64), and a per-output build script written in **bash** — `cd "$SRC_DIR/<sub>"` then `"$PYTHON" -m pip install .` — is run by **cmd.exe** on Windows, which doesn't understand `$SRC_DIR` / `$PYTHON` (bash variable refs; cmd uses `%SRC_DIR%` / `%PYTHON%`). The `crewai-suite`-style `cd "$SRC_DIR/<sub>"` idiom is bash-only and was never win-CI-tested. (Same bash-vs-cmd class as [G13](#g13-cwd-persists-across-script-list-entries--and-cmd-is-not-a-subshell-on-windows-cmdexe), specialized to the multi-output `target_directory` subdir-build pattern.)

**Fix**: drop the `cd` + shell-var form; use jinja `${{ PYTHON }}` (rendered to the literal interpreter path *before* any shell runs — neither bash nor cmd sees a variable) + a **relative subdir path** (the build CWD is already the work root holding the `target_directory` subdirs; the explicit `./` makes pip treat it as a path, not a PyPI name):
```yaml
build:
  noarch: python
  script: ${{ PYTHON }} -m pip install ./core_src -vv --no-deps --no-build-isolation
```
No `cd`, no `$SRC_DIR`, no `if: unix/else`. This is the standard noarch:python construct that passes win-64 across thousands of feedstocks; the only addition is `./<sub>` instead of `.`.

**Case study**: ibm-cos-suite (3-output core+s3transfer+sdk; staged-recipes #33886, Jun 25 2026) — `cd "$SRC_DIR/core_src"` + `"$PYTHON"` passed linux+osx, failed win_64 (buildId 1543755). `${{ PYTHON }} -m pip install ./core_src` per output → green. The repo's `crewai-suite` recipe carries the same latent bash-only bug.

### G57. A build-control env var set only via bash `export` is UNSET on win-64 — the build silently falls back to a network fetch (CMake FetchContent 404)

**Symptom**: a compiled recipe whose build script sets an env var that steers the build *away* from a network download — e.g. `export PYCBC_OPENSSL_DIR="${PREFIX}"` so CMake uses the conda OpenSSL — builds GREEN on linux + osx but **win_64** fails with a fetch + 404:
```
CMake Error ... downloading 'https://github.com/python/cpython-bin-deps/archive/openssl-bin-3.5.2.zip' failed
... The requested URL returned error : 404
```

**Why**: the script's `export VAR="${...}"` is **bash syntax**; on win-64 cmd.exe it does nothing, so `VAR` is **never set** on Windows. The upstream build's CMake/setup then takes its *fallback* path — a `FetchContent`/`urllib` download (here a prebuilt OpenSSL from `python/cpython-bin-deps`) — which 404s and is forbidden in hermetic CI anyway. The failure *looks* like a network/404 bug but the root cause is the **win-unset env var**. (Bash-vs-cmd class like [G56](#g56-multi-output-noarch-python-build-scripts-must-be-cross-platform), but here it degrades to a silent network fetch instead of erroring on the shell line.)

**Fix**: set build-control env vars **cross-platform**, splitting the script unix/win (`script.env:` can't — it doesn't shell-expand `${PREFIX}`/`%LIBRARY_PREFIX%`, G1). On unix the conda prefix is `$PREFIX`; on win the equivalent (where conda ships `lib/*.lib` + `include/`) is **`%LIBRARY_PREFIX%`** (= `%PREFIX%\Library`):
```yaml
build:
  script:
    content:
      - if: unix
        then: |
          export PYCBC_OPENSSL_DIR="${PREFIX}"
          ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
        else: |
          set "PYCBC_OPENSSL_DIR=%LIBRARY_PREFIX%"
          ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```
**Verify the var actually steers the build** by reading the upstream build code first (don't guess): for couchbase, `pycbc_build_setup.py` does `ssl_dir=os.getenv('PYCBC_OPENSSL_DIR'); cmake_extra_args += [f'-DOPENSSL_ROOT_DIR={ssl_dir}']`, and `CMakeLists.txt` only `FetchContent`s OpenSSL when `OPENSSL_ROOT_DIR` is **unset**.

**Case study**: couchbase 4.6.2 (staged-recipes #33893, Jun 25 2026) — `PYCBC_OPENSSL_DIR` set only via unix `export`; win_64 (buildId 1543796) FetchContent'd OpenSSL 3.5.2 → 404. Fixed by also setting it on win (`%LIBRARY_PREFIX%`); linux/osx were already green.

### G58. `lookup_feedstock` BEFORE submitting — a package already on conda-forge is rejected by the GHA linter ("feedstock exists"), even while the linting-service bot says "excellent"

**Symptom**: a staged-recipes PR's **linter** check fails, but the conda-forge-linting **service** bot comments the recipe is *"in excellent condition."* The two disagree. The GHA `linter.py` step's real output:
```
- recipes/<name>/recipe.yaml:
  - lints:
    - Feedstock with the same name exists in conda-forge.
```

**Why**: the package **already has a `conda-forge/<name>-feedstock`** (possibly maintained by someone else) — you can't submit to staged-recipes a package that already has a feedstock; updates go to the feedstock. The **two linters check different things**: the linting-*service* bot lints recipe **quality** (which can be perfect), while the GHA staged-recipes *linter.py* step also runs the **"feedstock already exists"** check. When they disagree, trust the **GHA linter** — it gates the PR.

**Fix — prevention**: run `lookup_feedstock(pkg_name=<name>)` (or the MCP tool) on **every** recipe before a staged-recipes submission — `exists=True` ⇒ already on conda-forge ⇒ do **not** submit (CLOSE the PR; the local recipe is a redundant mirror). This is load-bearing for **dep-closure** efforts (langflow / db-gpt class): a closure can contain popular packages already on conda-forge under another maintainer, and an unverified "net-new" assumption wastes one PR per false positive. A closure spec's *"already on conda-forge → consume, don't submit"* list must be **verified against `lookup_feedstock`**, never assumed. If the package needs a newer version or more platforms, that's a **feedstock PR** (version bump / platform expansion), not a staged-recipes submission.

**Case study**: impit (staged-recipes #33897, Jun 25 2026) — assumed net-new in the langflow closure + authored locally, but `conda-forge/impit-feedstock` v0.13.0 (maint. Pijukatel) already existed. Service bot said "excellent"; GHA linter rejected with "Feedstock with the same name exists." PR closed; the local recipe was repurposed as a feedstock platform-expansion mirror (osx-arm64 + linux-aarch64; aarch64 cross-build verified GREEN locally).

### G59. Prefer a SOURCE PATCH over an in-build `sed` for editing upstream source — bare `sed -i` fails on macOS/BSD sed (noarch builds on every platform), and reviewers ask for patches

**Symptom**: a `noarch` recipe edits the extracted upstream source with `sed -i 'script' file` (no backup-suffix) and builds on linux but fails the **osx** leg at the build script with `sed: 1: "<file>": extra characters at the end of p command` (or silently no-ops, so a later `pip check` fails). Separately, a reviewer asks *"Can we do this with a patch instead? … it becomes harder to maintain and less readable than a patch."*

**Why**: BSD/macOS `sed -i` **requires** the backup-suffix as the next token, so `sed -i 'script' file` parses `'script'` as the suffix and `file` as the script → error or wrong result (the G13/G23 bash-vs-BSD class). `noarch: python` recipes build on linux **and osx and win**, so *any* in-build `sed` runs on osx. Beyond portability, a **source patch is auditable** (the reviewer sees exactly what changed) and is the conda-forge-preferred mechanism for source edits.

**Fix**: move the source edit into a `source.patches:` entry — rattler-build applies it at extraction (before the build script), portably on every platform, and the build script reduces to just `pip install`. Generate the patch by applying the **exact** intended edit to the **real pinned source file** and diffing with `a/`,`b/` prefixes (rattler-build applies `-p1`):
```bash
cp <file> orig; sed -E '<the edit>' orig > new
diff -u orig new | sed -e '1s#^--- .*#--- a/<path>#' -e '2s#^+++ .*#+++ b/<path>#' > recipes/<name>/patches/0001-<desc>.patch
```
For a **multi-output** recipe, put the patches at the **top-level `source.patches`** — they apply once to the shared extracted source, then each output builds its already-patched subtree (don't re-`sed` per output).

**Exception — the edit must interpolate `${{ version }}`** (or another jinja value): a static patch can't carry it, so use a **portable** sed instead — `sed -i.bak 'script' file && rm -f file.bak` (the `.bak` suffix form works on **both** GNU and BSD sed). Example: injecting a placeholder `version = "0.0.0"` → `version = "${{ version }}"` (aurelio-sdk).

**Verifying the patch took effect** (don't trust "an artifact exists"): read the BUILT wheel's `dist-info/METADATA` and check `Requires-Dist:`. Distinguish **unconditional** `Requires-Dist: X` (main deps — what the patch + `pip check` govern) from `Requires-Dist: X ; extra == "..."` (extras — never stripped, not enforced by `pip check`); a "lean"-strip only touches the main `dependencies` array, so extra-marked entries legitimately remain. For a local build, the artifact lands in `noarch/` **only after tests pass** — a failed-test artifact is quarantined to `broken/`; check which dir to read pass/fail when the log is truncated.

**Case study**: graph-retriever [#33913](https://github.com/conda-forge/staged-recipes/pull/33913) (bare `sed -i '/pytest/d' pyproject.toml` failed the osx leg) + pksuid [#33895](https://github.com/conda-forge/staged-recipes/pull/33895) (reviewer ocefpaf requested patch-over-sed for the G26 pin-loosen) — both converted to source patches, GREEN. A repo-wide sweep (2026-06-26) converted **every** in-build `sed -i` source edit in `recipes/` to source patches (aurelio-sdk kept a portable `sed -i.bak` per the exception above). Cross-ref [G23](#g23-inline-sed--powershell-in-buildscript-hits-cmdexe-escape-hell--use-sed-with-m2-sed-on-windows-for-a-single-cross-platform-line) (portability when sed is unavoidable), [G26](#g26-loosening-upstream--pins-to--requires-patching-the-source-pyproject-when-pip_check-true--the-wheel-metadata-bakes-in-the-) (pin loosening), [G13](#g13-cwd-persists-across-script-list-entries--and-cmd-is-not-a-subshell-on-windows-cmdexe).

### G60. The strip-before-push must remove ONLY `extra.cfe-*` keys + `# CFE …` blocks — never the schema header or `context:` block

**Symptom**: a submitted staged-recipes recipe render-fails on **every** platform with `Jinja template error: Template rendering failed: undefined value (in <string>:1) (template: ${{ version }})` pointing at `recipe.yaml:3` (`version: ${{ version }}`). The **local** recipe is fine and builds.

**Why**: the strip that removes the CFE-local metadata before pushing (the `extra.cfe-*` keys + the bottom `# CFE metadata` / `# CFE comments` blocks — see "Never Add AI Comments…") over-reached and also deleted the leading `# yaml-language-server` + `schema_version: 1` header and/or the `context:` block. With `context.version` gone, `${{ version }}` (and `${{ python_min }}`) resolve to nothing → render fails before any build, on all platforms.

**Fix**: the strip removes **exactly** `extra.cfe-*` keys and the two bottom `# CFE …` blocks — **nothing above `extra:`**. Always diff the stripped recipe against the local source and confirm the header + `context:` survive. Quick gate: the submitted recipe's first non-comment line must still be `schema_version: 1`, and a `context:` block must precede `package:`.

**Case study**: langchain-litellm [#33917](https://github.com/conda-forge/staged-recipes/pull/33917) (Jun 26, 2026) — the pushed recipe had lost both the header and the `context:` block (render-fail on linux/osx/win); restoring them cleared the render error (a separate osx `python_min` issue then surfaced — see [G40](#g40-a-dependency-can-drop-a-python-version-in-a-newer-release--a-noarch-consumers-declared-floor-then-cant-resolve-the-deps-latest-build-refines-g38)).

### G61. GitHub commit-archive (`archive/<commit>.tar.gz`) sha256 can drift — GitHub re-gzips, breaking the recorded checksum

**Symptom**: a recipe sourcing `https://github.com/<org>/<repo>/archive/<commit>.tar.gz` fails at the **source-fetch** step (before the build even starts) with `× sha256 checksum validation failed for ".../src_cache/...<commit>.tar.gz"`. The recipe is unchanged and built fine previously.

**Why**: GitHub generates archive tarballs on demand and has, at times, changed the gzip framing of `archive/<commit>` (and `archive/refs/tags/<tag>`) tarballs, so the byte stream — and thus the sha256 — differs from when the recipe was authored, even though the underlying git tree is identical. Commit-pinned archives are the most exposed; uploaded **release assets** and PyPI sdists are byte-stable.

**Fix**: recompute the live sha256 and update the recipe — `curl -sL <url> | sha256sum`. Where a stable artifact exists, **prefer a release tarball / PyPI sdist** over `archive/<commit>`. For commit-pinned local-only recipes, just refresh the sha256 when it drifts — and treat it as a **latent fragility shared by every commit-pinned GitHub-archive recipe** in the same closure (the siblings may still match today but carry the same risk).

**Case study**: suite-st-transfers (Jun 26, 2026) — recorded `b3c875af…` vs live `e1082e44…`; refreshed the sha256 and the build proceeded. The 4 sibling `suite-*` recipes (same `archive/<commit>` pattern) still matched but carry the same risk.

### G62. NEVER ship `cfe-*` metadata — the strip is mandatory AND must be VERIFIED on the pushed artifact (verify, don't assume)

**Symptom**: a staged-recipes / feedstock PR ships the local-only `extra.cfe-*` keys and/or the `#### CFE metadata` + `# CFE comments` blocks (build-status, purls, upstream pointers, agent rationale). These are CFE-internal and must **never** appear in a submitted recipe.

**Why**: the strip is a **manual** step in the push flow (copy local recipe → remove the cfe block → push). A manual step can be forgotten or done partially, and the failure is **silent** — the recipe builds fine *with* `cfe-*` present (rattler-build ignores unknown `extra:` keys, conda-smithy lint doesn't flag them), so nothing catches it except a human reviewer. "I stripped it" is an assumption until proven.

**Fix**: treat the strip as mandatory **and verify it on the artifact you actually pushed** — never assume. After staging the recipe on the fork branch (and *before* opening the PR), grep the **pushed** recipe and abort if anything matches:
```bash
gh api "repos/<you>/staged-recipes/contents/recipes/<name>/recipe.yaml?ref=<branch>" \
  --jq '.content' | base64 -d | grep -nE 'cfe-|# CFE' && echo "ABORT: cfe metadata shipped" || echo "clean"
```
The stripped recipe ends at the `extra.recipe-maintainers` list; everything from the `#### CFE` marker down is removed. This is the **under-strip complement of [G60](#g60-the-strip-before-push-must-remove-only-extracfe--keys---cfe--blocks--never-the-schema-header-or-context-block)** (which warns against OVER-stripping the header / `context:`): strip **exactly** the cfe block — no less (G62), no more (G60). Applies to **both** staged-recipes and feedstock pushes. The same grep is a cheap repo-wide audit across every open/merged PR.

**The strip happens at push-time, on a COPY — never delete the `cfe-*` block from the LOCAL recipe.** The `cfe-*` block lives in the local `recipes/<name>/recipe.yaml` **permanently** (it caches identity + hard-won decisions + on-conda-forge status + local-build record that CFE/admin/maintainer tooling reads). The convention is **local-retains / strip-on-push**: when a recipe is submitted, update its local `cfe-on-conda-forge-status` → `pending-approval-on-conda-forge` and add `cfe-submission-pr:` — do **not** remove the block. Deleting `cfe-*` from the local recipe loses that state and is an error. (Live miss: qianfan's local cfe-block was deleted on 2026-06-26 — restored with the submitted status.)

**Case study**: 2026-06-26 — a full audit of all open + merged langflow-closure PRs (and qianfan #33935) found **every** pushed recipe clean, but the strip had been a manual, *unverified* step; adding the grep gate makes "clean" a checked fact, not an assumption.

### G63. Open staged-recipes PRs with the conda-forge **template + completed checklist** — `--body` REPLACES the template, it does not merge

**Symptom**: a staged-recipes PR is missing the reviewer-team guidance comment and the **Checklist** (License file packaged, source official, no vendoring, no static libs, build number 0, tarball-not-repo, maintainer confirmation). Reviewers and the `review-requested` bot flow rely on that checklist.

**Why**: GitHub only auto-populates `.github/pull_request_template.md` when a PR is opened **without** a body. Passing `--body` / `--body-file` to `gh pr create` (or a custom body via the API) **replaces** the template entirely — it does not merge with it. A custom description silently drops the checklist.

**Fix**: fetch the **live** template (don't hand-reconstruct — it drifts) and submit it as the body with the boxes ticked:
```bash
gh api "repos/conda-forge/staged-recipes/contents/.github/pull_request_template.md" --jq '.content' | base64 -d > /tmp/tmpl.md
# tick EVERY "- [ ]" box — including the "knowledge base" line, then:
sed -i 's/- \[ \]/- [x]/g' /tmp/tmpl.md
gh pr edit <pr> --repo conda-forge/staged-recipes --body-file /tmp/tmpl.md
```
Note the template path is **`.github/pull_request_template.md`** (lowercase). Keep the body to the template + ticked checklist (a short description is optional — when in doubt, template-only). The *"maintainers have posted a comment confirming…"* box is self-satisfied when the sole maintainer IS the submitter.

**Tick ALL boxes, including the "check the knowledge base before pinging a team" line** — it's a checklist item the submitter affirms, not a reviewer-only step, and leaving it unchecked reads as an incomplete checklist. (Earlier guidance wrongly carved out the knowledge-base box as an exception; that was an error — there are no exceptions, every box gets ticked.)

**Case study**: qianfan #33935 (Jun 26, 2026) — first opened with a custom `--body-file` description that dropped the checklist; fixed by re-fetching the live template and ticking the boxes. opik #33937 (Jun 26, 2026) — opened with the knowledge-base box left unticked under the old carve-out; corrected to all-boxes-ticked.

### G64. Request review with ONE language-matched ping AFTER CI is all-green — and check the PR's LABELS first (the bot's labels are the dedup signal)

**Symptom**: a staged-recipes PR gets the `@conda-forge/help-<lang>, ready for review!` ping posted **twice** (e.g. a manual ping + an automated one), or pinged while CI is still building — cluttering the thread / pinging the team prematurely.

**Why**: the ping is what moves a green PR into the review queue — a bot responds by adding the **`review-requested` label + the language label** (e.g. `python`). Once those labels exist, the request has already landed; posting the comment again is pure noise. The **labels (not the comment text) are the authoritative "already requested" signal** — comment-text grepping is a weaker proxy.

**Fix**: ping **exactly once**, with the team matching the recipe's language, only when **ALL three** preconditions hold — (a) **every check is green**, (b) the PR is **not a draft**, and (c) **`review-requested` is not already on the PR** (a prior ping already landed). A draft PR is not ready for review — pinging it is premature; the `review-requested` label is the authoritative "already requested" signal:
```bash
gh pr view <pr> --repo conda-forge/staged-recipes --json isDraft,labels \
  --jq '{draft: .isDraft, labels: [.labels[].name]}'
# ping ONLY if: all checks SUCCESS  AND  draft == false  AND  "review-requested" absent
gh pr comment <pr> --repo conda-forge/staged-recipes --body "@conda-forge/help-python, ready for review!"
```
Team by recipe language: pure-Python `noarch` → `@conda-forge/help-python`; C/C++ → `@conda-forge/help-c-cpp`; Rust → `@conda-forge/help-rust`; Go → `@conda-forge/help-go`; R → `@conda-forge/help-r`; … (full table is in the fetched `.github/pull_request_template.md`). The comment is terse — exactly `@conda-forge/help-<lang>, ready for review!`, no preamble. First-time contributors can't ping teams directly (use the `@conda-forge-admin, please ping team` bot command); established maintainers ping directly.

**Case study**: qianfan #33935 (Jun 26, 2026) — pinged twice (a manual ping, then an automated one that didn't check first); the bot had already applied `review-requested` + `python` after the first. The duplicate was deleted; the rule is now check-labels → ping-once.

### G65. Local-vs-CI linter parity — lint with the CURRENT conda-smithy via `pixi exec`, and run the `linter.py` checks conda-smithy doesn't

**Symptom**: a staged-recipes PR fails the `conda-forge-linter` *webservice* (or the GHA `linter`) on something the local gate "passed" — or the local lint is suspected stale.

**Why** — two parity gaps:
1. **conda-smithy version skew.** `validate_recipe` runs `conda-smithy recipe-lint --conda-forge` = the *same* linter the webservice uses (so it DOES catch most rules — e.g. it flagged opik's noarch selector). BUT the pixi env pins `conda-smithy >=3.44.6,<4` (→ 3.62.0): conda-smithy went **CalVer** (2026.x) and the `<4` cap freezes it on the old 3.x line, **deliberately** — the CalVer builds hard-depend on the `conda` package, which isn't in this rattler/conda-build pixi env (`pixi update conda-smithy` fails: *"conda-smithy 2026.6.14 would require conda >=4.2 … no candidates"*). So the env linter can lag the CI's ruleset.
2. **`linter.py` does MORE than conda-smithy.** The staged-recipes GHA `.github/workflows/scripts/linter.py` runs `conda_smithy.linter` recipe-lint **plus**: files-outside-`recipes/` (unless a `maintenance` label), feedstock-with-same-name-exists, recipe-exists-in-bioconda (hint), conda-package-name-already-exists. `validate_recipe` runs none of those.

**Fix** — before any staged-recipes submission:
- **CI-parity lint with the current conda-smithy, ephemerally** (no env change — the `<4` pin stays): `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/<name>` — `pixi exec` solves the CalVer conda-smithy + its `conda` dep in a throwaway env, exactly matching the webservice. Treat its output as authoritative; the env's 3.62.0 `validate_recipe` is the fast first pass. **Never dismiss a lint as a "false positive" (e.g. the G12 noarch-selector escape hatch) without confirming against this current-version lint.**
- **Run the `linter.py` extras:** `lookup_feedstock(<name>)` (feedstock-exists, [G58](#g58-lookup_feedstock-before-submitting--a-package-already-on-conda-forge-is-rejected-by-the-gha-linter-feedstock-exists-even-while-the-linting-service-bot-says-excellent)); confirm the conda package name isn't already on conda-forge; confirm all changed files are under `recipes/` (else the linter rejects unless `maintenance`). bioconda-name overlap is a hint, not a blocker.
- **Per-platform issues need per-platform analysis** — `recipe-build` is **host-only** (linux), so an osx/win-only failure (e.g. opik's osx-64 `litellm→fastuuid` py3.10 gap, [G40](#g40-a-dependency-can-drop-a-python-version-in-a-newer-release--a-noarch-consumers-declared-floor-then-cant-resolve-the-deps-latest-build-refines-g38)) won't surface locally; for compiled transitive deps run the G40 per-subdir repodata check before submitting.

**Case study**: opik #33936 (Jun 26, 2026) — local `validate_recipe` (3.62.0) flagged the noarch selector (which was wrongly dismissed), but missed nothing else the linter caught; the osx-64 fail was a per-platform build gap, not a lint gap. `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/opik` → "in fine form" after the fix, matching the green CI. (Env `conda-smithy` stays pinned `<4` because CalVer needs `conda`; the pixi.toml comment records the `pixi exec` parity command.)

### G66. A MERGED staged-recipes PR is NOT immediately installable — verify the prereq is LIVE on the cf channel before submitting its dependent

**Symptom**: a consumer recipe whose only blocker "just merged" is submitted, and its staged-recipes CI fails to **solve** (`nothing provides <prereq>` / unsatisfiable) — even though the prereq's PR shows MERGED.

**Why**: merging a staged-recipes PR creates the **feedstock**, which then has to run its own CI to **build + upload** artifacts to the `conda-forge` channel. That lag is minutes-to-hours (longer if the feedstock build is red or needs a rerender). "PR merged" ≠ "package installable" — there is a window where the feedstock exists but no artifact is on the channel yet, so any dependent submitted in that window fails to solve on CI. The local mirror can also mask this: a build against the **local channel** (which holds your locally-built prereq) goes green while the real conda-forge channel still has nothing.

**Fix**: before submitting a consumer whose prereq recently merged, confirm the prereq is **actually on the cf channel at a version that satisfies the pin** — don't trust the merged state:
```bash
# fresh repodata (a CACHED snapshot is unreliable for version maxima/floors — re-fetch for floor checks)
curl -s "https://conda.anaconda.org/conda-forge/noarch/repodata.json" -o /tmp/cf-noarch.json
python3 - <<'PY'
import json; from packaging.version import Version
pk={**(d:=json.load(open('/tmp/cf-noarch.json'))).get('packages',{}),**d.get('packages.conda',{})}
vs=[v['version'] for v in pk.values() if v['name']=='<prereq>']
ok=[x for x in vs if Version('<lo>')<=Version(x)<Version('<hi>')]   # the consumer's pin range
print('satisfying builds on cf:', sorted(set(ok)) or 'NONE — DO NOT SUBMIT YET')
PY
```
Then run a **local build that resolves against conda-forge** (not just the local mirror) as the authoritative solve. Verification depth scales with the consumer's dep shape: **pure-python deps** → confirm-prereq-live + build is enough; **compiled transitive deps** → ALSO run the [G40](#g40-a-dependency-can-drop-a-python-version-in-a-newer-release--a-noarch-consumers-declared-floor-then-cant-resolve-the-deps-latest-build-refines-g38) per-subdir python-floor check **proactively** (before submit, not after a red osx leg).

**Case study**: the 2026-06-27 § B′-consumer batch (langflow closure) — trustcall (←dydantic #33898), langchain-graph-retriever (←graph-retriever #33913), langchain-google-vertexai (←google-cloud-vectorsearch #33914), langchain-sambanova (←sambanova #33916). Each prereq's MERGED PR was cross-checked against live cf repodata (dydantic 0.0.8, graph-retriever 0.8.0, sambanova 1.9.1+1.10.0 all confirmed on-channel) *before* submitting the consumer — all six (incl. opik #33937, qianfan #33935) went green first try, no solve-fail round-trip. The cached snapshot trap was real: a reused `/tmp/cf-noarch.json` reported pydantic 2.9.2 / typing_extensions 4.9.0 as "latest" (stale), but the fresh build resolved the true cf pydantic 2.13.4 — floor checks must use fresh data or the build's own solve.

### G67. An external feedstock's stale `run_constrained` can block a consumer — it lives in `constrains`, NOT `depends`, so verify with the REAL consumer solve (a narrow dry-run misses it)

**Symptom**: a consumer recipe's test-env solve is unsatisfiable on a dependency that's clearly on conda-forge at a compatible version — and a narrow "does X co-install with Y" dry-run of the *direct* deps passed, so the conflict seems impossible.

**Why**: a conda package can carry `run_constrained` entries (surfaced as `constrains` in repodata) — soft pins that **do not pull the package** but **bind if that package is present in the env for any other reason**. A feedstock can add stale `run_constrained` that upstream never declared (a convenience copied from an old release's "extended testing deps"). It is invisible to:
- a `depends`-only check (the pin is in `constrains`, a separate field); and
- a **narrow proxy dry-run** that solves only the direct deps — if none of those *pull* the constrained package, the constraint never activates, so the dry-run is falsely green. The constraint only bites once the **real consumer** (with its full hard-dep set) drags the constrained package into the env.

**Fix**: verify a cross-package conflict claim against the **real consumer's full pin set**, not a hand-picked subset — the authoritative check is a solve/build of the actual consumer, not `mamba create X Y`. When you do hit such a conflict, inspect the blocker's **`constrains`** (not just `depends`): `python -c "import json; [print(v['build'], v.get('constrains')) for v in <repodata>.values() if v['name']=='<dep>']"`. Compare every `constrains` entry against the consumer's hard pins; one whose range can't intersect the consumer's pin is a **feedstock bug** — fix it in the feedstock, exactly like a `depends` skew. This is the `constrains`-axis sibling of the langchain `depends` text-splitters skew.

**Staleness is "diverges from the CITED SOURCE," NOT "cf has a higher version" — the latter is a false-positive generator.** Do not flag a `run_constrained` cap stale just because conda-forge ships a version above it. Optional-integration constraints **intentionally** cap to the *provider's* supported range, which legitimately lags the latest cf build. Counter-example: langchain's `run_constrained: groq >=0.4.1,<1` looks "stale" (cf has groq **1.5.0**) but is **correct** — upstream `langchain-groq 1.3.11` pins `groq>=0.30.0,<1.0.0` (it doesn't support groq 1.x), and the feedstock mirrors that; a consumer co-installing langchain + groq 1.x genuinely shouldn't, so the `<1` cap is protective, not stale. The real test: does the cap match the **cited source's CURRENT pin** (the upstream file / provider feedstock the comment points at)? Re-check the source, not cf-latest. (aiosqlite WAS stale because langchain's own `extended_testing_deps.txt` moved `<0.20`→`<0.23`; groq is NOT, because `langchain-groq` still pins `<1`.)

**Fix the cap to the AUTHORITATIVE value, don't guess a loose bound.** When the stale entry is annotated as copied from a pinned upstream file (langchain's run_constrained block cites `…/extended_testing_deps.txt` at a specific tag), the correct fix is to **re-sync to the CURRENT version's file** — bump the cited tag and copy the value verbatim — not to arbitrarily widen it (a guessed `<1.0` may over-admit). Read the source the comment points at: e.g. langchain `1.3.11`'s `libs/langchain/extended_testing_deps.txt` pins `aiosqlite>=0.19.0,<0.23` (the `1.2.0` file said `<0.20`); the durable PR is `>=0.19.0,<0.23` with the comment's tag bumped `langchain==1.2.0` → `1.3.11`.

**Case study**: langflow-suite 1.10.1 (Jun 27, 2026). lfx built green, but **langflow-base** failed its solve: cf `langchain 1.3.11` carries `run_constrained: aiosqlite >=0.19.0,<0.20` (a `langchain==1.2.0`-era "extended_testing_deps" cap, **absent from upstream langchain**), which collides with langflow-base's upstream-accurate hard `aiosqlite >=0.20.0`. An earlier `mamba create langchain langchain-classic` dry-run had "proven Skew-1 resolved" — but neither pulls aiosqlite, so the `constrains` never fired; only the real langflow-base solve (which hard-deps aiosqlite≥0.20) exposed it. Fix: a langchain-feedstock PR re-syncing the cap to langchain 1.3.11's `extended_testing_deps.txt` → `aiosqlite >=0.19.0,<0.23` (NOT a guessed `<1.0`; the `1.2.0`-era file said `<0.20`). The other 15 `run_constrained` entries were unchanged 1.2.0→1.3.11 and non-binding (verified: defusedxml 0.7.1 satisfies both, the rest aren't langflow-base deps) — so the surgical single-pin fix is the minimal defensible PR.

### G68. After an upstream/feedstock skew resolves, PURGE the obsolete local workaround build — stale higher-build artifacts shadow the real cf package under strict channel priority

**Symptom**: a recipe that *should* now resolve cleanly (after a skew was fixed upstream) still fails its local test-env solve — the error mentions "excluded because due to strict channel priority not using this option from `file://…/build_artifacts/`", or a dependency resolves to an old version that no longer satisfies the recipe's pins.

**Why**: local verification adds `build_artifacts/<subdir>/` as a **higher-priority** channel than conda-forge. With strict channel priority, the solver takes a package from the highest-priority channel that has it — so a stale **workaround build** left in the local channel (e.g. a `langchain 1.2.18` rebuilt during a skew, or a higher build-number rebuild) **shadows** the real, now-fixed conda-forge package. The recipe is correct; the local channel is lying.

**Fix**: when a skew/upstream issue resolves, **delete the obsolete workaround artifacts** from `build_artifacts/<subdir>/<noarch|subdir>/` and **re-index** (`python -m conda_index build_artifacts/<subdir>`) before re-testing. Confirm the package is gone from the local repodata, so the test resolves the real cf version. (If you still need a workaround for an *un*-resolved skew, build it at the lowest viable version/build-number and remember it's masking cf — it WILL cause a false green/red later.) Local-channel staleness is a top cause of "passes/fails locally but the opposite on CI."

**Case study**: langflow-suite 1.10.1 (Jun 27, 2026) — after bumping to `langchain~=1.3.0`, the lfx test failed with strict-priority "excluded" noise; root cause was the obsolete `langchain 1.2.18` skew-workaround (and `litellm 1.89.3`) still sitting in `build_artifacts/linux64/noarch/`. Strict priority picked local 1.2.18 (failing the new `>=1.3.0` pin) and refused cf's 1.3.x. Purging both + re-indexing let the tests resolve cf `langchain 1.3.11`.

### G69. A multi-output / suite version bump can CASCADE to a sibling recipe bump via a tightened cross-dep — bump + rebuild the sibling locally AND flag the submitted PR

**Symptom**: after bumping a multi-output suite to a new version, an output's `pip_check` fails with `<output> X.Y.Z has requirement <sibling>>=A.B.C, but you have <sibling> A.B.(C-1)` — the new upstream tightened its requirement on a package you maintain separately.

**Why**: upstream packages raise their floors on sibling/companion packages between releases. A suite bump that only edits the suite recipe leaves the **sibling recipe** (and its already-submitted PR) at the old version, which no longer satisfies the bumped suite's tightened cross-dep. The suite builds (run deps aren't checked at build time) but **`pip_check` in the test catches it**.

**Fix**: treat a suite bump as potentially **multi-recipe**. When the bump tightens a cross-dep on a package you own: (1) bump that **sibling recipe** to a satisfying version and rebuild it into the local channel so the suite test passes; (2) update the suite's own pin to match upstream's tightened floor; (3) if the sibling is **already submitted**, record in its `cfe-forge-recipe-updates-needed` that the open PR must bump too (a `>=` pin on an unmerged-at-old-version sibling is a real submission blocker).

**Case study**: langflow-suite 1.10.1 (Jun 27, 2026) — lfx 1.10.1 raised `langflow-sdk>=0.2.1` (was satisfiable by 0.2.0). The local channel + submitted PR #33856 had langflow-sdk 0.2.0 → lfx `pip_check` failed. Fixed by bumping the `langflow-sdk` recipe 0.2.0→0.2.1 (monorepo_tag 1.10.1, same archive), rebuilding it locally, raising the lfx pin to `>=0.2.1`, and recording in langflow-sdk's `cfe-forge-recipe-updates-needed` that #33856 must bump to 0.2.1.

### G70. Reconcile a recipe's OWN `run_constraints` to upstream's real extra pins — it's soft (metadata-only, lint-verified), so it's a safe high-value faithfulness pass

**Symptom**: a multi-output suite recipe carries hand-authored `run_constraints` with placeholder floors (`>=0.1`) or bare names instead of upstream's real optional-dependency pins — the soft constraints "work" but are uninformative and diverge from upstream.

**Why**: `run_constraints` are advisory (constrain-if-present, never installed), so a `>=0.1` placeholder passes build + lint while telling a downstream solver nothing useful. The faithful values live in the upstream `[project.optional-dependencies]` (and the aggregating `[complete]` extra) of the package's pyproject — the recipe should mirror those. This is the **inverse** of [G67](#g67-an-external-feedstocks-stale-run_constrained-can-block-a-consumer--it-lives-in-constrains-not-depends-so-verify-with-the-real-consumer-solve-a-narrow-dry-run-misses-it): G67 is an *external* feedstock's stale `constrains` blocking *your* consumer; G70 is *your* recipe's *own* `run_constraints` being unfaithful. When auditing, treat these as two separate passes.

**Fix**: reconcile each `run_constraint` to its upstream extra pin. It is a **safe, metadata-only** change — `run_constraints` are NOT installed in the test env, so re-pinning **cannot** change the build/test solve or `pip_check`; a full rebuild isn't required (though it stays green), and **lint/render is sufficient verification** (it validates every entry is a valid conda MatchSpec). Mechanics: source from the base + umbrella pyproject `optional-dependencies` (+ hard deps for lean-stripped integrations); **PEP 508 → conda** (`~=X.Y.Z` → `>=X.Y.Z,<X.(Y+1).0`; strip `; marker` and `[extra]`); **detect phantoms** (a `run_constraint` name absent from every upstream extra/dep → remove it, e.g. the earlier `atlaspy`/`dynamicconf`); **map cf renames** ([G10](#g10-pypi--conda-forge-name-divergence--verify-across-four-spellings-before-declaring-a-dep-missing), e.g. upstream `langfuse` → cf `langfuse-python`); resolve python-conditional duplicates to the broadest range. Preserve any in-recipe authoring markers (e.g. submission-order comments).

**Case study**: langflow-suite (Jun 27, 2026) — the `langflow` output's `run_constraints` had **75 of 78** entries as `>=0.1` placeholders. Reconciled all 78 to langflow 1.10.1's real extra pins (e.g. `litellm >=1.85.1,<2.0.0`, `chromadb >=1.0.0,<2.0.0`, exact pins like `composio ==0.9.2`), 0 unresolved, 0 phantoms (`atlaspy`/`dynamicconf` had already been removed), `langfuse-python` G10 rename preserved. All 3 outputs stayed GREEN and the recipe linted clean — confirming the change was metadata-only.

### G71. A dependency's event-loop reactor needs libev (Unix-only) or asyncore (removed in py3.12) — on win+py3.12+ `import <pkg>.cluster` raises, failing a noarch consumer's CFEP-25 `*` test (win-only)

**Symptom**: a `noarch: python` consumer (e.g. `cassio`) builds clean and passes on linux/osx and on win at `python_min`, but its CFEP-25 import test fails **only on win + the latest Python** (the `python_version: "*"` leg) with `cassandra.DependencyException: Unable to load a default connection class` — traceback originating in the *dependency's* `__init__` (`import cassandra.cluster`), not the consumer.

**Why**: the dependency picks its event-loop "reactor" at **module import**. The libev reactor needs a C-extension that is **Unix-only** (no Windows build); `asyncore` was **removed in Python 3.12**. So on **win + py3.12+** neither is available and `import <pkg>.cluster` raises at load. The `python_min` (3.10) leg passes (asyncore still present); linux/osx pass (libev built). The dependency's OWN feedstock test typically imports only the top-level package (`import cassandra`), never `cassandra.cluster`, so it ships win+py3.12 builds that are broken for any consumer that imports the cluster path (the G24-class "the dep's test didn't cover it" trap).

**Detect on linux** (no Windows needed): the same condition is "no compiled libev + no asyncore", which you can reproduce on linux py3.12+ by importing from source with the C-extension NOT built — `CASS_DRIVER_NO_EXTENSIONS=1`/`PYTHONPATH=<source>` then `python -c "import <pkg>.cluster"` → the identical DependencyException.

**Interim fix (consumer recipe)** — restrict the broken combo out of the test with a **platform-conditional CFEP-25 test**: on win, test `python_min` only; full triad off-win:
```yaml
tests:
  # win: <dep> has no event-loop reactor on py3.12+ (libev is Unix-only; asyncore
  # removed in 3.12), so importing <pkg>.cluster fails there. Test python_min only on win.
  - if: win
    then:
      python: {imports: [<pkg>], pip_check: true, python_version: ["${{ python_min }}.*"]}
    else:
      python: {imports: [<pkg>], pip_check: true, python_version: ["${{ python_min }}.*", "*"]}
```
**A platform-conditional TEST block on a `noarch: python` recipe is lint-clean** — unlike a platform-conditional *run-dep* selector ([G12](#g12-platform-conditional-run-deps-in-noarchpython-recipes-need-noarch_platforms-in-conda-forgeyml)/[G35](#g35-noarch-numpy-env-marker-selector-collapse-a-g12-refinement--per-python-numpy-run-dep-selectors-track-numpys-own-wheel-availability-floor-not-a-package-feature)), neither `validate_recipe` nor the **current** conda-smithy (verify via the [G65](#g65-local-vs-ci-linter-parity--lint-with-the-current-conda-smithy-via-pixi-exec-and-run-the-linterpy-checks-conda-smithy-doesnt) `pixi exec` lint) flags a `tests[].if` selector. Add a one-line body comment so reviewers know why win is restricted. **Caveat**: the noarch artifact is still *installable-but-broken* on win+py3.12+ at runtime — this only stops CI testing the broken combo; the durable fix is upstream.

**Durable fix (the dependency's feedstock)** — patch the reactor-detection chain to **append an asyncio fallback** so the import succeeds when libev+asyncore are both unavailable. cassandra-driver's `cassandra/cluster.py` reduces over a `conn_fns` tuple (`gevent → eventlet → libev → asyncore`); add a `_try_asyncio_import()` (`from cassandra.io.asyncioreactor import AsyncioConnection`, catch `(DependencyException, ImportError)`) and append it. Behavior is unchanged everywhere a reactor already loads; only the broken win+py3.12 case now resolves (to `AsyncioConnection`). Verify by the no-ext py3.12 repro above: unpatched raises, patched → `AsyncioConnection`.

**Case study**: `cassio` 0.1.10 / staged-recipes #33946 (Jun 27, 2026) — win+py3.12+ CFEP-25 `*` leg failed on cassandra-driver's missing reactor. Interim win-test restriction shipped (PR went green); durable `conda-forge/cassandra-driver-feedstock` asyncio-fallback patch authored + runtime-verified locally (`recipes/cassandra-driver/0001-add-asyncio-reactor-fallback.patch`, + `cassandra.cluster` added to its test as a regression guard). The full local `conda build` of cassandra-driver was blocked by an **unrelated** quirk — its `setup.py` runs the legacy `ez_setup.use_setuptools()` which dies on Python-3.12's changed `tarfile.chown` signature when the build env's setuptools triggers a download — so filing the feedstock PR is gated on a green local build per the test-locally-first rule.

### G72. Fold a same-monorepo sibling into a multi-output suite (per-output version + `pin_subpackage`) to dissolve a cross-feedstock submission gate

**Symptom**: a multi-output suite recipe (built from a monorepo tag) has an output that **hard-deps a SEPARATE recipe built from the SAME monorepo source**. Submitting the suite then has to WAIT for that sibling's standalone staged-recipes PR to merge → build → land on the channel ([G66](#g66-a-merged-staged-recipes-pr-is-not-immediately-installable--verify-the-prereq-is-live-on-the-cf-channel-before-submitting-its-dependent)) before the suite can solve — a self-imposed cross-feedstock submission gate for a package that shares the suite's own source.

**Fix**: make the sibling an **additional output of the suite** instead of an external dep:
- Build its subdir (e.g. `${{ PYTHON }} -m pip install src/sdk …`).
- Give it its **own per-output `version`** via a context var (e.g. `sdk_version: "0.2.1"`) — its version is independent of the monorepo tag, and v1 multi-output supports per-output `package.version`.
- List it **before** the consuming output (pin_subpackage resolves in build order).
- The consumer pins it with `${{ pin_subpackage('<sibling>', exact=True) }}` instead of the external spec.

This removes the gate (no "wait for the sibling PR"), and the suite builds the sibling itself. Versions stay locked in lockstep (autotick bumps the shared tag).

**Caveats**: (a) the sibling **inherits the suite's `python_min` floor** — folding can RAISE it (langflow-sdk 3.10→3.11); flag if it reduces the sibling's standalone usability. (b) **Close the sibling's now-redundant standalone PR** (superseded) and re-stamp its local recipe. (c) **Re-verify cf-resolvability with a clean-channel rebuild** ([G68](#g68-after-an-upstreamfeedstock-skew-resolves-purge-the-obsolete-local-workaround-build--stale-higher-build-artifacts-shadow-the-real-cf-package-under-strict-channel-priority)): purge local copies so the build resolves the sibling via `pin_subpackage` and everything else from cf. (d) the sibling is still an **independently-installable package** (multi-output produces separate packages); only the feedstock/maintenance unit is shared.

**Case study**: `langflow-sdk` folded into `recipes/langflow-suite/` as a 4th output (`src/sdk`, `sdk_version: 0.2.1`, lfx pins it via `pin_subpackage(exact=True)`), Jun 27 2026 — removed langflow-suite's external dependency on the standalone #33856 (CLOSED, superseded); a clean-channel rebuild then built all 4 outputs GREEN resolving entirely from conda-forge.

### G73. A noarch app built from a GitHub monorepo TAG ships NONE of the release-time-generated frontend/web assets (wheel-only) — and `import`/`pip_check` can't catch it (a G51 trap for apps with a UI)

**Symptom**: a `noarch: python` application (e.g. `langflow`) builds GREEN from the monorepo **tag**, `import <app>` + `pip check` PASS — but the app's **web UI is missing at runtime** (`<app> run` serves no frontend). The built `.conda` contains **zero** `index.html` / `.js` / `.css` / built-bundle files.

**Why**: the frontend (`<pkg>/frontend/` — the built React/Vite bundle) is generated at **release time** (`npm run build`) and shipped **only in the PyPI wheel**; the GitHub tag carries `src/frontend/` *source*, not the built bundle. Building from the tag (which a multi-output suite needs for its *other* outputs' Python source, [G72](#g72-fold-a-same-monorepo-sibling-into-a-multi-output-suite-per-output-version--pin_subpackage-to-dissolve-a-cross-feedstock-submission-gate)) omits the frontend. This is **[G51](#g51-a-github-monorepo-subdir-may-ship-none-of-the-release-time-generated-assets--source-the-pypi-wheel-instead-or-you-ship-a-broken-empty-package-a-possibly-already-deployed-real-bug)** specialized to a *frontend* — and unlike a missing Python module, **the CFEP-25 import/pip_check test does NOT exercise the UI**, so the green build hides a shipped-broken-app bug. There is **no tag-vs-wheel conflict**: the wheel's frontend is *generated* from the same tag's `src/frontend` at release time, so the recipe re-generates it at **build time** from the one tag source (below) — no second source needed.

**Detect** — for ANY recipe packaging an app **with a web/desktop UI**, inspect the **BUILT `.conda`** for the expected runtime assets; do NOT trust the green import/pip_check:
```bash
python3 -c "import zipfile,tarfile,io,zstandard,sys
z=zipfile.ZipFile(sys.argv[1]); inner=[n for n in z.namelist() if n.startswith('pkg-') and n.endswith('.tar.zst')][0]
names=[];
import io as _io
with zstandard.ZstdDecompressor().stream_reader(_io.BytesIO(z.read(inner))) as r:
    [names.append(m.name) for m in tarfile.open(fileobj=r,mode='r|')]
print('frontend assets:', len([n for n in names if n.endswith(('index.html','.js','.css'))]))" <built>.conda
```
Compare against the PyPI wheel's file list (`unzip -l <pkg>.whl | grep frontend/`). Zero in the conda + many in the wheel = this bug.

**Fix (node-build from source — the conda-forge idiom)**: build the frontend at **build time** from the tag's `src/frontend`. Add the JS toolchain to `requirements.build` (`nodejs` pinned to the project's `package.json` `engines.node`, plus the package manager the lockfile implies — `npm` ships with `nodejs`; `pnpm`/`yarn` are separate conda packages), run the upstream build (`npm ci && npm run build`, i.e. the Vite/webpack build → `src/frontend/build`), then copy the built bundle into the package tree (`<pkg>/frontend/`) **before** `pip install`, so the build backend ships it (e.g. hatchling `packages=["<pkg>"]` includes the whole dir).

**⚠️ The build script MUST be cross-platform.** staged-recipes builds a `noarch` recipe on **all three** platforms (linux/osx/win) for validation and runs `package_contents` on **each** — it is NOT linux-only (only *after* it becomes a feedstock does conda-smithy build noarch on linux alone). A unix/bash-only build (`set -ex`, `pushd`, `rm -rf`, `cp -r`, bare `npm`) runs through **cmd.exe** on the Windows leg and silently fails: bash-isms don't exist there, and a bare `.cmd` shim (`npm`/`pnpm`/`yarn`) **without `call`** *terminates* the script (the build.bat `call`-the-`.cmd`-shim rule) → the frontend never builds → the `package_contents` guard correctly fails **win-only**. Provide a Windows path (G56) and do the copy + `pip install` in **cross-platform Python** (`shutil`, not `rm -rf`/`cp -r`):
```yaml
script:
  - if: win
    then: |
      call npm --prefix src/frontend ci
      if errorlevel 1 exit 1
      call npm --prefix src/frontend run build
      if errorlevel 1 exit 1
    else: |
      set -ex
      npm --prefix src/frontend ci
      npm --prefix src/frontend run build
  - ${{ PYTHON }} -c "import shutil; d='<pkg-dir>/frontend'; shutil.rmtree(d, ignore_errors=True); shutil.copytree('src/frontend/build', d)"
  - ${{ PYTHON }} -m pip install <pkg-src-dir> -vv --no-deps --no-build-isolation
```
`npm --prefix` avoids `cd`/`pushd`. (Surfaced 2026-06-27: langflow-suite PR #33972's win leg failed exactly this way — the unix-only build shipped first passed linux/osx, but the `package_contents` guard caught the empty Windows frontend. Live CI caught what the local linux build could not — verify, don't assume.)

> **Build-time network IS available on conda-forge** — only the **test** phase is offline. `npm ci`/`pnpm i` fetching `node_modules` at build is fine and routine; Rust/Go/npm feedstocks do it constantly. (This corrects earlier guidance in this gotcha + [G45](#g45-a-browser-spa-vuereactsvelte--vite-is-usually-not-conda-forge-submittable--run-the-viability-gate-first-then-build-local-only-as-a-static-site--launcher)/G6 that implied a build-time fetch is disallowed — it is not. The *test* env is the offline one.)

**Precedents** (verified 2026-06-27): `gradio` (GitHub-archive source + `nodejs`+`pnpm` build deps, runs `scripts/build_frontend.sh` = `pnpm i --frozen-lockfile && pnpm build` at build — the exact no-sdist analogue), `chainlit` (`pnpm` build via the hatchling build hook), `mlflow` (`yarn install; yarn build` of `mlflow/server/js`, then strips `node_modules`/`.map`), `agentsview`/`nebi` (`pnpm install && pnpm run build`, then embed). **Verify the result** with a `package_contents` test (env-free — it inspects the built `.conda`, so it works even when the test-env solve is blocked): `site_packages: [<pkg>/frontend/index.html, <pkg>/frontend/assets/*.js]`.

**Alternatives, in order of preference**: (1) **sdist that already includes the frontend** — if upstream's sdist ships the built bundle, just `pip install` it (dominant pattern: streamlit/bokeh/jupyterlab); (2) **node-build from the tag** (above — when no usable sdist exists); (3) **`tensorboard` model** — source the wheel **wholesale** as the package when the wheel is exactly what you want to ship (`noarch: python` downgrades the wheel-in-source lint **R-029**→non-blocking hint **R-030**). **Avoid the wheel-graft** (extract `<pkg>/frontend/` from a *secondary* wheel source while building the rest from the tag): it has **no conda-forge precedent** and draws reviewer pushback. Note on the wheel-in-source lint: **R-028** (compiled wheel) and **R-029** (pure wheel, non-noarch) are blocking lints; **R-030** (pure wheel + `noarch: python`) is a non-blocking hint; **none is skippable** via `conda-forge.yml linter.skip` (no skip key exists for this check).

**Case study**: `langflow-suite` (langflow-base + langflow built from the `langflow-ai/langflow` v1.10.1 tag), surfaced Jun 27 2026 during an adversarial spec review: the built `langflow-base`/`langflow` `.conda` shipped **0** frontend files while the `langflow-base` PyPI wheel ships **~1,874** (`langflow/frontend/index.html` + the Vite/React assets bundle). `import langflow`/`pip_check` were green throughout — the UI-less break was invisible to them. **Fixed** by building the frontend at build time in the `langflow-base` output (`nodejs >=20.19` build dep; `npm ci && npm run build` of `src/frontend` → copy `build/` into `src/backend/base/langflow/frontend/` before `pip install`), guarded by a `package_contents` test for `langflow/frontend/index.html` + `assets/*.js`. The initial fix attempt was a wheel-graft; deep research into cf feedstocks (gradio/chainlit/mlflow) showed node-build-from-tag is the precedented idiom and that build-time network is available — the wheel-graft was dropped (no precedent). **Verified 2026-06-27:** the rebuilt `langflow-base` `.conda` grew **1.9 MB → 14 MB** and contains **1,873** frontend files (`index.html` + 1,855 JS + 2 CSS, vs the wheel's ~1,874); the `package_contents` test passes at packaging time even under `--test skip`.

---

### G74. "Is X on conda-forge?" — the offline atlas can be STALE for recently-created feedstocks; cross-check live `channeldata.json` before any membership-driven destructive edit

**Symptom**: a `cf_atlas.db` `packages` lookup says a dependency is NOT on conda-forge, but it actually is — its feedstock was created after the atlas's last refresh. Acting on the stale "absent" (dropping a `run_constraint`, re-packaging a prerequisite that already exists, marking a dep blocked) is then wrong.

**Why**: the atlas is an offline snapshot (Phase B/C build time). Feedstocks created in the days since — including your **own** freshly-merged staged-recipes PRs — aren't in it. Live case (2026-06-27): filtering langflow-suite's run_constraints to "on-cf only," the atlas showed `apify-client` absent, but its feedstock was created 2026-06-26 and it's live on the channel → it would have been wrongly removed.

**Fix**: when a membership check **drives a destructive or irreversible edit**, confirm against LIVE conda-forge, not the atlas alone. The authoritative, staleness-proof, one-fetch source is the channel index:
```bash
curl -sL --compressed https://conda.anaconda.org/conda-forge/channeldata.json -o cf.json
python3 -c "import json; p=set(json.load(open('cf.json'))['packages']); print('apify-client' in p)"
```
`channeldata.json` (~22 MB, ~33k packages) lists **every** package on the channel regardless of which feedstock built it — so it also catches multi-output-provided packages a feedstock-name check would miss. Apply [G10](#g10-pypi--conda-forge-name-divergence--verify-across-four-spellings-before-declaring-a-dep-missing)'s four-spelling variants when checking. The atlas stays the fast first pass (definitive for "present"); the live index resolves the "absent" set. (Read-side atlas metrics are fine offline — this rule is specifically for membership facts that gate edits, and is the membership analogue of [G66](#g66-a-merged-feedstock-pr--an-installable-package--re-check-the-live-channel-before-depending-on-it) merged≠installable.)

### G75. A lean staged-recipes SUBMISSION copy may go BEYOND the default cfe-strip — remove ALL comments + filter optional run_constraints to on-cf-only; branch off conda-forge MAIN, push to your fork, no PR

The default strip-before-push ([G60](#g60-the-strip-before-push-must-remove-only-extracfe--keys---cfe--blocks--never-the-schema-header-or-context-block)/[G62](#g62-never-ship-cfe-metadata--the-strip-is-mandatory-and-must-be-verified-on-the-pushed-artifact-verify-dont-assume)) is **surgical**: it removes only `extra.cfe-*` + `# CFE …` blocks and KEEPS the schema header + `context:`. But a user may direct a **fuller clean** for a lean first submission of a big multi-output suite. Two extra steps, both deliberate, both verified on the pushed artifact:

1. **Remove ALL comments**, not just the cfe blocks — the schema-header comment (`# yaml-language-server …`; optional per repo convention, ~29/30 cf PRs omit it), section dividers, and inline trailing comments. `schema_version: 1` (a key, not a comment) stays. Process **line-by-line, section-aware**, never via a YAML round-trip (it mangles `${{ }}` jinja + literal block scalars).
2. **Filter optional `run_constraints` to packages already on conda-forge** — a suite that lists constraints pointing at *unsubmitted* packages reads as depending on an un-packaged ecosystem and invites reviewer questions. Drop the not-yet-on-cf ones from the **submission copy**; keep the full set in the **local** recipe (source of truth). Re-verify membership LIVE per [G74](#g74-is-x-on-conda-forge--the-offline-atlas-can-be-stale-for-recently-created-feedstocks-cross-check-live-channeldatajson-before-any-membership-driven-destructive-edit) — the atlas is stale for recently-merged deps. (run_constraints are advisory → metadata-only; a constraint on an absent package is harmless but noise.) Collapse a now-empty `run_constraints:` key entirely (don't ship a bare `run_constraints:`).

**Branch-only flow (no PR)**: base the branch on **conda-forge/staged-recipes `main`** (NOT the local-recipes fork, NOT a bot fork) so the eventual PR diffs to just the one recipe; push to the personal fork (`<user>/staged-recipes`); do **not** open the PR when told to hold. Verify cfe/comment-free on the pushed artifact (G62). Live: `langflow-suite-clean` on `rxm7706/staged-recipes` — 519→313 lines, 40 of 85 run_constraints dropped (live-checked), 0 cfe/comment leakage. This is a deliberate variant of — not a replacement for — the default G60 strip.

### G76. A Unix-only dependency in a `noarch: python` recipe CANNOT be a hard dep — `noarch` bakes `depends` at build time, so the package becomes unsolvable on Windows; make it OPTIONAL (strip from the wheel + `run_constraints`)

**Symptom**: a `noarch: python` package lists a run dep that conda-forge ships **Unix-only** (no `win-64`, no `noarch` build — e.g. `gunicorn`, `uvloop`). On the Windows test/install leg the conda **solve fails** (`nothing provides <dep>`), and `pip check` (which staged-recipes runs **regardless of the recipe's `pip_check:` setting** — see below) flags the wheel's `Requires-Dist`.

**Why two half-fixes DON'T work**:
- **`if: unix` on the run dep** — for a `noarch` package, selectors are evaluated at **build time** (the build runs once, on linux=unix), so `gunicorn` bakes into `depends` **unconditionally**. The built `noarch` artifact requires it on every platform → Windows solve still fails. (Confirmed: `index.json` `depends` carried `gunicorn` with `subdir: noarch`.) Platform-conditional **hard** depends are impossible for noarch.
- **Wheel marker only** (`; sys_platform != 'win32'` in `[project.dependencies]`) — fixes `pip check` on win (the dep isn't required there) but does nothing for the conda **solve** (the conda depend, if present, still blocks win); and if you make the conda dep Unix-only it bakes anyway (above). It also fails `pip check` on **unix** if the dep is required-by-wheel but not installed.

**Fix — make it optional**: (1) **strip the dep from the wheel's `[project.dependencies]`** via a source patch (so `pip check` never requires it, on any platform); (2) **move it to conda `run_constraints`** (`<dep> >=x,<y`) — advisory, constrains-if-present, never installed, never blocks a solve. The package stays `noarch`, installs on **all** platforms, and `pip check` passes everywhere; the dep is still version-pinned **if** a unix user adds it. This is the same lean pattern used for optional integrations (G25/G70). **Verify on the built `.conda`**: the dep must be **absent** from the wheel main `Requires-Dist` AND from conda `depends`, and **present** in conda `constrains`.

**`pip_check: false` is NOT a workaround here**: staged-recipes CI runs `pip check` for every output **regardless** of the recipe's `pip_check:` setting (observed on PR #33972 — `>pip check` ran + "pip check passed!" for outputs explicitly set `pip_check: false`). So a wheel-vs-conda metadata mismatch must be **genuinely resolved**, not silenced. (The two alternatives to "optional" — keep the dep Unix-only and `noarch_platforms`-exclude win, or make the package non-noarch per-platform — are heavier; optional/`run_constraints` is preferred when the dep isn't import-required.)

**Case study**: `langflow-suite` `langflow-base` — `gunicorn` (cf Unix-only: `linux-*`/`osx-*` only) was a hard run dep of the `noarch` output → PR #33972 Windows leg unsolvable. Resolved Jun 27 2026 by stripping `gunicorn` from `src/backend/base/pyproject.toml` (patch 0001) + adding `gunicorn >=25.3.0,<27.0.0` to `run_constraints`. Verified: built `.conda` has gunicorn in `constrains`, absent from `depends` + wheel main deps; 5/5 outputs pass `pip check` on linux.

### G77. A TRANSITIVE dep whose conda feedstock dropped a win-only wheel marker breaks `pip check` on Windows — you can't fix it in your noarch recipe; exclude win via `conda-forge.yml noarch_platforms`, or fix the upstream feedstock

**Symptom**: `pip check` fails **only on the Windows** leg, on a **transitive** (not direct) requirement — e.g.:
```
magika 0.6.3 has requirement onnxruntime<=1.20.1; sys_platform == "win32", but you have onnxruntime 1.26.0.
```
linux + osx pass; the failing constraint comes from a package you don't depend on directly (here `<your-pkg> → markitdown → magika`).

**Why**: the transitive dep's **wheel** metadata has an environment-marked cap (`<dep> <=X; sys_platform == "win32"`), but its **conda feedstock didn't encode that cap** — conda `depends` can't carry PEP 508 markers, they'd need a `# [win]` selector. So the conda solver installs the latest `<dep>` on win, which violates the wheel marker, and `pip check` (which staged-recipes runs **regardless** of `pip_check:`, G76) flags it. It's an **upstream-feedstock metadata gap**, not your recipe's bug — and being transitive, you often can't even name it from your own dep list (read the pip check error to find the chain).

**Why you can't cleanly fix it in your recipe**: a win-only cap on the offending dep is impossible in a `noarch:python` recipe (noarch bakes `depends`, no platform-conditional specs — G76); an *unconditional* cap penalizes linux/osx with an old version; and the dep is transitive (capping it in your own `run_constraints` is brittle + over-broad).

**Remedies** (in order):
1. **Fix the upstream feedstock** (root) — PR the offending feedstock to add the cap as a conda selector (`<dep> <=X  # [win]`, the conda equivalent of its wheel marker); then rebuild-to-channel (G66). Correct but external + slow — and in a deeply unix-oriented dep tree expect **more** such moles after the first clears.
2. **Exclude win from the CI matrix** (pragmatic, when the package is unix-oriented) — add `recipes/<name>/conda-forge.yml` with `noarch_platforms: [linux_64, osx_64, osx_arm64]` (no `win_64`). The noarch artifact still **installs** on Windows (it's universal — one `.conda` built on `linux_64`); you only drop win from CI validation. Add `osx_arm64` to validate Apple Silicon (still one universal noarch artifact, not a per-arch build). Pair with **`workflow_settings.store_build_artifacts`** (the current key — `azure.store_build_artifacts` is deprecated; G18: the *unscoped* form crashes the win leg, mooted here since win is excluded) to publish the built `.conda` as a downloadable CI artifact. Skip emulated `linux_aarch64`/`linux_ppc64le` test legs for a large closure unless needed — they often red on dep-availability gaps.

**Case study**: `langflow-suite` PR #33972 — after fixing the bash-build (G73) and gunicorn (G76) win failures, the win leg STILL failed on `lfx → markitdown → magika 0.6.3`'s `onnxruntime<=1.20.1; sys_platform=="win32"` wheel marker (conda magika installed `onnxruntime 1.26.0`). The **third** distinct win-only failure in one closure. Excluded win via `conda-forge.yml noarch_platforms: [linux_64, osx_64, osx_arm64]` + `store_build_artifacts`; linux + osx (incl. osx-arm64) green, the noarch artifact still installs on win. Re-enabling win is a deferred task (magika-feedstock PR + re-check for more moles).

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

- **v8.54.0** (Jun 27, 2026): **G77 — a TRANSITIVE dep's dropped win-only wheel marker breaks pip check on win; exclude win via conda-forge.yml or fix the upstream feedstock (MINOR — 1 new gotcha).** Third win-only failure on langflow-suite PR #33972 (after G73 bash-build + G76 gunicorn): `lfx → markitdown → magika 0.6.3` whose **wheel** caps `onnxruntime<=1.20.1; sys_platform=="win32"`, but the conda magika-feedstock didn't encode the cap (conda deps can't carry markers) → solver installed `onnxruntime 1.26.0` → `pip check` fails on win. **G77**: a transitive conda-vs-wheel win-marker gap is an upstream-feedstock bug you can't fix in your (noarch) recipe — remedies are (1) PR the offending feedstock to add the `# [win]` cap (root, external), or (2) for a unix-oriented package, **exclude win via `recipes/<name>/conda-forge.yml noarch_platforms: [linux_64, osx_64, osx_arm64]`** (the noarch artifact still installs on win) + `workflow_settings.store_build_artifacts` (current key; `azure.` is deprecated) to publish downloadable `.conda`; add `osx_arm64` to validate Apple Silicon (one universal noarch artifact, not per-arch). Applied to langflow-suite: win excluded, linux+osx(arm64) green. Also drove the spec's new **§ Windows build** (failure analysis + re-enablement task). **Files**: `SKILL.md` (G77 + this entry); `config/skill-config.yaml` (8.53.0 → 8.54.0); `CHANGELOG.md`; `recipes/langflow-suite/conda-forge.yml`; `docs/specs/langflow-conda-forge.md`.
- **v8.53.0** (Jun 27, 2026): **G76 — a Unix-only dep in a noarch recipe must be OPTIONAL, not a hard dep (MINOR — 1 new gotcha).** Live-CI follow-on from PR #33972: `gunicorn` is **Unix-only on conda-forge** (`linux-*`/`osx-*` subdirs only — no `win-64`, no `noarch`), but it was a hard run dep of the `noarch` `langflow-base` → the Windows test env couldn't **solve** (`nothing provides gunicorn`). **G76**: a `noarch: python` package can't carry a platform-conditional **hard** dep — noarch bakes `depends` at build time, so `if: unix` becomes unconditional and the artifact is unsolvable on win; a wheel-only marker fixes `pip check` but not the conda solve. **Fix = make it optional**: strip the dep from the wheel's `[project.dependencies]` (source patch) + move to conda `run_constraints` (advisory) → installs on all platforms, `pip check` clean everywhere, dep still pinned-if-present on unix (same lean pattern as G25/G70). Also recorded: **staged-recipes runs `pip check` regardless of the recipe's `pip_check:` setting** (observed: pip check ran for outputs set `pip_check: false`) — a metadata mismatch must be genuinely resolved, not silenced. Applied to `langflow-suite` (gunicorn → run_constraints; verified on the built `.conda`: gunicorn in `constrains`, absent from `depends` + wheel main-deps; 5/5 pip checks pass). **Files**: `SKILL.md` (G76 + this entry); `config/skill-config.yaml` (8.52.1 → 8.53.0); `CHANGELOG.md`; `recipes/langflow-suite/recipe.yaml`; `patches/0001-strip-integration-deps.patch`.
- **v8.52.1** (Jun 27, 2026): **G73 cross-platform correction — a noarch frontend node-build MUST handle the Windows leg (PATCH).** Live-CI finding: langflow-suite PR #33972's **win leg failed** while linux/osx passed — the node-build script I shipped in v8.51.1 was **unix/bash-only** (`set -ex`/`pushd`/`rm -rf`/`cp -r`/bare `npm`), but **staged-recipes builds a `noarch` recipe on all three platforms** (linux/osx/win) for validation and runs `package_contents` on each (only *after* feedstock creation does conda-smithy build noarch on linux alone). On the Windows leg the script runs through cmd.exe: bash-isms fail and a bare `npm`/`.cmd` shim without `call` *terminates* the script → frontend never builds → the G73 `package_contents` guard correctly catches it win-only. Corrected G73's Fix with a cross-platform pattern: `if: win / then` with `call npm --prefix … && if errorlevel 1 exit 1`, copy + `pip install` in cross-platform Python (`shutil`, not `rm -rf`/`cp -r`). Cross-refs G56 + the build.bat call-the-.cmd-shim rule. The unix-only build passed local linux + the v8.51.1 verification — **live CI caught what the local build could not (verify, don't assume)**. Fix applied to `recipes/langflow-suite/recipe.yaml` (verified: linux rebuild still ships 1,873 frontend files) + the `langflow-suite-clean` submission branch. **Files**: `SKILL.md` (G73 cross-platform note + this entry); `config/skill-config.yaml` (8.52.0 → 8.52.1); `CHANGELOG.md`; `recipes/langflow-suite/recipe.yaml`.
- **v8.52.0** (Jun 27, 2026): **langflow-suite submission-prep retro (MINOR — 2 new gotchas G74/G75).** Closeout retro of the `langflow-suite-clean` lean-submission-branch effort (frontend node-build verified + cleaned recipe pushed to `rxm7706/staged-recipes`, no PR per directive). **G74 — atlas membership can be STALE for recently-created feedstocks:** a `cf_atlas.db` "absent" can be wrong (feedstock created since the last atlas refresh — incl. your own freshly-merged PRs); when a membership check **drives a destructive edit** (dropping a run_constraint, re-packaging an existing prereq), cross-check LIVE `conda-forge channeldata.json` (one fetch, ~33k packages, feedstock-agnostic — catches multi-output-provided packages too). Live: `apify-client` was atlas-absent but on-channel (feedstock 2026-06-26) → would have been wrongly dropped. The membership analogue of G66. **G75 — a lean staged-recipes SUBMISSION copy may go beyond the default cfe-strip:** beyond G60/G62 (surgical cfe-only strip, keep schema header), a user may direct (1) remove ALL comments incl. the schema-header comment + dividers + inline (process line-by-line section-aware, never a YAML round-trip), (2) filter optional run_constraints to **on-cf-only** (don't ship constraints pointing at unsubmitted packages — re-verify LIVE per G74; collapse a now-empty `run_constraints:` key); keep the full set in the LOCAL recipe. Branch-only flow: base on **conda-forge/staged-recipes main** (minimal PR diff), push to the personal fork, no PR when told to hold. Live: `langflow-suite-clean` 519→313 lines, 40/85 run_constraints dropped, 0 cfe/comment leakage verified on the pushed artifact. Also confirmed the G73 fix end-to-end (langflow-base `.conda` 1.9MB→14MB, 1,873 frontend files). **Files**: `SKILL.md` (G73 verified-note + G74/G75 + this entry); `config/skill-config.yaml` (8.51.1 → 8.52.0); `CHANGELOG.md`.
- **v8.51.1** (Jun 27, 2026): **G73 correction — node-build is the cf idiom for a wheel-only frontend; build-time network IS available (PATCH).** Deep research into existing conda-forge feedstocks corrected two wrong claims in the v8.51.0 G73: (1) the fix is to **build the frontend from source at build time** (`nodejs` build dep + `npm ci && npm run build` of `src/frontend`, copy into the package tree before `pip install`) — NOT the wheel-graft, which has **no cf precedent**; (2) **conda-forge BUILD jobs have network access** — only the *test* phase is offline, so `npm ci`/`pnpm i` fetching `node_modules` at build is fine and routine (the earlier "build-time fetch is disallowed" framing in G73/G45 was wrong). Precedents documented: `gradio` (exact no-sdist analogue — `scripts/build_frontend.sh`), `chainlit` (pnpm via hatchling hook), `mlflow` (`yarn build` of `server/js`), `agentsview`/`nebi`. Also captured the wheel-in-source lint mechanics (R-028 compiled / R-029 pure-non-noarch = blocking lints; R-030 pure+noarch = non-blocking hint; **none skippable**). Applied: `langflow-suite` `langflow-base` output now node-builds `langflow/frontend/` at build time, guarded by a `package_contents` test (`index.html` + `assets/*.js`). Heads-up recorded: competing staged-recipes PRs **#33853 langflow-base (draft, no frontend)** + **#33875 langflow-sdk (open)** by another submitter. **Files**: `SKILL.md` (G73 Why/Fix/case-study + this entry); `config/skill-config.yaml` (8.51.0 → 8.51.1); `CHANGELOG.md`; `recipes/langflow-suite/recipe.yaml`; `.claude/scripts/conda-forge-expert/native-build.sh` (extra-arg passthrough); `docs/specs/langflow-conda-forge.md`.
- **v8.51.0** (Jun 27, 2026): **adversarial-spec-review + langflow-suite-fold retro (MINOR — 3 new gotchas G71/G72/G73).** From the langflow-sdk fold + cassio win-fix + a 3-lens adversarial review of `docs/specs/langflow-conda-forge.md`. **G71**: a dependency whose event-loop reactor needs libev (Unix-only) or asyncore (removed py3.12) fails `import <pkg>.cluster` on **win+py3.12+**, breaking a noarch consumer's CFEP-25 `*` leg win-only; interim = platform-conditional CFEP-25 test (lint-clean — a `tests[].if` selector on noarch does NOT trip the noarch-selector lint, unlike a run-dep selector G12/G35); durable = patch the dep's reactor chain to append an asyncio fallback (cassio #33946 + cassandra-driver-feedstock patch). **G72**: fold a same-monorepo sibling into a multi-output suite (own per-output `version` + consumer `pin_subpackage(exact=True)`) to dissolve a cross-feedstock submission gate — caveats: inherits the suite python_min floor, close the sibling's standalone PR, re-verify clean-channel (G68) (langflow-sdk → langflow-suite 4th output, #33856 closed). **G73**: a noarch app built from a GitHub monorepo TAG ships none of the release-time-generated frontend assets (wheel-only) — a G51 trap that `import`/`pip_check` CANNOT catch because the UI isn't imported; detect by inspecting the BUILT `.conda` for `index.html`/`.js`/`.css` (langflow-suite shipped 0 frontend files vs the wheel's ~1,874 — the langflow-suite submission blocker; fix = node-build the frontend from the tag's `src/frontend` at build time — corrected in v8.51.1, see below). The review also drove a major consolidation of the langflow spec (single canonical CURRENT STATE block; ~25 accreted contradictions reconciled). **Files**: `SKILL.md` (G71–G73 + this entry); `config/skill-config.yaml` (8.50.0 → 8.51.0); `CHANGELOG.md`; `docs/specs/langflow-conda-forge.md`.
- **v8.50.0** (Jun 27, 2026): **run_constraints-reconciliation retro (MINOR — 1 new gotcha G70).** Closeout of the langchain + langflow-suite run_constraints audit/reconciliation. **G70**: reconcile a recipe's OWN `run_constraints` to upstream's real extra pins (not `>=0.1` placeholders) — it's soft/metadata-only (not installed in the test env), so re-pinning can't change the build/test/pip_check and lint/render is sufficient verification; mechanics = source from upstream base+umbrella `optional-dependencies`, PEP 508→conda (`~=` expand, strip markers/extras), detect phantoms (remove names absent from all upstream extras), map cf renames (G10). Distinct from G67 (external feedstock constrains blocking *you*) — two separate audit passes. Live: langflow-suite's `langflow` output had 75/78 `>=0.1` placeholders → reconciled all 78 to langflow 1.10.1 extra pins, 0 phantoms, green + lint-clean. (The audit also confirmed the v8.49.2 lesson — `groq <1` is NOT stale despite cf groq 1.5.0, because upstream langchain-groq pins `<1`.) **Files**: `SKILL.md` (G70 + this entry); `config/skill-config.yaml` (8.49.2 → 8.50.0); `CHANGELOG.md`; `docs/specs/langflow-conda-forge.md`.
- **v8.49.2** (Jun 27, 2026): **G67 staleness-detection correction (PATCH).** The audit heuristic "cf has a version above the cap → stale" is a **false-positive generator** for `run_constrained`. Optional-integration constraints intentionally cap to the *provider's* supported range, which lags cf-latest. Counter-example: langchain's `groq >=0.4.1,<1` is NOT stale despite cf groq 1.5.0 — upstream `langchain-groq 1.3.11` pins `groq>=0.30.0,<1.0.0` (no groq 1.x support) and the feedstock mirrors it, so `<1` is protective. Staleness = **diverges from the CITED SOURCE's current pin** (aiosqlite was stale because langchain's own `extended_testing_deps.txt` moved `<0.20`→`<0.23`; groq is not). Corrected G67's detection guidance. **Files**: `SKILL.md` (G67 + this entry); `config/skill-config.yaml` (8.49.1 → 8.49.2); `CHANGELOG.md`.
- **v8.49.1** (Jun 27, 2026): **G67 fix-value correction (PATCH).** G67's prescribed fix was a guessed "loosen aiosqlite to `<1.0`" — wrong discipline. When a feedstock's `run_constrained` is annotated as copied from a pinned upstream file (langchain cites `extended_testing_deps.txt` at a tag), the fix is to **re-sync to the CURRENT version's file** (bump the tag, copy verbatim), not arbitrarily widen. langchain `1.3.11`'s file pins `aiosqlite >=0.19.0,<0.23` (the `1.2.0` file said `<0.20`) — so the durable value is `<0.23`, not `<1.0`. Corrected G67 Fix + case study, and the spec. (User fixed `recipes/langchain/` to `<0.23` in commit d1c6b20c7a.) **Files**: `SKILL.md` (G67 + this entry); `config/skill-config.yaml` (8.49.0 → 8.49.1); `CHANGELOG.md`; `docs/specs/langflow-conda-forge.md`.
- **v8.49.0** (Jun 27, 2026): **langflow-suite 1.10.1 bump retro (MINOR — 3 new gotchas).** From bumping the 3-output langflow-suite to 1.10.1 + `langchain~=1.3.0` (all outputs built+tested GREEN locally). **G67**: an external feedstock's stale `run_constrained` (in `constrains`, NOT `depends`) can block a consumer; a narrow "does X co-install with Y" dry-run misses it because the constraint only fires when the *real consumer's* full hard-dep set drags the constrained package in — verify against the actual consumer solve, and when conflicting, inspect the blocker's `constrains` (cf langchain's stale `aiosqlite >=0.19.0,<0.20` vs langflow-base's `aiosqlite>=0.20`; the `constrains`-axis sibling of the text-splitters `depends` skew). **G68**: after a skew resolves, PURGE the obsolete local workaround build — under strict channel priority a stale higher-priority `build_artifacts/` artifact (e.g. `langchain 1.2.18`) shadows the real cf package and causes false failures; delete + `conda_index` re-index before re-testing. **G69**: a suite version bump can CASCADE to a sibling recipe bump via a tightened cross-dep (lfx 1.10.1 → `langflow-sdk>=0.2.1`); bump+rebuild the sibling locally, update the pin, and flag the submitted PR (#33856) to bump too. **Files**: `SKILL.md` (G67–G69 + this entry); `config/skill-config.yaml` (8.48.0 → 8.49.0); `CHANGELOG.md`. Also: `recipes/langflow-suite` + `recipes/langflow-sdk` bumped (committed a0045a9f46); `docs/specs/langflow-conda-forge.md` updated (new aiosqlite skew; Wave A not fully clear).
- **v8.48.0** (Jun 27, 2026): **§ B′-consumer batch retro (MINOR — 1 new gotcha + G40 refinement).** Closeout of the 6-PR langflow § B′-consumer batch (qianfan #33935, opik #33937, trustcall #33938, langchain-graph-retriever #33939, langchain-google-vertexai #33940, langchain-sambanova #33941 — all green first try + pinged). **G66 (new)**: a MERGED staged-recipes PR is **not** immediately installable — the feedstock must build + upload (minutes-to-hours), so before submitting a consumer whose blocker just merged, verify the prereq is **live on the cf channel at a satisfying version** (fresh repodata or a build that solves against conda-forge, not the local mirror which masks the gap). Verification depth scales with dep shape: pure-python → confirm-live + build; compiled → ALSO the G40 check. Includes the cached-snapshot trap (a reused repodata file reported pydantic 2.9.2 as "latest" when cf had 2.13.4 — floor checks need fresh data). **G40 refinement**: run the per-platform compiled-dep floor check **proactively before submit** (all prior case studies were reactive); added the concrete `depends`-parse method (collect each candidate build's `python >=3.X`, filter to the pinned range, confirm the floor on every subdir) — langchain-google-vertexai's pyarrow/bottleneck/numexpr all covered py3.10 → no bump, green first try. **Files**: `SKILL.md` (G66 + G40 refinement + this entry); `config/skill-config.yaml` (8.47.1 → 8.48.0); `CHANGELOG.md`.
- **v8.47.1** (Jun 26, 2026): **G63 correction (PATCH) — tick EVERY checklist box.** v8.47.0's G63 carved out the knowledge-base line ("tick every `- [ ]` except…") — wrong. The *"check the knowledge base before pinging"* item is a submitter-affirmed box like any other; an unticked box reads as an incomplete checklist. G63 now `sed -i 's/- \[ \]/- [x]/g'` the whole template, no exceptions. Live fix: opik #33937 opened with that box unchecked under the old carve-out → corrected on the PR (0 unchecked). **Files**: `SKILL.md` (G63 + this entry); `config/skill-config.yaml` (8.47.0 → 8.47.1); `CHANGELOG.md`.
- **v8.47.0** (Jun 26, 2026): **linter-parity gotcha (G65) — MINOR.** From the "does the local linter match the conda-forge CI?" audit. **G65**: (1) the pixi env pins `conda-smithy >=3.44.6,<4` (=3.62.0) and **can't** take the CalVer 2026.x line — it hard-depends on the `conda` pkg, absent from this rattler/conda-build env (`pixi update conda-smithy` fails) — so for **CI-parity lint** run the current conda-smithy **ephemerally**: `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/<name>` (no env change; matches the webservice exactly); never dismiss its lints (cf the G12 escape-hatch misjudgment on opik). (2) the staged-recipes GHA `linter.py` runs conda-smithy recipe-lint **plus** checks `validate_recipe` doesn't — files-outside-`recipes/`, feedstock/conda-name/bioconda-exists — so run `lookup_feedstock` (G58) + placement/name checks before submitting. (3) local `recipe-build` is **host-only** → per-platform gaps (opik's osx `fastuuid` py3.10, G40) need the per-subdir repodata check. Added a CI-parity-lint item to the Pre-PR checklist; `pixi.toml` comment records the `pixi exec` command (env pin kept `<4` deliberately). **Files**: `SKILL.md` (G65 + checklist + this entry); `pixi.toml` (comment); `config/skill-config.yaml` (8.46.2 → 8.47.0); `CHANGELOG.md`.
- **v8.46.2** (Jun 26, 2026): **G12 refinement (PATCH) — escape hatch caveat + why-local-misses.** From opik #33936: the `noarch_platforms` escape hatch does **not** reliably silence the `conda-forge-linter` *webservice* (worked for xorq's `if: linux`, NOT opik's `if: not (linux and aarch64)`), so **don't dismiss `validate_recipe`'s "noarch can't have selectors" as a guaranteed false-positive**. **Prefer eliminating the selector via G35** when conda-forge ships the dep on all subdirs (verify per-subdir repodata; mind `_`-vs-`-`, G10) → unconditional deps + no `conda-forge.yml` → green on both linters, installable everywhere. Also documents **why local gates "miss" CI failures**: (1) `validate_recipe` *does* catch lints — opik's miss was a judgment error (overriding a real lint); (2) local builds are **host-platform-only**, so per-platform issues (osx-64 `fastuuid` py3.10 gap, G40/G61) can't surface — run the G40 per-subdir check for compiled transitive deps before submitting. **Files**: `SKILL.md` (G12 refinement + this entry); `config/skill-config.yaml` (8.46.1 → 8.46.2); `CHANGELOG.md`.
- **v8.46.1** (Jun 26, 2026): **G64 refinement (PATCH).** Added a third precondition to the ready-for-review ping: the PR must **not be a draft** (a draft isn't ready for review — pinging is premature). G64's gate is now ping-only-if **all checks green AND `isDraft == false` AND `review-requested` absent** (`gh pr view <pr> --repo conda-forge/staged-recipes --json isDraft,labels`). Updated the Pre-PR Submission checklist item. **Files**: `SKILL.md` (G64 + checklist + this entry); `config/skill-config.yaml` (8.46.0 → 8.46.1); `CHANGELOG.md`.
- **v8.46.0** (Jun 26, 2026): **review-request retro (1 new gotcha + G62 reinforcement).** **MINOR bump** — from the qianfan #33935 review-request step. **G64** (after CI is all-green, request review with **one** language-matched ping — `@conda-forge/help-python` for pure-Python noarch, `help-c-cpp`/`help-rust`/… per language — and **check the PR's labels first**: the ping makes a bot add `review-requested` + the language label, so if those labels exist a prior ping already landed → skip; labels are the authoritative dedup signal, not comment text; qianfan #33935 was pinged twice, duplicate deleted). **G62 reinforcement** — the strip is **local-retains / strip-on-push**: the `cfe-*` block lives in the LOCAL recipe permanently and is removed only on a pushed COPY; **never delete `cfe-*` from the local recipe** (lose the cached CFE/admin state) — on submission, update the local `cfe-on-conda-forge-status` + add `cfe-submission-pr:`, don't remove the block (qianfan's local cfe-removal was an error, restored). Added a post-green review-request item to the Pre-PR Submission checklist. **Files touched**: `SKILL.md` (G64 + G62 reinforcement + checklist item + this entry); `config/skill-config.yaml` (8.45.0 → 8.46.0); `CHANGELOG.md` (this entry).
- **v8.45.0** (Jun 26, 2026): **submission-mechanics retro (2 new gotchas).** **MINOR bump** — from the qianfan [#33935](https://github.com/conda-forge/staged-recipes/pull/33935) test submission. **G62** (NEVER ship `cfe-*` metadata — the strip is a manual, *silent-if-skipped* step since rattler-build + conda-smithy ignore unknown `extra:` keys, so **verify it on the PUSHED artifact**: `gh api …contents/recipe.yaml?ref=<branch> | base64 -d | grep -nE 'cfe-\|# CFE'` before opening the PR; the under-strip complement of G60). **G63** (open staged-recipes PRs with the conda-forge **template + completed checklist** — `gh pr create --body`/`--body-file` REPLACES `.github/pull_request_template.md` rather than merging; fetch the live template [lowercase path] + tick the boxes). Both added as Pre-PR Quality-Gate **Submission** checklist gates. A full audit of all open + merged langflow-closure PRs confirmed zero cfe-metadata leaks (the strip had held, but unverified). **Files touched**: `SKILL.md` (G62/G63 + 2 checklist gates + this entry); `config/skill-config.yaml` (8.44.0 → 8.45.0); `CHANGELOG.md` (this entry).
- **v8.44.0** (Jun 26, 2026): **PR-debugging + sed→patch-sweep retro.** **MINOR bump** — 3 new gotchas + 1 refinement from a session that debugged 4 staged-recipes PRs to green and ran a repo-wide in-build-`sed`→source-patch conversion. **G59** (prefer a SOURCE PATCH over an in-build `sed` for editing upstream source: bare `sed -i 'script' file` fails on macOS/BSD sed — `noarch` builds on *every* platform — and reviewers prefer patches; move the edit to `source.patches` [top-level for multi-output]; exception = a `${{ version }}`-interpolating edit needs portable `sed -i.bak … && rm -f *.bak`; verify via the built wheel's METADATA + `noarch/`-vs-`broken/`; graph-retriever #33913 + pksuid #33895). **G60** (the strip-before-push must remove ONLY `extra.cfe-*` + `# CFE …` blocks — never the schema header or `context:`; dropping `context:` → `${{ version }}` undefined → render-fail on *all* platforms; langchain-litellm #33917). **G61** (GitHub `archive/<commit>.tar.gz` sha256 drifts when GitHub re-gzips → source-fetch `checksum validation failed`; recompute + prefer release/sdist tarballs; suite-st-transfers). **G40 refinement** (per-platform variant: a noarch consumer's real `python_min` can be forced by a COMPILED transitive dep that ships a Python version on some conda subdirs but not others — `fastuuid 0.14.0` has py3.10 on linux/win but only py3.11+ on osx-64 → langchain-litellm #33917 floor is 3.11; diagnose via per-subdir repodata). The sed→patch sweep (graph-retriever, pksuid, gibr, dataprofiler, agent-lifecycle-toolkit, db-gpt, milvus-lite, opendsstar, jigsawstack, langflow-base/langflow/langflow-suite, suite-*) all rebuilt+tested GREEN; repo now has zero bare `sed -i`. **Files touched**: `SKILL.md` (G59/G60/G61 + G40 refinement + this entry); `config/skill-config.yaml` (8.43.0 → 8.44.0); `CHANGELOG.md` (this entry).
- **v8.43.0** (Jun 25, 2026): **langflow-closure submission-session retro.** **MINOR bump** — 3 new gotchas + 2 refinements from a long multi-PR staged-recipes session (ibm-cos-suite + ~19 langflow-closure PRs + an impit platform-expansion). **G56** (multi-output `noarch:python` build scripts run on win-64 → bash `cd "$SRC_DIR/<sub>"`+`"$PYTHON"` fails on cmd.exe; use `${{ PYTHON }} -m pip install ./<sub>`; `crewai-suite` has the same latent bug; ibm-cos-suite #33886). **G57** (a build-control env var set only via bash `export` is UNSET on win-64 → build silently falls back to a network fetch / CMake FetchContent 404; set cross-platform after reading the upstream build code; couchbase #33893). **G58** (`lookup_feedstock` BEFORE submitting — a package already on conda-forge is rejected by the GHA `linter.py` "feedstock exists" check even while the linting-service bot says "excellent"; trust the GHA linter; impit #33897). **G19 refinement** (generalized beyond Rust to any win-64 cp1252 file read — pure-setuptools `setup.py open('README.md')` on a UTF-8 README; lomond #33889). **G26 refinement** (poetry-core builds the wheel METADATA from the sdist's `PKG-INFO`, not `pyproject.toml` — pyproject-only loosen sed passes locally, fails CI; patch all three files; pksuid #33895). Also: the adversarial BFS closure-audit workflow (prove a dep-closure spec has zero unpackaged gaps + name every blocker / list every net-new prereq — the langflow spec was missing 9), and the canonical compiled-Rust platform-expansion `conda-forge.yml` (cross-`linux_aarch64`, native `osx_arm64`, `test: native_and_emulated`; impit aarch64 cross-build verified GREEN locally). **Files touched**: `SKILL.md` (G56/G57/G58 + G19/G26 refinements + this entry); `config/skill-config.yaml` (8.42.2 → 8.43.0); `CHANGELOG.md` (this entry).
- **v8.42.2** (Jun 24, 2026): **wheel→source sweep retro — G54/G55 refinements.** **PATCH bump** — no new gotcha; refines the v8.42.0 source-preference rules from a `grep -rl 'cfe-source-kind:\s*pypi-wheel' recipes/` sweep. (1) **G54** — added a *retroactive-sweep* note (recipes generated before v8.42.0 may sit on a wheel when a usable sdist / GitHub source exists; audit + re-decide per recipe) and **corrected the case study**: the `ibm-watsonx-orchestrate-{core,clients}` "keep the wheel" call was overturned — their sdists are metadata-only, but the ADK monorepo ships source at `packages/{core,clients}` → migrated to GitHub source (GREEN). Lesson: *empty sdist ≠ no source*. Plus a *monorepo-subdir wrinkle*: build the subdir from the FULL extraction, because its dynamic version may read a file OUTSIDE it via a relative path (`[tool.hatch.version] path = "../../src/<pkg>/__init__.py"`) — isolating the subdir → G39 `0.0.0`. (2) **G55** — added the `setup_requires` / build-time network-fetch trap: a source build runs `setup.py`'s legacy `setup_requires` (or any net fetch) that a LOCAL build masks but conda-forge's OFFLINE CI fails on; strip it (`jigsawstack` `pytest-runner`) or host it. Corollary: *a clean local source build ≠ proof of offline-CI build*. (3) **cfe-source-kind** — keep it in sync with the `source:` block; a stale `pypi-wheel` (live: `pybase62`, already on a GitHub tag) mis-routes the next regen and hides the recipe from the sweep. Sweep migrations: `jigsawstack`, `ibm-watsonx-orchestrate-{core,clients}`, `lfx` (→ monorepo `src/lfx`); `pybase62` metadata-corrected. **Files touched**: `SKILL.md` (G54 + G55 + cfe-source-kind refinements + this entry); `config/skill-config.yaml` (8.42.1 → 8.42.2); `CHANGELOG.md` (this entry).
- **v8.42.1** (Jun 23, 2026): **langflow-closure retro — convention clarification.** **PATCH bump** — no new gotcha; verified v8.42.0's G54/G55 source-preference + build-backend rules held across the closure. Clarified the `extra.cfe-*` convention: recording the **first** local build on a recipe that has **no** `cfe-*` block (older pre-convention recipes — `firecrawl-py`, `mem0ai` — carried only `recipe-maintainers`) means adding the **full** canonical block, not a `cfe-local-build-*`-only six-field stub (the failure mode caught in local-recipes PR #24's first draft). Re-grounded `docs/specs/langflow-conda-forge.md` to current state (PRs #23–#27 merged → spec's "PR #25 (open)" + "only firecrawl-py lacks a build record" corrected; firecrawl-py/mem0ai now built; skill ref v8.35.0/G43 → v8.42.0/G55). The session's **staged-recipes-fork CI** findings are project-level (→ auto-memory, not the skill): the staged-recipes linter's hard-coded `{owner}/staged-recipes` repo-target 404s on a fork (use `github.repository`); the **ungated** `environment.yaml`↔`pixi.toml` sync check reds every PR until resynced (`pixi project export conda-environment -e build`); the `maintenance` label suppresses the linter's "outside `recipes/`" lint for non-recipe PRs. **Files touched**: `SKILL.md` (cfe-block first-build clarification + this entry); `config/skill-config.yaml` (8.42.0 → 8.42.1); `CHANGELOG.md` (this entry).
- **v8.42.0** (Jun 23, 2026): Source-selection + build-backend rules. **MINOR bump** — two new gotchas, no change to existing paths. Driven by the langflow closure: ~13 recipes sourced from PyPI **wheels** (the generator's fallback when no PyPI sdist) without ever checking GitHub, and a wheel→sdist switch then hit *"No valid build backend found … using pip."* (1) **G54 — source preference `sdist > GitHub-source > wheel`, with a usable-source check.** conda-forge prefers source over wheel; the generator never checks GitHub for wheel-only PyPI packages, and a naive sdist switch can ship `ModuleNotFoundError`/`0.0.0`. Decision order: usable PyPI sdist (verify it ships `.py` files — many are metadata-only/broken: `ibm-watsonx-orchestrate-*` sdists have 0 `.py`; `jigsawstack` omits a `requirements.txt` its build reads) → GitHub tag archive (incl. monorepo subdir via a separate `monorepo_tag` context var + `pip install ./src/<sub>`; autotick can't dual-bump) → wheel as last resort (documented). (2) **G55 — source builds need a build backend in `host`.** Wheel installs need none (so wheel recipes carry `host: [python, pip]`); a source build runs PEP 517 and requires the `[build-system]` backend in host — a wheel→source switch surfaces it. Backend map (setuptools / hatchling / flit-core / poetry-core / pdm-backend / scikit-build-core / maturin / `uv-build`). Enhanced the "PyPI source.url" wheel note to point at G54. Applied live: `langflow-sdk` switched wheel→GitHub-monorepo source (`src/sdk`, hatchling) — GREEN; `ibm-watsonx-orchestrate-{core,clients}` reverted to wheel (metadata-only sdists). Updated `config/skill-config.yaml` to 8.42.0.
- **v8.11.1** (Jun 2, 2026): Legacy-path cleanup + `edit_recipe` line-fold fix. **PATCH bump** — internal cleanup; no behavior change for the default path. Two follow-ups from v8.11.0's bmalph + yo CI runs. (1) **`recipe_editor.py` line-fold fix** — `ruamel.yaml`'s default `width=80` was folding long YAML strings (e.g. `pnpm-licenses generate-disclaimer --prod --output-file=third-party-licenses.txt`) into 2-line continuations during the load-modify-dump cycle of `edit_recipe`. The fold is semantically a no-op (YAML's implicit line-folding parses both forms to the same string) but cosmetically reviewers ask "why is this wrapped?". Set `yaml.width = 4096` so single-line items stay single-line. Caught when the IDE selection of `recipes/yo/recipe.yaml` showed the fold after `edit_recipe` was used to swap the `MAINTAINER` placeholder. (2) **Removed the legacy `--no-inline-build` escape hatch + its dead code**. The legacy path (noarch:generic + standalone build.sh + tee Windows shim) was kept "for back-compat" in v8.11.0 but it's BROKEN on current staged-recipes CI — that's why bmalph and yo PRs failed before the v8.11.0 refactor. Keeping a known-broken path adds maintenance burden with no real users. Dropped: `_build_sh_template` function (legacy build.sh emitter), `_template_npm_tarball_filename` helper (only consumer was the above), `inline_build` + `with_build_bat` + `no_bin_links` kwargs from `generate_npm_recipe_yaml`, `--inline-build` / `--no-inline-build` / `--with-build-bat` / `--no-bin-links` CLI flags, the `elif not inline_build:` branch in the conda-forge.yml emitter, the `if args.inline_build` extras-note line. Tests `test_npm_legacy_inline_build_false_emits_build_sh_and_cfy` + `test_npm_with_build_bat_opt_in` removed (the paths they exercise no longer exist). `test_npm_url_and_filename_are_version_templated` renamed to `test_npm_source_url_is_version_templated` (the filename helper test went with the helper). `test_npm_inline_build` renamed to `test_npm_inline_build_default` and simplified (no flag needed; inline IS the default). `test_npm_no_third_party_licenses_inline_build` renamed similarly. 44/44 tests pass (was 46; net -2 for the two deleted legacy tests). Generator output unchanged: regen of `recipes/bmalph` matches live byte-for-byte (modulo the `MAINTAINER` placeholder). Updated `config/skill-config.yaml` to 8.11.1.

- **v8.11.0** (Jun 2, 2026): npm generator switches default to per-platform inline build (openspec PR #32368 + bmalph PR #33557 pattern). **MINOR bump** — behavior change for all new npm recipes; legacy noarch:generic + standalone build.sh + tee Windows shim available via `--no-inline-build`. Driven by the bmalph PR #33557 CI failures that exposed two fundamental flaws in the v6+ "noarch:generic" canonical pattern: (1) rattler-build's symlink-portability check rejects the `bin/<cmd>` symlink that `npm install --global` creates on Unix because noarch:generic claims Windows compatibility where symlinks are non-portable; (2) staged-recipes CI builds noarch:generic on every platform, and without a `build.bat` the Windows leg runs nothing — no LICENSE staged → "No license files were copied" failure. The yo PR #33358 hit the same root cause (its `__unix`/`__win` virtual-package selectors are a different symptom of the same per-platform-vs-noarch tension). The merged openspec recipe (#32368) sidesteps both by dropping noarch:generic and using `build.script:` with `if: unix / then / else` branches — each platform's native `npm install --global` produces the right shape (Unix: symlinks-to-.js; Windows: native `.cmd` shims). Bmalph PR #33557's second attempt confirmed the pattern works cleanly on linux_64 + osx_64 + win_64 simultaneously (3m17s/6m14s/3m20s green CI). Six concrete changes in `scripts/recipe-generator.py`: (1) **`_inline_build_script` rewritten** to emit per-platform branches: `set -ex` + `pnpm install --ignore-scripts` + `npm pack --ignore-scripts` + `npm install --global "${SRC_DIR}/<filename>"` + `pnpm-licenses generate-disclaimer` on the Unix side; `call <cmd>` + `if %ERRORLEVEL% neq 0 exit 1` after every step on the Windows side. Tarball filename is jinja-templated (`${{ version }}`) — rattler-build pre-renders before the shell runs. (2) **`generate_npm_recipe_yaml` default `inline_build=True`** (was False); drops `noarch: generic` for ALL npm recipes when inline (native packages were already per-platform; pure-JS now matches). (3) **`requirements.host: nodejs`** now emitted for inline-build recipes (matches openspec; needed for the test-env solver). (4) **No standalone build.sh / build.bat / per-recipe conda-forge.yml** in the default output — staged-recipes' defaults cover everything and noarch_platforms restrictions are irrelevant when the recipe isn't noarch. (5) **`--inline-build` CLI flag rewired to `argparse.BooleanOptionalAction` with `default=True`** — `--no-inline-build` opts back into the pre-v8.11.0 standalone layout (noarch:generic + build.sh + per-recipe conda-forge.yml with `noarch_platforms: [linux_64]` + `shellcheck.enabled: true`); `--with-build-bat` documented as only effective with `--no-inline-build`. (6) **Feedstock-mode conda-forge.yml drops `noarch_platforms` and `shellcheck.enabled`** — feedstocks using the v8.11.0 pattern don't ship build.sh so shellcheck is a no-op and per-platform builds don't restrict to linux_64. **Test updates**: `test_npm_recipe_canonical_shape_offline` rewritten to assert the inline `script:` block + `if: unix` / `then:` / `else:` markers + per-platform commands + negative assertions (no build.sh, no conda-forge.yml, no `noarch: generic`); `test_npm_pure_js_keeps_noarch_generic` renamed to `test_npm_pure_js_omits_noarch_and_compilers` and reversed; `test_npm_prepare_fix` reads inline script from recipe.yaml instead of build.sh; `test_npm_default_mode_omits_feedstock_only_fields` renamed to `test_npm_default_mode_omits_conda_forge_yml`; new `test_npm_legacy_inline_build_false_emits_build_sh_and_cfy` asserts the back-compat path; live `test_npm_live_against_husky` + `test_npm_live_scoped_codex` updated for inline shape. 46/46 tests pass. Live verification: `recipe-generator.py npm bmalph` emits a recipe.yaml byte-for-byte identical to the CI-passing bmalph (modulo the `MAINTAINER` placeholder); no build.sh, no conda-forge.yml. **`scripts/_build_sh_template` + `_template_npm_tarball_filename` kept** for the legacy `--no-inline-build` path. Updated `config/skill-config.yaml` to 8.11.0. **Follow-up**: the yo PR #33358 will be regenerated with the new generator and force-pushed in the same session; expect the same green CI shape bmalph achieved.

- **v8.10.1** (Jun 2, 2026): npm generator emits `${{ version }}` in `source.url` + `${PKG_VERSION}` in `build.sh` + quoted `${PREFIX}` in the tee command. **PATCH bump** — bug fixes; no template additions. Driven by user-reported feedback on `recipes/bmalph` (npm@2.11.0). Three coupled bugs in `scripts/recipe-generator.py`'s npm path: (1) `fetch_npm_info` line 1593 set `source_url = tarball_url` literally — `v["dist"]["tarball"]` from the npm registry has the version baked in (`.../bmalph-2.11.0.tgz`). The autotick bot only mutates `context.version` and re-runs `calculate_hash` against the rendered URL; with a literal version in the URL, autotick would silently mint a recipe whose `context.version` advanced but whose source.url + sha256 still pointed at the previous tarball — a real functional bug, not just a style issue. New helper `_template_npm_source_url(url, version)` rewrites the `-<version>.tgz` (or `v<version>.tar.gz` for `--source github`) suffix to `${{ version }}`. Falls back to literal URL for unrecognized shapes. (2) `_build_sh_template` + `_inline_build_script` emitted `${{SRC_DIR}}/{info.tarball_filename}` literally (e.g. `${SRC_DIR}/bmalph-2.11.0.tgz`). New helper `_template_npm_tarball_filename(filename, version)` rewrites the version suffix to `${PKG_VERSION}` (bash env var, injected by rattler-build into build scripts — not jinja). Mirrors the existing `yo` and `generator-code` recipe pattern in this repo. (3) SC2086 shellcheck issue exposed by [staged-recipes#33358](https://github.com/conda-forge/staged-recipes/pull/33358) reviewer feedback: `tee ${PREFIX}/bin/<name>.cmd << EOF` needs `${PREFIX}` quoted. Both `_build_sh_template` and `_inline_build_script` updated to emit `tee "${PREFIX}"/bin/...`. New test `test_npm_url_and_filename_are_version_templated` covers all three helpers + a fallback case for unrecognized URLs; existing `test_npm_recipe_canonical_shape_offline` updated to assert templated forms + the `tee "${PREFIX}"/bin/` quoting + negative assertions (literal version must NOT appear in recipe or build.sh). 45/45 tests pass. Live verification: `recipe-generator.py npm bmalph` emits `source.url: .../bmalph-${{ version }}.tgz`, build.sh writes `"${SRC_DIR}/bmalph-${PKG_VERSION}.tgz"` + `tee "${PREFIX}"/bin/bmalph.cmd`. Updated `recipes/bmalph/recipe.yaml` + `build.sh` to match (and rebuilt clean). Updated `config/skill-config.yaml` to 8.10.1. PyPI / CRAN / CPAN / LuaRocks paths not audited in this patch — left for a follow-up sweep.

- **v8.10.0** (May 26, 2026): Drop `context.name` from Python v1 recipes; switch `package.name` and `source.url` to fully-literal form. **MINOR bump** — additive + corrective; matches what current grayskull emits and what conda-forge reviewers asked for on `recipes/xorq-datafusion` and `recipes/py-yaml12`. Three concrete changes in `scripts/recipe-generator.py`: (1) `_build_source_url_template()` rewritten to emit `https://pypi.org/packages/source/<first-letter>/<distribution-name>/<sdist-stem>-${{ version }}.tar.gz` — only `${{ version }}` interpolates; first letter, distribution name, and sdist filename stem are all literal. Drops the v8.9.1 `${{ name[0] }}` / `${{ name }}` / `${{ name | replace("-", "_") }}` chain entirely. (2) `generate_recipe_yaml()` (noarch path) drops `name:` from `context:`, switches `package.name:` from `${{ name | lower }}` to literal `info.name.lower()`. (3) `_generate_maturin_recipe_yaml()` does the same. (4) `generate_meta_yaml()` (v0 path) translates the v1 `${{ version }}` syntax in `info.source_url` down to v0 `{{ version }}` so meta.yaml renders correctly under conda-build jinja (closes a latent bug that surfaced once `info.source_url` carries v1 syntax). Three template updates: (5) `templates/python/noarch-recipe.yaml`, (6) `templates/python/compiled-recipe.yaml`, (7) `templates/python/maturin-recipe.yaml` — all drop the `context.name` line, switch `package.name` to a `REPLACE_NAME` literal placeholder, and rewrite the URL to literal segments with `REPLACE_SDIST_STEM-${{ version }}` for the filename stem (preserves the hyphen-vs-underscore distinction reviewers care about). SKILL.md updates: (8) "PyPI `source.url` Must Use..." critical-constraint section rewritten to show the literal pattern as canonical, including the why ("renames are rare, version bumps are common; the literal form is more legible and removes a class of jinja-typo bugs"). (9) "Recipe Formats Quick Reference" v1 example block updated to match. Live verification: `recipe-generator.py pypi rich` emits `package.name: rich` + `source.url: .../r/rich/rich-${{ version }}.tar.gz` + no `context.name`; `recipe-generator.py pypi py-yaml12` emits `package.name: py-yaml12` + `.../p/py-yaml12/py_yaml12-${{ version }}.tar.gz` (matches the user's existing `recipes/py-yaml12/recipe.yaml` byte-for-byte in the changed sections). 44/44 `test_recipe_generator.py` tests still pass. Non-Python templates (Rust CLI, Go, R, etc.) and v0 meta.yaml templates are intentionally untouched — grayskull's literal-URL convention applies to v1 Python recipes; v0 meta.yaml is legacy and grayskull's v0 output still emits `{% set name %}`. Updated `config/skill-config.yaml` to 8.10.0.

- **v8.9.1** (May 25, 2026): Two corrections on top of v8.9.0. **PATCH bump** — additive + corrective; same-day follow-up. (1) **Grayskull-style interpolated source URL**: new `_build_source_url_template()` helper emits `https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/<stem-template>-${{ version }}.tar.gz` where `<stem-template>` is `${{ name }}`, `${{ name | lower }}`, `${{ name | replace("-", "_") }}`, or `${{ name | lower | replace("-", "_") }}` depending on how the sdist filename relates to the distribution name. Version bumps now only touch `${{ version }}`. Falls back to a literal URL when the filename doesn't parse cleanly. `fetch_pypi_info` now tracks both the **concrete** URL (used internally to download the sdist) and the **templated** URL (emitted into the recipe) — fixes the v8.9.0 latent bug where I'd routed `source_url` through the sdist-cache helper with unrendered jinja inside. (2) **CARGO_PROFILE_RELEASE_{STRIP, LTO} env vars are conda-forge documented standard for ALL Rust builds**, not just CLI binaries. Per [conda-forge.org/.../rust](https://conda-forge.org/docs/maintainer/example_recipes/rust/) — "this recipe template supports different features: `CARGO_PROFILE_RELEASE_STRIP=symbols` … `CARGO_PROFILE_RELEASE_LTO=fat`". My v8.9.0 chose to **skip** these in the maturin template based on the empirical 27-PR sample where only 3-7/27 used them. But the docs are prescriptive, not descriptive — empirical low adoption reflects older PyO3 recipes authored before the guidance landed, not a maintainer rejection of the pattern. The maturin template + `_generate_maturin_recipe_yaml` now emit `script.env` with both env vars; `cargo build` (invoked internally by maturin) inherits them and produces a stripped + LTO-optimized cdylib. Cargo-auditable was investigated but **skipped** in this patch — maturin uses `cargo build` not `cargo install`, so wiring `cargo auditable` would require a `CARGO=cargo-auditable` wrapper that isn't first-class supported by maturin; defer to v8.10+ if community pressure builds. (3) Updated `recipes/py-yaml12/recipe.yaml` to match the new generator output (interpolated URL + env vars). Live verification: `recipe-generator.py pypi py-yaml12` emits the maturin route with `version_independent: true` + env vars + interpolated URL + 0 optimizer suggestions. `recipe-generator.py pypi rich` emits the noarch route with interpolated URL + 0 optimizer suggestions. Updated `config/skill-config.yaml` to 8.9.1.

- **v8.9.0** (May 25, 2026): Maturin/PyO3 generator routing + sdist-driven import-name extraction + abi3-gated `version_independent` + maturin template rewrite to phonors-pattern minimum. **MINOR bump** — additive + corrective; no breaking change. Driven by `recipes/py-yaml12` recipe build surfacing that `recipe-generator.py pypi <name>` produced an incorrect `noarch: python` recipe for a PyO3 package. Spec: `docs/specs/conda-forge-expert-v8.9.md`. Empirical anchor: 52 Rust label PRs (CLI subset `cargo auditable` 39/42 = 93%; CARGO_HOME 0/25 = 0%) + 27 PyO3/maturin PRs (Mar 2020 – May 2026: maturin in host 67%, version_independent 7%, CFEP-25 matrix 4%, Windows CARGO_HOME 4%) + 30 pure-python PRs + 5 docs sources (4 example_recipes/tutorials + new knowledge_base). Six concrete generator changes in `scripts/recipe-generator.py`: (1) **sdist cache** (`_sdist_cache_path`, `_ensure_sdist_cached`) — downloads sdist once per run under `/tmp/cfe-sdist-cache/` for authoritative metadata extraction; air-gap safe (network failure → fall back to PyPI JSON heuristics). (2) **`_extract_import_name_from_sdist()`** — reads `Cargo.toml [lib] name` + cross-checks `src/lib.rs #[pymodule] pub fn <X>()` for PyO3 packages; falls back to first-`__init__.py` for pure-Python. Closes G7 trap (`py-yaml12` → `yaml12`, not `py_yaml12`). (3) **`_extract_abi3_from_sdist()`** — regex-matches three Cargo.toml abi3 forms: `default = ["abi3"]`+`abi3 = ["pyo3/abi3-py3XX"]`, `pyo3 = { features = ["abi3-py3XX"] }`, bare `abi3 = ["pyo3/abi3-py3XX"]`. Gates `version_independent: true` emission so it appears only when the upstream actually builds abi3 wheels. (4) **`_extract_build_system_requires_from_sdist()`** — parses `pyproject.toml [build-system].requires` (the authoritative source for the build backend; G2 fix). PyPI's `requires_dist` only lists runtime deps. (5) **`_extract_entry_points_from_sdist()`** — parses `[project.scripts]` for CLI Python packages (Wave D / S18). (6) **`_classify_sys_platform_deps()`** — maps `colorama ; sys_platform == 'win32'` markers to `{"win": ["colorama"]}` for virtual-package `if: win / then:` selector emission (Wave D / S16; per knowledge_base virtual-package rule). New routing: `generate_recipe_yaml()` checks `info.build_backend == "maturin"` first and delegates to **`_generate_maturin_recipe_yaml()`** — a compiled-extension shape modelled on the phonors PR (the modal 27-PR PyO3 pattern), with optional `version_independent: true` block, no `noarch: python`, Rust toolchain in build, maturin in host. The pure-python path now also routes import-name through the sdist extraction. **Template rewrite**: `templates/python/maturin-recipe.yaml` simplified to the phonors shape (2-line script; no CFEP-25 matrix in tests; no Windows CARGO_HOME block; no CARGO_PROFILE_RELEASE_* env; `version_independent` annotated as opt-in commented block); now carries adoption-percentage citations in its header comment. **Rust CLI template addition**: `cli-recipe.yaml` now notes the `provider: osx_arm64: azure` conda-forge.yml requirement when shell-completion generation is enabled (cross-compile cannot run the native binary). **Live verification**: `recipe-generator.py pypi py-yaml12` now emits a clean maturin recipe with import `yaml12` + `version_independent: true` (abi3 detected from Cargo.toml) + 0 optimizer suggestions; `recipe-generator.py pypi rich` continues to emit the noarch shape; `recipe-generator.py pypi httpx` continues clean. Build verified: `recipes/py-yaml12` produces 4 conda artifacts for py310/py311/py312/py313 with the new template shape. Updated `config/skill-config.yaml` to 8.9.0.

- **v8.8.0** (May 25, 2026): Python recipe generator + template alignment with conda-forge canonical pure-python example. **MINOR bump** — additive + corrective. Driven by deep-research of [conda-forge.org pure-python](https://conda-forge.org/docs/maintainer/example_recipes/pure-python/) + rattler-build's [Python tutorial](https://rattler-build.prefix.dev/latest/tutorials/python/) and [Rust tutorial](https://rattler-build.prefix.dev/latest/tutorials/rust/), validated against 30 fresh merged Python staged-recipes PRs + 27 Rust PRs. Key finding: the conda-forge docs + recent merged PRs **lead** rattler-build's tutorials by ~12 months on Rust (rattler-build shows plain `cargo install`; conda-forge + PR sample show `cargo auditable install --locked --no-track --bins` at 17/17 adoption). Source-of-truth order codified in skill: conda-forge docs > merged PRs > rattler-build tutorials. Five generator gaps closed in `scripts/recipe-generator.py`: (1) `generate_recipe_yaml` now emits the CFEP-25 dual-version test matrix (`python_version: [${{ python_min }}.*, "*"]`); without this the optimizer's TEST-002 fired on every recipe the generator just produced — self-consistency fix. (2) `about:` block now includes `description: |`, `repository`, `documentation` extracted from PyPI's `project_urls` (handles all spelling variants: Repository/Source/Source Code/Code, Documentation/Docs, Homepage/Home). (3) `_extract_project_urls()` helper added; populated into the new `PackageInfo.repository` + `.documentation` fields. (4) `python_min:` in context is conditionally emitted only when the conda-forge floor (3.10) is exceeded — at the default it's now omitted, matching what 26/30 sampled PRs do. (5) New `_resolve_python_min()` helper clamps the parsed `python_requires` floor to the conda-forge minimum (3.10) — previously a package declaring `python_requires>=3.9` produced an invalid recipe with `python_min: "3.9"`. (6) `determine_build_backend()` now detects `pdm-backend` and `scikit-build-core` (1/30 emerging + modern compiled backend). (7) `generate_meta_yaml` mirrors patterns #1, #2, #4, #5 in v0 jinja syntax. Three template updates: (8) `templates/python/noarch-recipe.yaml` drops `python_min: "3.10"` from context (replaced with explanatory comment) + adds `pdm-backend` and `scikit-build-core` to the commented backend list. (9) `compiled-recipe.yaml` + `maturin-recipe.yaml` were already correct — no `python_min` in context. SKILL.md edits: (10) "Every v1 Recipe Must Declare the Schema Header" subsection now honest about empirical scope — 1/30 fresh PRs carry the comment; this is a local-recipes repo convention, not a conda-forge-wide requirement; reviewers do not block PRs that omit it. (11) Rust Recipe Standards subsection gains a one-line source-of-truth note explaining the divergence from rattler-build's tutorial. Live verification: `python recipe-generator.py pypi rich` now emits a clean recipe.yaml that passes `optimize_recipe` without TEST-002 or ABT-001 firing; `python_min: "3.9"` (rich's PyPI floor) correctly clamped to 3.10 + omitted from context. **No existing recipes in `recipes/` were touched** — generator-side change, idempotent for unchanged recipes.

- **v8.7.0** (May 25, 2026): Rust recipe template refresh + universal schema-header enforcement. **MINOR bump** — additive: new optimizer check + 3 template rewrites + 1 new SKILL.md subsection; no behavior change for non-Rust recipes. Driven by a 21-PR sample (6 first-pass + 15 expanded) of CLI Rust recipes merged to conda-forge/staged-recipes Apr–May 2026 plus the live [conda-forge.org/docs/maintainer/example_recipes/rust](https://conda-forge.org/docs/maintainer/example_recipes/rust/) page. Adoption across the CLI-Rust slice (17/17 = 100%): `cargo auditable install` (instead of plain `cargo install`), `--locked --no-track --bins`, unix/win install-root split (`${{ PREFIX }}` vs `%LIBRARY_PREFIX%`), `script.env`+`script.content` shape with `CARGO_PROFILE_RELEASE_STRIP: symbols` + `CARGO_PROFILE_RELEASE_LTO: fat`, `cargo-bundle-licenses` + `cargo-auditable` together in build deps, `package_contents` with `strict: true`. Holdouts in the 21-PR sample were all justified non-CLI patterns: pyo3/maturin Python extensions (`cachebox`, `phonors`, `cocoindex` — use pip install), Rust compilers with custom build scripts (`inko` — nushell `interpreter:` script), and 1 partial-adoption case (`goose`). Five concrete changes shipped: (1) **`templates/rust/cli-recipe.yaml`** — full rewrite to canonical pattern (auditable + no-track + bins + unix/win split + env map + LTO/strip + cargo-auditable in build + strict package_contents); shell-completion block commented in as opt-in. (2) **`templates/rust/library-recipe.yaml`** — added the env map for STRIP/LTO; kept the cdylib pattern (no `cargo install` — libs use `cargo build --release` + manual copy). (3) **`templates/rust/cli-meta.yaml`** — meta.yaml v0 mirror of cli-recipe.yaml (auditable + no-track + bins via `script_env:` since v0 lacks script.env+content) for legacy feedstocks. (4) **New optimizer check `SCHEMA-001`** in `recipe_optimizer.py` — flags any `recipe.yaml` (v1 file) that lacks the `# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json` header or `schema_version: 1` directive. Wired before format-mixing in the critical-constraints batch. Generator already emits both lines on all 3 v1 generation paths (PyPI/grayskull at line 255-256, rattler-generate via `_ensure_yaml_language_server_header` at line 1350, npm path explicit at line 1079-1080); SCHEMA-001 closes the gap for user-edited / hand-migrated recipes. v0 meta.yaml files are excluded from the check (the prefix-dev schema is v1-only). (5) **SKILL.md** — new "Every v1 Recipe Must Declare the Schema Header" + "Rust Recipe Standards (CLI binaries — conda-forge 2026 canonical pattern)" subsections in Critical Constraints, listing the 5 universal patterns + explicit exception list (pyo3/maturin, cdylib libraries, custom-script projects). Quarterly audit cron sweep should flag any future drift in the upstream docs. Updated `config/skill-config.yaml` to 8.7.0.

- **v8.6.0** (May 24, 2026): AppThreat Deep Signals — EPSS + CWE rollup wired into Phase G/G' overlay; schema v23 → v24 → v25 (v24 provisioned for Waves B/C; v25 cleanup dropped the Wave-C-cancelled `package_hardening` table + `vuln_total_active` + `vuln_withdrawn_count` columns); new fetchers `fetch-epss` (FIRST.org EPSS daily CSV from `epss.empiricalsecurity.com`; parent spec's `cyentia.com` URL was stale) + `fetch-cwe-catalog` (MITRE CWE Research Concepts at `/data/csv/1000.csv.zip`; parent spec said `2000.csv.zip` — wrong, that's Architectural Concepts); new `_load_epss_scores` + `_load_cwe_categories` helpers + shared `_aggregate_v8_6_0_overlays` pure function consumed by both Phase G + Phase G'; `_phase_g_sync_current_rollup` extended with COALESCE-to-existing pattern for new columns (review-finding fix — earlier draft clobbered Phase G's direct writes when Phase G' ran with stale maps); 4 new CLI flags (`staleness-report --by-epss / --has-cwe`, `my-feedstocks --epss / --cwe`, `cve-watcher --epss-threshold`); `detail-cf-atlas` auto-renders new EPSS + CWE rows; persona-profile auto-runs (maintainer + admin set `BOOTSTRAP_FETCH_CISA_KEV` + `BOOTSTRAP_FETCH_EPSS` + `BOOTSTRAP_FETCH_CWE_CATALOG`; consumer skips for air-gap). **MINOR bump** (additive: 2 fetchers + 4 packages columns survive v25 cleanup + 4 CLI flags + persona-profile gates; no breaking CLI/MCP changes). **Wave C CANCELLED pre-implementation** (Phase T blint: conda-forge's hermetic compile env produces uniform hardening — ~zero per-package variance; Phase U EPSS overlay phase: redundant with Wave B's `_phase_g_sync_current_rollup` extension). **Wave B withdrawn-filter scope DROPPED** after verifying vdb's OSV and GHSA ingest paths both skip withdrawn records at source; columns provisioned in Wave A → dropped in Wave D's v25 migration. **Four parent-spec corrections** caught by verify-don't-assume: MITRE 1000-vs-2000 URL; blint PyPI name (`blint` not `owasp-blint` — 404); withdrawn-filter redundancy; Phase U redundancy. Suite: 1,137 passing. Live verification: 334,683 EPSS rows + 944 CWEs ingested; channel-wide Phase G run populated 213 packages with EPSS + 216 with CWE classifications. Wave A commit `e4ba891cd2`; Wave B `e22c531ac2`; Wave D (this release) bundles Wave C cancellation + schema v25 cleanup + closeout. Retro at `_bmad-output/projects/local-recipes/implementation-artifacts/`. Updated `config/skill-config.yaml` to 8.6.0.

- **v8.3.0** (May 17, 2026): Three new recipe-authoring gotchas from the Microsoft Agents bundle (`azure-identity-broker` + `microsoft-kiota-bundle` + `microsoft-agents-m365copilot{-core,}`) and the npm bundle (`yo` + `generator-code`). **MINOR bump** — additive only. (1) **G7** — "Grayskull's inferred Python import name can be wrong — verify against the sdist": grayskull defaults the import test to the PyPI distribution name with hyphens→underscores, which is wrong for re-exported short names (`microsoft-kiota-bundle` → `kiota_bundle`), dotted namespace packages (`azure-identity-broker` → `azure.identity.broker`), and renamed-on-PyPI packages (`PyYAML` → `yaml`). The only authoritative source is the sdist's top-level `__init__.py`; verify with `tar tzf <sdist> | grep '__init__.py$' | head -3`. Case: `microsoft-kiota-bundle` v1.10.1 — generated `imports: [microsoft_kiota_bundle]`, actual is `kiota_bundle`. (2) **G8** — "Grayskull adds redundant `wheel` + `setuptools` host deps for poetry-core projects": belt-and-suspenders behavior; for any PEP 517 project with a single declared backend (`poetry-core`, `hatchling`, `flit-core`, `pdm-backend`, `scikit-build-core`), only that backend + `pip` is needed in `host:`. Inspect `pyproject.toml` `[build-system].requires` and drop everything not listed. Case: `microsoft-agents-m365copilot{-core,}` both got the redundant pair despite their `pyproject.toml` declaring only `poetry-core`; the third sibling `microsoft-kiota-bundle` was emitted clean — grayskull's behavior is non-deterministic across runs. (3) **G9** — "Monorepo upstreams may have no per-language Git tag — pin the LICENSE to a commit hash": G4 (sdist-missing-LICENSE) recommends `https://raw.githubusercontent.com/<org>/<repo>/v${{ version }}/LICENSE` but that's 404 when the project tags only its JS / .NET / Java releases (`microsoft/Agents-M365Copilot` only tags `@microsoft/agents-m365copilot-v1.6.0`, not `v1.6.0`). Fix: pin to a specific commit SHA + sha256, document the trade-off in the PR description (bot needs a manual LICENSE refresh on every version bump — autotick won't handle it). Case: `microsoft-agents-m365copilot` v1.6.0 — LICENSE pinned to commit `0376aa41834...`. Also: in v8.3.0 the v8.2.0 `native-build.sh` auto-channel injection was validated in production across a 4-recipe Microsoft Agents bundle (`m365copilot` resolved freshly-built `kiota-bundle` + `m365copilot-core` from the local channel without manual intervention). Updated `config/skill-config.yaml` to 8.3.0.

- **v8.2.0** (May 17, 2026): Local-build ergonomics + new gotcha. From the `yo` + `generator-code` two-recipe bundling session. (1) **New gotcha G6** — "npm packages with rich transitive deps ship `node_modules/.bin/` symlinks that fail noarch builds": documents that npm packages with substantial transitive dep trees (Yeoman generators, anything pulling `ejs` / `jake` / `semver` / `yosay` / `@octokit/*`) trigger rattler-build's noarch Windows-portability check after writing the artifact; minimal-dep packages (`copilot-api`, `openspec`) don't. The surgical fix is `find ${PREFIX}/lib/node_modules/<name> -type d -name .bin -exec rm -rf {} +` between `npm install --global` and `pnpm install`. `--allow-symlinks-on-windows` is local-only (staged-recipes CI rejects); `--no-bin-links` kills the top-level CLI shim. Case study: `generator-code` v1.11.18 first build `-hccbf638_0.conda` rejected, fixed build `-h5e06de4_0.conda` clean. (2) **`native-build.sh` auto-injects the local channel** — detects `build_artifacts/<config>/*/repodata.json` and prepends `file://${REPO_ROOT}/build_artifacts/<config>` to `channel_sources` via an `mktemp`'d 3rd `--variant-config` (rattler-build rejects mixing `--channel` flags with a variant-set `channel_sources`). Cleaned up via `EXIT` trap; switched `exec rattler-build` → direct invocation so the trap actually fires. Use case: recipe B has `run: A` where A was just built locally — `pixi run -e local-recipes recipe-build recipes/B` Just Works instead of requiring a hand-rolled variant config. Updated `config/skill-config.yaml` to 8.2.0.

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
