---
title: The chain standard — one page, every station, both roots
type: companion
spec: one-chain-per-station
status: ready
created: "2026-09-16"
updated: "2026-11-01"   # AMENDED 2026-11-01 (EGM audit, marshal Story 113.7; operator rulings 2026-11-01): § 0 terms and provenance; CAP date markers (ready <date>)/(shipped <date>), qualified spec-<x>:CAP-n cites and success clauses that name their command and exit code (§§ 1-4); the story-spec ladder (§ 4); station long and short forms (§ 5); B named rxm7706/python-foundry; § 11 item 3 dated done; counts read at their amendment; fr-baseline.json's one writer (§ 12). Prior "2026-10-26": AMENDED 2026-10-26 (CAP-5): a requirement cites defined CAPs only — §2, §6 (NFR families), §12 (the ruling and the arrows it reverses). Prior "2026-09-17"
---

# The chain standard

**Read this, not the history.** One station has one chain. Every name, status,
id and folder below is *the* form; a fold PR conforms its station to this page
in full, and a new artifact anywhere in the fleet conforms on the day it is
minted. Where this page and an older artifact disagree, this page wins and the
artifact moves (Spec Constraint *Precedence*). Each rule names the ruling it
comes from — nothing here is new vocabulary; it is the existing rulings with
their grandfathering removed (operator, 2026-09-16: *"don't make the operator
think"*).

Applies to `local-recipes` (A) now and to B, `rxm7706/python-foundry`, on cutover (Spec CAP-7).

---

## 0. Terms and provenance

Each term this page uses, defined once (operator ruling 2026-11-01). A count on
this page is the figure read at the amendment that wrote it — the 2026-09-16
rebase unless its section is dated otherwise — never a live figure; measure
again before relying on one.

| Term | Meaning |
|---|---|
| Station, Smith | The eight stations: atlas, doctor, herald, marshal, mason, scribe, steward, warden. *Smith* is the brand word for a station's agent (Charter § *The Lexicon*). A station has a long and a short form; § 5 says which a place takes. |
| Charter | The constitutive Dream `docs/dreams/pyforge-charter.md` and its Spec `docs/governance/spec-pyforge-charter/`; *Charter §n* is a numbered section of that Dream. |
| `CAP-n` | A capability in a Spec: an intent and a success clause. Everything below the Spec cites one (§ 2). |
| `FR-n`, `NFR-n` | A functional or non-functional requirement in a station PRD; each cites the CAPs it realizes or bounds (§ 2, § 6, § 12). |
| `AD-n`; `canopy:`, `pap:`, `fnd:` | An architecture decision in a spine, cited with its spine prefix: `canopy` for steward's spine (the Canopy, the platform's modular monolith), `pap` for the platform host's (python-agent-platform), `fnd` for the foundry cutover's (folded into the steward spine on 2026-09-08). |
| A, B | A is `rxm7706/local-recipes`, this repository; B is `rxm7706/python-foundry`, the root the cutover moves to. |
| Frame | The Intelligence Hub's word for a scoped, versioned text artifact that carries context and policy (`docs/dreams/pyforge-steward.md`, *The whitepaper, distilled* § 4.3). B rebuilds its engines from Frame and Spec. |
| CFE | The `conda-forge-expert` skill (`.claude/skills/conda-forge-expert/`), which owns recipe semantics. |
| Twin | The tracked `sprint-status-ledger.yaml`, which `sprint-ledger-sync` (`scripts/promote_sprint_status.py`) generates from the gitignored Tier-3 sprint feed. |
| Tier 0, 2, 3 | Dream; Spec and planning; execution output (AGENTS.md § *The tiers*). Tier 1, the legacy intake specs under `docs/specs/`, was retired on 2026-10-10 (§ 11 item 3). |
| The rebase | The one-time fold that brought each station to one chain: the marshal pilot on 2026-09-16, the other seven stations on 2026-09-17. "Retired at the rebase" means retired then. |
| Path B | A station persona that acts only through the `pyforge <station> …` grammar and its `POST /stations/<station>/mcp` face (`spec-pyforge-unifying-strategy:CAP-16`). |
| Lane 1 | The Wagtail CMS at `/`, the platform's front door. Lane 2 is the station portals at `/stations/<name>/` (`docs/explanation/pyforge-estate-overview.md`). |

