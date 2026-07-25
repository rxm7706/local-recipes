---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - docs/dreams/pyforge-genesis.md
  - docs/dreams/ecosystem-crew.md
  - archive/docs/bmad-setup-plan.md
  - AGENTS.md
  - _bmad-output/PROJECTS.md
workflowType: 'research'
lastStep: 4
research_type: 'domain'
research_topic: 'Repository scaffolders and operating-model installers — update semantics, greenfield vs brownfield adoption, drift management'
research_goals: 'Ground the pyforge-genesis PRD in prior art; resolve the extraction question (copied / referenced / generated) and the update story'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
---

# Research Report: Domain — Repository Scaffolders & Operating-Model Installers

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Domain
**For:** `pyforge-genesis` (Genesis — `genesis init` / `genesis adopt`)

---

## Research Overview

**Question this research must answer.** Genesis packages *this repo's* proven operating
model (Dream-first tiers, AGENTS.md family, BMAD multi-project wiring, deck family,
durable story specs) as an installable tool with two verbs — `init` (greenfield) and
`adopt` (brownfield). The Dream names one unresolved decision: **the extraction
question** — what is **copied**, what is **referenced**, what is **generated**. That
decision is inseparable from a second one the Dream does not name but that every tool
in this domain has had to answer: **how does an installed repo take a later upgrade of
the model?** A file that is copied must be updatable; a file that is referenced updates
itself; a file that is generated is owned by the repo forever.

**Method.** Documentation-first review of the seven most relevant prior-art tools,
read from primary sources (project documentation and repositories) rather than
secondary commentary. Every claim below is attributed. Where a primary source did not
cover a question, that is recorded explicitly rather than inferred — see
*Open Questions*.

**Scope note.** This is a *domain* report: the shape of the problem space and the
solution patterns the field has converged on. Technology selection (CLI framework,
templating engine, packaging) is deferred to the companion technical research report.

**Constraint that shapes everything.** Genesis is not a code scaffolder. Almost all
prior art in this domain generates *application* source (a React app, a Python
library, a microservice). Genesis generates *governance* — conventions, tier layouts,
agent-entry files, planning-folder wiring. The artifacts are markdown, config, and
directory structure, and they are read by **agents** as much as by humans. That shifts
the weight of several trade-offs, most importantly toward update-ability: a scaffolded
React app is expected to diverge from its template immediately and forever; an
operating model that diverges silently is a *broken* operating model, because the
agents reading it will follow the stale copy.

---

## Part 1 — The Landscape: Seven Tools, Four Generations

The field has moved through four distinguishable generations. Each generation exists
because the previous one's update story failed.

### Generation 1 — One-shot template expansion

