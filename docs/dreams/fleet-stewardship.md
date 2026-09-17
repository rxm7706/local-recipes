---
title: Fleet stewardship — tend every feedstock we can touch
type: practice
owner: mason
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-mason]]** on 2026-09-17 (one-chain-per-station mason fold; folded from `fleet-stewardship`).
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
- **2026-09-09 (realization-gate re-read)** — `realized` **holds**, with a dated dormancy note
  (operator ruling,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.2). CAP-1 (local-mirror-first) and CAP-2 (`cfe-*` metadata) are exercised **continuously**:
  70 commits touching `recipes/` since 2026-08-10 across a 7,873-directory tree. **CAP-3 — the
  recurring campaigns — is dormant.** All three engine specs are untouched since 2026-06/07
  (`feedstock-refresh.md` last commit `1aeaf12cee` 2026-07-02; `feedstock-platform-expansion.md`
  `1bdd5a2f02` 2026-06-28; `feedstock-failure-remediation.md` `1aeaf12cee`), Track A Wave H still
  lists **179** remaining and Track B (**232**) is unstarted. Recorded so "recurring waves" is not
  read as live — the status is defensible, the narrative was not. **Greenfield note:** steward
  S-44.8 moves only in-flight and sole-maintainer recipes to `factory/recipes/`; every other
  `recipes/**` row reads `stays` and is **archived with `local-recipes`**. This Dream's CAP-1
  surface is `recipes/**` (`surface-drift: exempt`), so after the cutover most of that surface
  lives in an archived repo — which changes what "every feedstock we can touch" can mean. Neither
  this Dream nor its Spec anticipated it; consult at 44.8, not after.
