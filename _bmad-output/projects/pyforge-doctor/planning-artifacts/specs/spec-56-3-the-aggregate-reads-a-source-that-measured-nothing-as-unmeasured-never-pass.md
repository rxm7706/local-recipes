---
title: '56.3: The aggregate reads a source that measured nothing as unmeasured, never pass'
type: 'fix'
created: '2026-11-10'
status: 'done'
story: 56-3-the-aggregate-reads-a-source-that-measured-nothing-as-unmeasured-never-pass
spec: spec-pyforge-doctor
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'scripts/detectors.py'
  - 'tests/scripts/test_detectors_doctor_sources.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/score.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_score.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_models.py'
  - 'docs/reference/judgement-vocabulary.md'
  - 'docs/how-to/run-and-understand-detectors.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A false green (audit MUST 1): the aggregate reads a row whose only findings say the source could not evaluate as `pass`.

**Approach:** One new row status word, `unmeasured`, with exit codes unchanged, so no source leaves `detectors-ci` and nothing is re-scoped (AD-15). Move `score._is_gather_failure` to `models.is_gather_failure`; `score.py` calls it. The text table's mark map gains `unmeasured: ○`. Story 56.4 makes each source say when it found no subject.

Ledger key: `56-3-the-aggregate-reads-a-source-that-measured-nothing-as-unmeasured-never-pass`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-93** — Doctor holds the verdict for every conformance detector; amended 2026-11-10 with the `unmeasured` clause.
- **`spec-pyforge-doctor` AD-15** — the aggregate reads a row that measured nothing as `unmeasured`, never `pass`; AD-2's warn rule binds `doctor` and the sources dispatcher.

## Boundaries & Constraints

**Always:**
- Keep the aggregate's exit codes `{0, 1, 2}`; `unmeasured` exits 0 (ruling of 2026-11-10: a warning the merge bar does not fail on).
- One predicate, public, in `models.py`; no second copy.

**Never:**
- Never move a source out of `detectors-ci` or change its scope; never make `unmeasured` fail the merge bar.
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — The aggregate's own suite, with the new cases.** Expected: exit 0; the -k run selects 6 or more: one unevaluable WARN reads status `unmeasured` with rc 0; a degrade_on_exception WARN reads `unmeasured`; () reads `pass`; a WARN about a real subject reads `pass`; a FAIL beside an unevaluable WARN reads `FINDINGS`; main() over pass and unmeasured rows returns 0, prints `○` for the unmeasured row and a summary line containing `measured nothing`.

  ```bash
  pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test && pixi run --frozen -e pyforge-doctor python -m pytest tests/scripts/test_detectors_doctor_sources.py -q -k unmeasured -p no:cacheprovider
  ```

- **AC2 — One predicate, public, in models.py.** Expected: prints 1 (the line is in models.py); the second command exits 1 (no match).

  ```bash
  git grep -n 'def is_gather_failure' -- src/shared/packages/pyforge-doctor/src | wc -l && git grep -n '_is_gather_failure' -- src/shared/packages/pyforge-doctor/src scripts/detectors.py
  ```

- **AC3 — Score and models tests.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_score.py src/shared/packages/pyforge-doctor/tests/unit/test_models.py -q -p no:cacheprovider
  ```

- **AC4 — On this tree no doctor row reads unknown and each reads a known word.** Expected: prints `29 []`, exit 0 (the whole-tree exit code is not this story's: other units' chains are mid-flight and capability-ledger reds by design until control-plane 121.3).

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/detectors.py --scope repo --json > "${TMPDIR:-/tmp}/doctor-detectors.json"; python3 -c "import json,os;r=json.load(open(os.environ.get('TMPDIR','/tmp')+'/doctor-detectors.json'))['results'];d=[x for x in r if x['path'].startswith('pyforge.doctor.sources:')];bad=[x['name'] for x in d if x['status'] not in ('pass','FINDINGS','unmeasured')];print(len(d),bad);raise SystemExit(1 if bad or len(d)!=29 else 0)"
  ```

- **AC5 — The generated detector page needs no change and the two hand-written pages name the new word.** Expected: docs-detectors exit 0 (registry rows did not change; nothing is written); grep prints a count of 1 or more for each file.

  ```bash
  pixi run --frozen -e pyforge-guild docs-detectors -- --check && grep -c unmeasured docs/reference/judgement-vocabulary.md docs/how-to/run-and-understand-detectors.md
  ```

- **AC6 — Rider: the phantom module name is gone from the files this story owns.** Expected: exit 1 (no match).

  ```bash
  git grep -n 'pyforge\.doctor\.sources\.fleet_scan' -- scripts/detectors.py src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py
  ```

- **AC7 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-56-3-*.md)"
  ```

- **AC8 — Lint, types and the doctor suite halves stay green.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types && pixi run --frozen -e pyforge-doctor pyforge-doctor-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-93 (amended 2026-11-10); FR-27 ← CAP-93.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 56, minted with this story.
- Ledger key: `56-3-the-aggregate-reads-a-source-that-measured-nothing-as-unmeasured-never-pass` (`backlog`).
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."56"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- Code is wrong (audit defect: a false green). Ruled 2026-11-10 (the second addendum): `unmeasured` is a warning and the merge bar does not fail on it; the plan's open question on failing closed is closed.
- Consumer: marshal's `cli/check.py` reads `pass`, `FINDINGS` and `unknown` and sends any other word to MRS-CHECK-001 (WARN-tier, never silently treated as clean), so `marshal check` warns, never errs, until marshal maps the word (marshal's shared request); no marshal test moves. No other code reads the status word.
- `docs/reference/detectors.md` is generated from the registry rows, which do not change here; Story 56.5 regenerates it.
- Rider: the phantom name at `models.py:240` and `scripts/detectors.py:13` becomes `scripts/fleet_scan.py`. `scripts/detectors.py` is on no Spec surface today (allowlist line 55); Story 57.3 puts it on doctor's.
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
