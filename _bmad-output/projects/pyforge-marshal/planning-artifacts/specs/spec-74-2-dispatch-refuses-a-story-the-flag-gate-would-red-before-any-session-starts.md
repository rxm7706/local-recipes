---
title: '74.2: Dispatch refuses a story the flag gate would red, before any session starts'
type: 'feature'
created: '2026-09-28'
status: 'blocked'
blocking_condition: 'blocked until doctor Story 34.2 (spec-feature-flag-governance CAP-2, "The flag gate ships in scripts, outside every station, and runs in detectors-ci") has landed on main -- dispatch consults that gate''s --spec interface, which does not exist before it. The operator flips the ledger key, never a session (marshal''s Deps: parser is station-local); flipping it the day 34.2 lands keeps the Spec''s Q7 (detectors-ci and marshal refuse from the same day).'
flag-exempt: detector-or-gate   # a refusal path is a gate; a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_re_preflight.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-3: a post-rule `type: feature` story spec with neither a `flag:` block
nor a `flag-exempt:` value is refused twice — by `detectors-ci` on its PR (CAP-2, doctor Story 34.2) and by `marshal
factory dispatch` before any session starts. Today the nearest refusal, `MRS-GATE-010` (`core/gate.py::check_spec_binding`),
fires in `dispatch_verify` only after a session has done the work. Under Charter §6 Marshal must not decide the flag
verdict itself: the gate belongs to no station, and Marshal is one of the Smiths it judges.

**Approach:** in `cli/dispatch.py::dispatch_once`'s preflight — beside the `MRS-DISP-041` / `042` / `049` refusals and
before any worktree or harness session exists — run the gate on the story's tracked spec as dispatch already locates it:
`<the running interpreter> scripts/flag_gate_check.py --spec <path>` from the repository root, through
`pyforge.core.process.ProcessPort` (the edge `dispatch_verify` already uses for verify commands). Hand the parsed JSON to
a new pure module, `core/dispatch_flag_gate.py`, which returns the decision:
- `red` → REFUSED `MRS-DISP-052`, naming the spec, the gate's findings and the remedy (a `flag:` block or a `flag-exempt:`
  value; `docs/reference/story-spec-flag-block.md` once doctor 34.1 lands).
- `warn` → one WARN finding naming the pre-rule spec; the dispatch proceeds (Ruling 3: backlog warns until retrofitted).
- `pass` → nothing.
- no `scripts/flag_gate_check.py` in the repository → one WARN naming its absence; the dispatch proceeds (a seeded
  repository that has not adopted the rule).
- exit 2, a timeout, or output that is not the gate's JSON → REFUSED `MRS-DISP-052` naming the gate's failure (AD-8:
  unevaluable is failure; never a silent green).
Register `MRS-DISP-052` in `core/findings.py`, and add it to `core/dispatch_re_preflight.py`'s `_RE_PREFLIGHTABLE_GATES`
so a drain's campaign block clears once the spec's fingerprint changes (the `MRS-DISP-005` shape). The module never reads
a spec's frontmatter: the rules live in the gate alone.

**Blocked until doctor Story 34.2 has landed; the operator flips it.** The `--spec` interface is 34.2's. The ledger key is
minted `blocked` because the `Deps:` parser is station-local (AGENTS.md § Known pitfalls; the doctor 33.1 precedent).

Ledger key: `74-2-dispatch-refuses-a-story-the-flag-gate-would-red-before-any-session-starts`.
Ledger status (do not edit the ledger): `blocked`.
Type / Effort / Deps: feature / S / — (cross-project gate: doctor Story 34.2).

### Living CAP citations

- `spec-feature-flag-governance` CAP-3 (Guild-owned; Marshal's stories per the Spec's table). No marshal CAP or FR (PRD
  § 31.11).
- AD-4 (pure decision, impure edge), AD-5 (the warning journaled), AD-8 (unevaluable is failure), AD-15 (a coded finding).
- Kinship: doctor Story 34.2 (the gate and its `--spec` interface); `MRS-GATE-010` (the spec-binding refusal after the
  work).

## Acceptance Criteria

- Given a fake `ProcessPort` answering `{"verdict": "red", …}` with exit 1 When `dispatch_once` runs Then it returns REFUSED `MRS-DISP-052` naming the spec and the findings, and no worktree is created and no harness launched
- Given `{"verdict": "warn", …}` with exit 0 When `dispatch_once` runs Then one WARN finding is journaled and the dispatch proceeds
- Given `{"verdict": "pass", …}` When `dispatch_once` runs Then no flag finding and the dispatch proceeds as today
- Given no `scripts/flag_gate_check.py` in the repository When `dispatch_once` runs Then one WARN names its absence and the dispatch proceeds
- Given exit 2, a timeout, or non-JSON output When `dispatch_once` runs Then it returns REFUSED `MRS-DISP-052` naming the gate's failure
- Given a drain cycle that met `MRS-DISP-052` When the spec's fingerprint changes Then the next cycle re-preflights the story
- Given `core/dispatch_flag_gate.py` When the unit suite runs Then a test fails if the module reads a spec's frontmatter itself
- Given the consult removed from the preflight When the red fixture runs Then it dispatches and the test fails (mutation)
- Given the code registry When the AD-15 meta-test runs Then `MRS-DISP-052` is registered once
- Given the change When `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci pyforge-deps-test` run Then both pass

## Boundaries & Constraints

**Always:**
- Keep the decision pure in `core/` and the process call at the edge (AD-4); consult the gate, never restate its rules.
- Refuse before any worktree, harness session or campaign launch; a refusal changes zero paths.
- Keep every other preflight refusal and its order unchanged.

**Never:**
- Do not import `scripts/` or any doctor module; the gate is a process.
- Do not add a policy key that turns the consult off: the gate is the Guild's (Charter §6), and CI reds regardless.
- Do not start before doctor Story 34.2 has landed; do not flip this story's ledger key.
- Do not edit `SPEC.md` or `sprint-status-ledger.yaml`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new feature, no block | gate `red`, exit 1 | REFUSED `MRS-DISP-052` | zero changed paths |
| pre-rule backlog | gate `warn`, exit 0 | WARN journaled, proceeds | — |
| flagged or exempt | gate `pass` | proceeds as today | — |
| gate absent | no script | WARN, proceeds | — |
| gate cannot judge | exit 2 | REFUSED naming the failure | — |
| gate hangs | timeout | REFUSED naming the timeout | — |
| drain re-run | spec edited after refusal | re-preflighted | — |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-3 and the Q7 ruling (memlog 23),
decomposed 2026-09-28 (night) as Epic 74's mint.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-3 (Guild-owned; Marshal's story).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `74-2-dispatch-refuses-a-story-the-flag-gate-would-red-before-any-session-starts`.
Ledger status at mint: `blocked` (cross-project gate: doctor Story 34.2).
Policy: `marshal-policy.toml` `[epic_surfaces]` `"74"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- On a scratch branch with a post-rule `type: feature` spec that has neither block nor exemption, `pixi run -e pyforge-guild marshal factory dispatch <project> <story>` — expected: REFUSED `MRS-DISP-052`, no worktree created.
- The same with a `flag-exempt:` value added — expected: the dispatch proceeds past preflight.

## Review Triage Log
