---
spec: vocabulary-one-name-one-job
status: draft   # 2026-09-14 — seeded so the Dream's chain link is durable (dream-chain INV-1).
                # Eleven open questions are unanswered and every one of them is an operator
                # decision about constitutional vocabulary, so nothing downstream may bind to
                # this yet. Per docs/dreams/README.md:71-78 a `draft` Spec establishes the CHAIN,
                # not the CONTRACT — the owning Dream therefore stays `dreamt`, exactly as
                # spec-intelligence-hub did on 2026-09-05. Flip to `ready` only when the
                # questions below are answered and the shapes are chosen.
created: "2026-09-14"
updated: "2026-09-14"
owner-dream: docs/dreams/vocabulary-one-name-one-job.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/vocabulary-one-name-one-job.md
  - ../research/technical-vocabulary-three-source-reconciliation-2026-09-14.md
open_questions:
  - spec-ladder-declared-or-reduced
  - in-progress-survives-on-specs
  - where-the-spec-ladder-lives
  - recommended-not-required-pattern
  - bmad-lexicon-cross-walk-in-charter
  - pitched-retire-or-use
  - one-declared-vocabulary-source
  - design-practice-vocabulary-joins-or-not
  - track-collision-resolution
  - design-repo-drift-prevention
  - who-owns-retiring-stale-teaching
---

> **Seed Spec — the chain, not the contract.** Derived 2026-09-14 from
> `docs/dreams/vocabulary-one-name-one-job.md` and the measured three-source research pass. It
> exists so `dream-chain` INV-1 has a durable link and so the corrections found during research
> are recorded where downstream can see them. **Every capability below is a candidate. Nothing is
> chosen.** `bmad-spec` re-derives this into a real contract once the open questions are answered.

# SPEC — One name, one job

## Why

PyForge speaks three vocabularies at once — BMAD-METHOD's upstream terms, our own Lexicon and the
artifact statuses derived from it, and the Intelligence Hub / Frame vocabulary adopted
2026-09-13 — plus a fourth, taught only in the Design tier. They had never been compared in one
pass until 2026-09-14. The comparison found the Lexicon's own rule — *every noun does exactly one
job; every job has exactly one noun* — holding inside the seven Lexicon nouns and nowhere else:
four status vocabularies of which one is declared, a word meaning three different things
(`in-progress`), one job with four names (`done`/`shipped`/`realized`/`review`), and our
most-used Spec status being upstream's canonical **illegal** value (`shipped`, 67 live Specs,
reset to `backlog` by upstream's own test).

It also found three errors in our own records, including one in a Tier-0 constitutional document.
Those are stated below as corrections, not capabilities, because they are true regardless of what
this Spec eventually decides.

## Corrections established by research (independent of any decision here)

- **C-1 — the Hub has SIX shared abstractions, not seven.** `docs/dreams/pyforge-charter.md:606`,
  `spec-intelligence-hub/SPEC.md:48,68` and `vocabulary-map.md` all fold Organizational Memory
  into the six. Upstream tiers it as Layer-1 infrastructure. The Charter's *substantive* rulings
  (cross-walk never joins; Cogs/Smith collision; Charter·Guild·Stations have no Hub counterpart)
  are unaffected — only the enumeration. **Fixing this is a Charter amendment with a
  Realization-log entry, never an edit.**
- **C-2 — Guard category order.** The seven are right; the order is not. Whitepaper §5.5:
  1 Algorithmic · 2 **Source-Grounding** · 3 Consensus · 4 Expert · 5 Policy & Safety ·
  6 Regression & Drift · 7 Outcome. We recorded Source-Grounding sixth. The substantive B7
  finding stands; "Source-Grounding goes first" turns out to be upstream's own ranking.
- **C-3 — `extension-point` is not a category error.** It is a documented parked-Spec state, the
  Spec-side sibling of `dreamt` (`docs/dreams/README.md:80-88`). An assessment made earlier on
  2026-09-14 called it a category error; that assessment was wrong.

