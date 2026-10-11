---
title: "94.1: The review gate orders review entries by their real commit times"
type: 'fix'
created: '2026-10-11'
status: 'done'
followup_review_recommended: false
baseline_revision: '378cfdf3f0cbed72caf9b2dbcfd36a124318865e'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-89-1-a-re-dispatch-never-lands-a-story-whose-review-failed.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-79-1-a-landing-promotes-the-story-s-tier-3-feed-row-and-its-tracked-spec-not-only-the-ledger-twin.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/drain_plan.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_only_spec_gate_89_1.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 89.1's review gate takes the latest Review Triage Log entry in git's order, and the blame read that
supplies that order gives most lines the time 0. On 2026-10-11 it took steward 87.5's iteration-1 send-back as the
latest entry over the iteration-2 PASS that answered it, and `marshal factory dispatch` refused a finished story.
Line numbers below are at `6b5182c155`.

**How the order is read.** `latest_review_triage_headings` (`core/dispatch_harness_done.py:419`-`:433`) scores each
`###` heading under `## Review Triage Log` by its line's blame fact: an uncommitted line (the all-zero sha) is newest,
then committed lines by `committer_time`, and a tie is a failed review if any member is. The facts come from
`VcsPort.line_blame_facts`, whose adapter `GitVcs.line_blame_facts` (`adapters/vcs_git.py:1989`-`:2008`) runs
`git blame --porcelain` and hands the output to `_parse_blame_porcelain` (`:2011`-`:2041`).

**What goes wrong.** `--porcelain` prints a commit's details (`author`, `committer-time`, `summary`, …) only the first
time that commit appears in the output. Every later line of the same commit gets a bare `<sha> <orig> <final>` header
and its content line. The parser starts each line at `committer_time = 0` and keeps 0 when no `committer-time` line
follows the header. So only the first surviving line of each commit, in file order, carries its real time. A heading
reads its time only when nothing its commit wrote survives above it.

**The evidence (git and the Tier-3 journal).**
- **The refusal.** Steward 87.5's spec (`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-5-the-herald-webhook-forward-survives-a-client-disconnect-and-proves-ac-6-in-any-order.md`)
  at `a937d924be` reads `status: 'in-review'`. Its log holds three headings:

  | Line | Heading | Commit | `--porcelain` time | `--line-porcelain` time |
  |---|---|---|---|---|
  | 388 | 2026-10-11 — Independent review, iteration 2: PASS (1 minor and 1 trivial deferred) | `a937d924be` | 0 | 1791717848 |
  | 398 | 2026-10-11 — Independent review, iteration 1: sent back (1 major, 4 minor, 2 info, 1 trivial) | `ddbd78cca7` | 1791714400 | 1791714400 |
  | 434 | 2026-10-11 — Build-auto review pass | `1ff032b979` | 0 | 1791710026 |

  `a937d924be` also changed `review_loop_iteration` and `landing_review` (lines 7 and 9), so its heading at line 388 is
  a later line of its commit and read 0. The gate took line 398 as the latest entry, a send-back. The re-dispatch was
  refused with `MRS-DISP-063`: run `pyforge-steward-20261011T085345666Z-55f786aa` journaled a `dispatch-blocked`
  INTENT and OUTCOME at 11:35:04Z naming that heading, status `in-review` and worktree head `a937d924be`.
- **The workaround.** `b80f33a196` changed only the heading line. The PASS heading became its commit's first line
  (1791718634), and the gate permitted. Both readings above were replayed with the shipped parser and gate.
- **The existing test hides it.** `test_git_blame_orders_triage_headings`
  (`tests/unit/test_dispatch_land_only_spec_gate_89_1.py:91`-`:112`) passes only on a tie. Under the shipped parser
  both of its heading lines read 0 (a scratch replay of the same repository gave `{1: t, 2: 0, 3: 0, 4: t, 5: 0}`), and
  the tie rule makes the failed heading "latest".

**Who reads it.** One adapter call serves three judgements:
- `dispatch_once`'s land-only gate: `_spec_line_blame_for_worktree` (`cli/dispatch.py:438`), called at `:3312`, then
  `evaluate_land_only_spec_gate` at `:3318`.
- `marshal factory drain --plan`: `cli/drain_plan.py:342`-`:359`, through the same helper.
- The landing finalize's promotion check: `_promote_tracked_spec`
  (`dispatch_land_finalize/__main__.py:794`-`:813`), which blames the spec at `origin/main`.

**The cost, both ways.**
- A pass committed together with a frontmatter edit reads as older than the failure it answers. A finished story is
  refused, and the operator needs a hand commit to land it (87.5).
- A failure committed together with a frontmatter edit can read as older than the pass before it. A send-back that
  leaves the spec at `in-review` or `done` then lands on a land-only re-dispatch, and the finalize promotes the spec
  past it. That is the landing Story 89.1 exists to stop.

