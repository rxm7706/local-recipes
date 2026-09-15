---
title: One name, one job — reconciling three vocabularies
type: dream
owner: steward
status: specified
---

# One name, one job — reconciling three vocabularies

> **Seed Dream.** PyForge now speaks three vocabularies at once — BMAD-METHOD's upstream terms,
> our own Lexicon and the artifact statuses derived from it, and the Intelligence Hub / Frame
> vocabulary adopted 2026-09-13. They have never been compared in one pass. This Dream carries
> that comparison into the Dream tier so `bmad-spec` can derive a contract from it. Nothing below
> is an adoption decision.
>
> **Two halves.** *Which vocabulary does this word belong to* (§ What is real) and *what shape do
> we write it in* (§ The shapes). The second half was added 2026-09-14; it is the same rule
> applied to identifiers rather than to words, and it is kept here rather than split into a
> sibling Dream because a status word that is perfectly reconciled is still unreachable if the id
> carrying it cannot be parsed.

## Source

`_bmad-output/projects/pyforge-steward/planning-artifacts/research/technical-vocabulary-three-source-reconciliation-2026-09-14.md`
— the measured three-source pass at `main` `445976e5be` (2026-09-14).

`…/research/technical-identifier-shapes-inventory-2026-09-14.md`
— the identifier-shape sweep, same head, same day; the source for § The shapes.

Every count and quotation in this Dream comes from one of those two; re-verify against them
rather than against this file's prose. **Both measured a dirty working tree** (36 modified or
untracked paths at `445976e5be`) — see the shapes research § 8 for the one place that changes a
result.

## The Dream

The Lexicon already states the rule this Dream wants to make true everywhere:

> **Every noun does exactly one job; every job has exactly one noun.**

Today that rule holds inside the Lexicon's seven nouns and nowhere else. Around them sit four
status vocabularies, of which one is declared; a word that means three different things
(`in-progress`); one job with four names (`done` / `shipped` / `realized` / `review`); and a
value that is our most-used Spec status but is upstream's canonical *illegal* value (`shipped`,
67 live Specs, reset to `backlog` by upstream's own test suite).

The Dream is that a reader — human or agent — can look at any status on any artifact in this
estate and know, without reading code, which vocabulary it belongs to, what act it asserts, and
what it obliges downstream. And that the detectors enforcing it read that vocabulary from one
declared place rather than five hard-coded sets scattered across `board.py`, `chain.py`, and
`status_body_consistency.py`.

The same rule has a second edge. *Every noun does exactly one job* is about meaning; **every
thing is written down exactly one way** is about shape, and the estate satisfies it in one place
and almost nowhere else. A story is named three times in three files and no two spellings are
derivable from each other. A deferred-work id has eleven grammars. The Dream's second half is
that an agent can find the thing it was told about — that a name, once chosen, survives the trip
between `epics.md`, the ledger, the spec folder, a branch, and a sentence of prose.

## What is real

Measured 2026-09-14, not remembered:

- **The Dream ladder is already principled and declared** (`docs/dreams/README.md:63-104`):
  *"each state names the act that completed, never the artifact that proves it"*, with the
  rejected alternatives recorded (`seeded`/`in-deck`/`in-spec`, renamed 2026-07-25) and a
  deliberate refusal of a `building` state. **This is the asset to extend, not replace.**
- **The Spec ladder has no declaration at all** — 8 values across 163 files, of which only
  `extension-point` is defined, and that in the *Dream* README.
- **Our ledger is largely upstream-conformant**, which the sprawl framing had obscured:
  `done`/`backlog`/`in-progress` are BMAD's story lattice and `optional` is BMAD's *retrospective*
  lattice applied exactly where it belongs. Only `blocked` is net-new local.
- **BMAD provides no extension point for status vocabulary**, and silently resets unrecognized
  values — the fail-open behaviour our local `STICKY_STATUSES` patch exists to defeat.
- **The Hub has six shared abstractions, not seven.** Our Charter (Tier 0, line 606), the
  Intelligence Hub Spec (lines 48, 68) and `vocabulary-map.md` all name seven by folding in
  Organizational Memory, which upstream tiers as Layer-1 infrastructure. The Charter's
  *substantive* rulings are unaffected; the enumeration is not.
