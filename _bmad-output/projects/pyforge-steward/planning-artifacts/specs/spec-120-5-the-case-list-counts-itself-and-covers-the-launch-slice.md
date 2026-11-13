---
title: '120.5: The case list counts itself and covers the Launch slice'
type: 'chore'
created: '2026-11-10'
status: 'done'
difficulty: medium
story: 120.5
spec: foundry-regenerate-not-fold
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md
  - src/shared/packages/pyforge-steward/tests/meta/test_cutover_case_list.py
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/ab-sync.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Ruling 3 (the Launch slice's A tests are the oracle) and an audit defect: the count line says 38 and the table has 40, and nothing checks it. Herald asked for its slice. The meta-test is new; no product code changes.

**Approach:** Correct the count (40 today: 3 estate, 18 core, 10 steward, 9 marshal), add herald's seven rows (nodeids in herald's request, verified present 2026-11-10) and one row per `launch-slice.md` step whose A test exists. The meta-test is `pytestmark = pytest.mark.live_tree`; it resolves nodeids statically (file exists, `def <name>`), reads `launch-slice.md`'s nodeid column, and holds the planted-count case inside the test on a `tmp_path` copy, so no tracked file is mutated. `k-steward-no-flip` keeps its nodeid (Story 121.2 keeps that test).

Ledger key: `120-5-the-case-list-counts-itself-and-covers-the-launch-slice`. Type / Effort / Deps: chore / M / S-120.1.

### Living CAP citations

- **`spec-foundry-regenerate-not-fold`** — fnr:CAP-1 (the case list is the Launch slice's oracle) to fnr:CAP-5 (A writes until the flip), amended 2026-11-10 and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Record core-kit's note that `k-core-parity-verbs` reads `_bmad-output` (live tree) in that row's note.

**Never:**
- Never mutate a tracked file from the test.
- Never fill an oracle gap here (DW row at build).

## Acceptance Criteria

- **AC1 — the count line equals the rows and every nodeid resolves.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_cutover_case_list.py -q -m live_tree -p no:cacheprovider
  ```
- **AC2 — the count check fires on a planted count.** Expected: exit 0, 1 test selected (it copies case-list.md under tmp_path, plants a wrong count and asserts the check reports it).
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_cutover_case_list.py -q -m live_tree -k planted_count -p no:cacheprovider
  ```
- **AC3 — every launch-slice step with an A test has a case row.** Expected: exit 0, at least 1 test selected.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_cutover_case_list.py -q -m live_tree -k launch_slice -p no:cacheprovider
  ```
- **AC4 — herald's slice is present.** Expected: 7.
  ```bash
  grep -c '^| k-herald-' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md
  ```
- **AC5 — doctor's case-list reader reads the same rows the count line states.** Expected: prints two equal numbers of 47 or more, exit 0.
  ```bash
  pixi run -e pyforge-guild python -c "import re;from pyforge.doctor.sources.capability_ledger import parse_case_list_ids as p;t=open('_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md').read();n=len(p(t));m=int(re.search(r'\*\*Count:\*\* (\d+) rows',t).group(1));print(n,m);raise SystemExit(0 if n==m>=47 else 1)"
  ```

</intent-contract>

## Binding

Parent: `spec-foundry-regenerate-not-fold` fnr:CAP-1

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 120.
- Ledger key: `120-5-the-case-list-counts-itself-and-covers-the-launch-slice` (`backlog` at mint).
- Deps: S-120.1.
- Surface: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md`, `src/shared/packages/pyforge-steward/tests/meta/test_cutover_case_list.py`.
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_cutover_case_list.py -q -m live_tree -p no:cacheprovider` — expected: exit 0.

## Notes

- Cross-station: herald:S-52.1 and marshal:S-117.1 asked for their rows.
