---
title: A dispatch branch names its station
type: bug
created: '2026-08-27'
status: done
updated: '2026-08-27'
baseline_revision: 8519bd3a835fad95a455b4b9e7eb198910693bb0
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode.md
warnings: []
deferred:
  - summary: >-
      A legacy branch that exists only on origin (pushed, local ref and worktree gone) is
      invisible to the refusal, so a re-dispatch mints the new name and the remote work is
      orphaned with no signal.
    evidence: |-
      resolve_dispatch_branch asks VcsPort.branch_exists, and GitVcs.branch_exists verifies
      refs/heads/<branch> only -- a remote-tracking ref under refs/remotes/origin/ never
      matches. Live: origin carries refs/heads/marshal/12.2 (05538789c674). Pre-existing in
      shape rather than caused by Story 22.9: before the change the same state re-created a
      fresh marshal/<key> from main with the same orphaning, so this story neither
      introduced nor widened it.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
    severity: medium
  - summary: >-
      Two concurrent dispatches of the SAME station and story key still share one branch and
      one worktree; station-scoping only makes CROSS-station collision impossible.
    evidence: |-
      resolve_dispatch_branch returns early on branch_exists(branch) without checking that
      the station-scoped branch is checked out at THIS run's worktree, so attribution is
      asymmetric -- legacy names must prove attribution, station-scoped names are trusted on
      mere existence. This is the failure already on record as the 2026-08-27 atlas 20.1
      duplicate dispatch (two identical runs in one worktree), which is same-station and
      therefore untouched by this story's fix.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py
    severity: medium
  - summary: >-
      Branch resolution now costs 1-2 extra git subprocesses on a hot path -- every
      supervisor tick, and once per historical run dir on every dispatch.
    evidence: |-
      gather_dispatch_git_facts was a pure derivation before Story 22.9 and now calls
      resolve_dispatch_branch, which shells branch_exists / worktree_path_for_branch. The
      supervisor calls it every _TICK_SECONDS for the life of a run and the CAP-5 in-flight
      guard reaches it per run dir. The answer is stable for a run, so it could be resolved
      once at attach time and threaded.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py:212
    severity: low
  - summary: >-
      No integration-tier test creates the three-segment ref dispatch/<slug>/<key> with real
      git; every 22.9 test uses hand-written FakeVcs doubles.
    evidence: |-
      The package has an established real-git tier for exactly this kind of provisioning
      work (tests/integration/test_init_worktree.py, real GitVcs, @pytest.mark.slow) and
      Story 22.9 added nothing there, so the new ref shape's interaction with git worktree
      add / merge-base is asserted only against fakes.
    location: >-
      src/shared/packages/pyforge-marshal/tests/integration/test_init_worktree.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** `core/dispatch.py::dispatch_worktree_branch(story_key)` renders
`marshal/<story_key>` with no station slug — mason 12.1 landed on `marshal/12.1`. Worse
than naming: `cli/dispatch.py::_ensure_dispatch_worktree` resolves an existing worktree BY
BRANCH NAME, so two stations sharing a story key silently reuse each other's worktree. At
Story 22.7 fleet-drain scale (eight stations dispatching concurrently) a cross-station key
collision is inevitable.

**Approach:** derive station-scoped branch names (`dispatch/<slug>/<key>`) from one
function every consumer shares; resolve or explicitly refuse legacy `marshal/<key>`
branches; never a second derivation site.

## Acceptance Criteria

- Given a dispatch for station `<slug>` story `<key>`, when the worktree branch is derived, then it carries the station (`dispatch/<slug>/<key>`) and no two stations can collide on a shared story key.
- Given an in-flight or preserved branch under the legacy `marshal/<key>` name, when dispatch or landing resolves it, then it is still found (or the refusal names the legacy branch and the land-first remedy) — never silent reuse of another station's tree.
- Given the branch-name consumers (worktree lookup, in-flight conflict guard, landing classification, status overlay), when any derives the name, then all agree on the one derivation function — verified by a test that fails on a second derivation site.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger key `22-9-a-dispatch-branch-names-its-station`. One derivation function; consumers import it.

**Block If:** Story 22.7 has not landed (its in-flight session edits `cli/dispatch.py`; implementing first manufactures a merge conflict). A change would strand the three preserved legacy branches (`marshal/20.1`, `marshal/12.1`, `marshal/22.7`, pushed to origin 2026-08-27) without a documented resolution path.

