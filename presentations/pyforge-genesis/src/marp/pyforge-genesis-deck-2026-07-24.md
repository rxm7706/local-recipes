---
marp: true
paginate: true
size: 16:9
title: Genesis — everything starts with a dream
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  a { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.dark { background:#201e1d; color:#f3f2f2; }
  section.dark h1, section.dark h2, section.dark h3, section.dark code { color:#f3f2f2; }
  section.dark strong { color:#ec3013; }
  hr { border:none; border-top:3px solid #201e1d; margin:.4em 0; }
  table { font-size:.78em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- 01 · Cover -->

GENESIS · pyforge · Dream to Code · founding Dream: `docs/dreams/ecosystem-crew.md`

# everything starts with a dream.

The mission of the factory is **Build More Architect Dreams**: turn a raw, inspired human aspiration — unconstrained by syntax or technical debt — into **deterministic, production-ready code**.

| Genesis | Crew | Method | Pipeline |
| --- | --- | --- | --- |
| `docs/dreams/` | 8 personas | BMAD · bmad-loop | Dream → Code |

<!-- The master vision deck. pyforge is a Dream-to-Code factory — an eight-persona crew carries a raw human aspiration to shipped, validated code. -->

---

<!-- _class: dark -->

## Act I

# The Dream

Not a ticket. Not a spec. The **raw aspiration** — before syntax, before constraints.

---

## Tier 0 — where work starts

**A Dream is** — a markdown doc in `docs/dreams/` — the starting point of every deliverable. It holds the **why**: the problem to solve, the system to construct, the audience to empower. Aspirational, narrative, human.

**Its lifecycle** — **seeded** → written down · **in-deck** → Herald renders the vision · **in-spec** → BMAD distills the contract · **realized** → shipped and proclaimed.

---

## The cadence — Dream → Deck → Spec → Code

**Deck first** — **Herald** is the first to touch the Dream; the vision deck is cheap alignment before expensive commitment.

**Spec second** — **Marshal** solidifies the same Dream into the contract — `bmad-spec` distills it; the planning chain scales it.

**Code third** — the factory builds **from the contract** — spec-driven, gated, never vibes. The crew maps, audits, binds, ships.

---

<!-- _class: dark -->

## Act II

# The Crew

Eight personas carry the Dream down one pipeline — **each has its own chapter deck.**

---

## Eight personas, eight mottos

| Persona | Motto |
| --- | --- |
| **Herald** · Proclaimer | "Capture the dream. Illustrate the telemetry. Proclaim the release." |
| **Marshal** · Commander | "Enforce the spec. Guard the boundaries. Run the line." |
| **Atlas** · Navigator | "Chart the dependencies. Map the world. Define the floor." |
| **Warden** · Guardian | "Halt the threat. Clear the axes. Protect the perimeter." |
| **Mason** · Artisan | "We forge the blocks. We bind the environment. We ship the structure." |
| **Doctor** · Physician | "Check the vitals. Diagnose the fault. Keep the ecosystem alive." |
| **Scribe** · Chronicler | "Capture the decision. Keep the graph. Answer from memory." |
| **Steward** · Provisioner | "Provision the line. Hold the keys. Keep the lights on." |

---

## The Master Pipeline — one loop, end to end

- **0 · Doctor** — pre-flight: verify the machinery is sound.
- **1 · Herald** — capture the Dream → the vision deck.
- **2 · Marshal** — spin the factory from the Spec contract.
- **3–5 · Atlas · Warden · Mason** — map, audit, bind & ship.
- **6–7 · Doctor · Herald** — monitor the fleet; broadcast the notables.
- **Throughout · Scribe · Steward** — record every decision; provision the line and hold the keys.

```
doctor check --env --engines        atlas map --ecosystem dual
herald deck generate --prompt "…"   warden audit --axes hygiene,security,license
marshal factory spin --spec …       mason package --ship conda-forge
```

---

<!-- _class: dark -->

## Act III

# Not a metaphor — a running factory

---

## Proof — already shipped

**32/32** — **Atlas**: the Kedro/Dagster/DuckDB migration — every story of waves 0–H shipped via bmad-loop (PRs #58–#105).

**23/31** — **Warden**: the compliance gate that never false-greens, mid-loop with epics 1–4 merged and an honest dashboard.

**0** — **The Bridge**: manual downloads between Claude Design and the repo — zero. Five decks seeded through it; the loop is specced as the **herald** CLI.

---

## One Dream, nine decks

**The parent + eight chapters** — `pyforge-genesis` (this deck) tells the founding story; `pyforge-atlas · warden · marshal · herald · mason · doctor · scribe · steward` each tell one persona's chapter — all in the shared **Modernist / Archivo** system, presenting side-by-side as one set.

**Authored in Design, shipped from the repo** — every deck round-trips through **Claude Design** via the bridge: seeded from the repo, refined visually, pulled back, shipped with its full export set. **Zero manual transfers.**

---

## Portable by construction

**Shared layers** — the **Dream** (the why) and the **neutral spec kernel** (the what + machine-checkable acceptance) — framework-agnostic by construction.

**Per-framework layers** — decomposition and execution: BMAD epics today; **CrewAI, Agno, LangGraph, Devin** tomorrow — all verified against the **same oracle**. No vendor lock.

---

## Genesis is also the seed

**Greenfield · init a new repo** — a repository born **Dream-first**: `docs/dreams/`, the tier layout, the agent conventions, BMAD wiring, the deck family — installed from day zero.

**Brownfield · adopt in place** — layer the operating model onto an **existing** repo — tiers, crew, bridge — without disturbing what already runs. **This repo was the first brownfield adoption.**

---

<!-- _class: lead -->

## Build More Architect Dreams

# Everything starts with a Dream. The factory exists to build more of them.

Genesis · pyforge · Dream to Code — `docs/dreams/` · write yours
