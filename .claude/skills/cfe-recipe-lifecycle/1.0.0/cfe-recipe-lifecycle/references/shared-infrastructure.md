# Shared Infrastructure (Slice 5, sanctioned cross-slice runtime deps)

## Contents

- [_http.py](#-httppy)
- [_paths.py](#-pathspy)
- [_cfy_template.py](#-cfy-templatepy)

## _http.py {#-httppy}

**Source:** `.claude/skills/conda-forge-expert/scripts/_http.py` (compiled copy: `scripts/_http.py`)

**Purpose (module docstring, verbatim first line):** Enterprise-safe HTTP helpers for conda-forge-expert scripts.

**CLI wrapper:** no wrapper/MCP of its own — imported by mapping_manager.py, dependency-checker.py, recipe_updater.py, npm_updater.py, pr_artifacts.py, github_version_checker.py (this slice) and by Slice 1/3/4 scripts  
**Pixi task:** —  
**MCP tool(s):** —

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def inject_ssl_truststore() -> bool  # line 49
def atomic_writer(path: str | Path, mode: str = ..., **kwargs: Any)  # line 92
def atomic_write_bytes(path: str | Path, data: bytes) -> None  # line 142
def atomic_write_text(path: str | Path, text: str, encoding: str = ...) -> None  # line 148
def netrc_credentials(url: str) -> tuple[str, str] | None  # line 156
def auth_headers_for(url: str, skip_auth: bool = ...) -> dict[str, str]  # line 417
def make_request(url: str, extra_headers: dict[str, str] | None = ..., user_agent: str = ..., skip_auth: bool = ...) -> urllib.request.Request  # line 535
def open_url(request: urllib.request.Request, timeout: int = ...) -> Any  # line 560
def read_pixi_config() -> dict  # line 665
def resolve_conda_forge_urls(config: dict | None = ...) -> list[str]  # line 707
def resolve_pypi_simple_urls(config: dict | None = ...) -> list[str]  # line 743
def resolve_pypi_json_urls(package_name: str, version: str | None = ..., config: dict | None = ...) -> list[str]  # line 770
def resolve_github_urls(repo: str, path: str = ...) -> list[str]  # line 804
def resolve_github_raw_urls(repo: str, ref: str, path: str) -> list[str]  # line 821
def resolve_npm_urls(package_name: str) -> list[str]  # line 838
def resolve_cran_urls(name: str) -> list[str]  # line 863
def resolve_cpan_urls(dist: str) -> list[str]  # line 874
def resolve_luarocks_urls(name: str) -> list[str]  # line 886
def resolve_crates_urls(name: str) -> list[str]  # line 898
def resolve_rubygems_urls(name: str) -> list[str]  # line 911
def resolve_maven_urls(query_path: str) -> list[str]  # line 924
def resolve_nuget_urls(package_name: str) -> list[str]  # line 937
def resolve_endoflife_urls(product: str) -> list[str]  # line 950
def resolve_github_api_urls(path_suffix: str = ...) -> list[str]  # line 964
def resolve_gitlab_api_urls(path_suffix: str = ...) -> list[str]  # line 984
def resolve_codeberg_api_urls(path_suffix: str = ...) -> list[str]  # line 1000
def resolve_anaconda_channel_urls(channel: str, subdir: str = ..., filename: str = ...) -> list[str]  # line 1016
def resolve_s3_parquet_urls(month: str) -> list[str]  # line 1045
def list_s3_parquet_months() -> list[str]  # line 1099
def fetch_with_fallback(urls: list[str] | str, extra_headers: dict[str, str] | None = ..., user_agent: str = ..., timeout: int = ..., retries: int = ..., return_json: bool = ...) -> Any  # line 1145
def fetch_to_file_resumable(target: str | Path, urls: list[str] | str, chunk_size: int = ..., timeout: int = ..., user_agent: str = ..., extra_headers: dict[str, str] | None = ..., max_retries: int = ..., skip_auth: bool = ...) -> Path  # line 1200
```

**Internal helpers:** 7 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## _paths.py {#-pathspy}

**Source:** `.claude/skills/conda-forge-expert/scripts/_paths.py` (compiled copy: `scripts/_paths.py`)

**Purpose (module docstring, verbatim first line):** Canonical path resolution for conda-forge-expert scripts (Rule-2 retro, Story 5.5).

**CLI wrapper:** no wrapper/MCP of its own — imported by recipe_optimizer.py, feedstock_lookup.py, feedstock_context.py (this slice) and Slice 3's bootstrap_data.py  
**Pixi task:** —  
**MCP tool(s):** —

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def get_repo_root() -> Path | None  # line 28
def get_data_dir() -> Path | None  # line 54
```

## _cfy_template.py {#-cfy-templatepy}

**Source:** `.claude/skills/conda-forge-expert/scripts/_cfy_template.py` (compiled copy: `scripts/_cfy_template.py`)

**Purpose (module docstring, verbatim first line):** Shared renderer for the universal ``conda-forge.yml`` pre-seed.

**CLI wrapper:** no wrapper/MCP of its own — imported by submit_pr.py (this slice) and Slice 1's recipe-generator.py  
**Pixi task:** —  
**MCP tool(s):** —

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def render_conda_forge_yml(compiled: bool, noarch_python: bool, python_wheel: bool, feedstock: bool = ...) -> str  # line 24
```

