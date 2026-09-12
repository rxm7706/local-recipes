---
title: Run state is a service — the loop's truth leaves the laptop
type: dream
owner: marshal
status: specified   # 2026-09-12 — spec-run-state-one-publisher is `ready` (CAP-1..5; the four
                    # questions that gated it answered the same day by operator-accepted research).
                    # Seeded that morning from the one CAP-17 realization-gap row still OPEN after
                    # Epic 49 (steward 49.8 + marshal 33.4, blocked on each other by design); the
                    # criterion stays on the Unifying Spec, the publisher comes home to marshal
---

# Run state is a service — the loop's truth leaves the laptop

## The Dream

Every run the factory makes — a bmad-loop story, a dispatch wave, an MCP `start` — should
be a fact the estate holds, not a file an operator's laptop holds. Today the platform's
`/runs/` board can answer "what is running?" only for MCP starts, because the host's
supervisor store has exactly one writer: `publish_start` on the MCP path. The two marshal
supervisors that watch the runs which actually build the fleet — the loop sidecar and the
dispatch supervisor — write their truth to journals under `~/.bmad-loops`. The front door
cannot see those runs, a completed run's timing dies with the workstation that produced it,
and two stations (marshal's own `status`, doctor's story-status source) learn run state by
scraping that home directory.

The Dream is **one publisher**. Both marshal supervisors feed a single module that publishes
start, heartbeat, completion, per-story timing and the per-layer savings numbers to the
estate's run-state service. Marshal's `status`, doctor's story-status source and the Hub's
Track all read the published plane. The home directory keeps the worktrees and journals that
bmad-loop itself needs; it stops being anyone's *source of run truth*.

> A run that only its laptop knows about is a run the estate cannot govern.

## Why now — measured, not feared

The 2026-09-09 currency review found nine "done but not in effect" capabilities. Eight are
closed. This is the ninth, and on 2026-09-12 every finding behind it is still live:

| Finding | Where it is visible |
|---|---|
| Marshal imports `django_pyforge` **zero** times | `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` → no files |
| The loop home resolves to the operator's home | `pyforge-marshal/src/pyforge/marshal/cli/init.py:336` (`BMAD_LOOP_HOME_ROOT` override, else `Path.home() / ".bmad-loops"`) |
| Doctor scrapes the same home | `pyforge-doctor/src/pyforge/doctor/sources/marshal.py:544`; the registration comment at `sources/__init__.py:223` says "preserve, don't redesign" |
| The only writer of `run_state` is the MCP path | `django-pyforge/src/django_pyforge/supervisor.py:435` `publish_start` — verifies an assertion, mints a handle, enqueues a Celery task |
| The sweep assumes a Celery task | `supervisor.py:681` `sweep_lost_runs` marks a live row `worker_lost` when no worker reports its task id — an external process would be swept as dead |
| The front door already forbids scraping | `src/platform/tests/test_front_door_queries_supervisor.py:235` asserts no laptop state is read |
| Four more home-dir readers sit outside both stories | steward `cli.py` and `upgrade.py`, scribe `promote.py`, doctor `sources/__init__.py` (story-status) |
| The two stories block each other by design | steward `49-8` and marshal `33-4` both `blocked` in the tracked ledgers; 33.4 says "joint landing with 49.8", 49.8 says "until marshal's Track story exists" — it exists, nobody has dispatched the pair |
| The contract's own verdict | Unifying `SPEC.md` CAP-17 `verified:` — "marshal loop homes still filesystem-backed; deployed egress-blocked proof unexercised" |

Every precondition the two stories name is already met: steward 49.1 (the verified column)
is done, marshal 33.1 (the benchmark with real savings getters) is done and the five savings
fields exist at `adapters/harness_bmadloop.py:743-768`, and doctor recorded the incoming
surface claim for `marshal.py:544` in its memlog on 2026-09-09. What is missing is not a
dependency. It is the act.

## What it looks like when real

- **The board shows the loop.** The front door's `/runs/` board lists a live bmad-loop story
  beside the MCP runs, in a deployed, egress-blocked namespace with no operator home mounted.
- **Timing outlives the workstation.** A completed run's per-story duration is queryable
  after the laptop that ran it is gone — the same query that already works for MCP runs.
- **One writer, provably.** `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/`
  returns exactly one module, and both supervisors call it. A second importer fails a test.
- **Savings are numbers.** The per-layer savings fields on a published run carry the values
  Story 33.1 measures, not stubs.
- **The readers moved.** `marshal status`, `cli/init.py`'s home resolution and doctor's
  `marshal.py:544` read the published plane. The `~/.bmad-loops` literal remains only where
  bmad-loop's own worktrees and journals live, never in a run-state read.
- **The host sweeps by heartbeat.** An externally-published run is judged live by its
  heartbeat, not by asking Celery whether a task id exists.
- **The verified line is rewritten by evidence.** CAP-17's `verified:` names the deployed
  exercise — a live loop run on the board, in the namespace, with the home unmounted — and
  Epic 49's last open row closes on effect, not on a ledger flip.

