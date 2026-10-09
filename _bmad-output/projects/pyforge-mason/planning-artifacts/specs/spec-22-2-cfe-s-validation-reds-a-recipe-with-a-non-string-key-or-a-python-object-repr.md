---
title: "22.2: CFE's validation reds a recipe with a non-string key or a Python object repr"
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: '400a0d0f77d58d0c115fdd959796a1653162e13a'
flag-exempt: detector-or-gate
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/validate_recipe.py
  - .claude/skills/conda-forge-expert/tests/unit/test_validate_recipe.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** conda-recipe-manager's v0→v1 conversion writes its internal sentinel's repr,
`<conda_recipe_manager.types.SentinelType object at 0x…>`, as a YAML mapping key wherever a `meta.yaml` construct has no
translation. The current crm (0.10.6) still does it, and exits 100 ("warnings") rather than failing. Twelve such files
reached `recipes/` on 2026-08-16 and sat there for six weeks (Story 22.1 repairs them). CFE's first gate did not catch
them. Measured on `main` at `0c8c07e6fc`:

- `validate_recipe` passes six of the twelve: semgrep, pyobjc-framework-systemconfiguration, psycopg2-yugabytedb,
  django-pygwalker, lerc and amundsen-databuilder.
- `validate_recipe_yaml` reads the file with `yaml.safe_load`, and PyYAML reads `<conda_recipe_manager… at 0x…>` as a
  plain string, so no check fires.
- conda-smithy's lint reports it only as an unexpected top-level key (pyautogui, shodan), and crashes in
  `lint_section_order` on the multi-output recipes.
- rattler-build refuses all twelve at parse time. The gate that should have been first was last.

The same blind spot lets through other non-string keys: `1:`, `true:` or `null:` load as `int`, `bool` or `None`, and
`2026-09-28:` loads as a `date`.

**Approach:** in `validate_recipe_yaml`, after the file parses and before the section checks, walk the parsed tree
(mappings and lists, recursively), carrying a path like `outputs[2].tests[0]`. Report one error per offence, naming the
path:

- `Non-string mapping key <repr(key)> at <path>` for any key that is not a `str`.
- `Python object repr as a mapping key at <path>: <key> (a converter leak, e.g. conda-recipe-manager's SentinelType)`
  for a `str` key that fully matches `^<[A-Za-z_][\w.]* object at 0x[0-9a-fA-F]+>$`.
- `Python object repr as a value at <path>` for a `str` scalar that fully matches the same pattern. Only a whole-value
  match counts, so prose that mentions a repr inside a sentence, such as an `about.description`, never fires.

Each error sets the result invalid, so the CLI exits non-zero. Wire nothing else: `validate_recipe` is already what the
MCP `validate_recipe` tool, `pixi run -e local-recipes validate` and `mason recipe validate` (by subprocess, AD-1) call,
so all of them gain the check. The v0 `meta.yaml` path is left alone: jinja makes a pre-render walk unreliable, and the
leak is a v1 artifact.

The whole change lands in the story's one `retro(cfe):` commit: the check, its test, the fixtures, the
`CHANGELOG.md` entry and the version carriers. Story 16.3 (`c1cb0db042`) set that path for a CFE behaviour change, and
it keeps the `spec-packaging-factory` CHANGELOG sentinel satisfied.

Ledger key: `22-2-cfe-s-validation-reds-a-recipe-with-a-non-string-key-or-a-python-object-repr`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-32 (FR-54); AD-1 (Mason gains the check through CFE, with no Mason change); AD-15 (the CFE
  surface moves only in the `retro(cfe):` commit).
- `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: detector-or-gate`. The check is a gate: it makes
  `validate_recipe` refuse a recipe, and a flag-OFF gate would be a silent green.
- Sibling: Story 22.1 repairs the twelve files. Independent: this story's fixtures are its own, so it does not depend
  on the corpus being clean, and either may land first.

## Acceptance Criteria

