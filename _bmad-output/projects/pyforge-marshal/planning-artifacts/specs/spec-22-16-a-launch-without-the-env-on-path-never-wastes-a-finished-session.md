---
title: "22.16: A launch without the env on PATH never wastes a finished session"
type: 'fix'
created: '2026-10-07'
status: 'ready-for-dev'
baseline_revision: '966b166f76797916b96286b88587aa6f10f8240d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - scripts/spec_surface_reconcile.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** how a dispatch is launched decides whether its finished session can land. A supervisor whose PATH has no
`python` runs the whole session and then refuses it at verification.

- **Where it happens.** Every dispatch verification runs the derived S-13.7 guard
  `_SURFACE_RECONCILE_COMMAND = "python scripts/spec_surface_reconcile.py"` (`adapters/harness_bmadloop.py`, about
  :447). `dispatch_verify._verify_commands_with_surface_guard` (about :551-:612) folds it in, and `_run_verify_command`
  (about :267-:305) tokenizes it and runs it through the `ProcessPort`. The bare `python` token is resolved from the
  supervisor's PATH. A missing executable is a `ProcessError`, which becomes `MRS-GATE-002`. The station's own
  `verify_commands` and the other derived commands are `pixi run …` lines, so `python` is the only token that depends
  on the activated env.
- **The live case.** On 2026-10-07 three dispatches were launched as
  `.pixi/envs/pyforge-guild/bin/marshal factory dispatch …` (not through `pixi run`). They ran their full sessions and
  were then refused with `verify command 'python scripts/spec_surface_reconcile.py' could not be run: executable not
  found: 'python'` (`MRS-GATE-002`). The runs were `pyforge-herald-20261007T055516715Z-20c28cc4`,
  `pyforge-steward-20261007T055444723Z-4d4c948e` and `pyforge-warden-20261007T055413377Z-abbfa51f`. The same launch
  also lost two context layers (`MRS-DISP-042` caveman, `MRS-DISP-054` codegraph not on PATH). Each session's work
  waited until an operator re-verified by hand and re-dispatched land-only.

**Approach:** the story picks one of two ways to meet the contract below (or both) and records the choice and the
reason in its Auto Run Result:

