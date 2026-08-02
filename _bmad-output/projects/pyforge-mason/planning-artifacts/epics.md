---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/prds/prd-pyforge-mason-2026-07-25/prd.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/briefs/brief-pyforge-mason-2026-07-25/brief.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/briefs/brief-pyforge-mason-2026-07-25/addendum.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/research/domain-packaging-automation-tooling-research-2026-07-25.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/research/technical-mason-cli-seam-research-2026-07-25.md"
project_name: pyforge-mason
epicCount: 5
storyCount: 38
frCount: 50
status: complete
revision: 2
revisionNote: "r2 tracks PRD revision 2 (adversarial-review fixes). Added S-1.10 (config+logging), S-3.9 (ship verb + TestPyPI rehearsal), S-5.6 removed in favour of folding FR-47 into S-5.5; corrected S-3.6, S-5.1, S-5.2, S-2.2 for the D-10/D-12/FR-44/FR-45 resolutions."
updated: '2026-08-02'
currency_review: "Reviewed 2026-08-02 — the architecture spine's AD-13/AD-15/AD-25/AD-26 now bind FR-47..FR-50, matching this epics doc's own r2 revision (S-1.10, S-3.9, S-5.5), which already fully covered FR-47..FR-50 (see the FR coverage table above). Re-checked and confirmed current; no story changes made."
---

# pyforge-mason — Epic Breakdown

## Overview

Decomposition of Mason's PRD (50 FRs / 16 NFRs / 13 D-records) and architecture spine (16 ADs,
ports-and-adapters with a knowledge-free core) into **5 epics and 38 stories**.

**dist** `pyforge-mason` · **module** `pyforge.mason` · **CLI** `mason`

Effort scale: XS (≤4 hr), S (½–1 day), M (1–3 days), L (3–5 days). Story IDs use `S-<epic>.<seq>`.

**Critical-path story: S-2.2 (the seam guard).** It lands the FR-42/FR-43 meta-tests immediately
after the CFE adapter is born, so recipe knowledge cannot leak inward during the four epics that
follow. Deferring it to the end would repeat the `pyforge-atlas` outcome, where intent alone failed
to prevent a second implementation.

## Requirements Inventory

### Functional Requirements covered

All 50 FRs (FR-1 through FR-50). No deferrals.

### Non-Functional Requirements covered

All 16 NFRs (NFR-1 through NFR-16). NFR enforcement is distributed: NFR-1/NFR-16 in S-2.1,
NFR-2 in S-2.3 and S-3.4, NFR-3/NFR-4 in S-1.4, NFR-7/NFR-10 in S-3.1, NFR-8 in S-3.7,
NFR-9 in S-3.3, NFR-11 in S-1.1, NFR-13 in S-1.9, NFR-14 in S-1.3, NFR-15 in S-1.2,
NFR-2 also in S-1.10 (logging).
NFR-5/NFR-6/NFR-12 are cross-cutting constraints verified in S-5.1 and S-5.3.

### Architecture Decisions covered

All 16 ADs flow into specific stories:

| AD | Owning story/stories |
|---|---|
| AD-1 knowledge-free core | S-2.2 |
| AD-2 dependency direction | S-1.2, S-2.2 |
| AD-3 sole CFE caller | S-2.1, S-2.2 |
| AD-4 subprocess/typed/timed | S-2.1 |
| AD-5 pure resolution | S-1.5, S-1.6 |
| AD-6 capability tiers | S-1.7, S-3.6, S-5.1 |
| AD-7 one error taxonomy | S-1.3 |
| AD-8 core returns data | S-1.4 |
| AD-9 ShipReceipt shape | S-2.9, S-3.7 |
| AD-10 idempotence by interrogation | S-3.7 |
| AD-11 one owner per operation | S-3.6 |
| AD-12 engine protocol | S-3.1, S-4.1 |
| AD-13 no config file | S-1.2, S-1.10 |
| AD-14 credential blindness | S-2.3, S-3.4 |
| AD-15 CFE surface read-only | S-5.2 |
| AD-16 fake CFE root | S-1.9 |

### FR Coverage Map

| FR | Epic | Story | Capability |
|---|---|---|---|
| FR-1 | 2 | S-2.1 | Single delegation point |
| FR-2 | 1 | S-1.5 | CFE root resolution chain |
| FR-3 | 1 | S-1.6 | Interpreter selection |
| FR-4 | 2 | S-2.1 | Typed invocation result |
| FR-5 | 1 | S-1.7 | Degradation |
| FR-6 | 2 | S-2.3 | Credential isolation |
| FR-7 | 2 | S-2.4 | `mason recipe new` |
| FR-8 | 2 | S-2.5 | `mason recipe validate` |
| FR-9 | 2 | S-2.6 | `mason recipe build` |
| FR-10 | 2 | S-2.7 | `mason recipe diagnose` |
| FR-11 | 2 | S-2.8 | `mason recipe optimize` |
| FR-12 | 2 | S-2.8 | `mason recipe scan` |
| FR-13 | 2 | S-2.9 | `mason recipe submit` |
| FR-14 | 2 | S-2.10 | `mason recipe update` |
| FR-15 | 3 | S-3.2 | `mason package build` |
| FR-16 | 3 | S-3.3, S-3.9 | Ship verb + target vocabulary |
| FR-17 | 3 | S-3.7 | Asymmetric ship reporting |
| FR-18 | 3 | S-3.7 | Partial-failure semantics |
| FR-19 | 3 | S-3.3 | Dry-run by default |
| FR-20 | 3 | S-3.4 | Credential handling |
| FR-21 | 3 | S-3.2 | `--target` project shapes |
| FR-22 | 3 | S-3.2 | Version consistency check |
| FR-23 | 3 | S-3.6 | Recipe sourcing for conda-forge |
| FR-24 | 3 | S-3.8 | Self-hosting |
| FR-25 | 4 | S-4.3 | `mason environment lock` |
| FR-26 | 4 | S-4.2 | Manifest discovery |
| FR-27 | 4 | S-4.3 | Platform targeting |
| FR-28 | 4 | S-4.4 | Lock verification |
| FR-29 | 4 | S-4.1 | Engine reporting |
| FR-30 | 1 | S-1.2 | Noun-verb structure |
| FR-31 | 1 | S-1.4 | Dual output format |
| FR-32 | 1 | S-1.3 | Exit-code contract |
| FR-33 | 1 | S-1.3 | Structured errors |
| FR-34 | 1 | S-1.8 | `mason doctor` |
| FR-35 | 1 | S-1.2 | Global flags |
| FR-36 | 1 | S-1.1 | Workspace member layout |
| FR-37 | 1 | S-1.1 | Dual-artifact build |
| FR-38 | 1 | S-1.1 | Console entry point |
| FR-39 | 1 | S-1.1 | Root workspace wiring |
| FR-40 | 3 | S-3.1 | Engine provisioning |
| FR-41 | 1 | S-1.1 | Lean dependency set |
| FR-42 | 2 | S-2.2 | No recipe knowledge |
| FR-43 | 2 | S-2.2 | Adapter is sole caller |
| FR-44 | 5 | S-5.1 | Non-CFE verbs independent |
| FR-45 | 5 | S-5.2 | No CFE surface modification |
| FR-46 | 5 | S-5.3 | Delegation fidelity |
| FR-47 | 5 | S-5.5 | Closing Rule-2 retrospective |
| FR-48 | 1 | S-1.10 | Configuration surface |
| FR-49 | 1 | S-1.10 | Logging and child-output streaming |
| FR-50 | 3 | S-3.9 | Rehearsal before irreversible publish |

