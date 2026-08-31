---
title: The slice-2 re-scope checkpoint
type: chore
created: '2026-08-27'
status: done
updated: '2026-08-28'
baseline_revision: 7e84b9174d740a7a488ba3f5d50d9fea6d0784a4
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-4-the-re-scope-gate-measured-cost-recorded-decision.md
warnings: [oversized]
deferred:
  - summary: >-
      cfe_rebuild_guard_check.py's clause (d) enforces only
      campaign.re_scope_gate.pre_conditions, never re_scope_gate_2.pre_conditions, so a
      slice-3/4 brief_path write is not machine-blocked by this story's new gate.
    evidence: |-
      Independently confirmed by 3 of 4 review-pass layers (Blind Hunter, Verification
      Gap Reviewer, Edge Case Hunter) against the diff since baseline_revision
      7e84b9174d740a7a488ba3f5d50d9fea6d0784a4. clause (d) reads only
      campaign.get("re_scope_gate") and its four hardcoded
      RE_SCOPE_GATE_PRE_CONDITION_KEYS (a_ci_enforcement/b_skf_setup/
      c_cross_slice_rederivation/d_ownership_decision) -- all four already
      status: closed today, so clause (d) is vacuously satisfied for any order>=2
      slice's brief_path regardless of re_scope_gate_2's two new pre-conditions
      (slice1_equivalence_closure/slice2_equivalence_closure, both still open).
      tests/scripts/test_cfe_rebuild_guard_check.py has no test referencing
      re_scope_gate_2 either. This story's own Never-boundary explicitly forbids
      touching cfe_rebuild_guard_check.py's clause logic (matching Story 6.4's own
      GATHERED GAPS #5 precedent of naming an enforcement gap rather than closing it),
      so closing this is out of scope here -- deferred for a follow-up story to extend
      clause (d) (or add a clause (e)) to also read re_scope_gate_2.pre_conditions.
    location: >-
      scripts/cfe_rebuild_guard_check.py:304-341
    severity: medium
---

<intent-contract>

## Intent

**Problem:** After slice 2 completes (Story 12.7), nothing yet records its measured cost or
a go/adjust/stop decision for slices 3-4, slice 5's opportunistic porting, or the end-cutover
decomposition trigger. Story 6.4's own re-scope note already recommends this exact repeat
"before slice 3's brief specifically, since slice 3 is even larger (12.3x) than slice 2."

**Approach:** Record a second dated re-scope note in `campaign-state.yaml` — slice 2's
measured cost, the go/adjust/stop decision for slices 3-4, slice 5's opportunistic-porting
status, and the end-cutover decomposition trigger — following Story 6.4's own note-writing
discipline. No slice-3 brief and no endgame stories land before this checkpoint.

## Acceptance Criteria

