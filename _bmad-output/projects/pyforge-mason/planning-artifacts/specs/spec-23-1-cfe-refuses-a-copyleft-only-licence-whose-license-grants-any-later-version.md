---
title: "23.1: CFE refuses a copyleft -only licence whose LICENSE grants any later version"
type: 'feature'
created: '2026-09-29'
status: 'in-progress'
baseline_revision: f7e9368e70338cca4dbfbfd2adc5d57270948aac
flag-exempt: detector-or-gate
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/license-checker.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a GPL-family licence has two SPDX spellings, `-only` and `-or-later`, and both are valid. So every check CFE
runs today passes either one, even when the LICENSE text says the opposite. `license-checker.py --check-source` reads the
recipe's `about.license` and `about.license_file` and checks that the file exists, but it never reads the file. auto-recipe
met the live case: `starlette-prometheus` declared `GPL-3.0-only` for a package whose LICENSE grants "any later version".
Both identifiers pass the SPDX check and conda-forge's linter, so the wrong one ships as package metadata.

A second defect sits on the same path. When `--check-source` cannot find the declared licence file, `main()` prints
`[ERROR] File not found in source` but never adds it to `errors`, so the run still exits 0. Only the `license-check` pixi
task calls this script, so making that error count is safe.

**Approach:** port auto-recipe's `check_license_semantics` (`OpenTeams-WFT-CDO/auto-recipe@8b53eda`,
`src/auto_recipe/verify/checks.py`; the operator owns the org) into `license-checker.py` as a pure function,
`check_license_semantics(declared: str, source_dir: Path) -> tuple[str, str]`, returning a status of `pass`, `fail` or
`skip` and a message. It skips when there is no declared licence or the licence has no `-only`/`-or-later` axis (only
GPL, LGPL, AGPL and GFDL do). Otherwise it reads every file under `source_dir` whose name matches
`(LICEN[CS]E|COPYING)` for "any later version", case-insensitively. It fails when that phrase is present and the declared
identifier ends in `-only`, naming the `-or-later` identifier to use. It skips, with "needs a human read", when the text
states neither. `main()` calls it on the `--check-source` path: a fail prints `[ERROR]` and joins `errors`, so the run
exits non-zero, and a skip prints a note and leaves the exit code alone. The missing-licence-file error joins `errors` too.
The function carries a provenance comment naming its source. Story 23.2 imports it, so it must not print or exit.

The whole change lands in the story's one `retro(cfe):` commit: the function, its tests, the fixtures, the `CHANGELOG.md`
entry and the version carriers (the Story 16.3 and 22.2 path).

Ledger key: `23-1-cfe-refuses-a-copyleft-only-licence-whose-license-grants-any-later-version`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-33 (FR-55); AD-1 (CFE code only, and Mason reaches it by subprocess); AD-15 (the CFE surface
  moves only in the `retro(cfe):` commit).
- `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: detector-or-gate`. The check refuses a recipe, and a flag-OFF
  gate would be a silent green.
- Next: Story 23.2 imports this function for the generator's licence decision; Story 23.3 pins it in the negative corpus.

## Acceptance Criteria

- Given a fixture source directory whose LICENSE says "either version 3 of the License, or (at your option) any later version" and a recipe declaring `GPL-3.0-only` When `license-checker.py <recipe> --check-source <dir>` runs Then it exits non-zero and the output names `GPL-3.0-or-later`
- Given the same LICENSE and a recipe declaring `GPL-3.0-or-later` When it runs Then it exits 0 and reports no licence-semantics error
- Given a `GPL-3.0-only` recipe whose LICENSE states neither "only" nor "any later version" When it runs Then it reports a skip needing a human read and the exit code is decided by the other checks alone
- Given an `MIT` recipe When it runs Then the licence-semantics check is skipped
- Given the LICENSE is named `COPYING` or `LICENCE.txt` When it runs Then the check reads it
- Given `license_file` names a file absent from the source directory When it runs Then it exits non-zero (it exits 0 today)
- Given `check_license_semantics` is imported and called When it returns Then nothing is printed and the process does not exit
- Given the comparison is removed When the mismatch fixture's test runs Then it fails (mutation)
- Given the story closes When the Rule-2 retro runs Then its `retro(cfe):` commit carries the function, the tests, the fixtures, a CFE `CHANGELOG.md` semver entry and the version carriers

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1). Read `license-checker.py` end to end, including
   `extract_license_info`, `check_license_file_exists` and `find_license_files`.
2. Add `check_license_semantics(declared, source_dir)` beside `check_license_file_exists`, with a provenance comment
   naming `auto-recipe@8b53eda` `src/auto_recipe/verify/checks.py`. Stdlib only (`re`, `pathlib`).
3. Call it from `main()` on the `--check-source` path. A fail joins `errors`. Make the missing-licence-file error join
   `errors` as well.
4. Add fixtures under `tests/fixtures/` (for example `license-semantics/{only-vs-or-later,or-later,only-silent,mit}/`,
   each with a `recipe.yaml` and a LICENSE or COPYING) and a unit test that asserts on the exit code and the message.
5. Run `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit -q -k license` and the offline CFE
   suite, `pixi run -e local-recipes test`.
6. Land everything in one commit. Subject `retro(cfe): v<x.y.z> — license-checker refuses a -only id whose LICENSE grants
   any later version`, never starting `Story 23.1:`. Bump MINOR: the gate is new behaviour. Add a line to SKILL.md's
   licence guidance naming the check.
7. Reconcile every Spec `spec-surface-check` names (`spec-packaging-factory` for the CFE surface): memlog first, `git add`,
   then a scoped `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert`. Where this story and the skill disagree, the skill wins and the story records the
  deviation.
- Keep `check_license_semantics` pure: no printing, no exit, no network.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not edit any `recipes/**` file.
- Do not change the verdict for any non-GPL-family licence.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| mismatch | `GPL-3.0-only` + "any later version" | fail naming `GPL-3.0-or-later` | exit non-zero |
| agreement | `GPL-3.0-or-later` + "any later version" | pass | exit 0 |
| silent LICENSE | `GPL-3.0-only`, neither phrase | skip, "needs a human read" | exit unchanged |
| permissive | `MIT` | skip | exit unchanged |
| other names | `COPYING`, `LICENCE.txt` | read | — |
| missing file | `license_file` absent from source | `[ERROR]` counted | exit non-zero |
| no `--check-source` | recipe only | no semantics check | as today |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-33 (FR-55).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-29 — Proposed: CFE takes the three checks auto-recipe
had and Mason lacked, and auto-recipe retires*.
Ledger key: `23-1-cfe-refuses-a-copyleft-only-licence-whose-license-grants-any-later-version`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: detector-or-gate` (a licence gate; flagging it OFF would be a silent green).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code, so the suite must stay green).

**Manual checks:**
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit -q -k license` — expected: pass, with the
  mismatch and missing-file fixtures exiting non-zero.
- `pixi run -e local-recipes test` — expected: pass (the offline CFE suite).
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert` — expected: exactly one `retro(cfe):`
  subject, carrying `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
