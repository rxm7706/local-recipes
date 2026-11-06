---
name: "2026-11-06-operator-rulings-on-wiring-the-seven-start-tools"
description: "2026-11-06 operator rulings on wiring the seven start tools (N1 second half, spec-pyforge-unifying-strategy CAP-20, ste…"
metadata:
  type: project
---

2026-11-06 operator rulings on wiring the seven start tools (N1 second half, spec-pyforge-unifying-strategy CAP-20, steward Epic 119): 'All seven'; laptop stack first, the worker image later (DW-steward-119-1); 'Dispatch, gated' (start_loop needs pyforge:admin and pyforge.steward.start_loop_dispatch, which ships off); 'Accept list' (one fixed verb per face in django_pyforge/station_cli.py, a caller passes a target only). Operator-owned: turning that flag on and the first real dispatch (DW-steward-119-4). A worker subprocess sits outside the session hook, so that table is the whole guard. Trap: mason recipe build exits 0 whatever the build did, so read data.returncode.
