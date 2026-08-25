# Fleet readiness — 2026-08-08

**SUPERSEDED (2026-08-15) — a dated snapshot, kept as historical record; do not read its
table or its methodology section as current.** Fact-checked against live state:

- **Per-station counts are stale by roughly 2x.** This doc: atlas 38/8/0/46 stories/epics/
  blocked/total, marshal 50/35/1/86, mason 4/34/0/38, steward 18/10/5/33 (6 blocked fleet-
  wide). Live (`pixi run -e local-recipes fleet-picture`, 2026-08-15): atlas 49/6/0/55,
  marshal 98/37/1/136, mason 32/10/0/42, steward 44/10/0/54 (1 blocked fleet-wide — every
  station roughly doubled in scope, and steward's 5 blocked stories are now fully resolved).
- **Its central methodology claim did not hold.** § *How to measure this correctly* asserts
  atlas's `a1-scaffold-…`/`story(A1)` alias convention is permanent-by-design ("DO NOT fix
  this by teaching the parser atlas's convention — tried and reverted 2026-07-30") and that
  atlas's board line must stay hand-authored forever. **The opposite happened, the same
  week**: the alias was normalized in the DATA (not the parser) on 2026-08-08 — 38 headings,
  32 ledger keys, 64 Tier-3 feed keys, 32 story-spec filenames, 32 board ids all moved to
  canonical form in lockstep, verified byte-identical detector output before/after. Full
  account in `EXEMPLAR-STANDARD.md` § INV-5. `epics.md` now reads fully canonical
  `### Story 1.1:`-style headings throughout — checked directly.
- **The "7 standing practices" list is mostly resolved**: of the 7 Dreams this doc frames as
  "tended, never finished," 6 now carry a terminal `status:` (`archived` or `realized`) —
  only `agentic-sdlc-autonomy` (`pitched`) still matches the doc's framing.
- Cited pixi tasks (`chain-completeness-check`, `dashboard-drift-check`, `dream-chain-check`,
  `ledger-regression-check`, `forward-dependency-check`) and `docs/dashboard/check_render.js`
  still exist under those names — the commands below still run, just against current state,
  not the 2026-08-08 numbers quoted in this file's body.

Original document follows, unedited, as a record of the 2026-08-08 readiness gate:

---

Measured state of all 8 stations after the PR #318/#319/#320/#321 sequence, plus what is
actually runnable and what is not. **Derived, not asserted** — every number below came
from `sprint-status-ledger.yaml` via `generate.py::parse_sprint_status`, not from a
regex (see § *How to measure this correctly*, which exists because getting that wrong
produced two retracted findings in one day).

Regenerate with:

```bash
pixi run -e local-recipes chain-completeness-check     # the invariants
pixi run -e local-recipes forward-dependency-check     # can a story actually start
retired-console-check                # the board
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
