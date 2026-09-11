---
id: SPEC-pyforge-mason
status: shipped
updated: "2026-09-11"
owner-dream: docs/dreams/pyforge-mason.md
covers-dreams:
  - docs/dreams/presenton-pixi-image.md   # folded in 2026-08-02 as CAP-8..CAP-13 (see § Satellite below); satisfies INV-1 for this Dream
surface:
  - src/shared/packages/pyforge-mason/**    # the CLI this Spec builds — as-built and shipped (fleet ledger: complete 2026-08-21)
companions:
  - glossary.md                                                                      # spec-authored: the vocabulary the chain requires verbatim
  - ../../prds/prd-pyforge-mason-2026-07-25/prd.md                                   # adopted (chain): FR-1..FR-50 / NFR-1..NFR-16 / D-1..D-13
  - ../../architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md   # adopted (chain): the ADs (AD-1..AD-16 + AD-25/AD-26; Presenton AD-17..AD-24), structural seed, stack, diagrams
  - ../../epics.md                                                                   # adopted (chain): 11 epics / 50 stories as-built (was 5/38 at authoring; see § Currency reconciliation)
  - ../spec-packaging-factory/SPEC.md # adopted: the Spec governing the CFE surface Mason wraps — authoritative over Mason (Rule 1)
sources:
  - ../../../../../../docs/dreams/packaging-factory.md
  - ../../briefs/brief-pyforge-mason-2026-07-25/brief.md
  - ../../briefs/brief-pyforge-mason-2026-07-25/addendum.md
  - ../../prds/prd-pyforge-mason-2026-07-25/review-adversarial.md   # absorbed: findings applied in PRD revision 2 (FR-47..FR-50, D-10..D-13)
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# mason CLI — the packaging factory, made portable

## Why

A pain to solve, and an asset to free. The repository's packaging capability is real, proven, and **trapped**: a nine-step recipe lifecycle across 769 maintained feedstocks, carrying 106 accumulated gotchas and 10 hard constraints, exposed through 46 MCP tools and backed by 1,186 tests — reachable only inside a Claude Code session, in one repository, through pixi tasks defined in one manifest, with `recipes/` hardcoded in seventeen scripts. You cannot install it. You cannot run it in CI. A colleague cannot use it. The asset is real; the distribution is zero. And the half it never had is the half nobody else has either: for the maintainer shipping a library, the wheel takes ninety seconds and then the conda half means switching toolchains entirely — a different metadata format, a different dependency namespace, a different build system, a platform matrix, and a volunteer review queue. The domain survey is unambiguous that **no single tool spans both ecosystems**: Hatch and maturin are structurally conda-unaware, `pixi publish` targets conda channels with documentation silent on PyPI, and conda-smithy and the autotick-bot state in their own documentation that they cannot be deployed outside conda-forge's infrastructure. That is not a missing feature in one product — it is an unowned seam between two toolchains with different governance. `mason` is the installable face of the trapped capability plus that missing half: three verb families, where the middle one is the differentiator and the outer two make the product usable by people who never touch a recipe. The deeper aim is smaller and more stubborn: **packaging a library should be a sentence, not an afternoon of YAML archaeology** — executable outside the room it was invented in.

## Capabilities

- **CAP-1 — the CFE seam**
  - **intent:** A single module is the entire boundary between Mason and the packaging machinery it wraps, so the wrap decision is enforceable rather than aspirational.
  - **success:** A static check finds no wrapped-script path or filename anywhere outside the adapter, and every recipe subcommand's call graph reaches the machinery through exactly one adapter function; the root-resolution chain (explicit flag → environment variable → upward walk → structured degradation) and the interpreter chain (flag → environment → the running interpreter, with the wrapped machinery's import floor probed before first use) are each independently unit-testable against a synthetic filesystem and always record which step matched; every invocation carries a mandatory timeout whose expiry produces a distinct typed error and leaves no orphaned process; output parsing tolerates a leading non-JSON progress line before the JSON body; and Mason's own code reads no credential variable at all.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD 9d882c3ea0d: `pytest tests/meta/test_adapter_sole_caller.py tests/unit/test_resolve.py tests/unit/test_cfe.py tests/meta/test_credential_isolation.py` — 425 passed. Read `cfe.py` directly: every subprocess path (`_invoke_captured`/`run_streamed`) validates `timeout` finite+positive before spawning, catches `subprocess.TimeoutExpired` and raises typed `CfeTimeoutError`, and `kill()`+`wait()`s the child on every exit from `run_streamed` (not only the timeout path) — no orphan. JSON parsing (`cfe.py:721-764`) explicitly skips a leading non-JSON progress line before `json.loads`. Live-confirmed both resolution chains record which step matched: `mason doctor --format json` reports `"cfe_root_step": "cwd-walk"` and `"cfe_interpreter_step": "running-interpreter"`. `recipe.py` imports only `from . import cfe` and each verb calls exactly one `cfe.*` adapter (`validate` → `cfe.validate_recipe`, `build` → `cfe.build_native`/`build_docker`, `diagnose` → `cfe.diagnose_failure`, etc.), confirmed by grep. Credential blindness: `test_credential_isolation.py`'s real-tree scan (JFrog/enterprise-credential-variable, banned-HTTP-import, and process-environment-mutation detectors) runs clean across the whole `src/pyforge/mason` tree, not just `cfe.py` — `package.py`'s `PREFIX_API_KEY`/`TWINE_*` **presence** checks (never a value read, never logged) are CAP-3's ship-credential precondition, a distinct claim this CAP does not cover.

- **CAP-2 — `mason recipe`: the lifecycle, as a product face**
  - **intent:** A user carries a package through the whole conda-forge recipe lifecycle — generate, validate, build, diagnose, optimize, scan, submit, update — through Mason's verbs, with every piece of packaging judgement supplied by the machinery Mason delegates to and none of it living in Mason.
  - **success:** Generation from each supported upstream source produces a v1 recipe at a user-specified path with Mason asserting no field defaults of its own; validation exits non-zero on any reported failure with the machinery's finding identifiers and check codes preserved **verbatim** — never renumbered or reworded; native build is the default with any CI-parity build behind an explicit flag that is never implicit, streaming child output as it is produced rather than leaving a silent terminal for a multi-minute build; diagnosis names cause and fix, and says so plainly when the machinery returns none rather than inventing one; update shows the change before writing it; submission defaults to dry-run, requires an explicit confirming flag, preserves the two-phase prepare-then-open flow as separately addressable, and returns a ship receipt carrying the pull-request reference.
  - **verified:** 2026-09-11 — PARTIAL (one claim does not hold as written) — mechanical re-verification at HEAD 9d882c3ea0d: `pytest tests/unit/test_recipe.py` — 87 passed. Live `mason recipe --help` confirms exactly the eight verbs (`new,validate,build,diagnose,optimize,scan,submit,update`). `validate()` returns `cfe.validate_recipe`'s `CfeResult` unmodified (no reinterpretation); only `cli.py`'s own dispatch projects it onto the process exit code. `build`'s CLI registers `--docker`/`--config` as opt-in (native is the unconditional default), and `cfe.build_native`/`build_docker` are STREAM-mode (`run_streamed`), confirmed by grep — real streaming, not buffered. `diagnose_failure`/`optimize_recipe` pass the wrapped script's own JSON body through verbatim, including its `error`/`hint` no-match shape — no local invention. `submit`'s CLI defaults to dry-run (`--yes` required to confirm), `--prepare-only` is a separate flag, and `_ship_target_result_from_cfe_result` sets `reference=json_body["pr_url"]` on success. **Finding:** "update shows the change before writing it" does not hold for the default path. `update_parser`'s own help text says `--dry-run` is "default: writes the field-scoped update for real" — with no `--dry-run`, `recipe.py::update()` calls `cfe.update_recipe(["recipe_path"])` (confirmed by `test_update_default_apply_calls_update_recipe_with_recipe_path_only`, no `--dry-run` appended) and the wrapped script's own real-write JSON body is `{"success","updated","new_version","message"}` only (`cfe.py:1088-1108`; confirmed against the fake-CFE-root fixture's canned real-write payload) — no diff/plan field. The `actions` list showing what would change exists only under the opt-in `--dry-run` flag, as an ALTERNATIVE to writing, not a preview gate ahead of it. The memlog's own S-2.10 landing entry calls this "the recipe noun's diff-before-apply upstream version bump" in one clause and "the default performs a real, field-scoped write" in the next — an internal contradiction that predates this pass. Not fixed here (a behavior change, out of scope for a verification pass); flagged for the next CFE-adjacent retro or a dedicated story.

- **CAP-3 — `mason package`: the dual-ship motion**
  - **intent:** A user builds a library's artifacts and ships them to PyPI, a conda channel, and conda-forge in one motion — with a receipt that tells the truth about which targets are done and which are merely queued.
  - **success:** A build produces wheel, sdist and conda artifact from one project manifest, reports their paths, uploads nothing, and runs with the wrapped machinery absent; ship accepts exactly the four defined targets and rejects anything else while listing the valid set, honours multiple targets independently, and builds first if artifacts are absent by reusing the build implementation rather than duplicating it; a version disagreement between the wheel and the conda package aborts before any upload with both values shown; a missing credential is detected **before** any artifact is built or uploaded; one target's failure never prevents the others being attempted; a repeat ship to conda-forge for an already-open pull request reports `pending` with the existing reference and opens **no** second pull request; and Mason ships Mason — a rehearsal publish to the test index must pass before the irreversible one runs.
  - **verified:** 2026-09-11 — PASS (1 real environment bug found and fixed this pass) — mechanical re-verification at HEAD 9d882c3ea0d: `ShipTargetKind` is exactly `{PYPI, PYPI_TEST, CHANNEL, CONDA_FORGE}` (4, confirmed by grep); `_versions_disagree`/`PackageVersionMismatchError` abort before upload with both versions in the message; `ship_channel`/`ship_pypi` check `PREFIX_API_KEY`/`TWINE_*` presence in `environ` before calling `build()` (AD-14); `ship()`'s `_ship_one` closure wraps every target in `try/except MasonError`, so one target's failure is independent of the others; `ship()`'s own docstring plus code (`package.py:917-936`) confirm the rehearsal gate — the first `PYPI_TEST` target runs once ahead of the loop and every `PYPI` target in the same invocation is gated on its cached `state`, only running for real when that state is `TERMINAL`. The "repeat ship to an already-open PR reports pending, no second PR" behavior is CFE's own `submit_pr.py` idempotence (Mason passes `pr_url`/`success` through verbatim via `_ship_target_result_from_cfe_result`, confirmed by reading `recipe.py:661-717` — no reinterpretation); not independently re-provable from Mason's own code alone. **"Mason ships Mason" self-hosting proof, live re-run this pass** (normally slow-marked, excluded from the default task): `test_package_build_self_hosting_produces_real_versioned_artifacts`, `test_package_ship_self_hosting_dry_run_names_real_artifacts`, and all 3 `test_delegation_fidelity.py` tests — 5/5 passed, but only after fixing a real, currently-live bug this pass found: mason's own `pixi.toml` `[package.run-dependencies]` pixi pin was stuck at `>=0.77.0,<0.78` while the root workspace's `requires-pixi` floor had already moved to `>=0.80.0` (recurrence of the 2026-08-21 incident the pin's own comment named) — the `pyforge-mason` pixi environment therefore installed pixi 0.77.1 internally and both self-hosting tests failed with `"this project requires pixi >=0.80.0, but you have pixi 0.77.1"`. `pixi-version-check` reported clean throughout because this package-level run-dependency is not one of its 17 registered sites. Fixed in this same PR: bumped the pin to `>=0.80.0,<0.81`, the mirrored `PIXI_VERSION_RANGE` constant in `engines/__init__.py`, and the two asserted-evidence values in `test_engine_version_range_sync.py`, then `pixi install -e pyforge-mason` to regenerate `pixi.lock`; re-confirmed the fast suite (1582 passed) and the combined `pyforge-container` environment (which also composes the `pyforge-mason` feature) still resolve cleanly.

- **CAP-4 — `mason environment`: dependency binding**
  - **intent:** A user resolves a project's mixed conda and pip dependency sets into a single lockfile, and can ask in CI whether that lockfile has gone stale.
  - **success:** Solving is delegated entirely to an engine with Mason implementing no resolution logic; discovered manifests are listed before solving and explicit paths override discovery; platform targeting is repeatable and the engine's default is reported when none is given; the check verb exits non-zero on a stale lockfile and emits machine-readable output suitable for CI; the producing engine's name and version appear in output and in the lockfile's provenance where the format allows; and the whole capability runs with the wrapped machinery absent.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD 9d882c3ea0d: `pytest tests/unit/test_environment.py tests/unit/test_engines_condalock.py` — 65 passed. `discover_manifests()` (Story 4.2) is built and wired into `cli.py`'s `lock`/`check` dispatch (`cli.py:1392`/`1441`), called only when the caller supplies no explicit `manifest_path` — confirmed by reading the call sites: explicit paths bypass discovery entirely. conda-lock is the sole lock engine (no pixi-lock adapter exists), matching the Spec's own recorded OQ-5 resolution. `environment.py::lock`/`check` never import `cfe` — `environment lock`/`check` are CFE-independent by construction, structurally satisfying "runs with the wrapped machinery absent" without needing CAP-3's allow-list mechanism. Engine name/version and machine-readable JSON/exit-code behavior for `check` were not independently re-exercised live this pass beyond the green unit suite; re-confirmed by that suite's assertions rather than a fresh live invocation.

- **CAP-5 — the CLI shell and output contract**
  - **intent:** Mason presents one coherent public surface — a noun-verb command tree with both human and machine output, a stable exit-code contract, structured errors, and the ability to diagnose its own installation truthfully, including what it cannot do.
  - **success:** Three nouns plus top-level self-diagnosis and version; a bare noun prints that noun's verbs and exits non-zero, with exactly one documented alias exception that a test asserts is the only one; under machine output stdout carries exactly one JSON document or nothing while every diagnostic goes to stderr; exit codes originate from one module and no command computes its own; every anticipated failure produces a typed error with a stable identifier and an actionable message, and none surfaces as a raw traceback; self-diagnosis reports Mason's version, the resolved root and which step found it, the selected interpreter and whether the import floor is satisfied, and each engine's presence and version — **exiting 0 when Mason is usable for the non-wrapping verbs even with the machinery missing**, reporting the gap rather than failing; and no global flag is required for any command to run.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD 9d882c3ea0d: `pytest tests/unit/test_cli.py tests/meta/test_exit_code_ownership.py tests/unit/test_doctor.py tests/meta/test_render_ownership.py tests/unit/test_exit_codes.py` — 348 passed. Live-invoked this pass: `mason --version` → `mason 0.1.0`, exit 0; `mason recipe` (bare noun, no `--format`) → the full verb listing printed via argparse usage, exit 2 (non-zero); `mason doctor --format json` → a single JSON document on stdout, empty stderr, exit 0, body containing `mason_version`, `cfe_root`+`cfe_root_step` ("cwd-walk"), `cfe_interpreter`+`cfe_interpreter_step` ("running-interpreter"), `cfe_import_floor_satisfied`/`cfe_import_floor_missing`, `unavailable_verbs`, and each of the 5 engines with `name`+`version`. `exit_codes.py` alone defines all five exit codes (`0/1/2/3/130`, confirmed by grep — no `EXIT_*` constant exists anywhere else in the tree). `test_recipe_and_environment_bare_nouns_still_usage_errors_after_ship_lands` + `test_package_ship_bare_noun_alias_dispatches_identically` together demonstrate `package --ship` is the exactly-one documented alias and `recipe`/`environment` carry none. **Currency note:** this live doctor run shows `cfe_import_floor_satisfied: true` and `unavailable_verbs: []` — both 2026-09-09 "Realization-gate re-read" gaps are now resolved (Story 16.1 / Story 16.2 landed since that note was written); see the dated addendum appended below.

- **CAP-6 — distribution**
  - **intent:** Mason ships the way its siblings ship, so the capability finally leaves the repository it was invented in.
  - **success:** One project manifest drives both a conda artifact and a wheel plus sdist, all building green through the three-task build triad; the console entry point resolves and reports the installed distribution version; the root workspace carries a path dependency and a lean environment for the member; engines are conda run-dependencies with declared version ranges mirrored by in-code constants and kept in sync by a meta-test, and nothing is fetched at runtime; and the wheel's dependencies contain only what the module imports, with any dependency on a sibling package an optional extra rather than a hard requirement.
  - **verified:** 2026-09-11 — PARTIAL (one claim does not hold as written, reconciled below) — mechanical re-verification at HEAD 9d882c3ea0d: live re-ran the full three-task build triad this pass (`pixi run -e pyforge-mason pyforge-mason-build`) — `pyforge-mason-build-conda` (`pixi build`) and `pyforge-mason-build-dist` (`python -m build`) both green from the one `pyproject.toml`/`pixi.toml` pair, producing `pyforge-mason-0.1.0-pyh4616a5c_0.conda` + `pyforge_mason-0.1.0-py3-none-any.whl` + `.tar.gz`. The `mason` console entry point (`pyproject.toml`'s `[project.scripts]`) live-confirmed: `mason --version` → `mason 0.1.0`. Root `pixi.toml` carries the path dependency (`pyforge-mason = { path = "src/shared/packages/pyforge-mason" }`) plus a lean `[feature.pyforge-mason.dependencies]` block. All 5 engines are conda run-dependencies with ranges mirrored 1:1 in `engines/__init__.py`, kept in sync by `test_engine_version_range_sync.py` — this pass found and fixed a real, live drift in that sync (see CAP-3's verified line for the same fix: mason's own pixi run-dependency pin lagged the root `requires-pixi` floor, breaking the self-hosting build/ship proof until fixed). **Finding:** "any dependency on a sibling package [is] an optional extra rather than a hard requirement" does not hold as written — `pyproject.toml`'s `dependencies = ["packaging", "pyforge-core", "PyYAML>=6.0.3"]` lists `pyforge-core` as a plain hard dependency, not a `[project.optional-dependencies]` extra. This is a real, deliberate, already-reconciled divergence, not a defect: the memlog's 2026-08-13 "SURFACE DRIFT RECONCILED" entry records that `pyforge-marshal/spec-pyforge-core`'s "one lattice, one envelope, one exception root" mandated `pyforge-core` as a hard run-dependency fleet-wide (`MasonError` re-parents to `PyforgeError`) — a cross-spec authority overriding this CAP's original text, never reflected back into it or into this Spec's own "Divergences and scope growth" list; added as item 6 there in this pass.

- **CAP-7 — proving the seam holds, and closing the loop**
  - **intent:** The product's central guarantee — that Mason wraps the packaging capability and never forks it — is verified by tests rather than asserted by documentation, and the effort closes by improving the very skill it wraps.
  - **success:** The knowledge deny-list is declared in one reviewable module where every entry cites the artifact it derives from, **and ships positive fixtures planting a violation of each category so that a deny-list matching nothing is a failing test, not a passing one**; weakening or removing an entry requires a rationale a companion test asserts is present; the sole-caller test finds no reference to the wrapped machinery outside the adapter; the independence test runs every `package` and `environment` verb with the root guaranteed unresolvable behind a **named one-entry allow-list**, asserting positively that the excepted target fails for the *right* reason; the governance check stays green with zero implementation commits touching the governed surface and exactly one sanctioned retrospective commit that does; the fidelity test proves Mason transforms presentation rather than semantics, is slow-marked, excluded from the default task, and **skips cleanly** when no root resolves; and the effort is not done until the retrospective lands skill edits plus a dated changelog entry with a semver bump.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD 9d882c3ea0d: `pytest tests/meta/test_no_recipe_knowledge.py tests/meta/test_cfe_independence.py tests/meta/test_capability_tiers.py` — 86 passed, including `test_deny_list_entries_all_carry_a_citation_and_rationale` (every entry cites its source plus a non-empty rationale) and `test_detector_fires_on_a_planted_gotcha_identifier`/`test_detector_fires_on_a_planted_check_code` (non-vacuous by construction) and `test_cfe_dependent_ship_targets_allow_list_has_exactly_one_entry` (the named one-entry allow-list, structurally asserted, not just a comment). `test_delegation_fidelity.py`'s 3 tests (slow-marked, excluded from the default `pyforge-mason-test` task) explicitly re-run this pass: the fidelity test itself passes, and `test_delegation_fidelity_test_skips_when_no_real_cfe_root_resolves` confirms the clean-skip contract. Governance check, git-verified directly against `origin/main`'s real merged history (not `--all`, which pulls in unmerged worktree-agent branches — 3 false positives were found and excluded that way): searched every commit touching `src/shared/packages/pyforge-mason/**` in `origin/main`'s ancestry for one that ALSO touches the governed CFE surface (`.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`, `.claude/tools/conda_forge_server.py`) in the same commit — **zero found**. Every `retro(cfe):`/`retro:` commit on `main` lands as its own dedicated, CFE-surface-only commit, never bundled with a mason src change — a cleaner invariant than the constraint's literal "one sanctioned exception" phrasing implies (CLAUDE.md Rule 2 retros run once per story, each its own standalone commit, not once ever across the whole project). Note: `scripts/cfe_rebuild_guard_check.py` (the Epic 6 CFE-rebuild-campaign's own governance script, belonging to the separate `spec-conda-forge-expert-rebuild`, explicitly named outside this kernel's CAP-1..7 scope by this Spec's own Currency reconciliation item 1) currently reports 2 "unmirrored-retro" findings for its own slice briefs — checked and confirmed out of this CAP's scope, not a CAP-7 finding.

## Constraints

- **The central decision — wrap by capability, not by product.** Mason **wraps** the packaging machinery by subprocess for all recipe operations and **builds** natively for `package` and `environment`. The boundary is drawn by *capability*. Pure porcelain was rejected because two of the three charter verb families have **nothing to wrap** — no wheel build, no upload path and no lock orchestration exists anywhere in the wrapped machinery's 41,410 lines, so a pure wrapper is not a smaller Mason but a Mason missing its reason to exist. Extraction/reimplementation was rejected on three independently sufficient grounds: **governance makes a fork structurally adversarial** (Rule 1 makes the skill authoritative over any conflicting story, and Rule 2 mandates that every conda-forge effort *edits the skill* — so a fork is continuously invalidated by the loop that governs the domain); **the in-repo precedent failed** (a sibling project rebuilt ~29,000 lines across 32 merged stories and the 8,902-line original is still the live runtime — nothing routes to the rebuild); and **it forks the moat**, converting 106 gotchas and 10 constraints from an appreciating asset into a depreciating one. The accepted cost, paid deliberately: **Mason is not standalone** — `mason recipe` requires a discoverable installation and is inert without one.
- **Knowledge-free core.** No module in Mason may contain a conda-forge gotcha identifier, policy constant, pin table, recipe-format field default, or selector/platform rule. Recipe semantics enter Mason only as opaque data through the port. Enforced by a meta-test with an explicit deny-list — because this repository has already proven that intent alone does not prevent the failure.
- **The port is the sole caller.** One module may name a wrapped script, hold its path, or spawn its process; every script used is declared once in a module-level table there, and a use-case calls a named adapter function rather than passing a script name. *(Amended 2026-08-10: AD-3 carries a two-entry carve-out — `resolve.py`'s root-marker constant and `errors.py`'s guidance echo, each allowlisted with a rationale comment; script names and process-spawning have no exception.)*
- **Subprocess only — never import, importlib, or exec.** Five of the wrapped modules are physically unimportable (hyphenated filenames, including the 2,653-line recipe generator, in a tree governed by a changelog sentinel so renaming is unavailable); import would inherit `__file__`-relative data resolution that is meaningless from an installed location, a repo-root anchor that varies across scripts, 55+ credential environment reads, and a documented hang history with no in-import timeout. Every invocation is a timed subprocess returning a typed result in which a non-zero return code is **data, not an exception**.
- **Capability tiers are structural, not conventional.** CFE-dependent: the recipe use-cases and **only** the `conda-forge` ship target. CFE-independent: everything else. The port resolves **per target, not per command** — a PyPI ship must succeed with the machinery absent. The exception is a named one-entry allow-list; a blanket "except where CFE is needed" formulation is explicitly forbidden, because that phrasing is the erosion the rule exists to stop.
- **The wrapped surface is read-only for the mason-CLI effort; the sanctioned rebuild replaces it under its own Spec's gates** *(amended 2026-08-10, correct-course — operator directive: the current skill is unsustainable, we rebuild and shift to the mason rebuilt version; parallel-run shape with equivalence-harness / dual-landing / end-cutover mitigations; see `spec-conda-forge-expert-rebuild` and amended AD-15)*. No *implementation* commit of THIS effort writes to the governed tree. Behaviour Mason needs and the machinery lacks is an open question routed to that machinery's own retrospective — never a local patch, never a vendored copy. Exactly one sanctioned exception: the closing retrospective, identified by a `retro:` subject plus a changelog entry in the same commit, with the check asserting it is used **once** so it cannot be borrowed to sneak an implementation change through.
- **Degradation is designed behaviour, never a crash.** An unresolvable root makes recipe commands exit non-zero naming all four resolution steps and how to satisfy each, while the other two verb families run unaffected. No command emits a Python traceback for this condition.
- **Resolution is a pure decision over inputs.** The resolution chains are pure functions over (explicit argument, environment mapping, start directory) performing filesystem *reads* only — never writes, network, or process spawns — and the outcome always records which step matched, so self-diagnosis reports without re-resolving.
- **Dependencies point inward only, and no use-case imports `subprocess`.** That single rule is what stops recipe logic leaking inward one helper at a time.
- **Mason never solves and never builds from scratch.** Every external tool is an adapter behind one protocol, discovered on `PATH`, provisioned as a conda run-dependency, and **never downloaded at runtime**; a missing engine is a typed error naming the engine and how to provision it.
- **One shared shape for all shipping, and `pending` is never collapsed into success.** Every target yields a state of `not_attempted`, `failed`, `pending`, or `terminal` plus a reference; the aggregate exit code is failure only if a target failed to *initiate*. PyPI completes in seconds and conda-forge completes in days behind a human review queue — reporting a uniform success for a queued pull request is a correctness bug, not a presentation choice. Adding a target means adding an adapter that produces this shape, never a new shape.
- **Idempotence by interrogating the target, never by local state.** Mason persists no state directory, no receipt cache, no lock file of its own — a local cache is a second source of truth that goes stale and silently skips a real upload. An uninterrogable target yields `pending` with the reason stated, never an assumption in either direction.
- **One owner per operation.** Staged-recipes submission has exactly one implementation, reached through the port; the `conda-forge` ship target *calls* it and wraps the result, and `mason recipe submit` is the same call rendered directly. Neither may reimplement the other.
- **One error taxonomy, one exit-code owner.** All anticipated failures are typed errors carrying a stable identifier that **is API** — changing one is a major version bump. A single module is the sole producer of every exit code; no other module computes or hardcodes one.
- **Core returns data; only the driving adapter formats.** Use-cases return frozen dataclasses; one renderer turns them into text or JSON. Under machine output, stdout carries exactly one JSON document or nothing and every diagnostic, progress line and log record goes to stderr. No use-case writes to stdout.
- **Credential blindness.** Mason reads no enterprise credential variable and makes no authenticated request on the wrapped machinery's behalf — credentials reach it only through the inherited process environment, confining that machinery's known-unconditional credential-header injection to its own process. Upload credentials are read at the point of use, never stored on a rendered or logged object, and validated **before** any artifact is built. No code path logs an environment-variable *value* at any verbosity.
- **No configuration file in v1.** Configuration is flags and environment variables only, precedence uniformly flag → environment → default, with the knob set enumerated. Two configuration systems with undefined precedence is the classic source of "it works on my machine."
- **Safety by default.** Every mutating verb accepts a dry-run flag and defaults to it where the operation is irreversible. A PyPI upload is recognized as irreversible and the dry-run plan says so explicitly.
- **Every test runs against a fake root.** The suite ships a fixture root of stub scripts with canned output; no test requires a real installation, network, or recipe directory — otherwise Mason's own CI would depend on the very co-location the design admits is a constraint. Exactly one declared exception, and it skips cleanly rather than failing.
- **Workspace conventions are adopted wholesale, not reconsidered.** Member layout under the shared packages tree, a member manifest with no workspace table, a namespace package with no package initializer, one build manifest driving both artifacts, `argparse` (no CLI framework dependency for ergonomics alone), lean dependencies, Python floor `>= 3.12`.
- **Offline-safe and enterprise-neutral.** Every command not inherently requiring the network runs offline and network use is never implicit; Mason imposes no direct-internet assumption, inheriting proxy and mirror routing through the process environment; Mason's own logic works on linux-64, osx-arm64 and win-64 with platform limits belonging to the engines and reported as such; and Mason never renders templates or executes recipe content itself.

## Non-goals

- **Mason will never hold recipe knowledge.** Not a v1 deferral — a permanent property.
- **Mason is not a fork.** No extracted, vendored, or re-implemented copy of the canonical scripts, in any version.
- **Mason does not modify the wrapped surface** — it is governed by its own Spec and authoritative over Mason.
- **Mason does not solve dependencies.** It orchestrates solvers.
- **Mason does not replace the existing pixi task surface in v1.** Additive; nothing is removed or deprecated. The sibling project's failure was not the rebuild alone — it was a rebuild with no migration. Mason earns the surface first; migration is its own effort.
- **Mason does not ship a second MCP server** duplicating the existing 46 tools — that is the sibling's failure mode in miniature.
- **Mason is not a build system**, and **not a general-purpose release manager**: changelogs, tags, releases and version bumping are out.
- **No operation in a repository with no discoverable installation** — it would require changing a surface Mason may not edit, which is reimplementation by the back door.
- **No shipping to conda-forge from a project with no co-located recipe source directory.** The submission flow reads from that path and writes into a fork clone, and Mason may not change either. This is the honest v1 boundary, stated up front and reported by self-diagnosis before a release is attempted — **not** a hidden failure. The PyPI half has no such limit.
- **No trusted-publishing credential flow in v1** — token-based only.
- **No multi-ecosystem autotick** (CRAN/npm/cargo updaters), **no smart test extractor**, **no static dependency-version checker** — the origin Dream's frontier, not v1.
- **No application or binary project shapes** — v1 is `library` only.
- **No persistent state and no concurrency** — every operation is sequential in v1, and the per-target result shape already permits parallelism later without a redesign.

## Success signal

**Mason ships Mason.** The master switch: `mason package` publishes `pyforge-mason` itself — rehearsal to the test index first, then the real one — and its build produces the same conda artifact the repository's hand-run build triad produces today. Until Mason can ship Mason, the dual-ship claim is unproven, and the honest caveat is that what the repository dogfoods today is the dual-artifact **build**, not the ship: neither sibling package has a publish task, so the ship half is a genuine first, which is exactly why the rehearsal gates the irreversible upload.

Supported by five secondary signals, each demonstrable rather than asserted: the deny-list test is green at every commit **and its own planted-violation fixtures prove it is not vacuous**; the independence allow-list has exactly one entry; a gotcha added to the wrapped skill *after* Mason ships changes Mason's behaviour with **no change to Mason**; the conda artifact, wheel and sdist all build green from one manifest; and the governance check is green with exactly one sanctioned retrospective commit carrying a dated changelog entry and a semver bump.

Deliberately **not** optimized, and tracked as counter-metrics: Mason's own line count (approaching the wrapped machinery's scale means the wrap decision has quietly inverted), the recipe verb count (wrapping all 46 tools would be surface bloat, not product — coverage is not a goal), and adapter surface area (a growing adapter API means recipe logic is migrating into Mason one helper at a time).

## Assumptions

- The Charter's verb cadence (`recipe build`, `package --ship`, `environment lock`) is binding product scope, taken verbatim and never confirmed with a stakeholder.
- "Dual-ecosystem" means conda-forge + PyPI. npm, CRAN, CPAN and LuaRocks are *source* ecosystems for recipe generation, not ship targets.
- The target operator is the individual maintainer or small team already using pixi — not conda-forge core infrastructure, where the autotick-bot is the incumbent and Mason would be redundant.
- The conventions demonstrated by the two sibling packages are normative for a new workspace member. Inferred from two instances and their in-file comments; no written standard exists.
- The wrapped machinery's stdout is stable enough to parse — a **de-facto** contract evidenced by 46 MCP tools over an extended period with one known tolerance shim, not a formal one. Mason inherits the risk and bounds it with tolerant parsing plus the fidelity test.
- Local measurements (41,410 lines, 106 gotchas, 10 constraints, 46 MCP tools, 1,186 tests, 769 feedstocks, 17 scripts hardcoding the recipe directory) are point-in-time and **will drift** — used for shape arguments, never as commitments.
- PyPI and the forge can be interrogated cheaply enough to make interrogation-based idempotence practical. If not, the revisit must reopen the no-persistent-state rule explicitly rather than adding a cache quietly.
- `packaging` is the only non-stdlib runtime import Mason needs; any addition must be justified at the story that introduces it.
- The conda build backend's preview member-package semantics remain stable for the duration — both existing members already carry this exposure.
- Mason's own package is representative enough to prove shipping. It is **pure Python**; a compiled package would exercise paths this self-hosting test does not.
- `pixi publish`'s documented silence on PyPI reflects an absent feature — not verified against its source.

## Open Questions

The chain's adversarial review returned *major revision required* and **was resolved**: revision 2 of the PRD added four requirements and four decision records, fixing the closeout contradiction, the missing ship verb, the flagship-journey scope conflict, and two requirement-level contradictions. Nothing below is a blocker; these are the decisions the chain deliberately left to architecture, implementation, or a later scoping round.

1. **Which wrapped script backs each recipe verb?** The adapter's declaration table must name one per verb — mechanical, no invariant depends on it, but it must exist before the first recipe-verb story starts.
2. **Which recipe verbs beyond the eight in scope earn a place?** Deferred to usage; the verb-count counter-metric warns against reflexive coverage.
3. **What exactly is the knowledge deny-list's content?** The rule is fixed; the concrete pattern set is an implementation artifact that must be reviewable and hard to weaken silently, and needs a review gate of its own — a vacuous deny-list passes forever while the seam sits unguarded.
4. **Does the channel target upload via `pixi publish`, `anaconda upload`, or both?** An engine choice with no product consequence; both satisfy the protocol.
5. **Should the lock capability prefer `conda-lock` or `pixi.lock` when both are viable**, and is the relationship between them one of succession? Unresolved by available sources; may need both adapters.
6. **Is the CI-parity container build reachable through the adapter at all?** That path is a task rather than a canonical script, and the local builder is explicitly container-less. If no adapter-reachable entry point exists, the CI-parity build drops from scope — it is the one part of the build requirement with no confirmed wrappable target.
7. **Can the governance check inspect the effort's commit range automatically** in this repository's branching model, or must it be a documented manual gate?
8. **Does Mason own multi-ecosystem autotick, or is that another station's territory?** The origin Dream places it in the packaging factory; the Charter omits it from Mason's cadence. This is the most load-bearing deferral — the Dream's headline frontier item.
9. **Does Mason declare a minimum version of the wrapped machinery** once coupling fragility is observed? v1 declares none: delegation is by argv and the machinery's own semver governs its behaviour, so a break is fixed in the adapter.
10. **Is there a real user for application or binary project shapes**, or is `library` the whole product?
11. **Competitive coverage risk** — the survey was assembled from known primary sources **without a web-search budget**, and a discovery sweep for unknown dual-publish entrants has not been run. An existing entrant would invalidate the central decision's differentiation premise.
12. **Does the conda-forge shipping boundary change the product's positioning claim**, or is "the PyPI half works everywhere, the conda half works where your recipes live" an acceptable public story?
13. **Should self-diagnosis be a fourth noun or a top-level verb?** Currently top-level; cosmetic, no invariant affected.

---

## Currency reconciliation — 2026-08-26 (as-built truth-up)

The station shipped: the fleet ledger reported mason **complete 2026-08-21** (11 epics / 50
stories all `done` in `sprint-status-ledger.yaml`), with three post-completion stories (10.1
build-engine hook, 11.1 persona, 11.2 portal slice) landing 2026-08-25/26. This section
reconciles the Spec against the as-built code in `src/shared/packages/pyforge-mason/`; the
capability text above (CAP-1..CAP-7) is confirmed accurate as written unless named below.

**As-built surface (ground truth).** `mason recipe {new,validate,build,diagnose,optimize,scan,
submit,update}` (the eight CAP-2 verbs, exactly); `mason package {build,ship}` plus the one
documented bare-noun alias `mason package --ship <targets>` (D-12) — CAP-5's "exactly one
documented alias exception" holds, guarded by `cli.py`'s explicit reject of `--ship` combined
with a verb; `mason environment {lock,check}`; top-level `mason doctor` (OQ-13 settled:
top-level, as built). Six global flags (AD-13's closed set) each with a `MASON_*` environment
form; five exit codes (0/1/2/3/130) owned solely by `exit_codes.py`. Engines as provisioned
(`_KNOWN_ENGINES`, five): `pixi`, `twine`, `conda-lock`, `build` (`pyproject-build`), `gh` —
adapters `engines/{pep517,pixi,twine,condalock,gh}.py` plus the `pypi_index.py` PyPI-JSON
interrogator (CAP-3 idempotence) — with in-code version-range constants mirrored from
`pixi.toml` and held in sync by `tests/meta/test_engine_version_range_sync.py` (pixi 0.77.x /
twine 7.x / conda-lock 4.x as of 2026-08-21).

**Open Questions settled by implementation** (list left intact above as the historical record):
OQ-1 — the adapter declaration table exists in `cfe.py` (one wrapped script per recipe verb).
OQ-3 — the deny-list landed as `tests/meta/test_no_recipe_knowledge.py` with planted-violation
fixtures (S-2.2), non-vacuous by construction. OQ-4 — the channel target uploads via
`pixi upload prefix` (neither `pixi publish` nor `anaconda upload`; PRD OQ-2 resolution,
2026-08-13). OQ-5 — `conda-lock` is the sole lock engine (`engines/condalock.py`); no pixi-lock
adapter was built. OQ-6 — the CI-parity container build **was** adapter-reachable: `mason recipe
build --docker --config` shipped in S-2.6, so the drop-from-scope contingency never triggered.
OQ-7 — the
governance check inspects the commit range automatically: S-5.2 scopes to commits touching
`src/shared/packages/pyforge-mason/**` (correct-course, 2026-08-10). OQ-11 — the competitive
discovery sweep ran as `../../research/market-mason-packaging-automation-2026-08-08.md`: no
dual-ship entrant found; the differentiation premise held. OQ-13 — top-level, as built. Still genuinely open: OQ-2
(verbs beyond eight — none added, counter-metric respected), OQ-8 (multi-ecosystem autotick
ownership), OQ-9 (minimum CFE version — none declared, no adapter break observed yet), OQ-10
(application/binary shapes), OQ-12 (positioning claim).

**Divergences and scope growth, named:**

1. **Scope grew past CAP-1..CAP-7.** Epics 6–11 shipped under authority this kernel does not
   carry: Epic 6 (CFE-rebuild pilot slice + re-scope gate) under `spec-conda-forge-expert-rebuild`
   and amended AD-15; Epic 7 (machine-checked recipe knowledge); Epic 8 (pixi base-layer
   Containerfile convention); Epic 9 (workflow_call CI + the air-gap distribution contract
   socket, `airgap_contract.py`, empty backend registry by design); Epic 10 (the replaceable
   build-engine hook `engines/build_hooks.py`, default = the CFE-native path, conda-build
   registered but never spawned — canopy:AD-21); Epic 11 (the `bmad-agent-mason` persona that
   consults conda-forge-expert, and the `/stations/mason/` last-diagnose portal slice via
   PortalClient — canopy FR-38/FR-10). Those bind to their own spec/canopy contracts; this
   kernel remains the contract for the mason CLI itself.
2. **The 2026-08-08 market-research recommendations were partially adopted.** Adopted: channel
   upload via the pixi/rattler upload family (§ 2c). **Not adopted:** the neutral
   `pypi_upload` adapter name — the uploader shipped as `engines/twine.py` with twine the
   engine (uv remains a swap behind the AD-12 protocol, at rename cost); and the pixi-first
   lock-engine recommendation (§ 4) — Epic 4 shipped conda-lock-only. Both are recorded
   decisions, not oversights.
3. **The success signal is proven at the rehearsal tier.** "Mason ships Mason" landed as S-3.8's
   real self-hosting proof of the ship **dry-run plan** plus S-3.9's TestPyPI rehearsal gate;
   the irreversible public PyPI publish of `pyforge-mason` has not been executed. The honest
   caveat in § Success signal stands and is now dated rather than hypothetical.
4. **Code exists beyond this Spec's surface intent:** `boot.py` (steward S-25.4 boot re-index —
   steward-owned contract hosted in the mason package) sits outside CAP-1..7; noted so the
   "counter-metrics" reading of Mason's line count attributes it correctly.
5. **`behind-code` suppression is now by design:** with the owner Dream flipped to `realized`
   (2026-08-26), the chain-layers audit's behind-code flag for this station is retired — the
   chain is no longer "still being built."
6. **`pyforge-core` is a hard dependency, not the optional extra CAP-6 describes** (found during
   the 2026-09-11 CAP-verification pass): `pyproject.toml`'s `dependencies` list carries
   `pyforge-core` unconditionally. The 2026-08-13 memlog entry "SURFACE DRIFT RECONCILED... marshal
   Story 14.3" records why — `pyforge-marshal/spec-pyforge-core`'s "one lattice, one envelope, one
   exception root" mandated it fleet-wide so `MasonError` re-parents to a shared `PyforgeError`
   base, the same pattern six other stations already carry. A deliberate, recorded, cross-spec
   decision that supersedes CAP-6's original text; never folded back into it until now.

### Realization-gate re-read — 2026-09-09

A **gap, not a defect**, and not a status change: the owner Dream keeps `status: realized` and
this Spec is `shipped`. What the gate finds is that the station's differentiator is not
exercised anywhere in the estate.

1. **`mason doctor` in mason's OWN pixi env reports `cfe_import_floor_satisfied: False`,
   `cfe_import_floor_missing: (truststore, conda-forge-metadata)` and
   `unavailable_verbs: ('recipe',)`** — because `[feature.pyforge-mason.dependencies]`
   (`pixi.toml:281-283`) declares neither floor dependency while `cfe.py:180-186`'s
   `CFE_IMPORT_FLOOR` requires both. CAP-5's graceful-degradation contract is working exactly
   as specified; what is unexercised is **CAP-2**, the station's differentiator. Vessel:
   **Story 16.1** (the env satisfies the CFE import floor — `pixi.toml` + a regenerated
   `environment.yaml` + a regression test; CLAUDE.md Rule 1/Rule 2 apply, it is CFE-floor work).
2. **Nothing in the estate invokes `mason recipe`, `mason package` or `mason environment`** —
   one comment at `pixi.toml:797`, zero call sites; all recipe work still routes through
   `pixi run -e local-recipes recipe-build`. "Mason ships Mason" remains rehearsal-tier (no
   `recipes/pyforge-mason` recipe, no public publish — consistent with item 3 above). Vessel:
   **Story 16.2** (a first estate caller of `mason recipe`, outside mason's own test tree —
   Story 49.2's effect check: "has a caller outside its own test file").

Both stories are minted on mason's own epics; steward Epic 49 carries the index row.

### Realization-gate resolution — 2026-09-11

Both gaps above are now resolved, confirmed live during this pass's CAP-5 re-verification
(`mason doctor --format json` in mason's own pixi env reports `cfe_import_floor_satisfied: true`,
`cfe_import_floor_missing: []`, `unavailable_verbs: []`):

1. **Story 16.1 landed** (`truststore`/`conda-forge-metadata` added to
   `[feature.pyforge-mason.dependencies]`, commits `6c8f2cc03d8`/`d220e6258c5`/`f5307f5c776`) —
   `cfe_import_floor_satisfied` flips to `true`, the recipe verb is available in mason's own env.
2. **Story 16.2 landed** (commits `3c8caaab3e8`/`5bdb3b5aba9`) — the new
   `pyforge-mason-recipe-build-smoke` pixi task (`mason recipe build recipes/click-help-colors`) is
   wired into `.github/workflows/pyforge-station-tests.yml`'s mason-test job, giving `mason recipe`
   its first real estate caller outside mason's own test tree. "Mason ships Mason" remains
   rehearsal-tier for the *ship* half (item 3 above still stands — no public PyPI publish); the
   *build* half of the differentiator is now exercised in CI on every run of that lane.

### The `status:` key — added 2026-09-09

This Spec carried **no `status:` line at all** (it uses the `id:` form), so `chain-completeness`
never saw it and reported 7/7 CAPs uncovered. That was a bookkeeping defect, not a coverage one.
`status: shipped` is now declared. Fleet note: eight Specs across the fleet carry no status line
(doctor ×4, marshal ×3, mason ×1) — this was mason's one.

## Satellite: Presenton (air-gapped conda-native repackaging)

**Status: BLOCKED.** This satellite Spec was finalized 2026-07-25 and governs a genuinely different
product from `mason` itself: an air-gapped, conda-forge-native repackaging of the third-party
Presenton AI deck-generation app for Red Hat OpenShift. Its owning Dream
(`docs/dreams/presenton-pixi-image.md`) carries `status: archived`, `archived-reason: blocked`,
`blocked-on: Phase-0 decision gate (Epic 1)` — no story has entered implementation, and the six
Phase-0 exit criteria named in the Open Questions below (most load-bearingly, exit 6a: whether
Microsoft's disconnected on-prem stack already ships a Copilot-for-PowerPoint-equivalent) remain
unresolved.

**Contradiction flagged — the most direct one in this whole consolidation.** On 2026-08-02, *before*
this consolidation, this satellite's own `SPEC.md` was rewritten from a live five-field kernel into an
archived retirement record. That retirement record names, as an explicit **non-goal**: *"Folding this
Dream's intent into `pyforge-mason`'s own narrative"* — reasoning that *"the two are genuinely
different subject matter... archiving this separately (rather than absorbing it) reflects that
difference honestly."* What follows in this section does exactly what that non-goal forbade. It is
done at the user's explicit direction, after being shown that separation language, overriding the
2026-08-02 retirement decision for the **planning-chain tier only** — the Dream-level narrative and
the epics/blocked-status stay separate (per `docs/dreams/pyforge-mason.md` § *Related but out of
scope*). This is recorded here rather than silently resolved. See
`archive/_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-presenton-pixi-image/` for
both the retirement record and (in git history within that archived copy) the live five-field kernel
this section reconstitutes.

**No other contradiction found** between the two kernels' Constraints/Non-goals: Presenton's own
AD-19 ("recipe.yaml content itself is out of this Spec's scope, governed by conda-forge-expert per
CLAUDE.md Rules 1 and 2") is consistent with — not contradicting — Mason's own stance that CFE is
authoritative over recipe semantics.

**Own scope, continued numbering.** Presenton's capabilities are folded in below as **CAP-8..CAP-13**
(continuing after this Spec's own `CAP-7`), and its Constraints' `AD-n` references are renumbered to
**AD-17..AD-24** to match the renumbering already applied in the merged
`ARCHITECTURE-SPINE.md`:

| Original ID | Renumbered ID |
|---|---|
| CAP-1 Air-gapped browser rendering | **CAP-8** |
| CAP-2 Clean-room deck export pipeline | **CAP-9** |
| CAP-3 LLM provider abstraction and tiering | **CAP-10** |
| CAP-4 Signed air-gapped image assembly | **CAP-11** |
| CAP-5 OCP deployment and operations | **CAP-12** |
| CAP-6 Upstream drift defense | **CAP-13** |
| AD-1 (build routing) | **AD-17** |
| AD-2 (one true port) | **AD-18** |
| AD-3 (recipe/image boundary) | **AD-19** |
| AD-5 (single provenance pass) | **AD-21** |
| AD-6 (phase-boundary enforcement) | **AD-22** |
| AD-8 (SCC target) | **AD-24** |

*(AD-4 and AD-7 are cited only inside capability success text below, renumbered to AD-20 and AD-23
respectively, consistent with the architecture spine — Presenton's own Constraints section never
headed those two directly.)*

### Presenton Capabilities

- **CAP-8**
  - **intent:** The image renders decks using a bundled, air-gap-buildable Chromium, with zero reachable public CDN at build or runtime.
  - **success:** `playwright-with-chromium` builds, validates, is scanned, and is optimized; AD-17's zero-external-CDN build routing holds; AD-20's Chromium sandbox defaults to a documented `--no-sandbox` posture compatible with OpenShift `restricted-v2`/`restricted-v3`.
- **CAP-9**
  - **intent:** The image renders AI-generated slide content into an editable `.pptx` (image-overlay + extracted-text-shapes fidelity — Decisions Log Q1) carrying a real `docProps/thumbnail.jpeg`, replacing the opaque upstream export bundle and `convert-linux-x64` binary with clean-room, source-available components wired in via Presenton patches.
  - **success:** `presenton-export-node`, `pptx-assembler`, and `pptx-thumbnail-inject` each build+validate+scan+optimize and pass Fixture Set 1 — `AC-FX-AUTHOR-01` (byte/structural equivalence) and `AC-FX-AUTHOR-02` (image SSIM ≥ 0.99).
- **CAP-10**
  - **intent:** The deployed app selects among three OpenAI-compatible LLM tiers (Tier 1 external corporate proxy, Tier 2 in-cluster `llama.cpp` sidecar, Tier 3 init-container GGUF fetch) purely via one env-var contract, with the `copilot-bridge` VSIX covering the VS Code developer inner loop.
  - **success:** `llmai` lands on conda-forge; Helm `values.llmProvider.tier` selects a sub-block with no per-tier code fork (AD-18); per-refinement latency ≤10s P95 on Tier-1 (measurable outcomes table).
- **CAP-11**
  - **intent:** The five confirmed recipes assemble into one pixi-locked, reproducibly-buildable OCI image, carrying a pre-wired, default-off memory-subsystem feature flag, with SBOM generation and signed attestation as the final build stage.
  - **success:** image builds reproducibly with zero external CDN access; CycloneDX (primary) + SPDX (secondary) SBOM plus a cosign attestation ship with every build (AD-21); the `presenton-memory` pixi feature + `values.memory.enabled` (default `false`) are wired end to end (AD-23).
- **CAP-12**
  - **intent:** The image deploys via a standard Helm chart on OpenShift with Restricted-SCC-compatible defaults, ships a versioned `/metrics` schema artifact, and gives day-0/day-2 operators preflight, smoke, credential-rotation, and mark-broken-response fixtures.
  - **success:** AD-24's `restricted-v2` defaults hold (capabilities dropped, `seccompProfile: runtime/default`, no privilege escalation, non-root arbitrary UID, no hardcoded UID/GID); `AC-FX-INSTALL-*` and `AC-FX-DAY2-01..03` pass; the `/metrics` schema is versioned and shipped with the chart.
- **CAP-13**
  - **intent:** Recipe-maintainers get a weekly, non-build-blocking drift-detection harness comparing current upstream Presenton against the captured Fixture Set 1 baseline, filing an auto-issue on breaking drift, in a CI workflow whose network egress is strictly separated from the air-gapped build pipeline.
  - **success:** `AC-FX-MAINT-01..03` and `AC-FX-DRIFT-01..04` all pass; the online-capture workflow never shares a runner or environment with the air-gapped build workflow, enforced at the network-policy level (AD-22), not by convention.

### Presenton Constraints

- **AD-17 build routing:** every channel/package resolution in the build pipeline routes through the `*_BASE_URL` env-var family; no recipe, build step, or CI job hardcodes a public URL; `pixitainer` only consumes the pixi-locked environment, never fetches externally itself.
- **AD-18 one true port:** the LLM provider is the *only* swappable seam. Presenton and the Helm chart set only `CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY` (plus optional `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL` passthrough) to select a tier; no tier-specific code path may creep into the app.
- **AD-19 recipe/image boundary:** the image-assembly layer consumes published, versioned conda artifacts by name and pin only — it never vendors or patches recipe internals. `recipe.yaml` content itself is out of this Spec's scope, governed by `conda-forge-expert` per CLAUDE.md Rules 1 and 2.
- **AD-21 single provenance pass:** exactly one `syft`+`cosign` step per image build (post-`pixitainer`, pre-registry-push), producing CycloneDX (primary) + SPDX (secondary) in one deterministic pass — never two disagreeing SBOMs for the same image tag.
- **AD-22 phase-boundary enforcement:** the online-capture/drift CI workflow and the air-gapped build workflow never share a runner or environment; the air-gapped pipeline has zero network egress, enforced at the CI-runner/network-policy level, not by convention.
- **AD-24 SCC target:** Helm SecurityContext defaults to `restricted-v2` compatibility on every target cluster — all capabilities dropped, `seccompProfile: runtime/default`, `allowPrivilegeEscalation: false`, non-root arbitrary UID via the GID-0/`chmod g=u` convention, no hardcoded UID/GID anywhere; `restricted-v3` (`hostUsers: false`) is asserted but not separately branch-tested until the AD-20 Chromium-sandbox spike runs.
- **Hard, no-regression constraints:** zero LibreOffice in the runtime, zero non-conda-forge packages in the runtime, zero non-pixi build steps, zero external CDN access at build or runtime.
- **Phase 0 gates v1 build kickoff (6 exit criteria):** exit 1 (build-complete-hold: GGUF model+quant chosen, bench methodology, source-pathway with alt-source clause) is the critical-path long-pole gating exits 2–3; exits 4/5/6 are independent. Exit 6 (Microsoft disconnected-stack check + memory-subsystem scope decision) is the highest-urgency independent exit because it bears on whether the core differentiator still holds and changes the confirmed recipe count (5 vs 7) — **unresolved, see Open Questions.**

### Presenton Non-goals

- `template-style-extractor` — dropped entirely; upstream Presenton already ships LibreOffice-free template import (stdlib `zipfile`+`ElementTree`, native ODF, `pdfplumber` MIT for PDF) with the identical legacy-format rejection this project had independently proposed (Decisions Log Q2, superseded).
- The end web UI of upstream Presenton — out of scope; upstream owns the React/Next.js UI entirely.
- A full JetBrains plugin — v1 ships a docs-only one-pager (REST + OpenAPI + Postman collection); the full plugin is a Growth-tier item.
- Upstreaming `chromium` directly to conda-forge — still stalled at staged-recipes#21431 with no 2026 movement; v1 vendors `chrome-headless-shell` via `playwright-with-chromium` instead; direct upstreaming is Vision-tier.
- An SVG→DrawingML fidelity tier — net-new conda-forge work with no existing library; Vision-tier, not v1/Growth.
- Knowledge-base integration beyond prompt + uploaded files — explicitly held against customer pressure as a v1 boundary (Landing Condition 4); decks whose source material doesn't fit in prompt+files stay out of scope until Vision tier.

### Presenton Success signal

A two-gate JTBD that must both hold, because either collapsing kills the product on its own axis. **Buyer-gate** (binary, procurement-visible): all confirmed recipes upstream-merged on conda-forge → landed on the customer's JFrog Artifactory mirror → OCI image on the customer's registry, with SBOM (CycloneDX+SPDX) + a signed-image (cosign) attestation + a versioned `/metrics` schema shipped with every build. **User-gate** (behavioral, renewal-driving): one pilot customer clears a three-signatory acceptance checklist (CISO/platform-owner + named end-user lead + backup-signatory continuity clause) within 12 weeks of go-live (18 with the one-time extension) — requiring `AC-PILOT-001` (≥60% of piloted decks show "edit-not-rewrite" behavior), ≤30 min P95 prompt-to-first-slide-renderable, and ≤10s P95 per-refinement latency on Tier-1. Missing either gate within its window returns the program to Phase 0 scoping rather than limping forward.

### Presenton Assumptions

- Q1 (editable-PPTX fidelity bar) is locked at image-overlay + extracted-text-shapes, matching upstream `convert-linux-x64` behavior — not native chart objects or theme/master editability.
- Q3 (LLM provider strategy) is locked: `llmai`'s existing `CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY` contract covers all three production tiers plus the `copilot-bridge` dev path without any Presenton source patch.
- Q4 (air-gap definition) is locked at full air-gap: build CI runs inside the perimeter against an internal JFrog Artifactory mirror; every dependency must be allowlisted on the mirror or the build fails.
- The reference LLM class for cost/latency targets, the Tier-2 default GGUF model+quantization, and the exact repo landing path for the build/Helm artifacts are all deferred to Phase 0 / architecture-spike resolution and do not change this Spec's shape.

### Presenton Open Questions

- **Phase-0 exit 6(a), Redmond-contingency check:** does Microsoft's disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, GA worldwide 2026-02-24) already include, or roadmap, a Copilot-for-PowerPoint-equivalent deck-generation capability? Unconfirmed — directly determines whether Risk R3 (existential, JTBD-collapsing) is materialized, partially materialized, or infrastructure-only. Must resolve before further v1 build investment.
- **Phase-0 exit 6(b), memory-subsystem scope:** does `mem0ai` + `fastembed-vectorstore` (unconditional Presenton dependencies, neither on conda-forge) become two additional v1 recipes (5→7 total), or is the memory/chat-history subsystem documented as dropped for v1? Architecture (AD-23) pre-wires both branches, but the no-op-without-a-Presenton-source-patch path is not yet verified — if a patch is required, the maintenance-burden model changes.
- **`psycopg` license flag (Risk R7 replacement):** LGPL-3.0-only, a different obligation class than the Apache/MIT-dominated rest of the stack — flagged for buyer legal/compliance review alongside the JFrog allowlist gap analysis (Phase 0 exit 4); likely-but-not-confirmed acceptable.
