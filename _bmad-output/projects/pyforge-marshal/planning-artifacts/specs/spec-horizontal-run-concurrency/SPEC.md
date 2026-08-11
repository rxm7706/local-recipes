---
spec: horizontal-run-concurrency
status: draft
owner-dream: docs/dreams/horizontal-run-concurrency.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-register.json
sources:
  - ../../../../../../docs/dreams/horizontal-run-concurrency.md
open_questions:
  - "What is the right advisory mechanism for CAP-1: a preflight finding (mirrors MRS-PREFLIGHT-* codes), a marshal config warning at render time, or both? Left to the downstream story."
  - "For CAP-3's readiness assessment: a written analysis only, or also a smoke test forcing bmad_loop's own internals past the clamp to observe what breaks? The former is safe and cheap; the latter risks depending on unsupported engine behavior. Left to the downstream story."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/horizontal-run-concurrency.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# One story in flight at a time, silently, by an upstream stub

## Why

A pain to solve, with a mandate-shaped twist. Marshal's rendered policy hard-codes
`scm.max_parallel = 1` (`adapters/harness_bmadloop.py:320`) with no explanation. Direct read of
the vendored `bmad_loop==0.9.0` package confirms this is not a Marshal default but an upstream
stub: `policy.py:448-451` states "Parallel fan-out (Phase 5) is not built yet, so any value > 1
is clamped to 1 in loads()"; `policy.py:815-817,841-842` clamp any requested value to 1
unconditionally, with no diagnostic surfaced to the caller. This gap is unregistered — Story
6.8's `upstream-register.json` tracks 8 other `bmad_loop` gaps (including the adjacent
per-story-model-tiering one) but not this one — and Marshal's own readiness for actual
multi-story dispatch (worktree isolation exists per the ONE current story; the journal,
supervisor, and landing path under true concurrency are unverified either way) has never been
assessed.

## Capabilities

- **CAP-1**
  - **intent:** An operator who requests `scm.max_parallel > 1` is told the request is inert,
    instead of it being silently floored to 1 with no signal.
  - **success:** Setting `max_parallel > 1` in a project's policy produces a registered
    finding/advisory naming the clamp and its cause, visible via the same surfaces (preflight,
    `marshal config`) other policy-shape findings already use.
- **CAP-2**
  - **intent:** The `bmad_loop` parallel-fan-out gap is tracked in the same upstream-contribution
    register Story 6.8 already maintains.
  - **success:** `upstream-register.json` carries an entry for this gap (id, gap description,
    workaround/status) in the same shape as its existing 8 entries, and `marshal upstream`
    surfaces it.
- **CAP-3**
  - **intent:** Marshal's own readiness for N-stories-in-flight — worktree isolation, the shared
    journal, the supervisor's idle/budget ladder, and the landing path — is assessed against what
    true concurrent dispatch would require, and the findings are recorded.
  - **success:** A written readiness assessment exists, naming what already holds (e.g.
    worktree-per-story isolation) and what is unverified or would need to change, so a future
    story adopting an upstream Phase 5 scheduler starts from a scoped list rather than a fresh
    investigation.

## Constraints

- **Always:** treat `max_parallel > 1` as inert given `bmad_loop` 0.9.0's server-side clamp —
  never build or claim actual concurrent dispatch against it.
- **Always:** nothing here touches the vendored `bmad_loop` package (AD-2/AD-3 wrap-never-fork;
  `adapters/harness_bmadloop.py` is the one seam).
- **Always:** keep this distinct from Marshal's existing CROSS-project concurrency (multiple loop
  homes running simultaneously, unaffected and out of scope here).

## Non-goals

- **Not** an attempt to build concurrent story dispatch inside Marshal now.
- **Not** a change to the vendored `bmad_loop` package or a request that it change on any
  timeline.
- **Not** a redesign of `scm.isolation`/`branch_per` or the journal's multi-writer model — both
  are read for the readiness assessment, not modified.

## Success signal

An operator setting `max_parallel > 1` sees a clear, named advisory instead of silent no-op
behavior. `marshal upstream` lists the parallel-fan-out gap alongside the other 8 known
`bmad_loop` gaps. A readiness assessment exists naming what Marshal-side machinery is proven,
unproven, or blocking for true concurrent dispatch — concluding "blocked, revisit when Phase 5
ships upstream" is an acceptable, complete outcome.

## Open Questions

- What is the right advisory mechanism for CAP-1: a preflight finding, a `marshal config`
  warning, or both?
- For CAP-3: a written analysis only, or also a smoke test against `bmad_loop`'s own internals?
  Left to the downstream story.
