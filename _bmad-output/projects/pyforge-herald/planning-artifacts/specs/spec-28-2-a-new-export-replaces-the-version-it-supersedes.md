---
title: '28.2: A new export replaces the version it supersedes'
type: 'feature'
created: '2026-09-28'
status: 'backlog'
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-28-1-each-deck-keeps-one-current-version-of-each-export.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/sync_all.py
  - scripts/deck_export.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** After Story 28.1's prune, each export kind under `presentations/<topic>/src/{pptx,marp}/`
carries exactly one dated file, and `tests/meta/test_deck_working_set.py` reds a second one. Every
writer still only adds files:
- `deck_pipeline.pull_marp_source` writes `src/marp/<slug>-<kind>-<today>.md` (`:808-842`).
- `pull_standalone_bundle` writes `src/marp/<slug>-infographic-standalone-<today>.html`
  (`:908-937`).
- `PptxTemplateExporter.export` writes `src/pptx/<slug>-deck-<today>.pptx` (`:583-600`).
- `scripts/deck_export.py` `stamp_marp_kinds` copies the newest source to
  `<slug>-<kind>-<rebuild_day>.md` (`:199-205`) and writes the outputs dated from their source
  (`:283-309`), each with a `stamps.write_stamp` sidecar.

So the next `herald deck sync-all` that pulls or re-exports on a new day would put a second dated
file beside the current one, and the herald suite would go red until someone pruned by hand.

**Approach:** Add `retire_superseded(written)` to `pyforge.herald.deck_versions`, the one rule from
Story 28.1 (CAP-53 D2), and call it from each writer after a successful write (D3). It removes the
strictly older dated versions of the written file's kind, and their `.stamp.json` sidecars, and
returns what it removed.

## Boundaries & Constraints

**Always:**
- Retire only after the write succeeded. A failed or interrupted write retires nothing.
- Retire only the strictly older dated versions of the same kind: same directory, same stem, same
  extension. A kind's sidecar goes with its file.
- When a newer version of the kind already exists, as with a `DECK_EXPORT_DATE` backdated
  re-export, remove nothing and report the written file as superseded, so the operator decides.
- Keep `sync-all`'s idempotency (CAP-36/CAP-50). A run that writes nothing retires nothing, so a
  second run still reports every deck `unchanged` with zero writes.
- `scripts/deck_export.py` reaches the rule through the herald package, which it already imports
  (`from pyforge.herald import stamps`). The rule is never copied into the script.
- Before landing, reconcile each co-governor: add a memlog entry on every Spec that
  `spec-surface-check` names (at least `spec-pyforge-herald` and `spec-pyforge-core` for
  `deck_pipeline.py`), `git add`, run one scoped stamp per named Spec, re-check, and read the exit
  code.
- The PR carries the `maintenance` label.

**Never:**
- Do not delete the file just written, a newer version, another kind, or an undated file
  (`project/*.dc.html`, `facts.yaml`, `README.md`).
- Do not change a file name or the dating rule: `rebuild_day`, `today` and each output's
  source-dated name stay as they are.
- Do not change the newest-date pickers (`_newest_dated_match`, `find_source`, `_marp_source`,
  `_listed_files`).
- Do not rename or remove a `.herald/` state key. Stale `export:<dated filename>` keys live in the
  gitignored state and are harmless.
- Do not touch `presentations/` content in this story, and do not move files (D1).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| newer pull | `src/marp/x-deck-2026-09-15.md` exists; a pull writes `x-deck-2026-10-02.md` | only `x-deck-2026-10-02.md` remains in that kind; the older file is returned as retired | none |
| sidecar | the retired file has `x-deck-2026-09-15.pptx.stamp.json` | the sidecar is removed with it; the new file's sidecar stays | none |
| other kinds | `x-infographic-2026-09-15.md` and `x-infographic-deck-narration-2026-07-31.md` beside a new `x-infographic-2026-10-02.md` | only `x-infographic-2026-09-15.md` is retired | none |
| same day | a re-export writes the same dated path | the file is overwritten in place; nothing is retired | none |
| backdated write | `DECK_EXPORT_DATE=2026-09-01` while `x-deck-2026-09-15.pptx` exists | nothing removed; the written file is reported as superseded | report, never delete the newer file |
| failed write | the exporter raises before the file is complete | nothing retired | propagate the writer's error |
| second sync | `sync-all` run twice on an unchanged fixture | the second run reports every deck `unchanged`, with zero writes and zero retirements | none |
| check after sync | fixture `sync-all` with a new day | `python -m pyforge.herald.deck_versions --root <fixture>` exits 0 | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-53` (FR-9.2; decision D3 in the Spec's `.memlog.md`).
Architecture: AD-4 (amended 2026-09-28: a new export retires the version it supersedes).
Ledger key: `28-2-a-new-export-replaces-the-version-it-supersedes`.
Ledger status at mint: `backlog`.
Deps: S-28.1 (the `deck_versions` module and the check this story keeps green).
Co-governing Spec: `spec-pyforge-core` (every station's `src/`, including `deck_pipeline.py`).
Source: operator ruling 2026-09-28; `docs/dreams/pyforge-herald.md` § Realization log, 2026-09-28.
Minted 2026-09-28 from `epics.md` so `marshal factory dispatch` can resolve this spec.

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** S-28.1 • **FR/AD:** spec-pyforge-herald CAP-53 (FR-9.2; D3); AD-4 (amended 2026-09-28)

**Surface:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_versions.py` gains
  `retire_superseded(written)`. It deletes the strictly older dated versions of the written file's
  kind, and their `.stamp.json` sidecars, and returns what it removed.
  - It never deletes the written file, a newer version, another kind or an undated file.
  - When a newer version already exists, it removes nothing and reports the written file as
    superseded.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py`: `pull_marp_source`
  (`:808-842`), `pull_standalone_bundle` (`:908-937`) and `PptxTemplateExporter.export`
  (`:583-600`) call it after a successful write only.
- `scripts/deck_export.py`: `stamp_marp_kinds` (`:199-205`) and the three dated outputs (`:283-309`: the standalone,
  the infographic PPTX and the deck PPTX) call it after each successful write.
- `src/shared/packages/pyforge-herald/tests/unit/test_deck_versions.py` (new) and the writer tests
  in `tests/unit/test_deck_pipeline.py`, `tests/unit/test_sync_all.py` and
  `tests/scripts/test_deck_export.py`.

**Given** every dated writer adds a new file and none removes the one it supersedes, so a `sync-all` after Story 28.1's prune would regrow the tree
**When** a writer writes `<stem>-<newer date>.<ext>` beside `<stem>-<older date>.<ext>`
**Then** only the newer file of that kind remains, its sidecar with it; a failed write retires nothing; a backdated write (`DECK_EXPORT_DATE` older than the current file) removes nothing and is reported; other kinds and undated files are untouched; `python -m pyforge.herald.deck_versions` exits 0 after a fixture `sync-all`
**And** a second `sync-all` run still reports every deck `unchanged` with zero writes (CAP-36/CAP-50); `test_deck_versions.py` and the writer tests pass in `pyforge-herald-test`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; `tests/unit/test_deck_versions.py` and the writer tests in `test_deck_pipeline.py` / `test_sync_all.py` run inside it).

**Manual checks:**
- `pixi run -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass, including
  `tests/scripts/test_deck_export.py`'s new retire cases.
- `pixi run -e pyforge-herald python -m pyforge.herald.deck_versions` — expected: exit 0 on the
  story's tree, which this story does not change.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and the
  scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.
