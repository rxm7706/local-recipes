# Per-station TEA status — verified 2026-08-02

Ground truth, checked directly against the repo (not the dashboard, not any
station's own claims) at spec-authoring time. Re-verify before trusting this
table after any station lands more stories.

| Station | Real tests (`src/shared/packages/pyforge-<slug>/tests/test_*.py`) | `planning-artifacts/test-architecture.md` | Notes |
|---|---:|---|---|
| Herald  | 20 | Real (2077 lines, epic/story-grounded) | Only station with both a real doc and a package-tests dir already wired to a pixi `-test` task from day one. |
| Marshal | 20 | Real (438 lines, epic/story/FR/AD-grounded) | Also has 4 real shared-support mocks under `_bmad-output/projects/pyforge-marshal/tests/mocks/` (`mock_github_api.py` 89 ln, `mock_worktree.py` 42 ln, `mock_supervisor.py` 61 ln, `mock_runner.py` 54 ln) and a 299-line `conftest.py` at that same planning-scaffold location — real, not boilerplate, but not yet consumed by any other station. |
| Atlas   | 78 | Boilerplate (81 lines, "TBD" ×3) | 100% code-complete (38/38 stories); real test coverage is far ahead of what the doc or dashboard currently shows. |
| Warden  | 54 | Boilerplate (78 lines, "TBD" ×3) | 100% code-complete (31/31 stories); same under-reporting as Atlas. |
| Doctor  | 13 | Boilerplate (78 lines, "TBD" ×3) | Tracks roughly with its 42% story completion. |
| Mason   | 8  | Boilerplate (78 lines, "TBD" ×3) | Tracks roughly with its 11% story completion. |
| Steward | 7  | Boilerplate (78 lines, "TBD" ×3) | Tracks roughly with its 17% story completion. |
| Scribe  | 3  | Boilerplate (78 lines, "TBD" ×3) | Tracks roughly with its 22% story completion. |

## What the boilerplate six have in common

Diffing any two of {atlas, doctor, mason, scribe, steward, warden}'s
`test-architecture.md` shows identical structure with only the station noun,
one-line scope description, and coverage-target label swapped — every
"Target Stories" cell reads "TBD", every status reads "⏳ READY". None
reference an actual story ID, module name, or FR/AD number. All six were
created in the 2026-08-02 09:42 bulk commit (`dad47c408a`) alongside
confirmed-fabricated content elsewhere in the same commit (a false
sprint-status-ledger migration note, since removed).

## Why the dashboard under-reports this

`docs/dashboard/generate.py`'s `_stage_globs()` `tea` entry (added in the
same commit, kept — the addition itself is legitimate) points at
`_bmad-output/projects/<slug>/tests/test_*.py` and `**/*.spec.ts`. That
planning-scaffold directory holds only mocks and fixtures (Marshal) or empty
`__init__.py` stubs (the other seven) — never the real tests, which live at
`src/shared/packages/pyforge-<slug>/tests/` per the workspace-package
convention already documented in `project-context.md`. Until CAP-1 lands,
the dashboard will show every station's `tea` stage as unpopulated
regardless of real coverage.
