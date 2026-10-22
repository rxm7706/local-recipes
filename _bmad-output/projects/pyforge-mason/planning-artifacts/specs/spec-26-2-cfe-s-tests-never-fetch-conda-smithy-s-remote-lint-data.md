---
title: "26.2: CFE's tests never fetch conda-smithy's remote lint data"
type: 'fix'
created: '2026-10-22'
status: 'done'
baseline_revision: '3a642c7bc498cd38403867aec037f8aceaf67607'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-26-1-cfe-s-tests-never-ask-github-whether-a-recipe-maintainer-exists.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/tests/conftest.py
  - .claude/skills/conda-forge-expert/tests/_smithy_maintainer_stub.py
  - .claude/skills/conda-forge-expert/tests/unit/test_stub_smithy_maintainer_lookups.py
  - .claude/skills/conda-forge-expert/tests/integration/test_workflow_npm.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-10-22 a local `pr-preflight` failed 1 of 9,391 `test-ci` tests:
`tests/integration/test_workflow_npm.py::TestWorkflowNpmCanonical::test_canonical_chain_with_deps`. conda-smithy's lint
could not resolve `raw.githubusercontent.com`; the same file passed minutes later. Story 26.1 stubbed conda-smithy's two
GitHub lookups (`lint_recipe._maintainer_exists`, `_team_exists`). conda-smithy 3.62.0's lint reads two more files from
GitHub:

- `validate_schema.validate_json_schema` resolves the `bot` property of a recipe's `conda-forge.yml` through a `$ref` to
  `https://raw.githubusercontent.com/regro/cf-scripts/refs/heads/main/conda_forge_tick/cf_tick_schema.json`, with
  `requests.get` and no timeout. Every recipe CFE generates carries a `bot:` block (CFE v8.61.0).
- `linter.utils.load_linter_toml_metdata_internal` fetches conda-forge-pinning's `recipe/linter_hints/hints.toml` for
  every recipe it lints. It catches only `Timeout`, so a DNS failure raises out of the lint.

With the network blocked (`unshare -rn`), four tests fail, among them Story 26.1's own regression test. Its trap matches
`github.com`, and `raw.githubusercontent.com` does not contain that string.

**Approach:**
1. The autouse fixture `stub_smithy_maintainer_lookups` (in `tests/conftest.py`) answers both reads for every test not
   marked `network`, in the pytest process and, through the existing `PYTHONPATH` sitecustomize, in the conda-smithy
   child `validate_recipe` starts.
2. The hints lookup returns an empty table, `{"hints": {}}`. It cannot return `None`, conda-smithy's own answer when the
   fetch fails: 3.62.0 then reads `{}.get("hints", [])`, gets a list, and `run_conda_forge_specific` raises
   `AttributeError` for any recipe with requirements.
3. `CONDA_SMITHY_BOT_SCHEMA_URI`, conda-smithy's own override for the `bot` `$ref`, points at a vendored copy of
   `cf_tick_schema.json` (`tests/fixtures/conda_smithy/`, BSD-3-Clause, regro/cf-scripts commit `4cec2cf621`, its last
   change on `main`). Validation runs against the real schema, so a malformed `bot` block still fails. The URI is
   `"file://" + path`, not `Path.as_uri()`: conda-smithy reads it back as `uri[7:]` without unquoting.
4. The trap matches `githubusercontent.com` too, and a `network`-marked test compares the vendored schema with upstream.

Ledger key: `26-2-cfe-s-tests-never-fetch-conda-smithy-s-remote-lint-data`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-34 (FR-56): CFE's tests give the same verdict in any environment. Story 24.1 made the
  host-gate tests hermetic and Story 26.1 the maintainer lookups; this is the same class, so no new CAP. A `fix` needs no
  flag (`spec-feature-flag-governance` Q1).

## Acceptance Criteria

- **AC1 — Offline.** With the network blocked (`unshare -rn`), `tests/integration/test_workflow_npm.py` and
  `tests/unit/test_stub_smithy_maintainer_lookups.py` pass (`-m 'not network'`).
