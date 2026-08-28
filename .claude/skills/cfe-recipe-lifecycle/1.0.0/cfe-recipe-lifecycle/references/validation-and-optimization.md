# Validation & Optimization

## Contents

- [validate_recipe.py](#validate-recipepy)
- [recipe_optimizer.py](#recipe-optimizerpy)
- [recipe_editor.py](#recipe-editorpy)

## validate_recipe.py {#validate-recipepy}

**Source:** `.claude/skills/conda-forge-expert/scripts/validate_recipe.py` (compiled copy: `scripts/validate_recipe.py`)

**Purpose (module docstring, verbatim first line):** Recipe validation script for conda-forge recipes.

**CLI wrapper:** validate_recipe wrapper  
**Pixi task:** validate  
**MCP tool(s):** validate_recipe

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
class ValidationResult  # line 34
def normalize_path(path: Path) -> Path  # line 43
def run_external_lint(recipe_path: Path) -> tuple[list[str], list[str], bool]  # line 57
def validate_recipe_yaml(path: Path) -> ValidationResult  # line 108
def validate_meta_yaml(path: Path) -> ValidationResult  # line 297
def validate_recipe(path: Path) -> ValidationResult  # line 354
def print_result(result: ValidationResult, use_json: bool = ...) -> None  # line 371
def main() -> int  # line 411
```

## recipe_optimizer.py {#recipe-optimizerpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/recipe_optimizer.py` (compiled copy: `scripts/recipe_optimizer.py`)

**Purpose (module docstring, verbatim first line):** Recipe Optimization Linter for conda-forge recipes.

**CLI wrapper:** recipe_optimizer wrapper  
**Pixi task:** lint-optimize  
**MCP tool(s):** optimize_recipe

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
class OptimizationSuggestion  # line 65
def analyze_dependencies(data: Dict) -> List[OptimizationSuggestion]  # line 99
def analyze_noarch_python_constraints(data: Dict) -> List[OptimizationSuggestion]  # line 120
def analyze_pinning(data: Dict) -> List[OptimizationSuggestion]  # line 163
def analyze_about_section(data: Dict) -> List[OptimizationSuggestion]  # line 256
def analyze_build_script(recipe_dir: Path) -> List[OptimizationSuggestion]  # line 368
def analyze_selectors(data: Dict, recipe_path: Path | None = ...) -> List[OptimizationSuggestion]  # line 401
def analyze_stdlib_compliance(data: Dict) -> List[OptimizationSuggestion]  # line 568
def analyze_format_mixing(recipe_path: Path) -> List[OptimizationSuggestion]  # line 611
def analyze_source_security(data: Dict) -> List[OptimizationSuggestion]  # line 636
def analyze_tests_section(data: Dict) -> List[OptimizationSuggestion]  # line 672
def analyze_noarch_python_test_matrix(data: Dict) -> List[OptimizationSuggestion]  # line 700
def analyze_noarch_python_test_type(recipe_path: Path, data: Dict) -> List[OptimizationSuggestion]  # line 776
def analyze_maintainers(data: Dict) -> List[OptimizationSuggestion]  # line 872
def analyze_license_placement(data: Dict) -> List[OptimizationSuggestion]  # line 899
def analyze_yaml_indent(recipe_path: Path) -> List[OptimizationSuggestion]  # line 953
def analyze_schema_header(recipe_path: Path, data: Dict) -> List[OptimizationSuggestion]  # line 1001
def optimize_recipe(recipe_path: Path) -> List[OptimizationSuggestion]  # line 1048
def main()  # line 1086
```

**Internal helpers:** 2 underscore-prefixed function(s)/method(s) — see provenance-map.json for the full list (not reproduced here per Tier-1/Tier-2 progressive-disclosure convention).

## recipe_editor.py {#recipe-editorpy}

**Source:** `.claude/skills/conda-forge-expert/scripts/recipe_editor.py` (compiled copy: `scripts/recipe_editor.py`)

**Purpose (module docstring, verbatim first line):** Programmatic Recipe Editor for conda-forge recipes.

**CLI wrapper:** MCP-server-only, no CLI wrapper  
**Pixi task:** —  
**MCP tool(s):** edit_recipe

**Public exports (T1-low, python-ast-quick-tier extraction — see provenance-map.json for the full per-export record):**

```python
def get_nested_item(data: Dict, path: str)  # line 34
def set_nested_item(data: Dict, path: str, value: Any)  # line 49
def calculate_sha256_from_url(url: str) -> str  # line 60
def execute_actions(recipe_path: Path, actions: List[Dict[str, Any]]) -> Dict[str, Any]  # line 80
def main()  # line 159
```

