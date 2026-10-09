---
title: "25.3: CFE gains a tracked bulk recipe-refresh driver that the refresh waves run through"
type: 'feature'
created: '2026-10-09'
status: 'ready-for-dev'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - docs/specs/feedstock-refresh.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/recipe_updater.py
  - .claude/skills/conda-forge-expert/scripts/recipe_editor.py
  - .claude/skills/conda-forge-expert/scripts/feedstock_lookup.py
  - .claude/skills/conda-forge-expert/scripts/feedstock_enrich.py
  - .claude/skills/conda-forge-expert/scripts/_path_guard.py
  - .claude/skills/conda-forge-expert/scripts/_paths.py
  - .claude/skills/conda-forge-expert/scripts/mcp_parity.py
  - .claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-1-track-a-s-wave-h-refreshes-the-sole-maintainer-recipes-the-first-waves-missed.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.1 (Track A, Wave H) refreshed 92 sole-maintainer recipes with scripts that were never committed:
`wave_h_rebaseline.py`, `wave_h_bump.py`, `wave_h_bump_any.py`, `wave_h_batch789_process.sh`,
`wave_h_run_batches_10plus.sh` and `wave_h_stamp.py`, all under `.cursor/` in its dispatch worktree
(`spec-25-1-…md:157`, `:193`). Story 25.2 (Track B, co-maintained) stopped `blocked` after Wave A. It queued 96
v1-refresh recipes. Its pilot through CFE's autotick failed on `recipes/billiard/recipe.yaml` with "Could not
determine package name and version from recipe context". Its spec records that no batch driver exists in the repo
(branch `origin/dispatch/pyforge-mason/25.2`, `spec-25-2-…md:16-34`, `:208-214`). The autotick path reads the name
only from `context.name` (`recipe_updater.py:86-91`). Recipes generated since CFE v8.10.0 carry a literal
`package.name` and no `context.name`.

The untracked scripts also caused four defects in 25.1's landing (`f1402da5d4`):

- **A v0 feedstock's `meta.yaml` was hidden.** `wave_h_batch789_process.sh` renamed `meta.yaml` to
  `.meta.yaml.wave_h_hold` (`:33-37`), restored it only after the build (`:55-57`), and exited on a failed validate
  or check-deps before the restore (`:24-30`). `recipes/wasmtime-py/meta.yaml` is now `.meta.yaml.wave_h_hold`
  (rename `R100` in `8b27631ec5`). Its feedstock is still v0: `recipe/` holds only `meta.yaml` (`gh api` GET,
  2026-10-09), and `recipes/wasmtime-py/recipe.yaml:76-78` records that. This breaks 25.1's own C1 rule.
- **56 `recipe.yaml` files got hashed PyPI URLs.** Their `${{ version }}`-templated
  `https://pypi.org/packages/source/…` URL became a hashed `https://files.pythonhosted.org/packages/<hash>/…` URL,
  for example `recipes/django-todo/recipe.yaml:13`. `wave_h_bump.py:44-47` writes PyPI JSON's `url` field. This
  breaks CFE's critical constraint at `SKILL.md:150`.
- **78 of the 92 `recipe.yaml` diffs re-indent lists.** List items moved to their parent key's depth (FMT-001).
  The scripts dumped with ruamel's default indent. `recipe_editor.py:93-101` already sets the canonical indent and
  width.
- **The CFE version carriers broke lockstep.** CFE `SKILL.md:10` and `CHANGELOG.md:5` moved to 8.97.1, while
  `MANIFEST.yaml:15` and `config/skill-config.yaml:6` stayed at 8.97.0. Story 22.1's branch
  (`dispatch/pyforge-mason/22.1` at `192e6843a4`) carries all four at 8.98.0 and restores lockstep when it lands.

These are recorded as context. This story fixes none of them in `recipes/`: the driver only stops them recurring.

**Approach:** add one tracked CFE script, `refresh_wave.py`, under the three-place rule. It reads a wave manifest and
refreshes each recipe to its feedstock's published version through CFE's existing edit path (`recipe_editor`). It
reads feedstocks through `feedstock_lookup` (`gh api` GET only) and merges maintainers through
`feedstock_enrich._merge_maintainers` (G53). It writes a wave report. It is dry-run by default, resumable, and
idempotent. The same commit fixes `recipe_updater.get_current_recipe_info` so the autotick path can read a recipe that
has no `context.name`.

