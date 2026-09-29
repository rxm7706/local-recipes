---
title: "23.2: CFE's recipe generator asks instead of guessing"
type: 'fix'
created: '2026-09-29'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/recipe-generator.py
  - .claude/skills/conda-forge-expert/scripts/license-checker.py
  - .claude/skills/conda-forge-expert/tests/unit/test_recipe_generator.py
  - src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CFE's own Operating Principle 1 says "If a request is ambiguous, present the interpretations — don't pick
silently." `recipe-generator.py`'s PyPI path breaks it at six points, each of which writes a plausible value with no
sign that it was a guess:

1. **Build backend.** `determine_build_backend` reads the sdist's `[build-system].requires` when it can. When it cannot,
   it falls back to matching runtime `requires_dist` and, when nothing matches, returns `setuptools`.
2. **Import name.** `_extract_import_name_from_sdist` returns `""` when ambiguous, and the caller falls back to
   `name.replace("-", "_")`. When several top-level packages exist, it takes the shortest.
3. **noarch.** `_can_noarch_python` decides from classifiers when the sdist is unavailable.
4. **Licence.** `_resolve_license` takes the first matching classifier when several match, and ends at `REPLACE_LICENSE`
   for a bare family (`BSD`, `GPL`) or no metadata. A GPL `-only` classifier whose LICENSE grants "any later version"
   passes silently.
5. **Licence file.** `PackageInfo.license_file` defaults to `LICENSE` whatever the sdist ships.
6. **Python floor.** `_resolve_python_min` uses the conda-forge floor when a non-empty `python_requires` does not parse.

G7, G55 and G90 each record a live recipe that shipped one of these guesses.

**Approach:** port auto-recipe's Decided/Ambiguous contract (`OpenTeams-WFT-CDO/auto-recipe@8b53eda`,
`src/auto_recipe/decisions/base.py`; the operator owns the org) as a small type in `recipe-generator.py`. A decision is
either `Decided(value, source)` or `Ambiguous(question, options, default)`. Each of the six points returns one:

- Decided when the value comes from an authoritative source: the sdist's `[build-system]`, a single top-level package or
  Cargo's `[lib] name`, the sdist's own files, PEP 639 `license_expression` or exactly one licence classifier, exactly one
  licence-named file in the sdist, or a parsed or empty `python_requires`.
- Ambiguous otherwise, with the value the generator uses today as the default.

The licence decision also calls Story 23.1's `check_license_semantics` on the cached sdist, and a fail becomes a question
whose options are the `-only` and `-or-later` identifiers. `license-checker.py` has a hyphen in its name, so load it with
`importlib.util.spec_from_file_location`, not `import`.

Output, on the v1 PyPI path (noarch and the maturin route):

- The default run writes the recipe with each question's default, prints a `Questions (N):` block to stdout (question,
  options, default taken), writes the same list into the recipe's bottom `# CFE comments` block under `# Header:`, and
  exits 0, as today.
- `--strict` prints the questions, writes no files, and exits non-zero when any question exists.
- A run with no questions prints nothing new and writes the same recipe as before.

The v0 `meta.yaml` path prints the questions but writes no CFE block, because that path deliberately emits none.
`mason recipe new` runs this script by subprocess and reads its return code (`cfe.generate_recipe`). The default run keeps
exit 0, so Mason needs no change (AD-1).

**Why this is a fix, not a feature:** the principle already exists and the generator breaks it. The default path gains
output but keeps its exit code and recipe. `--strict` is the only new mode, and it is opt-in.

The whole change lands in the story's one `retro(cfe):` commit: the type, the six decision points, the tests, the
fixtures, the `CHANGELOG.md` entry and the version carriers (the Story 16.3 and 22.2 path).

Ledger key: `23-2-cfe-s-recipe-generator-asks-instead-of-guessing`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / M / S-23.1.

### Living CAP citations

- `spec-pyforge-mason` CAP-33 (FR-55); AD-1 (the default exit code does not move, so `cfe.generate_recipe` needs no
  change); AD-15 (the CFE surface moves only in the `retro(cfe):` commit).
- `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` Q1: a `fix` needs no flag.
- Depends on Story 23.1 (`check_license_semantics`). Story 23.3 does not depend on this story.

## Acceptance Criteria

