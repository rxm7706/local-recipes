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

| Dream | What it is |
|---|---|
| [`ecosystem-crew.md`](ecosystem-crew.md) | **The founding Dream** — the Ecosystem Crew: the six personas (Herald · Marshal · Atlas · Warden · Mason · Doctor) that run the pyforge "Dream to Code" factory, and the pipeline that carries a Dream from vision to shipped release. |
| [`design-code-bridge.md`](design-code-bridge.md) | **The Design↔Code Bridge** — Claude Design and Claude Code as one continuous surface: seed a Design project from the repo, design visually, pull the prototype back, extract → build → ship. Herald's first organ; piloted 2026-07-23 with the Marshal deck. |
