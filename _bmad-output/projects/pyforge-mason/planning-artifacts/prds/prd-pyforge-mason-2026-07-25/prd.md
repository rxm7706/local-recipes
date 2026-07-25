---
title: Mason (pyforge-mason)
status: final
created: 2026-07-25
updated: 2026-07-25
project: pyforge-mason
dream: docs/dreams/packaging-factory.md
adopted_kernel: _bmad-output/projects/local-recipes/planning-artifacts/specs/spec-packaging-factory/SPEC.md
inputs:
  - ../../briefs/brief-pyforge-mason-2026-07-25/brief.md
  - ../../briefs/brief-pyforge-mason-2026-07-25/addendum.md
  - ../../research/domain-packaging-automation-tooling-research-2026-07-25.md
  - ../../research/technical-mason-cli-seam-research-2026-07-25.md
frCount: 50
nfrCount: 16
decisionCount: 13
revision: 2
revisionNote: "r2 applied the adversarial-review findings — see review-adversarial.md. Added FR-47..FR-50 and D-10..D-13; resolved the FR-45/Rule-2 contradiction, the missing ship verb, the UJ-1/D-2 scope conflict, and the FR-23/FR-44 and FR-46/NFR-13 contradictions."
---

# PRD: Mason

**dist** `pyforge-mason` · **module** `pyforge.mason` · **CLI** `mason`

## 0. Document Purpose

This PRD is for the architect and the epic/story authors who will build Mason, and for any
reviewer auditing why Mason is shaped the way it is. It is structured Glossary-first, with
features grouped and functional requirements nested and globally numbered (FR-1 … FR-46).

It builds on, and does not duplicate: the product brief and its addendum
(`../../briefs/brief-pyforge-mason-2026-07-25/`), the two research reports
(`../../research/`), and the adopted brownfield kernel
`spec-packaging-factory/SPEC.md`, which governs the existing conda-forge-expert surface Mason
delegates to.

**§10 is the load-bearing section.** It records D-1, the wrap-vs-build decision this PRD exists to
resolve, plus eight subsidiary decisions. Downstream work that contradicts a D-record is a defect,
not a preference.

## 1. Vision

Mason turns this repository's proven packaging capability into an installable product. That
capability is real — a 9-step recipe lifecycle across 769 maintained feedstocks, 106 accumulated
gotchas, 10 hard constraints, 46 MCP tools, 1,186 tests — and it is trapped inside a Claude Code
session in one repository. Mason gives it a product face and adds the half it never had.

Three verb families: `mason recipe` runs the lifecycle; `mason package` builds a library and ships
it to PyPI **and** conda-forge in one motion; `mason environment` resolves mixed conda+pip
dependency sets into one lockfile.

The middle verb is the one nobody offers. Hatch and maturin are structurally conda-unaware.
`pixi publish` targets conda channels and its documentation is silent on PyPI. conda-smithy and the
conda-forge autotick-bot are, by their own documentation, non-redeployable outside conda-forge's
infrastructure. Every serious Python library needs both ecosystems and no single tool spans them —
an unowned seam between two toolchains, not a missing feature in one product.

## 2. Target User

### 2.1 Jobs To Be Done

- **Ship a release once, not twice.** Build and publish a library to both ecosystems without
  switching toolchains, metadata formats, and dependency namespaces halfway through.
- **Run maintenance automation I control.** Get autotick-class behaviour against my channel, my
  fork, my mirror — not only against conda-forge's infrastructure.
- **Not re-learn packaging every time.** Have the accumulated judgement (why a `source.url` must
  use the `pypi.org/packages/...` pattern; why a `build.bat` must `call` every `.cmd` shim) applied
  for me rather than rediscovered.
- **Package on behalf of a human, as an agent.** Call a legible verb surface and get actionable
  errors rather than tracebacks.
- **Stop being the only person who can run the factory.** (The builder's own job: distribution is
  currently zero.)

### 2.2 Non-Users (v1)

- **conda-forge core infrastructure.** The autotick-bot is the incumbent there and Mason would be
  redundant. Mason serves the maintainer, not the institution.
- **Someone with no conda involvement at all.** Hatch already serves them completely.
- **Someone in a repository with no discoverable CFE installation** — see D-2; this is a v1
  boundary, not a permanent one.

### 2.3 Key User Journeys

Developer-product scope dial: lighter form, one to three beats each.

- **UJ-1. Dana ships release 2.1 of her library to both ecosystems.**
  Dana maintains a mid-sized analytics library used by both pip and conda users. Her recipe lives in
  a CFE-co-located packaging repo (D-2, D-10). She tags 2.1, runs
  `mason package ship --target library --to pypi,conda-forge --dry-run`, reads the plan, and re-runs
  it for real. The wheel is on PyPI in under a minute. The conda half returns a **PR reference** — a
  staged-recipes pull request is open and queued for human review. Dana knows the difference because
  Mason told her plainly, in the same output, rather than reporting a uniform "success."
  **Boundary (D-10):** from a project with no CFE root and no `recipes/<name>/` source directory,
  the `pypi` half of this journey works and the `conda-forge` half does not. Mason says so rather
  than failing obscurely.

- **UJ-2. Rae adds a package to conda-forge without knowing conda-forge.**
  Rae has never written a recipe. `mason recipe new --from-pypi some-lib` produces a v1
  `recipe.yaml`; `mason recipe build` builds it natively; the build fails; `mason recipe diagnose`
  names the cause and the fix. Rae never reads a gotcha list — the gotchas are applied on her behalf
  by the machinery Mason delegates to.

- **UJ-3. Kim runs the loop behind a corporate proxy.**
  Kim's employer routes everything through JFrog Artifactory and blocks direct PyPI. Kim sets the
  enterprise environment variables the existing HTTP layer already honours and runs the same
  commands. Nothing forks; nothing special-cases. **Edge case:** if the CFE machinery is not
  discoverable, `mason recipe` fails with a message naming the four-step resolution chain, while
  `mason package` and `mason environment` keep working.

- **UJ-4. An agent packages on request.**
  A model is asked to "get this library onto conda-forge." It calls Mason's verbs, receives
  structured JSON, and reports the PR link. No screen-scraping of human-formatted output.

## 3. Glossary

Downstream artifacts use these terms verbatim. Synonyms are a discipline violation.

- **CFE** — the `conda-forge-expert` skill: its canonical scripts
  (`.claude/skills/conda-forge-expert/scripts/`), its public wrapper tier
  (`.claude/scripts/conda-forge-expert/`), and its MCP server
  (`.claude/tools/conda_forge_server.py`). Governed by `spec-packaging-factory`. Authoritative over
  Mason on all recipe semantics (CLAUDE.md Rule 1).
- **CFE root** — the filesystem directory containing `.claude/scripts/conda-forge-expert/`. What the
  resolution chain (FR-2) locates.
- **The adapter** — `pyforge.mason.cfe`, the single module permitted to invoke CFE. Everything else
  in Mason reaches CFE through it or not at all.
- **Recipe knowledge** — packaging judgement specific to conda-forge: gotchas, constraints, pin
  rules, policy constants, format semantics. Owned by CFE. **Never** present in `pyforge.mason`.
