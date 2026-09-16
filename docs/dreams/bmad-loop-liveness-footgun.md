---
title: Nobody has to hand-parse engine.pid to answer "is this run alive?"
type: dream
owner: marshal
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `bmad-loop-liveness-footgun`).

# Nobody has to hand-parse engine.pid to answer "is this run alive?"

## The Dream

`bmad-loop` records each run's engine liveness identity as `<run_dir>/engine.pid` — and, since
0.9.0, that file is *not* a bare pid: it is `"<pid> <identity>"`, a whitespace-delimited pair where
the second token is a process-start-time float (a pid-reuse guard). This is the *correct*, already
pid-reuse-safe design internally (`runs.py`'s `read_named_pid_identity` / `engine_alive` /
`engine_liveness` / `probe_liveness`, a proper tri-state `alive`/`dead`/`unknown` API) — but nothing
outside `bmad_loop` itself is pointed at that API. The obvious, naive thing to do —
`ps -p $(cat engine.pid)` — silently breaks (the float token makes `ps -p`'s argument list
malformed, which reads as "no such process", i.e. always "dead") and nothing stops an operator, a
script, or a future Marshal feature from reaching for it. The dream is that this repo's own tooling
and its operators never touch `engine.pid` by hand again — there is one obvious, correct, already-
built way to ask "is run X alive", and it's the one everyone actually reaches for.

## What it looks like when real

- A human debugging a stuck-looking station reaches for `bmad-loop status <run_id> --json` (already
  returns a clean `"status"` field — confirmed `"stopped"`/presumably `"running"` this session) —
  not `cat engine.pid` / `ps -p $(cat engine.pid)`. The fleet-landing-pass operating instructions
  this repo already hands out ("verify liveness against real processes... engine.pid holds a float,
  not a pid... will mislead you") shrink from a manual `ps`/`tmux` workaround to "run this one
  command."
- Marshal's own `factory resume` double-drive gap (`spec-3-7-escalation-deferral-and-resume`,
  `deferred-work.md`) stops being blocked on "no `HarnessPort` counterpart and no Marshal-side
  [liveness] primitive" — this Dream's fix *is* that missing primitive, or a thin Marshal-side
  wrapper over it, unblocking that separate, already-deferred correctness fix rather than solving it
  itself.
- `fleet_picture.py` / `dashboard-gen`'s own liveness detection (currently `marshal status
  --format json`, keyed off the supervisor sidecar Marshal itself launches) has a documented,
  correct fallback path for a bmad-loop run Marshal didn't spawn — instead of silently reporting
  `UNSUPERVISED` with no cheaper way for an operator to double-check than raw `ps`/`tmux`.

## What is real

- **The two-token format is intentional, not a bug.** `write_named_pid`'s own docstring: "One
  whitespace-delimited line: `<pid>` (legacy) or `<pid> <identity>`" — the identity token exists so
  a reused pid reads as *not ours* rather than a false-alive. Nothing here is upstream's mistake to
  fix; the gap is entirely that no caller outside `bmad_loop` reuses its own correct liveness read.
- **bmad-loop already ships the fix as a public CLI surface.** `bmad-loop status <run_id> --json`
  returns a clean `{"run_id": ..., "status": "stopped"}` (confirmed live this session, run
  `20260814-201915-b953`) — this is the supported, versioned answer; `runs.py`'s
  `read_named_pid_identity`/`engine_alive`/`engine_liveness`/`probe_liveness` are the *internal*
  functions backing it (not part of any published API contract, so importing them directly would be
  a fragile private-API dependency across upstream version bumps).
- **This exact gotcha is already independently documented twice in this repo**, both discovered the
  hard way: the fleet-landing-pass operating instructions carry it verbatim as a standing warning,
  and `docs/dreams/artifact-chain-reconciliation.md`'s own Realization log notes "liveness verified
  against `ps`, not `engine.pid`" as something a prior session had to work around.
- **pyforge-marshal's own `deferred-work.md` already names the missing primitive as a blocker** for
  a real bug: `spec-3-7-escalation-deferral-and-resume`'s finding that `factory resume` can silently
  double-drive a still-live run, because "resuming would double-drive it; stop it first" (bmad-loop's
  own refusal) only fires *after* a live engine already exists, and Marshal has no cheap way to check
  liveness itself first — "Liveness is not [fixed]: it requires probing `engine.pid`, which has no
  `HarnessPort` counterpart and no Marshal-side primitive."
- **Empirically, today's dashboard/fleet-picture path never touches `engine.pid` at all** — `marshal
  status` keys off the `pyforge.marshal.supervisor` sidecar `marshal factory spin` launches
  alongside the engine, confirmed this session (a raw `bmad-loop run` invocation with no supervisor
  read correctly as `UNSUPERVISED`, not a false `RUNNING`). So the footgun is purely an
  operator-facing hand-diagnosis trap today, not something silently corrupting the dashboard — but
  it's exactly the primitive spec-3-7 already flagged as missing for a real correctness gap.
- **Installed version**: `bmad-loop 0.9.0` (`pixi.toml` pins `>=0.9.0`), source
  `https://github.com/bmad-code-org/bmad-loop`.

