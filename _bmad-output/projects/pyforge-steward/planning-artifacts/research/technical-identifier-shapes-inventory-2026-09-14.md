---
title: "Identifier shapes — how the estate spells the things its vocabulary names"
chain: "vocabulary-one-name-one-job"
created: "2026-09-14"
type: research
owner: steward
head: 445976e5be
status: draft   # research input for the Dream seed; no decision taken here
---

# Identifier shapes — one thing, many spellings

**Why this exists.** The three-source pass
(`technical-vocabulary-three-source-reconciliation-2026-09-14.md`) asked *which vocabulary does
this word belong to*. It did not ask the adjacent question: **when the estate writes down the
name of a thing, what shape does it use** — and does it use the same shape twice? A status word
can be perfectly reconciled and still be unreachable, because the id carrying it cannot be
parsed. This pass measures shapes, not word choice. **It takes no decision.**

**Method.** One read-only sweep on 2026-09-14 against `main` `445976e5be`. Every claim below
carries the command that produced it; nothing is recalled. Nine surfaces were enumerated:
station names, epic/story addressing, spec names, Dream names, deferred-work ids, detector
finding codes, pixi task names, branch/commit subjects, and planning-artifact filenames.

**Working-tree caveat — load-bearing.** The sweep measured the **working tree**, which was dirty
(`git status --porcelain | wc -l` → **36**). Three `epics.md` files carry uncommitted edits.
This changes one result materially — see § 8. Re-run against a clean checkout before treating
any count here as a baseline.

---

## 1. The one shape that never varies

```
grep -hoE '^#{2,5} Story [0-9]+\.[0-9]+' _bmad-output/projects/*/planning-artifacts/epics.md
  → 952, ALL at '###'
grep -hoE '^### Story [0-9]+\.[0-9]+.' … | grep -oE '.$' | sort | uniq -c
  → 952 ':'      (zero em-dashes, zero hyphens)
```

`^### Story \d+\.\d+: .+$` holds **952/952** across all eight stations. It is the only
identifier convention in the estate with no exceptions, and it is the reference point for
everything below: the shape exists and is achievable.

The doctor finding codes are the second-cleanest: **124 distinct codes, 124 matching
`^[a-z0-9]+(-[a-z0-9]+)*$`** (union of literal `check=` values, `_CHECK_*` module constants, and
`"kind"` literals under `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/*.py`).

---

## 2. The same story, spelled three ways — 2760 instances

| Place | Shape | Count |
|---|---|---|
| `epics.md` heading | `### Story <E>.<S>: <Title Case prose>` | 952 |
| `sprint-status-ledger.yaml` key | `<E>-<S>-<lowercase-slug>:` | 952 |
| `specs/` filename | `spec-<E>-<S>-<lowercase-slug>.md` | 856 |

The same story, in three files, three spellings:

```
### Story 33.9: `verify_scope` guards `marshal factory dispatch`
33-9-verify_scope-guards-marshal-factory-dispatch:
spec-33-9-verify_scope-guards-marshal-factory-dispatch.md
```

No two are mechanically derivable from each other without a slugify step — **and that step is
not deterministic.** Comparing ledger slug against spec-file slug for every story number present
in both (`comm` on the two sorted slug lists, per project):

| project | ledger keys | spec files | identical slug | same № **different slug** |
|---|---|---|---|---|
| atlas | 95 | 95 | 76 | **19** |
| doctor | 95 | 92 | 89 | 2 |
| herald | 94 | 82 | 62 | **19** |
| marshal | 271 | 230 | 222 | 7 |
| mason | 70 | 68 | 66 | 2 |
| scribe | 35 | 33 | 32 | 1 |
| steward | 243 | 207 | 204 | 3 |
| warden | 49 | 49 | 49 | 0 |
| **total** | **952** | **856** | **800** | **53 / 842** |

