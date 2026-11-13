---
title: 'pyforge-scribe — Retrospective (2026-11-11: Epics 31 to 33, the cutover-readiness change)'
project: pyforge-scribe
created: '2026-11-11'
updated: '2026-11-11'
scope: 'Epics 31 to 33 on spec-pyforge-scribe, built on branch cutover-readiness-2026-11-10 after the 2026-11-10 fleet audit returned "not ready" for scribe as a rebuild seed. Stories 33.1 and 33.2 moved the package manifest (the code stage) past the newest retro (2026-09-20), which fires the code→retro currency edge; this is the retrospective that follows it. Story 31.4, which closes scribe''s part at the integration head, has not run yet.'
evidence:
  - 'research/cutover-readiness-audit-2026-11-10.md (the audit at main 82a2b18828)'
  - 'commit c53c83c80c (2026-11-11): Stories 31.1, 32.1, 32.2, 32.3, 33.1 and 33.2 (waves BUILD-1 and BUILD-2)'
  - 'commit af915294d1 (2026-11-11): Story 31.2, the Spec re-derive (wave BUILD-3)'
  - 'the story specs of Stories 31.1 to 33.2: their Gate findings, Review findings, Auto Run Result and Spec Change Log sections'
  - 'docs/dreams/pyforge-unifying-strategy.md § Realization log, the 2026-11-10 entry and its two addenda (the operator rulings)'
---

# pyforge-scribe — Retrospective, 2026-11-11 (Epics 31 to 33)

## What the epics set out to do

The audit found the code right and its written record wrong. The Spec stated the memory schema flat where the code
and every record nest `metadata.type`. It named three of the CLI's five command groups. CAP-17 and CAP-18 read "See
absorbed memlog", and 26 status markers were stale. `AGENTS.md` still gave the writer lock and the seed to B. The
suite read the live tree with no split, and it skipped the branches it named in the only environment it runs in.
The package metadata asked for a psycopg the estate forbids. Epics 31 to 33 set out to make the record true without
adding product behaviour (operator ruling R4 of 2026-11-10).

## What landed

| Story | What it built | Held by |
|---|---|---|
| 31.1 | The public contract, written down: verbs and flags, MCP tools, the flag key, environment variables, exit codes (`specs/spec-pyforge-scribe/contract.md`) | `tests/meta/test_public_contract.py` |
| 31.2 | The Spec re-derived from its memlog: the nested schema, the compile surfaces, recency ties, CAP-17 and CAP-18 re-authored, one dated marker per capability | both self-validate passes logged under the `Story 31.2 re-derive` marker |
| 32.1 | The `bmad:context` block refreshed headless from the rulings (per-PR approval b): A writes until the flip, B reads A at a pinned SHA, the seed is Dream plus memlog | `tests/meta/test_cutover_wording.py` |
| 32.2 | The team-memory index held equal to the record files; 40 superseded receipts moved to `archive/.claude/memory/project/` | `tests/meta/test_team_memory_index.py` |
| 32.3 | CAP-35: no Spec is behind its memlog | `tests/meta/test_spec_not_behind_memlog.py` |
| 33.1 | The suite split on `live_tree` and `postgres`; a server test fails, never skips; one walk-up root finder | `tests/meta/test_live_tree_split.py` |
| 33.2 | The extras' floors equal the estate pins, the package floor is `>=3.14`, docstrings name the right staleness clock, the runbook routes guild tasks to `-e pyforge-guild` | `tests/meta/test_package_metadata_matches_estate.py` |

Story 31.3 (this pass) re-stamps the brief, PRD, spine and epics in that order and writes this retro, the readiness
report and seven deferred-work rows. Story 31.4 closes scribe's part at the integration head.

## What went well

- **Each fix is a test.** Six of the seven built stories end in a meta-test that names what it finds. The gaps the
  audit counted by hand (a verb missing from the Spec, a superseded clause in the block, an index line with no
  record) now red the suite by name.
- **Guards caught each other in the same wave.** Story 33.1's split guard named Story 31.1's
  `test_public_contract.py` for resolving the repository root at import. That is the one property a copied package
  cannot survive. The fix was made at the gate, in 31.1's file.
- **The rulings closed the open questions before the build.** The second addendum answered every scribe question
  the plan had left open (the seed includes `archive/**/.memlog.md`; `--supersedes` stays library-only; CAP-34
  retires). No story had to stop and ask.

## What went wrong, and why

- **The planning chain had been re-stamped without being re-read.** The PRD, spine and epics dated 2026-11-05 were
  date re-stamps (audit S5). Each cascade bumped `updated:` and wrote "no FR moves", so FR-1's flat `type`, FR-14's
  three verbs and the spine's `>=3.12` Stack row survived several re-stamps. A currency stamp shows only that a file
  was touched after its input. It does not show that the text was checked against the capability it cites.
- **A shrink-only file went stale inside one wave.** Story 32.3's known-rows file was measured at the plan. The same
  wave re-rendered four Guild and kernel Specs, so 52 rows were no longer behind and the shrink rule failed at the
  gate. The rows were pruned (84 to 32). A known-rows file in a change with concurrent re-derives has to be measured
  again at the integration head, which Story 31.4 does.
- **A no-git-writes build cannot `git mv`.** Story 32.2 moved its records with plain `mv`. Git records a rename only
  if the wave gate stages both halves in one commit. The story spec records this deviation. Review also returned two
  records to the index: one still carried an open operator ask, and the other stated a trap no other record states.
- **A line grep misses a wrapped line.** One of the runbook's three `-e local-recipes` sites was split across a line
  break, so Story 33.2's AC grep could not see it. All three were fixed by reading the file, not by trusting the grep.

## What to carry forward

- **Re-read the FR against its capability on every `spec→prd` cascade.** A re-stamp says what moved and what was
  checked. This pass amended FR-1, FR-14, FR-16, FR-51 and FR-52 for exactly that reason.
- **Resolve the repository root inside a function or fixture, never at import.** Story 33.1's guard now enforces it
  for every `.py` under `tests/`.
- **Re-measure shrink-only data at the head of a multi-station change, not at its plan.**
- **Open rows** (`deferred-work-ledger.md`): DW-scribe-cutover-2026-11-10-1 (the `--supersedes` CLI door, for a
  later Dream entry), -2 (five tests that run in no lane), -3 (the PRD traces 9 of 35 capabilities), -4 (no
  scheduled re-derive comparison), -5 (`scribe index move-list` stays until a Story removes it), -7 (a contract change
  hidden in a bookkeeping event) and -10 (the durable store's schema, which steward Story 124.5 writes into
  `spec-pyforge-unifying-strategy:CAP-14`). DW-scribe-egm-2026-11-05-3 closed with Story 32.1.

## Strategy convergence

Scribe's part of the Unifying Strategy is the record the cutover seeds from. The 2026-11-10 rulings make Dream plus
memlog the seed and A the writer until `pyforge.cutover_root` flips. After these epics, scribe's Spec says what its
code does, the memlog it re-derives from is held current by CAP-35, the public contract is written down, and the
suite can serve as the oracle a second root runs. Scribe gains no new capability toward B in this change. What
changed is that its existing contract can now be rebuilt from the seed without reading the code to correct it.
