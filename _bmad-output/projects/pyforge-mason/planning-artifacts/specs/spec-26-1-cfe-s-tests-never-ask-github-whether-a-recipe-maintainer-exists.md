---
title: "26.1: CFE's tests never ask GitHub whether a recipe maintainer exists"
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: 'c53f0d7d426824040d6fa03f210d0d3c98a61a81'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/tests/conftest.py
  - .claude/skills/conda-forge-expert/tests/integration/test_workflow_npm.py
  - .claude/skills/conda-forge-expert/scripts/validate_recipe.py
  - .claude/skills/conda-forge-expert/tests/unit/test_clean_mirror_env.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CFE's `validate_recipe` runs conda-smithy's linter, and the linter's maintainer check
(`conda_smithy.lint_recipe._maintainer_exists`, and `_team_exists` for a `org/team` maintainer) asks github.com whether
each maintainer exists. With `GH_TOKEN` unset it asks unauthenticated (an HTTP `HEAD` of the user's profile page). The
`cfe-regression-net` lane sets no token, so its verdict depends on how GitHub answers an unauthenticated request from a
CI runner: on 2026-10-02 one PR failed the lane twice, in a different test of `tests/integration/test_workflow_npm.py`
each time (`Recipe maintainer "rxm7706" does not exist`), and passed on a re-run. The same request from a workstation
returns 200.

**Approach:** a fixture in CFE's `tests/conftest.py` replaces both lookups with a local answer for every test not
marked `network`, so no CFE test asks GitHub. A regression test proves the stub is in force by failing if a lookup
reaches the network. CFE's runtime lint is unchanged.

Ledger key: `26-1-cfe-s-tests-never-ask-github-whether-a-recipe-maintainer-exists`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-34 (FR-56): CFE's tests give the same verdict in any environment (Story 24.1 made the
  host-gate tests hermetic). A defect of the same class, so no new CAP; a `fix` needs no flag.

## Boundaries & Constraints

**Always:** Go through `conda-forge-expert` (Rule 1). Land code, tests, `CHANGELOG.md` entry and version carriers in
one `retro(cfe):` commit (Rule 2). The stub must take effect in the pytest process and in the `conda-smithy`
child that `validate_recipe.run_external_lint` starts (`script_runner` copies `os.environ` via `_ensure_path`).
Name every governed path you change on the owning Spec's `.memlog.md` and on each co-governor `spec-surface` names,
then run `python scripts/spec_surface_reconcile.py`. Every `deferred:` entry must cite a real repo path in `location:`.

