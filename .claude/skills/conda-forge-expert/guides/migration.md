# Migration Guide: meta.yaml to recipe.yaml

Complete guide for converting conda recipes from legacy meta.yaml format to modern recipe.yaml (v1) format.

## Migration Decision Framework

*From `deprecation-and-migration`. Use this before touching a recipe — it prevents unnecessary churn.*

### Should You Migrate This Recipe?

Work through this decision tree before converting any recipe:

```
Is there an active PR or build in progress for this recipe?
  YES → Wait until it merges/closes. Never migrate mid-flight.
  NO  → Continue.

Is this recipe in staged-recipes (new submission)?
  YES → Use recipe.yaml v1 from the start. Do not create meta.yaml.
  NO  → Is it an existing feedstock? Continue.

Does the existing feedstock have open PRs?
  YES → Coordinate with maintainers or wait.
  NO  → Continue.

Does the package build cleanly in its current format?
  NO  → Fix the current format first. Migrating broken recipes is churn.
  YES → Migration is appropriate.
```

### The Churn Rule

**Do not migrate a recipe that already builds correctly unless:**
- The feedstock has explicitly requested v1 migration
- You are fixing a python_min/stdlib/other policy violation that cannot be expressed in meta.yaml
- The PR is specifically for migration (`migrate-to-v1` branch)

Migrating a working recipe "while you're in there" creates unnecessary diff noise and risks introducing regressions. The migration itself is a separate, atomic PR.

### Strangler Pattern for Safe Migration

Never do a "big bang" rewrite. Migrate incrementally:

1. **Keep meta.yaml intact** — `migrate_to_v1()` creates `recipe.yaml` alongside it; do not delete meta.yaml yet
2. **Build and validate the new format** — `validate_recipe()` + `trigger_build()` → confirm green
3. **Compare outputs** — rendered recipe and package contents should be identical
4. **Remove meta.yaml** — only after the new format is verified and the PR is ready to merge
5. **One recipe per PR** — never bundle multiple migrations in one PR

### Format Mixing Prohibition

`meta.yaml` and `recipe.yaml` **cannot coexist in the same build run** — the toolchain will reject it. The `optimize_recipe()` STD-002 check flags this with confidence=1.0. If both files exist, either:
- Delete `meta.yaml` (after verifying `recipe.yaml` builds), or
- Delete `recipe.yaml` (if migration is incomplete and meta.yaml is the source of truth)

---

## Overview

| Feature | meta.yaml | recipe.yaml |
|---------|-----------|-------------|
| Templating | `{{ var }}` (Jinja2) | `${{ var }}` |
| Selectors | `# [linux]` comments | `if/then/else` blocks |
| Variables | `{% set var = ... %}` | `context:` section |
| Tests | `test:` (singular) | `tests:` (list) |
| Validation | None | YAML schema |

## Quick Reference

### Variables

```yaml
# meta.yaml
{% set name = "my-package" %}
{% set version = "1.2.3" %}

package:
  name: {{ name }}
  version: {{ version }}
```

```yaml
# recipe.yaml
context:
  name: my-package
  version: "1.2.3"

package:
  name: ${{ name }}
  version: ${{ version }}
```

### Platform Selectors

```yaml
# meta.yaml
requirements:
  build:
    - gcc       # [linux]
    - clang     # [osx]
    - vs2019    # [win]
```

```yaml
# recipe.yaml
requirements:
  build:
    - if: linux
      then: gcc
    - if: osx
      then: clang
    - if: win
      then: vs2019
```

### Skip Conditions

```yaml
# meta.yaml
build:
  skip: true  # [py<39]
  skip: true  # [win]
```

```yaml
# recipe.yaml
build:
  skip:
    - py < 39
    - win
```

### Tests Section

```yaml
# meta.yaml
test:
  imports:
    - mypackage
  commands:
    - pip check
  requires:
    - pip
```

```yaml
# recipe.yaml
tests:
  - python:
      imports:
        - mypackage
      pip_check: true
  - script:
      - mycommand --version
```

## Automated Conversion

### Using rattler-build

```bash
rattler-build generate-recipe convert meta.yaml > recipe.yaml
```

