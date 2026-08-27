---
title: The re-scope gate is machine-enforced
type: feature
created: '2026-08-27'
status: ready
updated: '2026-08-27'
baseline_revision: cc8b3b2b1c09d6e56a5aebf752e25f507c846571
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-2-the-divergence-and-endgame-guard-proven-red-first.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-4-the-re-scope-gate-measured-cost-recorded-decision.md
warnings: []
deferred: []
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
