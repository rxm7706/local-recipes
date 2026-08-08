---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - '{project-root}/docs/dreams/pyforge-herald.md'
  - '{project-root}/docs/dreams/herald-moments-2-4-live-backend.md'
  - '{project-root}/docs/dreams/herald-pitch.md (archived)'
  - '{project-root}/docs/dreams/herald-moments-2-4-missing-surface.md (archived)'
  - '{project-root}/docs/dreams/pyforge-charter.md'
  - '{project-root}/docs/dreams/pyforge-genesis.md'
  - '{project-root}/docs/dreams/factory-console.md (archived, Marshal-owned)'
  - '{project-root}/docs/dreams/artifact-console.md (archived, Marshal-owned)'
  - '{project-root}/docs/dreams/dashboard-project-path-derivation.md (Marshal-owned)'
  - '{planning_artifacts}/retros/retro-herald-2026-08-08.md'
  - '{planning_artifacts}/prds/prd-pyforge-herald-2026-08-01/prd.md'
  - 'src/shared/packages/pyforge-herald/ (shipped code, Epics 1-12)'
workflowType: 'research'
lastStep: 5
research_type: 'domain'
research_topic: 'Engineering proclamation as a domain: what "capture the dream, illustrate the telemetry, proclaim the release" means now that Herald''s Four Moments are shipped; the invisible-work problem in an agentic SDLC; the Four Moments as a post-build domain model'
research_goals: 'Herald''s first domain research (none existed pre-build). Ground the domain problem Herald solves, test the Four Moments taxonomy against what actually shipped (47/47 stories), and name the domain tensions the shipped shape exposes — attested vs derived truth, register vs town crier, and the boundary with Marshal''s Guildhall.'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: false
source_verification: true
project_slug: 'pyforge-herald'
---

# Research Report: Domain

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Domain
**Project:** pyforge-herald

---

## Research Overview

### Question

Herald shipped 47/47 stories (Epics 1–12) without ever having had a domain research
document — the market analogue scan (2026-07-25) and the requirements analysis
(2026-08-01) both presupposed the domain rather than examining it. Now that the Four
Moments are real code, three questions can finally be answered from evidence rather
than aspiration:

1. What is the actual domain problem behind "invisible engineering is failed
   engineering," and why does an *agentic* SDLC make it worse, not better?
2. Does the Four Moments taxonomy (Pitch / Progress / Success / Operations) hold up
   as a domain model now that each moment has a concrete data shape and a CLI verb —
   and where did contact with reality bend it?
3. What domain tensions did shipping expose that the pre-build Dreams never named?

### Methodology

Post-hoc grounded analysis, not speculation: the constitutive Dream
(`docs/dreams/pyforge-herald.md`, status `realized`), both archived seed Dreams
(`herald-pitch.md`, `herald-moments-2-4-missing-surface.md`), the deferred
live-backend Dream (`herald-moments-2-4-live-backend.md`), the whole-build retro
(`retros/retro-herald-2026-08-08.md`), and the shipped modules themselves
(`src/shared/packages/pyforge-herald/src/pyforge/herald/{cli,progress,claims,notices}.py`
and `web/`). Cross-station context from the Charter, Genesis, and Marshal's
console Dreams.

### Limitations (declared)

- No external interviews or user studies — the "audience" for Herald's proclamations
  is currently one operator plus the hypothetical future contributor/stakeholder the
  Charter imagines. Domain claims about audiences beyond that are reasoned, not
  observed.
