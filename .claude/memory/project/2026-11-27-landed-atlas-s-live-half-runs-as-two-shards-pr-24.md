---
name: "2026-11-27-landed-atlas-s-live-half-runs-as-two-shards-pr-24"
description: "2026-11-27 LANDED: atlas's live half runs as two shards. PR #2419 merged as 735010abbf (Merge pyforge-steward/117-28 in…"
metadata:
  type: project
---

2026-11-27 LANDED: atlas's live half runs as two shards. PR #2419 merged as 735010abbf (Merge pyforge-steward/117-28 into main; steward Story 117.28). atlas-live-test takes a group: [1, 2] matrix; each of its task's three pytest runs takes its pytest-split group from tests/durations/pyforge-atlas-live.json (637 tests, written from empty under xdist with four workers), and each shard uploads atlas-live-<group>.json for atlas-gate. On the PR's CI run the shards' jobs took 86 and 100 s (test steps 49 and 67 s) against 97 to 126 s unsharded. Atlas's station path is now set by atlas-test (97 to 115 s per shard) and its gate; the run ended at +145 s on marshal-gate. Next levers: atlas's package half, and marshal's tea-architecture smoke test (37.9 s on CI), which alone sets marshal's second live shard.
