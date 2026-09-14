# Deck inventory — measured 2026-09-13

Companion to `SPEC.md` (CAP-3, CAP-4). Fourteen of fifteen `presentations/` folders carry a
`project/<Name> Infographic standalone.html`; `agentic-sdlc` has only a marp render and is
BMAD-branded, so it is outside this Spec. Design project ids come from each deck's README
`## Design project` section; `herald deck status` reported every row `linked: false` on this
date (no `.herald/bridge-state.json`).

| Deck | Persona (display) | Design project | Bytes | Sections | Acts | SVGs | Last pull | Wave |
|---|---|---|---|---|---|---|---|---|
| pyforge-atlas | PyForge Atlas | `2acb0575-9997-442b-bb0e-6207d78f6648` | 15,678 | 6 | 0 | 0 | 2026-07-24 | A |
| pyforge-doctor | PyForge Doctor | `46dbbdea-6f8d-45c6-9309-15d1f297beeb` | 14,419 | 5 | 0 | 0 | 2026-07-24 | A |
| pyforge-herald | PyForge Herald | `ff879a32-9741-4cf5-948f-d67040481d24` | 16,720 | 6 | 0 | 0 | 2026-07-25 | A |
| pyforge-marshal | PyForge Marshal | `ad84d4f6-c292-42c8-98bf-ede78a567773` | 91,340 | 19 | 6 | 3 | 2026-08-01 | A |
| pyforge-mason | PyForge Mason | `a7a2c3b1-5718-49fa-8c90-71d44d57eae9` | 14,404 | 6 | 0 | 0 | 2026-07-25 | A |
| pyforge-scribe | PyForge Scribe | `a1e42dac-7cee-438b-9acc-2523985b5253` | 15,978 | 6 | 0 | 0 | 2026-07-24 | A |
| pyforge-steward | PyForge Steward | `573d6554-0095-4126-b13f-cd537279ff8a` | 14,475 | 6 | 0 | 0 | 2026-07-24 | A |
| pyforge-warden | Warden | `100ca8cc-8daa-409a-8564-1f8d79c579d2` | 411,764 (bundle; 192,472 content) | 18 | 0 | 15 | 2026-07-24 | A (visual reference; rebuild adds the act arc and the ledger, keeps the form) |
| pyforge-genesis | PyForge Genesis | `6af4c28d-d510-4e9b-b788-6c0e5d651183` | 47,877 | 9 | 0 | 0 | 2026-07-25 | B |
| pyforge-unifying-strategy | The Canopy (masthead now reads "Foundry Platform" post-2026-09-13 pull, unreconciled — see deck's own README) | `1e4020bc-7f7f-43b2-9219-0904d4863df6` (created 2026-09-13, Story 20.12) | 236,761 | 23 | 7 | 3 | 2026-09-13 | B (structure reference; rebuild re-derives its facts and seeds Design) |
| unity-data-stack | Unity Data Stack | `0494e2b0-7132-43b7-8ff2-4b4b42fa8384` | 18,588 | 7 | 0 | 0 | 2026-07-25 | later (chain deck; Design head verified identical to disk 2026-09-13) |
| wasm-analytics-stack | Wasm Analytics Stack | `45c841c6-e807-4fee-a92a-f8e89cb890b4` | 18,713 | 6 | 0 | 0 | 2026-07-25 | later (chain deck) |
| deckcraft | Deckcraft | `59c42e9c-7c90-431d-adae-b0021dd3f727` | 15,774 | 6 | 0 | 0 | 2026-07-25 | later (chain deck) |
| presenton-pixi-image | Presenton Conda-Native | `c824a332-8e43-4b17-bf84-f38307085289` | 19,028 | 7 | 0 | 0 | 2026-07-25 | later (chain deck) |

Every Wave A/B Design project already holds `reference/Warden Infographic standalone.html`
(seeded 2026-07-24) and is bound to Modernist `fbc1d6c8-b35f-4df6-9044-a64d2675427b`.

## Known-stale facts in the deep posters (to be replaced by ledger rows)

| Poster | Says | Live 2026-09-13 |
|---|---|---|
| Marshal | `bmad-method 6.10.0`, `bmad-loop 0.9.0` | BMAD core 6.12.0; bmad-loop per `pixi.toml` pin |
| Marshal | "128/333 fleet-wide", "Marshal Epic 1 · 10/10" | fleet 846/865 stories, 183/188 epics; marshal 248/249 |
| Marshal | Herald 4/27 · Mason 4/48 · Doctor 5/18 · Scribe 2/13 · Steward 3/26 · Atlas 57/57 · Warden 43/43 | herald 67/68 · mason 66/66 · doctor 95/95 · scribe 20/20 · steward 206/222 · atlas 94/95 · warden 49/49 |
| Unifying Strategy | "CAP-1..18 closed 2026-08-26 · CAP-19 live", "40/40 five-tier" | re-derive from `spec-pyforge-unifying-strategy/SPEC.md` and steward's ledger at rebuild time |
| Warden | every stat (July 2026 authoring) | re-derive from warden's ledger, SPEC and CLI at rebuild time |