## Constraints

- **Cannot be fixed by editing the installed package in place** — same constraint as every other
  `bmad-loop-*` dream in this repo: `bmad_loop` ships via a pixi/conda-forge git-pinned dependency,
  not code this repo owns; a fix here means either shelling out to `bmad-loop status --json` (the
  supported surface) or asking upstream to publish `engine_liveness`/`probe_liveness` as public API,
  never patching `.pixi/envs/*/site-packages/bmad_loop/` directly.
- **Not a private-API dependency.** Whatever this repo builds must go through `bmad-loop status
  --json` (or another documented CLI/output contract), not `from bmad_loop.runs import
  engine_liveness` — an internal function with no stability guarantee across upstream bumps.

## Non-goals

- **Not a fix for Marshal's `factory resume` double-drive bug itself** (`spec-3-7`) — that is a
  separate, already-deferred, larger fix this Dream's primitive unblocks, not something this Dream
  needs to solve.
- **Not a request to change `engine.pid`'s on-disk format upstream.** The two-token identity design
  is correct and intentional; nothing here asks bmad-loop to change it.

## Kinships

[[pyforge-marshal]] (owns `bmad-loop` adoption per `docs/specs/bmad-loop-adoption.md`) ·
[[bmad-loop-baseline-drift]] (sibling bmad-loop-footgun dream, same "cannot edit the installed
package" constraint, same containment-over-upstream-fix framing) · `spec-3-7-escalation-deferral-
and-resume`'s `deferred-work.md` entry (names the missing liveness primitive as a live blocker) ·
`docs/dreams/artifact-chain-reconciliation.md` (independently rediscovered the same footgun)

## Realization log

- **2026-08-15** — Dream captured. Surfaced during a PyForge fleet landing pass: a raw `bmad-loop
  run` invocation (bypassing `marshal factory spin`) was correctly reported `UNSUPERVISED` by
  `marshal status`/`fleet-picture` (no supervisor sidecar was ever started for it — not a detector
  bug), but diagnosing *why* required manual `ps`/`tmux` checks because `engine.pid`'s two-token
  format breaks the naive `ps -p $(cat engine.pid)` check operators reach for by habit. Traced to
  `bmad-loop 0.9.0`'s `runs.py` (`read_named_pid_identity`/`engine_alive`/`engine_liveness`), found
  the correct fix already exists as `bmad-loop status --json`, and found this exact gap already
  named (but unaddressed) in pyforge-marshal's own `deferred-work.md` (spec-3-7).

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`.**
  Epic 24 is 3/3 `done` and in effect: CAP-1 landed as `HarnessPort.engine_liveness`
  (`ports/harness.py:771-782`, tri-state `alive`/`dead`/`unknown`, `unknown` never coerced),
  implemented at `adapters/harness_bmadloop.py:1657` by shelling to `bmad-loop status <run_id>
  --json` + `list --json`, never importing `bmad_loop`; CAP-2 named that command as the documented
  operator answer (team memory `.claude/memory/reference/fleet-landing-pass-liveness.md`); exercised
  live at `cli/dispatch.py:2711-2726`, which refuses a dispatch on the liveness fact.
  **Open question 1 is now answered by the operator:** the resume-preflight `unknown` policy is
  **warn-and-proceed**, with `unknown` a first-class printed reason — refusing would coerce a *probe*
  failure into `alive` semantics and would block routine resumes daily (auto-memory
  `project_steward_unknown_landing_journal`). Spec stays `in-progress` (not `shipped`) because that
  answer is still unwired: Epic 24 explicitly excluded resume-preflight consumption
  (`spec-24-2-…md:18`). Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
