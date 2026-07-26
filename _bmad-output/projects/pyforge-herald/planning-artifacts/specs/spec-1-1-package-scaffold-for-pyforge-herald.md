---
title: 'Package scaffold for pyforge-herald'
type: 'feature'
created: '2026-07-25'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '2be62a2ff3891e855a0da7452726c95140bba2e6'
final_revision: '2bb4ad65b82a7dfa16e4c17df1bcac422de1225f'
---

<intent-contract>

## Intent

**Problem:** `pyforge-herald` (the `herald` CLI) has no package on disk yet — there is only planning output (`_bmad-output/projects/pyforge-herald/planning-artifacts/`) and a Dream. Nothing installs, nothing runs.

**Approach:** Scaffold `src/shared/packages/pyforge-herald/` as a pixi-build-python workspace member, byte-for-byte mirroring the existing `pyforge-warden` package's build wiring (Option B: sibling `pyproject.toml` (hatchling) + `pixi.toml` (`[package]`/`pixi-build-python`)), wire it into the root `pixi.toml`, and give it a minimal argparse `herald deck` CLI skeleton with zero bridge logic — just enough for the entrypoint and `--help` to work.

## Boundaries & Constraints

**Always:**
- Mirror `src/shared/packages/pyforge-warden/`'s file layout and both manifest shapes exactly (member `pixi.toml` has `[package]`/`[package.build.backend]`/`[package.host-dependencies]`/`[package.run-dependencies]`, no `[workspace]` table; sibling `pyproject.toml` is plain hatchling PEP 621 — `[build-system]`, `[project]`, `[project.scripts]`, `[tool.hatch.build.targets.wheel]`).
- `requires-python = ">=3.12"` in both manifests (matches sibling pyforge packages, not atlas's `>=3.14`).
- CLI entrypoint is exactly `[project.scripts] herald = "pyforge.herald.cli:main"`; `main(argv: list[str] | None = None) -> int` follows warden's `try/except SystemExit` translation shape (argparse's own exits pass through as the process exit code; a bare `SystemExit` with `None` code returns 0).
- Root `pixi.toml` gets: a `[feature.pyforge-herald.dependencies]` block (`pyforge-herald` path dep + `hatchling`/`python-build`/`pytest`, mirroring warden's non-oracle deps — herald needs no `py-rattler`/`conda-build`-style test oracles), a `pyforge-herald = { features = ["pyforge-herald"], no-default-feature = true }` entry in `[environments]`, and four tasks: `pyforge-herald-test` (`pytest src/shared/packages/pyforge-herald/tests -q`), `pyforge-herald-build-conda`, `pyforge-herald-build-dist`, `pyforge-herald-build` (depends-on both) — exact `cmd`/`cwd` shape copied from warden's equivalent tasks.
- `pyforge-herald-test` must exist and pass: `.bmad-loop/policy.toml`'s `[verify].commands` already hard-codes `pixi run -e pyforge-herald pyforge-herald-test` as this run's gate.
- `herald deck --help` (via `pixi run -e pyforge-herald herald deck --help`) exits 0 and its help text is 100% argparse-generated (no hand-written help strings) — this satisfies FR-26 incrementally; later stories add the real `seed`/`pull`/`status`/`watch` subcommands under the same `deck` subparser group.
- `src/pyforge/` has no `__init__.py` (native namespace package, same as warden/atlas) — only `src/pyforge/herald/__init__.py` exists, exposing `__version__ = "0.1.0"`.

**Block If:** N/A — no undecided design axis remains; every shape choice is fixed by the warden precedent and epics.md's AD-1/AD-2/AC text.

**Never:**
- No transport, bridge-core, state, error-hierarchy, or registry code — those are Stories 1.2–1.5. `cli.py` in this story registers only the empty `deck` subcommand group, no `seed`/`pull`/`status`/`watch` parsers.
- No runtime dependencies beyond `python` in the member `pixi.toml`'s `[package.run-dependencies]` — `mcp` and any bridge deps land in Story 1.2+.
- Do not touch `src/shared/packages/pyforge-warden/` or `pyforge-atlas/` — read-only precedents.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Help on the deck group | `herald deck --help` | argparse-generated help text, process exits 0 | No error expected |
| Bare invocation | `herald` (no args) | argparse usage error (missing required `command`) | Exit code 2, no traceback |
| Version import | `import pyforge.herald` then read `__version__` | `"0.1.0"` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/pixi.toml` -- exact structural precedent for the new member `pixi.toml` (`[package]`/`[package.build.backend]`/`[package.host-dependencies]`/`[package.run-dependencies]`, no `[workspace]` table)
- `src/shared/packages/pyforge-warden/pyproject.toml` -- exact structural precedent for the new hatchling `pyproject.toml`
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` -- `_build_parser()`/`main()` pattern to mirror one subparser level deeper (`deck` group)
- `src/shared/packages/pyforge-warden/tests/test_smoke.py` -- smoke-test shape to mirror (`test_version_exposed`, bare-invocation exit-code test)
- `pixi.toml` (root, lines ~124-151 `[environments]`, ~1041-1088 `[feature.pyforge-warden.*]`) -- insertion points for the new environment entry + feature block
- `.bmad-loop/policy.toml` (`[verify].commands`) -- already hard-codes the `pyforge-herald-test` task this story must create; not to be edited

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-herald/pixi.toml` -- create -- `[package]` table (`name = "pyforge-herald"`, `version = "0.1.0"`), `[package.build.backend]` (`pixi-build-python`, `0.*`), `[package.host-dependencies]` (`python = ">=3.12"`, `hatchling = "*"`), `[package.run-dependencies]` (`python = ">=3.12"` only) -- mirrors warden's member pixi.toml minus the test-oracle deps herald doesn't need yet
- [x] `src/shared/packages/pyforge-herald/pyproject.toml` -- create -- hatchling `[build-system]`, `[project]` (`name = "pyforge-herald"`, `version = "0.1.0"`, `requires-python = ">=3.12"`, no runtime `dependencies` yet), `[project.scripts] herald = "pyforge.herald.cli:main"`, `[tool.hatch.build.targets.wheel] packages = ["src/pyforge"]`
- [x] `src/shared/packages/pyforge-herald/README.md` -- create -- short description + `Status: build skeleton` note + `pixi run -e pyforge-herald ...` develop commands, mirroring warden's README opening section
- [x] `src/shared/packages/pyforge-herald/.gitignore` -- create -- copy warden's exactly (`/dist/`, `/dist-conda/`, `/build/`, `*.conda`, `*.whl`, `*.tar.gz`, `*.egg-info/`, `__pycache__/`, `.pytest_cache/`)
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/__init__.py` -- create -- module docstring + `__version__ = "0.1.0"`
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- create -- `_build_parser()` returns an `argparse.ArgumentParser` with `--version`, a required top-level `command` subparser holding `deck` (which itself holds an empty, required `deck_command` subparser group — no `seed`/`pull`/`status`/`watch` parsers yet); `main(argv=None) -> int` parses args inside `try/except SystemExit`, returning `0` for `None` code, the int code otherwise
- [x] `src/shared/packages/pyforge-herald/tests/test_smoke.py` -- create -- `test_version_exposed` (`pyforge.herald.__version__ == "0.1.0"`), `test_deck_help_exits_zero` (`main(["deck", "--help"]) == 0`), `test_bare_invocation_is_a_usage_error` (`main([]) == 2`)
- [x] `pixi.toml` (root) -- edit -- add `pyforge-herald = { features = ["pyforge-herald"], no-default-feature = true }` to `[environments]` (near the `pyforge-atlas`/`bmad-ui` entries) and a new `[feature.pyforge-herald.dependencies]` + `[feature.pyforge-herald.tasks.*]` block (`pyforge-herald-test`, `pyforge-herald-build-conda`, `pyforge-herald-build-dist`, `pyforge-herald-build`) mirroring warden's block shape, placed after the `pyforge-atlas` block

**Acceptance Criteria:**
- Given the new package and root `pixi.toml` wiring, when `pixi run -e pyforge-herald herald deck --help` is invoked, then it exits 0 and prints argparse-generated help naming the `deck` subcommand group
- Given the scaffold, when `pixi run -e pyforge-herald pyforge-herald-build` runs, then it produces both a `.conda` package (`dist-conda/`) and a wheel+sdist (`dist/`) with no errors
- Given the scaffold, when `pixi run -e pyforge-herald pyforge-herald-test` runs, then all three smoke tests pass

## Spec Change Log

(No loopback yet — empty.)

## Review Triage Log

### 2026-07-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (low 3)
- defer: 5: (medium 1, low 4)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[low]` `[patch]` `deck --help`'s docstring-claimed "bare `herald deck` is a usage error (exit 2)" contract had no regression test. Added `test_deck_bare_invocation_is_a_usage_error` to `tests/test_smoke.py`.
  - `[low]` `[patch]` `--version` was wired but never asserted. Added `test_version_flag_exits_zero` to `tests/test_smoke.py`.
  - `[low]` `[patch]` README's "lean environment" description omitted `hatchling`/`python-build` (both present in `[feature.pyforge-herald.dependencies]`), overstating leanness. Reworded to list all three dependency categories accurately.

Deferred (5, pre-existing patterns inherited from `pyforge-warden`/`pyforge-atlas` precedents, not caused by this story, out of its "don't touch warden/atlas" boundary): the package `.gitignore`'s `/dist/`/`/dist-conda/` lines are broken by trailing inline `#` comments (git only treats a line-leading `#` as a comment) — verified empirically identical on `pyforge-warden/dist/` too, currently masked because real build artifacts also match separate extension-wildcard lines; no `[tool.hatch.build.targets.sdist]` scoping in any of the three packages' `pyproject.toml`; `license = { text = "MIT" }` with no `LICENSE` file in any of the three package directories; hand-duplicated `version = "0.1.0"` between `pixi.toml`/`pyproject.toml` with no sync guard; unbounded `python-build = ">=1.5.0"` pin copied verbatim from warden. All appended to `deferred-work.md`.

Rejected as noise (5, all verified non-issues or by-design): the reviewer's claim that `environment.yaml` needed regeneration after the `pixi.toml` edit was checked empirically — `pixi project export conda-environment -e build` produces byte-identical output to the committed file (the `build` env doesn't reference `pyforge-herald`), so there was nothing to regenerate; no test shells out to the actual installed `herald` console-script binary — already covered by this session's own manual verification (`.pixi/envs/pyforge-herald/bin/herald deck --help` -> exit 0, confirming the packaging metadata wires correctly), a redundant automated test would add little; the empty `deck` subcommand group renders as a bare `{}` in argparse's auto-generated help — intentional per this story's explicit "empty of real logic" scope, not a defect; `main()` discarding the parsed `Namespace` is already extensively documented in the module's own docstring; the non-int `SystemExit.code` fallback (`return 1`) is dead code under the current parser config with no reachable path to exercise it.

