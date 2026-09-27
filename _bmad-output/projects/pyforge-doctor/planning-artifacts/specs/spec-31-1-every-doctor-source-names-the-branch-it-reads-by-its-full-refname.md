---
title: '31.1: Every Doctor source names the branch it reads by its full refname'
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-61-1-every-local-branch-read-names-the-full-ref.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** git resolves a short name through `refs/<n>`, `refs/tags/<n>`, `refs/heads/<n>`, then `refs/remotes/<n>`. A local branch or tag named `origin/main` therefore stands in for the remote, and a tag named `main` for the local branch. Marshal Stories 60.1 and 61.1 closed this inside marshal's package; 61.1's third review left one reader in Doctor (`DW-marshal-doctor-route3-short-main-2026-09-27`). A sweep of Doctor's git reads found five, two of them `detectors-ci` merge-gate detectors:
- `sources/marshal.py` — the story-status source's route 3 reads the landing history of `main`;
- `sources/ledger.py::gather_direction` (`ledger-direction`) — its `base_ref`, default `main`: the history, the ledger read at the base, and the rekey-map listing and reads at the base;
- `sources/ledger.py::gather` (`ledger-regression`) — its `base`, default `origin/main`: resolved, merge-based, listed and read;
- `sources/frozen_path.py` and `sources/live_proof_surfaces.py` — the diff base, default `origin/main`.

Every caller runs these sources with their defaults. With a stray ref, each judges the wrong history: a regression unseen, a landing missed, a story read as landed that never was.

**Approach:** a new pure module `pyforge/doctor/refs.py` — `local_branch_ref(branch)`, `remote_tracking_ref(branch, remote="origin")`, `MAIN = "refs/heads/main"`, `ORIGIN_MAIN = "refs/remotes/origin/main"`, and `display_ref(ref)` (the short name people read). Doctor imports no station's internals, so this is Doctor's own. The five sites read their refs from it; the source signatures keep their parameters, with full-ref defaults. Findings and evidence people read keep the short names. A meta test flags a bare `main` or `origin/…` reaching a git argument or a base-like parameter default anywhere in the package.

Ledger key: `31-1-every-doctor-source-names-the-branch-it-reads-by-its-full-refname`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-doctor` CAP-85 (FR-18); marshal CAP-270 (60.1), CAP-271 (61.1).

## Acceptance Criteria

- Given a tag named `main` on an older commit than the branch `main` When the story-status source checks a hand-landed story through route 3 Then it reads the branch's history
- Given the same tag When `ledger-direction` runs Then it reads the branch's history and the ledger as committed on the branch
- Given a local branch or tag named `origin/main` on another commit When `ledger-regression`, `frozen-path-changed` and `live-proof-surface` run Then each diffs and reads against the remote-tracking ref
- Given no stray ref When any of the five runs Then every verdict and finding is unchanged, and findings still say `main` / `origin/main`
- Given the package source When scanned Then no git argument and no base-like parameter default is a bare `main` or `origin/…` (a meta test, each spelling in its self-test)

## Boundaries & Constraints

**Always:** one Doctor-local helper; full refs wherever git reads; short names in what people read.

**Ask First:** changing a source's signature or its CLI surface.

**Never:**
- Do not import marshal's (or any station's) internals.
- Do not change a verdict when no stray ref exists.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| no stray ref | ordinary repo | identical verdicts and findings | — |
| tag `main` | older than the branch | route 3 and `ledger-direction` read the branch | — |
| local branch or tag `origin/main` | on another commit | `ledger-regression`, `frozen-path-changed`, `live-proof-surface` read the remote-tracking ref | — |
| no `origin` remote | CI detached checkout | each degrades exactly as before | the existing WARN / inconclusive paths |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor` CAP-85 (FR-18).
Dream: `docs/dreams/pyforge-doctor.md` § Realization log → *2026-09-27 (late) — Proposed: Doctor names the refs it judges by their full refname*.
Deferred-work: closes `DW-marshal-doctor-route3-short-main-2026-09-27` (marshal's ledger).
Ledger key: `31-1-every-doctor-source-names-the-branch-it-reads-by-its-full-refname`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` — expected: pass.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log
