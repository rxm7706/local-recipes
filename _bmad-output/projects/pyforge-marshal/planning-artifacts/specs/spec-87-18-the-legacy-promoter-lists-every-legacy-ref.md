---
title: "87.18: The legacy promoter lists every legacy ref"
type: 'fix'
created: '2026-10-22'
status: 'done'
baseline_revision: 'ab50b079a8c8d68d364570b96e01cdd788885ac6'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-12-legacy-refs-are-promoted-and-attempt-preserve-leaves-the-protected-list.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-17-the-legacy-promoter-reads-every-commit-s-bytes.md
  - docs/dreams/pyforge-marshal.md
  - scripts/legacy_preserve_promote.py
  - tests/scripts/test_legacy_preserve_promote.py
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 87.12's AC says the tracked manifest names every legacy ref it lists. Once Story 87.17 let the
promoter run, the independent review found 8 of those refs missing from the 2026-10-22 manifest:
- `collect_promotion_rows` asked `git for-each-ref` for `refs/heads/*` and `refs/tags/*`. Those globs match one level
  only, so `backup/bmad-suite-updates-2026-09-26`, `archive/crewai-toolkit-wip-2026` and the nested legacy tags were never
  seen.
- The three kept `attempt-preserve/*` branches (Story 87.1's ruling) were read only from `refs/heads/`; they exist only as
  `refs/remotes/origin/attempt-preserve/*`.
- The tag loop skipped every `archive/` tag before it looked up `LEGACY_TAG_TWINS`, which names two `archive/` tags.

So Story 87.12's operator-gate rows ("after all three kept branches have preserve/ twins on origin") could never be
met, and a reviewer would read an incomplete manifest as the whole inventory.

**Approach:**
1. Every `for-each-ref` call takes a prefix (`refs/heads/`, `refs/tags/`, `refs/tags/rescue/`, the custom prefixes),
   never a one-level glob.
2. The kept branches are read from `refs/heads/attempt-preserve/` and `refs/remotes/origin/attempt-preserve/`, once each.
3. The tag loop looks up `LEGACY_TAG_TWINS` first.
4. `pyforge.core.preserve_refs` (AD-81) bars a date from a twin's name, so `backup/bmad-suite-updates-2026-09-26` cannot
   become `archive/heads/backup/bmad-suite-updates-2026-09-26`. A legacy name carrying a date falls back to a
   `preserve/unbound/hand-<sha8>` twin, as the custom refs do; its `Preserve-Source` trailer keeps the name.

Ledger key: `87-18-the-legacy-promoter-lists-every-legacy-ref`.
Type / Effort / Deps: fix / XS / S-87.17.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234; AD-81). A defect in Story 87.12's script, so no new CAP; the script is not
  flag-gated, so no flag.

## Acceptance Criteria

- **AC1 — Inventory.** A fixture repo with a nested `backup/` branch, `archive/crewai-toolkit-wip-2026`, the three legacy
  tags, and a kept branch only on `origin` yields a promotion row for each, with its twin.
- **AC2 — Grammar.** The `backup/...-2026-09-26` branch takes a `preserve/unbound/hand-*` twin; the others keep the
  names Story 87.12 gives them.
- **AC3 — Mutation.** The fixture test fails on the old inventory.
- **AC4 — Live.** The dry run on this repository lists the 8 refs. Their twins are not written without the operator's
  go-ahead.

## Boundaries & Constraints

**Always:** Keep the script dry-run by default; read every verdict from the exit code.

**Never:** Push a tag, delete a ref, or run `--execute` for the newly listed refs without the operator. Change the
AD-81 grammar in `pyforge.core.preserve_refs`.

**Residual risk:**
- A hand twin's name does not say which branch it came from; only its `Preserve-Source` trailer and the manifest do.

## I/O & Edge-Case Matrix

| Ref | Twin |
|-----|------|
| `refs/remotes/origin/attempt-preserve/<kept>` | `preserve/<slug>/<story>/hand-<sha8>` (or `unbound`) |
| `refs/heads/backup/bmad-suite-updates-2026-09-26` | `preserve/unbound/hand-<sha8>` (date barred) |
| `refs/heads/archive/crewai-toolkit-wip-2026` | `archive/heads/archive/crewai-toolkit-wip-2026` |
| `refs/tags/bmad-loop-preserve/5-9-intent-gap-2026-08-12` | `preserve/pyforge-marshal/5.9/hand-<sha8>` |
| `refs/tags/archive/recover-scribe-1-3` | `archive/tags/recover-scribe-1-3` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-marshal` CAP-287 (FR-234). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-22 entry (the legacy promoter dies on one
  commit's bytes, and misses nested refs).
- Epic: Epic 87 (done). Story 87.18 is minted `done`, so `epic-87` stays `done`.
- Ledger key: `87-18-the-legacy-promoter-lists-every-legacy-ref`; status at mint `done`.

## Verification

**Commands:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_legacy_preserve_promote.py -q` — expected: 8 passed.
- `pixi run -e pyforge-guild python scripts/legacy_preserve_promote.py --manifest-date 2026-10-22` — expected: exit 0,
  the 8 refs listed (AC4).

## Run results

Run 2026-10-22 in the landing worktree, every verdict read from its exit code.

- **AC1–AC3:** `test_inventory_reads_nested_legacy_refs` passes (8 passed in the file). It fails on Story 87.17's
  script and on `ab50b079a8`'s.
- **AC4:** the dry run exited 0 and wrote `legacy-preserve-promote-2026-10-22.json`: 688 rows, 27 promotion rows. The 8
  new ones, none of whose twins exists:
  - `refs/heads/archive/crewai-toolkit-wip-2026` → `refs/tags/archive/heads/archive/crewai-toolkit-wip-2026`
  - `refs/heads/backup/bmad-suite-updates-2026-09-26` → `refs/tags/preserve/unbound/hand-6069fa46` (date barred)
  - `refs/remotes/origin/attempt-preserve/20260712-125315-0aaa-c2605ff1` → `refs/tags/preserve/unbound/hand-c2605ff1`
  - `refs/remotes/origin/attempt-preserve/20260821-082415-mason-6-3-github-version-checker-gap` →
    `refs/tags/preserve/pyforge-mason/6.3/hand-6f595bd9`
  - `refs/remotes/origin/attempt-preserve/47.1-dispatch-20260920-80e85c57` →
    `refs/tags/preserve/pyforge-marshal/47.1/hand-80e85c57`
  - `refs/tags/archive/recover-scribe-1-3` → `refs/tags/archive/tags/recover-scribe-1-3`
  - `refs/tags/archive/scribe-1-3-dangling-91d3571f` → `refs/tags/archive/tags/scribe-1-3-dangling-91d3571f`
  - `refs/tags/bmad-loop-preserve/5-9-intent-gap-2026-08-12` → `refs/tags/preserve/pyforge-marshal/5.9/hand-77bb757a`

  The 19 rows Story 87.17's run listed are unchanged. `--execute` was not run for the 8: that waits on the operator.

## Spec Change Log

- 2026-10-22: minted `done` from Story 87.17's review (its blocker B1), implemented and verified in the same change.

## Review Triage Log

- 2026-10-22: the independent review runs as a separate pass and records its findings here.