**Never:** A second branch-name derivation site. Deleting or force-moving a preserved legacy branch. Touching the conda-forge-expert surface.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New dispatch | `pyforge-atlas`, `20-2` | branch `dispatch/pyforge-atlas/20.2`; worktree resolved by that name | — |
| Cross-station same key | `pyforge-atlas 20-1` while `pyforge-doctor 20-1` exists | two distinct branches/worktrees; zero reuse | collision impossible by construction |
| Legacy branch present | `marshal/12.1` exists with WIP | resolved for its original station, or loud refusal naming land-first | never silent cross-station reuse |
| Landing | verified story on new-name branch | Epic 4 landing + marshal-native classification unchanged | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py:160` — `dispatch_worktree_branch(story_key)` gains the slug parameter; the ONE derivation site.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:~156` — `_ensure_dispatch_worktree` passes the slug; `worktree_path_for_branch` lookup keeps legacy-name fallback for the three preserved branches.
- Grep for every other `dispatch_worktree_branch` / literal `marshal/` branch-string consumer (landing, status overlay `core/status.py`, conflict guard) and route through the one function.
- Tests: `tests/unit/test_dispatch.py` — collision case (two stations, same key), legacy-fallback case, single-derivation-site guard.

## Implementation record — 2026-08-27

**Shape as built.** `core/dispatch.py` owns two derivations and one resolver:
`dispatch_worktree_branch(slug, story_key)` → `dispatch/<slug>/<key>` (slug is a required
positional, so an unmigrated consumer raises `TypeError` rather than rendering a
station-less name), `legacy_dispatch_worktree_branch(story_key)` → `marshal/<key>` (read,
never minted), and `resolve_dispatch_branch(vcs, repo_root, slug=…, story_key=…,
worktree=…)` — the single site where the legacy name is reconciled. Attribution of a legacy
branch is a git fact, not a guess: it is this station's only when git has it checked out AT
this station's dispatch worktree. Every branch-name consumer routes through the resolver —
`cli/dispatch.py::_ensure_dispatch_worktree`, `dispatch_supervisor::gather_dispatch_git_facts`
(which is also what the CAP-2 zombie refusal and the CAP-5 in-flight guard read), and
`dispatch_land::execute_dispatch_land`. `core/status.py`'s dispatch overlay derives no
branch name, so it needed no change.

**New finding codes:** `MRS-DISP-030` (ERROR) — an unattributable legacy branch refuses the
dispatch/landing, naming the branch and the land-first remedy; `MRS-DISP-031` (WARN) — this
run IS on an attributable legacy branch and proceeds from it, so the migration is visible
rather than silent.

**Cross-package: the landing grammar had to learn the new name.**
`pyforge.core.landing_evidence`'s `parse_github_pr_merge_subject` / `parse_station_branch_name`
gated on `branch.startswith(f"{station}/")`, which `dispatch/pyforge-marshal/22.9` fails — so
without this, `merged_story_keys` → `story_merged_on_main` would stop recognizing marshal's own
dispatch landings, breaking the supervisor's re-landing guard and the CAP-2 zombie check. Both
parsers now accept `dispatch/<project_slug>/<key>` too, via one shared
`_branch_belongs_to_project` predicate, keeping the existing `STATION_BRANCH_NAME` /
`GITHUB_PR_MERGE_SUBJECT` shapes rather than minting a second enum member. The FULL slug in the
branch is what makes it project-scoped: `dispatch/pyforge-mason/22.9` never classifies for
`pyforge-marshal`. The literal `"dispatch"` lives ONCE, as
`pyforge.core.landing_evidence.DISPATCH_BRANCH_PREFIX`, which marshal's `core/dispatch.py`
imports — marshal mints these branches, pyforge-core recognizes them, and neither re-spells the
prefix.

**Never ask git about a branch the resolver did not resolve.** `effective_branch` falls back to
the station-scoped name, which by construction does NOT exist whenever `resolved is None`;
`is_branch_merged` shells `git merge-base --is-ancestor`, which exits 128 on a missing ref, and
the supervisor loop swallows the resulting `VcsCommandError` and `continue`s inside `while
True` — a run that spins forever, never judged complete, never landed. `gather_dispatch_git_facts`
now keeps the whole resolution and reports `branch_merged=False` without asking, which is the
factually correct answer for a branch that does not exist (and also closes the same latent raise
for a branch retired after landing).

