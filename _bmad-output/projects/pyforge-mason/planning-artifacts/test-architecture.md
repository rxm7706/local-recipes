---
title: "Test Architecture — pyforge-mason"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "All 38 stories (E1–E5). 4/38 done (Epic 1 partial); 34/38 pending. Real coverage documented for done stories; planned coverage documented for pending stories — nothing invented."
target_coverage: "Unit ≥80% on shipped modules; meta-tests enforce the CFE-wrapping seam (AD-1–AD-16) at every epic boundary; no fixed IT/E2E target yet — Epic 2–5 test shape depends on the fake-CFE-root harness (Story 1.9) not yet built"
---

# Test Architecture — PyForge Mason

## Executive Summary

This document replaces a fabricated placeholder discovered on 2026-08-02: the prior
`test-architecture.md` (78 lines) was generic template boilerplate — every row read
"Target Stories: TBD," and its Executive Summary mischaracterized Mason as a recipe
**linting/schema-validation** tool. That is not what Mason is. It was produced in a bulk
commit alongside a false migration note and other fabricated content, all found and
remediated this session. This document is the real replacement.

**Mason** is the Artisan Builder's CLI: it wraps `conda-forge-expert` (CFE) behind a
knowledge-free "seam" so a user can author/build/submit conda-forge recipes, ship a
library to PyPI + a conda channel + conda-forge in one command, and bind mixed
conda/pip dependencies into one lockfile — without Mason itself containing a single
line of recipe judgement, pin table, or conda-forge policy constant. Per
`_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md`, the product is 5
epics / 38 stories / 50 FRs / 16 ADs.

**Mason is 11% code-complete: 4 of 38 stories done, all four inside Epic 1** (Stories
1.1–1.4 — workspace scaffold, CLI noun-verb structure, error/exit-code taxonomy, dual
output format). Stories 1.5–1.10 and all of Epics 2–5 are **not yet implemented** — no
`cfe.py`, no `recipe.py`, no `package.py`, no `environment.py`, no `engines/` directory,
and no `tests/integration/` or `tests/e2e/` directory exist in the repo today.

Because of that, **this document is mostly prospective**: a small § *Real Coverage
Today* section documents what actually exists and passes, and the much larger
remainder documents planned coverage per epic — test **level** and what each future
test must prove, without naming a test file that has not been written. Per-story rows
for pending work state "not yet implemented" explicitly rather than leaving a
placeholder.

---

## Real Coverage Today (Epic 1, Stories 1.1–1.4)

**8 real test files, 119 passing tests**, all under
`src/shared/packages/pyforge-mason/tests/` (`tests/meta/` + `tests/unit/` only — no
`tests/integration/` or `tests/e2e/` directory exists yet). Verified this session via
`pixi run -e pyforge-mason pyforge-mason-test` → `119 passed in 0.26s`.