Drift examples: atlas 21.4 ledger `tier-1-catalog-sources-selfexplainml-anaconda-basilisk-aoss`
vs spec `tier-1-catalog-sources`; atlas 21.2 ledger `remove-cf_atlas-db-seeds-…` vs spec
`remove-cf-atlas-db-seeds-…` (underscore normalized on one side only); atlas 10.5 spec carries a
`-2` suffix the ledger lacks.

**The slugify is not closed over its own alphabet.** 14 of 952 ledger keys fail
`^\d+-\d+-[a-z0-9-]+$`: `33-9-verify_scope-…` (underscore),
`22-4-a-diátaxis-adapted-…` (non-ASCII), `34-4-the-attention-block-s-own-…` (typographic
apostrophe collapsed to `-s-`), `23-5-identity_complete_export-parquet-canonical`. A key-matching
regex over the documented shape silently drops all 14.

A fourth spelling lives in branch names (§ 6) and a fifth in prose (§ 3).

---

## 3. Prose reference — `Story N.N` 11941 ⟷ `S-N.N` 2615

```
grep -rhoE '\bStory [0-9]+\.[0-9]+\b' _bmad-output/projects/*/planning-artifacts docs/ | wc -l  → 11941
grep -rhoE '\bS-[0-9]+\.[0-9]+\b'     _bmad-output/projects/*/planning-artifacts docs/ | wc -l  →  2615
```

Both forms occur in the same files. marshal 1303 `S-` against 3178 `Story`; mason 505 / 1304;
warden barely uses it, 34 / 710. Neither form is declared anywhere.

---

## 4. Deferred-work ids — 11 shapes over 1338 ids

```
grep -hoE 'DW-[A-Za-z0-9._-]+' _bmad-output/projects/*/planning-artifacts/deferred-work-ledger.md
  → 2155 mentions, 1338 distinct
grep -hE '^#+ +DW-' … → 1437 entry headings (1238 at '###', 199 at '##')
```

| Shape | Count | Example |
|---|---|---|
| `DW-FU-<E>-<S>-<n>` | 665 | `DW-FU-21-8-4` |
| `DW-<E>-<S>-<n>` | 347 | `DW-3-12-2` |
| `DW-FU-<E>-<n>` | 185 | `DW-FU-28-19` |
| `DW-<WAVECODE>-<n>` | ~44 | `DW-B4-3`, `DW-A1-7` |
| `DW-<SLUG>-<YYYY-MM-DD>-<n>` | ~28 | `DW-RT-2026-09-02-5`, `DW-VOCAB-2026-09-14-7` |
| `DW-<SLUG>-<n>` | ~14 | `DW-CHAIN-COMPLETENESS-6` |
| bare `DW-<n>` | 10 | `DW-1` … `DW-10` |
| bare `DW-<CODE>` | 9 | `DW-D2`, `DW-H1` |
| `DW-<SLUG>-<YYYY-MM-DD>` | 2 | `DW-CANOPY-2026-08-24` |
| lowercase-slug tail | 4 | `DW-FU-marshal-land-cross-project-story-key-collision` |
| malformed | 6 | `DW-FU`, `DW-B4-`, `DW-B2-1..5` (a range), `DW-D2-3-stays-open` (prose) |

`665+185+347+141 = 1338` ✓. No parser reads all eleven. Bare `DW-1`…`DW-10` collide across
projects by construction — nothing in the shape records which ledger owns the number.

**This research's own sibling pass demonstrates the failure.** `DW-VOCAB-2026-09-14-1..7` is one
sequence split across two ledger files — steward holds 1,2,3,4,5,7 and marshal holds 6
(`grep -rln 'DW-VOCAB' */deferred-work-ledger.md` → 2). The id shape cannot express that.

Heading level also disagrees: steward 365 `###` / 1 `##`; marshal 396/53; atlas 160/60; herald
32/31; **warden inverted at 6 `###` / 43 `##`**.

---

## 5. Epic addressing — four forms, 1094 instances

