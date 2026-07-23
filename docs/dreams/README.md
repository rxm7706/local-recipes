# Dreams — Tier 0

> **Everything starts with a Dream.**

A **Dream** is the raw, unconstrained human aspiration that seeds a deliverable —
the BMAD mission itself: **B**uild **M**ore **A**rchitect **D**reams. It is
**Tier 0** of the framework-neutral layout (see
[`AGENTS.md` → the tiers](../../AGENTS.md)), upstream of the Tier-1 intake spec in
[`docs/specs/`](../specs/).

`docs/dreams/` is the home for the **starting point of each deliverable**. Going
forward, a deliverable **begins as a Dream here** — a vision, unconstrained by
syntax or technical debt — and is only then solidified into a Tier-1 intake spec
(`docs/specs/<slug>.md`), the "what to build" contract. (Historically these
starting points were folded into `docs/specs/`; we are separating them: the Dream
holds the *why*, the spec holds the *what*.)

## How a Dream flows through the crew

```
Dream            Deck        Spec              build · audit · ship        proclaim
docs/dreams/  →  (visual) →  docs/specs/  →    Atlas · Warden · Mason  →   (release)
   the vision     Herald      Marshal                                        Herald
```

- **Herald** reads the Dream and renders the **decks & infographics** — the visual
  alignment assets (`presentations/<slug>/`).
- **Marshal** solidifies the same Dream into a Tier-1 **intake spec**
  (`docs/specs/<slug>.md`), then drives the code with the **BMAD Method** — bmad
  skills + phases run autonomously via **bmad-loop** and **bmad-dev-auto**.
- **Atlas / Warden / Mason** map dependencies, guard the perimeter, and ship.
- **Doctor** runs pre-flight diagnostics before the build and monitors fleet &
  feedstock health after it ships.
- **Live status** — throughout execution, the epic/story progress dashboard is kept
  updated and published on **GitHub Pages** (`docs/dashboard/` → the program
  console). Deliveries, notables, successes, roadmaps, and updates are marshalled
  from there. *(Today the orchestrator — Marshal — owns this run lifecycle; in the
  persona ideal it is Herald who proclaims the release.)*

A Dream **motivates** an intake spec; it never replaces it. The spec remains the
build contract; the Dream is the "why" behind it.

## Convention

- One Dream per file: `docs/dreams/<slug>.md`, plain markdown, tracked in git.
- The Dream's `<slug>` should match its eventual `docs/specs/<slug>.md` intake
  spec, so the pair is easy to trace.
- Light frontmatter identifies it:

  ```yaml
  ---
  title: <Dream title>
  type: dream
  status: seeded | in-deck | in-spec | realized
  ---
  ```

- Keep it aspirational and readable — a Dream is a narrative, not a task list.

## Dreams

23 Dreams as of 2026-07-23 (2 born Dream-first; 16 retro-seeded from a complete
repo + Design-workspace audit; 2 persona dreams added when the ownership audit
grew the crew 6 → 8; 3 recovered from the gist audit). **No-straggler policy:** every BMAD project, deck, Design
project, and spec maps to exactly one Dream; the herald CLI's status capability
(CAP-3) flags any unlinked Design project permanently.

**Foundations**

| Dream | Status | What it is |
|---|---|---|
| [`ecosystem-crew.md`](ecosystem-crew.md) | in-deck | **The founding Dream** — six personas, one "Dream to Code" pipeline. Master vision deck: `presentations/pyforge-genesis/`. |
| [`pyforge-genesis.md`](pyforge-genesis.md) | in-deck | Genesis as master idea + **the seed**: init a new repo / adopt brownfield with the whole operating model (origin: `docs/bmad-setup-plan.md`). |
| [`sentinel.md`](sentinel.md) | seeded | **The ancestor** (2026-04): the AI Software Factory — "the graph is the product"; unbuilt core, stranded artifacts to repatriate; descendants credited. |
| [`design-code-bridge.md`](design-code-bridge.md) | realized | Design + Code as one surface — seed/design/pull, zero downloads; herald CLI specced (5 CAPs). |

