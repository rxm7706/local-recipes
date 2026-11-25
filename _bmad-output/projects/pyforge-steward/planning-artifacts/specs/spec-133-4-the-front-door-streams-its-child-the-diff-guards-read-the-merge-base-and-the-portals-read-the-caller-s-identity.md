---
title: '133.4: The front door streams its child, the diff guards read the merge base, and the portals read the caller''s identity'
type: 'fix'
created: '2026-11-25'
status: 'in-review'
story: 133-4-the-front-door-streams-its-child-the-diff-guards-read-the-merge-base-and-the-portals-read-the-caller-s-identity
spec: spec-pyforge-unifying-strategy
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py'
  - 'src/shared/packages/pyforge-core/src/pyforge/core/process.py'
  - 'src/shared/packages/pyforge-core/tests/**'
  - 'src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py'
  - 'src/shared/packages/pyforge-testing-kit/tests/unit/test_branch_diff_guard.py'
  - 'src/shared/packages/django-marshal/src/django_marshal_portal/views.py'
  - 'src/shared/packages/django-herald/src/django_herald_portal/deck_export_routes.py'
  - 'src/shared/packages/django-atlas/src/django_atlas_portal/board.py'
  - 'src/platform/mcp_host/app.py'
  - 'src/platform/mcp_host/settings.py'
  - 'src/platform/deploy/charts/platform/templates/_helpers.tpl'
  - 'src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml'
  - 'docs/how-to/reach-a-station-mcp-endpoint.md'
  - 'src/platform/tests/**'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-review-2026-11-24-5` reports six defects in code no station ledger owns. A reviewer reported them; the session lead confirmed only the third.

1. `pyforge <station> ...` captures all child output, gives the child no stdin and resolves the script by bare name, so streaming and interactive verbs differ from the station's own CLI; a bad `PYFORGE_ENVIRONMENT` is a traceback (`pyforge-core/src/pyforge/core/dispatch.py:179,200-223`).
2. The testing kit's branch diff guards diff against the tip of the base, so a local branch behind `origin/main` reds for commits it lacks, and paths with spaces break (`pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py:110,127,155,187,224`).
3. `django-marshal` reads `request.idp_sub`, which nothing sets, so every caller runs as the subject `marshal-portal` and shares one rate-limit bucket (`django_marshal_portal/views.py:24-25`).
4. `django-herald`'s deck-export routes read roles from the session, skipping the live identity-provider re-read production wires (`django_herald_portal/deck_export_routes.py:51-63`).
5. The MCP sidecar does not call `authorize_station_scope`; protection rests on the network policy (`src/platform/mcp_host/app.py`).
6. `django-atlas/board.py` imports `pyforge.steward.dashboard` at module level (`django_atlas_portal/board.py:18-20`).

**Approach:** Reproduce each defect first with a test that fails on the unchanged tree, and record the failing test's name in the Spec Change Log. Then: hand the front door's child the caller's stdio (inherit it, or `exec` the child), resolve the script beside `sys.executable`, and turn a bad `PYFORGE_ENVIRONMENT` into one line and the usage code; diff against the merge base and read paths NUL-separated or otherwise whole; read the marshal portal's subject through the host's claims reader; resolve the deck-export roles through the configured claims getter; verify the station scope in the sidecar, and correct the how-to and the chart comments that say it runs no check. A defect the tree does not reproduce is recorded here as not a defect, and so is one a dated and named carve-out already covers: `spec-pyforge-unifying-strategy` records the atlas portal's import of `pyforge.steward.dashboard` under a test allow-list, so defect 6 is fixed only if that record no longer holds.

**Rulings (session lead, 2026-11-25):** defect 6 is not a defect: the carve-out holds, `board.py` is not changed, and the evidence is in the Spec Change Log. The sidecar's check makes three texts false, and this story corrects them: `docs/how-to/reach-a-station-mcp-endpoint.md` and the two chart comments (`_helpers.tpl`, `mcp-host-networkpolicy.yaml`) now say the sidecar verifies the forwarded assertion itself (`401` without one, `403` for another station's, `503` with no public key).

Ledger key: `133-4-the-front-door-streams-its-child-the-diff-guards-read-the-merge-base-and-the-portals-read-the-caller-s-identity`.

### Living CAP citations

- spec-pyforge-unifying-strategy CAP-5, CAP-6, CAP-12, CAP-4 and CAP-3 (realized, no text change); reads `spec-pyforge-core:CAP-11`, `spec-pyforge-marshal:CAP-272` and `spec-pyforge-testing-charter:CAP-3` (no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce before fixing: one failing test per defect, written first, kept as the regression test.
- The front door's exit code stays the child's own; its refusals keep their words and the usage code.
- The guards keep `refs/remotes/origin/main` as their default base and keep skipping, never raising, when the base is absent (`spec-pyforge-marshal:CAP-272`).
- The platform's tests live under `src/platform/tests/` and import nothing of `pyforge`.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never add a `pyforge` import to a file under `src/platform/`; the station suites' import guards red it.
- Never change core's or the kit's written public contract without the contract test and its companion moving with it; a fix that needs a new public name stops and is reported.
- Never put an access check behind a flag.
- Never fix a defect that did not reproduce.
- Never change `django_atlas_portal/board.py`: defect 6 is covered by its carve-out (ruling of 2026-11-25).
- Never leave a page or a comment saying the sidecar runs no check of its own.

## Acceptance Criteria

**Given** `DW-steward-review-2026-11-24-5` reports that `pyforge <station> ...` captures all child output, gives the child no stdin, resolves its script by bare name and shows a traceback on a bad `PYFORGE_ENVIRONMENT`; that the testing kit's guards diff against the tip of the base and break on paths with spaces; that `django-marshal` reads `request.idp_sub`, which nothing sets; that `django-herald`'s deck-export routes read roles from the session and skip the live re-read; that the MCP sidecar does not call `authorize_station_scope`; and that `django-atlas/board.py` imports `pyforge.steward.dashboard` at module level
**When** each of the first five is first reproduced by a test that fails on the unchanged tree, the sixth is checked against its carve-out, and then the front door hands its child the caller's stdio and resolves the script beside the running interpreter, the guards diff against the merge base, the marshal portal reads the subject through the host's claims reader, the deck-export routes resolve roles through the configured claims getter, and the sidecar verifies the station scope
**Then** a front-door child's output arrives as it is written and its stdin is the caller's, a bad `PYFORGE_ENVIRONMENT` is one line and the usage code, a branch behind its base is judged on its own changes and a path with a space is read whole, two callers of the marshal portal carry two subjects, a revoked role is refused on the deck-export routes at the next request, and a sidecar call outside the caller's station scope is refused
**And** a defect the tree does not reproduce, or one a dated and named carve-out already covers, is recorded on this spec as not a defect; no changed file under `src/platform/` imports `pyforge`; and core's, the kit's and every station's suite pass

- **AC1 — Defect 1: the front door streams, passes stdin, and refuses a bad environment in one line.** The tests fail by name on a child whose first line arrives only after it exits, a child that reads end-of-file where the caller gave input, a script resolved off `PATH` when one sits beside the interpreter, and a traceback on a bad `PYFORGE_ENVIRONMENT`. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/unit/test_dispatch.py -q
  ```

