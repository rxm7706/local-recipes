# Autotick / Version Update

## Contents

- [recipe_updater.py](#recipe-updaterpy)
- [npm_updater.py](#npm-updaterpy)
- [github_version_checker.py](#github-version-checkerpy)

## recipe_updater.py {#recipe-updaterpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/recipe_updater.py` (compiled copy: `scripts/recipe_updater.py`)

**Purpose (module docstring, verbatim first line):** Automated Recipe Updater ("Autotick" Bot).

**CLI wrapper:** recipe_updater wrapper  
**Pixi task:** autotick  
**MCP tool(s):** update_recipe

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def get_latest_pypi_version(package_name: str) -> str | None  # line 45
def get_current_recipe_info(recipe_path: Path) -> Dict[str, Any]  # line 77
def update_recipe(recipe_path: Path, dry_run: bool = ...) -> Dict[str, Any]  # line 95
def main()  # line 158
```

## npm_updater.py {#npm-updaterpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/npm_updater.py` (compiled copy: `scripts/npm_updater.py`)

**Purpose (module docstring, verbatim first line):** npm Registry Autotick Bot.

**CLI wrapper:** npm_updater wrapper  
**Pixi task:** autotick-npm  
**MCP tool(s):** — (no dedicated MCP tool; CLI-only, see slice-map.md boundary note)

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def get_latest_npm_version(package_name: str, allow_prerelease: bool = ...) -> dict[str, Any]  # line 197
def update_recipe(recipe_path: Path, npm_package: str | None = ..., dry_run: bool = ..., allow_prerelease: bool = ...) -> dict[str, Any]  # line 245
def update_all_recipes(root: Path, dry_run: bool = ..., allow_prerelease: bool = ...) -> dict[str, Any]  # line 379
def main() -> None  # line 444
```

**Internal helpers:** 7 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## github_version_checker.py {#github-version-checkerpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/github_version_checker.py` (compiled copy: `scripts/github_version_checker.py`)

**Purpose (module docstring, verbatim first line):** GitHub release version checker for conda-forge recipes.

**CLI wrapper:** github_version_checker wrapper  
**Pixi task:** version-check  
**MCP tool(s):** check_github_version

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def get_latest_github_release(owner: str, repo: str) -> dict[str, Any]  # line 84
def extract_github_repo(recipe_file: Path) -> tuple[str, str] | None  # line 152
def get_current_version(recipe_file: Path) -> str | None  # line 179
def check_version(recipe_path: Path | None = ..., github_repo: str | None = ...) -> dict[str, Any]  # line 191
def main() -> None  # line 256
```

**Internal helpers:** 4 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