**One sanitization rule for both derivations.** `_safe_ref_segment` is the single rule the branch
name and the worktree path both apply to their segments — they must agree because attribution
compares a branch-derived expectation against a path-derived location. It collapses dot runs and
strips edge dots/dashes (`git check-ref-format` rejects `..` anywhere and a component that starts
or ends with `.`), so no slug or key can traverse or split the ref into extra components.
`22.9` / `20.2` / `12.1` render unchanged.

**Verification** (after the review-pass patches):
`pixi run -e pyforge-marshal pyforge-marshal-test` → **6508 passed / 1 failed**, the failure
being the pre-existing `test_skf_domain_skill::test_context_files_not_hand_edited` red that
predates this story (it asserts on `CLAUDE.md`/`AGENTS.md`, untouched here) and was already
recorded on Story 22.7. `pixi run -e pyforge-core pyforge-core-test` → **1573 passed / 13
failed**, byte-identical to the same 13 failures measured on the baseline tree
(`8519bd3a83`, 1565 passed) — all subprocess/atomic-write/exception-root sole-ownership meta
tests across seven packages, none touched here. `lint-imports` → **5 contracts kept, 0
broken** (AD-4 core purity holds: `resolve_dispatch_branch` takes a `VcsPort` and the shared
prefix comes from `pyforge.core`, neither of which is a forbidden module; the `..` collapse
in `_safe_ref_segment` is done by hand precisely because AD-4 forbids `os` in
`pyforge.marshal.core`). The single-derivation-site guard was verified to genuinely fire by
temporarily planting a second site. Live read-only run of `resolve_dispatch_branch` against
the real repo: the three in-flight legacy runs (`marshal/22.9`, `marshal/12.2`,
`marshal/20.2`) all resolve to their legacy branch, and a different station on a live key
(`pyforge-doctor 12.2`) is refused naming `.worktrees/dispatch-pyforge-mason-12.2` — the exact
silent-reuse defect, now loud. Live end-to-end classification check through
`promotion.merged_story_keys`: a `dispatch/pyforge-marshal/22.9` PR-merge subject classifies
for marshal and not for mason, `dispatch/pyforge-mason/12.2` the reverse, and the legacy
`marshal/22.7` subject still classifies.

**Correction to the Block If premise.** The three named preserved branches are not where the
spec says: `marshal/20.1`, `marshal/12.1` and `marshal/22.7` are absent from `origin`
(verified by `git ls-remote --heads origin`) and absent
from `refs/heads/` here; `marshal/20.1` and `marshal/22.7` survive only as stale
remote-tracking refs into the station loop homes, their stories having landed via PRs #886
and #887, and `marshal/12.1` does not exist in any form. The legacy branches that DO exist
are the three in-flight dispatch-worktree branches above, and all three resolve — nothing is
stranded, and the `MRS-DISP-030` refusal is the documented resolution path for any that
reappear. A narrower over-generalization in this paragraph's first draft ("origin carries no
dotted `<prefix>/<n>.<n>` head at all") was itself false and has been corrected: origin does
carry `refs/heads/marshal/12.2` (`05538789c674`). The three branches the Block If NAMES are
genuinely absent, which is what the premise turned on.

## Review Triage Log

