# Dreams — Tier 0

> **Everything starts with a Dream.**

A **Dream** is the raw, unconstrained human aspiration that seeds a deliverable —
the BMAD mission itself: **B**uild **M**ore **A**rchitect **D**reams. It is
**Tier 0** of the framework-neutral layout (see
[`AGENTS.md` → the tiers](../../AGENTS.md)), upstream of the spec BMAD produces
in `_bmad-output/projects/<slug>/planning-artifacts/` (legacy hand-authored
specs remain in [`docs/specs/`](../specs/)).

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
  [`unity-data-stack.md`](unity-data-stack.md) does not mean it ships as
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
  [`regenerable-factory.md`](regenerable-factory.md), a Dream that shipped
  before the model existed gets its PRD/spec **backfilled** (BMAD brownfield
  flow), so future change flows idea → spec → BMAD and drift checks can bind
  the code to its contract. The Realization log records the evidence either way.

## Dreams

**133 Dream files as of 2026-09-09** (README excluded), of which **72 are mapped below** — the
**61 omitted** are the archived per-station satellites folded into their parent Dream on
2026-08-08 (see **Dream-level-only consolidation**) plus later-seeded Dreams not yet given a row
(at this count: 20 archived, 22 specified, 16 realized, 3 dreamt). *(Two rows added 2026-09-09
for doctor's `capability-effect-check` and `status-body-consistency`, both minted in that pass —
new Dreams get a row on arrival; the 61 are a pre-existing backlog D2 owns, not a place to file
new work.)* Re-derive rather than trust the
literal: `ls docs/dreams/*.md | wc -l` for the total, and the per-status split from each file's
own frontmatter. **Coverage is a known gap, not a convention:** `dreams-hygiene` reconciles only
Dreams that have a row here (`chain.py:891`), so the 63 omitted files are invisible to it and
nothing enforces the `status:` rule above across them — vessel: a doctor extension of
`dreams-hygiene` to every Dream file plus a README-rule check (fleet readiness 2026-09-09, Class D
D2). Rows are **not** added by hand to close that gap. The **frontmatter is the source of
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
| [`sentinel.md`](sentinel.md) | archived | **The ancestor** (2026-04): the AI Software Factory — "the graph is the product"; unbuilt core, stranded artifacts to repatriate; descendants credited. |

**Persona products**

