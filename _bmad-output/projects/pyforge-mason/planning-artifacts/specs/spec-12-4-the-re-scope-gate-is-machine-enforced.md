---
title: The re-scope gate is machine-enforced
type: feature
created: '2026-08-27'
status: done
updated: '2026-08-28'
baseline_revision: 0d34c27d794c09a2b7f8c3508b02d990740f6a16
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-2-the-divergence-and-endgame-guard-proven-red-first.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-4-the-re-scope-gate-measured-cost-recorded-decision.md
warnings: []
deferred:
  - summary: >-
      spec-12-5's own Code Map suggests a top-level campaign-state.yaml field for the
      ownership decision, but Story 12.4 landed a nested field under
      campaign.re_scope_gate.pre_conditions instead, and the spec's own Block-If
      "flag for coordination" step wasn't exercised as a written artifact.
    evidence: |-
      Confirmed by reading spec-12-5-the-ownership-decision-is-recorded.md's Code Map
      directly. Mitigated in practice: campaign-state.yaml's own d_ownership_decision
      note already instructs Story 12.5 to "populate this entry -- do not invent a
      second key" -- but spec-12-5.md itself was not updated to match.
    location: >-
      _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-12-5-the-ownership-decision-is-recorded.md
    severity: medium
  - summary: >-
      Clause (d) checks a self-reported campaign.re_scope_gate.pre_conditions.<key>.status
      field rather than independently verified state, unlike clauses (a)-(c) which each
      derive their verdict from something other than a hand-set flag.
    evidence: |-
      Confirmed by reading scan()'s clauses (a) (computed equivalence field), (b) (real
      git history via retro_commits_since), and (c) (campaign.callers entries) against
      clause (d)'s status-string membership check. The intent-contract's own Approach and
      AC text explicitly specify a recording-based check ("campaign-state.yaml does not
      record the four pre-conditions closed"), so this is a design observation the intent
      itself authorized, not a defect of this diff.
    location: >-
      scripts/cfe_rebuild_guard_check.py (clause (d), scan())
    severity: medium
  - summary: >-
      An explicit slice `id: null` (key present, value None) falls through
      `sl.get("id", "<unknown-slice>")`'s default, since the default only applies when
      the key is absent -- a finding would render the literal id value instead of the
      intended placeholder.
    evidence: |-
      Confirmed via grep that this exact sl.get("id", "<unknown-slice>") pattern is
      shared verbatim by clauses (a) and (b), predating this story -- not introduced by
      clause (d)'s new code, which matches the file's existing style per this story's
      own Boundaries.
    location: "scripts/cfe_rebuild_guard_check.py:322"
    severity: low
  - summary: >-
      Pre-condition `status` matching (RE_SCOPE_GATE_SATISFIED_STATUSES) is
      case/whitespace-sensitive -- e.g. "Closed" would not satisfy the gate.
    evidence: |-
      Confirmed via grep that clause (a)'s EQUIVALENCE_GATED_STATUSES membership check
      uses the same exact-string frozenset pattern with no case normalization anywhere
      in the file -- clause (d) matches established convention rather than introducing
      a new gap.
    location: "scripts/cfe_rebuild_guard_check.py:178,325-327"
    severity: low
---

<intent-contract>

## Intent

**Problem:** `campaign.re_scope_gate` is honored by session/human discipline alone — nothing
in code reads it. Grepping every `.py` under `scripts/`, `_bmad/skf/`, `.claude/skills/` for
`re_scope_gate` returns zero hits outside prose docs (campaign-state.yaml's own GATHERED GAPS
#5). Nothing today stops a future session from writing slice 2's (or slice 3's) brief before
the gate's pre-conditions are actually met.

**Approach:** Add a fourth clause to `scripts/cfe_rebuild_guard_check.py`: a `brief_path` set
on any slice of order ≥ 2 while `campaign-state.yaml` does not record the four named
pre-conditions closed (or explicitly waived by a human) is a finding — proven red by a
fixture before it lands, matching Story 6.2's own discipline for clauses (a)-(c).

## Acceptance Criteria

- **Given** the gate is honored by session discipline alone (nothing reads `re_scope_gate`)
  **Then** `scripts/cfe_rebuild_guard_check.py` gains a clause (d): a `brief_path` set on any
  slice of order ≥ 2 while campaign-state.yaml does not record the four pre-conditions closed
  (or explicitly waived by a human) is a finding — proven red by a fixture before it lands,
  matching Story 6.2's discipline.

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-4-the-re-scope-gate-is-machine-enforced`.
- Add clause (d) inside `scripts/cfe_rebuild_guard_check.py`'s `scan()`, matching the file's
  existing style exactly (a `findings.append({...})` dict with `kind`/`ref`/`refs`/`detail`/
  `remedy`) — not a separate script.
- Add a structured, machine-checkable representation of the four named pre-conditions ((a)
  CI enforcement, (b) skf-setup run, (c) cross-slice re-derivation, (d) the ownership
  decision — see Stories 12.2/12.3/12.5) to `campaign-state.yaml`, so clause (d) can check
  real fields rather than string-matching `re_scope_gate.note`'s free prose — the exact
  anti-pattern the existing `decision` field was added to avoid (Story 6.4's own Review
  Triage Log).
- One red-proving fixture for the new clause, in `tests/scripts/test_cfe_rebuild_guard_check.py`
  (real tmp-git-repo + fabricated campaign-state.yaml, matching the (a)/(b)/(c) precedent).

**Block If:** Closing this story would require inventing new campaign-state.yaml top-level
keys that Stories 12.2/12.3/12.5 are themselves expected to produce — sequence the structured
pre-condition fields to read whatever those stories actually add, rather than guessing their
shape unilaterally; flag for coordination if their shape is not yet decided when this story
starts.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) — mason consults CFE, never edits it
  (mason-cfe-surface-check gate).
- Never touch clauses (a)/(b)/(c)'s existing logic or the `DEFAULT_SINCE` constant — this
  story is additive only.
- Never gate clause (d) on `re_scope_gate.note`'s free-text prose via substring matching —
  the same anti-pattern Story 6.4's own review flagged for the `decision` field.
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No slice of order ≥ 2 has `brief_path` set (today's real state) | Live campaign-state.yaml | Clause (d) clean | — |
| Slice 2's `brief_path` set, pre-conditions not recorded closed | Fixture | Exit 1, a finding naming the slice | — |
| Slice 2's `brief_path` set, pre-conditions recorded closed/waived | Fixture | Clean | — |
| Slice 1 (order 1) has `brief_path` set | Today's real slice 1 | Never a finding — clause (d) only applies to order ≥ 2 | — |

</intent-contract>

## Code Map

- `scripts/cfe_rebuild_guard_check.py` — add clause (d) to `scan()` (a new finding `kind`,
  e.g. `"gate-bypassed"`, plus whatever constant/lookup names "order ≥ 2 slices"); extend
  `main()`'s docstring/help text to list the new clause, matching (a)/(b)/(c)'s existing
  style.
- `tests/scripts/test_cfe_rebuild_guard_check.py` — add fixture(s) proving clause (d) red
  before it lands, per the AC's own "matching Story 6.2's discipline."
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — needs a new structured field set recording the four pre-conditions' closed/waived state
  (e.g. under `campaign.re_scope_gate`, alongside the existing `reached`/`decision`/`note`) for
  clause (d) to read; today only free prose in `note` (lines ~180-203) names them.
- `pixi.toml` — no new task needed; the existing
  `[feature.local-recipes.tasks.cfe-rebuild-guard-check]` (~line 932) already runs the whole
  script, including the new clause.

## Review Triage Log

### 2026-08-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2 (medium 1, low 1)
- defer: 4 (medium 2, low 2)
- reject: 12
- addressed_findings:
  - `[low]` `[patch]` The "Divergence-and-endgame guard hooks" doc-comment block in
    `campaign-state.yaml` didn't mention that `order` is now load-bearing for clause (d)
    (determines whether a slice is in scope). Added a bullet documenting `order` alongside the
    existing `brief_path`/`equivalence`/`callers` bullets.
  - `[medium]` `[patch]` The `pre_conditions` schema comment's `"closed"` definition
    ("holds in any future worktree/session, not per-worktree ephemeral state alone")
    contradicted `b_skf_setup`'s own note, which admits its supporting evidence
    (`forge-tier.yaml`) is gitignored per-worktree state that Story 12.7 will need to
    re-produce. Reworded the schema comment's `"closed"` definition to certify the
    pre-condition's specific cited concern is proven (not that every fact behind it persists
    per-worktree forever), and to allow a `note` to honestly flag a narrower recurring
    operational step without reopening the status. Text-only; no `status` value changed.

Deferred (see frontmatter `deferred`): spec-12-5's own Code Map suggests a different
(top-level) schema shape than the nested `pre_conditions` this story landed, and the spec's
own Block-If "flag for coordination" wasn't visibly exercised as a written artifact (though
`campaign-state.yaml`'s `d_ownership_decision` note already tells Story 12.5 which key to
populate); clause (d) checks a self-reported `status` field rather than independently
verified state the way clauses (a)-(c) do (the intent's own Approach/AC text explicitly
specifies a recording-based check, so this is a design observation, not a defect); an
explicit slice `id: null` falls through `sl.get("id", "<unknown-slice>")`'s default
(pre-existing pattern shared by clauses (a)/(b), not introduced here); pre-condition `status`
matching is case/whitespace-sensitive (pre-existing pattern matching clause (a)'s
`EQUIVALENCE_GATED_STATUSES` check, not unique to clause (d)).

Rejected as noise or as matching established codebase convention (verified against git
history and sibling-clause style, not merely asserted): non-int/float `order` values are
tolerated rather than flagged (matches existing malformed-shape tolerance in clauses
(a)-(c)); `campaign-state.yaml`'s `schema_version` left at 1 (verified via `git log` that no
prior additive change to this file has ever bumped it); a `"waived"` pre-condition isn't
required to carry a substantive `note` (enforcing note content would edge toward gating
clause (d) on note prose, which the spec's own Never-list discourages); no test for
`order == 3` specifically or for multiple simultaneous order>=2 violations (the matrix
doesn't require it and the code paths are trivial); `test_main_exit_0_clean`'s clean-message
text and the human-readable (non-JSON) finding-print path for `gate-bypassed` aren't
separately asserted (cosmetic, and the verification-gap layer traced `main()`'s only real
consumer — CI's blocking step — to depend solely on exit code); `b_skf_setup`'s note doesn't
restate slice 1's separate `equivalence` regression from Story 12.3 (a different field,
already documented in its own place in this file); spec-12-4.md itself lacked
`Auto Run Result`/`Verification` sections at `in-review` (expected at this stage — populated
in Finalize below); no diagnostic for a misspelled `pre_conditions` key (the existing design
already surfaces the exact expected key names via `RE_SCOPE_GATE_PRE_CONDITION_KEYS` in every
finding); the intent-contract's own Block-If text omits naming Story 12.6 for pre-condition
(c) (a pre-existing inaccuracy in read-only frozen intent-contract text, not a diff defect);
I/O matrix rows 1 and 4 are covered only incidentally by pre-existing Story-6.2-era tests
this diff didn't author (the coverage exists and is valid, just inherited).

## Auto Run Result

**Summary:** `scripts/cfe_rebuild_guard_check.py` gains clause (d) `gate-bypassed`: a
`brief_path` set on any slice of order ≥ 2 while `campaign.re_scope_gate.pre_conditions`
does not record all four named pre-conditions `"closed"`/`"waived"` is a finding. The four
pre-conditions ((a) CI enforcement, (b) skf-setup run, (c) cross-slice re-derivation, (d) the
ownership decision) are now a structured, machine-checkable block in `campaign-state.yaml`,
sequenced to what Stories 12.2/12.3 actually landed (both `closed`) and what 12.5/12.6 still
owe (`open`) — closing GATHERED GAPS #5. Proven red-first: 7 of the new tests failed against
the pre-clause-(d) script before it landed. Clause (d) reads only the structured
`pre_conditions` block, never `re_scope_gate.note`'s free prose.

**Files changed:**
- `scripts/cfe_rebuild_guard_check.py` — added clause (d) (`gate-bypassed`) to `scan()`, plus
  `RE_SCOPE_GATED_ORDER_FLOOR`/`RE_SCOPE_GATE_PRE_CONDITION_KEYS`/
  `RE_SCOPE_GATE_SATISFIED_STATUSES` constants; docstring and clean-run message extended.
  Clauses (a)-(c) and `DEFAULT_SINCE` untouched.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — added `campaign.re_scope_gate.pre_conditions` (four structured entries), a doc-block
  mention of `order`'s new role, and a dated addendum closing GATHERED GAPS #5.
- `tests/scripts/test_cfe_rebuild_guard_check.py` — 11 new fixtures covering all four I/O
  matrix rows plus malformed-shape tolerance and a `main()`/JSON integration test.
- `pixi.toml` — updated the `cfe-rebuild-guard-check` task description (three clauses → four);
  no dependency/task-structure change, so `environment.yaml` regen was not required.

**Review findings breakdown:** 2 patch (applied), 4 deferred, 12 rejected. See Review Triage
Log above and frontmatter `deferred` for detail.

**Follow-up review recommendation:** `false`. Patched-finding severity this pass: 1 medium, 1
low, 0 high. Score = 3×1(medium) + 1×1(low) = 4 (< 5 threshold, no high-severity patch).

**Verification performed:**
- Red-first proof: reverted the script only, re-ran the new tests — 7 failed as expected.
- `pixi run -e local-recipes pytest tests/scripts/test_cfe_rebuild_guard_check.py -q` — 39/39
  pass (re-run independently after both review patches; still 39/39).
- `pixi run -e local-recipes cfe-rebuild-guard-check` — exit 0, clean, against the real
  unmodified-in-spirit campaign-state.yaml (re-run independently after patches; still clean).
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — 1578 passed, 3 deselected,
  unaffected.
- `tests/scripts/test_mason_cfe_surface_check.py` — 19/19 pass, sibling detector unaffected.
- `python3 -c "import yaml..."` confirms `campaign-state.yaml` and the spec's own frontmatter
  (including the new `deferred` list) both still parse cleanly.
- `git status --short` confirms only the 5 intended files touched — no edits under the CFE
  surface, `epics.md`, or `sprint-status-ledger.yaml` (all forbidden per the spec's Never
  clauses).
- Matrix Test Audit: all four I/O & Edge-Case Matrix rows independently confirmed covered by
  a passing test (rows 1/4 via pre-existing tests that now also exercise clause (d); rows 2/3
  via new fixtures).

**Residual risks:** the four deferred items above (spec-12-5 schema-shape mismatch pending
coordination; clause (d)'s self-reported-status design vs. clauses (a)-(c)'s independently
verified checks; two pre-existing minor tolerance gaps shared with clauses (a)/(b)) are real
but judged out of this story's scope — tracked in frontmatter `deferred` for whoever picks up
Story 12.5 or a future hardening pass.