## Epic List

### Epic 1: Install, run, and diagnose Mason
A user can install `mason` as both a conda package and a wheel, run it, get consistent errors and
machine-readable output, and ask it to diagnose its own environment — including telling them
truthfully what it cannot do.
**FRs covered:** FR-2, FR-3, FR-5, FR-30 – FR-39, FR-41, FR-48, FR-49
**Standalone:** delivers a real, installable, self-diagnosing tool with no dependency on later epics.

### Epic 2: Author, build, and submit recipes
A user can carry a package through the whole conda-forge recipe lifecycle — generate, validate,
build, diagnose, optimize, scan, submit, update — through Mason's verbs, with every piece of recipe
judgement supplied by the conda-forge-expert machinery and none of it living in Mason.
**FRs covered:** FR-1, FR-4, FR-6, FR-7, FR-8, FR-9, FR-10, FR-11, FR-12, FR-13, FR-14, FR-42, FR-43
**Standalone:** complete lifecycle on top of Epic 1's shell. Consolidated into one epic because every
story touches the same two core files (`cfe.py`, `recipe.py`).

### Epic 3: Ship a library to both ecosystems
A user can build a library's artifacts and ship them to PyPI, a conda channel, and conda-forge in
one command — with a receipt that tells the truth about which targets are done and which are merely
queued.
**FRs covered:** FR-15 – FR-24, FR-40, FR-50
**Standalone:** the product's differentiator. Uses Epic 2's submission path for the conda-forge
target but delivers `pypi` and `channel:` value without it.

### Epic 4: Bind environments into lockfiles
A user can resolve a project's mixed conda and pip dependencies into a single lockfile, and check in
CI whether that lockfile has gone stale.
**FRs covered:** FR-25, FR-26, FR-27, FR-28, FR-29
**Standalone:** requires only Epic 1's shell and Epic 3's engine protocol.

### Epic 5: Prove the seam holds
The product's central guarantee — that Mason wraps the conda-forge-expert capability and never forks
it — is verified by tests rather than asserted by documentation, and the effort closes with the
mandatory retrospective that keeps the wrapped skill improving.
**FRs covered:** FR-44, FR-45, FR-46, FR-47
**Standalone:** verification and closeout. The two most critical guards (FR-42, FR-43) deliberately
ship early in Epic 2; this epic covers the guards that need the full product to exist.

---

## Epic 1: Install, run, and diagnose Mason

**Goal:** A user can install `mason`, run it, and trust its output and its self-report.

**FRs covered:** FR-2, FR-3, FR-5, FR-30 – FR-39, FR-41, FR-48, FR-49
**NFRs:** NFR-3, NFR-4, NFR-11, NFR-13, NFR-14, NFR-15
**ADs:** AD-2, AD-5, AD-7, AD-8, AD-13, AD-16

### Story 1.1: Workspace member scaffold and dual-artifact build

As a **maintainer of this repository**,
I want **`pyforge-mason` to build as both a conda package and a wheel from one manifest**,
So that **Mason is distributable the same way its sibling packages already are**.

**Acceptance Criteria:**

**Given** the repository root at `src/shared/packages/`
**When** the member package is created
**Then** `src/shared/packages/pyforge-mason/pyproject.toml` exists with `hatchling.build`,
`name = "pyforge-mason"`, `requires-python = ">=3.12"`, and
`[tool.hatch.build.targets.wheel] packages = ["src/pyforge"]`
**And** `[project.scripts]` declares `mason = "pyforge.mason.cli:main"`
**And** `src/pyforge/mason/` exists as a PEP-420 namespace package with **no** `src/pyforge/__init__.py`

**Given** the member package
**When** its `pixi.toml` is authored
**Then** it contains a `[package]` table and `[package.build.backend]` naming `pixi-build-python` `0.*`
**And** it contains **no** `[workspace]` table

**Given** the root `pixi.toml`
**When** workspace wiring is added
**Then** `[feature.pyforge-mason.dependencies]` declares `pyforge-mason = { path = "src/shared/packages/pyforge-mason" }`
**And** a `pyforge-mason` environment exists with `no-default-feature = true`
**And** tasks `pyforge-mason-build-conda`, `pyforge-mason-build-dist`, and `pyforge-mason-build`
(depending on both) are defined

**Given** the build tasks
**When** `pyforge-mason-build` runs
**Then** a `.conda` file appears in `dist-conda/` and a wheel plus sdist appear in `dist/`
**And** `mason --version` reports the installed distribution version

**Given** NFR-10 and FR-41
**When** wheel dependencies are declared
**Then** only libraries `pyforge.mason` actually imports are listed
**And** no CLI-framework dependency (click, typer) is present

*Effort: M. Realizes FR-36, FR-37, FR-38, FR-39, FR-41, NFR-11.*

### Story 1.2: CLI noun-verb structure and global flags

As a **user**,
I want **`mason <noun> <verb>` with consistent global flags**,
So that **the command surface is predictable and I never have to learn a per-command dialect**.

**Acceptance Criteria:**

**Given** the installed CLI
**When** I run `mason --help`
**Then** the nouns `recipe`, `package`, `environment` and the top-level `doctor` are listed