```
## Epic <N>: <Title>            214   body section heading, all 8 projects
### Epic <N>: <Title>            52   table-of-contents entry, 6 of 8 projects
| **E<N>** | …                   57   herald + marshal ONLY — they have zero '###' TOC entries
epic-<N>:                       214   ledger rollup key
epic-<N>-retrospective:         214   ledger retro key
```

Prose uses `Epic N` 756× inside `epics.md` against 17 uses of `epic-N`.

---

## 6. Branch and commit shapes

**Branches** (`git branch -a` → 714 refs, 609 distinct; 331 after removing the two whole-refset
mirrors `mason-home/*` and `marshal-home/*`):

| Shape | Count |
|---|---|
| `<conventional-type>/<slug>` (`fix` 53, `docs` 24, `feat` 11, `chore` 6, `maintenance` 5) | **99** |
| `bmad-loop/<YYYYMMDD-HHMMSS-hhhh>/<E-S-slug>` | 59 |
| `dispatch/<pyforge-LONG>/<E.S>` | 36 |
| `attempt-preserve/<YYYYMMDD-HHMMSS-hhhh>-<hex8>` | 30 |
| `<station-SHORT>/<slug or E-S-slug>` | 22 |
| `worktree-agent-<hex17>` | 20 |
| `bmad/<slug>` | 16 |
| flat `<station-SHORT>-<E>-<S>-<slug>` | 16 |
| other flat kebab | 14 |
| `loop/<pyforge-LONG>` | 8 |
| `claude/<slug>-<rand6>` | 4 |
| one-off namespaces (`archive/ backup/ cap-verify/ fleet/ plan/ recipes/`) | 7 |

Story addressing inside branches is a **fourth spelling of § 2**, and it disagrees internally:
`dispatch/pyforge-doctor/21.4` (dotted, LONG station) vs
`bmad-loop/<run>/6-9-fix-pr-actuator` (hyphenated + slug) vs
`herald/20-10-warden-poster` (SHORT station, hyphenated) vs
`steward-44-12-cutover-harness` (SHORT station, no separator).

**Commit subjects** (`git log --oneline -200`, 200 subjects):

```
Merge pull request #N from …                      76   (+1 other merge)
<type>(<scope>): lowercase, no period             72
Capitalized imperative sentence.                  50
<E>.<S>: lowercase sentence.                       1   ("52.1: chrome may show mybmad …")
```

The two families punctuate in exactly opposite ways: **46 of 50** sentence-style subjects end in
a period; **0 of 72** prefixed subjects do. Within the prefixed family, 5 use a *station name* as
the conventional-commit type (`marshal:`, `mason:`, `herald:`, `doctor:`, `platform:`) and 16 of
72 capitalize the word after the colon.

---

## 7. Long vs short station form — no rule anywhere

| LONG `pyforge-<x>` | | SHORT `<x>` | |
|---|---|---|---|
| BMAD project dirs | 8 | Dream `owner:` frontmatter | 165/165 |
| package dirs | 10 (+9 `django-*`) | `bmad-agent-<x>` skills | 8 |
| pixi environments | 13 of 31 | code `STATIONS` rosters | 4 files |
| pixi tasks | 64 | doctor `Source` enum values | 35/35 |
| `dispatch/` + `loop/` branches | 44 | station-topic branches | 22 |
| skill dirs | 7 (mason absent, deliberate) | pixi tasks | 9 |
| docs prose | ~1104 | | |

`pyforge-scribe` is the env and the package, but `scribe-pg-up` is its task.
`dispatch/pyforge-doctor/21.4` and `doctor/…` name the same station in the same refspace.

**The four short rosters also disagree with each other** — three different member orders, and one
holds only 6 of 8:

```
pyforge-marshal/…/coverage_gate.py:39    STATIONS        8, alphabetical
pyforge-steward/…/five_tier.py:18        STATIONS        8, alphabetical
pyforge-herald/…/progress.py:61          STATIONS        8, warden-first
pyforge-marshal/…/mcp/coverage.py:30     DREAM_STATIONS  6  — no doctor, no scribe
```

