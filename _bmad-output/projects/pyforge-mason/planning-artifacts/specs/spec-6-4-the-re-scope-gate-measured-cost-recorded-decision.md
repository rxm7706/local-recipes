---
title: 'Story 6.4 — The re-scope gate: measured cost, recorded decision'
type: 'chore'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
difficulty: 'S'
baseline_revision: 'b2188fcc01f0f9fc9ac1296adfbcc9582d3f55bf'
final_revision: 'f04553bced117ca46f69d5353a556eb8d094763d'
---

<intent-contract>

## Intent

**Problem:** CAP-4's re-scope gate (`campaign.re_scope_gate.reached: false`, `note: null`) has
never fired. Slice 1 (recipe generation) is now genuinely complete (`status: "compiled"`,
`equivalence: "green"`, Story 6.3 landed) but nothing records the measured cost of getting there
or a go/adjust/stop decision for slices 2-5, even though `campaign-state.yaml` already tells
slice 2 "briefing starts only after slice 1's re-scope gate records a go decision."

**Approach:** Analyze the real, already-measured evidence from Stories 6.1-6.3 (commit history,
dual-maintenance burden, the cross-slice-dependency gap Story 6.3 had to discover and fix by
hand, the skf-audit-skill tooling gap found in this environment, remaining-slice size
disparity) and record a dated `re_scope_gate` note with an honest cost accounting, a decision
for the remaining slices, and a high-level end-cutover plan. No slice-2+ brief is written by
this story regardless of the decision recorded.

## Boundaries & Constraints

**Always:**
- Base the cost accounting on evidence actually gathered from this repo's own history and
  files (commit counts, dual-maintenance burden, tooling gaps, remaining-slice sizes from
  `slice-map.md`) -- never invent a number or a claim not traceable to something read.
- The recorded decision must be one of `go` / `adjust` / `stop`, or `adjust` with explicit,
  concrete pre-conditions if the evidence doesn't cleanly support an unconditional `go` -- state
  the reasoning inline in the note, not just the verdict.
- The note must also record a high-level end-cutover plan: the trigger condition (all slices
  reach the appropriate terminal status), the mechanical steps (caller flip per slice-map's
  Mason Caller Inventory, legacy retirement/deprecation), and confirmation that
  `cfe_rebuild_guard_check.py` clause (c) already enforces "no legacy caller survives a
  declared endgame" -- this does not require resolving every open sub-question (e.g. the
  delete-vs-dated-stub deprecation posture) definitively; noting it as still per-slice/open is
  an acceptable outcome for a plan this early in the campaign.
- Set `campaign.re_scope_gate.reached: true` and populate `note` with the dated decision once
  written -- this is the field the acceptance criteria requires populated.
- If the decision is anything other than an unconditional `go`, slice 2's own `next_action`
  text ("briefing starts only after slice 1's re-scope gate records a go decision") must stay
  accurate -- update it if the recorded decision changes what unblocks slice 2 briefing.

**Block If:**
- If the actually-gathered evidence is genuinely ambiguous (points in no clear direction) or the
  cost/risk of recording the wrong decision is asymmetric enough that continuing without a human
  sign-off would be irresponsible -- HALT with status `blocked`, blocking condition `decision
  requires human input`, and present the gathered evidence plus the specific question a human
  needs to answer, rather than picking a verdict to avoid halting.

**Never:**
- Never write a second slice's brief (`skf-brief-skill` invocation) as part of this story --
  the story's own acceptance criteria forbids it regardless of the decision recorded.
- Never touch `cfe_rebuild_guard_check.py`'s clause logic.
- Never retroactively change Story 6.1-6.3's own recorded facts (slice-1 status/equivalence,
  the story specs) -- this story only adds the re-scope note and (if warranted) slice 2's
  `next_action` text.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Evidence supports a clear decision | Real, gathered cost/risk signals from Stories 6.1-6.3 | `re_scope_gate.reached: true`, dated `note` with decision + reasoning + end-cutover plan | — |
