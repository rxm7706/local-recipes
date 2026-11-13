---
title: '124.4: The cutover-ledger write kill switch joins the flag tree and every shipped-flag table'
type: 'chore'
created: '2026-11-10'
status: 'done'
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
- **AC5 — flag gate is green for the two stories that declare the key.** Expected: exit 0, but only once Story 121.2 (wave BUILD-4) writes its `read_boolean('pyforge.steward.cutover_ledger_write', default=True)` into `src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py`. Until then this story's own registration leaves a deferred red. It exits 1 with exactly one finding, `flag-key-orphan: ... tree key pyforge.steward.cutover_ledger_write is read by no tracked file under src/ or scripts/`. The same red fails the two live-tree tests in `tests/scripts/test_flag_gate_check.py` (`-k live_tree`): `test_every_key_the_live_tree_holds_is_read_in_src_or_scripts` and `test_the_live_tree_has_no_unknown_exemption_no_landed_key_missing_and_no_orphan`. Story 121.1's `cutover_ledger.py` does not read the key. See § Notes.
  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check
  pixi run --frozen -e pyforge-guild pytest tests/scripts/test_flag_gate_check.py -q -p no:cacheprovider -k live_tree
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
- Planned red window (recorded in fix round 1, 2026-11-11). This story registers the key in the tree and the shipped tables but adds no reader. A reader is new behaviour, and it belongs to Story 121.2. Only Story 121.2 (wave BUILD-4) reads the key, through `pyforge.core.flags.read_boolean('pyforge.steward.cutover_ledger_write', default=True)` in `cutover.py`. Story 121.1's `cutover_ledger.py` never reads it (epics.md Story 121.1's Flag line says "read by Story 121.2's verb"). The flag gate looks for readers among the tracked files under `src/` and `scripts/` (`git ls-files`) and reads each file's working-tree content. `cutover.py` is already tracked, so the orphan clears as soon as 121.2's edit is in the worktree, and the BUILD-4 wave gate commits it. Until then:
  - Wave gates BUILD-1, BUILD-2 and BUILD-3, and any full `pr-preflight` run on this branch, should expect exactly one `flag-gate-check` finding: `flag-key-orphan` on `pyforge.steward.cutover_ledger_write`.
  - They should also expect exactly two failures from `pytest tests/scripts/test_flag_gate_check.py -k live_tree`: `test_every_key_the_live_tree_holds_is_read_in_src_or_scripts` and `test_the_live_tree_has_no_unknown_exemption_no_landed_key_missing_and_no_orphan`. The file runs in the `scripts-lib-test` task (it is listed in `tests/scripts/scripts-lib-test.txt`), which the Detectors workflow's `scripts-suite` job and `pr-preflight` both call.
  - Any other finding or failure is a real red.
  - At the BUILD-4 wave gate, after 121.2, re-run both commands: each must exit 0. The plan owner should add them to the BUILD-4 gate or to Story 121.2's acceptance. This story's files cannot carry that change.

## Review findings (build, round 1, 2026-11-11)

1. **Major: AC5 and § Notes.** AC5 expected a plain exit 0, but `flag-gate-check` exits 1 on this tree with `flag-key-orphan: tree key pyforge.steward.cutover_ledger_write is read by no tracked file under src/ or scripts/`. The same red fails two live-tree tests in `tests/scripts/test_flag_gate_check.py` (`-k live_tree`, 2 failed). The spec never recorded that deferral.
   - **Fix:** AC5's Expected line and § Notes (*Planned red window*) now record it. The red clears only when Story 121.2 (BUILD-4) writes `read_boolean('pyforge.steward.cutover_ledger_write', default=True)` into `cutover.py`. Wave gates BUILD-1 to BUILD-3 expect exactly that one finding and those two test failures. Both commands are re-run at the BUILD-4 gate.
   - **No reader added:** a reader is Story 121.2's new behaviour.
   - **Two corrections to the reviewer.**
     - "Only once that file is committed": `cutover.py` is already tracked, and the gate reads the working-tree content of tracked files. So the orphan clears as soon as 121.2's edit is in the worktree, and the BUILD-4 gate commits it.
     - "Runs in the pyforge-station-tests CI lane": `tests/scripts/test_flag_gate_check.py` runs through the `scripts-lib-test` task (`tests/scripts/scripts-lib-test.txt`), which the Detectors `scripts-suite` job and `pr-preflight` call. The `scripts/flag_gate_check.py` line in `pyforge-station-tests.yml` is one of marshal's trigger paths. It does not run this test file.
   - The conclusion stands either way: every wave gate from BUILD-1 to BUILD-3, and any full preflight on this branch, reds on this one orphan.
2. **Minor: implementer report.** The report said AC5 goes green "after 121.1 or 121.2", and it left out the two live-tree test failures.
   - **Fix:** the reader is Story 121.2 alone. Story 121.1's `cutover_ledger.py` never reads the key (epics.md Story 121.1: "read by Story 121.2's verb"). Both live-tree tests are now named with the AC5 deferral.