| Story | Title | Test file(s) | What it verifies |
|-------|-------|---------------|-------------------|
| **1.1** | Workspace member scaffold and dual-artifact build | `tests/meta/test_namespace_is_implicit.py` | PEP 420 namespace root has no `src/pyforge/__init__.py` (so sibling stations coexist); `pyforge.mason` package itself does have one; FR-41/NFR-10 — manifest parsed for a banned `click`/`typer` dependency, not grepped (a prior text-scan version false-positived on its own explanatory comment) |
| **1.1** (forward-pinned) | — | `tests/meta/test_dependency_direction.py` | AD-2 — only `cli.py`, `cfe.py`, and `engines/*.py` may `import subprocess`; AST-based (not regex) so a comment mentioning "subprocess" isn't flagged; `cfe.py`/`engines/` don't exist yet, so the guard is "vacuous-but-real" today — it starts actually excluding files the moment Epic 2 lands them; also carries synthetic-fixture regression tests for the detector itself (unreadable/non-UTF-8/invalid-syntax files fail loudly, not with a raw traceback) |
| **1.2** | CLI noun-verb structure and global flags | `tests/unit/test_cli.py` | `mason --version` reports the installed version; bare `mason` prints help and exits 0 (not treated as a diagnostic); `--help` lists all four nouns (`recipe`, `package`, `environment`, `doctor`); a bare noun with no verb is a usage error |
| **1.3** | Error taxonomy and exit-code contract | `tests/unit/test_errors.py` | `MasonError` identifier must match the `word:word` colon-delimited pattern (parametrized valid/invalid cases incl. non-str identifier, empty/whitespace-only message, non-str message); `str(exc)` renders as `identifier: message` |
| **1.3** | — | `tests/unit/test_exit_codes.py` | Pins the exact integer value of every exit code: `EXIT_OK=0`, `EXIT_FAILED=1`, `EXIT_USAGE=2`, `EXIT_CFE_UNAVAILABLE=3`, `EXIT_INTERRUPTED=130` |
| **1.3** | — | `tests/meta/test_exit_code_ownership.py` | AD-7 — only `exit_codes.py` may define a module-level `EXIT_*` name; AST-based scan recurses through nested statements (if/try/for/while/with) and recognizes every module-level binding form (assign, unpack, annotated, augmented, walrus, `for`/`with as`, `except as`, `def`/`class`, `import as`), so a platform-conditional `if sys.platform == "win32": EXIT_WIN = 75` is caught — the realistic drift a shallower top-level-`Assign`-only scan would miss |
| **1.4** | Dual output format with stream discipline | `tests/unit/test_render.py` | The 5-key envelope (`schema_version`, `command`, `status`, `data`, `errors`) is exactly right; `render_json` is deterministic and key-order-independent; `write` emits exactly one JSON document plus one trailing newline (byte-equality, not just `json.loads`-parseable); text format renders a human-readable summary through the same `write` entry point; `write` never invokes the other format's renderer (verified via `monkeypatch`); stream is flushed |
| **1.4** | — | `tests/meta/test_render_ownership.py` | AD-8 — only `cli.py` and `render.py` may write to stdout; AST-based scan recognizes `print(...)` without a `file=stderr` keyword and `.write()`/`.writelines()` targeting `sys.stdout`/`sys.stdout.buffer`/a bare `stdout` name; `parser.print_help()` is explicitly out of scope (method name is `print_help`, not `print`/`.write`) |

