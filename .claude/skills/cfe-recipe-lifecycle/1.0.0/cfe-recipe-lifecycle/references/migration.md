# v0 -> v1 Feedstock Migration

## Contents

- [feedstock-migrator.py](#feedstock-migratorpy)

## feedstock-migrator.py {#feedstock-migratorpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/feedstock-migrator.py` (compiled copy: `scripts/feedstock-migrator.py`)

**Purpose (module docstring, verbatim first line):** Migrate feedstocks from meta.yaml to recipe.yaml format.

**CLI wrapper:** feedstock-migrator wrapper  
**Pixi task:** migrate  
**MCP tool(s):** migrate_to_v1

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
class MigrationResult  # line 29
def convert_jinja_syntax(content: str) -> str  # line 38
def convert_selectors(content: str) -> list[str]  # line 45
def convert_set_statements(content: str) -> tuple[dict, str]  # line 87
def convert_test_section(content: str) -> str  # line 112
def convert_about_fields(content: str) -> str  # line 119
def convert_pin_syntax(content: str) -> str  # line 133
def migrate_recipe(input_path: Path, output_path: Optional[Path] = ..., dry_run: bool = ..., backup: bool = ...) -> MigrationResult  # line 149
def main()  # line 252
```

