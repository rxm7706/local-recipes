---
title: The chain standard — one page, every station, both roots
type: companion
spec: one-chain-per-station
status: ready
created: "2026-09-16"
updated: "2026-09-17"
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

Applies to `local-recipes` now and `pyforge-foundry` on cutover (Spec CAP-7).

---

## 1. The hierarchy — one of each, per station

```
docs/dreams/pyforge-<s>.md                                   Dream        status: specified   (forever)
_bmad-output/projects/pyforge-<s>/planning-artifacts/
  specs/spec-pyforge-<s>/SPEC.md  +  .memlog.md               Spec         status: ready       (forever; CAP-n carry their own met dates)
  specs/spec-<E>-<S>-<slug>.md                               story spec   one file per story, named by the ledger key
  prds/prd-pyforge-<s>-<created>/prd.md                      PRD          FR-n  ← CAP-n
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
judge every Smith (Charter §5 as amended 2026-09-14).

**Everything else is a section, a CAP, or a Story** — never a new file.
A new `docs/dreams/*.md` or `spec-*/` folder needs `fold-exemption:` from
`{different-owner, different-lifecycle, cross-station-seam, governance}`
(Spec CAP-1); `chain-sprawl-check` refuses the rest (CAP-2).

## 2. The relations — every arrow points up

```
Dream § dated section  →  CAP-n  →  FR-n  →  AD-n  →  Story E.S  →  ledger key  →  story spec  →  code
       (why)              (what)    (PRD)    (how)     (work)         (state)        (contract)
```

- A **CAP** cites the Dream section it realizes (memlog `capability` entry).
- An **FR** cites its source CAP (`FR-n ← CAP-m`; Spec CAP-5, `fr-without-cap`).
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
| 7 | implementation | story `done`; CAP gains its met date; Dream log entry | ledger → `SPEC.md` → Dream |

No step is skipped for a "small fix" (AGENTS.md Dream-first §5). Steps 3–4
may be no-ops (recorded as such in the memlog), never absent.

## 4. Statuses — acts that completed, one enum per tier

| Tier | Enum (closed) | The living value | Retired at the rebase |
|---|---|---|---|
| Dream | `dreamt · pitched · specified · realized · archived` | station Dream = **`specified`** | — (`living` rejected: an ongoing state in an act-based ladder; README + roster) |
| Spec | `draft · ready · shipped · archived · absorbed · superseded · extension-point` | station Spec = **`ready`** — "the contract binds", forever; CAPs carry `(Met <date>)` | **`in-progress`** — 17 live uses → 0 (vocabulary CAP-1/2 said "grandfathered only, never write new"; the rebase ends the grandfathering) |
| Story (ledger) | `backlog · in-progress · done · blocked · optional` | — | — (`optional` is BMAD's retrospective lattice, vocabulary CAP-3; `blocked` is operator-flipped only) |

Coupling: Dream `specified` ⇔ its Spec at `ready` or beyond (README). Spec
`shipped` ≠ story `done` ≠ Dream `realized` (vocabulary CAP-3). A station Dream
never reads `realized` and a station Spec never reads `shipped`: those are CAP-
and story-level facts (Spec CAP-6).

## 5. Names — one form per concept

| Concept | Form | Source |
|---|---|---|
| Station, long | `pyforge-<s>` — paths, packages, pixi envs, project slugs | vocabulary CAP-7 |
| Station, short | `<s>` — `owner:`, `Source`, prose, `--project` keys | vocabulary CAP-7 |
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
heading, key and filename agree for all 1,445 stories, not only new ones.

## 6. Identifiers — one family per job

| Job | Family | Scope | Source |
|---|---|---|---|
| Spec capability | `CAP-n` | per station Spec, sequential from 1 | Spec CAP-3(b) |
| Product requirement | `FR-n`, `NFR-n` | per PRD; each `← CAP-m` | Spec CAP-5 |
| Architecture decision | `<spine>:AD-n` | per spine | steward spine |
| Story | `E.S` | per station, sequential | vocabulary CAP-6 |
| Deferred work | `DW-<STATION>-<n>` — **one** family, station token, sequential | per station | vocabulary CAP-6 Q14 said "new ids carry the token; no retro-rename of 1,338" — the rebase ends that carve-out: topic-word families (`DW-VOCAB-`, `DW-LEDGER-`, `DW-CANOPY-`, `DW-FU-`…) re-key through the fold map |
| Open question | `OQ-n` | per Spec, closed in frontmatter with the ruling | live |
| Detector invariant | `INV-<letter>` | per detector | live |
| CFE gotcha | `G-nn` | recipe domain only | CFE skill |
| Station rule / finding id | `<STATION>-<n>` — **one** family per station (`MARSHAL-033`); scope is prose, not id | per station | **new at the rebase** — replaces the 14-prefix long tail (`MRS-DISP-`, `HER-`, `GATE-`, `SM-`, `LB-`, `BS-`, `SC-`, `FU-`, `RB-`, `PORT-`, `DC-`, `DRAIN-`, `ATLAS-`, `MEM-`) |

**Eventual consistency for code-cited ids** (Spec Constraint): `MRS-*` (100
files), `GATE-*` (27), `FU-*` (22), `SC-*` (15), `ATLAS-*` (9), `DRAIN-*` (6)
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
4. Every folded Dream: `status: archived`, `Consolidated into` banner.
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
  banners (lesson 44).
- Shared `pixi.lock` / `pixi.toml` stay on their owning Specs, not the
  station Spec (lessons 25, 28, 43–44).
