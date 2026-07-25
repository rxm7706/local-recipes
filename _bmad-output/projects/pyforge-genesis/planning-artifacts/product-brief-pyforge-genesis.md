---
title: "Product Brief: pyforge-genesis (Genesis)"
status: "complete"
created: "2026-07-25"
updated: "2026-07-25"
inputs:
  - "{project-root}/docs/dreams/pyforge-genesis.md (Tier-0 Dream — the seed)"
  - "{project-root}/docs/dreams/ecosystem-crew.md (founding Dream — the eight personas)"
  - "{project-root}/docs/dreams/README.md (Dream conventions, Tier-0 contract)"
  - "{project-root}/archive/docs/bmad-setup-plan.md (the origin document — Phases 0–10)"
  - "{project-root}/AGENTS.md (tiers + portability contract)"
  - "{project-root}/CLAUDE.md (multi-project pattern, durable story specs, sync loop)"
  - "{project-root}/_bmad-output/PROJECTS.md (multi-project index + registration procedure)"
  - "{project-root}/scripts/bmad-switch, {project-root}/scripts/bmad-loop-worktree"
  - "{project-root}/docs/intake/gists/how-we-operate/HOW-WE-OPERATE.md"
  - "planning-artifacts/research/domain-research-scaffolder-landscape.md"
  - "planning-artifacts/research/technical-research-installer-implementation.md"
references:
  - "https://copier.readthedocs.io/en/stable/updating/ — the update algorithm Genesis wraps"
  - "https://github.com/github/spec-kit — closest comparable: an installer for a way of working"
  - "https://nx.dev/docs/features/automate-updating-dependencies — two-phase migrate (plan, then apply)"
  - "https://projen.io/docs/introduction/getting-started/ — synthesis model (regenerate, don't merge)"
  - "conda-forge/copier-feedstock v9.17.0 — noarch:python, MIT (verified live 2026-07-25)"
project_slug: "pyforge-genesis"
---

# Product Brief: pyforge-genesis (Genesis)

## Executive Summary

**Genesis** packages this repository's proven operating model as an installable tool.
Two verbs: **`genesis init`** creates a new repository born Dream-first — `docs/dreams/`,
the tier layout, the AGENTS.md family, BMAD multi-project wiring, the deck family, from
day zero. **`genesis adopt`** layers that same model onto an existing repository without
disturbing what already runs. Distribution: dist `pyforge-genesis` / module
`pyforge.genesis` / CLI `genesis`.