- **Ship target** — a named destination for a built artifact. Exactly three exist in v1: `pypi`,
  `conda-forge`, `channel:<name>` (D-3).
- **Synchronous target** — a ship target that reaches a terminal state within the command's
  lifetime (`pypi`, `channel:<name>`).
- **Asynchronous target** — a ship target whose command completion means *initiated*, not *done*
  (`conda-forge`, which opens a pull request into a human review queue).
- **Ship receipt** — the structured record a ship operation returns: per-target status, terminal or
  pending, and a reference (URL, PR number, channel path).
- **Engine** — an external tool Mason orchestrates and never reimplements: `rattler-build`,
  `grayskull`, `build`, `twine`, `conda-lock`, `pixi`.
- **Workspace member** — a package under `src/shared/packages/` wired into the root `pixi.toml` by
  a path dependency, per the `pyforge-warden` / `pyforge-atlas` convention.
- **Degradation** — the defined behaviour when the CFE root cannot be resolved: a structured,
  actionable error for CFE-dependent commands and unaffected operation for the rest.

## 4. Features

### 4.1 The CFE seam

**Description.** One module, `pyforge.mason.cfe`, is the entire boundary between Mason and CFE.
It locates the CFE root, selects an interpreter, invokes canonical scripts as subprocesses, parses
their output, and raises typed errors. No other module in `pyforge.mason` may import `subprocess`
against a CFE path or hold a CFE script name. This is the mechanism that makes D-1 enforceable
rather than aspirational.

Subprocess is not a compromise: it is the contract every existing consumer already uses — 57 CLI
wrappers, ~105 pixi tasks, and 46 MCP tools all invoke canonical scripts as
`[sys.executable, <script>, *args]`, and `conda_forge_server.py` imports zero canonical scripts.

**Functional Requirements:**

#### FR-1: Single delegation point

Mason invokes CFE only through `pyforge.mason.cfe`. Realizes UJ-2, UJ-3.

**Consequences (testable):**
- A static check over `pyforge/mason/` finds no CFE script path or filename outside the adapter.
- Every `mason recipe` subcommand's call graph reaches CFE through exactly one adapter function.

#### FR-2: CFE root resolution chain

Mason resolves the CFE root through an ordered chain, first match wins.

**Consequences (testable):**
1. `--cfe-root <path>` (explicit flag).
2. `MASON_CFE_ROOT` environment variable.
3. Upward walk from the current working directory for a directory containing
   `.claude/scripts/conda-forge-expert/`.
4. No match → degradation (FR-5), never a traceback.
- Each step is independently unit-testable with a synthetic filesystem.
- The resolved root and the step that produced it are reported by `mason doctor` (FR-34).

#### FR-3: Interpreter selection

Mason selects the interpreter used to run CFE scripts.

**Consequences (testable):**
- Order: `--cfe-python <path>` → `MASON_CFE_PYTHON` → `sys.executable`.
- CFE's import floor (`pyyaml`, `requests`, `packaging`, `truststore`, `ruamel.yaml`,
  `conda-forge-metadata`) is probed before first use; a missing floor produces a named error, not an
  `ImportError` traceback from a subprocess.

**Rationale:** `sys.executable` is correct inside a fat pixi environment and wrong inside a lean
`no-default-feature` one. See D-7.

#### FR-4: Typed invocation result

Every CFE invocation returns a structured result.

**Consequences (testable):**
- The result carries return code, stdout, stderr, and a parsed JSON body when one is present.
- A timeout is applied to every invocation; expiry produces a distinct timeout error and leaves no
  orphaned process.
- The timeout is configured by `--cfe-timeout` → `MASON_CFE_TIMEOUT` → a per-operation default
  (D-13 — there is no configuration file, so every knob is a flag plus an environment variable).
- Long-running operations (`recipe build`) stream child stderr through to the user's stderr rather
  than buffering it to completion; short JSON-returning operations capture stdout (FR-49).
- Output parsing tolerates a leading non-JSON progress line before the JSON body.

**Rationale on the last point:** the existing MCP server carries `_extract_json_from_stdout()` for
exactly this, needed today by `submit_pr` and `prepare_submission_branch`. Mason inherits the
problem and must port the behaviour — not import the shim (it lives in a governed surface).

#### FR-5: Degradation

Mason behaves predictably when the CFE root is unresolvable.

**Consequences (testable):**
- `mason recipe *` exits non-zero with a message naming all four resolution steps and how to satisfy
  each.
- `mason package *` and `mason environment *` run **unaffected**, verified by a test executing them
  with the CFE root guaranteed absent.
- No command emits a Python traceback for this condition.

#### FR-6: Credential isolation

Mason does not read, hold, or forward CFE's credential environment.

**Consequences (testable):**
- Mason's own code reads no `JFROG_*` variable. Credentials reach CFE through the inherited process
  environment only.
- Mason logs no environment-variable *values* at any verbosity.

**Rationale:** CFE's `_http.py` is known to attach `JFROG_API_KEY` to outbound requests
unconditionally. Process isolation confines that behaviour to CFE's process rather than extending it
to every HTTP call Mason makes.

---

### 4.2 `mason recipe` — the lifecycle

**Description.** The product face of CFE's lifecycle loop. Every subcommand is porcelain: it maps
arguments to a CFE invocation and renders the result. Mason contributes verb design, argument
ergonomics, output formatting, and error messages. Mason contributes **zero** recipe knowledge —
no gotcha, no constraint, no pin rule, no policy constant. Realizes UJ-2, UJ-3.

**Functional Requirements:**

#### FR-7: `mason recipe new`

A user generates a recipe from an upstream source.

**Consequences (testable):**
- `--from-pypi`, `--from-github`, `--from-cran`, `--from-npm` map to the corresponding CFE
  generators.
- Output is a v1 `recipe.yaml` at a user-specified path.
- Generation semantics come entirely from CFE; Mason asserts no field defaults of its own.

#### FR-8: `mason recipe validate`

A user validates a recipe against conda-forge policy.

**Consequences (testable):**
- Non-zero exit when CFE reports any validation failure.
- Findings are rendered with CFE's identifiers preserved verbatim — never renumbered or reworded.

#### FR-9: `mason recipe build`

A user builds a recipe on the host platform. Realizes UJ-2.

**Consequences (testable):**
- Native build is the default.
- A Docker / CI-parity build is available behind an explicit flag and is never implicit. It
  delegates to CFE's Docker entry point, **not** to `local_builder.py`, which is Docker-less.
  `[NOTE FOR PM]` If that entry point turns out not to be adapter-reachable, drop the Docker bullet
  — it is the one part of FR-9 with no confirmed wrappable target (OQ-8).
- Build output location and exit status are reported in both human and JSON forms.
- Child build output streams to stderr as it is produced (FR-49); the user is not left with a silent
  terminal for the duration of a multi-minute build.

#### FR-10: `mason recipe diagnose`

A user gets a cause and a proposed fix for a failed build. Realizes UJ-2.

**Consequences (testable):**
- Delegates to CFE's failure analyzer.
- When CFE returns no diagnosis, Mason says so plainly rather than inventing one.

#### FR-11: `mason recipe optimize`

A user gets recipe-quality findings.

**Consequences (testable):**
- CFE check codes are preserved verbatim in output.