- Given a fixture `recipe.yaml` with the sentinel repr as a key nested in `tests[1]` (not at the top level) When `validate_recipe` runs on it Then it exits non-zero and an error names `tests[1]` and the repr
- Given a fixture with the repr as a key under `source` When `validate_recipe` runs Then it exits non-zero and names `source`
- Given a fixture with an integer key (`1: foo`) under `extra` When `validate_recipe` runs Then it exits non-zero with a `Non-string mapping key 1` error naming `extra`
- Given a fixture whose `about.summary` is exactly `<foo.Bar object at 0x7f00>` When `validate_recipe` runs Then it exits non-zero naming `about.summary`
- Given a fixture whose `about.description` says `repr() prints <foo.Bar object at 0x7f00> for this type` When `validate_recipe` runs Then no repr error is reported
- Given the existing clean fixtures (for example `tests/fixtures/recipes/v1-go-nocgo`) When `validate_recipe` runs Then their results are unchanged
- Given the tree walk removed When the sentinel-key fixture test runs Then it fails (mutation)
- Given the story closes When the Rule-2 retro runs Then its `retro(cfe):` commit carries the check, the test, the fixtures, a CFE `CHANGELOG.md` semver entry and the version carriers

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1). Read `validate_recipe_yaml` and the fixtures layout under
   `tests/fixtures/recipes/`.
2. Add the walk as a small pure helper (for example `_find_bad_keys(tree) -> list[str]`), called once from
   `validate_recipe_yaml` after the parse succeeds. Use no new dependency (stdlib `re`).
3. Add fixtures `tests/fixtures/recipes/v1-sentinel-key/recipe.yaml` (a copy of a small real case, such as semgrep's
   shape), `v1-nonstring-key/recipe.yaml`, `v1-repr-value/recipe.yaml` and `v1-repr-in-prose/recipe.yaml`. Add tests to
   `tests/unit/test_validate_recipe.py`. Assert on the error text and the exit code, not only on `valid`.
4. Run `pixi run -e local-recipes test` (the offline CFE suite) and the targeted
   `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit/test_validate_recipe.py -q`.
5. Land everything in one commit. Subject `retro(cfe): v<x.y.z> — validate_recipe reds non-string keys and object reprs`,
   never starting `Story 22.2:`.
   - The commit carries the check, test and fixtures, the `CHANGELOG.md` entry, and the version in `SKILL.md`,
     `MANIFEST.yaml` and `config/skill-config.yaml`. Bump MINOR: the gate is new behaviour.
   - Add a line to SKILL.md's validation guidance naming the check. If Story 22.1's gotcha has landed, cross-reference
     it.
6. Reconcile every Spec `spec-surface-check` names (`spec-packaging-factory` for the CFE surface): memlog first,
   `git add`, then a scoped `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert`. Where this story and the skill disagree, the skill wins and the story records the
  deviation.
- Match object reprs only as a whole key or a whole value.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not edit any `recipes/**` file. The twelve are Story 22.1's.
- Do not add a repo-wide corpus check here. It would red `main` until 22.1 lands. The corpus check is 22.1's.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`.
- Do not change the v0 `meta.yaml` path or the external-lint path (`run_external_lint`).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| sentinel key, nested | `tests[1]: {<…SentinelType object at 0x…>: …}` | error naming `tests[1]` | exit non-zero |
| sentinel key, top level | a top-level `<…object at 0x…>:` | error naming the root | exit non-zero |
| int / bool / null / date key | `1:`, `true:`, `null:`, `2026-09-28:` | `Non-string mapping key` error | exit non-zero |
| repr as a whole value | `summary: <foo.Bar object at 0x7f00>` | error naming `about.summary` | exit non-zero |
| repr in prose | a description sentence containing a repr | nothing | — |
| clean recipe | an ordinary v1 recipe | unchanged result | — |
| unparseable YAML | a syntax error | the existing `YAML parse error` result, unchanged | as today |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-32 (FR-54).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-28 (night) — Proposed: twelve recipes lose a
converter's leaked sentinel key, and CFE refuses the next one*.
Ledger key: `22-2-cfe-s-validation-reds-a-recipe-with-a-non-string-key-or-a-python-object-repr`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: detector-or-gate` (a validation gate; flagging it OFF would be a silent green).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code, so the suite must stay green).

**Manual checks:**
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit/test_validate_recipe.py -q` — expected:
  pass, with the new fixtures red where they should be.
- `pixi run -e local-recipes test` — expected: pass (the offline CFE suite).
- `pixi run -e local-recipes validate recipes/semgrep` before Story 22.1 lands — expected: non-zero, naming `tests[1]`
  (today it passes).
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert` — expected: exactly one `retro(cfe):`
  subject, carrying `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
