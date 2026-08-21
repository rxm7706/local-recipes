# Full API Reference — github_updater.py

## Contents

- [`_get_recipe_context`](#-get-recipe-context) (internal)
- [`_detect_source_path`](#-detect-source-path) (internal)
- [`_parse_github_repo`](#-parse-github-repo) (internal)
- [`_is_newer`](#-is-newer) (internal)
- [`update_recipe`](#update-recipe) (public)
- [`main`](#main) (public)

6 exports from `github_updater.py` (2 public, 4 internal). All T1-low confidence (Quick tier — source reading, no AST tool).

### _get_recipe_context

```python
def _get_recipe_context(recipe_path: Path) -> dict[str, Any]:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/github_updater.py:L81`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/github_updater.py:L81]
- Confidence: T1-low

### _detect_source_path

```python
def _detect_source_path(recipe_path: Path) -> str:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/github_updater.py:L92`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/github_updater.py:L92]
- Confidence: T1-low

### _parse_github_repo

```python
def _parse_github_repo(spec: str) -> tuple[str, str] | None:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/github_updater.py:L106`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/github_updater.py:L106]
- Confidence: T1-low

### _is_newer

```python
def _is_newer(latest: str, current: str) -> bool:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/github_updater.py:L119`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/github_updater.py:L119]
- Confidence: T1-low

### update_recipe

```python
def update_recipe(recipe_path: Path, github_repo: str | None = None, dry_run: bool = False, allow_prerelease: bool = False) -> dict[str, Any]:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/github_updater.py:L131`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/github_updater.py:L131]
- Confidence: T1-low

### main

```python
def main() -> None:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/github_updater.py:L269`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/github_updater.py:L269]
- Confidence: T1-low

