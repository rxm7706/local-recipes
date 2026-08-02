# The Dream-to-Code operating model

**Reference implementation: `projects/pyforge-atlas/planning-artifacts/`.**
Established 2026-07-27, extended to the full chain 2026-07-28. Applies to every BMAD
project in this repo under bmad-method ≥ 6.10 with bmad-loop.

---

## The three invariants

Decided 2026-07-28 (operator). **Consistency first: one operating model, one ownership
model, one build tree — across every Dream-to-Code chain, with no per-artifact
exceptions.** These are not guidelines; a violation is a detector finding.

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
| `guild` — the two constitutive Dreams only | `projects/pyforge-genesis/planning-artifacts/` |

**It does not rename the package.** This is the distinction the superseded Charter clause
missed. What ships is declared by a Spec's `surface:`, which does not move when the planning
tree does: `spec-deckcraft` filed under `pyforge-herald/` still builds `apps/deckcraft/**`,
not `pyforge-herald`. Three of the four projects the old clause worried about
(`unity-data-stack`, `wasm-analytics-stack`, `presenton-pixi-image`) declare no `pyforge-*`
surface at all. *Planning home* and *package identity* are independent axes; the old clause
forbade the first to protect the second, and only the second needed protecting.

**`pyforge-genesis` is the constitutive project** — the one not named for a Smith, because
the two Dreams it holds *precede* the Smiths: `pyforge-charter` and `pyforge-genesis`
itself. It records the origin Dream, the Charter, the Lexicon, and the Guild's membership.
`owner: guild` is terminal for exactly these two; a third is an unassigned Dream hiding
behind a collective noun.

**Genesis's installer is not constitutive.** `genesis init` / `genesis adopt` — standing up
a repo with the pixi environment, bmad-method, bmad-loop, multi-project wiring, skill-forge
and the BMM/BMB/TEA modules — is buildable work owned by the **Marshal**, whose Charter
toolkit already lists every one of those components and whose cadence already opens with
`marshal init`. Constitutive records and the machine that installs them are different nouns.

**The placeholder is retired.** `local-recipes` — what this monorepo started as — is intake
only: somewhere a Dream can land before it has a station. Applying INV-2 moves all 8 of its
Specs out, leaving zero, and it is then removed. A Spec still sitting there is an
unassigned-ownership finding, not a settled location.

**Target: 9 projects — 8 Smiths + `pyforge-genesis`.**

*Corrections on the record (2026-07-28).* Three earlier drafts of this section were wrong and
are superseded: (1) a split between "project scope" and "owner scope", which let a station
show clean while owning open findings; (2) `guild` as non-terminal intake plus a
"constitutive exemption" parking the Charter in the placeholder — two inventions that kept
the placeholder alive to hold one file; (3) a new `pyforge-guild` project, when the
constitutive home already existed and is named Genesis. Each was an exception invented to
make an inconvenient case come out tidy; the rule was sufficient every time.

*Measured at adoption: 10 chains to move, 5 projects dissolved.*

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
| pyforge-marshal / genesis | ❌ flat | ✅ | ❌ | partial | ❌ | ❌ | partial |

*(`deckcraft`, `presenton-pixi-image`, `unity-data-stack`, `wasm-analytics-stack` and
`local-recipes` are omitted — all five dissolve under INV-2; their chains move to the owning
Smith.)*

Warden is the cheapest to finish: reshard `prd.md` → `prds/prd-pyforge-warden-<date>/`,
regenerate `architecture.md` as an `ARCHITECTURE-SPINE.md` run folder, and back-fill delivery
records from PR #110. Its companion pattern and story-spec fidelity already exceed the bar.

Marshal is the largest debt — 11 findings, a flat tree, four Specs to author (one for
`agent-tool-surface`, which is `realized` with **no contract at all**), and the Genesis
installer to absorb. It also owns the console and the loop that every other station depends
on, so its conformance is load-bearing rather than cosmetic.

## Verifying conformance

**`scripts/dream_chain_check.py` is the detector.** It enforces INV-0…INV-3 across every
Dream and project, rolls findings up **by owner** (the accountability unit), and exits
non-zero so it gates CI. Its findings **are** the migration backlog — derived, never
hand-listed in this document, because a hand-listed backlog is stale the moment it is
written.

```bash
pixi run -e local-recipes python scripts/dream_chain_check.py            # report + scoreboard
pixi run -e local-recipes python scripts/dream_chain_check.py --json     # machine-readable
pixi run -e local-recipes python scripts/dream_chain_check.py --inv INV-2
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
