# abi3 Matrix Collapse Pattern

For Rust+PyO3 (and any C-extension) packages whose Cargo.toml declares `pyo3 abi3-py3XX`, the produced binary is CPython-stable-ABI and works across all CPython ≥ 3.XX on a given platform. Without the collapse pattern below, conda-forge will still build that identical binary once per Python version (4× per platform on the current 3.11/3.12/3.13/3.14 matrix), paying the full Rust + fat-LTO link cost each time. The collapse cuts the build matrix to **one variant per platform**.

This is the canonical pattern shipped by `tree-sitter-typescript-feedstock`, `tree-sitter-cpp-feedstock`, `tree-sitter-go-feedstock`, `tree-sitter-julia-feedstock`, `tree-sitter-objc-feedstock`, `fsspec-rs-feedstock`, `openmeeg-feedstock`, `perspective-feedstock`, `minijinja-feedstock`, `rustworkx-feedstock`, and others. The conda-forge-pinning variant config supplies the `is_abi3: [true]` flag that makes the rule below activate; recipes that don't declare it (i.e., aren't abi3) get standard per-Python builds.

## When to apply

The recipe is a Rust+PyO3 (maturin) or C-extension package AND the upstream declares one of:

```toml
# Cargo.toml
pyo3 = { version = "0.27", features = ["abi3-py311"] }
# or
[features]
default = ["abi3"]
abi3 = ["pyo3/abi3-py311"]
```

Empirically detectable via `_extract_abi3_from_sdist()` (recipe-generator v8.9.0+) which regex-matches all three Cargo.toml abi3 forms.

For C-extension packages (no Rust), the analog is `Py_LIMITED_API` in the C source plus a `cp3XX-abi3-<plat>.whl` filename emitted by the wheel build.

## Two skip-rule variants

### Variant A — `is_abi3 and not is_python_min`

Use when **the upstream's abi3 minimum matches conda-forge-pinning's `python_min` default** (currently `3.10`). Example: `pyo3/abi3-py310`.

```yaml
build:
  number: 0
  skip: is_abi3 and not is_python_min
  python:
    version_independent: ${{ is_abi3 }}
```

Mechanism: conda-forge-pinning zip-keys `python` with `is_python_min` (`[true, false, false, false]`). The skip rule keeps only the `is_python_min=true` row, which aligns with pinning's `python_min: '3.10'`. One variant survives per platform; abi3audit confirms it's a stable-ABI binary; rattler-build emits `version_independent: true` packaging metadata so the single `.conda` installs on any CPython ≥ python_min.

Used by: tree-sitter-typescript, fsspec-rs, openmeeg, perspective, tree-sitter-go, tree-sitter-cpp, tree-sitter-objc, tree-sitter-zig, tree-sitter-c, tree-sitter-elixir, tree-sitter-rust, tree-sitter-ruby, tree-sitter-scala, ast-serialize, reasonable.

### Variant B — `not (match(python, python_min ~ ".*") and is_abi3)`

Use when **the upstream's abi3 minimum is higher than the conda-forge-pinning default** and you need to override `python_min` upward. Example: cocoindex with `pyo3/abi3-py311` while pinning's `python_min: '3.10'`.

```yaml
build:
  number: 0
  skip: not (match(python, python_min ~ ".*") and is_abi3)
  python:
    version_independent: ${{ is_abi3 }}
```

Paired with a recipe-local `conda_build_config.yaml`:

```yaml
# recipe/conda_build_config.yaml
python_min:
  - "3.11"
```

Mechanism: when `python_min` is overridden upward, conda-smithy correctly adopts the new value in the generated `.ci_support/*.yaml` BUT leaves the zip-keyed `python` axis pointing at the pinning's first entry (3.10) — see G21. The Variant A skip rule (`is_python_min`) then kicks in for the py3.10 variant, and the build fails at `pip install` with `requires Python >=3.11`. The Variant B skip rule sidesteps the misalignment by comparing the variant's `python` against the variant's `python_min` directly via `match()` + `~` (jinja string-concat); for non-min variants the match fails and the variant is skipped.

Used by: rustworkx, cocoindex.

**Note** — the `~` in `python_min ~ ".*"` is rattler-build's jinja string-concat (renders `"3.11" + ".*"` → `"3.11.*"`); it is NOT a regex operator. `match()` then does a substring/glob match against the variant `python` value (e.g. `"3.11.* *_cpython"`).

## Required companion: `python.version_independent`

```yaml
build:
  python:
    version_independent: ${{ is_abi3 }}
```

This tells rattler-build to:
- Mark the output as Python-version-independent in `info/index.json` (`"noarch": "python"` with `"platform": "linux"` + `"subdir": "linux-64"` — platform-specific but ABI-portable).
- Add `_python_abi3_support 1.*` as a runtime dependency (conda-forge ships the shim).
- Add `cpython >=${{ python_min }}` to runtime deps so the solver refuses to install on too-low a Python.

The `${{ is_abi3 }}` form is preferred over hard-coded `true` because it cleanly disables the markup if the recipe is ever rebuilt against a pinning that turns off abi3 (e.g., a freethreading variant).

## Required companion: `python-abi3` in host

```yaml
requirements:
  host:
    - python
    - pip
    - maturin >=1,<2
    - if: is_abi3
      then: python-abi3
```

`python-abi3` is a conda-forge convenience package; the `if: is_abi3` gate keeps it scoped to the variant being built.

## Required companion: cross-Python test

