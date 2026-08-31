---
title: 'Story 5.2: Governance test'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '5bef65e98da6cece8c5256c90a2d58ab08ca3d06'
final_revision: 'ba46a2f3c5f945642410b3067acd6ca57a78bd51'
---

<intent-contract>

## Intent

**Problem:** FR-45/AD-15 require automated proof that Mason never modifies the conda-forge-expert
(CFE) surface, with exactly one sanctioned exception (Story 5.5's closing retrospective commit).
Nothing today scans commit history to enforce this — the guarantee is stated, not checked.

**Approach:** Add a repo-level detector, `scripts/mason_cfe_surface_check.py`, that walks every
commit touching `src/shared/packages/pyforge-mason/**` and asserts none of them also touch the CFE
surface, except at most one commit whose subject starts `retro:` and whose diff includes the CFE
`CHANGELOG.md`. This is a standalone `DETECTOR = {"scope": "repo"}` script (per
`test-architecture.md`'s own classification, "Process/CI check, not a pytest file"), matching the
house pattern of `scripts/unpushed_work_check.py`/`scripts/llms_full_check.py`, not a pytest file
inside pyforge-mason's own suite.

## Boundaries & Constraints

**Always:**
- CFE surface = exactly `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  `.claude/tools/conda_forge_server.py` — no broader `.claude/**` match.
- Commit range is derived (`git log --format=%H HEAD -- src/shared/packages/pyforge-mason`), never a
  hardcoded baseline SHA — that path's history is self-bounding to the mason-CLI effort already
  (starts at Story 1.1's commit).
- Follow the `scripts/*_check.py` self-registration convention exactly (`DETECTOR = {"scope": "repo"}`
  module-level assignment; a pixi task whose `cmd` names the script file, no `--json`) so
  `scripts/detectors.py`'s own registry-gap check stays green with zero other files edited.
- New test file lives at `tests/scripts/test_mason_cfe_surface_check.py`, driving real `tmp_path` git
  repos via subprocess (pattern: `pyforge-doctor`'s `test_sources_ledger.py`) — no GitPython, no new
  dependency.
- If a CFE behavior gap is found during implementation, record it as an open question routed to a CFE
  retrospective; never create a local patch or vendored copy.

**Block If:** `pixi run -e local-recipes spec-surface-check` is currently red for reasons unrelated to
this story (pre-existing repo-wide drift) — fixing that is out of scope here.

**Never:**
- Never treat a `retro:`-subject commit as sanctioned on subject alone — it must also carry the CFE
  `CHANGELOG.md` move, or it is an unsanctioned CFE touch like any other.
- Never require the live repository to already contain the Story 5.5 retro commit for this story's own
  check to pass — that commit does not exist yet (5.5 is a later story). "Exactly once" (AC2) is an
  eventual invariant this detector enforces (0 or 1 sanctioned commits both pass today; 2+ always
  fails); it is proven via synthetic git-history fixtures, not by requiring live history to match.
- Never modify `scripts/spec_surface_check.py` for this story (AC3 only requires it stays green).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean history | commits touch mason path only, none touch CFE surface | 0 findings, exit 0 | — |
| Unsanctioned CFE touch | a non-`retro:` commit's diff touches mason path AND a CFE path | 1 finding, kind `unsanctioned-cfe-touch`, exit 1 | finding names the sha + touched CFE path(s) |
| Borrowed subject | `retro:`-subject commit touches CFE surface but its diff does NOT include CHANGELOG.md | 1 finding, kind `unsanctioned-cfe-touch` (subject alone never launders it) | same as above |
| Sanctioned retro (single) | one `retro:` commit touches CFE surface incl. CHANGELOG.md | 0 findings, exit 0 | recognized as the exception, not reported |
| Exception reused | two separate qualifying `retro:`+CHANGELOG commits in range | 1 finding, kind `exception-reused`, exit 1 | finding names both shas |
| Multi-parent merge touching CFE | a real 2-parent commit appears in the filtered log; plain parent-diff returns empty | falls back to first-parent diff (`<sha>^1..<sha>`) before concluding "touches nothing" | never silently waves through a conflict-resolving merge |
| Live repo, today | real HEAD, ~50 mason commits, 0 CFE touches | 0 findings, exit 0 | confirms current state is green (no retro landed yet) |

</intent-contract>

## Code Map

- `scripts/mason_cfe_surface_check.py` -- NEW, the detector; this story's main deliverable.
- `scripts/unpushed_work_check.py`, `scripts/llms_full_check.py` -- house-style templates: `git()`
  subprocess wrapper, `argparse` + `--json`, exit codes (0 clean / 1 findings / 2 could-not-run),
  findings-as-dicts-with-kind/detail/remedy shape.
- `scripts/detectors.py` -- read-only reference; `_declared_scope()`/`discover()` (~L88-152) define the
  `DETECTOR = {"scope": ...}` registration contract and the "task cmd must name the script file, no
  `--json`" matching rule this story's pixi task must satisfy. No edit needed.
- `pixi.toml` (~L586-589, `[feature.local-recipes.tasks.*]` block) -- add
  `[feature.local-recipes.tasks.mason-cfe-surface-check]`, `cmd = "python scripts/mason_cfe_surface_check.py"`.
- `tests/scripts/test_mason_cfe_surface_check.py` -- NEW test file; auto-collected by the existing
  `[feature.pyforge-ci.tasks.pyforge-doctor-scripts-test]` (`python -m pytest tests/scripts -q`) with
  no pixi.toml change needed on the test side.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger.py` (L37-113) -- reference pattern:
  `_isolate_git_env` autouse fixture (scrubs `GIT_DIR`/`GIT_WORK_TREE`/etc.), `_init_repo`,
  `_commit_all` helpers for building disposable `tmp_path` git repos.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` -- the file whose presence in a commit's diff is the
  CHANGELOG-move signal (no version-string parsing needed — "diff touches this path" is sufficient).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md` (L1260-1300) -- Story 5.2's AC
  source, incl. the 2026-08-10 correct-course re-issue narrowing the commit-range scope.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/mason_cfe_surface_check.py` -- create the detector module (`DETECTOR = {"scope": "repo"}`,
  module docstring citing FR-45/AD-15) with a `git()` subprocess wrapper, a function collecting commits
  via `git log --format=%H HEAD -- src/shared/packages/pyforge-mason`, and a per-commit changed-files
  helper (`git diff-tree --no-commit-id --name-only -r --root <sha>`, falling back to
  `git diff --name-only <sha>^1 <sha>` when that returns empty) -- establishes the scan.
- [x] Same file -- classify each commit that touches both the mason path and a CFE-surface path as
  sanctioned (subject starts `retro:` AND CHANGELOG.md in its diff) or a violation; report
  `unsanctioned-cfe-touch` for any violation and `exception-reused` if sanctioned commits exceed one --
  covers AC1/AC2.
- [x] Same file -- `main()`: argparse (`--json`), findings printout (kind/ref/detail, mirroring
  `llms_full_check.py`'s style), exit 0 clean / 1 findings / 2 if `git log` cannot run -- makes the
  detector consumable by `scripts/detectors.py` and the dashboard.
- [x] `pixi.toml` -- add the `mason-cfe-surface-check` task (see Code Map) -- required for
  `scripts/detectors.py`'s registry to resolve this detector's task (a scanned-but-taskless detector is
  itself a registry finding).
- [x] `tests/scripts/test_mason_cfe_surface_check.py` -- synthetic tmp-git-repo tests covering every row
  of the I/O & Edge-Case Matrix above, using the `test_sources_ledger.py` fixture pattern -- proves the
  detector's logic independent of the live repo's still-incomplete history (Story 5.5 hasn't landed).
- [x] Verify only (no edit expected): `pixi run -e local-recipes spec-surface-check` is green -- AC3.
- [x] `scripts/spec_surface_allowlist.txt` -- UNPLANNED, discovered during verification: the new
  detector script is a repo-root `scripts/*.py` file with no owning spec, so staging it turned AC3's
  `spec-surface-check` red (`ungoverned: fail`) -- the Tasks list above didn't anticipate this because
  the gate had only been exercised against the file while it was still untracked. Added a per-file
  allowlist entry (same class as `unpushed_work_check.py`/`loop_stall_check.py`) -- required for AC3 to
  hold for real, not just before `git add`.

**Acceptance Criteria:**
- Given the mason-CLI effort's commit range (commits touching `src/shared/packages/pyforge-mason/**`),
  when `scripts/mason_cfe_surface_check.py` scans it, then no non-sanctioned commit's diff touches
  `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`, or
  `.claude/tools/conda_forge_server.py`.
- Given a commit whose subject starts `retro:` and whose diff includes the CFE `CHANGELOG.md`, when the
  check runs, then it is recognized as the sanctioned exception and not reported as a finding; given two
  or more such commits, then the check reports `exception-reused` and exits non-zero.
- Given `pixi run -e local-recipes spec-surface-check`, when it runs, then it is green.
- Given `pixi run -e local-recipes mason-cfe-surface-check` (or the script directly) run against the
  live repository today, when it completes, then it exits 0 with zero findings.

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 1, low 6)
- defer: 1: (high 0, medium 0, low 1)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` A `retro:`-subject commit that DELETES (or renames away) the CFE
    `CHANGELOG.md`, rather than adding to it, was wrongly recognized as the sanctioned
    exception -- `is_sanctioned()` only checked whether the path appeared in the changed-file
    list, not its diff status. Fixed by switching from `--name-only` to `--name-status` and
    requiring the CHANGELOG's status be `A` or `M`; added
    `test_changelog_deletion_not_sanctioned`.
  - `[low]` `[patch]` `commit_subject()` was shelled out to twice per unsanctioned commit (once
    inside `is_sanctioned()`, again to build the finding's `detail`). Refactored `scan()` to
    fetch `diff_name_status()` once per commit and reuse it for both the CFE-touch scan and the
    sanction check; `commit_subject()` is now called at most once per CFE-touching commit.
  - `[low]` `[patch]` Zero commits found for `MASON_PATH` (wrong cwd, wrong branch, or a
    shallow/partial clone) was indistinguishable from "scanned and clean" -- `main()` printed
    "0 commit(s)... clean", exit 0. Added an explicit zero-commits guard returning exit 2
    (`UNKNOWN`), matching the existing "`git log` itself failed" exit-2 case; added
    `test_main_exit_2_zero_commits_never_reads_as_clean` and
    `test_mason_commits_returns_empty_list_when_path_never_touched`.
  - `[low]` `[patch]` The new exit-2 zero-commits case above (and the pre-existing `git log`-failed
    exit-2 case) printed plain stderr text even when `--json` was requested, so a machine
    consumer of `--json` couldn't rely on stdout being parseable JSON on every exit code. Added a
    shared `_unknown()` helper that emits a JSON error object on that path when `--json` is set;
    added `test_main_exit_2_json_still_emits_json`.
  - `[low]` `[patch]` The `--json` finding schema was inconsistent across `kind`s: `ref` held a
    single 10-char sha for `unsanctioned-cfe-touch` but a comma-joined multi-sha string for
    `exception-reused`, forcing a machine consumer to special-case parsing by `kind`. Normalized:
    `ref` is now always a single primary sha for every finding kind, and a new `refs` list field
    carries the full set (one entry for `unsanctioned-cfe-touch`, all offenders for
    `exception-reused`). Updated `test_exception_reused_two_qualifying_commits` to match.
  - `[low]` `[patch]` Test coverage never exercised the `.claude/scripts/conda-forge-expert/`
    branch of `CFE_SURFACE_PREFIXES` (only the `.claude/skills/...` sibling and the exact-file
    set were covered) -- added `test_scripts_conda_forge_expert_prefix_also_detected`.
  - `[low]` `[patch]` No test constructed a repo whose very first commit (no parent) is itself
    the CFE-touching Mason commit, so a regression dropping the `--root` flag on `diff-tree`
    would not have been caught -- added `test_root_commit_touching_cfe_surface_is_detected`.
  - `[low]` `[defer]` `git log`'s commit scan is blind to a shallow/partial clone -- systemic to
    every git-log-based `scope: "repo"` detector in this registry (e.g.
    `pyforge.doctor.sources.ledger::gather`), not introduced by this story. Recorded as
    `DW-5-2-1`.
  - `[low]` `[reject]` The self-attested `retro:` + CHANGELOG-in-diff sanction mechanism (no
    binding to a specific SHA, PR, or author) could in principle let any commit claim the
    exception by prefixing its subject -- matches `epics.md` AC2's own ratified definition of
    "sanctioned" verbatim; strengthening it beyond that is a spec-level decision, not this
    story's implementation to make unilaterally.
  - `[low]` `[reject]` No `--follow` on `git log`, so a hypothetical future rename of the whole
    `pyforge-mason` directory earlier in its own history would hide older commits -- speculative,
    no such rename has occurred or is planned; adding rename-tracking complexity now contradicts
    Simplicity First.
  - `[low]` `[reject]` `test_live_repo_today_is_clean`/`test_cli_against_live_repo_exits_zero`
    couple unit tests to the live repository's ever-changing commit history -- intentional,
    matches the spec's own Verification section requiring exactly this check against the live
    repo; a future real CFE-surface violation SHOULD fail these.
  - `[low]` `[reject]` `is_cfe_path()` does bare prefix matching with no path normalization --
    defensible given git's own clean, normalized `--name-status` output; no realistic trigger.
  - `[low]` `[reject]` The module docstring's "never" framing doesn't caveat a commit later
    squashed/rewritten out of history -- matches this repo's existing documentation style
    throughout `scripts/*_check.py` (none of the sibling detectors carry that level of caveat
    either).
  - `[low]` `[reject]` The `pyforge-steward` memlog's claim that `environment.yaml` is unaffected
    by the incidental `pixi.toml` touch ships with no embedded verification artifact -- the
    reviewer itself independently re-ran `pixi project export conda-environment -e build` and
    confirmed the claim true; not a defect.
  - `[low]` `[reject]` `git()` returns `""` on any subprocess failure, indistinguishable from a
    genuinely empty result -- exact match to every sibling detector's own `git()` wrapper (e.g.
    `unpushed_work_check.py`); diverging here would be inconsistent with house convention, not a
    fix.

## Design Notes

**Why "at most one," not "exactly one," at runtime.** AC2 in `epics.md` reads as an eventual invariant
of the whole effort (Story 5.5's retro commit will exist by the time Epic 5 closes), not a precondition
for Story 5.2 itself to be green — Story 5.2 lands strictly before 5.5. The detector therefore accepts
0 or 1 sanctioned commits as passing and only 2+ as a violation; the "must be exactly one, never
skipped" half of the guarantee is Story 5.5's own closing obligation (it must land that commit), proven
here only via synthetic fixtures showing the logic correctly flags a *second* one.

**Merge-commit fallback.** This repo's `gh pr merge --merge` convention (team memory) produces real
2-parent merges on `main`, distinct from bmad-loop's single-parent "Merge ... (bmad-loop)" commits
(verified via `git cat-file -p`). `git log -- <path>` prunes ordinary merges via history simplification,
but a merge that *does* resolve conflicts on a mason path would appear in the filtered range with an
empty default `diff-tree` (no `-m`/`-c` flag) — the first-parent fallback exists specifically so that
case is never silently treated as "touches nothing."

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Added `scripts/mason_cfe_surface_check.py`, proving FR-45/AD-15: a repo-level
`DETECTOR = {"scope": "repo"}` check that scans every commit touching
`src/shared/packages/pyforge-mason/**` and flags any whose diff also touches the CFE surface
(`.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
`.claude/tools/conda_forge_server.py`), except at most one sanctioned exception -- a commit whose
subject starts `retro:` AND whose diff adds/modifies the CFE `CHANGELOG.md` (a mere deletion does
not qualify, fixed during review). A second qualifying commit is itself a finding
(`exception-reused`). Wired into the self-registering detector registry via a new
`mason-cfe-surface-check` pixi task; against the live repository today it scans 50 commits with
zero findings.

**Files changed:**
- `scripts/mason_cfe_surface_check.py` -- new detector (201 lines): `git()` subprocess wrapper,
  `mason_commits()`, `diff_name_status()` (single per-commit fetch reused for both the CFE-touch
  scan and the sanction check, with a first-parent fallback for real multi-parent merges),
  `scan()`, `main()` (argparse `--json`, exit 0/1/2).
- `tests/scripts/test_mason_cfe_surface_check.py` -- new test file (19 tests): every I/O &
  Edge-Case Matrix row via synthetic `tmp_path` git fixtures (`test_sources_ledger.py`'s pattern),
  plus one live-repo regression test and CLI/`main()` smoke tests.
- `pixi.toml` -- added `[feature.local-recipes.tasks.mason-cfe-surface-check]`.
- `scripts/spec_surface_allowlist.txt` -- added a per-file entry for the new script (discovered
  during verification: staging it turned `spec-surface-check` red with `ungoverned: fail`, since
  no spec's `surface:` claims a bare repo-root `scripts/*.py` file; same class as
  `unpushed_work_check.py`/`loop_stall_check.py`).
- `scripts/.spec-surface-baseline.json`, `_bmad-output/projects/pyforge-steward/.../spec-python-agent-platform/.memlog.md`
  -- the mandatory `pixi.toml` task addition is also governed surface of a foreign spec
  (`pyforge-steward/spec-python-agent-platform`, which lists `pixi.toml` as a whole file); recorded
  the incidental touch in that spec's memlog and re-stamped its baseline (scoped to that one spec
  only), per this repo's established convention for incidental cross-spec `pixi.toml` touches.

**Review findings breakdown:** 15 findings from Blind Hunter + Edge Case Hunter (run independently,
no shared context), deduplicated. 7 patched (1 medium -- a real false-negative letting a
`retro:`-subject commit that *deletes* the CHANGELOG.md pass as sanctioned; 6 low -- duplicate
subprocess calls, a zero-commits vacuous-pass gap, `--json` shape/consistency gaps, two test-coverage
gaps). 1 deferred (`DW-5-2-1`: shallow-clone blind spot, systemic to every git-log-based `scope:
"repo"` detector in this registry, not introduced here). 7 rejected as noise (the self-attested
`retro:` sanction mechanism matches `epics.md` AC2's own ratified definition verbatim; a speculative
`--follow`/rename guard; intentional live-repo-coupled regression tests; no realistic path-
normalization trigger; documentation-precision nits matching house style; an independently
re-verified memlog claim; a `git()` failure-handling pattern matching every sibling detector). 0
intent gaps, 0 bad-spec loopbacks. Full detail in the Review Triage Log above.

**Verification performed:** `python -m pytest tests/scripts/test_mason_cfe_surface_check.py -v`
(19 passed). `python scripts/mason_cfe_surface_check.py` and
`pixi run -e local-recipes mason-cfe-surface-check` (50 commits scanned, 0 findings, exit 0) both run
independently after every patch. `pixi run -e local-recipes detectors -- --list` (confirms
`mason_cfe_surface_check` self-registered, `scope=repo`, resolved task, no registry-gap finding).
`pixi run -e local-recipes spec-surface-check` (green -- AC3 -- after the allowlist fix).
`pixi run -e local-recipes detectors-ci` and `pixi run --environment pyforge-ci
pyforge-doctor-scripts-test` run before/after via `git stash` to independently confirm their
respective pre-existing findings (unrelated detectors; `test_deferred_work_promote.py`'s 27
failures, a `ModuleNotFoundError: pyforge` environment issue) are unchanged by this diff, not
introduced by it. `pixi run --frozen -e pyforge-mason pyforge-mason-test` (the station's own suite,
1532 passed, 2 deselected -- confirms no regression, since this story deliberately does not touch
pyforge-mason's own package).

**Residual risks:** None identified that block this story. `DW-5-2-1` (shallow-clone blind spot) is
tracked as deferred, fleet-wide, not story-specific. The self-attested `retro:` + CHANGELOG sanction
mechanism has no cryptographic binding to Story 5.5's actual commit -- accepted as matching
`epics.md` AC2's own definition; Story 5.5 (not yet landed) will exercise this path for real. Story
5.3 (delegation-fidelity test) and 5.4 (free-inheritance verification) remain separate, unstarted
stories.
