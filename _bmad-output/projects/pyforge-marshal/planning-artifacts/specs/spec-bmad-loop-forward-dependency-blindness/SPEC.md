---
id: SPEC-bmad-loop-forward-dependency-blindness
spec: bmad-loop-forward-dependency-blindness
status: shipped
owner-dream: docs/dreams/bmad-loop-forward-dependency-blindness.md
surface: []          # retired 2026-08-09 (Story 6.9) — scripts/forward_dependency_check.py
  # moved into src/shared/packages/pyforge-doctor/** (sources/deps.py), already governed
  # by spec-pyforge-doctor's own blanket glob; see this spec's memlog for the hand-off.
sources:
  - ../../../../../docs/dreams/bmad-loop-forward-dependency-blindness.md
open_questions: []
---

> **RETROACTIVE, written 2026-08-08.** This Dream shipped (PR #238, merged 2026-08-03) before
> this Spec was written — a real process gap against this repo's Dream-first mandate (a fast,
> mechanical fix + detector went straight from Dream to code). Written after the fact from the
> Dream's own "What is real" section and the actual shipped detector, not invented.
>
> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> was built. Source documents listed in frontmatter are for traceability only.

# bmad-loop's forward-dependency blindness, closed

## Why

`bmad-loop`'s picker (`next_actionable` in `bmad_loop/sprintstatus.py`) is a strict file-order
scan within the current epic — it has no `depends_on` concept, confirmed directly against the
installed library source. A story whose own `epics.md` documents a dependency on a *later*
epic's story is dispatched anyway the moment its own epic's earlier stories clear, burning a
real dev attempt (and up to `max_review_cycles` review passes) on work that structurally cannot
complete. Found 2026-08-03 setting Marshal up to run its own backlog unattended — Marshal's own
`epics.md` had already documented three such forward dependencies (2.3→S-3.2, 2.7→S-4.1,
8.5→S-10.2) and the engine could not see any of them.

## Capabilities

- **CAP-1 — every station's structured epics doc is swept for forward-epic `**Deps:**`
  references.** *Intent:* find every story whose documented dependency lives in a later epic
  than the story itself. *Success:* a full sweep of all 8 stations' epics docs, confirming
  Marshal's three forward dependencies are the only real ones across the fleet, and that Atlas
  and Mason's presenton-pixi-image satellite (both structured enough to carry a mechanical Deps
  field) are otherwise clean.
  > **CORRECTED 2026-08-08 — the parenthetical claim was false.** Measured with the detector
  > itself: **Mason** carries 30 dependency declarations of which **zero** are machine-readable
  > (`'Story 1.4 (informs cost of …)'`, `'none (runs manually, …)'`), and **Atlas** carries 43
  > of which only 5 are (`'A1, A2.'`, `'B1 (Core pipeline datasets).'`, `'Epic 3 complete'`).
  > Neither was "structured enough to carry a mechanical Deps field." Mason nonetheless reported
  > MEASURED-and-clean from the day this shipped, because the coverage gate asked whether any
  > Deps *text* existed rather than whether any *reference parsed* — a false green in the
  > detector's own bookkeeping. Atlas reported UNMEASURED for an unrelated reason: its
  > alias-first headings (`### Story A1 (2.1):`) never matched `STORY_HEADING_RE`, so none of its
  > 46 stories parsed at all. Both are fixed; see § Refinements.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `a0aba94b0a`: `pixi run -e local-recipes forward-dependency-check` sweeps all 8 stations live; 7 now report `no-dispatch` (0 actionable stories each, since the fleet is 97% done) and 1 `measured` — 1 measured / 0 partial / 7 no-dispatch / 0 unmeasured, none silently clean. The underlying grammar/classification mechanism this CAP built is exercised directly by `test_sources_deps_forward_dependency.py` (24/24 pass, incl. whole-epic and cross-station forms).
- **CAP-2 — a found forward-dependent story is set to a non-actionable status.** *Intent:*
  make the engine structurally unable to dispatch the story early. *Success:* status `blocked`
  in both the loop-home's live Tier-3 feed and the tracked `sprint-status-ledger.yaml` twin;
  `ACTIONABLE_STATUSES = {"backlog", "ready-for-dev"}` naturally excludes it since
  `bmad_loop.sprintstatus.load()` does not validate `status` against its own declared
  `STORY_STATUSES` enum (the same mechanism the pre-existing `optional` retrospective status
  already relies on) — confirmed directly: `next_actionable(epic=2)` now correctly returns 2.4,
  skipping both Epic-2 findings.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `a0aba94b0a`: `test_forward_dep_on_actionable_story_is_a_fail` and `test_forward_dep_on_non_actionable_story_is_not_reported` (in `test_sources_deps_forward_dependency.py`, both pass) directly exercise the blocked-status-makes-it-invisible mechanism this CAP claims. Marshal's own original 3 findings (2.3/2.7/8.5) are now `done` in the tracked ledger — no longer live cases, but the mechanism they proved is still test-covered.
