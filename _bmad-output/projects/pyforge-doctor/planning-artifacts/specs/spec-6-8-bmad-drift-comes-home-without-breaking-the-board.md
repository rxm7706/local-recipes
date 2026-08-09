---
title: "Story 6-8: `bmad_drift` comes home without breaking the board"
type: "change"
created: "2026-08-09"
status: "ready-for-dev"
authored: "spec-first, ahead of implementation (operator instruction 2026-08-09: seed -> Dream -> Spec -> code)"
owner-dream: docs/dreams/pyforge-doctor.md
context:
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md'
  - '{project-root}/scripts/bmad_drift_check.py'
  - '{project-root}/docs/dashboard/generate.py'
---

## Intent

Port `scripts/bmad_drift_check.py`'s judgement into Doctor as `sources/factory.py` — the
**tenth and last** of the re-homed verdicts, completing Epic 6's Charter §6 sweep. FR-15.

This one carries a complication none of 6.4–6.7 did: the detector is not a leaf. It **owns
constants a second consumer imports**. `docs/dashboard/generate.py:770` does

```python
from bmad_drift_check import GUILD_DREAMS, STATIONS
```

and the import is deliberate. `bmad_drift_check.py:653` records why: *"Mirrored in
docs/dashboard/generate.py:GUILD_DREAMS; both change together."* A hand-mirrored copy is
what produced the 2026-07-28 false positive; the import replaced it. Moving the detector
without moving that contract would reintroduce the defect the import exists to prevent.

**Surface:** `sources/factory.py`, `docs/dashboard/generate.py`, `tests/`

## Acceptance Criteria

- **Given** `docs/dashboard/generate.py` imports `GUILD_DREAMS`/`STATIONS` from
  `scripts/bmad_drift_check.py`, **When** that detector moves, **Then** the shared constants
  have **exactly one home** and both consumers derive from it.
- **And** no hand-mirrored copy is reintroduced — the 2026-07-28 false positive is the
  reason that import exists.
- **And** (amended 2026-08-09, see *The constant set is four, not two*) `DREAM_STATUSES`
  and `DREAM_TYPES` are consolidated into the same single home, not left behind — they are
  the two constants still hand-mirrored between the pair today.
- **And** `gather_bmad_drift` produces the same verdict as the origin script against the
  live repo — parity proven on real data, not fixtures (the standard set by 6.4–6.7).
- **And** `sources/factory.py` imports no `pyforge.<station>` package, asserted by an
  independence test in the established shape.
- **And** the board still builds: `dashboard-gen` runs clean and `dashboard_drift_check`
  stays green after the constants move.

## Design notes

### The constant set is four, not two (amended 2026-08-09, before implementation)

The AC as written names the **imported** pair, `GUILD_DREAMS` and `STATIONS`. An AST sweep
of module-level upper-case constants defined in *both* files found **two more that are
hand-mirrored rather than imported**:

| constant | `bmad_drift_check.py` | `generate.py` | today |
|---|---|---|---|
| `GUILD_DREAMS` | defines | **imports** | safe by construction |
| `STATIONS` | defines | **imports** | safe by construction |
| `DREAM_STATUSES` | defines | **re-declares** | identical **by luck** |
| `DREAM_TYPES` | defines | **re-declares** | identical **by luck** |

Neither mirrored pair has diverged *yet*, so there is no live bug — which is exactly why
they were easy to miss, and exactly the state `GUILD_DREAMS` was in on 2026-07-27. The
source file even labels them: *"Mirrored in docs/dashboard/generate.py:DREAM_STATUSES"*.
"Mirrored" is the defect, written down as if it were the design.

Moving only the imported pair would leave the story's own AC — *"the shared constants have
exactly one home"* — false for half the shared constants, and would leave the duplication
hazard live in a file this story is already rewriting. All four move together.

**Verification, not inspection:** re-run the AST sweep after the change and assert the
intersection of module-level constants defined in both files is **empty**. A visual check
is what let two survive the first fix.

### Where the constants should live, and the constraint that decides it

Three candidate homes, and one is ruled out by an existing invariant:

1. **Inside `sources/factory.py`** — then `docs/dashboard/generate.py` must import from
   `pyforge.doctor`. **Ruled out:** `generate.py` runs under `local-recipes`, where
   `pyforge.doctor` is **not importable** (verified: `import pyforge.doctor` raises
   `ModuleNotFoundError` there, which is also why Story 6.7's conformance test reads
   Doctor's constant by `ast` rather than importing it). The board would break on every
   `dashboard-gen`.
2. **A third module both import** — e.g. a small `scripts/` or package-level constants
   module. Keeps one home, costs one new file, and works from both environments if it stays
   dependency-free stdlib.
3. **Leave them in `scripts/bmad_drift_check.py`** while moving only the judgement.
   **Ruled out by S-6.9**, which retires that file entirely — the constants would have to
   move anyway, one story later, with the board depending on a file scheduled for deletion.

Option 2 is the only one satisfying "exactly one home" *and* both runtimes. The
implementation should confirm the import direction empirically before committing to it —
the `ModuleNotFoundError` above is the whole reason option 1 fails, and it is easy to
assume away.

### What "same verdict" must cover

`bmad_drift_check.py` is the largest of the ported detectors and reports several finding
families (pin drift, count/phase-list staleness, stale rules, archive hygiene + stray
files, coverage completeness, baseline-vs-live surface change). Parity means the **whole
finding set** matches, not just the exit code. Capture the origin script's output on the
live repo before the move and diff it against the port's, the way 6.7's parity check
compared `2 measured / 3 partial / 3 no-dispatch / 0 unmeasured` and the per-station ratios.

### Ordering

`Deps: S-6.6`. This story completes the set of ten that **S-6.9 requires** before the
`scripts/` shims can retire, so it must land before 6.9 starts.

### Registry

Adds one `Source` member (`BMAD_DRIFT`), its `report-schema.json` enum entry, and one
`REGISTRY` row with `subject_station="marshal"` (the artifacts judged are Marshal-governed
BMAD planning artifacts). The closed-taxonomy tripwire in `tests/unit/test_models.py` will
fail until updated — that is the tripwire working, and it should be updated deliberately
rather than pre-emptively.
