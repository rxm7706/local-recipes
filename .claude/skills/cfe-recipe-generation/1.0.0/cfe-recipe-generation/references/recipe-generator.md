# Full API Reference — recipe-generator.py

## Contents

- [`_pypi_to_conda_name`](#-pypi-to-conda-name) (internal)
- [`PackageInfo`](#packageinfo) (public)
- [`_parse_requires_dist_specs`](#-parse-requires-dist-specs) (internal)
- [`determine_build_backend`](#determine-build-backend) (public)
- [`_resolve_python_min`](#-resolve-python-min) (internal)
- [`_sdist_cache_path`](#-sdist-cache-path) (internal)
- [`_ensure_sdist_cached`](#-ensure-sdist-cached) (internal)
- [`_read_sdist_files`](#-read-sdist-files) (internal)
- [`_extract_import_name_from_sdist`](#-extract-import-name-from-sdist) (internal)
- [`_extract_abi3_from_sdist`](#-extract-abi3-from-sdist) (internal)
- [`_extract_build_system_requires_from_sdist`](#-extract-build-system-requires-from-sdist) (internal)
- [`_extract_entry_points_from_sdist`](#-extract-entry-points-from-sdist) (internal)
- [`_build_source_url_template`](#-build-source-url-template) (internal)
- [`_is_maturin_pyo3`](#-is-maturin-pyo3) (internal)
- [`_can_noarch_python`](#-can-noarch-python) (internal)
- [`_classify_sys_platform_deps`](#-classify-sys-platform-deps) (internal)
- [`_extract_project_urls`](#-extract-project-urls) (internal)
- [`_resolve_license`](#-resolve-license) (internal)
- [`_sdist_ships_python_code`](#-sdist-ships-python-code) (internal)
- [`_github_tag_source`](#-github-tag-source) (internal)
- [`fetch_pypi_info`](#fetch-pypi-info) (public)
- [`_skill_version`](#-skill-version) (internal)
- [`_render_cfe_block`](#-render-cfe-block) (internal)
- [`generate_recipe_yaml`](#generate-recipe-yaml) (public)
- [`_generate_maturin_recipe_yaml`](#-generate-maturin-recipe-yaml) (internal)
- [`generate_meta_yaml`](#generate-meta-yaml) (public)
- [`copy_template`](#copy-template) (public)
- [`NpmPackageInfo`](#npmpackageinfo) (public)
- [`_normalize_repo_url`](#-normalize-repo-url) (internal)
- [`_strip_url_fragment`](#-strip-url-fragment) (internal)
- [`_check_spdx_license`](#-check-spdx-license) (internal)
- [`_extract_readme_paragraph`](#-extract-readme-paragraph) (internal)
- [`_parse_node_major`](#-parse-node-major) (internal)
- [`_detect_license_filename`](#-detect-license-filename) (internal)
- [`_fetch_tarball_bytes`](#-fetch-tarball-bytes) (internal)
- [`_hash_tarball`](#-hash-tarball) (internal)
- [`_hash_and_inspect_tarball`](#-hash-and-inspect-tarball) (internal)
- [`_parse_npm_name`](#-parse-npm-name) (internal)
- [`_npm_tarball_filename`](#-npm-tarball-filename) (internal)
- [`_template_npm_source_url`](#-template-npm-source-url) (internal)
- [`fetch_npm_info`](#fetch-npm-info) (public)
- [`_inline_build_script`](#-inline-build-script) (internal)
- [`_tests_block`](#-tests-block) (internal)
- [`generate_npm_recipe_yaml`](#generate-npm-recipe-yaml) (public)
- [`_run_preflight_validation`](#-run-preflight-validation) (internal)
- [`_run_rattler_generate`](#-run-rattler-generate) (internal)
- [`_ensure_yaml_language_server_header`](#-ensure-yaml-language-server-header) (internal)
- [`main`](#main) (public)

48 exports from `recipe-generator.py` (10 public, 38 internal). All T1-low confidence (Quick tier — source reading, no AST tool).

### _pypi_to_conda_name

```python
def _pypi_to_conda_name(pypi_name: str) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L47`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L47]
- Confidence: T1-low

### PackageInfo

```python
class PackageInfo:
```

- Type: class (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L82`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L82]
- Confidence: T1-low

### _parse_requires_dist_specs

```python
def _parse_requires_dist_specs(requires_dist: list[str]) -> list[str]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L118`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L118]
- Confidence: T1-low

### determine_build_backend

```python
def determine_build_backend(requires_dist: list[str]) -> str:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L191`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L191]
- Confidence: T1-low

### _resolve_python_min

```python
def _resolve_python_min(python_requires: str) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L220`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L220]
- Confidence: T1-low

### _sdist_cache_path

```python
def _sdist_cache_path(name: str, version: str) -> Path:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L248`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L248]
- Confidence: T1-low

### _ensure_sdist_cached

```python
def _ensure_sdist_cached(source_url: str, name: str, version: str) -> Path | None:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L255`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L255]
- Confidence: T1-low

### _read_sdist_files

```python
def _read_sdist_files(sdist_path: Path, suffixes: tuple[str, ...]) -> dict[str, str]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L285`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L285]
- Confidence: T1-low

### _extract_import_name_from_sdist

```python
def _extract_import_name_from_sdist(sdist_path: Path, distribution_name: str) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L338`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L338]
- Confidence: T1-low

### _extract_abi3_from_sdist

```python
def _extract_abi3_from_sdist(sdist_path: Path) -> bool:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L396`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L396]
- Confidence: T1-low

### _extract_build_system_requires_from_sdist

```python
def _extract_build_system_requires_from_sdist(sdist_path: Path) -> list[str]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L411`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L411]
- Confidence: T1-low

### _extract_entry_points_from_sdist

```python
def _extract_entry_points_from_sdist(sdist_path: Path) -> list[str]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L429`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L429]
- Confidence: T1-low

### _build_source_url_template

```python
def _build_source_url_template(name: str, version: str, sdist_filename: str) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L454`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L454]
- Confidence: T1-low

### _is_maturin_pyo3

```python
def _is_maturin_pyo3(info: dict, sdist_path: Path | None) -> bool:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L488`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L488]
- Confidence: T1-low

### _can_noarch_python

```python
def _can_noarch_python(info: dict, build_backend: str, sdist_path: Path | None) -> tuple[bool, list[str]]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L505`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L505]
- Confidence: T1-low

### _classify_sys_platform_deps

```python
def _classify_sys_platform_deps(requires_dist: list[str]) -> dict[str, list[str]]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L533`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L533]
- Confidence: T1-low

### _extract_project_urls

```python
def _extract_project_urls(info: dict) -> tuple[str, str, str]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L578`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L578]
- Confidence: T1-low

### _resolve_license

```python
def _resolve_license(info: dict, repository: str = "") -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L638`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L638]
- Confidence: T1-low

### _sdist_ships_python_code

```python
def _sdist_ships_python_code(sdist_path: Path) -> bool:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L674`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L674]
- Confidence: T1-low

### _github_tag_source

```python
def _github_tag_source(repo_url: str, version: str):
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L684`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L684]
- Confidence: T1-low

### fetch_pypi_info

```python
def fetch_pypi_info(package_name: str, version: Optional[str] = None) -> PackageInfo:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L714`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L714]
- Confidence: T1-low

### _skill_version

```python
def _skill_version() -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L931`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L931]
- Confidence: T1-low

### _render_cfe_block

```python
def _render_cfe_block(info: "PackageInfo", conda_name: str, noarch_kind: str) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L941`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L941]
- Confidence: T1-low

### generate_recipe_yaml

```python
def generate_recipe_yaml(info: PackageInfo, output_dir: Path) -> Path:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L995`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L995]
- Confidence: T1-low

### _generate_maturin_recipe_yaml

```python
def _generate_maturin_recipe_yaml(info: PackageInfo, output_dir: Path) -> Path:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1129`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1129]
- Confidence: T1-low

### generate_meta_yaml

```python
def generate_meta_yaml(info: PackageInfo, output_dir: Path) -> Path:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1279`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1279]
- Confidence: T1-low

### copy_template

```python
def copy_template(template_name: str, output_dir: Path, **replacements) -> Path:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1372`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1372]
- Confidence: T1-low

### NpmPackageInfo

```python
class NpmPackageInfo:
```

- Type: class (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1408`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1408]
- Confidence: T1-low

### _normalize_repo_url

```python
def _normalize_repo_url(repo_field) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1446`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1446]
- Confidence: T1-low

### _strip_url_fragment

```python
def _strip_url_fragment(url: str) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1465`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1465]
- Confidence: T1-low

### _check_spdx_license

```python
def _check_spdx_license(license_str: str) -> tuple[str, str | None]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1513`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1513]
- Confidence: T1-low

### _extract_readme_paragraph

```python
def _extract_readme_paragraph(raw_readme: str, *, max_length: int = 700) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1559`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1559]
- Confidence: T1-low

### _parse_node_major

```python
def _parse_node_major(engine_constraint: str) -> int:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1595`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1595]
- Confidence: T1-low

### _detect_license_filename

```python
def _detect_license_filename(tar_bytes: bytes) -> str | None:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1623`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1623]
- Confidence: T1-low

### _fetch_tarball_bytes

```python
def _fetch_tarball_bytes(url: str) -> bytes:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1668`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1668]
- Confidence: T1-low

### _hash_tarball

```python
def _hash_tarball(url: str) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1682`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1682]
- Confidence: T1-low

### _hash_and_inspect_tarball

```python
def _hash_and_inspect_tarball(url: str) -> tuple[str, str | None]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1694`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1694]
- Confidence: T1-low

### _parse_npm_name

```python
def _parse_npm_name(raw: str) -> tuple[str, str, bool]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1709`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1709]
- Confidence: T1-low

### _npm_tarball_filename

```python
def _npm_tarball_filename(raw_name: str, version: str) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1721`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1721]
- Confidence: T1-low

### _template_npm_source_url

```python
def _template_npm_source_url(url: str, version: str) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1733`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1733]
- Confidence: T1-low

### fetch_npm_info

```python
def fetch_npm_info(package_name: str, version: Optional[str] = None, *, source: str = "npm") -> NpmPackageInfo:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1755`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1755]
- Confidence: T1-low

### _inline_build_script

```python
def _inline_build_script(info: NpmPackageInfo, *, prepare_fix: bool, third_party_licenses: bool = True) -> list[str]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1931`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L1931]
- Confidence: T1-low

### _tests_block

```python
def _tests_block(info: NpmPackageInfo, *, mode: str) -> list[str]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2019`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2019]
- Confidence: T1-low

### generate_npm_recipe_yaml

```python
def generate_npm_recipe_yaml(info: NpmPackageInfo, output_dir: Path, *, prepare_fix: bool = False, test_mode: str = "script", third_party_licenses: bool = True, feedstock_mode: bool = False) -> Path:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2040`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2040]
- Confidence: T1-low

### _run_preflight_validation

```python
def _run_preflight_validation(recipe_dir: Path) -> None:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2220`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2220]
- Confidence: T1-low

### _run_rattler_generate

```python
def _run_rattler_generate(ecosystem: str, args: list[str], output_dir: Path) -> Path:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2259`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2259]
- Confidence: T1-low

### _ensure_yaml_language_server_header

```python
def _ensure_yaml_language_server_header(recipe_path: Path) -> None:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2319`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2319]
- Confidence: T1-low

### main

```python
def main():
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2332`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/recipe-generator.py:L2332]
- Confidence: T1-low

