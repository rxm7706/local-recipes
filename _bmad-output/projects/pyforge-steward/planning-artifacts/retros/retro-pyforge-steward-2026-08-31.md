---
title: "pyforge-steward — retrospective, post-Canopy-era reconciliation window"
created: "2026-08-31"
updated: "2026-08-31"
covers: "Everything since retro-pyforge-steward-2026-08-26.md (commit 112d6099a8) through 2026-08-31 — 21 commits touching src/shared/packages/pyforge-steward, src/platform, or this project's planning-artifacts"
evidence: "git log --oneline 112d6099a8..HEAD -- src/shared/packages/pyforge-steward src/platform _bmad-output/projects/pyforge-steward; pixi run -e pyforge-steward pyforge-steward-test"
---

# pyforge-steward — Retrospective, 2026-08-31

**Trigger:** `chain-currency-sweep` flagged the `code→retro` checkpoint stale (code — the
package's `pyproject.toml` — last touched 2026-08-30, prior retro dated 2026-08-26, exceeding the
2-day grace window per `CHAIN-CURRENCY-RUNBOOK.md`). Companion to
`retro-pyforge-steward-2026-08-26.md` (Epics 5–37, the Canopy era) — this covers only what landed
since that retro's own commit (`112d6099a8`).

## What landed, and what didn't

**No new story shipped.** The sprint ledger stayed at 38 epics / 170 real story keys `done`
across this window — the one epic-count delta since the last retro (37 → 38) is Epic 38
(`spec-mcp-factory-stdio-translator`), and it was decomposed **retroactively** over code that
already existed (commit `085e2e9993`, "retroactively decompose the MCP factory stdio translator,
close the last chain-completeness finding") — not a new build. Its single story
(`38-1-the-translator-wraps-a-factory-tool-over-stdio-and-never-claims-to-be-the-crc-fix`) is
`done`.

**The 21 commits in this window are reconciliation and housekeeping, not feature work:**

| Kind | Commits |
|---|---|
| Chain-currency / spec-surface drift reconciliation | `6a8fe0f5c5` (PRD/arch/epics re-dated), `3035a951e1` (drift since Epic 13), `a7721dd610` (drift + stale SKF-marker fix), `5f506bff71` (fleet-wide, 56 fails across 7 specs), `402121ef85` (this session — recovered an orphaned 2026-08-28 reconciliation commit's still-valid piece) |
| Deferred-work ledger promotion | `d70eec8458`, `27e7f340f6`, `754b21ea86`, `7b288e2dd8` |
| Retroactive decomposition / chain-completeness | `085e2e9993`, `75595f2157`, `6dff92afce` |
| Fleet-wide `epic_surfaces` widening (this session's own marshal work) | `c80bcb41f6` |
| Dream consolidation | `9adfa77052` |
| Dependency/pin maintenance | `daa35ee171` (django 5.2.17 asgiref resync), `0ab34e02b2` (same, second pass), `6ff2c008b4` (pixi 0.78.0 fleet bump) |
| Cross-station meta-test fix | `cfadb82d93` (pyforge-core sole-ownership) |
| Other-station work sharing the path filter | `e29f57b74c` (marshal), `9f9f97e09d`, `11780e08eb` (atlas) |

No commit in this window touches a Steward duty's behavior (`keys`, `deploy`, `provision`,
`budget`, `sync`, `workspace`, `upgrade`, `suite`, or the bootstrap group). The window is
entirely the fleet's own bookkeeping catching up with itself — twice over, in the
`6a8fe0f5c5` / `3035a951e1` / `a7721dd610` sequence, which is itself a visible instance of the
"repeated manual widening" pattern this session's `docs/dreams/marshal-dependency-aware-dispatch.md`
targets at the marshal-dispatch layer.

## Behavior verification

`pixi run -e pyforge-steward pyforge-steward-test`: **993 passed, 0 failed** (2026-08-31, current
`main`). No new test files appeared in this window (consistent with no new story landing); the
full suite still passes after the pin bumps and drift reconciliations above, which is the
relevant confirmation — a version bump or a spec-surface stamp is exactly the kind of change that
can silently break something without a green run.

## This session's own contribution to the window

Two of the 21 commits are this session's own work, both already independently verified before
this retro ran: `402121ef85` recovered the still-valid piece of an orphaned worktree commit
(the `spec-python-agent-platform` surface fix for `build-pixi-mirror.py`, CAP-6/Story 12.3 — every
individual claim re-checked against current `main` before applying, per this session's own
hygiene-sweep discipline) and `c80bcb41f6` widened `epic_surfaces` fleet-wide, including
Steward's own `marshal-policy.toml`, to close the `MRS-GATE-007` empty-tuple gap this session
root-caused. Both are corroborated by the file-level evidence already cited in their own commit
messages; not re-litigated here.

## Previous-retro follow-through

`retro-pyforge-steward-2026-08-26.md` is narrative delivery-log, not itemized action items —
nothing to check transition status against. Its scope (Epics 5–37, "the Canopy era") is
unaffected by this window: no CAP, FR, or AD changed underneath it, only a retroactive epic
number added over code that already existed when that retro ran.

## Action items

None. No fix-now findings — the window is reconciliation work that already closed its own
findings (drift fixes, ledger promotions) as part of landing. The repeated-widening pattern noted
above already has an owned fix in flight at the marshal layer (Stories 28.12–28.15), not
duplicated here since it isn't a Steward-owned defect.

## Acceptance verdict

**Accepted.** No stories to judge against declared acceptance criteria (none shipped in this
window); the ledger's own completeness (38/38 epics, all real story keys `done`) is unchanged
from the last retro plus the one retroactive addition. Test suite clean (993/993). Nothing in
this window contradicts or reopens the prior retro's scope.

## Open questions

None material. `OQ1`/`OQ3` (a real spend meter behind `budget check`; runner reaping) remain open
per the 2026-08-26 reconciliation in `briefs/brief-pyforge-steward-2026-07-25/brief.md` —
unforced by any incident in this window, unchanged.
