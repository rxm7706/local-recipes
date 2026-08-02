---
title: Marshal — autonomy a human can trust
type: dream
owner: marshal
status: realized
---

# Marshal — graduated autonomy on the factory floor

## The Dream

The Commander's dream: **unattended development loops a human can actually
trust.** Not autonomy as a leap of faith — autonomy as a *gradient*: attended
stories first, then unattended loops wrapped in verify gates and quality
gates, with a hard rule that anything the agent cannot safely decide
**escalates to a human** instead of being guessed. Spec in, validated code
out, every run visible. Anti-vibe, by construction.

Execution has one owner. Skills — existing, community, and forged — are the
unit of execution; the deterministic harness is the unit of governance;
station verdicts stay independent. The thing that governs the agent cannot be
a thing the agent authors.

## What is real

`marshal` (module `pyforge.marshal`) is 10/50 stories shipped — Epic 1
(provisioned, verified loop homes) complete; Epics 2-6 in progress. The
capability already exists as `bmad-loop` and has driven two sibling stations
to full completion unattended: `pyforge-atlas` (38/38) and `pyforge-warden`
(31/31). Ten real capabilities are contracted in `spec-pyforge-marshal`
(CAP-1 loop homes and isolation · CAP-2 supervised unattended runs · CAP-3
gates you can run · CAP-4 landing with a durable paper trail · CAP-5 fleet
visibility · CAP-6 portability proven, not claimed · CAP-7 policy composition
· CAP-8 one install yields the whole stack, plus CAP-9/CAP-10 from later
decomposition), decomposed into FR-1 through FR-65 across 6 epics / 50
stories.

The BMAD suite underneath: BMAD 6.10 (BMM 34+ workflows) + BMB/TEA/BMGD/CIS,
web bundles for flat-rate planning, community plugins (skill-forge), and the
multi-project machinery (`scripts/bmad-switch`, per-project config/artifact
isolation). Visibility runs through the GitHub Pages program console
(`docs/dashboard/`), regenerated from tracked ledgers, never hand-trusted.

## Six follow-on dreams, consolidated here (2026-08-02)

This Dream previously sat alongside six satellite dreams, each answering one
question the original scope raised. Five are now fully decomposed into
Marshal's real chain — their standalone dream files are archived, their
vision lives in the FRs named below, not as separate documents to track:

- **Durable runs** (bounded-loss durability) → **FR-61/62/63**. The measured
  cost of not having this: six station loop branches on no remote, ~5,150
  lines across rescue branches, one unpushed commit 40 minutes from a `git gc`.
  Stage-boundary push + fleet-launch wiring, branch retirement, durability as
  a reported fleet-status dimension.
- **Fidelity enforcement** (a gate that fires in both directions at every tier
  boundary) → **FR-64**, the Marshal-owned slice — a gate evaluation binds to
  the tracked spec's Success signal, so a spec that stops being tested does
  not silently keep passing. The Doctor- and Scribe-owned slices of the same
  Dream stay with their own stations, not folded in here.
- **One front door** (`marshal check` — the detector registry through a single
  command, context resolved once) → **FR-65**.
- **PR lifecycle** (open, label, wait for checks, merge, retire the branch,
  resync — done once by the harness instead of improvised each time) →
  **FR-59/60**, `marshal land`.