**Given** any noun
**When** I run `mason <noun>` with no verb
**Then** that noun's verbs are printed and the exit code is non-zero

**Given** any command
**When** I pass `--cfe-root`, `--cfe-python`, `--format`, `--verbose`, or `--quiet`
**Then** the flag is accepted
**And** no global flag is required for any command to run

**Given** AD-13
**When** a setting is resolved
**Then** precedence is flag → environment → default, uniformly
**And** Mason reads no `mason.toml` and no Mason-specific key from `pyproject.toml`

**Given** AD-2
**When** the CLI module is inspected
**Then** argparse is the only parsing library used
**And** a static check confirms no use-case module imports `subprocess`

*Effort: S. Realizes FR-30, FR-35, NFR-15.*

### Story 1.3: Error taxonomy and exit-code contract

As a **user scripting against Mason**,
I want **stable exit codes and typed errors**,
So that **I can branch on failure kind instead of grepping messages**.

**Acceptance Criteria:**

**Given** `errors.py`
**When** an anticipated failure occurs
**Then** a `MasonError` subclass is raised carrying a stable colon-delimited identifier
(e.g. `cfe:unresolved`, `ship:credential-missing`, `engine:absent`)
**And** the message states what failed and what to do next

**Given** `exit_codes.py`
**When** any command terminates
**Then** the exit code comes only from that module: `0` success, `1` operation failed, `2` usage
error, `3` CFE unavailable, `130` interrupt
**And** a static check confirms no other module produces an exit code

**Given** argparse's own `SystemExit`
**When** `--help` or a usage error triggers it
**Then** it surfaces as `0` or `2` respectively and never collides with a real failure code

**Given** an unanticipated exception
**When** it escapes a command
**Then** the process exits `1` with the traceback on stderr, never the interpreter default

*Effort: S. Realizes FR-32, FR-33, NFR-14; AD-7.*

### Story 1.4: Dual output format with stream discipline

As an **agent calling Mason**,
I want **exactly one JSON document on stdout and every diagnostic on stderr**,
So that **I can parse output without screen-scraping around log lines**.

**Acceptance Criteria:**

**Given** any command
**When** I pass `--format json`
**Then** stdout carries exactly one JSON document, or nothing
**And** every diagnostic, progress line, and log record goes to stderr

**Given** the JSON document
**When** it is parsed
**Then** it carries `schema_version`, `command`, `status`, `data`, and `errors`

**Given** `--format text` (the default)
**When** a command succeeds
**Then** a human-readable summary is written to stdout via the same writer the JSON branch uses

**Given** AD-8
**When** modules are inspected
**Then** only `render.py` formats output
**And** no use-case module writes to stdout

**Given** identical inputs
**When** a command runs twice
**Then** the JSON output is byte-identical apart from timestamps and declared provenance fields

*Effort: S. Realizes FR-31, NFR-3, NFR-4; AD-8.*

### Story 1.5: CFE root resolution chain

As a **user**,
I want **Mason to find the conda-forge-expert installation predictably**,
So that **it works in this repo, in another repo, and wherever I point it explicitly**.

**Acceptance Criteria:**

**Given** `resolve.py`
**When** the CFE root is resolved
**Then** the chain is: `--cfe-root` → `MASON_CFE_ROOT` → upward walk from cwd for a directory
containing `.claude/scripts/conda-forge-expert/` → not found
**And** first match wins

**Given** the resolution outcome
**When** it is returned
**Then** it records **which step matched**, so callers need not re-resolve

**Given** AD-5
**When** the resolver runs
**Then** it performs filesystem reads only — no writes, no network, no process spawn
**And** each step is unit-testable against a synthetic directory tree

**Given** an upward walk that reaches the filesystem root without a match
**When** resolution completes
**Then** a not-found outcome is returned, not an exception

*Effort: S. Realizes FR-2; AD-5.*

### Story 1.6: Interpreter selection and CFE import-floor probe

As a **user running Mason from a lean environment**,
I want **Mason to detect that its interpreter cannot run the CFE scripts**,
So that **I get a named error instead of a confusing subprocess ImportError**.

**Acceptance Criteria:**

**Given** `resolve.py`
**When** the interpreter is selected
**Then** the chain is `--cfe-python` → `MASON_CFE_PYTHON` → `sys.executable`, first match wins

**Given** a selected interpreter
**When** the CFE import floor is probed
**Then** `pyyaml`, `requests`, `packaging`, `truststore`, `ruamel.yaml`, and `conda-forge-metadata`
are each checked for importability under that interpreter
**And** the probe result is cached for the process lifetime

**Given** an interpreter missing part of the floor
**When** a CFE-dependent command runs
**Then** a typed error names the missing modules and the interpreter path
**And** no raw `ImportError` traceback from a subprocess reaches the user

*Effort: S. Realizes FR-3, D-7; AD-5.*

### Story 1.7: Degradation when CFE is unavailable

As a **user without a conda-forge-expert installation**,
I want **Mason to tell me precisely what is missing and keep working where it can**,
So that **a missing dependency costs me one feature, not the whole tool**.

**Acceptance Criteria:**

**Given** an unresolvable CFE root
**When** I run any `mason recipe` verb
**Then** the command exits `3` with a message naming all four resolution steps and how to satisfy each
**And** no Python traceback is printed

**Given** an unresolvable CFE root
**When** I run any `mason package` or `mason environment` verb
**Then** the command behaves exactly as it would with CFE present

**Given** AD-6
**When** modules are inspected
**Then** `package.py` and `environment.py` import `cfe` lazily or not at all
**And** module import of `pyforge.mason.package` succeeds with no CFE anywhere on the filesystem

*Effort: S. Realizes FR-5, D-2; AD-6.*

### Story 1.8: `mason doctor`

As a **user whose setup is not working**,
I want **one command that reports what Mason can see**,
So that **I can fix my environment without reading Mason's source**.

**Acceptance Criteria:**

**Given** `mason doctor`
**When** it runs
**Then** it reports the Mason version, the resolved CFE root **and which resolution step found it**,
the selected interpreter and whether the CFE import floor is satisfied, and each known engine's
presence and version

**Given** no CFE installation
**When** `mason doctor` runs
**Then** it exits `0`, reporting the gap rather than failing
**And** it states which verbs are unavailable as a result

