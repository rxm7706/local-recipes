---
title: '31.2: The scribe Spec says what the code does'
type: 'docs'
created: '2026-11-10'
status: 'done'
difficulty: 'medium'
story: 31-2-the-scribe-spec-says-what-the-code-does
spec: spec-pyforge-scribe
surface:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/glossary.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-31-2-the-scribe-spec-says-what-the-code-does.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/dreams/pyforge-unifying-strategy.md
  - .claude/skills/bmad-spec/SKILL.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-32.1, S-32.2, S-32.3, S-33.1,
> S-33.2). The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** At `82a2b18828` the scribe Spec is wrong or silent where the code is right (audit MUST 1, 2, 3, 5 (text),
6; SHOULD S3, S8, S9; NICE N6): it states the memory schema flat where `CaptureRecord.to_frontmatter` and all 121
records nest `metadata.type`; CAP-17 and CAP-18 read "See absorbed memlog"; 26 markers are stale; eight
`later-caps:CAP-n` cites point into the archive; twelve success bullets carry an inlined Constraints / Non-goals /
Success signal / Assumptions section; the Non-goal *Not CAP-14* names a `pg16` service by line number.

**Approach:** Each change is a memlog entry, then one `bmad-spec` re-derive through the anchored script render with
both self-validate passes logged. No code.

