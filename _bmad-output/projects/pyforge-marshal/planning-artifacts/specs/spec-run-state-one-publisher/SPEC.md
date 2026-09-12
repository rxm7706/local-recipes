---
id: SPEC-run-state-one-publisher
spec: run-state-one-publisher
status: ready
owner-dream: docs/dreams/run-state-one-publisher.md
companions:
  - brownfield.md
  - stack.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/publisher.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/publisher_host.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/publish.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/**
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
sources:
  - ../../../../../../docs/dreams/run-state-one-publisher.md
open_questions: []
---

> **Canonical contract.** This SPEC, `brownfield.md` and `stack.md` are the complete,
> preservation-validated contract for what to build, test, and validate.
> `docs/dreams/run-state-one-publisher.md` is listed in `sources:` for narrative rationale this
> contract intentionally omits.
>
> **Binds, never re-mints.** The criterion is `spec-pyforge-unifying-strategy` **CAP-17** (steward;
> in-effect Story 49.8). The publisher and its savings fields are `spec-marshal-token-economy`
> **CAP-18** + **CAP-7** (marshal; implementation Story 33.4). The Track it also feeds is
> `spec-intelligence-hub` **hub:CAP-3**. This Spec names only what none of those cover. The four
> questions that gated `ready` were answered 2026-09-12 (operator-accepted research; decisions of
> record in `.memlog.md`, mechanism in `stack.md`).

# Run state is a service — the loop's truth leaves the laptop

## Why

A pain to solve and a mandate to meet. The host's supervisor store has exactly one writer, the
MCP `start` path, so the front door's `/runs/` board cannot see the runs that actually build the
fleet: bmad-loop stories and dispatch waves, whose two marshal supervisors write their truth under
`~/.bmad-loops`. A completed run's timing dies with the workstation, and two stations learn run
state by scraping that home directory. The Unifying Spec's own "Never" clause forbids exactly
this — the supervisor is the only publisher and the front door never reads a filesystem — and
CAP-17 is the last of nine 2026-09-09 realization-gap rows still open. Its two vessels, marshal
33.4 and steward 49.8, block on each other by design and have never been dispatched together.
Every precondition they name is met. What was missing is the act, plus four things neither story
text names: the host cannot hold a run it does not own, the publisher has no credential path and
no legal transport from a laptop, the deployed proof has never been exercised, and more
home-directory readers exist than either story lists.

## Capabilities

- **CAP-1**
  - **intent:** The host holds a run it does not own — the supervisor store accepts, keeps
    alive and finishes a run whose process is external to the platform (a bmad-loop story, a
    dispatch wave) through publish, heartbeat and complete, without wrapping it in a Celery task.
  - **success:** An externally published run stays `running` across its heartbeats and is
    marked lost only when its heartbeat ages past the bound, with reason `heartbeat_lost`, never
    `worker_lost` and never by asking Celery; a terminal row is never rewritten — a later
    heartbeat opens a new attempt row linked by harness run id; a fan-out wave under one operator
    subject is not refused by the per-subject default; the same `/runs/` query lists held runs
    beside MCP runs.
- **CAP-2**
  - **intent:** A published external run is attributable to a verified subject — the
    out-of-host publisher presents, once at publish, an assertion the host minted from the
    operator's verified IdP bearer (signed, audience-bound, short-lived), and holds only a
    subject-bound run handle for the rest of the run's life.
  - **success:** A publish without a verifiable assertion is refused and leaves no row; a
    published loop run carries the operator's `idp_subject` and roles; heartbeat and complete
    succeed by handle alone and the handle cannot create rows, change subject or read results;
    `revoke --sub` cancels the run and its next heartbeat receives a terminal answer; no forwarded
    header, no shared laptop secret and no host private key exists on the workstation.
- **CAP-3**
  - **intent:** The deployed proof is exercised and recorded — CAP-17's success criterion runs
    in a deployed, egress-blocked namespace (a live bmad-loop run on `/runs/` with no operator
    home mounted; a completed run's timing queryable after the workstation is gone) and the
    evidence is written where the realization gate reads it.
  - **success:** The mechanism tier gates in `platform-ci-local --test` (publish, exit, re-query
    with timing intact; a socket guard on the render path; no hostPath volume in any chart
    template); one attended CRC exercise with the default-deny egress policy active is recorded
    as a dated verification file; CAP-17's `verified:` line names both tiers and states the
    Enterprise Managed OCP namespace as not exercised; marshal 33.4 and steward 49.8 close on that
    evidence and the Dream flips to `realized` on it and on nothing else.
- **CAP-4**
  - **intent:** No run-state read from a home directory remains in the fleet — every read of
    the loop home outside the publisher is either moved to the published plane (run state: which
    runs are live, story phase, commit, timing) or classified beside the site as loop-home *file*
    access (install tree, hook relays, worktrees, policy), with a guard that fails when a
    run-state read reappears.
  - **success:** A kind-aware guard over non-test code matches the `.bmad-loops` literal and the
    run-state file names (`.bmad-loop/runs`, `state.json`, `journal.jsonl`), allow-lists only the
    publisher and the tagged loop-home-file sites, never trips on comments or help text, and reds
    a new run-state read; steward's two `upgrade.py` reads carry their loop-home-file tag; doctor's
    story-status read moves once the published payload carries per-story phase and commit, and is
    tagged as CAP-17 debt until then.
- **CAP-5**
  - **intent:** The operator's bearer reaches the publisher by reference, and marshal is a
    station the host will mint for — an operator obtains an IdP bearer for the CLI without
    pasting a secret, it lands in a referenced bearer file, and the marshal station role exists in
    the realm and the dev personas.
  - **success:** `pyforge login` writes the bearer file with owner-only permissions and nothing
    else; a mint for station `marshal` returns 200 for a role-holding operator in both the local
    and the deployed profile, and 403 once the role is removed at the IdP; no token value appears
    in any environment dump or journal line.

## Constraints

- Single writer, one store: `run_state` and `mcp_handles` are written only through
  `django_pyforge.supervisor` (AD-12) — the publisher goes through that API over the host face,
  never raw SQL, never a second table; no station keeps a private copy of the fact.
- The publisher never imports `django_pyforge`: marshal's one publisher module reaches the store
  over `/stations/marshal/mcp` and a meta-test proves it is the only module that publishes. This
  supersedes the in-process reading of Story 33.4 and token-economy CAP-18; the sibling rewording
  is owed verbatim (`stack.md` § Sibling rewording) through their own memlogs before 33.4
  dispatches, and until it lands this Spec's CAP-1/CAP-2 text is the tie-breaker.
- External runs stay external: a bmad-loop run is never wrapped in a Celery task to make it
  publishable. Held rows are a distinct shape in the store (empty Celery task id, judged by
  heartbeat age, per-tool run-bound override).
- Identity is carried, never trusted: the assertion is minted by the host from a verified IdP
  bearer and consumed once; the workstation never holds the host's private key, a shared secret,
  or a machine identity standing in for the operator (RFC-3, CAP-6, CAP-12).
- Secrets by reference on the workstation too: the bearer reaches the publisher through a
  referenced file, never a value in the environment or a journal, and the egress scrubber knows
  its shape.
- The loop home stays: this Spec retires *reads of run state* from `~/.bmad-loops`. bmad-loop's
  worktrees, `state.json` and `journal.jsonl` keep landing there; `BMAD_LOOP_HOME_ROOT` remains
  the override for that purpose.
- The deployed proof is attended CRC, recorded once, documentary: the automated tier gates; the
  CRC record is evidence, not a CI gate; the Enterprise Managed OCP namespace is written as not
  exercised until an access record exists.
- Cross-station by construction: `django-pyforge/**` and the realm are steward's surface,
  `sources/**` is doctor's. A story touching either records an incoming surface claim in that
  station's memlog before code lands, or `spec-surface-check` reds the merge. This Spec's own
  `surface:` claims marshal paths only.
- Realized on effect, never on ledger: two ledger rows reading `done` is not the signal; CAP-3's
  recorded exercise is.
- Vessels stay where they are: marshal 33.4 and steward 49.8 remain the joint-landing stories for
  the publisher and the criterion. This Spec's stories carry only CAP-1..5 and dispatch beside
  them, never instead of them.
- Unattended re-spins are the dated exception (2026-09-12) until CAP-5 lands: a re-spin hours
  after the operator's bearer expired cannot mint, journals that fact, and never falls back to a
  shared secret.

## Non-goals

- Not a second store, ledger, board or dashboard — `/runs/` already reads `RunState`.
- Not the publisher's savings fields or the single-importer proof as token-economy words them:
  those are CAP-18 and CAP-7, delivered by Story 33.4 under the rewording this Spec names.
- Not the Track: `hub:CAP-3` stays on `spec-intelligence-hub`; this publisher feeds it.
- Not attribution signing: unforgeable operator attribution is marshal Story 33.11, dispatched
  behind 33.4 on its own trigger.
- Not moving bmad-loop's own `state.json`, `journal.jsonl` or worktrees off the loop home, and not
  retiring steward's install-tree reads of it.
- Not an automated cluster gate: `ocp-portability-smoke` stays out of the claim until its pull
  secret and Actions minutes exist.

## Success signal

An operator opens `/runs/` in the deployed, egress-blocked namespace and sees a bmad-loop story
running beside an MCP run, then closes the laptop that launched it; the run's completion and
per-story timing appear on the board anyway, and CAP-17's `verified:` line names that exercise.

## Assumptions

- The `/runs/` board needs no change beyond what CAP-18 delivers — it already reads `RunState`
  and already refuses laptop state.
- The heartbeat bound for a held run reuses the station's time limit unless a story finds the
  loop's cadence needs its own bound; the sweep already measures from `heartbeat_at`.
- Steward accepts the CAP-1/CAP-2 host changes under Story 49.8's own Surface line, which already
  names `django-pyforge/**`; the realm and dev-persona change rides CAP-5's story, with steward
  recording the incoming surface claim, rather than a steward story of its own.
- Owner is marshal by the C8 precedent: the surface that changes most — both supervisors and the
  publisher — is marshal's.
- CRC stays reachable to the operator as it was for Story 12.7 (an unsupported but working Ubuntu
  host).
