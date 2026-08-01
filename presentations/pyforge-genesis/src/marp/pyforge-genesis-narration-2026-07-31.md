# Narration script — PyForge Genesis

> Extracted from `PyForge Genesis.dc.html` speaker notes (regenerable — do not hand-edit; edit the deck's `data-speaker-notes` in Design and re-extract). 15 scenes.

## Scene 01 — Cover

The master vision deck. One line: PyForge is a Dream-to-Code factory — everything starts with a raw human aspiration, and an eight-persona crew carries it to shipped, validated code. This deck is the founding story; each persona has its own chapter deck.

## Scene 02 — Act I — The Dream

Act I: the genesis. What a Dream is and why the whole model starts there rather than with a ticket or a spec.

## Scene 03 — Tier 0 — where work starts

A Dream is a markdown doc in docs/dreams — Tier 0 of the layout, upstream of everything. It holds the WHY; BMAD turns it into the spec (the WHAT); code follows. The frontmatter tracks its lifecycle: seeded, in-deck, in-spec, realized.

## Scene 04 — Dream → Deck → Spec → Code

The cadence: Herald touches the Dream first and renders The Deck — cheap visual alignment before expensive commitment. Then Marshal solidifies the same Dream into the spec via bmad-spec or the planning chain, and the factory builds from the contract. Deck before spec; spec before code.

## Scene 05 — Act II — The Crew

Act II: who carries the Dream. Eight Smiths, each with its own chapter deck in this same design system.

## Scene 06 — Eight Smiths, eight mottos

The crew at a glance, each with its motto. Herald proclaims and bookends the pipeline; Marshal commands the BMAD factory; Atlas maps; Warden guards; Mason binds and ships; Doctor keeps it alive; Scribe keeps what the team knows; Steward provisions, holds the keys, and keeps the lights on. Each persona's chapter deck lives at presentations/pyforge-…, one per persona.

## Scene 07 — The SDLC, staffed

Every SDLC phase has an owner persona and a skill set — today and the frontier. Deployment & Operations was orphaned until Steward joined.

## Scene 08 — The autonomy gradient

Autonomy is a gradient L1-L5, not a leap of faith. L3 is the production ceiling running here today; unsafe calls escalate.

## Scene 09 — The Master Pipeline

The full automation loop: Doctor checks the machinery before the run; Herald captures the Dream into the vision deck; Marshal spins the BMAD factory from the spec; Atlas charts the dependency map; Warden audits; Mason binds and ships; Doctor keeps monitoring; Herald broadcasts the notables. Supervised end to end by Marshal, opened and closed by Herald.

## Scene 10 — Act III — A running factory

Act III: this is not a metaphor deck. The factory already runs — with shipped, verifiable results.

## Scene 11 — Proof

Three proofs the model runs. Atlas: 32 of 32 stories shipped across waves 0 through H, PRs 58 to 105, driven by bmad-loop. Warden: 23 of 31 mid-loop with an honest compliance gate that never false-greens. The Bridge: Design and Code became one continuous surface — five decks seeded with zero manual downloads, and the loop is specced as the herald CLI.

## Scene 12 — One Dream, nine decks

How the deck family hangs together: this Genesis deck is the parent narrative; the eight persona decks are its chapters, all in the shared Modernist Archivo system so they present side by side; agentic-sdlc is the origin engine the family was forked from. Every deck round-trips through Claude Design via the bridge.

## Scene 13 — Portable by construction

The portability contract: the Dream and the neutral spec kernel are the shared layers every framework can consume; decomposition and execution are per-framework. BMAD produces the spec, but CrewAI, Agno, LangGraph or Devin can start from the same Dream or the same kernel — and be verified against the same oracle. No vendor lock, by construction.

## Scene 14 — Genesis is also the seed

The reason this deck is named genesis: it doubles as the bootstrapper. Present it to align a team, then run genesis to install the operating model — a greenfield repo born Dream-first, or a brownfield repo adopting the tiers, the crew, and the bridge without disturbing what already runs. This very repo was the first brownfield adoption.

## Scene 15 — Build More Architect Dreams

Close: the factory exists so that more dreams get built — captured by Herald, enforced by Marshal, mapped by Atlas, guarded by Warden, bound by Mason, kept alive by Doctor. Everything starts with a Dream. Write yours in docs/dreams.