- **Given** the completed slice 2 **Then** a second dated re-scope note in campaign state
  records slice 2's measured cost and the go/adjust/stop decision for slices 3–4, slice 5's
  opportunistic porting, and the end-cutover decomposition trigger — no slice-3 brief and no
  endgame stories before this lands (the 6.4 note's own recommendation before the 12.3x
  slice).

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-8-the-slice-2-re-scope-checkpoint`.
- Block until Story 12.7 (`slice-2-recipe-lifecycle` at `status: compiled`/`equivalence:
  green`, or an honestly-recorded non-green) is done — this story's sole Dep.
- Follow Story 6.4's own note-writing discipline exactly: base the cost accounting on
  evidence actually gathered (12.7's real commit history, dual-maintenance burden, any new
  cross-slice gaps found), record a structured `decision` field (go/adjust/stop) alongside a
  dated prose `note` — avoiding 6.4's own review-caught pitfall of recording the verdict only
  in prose — and state whether slice 5's opportunistic porting needs any explicit action yet.
- Decide/record slices 3-4's own go/adjust/stop and the end-cutover decomposition trigger,
  updating Story 6.4's own "high-level end-cutover plan" with whatever changed since slice 1
  (e.g. `campaign.callers` population plan; SPEC.md Open Question 4's deprecation posture;
  Open Question 5's Rule-2-retro-landing-surface precedent, now that Story 12.7 should have
  set it).

**Block If:** The evidence is genuinely ambiguous, or the risk of recording the wrong
decision is asymmetric enough to need human sign-off — HALT `blocked`, per Story 6.4's own
precedent, rather than picking a verdict to avoid halting.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) — mason consults CFE, never edits it
  (mason-cfe-surface-check gate).
- Never write slice 3's brief as part of this story, regardless of the decision recorded —
  matches Story 6.4's own "never write a second slice's brief" boundary, one slice number
  further on.
- Never touch `cfe_rebuild_guard_check.py`'s clause logic (including the clause (d) Story
  12.4 adds) — this story only writes campaign-state.yaml's re-scope note, same as Story
  6.4's own boundary.
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Evidence supports a decision | Slice 2's real cost data (Story 12.7) | Second dated re-scope note recorded, `decision` field set | — |
| Evidence ambiguous | Conflicting signals | HALT `blocked`, evidence + question stated | — |
| Decision recorded | — | Slice 3/4's `next_action` text updated to match, same as Story 6.4 did for slice 2 | Must not leave stale `next_action` text (Story 6.4's own review-caught bug) |
| No slice-3 brief exists yet | — | Verified: `slices[2].brief_path` still `null` after this story | Test/verification step, not just a promise |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — add a second dated re-scope note (structured similarly to the existing
  `campaign.re_scope_gate` block — a new key such as `campaign.re_scope_gate_2`, or an
  appended dated entry within the existing note, whichever keeps the file most resumable per
  CAP-4's "fresh session reads one file" design intent); update slice 3/4's `next_action` text
  to match whatever is decided, mirroring how Story 6.4 updated slice 2's and its own
  `campaign.next_story` field.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md`
  — read-only source for slice 3 (37/35/22) and slice 4 (2/2/2) sizes, already exact per
  Story 6.4's own re-verification.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md`
  — read-only; Open Questions 4 (deprecation posture) and 5 (Rule-2 retro landing surface)
  should be referenced/updated if Stories 12.6/12.7 resolved either in practice.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  -- add a `campaign.re_scope_gate_2` block (sibling of the existing `campaign.re_scope_gate`,
  same shape: `reached`/`decision`/`pre_conditions`/`note`) recording slice 2's measured cost
  (Stories 12.6+12.7's real commit history), gathered gaps (dual-maintenance/drift signal from
  both compiled slices, new cross-slice findings from 12.6/12.7), a structured `decision` field
  (go/adjust/stop) for slices 3-4, slice 5's opportunistic-porting status, and the end-cutover
  plan update -- structured field alongside dated prose, per Story 6.4's own review-caught
  pitfall of recording the verdict only in prose -- DONE: `decision: "adjust"`,
  `pre_conditions: {slice1_equivalence_closure: {status: open}, slice2_equivalence_closure:
  {status: open}}` (each key is a nested object with its own `status`/`note` fields, not a
  flat scalar -- both currently `status: "open"`),
  cost/gaps/decision/slice-5-status/end-cutover-update all in the dated `note`, every figure
  independently re-verified against `git show --shortstat` and the live compiled packages
  (see Auto Run Result below).
