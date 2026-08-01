---
spec: fidelity-enforcement
status: in-progress
owner-dream: docs/dreams/fidelity-enforcement.md
surface:
  - .github/workflows/detectors.yml
  - scripts/detectors.py
companions:
  - fidelity-stack.md
  - audit-triad.md
  - migration-and-invariants.md
sources:
  - ../../../../../../docs/dreams/fidelity-enforcement.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. `docs/dreams/fidelity-enforcement.md` is listed in `sources:` for narrative rationale and prose color this contract intentionally omits.

# SPEC — fidelity enforcement

## Why

A contract that nothing can fail against is a plan. `EXEMPLAR-STANDARD.md`
states ten conformance requirements; `dream_chain_check` enforces only
INV-0..3. Rows 7–10 — per-story specs tracked, delivery records, the
deferred-work ledger, the layout README — are written down and enforced by
nothing. Verified fresh at spec time (2026-08-01, not restated from the
Dream's 2026-07-31 numbers): Marshal has 10 done stories against 1 tracked
story-spec — 9 of 10 lack one, worse than the Dream's own cited 6-of-7.
Fleet-wide at Dream-seed time: 125 done stories, 73 tracked specs, gap ~52.
The deeper finding from the Dream's own authoring review: the detectors that
should have caught this were themselves untriggered — no CI workflow and no
git hook invoked any of the eight then-existing scripts, so a red finding
never gated anything. See `fidelity-stack.md` for the full boundary-by-
boundary map of what holds today and what does not.

## Capabilities

- **CAP-1 — detector trigger, advisory.** *(shipped, verified on disk
  2026-08-01)*
  - **intent:** Every repo-scope detector runs on every PR and push to
    `main` via a registry derived from the filesystem, not hand-typed, so
    the registry fails on its own gaps.
  - **success:** `.github/workflows/detectors.yml` invokes
    `scripts/detectors.py --scope repo`; findings post as advisory warning
    annotations. Nine detector scripts confirmed present (see
    `migration-and-invariants.md`).

- **CAP-2 — INV-4: shipped story ⇒ tracked spec.**
  - **intent:** A story marked `done` in a station's sprint-status ledger
    must resolve to a tracked `specs/spec-<key>.md` on `main`; the check
    names the story key and accountable station when it does not. Closes
    row 7.
  - **success:** the detector reports every done-without-tracked-spec gap by
    story key + owner; deleting a tracked story spec at random makes CI name
    it within one run — this Spec's overall success signal.

- **CAP-3 — automatic Tier-2 promotion.**
  - **intent:** `bmad-loop`'s own completion path writes a finished story's
    spec directly to the tracked `planning-artifacts/specs/` location,
    rather than leaving it in gitignored Tier-3 for a human to promote after
    merge.
  - **success:** a story that reaches `done` in the loop has its tracked
    spec on `main` in the same merge, no separate human step required.

- **CAP-4 — reverse gate: Success signal bound to verify command.**
  - **intent:** A promoted story spec's Success criterion binds to the
    verify command that gated its story, so a later change that deletes or
    weakens that test is visible as a contract breach.
  - **success:** removing or defanging a story's verify command trips a
    finding naming the story spec whose Success signal it backed.

- **CAP-5 — Spec↔chain reverse gate.** *(extends `dream_chain_check`;
  `EXEMPLAR-STANDARD` rows 5–6)*
  - **intent:** Every kernel Constraint that compresses an enumeration must
    resolve to a live companion, and every chain artifact (PRD/architecture/
    epics) must name the Spec it decomposes — INV-3 today checks only the
    chain's shape, not that content.
  - **success:** a companion referenced by a kernel Constraint that goes
    missing, or a chain artifact naming no owning Spec, is a named finding.

- **CAP-6 — the actor-attributed event record.** *(Scribe records; Marshal
  and Doctor are emission points — see `audit-triad.md`)*
  - **intent:** Every act an agent or human makes is recorded with five
    fields — who, what, when, how, why — durably, outliving the worktree
    that wrote it.
  - **success:** `journal.jsonl`'s existing event schema gains actor-class
    and authority fields and is promoted out of Tier-3
    (`.gitignore:750`) into a durable, queryable store.

- **CAP-7 — the ungated boundary declares itself.**
  - **intent:** Where a tier boundary genuinely has no gate yet, the
    detector registry reports it as explicitly *ungated* rather than
    passing in silence.
  - **success:** the registry enumerates known-ungated boundaries by name,
    distinct from both pass and fail.

- **CAP-8 — the fixed point, declared per reconciliation.**
  - **intent:** When `bmad-drift-check`'s `surface-changed` reconciler (or
    any code/contract reconciliation) runs, it records which layer was
    treated as owning truth for that change and why.
  - **success:** a drift reconciliation's memlog carries a fixed-point entry
    a later reader can adjudicate against, rather than the decision
    surviving only in a session transcript.

- **CAP-9 — install the judge.** *(the control every other capability here
  depends on for trust)*
  - **intent:** (a) a check fires when a threshold, skip-list, or disable
    flag in a Marshal-owned detector moves without a Doctor-side approval
    marker; (b) structurally, checks that judge Marshal's own conformance
    live in Doctor's package with no Marshal write path.
  - **success:** a Marshal-authored change to a Doctor-judging check's
    threshold/skip-list/disable-flag is blocked or flagged without Doctor
    sign-off. Until (a) or (b) ships, every verdict this Spec produces about
    Marshal is self-graded, and the board says so.

## Constraints

- Marshal may not weaken, re-threshold, or disable a check that judges its
  own conformance rows (Charter ratification, 2026-07-28) — CAP-9 is how
  this becomes enforced rather than prose.
- A detector declares its own scope: `repo` (can run in CI) or `runtime`
  (structurally cannot). A `runtime` detector must never join the
  CI-required set — see `migration-and-invariants.md`.
- A detector that cannot run reports `unknown`, never green.
- CI detectors are advisory, not blocking (amended 2026-07-31). The fleet's
  own `[verify]` gate set carries the binding weight until CI is upgraded.
- No detector may run as a blocking `pre-commit` — every worktree resolves
  to the same `.git/hooks`, and a blocking hook would fire inside unattended
  loop sessions that cannot interpret a failure. `pre-push` is the local
  seam.
- CAP-2 (INV-4) cannot switch on unconditionally — see the migration
  doctrine in `migration-and-invariants.md`, which must land in the same
  change as INV-4, not after.

## Non-goals

- Writing a tenth ad hoc detector before the existing nine are wired and
  trustworthy — CAP-1 (wiring, shipped) was and remains the cheapest,
  highest-ratio item.
- Restoring AI-attribution commit trailers as the provenance mechanism —
  this repo's no-AI-attribution convention stays; CAP-6's structured,
  queryable record is the correct home for provenance.
- Narrowing the Spec's own kernel to be as detailed as the code — the
  Spec-to-code gap is deliberately wide per Charter; this Spec gates that
  gap's intermediate layers, it does not shrink the kernel.
- Adopting the source essay's privileged-layer framework wholesale —
  authorization stays permanently privileged from Tier 0; only origination
  is unprivileged, and the factory already does that half via
  `bmad-drift-check`'s `surface-changed` reconciliation.

## Success signal

Delete a tracked story spec at random, and CI names it — by story key, to
the accountable station — within one run (CAP-2). Then skip a gate, and the
record shows a skip rather than a silence (CAP-6). Two deletions, because
the Dream has two halves: the first proves the declarative gates close, the
second proves the observation plane exists.
