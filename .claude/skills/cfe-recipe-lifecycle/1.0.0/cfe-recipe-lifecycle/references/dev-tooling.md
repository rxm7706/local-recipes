# Reference Regeneration, Health Check & Ad-hoc Tooling

## Contents

- [gen_yml_reference.py](#gen-yml-referencepy)
- [health_check.py](#health-checkpy)
- [test-skill.py](#test-skillpy)

## gen_yml_reference.py {#gen-yml-referencepy}

**Source:** `.claude/skills/conda-forge-expert/scripts/gen_yml_reference.py` (compiled copy: `scripts/gen_yml_reference.py`)

**Purpose (module docstring, verbatim first line):** gen_yml_reference.py — auto-generate exhaustive Markdown references for

**CLI wrapper:** gen_yml_reference wrapper  
**Pixi task:** gen-yml-reference  
**MCP tool(s):** — (doc regenerator, no MCP tool)

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def fetch_schema(url: str, timeout: int = ...) -> dict  # line 51
def load_schema(target: str, schema_file: Path | None) -> dict  # line 57
def resolve_ref(ref: str, root: dict) -> dict  # line 63
def resolve_chain(body: dict, root: dict, depth: int = ...) -> dict  # line 75
def repr_default(v: Any) -> str  # line 83
def slugify(name: str) -> str  # line 90
def describe_type(schema: dict, root: dict, depth: int = ...) -> str  # line 94
def collect_top_level_keys(schema: dict) -> list[tuple[str, dict]]  # line 136
def collect_defs(schema: dict) -> dict[str, dict]  # line 140
def collect_nested_properties(body: dict, root: dict, depth: int = ...) -> dict[str, dict]  # line 144
def clean_desc(text: str | None) -> str  # line 159
def format_nested_row(name: str, body: dict, root: dict) -> str  # line 165
def render_key_section(name: str, body: dict, root: dict) -> list[str]  # line 180
def render_doc(target: str, schema: dict) -> str  # line 208
def parse_schema_file_args(raw: list[str]) -> dict[str, Path]  # line 280
def main()  # line 292
```

## health_check.py {#health-checkpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/health_check.py` (compiled copy: `scripts/health_check.py`)

**Purpose (module docstring, verbatim first line):** System Health Check for the local-recipes development environment.

**CLI wrapper:** health_check wrapper  
**Pixi task:** health-check  
**MCP tool(s):** run_system_health_check

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def health_check(func)  # line 35
def check_git_upstream_remote() -> Dict[str, Any]  # line 41
def check_github_cli_auth() -> Dict[str, Any]  # line 62
def check_docker_daemon() -> Dict[str, Any]  # line 84
def check_mcp_scripts() -> Dict[str, Any]  # line 108
def check_api_connectivity() -> Dict[str, Any]  # line 128
def run_all_checks() -> List[Dict[str, Any]]  # line 161
def print_results(results: List[Dict[str, Any]], use_json: bool) -> int  # line 171
def main()  # line 211
```

## test-skill.py {#test-skillpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/test-skill.py` (compiled copy: `scripts/test-skill.py`)

**Purpose (module docstring, verbatim first line):** 

**CLI wrapper:** no wrapper, no MCP tool — 10-line ad-hoc script, NOT the real test harness (that is tests/run_skill_suite.py, outside this slice); flagged as a likely dead-code/cleanup candidate by slice-map.md, not confirmed-useful  
**Pixi task:** —  
**MCP tool(s):** —

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def test_api()  # line 3
```

