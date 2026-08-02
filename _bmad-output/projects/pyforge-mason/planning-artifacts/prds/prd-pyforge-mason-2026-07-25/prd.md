---
title: Mason (pyforge-mason)
status: final
created: 2026-07-25
updated: 2026-08-01
project: pyforge-mason
currency_review: Reviewed 2026-08-04 — spec/brief timestamp bump was structural (project relocation / memlog story-completion recording), not content drift; PRD unchanged.
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

> **Consolidated 2026-08-02** — see
> `archive/_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-presenton-pixi-image-2026-05-01/`
> / `archive/_bmad-output/projects/pyforge-mason/planning-artifacts/briefs/brief-presenton-pixi-image-2026-07-25/`
> for the original standalone documents.

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

---

## Satellite: Presenton (air-gapped conda-native repackaging)

**Status: BLOCKED.** This satellite PRD was finalized 2026-07-25 (`status: final`) and describes a
genuinely different product from `mason` itself: an air-gapped, conda-forge-native repackaging of
the third-party Presenton AI deck-generation app for Red Hat OpenShift. Its owning Dream
(`docs/dreams/presenton-pixi-image.md`) carries `status: archived`, `archived-reason: blocked`,
`blocked-on: Phase-0 decision gate (Epic 1)` — no story has entered implementation, and the six
Phase-0 exit criteria below (most load-bearingly, exit 6a: whether Microsoft's disconnected on-prem
stack already ships a Copilot-for-PowerPoint-equivalent) remain unresolved.

**Contradiction flagged.** This satellite's own governing Spec (`spec-presenton-pixi-image`, prior
to this consolidation) was rewritten 2026-08-02 into an archived retirement record that names, as an
explicit non-goal, "Folding this Dream's intent into `pyforge-mason`'s own narrative" — reasoning
that "the two are genuinely different subject matter... archiving this separately (rather than
absorbing it) reflects that difference honestly." Folding this PRD into Mason's own PRD, as done
below, directly overrides that prior decision. It is done here at the user's explicit direction,
after being shown that separation language — recorded rather than silently resolved. The Dream-level
narrative and the epics/blocked-status stay separate; only the planning-chain documents (the brief,
this PRD, the architecture spine, and the Spec) are consolidated into one per-station document. See
`archive/_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-presenton-pixi-image-2026-05-01/`
for the original standalone document.

The full standalone document follows, verbatim, unchanged from its 2026-07-25 finalized form.

# Product Requirements Document - presenton-pixi-image

**Author:** rxm7706
**Date:** 2026-04-30 (revised 2026-07-25)

## Revision Log (2026-07-25)

This PRD was revised against a technical research pass (`planning-artifacts/research/technical-presenton-stack-ocp-airgap-research-2026-07-25.md`) and a domain research pass (`planning-artifacts/research/domain-regulated-enterprise-airgap-ai-deck-market-research-2026-07-25.md`), distilled through `planning-artifacts/briefs/brief-presenton-pixi-image-2026-07-25/`. Full delta trail: `planning-artifacts/.memlog.md`. Six load-bearing deltas from the 2026-04-30 draft, all primary-sourced:

1. **`template-style-extractor` dropped from v1.** Live upstream Presenton (`servers/fastapi/services/office_document_service.py`, fetched 2026-07-25) already does LibreOffice-free template import — stdlib `zipfile`+`ElementTree` for DOCX/PPTX/XLSX, native ODF, `pdfplumber` (MIT) for PDF — with the exact legacy-`.doc`/`.ppt` rejection behavior this PRD proposed inventing. Recipe count drops from a fixed six to **five confirmed**, pending item 2.
2. **New Phase-0 gap: the memory/RAG subsystem.** `mem0ai` + `fastembed-vectorstore` are unconditional upstream dependencies, neither on conda-forge. New Phase-0 exit criterion 6 added (§ Phase 0 Exit Criteria) to decide: two more recipes, or a documented feature-drop.
3. **Risk R3 rewritten.** The 2026-04-30 draft's trigger ("Microsoft Copilot reaches IL5 GA," 12-24mo window) already happened without collapsing the JTBD — IL5 remains Azure Government cloud, not air-gapped. The real trigger, Microsoft's own disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, GA worldwide 2026-02-24), is live now, and whether it includes a Copilot-for-PowerPoint-equivalent is unresolved — escalated to a Phase-0-blocking check, not a 12-24-month watch item.
4. **Risk R7 resolved/replaced.** PyMuPDF/AGPL is moot (template-style-extractor dropped; `pdfplumber`, MIT, is upstream's real and sufficient choice). Replaced with a smaller flag: `psycopg` (LGPL-3.0-only) for buyer legal review.
5. **`llmai` version corrected** 0.2.2 → 0.2.8 (PyPI-verified exact pin) throughout. Still Apache-2.0, still absent from conda-forge — the core claim was and remains correct.
6. **OpenShift Restricted SCC grounded** with current specifics (`restricted-v2` default: capabilities dropped, `seccompProfile: runtime/default`, no privilege escalation; `restricted-v3` new-install default: adds pod-level user-namespace isolation) and a new risk (R9) naming the headless-Chromium-sandbox-vs-user-namespace-isolation interaction as an explicit Phase-0/architecture spike.

Everything else — classification, the 9-persona model, the buyer-gate/user-gate JTBD, the M365-Copilot-for-PowerPoint reference product, Q1/Q3/Q4 decisions, the competitive table, MVP/Growth/Vision scope shape, the measurable-outcomes table, Phase-0 exits 1-5 — carries forward from the 2026-04-30 draft unchanged; this is a revision, not a rewrite.

## Executive Summary

It's 11pm in a SCIF. The board deck is due at 8am. Microsoft Copilot is on the other side of the air gap. Today she builds it by hand. Tomorrow Presenton builds it for her.

`presenton-pixi-image` repackages the open-source Presenton AI deck-generation web app as a fully air-gapped OCI image deployable on RedHat OpenShift Container Platform (OCP). Built from five conda-forge-native recipes (plus up to two more, pending a Phase-0 memory-subsystem decision — see Revision Log) plus a sideloadable VS Code extension; assembled via pixi + pixitainer; no LibreOffice in the runtime — confirmed current as of 2026-07-25, upstream has none anywhere, not just on the output side.

**Target users (buyer → end user):**

1. **Buyer** — Platform/security team owning the OCP cluster (CISO + compliance + platform engineering director). Signs procurement once.
2. **OCP operator (day-0)** — Pulls image, configures LLM provider tier, deploys via Helm/manifests; preflight via `tests/install/`.
3. **OCP operator (day-2)** — Operates deployed cluster: rotates LLM credentials, patches CVEs (P95 14-day rebuild-and-resign capability, response SLO measured-and-conditional-on JFrog allowlist SLA ≤48h AND maintainer staffing), responds to mark-broken on pinned deps; smoke + health via on-image `tests/operational/`.
4. **Recipe-maintainer** — Verifies upstream-Presenton drift via online weekly cron (`tests/drift/`); refreshes fixture set on path-watch trigger.
5. **Analyst (end user)** — Generates brand-compliant, agent-refined decks from prompts + uploaded source material; refinement latency `<10s P95` on Tier-1 LLM endpoints (Tier-2 llama.cpp on CPU is async/batch UX, not interactive).
6. **VS Code developer** — Installs sideload `copilot-bridge` VSIX (sideload-only, no Marketplace); bridge daemon at `localhost:4141` exposes OpenAI/Anthropic-compatible endpoints for local Presenton testing.
7. **JetBrains developer** — In-scope for v1 via REST + OpenAPI spec + Postman collection; full JetBrains plugin deferred to v2.
8. **End web user of upstream Presenton** — OUT-OF-SCOPE; upstream owns the React/Next.js UI.
9. **Conda-forge staged-recipes reviewer** — Five-to-seven recipes = five-to-seven review cycles (revised 2026-07-25); PRD acceptance criteria include lint-clean recipes, deterministic builds, rerender-survivability.

**The problem being solved:** Air-gapped enterprises whose data classification prohibits the FedRAMP-cloud version of Microsoft 365 Copilot are stuck producing decks by hand — slower than LLM-assisted tooling AND systematically lower in language and style quality. M365 Copilot for PowerPoint is the reference shape but unavailable on the wrong side of the cloud-vs-on-prem boundary. Boring substitutes (Marp, python-pptx + Jinja2) trivially clear the provenance bar but fail the capability bar — they don't summarize internal long-form documents into review-ready decks.

**Jobs-to-be-Done — two gates that don't collapse:**

- **Buyer gate (signs the PO):** *"Give me a turnkey, mirrorable AI deck generator that produces zero exfiltration paths and zero unreviewed dependencies, so I can approve it once and forget it."*
- **User gate (drives renewal):** *"Turn my 40-page internal compliance/research/incident document into a 12-slide draft I'd rather edit than write from scratch, without leaving my secure workstation — and the second deck takes half the time of the first."* User-gate quality anchored at "better than writing it by hand at 2 a.m.", NOT at "M365 Copilot quality."

**Combined JTBD:** *Summarize internal documents into review-ready decks without the content leaving the air-gap perimeter — what we'll call **boundary-local inference** throughout this doc.*

**Why now:**

- **Technical readiness:** Presenton OSS is mature enough to repackage; conda-forge ecosystem (Playwright + Chromium-bundled-recipe pattern, llama.cpp, pixi/rattler-build) finally lets us ship this air-gap-clean in 2026.
- **Acute pain:** Hand-crafted decks are systematically inferior in speed AND in language/style quality versus LLM+Presenton output.
- **Window of opportunity (REVISED 2026-07-25 — see Revision Log item 3):** the 2026-04-30 draft's "12-24 months until IL5 GA" framing is falsified — GCC/GCC-High/DoD/IL5 Copilot GA already happened without collapsing this JTBD, because none of it is air-gapped. The real window is bounded by Microsoft's own disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local), GA worldwide **2026-02-24** — whether it already includes Copilot-for-PowerPoint-equivalent deck generation is unconfirmed and is now a **Phase-0-blocking verification item** (exit criterion 6), not a 12-24-month monitoring assumption. Treat the window as unknown-and-urgent, not comfortable.
- **Supply-chain math claim:** Five unsigned Python/Node/binary upstreams (revised from six — see Revision Log item 1) cannot pass an IL5 SBOM gate independently; one signed conda-forge OCI image with one SBOM can. The math only closes via repackaging.

