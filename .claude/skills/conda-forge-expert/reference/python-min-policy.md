# Python Version Policy (`python_min`)

Procedural rules for setting `python_min` in conda-forge recipes. The current floor (3.10) and the active build matrix are documented in `recipe-yaml-reference.md` § "Python Build Matrix"; this file covers when and how to apply each rule.

## Rules for setting `python_min`

1. **New `noarch: python` recipes (recipe.yaml v1)** — always use the CFEP-25 triad:
   ```yaml
   context:
     python_min: "3.10"        # global floor; increase if upstream requires it
   requirements:
     host:
       - python ${{ python_min }}.*
     run:
       - python >=${{ python_min }}
   tests:
     - python:
         imports: [mypackage]
         pip_check: true
         python_version: ${{ python_min }}.*
   ```

2. **New `noarch: python` recipes (meta.yaml v0)** — use:
   ```yaml
   {% set python_min = "3.10" %}
   requirements:
     host:
       - python {{ python_min }}
     run:
       - python >={{ python_min }}
   test:
     requires:
       - python {{ python_min }}
   ```

3. **When to use a value higher than `3.10`** — only when the upstream `python_requires` metadata explicitly requires a higher version. Always verify before setting `python_min` above the global floor.

4. **Never downgrade below `3.10`** — packages targeting Python 3.9 or 3.8 cannot be accepted into conda-forge as new recipes and will fail CI. Exception: existing feedstocks with a freeze on specific Python ranges (these require special handling and are not submittable to staged-recipes).

5. **Compiled packages** — use `python >=3.10` (no python_min variable; the build matrix handles versioning via the global pin).

6. **When reviewing existing recipes with `python_min: '3.9'`** — run `optimize_recipe` (SEL-002 will flag it) and update to `'3.10'` unless the upstream package's own `python_requires` is `>=3.9,<3.10` (i.e., genuinely 3.9-only).

## References

- [CFEP-25: python_min](https://github.com/conda-forge/cfep/blob/main/cfep-25.md)
- `recipe-yaml-reference.md` § "Python Build Matrix" — current matrix and floor history