- [x] same file -- update `slices[2].next_action` (slice-3-atlas-intelligence) and
  `slices[3].next_action` (slice-4-project-scanning-security) to name the new gate; no stale
  text left behind (Story 6.4's own review-caught bug) -- DONE, both rewritten to point at
  `campaign.re_scope_gate_2` instead of restating "not yet scheduled" verbatim.
- [x] same file -- update `campaign.next_story` to point past Story 12.8 -- DONE.

**Acceptance Criteria:**
- Given the completed slice 2 (Story 12.7, done), when `campaign-state.yaml` is read, then a
  second dated re-scope note (`campaign.re_scope_gate_2`) exists recording slice 2's measured
  cost, a structured `decision` for slices 3-4, slice 5's opportunistic-porting status, and the
  end-cutover decomposition trigger.
- Given the new decision, when `slices[2]` and `slices[3]` are inspected, then their
  `next_action` fields reflect the new gate.
- Given this story's own scope, when the working tree is diffed, then only
  `campaign-state.yaml` (+ this spec file) changed -- no slice-3 brief
  (`slices[2].brief_path` stays `null`), no `epics.md`/`sprint-status-ledger.yaml`/CFE-surface
  edits.

## Design Notes

- **`status: ready` treated as this story's entry point (equivalent to `draft`).** The sibling
  story immediately before this one (12.7) started at the identical `status: ready` with no
  `Tasks & Acceptance` section yet present -- confirmed via `git show` on its first commit --
  and was planned/implemented/reviewed in place on the same physical file, ending `status:
  done`. This file follows that established, direct precedent rather than re-deriving a fresh
  spec under `implementation-artifacts/` (which would duplicate the existing intent-contract,
  violating "the spec is the contract" convention).
- **A real tension between this spec's Dep condition and `campaign-state.yaml`'s own
  `next_action`, resolved rather than papered over.** This story's own Boundaries say the sole
  Dep is "Story 12.7 done, with `equivalence: green` OR an honestly-recorded non-green" --
  satisfied (12.7 is done; slice 2's `equivalence: stale` is honestly recorded, a real,
  reproduced, pre-existing-debt finding, not fabricated). But `campaign-state.yaml`'s own
  slice-2 `next_action`, and Story 12.7's own Auto Run Result residual-risk #1, both say the
  stale equivalence should close "before Story 12.8's re-scope checkpoint." No story exists for
  that closure (Epic 12 ends at 12.8), and this story's own Approach is scoped to writing the
  note, not porting code across 5 scripts.

  Resolution: treat "close before 12.8" as intending "close before the *next* brief," the same
  gating shape CAP-4/Story 6.4 already established (pre-conditions gate a brief write, not the
  checkpoint story that records them) -- not a hard block on this story running. This is
  directly supported by precedent: Story 12.7 itself hit an analogous real, reproduced,
  pre-existing-debt divergence and did not halt -- it recorded `equivalence: stale` honestly and
  continued (mirroring Story 12.3's identical choice for slice 1's own stale finding). Both
  compiled slices now carry the same class of gap. `re_scope_gate_2` below names both slice 1's
  (`github_updater.py` HEAD-advance port, Story 12.3's residual) and slice 2's (5-script
  depth-independent repo-root port, this story's own finding) as new pre-conditions gating
  whichever of slice 3 (atlas) or slice 4 (mason) briefs next -- closing the gap for real before
  further campaign progress, without inventing a blocking condition this story's own literal
  Dep text does not support.
- **Open Questions 4 and 5 remain unresolved in practice.** Grepped Stories 12.6 and 12.7 for
  "deprecat" and "Rule-2" -- neither touched OQ4 (deprecation posture). Story 12.7 explicitly
  left OQ5 (Rule-2 retro landing surface) "genuinely undecided by this spec," and its own
  `brief_mirrored_through` note confirms no new CFE Rule-2 retro landed during 12.7 (clause (b)
  was already green), so no precedent was actually set. `SPEC.md` therefore is not edited by
  this story (per its own Code Map read-only note: update only if 12.6/12.7 resolved either in
  practice; neither did) -- both remain open, restated as still-open in `re_scope_gate_2`'s
  note rather than silently dropped.
- **One additional, minor observation surfaced during evidence-gathering (not a gap requiring
  action).** Slice 1's compiled `recipe-generator.py` optionally imports `_http` (a Slice-5
  shared-infra module), but slice 1's compiled package does not include `_http.py` --
  unlike slice 2, which ported it. The import is wrapped in an `ImportError`-tolerant fallback
  pattern per the script's own inline comments, so this is a designed-optional dependency, not
  a functional gap. Noted for completeness under slice 5's opportunistic-porting status; no
  action taken (out of this story's Code Map).

## Review Triage Log

### 2026-08-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (0 high, 1 medium, 2 low)
- defer: 1 (0 high, 0 medium, 1 low)
- reject: 10
- addressed_findings:
  - `low` `patch` `## Verification`'s grep command used `-A2`, which stops before
    reaching `brief_path` (5 lines after `id:`, not 2) -- the command as written never
    demonstrated what it claimed. Fixed to `-A5`, matching `## Auto Run Result`'s own
    already-correct re-run.
  - `medium` `patch` `campaign.re_scope_gate_2.note`'s "production-shape callers"
    evidence cited 8/10 adapters into slice 2 without noting 2 of them
    (`build_native`/`build_docker`) are this same file's own declared PERMANENTLY OUT
    OF CUTOVER SCOPE (Story 12.6). Added a parenthetical: 6 of 8 are genuinely
    cutover-relevant. `decision` field and overall verdict unchanged -- precision
    correction to supporting evidence only.
  - `low` `patch` `## Tasks & Acceptance`'s `pre_conditions` shorthand showed flat
    scalars (`slice1_equivalence_closure: open`); the real YAML has each key as a
    nested `{status, note}` object. Corrected the shorthand to match.
  - `low` `defer` `scripts/cfe_rebuild_guard_check.py` clause (d) enforces only
    `campaign.re_scope_gate.pre_conditions`, never `re_scope_gate_2.pre_conditions` --
    a slice-3/4 `brief_path` write would pass the guard-check clean today even with
    both new pre-conditions still `open` (independently confirmed by 3 of 4 review
    layers, one with a full reproduction). Real and reproducible, but this story's own
    Never-boundary explicitly forbids touching that detector's clause logic --
    deferred for a follow-up story to extend clause (d) (or add a clause (e)), same
    posture as Story 6.4's own GATHERED GAPS #5.
  - 10 findings rejected: mostly pre-existing campaign-wide conventions this story
    correctly continued rather than introduced (the "12.3x" framing inherited verbatim
    from Story 6.4's own note; `next_story`'s long-paragraph shape, already present in
    the pre-story baseline; the same facts restated across Tasks & Acceptance/Design
    Notes/Auto Run Result/YAML note, matching Stories 6.4 and 12.7's own pattern;
    `warnings: [oversized]`'s unquoted form, matching the immediately preceding
    story's style) or explicitly out of this story's writable Code Map (OQ4/OQ5
    unowned -- SPEC.md is read-only per this story's own Code Map;
    `failure_catalog_generator.py` restated -- slice-map.md is read-only). The
    `pre_conditions` key-naming-convention finding was also rejected: the "same shape"
    comment refers to the block's 4-field structure (`reached`/`decision`/
    `pre_conditions`/`note`), not the sub-keys' naming, so no contradiction exists.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Recorded CAP-4's second re-scope checkpoint: `campaign.re_scope_gate_2`
(`reached: true`, `decision: "adjust"`) with a full evidence-based cost accounting for
Stories 12.6-12.7, two structured pre-conditions (`slice1_equivalence_closure`,
`slice2_equivalence_closure`, both `status: "open"`) gating slice 3 or slice 4's brief,
slice 5's opportunistic-porting status (on track, no action needed), and an end-cutover
plan update. No slice-3/4 brief was written; `slices[2].brief_path`
(`slice-3-atlas-intelligence`) stays `null`. `slices[2]`/`slices[3]`'s own `next_action`
fields were rewritten to point at the new gate instead of "not yet scheduled";
`campaign.next_story` now reads past Story 12.8. A formal adversarial review pass (Blind
Hunter, Edge Case Hunter, Verification Gap Reviewer, Intent Alignment Auditor, run in
parallel against the diff since baseline) then found and fixed 3 real issues (see Review
Triage Log) and deferred 1 real, boundary-forbidden gap.

**Decision grounding:** slice 2's measured cost (Stories 12.6-12.7, PRs #895/#897) was
independently re-derived from `git show --shortstat` on every non-doc commit, not
transcribed from an earlier draft: 12.6 = 1 substantive commit (`97f25016c7`, 223 changed
lines); 12.7 = 3 substantive commits (`c46ac684af` 24705, `8c35423d58` 290, `f5dbabb85a`
95 changed lines; ~25,313 total) plus one trivial 2-line wip-resume commit
(`6c35e1022d`), excluding the ledger-doc commit (`82798cc360`) from the cost figure the
same way Story 6.4 excluded its own ledger commits. The decision (`adjust`, not `go`) is
grounded in a real, reproduced signal: both compiled slices now carry `equivalence:
stale` (slice 1's `github_updater.py` HEAD-advance gap, Story 12.3; slice 2's 5-script
path-depth divergence, Story 12.7) -- a 100% hit rate across the two compiled slices,
and slice 3 (the next candidate) is 12.3x slice 1's size, which is exactly the scenario
Story 6.4's own note flagged this repeat checkpoint for.

**Files changed:**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  -- only file touched: `campaign.re_scope_gate_2` added; `campaign.next_story`,
  `slices[2].next_action` (slice-3), and `slices[3].next_action` (slice-4) updated to stay
  consistent with the new gate.
- This spec file (`Tasks & Acceptance` checkboxes, `Review Triage Log`, `deferred`
  frontmatter, this `Auto Run Result` section).

**Verification performed:**
- `python3 -c "import yaml; yaml.safe_load(open('campaign-state.yaml'))"` -- parses clean;
  additionally spot-checked `campaign.re_scope_gate_2.decision`, `.pre_conditions` keys, and
  `slices[2].brief_path` via a second `yaml.safe_load` + attribute-access script.
- `pixi run -e local-recipes cfe-rebuild-guard-check` -- exit 0: "clean -- no slice has a
  stale equivalence result, no briefed slice is behind a landed retro, no legacy caller
  survives a declared endgame, and no order>=2 slice's brief bypasses the re-scope gate."
  (Clause (a) does not fire because both stale slices are still `status: "compiled"`, not
  `parallel`/`audited`/`cut-over` -- confirmed against the detector's own
  `EQUIVALENCE_GATED_STATUSES` set, same reasoning already recorded in slice 1's and
  slice 2's own `equivalence` comments.)
- `git status --porcelain` -- only `campaign-state.yaml` and this spec file changed.
- `git diff --name-only` grepped against the CFE-surface globs
  (`.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  `.claude/tools/conda_forge_server.py`, `scripts/cfe_rebuild_guard_check.py`) -- zero
  matches; CFE surface confirmed untouched.
- `grep -A5 'id: "slice-3-atlas-intelligence"' campaign-state.yaml` -- `brief_path: null`
  confirmed unchanged.
- Every commit-diff-line figure cited in `re_scope_gate_2.note` independently re-run via
  `git show --shortstat` on `97f25016c7`, `c46ac684af`, `8c35423d58`, `f5dbabb85a`,
  `6c35e1022d`.
- The `_http.py`/`_cfy_template.py`/`_paths.py` porting claims in the "SLICE 5" section
  independently re-verified by listing the actual compiled-package script directories
  (`.claude/skills/cfe-recipe-generation/1.0.0/.../scripts/`,
  `.claude/skills/cfe-recipe-lifecycle/1.0.0/.../scripts/`) and grepping
  `recipe-generator.py` for its `_http` import, rather than trusted from the spec's own
  Design Notes paragraph alone.
- Mason's live `_CFE_SCRIPTS` table (`src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py`)
  re-read directly: still exactly 10 adapter entries, 2 into slice 1 and 8 into slice 2 --
  unchanged from slice-map.md's Mason Caller Inventory, confirming the end-cutover plan's
  caller-flip mechanics needed no update.
- **Post-review pass:** all 4 `## Verification` commands (with the corrected `-A5` grep)
  re-run after the 3 patches landed -- all pass: YAML parses clean
  (`campaign.re_scope_gate_2.decision == "adjust"`), `cfe-rebuild-guard-check` exits
  0/clean, `git status --porcelain` still shows only the same two files, and the
  corrected grep now actually reaches and confirms `brief_path: null`.

**Review findings breakdown:** 4 review layers (Blind Hunter, Edge Case Hunter,
Verification Gap Reviewer, Intent Alignment Auditor) run in parallel against the diff
since `baseline_revision`. 3 `patch` (1 medium, 2 low) -- all applied and re-verified; 1
`defer` (low) -- added to frontmatter `deferred`; 10 `reject` -- pre-existing campaign
conventions this story correctly continued, or explicitly out of this story's writable
Code Map. Full breakdown: `## Review Triage Log` above.

**Follow-up review recommendation:** `true`. Score from this pass's `patch` findings
only (never defer/reject): 1 medium + 2 low -> `3*1 + 1*2 = 5` >= 5, so `true` on the
score threshold alone (no `high` finding this pass).

**Residual risks / left incomplete:**
1. This story recorded the checkpoint but did **not** close either pre-condition -- both
   `slice1_equivalence_closure` and `slice2_equivalence_closure` in `re_scope_gate_2`
   remain `status: "open"`. Closing them (the `github_updater.py` HEAD-advance port for
   slice 1, the 5-script depth-independent repo-root port for slice 2) is real, bounded
   follow-up work with no story minted for it yet -- by this story's own explicit Code Map
   and Never-boundary ("never write a second slice's brief... regardless of the decision
   recorded"), decomposing that follow-up work into a story is deliberately out of scope
   here, matching Epic 6/12's decompose-no-further discipline.
2. Neither pre-condition is machine-enforced -- now formally recorded in frontmatter
   `deferred` (see entry above) rather than only disclosed in prose: `cfe_rebuild_guard_
   check.py` clause (d) reads only `campaign.re_scope_gate.pre_conditions` (the first
   gate), never `re_scope_gate_2.pre_conditions` -- a future session could still write
   slice 3 or 4's `brief_path` without the detector objecting. This story's own
   Never-boundary explicitly forbids touching that detector's clause logic to close it.
3. SPEC.md's Open Questions 4 and 5 remain genuinely open (restated, not resolved, in
   `re_scope_gate_2.note`) -- unchanged risk carried forward from Story 12.7, not
   introduced by this story.
4. Landing (git commit beyond this session's working tree, the ledger flip for key
   `12-8-the-slice-2-re-scope-checkpoint`, and any PR/label work) is the dispatcher's,
   per this campaign's own established convention -- no `recipes/**` or `pixi.toml`
   change occurred, so no env-sync is needed.