### Using conda-recipe-manager

```bash
pip install conda-recipe-manager
conda-recipe-manager convert meta.yaml > recipe.yaml
```

### Using feedrattler (Full Feedstock)

```bash
pixi exec feedrattler my-package-feedstock your-github-username
```

## Manual Conversion Steps

### Step 1: Add Schema Header

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1
```

### Step 2: Convert Variables

**Before:**
```yaml
{% set name = "my-package" %}
{% set version = "1.2.3" %}
{% set sha256 = "abc123..." %}
```

**After:**
```yaml
context:
  name: my-package
  version: "1.2.3"
  sha256: abc123...
```

### Step 3: Convert Jinja Expressions

| meta.yaml | recipe.yaml |
|-----------|-------------|
| `{{ name }}` | `${{ name }}` |
| `{{ name\|lower }}` | `${{ name \| lower }}` |
| `{{ compiler('c') }}` | `${{ compiler("c") }}` |
| `{{ pin_subpackage('pkg', max_pin='x.x') }}` | `${{ pin_subpackage("pkg", upper_bound="x.x") }}` |

### Step 4: Convert Selectors

**Before (inline selectors):**
```yaml
requirements:
  build:
    - {{ compiler('c') }}       # [unix]
    - {{ compiler('m2w64_c') }} # [win]
  host:
    - python
    - numpy                     # [not win]
```

**After (if/then blocks):**
```yaml
requirements:
  build:
    - if: unix
      then: ${{ compiler("c") }}
    - if: win
      then: ${{ compiler("m2w64_c") }}
  host:
    - python
    - if: not win
      then: numpy
```

### Step 5: Convert Build Section

**Before:**
```yaml
build:
  number: 0
  skip: true  # [py<39]
  script: {{ PYTHON }} -m pip install . -vv
  entry_points:
    - mycli = mypackage.cli:main
```

**After:**
```yaml
build:
  number: 0
  skip:
    - py < 39
  script: ${{ PYTHON }} -m pip install . -vv
  python:
    entry_points:
      - mycli = mypackage.cli:main
```

### Step 6: Convert Test Section

**Before:**
```yaml
test:
  imports:
    - mypackage
    - mypackage.submodule
  commands:
    - pip check
    - mycli --version
    - mycli --help
  requires:
    - pip
    - pytest
  source_files:
    - tests/
```

**After:**
```yaml
tests:
  - python:
      imports:
        - mypackage
        - mypackage.submodule
      pip_check: true

  - script:
      - mycli --version
      - mycli --help

  - script:
      - pytest tests/ -v
    requirements:
      run:
        - pytest
    files:
      source:
        - tests/
```

### Step 7: Convert About Section

**Before:**
```yaml
about:
  home: https://github.com/org/pkg
  license: MIT
  license_family: MIT
  license_file: LICENSE
  summary: Short description
  doc_url: https://docs.example.com
  dev_url: https://github.com/org/pkg
```

**After:**
```yaml
about:
  homepage: https://github.com/org/pkg
  license: MIT
  license_file: LICENSE
  summary: Short description
  documentation: https://docs.example.com
  repository: https://github.com/org/pkg
```

### Step 8: Convert run_exports

**Before:**
```yaml
build:
  run_exports:
    - {{ pin_subpackage(name, max_pin='x.x') }}

  # OR with strength
  run_exports:
    strong:
      - {{ pin_subpackage(name, max_pin='x.x') }}
    weak:
      - openssl
```

**After:**
```yaml
build:
  run_exports:
    - ${{ pin_subpackage(name, upper_bound="x.x") }}

  # OR with strength
  run_exports:
    strong:
      - ${{ pin_subpackage(name, upper_bound="x.x") }}
    weak:
      - openssl
```

### Step 9: Convert ignore_run_exports

**Before:**
```yaml
build:
  ignore_run_exports:
    - libfoo
  ignore_run_exports_from:
    - {{ compiler('cuda') }}
```

**After:**
```yaml
requirements:
  ignore_run_exports:
    by_name:
      - libfoo
    from_package:
      - ${{ compiler("cuda") }}