- **Amended, one `(capability)` entry each:** CAP-1 (nested `metadata.type` and the optional `supersedes` line;
  `--source`; success names `tests/unit/test_capture.py` and `test_promote.py`; the entry quotes the superseded
  flat-schema sentence; the AD-3 and AD-9 constraint lines restated with the nested schema); CAP-2 (the compile
  surfaces as `compile.py` enumerates them, no line cite; Story 8.1's trigger installer and the 24-hour
  `scribe-graph-freshness-check`; supersession is declared by a record's `supersedes: <type>/<slug>` line,
  `capture(supersedes=)` is its only writer, `scribe capture` has no flag for it, and no record carries one today);
  CAP-3 (overlap ties break by recency, Story 26.1; answers are identical across checkouts on the shared durable store,
  while the default flat-file store is one gitignored `graph.json` per checkout); CAP-6 (also `scribe index report`);
  CAP-9 (full heading; the default target list names A's tree and is the contract a rebuild re-derives for its own);
  CAP-17 and CAP-18 (re-authored in full from the archived memlog and `transcripts.py`, Story 3.3's cost ceiling);
  CAP-21 (the portal argv: binary, `scribe`, `recall`, an optional `--mode <m>`, `--`, then the query; never `--kind`;
  success names `tests/meta/test_first_portal_slice.py`); CAP-22 (default mode planning; `memory` the one other mode
  marshal passes); CAP-23 (the MCP face, `start_recall` and `get_recall` over `run_recall`,
  `spec-pyforge-unifying-strategy:CAP-20`); CAP-31 (the CI service is pgvector on PostgreSQL 17, by job name); CAP-32
  (`--root`, `--output`, `--pipeline-truth`; the source paths name A's tree).
- **Verified:** CAP-33 and CAP-34, minted at the 2026-11-10 mint, are checked against the code; a wrong clause gets a
  correction entry. CAP-34 keeps its `(retired 2026-11-10: ...)` marker (operator ruling, second addendum item 4).
- **Markers (one `(change)` entry, decision D4):** every heading carries exactly one dated marker:
  `(shipped <date>)` from the merge of the last story citing the capability (git), `(ready <date>)` while a story that
  carries it is open, and CAP-34's `(retired ...)`. CAP-27..CAP-29 gain a marker beside their mint provenance; CAP-35
  reads `(shipped <date>)` once Story 32.3 is built. The qualifiers the mint fix pass wrote on the CAP-1, CAP-4 and
  CAP-33 headings (`not met until Story 32.2`, `31.1` and `33.1`, and CAP-1's `Story 31.2 re-authors it`) leave the
  headings at this re-derive, since those Stories are its Deps; a clause still unmet then takes R2's qualifier
  `; not met: <clause>, DW-<id>` (CHAIN-STANDARD § 4, steward Story 120.3).
- **Corrections:** one entry replaces the eight `later-caps:CAP-n` cites with station ids (CAP-8 → CAP-9, CAP-11 →
  CAP-25, CAP-13 → CAP-19, CAP-14 → CAP-5); one carries the twelve inlined sections as each capability's own
  constraint lines, word for word.
- **Non-goal *Not CAP-14*:** cites symbols and the pg17 service by job name, and points at the durable driver's
  schema, the four changesets `src/platform/db/changelog/changes/pyforge-scribe-1..4*.sql`, which the driver asserts
  and never creates, carried by `spec-pyforge-unifying-strategy:CAP-14`.
- **One `(assumption)` entry:** the oracle's prerequisites (PostgreSQL 17 with pgvector 0.8.1 on 127.0.0.1:5433 or
  `SCRIBE_GRAPH_DSN`; psycopg capped below 3.2.11 with libpq 17; git; a trigger backend; graphifyy and cocoindex
  optional; duckdb and `pyforge.atlas` only for the plane round trip).
- **One `(decision)` entry:** `surface:` gains `.claude/settings.json`, `.vscode/settings.json`,
  `docs/reference/agent-instruction-notes.md` and `.claude/memory/README.md`; team-memory records and the generated
  catalog stay allowlisted, with the reason; `companions:` gains `contract.md` (Story 31.1).

Ledger key: `31-2-the-scribe-spec-says-what-the-code-does`. Type / Effort / Deps: docs / M / 31.1, 32.1, 32.2, 32.3,
33.1, 33.2.

### Living CAP citations

- `spec-pyforge-scribe` CAP-1..3, CAP-6, CAP-9, CAP-17, CAP-18, CAP-21..23, CAP-31, CAP-32 (amended here), CAP-33 and
  CAP-34 (verified), and the markers of CAP-5..CAP-35.

## Boundaries & Constraints

**Always:**
- Memlog first, then the anchored script render (each anchor asserted to occur once), then both self-validate passes
  logged as `(event) Self-validate pass 1 (coherence) <date>, Story 31.2 re-derive ...` and
  `(event) Self-validate pass 2 (preservation) <date>, Story 31.2 re-derive ...` entries (AC9 reads that marker).
- Marker dates come from git: the merge of the last story that cites the capability.

**Never:**
- Do not hand-edit `SPEC.md`.
- Do not backfill a `(capability)` entry for CAP-5..CAP-26: the seed includes `archive/**/.memlog.md` (operator ruling
  2026-11-10, second addendum item 7), and there is no ratchet.
- Do not add a `--supersedes` CLI flag: supersession stays library-only (same ruling); the Spec says the door is not
  built and a deferred-work row (Story 31.3) holds the ask.
- Do not re-mint the durable driver's schema as a scribe capability; point at `spec-pyforge-unifying-strategy:CAP-14`.

</intent-contract>

## Acceptance Criteria

- **AC1 — One dated marker per capability.**
  `python3 -c "import re,sys;L=[l for l in open('_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md') if re.match(r'- \*\*CAP-\d+ ',l)];m=[(int(re.match(r'- \*\*CAP-(\d+)',l).group(1)),re.findall(r'\((shipped|ready|retired) \d{4}-\d{2}-\d{2}',l)) for l in L];bad=[n for n,k in m if len(k)!=1];rdy={n for n,k in m if k==['ready']};ret={n for n,k in m if k==['retired']};print(len(L),bad,sorted(rdy),sorted(ret));sys.exit(1 if bad or len(L)!=35 or rdy or ret!={34} else 0)"`
  exits 0 and prints `35 [] [] [34]`.
- **AC2 — No stub.** `grep -c 'See absorbed memlog' _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md` prints 0.
- **AC3 — The schema as the code writes it.** `grep -c 'metadata.type' _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md` prints 2 or more.
- **AC4 — The three-command claim is gone.** `grep -c -e 'three independently invocable' -e 'three top-level commands' -e 'three-command CLI skeleton exists' _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md` prints 0.
- **AC5 — No archive-only or stale citation, no inlined section.** `grep -c -e 'later-caps:CAP' -e 'pg16' -e '## Constraints -' _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md` prints 0.
- **AC6 — CAP-21 states the portal argv.**
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md').read();b=t[t.index('**CAP-21 '):t.index('**CAP-22 ')];sys.exit(0 if '--mode' in b and '`--`' in b else 1)"` exits 0.
- **AC7 — The durable driver is pointed at, not re-minted.** `grep -c -e 'spec-pyforge-unifying-strategy:CAP-14' -e 'src/platform/db/changelog/changes/pyforge-scribe-' _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md` prints 2 or more.
- **AC8 — The four contract files are on the surface.**
  `python3 -c "import sys;t=open('_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md').read().split('---')[1];need=['.claude/settings.json','.vscode/settings.json','docs/reference/agent-instruction-notes.md','.claude/memory/README.md'];sys.exit(0 if all('- '+n in t for n in need) else 1)"` exits 0.
- **AC9 — This story logs both self-validate passes under its own marker.** The four passes the mint and its fix pass
  logged do not carry the `Story 31.2 re-derive` marker, so before this story the command prints `[]` and exits 1.
  `python3 -c "import re,sys;t=open('_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md').read();k=sorted(set(re.findall(r'^- \(event\) Self-validate pass ([12]) \(\w+\) \d{4}-\d{2}-\d{2}, Story 31\.2 re-derive',t,re.M)));print(k);sys.exit(0 if k==['1','2'] else 1)"`
  exits 0 and prints `['1', '2']`.
- **AC10 — Scribe's own Spec is not behind its memlog.**
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py -q -k scribe_spec` exits 0 and its summary line reads `1 passed`.
- **AC11 — Every package path a success clause names exists.**
  `python3 -c "import re,os;t=open('_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md').read();print(sorted({p for l in t.splitlines() if '**success:**' in l for p in re.findall(r'src/shared/packages/[\w./-]+\.py',l) if not os.path.exists(p)}))"` prints `[]`.
- **AC12 — The tests the amended capabilities name pass.**
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_capture.py src/shared/packages/pyforge-scribe/tests/unit/test_promote.py src/shared/packages/pyforge-scribe/tests/unit/test_transcripts.py src/shared/packages/pyforge-scribe/tests/unit/test_supersession.py src/shared/packages/pyforge-scribe/tests/unit/test_extras_move_list.py src/shared/packages/pyforge-scribe/tests/unit/test_extras_cocoindex_flow.py src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py -q` exits 0.
- **AC13 — The mint fix pass's heading qualifiers are gone.**
  `grep -c -e 'not met until Story' -e 'Story 31.2 re-authors' _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md` prints 0.

## Binding

- Parent capabilities: `spec-pyforge-scribe` CAP-1..3, CAP-6, CAP-9, CAP-17, CAP-18, CAP-21..23, CAP-31..35; no AD moves.
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 31. Ledger key `31-2-the-scribe-spec-says-what-the-code-does`, minted `backlog`, then set `blocked` by
  the mint fix pass (forward dependency: its Deps name Epics 32 and 33; unblocked only with operator confirmation).
- Deps: 31.1, 32.1, 32.2, 32.3, 33.1, 33.2 (so each success clause names a test that exists and CAP-35 can read
  shipped). Wave BUILD-3.

## Notes

- Closes audit MUST 1, 2, 3, 4 (with 31.1), 5 (text), 6; SHOULD S3, S8, S9; NICE N6.
- The 2026-11-10 mint wrote CAP-33, CAP-34 and CAP-35 and the amendments of Stories 31.1, 32.1, 32.2, 32.3, 33.1 and
  33.2, and its fix pass wrote CAP-27's seed clause and the CAP-1, CAP-4 and CAP-33 heading qualifiers; together they
  logged four self-validate passes (two for the mint render, two for its fix-pass render), none with this story's
  marker. The amendments above are this story's build.
- Story 32.1 is not blocked (per-PR approval b given 2026-11-10), so CAP-27 reads `(shipped <date>)` once it lands.
- Shared request: steward amends `spec-pyforge-unifying-strategy:CAP-14` to name the four changesets and the plane
  driver (deferred-work row DW-scribe-cutover-2026-11-10-10 until it does).
- About 25 memlog entries and 150 changed `SPEC.md` lines.

## Spec Change Log

- 2026-11-10: minted with Epic 31 at the cutover-readiness mint; AC1 and AC11 follow the second addendum's rulings
  (CAP-34 retired; Story 32.1 not blocked).
- 2026-11-10: mint fix pass after the second review. AC9 counted dated self-validate passes ("4 or more"), which the
  mint render and its fix-pass render already met before this story runs; it now reads the `Story 31.2 re-derive`
  marker only this story writes, and the Always bullet names that marker. AC13 is added and the Markers bullet
  extended so the fix pass's not-met-until-Story qualifiers on CAP-1, CAP-4 and CAP-33 leave at this re-derive. The
  Notes count of the mint's passes is corrected to four.
- 2026-11-10 (mint fix pass, third review round): the fleet forward-dependency policy applies. The Deps in `epics.md`
  read `S-31.1, S-32.1, S-32.2, S-32.3, S-33.1, S-33.2`, the grammar `forward-dependency-check` parses, and the key is
  `blocked` (feed, synced ledger, this spec's status, the `epics.md` Status line) until Epics 32 and 33 are done; the
  dated blockquote above says so. AC9 and the Notes count stand as the second review left them: the memlog holds four
  self-validate passes dated 2026-11-10, none carrying the `Story 31.2 re-derive` marker, so AC9 prints `[]` and
  exits 1 before this story runs.
