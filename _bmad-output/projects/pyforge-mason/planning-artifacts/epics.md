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
epicCount: 14  # 2026-09-06: Epic 14 added (spec-bmad-suite-lifecycle mason relay); Epic 13 (2026-09-03) had not bumped this from 12.
storyCount: 59  # 2026-09-06: 58 + Story 14.1 (dated snapshot; the ledger enumerates).
frCount: 50
status: complete
revision: 2
revisionNote: "r2 tracks PRD revision 2 (adversarial-review fixes). Added S-1.10 (config+logging), S-3.9 (ship verb + TestPyPI rehearsal), S-5.6 removed in favour of folding FR-47 into S-5.5; corrected S-3.6, S-5.1, S-5.2, S-2.2 for the D-10/D-12/FR-44/FR-45 resolutions."
updated: "2026-10-09"   # RE-STAMPED 2026-10-09: Epic 28 / Story 28.1 minted (fix under spec-pyforge-mason CAP-16, no new CAP, no FR moves, no flag): the CFE-rebuild guard reads a SHA field whatever type YAML gives it. Prior "2026-10-09"   # RE-STAMPED 2026-10-09: Story 25.3 minted (feature under spec-pyforge-mason CAP-35 / FR-57, CAP-20, CAP-23; no new CAP, no FR moves) and given a --repair mode; Story 25.2 Deps S-25.3 and a Wave 0 that repairs Story 25.1's landing; § Currency reconciliation — 2026-10-09 (later) appended. Prior "2026-10-09"   # RE-STAMPED 2026-10-09: Stories 22.3 and 22.4 minted blocked (fixes under spec-pyforge-mason CAP-32, FR-54), split from Story 22.1 by two operator rulings; § Currency reconciliation — 2026-10-09 appended. Prior 2026-10-03   # RE-STAMPED 2026-10-03 (Phase 4+5): Epic 27 / Stories 27.1-27.2 minted from the operator's Phase 4+5 ruling (fix, no CAP; 61 open medium/low deferrals). Prior 2026-10-02   # RE-STAMPED 2026-10-02: Epic 26 / Story 26.1 minted (a fix under spec-pyforge-mason CAP-34, FR-56). Prior 2026-09-29 (evening)   # RE-STAMPED 2026-09-29 (evening): Epic 25 / Stories 25.1-25.2 minted (spec-pyforge-mason CAP-35, FR-57); § Currency reconciliation — 2026-09-29 (evening). Prior 2026-09-29 (later)   # RE-STAMPED 2026-09-29 (later): Epic 24 / Story 24.1 minted (spec-pyforge-mason CAP-34, FR-56); § Currency reconciliation — 2026-09-29 (later). Prior 2026-09-29   # RE-STAMPED 2026-09-29: Epic 23 / Stories 23.1-23.3 minted (spec-pyforge-mason CAP-33, FR-55); § Currency reconciliation — 2026-09-29. Prior 2026-09-28 (night, later)   # RE-STAMPED 2026-09-28 (night, later): Epic 22 / Stories 22.1-22.2 minted (spec-pyforge-mason CAP-32, FR-54); § Currency reconciliation — 2026-09-28 (night, later) appended. Prior 2026-09-28 (night): Epic 21 / Stories 21.1-21.5 minted (spec-pyforge-mason CAP-31, FR-53); § Currency reconciliation — 2026-09-28 (night) appended. Prior 2026-09-28 (later): Epic 20 / Story 20.1 minted (spec-pyforge-mason CAP-30, FR-52); § Currency reconciliation — 2026-09-28 (later) appended. Prior 2026-09-28: Epic 19 / Stories 19.1-19.5 minted (spec-pyforge-mason CAP-29, FR-51); § Currency reconciliation — 2026-09-28 appended. Prior 2026-09-27 (night): Epic 18 / Story 18.1 minted (spec-pyforge-mason CAP-28). Prior 2026-09-20   # RE-STAMPED 2026-09-20: fleet consistency pass (story-spec status ↔ ledger, reconstructed run results, epic roll-ups); § Currency reconciliation — 2026-09-20 (fleet consistency pass) appended. Prior 2026-09-20   # chain-currency cascade 2026-09-20 (engine version ranges become floors by operator ruling; pixi.toml run-dependency caps removed; surface reconcile for the pyforge-foundry-full union solve); no requirement/AD/story delta. Prior 2026-09-17
currency_review: "Reviewed 2026-09-14 (chain-currency sweep cascade, arch->epics edge) — validation note appended at end of file (§ Validation note — 2026-09-14): ledger re-measured with the real parser at 70/70 stories done across 17/17 epics; Epic 16's two realization-gate stories confirmed landed against live evidence (the pyforge-mason-recipe-build-smoke pixi task is wired into pyforge-station-tests.yml:228); the PRD's new FR-14 as-built divergence is recorded as owing a Dream/Spec, NOT minted as a story here. No epic or story restructured. Reviewed 2026-09-06 (Epic 14 added: spec-bmad-suite-lifecycle mason relay — bmad-eval-quality __win variant, Story 14.1; CFE Rule 1 + Rule 2 apply). Reviewed 2026-08-26 — validated against the ARCHITECTURE-SPINE as truth-upped the same day and the as-built code: all 50 stories across 11 epics are done in the tracked ledger (station complete per fleet ledger 2026-08-21). Counts corrected 6/42 -> 11/50 (Epics 6-11 had grown past the r2 snapshot). No story headings or statuses changed; see the appended Validation note. Prior review 2026-08-02 (AD binding check)."
# The single canonical story source for this station: every `### Story` heading
# here maps 1:1 to a sprint-status-ledger.yaml story key. Exactly one per station (marshal:AD-72).
epics_role: canonical
---

# pyforge-mason — Epic Breakdown

## Overview

Decomposition of Mason's PRD (50 FRs / 16 NFRs / 13 D-records) and architecture spine (18 ADs,
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

All 18 ADs flow into specific stories (AD-25/AD-26 rows added 2026-08-10, correct-course):

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
| AD-25 | S-1.10 (delivered — `run_streamed`; FR-49) |
| AD-26 | S-3.9 (`pypi-test` rehearsal gate; FR-50) |

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

### Epic 6: The CFE rebuild — pilot slice, parallel-run, and the re-scope gate
The CFE surface's sanctioned rebuild (operator directive 2026-08-10), decomposed only through its
re-scope gate: slice map + campaign state, the divergence-and-endgame guard, the recipe-generation
pilot built and parallel-validated, and the recorded go/adjust/stop decision.
**FRs covered:** none of FR-1..FR-50 — decomposes `spec-conda-forge-expert-rebuild`'s own contract.
**Standalone:** gated on nothing in Epics 1-5; its endgame gates the rebuild Dream's `realized`.

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
spawns a process against one — honoring AD-3's two-entry carve-out (amended 2026-08-10):
`resolve.py`'s `_CFE_MARKER` root-marker constant and `errors.py`'s guidance echo are allowlisted,
each allowlist entry carrying a rationale comment; script names and process-spawning have no
exception anywhere

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

