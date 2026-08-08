---
title: One primitive, one home — the shared floor under eight stations
type: dream
owner: marshal
status: archived
---

# One primitive, one home — the shared floor under eight stations

> **Consolidated into [[pyforge-marshal]] on 2026-08-08** (§ *Eight more, consolidated
> here*). This file is archived in place: its **Spec stays live and remains the
> contract** — archiving the Dream tier never retires the chain below it. Kept, not
> deleted, so the reasoning that produced the Spec is still readable.

## The Dream

Eight stations, one namespace, and the same five primitives written eight times.
Not by accident and not by neglect — by a doctrine that was right about the thing
it was protecting and silent about the thing it wasn't. Stations are
independently conda-installable and deliberately do not import each other, so
every station that needed to write a file atomically wrote its own atomic write.
The copies know they are copies: their docstrings say *"mirrors `state.write`"*
and *"identical shape."*

The Dream is a **leaf**: one small package, pure stdlib, that no station imports
*from another station* — it sits under all of them, depended on by each and
coupling none. Adding a station stops meaning re-deriving the floor. Fixing a bug
in the floor stops meaning finding twenty copies and hoping.

The counterweight is real and is the reason this Dream is narrow: a shared
package that grows station-specific knowledge becomes exactly the coupling the
architecture has spent eight stations refusing. **Leaf or nothing.**

## What is real — the census, measured

Counted directly against the tree on 2026-08-08, not inherited from a summary:

| Primitive | Copies | Spread |
|---|---|---|
| **Atomic write** (`os.replace` + tmp-in-dir) | **20 files** | 6 of 8 stations — herald 6, atlas 5, marshal 5, steward 2, scribe 1, warden 1; doctor and mason have none |
| **Verdict / exit-code lattice** | **5** | atlas, doctor, herald, marshal, warden each declare their own |
| **Report envelope schema** | **3** | warden 22 KB · doctor 4.5 KB · marshal `envelope.v1.json` 4.3 KB — one shape, three schemas |
| **Station roster** | **3 explicit + 1 implicit** | `bmad_drift_check.STATIONS` (canonical, imported by `generate.py`) · `herald/progress.py` · `Sidebar.jsx` · plus `PROJECT_SOURCES` keyed by station |
| **Subprocess invocation** | **15 modules** | marshal 7 · steward 3 · herald 2 · doctor 1 · scribe 1 · warden 1 |
| **Base exception root** | **0 shared** | herald and mason each invented one; warden/marshal/atlas scatter 12–13 `*Error` classes with no common root |

The duplication is genuine and, for atomic write and the verdict lattice,
mechanical: zero semantic divergence, self-documented sameness. Doctor's
`verdict.py` literally describes itself as *"a subset of `pyforge.warden`'s
frozen `{0, 1, 2, 130}`"* — a dependency asserted in a docstring because there
was no package to express it in.

### Three corrections to the source research

This Dream's census supersedes the figures in
`_bmad-output/projects/pyforge-marshal/planning-artifacts/research/technical-pyforge-unification-2026-08-08.md`
§ 7, which were the trigger for capturing it. Recorded because the third one
inverts that document's single strongest recommendation:

1. **Atomic write is 6/8 stations, not 8/8** — doctor and mason have zero copies.
2. **The report envelope is 3 schemas, not 2** — marshal's `envelope.v1.json` was
   not counted.
3. **Warden is not the subprocess outlier — Marshal is.** The research reads
   *"warden is the outlier: ~20 modules import `subprocess` with no sole-site
   guard,"* and calls fixing it *"the one item worth doing even if nothing else
   is."* That counted **mentions**, not imports. Exactly **one** warden module
   imports `subprocess` (`engines.py`), and its call site is annotated
   `# noqa: S603 — argv list, no shell; the sole seam`. Warden already has the
   guard the research says it lacks. **Marshal**, at 7 importing modules, is the
   station with the widest ungated surface — and it is the station that owns this
   Dream, which is the more uncomfortable finding and the reason it is written
   down here rather than quietly fixed.

## What it looks like when real

- One package under `src/shared/packages/`, pure stdlib, importable by any
  station and importing none of them.
- Atomic write has one implementation; the 20 copies are **retired in the same
  story that extracts them**, never left as a second path.
- The verdict lattice is declared once with per-station domain restriction, so
  doctor's `{0, 2, 130}` is expressed as a real narrowing of warden's
  `{0, 1, 2, 130}` rather than asserted in prose.
- One report-envelope schema; warden's richer fields are an extension of it, not
  a rival.
- The station roster is data with one owner, and adding a station is one edit.
- One exception root, so `except PyforgeError` is a sentence anyone can write.
- A meta-test per primitive fails the build if a second implementation appears —
  the sole-ownership pattern marshal and warden already use.

## Constraints

- **Leaf or nothing.** Pure stdlib; no station imports another station through
  it. If it ever needs a station's type, the extraction was wrong.
- **Retire the copy in the story that extracts it.** Atlas's Kedro migration is
  the cautionary precedent on record: ~29 k LOC merged and marked `shipped` while
  the 8,902-LOC legacy module stayed the live runtime, because the rebuild had no
  migration step. An extraction that leaves the copies standing has done nothing
  and claimed something.
- **Stations stay independently conda-installable.** A shared floor must not
  become a distribution constraint.
- **Extraction order follows the census**, heaviest and most mechanical first:
  atomic write → verdict lattice → report envelope → roster → exceptions →
  subprocess guard. Subprocess is last on purpose: two designs genuinely differ
  (doctor's `cli_bridge.run_cli_json` versus marshal's `ProcessPort`), and
  steward *deliberately* propagates raw `CalledProcessError`. That is a design
  reconciliation, not a copy-paste consolidation.

## Non-goals

- **Not a framework, not a plugin system, not a service.** Six primitives with a
  measured copy count each.
- **Not a home for anything with one caller.** A primitive earns its place by
  existing two or more times already.
- **Not a station.** It has no Dream of its own to deliver, no verdict, no
  station in the roster — it is a dependency, and Charter §5's roster stays at
  eight.
- **Not a rewrite of working tests.** Stations adopt the floor as they touch the
  code, except where the extracting story retires a copy outright.

## The frontier

- Whether `pyforge-testing-kit` (the testing charter's CAP-3, unbuilt) is a
  second leaf or a module of this one.
- Whether the roster belongs here or stays in the detector that already owns it —
  it is the one census entry whose canonical home already exists.

## Realization log

- **2026-08-08** — Captured during the Marshal planning rewrite, at the moment
  the unification research named as the window: *"decide `pyforge-core` scope
  now, before S-7.1 opens — it changes two Epic-7 stories."* Epic 7's stories
  7.2 (error taxonomy and exit codes) and 7.3 (the fs-write primitive and the
  never-write guard) would otherwise have minted copy #21 of atomic write and
  copy #6 of the verdict lattice inside the very rewrite meant to consolidate.
  Census re-measured directly rather than inherited; three figures corrected,
  including one that reverses the research's strongest single recommendation
  (see above). Owner `marshal` under the build-line/estate seam ratified the same
  day: the shared floor is factory machinery, not the estate beneath it.
