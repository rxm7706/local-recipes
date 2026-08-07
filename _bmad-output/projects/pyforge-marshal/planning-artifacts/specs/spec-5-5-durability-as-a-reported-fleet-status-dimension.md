---
title: 'Durability as a reported fleet-status dimension'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '8f8c22376765aeef9c6ff592ae797c06a59478dc'
---

<intent-contract>

## Intent

**Problem:** "is the fleet's work saved?" today means running a SEPARATE command, `scripts/unpushed_work_check.py` (the repo's own existing `runtime`-scoped detector, whose own docstring names the exact live incident that motivated it: 2026-07-31, six station branches with 8-9 unpushed commits each, none on origin, undetected by nine green detectors). FR-62/AD-48 close this: the SAME evidence that detector already computes shows up on the OWNING row in `marshal status`, so a second command is never required just to answer that question.

**Approach:** `cli/status.py`'s fleet-summary path runs the EXISTING `scripts/unpushed_work_check.py --json --branches-only` ONCE per invocation (via `ProcessPort.run`, never a second detection mechanism -- AD-48's own explicit "read from, never re-derive against git independently") and folds its own JSON `findings` (`{"kind": "unpushed-branch", "ref": <branch>, "files": <int>, "stat": <shortstat text>, "remedy": <str>}`) onto each home's own row by matching `ref` against that home's station branch (`loop/<slug>`). A matching finding means the row carries an `unpushed_work` field naming the branch, file count, and the detector's own shortstat text verbatim (never a re-derived line count) -- AND a registered WARN `Finding` is appended to the command's own envelope, so the row is NEVER reported clean (the envelope's own verdict lattice already makes a present finding non-`clean` -- this story leans on that existing machinery, it does not invent a second "is this row clean" concept). `--branches-only` is used deliberately (never the detector's own dangling-object scan), keeping this a bounded, local-branch-diff-only read that stays inside NFR-14's 10-second/7-homes budget -- the SAME reason the detector's own docstring names `--branches-only` as the fast path.

## Boundaries & Constraints

