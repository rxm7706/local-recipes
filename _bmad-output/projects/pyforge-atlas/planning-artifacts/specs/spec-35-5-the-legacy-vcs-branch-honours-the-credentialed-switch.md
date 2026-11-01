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

## Dev Notes

- Review follow-up 2026-11-01 (the independent review's observation, EGM audit): the module docstring of
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/credentials.py` said "OFF, a dataset keeps the path
  it had before this story" with no exception. It now names the one this story made: the legacy VCS host and registry
  branch (`vcs_sources._request_kwargs`) reads the switch too, so its catalog credential rides only when
  `PYFORGE_ATLAS_CREDENTIALED=1`, and without it the request sends no credential and a no-op auth that keeps
  `~/.netrc` out. The change is to the docstring only; behaviour is unchanged. `test_credentialed_switch.py` exits 0,
  and the atlas suite, ruff and `mypy -p pyforge.atlas` exit 0 (recorded on spec-34-15's Dev Notes, the same run).
