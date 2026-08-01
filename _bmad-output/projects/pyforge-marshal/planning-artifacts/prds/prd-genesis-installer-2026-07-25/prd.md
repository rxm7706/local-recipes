---
title: "Product Requirements Document — pyforge-genesis (Genesis)"
status: "final"
created: "2026-07-25"
updated: "2026-08-04"
project_slug: "pyforge-genesis"
currency_review: Reviewed 2026-08-04 — spec/brief timestamp bump was structural (project relocation / memlog story-completion recording), not content drift; PRD unchanged.
dream: "docs/dreams/pyforge-genesis.md"
inputs:
  - "planning-artifacts/product-brief-pyforge-genesis.md"
  - "planning-artifacts/research/domain-research-scaffolder-landscape.md"
  - "planning-artifacts/research/technical-research-installer-implementation.md"
  - "{project-root}/docs/dreams/pyforge-genesis.md"
  - "{project-root}/docs/dreams/ecosystem-crew.md"
  - "{project-root}/docs/dreams/README.md"
  - "{project-root}/AGENTS.md"
  - "{project-root}/CLAUDE.md"
  - "{project-root}/_bmad-output/PROJECTS.md"
  - "{project-root}/archive/docs/bmad-setup-plan.md"
  - "{project-root}/scripts/bmad-switch, scripts/bmad-loop-worktree, scripts/bmad_drift_check.py"
distribution:
  dist: "pyforge-genesis"
  module: "pyforge.genesis"
  cli: "genesis"
---

# Product Requirements Document — pyforge-genesis (Genesis)

## Executive Summary

Genesis packages this repository's proven operating model as an installable tool with
two verbs — **`genesis init`** (greenfield: a new repository born Dream-first) and
**`genesis adopt`** (brownfield: layer the model onto an existing repo without disturbing
what runs) — plus the two verbs that make an install *stay* correct: **`genesis check`**
(read-only conformance, non-zero exit, CI-runnable) and **`genesis update`** (take a later
model version via a reviewable plan and version-ordered migrations).

This PRD resolves the two questions the Dream and the brief left open:

1. **The extraction question** — § *The Extraction Manifest* gives the concrete
   per-artifact classification. The Dream's three-way split (copied / referenced /
   generated) is **one class short**: "copied" divides into **MANAGED** (tool-owned,
   regenerated on update) and **SEEDED** (written once, repo-owned forever). That
   distinction is exactly what decides whether a model upgrade may rewrite a file, so it
   is load-bearing rather than pedantic.
2. **The Genesis ↔ Marshal boundary** — § *Boundaries*. **Genesis installs the machinery;
   Marshal operates it.** Genesis's write scope is a repo's structure and conventions;
   Marshal's is a repo's executions.

Genesis wraps Copier (v9.17.0 on conda-forge, `noarch: python`, MIT — no new recipe) for
file materialization, versioned updates, and migrations, and builds four things Copier has
no concept of: the model content, the brownfield inventory/plan, marker-delimited managed
regions inside repo-owned files, and conformance checking.

---

## Success Criteria

### Primary success criterion (the master switch)

**SC-01.** A second repository created by `genesis init` runs a full Dream → spec → epics →
loop-driven build, and later **takes a model upgrade via `genesis update` with no hand
edits** — `genesis check` green before and after.

### Supporting metrics (all mechanically testable)

