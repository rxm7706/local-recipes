---
title: "32.3: A Spec that is behind its memlog reds scribe's live-tree suite"
type: 'feature'
created: '2026-11-10'
status: 'backlog'
flag-exempt: detector-or-gate   # a meta-test that judges; a gated gate reports a silent green (spec-feature-flag-governance Q2)
difficulty: 'medium'
story: 32-3-a-spec-that-is-behind-its-memlog-reds-scribe-s-live-tree-suite
spec: spec-pyforge-scribe
surface:
  - src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py
  - src/shared/packages/pyforge-scribe/tests/meta/data/spec_behind_memlog_known.json
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-32-3-a-spec-that-is-behind-its-memlog-reds-scribe-s-live-tree-suite.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - docs/dreams/pyforge-unifying-strategy.md
  - scripts/fleet_scan.py
  - scripts/memlog_fidelity_check.py
  - .github/workflows/pyforge-station-tests.yml
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Ruling 1 of 2026-11-10 makes Dream plus memlog the seed, including `archive/**/.memlog.md` (second
addendum, item 7), and audit SHOULD S6 found that Story 44.13's tool checks only that a memlog file exists. The
deterministic half of fidelity is small: an entry added to a memlog after its Spec was last rendered means the Spec is
behind. Nothing reds that today.

**Approach:** A test-only oracle in scribe's suite; no product code, no new verb, no new detector.

- For each live Spec folder (a `SPEC.md` whose status is not absorbed, archived or superseded: station Specs, declared
  seams and the Guild Specs under `docs/governance/`), C = `git log -1 --format=%H -- <folder>/SPEC.md`; old = the
  entries of `git show C:<folder>/.memlog.md`; an entry of the working-tree memlog that is not in old and is not
  bookkeeping is behind. No date is read from an entry's text or from frontmatter.
