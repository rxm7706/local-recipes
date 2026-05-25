# conda-forge-expert v8.9.0 — maturin/PyO3 generator path + template hardening

**Status:** intake-ready (not yet implemented).
**Bump:** MINOR (v8.8.0 → v8.9.0). Additive: new generator code path + template improvements. No breaking change.
**Driver:** `recipes/py-yaml12` recipe build (2026-05-25). Running `recipe-generator.py pypi py-yaml12` produced a noarch:python recipe for what is actually a Rust+PyO3 package — the generator silently misrouted to the wrong template. Hand-customization based on `template python-maturin` produced a clean recipe, but the workflow shouldn't require that step.
**Parent retro:** `_bmad-output/projects/local-recipes/implementation-artifacts/retro-conda-forge-expert-v8.7-v8.8-2026-05-25.md` (gap surfaced during py-yaml12 build).

**Empirical anchor:** Validated against an expanded sample (2026-05-25 second pass):
- **52 Rust label PRs total** (25 v8.7.0 CLI + 27 new — Mar–May 2026): `cargo auditable install` 39/42 = 93% of CLI subset; `--no-track` 22/25 = 88%; `cargo-bundle-licenses` 25/25 = 100%; `stdlib("c")` 24/25 = 96%; **`CARGO_HOME` workaround 0/25 = 0%** (definitively NOT canonical for CLI Rust).
- **27 PyO3/maturin PRs** (Mar 2020 – May 2026): `maturin` in host 18/27 = 67%; `compiler("rust")` 23/27 = 85%; `stdlib("c")` 18/27 = 67%; `cargo-bundle-licenses` 21/27 = 78%; **`cargo auditable` only 2/27 = 7%** (NOT canonical for PyO3 — older recipes pre-date the convention; newer ones still don't bother). **CARGO_HOME workaround 1/27 = 4%** (only ast-serialize, with a package-specific justification). **`version_independent` 2/27 = 7%** (only when paired with `is_abi3` variant). **CFEP-25 dual-version test matrix 1/27 = 4%** (rare in PyO3 — this is a pure-python convention, not a compiled-extension one).
- **30 pure-python PRs** (Apr–May 2026): patterns from v8.8.0 unchanged.
- **5 docs sources read:** [`conda-forge.org/.../rust`](https://conda-forge.org/docs/maintainer/example_recipes/rust/), [`.../pure-python`](https://conda-forge.org/docs/maintainer/example_recipes/pure-python/), [`conda-forge.org/.../knowledge_base`](https://conda-forge.org/docs/maintainer/knowledge_base/), [`rattler-build.../tutorials/python`](https://rattler-build.prefix.dev/latest/tutorials/python/), [`rattler-build.../tutorials/rust`](https://rattler-build.prefix.dev/latest/tutorials/rust/).
- **knowledge_base highlights** (new in this pass): `noarch: python` rules (no compiled extensions, no OS-specific scripts, no version-specific reqs); virtual packages `__unix`/`__win`/`__linux`/`__osx` for OS-conditional run deps under `noarch: python`; `run_constrained` for "installs everywhere but only constrained at runtime"; only `console_scripts` entry_points need recipe attention; "python in host creates a matrix per supported version" (key for compiled-vs-noarch routing).

## Goal

When a PyPI package builds Rust extensions via maturin/PyO3, the generator should emit a compiled-recipe shape (no `noarch: python`, Rust toolchain in build deps, maturin in host, the CFEP-25 test matrix wired correctly) without manual intervention.

Secondary: harden the `python-maturin` template with patterns that 17/17 of the recent merged PyO3 PRs need but the template doesn't pre-include.

## Acceptance criteria

1. `recipe-generator.py pypi <name>` on a maturin/PyO3 package produces a recipe that:
   - omits `noarch: python`
   - includes `${{ compiler("c") }} ${{ stdlib("c") }} ${{ compiler("rust") }} cargo-bundle-licenses` in `requirements.build`
   - includes `maturin >=1.X,<2.0` in `requirements.host` (not `setuptools`)
   - includes `cargo-bundle-licenses --format yaml --output THIRDPARTY.yml` as the first script line
   - lists `LICENSE` + `THIRDPARTY.yml` in `about.license_file`
   - emits the correct import name (read from sdist's `Cargo.toml [lib] name` and/or PyO3 `#[pymodule]` declaration), not the naïve `<dist-name>.replace("-", "_")`
   - includes the conditional Windows `CARGO_HOME=C:\.cargo` + idempotent `if not exist md` block
   - passes `optimize_recipe` with 0 suggestions
2. `recipe-generator.py pypi <name>` on a pure-Python package continues to emit the existing noarch:python shape (no regression).
3. `templates/python/maturin-recipe.yaml` is updated to be a complete drop-in starting point — even hand-instantiation via `template python-maturin` should produce a near-clean recipe (only metadata placeholders need replacement).
4. All 1168+ skill tests still pass; new tests cover the maturin detection + import-name extraction paths.

## Gaps (the four findings)

### G1 — `noarch: python` is hardcoded in `generate_recipe_yaml`

**Where:** `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:273` — `build: noarch: python` is literal in the f-string template.

**Why it's wrong:** PyO3/maturin packages produce platform-specific compiled extensions. `noarch: python` causes the package to be marked as architecture-independent, which breaks the actual build (no `cdylib` shipped) and breaks conda-forge CI matrix expansion.

**Fix:** Detect maturin from `pyproject.toml [build-system].requires` (fetched from sdist or from PyPI's `info` payload), route to a separate emit path that:
- skips `noarch: python`
- adds Rust toolchain to `requirements.build`
- adds maturin to `requirements.host`

The existing `templates/python/maturin-recipe.yaml` is the right shape; the generator can either (a) read the template file and substitute, or (b) keep f-string emission but in a separate `generate_maturin_recipe_yaml` function. Option (a) is simpler and matches the `template` subcommand machinery.

### G2 — `determine_build_backend()` misses maturin

**Where:** `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:96-115` — checks `requires_dist` for backend names.

**Why it's wrong:** Maturin is a **build-system** dependency, not a runtime dependency. PyPI's `info["requires_dist"]` lists only runtime/optional deps. Maturin lives in `pyproject.toml [build-system].requires` which PyPI exposes via the sdist contents or via project_urls/classifiers — not via the JSON metadata's `requires_dist`. The function returns `setuptools` (default) for every maturin package.

**Fix:** Extend `determine_build_backend()` to also inspect:
- the sdist's `pyproject.toml` `[build-system].requires` (preferred — authoritative)
- failing that, look for the `Programming Language :: Rust` classifier in `info["classifiers"]` as a strong hint that the package builds Rust extensions
- failing that, check if any wheel in `info["releases"]` has `cp3XX-cp3XX-<platform>` tags (platform-specific wheel = compiled package)

### G3 — `templates/python/maturin-recipe.yaml` missing canonical patterns

**Where:** `.claude/skills/conda-forge-expert/templates/python/maturin-recipe.yaml`.

**Missing patterns** (each appeared in 17/17 sampled merged Rust+PyO3 PRs):

a. **CFEP-25 dual-version test matrix** — template's `tests` section uses:
   ```yaml
   - python:
       imports: [...]
       pip_check: true
   ```
   Should be:
   ```yaml
   - python:
       imports: [...]
       pip_check: true
       python_version:
         - ${{ python_min }}.*
         - "*"
   ```
   The optimizer's `TEST-002` will fire on any recipe instantiated from this template until it's added.

b. **~~Windows `CARGO_HOME` long-path workaround~~ — DROPPED from this spec.** Initial draft proposed including the `set CARGO_HOME=C:\.cargo` + `if not exist md` block in the template. Empirical reality (verified against the v8.7.0 17/17 CLI Rust PR sample + this session's py-yaml12 build): the workaround is **not** canonical conda-forge style. The original comment in xorq-datafusion/recipe.yaml cited `pixi/issues/3691` which is closed-as-not-planned and is actually about publishing the `pixi_config` *crate*, not a generic path-too-long workaround. The hack is relevant only for packages whose Cargo dependency graph pulls pixi-related crates with deeply nested paths (xorq pulls these for its pixi integration; py-yaml12, ruff, etc. do not). The maturin template should **not** include this block by default. Document in SKILL.md as a per-package conditional pattern instead — only add when the cargo graph actually triggers the issue.

c. **`build.python.version_independent`** — **gated on upstream Cargo.toml abi3 feature**, not unconditional. Empirical 27-PR PyO3 sample: only 2/27 (7%) use it; both pair with `is_abi3` variant. The generator should:
   - Read the sdist's `Cargo.toml` `[features]` block when routing to the maturin path.
   - If `pyo3 = { features = ["abi3-py3XX"] }` or `default = ["abi3"]` + `abi3 = ["pyo3/abi3-py3XX"]` is present → emit `version_independent: true` (unconditional form, simpler for staged-recipes; the conditional `${{ is_abi3 }}` form is feedstock-level optimization).
   - Otherwise → omit. The package builds one wheel per Python version, no abi3 declaration needed.
   - Verified examples: py-yaml12 has `default = ["abi3"]` + `abi3 = ["pyo3/abi3-py310"]` → emit. phonors has `pyo3 = "*"` without abi3 feature → omit. cachebox has no abi3 → omit. ast-serialize has abi3 feature → emit conditional form.
   - Skill-internal G entry for this rule lives in SKILL.md "Recipe Authoring Gotchas" once landed.

d. **Source URL underscore-form filename** — many sdists publish as `<name_with_underscores>-<version>.tar.gz` even though the PyPI distribution name uses hyphens. Currently template uses:
   ```yaml
   url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
   ```
   Should add a comment near the URL line noting the underscore-rewrite pattern for sdists where the upstream uses it (`py-yaml12` → `py_yaml12-0.1.0.tar.gz`).

### G4 — Generator doesn't extract import name from sdist

**Where:** `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:319` (v1) — `{info.name.replace("-", "_").lower()}` is the hardcoded heuristic.

**Why it's wrong:** This is **G7** from SKILL.md ("Grayskull's inferred Python import name can be wrong — verify against the sdist"). For PyO3 packages the import name is determined by the `#[pymodule]` declaration in `src/lib.rs` and the `[lib] name` in `Cargo.toml`, which is frequently different from the PyPI distribution name. Examples in the wild:
- `py-yaml12` distribution → `yaml12` import
- `microsoft-kiota-bundle` → `kiota_bundle` (re-exported short name)
- `azure-identity-broker` → `azure.identity.broker` (dotted namespace)

**Fix:** Add a helper that downloads the sdist + extracts the import name:
1. For Rust+PyO3 packages: read `Cargo.toml` `[lib] name = "<X>"` and verify against `src/lib.rs` `#[pymodule] pub fn <X>(...)`.
2. For pure-Python packages: read the top-level `__init__.py` path (`grep '__init__.py$'` in the tar listing) and take the first significant segment.
3. Cache the sdist for the duration of the generator run to avoid double-fetching.

The PyPI JSON API doesn't expose the import name. Sdist inspection is the only reliable source.

## Wave breakdown

### Wave A — Generator backend detection + maturin routing (G1 + G2)

**Stories:**
- S1: Extend `determine_build_backend()` to inspect the sdist's `pyproject.toml [build-system].requires` (download the sdist once, cache for the run); fall back to classifier hint + wheel-tag heuristic.
- S2: Add a `generate_maturin_recipe_yaml()` function that reads `templates/python/maturin-recipe.yaml`, substitutes `name`/`version`/`source_url`/`sha256`/`license`/`homepage`/`repository`/`documentation`/`description`/`imports` from PackageInfo, and writes to `recipe.yaml`.
- S3: Route `generate_recipe_yaml()` to either the noarch path or the maturin path based on `info.build_backend == "maturin"`.
- S4: Same routing in `generate_meta_yaml()` for v0/legacy.
- S5: Unit tests: synthetic maturin package fixture (mock sdist with maturin `[build-system].requires`) → assert recipe.yaml has Rust toolchain, no noarch, maturin in host.

**Verification:** `recipe-generator.py pypi py-yaml12` produces a recipe that passes `optimize_recipe` with 0 suggestions; `recipe-generator.py pypi rich` continues to emit the noarch shape.

### Wave B — Template hardening (G3) — REVISED per ~52-PR sample

**Empirical reality** (27 PyO3 PRs): the maturin template should be **minimal**. The patterns we considered including (CFEP-25 test matrix, Windows CARGO_HOME, version_independent, LTO/strip) are NOT canonical for PyO3 — they show up only in single-digit-percent of PyO3 PRs. The modal PyO3 recipe is much closer to **phonors** (a 2-line script: `cargo-bundle-licenses` + `pip install`) than to the CLI Rust pattern.

**Stories:**
- S6: **DROP** the CFEP-25 dual-version test matrix from the maturin template default. Only 1/27 PyO3 PRs use it. Add as a commented-out option for the package author who wants per-version test coverage, with explanation "the CFEP-25 matrix is a pure-python convention; for compiled PyO3 packages the per-Python-version build matrix already exercises each version".
- S7: **DROP** the Windows `CARGO_HOME` proposal entirely. 0/25 new CLI Rust PRs use it; only 1/27 PyO3 PRs (ast-serialize) used a *different* `c:\.cg` short path for a *package-specific* git-checkout depth failure. The xorq-style block in the current py-yaml12 recipe is misattributed to pixi#3691 (which is closed-as-not-planned about an unrelated topic). Per-package conditional pattern only — add as an SKILL.md "Recipe Authoring Gotchas" entry (new G10) explaining when to use it ("only when the cargo dep graph includes git deps with deeply nested checkouts that trigger Windows 260-char path limit; verify the failure mode before adding").
- S8: **Add `version_independent` as a commented annotation, NOT default.** Only 2/27 PyO3 PRs use it. When upstream Cargo.toml declares `pyo3 = { features = ["abi3-py3XX"] }` or has an `abi3` feature, the template should suggest the abi3-aware shape:
  ```yaml
  build:
    # Uncomment when upstream Cargo.toml declares pyo3 abi3 feature.
    # The is_abi3 variant must be supported by the feedstock's CBC; for
    # staged-recipes submission, leave it as unconditional true if the
    # package builds against abi3-py3XX:
    # skip: is_abi3 and not is_python_min
    # python:
    #   version_independent: ${{ is_abi3 }}
  ```
- S9: Update `templates/python/maturin-recipe.yaml` source URL with a comment about the underscore-form sdist filename pattern (e.g., `py-yaml12` → `py_yaml12-<ver>.tar.gz`). PEP 625 normalisation means most modern sdists use underscore form; older ones use the hyphen.
- S10: **Drop `script.env` + `script.content` + LTO/strip from the maturin template.** Only 3/27 PyO3 PRs use `CARGO_PROFILE_RELEASE_LTO` — this is a CLI Rust optimization (binary-size reduction). PyO3 extensions don't benefit meaningfully since the .so/.pyd is small relative to the Python package. The 2-line script (`cargo-bundle-licenses` + `pip install`) is the modal pattern.
- S11: Add a meta-test similar to `test_recipe_yaml_schema_header.py` that asserts the maturin template includes the essentials: schema header, `cargo-bundle-licenses` first, Rust toolchain in build, maturin in host, `THIRDPARTY.yml` in license_file. Do NOT assert CFEP-25 or Windows block (those are conditional).

**Verification:** `template python-maturin --name foo --version 0.1.0` produces a minimal recipe matching the **phonors** pattern (the modal 27/27 PyO3 PR shape). Passes optimizer with 0 suggestions on a real package after metadata replacement.

### Wave C — Import-name extraction (G4)

**Stories:**
- S11: Add `_extract_import_name_from_sdist(sdist_path: Path) -> str` helper. For Rust+PyO3 sdists: parse `Cargo.toml` `[lib] name`. For pure-Python: parse first top-level `__init__.py` path. Return empty string when ambiguous (let the caller fall back to the existing heuristic).
- S12: Wire into `fetch_pypi_info()` to populate a new `PackageInfo.import_name` field; default to the existing heuristic when extraction fails.
- S13: Use `info.import_name` in both `generate_recipe_yaml` and `generate_meta_yaml` instead of the inline `.replace("-", "_")` heuristic.
- S14: Unit tests against fixtures for: PyO3 package (yaml12), namespace package (azure.identity.broker dotted-import shape), pure-Python (rich), unknown shape (fall back to heuristic).

**Verification:** `recipe-generator.py pypi py-yaml12` emits `imports: - yaml12` (not `py_yaml12`); `pypi microsoft-kiota-bundle` emits `imports: - kiota_bundle`; pure-Python packages unaffected.

### Wave D — Knowledge-base patterns + virtual-package selectors (new in this revision)

The conda-forge knowledge_base surfaces patterns the existing generator + templates don't currently handle. Adding them lifts the generator from "produces a builds-clean recipe" to "produces a builds-clean recipe that's idiomatic conda-forge".

**Stories:**
- S15: **`noarch: python` decision validator** — add a generator helper `_can_noarch_python(info)` that returns False if any of these are true (per knowledge_base rules):
  - Has compiled extensions (detected via maturin/scikit-build-core/meson-python backend, or `Programming Language :: Rust`/`C++`/`C` classifier with platform-specific wheels in PyPI releases).
  - Declares OS-specific dependencies in `requires_dist` (`; sys_platform == 'win32'`, etc.) — those need `__win`/`__unix` virtual-package selectors.
  - Has post-link/pre-link/pre-unlink scripts (heuristic: look for `post-install` hooks in `pyproject.toml`).
  - Lists pre-3.0 Python in requires_python.
  The validator is *advisory* — emits a warning when a noarch recipe is generated for a package that probably shouldn't be noarch.

- S16: **Virtual-package selectors for OS-conditional run deps** — when a PyPI dependency has a `sys_platform` marker (e.g., `colorama ; sys_platform == 'win32'`), the noarch-python generator should emit:
  ```yaml
  run:
    - if: win
      then:
        - colorama
    - __win  # virtual package; ensures variant hash differs per platform
  ```
  (Per knowledge_base: "Do not forget to specify the platform virtual packages with their selectors! Otherwise, the solver will not be able to choose the variants correctly.")

- S17: **`run_constrained` for "installs everywhere but only constrained at runtime" deps** — generator currently doesn't emit `run_constrained` at all. Document the rule + add a comment in the noarch template suggesting it for packages whose deps are optional/conditional.

- S18: **Entry-points handling** — generator currently doesn't extract `[project.scripts]` from pyproject.toml. Per knowledge_base: "Only console_scripts entry points have to be listed in meta.yaml". Add `_extract_entry_points()` helper that reads sdist's pyproject.toml `[project.scripts]` and emits:
  ```yaml
  build:
    python:
      entry_points:
        - mycli = mypackage.cli:main
  ```
  Required for CLI Python packages (avoids the package shipping but not creating the bin shim).

- S19: **Sample-anchored doc note** — when the generator routes to the maturin path, emit a header comment in the generated recipe.yaml citing the PR sample (`# Generated 2026-05-25 from python-maturin template; pattern validated against 27 PyO3 PRs (Mar 2020 - May 2026)`). Helps reviewers + future agents understand the lineage.

### Wave E — Closeout

**Stories:**
- S20: Update SKILL.md "Recipe Authoring Gotchas" — G7 entry now references the v8.9.0 generator extraction as the canonical fix. Add **G10** "Windows CARGO_HOME long-path workaround is package-specific, not canonical" with the 0/25 + 1/27 sample evidence and the ast-serialize precedent for *when* to add it.
- S21: CHANGELOG.md v8.9.0 entry covering G1–G4 + the Wave D knowledge_base additions, with verification examples for py-yaml12 (maturin route) + rich (noarch route) + a hypothetical Windows-conditional package (virtual-package selector route).
- S22: Bump `config/skill-config.yaml` to 8.9.0.
- S23: Retro lands in `_bmad-output/projects/local-recipes/implementation-artifacts/retro-conda-forge-expert-v8.9-YYYY-MM-DD.md`. Per Rule 2, retro inspects whether the sample sizes (~52 Rust + 27 PyO3 + 30 pure-python) held up in practice; refreshes the quarterly audit's sample list.

## Risks / non-goals

- **Non-goal**: extending support to `meson-python` / `scikit-build-core` compiled paths in this spec. Those need their own routing logic (different toolchain pinning, different host deps); file a v8.10+ spec when needed.
- **Risk**: sdist download adds network latency to the generator's PyPI path. Mitigate by caching the sdist tarball under `/tmp/cfe-sdist-cache/<name>-<version>.tar.gz` for the lifetime of the run; clear on exit.
- **Risk**: some maturin packages are pure-Python wrappers around a Rust binary (e.g. `ruff`) — they DO need `noarch: python` despite having maturin in build deps. **Disambiguation**: only route to compiled path when both maturin in build-system AND a `src/lib.rs` with `#[pymodule]` is present in the sdist. Pure-binary wrappers don't have a `#[pymodule]` declaration.

## Empirical anchor (sampled merged PRs, Apr–May 2026)

PyO3/maturin packages where the generator would currently produce a broken recipe:
- `cachebox` (#33349) — pure PyO3, would emit `noarch: python` instead of compiled.
- `cocoindex` (#33231) — PyO3 + extra C sources.
- `phonors` (#33286) — maturin + numpy.
- `burner-redis` (#33024) — pyo3 + redis bindings.
- `microsoft-kiota-bundle` (#33355) — re-export naming pattern (G4 trap).
- `py-yaml12` (this session) — PyO3 only.

All five of these required hand-customization on top of the generator output. After v8.9.0, all five should generate cleanly.

## Sign-off

This spec is **intake-ready** — open questions resolved, scope bounded, acceptance criteria measurable. Run via `bmad-quick-dev` when the next conda-forge session has bandwidth for a multi-wave generator change.
