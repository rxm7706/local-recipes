# Bridge protocol — the proven loop the herald CLI wraps

Companion to `SPEC.md` (SPEC-design-code-bridge). This is the HOW-evidence: the exact
tool sequence proven in the 2026-07-23 pilot, which CAP-1/CAP-2 formalize. Tool names
are the `claude-design` MCP surface's.

## Seed (repo → Design) — CAP-1

1. Prove locally: `npm run extract` (expected slide count, no lost sections) + `npm run build` in `presentations/<slug>/`.
2. `get_claude_design_prompt(design_system_id)` — mandatory gate before any write.
3. `create_project(name: "PyForge <Persona> deck", design_system_id: Modernist)`.
4. `finalize_plan(writes: ["support.js", "deck-stage.js", "<Deck>.dc.html"])` → `plan_token` + `base_etags` (all `"0"` for a fresh project).
5. `create_support_js(path: "support.js", if_match: "0")` — server writes the runtime; never author it.
6. `copy_files(deck-stage.js from an existing deck project, if_match: "0")` — server-side copy, exempt from the read cap.
7. `write_files(prototype, if_match: "0")` — the exact bytes that passed step 1.
8. Record the returned etags; register the project in the deck README § *Design project*.

## Pull (Design → repo) — CAP-2

1. `read_file(path, if_none_match: <last-seen etag>)`.
2. `{unchanged: true}` → report "unchanged", exit 0, stop (no body transferred).
3. Otherwise: decode the entity-escaped body (`&amp; &lt; &gt;` → `& < >`), write to `presentations/<slug>/project/<Deck>.dc.html`, store the new etag.
4. Re-derive: `npm run extract` → `npm run build` → `pixi run -e local-recipes deck-export <slug>`.
5. Commit is the operator's (or `--commit`'s) move — never implicit.

## Authored-source pull (v1 scope, per OQ-3 + export-revisit resolutions)

Same read/etag/decode loop as the prototype pull; different landing paths and no
extract/build — `deck-export` regenerates the derived set instead:

- Design-side Marp sources (e.g. `warden-deck.md`, `warden-executive-summary.md`,
  `warden-infographic.md` in the Warden Design project — the evidence that Marp
  authoring happens in Design) → land at
  `presentations/<slug>/src/marp/<slug>-{deck,executive-summary,infographic}-<date>.md`.
- Design-authored **standalone bundle** (e.g. `Warden Infographic standalone.html`,
  411,764 B — the richer "bundled page" poster) → lands at the export path
  `src/marp/<slug>-infographic-standalone-<date>.html`, **superseding** any marp
  `--html` render (fallback only when no bundle exists).
- After landing: `pixi run -e local-recipes deck-export <slug>`.

## Export push-back (CAP-5, per export-revisit resolution)

After `deck-export` regenerates, push the derived set into the Design project so
Design holds the complete set: `finalize_plan` declaring the export filenames →
`write_files` each with its last-known etag (`"0"` for first push). Unchanged
files are skipped (compare local hash vs last-pushed etag record); any conflict
is refused structurally — no partial clobber. Design-side names mirror the repo
filenames verbatim.

## Watch parameters (CAP-4 defaults)

- Poll: etag-only `read_file` per watched deck, **60 s** default, hard floor 30 s, jittered.
- Debounce: pull only after the etag is **stable for one full interval** (Design saves continuously mid-edit).
- Idle backoff: double after ~10 unchanged polls, cap 10 min, reset on any change.
- Halt on auth error — never retry a 401.

## Conventions (pilot-established)

- Design project name: `PyForge <Persona> deck`; prototype file: `PyForge <Persona>.dc.html` (spaces kept — the Design export convention).
- Modernist design system id: `fbc1d6c8-b35f-4df6-9044-a64d2675427b`.
- Per-deck registry: the deck README's § *Design project* records project name, id, and file URL — the durable link any session can pull from.
- Deck engine + export contracts: `docs/specs/presentation-deck.md` (adopted companion) — § *The MCP bridge*, § *Standard export set*, the prototype contract.

## Pilot evidence (2026-07-23 — ground truth for acceptance fixtures)

| Deck | Design project id | Result |
|---|---|---|
| pyforge-marshal | `ad84d4f6-c292-42c8-98bf-ede78a567773` | seeded; pull returned `{unchanged: true}` (etag short-circuit) |
| pyforge-herald | `ff879a32-9741-4cf5-948f-d67040481d24` | seeded; extract 10/10 + build green pre-seed |
| pyforge-mason | `a7a2c3b1-5718-49fa-8c90-71d44d57eae9` | seeded; extract 10/10 + build green pre-seed |
| pyforge-doctor | `46dbbdea-6f8d-45c6-9309-15d1f297beeb` | seeded; extract 10/10 + build green pre-seed |

Cautionary fixture for CAP-3: Design project *"Local recipes repository connection"*
(`e2a3ed13-7c0b-46ff-9d70-c41eeb93c2ea`) — a stale hand-mirrored copy of
`presentations/pyforge-atlas/`, exactly the pattern stale-mirror detection must flag.