**Never:** Do not change CFE's runtime lint or `validate_recipe`. Do not set a token in the workflow as the fix. Do not
touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `recipes/**`. Never pass `--write-baseline`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| suite lint, no token | non-`network` test runs `validate_recipe` / conda-smithy lint | recipe lint verdict from local rules; no github.com request | no flake on unauthenticated HEAD |
| stub in force | test calls `_maintainer_exists` or `_team_exists` | local answer; no request leaves the process | trap/assert if a request is attempted |
| network-marked test | test marked `network` | conda-smithy's real lookup | fixture does not replace the functions |
| stub removed | fixture body disabled; regression test runs | regression test fails (mutation) | CI reds if the stub is gone |

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/tests/conftest.py` -- add the autouse stub here, beside `clean_mirror_env` (Story 24.1, lines 170–193). `clean_mirror_env` is opt-in so `network` tests keep real mirrors; this stub is the opposite: on for every test that is not marked `network`.
- `.claude/skills/conda-forge-expert/scripts/validate_recipe.py:57–83` -- `run_external_lint` shells `conda-smithy recipe-lint --conda-forge <dir>`. Read-only. An in-process-only `monkeypatch.setattr` on the pytest process does not reach this child. The fixture must also land in that child (the child inherits `script_runner`'s copied `os.environ`).
- `.claude/skills/conda-forge-expert/tests/conftest.py:70–87` -- `script_runner` builds `env=_ensure_path()` from `os.environ.copy()`. Any `PYTHONPATH` / sitecustomize the fixture installs is visible to `validate_recipe` and therefore to conda-smithy.
- `conda_smithy.lint_recipe._maintainer_exists` -- unauthenticated path is `requests.head("https://github.com/{maintainer}", allow_redirects=False)` plus an orgs/teams HEAD; returns user-not-org. Installed copy: `.pixi/envs/local-recipes/lib/python3.14/site-packages/conda_smithy/lint_recipe.py` around the `_maintainer_exists` def.
- `conda_smithy.lint_recipe._team_exists` -- with no `GH_TOKEN` already returns `True` without a request; still stub it so a later smithy change cannot re-open the hole. Called from `run_conda_forge_specific` in the same module (maintainer string with `/` is the team path).
- `.claude/skills/conda-forge-expert/tests/integration/test_workflow_npm.py:91–93,165–167,217–219,232–234` -- the four `script_runner("validate_recipe.py", …)` sites that flaked on `Recipe maintainer "rxm7706" does not exist`. Do not change these tests.
- `.claude/skills/conda-forge-expert/tests/unit/test_clean_mirror_env.py` -- reuse this regression shape: plant a trap, assert the stub holds, document the mutation (fixture body disabled → the new test fails).
- `.claude/skills/conda-forge-expert/tests/pytest.ini` -- `network` marker is skipped by `pixi.toml` `test-ci` (`-m 'not network'`). The fixture reads `request.node.get_closest_marker("network")`.
- Version carriers at 8.91.2, PATCH to 8.91.3: `.claude/skills/conda-forge-expert/SKILL.md` (frontmatter `version:`, Version History), `CHANGELOG.md` (TL;DR current), `config/skill-config.yaml`, `MANIFEST.yaml`.
- Read-only: `.claude/skills/conda-forge-expert/scripts/validate_recipe.py`, `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock`, `recipes/**`.

## Tasks & Acceptance

**Execution:**
- `.claude/skills/conda-forge-expert/tests/conftest.py` -- add an autouse fixture that replaces `conda_smithy.lint_recipe._maintainer_exists` and `_team_exists` with a local answer for every test not marked `network`, including the conda-smithy child that `validate_recipe` starts -- in-process-only patch leaves the failing `script_runner` path live
- `.claude/skills/conda-forge-expert/tests/unit/test_stub_smithy_maintainer_lookups.py` -- new regression: with the stub in force, calling either lookup (and a `validate_recipe` lint of a fixture that names a maintainer) makes no request; with the fixture body disabled those assertions fail; a `network`-marked helper still sees the real functions
- `.claude/skills/conda-forge-expert/SKILL.md` -- add the testing rule next to the host-gate paragraph (`clean_mirror_env`); bump version and Version History to 8.91.3
- `.claude/skills/conda-forge-expert/CHANGELOG.md`, `.claude/skills/conda-forge-expert/config/skill-config.yaml`, `.claude/skills/conda-forge-expert/MANIFEST.yaml` -- PATCH carriers 8.91.2 → 8.91.3
- owning Spec `.memlog.md` and each co-governor `spec-surface` names -- name every governed path this story changes, then `python scripts/spec_surface_reconcile.py` (never `--write-baseline`)

**Acceptance Criteria:**
- Given no GH_TOKEN and no network route to github.com When the CFE suite runs Then every test that lints a recipe passes
- Given the stub in force When a test calls the maintainer or team lookup Then no request leaves the process
- Given a test marked `network` When it runs Then it keeps conda-smithy's real lookup
- Given the stub removed When the regression test runs Then it fails (mutation)

## Spec Change Log

## Review Triage Log

### 2026-10-02 — Review pass
- verdicts: 23 findings — high 0, medium 2, low 10, false 11, maybe-false 0
- findings:
  - `[low]` `[reject]` SKILL.md inserts the maintainer-lookup rule so “This gate HAD TWO independent copies…” no longer clearly names the JFrog credential host gate — the next sentences still name `dependency-checker.py` and `inventory_channel.py`; a rename is more than a needed correction and everyday readers still land on the auth-header copies.
  - `[false]` `[reject]` Reusing `@pytest.mark.network` means the helper never runs in `test-ci` / `cfe-regression-net`, and a future network lint would call GitHub — that is the specified split: `test-ci` is `-m 'not network'`, and a `network` test must keep conda-smithy’s real lookup. The helper ran and passed outside that filter.
  - `[low]` `[reject]` The production sitecustomize imports `conda_smithy.lint_recipe` at interpreter start in every `script_runner` child — extra import cost only; `ImportError` is swallowed; fixing it would add lazy-import complexity for a miss that everyday runs do not hit.
  - `[low]` `[reject]` Stub body exists in the helper module, `sitecustomize_source()`, and (before the patch) the trap string — all three still return `True`; unifying them would add indirection without a demonstrated current divergence.
  - `[false]` `[reject]` `CFE_STUB_SMITHY_LOOKUPS_ENV` is not read by the production sitecustomize — the env is the trap’s signal that the fixture installed the child stub; production sitecustomize is only on `PYTHONPATH` when that fixture ran, so it always applying stubs is correct.
  - `[false]` `[reject]` Stubs always return `True`, so a typo maintainer would pass — that is the specified local answer; the suite must not depend on GitHub existence.
  - `[low]` `[reject]` Story-spec `context:` does not name the new helper / regression / consistency files — fix is to edit this build’s spec.
  - `[low]` `[reject]` Binding block removed and Spec Change Log / Review Triage Log were empty at review start — planning rewrite plus this pass’s write-back; fix is to edit this build’s spec.
  - `[low]` `[reject]` I/O matrix omits GH_TOKEN already set, the two-hop grandchild, and PYTHONPATH sitecustomize shadowing — matrix lives in `<intent-contract>`; fix is to edit this build’s spec.
  - `[false]` `[reject]` Child lint test never mentions `rxm7706` and may pass without exercising the lookup — `v1-noarch/recipe.yaml` names `rxm7706`; the test asserts conda-smithy ran and validation passed, which is the maintainer check on that fixture.
  - `[low]` `[reject]` Code Map still cites `clean_mirror_env` at lines 170–193, now occupied by the new stub — fix is to edit this build’s spec.
  - `[low]` `[reject]` `test_skill_md_lists_existing_scripts_only` now allowlists every `tests/**/*.py` by basename — the check is “does this file exist”, not “did you cite the intended file”; a colliding typo was already possible among `test_*.py`.
  - `[low]` `[reject]` Regression trap patches only `requests.head` / `requests.get` — the product control is replacing `_maintainer_exists` / `_team_exists`; widening the trap to Session/urllib would be speculative complexity.
  - `[medium]` `[patch]` Child-path guard re-implemented the stub inside `_TRAP_THEN_STUB_SITECUSTOMIZE`, so emptying `sitecustomize_source()` left the regression green while `test_workflow_npm.py` would talk to GitHub again — trap sitecustomize now execs the fixture’s production `sitecustomize.py` on `PYTHONPATH` and only then wraps `requests`; emptying `sitecustomize_source()` fails the child lint test.
  - `[false]` `[reject]` Intent-alignment R2: proof should be `test_workflow_npm.py` itself — Approach asked for a new regression test; those four sites stay unchanged and inherit the autouse fixture.
  - `[false]` `[reject]` Suite-wide “no GitHub request” is only trapped in the new module — Approach says a regression test proves the stub; the fixture applies to the suite.
  - `[medium]` `[patch]` Intent-alignment: the child lint proof was aliased through the trap’s re-stub, not uniquely the fixture sitecustomize — same defect as the verification-gap row; same fix applied.
  - `[false]` `[reject]` `github_request_trap == []` only observes the parent process — a child GitHub call still raises in the child’s trap and fails `rc` / lint output; the real hole was the re-stub, not the parent list.
  - `[false]` `[reject]` Network helper does not call the real lookup (R4a vs R4b) — the helper asserts the original function objects and module; calling them would be a live GitHub request the matrix does not require.
  - `[low]` `[reject]` Child lint does not exercise `_team_exists` (`v1-noarch` is a user maintainer) — the in-process test calls both functions; a second fixture recipe is more than a direct correction.
  - `[false]` `[reject]` Mutation is documented, not an automated second case — that is the specified shape (same as `clean_mirror_env`); both fixture-body and empty-`sitecustomize_source()` mutations were run and failed as required.
  - `[false]` `[reject]` Trap is wider than the two smithy functions — the stub is the control; the trap is the proof. Width is intentional for the regression module.
  - `[false]` `[reject]` Diff also moves `test_skill_md_consistency.py`, memlogs, and version carriers the starting I/O matrix does not name — the Always clause requires Rule 2 carriers and memlog naming; those are process surfaces, not a product divergence.

## Design Notes

`validate_recipe.run_external_lint` is a subprocess. Patching `conda_smithy.lint_recipe` only inside pytest does not
change the child. The fixture must install something the child imports (a `PYTHONPATH` sitecustomize / `.pth` that
replaces the two functions on import) and also patch in-process for tests that import conda-smithy directly. `_team_exists`
without a token already returns True; stub it anyway. `_maintainer_exists` is the HEAD that flaked.

Do not invent a GH_TOKEN. Do not wrap `requests.head` as the only control: that would also mute unrelated HEAD calls
and would still miss a token-using `github.Github` path if a test exported `GH_TOKEN`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` -- expected: pass (no Mason code change)
- `pixi run --frozen -e local-recipes test-ci` with `GH_TOKEN` unset -- expected: pass
- `python scripts/spec_surface_reconcile.py` -- expected: exit 0 after every changed governed path is named on the owning Spec and each co-governor