Ledger key: `25-3-cfe-gains-a-tracked-bulk-recipe-refresh-driver-that-the-refresh-waves-run-through`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57): the refresh campaign whose waves run through this driver.
- `spec-pyforge-mason` CAP-20 (← `spec-fleet-stewardship` CAP-3): refresh runs as parameterized waves. A wave
  manifest is that parameter.
- `spec-pyforge-mason` CAP-23 (← `spec-packaging-factory` CAP-1): the recipe lifecycle machinery the driver extends.
- No new CAP, so no FR moves (decision recorded on the `spec-pyforge-mason` memlog, 2026-10-09). Precedent: Story 16.3
  added CFE scripts (`mcp_tools.py`, `mcp_parity.py`) under the governing Spec's CAP with no mint.
- AD-1: Mason's code carries no recipe knowledge, and this story touches no Mason code. AD-15: the CFE surface moves
  only in the `retro(cfe):` commit.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`. The driver is recipe-factory tooling run by
  an operator over `recipes/`. It is not a runtime capability of any station or of the platform.

## Contract

**Three places** (`docs/reference/agent-instruction-notes.md:409`):

1. `.claude/skills/conda-forge-expert/scripts/refresh_wave.py`, the implementation.
2. `.claude/scripts/conda-forge-expert/refresh_wave.py`, a thin wrapper that delegates entirely, shaped like
   `recipe_updater.py`'s wrapper.
3. `[feature.local-recipes.tasks.refresh-wave]` in `pixi.toml`, with `cmd = "python
   .claude/scripts/conda-forge-expert/refresh_wave.py"`, plus a `"refresh_wave.py"` entry in `SCRIPTS`
   (`tests/meta/test_all_scripts_runnable.py:12`).

It also needs a `CLI_ONLY_VERBS["refresh-wave"]` entry with a one-line reason in `scripts/mcp_parity.py:29`, so
`test_cli_tool_parity.py` stays green. The driver is an attended operator task, not an MCP tool.

**Manifest** (YAML or JSON):

```yaml
schema_version: 1
track: B            # A (sole-maintainer) | B (co-maintained)
wave: B1            # free-form wave id; names the report folder
recipes:
  - name: billiard  # recipes/<name>/, checked with _path_guard.validate_recipe_name
    feedstock: billiard   # optional; conda-forge/<feedstock>-feedstock; default: name
    version: "4.2.4"      # optional; the published version; default: the feedstock recipe's own version
```

An unknown key, a bad `track`, or a name `_path_guard` refuses is a manifest error: exit 2, nothing written.

**CLI:** `refresh-wave MANIFEST [--apply] [--gates] [--build] [--report-dir DIR] [--force] [--json]`.

- Without `--apply`, the run is a dry-run. It reads, plans and writes only the report. Gates and builds run only with
  `--apply`.
- The default report directory comes from `_paths.get_data_dir()`:
  `.claude/data/conda-forge-expert/refresh-waves/<track>-<wave>/`, which is gitignored (`.gitignore:742`).
  A `--report-dir` under `recipes/` is refused.

**Per recipe**, in order:

1. Read the local `recipes/<name>/`, and the feedstock through `feedstock_lookup` (format, version, maintainers,
   source sha256).
2. **Target version.** It is the manifest version, or else the feedstock's.
   - Local version ≥ target: `already-current`, and nothing is written.
   - A version that does not compare as PEP 440, or a feedstock tag that differs from the published version
     (landmine 1): `needs-review`.
3. **Shape.**
   - Feedstock v0 (only `recipe/meta.yaml`), C1: the local `meta.yaml` is rewritten byte-for-byte from the
     feedstock's raw text. It is never renamed, moved or deleted, and no `.meta.yaml*` file is ever created.
   - Feedstock v1, C2: a local `meta.yaml` is removed (G94).
   - No local `recipe.yaml`, or no local directory: `blocked`, with reason `no-recipe-yaml` or `no-local-mirror`.
     v0-to-v1 authoring and create-missing stay the wave story's manual steps.
4. **Edit.** Every edit goes through `recipe_editor.execute_actions`. That keeps its canonical indent and width, so no
   FMT-001 drift appears.
   - `context.version` is set to the target.
   - `build.number` resets to 0 on a version change. A same-version run writes nothing (G113).
   - `sha256` is recomputed with `calculate_hash` against the recipe's own rendered `source.url`. When it differs from
     the feedstock's sha256 for the same version, the outcome is `needs-review` and the original bytes are restored.
   - `source.url` is never rewritten. A templated `pypi.org/packages/source/…${{ version }}` URL stays templated. A
     literal, version-baked URL is `needs-review` (`SKILL.md:150`).
