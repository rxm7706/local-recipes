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
  skills + phases run autonomously via **bmad-loop** and **bmad-dev-auto**.
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

  **There is deliberately no `building` state.** Status declares what *exists*;
  the console *derives* what is happening from live build lines. Hand-maintained
  activity-tracking rots: `pyforge-warden` read `in-spec` while shipped 31/31,
  and `deckcraft` read `dreamt` while holding both a deck and a Spec — both
  found and fixed on 2026-07-25. `bmad-drift-check` now emits `dream-vocab` on a
  retired or invented value.

- **`owner:`** names the **station** accountable for carrying the Dream all the
  way to code — the through-line, propagated by the console onto every
  downstream row (Fleet, Backlog, In Build, Realized, Pitch, Archived). Owning
  is **not** becoming: the station is the post, not the product, so Atlas owning
  [`unity-data-stack.md`](unity-data-stack.md) does not mean it ships as
  `pyforge-atlas`. `guild` is reserved for the two Dreams that *precede* the
  stations ([`pyforge-charter.md`](pyforge-charter.md),
  [`pyforge-genesis.md`](pyforge-genesis.md)); `bmad-drift-check` emits
  `dream-unowned` for anything else claiming it. *(Replaces `crew`, which was
  both retired vocabulary and a non-answer — "the Guild owns it" means no
  station does.)*

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

