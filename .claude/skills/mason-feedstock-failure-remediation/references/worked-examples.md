# Worked Examples

> Each case records the PR set, per-PR classification + outcome, and any novel
> finding (which feeds the Wave E skill retro).

## Worked Example: 2026-06-17/18 batch — 12 PRs (first run of this workflow)

| Parameter | Resolved value |
|---|---|
| `<pr_refs>` | 12 PRs (11 feedstock autotick + 1 staged-recipes review comment) |
| `<mode>` | `batch` (6 parallel diagnostic subagents in Wave A) |
| `<fork_owner>` | `rxm7706` |
| `<local_test_subdir>` | `linux_64` |

**Empirical state (verified 2026-06-17/18)**: mixed format (v0 meta.yaml +
v1 recipe.yaml); all feedstocks `rxm7706`-maintained except the prerequisite
`sqlglot-feedstock` (caused the collate block).

### Per-PR classification + outcome

| PR | Class | Root cause | Fix | Outcome |
|---|---|---|---|---|
| cocoindex #12 | FLAKE | win pixi-provision `dispatch task is gone` (`attrs` fetch) | restart ci | **MERGED** |
| html-to-markdown #110 | FLAKE | win-py3.12 `dispatch task gone` (`m2-libintl`) | restart ci | **MERGED** |
| dlt #65 | FLAKE | win `_Py_HashRandomization_Init: failed to get random numbers` | restart ci | **MERGED** |
| selectolax #29 | FLAKE | osx-arm64-py3.13 `IncompleteRead` mid build-env download | restart ci | **MERGED** |
| llms-py #39 | REAL_FIX | `datetime.UTC` (py3.11+); 3.10 floor failed import | python_min 3.11 via **recipe CBC** (v1, G31) | **MERGED** |
| copilotkit #20 | REAL_FIX | pip_check: `ag-ui-langgraph>=0.0.35` needed, recipe capped `<0.0.32` | bump run dep `>=0.0.35` | **MERGED** |
| okta-jwt-verifier #8 | REAL_FIX | `retry2>=0.9.5` not on conda-forge | swap → `retry` (loosen + TODO, G10) | **MERGED** |
| fs.googledrivefs #7 | REAL_FIX | `import fs` → `No module named 'pkg_resources'` (setuptools 82) | `setuptools <81` in run (G34) | **MERGED** |
| wagtail-nav-menus #8 | REAL_FIX | `BackendUnavailable: hatchling.build` (upstream switched backend) | host `poetry-core` → `hatchling` | **MERGED** |
| wagtail-sharing #5 | REAL_FIX | `requires-python >=3.12` + linter float-parse | `{% set python_min = "3.12" %}` (v0, G31) + quote version (G14) | **MERGED** |
| microsoft-kiota-bundle #2 | BLOCKED | 5 sibling feedstocks at 1.10.1, recipe pins `1.10.3.*`; no sibling PRs | **deferred** (operator) | parked |
| collate-sqllineage #33 | BLOCKED | upstream pins `sqlglot==29.0.1`; conda-forge max 28.10.1; bump PR conflicting + not `<fork_owner>`'s feedstock | **deferred** (operator) | parked |
| lyric-py (staged-recipes) #33764 | adjacent | reviewer: redundant identical `if: unix` branches | collapse to single content entry; render+build-verified | operator-handled |

**Tally**: 10 merged (6 real fixes + 4 flake-restarts), 2 deferred-as-blocked,
1 adjacent review-comment fix (operator pushed).

### Novel findings → Wave E retro (CFE v8.30.0)
- **G31** — python_min override differs by format (v1 CBC+rerender; v0
  `{% set %}`); `context.python_min` is silently ignored on v1 feedstocks.
- **G32** — flake-vs-fix triage signature catalog + maintainer-edit push (the
  `gh pr checkout` → upstream-`origin` stray-branch trap).
- **G33** — local v1 build must not pass `.ci_support` (strict `channel_sources`
  excludes the just-built package from its own test); the `conda search`
  not-found-listing misread trap.
- **G34** — `pkg_resources.declare_namespace` deps break under setuptools 81+.
- **Auto-memory** — `feedback_test_locally_before_push`.

### Per-case decisions
- Both BLOCKED PRs deferred (operator chose skip/hold over bumping the
  prerequisite feedstocks or G26-loosening).
- lyric-py verified with a full 4-variant local build (all green) even though
  the change was a structural no-op, because the operator's "test locally first"
  directive was explicit; render-only would have sufficed per Q6.