- **AC2 — No request.** The trap fails on any request to `github.com` or `githubusercontent.com`. A test lints a recipe
  whose `conda-forge.yml` carries a `bot:` block through `validate_recipe`, and the trap sees no request.
- **AC3 — Real schema.** Validation against the vendored schema passes a well-formed `bot` block and rejects a
  malformed one.
- **AC4 — Network tests.** A `network`-marked test sees conda-smithy's real lookups, with neither stub nor env var in
  place, and another matches the vendored schema to upstream.
- **AC5 — Mutation.** Each of these fails a named test; restore each:
  - drop the hints stub from the fixture;
  - drop it from `sitecustomize_source()`;
  - drop the `CONDA_SMITHY_BOT_SCHEMA_URI` env var;
  - build the URI with `Path.as_uri()`.
- **AC6 — Retro.** One `retro(cfe):` commit lands the code, the tests, a CFE `CHANGELOG.md` PATCH entry (v8.101.4) and
  the version carriers.

## Boundaries & Constraints

**Always:** Go through `conda-forge-expert` (Rule 1). Land the CFE files in one `retro(cfe):` commit that moves
`CHANGELOG.md` (Rule 2, `pyforge.testing_kit.branch_diff_guard`). Name every governed path on the memlogs of the Specs
that govern it, then stamp scoped (AGENTS.md pre-PR item 5). Read every verdict from the exit code.

**Never:** Change CFE's runtime lint or `validate_recipe`: at runtime conda-smithy reads the live hints and schema. Set
`CONDA_SMITHY_BOT_SCHEMA_URI` outside the test fixture. Touch `src/shared/packages/pyforge-mason/`, `pixi.toml`,
`pixi.lock` or `recipes/**`.

**Residual risk:**
- The vendored schema ages. The `network`-marked test reds when upstream changes it; `test-ci` deselects `network`, so
  it runs only on demand.
- With an empty hints table, no non-network test sees a `PackageToAvoid` hint. No CFE test asserts one.
- The trap wraps `requests.get` and `requests.head`. A read through another client (`urllib`, a `requests.Session`)
  escapes it; the `unshare -rn` run is the backstop.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior |
