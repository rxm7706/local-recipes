---
title: "29.1: pwndbg passes pip check with a local pwntools that carries the upstream unicorn fix"
type: 'fix'
created: '2026-10-12'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - recipes/pwndbg/recipe.yaml
  - recipes/pwndbg/build.sh
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `recipes/pwndbg` landed in PR #2168 with `pip_check: false`, because no unicorn version satisfies both of
its Python dependencies. Facts checked live on 2026-10-12:

| Package | unicorn requirement | Source |
|---|---|---|
| pwndbg 2026.09.15 | `unicorn>=2.1.4,<3` | `pyproject.toml`; floor raised to 2.1.4 in pwndbg `d98f0b708` (#3292) |
| pwntools 4.15.0, the latest release | `unicorn>=2.0.1, !=2.1.3, !=2.1.4` | 2.1.3 and 2.1.4 segfault when pwntools emulates a MIPS PLT (unicorn-engine/unicorn#2134) |
| conda-forge `python-unicorn` | newest is 2.1.4 | channel index |

pwntools fixed this on its `stable` branch in `7e5e79d00f` (Gallopsled/pwntools#2721, 2026-04-27). It lifts the
exclusion to `unicorn>=2.0.1`, and `pwnlib/elf/plt.py` raises an `OSError` for MIPS on 2.1.3 and 2.1.4 instead of
crashing. No pwntools release carries it yet.

A second defect sits in the same recipe. It lists conda-forge `unicorn`, which `conda-forge/unicorn-feedstock` builds as
the C library. The Python bindings (`import unicorn`) are its `python-unicorn` output, which pwndbg receives only
through pwntools' own dependency. pwndbg's `context.python_min: "3.10"` is also below conda-forge's floor (3.11), so
Rule 6 deletes it.

**Approach:**
1. Add `recipes/pwntools` as a mirror of `conda-forge/pwntools-feedstock`:
   - `meta.yaml` copied verbatim from the feedstock;
   - a v1 `recipe.yaml` beside it, with the same sources, dependencies, entry points and tests;
   - #2721 applied as `patches/0001-allow-unicorn-2.1.3-and-2.1.4-but-throw-when-emulating-mips.patch`, identical to
     the upstream commit's two hunks (`pyproject.toml`, `pwnlib/elf/plt.py`);
   - build number 1, above the feedstock's 0, so the patched build supersedes the published one in a local solve.
2. In `recipes/pwndbg`: `unicorn` becomes `python-unicorn >=2.1.4,<3`, `pip_check` returns to `true`, and
   `context.python_min` is deleted.
3. In `recipes/niche-elf` and `recipes/gdb-pt-dump`, pwndbg's local prerequisites: delete `context.python_min: "3.10"`,
   which is below the 3.11 floor (Rule 6). `test_no_redundant_python_min.py` reds both on `main` today.
4. Build pwntools, the three prerequisites, then pwndbg against the local channel, on linux-64.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-mason` CAP-18 (the local mirror as source of truth) and CAP-23 (recipe
  lifecycle machinery). No CAP is minted, and no `SPEC.md` text changes.
- **No flag.** This is a `fix` (`spec-feature-flag-governance` Q1).
- **Origin.** `docs/dreams/pyforge-mason.md` Realization log, 2026-10-12 (a local pwntools carries the upstream unicorn
  fix). Operator rulings 2026-10-12: "Fix the unicorn conflict"; "Backport #2721 locally (Recommended)".

## Acceptance Criteria

- **AC1 — pwntools builds with the backport.** `pixi run -e local-recipes recipe-build recipes/pwntools` exits 0 on
  linux-64. The artifact is `pwntools-4.15.0-*_1.conda`. Its wheel metadata reads `Requires-Dist: unicorn>=2.0.1`, with
  no `!=2.1.3` or `!=2.1.4`. Its own tests pass: `pip check`, both imports, and the 20 `--help` commands the feedstock tests (all entry points
  but `main` and `common`).
- **AC2 — The MIPS guard is in the shipped code.** The packaged `pwnlib/elf/plt.py` raises `OSError` from
  `prepare_unicorn_and_context` for a MIPS ELF when the installed unicorn is 2.1.3 or 2.1.4. The recipe's
  `test_mips_guard.py` calls it with a stand-in ELF whose `arch` is `mips` (the guard reads nothing else; no network, no
  cross toolchain) and expects the `OSError` on unicorn 2.1.3 or 2.1.4, and no `OSError` on any other version. An `amd64` stand-in never
  gets the `OSError`.
- **AC3 — pwndbg's dependencies are consistent.** `recipes/pwndbg` lists `python-unicorn >=2.1.4,<3` and no bare
  `unicorn`, has no `context.python_min`, and runs `pip_check: true`. Its build exits 0 on linux-64, its test
  environment resolves the local pwntools `_1` with `python-unicorn` 2.1.4, and `pip check` passes there. The existing
  gdb test (`pwndbg -batch -ex version`) still passes.
- **AC4 — Mirror fidelity.** `recipes/pwntools/meta.yaml` is byte-identical to the feedstock's `recipe/meta.yaml` at
  the commit the CFE block names. Only `recipe.yaml` carries the patch and the build-number bump.
- **AC4b — The prerequisites sit at the floor.** `recipes/niche-elf` and `recipes/gdb-pt-dump` carry no
  `context.python_min`, build green on linux-64, and `test_no_redundant_python_min.py` passes.
- **AC5 — Gates.** Both recipes pass `validate_recipe`, `optimize_recipe` (STD-002 is expected on the v0 mirror) and the
  CI-parity lint. Each CFE block records the real build. `recipes/pwntools`'s block names #2721 in
  `cfe-forge-recipe-updates-needed` with its revert trigger: drop the patch when a pwntools release carries #2721.
- **AC6 — Rule 2.** The story closes with its own `retro(cfe):` commit, carrying a CFE `CHANGELOG.md` semver entry.
- **AC7 — Mutation.** Each change below makes a named check fail:
  - restore the `!=2.1.3, !=2.1.4` exclusion in the patch: pwndbg's `pip check` (AC3);
  - put bare `unicorn` back in pwndbg's run deps and drop `python-unicorn`: the CFE meta-test
    `test_split_distribution_run_deps.py`;
  - drop the `plt.py` hunk: AC2's test.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` (Rule 1). Build on linux-64 only.
- Keep `recipes/pwntools/meta.yaml` verbatim; the CFE block lives in `recipe.yaml` alone.
- Keep the feedstock's maintainers in `recipe.yaml` and add `rxm7706` (G53).
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it, then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never open a feedstock, staged-recipes or upstream PR without an explicit ask.
- Never loosen pwndbg's own unicorn floor below 2.1.4: pwndbg raised it twice on purpose.
- Never touch `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`.

**Residual risk:**
- Any solve that sees the local channel or SelfExplainML takes this pwntools over conda-forge's (strict channel
  priority). That is the point of the mirror until a pwntools release carries #2721; the CFE block names the trigger.

## I/O & Edge-Case Matrix

| Case | Expected |
|---|---|
| pwndbg + pwntools `_1` + `python-unicorn` 2.1.4 | solves; `pip check` passes |
| pwndbg + conda-forge pwntools `_0` + `python-unicorn` 2.1.4 | solves; `pip check` fails, as today (why the mirror exists) |
| pwntools `_1`, MIPS ELF, unicorn 2.1.4 | `OSError` naming unicorn-engine/unicorn#2134 |
| pwntools `_1`, x86-64 ELF, unicorn 2.1.4 | no `OSError` from the guard |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-mason` CAP-18 and CAP-23. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-mason.md` § *Realization log*, the 2026-10-12 entry (a local pwntools carries the upstream
  unicorn fix).
- Epic: Epic 29 (new), minted with this story.
- Ledger key: `29-1-pwndbg-passes-pip-check-with-a-local-pwntools-that-carries-the-upstream-unicorn-fix`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."29"`, added with this mint.

## Verification

**Commands:**
- `pixi run -e local-recipes recipe-build recipes/pwntools` — expected: exit 0, artifact `pwntools-4.15.0-*_1.conda`.
- `pixi run -e local-recipes recipe-build recipes/pwndbg` — expected: exit 0, `pip check` passes in its test.
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `validate_recipe`, `optimize_recipe` and `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint
  --conda-forge` on both recipes — expected: clean, STD-002 aside.
- The AC2 MIPS-guard test against the built pwntools — expected: `OSError`.
- The three mutations of AC7 — expected: each fails its named check. Restore each.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected:
  exit 0 after the memlogs and scoped stamps.

## Run results

Built on linux-64 with `recipe-build` (rattler-build, local channel), 2026-10-12/13:

| AC | Result |
|---|---|
| AC1 | `pwntools-4.15.0-pyhf3c603f_1.conda`: wheel `Requires-Dist: unicorn>=2.0.1`; `depends` keeps `python-unicorn >=2.0.1`; build number 1; tests pass: `pip check`, both imports, and the feedstock's 20 `--help` commands. |
| AC2 | The shipped `pwnlib/elf/plt.py` carries the guard. `test_mips_guard.py` in the rebuilt package: mips and mips64 "guard raised on unicorn 2.1.4", amd64 "no guard". |
| AC3 | `pwndbg-2026.09.15` green. The test env resolves pwntools `pyhf3c603f_1` with `python-unicorn` 2.1.4 on Python 3.11 and 3.14. `pip check` reports "No broken requirements found" on both. The gdb test loads 199 pwndbg commands. |
| AC4 | `recipes/pwntools/meta.yaml` was fetched from the feedstock at `04c47d9c88` and is unmodified. |
| AC4b | `niche-elf` and `gdb-pt-dump` rebuilt green without `context.python_min`. `test_no_redundant_python_min.py` passes. |
| AC5 | `validate` passes for all four recipes. The CI-parity lint (`conda-smithy>=2026.6.14`) says "in fine form" for pwndbg and pwntools. `optimize`: pwntools STD-002 (v0 mirror, expected); pwndbg 3× PIN-001 (upstream's exact pins, which `pip check` enforces; already on `main`), and its SEL-004 is cleared. |
| AC6 | `retro(cfe):` v8.100.0 (G122 new, G107 second case, G84 refinement, mapping overrides in `custom.yaml`, test fallback floor). |
| AC7 | (1) conda-forge pwntools `_0`: `pip check` → "pwntools 4.15.0 has requirement unicorn!=2.1.3,!=2.1.4,>=2.0.1, but you have unicorn 2.1.4." (2) Bare `unicorn`: `test_split_distribution_run_deps.py` fails with "recipes/pwndbg/recipe.yaml: run lists `unicorn`, not `python-unicorn`". (3) Without the `plt.py` hunk, `test_mips_guard.py` fails: "guard did not fire on unicorn 2.1.4". |

Gates: the planning checks, `spec-surface-check`, `flag-gate-check`, `mason-cfe-surface-check`, `failure-catalog-check`
and `pyforge-mason-test` pass. The CFE suite: 9340 passed with one failure (`test_skill_md_consistency`, which flagged G122's cited
`plt.py`/`test_mips_guard.py`), fixed in the retro and re-run green. `detectors-ci`'s two findings came from the branch
predating doctor 46.1's landing and from the test-architecture matrix; `main` was merged and the matrix regenerated.

## Spec Change Log

- 2026-10-12: minted at the operator's rulings "Fix the unicorn conflict" and "Backport #2721 locally (Recommended)".
- 2026-10-12 (implementation): AC2 now names the stand-in ELF the test uses. Added approach item 3 and AC4b: the two
  prerequisites' below-floor `python_min` reds `test_no_redundant_python_min.py` on `main`, so it is fixed here
  (healed tissue); the Epic 29 boundary and `epic_surfaces."29"` widened to match.
- 2026-10-12 (review): AC1 and AC7 reworded and AC2 extended to amd64, as the Review Triage Log records. The retro also
  changed `name_resolver.py`, the mapping files and three tests; the Surface line in `epics.md` now lists them.

## Review Triage Log

### 2026-10-12 — Independent review (adversarial, separate agent)
- Verified clean: `meta.yaml` byte-identical to the feedstock; the v1 translation (22/22 run deps, 22/22 entry points,
  host, sha256, tests); the patch is exactly 7e5e79d00f's two hunks and applies to 4.15.0; the guard test fails without
  the `plt.py` hunk; `python-unicorn` is the bindings; the built artifacts; no attribution; CFE only in `retro(cfe):`.
- `[medium]` `[fixed]` The retro said lookups read `custom.yaml` first, but the MCP `get_conda_name` tool runs
  `name_resolver.py`, which read only its cache (still `unicorn → unicorn`). `name_resolver.py` gained a tier 0 that
  reads `custom.yaml`, with three unit tests, and G107 / the CHANGELOG name both resolvers.
- `[low-medium]` `[fixed]` AC7 mutation 2 had no machine check. New CFE meta-test
  `test_split_distribution_run_deps.py`; bare `unicorn` in pwndbg now fails it. Unlinted, it flags 16 playwright
  recipes; that pair is declared but not linted, and a separate audit task was raised.
- `[low]` `[fixed]` The retro's files were missing from the Surface line: widened in `epics.md`.
- `[low]` `[fixed]` AC1 over-promised (20 of 22 entry points are tested, as in the feedstock) and the amd64 matrix row
  was untested: AC1 reworded; `test_mips_guard.py` checks mips, mips64 and amd64, rebuilt and green.
- `[low]` `[fixed]` `sync_pypi_mappings.py` drops `custom.yaml` overrides silently without PyYAML: documented in G107;
  `name_resolver.py` warns.
- `[low]` `[reject]` The hand-edited `python-unicorn` row in `different_names.json` has a shape a sync never writes:
  harmless, follows the July playwright alias, and `custom.yaml` now carries the durable answer.
- `[low]` `[reject]` Ledger still `backlog`: the landing finalize promotes it (`dispatch_land_finalize`), as for
  every hand-landed story.