**Given** `--format json`
**When** `mason doctor` runs
**Then** the report is emitted as a single JSON document conforming to the FR-31 envelope

*Effort: S. Realizes FR-34.*

### Story 1.9: Fake CFE root fixture and test harness

As a **developer of Mason**,
I want **a fixture CFE installation the test suite drives**,
So that **Mason's tests pass anywhere and never require the real machinery**.

**Acceptance Criteria:**

**Given** `tests/fixtures/fake_cfe_root/`
**When** the fixture is built
**Then** it mirrors the real layout (`.claude/scripts/conda-forge-expert/<script>.py`) with stub
scripts that emit canned stdout and configurable exit codes

**Given** the fixture
**When** a stub is asked to emit a leading progress line before its JSON body
**Then** it does so, exercising the tolerant-parsing path

**Given** the whole test suite except the FR-46 fidelity test
**When** it runs on a machine with no real CFE installation, no network, and no `recipes/` directory
**Then** every test passes

**Given** `pyproject.toml`
**When** pytest markers are declared
**Then** a `slow` marker exists, mirroring the `pyforge-warden` convention, and the default task
excludes it

*Effort: M. Realizes NFR-13; AD-16.*

### Story 1.10: Configuration surface, logging, and child-output streaming

As a **user running a multi-minute build**,
I want **to see progress as it happens and to tune behaviour without a config file**,
So that **I am not staring at a silent terminal wondering whether Mason is alive**.

**Acceptance Criteria:**

**Given** the v1 knob set
**When** each is exercised
**Then** `--cfe-root`/`MASON_CFE_ROOT`, `--cfe-python`/`MASON_CFE_PYTHON`,
`--cfe-timeout`/`MASON_CFE_TIMEOUT`, `--format`, `--verbose`, and `--quiet` all work in both forms
**And** precedence is flag → environment → default for every one

**Given** AD-13
**When** the codebase is scanned
**Then** no code path reads a Mason-specific key from any file
**And** a test asserts every knob has both a flag and an environment form

**Given** the logging subsystem
**When** any command runs at any verbosity
**Then** all log records go to stderr via stdlib `logging`
**And** no record contains an environment-variable value

**Given** a delegated operation expected to exceed a few seconds
**When** it runs
**Then** child stderr streams through to the user's stderr as produced, not buffered to completion

**Given** a streaming operation under `--format json`
**When** it completes
**Then** stdout still carries exactly one JSON document — streamed child output went to stderr
**And** a test asserts this explicitly

*Effort: M. Realizes FR-48, FR-49, NFR-2; AD-13.*

---

## Epic 2: Author, build, and submit recipes

**Goal:** The full conda-forge recipe lifecycle through Mason's verbs, with zero recipe knowledge in
Mason.

**FRs covered:** FR-1, FR-4, FR-6, FR-7 – FR-14, FR-42, FR-43
**NFRs:** NFR-1, NFR-2, NFR-5, NFR-16
**ADs:** AD-1, AD-2, AD-3, AD-4, AD-9, AD-14

### Story 2.1: The CFE port

As a **developer of Mason**,
I want **one module that owns every conda-forge-expert invocation**,
So that **the seam has a single, testable, enforceable location**.

**Acceptance Criteria:**

**Given** `cfe.py`
**When** it is authored
**Then** it declares every CFE script Mason uses in one module-level table
**And** it exposes named adapter functions; no caller ever passes a script name

**Given** an adapter call
**When** CFE is invoked
**Then** it runs as `[interpreter, script_path, *args]` via subprocess with a mandatory timeout
**And** the invocation uses a list argv, never `shell=True`

**Given** any invocation
**When** it completes
**Then** a `CfeResult` is returned carrying return code, stdout, stderr, and a parsed JSON body when
one is present
**And** a non-zero return code is data, not an exception

**Given** stdout with a leading non-JSON progress line before the JSON body
**When** the result is parsed
**Then** the JSON body is extracted successfully

**Given** a script that exceeds its timeout
**When** the timeout fires
**Then** a distinct typed timeout error is raised
**And** no orphaned child process remains

**Given** AD-4
**When** the codebase is inspected
**Then** no `import`, `importlib`, or `exec` of CFE code exists anywhere in `pyforge.mason`

*Effort: M. Realizes FR-1, FR-4, NFR-1, NFR-16; AD-3, AD-4.*

### Story 2.2: The seam guard

As a **maintainer accountable for D-1**,
I want **tests that fail the build when recipe knowledge or a stray CFE call appears in Mason**,
So that **the product's central guarantee cannot erode one helper at a time**.

**Acceptance Criteria:**

**Given** `tests/meta/test_no_recipe_knowledge.py`
**When** it scans `src/pyforge/mason/`
**Then** it fails if any module contains a conda-forge gotcha identifier, policy constant, pin table,
recipe-format field default, or selector/platform rule
**And** the deny-list of patterns is declared in one reviewable place

**Given** the deny-list
**When** it is authored
**Then** it enumerates, at minimum: the gotcha-identifier pattern (`G` + 1–3 digits, word-matched),
conda-forge policy nouns and check-code prefixes drawn from CFE's reference material, v1
recipe-format field names, and known pin/constraint string shapes
**And** each entry cites the CFE artifact it derives from

**Given** the test's own correctness
**When** it runs
**Then** it exercises positive fixtures — synthetic modules with a planted violation of **each**
deny-list category — and fails if any planted violation goes undetected
**And** a deny-list that matches nothing is therefore a failing test, not a passing one

**Given** a deny-list entry being weakened or removed
**When** the change is made
**Then** a companion test fails unless the entry carries a rationale comment

**Given** the deny-list
**When** a developer adds a matching constant to any Mason module
**Then** the test fails, naming the file, the line, and the matched pattern

**Given** `tests/meta/test_adapter_sole_caller.py`
**When** it scans `src/pyforge/mason/`
**Then** it fails if any module other than `cfe.py` references a CFE path, a CFE script filename, or
spawns a process against one

**Given** both tests
**When** the default test task runs
**Then** both execute (neither is marked `slow`) and both are green

**Given** this story completes
**When** any subsequent story in Epics 2 – 5 is implemented
**Then** these guards run against it

*Effort: M. Realizes FR-42, FR-43; AD-1, AD-2, AD-3. **Critical path.***

### Story 2.3: Credential isolation

As a **user behind a corporate proxy**,
I want **Mason to never touch my credentials**,
So that **the blast radius of a credentialed HTTP layer stays inside the process that needs it**.

