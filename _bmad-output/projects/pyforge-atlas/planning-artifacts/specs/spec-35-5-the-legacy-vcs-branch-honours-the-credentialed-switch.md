---
title: "35.5: The legacy VCS branch honours the credentialed switch"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-35-1-one-opt-in-switch-and-github-authenticates.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-35-4-gitlab-codeberg-and-the-eight-registries-fill.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/credentials.py
  - src/shared/packages/pyforge-atlas/tests/unit/datasets/test_credentialed_switch.py
  - src/platform/config/flag-overlays.json
deferred: []
---

<intent-contract>

## Intent

**Problem:** with `pyforge.atlas.live_vcs_universe` off, a VCS host or registry request carries the catalog
credential whether or not the operator set `PYFORGE_ATLAS_CREDENTIALED=1`. Line numbers are at `03a7aff5d9`.

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py` `_request_kwargs` (:104-113)
  returns `{"load_args": {"timeout": ...}, "credentials": credentials}` on the flag-off branch, and
  `VcsHostSeedDataset.fetch_one` / `RegistryUpstreamDataset.fetch_one` (:394-409) hand that to `APIDataset`, which
  sends the pair as Basic auth. Only the flag-on branch reads the switch.
- The Spec Constraint *Public sources live by default; credentials only on the operator's opt-in* (2026-10-18) says a
  request that carries a credential runs only when the operator sets `PYFORGE_ATLAS_CREDENTIALED=1`, so with it
  unset no request carries a credential. The staging and production overlays in
  `src/platform/config/flag-overlays.json` read `pyforge.atlas.live_vcs_universe` off, so those environments take the
  branch that breaks it.
- `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_credentialed_switch.py` pins the send:
  `test_with_the_flag_on_a_host_or_registry_request_carries_a_no_op_auth_and_no_credential` asserts the flag-off
  `credentials` (:279-292), and `test_a_vcs_host_sends_its_credential_only_with_the_flag_off` (:293-315) expects the
  suite's autouse guard to refuse the flag-off request.
- EGM audit 2026-11-01, finding **ATL-M-D4** (gap check accepted, narrowed to this flag-off branch;
  `_bmad-output/projects/pyforge-atlas/planning-artifacts/research/egm-audit-2026-11-01.md`). Operator ruling
  2026-11-01: fix the code to honour the switch; staging and production set it explicitly.

**Approach:**
- On the flag-off branch, `_request_kwargs` passes the catalog credential only when
  `credential_switch.credentialed()` is true; otherwise it sends no credential, with the same no-op auth the flag-on
  path uses so `~/.netrc` stays out.
- The flag-on branch is byte-identical (Story 35.4's User-Agent, no credential).
- A staging or production run that means the credentialed request sets `PYFORGE_ATLAS_CREDENTIALED=1` explicitly for
  that run (operator ruling 2026-11-01); no gate, loop path or CI job sets it.
- Rewrite the two pinning tests to the Constraint and add a transport-fixture test that a flag-off request without
  the switch carries no credential.
- A `fix` under CAP-65: no CAP is minted and no flag is added (`spec-feature-flag-governance` Q1).

Ledger key: `35-5-the-legacy-vcs-branch-honours-the-credentialed-switch`. Type / Effort / Deps: fix / S / —.

## Acceptance Criteria

- **AC1 — No credential without the switch.** With `pyforge.atlas.live_vcs_universe` off and
  `PYFORGE_ATLAS_CREDENTIALED` unset (or any value but `1`), `_request_kwargs` returns no `credentials` key and a
  no-op auth; a `VcsHostSeedDataset` (gitlab) and a `RegistryUpstreamDataset` (npm) fetch over the transport fixture
  sends no `Authorization`, `Proxy-Authorization`, `PRIVATE-TOKEN` or `X-NuGet-ApiKey` header, and the autouse guard
  does not fire.
- **AC2 — The switch still opts in.** With the flag off and `PYFORGE_ATLAS_CREDENTIALED=1`, the flag-off branch
  passes the catalog credential as it does today.
- **AC3 — The flag-on path is unchanged.** With the flag on, `_request_kwargs` returns exactly what it returns at
  `03a7aff5d9`, with or without the switch.
- **AC4 — The pins follow the Constraint.** The two tests named in the Problem assert AC1 and AC2 instead of the
  unconditional send; each new assertion fails when the switch check is removed (mutation).
- **AC5 — Suite.** `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` passes.

## Boundaries & Constraints

**Always:**
- Read the switch at the fetch, through `credential_switch.credentialed()`, never at import (Story 35.1's rule).
- Keep a credential on its own host (AD-2); keep tokens out of logs, datasets and markers.

**Never:**
- Never set `PYFORGE_ATLAS_CREDENTIALED` in a test lane, gate or workflow; never change a flag overlay; never change
  the flag-on path; never add a flag or a CAP.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-atlas` CAP-65 (FR-73): "a request that carries a credential runs only when the
  operator sets `PYFORGE_ATLAS_CREDENTIALED=1` for the run", and the Spec Constraint of 2026-10-18. No CAP is minted.