**Always:**
- **The unpushed-work evidence is READ from `scripts/unpushed_work_check.py`'s own JSON output, never re-derived** (AD-48) -- `marshal status` shells out to the EXISTING detector (`ProcessPort.run(["python3", str(script_path), "--json", "--branches-only"], cwd=repo_root)`) rather than reimplementing its own branch-diff-vs-remote logic a second way.
- **Scoped to `--branches-only`** -- the detector's own dangling-commit scan (`git fsck`) is skipped; this story's own scope is "is this HOME's branch unpushed," not the fleet-wide dangling-object sweep (out of scope, matching the detector's own documented fast-path flag).
- **A finding is matched to a home by `ref == f"loop/{slug}"`** -- the home's own station branch. Per-story branches (bmad-loop's own worktree-isolated task branches, already Story 4.10's own retirement-sweep concern) are OUT of this story's scope -- the AC's own wording ("that row") is singular, per-home, matching the detector's OWN default population (station branches are what actually accumulated unpushed work in the detector's own motivating incident).
- **The finding names the branch and the extent** -- `files` (an int) and `stat` (the detector's own `git diff --shortstat` text, which already contains the real insertion/deletion line counts as free text) -- reported VERBATIM, never re-parsed into a separate numeric line-count field this story would then own deriving.
- **A home with unpushed work is NEVER reported clean** -- a registered WARN `Finding` (new code) is appended whenever a matching finding exists, leaning on the existing verdict-lattice machinery (a present finding already makes the envelope non-`clean`) rather than inventing a parallel "dirty" flag.
- **Additive, no version bump** (FR-40/AD-39) -- `unpushed_work` is a NEW field on the ALREADY-shipped fleet-row shape (Story 5.1); per AD-39's own explicit rule, an additive field bumps neither `schema_version` nor `data_version`. `schemas/status.json`'s own fleet-row shape (if published; see Design Notes) gains the field as OPTIONAL, not required, to keep the additive contract honest for any consumer already validating against the prior shape.
- **A detector failure (script missing, non-zero exit, malformed JSON, or the documented `UNKNOWN` exit-2 case when offline/no remote) is a registered WARN, never a hard failure for the whole sweep** -- every home's row still reports, with `unpushed_work: null` (unknown, not "clean" -- this story never silently treats "could not check" as "nothing to report").

**Never:**
- No re-implementation of the detector's own branch-vs-remote diff logic, remote-branch enumeration, or shortstat computation.
- No dangling-object scan (`--branches-only` is always passed).
- No per-story-branch matching -- station branch only, this story's own explicit scope.
- Do not silently treat a detector failure as "no unpushed work" -- that is exactly the false-green the detector's own docstring names as the original incident's own root cause.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No unpushed work anywhere | Clean fleet | Every row's `unpushed_work: null`, no finding | No finding |
| A home's station branch has unpushed content | The motivating incident | That row's `unpushed_work` names files/stat/remedy; a WARN finding names the branch | Registered WARN |
| The detector script is missing/fails to run | Environment gap | Every row's `unpushed_work: null` (unknown), one WARN naming the failure | Registered WARN |
| The detector reports its own `UNKNOWN` (offline, no remote) | No network/remote | Same as above -- treated as "could not check," never "clean" | Registered WARN |
| A finding whose `ref` matches no known home's branch | An orphaned/other branch | Ignored for row-folding purposes (not this story's concern -- `marshal retire`'s own sweep, or the detector's own standalone output, still names it) | No finding |
| `--format json` vs default text | Either | `unpushed_work` present identically in both | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/cli/status.py` -- EDIT. Fleet-summary path gains one `ProcessPort.run` call to the detector script, JSON-parsed, folded per-home by `ref`.
- `src/pyforge/marshal/core/status.py` -- EDIT. `FleetHomeFacts` gains `unpushed_work: dict[str, object] | None`; `build_fleet_row` includes it.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- EDIT. Register + classify the new "unpushed work present"/"detector unavailable" codes.
- `src/pyforge/marshal/schemas/status.json` -- EDIT (optional field addition, additive only).
- `tests/unit/test_status.py` -- EDIT. Matrix above.

## Design Notes

- **Why the detector is invoked ONCE for the whole sweep, not once per home:** the detector's own read (`git for-each-ref`/`git diff --name-only` per local branch) already covers every branch in the ONE physical repo every loop home shares -- invoking it per-home would be `N` redundant full scans of the same repo state for no additional evidence, directly working against NFR-14's own budget.
- **Why `--branches-only`, always:** the dangling-commit half of the detector (`git fsck --no-reflogs`) is a genuinely slower, whole-object-graph scan; this story's own AC scope ("a loop home whose BRANCHES carry local-only content") never asks for dangling-commit coverage, so there is no reason to pay that cost on every `marshal status` invocation.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

## Spec Change Log

**1. `unpushed_work` is threaded through the `journal_unreadable`/`has_run=False` degraded row shapes, not hardcoded `None` — a critical, post-implementation-review correction to a literal reading of Story 5.3's own precedent.** The implementing engineer mirrored `escalation_reason`/`escalation_artifact`'s established "hardcode `None` in a degraded row" pattern without re-examining whether it applies here. It does not: those fields' only source IS the same journal that's unreadable/absent; `unpushed_work`'s source is a completely independent git branch-vs-remote diff, gathered once up front regardless of journal state. See Review Triage Log for the full account.

## Review Triage Log

### 2026-08-07 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 4 (critical 1, medium 2, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[critical]` `[patch]` **Degraded rows (`journal_unreadable`, `has_run=False`) structurally suppressed real unpushed-work evidence -- the exact false-green this whole story exists to eliminate.** Found by the Blind Hunter, specifically tasked with investigating a design gap the implementing engineer had already flagged in their own report. Confirmed the diff's own tests codified the bug as expected behavior (`test_*_never_surfaces_unpushed_work` asserted `unpushed_work is None` even given a real matching detector finding). Root cause: `build_fleet_row` hardcoded `"unpushed_work": None` in both degraded-row branches instead of reading `facts.unpushed_work` (an independently-sourced signal with no dependency on journal/run state at all). Fixed: both branches now report `facts.unpushed_work` verbatim; the existing WARN-emission gate (keyed off the resulting row, not `facts` directly) now correctly fires for degraded rows too. Both tests renamed and inverted to assert the finding DOES surface (`test_journal_unreadable_row_still_surfaces_real_unpushed_work`, `test_has_run_false_row_still_surfaces_real_unpushed_work`).
  - `[medium]` `[patch]` **A bare `"python3"` was used to launch the detector subprocess instead of `sys.executable`, diverging from `cli/spin.py`'s own established precedent for spawning a Python child under the SAME interpreter Marshal itself runs under.** Found by the Edge Case Hunter. In a pixi/conda environment whose activated shell doesn't expose a bare `python3` on `PATH`, this would silently degrade every run to `MRS-STATUS-009` ("detector unavailable") -- failing safe, but defeating the whole feature in exactly the environments most likely to differ from a developer's default shell. Fixed: `sys.executable`.
  - `[medium]` `[patch]` **A structurally-valid-but-incomplete detector finding entry (missing/wrong-typed `files`/`stat`/`remedy`) was still treated as "matched," producing a real `MRS-STATUS-008` WARN with garbage content (e.g. "carries None file(s)... (None) -- None") instead of degrading cleanly.** Found by the Edge Case Hunter. Fixed: `files`/`stat`/`remedy` are now type-validated (int/non-empty-str/non-empty-str); a malformed entry is skipped (never surfaced with placeholder content), without escalating the WHOLE sweep to "detector unavailable" over one bad entry.
  - `[low]` `[patch]` **The detector's own `stat` text was interpolated into the text-format renderer with no sanitization -- an embedded newline could break the "one line per row" contract every text-format consumer relies on.** Found by the Edge Case Hunter. Fixed: `stat` is newline-stripped before interpolation.
- deferred: none this pass (the remaining low-priority "timeout budget claim vs. real NFR-14 enforcement" comment inaccuracy was corrected inline as part of this same patch pass, not deferred).
- rejected: none this pass.

## Suggested Review Order

**The critical fix — start here**

- `build_fleet_row`'s degraded-row `unpushed_work` threading.
  [`core/status.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py) — search `Code review (2026-08-07, Blind Hunter, the single most severe`

**Correctness fixes**

- `_gather_unpushed_work_findings`'s `sys.executable` fix and the new `files`/`stat`/`remedy` type validation.
  [`cli/status.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py) — search `_gather_unpushed_work_findings`

**Tests (peripherals)**

- The two renamed/inverted degraded-row tests, plus the full `TestUnpushedWork` matrix.
</intent-contract>
