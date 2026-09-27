---
title: '31.1: Every Doctor source names the branch it reads by its full refname'
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 1
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

**Problem:** git resolves a short name through `refs/<n>`, `refs/tags/<n>`, `refs/heads/<n>`, then `refs/remotes/<n>`. A local branch or tag named `origin/main` therefore stands in for the remote, and a tag named `main` for the local branch. Marshal Stories 60.1 and 61.1 closed this inside marshal's package; 61.1's third review left one reader in Doctor (`DW-marshal-doctor-route3-short-main-2026-09-27`). A sweep of Doctor's git reads found five, all of them in `detectors-ci` (`ledger-regression` blocks a merge; the rest are advisory):
- `sources/marshal.py` — the story-status source's route 3 reads the landing history of `main`;
- `sources/ledger.py::gather_direction` (`ledger-direction`) — its `base_ref`, default `main`: the history, the ledger read at the base, and the rekey-map listing and reads at the base;
- `sources/ledger.py::gather` (`ledger-regression`) — its `base`, default `origin/main`: resolved, merge-based, listed and read;
- `sources/frozen_path.py` and `sources/live_proof_surfaces.py` — the diff base, default `origin/main`.

Every caller runs these sources with their defaults. With a stray ref, each judges the wrong history: a regression unseen, a landing missed, a story read as landed that never was.

**Approach:** a new pure module `pyforge/doctor/refs.py` — `local_branch_ref(branch)`, `remote_tracking_ref(branch, remote="origin")`, `MAIN = "refs/heads/main"`, `ORIGIN_MAIN = "refs/remotes/origin/main"`, and `display_ref(ref)` (the short name people read). Doctor imports no station's internals, so this is Doctor's own. The five sites read their refs from it; the source signatures keep their parameters, with full-ref defaults. Findings and evidence people read keep the short names; the `ledger-regression` remedy, a command handed to git, names the full ref. A meta test flags a bare `main` or `origin/…` reaching a git argument or a base-like parameter default anywhere in the package.

Ledger key: `31-1-every-doctor-source-names-the-branch-it-reads-by-its-full-refname`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-doctor` CAP-85 (FR-18); marshal:CAP-270 (60.1), marshal:CAP-271 (61.1).

## Acceptance Criteria

- Given the branch `main` renamed away and a tag named `main` left on an older commit When the story-status source checks a hand-landed story Then route 3 reports `main` could not be queried, never the tag's history as the branch's; and in every shape route 3 asks git for `refs/heads/main` (its argv is pinned -- with a tag merely older than the branch, route 4 over `--all` vouches either way, so the verdict alone cannot show it)
- Given the same tag When `ledger-direction` runs Then it reads the branch's history and the ledger as committed on the branch
- Given a local branch or tag named `origin/main` on another commit When `ledger-regression`, `frozen-path-changed` and `live-proof-surface` run Then each diffs and reads against the remote-tracking ref
- Given no stray ref When any of the five runs Then every verdict, message and evidence field is unchanged and findings still say `main` / `origin/main` -- but the `ledger-regression` remedy, a command handed to git, names the full ref (an equivalence test across the PR, push-to-main, no-parent, no-common-ancestor and no-remote shapes)
- Given the package source When scanned Then no git argument, no base-like keyword at a call and no base-like parameter default renders to a bare `main` or `origin/…` -- through assignments, imported constants, f-strings, `+`, `%`, `format`, `or` and conditionals (a meta test, each spelling in its self-test)

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

### Review 1 — 2026-09-27, independent adversarial reviewer, commit `be92d8f4d0` — FAIL (1 medium, 4 low)

Verified clean: every `run_git` / `_git` / subprocess path in the package — the five sites were the only branch reads, no source takes a base from env, policy or feed, and nothing introspects the signatures; with no stray ref the new defaults' findings are byte-identical to the short-name call in a PR-style detached clone, push-to-main, no `origin` remote, default branch `trunk` and a shallow clone; `detectors.yml` checks out with `fetch-depth: 0`, so `refs/remotes/origin/main` exists in CI and the PR shape degrades exactly as before; a tag `main` AHEAD of the branch now correctly reads `done-but-unmerged`; the new tests show trap and fix, and the route-3 test fails on the old short name.

- `[medium]` `[patch]` **`detectors-ci` red on six new cap-citation findings** — marshal's two CAP ids cited unqualified in `epics.md`, this spec and the memlog read as Doctor's own ids. **Fix:** `marshal:CAP-270` / `marshal:CAP-271` throughout (the Dream and CAP-85 too).
- `[low]` `[note]` `spec-surface` red until the landing reconcile (`pyforge/doctor/refs.py` on the co-governor `spec-pyforge-core`; the new tests on `spec-pyforge-doctor`) — done at landing, naming the paths.
- `[low]` `[patch]` **The FAIL remedy handed git the short name** — with a local `origin/main` shadow, `git checkout origin/main -- <ledger>` restored the shadow's blob. **Fix:** the remedy names the full ref; AC-4 amended (the one field that changes without a stray ref), pinned by the equivalence test.
- `[low]` `[patch]` **The meta scan missed the spellings marshal's reviews hardened** (function-local bindings, `or` / conditionals, `+` / `%` / `format`, imported constants, `main^`, `args=`, argv variables, starred args, call-site keywords, `base_branch` / `since` defaults). **Fix:** ported marshal 61.1's rendering and scoping, plus git-argv and call-site keyword collection; a second self-test pins every spelling; the live tree stays clean and the pre-change tree flags all five sites and the calls that consume them.
- `[low]` `[patch]` **AC-1's shape and AC-4's substitution / WARN paths were untested** — AC-1 reworded to what can be observed (the renamed-branch-plus-tag verdict, and route 3's argv pinned to `refs/heads/main`); an equivalence test covers `ledger.gather` in five shapes and `ledger.gather_direction` with both directions firing.
- `[low]` `[→ DW-marshal-testing-kit-short-origin-main-2026-09-27]` `pyforge-testing-kit`'s `branch_diff_guard` (and steward's `tea-test-review` task) default to `origin/main`; outside Doctor's package — the kit's charter is marshal's. Doctor's own `test_portal_fleet_pulse.py` read of `origin/main:<path>` is fixed here.
- `[nit]` `[patch]` Two ledger tests still built `origin/main` as a local branch — now `_origin_main_at`, and `_branch_at` is gone. "Two merge-gate detectors" corrected: all five run in `detectors-ci`, only `ledger-regression` blocks. The spine note and CAP-85 name `display_ref`.
- `[nit]` `[note]` With no `refs/remotes/origin/main` at all, a tag literally named `refs/remotes/origin/main` would still resolve through `refs/tags/` — no worse than before, and marshal shares it; not guarded.