> **Audit note (2026-08-10, correct-course):** CFE's `submit_pr.py` accepts an in-tree recipe
> slug only (`_path_guard` confines to `<cfe-root>/recipes/`; PRD D-10 states this for
> `--to conda-forge` and it applies here identically). S-2.4's user-specified output path
> composes with this ONLY via `CFE_RECIPES_ROOT`: the submit adapter sets it in the child
> process environment to the recipe's parent directory — no new user-facing CLI knob (AD-13's
> closed set holds), no CFE-side change (AD-15's wrap rule holds).

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

**Given** a recipe generated to a user-specified path (S-2.4)
**When** `mason recipe submit --to conda-forge` runs against it
**Then** the submit adapter sets `CFE_RECIPES_ROOT` in the child environment to the recipe's
parent directory so CFE's slug-confined `submit_pr.py` resolves it — no new user-facing CLI
knob, no CFE-side change — and a test proves an out-of-tree recipe submits (AC added
2026-08-10, correct-course)

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
**Then** it exits non-zero and reports `stale: true` (FR-28 requires no per-manifest
attribution — conda-lock's own hash data is keyed by platform, never by source file, and the
contract's Never clause forbids Mason from re-implementing conda-lock's content-hash algorithm
to synthesize one; resolved 2026-08-15, story 4.4 escalation)

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

> **Re-issued 2026-08-10 (correct-course, operator directive):** AD-15 was amended — the CFE
> surface is read-only for THE MASON-CLI EFFORT (this epic set), while the
> `spec-conda-forge-expert-rebuild` effort is the sanctioned writer under its own Spec's gates.
> This story's commit-range check therefore scopes to commits touching
> `src/shared/packages/pyforge-mason/**` (code paths only — deliberately NOT planning-artifacts,
> where the rebuild effort's slice map and campaign state live — resolving OQ-E5), and rebuild-effort
> commits are governed by the rebuild Spec's own entry-point-compatibility gates, not this test.

As a **repository maintainer**,
I want **automated proof that Mason never wrote to the conda-forge-expert surface**,
So that **CLAUDE.md Rule 1 and the `spec-packaging-factory` sentinel are enforced, not trusted**.

**Acceptance Criteria:**

**Given** the mason-CLI effort's commit range — commits touching
`src/shared/packages/pyforge-mason/**` (re-issued 2026-08-10: rebuild-effort commits are
governed by `spec-conda-forge-expert-rebuild`'s own gates and are outside this check)
**When** it is scanned
**Then** no **implementation** commit in that range touches `.claude/skills/conda-forge-expert/**`,
`.claude/scripts/conda-forge-expert/**`, or `.claude/tools/conda_forge_server.py`

**Given** the closing Rule-2 retrospective (S-5.5), which must edit exactly those files
**When** the check runs
**Then** that one commit is recognized as the sanctioned exception — identified by a `retro:` subject
plus a CFE `CHANGELOG.md` entry in the same commit — and excluded
**And** the check asserts the exception is used **exactly once within this effort's range** and
carries a CHANGELOG move, so it cannot be borrowed to slip an implementation change through
(rebuild-slice retros land under the rebuild Spec's own Rule-2 obligation, outside this count)

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

**SM-4 SATISFIED — CFE v8.82.0, 2026-08-21** (provisional; re-verify tracked as `DW-5-4-1`).
The external event occurred 2026-08-20: CFE MINOR v8.82.0 landed (merge `604549100a`, followed
same-day by PATCH passes v8.82.1–v8.82.3). Verified three ways on 2026-08-21:
(1) **Zero Mason change** — `git diff --name-only 604549100a~1 604549100a -- src/shared/packages/pyforge-mason`
is empty; only CFE surface files moved. (2) **The improvement reaches a Mason verb** — the
`optimize_recipe` adapter wraps `recipe_optimizer.py` (`cfe.py` `_CFE_SCRIPTS`), whose
`_read_conda_forge_python_floor()` v8.82.0 repaired: executed A/B shows the pre-8.82.0
`parents[3]` walk resolves `.claude/` as repo root (pinning file unreachable — the hardcoded
`3.10` fallback fired on every call since it shipped), while the new `_paths.get_repo_root()`
resolves the real root and finds `.pixi/envs/local-recipes/conda_build_config.yaml`. Every
network-touching verb likewise inherits `_http.py`'s v8.82.x JFrog host-gating. (3) **The
affected verb re-runs green through the inherited code** — `mason recipe optimize
recipes/channels --format json` → `status: ok`, real STD-002 suggestion returned.
**Provenance note, recorded honestly:** v8.82.0 was produced by this effort's own closing
retrospective (Story 5.5, Rule 2), not by an unrelated effort. The live `python_min` floor
(`3.10`) currently coincides with the old fallback, so the verb-level output delta materializes
only when conda-forge bumps the floor. Both caveats are why this record is provisional:
`DW-5-4-1` re-confirms at the next organic CFE MINOR (one produced outside Mason's own chain).

**SM-4 re-verified — CFE v8.91.7, 2026-10-04** (Story 27.2 closes `DW-5-4-1`). Organic CFE
MINOR/PATCH chain since v8.82.0 includes doctor Story 41.x test-only bumps and mason Story
27.2's v8.91.6–8.91.7 surface work — all outside `src/shared/packages/pyforge-mason/`.
Re-ran `pixi run --frozen -e pyforge-mason pyforge mason recipe optimize recipes/ironcalc
--format json` → `status: ok`, `suggestions_found: 0` (inherits `_paths.get_repo_root()` floor
read and v8.82.x host-gating with no Mason diff). Same command on `recipes/channels` still
surfaces STD-002 for the co-located legacy `meta.yaml`, confirming the verb still reads live
CFE optimizer output without a Mason code change.

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

## Epic 6: The CFE rebuild — pilot slice, parallel-run, and the re-scope gate

**Value delivered.** The feasibility spike of `spec-conda-forge-expert-rebuild`, decomposed
through its own re-scope gate and NO further. **Operator directives (2026-08-10,
in-session): (1) "the current conda-forge-expert skill is unsustainable — we rebuild and
shift to using the mason rebuilt version"; (2) cutover shape = PARALLEL-RUN both, cut over
at the end** — chosen over per-slice cutover with the atlas precedent on the table, and
survivable only with the three CAP-3 mitigations: the equivalence harness (divergence reds
CI), the dual-landing rule (Rule-2 knowledge lands in both homes while parallel), and the
detector-enforced end cutover (the campaign cannot close until every caller flips and
legacy retires). AD-15 (amended) sanctions this effort as the CFE surface's writer under
these gates; the mason-CLI effort (Epics 1-5) remains wrap-only; the live skill stays
authoritative for all conda-forge work at every commit until the end cutover. The end
cutover itself is decomposed later, from 6.4's decision — it is this epic's declared
terminal obligation, not its scope.

### Story 6.1: Slice map and campaign state
**Given** the CFE surface (3 tiers, ~67 canonical scripts, 106 gotchas) **Then** CAP-1's
slice map exists with explicit ordering and the first slice named (recipe generation), and
CAP-4's file-based campaign state initializes (mapped → briefed → compiled → parallel →
audited; cut-over/retired are campaign-end states), resumable from state alone.

*Effort: S. Realizes rebuild-Spec CAP-1, CAP-4.*

### Story 6.2: The divergence-and-endgame guard, proven red first
**Given** the slice map **Then** CAP-3's detector (registered in `scripts/detectors.py`)
enforces all three parallel-run clauses — (a) a parallel slice with a red or stale
equivalence-harness result reds CI; (b) a Rule-2 retro landing in the live skill and not
mirrored to affected slice briefs reds CI; (c) at the declared endgame, any caller still
resolving to legacy reds CI — each clause proven red by a fixture before any slice lands.
**Deps:** S-6.1.

*Effort: M. Realizes rebuild-Spec CAP-3.*

### Story 6.3: Pilot slice — recipe generation, built and parallel-validated
**Given** the recipe-generation slice (generator + satellites + MCP tools + wrappers +
G54/G91/G94c/G98 knowledge as verbatim brief inputs) **Then** CAP-2 end-to-end:
Skill-Forge brief → compiled replacement → existing regression tests pass UNMODIFIED →
the equivalence harness reports zero divergence on the shared corpus → skf-audit-skill
reports zero drift. **The old path stays authoritative; no caller flips** — flip and
retirement belong to the campaign-end cutover. **Deps:** S-6.2.

*Effort: L. Realizes rebuild-Spec CAP-2.*

### Story 6.4: The re-scope gate — measured cost, recorded decision
**Given** the completed pilot **Then** a dated re-scope note in campaign state records the
measured cost — including the dual-maintenance burden parallel-run adds — and the
go/adjust/stop decision for every remaining slice AND the end-cutover plan. **No second
brief is written before this lands**; the remaining slices and the endgame decompose only
from this decision. **Deps:** S-6.3.

*Effort: S. Realizes rebuild-Spec CAP-4's re-scope gate.*

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
2. **OQ-E2** — RESOLVED 2026-08-13 (S-3.5's spec, PRD OQ-2, spine OQ-A2): `pixi upload prefix
   --channel <name>` -- the only pixi-upload subcommand whose destination maps 1:1 onto
   `channel:<name>`'s bare-name vocabulary; `pixi publish` and `anaconda upload` were both ruled
   out (see PRD OQ-2 for the reasoning).
3. **OQ-E3** — S-4.1's engine: `conda-lock` or `pixi` (PRD OQ-4). May need both adapters.
4. **OQ-E4** — S-2.2's deny-list content (spine OQ-A3): the concrete pattern set must be reviewable
   and hard to weaken silently. Needs a review gate of its own.
5. **OQ-E5** — RESOLVED 2026-08-10 (correct-course): S-5.2 scopes automatically to commits
   touching `src/shared/packages/pyforge-mason/**`; rebuild-effort commits are governed by
   `spec-conda-forge-expert-rebuild`'s own gates, outside this check.

## Standing contracts (no stories until their triggers fire)

- **spec-django-accelerator-framework** (2026-08-14): the accelerator CONTRACT every PyForge
  Django surface renders to — CAP-1 documented with two conforming realizations
  (python-agent-platform's `src/platform/` render, Story 10.1; steward's dashboard); CAP-2
  (the templating engine) explicitly parked on the dream's own third-surface trigger. No
  stories are minted here until that trigger fires — this entry is the chain reference.

## Epic 7: Machine-checked recipe knowledge

**Spec binding.** Decomposes `spec-machine-checked-recipe-knowledge` CAP-1..2 (seeded from
the 2026-08-22 seven-repo analysis; auto-recipe pattern, unlicensed — pattern only).
Rules 1/2 govern (CFE surface).

### Story 7.1: The failure catalog derives from the skill spec
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-machine-checked-recipe-knowledge CAP-1
**Given** SKILL.md's G-corpus **Then** `failure-catalog.yaml` regenerates deterministically —
one row per gotcha class with greppable `symptom_signature` tokens and an `enforced_by:`
pointer or explicit null — derived-artifact discipline (hand edits detectably wrong).

### Story 7.2: The pointers lint and the drift gates
**Type:** feature • **Effort:** S • **Deps:** S-7.1 • **FR/AD:** spec-machine-checked-recipe-knowledge CAP-2
**Given** the catalog **Then** every non-null `enforced_by` resolves against the live CFE
check/test surface, catalog↔SKILL.md drift fails CI, and the null-rows report is the
machine-check backlog — planting a bogus pointer or editing a gotcha without regenerating
reds the suite.

## Epic 8: One pixi base-layer discipline across the Containerfiles

**Spec binding.** Decomposes `spec-pixi-container-image` CAP-1 (the Dream's trigger FIRED
— three Containerfiles ship; premise corrected in the Dream).

### Story 8.1: The convention is written and guarded
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pixi-container-image CAP-1
**Given** the three Containerfiles (root, src/platform, compose/dbgpt) **Then** one
documented base-layer convention holds (registry-pinned `ghcr.io/prefix-dev/pixi` tags,
multi-stage materialization, secrets only via `--mount=type=secret`) with a guard test
that reds on a planted ENV-credential or unpinned base.

## Epic 9: External integration seams

**Spec binding.** The two stub stories minted by the 2026-08-22 extension-point reframing
(operator decision): the fleet ships SOCKETS so these capabilities develop and integrate
separately — including as air-gapped solutions — never as core builds. Contracts live in
`spec-reusable-cicd-workflows` and `spec-miniforge-installer` (§ Extension contract).

### Story 9.1: The repo's CI is consumable via workflow_call
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-reusable-cicd-workflows (extension contract)
**Given** the existing plain-Actions workflows **Then** a thin `on: workflow_call`
reusable wrapper exists with documented inputs/secrets, provably consumable from another
repo via `uses:` (and vendorable where egress is blocked) — conda-forge-tracker is the
named first candidate consumer; the 63-family shape stays out of scope.

### Story 9.2: The air-gap distribution contract has a socket
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-miniforge-installer (extension contract; coordinate with steward 12.3)
**Given** no distributable exists or is built here **Then** the contract doc (mirrored
channel set, pixi bootstrap path, verification hooks), an EMPTY backend registry
(`_SUPPORTED_MODULES` precedent), and a shape-validating test ship — so any external
installer registers and validates as a separate deliverable; 12.3's air-gap run consumes
the same contract.

## Canopy obligations (2026-08-24)

Phase 5 (`bmad-correct-course`, `docs/dreams/pyforge-unifying-strategy.md`) records how
**pyforge-mason** mounts into the Platform Canopy. **Epic 10** is the CAP-18 build-engine hook.
**Epic 11** (2026-08-25) is station persona + first portal job. **`conda-forge-expert` is not replaced** (no mason SKF that supersedes CFE). Do **not** copy steward Epics 18–30. Cite **parent AD-n**
(`architecture-pyforge-mason-2026-07-25`) vs **canopy AD-n**
(`architecture-pyforge-unifying-strategy-2026-08-24`); bare `AD-n` is review-blocking.

### Boot and state (parent AD-1 / BS-8 / steward S-25.4)

- Mason **must not** scan MinIO or any object store on boot. Restart reconciliation is against
  **PostgreSQL** (canonical anchor) plus **RWX-mounted files** when they exist.
- **Forbidden:** boto3, MinIO client, or S3-backed artifact indexing as mason runtime backing
  store. The Dream's BS-8 Mason/MinIO example does **not** apply to mason.

### Domain skill (canopy:AD-17)

- **`conda-forge-expert` stays the hand-authored operating skill** — mason's recipe/build
  authority for conda-forge work (Rule 1). Do **not** compile a `pyforge-mason` SKF that
  replaces CFE. Persona (Epic 11) consults CFE.

### Operator-owned packaging (out of mason epic chain)

- Liquibase, OpenFeature feedstocks, and `cachebox` 5.x packaging are **operator-owned**
  (steward S-26.3 / CAP-9 / CAP-13 gates). Not mason epic work in this chain.

### Five-tier symmetry (steward Epics 19 / 21 / 29)

| Tier | Mason today | Canopy obligation | Steward owner |
| :-: | :--- | :--- | :--- |
| CLI | `mason` / `pyforge mason` — **shipped** (Epics 1–9) | Keep as primary local surface | — |
| Portal | — | `/stations/mason/` via `django-mason` reusable app; zero domain models in portal | Epic 19 |
| MCP | — | `POST /stations/mason/mcp` on host ASGI; dual-era handshake | Epic 21 |
| Domain skill | `conda-forge-expert` (hand-authored) | CFE never replaced | Epic 11 Never |
| Persona | — | `bmad-agent-mason` consults CFE; FR-13/FR-11 only | **Mason Epic 11** |

No second chrome, no extra public port — one modular-monolith ASGI process (canopy:AD-1, AD-5,
AD-10).

### Event backbone (steward Epic 24)

- When mason has an event **producer**, consume/produce **CloudEvents** on `pyforge.events`;
  poison payloads → `pyforge.events.dlq`. Event `type` values are dotted verbs registered in
  `django-pyforge`; payload validation lives in domain adapters, not at the stream boundary.
- Mason does not implement the backbone — it participates when a producer exists.

### Explicit non-goals

- Do **not** copy steward Epics 18–30 into mason's epic chain.
- Do **not** introduce MinIO/object-store boot reconciliation for mason.
- Do **not** replace `conda-forge-expert` with SKF-compiled output.
- Do **not** own Liquibase/OpenFeature/cachebox packaging in mason stories.

## Operating-model obligations (2026-08-24)

Estate-wide bind from Unifying Strategy Grounding (hooks/plugins principle + Q1–Q8)
and steward `sprint-change-proposal-2026-08-24-operating-model.md` (**§6 revisited**).
**Hooks and plugins (canopy:AD-21):** as far as possible every layer is replaceable —
the process owns hook specifications; a plugin implements or replaces a layer without
a fork. Kedro
[architecture overview](https://docs.kedro.org/en/stable/getting-started/architecture_overview/)
*names* the split; it does not require this station to be a Kedro project. Warden owns
PR-gate hook specs (Q8). This station owns its process hooks.

**Always / Never (every station):**
- Five-tier completeness is the **03** shape. 01/02 stay spec+script or spec+skill.
- Guildhall / switcher must not tile `work_class` 01 or 02 as a station.
- Golden Path: humans, CI, and agents invoke the same Pixi task names.
- CloudEvents: `spec_id` + git sha + SBOM purl; Jira optional; never fail for a missing key.
- Path B = Agent Canopy + this station's persona. Tachyon = production LLM provider adapter.
- Lane 2 = HTMX; station compute = FastAPI. No station-local DRF JSON:API on the portal.
- Design station processes as hook specs + plugins (AD-21). Do not fork a process to swap a vendor.
- **Never** a competing PR quality-gate verdict. Quality scanners register as **Warden plugins**.
- Scorecard measures are unpublished (human + agent + team; draft later). Do not optimize to invented metrics.

**Mason-local:** Build-engine variants (rattler-build, conda-build, sandboxes) are **station hook plugins** (Story **10.1**), not CI quality gates. A green Mason build is not a Warden verdict. Do not mint a portal/MCP/persona for 01 recipe experiments.

**Pointers:** `change-history/sprint-change-proposal-2026-08-24-operating-model.md`;
`change-history/sprint-change-proposal-2026-08-24-hook-specs.md`;
steward `sprint-change-proposal-2026-08-24-hook-specs.md`; `DW-OM-2026-08-24`.

## Epic 10: Build-engine hook spec

**FR-45.** Deps: steward S-32.1. Today's rattler-build (or current default) stays the default plugin.

### Story 10.1: Extract the build-engine hook

As a mason operator,
I want rattler-build and conda-build as plugins on the shared contract,
So that swapping a build engine does not fork the mason process.

**Type:** feature • **Effort:** L • **Deps:** steward S-32.1 • **FR/AD:** FR-45 • canopy:AD-21
**Given** the replaceable build-engine layer **When** the hook spec lands **Then** today's backend is the default plugin
**And** an alternate engine plugin can register without a process fork
**And** a successful mason build is not published as a PR quality-gate verdict

## Epic 11: Mason persona and one portal job (CFE stays)

Does **not** copy Canopy 18–30. **Never** a SKF skill that replaces `conda-forge-expert`.

### Story 11.1: BMAD persona consults conda-forge-expert

As an autonomous agent,
I want a `bmad-agent-mason` persona that consults `conda-forge-expert`,
So that Path B uses CAP-5 grammar and CAP-4 MCP without a second recipe skill.

**Type:** feature • **Effort:** M • **Deps:** S-10.1 • **FR/AD:** canopy FR-38 • canopy:AD-17
**Given** CFE is the operating skill **When** this story completes **Then** the persona transcript uses only `pyforge mason …` and `POST /stations/mason/mcp`
**And** no `skf-create-skill` output replaces CFE
**And** 01 recipe experiments still do not mint a portal/MCP/persona (existing Never)

### Story 11.2: First portal slice — last diagnose

As a mason operator,
I want `/stations/mason/` to show one `mason diagnose` (or equivalent) result,
So that one operator job works in HTMX on the host.

**Type:** feature • **Effort:** M • **Deps:** S-11.1 • **FR/AD:** canopy FR-10 • canopy:AD-7
**Given** an authenticated mason-role session **When** the operator opens `/stations/mason/` **Then** one diagnosis renders via PortalClient only
**And** no raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy, no MinIO

## Epic 12: The CFE rebuild continues — gate closure and slice 2

**Spec binding.** Resumes `spec-conda-forge-expert-rebuild` (CAP-2, CAP-3, CAP-4 residuals)
from Epic 6's re-scope gate (decision ADJUST, 2026-08-21, campaign-state.yaml): Stories
12.1–12.5 clear the guard's live clause-(b) finding and close the gate's four recorded
pre-conditions plus its own enforcement gap (GATHERED GAPS #2/#5); Stories 12.6–12.8 carry
slice 2 to CAP-2's bar and mint the second re-scope checkpoint. Slices 3–5 and the end
cutover (CAP-3 clause (c)) decompose only from 12.8's recorded decision, not here — the same
decompose-no-further discipline Epic 6 held. Rules 1/2 govern (CFE surface); the live skill
stays authoritative for all conda-forge work at every commit until the end cutover.

### Story 12.1: Landed retros are mirrored into the pilot brief
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-conda-forge-expert-rebuild CAP-3 (dual-landing rule)
**Given** the guard's live clause-(b) finding (4 qualifying CFE Rule-2 retros in
`806cb63046..HEAD`, newest `565ef7d194`, none mirrored; `brief_mirrored_through: null`)
**Then** each landed retro's CFE-surface delta is mirrored into slice 1's brief,
`brief_mirrored_through` records the newest mirrored SHA, and
`pixi run -e local-recipes cfe-rebuild-guard-check` exits clean — the detector, not this
story, re-opens the duty on the next unmirrored retro.

### Story 12.2: CI enforcement for the guard and the equivalence net
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-conda-forge-expert-rebuild CAP-3 (re-scope pre-condition (a))
**Given** the advisory-only detectors CI step (always `exit 0`, findings surface as
annotations only) **Then** either cfe-rebuild-guard-check findings block CI as a red check,
or a dated conscious acceptance of advisory-only enforcement lands in campaign-state.yaml —
and in BOTH branches the CFE regression suite plus `test_slice1_equivalence.py` run in a CI
workflow, so divergence has a place to red.

### Story 12.3: The real audit tool backs the pilot zero-drift claim
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-conda-forge-expert-rebuild CAP-2 (re-scope pre-condition (b))
**Given** slice 1's `equivalence: green` rests partly on a manual sha256 substitute
(`forge-tier.yaml` absent in the audit worktree; skf-audit-skill halts at exit 3,
`forge-tier-missing`) **Then** skf-setup has run in the worktree doing the audit,
skf-audit-skill completes end-to-end against the compiled
`.claude/skills/cfe-recipe-generation/` package, and its verdict replaces the substitute in
campaign-state.yaml — drift, if surfaced, honestly reopens slice 1's record rather than
being suppressed.

### Story 12.4: The re-scope gate is machine-enforced
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-conda-forge-expert-rebuild CAP-3/CAP-4 (GATHERED GAPS #5)
**Given** the gate is honored by session discipline alone (nothing reads
`re_scope_gate`) **Then** `scripts/cfe_rebuild_guard_check.py` gains a clause (d): a
`brief_path` set on any slice of order ≥ 2 while campaign-state.yaml does not record the
four pre-conditions closed (or explicitly waived by a human) is a finding — proven red by a
fixture before it lands, matching Story 6.2's discipline.

### Story 12.5: The ownership decision is recorded
**Type:** chore • **Effort:** XS • **Deps:** — • **FR/AD:** spec-conda-forge-expert-rebuild Open Question 1 (re-scope pre-condition (d))
**Given** SPEC.md's Open Question 1 (mason owns the whole rebuild vs per-slice station
ownership — atlas arguably owns the Slice-3 tier) predates any slice beyond the first
**Then** the operator's decision is recorded dated in SPEC.md § Open Questions and mirrored
into campaign-state.yaml, and slice 3's brief authorship follows it — until recorded,
slice-2 briefing stays gated (12.6's Deps).

### Story 12.6: Slice 2 brief — cross-slice dependencies re-derived first
**Type:** feature • **Effort:** M • **Deps:** S-12.2, S-12.3, S-12.4, S-12.5 • **FR/AD:** spec-conda-forge-expert-rebuild CAP-2/CAP-4 (re-scope pre-condition (c))
**Given** the gate's pre-conditions closed **Then** skf-brief-skill produces slice 2's brief
with its full cross-slice dependency list re-derived (not just re-confirming the
CVE-DB/Slice-3 ordering risk slice-map.md already names, and deciding
`native-build.sh`/`build-locally.py`'s cutover scope no later than this brief), the relevant
gotchas as verbatim inputs, and campaign-state slice 2 at `briefed` with `brief_path` set —
budgeting at least one BLOCKED-and-retry cycle per slice 1's precedent.

### Story 12.7: Slice 2 compiled and equivalence-validated
**Type:** feature • **Effort:** L • **Deps:** S-12.6 • **FR/AD:** spec-conda-forge-expert-rebuild CAP-2
**Given** the brief **Then** CAP-2's bar holds for slice 2: compiled replacement; the
slice's existing regression tests pass UNMODIFIED; the equivalence harness reports zero
divergence on the shared corpus; the REAL skf-audit-skill reports zero drift (no manual
substitute this time); the old path stays authoritative and no caller flips (flip and
retirement remain campaign-end, CAP-3 clause (c)); and the story closes with its Rule-2
retro mirrored into the slice briefs (clause (b) green).

### Story 12.8: The slice-2 re-scope checkpoint
**Type:** chore • **Effort:** S • **Deps:** S-12.7 • **FR/AD:** spec-conda-forge-expert-rebuild CAP-4
**Given** the completed slice 2 **Then** a second dated re-scope note in campaign state
records slice 2's measured cost and the go/adjust/stop decision for slices 3–4, slice 5's
opportunistic porting, and the end-cutover decomposition trigger — no slice-3 brief and no
endgame stories before this lands (the 6.4 note's own recommendation before the 12.3x
slice).

---

## Validation note — 2026-08-26 (chain-currency truth-up)

Validated against the same-day truth-upped ARCHITECTURE-SPINE and the as-built code in
`src/shared/packages/pyforge-mason/`: all 50 stories across Epics 1–11 are `done` in the tracked
`sprint-status-ledger.yaml` (station complete per fleet ledger 2026-08-21; Stories 10.1, 11.1
and 11.2 landed post-completion, 2026-08-25/26 — commits `6359c4676d`, `110f0c5212`,
`5a957ef25f`). Every `### Story` heading here still maps 1:1 to a ledger story key; no heading
or status was changed by this note. Frontmatter counts corrected 6/42 → 11/50 to match the
document's own contents. As-built divergences (engine choices, research-recommendation
adoption, SM-1's rehearsal-tier evidence) are recorded in the Spec/PRD/spine § Currency
reconciliation sections and in `retros/retro-pyforge-mason-2026-08-26.md`, not restated here.

## Reconciliation note — 2026-08-27 (spec-conda-forge-expert-rebuild)

`spec-conda-forge-expert-rebuild` reconciled against this chain: CAP-1 and CAP-4's gate are
decomposed-and-done (Epic 6, Stories 6.1/6.4); CAP-2 and CAP-3 are decomposed with recorded
residuals (the sha256 audit substitute, GATHERED GAPS #1; advisory-only CI enforcement, #2;
the unenforced gate, #5; plus the guard's live clause-(b) unmirrored-retro finding). The
uncovered remainder — gate closure and the campaign's continuation through slice 2 — is
minted as **Epic 12** (8 stories, `backlog` in the tracked ledger); slices 3–5 and the end
cutover stay gated on Story 12.8's checkpoint by design. The Spec's status moved
`ready → in-progress`; its dated decomposition record lives in
`specs/spec-conda-forge-expert-rebuild/SPEC.md`. Frontmatter counts corrected 11/50 → 12/58.
Same pass: Story 5.4's closing-run spec was confirmed never promoted from Tier-3 — the
tracked recheck spec (`specs/spec-5-4-free-inheritance-verification-2.md`) now carries the
dated Resolution record standing in for it (landing evidence: `7a05d20034`, 2026-08-21).

## Epic 13: Two feedstock pins admit Python 3.14 (steward 43.5 hybrid decision)

Minted 2026-09-02 from steward's `sprint-change-proposal-2026-09-02-red-team-high.md`
§ 7 amendment. The operator chose the hybrid interpreter option: raise the platform to
one interpreter (`3.14.*`) via feedstock work **and** keep `mcp-host` as MCP-SDK
isolation. Real solver probes (2026-09-02) found exactly two remaining blockers, both
upstream pins collapsed by `noarch` recipes. Both are maintainer-edit PRs on feedstocks
rxm7706 graduated; both run under `conda-forge-expert` (Rule 1) with a Rule 2 retro.
Steward **43.6** (the image flip) is gated on both. **Approved by the operator 2026-09-02** together with steward Epics 40–43.

### Story 13.1: langflow-base onnxruntime pin admits Python 3.14
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** steward 43.5 • steward `DW-FU-10-4` • CFE G26
**Given** `langflow-base` pins `onnxruntime >=1.20,<1.24` (no `cp314` below 1.25.1)
**When** the run-dep becomes `>=1.20` and the wheel METADATA is patched to one range
**Then** `python=3.14.* + langflow + dbgpt + django` solves, `pip check` passes on 3.12 and 3.14, and `import langflow.main` works on 3.14.

### Story 13.2: dbgpt-client sqlalchemy cap admits Python 3.14
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** steward 43.5 • CFE G26 (DB-GPT case study)
**Given** `dbgpt-client` pins `sqlalchemy >=2.0.25,<2.0.29` (no `cp314` in range)
**When** the cap becomes `<2.1` with the METADATA patch
**Then** `python=3.14.* + dbgpt + dbgpt-serve + dbgpt-app + django` solves and the sidecar REST round-trip passes on 3.14.

## Epic 14: The eval-quality Windows variant (spec-bmad-suite-lifecycle CAP-7 relay)

**Spec binding.** The mason-side relay of `spec-bmad-suite-lifecycle` CAP-7 / the channel-product
hole #2 (2026-09-05): `bmad-eval-quality` ships only the `__unix` noarch variant, so win-64 is
excluded and the pixi pin sits in the linux-64 / osx-arm64 target tables. **HARD boundaries:**
the recipe goes through `conda-forge-expert` (Rule 1) and the effort ends with a CFE retro
(Rule 2); the commit pin `0.2.0.dev0 @ 3172162f` does not move here; `anaconda upload` is the
operator's step.

### Story 14.1: `bmad-eval-quality` builds a `__win` variant
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-bmad-suite-lifecycle CAP-7 • spec-bmad-suite-channel-product (relayed hole #2) • CFE Rule 1 + Rule 2
**Surface:** `recipes/bmad-eval-quality/recipe.yaml` (+ `bld.bat` / `build.bat` per the `.cmd`-shim rule), `recipes/bmad-suite/suite-members.yaml` (unchanged row), `pixi.toml` (pin moves back to the shared table once solvable on win-64; `environment.yaml` regenerated), `install-matrix.md` hazard cell
**Given** the unix-only variant on the channel **When** the recipe gains the Windows build (`call` for `.cmd` shims, `noarch_platforms` carrying win-64, `build.number` bumped for the same version) and builds green locally via `recipe-build` **Then** the pixi pin can leave the target tables, `steward suite pipeline-truth` reads the member current on all three platforms after the operator uploads, and the CFE CHANGELOG carries the retro entry


## Epic 15: Close the CFE rebuild campaign at slices 1–2

**Spec binding.** `spec-conda-forge-expert-rebuild`, CAP-2 / CAP-3 / CAP-4. Minted 2026-09-09
from the operator's fleet-readiness ruling
(`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
§ 2.3 **C2**, evidence rows mason-B1 / mason-B2 / mason-B3): OQ3 answered **NO** — full scope does
not survive the measured cost, so the endgame is declared over **slices 1–2 only**. Slice 3
(atlas-owned under Story 12.5, 12.3× slice 1) and slice 4 are **not briefed and will not be**;
`campaign.re_scope_gate_2` is moot. OQ4 answered **delete-on-cutover, no stubs** — Mason reaches
CFE by filesystem path, not by import, so a stub module cannot serve a path resolver, and CAP-5's
degradation path already handles a missing root. **HARD boundaries:** the work edits
`.claude/skills/conda-forge-expert/**`, so it runs through `conda-forge-expert` (CLAUDE.md **Rule 1**)
and ends with a CFE retro (**Rule 2**). Rule-2 retros during the overlap window still land in the
**legacy** skill only and dual-land into the compiled slices in the same PR (the ratified OQ5
constraint / CAP-3 clause (b)).

**Also carried here (added 2026-09-09).** This epic is mason's **outstanding CFE-skill-surface
obligations**, not only the campaign close — the two stories share one surface, one Rule-1 route
and one Rule-2 retro window, so batching them means a single CFE release closes both instead of
two separate skill-surface PRs. Story 15.2 lands the Rule-2 retro that Story 13.2 deferred
(`DW-13-2-1`): CLAUDE.md Rule 2 says a conda-forge effort is **not done** until its retro lands,
and that retro has now been unwritten across four CFE releases.

**Batching plan superseded (2026-09-10).** Story 15.1 shipped its own independent CFE Rule-2
retro (v8.90.2, PATCH) per its own spec's explicit instruction — the "single CFE release closes
both" batching above did not hold. Story 15.2 lands its own separate version bump (v8.90.2+1 at
whatever PATCH/MINOR the retro's findings warrant).

### Story 15.1: Close the CFE rebuild campaign — cut callers over to slices 1–2 or retire the mirrors
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-conda-forge-expert-rebuild CAP-2 / CAP-3 / CAP-4 • CFE Rule 1 + Rule 2
**Surface:** `.claude/skills/conda-forge-expert/**` (the two compiled slices `cfe-recipe-generation` and `cfe-recipe-lifecycle`), `.claude/scripts/conda-forge-expert/**` (wrapper redirects, if any caller flips), `.claude/tools/conda_forge_server.py` (MCP registrations, if any caller flips), `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/{campaign-state.yaml,slice-map.md}`
**Given** the endgame is declared (`campaign.endgame_declared: true`, 2026-09-09) over slices 1–2, with `campaign.callers` empty and both slices still `status: compiled`
**When** each of the two compiled slices is resolved one way — either its callers are flipped to it (`campaign.callers` populated, every entry off `resolves_to: "legacy"`, slice `status: cut-over`) **or** the mirror is retired (slice `status: retired`, the compiled copy **deleted**, no dated stub left behind) — and the standing per-release byte-re-port obligation ends with it
**Then** `pixi run -e local-recipes cfe-rebuild-guard-check` is **clean** (clause (c) has no legacy caller surviving the declared endgame; clause (b) has no briefed slice behind a landed retro), `campaign-state.yaml` records the disposition per slice with a dated note, the Spec's status flips off `in-progress` via a memlog event, and the effort ends with a `conda-forge-expert` retro entry in `CHANGELOG.md` (Rule 2)
**Sequencing note (text only, not a `Deps:` token — it names a foreign station's story):** this story must land **before** steward's `fnd:CAP-3` story (steward Epic 44, S-44.6, "CFE comes home") moves the CFE cell to `skills/domain/conda-forge-expert/`. This Spec's `surface:` and the slice map are written against `.claude/skills/conda-forge-expert/**`; closing the campaign first makes 44.6 a pure move instead of a move that must also re-point a live campaign.
**Named surface-baseline clause (added 2026-09-09, folding the C-6 residue).** This story already has to re-stamp scoped surface baselines for every governed path it deletes or moves, so it also carries one unrelated-but-adjacent allowlist cleanup: **delete `scripts/spec_surface_allowlist.txt:100`** — the `scripts/failure_catalog_check.py` entry whose own comment reads *"allowlisted pending mason claiming it via a proper folder-format spec"*. `spec-machine-checked-recipe-knowledge` **is** that folder-format spec, and its 2026-09-09 re-derive adds `scripts/failure_catalog_check.py` to its `surface:`, so the allowlist entry becomes a governed path listed twice. **Done means:** the line is removed, `spec-surface-check` reports no finding for that path, and the baseline is re-stamped **scoped** — `python scripts/spec_surface_check.py --write-baseline --spec pyforge-mason/spec-machine-checked-recipe-knowledge` — **never a bare `--write-baseline`** (the baseline reads the working tree and `git ls-files`, and this repo's tree is routinely dirty with other stations' work; a bare stamp bakes their edits into mason's baseline). Stage the file before stamping.

### Story 15.2: Rule-2 retro for Story 13.2 lands in the CFE skill
**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** CLAUDE.md **Rule 2** (non-optional, non-deferrable) • `DW-13-2-1` • CFE Rule 1 + Rule 2
**Surface:** `.claude/skills/conda-forge-expert/SKILL.md` (G26 gains the Story-13.2 case study), `.claude/skills/conda-forge-expert/CHANGELOG.md` (a dated version entry), `.claude/skills/conda-forge-expert/MANIFEST.yaml` + `config/skill-config.yaml` (version bump), `config/failure-catalog.yaml` (regenerated if a gotcha's title or body moves), `_bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md` (close `DW-13-2-1`)
**Given** Story 13.2 (`dbgpt-client`'s `sqlalchemy` upper-bound cap admitting Python 3.14) shipped with its Rule-2 CFE retro **deferred** — mason's own meta-test `test_persona_consults_cfe.py::test_conda_forge_expert_not_replaced_or_skf_nested` fails when `SKILL.md`/`CHANGELOG.md` change on a story branch, so the retro could not land in-story — and the 2026-09-08 re-verification confirmed it is **still unwritten**: the G26 extension that *did* land (`SKILL.md:2454`) carries **Story 13.1's** `langflow-base` case study, not 13.2's, and no 13.2 entry exists anywhere in `CHANGELOG.md` through v8.90.1
**When** the retro runs against Story 13.2's actual evidence — the `dbgpt-client` `sqlalchemy >=2.0.25,<2.0.29` cap, why the recipe run-dep loosen alone was insufficient, and which upstream files the source patch had to touch for the wheel METADATA to agree (the G26 mechanism) — and lands as a **maintenance PR on the CFE surface**, outside any mason story branch, so the meta-test is satisfied by construction
**Then** `CHANGELOG.md` carries a dated entry naming Story 13.2, `SKILL.md`'s G26 gains the `dbgpt-client` case study distinct from 13.1's, the skill version is bumped **per semver** (PATCH for a case-study/clarification, MINOR if a new gotcha or section falls out), `MANIFEST.yaml` + `config/skill-config.yaml` agree with `SKILL.md`'s frontmatter `version:` (they have drifted apart before — v8.90.0 fixed exactly that), `config/failure-catalog.yaml` is regenerated if any gotcha text moved (`tests/meta/test_failure_catalog_freshness.py` guards it), and **`DW-13-2-1` is closed with a dated resolution note** rather than another `verified: still-open` line
**Rule 1/2:** the whole story is CFE-surface work — it runs through `conda-forge-expert`, and it **is** the Rule-2 retro, so it does not spawn a further one. **Mirror obligation:** per the ratified OQ5 constraint / CAP-3 clause (b), if this retro touches any script mirrored into a compiled slice, byte-re-port it and advance that slice's `brief_mirrored_through` **in the same PR**; a docs-only retro needs no re-port, but verify that rather than assuming it, and keep `cfe-rebuild-guard-check` clean either way.

## Epic 16: Turn on what is built — mason's realization-gate and coverage residue

**Spec binding.** `spec-pyforge-mason` CAP-2 (the `recipe` verb family) + CAP-5 (graceful
degradation), plus the ungated-surface and under-covered-guard residue the same pass found
(`spec-packaging-factory`, `spec-pixi-container-image`). Minted 2026-09-09 from the operator's fleet-readiness ruling
(`fleet-readiness-decision-batch-2026-09-09.md` § 2.3 **C6**, evidence row mason-B5): mason is one
of the twelve `done`-but-not-in-effect capabilities the pass found, and C6 places the effect story
on the **owning station's** epics with steward Epic 49 carrying only an index row. The gap is
concrete and dual: `mason doctor` in mason's own pixi env reports
`cfe_import_floor_satisfied: False`, `cfe_import_floor_missing: ('truststore', 'conda-forge-metadata')`
and **`unavailable_verbs: ('recipe',)`**, because `[feature.pyforge-mason.dependencies]`
(`pixi.toml:281-283`) declares neither floor dependency while `cfe.py:180-186`'s `CFE_IMPORT_FLOOR`
requires both — and nothing in the estate invokes `mason recipe` / `mason package` /
`mason environment` (one comment at `pixi.toml:797`, zero call sites; all recipe work still routes
through `pixi run -e local-recipes recipe-build`). Story 49.2's effect check applies: **a caller
outside its own test file.**

**Scope widened 2026-09-09** beyond the `recipe` verb family to the pass's two other
mason-owned *coverage* gaps, because both are the same shape — something built, and nothing
watching it: **16.3** (mason's 46-tool MCP surface is ungated for CLI⇄tool parity while marshal's
is gated) and **16.4** (the Containerfile convention guard enumerates three of four files).
16.4 belongs by subject to **Epic 8** (`spec-pixi-container-image`, Story 8.1 "The convention is
written and guarded"), and is carried **here** deliberately: `epic-8` reads `done` in the tracked
ledger, and hanging a `backlog` story off it would flip that rollup and misreport a genuinely
completed epic across the fleet picture. Recorded so the subject-vs-home split is not read as a
mis-file.

### Story 16.1: Mason's own env satisfies the CFE import floor
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-2 / CAP-5 • steward Epic 49 (C6 effect gate) • CFE Rule 1 + Rule 2
**Surface:** `pixi.toml` (`[feature.pyforge-mason.dependencies]`), `environment.yaml` (regenerated — the sync check is ungated by the `maintenance` label), `src/shared/packages/pyforge-mason/tests/**` (a regression assertion)
**Given** `mason doctor` reports `unavailable_verbs: ('recipe',)` and `cfe_import_floor_missing: ('truststore', 'conda-forge-metadata')` in the `pyforge-mason` env
**When** `truststore` and `conda-forge-metadata` are added to `[feature.pyforge-mason.dependencies]` at floors matching what `cfe.py`'s `CFE_IMPORT_FLOOR` actually requires, the lock is re-solved and `environment.yaml` regenerated
**Then** `pixi run -e pyforge-mason mason doctor` reports `cfe_import_floor_satisfied: True`, an empty `cfe_import_floor_missing`, and **no** `recipe` entry in `unavailable_verbs`; a test pins the floor so a future dependency edit that drops either package reds instead of silently re-disabling the verb family; and CAP-5's degradation path is re-verified (a deliberately broken floor still exits 0 with the verb reported unavailable — the graceful-degradation contract must not regress into a hard failure)
**Rule 1/2:** this is CFE-floor work — the change is driven by `cfe.py`'s import floor, so the story runs through `conda-forge-expert` and ends with the Rule-2 retro.

### Story 16.2: A first estate caller of `mason recipe`
**Type:** feature • **Effort:** S • **Deps:** 16.1 • **FR/AD:** spec-pyforge-mason CAP-2 • steward Epic 49 (C6 effect gate, "has a caller outside its own test file") • CFE Rule 1 + Rule 2
**Surface:** `pixi.toml` (one task), or `.github/workflows/**` (one step), plus whatever documentation names the route
**Given** the `recipe` verb family runs in mason's own env (16.1) but nothing in the estate invokes it — `pixi.toml:797` is a comment and there are zero call sites
**When** one real estate route is moved onto mason: a pixi task (or a CI step) that builds one recipe through `mason recipe build` rather than `pixi run -e local-recipes recipe-build`, chosen so the route is exercised on every run of an existing lane rather than only on demand
**Then** the caller exists **outside** mason's own test tree, a green run is recorded with its command and output, `mason doctor` reports the verb available on that lane's env, and the Unifying realization gate can read mason's CAP-2 as *exercised in the running estate* rather than *decomposed and merged*. The delegation boundary is unchanged — mason still wraps CFE (Rule 1), and the effort ends with the Rule-2 retro.

### Story 16.3: Mason's MCP tool surface passes the CLI⇄tool parity gate
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-packaging-factory (governs `.claude/tools/conda_forge_server.py`) • marshal `spec-agent-tool-surface` FR-155 / Story 18.2 (the primitive being extended) • CFE Rule 1 + Rule 2
**Surface:** `.claude/tools/conda_forge_server.py` (a declared CLI↔tool mapping + any CLI-only/tool-only allowlist), a new parity meta-test under `.claude/skills/conda-forge-expert/tests/meta/`, `pixi.toml` (the task, if a new one is needed) + the `SCRIPTS` list in `tests/meta/test_all_scripts_runnable.py` if a script is added (the three-place rule)
**Given** parity between a station's CLI verbs and its MCP tools is **a gated number, not review** for marshal only — `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py` drives `pyforge.marshal.mcp.parity` (`assert_cli_tool_parity`, `discover_cli_verbs`, `parity_findings`, `tools_by_cli_verb`, with explicit `CLI_ONLY_VERBS` / `TOOL_ONLY_NAMES` allowlists) against live `TOOL_SPECS` — while mason's **46** `@mcp.tool` registrations in `.claude/tools/conda_forge_server.py` have **no parity gate at all**, so a CLI wrapper can gain or lose a verb with no tool counterpart and nothing reds
**When** marshal's primitive is **extended over the CFE server** rather than re-implemented — the CLI surface derived from `.claude/scripts/conda-forge-expert/` and the pixi task registry, the tool surface from the live `@mcp.tool` registrations, with every deliberate asymmetry declared in an explicit allowlist carrying a one-line reason (not a silent skip)
**Then** the live inventory passes clean, a **fixture-injected** mismatch in each direction (an on-surface CLI verb with no tool; a tool with no CLI verb and no allowlist entry) **fails** the gate — proving the gate can fail, not merely that it passes — and the parity number is reported rather than asserted by review
**Boundaries (text only, no foreign `Deps:` token):** atlas's half of the marshal C10 routing — `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` — is **atlas's story to mint**, not mason's; this story touches no atlas file. If the extension needs a shared helper rather than a mason-local copy, propose it to marshal rather than forking `pyforge.marshal.mcp.parity` (a second independent copy of a gate is how the `_http.py` credential leak survived a "durable fix" — the CFE skill records that lesson explicitly). Rule 1 applies throughout; the effort ends with the Rule-2 retro.

### Story 16.4: The Containerfile convention guard derives its file list
**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pixi-container-image CAP-1 (restated 2026-09-09: *enumerated by glob, never a hard-coded list*) • steward Epic 49 (C6 effect gate)
**Surface:** `tests/packaging/test_containerfile_base_layer_convention.py`
**Given** the repo's two enumerations of its Containerfiles **disagree**: `scripts/pixi_version_registry.py:79-87` covers all four, while the convention guard's `CONTAINERFILES` tuple (`tests/packaging/test_containerfile_base_layer_convention.py:50-52`) hard-codes only three — omitting `src/platform/compose/mcp-host/Containerfile` (spec-mcp-era-isolation slice 1), which is therefore **ungoverned** by the registry-pinned-base and no-`ENV`-credential checks. The omitted file is compliant **today**; the finding is that nothing would notice if it stopped being
**When** the tuple is replaced by a **derivation** over the tracked tree (glob `Containerfile*`, git-tracked only, so an untracked scratch Containerfile cannot red the suite) — **not** by appending a fourth literal, which reproduces the same defect one file later
**Then** all four files are swept by both the `FROM` and `ENV` checks, a test proves the derivation actually **finds** them (a count assertion, or an explicit membership check for the previously-omitted path, so an empty glob cannot pass vacuously — an absence assertion that cannot be distinguished from having scanned nothing is the failure mode the fleet has hit before), a planted unpinned base or `ENV`-declared credential in the **fourth** file reds the suite, and `spec-pixi-container-image`'s Constraints line ("until ≥2 Containerfiles diverge") reads against four rather than three
**Note:** no `conda-forge-expert` involvement — this touches no recipe and no CFE surface, so Rules 1/2 do **not** apply to this story.

## Platform floor addendum — 2026-09-07

Every story in this epic set builds and tests against **Python 3.14 only**.
`pyforge-mason`'s `requires-python` was raised `>=3.12` -> `>=3.14` by marshal Story 32.2
(`spec-fleet-consistency-standard` CAP-5) to match the interpreter the workspace actually
installs. No story's acceptance criteria change; recorded here so a future story is not
written against a 3.12 assumption the estate cannot produce.

## Epic 17: The recipes/ fleet is stewarded (spec-fleet-stewardship fs:CAP-1..3)

**Retroactive.** All three CAPs were re-verified PASS on 2026-09-11 at HEAD `b36c8be118`
with mechanical evidence recorded in the Spec's own `verified:` lines, but no story was
ever written, so `chain-completeness`'s delivered-Spec arm flagged the Spec as
undecomposed. This epic documents a practice that is already in force; no new
implementation. Unlike mason's other epics this Spec governs a **continuous practice**
over `recipes/**` rather than a discrete build — which is why it carries
`surface-drift: exempt` (per-recipe governance is the CFE workflow, not spec
re-derivation) and adopts three legacy Tier-1 workflow specs as companions rather than
restating them.

### Story 17.1: The local mirror is the source of truth

As a recipe maintainer,
I want `recipes/<feedstock>/` edited first and verified locally before anything is
pushed upstream,
So that a feedstock never receives an unproven change and the mirror never drifts
behind what shipped.

**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** spec-fleet-stewardship CAP-1
**Surface:** `recipes/**` (`surface-drift: exempt`); `test_recipe_yaml_parse_audit.py`
**Given** recipe work could be done directly on a feedstock **When** this practice is in
force **Then** the local mirror is edited first, verified with a real build, and only
then pushed
**And** the parse audit holds the mirror machine-checkable
**Status:** done — re-verified 2026-09-11 at `b36c8be118`: 72 commits touched `recipes/`
since 2026-08-10 (continuous activity), `test_recipe_yaml_parse_audit.py` 6/6 passing

### Story 17.2: Every local recipe carries its internal metadata, stripped on push

As a recipe maintainer,
I want each local recipe to carry `cfe-*` internal metadata that never reaches an
upstream PR,
So that the factory keeps its own provenance without leaking local-only fields into
conda-forge.

**Type:** docs • **Effort:** S • **Deps:** S-17.1 • **FR/AD:** spec-fleet-stewardship CAP-2
**Given** `extra: cfe-*` is local-only internal metadata **When** this practice is in
force **Then** every local recipe carries it and SKILL.md step 8b strips it before push
**And** a duplicate-key guard (`cfe-conda-name`) keeps the block parseable
**Status:** done — re-verified 2026-09-11 (meta-test half): parse audit incl. the
duplicate-key guard 6/6 passing. **Residue recorded in the Spec, not resolved here:** the
strip-on-push half was not independently re-checked against a real published feedstock
file that pass — it rests on the documented step-8b convention and prior worked examples

### Story 17.3: The recurring campaigns have a home and a record

As a recipe maintainer,
I want refresh (Track A/B), platform expansion and red-PR remediation to run as named,
repeatable campaigns,
So that bulk feedstock work is a workflow with recorded evidence rather than ad-hoc
sweeps.

**Type:** docs • **Effort:** M • **Deps:** S-17.1 • **FR/AD:** spec-fleet-stewardship CAP-3
**Surface:** adopted companions `docs/specs/feedstock-refresh.md`,
`feedstock-platform-expansion.md`, `feedstock-failure-remediation.md` (legacy Tier-1, in
force)
**Given** bulk feedstock work could be ad-hoc **When** this practice is in force **Then**
each campaign has a named workflow spec and lands its evidence in that spec's own Worked
Examples / Current State
**And** dormancy between waves is a currency fact the specs self-document, not a defect
**Status:** done — re-verified 2026-09-11 (historical; dormant today, matching the Spec's
own 2026-09-09 realization-gate note): all three companions' last-touch commits still
match their documented dates (`1aeaf12cee` 2026-07-02, `1bdd5a2f02` 2026-06-28); the
criterion held when waves ran (Track A Waves B–F)

## Epic 18: The recipe CI picks changed recipes from the remote-tracking ref (spec-pyforge-mason CAP-28)

Minted 2026-09-27 (night) from the station Dream's entry of the same name, closing
`DW-mason-recipe-ci-short-base-ref-2026-09-27` (found by doctor Story 32.1). Hardening: the pull_request branch is
dormant today (no recipe workflow runs on `pull_request`). **HARD boundaries:** the manual
`workflow_dispatch` `recipes` input path is untouched; no recipe and no CFE surface changes; the regression test is
`pyforge-core:CAP-10`'s workflow scan (marshal Story 63.1), not a second one.

### Story 18.1: The recipe CI picks changed recipes from the remote-tracking ref

As a recipe maintainer whose pull request the recipe CI builds,
I want the four recipe workflows to choose recipes from a diff against `refs/remotes/origin/${{ github.base_ref }}`,
So that, when a pull_request trigger returns, a pushed tag named `origin/main` can never empty the changed-recipe set.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-28
**Surface:** `.github/workflows/test-all.yml`, `.github/workflows/test-linux.yml`, `.github/workflows/test-macos.yml`,
`.github/workflows/test-windows.yml` (the pull_request changed-recipe `git diff`).
**Given** a pull request that touches `recipes/<name>/`
**When** a recipe workflow picks what to build
**Then** it diffs `refs/remotes/origin/${{ github.base_ref }}...HEAD`, never the short `origin/<base>`
**And** marshal Story 63.1's workflow test passes over all four, and the manual `recipes` input path is unchanged
**Status:** done

## Epic 19: Mason has its own skills, and conda-forge-expert is one of them (spec-pyforge-mason CAP-29)

Minted 2026-09-28 from the station Dream's 2026-09-27 entry of the same name and the operator's four answers of 2026-09-28
(A-only until the cutover flip; all four skills; the station skill SKF-compiled; the five-tier cell requires both).
**HARD boundaries:** `conda-forge-expert` is never replaced, forked or demoted, and no Mason skill restates a CFE gotcha or
recipe workflow — Epic 11's rule holds, since nothing here supersedes CFE; no implementation commit writes the CFE surface
(AD-15) — the only CFE edit is Story 19.5's `retro(cfe):` commit; `.claude/skills/pyforge-mason/` exists under `AGENTS.md`
§ Policy's dated `A-only` exception until `pyforge.cutover_root` flips to `foundry`; `docs/foundry/frames/**` is B's and is
not edited (the Mason Frame's "Do not SKF-compile" line is an operator-owned B-side follow-up). The five-tier rule
(`spec-pyforge-steward:CAP-160`, Story 72.2) and the Guild environment's `pyforge mason` (`spec-pyforge-steward:CAP-161`, Story 72.1) are
steward's. The Deps are serial: each story lands on the last, since they share the mason skill meta-test and
`docs/reference/skills-catalog.md`.

### Story 19.1: Mason's station skill is SKF-compiled, exported and consulted by the persona

As an agent doing mason work,
I want a `pyforge-mason` station skill compiled from Mason's own package, like the other seven stations' skills,
So that the `mason` grammar is documented where every station's is, and recipe questions still go to `conda-forge-expert`.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-29 (FR-51); canopy:AD-17
**Surface:** `.claude/skills/pyforge-mason/**` (new: `skill-brief.yaml`, `0.1.0/pyforge-mason/{SKILL.md,metadata.json,
provenance-map.json,context-snippet.md}`, `active` → `0.1.0`); `AGENTS.md` (the SKF block only, written by
`skf-export-skill`); `.claude/skills/.export-manifest.json` and `.claude/skills/export-skill-result-*.json` (the
export's own records); `.claude/skills/bmad-agent-mason/{SKILL.md,customize.toml,transcripts/mason-doctor-e2e.json}`;
`src/shared/packages/pyforge-mason/tests/meta/test_skf_mason_skill.py` (new, the shape of steward's
`test_skf_steward_skill.py`); `src/shared/packages/pyforge-mason/tests/meta/test_persona_consults_cfe.py`;
`docs/reference/agent-instruction-notes.md` (§ *SKF skills block*); `docs/reference/skills-catalog.md` (regenerated).
**Given** `AGENTS.md` § Policy carries the dated `A-only` exception for `.claude/skills/pyforge-mason/`
**When** `skf-brief-skill`, `skf-create-skill` (Quick tier, scope `specific-modules` over `src/pyforge/mason/cli.py`,
`src/pyforge/mason/__init__.py` and `README.md`, like steward's brief) and `skf-export-skill` run for `pyforge-mason`
**Then** `.claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md` documents `pyforge mason recipe|package|environment|doctor`
and `POST /stations/mason/mcp`, and sends every recipe question to `.claude/skills/conda-forge-expert/SKILL.md`; its
provenance resolves under `src/shared/packages/pyforge-mason/`; the SKF validators report no high finding; `AGENTS.md`'s
SKF block reads `8 skills`
**And** the persona consults `pyforge-mason` for the grammar and CFE for recipe work; the mason meta-tests still assert CFE
is hand-authored and not version-nested, and no longer assert `.claude/skills/pyforge-mason` is absent; the notes line that
says Mason has no SKF skill is replaced; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

### Story 19.2: The package craft skill teaches mason package build and ship

As a maintainer shipping a library,
I want a Mason skill that walks `mason package build` and `mason package ship` end to end,
So that one pass to PyPI, a conda channel and conda-forge is a skill I follow, not a spec I reread.

**Type:** feature • **Effort:** S • **Deps:** S-19.1 • **FR/AD:** spec-pyforge-mason CAP-29 (FR-51); canopy:AD-17 (an
operating-procedure skill, hand-authored)
**Surface:** `.claude/skills/mason-package/**` (new, authored with bmad-builder's `bmad-workflow-builder`, which mason
wields per the adoption register); `src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py` (new);
`docs/reference/skills-catalog.md` (regenerated); `docs/reference/agent-instruction-notes.md` § *Skill Reference* (one row).
**Given** Mason's native `package` verbs (CAP-3)
**When** an agent loads `mason-package`
**Then** it walks `pyforge mason package build` and `pyforge mason package ship --to …` over the four targets (`pypi-test`,
`pypi`, `channel:<name>`, `conda-forge`): dry-run by default and `--yes` to confirm, the TestPyPI rehearsal that gates the
irreversible PyPI publish (FR-50), credentials checked before anything is built, and the receipt; the `conda-forge` target
links CFE, which owns the recipe and the submission
**And** `test_mason_skills.py` asserts the skill exists, names the verbs it teaches, links `.claude/skills/conda-forge-expert/`,
and carries no CFE gotcha heading (`### G<n>.`), with a planted heading proving the check is not vacuous;
`pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

### Story 19.3: The environment craft skill teaches mason environment lock and check

As a maintainer binding a project's conda and pip dependencies,
I want a Mason skill that walks `mason environment lock` and `mason environment check`,
So that one lockfile, and a CI check that says when it went stale, are a skill I follow.

**Type:** feature • **Effort:** S • **Deps:** S-19.2 • **FR/AD:** spec-pyforge-mason CAP-29 (FR-51); canopy:AD-17 (an
operating-procedure skill, hand-authored)
**Surface:** `.claude/skills/mason-environment/**` (new, authored with `bmad-workflow-builder`);
`src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py` (extended); `docs/reference/skills-catalog.md`
(regenerated); `docs/reference/agent-instruction-notes.md` § *Skill Reference* (one row).
**Given** Mason's native `environment` verbs (CAP-4)
**When** an agent loads `mason-environment`
**Then** it walks `pyforge mason environment lock` (discovered manifests listed before solving, explicit paths override
discovery, `--platform` repeatable, the engine's name and version in the output) and `pyforge mason environment check`
(non-zero on a stale lockfile, machine-readable for CI), with the solve left entirely to the engine
**And** `test_mason_skills.py` covers the skill the way it covers `mason-package`; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

### Story 19.4: The two feedstock campaigns become Mason skills

As a recipe maintainer running a feedstock campaign,
I want platform expansion and red-PR remediation to run from Mason skills,
So that each campaign is a skill an agent loads, with CFE still owning every recipe step it drives.

**Type:** docs • **Effort:** M • **Deps:** S-19.3 • **FR/AD:** spec-pyforge-mason CAP-29 (FR-51); CAP-20 (the recurring
campaigns); canopy:AD-17
**Surface:** `.claude/skills/mason-feedstock-platform-expansion/**` and `.claude/skills/mason-feedstock-failure-remediation/**`
(new: `SKILL.md` carrying the how-to's parameterized body, `references/worked-examples.md` carrying its Worked Examples);
`docs/how-to/feedstock-platform-expansion.md` and `docs/how-to/feedstock-failure-remediation.md` (each becomes a short
pointer to its skill, frontmatter kept); `docs/specs/feedstock-platform-expansion.md` and
`docs/specs/feedstock-failure-remediation.md` (the stubs point at the skill); `CLAUDE.md` (the two legacy-index rows'
descriptions); `src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py` (extended);
`docs/reference/skills-catalog.md` (regenerated); `docs/reference/agent-instruction-notes.md` § *Skill Reference* (two rows).
**Given** the two how-tos are the orchestration layer over CFE's procedure — in their own words CFE "owns the procedural
detail" and is authoritative on any conflict
**When** this story lands, with `conda-forge-expert` invoked first (Rule 1)
**Then** each campaign runs from its Mason skill — parameters, waves, open questions, acceptance and the Worked Examples new
cases append to — moved verbatim, not rewritten; the timeless workflow stays in
`.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md` and CFE's diagnostic chain, linked, never copied
**And** the how-to and the `docs/specs/` stub each resolve to the skill; `CLAUDE.md`'s legacy index still names both stub
filenames (`bmad-drift-check`); `test_mason_skills.py` covers both skills; `docs/specs/feedstock-refresh.md` does not
move; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

### Story 19.5: The closing Rule-2 retro teaches conda-forge-expert it is one of Mason's skills

As the maintainer of `conda-forge-expert`,
I want CFE to know it is one of Mason's skills and where Mason's other skills live,
So that a recipe task that starts in CFE finds Mason's grammar and campaigns, and this conda-forge effort closes as every one does.

**Type:** retro • **Effort:** S • **Deps:** S-19.4 • **FR/AD:** spec-pyforge-mason CAP-29 (FR-51); CAP-26 (the
self-improvement loop); FR-47; AD-15
**Surface:** `.claude/skills/conda-forge-expert/SKILL.md` (a pointer: Mason's station skill routes recipe work here, and the
feedstock campaigns run as Mason skills), `.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md` (names
`mason-feedstock-platform-expansion` as its parameterized runner), `.claude/skills/conda-forge-expert/CHANGELOG.md` (a dated
entry), `.claude/skills/conda-forge-expert/MANIFEST.yaml` and `config/skill-config.yaml` (the version), and
`config/failure-catalog.yaml` only if the generator regenerates it.
**Given** Epic 19 is a conda-forge effort (CLAUDE.md Rule 2)
**When** the retro runs
**Then** CFE's `SKILL.md` and the guide link Mason's skills, and no gotcha or procedure moves out of CFE; the CHANGELOG
carries a dated minor-version entry naming Epic 19 (a "guidance held" entry if nothing else is found)
**And** the commit subject is `retro(cfe): …` and touches only the CFE surface; mason's sanctioned-retro meta-test and the
CFE suite stay green; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

## Epic 20: No station or environment caps pixi (spec-pyforge-mason CAP-30)

Minted 2026-09-28 from the station Dream's entry of the same name and the operator's ruling of that date: *"we should
loosen pyforge-mason to be >=0.80.0 with no cap -- we don't need to cap pixi in any station / environment"*. Mason's
`pixi >=0.80.0,<0.81` run-dependency was the only pixi ceiling in the repo. **HARD boundaries:** the root `pixi.toml` does
not change (its three pixi pins are already floors) and `environment.yaml` is not regenerated; conda-lock's own upstream
`virtualenv <21` cap is out of scope; steward Story 72.1 is amended separately and its planning files are not touched
here; no CFE surface changes.

### Story 20.1: Mason's pixi run-dependency is a floor, and a guard reds any pixi ceiling

As a maintainer composing an environment that carries `pyforge-mason`,
I want Mason's pixi run-dependency to be a floor, and a check that fails on any capped pixi spec,
So that no station or environment holds pixi below what the rest of the workspace resolves.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-30 (FR-52); AD-12
**Surface:** `src/shared/packages/pyforge-mason/pixi.toml` (the `pixi` run-dependency and its comment),
`src/shared/packages/pyforge-mason/src/pyforge/mason/engines/__init__.py` (`PIXI_VERSION_RANGE`),
`src/shared/packages/pyforge-mason/tests/meta/test_engine_version_range_sync.py`, `scripts/pixi_version_registry.py`
(Mason's run-dep registered as a floor site), `scripts/pixi_version_check.py` (the upper-bound finding),
`tests/scripts/test_pixi_version_check.py` (new), `pixi.lock` (the path dependency's run-deps;
`spec-pixi-candidate-currency` co-governs it).
**Given** Mason's run-dependency reads `pixi >=0.80.0,<0.81`
**When** the story lands
**Then** it reads `pixi >=0.80.0`, `PIXI_VERSION_RANGE` is the same floor, and the sync meta-test holds them equal
**And** `pixi-version-check` exits 0 on the tree and 1 when a capped pixi spec is planted in a root feature, a package
`pixi.toml` or a package `pyproject.toml`
**And** `pixi.lock` resolves pixi 0.81.x in every environment that carries `pyforge-mason`;
`pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

## Epic 21: Mason packages the intake toolchain (spec-pyforge-mason CAP-31)

Minted 2026-09-28 from the station Dream's entry *Mason packages the intake toolchain* and the operator's ruling of that
date at the triage of three intakes: package all five tools. Packaging is not adopting. Warden adopts `git-pkgs`, `forge`
and `opengrep`; Atlas adopts `git-pkgs`; Herald adopts `pptxgenjs-plus-jsx`; `gitgres` stays a design reference that
nothing in the platform loads. Other stations mint rows blocked on mason 21.1 (atlas) and 21.4 (warden) and reference
21.5 (herald). The five stories are independent. **HARD boundaries:**
- Each recipe goes through `conda-forge-expert` (Rule 1).
- A green local build on linux-64 ends each story. No staged-recipes, feedstock or upstream PR is opened without an
  explicit ask.
- Each story closes with its own `retro(cfe):` commit carrying a CFE `CHANGELOG.md` semver entry (Rule 2). No other
  commit touches the CFE surface.
- No story touches `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`: packaging is not adopting.
- `gitgres` never builds against PostgreSQL 18 (fnd:CAP-12).
- Every story is `flag-exempt: recipe-build` (`spec-feature-flag-governance` CAP-1, Q2).

### Story 21.1: git-pkgs builds green from source as a local recipe

As the Warden and Atlas stations, which will adopt `git-pkgs`,
I want a local conda recipe that builds the `git-pkgs` CLI from source,
So that adopting it is a channel install, not a download.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-31 (FR-53); AD-1; AD-15; CFE Rule 1 + Rule 2
**Surface:** `recipes/git-pkgs/**` (new: `recipe.yaml`, `build.sh`, `build.bat`); the CFE retro surface
(`.claude/skills/conda-forge-expert/{CHANGELOG.md,SKILL.md,MANIFEST.yaml,config/skill-config.yaml}`, plus
`config/failure-catalog.yaml` if a new gotcha regenerates it), committed alone as `retro(cfe): …`.
**Given** `git-pkgs/git-pkgs` v0.20.0 (2026-09-04, MIT, Go; `go.mod` needs Go 1.26.7; upstream builds with
`CGO_ENABLED=0` on pure-Go SQLite)
**When** the recipe builds the tag archive with `compiler("go-nocgo")`, `CGO_ENABLED=0` and `GOTOOLCHAIN=local`, injects
`-X github.com/git-pkgs/git-pkgs/cmd.version=${PKG_VERSION}`, and bundles the dependency licenses with `go-licenses`
**Then** `pixi run -e local-recipes recipe-build recipes/git-pkgs` exits 0 on linux-64, and its test sees
`git-pkgs --version` report 0.20.0
**And** the recipe passes `validate_recipe`, `optimize_recipe` and the CI-parity lint; its CFE block records the real
build; the story's `retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry;
`pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

### Story 21.2: forge builds green from source as a local recipe

As the Warden station, which will adopt `forge`,
I want a local conda recipe that builds the `forge` CLI from source,
So that one binary answers for GitHub, GitLab, Gitea/Forgejo and Bitbucket from a channel install.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-31 (FR-53); AD-1; AD-15; CFE Rule 1 + Rule 2
**Surface:** `recipes/forge/**` (new: `recipe.yaml`, `build.sh`, `build.bat`); the CFE retro surface, committed alone as
`retro(cfe): …`.
**Given** `git-pkgs/forge` v0.10.0 (2026-09-02, MIT, Go; `go 1.26.0` with `toolchain go1.26.7`; the CLI's `main` is
`./cmd/forge`, and `internal/cli.Version` defaults to `dev`)
**When** the recipe builds `./cmd/forge` from the tag archive with `compiler("go-nocgo")`, `CGO_ENABLED=0` and
`GOTOOLCHAIN=local`, and injects `-X github.com/git-pkgs/forge/internal/cli.Version=${PKG_VERSION}`
**Then** `pixi run -e local-recipes recipe-build recipes/forge` exits 0 on linux-64, and its test sees `forge version`
print `forge 0.10.0`, not `forge dev`
**And** the name `forge` is re-checked against live conda-forge `channeldata.json` before the build (CFE G74, G118); the
recipe passes `validate_recipe`, `optimize_recipe` and the CI-parity lint; the story's `retro(cfe):` commit lands a CFE
`CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

### Story 21.3: gitgres builds green against PostgreSQL 17 from a pinned commit

As the maintainer keeping `gitgres` as a design reference,
I want a local conda recipe that builds its PostgreSQL extension and libgit2 backend against PostgreSQL 17,
So that the design can be tried in a conda environment without Docker, while nothing in the platform loads it.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-31 (FR-53); fnd:CAP-12; AD-1; AD-15; CFE Rule 1 + Rule 2
**Surface:** `recipes/gitgres/**` (new: `recipe.yaml`, `build.sh`, and a recipe-local `conda_build_config.yaml` only if
the explicit host pins do not hold 17); the CFE retro surface, committed alone as `retro(cfe): …`.
**Given** `andrew/gitgres` (MIT) has no tag or release. Its HEAD is `eaf8743f2c137d61a75432e44e13467cad7eceaa`
(2026-03-08). `ext/` is a PGXS extension (`default_version` 0.1, requires `pgcrypto`, links OpenSSL). `backend/`
builds `gitgres-backend` and `git-remote-gitgres` against libgit2 and libpq, hard-codes `CC = cc` and has no install
target. conda-forge-pinning pins `postgresql` and `libpq` at 18.
**When** the recipe pins that commit as a dev snapshot and builds against host `postgresql >=17.11,<18`,
`libpq >=17.11,<18`, `libgit2` and `openssl`. It uses `compiler("c")` and `stdlib("c")`, builds `ext` with
`PG_CONFIG=${PREFIX}/bin/pg_config` and `make -C ext install`, and builds `backend` with `CC="${CC}"`, copying both
binaries into `${PREFIX}/bin`
**Then** `pixi run -e local-recipes recipe-build recipes/gitgres` exits 0 on linux-64. Its test initdbs a throwaway
PostgreSQL 17 cluster on a Unix socket, runs `CREATE EXTENSION gitgres CASCADE` and a query against the extension, and
sees `gitgres-backend` print its usage
**And** the rendered build and test environments resolve PostgreSQL 17, never 18; Windows is skipped
(`build.skip: win`, CFE G102); the recipe passes `validate_recipe`, `optimize_recipe` and the CI-parity lint; the story's
`retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

### Story 21.4: opengrep is repackaged from its release binaries as a local-only recipe

As the Warden station, which will adopt `opengrep`,
I want a local conda recipe that installs the `opengrep` release binary for each platform,
So that the scanner is a channel install, with the reason it cannot be built from source written down.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-31 (FR-53); AD-1; AD-15; CFE G44, G101; CFE Rule 1 + Rule 2
**Surface:** `recipes/opengrep/**` (new: `recipe.yaml`, the tag's `LICENSE` shipped in-recipe, and a test fixture rule
and file); the CFE retro surface, committed alone as `retro(cfe): …`.
**Given** `opengrep/opengrep` v1.30.0 (2026-09-07). Its COPYRIGHT grants LGPL version 2.1, so the license is
`LGPL-2.1-only`. The release ships self-contained binaries (`opengrep_manylinux_x86` and `_aarch64`,
`opengrep_osx_x86` and `_arm64`, `opengrep_windows_x86.exe`) with cosign signatures and no checksum file. A source build
is not feasible on conda-forge today: it needs OCaml 5.5.0, while conda-forge's `ocaml` tops out at 5.4.0; `dune` is not
on conda-forge; there are 69 opam dependencies and a git-URL pin to a gitlab fork branch; and 40 git submodules are
missing from GitHub archives
**When** the recipe takes one source per conda subdir (`file_name: opengrep`), per-platform and not noarch, with a
streamed sha256 per asset and no compiler, and sets `build.dynamic_linking.binary_relocation: false`
**Then** `pixi run -e local-recipes recipe-build recipes/opengrep` exits 0 on linux-64. Its test sees
`opengrep --version` report 1.30.0 and a local rule find its planted match with no network access, and the packaged
binary is byte-identical to the release asset
**And** the CFE block records `cfe-source-kind: github-release-binary`,
`cfe-on-conda-forge-status: blocked-pending-prerequisites`, and the source-build blockers in `cfe-forge-blocker-list`, so
the recipe stays local; the story's `retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry;
`pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

### Story 21.5: pptxgenjs-plus-jsx builds green beside its pptxgenjs-plus sibling

As the Herald station, which will adopt `pptxgenjs-plus-jsx` for decks,
I want a local conda recipe for the JSX companion, next to a `pptxgenjs-plus` at the version it pins,
So that Herald gets the JSX authoring layer and its engine from one channel.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-31 (FR-53); AD-1; AD-15; CFE G69, G100, G103, G110; CFE Rule 1 + Rule 2
**Surface:** `recipes/pptxgenjs-plus-jsx/**` (new: `recipe.yaml`); `recipes/pptxgenjs-plus/recipe.yaml` (4.2.1 → 4.3.4);
the CFE retro surface, committed alone as `retro(cfe): …`.
**Given** `pptxgenjs-plus-jsx` 4.3.4 on npm (2026-09-24, MIT, ESM, no bin, `engines.node >=24`). It depends on
`markdown-it`, `@lofcz/mathlive` and `mathml2omml-plus`, and on `pptxgenjs-plus` at exactly 4.3.4, while
`recipes/pptxgenjs-plus` sits at 4.2.1
**When** `recipes/pptxgenjs-plus` moves to 4.3.4 (sha256 recomputed, `build.number` 0, `bin`/`engines`/`dependencies`
re-read per G110) and the JSX recipe follows the repo's canonical npm pattern for a bin-less library (the
`recipes/pptxgenjs-plus` shape: `noarch: generic`, `pnpm install --ignore-scripts`, `npm pack`, `npm install --global`,
`pnpm-licenses`, `node_modules/.bin` stripped, a Windows branch that `call`s every shim), with `nodejs >=24` as a floor
only (G103)
**Then** `pixi run -e local-recipes recipe-build recipes/pptxgenjs-plus` and
`pixi run -e local-recipes recipe-build recipes/pptxgenjs-plus-jsx` both exit 0 on linux-64, and the JSX test loads the
`.`, `./render` and `./jsx-runtime` exports under Node 24
**And** both recipes pass `validate_recipe`, `optimize_recipe` and the CI-parity lint; the story's `retro(cfe):` commit
lands a CFE `CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done


## Epic 22: Twelve recipes lose conda-recipe-manager's leaked sentinel key, and CFE's validation refuses the next one (spec-pyforge-mason CAP-32)

Minted 2026-09-28 (night) from the station Dream's entry of the same name and the operator's ruling of that night.
12 `recipes/*/recipe.yaml` files carry a YAML mapping key written as `<conda_recipe_manager.types.SentinelType object at
0x…>`, leaked by the 2026-08-16 bulk v0→v1 conversion (`20b2f459fa`) wherever a `meta.yaml` construct had no
translation. All 12 fail rattler-build's parse, and CFE's `validate_recipe` passes six of them. The two stories are
independent. Stories 22.3 and 22.4 were split from 22.1 on 2026-10-09 by two operator rulings: `ctng-compilers` waits on
rattler-build's output-graph render, `vc` on a named track feature, and 22.1 lands the other ten. **HARD boundaries:**
- Each recipe judgement goes through `conda-forge-expert` (Rule 1).
- `meta.yaml` stays beside each recipe: the feedstocks are still v0 (the local-mirror rule).
- A green render, validate and lint, and a local build where it is cheap, end Story 22.1. No feedstock, staged-recipes
  or upstream PR is opened without an explicit ask.
- Each story closes with its own `retro(cfe):` commit carrying a CFE `CHANGELOG.md` semver entry (Rule 2). Story 22.2's
  code lands in that commit, as Story 16.3's did.
- No story touches `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`.
- 22.1 is `flag-exempt: recipe-build`; 22.2 is `flag-exempt: detector-or-gate` (`spec-feature-flag-governance` CAP-1, Q2).

### Story 22.1: The twelve recipes carrying conda-recipe-manager's sentinel key are repaired

As the fleet steward who reads `recipes/` as the local mirror of each feedstock,
I want each of the twelve `recipe.yaml` files to say in v1 what its `meta.yaml` says,
So that every one renders, validates and, where cheap, builds, instead of failing rattler-build's parse on a Python
object's repr.

**Type:** fix • **Effort:** L • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-32 (FR-54); AD-1; AD-15; CFE G20, G47, G92,
G93, G95; CFE Rule 1 + Rule 2
**Surface:** `recipes/{semgrep,boost,pyautogui,pyobjc-framework-systemconfiguration,psycopg2-yugabytedb,vc,django-pygwalker,ctng-compilers,StringZilla,lerc,amundsen-databuilder,shodan}/recipe.yaml`;
the CFE retro surface (`.claude/skills/conda-forge-expert/{CHANGELOG.md,SKILL.md,MANIFEST.yaml,config/skill-config.yaml,config/failure-catalog.yaml,tests/meta/test_recipe_yaml_parse_audit.py}`),
committed alone as `retro(cfe): …`.
**Given** each sentinel stands for one of five `meta.yaml` constructs: a commented-out key (StringZilla, pyobjc-framework-systemconfiguration,
lerc); a test with only `requires:` left (semgrep, django-pygwalker, amundsen-databuilder); an `imports:` list split from
its key (psycopg2-yugabytedb); `test.requires` orphaned at the top level (pyautogui, shodan); or jinja control flow in
test commands (boost, ctng-compilers, vc)
**When** each sentinel is replaced by that construct's v1 form, and the conversion defects found beside it are fixed
(the bare `python ${{ python_min }}` host specs, pyobjc's `name.replace(...)`, boost's loops and context lists,
ctng-compilers' output-level `run_exports`, vc's `run_exports` shape)
**Then** `grep -rl 'object at 0x' recipes/ --include=recipe.yaml` finds only `recipes/ctng-compilers/recipe.yaml`
(Story 22.3) and `recipes/vc/recipe.yaml` (Story 22.4), and each of the ten files renders with
`rattler-build build --render-only` on a platform it builds and passes `validate_recipe` and the CI-parity lint
**And** shodan, django-pygwalker, amundsen-databuilder, lerc, StringZilla, psycopg2-yugabytedb and pyautogui build on
linux-64, with a test env that cannot solve recorded per G95; semgrep, pyobjc-framework-systemconfiguration and boost
are render, validate and lint only; `meta.yaml` stays; the story's `retro(cfe):` commit adds the gotcha and a corpus
meta-test that reds any `recipe.yaml` under `recipes/` (recursively) carrying a non-string key or an object repr, with
one allowlisted leak per split story, keyed by file and location; `pixi run --frozen -e pyforge-mason pyforge-mason-test`
green
**Split 2026-10-09 (two operator rulings):** 22.1 lands for ten recipes; `ctng-compilers` moves to Story 22.3 and `vc`
to Story 22.4. 22.1's corpus check allowlists each of those two leaks by file and location until its story removes the
entry.
**Status:** done

### Story 22.2: CFE's validation reds a recipe with a non-string key or a Python object repr

As a recipe author whose next v0→v1 conversion might leak the same way,
I want `validate_recipe` to refuse a `recipe.yaml` whose parsed tree holds a non-string mapping key or a Python object's
repr,
So that the leak fails at the first gate, instead of passing CFE's validation and failing rattler-build's parse.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-32 (FR-54); AD-1; AD-15; CFE Rule 1 + Rule 2
**Surface:** `.claude/skills/conda-forge-expert/scripts/validate_recipe.py` (a tree walk in `validate_recipe_yaml`),
`.claude/skills/conda-forge-expert/tests/unit/test_validate_recipe.py`, fixtures under
`.claude/skills/conda-forge-expert/tests/fixtures/recipes/`, and the CFE version carriers, all in one `retro(cfe): …`
commit.
**Given** `validate_recipe` today passes a `recipe.yaml` whose key is `<conda_recipe_manager.types.SentinelType object at
0x…>` everywhere but the top level, because PyYAML reads it as a plain string
**When** `validate_recipe_yaml` walks the parsed tree and reports an error for every non-string mapping key, and for every
key or whole scalar that matches a Python object repr (`<dotted.Name object at 0x…>`), naming its path
**Then** `validate_recipe` exits non-zero on fixtures with a sentinel key (nested, not top-level), an int key and a
whole-scalar repr value, and exits 0 on a clean fixture and on one whose `about.description` prose only mentions an
object repr
**And** `mason recipe validate` gains the check with no Mason change (it runs CFE's script by subprocess); the story's
`retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason pyforge-mason-test`
green
**Status:** done

### Story 22.3: ctng-compilers loses its sentinel key once rattler-build renders its output graph

As the fleet steward who reads `recipes/` as the local mirror of each feedstock,
I want `recipes/ctng-compilers/recipe.yaml` to say in v1 what its `meta.yaml` says, as the ten Story 22.1 landed do,
So that ctng-compilers' converter-leaked sentinel is gone and 22.1's corpus check loses its `ctng-compilers` allowlist
entry.

**Type:** fix • **Effort:** M • **Deps:** S-22.1 • **FR/AD:** spec-pyforge-mason CAP-32 (FR-54); AD-1; AD-15; CFE G93, G95,
G121; CFE Rule 1 + Rule 2
**Surface:** `recipes/ctng-compilers/recipe.yaml`; `.claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py`
(the allowlist entry goes) and the CFE version carriers, committed alone as `retro(cfe): …`.
**Blocked:** `rattler-build build --render-only` 0.76.1 (`.ci_support/linux64.yaml` plus the local pinning) exits 1 with
`Cycle detected in recipe outputs` across the gcc stack once the sentinel and the output-level `run_exports` are
repaired. rattler-build #2531 (closed 2026-07-03, fix in 0.76.1) does not cover this case. The story unblocks when a
rattler-build release renders the repaired file, or a feedstock-faithful variant set does; the operator flips it.
**Given** the 22.1 run's draft repair (the `gxx_impl` test's two nested `if:` blocks, the output-level `run_exports` moved
under `requirements`, the context the render asks for), kept in the history of `dispatch/pyforge-mason/22.1`
**When** a rattler-build release or a variant set renders the gcc output graph
**Then** `grep -rl 'object at 0x' recipes/ --include=recipe.yaml` no longer lists `recipes/ctng-compilers/recipe.yaml`, and
the file renders on linux-64 with at least one output, passes `validate_recipe` and the CI-parity lint, and its repaired
test says what `meta.yaml` says
**And** the allowlist entry for `recipes/ctng-compilers/recipe.yaml` leaves 22.1's corpus check, which then passes with no
`ctng-compilers` entry; `meta.yaml` stays; the story's `retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry;
`pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** blocked

### Story 22.4: vc loses its sentinel key once rattler-build can emit its vc14 track feature

As the fleet steward who reads `recipes/` as the local mirror of each feedstock,
I want `recipes/vc/recipe.yaml` to say in v1 what its `meta.yaml` says, as the other ten now do,
So that vc's converter-leaked sentinel is gone and 22.1's corpus check loses its `vc` allowlist entry.

**Type:** fix • **Effort:** M • **Deps:** S-22.1 • **FR/AD:** spec-pyforge-mason CAP-32 (FR-54); AD-1; AD-15; CFE G93, G94,
G121; CFE Rule 1 + Rule 2
**Surface:** `recipes/vc/` (`recipe.yaml`, plus the feedstock's `vc_repack.py`, `activate.bat`, `LICENSE.TXT` and
`conda_build_config.yaml`); `.claude/skills/conda-forge-expert/tests/meta/test_recipe_yaml_parse_audit.py` (the
allowlist entry goes) and the CFE version carriers, committed alone as `retro(cfe): …`.
**Blocked:** `meta.yaml` gives the `vc`, `vs<year>_<platform>` and `vs_<platform>` outputs `track_features: [vc14]`, one
feature they share.
rattler-build 0.76.1 rejects `build.track_features`, and `build.variant.down_prioritize_variant` writes a per-package
`<name>-p-0` instead. The story unblocks when a rattler-build release can emit a named track feature; the operator flips
it.
**Given** the 22.1 run's draft port (staging output `vc-extract`, `vc_repack.py` script calls, three `for %%D` DLL blocks),
kept in the history of `dispatch/pyforge-mason/22.1`, and the 22.1 review's findings on it
**When** a rattler-build release can emit `track_features: [vc14]`
**Then** `grep -rl 'object at 0x' recipes/ --include=recipe.yaml` no longer finds `recipes/vc/recipe.yaml`, and the file
renders on win-64 with at least one output for each of the feedstock's five variant entries (VS 2026 win-64 and
win-arm64, VS 2022 win-64 and win-arm64, VS 2019 win-64) read from `conda_build_config.yaml`, not from `context`; it passes
`validate_recipe` and the CI-parity lint; every output that runs `python` declares it; every `vsver` / `vsyear`
comparison converts with `| int`; and the `vc`, `vs<year>_<platform>` and `vs_<platform>` packages carry
`track_features: vc14`
**And** the allowlist entry for `recipes/vc/recipe.yaml` leaves 22.1's corpus check; `meta.yaml` stays; the story's
`retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** blocked

## Epic 23: CFE's generator asks instead of guessing, a mismatched copyleft licence is refused, and a negative corpus keeps each check honest (spec-pyforge-mason CAP-33)

Minted 2026-09-29 from the station Dream's entry of the same name and the operator's ruling of that day. A
capability-by-capability comparison found that Mason and CFE already do almost everything `OpenTeams-WFT-CDO/auto-recipe`
does, so auto-recipe retires, and the three things they lack come into CFE: a Decided/Ambiguous contract, a
licence-semantics check and a negative corpus. The operator owns that GitHub org, so code may be ported from
`auto-recipe@8b53eda`, with a provenance line in each file that carries ported code. The stories run in order: 23.2 uses
23.1's check, and 23.3 pins 23.1's and 22.2's refusals. **HARD boundaries:**
- Each story goes through `conda-forge-expert` (Rule 1).
- Each story's code, tests, fixtures, `CHANGELOG.md` entry and version carriers land in its own `retro(cfe):` commit
  (Rule 2; the Story 16.3 and 22.2 path).
- No story touches `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`, and none edits `recipes/**`.
- No staged-recipes, feedstock or upstream PR is opened.
- The unattended trigger layer (issue to draft PR, PR watcher, LLM fix loop) and the MCP `generate_recipe_from_pypi`
  grayskull path are out of scope.
- 23.1 and 23.3 are `flag-exempt: detector-or-gate`; 23.2 is a fix and carries no flag (`spec-feature-flag-governance`
  CAP-1, Q1/Q2).

### Story 23.1: CFE refuses a copyleft -only licence whose LICENSE grants any later version

As a recipe author declaring a GPL-family licence,
I want CFE to catch an `-only` identifier whose LICENSE text grants "any later version",
So that a valid but wrong SPDX identifier does not ship as package metadata.

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-33 (FR-55); AD-1; AD-15; CFE Rule 1 + Rule 2
**Surface:** `.claude/skills/conda-forge-expert/scripts/license-checker.py` (a pure `check_license_semantics(declared,
source_dir)` function, called from the existing `--check-source` path), `tests/unit/` for it, fixtures under
`tests/fixtures/`, and the CFE version carriers, all in one `retro(cfe): …` commit.
**Given** `license-checker.py --check-source` today checks only that the licence file exists, and both `GPL-3.0-only` and
`GPL-3.0-or-later` are valid SPDX, so no CFE check can tell a wrong one from a right one
**When** the check reads every `LICENSE*`, `LICENCE*` and `COPYING*` file in the source directory for "any later
version" and compares it with a GPL, LGPL, AGPL or GFDL declared identifier
**Then** `--check-source` exits non-zero on a `GPL-3.0-only` fixture whose LICENSE says "any later version" and names
`GPL-3.0-or-later`; exits 0 on the matching `-or-later` fixture; reports a skip, not a pass, for a GPL `-only` fixture
whose LICENSE says neither; skips an MIT fixture; and exits non-zero when `license_file` is missing from the source
directory (today it prints `[ERROR]` and exits 0)
**And** the function carries a provenance line naming `auto-recipe@8b53eda` `verify/checks.py`; removing the comparison
makes the mismatch fixture's test fail; the story's `retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry;
`pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

### Story 23.2: CFE's recipe generator asks instead of guessing

As a recipe author generating a recipe from PyPI,
I want `recipe-generator.py` to tell me which choices it could not settle, with the options and the default it took,
So that a guess becomes a question I answer, instead of a plausible wrong value in a recipe.

**Type:** fix • **Effort:** M • **Deps:** S-23.1 • **FR/AD:** spec-pyforge-mason CAP-33 (FR-55); AD-1; AD-15; CFE Rule 1 + Rule 2; CFE Operating Principle 1
**Surface:** `.claude/skills/conda-forge-expert/scripts/recipe-generator.py` (a small Decided/Ambiguous type and the six
decision points on the v1 PyPI path, including the maturin route), `tests/unit/test_recipe_generator.py`, fixture sdists
under `tests/fixtures/`, and the CFE version carriers, all in one `retro(cfe): …` commit.
**Given** the generator chooses silently at six points: `determine_build_backend` returns `setuptools` when nothing
matches; `_extract_import_name_from_sdist` returns an empty string when ambiguous and the caller falls back to the
distribution name; `_can_noarch_python` decides from classifiers when the sdist is unavailable; `_resolve_license` takes
the first matching classifier or ends at `REPLACE_LICENSE`; `license_file` defaults to `LICENSE`; and
`_resolve_python_min` uses the floor when `python_requires` does not parse
**When** each point returns a decided value or a question carrying its options and default, the licence decision also
calls 23.1's check on the cached sdist, and the run prints the questions and writes them into the recipe's bottom
`# CFE comments` block
**Then** a fixture with no `[build-system]` table, two top-level packages, no licence metadata and an unparseable
`python_requires` lists one question per point, writes them into the CFE block, and exits 0; with `--strict` it exits
non-zero and writes no recipe; a fully resolvable fixture lists no questions and writes the same recipe as before
**And** the Decided/Ambiguous type carries a provenance line naming `auto-recipe@8b53eda` `decisions/base.py`; the
default run keeps exit 0, so `mason recipe new` and `cfe.generate_recipe` need no change (AD-1); the story's
`retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason pyforge-mason-test`
green
**Status:** done

### Story 23.3: A negative corpus proves each CFE check keeps rejecting its defect

As the maintainer of CFE's checks,
I want a corpus of recipes that must stay rejected, each tied to the rule that rejects it,
So that a check which stops firing turns a test red instead of passing silently.

**Type:** feature • **Effort:** S • **Deps:** S-23.1, S-22.2 • **FR/AD:** spec-pyforge-mason CAP-33 (FR-55); AD-1; AD-15; CFE Rule 1 + Rule 2
**Surface:** fixtures under `.claude/skills/conda-forge-expert/tests/fixtures/negative/` with a `README`,
`tests/unit/test_negative_corpus.py`, a native `recipe_optimizer.py` check (next free code, `SEL-005`) only if nothing
offline rejects skip under noarch, and the CFE version carriers, all in one `retro(cfe): …` commit.
**Given** CFE has one negative fixture (`tests/fixtures/recipes/v1-broken`), and auto-recipe's `tests/negative/` holds
two grayskull outputs carrying three defects that passed conda-forge's linter: skip under `noarch: python`, a scalar
`python_version` test matrix, and `GPL-3.0-only` for an or-later LICENSE
**When** the two fixtures are ported, CFE's own known-bad shapes are added (the conda-recipe-manager sentinel key from
22.2, a compiler without `stdlib`), and each fixture's test asserts the specific rule that rejects it (for example
`TEST-002`, `STD-001`, 23.1's licence check, 22.2's repr check)
**Then** every fixture is rejected by its named rule, and a parametrized test fails for any fixture that passes every
check; if only conda-smithy's external lint rejects skip under noarch, a native `SEL-005` check is added so the corpus
runs offline
**And** the README says the fixtures must never be "fixed" and names `auto-recipe@8b53eda` `tests/negative` as the source
of the ported two; removing any one check makes its fixture's test fail; the story's `retro(cfe):` commit lands a CFE
`CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

## Epic 24: The CFE host-gate tests give the same verdict in any developer shell (spec-pyforge-mason CAP-34)

Minted 2026-09-29 from the station Dream's entry of the same name and the operator's ruling of that day. A local
`pr-preflight` failed one CFE test that CI passed, because the credential host gate derives its allowlist from every
`*_BASE_URL` var the shell exports, and a Claude Code shell exports `ANTHROPIC_BASE_URL`. The fix was already implemented
(CFE v8.91.1, PR #1669) when the operator ruled that it take the whole chain before it merges, so the epic's one story
is minted at `done` and lands with this chain. **HARD boundaries:**
- The story goes through `conda-forge-expert` (Rule 1).
- Its code, tests, `CHANGELOG.md` entry and version carriers land in one `retro(cfe):` commit (Rule 2; the Story 16.3
  and 22.2 path).
- It changes no runtime behaviour: `_http.py` and `inventory_channel.py` are untouched.
- It touches no `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `recipes/**` file.
- 24.1 is a fix and carries no flag (`spec-feature-flag-governance` CAP-1, Q1).

### Story 24.1: CFE's host-gate tests pass in any developer shell

As a maintainer running `pr-preflight` from an agent or enterprise shell,
I want the CFE host-gate tests to ignore the mirror and tool env vars my shell exports,
So that a test CI passes does not fail locally and block my push.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-34 (FR-56); AD-1; AD-15; CFE Rule 1 + Rule 2
**Surface:** `.claude/skills/conda-forge-expert/tests/conftest.py` (a shared, opt-in `clean_mirror_env` fixture), the six
host-gate test modules that opt into it, a new `tests/unit/test_clean_mirror_env.py`, SKILL.md's host-gate constraint,
and the CFE version carriers, all in one `retro(cfe): …` commit.
**Given** `_http._configured_enterprise_hosts()`, `inventory_channel._fallback_configured_enterprise_hosts()` and
`dependency-checker.py`'s `_auth_headers` derive their allowlist from every set `*_BASE_URL` var plus npm's registry
vars, and only one of the six test modules that exercise them cleared all of those vars
**When** a shared fixture removes every `*_BASE_URL` and each name in `_http._EXTRA_MIRROR_ENV_VARS` before each
host-gate test, and each of those modules opts in
**Then** the seven affected test modules pass with `ANTHROPIC_BASE_URL` set and without it, and `pr-preflight` exits 0
from a shell that exports it
**And** a regression test plants stray vars before the fixture runs and fails if they survive; with the fixture
disabled, it fails along with the originally failing test; the `retro(cfe):` commit lands a CFE `CHANGELOG.md` semver
entry (v8.91.1); `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** done

## Epic 25: The feedstock refresh campaign is Mason's: every feedstock rxm7706 can modify has a local recipe at its published version (spec-pyforge-mason CAP-35)

Minted 2026-09-29 (evening) from the station Dream's entry of the same name and the operator's ruling of that day.
`docs/specs/` retires (`spec-one-chain-per-station:CAP-11`), and its one unfinished effort, the two-track feedstock
refresh in `docs/specs/feedstock-refresh.md`, joins this chain as one story per track. The two stories are independent.
Their scope counts date from 2026-06-19, so each story re-counts live first. **HARD boundaries:**
- Every recipe judgement goes through `conda-forge-expert` (Rule 1), including G53 (re-merge co-maintainers) and G96 (a
  bump's dependency authority is the feedstock).
- A green local build (or a recorded G95 test block) ends each recipe. No feedstock or staged-recipes PR is opened
  without an explicit ask (Rule 3: submission is a separate story).
- `meta.yaml` stays beside a recipe whose feedstock is still v0 (the local-mirror rule).
- Each story closes with its own `retro(cfe):` commit carrying a CFE `CHANGELOG.md` semver entry (Rule 2).
- No story touches `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`.
- Both stories are `flag-exempt: recipe-build`.

Story 25.3 was added 2026-10-09, on the operator's ruling of that day: mint a driver story so Story 25.2 can continue.
Story 25.1 drove its refresh with scripts that were never committed. Story 25.2 stopped `blocked` after Wave A because
the repo has no batch driver. Story 25.3 adds that driver to conda-forge-expert, and Story 25.2 now depends on it.
Story 25.3 carries two dated exceptions to the boundaries above:
- It adds one task table to `pixi.toml` (the CFE three-place rule) and changes nothing else there. No dependency
  moves, so `pixi.lock` stays put and `environment.yaml` regenerates byte-identical.
- It edits no `recipes/**` file: the driver runs only on fixture trees in this story.

It is `flag-exempt: recipe-build`. Everything the driver does with recipes stays local (operator requirement,
2026-10-09): no `git push`, `gh pr create`, `gh repo fork` or `gh api` write, no `mason recipe submit` or
`mason package ship`, and no CFE `submit_pr` or `prepare_submission_branch`. It reads feedstocks only, and writes only
under `recipes/` and its own report directory.

A second operator ruling the same day: Story 25.2's first wave runs the new driver over the recipes Story 25.1's
landing damaged, to repair them. So Story 25.3 also gains a `--repair` mode, and Story 25.2 gains a Wave 0 that runs it
before any Track B wave. Wave 0 is the one place Story 25.2 touches Track A's sole-maintainer recipes.

### Story 25.1: Track A's Wave H refreshes the sole-maintainer recipes the first waves missed

As the maintainer of the sole-maintainer feedstocks,
I want every local recipe behind one of them at its feedstock's published version,
So that the local mirror is a faithful, buildable copy of what conda-forge ships.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-35 (FR-57); AD-1; AD-15; CFE Rule 1 +
Rule 2 + Rule 3 • `flag-exempt: recipe-build`
**Surface:** `recipes/<name>/` for each sole-maintainer feedstock in the live scope; the CFE retro surface, committed alone
as `retro(cfe): …`.
**Given** Track A shipped Waves B to F on 2026-06-21 for the 252 recipes then behind, and was reopened for Wave H (179
recipes the behind-only scope missed: v0-to-v1 migrations and missing mirrors), then paused
**When** the story re-counts the sole-maintainer scope live from the atlas, and regenerates each recipe in it through CFE
with diff-apply, folding in platform expansion where the recipe is compiled
**Then** every recipe in the live scope is at its feedstock's published version, and passes `validate_recipe`,
`optimize_recipe` and the CI-parity lint, with a local build on linux-64 or a recorded G95 test block
**And** the live count and the per-bucket results are recorded in the story spec; commits go per bucket through the
story's PR; the `retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason
pyforge-mason-test` green
**Status:** done

### Story 25.2: Track B refreshes the co-maintained recipes and keeps every other maintainer's work

As a co-maintainer of 232 conda-forge feedstocks,
I want each co-maintained local recipe at its feedstock's published version, with a mirror where none exists,
So that the local tree covers every feedstock I can modify without overriding another maintainer's choices.

**Type:** feature • **Effort:** L • **Deps:** S-25.3 • **FR/AD:** spec-pyforge-mason CAP-35 (FR-57); AD-1; AD-15; CFE Rule 1 +
Rule 2 + Rule 3; CFE G53 • `flag-exempt: recipe-build`
**Deps note (2026-10-09):** Story 25.2 stopped `blocked` after Wave A. It queued 96 v1-refresh recipes, and its pilot
through CFE's autotick failed on `recipes/billiard` (no `context.name`). Its waves now run through Story 25.3's driver.
This line is set on `main`'s `epics.md`. The 25.2 story spec on `dispatch/pyforge-mason/25.2` is not edited: it takes
the dependency when it next merges `main`. As for 25.3, all of 25.2's recipe work stays local. No `git push`,
`gh pr create`, `gh repo fork` or `gh api` write, no `mason recipe submit` or `mason package ship`, and no CFE
`submit_pr` or `prepare_submission_branch` reaches conda-forge, a feedstock or staged-recipes.
**Wave 0 (2026-10-09, operator ruling: repair 25.1's landing).** Before any Track B wave, the story runs Story 25.3's
`refresh-wave --repair` over the recipes Story 25.1's landing (`f1402da5d4`) damaged. Scope:
- the 56 `recipe.yaml` files in that landing that carry a hashed `files.pythonhosted.org` URL (52 introduced by 25.1;
  55 still hashed on `main` today);
- the 78 whose diff re-indented list items (76 of them now fire FMT-001);
- `recipes/wasmtime-py`, whose `meta.yaml` sits hidden as `.meta.yaml.wave_h_hold` although its feedstock is still v0.

The three sets overlap, so this is 79 recipes, all Track A's. Wave 0 is the one place this story touches a
sole-maintainer recipe; the branch spec's "do not touch a sole-maintainer recipe" line yields for Wave 0 only.

Procedure and outcome:
- Wave 0 writes its manifest from that selection rule, runs a dry-run, records the planned repairs in the story spec,
  then runs `--apply --gates`.
- Each recipe ends `repaired`, `already-clean` or `needs-review`, with the reason recorded. The repairs change neither
  version nor build number, and no rebuild is needed: the source bytes and the parsed recipe are unchanged.
- The other 46 hashed URLs elsewhere in `recipes/` are outside Wave 0.
- Wave 0 is local only, like every wave: no push, PR, fork, issue or comment outside `rxm7706/local-recipes`.

**Surface:** `recipes/<name>/` for each co-maintained feedstock in the live scope, including new mirrors, and Wave 0's
79 recipes; the CFE retro surface, committed alone as `retro(cfe): …`.
**Given** Track B was scoped on 2026-06-19 (232 co-maintained feedstocks, 190 with a local recipe and 42 without) and never
started
**When** the story re-counts the co-maintained scope live from the atlas, regenerates each existing recipe through CFE with
diff-apply, and pulls and authors a local mirror for each feedstock without one
**Then** every recipe in the live scope is at its feedstock's published version, passes `validate_recipe`,
`optimize_recipe` and the CI-parity lint, and builds on linux-64 or records a G95 test block; every recipe's
`recipe-maintainers` list is a superset of the deployed feedstock's (G53)
**And** a deliberate maintainer choice (an intentional pin, a platform exclusion) is kept and noted in the recipe's CFE
comments block rather than overridden; the live count and the per-bucket results are recorded in the story spec; the
`retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green
**Status:** backlog

### Story 25.3: CFE gains a tracked bulk recipe-refresh driver that the refresh waves run through

As the operator running the feedstock refresh waves,
I want one tracked conda-forge-expert driver that refreshes a wave of recipes from a manifest,
So that Track B can continue, and no wave depends on a script that was never committed.

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-35 (FR-57), CAP-20, CAP-23 (no new
CAP, so no FR moves); AD-1; AD-15; CFE Rule 1 + Rule 2; CFE G52, G53, G92, G95, G96, G113 • `flag-exempt: recipe-build`
**Surface:**
- The CFE surface, in one `retro(cfe): …` commit:
  - `.claude/skills/conda-forge-expert/scripts/refresh_wave.py` (new);
  - `.claude/scripts/conda-forge-expert/refresh_wave.py` (new wrapper);
  - `scripts/recipe_updater.py` (the name fallback);
  - `scripts/mcp_parity.py` (a CLI-only entry);
  - `tests/meta/test_all_scripts_runnable.py` (`SCRIPTS`);
  - new unit and meta tests;
  - `SKILL.md`, `CHANGELOG.md`, `MANIFEST.yaml`, `config/skill-config.yaml`, and `config/failure-catalog.yaml` if a
    gotcha is added.
- `pixi.toml`, one `[feature.local-recipes.tasks.refresh-wave]` table, in its own commit.
- No `recipes/**` file, and no `src/shared/packages/pyforge-mason/` file.

**Spec:** `planning-artifacts/specs/spec-25-3-cfe-gains-a-tracked-bulk-recipe-refresh-driver-that-the-refresh-waves-run-through.md`
**Given** Story 25.1 refreshed 92 recipes with uncommitted `.cursor/` scripts, and Story 25.2 is `blocked` with 96
v1-refresh recipes queued and no driver in the repo. 25.2's autotick pilot failed on a recipe with no `context.name`
(`recipe_updater.py:86-91`).
**When** CFE gains `refresh-wave`. It reads a wave manifest and refreshes each recipe to its feedstock's published
version through `recipe_editor`. It reads each feedstock through `feedstock_lookup` and merges maintainers through
`feedstock_enrich`, and writes a report. A `--repair` mode (operator ruling, 2026-10-09) undoes 25.1's three recipe
defects:
- a hashed `files.pythonhosted.org` sdist URL goes back to the canonical `pypi.org/packages/source` form, with the
  sha256 unchanged and verified;
- FMT-001 list indentation moves to `recipe_editor`'s canonical style, whitespace-only;
- a v0 feedstock's `meta.yaml` comes back from the feedstock, or else from `.meta.yaml.wave_h_hold`, and the hold file
  is removed.

**Then:**
- The run is dry-run by default, resumable and idempotent.
- It keeps a v0 feedstock's `meta.yaml` byte-identical to the feedstock, never renamed or moved.
- The refresh path never rewrites a `source.url`; only `--repair` does, as above. Neither path drops a maintainer.
- `--repair` changes nothing but those three defects: version, build number, requirements and maintainers are equal
  before and after.
- It reports a dependency difference instead of applying it.
- Every write parses, with its CFE block present exactly once.
- `recipe_updater` reads a recipe that has no `context.name`.

**And:**
- Unit tests cover these, each repair included, on a fixture recipe tree with the feedstock fetch and the hash
  mocked.
- A meta-test asserts the pixi task, the wrapper and the `SCRIPTS` entry exist.
- A dry-run leaves `recipes/` byte-identical and writes a report.
- A meta-test plus a run test prove the driver never pushes, opens a PR, forks, or writes through `gh api`.
- The `retro(cfe):` commit lands a CFE `CHANGELOG.md` MINOR entry, with all four version carriers in lockstep.
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` is green.

**Status:** done

## Epic 26: CFE's tests never ask GitHub whether a recipe maintainer exists (spec-pyforge-mason CAP-34)

Minted 2026-10-02 from the station Dream's entry of the same name, at the operator's request to chain the defects found
landing Phase 2. The same class as Epic 24: a CFE test whose verdict depends on its environment rather than the code.
**HARD boundaries:**
- The story goes through `conda-forge-expert` (Rule 1).
- Its code, tests, `CHANGELOG.md` entry and version carriers land in one `retro(cfe):` commit (Rule 2).
- It changes no runtime behaviour: CFE's validator keeps calling conda-smithy's real lint.
- It touches no `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `recipes/**` file.
- 26.1 is a fix and carries no flag (`spec-feature-flag-governance` CAP-1, Q1).

### Story 26.1: CFE's tests never ask GitHub whether a recipe maintainer exists

As a maintainer whose PR runs the CFE regression lane,
I want CFE's tests to answer conda-smithy's maintainer lookup locally,
So that GitHub declining an unauthenticated request from a CI runner never fails a test.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-34 (FR-56); AD-1; AD-15; CFE Rule 1 + Rule 2
**Surface:** `.claude/skills/conda-forge-expert/tests/conftest.py` (a fixture that stubs conda-smithy's maintainer and
team lookups for every test not marked `network`), a new regression test, and the CFE version carriers, all in one
`retro(cfe): …` commit.
**Given** `validate_recipe` runs conda-smithy's linter, whose `lint_recipe._maintainer_exists` and `_team_exists` ask
github.com, unauthenticated when no `GH_TOKEN` is set, and `cfe-regression-net` sets none
**When** the CFE test suite stubs both lookups for every test not marked `network`
**Then** `tests/integration/test_workflow_npm.py` and every other test that lints a recipe pass with no request to
github.com
**And** a regression test fails if a lookup reaches the network while the stub is in place; a `network`-marked test keeps
the real lookup; the `retro(cfe):` commit lands a CFE `CHANGELOG.md` semver entry; `pixi run --frozen -e pyforge-mason
pyforge-mason-test` green

## Epic 27: Phase 4+5 of the deferral burn-down: mason's open medium and low deferrals

Minted 2026-10-03 from the station Dream's entry of the same date, on the operator's Phase 4+5 ruling: the open medium
deferrals (Phase 4) and the open low ones (Phase 5) are fixed where they sit, as fewer, larger stories of at most about
30 rows each, split by package area, with the CFE-surface rows in their own story so its `retro(cfe):` landing stays
separate. Counted with a parser over this station's `deferred-work-ledger.md`: 20 open medium and 42 open low rows. 61
are placed below. DW-PRESENTON-PHASE0-1 is not: its exits 1, 2, 4 and 5 and the formal closure of 6(a) wait on decisions and access outside this repo (a benching decision, the customer's JFrog allowlist, a content review), and the Dream it gates is archived; no story can close it with a fix. Operator ruling 2026-10-03, after the mint: the six rows in Story 27.2 that only an independent follow-up review of an already-landed story can close (DW-FRR-7-1, DW-FRR-7-2, DW-FRR-24-1, DW-FU-5-5, DW-FRR-12-5, DW-FRR-12-6) leave that story and stay open for a separate per-station review batch, so 55 rows are now placed.
**HARD boundaries:**
- Both stories are `fix` stories: no new CAP and no flag (`spec-feature-flag-governance` CAP-1, Q1).
- A row closes only with a `resolution:` naming its story and a `verified:` line citing the line that fixed it, or,
  where Story 15.1 retired the surface or another station's landed story delivered it, the line that records that.
- Story 27.2 goes through `conda-forge-expert` (Rule 1) and lands its CFE edits in one `retro(cfe):` commit with a CFE
  `CHANGELOG.md` semver entry (Rule 2, AD-15).
- No commit touches both `src/shared/packages/pyforge-mason/` and the CFE surface (`mason-cfe-surface-check`): the
  package is 27.1's, the CFE surface 27.2's.
- No feedstock, staged-recipes or upstream PR opens without an explicit ask.

### Story 27.1: Mason's package and the repo tooling it owns close their open deferrals

As the operator burning down mason's deferred-work ledger,
I want every open medium and low row on Mason's package and the repo tooling it owns fixed where it sits,
So that each row closes on the line that fixed it and the ledger keeps only what is still open.

**Type:** fix • **Effort:** L • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-4, CAP-5, CAP-7, CAP-16 (no new CAP; a fix carries no flag, `spec-feature-flag-governance` Q1); AD-1; AD-3; AD-15
**Surface:** `src/shared/packages/pyforge-mason/` (`cli.py`, `errors.py`, `engines/condalock.py`, `tests/unit/`, `tests/meta/`), `src/shared/packages/django-mason/` (only if DW-16-3-1 is red on main), `scripts/cfe_rebuild_guard_check.py` and its test, the installer-owned `_bmad/skf/shared/scripts/` files DW-12-3-1 and DW-12-1-3 name with tests under `tests/scripts/`, and the deferred-work rows it closes. No CFE-surface path.
**Spec:** `planning-artifacts/specs/spec-27-1-mason-s-package-and-the-repo-tooling-it-owns-close-their-open-deferrals.md` (the row-by-row fixes)
**Closes (22; 11 medium, 11 low):** DW-4-4-11, DW-4-4-13, DW-4-4-6, DW-4-4-7, DW-4-4-8, DW-4-4-9, DW-4-4-12, DW-4-4-10, DW-4-4-5, DW-16-3-1, DW-12-7-3, DW-CANOPY-2026-08-24, DW-13-2-2, DW-12-1-1, DW-12-2-2, DW-12-4-3, DW-12-4-4, DW-12-4-2, DW-12-8-1, DW-7-2-3, DW-12-3-1, DW-12-1-3
**Given** the rows above, each read against the live code first
**When** each is fixed where its code lives
**Then** `environment lock` exits 1 after a failed solve, `--format json` prints a JSON error envelope, the conda-lock check engine never blames the user's lockfile for a temp-copy failure, the config-file meta-guard catches `yaml.unsafe_load`, and the CFE-rebuild guard opens the brief it certifies and walks no history when no slice has one
**And** each row closes with a `resolution:` naming this story and a `verified:` line citing the line that fixed it (or, for a row Story 15.1 superseded or steward delivered, the line that records it); no commit touches the CFE surface; `pixi run --frozen -e pyforge-mason pyforge-mason-test` green

### Story 27.2: CFE, its failure catalog and the closed rebuild campaign's records close their open deferrals

As the operator burning down mason's deferred-work ledger,
I want every open medium and low row on conda-forge-expert, its failure catalog and the closed CFE-rebuild campaign's records fixed where it sits,
So that each row closes on the line that fixed it and the ledger keeps only what is still open.

**Type:** fix • **Effort:** L • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-14, CAP-17, CAP-19, CAP-21, CAP-22, CAP-23, CAP-34 (no new CAP; a fix carries no flag, `spec-feature-flag-governance` Q1); AD-1; AD-15; CFE Rule 1 + Rule 2
**Surface:** `.claude/skills/conda-forge-expert/` (`scripts/failure_catalog_generator.py`, `config/failure-catalog.yaml`, `quickref/commands-cheatsheet.md`, tests, the version carriers) in one `retro(cfe): …` commit; `scripts/failure_catalog_check.py` and its test; `_bmad-output/projects/pyforge-marshal/.sync-baseline.json` (re-stamped); `epics.md` § Story 5.4's SM-4 record; the campaign records under `specs/spec-conda-forge-expert-rebuild/` (`campaign-state.yaml`, `slice-map.md`, its `.memlog.md`, `SPEC.md` by `bmad-spec` only) and `specs/spec-12-5-…`; and the deferred-work rows it closes. No `src/shared/packages/pyforge-mason/` path.
**Spec:** `planning-artifacts/specs/spec-27-2-cfe-its-failure-catalog-and-the-closed-rebuild-campaign-s-records-close-their-open-deferrals.md` (the row-by-row fixes)
**Closes (25; 8 medium, 17 low):** DW-7-1-1, DW-7-1-2, DW-7-1-3, DW-7-1-4, DW-7-2-1, DW-7-2-2, DW-12-2-3, DW-17-2-1, DW-5-4-1, DW-15-1-1, DW-13-2-3, DW-12-1-2, DW-12-6-1, DW-12-6-4, DW-12-6-3, DW-12-6-2, DW-12-4-1, DW-12-5-1, DW-12-5-2, DW-12-5-3, DW-12-5-4, DW-12-5-5, DW-12-7-1, DW-12-7-2, DW-12-3-2
**Given** the rows above, each read against the live tree first, and `conda-forge-expert` invoked before any CFE edit (Rule 1)
**When** each CFE row is fixed with a test and the campaign records are corrected with dated notes
**Then** the failure catalog's signatures diagnose, it carries `schema_version: 1`, its check resolves every spelling of a check code and tells drift from a broken generator by exit code, the cheatsheet names `test-ci`, and the campaign's resume header says the campaign is closed
**And** every CFE-surface edit lands in one commit whose subject starts `retro(cfe):` with a CFE `CHANGELOG.md` semver entry; each row closes with a `resolution:` naming this story and a `verified:` line citing the line that fixed it (or, for a surface Story 15.1 retired, the line that records it); `pixi run --frozen -e pyforge-mason pyforge-mason-test` green

## Epic 28: The CFE-rebuild guard reads a SHA field whatever type YAML gives it (spec-pyforge-mason CAP-16)

Minted 2026-10-09 from the station Dream's entry of the same name, on the operator's ruling of that day ("yes mint both
stories and keep going"). `scripts/cfe_rebuild_guard_check.py` is CAP-16's detector. Its own epics are done: Epic 6
(Story 6.2, clauses (a) to (c)) and Epic 12 (Story 12.4, clause (d)). Story 27.1 added clause (b') under CAP-16. A fix
story on a done epic breaks the ledger detectors, so this new epic carries the fix.
**HARD boundaries:**
- 28.1 touches only `scripts/cfe_rebuild_guard_check.py` and `tests/scripts/test_cfe_rebuild_guard_check.py`.
- The guard is repo tooling, not the CFE surface: no `retro(cfe):` commit and no CFE `CHANGELOG.md` entry.
- No `src/shared/packages/pyforge-mason/`, `campaign-state.yaml`, `pixi.toml`, `pixi.lock` or `recipes/**` file
  changes.
- 28.1 is a fix and carries no flag (`spec-feature-flag-governance` CAP-1, Q1).

### Story 28.1: The rebuild guard reads a SHA field whatever type YAML gives it

As the maintainer whose PR runs the `scripts-suite` job,
I want the CFE-rebuild guard to read a SHA the same way whether YAML loaded it as a string or a number,
So that a brief that names its retro never gets a false `brief-defect`, and the guard's own test never flakes.

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-mason CAP-16 (no new CAP; a fix carries no
flag, `spec-feature-flag-governance` Q1); AD-1; AD-15
**Surface:** `scripts/cfe_rebuild_guard_check.py` and `tests/scripts/test_cfe_rebuild_guard_check.py`. No CFE-surface
path, and no Mason package path.
**Spec:** `planning-artifacts/specs/spec-28-1-the-rebuild-guard-reads-a-sha-field-whatever-type-yaml-gives-it.md`
**Given** PyYAML's `safe_load` reads an unquoted all-digit SHA prefix (`commit: 4139357790`) as an `int`, and
`_amendment_sha_tokens` keeps only `str` values. PR #2031's `scripts-suite` job failed
`test_brief_must_name_every_retro_at_or_older_than_the_pointer` that way (Detectors run 37990293221), and it fails
whenever the older retro's 10-character prefix is all digits and loads as an int (all-digit prefixes come up in about
0.9% of runs).
**When** the guard reads every SHA from YAML through one reader, and compares every pair of SHAs with one rule.
**Then:**
- An int-loaded SHA field or list item (never a `bool`) matches exactly like a string one. A decimal int reads as its
  decimal string. An octal- or binary-shaped token (`0123456701`, `0b10110101`), which PyYAML loads as `21913025` and
  `181`, reads as written.
- A bool, float or null is never a SHA.
- `brief_mirrored_through` is read the same way in clauses (b) and (b').
- Two hex tokens of at least ten characters name the same commit when one is a prefix of the other, so clause (b)'s
  own remedy, a 10-character prefix, clears its finding.

**And:**
- Deterministic tests pin each form with fixed SHAs and no commits.
- The existing test passes unchanged for any SHA, and each new test fails against `origin/main`'s script first.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` and `pixi run --frozen -e pyforge-mason
  pyforge-mason-test` are green.

**Status:** backlog

## Validation note — 2026-09-14 (chain-currency sweep cascade)

Validated against the architecture spine as re-stamped today (its § Currency
reconciliation — 2026-09-14) and the PRD's same-day reconciliation.

- **Ledger agreement, re-measured with the real parser** (`fleet_scan.parse_sprint_status`,
  not a regex): **70/70 stories `done` across 17/17 epics.** Every `### Story` heading
  here maps 1:1 to a `sprint-status-ledger.yaml` key, no orphan either direction. The
  prior note's 11/50 figure is superseded by growth, not corrected.
- **Epic 16's realization-gate stories are confirmed landed against live evidence, not
  against their own status lines.** Story 16.1 (mason's env satisfies the CFE import
  floor) and Story 16.2 (a first estate caller of `mason recipe`) both read `done`;
  checked directly this pass, `[feature.pyforge-mason.tasks.pyforge-mason-recipe-build-smoke]`
  exists in `pixi.toml` and `.github/workflows/pyforge-station-tests.yml:228` invokes
  it in the mason job. The caller is real and runs on every mason CI run.
- **The PRD's new FR-14 as-built divergence is deliberately NOT minted as a story
  here.** `mason recipe update` writes by default while FR-14 promises diff-before-apply
  (and NFR-9 promises dry-run-by-default). Changing that is a **behaviour change to a
  shipped verb**, which under this repo's Dream-first rule enters through
  `docs/dreams/<slug>.md` → `bmad-spec` → a Story, not through a currency sweep
  hand-writing an epic entry. It is recorded in the PRD (FR-14's divergence box and
  NFR-9's partial marker) and surfaced to the operator; the story belongs to whoever
  takes the Dream.
- **Cross-station note.** The foundry-island wiring that moved mason's package this
  week (`cfe.py`/`errors.py`/`recipe.py`/`resolve.py`) is **steward Story 44.7**, on
  steward's epics. No mason story is owed for it, and none is minted — recorded so the
  package motion is not later read as an undecomposed mason change.
- No epic or story content above was restructured; this note and the frontmatter
  `updated:`/`currency_review:` bumps are the whole edit.

## Fold provenance — 2026-09-17

One-chain mason fold. Epics already sequential 1..17 with no gaps (identity remumber). Scite window: `spec-pyforge-mason` CAP-1..27. Story keys reminted for 11.1 / 11.2 only. Ledger regenerated through `rekey-2026-09-17.md`. No `blocked` row flipped.

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd→arch→epics` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this epics. `updated:` bumped to record that the
check ran.*

## Currency reconciliation — 2026-09-28

`arch→epics` edge after the spine's 2026-09-28 re-stamp (§ Currency reconciliation — 2026-09-28: FR-51 / CAP-29
lands on AD-1, AD-15 and canopy:AD-17; no AD added, amended or removed). Epic 19 (19.1–19.5) decomposes CAP-29, and each
story keeps to those decisions: no Mason skill restates recipe knowledge (19.2–19.4's gotcha-heading guard, AD-1's rule
carried from code to skills); no implementation commit writes the CFE surface, whose one edit is 19.5's `retro(cfe):`
commit (AD-15); the station skill is SKF-compiled and the four others are hand-authored operating-procedure skills
(canopy:AD-17). Epic 11's rule — no mason SKF that supersedes CFE — holds: none does. Every Story heading still maps 1:1
to a `sprint-status-ledger.yaml` key (`19-1`..`19-5` and `epic-19` added at `backlog`, `epic-19-retrospective` at
`optional`, through the Tier-3 feed and `sprint-ledger-sync`). `updated:` bumped.

## Currency reconciliation — 2026-09-28 (later)

`arch→epics` edge after the spine's second 2026-09-28 re-stamp (§ Currency reconciliation — 2026-09-28 (later): FR-52 /
CAP-30 lands on AD-12 as written; no AD added, amended or removed). Epic 20 (Story 20.1) decomposes CAP-30 and keeps to
AD-12: pixi's range stays declared in the member `pixi.toml` and mirrored by `PIXI_VERSION_RANGE` under the sync
meta-test, and only its shape changes, to a floor. Every Story heading still maps 1:1 to a `sprint-status-ledger.yaml` key
(`20-1` and `epic-20` added, `epic-20-retrospective` at `optional`, through the Tier-3 feed and `sprint-ledger-sync`).
`updated:` bumped.

## Currency reconciliation — 2026-09-28 (night)

`arch→epics` edge after the spine's third 2026-09-28 re-stamp (§ Currency reconciliation — 2026-09-28 (night): FR-53 /
CAP-31 lands on AD-1 and AD-15 as written; no AD added, amended or removed). Epic 21 (Stories 21.1–21.5) decomposes
CAP-31, one recipe per story, and keeps to those decisions. The recipes live under `recipes/`, and no story touches
Mason's code (AD-1). No implementation commit writes the CFE surface, and each story's one CFE edit is its own
`retro(cfe):` commit (AD-15, FR-47). Every Story heading still maps 1:1 to a `sprint-status-ledger.yaml` key. `21-1` to
`21-5` and `epic-21` were added at `backlog` and `epic-21-retrospective` at `optional`, through the Tier-3 feed and
`sprint-ledger-sync`. `updated:` bumped.

## Currency reconciliation — 2026-09-28 (night, later)

`arch→epics` edge after the spine's fourth 2026-09-28 re-stamp (§ Currency reconciliation — 2026-09-28 (night, later):
FR-54 / CAP-32 lands on AD-1 and AD-15 as written; no AD added, amended or removed). Epic 22 (Stories 22.1 and 22.2)
decomposes CAP-32 and keeps to those decisions. The recipes live under `recipes/` and the check in CFE's
`validate_recipe.py`, and no story touches Mason's code (AD-1). Story 22.1's CFE edit is its `retro(cfe):` commit, and
Story 22.2's code lands in its own `retro(cfe):` commit, as Story 16.3's did (AD-15, FR-47). Every Story heading still
maps 1:1 to a `sprint-status-ledger.yaml` key. `22-1`, `22-2` and `epic-22` were added at `backlog` and
`epic-22-retrospective` at `optional`, through the Tier-3 feed and `sprint-ledger-sync`. `updated:` bumped.

## Currency reconciliation — 2026-09-29

`arch→epics` edge after the spine's 2026-09-29 re-stamp (§ Currency reconciliation — 2026-09-29: FR-55 / CAP-33 lands on
AD-1 and AD-15 as written; no AD added, amended or removed). Epic 23 (Stories 23.1–23.3) decomposes CAP-33 and keeps to
those decisions. All three change CFE code only, and no story touches Mason's code (AD-1). Each story's code lands in its
own `retro(cfe):` commit, as Stories 16.3 and 22.2 set (AD-15, FR-47). The stories are numbered in the order they run,
so no story depends on a later sibling. Every Story heading still maps 1:1 to a `sprint-status-ledger.yaml` key. `23-1`
to `23-3` and `epic-23` were added at `backlog` and `epic-23-retrospective` at `optional`, through the Tier-3 feed and
`sprint-ledger-sync`. `updated:` bumped.

## Currency reconciliation — 2026-09-29 (later)

`arch→epics` edge after the spine's second 2026-09-29 re-stamp (§ Currency reconciliation — 2026-09-29 (later): FR-56 /
CAP-34 lands on AD-1 and AD-15 as written; no AD added, amended or removed). Epic 24 (Story 24.1) decomposes CAP-34 and
keeps to those decisions. The change is in CFE's tests, and no story touches Mason's code (AD-1). The story's code lands
in its own `retro(cfe):` commit (AD-15, FR-47). Every Story heading still maps 1:1 to a `sprint-status-ledger.yaml` key.
`24-1` and `epic-24` were added at `done`, and `epic-24-retrospective` at `optional`, through the Tier-3 feed and
`sprint-ledger-sync`. `updated:` bumped.

## Currency reconciliation — 2026-09-29 (evening)

`arch→epics` edge after the spine's third 2026-09-29 re-stamp (§ Currency reconciliation — 2026-09-29 (evening): FR-57 /
CAP-35 lands on AD-1 and AD-15 as written; no AD added, amended or removed). Epic 25 (Stories 25.1 and 25.2) decomposes
CAP-35, one story per track, and keeps to those decisions. The recipes live under `recipes/`, and no story touches Mason's
code (AD-1). Each story's one CFE edit is its own `retro(cfe):` commit (AD-15, FR-47). Every Story heading still maps 1:1
to a `sprint-status-ledger.yaml` key. `25-1`, `25-2` and `epic-25` were added at `backlog` and `epic-25-retrospective` at
`optional`, through the Tier-3 feed and `sprint-ledger-sync`. `updated:` bumped.

## Currency reconciliation — 2026-10-09

`arch→epics` edge after the spine's 2026-10-09 re-stamp (§ Currency reconciliation — 2026-10-09: the Story 22.1 splits
land on AD-1 and AD-15 as written; no AD added, amended or removed). By operator ruling, Story 22.1 lands for eleven
recipes, and **Story 22.3** (fix, M, Deps S-22.1, `flag-exempt: recipe-build`) takes `ctng-compilers`. It is minted
`blocked` until a rattler-build release, or a feedstock-faithful variant set, renders the repaired gcc output graph.
A second ruling the same day narrows 22.1 to ten: **Story 22.4** (fix, M, Deps S-22.1, `flag-exempt: recipe-build`)
takes `vc`, minted `blocked` until a rattler-build release can emit the named `vc14` track feature its `meta.yaml`
gives three outputs. Every Story heading still maps 1:1 to a `sprint-status-ledger.yaml` key: `22-3` and `22-4` were
added at `blocked` through the Tier-3 feed and `sprint-ledger-sync`. `updated:` bumped.

## Currency reconciliation — 2026-10-09 (later)

`arch→epics` edge after the spine's later 2026-10-09 re-stamp, which says Story 25.3 and its repair mode land on AD-1
and AD-15 as written; no AD is added, amended or removed. Two operator rulings decide what changes here:
- **Story 25.3** (feature, L, `flag-exempt: recipe-build`) adds a tracked CFE bulk refresh driver, with a `--repair`
  mode.
- **Story 25.2** depends on it (**Deps:** S-25.3), and gains a Wave 0 that repairs Story 25.1's landing before any
  Track B wave.

The 25.2 story spec on its dispatch branch is not edited. Every Story heading still maps 1:1 to a
`sprint-status-ledger.yaml` key: `25-3` was added at `backlog` through the Tier-3 feed and `sprint-ledger-sync`.
`updated:` bumped.
