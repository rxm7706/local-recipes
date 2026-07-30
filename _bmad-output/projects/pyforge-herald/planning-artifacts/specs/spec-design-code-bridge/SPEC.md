---
id: SPEC-design-code-bridge
owner-dream: docs/dreams/design-code-bridge.md
surface:
  - src/shared/packages/pyforge-herald/**   # the herald CLI this Spec builds (workspace member; the earlier `src/pyforge/herald/**` was import-path shorthand — AD-1)
  - scripts/deck_export.py     # CAP-5 export path the CLI wraps
companions:
  - bridge-protocol.md
  - ../../../../../../docs/specs/presentation-deck.md
sources:
  - ../../../../../../docs/dreams/design-code-bridge.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# herald CLI — the Design↔Code Bridge, formalized

## Why

A vision to realize, grounded in a pain already solved once by hand: deck prototypes and Marp sources are authored visually in Claude Design but built and shipped from this repo, and until 2026-07-23 the boundary was crossed by manual mirror-and-download (the stale *"Local recipes repository connection"* project is the fossil of that workflow). The bridge loop — seed a Design project from the repo, design visually, pull the artifacts back — was proven that day over the claude-design MCP tools across four persona decks. The `herald` CLI (module `pyforge.herald`, the Ecosystem Crew's Proclaimer) makes that proven loop a repeatable command instead of a session transcript, so any operator or agent can run it without re-deriving the protocol.

## Capabilities

- **CAP-1**
  - **intent:** An operator can seed a deck slug into Claude Design — a design-system-bound project carrying the deck runtime and a contract-compliant starter prototype — ready for visual iteration.
  - **success:** From a clean state, `herald deck seed <slug>` yields a Design project whose prototype, read back, passes the repo's `extract` (expected slide count, no lost sections) and `build`; seeding over existing Design-side edits is refused with a structured conflict and writes nothing.
- **CAP-2**
  - **intent:** An operator can pull a deck's authored sources — prototype, Marp sources, and any Design-authored standalone bundle — from Claude Design into the repo and have the deck re-derived end to end.
  - **success:** After a Design-side edit, `herald deck pull <slug>` lands the prototype in `presentations/<slug>/project/` (re-running extract → build green), Marp sources in `src/marp/`, and a Design-authored standalone bundle at its export path, then regenerates the derived export set; when Design is unchanged, pull is a no-op that transfers no file body and reports "unchanged" distinctly (exit 0).
- **CAP-3**
  - **intent:** An operator can see the bridge state of every deck — linked project, sync freshness, and hazards — without touching either surface.
  - **success:** `herald deck status` emits machine-readable per-deck state (linked/unlinked, unchanged/changed/conflict via etags, last pull) and flags a stale hand-mirror (a Design project holding a repo app-tree copy) in a fixture where one is planted.
- **CAP-4**
  - **intent:** An operator can leave the bridge in watch mode so Design-side edits land in the repo continuously.
  - **success:** With defaults — 60 s etag-only poll (hard floor 30 s, jittered), pull deferred until the etag has been stable for one interval, idle backoff doubling to a 10-minute cap and resetting on change, halt on auth error — an edit appearing in Design lands via CAP-2 within poll + debounce; consecutive unchanged polls perform zero writes on both surfaces.
- **CAP-5**
  - **intent:** An operator can push a deck's regenerated derived exports back into its Design project, so Design holds the complete export set alongside the sources.
  - **success:** After a pull + `deck-export` cycle, the Design project contains the current derived set (verified by returned etags); an unchanged re-push writes nothing; a Design-side conflict on any export file is refused structurally with no partial clobber.

## Constraints

- **Directional crossing rule:** inbound (Design → repo) carries only **authored sources** — the prototype, Marp `.md` sources, and a Design-authored standalone bundle; outbound (repo → Design) carries only **seeds and regenerated derived exports**. Never a mirrored app tree, in either direction.
- **Bridge operations are deterministic — no LLM in the loop** for seed/pull/status/watch, regardless of transport.
- **Prove-before-cross:** a prototype must pass local `extract` + `build` before any seed write reaches Design.
- **Etag discipline both directions:** every cross-surface read/write carries `if_none_match`/`if_match`; unconditional writes are forbidden; a conflict surfaces structurally and clobbers nothing.
- Design-side writes follow the platform protocol: design-prompt gate before writing, declared write-sets (`finalize_plan`), entity-escaped read bodies decoded on pull.
- User-facing output carries `claude.ai/design` URLs only; tokenized `serve_url`s never appear in output or files.
- pyforge persona decks bind the **Modernist** design system (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`).
- Acceptance is **framework-agnostic and machine-checkable** (exit codes + file artifacts as the oracle), per `AGENTS.md` § Portability contract.
- An unreachable Design surface is a clear structured failure — never a silent no-op; watch halts rather than retries on auth errors.

## Non-goals

- Herald's broadcast/megaphone surface (`updates compile`, `broadcast`) — a separate effort.
- BMAD monorepo/multi-project integration (`herald bmad init`) — a separate effort.
- Programmatic editing of Design-side content beyond the initial seed — design stays human.
- Replacing the deck pipeline — the CLI wraps `extract`/`build`/`deck-export` (contract: the adopted `presentation-deck.md` companion) as black boxes.
- **Marp-source seeding** — authoring stays wherever it happens; only pull is in scope for Marp.
- **Generating exports** — editable PPTX is the `deck-export`/deckcraft pipeline's job (see `presentation-deck.md` § Export decisions revisited); herald **transports** exports (CAP-5), never generates them.
- Automatic retirement of legacy hand-mirror projects — CAP-3 detects; humans retire.

## Success signal

An operator who has never seen the pilot transcript runs `seed` → edits in Claude Design → `pull`, and ships a green, fully exported deck without a single manual download — with an unchanged `pull` provably cheap (no body transferred) and a mid-edit conflict provably safe (structured refusal, both sides intact). All four verdicts read from exit codes and produced files alone.

## Assumptions

- **Transport is dual-path:** primary = a pure MCP client on the claude-design remote server reusing the `/design-login` OAuth credential — proven or killed by a time-boxed spike as the **first implementation story**; fallback = a headless Claude Code / Agent SDK wrapper with a tool allowlist reusing the stored login (the bmad-loop-proven substrate; token-costed). Either satisfies the deterministic-bridge constraint.
- Pull leaves git commits to the operator by default (the pilot committed via session); an opt-in `--commit` flag may exist.
- Watch mode is poll-based — no push/webhook channel exists on the Design surface.
- Deck slugs are `presentations/<slug>/` dirs with the standard engine layout and the README "Design project" registry line (the pilot's convention).