### 2026-08-27 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 2, medium 1, low 5)
- defer: 4: (high 0, medium 2, low 2)
- reject: 8: (high 0, medium 2, low 6)
- addressed_findings:
  - `[high]` `[patch]` `pyforge.core.landing_evidence`'s `parse_github_pr_merge_subject` /
    `parse_station_branch_name` gated on `branch.startswith(f"{station}/")`, so
    `dispatch/pyforge-marshal/22.9` classified as `None` — silently breaking
    `merged_story_keys` → `story_merged_on_main`, i.e. the supervisor's re-landing guard and
    the CAP-2 zombie check, for every dispatch landing merged with this repo's standing
    `gh pr merge --merge` convention. AC-3 names landing classification as a must-agree
    consumer, so this was in scope. Fixed: one shared `_branch_belongs_to_project` predicate
    in both parsers accepting `dispatch/<project_slug>/<key>`, with the literal `"dispatch"`
    living exactly once as `pyforge.core.landing_evidence.DISPATCH_BRANCH_PREFIX`, imported
    by marshal's `core/dispatch.py`. 6 new unit tests + 2 conformance-fixture rows.
  - `[high]` `[patch]` `gather_dispatch_git_facts` read `.effective_branch`, which falls back
    to the station-scoped name — a name that by construction does NOT exist whenever
    `resolved is None` — and handed it to `is_branch_merged`. `git merge-base --is-ancestor`
    exits 128 on a missing ref, and the supervisor's `except (VcsCommandError, ValueError)`
    at `dispatch_supervisor/__main__.py:479` `continue`s inside `while True`: a run that
    spins forever, never judged complete, never landed (and propagates uncaught through
    `cli/dispatch.py:473`). Fixed: keep the whole resolution and report `branch_merged=False`
    without asking git when `resolved is None`. Also closes the same latent raise for a
    branch retired after landing.
  - `[medium]` `[patch]` No test asserted that a `MRS-DISP-030` refusal yields a non-OK exit
    code — the `_dispatch` helper discarded `run_dispatch`'s return, so flipping the finding
    to `WARN` would have left a dispatch that provisioned nothing exiting 0 with the suite
    green. Fixed: helper returns the code; both refusal tests assert `!= EXIT_OK` and the
    `MRS-DISP-031` test asserts `== EXIT_OK` so the discriminator is not vacuous.
  - `[low]` `[patch]` `dispatch_worktree_branch` interpolated the raw story key while
    `dispatch_worktree_path` sanitized it — and attribution now compares a branch-derived
    expectation against a path-derived location, so a key needing sanitization made them
    disagree. Fixed: one `_safe_ref_segment` applied to both segments of both derivations.
  - `[low]` `[patch]` `_same_path`'s `OSError` fallback compared un-normalized paths, so two
    spellings of one worktree could raise a spurious `MRS-DISP-030`. Fixed with pure
    `PurePath` normalization (AD-4 forbids `os` in `pyforge.marshal.core`).
  - `[low]` `[patch]` `_ensure_dispatch_worktree` derived the attribution path twice; now
    passes `worktree=` explicitly like the other two callers.
  - `[low]` `[patch]` `MRS-DISP-031`'s message promised migration on the next dispatch, which
    does not hold while the legacy branch survives landing; reworded to what is guaranteed.
  - `[low]` `[patch]` Garbled `resolve_dispatch_branch` docstring sentence and a
    `_DISPATCH_BRANCH_PREFIX` comment implying the by-branch-name worktree lookup was removed
    (it still exists — which is exactly why the slug is load-bearing). Both corrected.

