---
title: '121.6: The ledger check refuses a row that contradicts its Spec or the rules'
type: 'feature'
created: '2026-11-10'
status: 'backlog'
flag-exempt: detector-or-gate
difficulty: heavy
story: 121.6
spec: foundry-capability-ledger
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cutover_ledger_check.py
  - src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py
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

<intent-contract>

## Intent

**Problem:** fcl:CAP-1's written rules and fcl:CAP-2's `flip` form need a judge, and review found that a marker the generator does not recognise would silently keep a row at rebuild. A separate module, so the generator and the rules are each one reviewable change.

**Approach:** `rebuild-never-built`: a `rebuild` row whose Spec heading reads `(ready` and none of whose citing stories (the stories in that station's `epics.md` whose FR/AD or Parent line names the capability) reads `done` in that station's sprint-status-ledger.yaml (ruling 3; the second addendum settles the row: B-only when a live blocked or backlog Story carries it, else retire). Expiry form only (dates and Story keys are doctor's clock); `flip-expiry-lapsed` reads `pyforge.core.cutover_root.root_of_record()` and tests pass an explicit flags path. `retire-without-marker`: a `retire` row whose Spec heading has no retired marker (fnd:CAP-7's legacy form counts). `marker-contradicts-mode`: a retired marker on a row that is not `retire`. `unknown-marker`: a parenthesised status word (`minted`, `unbuilt`, `deleted`, `never built`, `retired` with no date) outside the pinned forms. Case ids are read from `case-list.md` with the first-column rule doctor uses.

Ledger key: `121-6-the-ledger-check-refuses-a-row-that-contradicts-its-spec-or-the-rules`. Type / Effort / Deps: feature / L / S-121.1.

### Living CAP citations

- **`spec-foundry-capability-ledger`** — fcl:CAP-1 (schema v1 and the written rules) and fcl:CAP-2 (the refusals and the expiry clock), amended 2026-11-10 and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Dates and Story-key expiries are doctor's (spec-pyforge-doctor:CAP-95, doctor Story 56.2); this module judges the form.

**Never:**
- Never write the ledger.
- Never import another station.
- Never append a `Surface reconcile` line or stamp.

## Acceptance Criteria

- **AC1 — the rules' unit tests.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider
  ```
- **AC2 — every finding and warning code is named by a test.** Expected: prints 27 or more and [], exit 0.
  ```bash
  python3 -c "import re;s=open('src/shared/packages/pyforge-steward/src/pyforge/steward/cutover_ledger_check.py').read();t=open('src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py').read();codes=set();[codes.update(re.findall(r'\"([a-z]+(?:-[a-z]+)+)\"',s.split(k)[1].split(')')[0])) for k in ('FINDING_CODES','WARNING_CODES')];miss=sorted(c for c in codes if c not in t);print(len(codes),miss);raise SystemExit(0 if len(codes)>=27 and not miss else 1)"
  ```
- **AC3 — a flip expiry lapses only when the root of record is foundry.** Expected: exit 0, at least 2 tests selected.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider -k flip_expiry
  ```
- **AC4 — an unrecognised marker is a finding, a missing one a warning.** Expected: exit 0, at least 2 tests selected.
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider -k 'unknown_marker or no_marker'
  ```
- **AC5 — package half, coverage, lint.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json && pixi run -e pyforge-steward pyforge-steward-coverage-gate && pixi run -e pyforge-guild lint-types
  ```
- **AC6 — a rebuild row nothing built is a finding.** Expected: exit 0, at least 2 tests selected (a `(ready` row whose only citing story is blocked fires; the same row with one done story is silent).
  ```bash
  pixi run -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider -k rebuild_never_built
  ```

</intent-contract>

## Binding

Parent: `spec-foundry-capability-ledger` fcl:CAP-1, fcl:CAP-2

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 121.
- Ledger key: `121-6-the-ledger-check-refuses-a-row-that-contradicts-its-spec-or-the-rules` (`backlog` at mint).
- Deps: S-121.1.
- Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/cutover_ledger_check.py`, `src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py`.
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cutover_ledger_check.py -q -p no:cacheprovider` — expected: exit 0.

## Notes

- Cross-station: marshal:S-117.2 (`root_of_record()`) must land first; doctor:S-56.2 judges the expiry clock.