**Manual checks:**
- Disable the fixture body and re-run the new regression module -- expected: fail (mutation)
- Confirm `validate_recipe.py` is byte-identical to HEAD except none -- expected: untouched

## Auto Run Result

Status: done

Summary: CFE tests no longer ask GitHub whether a recipe maintainer exists. An autouse fixture stubs `conda_smithy.lint_recipe._maintainer_exists` and `_team_exists` for every test not marked `network`, in-process and in the conda-smithy child that `validate_recipe.run_external_lint` starts (`PYTHONPATH` sitecustomize). Runtime lint and `validate_recipe.py` are unchanged. Landed as CFE v8.91.3 (`retro(cfe):`).

Files changed:
- `.claude/skills/conda-forge-expert/tests/conftest.py` — autouse `stub_smithy_maintainer_lookups` plus session sitecustomize dir.
- `.claude/skills/conda-forge-expert/tests/_smithy_maintainer_stub.py` — local `True` answers and sitecustomize source.
- `.claude/skills/conda-forge-expert/tests/unit/test_stub_smithy_maintainer_lookups.py` — trap, `v1-noarch` lint, `network` identity check; trap sitecustomize execs the production sitecustomize then wraps `requests`.
- `.claude/skills/conda-forge-expert/tests/meta/test_skill_md_consistency.py` — Version History may name `tests/*.py` helpers.
- `.claude/skills/conda-forge-expert/SKILL.md`, `CHANGELOG.md`, `config/skill-config.yaml`, `MANIFEST.yaml` — PATCH 8.91.2 → 8.91.3 and the testing rule.
- `spec-pyforge-mason`, `spec-packaging-factory`, and `spec-conda-forge-expert-rebuild` `.memlog.md` — named every governed path this story changed.

