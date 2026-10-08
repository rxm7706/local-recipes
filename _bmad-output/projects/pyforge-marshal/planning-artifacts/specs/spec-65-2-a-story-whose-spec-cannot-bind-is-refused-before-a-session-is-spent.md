---
title: '65.2: A story whose spec cannot bind is refused before a session is spent'
type: 'fix'
created: '2026-09-27'
status: 'ready-for-dev'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A story whose tracked spec cannot bind can never pass the dispatch gate, yet marshal only finds that out after a whole session. The dispatch supervisor evaluates `MRS-GATE-010` (no `## Verification` → `**Commands:**` section) and `MRS-GATE-011` (a declared command outside the station's `verify_commands`) after the session ends. It reads the spec from the PRIMARY checkout (`dispatch_supervisor/__main__.py` → `dispatch_verify.resolve_spec_text_for_story`) and binds it against the guard-appended commands (`dispatch_verify.evaluate_dispatch_verification`). The session writes only its own worktree, so it cannot change that spec: the outcome is certain before launch. The drain then classes both gates TRANSIENT (`core/dispatch_retry.py`), so `station_story_block_facts` records no block and the next cycle re-dispatches the same story: a session per cycle, forever. Steward 44.4 (Deps `done`, spec without `## Verification`) would have entered this loop on 2026-09-27 had it not been parked by a `skip_policies` entry the same day.

**Approach:** `dispatch_once` already reads the tracked spec from the primary checkout and composes the station policy before it resolves a harness or provisions a worktree. Right there, it evaluates the spec-binding predicate Story 65.1 put in `core/dispatch_prelaunch.py` (`spec_binding.parse_success_signal` with `gate.check_spec_binding`, against the same guard-appended verify commands the post-session gate uses, `dispatch_verify._verify_commands_with_surface_guard`). When the predicate yields `MRS-GATE-010` or `MRS-GATE-011`, `dispatch_once` returns a new ERROR `MRS-DISP-050` whose message names the gate code(s) and, for `011`, each missing command. In that case it resolves no harness, adds no worktree, creates no run directory and writes no journal entry. The drain relays it through `_classify_attempt` as a REFUSED campaign block, the same path `MRS-DISP-005` takes. `core/dispatch_re_preflight.py` registers `MRS-DISP-050` as re-preflightable: a changed spec fingerprint or verify-commands fingerprint CLEARS the block, so the next cycle's `dispatch_once` re-checks before launch, which costs no session. An unchanged predicate is rate-limited (`MRS-DRAIN-017`). The post-session gate and its transient classification stay as they are. For a spec that fails to bind at launch they become unreachable; they still cover a spec edited on `main` mid-session.

Ledger key: `65-2-a-story-whose-spec-cannot-bind-is-refused-before-a-session-is-spent`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / S-65.1 (the shared `core/dispatch_prelaunch.py` binding predicate).

### Living CAP citations

- `spec-pyforge-marshal` CAP-274 (FR-220).

## Acceptance Criteria

- Given a backlog story whose tracked spec has no `## Verification` section When `dispatch_once` runs against fakes Then it returns `MRS-DISP-050` (ERROR) whose message names `MRS-GATE-010`; `build_harness.binary_present` and `build_harness.dispatch` are never called, no worktree is added and no run directory is created
- Given a tracked spec whose `**Commands:**` declares a command not among the station's `verify_commands` When `dispatch_once` runs Then it returns `MRS-DISP-050` naming `MRS-GATE-011` and that command, with nothing launched or provisioned
- Given a tracked spec that binds (its declared commands are among the station's `verify_commands`) When `dispatch_once` runs Then no `MRS-DISP-050` is returned and the launch proceeds exactly as before (every existing `test_dispatch.py` expectation unchanged)
- Given a drain cycle whose next story's spec has no `## Verification` When the cycle runs Then the station's result is REFUSED with the `MRS-DISP-050` detail recorded as a campaign block, and no session is launched
- Given that campaign block When the spec gains a `## Verification` section that binds (its fingerprint changes) and the next cycle runs Then re-preflight CLEARS the block and the story is handed to `dispatch_once` again; with the spec unchanged the block is rate-limited (`MRS-DRAIN-017`) and nothing is launched
- Given `MRS-DISP-050` When `test_findings.py` runs Then it is registered at the ERROR tier

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 65.2. Reuse 65.1's binding predicate from `core/dispatch_prelaunch.py` — one evaluator for the plan, the pre-launch refusal and (through `gate.check_spec_binding`) the post-session gate. Bind against the same guard-appended commands the post-session gate uses, and the same primary-checkout spec text `dispatch_once` already read.

**Never:**
- Do not provision, launch, journal or create a run directory for a spec that cannot bind.
- Do not change the post-session gate in `dispatch_verify.py` or the transient classification in `core/dispatch_retry.py`.
- Do not refuse on anything but `MRS-GATE-010`/`011` from the binding predicate (a spec with a `## Verification` section that declares no commands binds, exactly as `check_spec_binding` already rules).
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no Verification | tracked spec lacks `## Verification` | `MRS-DISP-050` naming `MRS-GATE-010`; nothing launched or provisioned | ERROR, refused before launch |
| command outside policy | declared command not in `verify_commands` | `MRS-DISP-050` naming `MRS-GATE-011` and the command | ERROR, refused before launch |
| empty Commands list | `## Verification` present, no command bullets | binds (no finding), launch proceeds | none |
| binding spec | declared ⊆ guard-appended policy commands | launch proceeds unchanged | none |
| drain, unbound spec | next story's spec cannot bind | REFUSED campaign block with the `MRS-DISP-050` detail | never a transient re-dispatch |
| spec fixed | spec fingerprint changes and it now binds | re-preflight clears; next cycle dispatches | none |
| spec unchanged | same fingerprint | rate-limited (`MRS-DRAIN-017`); nothing launched | none |

</intent-contract>

## Source

Contract authored from `docs/dreams/pyforge-marshal.md`'s 2026-09-27 (late night) Realization-log entry ("Proposed: a drain can be asked what it would dispatch before it launches anything") and `spec-pyforge-marshal` CAP-274 with its 2026-09-27 direction entry in the Spec's `.memlog.md`, decomposed the same session as Epic 65's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-274 (FR-220).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (late night) — Proposed: a drain can be asked what it would dispatch before it launches anything*.
Ledger key: `65-2-a-story-whose-spec-cannot-bind-is-refused-before-a-session-is-spent`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