- Written the same day as the retro and Epic 12's close-out; the shipped surface has
  had essentially zero production usage time. Adoption-dependent claims (e.g., "the
  operator will forget to run `--update`") are predictions from the architecture,
  not measurements — though well-founded ones (§4.2).

---

## Part 1 — The Domain Problem: Invisible Work in an Agentic Factory

### 1.1 The classic problem

Every engineering organization has a communication debt: work happens, and knowledge
of the work does not. The traditional industry answers are fragmentary and
role-scattered — release notes (owned by whoever cuts the release), changelogs
(owned by convention or tooling), status pages (owned by ops), deprecation policies
(owned by nobody until a user is burned), and pitch decks (owned by whoever wants
budget). Each is a separate genre with a separate owner, a separate cadence, and a
separate decay rate. No mainstream practice treats them as *one lifecycle owned by
one voice*.

### 1.2 Why the agentic SDLC intensifies it

The Charter's thesis ("Humans Dream, Agents Deliver") removes the last accidental
communication channel engineering ever had: **the humans who did the work**. In a
conventional team, knowledge of what shipped travels osmotically — standups, PR
reviews, hallway talk. When agents write the code, that osmosis is gone. The human's
role "rises from writing software to architecting Dreams" (`pyforge-charter.md`),
which means the human is *structurally further from the work* than any engineering
manager has ever been. This repo demonstrated the failure concretely during Herald's
own build: 47 stories landed across ~12 PRs in two weeks, and the only human-legible
records of what happened are the artifacts the factory deliberately produced —
story specs, the sprint ledger, the retro. Nothing about agentic delivery is
self-announcing.

This is the precise domain claim behind "invisible engineering is failed
engineering": in an agentic factory, **proclamation is not marketing, it is the
governance channel**. The Charter's own line — "no station reports a green it didn't
earn" — is unenforceable if nobody is structurally responsible for reporting greens
at all.

### 1.3 The three verbs of the dream title

"Capture the dream, illustrate the telemetry, proclaim the release" decomposes into
three distinct domain activities that the shipped system now lets us name precisely:

| Verb | Domain activity | Shipped as | Domain status |
|---|---|---|---|
| **Capture** | Making an aspiration arguable to people who did not have it | `herald deck seed/pull/status/watch/push` (Epics 1–5) — the Design↔Code bridge | **Real and mature** — 7+ decks round-tripped; the mechanism, not just the artifact |
| **Illustrate** | Rendering in-flight work and cost as evidence, not prose | `herald progress` + the Progress dashboard tab | **Real but attested, not derived** (§4.1) — the "telemetry" is operator-typed flags, not telemetry |
| **Proclaim** | Delivering claims and endings to an audience | `herald success` / `herald notice` + Success/Operations tabs | **Half-real** — the record exists; the *telling* does not (§3.2) |

---

## Part 2 — The Four Moments as a Domain Model: Imagined vs. Shipped

### 2.1 The taxonomy survived; the substrate did not

The pre-build model (both archived Dreams, the 2026-08-01 PRD satellite) imagined the
moments as *broadcast events on live infrastructure*: a webhook fires when CI merges,
a weekly cron compiles notables, delivery fans out to Slack/email/wiki. What shipped
(per the 2026-08-08 scope decision, recorded in
`docs/dreams/herald-moments-2-4-live-backend.md` and every implementing spec) is the
moments as **record types with lifecycles**, created by an operator's hand:

| Moment | Imagined (epics doc) | Shipped (actual domain object) |
|---|---|---|
| 2 — Progress | on-ship webhook + weekly cron aggregation | `Progress` record, unique per `(station, date)`, upserted via `herald progress <station> --update` with explicit cost flags (`progress.py`) |
| 3 — Success | PR-close auto-extraction + dashboard API | `Claim` with attached `Evidence`, a `draft → published` review gate, 7-day evidence staleness computed at read time (`claims.py`, `evidence.py`) |
| 4 — Operations | HTTP-served notice archive + redirects | Dual-representation notice: durable git-tracked markdown under `notices/YYYY-MM/<type>/<component>.md` plus a denormalized JSON index; file-based redirect map (`notices.py`) |

The consequential domain finding: **the taxonomy proved to be about data shapes, not
about triggers.** Every moment survived the loss of its imagined infrastructure
intact — the record schemas, lifecycles, and review gates are exactly what the
epics doc described; only the *cause* of each record changed (operator command
instead of webhook). This is strong evidence the Four Moments is a sound domain
model: a taxonomy that only works on one substrate is a product feature; one that
transplants cleanly is a domain model.

### 2.2 What the shipped model added that was never imagined

Three domain refinements emerged only in implementation:

1. **Evidence staleness as a computed property** (`claims.py`: "staleness is a
   function of how old `validated_at` is, recomputed at read time" — never stored).
   The pre-build spec had a re-validation *job*; the shipped model has a
   re-validation *epistemics*: a claim's proof decays on a 7-day clock whether or
   not anyone runs anything. That is a genuinely better domain statement — proof
   has a shelf life independent of process.
2. **Cross-moment citation** (Story 11.3): a Success claim's evidence can cite an
   Operations notice by component name, and the reverse view
   (`referenced_by_claims`) is computed, never persisted — the two moments
   reference each other without either owning the other. The moments are now a
   linked model, not four silos.
3. **Endings as first-class records with a permanent archive.** The constitutive
   Dream's sharpest line — "a retired product currently just stops appearing;
   nobody is told it ended" — got a real answer: `herald notice close/archive`
   produces a git-diffable markdown record filed by creation month, with a
   revisions trail. Scale-invariant ending ("one act... `archived`, with one of
   four reasons") is now enforced by a schema, not a convention.

### 2.3 What was retired

The "bookend framing" ("first to touch a Dream, last to touch a release") was
retired pre-build (2026-07-25) because it implied silence between touchpoints. The
shipped system vindicates the retirement: `herald progress` is architecturally a
*daily* surface (one record per station per day is the uniqueness key), which is the
opposite of a bookend.

---

## Part 3 — The Central Domain Tension: The Register vs. the Town Crier

### 3.1 Proclamation decomposes into capture, composition, and delivery

Herald v1 ships the first two and defers the third. The records exist
(`.herald/*.json`, `notices/`), the composed views exist (the three dashboard tabs,
`herald ... --json`), but **no delivery channel of any kind shipped** — no Slack, no
email, no RSS, not even a hosted URL for the dashboard (it is a local Vite bundle an
operator builds and views on their own machine, fed by hand-run snapshot exporters —
see the technical research, same date). The 2026-07-25 market research's entire
`herald broadcast` capability class remains at zero implementation.

### 3.2 In domain terms: Herald built a register, not a town crier

A medieval herald had two jobs: keep the roll (who is who, what was granted, what
died) and *cry the news*. V1 is the roll. This is not a criticism of the scope
decision — the scope decision was correct and cleanly executed (retro §4) — but it
is the honest domain characterization: **"shipping is not the same as being known to
have shipped" is still true of Herald's own records.** A published Claim in
`.herald/claims.json` on one operator's laptop has precisely the discoverability of
the closed PR it was meant to improve upon, until a snapshot is exported and the
dashboard is served somewhere. Moment 3's domain problem is solved at the
data-model layer and open at the audience layer.

This gives the deferred live-backend Dream its proper domain framing: the database/
webhook/cron question is really the **audience question** in disguise. A webhook is
how records become *current* without an operator; hosting is how they become
*visible* without one. Both are prerequisites of delivery, and delivery is the
unshipped half of proclamation.

---

## Part 4 — Two Dashboards, Two Truth Models: The Boundary with Marshal

### 4.1 Derived truth vs. attested truth

The factory now has two dashboard surfaces with opposite epistemics:

- **Marshal's Guildhall** (`docs/dashboard/generate.py`, successor to the archived
  [[artifact-console]] per `factory-console.md`): *derived* truth. "Nothing on the
  console is hand-maintained... if the repo moved, the console already knows."
  Its failure mode is derivation bugs — exactly what Marshal's
  `dashboard-project-path-derivation.md` Dream documents (the slug==directory
  assumption produced the same false-"nothing landed" bug twice).
- **Herald's Four Moments dashboard**: *attested* truth. Every Progress record is an
  operator's sworn statement (`--shipped`, `--compute-hours`, `--token-spend` typed
  by hand); every Claim's evidence is operator-supplied URLs. Its failure mode is
  the opposite: silence and staleness. Nothing in the system knows a ship happened
  unless someone says so.

### 4.2 The attested model reintroduces the invisible-work problem at the meta level

This is the sharpest domain finding of the refresh. Herald exists because work that
nobody announces is invisible — and Herald v1's own mechanism depends on an operator
remembering to announce. The live-backend Dream names this honestly: the scaled-down
pass "trades away the whole point of 'automatic': a factory lead currently has to
remember to run `herald progress warden --update` after a ship." The domain risk is
not that the dashboard will be wrong; it is that it will be **credibly incomplete**
— a Progress tab showing three stations' records reads as "the other five did
nothing," which is exactly the misreading Herald was built to prevent. An attested
register with no freshness signal is worse than no register once an audience trusts
it. (Mitigation paths — freshness indicators, telemetry-derived defaults, hook- or
CI-triggered CLI runs that need no server — are enumerated in the companion
technical research.)

### 4.3 The boundary itself is sound

The 2026-07-23/2026-08-02 ownership reviews drew the line correctly and it held
through the build: Marshal owns machinery and derived state (loop orchestration,
the Guildhall, fleet-chain regeneration); Herald owns the communication face and
attested narrative. The two dashboards are not duplicates — the Guildhall answers
"where is every Dream in the lifecycle" (governance of *intent*), the Four Moments
answers "what does the factory say about itself" (governance of *narrative*). The
persona ideal ("Herald proclaims from the stage the console provides") suggests the
eventual convergence: Herald's published records becoming a feed the Guildhall
renders — which the factory-console Dream's still-unbuilt "delivery/notables feed"
frontier explicitly anticipates. That convergence, not a merger of the dashboards,
is the domain-correct integration.

---

## Part 5 — Domain Synthesis

### 5.1 The forces, ranked

1. **Agentic delivery destroys osmotic knowledge** — proclamation becomes a
   governance requirement, not a marketing nicety. (Constitutive; nothing else
   matters if this is false, and this repo's own two-week/47-story build is the
   existence proof that it is true.)
2. **Proclamation = capture + composition + delivery; v1 shipped two of three.**
   The register/town-crier gap is the domain's open frontier and the real content
   of the live-backend Dream.
3. **Attested truth needs a freshness discipline** — the operator-triggered model
   reintroduces invisibility as staleness; any v2 must make silence visible
   (freshness signals) or make attestation automatic (triggers).
4. **The Four Moments held as a substrate-independent data model** — the strongest
   validation the taxonomy has received; future work can treat the record schemas
   as stable and iterate on triggers and channels.
5. **Two-truth-model coexistence with Marshal is a feature** — derived intent-state
   and attested narrative-state check each other; the integration point is a feed,
   not a merged dashboard.

### 5.2 Implications for what comes next

- Any Moments 2–4 v2 effort should be framed as **delivery work** (audience,
  hosting, channels, triggers), not data-model work — the model is done and proven.
- The "illustrate the telemetry" verb remains only half-honored: progress records
  *carry* cost figures but are not *derived from* the telemetry the factory already
  emits (`sprint-status-ledger.yaml`, loop journals, gate reports). Closing that
  gap — CLI defaults read from telemetry, operator confirms rather than types —
  would reconcile the shipped attested model with the 2026-07-25 research's
  telemetry-native differentiator without waiting for a live backend.
- Moment 4's archive is the quiet domain success worth publicizing internally: the
  factory now has a place where endings are told. It should be used the next time
  anything in this repo is actually retired (there is a real backlog of candidates:
  archived Dreams, retired specs, the deprecated BMAD wrapper skills).

## Assumptions

- The Charter's eight-station model remains current (the `STATIONS` tuple in
  `progress.py` and the dashboard sidebar both encode it).
- The single-operator posture persists near-term; multi-operator concurrency is a
  documented non-goal of the storage layer (lost-update class, see technical
  research).

## Open Questions

1. Who is the Four Moments dashboard's *second* user — a future contributor, a
   stakeholder, or another agent? The answer determines whether delivery means
   "host the dashboard" or "push to channels," and nothing yet forces the choice.
2. Should Progress attestation ever be creatable by an agent at story close-out
   (e.g., bmad-loop's own supervisor), or is human attestation load-bearing for
   trust? The Charter's "no green it didn't earn" cuts both ways.
3. Does Moment 1 (decks) belong on the same dashboard eventually — a "Pitch" tab
   showing deck freshness from `herald deck status` — unifying all four moments on
   one surface for the first time?

## Sources

Internal only (declared in frontmatter): the five Dream files, the 2026-08-08
whole-build retro, the consolidated PRD, and the shipped package source. No web
research was used for this domain report; the companion market refresh (same date)
carries the external landscape.
