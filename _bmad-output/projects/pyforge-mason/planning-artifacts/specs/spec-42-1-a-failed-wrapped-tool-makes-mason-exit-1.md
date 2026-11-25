---
title: '42.1: A failed wrapped tool makes mason exit 1'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 42-1-a-failed-wrapped-tool-makes-mason-exit-1
spec: spec-pyforge-mason
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/exit_codes.py'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/recipe.py'
  - 'src/shared/packages/pyforge-mason/tests/**'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md'
  - '.claude/skills/pyforge-mason/**'
  - 'src/shared/packages/django-pyforge/src/django_pyforge/station_cli.py'
  - 'src/platform/tests/test_station_cli.py'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md'
  - '.claude/memory/project/2026-11-06-operator-rulings-on-wiring-the-seven-start-tools.md'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-41-1-the-pypi-test-rehearsal-asks-the-index-it-uploads-to-and-a-wrapped-tool-s-failure-exits-as-the-contract-says.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-mason.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-mason-41-1-1` carries an operator decision Story 41.1 left open. `recipe build`, `scan`, `optimize`, `update` and `submit` exit 0 when the tool they wrap failed; the failure is in the payload only (`data.returncode`, or the ship state), while `package ship` with a `failed` target exits 1. A caller that reads the exit code alone reads a failed build as a pass. `recipe diagnose` and `package build` carry the same `data.returncode` and exit 0 the same way. The old exit is written down as intended in five places: `contract.md` § *Exit codes* (`EXIT_OK`: "For most verbs this says nothing about the delegated tool: read `data.returncode`") and § *Ship states* ("`recipe submit` exits 0 in every state"), the compiled station skill, `cli.py`'s comments citing AD-4, `tests/unit/test_cli.py -k wrapped_tool_exit` (Story 41.1's pin), and the docstring of `django_pyforge.station_cli._judge_build`, whose `start_build` row accepts exit 0 alone.

**Ruling (operator, 2026-11-25, in session, on this row): "Exit 1 on failure".** A failed wrapped tool makes mason exit 1. This is a contract change, not a defect fix: Story 41.1 was right that the code matched its contract, and this story changes the contract.

**Approach:**
- One rule, no exception list. A verb that wraps a tool exits `EXIT_FAILED` when that tool's return code is non-zero: `recipe build`, `diagnose`, `optimize`, `scan` and `update`, and `package build` on either engine's return code. `recipe submit` exits `EXIT_FAILED` when its ship state is `failed`, as `package ship` already does. Otherwise each exits `EXIT_OK`.
- Mason does not interpret the code. CFE's vulnerability scanner exits non-zero on a vulnerability and its optimizer on a suggestion; Mason then exits 1, as it already does for a failing validator. Deciding which non-zero codes are "only findings" would be recipe knowledge in Mason.
- The result is rendered exactly as today: the envelope's `status` stays `ok`, `errors` stays `[]`, and `data` carries the same return code or state. Nothing is raised; the projection is one expression per branch in `cli.py`, through `exit_codes.py`'s names.
- Write the failing test first: one parametrized test named `failed_wrapped_tool` drives the seven verbs through `main()` with a failed wrapped result and expects exit 1; it fails on the unchanged tree. Its sibling cases hold exit 0 for a return code of 0 and for `not_attempted`, `pending` and `terminal`. Story 41.1's `wrapped_tool_exit` test and the tests named `..._failed_child_still_renders_ok` take the new exit and keep their envelope assertions.
- Move every statement of the old exit in the same change: `contract.md` (the `EXIT_OK` and `EXIT_FAILED` rows, § *Ship states*, the envelope's `data` bullet, the `run_build` paragraph), the compiled station skill by the route its meta-tests accept, and `cli.py`'s comments and the `_dispatch_package_ship` docstring.
- The one outside reader: the `start_build` row in `station_cli.py` takes `result_codes` of 0 and 1, so a failed build still reaches `_judge_build`, which still fails the run with the build's own return code and the tail of its log; the docstring says what Mason now does.
- The Spec and the spine move by their own routes: CAP-2, CAP-5 and the "Subprocess only" constraint of `SPEC.md` through the memlog correction and the re-derive (never a hand edit), AD-4 by a dated note in the spine, and the PRD by a dated currency note that says no requirement moves (FR-32's code list is unchanged).

Ledger key: `42-1-a-failed-wrapped-tool-makes-mason-exit-1`.

### Living CAP citations

- spec-pyforge-mason CAP-2 and CAP-5 (each amended 2026-11-25); AD-4 as amended 2026-11-25.
- `spec-pyforge-unifying-strategy:CAP-20` (the start tools' closed table; read, no text change).
- `spec-feature-flag-governance` Q1: a fix carries no flag.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep `exit_codes.py` the one owner: `cli.py` returns its names and computes no number.
- Keep the envelope and `data` byte-identical for every case this story touches; only the process exit changes.
- Move `contract.md`, the compiled skill and the code in one change, so `tests/meta/test_public_contract.py` never reads two contracts.
- Close `DW-mason-41-1-1` naming the operator ruling and the commit.

**Never:**
- Never add an exit code, an option, an environment variable or a flag.
- Never raise for a non-zero delegated return code, and never set the envelope's `status` to `error` for one.
- Never interpret a wrapped tool's return code (no table of "findings" codes): that is recipe knowledge.
- Never change `doctor` (always 0), or the exit of `not_attempted`, `pending` and `terminal`.
- Never hand-edit a `SPEC.md` or `sprint-status-ledger.yaml`.
- Never import `pyforge` in a file under `src/platform/`.

## Acceptance Criteria

**Given** `recipe build`, `diagnose`, `optimize`, `scan` and `update` and `package build` exit 0 when the tool they wrap returned non-zero, `recipe submit` exits 0 when its ship state is `failed`, `contract.md` § *Exit codes* and § *Ship states*, the compiled station skill and `cli.py`'s reading of AD-4 state that exit as intended, Story 41.1's test pins it, and the `start_build` row of django-pyforge's verb table accepts exit 0 alone
**When** a test that fails on the unchanged tree first holds each of those seven verbs to exit 1 on a failed wrapped tool, `cli.py` then projects the return code or the ship state through `exit_codes.py`, Story 41.1's test takes the new exits, `contract.md` and the compiled skill state the new rule, the Spec's CAP-2 and CAP-5 and the spine's AD-4 are amended by their own routes, and the `start_build` row accepts exit 1 with a report
**Then** each of the seven verbs exits 1 when its wrapped tool's return code is non-zero or its ship state is `failed` and exits 0 otherwise, under an envelope whose `status` is `ok` and whose `data` carries the same return code or state as before; `not_attempted`, `pending` and `terminal` exit 0; `doctor` exits 0; and no exit code outside 0, 1, 2, 3 and 130 exists
**And** a failed build reached through `start_build` still fails its run with the build's own return code and the tail of its log, no sentence in `contract.md`, the compiled skill, Mason's source or django-pyforge's states the old exit, and no page under `docs/` did
**And** `chain-currency` reads the mason chain current after the Spec, the PRD and the spine carry their dated notes, and `DW-mason-41-1-1` reads closed in its ledger naming the ruling and the commit

- **AC1 — A failed wrapped tool exits 1, and a tool that passed exits 0.** Expected: exit 0 (exit 5 at mint: no such test). The selected tests are written first and fail on the unchanged tree. They drive `recipe build`, `diagnose`, `optimize`, `scan`, `update` and `submit` and `package build` (once per engine return code) through `main()` with a failed wrapped result and expect `EXIT_FAILED`; the same verbs with a return code of 0, and `recipe submit` in `not_attempted`, `pending` and `terminal`, expect `EXIT_OK`; every case asserts `status == "ok"`, `errors == []` and the return code or state in `data`.

  ```bash
  pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_cli.py -q -k failed_wrapped_tool
  ```

- **AC2 — Story 41.1's pin and the rest of the CLI suite hold the new contract.** Expected: exit 0. `-k wrapped_tool_exit` now expects exit 1 for the five recipe verbs it names and still exit 1 for `package ship`; no test in the file expects exit 0 from a failed wrapped tool.

  ```bash
  pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_cli.py -q
  ```

- **AC3 — No statement of the old exit is left.** Expected: exit 0 (exit 1 at mint: `git grep` finds the three sentences in `contract.md`, the compiled skill and `station_cli.py`). No page under `docs/` states the old exit at mint; the path is listed so one added later is caught. `SPEC.md` is not searched: it quotes the superseded wording on purpose.

  ```bash
  ! git grep -n -F -e 'says nothing about the delegated tool' -e 'exits 0 in every state' -e 'exits 0 whatever the build did' -- _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md .claude/skills/pyforge-mason/0.1.1 .claude/memory/project/2026-11-06-operator-rulings-on-wiring-the-seven-start-tools.md src/shared/packages/pyforge-mason/src src/shared/packages/django-pyforge docs/how-to docs/reference docs/explanation docs/tutorials
  ```

- **AC4 — `contract.md` and the compiled skill state the new rule.** Expected: exit 0 (exit 1 at mint). Both files carry the sentence the grep names, in the `EXIT_FAILED` row.

  ```bash
  grep -q -F 'a verb whose wrapped tool returned non-zero' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md && grep -q -F 'a verb whose wrapped tool returned non-zero' .claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md
  ```

- **AC5 — The code still matches the public contract, exit codes keep one owner, and the skill's meta-tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_public_contract.py src/shared/packages/pyforge-mason/tests/meta/test_exit_code_ownership.py src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py -q
  ```

