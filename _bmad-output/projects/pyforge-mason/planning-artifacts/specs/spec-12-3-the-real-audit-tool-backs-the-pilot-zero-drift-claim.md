---
title: The real audit tool backs the pilot zero-drift claim
type: chore
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
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-3-pilot-slice-recipe-generation-built-and-parallel-validated.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Slice 1's `equivalence: green` rests partly on a manual sha256 diff standing in
for `skf-audit-skill` (CAP-2's own zero-drift tool), because this worktree has no
`_bmad/_memory/forger-sidecar/forge-tier.yaml` — confirmed: `_bmad/_memory/` does not exist
in this worktree at all (it is gitignored per `.gitignore:805`) — so `skf-audit-skill` halts
deterministically at step 1 §2 with exit 3, `forge-tier-missing`.

**Approach:** Run `skf-setup` once in this worktree to populate the forger-sidecar state,
then run `skf-audit-skill` end-to-end against the compiled
`.claude/skills/cfe-recipe-generation/` package, and record its real verdict in
`campaign-state.yaml`, replacing the substitute language — honestly, even if it surfaces
drift the sha256 comparison could not detect.

## Acceptance Criteria

- **Given** slice 1's `equivalence: green` rests partly on a manual sha256 substitute
  (`forge-tier.yaml` absent in the audit worktree; skf-audit-skill halts at exit 3,
  `forge-tier-missing`) **Then** skf-setup has run in the worktree doing the audit,
  skf-audit-skill completes end-to-end against the compiled
  `.claude/skills/cfe-recipe-generation/` package, and its verdict replaces the substitute in
  campaign-state.yaml — drift, if surfaced, honestly reopens slice 1's record rather than
  being suppressed.

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-3-the-real-audit-tool-backs-the-pilot-zero-drift-claim`.
- Run `skf-setup` in this worktree first — it writes
  `_bmad/_memory/forger-sidecar/forge-tier.yaml` and `preferences.yaml` (gitignored,
  per-worktree state; confirmed neither exists here yet).
- Then invoke `skf-audit-skill` with `skill_name: cfe-recipe-generation` against the compiled
  package at `.claude/skills/cfe-recipe-generation/active` (→ `1.0.0/cfe-recipe-generation/`).
- Whatever the real verdict is, record it honestly in `campaign-state.yaml`'s slice-1
  `equivalence` clause-5 inline note (which today documents the sha256-substitute rationale) —
  replace that language with the real `skf-audit-skill` result, citing its report.

**Block If:** `skf-setup` itself cannot complete for a reason unrelated to
`forge-tier.yaml` (e.g. a genuine tool-detection failure) — halt and report rather than
inventing another substitute.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) — mason consults CFE, never edits it
  (mason-cfe-surface-check gate). The audit tool reads the live skill to diff against it;
  this story never writes to it.
- Never suppress a real drift finding to preserve the existing `equivalence: "green"` label —
  doing so would defeat this story's entire purpose.
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| forge-tier.yaml still absent when audit runs | skf-setup skipped | skf-audit-skill halts exit 3 again | Story is not done until skf-setup actually ran |
| Real audit finds zero drift | Clean compiled package | `campaign-state.yaml` clause-5 note updated to cite the real report; `equivalence` stays `green` | — |
| Real audit finds drift | e.g. a script diverged from its source | `equivalence` may need to flip off `green` — an allowed, expected-possible outcome | Never hidden or glossed over |
| skf-setup fails for an unrelated reason | e.g. a missing tool dependency | Report the real blocker; do not hand-write a forge-tier.yaml | HALT |

</intent-contract>

## Code Map

- `_bmad/_memory/forger-sidecar/forge-tier.yaml`, `preferences.yaml` — confirmed absent in
  this worktree (`_bmad/_memory/` does not exist at all; gitignored per `.gitignore:805`);
  `skf-setup` creates them.
- `_bmad/skf/skf-setup/` — the skill to invoke first; its Invocation Contract's Outputs row
  names exactly `forger-sidecar/forge-tier.yaml`, `forger-sidecar/preferences.yaml`, and
  `{forge_data_folder}/`.
- `_bmad/skf/skf-audit-skill/` — the skill to invoke second, `skill_name: cfe-recipe-generation`;
  its Invocation Contract's Outputs are `drift-report-{timestamp}.md` plus
  `audit-skill-result-{timestamp}.json` (+ `-latest.json`) under `{forge_version}/` — i.e.
  under this compiled package's own directory tree, not under CFE.
- `.claude/skills/cfe-recipe-generation/active` → `1.0.0/cfe-recipe-generation/` — the
  compiled package being audited (a distinct, non-CFE-surface skill tree); its own
  `metadata.json` already records each script's `source_file` pointer for the audit to diff
  against.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — slice-1's `equivalence` field's inline clause-5 comment (around lines 280-291) documents
  the sha256-substitute rationale today; replace with the real `skf-audit-skill` verdict once
  it runs.
