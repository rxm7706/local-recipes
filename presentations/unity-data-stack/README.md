# Unity Data Stack deck (`unity-data-stack`)

**Status: authored 2026-07-25 — 10 slides, full § Standard export set.** Engine + glue copied
**verbatim** from `presentations/pyforge-steward/` (Archivo / Modernist system). A **platform
product** deck (not a persona chapter); Dream: `docs/dreams/unity-data-stack.md`. Spec:
`_bmad-output/projects/unity-data-stack/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`.

The enterprise **innersource** platform — an opinionated, conda-native, air-gap-first,
spec-governed monorepo where teams co-contribute templates, libraries, services and Data Products
on one python-first toolchain. The deck carries the **Constitution** (14 Articles as the
requirement spine + its 8 required amendments), the pixi-orchestrator-root / PEP 751 `pylock.toml`
lock architecture, the AD-17 station map onto the PyForge Guild — and the **honest findings**:
the intake set's flagship `pdm export --override-platform` flag **does not exist**, PEP 751 does
not guarantee multi-platform lockfiles, and the EU CRA's vulnerability-reporting obligations begin
**2026-09-11**.

> **Planning depth:** this project ran to **PRD + architecture only** — 9 capabilities, 60 FRs,
> 23 ADs. There are **no epics and no stories**; they decompose fresh when the Dream is scheduled.
> The deck says so on its closing slide — don't imply stories exist.

Workflow: `docs/specs/presentation-deck.md` (prototype contract, § Standard export set,
§ The MCP bridge). `npm install && npm run extract && npm run dev`.
Engine files stay byte-identical across every deck.

## Artifacts

| Artifact | Path |
|---|---|
| Deck prototype (source of truth) | `project/Unity Data Stack.dc.html` — 10 sections |
| Executive summary | `project/Unity Data Stack - Executive Summary.dc.html` |
| Infographic (trio head) | `project/Unity Data Stack - Infographic.dc.html` |
| Infographic standalone | `project/Unity Data Stack Infographic standalone.html` |
| Infographic Deck | `project/Unity Data Stack - Infographic Deck.dc.html` — 7 sections |
| Marp — deck | `src/marp/unity-data-stack-deck-2026-07-25.md` |
| Marp — executive summary | `src/marp/unity-data-stack-executive-summary-2026-07-25.md` |
| Marp — infographic | `src/marp/unity-data-stack-infographic-2026-07-25.md` |
| Derived — standalone HTML | `src/marp/unity-data-stack-infographic-standalone-2026-07-25.html` |
| Derived — deck PPTX | `src/pptx/unity-data-stack-deck-2026-07-25.pptx` |
| Derived — infographic PPTX | `src/pptx/unity-data-stack_infographic_deck-2026-07-25.pptx` |

Regenerate the derived three with `pixi run -e local-recipes deck-export unity-data-stack`
(never hand-edit them).

## Design project (the bridge's far end)

Prototype lives in Claude Design project **"Unity Data Stack deck"**
(`0494e2b0-7132-43b7-8ff2-4b4b42fa8384`), bound to **Modernist** (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`):
https://claude.ai/design/p/0494e2b0-7132-43b7-8ff2-4b4b42fa8384?file=Unity+Data+Stack.dc.html
Pull it with the MCP bridge ("pull unity-data-stack") — see
`docs/specs/presentation-deck.md` § *The MCP bridge*.

Seeded 2026-07-25 (byte-exact, verified against disk via `list_files`):

| Design path | bytes | etag at seed |
|---|---|---|
| `Unity Data Stack.dc.html` | 38591 | `1785023001770676` |
| `src/marp/unity-data-stack-deck-2026-07-25.md` | 7478 | `1785022846414152` |
| `src/marp/unity-data-stack-executive-summary-2026-07-25.md` | 3640 | `1785022801707901` |
| `src/marp/unity-data-stack-infographic-2026-07-25.md` | 3698 | `1785022760254541` |
| `support.js` (runtime) | 66404 | `1785022600693637` |
| `deck-stage.js` (copied from the steward project) | 133230 | `1785022656367487` |
| `reference/Warden Infographic standalone.html` | 411764 | `1785022656710156` |

The three non-prototype `.dc.html` artifacts (exec summary, infographic, infographic deck) and the
standalone live in git only so far — seed them on the next Design pass if they need visual editing.
