---
doc_type: sync-proof
project: pyforge-herald
date: 2026-09-19
closes: DW-FU-23-6
opens: DW-FU-23-6-1
---

# Live `deck sync-all` idempotency proof — 2026-09-19

Operator-run (`HERALD_LIVE_SYNC_PROOF=1 pixi run -e pyforge-herald deck-sync-proof -- --slug <slug>`, live Claude Design credentials; the gitignored `.herald/sync-proof/` reports are transcribed here). Requested by DW-FU-23-6: the idempotency AC had only ever been exercised on the *skipped* path.

## Run 0 — `pyforge-herald` (seeded, never pulled)

- `report-20260919T200957976453Z-6d751a0e.json`: labels `['skipped']`, skipped_reason `seeded but nothing pulled yet -- run 'herald deck pull' first` — the same skipped path the DW names. Only `pyforge-warden` carries pull etags in `.herald/bridge-state.json`, so the unchanged path can only be reached through warden.

## Runs 1 and 2 — `pyforge-warden` (the one deck with pull state)

- `report-20260919T201122485002Z-8ae6ca61.json` (tree `b49ccf497b`, derived_at `2026-09-19T20:11:22.510500+00:00`): labels `['failed']`; pulled `[]`, pushed `[]`, overrode `0`, published `False`; error: `read-back after push did not match for 1 file(s) in 'pyforge-warden': pyforge-warden-infographic-standalone-2026-09-15.html -- refused rather than record an unproven push`
- `report-20260919T201203451643Z-6b319b4d.json` (tree `b49ccf497b`, derived_at `2026-09-19T20:12:03.478951+00:00`): labels `['failed']`; pulled `[]`, pushed `[]`, overrode `0`, published `False`; error: `read-back after push did not match for 1 file(s) in 'pyforge-warden': pyforge-warden-infographic-standalone-2026-09-15.html -- refused rather than record an unproven push`

**What actually happened (both runs identical):** sync-all re-derived the deck facts (`facts.yaml`: `derived_at` 2026-09-15 → 2026-09-19; doctor 22/24 → 25/28, 95/105 → 108/114, …), regenerated the marp / pptx / html artifacts and their `.stamp.json` sidecars, pushed the two PPTX artifacts to the Claude Design project (README push-and-prove ledger: read-back **identical ✓** both runs), and refused on `pyforge-warden-infographic-standalone-2026-09-15.html`: *read-back after push did not match — refused rather than record an unproven push*. The refusal is deterministic across two consecutive runs.

## Verdict

- **DW-FU-23-6 closes as verified-with-finding:** the live proof now exists on a real pulled deck; the *unchanged* path was not reached because (a) the deck was stale (facts from 09-15), so run 1 had real work, and (b) the standalone-HTML push never reads back equal, so run 2 could not converge to `unchanged` either. Idempotency of the no-op path stays unproven until (b) is fixed and a deck is fully in sync.

- **New finding — DW-FU-23-6-1 (herald, medium):** `deck sync-all` push of the standalone infographic HTML is refused on read-back mismatch every time (2/2). Likely Claude Design normalises HTML on write (whitespace / attribute order / injected support script), so byte-equality read-back can never hold for `.html` while it does for `.pptx`. Remedy candidates: compare a normalised form for HTML artifacts, or the Design-side content hash the API returns; until then the standalone poster is never re-published by sync-all.

- The re-derived warden deck (12 tracked artifacts + 5 sidecars) is committed with this record as the deck-currency refresh sync-all exists to produce (operator ruling 2026-09-19).
