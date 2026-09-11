---
spec: machine-checked-recipe-knowledge
status: shipped
owner-dream: docs/dreams/machine-checked-recipe-knowledge.md
surface:
  - scripts/failure_catalog_check.py   # the Story 7.2 drift detector this Spec owns
companions: []
sources:
  - ../../../../../../docs/dreams/machine-checked-recipe-knowledge.md
  - ../../../../../../docs/intake/external-repos-analysis-2026-08-22/report.md
open_questions: []
  # ANSWERED 2026-09-09, exactly as the question predicted: the catalog landed in
  # `.claude/skills/conda-forge-expert/config/`, because the artifact is derived AND tracked.
---

# SPEC — Machine-checked recipe knowledge

## Why
The CFE G-corpus (110+ gotchas) is prose with no machine linkage to the
checks that enforce it — knowledge and enforcement drift silently. Proven
pattern: auto-recipe's spec-generated 45-row catalog with lint-resolved
`enforced_by` pointers (2026-08-22 analysis; unlicensed, pattern only).

## Capabilities
- **CAP-1 — the generated catalog.** `failure-catalog.yaml` derives from
  SKILL.md's gotchas: per row, greppable `symptom_signature` tokens + an
  `enforced_by:` pointer into the real CFE check/test surface, or an
  explicit `null`. *Success:* regeneration is deterministic; hand-editing
  the catalog is detectably wrong (derived-artifact discipline).
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD b36c8be118: live `pixi run -e local-recipes failure-catalog-check` reports `117 row(s)... null_rows=115 coverage=1.7%`, matching the Spec's own 2026-09-09 snapshot exactly (no unnoticed drift); `test_failure_catalog_freshness.py::test_failure_catalog_check_passes_against_live_skill_md` and 28/28 `test_failure_catalog_generator.py` unit tests passing, including `test_enforced_by_stale_code_is_null`.
- **CAP-2 — the lint + drift gate.** Every non-null pointer resolves against
  the live check surface; catalog↔SKILL.md drift fails CI; the null-rows
  report is the prioritized machine-check backlog. *Success:* planting a
  bogus pointer or editing a gotcha without regenerating reds the suite.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD b36c8be118: `test_main_check_mode_in_sync_then_drift` (plants exactly this scenario -- in-sync then drifted) passing; `failure-catalog-check` scoped `repo`, auto-discovered by `scripts/detectors.py` per its own description text, confirmed live; 28/28 unit tests green.

## Constraints
Prose stays authoritative (the catalog derives); Rules 1/2 govern (CFE
surface — the landing carries its retro obligations); doctor's detector
conventions for the drift gate; no verbatim auto-recipe text/YAML.

## Non-goals
Rewriting gotchas; auto-generating new checks (the null backlog is a report,
not an actuator).

## Success signal
`enforced_by` coverage is a number the fleet can watch, drift is impossible
to land silently, and the next new gotcha arrives with its row + pointer or
an honest null.

**Shipped, and the number is watchable (2026-09-09).** Both CAPs are live and
green: `config/failure-catalog.yaml` (117 rows) derives from SKILL.md's gotcha
corpus via `scripts/failure_catalog_generator.py`, is freshness-guarded by
`tests/meta/test_failure_catalog_freshness.py`, and is independently re-resolved
by `scripts/failure_catalog_check.py` (DETECTOR scope `repo` at `:41`,
auto-discovered by `scripts/detectors.py`) — `pixi run -e local-recipes
failure-catalog-check` reports clean. It prints `null_rows=<n> coverage=<pct>` on
every run: **115 of 117 rows carry `enforced_by: null`, coverage 1.7 % as of
2026-09-09.** Raising that number is the null-rows backlog's job, not this Spec's —
this Spec's contract is that the number exists and cannot drift silently.

## Assumptions

- `scripts/spec_surface_allowlist.txt:100` still allowlists
  `scripts/failure_catalog_check.py` with the comment "allowlisted pending mason
  claiming it via a proper folder-format spec". This Spec **is** that spec, and
  this re-derive adds the path to `surface:`, so the allowlist entry now lists a
  governed path twice and should be deleted. That deletion is a code edit under
  `scripts/`, folded into **mason Story 15.1** as a named acceptance clause (that
  story already re-stamps scoped surface baselines for every governed path it
  deletes or moves). The stamp must be scoped — `python scripts/spec_surface_check.py
  --write-baseline --spec pyforge-mason/spec-machine-checked-recipe-knowledge` —
  never a bare `--write-baseline`, because the baseline reads the working tree plus
  `git ls-files` and this repo's tree is routinely dirty with other stations' work;
  new files must be `git add`-ed before stamping.
