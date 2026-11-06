---
title: "25.23: reactpy-django retires"
type: 'fix'
created: '2026-11-05'
status: 'done'
baseline_revision: '32cfb7e686'
review_loop_iteration: 1
followup_review_recommended: false
flag-exempt: recipe-build
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
deferred:
  - id: reactpy-router-local-only-stale-record
    summary: "reactpy-router 3.0.0b1 is local-only with no feedstock, pins reactpy >=2.0.0b12, and its success record predates the identity mirror, so it cannot solve against reactpy 1.1.0. reactpy-utils lists it, so it was not retired with reactpy-django. Rebuild reactpy-utils, then decide whether the router stays."
    location: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-23-reactpy-django-retires.md:70
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The identity mirror replaced the operator-directed local-only `reactpy` 2.0.0b13 with the feedstock's 1.1.0.
`reactpy-django` 6.0.0b1 pins `reactpy >=2.0.0b13`, has no feedstock, and can no longer solve, while its 2026-07-14 `success`
record stands. `DW-mason-25-22-3` asked the operator to restore the chain or retire the recipe.

**Approach:** Operator ruling 2026-11-05: "Retire reactpy-django". Remove `recipes/reactpy-django/`, and delete the `reactpy`
v2 patch file Story 25.22 kept until this decision. Git keeps both.

Ledger key: `25-23-reactpy-django-retires`. Type / Effort / Deps: fix / S / Story 25.22.

### Living CAP citations

- **CAP-35** — the feedstock refresh campaign; this recipe sits outside its scope, because no feedstock exists. This story closes `DW-mason-25-22-3`.

## Acceptance Criteria

- **AC1 — The recipe.** `recipes/reactpy-django/` is gone, and no `recipe.yaml` or `meta.yaml` under `recipes/` lists it.
- **AC2 — The patch.** `recipes/reactpy/patches/` is gone, and `reactpy`'s CFE comments say why, with its record and body unchanged.
- **AC3 — The rest.** `reactpy-router` stays and its state is deferred, the skill's live reference to `reactpy-django` no longer calls it live, and `DW-mason-25-22-3` closes.
- **AC4 — The retro.** A `retro(cfe):` commit carries a CFE `CHANGELOG.md` entry, and `pixi run --frozen -e pyforge-mason pyforge-mason-test` exits 0.

## Boundaries & Constraints

- Scope is `reactpy-django`, as ruled. `http-router`, `asgi-tools` and `reactpy-router` stay.
- The Warden test corpus keeps its own frozen copy of the chain, which nothing here reads.

**Never:**
- Never write a `cfe-local-build-*` field by hand; never open a feedstock, staged-recipes or upstream PR.

</intent-contract>

## Binding

Parent: `spec-pyforge-mason` CAP-35

- Closes: `DW-mason-25-22-3`.
- Epic: Epic 25.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).
- `grep -lE '^\s*-\s*reactpy-django\b' recipes/*/recipe.yaml recipes/*/meta.yaml` — expected: no match.

## Run record (2026-11-05)

`recipes/reactpy-django/` and `recipes/reactpy/patches/` are removed, and git keeps both at `32cfb7e686`. `reactpy` changed one CFE comment line, so its body and `cfe-local-build-*` record stand. No recipe was built: nothing that remains changed a body line. `reactpy-router` and `http-router` each gained a CFE comment saying the chain's end is retired.

`reactpy-router` 3.0.0b1 keeps a 2026-07-14 `success` record it could not earn today, the defect this story removes from `reactpy-django`. It stays because `reactpy-utils` lists `reactpy-router >=1.0.3`, and the ruling names one recipe. `DW-mason-25-23` carries it.

### Independent review

A separate reviewer found no high items and one medium: the Story's "so that" line claimed no recipe in the repo keeps the defect, though `reactpy-router` does. Reworded. Low items are fixed here: the two comments above, this run record, and the CHANGELOG's wording. It confirmed that nothing outside the Warden corpus reads the retired path, and that corpus keeps its own frozen copy.

## Spec Change Log

- 2026-11-05: minted on the operator's ruling, "Retire reactpy-django".