- **(A) Refuse at launch.** `dispatch_once` already refuses some stories before any worktree or session exists (Story
  74.2's flag-gate consult, about :2584-:2593). After the policy composes, it resolves the executable of every
  command dispatch verification will run (the station's `verify_commands` folded through
  `_verify_commands_with_surface_guard`) on the supervisor's PATH. When one does not resolve, the story is refused
  with one ERROR finding. The finding names the missing executable and the `pixi run -e pyforge-guild marshal …`
  launch form. It uses an existing dispatch preflight code, or the next free `MRS-DISP-` code registered in
  `core/findings.py` and `core/verdict.py`.
- **(B) Use the supervisor's own interpreter.** Wherever the supervisor itself runs the guard, it runs
  `[sys.executable, "scripts/spec_surface_reconcile.py"]`. That covers dispatch verification, the land-only
  merge-tree re-verify (`run_verify_commands_only`) and a fix turn's re-verification. The command string that is
  journaled and bound by `check_spec_binding` stays `_SURFACE_RECONCILE_COMMAND`. Only the executed argv changes, so
  PATH cannot break the guard. The script is stdlib plus this checkout's own doctor `src/` on `sys.path`, so any
  Python 3 interpreter runs it.

Ledger key: `22-16-a-launch-without-the-env-on-path-never-wastes-a-finished-session`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-161 (← `spec-marshal-single-story-dispatch` CAP-3; Story 22.3:
  verification is the product, and the driver itself runs the story's verify commands). The guard became part of
  that verification under CAP-261 (Story 53.1). This is a gap in shipped behaviour, so no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-07 (landing gaps, again), item 2.

## Acceptance Criteria

- Given a supervisor PATH on which `shutil.which("python")` returns `None`, with `pixi` and `git` resolvable (a test
  sets PATH to a temporary directory that holds only `pixi` and `git` shims, or injects a fake resolver or process
  port) When `marshal factory dispatch` runs a story Then the session's work is never refused with `MRS-GATE-002`
  `executable not found: 'python'`. Exactly one of these holds, and the story's tests pin whichever it chose:
  - (A) `dispatch_once` returns before it provisions a worktree. The fake harness port's launch is never called, the
    journal has no `dispatch-launch` record with a `session_pid`, the exit code is non-zero within the frozen domain
    `{0, 1, 2, 3, 4, 130}`, and the envelope carries one ERROR finding whose message contains `'python'` and
    `pixi run -e pyforge-guild marshal`.
  - (B) A recording process port shows that every argv the supervisor executes for the guard (dispatch verification,
    `run_verify_commands_only`, fix-turn re-verification) is `[sys.executable, "scripts/spec_surface_reconcile.py"]`,
    and that no executed argv's first token is the bare string `python`. The guard's report keeps the command string
    `python scripts/spec_surface_reconcile.py`, and its exit code decides `MRS-GATE-001` exactly as today.
- Given a supervisor PATH on which `python` resolves When a story is dispatched Then the launch is not refused, no new
  finding appears, and verification runs the same commands in the same order as today.
- Given the loop adapter When `render_policy_toml` renders a loop home's `policy.toml` Then `verify.commands` ends with
  the plain `python scripts/spec_surface_reconcile.py`, byte-identical to today. The `harness_bmadbuild` session
  prompt names the same plain form.
- Given an unavailable caveman or codegraph instrument When a story is dispatched Then `MRS-DISP-042` and
  `MRS-DISP-054` stay WARNs and the session launches.
- Given the comment block above `_SURFACE_RECONCILE_COMMAND` When the story lands Then it states how the dispatch side
  gets its interpreter (refused at launch, or `sys.executable`) beside why the rendered form stays plain `python`.
- Given the launch check or the interpreter substitution removed (mutation) When the station suite runs Then its new
  test fails.

## Boundaries & Constraints

**Always:**
- Keep the guard derived, never declared: no station's `marshal-policy.toml` gains it, and
  `_verify_commands_with_surface_guard` stays the one place derived commands are folded in.
- Keep the loop render deterministic (AD-12/AD-35): no absolute interpreter path in a rendered `policy.toml`.
- Keep the PATH probe or the `sys.executable` read at the edge (`cli/dispatch.py`, `dispatch_verify.py`), never in
  `core/**` (AD-4, AD-20).
- With (A), the refusal comes before any worktree, session or token spend, and names the remedy so the operator can
  relaunch with no code reading.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped (`spec-pyforge-marshal` and the
  co-governor `spec-pyforge-core`; AGENTS.md pre-PR item 5).

**Never:**
- Never route a verify command through a shell or add `pixi run` around the guard (the deep-worktree pixi path-length
  panic the comment block records still applies).
- Never expose `--write-baseline` from the guard or change `scripts/spec_surface_reconcile.py`'s contract.
- Never turn a context-layer WARN (`MRS-DISP-042`, `MRS-DISP-054`) into a refusal. An unavailable instrument never
  blocks a run.
- Never change the `MRS-GATE-002` meaning for a verify command that genuinely cannot run for another reason.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-07 (landing gaps, again) entry.
- Epic: Epic 22 (a fix joins its own epic, which reopens; doctor Story 41.5).
- Ledger key: `22-16-a-launch-without-the-env-on-path-never-wastes-a-finished-session`.
- Ledger status at mint: `backlog`.
- Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: remove the launch check (A) or the interpreter substitution (B) and re-run the station suite. Its new test fails. Restore it.
- With (A): from a shell whose PATH has no `python`, `.pixi/envs/pyforge-guild/bin/marshal factory dispatch <slug> <key>` refuses before it provisions a worktree and names the `pixi run -e pyforge-guild marshal` form. With (B): the recording-port tests are the proof, and the next dispatch launched that way verifies the guard under the env's own interpreter.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