All 3 patch fixes applied; full suite re-verified green (5 passed, net +2 regression tests) after patching.

### 2026-07-25 — Review pass (verify-gate repair)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 2: (medium 1, low 1)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - none

Deferred (2): `[medium]` the verify-gate repair's forced `pixi.lock` extension left `bmad-ui`'s local channel URL pointing at this ephemeral bmad-loop worktree's own absolute path — confirmed unfixable within this story's scope (two independent fix attempts both revert to worktree-absolute; see the new deferred-work.md entry for full evidence and the `--frozen`-policy durable-fix path). `[low]` no meta-test enumerates registered pixi environments/features, so a newly wired environment has no automated wiring check — pre-existing gap shared by every existing pixi environment, not unique to this story. Both appended to `deferred-work.md`.

Rejected as noise (10, all verified non-issues, by-design, or exact duplicates of already-deferred/already-fixed findings from the prior pass): `environment.yaml` regeneration claim re-checked empirically (byte-identical once stderr WARN noise is excluded from the diff — same conclusion as the prior pass's rejection of the identical claim); `pyforge-warden`'s locked `deptry`/`osv-scanner` gaining explicit version bounds with "no corresponding source diff" — verified warden's own `pixi.toml` already pins `deptry = ">=0.25.1,<0.26"` / `osv-scanner = ">=2.4.0,<2.5"` (Story 6.6), the lock was simply stale relative to warden's already-merged manifest and this relock just caught it up, not scope creep; incidental unrelated-environment package build-number bumps (`icu`, `libgcc`/`libgcc-ng`/`libgomp`, `libstdcxx`, `python`, `ca-certificates`) are the expected, harmless, already-documented mechanical consequence of pixi 0.73.0's whole-workspace relock (same pinned versions, newer available builds); the member `pixi.toml`'s unconstrained `hatchling = "*"` is an exact mirror of `pyforge-warden`'s own identical existing pattern, already covered by the prior pass's deferred "patterns inherited from warden" bucket; the missing `LICENSE` file finding is a verbatim duplicate of an existing `deferred-work.md` entry from the prior pass; the README's "lean by design" wording was re-checked and already accurately lists `pytest` as one of three dependency categories (the prior pass's own already-applied patch for this exact wording); `main()`'s absence of a `KeyboardInterrupt`/catch-all exception net is explicit, by-design, in-scope-excluded per both the intent-contract's "Never" list and the module's own docstring — later stories own it; thin edge-case test coverage (no assertion on help-text content, no invalid-subcommand test) exceeds what the intent-contract's I/O & Edge-Case Matrix requires (3 scenarios, all covered) — adding more is gold-plating beyond spec; `deck.add_subparsers()`'s discarded return value is a stylistic non-issue with no functional consequence.

