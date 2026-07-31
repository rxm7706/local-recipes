---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - "_bmad-output/projects/pyforge-genesis/planning-artifacts/prd.md"
  - "_bmad-output/projects/pyforge-genesis/planning-artifacts/architecture.md"
  - "_bmad-output/projects/pyforge-genesis/planning-artifacts/product-brief-pyforge-genesis.md"
  - "_bmad-output/projects/pyforge-genesis/planning-artifacts/research/domain-research-scaffolder-landscape.md"
  - "_bmad-output/projects/pyforge-genesis/planning-artifacts/research/technical-research-installer-implementation.md"
  - "pixi.toml"
  - "src/shared/packages/pyforge-warden/{pyproject,pixi}.toml"
project_name: pyforge-marshal
epicCount: 6
storyCount: 36
status: complete
---

# pyforge-genesis (installer) — Epic Breakdown

> **Epics 7–12, executed from pyforge-marshal's feed (2026-07-30).**
>
> This decomposition was authored as epics 1–6 under `pyforge-genesis`. On 2026-07-28
> that project was redefined as **constitutive** — it records the operating model and
> ships nothing — and its `epics.md` now states "No epics, and that is the contract."
> The buildable half moved here.
>
> **The move left one thing behind: the story feed.** `pyforge-genesis`'s
> `sprint-status.yaml` still listed all 36 installer stories, and `bmad-loop` reads
> `[stories] source = "sprint-status"` — so launching that loop home would have
> dispatched `1-1-package-skeleton-as-a-pixi-workspace-member` and built a package for
> the project whose contract is that it ships nothing. Genesis's own epics.md named the
> tripwire ("if epics reappear here … check whether buildable work has drifted back")
> — the feed *was* that drift; it simply never left.
>
> **Why 7–12 and not 1–6.** These stories now share pyforge-marshal's feed, and **33 of
> the 36 ids collided with marshal's own** (`1.1`–`6.6` in both). AD-23 makes the
> canonical key `<epic>.<seq>` unique within a project — the loop, the journal, the spec
> archive, the merge subject and the dashboard all key on it — so two `1.1`s would have
> been marshal shipping a violation of its own invariant, in its own feed. Shifting by
> +6 is the smallest change that keeps every key unique, keeps `--epic N` scoping
> meaningful, and leaves `--story <E>-<S>` unambiguous.
>
> Epic numbers below read 7–12; story ids read `S-7.1` … `S-12.6`. The PRD, architecture
> and research this decomposes still live under `_bmad-output/projects/pyforge-genesis/`
> — only the epics and the execution feed moved.

## Overview

Decomposition of Genesis's PRD (62 FRs / 20 NFRs / 10 success criteria) and architecture
(15 ADs / 12 conflict-prevention patterns / 14-component build order) into **6 epics and
36 stories**.

The epic order **is** the architecture's dependency-forced build order. It is not
value-first sequencing and that is deliberate: `check` before `adopt` before `init` means
each verb is the previous one plus exactly one capability, so the riskiest machinery (the
region engine, the write guard) is exercised from the first working verb rather than at
integration time.

**Critical-path story is S-7.6 (Spike-0, Copier API fit)** — a failure there changes AD-02
or promotes a bespoke materializer, so it gates E10 entirely.

Effort scale: XS (≤4 hr), S (½–1 day), M (1–3 days), L (3–5 days). Story IDs use
`S-<epic>.<seq>`.

## Requirements Inventory

### Functional Requirements covered

All 62 FRs (FR1–FR62). No FR is deferred out of V1; the deferrals named in architecture § 7
(feature modules, `check --fix`, `eject`, model-as-separate-artifact, Windows parity beyond
`init`/`check`) are all outside the FR set.

### Non-Functional Requirements covered

All 20 NFRs (NFR-R1–R4, A1–A2, P1–P3, C1–C4, S1–S3, M1–M3, O1). NFR enforcement concentrates
in E12, but NFR-R4 (guard at the primitive) is E7 by necessity.

### Architecture Decisions covered

All 15 ADs (AD-01–AD-15) flow into specific stories. The 12 conflict-prevention patterns
(P-01–P-12) are implemented throughout E7–E11 and enforced as executable tests by S-12.4.

### FR / Story Coverage Matrix

| FR Range | Capability | Owning Story/Stories |
|---|---|---|
| FR1–FR3, FR5 | Manifest as data, five classes, deferred state | S-7.4, S-7.5 |
| FR4 | Coverage check (no unclassified artifact) | S-9.5 |
| FR6 | Never-write path set declared | S-7.4, S-7.5 |
| FR7–FR13 | `genesis init` | S-10.7 |
| FR14–FR19 | `genesis adopt` detect→plan→apply, idempotent | S-10.6, S-9.6, S-12.5 |
| FR15–FR16 | Classification incl. `present-legacy` | S-9.2, S-9.4 |
| FR17 | Machine-readable plan artifact | S-9.6 |
| FR20–FR22 | Preconditions, refusals, skips | S-10.4 |
| FR23–FR28 | `genesis check` | S-10.5, S-9.1 |
| FR29 | Two-phase update | S-11.4 |
| FR30 | Referenced-dependency verification | S-11.5 |
| FR31–FR32 | Migration ordering, applied-once, seeded opt-in | S-11.3 |
| FR33–FR34 | Regenerate managed / recompute derived / replace regions | S-11.4, S-8.3, S-11.1 |
| FR35 | Never-write enforcement on update | S-7.3, S-12.4 |
| FR36 | `--force` → `run_recopy` | S-10.1, S-11.4 |
| FR37–FR42 | State file | S-10.2 |
| FR43–FR48 | Managed regions | S-8.1, S-8.2, S-8.3, S-8.4, S-8.5 |
| FR49–FR52 | Agent adapter fan-out | S-11.1 |
| FR53–FR54 | In-package templates + `--template` override | S-7.5, S-10.1 |
| FR55–FR56 | Copier public API only; `--unsafe` gate | S-10.1 |
| FR57 | Distribution (conda + wheel/sdist) | S-12.1 |
| FR58–FR59 | `--json` / `--quiet` / `--dry-run` | S-12.5 |
| FR60 | `genesis version` (both versions) | S-11.6 |
| FR61 | Distinct documented exit codes | S-7.2, S-12.5 |
| FR62 | `genesis explain <artifact>` | S-11.6 |

### NFR / Story Coverage Matrix

| NFR | Subject | Owning Story/Stories |
|---|---|---|
| NFR-R1 | No partial application | S-10.3 |
| NFR-R2 | Git is undo (clean worktree) | S-10.4 |
| NFR-R3 | No conflict markers ever | S-8.3 |
| NFR-R4 | Guard at the write primitive | S-7.3, S-12.4 |
| NFR-A1, NFR-A2 | Air-gapped, zero egress | S-12.3 |
| NFR-P1–P3 | check < 5 s, adopt --dry-run < 10 s, init < 5 min | S-12.5 |
| NFR-C1–C4 | Python ≥3.12, copier range-pin, platforms, namespace share | S-7.1, S-12.1 |
| NFR-S1 | No untrusted execution by default | S-10.1 |
| NFR-S2 | No credential handling | S-12.3 (no network stack) |
| NFR-S3 | Templates validated against manifest | S-10.1, S-10.3 |
| NFR-M1 | Manifest is the single source of truth | S-7.4, S-11.1 |
| NFR-M2 | Oracle in Genesis's own CI | S-12.2 |
| NFR-M3 | Every finding documented with a remedy | S-9.1, S-12.6 |
| NFR-O1 | Machine-readable plans and reports | S-9.6, S-12.5 |

