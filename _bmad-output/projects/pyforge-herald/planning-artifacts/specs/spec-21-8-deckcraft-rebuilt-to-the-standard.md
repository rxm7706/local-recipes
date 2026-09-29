---
title: 'deckcraft rebuilt to the standard'
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

**Problem:** `presentations/deckcraft/project/Deckcraft Infographic standalone.html` was a July stub below the infographic standard (no act bands, no diagrams, no fact ledger).

**Approach:** Derive `facts.yaml` with `deck-facts deckcraft`. Author the standalone poster to `infographic-standard.md` from that ledger only. Design push is out of scope for this Cursor pass.

## Boundaries

**Always:** Every count, version, status and date is a `data-fact` mark. Six acts, at least eighteen sections, three SVGs, three tables, at least ninety thousand bytes. Package and CLI rows absent by design.

**Never:** Never hand-edit `facts.yaml`. Never invent a spec capability count. Never push to Design from this worktree.

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-15 in worktree `local-recipes-wt-herald-epic-21-wave-c-chain-decks`.

**Local acceptance:** `deck-facts deckcraft --check` reports 0 unmarked / 0 mismatch; floors met; README ledger carries `PENDING-PUSH`.

**Not accepted here:** push and read-back.

## Blocked — 2026-09-17 (content corruption, do not push further)

