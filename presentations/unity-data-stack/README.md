# Unity Data Stack deck (`unity-data-stack`)

**Status: authored 2026-07-25 — 10 slides, full § Standard export set.** Local Wave C poster rebuild 2026-09-15 (Story 21.6) had left the standalone infographic corrupted (see the 2026-09-17 blocked Ledger entry below); **fixed and DONE 2026-09-17** — content rebuilt to the infographic standard, verified, pushed and read back byte-exact (see the 2026-09-17 rebuild+push Ledger entry). All five `project/` artifacts are confirmed in sync with Design. Engine + glue copied
**verbatim** from `presentations/pyforge-steward/` (Archivo / Modernist system). A **platform
product** deck (not a persona chapter); Dream: `docs/dreams/unity-data-stack.md`. The chain's Spec
was consolidated into `spec-pyforge-atlas` 2026-08-02 (see the Dream's own superseded-notice); the
original standalone Spec + its `constitution-provenance.md` companion now live archived at
`archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`
(the path formerly written here, `_bmad-output/projects/unity-data-stack/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`,
does not exist).

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
Prototype lives in Claude Design project **"Unity Data Stack deck"** (`0494e2b0-7132-43b7-8ff2-4b4b42fa8384`):
https://claude.ai/design/p/0494e2b0-7132-43b7-8ff2-4b4b42fa8384?file=Unity+Data+Stack.dc.html
### Provenance

Bound to **Modernist** (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`). Pull it with the MCP bridge
("pull unity-data-stack") — see `docs/specs/presentation-deck.md` § *The MCP bridge*. (This
`### Provenance` sub-heading was added 2026-09-17 to bring the section above into
`pyforge.herald.registry.read()`'s canonical two-body-line shape — the prose that used to sit
directly under the heading broke `registry.read()` with "expected exactly two body lines, found
21"; see the 2026-09-17 Ledger entry below for the incident that surfaced it.)

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

## Ledger — 2026-09-15 Wave C local rebuild (Story 21.6)

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `Unity Data Stack Infographic standalone.html` | 145176 B · 21 sections · 6 acts · 3 SVG · 3 tables · facts 56/56 | `PENDING-PUSH` | rendered 2026-09-15, page 18763 px at 1240 px; 0 unmarked / 0 mismatch; `poster_last_commit_date` unshown; head + Infographic Deck still July stubs |
| `facts.yaml` | 32 facts at tree `506ad58622` | — | spec_status omitted (SPEC lives in archive under Atlas); no package/CLI rows |

## Ledger — 2026-09-17 push attempt — BLOCKED, standalone corrupted (Story 21.6)

`list_files`/`read_file` + SHA-256 (decoding the wrapper's `&lt;`/`&gt;`/`&amp;` entities) confirmed
`Unity Data Stack.dc.html`, `- Executive Summary.dc.html`, `- Infographic.dc.html`, and
`- Infographic Deck.dc.html` were **already byte-identical** on Design — no push needed or
performed for these four (they were pushed in an earlier, undocumented pass; this session found no
drift and made no write). **`Unity Data Stack Infographic standalone.html` is corrupted** (found
independently, matching a sibling report from Story 21.9/presenton-pixi-image and the herald
coordinator): from character offset 6,350 through 142,949 (of 145,176 bytes total), a boilerplate
fleet-status paragraph ("The factory already runs a tracked fleet: stories 930 of 998 and epics 207
of 225. BMAD core …") repeats 72 times with every character space-separated, overwriting nearly the
whole body. Traced to commit `e483288d54f` ("Rebuild the four chain-deck posters from their fact
ledgers", 2026-09-15) — the same commit that authored the 2026-09-15 rebuild row above.
`deck-facts unity-data-stack --check`'s "0 unmarked / 0 mismatch" does not catch this (it checks
`data-fact` spans, not prose). **Not pushed** — Design's copy of the standalone (18,588 B, the
pre-rebuild July stub) is untouched. `PENDING-PUSH` below is intentionally NOT cleared until the
standalone is regenerated correctly and re-verified.

| Artifact | Design etag | Notes |
|---|---|---|
| `Unity Data Stack.dc.html` | `1785023001770676` (unchanged) | verified byte-identical, sha256 `46349813a6f7…`; no push |
| `Unity Data Stack - Executive Summary.dc.html` | `1785023542254041` (unchanged) | verified byte-identical, sha256 `595a3900b8d9…`; no push |
| `Unity Data Stack - Infographic.dc.html` | `1785023542254041` (unchanged) | verified byte-identical, sha256 `2ead3e671a11…`; no push |
| `Unity Data Stack - Infographic Deck.dc.html` | `1785023542254041` (unchanged) | verified byte-identical, sha256 `227dfc6926f5…`; no push |
| `Unity Data Stack Infographic standalone.html` | `PENDING-PUSH` (still) | **corrupted on disk since e483288d54f — not pushed; blocked on a content fix** |

## Ledger — 2026-09-17 rebuild + push — DONE (Story 21.6)

The standalone's content from character offset 6,347 onward (everything after the confirmed-real
header/stat-strip/Act I opening) was authored fresh — not a revert, not a re-run of the same broken
generation path — grounded in the Dream, the archived canonical Spec + its `constitution-provenance.md`
companion, and the archived PRD's FR-by-FR provenance/delta findings, Jobs To Be Done, four Key User
Journeys, Glossary, NFRs, risk register, and full Success Metrics catalog. `facts.yaml` untouched.

| Artifact | Measured | Design etag | Notes |
|---|---|---|---|
| `Unity Data Stack Infographic standalone.html` | 95360 B · 32 sections · 6 acts · 3 SVG · 15 tables | `1789645202687610` | `deck-facts --check`: 0 unmarked / 0 mismatch (12 drifted / 7 unshown — expected, `facts.yaml` not regenerated); Chromium render at 1240 px clean, 0 overflow, 0 empty sections; pushed and read back SHA-256-identical (`a2a1665c…`) |
| `facts.yaml` | unchanged, 32 facts at tree `506ad58622` | — | not touched by this story, per its own boundary |

`PENDING-PUSH` above (2026-09-17 blocked entry) is now cleared by this entry's etag. The other four
`project/` files remain byte-identical to Design, unchanged since the 2026-09-17 verification pass.
