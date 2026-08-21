# Full API Reference — _cfy_template.py

## Contents

- [`render_conda_forge_yml`](#render_conda_forge_yml) (public)

1 export from `_cfy_template.py` (1 public, 0 internal). T1-low confidence (Quick tier — source
reading, no AST tool). Added post-compile (Story 6.3, CAP-2 equivalence testing) — see
`references/knowledge-gotchas.md` and the compiled package's `provenance-map.json` for the finding
this addition resolved (`recipe-generator.py` has a hard top-level import of this module).

### render_conda_forge_yml

```python
def render_conda_forge_yml(*, compiled: bool, noarch_python: bool, python_wheel: bool, feedstock: bool = False) -> str:
```

- Type: function (public export)
- Source: `.claude/skills/conda-forge-expert/scripts/_cfy_template.py:24`
- Provenance: [SRC:.claude/skills/conda-forge-expert/scripts/_cfy_template.py:24]
- Confidence: T1-low
- Renders the universal `conda-forge.yml` pre-seed (trim top + bottom CFE block). Called from
  `recipe-generator.py`'s recipe-generation paths for `conda-forge.yml` scaffolding.
