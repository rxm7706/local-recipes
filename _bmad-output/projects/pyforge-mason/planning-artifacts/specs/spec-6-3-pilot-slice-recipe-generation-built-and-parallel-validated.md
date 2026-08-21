---
title: 'Story 6.3 — Pilot slice: recipe generation, built and parallel-validated'
type: 'feature'
created: '2026-08-21'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
difficulty: 'L'
baseline_revision: 'c4402271c5ccac501a6121bd4f60d0a036d338ca'
---

<intent-contract>

## Intent

**Problem:** Epic 6's CAP-2 (the pilot slice) is unrealized: the recipe-generation slice
(`recipe-generator.py` + satellites, its MCP tools, wrappers, and knowledge) has no
Skill-Forge-compiled replacement, so the campaign has never proven the toolchain end-to-end on
real code, and `campaign-state.yaml`'s slice-1 entry sits at `status: mapped` with every
Story-6.2 guard field still at its inert default.

**Approach:** Run the real Skill-Forge toolchain (`skf-brief-skill` → `skf-create-skill` →
`skf-audit-skill`) against slice-1's exact scope, then prove equivalence two ways: the slice's
existing 60 regression tests run unmodified against the compiled replacement's copied scripts,
and a new equivalence harness runs both copies against a shared fixture corpus and asserts
identical output. Advance `campaign-state.yaml`'s slice-1 entry to `status: audited` with a real
`equivalence: "green"` result once all five CAP-2 success clauses hold. The live original stays
authoritative throughout; no caller (Mason's `cfe.py`, pixi tasks, MCP tools) changes what it
resolves to.

## Boundaries & Constraints

**Always:**
- Scope is exactly Slice 1 per `slice-map.md` § "Slice 1: Recipe Generation": canonical
  scripts `recipe-generator.py`, `name_resolver.py`, `github_updater.py`
  (`.claude/skills/conda-forge-expert/scripts/`); MCP tools `generate_recipe_from_pypi`,
  `update_recipe_from_github`, `get_conda_name`; wrappers `generate-recipe` (+ `-cran`/`-cpan`/
  `-luarocks`/`-npm`), `resolve-name`, `autotick-github`; knowledge G54 (SKILL.md:3006), G91
  (SKILL.md:3721), G94's third sub-item (SKILL.md:3755 / `recipe-generator.py:2490`'s own
  `# G94c` shorthand comment — no separate "G94c" ID exists in SKILL.md itself), G98
  (SKILL.md:3790), the CFE-block emission contract (`_render_cfe_block()`), plus
  `reference/recipe-yaml-reference.md`, `reference/meta-yaml-reference.md`,
  `reference/jinja-functions.md`, `guides/getting-started.md`.
- Invoke `skf-brief-skill` with `target_repo` = this repo, scoped via `include`/`exclude` globs
  (or `scope_type: specific-modules`) to exactly the files above — do not let it onboard the
  whole `conda-forge-expert` skill.
- Invoke `skf-create-skill` from the resulting brief. Per its own documented behavior
  (`skf-create-skill/references/generate-artifacts.md` § "Files 4b"), when `scripts_inventory`
  is non-empty the compiled skill package's `scripts/*` are **copied from source with content
  preserved** — the three slice-1 scripts land in the new package byte-identical to their
  originals. This is not a from-scratch reimplementation; treat that as the correct, expected
  outcome, not a shortfall to work around.
