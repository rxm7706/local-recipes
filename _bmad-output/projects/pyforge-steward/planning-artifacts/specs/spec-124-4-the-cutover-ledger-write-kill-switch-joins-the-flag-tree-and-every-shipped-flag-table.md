---
title: '124.4: The cutover-ledger write kill switch joins the flag tree and every shipped-flag table'
type: 'chore'
created: '2026-11-10'
status: 'backlog'
difficulty: easy
story: 124.4
spec: python-foundry-cutover
surface:
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - src/shared/packages/pyforge-core/tests/unit/test_flags.py
  - src/platform/tests/test_openfeature_file_flags.py
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** No story of any unit plan registered the key 121.1 and 121.2 declare (team memory: a new feature flag must join three shipped-flag tables).

**Approach:** Shared-surface data edit in the four places `docs/reference/story-spec-flag-block.md` lists; runs early (BUILD-1) because 121.1 and 121.2 declare the key. core-kit 117.7 then splits the hermetic reader tests out of test_flags.py and leaves these tables in place.

Ledger key: `124-4-the-cutover-ledger-write-kill-switch-joins-the-flag-tree-and-every-shipped-flag-table`. Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-python-foundry-cutover` fnd:CAP-9** — `steward cutover plan`'s two write modes sit behind `pyforge.steward.cutover_ledger_write` (control-plane Stories 121.1 and 121.2); no text change.

## Boundaries & Constraints

**Always:**
- Register exactly the values control-plane's request declares.

**Never:**
- Never add another key or change another key's values.
- Never import a pyforge module in test_openfeature_file_flags.py.
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — the key is in the tree with the declared defaults.** Expected: exit 0; prints `on`.
  ```bash
  python3 -c "import json;d=json.load(open('src/platform/config/flags.json'));f=d['flags']['pyforge.steward.cutover_ledger_write'];print(f['defaultVariant'])"
  ```
- **AC2 — core's shipped tables name it.** Expected: prints a number >= 1.
  ```bash
  grep -c 'pyforge.steward.cutover_ledger_write' src/shared/packages/pyforge-core/tests/unit/test_flags.py
  ```
- **AC3 — the platform table names it.** Expected: prints 1.
  ```bash
  grep -c 'pyforge.steward.cutover_ledger_write' src/platform/tests/test_openfeature_file_flags.py
  ```
- **AC4 — core flag tests pass.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/unit/test_flags.py -q
  ```
- **AC5 — flag gate is green for the two stories that declare the key.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check
  ```
- **AC6 — Platform CI's test job, replayed locally, reads the new key in _SHIPPED_BOOLEANS.** Expected: exit 0 (Platform CI's `test` job runs raw pytest, which pr-preflight does not replay).
  ```bash
  pixi run --frozen -e pyforge-guild platform-ci-local -- --test
  ```

</intent-contract>

## Binding

Parent: `spec-python-foundry-cutover` fnd:CAP-9

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 124.
- Ledger key: `124-4-the-cutover-ledger-write-kill-switch-joins-the-flag-tree-and-every-shipped-flag-table` (`backlog` at mint).
- Deps: —.
- Surface: `src/platform/config/flags.json`, `src/platform/config/flag-overlays.json`, `src/shared/packages/pyforge-core/tests/unit/test_flags.py` (the shipped tables `_SHIPPED_CLOCKS`, `expected`/`per_environment` and `_LATER_KILL_SWITCHES` only), `src/platform/tests/test_openfeature_file_flags.py` (`_SHIPPED_BOOLEANS` only).
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `python3 -c "import json;d=json.load(open('src/platform/config/flags.json'));f=d['flags']['pyforge.steward.cutover_ledger_write'];print(f['defaultVariant'])"` — expected: exit 0; prints `on`.
- `grep -c 'pyforge.steward.cutover_ledger_write' src/shared/packages/pyforge-core/tests/unit/test_flags.py` — expected: prints a number >= 1.

## Notes

- Cross-station: marshal:S-117.7 (core-kit) follows it on test_flags.py. This key replaces the earlier plan for 124.4 (moving core's hermetic flag tests), which core-kit Story 117.7 carries.
- Surface: flags.json and src/platform/** are on spec-pyforge-unifying-strategy's surface and test_flags.py on spec-pyforge-core's and spec-pyforge-marshal's; their reconcile events are written by closers 122.5, marshal 117.8 and marshal 116.5 and the stamps by doctor 58.4.
- The kill switch is a new verb mode's switch, not a retrofit: the 2026-11-11 decision on the `spec-python-foundry-cutover` memlog reads the second addendum's ruling 5 ('No retrofit kill switch is added') as forbidding only switches retrofitted onto capabilities already shipped, so `pyforge.steward.cutover_ledger_write` stays (registered by Story 124.4).
