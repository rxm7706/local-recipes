---
title: '121.1: A generator derives the capability ledger from the live Specs'
type: 'feature'
created: '2026-11-10'
status: 'done'
flag:
  key: pyforge.steward.cutover_ledger_write
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: "plan --regenerate and plan --append refuse with steward's usage code and write nothing; plan --check and flip are unchanged"
  cleanup: "90 days after ON in every environment (Q4) the owning station files the removal story"
difficulty: heavy
story: 121.1
spec: foundry-capability-ledger
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cutover_ledger.py
  - src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger.py
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-124.4).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).
>
> **Unblocked 2026-11-13.** Every story its Deps name is `done` on branch `cutover-readiness-2026-11-10`. The operator's "Start build" consent covered the unblock; CLOSE-LEDGERS moved the key to `done`.

<intent-contract>

## Intent

**Problem:** Ruling 2 makes `plan` the ledger generator fnd:CAP-9 promises, and none exists: the ledger is hand-edited and its headings rot. New module and tests; the verb is wired in Story 121.2, the rules in Story 121.6.

**Approach:** `live_specs(root)`, `extract_caps(text)` (heading forms `**CAP-n — title**`, `**CAP-n**`, `**pap:CAP-n — title**`, normalised as `extract.md` says), `cap_id(spec, n, prefix)` (fnd/fnr/fcl; `pap` only for a prefixed heading; else `<spec>:CAP-n`), `marker(line)` returning `('ready'|'shipped'|'retired', date)`, `('unknown', text)` or None, `regenerate(root, ledger)` and `append(root, ledger)`. Deterministic YAML: Specs by path, CAPs numeric, schema key order, expiry and dates as quoted strings through a str representer. The header gets generated_by `pyforge steward cutover plan`, updated, source_sha (HEAD the Specs were read at; `check` never compares it). Tests build fixture trees under `tmp_path` (package half, no marker). PyYAML is already a steward dependency.

Ledger key: `121-1-a-generator-derives-the-capability-ledger-from-the-live-specs`. Type / Effort / Deps: feature / L / S-120.1, S-120.2, S-124.4.

### Living CAP citations

- **`spec-foundry-capability-ledger`** — fcl:CAP-1 (schema v1 and the written rules) and fcl:CAP-2 (the refusals and the expiry clock), amended 2026-11-10 and re-derived at mint.
- **`spec-python-foundry-cutover`** — fnd:CAP-2, fnd:CAP-8 (the writer lock), fnd:CAP-9 (the ledger generator) and fnd:CAP-11, amended 2026-11-10 by memlog and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Read the flag only through Story 121.2's verb; the functions here take no flag.
- Steward's package half runs without `test_station_tests_trigger_map.py` until Story 124.2 lands (planned red window).

**Never:**
- Never import `pyforge.doctor`, `pyforge.scribe` or `pyforge.marshal`.
- Never read under `archive/`.
- Never append a `Surface reconcile` line or stamp: Story 122.5 and doctor Story 58.4 do.

## Acceptance Criteria

- **AC1 — the module's unit tests.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger.py -q -p no:cacheprovider
  ```
- **AC2 — named behaviours each have a test.** Expected: exit 0, at least 9 tests selected.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger.py -q -p no:cacheprovider -k 'idempotent or defaulted or prefixed_heading or unifying_id or commented_status or quoted_expiry or retired_marker or archive_ignored or orphan_dropped'
  ```
- **AC3 — a heading with a comment-carrying status is live.** Expected: exit 0, 1 test selected (fixture `status: ready   # note` is read as ready).
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger.py -q -p no:cacheprovider -k commented_status
  ```
- **AC4 — steward never imports another station for this.** Expected: 0.
  ```bash
  grep -c 'pyforge.doctor\|pyforge.scribe\|pyforge.marshal' src/shared/packages/pyforge-steward/src/pyforge/steward/cutover_ledger.py
  ```
- **AC5 — package half and coverage floor.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json && pixi run -e pyforge-steward pyforge-steward-coverage-gate
  ```
- **AC6 — lint and types.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

Parent: `spec-python-foundry-cutover` fnd:CAP-9; `spec-foundry-capability-ledger` fcl:CAP-1

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 121.
- Ledger key: `121-1-a-generator-derives-the-capability-ledger-from-the-live-specs` (`backlog` at mint).
- Deps: S-120.1, S-120.2, S-124.4.
- Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/cutover_ledger.py`, `src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger.py`.
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger.py -q -p no:cacheprovider` — expected: exit 0.
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover.py -q -p no:cacheprovider` — expected: exit 0. This module runs `pyforge.steward.cutover_ledger_write` in both states through the testing kit's `flag_states` (Story 121.2's verb is the one flag reader; integrator addition 2026-11-13, after the flag gate went red when CLOSE-LEDGERS moved this spec to `done`).

## Notes

- Spec surface: `src/shared/packages/pyforge-steward/**` is governed by spec-pyforge-steward and its `src/**` co-governed by spec-pyforge-core; their closers reconcile.
- The kill switch is a new verb mode's switch, not a retrofit: the 2026-11-11 decision on the `spec-python-foundry-cutover` memlog reads the second addendum's ruling 5 ('No retrofit kill switch is added') as forbidding only switches retrofitted onto capabilities already shipped, so `pyforge.steward.cutover_ledger_write` stays (registered by Story 124.4).