Parent: `spec-pyforge-atlas` CAP-65

- Audit finding carried: ATL-M-D4 (EGM audit 2026-11-01;
  `_bmad-output/projects/pyforge-atlas/planning-artifacts/research/egm-audit-2026-11-01.md`).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 35 (done; reopened by this story under doctor Story 41.5's rule).
- Ledger key: `35-5-the-legacy-vcs-branch-honours-the-credentialed-switch`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py`,
  `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_credentialed_switch.py`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); built later through `marshal factory dispatch`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` — expected: pass (the station's `verify_commands`; AC5).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_credentialed_switch.py src/shared/packages/pyforge-atlas/tests/unit/datasets/test_vcs_sources.py src/shared/packages/pyforge-atlas/tests/unit/datasets/test_hosts_and_registries.py -q` — expected: pass (AC1-AC4).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Run before the push:** AC4's mutation (drop the `credentialed()` check from the flag-off branch) fails the rewritten
tests; revert.

## Auto Run Result

Status: in-review (built 2026-11-01 in the landing worktree `egm-audit-2026-11`; not committed).

**What changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py` `_request_kwargs`: the flag-on
  branch is untouched. On the flag-off branch, `credential_switch.credentialed()` is read when the fetch runs. When it
  is true, the branch returns `{"load_args": {"timeout": t}, "credentials": credentials}` as before (AC2). Otherwise it
  returns `{"load_args": public_sources.request_args(t)}`, with no `credentials` key and the same no-op auth the
  flag-on path uses, so `~/.netrc` stays out (AC1). The docstring records the change.
- `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_credentialed_switch.py`: the two pinning tests are
  rewritten and renamed, because their old names stated the unconditional send.
  - `test_with_the_flag_on_a_host_or_registry_request_carries_a_no_op_auth_and_no_credential` is now
    `test_a_host_or_registry_request_carries_the_credential_only_with_the_flag_off_and_the_switch`, parametrized
    over the switch values unset, `""`, `0`, `true` and `1`. With the flag on, the result is byte-identical to
    `03a7aff5d9` whatever the switch is (AC3). With the flag off, only `1` gets the credential (AC1, AC2).
  - `test_a_vcs_host_sends_its_credential_only_with_the_flag_off` is now
    `test_a_vcs_host_or_registry_sends_its_credential_only_with_the_flag_off_and_the_switch`, parametrized over
    flag, switch and a gitlab host or npm registry. It runs over `fake_transport` with a `NETRC` file that holds
    credentials for both hosts. Only flag off with the switch on sends exactly the catalog pair as Basic auth, never
    the netrc entry. Every other case sends none of `Authorization`, `Proxy-Authorization`, `PRIVATE-TOKEN` or
    `X-NuGet-ApiKey`, and the autouse guard does not fire (AC1).
- No flag overlay, flag, CAP, gate, lane or workflow was touched. `PYFORGE_ATLAS_CREDENTIALED` is set only through
  `monkeypatch` inside the tests.

**Commands (exit codes read from `$?`):**
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_credentialed_switch.py src/shared/packages/pyforge-atlas/tests/unit/datasets/test_vcs_sources.py src/shared/packages/pyforge-atlas/tests/unit/datasets/test_hosts_and_registries.py -q`: exit 0 (136 passed).
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test`: exit 0 (3279 passed, 19 skipped / 217 passed, 1 skipped
  / 103 passed) (AC5).
- AC4 mutations were run as a scratch pytest plugin that swaps `vcs_sources._request_kwargs`. The source file was not
  edited in place.
  - `drop-check` (the pre-35.5 unconditional send): exit 1. Six tests fail: switch unset, `""`, `0` and `true`, plus
    the gitlab and npm transport cases with the flag off and the switch off, where the guard refuses.
  - `drop-noop-auth`: exit 1. The same six fail, because netrc's credential reaches the guard.
  - `never-send`: exit 1. Three tests fail: switch `1`, plus the gitlab and npm transport cases with the flag off and
    the switch on (AC2).
- `ruff check` / `ruff format --check` on the two files, run from the package dir with the guild ruff: exit 0 / exit 0.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.atlas` (the `lint-types` mypy slice, run from the package
  dir): exit 0 (150 files).
- `pixi run --frozen -e pyforge-guild lint-types`: exit 1. The failure is outside this story: an `I001` in
  `src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py`, which another agent has modified in this
  worktree. Atlas, django-atlas and every other package's ruff passed. The task stops after its ruff stage, so the
  atlas format and mypy slices were run directly (above).

**Review follow-up 2 (2026-11-01).** A later review (EGM audit, ATL-M-D4) found the same gap on another path. With
`pyforge.atlas.live_vcs_universe` off, `GitHubRequestDataset.save()` runs `fetch_repo_health`. Its
`_fetch_batch_with_retry` in `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/request_datasets.py` built
its request with `credentials=self._credentials`, whatever the switch said. The code and tests show that this gap was
latent, not a live send. kedro's `APIDataset.load()` refuses a POST before it sends anything, and
`test_flag_off_keeps_the_path_this_story_found` pins `sent == []` and an "Only GET" row. The path was still fixed, so
that the rule holds by construction and not because of how kedro handles a POST.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/credentials.py`: a new
  `catalog_request(timeout, credentials, /, **load_args)` now holds this story's flag-off rule in one place. With the
  switch, it returns `load_args`, the timeout and the credential, as before. Without it, it returns no credential and
  `public_sources.request_args`' no-op auth, so `~/.netrc` stays out. The switch is read when the request is built.
  The module docstring names the three call sites.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py` `_request_kwargs`: the flag-off
  branch returns `credential_switch.catalog_request(timeout, credentials)`. Its output is byte-identical, and this
  story's tests pass unchanged. The flag-on branch is untouched.
- `request_datasets.py` `_fetch_batch_with_retry`: the POST is built from
  `catalog_request(self._timeout_seconds, self._credentials, json=body)`.
- `request_datasets.py` `_RequestParameterizedAPIDataset.fetch_one` was found by the grep. GitHubRequestDataset and
  AnacondaDownloadsDataset inherit it. It passed `self._credentials` without the switch, and it now builds its request
  from `catalog_request`. The timeout is the catalog's `load_args` timeout, else `DEFAULT_REFRESH_TIMEOUT_SECONDS`
  (900 s); before, the request had none. For the catalog's GitHub entry, `fetch_one` never reached the network,
  because the entry is a POST. AnacondaDownloadsDataset has no catalog credential. But an instance built as a GET with
  a credential sent it as Basic auth without the switch.
- The grep covered every catalog entry with `credentials:`, plus each class's paths.
  - `vcs_gitlab_api_raw`, `vcs_codeberg_api_raw` and the npm, crates, rubygems and nuget registries go through
    `_request_kwargs`.
  - `vcs_github_api_raw` takes the two paths above, and with the flag on it uses `github_auth`.
  - `openteams_project_1_board_raw` and `discovery_staged_recipes_prs_raw` use `github_auth` only.
  - `pypi_bigquery_downloads_raw` discards its credential. Basilisk reads its token through `basilisk_auth`.
  - No other dataset is given a catalog credential. The core, JSON and PyPI request classes pass through a
    `credentials` argument their catalog entries never set. They were left as they are.
  - The base class's `self._inner` is built with the credential but never loaded: every subclass overrides `load()`.
- `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_credentialed_switch.py` has two new tests.
  - `test_the_flag_off_github_batch_hands_over_the_credential_only_with_the_switch` covers the switch unset, `""`,
    `0`, `true` and `1`. It records the `APIDataset` arguments that the flag-off `save()` batch builds, because the
    POST never reaches a transport. Only `1` gets the credential; every other value gets no credential and the no-op
    auth.
  - `test_a_request_dataset_fetch_one_sends_its_credential_only_with_the_switch` runs a GitHub request built as a GET
    and an AnacondaDownloadsDataset over `fake_transport`, with the switch off and on. A `NETRC` file holds
    credentials for both hosts. Only the switch sends the catalog pair, never netrc's, and the timeout is pinned.
- Commands (exit codes read from `$?`):
  - The new tests, run against the code before the change, exit 1. Eight fail: the four non-`1` batch cases and the
    two switch-off `fetch_one` cases, where the guard fires. The two switch-on `fetch_one` cases fail on the new
    timeout pin only.
  - After the change, the five dataset test files (`test_credentialed_switch.py`, `test_request_datasets.py`,
    `test_vcs_sources.py`, `test_hosts_and_registries.py` and `test_github_versions_health.py`) exit 0 (224 passed).
  - Mutants of `catalog_request` ran as a scratch pytest plugin, and each exits 1. `drop-check` fails 12 tests,
    `never-send` fails 6 and `drop-noop` fails 12.
  - `TMPDIR=$HOME/.cache/pyforge-preflight-tmp COVERAGE_FILE=$HOME/.cache/pyforge-preflight-tmp/atlas-cov/.coverage
    pixi run --frozen -e pyforge-atlas pyforge-atlas-test` exits 0 (3327 passed and 17 skipped, 221 passed and 1
    skipped, 103 passed).
  - From the package dir, the guild `ruff check` and `ruff format --check` on the four files exit 0 and 0. On
    `src tests` they also exit 0 and 0. `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.atlas` exits 0
    (150 files).
  - No flag, flag overlay, CAP, gate or workflow was touched.

## Spec Change Log

- 2026-11-01: minted from the EGM audit's finding ATL-M-D4 at the operator's ruling of 2026-11-01 (fix the code to
  honour the switch; staging and production set it explicitly), as a fix under CAP-65 with no new CAP and no flag.

## Review Triage Log

- 2026-11-01 (reviewer: independent session; read against this spec's ACs and Boundaries, not the Auto Run
  Result). Verdict: **pass**, no failures.
  - Diff read: `git diff HEAD` on `vcs_sources.py` and `test_credentialed_switch.py`; HEAD carries no atlas change
    since `03a7aff5d9`, so the flag-on return in `_request_kwargs` is byte-identical to `03a7aff5d9` (AC3). The
    flag-off branch reads `credential_switch.credentialed()` inside `_request_kwargs`, which is called from each
    `fetch_one`'s `_do_fetch`. The switch is read at the fetch, never at import. The only callers are the two
    `fetch_one` sites (`vcs_sources.py:405`, `:597`). No logging was added, and no credential moves to another host.
  - AC1: the parametrized `_request_kwargs` test asserts `{"load_args": public_sources.request_args(30)}` exactly,
    with no `credentials` key and the no-op auth, for the switch unset, `""`, `0` and `true`. The transport test runs
    gitlab and npm over `fake_transport`, with a `NETRC` that holds credentials for both hosts. It asserts that none
    of the four headers are sent, and the guard does not fire.
  - AC2: switch `1` with the flag off returns the catalog pair, and the transport test sees exactly the catalog pair
    as Basic auth, never netrc's credential.
  - AC4 mutations ran as a scratch pytest plugin that swaps `vcs_sources._request_kwargs`. The source was not edited.
    Each mutant was run over the three Verification test files, and each was killed: `drop-check` (the pre-35.5
    send) exits 1 with 6 failures, and the guard fires on the gitlab and npm transport cases. `drop-noop` (no
    no-op auth) exits 1 with 6 failures, because netrc's credential reaches the guard. `never-send` exits 1 with 3
    failures (AC2). `flag-on-changed` (the credential under the flag when the switch is set) exits 1 with 3
    failures (AC3). The unmutated baseline exits 0.
  - Verification: the three-file pytest exits 0 (136 passed). `pixi run --frozen -e pyforge-atlas
    pyforge-atlas-test` exits 0 (3279 passed and 19 skipped, 217 passed and 1 skipped, 103 passed) (AC5). The guild
    `ruff check` and `ruff format --check` on the two files, run from the package dir, exit 0 and 0. The atlas `ruff
    format --check src tests` exits 0, and `mypy -p pyforge.atlas` exits 0 (150 files).
  - `pixi run --frozen -e pyforge-guild lint-types` exits 1 on a ruff `I001` in
    `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py`. Another station's agent has
    modified that file in this worktree, so the failure is not this story's. `pyforge-atlas` and every other
    package passed ruff.
  - Boundaries: no flag overlay, flag, CAP, gate, lane or workflow sets or changes `PYFORGE_ATLAS_CREDENTIALED`. The
    only `+` lines that name it in the worktree diff are this spec and the `vcs_sources.py` docstring. The old test
    names are referenced nowhere but this spec's Problem.
  - Observation (not an AC failure): the module docstring in `datasets/credentials.py` still says "OFF, a dataset
    keeps the path it had before this story". That is now true of the flag-off VCS and registry branch only for the
    switch-on case, so the line is worth a touch the next time someone edits that file.
- 2026-11-01 (reviewer: independent session, review follow-up 2; read `git diff 03a7aff5d9` on `credentials.py`,
  `vcs_sources.py`, `request_datasets.py` and `test_credentialed_switch.py` against the ACs, Boundaries and the
  Constraint, not the follow-up's own account). Verdict: **pass**, no failures.
  - One rule: `credential_switch.catalog_request` is the only place a catalog credential handed to requests as the
    catalog gives it is gated. It reads `credentialed()` when the request is built. Its three callers are
    `vcs_sources._request_kwargs` (flag off), `GitHubRequestDataset._fetch_batch_with_retry` (no `auth`) and
    `_RequestParameterizedAPIDataset.fetch_one`. Every other credentialed request goes through a switch-gated auth:
    `github_auth` (the flag-on batch `_post`, `OpenTeamsBoardDataset`, `StagedRecipesPRDataset`), `gitlab_auth`
    (`VcsHostSeedDataset._get`) and `basilisk_auth`. `PyPIBigQueryDownloadsDataset` discards its credential.
  - Grep of `credentials=` and `APIDataset(` in `src/pyforge/atlas/datasets`. A `credentials` pass-through with no
    switch remains in `core_sources.py` (:706, :752, :794, :1028, :1098, :1144, :1184), `json_sources.py:79` and
    `PyPIJsonRequestDataset.fetch_one` (`request_datasets.py:1180`). None of them can get a catalog credential: the
    catalog's `credentials:` entries equal `CREDENTIAL_ALLOWLIST`, which
    `tests/unit/catalog/test_credential_scoping.py::test_credentials_attach_only_where_the_host_requires_them`
    pins, and no entry for those classes is on it. A credential added to one of them reds that test first.
    `incremental_parquet.py:132` and `degrading_parquet.py:41` are `ParquetDataset` storage options, not requests.
  - Flag on: `_request_kwargs`' flag-on return is byte-identical to `03a7aff5d9`. On the flag-off branch,
    `catalog_request(timeout, credentials)` returns exactly what this story's first build returned. The flag-on
    GitHub batch always has a `BearerAuth` and takes `_post`, which is unchanged. The base `fetch_one` has no flag
    branch, so its change applies in both states: the timeout, and without the switch no credential plus the no-op
    auth. No `src` code calls it. `AnacondaDownloadsDataset.load_many` and `GitHubRequestDataset.fetch_one` have no
    production caller, so no live request changes (observation, not a failure).
  - Timeout: `fetch_one` now passes the catalog `load_args` timeout, else `DEFAULT_REFRESH_TIMEOUT_SECONDS` (900 s,
    `refresh.py:91`); before, it passed none, an unbounded request. The positional-only `/` lets a catalog `timeout`
    in `load_args` pass through without a keyword clash. Nothing in `src` or the suite relies on an unbounded
    request.
  - The new tests fail without the change. `request_datasets.py` was taken from `03a7aff5d9` into a scratch
    `PYTHONPATH` copy, and the import was checked to resolve there; the tree was not edited. Run with the new
    tests, it exits 1 with 8 failures: batch switch unset, `""`, `0` and `true` (the pair is handed over);
    `fetch_one` switch-off on GitHub and Anaconda (the guard fires); and `fetch_one` switch-on (`[None] == [900]`,
    the timeout pin only). Batch `1` passes, as AC2 expects.
  - Mutants of `catalog_request` and the timeout default ran as a scratch pytest plugin over `tests/unit/datasets`.
    The baseline exits 0 (1298 passed). Every mutant exits 1: `drop-check` with 12 failures, `never-send` with 6,
    `drop-noop` with 12, `no-timeout` with 4, `batch-bypass` (only the batch keeps the old send) with 4, and
    `pre-change` with 14.
  - Commands (exit codes read from `$?`):
    - `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets -q`: exit 0
      (1298 passed).
    - From the package dir with the guild binaries, `ruff check` and `ruff format --check` on the four files exit 0
      and 0, and on `src tests` exit 0 and 0. `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.atlas` exits
      0 (150 files).
    - `TMPDIR=$HOME/.cache/pyforge-preflight-tmp pixi run --frozen -e pyforge-atlas pyforge-atlas-test`: exit 0
      (3327 passed and 17 skipped, 221 passed and 1 skipped, 103 passed) (AC5).
  - Boundaries: no flag overlay, flag, CAP, gate or workflow changes. The one workflow diff since `03a7aff5d9`
    (`pyforge-station-tests.yml`) only adds sparse-checkout paths. The only `+` line in `src` that names
    `PYFORGE_ATLAS_CREDENTIALED` is the `vcs_sources.py` docstring. No token is logged. The batch's failure text on
    the uncredentialed path is kedro's "Only GET" message.

## Dev Notes

- Review follow-up 2026-11-01 (the independent review's observation, EGM audit): the module docstring of
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/credentials.py` said "OFF, a dataset keeps the path
  it had before this story" with no exception. It now names the one this story made: the legacy VCS host and registry
  branch (`vcs_sources._request_kwargs`) reads the switch too, so its catalog credential rides only when
  `PYFORGE_ATLAS_CREDENTIALED=1`, and without it the request sends no credential and a no-op auth that keeps
  `~/.netrc` out. The change is to the docstring only; behaviour is unchanged. `test_credentialed_switch.py` exits 0,
  and the atlas suite, ruff and `mypy -p pyforge.atlas` exit 0 (recorded on spec-34-15's Dev Notes, the same run).
