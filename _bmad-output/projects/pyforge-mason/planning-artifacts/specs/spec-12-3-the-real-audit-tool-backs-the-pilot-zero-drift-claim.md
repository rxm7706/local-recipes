---
title: The real audit tool backs the pilot zero-drift claim
type: chore
created: '2026-08-27'
status: done
updated: '2026-08-28'
baseline_revision: 440a9183981350421605dd17b61b8a4fc9d4312d
final_revision: null
review_loop_iteration: 0
followup_review_recommended: true
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

## Tasks & Acceptance

**Execution:**
- [x] `skf-setup` run in this worktree (`--headless`) — DONE. Wrote
  `_bmad/_memory/forger-sidecar/forge-tier.yaml` (tier `Quick` — no ast-grep/qmd/ccc detected)
  and `preferences.yaml`. Gitignored, per-worktree state, as the Code Map predicted.
- [x] `skf-audit-skill` invoked with `skill_name: cfe-recipe-generation` — encountered a SECOND,
  previously-undocumented gap beyond the one this story was scoped to close: no
  `provenance-map.json` for this skill existed anywhere in this worktree (the original, from
  Stories 6.1-6.3, was written only under the now-deleted ephemeral agent worktree
  `.claude/worktrees/agent-a00a0f6206d94a499` per this package's own
  `metadata.json.source_root`, and never persisted anywhere durable). Rather than run full
  degraded mode (would scan all ~68 conda-forge-expert scripts, drowning this slice's 12-file
  scope in false "added" noise) or halt the story on a blocker outside its own Boundaries, a
  minimal `provenance-map.json` was reconstructed with `file_entries[]` only (real, current
  sha256 hashes of the 12 tracked files, from `metadata.json`'s own already-tracked
  `source_file` pointers) — `entries[]` (per-export AST baseline) deliberately left empty, since
  none survived and inventing one would fabricate findings. This let the workflow's own real
  deterministic helper scripts (`skf-load-provenance.py`, `skf-structural-diff.py`,
  `skf-compare-file-hashes.py`, `skf-severity-classify.py`, `skf-detect-docs.py`) run end-to-end
  — DONE, all 7 stages completed (init → re-index → structural-diff → semantic-diff-skipped →
  severity-classify → doc-drift → report → health-check).
