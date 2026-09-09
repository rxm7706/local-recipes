---
spec: bmad-switch-scope-enforcement
status: in-progress
updated: "2026-09-09"
owner-dream: docs/dreams/bmad-switch-scope-enforcement.md
surface:
  - scripts/bmad-switch
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
sources:
  - ../../../../../../docs/dreams/bmad-switch-scope-enforcement.md
open_questions: []
  # OQ-1 ANSWERED 2026-09-09 (operator, fleet-readiness batch rows mars-A-B5 / C10): NO further
  # BMAD write-skill gets the preflight in local-recipes. Wire `verify_scope` at
  # `marshal factory dispatch` instead, and DEFER the skill-injection question to the foundry
  # cutover's 44.5 layout. See § Open question -- closed 2026-09-09.
decisions:
  - "Story 20.6 CAP-1: shared primitive lives at pyforge.marshal.scope (import path; stdlib-only body). never-two-parallel-copies — no Genesis twin in this repo; 20.7 consumers import this module."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/bmad-switch-scope-enforcement.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# The BMAD switch has two divergent guards, and neither checks the slug the caller asked for

## Why

A gap to close, mechanically. Every BMAD write-skill resolves through two gitignored symlinks
(`_bmad-output/planning-artifacts`, `_bmad-output/implementation-artifacts`) that must agree with
the `.active-project` marker AND with the project the caller actually intended. Today two divergent
partial checks guard that triangle: `scripts/bmad-switch --current` warns on marker/symlink
disagreement but advisorily — stderr text at exit 0, called only when someone remembers — and
Marshal's stricter ported copy (`cli/init.py`'s `MRS-INIT-003`, provisioning a loop home) hard-fails
on the same internal disagreement. Both miss the one guarantee that matters: that a write resolves
to the slug the caller ASKED for. A home whose marker and symlinks consistently agree on the WRONG
project — repurposed by an earlier `bmad-switch`, a stale worktree, or a racing concurrent agent —
sails through both checks clean.

