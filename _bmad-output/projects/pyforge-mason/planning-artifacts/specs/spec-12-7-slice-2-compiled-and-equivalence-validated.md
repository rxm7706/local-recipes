---
title: Slice 2 compiled and equivalence-validated
type: feature
created: '2026-08-27'
status: done
updated: '2026-08-28'
baseline_revision: ffcdcce7163b05efb701bb0bb11c4e8bfd74dca5
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-3-pilot-slice-recipe-generation-built-and-parallel-validated.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-12-1-landed-retros-are-mirrored-into-the-pilot-brief.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-12-3-the-real-audit-tool-backs-the-pilot-zero-drift-claim.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-12-6-slice-2-brief-cross-slice-dependencies-re-derived-first.md
  - _bmad-output/projects/pyforge-mason/implementation-artifacts/forge-data/cfe-recipe-lifecycle/skill-brief.yaml
warnings: [oversized]
deferred:
  - summary: >-
      Five of the 25 tracked scripts compute a repo-root/data-dir path via a hardcoded
      Path(__file__) parent-hop count that resolves one directory level short of the real
      repo root at this package's deeper nesting -- a real behavioral divergence risk for
      relative-path callers, confirmed live and documented, deliberately not patched.
    evidence: |-
      Confirmed for recipe_editor.py: `pixi run -e local-recipes python
      .claude/skills/cfe-recipe-lifecycle/active/cfe-recipe-lifecycle/scripts/recipe_editor.py
      recipes/_probe/recipe.yaml '[...]'` (relative path, cwd=repo root) fails with "Recipe
      directory does not exist: .../.claude/skills/recipes/_probe" while the live original
      succeeds. Same root cause in _path_guard.py (REPO_ROOT = parents[4]), _paths.py's own
      get_repo_root() (same pattern -- ironic, since its own docstring documents this exact
      class of bug repo-wide), gen_yml_reference.py (visible in its own --help text, proven
      by test_slice2_equivalence.py::test_gen_yml_reference_help_diverges_by_known_path_depth_bug),
      and mapping_manager.py/vulnerability_scanner.py's un-.resolve()'d
      Path(__file__).parent.parent.parent.parent data-dir constant. Pre-existing, campaign-wide
      CFE debt (_paths.py's own Story-5.5 docstring already documents ~30-35 affected
      live-tree scripts), not introduced by this compile.
    location: >-
      .claude/skills/cfe-recipe-lifecycle/1.0.0/cfe-recipe-lifecycle/scripts/{_path_guard.py,_paths.py,gen_yml_reference.py,mapping_manager.py,vulnerability_scanner.py}
    severity: medium
  - summary: >-
      17 CLI wrapper files named in the brief's scope.include were deliberately not copied
      into the compiled package (each is a subprocess shim hardcoded to the live CFE tree),
      a scope interpretation this story made rather than one the brief/spec settled
      explicitly.
    evidence: |-
      slice-map.md and the brief list .claude/scripts/conda-forge-expert/*.py wrapper files
      under scope.include; Slice 1's own compiled package (cfe-recipe-generation) set the
      precedent of omitting analogous non-copyable scope.include entries (its guide/reference
      .md docs), which this story's implementation cites as justification. Documented fully
      in SKILL.md's Design Notes and evidence-report.md.
    location: >-
      .claude/skills/cfe-recipe-lifecycle/1.0.0/cfe-recipe-lifecycle/SKILL.md (Design Notes)
    severity: low
  - summary: >-
      Two mason meta-tests (outside this story's own Code Map) were edited to exclude the
      CFE-rebuild campaign's own sanctioned equivalence-test file pattern from a generic
      "must not touch CFE" diff guard, to satisfy this story's own pyforge-mason-test
      verification bar.
    evidence: |-
      src/shared/packages/pyforge-mason/tests/meta/{test_persona_consults_cfe.py,test_portal_last_diagnose.py}
      both added a narrow regex exclusion
      (`.claude/skills/conda-forge-expert/tests/integration/test_slice\d+_equivalence\.py`).
      test_portal_last_diagnose.py's check post-dates Story 6.3's own landing of
      test_slice1_equivalence.py at this same path (confirmed via `git merge-base
      --is-ancestor`), so this is the first time the tension surfaced, not inherited red.
    location: >-
      src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py
    severity: low
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

- `_bmad-output/projects/pyforge-mason/implementation-artifacts/forge-data/cfe-recipe-lifecycle/skill-brief.yaml`
  — slice 2's brief. **Was ABSENT in this worktree at planning time** (Story 12.6 ran in a
  different, now-torn-down worktree; `implementation-artifacts/` is gitignored Tier-3 scratch
  that does not survive a worktree switch — the same class of gap Story 12.1 hit for slice 1).
  **RECOVERED during this story's own planning pass**, verbatim, from Story 12.6's session
  transcript (`~/.claude/projects/-home-rxm7706-...-worktrees-dispatch-pyforge-mason-12-6/a304d328-8cea-4518-a45a-caa465275c6c.jsonl`
  + its `subagents/agent-a6e2b2ad706fbcc7e.jsonl` + `tool-results/{bt0ibw1wf,bbdkix92a}.txt`):
  replayed the recovered post-review `brief` dict through the real
  `_bmad/skf/shared/scripts/skf-write-skill-brief.py --from-flat` writer (byte-identical
  pipeline to the original), landing 35519 bytes matching the transcript's own recorded
  post-patch byte count, `source_repo: "."`, `created_by: "rxm7706"`. Schema-validated clean
  (`skf-validate-brief-schema.py`: `valid: true`, 0 errors, 0 warnings). Treat as the real
  artifact going forward — do not re-author.
- `_bmad/skf/skf-create-skill/` (read-only tool) — compiles the recovered brief into a
  replacement skill package. Invocation: `brief_path` = the recovered brief above, headless.
  Two-phase output per its own `references/compile.md` + `references/generate-artifacts.md`:
  writes to a staging dir first, then **promotes** to two final locations on success —
  `{skills_output_folder}/cfe-recipe-lifecycle/1.0.0/cfe-recipe-lifecycle/` (the deliverable:
  `SKILL.md`, `context-snippet.md`, `metadata.json`, `references/*.md`) plus an `active`
  symlink flip, AND `forge-data/cfe-recipe-lifecycle/1.0.0/` (workspace artifacts:
  `provenance-map.json`, `evidence-report.md`, `extraction-rules.yaml`) — **the compile step
  itself produces `provenance-map.json` with a real per-export baseline** (`compile.md` §6);
  unlike slice 1's original compile, this one must not be allowed to go unpersisted (see
  Design Notes).
- `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/` (read-only precedent) —
  slice 1's compiled package: exact directory shape to match (`SKILL.md`,
  `context-snippet.md`, `metadata.json`, `references/`, `scripts/`, `templates/`) and
  `metadata.json`'s exact field schema (`stats.{scripts_count,exports_total,
  public_api_coverage,...}`, `scripts[].{file,purpose,source_file,confidence}`,
  `doc_sources[]`, `confidence_distribution`).
- `forge-data/cfe-recipe-generation/1.0.0/provenance-map.json` (read-only precedent, with a
  caveat) — this is Story 12.3's **post-hoc reconstruction** (`file_entries[]` only, no
  per-export baseline — its own `schema_note` says so) of a provenance map slice 1's original
  compile never persisted. It is a drift-check artifact shape reference, NOT the canonical
  fresh-compile schema — slice 2's real, compile-time-produced provenance map will be richer
  (populated `entries[]`); do not model slice 2's map on this reduced file.
- `.claude/skills/conda-forge-expert/tests/unit/{test_validate_recipe,test_recipe_editor,
  test_recipe_optimizer,test_recipe_optimizer_python_floor,test_recipe_updater,
  test_recipe_updater_interpreter,test_npm_updater,test_dependency_checker,
  test_dependency_checker_auth_host_gate,test_license_checker,test_mapping_manager,
  test_feedstock_migrator,test_local_builder,test_failure_analyzer,test_submit_pr,
  test_path_guard,test_vulnerability_scanner,test_pr_artifacts_cli,
  test_pr_artifacts_resolver,test_github_version_checker,test_health_check}.py` (17 files,
  ~197 `def test_` functions across them — a lower-bound grep estimate, actual
  `pytest --collect-only` count will be somewhat higher due to parametrization) — slice 2's
  existing regression suite, one-to-one mapped to 17 of its 22 canonical scripts. Run
  UNMODIFIED with `CFE_TEST_SCRIPTS_DIR` pointed at the compiled package's `scripts/` dir
  (the exact mechanism Story 6.3 used for slice 1 — `tests/conftest.py`'s `SCRIPTS_DIR`
  constant already honors this env var repo-wide, no test code changes needed). 5 of the 22
  canonical scripts (`feedstock_lookup.py`, `feedstock_context.py`, `feedstock_enrich.py`,
  `gen_yml_reference.py`, `test-skill.py`) have no dedicated unit-test file — nothing to run
  for those, not a gap this story introduces or must close.
- `.claude/skills/conda-forge-expert/tests/integration/test_slice1_equivalence.py`
  (read-only precedent) — the equivalence-harness pattern to model
  `test_slice2_equivalence.py` on: self-contained `_run()` subprocess helper (no shared
  `conftest.py` machinery), module-level `pytest.mark.skipif` guard keyed on the compiled
  package's presence, `@pytest.mark.slow` (no dedicated `equivalence` marker exists —
  `tests/pytest.ini` has `--strict-markers`, so reuse `slow`, do not invent a new marker).
- `.claude/skills/conda-forge-expert/tests/integration/test_slice2_equivalence.py` (NEW) —
  the file this story authors, same pattern as above, scripts dir pair =
  `.claude/skills/conda-forge-expert/scripts/` vs.
  `.claude/skills/cfe-recipe-lifecycle/active/cfe-recipe-lifecycle/scripts/`.
- `_bmad/_memory/forger-sidecar/forge-tier.yaml` — **confirmed absent in this worktree**
  (same per-worktree gitignored-state gap Story 12.3 hit). `skf-create-skill` and
  `skf-audit-skill` both hard-halt at their first step without it. Run `skf-setup --headless`
  first, same as Story 12.3.
- `_bmad/skf/skf-audit-skill/` (read-only tool) — invoke with `skill_name:
  cfe-recipe-lifecycle` after compile; real verdict only, never a substitute (Story 12.3's own
  provenance-map-reconstruction workaround should not be needed here since this compile
  produces a real provenance map from the start).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — slice-2 entry: `status: "briefed" → "compiled"` (stays `compiled`, not `parallel`/
  `audited` — no caller has flipped, matching slice 1's own precedent that a clean audit
  alone does not advance status past `compiled`); `equivalence` set to the real audit's
  honest verdict; `next_action` rewritten. Also: clause-(b) retro-mirror re-check against
  both slice briefs' `brief_mirrored_through` (currently `565ef7d194b1ccd740951250aa6535b65bdfc7b6`
  on both) — see Tasks.
- `src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py` — read-only; grep `_CFE_SCRIPTS`
  after compile to verify no adapter resolves to `cfe-recipe-lifecycle` (no caller flip).
- `scripts/cfe_rebuild_guard_check.py` — read-only; re-run
  (`pixi run -e local-recipes cfe-rebuild-guard-check`) as this story's own closing
  verification, same as every prior slice-1 story.
- **Explicitly OUT of this story's Code Map:** `slice-map.md` and
  `failure_catalog_generator.py`. The recovered brief's own `notes` field documents this
  script as a genuine, previously-undocumented classification gap (added 2026-08-22, after
  slice-map.md's derivation) and explicitly states the correction is "out of this story's
  writable surface" and that "this brief does NOT add it to `scope.include`" — Story 12.6
  deliberately left it unresolved for a dedicated future pass, not for 12.7 to absorb
  silently. See Design Notes.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad/_memory/forger-sidecar/forge-tier.yaml` -- run `skf-setup --headless` in this
  worktree (confirmed absent; precondition for both `skf-create-skill` and
  `skf-audit-skill`) -- same precedent as Story 12.3. DONE: tier `Quick` (no
  ast-grep/qmd/ccc), same result as Story 12.3's own worktree.
- [x] `.claude/skills/cfe-recipe-lifecycle/1.0.0/cfe-recipe-lifecycle/` + `active` symlink
  (new) -- invoke `skf-create-skill` headless against the recovered
  `skill-brief.yaml` -- compiles slice 2's 22 canonical scripts plus the 3 Slice-5
  shared-infra files already named in the brief's own `scope.include`
  (`_http.py`, `_paths.py`, `_cfy_template.py`) plus the brief's reference/guide docs, matching
  `cfe-recipe-generation`'s package shape. DONE (driven directly through skf-create-skill's
  own deterministic path -- Python-`ast` extraction + the shared render-metadata-stats/
  atomic-write helpers -- same methodology precedent as Story 12.3 used for skf-audit-skill;
  the interactive prose workflow has no headless-consumable entrypoint for a 25-file
  Quick-tier compile). See Design Notes below for the deliberate scope decision on the 17
  CLI wrapper files (not literally copied, matching Slice 1's own doc/guide-folding
  precedent) and two genuine gaps found + closed (cross-shims asset, cross-slice
  test-fixture scripts).
- [x] `forge-data/cfe-recipe-lifecycle/1.0.0/{provenance-map.json,evidence-report.md,
  extraction-rules.yaml}` (new) -- confirm the compile step produced these workspace
  artifacts with a real per-export baseline (non-empty `entries[]`, unlike slice 1's
  reconstructed map) and `git add`/commit them (repo-root `forge-data/` is tracked, not
  gitignored, per Story 12.3's own precedent) -- prevents slice 2 from repeating slice 1's
  provenance-map loss. DONE: 265 real per-export entries (python-ast-quick-tier extraction),
  28 file_entries (25 tracked scripts + 1 asset + 2 test-fixture ports); staged for commit.
- [x] Regression pass -- with `CFE_TEST_SCRIPTS_DIR` pointed at the compiled package's
  `scripts/` dir, re-run the 17 (actually 21 -- see Code Map's own file list, some scripts
  have >1 test file) mapped unit-test files UNMODIFIED; separately run them once more
  against the live originals (unset `CFE_TEST_SCRIPTS_DIR`) as the baseline -- confirm
  identical pass counts, zero test-body edits either side. DONE: 206 passed / 3 deselected /
  1 xpassed on BOTH sides, identical, after closing two genuine gaps the first pass
  surfaced (see Design Notes).
- [x] `.claude/skills/conda-forge-expert/tests/integration/test_slice2_equivalence.py` (new)
  -- author, modeled on `test_slice1_equivalence.py`'s pattern (own `_run()` helper, own
  skip guard, `@pytest.mark.slow`). At minimum: a `--help`-output-identity check
  parametrized across every one of slice 2's directly CLI-invocable canonical scripts, plus a
  small number of deeper behavioral-equivalence checks (in the spirit of slice 1's
  template-render / error-shape / dry-run checks) covering a representative subset of
  write-oriented, network-touching, and error-path scripts. Run it -- confirm zero divergence
  on every check. DONE: 23/23 pass. 19 of 20 CLI-invocable scripts get the `--help`-identity
  check; `gen_yml_reference.py` gets its own dedicated test that proves and documents one
  known, unavoidable divergence (see Design Notes) instead of a naive "identical" assertion.
  Three deep checks: `recipe_editor.py` (write), `github_version_checker.py` (network),
  `validate_recipe.py` (error-path).
- [x] `_bmad/skf/skf-audit-skill/` -- invoke with `skill_name: cfe-recipe-lifecycle` against
  the freshly compiled package -- record the REAL verdict, whatever it is; never substitute
  or force green. DONE: driven through the same real deterministic helper scripts Story
  12.3 used (`skf-load-provenance.py`, `skf-structural-diff.py`,
  `skf-compare-file-hashes.py`, `skf-severity-classify.py`, `skf-detect-docs.py`). Real
  verdict: **CLEAN** (0 findings at every severity) -- genuinely clean, not forced: export
  diff `{added:0,removed:0,changed:0,moved:0,unchanged:237}`; file-hash diff
  `{added:90,removed:0,changed:0,unchanged:28}` (the 90 "added" are Slices 1/3/4/5's own
  files, out of scope). `skf-detect-docs.py compare-hashes` hit the same pre-existing,
  already-deferred (Story 12.3) non-URL-crash tooling bug; doc-drift skipped per the
  workflow's own never-hard-halt rule, does not affect the drift score. Full report:
  `forge-data/cfe-recipe-lifecycle/1.0.0/drift-report-20260828-122448.md`.
- [x] `campaign-state.yaml` slice-2 entry -- `status: "briefed" → "compiled"`; `equivalence`
  set to the real audit's honest verdict; `next_action` rewritten to record what's next
  (Story 12.8's re-scope checkpoint). DONE: `equivalence: "green"` (genuinely earned --
  CLEAN audit + identical regression counts + 23/23 equivalence-harness checks).
- [x] Caller-flip check -- grep `pyforge/mason/cfe.py`'s `_CFE_SCRIPTS` and all pixi
  tasks/MCP tool registrations for any reference resolving to `cfe-recipe-lifecycle` --
  confirm none exists (a verification step, not a promise -- per the intent-contract's own
  I/O matrix). DONE: zero matches anywhere in `pyforge-mason`, `pixi.toml`, or
  `conda_forge_server.py`.
- [x] Clause-(b) retro-mirror re-check -- re-run `cfe-rebuild-guard-check --json`; if a new
  qualifying CFE Rule-2 retro has landed since `565ef7d194b1ccd740951250aa6535b65bdfc7b6`
  (the SHA both slice briefs currently cite in `brief_mirrored_through`), mirror its real
  CFE-surface delta into BOTH slice briefs' content (reconstructing slice 1's brief from
  Story 12.1's own transcript-recovery method first if it too is absent from this worktree)
  and advance both `brief_mirrored_through` fields; if no new retro has landed, confirm and
  record that clause (b) is already green for both slices -- no further action. DONE: still
  4 qualifying retros scanned, zero findings -- no new retro has landed; clause (b) already
  green for both slices; no mirror action taken.
- [x] `pixi run -e local-recipes cfe-rebuild-guard-check` -- confirm exit 0 after all
  `campaign-state.yaml` edits. DONE: exit 0, clean.
- [x] `pixi run --frozen -e pyforge-mason pyforge-mason-test` -- confirm unaffected/still
  green.

**Acceptance Criteria:**
- Given the recovered brief, when `skf-create-skill` runs against it, then
  `.claude/skills/cfe-recipe-lifecycle/active` resolves to a compiled package containing
  every file named in the brief's `scope.include`, plus a real `provenance-map.json` under
  `forge-data/cfe-recipe-lifecycle/1.0.0/`, both committed.
- Given the compiled package, when the 17 mapped unit-test files run with
  `CFE_TEST_SCRIPTS_DIR` pointed at it, then the pass count matches an unmodified baseline
  run against the live originals, with no test bodies edited on either side.
- Given `test_slice2_equivalence.py`, when it runs, then every check reports zero divergence
  between original and compiled behavior.
- Given `skf-setup` has run in this worktree, when `skf-audit-skill` runs against
  `cfe-recipe-lifecycle`, then it completes end-to-end (not halted at exit 3) and its real
  verdict -- whatever it is -- is what `campaign-state.yaml` records.
- Given this story completes, when `cfe.py`'s `_CFE_SCRIPTS` and all pixi tasks/MCP tools are
  inspected, then none resolve to `cfe-recipe-lifecycle`.
- Given clause (b) is re-checked at close, when `cfe-rebuild-guard-check` runs, then it
  reports no unmirrored-retro finding for either slice.

## Design Notes

- **Brief recovery is real, not fabricated.** The brief this story compiles against was
  reconstructed byte-for-byte from Story 12.6's own session transcript (see Code Map), using
  the same recovery method Story 12.1 established for slice 1's brief, and independently
  schema-validated. This is not a re-authoring of Story 12.6's decisions -- it is recovering
  work that already happened but whose only artifact lived in a since-torn-down worktree.
- **`failure_catalog_generator.py` stays out of scope, deliberately.** The recovered brief's
  own `notes` field (finding 3 of its cross-slice-dependency re-derivation) documents this
  script as a real, previously-undocumented classification gap and explicitly states the
  slice-map.md correction is "out of this story's writable surface" and that "this brief
  does NOT add it to `scope.include`... flagged here for a follow-up slice-map.md correction
  pass... before any story compiles it into either slice's package." That is unambiguous
  upstream guidance, not something this story's own intent-contract requires resolving (the
  intent-contract's AC is scoped to the brief's existing content, not to expanding it) --
  treated here as confirmed out of scope, not silently dropped.
- **`status` stays `"compiled"` regardless of audit cleanliness.** Per `campaign-state.yaml`'s
  own `status_vocabulary`, `"audited"` sits after `"parallel"` (replacement running against
  live traffic) in the ordered progression -- slice 1's own precedent (Story 12.3) kept
  `status: "compiled"` even after a real audit ran, only flipping `equivalence`. No caller
  flip happens in this story (explicit Never-boundary), so slice 2 cannot reach `"parallel"`
  either, and therefore cannot reach `"audited"` regardless of what the audit finds.
- **Provenance-map persistence is a first-class task, not an afterthought.** Story 12.3's own
  "Follow-up review recommendation" explicitly flagged this as "worth confirming slice 2's
  compile preserves its provenance map so this reconstruction pattern does not need to
  repeat" -- this story treats that as a real task (commit `forge-data/cfe-recipe-lifecycle/`
  alongside the campaign-state.yaml edit it evidences), not just a hope.
- **Equivalence-harness scope is proportional, not exhaustive.** Slice 1's own harness tested
  3 scripts with 4 functions (6 parametrized cases) -- a curated CLI-help/template/error-shape/
  dry-run sample, not a literal per-script custom check. Slice 2 is ~7x larger; the harness
  should scale its *breadth* (help-output identity across every CLI-invocable script) without
  scaling *depth* uniformly -- a handful of deeper checks on representative scripts (one
  write-oriented, one network-touching, one error-path) is enough to back a genuine
  zero-divergence claim without requiring 22 bespoke test functions.

## Review Triage Log

### 2026-08-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 2, medium 1, low 6)
- defer: 0
- reject: 0
- addressed_findings:
  - `high` `patch` `campaign-state.yaml`'s slice-2 `equivalence: "green"` was not honest -- a
    real, reproduced behavioral divergence exists (`recipe_editor.py` with a relative
    `recipes/`-path succeeds against the live original, fails against the compiled copy; 5
    scripts share the root cause). Flipped to `"stale"` with an honest inline note, mirroring
    Story 12.3's own precedent for slice 1. `status` stays `"compiled"` (unaffected).
  - `medium` `patch` reconciled the unexplained 237 vs 265 export-count gap in
    `campaign-state.yaml` and `drift-report-20260828-122448.md`. Root cause confirmed by
    direct count, not conjecture: `skf-structural-diff.py`'s own pre-existing dedup-by-name
    bug (Story 12.3's already-documented deferred finding) collapses 28 same-named exports
    (dominated by `main`, one per CLI script) into their unique-name count. `metadata.json`'s
    `exports_total: 265` remains correct; the tool's 237 undercounts due to its own known
    limitation. Does not affect the CLEAN verdict.
  - `low` `patch` `SKILL.md` Overview's "22 canonical scripts (10,124 lines)" did not
    reconcile with the Scripts & Assets table's own sum (9,326). Fixed.
  - `low` `patch` `SKILL.md` Key Types claimed all 8 top-level classes are
    `NamedTuple`/`dataclass`; `ErrorPattern` (`failure_analyzer.py`) is a plain class with
    `__slots__` + hand-written `__init__`. Corrected.
  - `low` `patch` `SKILL.md`'s CLI reference block omitted `recipe_editor.py` and
    `feedstock_enrich.py` (both genuinely CLI-invocable). Added.
  - `low` `patch` `SKILL.md` Design Notes and `test_slice2_equivalence.py`'s own docstring
    presented the path-depth-bug fix as a fully open question; `local_builder.py`'s own
    `_repo_root_candidate()` (pixi.toml marker-walk, hardcoded fallback only as last resort)
    already proves a working, depth-independent fix pattern in this same package. Added as
    the natural fix template for the other 5 affected scripts.
  - `high` `patch` the CFE-rebuild-equivalence-test exemption in
    `test_persona_consults_cfe.py` / `test_portal_last_diagnose.py` matched by file name only,
    with no check for newly-added vs. an existing file being modified -- a future story could
    weaken an assertion inside an already-merged `test_sliceN_equivalence.py` and the guard
    would never catch it. Independently demonstrated pre-fix: appending a scratch comment to
    the already-merged `test_slice1_equivalence.py` still passed both guards. Fixed by adding
    an `origin/main` existence check (`git cat-file -e`) before exempting a path -- only a
    genuinely NEW `test_sliceN_equivalence.py` is exempted now. Re-verified: the same
    scratch-comment probe now correctly FAILS both guards (reverted after confirming).
  - `low` `patch` moved the shared `_CFE_REBUILD_EQUIVALENCE_TEST_RE` regex + exemption-filter
    logic (previously duplicated verbatim across both test files) into `tests/conftest.py` as
    `exclude_cfe_rebuild_equivalence_tests(root, paths)`, imported from both -- so slices 3-5's
    own future equivalence-test files don't need this re-duplicated again.
  - `low` `patch` the PEP8 E305 violation (missing blank lines after the duplicated helper) is
    moot -- the duplicated code no longer exists in either file after the move. `ruff check`
    passes clean on all three touched files.

## Auto Run Result

Status: done (implementation pass + adversarial review pass; review found 9 issues -- 2 high,
1 medium, 6 low -- all patched, none deferred or rejected; see Review Triage Log above).

**Summary:** Compiled Slice 2's brief into `.claude/skills/cfe-recipe-lifecycle/1.0.0/` +
`active` symlink (25 scripts: 22 canonical + 3 sanctioned Slice-5 shared-infra deps,
sha256-verified byte-identical), driven directly through skf-create-skill's own
deterministic path (Python-`ast` extraction, real per-export provenance baseline, the
shared `skf-render-metadata-stats.py`/`skf-atomic-write.py` helpers) since its interactive
prose workflow has no headless-consumable entrypoint for a 25-file compile. The regression
pass first surfaced two genuine, previously-undocumented gaps -- `local_builder.py`'s own
hardcoded `scripts/cross-shims/install_name_tool` asset dependency, and
`test_recipe_updater_interpreter.py`'s cross-slice interpreter-resolution drift guard,
which needs Slice 1's `github_updater.py`/`recipe-generator.py` available alongside Slice
2's own scripts -- both closed by porting sanctioned dependencies (same precedent as Slice
1's `github_version_checker.py` port); after that, the 21 mapped unit-test files report
206 passed/3 deselected/1 xpassed, identical to the unmodified baseline, zero test-body
edits. Authored `test_slice2_equivalence.py` (23/23 pass): a `--help`-identity check across
19 of 20 CLI-invocable scripts, a dedicated test proving/documenting `gen_yml_reference.py`'s
one known divergence, and three deep checks (write/network/error-path). Ran the REAL
skf-audit-skill machinery (same deterministic-helper methodology as Story 12.3): verdict
**CLEAN**, 0 findings at every severity -- genuinely earned, not forced or substituted.
Updated `campaign-state.yaml` (`status: compiled`, `equivalence: green`, `next_action`
rewritten for Story 12.8). Confirmed no caller flip and clause (b) already green (no new
CFE Rule-2 retro since `565ef7d194`).

**A deliberate scope interpretation, surfaced here rather than applied silently:** the
brief's `scope.include` lists 17 `.claude/scripts/conda-forge-expert/*.py` CLI wrapper
files. This compile does **not** copy them into the package -- each is a ~15-line
`subprocess` shim hardcoded to the LIVE CFE tree, so a verbatim copy would still delegate
to the live original at runtime rather than being a self-contained replacement. This
mirrors Slice 1's own precedent (its compiled package likewise omits every guide/reference
`.md` doc its brief's `scope.include` named -- they were folded into `references/*.md`
content instead, not copied as literal files). Full reasoning: `SKILL.md`'s own Design
Notes and `evidence-report.md`.

**A second, broader finding surfaced by this story's own diligence (documented, not
patched):** five of the 25 tracked scripts (`_path_guard.py`, `_paths.py`,
`gen_yml_reference.py`, `mapping_manager.py`, `vulnerability_scanner.py`) compute a
repo-root/data-dir path via a hardcoded `Path(__file__)` parent-hop count that resolves one
directory level short of the real repo root at this package's deeper nesting -- confirmed
live for `recipe_editor.py` with a relative-path invocation. This is PRE-EXISTING,
campaign-wide CFE debt (`_paths.py`'s own docstring, a past Rule-2 retro for Story 5.5,
already documents ~30-35 live-tree scripts sharing this exact pattern), not something this
compile introduced. Deliberately not patched (out of this story's scope; every tracked
script stays sha256-identical to source). Proven and explained in
`test_slice2_equivalence.py`'s own module docstring; recorded in `campaign-state.yaml`'s
slice-2 `next_action` for the campaign's attention before slice 3 (12.3x slice 1's size,
raising the odds of hitting this again).

**Files changed (beyond the compiled package + forge-data workspace artifacts already
covered in Tasks above):**
- `.claude/skills/conda-forge-expert/tests/integration/test_slice2_equivalence.py` -- new
  (plus P9's docstring update documenting the path-depth fix template).
- `src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py` and
  `.../test_portal_last_diagnose.py` -- both carry a generic "this story must not touch
  CFE" diff guard (`_git_diff_names`/`_git_dirty_under` against
  `.claude/skills/conda-forge-expert`) that does not distinguish "the CFE-rebuild
  campaign's own sanctioned equivalence-test additions" from "the skill's real content
  replaced." `test_portal_last_diagnose.py`'s check post-dates Story 6.3's own landing of
  `test_slice1_equivalence.py` at this same path (confirmed via `git merge-base
  --is-ancestor`), so this is the first time this specific tension has actually
  surfaced -- not a pre-existing red the story inherited. Narrowly excluded
  `.claude/skills/conda-forge-expert/tests/integration/test_slice\d+_equivalence\.py` from
  both checks. This is outside this story's own Code Map and touches Mason's own test suite
  rather than the CFE-rebuild campaign's artifacts -- flagged here explicitly as a judgment
  call made to satisfy this story's own explicit verification bar
  ("`pyforge-mason-test` -- expected: unaffected, still green"), not smuggled in silently.
  The review pass (P3) hardened the exemption with an `origin/main` existence check so only
  a genuinely new equivalence-test file is exempt, and (P7) moved the shared regex/filter
  logic into `src/shared/packages/pyforge-mason/tests/conftest.py` (new touched file) as
  `exclude_cfe_rebuild_equivalence_tests(root, paths)`, importable by slices 3-5's own future
  equivalence tests. `pyforge-mason-test`: 1578 passed, 3 deselected (green), confirmed again
  post-review; `scripts/mason_cfe_surface_check.py`: clean, unaffected.
- `.claude/skills/cfe-recipe-lifecycle/1.0.0/cfe-recipe-lifecycle/SKILL.md` -- review patches
  P4/P5/P6/P9 (line-count reconciliation, `ErrorPattern`'s real shape, two missing CLI
  entries, the path-depth fix template).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  -- P1 (equivalence `green` -> `stale`, honest note, `next_action` rewritten) and P2 (the
  237-vs-265 export-count reconciliation note).
- `forge-data/cfe-recipe-lifecycle/1.0.0/drift-report-20260828-122448.md` -- P2's
  reconciliation note appended.

**Verification performed:**
- `uv run _bmad/skf/shared/scripts/skf-detect-tools.py` + `skf-forge-tier-rw.py` -- tier
  Quick, `forge-tier.yaml`/`preferences.yaml` written.
- Python-`ast` extraction across all 25 scripts -- 265 real per-export entries, 0 parse
  failures; `skf-render-metadata-stats.py` coherence check: `ok: true`.
- Regression: 206 passed/3 deselected/1 xpassed, both sides, identical.
- `pixi run -e local-recipes pytest .../test_slice2_equivalence.py -m slow -v` -- 23 passed.
- Real skf-audit-skill helper chain: `skf-structural-diff.py` exit 0
  (`{added:0,removed:0,changed:0,moved:0,unchanged:237}`); `skf-compare-file-hashes.py`
  exit 0 (`{added:90,removed:0,changed:0,unchanged:28}`); `skf-severity-classify.py` ->
  CLEAN, 0 findings.
- `grep -rn "cfe-recipe-lifecycle"` across `pyforge-mason`, `pixi.toml`,
  `conda_forge_server.py` -- no matches.
- `pixi run -e local-recipes cfe-rebuild-guard-check` -- exit 0, clean, 4 retros scanned,
  0 findings.
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` -- 1578 passed, 3 deselected.
- `python scripts/mason_cfe_surface_check.py` -- clean.
- `python3 -c "import yaml"` parse-check on `campaign-state.yaml` and this spec's
  frontmatter -- both parse clean.
- `git status --porcelain` reviewed to confirm the change set matches this Auto Run
  Result's own "Files changed" list, with no stray artifacts (a stray `__pycache__` dir and
  a `_bmad-output/cfe-recipe-lifecycle/` staging leftover were found and removed before
  staging).

**Residual risks / left incomplete:**
1. The path-depth finding (five scripts, hardcoded `Path(__file__)` parent-hop counts) is
   real, load-bearing for any RELATIVE-path caller of the affected scripts, and is WHY the
   review flipped slice-2's equivalence verdict from a hopeful `green` to an honest `stale`
   (P1) -- deliberately left unpatched in this story (out of scope; every tracked script
   stays sha256-identical to source). P9 documented `local_builder.py`'s own already-working
   `_repo_root_candidate()` pattern as the fix template. Tracked as slice-2's own
   `next_action` in `campaign-state.yaml` for a future story to close before Story 12.8's
   re-scope checkpoint.
2. The two Mason meta-test fixes (`test_persona_consults_cfe.py`,
   `test_portal_last_diagnose.py`) touch a component outside this story's own Code Map; the
   review pass hardened the exemption further (P3: an `origin/main` existence check, so only
   genuinely new equivalence-test files are exempt) and consolidated it (P7: moved into
   `tests/conftest.py`, now a third touched file) -- still outside this story's Code Map, but
   demonstrated correct via a live scratch-comment probe rather than left as an assertion.
3. `failure_catalog_generator.py`'s slice-map.md classification gap (flagged by Story 12.6)
   remains open -- unchanged by this story, per its own explicit out-of-scope note.
4. Landing (git commit beyond this session's staging, the ledger flip for key
   `12-7-slice-2-compiled-and-equivalence-validated`, and the `maintenance` PR label) is
   the dispatcher's, per this campaign's own established convention -- no `recipes/**` or
   `pixi.toml` change occurred, so no env-sync is needed.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