---

## 8. The two epic-heading findings are raised, fixed and closed — in one uncommitted changeset

`DW-VOCAB-2026-09-14-5` (steward `epic-18` is a ledger row with no `## Epic 18` heading) and `-6`
(marshal `epic-29`, same defect) are **complete work**: raised, fixed, and closed. This sweep
cross-checked every epic key against every epic heading in all eight projects and found **zero
mismatches**:

```
per project: comm -23/-13 on (ledger epic-<N> keys) vs (## Epic <N> headings)
  atlas 24=24, doctor 22=22, herald 22=22, marshal 41=41,
  mason 17=17, scribe 18=18, steward 58=58, warden 12=12   — all empty both directions
```

The fixes are correct, not merely present. `## Epic 18` sits at steward `epics.md:1563` with
Stories 18.1/18.2/18.3 at 1567/1581/1592 and `## Epic 19` following at 1605; `## Epic 29` sits at
marshal `epics.md:4685` with Stories 29.1/29.2 at 4701/4721 and `## Epic 30` at 4742. No story is
orphaned or re-parented.

**But none of it is committed.** Every artifact in the chain — the DW entries themselves, the two
heading fixes, and the `status: closed` flags — was minted on 2026-09-14 and exists only in the
working tree:

```
git show HEAD:…/pyforge-steward/…/deferred-work-ledger.md | grep -c 'DW-VOCAB'  → 0
git show HEAD:…/pyforge-marshal/…/deferred-work-ledger.md | grep -c 'DW-VOCAB'  → 0
git show HEAD:…/pyforge-steward/…/epics.md | grep -cE '^## Epic 18'             → 0
grep -cE '^## Epic 18' …/pyforge-steward/…/epics.md                             → 1
git diff --cached … | grep '^[+-]## Epic 18'   → -### Epic 18 / +## Epic 18
```

**CORRECTION to this document's own first draft.** An earlier revision of this section asserted
that both ledger entries "still read as open". That was an inference from a truncated
`grep -A6`, which stopped at `severity:` and never reached the `status:` line — not a
measurement. Both read `status: closed`. Of the seven `DW-VOCAB-2026-09-14-*` entries, exactly
these two are closed and the other five (`-1`, `-2`, `-3`, `-4`, `-7`) are genuinely open. The
estate's own rule applies to this file as much as to any other: *your own prior claim is not
evidence*.

The real exposure is therefore not correctness but durability: **46 files staged on `main` and
uncommitted**, including this research, the Dream it feeds, and both closed findings. Discard the
index or reset the tree and all of it goes at once — the fixes, the ledger entries recording
them, and the record that the work was ever done. That is the only reason this section exists.

---

## 9. Remaining shape disagreements, stated plainly

1. **Frontmatter key casing is inverted between the two spec tiers.** Numbered story specs use
   **27 snake_case** distinct keys against **1 kebab** (`baseline_revision` 650,
   `followup_review_recommended` 700). Named `SPEC.md` files use **7 kebab** against **4 snake**
   (`owner-dream` 164, `surface-drift-exclude` 20 — but `open_questions` 139). Both conventions
   appear **in the same file**: every `SPEC.md` carries `owner-dream:` and `open_questions:`.
2. **Named specs: 164 are `spec-<slug>/SPEC.md`, 6 are flat `spec-<slug>.md`** (5 marshal,
   1 steward). Inverted for numbered specs: 855 flat files, **1 directory** —
   `pyforge-doctor/…/spec-19-1-the-suite-watched-set…/`, which is also the only spec directory in
   the estate with no `SPEC.md` inside.
3. **`spec:` frontmatter vs its own dir name.** 145 drop the `spec-` prefix, 1 keeps it
   (`spec-surface-overlap-tolerance`), **18 have no `spec:` key at all** — including 5 of the 8
   kernel specs.