**Acceptance Criteria:**

**Given** the Mason codebase
**When** it is scanned
**Then** no module reads any `JFROG_*` environment variable
**And** no module makes an authenticated HTTP request on CFE's behalf

**Given** a CFE invocation
**When** the subprocess is spawned
**Then** credentials reach CFE only through the inherited process environment

**Given** any verbosity level including `--verbose`
**When** logging occurs
**Then** no environment-variable **value** is written to any stream

**Given** a test asserting credential blindness
**When** it runs with sentinel credential values set in the environment
**Then** no sentinel value appears in stdout, stderr, or any produced artifact

*Effort: S. Realizes FR-6, NFR-2; AD-14.*

### Story 2.4: `mason recipe new`

As a **user packaging an upstream library**,
I want **to generate a recipe from PyPI, GitHub, CRAN, or npm**,
So that **I start from a working draft instead of a blank file**.

**Acceptance Criteria:**

**Given** `mason recipe new --from-pypi <name>`
**When** it runs against a resolvable CFE root
**Then** the corresponding CFE generator is invoked through the adapter
**And** a v1 `recipe.yaml` is written to the user-specified path

**Given** `--from-github`, `--from-cran`, `--from-npm`
**When** each is used
**Then** the matching CFE generator is invoked

**Given** the generated recipe
**When** its content is compared to the CFE generator's direct output
**Then** Mason has applied no field defaults, no rewriting, and no normalization of its own

**Given** a generation failure reported by CFE
**When** it surfaces
**Then** it becomes a typed error with CFE's message preserved

*Effort: S. Realizes FR-7.*

### Story 2.5: `mason recipe validate`

As a **user**,
I want **to validate a recipe against conda-forge policy**,
So that **I catch problems before a build burns CI time**.

**Acceptance Criteria:**

**Given** a recipe with validation failures
**When** `mason recipe validate` runs
**Then** the exit code is non-zero

**Given** validation findings
**When** they are rendered
**Then** CFE's identifiers are preserved verbatim — never renumbered, reworded, or re-severitied

**Given** `--format json`
**When** validation runs
**Then** findings appear in the `data` field of the FR-31 envelope

*Effort: XS. Realizes FR-8.*

### Story 2.6: `mason recipe build`

As a **user**,
I want **to build a recipe on my machine**,
So that **I know it works before I ask anyone to review it**.

**Acceptance Criteria:**

**Given** `mason recipe build <path>`
**When** it runs
**Then** a native host-platform build is performed by default

**Given** a Docker / CI-parity build
**When** the user wants one
**Then** it requires an explicit flag and is never selected implicitly

**Given** a completed build
**When** the result is rendered
**Then** the output artifact location and the exit status are reported in both text and JSON forms

**Given** a build that exceeds its timeout
**When** the timeout fires
**Then** the typed timeout error from S-2.1 surfaces and no orphaned process remains

*Effort: S. Realizes FR-9.*

### Story 2.7: `mason recipe diagnose`

As a **user whose build failed**,
I want **a named cause and a proposed fix**,
So that **I do not have to read a thousand lines of build log**.

**Acceptance Criteria:**

**Given** a failed build's log
**When** `mason recipe diagnose` runs
**Then** CFE's failure analyzer is invoked through the adapter and its diagnosis is rendered

**Given** CFE returning no diagnosis
**When** the result is rendered
**Then** Mason states plainly that no diagnosis was produced
**And** Mason offers no cause, guess, or suggestion of its own

*Effort: S. Realizes FR-10.*

### Story 2.8: `mason recipe optimize` and `mason recipe scan`

As a **user preparing a recipe for review**,
I want **quality findings and a vulnerability scan**,
So that **I fix what a reviewer would flag before they see it**.

**Acceptance Criteria:**

**Given** `mason recipe optimize`
**When** it runs
**Then** CFE's check codes are preserved verbatim in the output

**Given** `mason recipe scan`
**When** it runs
**Then** CFE's scanner is invoked and its findings are rendered
**And** Mason applies no severity policy, threshold, or filtering of its own

**Given** `--format json` on either verb
**When** it runs
**Then** findings appear in the FR-31 envelope's `data` field

*Effort: S. Realizes FR-11, FR-12.*

### Story 2.9: `mason recipe submit`

As a **user with a working recipe**,
I want **to open a staged-recipes pull request safely**,
So that **I can contribute without memorizing the submission dance**.

**Acceptance Criteria:**

**Given** `mason recipe submit`
**When** no confirming flag is passed
**Then** the operation is a dry run and nothing is pushed or opened

**Given** an explicit confirming flag
**When** submission proceeds
**Then** CFE's two-phase flow (prepare branch, then open PR) is preserved and each phase is
separately addressable

**Given** a successful submission
**When** the result is returned
**Then** it is a `ShipTargetResult` with `state = pending` and a `reference` carrying the PR
identifier
**And** the `ShipState` enum (`not_attempted`, `failed`, `pending`, `terminal`) is defined in
`models.py`

**Given** this story
**When** it completes
**Then** staged-recipes submission has exactly one implementation in `recipe.py`, which Epic 3 will
call rather than reimplement

*Effort: M. Realizes FR-13; AD-9, AD-11 (owner side).*

### Story 2.10: `mason recipe update`

As a **maintainer**,
I want **to update a recipe to a newer upstream version and see the diff first**,
So that **I never apply a change I have not read**.

**Acceptance Criteria:**

**Given** `mason recipe update`
**When** it runs
**Then** the proposed change is displayed before anything is written

**Given** `--dry-run`
**When** used with any supported source type
**Then** the diff is shown and no file is modified

**Given** the user confirming
**When** the update applies
**Then** only the fields CFE's updater changed are written

*Effort: S. Realizes FR-14.*

---

## Epic 3: Ship a library to both ecosystems

**Goal:** One command builds a library and ships it to PyPI, a conda channel, and conda-forge —
reporting each target's true state.

**FRs covered:** FR-15 – FR-24, FR-40, FR-50
**NFRs:** NFR-2, NFR-7, NFR-8, NFR-9, NFR-10
**ADs:** AD-6, AD-9, AD-10, AD-11, AD-12, AD-14

### Story 3.1: Engine protocol and provisioning

As a **developer of Mason**,
I want **every external tool behind one adapter protocol**,
So that **engine absence, version drift, and invocation are handled identically everywhere**.

