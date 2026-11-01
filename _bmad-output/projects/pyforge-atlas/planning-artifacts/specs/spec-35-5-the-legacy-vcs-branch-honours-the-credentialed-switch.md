---
title: "35.5: The legacy VCS branch honours the credentialed switch"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
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

Status: backlog (minted 2026-11-01 by the EGM fleet audit, marshal Story 113.7).

## Spec Change Log

- 2026-11-01: minted from the EGM audit's finding ATL-M-D4 at the operator's ruling of 2026-11-01 (fix the code to
  honour the switch; staging and production set it explicitly), as a fix under CAP-65 with no new CAP and no flag.

## Review Triage Log

- (none yet)
