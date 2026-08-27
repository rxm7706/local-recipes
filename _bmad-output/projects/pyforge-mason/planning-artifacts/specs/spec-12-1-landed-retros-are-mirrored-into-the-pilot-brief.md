---
title: Landed retros are mirrored into the pilot brief
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
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-2-the-divergence-and-endgame-guard-proven-red-first.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-3-pilot-slice-recipe-generation-built-and-parallel-validated.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `pixi run -e local-recipes cfe-rebuild-guard-check` reports a live
`unmirrored-retro` finding today: 4 commits in `806cb63046..HEAD` qualify as landed CFE
Rule-2 retros (CFE-surface touch + `CHANGELOG.md` A/M in the same commit — mechanical, never
subject-pattern-based), newest `565ef7d194`, and slice 1's `brief_mirrored_through` is still
`null`. Nothing has re-opened this duty since Story 6.2 shipped the detector.

**Approach:** Read each of the 4 qualifying commits' real diff (not just its subject or
CHANGELOG one-liner), mirror the actual CFE-surface delta into slice 1's brief, then set
`brief_mirrored_through` to the newest qualifying SHA and confirm the detector goes clean.
The detector, not this story, re-opens the duty the next time a retro lands unmirrored.

## Acceptance Criteria

- **Given** the guard's live clause-(b) finding (4 qualifying CFE Rule-2 retros in
  `806cb63046..HEAD`, newest `565ef7d194`, none mirrored; `brief_mirrored_through: null`)
  **Then** each landed retro's CFE-surface delta is mirrored into slice 1's brief,
  `brief_mirrored_through` records the newest mirrored SHA, and
  `pixi run -e local-recipes cfe-rebuild-guard-check` exits clean — the detector, not this
  story, re-opens the duty on the next unmirrored retro.

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-1-landed-retros-are-mirrored-into-the-pilot-brief`.
- Mirror all 4 qualifying commits' actual CFE-surface delta (read each via `git show <sha>`,
  not just its one-line subject) into slice 1's brief content, then set
  `campaign-state.yaml`'s `slices[0].brief_mirrored_through` to the newest SHA
  (`565ef7d194b1ccd740951250aa6535b65bdfc7b6`).
- Re-run `pixi run -e local-recipes cfe-rebuild-guard-check` and confirm exit 0 before closing.

**Block If:** The brief target
(`_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data/cfe-recipe-generation/skill-brief.yaml`,
per `campaign-state.yaml`'s `brief_path`) cannot be located or reconstructed in this
worktree — HALT and report rather than fabricating brief content Story 6.3 never actually
authored here.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) — mason consults CFE, never edits it
  (mason-cfe-surface-check gate). Reading each commit's diff against that tree is fine;
  editing anything under it is not.
- Never gate which commits count as "real" retros on their subject line — the detector's
  clause (b) is mechanical (CFE-surface touch + CHANGELOG.md touch), and this story's
  judgment about what to actually mirror must come from each commit's real diff.
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean run | Brief mirrored, `brief_mirrored_through` set to `565ef7d194b1ccd740951250aa6535b65bdfc7b6` | `cfe-rebuild-guard-check` exits 0 | — |
| Brief target missing | Tier-3 `forge-data/cfe-recipe-generation/` absent in this worktree | Halt, name the physical path checked | Never fabricate a brief from scratch |
| A 5th retro lands mid-story | New qualifying commit lands after work starts | Re-check `--json` output's newest SHA before closing; mirror it too | A stale `brief_mirrored_through` re-opens on the next detector run |
| Commit is a merge / feature commit, not an obvious "retro" (e.g. `621ab29c`, `2d276ecb`) | Mechanically qualifies per clause (b) | Still mirror its actual CFE-surface delta honestly, even if the note is short | Never silently skip a mechanically-qualifying commit |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — slice `slice-1-recipe-generation`'s `brief_mirrored_through: null` (line 293) → set to
  `565ef7d194b1ccd740951250aa6535b65bdfc7b6` once mirrored.
- Slice 1's brief target,
  `_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data/cfe-recipe-generation/skill-brief.yaml`
  (campaign-state.yaml line 292) — CONFIRMED ABSENT in this worktree: `forge-data/` here
  contains only `cf-atlas-legacy/` and `.gitkeep`, no `cfe-recipe-generation/` subdirectory.
  This is gitignored Tier-3, per-worktree state (the same class of gap as GATHERED GAPS #1's
  `forge-tier.yaml`) — locating or reconstructing it is this story's first real task, not an
  assumed-solved precondition.
- The 4 qualifying commits to mirror, newest first: `565ef7d194b1ccd740951250aa6535b65bdfc7b6`
  (merge PR #676, 2026-08-23, steward 15-2 one-command suite advance),
  `621ab29c72a22b2b900144be20b74823dffe36cc` (2026-08-23, the underlying steward 15-2 feat
  commit), `2d276ecbf4bce613c369507ae74dc283de016b2c` (merge PR #606, 2026-08-21, bmad-method
  v6.11.0 update), `6ace3fd6ab204324dffc2ec4c5e1133749d4e6c5` (2026-08-21, "cfe: v8.83.0 —
  Rule-2 retro for the bmad-suite refresh"). `git show <sha>` each one for its real
  CFE-surface delta rather than restating the subject line.
- `scripts/cfe_rebuild_guard_check.py` — read-only; defines clause (b)'s exact detection
  mechanics (`retro_commits_since()`, `DEFAULT_SINCE = "806cb630469688d596cac00a53573f01f39386e2"`)
  — ground truth for what "qualifying" means. Do not edit its logic (that is Story 12.4's
  clause-(d) addition, not this story's).
- `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/metadata.json` — the
  compiled package's own record of which source scripts it ported and why (a distinct,
  non-CFE-surface skill tree); a useful cross-check for what the brief should already
  reflect.
