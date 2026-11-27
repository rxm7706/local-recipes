---
name: "2026-11-27-landed-the-chain-currency-sweep-scans-the-fleet-o"
description: "2026-11-27 LANDED: the chain-currency sweep scans the fleet once. PR #2436 merged as 5d53f6fdad (Merge pyforge-doctor/6…"
metadata:
  type: project
---

2026-11-27 LANDED: the chain-currency sweep scans the fleet once. PR #2436 merged as 5d53f6fdad (Merge pyforge-doctor/69-1 into main; doctor Story 69.1, spec-pyforge-steward CAP-175 realized with no text change), with 24 checks passed. board.gather_chain_layers_audits audits several projects over one load of scripts/fleet_scan.py, one scan_fleet() and one Dream orphan index (_FleetScan), each project degrading alone; gather_chain_layers_audit runs the same code with a fresh scan. scripts/chain_currency_sweep_check.py makes one batch call and reads a station the batch leaves out as could-not-run. Measured: the sweep alone 43.4 s to 6.3 s, its --json output byte for byte the same; the batch equals origin/main's per-project audit on every finding of the eight stations; on CI the Detectors job fell from 132 s to 55 s and its detectors step from 87 s to 23 s. It is no longer the longest job on a PR. Levers still open from the 2026-11-27 ranked list: the scripts-suite library part (scripts-lib-test about 55 s; whether it needs the full-history checkout, about 24 s), Platform CI shards' fixed setup (about 40 s each), herald-live builds, and the local full preflight (322 to 374 s before today's last changes).