The model Genesis installs is not theoretical. It was installed *here*, by hand, from a
562-line setup plan (`archive/docs/bmad-setup-plan.md`), and then run hard enough to
prove it: **pyforge-atlas** shipped 32 stories across waves 0–H through it (PRs #58–#105);
**pyforge-warden** shipped 31 stories across 6 epics through it (PR #110); fifteen BMAD
projects now share one installation; 25 Dreams sit at Tier 0 with a no-straggler policy
binding each to exactly one project. The Dream set the gate — *"awaits its own
`bmad-spec` run when the model stabilizes"* — and the model has stabilized. This brief
is the beginning of collecting on that.

The hard part is not scaffolding. Scaffolding is a solved commodity — Copier, cruft,
cookiecutter, and Nx generators all do it, and Copier is already a conda-forge package
(`copier` v9.17.0, `noarch: python`, MIT) that Genesis can simply consume. The hard part
is **the second install and every one after it**: when the model improves — a corrected
tier rule, a new drift-check finding, the durable-story-specs convention that landed on
2026-07-25 — how does an already-installed repository take that improvement? Every tool
in the field that failed, failed there. Genesis is designed backwards from that question.

## The Problem

**1. The model is trapped in one repository.** Everything that makes this repo work —
Dream-first governance, the four tiers and the rules against crossing them, the
framework-neutral portability contract, the six-layer BMAD config merge, the
marker+symlink project switch, the durable-story-specs convention, the detector/reconciler
sync loop — exists as conventions written into `CLAUDE.md`, `AGENTS.md`, `PROJECTS.md`,
and two shell-invoked Python scripts. There is exactly one way to get it into a second
repository today: read the 562-line setup plan and do all ten phases by hand. The next
pyforge sibling, the next enterprise innersource monorepo (`unity-data-stack` is already
waiting), and every external adopter pays that cost from scratch.

**2. Hand-installed models drift the moment they are installed.** The origin document is
itself the evidence: it is dated `2026-07-18`, and by `2026-07-25` it is already behind
in at least three ways — it points spec-first work at the now-legacy `docs/specs/` Tier 1,
it lists a `scripts/bmad-loop-project` helper as "recommended, not yet built," and it
predates the durable-story-specs convention entirely. A hand-installed copy in another
repo would have frozen at *its* install date with no mechanism to catch up, and the
agents reading it would faithfully follow the stale rules. **For an operating model read
by autonomous agents, staleness is not documentation debt — it is a behavioral bug.**

**3. The cost of getting it subtly wrong is high and silent.** The model has sharp edges
that took production incidents to find. The marker/symlink desync ran undetected for 10
hours and came within one command of overwriting pyforge-warden's PRD and epics with
local-recipes content. Story specs were being written into a gitignored Tier-3 directory,
and pyforge-warden lost 13 of 31 of them to worktree teardown before anyone noticed —
recovered only because Claude Code session transcripts happened to preserve the tool
calls; pyforge-atlas, whose transcripts were not in the local store, permanently lost 30
of 32. A hand-installed model reproduces the *shape* of these conventions without the
*guards*, and the guards are the expensive part.

**4. Brownfield is the common case, and it is the dangerous one.** Most repositories that
should adopt this model already exist, already build, already ship. An installer that
overwrites a working `.gitignore`, clobbers an existing `CLAUDE.md`, or deletes a legacy
convention that is still load-bearing is worse than no installer. This repo's own
`docs/specs/` tier is the canonical example: superseded, but still holding five in-flight
efforts that must be preserved and *marked* legacy — never removed.

## The Solution

Genesis is a small Python CLI that wraps a mature engine and adds the three things the
engine does not know about: the model itself, brownfield safety, and conformance.

**`genesis init <path>`** — greenfield. Materializes a complete Dream-first repository:
`docs/dreams/` with the README, frontmatter contract, and one seed Dream; the tier layout
with its gitignore rules; `AGENTS.md` carrying the portability contract plus the per-tool
adapter files for whichever agents the user selects; the BMAD multi-project subtree
(`_bmad-output/projects/<slug>/`, `.bmad-config.toml`, `PROJECTS.md` with the first row);
`scripts/bmad-switch` with its atomic marker+symlink switch; the drift detector wired
into CI; and the deck-family scaffolding.

**`genesis adopt`** — brownfield, and the verb that carries the product's risk. It runs
**detect → plan → confirm → apply**, dry-run by default:

- **Detect** walks the repo and classifies every model artifact as `absent`,
  `present-conformant`, `present-divergent`, or **`present-legacy`** — the state that
  exists specifically so a superseded-but-live convention is preserved and marked, not
  deleted.
- **Plan** emits a reviewable, committable artifact naming every proposed action. Nothing
  is written yet. (This two-phase split is Nx's `migrations.json` pattern, and it matches
  the detector/reconciler loop this repo already runs.)
- **Apply** materializes only what the plan says, preserving anything already present.
- **Re-running converges.** A second `adopt` on an already-adopted repo produces an empty
  plan and touches nothing.

**`genesis check`** — read-only, non-zero exit on drift. Runs in CI. This is the verb that
makes the model *stay* installed, and it is the one capability no comparable tool in the
field ships.

**`genesis update`** — the reason the whole thing is architected the way it is. The model
is versioned independently of the CLI; a repo records which model version it is at; an
update computes a plan, applies version-ordered migrations, and rewrites **only** the
regions Genesis owns.

That last point is the core design idea. Files split into four classes by *who owns them*:

| Class | Example | On update |
|---|---|---|
| **Referenced** | `bmad-method`, `copier`, `pixi` | version range only — nothing in the repo changes |
| **Copied (managed)** | `scripts/bmad-switch`, the drift detector | regenerated wholesale; hash-guarded against hand-edits |
| **Copied (seeded)** | a starter Dream, `.bmad-config.toml` | written once, repo-owned forever, never auto-touched |
| **Generated (derived)** | `.cursor/rules/specs.mdc`, `GEMINI.md`, `PROJECTS.md` rows | recomputed from the neutral contract + repo state |

And for the files that must be both — `AGENTS.md` and `CLAUDE.md` are narrative documents
a team writes in freely, *and* they carry the tier rules that must upgrade — a
**marker-delimited managed region**:

```markdown
<!-- genesis:begin managed-block=tiers model-version=1.4.0 -->
…generated; do not edit — run `genesis update`…
<!-- genesis:end managed-block=tiers -->
```

Only the span between markers is replaced. The file stays the team's. Deleting the markers
is a deliberate, greppable opt-out. Hand-editing inside them is detected by content hash
and reported by `genesis check`. This is the same two-zone discipline the repo already
runs on recipes, where agent-authored rationale parks in a bottom `# CFE comments` block
and human comments stay in the body.

**One hard structural guarantee:** the update path has no write access to Tier-0 or Tier-2
content. A repo's Dreams, PRDs, architectures, epics, and specs are unreachable from
`genesis update` by construction, not by convention. Upgrading the model can never touch
the work made with it.

## What Makes This Different

| Dimension | cookiecutter / Yeoman / degit | cruft (on cookiecutter) | Copier | projen | spec-kit | **Genesis** |
|---|---|---|---|---|---|---|
| What it installs | app source | app source | app source | build config | a way of working | **an operating model** |
| Update after install | ✗ none | ✓ commit-hash diff | ✓ tag-ordered smart merge | ✓ regenerate (files not editable) | ✓ `self upgrade` (tool only) | ✓ **plan → migrate → apply** |
| Versioned migrations | ✗ | ✗ | ✓ | n/a | ✗ | ✓ |
| Brownfield adopt verb | ✗ | ✓ `link` (state only) | partial | ✗ | ✓ documented loop | ✓ **detect → plan → apply, dry-run default** |
| Editable files that still upgrade | ✗ | skip-globs only | conflict markers | ✗ by design | override layer | ✓ **managed regions** |
| Conformance check in CI | ✗ | ✓ `check` | ✗ | ✗ | ✗ | ✓ **`genesis check`** |
| Agent entry-point fan-out | ✗ | ✗ | ✗ | ✗ | ✓ 30+ agents | ✓ generated from one contract |
| Air-gapped | varies | ✗ (git fetch) | ✗ (git fetch) | ✗ (npm) | ✗ (GitHub releases) | ✓ **templates in-package, conda-provisioned** |

Two of those columns are the whole thesis. **Conformance checking** — every surveyed tool
stops at "here are the files"; Backstage, the most institutional of them, does not address
post-scaffold updates at all. And **managed regions** — the field's two update models are
projen's regenerate-everything (perfect fidelity, files not editable) and Copier's
three-way merge (editable, but produces conflict markers in documents humans are actively
writing). Neither works for `AGENTS.md`. The hybrid does.

The third differentiator is not technical: **the model itself is the product.** Copier
ships an engine and you supply the template. Genesis ships a specific, battle-tested
operating model — 63 stories of production evidence across two shipped projects — with an
engine attached.

## Who This Serves

1. **The pyforge ecosystem, immediately.** Nine sibling projects (`herald`, `marshal`,
   `mason`, `doctor`, `scribe`, `steward`, `atlas`, `warden`, and the applications) plus
   `unity-data-stack` and `wasm-analytics-stack`. Several will graduate out of this
   monorepo into their own repositories; each needs the model installed correctly on day
   one rather than hand-copied and immediately stale.
2. **This repository, as the reference implementation.** `local-recipes` was the first
   brownfield adoption, done by hand. It becomes Genesis's regression oracle:
   `genesis adopt --dry-run` here must produce an **empty plan**. One mechanical test
   validates the entire model manifest — if Genesis's notion of the model disagrees with
   the repo the model was extracted from, the test fails.
3. **Teams adopting spec-driven, agent-run development.** The audience
   `HOW-WE-OPERATE.md` was written for — organizations that want documentation as
   programmable infrastructure and need a starting configuration rather than a blank page
   and a framework.
4. **Enterprise / air-gapped adopters.** A standing constraint in this repo and a real
   differentiator: with templates shipped in-package and the engine consumed as a conda
   package, `genesis init` runs with zero egress behind a firewall.

## Success Criteria

**Primary (the master switch).** A second repository is created by `genesis init`, runs a
full Dream → spec → epics → loop-driven build, and **takes a later model upgrade via
`genesis update` without hand-editing** — with `genesis check` green before and after.

**Supporting, all mechanically testable:**

- `genesis adopt --dry-run` against `local-recipes` at the shipped model version produces
  an **empty plan**. (The oracle.)
- `genesis adopt` is idempotent: second run ⇒ empty plan, zero files changed.
- `genesis adopt` on a repo with a hand-edited managed region **refuses and reports**
  rather than overwriting.
- `genesis adopt --apply` on a dirty git worktree refuses.
- `genesis init` + `genesis check` = green, offline, **zero network calls** (egress-counter
  test, the pattern warden already established).
- A simulated breaking model change (v1 → v2) is absorbed by a migration in an installed
  repo with no manual edits.
- `genesis update` cannot write to `docs/dreams/**` or `**/planning-artifacts/**` — proven
  by test, not by policy.
- Time to a working Dream-first repo: **under 5 minutes**, versus the ten-phase manual
  setup plan.

**Kill criteria.** Genesis pauses or rescopes if: the managed-region merge proves
unreliable on real files (conflicts or corruption in the first two adopters); the empty-plan
oracle against `local-recipes` cannot be reached without special-casing the model into
incoherence (meaning the model is not actually extractable and the Dream's stabilization
gate was called too early); or the model changes so fast that migrations cost more than
hand-editing each installed repo would.

## Technical Approach

**Wrap Copier, don't rebuild it.** Copier is on conda-forge at v9.17.0, `noarch: python`,
MIT, with a clean run-dependency set — consumed exactly as `pyforge-warden` consumes
`deptry` and `osv-scanner` from existing feedstocks (no new recipe, no runtime fetch). Its
public API is the surface Genesis needs: `run_copy` / `run_update` / `run_recopy`, with
`pretend` (dry-run), `skip_if_exists` (the brownfield primitive), `data` (programmatic
answers computed from inventory), `exclude`, `vcs_ref` (version pinning), and `conflict`.
Copier also brings the two most expensive pieces for free: the six-step update algorithm
and **migrations** — the only tool in the survey that has them. Genesis confines itself to
the three documented `run_*` functions; the internals are marked private upstream.

**Genesis builds four things Copier does not have:** the model content itself; the
brownfield inventory and plan; the managed-region post-pass; and `genesis check`.

**Packaging clones `pyforge-warden` exactly** — a pixi workspace member at
`src/shared/packages/pyforge-genesis/`, hatchling backend, `packages = ["src/pyforge"]`
namespace layout, `genesis = "pyforge.genesis.cli:main"` entry point, `pixi-build-python`,
and a lean environment with `no-default-feature = true` (required, not cosmetic: bmad-loop
worktrees materialize the lean env, never the fat `local-recipes` one). Root `pixi.toml`
gains a feature + environment via path dependency — there is no `[workspace] members` key
in pixi through 0.72.2.

**Templates ship inside the package**, spec-kit style, rather than being fetched from a
git-tagged repo (Copier's default). This is what makes air-gapped operation work, and
`--template <path|url>` covers development and forks. The trade-off is explicit: a model
change requires a package release.

**Two version numbers, both recorded in state:** the CLI version and the operating-model
semver. They move independently — the model is what installed repos track.

## Boundaries With the Crew

Genesis is a `crew`-owned Dream, and it sits close enough to two siblings that the lines
must be drawn in the PRD or the products will overlap:

- **Marshal** owns *operating* the multi-project machinery — `scripts/bmad-switch`,
  `scripts/bmad-loop-worktree`, concurrent loop homes, graduated autonomy — after the
  2026-07-23 ownership review, and already advertises `marshal init --spec …`. **Genesis
  installs that machinery; Marshal runs it.** Proposed rule: Genesis's write scope is a
  repo's *structure and conventions*; Marshal's is a repo's *executions*. `marshal init`
  initializes a build from a spec; `genesis init` initializes the repo the spec lives in.
- **Doctor** owns pre-flight toolchain verification. `genesis check` asks *"does this repo
  conform to the model?"*; `doctor check` asks *"is this machine able to run the factory?"*
  Genesis should verify referenced-dependency presence by delegating to Doctor where the
  surfaces overlap, rather than growing its own probe suite.
- **Herald** owns the deck family Genesis scaffolds; Genesis lays down the directory and
  conventions, Herald fills and round-trips them.

## Roadmap Thinking

- **V1** — `init`, `adopt`, `check`, `update`; the full model manifest; managed regions;
  migrations; in-package templates; the `local-recipes` empty-plan oracle; adapter fan-out
  for the four agents this repo already targets (Claude Code, Cursor, Copilot, Gemini).
- **V1.x** — feature modules (adopt a subset of the model: tiers only, or tiers + BMAD
  wiring); more agent adapters; `genesis check --fix` for mechanically-safe findings.
- **V2** — the model published as an independently versioned artifact for teams that fork
  it; conformance scorecards across a fleet of repos; a `genesis migrate` authoring flow so
  a model change *generates* its own migration.
- **Deliberately out of scope for V1** — hosted registry of installations, repo creation
  on a git host (`genesis init` makes a tree, not a GitHub repo), and non-git targets.

## Known Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Managed-region merge corrupts a file | pure span substitution (no three-way merge); hash guard; dry-run default; clean-worktree precondition so git is always the undo |
| R2 | The model is not actually extractable — too much of it is repo-specific | the empty-plan oracle surfaces this in V1, early; it is also the stated kill criterion |
| R3 | Model churn makes migrations a treadmill | model semver decoupled from CLI; only *managed* and *derived* classes ever migrate; seeded files never do |
| R4 | An upgrade damages a team's real work | structural guarantee: no write access to Tier-0/Tier-2 from the update path, enforced by test |
| R5 | Genesis and Marshal overlap and confuse users | boundary resolved explicitly in the PRD (§ Boundaries), before any code |
| R6 | Copier API drift | pin `>=9.17,<10`; public `run_*` only; version-range sync test (warden's established pattern) |
| R7 | Brownfield adopt breaks a working repo | dry-run default; `skip_if_exists`; `present-legacy` classification; refuses on dirty worktree |
| R8 | In-package templates couple model releases to package releases | accepted trade-off for air-gap; `--template` override for development and forks |

## Assumptions

1. Genesis targets **git repositories only** — every update mechanism in the field depends
   on git for diffing, undo, and version pinning.
2. The operating model is **semver'd and released independently** of the `pyforge-genesis`
   package version.
3. Installed repos run `genesis check` in **their own CI**; Genesis is not a service and
   keeps no central registry of installations.
4. First two adopters are **this repo** (oracle) and **one greenfield pyforge sibling**;
   external adoption is a later concern.
5. The model has genuinely stabilized — the Dream's own gate. Evidence: atlas and warden
   both shipped through it; the durable-story-specs convention closed the last known hole
   on 2026-07-25.
6. `pyforge.genesis` coexists with `pyforge.warden` / `pyforge.atlas` in the `pyforge`
   namespace under the shared hatch layout. Not yet built and verified.
7. This repo's existing `bmad-drift-check` seeds the shipped detector rather than a
   from-scratch build. **Not yet validated against the code.**
8. `genesis adopt` must be idempotent — implied by detect/plan/apply, not directly
   documented by any surveyed tool.

## Open Questions (for the PRD)

1. **The extraction manifest.** The Dream's central question. The research resolves the
   *rule* (classify by who owns the file and how it updates) and shows the Dream's
   three-way split is one class short — "copied" must divide into **managed** (tool-owned,
   updatable) and **seeded** (repo-owned after first write). The PRD must ratify the actual
   per-artifact manifest.
2. **Genesis ↔ Marshal boundary** — must be resolved explicitly (§ Boundaries proposes a
   rule; the PRD ratifies it).
3. **Does `genesis init` create a repository or only a tree?** (git init / remote / first
   commit, or not.)
4. **One model or composable feature modules?** Modularity is attractive; it multiplies the
   test matrix.
5. **CLI framework** — typer + rich (both already pinned; better for plan/diff/confirm UX)
   vs argparse (warden's lean-engine precedent). Note Copier already pulls in
   prompt-toolkit / questionary / pygments regardless.
6. **State file shape** — one Genesis-owned file, or Genesis state alongside Copier's
   `.copier-answers.yml` (which must never be hand-edited)?
7. **Marker syntax for non-markdown files** — `.gitignore`, `pixi.toml`, workflow YAML each
   have different comment syntax; a per-format marker registry may be needed.
8. **`genesis check` and `bmad-drift-check`** — reuse, extract, or re-implement?
9. **Legacy conventions as a first-class state** — is `present-legacy` recorded in the state
   file, and does the model define a deprecation path (e.g. `docs/specs/` → Tier 2)?