## Capabilities — all candidates, none chosen

- **CAP-1 — the Spec ladder is declared.**
  - **intent:** the eight Spec statuses get what the Dream ladder already has — a stated naming
    rule, a definition per value, and the coupling rules to the Dream ladder in the same place.
  - **success:** a reader can determine a Spec's legal statuses and what each asserts without
    reading `board.py`. *(Open: declared as-is or reduced; where it lives.)*
- **CAP-2 — one declared vocabulary source the detectors read.**
  - **intent:** replace the five hard-coded sets across `board.py`, `chain.py` and
    `status_body_consistency.py` with one declaration both prose and code consume.
  - **success:** adding or retiring a status value is a one-place change, and no detector carries
    a private copy.
  - **Scope widened 2026-09-14 (operator ruling on `DW-VOCAB-2026-09-14-8`): the exit-code
    lattices are the second vocabulary this CAP owns.** Four exit-code domains are live at once —
    `pyforge.doctor.verdict` `{0, 2, 130}` (2 = FAIL, no 1), `scripts/detectors.py` `{0, 1, 2}`
    (2 = could-not-run), `pyforge.warden.verdict` `{0, 1, 2, 130}`, `pyforge.marshal.core.verdict`
    `{0, 1, 2, 3, 4, 130}` — three of which invented their own numbers, with only Doctor⊂Warden
    documented as intentional and Marshal's recorded in its own docstring as "a recorded
    assumption, not architecture-dictated". The **declaration half is done**:
    `docs/reference/judgement-vocabulary.md` is the declared home and
    `tests/scripts/test_exit_code_domains_are_declared.py` pins all four domains against it,
    asserting the *code* rather than its prose, so the rot risk is closed. The **unification
    half is this CAP's**: one declared exit-code vocabulary the four surfaces *read*, rather
    than four hand-maintained constants — the same "no detector carries a private copy" success
    criterion, applied to exit codes instead of status values. Ruled to live here rather than in
    a Dream of its own because this Dream already owns "one name, one job" for the estate's
    vocabulary and a second Dream would split one contract across two chains. Constraints
    carried from the ledger entry: Doctor's subset of Warden's domain is deliberate
    (`doctor/verdict.py:4-7` — Doctor reports operability, not policy, so it omits the policy
    rung `1`) and survives unification as a declared subset; only the aggregator's `2` genuinely
    conflicts and it is the one surface with no lattice at all. Cross-station (doctor, warden,
    marshal, `scripts/detectors.py`), so the Story that lands it names all four surfaces and
    is dispatched when this Spec flips to `ready`.
- **CAP-3 — the BMAD↔Lexicon cross-walk.**
  - **intent:** BMAD supplies the terms in heaviest daily use (Epic, Story, Sprint, PRD,
    Retrospective, the five agents) and has no cross-walk, though the Hub got one.
  - **success:** every BMAD term we use maps to a Lexicon noun or is named as having none, and
    the places we diverge from upstream literals are recorded in the open.
