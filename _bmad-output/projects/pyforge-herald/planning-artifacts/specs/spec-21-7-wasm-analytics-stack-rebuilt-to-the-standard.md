---
title: 'wasm-analytics-stack rebuilt to the standard'
type: 'feature'
created: '2026-09-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
verdict_mode: advisory
---

<intent-contract>

## Intent

**Problem:** `presentations/wasm-analytics-stack/project/Wasm Analytics Stack Infographic standalone.html` was a July stub below the infographic standard (no act bands, no diagrams, no fact ledger).

**Approach:** Derive `facts.yaml` with `deck-facts wasm-analytics-stack`. Author the standalone poster to `infographic-standard.md` from that ledger only. Design push is out of scope for this Cursor pass.

## Boundaries

**Always:** Every count, version, status and date is a `data-fact` mark. Six acts, at least eighteen sections, three SVGs, three tables, at least ninety thousand bytes. Package and CLI rows absent by design.

**Never:** Never hand-edit `facts.yaml`. Never invent a spec capability count. Never push to Design from this worktree.

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-15 in worktree `local-recipes-wt-herald-epic-21-wave-c-chain-decks`.

**Local acceptance:** `deck-facts wasm-analytics-stack --check` reports 0 unmarked / 0 mismatch; floors met; README ledger carries `PENDING-PUSH`.

**Not accepted here:** push and read-back.

## Completion (2026-09-17)

The 2026-09-15 hand-authored pass (commit `e483288d54f`) was itself corrupted: everything
from character offset 6341 onward (~95% of the file) was a single boilerplate sentence
repeated dozens of times, character-space-separated, with no real content — `deck-facts
--check` never caught it because it only validates `data-fact` span presence, not prose
sanity. The corrupted content had already been pushed to the live Design project before
the corruption was discovered (Story 21.4/21.7 push work), so the corruption was live,
not merely at risk.

This pass replaced the entire corrupted span with real, subject-specific content —
21 numbered sections across the canonical six acts, 3 inline SVG diagrams (pipeline
topology, upload-journey flow, isolation-gate ladder), 13 tables (capabilities, layer
map, pinned stack, success metrics, five named risks, ten architecture invariants,
capability→invariant map, NFRs, per-leader value, five open questions, three integration
seams) — sourced from the Dream, the folded Atlas Spec (CAP-27..31), and the archived
pre-fold Brief/PRD/Architecture (user journeys, glossary, kill criteria, risk table,
stack pins, deferred items). Every count/version/status/date is a `data-fact` mark
against `presentations/wasm-analytics-stack/facts.yaml` (untouched, used as-is); the
one number with no facts.yaml row — the capability/FR/AD count — is named in prose
instead of guessed. Final file: 91,427 bytes, `deck-facts --check` reports 0 unmarked /
0 mismatch, facts 30/30.

Verified: read the full rebuilt file back and confirmed by eye it is real, varied,
structured content (no repeated sentence anywhere); rendered headless at 1240px width
(19,612px full-page height) and visually inspected the whole render — no broken or
empty sections. Found and fixed one bug from the rebuild itself (a stray duplicate
`</p></section>` at the section-21/Creed seam) before pushing.

Pushed to Design (`45c841c6-e807-4fee-a92a-f8e89cb890b4`) via `finalize_plan` +
`write_files`, etag `1789639734959225` → `1789646107497288`. Read the pushed file back
fresh via `read_file`, decoded its HTML-entity-escaped body, and confirmed SHA-256
byte-exact match against the local file (`fc5ac86ad0264d8e082cbdc1646fc2a02b6cec6fa78e3c9e480b95742429f776`)
— the corrupted boilerplate pattern is confirmed absent from the re-read content. The
corrective push fully supersedes the corrupted etag; the live Design project now carries
the real content.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `095c9a50c9` (2026-09-17, "Merge pull request #1418 from rxm7706/herald/21-7-wasm-analytics-stack-fix"); also `ce9c791abc` (2026-09-17, "Merge pull request #1407 from rxm7706/herald/21-7-wasm-analytics-stack-blocked-corrupt-pos"). Ledger row `21-7-wasm-analytics-stack-rebuilt-to-the-standard: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-7-wasm-analytics-stack-rebuilt-to-the-standard.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml`, `presentations/wasm-analytics-stack/README.md`, `presentations/wasm-analytics-stack/project/Wasm Analytics Stack Infographic standalone.html`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
