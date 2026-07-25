# Wasm Analytics Stack deck (`wasm-analytics-stack`)

**Status: authored 2026-07-25 — 10 slides, full § Standard export set.** Engine + glue copied
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
