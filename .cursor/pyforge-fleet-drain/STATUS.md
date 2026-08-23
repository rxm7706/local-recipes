# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23 ~17:00 CDT
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
| Backlog | **marshal 22** · **steward 4** (**26 total**; 12-7 skipped forever) |
| Drained | atlas, doctor, herald, mason, scribe, warden |

## Merge policy (operator override — 2026-08-23)

GitHub Actions billing blocks CI. Until restored: **local tests green → `gh pr merge <n> --merge --admin`** (never squash). Document in spec `shipped_ref` + Auto Run Result.

## In-flight (canonical only — do not duplicate)

| Station | Story | Canonical agent |
|---------|-------|-----------------|
| marshal | `20-8` | launching |
| steward | `16-5` | launching (skip 12-7) |

## Operator skip

| Story | Reason |
|-------|--------|
| steward `12-7` | Live OCP — permanently `skip_on_blocked` until CRC available |

## Recently merged (admin merge, no CI)

| Station | Story | PR |
|---------|-------|-----|
| steward | `16-4` | [#693](https://github.com/rxm7706/local-recipes/pull/693) merge `b439626af4` ([Steward 16-4](cb73af2f-982d-4638-9f98-fda65b7ff656)) |
| marshal | `20-7` | [#692](https://github.com/rxm7706/local-recipes/pull/692) merge `1a5f2d32c5` ([Marshal 20-7](8c9bd6f9-a33f-407d-8eef-6e4d8b67e3ca)) |

```bash
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary
gh pr list --repo rxm7706/local-recipes --state open
```