- **AC6 — A failed build through `start_build` still fails its run by the build's own return code.** Expected: exit 0. `src/platform/tests/test_station_cli.py` holds a mason child that exits 1 with a report whose `data.returncode` is 1 to "the build exited 1" and its log tail, a child that exits 1 with no report to a failed verb, and a build that passed to a result. The file imports no `pyforge`.

  ```bash
  pixi run --frozen -e pyforge-guild platform-ci-local -- --test
  ```

- **AC7 — The mason chain is current.** Expected: exit 0. Run after the Spec's re-derive, the spine's dated note on AD-4 and the PRD's dated currency note.

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/chain_currency_sweep_check.py --project pyforge-mason --json
  ```

- **AC8 — The row is closed.** Expected: prints 1 and exits 0 (prints 0 and exits 1 at mint).

  ```bash
  grep -A 14 '^### DW-mason-41-1-1:' _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md | grep -c '^  status: closed'
  ```

- **AC9 — The package half, the live-tree half and the touched modules' unit floor.** Expected: each exits 0.

  ```bash
  pixi run --frozen -e pyforge-mason pyforge-mason-test
  pixi run --frozen -e pyforge-mason pyforge-mason-live-test
  pixi run --frozen -e pyforge-mason pyforge-mason-coverage-gate
  ```

- **AC10 — Lint and types.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-mason CAP-2 and CAP-5 (each amended 2026-11-25); AD-4 as amended 2026-11-25; reads `spec-pyforge-unifying-strategy:CAP-20` (no text change).
- Dream: `docs/dreams/pyforge-mason.md`, the 2026-11-25 entry (a failed wrapped tool makes mason exit 1); operator ruling of 2026-11-25, "Exit 1 on failure".
- Epic: Epic 42, minted with this story.
- Ledger key: `42-1-a-failed-wrapped-tool-makes-mason-exit-1`.
- Deferred-work row: `DW-mason-41-1-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."42"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date. Not implemented. Prepared and not applied: the Spec amendment (CAP-2, CAP-5 and the "Subprocess only" constraint) and the spine's dated note on AD-4.
- 2026-11-25: implemented, Mason's package and `contract.md` only. Reproduced: `-k failed_wrapped_tool` written first, 8 failed and 9 passed on the unchanged `cli.py` (each of `recipe build`, `diagnose`, `optimize`, `scan`, `update` and `submit`, and `package build` once per engine, exited 0 on a failed wrapped result). Changed: `cli.py` projects the return code (`recipe build`, `diagnose`, `optimize`, `scan`, `update`; `package build` on either engine) or the ship state (`recipe submit`) through `EXIT_OK` / `EXIT_FAILED`, with the envelope untouched; its comments, the `_dispatch_package_ship` docstring, two docstrings in `recipe.py` and `EXIT_FAILED`'s in `exit_codes.py` state the rule. Tests that pinned the old exit and now expect `EXIT_FAILED`: `test_wrapped_tool_exit_is_the_one_the_contract_table_states` (five recipe rows), `test_recipe_build_failed_child_still_renders_ok`, `test_package_build_failed_child_still_renders_ok`, and seven `recipe optimize` tests whose fixture returns CFE's suggestion exit 1 (`..._text_mode_renders_the_cfe_result_fields`, `..._json_mode_data_matches_dataclasses_asdict_of_the_result`, `..._passes_recipe_path_and_resolved_flags_through`, `..._resolves_cfe_timeout_flag_via_the_shared_resolver`, `..._cfe_timeout_env_var_applies_without_the_flag`, `..._cfe_timeout_defaults_to_none_when_unset`, `..._against_fake_cfe_root_end_to_end`). `contract.md`: the `EXIT_OK` and `EXIT_FAILED` rows, the envelope's `data` bullet, § *Ship states* and the `run_build` paragraph. Verified: AC1 exit 0 (17 passed); AC5 exit 0 (63 passed); AC9 exit 0 three times (1725 passed; 73 + 2 + 12 passed; the coverage gate saw no touched module, the tree being uncommitted); AC10 exit 0. Not done here, left to the lead: the compiled skill (AC3 and AC4 still exit 1 on it), `station_cli.py` and its platform test (AC6), the Spec re-derive, the spine and PRD notes (AC7), and the ledger row (AC8).
- 2026-11-25: review findings closed (second pass). `django_pyforge.station_cli`: the mason `start_build` row takes `result_codes` of 0 and 1, so a failed build with a report reaches `_judge_build`, which fails the run by the build's own return code and the tail of its log; its docstring says what Mason now does. Test first in `src/platform/tests/test_station_cli.py`: the pinned row's codes become `{0, 1}`, the failed-build case fakes `exit 1` with `data.returncode` 1, a new case holds exit 1 with no report to a failed verb, and a new case holds a passing build to a result; 3 failed on the unchanged row, then 90 passed, run against a throwaway PostgreSQL from the `platform-dev` environment on 127.0.0.1:25471 (torn down). The compiled station skill is regenerated by `skf-update-skill` (headless, from the module copy) as version 0.1.1, beside 0.1.0, which the tool keeps unchanged; `active` points at 0.1.1, and its `EXIT_OK` and `EXIT_FAILED` rows, the `run_build` row, the CI gate, the envelope `data` bullet, the ship-state exits and the dispatch rule match `contract.md`. Not exported: the AGENTS.md SKF block and `.claude/skills/.export-manifest.json` still name 0.1.0 until `skf-export-skill` runs. AC3 now searches `.claude/skills/pyforge-mason/0.1.1` and the team-memory entry in place of the whole skill group: the skill-forge version model keeps every earlier version folder unchanged, as the doctor, marshal and steward skill groups do, so 0.1.0 keeps the old wording as a record. Docstrings in `cli.py`, `exit_codes.py` and `recipe.py` that stated the rule as every wrapping verb's now name the verbs as `contract.md`'s `EXIT_FAILED` row does (`recipe new` raises; a `recipe submit` dry run exits 0). The team-memory entry of 2026-11-06 no longer states the old exit as a live trap. Surface widened to `exit_codes.py`, `recipe.py` and that memory entry.
- 2026-11-25: closed. Implemented, independently reviewed against this spec, its findings applied and re-reviewed; the full local `pr-preflight` gates the PR that lands it (branch `open-rows-and-onboarding-2026-11-25`).
