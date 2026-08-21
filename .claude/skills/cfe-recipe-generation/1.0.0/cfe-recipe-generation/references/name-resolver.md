# Full API Reference — name_resolver.py

## Contents

- [`_get_data_dir`](#-get-data-dir) (internal)
- [`normalize_name`](#normalize-name) (public)
- [`search_local_cache`](#search-local-cache) (public)
- [`search_repodata_fallback`](#search-repodata-fallback) (public)
- [`search_metadata_api`](#search-metadata-api) (public)
- [`resolve_name`](#resolve-name) (public)
- [`main`](#main) (public)

7 exports from `name_resolver.py` (6 public, 1 internal). All T1-low confidence (Quick tier — source reading, no AST tool).

### _get_data_dir

```python
def _get_data_dir() -> Path:
```

- Type: function (internal helper)
- Source: `.claude/skills/conda-forge-expert/scripts/name_resolver.py:L35`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/name_resolver.py:L35]
- Confidence: T1-low

### normalize_name

```python
def normalize_name(name: str) -> str:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/name_resolver.py:L47`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/name_resolver.py:L47]
- Confidence: T1-low

### search_local_cache

```python
def search_local_cache(pypi_name: str) -> str | None:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/name_resolver.py:L51`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/name_resolver.py:L51]
- Confidence: T1-low

### search_repodata_fallback

```python
def search_repodata_fallback(pypi_name: str) -> str | None:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/name_resolver.py:L61`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/name_resolver.py:L61]
- Confidence: T1-low

### search_metadata_api

```python
def search_metadata_api(pypi_name: str) -> str | None:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/name_resolver.py:L95`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/name_resolver.py:L95]
- Confidence: T1-low

### resolve_name

```python
def resolve_name(pypi_name: str) -> dict:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/name_resolver.py:L112`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/name_resolver.py:L112]
- Confidence: T1-low

### main

```python
def main():
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/name_resolver.py:L163`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/name_resolver.py:L163]
- Confidence: T1-low

