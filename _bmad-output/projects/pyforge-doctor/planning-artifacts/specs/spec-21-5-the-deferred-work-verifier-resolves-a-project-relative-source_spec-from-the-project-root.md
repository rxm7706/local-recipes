---
title: 'The deferred-work verifier resolves a project-relative `source_spec` from the project root'
type: 'fix'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The 2026-09-02 mechanical re-verification pass stamped herald's
`DW-FU-15-1` as *"source_spec path absent at HEAD; no repo paths cited; ledger status
mapped to still-open,"* even though the file is genuinely present. `source_spec` is
recorded **relative to the project**
(`planning-artifacts/specs/spec-15-1-…md`), which resolves at
`_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-15-1-template-parse-then-fill-produces-a-genuinely-editable-deck.md`
— but the verifier resolved it from the repo root instead, so it never found the
file and re-marked a resolvable, real entry as `still-open` **without ever reading
it**. This is a false-stamp class, not an isolated incident: any entry recorded with
a project-relative `source_spec` is vulnerable to it.

**Approach:** Make the resolver try the project root before declaring a path absent.
Every entry using the project-relative `source_spec` form then resolves correctly. An
entry is never re-stamped `still-open` on the strength of a path the verifier merely
failed to find. A regression test pins the exact `DW-FU-15-1` case. The verdict text
distinguishes "spec absent" (genuinely missing) from "spec not located by this
resolver" (a resolver limitation), so the two failure classes stop reading as
identical.

## Boundaries & Constraints

**Always:**
- The resolver tries the project-relative root (the owning project's own directory,
  e.g. `_bmad-output/projects/<slug>/`) before concluding a `source_spec` path is
  absent.
- A regression test built from herald's `DW-FU-15-1` pins this exact behavior.
- The verdict text distinguishes "spec absent" from "spec not located by this
  resolver" — the two are different facts and must read differently.

**Never:**
- An entry is never re-stamped `still-open` on the strength of a path the verifier
  failed to find — a resolver miss is not evidence the spec is absent.
- The resolver does not silently keep resolving only from the repo root; the
  project-root fallback must be exercised, not just declared.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Project-relative `source_spec`, real regression case | herald `DW-FU-15-1`, `source_spec: planning-artifacts/specs/spec-15-1-…md` | Resolves at `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-15-1-template-parse-then-fill-produces-a-genuinely-editable-deck.md`; verdict is not `still-open` on a false "absent" basis | n/a |
| Repo-root-relative `source_spec` (existing working case) | `source_spec` already resolves from repo root today | Continues to resolve exactly as before | n/a |
| Genuinely absent spec file | Neither project-root nor repo-root resolution finds the file | Verdict states "spec absent" | Named, distinct from resolver-miss wording |
| Path present only under project root | Any other entry sharing herald's project-relative recording convention | Resolves correctly via the new project-root-first resolution | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/` — the deferred-work verification/sweep modules that resolve `source_spec`.
- `scripts/` — the sweep's CLI entrypoint, if `source_spec` resolution lives there rather than in the package.
- `src/shared/packages/pyforge-doctor/tests/unit/` — new regression test built from herald's `DW-FU-15-1`.

## Tasks & Acceptance

**Execution:**
- `fix` — update the `source_spec` resolver to try the project root (the owning project's `_bmad-output/projects/<slug>/` directory) before declaring a path absent.
- `fix` — separate the "spec absent" verdict text from "spec not located by this resolver" so the two are distinguishable.
- `feature` — add a regression fixture/test built from herald's `DW-FU-15-1` pinning the correct resolution and verdict.

**Acceptance Criteria:**
- Given the 2026-09-02 mechanical re-verification stamped herald's `DW-FU-15-1` as "source_spec path absent at HEAD" while the file is present at its project-relative path, when the resolver tries the project root before declaring a path absent, then every entry using the project-relative `source_spec` form resolves.
- An entry is never re-stamped `still-open` on the strength of a path the verifier failed to find.
- A regression test over `DW-FU-15-1` pins the behavior.
- The verdict text distinguishes "spec absent" from "spec not located by this resolver."

## Spec Change Log

## Review Triage Log