```

### Step 10: Convert Multi-Output

**Before:**
```yaml
outputs:
  - name: libfoo
    script: build-lib.sh
    build:
      run_exports:
        - {{ pin_subpackage('libfoo', max_pin='x.x') }}
    requirements:
      build:
        - {{ compiler('c') }}
    test:
      commands:
        - test -f $PREFIX/lib/libfoo.so
```

**After:**
```yaml
outputs:
  - package:
      name: libfoo
    build:
      script: build-lib.sh
      run_exports:
        - ${{ pin_subpackage("libfoo", upper_bound="x.x") }}
    requirements:
      build:
        - ${{ compiler("c") }}
    tests:
      - script:
          - test -f $PREFIX/lib/libfoo${{ shlib_ext }}
```

## Complex Conversions

### Jinja Conditionals

**Before:**
```yaml
{% if cuda_compiler_version != "None" %}
requirements:
  build:
    - {{ compiler('cuda') }}
{% endif %}
```

**After:**
```yaml
requirements:
  build:
    - if: cuda_compiler_version != "None"
      then: ${{ compiler("cuda") }}
```

### Dynamic Skip Lists

**Before:**
```yaml
{% set tests_to_skip = "_not_a_test" %}
{% set tests_to_skip = tests_to_skip + " or test_network" %}
{% set tests_to_skip = tests_to_skip + " or test_slow" %}  # [aarch64]

test:
  commands:
    - pytest -k "not ({{ tests_to_skip }})"
```

**After:**
```yaml
context:
  base_skip: "_not_a_test or test_network"
  skip_slow: ${{ " or test_slow" if aarch64 else "" }}
  tests_to_skip: ${{ base_skip }}${{ skip_slow }}

tests:
  - script:
      - pytest -k "not (${{ tests_to_skip }})"
```

### Build Number Variants

**Before:**
```yaml
{% set build_number = 0 %}

build:
  number: {{ build_number + 200 }}  # [cuda_compiler_version != "None"]
  number: {{ build_number }}         # [cuda_compiler_version == "None"]
```

**After:**
```yaml
context:
  build_number: 0
  cuda_offset: ${{ 200 if cuda_compiler_version != "None" else 0 }}

build:
  number: ${{ build_number + cuda_offset }}
```

### Cross-Compilation

**Before:**
```yaml
requirements:
  build:
    - {{ compiler('c') }}
    - python                                     # [build_platform != target_platform]
    - cross-python_{{ target_platform }}         # [build_platform != target_platform]
```

**After:**
```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}
```

## Field Name Changes

| meta.yaml | recipe.yaml |
|-----------|-------------|
| `home:` | `homepage:` |
| `doc_url:` | `documentation:` |
| `dev_url:` | `repository:` |
| `license_family:` | (removed) |
| `max_pin:` | `upper_bound:` |
| `min_pin:` | `lower_bound:` |
| `folder:` | `target_directory:` |
| `git_url:` | `git:` |
| `git_rev:` | `rev:` or `tag:` |
| `source_files:` | `files: source:` |
| `test:` | `tests:` |

## Validation

### Validate Converted Recipe

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('recipe.yaml'))"

# Render recipe
rattler-build build -r recipe.yaml --render-only

# Full lint
conda-smithy recipe-lint .
```

### Common Conversion Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Invalid YAML | Missing quotes around version | `version: "1.0"` not `version: 1.0` |
| Unknown field | Field name changed | Check field name mapping |
| Invalid selector | Wrong syntax | Use `if/then` not `# [selector]` |
| Schema error | Missing `schema_version: 1` | Add at top of file |

## Testing Both Formats

During migration, test both formats work:

```bash
# Test legacy
conda-build recipes/my-package-legacy -c conda-forge

# Test modern
rattler-build build -r recipes/my-package/recipe.yaml -c conda-forge

# Compare outputs
diff <(conda-render recipes/my-package-legacy) \
     <(rattler-build build -r recipes/my-package/recipe.yaml --render-only)
```

## Feedstock Migration

### Full Feedstock Conversion