### Differentiator

**Core insight (validated):** *"The buyer is paying for a Copilot-class deck generator they're allowed to install."* (Capability target: 70-85% parity with M365 Copilot for PowerPoint on long-form-doc summarization — analyst estimate based on feature-coverage comparison; methodology defined in Phase 0 evaluation plan; gap-closure tracked on roadmap.)

**The intersection that nothing else clears.** This product wins on the conjunction of **Copilot-class capability** AND **survives security review**. Among evaluated alternatives, the only product delivering both halves without an exfiltration path:

| Substitute | Why it loses |
|---|---|
| Marp / Marpit, python-pptx + Jinja2 templates (DIY power-user floor) | Trivially clears provenance; fails capability (no LLM long-form summarization). |
| LibreOffice Impress + local LLM plugins (open-source floor) | Air-gap-deployable but lacks integrated agent-orchestration UX for deck-class workflows. |
| M365 Copilot for PowerPoint | Reference shape; cloud-only; unavailable to customers whose data classification prohibits the FedRAMP-cloud version. |
| SlidesGPT / Gamma / Tome | SaaS, cloud-only — air-gap-incompatible. Shape end-user expectations but cannot be deployed. |
| hugohe3/ppt-master | AI IDE skill (Claude Code, Cursor, Copilot); requires external LLM API; air-gap-incompatible by design. |

**Customer-facing supply-chain framing:** *Today the customer integrates five unsigned upstream artifacts (revised 2026-07-25, was six) and owns the integration risk. With this, they integrate one signed artifact and we own the integration risk* — attested via the build-provenance section of this PRD. The five conda-forge recipes (plus up to two more, pending the Phase-0 memory-subsystem decision) + Chromium-vendoring + clean-room reimpls + JFrog mirror integration are the price of admission to the capability-plus-defensibility intersection. Each artifact is a receipt proving the platform team is permitted to install Copilot-equivalent capability inside the perimeter.

**Architecture cohesion:** The 6 recipes compose into a single OCI image; the image deploys as a standard Helm chart on OCP; the chart consumes a Tier 1/2/3 LLM endpoint as configuration, not as a bundled component.

### v1 Deliverables

**Five conda-forge recipes confirmed (each gated on a 4-check validation pattern: build + validate + scan + optimize), plus up to two more pending a Phase-0 decision:**

- `presenton-export-node` — Node + Playwright bundle; replaces opaque upstream `presenton-export/index.js`.
- `pptx-assembler` — python-pptx + Pillow; replaces opaque upstream `convert-linux-x64`; produces image-overlay + extracted text shapes.
- `pptx-thumbnail-inject` — `docProps/thumbnail.jpeg` injection for AI-generated decks.
- `playwright-with-chromium` — Playwright + bundled `chrome-headless-shell` for air-gap.
- `llmai` — Apache-licensed unified-LLM-provider abstraction (used by upstream Presenton; pinned `0.2.8` as of 2026-07-25, upstream re-pins fast, re-verify at submission time).

**DROPPED 2026-07-25:** `template-style-extractor` — live upstream Presenton already implements LibreOffice-free template import (stdlib `zipfile`+`ElementTree` for PPTX/DOCX/XLSX, native ODF, `pdfplumber` for PDF), including the legacy-`.doc`/`.ppt`-rejection behavior this recipe was going to (re)build. See Discovery & Re-Architecture and Decisions Log Q2 below.

**Phase-0-gated (new 2026-07-25):** `mem0ai` + `fastembed-vectorstore` — unconditional Presenton memory/RAG dependencies, neither on conda-forge today. Phase 0 exit criterion 6 decides: add both as recipes 6-7, or ship v1 with the memory/chat-history subsystem disabled.

**One VS Code extension:** `copilot-bridge` (sideload-only, no Marketplace; spec at `docs/specs/copilot-bridge-vscode-extension.md`).

**Five v1 platform additions** (each with explicit scope from R3 reclassification):

- **Brand-compliance enforcement** — three-lane UX framework: auto-fix high-confidence, batched-review mid-confidence, ignore low-confidence + strict-mode opt-in. Thresholds TBD pending Phase 0 spike.
- **Agent orchestration** — Presenton-existing only (pinned to specific Presenton release tag, set in Phase 0); not net-new build.
- **Observability** — Prometheus `/metrics` endpoint, scrapeable + non-blocking; no dashboards shipped.
- **Chargeback** — rides the same `/metrics` endpoint as observability; emit-only, no ledger.
- **LLM use-case approval workflow** — documentation only, not software.

### Landing Conditions (4 guardrails)

1. Engineering complexity is honestly re-rated whenever v1 scope expands (exercised already: `engineering: recipes=medium-high, cleanroom=high, platform=very-high`; supply-chain=very-high).
2. CVE-response cycle is **measured-and-conditional-on-JFrog-SLA** (per-segment SLA for upstream-patch + recipe-rebuild + JFrog-allowlist-sync), not assumed.
3. Brand-compliance enforcement: thresholds sized as a research spike; the UX-band design (auto-fix / batched-review / ignored + strict-mode) is a v1 commitment, not deferred.
4. The "knowledge-base integration = vision, not v1" boundary is held against customer pressure; v1 is explicitly scoped to "decks where source material fits in prompt + uploaded files." Fixture-capture sequencing defined in Test Strategy section (Phase 0 boundary).

### LLM Dependency (Explicit)

Customer must have at least one approved LLM endpoint (tier selection covered in deployment guide):

- **Tier 1** — Internal corporate proxy at `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` / `GEMINI_BASE_URL` (operational targets measured against Tier 1).
- **Tier 2** — `llama.cpp` sidecar with allowlisted GGUF model from HuggingFace mirror (Qwen 2.5 7B Q4_K_M default, Llama 3.2 3B Q4 fallback; async/batch UX, not interactive).
- **Tier 3** — Init-container fetches GGUF from internal artifact registry (JFrog Artifactory or equivalent) at startup.

Reference LLM class for measurable cost/latency targets selected in Phase 0 (initial discovery + benchmark-definition phase before v1 development; candidates: vLLM-served 70B-class GPU, Azure OpenAI tenant endpoint, on-prem Llama-3-70B).

### Continuity Plan (if upstream Presenton stalls or maintainer team turns over)

Maintainer-team independence covers all three engineering axes (recipes, cleanroom reimpls, platform): conda-forge recipes are mainline-eligible (any conda-forge maintainer could take over); cleanroom reimpls are documented and source-available; platform manifests are vanilla Helm/kustomize. Fixture-capture phase + drift-detection harness make ownership transferable across team turnover.

## Project Classification

