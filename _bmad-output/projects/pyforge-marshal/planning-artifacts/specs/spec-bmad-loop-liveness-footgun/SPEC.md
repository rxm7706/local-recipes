---
spec: bmad-loop-liveness-footgun
status: in-progress
updated: "2026-09-09"
owner-dream: docs/dreams/bmad-loop-liveness-footgun.md
companions:
  - convergence.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
  - docs/dreams/bmad-loop-liveness-footgun.md
sources:
  - ../../../../../../docs/dreams/bmad-loop-liveness-footgun.md
open_questions: []
  # ALL THREE ANSWERED, retired 2026-09-09. OQ-2 (primitive home) and OQ-3 (operator front door)
  # were answered by Epic 24's shipment: the primitive is a `HarnessPort` method
  # (`ports/harness.py:771-782`), implemented at `adapters/harness_bmadloop.py:1657` by shelling
  # to `bmad-loop status <run_id> --json` plus `list --json` -- never importing `bmad_loop` -- and
  # that command IS the documented operator front door.
  # OQ-1 ANSWERED 2026-09-09 (operator, fleet-readiness batch rows mars-A-B4 / C10): the
  # resume-preflight `unknown` verdict policy is WARN-AND-PROCEED, with `unknown` a FIRST-CLASS
  # PRINTED REASON -- not refuse, not operator-confirm. See § The `unknown` policy.
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/bmad-loop-liveness-footgun.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits. `convergence.md`
> (companion) is part of the contract: it names the adjacent machinery already covering parts
> of the Dream, so downstream never re-mints those capabilities.

# Nobody has to hand-parse engine.pid to answer "is this run alive?"

## Why

`bmad-loop 0.9.0` records each run's engine identity as `<run_dir>/engine.pid` — not a bare
pid but `"<pid> <identity>"`, a whitespace-delimited pair whose second token is a
process-start-time float (an intentional, correct pid-reuse guard). The naive check every
operator reaches for by habit — `ps -p $(cat engine.pid)` — is silently malformed by the
float token and always reads "dead". The correct answer already ships as a supported CLI
(`bmad-loop status <run_id> --json`, clean `{"run_id", "status"}`), but nothing in this repo
is pointed at it: the fleet landing-pass protocol prescribes a manual `ps`/`tmux` workaround
(itself blind to two of the engine's three argv forms — a supervisor auto-resumes a dead loop
as `bmad-loop resume <run_id>`, and `bmad-loop resolve <run> --no-interactive --resume` runs
the engine inline, so a `grep 'bmad-loop run'` liveness check misreads both as dead; live
miss 2026-08-14, mason), and Marshal itself has no liveness primitive at all —
`spec-3-7-escalation-deferral-and-resume`'s deferred `[medium]` entry names it verbatim as
the blocker on the `factory resume` double-drive fix: "liveness requires probing
`engine.pid` — no `HarnessPort` counterpart exists." This footgun has been independently
rediscovered twice (`artifact-chain-reconciliation`'s Realization log; the landing-pass
instructions' standing warning). The gap is a binding gap, not a probe gap: build nothing
new, point everything at the surface that already exists. What is already covered by
adjacent shipped machinery — and therefore out of scope here — is cataloged in
`convergence.md`.

## Capabilities

- **CAP-1 — Marshal gains the missing liveness primitive.**
  - **intent:** A Marshal-side primitive answers "is run X's engine alive?" by consuming
    `bmad-loop status <run_id> --json` (the supported, versioned surface) — never by parsing
    `engine.pid`, never by importing `bmad_loop.runs` internals. It preserves the tri-state
    honestly: `alive` / `dead` / `unknown`, with `unknown` reported as `unknown` — not
    coerced to either verdict. This is exactly the "no `HarnessPort` counterpart and no
    Marshal-side primitive" blocker spec-3-7's deferred entry names; this Spec ships the
    primitive, spec-3-7's own deferred fix then consumes it (see Non-goals).
  - **success:** Given a live run, a stopped run, and an absent/unreadable run directory,
    the primitive returns `alive`, `dead`, and `unknown` respectively — with zero reads of
    `engine.pid` and zero `bmad_loop` imports (assertable in its tests); spec-3-7's
    deferred-work entry can be updated to name the primitive as existing.

- **CAP-2 — The operator answer is one command.**
  - **intent:** The operating instructions this repo hands out (the fleet landing-pass
    liveness-verification step and its team/auto-memory carriers) prescribe the supported
    one-command check as the primary answer, replacing hand-parsed `engine.pid` and the
    `ps`-grep workaround. Where a raw process check survives as *corroboration*, it must
    match all three engine argv forms — `bmad-loop (run|resume|resolve)` — so a
    supervisor-resumed or resolve-resumed engine never again reads as dead.
  - **success:** No tracked operator instruction prescribes `cat engine.pid` /
    `ps -p $(cat engine.pid)` or a bare `grep 'bmad-loop run'` as the liveness answer; the
    2026-08-14 mason scenario (engine live under `bmad-loop resume`) answers correctly by
    following the documented steps alone, no source-reading required.

- **CAP-3 — An UNSUPERVISED row has a cheap double-check.**
  - **intent:** For a run Marshal did not spawn (a raw `bmad-loop run`/`resume` with no
    supervisor sidecar — correctly reported `UNSUPERVISED` today), the operator's next
    question, "but is the engine actually alive?", is answered by the CAP-1 primitive /
    CAP-2 command as the documented follow-up — not by raw `ps`/`tmux` archaeology. This
    binds the diagnosis path; it does not alter `derive_home_state`'s row derivation (Story
    5.8's territory — see `convergence.md`).
  - **success:** Reproducing the Dream's 2026-08-15 scenario (raw `bmad-loop run`, no
    sidecar), the documented UNSUPERVISED follow-up resolves engine liveness in one command;
    fleet-status output/docs name that follow-up wherever UNSUPERVISED is explained.

