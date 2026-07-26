# pyforge-atlas — per-epic retrospectives (tracked, durable)

**Tier 2, git-tracked — deliberately not `implementation-artifacts/retros/`.**

The default BMAD home for retros is Tier-3 `implementation-artifacts/`, which is
gitignored. This project is the reason not to use it: its own
`implementation-artifacts/deferred-work.md` is **truncated to 9 of 54 entries**
(collateral of the 2026-07-19 copy failure), and because the directory is
gitignored there is no tracked copy of the other 45. The deferrals were made
honestly; the record of them was lost.

A retrospective of a **shipped** effort is permanent record, in the same class as
the story specs this repo promoted to `planning-artifacts/specs/` on 2026-07-25.
So these land tracked.

## Provenance

Atlas ran through an **in-session agent loop**, not `bmad-loop`, so no
`.bmad-loop/runs/` journals exist. These retros are reconstructed from
**tracked** evidence only:

- `../../spec-archive/pyforge-atlas-effort-run-log.md` — per-wave narrative, PR
  numbers, per-story review findings, the 54-deferral index
- `../../spec-archive/retro-story-files/` — 20 reconstructed story files with Dev
  Agent Record / Completion Notes / File List / Review Triage Log
- `../epics.md` — intent + acceptance criteria
- merged PRs **#58–#105** and the `main` commit log

Waves map 1:1 to epics: Epic 1 = Wave 0 · 2 = A · 3 = B · 4 = C · 5 = D · 6 = E ·
7 = F · 8 = G · 9 = H.

## Status

| Epic | Wave | Retro |
|---|---|---|
| 1–8 | 0, A–G | this directory, written 2026-07-25 |
| 9 | H | **satisfied by the CFE Rule-2 retro** — skill v8.78.0→v8.79.0, PR #103. Recorded `done` in `sprint-status.yaml` before these ran. |

Written 2026-07-25, one week after ship (2026-07-18), on the operator's decision
to run rather than waive them.
