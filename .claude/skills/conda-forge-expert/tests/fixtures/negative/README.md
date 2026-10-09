# CFE negative corpus (Story 23.3)

These fixtures are **deliberately bad**. Never "fix" them to make tests pass — a green
negative fixture is a failing test.

| Fixture | Defect | Expected offline check |
|---|---|---|
| `grayskull-flask-pydantic.yaml` | scalar `python_version` test; `build.skip` on `noarch: python`; below-floor `python_min` | `TEST-002`, `SEL-005`, `SEL-004` |
| `grayskull-starlette-prometheus/` | scalar test matrix; `GPL-3.0-only` vs or-later LICENSE | `TEST-002`, `check_license_semantics` → fail |
| `compiler-no-stdlib/` | `compiler('c')` without `stdlib('c')` | `STD-001` |
| (by reference) `tests/fixtures/recipes/v1-sentinel-key/` | conda-recipe-manager sentinel key | `validate_recipe` repr error |

The two grayskull YAML files are ported verbatim from
`OpenTeams-WFT-CDO/auto-recipe@8b53eda` `tests/negative/` (2026-08-04 grayskull outputs
that passed conda-forge's linter).