**Where a citation resolves.**

- *Lesson N*: the numbered fold lessons in this folder's
  `docs/governance/spec-one-chain-per-station/.memlog.md` (its 2026-09-16 and
  2026-09-17 `note` entries).
- *Vocabulary CAP-n*, and *Q14* (that Spec's open question 14): the absorbed
  `spec-vocabulary-one-name-one-job`, whose pointer and memlog are under
  `archive/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-vocabulary-one-name-one-job/`.
  Its capabilities live on as `spec-pyforge-steward:CAP-132` to `spec-pyforge-steward:CAP-138`; their
  `← spec-vocabulary-one-name-one-job CAP-n` provenance lines are in
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md`.
- *Spec CAP-n*: this folder's Spec, `docs/governance/spec-one-chain-per-station/SPEC.md`.
- *README*: `docs/dreams/README.md`, the Dream status vocabulary.
- *Roster*: `docs/governance/guild-roster.json` (`fold_exemptions`, `session_denials`).

## 1. The hierarchy — one of each, per station

```
docs/dreams/pyforge-<s>.md                                   Dream        status: specified   (forever)
_bmad-output/projects/pyforge-<s>/planning-artifacts/
  specs/spec-pyforge-<s>/SPEC.md  +  .memlog.md               Spec         status: ready       (forever; each CAP-n reads (ready <date>), then (shipped <date>))
  specs/spec-<E>-<S>-<slug>.md                               story spec   one file per story, named by the ledger key
  prds/prd-pyforge-<s>-<created>/prd.md                      PRD          FR-n  ← CAP-m  (traced, never numbered)
  architecture/architecture-pyforge-<s>-<created>/           spine        AD-n  (prefixed: canopy:AD-n, pap:AD-n, fnd:AD-n)
  epics.md                                                   Epic E / Story E.S — sequential from 1, no gaps
  sprint-status-ledger.yaml                                  key: <E>-<S>-<slug>  (generated; never hand-edited)
  deferred-work-ledger.md                                    DW-<STATION>-<n>
implementation-artifacts/                                    Tier 3 — gitignored, never tracked
```

Plus **declared seams** (Spec CAP-3): a Spec folder that survives the fold
carries `fold-exemption: cross-station-seam` in its frontmatter. Today: marshal's
`spec-pyforge-core` and `spec-pyforge-testing-charter`. Plus the **Guild chain**
under `docs/governance/spec-<slug>/` for the constitutive Dream and gates that
judge every Smith (Charter §5 as amended 2026-09-14). Plus **marshal's factory-doc
set** (operator ruling 2026-10-26, the one-chain re-audit): `_bmad-output/projects/pyforge-marshal/planning-artifacts/PRD.md`,
its `architecture.md` and four `architecture-<part>.md`, `integration-architecture.md`
and `validation-report-PRD.md` in the same directory — the whole-factory rebuild
contract the PRD's own § 0 decomposes across five stations, not a chain PRD: no
`FR-n`, never read by `fr-without-cap`, governed by `bmad-drift` and
`_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md`, and never moved into
`prds/` (marshal's planning README § *Deliberate asymmetries*).

**Everything else is a section, a CAP, or a Story** — never a new file.
A new `docs/dreams/*.md` or `spec-*/` folder needs `fold-exemption:` from
`{different-owner, different-lifecycle, cross-station-seam, governance}`
(Spec CAP-1); `chain-sprawl-check` refuses the rest (CAP-2).

## 2. The relations — every arrow points up

```
Dream § dated section  →  CAP-n  →  FR-n  →  AD-n  →  Story E.S  →  ledger key  →  story spec  →  code
       (why)              (what)    (PRD)    (how)     (work)         (state)        (contract)
```

- A **CAP** cites the Dream section it realizes, in its memlog `capability`
  entry. It reads `(ready <date>)` until it is met and `(shipped <date>)`
  once it is (operator ruling 2026-11-01).
- A CAP's **success** clause names the command or test that proves it and the
  exit code that proves it, and that command fails when the capability is
  absent (operator ruling 2026-11-01; rule text only — no detector checks it
  yet).
- A citation of another Spec's capability is always qualified:
  `spec-<x>:CAP-n` (operator ruling 2026-11-01).
- A **requirement** (`FR-n`, `NFR-n`) cites one or more *defined* CAPs —
  `← CAP-m`, or `← spec-<x>:CAP-m` for another Spec's capability — and
  nothing else: never a Spec Constraint, a Charter clause, an AD or a
  decision id (Spec CAP-5 as amended 2026-10-26; `fr-without-cap`; §12).
  The arrow is traced from the cited CAP's intent and success, never
  numbered in sequence.
- A Spec **Constraint** reaches code through an **AD** that names the
  Constraint by its bolded lead and the CAPs it bounds. A Constraint that
  promises something a user or operator can see is minted as a CAP through
  `bmad-spec`, with the Constraint as provenance, and requirements cite that
  CAP. A PRD line that only restates HOW is not a requirement: it lives in
  the PRD's *Constraints and Guardrails* section (or `addendum.md`) as prose
  naming its AD.
- An **AD** cites the FR/CAP it decides for.
- A **Story** carries `FR:` and `AD:` lines and cites its CAP range (INV-A).
- A **story spec** is named by the ledger key and cites the Story heading.
- **Downward references are provenance only** — a memlog line or the fold
  PR's re-key map — never a live pointer a detector must keep green.

## 3. The sequence — the four BMAD phases, in order, per change

| # | Phase | Act | Artifact that moves |
|---|---|---|---|
| 1 | analysis | append a dated section to the station Dream | `pyforge-<s>.md` |
| 2 | analysis | append the memlog; re-derive the Spec (`bmad-spec`) | `.memlog.md` → `SPEC.md` CAP-n |
| 3 | planning | re-derive the PRD; new FR cites its CAP | `prd.md` FR-n |
| 4 | solutioning | append an AD only if the *how* changed | spine AD-n |
| 5 | implementation | mint the Story (heading + ledger key + story spec, one function) | `epics.md`, ledger, `spec-<key>.md` |
| 6 | implementation | build in a worktree; land by PR | code |
| 7 | implementation | story `done`; the CAP's `(ready <date>)` becomes `(shipped <date>)`; Dream log entry | ledger → `SPEC.md` → Dream |

No step is skipped for a "small fix" (AGENTS.md Dream-first §5). Steps 3–4
may be no-ops (recorded as such in the memlog), never absent.

## 4. Statuses — acts that completed, one enum per tier

| Tier | Enum (closed) | The living value | Retired at the rebase |
|---|---|---|---|
| Dream | `dreamt · pitched · specified · realized · archived` | station Dream = **`specified`** | — (`living` rejected: an ongoing state in an act-based ladder; README + roster) |
| Spec | `draft · ready · shipped · archived · absorbed · superseded · extension-point` | station Spec = **`ready`** — "the contract binds", forever; each CAP reads `(ready <date>)` until met and `(shipped <date>)` once met | **`in-progress`** — 17 uses at this amendment → 0 (vocabulary CAP-1/2 said "grandfathered only, never write new"; the rebase ends the grandfathering) |
| Story (ledger) | `backlog · in-progress · done · blocked · optional` | — | — (`optional` is BMAD's retrospective lattice, vocabulary CAP-3; `blocked` is operator-flipped only) |
| Story spec (frontmatter) | `draft · ready-for-dev · in-progress · in-review · done · blocked · superseded` | — | — (a story's own ladder, `.claude/skills/bmad-build-auto/spec-template.md`; not the ledger enum) |

**The story-spec ladder is not mapped onto the ledger.** No code translates
one into the other. `scripts/promote_sprint_status.py` never reads story-spec
frontmatter: it copies the Tier-3 feed's story values into the twin unchanged, keeps
`done` terminal and story `blocked` sticky, and ranks feed values
(`_STORY_PROGRESS_RANK`: `backlog` 0, `ready-for-dev` 1, `in-progress` 2,
`review` 3, `done` 4) only to roll up epics and to pick between a stale and a
current key. The one place story-spec values are read is a landing
(`src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py`,
`PRE_DONE_SPEC_STATUSES` and `TERMINAL_SPEC_STATUSES`, applied by
`dispatch_land_finalize`): a merged story's tracked spec at `draft`,
`ready-for-dev`, `in-progress` or `in-review` (or at the ledger words
`backlog`, `ready` or `review` that older specs carry) is set to `done`;
`done`, `blocked` and `superseded` are left alone, as deliberate states; any
other value is a warning.

Coupling: Dream `specified` ⇔ its Spec at `ready` or beyond (README). Spec
`shipped` ≠ story `done` ≠ Dream `realized` (vocabulary CAP-3). A station Dream
never reads `realized` and a station Spec never reads `shipped`: those are CAP-
and story-level facts (Spec CAP-6).

## 5. Names — one form per concept

| Concept | Form | Source |
|---|---|---|
| Station, long | `pyforge-<s>` — paths (`_bmad-output/projects/pyforge-<s>/`), packages, pixi envs (`-e pyforge-<s>`), the BMAD project slug (`BMAD_ACTIVE_PROJECT`, `scripts/bmad-switch`) and `marshal … --project` | vocabulary CAP-7; amended 2026-11-01 |
| Station, short | `<s>` — `owner:`, `Source`, prose, ids, and `sprint-ledger-sync --project` (a dashboard key: it refuses the long form) | vocabulary CAP-7; amended 2026-11-01 |
| Station token | `<s>` — the short name, **the same token** in CLI, URL, distribution, skill, persona and ids; uppercased inside an id (`DW-MARSHAL-n`) | steward spine § Station token; vocabulary CAP-6 |
| Epic heading | `## Epic E: <Title>` | live convention, all eight |
| Story heading | `### Story E.S: <Title>` — human-canonical | vocabulary CAP-6 |
| Ledger key | `<E>-<S>-<slug>` — machine-canonical; slug derived from the title by **one mint function** | vocabulary CAP-6 |
| Story spec file | `spec-<E>-<S>-<slug>.md` — `spec-` + the ledger key, exactly | vocabulary CAP-6 |
| Station Spec folder | `spec-pyforge-<s>/` with `SPEC.md` + `.memlog.md` | Spec CAP-3 |
| PRD / spine folder | `prd-pyforge-<s>-<created>/`, `architecture-pyforge-<s>-<created>/` — one per station; `updated:` moves, the folder does not | AGENTS.md § Dates |
| Detector task | `<noun>-check` (pixi task), finding `check=` is a kebab code, never a package name | vocabulary CAP-8 |
| Memlog entry type | `event · decision · note · capability · constraint · change · question · assumption · direction · non-goal · correction · provenance · success` | live enum, 13 (the 19 malformed `(non` entries are repaired at the rebase) |
| Commit subject | Capitalized sentence, no trailing period; `type(scope):` only under `recipes/` and the CFE changelog | vocabulary CAP-7 |
| Dates vs versions | `YYYY-MM-DD` in names/frontmatter; `YYYY.M.D` CalVer in versions/tags | AGENTS.md § Dates |

**The 53 story-spelling divergences vocabulary CAP-6 left in place are gone at
the rebase** — every renumbered story is minted through the one function, so
heading, key and filename agree for all 1,445 stories at this amendment, not
only new ones.

## 6. Identifiers — one family per job

| Job | Family | Scope | Source |
|---|---|---|---|
| Spec capability | `CAP-n` | per station Spec, sequential from 1 | Spec CAP-3(b) |
| Product requirement | `FR-n`, `NFR-n` — or a lettered NFR family `NFR-<L>n` where a PRD groups its NFRs (marshal `NFR-C2`, warden `NFR-S8`); the one grammar is `N?FR-[A-Z]?\d+(\.\d+)*`, always hyphenated; the letters are sections of the one lettered family (marshal's R, A, P, C, S, M, O), and what is forbidden is mixing `NFR-n` with `NFR-<L>n` in one PRD or spelling an id outside the grammar (`NFR-R3a`, `NFR-P-warm`) | per PRD; each `← CAP-m` naming the defined CAP(s) it realizes (FR) or bounds (NFR), and nothing else — never a Constraint, Charter clause, AD or decision id (§2, §12) | Spec CAP-5 (amended 2026-10-26) |
| Architecture decision | `<spine>:AD-n` | per spine | steward spine |
| Story | `E.S` | per station, sequential | vocabulary CAP-6 |
| Deferred work | `DW-<STATION>-<n>` — **one** family, station token, sequential | per station | vocabulary CAP-6 Q14 said "new ids carry the token; no retro-rename of 1,338" — the rebase ends that carve-out: topic-word families (`DW-VOCAB-`, `DW-LEDGER-`, `DW-CANOPY-`, `DW-FU-`…) re-key through the fold map |
| Open question | `OQ-n` | per Spec, closed in frontmatter with the ruling | live |
| Detector invariant | `INV-<letter>` | per detector | live |
| CFE gotcha | `G-nn` | recipe domain only | CFE skill |
| Station rule / finding id | `<STATION>-<n>` — **one** family per station (`MARSHAL-033`); scope is prose, not id | per station | **new at the rebase** — replaces the 14-prefix long tail (`MRS-DISP-`, `HER-`, `GATE-`, `SM-`, `LB-`, `BS-`, `SC-`, `FU-`, `RB-`, `PORT-`, `DC-`, `DRAIN-`, `ATLAS-`, `MEM-`) |

**Eventual consistency for code-cited ids** (Spec Constraint): at this
amendment, `MRS-*` (100 files), `GATE-*` (27), `FU-*` (22), `SC-*` (15), `ATLAS-*` (9), `DRAIN-*` (6)
are cited in `src/`. The planning artifacts re-key in the fold PR; the code
citations migrate when their module is next touched, each with a memlog line.
A planning artifact never waits on code to conform.

## 7. What a fold PR must show (the checklist the operator does not write)

1. Re-key map committed: `planning-artifacts/rekey-<date>.md`, one line per
   old → new key (stories, CAPs, DW ids, rule ids).
2. `spec-pyforge-<s>/SPEC.md` at `ready`; `covers-dreams:` lists every folded
   Dream; CAPs sequential from 1 with `← spec-old CAP-m` provenance lines.
3. Every absorbed Spec folder: pointer header + its memlog + **every
   companion document it had**. Companions (inventories, whitepapers,
   audit methods, verification records, playbooks) are *record*, not
   derived bodies; one moves only with a memlog line naming its new path
   and is never deleted. (Marshal pilot, lesson 15: this line read
   "nothing else" and 24 companions were lost to it before review.)
4. Every folded Dream's whole body is in a dated section of the station
   Dream, verbatim, with its headings demoted one level. Only then does the
   file move to `archive/docs/dreams/<slug>.md` (`git mv`, never a delete),
   and every reference to its old path is repointed. No `Consolidated into`
   banner (§11; CAP-11, 2026-09-29, superseding the banner rule).
5. `epics.md`: `## Epic E` sequential from 1; `### Story E.S` sequential;
   ledger regenerated through the map — zero `done → not-done` transitions.
6. Story spec files renamed to `spec-<key>.md`; zero spelling divergences.
   `deferred-work-ledger.md` rows citing a renamed file are **re-pointed
   through the map** (`source_spec:`, `location:`) — never re-ingested with
   `deferred_work_intake.py --fix`, which appends a duplicate row per
   fingerprint (pilot lesson 16).
7. PRD re-derived; every FR cites a CAP (`fr-without-cap` green).
8. `dream-chain`, `dreams-hygiene`, `chain-completeness`, `spec-surface`,
   `story-status`, `ledger-regression`, `status-body-consistency`,
   `chain-sprawl`, `deferred-work`, `bmad-drift` — all green on the PR head,
   **proved by a local `detectors-ci` run**: the CI `detectors` check is
   advisory (findings print as warnings, the step exits 0), so its green is
   not evidence (pilot lesson 17).
9. `spec-foundry-regenerate-not-fold` memlog entry naming the folded Spec
   (CAP-7), before the *next* station begins.

## 8. Order of stations

marshal (pilot) → steward → herald → scribe · doctor · atlas · warden ·
mason in parallel. Mason was **not** already one Spec (lesson 30, 2026-09-17):
it took the full §7 checklist (twelve folders → `spec-pyforge-mason`
CAP-1..27). Do not steal CAPs from a folder already `absorbed-into` the
Guild chain.

## 9. Lock, mop, exemption — when a fold PR runs (CAP-10)

**Read this before opening another fold PR.** After the eight station
chains exist, 1:1 is the **lock**, not a periodic fleet fold.

| Verb | Meaning |
|---|---|
| **lock** | Dream-append-first + `chain-sprawl-check`. Day-to-day is §3. |
| **exemption** | New Dream/Spec folder only with `fold-exemption:` from `guild-roster.json` `fold_exemptions`. |
| **mop** | §7 fold PR only when unexempted satellites already reached `main`. One station, one PR, `fold/<s>`. |

An unexempted satellite on a PR is rewritten to a dated station-Dream
section plus a station Spec CAP; drop the extra file. Do not reset or
un-archive. Parallel agents: one worktree per station; serialize shared
memlogs, `fr-baseline.json`, and `capability-ledger.yaml`; merge `--merge`
one at a time. Environment: `pixi run -e pyforge-guild`. Never
`scripts/bmad-switch` from a parallel agent. This page is the checklist —
not a harness-specific workflow.

## 10. Parallel-fold lessons (2026-09-17, leftover shared memlog)

Station folds do **not** write this Spec's memlog, `spec-foundry-regenerate-not-fold`,
or `chain_sprawl_baseline.py --prune` (lesson 31). CAP-7 for the six
parallel stations is one leftover PR. Extra checklist teeth from that wave:

- STEP 0: seed a missing Tier-3 feed from the twin; `--rekey` only while
  old keys still exist in the feed (lesson 29).
- Surface YAML: `_parse_surface` wants two-space `- ` lists, never
  column-0 dumps; do not quote `src/**` (lessons 24, 32).
- DW `source_spec` matches on-disk `specs/spec-*.md` slugs, longest-old-key
  first; never `--fix` (lessons 16, 27, 33).
- `mint_slug` strips apostrophes as well as italic `*(…)*` (lesson 34).
- Copy inline `Intent:`/`Success:` from `HEAD` before pointer rewrite
  (lessons 19, 35). Reminted CAPs live under `## Capabilities` as
  `### CAP-N —` headings (lesson 37).
- Do not stamp a `[recipes/**]` pointer that has empty `files: {}`; keep
  `surface-drift` / `exempt` (lesson 38). No `recipes/` and no
  `.claude/skills/pyforge-mason/` on a fold PR.
- Capability-ledger rows for every reminted CAP in the same pass as
  `ready` (lesson 39). Cascade spine `updated:`; never two `updated:`
  keys (lesson 40). Archive specified satellites; keep already-archived
  banners (lesson 44). *(Superseded 2026-09-29 by §11 and CAP-11: a folded
  Dream carries no banner and moves to `archive/docs/dreams/` once its body
  is in the station Dream.)*
- Shared `pixi.lock` / `pixi.toml` stay on their owning Specs, not the
  station Spec (lessons 25, 28, 43–44).

## 11. One archive home (CAP-11, 2026-09-29)

Everything the fleet retires goes to one place: `archive/<original path>`,
structure-preserving, so `archive/docs/dreams/foo.md` was
`docs/dreams/foo.md`. That is the rule `archive/docs/README.md` already
states. Nothing is deleted; every move is a `git mv`. No other archive
location is used: `docs/dreams/archive/` and atlas's `spec-archive/` fold
into this one.

**A Dream is live or archived, never both.** A live Dream sits in
`docs/dreams/`. An archived one sits under `archive/docs/dreams/`, and
nothing in `docs/dreams/` reads `status: archived`.

**A fold is complete before the file moves.** The satellite's whole body
goes, verbatim, into a dated section of its station Dream, with its headings
demoted one level. A doctor check confirms that the satellite's paragraphs
are there. Then the file moves and its references are repointed. Where the
body is already in the station Dream (steward's 2026-09-17 fold), the move
is all that is left to do.

**The order.**

1. Archived Dreams, one station per PR (§9's mop shape). Steward goes
   first, because its bodies are already in its station Dream.
2. Absorbed and archived Spec folders, each with its memlog and every
   companion (§7 item 3 still holds; it now holds under `archive/`).
   `owner-dream:` and `covers-dreams:` are repointed in the same PR.
3. `docs/intake/`, which keeps only its README, because the inbox rule
   stays. `docs/specs/`, whose legacy tier retires once its last files are
   carried into a station chain or archived. `CLAUDE.md`'s legacy index,
   `AGENTS.md`'s Tier 1 row and doctor's `check_spec_indexed` go in the same
   PR that empties the directory. *(Done 2026-10-10, doctor Story 37.1:
   `docs/specs/` is empty and gone, its files under `archive/docs/specs/`, and
   the index, the Tier 1 row and `check_spec_indexed` went with it;
   `docs/intake/` keeps only its README.)*

**Readers follow the move.** Anything that lists Dreams (the console's
Archived column, the deck facts, scribe's compile, the sibling-drift check)
reads `archive/docs/dreams/` wherever it needs archived Dreams. Those
changes land as Stories before the first fold PR moves a file.


## 12. Requirements derive from capabilities (CAP-5 amended, 2026-10-26)

**The rule.** A requirement (`FR-n`, `NFR-n`, or a lettered NFR family)
cites one or more *defined* CAPs and nothing else. `← CAP-m` resolves
against the station Spec's capability *definition* lines; `← spec-<x>:CAP-m`
resolves against the named Spec's (the detector also reads the older
space-separated `spec-<x> CAP-m`; new arrows use the colon, § 2). A Spec Constraint is realized by an AD
that names the Constraint by its bolded lead; a Constraint that promises a
user- or operator-visible guarantee is minted as a CAP through `bmad-spec`
(the Constraint is its provenance) and requirements cite that CAP; a line
that only says how something is built is not a requirement and goes in the
PRD's *Constraints and Guardrails* section naming its AD. Arrows are traced
from the cited CAP's intent and success, never numbered in sequence.

**Why.** §2 and §6 already required `← CAP-m` and this page's preamble says
the artifact moves; Spec CAP-7 names FR ← CAP as B's (`rxm7706/python-foundry`)
starting discipline; the capability ledger (`docs/foundry/capability-ledger.yaml`)
routes only capabilities, so a requirement sourced from a Constraint has no
rebuild/retire decision anywhere; Constraints have no stable id, so a
quoted-text arrow breaks on the first rewording and no detector can resolve
it; and every Constraint-cited requirement already lived as an AD in its
spine (atlas AD-16; marshal A-04, A-05, P-10, L-01).

**The ruling it records, and the rulings it reverses.** Operator,
2026-10-26: *"yes forbid it — single pr for all stations / all open items for
pyforge stations and aligned to unifying strategy / cutover"*. This
supersedes the 2026-10-25 rulings on `spec-pyforge-atlas` (memlog, Story
40.1: *"FR-15, 'Cite the constraint (Recommended)' — an FR that derives from
a Spec Constraints bullet, not a capability, names the constraint in its
arrow"*) and on `spec-pyforge-marshal` (memlog, Story 106.1: *"Cite the
constraint (Recommended)": the arrow names the constraint, e.g.
`<- Constraint "Copier is a dependency, not a framework"`*; and the round-1
review ruling for FR-101, *"CAP-15 + constraint (Recommended)"*). Those
rulings were made on a brief that did not show that each Constraint already
lived as an AD, nor the ledger and CAP-7 consequences. The arrows they
produced (atlas FR-15; marshal FR-101, FR-120, FR-121, FR-125, FR-126) are
re-pointed by atlas Story 41.1 and marshal Story 108.1 (FR-125 to marshal
CAP-297, minted from the Constraint "Two clocks" on the Story 108.1 review —
this section's own rule applied); doctor FR-14 and FR-15, which cited
Charter §6, by doctor Story 50.1.

**NFRs.** §6 says every NFR cites a CAP; at this amendment none of the 82 NFR
lines fleet-wide did (atlas 10, marshal 33, mason 16, warden 23, as the detector
reads them), and marshal's and warden's ids are lettered (five of warden's
outside the grammar: `NFR-R3a`, `NFR-R3b`, `NFR-P-warm`, `NFR-P-cold`,
`NFR-P-concurrency`). The lettered family is sanctioned (§6); an NFR
cites the CAP(s) it bounds; the 82 enter `docs/governance/fr-baseline.json`
as the pre-rule population and leave it as each station's backfill story
lands (atlas 41.3, marshal 108.2, mason 33.2, warden 20.2).

**One writer.** `docs/governance/fr-baseline.json` changes only through
`scripts/fr_baseline.py`, never by hand: `--prune` is the routine verb and only
removes entries; the file grows only through that script's one-time acts
(`--snapshot-findings`, and `--project pyforge-<s>` at a station's fold PR).
Once `findings` exists, `--snapshot-findings` prints the keys it would add
and remove and refuses without `--force`; `--project` prints the same delta
and refuses an addition without `--force`; only a review that names each
added key in the PR justifies `--force`. The script records each key it adds,
with the HEAD it ran at, in the file's `forced` list. The guard is doctor Story 50.2's: `fr-without-cap`
reads the file at the merge-base of `HEAD` and `refs/remotes/origin/main`, and
a `projects` id or `findings` key added since that no `forced` record names is
`fr-baseline-grown` (FAIL) — an `owners` row, written by hand, never admits
one. A base it cannot read (no `refs/remotes/origin/main`, a shallow clone,
the file absent there) is `fr-baseline-base-unread` (WARN), never a FAIL.

**Enforced, not asserted.** `fr-without-cap` (doctor CAP-92, Story 50.1)
fails, on new findings against a baseline that only shrinks: a post-date
requirement with no CAP; a non-CAP arrow (`fr-cites-non-capability`); a cite
that resolves to no definition line (`fr-cap-unresolved`); an unhyphenated
id (`fr-id-unhyphenated`); an id spelled outside the grammar
(`fr-id-malformed`); a second definition of an id in one PRD
(`fr-duplicate-id`); and a counted run — four or more consecutive
requirements whose CAP number steps with the requirement number while their
titles share no word with the CAPs' (`fr-counted-run`). It fails, too, a
baseline key added by hand since the merge-base (`fr-baseline-grown`, Story
50.2), and warns when that base cannot be read (`fr-baseline-base-unread`).
A title-overlap score is advisory only. The same rule travels as `persistent_facts` in
`_bmad/custom/bmad-prd.toml`, `bmad-spec.toml` and `bmad-architecture.toml`,
as the `fr-arrow` review lens in `bmad-build.toml`, and as
`spec-foundry-regenerate-not-fold` CAP-7's on-ramp line for B.
