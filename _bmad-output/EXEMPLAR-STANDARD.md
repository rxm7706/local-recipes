# The Dream-to-Code operating model

**Reference implementation: `projects/pyforge-atlas/planning-artifacts/`.**
Established 2026-07-27, extended to the full chain 2026-07-28. Applies to every BMAD
project in this repo under bmad-method ≥ 6.10 with bmad-loop.

---

## The invariants

Decided 2026-07-28 (operator). **Consistency first: one operating model, one ownership
model, one build tree — across every Dream-to-Code chain, with no per-artifact
exceptions.** These are not guidelines; a violation is a detector finding.

INV-0..INV-3 were the original three plus `owner-dream:`. **INV-4 and INV-5 were added
2026-08-08** and extend the same principle from the artifacts to the *instruments*: a
detector must itself be owned (INV-4) and must read one shared declaration of convention
rather than carry its own (INV-5). Both came from measurement, not theory — see each.

*Enforcement is stated per invariant and is not uniform.* INV-0..3 are enforced by
`dream-chain-check`; INV-4's ownership half is enforced by `spec-surface-check`, its §6 half
is not yet enforced (`pyforge-doctor` S-6.10); INV-5's canonical forms are partly enforced
by `forward-dependency-check`'s coverage classes, and its "detectors read the register" rule
is **not yet mechanically checked** — that is honest status, not an aspiration dressed as a
gate.

### INV-0 — Every Spec declares `owner-dream:`

Not decided — **discovered**, while validating the detector against pyforge-atlas. It is
listed first because INV-1 and INV-2 cannot be measured without it.

The first cut of `dream_chain_check.py` reported **21** Dreams without a Spec. The true
number is **11**. The other 10 had Specs that simply never declared the link, and an
eleventh (`spec-upstream-discovery`) had frontmatter that would not parse at all — its
`open_questions` list contained an unquoted `(legacy default: monthly):`, and the
detector's `except: return {}` turned that silently into "no Spec."

The lesson is the session's recurring one: **a detector's own bugs propagate outward as
confident, wrong numbers.** Validate a new detector against a chain you already know well
before trusting its backlog.

*Measured at adoption: 10 Specs missing the link; 1 unparseable (fixed 2026-07-28).*

### INV-1 — Every Dream has a Spec

All Dreams in `docs/dreams/*.md` get a Spec, **including `archived` and `pitched` ones**.
No status is exempt.

An archived Dream's Spec is not busywork: it records the contract that was abandoned and
why, so a future reader learns from the retirement instead of rediscovering the idea. A
pitched Dream's Spec is what makes the pitch reviewable.

*Measured at adoption: **11** of 31 Dreams have no Spec. Only one is `realized` —
`agent-tool-surface` (marshal), i.e. shipped work with no governing contract — and two are
`specified` (`pyforge-herald`, `team-memory`); the remaining 8 are dreamt/pitched/archived.
An earlier draft of this section claimed 21, and named `design-code-bridge` as a second
realized-without-a-Spec case. Both were wrong, from the INV-0 defect above.*

### INV-2 — Owning is becoming, at the planning tier

> **The station owns the chain.** A Dream may start anywhere, but it is assigned to a
> station at birth, and its whole Dream→Code chain — Spec, PRD, architecture, epics,
> stories — then lives in that station's project.
> — Charter § 5, as amended 2026-07-28

| Dream `owner:` | Chain lives in |
|---|---|
| a Smith (`marshal`, `mason`, `atlas`, …) | `projects/pyforge-<owner>/planning-artifacts/` |
| `guild` — the two constitutive Dreams only | `docs/governance/` (2026-08-02: `pyforge-genesis` dissolved — no Smith may own the Charter that constitutes the Smiths) |

**It does not rename the package.** This is the distinction the superseded Charter clause
missed. What ships is declared by a Spec's `surface:`, which does not move when the planning
tree does: `spec-deckcraft` filed under `pyforge-herald/` still builds `apps/deckcraft/**`,
not `pyforge-herald`. Three of the four projects the old clause worried about
(`unity-data-stack`, `wasm-analytics-stack`, `presenton-pixi-image`) declare no `pyforge-*`
surface at all. *Planning home* and *package identity* are independent axes; the old clause
forbade the first to protect the second, and only the second needed protecting.

**The constitutive Specs are not project-shaped.** The two Dreams that *precede* the Smiths —
`pyforge-charter` and `pyforge-genesis` — record the origin Dream, the Charter, the Lexicon,
and the Guild's membership. `owner: guild` is terminal for exactly these two; a third is an
unassigned Dream hiding behind a collective noun. Their Spec kernels live at
`docs/governance/spec-pyforge-charter/` and `docs/governance/spec-pyforge-genesis/` — not a
`_bmad-output/projects/<x>/planning-artifacts/` tree, since they own no product and no
Smith-shaped scaffolding (2026-08-02: the `pyforge-genesis` *project* dissolved for exactly
this reason — see below).

**Genesis's installer is not constitutive.** `genesis init` / `genesis adopt` — standing up
a repo with the pixi environment, bmad-method, bmad-loop, multi-project wiring, skill-forge
and the BMM/BMB/TEA modules — is buildable work owned by the **Marshal**, whose Charter
toolkit already lists every one of those components and whose cadence already opens with
`marshal init`. Constitutive records and the machine that installs them are different nouns.

**The placeholder is retired.** `local-recipes` — what this monorepo started as — is intake
only: somewhere a Dream can land before it has a station. Applying INV-2 moves all 8 of its
Specs out, leaving zero, and it is then removed. A Spec still sitting there is an
unassigned-ownership finding, not a settled location.

