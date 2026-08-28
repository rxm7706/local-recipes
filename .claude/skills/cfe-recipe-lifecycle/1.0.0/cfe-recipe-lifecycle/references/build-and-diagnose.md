# Local Build & Failure Diagnosis

## Contents

- [local_builder.py](#local-builderpy)
- [failure_analyzer.py](#failure-analyzerpy)

## local_builder.py {#local-builderpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/local_builder.py` (compiled copy: `scripts/local_builder.py`)

**Purpose (module docstring, verbatim first line):** Docker-less local builder for conda-forge recipes.

**CLI wrapper:** local_builder wrapper  
**Pixi task:** build-local(-all|-check|-setup-sdk)  
**MCP tool(s):** — (trigger_build/get_build_summary have no backing script per slice-map.md)

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def detect_native_platform() -> str  # line 81
def find_osx_sdk(sdk_version: str = ..., repo_root: Path | None = ...) -> Path | None  # line 163
def setup_osx_sdk(target_dir: Path, sdk_version: str = ..., accept_license: bool = ..., download_url: str | None = ..., timeout: int = ...) -> dict[str, Any]  # line 204
def build_one_platform(recipe_path: Path, target_platform: str, channels: tuple[str, ...] = ..., output_dir: Path | None = ..., dry_run: bool = ..., timeout: int = ...) -> dict[str, Any]  # line 367
def build_all_platforms(recipe_path: Path, platforms: tuple[str, ...] = ..., channels: tuple[str, ...] = ..., output_dir: Path | None = ..., dry_run: bool = ..., timeout: int = ...) -> dict[str, Any]  # line 472
def diagnose_environment(sdk_version: str = ...) -> dict[str, Any]  # line 519
def main() -> None  # line 573
```

**Internal helpers:** 6 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## failure_analyzer.py {#failure-analyzerpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/failure_analyzer.py` (compiled copy: `scripts/failure_analyzer.py`)

**Purpose (module docstring, verbatim first line):** Intelligent Build Failure Analyzer for conda-forge recipes.

**CLI wrapper:** failure_analyzer wrapper  
**Pixi task:** analyze-failure  
**MCP tool(s):** analyze_build_failure

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
class ErrorPattern  # line 28
def analyze_log(error_log: str) -> list[dict[str, Any]]  # line 926
def main() -> None  # line 959
```

**Internal helpers:** 1 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

