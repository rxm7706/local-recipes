---
chain: pyforge-marshal
created: 2026-11-10
updated: 2026-11-10
status: final
type: research
title: "CAP marker truth 2026-11-10: pyforge-marshal"
source: marshal Story 114.1 (the marker sweep under spec-one-chain-per-station:CAP-6 and spec-one-chain-per-station:CAP-9)
---

# CAP marker truth, 2026-11-10: pyforge-marshal

**What this is.** One row per capability of `spec-pyforge-marshal` as it stood at `82a2b18828`
(CAP-1..CAP-303): the marker the capability carries after marshal Story 114.1's render, the open
stories that still cite it, the evidence for the marker, and the ledger mode proposed for it.
The memlog `correction` entry of the same story carries the markers by reference to column 2.
Column 5 is the input steward Story 121.3 regenerates `docs/foundry/capability-ledger.yaml` from;
this file writes no ledger row. spec-pyforge-marshal:CAP-304 and spec-pyforge-marshal:CAP-305 are
minted by their own memlog `capability` entries (2026-11-10) and are not rows here: both read
`(ready 2026-11-10)` while Stories 114.3 and 116.1 to 116.5 are open.

**Inputs.** `specs/spec-pyforge-marshal/SPEC.md` (unchanged since `82a2b18828` until this render),
`epics.md` and `sprint-status-ledger.yaml` on branch `cutover-readiness-2026-11-10` at `0f8a95114e`,
the PRD's FR arrows, and `git ls-files`.

## Method

