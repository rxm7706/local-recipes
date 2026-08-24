---
title: "Console parity inventory — what CAP-2 must reproduce before the console is retired"
chain: "pyforge-unifying-strategy"
created: "2026-08-24"
updated: "2026-08-24"
status: "ready"
answers:
  - console-parity-inventory
gates: "FR-7 (removal of the old build path) — this artifact is its precondition"
inputs:
  - "docs/dashboard/generate.py"
  - "docs/dashboard/index.html"
  - "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-factory-console/SPEC.md"
---

# Console parity inventory

Answers the SPEC open question `console-parity-inventory` and satisfies PRD **FR-6**. The supersede
ruling of 2026-08-24 settled *that* Marshal's console is retired; this settles *what has to exist
first*.

**Headline: seven of twenty-three surfaces cannot be reproduced by a request-time query, and one of
them is the console's own delivery model.** That is a real scope conversation, which is what the
constraint anticipated — not a formality to sign off.

## Counts

| Classification | Count | Meaning |
|---|---|---|
| **Runtime-reproducible** | 14 | Data comes from tracked repo artifacts or git history; a live app can query it at request time. Straightforward ETL. |
| **Build-time-only** | 7 | Data is not available at request time from any live source. Each needs a product decision. |
| **Uncertain / mixed** | 3 | Core data is runtime-reproducible; an overlay on it is not. |

Plus one **co-deployed sub-application**: a static Kedro-Viz export of roughly 195 tracked files
under `docs/dashboard/kedro-viz/`, published to the same origin and **not linked from the console
itself**. Nothing in `index.html` references it.

## Architecture, and why it matters here

The console is a single static page. `generate.py` writes `data.js` — a committed
`window.DASHBOARD_DATA` blob — and `index.html` renders it client-side. There is no server and no
API. GitHub Pages serves the tree.

One inherited assumption is worth killing now: **the atlas database does not feed this console.**
`generate.py` sources repo files, git history, local loop homes and subprocess detectors. Any plan
premised on "point the new front door at `cf_atlas.db` and re-render" is wrong.

## The seven that resist

Grouped by what the decision actually is, because three of them are the same decision.

### Three faces of one problem: live run state

**Status chip ("running"), the in-flight card, and the fleet picture's live/projected overlay.**
All three read `~/.bmad-loops`, tmux sessions, or `marshal status --format json` through a local
pixi environment. Those paths are gitignored Tier-3 — a production pod does not have them, which is
why the published board *already* degrades to `unavailable` today while a local `dashboard-gen`
shows them.

**This is one decision, not three:** either the estate grows a loop-supervisor service the front
door can query, or live run state leaves the front door and stays a local-only view. The second is
cheaper and is closer to what the published board already does honestly.

### Sync & Health

Verdicts come from running `bmad-drift-check`, `spec-surface-check` and `llms-full-check` as
subprocesses against a **full factory checkout**, then diffing live ground truth against a
committed baseline fingerprint. A web request cannot do this.

**Cheapest honest equivalent:** a scheduled job runs the detectors and writes the last verdict to a
table; the page reads the cached result and shows its age. What it must not do is imply a
per-request check.

### Curated narrative blocks in the program consoles

The console's own contract splits generated from hand-authored: `generate.py` mutates only story
statuses, dreams, and the snapshot timestamp. Everything else round-trips from the committed
`data.js` — branch names, contract text, segment labels, roadmap prose, epic and story *titles*,
gate notes, and the curated timing/velocity annotations for warden and atlas.

**This is the one that will surprise people.** It is not a data-source problem; it is editorial
content that has no generator at all. It is also, conveniently, exactly what a CMS is for — so this
gap argues *for* the supersession rather than against it, provided the migration is planned as
content authoring and not as ETL.

### Derived timing and velocity

Reads bmad-loop journals under `~/.bmad-loops/<slug>/.bmad-loop/runs/*/journal.jsonl` — gitignored,
local-only. Same shape of decision as live run state: ingest journals into a durable store at loop
completion, or drop the panel from the public front door.

### The committed-snapshot model itself

The published board is a baked blob regenerated on deploy. **Even the fourteen runtime-reproducible
sections are stale until the next regeneration.** This is not a view to port; it is the property the
supersession exists to remove, and it is the strongest single argument for CAP-2.

### Kedro-Viz static export

Produced by `kedro viz build` over the full atlas catalog, requiring the `pyforge-atlas` pixi
environment and a normalization pass, emitting ~195 content-hashed assets. Not servable from a
request-time query under any design.

**But it is not linked from the console**, so it is not a parity obligation — it is a co-published
neighbour on the same origin. FR-7 must therefore be careful: retiring the console's build path
must not silently delete a tree that has its own separate publishing workflow and its own consumer.

## The three uncertain ones

| Surface | Unknown | Resolve by |
|---|---|---|
| Fleet chain audit badge | Needs a `pyforge.doctor` import that fails soft when unavailable | Run the generator in bare CI vs. locally and diff the badge field |
| Sync & Health on production | CI invokes detectors directly rather than through the full pixi environment | Compare the published board's health rows against a local run; document which return `unknown` |
| In Build / Realized membership | Which projects appear depends partly on gitignored Tier-3 feeds | Run both generator sources and diff project line-state |

None blocks the inventory's conclusion. All three are the same underlying fact — the local
generator sees more than CI does — and they should be resolved during CAP-2's build, not before it.

## Consequences for the chain

1. **FR-6 is satisfied by this document.** FR-7's precondition is met and the cutover may be
   scheduled.
2. **FR-7 gains a boundary.** "Remove the old build path" means `generate.py`, its pixi tasks
   (`dashboard-gen`, `dashboard-watch`, `dashboard-check`, `dashboard-drift-check`), its workflow
   trigger, and the committed `data.js`. It does **not** mean the Kedro-Viz tree, which has its own
   workflow and no inbound link from the console.
3. **The scope conversation is narrower than the raw count suggests.** Seven build-time-only
   surfaces reduce to four decisions: live run state (three surfaces, one decision), detector
   verdicts, editorial content, and journal-derived timing. The fifth item — the snapshot model —
   is not a loss to mitigate but the point of the exercise.
4. **Over 100 inbound references to `docs/dashboard` exist across the repo** — dreams, specs,
   presentations, pixi tasks, workflows, tests, scripts, and the Charter's own accountability gate.
   FR-7's "no inbound reference remains" consequence is therefore substantially more work than
   deleting a directory, and the epic pass should size it as its own story rather than as cleanup.
5. **A downstream parser exists.** Tooling reads `data.js` by stripping the
   `window.DASHBOARD_DATA =` prefix. Removing the file breaks those consumers; they need finding
   before, not after.

## Recommendation to the epic pass

Split CAP-2's retirement into three stories, not one: **the inventory** (done — this document),
**the parity build**, and **the removal**. The removal story carries the 100+ reference sweep and
the `spec-factory-console` correction, and it must not start until the parity build proves the
fourteen reproducible surfaces and the four decisions above are recorded as decided.
