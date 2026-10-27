# Dreams — Tier 0

> **Everything starts with a Dream.**

A **Dream** is the raw, unconstrained human aspiration that seeds a deliverable —
the BMAD mission itself: **B**uild **M**ore **A**rchitect **D**reams. It is
**Tier 0** of the framework-neutral layout (see
[`AGENTS.md` → the tiers](https://github.com/rxm7706/local-recipes/tree/main)), upstream of the spec BMAD produces
in `_bmad-output/projects/<slug>/planning-artifacts/` (legacy hand-authored
specs are archived under `archive/docs/specs/`).

`docs/dreams/` is the home for the **starting point of each deliverable**. Going
forward, a deliverable **begins as a Dream here** — a vision, unconstrained by
syntax or technical debt — and is only then solidified by BMAD (`bmad-spec` or
the planning chain) into the "what to build" contract in its project's
planning-artifacts. (Historically these
starting points were folded into `docs/specs/`; we are separating them: the Dream
holds the *why*, the spec holds the *what*.)

## How a Dream flows through the crew

```
Dream            Deck        Spec                  build · audit · ship        proclaim
docs/dreams/  →  (visual) →  bmad-spec →           Atlas · Warden · Mason  →   (release)
   the vision     Herald      planning-artifacts/                              Herald
```

- **Herald** reads the Dream and renders the **decks & infographics** — the visual
  alignment assets (`presentations/<slug>/`).
- **Marshal** solidifies the same Dream into the **spec** (`bmad-spec` →
  `_bmad-output/projects/<slug>/planning-artifacts/`), then drives the code with the **BMAD Method** — bmad
  skills + phases run autonomously via **bmad-loop** and **bmad-build-auto**.
- **Atlas / Warden / Mason** map dependencies, guard the perimeter, and ship.
- **Doctor** runs pre-flight diagnostics before the build and monitors fleet &
  feedstock health after it ships.
- **Live status** — throughout execution, the epic/story progress dashboard is kept
  updated and published on **GitHub Pages** (`docs/dashboard/` → the program
  console). Deliveries, notables, successes, roadmaps, and updates are marshalled
  from there. *(Today the orchestrator — Marshal — owns this run lifecycle; in the
  persona ideal it is Herald who proclaims the release.)*

A Dream **motivates** a spec; it never replaces it. The spec remains the build
contract; the Dream is the "why" behind it.

## Convention

- One Dream per file: `docs/dreams/<slug>.md`, plain markdown, tracked in git.
- The Dream's `<slug>` should match its eventual BMAD project slug
  (`_bmad-output/projects/<slug>/`), so the pair is easy to trace.
- Light frontmatter identifies it:

  ```yaml
  ---
  title: <Dream title>
  type: dream
  type: dream | practice
  owner: herald | marshal | atlas | warden | mason | doctor | scribe | steward | guild
  status: dreamt | pitched | specified | realized | archived
  blocked-on: <gate>          # optional; backlog qualifier only
  ---
  ```

- **`status:`** — each state names the **act that completed**, never the
  artifact that proves it: `dreamt` (a human captured it) → `pitched` (the case
  was made; a deck exists) → `specified` (the contract exists; a Spec exists) →
  `realized` (it runs) → `archived` (it ended). *(Renamed 2026-07-25 from
  `seeded`/`in-deck`/`in-spec` — those three named a file or a place rather than
  a state, and "in the deck" reads as *shuffled in, queued*, near the opposite of
  "the case has been made".)*

  **`specified` requires a Spec at `ready` or beyond, not merely a Spec that
  exists.** `dream_chain_check`'s INV-1 forces every Dream to carry a Spec from
  birth, so "a Spec exists" cannot by itself separate `dreamt` from `specified` —
  it is true of every Dream in the repo. A Spec still at `draft` establishes the
  *chain*, not the *contract*: its open questions are unanswered, so nothing
  downstream can bind to it. `dreamt` therefore stays reachable and means
  "captured, chain started, contract not settled". *(Clarified 2026-08-10 after
  four Dreams were found understating or overstating their state at once.)*

  **`extension-point` is a recognised parked-Spec state, and it does NOT satisfy
  `specified`.** A Spec may carry `status: extension-point` to mean "the chain
  exists and the contract is deliberately open — this is a seam a later effort
  extends, not a thing being built". It is the Spec-side sibling of `dreamt`:
  nothing downstream can bind to it either, so a Dream whose only Spec is
  `extension-point` reads `dreamt`, never `specified`. *(Named 2026-09-09, fleet
  readiness pass, atlas-B4 — `enterprise-data-models-and-apis` was reading
  `specified` on an `extension-point` Spec whose own § What is real says
  "Nothing".)*

  **Status is NOT a proxy for work remaining, in either direction — the ledger
  is.** Two live cases make the point. `bmad-module-provisioning` and
  `unified-container` both read `dreamt` while their epics were 3/3 and 5/5 done
  and merged. And the reverse direction is now even
  better evidenced than when this example was written: marshal's E7–E12 sat here
  as **36 backlog stories** under `genesis-installer`, which reads `archived`
  because it was correctly consolidated into `pyforge-marshal` (`realized`, and
  it does run) — and as of 2026-09-14 that block is **37 of 37 done**, with
  `genesis-installer` still reading `archived` throughout. The status never moved
  in either direction while the work went from all-unbuilt to all-shipped
  underneath it. *(Figures re-measured 2026-09-14. Today's largest unbuilt blocks
  are steward's Epic 44 — 8 blocked + 3 backlog — and herald's Epic 21, 10
  backlog; both sit under Dreams reading `specified`, which is correct and still
  tells you nothing about how much is left.)* Neither status is wrong under
  the definitions above; both are useless for "what is left". For that, read
  `sprint-status-ledger.yaml` or run `pixi run -e pyforge-guild fleet-picture`.

  **There is deliberately no `building` state.** Status declares what *exists*;
  the console *derives* what is happening from live build lines. Hand-maintained
  activity-tracking rots: `pyforge-warden` read `in-spec` while shipped 31/31,
  and `deckcraft` read `dreamt` while holding both a deck and a Spec — both
  found and fixed on 2026-07-25. `bmad-drift-check` now emits `dream-vocab` on a
  retired or invented value.

- **`owner:`** names the **station** accountable for carrying the Dream all the
  way to code — the through-line, propagated by the console onto every
  downstream row (Fleet, Backlog, In Build, Realized, Pitch, Archived). Owning
  **is** becoming — at the planning tier — but **the planning home is not the
  package name**, so Atlas owning
  [`unity-data-stack.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/unity-data-stack.md>) does not mean it ships as
  `pyforge-atlas`. *(Corrected 2026-09-14 on two counts: "owning is **not**
  becoming" was superseded by the Charter's 2026-07-28 §5 amendment, and the
  clause borrowed §5's other formula — "the station is the post, not the
  **person**", which is about a Smith being swappable, not about package
  identity. Two rulings had collapsed into one sentence with a swapped last
  word; they now read separately.)* `guild` is reserved for the one Dream that *precedes* the
  stations ([`pyforge-charter.md`](pyforge-charter.md)) **and, since 2026-09-14, for a gate
  that judges all eight Smiths** ([`coverage-gate-independence.md`](coverage-gate-independence.md)
  — the Charter §5 amendment of that date: `guild` is legal only where no Smith *can* be
  accountable because the artifact judges every one of them; cross-cutting or unowned does not
  qualify); `bmad-drift-check` emits `dream-unowned` for anything else claiming it. *(Closed at
  one on 2026-08-08, when `pyforge-genesis` was absorbed into the Charter — Dream § Satellite:
  The Seed, Spec CAP-5..CAP-8; re-opened for exactly that one further shape on 2026-09-14.
  `docs/governance/guild-roster.json` `guild_dreams` is the authority; this line trailed it
  until 2026-08-24.)* *(Replaces `crew`, which was both retired vocabulary and a non-answer —
  "the Guild owns it" means no station does.)*

- **`type: practice`** marks a perpetual concern — tended, never finished. It
  sits **outside** the lifecycle: excluded from Backlog (nobody can close it)
  and from Realized (it is never done).

- **`blocked-on:`** is a **backlog qualifier**, naming the external gate that
  makes an otherwise-available Dream un-pickup-able. It applies only to
  non-realized Dreams.

- Keep it aspirational and readable — a Dream is a narrative, not a task list.
- **`realized` is not exempt from the chain.** Per
  [`regenerable-factory.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/regenerable-factory.md>), a Dream that shipped
  before the model existed gets its PRD/spec **backfilled** (BMAD brownfield
  flow), so future change flows idea → spec → BMAD and drift checks can bind
  the code to its contract. The Realization log records the evidence either way.

## Dreams

**15 Dream files as of 2026-10-26** (README excluded), **every one mapped below.** The 158
archived per-station satellites that sat here until 2026-10-26 now live under
`archive/docs/dreams/<same name>` (`spec-one-chain-per-station` CAP-11; CHAIN-STANDARD §11: a
Dream is live in `docs/dreams/` or archived under `archive/`, never both). Each one's body is a
dated section of its station Dream, verbatim, and doctor's `fold-complete` check proves it; this
table lists live Dreams only. New Dreams get a row on arrival. Re-derive rather than trust the
literal: `ls docs/dreams/*.md | wc -l` for the total, and the per-status split from each file's
own frontmatter. **Reconciliation is file-driven, not row-driven.** It was row-driven until
doctor Story 21.6: `dreams-hygiene` read this table and judged only the Dreams with a row here,
so every omitted file was invisible to it. It now walks `docs/dreams/` itself, so a Dream is
reconciled because the FILE exists — a Dream cannot escape the checks by being left out of this
table, and this table is no longer load-bearing for them. Three of its warn-only classes come
from that walk: `dream-readme-missing` (a Dream file with no row below — the omitted backlog,
named rather than silent), `specified-spec-not-ready` (the `status:` rule stated above,
enforced), and `kinship-wikilink-dead` (a `Kinship` wikilink that resolves to no file under
`docs/dreams/` or `archive/docs/dreams/`). All three WARN and none gates; `dreams-hygiene-check` runs them, and
`detectors-ci` has since Story 41.1. The `dream-readme-missing` backlog was closed on 2026-10-24
by operator ruling (doctor Story 30.4): its rows were derived from each file's frontmatter, not
written from memory, and a new Dream's row lands with the Dream. The 158 interim rows for
archived Dreams left with their files on 2026-10-26, when CHAIN-STANDARD §11's move landed for
every station in one PR (`readme-table-orphan` names a row whose file is gone). The
**frontmatter is the source of
truth**; this table is a
curated map, and its Status column is now synced from frontmatter rather than hand-copied.
*(Historical: 25 Dreams as of 2026-07-23 — 3 born Dream-first — the regenerable factory among
them; 17 retro-seeded from a complete
repo + Design-workspace audit — the factory console among them; 3 persona
dreams added by ownership audits — Scribe + Steward when the crew grew 6 → 8,
Herald's charter when the ownership review re-scoped it; 2 recovered from the gist audit (a third, local-ai hardware, was judged out-of-repo scope and archived).)* **No-straggler policy:** every BMAD project, deck, Design
project, and spec maps to exactly one Dream; the herald CLI's status capability
(CAP-3) flags any unlinked Design project permanently.

**Foundations**

| Dream | Status | What it is |
|---|---|---|
| [`pyforge-charter.md`](pyforge-charter.md) | specified | **The founding Dream** — the PyForge Guild: eight Smiths, one "Dream to Code" pipeline. Master vision deck: `presentations/pyforge-genesis/`. |

**Persona products**

| Dream | Status | What it is |
|---|---|---|
| [`pyforge-atlas.md`](pyforge-atlas.md) | specified | The intelligence layer reborn as Kedro/Dagster/DuckDB dataflow an agent workforce maintains. *(Per-station progress figures are deliberately not carried here — the original migration's "waves 0–H, PRs #58–#105" long since stopped describing the station, which has grown through Epics 10–16 and beyond. Read `pixi run -e pyforge-guild fleet-picture`.)* |
| [`pyforge-warden.md`](pyforge-warden.md) | specified | The compliance gate that never false-greens — six axes of dependency trust. *(Story counts are deliberately not carried here — "25/31 built" was stale long before it was noticed. Read `pixi run -e pyforge-guild fleet-picture`.)* |
| [`pyforge-marshal.md`](pyforge-marshal.md) | specified | Graduated autonomy a human can trust — bmad-loop/dev-auto + gates + escalation; proved on atlas + warden. |
| [`pyforge-mason.md`](pyforge-mason.md) | specified | **Mason** — the Artisan Builder's station: the `mason` CLI (recipe / package / environment), seam-by-capability over the CFE craft; distinct from [`packaging-factory.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/packaging-factory.md>), the practice he tends. |
| [`pyforge-doctor.md`](pyforge-doctor.md) | specified | One bedside manner over the fleet's vitals — pre-flight diagnostics + continuous monitoring + prescriptions (a consolidation of existing instruments). |
| [`pyforge-herald.md`](pyforge-herald.md) | specified | The outward voice + design surface — decks, bridge, telemetry imagery, proclamations (charter re-scoped 2026-07-23: infrastructure → Marshal). |
| [`pyforge-scribe.md`](pyforge-scribe.md) | specified | The inward voice — team knowledge captured, curated, compiled into the graph, answerable (owns team-memory + sentinel's core). |
| [`pyforge-steward.md`](pyforge-steward.md) | specified | The estate the factory stands on — provisioning, deployment, credential lifecycle, budgets, incident response. |

**Capabilities**

| Dream | Status | What it is |
|---|---|---|
| [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md) | specified | Evergreen Foundry Dream (hub-and-spoke, eight stations). Read **Grounding** + **How to read** first. Living file = build-target mermaid; historical topology / tree / fleet evidence in [`archive/pyforge-unifying-strategy-2026-08-23-topology.md`](archive/pyforge-unifying-strategy-2026-08-23-topology.md). Host work is **`pap:CAP-1`..`6`** (`extends` `spec-python-agent-platform`); Unifying **CAP-1..19** are a different set. CAP-1..18 closeout stands; CAP-19 / Epic 34 shipped 2026-08-26. **Live build target is § *Cutover to `python-foundry`*** — `spec-python-foundry-cutover` (`fnd:CAP-1..15`, CAP-7 retired), steward Epic 44 (44.3 / 44.7 / 44.12 / 44.13 `done`, 44.4–44.6 parked, 8 `blocked`) plus Epic 67; Epic 47's P1–P18 readiness lines gated 44.3 (flipped 2026-09-13). Red-team Epics 40–43 `done` (43.7 `backlog`). **Currency review 2026-09-09** (`research/currency-review-pyforge-unifying-strategy-2026-09-09.md`): code healthy, 28/28 detectors; document tier corrected the same day; contractual residue (≤400-line constraint, CAP-axis namespace, five open `DW-RT` directives, Single-Spec merge) awaits `bmad-correct-course`. Q5 published 2026-09-15 on [`build-league-scorecard.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/build-league-scorecard.md>) (Epic 62 catalog). **Consolidation 2026-09-25** (§ *Where next*): PRs #1563 / #1564 / #1576 and the BMAD-method whitepaper folded in one PR — `fnd:CAP-12..15` (laptop SBOM, checkable SBOM, dossier as control plane, estate-first instruction surface), `fnd:CAP-7` retired (**no archive of A**); decomposed as steward Epic 67, herald 26.1, scribe 21.1. |

**Applications**

| Dream | Status | What it is |
|---|---|---|
| [`foundry-regenerate-not-fold.md`](foundry-regenerate-not-fold.md) | specified | Launch foundry by regenerating core/steward/marshal from Frames + a thin test oracle — not folding `src/shared/packages/`. Epic 54; 44.4/44.5 parked. CLI+MCP only; invent in local-recipes. |
| [`foundry-capability-ledger.md`](foundry-capability-ledger.md) | specified | Strangler routing table: rebuild / retire / dated A-only / B-only. Extract inventory. Epic 55; kit with 53.5 Frames + 54.1 case-list. |
| [`coverage-gate-independence.md`](coverage-gate-independence.md) | specified | **A check that can red a station's PR must not ship inside that station's package.** Found 2026-09-14 by an investigation aimed elsewhere: marshal's verdict lattice was *cleared*, and the violation was one directory up — `pyforge/marshal/coverage_gate.py` + `coverage_thresholds.toml` ship **inside** marshal while `coverage-gates.yml` runs that gate over all eight stations with no `continue-on-error` (Charter §6 verbatim, scope ruled **broad**). Every station-side home failed (`pyforge-core`, `pyforge-testing-kit` *and* `scripts/` are marshal-governed; doctor is advisory), so the question was "who owns a policy that binds all eight". **Ruled the same day:** `owner: guild` by the narrow Charter §5 amendment (a gate that judges all eight Smiths is the Guild's — the only Dream besides the Charter to carry `guild`); Spec at `docs/governance/spec-coverage-gate-independence/`, `ready`, all five questions answered; the mechanism stories are doctor's (§5 outcome/mechanism rule). Sibling ruling: `ledger-regression` is now a scoped blocking step in `detectors.yml`, so the judge's verdict on Marshal has force. |
| [`one-chain-per-station.md`](one-chain-per-station.md) | specified | **One Dream, one Spec, one PRD, one architecture, one epic chain — per station.** Seeded 2026-09-16 the morning the token-savings fold (PRs #1382/#1383) proved the shape on marshal. Fleet: 171 Dreams / 172 Specs for eight stations while PRD, spine and epics are already one-per-station; the 2026-08-08 61-Dream fold regrew in five weeks because the minting rules compose into a Dream+Spec pair per effort. Six operator rulings: Dream-**append**-first with a closed `fold-exemption:` list and a `chain-sprawl-check` detector; 8 station chains + the Guild's; fold **everything** (shipped included; the decision record survives, derived bodies are disposable); the PRD stays and **derives** from the Spec (FR ← CAP); the fold is the foundry on-ramp; **marshal is the pilot**. `owner: guild` (second instance of the 09-14 §5 shape — the gate grades every Smith's row; Dream-append-first is a *reading* under Charter CAP-1, not an amendment; carries the first `fold-exemption: governance`). Spec **`ready`** at `docs/governance/spec-one-chain-per-station/` — the three OQs ruled the same day: no fifth Dream status (station Dreams read `specified` by the existing rule once their Spec is `in-progress`); `pyforge-core` and the testing kit are marshal-owned `cross-station-seam` exemptions; the Charter's only ritual is CAP-1. Operator constraint: **evergreen standard > historical accuracy > implementation**, eventual consistency station by station, portable to pyforge-foundry; a fold is a **rebase** (CAPs, epics and stories renumber sequentially across all four BMAD phases, re-key map in the PR); **marshal → steward → herald → the rest in parallel**. CAP-9: one companion page, `CHAIN-STANDARD.md` — hierarchy, relations, sequence, one status enum per tier, one name per concept, one id family per job, the fold checklist — every existing ruling with its grandfathering removed. |
| [`feature-flag-governance.md`](feature-flag-governance.md) | specified | **Every capability ships behind a flag, and a gate that no station owns checks that it does.** Seeded 2026-09-28 from the intake triage (`archive/docs/intake/bmad_feature_flag_governance_prompt.md`). The flag platform already exists: OpenFeature FILE, one tree (canopy:AD-11, steward Epic 26). Nothing uses it yet: the tree holds two flags, no story names a flag, and a second tree (`.steward/flags.json`) breaks AD-11. **Four operator rulings:** every capability, blocking; a closed exemption list plus a retrofit; backlog warns until retrofitted while stories minted after the rule date are refused; the Guild owns it. `owner: guild` is the third instance of the 09-14 §5 shape. Doctor owns the mechanism stories and each Smith owns its retrofit stories. Spec **`ready`** at `docs/governance/spec-feature-flag-governance/`: CAP-1..7 chosen, and all seven open questions were ruled the same session. The gate counts `type: feature` stories and exempts fixes; an OFF verb stays listed and refuses; a flag must be removed 90 days after it is ON everywhere; flags are global only in v1; the retrofit uses one flag per CAP; CI and dispatch start refusing on the same day. The rule date is 2026-09-28. |
