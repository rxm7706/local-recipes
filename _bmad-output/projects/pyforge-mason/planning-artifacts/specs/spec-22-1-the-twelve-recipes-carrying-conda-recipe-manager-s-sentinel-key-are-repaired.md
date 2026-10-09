---
title: "22.1: The twelve recipes carrying conda-recipe-manager's sentinel key are repaired"
type: 'fix'
created: '2026-09-28'
status: 'done'
baseline_revision: 'f0eeddddb3c9a05a95235c872be495801457c1ff'
flag-exempt: recipe-build
review_loop_iteration: 2
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py
deferred:
  - deferred: ctng-compilers rattler render cycle on 0.76.1 -> Story 22.3
    location: recipes/ctng-compilers/recipe.yaml
    reason: >-
      Sentinel and output-level run_exports fixes parse and validate; `rattler-build build --render-only`
      with `.ci_support/linux64.yaml` plus local conda_build_config still exits 1 with
      `Cycle detected in recipe outputs` (gcc stack). Needs rattler-build fix for pin_subpackage/run_exports
      cycle detection (prefix-dev/rattler-build#2531 family) or feedstock-faithful variant matrix beyond
      generic linux64. Split out by operator ruling 2026-10-09: owned by mason Story 22.3
      (22-3-ctng-compilers-loses-its-sentinel-key-once-rattler-build-renders-its-output-graph, blocked);
      this story restores the file to main's copy and allowlists its leak (outputs[6].tests[0]) in the corpus check.
  - deferred: vc's faithful v1 port needs a named track feature -> Story 22.4
    location: recipes/vc/recipe.yaml
    reason: >-
      meta.yaml gives the vc, vs<year>_<platform> and vs_<platform> outputs track_features [vc14], one shared feature;
      rattler-build 0.76.1 rejects build.track_features, and variant.down_prioritize_variant writes a per-package
      <name>-p-0 instead. The independent review of the 22.1 landing also found the draft port hardcoded one of the
      feedstock's five conda_build_config.yaml variant entries in context, left out vc_repack.py, activate.bat,
      LICENSE.TXT and conda_build_config.yaml (G94), had inheriting outputs call python without declaring it, and
      compared the string vsver with an integer (minijinja: "9" >= 17 is true). Split out by the second operator ruling
      of 2026-10-09: owned by mason Story 22.4
      (22-4-vc-loses-its-sentinel-key-once-rattler-build-can-emit-its-vc14-track-feature, blocked); this story restores
      recipes/vc/ to main's copy and allowlists its leak (outputs[5].tests[0]) in the corpus check.
declared_low_risk: false
---

<intent-contract>

## Intent

**Scope (two operator rulings, 2026-10-09):** this story lands for ten of the twelve recipes.
- `ctng-compilers` moved to Story 22.3: once its sentinel and output-level `run_exports` are repaired, rattler-build
  0.76.1 reports `Cycle detected in recipe outputs`.
- `vc` moved to Story 22.4: its `meta.yaml` gives three outputs the shared track feature `vc14`, which rattler-build
  0.76.1 cannot emit, and the independent review found the draft port unfaithful in four more ways (the `deferred:`
  entry lists them).

Both files stay as `main` has them, sentinel included. The corpus check allowlists each leak by file and parsed-tree
location, naming its story. The twelve-recipe text below is the original contract; the table's `ctng-compilers` and
`vc` rows belong to 22.3 and 22.4.

**Problem:** 12 `recipes/*/recipe.yaml` files carry a YAML mapping key written as
`<conda_recipe_manager.types.SentinelType object at 0x…>`. That is the repr of conda-recipe-manager's internal sentinel.
It leaked in the 2026-08-16 bulk v0→v1 conversion (`20b2f459fa`, "Add mirrored and generated recipe.yaml files for the
identity snapshot") wherever the `meta.yaml` beside it had a construct crm could not translate. Measured on `main` at
`0c8c07e6fc`:

- All 12 fail `rattler-build build --render-only` (0.76.1) with `Failed to parse recipe`.
- CFE's `validate_recipe` passes six of them, because the key parses as a plain string. conda-smithy flags it only at
  the top level (pyautogui, shodan) and crashes in `lint_section_order` on boost, vc and ctng-compilers.
- The current crm (0.10.6, `-e grayskull`) still writes the sentinel on all 12 and exits 100 ("warnings"), so
  re-converting does not help. The fix is by hand, per construct.
- Every feedstock is still `meta.yaml` (semgrep has none), so each `meta.yaml` stays (CFE's local-mirror rule).

What the sentinel replaced, read against each `meta.yaml`, and the defects the render finds once it is gone
(measured on scratch copies):

| Recipe | Where | The `meta.yaml` construct | v1 repair | Next defect the render finds | Gate |
|---|---|---|---|---|---|
| StringZilla | `source` | `#patches:` / `#- patches/…` (commented out) | drop the key; keep the two lines as indented comments | none on linux-64 | build |
| pyobjc-framework-systemconfiguration | `source` | `#patches:` (commented out) | as StringZilla | `name.replace(...)` in `source.url` (a method minijinja lacks): the literal PyPI URL | render (osx-64), validate, lint |
| lerc | `requirements` | `#host:` + `# TODO …` comments | drop the key; keep the comments indented | none on linux-64 | build |
| semgrep | `tests[1]` | `requires: [pip]`, its `#commands:`/`#- pip check` commented out | remove the element (the `python:` test keeps `imports` and `pip_check: false`) | none on linux-64 | render, validate, lint |
| django-pygwalker | `tests[1]` | `requires: [python {{ python_min }}, pip]`, pip check commented out | remove the element (`python_version: ${{ python_min }}` covers it) | bare `python ${{ python_min }}` in host → `python ${{ python_min }}.*` | build |
| amundsen-databuilder | `tests[1]` | `requires: [python {{ python_min }}]`, pip check commented out | as django-pygwalker | as django-pygwalker | build |
| psycopg2-yugabytedb | `tests[1]` | `imports:` then comment lines, then `- psycopg2` | `imports: [psycopg2]` in the `python:` element; drop the sentinel element; keep the two upstream comments above it | none on linux-64 | build |
| shodan | top level, after `extra:` | `test.requires: [pip, pytest, python {{ python_min }}]` after a commented `pytest` line | remove the top-level key; `pip` and `python ${{ python_min }}.*` go in the script element's `requirements.run`; `pytest` served only the commented-out suite and goes, with that line kept in the `# CFE comments` block (G93) | bare `python ${{ python_min }}` in host → `.*` | build |
| pyautogui | top level, after `extra:` | `test.requires: [pip]` after three commented `pytest` lines | remove the top-level key; nothing in the script test needs `pip`; the three `pytest` lines move to the `# CFE comments` block | none on linux-64 | build |
| ctng-compilers (moved to Story 22.3) | `gxx_impl` output `tests[0]` | `{% if cross_target_cxx_stdlib == "libstdcxx" %}` around the tzdb checks, nesting `{% if target_platform == cross_target_platform %}` | append to the element's own `script:` as `- if: cross_target_cxx_stdlib == "libstdcxx"` / `then:` holding the two compile lines and a nested `- if: target_platform == cross_target_platform` / `then:` holding the rest, in `meta.yaml`'s order | an output-level `run_exports` (valid fields: package, inherit, source, requirements, build, about, tests) | render, validate, lint |
| vc (moved to Story 22.4) | the activation output's `tests[0]` | `{% if vsyear \| int >= 2022 %}` around three `# [win]` clang checks and `requires: clang {{ clang_test_version }}.*` | append the checks to the element's `script:` under `- if: win and vsyear \| int >= 2022`; the `clang` run requirement under the same condition | `run_exports: - strong:` read as a scalar list (the v1 shape is `run_exports: strong: [...]`) | render (win-64), validate, lint |
| boost | `libboost` output `tests[0]` | `{% for each_lib in boost_libs + boost_libs_static_only + boost_libs_py %}` with `{% if each_lib in … %}` / `{% else %}` blocks | one shell loop per platform in the element's `script:` (a single `if: unix` entry looping over the rendered lists, and an `if: win` `for %%L in (…) do (…)` entry) that reproduces `meta.yaml`'s present/absent checks exactly | `boost_libs` missing from `context`; `boost_libs_py` left as a v0 expression string; `${{ each_lib }}` used outside any loop in the headers, devel and python outputs; one output's `tests:` a mapping, not a list | render, validate, lint |

Each repair follows CFE's own conventions:

- Loop over the lists in one multi-line script entry, since shell state does not carry across list entries (G1).
- Use `${{ }}` everywhere, never a bare `{{ }}` (G20).
- Put no column-0 comment inside an indented block (G93). An agent note goes in the bottom `# CFE comments` block, and
  an upstream comment stays verbatim in the body.

**Approach:**

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1).
2. Fix each file per the table, against its `meta.yaml`, one recipe at a time.
3. After each file:
   - `rattler-build build --render-only` must pass on a platform the recipe builds: linux-64, osx-64 for pyobjc, win-64
     for vc.
   - Then run `validate_recipe` and the CI-parity lint.
4. Build the seven cheap recipes on linux-64. Point each build at `recipe.yaml` explicitly, so `meta.yaml` never enters
   the run. Record each outcome in a full CFE block (none carries one today).
5. In the story's `retro(cfe):` commit:
   - add the gotcha (the next free G-number): crm's v0→v1 conversion leaks a `SentinelType` repr as a key for
     constructs it cannot translate, and exits 100, not an error;
   - add a corpus check to `tests/meta/test_recipe_yaml_parse_audit.py` that reds any `recipe.yaml` under `recipes/`
     (recursively) whose parsed tree has a non-string mapping key or a key or whole scalar matching an object repr,
     with two allowlist entries, each a file and the location of its leak: `ctng-compilers` (Story 22.3) and `vc`
     (Story 22.4). Each entry admits exactly one object-repr key at its location, so a second leak in an allowlisted
     file reds, even a second key in the same mapping, and an entry whose leak is gone fails;
   - regenerate `config/failure-catalog.yaml`.

Ledger key: `22-1-the-twelve-recipes-carrying-conda-recipe-manager-s-sentinel-key-are-repaired`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-32 (FR-54); AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in
  the `retro(cfe):` commit).
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Sibling: Story 22.2 (CFE's validation refuses the next leak). Independent; either may land first.

## Acceptance Criteria

- Given `recipes/` When `grep -rl 'object at 0x' recipes/ --include=recipe.yaml` runs Then it finds only `recipes/ctng-compilers/recipe.yaml` (Story 22.3) and `recipes/vc/recipe.yaml` (Story 22.4)
- Given each of the 10 When `rattler-build build --render-only` runs on a platform it builds (linux-64; `--target-platform osx-64` for pyobjc-framework-systemconfiguration) Then it exits 0 with at least one output rendered, not skipped
- Given each of the 10 When `validate_recipe` and `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge` (run on a copy without `meta.yaml`, so the lint reads `recipe.yaml`) run Then neither reports an error
- Given shodan, django-pygwalker, amundsen-databuilder, lerc, StringZilla, psycopg2-yugabytedb and pyautogui When each builds on linux-64 with the recipe pointed at explicitly Then the build exits 0 and its CFE block records the real outcome (`success`, or `build-clean-test-blocked` naming the unsolvable dependency, or the missing system tool such as pyautogui's `xvfb-run`, which its feedstock takes from `yum_requirements.txt`; G95)
- Given each repaired construct When it is compared with its `meta.yaml` Then it says the same thing: the same commands under the same conditions, the same test requirements, and the same comments kept
- Given each recipe directory When it is listed Then `meta.yaml` is still there
- Given the story's `retro(cfe):` commit When `pixi run -e local-recipes test` runs Then the new corpus check passes on the repaired tree (the ctng-compilers and vc leaks allowlisted by location for Stories 22.3 and 22.4) and fails when a sentinel key is planted, at top level or one directory deeper, or when a second leak is planted in an allowlisted file, in another element or in the same mapping as the allowlisted key
- Given the story closes When the Rule-2 retro runs Then its `retro(cfe):` commit carries a CFE `CHANGELOG.md` semver entry, the new gotcha and its version carriers

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md. Re-run `grep -rl 'SentinelType object' recipes/ --include=recipe.yaml`:
   a file added since the mint joins the list. For each feedstock, check that `recipe/` still holds `meta.yaml`. If a
   feedstock has since moved to v1, mirror its `recipe.yaml` verbatim instead (G94).
2. Repair each file per the table, reading its `meta.yaml`. After each one, run `rattler-build build --render-only`
   (the variant configs `.ci_support/<platform>.yaml` and the local-recipes pinning) and fix what it reports until it
   exits 0.
3. Gates per recipe, in order: `pixi run -e local-recipes validate recipes/<name>`,
   `pixi run -e local-recipes lint-optimize recipes/<name>`, and the CI-parity lint.
4. Build the seven cheap recipes with `pixi run -e local-recipes recipe-build recipes/<name>`. `get_build_summary` can
   report "unknown" on a native success (G85); confirm from the `.conda` and `rattler-build test --package-file`.
5. Commit the recipe files. Subject `mason: …`, never starting `Story 22.1:`.
6. Close with the Rule-2 retro in its own commit. Subject `retro(cfe): v<x.y.z> — …`, never starting `Story 22.1:`.
   - The commit carries the gotcha, the corpus check, the regenerated failure catalog, the `CHANGELOG.md` entry, and
     the version in `SKILL.md`, `MANIFEST.yaml` and `config/skill-config.yaml`.
   - Bump MINOR: the gotcha is new.
7. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped `--write-baseline --spec`
   for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement; where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Keep `meta.yaml` in every directory, and point every build, test and lint at `recipe.yaml`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not delete a `meta.yaml`, and do not re-run the bulk conversion to regenerate a file.
- Do not open a feedstock, staged-recipes or upstream PR (no explicit ask).
- Do not build boost, ctng-compilers or vc (heavyweight or Windows-only), semgrep (its sdist carries a prebuilt native
  `semgrep-core` that a `noarch: python` build would repackage; its packaging shape is a separate question), or
  pyobjc-framework-systemconfiguration (osx-only).
- Do not change CFE's `validate_recipe.py`. That is Story 22.2.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| commented-out key | `<sentinel>:  #patches:` | the key removed, the comment kept indented | — |
| nothing left to run | `- <sentinel>: {requirements: …}` | the element removed | — |
| split imports | `imports:` null + `- <sentinel>: [psycopg2]` | `imports: [psycopg2]` | — |
| orphaned requires | top-level `<sentinel>: {requires: …}` | folded into the script test or dropped, with the reason in CFE comments | — |
| jinja loop | `{% for each_lib … %}` flattened | one shell loop per platform reproducing `meta.yaml`'s checks | G1: one entry per loop |
| test env unsolvable | a cheap build's deps absent on conda-forge | `build-clean-test-blocked` recorded, dependency named | G95 |
| feedstock went v1 | `recipe/recipe.yaml` exists upstream | mirror it verbatim | G94 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-32 (FR-54).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-28 (night) — Proposed: twelve recipes lose a
converter's leaked sentinel key, and CFE refuses the next one*.
Ledger key: `22-1-the-twelve-recipes-carrying-conda-recipe-manager-s-sentinel-key-are-repaired`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: recipe-build` (recipe repairs ship no runtime capability behind a flag).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code, so the suite must stay green).

**Manual checks:**
- `grep -rl 'object at 0x' recipes/ --include=recipe.yaml` — expected: `recipes/ctng-compilers/recipe.yaml` (Story 22.3)
  and `recipes/vc/recipe.yaml` (Story 22.4) only.
- `pixi run -e local-recipes rattler-build build --render-only --recipe recipes/<name>/recipe.yaml --variant-config .ci_support/linux64.yaml --variant-config .pixi/envs/local-recipes/conda_build_config.yaml`
  for each of the 10 (for pyobjc-framework-systemconfiguration use `osx64.yaml` with `--target-platform osx-64`, so the
  render is not an all-variants-skipped pass) — expected: exit 0 with at least one rendered output.
- `pixi run -e local-recipes validate recipes/<name>` and
  `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge <copy without meta.yaml>` for each
  of the 10 — expected: no error.
- `pixi run -e local-recipes recipe-build recipes/<name>` for shodan, django-pygwalker, amundsen-databuilder, lerc,
  StringZilla, psycopg2-yugabytedb and pyautogui — expected: exit 0 on linux-64.
- `pixi run -e local-recipes test` — expected: pass, including the new corpus check.
- `git log origin/main..HEAD --no-merges --format=%s -- .claude/skills/conda-forge-expert` — expected: every subject
  starts `retro(cfe):`, each such commit carries `CHANGELOG.md`, and all of them carry one version, `8.98.0` (the
  review fixes amend the unreleased entry).
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Spec Change Log

- 2026-10-09: **Operator ruling — land 22.1 for eleven recipes; split `ctng-compilers` into Story 22.3.** The dispatch
  run (`dispatch/pyforge-mason/22.1`) repaired all twelve sentinel keys, but `ctng-compilers`' repaired file hits
  rattler-build 0.76.1's `Cycle detected in recipe outputs`. `recipes/ctng-compilers/recipe.yaml` is restored to
  `main`'s copy. The corpus check allowlists exactly that file, naming Story 22.3. The ACs above, the `deferred:` entry
  and the Verification section now read eleven.
- 2026-10-09: **Deviations recorded during the landing (the skill wins; each is in that recipe's `# CFE comments`):**
  - `boost`: the libboost test is one `if: unix` loop and one `if: win` `for %%L` block, as the table says. So are the
    flattened `${{ each_lib }}` checks in the headers, devel and python outputs (the run had moved them into helper
    scripts that dropped the Windows and macOS checks). A multi-output v1 recipe has no top-level `requirements`, so
    conda-build's top-level build is a `staging` output (`boost-build`); every output inherits it with
    `run_exports: false`. meta.yaml's `py` becomes `python_min` for the outputs that do not vary by python, and
    `python | version_to_buildstring` for libboost-python. `# [win]` on two `build:` keys is gone (v1 lint).
  - `vc` (draft port, not landed; the second ruling moved vc to Story 22.4, and the port stays reachable at
    `2ebf09ea75:recipes/vc/recipe.yaml`): the top-level `--extract` build is a `staging` output (`vc-extract`), with its p7zip/python requirements
    restored; the run had dropped them. Each `script_interpreter` is a `python ${{ RECIPE_DIR }}/vc_repack.py --<mode>`
    script. `track_features` (rejected by 0.76.1) is `variant.down_prioritize_variant: 1`. vc_runtime's flattened
    DLL loop is three `for %%D` blocks. A top-level `license_file: LICENSE.TXT` satisfies v1 lint R-013, and the
    BSD-3-Clause metapackages set `license_file: []`. `context` is the feedstock CBC's first zip (VS 2026, win-64).
  - `StringZilla`: the stale recipe-dir `conda_build_config.yaml` is removed; the feedstock has none (G94), and it failed
    `validate_recipe`'s `c_stdlib_version` lint.
  - `lerc`: the feedstock's `build.sh` and `bld.bat` are added (G94), `bld.bat` under the v1 name `build.bat`; without
    them a local build packages nothing.
  - `shodan`: `setuptools <81` in run (G34): `shodan/__main__.py` imports `pkg_resources`, which setuptools 82+ lacks, so
    `shodan --help` failed on a fresh solve.
  - `psycopg2-yugabytedb`: `setuptools` in host (G55) and a `>=3.13` skip (G50). The recipe's own CFE comments
    (2026-06-21) record both; the 2026-08-16 conversion dropped them from the body.
  - `pyautogui`: meta.yaml's three commented `pytest` lines and its commented `pytest` requirement go to the
    `# CFE comments` block (crm had moved two of them to the file header).
  - The CI-parity lint is run on a copy without `meta.yaml`. With both files present it reports only the two-file lint.
- 2026-10-09: The cheap builds' outcomes, per G95, are in the `## Run results` section below.
- 2026-10-09: **Second operator ruling — land 22.1 for ten recipes; split `vc` into Story 22.4.** The independent review
  of the landing found the vc port unfaithful (the `deferred:` entry lists how). `recipes/vc/` is restored to `main`'s
  copy (`git diff origin/main -- recipes/vc` is empty). The corpus check allowlists its leak at `outputs[5].tests[0]`,
  naming Story 22.4. The ACs, the `deferred:` entries and the Verification section now read ten, and both allowlist
  entries are keyed by file and location.
- 2026-10-09: **Review fixes** (the Review Triage Log has each finding): `pyautogui` gains the feedstock's
  `yum_requirements.txt` (G94), its python test element sits under `if: not linux`, and it was rebuilt; the comments the
  repair had dropped are back in `psycopg2-yugabytedb`, `semgrep`, `django-pygwalker`, `amundsen-databuilder` and
  `boost`; `shodan`'s python test runs on `python_min` and the newest python. The corpus check scans `recipes/`
  recursively. The CFE retro stays `8.98.0` (unreleased) and lands a second `retro(cfe):` commit, so the Verification
  line on the CFE commits now reads "every subject starts `retro(cfe):`" instead of "exactly one".
- 2026-10-09: **Second review fixes** (the Review Triage Log has each finding): the corpus check's allowlist admits
  exactly one object-repr key per entry; Story 22.3's spec, its epics entry, this story's epics entry and the Dream no
  longer assume eleven fixed recipes or an empty allowlist; boost's mirror gains the feedstock's recipe/ files at its
  1.91.0 commit and pyobjc-framework-systemconfiguration's gains the feedstock's `conda_build_config.yaml` at its 12.2.1
  commit (G94); boost's CFE comments record its staging-inherited build strings; three more upstream comments are back
  in the body (shodan, pyautogui, lerc); pyobjc's CFE metadata is refreshed; psycopg2-yugabytedb's and semgrep's CFE
  blocks follow the convention. The CFE retro stays `8.98.0` and lands a third `retro(cfe):` commit.

## Run results

Measured 2026-10-09 on the merged tree (origin/main d377581be4 + this branch), rattler-build 0.76.1. After the review
fixes, pyautogui, psycopg2-yugabytedb, semgrep, django-pygwalker, amundsen-databuilder, shodan and boost were re-run
through render, validate and the CI-parity lint, and pyautogui and shodan were rebuilt. After the second review's fixes,
pyautogui, shodan, lerc, semgrep, psycopg2-yugabytedb, boost and pyobjc-framework-systemconfiguration were re-run
through render, validate and the CI-parity lint (comment, metadata and recipe-dir file changes; no rebuild):

| Recipe | grep | render-only (platform: outputs) | validate_recipe | CI-parity lint (no meta.yaml) | Local build (linux-64) |
|---|---|---|---|---|---|
| StringZilla | clean | linux-64: 4 | pass | in fine form | success (py3.11-3.14) |
| lerc | clean | linux-64: 1 | pass | in fine form | success |
| semgrep | clean | linux-64: 1 | pass | suggestions only | not built (story boundary) |
| django-pygwalker | clean | linux-64: 1 | pass | suggestions only | success |
| amundsen-databuilder | clean | linux-64: 1 | pass | suggestions only | build-clean-test-blocked: `pandas >=0.21.0,<1.5.0` has no python >=3.11 build |
| psycopg2-yugabytedb | clean | linux-64: 2 (+2 skipped, >=3.13) | pass | in fine form | success (py3.11, py3.12) |
| pyautogui | clean | linux-64: 4 | pass | in fine form | success (py3.11-3.14) on a scratch copy with a pass-through `xvfb-run` shim on PATH: the host has no Xvfb, and `setup.py` never imports pyautogui (the feedstock gets xvfb-run from yum_requirements.txt, now copied here). The first run, without the shim, failed with `xvfb-run: command not found` |
| shodan | clean | linux-64: 1 | pass | in fine form | success (imports and pip check on `python_min` and the newest python, then `shodan --help`) |
| pyobjc-framework-systemconfiguration | clean | osx-64: 4 (render reads the feedstock's `conda_build_config.yaml`) | pass | in fine form | not built (osx-only) |
| boost | clean | linux-64: 11 (render reads the feedstock's `conda_build_config.yaml`) | pass (G29 "no tests" warning) | one suggestion: rename `bld.bat` to `build.bat` (the staging output names `bld.bat`, the feedstock's file) | not built (heavyweight) |
| vc | sentinel (main's copy) | — | — | — | Story 22.4 |
| ctng-compilers | sentinel (main's copy) | — | — | — | Story 22.3 |

`lint-optimize` reports STD-002 (both files present, expected for a v0 mirror) on all ten; TEST-001 on boost is G29's
multi-output false positive; the SEL-002 / TEST-002 / DEP-001 / PIN-001 suggestions on semgrep, shodan,
django-pygwalker and amundsen-databuilder mirror their feedstocks' `meta.yaml` and are left as is. `meta.yaml` is
present in all twelve directories. Each built recipe's CFE block records its outcome (G95).

## Review Triage Log

- 2026-10-09 second independent review (`261e814a2a`, `a799b822f4`, `f81e67e87b`): every first-review finding verified
  resolved; landing **blocked** on two new MEDIUM findings. Evidence in the session scratchpad `review-221b/`.
  Dispositions:
  1. **MEDIUM: Story 22.3's spec and epics entry assumed the other eleven fixed** (the grep "finds nothing", an empty
     allowlist). **Fixed** as 22.4 words it: the grep "does not list `recipes/ctng-compilers/recipe.yaml`" and the check
     passes "with no `ctng-compilers` allowlist entry"; 22.3's Spec Change Log and spec-pyforge-mason's memlog record the
     correction. The same stale text is fixed in this story's epics entry (the grep finds only ctng-compilers and vc; the
     corpus check scans recursively), in 22.3's Intent ("allowlists exactly one leak here", by location) and in the
     Dream's 22.3 entry ("by file and location", not "by name").
  2. **MEDIUM: `_triage` let any number of object-repr keys pass at an allowlisted location.** **Fixed:** each entry is
     consumed by the first object-repr key at its location; any other finding there is unexpected.
     `test_sentinel_allowlist_is_per_location` gains the same-mapping case, and the new
     `test_second_sentinel_key_in_an_allowlisted_mapping_reds` parses a YAML element with two sentinel keys. On a
     scratch copy of `recipes/`, the review's `plant.py` gives: unmodified copy green; a second key in the same mapping
     red for both ctng-compilers and vc; a second leak in another element red; a repr value, a top-level leak and a
     nested-recipe leak red; a removed ctng leak red as a stale entry.
  3. **LOW: boost's mirror lacked every file its recipe.yaml references; pyobjc lacked its `conda_build_config.yaml`.**
     **Fixed** (G94): boost's `build.sh`, `bld.bat`, `build-py.*`, `install-lib.*`, `install-py.*`, `test_lib.*`, `test/`,
     `patches/0001-…` and `conda_build_config.yaml` copied verbatim from the feedstock's 1.91.0 commit `306f17e6d3e2`,
     whose `meta.yaml` matches the mirror's byte for byte; file modes match and every blob hash was checked.
     pyobjc's `conda_build_config.yaml` (`c_stdlib_version` 11.3 on osx-arm64) copied from `7cd5763fa158`, the last
     12.2.1 commit, whose `meta.yaml` matches. Both renders now load the recipe-dir config. Epic 22's surface names the
     new paths.
  4. **LOW: boost's staging inheritance changes three build strings** (`np2he8b8257_0` against conda-forge's
     `ha770c72_N`). **Recorded** in boost's CFE comments and in G121: `inherit:` takes only `from` and `run_exports`, so
     no inherit form drops the staging variant keys, and a hardcoded `build.string` would hide the variant.
  5. **CFE: G1's heading and catalog title still said env vars do not carry; G121's "first variant is `python_min`"
     lacked its condition.** **Fixed** in the third `retro(cfe):` commit: G1 is retitled, its Why says the behavior
     depends on the rattler-build version, and its one anchor link is updated; the `python_min` sentence states that it
     holds only while `python_min` is the matrix's lowest python. The regenerated catalog changes only G1's title and
     the source hash.
  6. **LOW: upstream comments still relocated.** **Fixed:** shodan's "Skip test suite becuase it requires Shodan API
     key" is back after `shodan --help`; pyautogui's "Disabling test suite for now so many of them requires" is back
     above its test element, indented (G93); lerc's "No real information, keep conda-forge defaults" is back above
     `run_exports`. The commented-out `pytest` lines stay in the CFE comments blocks: they sit at column 0 in
     `meta.yaml` (G93).
  7. **LOW: pyobjc's CFE metadata named `version-bump-to-12.2.1`** while the feedstock is at 12.2.2. **Fixed:**
     `version-bump-to-12.2.2`, `cfe-last-checked` refreshed.
  8. **LOW: housekeeping.** **Fixed:** `review_loop_iteration: 2`; psycopg2-yugabytedb's `# mason-22.1:` and
     `# platform-expansion:` notes folded into `# Header:`; semgrep's block gains the canonical `# CFE metadata` section
     (no feedstock on conda-forge, checked 2026-10-09; `cfe-local-build-status: not-attempted`).

- 2026-10-09 independent review of the landing (`2ebf09ea75`, `56b56f62cd`, `348a7c9af1`): **failed**. Evidence in the
  session scratchpad `review-221/`. Dispositions:
  1. **pyautogui, AC 4 unmet** (the CFE block said `failed` while its comment called the failure "not a recipe defect";
     `yum_requirements.txt` missing; the python test rendered `imports: []` on linux). **Fixed:** the feedstock's
     `yum_requirements.txt` copied verbatim; the whole python test element now sits under `if: not linux`, as
     `meta.yaml`'s `# [not linux]` import says; rebuilt on a scratch copy with a pass-through `xvfb-run` shim on PATH,
     exit 0 for py3.11-3.14 with tests passing. The CFE block records `success` and the shim, and the contradiction is
     gone. AC 4 is met.
  2. **Comments dropped (AC 5; CFE's verbatim rule).** **Fixed:** psycopg2-yugabytedb's two upstream comments (yugabyte
     #12283) above the import; semgrep's commented `pip check` and its reason; django-pygwalker's commented `pip check`
     and its error list; boost's test, `run_constraints` and `run_exports` comments where they map, as shell comments
     inside the unix loops that replaced meta.yaml's jinja loops. The same class was found in amundsen-databuilder (its
     "Pip check disabled" note and commented `pip check` / `requires`) and fixed there too. The commented `pytest` lines
     of shodan and pyautogui stay in their CFE comments blocks, as this spec's table says.
  3. **shodan's python test ran on the newest python only** (meta.yaml pins `python {{ python_min }}` in its test).
     **Fixed:** `python_version: [${{ python_min }}.*, "*"]`; the rebuild ran imports and `pip check` on both.
  4. **Corpus check non-recursive; allowlist too wide.** `_recipe_files()` globbed `*/recipe.yaml`, missing the five
     nested recipes under `recipes/pixi/*`, `recipes/teradata/*` and `recipes/tolaria-app/vendored`; the allowlist
     exempted the whole ctng-compilers file. **Fixed:** every check scans recursively; the allowlist is keyed by file and
     location (`outputs[6].tests[0]` for ctng-compilers; `outputs[5].tests[0]` for vc after the second ruling). Live
     proofs: a sentinel planted at `recipes/zz-plant-221-group/nested/recipe.yaml` reds the check, and so does a second
     leak planted in ctng-compilers (both reverted).
  5. **CFE guidance wrong in three places.** **Fixed:** G121 says an inheriting output does not get the staging build
     environment; G121 no longer says `track_features` maps to `down_prioritize_variant` (it writes `<name>-p-0`; a
     0.76.1 v1-migration gap); the CHANGELOG no longer lists G1 as held (0.76.1 joins script entries into one
     `conda_build.sh`, so env vars carry), and G1 gains a dated note. G121 also gains the minijinja string-vs-int trap
     the review's `mj/` probe showed. The version stays `8.98.0`: the retro is unreleased.
  6. **Failure catalog dropped `validate_recipe` from G4, G7, G20, G24, G26, G29, G93 and G94.** G121's symptom made it a
     ninth row, over the generator's cross-row cap of eight. **Fixed:** G121's symptom names the check in words; the
     regenerated catalog changes only G121's row and the source hash.
  7. **vc port unfaithful** (`track_features` approximated by `down_prioritize_variant`; one of five variant entries
     hardcoded in `context`; `vc_repack.py`, `activate.bat`, `LICENSE.TXT` and `conda_build_config.yaml` missing;
     inheriting outputs calling `python` without declaring it; a string-vs-int `vsver` comparison). **Deferred** by the
     second operator ruling: Story 22.4 owns it, blocked on a rattler-build that emits a named track feature.

- 2026-10-09 landing preparation (operator ruling: land for eleven, split ctng-compilers into Story 22.3): boost's
  helper-script tests were replaced with inline per-platform loops (they had dropped the Windows and macOS checks and
  called `python` in an env without it); vc's dropped requirements, scripts and DLL loop were restored as v1 staging
  output, script calls and `for %%D` blocks; shodan, psycopg2-yugabytedb, StringZilla and lerc needed the gate fixes in
  the Spec Change Log. All gates in Run results. CFE retro v8.98.0 (G121 + corpus check) is a separate `retro(cfe):`
  commit. An independent review of the landing diff has not run (implementation and review stay separate).
- 2026-10-09 implement (bmad-build-auto): All 12 `recipe.yaml` files cleared of CRM sentinel keys (`grep -rl 'object at 0x'` clean). Render-only passes for 11/12 on spec platforms (pyobjc osx-64, vc win-64, others linux-64). **ctng-compilers** remains blocked on rattler-build 0.76.1 output cycle after v1 `run_exports` migration; validate_recipe passes. CFE retro drafted (G121, corpus test, v8.94.0) — land as separate `retro(cfe):` commit so mason meta-tests see a sanctioned CFE touch. Seven cheap `recipe-build` runs and full smithy lint matrix not completed this iteration. Independent adversarial review not run yet.
