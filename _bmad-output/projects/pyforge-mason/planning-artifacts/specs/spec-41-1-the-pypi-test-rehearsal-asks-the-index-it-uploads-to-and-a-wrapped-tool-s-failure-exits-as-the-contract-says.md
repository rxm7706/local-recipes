---
title: "41.1: The pypi-test rehearsal asks the index it uploads to, and a wrapped tool's failure exits as the contract says"
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 41-1-the-pypi-test-rehearsal-asks-the-index-it-uploads-to-and-a-wrapped-tool-s-failure-exits-as-the-contract-says
spec: spec-pyforge-mason
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/pypi_index.py'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/package.py'
  - 'src/shared/packages/pyforge-mason/src/pyforge/mason/cli.py'
  - 'src/shared/packages/pyforge-mason/tests/unit/test_pypi_index.py'
  - 'src/shared/packages/pyforge-mason/tests/unit/test_package.py'
  - 'src/shared/packages/pyforge-mason/tests/unit/test_cli.py'
  - '_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-mason.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-mason-review-2026-11-24-1` carries two findings of the repository review of 2026-11-24 (main `7da08791f3`). First, `pypi_index.py:50` holds one URL template, the pypi.org JSON index, and `package.py::ship_pypi` calls `version_exists` for the `pypi-test` target too and writes a `https://pypi.org/project/` reference for it. After a rehearsal that uploaded and a real upload that failed, a re-run asks pypi.org, hears 404, uploads to TestPyPI again, fails on a file that exists, and the rehearsal gate then holds pypi back for that version (reviewer-traced, not run). Second, the reviewer reported that `recipe build`, `scan`, `optimize`, `update` and `submit` exit 0 when the wrapped tool failed while `package ship --to conda-forge --yes` exits 1 on the same state; `cli.py` and `contract.md` § *Exit codes* record that exit as decided.

**Approach:**
- Reproduce first. Each defect gets a test that fails on the unfixed tree before any source line changes. A defect the tree does not reproduce is not fixed: it is recorded in this spec's change log as not a defect, with the command that showed it.
- Defect 1: `version_exists` takes the index base as a keyword whose default is pypi.org; `ship_pypi` derives the base from its `repository_url` through one mapping kept beside `_TESTPYPI_REPOSITORY_URL`, and builds the `terminal` reference and both messages from the same base. A repository URL with no known JSON index reads `pending` and uploads nothing: never an assumption in either direction.
- Defect 2: one parametrized test drives the five verbs through `main()` with a wrapped tool that ran and failed, and holds each exit code to `contract.md`'s exit-code table. Where the code and the table agree, the finding is recorded as not a defect. Where a verb's exit differs from the table, the code is brought to the table. Where the table does not cover a verb, `contract.md` gains the sentence and no code changes.
- Ruling of the session lead, 2026-11-25, after the independent review: defect 2 is closed as not a defect. `contract.md` § *Exit codes* states it (`EXIT_OK`: "For most verbs this says nothing about the delegated tool: read `data.returncode`"; `EXIT_FAILED` names `recipe validate`, `environment lock`, `environment check` and `package ship` alone; § *Ship states*: "`recipe submit` exits 0 in every state"), so neither `cli.py` nor `contract.md` changes. Whether a failed wrapped tool should project to exit 1 stays an operator decision outside this story, carried by `DW-mason-41-1-1`.
- The same ruling: `ship_pypi`'s docstring states what the code does. The two sentences the fix left stale (that `canonical` is the only difference between a real ship and a rehearsal, and that the already-shipped reference and the version check are pypi.org's) are corrected in place: the index base is the second difference, and the reference and the check take the index base of the upload repository.

Ledger key: `41-1-the-pypi-test-rehearsal-asks-the-index-it-uploads-to-and-a-wrapped-tool-s-failure-exits-as-the-contract-says`.

### Living CAP citations

- spec-pyforge-mason CAP-3 (realized, no text change), CAP-5 (realized, no text change); no AD moves.
- `spec-feature-flag-governance` Q1: a fix carries no flag.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep `urllib.request` in `pypi_index.py` alone, and keep `version_exists` from raising.
- Close the deferred-work row this story names with the commit that resolves it.
- Keep `ship_pypi`'s docstring true of the code: a sentence the fix makes false is corrected in place, never contradicted by an appended paragraph.

**Never:**
- Never change an exit code or add one: projecting a failed wrapped tool to exit 1 is an operator decision with its own Dream entry.
- Never reach a real index from a test; the package half runs with no network.
- Never add a flag, a ship target, an option or an environment variable.
- Never hand-edit a `SPEC.md` or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** `pypi_index.version_exists` builds its URL from the pypi.org JSON index alone, `ship_pypi` calls it for the `pypi-test` target and writes a `https://pypi.org/project/` reference for it, and the reviewer reported that `recipe build`, `scan`, `optimize`, `update` and `submit` exit 0 when the wrapped tool failed
**When** each defect is first reproduced by a test that fails on the unfixed tree, the version check takes the index base of the target it serves and the reference is derived from that base, and one test holds the five verbs' exit to `contract.md`'s exit-code table
**Then** a `pypi-test` target whose version TestPyPI already has reads `terminal` with a `test.pypi.org` reference and no upload, the `pypi` target after it is attempted, a `pypi` target still asks pypi.org, and a repository with no known JSON index reads `pending` with no upload
**And** `ship_pypi`'s docstring names the index base as the second difference between the two targets, defect 2 is recorded as not a defect in this spec's change log with `contract.md` § *Exit codes* as its evidence, and `DW-mason-review-2026-11-24-1` reads closed in its ledger with the commit that closed it