## Constraints

- **HARD:** no in-place edits to the installed `bmad_loop` package — git-pinned pixi
  dependency, wiped on `pixi install`, live-imported by running loops. Everything ships on
  this repo's side of the seam (same posture as every `bmad-loop-*` sibling spec).
- **HARD:** no private-API dependency — the primitive goes through `bmad-loop status
  --json` (or another documented CLI/output contract), never `from bmad_loop.runs import
  engine_liveness`; internals carry no stability guarantee across upstream bumps.
- **Always:** the primitive is on-demand (resume preflight, an explicit operator
  double-check) — never wired as a per-home subprocess probe into `marshal status`'s fleet
  sweep. NFR-14's "no live query per home" discipline stands; CAP-3 documents a follow-up
  command, it does not add a per-row probe.
- **Always:** `unknown` stays `unknown` — the primitive never converts an unprobeable run
  into a confident verdict; what a *caller* does with `unknown` is that caller's recorded
  policy decision (Open Questions).

## Non-goals

- **Not** the `factory resume` double-drive fix itself (spec-3-7's deferred entry) — this
  Spec ships the primitive that unblocks it; consuming it at resume preflight is that
  already-deferred fix's own scope.
- **Not** a change to `engine.pid`'s on-disk format upstream — the two-token identity design
  is correct and intentional; nothing here asks bmad-loop to change, and no upstream filing
  is warranted (unlike the baseline-drift sibling, there is no upstream bug).
- **Not** the fleet-status dead-sidecar fallback — that is
  `spec-fleet-status-supervisor-fallback` (Story 5.8 / FR-181), including landing its
  currently-unlanded implementation branch (see `convergence.md`).
- **Not** hardening Marshal's own pid probes — DW-5-8-1 (`is_run_live` never consults
  `engine_alive`) and DW-5-8-2 (`ProcessPort.is_alive` pid-reuse/pid-0) are separate
  deferred stories; the CAP-1 primitive may later serve them but does not absorb them.
- **Not** a re-plumb of `fleet_picture.py`/`dashboard-gen` liveness detection — today's
  `marshal status --format json` path is empirically correct for supervised runs and never
  touches `engine.pid`.

## Success signal

The three Dream bullets hold: (1) a human debugging a stuck-looking station answers "is it
alive?" with one documented command instead of `cat engine.pid` + manual `ps`/`tmux` — the
landing-pass instructions' standing multi-step warning shrinks to that command; (2)
spec-3-7's deferred double-drive fix is no longer blocked on a missing primitive — its
ledger entry can cite CAP-1's primitive by name; (3) an `UNSUPERVISED` row for a run Marshal
didn't spawn has a documented, one-command engine-liveness follow-up. Demonstrable end to
end by replaying the two live incidents: 2026-08-15 (raw run, UNSUPERVISED diagnosis) and
2026-08-14 (mason, engine alive under `bmad-loop resume`), both resolved by the documented
path with no `engine.pid` read.

## The `unknown` policy (answered 2026-09-09)

`EngineLiveness` is a deliberate tri-state, and `ports/harness.py:781-782` states that `unknown`
is never coerced. **Refusing on `unknown` would coerce it into alive semantics at the operator's
expense**, and every `unknown` cause listed there — an unreadable run dir, an unimportable
`bmad_loop` — is a **probe** failure, not a run failure. It is also the common case, not the
edge: steward is recorded reading `unknown` from a landing journal after every `land-story`, so a
refuse policy would block routine resumes daily.

**Rejected: operator-confirm** — it converts an unattended resume into an attended one on the
fleet's most frequent condition.

Wiring this answer into the resume preflight is what keeps the Spec `in-progress`: OQ-1 was
explicitly out of Epic 24's scope (`spec-24-2:18`, *"resume preflight consumption (spec-3-7
deferred)"*).

## Assumptions

- `bmad-loop status <run_id> --json`'s `{"run_id", "status"}` shape is the stable contract
  at the `>=0.9.0` pin (confirmed live in the Dream, run `20260814-201915-b953`); an
  upstream bump revalidates it.
- Convergence was computed against `main` @ `d7b19b255b` (2026-08-21). Story 5.8's
  `engine_alive` fallback is treated as covered-by-existing-spec even though its
  implementation is dev-complete on an unlanded branch only (verified: `engine_alive` has
  never existed in `main`'s history) — landing it is that story's affair, not new scope
  here.
- Unattended authoring session: express-mode calls above were made without operator
  confirmation and are recorded here and in `.memlog.md` rather than asked.
- `status: in-progress`, not `shipped` (2026-09-09). Epic 24 is 3/3 `done` and CAP-1..CAP-3 are
  in effect — `HarnessPort.engine_liveness` (`ports/harness.py:771-782`) implemented at
  `adapters/harness_bmadloop.py:1657`, consumed live by `cli/dispatch.py:2711-2726`'s liveness
  refusal. The Spec stays `in-progress` until the operator's `unknown` answer is wired into the
  resume preflight.
- `docs/dreams/bmad-loop-liveness-footgun.md` moved `specified` → `realized` on 2026-09-09 with a
  dated Realization-log entry recording Epic 24 in effect and the warn-and-proceed answer.
  Content-only; no capability or surface semantics changed.