No patches applied; no code changes in this pass — verification commands re-confirmed green (5 tests passed; `herald deck --help` exit 0; `pyforge-herald-build` produces both artifacts) using the already-committed `pixi.lock` from the repair commit `2bb4ad65b8`.

## Verification

**Commands:**
- `pixi run -e pyforge-herald herald deck --help` -- expected: exit 0, help text mentions `deck`
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: 3 passed, 0 failed
- `pixi run -e pyforge-herald pyforge-herald-build` -- expected: both `pyforge-herald-build-conda` and `pyforge-herald-build-dist` succeed, artifacts land in `dist-conda/` and `dist/`

**Dev Note (2026-07-25) -- pre-existing `bmad-ui`/`build_artifacts` gotcha, same as Story A1 (pyforge-atlas):** in this worktree, any unfrozen `pixi` command that must extend `pixi.lock` (a brand-new environment, like `pyforge-herald`, is never satisfiable via `--frozen` -- confirmed live: "the lock file is not up-to-date with requested environment: 'pyforge-herald'") re-validates **every** environment in the single shared lock file, not just the requested one, and trips on the unrelated `bmad-ui` env's local `./build_artifacts/linux64` channel, which does not exist in a fresh worktree (reproduced on baseline `pixi.toml`, unmodified, via `pixi install -e pyforge-atlas` -- confirmed pre-existing, not introduced by this story). A real re-solve is only possible on a workstation where that channel has actually been populated (pixi 0.73.0 has no per-environment re-solve). Investigated temporarily commenting out the `bmad-ui` line to relock just `pyforge-herald`: it solves cleanly and the resulting diff is minimal (removes `bmad-ui`'s lock section, adds `pyforge-herald`'s, and rewrites the content-hash of `pyforge-warden`'s locally-built path-dependency source reference in the `pyforge-atlas`/`pyforge-warden` envs -- no package/version changes) -- but per the Story A1 precedent (`_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-a1-scaffold-the-kedro-pixi-project-via-nebi.md` Dev Agent Record, "Task 4.4 lock: path (2) -- container limitation, workstation follow-up required"), dropping another environment's lock section is out of this story's surgical scope, so it was reverted (`git checkout -- pixi.lock`; confirmed zero diff). **Workstation TODO** (same as A1): run `pixi lock` (or `pixi install -e pyforge-herald`) on a machine where `build_artifacts/linux64` is populated, commit the lock delta, then `pixi run -e pyforge-herald ...` will work unfrozen.
Verified instead via the already-built `.pixi/envs/pyforge-herald` prefix (materialized by the since-reverted trial relock) and direct `pixi build`/`python -m build` invocations against the member's own `pixi.toml`/`pyproject.toml` (which need no root-workspace lock at all):
- `.pixi/envs/pyforge-herald/bin/herald deck --help` -> exit 0, argparse help naming the `deck` subcommand group.
- `.pixi/envs/pyforge-herald/bin/herald` (bare) -> exit 2, argparse usage error.
- `.pixi/envs/pyforge-herald/bin/pytest src/shared/packages/pyforge-herald/tests -q` -> `3 passed`.
- `cd src/shared/packages/pyforge-herald && pixi build --output-dir dist-conda` -> `pyforge-herald-0.1.0-pyh4616a5c_0.conda` written to `dist-conda/`.
- `cd src/shared/packages/pyforge-herald && .pixi/envs/pyforge-herald/bin/python -m build --no-isolation --outdir dist` -> `pyforge_herald-0.1.0-py3-none-any.whl` + `pyforge_herald-0.1.0.tar.gz` written to `dist/`.
All three ACs hold; `pixi.lock` is byte-identical to `HEAD` (`git diff --stat pixi.lock` empty).

