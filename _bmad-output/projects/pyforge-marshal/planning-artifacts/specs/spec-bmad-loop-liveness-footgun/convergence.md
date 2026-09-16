# Convergence — what is already covered, and by what

Companion to `SPEC.md` (spec-bmad-loop-liveness-footgun). Computed against `main` @
`d7b19b255b`, 2026-08-21, per the repo's standing check-convergence-before-new-FR rule.
Downstream reads this to know which capabilities NOT to re-mint and which adjacent deferred
items this Spec deliberately does not absorb.

## Already covered — do not re-mint

| Dream surface | Covered by | Evidence |
|---|---|---|
| Fleet-status rows misreading a dead sidecar over a live engine | `spec-fleet-status-supervisor-fallback` (Story 5.8 / FR-181, epics.md:1439; ledger `done`) | `derive_home_state` gains an `engine_alive` fallback; two failure shapes distinguishable from the report. **Caveat below.** |
| Liveness detection for supervised (Marshal-spawned) runs | `marshal status --format json` (Story 5.1) + `scripts/fleet_picture.py::running_stations` | Keys off the supervisor sidecar's own journaled pid; empirically never touches `engine.pid` (Dream, confirmed by `git grep` — no code in this repo parses `engine.pid`). |
| "Is a live run making progress?" (stall, wedged dialog, gone engine) | `scripts/loop_stall_check.py` (scope=runtime detector) | Decides via `state.json` + log/journal mtime + tmux pane `bmad-loop-<run>`; never `engine.pid`. Reports "engine is gone" for a missing pane. |
| The liveness probe itself | Upstream: `bmad-loop status <run_id> --json` (0.9.0) | Returns clean `{"run_id", "status"}` (Dream, live-confirmed run `20260814-201915-b953`). Internally backed by `runs.py`'s pid-reuse-safe `read_named_pid_identity`/`engine_liveness` — private API this repo must not import. **The residual is binding, not building.** |
| The `factory resume` double-drive *fix* | spec-3-7's own deferred `[medium]` entry (`specs/spec-3-7-escalation-deferral-and-resume.md:153`) | Bounded blast radius (bmad-loop's own refusal prevents the actual double-drive). Blocked on the primitive this Spec's CAP-1 ships; the fix stays spec-3-7's scope. |

### Caveat — Story 5.8 is dev-complete but unlanded

Discovered during this convergence pass: the `engine_alive` implementation exists **only** on
branch `bmad-loop/20260811-190409-5c73/5-8-a-dead-supervisor-sidecar-doesnt-hide-a-live-engine`
(tip `96d8407ad2`, story commit `d9f7691c97`). `git merge-base --is-ancestor` says not merged;
`git grep engine_alive` on `main` is empty and `git log -S engine_alive` shows it never
touched `main`'s history — despite `sprint-status-ledger.yaml` reading `5-8: done` (the known
"loop marks done at DEV completion" trap) and `spec-fleet-status-supervisor-fallback`'s
frontmatter reading `status: shipped`. This Spec still treats that surface as covered — the
capability is owned and contracted there — but landing the branch is Story 5.8's own affair
and a fleet-landing concern, not scope here. Recorded so downstream doesn't mistake "covered"
for "on main".

## Adjacent-not-absorbed — deferred items this Spec touches but does not own

- **DW-5-8-1** — `core/status.py::is_run_live` (gates `marshal land` branch retirement)
  consults `supervisor_alive` only, never `engine_alive`. A dedicated follow-up story;
  CAP-1's primitive is a candidate mechanism for it, nothing more.
- **DW-5-8-2** — `adapters/process_posix.py::ProcessPort.is_alive` has no start-time/identity
  corroboration and admits `pid: 0`. A dedicated hardening story for Marshal's *own* pid
  probes. Note the asymmetry it motivates: bmad-loop's `engine.pid` two-token design already
  solves pid reuse on its side — consuming `bmad-loop status --json` (CAP-1) inherits that
  safety for free, which is one more reason the primitive shells out rather than probing pids.
- **Epic 20** (baseline drift, work preservation, landing-evidence grammar) — same
  bmad-loop-containment family and same no-package-edits posture, zero liveness overlap. The
  memory note tying the resolve-resumed UNSUPERVISED misread to "Epic 20's landing-evidence
  work" concerns landing *classification*, not process liveness.

## The residual this Spec binds (for cross-check)

1. No Marshal-side liveness primitive exists (spec-3-7's named blocker) → CAP-1.
2. The operator protocol still prescribes `engine.pid` hand-parsing / a `grep 'bmad-loop
   run'` that misses the `resume` and `resolve --resume` argv forms (live misses 2026-08-14,
   mason) → CAP-2.
3. An UNSUPERVISED row for a run Marshal didn't spawn has no documented cheap double-check
   (2026-08-15 incident) → CAP-3.
