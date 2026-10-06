---
title: "85.6: A fix turn re-runs only the failing commands and knows the flag checklist"
type: 'fix'
created: '2026-10-06'
status: 'ready-for-dev'
baseline_revision: '7ab1f2d7b79f4e0c91755c060e902bb3cb1fcc6a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verify_fix.py
  - docs/reference/story-spec-flag-block.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** one fix turn was not enough for the two refusals on 2026-10-05, and both failures were predictable.

- **Warden 14.1.** Its fix turn received the failed commands (`pixi run --frozen -e pyforge-core pyforge-core-test`,
  `pixi run --frozen -e pyforge-warden pyforge-warden-coverage-gate`). It ran
  `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q --cov=…` instead. That
  reaches the `slow` corpus-oracle tests the station task deselects (`pyforge-warden-test` runs `-m "not slow"`), and
  the turn was killed at its 900 s budget (MRS-DISP-059) with its edits uncommitted.
- **Atlas 25.2 and warden 14.1.** Both stories declared a flag with `flag.default: {production: off, staging: on,
  dev: on}`. Each session registered the flag in `src/platform/config/flags.json` only. They missed the per-environment
  entries in `src/platform/config/flag-overlays.json`, core `tests/unit/test_flags.py` (`_SHIPPED_CLOCKS`, `expected`
  or `per_environment`), and platform `tests/test_openfeature_file_flags.py` (`_SHIPPED_BOOLEANS`). Atlas's fix turn
  fixed the core test, then `platform-ci-local` refused and the story parked (MRS-DISP-060).
- **The prompt today.** `build_verify_fix_prompt` (`core/dispatch_verify_fix.py`, about :197) lists each failed
  command and its scrubbed output tail. It says nothing about how to re-run, and nothing about flags.

**Approach:** two additions to the prompt, and one doc section.
- Always: tell the session to reproduce and confirm the fix with the failed commands exactly as quoted. Station tasks
  already deselect `slow`, so it must never run a package's raw test directory.
- When a flag is in play: add a short checklist naming the four registration points, and point to
  `docs/reference/story-spec-flag-block.md` § *Registering a flag*. A flag is in play when the failing output or the
  story's spec mentions `flags.json`, `flag-overlays.json`, `test_flags.py`, `test_openfeature_file_flags.py`,
  `flag-gate-check` or `flag-default-env-mismatch`, or the spec has a `flag:` block.
- Add that section to the doc once. The doc is where a story's first dev session already looks (MRS-DISP-055 points
  to it), so the original session sees the checklist too.

Ledger key: `85-6-a-fix-turn-re-runs-only-the-failing-commands-and-knows-the-flag-checklist`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-286 (FR-233; Epic 85, a verification refusal goes back to the
  session for one fix turn). A gap in shipped behaviour; no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag; `pyforge.marshal.verify_fix_loop` is
  unchanged.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-06 (landing gaps), item 2.

## Acceptance Criteria

- Given any failed verify command When `build_verify_fix_prompt` runs Then the prompt instructs re-running exactly the
  quoted commands and names that a package's raw test directory must not be run.
- Given a failing output that contains `test_flags.py` (or a spec with a `flag:` block) When the prompt is built Then
  it lists `src/platform/config/flags.json`, `src/platform/config/flag-overlays.json`, core `tests/unit/test_flags.py`
  and platform `tests/test_openfeature_file_flags.py`, and points to the doc section.
- Given a failing output with no flag signal and a spec with no `flag:` block When the prompt is built Then no flag
  checklist appears.
- Given `docs/reference/story-spec-flag-block.md` When read Then it has one *Registering a flag* section with the
  same four points, including that the overlay values follow the spec's `flag.default`.
- Given either prompt addition removed (mutation) When the station suite runs Then its new test fails.

## Boundaries & Constraints

**Always:**
- Keep the prompt's existing scrub and tail behaviour (Stories 85.3/85.4) exactly as it is.
- Keep the checklist in one place (the doc). The prompt carries the four paths and the pointer, nothing more.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped (`spec-pyforge-marshal` and the
  co-governor `spec-pyforge-core`; the doc's governor if `spec-surface-check` names one).

**Never:**
- Never change the fix-turn budget, the single-turn rule, or `pyforge.marshal.verify_fix_loop`.
- Never make the fix turn edit flags itself; the prompt informs the session, nothing more.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-06 (landing gaps) entry.
- Epic: Epic 85 (a fix joins its own epic, which reopens; doctor Story 41.5).
- Ledger key: `85-6-a-fix-turn-re-runs-only-the-failing-commands-and-knows-the-flag-checklist`.
- Ledger status at mint: `backlog`.
- Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: remove the flag checklist branch and re-run the station suite; its test fails. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
