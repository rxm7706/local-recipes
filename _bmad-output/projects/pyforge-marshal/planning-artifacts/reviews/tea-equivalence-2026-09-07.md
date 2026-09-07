# TEA Equivalence Report — Story 31.1 (2026-09-07)

**Contract:** `spec-bmad-suite-lifecycle` CAP-4 / AD-5, AD-9, AD-10; `spec-bmad-611-era-alignment`
CAP-13. Verifies whether TEA's `bmad-testarch-test-design` (system-level) can replace
`_bmad/scripts/bmad_tea_playwright.py`'s mechanically-generated `test-architecture.md` for each
of the 8 PyForge stations, per Story 31.1's own Given/When/Then.

## Procedure

1. **Baseline captured** (`python _bmad/scripts/bmad_tea_playwright.py --all`, commit `1363b6c5ca`):
   refreshed all 8 stations' `test-architecture.md` immediately before running TEA, so the
   comparison is against each station's current Story Coverage Matrix + Test Inventory, not a
   stale snapshot.
2. **TEA ran for real** against all 8 stations: `bmad-testarch-test-design`, Create mode, invoked
   via the Skill tool (never `render_skill.py` — steward 46.3 already disclosed that TEA's
   `workflow.yaml`/`instructions.md` format is structurally incompatible with `render_skill.py`'s
   `workflow.md` requirement; these skills are invoked the way Claude Code loads any skill
   natively). Every run hit the same disclosed config gap (`_bmad/tea/config.yaml` does not exist
   in this repo — steward 46.3 stored TEA's answers as an unresolved template in
   `_bmad/custom/config.toml`'s `[modules.tea]` instead) and substituted those values directly, a
   reasonable, disclosed workaround rather than a silent one.
3. **Mode routing**: all 8 stations independently resolved to **System-Level** (each has a PRD +
   architecture set + `epics.md`; step-01's own rule prefers System-Level whenever both exist).
4. **Equivalence check**: for each station, compared TEA's output (`test-design-architecture.md`,
   `test-design-qa.md`, `test-design/<slug>-handoff.md`) against the baseline's **Story Coverage
   Matrix** (every epic story id) and **Test Inventory** (every live test file path).

## Result: narrowed for all 8 stations (0/8 full pass)

TEA's system-level templates (`test-design-architecture-template.md`, `test-design-qa-template.md`,
`test-design-handoff-template.md`) are structurally risk-tiered (P0–P3 priority, P×I-scored risk
registers) — none of the three contains a per-story enumeration. The closest analog, the
handoff's "Risk-to-Story Mapping" table, recommends which epic/story should *own* a risk (a
sparse sample, one row per identified risk) — it does not enumerate every story or every test
file path. This is confirmed empirically across all 8 real runs, not assumed from the templates
alone:

| Station | Baseline stories | Baseline test files | Story ids named in TEA output | Test paths named verbatim | Verdict |
|---|---|---|---|---|---|
| pyforge-marshal | 208 | 181 | 0 (13 risk rows map to epics/parts, never a bare story id) | 0 | **narrowed** |
| pyforge-herald | 50 (epics.md; generator counted 64 — see Observations) | 45 | 10 | 0 | **narrowed** |
| pyforge-atlas | 91 | 129 | 0 (epics/waves/gate names only) | 0 | **narrowed** |
| pyforge-warden | 43 | 64 | ~16 | 0 | **narrowed** |
| pyforge-mason | 61 | 39 | ~15–18 | 0 | **narrowed** |
| pyforge-doctor | 113 (epics.md; generator counted 73 — see Observations) | 61 | ~8–10 | 0 | **narrowed** |
| pyforge-scribe | 19 | 19 | ~5 | 0 | **narrowed** |
| pyforge-steward | 190 | 67 | ~30 | 0 | **narrowed** |

**The generator's own TBD-free invariant** (its hard-fail rule against a delivered placeholder in
`test-architecture.md` itself) **holds trivially for all 8 stations**, since no station's file was
actually regenerated (0/8 equivalence) — the generator's existing output, unchanged, was produced
under that rule at generation time. Separately, a direct `grep -c TBD` across all 32 real
TEA-produced documents (8 stations × 4 files: `test-design-architecture.md`, `test-design-qa.md`,
`test-design/<slug>-handoff.md`, `test-design-progress-system.md`) found 7 literal `TBD` tokens in
2 stations — atlas (`test-design-architecture.md` ×3, `test-design-qa.md` ×1) and herald
(`test-design-qa.md` ×2, `test-design/pyforge-herald-handoff.md` ×1) — all in the templates' own
"owner: TBD" / "recommended owner: TBD" convention for a genuinely-unassigned real-world decision,
not a fabricated content gap (an earlier draft of this report incorrectly claimed 0 everywhere;
corrected after review). Every run is grounded in real PRD/architecture/epics/code content (no
fabricated placeholder *content*, distinct from the legitimate "owner: TBD" convention above) —
the narrowing is a structural template-shape mismatch, not a quality defect in TEA's output or a
run that failed to try.

