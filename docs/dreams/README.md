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
  owner: herald | marshal | atlas | warden | mason | doctor | scribe | steward | crew
  status: seeded | in-deck | in-spec | realized
  ---
  ```

- **`owner:`** names the crew station accountable for the Dream (`crew` for
  genesis-level and application Dreams the whole pipeline builds). Stamped
  across all Dreams in the 2026-07-23 ownership review (which also re-scoped
  Herald: BMAD multiproject machinery + agent portability → Marshal). The
  Dreamscape board on the program console surfaces it.

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
| [`pyforge-charter.md`](pyforge-charter.md) | in-deck | **The founding Dream** — the PyForge Guild: eight Smiths, one "Dream to Code" pipeline. Master vision deck: `presentations/pyforge-genesis/`. |
| [`pyforge-genesis.md`](pyforge-genesis.md) | in-deck | Genesis as master idea + **the seed**: init a new repo / adopt brownfield with the whole operating model (origin: `archive/docs/bmad-setup-plan.md`). |
| [`sentinel.md`](sentinel.md) | seeded | **The ancestor** (2026-04): the AI Software Factory — "the graph is the product"; unbuilt core, stranded artifacts to repatriate; descendants credited. |
| [`design-code-bridge.md`](design-code-bridge.md) | realized | Design + Code as one surface — seed/design/pull, zero downloads; herald CLI specced (5 CAPs). |

**Persona products**

| Dream | Status | What it is |
|---|---|---|
| [`packaging-factory.md`](packaging-factory.md) | realized · perpetual | The origin dream: the AI-assisted conda-forge factory (Mason) — CFE skill, 769 feedstocks, campaigns; frontier: multi-ecosystem autotick, smart test extractor. |
| [`pyforge-atlas.md`](pyforge-atlas.md) | realized | The intelligence layer reborn as Kedro/Dagster/DuckDB dataflow an agent workforce maintains (waves 0–H shipped, PRs #58–#105). |
| [`pyforge-warden.md`](pyforge-warden.md) | in-spec | The compliance gate that never false-greens — six axes of dependency trust (25/31 built). |
| [`pyforge-marshal.md`](pyforge-marshal.md) | realized | Graduated autonomy a human can trust — bmad-loop/dev-auto + gates + escalation; proved on atlas + warden. |
| [`pyforge-mason.md`](pyforge-mason.md) | in-spec | **Mason** — the Artisan Builder's station: the `mason` CLI (recipe / package / environment), seam-by-capability over the CFE craft; distinct from [`packaging-factory.md`](packaging-factory.md), the practice he tends. |
| [`pyforge-doctor.md`](pyforge-doctor.md) | in-deck | One bedside manner over the fleet's vitals — pre-flight diagnostics + continuous monitoring + prescriptions (a consolidation of existing instruments). |
| [`pyforge-herald.md`](pyforge-herald.md) | in-deck | The outward voice + design surface — decks, bridge, telemetry imagery, proclamations (charter re-scoped 2026-07-23: infrastructure → Marshal). |
| [`pyforge-scribe.md`](pyforge-scribe.md) | in-deck | The inward voice — team knowledge captured, curated, compiled into the graph, answerable (owns team-memory + sentinel's core). |
| [`pyforge-steward.md`](pyforge-steward.md) | in-deck | The estate the factory stands on — provisioning, deployment, credential lifecycle, budgets, incident response. |

**Practices**

| Dream | Status | What it is |
|---|---|---|
| [`fleet-stewardship.md`](fleet-stewardship.md) | realized · perpetual | Tend every touchable feedstock: refresh tracks, platform expansion, failure remediation — recurring waves, never finished. |
| [`upstream-discovery.md`](upstream-discovery.md) | seeded | Sense what the world is building (trending + org audits, atlas Phase T) and package it before it's asked for. |
| [`regenerable-factory.md`](regenerable-factory.md) | realized | Backfill Dream→PRD→spec chains under every realized surface (BMAD brownfield) so the factory can change any code through the pipeline; drift checks on all code; the regeneration drill as proof. |

**Capabilities**

| Dream | Status | What it is |
|---|---|---|
| [`agent-portability.md`](agent-portability.md) | seeded | BMAD on any agent (Devin/Copilot/Claude/Cursor); planning on flat-rate subscriptions; the Portability contract enforced. |
| [`team-memory.md`](team-memory.md) | seeded | Shared, version-controlled team memory — what the team knows, every agent knows. |
| [`enterprise-airgap.md`](enterprise-airgap.md) | realized | The factory behind the firewall — JFrog routing + air-gap-by-design; frontier: presenton, deckcraft, warden's registry perimeter. |
| [`modernist-identity.md`](modernist-identity.md) | realized | One visual language for everything PyForge — the Modernist DS across 7 decks; frontier: the design-tokens round-trip (Figma↔JSON↔POTX). |
| [`agentic-sdlc-autonomy.md`](agentic-sdlc-autonomy.md) | in-deck | The four views of agentic autonomy (taxonomy/process/architecture/environment) — the white paper + the 45-slide deck + our live L3 evidence. |
| [`factory-console.md`](factory-console.md) | realized | The whole pipeline on one public page — every Dream + lifecycle stage (Dreamscape board), live epic/story progress, nothing hand-maintained (GitHub Pages). |

**Applications**

| Dream | Status | What it is |
|---|---|---|
| [`deckcraft.md`](deckcraft.md) | seeded | Air-gapped editable-PPTX/Marp/infographic pipeline from primitives — the family's designated PPTX engine. |
| [`presenton-pixi-image.md`](presenton-pixi-image.md) | seeded | Presenton repackaged conda-native + air-gapped for OpenShift in regulated enterprises. |
| [`unity-data-stack.md`](unity-data-stack.md) | seeded | The enterprise innersource platform — a python-first shared monorepo (Constitution + working pixi root recovered from gists). |
| [`wasm-analytics-stack.md`](wasm-analytics-stack.md) | seeded | Wasm-first analytical data stack on OpenShift — WASI-sandboxed Python, dlt+dbt, OTel/OL, Restricted-SCC hardened. |
