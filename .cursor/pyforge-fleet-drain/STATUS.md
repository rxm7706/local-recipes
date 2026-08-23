# PyForge fleet drain — status snapshot

**Updated:** 2026-08-23  
**Playbook:** [PLAN.md](./PLAN.md)  
**Queues:** [queues.yaml](./queues.yaml) (regenerate with `generate-queues.py`)

## Campaign

| Field | Value |
|-------|--------|
| Mode | `drain_to_zero` |
| Active stations | **marshal**, **steward** |
| Drained (ledger) | atlas, doctor, herald, mason, scribe, warden |

## 2026-08-22 → 2026-08-23 closeout

Doctor, mason, and warden reached **zero backlog** on tracked ledgers (warden through `8-2`, mason through `9-2`, doctor through `16-1`). The 2026-08-22 pause queue for those three stations is **complete**.

## Known ledger lag

Run `pixi run -e local-recipes sprint-ledger-sync --project steward` after confirming merges on main:

- `12-3-air-gap-parity` — merged via PR #622; ledger may still read `backlog`
- `12-2-gke-as-a-portability-profile` — done on ledger

## Next dispatch (preflight first)

| Station | Next story | Notes |
|---------|------------|--------|
| **marshal** | `11-5-referenced-dependency-verification-and-doctor-delegation` | 49-story queue; Epic 22 productizes this playbook |
| **steward** | `12-3-air-gap-parity-is-a-failing-check` | Skip ledger sync if already on main; then `12-4` … `12-9` (new OCP CI spec seeded) |

## In-flight / open branches

Stale remote branches may exist from prior waves (`git ls-remote --heads origin 'marshal/*' 'steward/*'`). Preflight per PLAN.md before each dispatch — do not duplicate work.

## Operator commands

```bash
# Refresh queues from ledgers
python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary

# After each merge
pixi run -e local-recipes sprint-ledger-sync --project <station>
python3 .cursor/pyforge-fleet-drain/generate-queues.py
```