- **AC1 — Defect 1: the rehearsal's version check asks the index it uploads to.** Expected: exit 0 (exit 5 at mint: no such test). The selected tests are written first and fail on the unfixed tree; they cover the URL `version_exists` opens for each base, the `pypi-test` target reading `terminal` with a `test.pypi.org` reference and no `twine.upload` call, the `pypi` target after it being attempted, a `pypi` target still asking pypi.org, and an unknown repository reading `pending`. If the tree does not reproduce the defect, the tests that show it stay and the change log records it as not a defect.

  ```bash
  pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_pypi_index.py src/shared/packages/pyforge-mason/tests/unit/test_package.py -q -k rehearsal_index
  ```

- **AC2 — Defect 2: each recipe verb's exit on a failed wrapped tool is the one `contract.md` states.** Expected: exit 0 (exit 5 at mint: no such test). One parametrized test covers `recipe build`, `scan`, `optimize`, `update` and `submit` through `main()` with a non-zero wrapped return code, and `package ship` with a `failed` target. Every exit already matches the table (lead's ruling, 2026-11-25), so the change log records the finding as not a defect and the test stays as the pin.

  ```bash
  pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_cli.py -q -k wrapped_tool_exit
  ```

- **AC3 — Each defect has its verdict on record.** Expected: prints 2 and exits 0 (exit 1 at mint). The build appends one line per defect to *Spec Change Log* below, in the form `- <date>: defect 1: reproduced and fixed - <the test or command that failed on the unchanged tree>` or `- <date>: defect 2: not a defect - <evidence>`.

  ```bash
  grep -c -E '^- 2026-[0-9]{2}-[0-9]{2}: defect [12]: (reproduced and fixed|not a defect) - ' _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-41-1-the-pypi-test-rehearsal-asks-the-index-it-uploads-to-and-a-wrapped-tool-s-failure-exits-as-the-contract-says.md
  ```

- **AC4 — The code still matches the public contract, and no other module reaches the network.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/test_public_contract.py src/shared/packages/pyforge-mason/tests/meta/test_credential_isolation.py -q
  ```

- **AC5 — The package half and the touched modules' unit floor.** Expected: each exits 0.

  ```bash
  pixi run --frozen -e pyforge-mason pyforge-mason-test
  pixi run --frozen -e pyforge-mason pyforge-mason-coverage-gate
  ```

- **AC6 — Lint and types.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-mason CAP-3 (realized, no text change), CAP-5 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-mason.md`, the 2026-11-25 entry (the pypi-test rehearsal asks the index it uploads to); operator ruling of 2026-11-25.
- Epic: Epic 41, minted with this story.
- Ledger key: `41-1-the-pypi-test-rehearsal-asks-the-index-it-uploads-to-and-a-wrapped-tool-s-failure-exits-as-the-contract-says`.
- Deferred-work row: `DW-mason-review-2026-11-24-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."41"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date.
- 2026-11-25: defect 1: reproduced and fixed - `pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_pypi_index.py src/shared/packages/pyforge-mason/tests/unit/test_package.py -q -k rehearsal_index` exited 1 with 9 failed on the unchanged tree (the rehearsal asked pypi.org and wrote a pypi.org reference) and exits 0 with 9 passed after the fix. `version_exists` takes `index_base`; `ship_pypi` derives it from `repository_url` through `_INDEX_BASE_BY_REPOSITORY_URL`. The independent review then found two sentences of `ship_pypi`'s docstring stale; both are corrected in place.
- 2026-11-25: defect 2: not a defect - `pixi run --frozen -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/unit/test_cli.py -q -k wrapped_tool_exit` exits 0 with 6 passed on the unchanged tree: `recipe build`, `scan`, `optimize`, `update` and `submit` exit 0 with the failure as data and `package ship` with a `failed` target exits 1, as `contract.md` § *Exit codes* (`EXIT_OK`, `EXIT_FAILED`) and § *Ship states* ("`recipe submit` exits 0 in every state") state. No change to `cli.py` or `contract.md`. Ruling of the session lead, 2026-11-25. Projecting a failed wrapped tool to exit 1 remains an operator decision with its own Dream entry.
- 2026-11-25: AC3's line form and its grep take ` - ` in place of ` (`, the form the session lead set for the review-defect stories.
- 2026-11-25: the story is implemented and in review. Not yet done, at landing: the deferred-work row's `resolved` status with the closing commit, the ledger key, and the spec-surface reconcile.
- 2026-11-25: the station closer closed `DW-mason-review-2026-11-24-1` in the ledger's own form (`status: closed` with a `resolution:` line, branch `review-defects-2026-11-25`) and opened `DW-mason-41-1-1` for the operator's decision whether a failed wrapped tool projects to exit 1; the acceptance text reads `closed` where it read `resolved`, the word this ledger uses. Left to landing: the ledger key and the spec-surface reconcile.
- 2026-11-25: closed. PR #2385 merged as 080f89c4df (`Merge pyforge-steward/133-1 into main`) after its 51 CI checks passed and the full local `pr-preflight` exited 0 on 48 lanes; an independent reviewer read the diff against this spec before the merge, its findings were applied and re-reviewed.