## Constraints / Non-goals

- **No second ledger.** The supervisor store in `django_pyforge` is the run-state service;
  nothing publishes anywhere else and no station keeps a private copy of the fact.
- **Identity is carried, never trusted.** The publisher presents an assertion the host
  verifies (CAP-6's shape), or a dated, recorded exception — a forwarded header or a shared
  laptop secret is not an identity.
- **The loop home stays.** This Dream retires *reads of run state* from `~/.bmad-loops`. It
  does not delete the directory, move bmad-loop's worktrees, or change where journals land.
- **External runs stay external.** A bmad-loop run is not wrapped in a Celery task to make it
  publishable; the host learns to hold a run whose process it does not own.
- **Mints nothing already minted.** Unifying CAP-17 owns the criterion and token-economy
  CAP-18 owns the publisher; the Spec derived from this Dream binds to both and names only
  what neither covers — the host-side non-Celery publish and sweep path, the deployed proof,
  and the four residual home-dir readers.
- **Cross-station by construction.** The host-side path is steward's surface
  (`django-pyforge/**`), doctor's read is doctor's — each station records the incoming
  surface claim in its own memlog before code lands, or `spec-surface-check` reds the merge.
- **Realized on effect.** The Dream flips to `realized` when the board shows a loop run in
  the deployed namespace, never when the two ledger rows read `done`.

## Kinships

[[pyforge-unifying-strategy]] (CAP-17 — the criterion's home; steward Story 49.8 is its
in-effect story) · [[marshal-token-economy]] (CAP-18 one publisher + CAP-7 savings telemetry;
marshal Story 33.4 is the implementation story) · [[intelligence-hub]] (`hub:CAP-3`, the Track
this publisher also feeds) · [[capability-effect-check]] (the sibling relay from the same
2026-09-09 batch, and the check that will report this capability until it is reached) ·
[[durable-runs]] (the ancestor: work survives the machine that made it — this is its
run-state half) · [[fleet-status-supervisor-fallback]] (`derive_home_state` — the reader whose
truth moves off the disk) · [[pyforge-marshal]] (the station; both supervisors) ·
[[pyforge-doctor]] (`sources/marshal.py:544`) · [[pyforge-steward]] (the host's supervisor
store and the deployed proof).

## Realization log

- **2026-09-12** — Seeded (operator ruling: every effort enters through the Dream-to-Code
  chain, gap-closure included — no story drafting or dispatch before a Dream and its Spec).
  Captured after a live re-verification of the 2026-09-11 infographic's § 18 row "CAP-17 run
  state — OPEN · 33.4 + 49.8 blocked": the tracked ledgers still read `blocked`, marshal still
  imports `django_pyforge` zero times, `cli/init.py:336` and doctor's `marshal.py:544` still
  resolve the home directory, and `publish_start` is still the only writer of `run_state`. Two
  design facts found in that pass that neither story text names: the host sweep
  (`sweep_lost_runs`) would mark an externally-published run dead for lacking a Celery task,
  and four more `~/.bmad-loops` readers (steward, scribe, doctor story-status) sit outside
  both stories' Surface lines. Owner **marshal** by the C8 precedent (the surface that changes
  most — both supervisors and the publisher — is marshal's); the criterion stays on the
  Unifying Spec. Next act: `bmad-spec` derives the Spec under `pyforge-marshal`.
- **2026-09-12** — Spec derived: `spec-run-state-one-publisher` under `pyforge-marshal`
  (`bmad-spec` headless, express; `status: draft`). Binds Unifying CAP-17 and token-economy
  CAP-18/CAP-7 by kinship and mints only CAP-1..4 (the host holds a run it does not own; a
  published external run is attributable; the deployed proof is exercised and recorded; no
  run-state read from a home directory remains). Four open questions gate `ready`: the
  publisher's credential path, in-process versus host-face publishing, the proof lane, and the
  classification of steward's two `upgrade.py` reads. `dream-chain-check` and
  `dreams-hygiene-check` clean for this pair. Dream stays `dreamt` until the Spec is `ready`.
- **2026-09-12** — Specified. The four open questions were researched in parallel against the
  pyforge code, PRD, architecture and Specs, spot-checked, and accepted by the operator: (1) the
  operator's IdP bearer is exchanged once at the host for a delegated assertion, the sidecar then
  holds only a subject-bound run handle; (2) the publisher reaches the store over the host's
  `/stations/marshal/mcp` face — never an in-process `django_pyforge` import, which inverts Story
  33.4's and token-economy CAP-18's literal wording (rewording owed through their memlogs); (3)
  the proof is two-tier, `platform-ci-local --test` gating the mechanism and one attended CRC
  exercise recording the criterion, the OCP namespace written as not exercised; (4) steward's two
  `upgrade.py` reads are loop-home file reads and stay tagged, doctor's story-status read is run
  state and moves once the payload carries per-story phase and commit. Two gaps neither story
  named became CAP-5: no CLI login exists anywhere and the realm has no marshal station role.
  Spec `ready`, `open_questions: []`; Dream `dreamt → specified` per README § status.
