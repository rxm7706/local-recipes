# Foundry epoch (Story 44.3 / fnd:CAP-1)

Operator flipped `44-3-open-the-foundry` on **2026-09-13** (explicit: create
the second git root; protect `main`; trunk-based from the start).

| Field | Value |
|---|---|
| Remote | `https://github.com/rxm7706/python-foundry` (private, permanently) |
| Epoch SHA | `6e0607b530f5fa5db2faffd12cbc49da9d880083` |
| Trunk | `main`, protected: PRs required, force-push off, deletions off |
| Merge | merge commits only (`allow_squash_merge=false`, `allow_rebase_merge=false`) |
| `pyforge.cutover_root` | `local-recipes` (`src/platform/config/flags.json` on foundry) |
| Local oracle | `pixi run estate-smoke` on a clone (no `recipes/`, name `pyforge`, no solver-farm deps) |
| Secrets | none yet — later rows of kind `secret` via `steward keys` |

`local-recipes` remains the root of record. 44.9 / 44.10 stay `blocked`.