- Entries are parsed and classified with `_parse_memlog_body` and `_memlog_entry_is_bookkeeping` imported from
  `scripts/fleet_scan.py` (the suite's `PYTHONPATH` carries `scripts/`), so the repository keeps one definition of
  "the contract moved"; the tag is normalised as that function does (the kind is the text before ` by `).
- Known rows live in `tests/meta/data/spec_behind_memlog_known.json`: Spec folder → rows of `fingerprint` (the first 16
  hex digits of the SHA-256 of the entry line), `kind`, `committed` and `owner` (one of `atlas`, `doctor`, `herald`,
  `marshal`, `mason`, `scribe`, `steward-station`, `warden`, `core-kit`, `control-plane`, `governance`). The file only
  shrinks. The 24 rows of `docs/governance/spec-one-chain-per-station` and
  `docs/governance/spec-coverage-gate-independence` are owned by `control-plane`: steward Story 120.3 re-derives both
  (operator ruling 2026-11-10). Scribe's own Spec is judged with no known row.
- An uncommitted `SPEC.md` change counts as a render. In a shallow clone (CI checks out two commits) C collapses to the
  base tip or the head, so the rule judges exactly the entries the change under test added without a render, and the
  shrink rule runs only when `git rev-parse --is-shallow-repository` prints false (the local merge bar).
- The module carries `pytestmark = pytest.mark.live_tree`.

Ledger key: `32-3-a-spec-that-is-behind-its-memlog-reds-scribe-s-live-tree-suite`.
Type / Effort / Deps: feature (flag-exempt: detector-or-gate) / M / none.

### Living CAP citations

- `spec-pyforge-scribe` CAP-35, minted at the 2026-11-10 mint (`(ready 2026-11-10)`; FR-53). Story 31.2 flips it to
  `(shipped <date>)` once this story is built.

## Boundaries & Constraints

**Always:**
- Import the classifier from `scripts/fleet_scan.py`; define none.
- Judge every non-bookkeeping entry, events included.

**Never:**
- Do not re-derive a Spec; the LLM comparison stays `memlog-fidelity-check --compare`.
- Do not edit `scripts/memlog_fidelity_check.py` (doctor's; a docstring pointer is a shared request).
- Do not add a capability-entry ratchet: the seed includes the archived memlogs, with no backfill (operator ruling
  2026-11-10).

</intent-contract>

## Acceptance Criteria

- **AC1 — The live tree is clean against the known rows, judged with full history.**
  `test "$(git rev-parse --is-shallow-repository)" = false && PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py -q` exits 0.
- **AC2 — Each case fires on a planted fixture repository and clears on its twin** (a contract entry after the SPEC
  commit; the same commit is clean; `Surface reconcile` and `Story N.M landed` events are clean; a typed tag such as
  `decision by operator, 2026-09-14` is judged as a decision; a known row is tolerated; a stale known row fails with
  full history; a depth-2 clone flags the change under test and skips the shrink rule; an uncommitted `SPEC.md`
  change is a render):
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py -q -k fixture` exits 0 and its summary line reads `8 passed`.
- **AC3 — Scribe's own Spec is judged with no known row allowed.**
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py -q -k scribe_spec` exits 0 and its summary line reads `1 passed`.
- **AC4 — The known-rows file has the stated shape.**
  `python3 -c "import json,sys,os;b=json.load(open('src/shared/packages/pyforge-scribe/tests/meta/data/spec_behind_memlog_known.json'));own={'atlas','doctor','herald','marshal','mason','scribe','steward-station','warden','core-kit','control-plane','governance'};ok=all(os.path.isfile(k+'/SPEC.md') and isinstance(v,list) and v and all(set(r)=={'fingerprint','kind','committed','owner'} and r['owner'] in own for r in v) for k,v in b.items());print(sum(len(v) for v in b.values()));sys.exit(0 if ok else 1)"`
  exits 0 and prints the number of rows (43 at plan time, in 8 folders).
- **AC5 — One classifier in the repository.**
  `git grep -c 'from fleet_scan import' -- src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py && ! git grep -nE 'def _?(memlog_entry_)?is_bookkeeping' -- src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py` exits 0.
- **AC6 — Lint and types.** `pixi run --frozen -e pyforge-guild lint-types` exits 0.

## Binding

- Parent capability: `spec-pyforge-scribe` CAP-35 (minted 2026-11-10); FR-53.
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 32. Ledger key `32-3-a-spec-that-is-behind-its-memlog-reds-scribe-s-live-tree-suite`, minted `backlog`.
- Deps: none. Wave BUILD-1. Story 31.4 re-measures the known-rows file at the integration head.

## Notes

- Closes audit SHOULD S6 in part (the deterministic half). DW-scribe-cutover-2026-11-10-4 (no scheduled re-derive
  comparison) and -7 (a contract change hidden in a bookkeeping event) hold the rest; Story 31.3 writes both rows.
- Known rows at plan time: 43 in 8 folders (spec-one-chain-per-station 21, spec-pyforge-core 5, spec-pyforge-steward 5,
  spec-pyforge-herald 4, spec-pyforge-unifying-strategy 3, spec-coverage-gate-independence 3, spec-pyforge-mason 1,
  spec-foundry-regenerate-not-fold 1). The file is written from the tree this story builds on; each owning unit has a
  request to re-derive.
- Shared requests (steward-station): the scribe live-test trigger paths carry every station's Spec folders
  (`_bmad-output/projects/*/planning-artifacts/specs/*/SPEC.md` and `.memlog.md`, `docs/governance/spec-*/`), since
  the module reads them by design.
- Not adopted, with the evidence at the plan: a rule for a `Surface reconcile` event that names a path a success
  clause names fires on 268 of 2,356 reconcile events and misses the audit's own case.

## Spec Change Log

- 2026-11-10: minted with Epic 32 at the cutover-readiness mint; the Guild Specs' rows name `control-plane` as owner
  because the operator ruled the same day that steward Story 120.3 re-derives both.