**Acceptance Criteria:**

**Given** `engines/__init__.py`
**When** the protocol is defined
**Then** every engine adapter implements `name`, `probe() -> version | None`, and its operation

**Given** an engine
**When** it is located
**Then** it is discovered on `PATH`
**And** nothing is downloaded at runtime

**Given** a missing engine
**When** an operation needs it
**Then** a typed error names the engine and how to provision it — never a raw `FileNotFoundError`

**Given** the member `pixi.toml`
**When** engines are declared
**Then** each is a conda run-dependency with a version **range** (not an exact pin)
**And** in-code version-range constants mirror those declarations
**And** `tests/meta/test_engine_version_range_sync.py` fails if the two diverge

*Effort: M. Realizes FR-40, NFR-7, NFR-10; AD-12.*

### Story 3.2: `mason package build`

As a **library maintainer**,
I want **to build my wheel, sdist, and conda package in one command**,
So that **I have every artifact ready before deciding where to send it**.

**Acceptance Criteria:**

**Given** `mason package build`
**When** it runs against a project
**Then** a wheel and an sdist are produced via PEP-517 (`python -m build`)
**And** a `.conda` is produced via `pixi build`
**And** every artifact path is reported

**Given** a build command
**When** it completes
**Then** nothing has been uploaded anywhere

**Given** `--target`
**When** a value is supplied
**Then** `library` is accepted (and is the default)
**And** any other value is rejected with a message naming `library` as the v1 set

**Given** built artifacts
**When** the version consistency check runs
**Then** the wheel version and the conda package version are compared
**And** a mismatch aborts before any upload, showing both values

**Given** no CFE installation anywhere
**When** `mason package build` runs
**Then** it succeeds

*Effort: M. Realizes FR-15, FR-21, FR-22; AD-6.*

### Story 3.3: Ship-target vocabulary and dry-run default

As a **user**,
I want **a small, explicit set of ship targets that default to doing nothing**,
So that **I cannot publish by accident**.

**Acceptance Criteria:**

**Given** `--ship`
**When** a value is parsed
**Then** exactly three forms are accepted: `pypi`, `conda-forge`, `channel:<name>`
**And** any other value is rejected with the valid set listed

**Given** multiple comma-separated targets
**When** they are parsed
**Then** each is honoured independently

**Given** `--ship` without a confirming flag
**When** the command runs
**Then** it plans and prints, and uploads nothing
**And** the plan names every target, every artifact, and every destination

*Effort: S. Realizes FR-16, FR-19, NFR-9.*

### Story 3.4: The `pypi` ship target

As a **library maintainer**,
I want **to publish my wheel to PyPI**,
So that **pip users get the release**.

**Acceptance Criteria:**

**Given** the `pypi` target
**When** it executes
**Then** the wheel and sdist are uploaded via the `twine` engine adapter
**And** the result is a `ShipTargetResult` with `state = terminal` and a URL reference

**Given** missing credentials
**When** a ship is requested
**Then** the failure is detected **before** any artifact is built or uploaded

**Given** credentials
**When** they are used
**Then** they are read at the point of use, never stored on a rendered or logged object
**And** no credential value appears in any receipt, log, or error message

**Given** no CFE installation anywhere
**When** `mason package --ship pypi` runs
**Then** it succeeds

*Effort: M. Realizes FR-20, NFR-2; AD-6, AD-14.*

### Story 3.5: The `channel:<name>` ship target

As an **enterprise user with a private channel**,
I want **to upload my conda package to a named channel**,
So that **my organization consumes it without conda-forge involvement**.

**Acceptance Criteria:**

**Given** `--ship channel:<name>`
**When** it executes
**Then** the `.conda` artifact is uploaded to the named channel via an engine adapter
**And** the result is a `ShipTargetResult` with `state = terminal` and a channel-path reference

**Given** a channel that rejects the upload
**When** the failure surfaces
**Then** it becomes a typed error and a `failed` target result, without affecting other targets

**Given** no CFE installation anywhere
**When** this target runs
**Then** it succeeds

*Effort: S. Realizes FR-16 (channel form); AD-6, AD-12.*

### Story 3.6: The `conda-forge` ship target

As a **library maintainer**,
I want **conda-forge shipping to reuse the same submission path as `mason recipe submit`**,
So that **there is one implementation of staged-recipes submission, not two**.

**Acceptance Criteria:**

**Given** `--ship conda-forge`
**When** it executes
**Then** it **calls** the submission function implemented in `recipe.py` (S-2.9)
**And** wraps the returned result in a `ShipTargetResult` with `state = pending`

**Given** the codebase
**When** it is inspected
**Then** `package.py` contains no staged-recipes submission logic of its own

**Given** a recipe path supplied by the user
**When** the target runs
**Then** that recipe is used

**Given** no recipe path
**When** the target runs
**Then** Mason offers to generate one via `mason recipe new` and does **not** generate silently

**Given** an unresolvable CFE root, **or** a recipe that is not at `<cfe-root>/recipes/<name>/`
**When** `ship --to pypi,conda-forge` runs
**Then** the `conda-forge` target alone fails, naming the unmet precondition
**And** the `pypi` target completes normally

**Given** D-10's boundary
**When** `mason doctor` runs
**Then** it reports whether both conda-forge-ship preconditions are met
**And** a user learns the boundary before attempting a release, not during one

*Effort: M. Realizes FR-23, D-10; AD-6, AD-11.*

### Story 3.9: The `ship` verb and TestPyPI rehearsal

As a **library maintainer about to publish irreversibly**,
I want **a real `ship` verb and a rehearsal target**,
So that **the command exists at all and my first production upload is not my first attempt**.

**Acceptance Criteria:**

**Given** FR-30's noun-verb rule and FR-15's build-uploads-nothing rule
**When** the command surface is built
**Then** `mason package ship --to <targets>` exists as the canonical shipping command

**Given** the crew charter's cadence
**When** a user runs `mason package --target library --ship pypi,conda-forge`
**Then** it works, dispatching to `mason package ship`
**And** a test asserts this is the **only** bare-noun form that runs

**Given** `ship` invoked with no artifacts present
**When** it runs
**Then** it builds first by calling FR-15's implementation, not a duplicate of it

**Given** `--to pypi-test`
**When** it runs
**Then** the upload goes to TestPyPI through the same code path as `pypi`, differing only in
repository configuration

