# Vulnerability Scanning & PR Artifacts

## Contents

- [vulnerability_scanner.py](#vulnerability-scannerpy)
- [pr_artifacts.py](#pr-artifactspy)

## vulnerability_scanner.py {#vulnerability-scannerpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/vulnerability_scanner.py` (compiled copy: `scripts/vulnerability_scanner.py`)

**Purpose (module docstring, verbatim first line):** Vulnerability Scanner for conda-forge recipes.

**CLI wrapper:** vulnerability_scanner wrapper  
**Pixi task:** scan-vulnerabilities  
**MCP tool(s):** scan_for_vulnerabilities

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def extract_dependencies(recipe_path: Path) -> list[tuple[str, str]]  # line 125
def scan_via_api(packages: list[tuple[str, str]]) -> list[dict[str, Any]]  # line 235
def scan_via_local_db(packages: list[tuple[str, str]]) -> list[dict[str, Any]]  # line 307
def run_scan(recipe_path: Path, offline: bool = ...) -> dict[str, Any]  # line 352
def main() -> None  # line 418
```

**Internal helpers:** 9 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## pr_artifacts.py {#pr-artifactspy}

**Source:** `.claude/skills/conda-forge-expert/scripts/pr_artifacts.py` (compiled copy: `scripts/pr_artifacts.py`)

**Purpose (module docstring, verbatim first line):** pr_artifacts.py — download conda-forge PR build artifacts from Azure DevOps.

**CLI wrapper:** pr_artifacts wrapper  
**Pixi task:** pr-artifacts  
**MCP tool(s):** download_pr_artifacts

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def parse_pr_ref(ref: str, default_repo: str = ...) -> tuple[str, int]  # line 49
def resolve_build_ids(pr: int, repo: str = ..., check_name: str | None = ..., all_runs: bool = ...) -> list[int]  # line 138
def list_azure_artifacts(build_id: int, include_all: bool = ..., timeout: int = ...) -> list[dict[str, Any]]  # line 168
def download_artifact(artifact: dict[str, Any], target_dir: str | Path, timeout: int = ...) -> Path  # line 231
def extract_zip(zip_path: str | Path, dest: str | Path, platform: str | None = ..., platforms: list[str] | None = ...) -> list[str]  # line 287
def fetch_one_build(pr_ref: str, repo: str, build_id: int, output_root: Path, extract: bool = ..., keep_zips: bool = ..., platforms: list[str] | None = ..., include_all: bool = ..., force: bool = ...) -> dict[str, Any]  # line 459
def main(argv: list[str] | None = ...) -> int  # line 656
```

**Internal helpers:** 10 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

