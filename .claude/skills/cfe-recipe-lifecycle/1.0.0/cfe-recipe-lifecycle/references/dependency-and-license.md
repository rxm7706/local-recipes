# Dependency & License Checking

## Contents

- [dependency-checker.py](#dependency-checkerpy)
- [license-checker.py](#license-checkerpy)
- [mapping_manager.py](#mapping-managerpy)

## dependency-checker.py {#dependency-checkerpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/dependency-checker.py` (compiled copy: `scripts/dependency-checker.py`)

**Purpose (module docstring, verbatim first line):** Check if recipe dependencies exist on conda-forge or a configured enterprise mirror.

**CLI wrapper:** dependency-checker wrapper  
**Pixi task:** check-deps  
**MCP tool(s):** check_dependencies

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
class DependencyCheck  # line 149
def normalize_package_name(name: str) -> str  # line 162
def get_skill_config() -> dict  # line 166
def get_configured_channels(override: Optional[str] = ...) -> List[str]  # line 183
def build_package_index(channels: List[str], subdirs: List[str]) -> PackageIndex  # line 572
def batch_check_deps(deps: List[str], index: PackageIndex, suggest: bool) -> Tuple[List[DependencyCheck], List[DependencyCheck]]  # line 604
def extract_package_name(dep_string: str) -> str  # line 639
def extract_dependencies_v1(recipe_path: Path) -> List[str]  # line 645
def extract_dependencies_legacy(recipe_path: Path) -> List[str]  # line 678
def extract_dependencies_basic(recipe_path: Path) -> List[str]  # line 703
def check_recipe(recipe_path: Path, verbose: bool = ..., suggest: bool = ..., channel: Optional[str] = ..., subdirs: Optional[List[str]] = ...) -> Tuple[List[DependencyCheck], List[DependencyCheck]]  # line 722
def main() -> None  # line 775
```

**Internal helpers:** 15 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## license-checker.py {#license-checkerpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/license-checker.py` (compiled copy: `scripts/license-checker.py`)

**Purpose (module docstring, verbatim first line):** Check and validate license information in conda recipes.

**CLI wrapper:** license-checker wrapper  
**Pixi task:** license-check  
**MCP tool(s):** — (no dedicated MCP tool)

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def is_valid_spdx(license_id: str) -> bool  # line 142
def suggest_spdx(license_str: str) -> Optional[str]  # line 153
def extract_license_info(recipe_path: Path) -> tuple[Optional[str], Optional[str]]  # line 169
def check_license_file_exists(source_dir: Path, license_file: str) -> bool  # line 212
def find_license_files(source_dir: Path) -> list[str]  # line 231
def main()  # line 252
```

## mapping_manager.py {#mapping-managerpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/mapping_manager.py` (compiled copy: `scripts/mapping_manager.py`)

**Purpose (module docstring, verbatim first line):** PyPI-to-Conda Name Mapping Manager.

**CLI wrapper:** mapping_manager wrapper  
**Pixi task:** update-mapping-cache  
**MCP tool(s):** update_mapping_cache

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def fetch_mapping_via_curl() -> dict  # line 105
def fetch_conda_forge_metadata_mapping() -> dict  # line 157
def load_local_cache() -> dict  # line 184
def save_to_local_cache(mapping: dict)  # line 191
def update_mapping_cache(force: bool = ...)  # line 203
def main()  # line 234
```

**Internal helpers:** 3 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

