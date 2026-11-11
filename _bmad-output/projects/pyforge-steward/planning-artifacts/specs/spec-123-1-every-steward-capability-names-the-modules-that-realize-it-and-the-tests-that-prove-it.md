---
title: '123.1: Every steward capability names the modules that realize it and the tests that prove it'
type: 'feature'
created: '2026-11-10'
status: 'backlog'
flag-exempt: detector-or-gate
difficulty: heavy
story: 123.1
spec: pyforge-steward
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md
  - src/shared/packages/pyforge-steward/tests/meta/test_oracle_map.py
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The oracle is unusable as it stands: nothing says which tests prove which capability.

**Approach:** Bootstrap by script (test docstrings cite Story ids, Story FR/AD lines cite capabilities, the SPEC headings translate absorbed ids, contract.md gives verb to capability), then check by hand. About 60 to 90 rows. Host, chart and container capabilities read `platform`; recipe and channel capabilities `script` or `none` with a reason. The source-modules column is what Story 122.3's citation test reads.

Ledger key: `123-1-every-steward-capability-names-the-modules-that-realize-it-and-the-tests-that-prove-it`. Type / Effort / Deps: feature / L / S-120.5, S-121.1, S-121.2, S-121.3, S-121.6, S-121.7, S-122.2, S-123.2.

### Living CAP citations

- **`spec-pyforge-steward` CAP-181** — every capability names its source modules and the tests that prove it, and every test names a capability; minted 2026-11-10 `(ready 2026-11-10)` and rendered at mint.

## Boundaries & Constraints

**Always:**
- Build after every story of this PR that adds a steward test module outside this unit, so the map starts total.
- Judge totality and truth to the tree, never whether a test is sufficient.

**Never:**
- Never change code or a test body.
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — the map test passes.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_oracle_map.py -q
  ```
- **AC2 — the test can fire.** Expected: exit 0 with at least 4 tests selected (a capability with no row, a glob matching nothing, a proof value against the marker, an unnamed test module).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_oracle_map.py -q -k fires
  ```
- **AC3 — every capability has a proof value.** Expected: prints a count for each proof value in use; every `none` row carries a reason (asserted by the test).
  ```bash
  python3 -c "import re,collections;t=open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md').read();print(sorted(collections.Counter(re.findall(r'\b(package|live-tree|platform|other-station|script|attended|none)\b(?= *[|,])',t)).items()))"
  ```
- **AC4 — control-plane's four test modules are on the cutover rows.** Expected: prints 1 or more, and test_oracle_map names no control-plane module as unmapped.
  ```bash
  grep -cE 'test_cutover\.py|test_cutover_ledger\.py|test_cutover_case_list\.py|test_capability_ledger_live\.py|test_cutover\*' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md
  ```
- **AC5 — Post-condition (Story 124.2 runs it): the test reads only what steward's live job already fires on.** Expected: exit 0 once Story 124.2 has landed; red before it by design (other units' new reads).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q
  ```
- **AC6 — package half.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json
  ```
- **AC7 — live-tree half.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```
- **AC8 — lint and types.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-181

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 123.
- Ledger key: `123-1-every-steward-capability-names-the-modules-that-realize-it-and-the-tests-that-prove-it` (`backlog` at mint).
- Deps: S-120.5, S-121.1, S-121.2, S-121.3, S-121.6, S-121.7, S-122.2, S-123.2.
- Surface: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md` (new), `src/shared/packages/pyforge-steward/tests/meta/test_oracle_map.py` (new).
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_oracle_map.py -q` — expected: exit 0.
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_oracle_map.py -q -k fires` — expected: exit 0 with at least 4 tests selected (a capability with no row, a glob matching nothing, a proof value against the marker, an unnamed test module).

## Notes

- Cross-station: none. A later story of this unit that adds a steward test module owns its row through its dependency on this story (122.3 does: test_cap_citations.py).
- Story 121.7's live-tree test (`test_capability_ledger_live.py`) exempts the `rebuild-never-built` finding on `pyforge-steward:CAP-181`, this story's capability, by name while this story's ledger key is not `done`, because this story depends on 121.7; so this story's live-half run passes before it is marked done, and the exemption lapses once it is. The ledger row stays `rebuild`; Story 122.5 flips the marker and runs the check with no exemption.
- Until Story 124.2 lands, steward's trigger-map test may red on other units' new reads (a planned red window); this story is judged by its own test modules and by steward's package half without that module.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.