**Target: 8 projects (the 8 Smiths).** No ninth. The constitutive Specs live at
`docs/governance/`, deliberately outside the project roster — see the amendment below.

*Corrections on the record (2026-07-28).* Three earlier drafts of this section were wrong and
are superseded: (1) a split between "project scope" and "owner scope", which let a station
show clean while owning open findings; (2) `guild` as non-terminal intake plus a
"constitutive exemption" parking the Charter in the placeholder — two inventions that kept
the placeholder alive to hold one file; (3) a new `pyforge-guild` project, when the
constitutive home already existed and is named Genesis. Each was an exception invented to
make an inconvenient case come out tidy; the rule was sufficient every time.

*Measured at adoption: 10 chains to move, 5 projects dissolved.*

*Amendment (2026-08-02): `pyforge-genesis` itself dissolved.* The correction above rejected a
*new*, differently-named project (`pyforge-guild`) as an invented exception — that reasoning
holds. It did not anticipate the actual defect: `pyforge-genesis`, though correctly named and
correctly excluded from Smith ownership, was still *shaped like a Smith's project* — carrying
a `.bmad-config.toml`, an `epics.md`, a `test-architecture.md`, a PRD and architecture that
existed only to say "there is no product here." That scaffolding was real vestigial debt
(dead test fixtures, a fabricated bulk-commit-era `test-architecture.md`), not a second
naming mistake. The fix is not a new project; it is *no project* — the two Spec kernels move
to `docs/governance/`, a plain documentation directory with no `.bmad-config.toml` and no
Smith-shaped machinery to keep vestigially current. `pyforge.doctor.sources.fleet_scan` and
`scripts/dream_chain_check.py` both special-case this location for the two `owner: guild`
chains. The Dream files themselves (`docs/dreams/pyforge-genesis.md`,
`docs/dreams/pyforge-charter.md`) are unchanged; only their Spec kernels' physical home moved.
The rest of the old project is archived at `archive/_bmad-output/projects/pyforge-genesis/`,
never deleted.

*Further amendment (2026-08-08, found stale 2026-08-15 while auditing `docs/` for this repo's
own housekeeping): the two-kernel split above did not last either.* Commit `a3b5fefae8`
("charter: absorb pyforge-genesis; `owner: guild` closes at one Dream") went one step further
than this amendment anticipated: `spec-pyforge-genesis`'s capabilities were absorbed directly
into `spec-pyforge-charter` as CAP-5..CAP-8, and `docs/dreams/pyforge-genesis.md` itself was
folded into `docs/dreams/pyforge-charter.md` as "§ Satellite: The Seed" — **neither file exists
standalone any more.** `docs/governance/spec-pyforge-genesis/` was moved to
`archive/docs/governance/spec-pyforge-genesis/` (archived, not deleted, same convention as
everything else here). The constitutive tier is now genuinely **one Dream, one Spec kernel** —
`docs/dreams/pyforge-charter.md` / `docs/governance/spec-pyforge-charter/` — not two files at
one shared location as this section's 2026-08-02 text still describes above. Verified directly
2026-08-15: `docs/governance/` contains only `spec-pyforge-charter/` and `guild-roster.json`.

### INV-3 — One build tree, sharded

Every project's `planning-artifacts/` uses the 6.10 sharded shape — what `bmad-prd` and
`bmad-architecture` actually emit:

```
planning-artifacts/
├── specs/spec-<slug>/          SPEC.md + peer companions (+ .memlog.md)
├── prds/prd-<slug>-<date>/     prd.md, .memlog.md, addendum.md, review-*.md
├── architecture/architecture-<slug>-<date>/
│                               ARCHITECTURE-SPINE.md, .memlog.md, reviews/
├── epics.md
├── briefs/  research/  retros/
└── README.md
```

Flat `prd.md` / `architecture.md` is the output of `bmad-create-prd` /
`bmad-create-architecture` — deprecated wrappers slated for removal in v7 — and is
non-conformant.

*Measured at adoption: 9 of 14 projects sharded; 5 flat (local-recipes, pyforge-marshal,
pyforge-warden, pyforge-genesis, deckcraft); 2 with no `epics.md` at all
(unity-data-stack, wasm-analytics-stack).*

### INV-4 — Every detector has an owning station, and it is never the station it judges

Added 2026-08-08. The instruments that enforce this model must themselves be inside it —
the same argument INV-0..3 make about artifacts, applied to the checks.

**Two halves, both required:**

1. **Ownership is explicit.** Every detector resolves to exactly one owning station via a
   Spec's `surface:` globs. A detector no Spec claims is a finding, never a silent
   exemption.
2. **The owner is not the subject.** A detector whose subject is station X's artifact may
   not be owned by station X. Charter §6: *"the Doctor holds the verdict on the Marshal's
   conformance — the one station that would otherwise grade itself,"* and *"the Marshal may
   not weaken, re-threshold or disable a check that judges the Marshal."* The producing
   station keeps its **pre-write operational guards**; it loses only the authority to be
   the final word on itself. Two layers, not a transfer.

**Why this became an invariant.** Measured 2026-08-08: `scripts/spec_surface_allowlist.txt`
carried a blanket `scripts/**` exemption whose stated reason named 2 detectors. The
directory had grown to 12, and the glob silently absorbed **20 tracked files — 6 detectors
plus the registry itself** — with no finding emitted, because the checker reports a glob
matching *nothing* (`stale-allowlist`) but never one matching *too much*. Of the 13
detectors, **10 judge an artifact another station produces, and none belonged to Doctor.**
Marshal owns the ledger, the board, the Dream→Spec chain and the spec surface — and owned
the detectors grading all four.