### Success-criteria ownership

| SC | Owning story |
|---|---|
| SC-01 (master switch) | S-11.4 + S-11.7-equivalent coverage inside S-11.3/S-11.4 |
| SC-02 (empty-plan oracle) | **S-12.2** |
| SC-03 (adopt idempotent) | S-12.5 |
| SC-04 (refuse on hand-edited region) | S-10.4 |
| SC-05 (refuse on dirty worktree) | S-10.4 |
| SC-06 (offline, zero network) | S-12.3 |
| SC-07 (breaking model change absorbed) | S-11.3 |
| SC-08 (update cannot write Tier-0/2) | S-12.4 |
| SC-09 (init < 5 min) | S-12.5 |
| SC-10 (100% manifest coverage) | S-9.5 |

## Epic List

| Epic | Title | Story Count | Effort Sum |
|---|---|---|---|
| E7 | Foundation & the Write Guard | 6 | ~7 days |
| E8 | The Managed-Region Engine | 5 | ~8 days |
| E9 | Detect & Plan | 6 | ~9 days |
| E10 | Materialize & the Core Verbs | 7 | ~12 days |
| E11 | Derive, Migrate & Update | 6 | ~10 days |
| E12 | Packaging, Oracle & Hardening | 6 | ~8 days |
| **Total** | | **36** | **~54 days ≈ 11 weeks (single-builder, focused)** |

---

## Epic 7: Foundation & the Write Guard

**Goal:** The package skeleton, the exit-code taxonomy, the single write primitive with its
never-write guard, the manifest schema and loader, the actual V1 model manifest, and the
Copier fit spike. **Nothing else can be built safely until the guard exists** — every
subsequent component assumes writes are already policed.

### Story 7.1: Package skeleton as a pixi workspace member

As the Genesis builder,
I want a buildable `pyforge-genesis` package at `src/shared/packages/pyforge-genesis/`,
So that every later story has a stable, importable home that matches the repo's existing
pyforge packaging convention.

**Type:** infra • **Effort:** S • **Deps:** none • **FR/AD:** AD-14, NFR-C1, NFR-C4

**Acceptance Criteria:**

**Given** the repo's pixi workspace root
**When** the developer creates the member package and runs the test task
**Then** `pyproject.toml` declares `name = "pyforge-genesis"`, `requires-python = ">=3.12"`,
MIT license, `[tool.hatch.build.targets.wheel] packages = ["src/pyforge"]`, and
`[project.scripts] genesis = "pyforge.genesis.cli:main"`
**And** the member `pixi.toml` has a `[package]` table with `pixi-build-python` backend and
**no `[workspace]` table** (root owns workspace config)
**And** `import pyforge.genesis` succeeds alongside `import pyforge.warden` in the same
environment (namespace coexistence, NFR-C4)
**And** the module tree from architecture § 4 exists with `__init__.py` stubs
**And** `tests/{unit,integration,oracle,meta}/` exist with one passing smoke test
**And** ruff + pyright are clean on the skeleton

> Full root-`pixi.toml` wiring (feature, environment, tasks, `environment.yaml` regeneration)
> lands in S-12.1; this story adds only what is needed to import and test locally.

### Story 7.2: Error taxonomy and exit codes

As a CI pipeline invoking Genesis,
I want distinct, documented exit codes per failure mode,
So that automation can distinguish "repo is non-conformant" from "you gave me bad arguments"
from "Genesis broke."

**Type:** foundation • **Effort:** XS • **Deps:** S-7.1 • **FR/AD:** FR61, P-10

**Acceptance Criteria:**

**Given** `pyforge.genesis.errors`
**When** any verb fails
**Then** exactly one exception type from a closed hierarchy is raised, each mapped to a
distinct exit code: `0` success · `1` conformance failure (HARD findings) · `2` usage/argument
error · `3` precondition failure (dirty worktree, not a git repo, hand-edited managed content)
· `4` `NeverWriteViolation` · `5` state invalid · `10` internal error
**And** every exception carries a `remedy` string
**And** the exit-code table is asserted by a unit test that enumerates the hierarchy, so
adding an exception without a code fails the build
**And** no module raises a bare `Exception` or `SystemExit` outside `cli.py`

### Story 7.3: The `fs` write primitive and the never-write guard

As the Genesis architecture,
I want every byte written to a target repo to pass through one guarded primitive,
So that the never-write set (Tier-0 Dreams, Tier-2 planning artifacts, Tier-3, legacy specs,
BMAD installer files) is structurally unreachable rather than merely policy.

**Type:** foundation • **Effort:** M • **Deps:** S-7.2 • **FR/AD/P:** FR6, FR35, AD-11,
NFR-R4, P-01

**Acceptance Criteria:**

**Given** an orchestrator constructed with a frozen `NeverWrite` path set
**When** any code calls `fs.write()`, `fs.replace_span()`, or `fs.remove()`
**Then** the target path is resolved to an absolute, **symlink-resolved** form *before* any
file handle is opened
**And** a path matching the never-write set raises `NeverWriteViolation` (exit 4) with the
matched rule in the message
**And** the symlink case is explicitly covered: writing through
`_bmad-output/planning-artifacts` (a symlink into `projects/<slug>/planning-artifacts`) is
**blocked**, proving unresolved matching would have missed it
**And** the `NeverWrite` set is immutable after construction (mutation attempt raises)
**And** `fs` imports nothing from the package except `errors`
**And** `fs.write()` is atomic (write-temp + rename) so an interrupted write cannot truncate
an existing file

### Story 7.4: Manifest schema, loader, and model-version ranges

As the Genesis engine,
I want the model declared as validated data addressed by stable artifact ids,
So that adding a model artifact never requires an engine code change.

**Type:** foundation • **Effort:** M • **Deps:** S-7.2 • **FR/AD/P:** FR1, FR2, FR3, FR5,
FR6, AD-05, A-02, A-05, NFR-M1, P-11

**Acceptance Criteria:**

**Given** `templates/manifest.yaml`
**When** the loader parses it
**Then** each entry validates against a schema requiring: `id` (stable, unique), `class`
(one of `referenced` / `copied-managed` / `copied-seeded` / `generated-derived` /
`hybrid-managed-region` / `unclassified-deferred`), `path` (jinja-templated on slug),
`applies_to` (`init` / `adopt` / `both`), and `rationale`
**And** hybrid entries additionally require `format` and `regions[]` each with `name` and
ordered `anchor[]`
**And** referenced entries require `pin` (a version range)
**And** entries may carry `since` / `until` model-version bounds, and the loader filters by
the bundled model version
**And** entries may carry `legacy_of: <artifact-id>`
**And** the manifest declares the `never_write[]` path set consumed by S-7.3
**And** duplicate ids, unknown classes, or a hybrid entry without regions are load-time
errors, not runtime surprises
**And** model semver parsing/comparison is covered including pre-release ordering

### Story 7.5: The V1 extraction manifest (the model, as data)

As an adopting repository,
I want the operating model declared completely and correctly,
So that what Genesis installs is exactly the model this repo proved.

**Type:** content • **Effort:** L • **Deps:** S-7.4 • **FR/AD:** FR1, FR6, FR53, PRD
§ Extraction Manifest

**Acceptance Criteria:**

