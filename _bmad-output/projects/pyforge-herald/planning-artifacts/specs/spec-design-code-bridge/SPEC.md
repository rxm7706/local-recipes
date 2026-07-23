---
id: SPEC-design-code-bridge
companions:
  - bridge-protocol.md
  - ../../../../../../docs/specs/presentation-deck.md
sources:
  - ../../../../../../docs/dreams/design-code-bridge.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# herald CLI — the Design↔Code Bridge, formalized

## Why

A vision to realize, grounded in a pain already solved once by hand: deck prototypes are authored visually in Claude Design but built and shipped from this repo, and until 2026-07-23 the boundary was crossed by manual mirror-and-download (the stale *"Local recipes repository connection"* project is the fossil of that workflow). The bridge loop — seed a Design project from the repo, design visually, pull the prototype back — was proven that day over the claude-design MCP tools across four persona decks. The `herald` CLI (module `pyforge.herald`, the Ecosystem Crew's Proclaimer) makes that proven loop a repeatable command instead of a session transcript, so any operator or agent can run it without re-deriving the protocol.

## Capabilities

- **CAP-1**
  - **intent:** An operator can seed a deck slug into Claude Design — a design-system-bound project carrying the deck runtime and a contract-compliant starter prototype — ready for visual iteration.
  - **success:** From a clean state, `herald deck seed <slug>` yields a Design project whose prototype, read back, passes the repo's `extract` (expected slide count, no lost sections) and `build`; seeding over existing Design-side edits is refused with a structured conflict and writes nothing.
- **CAP-2**
  - **intent:** An operator can pull a deck's prototype from Claude Design into the repo and have the deck re-derived end to end.
  - **success:** After a Design-side edit, `herald deck pull <slug>` lands the prototype in `presentations/<slug>/project/`, re-runs extract → build green, and regenerates the derived export set; when Design is unchanged, pull is a no-op that transfers no file body and reports "unchanged" distinctly (exit 0).
- **CAP-3**
  - **intent:** An operator can see the bridge state of every deck — linked project, sync freshness, and hazards — without touching either surface.
  - **success:** `herald deck status` emits machine-readable per-deck state (linked/unlinked, unchanged/changed/conflict via etags, last pull) and flags a stale hand-mirror (a Design project holding a repo app-tree copy) in a fixture where one is planted.
- **CAP-4**
  - **intent:** An operator can leave the bridge in watch mode so Design-side edits land in the repo continuously.
  - **success:** With watch running, an edit appearing in Design is pulled (per CAP-2) within one poll interval; consecutive unchanged polls perform zero writes on both surfaces.

## Constraints

- Only the **prototype** crosses the bridge — never a mirrored app tree.
- **Prove-before-cross:** a prototype must pass local `extract` + `build` before any seed write reaches Design.
- **Etag discipline both directions:** every cross-surface read/write carries `if_none_match`/`if_match`; unconditional writes are forbidden; a conflict surfaces structurally and clobbers nothing.
- Design-side writes follow the platform protocol: design-prompt gate before writing, declared write-sets (`finalize_plan`), entity-escaped read bodies decoded on pull.
- User-facing output carries `claude.ai/design` URLs only; tokenized `serve_url`s never appear in output or files.
- pyforge persona decks bind the **Modernist** design system (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`).
- Acceptance is **framework-agnostic and machine-checkable** (exit codes + file artifacts as the oracle), per `AGENTS.md` § Portability contract.
- An unreachable Design surface is a clear structured failure — never a silent no-op.

## Non-goals

- Herald's broadcast/megaphone surface (`updates compile`, `broadcast`) — a separate effort.
- BMAD monorepo/multi-project integration (`herald bmad init`) — a separate effort.
- Programmatic editing of Design-side slide content beyond the initial seed — design stays human.
- Replacing the deck pipeline — the CLI wraps `extract`/`build`/`deck-export` (contract: the adopted `presentation-deck.md` companion) as black boxes.
- Marp/infographic source bridging (v1) — pending the open question below.
- Automatic retirement of legacy hand-mirror projects — CAP-3 detects; humans retire.

## Success signal

An operator who has never seen the pilot transcript runs `seed` → edits in Claude Design → `pull`, and ships a green, fully exported deck without a single manual download — with an unchanged `pull` provably cheap (no body transferred) and a mid-edit conflict provably safe (structured refusal, both sides intact). All four verdicts read from exit codes and produced files alone.

## Assumptions

- Pull leaves git commits to the operator by default (the pilot committed via session); an opt-in `--commit` flag may exist.
- Watch mode is poll-based — no push/webhook channel exists on the Design surface.
- Deck slugs are `presentations/<slug>/` dirs with the standard engine layout and the README "Design project" registry line (the pilot's convention).

## Open Questions

- **Standalone transport/auth:** how does the CLI reach the claude-design MCP surface *outside* a Claude Code session (the pilot ran inside one)? Blocking for implementation, not for this contract.
- **Watch cadence:** acceptable poll interval versus Design-surface rate limits?
- **Scope check:** should v1 also bridge Marp/infographic sources (the Dream's fuller scope), or stay prototype-only as specified?
