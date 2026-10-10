---
title: "25.3: CFE gains a tracked bulk recipe-refresh driver that the refresh waves run through"
type: 'feature'
created: '2026-10-09'
status: 'done'
baseline_revision: '222530149e164d7d7929c175b8418d82afedc5bc'
followup_review_recommended: false
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md
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
  2026-10-09), and `recipes/wasmtime-py/recipe.yaml:76-78` records that. This breaks 25.1's own C1 rule. 25.1 hid
  a second one the same way, `recipes/pyobjc-framework-systemconfiguration/meta.yaml`. Story 22.1's landing renamed it
  back, so `wasmtime-py`'s is the one left (`git ls-files 'recipes/*/.meta.yaml*'`).
- **56 of its `recipe.yaml` files carry hashed PyPI URLs.** 25.1 introduced 52 of them; 4 (`ag-ui-protocol`,
  `openmetadata-managed-apis`, `tox-uv`, `wagtailmedia`) were already hashed before it. A `${{ version }}`-templated
  `https://pypi.org/packages/source/…` URL became a hashed `https://files.pythonhosted.org/packages/<hash>/…` URL, for
  example `recipes/django-todo/recipe.yaml:13`. `wave_h_bump.py:44-47` writes PyPI JSON's `url` field. All 56 are
  sdists (`.tar.gz`). This breaks CFE's critical constraint at `SKILL.md:150`.
- **78 of the 92 `recipe.yaml` diffs re-indent list items** (lines whose text is unchanged but whose indentation
  moved). In 76 of them, FMT-001 now fires where it did not before: list items sit at their parent key's depth. The
  scripts dumped with ruamel's default indent. `recipe_editor.py:93-101` already sets the canonical indent and width.
- **The CFE version carriers broke lockstep.** CFE `SKILL.md:10` and `CHANGELOG.md:5` moved to 8.97.1, while
  `MANIFEST.yaml:15` and `config/skill-config.yaml:6` stayed at 8.97.0. Story 22.1's landing (PR #2017) restored
  lockstep: all four now read 8.98.0.

This story edits no file in `recipes/`. The driver stops these defects recurring. Its repair mode (§ *Repair mode*)
can also undo the three recipe defects. A second operator ruling, the same day, has Story 25.2's Wave 0 run that
repair over the damaged recipes.

**Approach:** add one tracked CFE script, `refresh_wave.py`, under the three-place rule. It reads a wave manifest and
refreshes each recipe to its feedstock's published version through CFE's existing edit path (`recipe_editor`). It
reads feedstocks through `feedstock_lookup` (`gh api` GET only) and merges maintainers through
`feedstock_enrich._merge_maintainers` (G53). It writes a wave report. It is dry-run by default, resumable, and
idempotent. A separate `--repair` mode undoes the three recipe defects above and changes nothing else. The default
refresh path never rewrites a URL. The same commit fixes `recipe_updater.get_current_recipe_info` so the autotick path
can read a recipe that has no `context.name`.

Ledger key: `25-3-cfe-gains-a-tracked-bulk-recipe-refresh-driver-that-the-refresh-waves-run-through`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: feature / L / —.

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

**CLI:** `refresh-wave MANIFEST [--repair] [--apply] [--gates] [--build] [--report-dir DIR] [--force] [--json]`.
Without `--repair`, the run is a refresh (the per-recipe steps below). With it, the run is a repair (§ *Repair mode*);
`--build` is refused with `--repair`.

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
     literal, version-baked URL is `needs-review` (`SKILL.md:150`), and the report names `--repair` as its remedy.
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

**Repair mode** (`--repair`). It reads the same manifest, and dry-run is still the default. It changes only the three
defects below. It never changes `context.version`, `build.number`, `requirements`, tests, `about`, or
`recipe-maintainers`. The built artifact does not change: the source bytes are the same, and so is the parsed recipe.
So no build number moves, and G113 does not apply. Each recipe gets the repairs its files call for, in this order:

1. **Hashed URL.** A `source.url` matching `https://files.pythonhosted.org/packages/<xx>/<xx>/<hash>/<file>` is
   rewritten to the canonical form at `SKILL.md:150`:
   `https://pypi.org/packages/source/<first letter>/<dist>/<stem>-${{ version }}.<ext>`.
   - **`<dist>`** is the PyPI project name: `extra.cfe-upstream-name`, else the path segment of the feedstock's own
     `pypi.org/packages/source` URL. It is never `package.name`; `wasmtime-py`'s project is `wasmtime` (G10). With
     neither source, the outcome is `needs-review`.
   - **`<stem>` and `<ext>`** come from `<file>`, which must end in `-<context.version>.<ext>`. A wheel, or any other
     shape, is `needs-review`.
   - **The sha256 line is unchanged and verified.** The new URL, rendered at the recipe's version, must hash to the
     recipe's existing `sha256`. On a mismatch, or a failed fetch, the file is left byte-identical and the outcome is
     `needs-review`.
2. **List indentation.** List items at their parent key's depth (FMT-001) move to `recipe_editor`'s canonical style
   (`recipe_editor.py:93-101`: mapping 2, sequence 4, offset 2). The change must be whitespace-only:
   - `yaml.safe_load` gives the same value before and after;
   - every line keeps its non-whitespace text, in the same order;
   - every comment line is kept, including both `# CFE …` blocks (G92).
   Any other difference restores the original bytes, and the outcome is `needs-review`. A line-level re-indent meets
   this. A whole-file parse-and-dump is allowed only if it passes the same checks.
3. **Hidden `meta.yaml`.** The defect is a hold file such as `.meta.yaml.wave_h_hold`, with no `meta.yaml` beside it.
   - **Feedstock v0 (C1):** `meta.yaml` is written from the feedstock's raw `recipe/meta.yaml` (the mirror rule,
     `SKILL.md:1157`), and the report records whether that text equals the hold file.
   - **Feedstock v1 (C2):** no `meta.yaml` is restored.
   - **Feedstock unreadable:** the hold file is renamed back to `meta.yaml` byte-for-byte, and the outcome is
     `needs-review` (`feedstock-unread`).

   In all three cases the hold file is removed. A hold file beside an existing `meta.yaml` is `needs-review`, and
   neither file is touched.

Repair outcomes are `repaired` (naming each repair applied), `already-clean`, `needs-review` and `failed`, or
`would-repair` in a dry-run. The write check (step 8 above) runs after every repair write, and `--gates` runs the same
gates as a refresh. Like the refresh path, the repair path reads feedstocks only through `feedstock_lookup` and runs no
`git` command.

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
- **Repair: hashed URL.** Given a fixture whose `source.url` is a hashed `files.pythonhosted.org` sdist URL, with
  `extra.cfe-upstream-name` set, and the mocked hash of the canonical URL equal to the recipe's `sha256`, When
  `--repair --apply` runs, Then:
  - `source.url` reads `https://pypi.org/packages/source/<l>/<dist>/<stem>-${{ version }}.tar.gz`;
  - the `sha256` line and every other line are byte-identical;
  - the report records `repaired: url`.

  With the mocked hash different, or the fetch failing, the file is byte-identical and the outcome is `needs-review`.
  A wheel URL, a file name not ending in `-<version>.<ext>`, or a recipe with no `<dist>` source is `needs-review`,
  with no write. A fixture whose package name differs from its PyPI name (the `wasmtime-py` shape) gets the PyPI name
  in the path.
- **Repair: indentation.** Given a fixture with list items at their parent key's depth (FMT-001), When
  `--repair --apply` runs, Then:
  - the optimizer's FMT-001 check no longer fires;
  - `yaml.safe_load` is equal before and after;
  - every line's non-whitespace text is unchanged, in order;
  - the `#### CFE metadata` and `# CFE comments` lines are all present, with `cfe-conda-name` exactly once.

  A planted change that would also alter content is restored and reported `needs-review`.
- **Repair: hidden `meta.yaml`.** Given `.meta.yaml.wave_h_hold` and no `meta.yaml`, When `--repair --apply` runs,
  Then no hold file remains, and:
  - with a v0 feedstock, `meta.yaml` equals the feedstock's raw text, and the report says whether that equals the hold
    file;
  - with a v1 feedstock, no `meta.yaml` exists;
  - with the feedstock unreadable, `meta.yaml` equals the old hold file byte-for-byte, and the outcome is
    `needs-review`.

  Given both a hold file and `meta.yaml`, both files are byte-identical afterwards and the outcome is `needs-review`.
- **Repair touches nothing else.** Over a fixture with all three defects, the parsed `context`, `build`,
  `requirements`, `tests`, `about` and `extra.recipe-maintainers` are equal before and after. A rerun reports
  `already-clean` and writes nothing. A `--repair` dry-run leaves `recipes/` byte-identical and writes a report.
  `--repair --build` exits 2.
- **The refresh path still never rewrites a URL.** Given the hashed-URL fixture, When a refresh (no `--repair`)
  applies, Then the file is byte-identical, and the outcome is `needs-review`, with a reason that names `--repair`.
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
   `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md`'s landmines 1 to 13. Where this story and the skill disagree, the skill wins and
   the story records the deviation.
2. Read the untracked 25.1 and 25.2 scripts read-only as evidence of what a wave needed. Never copy them:
   - `.worktrees/dispatch-pyforge-mason-25.1/.cursor/wave_h_*.py` and `.sh`;
   - `.worktrees/dispatch-pyforge-mason-25.2/.cursor/track_b_wave_a.py`.
3. Write the tests first, from the Acceptance Criteria, and see each fail.
4. Implement `refresh_wave.py` with both its refresh path and its `--repair` mode, reusing `_path_guard`, `_paths`,
   `feedstock_lookup`, `feedstock_enrich` and `recipe_editor`. Keep one subprocess seam for gates and builds. Then add the wrapper, the pixi task, the `SCRIPTS`
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
- Never rename, move or delete a `meta.yaml` whose feedstock is still v0, and never create a `.meta.yaml*` file. The
  one exception is `--repair`: it removes a hold file after restoring `meta.yaml`.
- Never drop a maintainer handle. The refresh path never rewrites a `source.url`. Only `--repair` rewrites one, and
  only from a hashed `files.pythonhosted.org` URL to the canonical form, with the sha256 unchanged and verified.
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
| repair: hashed URL | sdist URL under `files.pythonhosted.org/packages/<hash>/` | canonical `pypi.org/packages/source` URL; sha256 unchanged; `repaired: url` | hash mismatch, failed fetch, wheel or no `<dist>`: `needs-review`, no write |
| repair: indentation | FMT-001 list items | canonical indent; whitespace-only change | any non-whitespace change restored: `needs-review` |
| repair: hidden meta.yaml, v0 | hold file, no `meta.yaml`, feedstock v0 | `meta.yaml` from the feedstock; hold file removed | feedstock unreadable: hold renamed back; `needs-review` |
| repair: hidden meta.yaml, v1 | hold file, feedstock v1 | hold file removed, no `meta.yaml` | — |
| repair: both files present | hold file and `meta.yaml` | nothing touched; `needs-review` | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57); also CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 — Ruled: CFE gains a tracked bulk refresh
driver, so Track B can continue*.
Ledger key: `25-3-cfe-gains-a-tracked-bulk-recipe-refresh-driver-that-the-refresh-waves-run-through`.
Ledger status at mint: `backlog`.
Deps: —. Story 25.2 now depends on this story (`epics.md` § Story 25.2, **Deps:** S-25.3). Its Wave 0 runs this
story's `--repair` mode over the recipes 25.1's landing damaged (operator ruling, 2026-10-09).
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
- `pixi run -e local-recipes refresh-wave <manifest> --repair`, as a dry-run over `wasmtime-py`, `django-todo` and
  `tox-uv`. The report plans the URL, indentation and `meta.yaml` repairs, and `git status --porcelain recipes/` is
  empty afterwards.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert .claude/scripts/conda-forge-expert`
  shows exactly one `retro(cfe):` subject, and that commit carries `CHANGELOG.md`. The four version carriers agree.
- `pixi project export conda-environment -e build` leaves `environment.yaml` byte-identical.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Spec Change Log

- **2026-10-09 (later), operator ruling:** Story 25.2's first wave runs the new driver over the recipes Story 25.1's
  landing damaged, to repair them. This spec gains `--repair`. It rewrites a hashed `files.pythonhosted.org` sdist URL
  to the canonical `pypi.org/packages/source` form, with the sha256 unchanged and verified. It re-indents FMT-001 list
  items to `recipe_editor`'s canonical style, whitespace-only. It restores a v0 feedstock's `meta.yaml` from the
  feedstock, or else from the `.meta.yaml.wave_h_hold` file, and removes the hold file. ACs on fixtures cover each
  repair, and the refresh path keeps never rewriting a URL.
  - The CLI, the per-recipe outcomes, the I/O matrix, the Boundaries and the manual checks follow.
  - Effort moves from M to L.
  - The context counts are made exact: of the 56 hashed URLs, 25.1 introduced 52. Of the 78 re-indented recipes, 76
    now fire FMT-001. 25.1 hid two `meta.yaml` files, and 22.1's landing restored one of them. Story 22.1's landing
    (PR #2017) also restored the CFE version lockstep at 8.98.0.
  - Every local-only line is unchanged.
  Recorded on `spec-pyforge-mason`'s memlog.

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - Implementation reviewed against acceptance criteria and the I/O matrix via unit/meta tests (95 passed); no adversarial layer findings recorded on this pass.

## Auto Run Result

Status: done

Summary: Added tracked CFE `refresh_wave.py` with refresh and `--repair` modes, three-place wiring (wrapper, pixi `refresh-wave` task, SCRIPTS + CLI_ONLY_VERBS), and `recipe_updater.get_current_recipe_info` name fallback. CFE version carriers moved to 8.99.0 in lockstep.

Files changed:
- `.claude/skills/conda-forge-expert/scripts/refresh_wave.py` — bulk refresh/repair driver
- `.claude/scripts/conda-forge-expert/refresh_wave.py` — CLI wrapper
- `.claude/skills/conda-forge-expert/scripts/recipe_updater.py` — billiard-shape name resolution
- `.claude/skills/conda-forge-expert/scripts/mcp_parity.py` — refresh-wave CLI-only verb
- `.claude/skills/conda-forge-expert/tests/unit/test_refresh_wave.py` — AC/matrix coverage
- `.claude/skills/conda-forge-expert/tests/meta/test_refresh_wave_wiring.py` — wiring + local-only ast guard
- `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py` — SCRIPTS entry
- `.claude/skills/conda-forge-expert/SKILL.md`, `CHANGELOG.md`, `MANIFEST.yaml`, `config/skill-config.yaml` — v8.99.0 docs
- `pixi.toml` — `[feature.local-recipes.tasks.refresh-wave]` (prior checkpoint commit)
- Spec memlogs on `spec-conda-forge-expert-rebuild`, `spec-packaging-factory`, `spec-pyforge-mason`

Review: no patch/defer entries; AC verified by pytest.

Verification:
- `pytest` refresh_wave unit + wiring tests: 95 passed
- `python scripts/spec_surface_reconcile.py`: OK
- `pixi run --frozen -e pyforge-mason pyforge-mason-test`: pass after `retro(cfe):` commit (CFE meta tests require sanctioned commit)

Residual: operator dry-runs over live Wave A / repair manifests not executed in this run; `--build` exercised via mocks only.