**Given** the PRD's extraction manifest
**When** `templates/manifest.yaml` and `templates/files/` are authored
**Then** every artifact named in PRD § *The V1 manifest* has an entry with the class the PRD
assigns it — REFERENCED (bmad-method ≥6.10.0, bmad-loop ≥0.8.1, copier ≥9.17<10, pixi
≥0.72.2, tmux ≥3.7b, BMAD installer dirs), COPIED·MANAGED (`bmad-switch`,
`bmad-loop-worktree`, the detector, `docs/dreams/README.md`, the CI workflow, the
`.gitignore` model region), COPIED·SEEDED (starter Dream, `.bmad-config.toml`,
`_bmad/custom/config.toml`, `.bmad-loop/policy.toml`, `specs/README.md`, deck scaffolding),
GENERATED·DERIVED (the four adapter files, `PROJECTS.md` rows, the two symlinks, directory
skeletons), HYBRID (`AGENTS.md` × 3 regions, `CLAUDE.md` × 2, `.gitignore` × 1, optional
`README.md` badge)
**And** `.claude/skills/**`, `pixi.toml` task blocks, and `library-llms-full.md` are present
as `unclassified-deferred` with a rationale
**And** the never-write set covers `docs/dreams/*.md` (except the init seed),
`**/planning-artifacts/**` (except the init-seeded `specs/README.md`),
`**/implementation-artifacts/**`, `docs/specs/*.md`, `_bmad/bmm/**`, `_bmad/core/**`
**And** template bodies render the tier table, portability contract, and Dream-first workflow
faithfully to `AGENTS.md`
**And** the manifest loads clean and passes the coverage check from S-9.5
**And** initial `model_version` is `1.0.0`

### Story 7.6: Spike-0 — Copier API fit (CRITICAL GATE)

As the Genesis architect,
I want the five load-bearing Copier behaviors proven on 9.17 before E10 is built,
So that a wrong assumption changes the design now rather than after seven stories depend on it.

**Type:** spike • **Effort:** S • **Deps:** S-7.1 • **FR/AD:** AD-02, AD-04, A-04, FR55

**Acceptance Criteria:**

**Given** a throwaway template and a temp destination
**When** the spike runs against `copier` 9.17
**Then** `run_copy(..., pretend=True)` performs **zero writes** and returns a usable result
**And** `skip_if_exists` preserves a pre-existing file while creating its siblings
**And** `data=` combined with `defaults=True` fully suppresses interactive prompting
**And** the answers-file path is template-configurable to `.genesis/.copier-answers.yml`
(**if not**, AD-02's fallback triggers and the finding is recorded in the story's dev notes)
**And** `run_update` with `vcs_ref` orders correctly against PEP 440 tags
**And** the spike's findings are written into the story record; any failure raises a
`correct-course` before E10 begins
**And** the spike code is discarded — it is not shipped

---

## Epic 8: The Managed-Region Engine

**Goal:** The one genuinely bespoke algorithm in the product — marker-delimited spans inside
repo-owned files. Built early and tested hardest because AR-1 (region corruption) is the
project's top risk and K-01 (managed-region merge proves unreliable) is a stated kill
criterion.

### Story 8.1: Marker grammar and the per-format registry

As a model artifact in any file format,
I want one canonical marker grammar rendered in the right comment syntax,
So that regions are unambiguous, greppable, and self-describing.

**Type:** foundation • **Effort:** S • **Deps:** S-7.4 • **FR/AD:** FR43, FR45, AD-03

**Acceptance Criteria:**

**Given** the marker grammar
`<open> genesis:begin region=<name> model-version=<semver> sha=<8-hex> <close>` and its
matching `genesis:end`
**When** a region is rendered for a given file
**Then** the comment style is selected from the registry by the artifact's declared `format`
(**never sniffed** from content): `html` (`<!-- … -->`) for `.md`; `hash` (`# …`) for
`.gitignore`, `.toml`, `.yml`, `.yaml`, shell
**And** `slashstar` is registered but unused in V1 and raises `NotImplementedError` if selected
**And** `sha` covers the **region body only**, so the marker line is not self-referential
**And** a round-trip test proves render → parse → render is byte-identical for every
registered format
**And** an artifact declaring a format not in the registry is a manifest load error (S-7.4)

### Story 8.2: Region parser — span discovery, nesting rejection, fence awareness

As the detect stage,
I want to locate every managed region in a file precisely and refuse malformed ones,
So that substitution operates on a span that is provably correct.

**Type:** foundation • **Effort:** M • **Deps:** S-8.1 • **FR/AD/P:** FR48, AD-03, P-06

**Acceptance Criteria:**

