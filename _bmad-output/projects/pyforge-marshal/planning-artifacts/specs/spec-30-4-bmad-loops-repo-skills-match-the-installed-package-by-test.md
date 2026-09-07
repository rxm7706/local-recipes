---
title: "Story 30.4: bmad-loop's repo skills match the installed package -- by test"
type: 'chore'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'ae4603eb559dd5726a809827382729402c116dfe'
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/epic-30-context.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `bmad-loop-setup`'s three repo skill dirs (`bmad-loop-setup`, `bmad-loop-sweep`,
`bmad-loop-resolve`) are hand-vendored copies of the installed `bmad-loop` conda package's own
`bmad_loop/data/skills/` canon, and nothing catches them drifting apart when the package
upgrades. `module.yaml`'s `module_version` field already reads `0.11.1` (already fixed, verified
against the installed package), and all three skill dirs are already byte-identical to the
installed canon (verified via `diff -rq`) — so the one remaining gap is that this equivalence
is asserted nowhere; a future package bump could silently drift the repo copies without any
test noticing.

**Approach:** Add one new meta-test that resolves the installed `bmad_loop` package's directory
via `importlib.util.find_spec("bmad_loop")` (never `importlib.metadata`, which does not reliably
locate a conda-installed package's data files the same way), diffs each of the three repo skill
dirs against `<package>/data/skills/<name>/`, and reds on any divergence — proven by a planted
one-line fixture divergence. Verify `bmad-loop validate` stays clean across all 8 loop homes
(no code change expected there; a verification-only check).

## Boundaries & Constraints

**Always:**
- The new test resolves the installed package location via `importlib.util.find_spec` (never
  `importlib.metadata.distribution(...).locate_file`), matching the register's own resolution
  choice.
- Compare all three repo skill dirs (`bmad-loop-setup`, `bmad-loop-sweep`, `bmad-loop-resolve`)
  against the installed package's `data/skills/<name>/` canon, file-by-file, recursively.
- The test must skip gracefully (not fail) if `bmad_loop` is not importable in the running
  environment (e.g. a different pixi env without the package) — this is a repo-hygiene guard,
  not a hard requirement that every test env has bmad-loop installed; assert nothing if the
  package cannot be located, rather than false-failing on a missing dependency.
- Prove detection with a `tmp_path`-based fixture (never mutate the real repo tree) that plants
  a one-line divergence and asserts the test's own diff logic reports it.

**Never:**
- Do not touch `module.yaml` — `module_version` already reads `0.11.1`, matching the installed
  package; no change needed there.
- Do not modify any of the three repo skill dirs — they are already identical to the installed
  canon; this story only adds the regression proof.
- Do not perform the CFE Rule-2 retro dance inline in the story commit — per Story 30.1's
  landed precedent, any new file under `.claude/skills/conda-forge-expert/**` must land in its
  own separate `retro:`-subject commit that also bumps `CHANGELOG.md`/`SKILL.md`
  version/`MANIFEST.yaml`/`config/skill-config.yaml` (PATCH), because `pyforge-marshal`'s own
  `test_conda_forge_expert_not_replaced` (and the mason/steward/atlas station equivalents)
  reject any non-mason commit touching the CFE surface outside that sanctioned shape.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Repo skills match installed canon (current real state) | The live repo tree + installed `bmad_loop` 0.11.1 | New test passes: zero diffs across all three skill dirs | N/A |
| Planted one-line divergence | A `tmp_path` fixture copy of one skill dir with one line changed | Test's diff logic reports the divergence (red-on-plant proof) | N/A |
| `bmad_loop` not importable | `importlib.util.find_spec("bmad_loop")` returns `None` | Test skips (pytest.skip), never fails | N/A |

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py` — NOT
  touched by this story (unrelated file, referenced only for precedent on `pytest.mark.meta`
  usage and `tmp_path` fixture style already established in this test directory).
- `.claude/skills/conda-forge-expert/tests/meta/test_bmad_loop_skills_match_installed.py` (NEW)
  — the deliverable. Uses `importlib.util.find_spec("bmad_loop")` to locate the installed
  package (its `spec.submodule_search_locations` or the parent of `spec.origin`), builds the
  path `<pkg_dir>/data/skills/<name>/` for each of `("bmad-loop-setup", "bmad-loop-sweep",
  "bmad-loop-resolve")`, and recursively diffs file contents (and file sets) against
  `REPO_ROOT / ".claude/skills/<name>"`. A `pytest.mark.meta` test for the real-tree
  assertion (skips cleanly if `bmad_loop` is not importable), plus a `tmp_path`-based
  red-on-plant test using two small synthetic directory trees (not the real skill dirs) to
  prove the diff logic itself detects a one-line divergence, independent of whether
  `bmad_loop` happens to be installed in the CI environment running this specific test.
- `.claude/skills/bmad-loop-setup/assets/module.yaml` — read-only reference; confirmed already
  at `module_version: 0.11.1`, matching installed `bmad-loop 0.11.1` (`pixi list -e
  local-recipes | grep bmad-loop`). No edit.
- `.claude/skills/{bmad-loop-setup,bmad-loop-sweep,bmad-loop-resolve}/` — read-only reference;
  confirmed byte-identical to `<installed bmad_loop pkg>/data/skills/<name>/` via `diff -rq`
  (zero output, all three). No edit.
- `~/.bmad-loops/pyforge-{atlas,doctor,herald,marshal,mason,scribe,steward,warden}/` — the 8
  loop homes; `bmad-loop validate` run against each as a verification step, no code change
  expected.

## Tasks & Acceptance

**Execution:**
- `.claude/skills/conda-forge-expert/tests/meta/test_bmad_loop_skills_match_installed.py` --
  CREATE -- proves by test (not just observation) that the three repo `bmad-loop-*` skill
  dirs never silently drift from the installed package's canon, closing the gap the Spec's
  open question named (no assertion existed before this story).

**Acceptance Criteria:**
- Given the installed `bmad-loop` 0.11.1 package and the current repo tree, when the new
  meta-test runs, then it passes (zero divergence across all three skill dirs).
- Given a `tmp_path` fixture with a planted one-line divergence between two synthetic
  directory trees, when the test's diff-detection logic runs against them, then it reports
  the divergence (proves the guard is not a vacuous no-op).
- Given `bmad_loop` is not importable in some other test environment, when the real-tree test
  runs there, then it skips cleanly rather than failing.
- Given all 8 loop homes (`~/.bmad-loops/pyforge-*`), when `bmad-loop validate` runs against
  each, then it reports clean for all 8 (verification only; no code change from this story
  should affect this).

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- verdicts: 18 findings — high 0, medium 5, low 5, false 8, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind Hunter: `spec-packaging-factory`'s new memlog note claims "no other file in this surface is touched" while the same diff's baseline stamp re-hashes `CHANGELOG.md`/`MANIFEST.yaml`/`SKILL.md`/`config/skill-config.yaml` — verified true (confirmed via `git show HEAD:scripts/.spec-surface-baseline.json`: those 4 entries were stale, pre-dating the 647fda3ed3 retro). Fixed: appended a correction note explaining the stale entries were leftovers Story 30.1's cleanup missed for this spec (only the sibling spec was scoped-stamped), with the `Scoped-stamped:` trailer.
  - `[medium]` `[patch]` Blind Hunter: the same 4 hashes were already reconciled once under `spec-conda-forge-expert-rebuild` (commit `ae4603eb55`) — this diff silently re-stamps them again under `spec-packaging-factory` with no note explaining the second, independent catch-up. Grouped with the finding above; same fix.
  - `[medium]` `[patch]` Blind Hunter: the `spec-packaging-factory` entry omits the `Scoped-stamped:` trailer every sibling entry in both memlogs carries — verified true. Grouped with the two findings above; same fix.
  - `[medium]` `[patch]` Verification Gap Reviewer: same underlying issue independently confirmed (`git show` diff of the stale vs. corrected hashes) — not a functional risk (`spec-surface` detector passes either way) but a factually inaccurate audit note. Grouped with the findings above; same fix.
  - `[medium]` `[patch]` Intent Alignment Auditor: governance bookkeeping (baseline stamp) touches CFE files not touched in this diff's content, with no written trail inside the diff explaining the prior-commit attribution. Grouped with the findings above; same fix.
  - `[low]` `[patch]` Blind Hunter: `assert installed.is_dir()` / `assert repo.is_dir()` sit inside the per-skill loop, so a missing dir for one skill aborts before checking the remaining ones or reporting already-collected diffs — verified true by reading the code. Fixed: missing dirs now collect as diff entries; the loop always checks all three skills.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter: `find_installed_package_dir`'s `spec.origin`-parent fallback branch had no test coverage — verified true (grep for the branch in test bodies found none). Fixed: added `test_find_installed_package_dir_uses_origin_fallback`.
  - `[low]` `[patch]` Blind Hunter: the assertion failure message says "re-run bmad-loop-setup's refresh" without naming the concrete command — verified true; the real command (`bmad-loop init --project <root> --cli claude --force-skills`) is documented in `bmad-loop-setup/SKILL.md`. Fixed: message now names it verbatim.
  - `[low]` `[patch]` Blind Hunter: the module docstring's "verified directly against the installed package before writing this test" is an unfalsifiable claim a future reader can't audit — verified true (no recorded evidence of that specific manual check). Fixed: reworded to point at the checkable fact (the real-tree test passes unskipped) instead.
  - `[low]` `[reject]` Blind Hunter: `diff_dirs` doesn't check file mode (executable bit) or file type (symlink vs. regular file) — verified true but rejected: the three `bmad-loop-*` skill dirs hold only Markdown/YAML assets (confirmed by listing), so an executable-bit or symlink divergence is not a defect class this package's actual content can exhibit in everyday use, and the fix (stat + symlink-aware comparison) adds meaningfully more logic than a direct correction.
  - `[false]` `[reject]` Blind Hunter: `REPO_ROOT`/`SKILL_DIR` computed via a two-step `.parent.parent.parent` + `.parents[2]` idiom, claimed to diverge from the directory's established one-line `parents[5]` convention — refuted: this is the IDENTICAL two-step idiom already used in the sibling `test_no_retired_bmad_skill_ids.py` (Story 25.1/30.1), not a novel divergence; both idioms already co-exist in this test directory, and the new file matches the more directly comparable BMAD-hygiene-guard precedent.
  - `[low]` `[reject]` Blind Hunter: `_relative_files`/`diff_dirs` uses unrestricted `rglob("*")`, which follows symlinked subdirectories with no cycle handling — verified true but rejected: no symlinks exist in the real skill-dir trees (confirmed by listing), unlikely in everyday use, and cycle-safe symlink handling is meaningfully more code than a direct correction.
  - `[low]` `[reject]` Edge Case Hunter: `submodule_search_locations` may have multiple entries; only the first is used — verified true as written but rejected: `bmad_loop` is a regular (non-namespace) conda-installed package, which always has exactly one search location; the multi-location case is unreachable for this package, and handling ambiguity across multiple locations is more than a direct correction.
  - `[false]` `[reject]` Edge Case Hunter: `find_spec` could raise on a corrupted install instead of returning `None`, "contradicting the skip-not-fail intent" — refuted: the spec's stated skip condition is "not importable in this environment" (package absent), not "installed but corrupted"; a corrupted install is a different, more severe failure that surfacing loudly is the correct behavior for a repo-hygiene guard, not a defect.
  - `[low]` `[reject]` Edge Case Hunter: `_relative_files` only collects files, so an added/removed empty directory goes undetected — verified true but rejected: git does not track empty directories, so this scenario cannot arise from a real commit to either tree in practice; unlikely in everyday use, and the fix (directory-set comparison) is more than a direct correction.
  - `[false]` `[reject]` Intent Alignment Auditor: `module.yaml` is named in Story 30.1's — Story 30.4's — Surface line but the diff touches zero bytes of it, with the real fix attributed to an unrelated commit under a different spec's FR/AD — refuted: the Given/Then describes an outcome state (module_version correct), independently verified true (installed package matches) and explicitly documented as already-satisfied in both this spec's Design Notes and the new test's own docstring; which commit/spec gets attribution is immaterial to the outcome the AC asks for.
  - `[false]` `[reject]` Intent Alignment Auditor: the real-tree test is skip-capable and the red-on-plant proof only exercises synthetic directories, so the "reds a planted divergence" guarantee reads as conditional rather than the one integrated behavior the story text implies — refuted: never mutating the real repo tree during a test is the correct engineering practice, and this spec's own Boundaries explicitly mandated exactly this two-test decomposition as a deliberate, safer reading of the literal epics.md wording, not an accidental gap; the real-tree test did run unskipped and pass against the actual installed package.
  - `[false]` `[reject]` Intent Alignment Auditor: nothing in the diff records that `bmad-loop validate` was run against all 8 loop homes — refuted: verification-only checks (no code produced) are recorded in the Tier-3 spec's own Auto Run Result section per this workflow's established convention (see Story 30.1), not in the tracked diff; the check was run (7/8 clean, 1 pre-existing unrelated finding on the `pyforge-marshal` loop home, disclosed below) even though a runtime-only check leaves no diffed artifact.

## Design Notes

`module_version` and the three skill-dir contents are ALREADY correct in the live tree
(verified directly: `module.yaml` reads `0.11.1`; `diff -rq` against the installed package's
`data/skills/*` is empty for all three dirs) — a prior commit already closed that one-line
drift before this story ran. This story's actual remaining work, per the register's own
compressed framing ("bmad-loop skills meta-test"), is narrower than the story's own epics.md
text implies: only the regression-guard TEST is new; there is no skill-file content to change.

## Verification

**Commands:**
- `pixi run -e local-recipes test-skill --keyword test_bmad_loop_skills_match_installed` --
  expected: all tests in the new file pass.
- `pixi run -e local-recipes test-skill --meta` -- expected: full suite green.
- `bmad-loop validate` run against each of the 8 `~/.bmad-loops/pyforge-*` homes -- expected:
  clean for all 8.
- `pixi run -e local-recipes detectors-ci` -- expected: clean (or unchanged pre-existing
  findings only).

## Auto Run Result

**Summary:** Added `test_bmad_loop_skills_match_installed.py`, a regression guard proving the
repo's three `bmad-loop-*` skill dirs never silently drift from the installed `bmad_loop`
package's canon (located via `importlib.util.find_spec`). `module.yaml` and the three skill
dirs needed no edit — both were already correct in the live tree. Review pass fixed a
misleading `spec-packaging-factory` memlog note (a pre-existing Story 30.1 reconciliation gap
this story's baseline stamp happened to surface) plus four small code-quality patches in the
new test file.

**Files changed:**
- `.claude/skills/conda-forge-expert/tests/meta/test_bmad_loop_skills_match_installed.py` (new)
  — the regression guard + its unit-test coverage of the diff/resolution logic.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/{spec-conda-forge-expert-rebuild,spec-packaging-factory}/.memlog.md`
  — foreign spec-surface reconcile notes; `spec-packaging-factory`'s corrected for a Story
  30.1 reconciliation gap this story's stamp surfaced.
- `scripts/.spec-surface-baseline.json` — scoped re-stamp for both mason specs.

**Review findings breakdown:** 18 findings total — 5 patched (1 medium grouped entry, 4 low
entries; all applied directly), 8 rejected as false (claims refuted with evidence), 5 rejected
as low (unlikely in everyday use + fix adds more than a direct correction).

**Follow-up review recommendation:** `false` — 0 high-verdict patches, 1 medium-verdict patch
(below the "two or more medium" threshold).

**Verification performed:**
- `pixi run -e local-recipes test-skill --keyword test_bmad_loop_skills_match_installed` — 5
  passed.
- `pixi run -e local-recipes test-skill --meta` — 7617 passed, 3 skipped (pre-existing).
- `bmad-loop validate --project <home> --json` against all 8 `~/.bmad-loops/pyforge-*` homes —
  7/8 clean; `pyforge-marshal`'s home reports one pre-existing `git.worktree-clean` problem
  (an untracked `.bmad-loop/marshal-model-cost-catalog.json` dated 2026-09-02, four days
  before this session, in a separate git repository from `local-recipes` entirely) —
  unrelated to this story, disclosed rather than silently claimed clean.
- `pixi run -e local-recipes detectors-ci` — 17/18 clean; the one finding (`dream-chain`,
  `bmad-cursor-interactive-routing`) is pre-existing, landed on `main` before this branch.

**Residual risks:** the `pyforge-marshal` loop home's stray untracked file is a separate,
pre-existing hygiene item outside this story's and this repo's scope (a different git
worktree entirely) — noted for a future operator hygiene pass, not blocking.