- **AC2 — Defect 1: core's suite passes, its public contract with it.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-core pyforge-core-test
  ```

- **AC3 — Defect 2: the guards read the merge base and whole paths.** The tests fail by name on a branch behind its base that reads the base's newer commits as its own changes, and on a changed path with a space that is split or lost. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-testing-kit pytest src/shared/packages/pyforge-testing-kit/tests/unit/test_branch_diff_guard.py -q
  ```

- **AC4 — Defect 2: the kit's suite passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test
  ```

- **AC5 — Defects 3, 4 and 5: the portals and the sidecar act for the caller.** New tests under `src/platform/tests/` fail by name on two marshal-portal callers sharing one subject, a deck-export request served on a role the identity provider no longer gives, and a sidecar call with no assertion, with another station's assertion, or with no verifier key that is served. Defect 6 has no test here: its carve-out covers it (AC7). Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild platform-ci-local -- --test
  ```

- **AC6 — Every station's suite passes** (core and the kit are surfaces every station imports). Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pyforge-station-tests
  ```

- **AC7 — Not a defect is written down.** For each of the six defects, the Spec Change Log names either the test that failed on the unchanged tree, or the command or record that showed the tree does not reproduce it and the words "not a defect". A defect recorded as not a defect has no AC above to meet. Expected: exit 0.

  ```bash
  grep -c -E "defect [1-6]: (reproduced|not a defect)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-133-4-the-front-door-streams-its-child-the-diff-guards-read-the-merge-base-and-the-portals-read-the-caller-s-identity.md
  ```

- **AC8 — The how-to and the chart comments say what the sidecar does.** No text on the story's surface says the sidecar runs no assertion check or has no auth of its own. Expected: exit 1 (no match).

  ```bash
  grep -rn -e "runs no assertion check" -e "no auth of its own" docs/how-to/reach-a-station-mcp-endpoint.md src/platform/deploy/charts/platform/templates src/platform/mcp_host src/platform/tests/test_chart_invariants.py
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-unifying-strategy CAP-5, CAP-6, CAP-12, CAP-4 and CAP-3 (realized, no text change); reads `spec-pyforge-core:CAP-11`, `spec-pyforge-marshal:CAP-272` and `spec-pyforge-testing-charter:CAP-3` (no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the review's lower-severity defects are reproduced, then fixed or closed); operator ruling of 2026-11-25.
- Epic: Epic 133, minted with this story.
- Ledger key: `133-4-the-front-door-streams-its-child-the-diff-guards-read-the-merge-base-and-the-portals-read-the-caller-s-identity`.
- Deferred-work row: `DW-steward-review-2026-11-24-5`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."133"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date. Not implemented.
- 2026-11-25: defect 1: reproduced and fixed - `test_the_front_door_streams_its_child_output_as_it_is_written`, `test_the_front_door_hands_its_child_the_callers_stdin`, `test_main_runs_the_script_beside_the_interpreter_not_one_off_path` and `test_main_bad_environment_is_one_line_and_the_usage_code` (`pyforge-core/tests/unit/test_dispatch.py`) and `test_run_inherit_stdio_leaves_the_output_on_the_callers_streams` (`tests/unit/test_process.py`) failed on the unchanged tree. `PosixProcess.run` takes a keyword-only `inherit_stdio`; `dispatch.main` uses it when no process is injected, prefers the script beside `sys.executable`, and answers a bad `PYFORGE_ENVIRONMENT` with one line and exit 2. No new public name.
- 2026-11-25: defect 2: reproduced and fixed - `test_a_branch_behind_its_base_is_judged_on_its_own_changes`, `test_a_branch_behind_its_base_still_reports_its_uncommitted_changes`, `test_a_changed_path_with_a_space_or_a_non_ascii_name_is_read_whole` and `test_unsanctioned_commits_reads_a_path_with_a_space_whole` (`pyforge-testing-kit/tests/unit/test_branch_diff_guard.py`) failed on the unchanged tree. The guards diff from `git merge-base <base> HEAD`, falling back to the base's tip when there is no common commit, and read path lists with `-z`.
- 2026-11-25: defect 3: reproduced and fixed - `src/platform/tests/test_marshal_loop_homes_portal.py::test_watch_report_carries_each_callers_own_subject` failed on the unchanged tree (`['marshal-portal', 'marshal-portal']`). `watch_report` reads the subject through `claims_from_request`.
- 2026-11-25: defect 4: reproduced and fixed - `src/platform/tests/test_herald_deck_exports.py::test_list_forbidden_once_the_idp_no_longer_gives_the_role` and `::test_list_requires_identity_when_the_idp_cannot_confirm_the_session` failed on the unchanged tree (200, not 403 and 401). `resolve_herald_roles` resolves a session's claims through `django_pyforge.roles.claims_from_request`, the configured claims getter.
- 2026-11-25: defect 5: reproduced and fixed - `src/platform/tests/test_mcp_host_sidecar.py::test_mcp_host_refuses_a_call_with_no_assertion`, `::test_mcp_host_refuses_an_assertion_minted_for_another_station` and `::test_mcp_host_refuses_when_no_verifier_key_resolves` failed on the unchanged tree (200 each). `mcp_host/app.py` calls `authorize_station_scope` on every station `POST`: 401 without an assertion, 403 for another station's, 503 with no public key. Under the ruling, `docs/how-to/reach-a-station-mcp-endpoint.md` (`verified: 2026-11-25`), the comments in `_helpers.tpl`, `mcp-host-networkpolicy.yaml` and `mcp_host/settings.py`, and the docstring of `_assert_mcp_host_network_policy_admits_web_only` now say so.
- 2026-11-25: defect 6: not a defect - the import at `django_atlas_portal/board.py:18-20` is covered by a dated, named carve-out that still holds: `spec-pyforge-unifying-strategy/SPEC.md` § "`pyforge.*` import carve-outs (2026-09-10, Story 48.7)" (lines 940-945, and line 917); the allow-list `_STATION_PYFORGE_ALLOWED["atlas"]` at `src/platform/tests/test_station_portal_shells.py:115`, enforced by `test_new_portals_are_client_only_and_projection`; and `src/platform/tests/test_host_board_row_isolation.py::test_atlas_vizro_cli_is_not_mounted_on_host_urlconf`, which asserts the two imports are present. Both tests pass; `board.py` is unchanged (session lead's ruling, 2026-11-25).
- 2026-11-25: the story is implemented and in review. Not run in this pass: AC5's full `platform-ci-local -- --test` and AC6's `pyforge-station-tests` (other stations are mid-edit in the shared worktree); the named platform tests, core's and the kit's package halves and steward's package half pass.