- **Agent portability** (the method outlives the tool — Devin, Copilot,
  Cursor, Gemini, not just Claude) → **CAP-6 / Epic 6** ("Portability proven,
  not claimed"): skill-tree projection, adapter probe, conformance matrix,
  entry-file drift detection. A standing practice, not a one-time build — its
  narrative now lives here rather than in a separate practice document.

## Kept separate on purpose

**Genesis installer** (`genesis init` / `genesis adopt` — standing up a repo
with the pixi environment, bmad-method, multi-project wiring, and the
BMM/BMB/TEA modules in one command) is real, substantial, Marshal-owned
buildable work — but it is not the `marshal` CLI itself. It keeps its own PRD,
Architecture, and epics (`prds/prd-genesis-installer-2026-07-25/`,
`architecture/architecture-genesis-installer-2026-07-25/`,
`epics-genesis-installer.md`), referenced here, not merged into Marshal's own
FR range. Constitutive records (the Charter, the Guild's membership) and the
machine that installs them are different nouns.

**Factory console** (the GitHub Pages program console at
`docs/dashboard/`, published from `main`, two-source refresh, the Dreamscape
lifecycle board) is shipped and real — the "every run stays visible" doctrine
above, given a front door. Folded in here 2026-08-02 (dream-level only):
`spec-factory-console` (2 companions — `console-contract.md`,
`drill-evidence.md`) stays live and untouched, since real frontier work is
still named against it — per-Dream drill-through to deck/spec/BMAD-project
rows, a delivery/notables feed, and a fleet-health strip fed from
[[pyforge-doctor]]. No PRD exists for it yet; this Spec is the current,
binding reference for that unbuilt work, not this Dream's prose.

## The frontier — real, not yet built

**Fleet-chain completeness** — an orchestrated workflow that regenerates a
project's entire Dream→Spec→Research→Brief→PRD→Architecture→Epics chain from
a consolidated Dream, pausing for human review before committing. Moved here
2026-08-02 from Herald (it is infrastructure/machinery, not Herald's "voice
and visual surface" scope) and consolidated from its own former dream file.
Genuinely unbuilt — the eight-phase workflow it describes is exactly what this
session's own dream-consolidation pass did by hand, station by station. Real
enough to warrant its own Spec — authored 2026-08-02 (`spec-fleet-chain-completeness`,
5 capabilities: orchestrated regeneration, code-status preservation, an audit
mode, review-gated orphan cleanup, per-project configurability) — not yet
decomposed to PRD/Architecture/Epics.

**Fleet-wide test architecture** (`spec-pyforge-testing-charter`, 5
capabilities) — mixed disposition, folded in 2026-08-02 from its own former
dream file. Two capabilities already shipped this session: CAP-1 (the
dashboard's `tea` glob corrected to `src/shared/packages/<slug>/tests/**/test_*.py`,
verified on disk in `docs/dashboard/generate.py`) and CAP-2 (real, generated
`test-architecture.md` for all 8 stations, replacing the six boilerplate
stand-ins a prior bulk commit had fabricated). CAP-5 (test architecture stays
current as stories land) is an ongoing practice, not a one-time build. **CAP-3
(a shared `pyforge-testing-kit` package — verified 2026-08-02, does not yet
exist) and CAP-4 (a CI coverage gate — verified 2026-08-02, no
`--cov-fail-under` in any workflow) are real, unbuilt, and not yet decomposed
to a PRD.** The Spec (and its `station-tea-status.md` companion — the real,
verified per-station test-file counts this Dream's own claims got wrong) stays
live as the reference for that remaining work.

Other open frontier items, unchanged: many-lines-one-floor concurrency (a
floor that survives two writers, not just isolated worktrees); crossing the
boundary between stations as structured, machine-checkable output; a crash an
unattended reader can act on; a run that cannot be torn down while still
alive; a seam for estates this factory cannot see ([[enterprise-airgap]]).

## Realization log

- **2026-07-25** — three loop-policy actions adopted from the pyforge-atlas
  retro: the independent review pass made standing, not self-flagged; a
  deferral repeated in a second wave promoted to contract level; story size
  capped and keystones split at authoring time.
- **2026-07-17/18** — atlas proven: a full system shipped unattended-with-gates.
- **2026-07-23** — Dream retro-seeded; execution doctrine affirmed (one owner,
  skills as the unit of execution, the harness as the unit of governance,
  deliberately not itself a skill).
- **2026-07-23 (later)** — concurrent-loop isolation shipped as
  [[regenerable-factory]] Wave 0.
- **2026-07-24** — `spec-pyforge-marshal` backfilled, binding `.bmad-loop/**`
  into governance.
- **2026-07-31** — five open questions ruled on in one sitting; sequencing
  resolved as *sequence on verdicts, never author them*. Same day, an audit
  found four factual errors written into this Dream's frontier section by a
  prior pass — the lesson recorded then and worth repeating now: a premise
  handed to an agent is not evidence.
- **2026-08-01** — durable-runs, fidelity-enforcement, and one-front-door
  decomposed into FR-61..65 / AD-46..50; PRD now FR-1..65, architecture now
  AD-1..50, epics now 6 epics / 50 stories.
- **2026-08-02** — dream consolidation: agent-portability, durable-runs,
  fidelity-enforcement, one-front-door, and pr-lifecycle archived as absorbed
  (their vision already lives in the FRs above); genesis-installer kept
  separate on purpose; fleet-chain-completeness moved in from Herald as a
  real, unbuilt frontier item. Story 2.1 found missing a resolved
  architecture decision (F-3/AD-26) in its own acceptance criteria — fixed
  the same pass. Marshal's chain re-verified end to end: all 65 FRs trace to
  a story both directions, 50/50 unique story ids, zero dangling dependencies.
- **2026-08-02 (second pass)** — factory-console archived as absorbed
  (dream-level only, `spec-factory-console` stays live for its own unbuilt
  frontier). herald-pitch (Herald's) similarly folded there. pyforge-testing-charter
  archived as absorbed — `spec-pyforge-testing-charter` stays live: 2 of its 5
  capabilities (correct dashboard TEA signal, real per-station test
  architecture) already shipped this session; the shared `pyforge-testing-kit`
  package and a CI coverage gate remain real, unbuilt, undecomposed work.
  fleet-chain-completeness's own dream file (this session's first pass had
  moved it in from Herald and given it a Spec) archived the same way —
  `spec-fleet-chain-completeness` stays live, undecomposed. All four of this
  second pass keep their Specs untouched; only the top-level Dream files
  consolidated.