5. **Maintainers.** `extra.recipe-maintainers` becomes the union of the local list and the deployed list, local order
   first. No handle is ever dropped (G53).
6. **Dependencies.** The feedstock is the dependency authority (G96). When the local `host` or `run` names differ from
   the feedstock's at the target version, the body is left unchanged. The difference goes into the report and the CFE
   comments block, `cfe-forge-recipe-updates-needed` gets `dependency-fix` (landmine 9), and the outcome is
   `needs-review`. A pin or platform exclusion that another maintainer chose is never changed (landmine 12).
7. **CFE block.** `cfe-last-checked` is updated, and one dated line naming the driver, the wave and the outcome is
   appended under `# CFE comments` → `# Header:`. The line contains no `${{` (landmine 7).
8. **Write check.** After each write, the file must parse with `yaml.safe_load`, carry `#### CFE metadata` and
   `cfe-conda-name` exactly once (G92), and stay free of FMT-001. On any failure the original bytes are restored and
   the outcome is `failed`.
9. **`--gates`.** `validate_recipe`, `recipe_optimizer`, `dependency-checker` and `vulnerability_scanner` run through
   their CFE wrappers, pointed at `recipes/<name>/recipe.yaml`. Each verdict is read from its exit code into the
   report.
10. **`--build`.** The recipe builds into its own `build_artifacts/<name>` output directory (G52), pointed at
    `recipe.yaml` explicitly. `meta.yaml` stays in place: no stashing (`SKILL.md:1157`).
    `cfe-local-build-{status,datetime,platform,tool}` are stamped from the real outcome: `success`,
    `build-clean-test-blocked` (G95) or `failed`.

**Report:** `report.json` is the resume state, and `report.md` is the per-bucket summary. Each recipe carries:

- the outcome, from the closed set: `refreshed`, `already-current`, `needs-review`, `blocked`, `failed`, or in a
  dry-run `would-refresh`;
- the reasons;
- the from-version and to-version;
- the maintainers added;
- the dependency diff;
- the gate exit codes;
- the build status;
- the `recipe.yaml` sha256 after the run.

A rerun skips any recipe whose outcome is terminal and whose file hash is unchanged. `--force` reprocesses it.

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | The run completed. `needs-review` and `blocked` are data, not failures. |
| 1 | At least one recipe ended `failed`. |
| 2 | The manifest or the environment made the run impossible. |

**Also in scope:** `recipe_updater.get_current_recipe_info` falls back from `context.name` to
`extra.cfe-upstream-name`, then to a literal `package.name` that contains no `${{`. A recipe with none of those still
raises the same error.

## Acceptance Criteria

All tests below run on a fixture recipe tree under `tmp_path`, with `CFE_RECIPES_ROOT` pointed at it. The feedstock
fetch and the hash calculation are mocked, so no test touches the network.

- Given a v1 recipe behind its v1 feedstock, When `refresh-wave --apply` runs, Then:
  - `context.version`, `sha256` and `build.number` change;
  - every other line of the recipe body is byte-identical;
  - a templated `pypi.org/packages/source/…${{ version }}` URL is still templated;
  - list items stay two spaces deeper than their key (no FMT-001);
  - the report records `refreshed`.
- Given the same recipe after that run, When `--apply` runs again, Then the file is byte-identical and the outcome is
  `already-current`. When `--apply` runs a third time over an unchanged report, the recipe is skipped as resumed.
- Given a feedstock that is still v0 and a local `meta.yaml` beside `recipe.yaml`, When the run applies, including a
  run where a mocked gate exits non-zero, Then:
  - `meta.yaml` exists and equals the feedstock's raw text;
  - no file matching `.meta.yaml*` exists in `recipes/<name>/`;
  - the build mock received `recipe.yaml` as its explicit target.
- Given a v1 feedstock and a local `meta.yaml`, When the run applies, Then the local `meta.yaml` is gone and the
  report says so.
- Given a Track B recipe whose deployed maintainers include a handle missing locally, When the run applies, Then the
  local `recipe-maintainers` list is a superset of the deployed list, and the report names the added handle.
- Given a feedstock sha256 that differs from the recomputed one, or a version-baked `source.url`, or a dependency-name
  difference, When the run applies, Then the outcome is `needs-review` with that reason. In the sha256 and URL cases
  the file is byte-identical. In the dependency case only the CFE block changes, and it gains `dependency-fix`.