- **Our nine Frames are authored against an unmerged, unlicensed draft** — `type: frame [0.3]`,
  `identifier:`, `license:` are v0.3-only fields, and `frame-spec` PR #28 (which would add both
  v0.3 and Apache-2.0) is still open.
- **The failure this prevents has already happened three times.** Two Dreams are recorded in
  `docs/dreams/README.md:90-98` as reading `dreamt` while their epics were 3/3 and 5/5 done;
  `intelligence-hub` was found the same way on 2026-09-14.
- **There is a fourth vocabulary tier nobody mapped: Design.** The 45-slide deck teaches a whole
  practice vocabulary — **four phases**, **three tracks**, parallel track, party mode, execution
  matrix, method-vs-machinery, project-context-as-constitution — and **none of it** appears in
  `vocabulary-map.md`, the Charter cross-walk, or any repo glossary. The Lexicon slide itself is
  current; everything around it was recorded in Design and never entered practice.
- **`Track` collides and nobody named it.** Hub `Track` is the durable evidence record
  (`hub:CAP-3`, Story 53.3's `track.json`); the deck's `Track` is a BMAD planning lane (Quick
  Flow / BMad Method / Enterprise). The Charter named the Cogs/Smith collision and stopped.
  `Guard`/`Gate` were never examined at all, and already carry three senses across Hub, our
  detectors/`gate_mode`, and BMAD's `PASS`/`CONCERNS`/`FAIL`.
- **The deck teaches four names BMAD retired** (`bmad-quick-dev`, `bmad-dev-auto`,
  `bmad-create-story`, `bmad-dev-story`) plus **Paige**, the Tech Writer persona retired in 6.11.
  `CLAUDE.md` records the renames correctly; the public-facing deck does not.
- **The Design→repo pull is stale again.** Local copies date to 2026-08-01 and
  `Agentic SDLC.dc.html` is **13.5 KB behind** Design. The Charter's own log (line 826) records
  the 2026-08-01 pull as the *first* one ever, made to fix exactly this drift class. It recurred.

## The shapes

The same question asked of identifiers rather than words. Measured 2026-09-14, not remembered;
every count is in `technical-identifier-shapes-inventory-2026-09-14.md`.

- **The estate proves the shape is achievable.** `^### Story \d+\.\d+: .+$` holds **952/952**
  across all eight stations — zero exceptions, one separator, no drift. The doctor finding codes
  are second: **124 distinct codes, 124 conforming to `^[a-z0-9]+(-[a-z0-9]+)*$`**. Neither is
  declared anywhere; both are simply obeyed. **These are the assets to extend, exactly as the
  Dream ladder was on the word side.**
- **One story is spelled three ways, 2760 times.** `### Story 33.9:` (dotted, Title Case) ⟷
  ledger `33-9-verify_scope-guards-marshal-factory-dispatch:` ⟷
  `spec-33-9-verify_scope-…md`. No two are mechanically derivable, **and the slugify that
  connects them is not deterministic**: of 842 stories present in both the ledger and a spec file,
  **53 carry different slugs for the same number** (atlas 19, herald 19, marshal 7). A fourth
  spelling lives in branch names, a fifth in prose.
- **The slugify is not closed over its own alphabet.** 14 of 952 ledger keys fail the shape they
  are documented to have — underscores (`33-9-verify_scope-…`), non-ASCII
  (`22-4-a-diátaxis-adapted-…`), a typographic apostrophe collapsed to `-s-`. A regex over the
  documented shape silently drops all 14.
- **`Story N.N` (11941) and `S-N.N` (2615) are both live prose**, in the same files, neither
  declared. marshal alone writes `S-` 1303 times.
- **Deferred-work ids have eleven grammars over 1338 ids** — `DW-FU-<E>-<S>-<n>` 665,
  `DW-<E>-<S>-<n>` 347, `DW-FU-<E>-<n>` 185, then eight more including bare `DW-1`…`DW-10`
  (which collide across projects by construction) and six malformed (`DW-FU`, `DW-B4-`,
  `DW-B2-1..5` — a range in an id slot). **This Dream's own sibling pass demonstrates the
  failure**: `DW-VOCAB-2026-09-14-1..7` is one sequence split across two ledger files, steward
  holding 1,2,3,4,5,7 and marshal holding 6, with nothing in the shape able to say so.
- **Long vs short station form has no rule.** LONG in project dirs (8), packages (10), pixi envs
  (13), pixi tasks (64), `dispatch/`+`loop/` branches (44); SHORT in Dream `owner:` (165/165),
  `bmad-agent-*` skills (8), all 35 `Source` enum values, 22 branch namespaces, 9 pixi tasks.
  `pyforge-scribe` is the env and package but `scribe-pg-up` is its task. **And the four short
  rosters in code disagree with each other** — three member orders, and `DREAM_STATIONS`
  (`marshal/mcp/coverage.py:30`) holds only 6 of 8, omitting doctor and scribe.
- **Frontmatter key casing is inverted between the two spec tiers, inside the same files.**
  Numbered story specs run 27 snake_case keys to 1 kebab; named `SPEC.md` runs 7 kebab to 4
  snake. Every `SPEC.md` carries `owner-dream:` and `open_questions:` side by side.
- **Commit subjects split 72/50 and punctuate in opposite directions.** Conventional-commit
  `type(scope):` never ends in a period (0 of 72); the Capitalized-sentence family almost always
  does (46 of 50). Five commits use a *station name* as the conventional-commit type.
- **Dream `title:` matches its own filename in 0 of 165 cases** — kebab slug against prose title,
  69 of them `Noun phrase — subtitle` and 96 full sentences. And **19 of 165 `status:` values
  carry a trailing `# …` comment on the same line**, so a naive parse reports 40+ statuses where
  the ladder declares 5. That is a shape defect sitting directly on top of the word-side ladder
  this Dream is otherwise trying to preserve.
- **Finding codes are clean until they carry data.** 124/124 literal codes are kebab, but six
  call sites in `sources/atlas.py` pass a feedstock or package name into `check=`, so the field
  that elsewhere carries `spec-surface` can carry a package name or the literal
  `"<unknown feedstock>"` (`atlas.py:172`).
- **The estate can already close a shape defect cleanly — but the record of it is uncommitted.**
  `DW-VOCAB-2026-09-14-5` (steward `epic-18`) and `-6` (marshal `epic-29`) report ledger rows with
  no epic heading. Both are raised, fixed and `status: closed`; a full cross-check of all eight
  projects found **214 epic keys against 214 headings, zero mismatches**, with no story orphaned.
  That is the whole loop working. **None of it is committed** — the DW entries, the two headings
  and the closures were all minted 2026-09-14 and `git show HEAD:…` returns 0 for every one of
  them, inside a 46-file changeset staged on `main`. The shape defect is solved; its durability
  is not.

## Constraints

- **The Charter is Tier 0.** Its six-vs-seven correction is an *amendment with a Realization-log
  entry*, never an edit. Its standing CAP-4 ruling — an external vocabulary is cross-walked and
  **never joins** the seven Lexicon nouns — binds this Dream too.
- **Do not rename a Lexicon noun.** The seven are constitutional.
- **Upstream BMAD terms are not ours to redefine.** Where we differ from `sprint_plan.py`'s
  lattices we either conform or record why, in the open — never silently.
- **Status is not a proxy for work remaining** (`docs/dreams/README.md:90-98`). Any proposal that
  re-introduces activity-tracking into a hand-declared status is already answered: the ledger and
  `fleet-picture` own that question.
- **No migration that rewrites history.** Memlogs are append-only; Realization logs are the
  amendment record.
- **A vocabulary change lands with its detector.** Any renamed or retired value updates the code
  that reads it in the same change, or it is not done.
- **A shape change is a mass rename, and mass renames break readers.** 1338 `DW-` ids and 952
  ledger keys are each read by detectors, ledgers, branch names and prose. Nothing here may
  propose a rename whose reader-update cost has not been measured first.
- **`### Story N.N:` and the 124 kebab finding codes are not up for redesign.** They already hold
  at 952/952 and 124/124. Any shape ruling extends them or leaves them alone.
- **Historical prose keeps its original names.** Memlogs, Realization logs and retros record what
  was written at the time; only live pointers get repointed.

## Non-goals

- Adopting Cogs / Ops as PyForge nouns — the Charter already ruled cross-walk, never join.
- Building a Frame registry, or chasing `frame-spec` v0.3 before PR #28 merges.
- Renaming `sprint-status-ledger.yaml` to upstream's `sprint-status.yaml` as an end in itself.
- Re-litigating the Dream ladder, which is declared, principled, and working.
- A vocabulary UI, linter-as-product, or anything shipped outside this estate.
- **Retro-renaming the 1338 existing `DW-` ids**, or the 53 divergent story slugs. A grammar for
  what is minted *next* is a different and much smaller question than a migration of what exists.
- **Unifying branch names.** Five of the twelve branch shapes are machine-generated by
  `bmad-loop`, `dispatch`, `attempt-preserve` and the worktree tooling; they are internal and
  short-lived. Only the human-authored namespaces are in scope at all, and possibly none of them.
- Fixing `DW-VOCAB-2026-09-14-5`/`-6` here — they have working-tree fixes already and belong to
  whoever owns that uncommitted change, not to this Dream.

## Open questions for the Spec

1. **Does the Spec ladder get declared as-is, or reduced?** Eight values exist; `absorbed`,
   `superseded` and `archived` arguably name one act (ended, by three different routes).
2. **Does `in-progress` survive on Specs?** It is the "what is happening" shape the Dream side
   deliberately rejected, and it collides with two other vocabularies.
3. **Where does the Spec ladder live?** A Spec-side README mirroring `docs/dreams/README.md`, a
   section of the Charter, or a machine-readable declaration both prose and detectors read.
4. **Do we follow Frame v0.3's `recommended, not required` + `must preserve unregistered`
   pattern?** Upstream adopted it for exactly our reason — a required enum would invalidate their
   own examples.
5. **Does a BMAD↔Lexicon cross-walk belong in the Charter** beside the Hub one, given BMAD
   supplies the terms in heaviest daily use (Epic, Story, Sprint, PRD, Retrospective)?
6. **`pitched`** — declared in `guild-roster.json`, used by nothing. Retire it or use it?
7. **Is one declared vocabulary source feasible** that `board.py`, `chain.py` and
   `status_body_consistency.py` all read, replacing five hard-coded sets?
8. **Does the Design tier's practice vocabulary join the map, or stay teaching-only?** Four
   phases, three tracks, party mode and method-vs-machinery are taught publicly and carried
   nowhere in the repo. Either they are estate vocabulary and belong in the map, or they are
   presentation scaffolding and should say so.
9. **How is the `Track` collision resolved** — rename our planning-lane sense, qualify both
   (`planning track` vs `evidence Track`), or accept the overload with a named ruling as the
   Charter did for Cogs/Smith? Same question for `Guard`/`Gate` across three senses.
10. **What keeps Design and repo from drifting a third time?** The 2026-08-01 pull was itself the
    fix for a year of drift, and the deck is 13.5 KB behind again. Is this a detector, a pull
    step in a Herald story, or an accepted manual cadence?
11. **Who owns retiring stale teaching?** The deck teaches four retired BMAD skill names and a
    retired persona. Correcting it is Herald's surface, but the vocabulary ruling is steward's.

### On shapes (added 2026-09-14)

12. **Which of the three story spellings is canonical, and do the other two derive from it?**
    The heading is the human one, the ledger key is the machine one, the spec filename is neither
    consistently. A declared slugify — applied once, at mint time, by one function — would make
    the other two derivable; 53 existing divergences say no such function is in use today.
13. **Does `DW-` get one grammar for newly minted ids?** Eleven shapes exist. The two that carry
    real information are `DW-[FU-]<E>-<S>-<n>` (story-scoped, 1197 ids) and
    `DW-<SLUG>-<date>-<n>` (sweep-scoped, ~30). The rest are neither. Note that
    `deferred_work_promote.py` is already recorded as keeping generic Tier-3 ids verbatim, so a
    grammar without a mint-time guard will not hold.
14. **Is a project qualifier part of a `DW-` id?** Bare `DW-1`…`DW-10` collide across ledgers,
    and this Dream's own `DW-VOCAB` sequence is split across two of them.
15. **Kebab or snake for frontmatter keys?** The two spec tiers answer oppositely, in the same
    files. Whichever wins, `open_questions` or `owner-dream` has to move — and both are read by
    detectors.
16. **Does `S-N.N` retire, or get declared as a legitimate short form?** 2615 uses; retiring it is
    a prose migration across every planning artifact, declaring it is one sentence.
17. **Do commit subjects get one style?** 72 conventional-commit against 50 Capitalized-sentence
    in the last 200, punctuating in opposite directions. This is the cheapest ruling available and
    the only one enforceable at the gate rather than by sweep.
18. **Does the long/short station form get a per-context rule** — long for paths and packages,
    short for code and prose, say — or is one form canonical everywhere? And separately: do the
    four `STATIONS` rosters collapse into one declared list? `DREAM_STATIONS` silently omitting
    doctor and scribe is the kind of defect a single source would have prevented.
19. **Should `docs/dreams/README.md`'s ladder forbid the trailing `# …` comment on `status:`?**
    19 of 165 Dreams carry one, which is why the ladder parses as 40+ values instead of 5. The
    word-side ladder is this Dream's protected asset; this is a shape defect sitting on top of it.
20. **Is a `check=` that carries runtime data still a finding code?** Six call sites in
    `atlas.py` say the field has two jobs. Either it has one and the data moves to `evidence`, or
    the code vocabulary is declared open and nothing downstream may enumerate it.

Answers for 1–20 were accepted 2026-09-15 and are recorded in § *Operator rulings* below.
They bind a later `bmad-spec` re-derive. They do **not** make this Dream `specified` — the
Spec is still `draft` until that re-derive lands the same answers in the contract.

## Operator rulings (accepted 2026-09-15)

Operator accepted the full recommended batch in session. Recorded here so the Dream carries
the *why*, not only a key. The test that judged every answer is the one this Dream already
had: **each state names the act that completed, never what is happening; remaining work is
the ledger.** No mass rename, no history rewrite, no Lexicon-noun change.

### Word side

1. **Declare all eight Spec values. Do not collapse `absorbed` / `superseded` / `archived`.**
   They look like one “ended” act and are not. `board.py` already treats them as different
   obligations: `shipped` still owes a story trail; `absorbed` is credited on the absorbing
   chain; `archived` / `superseded` were abandoned, not delivered; `extension-point` is a
   seam. Collapsing them would make INV-A lie. Keep `shipped` as *our* Spec-terminal. That
   it is illegal on an upstream *story* is a cross-walk footnote, not a rename of the
   ~67 live `shipped` Specs.

2. **Stop putting `in-progress` on Specs.** It is the `building` state the Dream ladder
   refused, and it collides with BMAD’s story lattice and our ledger. Live Specs already
   use it as leftover-CAP accounting (`deferred-work-visibility`; `developer-machine-bootstrap`
   still `in-progress` after Epic 17 is 2/2 `done`). A contract that exists is `ready` until
   every CAP is delivered (`shipped`) or the chain is ended. **Grandfather** today’s files —
   no mass rewrite. Detectors may keep treating the old value as open until each file is
   next edited.

3. **One machine-readable declaration detectors import; the Charter states the rule in a
   short paragraph.** The Dream README stays the Dream ladder only. The coupling
   (`specified` requires Spec `ready`; `extension-point` keeps the Dream `dreamt`) must not
   live only in `docs/dreams/README.md` while `board.py` / `chain.py` /
   `status_body_consistency.py` each keep a private set.

4. **Yes — recommended, not required, and a reader must preserve an unregistered value.**
   Frame v0.3 chose that so its own examples stayed valid. A closed enum would red ~163
   `SPEC.md` files on day one. Unknown values: preserve, warn, do not reset (the fail-open
   BMAD already does is why `STICKY_STATUSES` exists).

5. **Yes — a BMAD↔Lexicon cross-walk belongs in the Charter, same shape as the Hub walk:
   map, never join.** Epic / Story / Sprint / PRD / Retrospective are the daily nouns and
   have no walk. Record the divergences in the open: Spec `shipped` ≠ story `done` ≠ Dream
   `realized`; ledger `blocked` is ours; `optional` is BMAD’s retrospective lattice used
   where it belongs.

6. **Keep `pitched`. Do not require it. Do not backfill.** Use it when Herald has actually
   made the case (a deck exists) and the Spec is still `draft`. `guild-roster.json` already
   declares it; zero live Dreams use it. Forcing the rung would invent ceremony the
   factory does not run.

7. **Yes — one declared source for status sets.** Exit-code lattices sit in the **same
   file, a different key** — do not mash “what a Spec may say” with “what a process may
   return.” That leftover design half is `DW-VOCAB-2026-09-14-8` (docs half already in
   `CLAUDE.md`).

8. **Design practice vocabulary is teaching-only, and the deck must say so.** Do not
   import four-phases / three-tracks / party mode / execution matrix into
   `vocabulary-map.md`. Upstream 6.12 already says those phases are independent tools, not
   stages, and “three tracks” collides with *evidence Track*. **Exception:**
   method-vs-machinery and project-context-as-constitution already describe this estate —
   they belong next to the Charter, not as new Lexicon nouns.

9. **Already ruled 2026-09-14; restated.** Write **evidence Track** vs **planning track**.
   Gate has three senses; `verdict` is the narrow word. Charter amendments, not edits.

10. **Herald owns the Design→repo pull; a detector owns recurrence (etag/size).** Manual
    cadence failed twice (2026-08-01 pull; 2026-09-14 deck 13.5 KB behind). Do not accept
    “we’ll remember.” This is CAP-5 / `DW-VOCAB-2026-09-14-3`.

11. **Steward writes the vocabulary ruling; Herald changes the deck.** Same split already
    on `DW-VOCAB-2026-09-14-3`.

### Shape side

12. **Heading is human-canonical (`### Story N.N:`). Ledger key is machine-canonical.
    Spec filename is `spec-` plus that ledger key. One slugify, at mint time only.**
    Headings already hold 952/952. 53 of 842 number-pairs have divergent slugs — no
    retro-rename.

13. **New `DW-` ids only: two families.** Story-scoped and sweep-scoped (the two that
    already carry information). Ban the other nine shapes for anything minted after this
    ruling. A grammar without a mint-time guard will not hold —
    `deferred_work_promote.py` copies generic Tier-3 ids verbatim.

14. **Yes — every new `DW-` id includes the short station token.** Bare `DW-1`…`DW-10`
    collide across ledgers; this Dream’s own `DW-VOCAB` sequence split across steward and
    marshal. No retro-rename of the 1338 existing ids.

15. **Both casings stay, as context rules.** Named `SPEC.md` is kebab-led (`owner-dream`)
    with `open_questions` beside it; numbered story specs are snake-led. Do not move
    either key — detectors read both. A single “winner” is a detector break.

16. **Declare `S-N.N` as a legal short form in prose only.** The heading stays
    `### Story N.N:`. Retiring 2615 uses is a planning-prose migration with no reader
    benefit.

17. **Capitalized sentence, no trailing period, no `Co-Authored-By`.** Conventional
    `type(scope):` is allowed only under `recipes/` and the CFE changelog. This is the
    one shape a commit hook can enforce; the last-200 mix punctuates in opposite
    directions.

18. **Per-context, plus one declared roster of eight.** LONG for paths, packages, pixi
    envs; SHORT for Dream `owner:`, `Source`, and prose. Collapse the four disagreeing
    `STATIONS` lists. `DREAM_STATIONS` omitting doctor and scribe is the defect a single
    list prevents. Do not pick one form for every surface.

19. **Forbid a trailing `# …` on the same line as Dream `status:`.** Put the comment on
    the next line. 19 of 165 Dreams make a five-value ladder parse as 40+. Fix-on-touch
    or one hygiene PR; add a detector. This protects the Dream ladder this file exists
    to extend.

20. **`check=` is a finding code only. Runtime data goes in `evidence`.** Six `atlas.py`
    call sites put a feedstock or package name (or `"<unknown feedstock>"`) in the field
    that elsewhere carries `spec-surface`. That is a small code fix once the Spec is
    `ready`, not a second vocabulary.

### Deliberately not in this batch

- Renaming Spec `shipped` to `done` (fights the story lattice and ~67 files).
- Unifying branch names (most are machine-generated and short-lived).
- Retro-fixing the 53 divergent slugs or the 1338 `DW-` ids.
- Re-opening Frame v0.3 (adopted on steward Story 53.6).

## Kinships

- [[intelligence-hub]] — the Hub half of the vocabulary; its CAP-1 landed the Charter cross-walk
  this Dream corrects the enumeration of.
- [[pyforge-charter]] — Tier 0; holds the Lexicon and the cross-walk ruling.
- [[pyforge-unifying-strategy]] — the estate-wide chain these statuses report into.
- [[build-league-scorecard]] — parked on the operator's measure set; shares the "what do our
  words assert" question from the measurement side.

## Realization log

- **2026-09-14** — Seeded. Three parallel read-only passes (this repo's live vocabulary; BMAD
  v6.12.0 pristine; OpenTeams whitepaper `v9` + `frame-spec` + the guide) recorded in
  `research/technical-vocabulary-three-source-reconciliation-2026-09-14.md`. Three corrections to
  our own records came out of it: the Hub has **six** shared abstractions and our Charter names
  seven; the Guard categories are right but **Source-Grounding ranks second, not sixth**; and
  `extension-point` is **not** a category error but a documented parked-Spec state. No adoption
  decided, no Charter amendment made — `status: dreamt` until a Spec reaches `ready`.
- **2026-09-14 (later)** — Operator direction: the Design tier belongs in this research too. A
  fourth pass over Design project `f58c0f17` (`Agentic SDLC` deck + the two Lexicon posters) found
  three further things, recorded as § 5b of the research: the deck teaches a practice vocabulary
  (four phases, three tracks, parallel track, party mode, execution matrix, method-vs-machinery,
  project-context-as-constitution) that **never entered `vocabulary-map.md` or the Charter
  cross-walk**; it still names four BMAD skills retired in 6.11 plus the retired Paige persona;
  and the local pull is stale again — `Agentic SDLC.dc.html` is 13.5 KB behind Design, the same
  drift class the Charter's line-826 amendment fixed on 2026-08-01. The `Track` collision (Hub
  evidence record vs BMAD planning lane) and the unexamined `Guard`/`Gate` overload were added to
  the disagreement list; the Lexicon slide itself verified current against the Charter's seven.
