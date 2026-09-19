---
name: "coverage-gates-run-per-station-in-that-station-s-own-pixi-en"
description: "Coverage gates run per station in that station's OWN pixi environment: scripts/coverage_gates_ci.py evaluates only the…"
metadata:
  type: feedback
---

Coverage gates run per station in that station's OWN pixi environment: scripts/coverage_gates_ci.py evaluates only the modules a branch touches, and the pyforge-station-coverage-gates task walks every station with COVERAGE_GATES_STATIONS=<station> in -e pyforge-<station>. A single invocation from one env (e.g. -e pyforge-steward for a marshal change) measures nothing for the other station and reports a false green. Run pixi run -e pyforge-guild pr-preflight, or COVERAGE_GATES_STATIONS=<station> pixi run --frozen -e pyforge-<station> python scripts/coverage_gates_ci.py --base origin/main --head HEAD --suites unit for one station.
