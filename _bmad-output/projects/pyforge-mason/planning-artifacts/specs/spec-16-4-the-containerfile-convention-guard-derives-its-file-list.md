---
title: 'The Containerfile convention guard derives its file list'
type: 'fix'
created: '2026-09-10'
status: 'in-progress'
baseline_revision: '3aada76d39921c8951520906ec5bc543fd22f77f'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The repo's two enumerations of its Containerfiles disagree. `scripts/pixi_version_registry.py:79-87`
covers all four (`Containerfile`, `src/platform/Containerfile`,
`src/platform/compose/dbgpt/Containerfile`, `src/platform/compose/mcp-host/Containerfile`), while
`tests/packaging/test_containerfile_base_layer_convention.py`'s `CONTAINERFILES` tuple
(currently ~lines 50-52) hard-codes only three, omitting `src/platform/compose/mcp-host/Containerfile`
(spec-mcp-era-isolation slice 1). That file is therefore ungoverned by the registry-pinned-base
and no-`ENV`-credential checks. It is compliant today, but nothing would notice if it stopped
being — the guard's own coverage is silently short of the repo's real surface.

**Approach:** Replace the hard-coded `CONTAINERFILES` tuple with a derivation over the tracked
tree — a glob for `Containerfile*`, restricted to git-tracked files so an untracked scratch
Containerfile cannot red the suite — rather than appending a fourth literal, which would reproduce
the identical defect one file later. Add a test proving the derivation actually finds all four
files (a count assertion, or an explicit membership check for the previously-omitted path), so an
empty or partial glob cannot pass vacuously.

## Boundaries & Constraints

**Always:**
- Replace the hard-coded tuple with a derivation (glob `Containerfile*`, git-tracked only) — not
  a fourth hand-added literal.
- Prove the derivation actually finds the files: a count assertion or explicit membership check,
  so an empty/partial glob cannot pass vacuously — this repo has hit that exact failure mode
  before (an absence assertion indistinguishable from having scanned nothing).
- All four Containerfiles must be swept by both the `FROM` and `ENV` checks after this change.
- A planted unpinned base or `ENV`-declared credential in the fourth file
  (`src/platform/compose/mcp-host/Containerfile`) must red the suite — add or extend the
  synthetic-regression coverage this test file's docstring already requires as mandatory.
- Update `spec-pixi-container-image`'s Constraints line ("until ≥2 Containerfiles diverge") to
  read against four rather than three.
- This story touches no recipe and no CFE surface — Rules 1/2 do not apply.

**Never:**
- Do not simply append `src/platform/compose/mcp-host/Containerfile` as a fourth literal to the
  existing tuple — that reproduces the same "nothing notices when the set changes" defect one file
  later.
- Do not let an untracked scratch/experimental Containerfile affect the derived set — restrict the
  glob to git-tracked files.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Derivation finds all four | Repo tree with the four known Containerfiles, all git-tracked | Derived set includes all four, including `src/platform/compose/mcp-host/Containerfile` | A count/membership test fails if the derivation misses any |
| Empty/partial glob | (regression scenario, guarded by the new test) A change to the derivation logic that would silently under-match | The proving test fails rather than passing vacuously | Test is written to fail loudly, not pass on zero matches |
| Untracked scratch Containerfile | A stray, untracked `Containerfile.local` or similar exists in the working tree | Excluded from the derived set (git-tracked filter) | Suite stays green — the scratch file is not swept |
| Planted violation in the 4th file | Unpinned `FROM` or `ENV`-declared credential planted in `mcp-host/Containerfile` | Suite reds | Confirms the 4th file is now actually governed, not just listed |
| `spec-pixi-container-image` Constraints line | Currently reads "until ≥2 Containerfiles diverge" against a 3-file assumption | Updated to read against four | N/A |

</intent-contract>

## Code Map

- `tests/packaging/test_containerfile_base_layer_convention.py` — replace the hard-coded
  `CONTAINERFILES: tuple[Path, ...]` (currently 3 entries, ~lines 50-52) with a derivation: glob
  `Containerfile*` under `REPO_ROOT`, filtered to git-tracked paths; add a count/membership
  assertion proving the derivation finds all four, and extend the existing synthetic-regression
  parametrization to cover a planted violation in
  `src/platform/compose/mcp-host/Containerfile`.
- `scripts/pixi_version_registry.py` (read-only reference, `SITES` ~lines 70-87) — the existing
  four-file enumeration this story's derivation should end up agreeing with (not import from
  directly unless that's the simplest correct approach — the two checks are for different
  concerns, base-layer convention vs. pixi-version pinning).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pixi-container-image/` (or
  wherever its Constraints section lives) — update the "until ≥2 Containerfiles diverge" line to
  read against four Containerfiles.
- `src/platform/compose/mcp-host/Containerfile` (read-only reference) — the previously-omitted,
  currently-compliant file this story brings under governance; no content change expected unless
  the new synthetic-regression test reveals an actual violation (not expected — the epic states it
  is compliant today).

## Tasks & Acceptance

**Execution:**
- `[fix]` Replace `CONTAINERFILES`'s hard-coded tuple with a derivation (glob `Containerfile*`,
  git-tracked only) in `tests/packaging/test_containerfile_base_layer_convention.py`.
- `[fix]` Add a test proving the derivation finds all four files (count assertion or explicit
  membership check for `src/platform/compose/mcp-host/Containerfile`), so an empty/partial glob
  cannot pass vacuously.
- `[fix]` Extend the file's mandatory synthetic-regression parametrization so a planted unpinned
  base image or `ENV`-declared credential in `src/platform/compose/mcp-host/Containerfile` reds
  the suite.
- `[docs]` Update `spec-pixi-container-image`'s Constraints line ("until ≥2 Containerfiles
  diverge") to read against four Containerfiles.

**Acceptance Criteria:**
- Given the repo's two enumerations of its Containerfiles disagree: `scripts/pixi_version_registry.py:79-87`
  covers all four, while the convention guard's `CONTAINERFILES` tuple
  (`tests/packaging/test_containerfile_base_layer_convention.py:50-52`) hard-codes only three —
  omitting `src/platform/compose/mcp-host/Containerfile` (spec-mcp-era-isolation slice 1), which is
  therefore ungoverned by the registry-pinned-base and no-`ENV`-credential checks. The omitted file
  is compliant today; the finding is that nothing would notice if it stopped being.
- When the tuple is replaced by a derivation over the tracked tree (glob `Containerfile*`,
  git-tracked only, so an untracked scratch Containerfile cannot red the suite) — not by appending
  a fourth literal, which reproduces the same defect one file later.
- Then all four files are swept by both the `FROM` and `ENV` checks, a test proves the derivation
  actually finds them (a count assertion, or an explicit membership check for the
  previously-omitted path, so an empty glob cannot pass vacuously — an absence assertion that
  cannot be distinguished from having scanned nothing is the failure mode the fleet has hit
  before), a planted unpinned base or `ENV`-declared credential in the fourth file reds the suite,
  and `spec-pixi-container-image`'s Constraints line ("until ≥2 Containerfiles diverge") reads
  against four rather than three.
- Note: no `conda-forge-expert` involvement — this touches no recipe and no CFE surface, so
  Rules 1/2 do not apply to this story.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live across doctor's own Epic 21 backlog this session.

## Review Triage Log