#### FR-12: `mason recipe scan`

A user gets a vulnerability scan of a recipe's dependency set.

**Consequences (testable):**
- Delegates to CFE. Mason applies no severity policy of its own.

#### FR-13: `mason recipe submit`

A user opens a staged-recipes pull request. Realizes UJ-1.

**Consequences (testable):**
- `--dry-run` is the default; a real submission requires an explicit confirming flag.
- Returns a **ship receipt** (Glossary) with the PR reference on success.
- The two-phase CFE flow (prepare branch, then open PR) is preserved and separately addressable.

#### FR-14: `mason recipe update`

A user updates an existing recipe to a newer upstream version.

**Consequences (testable):**
- Diff-before-apply: the change is shown before it is written.
- `--dry-run` supported on every source type.

**Notes:** The v1 subcommand set is the intersection of CFE capability and product coherence, not
the full 46-tool surface. Verbs not listed remain reachable through existing pixi tasks (D-4).

---

### 4.3 `mason package` — the dual-ship motion

**Description.** The product's differentiator and its largest net-new build. There is **no wheel
build, no PyPI upload, and no publish orchestration anywhere in CFE's 41,410 LOC** — this feature
wraps nothing and must be written. It orchestrates engines (`build`, `twine`, `pixi build`) and
owns the reporting contract for a fundamentally asymmetric operation. Realizes UJ-1, UJ-4.

**Functional Requirements:**

#### FR-15: `mason package build`

A user builds distributable artifacts from a project.

**Consequences (testable):**
- Produces a wheel and an sdist via PEP-517 (`python -m build`), and a `.conda` via `pixi build`.
- Artifact paths are reported; nothing is uploaded.
- Runs with the CFE root absent (FR-5).

#### FR-16: `mason package ship` and the target vocabulary

A user ships built artifacts to one or more targets. **This is the verb that ships** — FR-15's
`build` explicitly uploads nothing, so shipping needs its own verb under FR-30's noun-verb rule.
Realizes UJ-1, SM-1.

**Consequences (testable):**
- The canonical form is `mason package ship --to <targets>`.
- `mason package --ship <targets>` is accepted as a documented alias, so the crew charter's cadence
  (`mason package --target library --ship pypi,conda-forge`) works verbatim. The alias is the sole
  exception to FR-30's "bare noun exits non-zero" rule and is tested as such.
