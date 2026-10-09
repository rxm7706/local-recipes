---
title: "23.3: A negative corpus proves each CFE check keeps rejecting its defect"
type: 'feature'
created: '2026-09-29'
status: 'ready-for-dev'
flag-exempt: detector-or-gate
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/recipe_optimizer.py
  - .claude/skills/conda-forge-expert/scripts/validate_recipe.py
  - .claude/skills/conda-forge-expert/scripts/license-checker.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CFE's tests prove that good recipes stay good. Almost nothing proves that bad recipes stay rejected, and that
half rots silently: a regex stops matching, or a check drops out of a registry, and no test turns red. CFE has one
negative fixture, `tests/fixtures/recipes/v1-broken`. auto-recipe keeps a corpus for exactly this. Its `tests/negative/`
(`OpenTeams-WFT-CDO/auto-recipe@8b53eda`; the operator owns the org) holds two verbatim grayskull outputs from 2026-08-04
that both passed conda-forge's linter:

- `grayskull-flask-pydantic.yaml`: `skip: match(python, "<3.9")` beside `noarch: python`, and a scalar
  `python_version: ${{ python_min }}.*` test. It also declares `python_min: "3.7"`, below the conda-forge floor.
- `grayskull-starlette-prometheus.yaml`: the same scalar test, and `license: GPL-3.0-only` for a package whose LICENSE
  grants "any later version".

auto-recipe's own rule is "A green negative fixture is a failing test."

**Approach:** add `tests/fixtures/negative/` with a `README` and one test module, `tests/unit/test_negative_corpus.py`.
Port the two grayskull fixtures verbatim. The starlette-prometheus case becomes a directory holding its `recipe.yaml` and
a LICENSE carrying the or-later text, because the licence check reads the LICENSE. Add CFE's own known-bad shapes: a
compiler with no `stdlib`, and the conda-recipe-manager sentinel key (reuse Story 22.2's fixture, don't copy it). Each
defect gets its own test asserting the specific rule that rejects it:

| Defect | Rule |
|---|---|
| scalar `python_version` test matrix (both grayskull fixtures) | `recipe_optimizer` `TEST-002` |
| compiler without `stdlib` | `recipe_optimizer` `STD-001` |
| `-only` licence against an or-later LICENSE | Story 23.1's `check_license_semantics` returns `fail` |
| sentinel key | Story 22.2's `validate_recipe` repr error |
| skip under `noarch: python` | a native offline check (see below) |
| `python_min` below the floor | whichever existing optimizer code fires; record it |

A parametrized test also fails for any fixture that no check rejects.

Skip under noarch is the one defect that may have no offline check today. conda-forge's linter rejects it, and CFE reaches
that linter only through `validate_recipe`'s external conda-smithy lint. If that is the only thing that fires, add a
native `recipe_optimizer.py` check at the next free code, `SEL-005`, so the corpus runs offline and fast. Record which
path was taken.

The whole change lands in the story's one `retro(cfe):` commit: the fixtures, the README, the test module, any `SEL-005`
check, the `CHANGELOG.md` entry and the version carriers (the Story 16.3 and 22.2 path).

Ledger key: `23-3-a-negative-corpus-proves-each-cfe-check-keeps-rejecting-its-defect`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-23.1, S-22.2.

### Living CAP citations

- `spec-pyforge-mason` CAP-33 (FR-55); AD-1 (CFE code only); AD-15 (the CFE surface moves only in the `retro(cfe):`
  commit).
- `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: detector-or-gate`. The corpus is a gate that reds CI when a
  check stops firing, and a flag-OFF gate would be a silent green.
- Depends on Story 23.1 (the licence check) and Story 22.2 (the sentinel-key check and its fixture).

## Acceptance Criteria