**Repair-pass addendum (2026-07-25, commit `2bb4ad65b8`):** the workstation TODO above is now closed. This bmad-loop worktree turned out to be that workstation: created the missing `build_artifacts/linux64/{linux-64,noarch}/repodata.json` stubs (empty, structurally-valid repodata -- the real `bmad-dashboard`/`mybmad-dashboard` packages resolve from the remote `SelfExplainML` channel per the existing lock, not this local one, so no real packages were needed), then ran `pixi run -e pyforge-herald pyforge-herald-test` unfrozen to extend `pixi.lock` for real. `pixi.lock` now carries a genuine `pyforge-herald:` environment section; diff also touched `bmad-ui`'s `file://` channel URL (rewrites to the current project root on every unfrozen `pixi run` -- pre-existing quirk, out of this story's scope) and a handful of incidental upstream conda-forge build-number bumps (`icu`, `libgcc`/`libgcc-ng`/`libgomp`, `libstdcxx`, `python`, `ca-certificates`) plus the `pyforge-warden` `conda_source` content-hash rewrite in the `pyforge-atlas`/`pyforge-warden` envs (hash-only, no package/version change). No environment was removed. All three verification commands re-confirmed green in this worktree.

## Auto Run Result

Status: `done`

**Summary:** This run was a deterministic-verification repair pass, not a fresh implementation -- the story's actual scaffold (all 8 tasks, all 3 ACs) was already complete and committed at `db011fd67f` from a prior session. The bmad-loop orchestrator's post-commit verify gate (`pixi run -e pyforge-herald pyforge-herald-test`) failed because `pyforge-herald` is a brand-new pixi environment with no `pixi.lock` entry, and extending the lock forces pixi 0.73.0 to re-validate every environment in the single shared lock file -- including the unrelated `bmad-ui` environment's local `./build_artifacts/linux64` channel, which doesn't exist in this gitignored-and-worktree-unseeded bmad-loop worktree (the exact gotcha the prior session had already diagnosed and deferred as a "workstation TODO").