Rejected as noise, for the record: the cross-station legacy refusal being a "false block"
(the I/O matrix explicitly sanctions "resolved for its original station, **or** loud refusal
naming land-first"), legacy-branch precedence when the station-scoped branch already exists,
the unreachable `MRS-DISP-006` defensive branch, the derivation-guard regex's breadth, the
AC-3 consumer-agreement test not re-covering consumers already covered elsewhere, the
refusal's remedy naming the wrong actor, the absence of a migration/discovery surface, and
ledger/status hygiene that lands with the dispatcher, not the story.

## Auto Run Result

Status: done

**Implemented change.** A dispatch branch now carries its station:
`dispatch/<slug>/<key>`, derived at exactly one site. `core/dispatch.py` owns
`dispatch_worktree_branch(slug, story_key)` (slug a required positional, so any unmigrated
consumer raises `TypeError` instead of silently rendering a station-less name),
`legacy_dispatch_worktree_branch(story_key)` (rendered, never minted), and
`resolve_dispatch_branch(...)` — the single site reconciling the pre-22.9 `marshal/<key>`
name. Attribution is a git fact, never a guess: a legacy branch is this station's only when
git has it checked out at this station's dispatch worktree; anything else is a loud
`MRS-DISP-030` refusal naming the branch and the land-first remedy. Migration is lazy and
one-way — in-flight runs finish on their legacy branch (`MRS-DISP-031`, WARN, so it is
visible), and only new dispatches mint the station-scoped name.

**Files changed**

- `pyforge-marshal/.../core/dispatch.py` — the one derivation, the legacy renderer, the
  resolver, `DispatchBranchResolution`, and the shared `_safe_ref_segment` sanitization.
- `pyforge-marshal/.../cli/dispatch.py` — `_ensure_dispatch_worktree` returns a
  `DispatchWorktreeResolution` and surfaces the refusal.
- `pyforge-marshal/.../dispatch_supervisor/__main__.py` — `gather_dispatch_git_facts`
  resolves rather than derives, and never asks git about an unresolved branch.
- `pyforge-marshal/.../dispatch_land.py` — landing resolves through the same function.
- `pyforge-marshal/.../core/findings.py`, `core/verdict.py` — `MRS-DISP-030` (ERROR) and
  `MRS-DISP-031` (WARN).
- `pyforge-core/.../landing_evidence.py` — `DISPATCH_BRANCH_PREFIX` (the single spelling of
  the literal across both packages) and `_branch_belongs_to_project`, so a dispatch landing
  still classifies.
- Tests: `test_dispatch.py`, `test_dispatch_landing.py`, `test_findings.py`,
  `pyforge-core/tests/unit/test_landing_evidence.py`, plus `branch_exists` on four existing
  dispatch fakes.

**Review findings breakdown.** 8 patched (high 2, medium 1, low 5), 4 deferred (medium 2,
low 2), 8 rejected. 0 intent_gap, 0 bad_spec — no spec loopback; `review_loop_iteration`
stayed 0.

**Follow-up review recommendation: `true`.** Patched-finding counts: high 2, medium 1,
low 5. Two high-severity patched findings alone force `true`; the score is also
`3 × 1 + 1 × 5 = 8`, at or above the threshold of 5.

**Verification performed** (all re-run by the orchestrator after the patches, not taken on
the implementer's report):

- `pixi run -e pyforge-marshal pyforge-marshal-test` → `1 failed, 6508 passed, 12 deselected`.
  The sole failure is `tests/meta/test_skf_domain_skill.py::test_context_files_not_hand_edited`,
  pre-existing: it asserts on `CLAUDE.md` / `AGENTS.md`, and neither file appears anywhere in
  this story's diff.
- `pixi run -e pyforge-core pyforge-core-test` → `13 failed, 1573 passed`. Pre-existing and
  fleet-wide: the 13 are subprocess / atomic-write / exception-root sole-ownership meta tests
  spanning pyforge-atlas, -herald, -mason, -scribe and -steward — packages this story never
  touched. `cli/dispatch.py` appears among them, so that one was checked specifically: the
  diff adds and removes no `subprocess` line in that file.
- `lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml` → `Contracts: 5
  kept, 0 broken` (AD-4 core purity holds — `resolve_dispatch_branch` takes a `VcsPort`, and
  the shared prefix comes from `pyforge.core`; the `..` collapse is hand-rolled because AD-4
  forbids `os` in `pyforge.marshal.core`). Note the bare `lint-imports` invocation reports
  "Could not read any configuration" from the repo root — the config lives in the package's
  `pyproject.toml` and must be named explicitly.
- Matrix test audit: all four I/O-matrix rows are covered by tests that ran and passed —
  new dispatch (`test_dispatch_branch_carries_its_station`), cross-station same key
  (`test_two_stations_sharing_a_story_key_never_reuse_one_worktree`), legacy branch present
  (`..._at_this_stations_worktree_is_still_resolved`, `..._of_another_station_is_refused_land_first`,
  `..._preserved_legacy_branch_without_a_worktree_is_refused_not_stranded`), and landing
  (`test_execute_dispatch_land_lands_an_in_flight_legacy_branch` plus two refusal cases).
  AC-3's guard is `test_only_one_dispatch_branch_derivation_site`, proven to fire by
  temporarily planting a second derivation site.

**Residual risks**

- Highest-value one is deferred, not fixed: a legacy branch surviving only on `origin` is
  invisible to the refusal and gets silently bypassed. Pre-existing in shape, but the
  station-scoped rename makes the orphaned-remote-work state easier to reach in practice.
- Same-station concurrent dispatch is still unguarded (deferred item 2); this story closes
  the cross-station collision only, and the one collision actually on record was
  same-station.
- The new ref shape is asserted only against fakes — no real-git integration test creates a
  three-segment `dispatch/<slug>/<key>` ref (deferred item 4).
- `pyforge-core` is a shared package: the landing-grammar change is additive (it recognizes
  one more branch shape) but is read by doctor and every other station's promotion path.
- Process note for the landing operator: this story's own branch is the legacy-named
  `marshal/22.9`, which `resolve_dispatch_branch` was verified to still resolve. Per the
  always-on PR gate, the PR needs the `maintenance` label (nothing under `recipes/` changed);
  `pixi.toml` is untouched, so no `environment.yaml` re-export is required.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
