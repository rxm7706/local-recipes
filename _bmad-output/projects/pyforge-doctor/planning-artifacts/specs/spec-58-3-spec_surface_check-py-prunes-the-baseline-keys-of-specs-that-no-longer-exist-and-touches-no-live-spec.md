---
title: '58.3: spec_surface_check.py prunes the baseline keys of Specs that no longer exist, and touches no live Spec'
type: 'fix'
created: '2026-11-10'
status: 'backlog'
story: 58-3-spec_surface_check-py-prunes-the-baseline-keys-of-specs-that-no-longer-exist-and-touches-no-live-spec
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'scripts/spec_surface_check.py'
  - 'tests/scripts/test_spec_surface_prune.py'
  - 'scripts/memlog_fidelity_check.py'
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

**Problem:** Audit defect (orphaned baseline entries, measured): no sanctioned verb removes the dead keys. `chain_sprawl_baseline.py --prune` and `fr_baseline.py --prune` are the precedent.

**Approach:** Mirror the scoped stamp: `_baseline_lock()`, `_read_baseline()`, atomic write; `discover` is the same function the stamp uses, so 'live' means exactly what a stamp means by it. It removes keys only; the 87 untracked paths inside live keys are left to each live Spec's scoped stamp in Story 58.4. The test monkeypatches REPO_ROOT and BASELINE to tmp_path (stdlib only, pyforge-ci).

Ledger key: `58-3-spec_surface_check-py-prunes-the-baseline-keys-of-specs-that-no-longer-exist-and-touches-no-live-spec`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-59** — the `--write-baseline` race is closed; amended 2026-11-10 with the `--prune` clause.

## Boundaries & Constraints

**Always:**
- Remove keys only; never edit a live Spec's entry.

**Never:**
- Never run the prune on the real baseline in this story; never touch a CFE file (no CFE retro is due).
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — The prune's cases, in the stdlib-only scripts lane.** Expected: exit 0, 6 or more: a dead key is removed and printed; every live key stays byte-identical; zero discovered Specs over a non-empty baseline exits 1 and leaves the file untouched; a corrupt baseline exits 1 untouched; `--prune --spec X` is a usage error (exit 2); a second prune removes nothing.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_spec_surface_prune.py -q -p no:cacheprovider
  ```

- **AC2 — The whole scripts lane and the two existing readers of the script.** Expected: exit 0 for all three (no CFE file is edited, so no CFE retro).

  ```bash
  pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test && pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_spec_surface_stamp.py -q -p no:cacheprovider && pixi run --frozen -e pyforge-guild python -m pytest .claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py -q -p no:cacheprovider
  ```

- **AC3 — The verb is offered and the real baseline is untouched by this story.** Expected: prints 1 or more; the diff exits 0 (58.4 runs the prune).

  ```bash
  python scripts/spec_surface_check.py --help | grep -c -- '--prune'; git diff --exit-code origin/main -- scripts/.spec-surface-baseline.json
  ```

- **AC4 — The fidelity script says where currency is checked.** Expected: prints 1 or more.

  ```bash
  grep -c 'test_spec_not_behind_memlog' scripts/memlog_fidelity_check.py
  ```

- **AC5 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-58-3-*.md)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-59 (amended 2026-11-10: the `--prune` clause); FR-33 ← CAP-59.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 58, minted with this story.
- Ledger key: `58-3-spec_surface_check-py-prunes-the-baseline-keys-of-specs-that-no-longer-exist-and-touches-no-live-spec` (`backlog`).
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."58"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- `spec_surface_check.py` is realized under CAP-59 (the stamp race) and allowlisted as a mutation-only residual (`scripts/spec_surface_allowlist.txt:31`); it sits on no Spec surface.
- memlog_fidelity_check.py rider (scribe's request, needed by scribe Story 32.3): the docstring says the tool checks that a memlog exists and diffs a scratch re-derive, and that currency and capability coverage are scribe's `tests/meta/test_spec_not_behind_memlog.py` (spec-pyforge-scribe:CAP-35); no behaviour change; the script is allowlisted (steward Story 44.13) and no Spec governs it.
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