`deck-facts --check` reporting 0 unmarked / 0 mismatch is **not** a content-sanity check — it
only validates `data-fact` span presence, and does not catch this. On live inspection while
executing the push+read-back leg, `presentations/deckcraft/project/Deckcraft Infographic
standalone.html` (the same file this spec's own 2026-09-15 pass authored) was found corrupted:
from byte offset 6235 to near EOF (72 occurrences, ~96% of the file by span), a boilerplate
paragraph repeats with every character space-separated ("T h e   f a c t o r y   a l r e a d y
r u n s   a   t r a c k e d   f l e e t ...") in place of real section content. Confirmed via
`python3` byte-offset/regex inspection of the local file (git blame: commit `e483288d54f`,
"Rebuild the four chain-deck posters from their fact ledgers", 2026-09-15 — already on `main`,
predates this session). The same corruption independently affects the sibling
unity-data-stack, wasm-analytics-stack, and presenton-pixi-image posters from the same commit.

**This story's push+read-back leg had already run before the corruption was discovered.** The
corrupted local bytes were pushed to the live "Deckcraft deck" Design project
(`59c42e9c-7c90-431d-adae-b0021dd3f727`, path `Deckcraft Infographic standalone.html`, new etag
`1789639747822045`) and read back byte-identical — the read-back correctly proved the push was
byte-faithful, it just faithfully mirrored already-corrupted local content. Re-fetched via
`read_file` after this discovery: the live Design copy carries the identical 72-occurrence
corruption at the identical byte offset — confirmed, not assumed.

No further push attempted. No content fix attempted here (out of this spec's Code Map — a
content-authoring fix belongs to whoever restores the poster's real prose, then a fresh
push+read-back cycle). Story 21.8 is `blocked` pending that fix; the corrupted Design copy is
left as-is pending an operator/coordinator decision on remediation (fix-and-repush vs. revert).

## Done — 2026-09-17 (content rebuilt for real, pushed, read back byte-identical)

The content-authoring fix this entry deferred above is now complete. Everything from byte
offset 6235 onward (the corrupted ~96% of the file) was replaced with genuine prose, tables and
inline SVG diagrams, sourced from the archived `spec-deckcraft` planning chain
(`archive/_bmad-output/projects/pyforge-herald/planning-artifacts/{specs/spec-deckcraft/SPEC.md,
epics-deckcraft.md, architecture/architecture-deckcraft-2026-05-10/architecture.md,
briefs/product-brief-deckcraft{,-distillate}.md, prds/prd-deckcraft-2026-05-10/*,
research/*-2026-07-25.md}`) plus the still-live `docs/dreams/pptx-deck-generation.md`,
`presentations/deckcraft/{facts.yaml,README.md}` and the still-correct `project/Deckcraft.dc.html`
/ Executive Summary. The opening intro paragraphs (byte 0–6235) were left untouched — they were
never corrupted.

**Structure:** 41 numbered sections (floor 18), 6 act bands exactly, 4 inline SVG diagrams (floor
3: a three-layer pipeline topology, a document-journey flow, a hardware-tier ladder, a
now/next/later roadmap ladder), 25 tables (floor 3), 93,813 bytes (floor 90,000).

**Facts:** every count/version/status/date in new prose is either a `data-fact` span over an
existing `facts.yaml` row (`tree_commit_date`, `herald_*`, `fleet_*`, `cfe_skill_version`,
`recipes_count`) or a static planning-chain number with no `facts.yaml` row — 28 stories / 6
epics / 52 FRs / 23 NFRs / 15 ADs / 10 patterns / 9 CAPs (from the archived epics/PRD/architecture,
not the live ledger) — deliberately left unmarked per the deck's own established convention (the
untouched intro already treats the pymupdf item the same way): a number with no ledger row is
never dressed as a tracked count. `pixi run -e local-recipes deck-facts deckcraft --check`: **0
unmarked, 0 mismatch** (12 `drifted` — the ledger's 2026-09-15 snapshot vs. live 2026-09-17 fleet
counts, expected and out of this story's scope per the task's own instruction to use `facts.yaml`
as-is; 19 `unshown` — facts.yaml rows this poster's content doesn't happen to reference).

**Honesty check (the thing that failed last time):** the file was read back in full (two `Read`
passes covering all 266 lines) and confirmed to be real, varied, six-act content — not a repeated
sentence. Rendered headless via Playwright at 1240px width (`page scrollHeight: 20453`); every
`section.sec`, `div.act`, `table` and `svg` element has a non-zero bounding box (0 of 76 checked
elements clipped/blank); PNG crops of the top, an SVG diagram, a mid-document table run, and the
closing Creed band were visually inspected and all render cleanly.

**Push + read-back:** `.herald/bridge-state.json` bootstrapped (the four chain decks' READMEs
still fail `registry.read`'s two-line-body parser per Story 21.10's own scope — `deckcraft` was
registered by hand with the project id already on record in the README). Pushed via
`pyforge.herald.transport.mcp_transport.McpTransport` directly (`herald deck push`'s CLI verb only
covers the CAP-5 marp export, not this file): read the live file first (etag `1789639747822045`,
145,025 B, SHA-256 `5cb3f51d…` — confirmed byte-identical to the corrupted local content this
entry already recorded, i.e. Design really did still hold the corruption), `finalize_plan` +
`write_files` with `if_match` on that etag, new etag `1789645287157037`. Read back in full (93,813
B, under the 256 KiB cap, `truncated: False`) and SHA-256-compared: **byte-identical to the local
file** (`97e9b485…`). Explicitly re-checked for the corruption pattern in the read-back body:
`"factory already runs a tracked fleet"` occurs **0** times (was 72). The corrupted Design copy is
gone.

Story 21.8 is `done`. `sprint-status-ledger.yaml` updated to match; the gitignored Tier-3
`implementation-artifacts/sprint-status.yaml` symlink does not exist in this worktree (same gap
Story 21.4 hit) so only the tracked ledger twin was updated.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `3304bc19b8` (2026-09-17, "Merge pull request #1415 from rxm7706/herald/21-8-deckcraft-rebuilt-standalone-fix"); also `13e4459692` (2026-09-17, "Merge pull request #1406 from rxm7706/herald/21-8-deckcraft-push-readback"). Ledger row `21-8-deckcraft-rebuilt-to-the-standard: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-8-deckcraft-rebuilt-to-the-standard.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml`, `presentations/deckcraft/README.md`, `presentations/deckcraft/project/Deckcraft Infographic standalone.html`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