Review findings: one medium patch entry (two member rows: verification-gap child-path re-stub, and the matching intent-alignment alias). Trap sitecustomize no longer re-implements the stub. Nothing deferred. Every other finding was rejected (false claims, spec-edit-only nits, or low issues not worth extra complexity). Patched counts this pass: high 0, medium 1 entry, low 0.

Follow-up review recommendation: false. First pass; one medium patched entry, no high.

Verification:
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — 1589 passed + 12 parity passed.
- `env -u GH_TOKEN -u GITHUB_TOKEN pixi run --frozen -e local-recipes test-ci` — 9164 passed, 30 skipped, 11 deselected, 1 xpassed.
- `python scripts/spec_surface_reconcile.py` — exit 0, no drift. Never `--write-baseline`.
- `validate_recipe.py` byte-identical to HEAD.
- Mutation: fixture body disabled — both non-`network` regression tests failed (`CFE test asked GitHub: https://github.com/rxm7706` and env unset); restored.
- Mutation: empty `sitecustomize_source()` — child lint test failed; restored.
- All three regression tests, including the `network` helper, passed with tokens unset.

Residual risks: runtime lint with no `GH_TOKEN` still does the unauthenticated GitHub HEAD (required). Tests marked `network` keep the real lookup and can still flake if they lint a recipe; `test-ci` deselects them.