| Evidence is genuinely ambiguous | Conflicting or insufficient signals | HALT `blocked`, `decision requires human input`, evidence + question stated | — |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  -- `campaign.re_scope_gate` (`reached`, `note`) populated; slice-2's `next_action` updated if
  the decision changes what unblocks it.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md`
  -- read-only source for remaining-slice sizes (Slice 2/3/4/5 canonical-script/wrapper/MCP-tool
  counts) and the known slice-2/slice-3 cross-slice ordering risk.
- `.github/workflows/` -- read-only, checked for whether any CI workflow already runs the
  equivalence harness / `cfe-rebuild-guard-check` (dual-maintenance-burden evidence).
- Story 6.1-6.3's git history (`23130ee53f`, `1510a022e6`, `bf81f0b7ff`, `ec193303b6`,
  `6dcb882e94`) -- read-only source for the actual measured effort.

## Tasks & Acceptance

**Execution:**
- [x] Gather evidence: real commit history for Stories 6.1-6.3 (effort/rework signal), whether
  any CI workflow enforces the equivalence harness or `cfe-rebuild-guard-check`
  (dual-maintenance-burden signal), the cross-slice-dependency gap Story 6.3 found and its
  implication for larger slices, the `skf-audit-skill` tooling gap (`setup-forge` never run in
  this environment), and slice-map.md's remaining-slice size disparity -- no fabricated numbers
  -- DONE, independently re-verified: all 4 commit diff-line counts exact
  (547/901/5367/447), CI grep exact (only `platform-ci.yml` runs pytest, unrelated Django
  suite; `detectors.yml` line 135 literally `exit 0` regardless of findings), slice sizes exact
  (2=22/17/19, 3=37/35/22, 4=2/2/2, 5=4/0/0) against `slice-map.md`
- [x] Draft the dated re-scope note: cost accounting, decision (go/adjust/stop, with reasoning),
  end-cutover plan -- DONE, decision: ADJUST with 4 concrete, evidence-grounded pre-conditions
- [x] `campaign-state.yaml` -- set `campaign.re_scope_gate.reached: true`, populate `note` --
  DONE, independently re-verified via `yaml.safe_load`
- [x] `campaign-state.yaml` -- update slice-2's `next_action` if the recorded decision changes
  what unblocks slice-2 briefing -- DONE, rewritten to state `reached: true` alone is not a
  green light to brief
- [x] `pixi run -e local-recipes cfe-rebuild-guard-check` -- confirm still exit 0 -- DONE,
  independently re-run: exit 0, clean

**Acceptance Criteria:**
- Given Slice 1's completion, when `campaign-state.yaml` is read after this story, then
  `campaign.re_scope_gate.reached` is `true` and `note` is non-null, dated, and records the
  measured cost, the go/adjust/stop decision for slices 2-5, and an end-cutover plan.
- Given this story completes, when the planning artifacts are inspected, then no slice-2+
  `brief_path` has been set and no `skf-brief-skill`/`skf-create-skill` invocation occurred.
- Given the recorded decision, when slice 2's `next_action` is read, then it accurately
  reflects what (if anything) unblocks slice-2 briefing next.

## Spec Change Log

None -- initial draft.

## Review Triage Log

### 2026-08-21 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 0, medium 5, low 4)
- defer: 0
- reject: 2 (high 0, medium 0, low 2)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter: recording the verdict only in unstructured `note`
    prose (which itself contains the literal word "go" inside negated phrases like "not
    an unconditional go") risks a future naive keyword-grep misreading it as a green
    light. Added a structured, greppable `decision: "adjust"` field alongside
    `reached`/`note`, with an inline comment stating it is not machine-enforced today.
  - `[medium]` `[patch]` Blind Hunter: this file's own pre-existing `status_vocabulary`
    comment reserves "adjust" for dropping/reordering a *specific* slice (mapped to the
    `skipped` state) -- this decision doesn't drop or reorder anything, so labeling it
    "adjust" is a semantic mismatch with the campaign's own vocabulary; it reads closer
    to "conditional go." Added an explanatory comment on the new `decision` field and a
    parenthetical in `note`'s opening line clarifying the label was kept for CAP-4's
    literal three-way vocabulary rather than inventing a fourth term, and pointing to the
    real meaning.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently converged): none
    of the four pre-conditions are machine-enforced -- grepped every relevant script for
    `re_scope_gate`, zero hits outside prose. Added GATHERED GAPS item 5 naming this
    explicitly (a future clause-(d) on `cfe_rebuild_guard_check.py` would close it, out
    of this story's own "never touch clause logic" boundary, named as follow-up-story
    material) rather than leaving the gap silently undocumented.
  - `[low]` `[patch]` Blind Hunter: the per-commit "diff lines" figures were
    insertions-only from `--shortstat`, undercounting `ec193303b6` by 62 lines (~12% --
    those are the review-pass test-hardening deletions, not noise) while the note called
    the counts "exact." Independently re-verified via `git show --shortstat` on all four
    commits; corrected all four figures to state insertions + deletions explicitly
    (548/901/5374/509, ~7,330 total) instead of an insertions-only figure presented as
    the whole count.
  - `[low]` `[patch]` Blind Hunter: REASONING restated "slides 7-12x larger" as a blanket
    justification two paragraphs after REMAINING-SLICE SIZES explicitly corrected that
    framing to apply only to slices 2 and 3 (slice 4 is smaller than slice 1, slice 5
    isn't independent) -- the correction didn't propagate. Reworded REASONING to name
    slices 2 and 3 specifically.
  - `[medium]` `[patch]` Blind Hunter: REASONING called the detector structure "real and
    largely working" while GATHERED GAPS #2, two paragraphs earlier in the same note,
    established CI enforcement is advisory-only for both the guard-check and the
    regression/equivalence net -- an internally inconsistent, overly optimistic framing.
    Also: pre-condition (a)'s "explicitly accept advisory-only enforcement" branch was
    presented as equivalent to actually fixing CI blocking, when it really just accepts
    the residual risk rather than closing gap #2. Reworded both: REASONING now names the
    advisory-only state as a live caveat, not an assumed-solved fact; pre-condition (a)
    now says the accept-the-risk branch "does not close gap #2, it accepts the residual
    risk."
  - `[low]` `[patch]` Blind Hunter: pre-condition (b) elevates a gap diagnosed as
    blocking specifically the *audit* step (gap #1) into a gate on slice 2's *brief* (an
    earlier step), with no stated reason. Added one sentence explaining the deliberate
    choice: discovering the tooling gap only at audit time would repeat gap #1's cost
    pattern one step later, after a full brief-and-compile cycle was already sunk.
  - `[medium]` `[patch]` Blind Hunter: "none of these requires re-opening slice 1's own
    recorded facts" overstates confidence -- slice 1's `equivalence: green` rests partly
    on a manual sha256 substitute (gap #1); once pre-condition (b) is met and
    skf-audit-skill actually runs, it could plausibly surface drift the substitute
    couldn't detect, which would reopen exactly that fact. Reworded to state this
    explicitly as a real, non-zero possibility rather than a closed question. Also added
    Blind Hunter's separate but related suggestion: recommended (not mandated) a repeat
    of this same cost/re-scope exercise before slice 3's brief specifically, since slice
    3 is even larger (12.3x) than slice 2.
  - `[low]` `[patch]` Blind Hunter: the end-cutover plan's caller-flip mechanics only
    discussed the 10 counted `_CFE_SCRIPTS` adapters, omitting two CFE-root artifacts
    slice-map.md's own Coverage Reconciliation section names as outside the counted
    surfaces (`native-build.sh`, `build-locally.py`, both Slice 2). Independently
    verified via grep (`slice-map.md` lines 39/435/436). Added a sentence naming both and
    flagging their cutover-scope status as undecided, to be resolved no later than
    slice 2's brief.
  - `[medium]` `[patch]` Edge Case Hunter (independently found, real): slice-1's own
    `next_action` still read "still reached: false / note: null as of this story" after
    this diff set `reached: true` and populated `note` -- a literal, verifiable
    contradiction of the state two fields away in the same file. Also `campaign.next_story`
    still read "6.2" though 6.2, 6.3, and 6.4 are all done. Independently confirmed both
    via `grep`. Rewrote both to reflect the current state and point at
    `campaign.re_scope_gate` rather than restating values that will go stale again.
  - `[low]` `[reject]` Blind Hunter: "self-assessed governance -- no independent
    reviewer... validating the four pre-conditions are sufficient." The Blind
    Hunter/Edge Case Hunter review pass this finding is itself part of *is* that
    independent check (per this workflow's own step-04 design) -- the concern is
    addressed by the review process already running, not by a further story change.
  - `[low]` `[reject]` Edge Case Hunter: "`campaign-validate-state.py` has zero
    `re_scope_gate` references, so a future edit could desync `reached`/`note` with no
    validator catching it." Ran the validator against this file directly: it validates
    an entirely different, generic `skf-campaign` orchestration-state schema (`skills`,
    `dependency_graph`, `quality_gate`, etc.) that this Epic-6-specific
    `campaign-state.yaml` was never conformant with, before or after this story --
    confirmed by running it and getting the same category of schema-mismatch errors this
    file would have produced under Story 6.1 already. Not a regression this story
    introduced or could reasonably fix (a bespoke schema for this file is a separate,
    larger effort).

## Design Notes

SPEC.md's own Open Questions §3 states explicitly: "Stopping after a clean first slice is an
allowed outcome of the gate, not a failure of the Spec." This story's decision is not a verdict
on whether the pilot succeeded (it did, per Story 6.3's honest CAP-2 completion) -- it is a
forward-looking judgment about whether to keep investing in slices that are, per `slice-map.md`,
7-12x larger than the one just completed, given the real (not hypothetical) cross-slice-gap
discovery cost slice 1 already incurred.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Recorded CAP-4's re-scope gate decision: `campaign.re_scope_gate.reached: true`,
`decision: "adjust"` (continue toward slice 2, gated on 4 concrete pre-conditions rather than
an unconditional go), with a full evidence-based cost accounting and a high-level end-cutover
plan. No slice-2+ brief was written. The decision is grounded in real, independently-verified
evidence: exact commit diff-line counts for Stories 6.1-6.3 (including that Story 6.3 needed a
first BLOCKED pass plus a second pass to close), confirmed absence of CI enforcement for the
CFE test suite/equivalence harness (advisory-only `detectors.yml`), the confirmed
`skf-audit-skill` tooling gap in this worktree, and slice-map.md's exact remaining-slice sizes
(slice 2 ~7.3x, slice 3 ~12.3x slice 1's size; slice 4 smaller; slice 5 not independent).

**Files changed:**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  -- only file touched: `campaign.re_scope_gate.reached`/`decision`/`note` populated;
  slice-2's and slice-1's `next_action` and `campaign.next_story` updated to stay consistent
  with the new state

**Review findings breakdown:** Blind Hunter (adversarial) + Edge Case Hunter ran in parallel,
independently, with no shared context, on this story's diff. 11 distinct findings: 9 patched
(all applied and independently re-verified above -- structured `decision` field added; the
"adjust" label reconciled with this file's own status_vocabulary meaning; machine-enforcement
gap named explicitly; diff-line-count precision fixed; the "7-12x larger" over-generalization
fixed; an internal inconsistency between "real and largely working" and the CI-advisory-only
finding two paragraphs earlier fixed; pre-condition (b)'s brief-vs-audit-time gating justified;
an overclaim about not reopening slice 1's facts softened plus a slice-3 repeat-checkpoint
recommendation added; two concrete, verified staleness bugs in slice-1's `next_action` and
`campaign.next_story` fixed), 2 rejected (with concrete rebuttals recorded in the Review Triage
Log: the review pass itself already is the independent check one finding asked for, and the
other finding's premise -- a generic schema validator should catch this file's drift -- was
verified false by actually running that validator against this file).

**Follow-up review recommendation:** `false`. All patches are narrowly-scoped documentation/
precision fixes to a single YAML file (plus one new, additive, non-breaking structured field);
no code changed, no detector logic changed, already independently re-verified (YAML valid,
`cfe-rebuild-guard-check` clean, `pyforge-mason-test` green) after the patches landed.

**Verification performed (independently, not just trusted from the implementation
subagent):**
- All 4 cited commit `--shortstat` outputs re-run directly: 547/1/901/0/5367/7/447/62
  insertions/deletions exactly as now stated in the corrected note
- `slice-map.md` grep-verified: exact script/wrapper/MCP-tool counts per slice, the CVE-DB
  ordering-risk quote verbatim, the `native-build.sh`/`build-locally.py` Coverage
  Reconciliation exclusion
- `.github/workflows/*.yml` grepped for `pytest`: only `platform-ci.yml`'s unrelated Django
  suite; `detectors.yml` line 135 confirmed literal `exit 0`
- SPEC.md's Open Question 1 quote verified verbatim
- `campaign-validate-state.py` run directly against this file: confirmed it targets an
  unrelated generic schema, not a regression this story caused
- `python3 -c "import yaml; ..."` -- valid YAML, `reached: True`, `decision: "adjust"`,
  `note` non-null, all 5 slices intact and unchanged in status/equivalence
- `pixi run -e local-recipes cfe-rebuild-guard-check` -- exit 0, clean (re-run twice, before
  and after the review-pass patches)
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` -- 1534 passed, 3 deselected
  (unaffected)
- `grep` confirmed no `brief_path` set for any slice beyond slice 1 -- no second brief written

**Residual risks:** The four pre-conditions gating slice 2's brief are not machine-enforced
(explicitly acknowledged in the note itself as GATHERED GAPS #5) -- honored by session/human
discipline reading this file until a follow-up story adds detector support. Slice 1's
`equivalence: green` still rests partly on a manual sha256 substitute for `skf-audit-skill`'s
real workflow; running the real tool later (pre-condition (b)) could in principle surface
something the substitute missed. Two of the four pre-conditions ((a) CI enforcement, (d) the
operator's station-ownership decision) require action beyond this story's own scope to close.