4. **Dream `title:` vs filename — 0 of 165 agree in shape.** Filenames are 164/164 kebab; titles
   are 165/165 prose, splitting into 69 `Noun phrase — subtitle` and 96 full sentences, 4 of them
   starting lowercase. `status:` compounds it: **19 of 165** append a `# …` comment to the value
   on the same line, so a naive parse yields 40+ statuses instead of 5.
5. **Finding codes: stable vocabulary ⟷ runtime data.** 124/124 literal codes are kebab, but
   **6 call sites in `sources/atlas.py`** (lines 200, 240, 278, 317, 365, 403) pass a feedstock or
   package name into `check=`, so the field that elsewhere carries `spec-surface` can carry a
   package name or the literal `"<unknown feedstock>"` (`atlas.py:172`). Warden contributes three
   **colon-and-underscore** codes through `check=check.name` (`cfe:match_confidence`).
6. **Two date formats.** `YYYY-MM-DD` in every filename (54 research, 33 retros, 50
   change-history, 17 readiness reports, ~28 DW ids); compact `YYYYMMDD-HHMMSS-<hash>` in **89**
   branch names. One named spec carries a date at all
   (`spec-code-audit-remediation-2026-07-26.md`) — 1 of 170.
7. **Research filename infix is optional.** 37 of 57 carry `-research-`, 20 do not; 54 carry a
   trailing date, 3 do not. Type prefix is `technical` 23 / `domain` 16 / `market` 14, then four
   ad-hoc.
8. **Retro filenames: 33 dated `epic-<N>-retro-<date>.md` ⟷ 13 `epic-<N>-<wave-slug>.md`.** Both
   forms exist for atlas epics 1–6 simultaneously, so `epic-N-*` does not identify a retro.
9. **Pixi tasks: 276 of 278 kebab.** Breakers are `build-osx.env` (`pixi.toml:81`) and
   `build-win.env` (`pixi.toml:92`) — the only names containing `.`, which is also pixi's own
   table separator. Three names are defined under more than one feature (`atlas-phase`,
   `build-cf-atlas`, `detail-cf-atlas`).
10. **Four SCREAMING-CASE filenames** among ~130 kebab under `planning-artifacts/`: `PRD.md`,
    `DESIGN.md`, `EXPERIENCE.md`, `SPEC.md` — and `PRD.md` sits beside a lowercase `prds/`
    directory holding dated `prd-pyforge-<station>-<date>/` variants.
11. **Skill dir layout: 117 flat `SKILL.md` ⟷ 8 versioned `<ver>/` + `active` symlink** (all 7
    `pyforge-*` plus one). Three stray `.json` files sit in `.claude/skills/` as if they were
    skills.

---

## 10. What this research does NOT settle

- **No shape is proposed.** Which of three story spellings is canonical, whether `DW-` ids get one
  grammar, whether frontmatter keys go kebab or snake — all are operator decisions.
- **No migration is costed.** Renaming 1338 `DW-` ids or 952 ledger keys touches the detectors
  that read them; that cost was not measured.
- **Cross-station conventions were not distinguished from per-station ones.** Warden's inverted
  DW heading level and herald/marshal's epic table may be deliberate local choices; this pass
  measured that they differ, not whether they should.
- **Only `docs/` prose was sampled for long/short station form,** and the `the atlas` count (84)
  is inflated by non-station senses (the database, the pipeline). Treat § 7's prose row as
  indicative, not exact.
- **The tree was dirty.** See § 8. Every count above is a working-tree count at
  `445976e5be` + 36 modified/untracked paths.

## Sources

- This repo at `main` `445976e5be`, working tree as of 2026-09-14, measured with the commands
  shown inline above.
- `technical-vocabulary-three-source-reconciliation-2026-09-14.md` — the sibling pass this one
  extends; § 8 corrects two of its findings.
- `docs/dreams/vocabulary-one-name-one-job.md` — the Dream this feeds.
