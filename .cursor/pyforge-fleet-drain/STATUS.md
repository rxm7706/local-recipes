# PyForge fleet drain — status snapshot

**Updated:** 2026-08-24 ~03:45 CDT
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | `parent-chat` (this Cursor session — sole dispatcher) |
| `held_since` | 2026-08-23T09:40-05:00 |
| `state` | `active` |

**HARD:** Do not launch another fleet-drain coordinator Task.

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · merge-in-agent · **singleton coordinator** |
| Backlog | steward **12-7 only** (skipped) |
| Drained | atlas, doctor, herald, mason, scribe, **steward**, warden, **marshal** |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| — | — | none — marshal Epic 25 complete; fleet drain complete except steward 12-7 skip |

## Dispatch sequencing (operator — 2026-08-24)

**marshal DRAINED** after `25-7` / Epic 25. Fleet drain complete (steward `12-7` remains skipped).

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `25-7` | [#722](https://github.com/rxm7706/local-recipes/pull/722) merge `ac6c223c54` · **Epic 25 done** · CAP-7 · **marshal DRAINED** |
| marshal | `25-6` | [#721](https://github.com/rxm7706/local-recipes/pull/721) merge `8d5e439f2d` · CAP-6 / DW-BL011-2 closed |
| marshal | `24-3` | [#720](https://github.com/rxm7706/local-recipes/pull/720) merge `39cee7530c` · **Epic 24 done** |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