**Enforcement, stated honestly.** Half is live: the blanket glob was split into per-file
entries on 2026-08-08, so a newly added unclaimed detector now produces `[ungoverned]`
(verified by mutation — a throwaway `scripts/zz_fake_detector.py` was flagged where the
glob had absorbed it). Half is **not yet enforced**: no check asserts owner ≠ subject. That
is `pyforge-doctor` Story 6.10's meta-test, behind Epic 6's re-home of the 10 judging
detectors — itself sequenced behind S-6.1, because `doctor check` is 7.04s against a
documented 5.0s budget and 10 new gathers land on it.

*The one deliberate exception, and why it is not a loophole:* `sources/warden.py` **does**
import warden, because it relays an instrument's self-report about its own environment.
That is a different act from judging an artifact. The exception is allowlisted with its
reason recorded, not assumed.

### INV-5 — One convention, and exactly one register of its exceptions

Added 2026-08-08, after the root cause of four separate defects turned out to be the same
thing: **detectors accommodating variant conventions privately instead of reading one
declaration.**

**The canonical conventions** (normative for all new work, every station, every artifact):

| Surface | Canonical form |
|---|---|
| Story heading | `### Story <epic>.<num>: Title` |
| Ledger / sprint key | `<epic>-<num>-<kebab-title>` |
| Board story id | `<epic>.<num>` |
| Epic heading | `## Epic <n>: Title` |
| `**Deps:**` | `S-<epic>.<num>` · `S-<epic>.*` · `<station>:S-<epic>.<num>` · `—` (see row 11) |

*Measured 2026-08-08 — the convention is already near-universal:* 7 of 8 stations are
**100% conformant** on headings and ledger keys (marshal 86, herald 47, mason 38, steward
33, warden 31, doctor 28, scribe 9 — all plain/numeric, zero alias). `pyforge-atlas` is the
single outlier.

**The rule:**

1. **All work uses the canonical form. No exceptions, no size-based carve-outs** (see below).
2. **Detectors never carry a private accommodation.** A detector that pattern-matches a
   station-specific shape inline is non-conformant *even when it works* — it is a second
   copy of a convention, free to drift from the first.
3. **A deviation is fixed in the DATA, not tolerated in the parser.** If normalizing the
   data is genuinely impossible, the exception is registered below with its reason — and the
   register is empty, which is the target state.

**The legacy register: EMPTY.**

It had exactly one entry for about an hour. Recording why it closed, because the reasoning
generalizes:

Atlas's alias heading (`### Story A1 (2.1):`) was coupled to its alias ledger key (`a1-…`),
and the first instinct was that the pair was irreducible — its completion signal for Epics
1–10 was a `story(A1)` commit subject across merged PRs #58–#105, so renaming the heading
would orphan the key and renaming the key would orphan the shipped record. A 2026-07-30
attempt had already failed and left a warning in `generate.py`: *"DO NOT fix this by teaching
the parser atlas's convention. Tried and reverted."*

**That warning is about the parser, and it was obeyed. The data was fixed instead.** Two
things made it safe, both checkable rather than argued: since 2026-07-30 the *tracked ledger*
is the completion signal — it exists precisely so doneness is not reconstructed from commit
subjects, which remain valid history but stop being load-bearing; and the alias→canonical map
is **derivable from atlas's own headings** (38 entries, never hand-typed). So on 2026-08-08
all four surfaces moved in lockstep — 38 headings, 32 tracked ledger keys, 64 Tier-3 feed
keys (`development_status` *and* `story_meta`), 32 story-spec filenames (`git mv`), 32 board
story ids — with 57 `done` before and 57 after.

**What the register's emptiness bought.** Four codebases had each grown a private
accommodation for that one station: `generate.py`'s refuse-to-overwrite guard,
`dashboard_drift_check`'s *"accepts either id form and stays agnostic"*,
`chain_completeness_check`'s alias-**or**-parenthetical matcher, and — added the same morning,
while fixing the third — an alias branch in `forward_dependency_check`. Three were deleted
outright, each verified by **byte-identical detector output** before and after.
`generate.py`'s guard stays, because it protects *every* project from a parse failure
blanking curated state; what left it is the atlas special case.

`ledger_regression_check` also gained a real capability rather than an exemption: a vanished
`done` key is excused only when the completion still exists in the same ledger, still
terminal, under a key with a byte-identical descriptive tail. A genuine loss has no surviving
twin, so it still fires — mutation-tested both ways.

**The disposition for any future deviation:** fix the data. Register nothing you have not
first tried to normalize.

### Why no size-based exemption

The tempting rule is "small artifacts skip the PRD/epics tier." It was considered and
**rejected**: it makes conformance a judgement call, judgement calls drift, and the drift
is invisible. A uniform model is mechanically checkable; a tasteful one is not.

Where a tier genuinely has nothing to say, it says so in one line. That is cheaper than
arguing about thresholds forever, and it keeps the detector honest.

---

## The Exemplar

**`pyforge-atlas` is the single exemplar for all 16 stages of the Dream-to-Code chain.**

**Full pipeline (16 stages — verified in generator.py and index.html):**
Dream · Deck · Spec · Rsch · Brief · PRD · UX · Arch · Context · Epics · Sprint · TEA · Gates · Code · Tested · Retro

