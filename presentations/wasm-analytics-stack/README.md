# Wasm Analytics Stack deck (`wasm-analytics-stack`)

**Status: authored 2026-07-25 — 10 slides, full § Standard export set.** Local Wave C poster rebuild 2026-09-15 (Story 21.7). **Story 21.7 FIXED 2026-09-17: the 2026-09-15 rebuild was
corrupted at the source (see Ledger below); the standalone poster has been rewritten with real
content and re-pushed to Design, byte-exact, overwriting the corrupted copy.** Engine + glue copied
**verbatim** from `presentations/pyforge-steward/` (Archivo / Modernist system). A **platform
product** deck (not a persona chapter); Dream: `docs/dreams/wasm-analytics-stack.md`. Spec:
`_bmad-output/projects/wasm-analytics-stack/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`.

Sandboxed analytical pipelines for the hardened enterprise — a WASI Preview 2 upload-validation
boundary under Wasmtime, `dlt` ingestion into DuckDB Bronze, `dbt-duckdb` Silver/Gold, OTel +
OpenLineage end to end, and one Pixi toolchain across laptop → Podman digital twin → OpenShift
under Restricted SCC.

> **The deck leads with the honest maturity verdict** (slide 2, its most valuable slide):
> DuckDB's native engine has **no WASI build and no WASI roadmap** — a `duckdb/duckdb` issue
> search for "WASI" returns **zero** results — and the only community WASI-wheel project
> (`dicej/wasi-wheels`) is **unmaintained since December 2024** and disclaimed by its own author,
> with no `pyarrow` and no `duckdb` in it at all. So `dlt`, `dbt` and DuckDB **cannot run inside a
> genuine WASI component today**, and the sandbox is deliberately scoped to the pure-Python
> upload-validation step while ingestion and transformation stay conventional hardened processes
> (AD-3).

> **Planning depth:** this project ran to **PRD + architecture only** — 5 capabilities, 17 FRs,
> 10 ADs. There are **no epics and no stories**; they decompose fresh when the Dream is scheduled.
> The deck says so on its closing slide — don't imply stories exist.

Workflow: `docs/specs/presentation-deck.md` (prototype contract, § Standard export set,
§ The MCP bridge). `npm install && npm run extract && npm run dev`.
Engine files stay byte-identical across every deck.

## Artifacts

| Artifact | Path |
|---|---|
| Deck prototype (source of truth) | `project/Wasm Analytics Stack.dc.html` — 10 sections |
| Executive summary | `project/Wasm Analytics Stack - Executive Summary.dc.html` |
| Infographic (trio head) | `project/Wasm Analytics Stack - Infographic.dc.html` |
| Infographic standalone | `project/Wasm Analytics Stack Infographic standalone.html` |
| Infographic Deck | `project/Wasm Analytics Stack - Infographic Deck.dc.html` — 7 sections |
| Marp — deck | `src/marp/wasm-analytics-stack-deck-2026-07-25.md` |
| Marp — executive summary | `src/marp/wasm-analytics-stack-executive-summary-2026-07-25.md` |
| Marp — infographic | `src/marp/wasm-analytics-stack-infographic-2026-07-25.md` |
| Derived — standalone HTML | `src/marp/wasm-analytics-stack-infographic-standalone-2026-07-25.html` |
| Derived — deck PPTX | `src/pptx/wasm-analytics-stack-deck-2026-07-25.pptx` |
| Derived — infographic PPTX | `src/pptx/wasm-analytics-stack_infographic_deck-2026-07-25.pptx` |

Regenerate the derived three with `pixi run -e local-recipes deck-export wasm-analytics-stack`
(never hand-edit them).

## Design project (the bridge's far end)