- CAP-2's success bar is all five of: (1) `skf-brief-skill` produces the brief with the gotchas
  above as verbatim inputs; (2) `skf-create-skill` compiles the replacement package; (3) the
  slice's existing regression tests — `.claude/skills/conda-forge-expert/tests/unit/
  test_recipe_generator.py` (53 tests), `test_name_resolver.py` (5 tests),
  `test_github_updater.py` (2 tests), 60 total — pass **with their test-function bodies and
  assertions completely untouched** when pointed at the compiled replacement's copied scripts
  (a shared-fixture indirection change, e.g. making `tests/conftest.py`'s `SCRIPTS_DIR`
  resolution overridable via an environment variable, is in scope and does not count as
  "rewriting expectations" — the assertions and inputs inside each test function must not
  change); (4) a new equivalence harness runs both the original and the compiled-replacement
  copies of the three scripts against the same fixture corpus and asserts identical output
  (model its shape on `src/shared/packages/pyforge-mason/tests/integration/
  test_delegation_fidelity.py` — `@pytest.mark.slow`, skip cleanly if a needed input is
  unavailable, real subprocess/import calls rather than mocks); (5) `skf-audit-skill` run
  against the compiled package reports zero drift. All five must hold before slice-1 advances
  past `compiled` in `campaign-state.yaml`.
- Only after all five hold: set slice-1's `status: audited`, `equivalence: "green"`,
  `brief_path: <path to the produced skill-brief.yaml>` in `campaign-state.yaml`, and run
  `pixi run -e local-recipes cfe-rebuild-guard-check` to confirm it stays clean (clause (a) now
  reads a real `audited` status, so it must find a real `green` equivalence value or it reds).
- The live original CFE skill remains the sole thing every caller resolves to. Nothing under
  `.claude/tools/conda_forge_server.py`, `src/shared/packages/pyforge-mason/`, or any pixi task
  changes what path it invokes.

**Block If:**
- If `skf-brief-skill` or `skf-create-skill`, when actually invoked against this scope, cannot
  produce a usable brief/package for a reason intrinsic to the tooling (not a scoping mistake
  fixable by adjusting include/exclude globs) — HALT with status `blocked`, blocking condition
  `intent gaps`, and report exactly what the tool reported.
- If any of the 60 existing regression tests do not pass against the compiled replacement's
  copied scripts for a reason that traces to the copy being non-identical (i.e., `skf-create-skill`
  did not in fact preserve content byte-for-byte as its own documentation states) — this is a
  genuine tooling discrepancy, not something to patch around by editing test expectations; HALT
  and report it rather than weakening the "unmodified" requirement.

**Never:**
- Never edit a test function's body, assertions, or inputs in any of the three existing test
  files to make it pass against the replacement — only fixture/conftest indirection may change.
- Never flip any caller to the replacement, retire any legacy code, or touch
  `.claude/skills/conda-forge-expert/scripts/**` (the originals) beyond what `skf-brief-skill`/
  `skf-create-skill` read (read-only from their perspective).
- Never advance slice-1's `campaign-state.yaml` status past `compiled` while any of the five
  CAP-2 success clauses is unmet — a partial pass must leave the recorded status honest (e.g.
  `compiled` with `equivalence: null`, not `parallel`/`audited` with a fabricated `green`).
- Never touch `cfe_rebuild_guard_check.py`'s clause logic itself — this story populates the
  fields that detector already reads; it does not change the detector.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Full CAP-2 pass | brief produced, package compiled, 60 tests green against the copy, equivalence harness zero-divergence, skf-audit-skill zero-drift | `campaign-state.yaml` slice-1: `status: audited`, `equivalence: "green"`, `brief_path` set | — |
| Skill-Forge tooling cannot compile this scope | a tool-intrinsic failure, not a scoping error | HALT `blocked`, `intent gaps`, exact tool output quoted | — |
| Existing tests fail against the copy | a real behavioral or import-path defect surfaces | Fix the import/fixture indirection if the defect is in this story's own conftest change; if the defect traces to the copy itself not being content-identical, HALT and report — do not edit test assertions | — |
| Equivalence harness cannot run (missing input) | e.g. no network / no fixture corpus material available | Skip cleanly (`pytest.mark.slow` + a skip guard), same as `test_delegation_fidelity.py`'s pattern — not a hard failure of the whole story, but CAP-2 clause (4) is then unmet and slice-1 must not advance past `compiled` | — |

</intent-contract>

## Code Map

- `.claude/skills/conda-forge-expert/scripts/{recipe-generator,name_resolver,github_updater}.py` -- read-only source for the Skill-Forge brief/compile.
- `.claude/skills/conda-forge-expert/SKILL.md`, `reference/*.md`, `guides/getting-started.md` -- read-only knowledge source (G54/G91/G94-third-subitem/G98 + reference docs).
- `{forge_data_folder}/<skill-name>/skill-brief.yaml` -- produced by `skf-brief-skill` (exact path per its own Outputs contract).
- `{skills_output_folder}/<skill-name>/<version>/<skill-name>/` -- produced by `skf-create-skill`: `SKILL.md`, `references/*.md`, `scripts/*` (copied slice-1 scripts), `metadata.json`, etc.
- `.claude/skills/conda-forge-expert/tests/conftest.py` -- `SCRIPTS_DIR` resolution made overridable so the existing tests can point at the compiled replacement's copy without editing test bodies.
- `.claude/skills/conda-forge-expert/tests/unit/{test_recipe_generator,test_name_resolver,test_github_updater}.py` -- run unmodified against both script locations; not edited.
- New equivalence-harness test file (path/name TBD by the implementer, modeled on `src/shared/packages/pyforge-mason/tests/integration/test_delegation_fidelity.py`) -- runs old vs. compiled-copy against a shared corpus, asserts identical output.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml` -- slice-1's status/equivalence/brief_path updated once all five clauses hold.

## Tasks & Acceptance

**Execution:**
- [x] Invoke `skf-brief-skill` (skill_name kebab-case, e.g. `cfe-recipe-generation`; `include`/`exclude` or `scope_type: specific-modules` scoped to exactly the slice-1 files/knowledge listed above) -- produces `skill-brief.yaml` with the gotchas as verbatim inputs -- CAP-2 clause 1 -- DONE
- [x] Invoke `skf-create-skill` against that brief -- produces the compiled skill package (SKILL.md + references/ + scripts/ with the 3 scripts copied content-preserved) -- CAP-2 clause 2 -- DONE (`.claude/skills/cfe-recipe-generation/1.0.0/`, scripts sha256-verified byte-identical)
- [x] `.claude/skills/conda-forge-expert/tests/conftest.py` -- make `SCRIPTS_DIR` overridable (env var, default unchanged) -- lets the existing tests point at the compiled copy without editing test bodies -- DONE (`CFE_TEST_SCRIPTS_DIR`)
- [ ] Run the 3 existing test files (unmodified) against the compiled replacement's copied scripts, confirm all 60 pass -- CAP-2 clause 3 -- **BLOCKED: 59/60 pass.** `test_github_updater.py::test_dry_run_live_against_actionlint` fails: `github_updater.py` (Slice 1) has a hard runtime import of `github_version_checker.py`, which `slice-map.md` classifies as Slice 2 canonical -- outside this story's "exactly Slice 1" scope boundary. Independently re-verified by re-running both test passes myself.
- [x] New equivalence-harness test -- runs both script copies against a shared fixture corpus, asserts identical output, `@pytest.mark.slow`, skips cleanly if a needed input is unavailable -- CAP-2 clause 4 -- DONE, but honestly reports the one known divergence above rather than a false zero (`test_slice1_equivalence.py`, 6/6 pass, independently re-run)
- [x] Invoke `skf-audit-skill` against the compiled package, confirm zero drift -- CAP-2 clause 5 -- DONE (clean, 0 findings, after a self-inflicted provenance gap was found and fixed)
- [x] `campaign-state.yaml` -- record the real, honest outcome -- DONE: slice-1 left at `status: "compiled"`, `equivalence: null` (NOT advanced to `parallel`/`audited`/`"green"`, since clause 3 is unmet) -- independently re-verified against the actual diff
- [x] `pixi run -e local-recipes cfe-rebuild-guard-check` -- confirm still clean after the status change -- DONE, independently re-run: exit 0

**Acceptance Criteria:**
- Given the slice-1 scope, when `skf-brief-skill` runs, then `skill-brief.yaml` exists and cites G54/G91/G94's third sub-item/G98 among its inputs.
- Given that brief, when `skf-create-skill` runs, then the compiled package's `scripts/` contains the three slice-1 scripts byte-identical to their originals.
- Given the compiled package, when the 3 existing test files run against it (test bodies unmodified) using the conftest override, then all 60 pass.
- Given the same fixture corpus run through both script locations, when the equivalence harness runs, then it reports zero divergence (or skips cleanly per the Edge-Case Matrix, in which case slice-1 does not advance past `compiled`).
- Given the compiled package, when `skf-audit-skill` runs, then it reports zero drift.
- Given all five clauses hold, when `campaign-state.yaml` is updated, then `cfe-rebuild-guard-check` still exits 0.
- Given this story completes, when any caller (`cfe.py`, pixi tasks, MCP tools) is inspected, then none resolve to the replacement -- the live original remains authoritative.

## Design Notes

`skf-create-skill`'s own documentation (`references/generate-artifacts.md` § "Files 4b") states
detected scripts are copied into the compiled package "with content preserved" -- this resolves
what would otherwise be a serious ambiguity in CAP-2's "existing regression tests pass unmodified
against the replacement" clause: since the replacement's scripts are byte-identical copies (not
an independent reimplementation), "the replacement passes the same tests" is a claim about the
*packaging and import path* being interchangeable, not a claim about a from-scratch Skill-Forge
rewrite matching 2,332 lines of hand-authored logic. Treat this as settled, verified fact (quoted
above), not as an assumption -- it is why this story is tractable as a single Effort:L unit rather
than a multi-story reimplementation effort.

The equivalence harness therefore does not need to prove deep behavioral equivalence between two
independently-written implementations -- it proves the copy operation didn't silently diverge the
two locations, using the same "run both, diff the result" shape `test_delegation_fidelity.py`
already established for a structurally similar (though not identical) old-path-vs-new-path
comparison in this repo.

## Spec Change Log

None — initial draft.

## Review Triage Log

## Verification

**Commands:**
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit/test_recipe_generator.py .claude/skills/conda-forge-expert/tests/unit/test_name_resolver.py .claude/skills/conda-forge-expert/tests/unit/test_github_updater.py -v` -- expected: 60 pass, run first against the original (baseline) then again with the conftest override pointed at the compiled copy
- `pixi run -e local-recipes pytest -m slow -k equivalence -v` (or the equivalent path to the new harness test) -- expected: pass or clean skip
- `pixi run -e local-recipes cfe-rebuild-guard-check` -- expected: exit 0 both before (slice-1 still `mapped`/`compiled`, clause (a) not gated) and after (slice-1 `audited`, `equivalence: "green"`) the campaign-state.yaml update
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` -- expected: unaffected, still green

## Auto Run Result

Status: blocked

Blocking condition: implementation verification failed -- 2 of CAP-2's 5 mandatory success
clauses are genuinely unmet, and the missing work cannot be completed without violating this
story's own scope boundary ("exactly Slice 1").

**Root cause (independently re-verified, not just trusted from the implementation pass):**
`github_updater.py` (a Slice-1 canonical script) has a hard runtime import of
`github_version_checker.py`. `slice-map.md` (Story 6.1's own deliverable) classifies
`github_version_checker.py` as a **Slice 2** ("Recipe Lifecycle") canonical script (confirmed:
`grep github_version_checker slice-map.md` lines 205/212 list it under Slice 2's canonical-scripts
table) -- unlike `_cfy_template.py` (Slice 5), which slice-map.md already documented as a sanctioned
Slice-1 cross-slice dependency. This is a **previously undocumented gap in Story 6.1's own
cross-slice-dependency inventory**, discovered by Story 6.3's actual engineering work -- exactly
what a pilot slice is for. Pulling `github_version_checker.py` into the compiled Slice-1 package
would silently expand this story's scope past what CAP-2/the slice map sanction; the story's own
"Never" boundary forbids it.

**Concretely, this leaves:**
- CAP-2 clause 3 (all 60 existing tests pass unmodified against the replacement): **59/60**
  (`test_github_updater.py::test_dry_run_live_against_actionlint` fails with `"github_version_checker.py
  could not be imported"` against the compiled copy; independently re-run and confirmed).
- CAP-2 clause 4 (equivalence harness reports zero divergence): the harness runs (6/6 tests pass)
  but **honestly asserts the one known divergence** rather than reporting a false zero
  (`test_slice1_equivalence.py::test_github_updater_known_cross_slice_gap`).
- CAP-2 clauses 1, 2, and 5 (brief cites gotchas; package compiled with the in-scope scripts
  byte-identical; `skf-audit-skill` reports clean/zero-drift) are genuinely met.

**What was NOT done and could not be done within scope:** advancing `campaign-state.yaml`'s
slice-1 entry past `status: "compiled"` to `parallel`/`audited` with `equivalence: "green"` --
doing so would misrepresent an unmet clause as met, which `scripts/cfe_rebuild_guard_check.py`
(Story 6.2) exists specifically to catch. The file is left honest: `status: "compiled"`,
`equivalence: null`, with a full explanation inline and a `next_action` framing the two real
options (port `github_version_checker.py` as a sanctioned Slice-1 dependency like
`_cfy_template.py`, or accept the gap and re-scope CAP-2's bar) for a future story or human
decision -- this story does not pick one, since that is exactly a "decision requiring human
input" per its own `<intent-contract>` boundaries.

**What genuinely landed (real, verified, not built on any false premise):**
- `.claude/skills/cfe-recipe-generation/1.0.0/` -- a real, Skill-Forge-compiled skill package;
  its 3 slice-1 scripts plus 2 legitimately in-scope runtime dependencies (`_cfy_template.py`,
  already sanctioned by slice-map.md; 7 `templates/` files `copy_template()` needs, previously
  untracked by slice-map.md at all) are sha256-verified byte-identical to their originals.
- `.claude/skills/conda-forge-expert/tests/conftest.py` -- a 5-line, additive-only change
  (`SCRIPTS_DIR` overridable via `CFE_TEST_SCRIPTS_DIR`, default unchanged); the three existing
  test files' function bodies/assertions are confirmed byte-for-byte untouched.
- `.claude/skills/conda-forge-expert/tests/integration/test_slice1_equivalence.py` -- 6 new
  tests, real subprocess/import calls, `@pytest.mark.slow`, independently re-run and passing.
- No caller changed what it resolves to -- confirmed via `git diff --stat` on
  `.claude/tools/conda_forge_server.py`, `src/shared/packages/pyforge-mason/`, and `pixi.toml`:
  no changes.
- `pixi run --frozen -e pyforge-mason pyforge-mason-test`: 1534 passed, 3 deselected, unaffected.

**Verification performed:** every claim above was independently re-run by the orchestrating
agent (not just trusted from the implementation subagent's report) -- both test-suite passes
(original and compiled-copy), the equivalence harness, `cfe-rebuild-guard-check` (exit 0), the
`slice-map.md` cross-check for `github_version_checker.py`'s Slice-2 classification, and a
`git diff --stat` scope check for caller-flip absence.

**Follow-up recommendation:** `followup_review_recommended` left `false` -- this is a blocked
HALT, not a `done` completion; no review-loop pass ran (step-04 is never reached from a
step-03 verification-failed HALT). A human or a future story should decide the
`github_version_checker.py` question named in `campaign-state.yaml`'s `next_action` before any
further CAP-2 work proceeds.