**Stage definitions:**
- **Dream** — Raw human aspiration / starting point, documented in `docs/dreams/`
- **Deck** — Rendered presentation of the Dream (Herald renders via design system)
- **Spec** — Five-field BMAD spec: Problem/Goal/Scope/Success/Constraints
- **Rsch** — Research stage: domain, market, and technical research (runs `bmad-domain-research`, `bmad-market-research`, `bmad-technical-research`)
- **Brief** — Research findings summary and key insights synthesized from Rsch stage
- **PRD** — Product requirements document with features, success metrics, out-of-scope
- **UX** — User experience design (UI mockups, flows, component specs) — optional per surface
- **Arch** — Architecture and API specifications with implementation contracts
- **Context** — Project context, assumptions, and dependencies documentation
- **Epics** — Epic breakdown, epics-with-stories, acceptance criteria per story
- **Sprint** — Sprint planning with velocity estimates and story-to-epic mapping
- **TEA** — Test Architecture: test strategy, coverage targets, test-per-story specs
- **Gates** — Implementation readiness gates (spec-complete, architecture-final, tests-passing)
- **Code** — Source code implementation of stories and features
- **Tested** — **Code + Tests (per TEA) + PR + Merged + Retro** — full delivery cycle, execution complete
- **Retro** — Retrospective capturing lessons learned, feedback, and next improvements

**BMAD skill execution sequence (mapped to skills):**

| Stage | Skill | Input | Output | Notes |
|---|---|---|---|---|
| 1. Dream | — | Raw aspiration in `docs/dreams/` | Dream file exists | Pre-BMAD; human-authored |
| 2. Deck | Herald | Dream + spec (draft OK) | Deck HTML/PDF | Renders from Dream; runs in parallel with spec chain |
| 3. Spec | `bmad-spec` | Dream | `SPEC.md` (5-field contract) | Problem/Goal/Scope/Success/Constraints |
| 4. Rsch | `bmad-domain-research` + `bmad-market-research` + `bmad-technical-research` | Spec | Research artifacts in `planning-artifacts/research/` | Domain + market + technical research; outputs to `research/<topic>-research-<date>.md` |
| 5. Brief | `bmad-prd` | Spec + Research | `prd.md` research synthesis section | Research findings summary and key insights |
| 6. PRD | `bmad-prd` | Spec + Research + Brief | `prd.md` (full) | Features, success metrics, out-of-scope |
| 7. UX | Surface-specific design work | Spec + PRD | UI mockups, flows, component specs | **Optional** — skipped for non-UI/backend surfaces |
| 8. Arch | `bmad-architecture` | Spec + PRD | `ARCHITECTURE-SPINE.md` + contracts | API specs, deployment model, dependencies |
| 9. Context | `bmad-document-project` | Spec + PRD + Arch | Project context doc | Assumptions, platform context, dependencies |
| 10. Epics | `bmad-create-epics-and-stories` | Spec + PRD + Arch | `epics.md` + `epics-with-stories.md` | Epic definitions, story rollup |
| 11. Sprint | `bmad-create-story` (per epic) | Epics | Story specs + velocity mapping | Story-to-epic, effort estimates |
| 12. TEA | `bmad-create-story` or standalone | Spec + Epics | `test-architecture.md` + per-story test specs | Test strategy, coverage targets |
| 13. Gates | `bmad-check-implementation-readiness` | All upstream artifacts | Gate report (pass/fail) | Verify readiness before implementation |
| 14. Code | `bmad-dev-auto` / `bmad-loop` | Stories + TEA | Source code in repo | Implementation from story specs |
| 15. Tested | `bmad-loop` (delivery cycle) | Code + TEA | PR + Merged + Tests passing | Code + Tests per TEA + PR + Merged + Retro |
| 16. Retro | `bmad-retrospective` | Session logs + merged PRs | Retrospective + skill updates | Lessons learned + BMAD improvements |

**Parallelization notes:**
- **Deck** renders while **Spec** is being produced (can start from draft Spec)
- **Rsch** is gathered during **PRD** workshops/interviews (collected, not a separate phase)
- **Context** is typically derived from the Spec/PRD/Arch chain rather than standalone work
- **UX** runs parallel to **Arch** for user-facing surfaces; omitted entirely for backend/infrastructure work

**What an exemplar is:**
- The most complete and mature project in the portfolio
- The working tree reference when documentation and code diverge
- The source of truth for layout, conventions, and completeness standards

**Selection criteria — verified facts:**
- **Atlas:** 14/16 stages complete (missing: tea-new, ux-n/a) ✅ EXEMPLAR
  - All research disciplines present (3/3: domain, market, technical)
  - Final retro delivered (2026-07-25)
  - Sharded planning structure with dated folders
  - Highest conformance in portfolio
  
- **Warden:** 13/16 stages complete (missing: retro-no, tea-new, ux-n/a)
  - Research incomplete (2/3: domain, market; missing technical)
  - No retro delivered yet
  - Sharded planning structure (matches atlas pattern)