- Given any applied write, Then:
  - the file parses with `yaml.safe_load`;
  - `#### CFE metadata` and `cfe-conda-name` each appear exactly once;
  - the appended CFE comment contains no `${{`.
  A write planted to break the parse is restored and reported `failed`, and the run exits 1.
- Given a manifest with an unknown key, a bad `track` or a name like `../x`, When the run starts, Then it exits 2 and
  writes nothing.
- Given a dry-run (no `--apply`), When it runs over three fixture recipes, Then:
  - a hash of every file under the fixture `recipes/` is unchanged;
  - `report.json` and `report.md` exist under the report directory, with the planned outcomes;
  - no gate or build runs.
- Given a fixture recipe with a literal `package.name` and no `context.name` (the billiard shape), When
  `recipe_updater.get_current_recipe_info` reads it, Then it returns that name and version. A recipe with no name
  source still raises the same `ValueError`.
- **Wiring.** A meta-test asserts:
  - the CLI wrapper exists and delegates to the skill script;
  - `pixi.toml` declares `[feature.local-recipes.tasks.refresh-wave]` naming the wrapper;
  - `refresh_wave.py` is in `SCRIPTS`, and `refresh_wave.py --help` exits 0 with a usage line;
  - `test_cli_tool_parity.py` passes with the `refresh-wave` CLI-only entry.
- **Local only.** A meta-test parses `refresh_wave.py` with `ast` and asserts:
  - no `git` argv, and no argv or string containing `push`, `pr create`, `repo fork`, `--method`, `-X`, `submit` or
    `ship`;
  - no import of `submit_pr`, `prepare_pr` or `prepare_submission_branch`;
  - no `mason` invocation.

  A run test drives a dry-run and an `--apply` run with the driver's subprocess seam and `_http`'s non-GET requests
  patched to raise. Both complete, so neither run attempted a write anywhere but the local disk.
- **Landing.**
  - Every CFE-surface edit lands in one commit whose subject starts `retro(cfe):`. It carries a CFE `CHANGELOG.md`
    MINOR entry, and `SKILL.md`, `CHANGELOG.md`, `MANIFEST.yaml` and `config/skill-config.yaml` all agree on the new
    version.
  - `SKILL.md` documents the driver (Manual CLI Commands and the update sub-workflow at `:853`).
  - `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1). Read the critical constraints at `:150`, `:202` and
   `:246`, the local-mirror rule at `:1157`, and G52, G53, G92, G95, G96 and G113. Read
   `docs/specs/feedstock-refresh.md`'s landmines 1 to 13. Where this story and the skill disagree, the skill wins and
   the story records the deviation.
2. Read the untracked 25.1 and 25.2 scripts read-only as evidence of what a wave needed. Never copy them:
   - `.worktrees/dispatch-pyforge-mason-25.1/.cursor/wave_h_*.py` and `.sh`;
   - `.worktrees/dispatch-pyforge-mason-25.2/.cursor/track_b_wave_a.py`.
3. Write the tests first, from the Acceptance Criteria, and see each fail.
4. Implement `refresh_wave.py`, reusing `_path_guard`, `_paths`, `feedstock_lookup`, `feedstock_enrich` and
   `recipe_editor`. Keep one subprocess seam for gates and builds. Then add the wrapper, the pixi task, the `SCRIPTS`
   entry and the `CLI_ONLY_VERBS` entry, and fix `recipe_updater.get_current_recipe_info`.
5. Document the driver in SKILL.md. Add a gotcha if the work finds a new failure class, for example the
   `meta.yaml` hold an early exit never restores. Regenerate `config/failure-catalog.yaml` if a gotcha is added.
6. Commit the `pixi.toml` task first, alone, since it is outside the CFE surface. `environment.yaml` is unchanged,
   because a task changes no dependency: confirm with `pixi project export conda-environment -e build`. Then land
   every CFE-surface edit in one `retro(cfe): v<x.y.z> — …` commit, MINOR above the version `main` carries at landing,
   with all four version carriers in lockstep.
7. Reconcile every Spec `spec-surface-check` names: memlog first, then `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5). `spec-packaging-factory` and
   `spec-conda-forge-expert-rebuild` co-govern the CFE surface.

## Boundaries & Constraints

**Always:**