- Given the ported flask-pydantic fixture When the optimizer runs on it Then `TEST-002` is reported, and the skip-under-noarch rule (native `SEL-005`, or the documented alternative) is reported by the check named in the test
- Given the ported starlette-prometheus fixture directory When the optimizer and Story 23.1's check run on it Then `TEST-002` is reported and `check_license_semantics` returns `fail`
- Given the compiler-without-stdlib fixture When the optimizer runs Then `STD-001` is reported
- Given Story 22.2's sentinel-key fixture When `validate_recipe` runs Then it exits non-zero with the repr error
- Given any fixture in the corpus When every check runs and none rejects it Then the parametrized test fails
- Given any one check is disabled (for example `analyze_noarch_python_test_matrix` returns no suggestions) When the corpus runs Then that check's fixture test fails (mutation)
- Given the corpus When it runs Then it needs no network and no conda-smithy install
- Given the README When it is read Then it says the fixtures must never be "fixed", and names `auto-recipe@8b53eda` `tests/negative` as the source of the two ported files
- Given the story closes When the Rule-2 retro runs Then its `retro(cfe):` commit carries the fixtures, the README, the test module, any `SEL-005` check, a CFE `CHANGELOG.md` semver entry and the version carriers

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1). Read `recipe_optimizer.py`'s `optimize_recipe`,
   `analyze_noarch_python_test_matrix`, `analyze_stdlib_compliance` and `analyze_selectors`, and confirm Stories 23.1 and
   22.2 have landed.
2. Port the two grayskull fixtures verbatim into `tests/fixtures/negative/`, with a provenance line in the README. Put the
   starlette-prometheus recipe in a directory with a LICENSE carrying the or-later text.
3. Add the compiler-without-stdlib fixture, and reference Story 22.2's sentinel-key fixture by path.
4. Check whether any offline CFE check rejects skip under noarch. If none does, add `SEL-005` to `analyze_selectors` (a
   `skip:` entry on a `noarch: python` recipe), with a unit test.
5. Write `tests/unit/test_negative_corpus.py`: one test per defect asserting the rule code or message, and one
   parametrized "rejected by something" test. Assert the specific rule, never only that something failed.
6. Run `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit/test_negative_corpus.py -q` and the
   offline CFE suite, `pixi run -e local-recipes test`. Prove the mutation clause by disabling one check locally.
7. Land everything in one commit. Subject `retro(cfe): v<x.y.z> — a negative corpus pins each check to its defect`, never
   starting `Story 23.3:`. Bump MINOR if `SEL-005` lands, PATCH otherwise. Name the corpus in SKILL.md's testing guidance.
8. Reconcile every Spec `spec-surface-check` names (`spec-packaging-factory` for the CFE surface): memlog first, `git add`,
   then a scoped `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert`. Where this story and the skill disagree, the skill wins and the story records the
  deviation.
- Assert each fixture against its specific rule.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not "fix" a fixture to make a test pass. A green negative fixture is a failing test.
- Do not put the fixtures under `recipes/`. The repo-wide recipe meta-tests would red on them.
- Do not edit any `recipes/**` file.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| scalar test matrix | `python_version: ${{ python_min }}.*` | `TEST-002` | test asserts the code |
| skip under noarch | `skip:` + `noarch: python` | `SEL-005` (or the recorded alternative) | test asserts the rule |
| licence mismatch | `GPL-3.0-only` + or-later LICENSE | `check_license_semantics` → `fail` | test asserts `fail` |
| no stdlib | `compiler('c')`, no `stdlib('c')` | `STD-001` | test asserts the code |
| sentinel key | Story 22.2's fixture | `validate_recipe` repr error | exit non-zero |
| a fixture nothing rejects | a check disabled | parametrized test fails | the suite reds |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-33 (FR-55).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-29 — Proposed: CFE takes the three checks auto-recipe
had and Mason lacked, and auto-recipe retires*.
Ledger key: `23-3-a-negative-corpus-proves-each-cfe-check-keeps-rejecting-its-defect`.
Ledger status at mint: `backlog`.
Deps: S-23.1, S-22.2.
Flag: `flag-exempt: detector-or-gate` (a gate on CFE's own checks; flagging it OFF would be a silent green).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code, so the suite must stay green).

**Manual checks:**
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit/test_negative_corpus.py -q` — expected:
  pass, offline.
- `pixi run -e local-recipes test` — expected: pass (the offline CFE suite).
- Disable one check locally and re-run the corpus — expected: that check's fixture test fails (the mutation clause).
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert` — expected: exactly one `retro(cfe):`
  subject, carrying `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