| ID | Criterion | Measured by |
|---|---|---|
| SC-02 | `genesis adopt --dry-run` against `local-recipes` at the shipped model version produces an **empty plan** | the reference-oracle test |
| SC-03 | `genesis adopt` is idempotent — second run ⇒ empty plan, zero files changed | integration test |
| SC-04 | `genesis adopt` on a hand-edited managed region **refuses and reports**; does not overwrite | integration test |
| SC-05 | `genesis adopt --apply` on a dirty git worktree refuses | integration test |
| SC-06 | `genesis init` + `genesis check` green **offline, zero network calls** | egress-counter test (warden's established pattern) |
| SC-07 | A simulated breaking model change (model v1 → v2) is absorbed by a migration in an installed repo with no manual edits | migration integration test |
| SC-08 | `genesis update` **cannot** write to `docs/dreams/**` or `**/planning-artifacts/**` | write-scope guard test |
| SC-09 | `genesis init` to a working Dream-first repo in **< 5 minutes** wall-clock (vs. the 10-phase manual setup plan) | timed smoke test |
| SC-10 | 100% of model artifacts in the manifest are classified; no artifact is unclassified | manifest-coverage test (mirrors `bmad_drift_check.py`'s `uncovered` HARD finding) |

### Counter-metrics (watch for success that is actually failure)

| ID | Counter-metric | Why it matters |
|---|---|---|
| CM-01 | Number of manifest entries in the **SEEDED** class that adopters later hand-edit back toward the model | high count means the class was assigned wrong — those artifacts should be MANAGED |
| CM-02 | Number of `skips[]` entries adopters accumulate | a growing skip list means the model is being rejected in practice |
| CM-03 | Migrations authored per model minor version | if every minor needs a migration, the model surface is too volatile to install |

### Kill criteria

Genesis pauses or rescopes if, at V1 completion:

- **K-01** — the managed-region merge proves unreliable on real files (corruption or
  unresolvable conflicts in either of the first two adopters);
- **K-02** — SC-02 (the empty-plan oracle against `local-recipes`) cannot be reached
  without special-casing the model into incoherence — meaning the model is not actually
  extractable and the Dream's stabilization gate was called too early;
- **K-03** — CM-03 shows migrations cost more than hand-editing each installed repo would.

---

## User Journeys

### J1 — "Start a new pyforge sibling, Dream-first from day zero"

A maintainer is spinning `pyforge-scribe` out of the monorepo into its own repository. He
runs `genesis init ../pyforge-scribe --slug pyforge-scribe --agents claude,cursor`. Genesis
materializes `docs/dreams/` (README, frontmatter contract, one seed Dream stub named for
the slug), the tier layout with its gitignore rules, `AGENTS.md` carrying the portability
contract, `CLAUDE.md` and `.cursor/rules/specs.mdc` generated from that contract, the BMAD
multi-project subtree with `PROJECTS.md` and its first row, `scripts/bmad-switch`, and the
drift detector wired into CI. He writes the Dream, runs `bmad-spec`, and the loop starts.
Total elapsed before the first Dream: under five minutes, versus reading ten phases of a
562-line plan.

### J2 — "Adopt the model into a repo that already ships"

A team has a working data-platform monorepo — CI, releases, an existing `CLAUDE.md`, and a
`docs/adr/` convention they like. They run `genesis adopt` (dry-run by default). Genesis
prints a plan: 9 artifacts absent (will create), 3 present-conformant (skip), 1
present-divergent (`CLAUDE.md` — will insert a managed region at an anchor, leaving all
existing content), 1 present-legacy (`docs/adr/` — recorded, preserved, untouched). Nothing
has been written. They review the plan in a PR, run `genesis adopt --apply`, and their
build still works because Genesis never touched a file it did not name.

### J3 — "Take a model upgrade six weeks later"

The model ships v1.3.0: the durable-story-specs convention adds a `planning-artifacts/specs/`
rule to the tier table, and `bmad-switch` gains an atomicity fix. An installed repo runs
`genesis check` in CI, which fails with `model-behind: repo at 1.2.0, available 1.3.0`. The
maintainer runs `genesis update` — a plan is written naming two migrations and three files.
He reviews it, runs `genesis update --run`. The tiers managed region in `AGENTS.md` is
replaced; `scripts/bmad-switch` is regenerated wholesale; the derived adapters are
recomputed. His Dreams, PRDs, and epics are untouched — structurally unreachable from the
update path. `genesis check` is green.

### J4 — "The model and the repo disagree"

An engineer hand-edits the tiers block inside `AGENTS.md` because a rule did not fit. Next
CI run, `genesis check` reports `managed-region-modified: AGENTS.md#tiers (hash mismatch)`
and exits non-zero. He has three sanctioned moves: revert; delete the markers (a deliberate,
greppable opt-out that Genesis records and thereafter respects); or add the path to
`skips[]`. What he cannot do is diverge silently — which is the entire point, because the
agents reading that file would otherwise follow a rule the model does not have.

### J5 — "Verify the model is still extractable"

A CFE retro lands a convention change directly in `local-recipes` (out-of-band, as always
happens). CI runs `genesis adopt --dry-run` against the repo itself. The plan is non-empty:
the model in the package no longer matches the repo it was extracted from. That is the
signal to update the Genesis templates — the drift is caught the day it appears rather than
at the next install.

---

## Domain Requirements

### D1 — The model is read by agents, not only humans

Every artifact Genesis installs is consumed by autonomous agents (Claude Code, Cursor,
Copilot, Gemini, BMAD skills, bmad-loop). Consequences that shape requirements throughout:
staleness is a **behavioral bug**, not documentation debt; "correctness of an install" must
be **machine-verifiable** (files present, markers intact, hashes matching, detector green)
rather than a matter of taste; and any ambiguity in a convention becomes divergent agent
behavior.

### D2 — Air-gapped operation is a standing constraint

`docs/dreams/enterprise-airgap.md` is `realized`; `pyforge-warden`'s packaging states
engines are "never curl-fetched at runtime." Genesis inherits this: engine as conda
package, templates in-package, zero egress on `init` / `adopt` / `check`.

### D3 — This repo's PR CI gates apply to Genesis's own development

Per `CLAUDE.md`: any change outside `recipes/` requires the `maintenance` label on the PR,
and any `pixi.toml` change requires a regenerated committed `environment.yaml`
(ungated by the label). Genesis adds a pixi feature + environment, so both gates fire.
`pixi run -e local-recipes llms-full-check` will additionally flag
`docs/reference/library-llms-full.md` as stale — that catalog's scaffolding section
currently recommends "cookiecutter (+ cruft to stay synced)" and must be updated.

### D4 — Tier discipline binds Genesis itself

Genesis's own planning artifacts are Tier 2; its story specs are durable and tracked under
`planning-artifacts/specs/` per the 2026-07-25 convention; nothing it produces may be
git-tracked under `implementation-artifacts/`.

### D5 — Not a conda-forge recipe effort

Genesis consumes `copier` from the existing conda-forge feedstock (consume-not-submit,
CFE G58). No new recipe is authored, so the CFE Rule-1 invocation and Rule-2 retro are
**not** triggered by the core work. They *are* triggered if a story adds a recipe under
`recipes/` (none is planned in V1).

---

## The Extraction Manifest

**This section resolves the Dream's central question.** It is the normative contract that
FR1–FR6 encode and SC-10 tests.

### The classification rule

> Classify each artifact by **who must be able to change it** and **how an installed repo
> takes a later model upgrade for it.**

| Class | Definition | Behavior on `genesis update` | Behavior on hand-edit |
|---|---|---|---|
| **REFERENCED** | Not materialized. The repo depends on it by version range; it lives upstream. | nothing in the repo changes | n/a |
| **COPIED · MANAGED** | Materialized, **tool-owned**. The repo should not hand-edit it. | regenerated wholesale | `check` reports; `update` refuses without `--force` |
| **COPIED · SEEDED** | Materialized once as a starting point, then **repo-owned forever**. | never touched | expected and fine |
| **GENERATED · DERIVED** | Computed from the neutral contract and/or repo state. | recomputed every run (idempotent) | overwritten on next run; `check` reports |
| **HYBRID · MANAGED REGION** | A repo-owned file containing a tool-owned, marker-delimited span. | only the span is replaced | `check` reports hash mismatch on the span only |

### The V1 manifest

Derived from a live inventory of the model surface in `local-recipes` (2026-07-25).

#### REFERENCED

| Artifact | Pin | Rationale |
|---|---|---|
| `bmad-method` | `>=6.10.0` (conda-forge) | upstream product; gains `bmad-dev-auto` at 6.10; never vendored |
| `bmad-loop` | `>=0.8.1` (conda-forge) | Marshal's orchestrator; Genesis declares the floor, Marshal operates it |
| `copier` | `>=9.17,<10` (conda-forge) | Genesis's own engine |
| `pixi` | `>=0.72.2` | `preview = ["pixi-build"]` requires it |
| `tmux` | `>=3.7b` | loop spawns agent sessions in it; Linux/macOS only |
| Installed BMAD skills (`_bmad/bmm/**`, `_bmad/core/**`) | installer-owned | regenerated by `bmad-method install`; Genesis must never write here |

Genesis **verifies presence and floor** for these (FR30) and never installs them.

#### COPIED · MANAGED

| Artifact | Why managed |
|---|---|
| `scripts/bmad-switch` | executable model machinery with a known production incident (the 10-hour marker/symlink desync); bug fixes **must** propagate to installed repos |
| `scripts/bmad-loop-worktree` | concurrent loop homes; same reasoning |
| `scripts/bmad_drift_check.py` (the detector) | must run locally, offline, in the adopting repo's CI; this is the conformance engine and it evolves with the model |
| `docs/dreams/README.md` | the Tier-0 contract itself — the Dream frontmatter schema, the flow diagram, the conventions |
| The model's own rule text (tier tables, portability contract) | delivered *into* hybrid files, not as standalone files — see HYBRID |
| CI workflow that runs `genesis check` + the detector | mechanical; no reason for a repo to own it |
| `.gitignore` model block | the tier rules made executable (`_bmad-output/projects/*/implementation-artifacts/`, the two symlinks, `_bmad/custom/.active-project`, `.bmad-loop/runs/`) — delivered as a managed region in a repo-owned `.gitignore` |

#### COPIED · SEEDED

| Artifact | Why seeded |
|---|---|
| A starter Dream at `docs/dreams/<slug>.md` | it is the repo's content from the moment it is written |
| `_bmad-output/projects/<slug>/.bmad-config.toml` | per-project config the team tunes |
| `_bmad/custom/config.toml` (global custom layer) | exists precisely so teams customize it |
| `.bmad-loop/policy.toml` | per-project verify gates and worktree seeds — necessarily repo-specific (the origin document devotes Phase 9.3 to this) |
| `planning-artifacts/specs/README.md` | the durable-specs convention explainer; the repo will extend it with its own provenance table |
| Deck-family scaffolding under `presentations/<slug>/` | Herald's surface; Genesis lays the directory, Herald owns the content |

#### GENERATED · DERIVED

| Artifact | Derived from |
|---|---|
| `CLAUDE.md` (the Dream-first / tiers head matter) | the neutral contract + selected agents |
| `.cursor/rules/specs.mdc` | the neutral contract (verified: it is a mechanical projection of `AGENTS.md`'s tier table) |
| `GEMINI.md` | same |
| `.github/copilot-instructions.md` | same |
| `_bmad-output/PROJECTS.md` § *Projects* table rows | the set of `_bmad-output/projects/*/.bmad-config.toml` files present |
| The `_bmad-output/{planning,implementation}-artifacts` symlinks | the active-project marker (already generated by `bmad-switch`; Genesis ensures they exist and are gitignored) |
| Directory skeletons (`docs/dreams/`, `docs/specs/` only when legacy, project subtrees) | the manifest + slug |

The four agent-adapter files are the clearest case for DERIVED: all three inspected
(`GEMINI.md`, `.cursor/rules/specs.mdc`, `.github/copilot-instructions.md`) restate the
same tier table with per-tool framing. Maintaining them as four independent copies is how
they drift; generating them from one contract is how they cannot.

#### HYBRID · MANAGED REGION

| File | Region(s) | Rationale |
|---|---|---|
| `AGENTS.md` | `tiers`, `portability-contract`, `dream-first-workflow` | the neutral contract must upgrade; the rest of the file is the repo's own (tool-discovery table, local pointers) |
| `CLAUDE.md` | `tiers`, `bmad-multiproject` | in `local-recipes` this file is 230 lines of repo-specific guidance around a small model core; the model core must upgrade, the rest must never be touched |
| `.gitignore` | `model-ignores` | the tier rules in executable form, inside a file every repo owns |
| `README.md` (optional) | `model-badge` | opt-in; off by default |

### What Genesis must NEVER write (the structural guarantee)

| Path | Why |
|---|---|
| `docs/dreams/*.md` (except the one seed at `init`) | Tier 0 is the team's aspiration |
| `**/planning-artifacts/**` (except the seeded `specs/README.md` at `init`) | Tier 2 is the team's spec and planning work |
| `**/implementation-artifacts/**` | Tier 3, gitignored, runtime scratch |
| `docs/specs/*.md` | legacy tier — preserve and mark, never edit |
| `_bmad/bmm/**`, `_bmad/core/**` | installer-owned; regenerated by BMAD |

Enforced by code and proven by test (FR35, SC-08), not by convention. This is the
structural expression of the field's hardest-won lesson — spec-kit's guidance to *"keep
tooling updates separate from feature artifact evolution."*

### Deliberately deferred to V1.x

`.claude/skills/**` (skill content), `pixi.toml` task blocks, and
`docs/reference/library-llms-full.md` are model-adjacent but too repo-specific to classify
confidently at V1. They are recorded as `unclassified-deferred` in the manifest, and
SC-10's coverage test treats that as an explicit, enumerated state rather than a gap.

---

## Boundaries

### Genesis ↔ Marshal (the resolution)

**Genesis installs the machinery; Marshal operates it.**

| | Genesis | Marshal |
|---|---|---|
| Write scope | a repo's **structure and conventions** | a repo's **executions** |
| Owns | the tier layout, AGENTS.md family, BMAD multi-project wiring, the deck-family skeleton, the conformance detector | bmad-loop runs, gates, escalation, graduated autonomy, worktree lifecycle, project switching **at run time** |
| Lifecycle | install-time and upgrade-time | run-time |
| `init` semantics | `genesis init` creates **the repository** the specs will live in | `marshal init --spec …` initializes **a build** from a spec |
| `scripts/bmad-switch`, `scripts/bmad-loop-worktree` | **delivers** them (MANAGED class) and keeps them current | **runs** them; owns their behavior and evolution |
| `.bmad-loop/policy.toml` | **seeds** it | **owns and rewrites** it per project |

The overlap point is real and named: the two scripts are Marshal's per the 2026-07-23
ownership review, but they must be *installed* to exist in a new repo at all. Resolution:
**Marshal owns the source; Genesis owns the delivery.** A change to `bmad-switch` lands in
Marshal's tree and is picked up by Genesis's manifest at the next model version. Genesis
never forks them.

### Genesis ↔ Doctor

`genesis check` asks *"does this repo conform to the model?"*; `doctor check` asks *"is this
machine able to run the factory?"* Genesis's REFERENCED-dependency verification (FR30)
overlaps Doctor's pre-flight charter, so: **Genesis performs a minimal presence-and-floor
probe with no dependency on Doctor** (it must work in a repo that has not adopted Doctor),
and **delegates to `doctor check` when it is available**, reporting Doctor's findings
rather than duplicating them.

### Genesis ↔ Herald

Genesis lays down `presentations/<slug>/` and the deck-family conventions (SEEDED); Herald
fills, seeds to Design, and pulls back. Genesis never touches deck content.

---

## Project Scoping

### Strategy

Build the **update path first**, not the install path. Every tool in the surveyed field
that failed, failed at update; `init` on top of Copier is close to free once the manifest
and the managed-region engine exist. The `local-recipes` empty-plan oracle (SC-02) is
available from the first week and is the highest-signal test in the project — it should
gate every epic, not just the last.

### V1 feature set

1. **Manifest + classification engine** — the model declared as data, with the five classes
   and complete coverage.
2. **Managed-region engine** — marker parse, span replace, content hash. The riskiest
   bespoke component; independently testable; built early.
3. **`genesis adopt`** — detect → plan → confirm → apply, dry-run default, idempotent,
   `present-legacy` aware.
4. **`genesis check`** — read-only, non-zero exit, CI-shaped output.
5. **`genesis init`** — greenfield, on the same engine as adopt.
6. **`genesis update`** + migration runner — two-phase plan/apply, version-ordered,
   applied-once, write-scope guarded.
7. **State file** — schema-validated, tool-owned, do-not-edit.
8. **Agent adapter fan-out** — Claude Code, Cursor, Copilot, Gemini generated from the
   neutral contract.
9. **Packaging** — pixi workspace member, in-package templates, lean env, offline proof.

### Explicitly out of scope for V1

Hosted registry of installations · repository creation on a git host (`init` makes a tree,
not a GitHub repo) · non-git targets · composable feature modules (adopt a subset) ·
`check --fix` · fleet conformance scorecards · publishing the model as a separately
versioned artifact.

---

## Functional Requirements

### Model manifest & classification

- **FR1** — The model is declared as **data** (a manifest file inside the package), not as
  code branches. Each entry carries: path or path-pattern, class, applicable model-version
  range, and (for HYBRID) its region names and anchors.
- **FR2** — Five classes are supported: `referenced`, `copied-managed`, `copied-seeded`,
  `generated-derived`, `hybrid-managed-region`.
- **FR3** — The manifest supports an explicit `unclassified-deferred` state so that
  deferral is enumerated rather than silent.
- **FR4** — A coverage check verifies that every artifact Genesis knows about carries
  exactly one class; an unclassified artifact is a HARD failure. (Mirrors
  `bmad_drift_check.py`'s `uncovered` finding.)
- **FR5** — The manifest is versioned by **model semver**, independent of the
  `pyforge-genesis` package version. Both are recorded in installed state.
- **FR6** — The manifest declares the **never-write path set** (§ *The Extraction
  Manifest*), which the apply and update paths enforce.

### `genesis init` (greenfield)

- **FR7** — `genesis init <path>` creates a Dream-first repository tree at `<path>`,
  materializing every manifest artifact applicable to a new repo.
- **FR8** — `init` accepts `--slug` (the first BMAD project slug, defaulting to the
  directory name) and `--agents` (comma-separated adapter selection).
- **FR9** — `init` seeds exactly one Dream stub at `docs/dreams/<slug>.md` conforming to
  the Tier-0 frontmatter contract (`title`, `type: dream`, `owner`, `status: seeded`).
- **FR10** — `init` creates the BMAD multi-project subtree:
  `_bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}`,
  `.bmad-config.toml`, `planning-artifacts/specs/README.md`, and `PROJECTS.md` with the
  first row.
- **FR11** — `init` writes the `.gitignore` model region covering the tier rules: the
  gitignored `implementation-artifacts/`, the two `_bmad-output` compatibility symlinks,
  `_bmad/custom/.active-project`, `.bmad-loop/runs/` and `cache/`, and
  `_bmad-output/projects/*/.bmad-config.user.toml`.
- **FR12** — `init` writes the state file recording `mode: init`, model version, CLI
  version, selected agents, and the per-artifact hashes.
- **FR13** — `init` refuses to run into a non-empty directory unless `--force`; the
  documented path for an existing repo is `adopt`.

### `genesis adopt` (brownfield)

- **FR14** — `genesis adopt` runs **detect → plan → confirm → apply** and is **dry-run by
  default**; `--apply` (or `--yes` for unattended use) executes.
- **FR15** — Detect classifies each manifest artifact in the target repo as `absent`,
  `present-conformant`, `present-divergent`, or `present-legacy`.
- **FR16** — `present-legacy` artifacts are **recorded and preserved, never modified or
  deleted**, and are listed in the state file's `legacy[]`.
- **FR17** — The plan is a **machine-readable artifact** written to disk (not only printed),
  listing per artifact: path, class, detected state, proposed action, and rationale.
- **FR18** — Apply materializes only what the plan names. Artifacts already present are
  preserved unless their class is `copied-managed` or `generated-derived`.
- **FR19** — `adopt` is **idempotent**: a second run on an unchanged repo produces an empty
  plan and writes nothing.
- **FR20** — `adopt --apply` refuses on a dirty git worktree, and refuses outside a git
  repository.
- **FR21** — `adopt` refuses (with a specific, actionable message) when a managed region or
  managed file has been hand-modified, unless `--force`.
- **FR22** — `adopt` accepts `--skip <glob>` (recorded in state) and honors previously
  recorded skips on subsequent runs.

### `genesis check` (conformance)

- **FR23** — `genesis check` is **read-only** and never writes to the repo (state file
  included).
- **FR24** — `check` exits non-zero on any HARD finding; `--strict` additionally fails on
  DRIFT findings.
- **FR25** — Findings are typed and stable, at minimum: `artifact-missing`,
  `managed-file-modified`, `managed-region-modified`, `managed-region-missing`,
  `derived-stale`, `model-behind`, `state-invalid`, `never-write-violation`,
  `referenced-dep-missing`.
- **FR26** — `check --json` emits a machine-readable report suitable for CI annotation.
- **FR27** — `check` reports the repo's model version against the model version available
  in the installed package (`model-behind` / current / ahead).
- **FR28** — `check` runs offline and completes in under 5 seconds on a repo the size of
  `local-recipes`.

### `genesis update` + migrations

- **FR29** — `genesis update` is **two-phase**: the default invocation writes a plan and
  changes nothing; `--run` applies the plan.
- **FR30** — Update verifies REFERENCED dependencies against their declared floors and
  reports (does not install) anything missing or below floor; delegates to `doctor check`
  when available.
- **FR31** — Migrations are ordered by model semver, applied **exactly once**, and recorded
  in state's `migrations_applied[]`.
- **FR32** — Migrations may only touch `copied-managed`, `generated-derived`, and
  `hybrid-managed-region` artifacts. Touching `copied-seeded` requires an explicit
  interactive/`--yes` opt-in and is reported as an offer, never imposed.
- **FR33** — Update regenerates `copied-managed` files wholesale and recomputes
  `generated-derived` files, after hash-guard checks pass.
- **FR34** — Update replaces only the marked span of `hybrid-managed-region` files.
- **FR35** — Update **cannot** write to any path in the never-write set (FR6); an attempt is
  a hard error and a test asserts it.
- **FR36** — `genesis update --force` maps to Copier `run_recopy` semantics (discard local
  evolution of managed artifacts) and requires explicit confirmation.

### State file

- **FR37** — Genesis writes one tool-owned state file recording: `model_version`,
  `genesis_version`, `adopted_at`, `last_update`, `mode`, `agents[]`, `managed[]` (path +
  class + content hash), `skips[]`, `legacy[]`, `migrations_applied[]`.
- **FR38** — The state file carries a prominent do-not-hand-edit header.
- **FR39** — State is validated against a JSON schema on every read; an invalid state file
  is a `state-invalid` finding, not a crash.
- **FR40** — Genesis never hand-edits Copier's answers file; if Copier's answers file is
  used it is treated as a second tool-owned file.
- **FR41** — Content hashes cover managed files and managed regions, enabling FR21 / FR25.
- **FR42** — The state file is git-tracked (it is repo metadata, not scratch).

### Managed regions

- **FR43** — A managed region is delimited by begin/end markers carrying the region name and
  the model version that wrote it.
- **FR44** — Update replaces the span between markers by **pure text substitution** — never
  a three-way merge — so a half-merged file is not representable.
- **FR45** — Marker syntax is **per file format** (HTML comments for markdown, `#` comments
  for `.gitignore` / TOML / YAML), resolved through a format registry.
- **FR46** — If markers are absent in a file that should carry a region, Genesis inserts the
  region at a declared **anchor** (e.g. after the first `# Heading`), or appends when no
  anchor matches.
- **FR47** — Deleting the markers is a **sanctioned permanent opt-out**: Genesis records it
  in state and does not reinsert on later runs. (Mirrors Copier's locally-deleted-path rule.)
- **FR48** — Nested or overlapping regions are rejected with a specific error.

### Agent adapter fan-out

- **FR49** — The neutral contract (tiers, portability, Dream-first workflow) has exactly one
  source in the manifest; all adapter files derive from it.
- **FR50** — V1 supports four adapters: Claude Code (`CLAUDE.md`), Cursor
  (`.cursor/rules/specs.mdc`), GitHub Copilot (`.github/copilot-instructions.md`), Gemini
  (`GEMINI.md`).
- **FR51** — Adapter selection is per-repo, recorded in state, and changeable later
  (`genesis adopt --agents …` adds adapters idempotently).
- **FR52** — For an adapter file that already exists with repo-specific content
  (`CLAUDE.md` is the common case), the model content is delivered as a **managed region**
  rather than by overwriting the file.

### Templates, distribution & CLI

- **FR53** — Model templates ship **inside** the `pyforge-genesis` package; no runtime fetch
  is required for any verb.
- **FR54** — `--template <path|url>` overrides the in-package templates, for development and
  for teams that fork the model.
- **FR55** — Genesis wraps Copier via its **public API only** (`run_copy`, `run_update`,
  `run_recopy`); no reliance on `Worker` internals or private modules.
- **FR56** — Copier's code-executing template features remain gated behind an explicit
  `--unsafe` flag.
- **FR57** — Genesis is distributed as a pixi workspace member producing a conda package,
  plus wheel/sdist, with console entry point `genesis`.
- **FR58** — All verbs support `--json` for machine consumption and `--quiet` for
  unattended runs.
- **FR59** — All mutating verbs support `--dry-run` explicitly (and default to it where
  FR14 requires).
- **FR60** — `genesis version` reports both the CLI version and the bundled model version.
- **FR61** — Non-zero exit codes are distinct and documented per failure mode (conformance
  failure, precondition failure, internal error).
- **FR62** — A `genesis explain <artifact>` verb prints an artifact's class, rationale, and
  update behavior — the model documenting itself to the agents that read it (D1).

---

## Non-Functional Requirements

### Reliability & safety

- **NFR-R1** — No verb may leave the repo in a partially-applied state: apply is
  transactional per plan, or reverts.
- **NFR-R2** — Git is the undo mechanism; every mutating verb requires a clean worktree so
  `git checkout .` fully reverts.
- **NFR-R3** — Managed-region substitution never produces conflict markers (a consequence
  of FR44).
- **NFR-R4** — The never-write guard (FR35) is enforced at the lowest write primitive, not
  at call sites, so no future code path can bypass it.

### Air-gapped operation

- **NFR-A1** — `init`, `adopt`, and `check` make **zero network calls** with in-package
  templates; asserted by an egress-counter test.
- **NFR-A2** — Every runtime dependency resolves from conda-forge (or an internal mirror);
  nothing is fetched at runtime.

### Performance

- **NFR-P1** — `check` completes in < 5 s on a `local-recipes`-sized repo.
- **NFR-P2** — `adopt --dry-run` completes in < 10 s on the same.
- **NFR-P3** — `init` to a working tree in < 5 minutes wall-clock end to end (SC-09).

### Compatibility

- **NFR-C1** — Python `>=3.12`, matching the other pyforge packages and Copier's floor.
- **NFR-C2** — `copier >=9.17,<10`, range-pinned not exact-pinned, with a version-range
  sync test (warden's established pattern).
- **NFR-C3** — Linux and macOS are first-class; Windows support is best-effort for
  `init`/`check` (the loop machinery is Linux/macOS, Windows via WSL).
- **NFR-C4** — `pyforge.genesis` coexists with `pyforge.warden` and `pyforge.atlas` in the
  shared `pyforge` namespace.

### Security

- **NFR-S1** — No execution of untrusted template content by default (FR56).
- **NFR-S2** — Genesis never writes credentials and never reads them from the target repo.
- **NFR-S3** — Templates are validated against the manifest before apply; a template
  writing outside its declared paths is a hard error.

### Maintainability & observability

- **NFR-M1** — The model manifest is the single source of truth; adding an artifact must not
  require editing engine code.
- **NFR-M2** — The `local-recipes` empty-plan oracle (SC-02) runs in Genesis's own CI, so
  model drift in the source repo is caught the day it appears.
- **NFR-M3** — Every finding type is documented with a remedy, in the shape of
  `bmad_drift_check.py`'s finding→remedy mapping.
- **NFR-O1** — Plans and reports are machine-readable (`--json`) and human-readable by
  default.

---

## Assumptions

1. **[ASSUMPTION]** Genesis targets git repositories only; non-git targets forfeit the
   update story entirely.
2. **[ASSUMPTION]** The model has genuinely stabilized (the Dream's gate). Evidence: atlas
   (32 stories) and warden (31 stories) both shipped through it; the durable-story-specs
   convention closed the last known hole on 2026-07-25.
3. **[ASSUMPTION]** `scripts/bmad_drift_check.py` (662 lines, with a HARD/DRIFT/INFO
   severity model and a coverage check that already HARD-fails unclassified files) can seed
   `genesis check` rather than requiring a from-scratch build. **Not yet validated against
   the code** — an early spike should confirm before Epic scoping hardens.
4. **[ASSUMPTION]** Copier's `run_copy` / `run_update` / `run_recopy` signatures are stable
   across 9.x.
5. **[ASSUMPTION]** Copier's answers-file path is template-configurable (affects FR40).
6. **[ASSUMPTION]** HTML-comment markers are unambiguous in the specific markdown files in
   the manifest.
7. **[ASSUMPTION]** First two adopters are `local-recipes` (oracle) and one greenfield
   pyforge sibling; external adoption is post-V1.
8. **[ASSUMPTION]** Marshal will accept ownership of `bmad-switch` / `bmad-loop-worktree`
   *source* while Genesis owns *delivery* — this needs Marshal's PRD to agree.

## Open Questions (carried to architecture)

1. **OQ-1** — CLI framework: typer + rich (both already pinned; better for the
   plan/diff/confirm UX) vs argparse (warden's lean-engine precedent). Note Copier already
   pulls in prompt-toolkit / questionary / pygments regardless.
2. **OQ-2** — One state file, or Genesis state alongside Copier's `.copier-answers.yml`?
   Depends on assumption 5.
3. **OQ-3** — Exact marker syntax and the format registry's initial coverage (FR45).
4. **OQ-4** — Does `genesis check` copy, extract, or re-implement `bmad_drift_check.py`?
   Depends on assumption 3. Extraction into the package is attractive but couples
   `local-recipes` to a Genesis release.
5. **OQ-5** — Where does the manifest live physically — one YAML/TOML file, or one file per
   class? Affects FR1 and NFR-M1.
6. **OQ-6** — Anchor semantics for FR46 when a repo's `CLAUDE.md` has an unusual structure.
   Fallback-to-append is specified; is that always safe?
7. **OQ-7** — Does the plan artifact get committed by convention (like Nx's
   `migrations.json`), and if so, where — and is it gitignored or tracked?
8. **OQ-8** — How does a repo *leave* the model (`genesis eject`)? Not in V1 scope, but the
   state file's design should not preclude it.
9. **OQ-9** — Model deprecation path: the manifest marks `docs/specs/` legacy today. Does
   the model define a migration from Tier-1 legacy to Tier-2, or only preserve?