- **CAP-3 — a permanent detector prevents recurrence.** *Intent:* a new story added later with
  an unmarked forward dependency is caught in CI, not discovered by a run burning compute on it.
  *Success:* `scripts/forward_dependency_check.py`, self-registered via `scripts/detectors.py`,
  scans every station's structured epics doc for forward-epic `**Deps:**`, cross-checks each
  against the tracked ledger, and fails if a forward-dependent story is still
  `backlog`/`ready-for-dev`.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `a0aba94b0a`: `scripts/detectors.py:227` registers `("forward-dependency", "forward-dependency-check")`; the detector (now `pyforge.doctor.sources` per the frontmatter's 2026-08-09 Story 6.9 hand-off, invoked via the same pixi task) ran clean above. `test_coverage_finding_is_emitted_even_on_a_red_run` confirms it still reports even when failing, not just on success.
- **CAP-4 — an unparseable epics format is reported honestly, never silently passed.**
  *Intent:* this repo's fidelity-enforcement doctrine (never claim green you didn't measure)
  applies to the detector itself. *Success:* stations whose `epics.md` uses an older narrative
  format with no structured `**Deps:**` field (confirmed: `pyforge-warden`) are reported as
  **not determinable from this format**, not as clean.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `a0aba94b0a`: live run above reports `no-dispatch`/`measured` per-station, never a bare "clean" for an unparseable format; `test_unparseable_heading_is_not_silently_clean` and `test_headings_without_deps_field_report_unmeasured` (both pass) pin this directly.

## Constraints

- **Always:** flipping a `blocked` story back to `backlog` once its real dependency lands is a
  one-line edit, not a rediscovery — the PROJECT NOTES comment at the top of each affected
  `sprint-status.yaml` names exactly which dependency to watch for.
- **Never:** the detector never infers a dependency that isn't explicitly written in a
  `**Deps:**` field — it does not attempt semantic inference across epics.

## Non-goals

- **A general-purpose dependency graph / scheduler.** This closes the specific blindness
  (forward-epic deps invisible to a strict file-order picker), not a DAG-based execution model.
- **Retrofitting `**Deps:**` onto stations using the narrative epics format.** CAP-4 reports
  those honestly as undeterminable; migrating them to a structured format is separate,
  unscheduled work.

## Delivery Record

Shipped via PR #238 (`dream+detector: bmad-loop can't see a story's forward dependency`), merge
commit `a825ac0749`, 2026-08-03T08:01:58Z. Stories 2-3 and 2-7 (the mechanical fix) shipped
earlier the same session in PR #237; 8-5 and the permanent detector landed in #238.
https://github.com/rxm7706/local-recipes/pull/238

## Refinements — 2026-08-08

Found while acting on the fleet-readiness note that four stations read `[unmeasured]`. The
premise turned out to be wrong in both directions: the data was fine, the detector was not.

**R-1 — CAP-4 gains a fourth coverage class, and coverage is keyed on *readable* references.**
CAP-4 as written had one non-clean bucket, which conflated two unrelated situations and let a
third go unnoticed. The classes are now `NO-DISPATCH` (ledger positively shows zero actionable
stories — nothing can be dispatched, so no forward dep can fire; a measured fact, explicitly
**not** a parse-clean claim), `MEASURED` (every declaration resolved or explicitly declared
none), `PARTIAL` (a real dependency is stated in a grammar `DEP_RE` cannot read — readable refs
are still checked, but the ratio is reported so the station can never read as fully verified),
and `UNMEASURED` (no declaration and work remains, or the ledger is unreadable). `NO-DISPATCH`
requires **positive** ledger evidence — a missing ledger falls to `UNMEASURED`, never to
`NO-DISPATCH`, or absence would read as reassurance.

*This does not weaken CAP-4.* CAP-4's requirement is that an unparseable format never be
reported as clean, and none of the three non-`MEASURED` classes asserts cleanliness. What
changed is that "measured" now means what it says.

**R-2 — the `**Deps:**` grammar gains a whole-epic and a cross-station form.** Declarations
legitimately depend on an entire epic (`'Epic 3 complete'`, `'Epics 4–6'`) or on another
station (Atlas 12.2 → `Steward S-2.1`), and neither was expressible — which is *why* those
declarations were written as prose the detector could not read. `S-<epic>.*` and
`<station>:S-<epic>.<num>` close that. The cross-station form also fixes a live misread: Atlas
12.2's `Steward S-2.1` parsed as *Atlas's own* epic 2, benign only because 2 < 12 and Atlas's
epic 2 is shipped. Canonical grammar, binding on all stations:

```
**Type:** feature • **Effort:** S • **Deps:** S-5.1, S-3.* • **FR/AD:** FR-14
    S-5.1            same-station story        S-3.*   whole epic, same station
    steward:S-2.1    cross-station story       —       genuinely no dependency
Prose is allowed ONLY as trailing context, never alone:  S-3.1 (consumes its handoff contract)
```

**R-3 — atlas's alias-first headings are parsed.** A second, deliberately-enumerated regex
branch handles `### Story A1 (2.1):`, with the parenthetical canonical. Atlas went from 0 to 46
stories parsed; every other station's extracted tuples are byte-identical (verified by diff).

**Still open, deliberately.** The 59 prose declarations in atlas/mason/steward are **not**
migrated by this refinement, and the fleet therefore reports `PARTIAL` for those stations rather
than `MEASURED`. A by-hand audit of all 62 confirmed **no prose declaration hides a forward
dependency** — mason's chain is strictly backward, atlas's likewise — so this is a legibility
gap, not a live risk. Migration plus a gate that fails on `PARTIAL` is tracked separately; it
must land in one change, because the gate reds CI until the migration completes.

## Success signal

`next_actionable(epic=2)` returns 2.4, not 2.3 or 2.7, until their real dependencies land; the
detector fails CI on any newly-added forward dependency left unmarked; a re-run of the
cross-station sweep finds no new forward dependencies undetected.