| Dream | Status | What it is |
|---|---|---|
| [`packaging-factory.md`](packaging-factory.md) | archived | The origin dream: the AI-assisted conda-forge factory (Mason) — CFE skill, 769 feedstocks, campaigns; frontier: multi-ecosystem autotick, smart test extractor. |
| [`pyforge-atlas.md`](pyforge-atlas.md) | realized | The intelligence layer reborn as Kedro/Dagster/DuckDB dataflow an agent workforce maintains. *(Per-station progress figures are deliberately not carried here — the original migration's "waves 0–H, PRs #58–#105" long since stopped describing the station, which has grown through Epics 10–16 and beyond. Read `pixi run -e pyforge-guild fleet-picture`.)* |
| [`pyforge-warden.md`](pyforge-warden.md) | specified | The compliance gate that never false-greens — six axes of dependency trust. *(Story counts are deliberately not carried here — "25/31 built" was stale long before it was noticed. Read `pixi run -e pyforge-guild fleet-picture`.)* |
| [`pyforge-marshal.md`](pyforge-marshal.md) | realized | Graduated autonomy a human can trust — bmad-loop/dev-auto + gates + escalation; proved on atlas + warden. |
| [`pyforge-mason.md`](pyforge-mason.md) | specified | **Mason** — the Artisan Builder's station: the `mason` CLI (recipe / package / environment), seam-by-capability over the CFE craft; distinct from [`packaging-factory.md`](packaging-factory.md), the practice he tends. |
| [`pyforge-doctor.md`](pyforge-doctor.md) | realized | One bedside manner over the fleet's vitals — pre-flight diagnostics + continuous monitoring + prescriptions (a consolidation of existing instruments). |
| [`pyforge-herald.md`](pyforge-herald.md) | realized | The outward voice + design surface — decks, bridge, telemetry imagery, proclamations (charter re-scoped 2026-07-23: infrastructure → Marshal). |
| [`pyforge-scribe.md`](pyforge-scribe.md) | realized | The inward voice — team knowledge captured, curated, compiled into the graph, answerable (owns team-memory + sentinel's core). |
| [`scribe-graphify-nightly-currency.md`](scribe-graphify-nightly-currency.md) | specified | Nightly compile keeps the graphify code surface — adapter works against live graphifyy; 02:30 does not drop `code:` nodes. |
| [`scribe-knowledge-layers.md`](scribe-knowledge-layers.md) | specified | Compile and recall are layered knowledge (hygiene, named Dreams/SPECs/facts, default recall omits `code:`), not one lexical bag. |
| [`scribe-marshal-fact-visibility.md`](scribe-marshal-fact-visibility.md) | specified | Scoped Marshal retrieve can cite that project's own `presentations/<slug>/facts.yaml` (identity, not a presentations/ leak). |
| [`scribe-in-flight-story-specs.md`](scribe-in-flight-story-specs.md) | specified | Compile in-flight story specs only; the sprint ledger is the filter, not stale frontmatter. |
| [`scribe-recall-stale-between-nightlies.md`](scribe-recall-stale-between-nightlies.md) | specified | Persist `compiled_at`; recall withholds sources committed after that compile. |
| [`scribe-portal-recall-defaults.md`](scribe-portal-recall-defaults.md) | specified | Portal and Marshal inherit default recall (no `--kind`); Cursor names the session path. |
| [`scribe-planning-pointers.md`](scribe-planning-pointers.md) | specified | Compile Brief/PRD/Architecture-spine/`epics.md` as pointer nodes (title, path, status, FR/AD/headings) — never the wholesale body. |
| [`scribe-named-docs.md`](scribe-named-docs.md) | specified | Named docs extras: how-tos plus a library-catalog heading extract — never `docs/**`. |
| [`scribe-graphify-target-list.md`](scribe-graphify-target-list.md) | specified | Extra-on graphify ingest walks packages + platform + scripts — never `recipes/` or the repo root. |
| [`scribe-recall-modes.md`](scribe-recall-modes.md) | specified | First-class `--mode planning|memory|code` bags, exclusive with `--kind`. |
| [`scribe-code-navigation-owner.md`](scribe-code-navigation-owner.md) | specified | One nav owner: Marshal `codegraph.db` for symbols; graphify `code:` is AST/report only. Epic 17 / Story 17.1. |
| [`pyforge-steward.md`](pyforge-steward.md) | realized | The estate the factory stands on — provisioning, deployment, credential lifecycle, budgets, incident response. |

**Practices**

| Dream | Status | What it is |
|---|---|---|
| [`fleet-stewardship.md`](fleet-stewardship.md) | realized · perpetual | Tend every touchable feedstock: refresh tracks, platform expansion, failure remediation — recurring waves, never finished. |
| [`upstream-discovery.md`](upstream-discovery.md) | archived | Sense what the world is building (trending + org audits, atlas Phase T) and package it before it's asked for. |
| [`regenerable-factory.md`](regenerable-factory.md) | realized | Backfill Dream→PRD→spec chains under every realized surface (BMAD brownfield) so the factory can change any code through the pipeline; drift checks on all code; the regeneration drill as proof. |
| [`chain-currency-sweep.md`](chain-currency-sweep.md) | specified | Planning spines re-derived, not decayed: the two-layer detector+reconciler sweep that clears the chain audit's staleness/coherence findings — per-station cascades grounded in research, the Unifying Strategy, and as-built code. |

**Capabilities**

| Dream | Status | What it is |
|---|---|---|
| [`agent-portability.md`](agent-portability.md) | archived | BMAD on any agent (Devin/Copilot/Claude/Cursor); planning on flat-rate subscriptions; the Portability contract enforced. |
| [`bmad-cursor-interactive-routing.md`](bmad-cursor-interactive-routing.md) | archived | Headless Cursor dispatch (`cursor-agent -p`, Story 22.8/CAP-6) is already live; this Dream is the narrower, unverified gap — routing BMAD skills from Cursor's own interactive chat, and confirming that surface can spawn the context-free subagents `bmad-build-auto`'s review mandates. **Folded into `marshal-token-economy` 2026-09-16** (operator-ruled consolidation; the Spec folded too — superseded, re-minted as `spec-marshal-token-economy` CAP-19..24, Epic 46). |
| [`team-memory.md`](team-memory.md) | archived | Shared, version-controlled team memory — what the team knows, every agent knows. |
| [`enterprise-airgap.md`](enterprise-airgap.md) | realized | The factory behind the firewall — JFrog routing + air-gap-by-design; frontier: presenton, deckcraft, warden's registry perimeter. |
| [`agentic-sdlc-autonomy.md`](agentic-sdlc-autonomy.md) | specified | The four views of agentic autonomy (taxonomy/process/architecture/environment) — the white paper + the 45-slide deck + our live L3 evidence. |
| [`factory-console.md`](factory-console.md) | realized | The whole pipeline on one public page — every Dream + lifecycle stage (Dreamscape board), live epic/story progress, nothing hand-maintained (GitHub Pages). |
| [`pyforge-pages.md`](pyforge-pages.md) | specified | The public Pages root is one dossier YAML with many renders — landing, gallery, Claude Artifact — Kedro-Viz stays at `/kedro-viz/`; foundry rebuilds this surface after 54.5. |
| [`fidelity-enforcement.md`](fidelity-enforcement.md) | archived | A contract is only a contract if something fails against it — every tier boundary gated in both directions; generalizes §7's law from the Guildhall to the whole chain. |
| [`durable-runs.md`](durable-runs.md) | realized | Work survives the machine that made it — no commit, spec or verdict exists only on one disk; the loop pushes at its own stage boundaries. |
| [`pr-lifecycle.md`](pr-lifecycle.md) | realized | A story lands itself — open, label, wait for checks, merge, resync; landing rules declared as policy instead of remembered. Resolves marshal open question #10. |
| [`one-front-door.md`](one-front-door.md) | archived | Marshal drives everything BMAD installs — one composed surface over 11 packages, 51 skills, 10 detectors and the engine; the runtime half of [`genesis-installer`](genesis-installer.md). **Draft for refinement.** |
| [`unified-container.md`](unified-container.md) | realized | All 8 stations in one Docker/Podman image — one boot, the whole Guild available; motivated by the 2026-08-02 per-station architecture consolidation. |
| [`bmad-output-hygiene.md`](bmad-output-hygiene.md) | archived | One fabricated bulk commit stamped dead test scaffolding, a hollow sprint-status template, and (in places) fake test-architecture/README content across all 8 stations, inconsistently fixed since — a 5-agent audit mapped exactly what's real vs. debris. |
| [`dashboard-project-path-derivation.md`](dashboard-project-path-derivation.md) | archived | The dashboard builds links/`have` checks by gluing a roster slug straight onto a project directory — broke twice already for absorbed/dissolved satellites; wants one derivation helper instead of one override dict per occurrence. |
| [`genesis-installer-name-retirement.md`](genesis-installer-name-retirement.md) | archived | genesis-installer should retire completely — not just renumbered, but a full PRD/architecture/epics rewrite that actually decides the CLI framework contradiction (argparse vs typer+rich) and the `init`/`check` verb collisions the mechanical fold-in left open. |
| [`bmad-loop-forward-dependency-blindness.md`](bmad-loop-forward-dependency-blindness.md) | archived | `bmad-loop`'s picker has no `depends_on` concept and will dispatch a story whose own documented `**Deps:**` names a later epic — 3 instances fixed in marshal (the only affected station); `forward_dependency_check.py` closes the gap for good. |
| [`sprint-status-auto-promote.md`](sprint-status-auto-promote.md) | archived | A landed story doesn't reach the dashboard/tracked ledger until someone remembers to run `promote_sprint_status.py` + regenerate — bit the same session 3 times; wants the promotion triggered by landing itself, not a periodic human check. |
| [`loop-home-fleet-refresh.md`](loop-home-fleet-refresh.md) | archived | Refreshing every loop-home from `main` is a hand-run ritual with real judgment calls; the during-run push side is now the supervisor's own automatic push (FR-61) — `loop-push-watch` was retired 2026-08-10, `dashboard-watch` still requires manual start. |
| [`dream-to-code-model-self-verification.md`](dream-to-code-model-self-verification.md) | archived | Two follow-ups named at the 2026-07-23 Dream-to-Code restructure were never built: a `dream_chain_check.py --dreams` mode, and dogfooding `bmad-spec` against the model's own governing docs — both confirmed still genuinely missing. |
| [`jira-github-projects-sync.md`](jira-github-projects-sync.md) | specified | Bidirectional GitHub Projects V2 ↔ Jira Cloud sync, no third-party SaaS, zero-loop + idempotent — full v1 draft spec handed in whole, staged at `archive/docs/intake/jira-github-projects-sync/` (archived doctor 23.4). |
| [`conda-forge-expert-rebuild.md`](conda-forge-expert-rebuild.md) | specified | Reopens Mason's D-1 (wrap, never fork) for CFE itself only — Skill-Forge-authored rebuild, sliced along CFE's own 3 tiers, **parallel-run to a detector-enforced end cutover** (operator re-shape 2026-08-10; equivalence harness + dual-landing + endgame detector are what prevent atlas's ~29,000-unused-lines outcome). Epic 6 decomposes the pilot to its re-scope gate. |
| [`bmad-module-provisioning.md`](bmad-module-provisioning.md) | realized | Skill Forge/`bmad-builder` were hand-installed once (a 2026-07-17 ad-hoc commit driving an npm Installer class), not reproducibly — Steward's own `provision` duty (Epic 3) should wrap this the way it already wraps pixi/bmad-loop-worktree. |
| [`kedro-org-tooling-adoption.md`](kedro-org-tooling-adoption.md) | realized | `kedro-mcp` already resolved (wired, deliberately scoped); `kedro-skills`/`publish-kedro-viz`/`vscode-kedro` genuinely unused — owned by Atlas (the domain knowledge), mechanism leans on Steward's provisioning/deploy ducts. |
| [`herald-moments-2-4-live-backend.md`](herald-moments-2-4-live-backend.md) | specified | The full-spec version of Epics 8-10 (real database + webhook server + cron scheduler) that CI would call automatically — deferred in favor of a scaled-down local-storage/CLI-triggered first pass, since no persistent-service architecture exists anywhere in Herald today. |
| [`deck-family-currency.md`](deck-family-currency.md) | realized | The deck family stays current — every `Infographic standalone.html` re-derived from the tracked ledgers to one codified standard (six-act arc, full depth, inline diagrams; Unifying Strategy = structure, Warden = visual form), with a per-deck `facts.yaml` so no number ships without its source; eleven of fourteen posters are July stubs and the deep ones quote 2026-07 versions and counts. |
| [`deck-family-lockstep.md`](deck-family-lockstep.md) | specified | The whole deck family moves together — the Infographic head, Infographic Deck, exec summary and exports derive from the same `facts.yaml` as the poster (no more "standalone ahead"), the four chain decks join the standard and the registry, and the Design side is finally used as a design surface with a byte-exact pull. The three slices `deck-family-currency` deferred. |
| [`design-sync-loop.md`](design-sync-loop.md) | specified | **The Design sync loop — every Design project has a local twin, and one command keeps the whole family true.** Seeded, ruled and specified 2026-09-14 from the operator's four requirements the afternoon the second manual poster sweep (PR #1361) landed: every Design project local (presentations *and* the three design systems; two retired projects excluded by name), posters synced with **Design edits winning** then the ledger re-applied over marked literals, the deck family (trio, executive summary, Marp, PowerPoints — Marp-derived by default, `.potx`-filled where declared) re-derived from one `facts.yaml`, and a family page per deck with downloads on the one existing Pages deployment. `spec-design-sync-loop` `ready` (CAP-1..8, CAP-3..6 narrowed the same evening to deltas over the kernel's `pull`/`watch`/`push` and Epic 21's 21.3/21.5); herald Epic 23, six `backlog` stories (23.3/23.4 folded, reserved holes); 21.1 → 21.3 first, 23.8 last. Session-run, idempotent — a second run is a no-op. |
| [`secure-live-dashboards.md`](secure-live-dashboards.md) | specified | A reusable role-based live-dashboard pattern other dashboards adopt — filter-then-search by API shape, role-isolated audit trail, identity at the ASGI boundary (Django+Channels), and a static GitHub-Pages mode that is mutually exclusive with role isolation. Atlas's Vizro board is the first adopter, not the subject. |
| [`deferred-work-visibility.md`](deferred-work-visibility.md) | specified | `deferred_work_check` matches deferrals by `DW-*` id, but `bmad-build-auto` writes bare `- source_spec:` bullets with no id — **470 anonymous vs 33 identified**, so the gate covers 6.6% of what it claims. Both sides must move, in order: writer, then grandfathering, then the gate. Sequenced behind doctor 6-9. |
| [`artifact-chain-reconciliation.md`](artifact-chain-reconciliation.md) | realized | The pause-and-audit at 267/335, spanning **all of PyForge** — all 61 Dreams, all artifacts, all stages, all code: cited verdicts per story, done-claim sampling on all eight stations (completed ones first-class — three of the four queued decomposition chains extend them), AC→test coverage, two-sided correction pre-authorized (artifact↔code), nothing silent. CAP-1..8, serial: steward → mason → marshal → completed five → full inventory. |
| [`fleet-status-supervisor-fallback.md`](fleet-status-supervisor-fallback.md) | realized | `derive_home_state`'s first branch reports `"unsupervised"` whenever the supervisor sidecar pid is dead, before ever checking whether the underlying engine is still doing anything — collapsing "sidecar died, engine fine" and "actually needs a re-spin" into the same word. Wants a fallback liveness signal for the `supervisor_alive is False` case. **Realized** per frontmatter (2026-08-14 chain bookkeeping, `778f4acef9`). |
| [`marshal-token-economy.md`](marshal-token-economy.md) | specified | Marshal owns spend *brakes* (ceilings, idle ladder, cache TTL, tiering) but nothing that *shrinks* an iteration — five already-packaged instruments (headroom-ai wire compression, caveman output compression, codegraph structure graph, cocoindex incremental derived context, graphifyy planning graph via Scribe's GraphStore) wired in as a policy-rendered, Genesis-seeded, savings-metered context pipeline. Spec `ready`; decomposed as marshal Epic 28 (28.1–28.24, **all `done` 2026-09-01**). **Built, but every layer is off** — verified 2026-09-09: no `[context]` block is declared in any policy, so behaviour is byte-identical to pre-Epic-28, and the pinned benchmark has never been run. Three of five layers pay only on `factory dispatch` / build-auto, not on spin (`DW-FU-28-2`). See the 2026-09-09 addendum; next is `bmad-correct-course` → marshal Epic 33. Not `realized` until a benchmark artifact reports a measured saving. |
| [`token-economy-claude-session-path.md`](token-economy-claude-session-path.md) | archived | Claude spends the tokens the factory already learned to save — a **session path**, not a second compressor. Interactive Claude still pays the always-on doc tax; every station prefers Cursor so `headroom wrap claude` never launches (28.29: wire is Cursor-dead). Seeded 2026-09-16. Spec `draft` (three OQs). Do not mint an epic or flip `harness_preference` from the seed. **Folded into `marshal-token-economy` 2026-09-16** (operator-ruled consolidation; Spec stays live). |
| [`adaptive-model-tiering.md`](adaptive-model-tiering.md) | archived | FR-51's model-tiering chain (Story 6.1: `spec_difficulty.py`, `cli/spin.py`'s difficulty resolution, `render_policy_toml`'s tier-batching) is fully built and wired into `marshal factory spin` — but zero story declares a `difficulty:`, zero project populates a real `model_tier_map`, and nothing escalates a struggling retry's model. Wants the mechanism actually fed, plus a retry-triggered floor-raise. **Realized** per frontmatter (2026-08-14 chain bookkeeping, `778f4acef9`). **Folded into `marshal-token-economy` 2026-09-16** (operator-ruled consolidation; Spec stays live). |
| [`horizontal-run-concurrency.md`](horizontal-run-concurrency.md) | realized | `scm.max_parallel = 1` in Marshal's rendered policy isn't a Marshal default — vendored `bmad_loop` 0.9.0 hard-clamps any requested value to 1 at policy load ("Phase 5" fan-out unbuilt upstream), silently, with no upstream-register entry tracking the gap. Wants the clamp surfaced, the gap registered, and Marshal-side readiness assessed for when it ships. **Realized** per frontmatter (2026-08-14 chain bookkeeping, `778f4acef9`). |
| [`bmad-drift-new-artifact-shape.md`](bmad-drift-new-artifact-shape.md) | realized | `pyforge.doctor.sources.factory::classify()` HARD-fails any project file it has no rule for — working as designed (fourteen shapes 2026-07-28, eleven more 2026-08-08, each closed by one git-reviewed rule), but Marshal Story 7.6's spike report (`planning-artifacts/spike-0-copier-api-fit-report.md`, PR #427) is a shape it hasn't seen yet, HARD-failing `detectors-ci`. Wants one more classification rule for the spike-report shape. **Realized** per frontmatter (2026-08-14 chain bookkeeping, `778f4acef9`). |
| [`quick-dev-reconciliation.md`](quick-dev-reconciliation.md) | realized | A story hand-implemented via `bmad-quick-dev` is invisible to Marshal — zero references in `pyforge-marshal`'s own source, `sprint-status-ledger.yaml` only ever advances on a `bmad-loop` completion signal, and Epic 4's spec-promotion/durability guarantees never apply to it. Wants quick-dev completions reconciled into the same tracked ledger/dashboard flow a loop-landed story gets, so an operator can mix modes within one station without Marshal's state drifting from reality. **Realized** per frontmatter (2026-08-14 chain bookkeeping, `778f4acef9`). |
| [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md) | specified | Evergreen Foundry Dream (hub-and-spoke, eight stations). Read **Grounding** + **How to read** first. Living file = build-target mermaid; historical topology / tree / fleet evidence in [`archive/pyforge-unifying-strategy-2026-08-23-topology.md`](archive/pyforge-unifying-strategy-2026-08-23-topology.md). Host work is **`pap:CAP-1`..`6`** (`extends` `spec-python-agent-platform`); Unifying **CAP-1..19** are a different set. CAP-1..18 closeout stands; CAP-19 / Epic 34 shipped 2026-08-26. **Live build target is § *Cutover to `python-foundry`*** — `spec-python-foundry-cutover` (`fnd:CAP-1..10`), steward Epic 44, 14 of 15 stories `blocked` by operator gate, and Epic 47's P1–P18 readiness lines gate 44.3. Red-team Epics 40–43 `done` (43.7 `backlog`). **Currency review 2026-09-09** (`research/currency-review-pyforge-unifying-strategy-2026-09-09.md`): code healthy, 28/28 detectors; document tier corrected the same day; contractual residue (≤400-line constraint, CAP-axis namespace, five open `DW-RT` directives, Single-Spec merge) awaits `bmad-correct-course`. Q5 published 2026-09-15 on [`build-league-scorecard.md`](build-league-scorecard.md) (Epic 62 catalog). **Consolidation 2026-09-25** (§ *Where next*): PRs #1563 / #1564 / #1576 and the BMAD-method whitepaper folded in one PR — `fnd:CAP-12..15` (laptop SBOM, checkable SBOM, dossier as control plane, estate-first instruction surface), `fnd:CAP-7` retired (**no archive of A**); decomposed as steward Epic 67, herald 26.1, scribe 21.1. |
| [`htap-query-plane.md`](htap-query-plane.md) | archived | Absorbed into [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md) § *The query plane* — not a sibling chain. |
| [`platform-image-one-pixi-env.md`](platform-image-one-pixi-env.md) | specified | One frozen `python-agent-platform` env for the platform image — drop Containerfile `pip install --no-deps`; overlap fails at lock; pixitainer-docker re-eval vs Story 10.3. Spec `ready`. |
| [`build-league-scorecard.md`](build-league-scorecard.md) | specified | Operator approved the eight already-counted signals on 2026-09-15 (Dream § Operator rulings), with on/off/archived config. Spec `ready` (CAP-1..4; CAP-4 later slot). Steward Epic **62** (62.1–62.3 `backlog`) is the marshal dispatch home. |
| [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md) | specified | Every story pays the identical review cost regardless of risk — `gate_mode = "none"` only ever skips the human approval gate, never the independent reviewer, and `max_review_cycles`/`max_followup_reviews` are flat, repo-wide ceilings. `classify_doc_only_declaration` (Story 2.4) is real precedent for classifying a story's risk shape, but it feeds gate pass/fail, not review scheduling. Wants a similar classification to inform review *depth* for low-risk stories, without reproducing the `DW-AD23-3` incident (a lower `max_followup_reviews` cap silently dropped real recommended follow-ups). **Demoted `realized` → `specified` 2026-09-09** (fleet readiness, mars-B): the 2026-08-14 flip was chain bookkeeping (`778f4acef9`); `classify_review_tier` / `resolve_review_cycles` have **zero callers** outside `core/gate.py` and `tests/unit/test_gate.py`, so the capability is built and not in effect. Vessel: marshal Epic 33's wiring story (steward index row 49.9). |
| [`golden-path-conda-blind-spot.md`](golden-path-conda-blind-spot.md) | archived | Folded into [`pyforge-warden.md`](pyforge-warden.md) 2026-09-17 (one-chain). `golden-path-promotion`'s Warden verdict is structurally `indeterminate` — it scans a bare unresolved `pixi.toml` (Warden's lock reader has no per-environment selector for this repo's multi-env `pixi.lock`), no CI job provisions the offline OSV database, and the offline OSV database is provisioned by no CI job. *(Corrected 2026-09-09, fleet readiness: the row previously claimed `platform-deploy` "gates on the record existing, not `warden_status == \"clean\"`" — **false since `1016f4e763`**; `scripts/platform-deploy-verify-promotion.py:31` fails closed on `status != "clean"`, and it is the only fail-closed promotion gate there is.)* Retro action item 8 (2026-09-04). |
| [`package-inventory-eligibility.md`](package-inventory-eligibility.md) | archived | Folded into [`pyforge-warden.md`](pyforge-warden.md) 2026-09-17 (one-chain). One provenance trail and one eligibility answer, from any source — reminted as spec-pyforge-warden CAP-13..15. |
| [`compliance-factory-web-face.md`](compliance-factory-web-face.md) | archived | Folded into [`pyforge-warden.md`](pyforge-warden.md) 2026-09-17 (one-chain). Upload a manifest, watch the engines analyze it — reminted as spec-pyforge-warden CAP-16..17. |
| [`pyforge-warden-compliance-gates.md`](pyforge-warden-compliance-gates.md) | archived | Folded into [`pyforge-warden.md`](pyforge-warden.md) 2026-09-17 (one-chain). Already archived as a duplicate (2026-08-02); remains a retirement record. |
| [`pixi-candidate-currency.md`](pixi-candidate-currency.md) | realized | Two mirrored ledgers, one Dream. Candidates: 44 commented-out `pixi.toml` packages audited — 37 already have a local recipe, 6 fully resolved this session (2 added; `headroom-ai`/`dbt-*`/`caveman` root-caused as blocked). Currency: **all 111** ACTIVE dependencies stuck below conda-forge latest evidence-verified, none left as hypothesis — 9 root-caused directly (incl. `conda-recipe-manager==8.2.1`, the SAME pin blocking `headroom-ai` on the candidate side), 1 platform-gap solver-confirmed (`pyarrow-core` on osx-arm64), and the remaining 93 traced through their full blocking chain to 34 distinct terminal packages (each independently confirmed already at ITS OWN latest) — sorted by blast radius (`aws-sdk-cpp` alone explains 13), plus 28 same-recipe-family siblings, a 4-package multi-producer ecosystem diamond (`grpcio`/`libabseil`/etc.), and 2 deliberate tradeoffs. Every finding names its exact culprit + spec, never "something conflicts." |
| [`bmad-eval-quality.md`](bmad-eval-quality.md) | realized | `eval-quality` (bmad-code-org) joins the bmad-suite as its 14th member — **tag-sourced since 1.3.0; live at `1.4.1` with the pixi pin `>=1.4.1`** (the original `0.2.0.dev0 @ 3172162f` commit pin is historical record, retired once upstream shipped real tags); then one Behavioral Evaluation Contract runs the `edge-case-hunter` review layer twice — clean arm and one planted `file:line` defect — to measure whether the reviewer bmad-loop relies on actually catches it. Contracts compile only as `kind: api`; the driver is the adapter. Operator decisions 2026-09-05: name + source locked. **`specified` → `realized` 2026-09-09** (fleet readiness, Class B): Epic 45 2/2 `done`, CAP-1 on the channel + pin, CAP-2's twin-run exercised live at 3 trials/arm. |
| [`bmad-suite-channel-product.md`](bmad-suite-channel-product.md) | realized | The private-channel bmad-suite as a governed product — 13 members always latest, dual-path installable (pixi + native), modules provisioned, the seven stages connected (`pipeline-truth` → `advance` → metapackage); first governed refresh 2026-09-05. |
| [`bmad-611-era-alignment.md`](bmad-611-era-alignment.md) | realized | PyForge stays aligned to the installed BMAD era: the 6.11 round shipped as marshal Epic 25 (retired-ID guard, memlog migration, 0.11 policy + status parity, living-doc owner); each era shift reopens a round — 6.12.0 minted CAP-8..11 on 2026-09-05. |
| [`intelligence-hub.md`](intelligence-hub.md) | realized | Seed from the OpenTeams whitepaper *The Distributed AI Economy* (Oliphant, Aug 2026, Rev 9), distilled section-complete: owned Intelligence Hubs on Nebari/Nebi, Frames · Cogs · Ops, the Guards · Gates · Tracks accountability plane, Organizational Memory, the four-class marketplace, the Desktop/Web Application. Maps each abstraction to its nearest PyForge surface and lists seven candidate shapes for the Spec; **no adoption decided** — `bmad-spec` under steward chooses. Research backlog closed: RB-1 (Frame Spec v0.2.0 is published) and RB-2 (`nebari` + `nebi` on conda-forge, NIC absent) 2026-09-06; RB-3 (field guide, `nebari-dev` pack maturity from `pack-metadata.yaml`, the `NebariApp` CRD) 2026-09-09, with a candidate approach for aligning the Unifying Strategy recorded, not decided. Shape 5's local recipes (`nebari-infrastructure-core` 0.14.0, `nebari-frames` 0.1.7) already landed 2026-09-07. PDF not tracked (sha256 in the Dream). |
| [`bmad-method-core-upgrade.md`](bmad-method-core-upgrade.md) | specified | BMAD-METHOD's own core stays current, not stuck at whatever version got installed — steward runs `npx bmad-method install`/`@next` against THIS repo (not a fresh clone), reconciles `_bmad/bmm/**`/`_bmad/core/**` against the repo's own customizations (`_bmad/custom/**`, the active-symlink mechanism, locally overridden skills) and reports new/changed/deprecated — a repeatable upgrade path instead of a from-scratch manual effort per release. Steward Epic 14 (14.1–14.8 done); Spec stays `in-progress` by operator directive, open questions Q2–Q5 answered/relayed 2026-09-06. |
| [`bmad-suite-install-class-wiring.md`](bmad-suite-install-class-wiring.md) | realized | Non-module bmad-suite pieces are provisioned by install class — not forced through `--module`: the **whole** SelfExplainML suite live on a fresh clone without a session-scratchpad ritual; `--module skf` refused as a non-goal. Steward Epic 31 (3/3 done 2026-08-24); status flipped 2026-09-06, remaining module wiring now driven by [`bmad-suite-lifecycle.md`](bmad-suite-lifecycle.md). |
| [`bmad-suite-metapackage.md`](bmad-suite-metapackage.md) | realized | One conda metapackage installs the whole SelfExplainML bmad-suite at latest — `conda install -c SelfExplainML bmad-suite` pulls all 13 `install-matrix.md` members at pipeline-truth versions; manifest + metapackage version bump in one reviewable commit. Steward Epic 39 (4/4 done 2026-09-01); `bmad-suite 2026.9.5` was the first governed refresh (2026-09-05, eval-quality seated, WDS retired). |
| [`bmad-method-version-drift.md`](bmad-method-version-drift.md) | realized | Doctor notices when BMAD-METHOD's own installed core falls behind upstream — declared floor vs the actually-installed `_bmad/bmm/**`/`_bmad/core/**` vs latest upstream, as an ambient read-only signal instead of an operator remembering to check. Core CAP-1..3 as doctor Epic 10 (2026-08-16); suite extension CAP-4 as doctor Epic 14; the 7-of-13 suite-mapping residual relayed to doctor Epic 20 (2026-09-06). |
| [`bmad-loop-baseline-drift.md`](bmad-loop-baseline-drift.md) | realized | A story's orchestrator-recorded baseline can never drift out from under its own worktree — `task.baseline_commit` silently moves to a later commit mid-dev, so honest, reviewed work is rejected by its own verify gate and deferred while the run dispatches the *next* story; wants the drift impossible, or at minimum loud and self-healing. |
| [`bmad-loop-intent-gap-work-preservation.md`](bmad-loop-intent-gap-work-preservation.md) | realized | An intent-gap revert can never discard real work without a recoverable trace — today an `intent_gap` halt correctly reverts but leaves no `attempt-preserve/*` branch and no `changes.patch` (the deferred-story path already preserves every attempt via `scm.keep_failed`); wants the same preservation guarantee for the intent-gap path. |
| [`bmad-loop-liveness-footgun.md`](bmad-loop-liveness-footgun.md) | realized | Nobody has to hand-parse `engine.pid` to answer "is this run alive?" — since 0.9.0 the file is `"<pid> <identity>"`, so the naive `ps -p $(cat engine.pid)` silently reads as "dead"; the tri-state liveness API in `runs.py` is correct, but nothing outside `bmad_loop` is pointed at it. |
| [`bmad-switch-scope-enforcement.md`](bmad-switch-scope-enforcement.md) | realized | A BMAD write can never land in the wrong project's artifacts, mechanically — the two gitignored compatibility symlinks, the `.active-project` marker and the caller's intent are checked two different ways in two different places, and neither guarantees the write lands in the project the caller meant. |
| [`bmad-suite-lifecycle.md`](bmad-suite-lifecycle.md) | specified | The whole bmad-suite is wielded, kept current per release by one cadence runbook, and carried cutover-ready into the foundry — adoption register (13 members: TEA full adoption, BMB beside skf, utility-skills, manticore for Herald, labs skill-by-skill, eval-quality pilot), shim retirement now, 17 cutover prerequisites; steward Epics 46/47 + relays to seven stations (2026-09-06). |

**Applications**

| Dream | Status | What it is |
|---|---|---|
| [`presenton-pixi-image.md`](presenton-pixi-image.md) | archived | Presenton repackaged conda-native + air-gapped for OpenShift in regulated enterprises. |
| [`unity-data-stack.md`](unity-data-stack.md) | archived | The enterprise innersource platform — a python-first shared monorepo (Constitution + working pixi root recovered from gists). |
| [`wasm-analytics-stack.md`](wasm-analytics-stack.md) | archived | Wasm-first analytical data stack on OpenShift — WASI-sandboxed Python, dlt+dbt, OTel/OL, Restricted-SCC hardened. |
| [`capability-effect-check.md`](capability-effect-check.md) | dreamt | A capability is not done until something exercises it. Relayed 2026-09-09 from steward Story 49.2 by the fleet-readiness decision batch (§ 2.3 C8): the **criterion** stays on `spec-pyforge-unifying-strategy`'s `verified:` column, the **implementation** comes home to doctor's own chain like every other doctor Source. Cheapest effect test the pass found: "has a caller outside its own test file". Input is every station's Specs, not one CAP list — the pass's five worst cases were steward's own satellites. Advisory, never a second PR verdict. |
| [`status-body-consistency.md`](status-body-consistency.md) | dreamt | A document's prose agrees with its own status. **2026-09-16 inbox disposition:** the only new Spec→Story still worth minting (Spec still `draft`; answer the scope OQ, then one doctor epic). See `research/fleet-inbox-disposition-2026-09-16.md`. Raised 2026-09-09 by the fleet-readiness pass (§ 2.4 D1) after **six documents in one sweep** were found contradicting their own frontmatter (herald ×2, scribe ×2, charter, unified-container); `bmad-drift-check` polices vocabulary and counts, never narrative. Ambient, warn-only, fail-open — the `sibling-dreams-drift` shape — and the join must be proven on live data before the story closes. |
| [`run-state-one-publisher.md`](run-state-one-publisher.md) | specified | Run state is a service — one publisher, fed by both marshal supervisors, carries bmad-loop/dispatch run truth to the host's supervisor store; marshal and doctor read the plane, not `~/.bmad-loops`. Seeded 2026-09-12 from the last OPEN CAP-17 realization-gap row (steward 49.8 + marshal 33.4). |
| [`mcp-host-real-station-tools.md`](mcp-host-real-station-tools.md) | realized | The mcp-host sidecar (`spec-mcp-era-isolation` slice 1) proxied every station's `/stations/<name>/mcp` call correctly but only answered with a generic `station_face()` identity stub. Found 2026-09-12 chasing CAP-3's live-run proof; realized the same day — the sidecar now hosts marshal's real held-loop tools via a minimal Django settings module, proven with a real live run appearing on `/runs/` after the publishing workstation exited. |
| [`library-catalog-manifest-sync.md`](library-catalog-manifest-sync.md) | realized | `docs/reference/library-llms-full.md` and `llms_full_check.py` only ever read root `pixi.toml`, so each `pyforge-*` station's own second manifest (`src/shared/packages/pyforge-<station>/pixi.toml [package.run-dependencies]`, the one `pixi-build-python` actually builds from) is invisible to both. Found 2026-09-12 auditing the catalog's own scope: seven real, already-shipped station deps (`packaging`, `jsonschema`, `psutil`, `attrs`, `packageurl-python`, `license-expression`) never appear in root `pixi.toml` and are undocumented. Seeded from [[pyforge-unifying-strategy]]'s Realization log; generalizes Story 12.1's pixi-wiring precedent into a standing detector fix. |
| [`spec-surface-overlap-tolerance.md`](spec-surface-overlap-tolerance.md) | realized | `spec-surface-check`'s drift half checks every governing spec of a changed file independently, with no awareness that a file is routinely governed by more than one spec at once — a station's kernel spec and a narrower, active spec both matching it. Found fixing 178 `drift-presumed` findings across 17 specs (2026-09-12, PR #1288, data-level fix); this Dream is the root-cause fix so the same class of noise stops recurring as new narrow specs get minted under existing kernel specs. |
| [`dispatch-tier-routing-fails-safe.md`](dispatch-tier-routing-fails-safe.md) | archived | The FR-51 model-tier resolver could silently launch a hybrid, broken dispatch — a real adapter binary paired with another provider's model string it was never meant to receive — producing an instant CLI crash with zero tokens spent that bmad-loop reported only as "deferred." Found 2026-09-12 chasing three identical silent failures for marshal Story 28.29: `model_tier_map.heavy.dev = "composer-2.5-fast"` (a Cursor-only model, all eight stations) resolved to no harness, so the base `claude` adapter launched with an invalid model. Realized same day: `render_policy_toml` now cross-checks each stage's model against the declared cost catalog and skips a cross-provider mismatch; `resolve_stage_candidate` no longer fabricates an answer when nothing is available; all 8 stations' `model_tier_map` reverted to the plain sonnet/opus baseline. **Folded into `marshal-token-economy` 2026-09-16** (operator-ruled consolidation; Spec stays live). |
| [`cursor-native-tier-map.md`](cursor-native-tier-map.md) | archived | The campaign runs in Cursor. Re-point `model_tier_map` to explicit `{ harness = "cursor", model = "…" }` tables (easy composer-2.5, medium grok-4.6, heavy composer-2.5-fast) before any unattended drain. Fail-safe unchanged. Wave driven from this IDE. Story 33.15. **Folded into `marshal-token-economy` 2026-09-16** (operator-ruled consolidation; Spec stays live). |
| [`suite-scaffold-and-mybmad-sidecar.md`](suite-scaffold-and-mybmad-sidecar.md) | specified | 2026-09-06 skip rows flip: `bmad-module-template` is an authoring tool beside `bmad-builder`; `mybmad-dashboard` is a sidecar on **estate Postgres schema `mybmad` + estate Keycloak/OIDC**, never `/console/`, no second login in `src/platform/`. Steward Epic 52 / Story 52.1. |
| [`foundry-regenerate-not-fold.md`](foundry-regenerate-not-fold.md) | specified | Launch foundry by regenerating core/steward/marshal from Frames + a thin test oracle — not folding `src/shared/packages/`. Epic 54; 44.4/44.5 parked. CLI+MCP only; invent in local-recipes. |
| [`foundry-capability-ledger.md`](foundry-capability-ledger.md) | specified | Strangler routing table: rebuild / retire / dated A-only / B-only. Extract inventory. Epic 55; kit with 53.5 Frames + 54.1 case-list. |
| [`platform-dev-boots-local.md`](platform-dev-boots-local.md) | specified | `platform-dev` loads `config.settings.local` (toolbar on that feature only). Steward Epic 56. |
| [`scribe-recall-mode-wiring.md`](scribe-recall-mode-wiring.md) | specified | Story 16.1 shipped `--mode`. Wire Marshal retrieve and session agents to `--mode planning`. Portal mode stays optional. Story 18.1. |
| [`coverage-gate-independence.md`](coverage-gate-independence.md) | specified | **A check that can red a station's PR must not ship inside that station's package.** Found 2026-09-14 by an investigation aimed elsewhere: marshal's verdict lattice was *cleared*, and the violation was one directory up — `pyforge/marshal/coverage_gate.py` + `coverage_thresholds.toml` ship **inside** marshal while `coverage-gates.yml` runs that gate over all eight stations with no `continue-on-error` (Charter §6 verbatim, scope ruled **broad**). Every station-side home failed (`pyforge-core`, `pyforge-testing-kit` *and* `scripts/` are marshal-governed; doctor is advisory), so the question was "who owns a policy that binds all eight". **Ruled the same day:** `owner: guild` by the narrow Charter §5 amendment (a gate that judges all eight Smiths is the Guild's — the only Dream besides the Charter to carry `guild`); Spec at `docs/governance/spec-coverage-gate-independence/`, `ready`, all five questions answered; the mechanism stories are doctor's (§5 outcome/mechanism rule). Sibling ruling: `ledger-regression` is now a scoped blocking step in `detectors.yml`, so the judge's verdict on Marshal has force. |
| [`one-chain-per-station.md`](one-chain-per-station.md) | specified | **One Dream, one Spec, one PRD, one architecture, one epic chain — per station.** Seeded 2026-09-16 the morning the token-savings fold (PRs #1382/#1383) proved the shape on marshal. Fleet: 171 Dreams / 172 Specs for eight stations while PRD, spine and epics are already one-per-station; the 2026-08-08 61-Dream fold regrew in five weeks because the minting rules compose into a Dream+Spec pair per effort. Six operator rulings: Dream-**append**-first with a closed `fold-exemption:` list and a `chain-sprawl-check` detector; 8 station chains + the Guild's; fold **everything** (shipped included; the decision record survives, derived bodies are disposable); the PRD stays and **derives** from the Spec (FR ← CAP); the fold is the foundry on-ramp; **marshal is the pilot**. `owner: guild` (second instance of the 09-14 §5 shape — the gate grades every Smith's row; Dream-append-first is a *reading* under Charter CAP-1, not an amendment; carries the first `fold-exemption: governance`). Spec **`ready`** at `docs/governance/spec-one-chain-per-station/` — the three OQs ruled the same day: no fifth Dream status (station Dreams read `specified` by the existing rule once their Spec is `in-progress`); `pyforge-core` and the testing kit are marshal-owned `cross-station-seam` exemptions; the Charter's only ritual is CAP-1. Operator constraint: **evergreen standard > historical accuracy > implementation**, eventual consistency station by station, portable to pyforge-foundry; a fold is a **rebase** (CAPs, epics and stories renumber sequentially across all four BMAD phases, re-key map in the PR); **marshal → steward → herald → the rest in parallel**. CAP-9: one companion page, `CHAIN-STANDARD.md` — hierarchy, relations, sequence, one status enum per tier, one name per concept, one id family per job, the fold checklist — every existing ruling with its grandfathering removed. |
| [`self-hosted-bmad-marketplace.md`](self-hosted-bmad-marketplace.md) | specified | Operator approved Q1–7 on 2026-09-15 (Dream § Operator rulings). Spec `ready` (CAP-1..7; CAP-5 later slot; CAP-6 Layer 3 non-goal). Steward Epic **60** (60.1–60.4 `backlog`) is the marshal dispatch home. |
| [`work-passports-dated-extracts.md`](work-passports-dated-extracts.md) | specified | Operator approved Q1–6 on 2026-09-15 (Dream § Operator rulings). Spec `ready` (CAP-1..7; CAP-6/7 later slots). Steward Epic **61** (61.1–61.5 `backlog`) is the marshal dispatch home. Not Epic 8. |
| [`docs-shelf-alignment.md`](docs-shelf-alignment.md) | specified | Residue of realized [[general-docs-consistency]] after Epic 22. Spec `ready` 2026-09-14: workflow specs stub+how-to (not a full move); brownfield extract-then-stub; new Doctor source (not an extension of `general_docs_consistency`); doctor Epic 23; do not mint empty `docs/dashboard/vizro/`. |
| [`vocabulary-one-name-one-job.md`](vocabulary-one-name-one-job.md) | specified | Operator accepted Q1–20 on 2026-09-15 (Dream § Operator rulings). Spec `ready` (CAP-1..8; CAP-4 already met). Steward Epic **59** (59.1–59.7 `backlog`) is the marshal dispatch home. |