- Given a fixture package whose sdist is available and has no `[build-system]` table, two top-level packages and exactly one LICENSE file, with no licence metadata or licence classifier and a `python_requires` of `">=3.1x"` When the generator runs Then stdout lists four questions (build backend, import name, licence, Python floor), the recipe's CFE comments block lists the same four, the recipe is written with each default, and it exits 0
- Given the same fixture When the generator runs with `--strict` Then it exits non-zero, prints the four questions, and writes no recipe
- Given a fully resolvable fixture (PEP 517 `[build-system]`, one package, `license_expression`, one LICENSE file, a parseable `python_requires`) When it runs Then no questions are printed and the recipe matches the one written before this change, apart from the CFE block's timestamps
- Given a fixture sdist that ships both `LICENSE` and `COPYING` When it runs Then a licence-file question offers both
- Given a fixture declaring `GPL-3.0-only` whose sdist LICENSE grants "any later version" When it runs Then a licence question offers `GPL-3.0-only` and `GPL-3.0-or-later`
- Given no sdist can be fetched When it runs Then the noarch decision is a question, not a silent classifier verdict
- Given the maturin route When a Cargo `[lib] name` exists Then the import name is decided and not questioned
- Given the Ambiguous branch of any decision point is removed When its fixture test runs Then it fails (mutation)
- Given `mason recipe new` runs the generator When the default run finishes Then its exit code is 0 and `cfe.generate_recipe` is unchanged
- Given the story closes When the Rule-2 retro runs Then its `retro(cfe):` commit carries the type, the decision points, the tests, the fixtures, a CFE `CHANGELOG.md` semver entry and the version carriers

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1), G7, G55 and G90. Read `fetch_pypi_info`,
   `generate_recipe_yaml`, `_generate_maturin_recipe_yaml`, `_render_cfe_block` and the six helpers named above.
2. Add the Decided/Ambiguous type with a provenance comment naming `auto-recipe@8b53eda`
   `src/auto_recipe/decisions/base.py`. Stdlib only.
3. Return a decision from each of the six points, and collect the questions on `PackageInfo`. Keep every current default.
4. Load `license-checker.py` with `importlib.util.spec_from_file_location` and call `check_license_semantics` on the
   cached sdist in the licence decision.
5. Print the questions, write them into the CFE block's `# Header:` section, and add `--strict` to the `pypi` subcommand.
6. Add offline tests to `tests/unit/test_recipe_generator.py`, building `PackageInfo` and fixture sdists in `tmp_path`
   through the `load_module` fixture the way `test_pypi_noarch_python_emits_universal_conda_forge_yml` does. Assert on the
   printed questions, the written CFE block, the exit code and the unchanged resolvable recipe.
7. Run `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit/test_recipe_generator.py -q` and
   the offline CFE suite, `pixi run -e local-recipes test`.
8. Land everything in one commit. Subject `retro(cfe): v<x.y.z> — recipe-generator reports the choices it could not
   settle`, never starting `Story 23.2:`. Bump MINOR: `--strict` is a new mode. Add a line to SKILL.md's generator
   guidance and cross-reference G7, G55 and G90.
9. Reconcile every Spec `spec-surface-check` names (`spec-packaging-factory` for the CFE surface): memlog first, `git add`,
   then a scoped `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert`. Where this story and the skill disagree, the skill wins and the story records the
  deviation.
- Keep every current default value. This story adds questions; it does not change what a default run writes.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not change the MCP `generate_recipe_from_pypi` tool. It runs grayskull, not this script.
- Do not change the npm, CRAN, CPAN or LuaRocks paths.
- Do not edit any `recipes/**` file.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| all resolvable | `[build-system]`, one package, PEP 639, one LICENSE, parseable floor | no questions, same recipe | exit 0 |
| no `[build-system]` | backend from `requires_dist` or default | backend question | exit 0 |
| two top-level packages | e.g. `pkg/` and `pkg_extra/` | import-name question | exit 0 |
| no sdist | fetch fails | noarch question | exit 0 |
| no licence metadata | `REPLACE_LICENSE` today | licence question | exit 0 |
| `-only` vs "any later version" | 23.1's check fails | licence question with both ids | exit 0 |
| `LICENSE` and `COPYING` | two licence files | licence-file question | exit 0 |
| unparseable floor | `python_requires=">=3.1x"` | floor question | exit 0 |
| any question, `--strict` | — | questions printed, no files | exit non-zero |
| v0 `--format legacy` | any question | questions printed, no CFE block | exit 0 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-33 (FR-55).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-29 — Proposed: CFE takes the three checks auto-recipe
had and Mason lacked, and auto-recipe retires*.
Ledger key: `23-2-cfe-s-recipe-generator-asks-instead-of-guessing`.
Ledger status at mint: `backlog`.
Deps: S-23.1.
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1): CFE's Operating Principle 1 already forbids a silent
pick, and the default run keeps its exit code and recipe.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code, so the suite must stay green).

**Manual checks:**
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit/test_recipe_generator.py -q` — expected:
  pass, with each ambiguous fixture listing its question and `--strict` exiting non-zero.
- `pixi run -e local-recipes test` — expected: pass (the offline CFE suite).
- `pixi run -e local-recipes generate-recipe pypi rich` into a scratch directory — expected: exit 0, and every question
  printed names a real ambiguity in rich's published metadata (record which, if any, in the story's Dev Notes).
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert` — expected: exactly one `retro(cfe):`
  subject, carrying `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
