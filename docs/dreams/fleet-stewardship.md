---
title: Fleet stewardship — tend every feedstock we can touch
type: practice
owner: mason
status: realized
---

# Fleet stewardship — 769 feedstocks, none left behind

## The Dream

*(Naming: this practice Dream — feedstock tending under Mason + Doctor — is
distinct from the **Steward persona**, the platform/ops station:
[[pyforge-steward]].)*

Maintainership as a *practice*, not a backlog: every feedstock this factory can
modify is kept current with upstream, on the modern recipe format, built for
every platform its users need — and when CI goes red anywhere in the fleet, a
disciplined remediation loop turns it green again. A **perpetual** dream:
realized as recurring waves, never finished.

## What is real (the three workflow engines)

- **`feedstock-refresh`** — the two-track bulk refresh of ALL 769 modifiable
  feedstocks: Track A (sole-maintainer, 537; waves B–F shipped, Wave H
  total-coverage open) and Track B (co-maintainer, 232; adds etiquette rules).
- **`feedstock-platform-expansion`** — the per-feedstock dual-goal workflow:
  latest CFE shape at latest upstream + widened build matrix (osx-arm64,
  linux-aarch64) in one PR.
- **`feedstock-failure-remediation`** — the red-PR loop: triage
  FLAKE / REAL_FIX / BLOCKED, execute-locally-first, maintainer-edit push,
  rerender-after-push.
- The sibling **conda-forge-tracker** repo (markdown-first personal tracker) and
  the atlas-derived maintainer lists on `rxm7706/about`.

## The frontier

- Track A Wave H (179 feedstocks remaining); Track B execution.
- Signal-driven scheduling: let [[pyforge-doctor]]'s pulse (staleness, CVE,
  abandonment) *order* the waves instead of alphabetical sweeps.

## Realization log

- **2026-06 → 07** — waves B–F shipped; the 12-PR remediation batch (G31–G34)
  became the workflow's worked example.
- **2026-07-23** — Dream retro-seeded; engines live as timeless workflow specs
  (legacy tier), powered by [[packaging-factory]] intelligence from [[pyforge-atlas]].
