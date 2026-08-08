# Fleet readiness — 2026-08-08

Measured state of all 8 stations after the PR #318/#319/#320/#321 sequence, plus what is
actually runnable and what is not. **Derived, not asserted** — every number below came
from `sprint-status-ledger.yaml` via `generate.py::parse_sprint_status`, not from a
regex (see § *How to measure this correctly*, which exists because getting that wrong
produced two retracted findings in one day).

Regenerate with:

```bash
pixi run -e local-recipes chain-completeness-check     # the invariants
pixi run -e local-recipes forward-dependency-check     # can a story actually start
pixi run -e local-recipes dashboard-gen                # the board
```

## Where the fleet stands

| station | done | backlog | blocked | total | next runnable |
|---|---|---|---|---|---|
| marshal | 50 | 35 | 1 | 86 | `10-1-copier-engine-wrapper-the-single-seam` |
| mason | 4 | 34 | 0 | 38 | `1-10-configuration-surface-logging-and-child` |
| steward | 18 | 10 | 5 | 33 | `5-1-retire-provision-runner-bmad-loop-in-favour-of-marshal-init` |
| atlas | 38 | 8 | 0 | 46 | `12-1-kedro-skills-audit-then-adopt` |
| doctor | 17 | 1 | 0 | 18 | `5-2-render-the-verdict-through-a-doctor-verb` |
| herald | 47 | 0 | 0 | 47 | — |
| scribe | 9 | 0 | 0 | 9 | — |
| warden | 31 | 0 | 0 | 31 | — |
| **TOTAL** | **214** | **88** | **6** | **308** | |

All gates green as of this writing: `chain-completeness-check`
(*"every open Spec is decomposed, and epics, ledger and board agree"*),
`dashboard-drift-check`, `dream-chain-check`, `ledger-regression-check`, `check_render.js`.

## Ready to run now (~6 stories)

Real ACs, no blockers, self-contained:

1. **Doctor 5.2** — render the marshal-durability verdict through a verb (XS).
   **Sequence the profile first**: `doctor check` is 7.04s against its documented 5.0s
   budget (`DW-DOCTOR-2026-08-08-1`); adding a gather filter before profiling knowingly
   worsens a live NFR breach.
2. **Atlas Epic 12** — Kedro-org tooling, 3 stories, deliberately audit-and-decide.
   12.2 depends on Steward's shipped `deploy dashboard` (owner ≠ mechanism).
3. **Steward Epic 5** — the Marshal seam, 2 stories.

## NOT ready, and why

- **88 stories is not a night.** Marshal's Epics 7–12 alone are estimated **~54 days**
  in its own epics doc; Mason's 34 are the CFE seam. Scheduling them as an overnight run
  would be the false-green this whole day's work existed to remove.
- **6 blocked, correctly marked.** Steward Epic 8 (all 5 + rollup) on three undecided
  questions in its own Spec — authoritative side, Mode A vs B, Mode B's schema. Marshal
  `8-5-marker-deletion-as-a-sanctioned-opt-out` on its own gate.
- **4 stations are `[unmeasured]` for forward dependencies** — atlas, herald, scribe,
  warden have no structured `**Deps:**` field, so `forward-dependency-check` reports
  *"coverage unknown, not asserted clean"* rather than green. **Herald's is self-inflicted:**
  its epics.md was rebuilt from the ledger on 2026-08-08 without Deps fields.
  **Close this before any large unattended run** — a dependency the loop cannot see is one
  it discovers at minute 90.

## How to measure this correctly

Three findings were filed wrong in one day by measuring with an ad-hoc regex; one shipped
and had to be retracted. The rule:

> **Use `generate.py::parse_sprint_status`, never `^  \d+-\d+`.**

Atlas keys stories `a1-scaffold-…` / `b2-…` alongside `10-1-…` **by design** — its
completion signal is a `story(A1)` commit subject, not a bmad-loop merge. Any parser
assuming `<int>-<int>` silently under-counts that station and manufactures orphans that
do not exist.

Likewise, atlas's board line is **hand-authored on purpose**. `generate.py` preserves it
only while **zero** stories parse from its epics.md; making some parseable flips it to
"rebuild from those" and destroys the rest. That file's own comment says
*"DO NOT fix this by teaching the parser atlas's convention — tried and reverted
2026-07-30."* Atlas stories are added to `data.js` by hand, with a before/after assertion.

## Standing practices (7) — outside the lifecycle

Tended, never finished; **not** backlog and **not** realized (Charter, `docs/dreams/README.md`):
`agent-portability` · `agent-tool-surface` · `agentic-sdlc-autonomy` ·
`enterprise-airgap` · `fleet-stewardship` · `packaging-factory` · `regenerable-factory`.

Archiving one would assert a completion that cannot exist — which is why the 2026-08-08
Dream consolidation absorbed 8 Marshal Dreams but deliberately left 3 practices standing.

## The generalisable lesson

**Completion is measured against a contract that can change underneath it.** Adding FRs to
a shared surface silently invalidates other stations' "done" — and until 2026-08-08
nothing detected that. `chain_completeness_check.py` (INV-A..INV-D) is the answer;
every one of its four invariants was written for a failure that day that needed a
*human* to notice.
