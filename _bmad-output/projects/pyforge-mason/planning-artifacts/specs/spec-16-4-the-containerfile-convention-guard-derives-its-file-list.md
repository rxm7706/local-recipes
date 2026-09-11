---
title: 'The Containerfile convention guard derives its file list'
type: 'fix'
created: '2026-09-10'
status: 'done'
baseline_revision: '57c001c9d7c8864ec235b871c8e3dc024845e414'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      docs/reference/container-base-layer-convention.md still says "three Containerfiles"
      and never mentions src/platform/compose/mcp-host/Containerfile, even though the
      guard test's own module docstring points readers there for "the full convention."
    evidence: |-
      Verified unchanged by this diff and predates it -- stale since mcp-host/Containerfile
      was added (spec-mcp-era-isolation slice 1), independent of today's derivation fix.
      The intent-contract names only spec-pixi-container-image's Constraints line for a
      doc update (already satisfied pre-diff), not this file.
    location: >-
      docs/reference/container-base-layer-convention.md
    severity: low
  - summary: >-
      tests/packaging (including this guard test and its new coverage) is never invoked
      by any CI workflow, so a real regression here could merge to main undetected.
    evidence: |-
      Verification-gap review searched every .github/workflows/*.yml for "packaging",
      "pyforge-deps-test", and "test-packaging" -- zero matches, independently
      re-confirmed. Pre-existing: predates this diff, and the sibling
      tests/packaging/test_containerfile_checkout_path.py has the identical gap. Worth
      a follow-up story mirroring how cfe-regression-net.yml closed the analogous gap
      for the CFE test suite.
    location: >-
      .github/workflows/ (missing tests/packaging wiring)
    severity: high
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

## Spec Change Log

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 17 findings — high 1, medium 1, low 11, false 4, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind-hunter: `MIN_EXPECTED_ENV_LINES = 5` contradicts the comment directly above it, which computes "HOME+DJANGO_SETTINGS_MODULE (2) + HOME+NOTE_BOOK_ENABLE (2) + HOME+PYTHONPATH (2) = 6 ENV directives today" — verified the four real Containerfiles do have exactly 6 tracked `ENV` lines today (`grep -c "^ENV "` across all four), so the floor is one weaker than its own documented arithmetic and the story's own math. — fixed: `MIN_EXPECTED_ENV_LINES` set to `6`.
  - `[low]` `[patch]` blind-hunter: the `test_unpinned_base_guard_fires_on_synthetic_regressions` parametrize block still comments "Real, correctly-pinned examples (mirroring the three real files)" — the one stale "three Containerfiles" reference this diff's otherwise-thorough four-file sweep missed (verified: this line was untouched by the diff). — fixed: comment updated to reflect four real files.
  - `[low]` `[defer]` blind-hunter + verification-gap (other) + intent-alignment (divergence 2): `docs/reference/container-base-layer-convention.md` — cross-referenced by this test file's own module docstring — still says "three Containerfiles" throughout and never mentions `mcp-host/Containerfile` (verified: doc unchanged by this diff, predates it). Pre-existing since `mcp-host/Containerfile` was added (spec-mcp-era-isolation slice 1), not caused by this story; the intent-contract names only the `spec-pixi-container-image` Constraints line for a doc update, not this file. — deferred, see frontmatter.
  - `[low]` `[patch]` blind-hunter + edge-case-hunter (x2): `_git_ls_files()`'s `subprocess.run(["git", "-C", REPO_ROOT, "ls-files"], ...)` runs at module import time with no `timeout` and no exception handling, unlike every other subprocess call in `tests/packaging/*.py` (all inside test functions, never at collection time) — a hang or failure here fails collection of the whole 25-test module rather than one test. Verified git itself is guaranteed present and working in every consumer of this module (this is always collected from inside a git worktree; no pixi task or CI workflow invokes it elsewhere), so the "git absent" half is unreachable in this codebase's actual topology, but the missing `timeout` is a real, trivial-to-fix gap this diff introduced. — fixed: added `timeout=30` to the `subprocess.run` call.
  - `[low]` `[patch]` blind-hunter: `_filter_containerfile_paths()` uses `fnmatch.fnmatch(name, "Containerfile*")`, which is case-normalized per `os.path.normcase` (case-insensitive on Windows, case-sensitive on POSIX) — verified `win-64` is a real declared platform for this workspace (`pixi.toml:20`), so the derived `CONTAINERFILES` set could differ by OS for an identical tracked tree. — fixed: switched to `fnmatch.fnmatchcase`.
  - `[low]` `[reject]` blind-hunter + edge-case-hunter: the `Containerfile*` glob matches any tracked file whose basename merely starts with "Containerfile" (e.g. a hypothetical `Containerfile.bak`), which could get swept into FROM/ENV parsing. Verified no such file exists today (`git ls-files | grep -i Containerfile` returns exactly the four real files plus this story's own spec/test files, neither of which matches the case-sensitive basename prefix) — this is exactly the glob the intent-contract's own Approach section specifies verbatim ("a glob for `Containerfile*`, restricted to git-tracked files"), so tightening it is a spec-level design question, not a diff defect; also unlikely to be encountered in everyday use, and even if it occurred `_from_directives`/`_env_directives` would almost certainly find zero matching lines in an unrelated file. Rejected as low-severity, non-currently-manifesting, and not worth a non-trivial glob redesign.
  - `[false]` `[reject]` blind-hunter: claimed the two new planted-violation tests couple to real file content (`.replace()` on real `mcp-host/Containerfile` text), creating a recurring maintenance cost. Refuted: both tests explicitly `assert planted_text != real_text` before proceeding, so a future base-image/pin change to that file fails loudly with an instructive message ("update this test if that line changed") rather than silently drifting — the coupling is a deliberate, self-guarded design choice mandated by the intent-contract's own AC ("Confirms the 4th file is now actually governed, not just listed"), not an unguarded defect.
  - `[false]` `[reject]` blind-hunter: claimed the new `MCP_HOST_CONTAINERFILE` module-level constant reintroduces the "hard-coded literal" anti-pattern the story fixes. Refuted: the anti-pattern this story targets is specifically about the coverage-determining `CONTAINERFILES` tuple silently omitting a file — that tuple remains fully derived. `MCP_HOST_CONTAINERFILE` only selects which real file two supplementary regression tests target; it plays no role in governance/coverage, and a rename would surface as a loud `FileNotFoundError` in those two tests, not a silent coverage gap.
  - `[low]` `[reject]` edge-case-hunter: `git ls-files` C-quotes non-ASCII/special-character paths by default, but `_git_ls_files()` parses stdout with plain `.splitlines()`, which could mis-parse a quoted path. Verified no tracked file in this repo has such a name, and no Containerfile plausibly would. Unlikely to be encountered in everyday use, and the fix (switching to `git ls-files -z` plus NUL-splitting) is more than a direct correction — rejected.
  - `[high]` `[defer]` verification-gap (pre-verified): no `.github/workflows/*.yml` invokes `tests/packaging` (searched all workflow files for `packaging`, `pyforge-deps-test`, `test-packaging` — zero matches; independently re-confirmed via `grep -rl` during triage), so none of this file's assertions — old or new — ever run in CI; a regression could merge to `main` undetected. Pre-existing (predates this diff; the sibling `test_containerfile_checkout_path.py` in the same directory has the identical gap; the intent-contract scopes only the derivation logic and one doc line, not CI wiring) — deferred, see frontmatter, per the layer's own filed disposition.
  - `[false]` `[reject]` intent-alignment (divergence 1): noted the diff carries no self-documentation that `spec-pixi-container-image`'s Constraints-line AC was already satisfied pre-diff. Refuted: verified directly against `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pixi-container-image/SPEC.md` — its Constraints section already reads "four now exist and none diverges (2026-09-09)," landed a day before this story's spec was even created (commit `2a63b00c27`, confirmed an ancestor of this diff's baseline). The AC is satisfied at HEAD; no bad outcome occurs.
  - `[false]` `[reject]` intent-alignment (divergence 3): noted `test_untracked_scratch_containerfile_is_excluded_from_derivation` drives the pure `_filter_containerfile_paths()` function against a synthetic list rather than an actual untracked file in a real working tree. Refuted: `_git_ls_files()` is a thin wrapper over `git ls-files`, which by definition never lists untracked files, so the integration-level guarantee holds by construction; testing the pure function in isolation (matching this file's established "never mutate the working tree" design philosophy) is the correct unit-testing choice, not a gap.

## Auto Run Result

**Summary:** Replaced `tests/packaging/test_containerfile_base_layer_convention.py`'s hard-coded 3-entry `CONTAINERFILES` tuple with a derivation over the git-tracked tree (`_git_ls_files()` + `_filter_containerfile_paths()`, matching basename against `Containerfile*`, case-sensitively), so the previously-omitted `src/platform/compose/mcp-host/Containerfile` is now governed by both the unpinned-base and ENV-credential checks. Added a non-vacuous proving test (count floor + explicit membership), an untracked-scratch-file exclusion test, and two planted-violation regression tests against the real `mcp-host/Containerfile` content. `spec-pixi-container-image`'s Constraints line was already updated to read against four Containerfiles in a prior, unrelated commit (`2a63b00c27`, landed the day before this story's spec was created) — verified satisfied at HEAD, no further doc edit needed.

**Files changed:**
- `tests/packaging/test_containerfile_base_layer_convention.py` — derivation replaces the hard-coded tuple; `MIN_EXPECTED_FROM_LINES`/`MIN_EXPECTED_ENV_LINES` floors raised to match four files (8/6); four new tests (non-vacuous derivation proof, untracked-scratch exclusion, two planted-violation regressions against `mcp-host/Containerfile`); docstrings/comments swept from "three" to "four"/"every tracked".

**Review findings breakdown** (full detail in Review Triage Log above):
- Patched (4): `MIN_EXPECTED_ENV_LINES` off-by-one vs. its own documented arithmetic (medium); a stale "three real files" comment the four-file sweep missed (low); no `timeout` on the module-import-time `git ls-files` subprocess call (low); `fnmatch.fnmatch` case-sensitivity portability risk on the declared `win-64` platform (low).
- Deferred (2, pre-existing, not caused by this story — see frontmatter `deferred`): `docs/reference/container-base-layer-convention.md` still describes three Containerfiles and omits `mcp-host` (low); `tests/packaging` is never invoked by any CI workflow, so no assertion in this file — old or new — currently runs on a PR or push to `main` (high).
- Rejected (11): over-broad `Containerfile*` glob could theoretically sweep in an unrelated tracked file (low, unlikely + the exact glob the intent-contract specified verbatim) — 2 reports, same root cause; `git ls-files` C-quoting of exotic filenames unhandled (low, unlikely + fix is more than a direct correction); planted-violation tests' coupling to real file content (false — the tests self-guard with an explicit loud-failure assertion); the new `MCP_HOST_CONTAINERFILE` constant "reintroducing" the hard-coded-literal anti-pattern (false — it doesn't participate in coverage/governance); the diff not self-documenting that the `spec-pixi-container-image` doc AC was already satisfied pre-diff (false — verified satisfied at HEAD); the untracked-scratch test exercising the pure function rather than a real untracked file (false — correct by construction and by this file's established testing philosophy).

**Follow-up review recommendation:** `false`. This is a first pass; only one `medium` entry was patched (not two-or-more) and no `high` entry was patched — the convergence bar isn't met. Patched counts by verdict: medium 1, low 3.

**Verification performed:** `pixi run -e pyforge-ci pytest tests/packaging/test_containerfile_base_layer_convention.py -v` → 25/25 passed, both before and after the patch pass. Matrix Test Audit: all five I/O & Edge-Case Matrix rows covered by a passing test (derivation finds all four; non-vacuous proof; untracked-scratch exclusion; planted violation in the fourth file, both FROM and ENV; the doc-line AC verified satisfied out-of-band). `git diff --stat` confirms only the target test file and this spec changed — no scope creep.

**Residual risks:** the two deferred, pre-existing gaps above remain open (human-facing convention doc undercounts the governed surface by one file; `tests/packaging` — including this story's own new coverage — has no CI wiring, so a real regression here could still merge to `main` undetected). Neither is caused by this story; both are recorded in frontmatter `deferred` for future pickup.