- Go through `conda-forge-expert` for every recipe judgement (Rule 1).
- Read every verdict from the exit code, never through a pipe.
- Confine every recipe name and path through `_path_guard`. Resolve the data directory through `_paths`.

**Never:**

- **Everything the driver does with these recipes stays local** (operator requirement, 2026-10-09). The driver never
  runs any of:
  - `git push`, or any other `git` command;
  - `gh pr create`, `gh repo fork`, or a `gh api` write (any `--method`/`-X` other than GET, or `-f`/`-F` fields);
  - `mason recipe submit` or `mason package ship`, with or without `--yes`;
  - CFE's `submit_pr` or `prepare_submission_branch`.

  It opens no PR, issue or comment on conda-forge, a feedstock, staged-recipes, or any repository other than
  `rxm7706/local-recipes`. It only reads feedstocks (raw files, or `gh api` GETs through `feedstock_lookup`), and
  writes only under `recipes/` and its own report directory.
- Never rename, move or delete a `meta.yaml` whose feedstock is still v0, and never create a `.meta.yaml*` file.
- Never rewrite a `source.url`, and never drop a maintainer handle.
- Never apply a dependency or pin change, or override a deliberate maintainer choice: report it.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.lock`, `recipes/**`, any `SPEC.md`, or
  `sprint-status-ledger.yaml`. The driver runs only on fixture trees here, and refreshing real recipes is Stories
  25.1 and 25.2's work.
- In `pixi.toml`, touch only the one task table. This is Epic 25's one dated exception to its no-`pixi.toml`
  boundary.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | v1 recipe behind its v1 feedstock | version, sha256 and build.number updated; `refreshed` | — |
| already current | local ≥ target | file untouched; `already-current` | — |
| C1 | feedstock still v0 | `meta.yaml` mirrored byte-for-byte; no `.meta.yaml*`; `recipe.yaml` refreshed | a failing gate never skips the restore, because nothing is moved |
| C2 | feedstock v1, local `meta.yaml` present | local `meta.yaml` removed | — |
| no `context.name` | billiard shape (literal `package.name`) | name resolved, refreshed | `recipe_updater` fallback |
| maintainer clobber | the deployed list has an extra handle | local list becomes the superset | landmine 10, G53 |
| deliberate pin | a maintainer-commented pin differs from the feedstock | body untouched; diff reported; `dependency-fix` | landmine 12 |
| hashed or literal URL | a version-baked `source.url` | `needs-review`, no write | `SKILL.md:150` |
| sha mismatch | recomputed ≠ feedstock sha256 | `needs-review`, original bytes kept | — |
| tag numbering | feedstock tag ≠ PyPI version | `needs-review` | landmine 1 |
| missing mirror | no `recipes/<name>/` | `blocked: no-local-mirror` | Wave F stays manual |
| bad write | the edit breaks the parse or duplicates the CFE block | original bytes restored; `failed`; exit 1 | G92 |
| resume | rerun over a recorded wave | terminal, unchanged recipes skipped | `--force` reprocesses |
| dry-run | no `--apply` | report only; `recipes/` byte-identical | — |
| bad manifest | unknown key, bad track, `../x` | exit 2, nothing written | `_path_guard` |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57); also CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 — Ruled: CFE gains a tracked bulk refresh
driver, so Track B can continue*.
Ledger key: `25-3-cfe-gains-a-tracked-bulk-recipe-refresh-driver-that-the-refresh-waves-run-through`.
Ledger status at mint: `backlog`.
Deps: —. Story 25.2 now depends on this story (`epics.md` § Story 25.2, **Deps:** S-25.3).
Flag: `flag-exempt: recipe-build` (recipe-factory tooling, not a runtime capability).
Minted 2026-10-09 from the operator's ruling of the same day: mint a driver story so Story 25.2 can continue.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test`. Expected: pass. This is the station's `verify_commands`;
  the story changes no Mason code.

**Manual checks:**

- `pixi run -e local-recipes test-ci`: the CFE suite passes, including the new unit and meta tests and
  `test_cli_tool_parity.py`.
- `pixi run -e local-recipes refresh-wave <manifest>`, as a dry-run over a three-recipe manifest taken from 25.2's
  Wave A list. It prints a report, and `git status --porcelain recipes/` is empty afterwards.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert .claude/scripts/conda-forge-expert`
  shows exactly one `retro(cfe):` subject, and that commit carries `CHANGELOG.md`. The four version carriers agree.
- `pixi project export conda-environment -e build` leaves `environment.yaml` byte-identical.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

- No review has run yet.
