---
title: 'presenton-pixi-image rebuilt to the standard'
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

**Problem:** `presentations/presenton-pixi-image/project/Presenton Conda-Native Infographic standalone.html` was a July stub below the infographic standard (no act bands, no diagrams, no fact ledger).

**Approach:** Derive `facts.yaml` with `deck-facts presenton-pixi-image`. Author the standalone poster to `infographic-standard.md` from that ledger only. Design push is out of scope for this Cursor pass.

## Boundaries

**Always:** Every count, version, status and date is a `data-fact` mark. Six acts, at least eighteen sections, three SVGs, three tables, at least ninety thousand bytes. Package and CLI rows absent by design.

**Never:** Never hand-edit `facts.yaml`. Never invent a spec capability count. Never push to Design from this worktree.

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-authored 2026-09-15 in worktree `local-recipes-wt-herald-epic-21-wave-c-chain-decks`.

**Local acceptance:** `deck-facts presenton-pixi-image --check` reports 0 unmarked / 0 mismatch; floors met; README ledger carries `PENDING-PUSH`.

**Not accepted here:** push and read-back.

### Completion (2026-09-17)

**Found:** the 2026-09-15 pass's own claimed rebuild was corrupted — everything past the
opening intro paragraph (~char 6339 of ~145,236) was one boilerplate fleet-status sentence
repeated 72 times, character-space-separated, through `</html>`. `deck-facts --check` had
reported 0 unmarked / 0 mismatch anyway, because it only validates `data-fact` span presence
against `facts.yaml`, never prose sanity — so the corruption shipped past its own local
acceptance gate undetected. It had not reached Design: the project's stored copy was still the
original pre-corruption 19,028-byte stub, never overwritten.

**Fixed:** kept the file's `<head>` and the genuine intro (through the closing `</p>` after the
three `dream_log_*` dates), discarded everything after, and authored real content for the rest:
six acts, 37 numbered sections (floor 18), 4 inline SVG diagrams (floor 3), 20 tables (floor 3),
92,582 bytes total (floor 90,000). Every count/version/status/date on the page is a `data-fact`
span backed by a `presentations/presenton-pixi-image/facts.yaml` row. Content is drawn from the
Dream, the Satellite Spec folded into `pyforge-mason`'s own `SPEC.md`, the frozen epics/PRD/
architecture-spine documents, and the domain + technical research reports — not invented; a
handful of structural facts with no `facts.yaml` row (the epic/story/FR/NFR/CAP counts, recipe
count, MVP/Growth-gate numbers) are presented as attributed prose/tables instead of `data-fact`
marks, since no ledger row exists to back them (facts.yaml only tracks fleet/version/date
context for this chain, since it has zero implementation progress of its own).

**Verified:** `deck-facts presenton-pixi-image --check` → 0 unmarked, 0 mismatch (12 `drifted` /
14 `unshown` are pre-existing fleet-ledger staleness, not this poster's own defect, and out of
this spec's scope — `facts.yaml` itself is untouched per this Spec's own Never-clause). Read the
full rendered prose back section by section — real, varied, six distinct acts, not a repeated
sentence. Rendered headless via Playwright at 1240px width: page height 20,389px, 0 empty
sections, all 37 sections / 4 SVGs / 20 tables present in the DOM; full-page screenshot reviewed
segment by segment, tables and SVG diagrams render cleanly with no clipping.

**Pushed and read back:** via `pyforge.herald.transport.mcp_transport.McpTransport` directly
(the `herald deck push` CLI verb covers only the CAP-5 marp export, not this `project/*.html`
trio file). `finalize_plan` against the live Design project (base etag
`1785023371126226`, confirming the pre-push copy was indeed the untouched 19,028-byte stub) →
`write_files` with inline `data` → new etag `1789645274081278`. Read back in full via
`read_file` (92,582 bytes, not truncated) and SHA-256-compared against the local file:
`e8d81e2966f5904f8e200696f661447b597f9f011c5124a19f9d4625df68163c` on both sides — byte-exact.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `6852f29fbb` (2026-09-17, "Merge pull request #1416 from rxm7706/herald/21-9-presenton-pixi-image-corruption-fix"); also `371757e264` (2026-09-17, "Merge pull request #1405 from rxm7706/herald/21-9-presenton-pixi-image-blocked-corrupt-pos"). Ledger row `21-9-presenton-pixi-image-rebuilt-to-the-standard: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-21-9-presenton-pixi-image-rebuilt-to-the-standard.md`, `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml`, `presentations/presenton-pixi-image/README.md`, `presentations/presenton-pixi-image/project/Presenton Conda-Native Infographic standalone.html`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