- **CAP-4 — the unnamed collisions get rulings.** *(Delivered 2026-09-14; one Design-side follow-through carried in DW-VOCAB-2026-09-14-3.)*
  - **intent:** `Track` (Hub evidence record vs BMAD planning lane) and `Guard`/`Gate` (Hub
    check/decide vs our `gate_mode` and detectors vs BMAD's PASS/CONCERNS/FAIL) are named and
    ruled on, as the Charter did for Cogs/Smith.
  - **success:** no artifact uses either word without its sense being determinable.
  - **`Gate`: RULED 2026-09-14** by operator decision, landed as a Charter amendment
    (`pyforge-charter.md` § The Lexicon → `### Gate has three senses; verdict has one`, with a
    Realization-log entry). Three senses named and scoped — Warden's PR verdict, the harness CI
    gate, upstream BMAD's readiness gate — plus `verdict` reserved as the narrow word. The five
    surfaces that had declared themselves in violation were not: the Execution Doctrine already
    placed CI verify gates in the harness. No code changed. Closes
    `DW-VOCAB-2026-09-14-10`.
  - **`Track`: RULED 2026-09-14**, and more strictly than `Gate`. Both senses are written out in
    full — **evidence Track** (the Hub's durable run record) and **planning track** (a BMAD lane)
    — rather than the collision merely being named. The asymmetry is deliberate: the planning-lane
    sense is public-facing while the evidence sense is what our code emits, so a reader meeting
    either in isolation has no context to disambiguate from, whereas `Gate`'s three senses all sit
    inside the estate. Landed as a Charter amendment with a Realization-log entry. Applied to the
    20 legacy `docs/specs/` header rows; the deck half is **not** applicable in-repo — its
    fragments are generated and its prototype is a Claude Design pull — so it is folded into
    `DW-VOCAB-2026-09-14-3`, which already owns a Design-side pass.
  - **CAP-4 is therefore met on both halves**, subject to that one Design-side follow-through.
  - **Out of scope for this CAP, recorded so it is not mistaken for part of it:** marshal's own
    six-rung verdict lattice and its `GATE_FAILED` rung are a question of *fact* — does that
    value ever escape the loop to a PR? — not of vocabulary. Tracked separately; the Gate ruling
    deliberately does not pre-judge it.
- **CAP-5 — the Design tier stops drifting.**
  - **intent:** the deck's practice vocabulary either joins the map or is declared
    teaching-only; its four retired BMAD names and the retired Paige persona are corrected; and
    the Design→repo pull stops silently falling behind (13.5 KB today, the same class the
    Charter's 2026-08-01 amendment fixed).
  - **success:** Design and repo agree, and a recurrence is detected rather than noticed.

## Constraints

- The Charter is Tier 0: corrections are **amendments with Realization-log entries**.
- Charter CAP-4 binds: an external vocabulary is cross-walked and **never joins** the seven.
- Do not rename a Lexicon noun.
- Upstream BMAD literals are not ours to redefine; where we differ we conform or record why.
- Status is not a proxy for work remaining — the ledger is (`docs/dreams/README.md:90-98`).
- Memlogs are append-only; no migration rewrites history.
- A vocabulary change lands with the detector that reads it, in the same change.

## Non-goals

- Adopting Cogs / Ops as PyForge nouns.
- A Frame registry.
- ~~Chasing `frame-spec` v0.3 before PR #28 merges.~~ **Amended 2026-09-14 by operator ruling:**
  *"we move forward by adopting frame-spec v0.3 — the PR will merge, and no point starting with an
  outdated version."* Landed as steward **Story 53.6**. The original caution was not wrong about
  the risk — #28 is still open — but it was wrong about the exposure: the estate already declared
  `type: frame [0.3]` in Story 53.5, so waiting meant conforming to *neither* version, and the
  conformance gaps found (a `name-ref` where §4.2.1 wants a `qualified-ref`, slug titles where the
  element profile says `title` MUST NOT be slug-constrained, scalar repeatables where §6.2.1 says a
  writer MUST emit sequences) are stable properties of the Markdown encoding rather than v0.3
  novelties, so a further draft revision cannot invalidate them. Residual exposure is named in
  CAP-5's research trail, not hidden: if #28's element registry changes before merge, the nine
  Frames and `frames.py` are re-run from the same profile CSV.
- Renaming `sprint-status-ledger.yaml` as an end in itself.
- Re-litigating the Dream ladder, which is declared, principled, and working.

## Success signal

A reader — human or agent — can look at any status on any artifact in this estate and know which
vocabulary it belongs to, what act it asserts, and what it obliges downstream; the detectors read
that vocabulary from one declared place; and the Charter's Hub enumeration is correct.

## Open Questions

All eleven are carried verbatim from the Dream's § *Open questions for the Spec* and are
**operator decisions**, not agent fills. They are listed in this file's `open_questions:`
frontmatter by key. None may be answered by inference from the research alone — the research
establishes what is true, not what we should do about it.