- `--to` accepts exactly four target forms:
  - `pypi` — synchronous upload.
  - `pypi-test` — synchronous upload to TestPyPI (SM-1's rehearsal target; see FR-50).
  - `conda-forge` — asynchronous; opens a staged-recipes pull request.
  - `channel:<name>` — synchronous upload to a named conda channel.
- Any other value is rejected with the valid set listed.
- Multiple targets are comma-separated and each is honoured independently.
- `ship` builds first if artifacts are absent, reusing FR-15's implementation rather than duplicating
  it.

#### FR-17: Asymmetric ship reporting

A ship operation reports each target's true terminal state. Realizes UJ-1.

**Consequences (testable):**
- Every target in the receipt carries an explicit `terminal` or `pending` state.
- A run where `pypi` succeeded and `conda-forge` opened a PR reports **success + pending**, never a
  uniform success.
- Exit code reflects the aggregate: any target that failed to *initiate* is a failure; a target that
  initiated but is pending is not.

**Rationale:** PyPI completes in seconds; conda-forge completes in days behind a human review queue.
Reporting "success" for a queued PR is a correctness bug. See D-3.

#### FR-18: Partial-failure semantics

A multi-target ship handles per-target failure without corrupting the others.

**Consequences (testable):**
- One target's failure does not prevent the others from being attempted.
- The receipt distinguishes not-attempted, failed, pending, and terminal.
- Retrying is safe: an already-terminal target is skipped, not re-uploaded.
- **Cross-invocation idempotence is achieved by interrogating the target, not by persisting state**
  (D-11): `pypi` / `pypi-test` by querying the index for the version; `channel:<name>` by querying
  the channel; `conda-forge` by searching the fork for an open pull request on the deterministic
  `add-recipe-<name>` branch CFE's submission flow produces.
- A second `ship --to conda-forge` for an already-open PR reports `pending` with the existing PR
  reference and opens **no** second pull request. This case is explicitly tested.
- A target that cannot be interrogated yields `pending` with the reason stated — never an assumption
  in either direction.

#### FR-19: Dry-run by default for shipping

Shipping requires explicit intent.

**Consequences (testable):**
- `--ship` without a confirming flag plans and prints, and uploads nothing.
- The dry-run plan names every target, artifact, and destination.

#### FR-20: Credential handling

Mason obtains upload credentials from the environment.

**Consequences (testable):**
- PyPI credentials are read from the standard environment variables the chosen uploader honours.
- No credential is ever written to disk, logged, or included in a ship receipt.
- A missing credential is detected **before** any artifact is built or uploaded.

#### FR-21: `--target` project shapes

`--target` declares what kind of thing is being packaged.

**Consequences (testable):**
- `library` is supported in v1 and is the default.
- Other values are rejected with a message naming `library` as the v1 set.

**Out of Scope:** application and binary targets (v2).

#### FR-22: Version consistency check

Mason refuses to ship artifacts whose versions disagree.

**Consequences (testable):**
- The wheel version and the conda package version are compared before any upload; a mismatch aborts
  with both values shown.

#### FR-23: Recipe sourcing for `conda-forge` shipping

Shipping to `conda-forge` requires a recipe **and** a CFE-co-located repository. Realizes UJ-1's
conda half, within the D-10 boundary.

**Consequences (testable):**
- If a recipe path is given, it is used. If not, Mason offers to generate one via FR-7 and does not
  generate silently.
- **This is the sole exception to FR-44.** It is the one target in `mason package` that requires the
  CFE root, and it additionally requires the recipe to sit where CFE's submission flow expects it —
  `<cfe-root>/recipes/<name>/`. CFE's `submit_pr.py` reads from that path and writes into a
  staged-recipes fork clone; Mason may not change either behaviour (AD-15).
- When either precondition is unmet, the `conda-forge` target alone fails with a message naming the
  precondition, and every other target in the same invocation completes normally.
- The preconditions are checked and reported by `mason doctor` (FR-34), so a user learns the boundary
  before attempting a release rather than during one.

**Out of Scope:** shipping to conda-forge from a project with no CFE root and no `recipes/<name>/`
source directory. See D-10 — this is the honest v1 boundary, not a hidden failure.

#### FR-24: Self-hosting

Mason can ship Mason.

**Consequences (testable):**
- `mason package build` against `src/shared/packages/pyforge-mason/` produces the same artifacts the
  repository's existing hand-run `pyforge-mason-build` triad produces.
- `mason package ship --to pypi-test` publishes `pyforge-mason` to TestPyPI **first**. Only after
  that rehearsal passes does `--to pypi` run (FR-50).
- This is SM-1, the primary success metric.

**Note:** what the repository dogfoods today is the dual-artifact **build**, not the ship — neither
sibling package has a publish or upload task. FR-24 is therefore a genuine first, which is exactly
why FR-50's rehearsal exists.

---

### 4.4 `mason environment` — dependency binding

**Description.** Deliberately the thinnest feature. conda-lock already spans conda and pip via a
vendored Poetry solver and is actively maintained; `pixi.lock` already exists. Mason orchestrates and
applies policy. Mason does not solve. Scope inflation into re-solving is a stated non-goal.

**Functional Requirements:**

#### FR-25: `mason environment lock`

A user produces a lockfile from a project's dependency manifests.

**Consequences (testable):**
- Delegates solving to an engine (`conda-lock` or `pixi`); Mason implements no resolution logic.
- `--output <path>` controls the destination.
- Runs with the CFE root absent (FR-5).

#### FR-26: Manifest discovery

Mason locates the manifests to feed the engine.

**Consequences (testable):**
- Discovers `pyproject.toml`, `environment.yml`, `requirements*.txt`, `pixi.toml`.
- Discovered manifests are listed before solving; explicit paths override discovery.

#### FR-27: Platform targeting

A user controls which platforms the lock covers.

**Consequences (testable):**
- `--platform` is repeatable; absent, the engine's default applies and is reported.

#### FR-28: Lock verification

A user checks whether an existing lockfile is current.

**Consequences (testable):**
- `mason environment check` exits non-zero when the lockfile is stale relative to its manifests.
- Suitable for CI use; emits JSON under `--format json`.

#### FR-29: Engine reporting

Mason names the engine that produced a lock.

**Consequences (testable):**
- Engine name and version appear in output and in the lockfile's provenance where the format allows.

---

### 4.5 CLI shell and output contract

**Description.** The public surface. `mason <noun> <verb>` throughout — the crew charter's cadence.
argparse, matching `pyforge.warden.cli` and all 60 CFE scripts; adding click or typer would violate
the workspace's lean-dependency doctrine for ergonomics alone.

**Functional Requirements:**

#### FR-30: Noun-verb command structure

**Consequences (testable):**
- Three nouns in v1: `recipe`, `package`, `environment`, plus top-level `doctor` and `--version`.
- `mason <noun>` with no verb prints that noun's verbs and exits non-zero.
- **One documented exception:** `mason package --ship <targets>` (FR-16's charter alias) is valid
  without a verb and dispatches to `mason package ship`. It is the only bare-noun form that runs, and
  a test asserts no other exists.

#### FR-31: Dual output format

Realizes UJ-4.

**Consequences (testable):**
- `--format text` (default) and `--format json` on every command.
- Under `--format json`, stdout carries exactly one JSON document or nothing; every diagnostic goes
  to stderr.

**Rationale:** the stream-discipline rule proven in `pyforge.warden.cli`.

#### FR-32: Exit-code contract

**Consequences (testable):**
- `0` success; `1` operation failed; `2` usage error; `3` CFE unavailable for a CFE-dependent
  command; `130` interrupted.
- Exit codes originate from one module; no command computes its own.

#### FR-33: Structured errors

**Consequences (testable):**
- Every anticipated failure produces a typed error with a stable identifier and an actionable
  message.
- No anticipated failure surfaces as a raw traceback; unanticipated ones exit `1` with the traceback
  on stderr.

#### FR-34: `mason doctor`

A user diagnoses their own installation. Realizes UJ-3.

**Consequences (testable):**
- Reports: Mason version; CFE root and which resolution step found it; selected interpreter and
  whether the CFE import floor is satisfied; each engine's presence and version.
- Exits `0` when Mason is usable for the non-CFE verbs, even if CFE is missing — reporting the gap
  rather than failing.

#### FR-35: Global flags

**Consequences (testable):**
- `--cfe-root`, `--cfe-python`, `--format`, `--verbose`, `--quiet` accepted on every command.
- No global flag is required for any command to run.

---

### 4.6 Distribution

**Description.** Mason ships the way its siblings ship. The conventions are settled by two prior
instances and are adopted wholesale rather than reconsidered.

**Functional Requirements:**

#### FR-36: Workspace member layout

**Consequences (testable):**
- Lives at `src/shared/packages/pyforge-mason/`.
- Member `pixi.toml` has a `[package]` table and **no** `[workspace]` table.
- `src/pyforge/mason/` is a PEP-420 namespace package; no `src/pyforge/__init__.py` exists.

#### FR-37: Dual-artifact build

**Consequences (testable):**
- One `pyproject.toml` (hatchling) drives both artifacts.
- `pyforge-mason-build-conda` produces a `.conda` via `pixi-build-python`.
- `pyforge-mason-build-dist` produces wheel + sdist via `python -m build --no-isolation`.
- `pyforge-mason-build` depends on both.

#### FR-38: Console entry point

**Consequences (testable):**
- `[project.scripts] mason = "pyforge.mason.cli:main"`.
- `mason --version` reports the installed distribution version.

#### FR-39: Root workspace wiring

**Consequences (testable):**
- `[feature.pyforge-mason.dependencies]` carries a path dependency to the member.
- A `pyforge-mason` environment exists with `no-default-feature = true`.

#### FR-40: Engine provisioning

**Consequences (testable):**
- Engines are conda run-dependencies in the member `pixi.toml`; nothing is fetched at runtime.
- Engine version ranges in `pixi.toml` are mirrored by in-code constants, and a meta-test enforces
  the two stay in sync.

**Rationale:** ported from `pyforge-warden`'s `tests/meta/test_engine_version_range_sync.py`.

#### FR-41: Lean dependency set

**Consequences (testable):**
- Wheel `dependencies` contain only what `pyforge.mason` imports.
- No CLI framework dependency; `argparse` is stdlib.
- Any dependency on a sibling package is an optional extra, never a hard dependency.

---

### 4.7 Seam enforcement

**Description.** D-1 is worthless if nothing enforces it. This repository has already demonstrated
the failure mode being guarded against: `pyforge-atlas` rebuilt its capability as ~29,000 lines, and
the 8,902-line original is still what runs in production. Intent did not prevent it. These
requirements are the mechanism that does.

**Functional Requirements:**

#### FR-42: No recipe knowledge in Mason

**Consequences (testable):**
- A meta-test asserts `pyforge/mason/` contains no CFE gotcha identifier, no conda-forge policy
  constant, no pin table, and no recipe-format field defaults.
- The test fails on introduction of any such constant. **This is the single most valuable test in
  the product.**
- **The decision procedure is enumerated, not left to judgement.** The deny-list is declared in one
  reviewable module and must include, at minimum: the gotcha-identifier pattern (`G` followed by
  1–3 digits, matched as a word); conda-forge policy nouns and check-code prefixes drawn from CFE's
  own reference material; recipe-format field names from the v1 schema; and known pin/constraint
  string shapes. Each entry cites the CFE artifact it derives from.
- **The test proves itself.** It ships with positive fixtures — synthetic modules containing a
  planted violation of each deny-list category — and fails if any planted violation goes undetected.
  A deny-list that matches nothing is a failing test, not a passing one.
- Weakening or removing a deny-list entry requires an accompanying rationale comment; a
  companion test asserts every entry carries one.

#### FR-43: Adapter is the sole CFE caller

**Consequences (testable):**
- A meta-test asserts no module outside `pyforge/mason/cfe.py` references a CFE path or script name.

#### FR-44: Non-CFE verbs are independent

**Consequences (testable):**
- A meta-test runs every `mason package` and `mason environment` verb with the CFE root guaranteed
  unresolvable and asserts each behaves normally — **with exactly one enumerated exception, the
  `conda-forge` ship target (FR-23).**
- The exception is expressed as a named allow-list of one entry, not as a weakened assertion. Adding
  a second entry requires changing the test, which is the review gate. A blanket "except where CFE is
  needed" formulation is explicitly forbidden — that phrasing is the erosion this FR exists to stop.
- The test asserts positively that the excepted target fails **for the right reason** (the FR-5
  error), not merely that it fails.

#### FR-45: No CFE surface modification by implementation work

**Consequences (testable):**
- The repository's `spec_surface_check` remains green across the whole effort.
- **No implementation commit** touches `.claude/skills/conda-forge-expert/**`,
  `.claude/scripts/conda-forge-expert/**`, or `.claude/tools/conda_forge_server.py`. "Implementation
  commit" means every commit in the effort except the one sanctioned exception below.
- **The sanctioned exception:** the closing Rule-2 retrospective (FR-47) edits exactly those files —
  because CLAUDE.md Rule 2 requires it. That commit is identified by convention (a `retro:` subject
  and a CFE `CHANGELOG.md` entry in the same commit) and is excluded from the check.
- The check asserts the exception is used **once**, by the retrospective, and carries a CHANGELOG
  move — so it cannot be borrowed to sneak an implementation change through.

**Rationale:** an earlier draft of this FR forbade *all* commits to the CFE surface, which directly
contradicted §9 and made the effort impossible to close. Rule 2 is not optional; Mason's constraint
is that it may not edit CFE *while implementing*, and must edit CFE *when retrospecting*.

#### FR-46: Delegation-fidelity test

**Consequences (testable):**
- For a representative recipe operation, Mason's result matches the corresponding direct CFE
  invocation's result — proving Mason transforms presentation, not semantics.
- This test is the **single declared exception to NFR-13**: it requires a real CFE installation. It
  carries the `slow` marker, is excluded from the default test task, and **skips cleanly** (never
  fails) when no CFE root resolves.

#### FR-47: Closing Rule-2 retrospective

The effort closes with a retrospective that improves the skill it wraps.

**Consequences (testable):**
- A retrospective runs at closeout, reviewing this effort against the conda-forge-expert skill.
- Findings land as edits to the skill's files plus a dated `CHANGELOG.md` entry with a one-line
  summary per finding, and the skill version is bumped per semver.
- The CFE defects recorded during planning (13 duplicated `_get_data_dir()` copies, the
  `parents[3/4/5]` repo-root divergence, the two scripts resolving to a divergent data directory,
  the unconditional JFrog header injection) are each surfaced for triage.
- If no novel findings emerge, a CHANGELOG entry still states that existing guidance held, naming
  this effort.
- The effort is not done until this lands. Not optional, not deferrable.

#### FR-48: Configuration surface

Every runtime knob is reachable without a configuration file.

**Consequences (testable):**
- Each knob is exposed as both a flag and an environment variable, resolved
  flag → environment → default (D-13).
- The v1 knob set is enumerated: `--cfe-root`/`MASON_CFE_ROOT`, `--cfe-python`/`MASON_CFE_PYTHON`,
  `--cfe-timeout`/`MASON_CFE_TIMEOUT`, `--format`, `--verbose`, `--quiet`.
- A test asserts every knob has both forms and that no code path reads a Mason-specific key from a
  file.

#### FR-49: Logging and child-output handling

A user can see what a long operation is doing without losing the machine-readable contract.

**Consequences (testable):**
- Logging uses the stdlib `logging` module and writes to stderr only, at every verbosity.
- `--verbose` raises the level; `--quiet` lowers it; neither affects what stdout carries.
- **Delegated operations expected to exceed a few seconds (`recipe build`, `package build`) stream
  child stderr through to the user's stderr as it is produced**; short JSON-returning operations
  capture stdout for parsing.
- Under `--format json`, streamed child output still goes to stderr, so the single-JSON-document
  guarantee on stdout holds during a streaming operation. A test asserts this.
- No log record at any level contains an environment-variable value (NFR-2).

#### FR-50: Rehearsal before an irreversible publish

A user can rehearse a PyPI publish before performing the one-way one.

**Consequences (testable):**
- The `pypi-test` target (FR-16) uploads to TestPyPI using the same code path as `pypi`, differing
  only in repository configuration.
- FR-24's self-hosting sequence runs `pypi-test` and requires it to pass before `pypi` runs.
- A PyPI upload is recognized as irreversible: the dry-run plan (FR-19) states so explicitly for the
  `pypi` target.

---

## 5. Non-Goals (Explicit)

- **Mason will never hold recipe knowledge.** Not a v1 deferral — a permanent property. Gotchas,
  constraints, pins, and conda-forge policy live in CFE and nowhere else.
- **Mason is not a fork of CFE.** No extracted, vendored, or re-implemented copy of the canonical
  scripts, in any version.
- **Mason does not modify the CFE surface.** It is governed by `spec-packaging-factory` and
  authoritative over Mason under CLAUDE.md Rule 1.
- **Mason does not solve dependencies.** It orchestrates solvers.
- **Mason does not replace the existing pixi task surface in v1.** Additive. See D-4.
- **Mason does not ship a second MCP server** duplicating the existing 46 tools. See D-8.
- **Mason is not a build system.** It calls `rattler-build`, `pixi build`, and PEP-517 backends.
- **Mason does not become a general-purpose release manager.** Changelogs, tags, GitHub releases,
  and version bumping are out.

## 6. MVP Scope

### 6.1 In Scope

- The adapter and its resolution chains (FR-1 – FR-6)
- `mason recipe`: new, validate, build, diagnose, optimize, scan, submit, update (FR-7 – FR-14)
- `mason package`: build and ship to `pypi` / `pypi-test` / `conda-forge` / `channel:<name>` with
  asymmetric receipts (FR-15 – FR-24)
- `mason environment`: lock, check (FR-25 – FR-29)
- CLI shell, dual output, exit codes, structured errors, `doctor` (FR-30 – FR-35)
- Distribution as a workspace member with the dual-artifact build (FR-36 – FR-41)
- The enforcement meta-tests and the closing retrospective (FR-42 – FR-47)
- Configuration surface, logging/streaming, and publish rehearsal (FR-48 – FR-50)

### 6.2 Out of Scope for MVP

- **Operation in a repository with no discoverable CFE root** — requires changes to a surface Mason
  may not edit (D-2).
- **Shipping to conda-forge from a project with no `recipes/<name>/` source directory** — CFE's
  submission flow reads from that path and Mason may not change it (D-10). The `pypi`,
  `pypi-test`, and `channel:` targets have no such limit.
- **A Mason MCP server** — deferred; `fastmcp` is already a root dependency, so it costs nothing to
  add later (D-8).
- **OIDC / trusted publishing** — v1 is token-based (D-5).
- **Multi-ecosystem autotick** (CRAN/npm/cargo updaters) — the dream's frontier; ownership between
  Mason and Marshal/Steward is unresolved (OQ-3).
  `[NOTE FOR PM]` This is the most emotionally load-bearing deferral — it is the origin dream's
  headline frontier item. Revisit once the seam is proven.
- **Smart test extractor** and **static dependency-version checker** — dream frontier, v2+.
- **`--target application` / `--target binary`** — v1 is `library` only.
- **Deprecating any pixi task** (D-4).

## 7. Success Metrics

**Primary**

- **SM-1: Mason ships Mason.** `mason package ship --to pypi-test` then `--to pypi` publishes
  `pyforge-mason` itself, and `mason package build` produces the same `.conda` the hand-run build
  triad produces. Target: achieved before v1 is declared done. Validates FR-15 – FR-24, FR-37, FR-50.
  *Until Mason can ship Mason, the dual-ship claim is unproven.*
  **Evidence caveat:** the repository dogfoods the dual-artifact **build** by hand for two sibling
  packages — neither has a publish or upload task. The **ship** half is genuinely new, which is why
  FR-50's TestPyPI rehearsal gates the irreversible upload.

**Secondary**

- **SM-2: Zero recipe knowledge in Mason.** FR-42's meta-test is green at every commit, **and its own
  planted-violation fixtures prove it is not vacuous.** Target: 100%.
- **SM-3: CFE-independence holds.** Every `mason package` / `mason environment` verb passes with the
  CFE root absent, except the single enumerated `conda-forge` ship target (FR-23/FR-44). Target: the
  exception allow-list has exactly one entry. Validates FR-5, FR-44.
- **SM-4: Free inheritance.** A CFE gotcha added after Mason ships changes Mason's behaviour with
  **no change to Mason**. Measured once against a real post-ship CFE MINOR bump. Validates FR-1.
- **SM-5: Distribution parity.** `.conda` + wheel + sdist build green from one `pyproject.toml`.
  Validates FR-36 – FR-39.
- **SM-6: Governance clean.** `spec_surface_check` green; zero **implementation** commits touching the
  CFE surface; exactly one sanctioned retrospective commit that does (FR-45, FR-47). Validates FR-45.
- **SM-7: Rule-2 closed.** A dated CFE `CHANGELOG.md` entry exists naming this effort, with a semver
  bump. Validates FR-47.

**Counter-metrics (do not optimize)**

- **SM-C1: Mason LOC.** Growth is a warning, not an achievement. A `pyforge.mason` approaching
  CFE's scale means D-1 has quietly inverted. Counterbalances SM-1.
- **SM-C2: `mason recipe` verb count.** Wrapping all 46 MCP tools would be surface bloat, not
  product. Coverage is not a goal. Counterbalances SM-2.
- **SM-C3: Adapter surface area.** A growing adapter API means recipe logic is migrating into Mason
  one helper at a time. Counterbalances FR-1.

## 8. Cross-Cutting NFRs

- **NFR-1 (Isolation).** Every CFE invocation is a subprocess with a timeout. A CFE hang must never
  hang Mason. *(CFE has a documented hang history — Phase K — fixed with an in-script watchdog.)*
- **NFR-2 (Credentials).** No credential is logged, persisted, or included in any output.
- **NFR-3 (Determinism).** Identical inputs produce identical JSON output, modulo timestamps and
  explicit provenance fields.
- **NFR-4 (Stream discipline).** Under `--format json`, stdout carries exactly one JSON document or
  nothing.
- **NFR-5 (Offline-safe).** Every command that does not inherently require the network runs offline.
  Network use is never implicit.
- **NFR-6 (Enterprise routing).** Mason imposes no direct-internet assumption; proxy/mirror routing
  is inherited through the process environment.
- **NFR-7 (No runtime fetch).** Engines are provisioned as conda dependencies. Nothing is downloaded
  at runtime.
- **NFR-8 (Idempotence).** Re-running a completed ship does not duplicate an upload.
- **NFR-9 (Safety by default).** Every mutating operation defaults to dry-run.
- **NFR-10 (Lean deps).** A new runtime dependency requires justification against the workspace's
  lean-dependency doctrine.
- **NFR-11 (Python floor).** `requires-python >= 3.12`, matching `pyforge-warden` (D-6).
- **NFR-12 (Platform parity).** Mason's own logic works on linux-64, osx-arm64, win-64. Platform
  limits belong to the engines, not to Mason, and are reported as such.
- **NFR-13 (Test coverage of the seam).** Every adapter code path has a test using a fake CFE root.
  No test requires a real CFE installation, **with one declared exception: FR-46's fidelity test**,
  which is `slow`-marked, excluded from the default task, and skips cleanly when CFE is absent.
- **NFR-14 (Error actionability).** Every structured error names what failed and what to do next.
- **NFR-15 (Backward compatibility).** Post-v1, the CLI surface and JSON schema follow semver; a
  breaking change requires a MAJOR bump.
- **NFR-16 (No untrusted execution).** Mason never renders Jinja or executes recipe content itself;
  all such handling stays inside CFE's process.

## 9. Constraints and Guardrails

**Governance.** CLAUDE.md Rule 1 makes CFE authoritative over any Mason story that conflicts with it.
Rule 2 requires that every conda-forge effort close with a retrospective that edits the CFE skill —
including this one. The CFE surface is governed by `spec-packaging-factory` with a CHANGELOG sentinel;
`scripts/spec_surface_check.py` and `tests/meta/test_spec_surface_check.py` enforce it. **Mason cannot
edit CFE, and CFE will keep changing underneath Mason.** Both facts point the same direction: delegate.

**Preview dependency.** `pixi build` is preview software (`preview = ["pixi-build"]`), as are its
member-package semantics. Both sibling packages already accept this exposure.

**Stdout contract risk.** CFE script stdout is a de-facto contract, not a formal one. 46 MCP tools
have relied on it successfully, with one known tolerance shim. Mason inherits this risk; FR-4 and
FR-46 bound it.

**Upstream defects noted, not owned.** CFE's duplicated `_get_data_dir()` (13 copies), inconsistent
`parents[3/4/5]` repo-root anchors, two scripts resolving to a divergent data directory, and the
unconditional JFrog header injection are genuine findings. They belong to a CFE Rule-2 retrospective,
not a Mason story. Recorded so they are not lost.

## 10. Decision Record

The section this PRD exists to produce. Downstream work contradicting a D-record is a defect.

### D-1 — Wrap-vs-build: **seam by capability** *(the central decision)*

**Decision.** Mason **wraps** CFE by subprocess for all recipe operations and **builds** natively
for `mason package` and `mason environment`. The boundary is drawn by capability, not by product.

**The three options considered.**

| | **A — pure porcelain** | **B — extract/re-implement** | **C — seam by capability** ✅ |
|---|---|---|---|
| Size | Small | ~41,410 LOC re-earned | Small wrap + focused build |
| Recipe knowledge | Zero duplicated | Forked, then drifts | Zero duplicated |
| Rule 1 / Rule 2 | Compliant by construction | Structurally adversarial | Compliant by construction |
| Distribution | Inert without CFE | Genuinely standalone | Works without CFE for 2 of 3 verb families |
| Delivers `--ship pypi` | **No** | Yes | Yes |
| Delivers `environment lock` | **No** | Yes | Yes |

**Why not A.** A pure wrapper **cannot deliver the product's differentiator.** There is no wheel
build, no upload path, and no lock orchestration anywhere in CFE's 41,410 LOC — two of the three
charter verb families have nothing to wrap. Option A is not a smaller Mason; it is a Mason missing
the reason to exist.

**Why not B.** Three independent reasons, any one sufficient:

1. **Governance makes a fork adversarial.** Rule 1 makes SKILL.md authoritative; Rule 2 mandates
   that every conda-forge effort *edits the skill*. A fork is continuously invalidated by the loop
   that governs the domain. Every retro would widen the gap.
2. **The precedent is in this repository and it failed.** `pyforge-atlas` chose B: 80 files /
   14,461 src LOC + 110 files / 14,682 test LOC, 32 stories, PRs #58–#105 all merged. **The legacy
   `conda_forge_atlas.py` (8,902 LOC) is still the live runtime.** Every `build-cf-atlas` /
   `atlas-phase` / `query-cf-atlas` task and every atlas MCP tool still shells out to the old path.
   Nothing routes to `pyforge.atlas`. ~29,000 lines did not displace the original.
   *(The contrast confirms the rule: `pyforge-warden` also built — from nothing, with no legacy
   counterpart — and shipped 31/31, merged. Warden built because there was nothing to wrap.)*
3. **It forks the moat.** The 106 gotchas and 10 constraints are the actual differentiator. Copying
   them converts an appreciating asset into a depreciating one.

**Why C.** It is the recognition that A and B answer a question the product does not pose. The three
verb families have *different* incumbent situations, so one global answer is wrong for two of them.

**Tradeoff accepted.** Mason is **not standalone**: `mason recipe` requires a discoverable CFE root
and is inert without one (D-2). This is the real cost of C, paid deliberately, and it is why FR-5
makes degradation a designed behaviour rather than a crash, and why the other two verb families are
architecturally independent (FR-44). We buy zero knowledge duplication, automatic inheritance of
every future CFE improvement, and governance compliance by construction — and we pay with a runtime
dependency on a co-located installation.

**Enforcement.** FR-42 – FR-46. The atlas outcome proves intent is insufficient.

### D-2 — Deployment target: CFE co-located (v1)

**Decision.** v1 targets repositories where a CFE root is discoverable (this repo, or another with
its own `.claude/`). Operation with no CFE anywhere is out of scope.
**Rationale.** `recipes/` is hardcoded in 17 canonical scripts and no data-directory override exists
— making CFE relocatable is a change to a surface Mason may not edit. Pursuing it would mean
vendoring, i.e. Option B by the back door.
**Revisit when** CFE gains a portable data-directory contract through its own retro loop.

### D-3 — Three ship targets; conda-forge is asynchronous

**Decision.** `pypi` (synchronous), `channel:<name>` (synchronous), `conda-forge` (asynchronous,
returns a PR reference). Receipts state terminal-vs-pending per target.
**Rationale.** These are not the same operation. Conflating them makes "success" mean two different
things in one output line.

### D-4 — Coexist with pixi tasks; deprecate nothing

**Decision.** Mason is additive in v1. No pixi task is removed or deprecated.
**Rationale.** The atlas failure was not the rebuild alone — it was a rebuild with no migration.
Mason earns the surface by being better, then migration is proposed as its own effort.
**Revisit when** SM-1 and SM-4 are both demonstrated.

### D-5 — Token-based credentials (v1)

**Decision.** Environment-variable tokens for uploads; OIDC trusted publishing deferred to v2.
**Rationale.** Trusted publishing is CI-context-specific and would constrain v1's runtime model for
a security improvement that matters most in a CI setup Mason does not yet have.

### D-6 — Python floor 3.12

**Decision.** `requires-python >= 3.12`, matching `pyforge-warden`.
**Rationale.** Mason shells out, so its floor is genuinely free. 3.12 maximises co-installability
with the sibling most likely to share an environment. Atlas's 3.14 is documented as intentional for
atlas and does not generalise.

### D-7 — Interpreter selection is explicit

**Decision.** `--cfe-python` → `MASON_CFE_PYTHON` → `sys.executable`, with the import floor probed.
**Rationale.** `sys.executable` is right in a fat pixi env and wrong in a lean one. Without this,
Mason installed into its own lean environment cannot run CFE at all — a silent, confusing failure.

### D-8 — No Mason MCP server in v1

**Decision.** v1 ships no MCP server. The existing 46-tool server stands. A later epic may add a
small server for Mason-only verbs.
**Rationale.** Duplicating 46 tools is the atlas failure mode in miniature. `fastmcp >= 3.4.4` is
already a root dependency, so deferring costs nothing. FR-31's JSON output keeps the agent path open
meanwhile.

### D-9 — argparse

**Decision.** argparse; no click, no typer.
**Rationale.** Matches `pyforge.warden.cli` and all 60 CFE scripts; zero new dependency; satisfies
the lean-dependency doctrine. Cost — worse help-text ergonomics — is accepted.

---

*Decisions D-10 – D-13 were added in revision 2, resolving contradictions the adversarial review
found in revision 1 (`review-adversarial.md`).*

### D-10 — `--to conda-forge` requires a CFE-co-located recipe directory

**Decision.** Shipping to conda-forge works only from a repository where the CFE root resolves
**and** the recipe sits at `<cfe-root>/recipes/<name>/`. Shipping to `pypi`, `pypi-test`, and
`channel:<name>` has no such requirement.
**Rationale.** CFE's `submit_pr.py` reads from `REPO_ROOT/recipes/<name>` and writes into a
staged-recipes fork clone. Mason cannot change either behaviour (AD-15), so from an arbitrary
project there is no source directory and no fork. Revision 1's UJ-1 promised a journey the product
could not deliver; this decision makes the boundary explicit rather than letting a user discover it
mid-release.
**Tradeoff.** The differentiator is fully executable only inside a CFE-co-located packaging repo in
v1. `pypi` shipping — the half with no incumbent competitor for the combined motion — works
everywhere. `mason doctor` reports the boundary before a user attempts a release.
**Revisit when** CFE gains a recipe-path parameter through its own retro loop.

### D-11 — Idempotence is achieved by interrogation; no ship state is persisted

**Decision.** Cross-invocation idempotence (FR-18, NFR-8) is implemented by querying each target,
including a fork search for an open PR on CFE's deterministic `add-recipe-<name>` branch. Mason
persists no receipt cache.
**Rationale.** A local cache is a second source of truth that goes stale and silently skips a real
upload. The interrogation is feasible for all four targets because each has a queryable identity.
**Tradeoff.** Every ship pays a query round-trip and is unavailable offline. Accepted: shipping is
inherently a network operation.

### D-12 — `ship` is a verb; the charter form is an alias

**Decision.** The canonical command is `mason package ship --to <targets>`. `mason package --ship
<targets>` is a documented alias, and the only bare-noun form that runs.
**Rationale.** Revision 1 had no command that shipped: FR-30 mandates noun-verb and makes bare
`mason package` exit non-zero, while `build` explicitly uploads nothing. The alias preserves the crew
charter's cadence verbatim without abandoning the structural rule.

### D-13 — No configuration file; every knob is flag plus environment variable

**Decision.** Confirms and completes AD-13. Each runtime knob has both forms; the v1 set is
enumerated in FR-48.
**Rationale.** Revision 1 called FR-4's timeout "configurable" while providing no configuration
mechanism anywhere. Rather than introduce a file — and with it a precedence question — every knob
gets the flag/env pair the rest of the CLI already uses.

## 11. Public Surface and Versioning

- **Public surface** = the CLI (`mason <noun> <verb>` + global flags), the JSON output schema, the
  exit-code contract, and the console entry point. `pyforge.mason`'s Python API is **not** public in
  v1; nothing may import it as a library and rely on stability.
- **Versioning.** Semver from the first release. MAJOR for a CLI or JSON-schema break; MINOR for new
  verbs or fields; PATCH for fixes.
- **Deprecation.** A removed verb or JSON field is announced one MINOR ahead, warns on use, and is
  removed no earlier than the next MAJOR.
- **CFE coupling is not versioned.** Mason declares no CFE version compatibility range in v1 —
  delegation is by argv, and CFE's own semver governs its behaviour. If a CFE change breaks an
  adapter call, the fix is in the adapter. `[NOTE FOR PM]` If this proves fragile, a declared
  minimum CFE version becomes necessary; watch for it.

## 12. Risks and Mitigations

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R-1 | **Seam erosion** — recipe logic migrates into Mason one helper at a time, reproducing atlas | Fatal to D-1 | FR-42/FR-43 meta-tests; SM-C1/SM-C3 counter-metrics |
| R-2 | CFE stdout changes and breaks an adapter call | Medium | FR-4 tolerant parsing; FR-46 fidelity test; adapter-local fix |
| R-3 | Nobody adopts Mason because pixi tasks already work | High | SM-1 self-hosting is the proof; D-4 coexistence removes migration pressure |
| R-4 | `--ship conda-forge` reports success for a PR that is later rejected | Medium | FR-17 asymmetric receipts make pending explicit |
| R-5 | pixi build preview semantics change | Medium | Both siblings share the exposure; fix is workspace-wide, not Mason-specific |
| R-6 | Lean env cannot run CFE (interpreter mismatch) | Medium | D-7 explicit selection + FR-3 floor probe + FR-34 doctor |
| R-7 | Competitive blind spot — an unknown entrant already does dual-ship | Medium | OQ-6; the survey ran without a web-search budget |
| R-8 | Credential leak through logs or receipts | High | NFR-2; FR-20 never logs values; FR-6 isolation |
| R-9 | **FR-42 ships vacuous** — a deny-list that matches nothing passes forever and the seam is unguarded in practice | Fatal to D-1 | FR-42's planted-violation fixtures make an empty deny-list a failing test; SM-2 requires the fixtures |
| R-10 | SM-1's first `--to pypi` is also its production one-way door | Medium | FR-50 TestPyPI rehearsal gates it |
| R-11 | D-10's boundary makes the differentiator look narrower than the positioning claims | Medium | Stated in UJ-1, FR-23, §6.2, and reported by `doctor`; the `pypi` half is unrestricted |

## 13. Open Questions

Resolved during this PRD (now D-records): deployment target → D-2; ship-target semantics → D-3;
pixi-task coexistence → D-4; credential model → D-5; Python floor → D-6; interpreter resolution →
D-7; MCP in v1 → D-8; CLI framework → D-9. Resolved in revision 2: conda-forge ship boundary →
D-10; idempotence mechanism → D-11; the missing ship verb → D-12; configuration surface → D-13.

Carried forward:

1. **OQ-1** — Which `mason recipe` verbs beyond the eight in FR-7 – FR-14 earn a place? Deliberately
   deferred to usage; SM-C2 warns against reflexive coverage. *Owner: architect. Revisit: after v1
   dogfooding.*
2. **OQ-2** — Does `channel:<name>` upload via `pixi publish`, `anaconda upload`, or both? An
   architecture-level engine choice with no product consequence. *Owner: architect. Revisit: at
   architecture.*
3. **OQ-3** — Does Mason own multi-ecosystem autotick (CRAN/npm/cargo), or Marshal/Steward? The
   origin dream places it in the packaging factory; the crew charter omits it from Mason's cadence.
   *Owner: crew-level. Revisit: before v2 scoping.*
4. **OQ-4** — Should `mason environment lock` prefer `conda-lock` or `pixi.lock` when both are
   viable, and is the relationship between them one of succession? Unresolved by available sources.
   *Owner: architect. Revisit: at architecture.*
5. **OQ-5** — Is there a real user for `--target application` / `--target binary`, or is `library`
   the whole product? *Owner: PM. Revisit: after v1 feedback.*
6. **OQ-6** — Competitive coverage risk: the survey was assembled from known primary sources without
   a web-search budget. A discovery sweep for unknown dual-publish entrants has not been run. Would
   invalidate D-1's differentiation premise if one exists. *Owner: PM. Revisit: before public
   positioning.*
7. **OQ-7** — Does Mason declare a minimum CFE version once coupling fragility is observed?
   *Owner: architect. Revisit: on first adapter break.*
8. **OQ-8** *(new in r2)* — Is CFE's Docker / CI-parity build reachable through an adapter at all?
   The Docker path is a pixi task (`recipe-build-docker` → `build-locally.py`), not a canonical
   script, and `local_builder.py` is explicitly Docker-less. If no adapter-reachable entry point
   exists, drop FR-9's Docker bullet. *Owner: architect. Revisit: at S-2.6.*
9. **OQ-9** *(new in r2)* — Can the FR-45 governance check inspect the effort's commit range
   automatically in this repository's branching model, or must it be a documented manual gate?
   *Owner: architect. Revisit: at S-5.2.*
10. **OQ-10** *(new in r2)* — D-10 narrows the differentiator's reach in v1. Does that change the
    product's positioning claim, or is "the `pypi` half works everywhere, the conda half works where
    your recipes live" an acceptable public story? *Owner: PM. Revisit: before public positioning.*

## 14. Assumptions Index

- **§1, §2** — The crew-charter verbs (`recipe build`, `package --ship`, `environment lock`) are
  binding scope, taken verbatim from `docs/dreams/ecosystem-crew.md` § 5. Never confirmed with a
  stakeholder.
- **§1** — "Dual-ecosystem" means conda-forge + PyPI. npm/CRAN/CPAN/LuaRocks are *source* ecosystems
  for recipe generation, not `--ship` targets.
- **§2** — The target operator is the individual maintainer or small team already using pixi. If it
  were conda-forge core, the autotick-bot is the incumbent and Mason is redundant.
- **§4.6, D-6** — The conventions demonstrated by `pyforge-warden` and `pyforge-atlas` are normative
  for new workspace members. Inferred from two instances plus their comments, not a written standard.
- **§4.1, NFR-13** — CFE script stdout is stable enough to parse. Evidenced by 46 MCP tools over an
  extended period with one known tolerance shim; not a formal contract.
- **§9** — Local measurements (41,410 LOC, 106 gotchas, 46 MCP tools, 1,186 tests) are point-in-time
  at CFE v8.79.1 and will drift. Used for shape arguments, not commitments.
- **D-3** — `pixi publish`'s documented silence on PyPI reflects an absent feature. Not verified
  against pixi source.
- **FR-24, SM-1** — Mason's own package is a representative test case for `--ship`. It is a
  pure-Python library; a compiled package would exercise paths Mason's self-hosting does not.
