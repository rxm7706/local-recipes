---
title: 'Story 1.1: Package spine, verdict lattice, findings registry, and the meta-tests that enforce them'
type: 'feature'
created: '2026-07-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: 'd2ee6c50e1b00d6795c5394a554499a7ce6d3f1b'
final_revision: 'f49bea7b71fdfe48f501b006c1e0b06388d8bfb1'
context:
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `pyforge-marshal` does not exist yet. Every later Epic-1+ story depends on machinery this story alone establishes: the closed verdict lattice, the finding-code registry, the one response envelope, and the meta-tests that make AD-3/AD-4/AD-7/AD-39 build-breaking rather than memorized conventions.

**Approach:** Scaffold the package at `src/shared/packages/pyforge-marshal/` matching the architecture's Structural Seed (top-level dirs only — `cli/`, `core/`, `ports/`, `adapters/`, `supervisor/`, `schemas/`, `tests/{unit,contract,meta,integration}`), implement `core/model.py` (Verdict/Status/Severity/Finding/Envelope), `core/findings.py` (code registry), `core/verdict.py` (lattice + classify + exit projection), a minimal `--version`/`--help` CLI, wire `import-linter` into `pyproject.toml` + root `pixi.toml`, and write the meta-tests. Mirror `src/shared/packages/pyforge-doctor/` and `pyforge-warden/`'s existing Story-1.1 precedent (same repo, already merged) for package layout, dataclass coercion idiom, and AST-scan meta-test style — do not invent a new house style.

## Boundaries & Constraints