**Approach:** the adapter gives every committed line its own commit's committer time. Nothing else changes.
- Either run `git blame --line-porcelain`, which repeats a commit's details on every line (the parser already reads
  them per header), or keep each commit's `committer-time` by sha while parsing `--porcelain` and apply it to every
  line of that sha. The dev chooses; both meet the ACs.
- A committed line whose commit's `committer-time` never appears in the output (malformed output) is left out of the
  returned map. The gate already reads a heading line with no fact as unevaluable and refuses (AD-8). It is never
  given time 0, which would rank it oldest.
- `VcsPort.line_blame_facts` keeps its signature and return shape (`dict[int, tuple[str, int]]`). Its docstring
  states that every committed line carries its own commit's time.
- **Unchanged:** `iter_review_triage_heading_lines`, `latest_review_triage_headings` and its tie rule, the all-zero
  sha rule for uncommitted lines, `evaluate_land_only_spec_gate`, `MRS-DISP-063`, `MRS-DISP-047`, the three callers,
  and every fake `VcsPort` in the tests.

Ledger key: `94-1-the-review-gate-orders-review-entries-by-their-real-commit-times`.
Type / Effort / Deps: fix / S / 93.1 (queue order, per the operator's ruling; no code dependency).

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-169 (← `spec-marshal-single-story-dispatch` CAP-11): Story 29.2's
  land-only path, extended by Stories 83.7, 83.10 and 83.18, whose review gate Story 89.1 added. With it, CAP-229
  (promotion runs on landing), realized for the tracked spec by Story 79.1, where Story 89.1 added the check that a
  failed review is never promoted. This story fixes the realization of both, so it mints no CAP and changes no
  `SPEC.md`.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: it restores intended behaviour (git's
  order), and a flag would keep the defect reachable.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-11 (a passing review read as older). Operator
  ruling 2026-10-11, verbatim label: "Mint fix story (Recommended)"; option text: "Epic 94 / Story 94.1 on
  pyforge-marshal: correct per-line committer time in _parse_blame_porcelain, test with a commit that edits
  frontmatter and a later heading; queue after 93.1."

## Acceptance Criteria

Every repository test builds a real temporary git repository (as `test_git_blame_orders_triage_headings` does) and
commits with explicit, distinct committer dates (`GIT_COMMITTER_DATE`), so the order never rests on two commits landing
in the same second. The spec fixture has a frontmatter fence with `status:` and `review_loop_iteration:` lines above
`## Review Triage Log`.

- **AC1 — The 87.5 shape lands.**
  - **Given** commit A adds only a send-back entry (its heading "Independent review, iteration 1: sent back (1 major)"
    and a body line) to the log, and a later commit B changes `review_loop_iteration:` in the frontmatter **and** adds
    a heading "Independent review, iteration 2: PASS" above A's heading, with the spec at `status: 'in-review'`.
  - **When** `GitVcs.line_blame_facts` reads the spec in the worktree and `evaluate_land_only_spec_gate` judges it.
  - **Then** the PASS heading's line carries B's committer time, `latest_review_triage_headings` returns only the
    PASS heading, and the verdict is `permitted` with no `failed_heading`. (At `6b5182c155` the PASS line reads 0, the
    send-back is latest and the verdict refuses.)
  - **And** the same spec blamed at a ref (`ref=` instead of `worktree=`, the finalize's read) gives the same facts and
    the same verdict.
- **AC2 — The mirror refuses.**
  - **Given** commit A adds only a passing entry (its heading "Review pass" and a body line), and a later commit B
    changes a frontmatter line **and** adds a heading "Independent review: FAIL (1 high)" below it, with the spec at
    `status: 'in-review'`.
  - **Then** the FAIL heading is the only latest heading, and the verdict refuses with `failed_heading` naming it,
    whether the spec is blamed in the worktree or at a ref. That `failed_heading` is what `_promote_tracked_spec` turns
    into its `MRS-DISP-047` WARN instead of promoting. (At `6b5182c155` the FAIL line reads 0, "Review pass" is
    latest and the verdict permits.)
- **AC3 — Every committed line carries its commit's time.**
  - A parser test over `--porcelain`-shaped text, where one sha owns two groups and only the first carries its
    details, maps every line of both groups to that commit's `committer-time`.
  - A repository test asserts that every line of a commit that changed several lines carries a non-zero time equal to
    `git log -1 --format=%ct <sha>`.
- **AC4 — An unreadable time is never oldest.** A parser test feeds output in which a committed sha's details carry
  no `committer-time` line. That sha's lines are absent from the returned map, `latest_review_triage_headings` returns
  `None` for a heading on such a line, and `evaluate_land_only_spec_gate` returns `unevaluable=True` and refuses. No
  committed line is ever returned with time 0.
- **AC5 — The existing test proves the order.** `test_git_blame_orders_triage_headings` asserts that its two heading
  lines carry distinct non-zero times and that the newer one is the FAIL heading alone, so it can no longer pass on a
  tie. `test_parse_blame_porcelain_sample` passes unchanged.
- **AC6 — Everything else is unchanged.**
  - Uncommitted lines still use the all-zero sha and rank newest.
  - The fakes in `tests/unit/test_dispatch.py`, `test_dispatch_fleet.py` and `test_dispatch_land_finalize.py` are
    untouched, and every existing marshal test passes.
  - `tests/meta/test_local_branch_refs_are_full_refnames.py` still pins `line_blame_facts`'s ref argument.
  - The dev names any changed expectation, with its reason, in the Spec Change Log.
- **AC7 — Mutation.**
  - Restoring the first-header-only parse (`--porcelain` with `committer_time` reset to 0 per header) fails AC1, AC2,
    AC3 and AC5.
  - Defaulting a missing time to 0 instead of leaving the line out fails AC4.

## Boundaries & Constraints

**Always:**
- Keep git's order as the one authority for which entry is latest (AD-33). The fix is in the adapter, at the edge
  (AD-4); the pure gate in `core/dispatch_harness_done.py` does not change.
- Treat a time that cannot be read as unevaluable (AD-8), never as oldest.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-marshal`, and `spec-pyforge-core` for the port and the adapter, plus every co-governor
  `spec-surface-check` names (AGENTS.md pre-PR item 5).

**Never:**
- Never change the gate's rule, its tie rule, its finding codes or its callers here.
- Never change the `VcsPort.line_blame_facts` signature or return shape.
- Never edit a story spec, its Review Triage Log or a ledger key to get past the gate, and never land, push or merge
  steward 87.5 from this story.

**Residual risk:**
- Committer time is wall-clock time. A rebase or an amend restamps a commit, so it can reorder entries. That is Story
  89.1's chosen rule, and it is unchanged here.
- A heading line edited later (a typo fix) still becomes the newest entry, as Story 89.1's spec records.

## I/O & Edge-Case Matrix

| Log state | Commit that wrote the latest heading | At `6b5182c155` | After |
|---|---|---|---|
| send-back (older) then PASS | also edits frontmatter above the log | PASS reads 0; send-back is latest; `MRS-DISP-063` | PASS is latest; land-only proceeds |
| PASS (older) then FAIL | also edits frontmatter above the log | FAIL reads 0; PASS is latest; lands, finalize promotes | FAIL is latest; `MRS-DISP-063`; finalize does not promote |
| send-back then PASS | touches only the heading (87.5's `b80f33a196`) | PASS is latest | unchanged |
| any committed heading | its commit's time missing from the output | read as 0 (oldest) | left out; unevaluable; refused |
| uncommitted heading | none (all-zero sha) | newest | unchanged |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-11 (a passing review read as older) entry.
- Epic: Epic 94, a new fix epic, because Epic 89, which shipped the gate, is `done`.
- Ledger key: `94-1-the-review-gate-orders-review-entries-by-their-real-commit-times`.
- Ledger status at mint: `backlog`.
- Deps: 93.1. It is a queue order from the operator's ruling ("queue after 93.1"); the drain's plan holds this story
  until 93.1 is `done`. No code depends on 93.1.
- Surface: `[epic_surfaces]` `"94"` in `marshal-policy.toml` (the default surface and every Spec memlog).
- Related: steward 87.5's own landing is the operator's (its PASS heading was re-committed alone at `b80f33a196`).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 (the derived surface guard).

**Manual checks (not a dispatch gate):**
- The two mutations of AC7 — expected: each fails its named test. Restore each.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the
  scoped stamps.
- Replay on the host: blame steward 87.5's spec at `a937d924be` through `GitVcs.line_blame_facts(ref=...)` and judge it
  with `evaluate_land_only_spec_gate`. Expected: line 388 carries 1791717848 and the verdict is `permitted`.

## Named, not fixed here

- **The finalize promotes when the log cannot be read.** `_promote_tracked_spec` blocks only on a named failed heading
  (`gate.failed_heading is not None`), so an unevaluable blame still promotes the spec to `done`. Story 89.1 chose
  that; this story leaves it as it is.
- **Steward 87.5's landing** is the operator's. Its branch already carries the workaround commit `b80f33a196`.

## Spec Change Log

- 2026-10-11 — `test_git_blame_orders_triage_headings` now uses distinct `GIT_COMMITTER_DATE` values and asserts non-zero times with FAIL alone as latest (AC5); prior tie-only pass hid the porcelain reuse bug.

## Auto Run Result

- Summary: `_parse_blame_porcelain` caches `committer-time` by commit sha so bare `--porcelain` headers inherit the real time; committed lines without a readable time are omitted (never time 0).
- Files: `vcs_git.py` (parser + adapter docstring), `ports/vcs.py` (port docstring), `test_dispatch_land_only_spec_gate_89_1.py` (AC1–AC5 tests).
- Review: one review pass; 0 patch/defer/intent findings after triage (self-review of diff).
- Follow-up review recommended: `false`
- Verification: `pyforge-marshal-test`, `pyforge-deps-test`, `lint-types`, `spec_surface_reconcile` — all exit 0.
- Residual: finalize still promotes on unevaluable blame (unchanged per spec).

## Review Triage Log

### 2026-10-11 — Build-auto review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - (no findings from review layers)