1. **Fork the feedstock**
2. **Create branch**: `git checkout -b migrate-to-v1`
3. **Convert recipe**: Use automated tools + manual review
4. **Update conda-forge.yml**:
   ```yaml
   conda_build_tool: rattler-build
   ```
5. **Rerender**: `conda-smithy rerender`
6. **Test locally**: `python build-locally.py`
7. **Submit PR**

### Partial Migration (Hybrid)

Not recommended. Choose one format per feedstock.

## Migration Discipline

Five points learned the hard way from feedstock v0→v1 migrations. Each one carries an empirical case to show why the discipline is required, not optional.

### 1. `package.name:` MUST match the feedstock identity, not the local folder name

When migrating an existing feedstock, the conda-forge package on the channel is the canonical name. The local-recipes folder often mirrors the upstream GitHub repo (because that's where you first scaffolded the recipe) — those two names can differ:

| Local folder | Upstream GitHub repo | conda-forge feedstock | conda-forge package |
|---|---|---|---|
| `recipes/confluent-kafka-python/` | `confluentinc/confluent-kafka-python` | `python-confluent-kafka-feedstock` | `python-confluent-kafka` |

The v1 `package.name:` MUST match the **package name conda-forge already ships**, not the folder name or the GitHub repo name. Changing it during the migration would:
- Mint a parallel package on conda-forge (e.g. `confluent-kafka-python` *and* `python-confluent-kafka`)
- Orphan existing users on the old name (their `conda install python-confluent-kafka` continues to resolve to the legacy v0 build; the new v1 build only ships under the new name)
- Fail review on staged-recipes / feedstock review because the rename isn't deliberate

**Verify before pushing**:

```bash
# Confirm what conda-forge currently ships
pixi run -e local-recipes lookup_feedstock <expected-conda-name>
```

`exists=True` with the right feedstock URL confirms the canonical name. The hand-written `recipe.yaml` carrying a different `package.name:` is a recipe-audit failure, even if `validate_recipe` and `optimize_recipe` are both clean — neither tool knows the canonical conda-forge name; only the maintainer does.

### 2. Bump `build.number` on same-version v0→v1 swap

When the migration ships against the same upstream version that's currently shipping on conda-forge (no version bump in the same PR), `build.number` MUST increment (typically `0 → 1`).

| Scenario | `build.number` |
|---|---|
| v0→v1 migration, same upstream version | `0 → 1` (increment) |
| v0→v1 migration, bundled with upstream version bump | `0` (reset; version bump provides hash separation) |
| Pure version bump, no format change | reset to `0` |

The reasoning: conda-forge's solver chooses among build variants of the same `<name>-<version>` by build number (higher wins). Existing users on `<pkg>-<version>-*_0` need to be able to upgrade cleanly to the v1-built `<pkg>-<version>-*_1`. Reusing `_0` would either fail the channel upload (immutability — same `<name>-<version>-<build_hash>_<build_num>` already exists) or mint a colliding hash that nobody can sort out.

This isn't documented in any conda-forge schema or tool; reviewers will ask for it on the PR if you forget.

### 3. Stash `meta.yaml` aside during local validation — don't pre-delete

The CRITICAL CONSTRAINT in SKILL.md is "Never Mix Formats in a Build Run" — `meta.yaml` and `recipe.yaml` cannot coexist for an active build. But the Migration Protocol also says "Remove `meta.yaml` only after step 4 succeeds — never before." How do you run steps 2-4 without both files being present and triggering `STD-002`?

The practical pattern:

```bash
# Before running validate / optimize / build:
mv recipes/<name>/meta.yaml recipes/<name>/meta.yaml.bak

# Now optimize_recipe stops emitting STD-002, build sees only recipe.yaml.
pixi run -e local-recipes validate recipes/<name>
pixi run -e local-recipes optimize recipes/<name>
pixi run -e local-recipes recipe-build recipes/<name>

# After the green build, restore meta.yaml in the local mirror as the
# pre-migration reference; only the feedstock fork drops it.
mv recipes/<name>/meta.yaml.bak recipes/<name>/meta.yaml
```

Keep the v0 copy in the local mirror until the feedstock PR merges — it's a useful before/after reference during PR review. When the PR merges and the migration is done, `git rm recipes/<name>/meta.yaml` in the local-recipes repo too.

The fork branch is where `meta.yaml` actually disappears (`git rm recipe/meta.yaml` + commit). Two different deletes: the fork branch deletes it on the migration PR; the local mirror deletes it at PR-merge time.

### 4. `conda_build_tool: rattler-build` MUST ship paired with `conda_install_tool: pixi`

Adding `conda_build_tool: rattler-build` to `conda-forge.yml` is required for CI to use the v1 parser. But the modern 2026 canonical pattern pairs it with `conda_install_tool: pixi`:

```yaml
conda_build:
  pkg_format: '2'
conda_build_tool: rattler-build
conda_install_tool: pixi
conda_forge_output_validation: true
```

`conda_install_tool: pixi` tells the CI to use pixi for environment installs (faster than micromamba and matches conda-forge's 2026 standardization on pixi). Without it, you get the older micromamba-driven CI install path; functional, but slower and a step behind the ecosystem standard.

Both keys land in the **same** PR that drops `meta.yaml` and adds `recipe.yaml`. They're not separate concerns — they're the canonical "this feedstock uses v1 + rattler-build + pixi" declaration.

After pushing the migration commit to the fork branch, **always request rerender** with `@conda-forge-admin, please rerender` on the PR comment thread. The CI scripts (Azure YAML, build-locally helpers, conda-forge-ci-setup invocations) need regenerating to invoke rattler-build instead of conda-build. Without the rerender, CI may still try the conda-build path and produce confusing errors.

### 5. `pip_check: true` on first-time enablement may surface "new" runtime deps

Many older meta.yaml v0 recipes don't have `pip check` in `test:` — it was opt-in for years. CFEP-25's v1 canonical noarch:python test block turns it on by default (`pip_check: true`), and best practice on v1 compiled recipes is to enable it too.

When migrating an old recipe, expect `pip_check` to find runtime deps that upstream's PEP-508 markers introduced post-original-feedstock-creation. The original v0 recipe shipped without them because the v0 test was just `imports:` (no pip-check), so the missing dep was never caught.

**Fix pattern**: add the missing dep to `requirements.run:`. Prefer unconditional listing over PEP-508-marker-gated conda-forge selectors for single transitive deps:

```yaml
# Upstream's requirements.txt:
#   typing-extensions ; python_version < "3.11"
#
# Conda-forge recipe — ship unconditionally instead of gating the marker:
requirements:
  run:
    - python
    - librdkafka >=${{ version }}
    # Upstream requires typing-extensions on Python <3.11. We ship it
    # unconditionally; the runtime overhead on 3.11+ is negligible and
    # the recipe stays simpler than gating the marker into a v1 selector.
    - typing_extensions
```

The trade-off: the v1 selector form (`if: match(python, "<3.11") then: typing_extensions`) is more precise but adds recipe complexity for a tiny pure-Python dep. For single transitive deps, the unconditional pattern is canonical; for many marker-gated deps or large native deps, the selector form pays back its complexity.

**Case**: python-confluent-kafka v0→v1 migration (Jun 14, 2026). Original v0 meta.yaml had `test.imports: [confluent_kafka]` only — no `pip check`. v1 migration added `pip_check: true` per CFEP-25 canonical pattern; local rattler-build immediately failed on `confluent-kafka 2.14.2 requires typing-extensions, which is not installed`. Upstream's `requirements/requirements.txt` had been declaring `typing-extensions ; python_version < "3.11"` since v2.x.x; the v0 recipe had simply never caught it because pip-check was off. Added `typing_extensions` to `run:` unconditionally; subsequent build green across py310/311/312/313.

This is *expected* during v0→v1 migrations of older feedstocks. Plan for it; don't be surprised by it.

## Resources

- [Recipe Format Schema](https://github.com/prefix-dev/recipe-format)
- [rattler-build Migration Docs](https://rattler-build.prefix.dev/latest/converting_from_conda_build/)
- [conda-forge v1 Announcement](https://conda-forge.org/blog/2025/02/27/conda-forge-v1-recipe-support/)