**Always:**
- Follow the sibling packaging convention exactly: `pyproject.toml` (hatchling backend) + member `pixi.toml` (`pixi-build-python` backend, no `[workspace]` table), `src/pyforge/marshal/` import root, console script `marshal`.
- `core/**` has zero imports of `subprocess`, `os`, `time`, or `pyforge.marshal.adapters` — enforced by an `import-linter` "forbidden" contract (AD-4).
- Only `adapters/harness_bmadloop.py` may reference `bmad_loop` (the harness's importable package name, confirmed via `recipes/bmad-loop/recipe.yaml`) — enforced by a second `import-linter` "forbidden" contract (AD-3). Both contracts live in one `[tool.importlinter]` block in `pyproject.toml`; provision `import-linter>=2.13` in the ROOT `pixi.toml`'s new `[feature.pyforge-marshal.dependencies]` (mirrors how `pytest` is provisioned there for every sibling — never in the package's own runtime deps).
- `core/verdict.py` is the only module that may embed a literal exit-code integer from `{0,1,2,3,4,130}` — enforced by an AST-scan meta-test mirroring `pyforge-warden/tests/meta/test_verdict_sole_ownership.py`'s exact technique (exit-call-alias detection, module-constant detection, lattice-order-literal detection), adapted to Marshal's 6-member lattice and exit set.
- `Envelope.__post_init__` (not a convention, a hard type-level check) raises `ValueError` if `status` doesn't match `status_for(verdict)`, or if `status` is `ok` while any finding has `severity == error` (AD-39's own named failure example).
- Declare `PyYAML>=6.0`, `tomlkit>=0.13,<0.13.3`, `psutil>=7.2.2`, `jsonschema>=4.25` as Marshal's own direct dependencies in both `pyproject.toml` and the package's own `pixi.toml` `[package.run-dependencies]` — never inherited transitively from `bmad-loop`.
- Root `pixi.toml`: add `[feature.pyforge-marshal.dependencies]` + 4 tasks (`-build-conda`, `-build-dist`, `-build`, `-test`) placed after the `pyforge-steward` block (before `[environments]`, matching the newest sibling convention), plus a `pyforge-marshal` entry in `[environments]` (`no-default-feature = true`).

**Block If:** None identified — every ambiguity below was resolved by grounding in AD text, PRD FR-19, or existing sibling precedent (see Design Notes), not by guessing.

**Never:**
- Do not stub the 8 port Protocols, the 7 remaining adapters, `supervisor/`'s real entry point, or any `core/` module besides `model.py`/`findings.py`/`verdict.py` (`policy.py`, `gate.py`, `supervise.py`, `journal.py`, `identity.py`, `status.py`, `conformance.py`, `egress.py` are later stories' explicit scope — inventing their shape now risks getting it wrong before a real consumer exists). `ports/__init__.py`, `adapters/__init__.py`, `supervisor/__init__.py` are docstring-only placeholders.
- Do not wire `--version`/`--help` through the envelope/finding machinery — they stay plain `argparse` (mirrors `pyforge-doctor/src/pyforge/doctor/__main__.py` exactly). No real command exists yet to justify a live envelope-emitting example; the mechanism is proven by direct unit/meta tests instead.
- Do not seed `core/findings.py`'s `REGISTERED_CODES` with invented codes that have no real caller — it starts an empty `frozenset()`, documented as populated additively by later stories. Prove the registry mechanism with `monkeypatch`, not fabricated production codes.
- Do not resolve or invoke the harness in `adapters/harness_bmadloop.py` — it stays a docstring-only seam declaration this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Construct `Finding` with unregistered code | `code="MRS-ZZZ-999"` not in `REGISTERED_CODES` | raises `UnregisteredFindingCodeError` (subclass of `ValueError`) | test asserts raise (AD-15) |
| Construct `Finding` with malformed code | `code="not-a-code"` | raises `UnregisteredFindingCodeError` before the membership check | test asserts raise |
| Construct `Envelope` with mismatched status/verdict | `verdict=Verdict.ERROR, status=Status.OK` | raises `ValueError` at construction | test asserts raise (AD-39) |
| Construct `Envelope`, status `ok`, a finding severity `error` present | `status=Status.OK`, `findings=(Finding(severity=ERROR,...),)` | raises `ValueError` | test asserts raise (AD-39's named example) |
| `verdict.classify(code)` on a registered-but-unclassified code | code passes `require_registered` but absent from `_CLASSIFY_TABLE` | raises `ValueError` naming the gap | test asserts raise (totality) |
| `verdict.compute_verdict([])` | no findings | returns the `floor` (`Verdict.CLEAN` default) | none — defined behavior |
| `marshal --version` / `marshal --help` | CLI invocation | exits 0, prints version/help via argparse's own path | argparse handles it; `main()` relays `exc.code`, never a new literal |
| A non-`verdict.py` module contains `sys.exit(2)` | synthetic violation string parsed by the AST scanner | scanner reports the violation | proves the meta-test guard is alive, not vacuous |
| `lint-imports` run against the built package | current tree (compliant) | exits 0 | meta-test asserts subprocess returncode 0 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/` -- READ-ONLY reference for dataclass coercion idiom, package layout, `__main__.py` exit-relay pattern (already merged, do not modify)
- `src/shared/packages/pyforge-warden/tests/meta/test_verdict_sole_ownership.py` -- READ-ONLY reference for the lattice-order + exit-literal AST-scan technique (already merged, do not modify)
- `recipes/bmad-loop/recipe.yaml` -- confirms the harness's importable name is `bmad_loop` (entry point `bmad-loop = bmad_loop.cli:main`)
- `src/shared/packages/pyforge-marshal/` -- NEW package root (this story creates everything under it)
- `pixi.toml` (repo root) -- add `[feature.pyforge-marshal.*]` + `[environments]` entry, mirroring the `pyforge-steward` block immediately above `[environments]`

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-marshal/pyproject.toml` -- hatchling backend, deps (PyYAML/tomlkit/psutil/jsonschema), `[project.scripts] marshal = "pyforge.marshal.cli.main:main"`, `[tool.importlinter]` with the two AD-3/AD-4 contracts -- the dependency + seam declarations
- [x] `src/shared/packages/pyforge-marshal/pixi.toml` -- member manifest, `pixi-build-python` backend, same 4 deps as run-dependencies -- conda build wiring
- [x] `src/shared/packages/pyforge-marshal/README.md`, `.gitignore` -- mirror `pyforge-doctor`'s exactly (build-artifact ignores)
- [x] `src/pyforge/marshal/__init__.py` -- empty, matches sibling convention
- [x] `src/pyforge/marshal/core/model.py` -- `Verdict`, `Status`, `Severity` enums; `status_for()`; `Finding`, `Envelope` frozen dataclasses; `build_envelope()` -- the shared value types + envelope contract (AD-14, AD-39)
- [x] `src/pyforge/marshal/core/findings.py` -- `CODE_PATTERN`, `REGISTERED_CODES` (empty), `UnregisteredFindingCodeError`, `require_registered()` -- the central code registry (AD-15)
- [x] `src/pyforge/marshal/core/verdict.py` -- `LATTICE_ORDER`, `_RANK`, `_EXIT_BY_VERDICT`, `_CLASSIFY_TABLE` (empty), `classify()`, `compute_verdict()`, `exit_code_for()`, `EXIT_SIGINT` -- sole lattice + exit-code owner (AD-7, AD-31)
- [x] `src/pyforge/marshal/cli/__init__.py`, `src/pyforge/marshal/cli/main.py` -- argparse tree, `--version`/`--help` only, `main(argv) -> int` never itself embedding an exit literal -- the entry point AC
- [x] `src/pyforge/marshal/ports/__init__.py`, `src/pyforge/marshal/supervisor/__init__.py` -- docstring-only placeholders reserving the location
- [x] `src/pyforge/marshal/adapters/__init__.py`, `src/pyforge/marshal/adapters/harness_bmadloop.py` -- docstring-only seam declaration (AD-3)
- [x] `src/pyforge/marshal/schemas/envelope.v1.json` -- JSON Schema for the 8-key envelope + finding sub-schema
- [x] `tests/unit/test_model.py` -- Envelope/Finding construction, coercion, the two AD-39 raise scenarios, jsonschema validation of `to_json_dict()` against `schemas/envelope.v1.json`
- [x] `tests/unit/test_findings.py` -- format + membership checks via `monkeypatch`-registered synthetic codes
- [x] `tests/unit/test_verdict.py` -- `classify`/`compute_verdict`/`exit_code_for` behavior via monkeypatched registry+classify-table entries; empty-findings floor behavior
- [x] `tests/unit/test_cli.py` -- `main(["--version"])` and `main(["--help"])` both return `0`
- [x] `tests/meta/test_ad3_ad4_import_linter.py` -- invokes `lint-imports` via subprocess against the package's `pyproject.toml`; asserts returncode 0; asserts the two contracts are present with the expected `source_modules`/`forbidden_modules`
- [x] `tests/meta/test_ad7_verdict_sole_ownership.py` -- AST-scan every installed module except `verdict.py` for guarded exit literals / lattice-order literals / private-verdict-name references; positive proof the detectors fire on synthetic strings
- [x] `tests/meta/test_ad39_envelope_consistency.py` -- constructs a valid Envelope per lattice member and asserts `status_for` partitioning; asserts both invalid-construction scenarios from the I/O matrix raise
- [x] `tests/contract/README.md`, `tests/integration/README.md` -- one-line placeholders (nothing to test until ports/adapters have real implementations)
- [x] root `pixi.toml` -- `[feature.pyforge-marshal.dependencies]` (`pyforge-marshal` path dep, `hatchling>=1.31.0`, `python-build>=1.5.0`, `pytest>=9.1.1`, `import-linter>=2.13`) + 4 tasks + `[environments]` entry, placed like the `pyforge-steward` block

**Acceptance Criteria:**
- Given a clean pixi env, when `pixi run -e pyforge-marshal pyforge-marshal-test` runs, then all unit + meta tests pass, including the two import-linter contracts and the AD-7/AD-39 synthetic-violation proofs
- Given the installed package, when `python -c "import pyforge.marshal"` runs, then it succeeds with no error
- Given the built console script, when `marshal --version` and `marshal --help` run, then both exit `0`
- Given `core/verdict.py` alone, when every other installed module is AST-scanned, then none embeds an exit-code literal from `{0,1,2,3,4,130}` and none references a private `verdict` name
- Given an `Envelope` constructed with `verdict=X`, when inspected, then `status == status_for(X)` always holds and cannot be constructed otherwise
- Given `pixi run -e pyforge-marshal pyforge-marshal-build`, when it runs, then both the conda package and the wheel/sdist build successfully

## Spec Change Log

## Review Triage Log

### 2026-07-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 0, medium 7, low 6)
- defer: 1 (high 0, medium 1, low 0)
- reject: 9 (high 0, medium 0, low 9)
- addressed_findings:
  - `[medium]` `[patch]` `core/findings.py` `CODE_PATTERN` was matched with `.match()` against a `^...$`-anchored pattern, which wrongly accepts a code with a trailing newline (classic Python `re` pitfall, already avoided by `pyforge-warden`'s own sibling module). Switched to unanchored pattern + `.fullmatch()`; added regression tests.
  - `[medium]` `[patch]` `Envelope.__post_init__` didn't validate `data` is a `dict`, `schema_version == SCHEMA_VERSION`, or `data_version >= 1` before use — a caller could construct an envelope whose own `to_json_dict()` fails its packaged JSON schema. Added all three checks + tests.
  - `[medium]` `[patch]` `Envelope.data`'s defensive copy was shallow (`dict(self.data)`), so a nested list/dict inside `data` remained mutable by the original caller after construction; `to_json_dict()` also returned a live reference to the stored dict. Switched to `copy.deepcopy` in both places; added tests for both leaks.
  - `[medium]` `[patch]` `schemas/envelope.v1.json` had no `additionalProperties: false` at the envelope or finding level, so a typo'd/extra key would silently validate. Added it to both, updated the schema description, added tests proving a typo'd key at each level now fails validation.
  - `[low]` `[patch]` `verdict.compute_verdict`'s `floor` parameter wasn't coerced via `Verdict(floor)` (unlike `exit_code_for`, which does coerce), so an invalid/raw-string floor on empty findings passed through unvalidated. Fixed + added tests.
  - `[low]` `[patch]` The import-linter meta-test asserted the exact substring `"2 kept, 0 broken"` against `lint-imports`' stdout — brittle against a future output-format change unrelated to the contracts themselves. Relaxed to a `0 broken` regex; the contract count is separately enforced by a config-based test.
  - `[low]` `[patch]` `cli/main.py`'s hand-synced `__version__` literal had no test tying it to `pyproject.toml`'s version. Added a sync test.
  - `[low]` `[patch]` `core/findings.py`'s `CODE_PATTERN` and `schemas/envelope.v1.json`'s `finding.code` pattern are independent copies with nothing keeping them in sync. Added a tripwire test comparing both patterns' behavior across several probe strings.
  - `[low]` `[patch]` The `tomlkit>=0.13,<0.13.3` ceiling in `pyproject.toml`/`pixi.toml` had no comment explaining the specific upper bound. Added a one-line comment pointing at the root `pixi.toml`'s own identical cap (for `dagster-dg-core`) and the architecture Stack table's rationale.
  - `[low]` `[patch]` `cli/main.py`'s module docstring overclaimed "`core/verdict.py` is the sole module permitted to call an exit primitive," which its own `raise SystemExit(main())` line technically contradicts (the meta-test only flags a *literal* guarded exit-code constant, not any call to an exit primitive). Tightened the wording to describe what the meta-test actually enforces.
  - `defer`: the `pyforge-mason`/`pyforge-steward`/`pyforge-warden` `*-build-conda` tasks use a `pixi build --manifest-path` flag the installed pixi (0.73.0) doesn't have (confirmed live) — pre-existing, outside this story's surface. Logged to `deferred-work.md`.
  - `reject` (9, noise or already-addressed): declaring PyYAML/tomlkit/psutil/jsonschema as dependencies with no current caller (explicitly mandated by the epics.md AC, not speculative); the AD-3 import-linter contract's `adapters`-package exclusion (already documented in three places — spec Design Notes, `pyproject.toml` comment, and a dedicated meta-test assertion); the AST-scan meta-test's size/complexity ("the meta-tests that enforce them" is this story's own named deliverable); `require_registered` raising a raw `TypeError` on non-`str` input; `main()` on non-`str` `argv` elements; the exit-literal detector's bool-literal exclusion; an undetected bare `raise SystemExit`; `sys`/`os` aliased via plain assignment rather than `import`; `Verdict` imported under an alias when spelling the lattice order — the last five are narrow, contrived adversarial patterns absent from any code this story actually ships, consistent with the AST scanner's own documented best-effort bounds and the unmodified sibling precedent it mirrors.

### 2026-07-26 — Review pass (follow-up, fresh pass on the done spec)
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 0, medium 6, low 7)
- defer: 2 (high 0, medium 1, low 1)
- reject: 8 (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` The package `.gitignore` (a byte-for-byte doctor mirror) put comments inline after `/dist/`/`/dist-conda/`; gitignore has no trailing-comment syntax, so both patterns matched nothing (reproduced with probe files — the root `.gitignore`'s `!src/**/packages/*/**` re-include makes the local file load-bearing). Comments moved to their own lines; verified probes now ignored. The identical doctor/warden sibling defect → deferred-work.md.
  - `[medium]` `[patch]` The new `pyforge-marshal-build-conda`/`-build-dist` tasks emit `dist-conda/`/`dist/` at the REPO root (pixi tasks run with cwd = workspace root), and root `.gitignore` had no `dist-conda` entry — a built `.conda` sat one `git add -A` from being committed. Added `dist-conda/` to root `.gitignore`; verified live (ran the build, `git status` clean).
  - `[medium]` `[patch]` `cli/main.py` embedded `return 0`, `return 2`, and the inline `{0,1,2,3,4,130}` set while its docstring claimed it "never embeds a literal guarded exit-code integer" — contradicting the spec's Always constraint (only `core/verdict.py` may embed those literals) and leaving the frozen domain spelled in four unlinked copies. verdict.py now exports `EXIT_OK`/`EXIT_USAGE`/`GUARDED_EXIT_CODES` (computed, never re-spelled); main.py imports them; docstring now truthful; new unit test pins the domain. (Doctor's file shares the original pattern — recorded as a deliberate stricter divergence in Design Notes.)
  - `[medium]` `[patch]` `Envelope.__post_init__` never validated member types: a non-`Finding` element constructed fine on the error-status path (crashing only later in `to_json_dict()`) but crashed with a raw `AttributeError` on the ok path — validation strictness depended on the verdict. Also unchecked: `command` non-str, `assumptions` element types, `Finding.message`/`path` types, and `schema_version=True` (bool passes `== 1`). All now raise `ValueError` at construction; 7 new tests.
  - `[medium]` `[patch]` `CODE_PATTERN` used `\d` (Unicode-wide in Python: `MRS-GATE-١٢٣` fullmatched) while the packaged JSON schema's ECMA `\d` means `[0-9]` — and the drift-tripwire test compares both patterns via Python `re`, so it was structurally blind to this divergence class. Both patterns now spell `[0-9]`; Unicode-digit probes added to the format tests and the tripwire.
  - `[medium]` `[patch]` `schemas/envelope.v1.json` accepted documents the producer can never construct: `schema_version: 2` validated against the v1 schema (`minimum: 1`, now `const: 1`), and a mismatched status/verdict pair (`ok`+`error`) passed — AD-39 existed only producer-side. Added a top-level `oneOf` encoding the `status_for` partition; 2 new schema tests.
  - `[low]` `[patch]` The AD-3 contract is enumerative — a future new subpackage would silently sit outside the `bmad_loop` prohibition with all gates green. Added a complement meta-test deriving the subpackage set from the installed package and asserting `source_modules` == everything except `adapters`.
  - `[low]` `[patch]` The `lint-imports` meta-test died with a raw `FileNotFoundError` traceback when run outside the provisioning env (reproduced). Now `pytest.fail`s with the exact `pixi run -e pyforge-marshal` remedy; `timeout=120` added to the subprocess call.
  - `[low]` `[patch]` The sole-ownership scan exempted ANY file named `verdict.py` (basename filter) — a future `adapters/verdict.py` would inherit the exemption. Now full-path comparison against `core/verdict.py` only.
  - `[low]` `[patch]` `_contract_forbidding` would `KeyError` on a future contract type without a `forbidden_modules` key (e.g. `layers`), masking the real assertion. Switched to `.get(..., [])`.
  - `[low]` `[patch]` Dead `tomli` fallback branches in two test files (unreachable under `requires-python >=3.12`, and `tomli` is declared nowhere — it would `ImportError` if ever taken). Replaced with plain `import tomllib`.
  - `[low]` `[patch]` The three AST-scan parametrizations used `ids=lambda p: p.name`, yielding six indistinguishable `__init__.py` ids — a violation report couldn't say which package fired. Now package-relative paths.
  - `[low]` `[patch]` README claimed the env "carries only the built package … a test runner, and import-linter", omitting `hatchling`/`python-build` (provisioned in the same feature block). Wording corrected.
  - `defer` (medium): doctor's and warden's package `.gitignore` share the broken inline-comment `/dist/`/`/dist-conda/` patterns (steward/mason are fine) — pre-existing in merged siblings, outside this story's surface. Ledger entry appended.
  - `defer` (low): all five pyforge sibling packages declare MIT in `pyproject.toml` but ship no LICENSE file — repo-wide convention gap needing a one-sweep fix; fixing marshal alone would diverge from the mirror mandate. Ledger entry appended.
  - `reject` (8, noise or spec-mandated): AD-4 forbidden-modules breadth (datetime/pathlib/io/socket not forbidden — the spec's Always bullet pins exactly `subprocess`/`os`/`time`/`adapters`; broadening is an architecture-level decision); unused runtime deps (explicitly mandated by the epics AC — prior-pass reject repeated); `require_registered` raising `TypeError` on non-str (prior-pass reject repeated); cross-StrEnum coercion (`Verdict(Severity.ERROR)` — contrived, the coercion idiom is sibling house style); private-name detector false-positives on `X.verdict._attr` (conservative-side, documented best-effort bounds, no shipped code trips); `Verdict`-alias/qualified-attribute lattice-order evasion (prior-pass reject class — contrived patterns within documented bounds); bare `sys.exit()` implicit-0 undetected (documented, test-asserted non-firing bound); bare `marshal` exiting 0 silently (mirrors doctor exactly per the spec's Never bullet; will naturally become a usage error when real subcommands land).

### 2026-07-26 — Review pass (third pass, fresh review on the done spec)
- intent_gap: 0
- bad_spec: 0
- patch: 17 (high 0, medium 5, low 12)
- defer: 1 (high 0, medium 1, low 0)
- reject: 14 (high 0, medium 0, low 14)
- addressed_findings:
  - `[medium]` `[patch]` The packaged schema's `finding.code` pattern was validated by python-jsonschema via `re.search`, where a bare `$` matches before a trailing newline — so `"MRS-GATE-001\n"` validated on the wire while the producer's `fullmatch` rejects it, and the drift-tripwire test compared both patterns via `fullmatch`, making it structurally blind to exactly this divergence. Pattern now ends `$(?!\n)` (inert under ECMA-262), the tripwire models the schema side with `re.search`, and a real-jsonschema-engine newline probe was added.
  - `[medium]` `[patch]` `Envelope(assumptions="assumed x")` silently became nine one-char assumptions — `tuple()` iterates a bare str and each char passes the str member check. Bare-str `assumptions` now raise `ValueError` at construction.
  - `[medium]` `[patch]` `schema_version` was checked with bool-exclusion + equality only, so `1.0` (== 1) constructed and emitted `"schema_version": 1.0` on the wire — while `data_version` one field over got the full bool+int treatment. Now requires a real int.
  - `[medium]` `[patch]` The `Envelope` docstring promised "a successfully constructed envelope always serializes to schema-valid JSON," but `data` contents were never checked: a set inside `data` constructed fine and blew up later in `json.dumps`, and a non-deepcopyable value (generator/open file) crashed construction with a raw `TypeError`. `__post_init__` now deep-copies under a `ValueError` wrap and requires `json.dumps(data)` to succeed — the docstring claim is now enforced, not aspirational.
  - `[medium]` `[patch]` `pyforge-marshal-build-dist` lacked `--no-isolation`, so `python -m build` created an isolated venv and pip-fetched hatchling from PyPI — dead weight for the provisioned hatchling and a hard failure air-gapped (warden/doctor pass the flag; the story mirrored steward/mason, which dropped it). Fixed and verified live (wheel + sdist built in-env). The steward/mason sibling defect → deferred-work.md.
  - `[low]` `[patch]` The AD-7 exit-primitive detector matched attribute calls only for `sys.exit`/`os._exit`/`*.SystemExit`, so argparse's public `parser.exit(3)` — available to the very CLI module the guard most needs to watch — sailed past undetected and undocumented. The attribute branch now treats ANY `.exit`/`._exit`/`.SystemExit` call as an exit primitive (stricter than the warden guard it mirrors; recorded in Design Notes), with a `parser.exit` probe and a `parser.error` non-firing probe.
  - `[low]` `[patch]` The AD-3 complement meta-test derived its universe from `__init__.py`-bearing directories only — a PEP 420 namespace subpackage or a future top-level `util.py` module would sit outside the `bmad_loop` prohibition with every gate green (the exact failure class the test's docstring names). Universe now = any `*.py`-bearing directory + top-level modules; a new companion test pins the root `__init__.py` import-free (the one file no source_modules entry can ever cover).
  - `[low]` `[patch]` `0.1.0` was spelled in three places with a tripwire covering two: package `pixi.toml`'s `[package] version` could drift silently. New `tests/meta/test_manifest_sync.py` pins pixi version AND `[package.run-dependencies]` against `pyproject.toml`'s `[project]` equivalents (the dual dependency manifests previously had no drift guard at all).
  - `[low]` `[patch]` The schema's `schema_version` description claimed "additive fields do not bump it" while `additionalProperties: false` makes any additive key wholesale-reject against a cached v1 schema — self-contradictory policy text. Reworded: any key-set change is a new schema version.
  - `[low]` `[patch]` The README's `lint-imports` command (unlike the meta-test's invocation) omitted `--no-cache`, littering an un-gitignored `.import_linter_cache/` at the repo root. `--no-cache` added to the README + spec Verification command; `.import_linter_cache/` added to the root `.gitignore` as belt-and-braces.
  - `[low]` `[patch]` `compute_verdict` duck-typed its findings (a raw string produced `AttributeError`) while `Envelope.__post_init__` in the same layer rejects non-`Finding` members with a dedicated regression test — now the same fail-loud `ValueError` + test.
  - `[low]` `[patch]` `main()`'s try block opened after `_build_parser()`, so a `KeyboardInterrupt` during parser construction violated the returns-int-never-raises contract; and `SystemExit(True)` relayed a bool (bool passes `isinstance(int)`). Parser construction moved inside the try; bool exclusion added to the relay; both tested.
  - `[low]` `[patch]` `build_envelope` exposed a `schema_version` parameter whose every non-default value is a guaranteed `ValueError` — API noise inviting the one mistake it cannot survive. Dropped; the constructor pins `SCHEMA_VERSION`.
  - `[low]` `[patch]` Empty-string `command` was wire-valid and constructible — a nameless envelope. Producer now requires non-empty; schema gains `minLength: 1`; both tested.
  - `[low]` `[patch]` No invalid-input tests existed for `exit_code_for`/`status_for` despite both advertising coercion; `GUARDED_EXIT_LITERALS` in the AD-7 test lacked the independent-copy rationale its sibling in `test_verdict.py` states. Tests + comment added.
  - `[low]` `[patch]` The package ships full type annotations but no `py.typed` marker, silently discarding them for downstream type checkers — warden (the explicit exemplar) ships one. Added; verified present in the built wheel.
  - `[low]` `[patch]` `test_findings.py` defined an inner function and immediately called it once — pointless indirection inlined.
  - `defer` (medium): `pyforge-steward`/`pyforge-mason`'s `*-build-dist` tasks share the missing `--no-isolation` defect (warden/doctor have the flag) — pre-existing in merged sibling blocks, outside this story's surface. New ledger entry appended.
  - `reject` (14, prior-pass rejects repeated or contrived/out-of-bounds): unused runtime deps (spec-mandated, third repeat); AD-4 forbidden-set breadth (spec pins exactly `subprocess`/`os`/`time`/`adapters`, second repeat); `require_registered` `TypeError` on non-str (third repeat); bare `marshal` exiting 0 (second repeat — mirrors doctor per Never bullet); lattice-order-via-aliased-`Verdict` and private-name false-positive detector bounds (second repeats, documented best-effort); `sys.exit(None)`/`sys.exit(2.0)`/bare-`SystemExit` escapes (documented, test-asserted non-firing bounds); envelope not tying `verdict` to `classify()` (enforcing it in `model.py` requires the exact import cycle the Design Notes' layering decision exists to avoid; `compute_verdict` is the projection path); meta-guards scanning the installed package (the whole suite runs against the same installed copy — coherent, sibling-mandated); non-iterable `findings`/`assumptions` raising `TypeError` from `tuple()` (fails loudly at construction; exception-type cosmetics); `Envelope` unhashable via its `dict` field (inherent to a dict payload, loud, no consumer hashes envelopes); package `.gitignore` comments "wrong location" (entries legitimately cover manual in-package builds); steward/mason `--manifest-path` breakage (already ledgered by pass 1 — appending again would duplicate an entry the orchestrator owns); cross-StrEnum coercion `Verdict`↔`Severity` (second repeat, house coercion idiom).

## Design Notes

**Why `core/model.py` owns `Verdict`/`Status` (not `core/verdict.py`).** `core/verdict.py` needs `Verdict`/`Finding` types — importing them from `model.py` is the one allowed edge. If `model.py` in turn needed to call into `verdict.py` to derive `status`, that would cycle. Resolution: `status_for(verdict) -> Status` is a pure 2-way partition ({clean, warn} -> ok, else -> error) that only needs the `Verdict` enum itself, so it lives in `model.py` alongside the enum. `core/verdict.py` owns the *lattice ordering*, `classify()`, and the *exit-code* projection — genuinely distinct concerns from the *status* projection.

**Exit-code assignment (recorded assumption, not architecture-dictated).** Architecture pins only `clean -> 0` and PRD FR-19 requires "a distinct code for could not evaluate." Neither source gives the other 3 numbers. Chosen, monotonic with lattice strength: `warn=0` (AD-31's own reasoning for why `warn` is a distinct rung from `unevaluable` — a read-only surface classifies a condition `warn` specifically so it does *not* block — only holds if `warn` exits 0, matching both `pyforge-warden` and `pyforge-doctor`'s existing exit-0 treatment of `warn`), `unevaluable=1`, `scope-violation=2`, `gate-failed=3`, `error=4`, `EXIT_SIGINT=130`. If a later story's AC contradicts this, amend `_EXIT_BY_VERDICT` in one place.

**Why `REGISTERED_CODES`/`_CLASSIFY_TABLE` start empty.** No command in this story emits a real finding (`--version`/`--help` bypass the envelope entirely, mirroring `pyforge-doctor`). Inventing placeholder codes with no caller would violate Simplicity First. The registry mechanism (format check, membership check, `Finding.__post_init__` calling `require_registered`) is fully real and tested via `monkeypatch`-injected synthetic codes — the same non-vacuous-proof style already used by every sibling meta-test in this repo.

**Import-linter contract scope gap (acknowledged, not this story's problem).** The AD-3 contract's `source_modules` list (`cli`, `core`, `ports`, `supervisor`) deliberately does NOT include `pyforge.marshal.adapters` as a whole package — doing so would also forbid `harness_bmadloop.py` itself. Consequence: a *future* adapter module (e.g. `vcs_git.py`) that wrongly imports `bmad_loop` won't be caught by this contract until whichever story adds that module also adds it to `source_modules`. Documented in the contract's own comment; not a gap this story can close since those modules don't exist yet.

**Golden reference precedent (same repo, already merged).** `pyforge-doctor`'s `models.py`/`verdict.py`/`__main__.py` and `pyforge-warden`'s `tests/meta/test_verdict_sole_ownership.py` are the load-bearing style references — frozen-dataclass `__post_init__` coercion, `EXIT_SIGINT` as a named constant never passed as a literal to an exit primitive, and the AST-scan meta-test technique (exit-alias detection, module-int-constant detection, lattice-order-literal detection). Do not diverge from this house style without a reason recorded here.

**Recorded divergences from the doctor mirror (follow-up review pass, 2026-07-26).** Two deliberate, stricter-than-sibling deviations: (1) `cli/main.py` no longer embeds `return 0`/`return 2`/the inline `{0,1,2,3,4,130}` set the doctor file carries — this spec's own Always constraint says only `core/verdict.py` may embed a guarded exit-code literal, so verdict.py now exports `EXIT_OK`/`EXIT_USAGE`/`GUARDED_EXIT_CODES` (computed from `_EXIT_BY_VERDICT` + the boundary constants, never re-spelled) and main.py imports them; the doctor exit-relay PATTERN (return an int, never raise, relay argparse's code, clamp anything foreign) is preserved unchanged. (2) the package `.gitignore` moves the `# pypi:`/`# conda:` comments to their own lines — doctor's inline-comment variant is byte-mirrored but broken (gitignore has no trailing-comment syntax, so doctor's `/dist/`/`/dist-conda/` patterns match nothing); the sibling defect is logged in `deferred-work.md`.

**Recorded divergences from the warden meta-test mirror (third review pass, 2026-07-26).** The AD-7 exit-primitive detector is one step stricter than `pyforge-warden`'s guard it mirrors: the AST attribute branch now treats ANY `.exit`/`._exit`/`.SystemExit` call as an exit primitive (warden's tracks only `sys`/`os` module bindings). Reason: argparse's public `parser.exit(N)` is an exit primitive directly available to `cli/main.py` — the module this guard most needs to watch — and it sailed past the binding-tracking variant undetected and undocumented. Conservative-by-design: a future in-package method legitimately named `exit` taking a guarded literal should stop for a human here anyway. Also stricter than the mirror: `build_envelope` takes no `schema_version` parameter (its only legal value is `SCHEMA_VERSION`), `Envelope` construction requires `data` to be deep-copyable AND `json.dumps`-serializable, and the package ships `py.typed` (warden does; doctor doesn't).

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: all tests pass (unit + meta)
- `pixi run -e pyforge-marshal pyforge-marshal-build` -- expected: conda package + wheel/sdist both build
- `pixi run -e pyforge-marshal marshal --version` -- expected: prints version, exits 0
- `pixi run -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- expected: `Contracts: 2 kept, 0 broken.` (`--no-cache`: don't write `.import_linter_cache/` into the repo root)

**Third-pass verification record (2026-07-26):** this run worktree's path length trips the known pixi-build-python panic (`end byte index ... out of bounds`, blaming the unrelated `pyforge-atlas` env — see auto-memory `bmad_loop_worktree_path_length_limit`), so gates ran in a short-path worktree (`.bmad-loop/rv11`, since removed) at the review commit: `pyforge-marshal-test` **155 passed** (including the live `lint-imports` meta-test), `pyforge-marshal-build` produced `dist-conda/pyforge-marshal-0.1.0-pyh4616a5c_0.conda` + wheel + sdist with `--no-isolation` against the in-env hatchling, `marshal --version` printed `marshal 0.1.0` and exited 0, and `git status` stayed clean of build litter (only `pixi.lock` re-solved; deliberately not committed — the short-worktree solve embeds its own absolute local-channel path). The fabricated empty `build_artifacts/linux64/{noarch,linux-64}/repodata.json` channel was needed for the fresh worktree's env solve (that gitignored local channel only exists in long-lived checkouts).

## Auto Run Result

**Pass 3 (2026-07-26, fresh review on the done spec — invoked by the orchestrator):**

- **Summary:** third adversarial + edge-case review of the full Story 1.1 diff (baseline `d2ee6c50e1`..`1eeac554cb`); 37 raw findings from the two reviewers deduplicated and triaged to 17 patches (5 medium, 12 low), 1 new defer, 14 rejects; all patches applied and verified; committed as `f49bea7b71`.
- **Files changed this pass:** `core/model.py` (schema_version real-int check, non-empty command, bare-str assumptions rejection, deep-copy + JSON-serializability enforcement, `build_envelope` param drop), `core/verdict.py` (compute_verdict member strictness), `cli/main.py` (KeyboardInterrupt window closed, bool SystemExit clamp), `schemas/envelope.v1.json` (`$(?!\n)` code-pattern tail, command minLength, versioning-policy text), `tests/meta/test_ad7_verdict_sole_ownership.py` (any-`.exit` attribute detection incl. `parser.exit`), `tests/meta/test_ad3_ad4_import_linter.py` (PEP 420 + top-level-module complement coverage, root-`__init__` import guard), NEW `tests/meta/test_manifest_sync.py` (pixi↔pyproject version + dependency tripwires), NEW `src/pyforge/marshal/py.typed`, unit tests (16 new tests; suite 139→155), root `pixi.toml` (build-dist `--no-isolation`), root `.gitignore` (`.import_linter_cache/`), package `README.md` (`--no-cache`).
- **Findings breakdown:** patch 17 applied (all listed in the triage log), defer 1 (steward/mason `--no-isolation` — new ledger entry appended; existing entries untouched per the orchestrator's instruction), reject 14 (mostly prior-pass reject repeats and contrived detector-evasion classes within documented bounds).
- **Verification:** full gate suite in a short-path worktree at the review commit — 155/155 tests incl. live import-linter, conda + wheel + sdist builds, CLI smoke, litter check (details above).
- **Follow-up review recommendation: true.** 17 patched findings with 5 medium and API-visible behavior changes (the envelope now rejects inputs it previously accepted; the wire schema pattern changed; the AD-7 detector broadened) is significant by both volume and contract impact — same standard the second pass applied at comparable volume. Severity is trending down across passes (no high ever; medium 7→6→5), so convergence is plausible next pass.
- **Residual risks:** `pixi.lock` still lacks a `pyforge-marshal` environment entry (deliberate — a solve from a canonical checkout should add it, not one from a temp worktree that bakes its absolute path into the local-channel URL); the AD-7 scanner's documented best-effort bounds (helper indirection, arithmetic, getattr) remain, per design; the schema's `$(?!\n)` tail is inert under ECMA-262 but has not been exercised against a non-Python validator.