- **Project type:** `infrastructure` (primary) + `developer_tool` (secondary). Customer is *handed* this product (mandate from CISO/security team), not *reaching for* it. Infrastructure decomposes into named sub-deliverables (Helm chart, OCP manifests, JFrog mirror topology, LLM provider tiering); the VSIX is a first-class delivery surface regardless of secondary classification rank.
- **Domain:** `general` (product). **Deployment domain:** `regulated-enterprise (air-gapped)`. Product is horizontal (AI deck generation, any industry); deployment context is govtech/fintech/defense-adjacent customers whose data classification prohibits cloud SaaS.
- **Complexity:** `high` with split axes —
  - **Engineering:** `recipes=medium-high`, `cleanroom=high`, `platform=very-high` (re-rated from "high" per guardrail #1 to honestly account for the 5 v1 platform-layer additions).
  - **Supply-chain:** `very-high` — multi-week security-review SLA per recipe through JFrog mirror, allowlist gating, browser-binary vendoring.

  Schedule should be driven by the supply-chain axis, not the engineering axis.
- **Project context:** `greenfield-with-brownfield-constraints` (building 6 recipes + fixture-capture phase + OCP manifests + 4 fixture trees from scratch, but constrained by upstream Presenton API surface and local-recipes monorepo conventions: pixi + rattler-build, v1 recipe.yaml, JFrog auth pattern via `JFROG_API_KEY`).

## Discovery & Re-Architecture (step-01b)

### Original assumption (step-01-init)
Repackage Presenton as a conda-forge OCI image by vendoring `hnrobert/pptx2marp` + `ebibibi/marp2pptx` into a single `pptx2marp-bridge-marp2pptx` Python package, replacing every LibreOffice-based path with bridge calls.

### Why that assumption collapsed

1. **Adversarial review** flagged two dealbreakers:
   - **A1.** PPTX ↔ Marp round-trip is structurally lossy — the two data models (OOXML object graph vs. constrained Markdown grammar) are fundamentally incompatible.
   - **C2.** `python-pptx` does not embed `docProps/thumbnail.jpeg`, so AI-generated decks land in PowerPoint/Finder/Explorer with placeholder thumbnails 100% of the time.

2. **Gemini cross-check** (gemini-2.5-pro) confirmed both dealbreakers and added that the OOXML thumbnail injection via `zipfile` + `[Content_Types].xml` Override is the standard LibreOffice-free workaround.

3. **Code investigation** of `presenton/presenton` revealed:
   - Presenton does **not use Marp**. Slides are React/Next.js components rendered live in a running Next.js server.
   - The export pipeline is `Puppeteer chrome-headless-shell → Next.js URL → page.pdf() / page.screenshot() → JSON+images.zip handoff → convert-linux-x64 (PyInstaller binary) → final .pptx`.
   - LibreOffice was, at the time of this discovery pass, on the **input side** (template import: uploaded PPTX/DOCX → soffice → PDF → screenshots → AI extraction), gated by `ARG INSTALL_LIBREOFFICE=true`. **CORRECTED 2026-07-25:** re-verified against current upstream `main` — LibreOffice is gone entirely, not even on the input side. No `ARG INSTALL_LIBREOFFICE`, zero `soffice` references anywhere in the repo (code search confirmed). Template import (`servers/fastapi/services/office_document_service.py`) now runs on pure stdlib (`zipfile`+`ElementTree`) for DOCX/PPTX/XLSX, native ODF support, and `pdfplumber` (MIT) for PDF text extraction — LibreOffice-free, near-zero new dependencies, and it already rejects legacy `.doc`/`.ppt`/`.xls`/`.rtf` with the same "save in a modern format" behavior this PRD independently proposed inventing (see Decisions Log Q2, revised). This upstream change happened sometime between this draft's original 2026-04-30 authoring and the 2026-07-25 revision pass — a reminder that Presenton moves fast and every "current state of upstream" claim in this document has a shelf life.
   - The export bundle (`index.js`, ~6 MB minified Node) and the PPTX assembler (`convert-linux-x64`, ~50 MB PyInstaller) are downloaded from `presenton/presenton-export` releases at build time. **Source for both is not published** — the repo contains only release artifacts.

4. **Conda-forge ecosystem check**:
   - `pyppeteer` is officially unmaintained; upstream recommends Playwright. Ruled out.
   - `playwright` (Node) and `playwright-python` are on conda-forge but do **not** bundle browser binaries; `playwright install` fetches at runtime. Air-gap-hostile by default; supports `PLAYWRIGHT_DOWNLOAD_HOST` mirror.
   - `chromium` is **not** on conda-forge. Three PRs (#5256, #7146, #11864) failed; staged-recipes#21431 tracks intent but the issue opener himself doubts it's worth the effort.
   - Bundled-binary pattern from `pyppeteer-feedstock#3` (bollwyvl, 2020) is the realistic path: build a `playwright-with-chromium` recipe that downloads the browser at conda-build time and ships it inside the conda artifact.

### New architecture

Four replacement components, each source-available and conda-forge-recipeable:

| Component | Replaces | Stack | Approx. size |
|---|---|---|---|
| `presenton-export-node` | `presenton-export/index.js` (opaque minified bundle) | Node + Playwright + Chromium | ~200–500 LOC |
| `pptx-assembler` | `convert-linux-x64` (opaque PyInstaller binary) | Python + python-pptx + Pillow | ~500 LOC |
| `pptx-thumbnail-inject` | (gap — no upstream solution) | Python + zipfile + Pillow | ~100 LOC, may fold into `pptx-assembler` |
| `playwright-with-chromium` | (gap — Playwright doesn't bundle browser on conda-forge) | conda-forge recipe; bundles `chrome-headless-shell` at build time | recipe + ~150 MB binary |

Plus Presenton patches: swap the upstream binary fetch for the new packages, flip `INSTALL_LIBREOFFICE=false`, and either drop or rewrite the template-import path that currently relies on `soffice --convert-to pdf`.

## Decisions Log

- **Q1 — Editable PPTX fidelity bar:** Option **(b)** image-overlay + extracted text shapes. Matches upstream `convert-linux-x64` behavior. User retains visual fidelity to web preview AND ability to edit text (fix typos, change names, copy text out, screen-reader-readable, search works). Trades away: theme/master changes, element-level animations, native chart objects, length-tolerant text edits. Industry norm for AI-deck SaaS.
- **Q2 — Template-import feature scope [SUPERSEDED 2026-07-25 — see Revision Log item 1].** Original 2026-04-30 decision: reimplement on conda-forge-native libraries via a new `template-style-extractor` component (`.pptx` via python-pptx, `.docx` via python-docx, `.pdf` via pymupdf text-based + pdf2image/pytesseract OCR fallback; ODP/ODT via odfpy deferred; legacy `.ppt`/`.doc` dropped with a clear error). **Revised decision:** build nothing — live upstream Presenton (`servers/fastapi/services/office_document_service.py` + `documents_loader.py`, verified 2026-07-25) already ships exactly this shape, LibreOffice-free, using only the Python standard library (`zipfile`+`ElementTree`) for DOCX/PPTX/XLSX, native ODF support (no `odfpy` needed), and `pdfplumber` (MIT, already conda-forge-available) for PDF text — plus the identical legacy-format rejection this PRD had independently proposed. No OCR fallback exists upstream (no `pytesseract`/`pdf2image` dependency), so scanned-PDF support remains a genuine gap, but it is a net-new capability question, not a "replace LibreOffice" one — if a buyer needs it, scope it separately in a later cycle, don't fold it into this repackaging effort. Net effect: `template-style-extractor` is dropped from v1 entirely; the pipeline Presenton already runs (`parse → JSON → LLM`, no rendering, no browser, no LibreOffice) is directly reusable as-is.
- **Q3 — AI/LLM provider strategy (two paths):**
  - **Dev path:** Reuse the existing `copilot-bridge` VSIX (spec: `docs/specs/copilot-bridge-vscode-extension.md`). Developer with VS Code or PyCharm + GitHub Copilot subscription installs the sideload-only `.vsix`; bridge daemon (`copilot-api`, recipe in this repo) runs on `localhost:4141` and exposes OpenAI/Anthropic-compatible endpoints. Story 6 ("Configure presenton") emits Presenton env vars. PyCharm support: docs-only one-pager pointing JetBrains AI Assistant at the same daemon — no separate JetBrains plugin in v1 (defers v2).
  - **Production path:** Three-tier configurable LLM provider, all OpenAI-compatible, operator picks at deploy time:
    - Tier 1 (default for OCP) — internal corporate LLM proxy via `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` / `GEMINI_BASE_URL` env vars; no in-image model.
    - Tier 2 — bundled local LLM via `llama.cpp` sidecar (conda-forge), GGUF model mounted from volume; default Qwen 2.5 7B Q4_K_M (~6GB RAM) or fallback Llama 3.2 3B Q4 (~3GB RAM).
    - Tier 3 — init-container fetches GGUF from internal artifact registry (JFrog/Harbor/S3) at startup, mounts to shared volume; model lifecycle managed centrally.
  - Same Presenton code on both paths; only env-var config differs. Air-gap-clean by construction (Tier 1 endpoint inside perimeter; Tier 2/3 fully in-image / in-cluster).
- **Q4 — Air-gap definition:** Option **(b) Full air-gap.** Build CI runs inside the perimeter against an internal JFrog Artifactory mirror; mirror holds curated subsets of conda-forge, npm, HuggingFace (and possibly more). Some packages are restricted; some GGUF models are restricted. Implies: (i) every dependency must be allowlisted on the mirror or the build fails; (ii) net-new conda-forge recipes authored by this project must complete upstream-merge → mirror-sync → security-review before deployment; (iii) build-time external CDNs (Microsoft Playwright CDN for chrome-headless-shell, etc.) cannot be reached and must be either mirrored or vendored. Existing infrastructure: `docs/enterprise-deployment.md` and the `check_dependencies` MCP tool already support JFrog Artifactory + auth env vars (`JFROG_API_KEY`).
- **Q5 — Project classification (step-02-discovery, validated through 5-method advanced elicitation + 2 party-mode rounds, 6 BMAD agents, 3 cross-talk pairings):** Locked. See `classification:` block in frontmatter for full structure. Key shifts from initial proposal: (i) projectType flipped from `web_app` to `infrastructure` primary on the JTBD verb test (John: nobody reaches for this; they're handed it), with `developer_tool` secondary for the VSIX + recipes-as-artifacts surface. (ii) Engineering complexity split into three sub-axes (recipes=medium, cleanroom=high, platform=high) — Amelia's flag that "medium" was dishonest given clean-room reimpls. (iii) primaryUsers expanded from 3 to 7 with explicit out-of-scope marking (recipe-maintainer added by 3 agents independently; OCP operator split day-0/day-2 by Sally; jetbrains-developer flagged as packaging gap not silent omission; conda-forge-staged-recipes-reviewer added as gatekeeper persona by Mary). (iv) Domain language plain-English fixed: `regulated-enterprise (air-gapped)` instead of `govtech-adjacent` (Paige). (v) New strategic frontmatter fields: `buyer`, `referenceProductSubstituted` (M365 Copilot for PowerPoint — Mary's finding), `supplyChainPosture: defensive-mirror-gated` (Porter's five lens), `upstreamDriftRisk: high` (John). (vi) JTBD reframed by Mary→John dialogue from "deck generation" → "defensible provenance" → final form: **inference-at-the-edge of a security boundary** (intersection of Copilot-class capability AND survives security review). See JTBD section below for two-gate buyer/user form.
- **Q6 — Product vision (step-02b, validated through 5-method advanced elicitation [Hindsight, What-If, Shark Tank, Failure Mode, Critique] + party-mode round 3 with all 6 BMAD agents):** Locked. 13 deltas applied to working vision model; full vision content lands in Executive Summary (step-02c). Key shifts from initial-answer vision: (i) Latency target conditional on LLM tier — `<10s P95 Tier 1+3; Tier 2 documented as async/batch` (Winston, Amelia). (ii) CVE-response 14d reframed as "rebuild-and-resign capability within 14 days; response SLO contingent on JFrog allowlist SLA ≤48h AND maintainer staffing tier" (Winston, Amelia, Mary). (iii) Five v1 scope additions re-classified rather than wholesale-added: brand-compliance enforcement = v1 with UX-band spec (auto-fix/batched-review/ignored), agent-orchestration = clarify Presenton-today vs add-on (likely already-there), observability = scope to "scrapeable + non-blocking" not "instrument from scratch", chargeback = scope to "emit metrics" not "build ledger", LLM-approval-workflow = move to documentation rather than software (John, Mary, Amelia, Sally). (iv) Engineering complexity re-rated per guardrail #1: platform high→very-high, recipes medium→medium-high, cleanroom unchanged (John, Amelia). (v) Window of opportunity reframed: "Window closes when Microsoft Arc-connected Copilot reaches IL5 GA (12-24mo, tracked)" — replaces unsourced "18-24mo on-prem" estimate (Mary, Paige). (vi) Knowledge-base deferral made explicit: v1 use case = "decks where source material fits in prompt + uploaded files"; deep-internal-data decks excluded (Sally). (vii) JetBrains gap owned: REST + OpenAPI spec + Postman collection in v1 (Sally). (viii) "WE ARE the supply chain" kept as internal posture; customer-facing translation: "Today the customer integrates six unsigned upstream artifacts and owns the integration risk; with this, they integrate ONE signed artifact and we own the integration risk" (Paige). (ix) FedRAMP language reworded as factual constraint, not verdict (Paige). (x) Continuity plan extended to cover cleanroom + platform engineering, not just recipes (John). (xi) LLM-class taxonomy added: targets measured against named reference LLM class (Mary). (xii) Confidence qualifier added to "Copilot-class" claim — Buyer should know if v1 is 70%/85%/100% Copilot-equivalent (John). (xiii) Brand-compliance UX bands as v1 commitment (auto-fix high-confidence, batched-review mid-confidence, ignore low-confidence with strict-mode opt-in) — not deferred to a future spike (Sally). Core insight UNCHANGED and validated by all six agents: "The buyer is paying for a Copilot-class deck generator they're allowed to install."

## Jobs-to-be-Done

The classification's `referenceProductSubstituted: M365 Copilot for PowerPoint` is load-bearing — it explains why boring substitutes (Marp, python-pptx + Jinja2) lose despite trivially-better provenance, and what the AI part actually buys the customer. The JTBD has two gates that don't collapse:

**Buyer gate (signs the PO):**
> "Give me a turnkey, mirrorable AI deck generator that produces zero exfiltration paths and zero unreviewed dependencies, so I can approve it once and forget it."

**User gate (drives renewal):**
> "Turn my 40-page internal compliance/research/incident document into a 12-slide draft I'd rather edit than write from scratch, without leaving my secure workstation."

Buyer signs because of gate 1. Buyer renews because of gate 2 — if user output is unusable, ticket volume rises, head-of-research calls CISO, deal dies. **Anchor user-gate quality at "better than writing it by hand at 2 a.m." NOT at "M365 Copilot quality"** — anchoring on M365 loses; anchoring on the by-hand baseline is achievable with Presenton's actual capabilities.

The combined JTBD: **inference-at-the-edge of a security boundary** — long-form internal-document summarization into review-ready decks, where "at the edge" means: the boundary is the customer's air-gap, and our five-to-seven recipes (revised 2026-07-25) + Helm chart + clean-room reimpls + JFrog mirror integration are the receipts that prove the analyst is allowed to do this.

## Risk Register

| ID | Risk | Severity | Owner | Mitigation |
|---|---|---|---|---|
| R1 | `pptx-thumbnail-inject` is the one novel recipe — python-pptx has no thumbnail support and no conda-forge recipe synthesizes OOXML thumbnails today | High | recipe-maintainer | Spike story before estimate; pick rendering method (LibreOffice headless? python-pptx slide render? Pillow synthesis from rendered HTML PNG?) before sprint planning — gates entire image generation path (Winston, Amelia) |
| R2 | Upstream Presenton drift — 6 clean-room artifacts = 6 divergence vectors when upstream ships v2.0 | High | recipe-maintainer | `tests/drift/` online weekly cron + `.github/ISSUE_TEMPLATE/upstream-drift.md` auto-fired on breaking drift; path-watch on upstream `presenton-export/` triggers fixture-capture refresh (John, Sally) |
| R3 | **[REVISED 2026-07-25]** Microsoft ships a disconnected/on-prem Copilot-equivalent — JTBD collapses. **Old trigger falsified:** GCC/GCC-High/DoD/IL5 Copilot GA already happened (2025-2026) without collapsing the JTBD — those tiers are Azure Government cloud, not air-gapped. **Real trigger, already live:** Microsoft's own disconnected stack — Azure Local disconnected operations + Microsoft 365 Local + Foundry Local — GA'd worldwide 2026-02-24, explicitly targeting "government, healthcare, and finance" sovereign/data-residency buyers. Whether the Copilot deck-generation application layer rides on this infrastructure today is **unconfirmed**. | Existential, and no longer low-probability-future — the infrastructure precondition already shipped | strategic / steering | **Phase-0-blocking** (new exit criterion 6, shared with the memory-subsystem decision — see § Phase 0 Exit Criteria): confirm or rule out Copilot-deck-generation inclusion in Microsoft 365 Local disconnected before further build investment. Audit the existing RSS/keyword-watch mechanism (`on-prem`/`sovereign`/`air-gap`/`disconnected` keywords) — it appears to have missed the 2026-02-24 announcement; fix its channel coverage. Pivot plan unchanged: harvest the conda-forge recipes as standalone tools, retire the OCI image (Mary). |
| R4 | JFrog mirror security-review SLA blocks recipe submission for multi-week periods per recipe — 6 recipes × multi-week = months of supply-chain delay | High | platform-engineer + recipe-maintainer | Submit dependency manifest + air-gap build playbook as part of architecture sign-off (Q4 deliverable); parallelize submissions; pre-stage allowlist requests during step-03 |
| R5 | Microsoft Playwright CDN not mirrored on JFrog — `playwright-with-chromium` recipe can't fetch chrome-headless-shell at conda-build time | Medium | platform-engineer | Sub-question (h) — investigate during step-02b; fallback options: vendor binary into recipe source, use already-mirrored Chromium binary, or pivot to ungoogled-chromium |
| R6 | Fixture-capture phase boundary collapses — someone tries to refresh F from inside air-gap and discovers they can't | Medium | recipe-maintainer | Architectural-seam callout in test strategy; "fixture maintainer" role wears recipe-maintainer hat during online-capture phase (Sally); cadence policy = refresh on path-watch trigger, online-only |
| R7 | **[RESOLVED/REPLACED 2026-07-25]** PyMuPDF AGPL/Artifex dual-license blocks allowlist — **moot**: `template-style-extractor` is dropped (Decisions Log Q2, revised), and upstream Presenton's actual PDF dependency is `pdfplumber` (MIT), never PyMuPDF. New, smaller flag replacing this row: `psycopg` (LGPL-3.0-only) is a direct Presenton backend dependency, a different obligation class than the Apache/MIT-dominated rest of the stack. | Low | platform-engineer | Flag for buyer legal/compliance review alongside the JFrog allowlist gap analysis (Phase 0 exit 4); likely acceptable on most enterprise allowlists but not asserted without buyer confirmation. |
| R8 | JetBrains developer population blocked — VSIX is VS Code only, no v1 plugin | Low (v1 acceptable gap) | PM | Explicit docs-only fallback path documented; revisit in v2 if pilot-customer JetBrains share warrants the plugin work |
| R9 | **[NEW 2026-07-25]** Headless-Chromium sandbox model may conflict with OpenShift `restricted-v3`'s pod-level user-namespace isolation (`hostUsers: false`, default for new OCP installs). Chromium's conventional container workaround (`--no-sandbox`) may be required regardless, may be redundant-but-harmless under OCP's own isolation, or may need a different SCC (e.g. `nonroot-v2`) — not yet spiked against a real cluster. | Medium | platform-engineer | Named Phase-0/architecture-phase spike, not assumed away; `--no-sandbox` (if needed) must be an explicit, buyer-documented security decision, not a silent default. See technical research report § 2.2. |

## Test Strategy (4 Fixture Sets + Phase Boundary)

A clean-room reimpl of opaque upstream binaries is meaningless without a test oracle. We have four distinct fixture sets, each with a different purpose, audience, and network posture. Phase boundary: **fixture-capture happens online, fixture-consumption happens air-gapped** — this is an architectural seam that must be documented or it collapses on first refresh attempt.

### Fixture Set 1 — `tests/fixtures/upstream-baseline/v{N}/` (package-author, AC-FX-AUTHOR-*)
- Captured ONCE per upstream Presenton version while internet exists
- Anchors clean-room reimpls (`presenton-export-node`, `pptx-assembler`, `pptx-thumbnail-inject`)
- Air-gapped CI gate: AC-FX-AUTHOR-01 = byte/structurally equivalent (zip-entry order normalized, timestamps normalized); AC-FX-AUTHOR-02 = SSIM ≥ 0.99 for image equivalence (NOT byte-equivalence — pin tolerance explicitly)
- Capture script: `tests/capture_upstream.py --version <V> --output tests/fixtures/upstream-baseline/v<V>/` runs ONCE, commits artifacts, never re-runs in CI

### Fixture Set 2 — `tests/drift/` (recipe-maintainer, AC-FX-MAINT-*)
- Online weekly cron CI workflow (separate from air-gapped build pipeline)
- Detects drift between Set 1 and current upstream
- AC-FX-MAINT-01 = `recapture.py` runs against latest upstream and emits structured drift report (added/removed/changed fixtures, per-fixture diff summary)
- AC-FX-MAINT-02 = report distinguishes **breaking drift** (clean-room reimpl will diverge) from **benign drift** (upstream cosmetic change, our reimpl still semantically correct); categorization rules in `tests/drift/README.md`
- AC-FX-MAINT-03 = breaking drift triggers `.github/ISSUE_TEMPLATE/upstream-drift.md` auto-issue with diff body
- NOT a CI gate — failure files an issue, doesn't break the build

### Fixture Set 3 — `tests/operational/` (day-2 operator, AC-FX-DAY2-*)
- Shipped INSIDE the OCI image at `/opt/presenton/tests/`
- AC-FX-DAY2-01 = post-deploy smoke runs `minimal-deck.json` end-to-end, asserts output `.pptx` opens (zip integrity + minimum slide count); 60s budget
- AC-FX-DAY2-02 = credential-rotation runbook executes `rotation-check.sh` and verifies LLM endpoint reachable with new creds, no app restart
- AC-FX-DAY2-03 = mark-broken response — `check-pinned-deps.sh` reports flagged-broken deps via conda-forge repodata-patches; gates rollback decision
- Air-gapped runtime; no upstream comparison; purely "does this image still work"

### Fixture Set 4 — `tests/install/` (day-0 operator, AC-FX-INSTALL-*)
- Day-0 preflight; runs in target environment before first `oc apply`
- AC-FX-INSTALL-* = registry-reachable, secrets-present, manifest-validates, JFrog auth working, GGUF model present (if Tier-2/3)

### The Phase Boundary
Fixture Set 1 is **captured online** by the recipe-maintainer wearing the "fixture maintainer" hat; the rest of the pipeline is air-gapped. This is a documented architectural seam — sprint-planning must allocate an explicit online-capture session before air-gap CI can run. Cadence: path-watch on upstream `presenton-export/` triggers refresh; signed manifest committed per refresh; fixture-changelog written with every refresh explaining intentional vs unintentional drift.

## Competitive Context

| Substitute | Why it doesn't displace us |
|---|---|
| **Marp / Marpit** | Markdown-to-slides; no LLM; no long-form summarization. Gives provenance for free but fails capability gate. |
| **python-pptx + Jinja2 templates** | Stamping templates; no AI generation; no long-form summarization. Same as Marp — boring path with provenance, fails capability. |
| **Microsoft 365 Copilot for PowerPoint** | THE reference shape. Cloud-only (incl. GCC/GCC-High/DoD/IL5 — all Azure Government cloud, none air-gapped), no disconnected/on-prem SKU confirmed for the Copilot application layer itself. Buyer can't have it, which is *why this product exists*. **Existential threat, status REVISED 2026-07-25: Microsoft's own disconnected infrastructure stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local) already shipped 2026-02-24 — whether the Copilot deck-generation layer rides on it is unconfirmed** (Risk R3). |
| **SlidesGPT / Gamma / Tome** | SaaS, cloud-only. Air-gap-incompatible. Shape end-user expectations though — anchoring user-gate at "M365 quality" loses; anchor at "better than 2am-by-hand" instead. |
| **hugohe3/ppt-master** | AI IDE skill (Claude Code, Cursor, Copilot); requires external LLM API; air-gap-incompatible by design. Useful as architectural inspiration (SVG→DrawingML approach) but not a competitor in our deployment context. |

**Strategic positioning:** This product wins on the intersection: Copilot-class capability that survives security review. Strip either half (capability OR defensibility) and a cheaper substitute exists. The 6 conda-forge recipes + Chromium-vendoring + PyInstaller-replacement + JFrog mirror integration are the price of admission to that intersection — they're what proves the buyer is *allowed* to install Copilot-equivalent capability inside the perimeter.

## Open Questions

*All four gating questions resolved. Sub-questions a–j land during step-02b/03 (architecture/sprint planning). Items 5–12 below are tracking-only.*

### Sub-questions surfaced from Q3 (resolve during step-02b/03)
- **a.** ✅ **Resolved (Verdict B+), re-verified 2026-07-25.** Presenton routes all LLM traffic through `llmai` (Apache-licensed unified provider abstraction), now pinned `==0.2.8` (was `0.2.2` at original drafting — upstream re-pins fast, six releases in the interval; re-verify again at submission time). First-class `LLM=custom` mode with `CUSTOM_LLM_URL` + `CUSTOM_LLM_API_KEY` env vars covers Tier-1 (internal proxy), Tier-2 (llama.cpp sidecar), and dev path (Copilot bridge) without any source patches — confirmed still present in `utils/get_env.py` (`get_custom_llm_url_env`/`get_custom_llm_api_key_env`). Optional ~3 LOC docker-compose.yml UX polish to forward `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL` explicitly. New conda-forge dep: `llmai` (recipe submission needed — confirmed absent from conda-forge as of 2026-07-25 via `api.anaconda.org` lookup). Evidence: `servers/fastapi/utils/llm_config.py`, `servers/fastapi/utils/get_env.py`, `servers/fastapi/pyproject.toml`.
- **b.** Existing `copilot-bridge` extension VSIX packaging — is Story 12 (CI builds `.vsix` on tag) implemented yet, or still TODO?
- **c.** PyCharm support depth — confirmed docs-only for v1; full JetBrains plugin deferred to v2.
- **d.** Tier-2 model pick — Qwen 2.5 7B Q4_K_M vs Llama 3.2 3B Q4 vs Phi-3.5 — needs a small bench-off against Presenton's actual prompt templates; ALSO subject to mirror allowlist (sub-question g).

### Sub-questions surfaced from Q4 (resolve during step-02b/03)
- **e.** Internal JFrog conda-forge mirror — what subset is currently mirrored, and what is the SLA for adding new packages? (Drives feasibility timing for net-new recipes.)
- **f.** Internal JFrog npm registry mirror — full transitive coverage or curated? (Drives feasibility of `presenton-export-node` and the Node export bundle.)
- **g.** Approved GGUF models on the HuggingFace mirror — what's the current allowlist? (Drives Tier-2 default pick; may force a different model than Qwen 2.5 7B if it's not approved.)
- **h.** Microsoft Playwright CDN — mirrored on JFrog, or does `playwright-with-chromium` recipe need to vendor `chrome-headless-shell` into the recipe source / use an alternative Chromium binary?
- **i.** Security-review SLA for newly-authored conda-forge recipes added to the internal mirror — drives delivery timeline for `presenton-export-node`, `pptx-assembler`, `pptx-thumbnail-inject`, `playwright-with-chromium`, `llmai` (and `mem0ai`/`fastembed-vectorstore` if Phase 0 exit 6 adds them). **[REVISED 2026-07-25]** `template-style-extractor` removed from this list — dropped from scope, see Decisions Log Q2.
- **j.** ✅ **Resolved/moot 2026-07-25.** PyMuPDF licensing question no longer applies — `template-style-extractor` is dropped, and upstream Presenton's actual PDF dependency is `pdfplumber` (MIT), confirmed via live code search, never PyMuPDF. See Risk R7 (revised).
- **k. [NEW 2026-07-25]** Memory/RAG subsystem scope — does Phase 0 add `mem0ai` + `fastembed-vectorstore` as two more conda-forge recipes, or feature-drop the memory/chat-history subsystem for v1? Contingent on confirming whether the import graph can be cleanly disabled without a Presenton-side source patch (not yet verified — env-var accessors exist in `utils/get_env.py` but a full no-op path was not traced). This is Phase 0 exit criterion 6 (see below).

## Success Criteria

> **Reader's note (v5, 2026-05-01):** Three phrases in the Executive Summary, Differentiator, and Risk Register R3 reference "Copilot-class capability" / "M365 parity." These framings are superseded by the v5 scope decision (long-form-document summarization into review-ready decks; M365 retained only for procurement-recognition). Final wording lands in step-11 polish; the substance below already reflects the v5 scope.
>
> **Reader's note (v6, 2026-07-25):** See the Revision Log at the top of this document for the full delta trail. In brief: `template-style-extractor` is dropped from v1 (Decisions Log Q2, superseded); Risk R3's trigger is corrected and escalated to a Phase-0-blocking check (new exit criterion 6); Risk R7 is resolved and replaced; `llmai` is re-pinned to `0.2.8`; a new Risk R9 names an OpenShift-Chromium-sandbox interaction spike; recipe count throughout this document is now "five confirmed, plus up to two pending Phase-0 exit 6," not a fixed six.

The two-gate JTBD (buyer/user) drives a two-axis success model: one axis tracks "survives security review" (buyer-gate), the other tracks "long-form-document summarization into review-ready decks" capability (user-gate). Either axis collapsing kills the product. Phase 0 must close before v1 build is unblocked.

### User Success

The analyst (renewal-driving persona) wins when:

- **First-draft latency:** ≤30 min P95 from "deck request" to **first-slide-renderable**. The clock starts at *prompt-submit* and stops when the thumbnail strip is populated and slide 1 is paintable. Editorial judgment time (analyst scrolling through and deciding "I'd rather edit than write from scratch") is explicitly outside the budget.
- **In-flight stall recovery contract:** If no token/slide progress for >45s, the UI surfaces *"Generation paused — [Resume from slide N] [Restart] [Save partial draft]."* A silent 5-minute hang at minute 8 burns the 30-min P95 and the user's trust simultaneously.
- **Per-refinement latency:** ≤10s P95 on Tier-1 LLM. Tier-2 llama.cpp is async/batch UX and is NOT a quality-gated success criterion.
- **Quality anchor:** Output beats *"writing it by hand at 2 a.m."* Sole anchor; no M365 calibration.
- **Capability rubric (buyer-facing, JTBD-anchored):** Covers **12 deck archetypes** validated during Phase 0 by the pilot's compliance team. Initial seed list (refined with pilot during Phase 0):
  1. Quarterly board update / executive summary
  2. Incident postmortem brief
  3. Compliance review / audit response
  4. Research findings / threat-intel briefing
  5. Project status / program review
  6. Risk assessment / risk register summary
  7. Budget proposal / resource ask
  8. Vendor evaluation / make-vs-buy
  9. Architecture review / technical proposal
  10. Training / readiness brief
  11. Stakeholder/customer presentation
  12. Regulatory submission summary
- **First-run calibration (in-product, replaces lost M365 anchor):** *"Pick the archetype closest to your deck; we'll get you to a reviewable draft faster than starting from a blank slide at 2 a.m."* Tied to the 12-archetype rubric. Sets analyst expectation in the moment of first prompt.
- **Velocity signal:** Second deck takes ≤50% wall-clock time of the first.
- **Canonical task shape:** 40-page internal compliance/research/incident document → 12-slide draft.
- **Measurement protocol (air-gap-honest):** All latency and adoption metrics scraped at the customer's own Prometheus `/metrics` endpoint inside the perimeter. Customer self-reports aggregates at customer cadence and discretion. We do not see raw telemetry.

### Business Success

The buyer (CISO/platform/procurement) wins when:

- **Pilot acceptance gate (MVP):** One pilot customer signs the acceptance checklist on Tier-1 LLM configuration. The checklist requires ALL of:
  - `AC-FX-INSTALL-*` + `AC-FX-DAY2-*` green in customer's environment.
  - Pilot generates ≥10 production-shape decks from real internal documents over ≥2 weeks.
  - **AC-PILOT-001 (user-gate behavioral metric):** Pilot users demonstrate **"edit-not-rewrite" behavior on ≥60% of generated decks**, measured by:
    - (a) Edit-distance from generated draft to final deck stays below threshold X (set in Phase 0), OR
    - (b) Post-session survey: user-reported "kept the structure, edited content" on ≥60% of sessions.
    Without this, the checklist can pass on task-completion-time while users silently rewrite from scratch — which kills renewal regardless of acceptance signature.
  - **Three-signatory signoff with backup-signatory clause:**
    - **CISO or platform-owner** (deployment + security gate).
    - **Named end-user lead** (user-gate signatory) attesting in writing that ≥3 of the 10 decks were used in actual customer/board/regulatory deliverables — not internal demos.
    - **At deployment go-live, each signatory designates a backup.** If signatory turnover happens during the 12-week window, backup has 30-day signoff window AND ONE 6-week extension is available before triggering Phase 0 reset. Caps personnel-risk impact at 18 weeks total.
  - **Backup-signatory continuity kit:**
    - Backup auto-receives **read-access to running deck-quality corpus** (the 10 production-shape decks as they accrue).
    - Weekly 5-minute "what changed" digest: prompts authored, ledger entries opened/closed, brand-token version deltas.
    - **30-day signoff clock starts on *handoff-acknowledged*, NOT on promotion-effective.** Backup inherits a pre-warmed dossier, not a cold ledger.
- **Pilot acceptance failure branch:** If no acceptance achieved within 12 weeks of pilot deployment go-live (or 18 weeks if extension invoked under backup-signatory clause), the program returns to Phase 0 scoping rather than advancing to Phase 1.
  - **Phase 0 reset mechanics:** Default re-opens **exit 1** (build-complete-hold) if pilot's GRC model-source policy differs from initial assumption; **carry-forward exits** (sunk-cost-correct): exits 3 (fixture-capture v1) and 4 (JFrog allowlist gap analysis) remain valid unless explicitly invalidated by the new pilot's environment. **Re-entry criterion:** new pilot identified + Phase 0 re-scope timeline filed before Phase 1 work resumes.
- **Second-pilot validation milestone (between MVP and Growth):** 2 pilots accepted under the full checklist, where pilot #2's parent organization is different from pilot #1's AND uses a different Tier-1 endpoint shape (e.g., #1 Gemini-on-prem, #2 Azure OpenAI disconnected or Claude on-prem). If pilot #2 not in production within 12 months of pilot #1's acceptance signoff, formally re-evaluate the procurement-driven adoption thesis (strategic-review milestone).
- **Operational watch (yearly + gate-coupled + always-on RSS):**
  - **Yearly cadence:** annual review of Microsoft Arc-connected/IL5/disconnected Copilot announcements; alert thresholds defined in Phase 0; auto-trigger Redmond-contingency review if any announcement crosses an alert threshold. **[REVISED 2026-07-25]** This cadence appears to have missed the 2026-02-24 Azure Local disconnected operations / Microsoft 365 Local / Foundry Local GA announcement — channel coverage audit is part of Phase 0 exit criterion 6, not deferred to the next yearly review.
  - **At every exit-criteria gate event** (Phase 0 close, pilot #1 acceptance signoff, pilot #2 acceptance signoff, Pilot → GA reviews): auto-trigger Redmond-contingency review BEFORE signoff on any gate.
  - **Always-on lightweight trigger:** RSS/Atom subscription to Microsoft 365 roadmap + Copilot blog with keyword filter (`on-prem`, `sovereign`, `air-gap`, `disconnected`, `GCC-High` paired with `Copilot`). Hit → escalate to gate review out-of-cycle, regardless of yearly cadence. Closes the multi-month blindside window between gate events.
  - **Analyst-facing UX during gate review:** non-blocking editor banner *"Platform review in progress — your work is unaffected; signoff packet will note status."* Surfaces the operator concern at signoff time without blindsiding the analyst.
- **Adoption ramp (Growth):** 100 pilot customers via procurement pipeline (procurement-driven, not sales-driven).
- **Procurement gate (binary chain visible):** All confirmed recipes (five, plus up to two more pending Phase-0 exit 6 — revised 2026-07-25) upstream-merged on conda-forge → matching feedstocks producing artifacts → artifacts landed on customer's JFrog Artifactory mirror → OCI image landed on customer's image registry. Each link separately-trackable.
- **Procurement SLA (measured-against, not owned):** Security-review cycle completion time, set by JFrog allowlist + customer GRC.
- **Provenance simplification:** One signed OCI artifact + one SBOM + one cosign attestation replaces five-to-seven unsigned upstream Python/Node packages (revised 2026-07-25, was six).
- **Window of opportunity [REVISED 2026-07-25]:** Capture pilot adoption before Microsoft's disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, already GA 2026-02-24) ships Copilot-equivalent deck generation on top of it — status unconfirmed, Phase-0-blocking (exit criterion 6). The old "12-24mo to IL5 GA" framing is retired; IL5 GA already happened without ending this window, because IL5 is cloud, not air-gapped.

### Technical Success

- **Recipe quality (all confirmed recipes — five, plus up to two more pending Phase-0 exit 6; revised 2026-07-25, was "all six"):** Lint-clean (`conda-smithy` + `rattler-build lint`), deterministic builds, rerender-survivable across one full conda-forge global pinning bump.
- **Fixture acceptance (FIVE sets pass):**
  - `AC-FX-AUTHOR-01/02`: byte/structurally equivalent + SSIM ≥ 0.99.
  - `AC-FX-MAINT-01..03`: weekly drift detection runs, breaking-vs-benign categorization, auto-issues on breaking drift.
  - `AC-FX-DAY2-01..03`: 60s smoke-deck budget; cred rotation without app restart; mark-broken response on pinned deps.
  - `AC-FX-INSTALL-*`: day-0 preflight green.
  - `AC-FX-DRIFT-01..04` (drift-harness self-tests):
    - `AC-FX-DRIFT-01`: classifier categorizes 4 synthetic-release fixtures correctly (benign patch / breaking dep / breaking API / no-op rerelease).
    - **`AC-FX-DRIFT-02a` (CI-gated, deterministic):** Pattern-match against benign-drift allowlist. Categories that pass without firing an issue:
      - `*.md` and `CHANGELOG*` files (any change)
      - `*.css` class-rename-only diffs (AST-compare via PostCSS; no JSX/TSX behavior change in matched component tree)
      - `package.json` version bumps within semver-minor
      Files: `tests/drift/benign_filter.py` + `tests/drift/benign_allowlist.yaml`.
    - **`AC-FX-DRIFT-02b` (human-gated, 48hr SLA):** Fixture-only changes + ambiguous CSS/JSX edits route to maintainer review queue. Files: `tests/drift/review_queue/` + GitHub issue template `human-review-required.md`. Drift harness fires P1 issue on queue depth >5 OR oldest-item age >72hr.
    - `AC-FX-DRIFT-03`: drift-harness step failure exits 0 from cron job; emits `::warning::` annotation.
    - `AC-FX-DRIFT-04`: `.github/workflows/drift-cron.yml` includes `if: github.event_name == 'schedule'` guard + `continue-on-error: true`.
- **Internal proxy benchmark (split into gating + informational):**
  - **`AC-PROXY-001a` (CI-gating, with full hardware-class spec):**
    - **CI-side:** CI pinned to `ubuntu-22.04`, declares `hwclass-ci-x86_64-generic`. Determinism check (fixed seed + temp=0 + fixed prompt → byte-equal output) runs within this class only. Documented in `tests/proxy/determinism/HARDWARE_CLASS.md`.
    - **Customer-side boundary contract:** When customer hardware class falls outside CI matrix, recipe behavior is **fail-closed by default** — refuses to load with clear *"unverified hardware class: <detected> not in [hwclass-ci-x86_64-generic, ...]"* error. Opt-in to **degraded-determinism mode** via `PRESENTON_HW_CLASS_OVERRIDE=accept-degraded` env var; this loads with logged warning + degraded-determinism flag in output manifest.
    - **Production-deployment declaration:** Each pilot's `pilot-acceptance-checklist.yaml` includes `hardware_class: <id>`. CI matrix grows as pilots register classes.
    File: `tests/proxy/determinism/`.
  - **`AC-PROXY-001b` (informational, non-gating):** ROUGE-L/BLEU drift report posted as PR comment; threshold-alert at >0.05 deviation from rolling 30-day baseline. File: `tests/proxy/quality-drift/`.
- **Supply-chain provenance (MVP gates — all required):**
  - **SBOM** emitted in CycloneDX (primary) + SPDX (exportable secondary), regenerated per build, attached to OCI image.
  - **Signed-image attestation** via cosign / sigstore-equivalent.
  - **`/metrics` schema artifact** — versioned schema doc shipped with the Helm chart, locking metric names, label keys, histogram buckets, cardinality bounds. First-class deliverable, not a capability claim.
- **CVE-response capability:** Rebuild-and-resign within 14 days P95, *conditional on JFrog allowlist SLA ≤48h AND maintainer staffing tier*.
- **Drift-detection harness:** Weekly cron CI workflow runs against latest upstream Presenton; files `.github/ISSUE_TEMPLATE/upstream-drift.md` on breaking drift; never breaks the build (verified by `AC-FX-DRIFT-03/04`).
- **Hard constraints (no regression):** Zero LibreOffice in runtime, zero non-conda-forge packages, zero non-pixi build steps, zero external CDN access at build or runtime.

### Measurable Outcomes

| Metric | Target | Tier | Source / Note |
|---|---|---|---|
| Time-to-first-deck (P95) | ≤30 min, prompt-submit → first-slide-renderable | MVP | Customer-internal Prometheus scrape |
| Per-refinement latency on Tier-1 (P95) | ≤10s | MVP | Customer-internal Prometheus scrape |
| Stall recovery surfaced | >45s no progress → recovery dialog | MVP | UX requirement |
| Deck-archetype coverage (buyer-facing) | 12 of 12 (Phase-0-validated by pilot's compliance team) | MVP | User-gate, JTBD-anchored |
| `AC-PILOT-001` edit-not-rewrite behavior | ≥60% of decks | MVP | User-gate; renewal signal |
| `AC-PROXY-001a` deterministic-output equivalence | byte/diff-clean, fixed seed + temp=0; per-hardware-class | MVP CI gate | Hardware-class-scoped; fail-closed default |
| `AC-PROXY-001b` ROUGE-L/BLEU drift report | informational; PR comment; alert >0.05 deviation | MVP non-gating | Reports, doesn't block |
| Image equivalence SSIM | ≥0.99 | MVP | AC-FX-AUTHOR-02 |
| `AC-FX-DRIFT-01..04` pass | all 4 ACs green; benign-drift filter active (02a CI + 02b human queue) | MVP | 5th fixture set |
| Day-2 smoke-deck budget | ≤60s | MVP | AC-FX-DAY2-01 |
| CVE rebuild-and-resign (P95) | ≤14 days | MVP capability; SLO conditional | Risk R4 / JFrog SLA |
| Recipe-set landed on JFrog mirror (chain) | yes/no across 4 chain links | MVP gate | Buyer-gate |
| Signed-image attestation present | yes/no (binary) | MVP gate | cosign |
| `/metrics` schema artifact shipped | yes/no (versioned) | MVP gate | Helm chart deliverable |
| Pilot #1 acceptance signoff | 3-signatory + backup-clause; ≤12wk (or 18wk with extension) from go-live | MVP | Reset to Phase 0 on miss |
| Microsoft watch cadence | yearly + at every exit-criteria gate + always-on RSS keyword filter | MVP | Replaces ad-hoc R3 monitoring |
| Pilot #2 validation (different org + different Tier-1) | 2 pilots accepted before Growth | MVP→Growth boundary | Strategic re-eval at 12mo |
| Pilot customers in production | 100 | Growth | Procurement-driven |
| Pilot → GA: deck volume × duration × P0 | ≥30 decks/mo × 3mo × 0 P0 | Growth gate (a) | Q7(a) |
| Pilot → GA: drift-clean window | 1 upstream release OR 6mo, whichever first | Growth gate (b) | Q7(b) |
| Pilot → GA: CVE cycle exercised | ≥1 e2e (real OR synthetic drill) meeting 14d P95 | Growth gate (c) | Q7(c) |
| Pilot → GA: procurement commitment OR NULL-case substitute | (i) ≥1 pilot multi-year commitment surviving Microsoft announcement, OR (ii) NULL-case requires substitute (LOI / analyst report / RFP language match) | Growth gate (d) | Engineering baseline alone does NOT satisfy |

**P0 incident definition** (used in Pilot→GA gate (a)):
- (a) Data exfiltrated outside customer perimeter.
- (b) Deck output corrupted/unrecoverable.
- (c) Image deployment unable to start.
- (d) LLM provider integration fails for entire user population for >1 hour.

### Phase 0 Exit Criteria (gates v1 build kickoff)

Phase 0 has a critical-path long-pole (exit 1, "build-complete-hold"). Exits 2 and 3 are gated by exit 1. Exits 4, 5, and 6 run independently. **6 exits total (revised 2026-07-25, was 5 — see exit 6 below).** Exit 6 is the highest-urgency of the independent exits: it resolves whether the product's core differentiator still holds (Risk R3, revised) and materially changes the recipe-count/scope math (Risk R2, revised) — start it first among the independents, don't let it queue behind exits 4-5.

**Phase 0a (critical path — build-complete-hold):**

1. **Build-complete-hold** *(named for CISO clarity — avoids "baseline" which reads as security-baseline. Inline gloss: **build-complete-hold = recipe builds and tests pass; procurement-signal not yet sufficient to justify pilot scoping**.)*
   All of:
   - GGUF model family (Qwen / Llama / Mistral) and quantization tier (Q4_K_M / Q5 / Q6) chosen.
   - Bench methodology documented using public datasets (GovReport, BillSum for long-form summarization; 12-archetype rubric coverage demonstration).
   - **Bench-archetype coverage floor:** Methodology specifies which of the 12 archetypes GovReport+BillSum exercise; **coverage floor ≥8/12 archetypes** must have at least one public-dataset proxy task. **Uncovered archetypes named explicitly as Phase-1 deferred risk** in the bench methodology document — they are not silently absent.
   - Bench fixtures committed.
   - **Source-pathway commitment with alt-source clause:** if customer GRC bans HuggingFace as a model source, alternative paths satisfy this exit:
     - (a) Customer-supplied GGUF from approved internal registry.
     - (b) Pre-vetted internal model registry path.
     - (c) Customer-licensed model converted to GGUF via approved tooling.
   - Specific model+quant LOCK happens at customer-mirror-allowlist resolution time, NOT at Phase 0 close.
   - This is the long-pole; exits 2 and 3 cannot begin until exit 1 closes.

**Phase 0b (gated by exit 1):**

2. **Tier-1 reference LLM class chosen for methodology committal** — Named class against which user-success metrics are evaluated. Customer's actual Tier-1 endpoint may be a different specific endpoint within the class.
3. **Fixture-capture v1 committed** — `tests/fixtures/upstream-baseline/v1/` populated and signed; capture script run against locked upstream Presenton tag; fixture-changelog initialized.

**Phase 0c (independent — exit 4):**

4. **JFrog allowlist gap analysis filed** — Per-dependency gap report (conda + npm + GGUF) covering: which packages already mirrored, which need allowlist requests, which have licensing blockers (e.g., `psycopg` LGPL-3.0-only — Risk R7, revised 2026-07-25), expected security-review SLA per gap.

**Phase 0d (independent — exit 5):**

5. **Capability Claim Statement committed** — single buyer-facing sentence in canonical form:
   > *"Generates [artifact-class] at [public-bench-score] quality, fully on-prem, with [SLA]."*
   Bound to a content-review checkpoint that **explicitly forbids cloud-product comparisons** (no "Copilot-class," no parity numbers, no SaaS-equivalent framing). Required deliverable before Phase 0 close. Without it, every field conversation re-litigates positioning ad-hoc and competitors define us by negation.

**Phase 0e (independent, highest-urgency — exit 6, NEW 2026-07-25):**

6. **Microsoft disconnected-stack verification + memory-subsystem scope decision committed** — two coupled sub-items, both required:
   - **(a) Redmond-contingency check.** Confirm or rule out whether Microsoft's disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, GA worldwide 2026-02-24) includes, or has an announced roadmap to include, Copilot-for-PowerPoint-equivalent deck generation. This directly determines Risk R3's status (materialized / partially materialized / infrastructure-only). Also audit the existing RSS/keyword-watch mechanism's channel coverage — it appears to have missed the 2026-02-24 announcement.
   - **(b) Memory-subsystem scope decision.** Decide whether `mem0ai` + `fastembed-vectorstore` (unconditional Presenton dependencies, neither on conda-forge) become two additional v1 recipes, or the memory/chat-history feature is documented as dropped for v1 — contingent on confirming a clean no-op import path if dropped (not yet verified; may require a Presenton-side patch, which changes the maintenance-burden model this PRD doesn't currently carry for any other component).
   Required before Phase 0 close, alongside exits 1-5. Given exit 6(a)'s bearing on whether the product's core differentiator still holds, this exit should be actioned first among the independent exits (4, 5, 6), not queued last because it's numbered last.

## Product Scope

### MVP — Minimum Viable Product

Ships when ALL of the following are simultaneously true:

- All confirmed conda-forge recipes lint-clean and **upstream-merged** (revised 2026-07-25 — was "all six," now five confirmed plus the Phase-0 exit-6 decision): `presenton-export-node`, `pptx-assembler`, `pptx-thumbnail-inject`, `playwright-with-chromium`, `llmai` — plus `mem0ai` and `fastembed-vectorstore` if Phase 0 exit 6(b) decides to add them rather than feature-drop the memory subsystem. `template-style-extractor` is dropped (see Decisions Log Q2, revised) — not part of this gate.
- OCI image builds reproducibly via pixi + pixitainer with zero external CDN access.
- All FIVE fixture sets pass: `AC-FX-INSTALL/DAY2/AUTHOR/MAINT/DRIFT`.
- `AC-PROXY-001a` (deterministic-output equivalence, hardware-class-scoped) passes in CI.
- `AC-PILOT-001` (edit-not-rewrite ≥60%) passes in pilot environment.
- Helm chart / kustomize overlays deploy on OCP and consume any OpenAI-compatible Tier-1 endpoint via env vars.
- SBOM (CycloneDX + SPDX) + signed-image cosign attestation + versioned `/metrics` schema artifact attached to/shipped with image.
- **Pilot #1 acceptance gate cleared:** 3-signatory acceptance checklist (with backup-signatory clause + continuity kit) on Tier-1 LLM. If no acceptance within 12 weeks of go-live (or 18 weeks if extension invoked), program returns to Phase 0 scoping per Phase 0 reset mechanics.
- Phase 0 exit criteria all met (5 exits, phased a→b→c+d).
- Buyer-facing capability rubric: 12 of 12 deck archetypes covered (Phase-0-validated by pilot's compliance team).
- Capability Claim Statement committed and approved through content-review checkpoint.
- **Tier-2 llama.cpp sidecar shipped as architectural capability — not quality-gated.**
- Operational Microsoft-watch active (yearly + gate-coupled + always-on RSS).

> **Tier-2 framing note:** Tier-2 llama.cpp ships as a *deployable option at customer discretion*. We do not claim a quality bar against it; customers selecting Tier-2 own their own quality validation. Removing it would force customers wanting offline operation to fork the recipe — a worse outcome.

### Growth Features (Post-MVP)

Tier flips when ALL of the following are met:

**Pilot → GA conjunction (4 criteria):**
- **(a)** ≥30 decks/mo × 3mo × 0 P0 incidents.
- **(b)** Drift-clean for 1 upstream Presenton release OR 6 calendar months, whichever first.
- **(c)** CVE drill (real OR synthetic) end-to-end meeting 14d P95.
- **(d)** Procurement-commitment OR NULL-case **substitutes** (no longer auto-satisfy):
  - (i) ≥1 pilot has executed multi-year purchase commitment OR budget line-item allocation that survives a Microsoft on-prem-Copilot announcement, OR
  - (ii) **NULL-case substitutes** (when no qualifying Microsoft announcement during window) — require ONE of:
    - (ii-a) Second pilot LOI from independent customer, OR
    - (ii-b) Analyst report (Gartner / Forrester) citing the category, OR
    - (ii-c) RFP language from prospect matching capability description.
  - **Engineering baseline alone does NOT satisfy (d).** Procurement-recognition needs external signal, not internal trajectory.

**Plus second-pilot validation milestone:** 2 pilots accepted under the full checklist, with pilot #2's parent org different from pilot #1's AND a different Tier-1 endpoint shape. Strategic-review milestone if pilot #2 not in production within 12 months of pilot #1's acceptance.

**Growth scope:**

- **Named commercial-grade Tier-1 endpoint shape validated** — internally-hosted Gemini is the reference. Equivalent shapes (Anthropic Claude on-prem, Azure OpenAI disconnected) substitute one-for-one.
- **Brand-compliance enforcement UX bands:**
  - **"Auto-applied (reviewable)"** band: system applies high-confidence corrections without blocking; persistent compliance-ledger chip ("N brand corrections applied — view") in editor chrome until acknowledged or exported with deck. Default is passive disclosure, not silence. Strict-mode opt-in stays.
  - **"Batched-review"** band (mid-confidence): user reviews queued corrections in batch dialog before apply.
  - **"Ignore"** band (low-confidence): no action; surfaced only in strict mode.
- **JetBrains REST one-pager** + Postman collection.
- **Adoption ramp:** 100 pilot customers via procurement pipeline.
- **Compliance posture upgrades (nice-to-have):** FIPS-mode operation; audit log shape + retention period; WCAG AA/AAA on analyst UI.

### Vision (Future)

- `chromium` upstreamed to conda-forge directly (replaces vendored `chrome-headless-shell` in `playwright-with-chromium`); resolves staged-recipes#21431.
- **SVG→DrawingML fidelity tier** — render slides to SVG via Playwright, convert to native PPTX shapes (option-C-equivalent without HTML→shape lossiness). Net-new conda-forge work; no SVG→DrawingML library exists today. Inspired by `hugohe3/ppt-master` architecture.
- **Full JetBrains plugin** — replaces docs-only one-pager.
- **Knowledge-base integration** — decks where source material does NOT fit in prompt + uploaded files. Currently held against customer pressure as a v1 boundary; revisited at Vision tier.
- **Upstream `presenton-export` source acquired** — Presenton team open-sources the export bundle build pipeline; vendored `presenton-export-node` retired in favor of canonical upstream.