- **Others:** Varying stages of completion (converging toward atlas's pattern)

**Why atlas is the exemplar:** It has the most complete chain — specifically, retro is shipped (a terminal stage), all research disciplines are present, and the planning structure matches the v6.10 standard that all projects are adopting.

## Planning-artifacts detail

This document is the conformance target. When it and pyforge-atlas disagree,
**pyforge-atlas is right and this document is stale** — the exemplar is a working tree,
not a specification of one.

---

## Why a standard

Fourteen projects live under `_bmad-output/projects/`, built across three different BMAD
eras. They diverged in shape, not just content: some carry a flat `prd.md`, some a dated
`prds/<run>/` folder; some have story specs, some have stubs; one has a deferred-work
ledger and the rest do not. Divergence is fine while a project is in flight and expensive
once you need to answer "is this project's record complete?" across all of them.

The standard exists so that question has a mechanical answer.

## The conformance table

| # | Requirement | Why it is load-bearing |
|---|---|---|
| **1** | PRD lives in `prds/prd-<slug>-<date>/` with `prd.md`, `.memlog.md`, and any `addendum.md` / `review-*.md` / `validation-report.*` | This is what `bmad-prd` binds (`{prd_output_path}/{run_folder_pattern}/`). A flat `prd.md` is pre-6.10 `bmad-create-prd` output — a deprecated wrapper slated for removal in v7. |
| **2** | Architecture lives in `architecture/architecture-<slug>-<date>/ARCHITECTURE-SPINE.md` with its `.memlog.md` and `reviews/` | Same reason: `bmad-architecture` binds a spine run folder. A flat `architecture.md` predates the spine concept. |
| **3** | Core docs carry `status` / `created` / `updated` frontmatter | `stepsCompleted:` alone records *which workflow steps ran*, not whether the document is final. Only the former survives a reader who wasn't there. |
| **4** | A Spec kernel exists at `specs/spec-<slug>/SPEC.md` | The Spec is the unit of contract. The planning chain decomposes it; it does not replace it. |
| **5** | Companions are **peer contracts** in the kernel directory; `companions:` frontmatter lists only those; the chain (PRD / spine / epics) lives in `sources:` | Two different relationships. Conflating them makes "what is normative?" unanswerable. |
| **6** | Every kernel Constraint that compresses an enumeration cross-references its companion inline | A companion nobody is pointed to is documentation, not contract. |
| **7** | Per-story specs are tracked in `specs/`, never left in gitignored `implementation-artifacts/` | In a spec-driven build the spec *is* the contract. Tier-3 specs die on worktree teardown — this has already cost this repo real artifacts twice. |
| **8** | Every story has a delivery record — in its spec and in `epics.md` | Otherwise the planning chain reads as pre-implementation forever, no matter what shipped. |
| **9** | The deferred-work ledger is tracked in `planning-artifacts/` | The bmad-loop ledger is Tier-3 and gets truncated. If it matters after the run, it belongs in Tier-2. |
| **10** | `planning-artifacts/README.md` explains the layout and any deliberate asymmetry | The next reader is an agent with no session context. |
| **11** | A story's `**Deps:**` field is **machine-readable**: `S-<epic>.<num>` (story) · `S-<epic>.*` (whole epic) · `<station>:S-<epic>.<num>` (cross-station) · `—` (none). Prose is allowed only as *trailing context* after the refs, never as the whole declaration. | A dependency the harness cannot parse is a dependency it dispatches into. `bmad-loop`'s picker has no `depends_on` concept, so `epics.md` is the only place a dependency is stated — and until 2026-08-08 two stations stated theirs in prose. **Mason reported measured-and-clean with 0 of 30 declarations parseable**; atlas had 5 of 43. Enforced by `forward-dependency-check`'s coverage classes (`PARTIAL` names the ratio); it reports today and gates once the 59-declaration migration lands. |

## The kernel/companion rule

> If a normative claim in the kernel cannot be reviewed or refuted without an enumeration,
> that enumeration is a **companion** — a contract, not documentation.

Worked examples from the exemplar:

| Kernel claim | Without the table | Companion |
|---|---|---|
| "TTLs are declared per dataset, never a global constant" | unverifiable | `catalog-contract.md` |
| "Gates are never weakened, and the verify set only grows" | unenforceable against an unenumerated set | `gate-contract.md` |
| "The legacy phases survive the port with their contracts intact" | names no contract | `signals.md` |
| "Three markers, never interchanged" | three words that look like synonyms | `degradation-contract.md` |

The pattern originates in `pyforge-warden` (`verdict-contract.md` / `axes.md` /
`extraction-contract.md`); pyforge-atlas is where it was generalized.

**Companions hold tables; the kernel holds the compressed normative sentence.** A companion
that argues rather than enumerates has drifted into being a second kernel.

## Provenance rules

These are the ones most likely to be violated with good intentions.

1. **Never fabricate a session record.** A `Dev Agent Record` or `Review Triage Log` describes
   something that happened. If the session never emitted one, say so and supply a
   `## Delivery Record` derived from durable evidence (PR body, merge date, commit list, exact
   file list from the diff) — labeled as derived.
2. **Recovered originals are not normalized.** If a spec was recovered verbatim, it keeps its
   original shape and its `<!-- RECOVERED … -->` banner even when siblings look different.
   Uniformity is worth less than provenance. Document the asymmetry instead of erasing it.
3. **Derive counts; do not restate them.** Every number in a companion should be reproducible
   from the code or the API. The exemplar's "86 datasets / 7 pipelines / 7 gates" came from
   `catalog.yml` and `pixi.toml`, and the kernel's own "six gates" prose was found wrong
   against it.
4. **Corrections stay on the record.** When a claim is found wrong, correct it *and* say what
   it used to say and why it was wrong. The exemplar's ledger and SPEC both carry dated
   corrections rather than silent edits.

## Conformance status

> **Conformance is measured by OWNER, and that is the only scope.** A station is answerable
> for every Dream carrying its `owner:`, wherever those artifacts happen to sit on disk.
> Directory layout is a filing decision; it is not an accountability boundary.
>
> An earlier draft of this document split "project scope" from "owner scope" and reported
> `pyforge-atlas` as **0 findings**. That was rejected 2026-07-28: it is a true statement
> that produces a false impression, and it opens a loophole — a station can park its debt in
> satellite projects and still show a clean table. It is the same shape as `status: shipped`
> meaning "32 stories merged" while three attended events sat undischarged. **The station's
> number is the sum of its Dreams.**
>
> So: **atlas carries 5 findings** — `microsoft-org-sweep` (archived, no Spec), and
> `unity-data-stack` / `wasm-analytics-stack` (no `owner-dream:` link, no `epics.md`).
> Atlas is the exemplar **for the build tree** — the shape of `pyforge-atlas/planning-artifacts/`
> is what every project migrates toward. It is *not* a clean station, and the table below is
> about the tree, not a conformance score.
>
> Nor was it clean when the invariants arrived: `spec-upstream-discovery/SPEC.md` had
> frontmatter that would not parse (fixed 2026-07-28). An exemplar that survives its own new
> detector unchanged usually means the detector is too weak.

| Project | 6.10 shape | Spec kernel | Companions | Story specs | Delivery records | DW ledger | README |
|---|---|---|---|---|---|---|---|
| **pyforge-atlas** | ✅ | ✅ | ✅ 4 | ✅ 32 | ✅ 32/32 | ✅ 52 | ✅ |
| pyforge-warden | ❌ flat | ✅ | ✅ 3 | ✅ 31 | ❌ | ❌ | ❌ |
| pyforge-doctor / mason / herald / scribe / steward | ✅ | ✅ | ❌ | partial | ❌ | ❌ | mostly ✅ |
| pyforge-marshal | ❌ flat | ✅ | ❌ | partial | ❌ | ❌ | partial |

*(`deckcraft`, `presenton-pixi-image`, `unity-data-stack`, `wasm-analytics-stack` and
`local-recipes` are omitted — all five dissolve under INV-2; their chains move to the owning
Smith. `pyforge-genesis` is also omitted, but dissolved differently (2026-08-02): no Smith
absorbed it — its two Spec kernels moved to `docs/governance/`, outside the project roster
this table measures. Not a conformance row candidate; it never had epics/stories to score.)*

Warden is the cheapest to finish: reshard `prd.md` → `prds/prd-pyforge-warden-<date>/`,
regenerate `architecture.md` as an `ARCHITECTURE-SPINE.md` run folder, and back-fill delivery
records from PR #110. Its companion pattern and story-spec fidelity already exceed the bar.

Marshal is the largest debt — 11 findings, a flat tree, four Specs to author (one for
`agent-tool-surface`, which is `realized` with **no contract at all**), and the Genesis
installer to absorb. It also owns the console and the loop that every other station depends
on, so its conformance is load-bearing rather than cosmetic.

**The table above is dated 2026-07-28/08-08 and is now stale — kept verbatim above per this
document's own Provenance rule 4 (corrections stay on the record), superseded by the refresh
below.** Found stale while writing `docs/dreams/fleet-hygiene-verification-exemplar-program.md`
(2026-08-15): its "DW ledger" column reads ❌ for every project but atlas, when in fact all 8
now carry a real, tracked `deferred-work-ledger.md` — the two-pass promotion this session ran
against exactly the blind spots that Dream documents (a pre-convention Tier-3 format, and a
`#`-header-swallows-body content-diff miss).

### Conformance status — 2026-08-15 refresh

`scripts/dream_chain_check.py`, the detector this document names as authoritative, was
retired 2026-08-10 (`c698d4b1ad`, "doctor: retire 8 scripts/ shims fully superseded by Doctor
sources") — its INV-0..1 half now lives at `python -m pyforge.doctor.sources dream-chain`.
That subcommand only covers Spec-linkage (INV-0/INV-1), not the 7-column table below — the
2026-07-28 table's other columns were themselves hand-derived via spot checks, not a single
tool, and this refresh follows the same method, stated per column so a future pass can judge
what to trust vs. re-verify:

| Project | 6.10 shape | Spec kernels | Story specs | Companions (spot count) | Delivery records (spot grep) | DW ledger | README | epics.md |
|---|---|---|---|---|---|---|---|---|
| pyforge-atlas | ✅ sharded | 8 | 47 | 9 | 32/47 | ✅ 122 | ✅ | ✅ |
| pyforge-doctor | ✅ sharded | 4 | 28 | 0 | 5/28 | ✅ 20 | ✅ | ✅ |
| pyforge-herald | ✅ sharded | 4 | 48 | 6 | 0/48 | ✅ 45 | ✅ | ✅ |
| pyforge-marshal | ✅ sharded | 36 | 56 | 14 | 0/56 | ✅ 109 | ✅ | ✅ |
| pyforge-mason | ✅ sharded | 8 | 10 | 1 | 0/10 | ✅ 48 | ✅ | ✅ |
| pyforge-scribe | ✅ sharded | 4 | 9 | 0 | 2/9 | ✅ 7 | ✅ | ✅ |
| pyforge-steward | ✅ sharded | 9 | 20 | 1 | 0/20 | ✅ 74 | ✅ | ✅ |
| pyforge-warden | ✅ sharded | 2 | 31 | 3 | 0/31 | ✅ 43 | ✅ | ✅ |

Method and honest caveats:
- **6.10 shape / spec kernels / story specs / companions / README / epics.md**: mechanical
  `find`/`ls` counts against each project's `planning-artifacts/` tree, run 2026-08-15. The
  flat-vs-sharded gap that made warden and marshal ❌ in the 2026-07-28 table is fully closed
  — every project now has `specs/`, `prds/`, and `architecture/` in the sharded shape.
- **Delivery records**: `grep -l "^## Delivery Record\|^## Dev Agent Record"` across each
  project's story specs — a **spot check, not exhaustive**. Only atlas (32/47) and doctor
  (5/28) and scribe (2/9) show non-zero hits; every other project shows 0, which is
  suspicious enough to be a false negative from heading-convention drift (some projects may
  use a differently-worded section heading) rather than a true "zero stations record
  delivery" finding — **do not treat the 0s as confirmed debt without re-checking headings
  directly**, the same caution this document's own INV-0 section demonstrates about trusting
  a first-cut detector's confident wrong number.
- **DW ledger**: verified directly, not a spot check — every count above is the same number
  this session's own `deferred-work-check` detector and duplicate/collision scan confirmed
  clean (see `docs/dreams/deferred-work-audit-completeness.md` and
  `docs/dreams/deferred-work-resolution-sweep.md`).
- **Not re-measured this pass**: INV-2 station-ownership migration progress (dissolution of
  `deckcraft`/`presenton-pixi-image`/`unity-data-stack`/`wasm-analytics-stack`/
  `local-recipes`), INV-4/INV-5 enforcement status, and the Dream-count growth itself — the
  fleet now carries **96 Dreams** (up from 31 at 2026-07-28), of which **16 have no Spec**
  (`python -m pyforge.doctor.sources dream-chain`, 2026-08-15: 5 owned by steward, 3 each by
  doctor/mason, 2 by herald, 1 each by marshal/atlas/warden) — a real INV-1 backlog nearly
  50% larger in absolute count than the 11 the 2026-07-28 table reported, though smaller as a
  fraction of a much bigger Dream corpus. Worth a dedicated pass, not folded into this one.

**Reading this refresh:** the sharpest gap the old table named — flat trees on warden/marshal
— is closed. The sharpest gap this refresh finds instead is delivery-record convention drift
(real or a heading-detection artifact, undetermined) and the growing INV-1 backlog keeping
pace with — arguably outpacing — the fleet's own Dream production rate. Both are better next
targets than re-chasing the DW-ledger or 6.10-shape columns, which this pass shows are now
solid.

**The table above is dated 2026-08-15 and is now stale — kept verbatim above per this
document's own Provenance rule 4 (corrections stay on the record), superseded by the refresh
below.**

### Conformance status — 2026-08-21 refresh

Same 8-column mechanical count as the 2026-08-15 pass, re-run today against the live
`_bmad-output/projects/*/planning-artifacts/` trees (still the same 8 projects — no project
was added, removed, or renamed since 08-15), with one methodology fix: the delivery-records
grep now unions in a third pattern, `## Auto Run Result` — `bmad-dev-auto`'s own HALT-protocol
section name — alongside `Delivery Record` and `Dev Agent Record`. That third pattern answers
the 08-15 section's own stated caveat ("do not treat the 0s as confirmed debt without
re-checking headings directly"): all five of that table's 0/N rows — herald, marshal, mason,
steward, and warden — were a heading-convention false negative, not a real "zero stations
record delivery" finding.

| Project | 6.10 shape | Spec kernels | Story specs | Companions (exhaustive count) | Delivery records (exhaustive grep, heading-level) | DW ledger | README | epics.md |
|---|---|---|---|---|---|---|---|---|
| pyforge-atlas | ✅ sharded | 8 | 48 | 9 | 43/48 | ✅ 138 | ✅ | ✅ |
| pyforge-doctor | ✅ sharded | 8 | 36 | 3 | 23/36 | ✅ 29 | ✅ | ✅ |
| pyforge-herald | ✅ sharded | 4 | 48 | 6 | 5/48 | ✅ 58 | ✅ | ✅ |
| pyforge-marshal | ✅ sharded | 38 | 58 | 14 | 28/58 | ✅ 169 | ✅ | ✅ |
| pyforge-mason | ✅ sharded | 8 | 11 | 3 | 9/11 | ✅ 54 | ✅ | ✅ |
| pyforge-scribe | ✅ sharded | 4 | 9 | 0 | 3/9 | ✅ 7 | ✅ | ✅ |
| pyforge-steward | ✅ sharded | 9 | 20 | 1 | 4/20 | ✅ 124 | ✅ | ✅ |
| pyforge-warden | ✅ sharded | 2 | 31 | 3 | 16/31 | ✅ 46 | ✅ | ✅ |

Every column above is reproduced by one of these commands, per project (`<pa>` =
`_bmad-output/projects/<slug>/planning-artifacts`):

```bash
test -d <pa>/prds && test -d <pa>/architecture && test -d <pa>/specs            # 6.10 shape
find <pa>/specs -maxdepth 2 -iname SPEC.md | wc -l                              # spec kernels
find <pa>/specs -maxdepth 1 -iname 'spec-*.md' | wc -l                          # story specs
find <pa>/specs -mindepth 2 -maxdepth 2 -type f \
  ! -iname SPEC.md ! -iname .memlog.md | wc -l                                  # companions
grep -rlE '^## (Delivery Record|Dev Agent Record|Auto Run Result)' \
  <pa>/specs --include='spec-*.md' | wc -l                                      # delivery records
grep -ohE '\bDW-[A-Za-z0-9][A-Za-z0-9-]*' <pa>/deferred-work-ledger.md \
  | sed 's/-$//' | sort -u | wc -l                                              # DW ledger
test -f <pa>/README.md                                                          # README
test -f <pa>/epics.md                                                           # epics.md
```

Method and honest caveats:
- **6.10 shape / spec kernels / story specs / companions / README / epics.md**: the commands
  above, run 2026-08-21 — each is an exhaustive walk of the project's tree, not a sample,
  despite the "spot count" wording the 08-15 table used for the same columns. All eight remain
  fully sharded. Every count moved: story specs (atlas 47→48, doctor 28→36, marshal 56→58,
  mason 10→11; herald/scribe/steward/warden unchanged), spec kernels (doctor 4→8, marshal
  36→38, others unchanged), and companions (doctor 0→3, mason 1→3, others unchanged) — six
  days of organic growth, not a methodology change.
- **Delivery records — the 08-15 false negative is resolved; verification scope stated
  honestly**: re-running the *old* two-pattern grep (`Delivery Record`/`Dev Agent Record` only)
  today, in isolation, reproduces the 08-15 numbers exactly for every project (atlas 32, doctor
  5, scribe 2, and 0 for herald/marshal/mason/steward/warden) — the old pattern's zero rows
  stayed zero even where story-spec counts grew, consistent with (though not itself proof of)
  every new story using a different heading. Adding the third pattern lifts every project's
  count: atlas +11 (32→43), doctor +18 (5→23), herald +5 (0→5), marshal +28 (0→28), mason +9
  (0→9), scribe +1 (2→3), steward +4 (0→4), warden +16 (0→16). Content-verified for two of the
  eight — herald and marshal, opened file-by-file for this refresh — where every newly-matched
  file does carry `## Auto Run Result` and nothing else; the remaining six projects' matches
  rest on the heading-level grep only, not a per-file read. The false negative on the *zero*
  rows is resolved, but coverage is still well below the story-spec total for several projects
  (herald 5/48, marshal 28/58, mason 9/11, scribe 3/9, steward 4/20) — that gap is not claimed
  to be fully explained here; it plausibly includes in-progress stories with no delivery
  section yet, and possibly a fourth convention this pass did not check for.
- **DW ledger — no first-time fix needed this pass**: the 08-15 refresh already corrected the
  07-28 table's stale all-❌ column; this pass's numbers are six more days of ledger growth on
  the same counting method (unchanged since 08-15): atlas 122→138, doctor 20→29, herald
  45→58, marshal 109→169, mason 48→54, scribe 7→7 (flat), steward 74→124, warden 43→46. Caveat
  inherited from the method's own shape, not new to this pass: the count is distinct `DW-*`
  tokens found anywhere in the file — including an id one entry cites in another's `evidence:`
  prose (e.g. "supersedes DW-X") — the same file-wide harvest `pyforge.doctor.sources.chain`
  uses when minting new ids, so it stays consistent with the fleet's own tooling, but it means
  the number is "distinct ids mentioned," not strictly "open items."
- **Not re-measured this pass**: INV-2 station-ownership migration progress, INV-4/INV-5
  enforcement status, and the Dream-count/dream-chain gap — the 08-15 section's figures and
  caveats on these stand un-superseded; this refresh covers only the same 8 columns the 08-15
  pass covered and adds no new information about them.

## Verifying conformance

**`scripts/dream_chain_check.py` was retired 2026-08-10** (`c698d4b1ad`, superseded by Doctor
sources per the same pattern `bmad_drift_check.py` followed for its own verdict — CLAUDE.md
§ "Keeping BMAD artifacts in sync"). Its INV-0/INV-1 half (Spec linkage) now lives at
`python -m pyforge.doctor.sources dream-chain`; INV-2/INV-3 (station ownership, build-tree
shape) are **not yet ported** — the 2026-08-15 and 2026-08-21 refresh tables above measured
those columns by hand-run `find`/`grep`, the same un-mechanized method the original 2026-07-28
table used before this detector existed. Its findings **are** the migration backlog for INV-0/1 —
derived, never hand-listed — but the rest of the table is still exactly the kind of
hand-derived snapshot this document warns goes stale the moment it's written, until INV-2/3
land in `pyforge.doctor.sources` too.

```bash
pixi run -e local-recipes python -m pyforge.doctor.sources dream-chain            # INV-0/1 report
pixi run -e local-recipes python -m pyforge.doctor.sources dream-chain --json     # machine-readable
```

`scripts/bmad_drift_check.py` remains the `local-recipes`-scoped detector and owns the
`dream-unowned` check (`GUILD_DREAMS` = the two constitutive Dreams).

**Validate a new detector against a chain you already know.** The first cut of
`dream_chain_check.py` reported 21 Dreams without a Spec; the true number was 11. Ten Specs
existed but declared no link, and one had frontmatter that would not parse — which
`except: return {}` turned silently into "missing." A detector's own bugs propagate outward
as confident, wrong numbers, and this document repeated them until the exemplar was used as
the test case.

The mechanical spot-checks used alongside it:

```bash
# companions all exist and are all cross-referenced from the kernel
python3 - <<'PY'
import yaml, re, pathlib
p = pathlib.Path('specs/spec-<slug>')
t = (p / 'SPEC.md').read_text()
fm = yaml.safe_load(t.split('---')[1])
body = t.split('---', 2)[2]
refs = set(re.findall(r'`([a-z-]+\.md)`', body))
for c in fm['companions']:
    print(('OK  ' if (p / c).exists() else 'MISS'), c, '| referenced' if c in refs else '| NOT REFERENCED')
PY

# every story has exactly one contract, and no spec carries a sibling's
grep -c '^### Story ' specs/spec-*.md

# nothing Tier-3 became tracked
git status --porcelain | grep implementation-artifacts

# the switch is not desynced before any write-skill runs
scripts/bmad-switch --current && readlink -f _bmad-output/planning-artifacts
```
