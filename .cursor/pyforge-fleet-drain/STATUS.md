# PyForge fleet drain — status snapshot

**Updated:** 2026-08-24 00:05 CDT
**Playbook:** [PLAN.md](./PLAN.md) · [COORDINATOR.md](./COORDINATOR.md)

## Coordinator lock (singleton)

| Field | Value |
|-------|--------|
| `owner` | — |
| `held_since` | — |
| `state` | `released` |

**Lock is free.** No coordinator is held. The 2026-08-23 `parent-chat` claim was released 2026-08-24 on campaign completion. A future coordinator may claim it per [COORDINATOR.md](./COORDINATOR.md) § Claim / release.

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` · **COMPLETE** (actionable backlog) |
| Backlog | steward **12-7 only** (`skip_on_blocked`) |
| Drained | atlas, doctor, herald, mason, marshal, scribe, steward\*, warden |

\*steward drained except permanently skipped `12-7` (live OCP).

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash).

## In-flight

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| — | — | none |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| marshal | `25-7` | [#722](https://github.com/rxm7706/local-recipes/pull/722) / finalize [#723](https://github.com/rxm7706/local-recipes/pull/723) merge `5b09bbce14` ([Marshal 25-7](20e87c08-76d1-4a60-a176-4877ea6d62e5)) · **Epic 25 done** · **marshal DRAINED** |
| marshal | `25-6` | [#721](https://github.com/rxm7706/local-recipes/pull/721) merge `8d5e439f2d` |
| marshal | `24-3` | [#720](https://github.com/rxm7706/local-recipes/pull/720) merge `39cee7530c` · **Epic 24 done** |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