1. **Join.** Each capability is joined to the `### Story` blocks of `epics.md` by its number
   (`spec-pyforge-marshal CAP-n`, or a bare `CAP-n` in a story that names no single pre-fold Spec),
   by its `<- spec-old CAP-m` provenance (the pre-fold Spec name, a short alias such as
   `token-economy`, or a bare `CAP-m` in a story whose only cited pre-fold Spec is that one), and by the
   PRD requirements whose arrow names it (`FR-n <- CAP-m`, read from the story's FR/AD line). A
   story cites a capability through its title, its `FR/AD` line, or, once done, its epic's
   heading.
2. **Ledger.** Each citing story's value is read from `sprint-status-ledger.yaml`. A story is
   open unless it reads `done`.
3. **Date.** A `(shipped <date>)` marker set by this sweep is dated the day the last citing story
   reached done: `git log --reverse -S'<key>: done' --format=%as -- sprint-status-ledger.yaml | head -1`,
   taken for every citing story and maximised. A retired marker is dated from the deleting
   commit (`git log --diff-filter=D`).
4. **Paths.** The backticked paths a capability's heading, intent and success name are checked
   with `git ls-files` (a tracked file or directory, or a tracked path ending in the name). An
   untracked name is listed; most are runtime files (`policy.toml`, `project-context.md`) or
   upstream names, and the dead names are Story 114.2's to correct.
5. **Open keys (column 3).** The open stories whose own text cites the capability. Story 114.1
   (this sweep) and Story 116.5 (the closer) are listed only for the seven capabilities whose
   amendments they render and flip. Story 114.2 is listed where it corrects a capability's words;
   a correction of words alone moves no marker (memlog 2026-11-10, Marker of an amended capability).
   At `82a2b18828` the three open marshal keys, 108.2, 110.38 and 33.11, cite no marshal
   capability: 108.2 cites spec-one-chain-per-station:CAP-5, 110.38 the Guild flag rule, 33.11
   finding F-4 and `hub:CAP-3`.

## Rules applied

- **Grammar** (CHAIN-STANDARD section 4, ruling (c) of 2026-11-10, steward Story 120.3): a marker
  is `(ready <date>[; <qualifier>])`, `(shipped <date>[; <qualifier>])` or
  `(retired <date>[: <reason>])`. No other marker word is written. Each `<-` tail, and any text
  after a marker's date, is kept.
- **Ready** only while a citing story is open. Every other capability with a built story reads
  shipped.
- **Amended capabilities** (decision (g) and the decision Marker of an amended capability, with
  its addendum): CAP-13 and CAP-23 (Story 115.3), CAP-208 (115.4), CAP-227 (115.1), CAP-229
  (115.1 and 114.2), CAP-261 (115.2) and CAP-287 (core-kit 117.3) read `(ready 2026-11-10)` while
  any fix story is open. Under the plan's CLOSE-LEDGERS step none of them reads done at this
  render, so all seven read ready, and Story 116.5 flips them.
- **Console** (ruling (f)): CAP-82 and CAP-93..CAP-96 read `(retired 2026-08-25: ...)`; the
  Guildhall console's `data.js` was deleted, and `docs/dashboard/generate.py` became
  `scripts/fleet_scan.py`, in `e07834580d` (steward Story 30.2). CAP-80, CAP-81, CAP-84..CAP-86
  and CAP-121 stay shipped; CAP-83's fail-loud resolver lives on in `scripts/fleet_scan.py`
  (`UnresolvableProjectError`, FR-143), so it reads shipped too.
- **Never built** (ruling (d)): a capability no story built reads `(retired 2026-11-10: never built)`
  unless a live `blocked` or `backlog` story carries it (then ready, ledger mode `B-only`). The
  sweep found none. CAP-46 has no story, but its success is a dated probe result, recorded PASS
  on 2026-09-15, so it reads shipped.
- **Kept**: a capability that already read `(shipped <date>)` at `82a2b18828` and is neither
  amended nor retired keeps its marker, the fold's from its source Spec.

## Counts

| Group at `82a2b18828` | Rows | After this render |
|---|---|---|
| shipped with a date | 145 | 2 ready, 4 retired, 139 shipped |
| shipped with no date (CAP-293..CAP-297) | 5 | 5 shipped |
| ready (CAP-244..CAP-292) | 49 | 2 ready, 47 shipped |
| no marker | 104 | 3 ready, 1 retired, 100 shipped |
| **all** | **303** | **7 ready, 5 retired, 291 shipped** |

With spec-pyforge-marshal:CAP-304 and spec-pyforge-marshal:CAP-305 the Spec holds 305 capabilities: 291 shipped, 9 ready, 5 retired. No capability reads `(retired 2026-11-10: never built)` and none routes `B-only`.

## Findings beside the markers

- Story 55.1 has no tracked story spec (deferred row DW-marshal-114-1-1, written by Story 116.5).
- Story lines that cite a capability by its pre-fold Spec name (`spec-marshal-token-economy CAP-3`, `token-economy CAP-3`) resolve only through the provenance join (DW-marshal-114-1-2, written by Story 116.5).
- The ledger history dates three landings (CAP-257, CAP-258, CAP-260) the day before the ready date their capability entries carry; the dates are the ledger commits' author dates.

## Table

| CAP | marker | open story keys | evidence | proposed ledger mode |
|---|---|---|---|---|
| CAP-1 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (1.4, 1.5, 1.6, ... 104.1, 110.2 (14 stories); the last, 110.2, done 2026-10-26) | rebuild |
| CAP-2 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (3.1, 3.2, 3.3, ... 82.7, 110.3 (12 stories); the last, 110.3, done 2026-10-26) | rebuild |
| CAP-3 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (2.1, 2.2, 2.3, ... 109.1, 110.4 (12 stories); the last, 110.4, done 2026-10-26) | rebuild |
| CAP-4 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (1.2, 4.1, 4.2, ... 87.9, 88.1 (22 stories); the last, 88.1, done 2026-10-10) | rebuild |
| CAP-5 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (5.1, 5.2, 5.3, ... 82.8, 110.5 (9 stories); the last, 110.5, done 2026-10-26) | rebuild |
| CAP-6 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (1.7, 6.1, 6.2, ... 52.1, 73.2 (11 stories); the last, 73.2, done 2026-10-01) | rebuild |
| CAP-7 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (1.3, 1.10, 3.3, ... 82.7, 110.6 (9 stories); the last, 110.6, done 2026-10-26) | rebuild |
| CAP-8 | (shipped 2026-09-09) | 114.2 | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (1.1, 1.9, 6.8, 12.1, 63.1, 105.1, 106.1, 108.1; the last, 108.1, done 2026-10-26); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-9 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (4.7, 4.8, 4.11, 4.12, 82.2, 82.3, 87.6; the last, 87.6, done 2026-10-09) | rebuild |
| CAP-10 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (7.3, 7.4, 7.5, ... 97.1, 110.7 (9 stories); the last, 110.7, done 2026-10-26) | rebuild |
| CAP-11 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (8.1, 8.2, 8.3, ... 97.2, 110.8 (17 stories); the last, 110.8, done 2026-10-26) | rebuild |
| CAP-12 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (9.2, 9.3, 9.4, ... 108.1, 110.9 (16 stories); the last, 110.9, done 2026-10-26) | rebuild |
| CAP-13 | (ready 2026-11-10) | 114.1, 115.3, 116.5 | ready: fix story 115.3 open (memlog 2026-11-10, CAP-13 amended: the seed exit domain; decision Marker of an amended capability and its addendum); Story 116.5 flips it to shipped, dated the day the last fix story reaches done | rebuild |
| CAP-14 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (7.6, 10.1, 10.7, 104.1, 108.1; the last, 108.1, done 2026-10-26); paths named: 1, all tracked | rebuild |
| CAP-15 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (7.3, 7.4, 7.5, ... 104.1, 108.1 (17 stories); the last, 108.1, done 2026-10-26) | rebuild |
| CAP-16 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (11.1, 110.11; the last, 110.11, done 2026-10-26); paths named: 4, all tracked | rebuild |
| CAP-17 | (shipped 2026-09-09) | 114.2 | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (7.4, 9.3, 10.2, ... 108.1, 110.12 (11 stories); the last, 110.12, done 2026-10-26); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-18 | (shipped 2026-09-09) | 114.2 | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (7.5, 10.1, 82.11; the last, 82.11, done 2026-10-02); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-19 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (3.11, 33.6, 82.6; the last, 82.6, done 2026-10-02); paths named: 1, not tracked: policy.toml | rebuild |
| CAP-20 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (3.12, 33.6, 82.6; the last, 82.6, done 2026-10-02); paths named: 1, not tracked: policy.toml | rebuild |
| CAP-21 | (shipped 2026-10-25) | - | shipped (was no marker): every citing story done (18.1, 103.1); the last, 103.1, reached done 2026-10-25 (ledger history) | rebuild |
| CAP-22 | (shipped 2026-10-25) | - | shipped (was no marker): every citing story done (18.1, 103.1); the last, 103.1, reached done 2026-10-25 (ledger history) | rebuild |
| CAP-23 | (ready 2026-11-10) | 114.1, 115.3, 116.5 | ready: fix story 115.3 open (memlog 2026-11-10, CAP-23 amended: the MCP registration; decision Marker of an amended capability and its addendum); Story 116.5 flips it to shipped, dated the day the last fix story reaches done | rebuild |
| CAP-24 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (18.2); the last, 18.2, reached done 2026-08-23 (ledger history) | rebuild |
| CAP-25 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (37.1, 37.2, 37.3, 37.4, 37.5, 37.6; the last, 37.6, done 2026-09-14) | rebuild |
| CAP-26 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (37.1, 37.2, 37.3, 37.4, 37.5, 37.6; the last, 37.6, done 2026-09-14) | rebuild |
| CAP-27 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (37.1, 37.2, 37.3, 37.4, 37.5, 37.6; the last, 37.6, done 2026-09-14) | rebuild |
| CAP-28 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (37.1, 37.2, 37.3, 37.4, 37.5, 37.6; the last, 37.6, done 2026-09-14) | rebuild |
| CAP-29 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (37.1, 37.2, 37.3, 37.4, 37.5, 37.6; the last, 37.6, done 2026-09-14) | rebuild |
| CAP-30 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (37.1, 37.2, 37.3, 37.4, 37.5, 37.6; the last, 37.6, done 2026-09-14) | rebuild |
| CAP-31 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (37.1, 37.2, 37.3, 37.4, 37.5, 37.6; the last, 37.6, done 2026-09-14) | rebuild |
| CAP-32 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (37.1, 37.2, 37.3, 37.4, 37.5, 37.6; the last, 37.6, done 2026-09-14); paths named: 1, all tracked | rebuild |
| CAP-33 | (shipped 2026-08-22) | - | shipped (was no marker): every citing story done (25.1); the last, 25.1, reached done 2026-08-22 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-34 | (shipped 2026-08-22) | - | shipped (was no marker): every citing story done (25.2); the last, 25.2, reached done 2026-08-22 (ledger history) | rebuild |
| CAP-35 | (shipped 2026-08-22) | - | shipped (was no marker): every citing story done (25.3); the last, 25.3, reached done 2026-08-22 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-36 | (shipped 2026-08-22) | - | shipped (was no marker): every citing story done (25.4); the last, 25.4, reached done 2026-08-22 (ledger history) | rebuild |
| CAP-37 | (shipped 2026-08-22) | - | shipped (was no marker): every citing story done (25.5); the last, 25.5, reached done 2026-08-22 (ledger history) | rebuild |
| CAP-38 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (25.6); the last, 25.6, reached done 2026-08-23 (ledger history) | rebuild |
| CAP-39 | (shipped 2026-09-06) | - | shipped (was no marker): every citing story done (25.7, 30.3); the last, 30.3, reached done 2026-09-06 (ledger history); paths named: 2, not tracked: project-context.md | rebuild |
| CAP-40 | (shipped 2026-09-06) | - | shipped (was no marker): every citing story done (30.1); the last, 30.1, reached done 2026-09-06 (ledger history); paths named: 3, not tracked: removals.txt | rebuild |
| CAP-41 | (shipped 2026-09-06) | - | shipped (was no marker): every citing story done (30.2); the last, 30.2, reached done 2026-09-06 (ledger history); paths named: 5, not tracked: project-context.md | rebuild |
| CAP-42 | (shipped 2026-09-06) | - | shipped (was no marker): every citing story done (30.3); the last, 30.3, reached done 2026-09-06 (ledger history); paths named: 3, not tracked: llms-full.txt, llms.txt | rebuild |
| CAP-43 | (shipped 2026-09-16) | - | shipped (was no marker): every citing story done (30.4); the last, 30.4, reached done 2026-09-16 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-44 | (shipped 2026-09-16) | 114.2 | shipped (was no marker): every citing story done (30.5); the last, 30.5, reached done 2026-09-16 (ledger history); 114.2 corrects its words only and moves no marker; paths named: 4, all tracked | rebuild |
| CAP-45 | (shipped 2026-09-16) | - | shipped (was no marker): every citing story done (31.1); the last, 31.1, reached done 2026-09-16 (ledger history); paths named: 6, not tracked: policy.toml | rebuild |
| CAP-46 | (shipped 2026-09-15) | - | shipped: no story; its success is a dated probe result, recorded PASS in the archived spec-bmad-cursor-interactive-routing memlog on 2026-09-15 (Epic 45 preamble: closed in the Spec memlog, no story); not never-built | rebuild |
| CAP-47 | (shipped 2026-09-16) | - | shipped (was no marker): every citing story done (45.1, 45.2, 45.3); the last, 45.3, reached done 2026-09-16 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-48 | (shipped 2026-09-16) | - | shipped (was no marker): every citing story done (45.1, 45.2, 45.3); the last, 45.3, reached done 2026-09-16 (ledger history) | rebuild |
| CAP-49 | (shipped 2026-09-16) | - | shipped (was no marker): every citing story done (45.1, 45.2, 45.3); the last, 45.3, reached done 2026-09-16 (ledger history); paths named: 5, all tracked | rebuild |
| CAP-50 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.1, 20.2, 20.3, 20.12, 33.7; the last, 20.12, done 2026-09-10); paths named: 1, all tracked | rebuild |
| CAP-51 | (shipped 2026-09-09) | 114.2 | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.1, 20.2, 20.3, 20.12, 33.7; the last, 20.12, done 2026-09-10); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-52 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.1, 20.2, 20.3, 20.12, 33.7; the last, 20.12, done 2026-09-10); paths named: 3, not tracked: engine.py, runs.py | rebuild |
| CAP-53 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (38.1, 38.2, 38.3, 38.4; the last, 38.1, done 2026-09-16) | rebuild |
| CAP-54 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (38.1, 38.2, 38.3, 38.4; the last, 38.1, done 2026-09-16); paths named: 1, all tracked | rebuild |
| CAP-55 | (shipped 2026-09-16) | 114.2 | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (38.1, 38.2, 38.3, 38.4; the last, 38.1, done 2026-09-16); 114.2 corrects its words only and moves no marker; paths named: 2, not tracked: scripts/forward_dependency_check.py | rebuild |
| CAP-56 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (38.1, 38.2, 38.3, 38.4; the last, 38.1, done 2026-09-16); paths named: 1, all tracked | rebuild |
| CAP-57 | (shipped 2026-09-16) | 114.2 | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-bmad-loop-governance); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-58 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-bmad-loop-governance); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-59 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-bmad-loop-governance); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-60 | (shipped 2026-09-16) | 114.2 | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-bmad-loop-governance); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-61 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.3, 20.4, 20.5, 33.7, 87.4, 87.9; the last, 87.9, done 2026-10-09) | rebuild |
| CAP-62 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.3, 20.4, 20.5, 33.7, 87.4, 87.9; the last, 87.9, done 2026-10-09) | rebuild |
| CAP-63 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.3, 20.4, 20.5, 87.4, 87.9; the last, 87.9, done 2026-10-09) | rebuild |
| CAP-64 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (24.1, 24.2, 24.3); the last, 24.3, reached done 2026-08-23 (ledger history) | rebuild |
| CAP-65 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (24.1, 24.2, 24.3); the last, 24.3, reached done 2026-08-23 (ledger history) | rebuild |
| CAP-66 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (24.1, 24.2, 24.3); the last, 24.3, reached done 2026-08-23 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-67 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (41.1, 41.2, 41.3, 41.4; the last, 41.4, done 2026-09-14); paths named: 1, all tracked | rebuild |
| CAP-68 | (shipped 2026-09-16) | 114.2 | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (41.1, 41.2, 41.3, 41.4; the last, 41.4, done 2026-09-14); 114.2 corrects its words only and moves no marker; paths named: 4, not tracked: dashboard_drift_check.py | rebuild |
| CAP-69 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (41.1, 41.2, 41.3, 41.4; the last, 41.4, done 2026-09-14); paths named: 2, not tracked: src/pyforge_genesis | rebuild |
| CAP-70 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (41.1, 41.2, 41.3, 41.4; the last, 41.4, done 2026-09-14); paths named: 3, all tracked | rebuild |
| CAP-71 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (41.1, 41.2, 41.3, 41.4; the last, 41.4, done 2026-09-14); paths named: 2, all tracked | rebuild |
| CAP-72 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (41.1, 41.2, 41.3, 41.4; the last, 41.4, done 2026-09-14); paths named: 4, not tracked: project-context.md | rebuild |
| CAP-73 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (41.1, 41.2, 41.3, 41.4; the last, 41.4, done 2026-09-14); paths named: 5, all tracked | rebuild |
| CAP-74 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (41.1, 41.2, 41.3, 41.4; the last, 41.4, done 2026-09-14); paths named: 4, not tracked: product-brief-pyforge-marshal.md | rebuild |
| CAP-75 | (shipped 2026-10-08) | - | shipped (was no marker): every citing story done (20.6, 20.7, 33.9, 64.1, 69.1); the last, 69.1, reached done 2026-10-08 (ledger history) | rebuild |
| CAP-76 | (shipped 2026-10-08) | - | shipped (was no marker): every citing story done (20.6, 20.7, 33.9, 64.1, 69.1); the last, 69.1, reached done 2026-10-08 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-77 | (shipped 2026-10-08) | - | shipped (was no marker): every citing story done (20.6, 20.7, 64.1, 69.1); the last, 69.1, reached done 2026-10-08 (ledger history) | rebuild |
| CAP-78 | (shipped 2026-09-18) | - | shipped (was no marker): every citing story done (33.15, 50.3); the last, 50.3, reached done 2026-09-18 (ledger history) | rebuild |
| CAP-79 | (shipped 2026-11-04) | - | shipped (was no marker): every citing story done (33.15, 33.16); the last, 33.16, reached done 2026-11-04 (ledger history) | rebuild |
| CAP-80 | (shipped 2026-08-15) | 114.2 | shipped (was no marker): every citing story done (16.1); the last, 16.1, reached done 2026-08-15 (ledger history); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-81 | (shipped 2026-08-15) | 114.2 | shipped (was no marker): every citing story done (16.1); the last, 16.1, reached done 2026-08-15 (ledger history); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-82 | (retired 2026-08-25: the Guildhall console's data.js was deleted and its generator retired in e07834580d, steward Story 30.2) | 114.2 | retired: realized by 16.1, then data.js was deleted and generate.py became scripts/fleet_scan.py in e07834580d on 2026-08-25 (git log --diff-filter=D); ruling (f) of 2026-11-10; 114.2 corrects its words only and moves no marker; paths named: 1, all tracked | retire |
| CAP-83 | (shipped 2026-08-15) | 114.2 | shipped (was no marker): every citing story done (16.1); the last, 16.1, reached done 2026-08-15 (ledger history); 114.2 corrects its words only and moves no marker; paths named: 1, not tracked: scripts/dashboard_drift_check.py | rebuild |
| CAP-84 | (shipped 2026-09-09) | 114.2 | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (23.1, 23.2, 23.3; the last, 23.3, done 2026-08-23); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-85 | (shipped 2026-09-09) | 114.2 | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (23.1, 23.2, 23.3; the last, 23.3, done 2026-08-23); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-86 | (shipped 2026-09-09) | 114.2 | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (23.1, 23.2, 23.3; the last, 23.3, done 2026-08-23); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-87 | (shipped 2026-09-12) | - | kept: (shipped 2026-09-12), the fold's marker from its source Spec; citing stories all done (33.15, 33.16; the last, 33.16, done 2026-11-04) | rebuild |
| CAP-88 | (shipped 2026-09-12) | - | kept: (shipped 2026-09-12), the fold's marker from its source Spec (spec-dispatch-tier-routing-fails-safe); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-89 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (3.10; the last, 3.10, done 2026-08-09) | rebuild |
| CAP-90 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (3.8, 3.9, 4.15; the last, 4.15, done 2026-08-10) | rebuild |
| CAP-91 | (shipped 2026-09-16) | 114.2 | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (4.14, 5.5, 82.8, 87.2, 87.9; the last, 87.9, done 2026-10-09); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-92 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (4.10, 87.6; the last, 87.6, done 2026-10-09) | rebuild |
| CAP-93 | (retired 2026-08-25: the Guildhall console's data.js was deleted and its generator retired in e07834580d, steward Story 30.2) | 114.2 | retired: realized by its source Spec, then data.js was deleted and generate.py became scripts/fleet_scan.py in e07834580d on 2026-08-25 (git log --diff-filter=D); ruling (f) of 2026-11-10; 114.2 corrects its words only and moves no marker; paths named: 2, not tracked: data.js | retire |
| CAP-94 | (retired 2026-08-25: the Guildhall console's data.js was deleted and its generator retired in e07834580d, steward Story 30.2) | 114.2 | retired: realized by its source Spec, then data.js was deleted and generate.py became scripts/fleet_scan.py in e07834580d on 2026-08-25 (git log --diff-filter=D); ruling (f) of 2026-11-10; 114.2 corrects its words only and moves no marker; paths named: 1, not tracked: data.js | retire |
| CAP-95 | (retired 2026-08-25: the Guildhall console's data.js was deleted and its generator retired in e07834580d, steward Story 30.2) | 114.2 | retired: realized by its source Spec, then data.js was deleted and generate.py became scripts/fleet_scan.py in e07834580d on 2026-08-25 (git log --diff-filter=D); ruling (f) of 2026-11-10; 114.2 corrects its words only and moves no marker | retire |
| CAP-96 | (retired 2026-08-25: the Guildhall console's data.js was deleted and its generator retired in e07834580d, steward Story 30.2) | 114.2 | retired: realized by 5.7, then data.js was deleted and generate.py became scripts/fleet_scan.py in e07834580d on 2026-08-25 (git log --diff-filter=D); ruling (f) of 2026-11-10; 114.2 corrects its words only and moves no marker; paths named: 1, not tracked: data.js | retire |
| CAP-97 | (shipped 2026-09-16) | 114.2 | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-fidelity-enforcement); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-98 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-fidelity-enforcement); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-99 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (2.7; the last, 2.7, done 2026-08-06) | rebuild |
| CAP-100 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-fidelity-enforcement); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-101 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-fidelity-enforcement); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-102 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (17.4, 21.1, 21.2, 21.3, 21.4, 21.5); the last, 21.5, reached done 2026-08-23 (ledger history) | rebuild |
| CAP-103 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (17.4, 21.1, 21.2, 21.3, 21.4, 21.5); the last, 21.5, reached done 2026-08-23 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-104 | (shipped 2026-08-23) | 114.2 | shipped (was no marker): every citing story done (17.3, 21.1, 21.2, 21.3, 21.4, 21.5); the last, 21.5, reached done 2026-08-23 (ledger history); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-105 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (17.4, 21.1, 21.2, 21.3, 21.4, 21.5); the last, 21.5, reached done 2026-08-23 (ledger history); paths named: 2, not tracked: orphans.json, orphans.md | rebuild |
| CAP-106 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (17.3, 21.1, 21.2, 21.3, 21.4, 21.5); the last, 21.5, reached done 2026-08-23 (ledger history) | rebuild |
| CAP-107 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (32.1; the last, 32.1, done 2026-09-07); paths named: 2, all tracked | rebuild |
| CAP-108 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (32.5, 32.8; the last, 32.8, done 2026-09-08); paths named: 2, all tracked | rebuild |
| CAP-109 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (32.4; the last, 32.4, done 2026-09-07); paths named: 5, all tracked | rebuild |
| CAP-110 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (32.3; the last, 32.3, done 2026-09-07); paths named: 1, all tracked | rebuild |
| CAP-111 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (32.2, 32.8; the last, 32.8, done 2026-09-08); paths named: 1, all tracked | rebuild |
| CAP-112 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (32.6, 33.10, 43.1; the last, 43.1, done 2026-09-16); paths named: 5, all tracked | rebuild |
| CAP-113 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (5.8, 82.2; the last, 82.2, done 2026-10-02) | rebuild |
| CAP-114 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (5.8, 82.2; the last, 82.2, done 2026-10-02); paths named: 1, all tracked | rebuild |
| CAP-115 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (40.1, 40.2, 40.3, 40.4, 40.5; the last, 40.5, done 2026-09-14); paths named: 3, all tracked | rebuild |
| CAP-116 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (40.1, 40.2, 40.3, 40.4, 40.5; the last, 40.5, done 2026-09-14); paths named: 1, all tracked | rebuild |
| CAP-117 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (40.1, 40.2, 40.3, 40.4, 40.5; the last, 40.5, done 2026-09-14); paths named: 2, all tracked | rebuild |
| CAP-118 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (40.1, 40.2, 40.3, 40.4, 40.5; the last, 40.5, done 2026-09-14) | rebuild |
| CAP-119 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (40.1, 40.2, 40.3, 40.4, 40.5; the last, 40.5, done 2026-09-14) | rebuild |
| CAP-120 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (40.1, 40.2, 40.3, 40.4, 40.5; the last, 40.5, done 2026-09-14); paths named: 1, all tracked | rebuild |
| CAP-121 | (shipped 2026-09-16) | 114.2 | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (40.1, 40.2, 40.3, 40.4, 40.5; the last, 40.5, done 2026-09-14); 114.2 corrects its words only and moves no marker; paths named: 1, not tracked: scripts/dashboard_drift_check.py | rebuild |
| CAP-122 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (40.1, 40.2, 40.3, 40.4, 40.5; the last, 40.5, done 2026-09-14); paths named: 1, all tracked | rebuild |
| CAP-123 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (3.13; the last, 3.13, done 2026-08-12) | rebuild |
| CAP-124 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (3.13; the last, 3.13, done 2026-08-12); paths named: 1, all tracked | rebuild |
| CAP-125 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (3.13; the last, 3.13, done 2026-08-12) | rebuild |
| CAP-126 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.8, 20.9, 20.10, 20.11; the last, 20.11, done 2026-08-28) | rebuild |
| CAP-127 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.8, 20.9, 20.10, 20.11; the last, 20.11, done 2026-08-28) | rebuild |
| CAP-128 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.8, 20.9, 20.10, 20.11; the last, 20.11, done 2026-08-28); paths named: 1, all tracked | rebuild |
| CAP-129 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (20.8, 20.9, 20.10, 20.11; the last, 20.11, done 2026-08-28); paths named: 2, all tracked | rebuild |
| CAP-130 | (shipped 2026-09-12) | - | kept: (shipped 2026-09-12), the fold's marker from its source Spec; citing stories all done (36.1; the last, 36.1, done 2026-09-16); paths named: 3, all tracked | rebuild |
| CAP-131 | (shipped 2026-09-12) | - | kept: (shipped 2026-09-12), the fold's marker from its source Spec; citing stories all done (36.2; the last, 36.2, done 2026-09-16); paths named: 2, all tracked | rebuild |
| CAP-132 | (shipped 2026-10-25) | - | shipped (was no marker): every citing story done (15.1, 104.1, 107.1); the last, 107.1, reached done 2026-10-25 (ledger history) | rebuild |
| CAP-133 | (shipped 2026-10-25) | - | shipped (was no marker): every citing story done (15.1, 104.1); the last, 104.1, reached done 2026-10-25 (ledger history) | rebuild |
| CAP-134 | (shipped 2026-10-25) | - | shipped (was no marker): every citing story done (15.1, 107.1); the last, 107.1, reached done 2026-10-25 (ledger history); paths named: 1, not tracked: policy.toml | rebuild |
| CAP-135 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.18, 82.10; the last, 82.10, done 2026-10-02) | rebuild |
| CAP-136 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.19; the last, 28.19, done 2026-09-01) | rebuild |
| CAP-137 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (22.18, 22.19, 28.20, 58.1, 59.1; the last, 22.19, done 2026-10-07); paths named: 1, all tracked | rebuild |
| CAP-138 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.20, 28.21, 28.26; the last, 28.26, done 2026-09-16) | rebuild |
| CAP-139 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.22, 98.1; the last, 98.1, done 2026-10-12) | rebuild |
| CAP-140 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.23; the last, 28.23, done 2026-09-01) | rebuild |
| CAP-141 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.24, 28.25, 88.1, 90.1, 92.1, 110.13; the last, 110.13, done 2026-10-26) | rebuild |
| CAP-142 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec (spec-marshal-land-cross-project-story-key-collision); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-143 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (5.10, 82.3; the last, 82.3, done 2026-10-02) | rebuild |
| CAP-144 | (shipped 2026-09-11) | - | kept: (shipped 2026-09-11), the fold's marker from its source Spec (spec-marshal-launch-environment-integrity); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain); paths named: 1, all tracked | rebuild |
| CAP-145 | (shipped 2026-09-11) | - | kept: (shipped 2026-09-11), the fold's marker from its source Spec (spec-marshal-launch-environment-integrity); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-146 | (shipped 2026-09-11) | - | kept: (shipped 2026-09-11), the fold's marker from its source Spec (spec-marshal-launch-environment-integrity); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-147 | (shipped 2026-09-11) | - | kept: (shipped 2026-09-11), the fold's marker from its source Spec (spec-marshal-launch-environment-integrity); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain); paths named: 1, all tracked | rebuild |
| CAP-148 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.16, 33.8; the last, 33.8, done 2026-09-16) | rebuild |
| CAP-149 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.16, 33.8; the last, 33.8, done 2026-09-16) | rebuild |
| CAP-150 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.16, 33.8; the last, 33.8, done 2026-09-16) | rebuild |
| CAP-151 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.16, 33.8; the last, 33.8, done 2026-09-16); paths named: 1, all tracked | rebuild |
| CAP-152 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.16, 33.8; the last, 33.8, done 2026-09-16) | rebuild |
| CAP-153 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (33.8; the last, 33.8, done 2026-09-16); paths named: 2, all tracked | rebuild |
| CAP-154 | (shipped 2026-10-26) | - | shipped (was no marker): every citing story done (44.1, 44.2, 44.3, 44.4, 110.14); the last, 110.14, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-155 | (shipped 2026-09-15) | - | shipped (was no marker): every citing story done (44.1, 44.2, 44.3, 44.4); the last, 44.4, reached done 2026-09-15 (ledger history) | rebuild |
| CAP-156 | (shipped 2026-09-15) | - | shipped (was no marker): every citing story done (44.1, 44.2, 44.3, 44.4); the last, 44.4, reached done 2026-09-15 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-157 | (shipped 2026-09-15) | - | shipped (was no marker): every citing story done (44.1, 44.2, 44.3, 44.4); the last, 44.4, reached done 2026-09-15 (ledger history) | rebuild |
| CAP-158 | (shipped 2026-09-15) | - | shipped (was no marker): every citing story done (44.1, 44.2, 44.3, 44.4); the last, 44.4, reached done 2026-09-15 (ledger history) | rebuild |
| CAP-159 | (shipped 2026-10-15) | 114.2 | shipped (was no marker): every citing story done (19.4, 22.1, 22.2, ... 87.5, 102.1 (18 stories)); the last, 102.1, reached done 2026-10-15 (ledger history); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-160 | (shipped 2026-10-26) | - | shipped (was no marker): every citing story done (19.4, 22.1, 22.2, ... 102.1, 110.15 (21 stories)); the last, 110.15, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-161 | (shipped 2026-10-26) | - | shipped (was no marker): every citing story done (19.4, 22.1, 22.2, ... 102.1, 110.16 (25 stories)); the last, 110.16, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-162 | (shipped 2026-10-26) | - | shipped (was no marker): every citing story done (19.4, 22.1, 22.2, ... 102.1, 110.17 (25 stories)); the last, 110.17, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-163 | (shipped 2026-10-26) | - | shipped (was no marker): every citing story done (19.4, 22.1, 22.2, ... 102.1, 110.18 (20 stories)); the last, 110.18, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-164 | (shipped 2026-10-15) | - | shipped (was no marker): every citing story done (19.4, 22.1, 22.2, ... 87.5, 102.1 (18 stories)); the last, 102.1, reached done 2026-10-15 (ledger history) | rebuild |
| CAP-165 | (shipped 2026-08-27) | - | shipped (was no marker): every citing story done (22.8); the last, 22.8, reached done 2026-08-27 (ledger history); paths named: 3, not tracked: policy.toml | rebuild |
| CAP-166 | (shipped 2026-10-15) | 114.2 | shipped (was no marker): every citing story done (19.4, 22.1, 22.2, ... 87.5, 102.1 (18 stories)); the last, 102.1, reached done 2026-10-15 (ledger history); 114.2 corrects its words only and moves no marker; paths named: 2, all tracked | rebuild |
| CAP-167 | (shipped 2026-10-26) | - | shipped (was no marker): every citing story done (22.10, 90.1, 92.1, 110.19); the last, 110.19, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-168 | (shipped 2026-08-30) | - | shipped (was no marker): every citing story done (22.11); the last, 22.11, reached done 2026-08-30 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-169 | (shipped 2026-10-26) | - | shipped (was no marker): every citing story done (22.17, 89.1, 94.1, 94.2, 96.1, 110.20); the last, 110.20, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-170 | (shipped 2026-10-11) | - | shipped (was no marker): every citing story done (22.12, 22.14, 91.1); the last, 91.1, reached done 2026-10-11 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-171 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (39.1, 39.2; the last, 39.2, done 2026-09-14); paths named: 1, all tracked | rebuild |
| CAP-172 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (39.1, 39.2; the last, 39.2, done 2026-09-14) | rebuild |
| CAP-173 | (shipped 2026-09-11) | - | kept: (shipped 2026-09-11), the fold's marker from its source Spec; citing stories all done (35.1, 50.4; the last, 50.4, done 2026-09-18); paths named: 1, all tracked | rebuild |
| CAP-174 | (shipped 2026-10-26) | - | shipped (was no marker): every citing story done (28.1, 33.2, 33.3, 93.1, 110.21); the last, 110.21, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-175 | (shipped 2026-09-12) | - | shipped (was no marker): every citing story done (28.2, 28.29, 33.2); the last, 28.29, reached done 2026-09-12 (ledger history) | rebuild |
| CAP-176 | (shipped 2026-09-24) | - | shipped (was no marker): every citing story done (28.3, 28.30, 28.31, 28.32, 28.33, 33.4, 55.1); the last, 55.1, reached done 2026-09-24 (ledger history) | rebuild |
| CAP-177 | (shipped 2026-08-31) | - | shipped (was no marker): every citing story done (28.3); the last, 28.3, reached done 2026-08-31 (ledger history) | rebuild |
| CAP-178 | (shipped 2026-09-10) | - | shipped (was no marker): every citing story done (28.8, 28.28, 28.32, 33.2); the last, 28.32, reached done 2026-09-10 (ledger history) | rebuild |
| CAP-179 | (shipped 2026-09-10) | - | shipped (was no marker): every citing story done (28.9, 28.27, 28.28, 33.2); the last, 28.28, reached done 2026-09-10 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-180 | (shipped 2026-09-12) | - | shipped (was no marker): every citing story done (28.4, 33.1, 33.4); the last, 33.4, reached done 2026-09-12 (ledger history) | rebuild |
| CAP-181 | (shipped 2026-09-01) | - | shipped (was no marker): every citing story done (28.6); the last, 28.6, reached done 2026-09-01 (ledger history) | rebuild |
| CAP-182 | (shipped 2026-09-09) | - | shipped (was no marker): every citing story done (28.5, 33.1); the last, 33.1, reached done 2026-09-09 (ledger history) | rebuild |
| CAP-183 | (shipped 2026-09-01) | - | shipped (was no marker): every citing story done (28.7); the last, 28.7, reached done 2026-09-01 (ledger history) | rebuild |
| CAP-184 | (shipped 2026-09-01) | - | shipped (was no marker): every citing story done (28.10); the last, 28.10, reached done 2026-09-01 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-185 | (shipped 2026-09-01) | - | shipped (was no marker): every citing story done (28.11); the last, 28.11, reached done 2026-09-01 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-186 | (shipped 2026-09-10) | - | shipped (was no marker): every citing story done (28.9, 28.27); the last, 28.27, reached done 2026-09-10 (ledger history) | rebuild |
| CAP-187 | (shipped 2026-09-01) | - | shipped (was no marker): every citing story done (28.12); the last, 28.12, reached done 2026-09-01 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-188 | (shipped 2026-09-01) | - | shipped (was no marker): every citing story done (28.13); the last, 28.13, reached done 2026-09-01 (ledger history) | rebuild |
| CAP-189 | (shipped 2026-08-31) | - | shipped (was no marker): every citing story done (28.14); the last, 28.14, reached done 2026-08-31 (ledger history); paths named: 3, all tracked | rebuild |
| CAP-190 | (shipped 2026-10-01) | - | shipped (was no marker): every citing story done (28.15, 33.4, 79.2); the last, 79.2, reached done 2026-10-01 (ledger history) | rebuild |
| CAP-191 | (shipped 2026-09-12) | - | shipped (was no marker): every citing story done (33.4); the last, 33.4, reached done 2026-09-12 (ledger history); paths named: 3, all tracked | rebuild |
| CAP-192 | (shipped 2026-10-08) | - | shipped (was no marker): every citing story done (46.1, 46.2, 46.3, ... 46.11, 46.12 (12 stories)); the last, 46.9, reached done 2026-10-08 (ledger history) | rebuild |
| CAP-193 | (shipped 2026-10-08) | - | shipped (was no marker): every citing story done (46.1, 46.2, 46.3, ... 46.11, 46.12 (12 stories)); the last, 46.9, reached done 2026-10-08 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-194 | (shipped 2026-10-08) | - | shipped (was no marker): every citing story done (46.1, 46.2, 46.3, ... 46.11, 46.12 (12 stories)); the last, 46.9, reached done 2026-10-08 (ledger history) | rebuild |
| CAP-195 | (shipped 2026-10-08) | - | shipped (was no marker): every citing story done (46.1, 46.2, 46.3, ... 46.11, 46.12 (12 stories)); the last, 46.9, reached done 2026-10-08 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-196 | (shipped 2026-10-08) | - | shipped (was no marker): every citing story done (46.1, 46.2, 46.3, ... 46.11, 46.12 (12 stories)); the last, 46.9, reached done 2026-10-08 (ledger history) | rebuild |
| CAP-197 | (shipped 2026-10-08) | - | shipped (was no marker): every citing story done (46.1, 46.2, 46.3, ... 46.11, 46.12 (12 stories)); the last, 46.9, reached done 2026-10-08 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-198 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.17; the last, 28.17, done 2026-09-01) | rebuild |
| CAP-199 | (shipped 2026-09-09) | 114.2 | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.17; the last, 28.17, done 2026-09-01); 114.2 corrects its words only and moves no marker | rebuild |
| CAP-200 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (28.17; the last, 28.17, done 2026-09-01) | rebuild |
| CAP-201 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (69.1; the last, 69.1, done 2026-10-08) | rebuild |
| CAP-202 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-multi-loop-isolation); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-203 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-multi-loop-isolation); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-204 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-one-front-door); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-205 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (5.6; the last, 5.6, done 2026-08-07) | rebuild |
| CAP-206 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (4.7, 4.8, 87.6; the last, 87.6, done 2026-10-09) | rebuild |
| CAP-207 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (5.6; the last, 5.6, done 2026-08-07) | rebuild |
| CAP-208 | (ready 2026-11-10) | 114.1, 115.4, 116.5 | ready: fix story 115.4 open (memlog 2026-11-10, CAP-208 amended: the root-of-record forge; decision Marker of an amended capability and its addendum); Story 116.5 flips it to shipped, dated the day the last fix story reaches done | rebuild |
| CAP-209 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (4.8, 4.12, 82.2; the last, 82.2, done 2026-10-02) | rebuild |
| CAP-210 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (4.8, 4.11, 82.2; the last, 82.2, done 2026-10-02) | rebuild |
| CAP-211 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (4.8; the last, 4.8, done 2026-08-06) | rebuild |
| CAP-212 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (5.9, 82.3; the last, 82.3, done 2026-10-02) | rebuild |
| CAP-213 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (5.9, 82.3; the last, 82.3, done 2026-10-02); paths named: 1, all tracked | rebuild |
| CAP-214 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (5.9, 82.3; the last, 82.3, done 2026-10-02) | rebuild |
| CAP-215 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (5.9, 82.3; the last, 82.3, done 2026-10-02) | rebuild |
| CAP-216 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-regenerable-factory); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-217 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-regenerable-factory); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain); paths named: 1, all tracked | rebuild |
| CAP-218 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-regenerable-factory); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-219 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec (spec-regenerable-factory); no epics.md story cites it by number, provenance or FR (built under its source Spec's own chain) | rebuild |
| CAP-220 | (shipped 2026-09-09) | - | shipped (was no marker): every citing story done (2.8, 33.5); the last, 33.5, reached done 2026-09-09 (ledger history) | rebuild |
| CAP-221 | (shipped 2026-09-09) | - | shipped (was no marker): every citing story done (2.8, 33.5); the last, 33.5, reached done 2026-09-09 (ledger history) | rebuild |
| CAP-222 | (shipped 2026-09-09) | - | shipped (was no marker): every citing story done (2.8, 33.5); the last, 33.5, reached done 2026-09-09 (ledger history) | rebuild |
| CAP-223 | (shipped 2026-09-09) | - | shipped (was no marker): every citing story done (2.8, 33.5); the last, 33.5, reached done 2026-09-09 (ledger history) | rebuild |
| CAP-224 | (shipped 2026-09-12) | - | shipped (was no marker): every citing story done (33.12); the last, 33.12, reached done 2026-09-12 (ledger history) | rebuild |
| CAP-225 | (shipped 2026-09-12) | - | shipped (was no marker): every citing story done (33.12); the last, 33.12, reached done 2026-09-12 (ledger history) | rebuild |
| CAP-226 | (shipped 2026-09-12) | - | shipped (was no marker): every citing story done (33.13); the last, 33.13, reached done 2026-09-12 (ledger history) | rebuild |
| CAP-227 | (ready 2026-11-10) | 114.1, 115.1, 116.5 | ready: fix story 115.1 open (memlog 2026-11-10, CAP-227 amended: a loop-home guard that can fire; decision Marker of an amended capability and its addendum); Story 116.5 flips it to shipped, dated the day the last fix story reaches done; paths named: 2, all tracked | rebuild |
| CAP-228 | (shipped 2026-09-12) | - | shipped (was no marker): every citing story done (33.12, 33.14); the last, 33.14, reached done 2026-09-12 (ledger history) | rebuild |
| CAP-229 | (ready 2026-11-10) | 114.1, 114.2, 115.1, 116.5 | ready: fix stories 115.1 and 114.2 open (memlog 2026-11-10, CAP-229 amended: the guarded checkout root; decision Marker of an amended capability and its addendum); Story 116.5 flips it to shipped, dated the day the last fix story reaches done; paths named: 3, not tracked: data.js | rebuild |
| CAP-230 | (shipped 2026-08-23) | 114.2 | shipped (was no marker): every citing story done (15.2); the last, 15.2, reached done 2026-08-23 (ledger history); 114.2 corrects its words only and moves no marker; paths named: 3, not tracked: dashboard_drift_check.py, data.js, forward_dependency_check.py | rebuild |
| CAP-231 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (15.2); the last, 15.2, reached done 2026-08-23 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-232 | (shipped 2026-08-23) | - | shipped (was no marker): every citing story done (15.2); the last, 15.2, reached done 2026-08-23 (ledger history) | rebuild |
| CAP-233 | (shipped 2026-10-01) | - | shipped (was no marker): every citing story done (79.1); the last, 79.1, reached done 2026-10-01 (ledger history) | rebuild |
| CAP-234 | (shipped 2026-09-16) | - | kept: (shipped 2026-09-16), the fold's marker from its source Spec; citing stories all done (15.2, 54.1; the last, 54.1, done 2026-10-08) | rebuild |
| CAP-235 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (13.1, 82.3; the last, 82.3, done 2026-10-02) | rebuild |
| CAP-236 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (13.2; the last, 13.2, done 2026-08-08) | rebuild |
| CAP-237 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (13.3, 13.4; the last, 13.4, done 2026-08-08) | rebuild |
| CAP-238 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (13.1, 13.2; the last, 13.2, done 2026-08-08) | rebuild |
| CAP-239 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (13.7, 53.1; the last, 53.1, done 2026-09-20); paths named: 1, all tracked | rebuild |
| CAP-240 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (13.6; the last, 13.6, done 2026-08-08) | rebuild |
| CAP-241 | (shipped 2026-09-09) | - | kept: (shipped 2026-09-09), the fold's marker from its source Spec; citing stories all done (13.5; the last, 13.5, done 2026-08-08); paths named: 1, all tracked | rebuild |
| CAP-242 | (shipped 2026-09-16) | - | shipped (was no marker): every citing story done (42.1, 42.2); the last, 42.2, reached done 2026-09-16 (ledger history) | rebuild |
| CAP-243 | (shipped 2026-09-16) | - | shipped (was no marker): every citing story done (42.1, 42.2); the last, 42.2, reached done 2026-09-16 (ledger history) | rebuild |
| CAP-244 | (shipped 2026-09-18) | - | shipped (was (ready 2026-09-18)): every citing story done (5.11, 50.1, 50.2, 50.3, 50.4, 50.5); the last, 50.5, reached done 2026-09-18 (ledger history) | rebuild |
| CAP-245 | (shipped 2026-09-18) | - | shipped (was (ready 2026-09-18)): every citing story done (50.1, 50.2, 50.3, 50.4, 50.5); the last, 50.5, reached done 2026-09-18 (ledger history) | rebuild |
| CAP-246 | (shipped 2026-09-18) | - | shipped (was (ready 2026-09-18)): every citing story done (50.1, 50.2, 50.3, 50.4, 50.5); the last, 50.5, reached done 2026-09-18 (ledger history) | rebuild |
| CAP-247 | (shipped 2026-09-18) | - | shipped (was (ready 2026-09-18)): every citing story done (50.1, 50.2, 50.3, 50.4, 50.5); the last, 50.5, reached done 2026-09-18 (ledger history) | rebuild |
| CAP-248 | (shipped 2026-09-18) | - | shipped (was (ready 2026-09-18)): every citing story done (50.1, 50.2, 50.3, 50.4, 50.5); the last, 50.5, reached done 2026-09-18 (ledger history) | rebuild |
| CAP-249 | (shipped 2026-09-19) | - | shipped (was (ready 2026-09-19)): every citing story done (51.1, 51.2, 51.3, ... 51.12, 51.13 (13 stories)); the last, 51.13, reached done 2026-09-19 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-250 | (shipped 2026-09-19) | - | shipped (was (ready 2026-09-19)): every citing story done (51.1, 51.2, 51.3, ... 51.12, 51.13 (13 stories)); the last, 51.13, reached done 2026-09-19 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-251 | (shipped 2026-10-01) | - | shipped (was (ready 2026-09-19)): every citing story done (51.1, 51.2, 51.3, ... 51.13, 67.1 (14 stories)); the last, 67.1, reached done 2026-10-01 (ledger history) | rebuild |
| CAP-252 | (shipped 2026-09-19; widened 2026-09-19 after the 51.3 hollow landing) | - | shipped (was (ready 2026-09-19; widened 2026-09-19 after the 51.3 hollow landing)): every citing story done (51.1, 51.2, 51.3, ... 51.12, 51.13 (13 stories)); the last, 51.13, reached done 2026-09-19 (ledger history) | rebuild |
| CAP-253 | (shipped 2026-09-19) | - | shipped (was (ready 2026-09-19)): every citing story done (51.1, 51.2, 51.3, ... 51.12, 51.13 (13 stories)); the last, 51.13, reached done 2026-09-19 (ledger history) | rebuild |
| CAP-254 | (shipped 2026-09-19) | - | shipped (was (ready 2026-09-19)): every citing story done (51.1, 51.2, 51.3, ... 51.12, 51.13 (13 stories)); the last, 51.13, reached done 2026-09-19 (ledger history) | rebuild |
| CAP-255 | (shipped 2026-09-19) | - | shipped (was (ready 2026-09-19)): every citing story done (51.1, 51.2, 51.3, ... 51.12, 51.13 (13 stories)); the last, 51.13, reached done 2026-09-19 (ledger history); paths named: 5, all tracked | rebuild |
| CAP-256 | (shipped 2026-09-19) | - | shipped (was (ready 2026-09-19)): every citing story done (51.1, 51.2, 51.3, ... 51.12, 51.13 (13 stories)); the last, 51.13, reached done 2026-09-19 (ledger history); paths named: 6, all tracked | rebuild |
| CAP-257 | (shipped 2026-09-19) | - | shipped (was (ready 2026-09-20)): every citing story done (51.10); the last, 51.10, reached done 2026-09-19 (ledger history); paths named: 1, all tracked; the ledger history dates the landing 2026-09-19, a day before the 2026-09-20 ready date its capability entry carries | rebuild |
| CAP-258 | (shipped 2026-09-19) | - | shipped (was (ready 2026-09-20)): every citing story done (51.11); the last, 51.11, reached done 2026-09-19 (ledger history); the ledger history dates the landing 2026-09-19, a day before the 2026-09-20 ready date its capability entry carries | rebuild |
| CAP-259 | (shipped 2026-10-26) | - | shipped (was (ready 2026-09-20)): every citing story done (51.12, 110.23); the last, 110.23, reached done 2026-10-26 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-260 | (shipped 2026-09-19) | - | shipped (was (ready 2026-09-20)): every citing story done (51.13); the last, 51.13, reached done 2026-09-19 (ledger history); paths named: 3, all tracked; the ledger history dates the landing 2026-09-19, a day before the 2026-09-20 ready date its capability entry carries | rebuild |
| CAP-261 | (ready 2026-11-10) | 114.1, 115.2, 116.5 | ready: fix story 115.2 open (memlog 2026-11-10, CAP-261 amended: Doctor's verdict by command; decision Marker of an amended capability and its addendum); Story 116.5 flips it to shipped, dated the day the last fix story reaches done; paths named: 1, all tracked | rebuild |
| CAP-262 | (shipped 2026-09-20) | - | shipped (was (ready 2026-09-20)): every citing story done (46.11); the last, 46.11, reached done 2026-09-20 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-263 | (shipped 2026-10-26) | - | shipped (was (ready 2026-09-20)): every citing story done (46.12, 110.24); the last, 110.24, reached done 2026-10-26 (ledger history); paths named: 3, all tracked | rebuild |
| CAP-264 | (shipped 2026-09-20) | 114.2 | shipped (was (ready 2026-09-20)): every citing story done (53.3); the last, 53.3, reached done 2026-09-20 (ledger history); 114.2 corrects its words only and moves no marker; paths named: 2, not tracked: coverage_thresholds.toml | rebuild |
| CAP-265 | (shipped 2026-10-25; re-scoped 2026-09-28) | - | shipped (was (ready 2026-09-24; re-scoped 2026-09-28)): every citing story done (54.1, 107.1); the last, 107.1, reached done 2026-10-25 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-266 | (shipped 2026-09-27; amended 2026-09-27, Story 56.1 review 1) | - | shipped (was (ready 2026-09-27; amended 2026-09-27, Story 56.1 review 1)): every citing story done (56.1); the last, 56.1, reached done 2026-09-27 (ledger history) | rebuild |
| CAP-267 | (shipped 2026-10-26; amended 2026-09-27, Story 57.1 review 2) | - | shipped (was (ready 2026-09-27; amended 2026-09-27, Story 57.1 review 2)): every citing story done (57.1, 60.1, 68.1, 110.25); the last, 110.25, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-268 | (shipped 2026-09-27; amended 2026-09-27, Story 58.1 review 1) | - | shipped (was (ready 2026-09-27; amended 2026-09-27, Story 58.1 review 1)): every citing story done (58.1); the last, 58.1, reached done 2026-09-27 (ledger history) | rebuild |
| CAP-269 | (shipped 2026-10-10; amended 2026-09-27, Story 59.1 reviews 1 and 2) | - | shipped (was (ready 2026-09-27; amended 2026-09-27, Story 59.1 reviews 1 and 2)): every citing story done (59.1, 60.1, 88.1); the last, 88.1, reached done 2026-10-10 (ledger history) | rebuild |
| CAP-270 | (shipped 2026-10-01; amended 2026-09-27, Story 60.1 reviews 1 and 2) | - | shipped (was (ready 2026-09-27; amended 2026-09-27, Story 60.1 reviews 1 and 2)): every citing story done (60.1, 61.1, 62.1, 72.1); the last, 72.1, reached done 2026-10-01 (ledger history); paths named: 3, all tracked | rebuild |
| CAP-271 | (shipped 2026-09-27; amended 2026-09-27, Story 61.1 reviews 1-3) | - | shipped (was (ready 2026-09-27; amended 2026-09-27, Story 61.1 reviews 1-3)): every citing story done (61.1); the last, 61.1, reached done 2026-09-27 (ledger history); paths named: 5, all tracked | rebuild |
| CAP-272 | (shipped 2026-09-27) | - | shipped (was (ready 2026-09-27)): every citing story done (62.1); the last, 62.1, reached done 2026-09-27 (ledger history) | rebuild |
| CAP-273 | (shipped 2026-09-28) | - | shipped (was (ready 2026-09-27)): every citing story done (64.1); the last, 64.1, reached done 2026-09-28 (ledger history); paths named: 2, not tracked: _bmad/custom/.active-project | rebuild |
| CAP-274 | (shipped 2026-10-08) | - | shipped (was (ready 2026-09-27)): every citing story done (65.1, 65.2, 81.2); the last, 65.2, reached done 2026-10-08 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-275 | (shipped 2026-10-26) | - | shipped (was (ready 2026-09-28)): every citing story done (22.21, 66.1, 66.2, 73.1, 96.1, 110.26); the last, 110.26, reached done 2026-10-26 (ledger history); paths named: 3, all tracked | rebuild |
| CAP-276 | (shipped 2026-10-01) | - | shipped (was (ready 2026-09-28)): every citing story done (67.1, 72.1); the last, 72.1, reached done 2026-10-01 (ledger history) | rebuild |
| CAP-277 | (shipped 2026-10-26) | - | shipped (was (ready 2026-09-28)): every citing story done (68.1, 79.1, 79.2, 110.27); the last, 110.27, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-278 | (shipped 2026-10-26) | - | shipped (was (ready 2026-09-28)): every citing story done (69.1, 110.28); the last, 110.28, reached done 2026-10-26 (ledger history); paths named: 3, all tracked | rebuild |
| CAP-279 | (shipped 2026-10-26; amended 2026-09-28) | - | shipped (was (ready 2026-09-28; amended 2026-09-28)): every citing story done (70.1, 70.2, 97.2, 110.29); the last, 110.29, reached done 2026-10-26 (ledger history); paths named: 6, not tracked: _bmad/custom/.active-project, docs/dreams/demo.md | rebuild |
| CAP-280 | (shipped 2026-10-02; widened 2026-09-28) | - | shipped (was (ready 2026-09-28; widened 2026-09-28)): every citing story done (72.1, 73.1, 82.8); the last, 82.8, reached done 2026-10-02 (ledger history); paths named: 4, all tracked | rebuild |
| CAP-281 | (shipped 2026-10-26; amended 2026-09-28; amended 2026-10-01) | - | shipped (was (ready 2026-09-28; amended 2026-09-28; amended 2026-10-01)): every citing story done (22.21, 73.1, 73.2, 110.30); the last, 110.30, reached done 2026-10-26 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-282 | (shipped 2026-10-26) | - | shipped (was (ready 2026-09-29)): every citing story done (77.1, 110.31); the last, 110.31, reached done 2026-10-26 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-283 | (shipped 2026-10-26) | - | shipped (was (ready 2026-09-30)): every citing story done (78.1, 83.3, 83.11, 83.13, 110.32); the last, 110.32, reached done 2026-10-26 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-284 | (shipped 2026-10-15) | - | shipped (was (ready 2026-10-01)): every citing story done (22.18, 22.19, 22.21, 80.1, 102.1); the last, 102.1, reached done 2026-10-15 (ledger history) | rebuild |
| CAP-285 | (shipped 2026-10-26) | - | shipped (was (ready 2026-10-02)): every citing story done (84.1, 84.2, 110.33); the last, 110.33, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-286 | (shipped 2026-10-10) | - | shipped (was (ready 2026-10-03)): every citing story done (22.20, 85.1, 85.2, 85.3, 85.4, 85.5, 85.6, 85.7); the last, 85.7, reached done 2026-10-10 (ledger history) | rebuild |
| CAP-287 | (ready 2026-11-10; co-governed by spec-pyforge-steward:CAP-165 and spec-pyforge-core) | 114.1, 116.5, 117.3 | ready: fix story 117.3 open (memlog 2026-11-10, CAP-287 amended: a missing purge list keeps the tag local; decision Marker of an amended capability and its addendum); Story 116.5 flips it to shipped, dated the day the last fix story reaches done; paths named: 1, all tracked | rebuild |
| CAP-288 | (shipped 2026-10-26; built by Stories 47.1 and 47.2, live only when Story 93.1 lands) | - | shipped (was (ready 2026-10-11; built by Stories 47.1 and 47.2, live only when Story 93.1 lands)): every citing story done (47.1, 47.2, 47.3, 47.4, 93.1, 110.34); the last, 110.34, reached done 2026-10-26 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-289 | (shipped 2026-10-26; built by Story 47.2, live only when Story 93.1 lands) | - | shipped (was (ready 2026-10-11; built by Story 47.2, live only when Story 93.1 lands)): every citing story done (47.1, 47.2, 47.3, 47.4, 93.1, 110.35); the last, 110.35, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-290 | (shipped 2026-10-26; the gate is Story 47.3's, reaching live sessions with Story 93.1) | - | shipped (was (ready 2026-10-11; the gate is Story 47.3's, reaching live sessions with Story 93.1)): every citing story done (47.1, 47.2, 47.3, 47.4, 93.1, 110.36); the last, 110.36, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-291 | (shipped 2026-10-26; the empty miss is Story 47.4's, recorded per run with Story 93.1) | - | shipped (was (ready 2026-10-11; the empty miss is Story 47.4's, recorded per run with Story 93.1)): every citing story done (47.1, 47.2, 47.3, 47.4, 93.1, 110.37); the last, 110.37, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-292 | (shipped 2026-10-17; reads pyforge-steward:CAP-166) | - | shipped (was (ready 2026-10-14; reads pyforge-steward:CAP-166)): every citing story done (100.1, 101.1); the last, 101.1, reached done 2026-10-17 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-293 | (shipped 2026-10-25; restored 2026-10-25: the 2026-09-16 fold minted no CAP from that Spec's plain-list scope) | - | shipped (was shipped with no date): every citing story done (17.1, 106.2); the last, 106.2, reached done 2026-10-25 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-294 | (shipped 2026-10-25; restored 2026-10-25: the 2026-09-16 fold minted no CAP from that Spec's plain-list scope) | - | shipped (was shipped with no date): every citing story done (17.1, 106.2); the last, 106.2, reached done 2026-10-25 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-295 | (shipped 2026-10-25; restored 2026-10-25: the 2026-09-16 fold minted no CAP from that Spec's plain-list scope) | - | shipped (was shipped with no date): every citing story done (17.1, 106.2); the last, 106.2, reached done 2026-10-25 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-296 | (shipped 2026-10-25; restored 2026-10-25: the 2026-09-16 fold minted no CAP from that Spec's plain-list scope) | - | shipped (was shipped with no date): every citing story done (17.2, 106.2); the last, 106.2, reached done 2026-10-25 (ledger history); paths named: 1, all tracked | rebuild |
| CAP-297 | (shipped 2026-10-26; minted 2026-10-26 on the Story 108.1 review under CHAIN-STANDARD §12: a Constraint that promises a visible guarantee is a capability; the Constraint stays as its provenance) | - | shipped (was shipped with no date): every citing story done (11.6, 108.1); the last, 108.1, reached done 2026-10-26 (ledger history) | rebuild |
| CAP-298 | (shipped 2026-11-05) | - | shipped (was no marker): every citing story done (113.1, 113.2, 113.3, ... 113.18, 113.19 (19 stories)); the last, 113.19, reached done 2026-11-05 (ledger history); paths named: 7, not tracked: installed_plugins.json, plugin.json, report.json | rebuild |
| CAP-299 | (shipped 2026-11-05) | 114.2 | shipped (was no marker): every citing story done (113.1, 113.2, 113.3, ... 113.18, 113.19 (19 stories)); the last, 113.19, reached done 2026-11-05 (ledger history); 114.2 corrects its words only and moves no marker; paths named: 17, all tracked | rebuild |
| CAP-300 | (shipped 2026-11-05) | - | shipped (was no marker): every citing story done (113.1, 113.2, 113.3, ... 113.18, 113.19 (19 stories)); the last, 113.19, reached done 2026-11-05 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-301 | (shipped 2026-11-05) | - | shipped (was no marker): every citing story done (113.1, 113.2, 113.3, ... 113.18, 113.19 (19 stories)); the last, 113.19, reached done 2026-11-05 (ledger history); paths named: 2, all tracked | rebuild |
| CAP-302 | (shipped 2026-11-05) | - | shipped (was no marker): every citing story done (113.1, 113.2, 113.3, ... 113.18, 113.19 (19 stories)); the last, 113.19, reached done 2026-11-05 (ledger history); paths named: 7, all tracked | rebuild |
| CAP-303 | (shipped 2026-11-05) | - | shipped (was no marker): every citing story done (113.1, 113.2, 113.3, ... 113.18, 113.19 (19 stories)); the last, 113.19, reached done 2026-11-05 (ledger history); paths named: 9, all tracked | rebuild |