This is not hypothetical: the 2026-07-25 fan-out incident (5 concurrent agents running
`bmad-switch`; symlinks observed moving `pyforge-doctor → pyforge-marshal → pyforge-mason →
deckcraft` mid-run; one memlog landed under the wrong project) was caught only because every agent
independently ran `readlink -f`. CLAUDE.md's standing "PARALLEL AGENTS: physical paths, never
bmad-switch" rule is discipline, not enforcement — this SPEC converts it into enforcement. The two
blind spots are already triaged: **DW-1-4-2** (`pyforge-marshal`'s `deferred-work-ledger.md:385`,
from Story 1.4's adversarial review) names them both — (1) `_slug_from_symlink_target` treats any
unrecognized target shape as `None`, letting a real desync evade the check; (2) marker and symlink
are compared only to EACH OTHER, never to the requested slug — and says the fix "needs a product
decision." The owner-dream IS that decision; this contract executes it.

## Capabilities

- **CAP-1**
  - **intent:** One shared verification primitive — `verify_scope(root, expected_slug) -> None |
    ScopeDrift` — checks the whole triangle in a single pass: the `.active-project` marker, both
    symlink targets, and the caller's `expected_slug`. Three file reads, string compares, no
    subprocess. A home internally consistent on the wrong project is a drift, not a pass; an
    unrecognized symlink-target shape (absolute path, foreign tooling) is reported as
    "unrecognized," never silently treated as agreement.
  - **success:** With marker and both symlinks all pointing at slug B, `verify_scope(root, "A")`
    returns a `ScopeDrift` naming found-vs-expected; with a symlink target that matches no
    recognized shape, it returns a drift reporting "unrecognized" — closing DW-1-4-2's blind
    spots (2) and (1) respectively. The all-agree happy path returns `None`.
- **CAP-2**
  - **intent:** BOTH existing guards are replaced by consumption of the primitive —
    `scripts/bmad-switch` (including `--current`) and `cli/init.py`'s `MRS-INIT-003` call the SAME
    logic. Never two parallel copies: the divergent-pair failure mode this work exists to kill is
    not reintroduced as an implementation detail.
  - **success:** Exactly one implementation of the triangle check exists in the repo; both callers
    resolve to it; the retired per-caller check bodies are gone, not shadowed.
- **CAP-3**
  - **intent:** Drift is a hard failure everywhere. `bmad-switch --current` exits non-zero on
    drift — no more advisory stderr at exit 0 — and `marshal init` keeps its hard-fail posture,
    now against the caller's requested slug too. A scripted caller or parallel agent gets a real
    exit-code signal instead of parsing warning text.
  - **success:** On a deliberately desynced tree, `scripts/bmad-switch --current` exits non-zero
    with the drift named; `marshal init` for a home whose marker/symlinks agree on a different
    project than requested refuses instead of silently reconciling it onto the new target.

## Constraints

- **Always:** one shared implementation, not two — `scripts/bmad-switch` and `cli/init.py` must
  call the same logic (the Dream's own hard constraint; parallel copies are how the current two
  checks diverged in the first place).
- **Always:** hard-fail, never a warning that can be ignored — a check that prints to stderr and
  exits 0 documents the gap, it does not close it.
- **Always:** cheap enough to call before every write — three file reads and string compares, no
  subprocess, no network — so wiring it into a write-skill preflight is free, not a tax.
- **Always:** fail-closed on parse — a symlink target the parser does not recognize is reported
  drift ("unrecognized"), never inferred agreement.
- **Always:** operates inside the already-decided ownership boundary — Marshal owns the *source*
  of `scripts/bmad-switch`; Genesis owns its *delivery* as a COPIED·MANAGED artifact
  (`spec-pyforge-marshal/SPEC.md`).

## Non-goals

- **Not** automatic switch-on-workspace-open — that trigger needs a workspace-management
  capability this repo does not have; wiring it would be speculative.
- **Not** a `checkpoint`-style stash/restore of session work — no documented local pain point;
  bmad-loop's `keep_failed` patch preservation covers the adjacent concern.
- **Not** a general `scope.yml` path-boundary enforcer for arbitrary writes — scope is the
  marker/symlink/expected-slug triangle specifically.
- **Not** re-litigating whether Marshal owns `bmad-switch`'s source — already decided.

## Success signal

Today, a working tree whose marker and both symlinks consistently point at the wrong project
passes `bmad-switch --current` (exit 0) and `MRS-INIT-003` (internal agreement only), and gets
silently reconciled onto whatever slug is requested next. After this work: `verify_scope(root,
expected_slug)` flags it as `ScopeDrift`; `bmad-switch --current` exits non-zero naming the drift;
`marshal init` refuses the repurposed home; an unrecognized symlink-target shape reports
"unrecognized" rather than passing; and exactly one implementation backs all of it — at which
point DW-1-4-2 (`deferred-work-ledger.md:385`) can be closed against this spec.

## Open question — closed 2026-09-09

- ~~"Which write boundaries beyond `bmad-switch` and `marshal init` get the preflight wired first
  — the Dream wants it before every BMAD write-skill invocation, but the injection mechanism into
  skills is undecided."~~ **CLOSED (operator):** no further BMAD write-skill gets the preflight in
  `local-recipes`. Story 20.7 shipped exactly two call sites and said so (`spec-20-7:19,:31`).
  The remaining exposure is not skills-in-general — it is the **parallel-agent case** `CLAUDE.md`
  documents as a HARD rule and auto-memory records as a live incident (the 2026-07-25 five-agent
  fan-out). Every parallel BMAD write today enters through `marshal factory dispatch`, which
  already stamps `BMAD_ACTIVE_PROJECT` per invocation (verified in a live journal payload:
  `"bmad_active_project": "pyforge-steward"`), so **one `verify_scope` call there covers the whole
  class** without inventing an injection mechanism — and the two gitignored compatibility symlinks
  this Dream guards may not survive the cutover at all. **Rejected:** wire a `bmad-customize`
  override into every write-skill now — it lives in the regenerated BMAD install layer and would
  have to survive every `bmad-method update`. **Decomposed as marshal Story 33.9**; the
  skill-injection question defers to foundry 44.5.

## Decisions (Story 20.6)

- Shared primitive home: `pyforge.marshal.scope` (import path; stdlib-only). never-two-parallel-copies
  — no Genesis twin in this repo; story 20.7 callers import this module.

## Assumptions

- `status: in-progress`, not `shipped` (2026-09-09). CAP-1/CAP-2 are in effect: Stories 20.6/20.7
  shipped one shared stdlib-only primitive (`pyforge/marshal/scope.py`) consumed by exactly two
  hard-failing call sites — `scripts/bmad-switch:207-210,232-233` and
  `pyforge/marshal/cli/init.py:247` — and `DW-1-4-2` is closed. The third call site the operator
  chose (`verify_scope` at `marshal factory dispatch`) is unbuilt: Story 33.9.
