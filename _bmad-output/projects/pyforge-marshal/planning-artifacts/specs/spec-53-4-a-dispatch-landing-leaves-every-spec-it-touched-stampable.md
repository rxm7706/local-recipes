---
title: "53.4: A dispatch landing leaves every Spec it touched stampable"
type: 'fix'
created: '2026-10-06'
status: 'ready-for-dev'
baseline_revision: '7ab1f2d7b79f4e0c91755c060e902bb3cb1fcc6a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - scripts/spec_surface_check.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** two dispatch landings left `spec-pyforge-core` paths unnamed, so core's scoped stamp refused afterwards.

- **The evidence.** Marshal 46.10 changed
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/copilot.toml`, and marshal 70.2 changed
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/apply/run.py` and added
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/skip_match.py`. Both landed by
  `marshal factory dispatch` on 2026-10-05. `spec-pyforge-marshal`'s memlog named all three paths. On `6b55df1123`,
  `python scripts/spec_surface_check.py --write-baseline --spec pyforge-marshal/spec-pyforge-core` refused, naming
  exactly those three as "differ from the spec's baseline and its memlog does not name them". 46.10's run journal
  (`pyforge-marshal-20261005T153528899Z-8e52c1e7/journal.jsonl`) has no `MRS-DISP-047` reconcile row at all. A hand
  PR (#1884, commit `7cbe757cc0`) named them and stamped core.
- **What already exists.** `dispatch_land.py` runs doctor's `gather_spec_surface` and reconciles
  (`_reconcile_spec_surface_drift`, about :316) every Spec whose `drift` or `drift-presumed` rows name the branch's own
  paths (`_group_surface_findings`, about :277-:301), looping until none does. So the gap is not "drift-presumed is
  ignored"; the cause is not yet known.
- **Why it matters.** Every later landing that touches station `src/` meets `MRS-DISP-048` (foreign drift on core)
  for paths it never changed, as on 2026-10-03 for scribe 26.1 and mason 27.1.

**Approach:** trace why the 46.10 and 70.2 landings recorded no reconcile for `spec-pyforge-core`, then fix the
landing so it leaves every Spec it touched stampable. Candidate causes to test first, in order:
- the doctor verdict, run from the dispatch worktree, did not report core's rows at all (for example because core's
  baseline entry or memlog movement made those paths read as clean);
- the reconcile ran only on Specs that the repo-wide `spec-surface-check` reports as failing, and core's rows were
  WARN-level `drift-presumed`;
- the session's own memlog entry on `spec-pyforge-marshal` satisfied the check the landing uses, and core was never
  evaluated.

Record the cause found in the Auto Run Result. The fix lives in `dispatch_land.py`; it may call doctor's existing
read-only verdict as today, never modify it.

Ledger key: `53-4-a-dispatch-landing-leaves-every-spec-it-touched-stampable`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-261 (Story 53.2, the landing reconciles from git facts). A
  defect of shipped behaviour; no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-06 (landing gaps), item 4.

## Acceptance Criteria

- Given a real-git fixture whose branch changes a path governed by both its station Spec and `spec-pyforge-core`, the
  session named it only on the station Spec, and core's memlog had already moved for another story When the landing
  reconcile runs Then core's memlog names the path and `spec_surface_check.py --write-baseline --spec
  pyforge-marshal/spec-pyforge-core` succeeds on the landed tree.
- Given the same fixture's original shape before the fix When it runs (mutation, or a test pinned to the old
  behaviour) Then core is left unnamed, reproducing 2026-10-05.
- Given drift on core that names a path the branch did not change When the landing reconcile runs Then it still
  refuses with `MRS-DISP-048` naming that path.
- Given a branch whose every touched Spec already names its paths When the landing runs Then no reconcile commit and
  no `MRS-DISP-047` row are recorded.
- The Auto Run Result names the cause found.

## Boundaries & Constraints

**Always:**
- Fix the landing (`dispatch_land.py`); doctor's verdict is read-only input.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped (`spec-pyforge-marshal` and the
  co-governor `spec-pyforge-core`).

**Never:**
- Never use a bare `--write-baseline`, and never `--accept` a path the branch did not change.
- Never weaken `MRS-DISP-048` for foreign drift.
- Never modify `pyforge.doctor` or `scripts/spec_surface_check.py` in this story; if the cause is there, stop and
  record an intent gap naming it.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-06 (landing gaps) entry.
- Epic: Epic 53 (a fix joins its own epic, which reopens; doctor Story 41.5).
- Ledger key: `53-4-a-dispatch-landing-leaves-every-spec-it-touched-stampable`.
- Ledger status at mint: `backlog`.
- Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- On the landed tree: `python scripts/spec_surface_check.py --write-baseline --spec pyforge-marshal/spec-pyforge-core`
  stamps without refusing (run on a scratch clone, not the shared checkout).
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