|----------|---------------|----------------------------|
| non-`network` test lints a recipe | network blocked | lint verdict from local rules; no request |
| recipe `conda-forge.yml` has `bot:` | `validate_recipe` | `bot` validated against the vendored schema |
| malformed `bot` (`automerge: "sometimes"`) | `validate_json_schema` | a validation error |
| hints lookup | `load_linter_toml_metadata()` | `{"hints": {}}` |
| `network`-marked test | live network | real lookups; vendored schema equals upstream |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-mason` CAP-34 (FR-56). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-mason.md` § *Realization log*, the 2026-10-22 entry (CFE's tests never fetch
  conda-smithy's remote lint data).
- Epic: Epic 26 (done). Story 26.2 is minted `done`, so `epic-26` stays `done` (operator rule 2026-10-04: a fix story
  goes into its done epic).
- Ledger key: `26-2-cfe-s-tests-never-fetch-conda-smithy-s-remote-lint-data`; status at mint `done`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."26"`, which already covers `.claude/skills/conda-forge-expert/**`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).
- `unshare -rn pixi run --frozen -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/integration/test_workflow_npm.py .claude/skills/conda-forge-expert/tests/unit/test_stub_smithy_maintainer_lookups.py -m 'not network' -q` — expected: 10 passed (AC1).
- `pixi run --frozen -e local-recipes python -m pytest .claude/skills/conda-forge-expert/tests/unit/test_stub_smithy_maintainer_lookups.py -q` — expected: 8 passed, the two `network` tests included (AC2–AC4).

**Run before the push (not dispatch gates):**
- `unshare -rn` over the whole non-network CFE suite — expected: no failure that reaches the network.
- The three mutations of AC5 — expected: each fails a named test.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.

## Run results

Run 2026-10-22 in the landing worktree on `3a642c7bc4`, every verdict read from its exit code. Tests ran with the
primary checkout's `local-recipes` interpreter (conda-smithy 3.62.0).

- **Before the fix, network blocked** (`unshare -rn`): `test_workflow_npm.py` plus the stub test file gave 4 failed,
  2 passed (exit 1). Every failure traces to `raw.githubusercontent.com`, for `linter_hints/hints.toml` or
  `cf_tick_schema.json`. The four failures: `test_canonical_chain_with_deps`, `test_zero_dep_chain`,
  `test_pip_check_still_suggested_for_python` and Story 26.1's
  `test_validate_recipe_lint_of_a_named_maintainer_makes_no_request`.
- **First attempt, `None` from the hints stub:** both `validate_recipe` tests failed online with conda-smithy's
  `AttributeError: 'list' object has no attribute 'get'` at `run_conda_forge_specific`
  (`lint_recipe.py:620`), the 3.62.0 fallback bug Approach 2 records. The stub answers `{"hints": {}}`.
- **AC1:** network blocked, the two files give 9 passed, 2 deselected (exit 0). The whole non-network CFE suite,
  network blocked: 9,392 passed, 30 skipped, 2 failed. Both failures were git state at that moment, not the network:
  `test_skill_files_tracked` (the vendored schema not yet `git add`ed) and `test_spec_surface_check_green` (the
  memlogs not yet appended).
- **AC2–AC4:** online, the stub file gives 7 passed (exit 0), the two `network` tests included. The vendored schema
  equals upstream `main`, and is byte-identical to the file at commit `4cec2cf621`.
- **AC5:** each mutation fails a named test, and the restored files give 5 passed, 2 deselected:
  - fixture hints stub dropped: `test_linter_hints_make_no_request`;
  - sitecustomize hints stub dropped: `test_validate_recipe_lint_of_a_named_maintainer_makes_no_request` and
    `test_validate_recipe_lint_of_a_bot_block_makes_no_request`;
  - `CONDA_SMITHY_BOT_SCHEMA_URI` dropped: `test_bot_schema_resolves_from_the_vendored_copy` and
    `test_validate_recipe_lint_of_a_bot_block_makes_no_request`.
- **AC6:** CFE v8.101.4, a PATCH entry in `CHANGELOG.md`; the version moves in `SKILL.md`, `MANIFEST.yaml` and
  `config/skill-config.yaml`.
- **Planning:** `chain-currency-sweep-check -- --project pyforge-mason` went stale on the memlog append; the PRD and
  the spine each gained a "Currency reconciliation — 2026-10-22" section, and it then reported current.

## Spec Change Log

- 2026-10-22, independent review (PASS, no blocker), fixed on the same branch:
  - S1: the spec-pyforge-mason memlog's 2026-10-22 decision said the hints stub returns `None`; a correcting decision
    entry records `{"hints": {}}`.
  - S2: `bot_schema_uri()` used `Path.as_uri()`, which percent-encodes; conda-smithy reads `uri[7:]` without unquoting,
    so a checkout path with a space would not resolve. It now builds `"file://" + path`, and a test validates through a
    copy under a directory whose name has a space (the `as_uri()` mutation fails it).
  - Nits: the unused module-level `apply_smithy_maintainer_stubs()` removed; two trap docstrings name
    `githubusercontent.com`; the `network` test checks the hints function's `__module__`; the log-format-dependent
    occurrence count is dropped from Run results, and the final offline runs are recorded.

- 2026-10-22: minted `done`, implemented and verified in the same change.

## Review Triage Log

- 2026-10-22, review 1 (independent subagent, read the diff against this spec): PASS, 0 blockers, 2 should-fix, 5
  nits. It reproduced AC1–AC6, the before-fix failures, every gate, and the whole non-network CFE suite offline
  (9,394 passed). All fixed on the branch (Spec Change Log) except one nit: the `26-2` key is in the tracked ledger but
  not yet the shared Tier-3 feed. That is deliberate, so the key cannot reach main before the merge; it is added to the
  feed at landing.