```yaml
tests:
  - python:
      imports:
        - mypackage
      pip_check: true
      python_version:
        - if: is_abi3
          then: ${{ python_min }}.*
        - "*"
```

Runs the import test **twice**: once against the build-time Python (= `python_min`), once against the latest. The two-env test empirically validates that the abi3 wheel actually works across Python versions — without this you only prove it works on the version it was built against.

## Required companion: `abi3audit` symbol-level verification

```yaml
tests:
  - if: is_abi3
    then:
      requirements:
        run:
          - abi3audit
      script:
        - if: unix
          then: abi3audit $SP_DIR/mypackage/_internal/core.abi3.so -s -v --assume-minimum-abi3 ${{ python_min }}
          else: abi3audit %SP_DIR%\mypackage\_internal\core.pyd -s -v --assume-minimum-abi3 ${{ python_min }}
```

`abi3audit` scans the compiled binary for any non-stable-ABI symbols. A passing run prints `N extensions scanned; 0 ABI version mismatches and 0 ABI violations found`. This is the only check that catches a Cargo.toml-declares-abi3-but-something-leaks regression — maturin and rattler-build will both happily produce a wheel tagged `abi3` that depends on private CPython symbols. The audit is cheap (sub-second) and runs in the test environment.

**Finding the binary path**: the `_internal/core.abi3.so` segment is package-specific. Inspect the recipe's wheel output (or any successful build's `.conda`) to locate the actual abi3 extension. Common shapes:

| Build backend | Typical path (Unix) | Typical path (Windows) |
|---|---|---|
| maturin (default) | `$SP_DIR/<pkg>/_<libname>.abi3.so` | `%SP_DIR%\<pkg>\_<libname>.pyd` |
| maturin with `module-name` | `$SP_DIR/<pkg>/_internal/core.abi3.so` | `%SP_DIR%\<pkg>\_internal\core.pyd` |
| setuptools-rust | `$SP_DIR/<pkg>/<libname>.abi3.so` | `%SP_DIR%\<pkg>\<libname>.pyd` |
| Py_LIMITED_API (pure C) | `$SP_DIR/<pkg>.abi3.so` | `%SP_DIR%\<pkg>.pyd` |

Windows binaries don't carry the `abi3` filename suffix — the extension is just `.pyd`. The abi3 nature is internal to the binary; `abi3audit` reads the PE header to confirm.

## Empirical results

For cocoindex (v1.0.10; ~600 transitive Rust crates including tree-sitter × ~70 grammars + heed + hyper + tower + rustls + axum):

| Metric | Before (4 variants/platform) | After (1 variant/platform) |
|---|---|---|
| linux_64 CI wall | ~12 min | **~3 min** |
| osx_arm64 CI wall | ~14 min | **~4 min** |
| **win_64 CI wall** | (would have exceeded 6h Azure cap on fat LTO) | **9 min 45 s** |
| `.conda` artifacts shipped | 4 × ~6.7 MiB | 1 × 6.7 MiB |
| `info/index.json` noarch tag | (per-py3X) | `noarch: python` |
| Solver lookup at install time | matches user's exact Python | matches any Python ≥ python_min |

Live reference: https://github.com/conda-forge/cocoindex-feedstock/pull/11 (merged 2026-06-14).

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| `Failed to render recipe with variants: Jinja template error: undefined variable in condition 'is_abi3'` | `.ci_support/*.yaml` files predate the abi3-mode rerender; they don't carry `is_abi3: true` | Comment `@conda-forge-admin, please rerender` on the PR; the regenerated configs include `is_abi3` |
| `pip install` fails with `requires Python >=3.XX` while recipe uses Variant A skip | python_min override > pinning default → smithy mis-aligns is_python_min vs python (G21) | Switch to Variant B (`match(python, python_min ~ ".*") and is_abi3`) |
| Variant A skip leaves zero builds: all variants skipped | Recipe has both `match(python, "<3.XX")` AND `is_abi3 and not is_python_min` AND the explicit version skip > pinning's python_min | Drop the explicit `match(python, "<3.XX")` skip — the abi3 + python_min variant override handles the floor |
| `ValueError: '3.13.* *_cpython' is not in list` during smithy rerender | Recipe-local CBC overrides `python:` axis with wrong suffix syntax for newer pythons (G22) | Drop the `python:` axis override; let smithy use pinning. Override only `python_min:`. |
| Smithy rerender reports `'changed': False` but you expect new `.ci_support` files | Recipe-local CBC override is being unioned (not replacing) by smithy's variant_algebra | Don't override `python:` axis; pick the matching skip-rule variant for your python_min instead |
| `Zip key elements do not all have same length: is_python_min` in local rattler-build | Recipe-local CBC overrides `python` to a 1-entry list but doesn't override the zip-keyed `is_python_min` | Don't override `python:` axis; or override BOTH `python` and `is_python_min` with matching lengths. Variant B sidesteps this entirely. |

## See also

- SKILL.md § Recipe Authoring Gotchas — G21 (smithy zip-key mis-alignment), G22 (CBC `python:` suffix syntax)
- `reference/python-min-policy.md` — when to override `python_min` upward
- `reference/recipe-yaml-reference.md` — `build.python.version_independent` schema
- `guides/feedstock-maintenance.md` — gh OAuth scope needed to merge rerender PRs
- conda-forge-pinning's `conda_build_config.yaml` § `is_abi3` — the variant variable this pattern keys on