Note: `tests/unit/test_cli.py`'s own docstring states it exercises Stories 1.2 + 1.3 +
1.4 **together** (the noun→verb tree, global flags, the exit-code/`MasonError`
projection inside `main()`, and `doctor`'s stub dual-output contract) — the table above
attributes it to 1.2 because that is its primary subject, but its `main()`-level
assertions are genuinely shared with 1.3 and 1.4's error/output paths.

**Not yet covered by any test, because not yet built**: Stories 1.5–1.10 (CFE root
resolution, interpreter selection, degradation, `mason doctor`, the fake-CFE-root
fixture, configuration/logging/streaming). See § *Epic 1 — Remaining Stories* below.

---

## Architecture Context: Why the Seam Dominates This Test Plan

Per `epics.md`, Mason's central guarantee (AD-1, "knowledge-free core") is that it
**wraps** conda-forge-expert and never re-implements recipe judgement. `cfe.py` (Story
2.1) is declared the **sole** CFE caller (AD-3/AD-4); every other module reaches CFE
only through it. `epics.md` calls out **Story 2.2 (the seam guard) as the critical-path
story**: it lands the meta-tests that make this guarantee mechanically enforced rather
than merely documented, specifically because a documentation-only guarantee is exactly
what failed on the sibling `pyforge-atlas` effort (a second implementation crept in
despite stated intent).

This shapes the test architecture in two ways that don't apply to Marshal or other
PyForge stations:

1. **Meta-tests are load-bearing, not supplementary.** Three of Mason's stories —
   2.2 (seam guard), 5.1 (CFE-independence), 5.2 (governance) — exist *specifically to
   produce* `tests/meta/*.py` files, not application code. `tests/meta/` will grow
   faster relative to `tests/unit/` than is typical.
2. **A "fake CFE root" test harness is a prerequisite, not a nice-to-have.** Story 1.9
   builds `tests/fixtures/fake_cfe_root/` — a synthetic mirror of CFE's real script
   layout with stub scripts emitting canned stdout/exit codes. Every Epic 2 recipe-verb
   test (2.4–2.10) and most of Epic 3's ship-target tests depend on it; until 1.9 ships,
   Epic 2/3 integration tests cannot be written in a form that "passes anywhere and
   never requires the real machinery" (the story's own acceptance criterion).

**Test-enablement sequencing risk** (derived from `epics.md`'s own dependency table,
not asserted independently): Story 1.9 (fixture harness) and Story 2.2 (seam guard) sit
on the critical path for *test-writability itself*, separate from the product's own
feature dependency order. A team could build Stories 2.4–2.10 against a real CFE
install and defer 1.9 — but that would mean Epic 2's tests fail the "passes anywhere,
no real CFE" bar epics.md sets for them until 1.9 lands retroactively. The order this
document assumes for planned-coverage purposes is: **1.9 → 2.1 → 2.2 → (2.3–2.10 in any
order) → 3.1 → (3.2–3.9) → (4.1–4.4 in parallel with Epic 3) → 5.1/5.2/5.3 → 5.4 → 5.5**.

---

## Epic 1 — Remaining Stories (1.5–1.10, all pending)

None of these six stories are implemented; no test files exist for them yet.

| Story | Title | Planned level(s) | What the test must prove once built |
|-------|-------|-------------------|----------------------------------------|
| **1.5** | CFE root resolution chain | Unit | The 4-step chain (`--cfe-root` → `MASON_CFE_ROOT` → upward filesystem walk → not-found) resolves in priority order against synthetic directory trees; the resolver performs filesystem reads only (AD-5 — no writes, no network, no subprocess); an upward walk reaching the filesystem root returns a not-found outcome, not an exception |
| **1.6** | Interpreter selection and CFE import-floor probe | Unit | The interpreter chain (`--cfe-python` → `MASON_CFE_PYTHON` → `sys.executable`) resolves correctly; the import-floor probe (pyyaml, requests, packaging, truststore, ruamel.yaml, conda-forge-metadata) is cached for the process lifetime; a missing-module interpreter surfaces a typed error naming the gap, never a raw subprocess `ImportError` traceback |
| **1.7** | Degradation when CFE is unavailable | Unit + meta | Any `mason recipe` verb exits 3 with a message naming all four resolution steps when CFE is unresolvable, with no Python traceback; `mason package`/`mason environment` verbs behave identically with or without CFE present; a meta-test (AD-6) confirms `import pyforge.mason.package` succeeds with no CFE anywhere on the filesystem |
| **1.8** | `mason doctor` | Integration | Reports Mason version, resolved CFE root **and which resolution step found it**, selected interpreter + import-floor status, and each known engine's presence/version; exits 0 (not an error) when CFE is absent, naming which verbs are consequently unavailable; `--format json` conforms to the FR-31 envelope already proven generically in `test_render.py` |
| **1.9** | Fake CFE root fixture and test harness | Infrastructure (enables IT for Epic 2+) | `tests/fixtures/fake_cfe_root/` mirrors CFE's real script layout (`.claude/scripts/conda-forge-expert/<script>.py`) with stub scripts emitting canned stdout + configurable exit codes, including a leading-progress-line-before-JSON variant (exercises the tolerant-parsing path Story 2.1 needs); a `slow` pytest marker is registered, mirroring the `pyforge-warden` convention, excluded from the default test task; the whole suite (minus the one FR-46 fidelity test) must pass with no real CFE install, no network, and no `recipes/` directory present |
| **1.10** | Configuration surface, logging, and child-output streaming | Unit + integration | Every v1 knob (`--cfe-root`/`MASON_CFE_ROOT`, `--cfe-python`/`MASON_CFE_PYTHON`, `--cfe-timeout`/`MASON_CFE_TIMEOUT`, `--format`, `--verbose`, `--quiet`) works in both flag and env forms with flag→env→default precedence; a test asserts every knob has both forms (AD-13 — no config file is ever read); no log record contains an environment-variable **value**; a streaming child-process test asserts stderr passes through live while `--format json` still emits exactly one stdout document |

---

## Epic 2 — Author, build, and submit recipes (10 stories, all pending)

None of Epic 2 is implemented — no `cfe.py`, `recipe.py`, or `engines/` module exists.
Depends on Story 1.9's fixture harness for any integration-level test.

| Story | Title | Planned level(s) | What the test must prove once built |
|-------|-------|-------------------|----------------------------------------|
| **2.1** | The CFE port | Unit | `cfe.py` invokes `[interpreter, script_path, *args]` via subprocess with a mandatory timeout, list argv only (never `shell=True`); returns a `CfeResult` (return code, stdout, stderr, parsed JSON body) where a non-zero return code is data, not a raised exception; extracts a JSON body preceded by a non-JSON progress line; a timeout raises a distinct typed error and leaves no orphaned child process; AD-4 verified — no `import`/`importlib`/`exec` of CFE code anywhere in `pyforge.mason` |
| **2.2** | The seam guard | **Meta (this story delivers the test files)** | Delivers `tests/meta/test_no_recipe_knowledge.py` (fails if any Mason module contains a gotcha identifier, policy constant, pin table, v1 recipe-field default, or selector/platform rule — with **positive fixtures planting a violation in each deny-list category**, so a deny-list matching nothing is a failing test) and `tests/meta/test_adapter_sole_caller.py` (fails if any module but `cfe.py` references a CFE path/script/process). Both must run in the default (non-`slow`) test task. **Critical path** — every story in Epics 2–5 built after this one is guarded by it. |
| **2.3** | Credential isolation | Unit + meta | No module reads any `JFROG_*` env var or makes an authenticated HTTP request on CFE's behalf; credentials reach CFE only via inherited process environment; a sentinel-credential test confirms no credential value appears in stdout, stderr, or any produced artifact at any verbosity |
| **2.4** | `mason recipe new` | Integration (needs 1.9 fixture) | `--from-pypi`/`--from-github`/`--from-cran`/`--from-npm` each invoke the matching CFE generator through the adapter; the written `recipe.yaml` matches the fixture generator's direct output byte-for-byte (Mason applies no defaults/rewriting of its own); a CFE-reported generation failure becomes a typed error with CFE's message preserved |
| **2.5** | `mason recipe validate` | Integration | Non-zero exit on validation failure; CFE's finding identifiers preserved verbatim (never renumbered/reworded/re-severitied); `--format json` places findings in the envelope's `data` field |
| **2.6** | `mason recipe build` | Integration | Native host-platform build by default; a CI-parity/Docker build requires an explicit flag, never selected implicitly; artifact path + exit status reported in both formats; a timeout surfaces Story 2.1's typed timeout error with no orphaned process |
| **2.7** | `mason recipe diagnose` | Integration | CFE's failure analyzer is invoked and its diagnosis rendered; when CFE returns no diagnosis, Mason states that plainly and offers no cause/guess of its own |
| **2.8** | `mason recipe optimize` and `mason recipe scan` | Integration | `optimize` preserves CFE's check codes verbatim; `scan` renders CFE's scanner findings with no Mason-side severity policy or filtering; both place findings in the `data` field under `--format json` |
| **2.9** | `mason recipe submit` | Integration | No confirming flag → dry run, nothing pushed/opened; confirming flag → CFE's two-phase flow (prepare branch, then open PR) preserved as separately addressable phases; success returns a `ShipTargetResult` with `state=pending` and a PR-identifier `reference`; this becomes the **one** staged-recipes-submission implementation Epic 3's `conda-forge` ship target (3.6) will call rather than duplicate |
| **2.10** | `mason recipe update` | Integration | Proposed change displayed before any write; `--dry-run` shows the diff and modifies nothing; on confirmation, only the fields CFE's updater actually changed are written |

---

## Epic 3 — Ship a library to both ecosystems (9 stories, all pending)

None of Epic 3 is implemented — no `package.py` or `engines/` adapters exist.

| Story | Title | Planned level(s) | What the test must prove once built |
|-------|-------|-------------------|----------------------------------------|
| **3.1** | Engine protocol and provisioning | Unit + meta | Every engine adapter implements `name`, `probe() -> version \| None`, and its operation; engines are discovered on `PATH` only, nothing downloaded at runtime; a missing engine surfaces a typed error naming it and how to provision it, never a raw `FileNotFoundError`. The story's own AC names a specific meta-test file to be created — `tests/meta/test_engine_version_range_sync.py`, failing if the `pixi.toml` version-range declarations and in-code range constants diverge — **not yet present in the repo; cited here because the story spec names it, not because it exists today** |
| **3.2** | `mason package build` | Integration | Produces a wheel + sdist (PEP-517 `python -m build`) and a `.conda` (`pixi build`) with every artifact path reported; nothing is uploaded; `--target library` is the only accepted value in v1; a wheel/conda version mismatch aborts before any upload, showing both values; succeeds with zero CFE installation present |
| **3.3** | Ship-target vocabulary and dry-run default | Unit | `--ship` accepts exactly `pypi`, `conda-forge`, `channel:<name>` (comma-separated, each honoured independently); any other value rejected listing the valid set; without a confirming flag, the command plans and prints but uploads nothing |
| **3.4** | The `pypi` ship target | Integration | Wheel + sdist uploaded via the `twine` engine adapter; result is `ShipTargetResult(state=terminal)` with a URL reference; missing credentials detected **before** any build/upload; credentials read at point-of-use only, never stored on a rendered/logged object; succeeds with zero CFE installation present |
| **3.5** | The `channel:<name>` ship target | Integration | `.conda` artifact uploaded to the named channel via an engine adapter; result is `terminal` with a channel-path reference; a channel rejection becomes a typed error + `failed` result without affecting other targets; succeeds with zero CFE installation present |
| **3.6** | The `conda-forge` ship target | Integration | **Calls** Story 2.9's submission function rather than reimplementing it — `package.py` must contain no staged-recipes submission logic of its own; wraps the result as `ShipTargetResult(state=pending)`; an unresolvable CFE root or a recipe not at the expected path fails only this target while `pypi` in the same invocation completes normally; `mason doctor` reports whether both preconditions are met |
| **3.7** | Asymmetric receipts, partial failure, and idempotence | Unit + integration | Every ship target carries an explicit `state` (`not_attempted`/`failed`/`pending`/`terminal`) + `reference`; a mixed pypi-success/conda-forge-pending run reports both, never collapsing `pending` into success in either output format; aggregate exit code fails only if a target failed to *initiate*; one target failing doesn't stop the others; a retry skips an already-terminal target by **interrogating the target directly** (index/PR lookup), never a local state file — and Mason creates no state directory, receipt cache, or lock file anywhere |
| **3.8** | Mason ships Mason | Integration / self-hosting | `mason package --ship pypi` run against Mason's own `src/shared/packages/pyforge-mason/` publishes `pyforge-mason` with a `terminal` receipt + URL; `mason package build` output matches the repo's existing hand-run `pyforge-mason-build` triad. Satisfies SM-1, the primary success metric. |
| **3.9** | The `ship` verb and TestPyPI rehearsal | Integration | `mason package ship --to <targets>` is the canonical shipping command; the compatibility form `mason package --target library --ship ...` is the **only** bare-noun form that dispatches (asserted by a dedicated test); `ship` with no artifacts present builds first by calling Story 3.2's implementation, not a duplicate; `--to pypi-test` uploads to TestPyPI through the same code path as `pypi`, differing only in repository config; the FR-24 self-hosting sequence enforces `pypi-test` passes before `pypi` runs; a dry-run plan naming `pypi` states explicitly that the upload is irreversible |

---

## Epic 4 — Bind environments into lockfiles (4 stories, all pending)

None of Epic 4 is implemented — no `environment.py` or lock-engine adapter exists.

| Story | Title | Planned level(s) | What the test must prove once built |
|-------|-------|-------------------|----------------------------------------|
| **4.1** | Lock engine adapter and provenance | Unit | `engines/condalock.py` implements the Story 3.1 engine protocol; engine name + version appear in rendered output and (where the format allows) in the lockfile's own provenance; Mason itself contains no dependency-resolution logic |
| **4.2** | Manifest discovery | Unit | Discovery locates `pyproject.toml`, `environment.yml`, `requirements*.txt`, `pixi.toml`; discovered list is displayed before solving begins; explicit user-supplied manifest paths override discovery entirely; no manifests found → typed error naming the directory and filenames searched |
| **4.3** | `mason environment lock` | Integration | Solving delegated to the engine, lockfile written; `--output <path>` honored; `--platform` (one or more) scopes the lock to exactly those platforms; no `--platform` falls back to the engine's default, reported in output; succeeds with zero CFE installation present |
| **4.4** | `mason environment check` | Integration | Current lockfile → exit 0; a manifest changed since lock was produced → non-zero exit naming which manifests drifted; `--format json` conforms to the FR-31 envelope; a missing lockfile produces a typed error distinguishing "missing" from "stale" |

---

## Epic 5 — Prove the seam holds (5 stories, all pending)

The most meta-test-dense epic: three of its five stories exist specifically to
mechanize the AD-1 "wraps, never forks" guarantee. None are implemented yet.

| Story | Title | Planned level(s) | What the test must prove once built |
|-------|-------|-------------------|----------------------------------------|
| **5.1** | CFE-independence test | **Meta (this story delivers `tests/meta/test_cfe_independence.py`)** | Every `mason package` and `mason environment` verb runs normally with the CFE root guaranteed unresolvable; the one legitimate exception (the `conda-forge` ship target) appears in a **named allow-list of exactly one entry** — no blanket "except where CFE is needed" phrasing, since that's the exact erosion this test exists to stop; the excepted target is asserted to fail with the FR-5 error specifically, not merely "fail"; `pyforge.mason.package`/`environment` import cleanly with no CFE on the filesystem |
| **5.2** | Governance test | **Process/CI check, not a pytest file** | The effort's commit range contains no **implementation** commit touching `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`, or `.claude/tools/conda_forge_server.py`; the one sanctioned exception is the closing Story 5.5 retrospective commit, identified by a `retro:` subject + a CFE `CHANGELOG.md` entry, and the check asserts that exception is used **exactly once**; the existing repo-level `scripts/spec_surface_check.py` gate is green |
| **5.3** | Delegation-fidelity test | Integration, `slow`-marked | A representative recipe operation run through Mason and separately as a direct CFE invocation produces matching semantic content; carries the `slow` marker (excluded from the default test task, mirroring `pyforge-warden`); skips cleanly (not a failure) when no real CFE installation is present |
| **5.4** | Free-inheritance verification | Observation, not a repeatable test | Depends on an external event — a CFE MINOR version bump landing after Mason ships. When it happens, the affected Mason verb is re-run and the improvement is observed with **zero corresponding change to the Mason repository**; recorded as SM-4 satisfied, with the CFE version and date. May complete after v1 ships; not blocking. |
| **5.5** | Rule-2 conda-forge-expert retrospective | Not a test story — the mandatory CFE-skill closeout | Per this repo's CLAUDE.md Rule 2: reviews the whole effort against `conda-forge-expert`'s skill files, lands corrections/refinements/additions as skill-file edits plus a dated `CHANGELOG.md` entry, bumps the skill version per semver, and specifically triages the CFE upstream defects already recorded during planning (13 duplicated `_get_data_dir()` copies, `parents[3/4/5]` repo-root divergence, two scripts resolving to different data directories, unconditional JFrog header injection). Commits with a `retro:` subject so Story 5.2's governance check recognizes it as the sanctioned exception. |

---

## Test Coverage Summary

| Level | Real today | Planned once epics ship | Notes |
|-------|-----------|--------------------------|-------|
| **Meta** | 4 files, 119 tests total (meta+unit combined) — `test_dependency_direction.py`, `test_exit_code_ownership.py`, `test_namespace_is_implicit.py`, `test_render_ownership.py` | +6 files: `test_no_recipe_knowledge.py`, `test_adapter_sole_caller.py` (2.2), `test_engine_version_range_sync.py` (3.1), `test_cfe_independence.py` (5.1), plus 1.7's AD-6 lazy-import check and 5.2's governance check | Meta-tests are Mason's dominant enforcement mechanism — see § *Architecture Context* above |
| **Unit** | 4 files — `test_cli.py`, `test_errors.py`, `test_exit_codes.py`, `test_render.py` | Growth expected on `resolve.py` (1.5), interpreter/probe logic (1.6), `cfe.py` result shapes (2.1), engine protocol (3.1/4.1), manifest discovery (4.2) | No `tests/integration/` or `tests/e2e/` directory exists in the repo yet |
| **Integration** | **0** — directory doesn't exist | Nearly all of Epic 2 (2.4–2.10), Epic 3 (3.2–3.9), Epic 4 (4.3–4.4), and 1.8/5.3 | Blocked on Story 1.9 (fake CFE root fixture) for anything CFE-dependent |
| **E2E / self-hosting** | 0 | Story 3.8 (Mason ships Mason) is the closest analogue to an E2E test — real self-publish, not a fixture | No dedicated `tests/e2e/` convention decided yet; may not be warranted given Mason's CLI-only surface |

**4/38 stories done (11%); 34/38 pending.** No coverage percentage target is set for
IT/E2E because the harness those levels depend on (Story 1.9) has not shipped —
setting a numeric target now would itself be a fabrication.

---

## Framework & Tooling (real, verified this session)

- **Pytest**, invoked via the pixi task `pyforge-mason-test`
  (`pytest src/shared/packages/pyforge-mason/tests -q`, defined in root `pixi.toml`
  under `[feature.pyforge-mason.tasks]`), run through the dedicated `pyforge-mason`
  pixi environment (`no-default-feature = true`).
- **Directory convention**: `tests/meta/` (AST-based invariant guards) and
  `tests/unit/` (pure-function/class tests) exist today. `tests/integration/`,
  `tests/e2e/`, and `tests/fixtures/` do not exist yet — the last is Story 1.9's
  deliverable.
- **No `conftest.py` exists yet** — the four done stories needed no shared fixtures;
  one will likely appear once Story 1.9's fake-CFE-root fixture needs sharing across
  Epic 2 integration tests.
- **`slow` marker**: not yet registered (no `pyproject.toml` `[tool.pytest.ini_options]`
  block exists). Stories 1.9 and 5.3 both commit to adding it, mirroring the
  `pyforge-warden` convention (exclude slow/real-dependency tests from the default
  task).
- **AST-based scanning, not regex, for every meta-test.** This is an explicit,
  repeated design choice across all four real meta-test files — each docstring cites
  the same precedent: a naive text/regex scan false-positives on a comment or
  docstring that merely *mentions* a banned pattern (concretely hit once already, in
  an early draft of `test_namespace_is_implicit.py`'s `click`/`typer` check). Every
  future meta-test in this plan (2.2's deny-list, 5.1's independence check) should
  follow the same discipline.

---

## Readiness Checklist

- [x] All 38 stories defined in `epics.md`, mapped to FRs/ADs/NFRs
- [x] Real coverage for all 4 done stories verified against actual test files (not
      assumed from story titles)
- [x] Planned coverage level + scope stated for all 34 pending stories, with no
      invented file names
- [x] Fabricated placeholder content identified and fully replaced
- [ ] `tests/integration/` directory scaffolded (blocked on Story 1.9)
- [ ] `tests/fixtures/fake_cfe_root/` built (Story 1.9)
- [ ] `slow` marker registered in `pyproject.toml`
- [ ] `conftest.py` introduced once a shared fixture is needed
- [ ] Coverage percentage targets set for IT/E2E (deferred until the harness exists)
- [ ] CI workflow configured for `pyforge-mason-test`

---

**Status**: DRAFT — accurate as of Mason's real 11% (4/38) completion state.

**Coverage Target**: Not numerically fixed for IT/E2E pending Story 1.9's harness; Unit
≥80% expected per shipped module once Epics 2–5 land.

**Last updated**: 2026-08-02