**Cookiecutter** and **Yeoman** define the baseline: prompt for variables, expand a
template directory through a templating engine (Jinja for Cookiecutter, EJS for
Yeoman), write files, exit. The relationship between the generated project and the
template ends at generation time. Copier's own comparison documents this as the
dividing line — updates are simply "not supported" in this generation, and Yeoman
additionally requires templates be distributed as NPM packages rather than plain git
repositories, adding a publication step Copier avoids
([Copier — Comparisons](https://copier.readthedocs.io/en/stable/comparisons/)).

**degit** sits at the extreme end of this generation: it is a straight
copy-the-repo-without-git-history tool, with no templating and no state at all. It is
included here only as the "zero-ceremony" boundary case — the minimum viable
scaffolder, useful as a comparison for how much ceremony Genesis is choosing to take
on.

**Why it fails for Genesis.** A one-shot install means every convention improvement
the model makes later — a new gotcha in the tier rules, a corrected AGENTS.md
portability clause, a new drift-check invocation — reaches only new repos. The
installed base freezes at its install date. Given that the pyforge model demonstrably
changes weekly (the Dream's own realization log shows three material revisions inside
a single day, 2026-07-23), Generation 1 is disqualified outright.

### Generation 2 — Retrofitted update via recorded state

**cruft** is the field's proof that the update problem is solvable *as a layer* on top
of a one-shot generator. It wraps Cookiecutter and adds a `.cruft.json` file recording
the template's **git commit hash** plus the variable values used. From that state it
derives four capabilities that Cookiecutter alone cannot offer
([cruft](https://github.com/cruft/cruft)):

| Command | Capability | Why it matters to Genesis |
|---|---|---|
| `cruft update` | applies template improvements to an existing project, presenting changes for review before applying | this is the core update verb Genesis needs |
| `cruft check` | returns a **non-zero exit code** when the project is behind the template — explicitly designed for CI | this is a *drift detector*, and Genesis already has the analogous concept in `bmad-drift-check` |
| `cruft diff` | shows the difference between the local project and the current template, git-diff style | the "what would change" preview |
| `cruft link` | **adopts an existing project** into template management by recording the template + commit hash retroactively | this is *literally* `genesis adopt` |

Two cruft details are directly load-bearing for the Genesis design:

1. **`cruft link` is the brownfield primitive.** The field has already established that
   "adopt an existing repo into a managed template relationship" is a distinct verb
   from "create a new repo," and that the *state file* is what makes it possible. This
   validates Genesis's two-verb structure and tells us `genesis adopt` must, at
   minimum, write the state file even when it writes nothing else.
2. **Skip lists are mandatory, not optional.** cruft supports a `skip` section (in
   `.cruft.json` or `pyproject.toml`, glob-capable) excluding paths from updates. The
   documented motivation is that the tool "cannot intelligently merge all changes." Any
   Genesis update mechanism will need the same escape hatch, and the choice of *what a
   repo may opt out of* is a governance decision, not a technical one.

### Generation 3 — Update as a first-class design goal

**Copier** is the most directly relevant prior art, because it was designed from the
start around the lifecycle rather than the birth event. Its documentation positions it
explicitly as "a code lifecycle management tool, not just a scaffolder"
([Copier — Comparisons](https://copier.readthedocs.io/en/stable/comparisons/)).

**The update algorithm** ([Copier — Updating](https://copier.readthedocs.io/en/stable/updating/))
is worth reproducing precisely, because it is the most sophisticated answer the field
has and Genesis should either adopt it or consciously reject it:

1. **Regenerate** a fresh project from the *current* template version, using the saved
   answers.
2. **Diff** that fresh project against the user's actual current project — this
   isolates the user's local modifications.
3. Run **pre-migration** hooks.
4. **Update** the project to the latest template (prompting for questions that are new
   since last time).
5. **Re-apply** the local-modification diff, so user work is not lost.
6. Run **post-migration** hooks.

Three preconditions gate this: a `.copier-answers.yml` answers file must exist; the
**template must be git-versioned with PEP 440-conformant tags** (so versions are
comparable and migrations can be ordered); and the **destination must be a git repo
with a clean working tree** (so the diff is meaningful and the operation is
revertible).

**Conflict semantics.** When the re-applied diff does not merge cleanly, Copier offers
`--conflict inline` (default — git-style conflict markers in the file) or
`--conflict rej` (a separate `.rej` file per unresolved hunk). The documentation notes
that **both** require pre-commit hooks to stop unresolved conflicts being committed —
an admission that the mechanism can leave a repo in a broken state that only process
discipline catches.

**Escape hatches and failure recovery.**
- Files **deleted locally are excluded from future updates** — deletion is a
  permanent opt-out signal, not something the tool fights.
- `copier recopy` abandons the smart algorithm entirely and regenerates from scratch,
  keeping the answers but leaving the user to reconcile via git.
- Aborting is `git reset` + `git checkout .` + `git clean` — i.e. **git is the undo
  mechanism**, which is why the clean-worktree precondition exists.

**The hard rule.** "**Never** update `.copier-answers.yml` manually" — manual edits
mislead the diff algorithm and produce unpredictable behavior. The state file is
tool-owned, and the tool says so loudly. This is a direct precedent for how Genesis
should treat whatever state file it writes.

**Migrations** are Copier-exclusive per its own comparison table: structured,
version-ordered transformations that run as part of an update. This is the mechanism
that turns "the model changed shape" from a breaking change into a scripted one — the
difference between "v2 renamed `docs/specs/` to legacy status" being a manual chore in
every installed repo versus a migration script that runs once.

### Generation 4 — Synthesis: the repo never owns the generated files

**projen** takes a genuinely different position. Rather than generating files once and
then trying to merge later template changes into whatever the user did to them, projen
makes configuration **code-first**: the user edits a `.projenrc.{ts,py,…}` file and
calls `project.synth()`, and projen (re)generates the config files from that program.
The documented rule is absolute: *"From this point forward, all changes to files
managed by projen will be made in the projen RC file"*
([projen — Getting Started](https://projen.io/docs/introduction/getting-started/)).

Customization does not happen by editing outputs; it happens through the API —
`project.eslint?.addRules()`, or dropping in `JsonFile` / `YamlFile` / `TextFile`
objects that layer additional generated content.

**Why this matters enormously for Genesis.** Synthesis *dissolves* the update problem
instead of solving it. There is no three-way merge because there is no divergence:
regenerate and the file is correct by construction. The cost is equally stark — the
generated files stop being editable, which is fine for `.eslintrc.json` and
categorically **not** fine for `AGENTS.md` or a repo's `CLAUDE.md`, which are
narrative documents a team must be able to write in freely.

This tension is the single most important finding in this report, and it points
directly at the answer to the extraction question (see Part 3).

**Note on evidence quality.** The projen Getting Started page does not state whether
generated files are committed to version control, nor how a project takes upgrades of
the projen library itself. Both are recorded as open questions rather than assumed.

### The two adjacent tools: workflow-shaped and platform-shaped

**GitHub spec-kit** is the closest thing in the field to "Genesis, but for
spec-driven development," and it is the single best comparable
([github/spec-kit](https://github.com/github/spec-kit)). What `specify init` installs
is not application code but *a way of working*:

- `.specify/` — templates, presets, extensions, and **memory**
- `.specify/templates/` — the core spec-driven-development commands and templates
- `.specify/presets/templates/` — customization **overrides** (note: a dedicated
  override layer, separate from the base templates)
- `.specify/extensions/templates/` — additional capability templates
- **agent-specific command folders** — e.g. `.claude/commands/` for Claude, generated
  per selected integration, across "30+ AI coding agents"
- a **constitution file** capturing project principles, plus specification, planning,
  and task templates

Four properties of spec-kit map one-to-one onto Genesis requirements:

1. **The agent-adapter fan-out is generated, not copied.** One model, N agent entry
   points, materialized per the integration the user picks
   (`specify integration list`). This is exactly the AGENTS.md-family problem: one
   portability contract, thin per-tool pointers for Claude Code / Cursor / Copilot /
   Gemini.
2. **A dedicated override layer exists in the layout.** `presets/templates/`
   overriding `templates/` is the same architectural move as this repo's six-layer
   BMAD config merge — and it exists precisely so that upgrading the base layer does
   not clobber local customization.
3. **Upgrade is a first-class, self-managed command set** —
   `specify self check` (is there a newer release?), `specify self upgrade --dry-run`,
   `specify self upgrade`, `specify self upgrade --tag vX.Y.Z` (pin an exact release),
   with auto-detection of whether the tool was installed via `uv tool` or `pipx`.
4. **Tooling upgrades are deliberately separated from artifact evolution.** The
   documented brownfield guidance is to "keep Spec Kit tooling updates separate from
   feature artifact evolution," and spec-kit names its two modes exactly as the
   Genesis Dream does — 0-to-1 "Greenfield" and iterative-enhancement "Brownfield,"
   with a distinct documented brownfield loop.

Point 4 is a significant finding: the field's most similar tool has concluded that
**the model's own files and the work products made with the model must upgrade on
separate tracks**. Genesis inherits that constraint directly — upgrading the tier
rules must never touch a repo's actual Dreams or planning artifacts.

**Backstage Software Templates** represent the platform-scale variant: a
`template.yaml` declaring `parameters` (user inputs), `steps`, and `actions`; the
template is registered in the software **catalog** and surfaced at a `/create` route;
execution runs built-in actions such as `fetch:template`, `publish:github`, and
`catalog:register`, ending with the new component registered back into the catalog
([Backstage — Software Templates](https://backstage.io/docs/features/software-templates/)).

Two takeaways. First, the **catalog/registry** pattern — the platform maintains a
central index of what exists and what it was made from — is the organizational
analogue of this repo's `_bmad-output/PROJECTS.md` index and its "no-straggler policy"
(every project, deck, Design project, and spec maps to exactly one Dream). Genesis
generating and maintaining that index is well-precedented. Second, and pointedly: the
Software Templates documentation **does not address whether already-scaffolded repos
receive later template updates**. The largest, most institutional tool in the survey
simply does not solve the update problem — its templates are a creation event, and
ongoing conformance is handled elsewhere in the platform (or not at all).

**Nx** contributes the fourth distinct pattern and, for Genesis, arguably the most
important one after synthesis. Nx separates two concerns that every other tool
conflates:

- **Generators** ([Nx — Generate Code](https://nx.dev/docs/features/generate-code))
  are the scaffolding half: TypeScript functions invoked as
  `nx g <plugin>:<generator> [options]`, which "scaffold new projects **or augment
  existing projects with new features**" and "ensure your code is consistent and
  follows best practices." Note the explicit both-modes framing — the same mechanism
  serves greenfield and brownfield. Organizations write their own generators to
  standardize project creation and enforce internal standards.
- **`nx migrate`** ([Nx — Automate Updating Dependencies](https://nx.dev/docs/features/automate-updating-dependencies))
  is the upgrade half, and it is a **deliberately two-phase** process:
  - *Phase 1:* `nx migrate` updates `package.json` versions and writes a
    **`migrations.json`** listing pending migrations. **No source changes yet** — the
    user reviews and adjusts versions first.
  - *Phase 2:* `nx migrate --run-migrations` applies them, updating configuration and
    source to match.

  Migrations come in two flavors: **generator-based** (programmatic edits, e.g.
  renaming a config property across a breaking change) and **prompt-based**
  (AI-assisted changes requiring judgment about the specific codebase). Nx collects
  pending migrations from *all installed plugins*, and the design explicitly allows
  "intervention between the phases."

The two-phase split is a governance insight, not just an ergonomic one: it creates a
**reviewable, committable plan artifact** (`migrations.json`) between "decide to
upgrade" and "the upgrade touches my files." For a tool whose entire subject matter is
governance, that is the right shape. It is also exactly congruent with this repo's
existing detector/reconciler loop (`bmad-drift-check` detects; BMAD skills reconcile)
and with `bmad-loop`'s gate model.

The mention of **prompt-based, AI-assisted migrations** is notable as the field's
current frontier: the acknowledgment that some upgrades cannot be scripted and need an
agent's judgment. Genesis operates in a repo where that capability is ambient.

---

## Part 2 — Cross-Cutting Findings

### F1 — The update mechanism determines the whole architecture

Every tool's structure is downstream of its update answer. One-shot tools need no
state file; cruft needs a commit hash; Copier needs answers + version tags + a clean
worktree + conflict markers + migrations; projen needs none of it because it
regenerates. **Genesis must pick its update model before its file layout**, not after
— which means this decision belongs in the PRD, not the architecture.

### F2 — Every serious tool writes a tool-owned state file, and forbids hand-editing it

`.copier-answers.yml`, `.cruft.json`, `.specify/`, `migrations.json`. The consistent
pattern: a machine-owned record of *what was installed, from what version, with what
answers, and what was opted out of*. Copier states the hand-editing prohibition
explicitly. Genesis needs this file, and it should be the *only* thing `genesis adopt`
is strictly required to write.

### F3 — Drift detection is a separate, cheaper capability than drift correction

cruft splits `check` (CI-friendly, exit-code) from `update` (mutating). Nx splits
`migrate` (plan) from `--run-migrations` (apply). This repo has already independently
converged on the same split — `bmad-drift-check` is a cheap deterministic detector and
the BMAD skills are the expensive correctness reconciler, a two-layer loop documented
in `CLAUDE.md` and `SYNC-RUNBOOK.md`. **Genesis should ship the detector as a
first-class verb**, and it can plausibly reuse this repo's detector design directly.

### F4 — The "generated vs. authored" line must be drawn *inside individual files*

The sharpest conflict in the survey: projen's regenerate-everything gives perfect
update fidelity but forbids editing; AGENTS.md and CLAUDE.md must be editable. Neither
whole-file mode works for Genesis on its own. The resolution the field points toward
is **managed regions** — projen manages whole files but composes them from layered
objects; spec-kit separates `templates/` from `presets/templates/` overrides; cruft
supports per-path skip globs. Genesis's version of this is likely a **marker-delimited
managed block** inside otherwise repo-owned files, plus whole-file management for
files that are purely mechanical.

### F5 — Greenfield and brownfield differ in *first step*, not in machinery

This repo's own origin document reached this conclusion independently and states it
crisply: the install is "project-type-agnostic"; the two tracks differ only in the
planning chain (brownfield starts with `bmad-document-project` to capture what must be
respected; greenfield starts with PRD + architecture to design from scratch) and in
whether `project-context.md` *preserves* or *establishes* conventions — "never the
loop mechanics" (`archive/docs/bmad-setup-plan.md`, § *Greenfield vs Brownfield*).
Nx's generators make the same claim ("scaffold new projects **or** augment existing
projects"), and spec-kit names both modes while sharing one toolchain. **`genesis
init` and `genesis adopt` should therefore be thin front-ends over one shared engine**,
differing in a preflight/inventory phase and in defaults — not two implementations.

### F6 — Brownfield safety is an inventory problem

`cruft link` adopts an existing project by recording state without touching files.
Copier's clean-worktree precondition and git-based undo exist so an update to a live
repo is always revertible. The Dream's own constraint — "layer the model onto an
existing repo **without disturbing what already runs**" — is the same requirement
stated as a product principle. The implication: `genesis adopt` needs a **detect →
plan → confirm → apply** sequence with a dry-run default, and it must be able to
recognize a convention that is *already present in a different form* (this repo, for
instance, already has `docs/specs/` as a legacy tier that must be preserved and marked
legacy, not deleted).

### F7 — Agent-entry-point fan-out is a solved, generated problem

spec-kit generates per-agent command folders for 30+ agents from one source of truth.
This is strong evidence that the AGENTS.md family (`CLAUDE.md`,
`.cursor/rules/specs.mdc`, `GEMINI.md`, `.github/copilot-instructions.md`) should be
**generated from the neutral `AGENTS.md` contract**, not copied as N independent
files — and that which adapters get materialized should be a user choice at install
time, extensible later.

### F8 — Versioning the model is a precondition for updating it

Copier requires **PEP 440 git tags on the template**; cruft pins a **commit hash**;
spec-kit pins a **release tag** (`--tag vX.Y.Z`); Nx orders migrations by package
version. There is no update story without a versioned model. Genesis therefore needs
an explicit, semver'd **operating-model version** distinct from the `pyforge-genesis`
package version — the model is the thing installed repos track, and it must be able to
evolve at a different rate than the CLI that installs it.

### F9 — Nobody in the survey solves conformance *enforcement*

Every tool stops at "here are the files." Ongoing conformance — does the repo still
follow the model? — is left to CI, review, or nothing at all (Backstage's silence on
updates is the clearest case). This repo has already built the missing piece for
itself (`bmad-drift-check` with HARD findings such as `tracked-impl-artifact`, wired
into the test suite). **That detector is a genuine differentiator, and it is a
"copied-then-updated" asset, not a referenced one** — an installed repo needs it to
run locally, offline, in its own CI.

### F10 — Templating engines are table stakes; the differentiator is lifecycle

Copier and Cookiecutter both use Jinja; Yeoman uses EJS; all support hooks/tasks and
templated filenames ([Copier — Comparisons](https://copier.readthedocs.io/en/stable/comparisons/)).
Copier's claimed exclusives are updates, migrations, and loop-based file generation;
its usability claim is a single YAML config against Cookiecutter's hand-written JSON
and Yeoman's JavaScript programming. Conclusion: **do not differentiate on
templating** — it is commodity. Differentiate on the lifecycle and on the model itself.

---

## Part 3 — Implications for the Extraction Question

The Dream asks: what is copied, what is referenced, what is generated? The survey
supplies a decision rule rather than a list, and the rule follows from F1 and F4:

> **Classify each artifact by who must be able to change it, and how the repo takes
> a later model upgrade for it.**

| Class | Definition | Update mechanism | Prior art |
|---|---|---|---|
| **Referenced** | The repo depends on it by version; it lives outside the repo | dependency bump — nothing in the repo changes | bmad-method releases; Nx plugin versions |
| **Copied (managed)** | Materialized into the repo but tool-owned; the repo should not hand-edit it | regenerate on update; drift-check flags edits | projen's synthesized files; spec-kit `templates/` |
| **Copied (seeded)** | Materialized once as a starting point, then repo-owned forever | never auto-updated; migrations may offer opt-in edits | Copier's locally-deleted-path rule; cruft `skip` |
| **Generated (derived)** | Computed from repo state or from another artifact | recomputed on demand; never hand-edited | spec-kit agent adapters; Backstage catalog registration |
| **Hybrid (managed region)** | A repo-owned file containing a tool-owned block | only the marked region is regenerated | spec-kit `presets/` overrides; projen file-layering |

The three-way split in the Dream is therefore **too coarse in one place**: "copied"
must split into *managed* (updatable, tool-owned) and *seeded* (one-shot, repo-owned),
because that distinction is precisely what decides whether a later model upgrade is
allowed to rewrite the file. Everything else in the survey follows once that line is
drawn.

**Applying the rule to the known model surface** (illustrative — the PRD must ratify
the manifest):

- The **tier rules and portability contract** in `AGENTS.md` are the model's core and
  change with the model → *hybrid managed region* inside a repo-owned file.
- The **per-tool pointer files** (`CLAUDE.md` head matter, `.cursor/rules/specs.mdc`,
  `GEMINI.md`, `.github/copilot-instructions.md`) are mechanical projections of that
  contract → *generated/derived* (F7).
- **bmad-method itself, and any pinned external tool** → *referenced* (F8's corollary:
  never vendor what upstream versions well).
- The **drift detector** must run locally and offline in the adopting repo's CI →
  *copied, managed* (F9).
- **`docs/dreams/README.md`, the Dream frontmatter convention, the PROJECTS.md
  registration procedure** → *copied, managed*, since they are the model's own rules.
- **A repo's actual Dreams, PRDs, epics, `project-context.md`** → *generated once, then
  repo-owned forever* — and per spec-kit's point 4 these must upgrade on a **separate
  track** from the model, i.e. a model upgrade must be structurally incapable of
  touching them.
- **`scripts/bmad-switch` and `scripts/bmad-loop-worktree`** are executable model
  machinery with known sharp edges (the marker/symlink desync incident recorded in
  `CLAUDE.md` and in the script's own docstring) → *copied, managed*, because bug
  fixes must propagate to installed repos.

---

## Part 4 — Risks Surfaced by the Prior Art

| # | Risk | Evidence from the survey | Mitigation the field uses |
|---|---|---|---|
| R1 | Update leaves the repo in a broken, half-merged state | Copier's conflict markers "require pre-commit hooks" to avoid committing conflicts | dry-run default; clean-worktree precondition; git-based undo; a `check` verb that runs before `update` |
| R2 | The tool cannot merge some changes at all | cruft ships `skip` globs precisely for this | per-path opt-out recorded in the state file; deletion treated as permanent opt-out (Copier) |
| R3 | Managed files get hand-edited and silently diverge | Copier's explicit "never edit the answers file"; projen's "all changes go in the RC file" | loud in-file markers; drift detector flags edited managed regions |
| R4 | Model upgrade clobbers the team's actual work products | spec-kit: keep tooling updates separate from feature-artifact evolution | structural separation — the update path must not have write access to Tier-0/Tier-2 content |
| R5 | Breaking model changes strand the installed base | Copier migrations; Nx `migrations.json` | versioned model + ordered migration scripts, planned in phase 1 and applied in phase 2 |
| R6 | Brownfield adoption breaks a working repo | the Dream's own "without disturbing what already runs"; `cruft link` writes state only | inventory/detect phase; adopt defaults to writing state + a plan, applying nothing without confirmation |
| R7 | Nobody knows what's installed where | Backstage's catalog; this repo's PROJECTS.md no-straggler policy | the state file makes each repo self-describing; `check` is CI-runnable |
| R8 | The installer's own version and the model's version get conflated | Copier: template tags ≠ Copier version; spec-kit: `self upgrade --tag` pins the *tool* | two independent version numbers, both recorded in the state file |

---

## Assumptions

1. **A1** — Genesis targets git repositories exclusively. Every update mechanism in the
   survey (Copier, cruft, Nx, spec-kit) assumes git for diffing, undo, and version
   pinning; a non-git target would forfeit the entire update story.
2. **A2** — The operating model is versioned with semver and released independently of
   the `pyforge-genesis` package version (F8, R8).
3. **A3** — Installed repos are expected to run the drift detector in their own CI;
   Genesis is not a hosted service and has no central registry of installations
   (Backstage's catalog model is out of scope).
4. **A4** — The first two adopters are this repo (already hand-adopted — the model's
   reference implementation and regression oracle) and one greenfield pyforge sibling;
   external/public adoption is a later concern.
5. **A5** — Because Genesis installs *agent-facing* governance, "correctness" of an
   install is verifiable by machine (files present, markers intact, detector green) far
   more than by human taste — so acceptance criteria can be mechanical.
6. **A6** — This repo's existing `bmad-drift-check` is the seed of the shipped detector
   rather than a from-scratch build. Not yet validated against the code.
7. **A7** — `genesis adopt` must be **idempotent** — re-running on an already-adopted
   repo converges rather than duplicating. Implied by the detect/plan/apply pattern
   (F6) but not directly documented by any surveyed tool.

---

## Open Questions

1. **OQ1** — Does projen commit its synthesized files to version control, and how does
   a projen project take an upgrade of the projen library itself? The Getting Started
   page does not say. This matters because projen is the strongest candidate model for
   the *managed* class, and its real-world upgrade ergonomics are unverified here.
2. **OQ2** — Does Backstage have *any* mechanism for propagating template changes to
   already-scaffolded repos (outside the Scaffolder docs — e.g. Tech Insights /
   scorecards)? The surveyed page is silent. If a conformance-scoring pattern exists
   there, it is directly relevant to F9.
3. **OQ3** — What exactly is in spec-kit's `.specify/memory/`, and does the brownfield
   loop mutate it on upgrade? This is the closest analogue to team memory / project
   context and would inform the separate-tracks rule (R4).
4. **OQ4** — Nx's `--from` / `--to` and `--interactive` flags were not covered by the
   fetched page; the precise ergonomics of partial and pinned migrations are unverified.
5. **OQ5** — **Product decision, not researchable:** does Genesis adopt Copier's
   three-way-merge model, projen's regenerate model, or a managed-region hybrid (F4)?
   The survey argues for the hybrid but the cost is a bespoke merge engine.
6. **OQ6** — **Product decision:** does Genesis *wrap* an existing engine (Copier is
   Python, library-API-capable, and already implements updates + migrations) or
   implement its own? Wrapping inherits a battle-tested update algorithm and its
   preconditions; implementing gives control over managed-region semantics that Copier
   does not natively offer. This is the single highest-leverage architecture question
   and mirrors the wrap-vs-build decisions already resolved in the `pyforge-mason` and
   `pyforge-marshal` PRDs.
7. **OQ7** — Should the model be distributed *inside* the `pyforge-genesis` package, or
   as a separate versioned artifact (a git-tagged template repo) the CLI fetches? Copier
   and cruft assume the latter; spec-kit ships templates inside its releases. Affects
   air-gapped operation, which is a standing constraint in this repo.
8. **OQ8** — How does Genesis behave in a repo that has *drifted from* or *deliberately
   forked* the model (this repo's `docs/specs/` legacy tier is a live example)? Is
   "legacy, preserved, marked" a first-class state in the state file?

---

## Sources

- [Copier — Updating a project](https://copier.readthedocs.io/en/stable/updating/)
- [Copier — Comparisons](https://copier.readthedocs.io/en/stable/comparisons/)
- [cruft — GitHub repository](https://github.com/cruft/cruft)
- [projen — Getting Started](https://projen.io/docs/introduction/getting-started/)
- [github/spec-kit — GitHub repository](https://github.com/github/spec-kit)
- [Nx — Generate Code](https://nx.dev/docs/features/generate-code)
- [Nx — Automate Updating Dependencies (`nx migrate`)](https://nx.dev/docs/features/automate-updating-dependencies)
- [Backstage — Software Templates](https://backstage.io/docs/features/software-templates/)

**In-repo primary sources** (the model being extracted):
`docs/dreams/pyforge-genesis.md` · `docs/dreams/ecosystem-crew.md` ·
`docs/dreams/README.md` · `AGENTS.md` · `CLAUDE.md` · `_bmad-output/PROJECTS.md` ·
`archive/docs/bmad-setup-plan.md` · `scripts/bmad-switch` ·
`docs/intake/gists/how-we-operate/HOW-WE-OPERATE.md`