**Given** the FR-24 self-hosting sequence
**When** it executes
**Then** `pypi-test` runs first and must pass before `pypi` runs

**Given** a dry-run plan naming the `pypi` target
**When** it is printed
**Then** it states explicitly that a PyPI upload is irreversible

*Effort: M. Realizes FR-16 (verb form), FR-50, D-12; supports SM-1.*

### Story 3.7: Asymmetric receipts, partial failure, and idempotence

As a **user shipping to several places at once**,
I want **a receipt that distinguishes done from queued and survives a retry**,
So that **I never believe a pending pull request is a completed release**.

**Acceptance Criteria:**

**Given** a multi-target ship
**When** the receipt is produced
**Then** every target carries an explicit `state` of `not_attempted`, `failed`, `pending`, or
`terminal`, plus a `reference`

**Given** a run where `pypi` succeeded and `conda-forge` opened a pull request
**When** the result is rendered in either format
**Then** it reports success **and** pending — never a uniform success
**And** `pending` is not collapsed into success in any rendering

**Given** the aggregate exit code
**When** it is computed
**Then** failure results if any target failed to *initiate*
**And** a target that initiated but is pending is not a failure

**Given** one target failing
**When** the ship continues
**Then** the remaining targets are still attempted

**Given** a retry of a partially completed ship
**When** it runs
**Then** an already-terminal target is skipped, not re-uploaded
**And** "already shipped?" is answered by interrogating the target (index or PR lookup), not by any
local state file

**Given** the Mason installation
**When** the filesystem is inspected after any command
**Then** Mason has created no state directory, receipt cache, or lock file of its own

**Given** a target that cannot be interrogated
**When** the result is produced
**Then** it is `pending` with the reason stated, never an assumption

*Effort: L. Realizes FR-17, FR-18, NFR-8; AD-9, AD-10.*

### Story 3.8: Mason ships Mason

As the **product owner**,
I want **Mason to publish its own release**,
So that **the dual-ship claim is proven rather than asserted**.

**Acceptance Criteria:**

**Given** `src/shared/packages/pyforge-mason/`
**When** `mason package --ship pypi` runs against it
**Then** `pyforge-mason` is published and the receipt shows `terminal` with a URL

**Given** the same project
**When** `mason package build` runs
**Then** the produced `.conda`, wheel, and sdist match what the repository's existing hand-run
`pyforge-mason-build` triad produces

**Given** this story
**When** it passes
**Then** SM-1, the primary success metric, is satisfied

*Effort: M. Realizes FR-24, SM-1.*

---

## Epic 4: Bind environments into lockfiles

**Goal:** One lockfile across conda and pip, and a CI check that it is current.

**FRs covered:** FR-25 – FR-29
**NFRs:** NFR-5, NFR-12
**ADs:** AD-6, AD-12

### Story 4.1: Lock engine adapter and provenance

As a **developer of Mason**,
I want **the solver behind the engine protocol with its identity reported**,
So that **Mason never implements resolution and users always know what solved their lock**.

**Acceptance Criteria:**

**Given** `engines/condalock.py`
**When** it is authored
**Then** it implements the S-3.1 engine protocol

**Given** any produced lock
**When** the result is rendered
**Then** the engine name and version appear in the output
**And** they appear in the lockfile's provenance where the format allows

**Given** the Mason codebase
**When** it is inspected
**Then** it contains no dependency-resolution logic

*Effort: S. Realizes FR-29; AD-12.*

### Story 4.2: Manifest discovery

As a **user**,
I want **Mason to find my dependency manifests**,
So that **I do not have to enumerate them by hand**.

**Acceptance Criteria:**

**Given** a project directory
**When** discovery runs
**Then** `pyproject.toml`, `environment.yml`, `requirements*.txt`, and `pixi.toml` are located

**Given** discovered manifests
**When** solving is about to begin
**Then** the list is displayed first

**Given** explicit manifest paths supplied by the user
**When** they are provided
**Then** they override discovery entirely

**Given** no manifests found
**When** discovery completes
**Then** a typed error names the directory searched and the filenames looked for

*Effort: S. Realizes FR-26.*

### Story 4.3: `mason environment lock`

As a **user with mixed conda and pip dependencies**,
I want **one lockfile covering both**,
So that **my environment is reproducible without maintaining two files**.

**Acceptance Criteria:**

**Given** `mason environment lock`
**When** it runs
**Then** solving is delegated to the engine and a lockfile is written

**Given** `--output <path>`
**When** supplied
**Then** the lockfile is written there

**Given** `--platform`
**When** supplied one or more times
**Then** the lock covers exactly those platforms

**Given** no `--platform`
**When** the command runs
**Then** the engine's default applies and is reported in the output

**Given** no CFE installation anywhere
**When** this command runs
**Then** it succeeds

*Effort: M. Realizes FR-25, FR-27; AD-6.*

### Story 4.4: `mason environment check`

As a **CI pipeline**,
I want **a non-zero exit when the lockfile is stale**,
So that **a drifted lock fails the build instead of shipping**.

**Acceptance Criteria:**

**Given** a lockfile current with its manifests
**When** `mason environment check` runs
**Then** it exits `0`

**Given** a manifest changed since the lock was produced
**When** the check runs
**Then** it exits non-zero and names which manifests drifted

**Given** `--format json`
**When** the check runs
**Then** a single JSON document conforming to the FR-31 envelope is emitted

**Given** no lockfile present
**When** the check runs
**Then** a typed error distinguishes "missing" from "stale"

*Effort: S. Realizes FR-28.*

---

## Epic 5: Prove the seam holds

**Goal:** The D-1 guarantee is verified by tests and the effort closes with the mandatory
retrospective.

**FRs covered:** FR-44, FR-45, FR-46, FR-47
**NFRs:** NFR-5, NFR-6, NFR-12
**ADs:** AD-6, AD-15

### Story 5.1: CFE-independence test

As a **maintainer**,
I want **automated proof that two of three verb families work without CFE**,
So that **the accepted D-1 tradeoff stays bounded to `mason recipe` alone**.

**Acceptance Criteria:**

**Given** `tests/meta/test_cfe_independence.py`
**When** it runs
**Then** every `mason package` and every `mason environment` verb executes with the CFE root
guaranteed unresolvable
**And** each behaves normally

