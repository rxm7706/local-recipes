---
title: 'Close the CFE rebuild campaign — cut callers over to slices 1–2 or retire the mirrors'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The endgame is declared (`campaign.endgame_declared: true`, 2026-09-09) over slices
1-2 of the conda-forge-expert rebuild campaign, with `campaign.callers` empty and both slices still
`status: compiled` — the standing per-release byte-re-port obligation has not been closed.

**Approach:** Resolve each of the two compiled slices (`cfe-recipe-generation` and
`cfe-recipe-lifecycle`) one way each: either flip its callers to it (`campaign.callers`
populated, every entry off `resolves_to: "legacy"`, slice `status: cut-over`), or retire the
mirror (slice `status: retired`, the compiled copy DELETED, no dated stub left behind). This story
runs through `conda-forge-expert` per CLAUDE.md Rule 1/2 (it is CFE-surface work).

## Boundaries & Constraints

**Always:**
- `pixi run -e local-recipes cfe-rebuild-guard-check` is clean when done: clause (c) has no legacy
  caller surviving the declared endgame; clause (b) has no briefed slice behind a landed retro.
- `campaign-state.yaml` records the disposition per slice with a dated note.
- The Spec's status flips off `in-progress` via a memlog event.
- The effort ends with a `conda-forge-expert` retro entry in `CHANGELOG.md` (Rule 2).
- Delete `scripts/spec_surface_allowlist.txt:100` (the `scripts/failure_catalog_check.py` entry
  pending mason claiming it via a proper folder-format spec — `spec-machine-checked-recipe-knowledge`
  now IS that spec) and re-stamp its baseline SCOPED:
  `python scripts/spec_surface_check.py --write-baseline --spec pyforge-mason/spec-machine-checked-recipe-knowledge`
  — never a bare `--write-baseline`. Stage the file before stamping.
- **Sequencing:** this story must land BEFORE steward's `fnd:CAP-3` story (steward Epic 44, S-44.6,
  "CFE comes home") moves the CFE cell to `skills/domain/conda-forge-expert/`.

**Never:**
- Never leave a dated stub behind when retiring a mirror — the compiled copy is deleted outright.
- Never bare `--write-baseline` — it reads the working tree and `git ls-files`, and this repo's
  tree is routinely dirty with other stations' work; a bare stamp bakes their edits into mason's
  baseline.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Cut-over path | A slice's callers are flipped to it | `campaign.callers` populated, every entry off `resolves_to: "legacy"`, slice `status: cut-over` | n/a |
| Retire path | A slice's mirror is retired | Slice `status: retired`, compiled copy deleted, no dated stub | n/a |
| Guard check | Either resolution applied to both slices | `cfe-rebuild-guard-check` clean | n/a |
| Allowlist cleanup | `spec_surface_allowlist.txt:100`'s `failure_catalog_check.py` entry | Removed; `spec-surface-check` reports no finding; baseline re-stamped SCOPED to `pyforge-mason/spec-machine-checked-recipe-knowledge` | n/a |

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/**` — the two compiled slices `cfe-recipe-generation` and `cfe-recipe-lifecycle`.
- `.claude/scripts/conda-forge-expert/**` — wrapper redirects, if any caller flips.
- `.claude/tools/conda_forge_server.py` — MCP registrations, if any caller flips.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/{campaign-state.yaml,slice-map.md}`.
- `scripts/spec_surface_allowlist.txt` (line 100 removal).
- `.claude/skills/conda-forge-expert/CHANGELOG.md` (Rule-2 retro entry).

## Tasks & Acceptance

**Execution:**
- `feature` — resolve `cfe-recipe-generation`: cut-over or retire.
- `feature` — resolve `cfe-recipe-lifecycle`: cut-over or retire.
- `feature` — update `campaign-state.yaml` with dated dispositions.
- `feature` — flip the Spec's status off `in-progress` via a memlog event.
- `chore` — delete `scripts/spec_surface_allowlist.txt:100`'s `failure_catalog_check.py` entry; re-stamp scoped baseline.
- `chore` — land a `conda-forge-expert` Rule-2 retro entry in `CHANGELOG.md`.

**Acceptance Criteria:**
- Given the endgame is declared over slices 1-2 with empty `campaign.callers` and both slices still `compiled`, when each compiled slice is resolved (cut-over or retired), then `pixi run -e local-recipes cfe-rebuild-guard-check` is clean, `campaign-state.yaml` records the disposition per slice with a dated note, the Spec's status flips off `in-progress`, and the effort ends with a `conda-forge-expert` retro entry in `CHANGELOG.md`.
- `scripts/spec_surface_allowlist.txt:100` is removed and `spec-surface-check` reports no finding for that path, with the baseline re-stamped scoped to `pyforge-mason/spec-machine-checked-recipe-knowledge`.
- This story lands before steward S-44.6 moves the CFE cell.

## Spec Change Log

## Review Triage Log

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `0e325050cc` (2026-09-12, "feat(mason): Story 15.1 -- retire both CFE rebuild-campaign mirrors"). Ledger row `15-1-close-the-cfe-rebuild-campaign-cut-callers-over-to-slices-1-2-or-retire-the-mirrors: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/SKILL.md`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/context-snippet.md`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/metadata.json`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/references/cfy-template.md`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/references/github-updater.md`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/references/knowledge-gotchas.md`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/references/name-resolver.md`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/references/recipe-generator.md`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/scripts/_cfy_template.py`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/scripts/github_updater.py`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/scripts/github_version_checker.py`, `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/scripts/name_resolver.py` (+72 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `15-1-close-the-cfe-rebuild-campaign-cut-callers-over-to-slices-1-2-or-retire-the-mirrors: done`).
- `## Auto Run Result` reconstructed from git (none survived).
