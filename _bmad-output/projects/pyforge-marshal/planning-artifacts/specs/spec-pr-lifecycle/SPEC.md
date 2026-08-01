---
spec: pr-lifecycle
status: draft
owner-dream: docs/dreams/pr-lifecycle.md
surface: []          # lands inside spec-pyforge-marshal's existing package surface — see Non-goals
companions: []
sources:
  - ../../../../../../docs/dreams/pr-lifecycle.md
  - ../spec-pyforge-marshal/SPEC.md    # adopted: CAP-9 already ratifies this scope at a compressed grain (resolves its Open Question 10)
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. `docs/dreams/pr-lifecycle.md` is listed in `sources:` for narrative rationale this contract intentionally omits. `spec-pyforge-marshal`'s CAP-9 is the ratified, compressed acknowledgment of this same scope; this Spec is its detailed decomposition, at the grain an epics/stories breakdown needs.

# SPEC — PR lifecycle

## Why

`bmad-loop` drives a story to a merged commit on its station branch and
stops. Everything after — open the PR, know which labels this repo demands,
wait for the right checks, merge, delete the branch, resync — is hand-driven
or improvised from memory each time. A factory unattended until the
interesting part is not unattended. Evidence, 2026-07-31: one session
hand-drove five PRs (#170–174), each repeating create-with-`--repo` + the
`maintenance` label + a conditional `environment.yaml` regen + poll the
linter + squash-merge + delete branch + resync — every step a written rule
enforced by nothing but attention. **#170 merged with a broken detector**: it
changed a file governed by `spec-pyforge-genesis` without moving that Spec's
memlog, and the only check that ran was the inherited linter, so it went
green. Merge strategy is load-bearing and invisible: squash-merging once made
Epic 10's story commits unreachable from `main` and froze a dashboard at
36/38 with a ticking clock on a finished story.

## Capabilities

- **CAP-1 — landing policy surface.**
  - **intent:** Required checks, merge strategy, label rules (including
    repo-specific ones — this fork's `maintenance` label and its **ungated**
    `environment.yaml` sync trigger, which the label does not suppress), and
    branch-delete behaviour are declared once in `EffectivePolicy` with
    per-key provenance, the same treatment gates already got.
  - **success:** a repo states its landing rules as policy; `marshal land`
    executes them with no hand-typed `--repo` flags, no memorized label
    rules, no manually-triggered `environment.yaml` regen.

- **CAP-2 — `marshal land <story>`.**
  - **intent:** One verb performs open-or-update PR, apply labels, wait on
    required checks, merge, retire the branch, resync — idempotent and
    re-entrant, because the interesting failure mode is a half-landed story
    (PR open, checks green, merge never issued).
  - **success:** re-running `marshal land` on a half-landed story converges
    to fully landed rather than erroring or duplicating the PR; the five
    hand-driven 2026-07-31 PRs would have required one `marshal land` call
    each instead of the six-step manual sequence.

- **CAP-3 — refusal semantics, mirroring teardown.**
  - **intent:** Landing refuses exactly as story 1.8's teardown does — no
    merge on a red required check, no merge past an unacknowledged advisory
    finding, no silent force.
  - **success:** an irreversible merge to `main` never proceeds on an
    unproven claim of green.

- **CAP-4 — a verdict and paper trail for the last mile.** *(the audit
  triad applied to landing — [[fidelity-enforcement]] CAP-6: Marshal
  builds, Doctor judges, Scribe records)*
  - **intent:** Every landing leaves a journal verdict recording which
    checks were required, which passed, what merged, and under whose
    authority — closing the one place in the factory's whole claim (every
    stage has a supervisor, a journal, a verdict) that today has none of
    the three.
  - **success:** a landed story's journal entry answers, without
    re-deriving from git history, exactly what gated its merge and who or
    what authorized it.

## Constraints

- **Wrap, never absorb, carried forward unchanged.** `bmad-loop`
  deliberately leaves this gap open — it owns dev/verify/review/commit and
  stops at a station-branch commit. Marshal fills the gap around the
  engine, exactly as it already does for provisioning and teardown.
- **The merge-subject contract (already Marshal's, story 1.2) is consumed,
  not redefined.** Landing must preserve the existing recorded-subject
  contract — the Epic 10 squash-merge incident is the proof of what happens
  when a merge step and the subject contract disagree.
- **Repo-specific landing rules are data in the policy layer, not
  hard-coded assumptions.** The `maintenance` label and the ungated
  `environment.yaml` sync check are true of this fork specifically; CAP-1
  must not bake fork-specific behaviour into code a different repo's policy
  could not override.
- **Required-checks decisions must account for today's CI being advisory,
  not blocking** ([[fidelity-enforcement]] CAP-1). CAP-3's refusal
  semantics apply to Marshal's own required-check evaluation, which must
  not assume an advisory CI green means actually green — that gap is
  exactly what let #170 through.

## Non-goals

- Redefining the merge-subject contract — that stays story 1.2's / owned
  by `spec-pyforge-marshal`, consumed here.
- The engine's dev/verify/review/commit stages — `bmad-loop` keeps them;
  this Spec starts at a merged station-branch commit and ends at `main`.
- Marshal's Epic 4 (landing with a durable paper trail) taken whole — that
  epic is about the *record* a landing leaves; this Spec is about
  *performing* the landing at all. They meet at CAP-4 and must not merge
  scope: a paper trail is worthless if the act it records is still manual.

## Success signal

A session that hand-drove five PRs on 2026-07-31 — each requiring
`--repo`, a manually-added label, a manually-triggered `environment.yaml`
regen, manual linter polling, a manual squash-merge, and manual branch
cleanup — instead issues one `marshal land <story>` per PR, and a repeat of
the #170 scenario (a change breaking a governed Spec's contract) is caught
by the landing path itself, not only the inherited linter.