**Persona products**

| Dream | Status | What it is |
|---|---|---|
| [`packaging-factory.md`](packaging-factory.md) | realized · perpetual | The origin dream: the AI-assisted conda-forge factory (Mason) — CFE skill, 769 feedstocks, campaigns; frontier: multi-ecosystem autotick, smart test extractor. |
| [`pyforge-atlas.md`](pyforge-atlas.md) | realized | The intelligence layer reborn as Kedro/Dagster/DuckDB dataflow an agent workforce maintains (waves 0–H shipped, PRs #58–#105). |
| [`pyforge-warden.md`](pyforge-warden.md) | in-spec | The compliance gate that never false-greens — six axes of dependency trust (23/31 built). |
| [`pyforge-marshal.md`](pyforge-marshal.md) | realized | Graduated autonomy a human can trust — bmad-loop/dev-auto + gates + escalation; proved on atlas + warden. |
| [`pyforge-doctor.md`](pyforge-doctor.md) | seeded | One bedside manner over the fleet's vitals — pre-flight diagnostics + continuous monitoring + prescriptions (a consolidation of existing instruments). |
| [`pyforge-scribe.md`](pyforge-scribe.md) | seeded | The inward voice — team knowledge captured, curated, compiled into the graph, answerable (owns team-memory + sentinel's core). |
| [`pyforge-steward.md`](pyforge-steward.md) | seeded | The estate the factory stands on — provisioning, deployment, credential lifecycle, budgets, incident response. |

**Practices**

| Dream | Status | What it is |
|---|---|---|
| [`fleet-stewardship.md`](fleet-stewardship.md) | realized · perpetual | Tend every touchable feedstock: refresh tracks, platform expansion, failure remediation — recurring waves, never finished. |
| [`upstream-discovery.md`](upstream-discovery.md) | seeded | Sense what the world is building (trending + org audits, atlas Phase T) and package it before it's asked for. |

**Capabilities**

| Dream | Status | What it is |
|---|---|---|
| [`agent-portability.md`](agent-portability.md) | seeded | BMAD on any agent (Devin/Copilot/Claude/Cursor); planning on flat-rate subscriptions; the Portability contract enforced. |
| [`team-memory.md`](team-memory.md) | seeded | Shared, version-controlled team memory — what the team knows, every agent knows. |
| [`enterprise-airgap.md`](enterprise-airgap.md) | realized | The factory behind the firewall — JFrog routing + air-gap-by-design; frontier: presenton, deckcraft, warden's registry perimeter. |
| [`modernist-identity.md`](modernist-identity.md) | realized | One visual language for everything pyforge — the Modernist DS across 7 decks; frontier: the design-tokens round-trip (Figma↔JSON↔POTX). |
| [`agentic-sdlc-autonomy.md`](agentic-sdlc-autonomy.md) | in-deck | The four views of agentic autonomy (taxonomy/process/architecture/environment) — the white paper + the 45-slide deck + our live L3 evidence. |

**Applications**

| Dream | Status | What it is |
|---|---|---|
| [`deckcraft.md`](deckcraft.md) | seeded | Air-gapped editable-PPTX/Marp/infographic pipeline from primitives — the family's designated PPTX engine. |
| [`presenton-pixi-image.md`](presenton-pixi-image.md) | seeded | Presenton repackaged conda-native + air-gapped for OpenShift in regulated enterprises. |
| [`unity-data-stack.md`](unity-data-stack.md) | seeded | The enterprise innersource platform — a python-first shared monorepo (Constitution + working pixi root recovered from gists). |
| [`local-ai.md`](local-ai.md) | seeded | The factory's own compute — dual-GPU local AI workstation + local model backends (vLLM tiers, offline planning). |
| [`wasm-analytics-stack.md`](wasm-analytics-stack.md) | seeded | Wasm-first analytical data stack on OpenShift — WASI-sandboxed Python, dlt+dbt, OTel/OL, Restricted-SCC hardened. |