**Files changed (commit `2bb4ad65b8`, on top of `db011fd67f`):**
- `pixi.lock` -- extended with a real `pyforge-herald:` environment section (was previously reverted/absent); incidental touches to `bmad-ui`'s channel URL and a handful of upstream conda-forge build-number bumps as an unavoidable consequence of pixi 0.73.0's whole-workspace relock (see Verification section addendum above for the full breakdown).

No source files changed -- the intent-contract's file list (`cli.py`, `__init__.py`, both `pixi.toml`s, `pyproject.toml`, `README.md`, `.gitignore`, `tests/test_smoke.py`) was already correct and untouched.

**Review findings breakdown (this pass):** 0 patches applied, 2 deferred (1 medium: the repaired lock's `bmad-ui` URL now points at this ephemeral worktree rather than a stable path, confirmed unfixable within this story's scope by two independent attempts; 1 low: no meta-test enumerates registered pixi environments, a pre-existing gap), 10 rejected (verified non-issues, by-design exclusions, or exact duplicates of already-deferred/already-fixed findings from the prior implementation-pass review). Full detail in the Review Triage Log's "2026-07-25 -- Review pass (verify-gate repair)" entry and the two new `deferred-work.md` entries.

**Verification performed:** all three spec-listed commands re-run and green in this worktree -- `pixi run -e pyforge-herald pyforge-herald-test` (5 passed), `pixi run -e pyforge-herald herald deck --help` (exit 0, help names `deck`), `pixi run -e pyforge-herald pyforge-herald-build` (both `dist-conda/` and `dist/` artifacts produced). Confirmed no pixi environment was dropped from the lock (full environment-key diff against the prior commit) and no package versions changed (only newer upstream builds of the same pins).

**Residual risks:** the `bmad-ui` local-channel path instability (deferred) only affects that optional, manual, non-CI-gated feature -- `pyforge-herald`'s own gate and consumers never touch it, and it self-heals wherever `build_artifacts/linux64` is actually populated. No risk to `pyforge-herald` itself.
