# Submission & Pre-Submission Feedstock Context

## Contents

- [submit_pr.py](#submit-prpy)
- [feedstock_lookup.py](#feedstock-lookuppy)
- [feedstock_context.py](#feedstock-contextpy)
- [feedstock_enrich.py](#feedstock-enrichpy)
- [_path_guard.py](#-path-guardpy)

## submit_pr.py {#submit-prpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/submit_pr.py` (compiled copy: `scripts/submit_pr.py`)

**Purpose (module docstring, verbatim first line):** Two-step submission to conda-forge/staged-recipes.

**CLI wrapper:** submit_pr wrapper + prepare_pr wrapper (--prepare-only)  
**Pixi task:** submit-pr / prepare-pr  
**MCP tool(s):** submit_pr, prepare_submission_branch

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def prepare_branch(recipe_name: str, branch: str | None = ..., force: bool = ..., dry_run: bool = ...) -> dict[str, Any]  # line 128
def open_pr(recipe_name: str, branch: str | None = ..., pr_title: str | None = ..., pr_body: str | None = ..., dry_run: bool = ...) -> dict[str, Any]  # line 292
def submit_pr(recipe_name: str, dry_run: bool = ..., pr_title: str | None = ..., pr_body: str | None = ..., branch: str | None = ..., force: bool = ...) -> dict[str, Any]  # line 359
def main() -> None  # line 394
```

**Internal helpers:** 6 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## feedstock_lookup.py {#feedstock-lookuppy}

**Source:** `.claude/skills/conda-forge-expert/scripts/feedstock_lookup.py` (compiled copy: `scripts/feedstock_lookup.py`)

**Purpose (module docstring, verbatim first line):** Look up an existing conda-forge/<pkg>-feedstock and return its parsed recipe.

**CLI wrapper:** MCP-server-only, no CLI wrapper  
**Pixi task:** —  
**MCP tool(s):** lookup_feedstock

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
class FeedstockLookupResult  # line 52
def feedstock_lookup(pkg_name: str, use_cache: bool = ...) -> FeedstockLookupResult  # line 170
def main() -> int  # line 233
```

**Internal helpers:** 6 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## feedstock_context.py {#feedstock-contextpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/feedstock_context.py` (compiled copy: `scripts/feedstock_context.py`)

**Purpose (module docstring, verbatim first line):** Surface open issues + recent closed issues from an existing conda-forge feedstock

**CLI wrapper:** MCP-server-only, no CLI wrapper  
**Pixi task:** —  
**MCP tool(s):** get_feedstock_context

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
class IssueSummary  # line 49
class FeedstockContext  # line 62
def fetch_feedstock_context(pkg_name: str, max_open: int = ..., max_closed: int = ..., use_cache: bool = ...) -> FeedstockContext  # line 149
def main() -> int  # line 216
```

**Internal helpers:** 6 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## feedstock_enrich.py {#feedstock-enrichpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/feedstock_enrich.py` (compiled copy: `scripts/feedstock_enrich.py`)

**Purpose (module docstring, verbatim first line):** Enrich a freshly-generated recipe with metadata from the existing conda-forge feedstock.

**CLI wrapper:** MCP-server-only, no CLI wrapper  
**Pixi task:** —  
**MCP tool(s):** enrich_from_feedstock

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def enrich_recipe(recipe_path: Path, dry_run: bool = ...) -> dict  # line 161
def main() -> int  # line 248
```

**Internal helpers:** 6 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## _path_guard.py {#-path-guardpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/_path_guard.py` (compiled copy: `scripts/_path_guard.py`)

**Purpose (module docstring, verbatim first line):** Path confinement for recipe-facing CLIs (AUD-CFE-001 / -002 / -006).

**CLI wrapper:** no wrapper, no MCP tool (internal guard used by recipe_editor.py + submit_pr.py)  
**Pixi task:** —  
**MCP tool(s):** —

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def recipes_root() -> Path  # line 42
def validate_recipe_name(recipe_name: str) -> None  # line 50
def resolve_under_recipes(path: Path | str) -> Path  # line 67
def validate_recipe_file_path(recipe_path: Path | str) -> Path  # line 80
```

