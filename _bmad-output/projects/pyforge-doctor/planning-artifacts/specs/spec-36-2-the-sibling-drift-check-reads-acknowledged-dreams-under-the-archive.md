---
title: "36.2: The sibling-drift check reads acknowledged Dreams under the archive"
type: 'chore'
created: '2026-09-29'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the sibling-drift check (spec-pyforge-doctor CAP-71, extended by CAP-82) diffs the Dreams this repo shares
with `openteams-ai/mgmt-wf-python-modernization`, and honours a local `sibling-acknowledged:` hash. It builds its local side
in `sources/sibling_dreams.py::_local_fingerprints`, which reads only `docs/dreams/*.md`. Seven local Dreams carry an
acknowledgement: `pyforge-doctor` (live) and six archived ones (`package-inventory-eligibility`, `pixi-container-image`,
`django-accelerator-framework`, `enterprise-data-models-and-apis`, `miniforge-installer`, `reusable-cicd-workflows`).
`spec-one-chain-per-station` CAP-11 moves archived Dreams to `archive/docs/dreams/`. After that move, the check would stop
seeing those six, and their acknowledgements would stop suppressing the drift they were written for.

**Approach:** `_local_fingerprints` also reads `archive/docs/dreams/*.md`. When a slug exists in both places, the
`docs/dreams/` copy wins. Nothing else changes: the fingerprint, the acknowledgement rule and the messages stay as they are.
CHAIN-STANDARD §11 requires this before the first fold PR moves a file.

Ledger key: `36-2-the-sibling-drift-check-reads-acknowledged-dreams-under-the-archive`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-one-chain-per-station` CAP-11 (the Guild's; the Epic 34 relay shape, so no doctor CAP or FR); CHAIN-STANDARD §11.
- `spec-pyforge-doctor` CAP-71 and CAP-82 (the check being extended).
- `spec-feature-flag-governance` Q1: a `chore` needs no flag. This story keeps an existing check's output the same across a
  planned file move.

## Acceptance Criteria

- Given an acknowledged Dream fixture in `docs/dreams/` When the check runs Then it reports what it reports today (no change)
- Given the same Dream moved to `archive/docs/dreams/` When the check runs Then it reads the acknowledgement there and reports the same result as before the move
- Given one slug in both `docs/dreams/` and `archive/docs/dreams/` with different acknowledgement hashes When the check runs Then it uses the `docs/dreams/` copy
- Given no `archive/docs/dreams/` directory When the check runs Then it behaves as today
- Given today's `main` When the check runs Then its findings are unchanged
- Given the archive read is removed When the moved-Dream test runs Then it fails (mutation)

## Tasks

1. Read `sources/sibling_dreams.py` end to end and `tests/unit/test_sources_sibling_dreams.py`.
2. Extend `_local_fingerprints` to read `archive/docs/dreams/*.md` after `docs/dreams/*.md`, keeping the first copy of each
   slug. Keep its `OSError` handling.
3. Add tests for every acceptance criterion, on `tmp_path` fixtures (no network; the sibling side stubbed the way the
   existing tests stub it).
4. Run `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` and read the exit code.
5. Reconcile every Spec `spec-surface-check` names (`spec-pyforge-doctor`, and `spec-pyforge-core` as co-governor): memlog
   first, `git add`, then a scoped `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Keep the fingerprint and acknowledgement rules byte-for-byte.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not move any Dream in this story.
- Do not change the sibling repository coordinates or the fail-open paths (unreachable, unauthenticated).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dream in `docs/dreams/` | acknowledged | as today | — |
| Dream moved to the archive | acknowledged | same result as before the move | — |
| slug in both places | different hashes | `docs/dreams/` copy used | — |
| no archive directory | — | as today | — |
| unreadable file | `OSError` | skipped, as today | fail-open |

</intent-contract>

## Binding

Parent capability: `spec-one-chain-per-station` CAP-11 (Guild relay; no doctor CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `36-2-the-sibling-drift-check-reads-acknowledged-dreams-under-the-archive`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