**Given** the one legitimate exception
**When** the test is written
**Then** the `conda-forge` ship target appears in a **named allow-list of exactly one entry**
**And** a blanket "except where CFE is needed" formulation is not used — that phrasing is the erosion
this test exists to stop
**And** adding a second allow-list entry requires editing the test, which is the review gate

**Given** the excepted target
**When** it runs without CFE
**Then** the test asserts positively that it fails **with the FR-5 error specifically**, not merely
that it fails
**And** every other target in the same invocation succeeds

**Given** the same test
**When** module imports are checked
**Then** `pyforge.mason.package` and `pyforge.mason.environment` import successfully with no CFE on
the filesystem

*Effort: S. Realizes FR-44; AD-6.*

### Story 5.2: Governance test

As a **repository maintainer**,
I want **automated proof that Mason never wrote to the conda-forge-expert surface**,
So that **CLAUDE.md Rule 1 and the `spec-packaging-factory` sentinel are enforced, not trusted**.

**Acceptance Criteria:**

**Given** the effort's commit range
**When** it is scanned
**Then** no **implementation** commit touches `.claude/skills/conda-forge-expert/**`,
`.claude/scripts/conda-forge-expert/**`, or `.claude/tools/conda_forge_server.py`

**Given** the closing Rule-2 retrospective (S-5.5), which must edit exactly those files
**When** the check runs
**Then** that one commit is recognized as the sanctioned exception — identified by a `retro:` subject
plus a CFE `CHANGELOG.md` entry in the same commit — and excluded
**And** the check asserts the exception is used **exactly once** and carries a CHANGELOG move, so it
cannot be borrowed to slip an implementation change through

**Given** the repository
**When** `scripts/spec_surface_check.py` runs
**Then** it is green

**Given** a need for CFE behaviour that CFE does not have
**When** it is encountered during implementation
**Then** it is recorded as an open question routed to a CFE retrospective
**And** no local patch or vendored copy is created

*Effort: S. Realizes FR-45; AD-15.*

### Story 5.3: Delegation-fidelity test

As a **maintainer**,
I want **proof that Mason transforms presentation and not semantics**,
So that **wrapping is verified rather than assumed**.

**Acceptance Criteria:**

**Given** a representative recipe operation
**When** it is run through Mason and separately as a direct CFE invocation
**Then** the semantic content of the two results matches

**Given** this test
**When** it is registered
**Then** it carries the `slow` marker and is excluded from the default test task, mirroring the
`pyforge-warden` convention

**Given** the test running against a real CFE installation
**When** CFE is absent
**Then** the test skips cleanly rather than failing

*Effort: M. Realizes FR-46.*

### Story 5.4: Free-inheritance verification

As the **product owner**,
I want **evidence that a CFE improvement reaches Mason with no change to Mason**,
So that **the core argument for wrapping is demonstrated on real data**.

**Acceptance Criteria:**

**Given** a CFE MINOR version bump landing after Mason ships
**When** the affected Mason verb is re-run
**Then** the improved behaviour is observed
**And** the Mason repository shows no corresponding change

**Given** the observation
**When** it is recorded
**Then** SM-4 is marked satisfied with the CFE version and the date

*Effort: XS. Realizes SM-4. Depends on an external event; may complete after v1 ships.*

### Story 5.5: Rule-2 conda-forge-expert retrospective

As the **repository owner**,
I want **the mandatory retrospective that closes any conda-forge effort**,
So that **the skill Mason wraps is improved by the effort that wrapped it**.

**Acceptance Criteria:**

**Given** the effort reaching closeout
**When** the retrospective runs
**Then** it reviews the build against the conda-forge-expert skill and identifies corrections,
refinements, and additions

**Given** findings
**When** they land
**Then** they are edits to the skill's own files plus a dated CHANGELOG entry with a one-line summary
per finding
**And** the skill version is bumped per semver

**Given** the CFE upstream defects recorded during planning — the 13 duplicated `_get_data_dir()`
copies, the `parents[3/4/5]` repo-root divergence, the two scripts resolving to a different data
directory, and the unconditional JFrog header injection
**When** the retrospective runs
**Then** each is surfaced for triage as a CFE finding

**Given** no novel findings (unlikely)
**When** the retrospective completes
**Then** a CHANGELOG entry still states that existing guidance held, naming this effort

**Given** this story
**When** it completes
**Then** the effort is done. It is not optional and not deferrable.

**Given** FR-45's governance check
**When** this retrospective commits its skill edits
**Then** the commit uses a `retro:` subject and includes the CFE `CHANGELOG.md` entry, so the
sanctioned-exception rule recognizes it
**And** it is the **only** commit in the effort touching the CFE surface

*Effort: M. Realizes FR-47, SM-7, CLAUDE.md Rule 2.*

---

## assumptions[]

1. **A-1** — Story effort estimates assume a developer with access to this repository and a working
   pixi environment; they exclude time spent waiting on conda-forge review.
2. **A-2** — S-2.4 through S-2.8 are individually small because each is a thin mapping onto an
   existing CFE script. If a CFE script's argv contract proves richer than expected, these grow.
3. **A-3** — S-3.7 is sized L because target interrogation (AD-10) requires PyPI and GitHub API
   integration that no earlier story establishes.
4. **A-4** — S-5.4 depends on an external event (a post-ship CFE MINOR bump) and may complete after
   v1 is declared done. It is included because SM-4 is a named success metric.
5. **A-5** — S-3.8 assumes Mason's own package is representative enough to prove `--ship`. It is a
   pure-Python library; a compiled package would exercise paths this does not.

## open_questions[]

1. **OQ-E1** — S-2.1's script table must name a specific CFE script per verb (PRD OQ-1, spine
   OQ-A1). Mechanical, but must be produced before S-2.4 starts.
2. **OQ-E2** — S-3.5's engine choice: `pixi publish` or `anaconda upload` (PRD OQ-2, spine OQ-A2).
   Either satisfies AD-12.
3. **OQ-E3** — S-4.1's engine: `conda-lock` or `pixi` (PRD OQ-4). May need both adapters.
4. **OQ-E4** — S-2.2's deny-list content (spine OQ-A3): the concrete pattern set must be reviewable
   and hard to weaken silently. Needs a review gate of its own.
5. **OQ-E5** — Whether Epic 5's governance test (S-5.2) can inspect the commit range automatically
   in this repository's branching model, or must be a documented manual check.