Prototype lives in Claude Design project **"Wasm Analytics Stack deck"**
(`45c841c6-e807-4fee-a92a-f8e89cb890b4`), bound to **Modernist** (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`):
https://claude.ai/design/p/45c841c6-e807-4fee-a92a-f8e89cb890b4?file=Wasm+Analytics+Stack.dc.html
Pull it with the MCP bridge ("pull wasm-analytics-stack") — see
`docs/specs/presentation-deck.md` § *The MCP bridge*.

Seeded 2026-07-25 (byte-exact, verified against disk via `list_files`):

| Design path | bytes | etag at seed |
|---|---|---|
| `Wasm Analytics Stack.dc.html` | 40573 | `1785023174376282` |
| `src/marp/wasm-analytics-stack-deck-2026-07-25.md` | 7152 | `1785023278126698` |
| `src/marp/wasm-analytics-stack-executive-summary-2026-07-25.md` | 3954 | `1785023236194680` |
| `src/marp/wasm-analytics-stack-infographic-2026-07-25.md` | 3850 | `1785023207400489` |
| `support.js` (runtime) | 66404 | `1785022602553358` |
| `deck-stage.js` (copied from the steward project) | 133230 | `1785022660837191` |
| `reference/Warden Infographic standalone.html` | 411764 | `1785022661082860` |

The three non-prototype `.dc.html` artifacts (exec summary, infographic, infographic deck) and the
standalone live in git only so far — seed them on the next Design pass if they need visual editing.

## Ledger — 2026-09-15 Wave C local rebuild, fixed 2026-09-17 (Story 21.7)

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `Wasm Analytics Stack Infographic standalone.html` | 91427 B · 21 sections · 6 acts · 3 SVG · 13 tables · facts 30/30 | `1789646107497288` | rendered 2026-09-17, page 19612 px at 1240 px; 0 unmarked / 0 mismatch; re-pushed, read back and SHA-256-verified byte-exact (`fc5ac86a...6b63641`). |
| `facts.yaml` | 33 facts at tree `506ad58622` | — | spec_status omitted (SPEC archived under Atlas); no package/CLI rows; untouched by the 21.7 fix |
| `Wasm Analytics Stack.dc.html` | 40573 B (unchanged prototype) | `1785023174376282` | already byte-identical on Design (seeded 2026-07-25); verified clean, re-confirmed via SHA-256 2026-09-17 |
| `Wasm Analytics Stack - Executive Summary.dc.html` | 7919 B | `1785023556712367` | already byte-identical on Design; verified clean via SHA-256 2026-09-17 |
| `Wasm Analytics Stack - Infographic.dc.html` | 18867 B | `1785023556712367` | already byte-identical on Design; verified clean via SHA-256 2026-09-17 |
| `Wasm Analytics Stack - Infographic Deck.dc.html` | 22867 B | `1785023556712367` | already byte-identical on Design; verified clean via SHA-256 2026-09-17 |

**2026-09-17 — Story 21.7 FIXED.** The 2026-09-15 rebuild (committed `e483288d5`) was corrupted at
the source: from character offset 6344 through ~142980 of 145174, a boilerplate paragraph repeated
72 times, every character space-separated ("T h e   f a c t o r y..."), replacing real section
content — `deck-facts --check` did not catch it (data-fact spans only, no prose-sanity check). That
corrupted content had already been pushed to Design (etag `1789639734959225`) before the corruption
was discovered.

This pass replaced the entire corrupted span with real, subject-specific content sourced from the
Dream, the folded Atlas Spec (CAP-27..31), and the archived pre-fold Brief/PRD/Architecture (two
user journeys, the full glossary, kill criteria, the five-risk table, pinned stack versions, the
Deferred list) — 21 sections, 6 acts, 3 inline SVGs, 13 tables, 91427 bytes, `deck-facts --check`
0 unmarked / 0 mismatch (facts 30/30). Read back the full rebuilt file by eye and confirmed real,
varied, structured content (no repeated sentence anywhere); rendered headless at 1240 px (19612 px
full-page height) and visually inspected every section — no broken or empty regions. One bug from
the rebuild itself (a stray duplicate `</p></section>` at the section-21/Creed seam) was found and
fixed before pushing.

Re-pushed to Design via `finalize_plan` + `write_files` (etag `1789639734959225` → `1789646107497288`),
read back fresh via `read_file`, decoded the HTML-entity-escaped body, and confirmed SHA-256
byte-exact match against the local file
(`fc5ac86ad0264d8e082cbdc1646fc2a02b6cec6fa78e3c9e480b95742429f776`) — **the corrupted boilerplate
pattern is confirmed absent from the re-read Design content.** The other 4 `project/` files were
already clean and in sync, no push needed for them. Full writeup:
`_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-7-wasm-analytics-stack-rebuilt-to-the-standard.md`
§ Completion. Sibling decks with the same root-commit corruption (Story 21.6 `unity-data-stack`,
21.8 `deckcraft`, 21.9 `presenton-pixi-image`) are tracked separately and not touched by this pass.