**Given** a file containing zero or more managed regions
**When** the parser runs
**Then** it returns, per region: name, model-version, declared sha, body byte-span, and
marker byte-spans
**And** **nested** regions (a begin inside an open region) are a hard error naming both
regions
**And** **overlapping** regions (interleaved begin/end) are a hard error
**And** an unterminated begin marker is a hard error
**And** a duplicate region name in one file is a hard error
**And** markers appearing inside a fenced code block (``` or ~~~) in a markdown file are
**ignored** — proven by a test where a fence contains a literal marker
**And** files with CRLF line endings parse identically to LF
**And** the parser performs no I/O — it takes text and returns spans (P-03 support)

### Story 8.3: Span substitution — the update primitive

As `genesis update`,
I want to replace a region's body by pure byte-span substitution,
So that a half-merged or conflict-marked file is not representable.

**Type:** foundation • **Effort:** M • **Deps:** S-8.2, S-7.3 • **FR/AD/P:** FR44, NFR-R3,
P-06, P-01

**Acceptance Criteria:**

**Given** a file with a managed region and new body content
**When** `regions.apply` substitutes it
**Then** only the bytes between the markers change; **every byte outside the span is
identical** (asserted by comparing the prefix and suffix byte-for-byte)
**And** the begin marker's `model-version` and `sha` are updated to the new values
**And** the operation writes through `fs.replace_span()` — never `Path.write_text` (P-01)
**And** no code path can emit `<<<<<<<`, `=======`, or `>>>>>>>` — asserted by a test that
substitutes content deliberately containing conflict-marker-like text and confirms it is
written literally
**And** the file's original trailing-newline state is preserved
**And** substitution on a file whose region sha does not match the caller's expectation raises
rather than silently overwriting (the guard is evaluated in detect per P-07; this is the
belt-and-braces assertion)

### Story 8.4: Anchor resolution and region insertion

As `genesis adopt`,
I want to insert a region into a pre-existing file at a declared anchor,
So that a team's `CLAUDE.md` gains the model content without Genesis guessing at structure.

**Type:** feature • **Effort:** M • **Deps:** S-8.2, S-8.3 • **FR/AD:** FR46, AD-06

**Acceptance Criteria:**

**Given** a hybrid artifact with an ordered `anchor[]` of literal line-prefix matchers
**When** the region is absent from the target file
**Then** insertion occurs immediately after the **first** matching anchor line
**And** when no anchor matches, the region is **appended at end of file** preceded by a blank
line
**And** anchors are matched only outside fenced code blocks
**And** the special anchor `<top>` inserts after any YAML frontmatter block, or at byte 0 when
there is none
**And** Genesis never infers structure beyond these literal matchers
**And** the chosen anchor (or the append fallback) is **named in the plan** so a reviewer can
veto placement before apply
**And** inserting into a file that already has the region is a no-op that reports
`already-present` (idempotence, AD-10)
**And** insertion into an absent file creates it with only the region and a minimal header

### Story 8.5: Marker deletion as a sanctioned opt-out

As a repo maintainer who rejects a model convention,
I want deleting the markers to be a permanent, greppable opt-out,
So that I can diverge deliberately without fighting the tool every update.

**Type:** feature • **Effort:** S • **Deps:** S-8.4, S-10.2 • **FR/AD:** FR47, AD-08

**Acceptance Criteria:**

**Given** a repo where a previously-present managed region's markers have been deleted
**When** `genesis check` or `genesis adopt` runs
**Then** the region is classified `opted-out`, **not** `managed-region-missing`
**And** the opt-out is recorded in state so later runs do not reinsert it
**And** `check` reports it at **INFO** severity (never HARD or DRIFT)
**And** `--reinstate <artifact>#<region>` clears the opt-out and reinserts on the next apply
**And** the distinction is proven by two tests: markers deleted (⇒ opted-out) vs. file never
had the region and state has no record (⇒ missing, will be inserted)

---

## Epic 9: Detect & Plan

**Goal:** The pure, side-effect-free half of the pipeline — walk a repo, classify every
artifact, hash what is managed, and emit a reviewable plan. `check` is nothing more than this
epic plus a renderer, so E9 completing means the product's read-side is done.

### Story 9.1: Findings model — severity, types, remedies

As a CI pipeline,
I want every conformance problem expressed as a typed finding with a documented remedy,
So that failures are actionable without reading Genesis's source.

**Type:** foundation • **Effort:** S • **Deps:** S-7.2 • **FR/AD/P:** FR25, AD-04, NFR-M3, P-10

**Acceptance Criteria:**

**Given** `detect/findings.py`
**When** any check produces a finding
**Then** it is a `Finding(severity, type, path, message, remedy)` with severity from the ladder
`HARD` / `DRIFT` / `INFO` (design borrowed from `bmad_drift_check.py`, **not imported or
vendored** — AD-04)
**And** finding types are a closed enum covering at minimum: `artifact-missing`,
`managed-file-modified`, `managed-region-modified`, `managed-region-missing`, `derived-stale`,
`model-behind`, `state-invalid`, `never-write-violation`, `referenced-dep-missing`,
`uncovered`, `legacy-present`, `opted-out`
**And** every enum member has a non-empty remedy string, asserted by a test that iterates the
enum
**And** adding a member without a remedy fails the build
**And** findings serialize to stable JSON for `--json`

### Story 9.2: Repo inventory walker and artifact classification

As `genesis adopt`,
I want each manifest artifact classified against the target repo,
So that the plan reflects what is actually there rather than what the model assumes.

**Type:** feature • **Effort:** M • **Deps:** S-7.4, S-8.2, S-9.1 • **FR/AD/P:** FR15, P-03

**Acceptance Criteria:**

**Given** a manifest and a target repo
**When** detect runs
**Then** each artifact is classified `absent`, `present-conformant`, `present-divergent`, or
`present-legacy`
**And** classification is **pure**: no writes, no network, no mutation of inputs — asserted by
running detect against a read-only filesystem mount (or an equivalent write-blocking fixture)
**And** the repo tree is walked **once**, with results cached for the run (NFR-P1/P2)
**And** `.git/`, `node_modules/`, `.pixi/`, and gitignored paths are excluded from the walk
except where an artifact explicitly targets them
**And** detect works on a repo missing `.genesis/` entirely (first-ever adopt)
**And** detect returns a structure sufficient for both plan building and finding emission —
no second pass required

### Story 9.3: Content hashing for managed files and regions

As the update path,
I want a precise signal that a tool-owned artifact was hand-edited,
So that Genesis refuses rather than silently overwriting a human's change.

**Type:** feature • **Effort:** S • **Deps:** S-9.2, S-8.2 • **FR/AD/P:** FR41, FR21, P-07

**Acceptance Criteria:**

**Given** a managed file or managed region recorded in state with a body sha
**When** detect hashes the current content
**Then** a mismatch yields `managed-file-modified` / `managed-region-modified` at HARD severity
**And** hashing normalizes line endings so a CRLF checkout does not false-positive
**And** region hashing covers the body only (consistent with S-8.1)
**And** hash checks happen **in detect, never in apply** (P-07) — asserted by a meta-test that
finds no hash comparison in `apply/`
**And** an artifact present in the repo but absent from state (adopted out-of-band) is
classified `present-divergent`, not silently accepted

### Story 9.4: Legacy convention detection

As a repo with a superseded-but-live convention,
I want it recognized, recorded, and left completely alone,
So that adopting the model never destroys work still in flight.

**Type:** feature • **Effort:** S • **Deps:** S-9.2 • **FR/AD:** FR16, AD-09

**Acceptance Criteria:**

**Given** a manifest entry carrying `legacy_of: <successor-artifact-id>`
**When** detect finds the legacy artifact present
**Then** it is classified `present-legacy` and recorded in `state.legacy[]`
**And** it is added to the effective never-write set for the run — no plan action may target it
**And** `check` emits `legacy-present` at **INFO** naming the successor, never HARD or DRIFT
**And** the canonical case is covered by test: `docs/specs/*.md` present ⇒ preserved, recorded,
successor named as Tier-2 planning-artifacts
**And** no automated Tier-1 → Tier-2 migration is attempted (explicitly out of V1)

### Story 9.5: Manifest coverage check

As the Genesis maintainer,
I want an unclassified artifact to be a build failure,
So that the model's coverage cannot silently lapse the way undocumented conventions do.

**Type:** feature • **Effort:** S • **Deps:** S-7.5, S-9.1 • **FR/AD:** FR4, SC-10

**Acceptance Criteria:**

**Given** the loaded manifest
**When** the coverage check runs
**Then** every artifact carries **exactly one** class
**And** an artifact with no class, or with a class outside the enum, produces an `uncovered`
HARD finding
**And** `unclassified-deferred` counts as covered **only** when it carries a rationale — a bare
deferral fails
**And** the check runs in Genesis's own test suite so a manifest edit that drops coverage fails
CI (this mirrors `bmad_drift_check.py`'s `uncovered` HARD finding — the design that made
coverage lapse impossible in this repo)
**And** the check reports coverage counts per class for the report renderer

### Story 9.6: Plan and Action types, repo fingerprint, and the plan builder

As a human reviewing a change before it happens,
I want the plan to be a complete, serializable, self-validating artifact,
So that "review then apply" is a real gate rather than a printed summary.

**Type:** feature • **Effort:** M • **Deps:** S-9.2, S-9.3, S-9.4 • **FR/AD/P:** FR17, AD-07,
NFR-O1, P-04, P-05

**Acceptance Criteria:**

**Given** a detect result
**When** the plan builder runs
**Then** it emits a `Plan` dataclass serializable to `.genesis/plan.json`
**And** every `Action` names: artifact id, class, current state, target state, target path,
chosen anchor (where applicable), and a rationale string (P-05)
**And** the plan carries a `repo_fingerprint` = git HEAD + dirty flag + per-artifact content
hashes for every artifact it names
**And** an empty plan (zero actions) is a first-class, valid result — the idempotence signal
(AD-10)
**And** the plan is round-trippable: serialize → load → identical
**And** the plan file is written to `.genesis/plan.json` and is covered by the model's own
`.gitignore` region; `--plan-out <path>` redirects it
**And** actions are ordered deterministically (by artifact id) so two runs produce identical
plan bytes

---

## Epic 10: Materialize & the Core Verbs

**Goal:** Add writes. The Copier seam, the apply runner, the state store, the preconditions,
and then the three verbs in dependency order — `check` (no writes), `adopt` (writes), `init`
(adopt against an empty target). **Gated on S-7.6 (Spike-0).**

### Story 10.1: Copier engine wrapper — the single seam

As the Genesis architecture,
I want exactly one module that knows Copier exists,
So that the engine can be version-bumped or replaced behind one boundary and the
public-API-only rule is enforceable.

**Type:** foundation • **Effort:** M • **Deps:** S-7.6, S-7.3 • **FR/AD/P:** FR53, FR54, FR55,
FR56, FR36, NFR-S1, NFR-S3, A-04, P-02

**Acceptance Criteria:**

**Given** `engine/copier.py`
**When** materialization is requested
**Then** the module exposes a Genesis-internal `MaterializeRequest` → result API; callers never
see Copier types
**And** it calls only `run_copy`, `run_update`, `run_recopy` with documented kwargs — no
`Worker` attribute access, no private-module imports (asserted by S-12.4's import test)
**And** `copier` is imported in **this module only** (P-02)
**And** in-package templates are the default source; `--template <path|url>` overrides (FR54)
**And** Copier's code-executing template features are reachable only with `--unsafe` (FR56,
NFR-S1)
**And** `--force` maps to `run_recopy` and requires explicit confirmation (FR36)
**And** a template that attempts to write outside its manifest-declared paths is rejected
(NFR-S3) — Copier's output is reconciled against the plan before any byte is committed
**And** all writes still route through `fs` (P-01), not Copier's own filesystem access, or the
story documents precisely how Copier's writes are fenced into a staging dir and then applied
through `fs`

### Story 10.2: State schema and the atomic store

As Genesis across runs,
I want a schema-validated, tool-owned state file written last and atomically,
So that the repo and its state can never disagree — the failure mode that cost this repo ten
hours with the `bmad-switch` marker.

**Type:** foundation • **Effort:** M • **Deps:** S-7.3 • **FR/AD/P:** FR37, FR38, FR39, FR40,
FR41, FR42, AD-02, AD-08, P-08

**Acceptance Criteria:**

**Given** `.genesis/state.yml`
**When** state is written
**Then** it contains `model_version`, `genesis_version`, `adopted_at`, `last_update`, `mode`,
`agents[]`, `managed[]` (id, path, class, body_sha, inserted_region_span), `skips[]`,
`legacy[]`, `migrations_applied[]`, `opted_out[]`
**And** it carries a prominent do-not-hand-edit header
**And** it validates against `state/schema.json` on every read; an invalid file produces
`state-invalid` (exit 5), **never a traceback** (FR39)
**And** it is git-tracked (FR42) and **not** in the model's gitignore region
**And** it is written **last**, after all file writes succeed, in one atomic replace (P-08) —
asserted by a fault-injection test that fails a mid-apply write and confirms state is unchanged
**And** Copier's answers file is treated as opaque: Genesis never reads or hand-edits it
(FR40), and answers are re-supplied from Genesis state via `data=` on every Copier call
**And** `managed[]` records enough for a future `eject` (AD-08) — asserted by a test that
reconstructs the removal set from state alone

### Story 10.3: The apply runner — transactional, guarded

As a repo owner,
I want apply to either complete or leave nothing behind,
So that an interrupted install never leaves a half-configured repo.

**Type:** feature • **Effort:** M • **Deps:** S-10.1, S-10.2, S-8.3, S-9.6 • **FR/AD/P:** FR18,
NFR-R1, NFR-S3, P-04, P-07

**Acceptance Criteria:**

**Given** a `Plan` and a matching repo
**When** apply runs
**Then** it consumes **only** the plan and never re-derives state (P-04)
**And** it refuses a plan whose `repo_fingerprint` no longer matches the repo (AD-07) with a
`stale-plan` precondition error (exit 3)
**And** every write goes through `fs` (P-01)
**And** apply performs **no** hash comparisons — it trusts detect (P-07)
**And** on any failure mid-run, all completed writes are reverted and state is untouched
(NFR-R1) — asserted by fault injection at three different action indices
**And** actions execute in the plan's deterministic order
**And** apply is a no-op on an empty plan and exits 0

### Story 10.4: Preconditions, refusals, and skips

As a repo owner,
I want Genesis to refuse loudly in the situations where it could do harm,
So that git remains a complete undo and no hand-edit is ever silently discarded.

**Type:** feature • **Effort:** S • **Deps:** S-10.3, S-9.3 • **FR/AD:** FR20, FR21, FR22,
NFR-R2, SC-04, SC-05

**Acceptance Criteria:**

**Given** a mutating verb invoked with `--apply` / `--run`
**When** preconditions are evaluated
**Then** running outside a git repository is refused (exit 3)
**And** running on a **dirty worktree** is refused (exit 3) — SC-05
**And** a hand-edited managed file or managed region causes refusal with the specific artifact
and region named, unless `--force` (exit 3) — SC-04
**And** `--skip <glob>` records the pattern in `state.skips[]` and is honored on every
subsequent run (FR22)
**And** skipped artifacts appear in the plan as `skipped` actions with the matching pattern
named, so a skip is visible rather than invisible
**And** dry-run invocations bypass the clean-worktree requirement (reading is always safe)
**And** each refusal message states the remedy (P-10)

### Story 10.5: `genesis check`

As a CI pipeline,
I want a read-only conformance verb with a non-zero exit,
So that a repo cannot silently drift from the model it installed.

**Type:** feature • **Effort:** M • **Deps:** S-9.6, S-9.1, S-10.2 • **FR/AD:** FR23, FR24,
FR25, FR26, FR27, FR28, NFR-P1

**Acceptance Criteria:**

**Given** an adopted repo
**When** `genesis check` runs
**Then** it performs detect + plan and **never writes** — including not writing state, not
writing `plan.json`, and not creating `.genesis/` (FR23), asserted against a write-blocking
fixture
**And** it exits non-zero on any HARD finding; `--strict` additionally fails on DRIFT (FR24)
**And** `--json` emits the full findings report, stable and CI-annotatable (FR26)
**And** it reports the repo's `model_version` against the bundled model version as
`model-behind` / current / ahead (FR27)
**And** it completes in **< 5 s** on a `local-recipes`-sized repo (NFR-P1), asserted by a timed
test
**And** it runs correctly on a repo that has never been adopted (reports every artifact absent
rather than erroring)
**And** the human-readable report groups findings by severity with counts, in the shape of
`bmad_drift_check.py`'s report

### Story 10.6: `genesis adopt`

As a team with a working repository,
I want the model layered on without disturbing what already runs,
So that adoption is a reviewable, revertible, and repeatable operation.

**Type:** feature • **Effort:** L • **Deps:** S-10.3, S-10.4, S-10.5, S-8.4 • **FR/AD:** FR14,
FR15, FR16, FR17, FR18, FR19, FR22, AD-10

**Acceptance Criteria:**

**Given** an existing repository
**When** `genesis adopt` runs with no flags
**Then** it is **dry-run**: a plan is written and printed, and no repo file changes (FR14)
**And** `--apply` executes the plan; `--yes` executes without interactive confirmation
(unattended/CI use)
**And** artifacts already present are preserved unless their class is `copied-managed` or
`generated-derived` (FR18)
**And** `present-legacy` artifacts are preserved and recorded, never modified (FR16)
**And** a **second** `adopt` on an unchanged repo produces an **empty plan and writes nothing**
(FR19, SC-03, AD-10)
**And** `--agents <list>` adds adapters idempotently on a repo already adopted (FR51 support)
**And** the end-to-end journey from PRD J2 is covered by an integration test: a repo with an
existing `CLAUDE.md` and a legacy convention adopts cleanly, its build-relevant files
untouched

### Story 10.7: `genesis init`

As a maintainer starting a new project,
I want a complete Dream-first repository in one command,
So that day zero already has the tiers, the contract, the wiring, and a Dream to write into.

**Type:** feature • **Effort:** M • **Deps:** S-10.6 • **FR/AD:** FR7, FR8, FR9, FR10, FR11,
FR12, FR13

**Acceptance Criteria:**

**Given** an empty target directory
**When** `genesis init <path> --slug <slug> --agents claude,cursor` runs
**Then** every manifest artifact whose `applies_to` includes `init` is materialized
**And** `docs/dreams/<slug>.md` is seeded with valid Tier-0 frontmatter (`title`, `type: dream`,
`owner`, `status: seeded`) — and it is the **only** Dream written (FR9)
**And** `_bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}`,
`.bmad-config.toml`, `planning-artifacts/specs/README.md`, and `PROJECTS.md` with the first row
are created (FR10)
**And** the `.gitignore` model region covers `_bmad-output/projects/*/implementation-artifacts/`,
the two `_bmad-output` compatibility symlinks, `_bmad/custom/.active-project`,
`.bmad-loop/{runs,cache}/`, and `_bmad-output/projects/*/.bmad-config.user.toml` (FR11)
**And** state records `mode: init` plus both versions, agents, and per-artifact hashes (FR12)
**And** init into a **non-empty** directory is refused unless `--force`, with the message
directing the user to `adopt` (FR13)
**And** `genesis check` on the fresh repo is green
**And** init runs the same `resolve → detect → plan → apply` pipeline as adopt — asserted by a
test that init produces a plan artifact identical in shape

---

## Epic 11: Derive, Migrate & Update

**Goal:** The generated class and the upgrade path — the reason the whole architecture exists.
After this epic an installed repo can take a later model version through a reviewable plan and
version-ordered migrations, with Tier-0/Tier-2 structurally unreachable.

### Story 11.1: Neutral contract and agent-adapter fan-out

As four different coding agents,
I want one contract rendered into whichever entry file I read,
So that the four adapter files cannot drift from each other or from `AGENTS.md`.

**Type:** feature • **Effort:** M • **Deps:** S-7.5, S-8.4 • **FR/AD:** FR49, FR50, FR51, FR52,
AD-13, NFR-M1

**Acceptance Criteria:**

**Given** one jinja source for the neutral contract (tier table, portability contract,
Dream-first workflow)
**When** the derive stage runs
**Then** `.cursor/rules/specs.mdc`, `GEMINI.md`, and `.github/copilot-instructions.md` are
generated as **whole files** (`generated-derived`), each wrapping the same contract in its
tool-specific framing (FR50)
**And** `AGENTS.md` and `CLAUDE.md` receive the contract as **managed regions**, never by
overwrite (FR52)
**And** the contract has exactly one source in the manifest (FR49) — asserted by a test that
mutates the source and confirms all four outputs change
**And** derived output is deterministic: two runs produce byte-identical files
**And** adapter selection is per-repo, recorded in `state.agents[]`, and extensible by adding a
manifest entry plus a wrapper template with **no engine change** (FR51, NFR-M1) — asserted by
adding a fifth dummy adapter in a test
**And** the tier table rendered into `GEMINI.md` matches the tier table rendered into
`AGENTS.md` semantically (same tiers, same paths, same git dispositions)

### Story 11.2: `PROJECTS.md` index and artifact-symlink derivation

As a multi-project repo,
I want the project index and the two BMAD artifact symlinks derived from what actually exists,
So that the index cannot go stale and the marker/symlink desync cannot recur.

**Type:** feature • **Effort:** S • **Deps:** S-11.1 • **FR/AD:** FR (generated-derived class),
AD-13

**Acceptance Criteria:**

**Given** a repo with N `_bmad-output/projects/*/.bmad-config.toml` files
**When** the derive stage runs
**Then** `PROJECTS.md`'s Projects table has exactly N rows, one per project, with slug,
status, and description read from each `.bmad-config.toml`
**And** hand-written prose elsewhere in `PROJECTS.md` is preserved — only the table region is
derived
**And** the two `_bmad-output/{planning,implementation}-artifacts` symlinks are ensured to
exist, point at the active project, and be covered by the gitignore region
**And** a symlink pointing at a **different** project than the `.active-project` marker
produces a HARD finding naming both — the desync that cost this repo ten hours becomes a
detectable, named condition
**And** derive never writes into `projects/*/planning-artifacts/**` (never-write set)

### Story 11.3: Migration registry and runner

As an installed repo,
I want breaking model changes absorbed by ordered, once-only migrations,
So that a model upgrade is a scripted operation rather than a manual chore in every repo.

**Type:** feature • **Effort:** M • **Deps:** S-10.3, S-10.2 • **FR/AD/P:** FR31, FR32, AD-12,
SC-07, P-12

**Acceptance Criteria:**

**Given** migration modules registered with `from_version` / `to_version`
**When** the runner computes the chain from `state.model_version` to the bundled model version
**Then** migrations are selected in **semver order** and composed into a single `Plan`
**And** each migration is a **pure function** `(RepoView, State) -> Plan` that performs no
writes (P-12) — asserted against a write-blocking fixture
**And** applied migrations are appended to `state.migrations_applied[]` and **never re-run**
(FR31) — asserted by running update twice
**And** a migration targeting a `copied-seeded` artifact emits an **offer** action that apply
skips unless `--include-seeded` is passed (FR32)
**And** a migration targeting a never-write path fails at plan time, not apply time
**And** **SC-07 is proven**: a simulated model v1 → v2 breaking change (a tier-table rule
change plus a renamed managed artifact) is absorbed in a fixture repo with **zero manual
edits**, and `genesis check` is green afterward
**And** a gap in the migration chain (no path from the repo's version to the bundled version)
is a clear error naming the missing step

### Story 11.4: `genesis update` — two-phase

As a maintainer taking a model upgrade,
I want a plan I can review and then apply,
So that an upgrade to my repo's governance is never a surprise.

**Type:** feature • **Effort:** M • **Deps:** S-11.3, S-11.1, S-8.3 • **FR/AD:** FR29, FR33,
FR34, FR35, FR36, SC-01

**Acceptance Criteria:**

**Given** a repo behind the bundled model version
**When** `genesis update` runs with no flags
**Then** a plan is written naming every migration and every file action, and **nothing is
changed** (FR29)
**And** `--run` applies the plan
**And** `copied-managed` files are regenerated wholesale and `generated-derived` files are
recomputed, after detect's hash guards pass (FR33)
**And** only the marked span of `hybrid-managed-region` files is replaced (FR34)
**And** `copied-seeded` artifacts are untouched unless `--include-seeded`
**And** an attempted write to the never-write set is a hard error (FR35) — see S-12.4 for the
standing proof
**And** `--force` maps to `run_recopy` with explicit confirmation (FR36)
**And** the PRD J3 journey is covered end to end: `check` reports `model-behind` → `update`
plans → `--run` applies → Dreams/PRDs/epics byte-identical before and after → `check` green
(this is **SC-01**'s mechanical half)

### Story 11.5: Referenced-dependency verification and Doctor delegation

As an adopting repo,
I want Genesis to tell me which required tools are missing or below floor,
So that the model's machinery is not installed into an environment that cannot run it.

**Type:** feature • **Effort:** S • **Deps:** S-10.5 • **FR/AD:** FR30, PRD § Boundaries

**Acceptance Criteria:**

**Given** the manifest's REFERENCED entries with their pins
**When** `check` or `update` runs
**Then** each dependency's presence and version floor is verified (bmad-method ≥6.10.0,
bmad-loop ≥0.8.1, copier ≥9.17<10, pixi ≥0.72.2, tmux ≥3.7b)
**And** a missing or below-floor dependency yields `referenced-dep-missing` at **DRIFT**
severity (not HARD — the repo is still conformant, the machine is not ready)
**And** Genesis **never installs** any referenced dependency (FR30)
**And** the probe is minimal and self-contained — it works in a repo that has **not** adopted
`pyforge-doctor`
**And** when `doctor` is available on PATH, Genesis delegates and reports Doctor's findings
rather than duplicating them, marking them as such in the report
**And** the probe makes no network calls

### Story 11.6: `genesis explain` and `genesis version`

As an agent reading this repo,
I want the model to describe its own rules,
So that the conventions are queryable rather than only narrated in prose.

**Type:** feature • **Effort:** S • **Deps:** S-7.4, S-10.2 • **FR/AD:** FR60, FR62, D1

**Acceptance Criteria:**

**Given** an artifact id or path
**When** `genesis explain <artifact>` runs
**Then** it prints the artifact's class, its rationale from the manifest, its update behavior,
and (for hybrid) its regions and anchors
**And** it accepts a path as well as an id, resolving the path to its manifest entry
**And** an unknown artifact yields a helpful message listing near matches
**And** `--json` emits the same data structurally
**And** `genesis version` prints **both** the CLI version and the bundled model version, plus
the adopted repo's model version when run inside one (FR60)
**And** both verbs are read-only

---

## Epic 12: Packaging, Oracle & Hardening

**Goal:** Ship it, and prove the claims that distinguish Genesis from every comparable tool —
the empty-plan oracle, zero egress, the write guard, and the pattern invariants as executable
tests.

### Story 12.1: Full pixi wiring, distribution, and repo-gate compliance

As the repo,
I want Genesis wired into the workspace exactly like `pyforge-warden`,
So that it builds as a conda package and its landing does not red the always-on PR gates.

**Type:** infra • **Effort:** M • **Deps:** S-7.1, S-11.6 • **FR/AD:** FR57, AD-14, NFR-C1,
NFR-C2, NFR-C3, D3

**Acceptance Criteria:**

**Given** the root `pixi.toml`
**When** the member is wired in
**Then** `[feature.pyforge-genesis.dependencies]` declares the path dependency plus
`hatchling`, `python-build`, and `pytest`, and the member's `[package.run-dependencies]`
declare `python >=3.12` and `copier >=9.17,<10`
**And** `[environments] pyforge-genesis = { features = ["pyforge-genesis"],
no-default-feature = true }` — the lean env bmad-loop worktrees materialize
**And** `pyforge-genesis-test` and `genesis` tasks exist
**And** a version-range sync test asserts the `copier` pin in `pixi.toml` matches the constant
in `engine/copier.py` (NFR-C2, warden's established pattern)
**And** the package builds as a conda package **and** as wheel + sdist (FR57)
**And** **`environment.yaml` is regenerated and committed**
(`pixi project export conda-environment -e build > environment.yaml`) — the ungated repo gate
**And** the PR carries the **`maintenance` label** (change outside `recipes/`)
**And** `docs/reference/library-llms-full.md` is updated: Genesis added, and the scaffolding
decision table's "Scaffold a project → cookiecutter (+ cruft)" line reconciled with Copier's
adoption; `pixi run -e local-recipes llms-full-check` passes
**And** Linux and macOS are first-class; Windows is best-effort for `init`/`check` (NFR-C3)

### Story 12.2: The `local-recipes` empty-plan oracle (CRITICAL)

As the Genesis maintainer,
I want the source repo to be the regression test for the model manifest,
So that any divergence between the model and the repo it was extracted from fails the build
the day it appears.

**Type:** test • **Effort:** M • **Deps:** S-10.6, S-11.1, S-11.2 • **FR/AD:** SC-02, NFR-M2,
AD-10

**Acceptance Criteria:**

**Given** the `local-recipes` repository at the shipped model version
**When** `genesis adopt --dry-run` runs against it
**Then** the resulting plan has **zero actions** (SC-02)
**And** the test runs in Genesis's own CI so drift in the source repo fails Genesis's build
(NFR-M2)
**And** a non-empty plan fails with a readable diff of exactly which artifacts diverged and how
**And** the test is resilient to the repo's mutable content (recipe counts, project counts,
dashboard state) — it asserts on the model manifest's artifacts only, never on repo volume
**And** `unclassified-deferred` artifacts are excluded from the assertion by design and the
exclusion is explicit in the test
**And** the story documents any special-casing required; **if special-casing is needed to reach
empty, kill criterion K-02 is triggered and escalated** rather than worked around

### Story 12.3: Offline operation and the egress counter

As an air-gapped adopter,
I want proof that Genesis makes no network calls,
So that the model can be installed behind a firewall with confidence rather than hope.

**Type:** test • **Effort:** S • **Deps:** S-10.7, S-10.5 • **FR/AD:** NFR-A1, NFR-A2, NFR-S2,
AD-15, P-09, SC-06

**Acceptance Criteria:**

**Given** the package with in-package templates
**When** the meta-test inspects imports
**Then** no module imports `requests`, `httpx`, `urllib.request`, or `socket` (AD-15, P-09)
**And** an egress-counter test asserts **zero** network calls across `init`,
`adopt --dry-run`, `adopt --apply`, `check`, and `update --run` (SC-06, NFR-A1)
**And** the suite additionally runs the same set under `unshare -n` (Linux) and passes
**And** every runtime dependency resolves from conda-forge (NFR-A2), asserted by the lean env
building with no PyPI access
**And** Genesis reads and writes no credentials (NFR-S2) — trivially true given no network
stack, asserted by the import test
**And** the only network path is Copier's git fetch, reachable **only** via `--template <url>`,
asserted by a test that confirms the default path never constructs a remote source

### Story 12.4: Pattern meta-tests and the never-write proof

As the Genesis architecture,
I want the twelve conflict-prevention patterns enforced by executable tests,
So that a future story cannot quietly violate an invariant the whole design rests on.

**Type:** test • **Effort:** M • **Deps:** S-10.3, S-11.4 • **FR/AD/P:** P-01–P-12, FR35, SC-08,
NFR-R4

**Acceptance Criteria:**

**Given** the package source
**When** the meta-test suite runs
**Then** **P-01** is enforced by an AST scan finding no `open(..., 'w')`, `Path.write_text`,
`Path.write_bytes`, `shutil.copy*`, `os.remove`, or `os.rename` against a target path outside
`fs.py`
**And** **P-02** is enforced by an import scan finding `copier` imported only in
`engine/copier.py`, and no import of Copier private/deprecated modules
**And** **P-03** is enforced by running detect against a write-blocking fixture
**And** **P-07** is enforced by an AST scan finding no hash comparison inside `apply/`
**And** **P-09** is covered by S-12.3's import test
**And** the layer rule (no upward imports; `detect` never imports `apply`/`engine`) is enforced
**And** **SC-08 is proven**: `genesis update --run` against a fixture repo cannot write to
`docs/dreams/**` or `**/planning-artifacts/**` — tested by a deliberately malicious manifest
entry and a deliberately malicious migration, both of which must raise `NeverWriteViolation`
**And** the symlinked-planning-artifacts case is included in the SC-08 proof

### Story 12.5: CLI contract, idempotence harness, and performance gates

As a machine and as a human,
I want consistent flags, stable JSON, correct exit codes, and bounded runtimes,
So that Genesis is usable unattended and predictable interactively.

**Type:** test • **Effort:** M • **Deps:** S-10.7, S-11.6 • **FR/AD:** FR58, FR59, FR61, NFR-P1,
NFR-P2, NFR-P3, NFR-O1, AD-01, AD-10, SC-03, SC-09

**Acceptance Criteria:**

**Given** every verb
**When** the contract suite runs
**Then** all verbs accept `--json` and `--quiet`, and `--json` output is schema-stable across
verbs (FR58, NFR-O1)
**And** all mutating verbs accept `--dry-run` explicitly, and `adopt` / `update` default to it
(FR59)
**And** exit codes match S-7.2's taxonomy for every failure mode, asserted case by case (FR61)
**And** `rich` and `typer` are imported **only** in `cli.py` (AD-01), asserted by an import test
**And** the **idempotence harness** applies AD-10's universal shape to every verb: run, then
detect+plan, assert zero actions — covering `init`, `adopt` (SC-03), and `update`
**And** performance gates: `check` < 5 s (NFR-P1) and `adopt --dry-run` < 10 s (NFR-P2) on a
`local-recipes`-sized fixture; `init` end-to-end < 5 min (NFR-P3, SC-09)

### Story 12.6: README, adoption guide, and the finding→remedy reference

As a first-time adopter,
I want to understand the four verbs, the five classes, and every finding I might hit,
So that adopting the model does not require reading Genesis's source.

**Type:** docs • **Effort:** S • **Deps:** S-12.5 • **FR/AD:** NFR-M3, D1

**Acceptance Criteria:**

**Given** the shipped package
**When** the documentation is written
**Then** the README covers all four verbs with worked examples, the five artifact classes and
what each means for the reader, the two version numbers, and the state file's role
**And** a **finding → remedy reference** documents every member of the findings enum with its
severity and its fix (NFR-M3), in the shape of `SYNC-RUNBOOK.md`'s finding→remedy mapping
**And** an adoption guide walks the brownfield path: dry-run → review plan → apply → wire
`check` into CI
**And** an air-gapped deployment note covers the in-package templates and the conda-provisioned
engine
**And** the managed-region contract is documented for humans: what the markers mean, that
editing inside them is detected, and that deleting them is a sanctioned opt-out
**And** a test asserts every findings-enum member appears in the reference doc, so the doc
cannot go stale

---

## Story DAG (critical path + key dependencies)

```
S-7.1 ──┬─→ S-7.2 ──→ S-7.3 (GUARD) ──────────────────────────┐
        │              ↘                                       │
        │               S-7.4 ──→ S-7.5 ──→ S-9.5              │
        └─→ S-7.6 (SPIKE-0 · GATES E10)                         │
                                                               │
S-7.4 ──→ S-8.1 ──→ S-8.2 ──→ S-8.3 ──→ S-8.4 ──→ S-8.5        │
                       ↘                    ↘                  │
S-7.2 ──→ S-9.1 ──→ S-9.2 ──→ S-9.3 ──→ S-9.6 ←────────────────┘
                       ↘  ↘
                        S-9.4 ─────────↗

S-7.6 + S-7.3 ──→ S-10.1 ─┐
S-7.3 ────────→ S-10.2 ───┼─→ S-10.3 ──→ S-10.4 ──→ S-10.5 ──→ S-10.6 ──→ S-10.7
S-9.6 ───────────────────┘                                   ↘
                                                              S-8.5

S-7.5 + S-8.4 ──→ S-11.1 ──→ S-11.2
S-10.3 + S-10.2 ──→ S-11.3 ──→ S-11.4 ←── S-11.1, S-8.3
S-10.5 ──→ S-11.5
S-7.4 + S-10.2 ──→ S-11.6

S-7.1 + S-11.6 ──→ S-12.1
S-10.6 + S-11.1 + S-11.2 ──→ S-12.2 (ORACLE)
S-10.7 + S-10.5 ──→ S-12.3
S-10.3 + S-11.4 ──→ S-12.4
S-10.7 + S-11.6 ──→ S-12.5 ──→ S-12.6
```

**Critical path (single builder, no parallelism):**
S-7.1 (S) → S-7.2 (XS) → S-7.3 (M) → S-7.4 (M) → S-7.5 (L) → S-8.1 (S) → S-8.2 (M) →
S-8.3 (M) → S-8.4 (M) → S-9.2 (M) → S-9.6 (M) → S-10.1 (M) → S-10.3 (M) → S-10.5 (M) →
S-10.6 (L) → S-10.7 (M) → S-11.1 (M) → S-11.3 (M) → S-11.4 (M) → S-12.2 (M) ≈ **38 days**.
Off-critical-path work (S-7.6, S-8.5, S-9.1/9.3/9.4/9.5, S-10.2/10.4, S-11.2/11.5/11.6,
S-12.1/12.3/12.4/12.5/12.6) adds ≈ 16 days ⇒ **~54 days ≈ 11 weeks**.

**S-7.6 (Spike-0) is off the critical path in duration but gates E10 in sequence** — it must
complete before S-10.1 starts, and it is cheap (S), so it should be run in parallel with E7's
back half.

---

## Special stories

| Story | Why it is special |
|---|---|
| **S-7.3** | The write guard. Everything downstream assumes it. Build it before anything writes. |
| **S-7.6** | Spike-0 — **gates E10**. A failure changes AD-02 or promotes a bespoke materializer. |
| **S-8.3** | The one algorithm that cannot be delegated to Copier; AR-1 and kill criterion K-01 live here. |
| **S-12.2** | The oracle. A non-empty plan that needs special-casing to fix triggers **K-02**. |
| **S-12.4** | Proves SC-08 — the structural guarantee that the update path cannot touch Tier-0/Tier-2. |

**Not a conda-forge effort.** Per PRD § D5, Genesis consumes `copier` from the existing
feedstock (consume-not-submit, G58) and authors no recipe. CLAUDE.md's CFE Rule 1 (invoke
`conda-forge-expert`) and Rule 2 (closeout retro) are **not** triggered by this epic set. If a
future story adds anything under `recipes/`, both rules apply to that story.

---

## Final structured JSON

```json
{
  "status": "complete",
  "epicsFile": "_bmad-output/projects/pyforge-marshal/planning-artifacts/epics-genesis-installer.md",
  "epicCount": 6,
  "storyCount": 36,
  "epics": [
    {"id": "E7", "title": "Foundation & the Write Guard", "stories": 6, "effort_days": 7},
    {"id": "E8", "title": "The Managed-Region Engine", "stories": 5, "effort_days": 8},
    {"id": "E9", "title": "Detect & Plan", "stories": 6, "effort_days": 9},
    {"id": "E10", "title": "Materialize & the Core Verbs", "stories": 7, "effort_days": 12},
    {"id": "E11", "title": "Derive, Migrate & Update", "stories": 6, "effort_days": 10},
    {"id": "E12", "title": "Packaging, Oracle & Hardening", "stories": 6, "effort_days": 8}
  ],
  "criticalPath": [
    "S-7.3: fs write primitive + never-write guard",
    "S-7.5: the V1 extraction manifest",
    "S-8.3: span substitution",
    "S-8.4: anchor resolution + insertion",
    "S-9.6: Plan types + fingerprint + builder",
    "S-10.1: Copier engine wrapper",
    "S-10.3: apply runner",
    "S-10.6: genesis adopt",
    "S-11.4: genesis update",
    "S-12.2: local-recipes empty-plan oracle"
  ],
  "criticalPathDays": "~38 days (54 days total V1 with off-path work)",
  "specialStories": {
    "spike0": "S-7.6 (GATES E10)",
    "writeGuard": "S-7.3 (foundation for every write)",
    "riskiestAlgorithm": "S-8.3 (region substitution; kill criterion K-01)",
    "oracle": "S-12.2 (SC-02; kill criterion K-02)",
    "structuralGuarantee": "S-12.4 (SC-08 proof)",
    "condaRecipe": "none — copier is consumed from the existing feedstock (G58); CFE Rules 1 & 2 not triggered"
  },
  "next": "bmad-check-implementation-readiness gate, then bmad-sprint-planning"
}
```
