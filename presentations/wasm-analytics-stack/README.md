# Wasm Analytics Stack deck (`wasm-analytics-stack`)

**Status: authored 2026-07-25 — 10 slides, full § Standard export set.** Local Wave C poster rebuild 2026-09-15 (Story 21.7). **Story 21.7 BLOCKED 2026-09-17: the standalone poster is
corrupted at the source (see Ledger below) and the corruption has already been pushed to the live
Design project — do not treat the push as a success.** Engine + glue copied
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

## Ledger — 2026-09-15 Wave C local rebuild (Story 21.7)

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `Wasm Analytics Stack Infographic standalone.html` | 145188 B · 21 sections · 6 acts · 3 SVG · 3 tables · facts 58/58 | `1789639734959225` | rendered 2026-09-15, page 18763 px at 1240 px; 0 unmarked / 0 mismatch; `poster_last_commit_date` unshown. **CORRUPTED — see 2026-09-17 note below; the etag above is the corrupted content, do not treat this row as a clean push.** |
| `facts.yaml` | 33 facts at tree `506ad58622` | — | spec_status omitted (SPEC archived under Atlas); no package/CLI rows |
| `Wasm Analytics Stack.dc.html` | 40573 B (unchanged prototype) | `1785023174376282` | already byte-identical on Design (seeded 2026-07-25); verified clean, re-confirmed via SHA-256 2026-09-17 |
| `Wasm Analytics Stack - Executive Summary.dc.html` | 7919 B | `1785023556712367` | already byte-identical on Design; verified clean via SHA-256 2026-09-17 |
| `Wasm Analytics Stack - Infographic.dc.html` | 18867 B | `1785023556712367` | already byte-identical on Design; verified clean via SHA-256 2026-09-17 |
| `Wasm Analytics Stack - Infographic Deck.dc.html` | 22867 B | `1785023556712367` | already byte-identical on Design; verified clean via SHA-256 2026-09-17 |

**2026-09-17 — Story 21.7 BLOCKED, do not resume as a normal push story.** The standalone poster
above is corrupted at the source (committed `e483288d5`, 2026-09-15, predates this push work): from
character offset 6344 through ~142980 of 145174, a boilerplate paragraph repeats 72 times with
every character space-separated ("T h e   f a c t o r y..."), replacing real section content.
`deck-facts --check` does not catch it (data-fact spans only, no prose-sanity check). This story's
push ran before the corruption was discovered, so **the corrupted content is now live on the Design
project** at the etag above, not merely at risk of it — re-verified by reading it back from Design
directly. The other 4 `project/` files are clean and were already in sync, no push needed for them.
Full writeup: `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-lockstep/.memlog.md`
and deferred-work-ledger `DW-21-7-1`/`DW-21-7-2`. Sibling Story 21.9 (`presenton-pixi-image`, PR
#1405) found the identical pattern from the same root commit and withheld its own push.