- **2026-09-14 (third)** — Operator direction: keep the identifier-shape question in this Dream
  rather than minting a sibling. A fifth read-only pass over the same head measured nine naming
  surfaces (station names, epic/story addressing, spec names, Dream names, deferred-work ids,
  detector codes, pixi tasks, branches/commits, planning-artifact filenames), recorded as
  `research/technical-identifier-shapes-inventory-2026-09-14.md` and summarized in § The shapes.
  It found two things worth stating at Dream level: the estate **already holds one shape
  perfectly** (`### Story N.N:`, 952/952, and 124/124 kebab finding codes) so the goal is
  demonstrably reachable; and **one story is spelled three non-derivable ways 2760 times**, with
  53 of 842 slugs actually divergent between ledger and spec file. Open questions 12–20 added; no
  shape chosen, no rename proposed. The Spec stays `draft` and this Dream stays `dreamt` — the
  shape questions are operator decisions of exactly the kind already blocking the word side.
- **2026-09-14 (third, corrected same session)** — The entry above first recorded that
  `DW-VOCAB-2026-09-14-5`/`-6` were "fixed but still open in the ledger". **That was wrong**: both
  read `status: closed`, and the claim came from a truncated `grep` that never reached the
  `status:` line rather than from a measurement. Corrected in place here and in the research § 8.
  The accurate finding is narrower and more useful: those two are a **complete, correct loop**
  (raised → fixed → closed, 214 epic keys against 214 headings fleet-wide, no story orphaned),
  and the exposure is durability, not correctness — the whole chain, this Dream included, sits in
  a 46-file changeset **staged on `main` and uncommitted**, none of it reachable from `HEAD`.
- **2026-09-15** — Operator accepted the full recommended ruling batch (word-side Q1–11,
  shape-side Q12–20) and directed that the answers and their reasons be appended to **this
  Dream** before any Spec re-derive. Recorded in § *Operator rulings (accepted 2026-09-15)*.
  Status stays `dreamt`: a `draft` Spec still has unanswered `open_questions:` in its
  frontmatter until `bmad-spec` re-derives the contract from this file. No epic. No
  `SPEC.md` hand-edit.
- **2026-09-15 (later)** — Operator: decompose all the way to stories ready for
  marshal dispatch. `bmad-spec` re-derived `spec-vocabulary-one-name-one-job` to
  `ready` (CAP-1..8; CAP-4 already met; `open_questions: []`). This Dream flips
  `dreamt` → `specified`. Steward Epic **59** (59.1–59.7 `backlog`) is the
  dispatch home. `DEFERRED_SPECS` drops this slug.