**Per AD-5/Story 31.1's own escape hatch:** a failing equivalence for any station keeps that
station's generator output and narrows CAP-4 for it, without blocking the story's own completion.
Since all 8 narrow, `test-architecture.md` stays generator-authored for every station — no file
was replaced. TEA's own documents are new, additive artifacts (kept, not discarded — see
Disposition below), each pinned in that station's `.bmad-config.toml` under `[tea]` alongside the
unchanged `test_architecture_writer = "generator"` declaration (AD-9 "one writer, one path
pinned").

## `bmad-testarch-framework` — not invoked live, applicability-checked instead

The story names `bmad-testarch-test-design` / `-framework` together. `bmad-testarch-framework`'s
own `workflow.yaml` states its purpose plainly: initialize a **Playwright or Cypress** JS/TS test
framework (`default_output_file: "{test_dir}/README.md"`, i.e. `tests/README.md`). A repo-wide
scan confirms no station has anything for it to initialize or manage:

- No `playwright.config.*` / `cypress.config.*` exists anywhere in the repo.
- The only two `package.json` files under `src/shared/packages/` are `pyforge-herald/web/`
  (a React dashboard already wired to **Vitest**, not Playwright/Cypress) and
  `pyforge-atlas/wasm/` (DuckDB-WASM build deps, not a testable frontend app).
- `pyforge-atlas` does use Playwright, but via the **Python** binding driven directly from pytest
  (`tests/dashboard/test_dashboard_e2e.py`) — a different usage pattern than the npm-based
  scaffold this skill sets up, and already established.

Running the skill live 8 more times would, per its own applicability gate, report "nothing to
initialize" for every station at real token cost with no new information — a live run was
deliberately not spent on this. Recorded here as the explicit, reasoned finding this story's
own convention requires (not a silent skip).

## Disposition of TEA's new documents

TEA's outputs are real, grounded, and useful in their own right (a risk register + QA coverage
plan is complementary content the mechanical generator never produced) — they are **kept**, not
discarded, at their own default paths:
`planning-artifacts/{test-design-architecture,test-design-qa}.md`,
`planning-artifacts/test-design/<slug>-handoff.md`, and the workflow's own
`test-design-progress-system.md` checkpoint. They are informational additions alongside
`test-architecture.md`, not a replacement for it — Story 31.2 (generator retirement) is refused
for all 8 stations per this report (see that story's own spec).

## Observations (disclosed, not fixed in this story)

- **Marshal's own Story Coverage Matrix is nearly empty independent of TEA:** 207 of 208 rows
  read "none observed" despite 181 real test files existing, because the generator's
  story-to-test-file linkage (`_stories_linked_to_test`) only matches filenames literally
  embedding a story id (e.g. `test_1_2_*`) — a naming convention this repo's tests mostly don't
  follow. This is a pre-existing generator limitation, not a regression from this story; flagged
  by the pyforge-marshal TEA run and confirmed by direct inspection.
- **Herald and Doctor story-count discrepancy:** the generator's own `story_count` (herald 64,
  doctor 73) disagrees with what each TEA run counted directly from `epics.md` (herald 50, doctor
  113 — doctor's run additionally noted 108 of its stories are already `done`/shipped and out of
  its own scope). Not investigated further here (root cause could be either side); a real,
  disclosed discrepancy worth a follow-up if `tea-playwright-check`'s drift gate is ever found
  passing or failing incorrectly for these two stations.

## Verification performed

- `grep -c TBD` on all 32 TEA-produced documents (8 stations × 4 files) — 7 occurrences across 2
  stations (atlas, herald), 0 everywhere else; see the corrected TBD-invariant note above (an
  earlier draft of this section undercounted the file set as 24 and claimed 0 everywhere, both
  wrong — caught by independent review and fixed here).
- Direct `grep -oE` counts of story-id-shaped tokens and literal `tests/.../*.py` path strings in
  every station's TEA output, cross-checked against each subagent's self-reported count (marshal,
  herald, mason verified directly by this story's own author; others cross-checked by spot count).
- `git status` after each run confirmed only the 4 new files per station were created — no
  existing file (`test-architecture.md`, `epics.md`, `sprint-status-ledger.yaml`,
  `implementation-artifacts/`) was modified, and the active project (`pyforge-marshal`) was never
  switched mid-run.
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py::test_bmad_artifacts_integrity` — failed before this pass's classifier fix (5 new pyforge-marshal file shapes were `uncovered`), passes after (see `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py::classify`).
- `pixi run -e pyforge-marshal pyforge-marshal-test` — 7510 passed after all fixes in this pass.
