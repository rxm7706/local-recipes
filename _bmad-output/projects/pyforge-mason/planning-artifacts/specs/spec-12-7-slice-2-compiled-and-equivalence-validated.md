---
title: Slice 2 compiled and equivalence-validated
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
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-3-pilot-slice-recipe-generation-built-and-parallel-validated.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Slice 2's brief exists (Story 12.6) but nothing has compiled or validated it
yet. CAP-2's bar — compiled replacement, unmodified regression tests, zero-divergence
equivalence harness, real zero-drift audit, no caller flip, retro mirrored — has to be met
the same way Story 6.3 met it for slice 1, this time at ~7.3x the size and without a manual
audit substitute (Story 12.3 already closed that tooling gap).

**Approach:** `skf-create-skill` compiles the replacement from slice 2's brief; slice 2's
existing regression tests run unmodified; the equivalence harness runs against the shared
corpus; the REAL `skf-audit-skill` runs (no substitute); the old path stays authoritative with
no caller flip; and the story closes with its Rule-2 retro mirrored into the slice briefs so
clause (b) is green immediately, without needing a future 12.1-style cleanup for slice 2.

## Acceptance Criteria

- **Given** the brief **Then** CAP-2's bar holds for slice 2: compiled replacement; the
  slice's existing regression tests pass UNMODIFIED; the equivalence harness reports zero
  divergence on the shared corpus; the REAL skf-audit-skill reports zero drift (no manual
  substitute this time); the old path stays authoritative and no caller flips (flip and
  retirement remain campaign-end, CAP-3 clause (c)); and the story closes with its Rule-2
  retro mirrored into the slice briefs (clause (b) green).

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-7-slice-2-compiled-and-equivalence-validated`.
- Block until Story 12.6's brief exists (`campaign-state.yaml` slice 2 `status: briefed`,
  `brief_path` set) — this story's sole Dep.
- Follow Story 6.3's own pattern for slice 1 (compile → unmodified regression pass →
  equivalence-harness pass → real audit → honest campaign-state.yaml update), scaled to slice
  2's 22 scripts/17 wrappers/19 MCP tools (~7.3x slice 1's size per campaign-state.yaml's
  re-scope note) — budget for at least one BLOCKED-and-retry cycle, per slice 1's own
  cross-slice-import precedent.
- The REAL `skf-audit-skill` must run this time — this depends on Story 12.3 having already
  closed the `forge-tier.yaml` gap; if this worktree lacks that state (e.g. a fresh worktree),
  re-run `skf-setup` here rather than reverting to a substitute.
- Close with a Rule-2 CFE retro whose delta is mirrored into BOTH slice briefs (slice 1's and
  slice 2's) in the same pass this story lands — this is what keeps clause (b) green going
  forward without a future 12.1-style follow-up for slice 2.

**Block If:** The equivalence harness or the real audit surfaces genuine drift/divergence
that cannot be resolved by porting a legitimate shared dependency (slice 1's own precedent) —
halt and report rather than fabricating a green result, mirroring Story 6.3's own honest
BLOCKED-then-retry precedent.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) as part of *compiling the
  replacement* — `skf-create-skill` writes to a new, sibling skill directory (e.g. alongside
  `.claude/skills/cfe-recipe-generation/`), never back into the live CFE tree; mason consults
  CFE, never edits it (mason-cfe-surface-check gate). Per SPEC.md's own **Open Question 5**
  ("does a mid-campaign Rule-2 retro edit the legacy SKILL.md, the successor slice's skill, or
  both during the overlap window? — the first slice's retro sets the precedent"), where this
  story's closing retro actually lands is genuinely undecided by this spec; if it requires an
  edit under `.claude/skills/conda-forge-expert/`, that edit is CFE's own Rule-2-governed
  process (invoking the `conda-forge-expert` skill per Rule 1), and is deliberately **not**
  enumerated as a Code Map target here.
- Never flip any Mason caller from legacy to the replacement — CAP-3's caller flip is
  campaign-end only; this story's compiled replacement runs in parallel, unused by any real
  caller yet.
- Never weaken or delete slice 2's existing tests to make them pass against the replacement.
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean compile, all gates pass | Slice 2's brief | `status: compiled`, `equivalence: green`, real audit clean, retro mirrored | — |
| A cross-slice import surfaces mid-compile (slice-1 precedent) | e.g. an undocumented Slice-5/Slice-3 import | Document and resolve (port a sanctioned dependency, same shape as `_cfy_template.py`/`github_version_checker.py`) | BLOCKED-then-retry is an acceptable, budgeted outcome — never silently papered over |
| Real audit finds drift | skf-audit-skill reports non-zero drift | HALT / reopen; do not force `equivalence: green` | Matches Story 12.3's "honestly reopens" discipline |
| No caller flip attempted | — | Verified: no `_CFE_SCRIPTS` adapter changed `resolves_to` | A test/verification step, not just a promise |
| Retro not mirrored by close | — | Story is not done — clause (b) must be green, not left for a follow-up | Avoids repeating Story 12.1's own gap for slice 2 |

</intent-contract>

## Code Map

- `_bmad/skf/skf-create-skill/` — compiles the brief into a replacement skill package
  (modeled on `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/`'s existing
  shape: SKILL.md, `references/`, `scripts/`, `metadata.json`).
- `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/metadata.json` —
  read-only precedent for the compiled-package metadata shape (scripts/assets inventory,
  `source_file` pointers, `stats`); slice 2's compiled package follows the same shape under
  its own sibling directory.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — slice 2 entry: `status` → `compiled`, `equivalence` → `green` (or an honest non-green),
  `brief_mirrored_through` set alongside slice 1's own field once the closing retro lands.
- `_bmad/skf/skf-setup/`, `_bmad/skf/skf-audit-skill/` — same invocation pattern as Story
  12.3, already unblocked if 12.3 landed first.
- `scripts/cfe_rebuild_guard_check.py` — read-only; re-run
  (`pixi run -e local-recipes cfe-rebuild-guard-check`) as this story's own closing
  verification, same as every prior slice-1 story.