25 Dreams as of 2026-07-23 (3 born Dream-first — the regenerable factory among
them; 17 retro-seeded from a complete
repo + Design-workspace audit — the factory console among them; 3 persona
dreams added by ownership audits — Scribe + Steward when the crew grew 6 → 8,
Herald's charter when the ownership review re-scoped it; 2 recovered from the gist audit (a third, local-ai hardware, was judged out-of-repo scope and archived)). **No-straggler policy:** every BMAD project, deck, Design
project, and spec maps to exactly one Dream; the herald CLI's status capability
(CAP-3) flags any unlinked Design project permanently.

**Foundations**

| Dream | Status | What it is |
|---|---|---|
| [`pyforge-charter.md`](pyforge-charter.md) | pitched | **The founding Dream** — the PyForge Guild: eight Smiths, one "Dream to Code" pipeline. Master vision deck: `presentations/pyforge-genesis/`. |
| [`pyforge-genesis.md`](pyforge-genesis.md) | pitched | Genesis as master idea + **the seed**: init a new repo / adopt brownfield with the whole operating model (origin: `archive/docs/bmad-setup-plan.md`). |
| [`sentinel.md`](sentinel.md) | dreamt | **The ancestor** (2026-04): the AI Software Factory — "the graph is the product"; unbuilt core, stranded artifacts to repatriate; descendants credited. |
| [`design-code-bridge.md`](design-code-bridge.md) | realized | Design + Code as one surface — seed/design/pull, zero downloads; herald CLI specced (5 CAPs). |

**Persona products**

| Dream | Status | What it is |
|---|---|---|
| [`packaging-factory.md`](packaging-factory.md) | realized · perpetual | The origin dream: the AI-assisted conda-forge factory (Mason) — CFE skill, 769 feedstocks, campaigns; frontier: multi-ecosystem autotick, smart test extractor. |
| [`pyforge-atlas.md`](pyforge-atlas.md) | realized | The intelligence layer reborn as Kedro/Dagster/DuckDB dataflow an agent workforce maintains (waves 0–H shipped, PRs #58–#105). |
| [`pyforge-warden.md`](pyforge-warden.md) | specified | The compliance gate that never false-greens — six axes of dependency trust (25/31 built). |
| [`pyforge-marshal.md`](pyforge-marshal.md) | realized | Graduated autonomy a human can trust — bmad-loop/dev-auto + gates + escalation; proved on atlas + warden. |
| [`pyforge-mason.md`](pyforge-mason.md) | specified | **Mason** — the Artisan Builder's station: the `mason` CLI (recipe / package / environment), seam-by-capability over the CFE craft; distinct from [`packaging-factory.md`](packaging-factory.md), the practice he tends. |
| [`pyforge-doctor.md`](pyforge-doctor.md) | pitched | One bedside manner over the fleet's vitals — pre-flight diagnostics + continuous monitoring + prescriptions (a consolidation of existing instruments). |
| [`pyforge-herald.md`](pyforge-herald.md) | pitched | The outward voice + design surface — decks, bridge, telemetry imagery, proclamations (charter re-scoped 2026-07-23: infrastructure → Marshal). |
| [`pyforge-scribe.md`](pyforge-scribe.md) | pitched | The inward voice — team knowledge captured, curated, compiled into the graph, answerable (owns team-memory + sentinel's core). |
| [`pyforge-steward.md`](pyforge-steward.md) | pitched | The estate the factory stands on — provisioning, deployment, credential lifecycle, budgets, incident response. |

**Practices**

| Dream | Status | What it is |
|---|---|---|
| [`fleet-stewardship.md`](fleet-stewardship.md) | realized · perpetual | Tend every touchable feedstock: refresh tracks, platform expansion, failure remediation — recurring waves, never finished. |
| [`upstream-discovery.md`](upstream-discovery.md) | dreamt | Sense what the world is building (trending + org audits, atlas Phase T) and package it before it's asked for. |
| [`regenerable-factory.md`](regenerable-factory.md) | realized | Backfill Dream→PRD→spec chains under every realized surface (BMAD brownfield) so the factory can change any code through the pipeline; drift checks on all code; the regeneration drill as proof. |

**Capabilities**

| Dream | Status | What it is |
|---|---|---|
| [`agent-portability.md`](agent-portability.md) | dreamt | BMAD on any agent (Devin/Copilot/Claude/Cursor); planning on flat-rate subscriptions; the Portability contract enforced. |
| [`team-memory.md`](team-memory.md) | dreamt | Shared, version-controlled team memory — what the team knows, every agent knows. |
| [`enterprise-airgap.md`](enterprise-airgap.md) | realized | The factory behind the firewall — JFrog routing + air-gap-by-design; frontier: presenton, deckcraft, warden's registry perimeter. |
| [`modernist-identity.md`](modernist-identity.md) | realized | One visual language for everything PyForge — the Modernist DS across 7 decks; frontier: the design-tokens round-trip (Figma↔JSON↔POTX). |
| [`agentic-sdlc-autonomy.md`](agentic-sdlc-autonomy.md) | pitched | The four views of agentic autonomy (taxonomy/process/architecture/environment) — the white paper + the 45-slide deck + our live L3 evidence. |
| [`factory-console.md`](factory-console.md) | realized | The whole pipeline on one public page — every Dream + lifecycle stage (Dreamscape board), live epic/story progress, nothing hand-maintained (GitHub Pages). |
| [`fidelity-enforcement.md`](fidelity-enforcement.md) | dreamt | A contract is only a contract if something fails against it — every tier boundary gated in both directions; generalizes §7's law from the Guildhall to the whole chain. |
| [`durable-runs.md`](durable-runs.md) | dreamt | Work survives the machine that made it — no commit, spec or verdict exists only on one disk; the loop pushes at its own stage boundaries. |
| [`pr-lifecycle.md`](pr-lifecycle.md) | dreamt | A story lands itself — open, label, wait for checks, merge, resync; landing rules declared as policy instead of remembered. Resolves marshal open question #10. |
| [`one-front-door.md`](one-front-door.md) | dreamt | Marshal drives everything BMAD installs — one composed surface over 11 packages, 51 skills, 10 detectors and the engine; the runtime half of [`genesis-installer`](genesis-installer.md). **Draft for refinement.** |
| [`unified-container.md`](unified-container.md) | dreamt | All 8 stations in one Docker/Podman image — one boot, the whole Guild available; motivated by the 2026-08-02 per-station architecture consolidation. |
| [`bmad-output-hygiene.md`](bmad-output-hygiene.md) | dreamt | One fabricated bulk commit stamped dead test scaffolding, a hollow sprint-status template, and (in places) fake test-architecture/README content across all 8 stations, inconsistently fixed since — a 5-agent audit mapped exactly what's real vs. debris. |
| [`dashboard-project-path-derivation.md`](dashboard-project-path-derivation.md) | dreamt | The dashboard builds links/`have` checks by gluing a roster slug straight onto a project directory — broke twice already for absorbed/dissolved satellites; wants one derivation helper instead of one override dict per occurrence. |
| [`genesis-installer-name-retirement.md`](genesis-installer-name-retirement.md) | dreamt | genesis-installer should retire completely — not just renumbered, but a full PRD/architecture/epics rewrite that actually decides the CLI framework contradiction (argparse vs typer+rich) and the `init`/`check` verb collisions the mechanical fold-in left open. |
| [`bmad-loop-forward-dependency-blindness.md`](bmad-loop-forward-dependency-blindness.md) | realized | `bmad-loop`'s picker has no `depends_on` concept and will dispatch a story whose own documented `**Deps:**` names a later epic — 3 instances fixed in marshal (the only affected station); `forward_dependency_check.py` closes the gap for good. |
| [`sprint-status-auto-promote.md`](sprint-status-auto-promote.md) | dreamt | A landed story doesn't reach the dashboard/tracked ledger until someone remembers to run `promote_sprint_status.py` + regenerate — bit the same session 3 times; wants the promotion triggered by landing itself, not a periodic human check. |

**Applications**

| Dream | Status | What it is |
|---|---|---|
| [`deckcraft.md`](deckcraft.md) | dreamt | Air-gapped editable-PPTX/Marp/infographic pipeline from primitives — the family's designated PPTX engine. |
| [`presenton-pixi-image.md`](presenton-pixi-image.md) | dreamt | Presenton repackaged conda-native + air-gapped for OpenShift in regulated enterprises. |
| [`unity-data-stack.md`](unity-data-stack.md) | dreamt | The enterprise innersource platform — a python-first shared monorepo (Constitution + working pixi root recovered from gists). |
| [`wasm-analytics-stack.md`](wasm-analytics-stack.md) | dreamt | Wasm-first analytical data stack on OpenShift — WASI-sandboxed Python, dlt+dbt, OTel/OL, Restricted-SCC hardened. |