- [x] Real verdict recorded in `campaign-state.yaml` — DONE. `equivalence: "green" → "stale"`
  (flipped honestly, not suppressed); the giant clause-5 inline comment rewritten to cite the
  real report and describe the reconstruction; `next_action` rewritten with the concrete
  remaining work (re-port `github_updater.py`'s HEAD-advance feature).
- [x] `pixi run -e local-recipes cfe-rebuild-guard-check` — exit 0, clean (confirmed
  `EQUIVALENCE_GATED_STATUSES = {"parallel", "audited", "cut-over"}` does not include
  `"compiled"`, so flipping `equivalence` off `"green"` does not trip clause (a) while status
  stays `"compiled"` — verified by reading the detector source, then re-running it).
- [x] `pixi run --frozen -e pyforge-mason pyforge-mason-test` — 1578 passed, 3 deselected
  (unaffected; this story touched no `pyforge.mason` code).
- [x] No edits to `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  `.claude/tools/conda_forge_server.py`, `epics.md`, or `sprint-status-ledger.yaml` — confirmed
  via `git status` before and after.

**Acceptance Criteria:**
- Given slice 1's `equivalence: green` rested partly on a manual sha256 substitute, when
  `skf-setup` and `skf-audit-skill` are run in this worktree, then both complete (`skf-setup`
  fully clean; `skf-audit-skill` completed end-to-end through its own real deterministic
  scripts, with the provenance-map gap documented rather than papered over) — met.
- Given the real verdict, when it is recorded in `campaign-state.yaml`, then the substitute
  language is replaced and the drift found (SIGNIFICANT: 2 MEDIUM + 1 LOW, all in
  `scripts/github_updater.py` — missing the CFE v8.84.0 HEAD-advance feature) is not hidden —
  met; `equivalence` flipped off `"green"` to `"stale"`, per the I/O matrix's own explicitly
  allowed outcome.

## Verification

**Commands:**
- `uv run _bmad/skf/shared/scripts/skf-forge-tier-rw.py write-tools ...` /
  `init-prefs ...` — forge-tier.yaml + preferences.yaml written, confirmed present.
- `uv run _bmad/skf/shared/scripts/skf-load-provenance.py normalize forge-data/cfe-recipe-generation/1.0.0/provenance-map.json`
  — bounded_scan_files = the 12 tracked files; `baseline_ref: "local"` (confirms §5b's
  upstream-drift check short-circuits cleanly).
- `uv run _bmad/skf/shared/scripts/skf-structural-diff.py ...` — summary
  `{"added": 70, "removed": 0, "changed": 0, "moved": 0, "unchanged": 0}` (the 70 is an artifact
  of the empty `entries[]` baseline, documented and excluded from severity scoring).
- `uv run _bmad/skf/shared/scripts/skf-compare-file-hashes.py compare ...` — the decisive check:
  `{"added": 106, "removed": 0, "changed": 1, "unchanged": 11}`. The 1 changed file is
  `scripts/github_updater.py` (311 compiled vs. 469 live lines); the 106 added are Slices 2-5's
  own files, out of this slice's scope, not drift.
- `echo '[...]' | uv run _bmad/skf/shared/scripts/skf-severity-classify.py -` — real verdict:
  `drift_score: "SIGNIFICANT"`, `by_severity: {CRITICAL: 0, HIGH: 0, MEDIUM: 2, LOW: 1}`.
- `pixi run -e local-recipes cfe-rebuild-guard-check` — exit 0, clean, both before and after the
  `campaign-state.yaml` edit.
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — 1578 passed, 3 deselected.
- `pixi run -e local-recipes bmad-drift-check` — the one `fail` (`pin-missing`) and the
  `surface-changed` warnings are pre-existing on the baseline commit `440a918398` (confirmed via
  `git stash` round-trip) — unrelated to this story, not introduced by it.

**Residual risks / left incomplete:**
- `scripts/github_updater.py`'s compiled copy is now confirmed BEHIND the live source (CFE
  v8.84.0's HEAD-advance feature is missing) — this story's job was to surface that honestly,
  not to fix it. Re-porting it (and re-running the equivalence harness) is named as the concrete
  next step in `campaign-state.yaml`'s `next_action`, but is explicitly out of this story's own
  Boundaries (which say nothing about closing the drift, only recording it).
- The reconstructed `provenance-map.json` is real (current, correct hashes; no fabricated
  per-export data) but weaker than a genuine create-skill-time provenance map — it has no
  cross-run per-export baseline, so the export-level structural diff (§1) could not produce a
  meaningful "added since compile" signal and was excluded from severity scoring. The decisive
  Script/Asset Drift check (file-hash comparison) does not depend on that gap.
- Two real, previously-undocumented gaps in the SKF tooling itself were found and recorded as
  local health-check findings under `forge-data/improvement-queue/` (not live-submitted as
  GitHub issues — no human was present to clear the review gate `skf-audit-skill`'s own
  health-check step requires before live submission): (1) degraded mode has no
  headless-consumable way to supply the current source path; (2) `skf-detect-docs.py
  compare-hashes` crashes on a non-URL `doc_sources` entry instead of failing gracefully as its
  own step's contract promises. A third, `bug`-severity finding (same crash) is also queued.
- `followup_review_recommended: true` — the provenance-map reconstruction (Boundaries didn't
  anticipate this second gap) is a genuine judgment call worth an independent second look, even
  though `cfe-rebuild-guard-check` and the full mason test suite both stay green.

## Auto Run Result

Status: done

**Summary:** Closed the real audit-tool gap this story targeted (`skf-setup` had never run in
this worktree, so `skf-audit-skill` halted at exit 3 `forge-tier-missing`) — but along the way
found a second, deeper gap the story's own Problem statement did not anticipate: the compiled
`cfe-recipe-generation` package's original `provenance-map.json` was never persisted outside the
ephemeral agent worktree Stories 6.1-6.3 ran in, so even with `forge-tier.yaml` present,
`skf-audit-skill`'s documented degraded-mode path (the only route available with no provenance
map) has no headless-consumable way to supply a bounded source scope. Rather than either (a)
halting the story on a blocker its own Boundaries don't name, or (b) running an unbounded
degraded-mode scan that would drown this slice's real signal in ~68-script noise from unrelated
slices, reconstructed a minimal, honest `file_entries[]`-only provenance map from already-tracked
metadata (real current sha256 hashes, real `source_file` mappings from `metadata.json`) and drove
`skf-audit-skill`'s own real deterministic helper scripts through all 7 stages end-to-end. The
real verdict: SIGNIFICANT drift (2 MEDIUM + 1 LOW), entirely in `scripts/github_updater.py`,
which is missing the CFE v8.84.0 HEAD-advance feature — exactly the divergence
`campaign-state.yaml`'s own prior `next_action` had already predicted qualitatively, now
quantified and tool-confirmed. Recorded this honestly: `equivalence` flipped from `"green"` to
`"stale"`, the clause-5 substitute language fully replaced, and `next_action` rewritten with the
concrete remaining work (re-port `github_updater.py`). Did not fix the drift itself — out of this
story's scope — and did not touch the CFE surface, `epics.md`, or `sprint-status-ledger.yaml`.

**Files changed:**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — slice-1 `equivalence: "green" → "stale"`; clause-5 comment and `next_action` rewritten with
  the real verdict.
- `forge-data/cfe-recipe-generation/1.0.0/` (new, untracked by `.gitignore` — evidence cited by
  the campaign-state.yaml edit above, intended to be committed alongside it so the citation
  resolves for future readers) — `provenance-map.json` (reconstructed, `schema_note` field
  explains why), `extraction-snapshot.json`, `structural-diff-result.json`,
  `file-hash-diff-result.json`, `drift-report-20260828-073026.md`, `audit-skill-result-*.json` (+
  `-latest.json`).
- `forge-data/improvement-queue/` (new, untracked, NOT intended for commit — local self-improvement
  queue, per `skf-audit-skill`'s own health-check step, for a human to review later) — 3 findings
  against the SKF tooling itself (2 `gap`, 1 `bug`).
- `_bmad/_memory/forger-sidecar/` (new, gitignored per `.gitignore:805`, per-worktree state) —
  `forge-tier.yaml`, `preferences.yaml`.

**Review findings breakdown:** No separate adversarial review pass was run (this was a direct
single-agent implementation, not a `bmad-build-auto` dev+review cycle). Self-verification only —
see Verification above. `followup_review_recommended: true` given the provenance-map
reconstruction judgment call.

**Follow-up review recommendation:** `true`. The one substantive judgment call in this story —
reconstructing a `file_entries[]`-only provenance map rather than running full degraded mode or
halting — is defensible (documented in full, no fabricated per-export data, the decisive
file-hash check is unaffected by the gap) but was not anticipated by the story's own Boundaries
and deserves an independent look before being treated as the template for slice 2's audit
(Story 12.7 names "the REAL skf-audit-skill reports zero drift (no manual substitute this
time)" — worth confirming slice 2's compile preserves its provenance map so this reconstruction
pattern does not need to repeat).
