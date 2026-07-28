---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/projects/pyforge-genesis/planning-artifacts/research/domain-research-scaffolder-landscape.md
  - src/shared/packages/pyforge-warden/pyproject.toml
  - src/shared/packages/pyforge-warden/pixi.toml
  - pixi.toml
  - docs/reference/library-llms-full.md
workflowType: 'research'
lastStep: 4
research_type: 'technical'
research_topic: 'Genesis installer implementation — engine selection, managed-region merge, pixi workspace packaging, idempotent adopt, state file, migrations, offline operation'
research_goals: 'Pick the engine (wrap vs build), fix the packaging shape, and de-risk the update/merge mechanics before architecture'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
---

# Research Report: Technical — Implementing the Genesis Installer

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Technical
**For:** `pyforge-genesis` — dist `pyforge-genesis` / module `pyforge.genesis` / CLI `genesis`
**Companion:** `research/domain-research-scaffolder-landscape.md` (read that first — it
establishes the copied/referenced/generated taxonomy this report implements)

---

## Research Overview

The domain report established *what* the field does. This report answers *how Genesis
should build it*, against six technical questions:

1. **Engine** — wrap Copier, wrap cookiecutter+cruft, or build bespoke?
2. **Merge strategy** — how does a later model version update a file the repo has
   edited, given the domain report's finding (F4) that neither whole-file
   regeneration nor free-form three-way merge works alone?
3. **Packaging** — the exact shape of a `pyforge-genesis` pixi workspace member.
4. **Idempotent brownfield apply** — how `genesis adopt` converges rather than
   duplicates.
5. **State file** — the schema of the tool-owned record.
6. **Offline / air-gapped operation** — a standing constraint in this repo.

Primary sources are Copier's API reference plus **in-repo ground truth**: this repo
already ships a working pyforge package (`pyforge-warden`) whose packaging is the
template to copy, and its library catalog already pins the relevant scaffolding
libraries. Where a fact came from the live repo it is cited by path.

---

## Part 1 — Engine Selection: Wrap Copier

### The finding that decides it

**Copier is already available as a conda-forge package.** Verified live against the
feedstock: `conda-forge/copier-feedstock`, **v9.17.0**, `recipe.yaml` (v1 schema),
**`noarch: python`**, **MIT** licensed, with a clean run-dependency set
(jinja2, pydantic, pyyaml, questionary, plumbum, pathspec, packaging, platformdirs,
funcy, dunamai, colorama, pygments, prompt-toolkit, jinja2-ansible-filters,
eval-type-backport, typing_extensions).

This is decisive for three independent reasons:

1. **No new recipe.** Genesis can take Copier as a conda run-dependency exactly the way
   `pyforge-warden` takes `deptry` and `osv-scanner` from existing feedstocks — the
   pattern is already documented in `src/shared/packages/pyforge-warden/pixi.toml`:
   *"Runtime engines are provisioned as conda packages (NFR1/NFR2) — never curl-fetched
   at runtime."* This satisfies the CFE consume-not-submit precedent (G58) with zero
   packaging work.
2. **`noarch: python` + MIT** means no platform matrix problem and no license friction.
3. **Air-gap compatible by construction** — a conda package resolves from an internal
   mirror; there is no runtime network fetch of the engine itself.

### Copier's public API is exactly the surface Genesis needs

Per [Copier — API reference](https://copier.readthedocs.io/en/stable/reference/api/),
three public functions, each returning a `Worker`:

| Function | Purpose | Genesis verb |
|---|---|---|
| `run_copy()` | "Copy a template to a destination, from zero." | `genesis init` |
| `run_update()` | "Update a subproject, from its template." — merges template changes while preserving local modifications | `genesis update` |
| `run_recopy()` | "Update a subproject from its template, **discarding subproject evolution**." | `genesis update --force` / repair path |

Parameters that map straight onto Genesis requirements:

- `src_path`, `dst_path` — template source and target repo.
- `data` (dict) — **programmatic answers**, so Genesis can compute answers from a
  brownfield inventory instead of prompting. This is the mechanism that makes
  `genesis adopt` non-interactive-capable.
- `defaults` (bool) — non-interactive runs; required for `bmad-loop`/CI use.
- **`pretend` (bool) — simulation mode without applying changes.** This *is* the
  dry-run requirement (domain R1/R6) and it comes free.
- `exclude` (sequence of patterns) — skip patterns; the per-path opt-out of domain R2.
- `skip_if_exists` — **preserve files that are already present**. This is the single
  most important brownfield primitive: it is how `genesis adopt` layers the model onto
  a repo "without disturbing what already runs."
- `overwrite` (bool) — replace existing files, for the managed class.
- `vcs_ref` — pin the template version; the model-version pin of domain F8/A2.
- `conflict` — `'inline'` (git-style markers) or `'rej'` (`.rej` files), update only.
- `unsafe` (bool) — gate on template features that execute code (tasks/migrations).
- `quiet` (bool) — machine-readable runs.

**Stability caveat (record it):** the API docs mark several internal modules
"Deprecated: module is intended for internal use only," which implies the three `run_*`
functions are the stable surface and the `Worker` internals are not. **Genesis must
confine itself to `run_copy` / `run_update` / `run_recopy` plus the documented kwargs,
and must not reach into `Worker` attributes.** Pin Copier with a compatible range
(`>=9.17,<10`), mirroring the range-not-exact engine-pinning convention warden already
uses and enforces with a sync test
(`tests/meta/test_engine_version_range_sync.py`).

### What Copier gives Genesis for free

Everything the domain report identified as expensive: the six-step update algorithm
(regenerate → diff → pre-migrate → update → re-apply diff → post-migrate), the answers
file, PEP 440 version ordering, conflict markers, and **migrations** — which Copier's
own comparison lists as an exclusive capability
([Copier — Comparisons](https://copier.readthedocs.io/en/stable/comparisons/)).
Rebuilding these is a multi-month effort with a long tail of merge bugs.

### Why not cookiecutter + cruft

Both **are already in this repo's pixi environment** — `cookiecutter >=2.7.1` and
`cruft >=2.16.0`, and the library catalog's decision table currently says
*"Scaffold a project → cookiecutter (+ cruft to stay synced)"*
(`docs/reference/library-llms-full.md`). That makes them the incumbent, so the case
against them must be explicit:

- cruft's update is **commit-hash-based**, not version-tag-based — no semver ordering,
  therefore **no migrations**, therefore no scripted answer to a breaking model change
  (domain R5). Genesis's whole reason to exist is a model that evolves.
- Cookiecutter has no answers-file concept of its own; cruft bolts one on. Copier
  treats the lifecycle as the primary design goal.
- Copier's `skip_if_exists` + `pretend` + programmatic `data` are exactly the
  brownfield triad; cruft's `link` records state but has no equivalent layered-apply.

**Recommendation:** wrap Copier; update `docs/reference/library-llms-full.md`'s
scaffolding section and decision table when Genesis lands (that file has a drift
detector, `pixi run -e local-recipes llms-full-check`, which will flag the pixi.toml
change — so the catalog edit is a required, not optional, part of the story).

### What Genesis still has to build

Copier is a *file-materialization* engine. It does not know about:

- **Managed regions inside repo-owned files** (Part 2) — Copier's unit is a file.
- **Brownfield inventory** — detecting a convention already present in a different form
  (this repo's `docs/specs/` legacy tier), and computing `data`/`exclude` from it.
- **Conformance checking** — the `genesis check` verb (domain F3/F9), which is
  read-only and must run in CI. Copier has no `check`.
- **The model content itself** — the templates, the tier rules, the AGENTS.md family,
  the adapter fan-out.
- **The two-phase plan/apply split** (domain: Nx `migrations.json`), which is a Genesis
  layer above Copier's single-shot update.

---

## Part 2 — Merge Strategy: Managed Regions

### The problem restated

Domain F4: `AGENTS.md` and `CLAUDE.md` must be **freely editable by the team** and yet
**carry model content that must upgrade**. Whole-file regeneration (projen) forbids the
first; free-form three-way merge (Copier's default) makes the second unreliable — every
model upgrade would produce conflict markers in a document humans are actively writing.

### The mechanism

A **marker-delimited managed block** inside a repo-owned file:

```markdown
<!-- genesis:begin managed-block=tiers model-version=1.4.0 -->
…generated content — do not edit; run `genesis update` …
<!-- genesis:end managed-block=tiers -->
```

Properties this buys, mapped to the domain risks:

| Property | Addresses |
|---|---|
| The file is repo-owned; only the block is tool-owned | F4 — resolves the projen-vs-editable tension |
| Update = replace block content between markers; a pure text-span substitution, no three-way merge | R1 — cannot produce a half-merged file |
| `model-version` stamped in the marker | F8/R8 — each block self-reports its version |
| Content-hash the block; a mismatch means someone hand-edited it | R3 — the drift detector has a precise, cheap signal |
| Missing markers ⇒ block absent ⇒ `genesis check` reports it, `genesis update` re-inserts at an anchor | R6 — brownfield repos that never had the block converge |
| Deleting the markers is a deliberate, greppable opt-out | R2 — mirrors Copier's "locally deleted paths are excluded from future updates" |

### The four-class file taxonomy in implementation terms

| Class | Copier mechanism | Genesis behavior on `update` |
|---|---|---|
| **Referenced** | not materialized at all | dependency range in `pixi.toml` / `pyproject.toml`; nothing to update |
| **Copied (managed)** — whole file | `overwrite=True`, file listed in the manifest as managed | overwritten wholesale; hash-checked by `check` first, refuses if hand-edited without `--force` |
| **Copied (seeded)** — one-shot | `skip_if_exists` | never touched again; migrations may *offer* an edit, never impose one |
| **Generated (derived)** | rendered from repo state, not from a template diff | recomputed every run; idempotent by construction |
| **Hybrid (managed region)** | Genesis-owned post-pass over a `skip_if_exists` file | only the marked span is replaced |

The hybrid class is the one Copier does not natively serve, so it is Genesis's own
code: a small, well-tested marker parser + span replacer. Scoping note — **this is the
riskiest bespoke component and should be an early, independently testable story.**

### Precedent inside this repo

The managed-region idea is not novel here. `recipes/**` already runs a two-zone
convention — human/upstream comments stay in the body, agent-authored rationale parks
in a bottom `# CFE comments` block, and `extra.cfe-*` metadata is stripped before push
(auto-memory: *CFE/AI comments go at the bottom* and *extra: cfe-\* is local-internal
metadata*). Same shape: a machine-owned region inside a human-owned file, with a
mechanical rule for what happens to it at a boundary.

---

## Part 3 — Packaging: A Pixi Workspace Member

`pyforge-warden` is the working, shipped exemplar and Genesis should clone its shape
exactly. Verified from the live files:

### Layout

```
src/shared/packages/pyforge-genesis/
├── pixi.toml          # [package] — MEMBER, deliberately NO [workspace] table
├── pyproject.toml     # hatchling build backend
├── README.md
├── src/pyforge/genesis/…
└── tests/
```

### `pyproject.toml` (pattern from `src/shared/packages/pyforge-warden/pyproject.toml`)

- `build-backend = "hatchling.build"`, `requires = ["hatchling"]`
- `[project] name = "pyforge-genesis"`, `requires-python = ">=3.12"`, MIT
- `[project.scripts] genesis = "pyforge.genesis.cli:main"` — mirrors warden's
  `warden = "pyforge.warden.cli:main"`
- `[tool.hatch.build.targets.wheel] packages = ["src/pyforge"]` — the namespace-package
  layout that lets `pyforge.warden` and `pyforge.genesis` coexist

### `pixi.toml` (pattern from `src/shared/packages/pyforge-warden/pixi.toml`)

- `[package] name/version`; **no `[workspace]` table** — the root `pixi.toml` owns
  workspace config and pulls the member in via a path dependency.
- `[package.build.backend] name = "pixi-build-python", version = "0.*"`
- `[package.host-dependencies]`: `python >=3.12`, `hatchling`
- `[package.run-dependencies]`: `python >=3.12`, **`copier >=9.17,<10`**, plus
  `jinja2`, `pyyaml`, and the CLI layer.

### Root `pixi.toml` wiring

Follows the warden precedent verbatim:

```toml
[feature.pyforge-genesis.dependencies]
pyforge-genesis = { path = "src/shared/packages/pyforge-genesis" }
hatchling = ">=1.31.0"
python-build = ">=1.5.0"
pytest = ">=9.1.1"

[feature.pyforge-genesis.tasks.pyforge-genesis-test]
cmd = "pytest src/shared/packages/pyforge-genesis/tests -q"

[environments]
pyforge-genesis = { features = ["pyforge-genesis"], no-default-feature = true }
```

`no-default-feature = true` is load-bearing and already justified in-repo twice: warden
uses it for a lean standalone-tool env, and atlas's comment states that **loop worktrees
materialize the lean env, never the fat `local-recipes` env — "the worktree-affordability
claim."** Since Genesis will be developed via `bmad-loop`, the lean env is required, not
cosmetic.

The workspace also already carries `preview = ["pixi-build"]` and
`requires-pixi = ">=0.72.2"` at the root, so no workspace-level change is needed beyond
adding the feature/environment.

**Known trap to carry into architecture:** the root `pixi.toml` note that pixi
"(through 0.72.2) has no `[workspace] members` key — workspace members are declared via
path dependencies." A Gemini PR review previously suggested otherwise and was wrong;
don't relitigate it.

**Repo-rule consequence:** touching `pixi.toml` triggers two always-on PR gates —
regenerate `environment.yaml` (`pixi project export conda-environment -e build >
environment.yaml`, ungated by the `maintenance` label) and add the `maintenance` label
for any change outside `recipes/` (`CLAUDE.md` § *Critical Rule — PR CI gates*). Also
`llms-full-check` will flag the catalog. These are story-level acceptance criteria, not
afterthoughts.

### CLI framework

`typer >=0.27.0` + `rich >=14.3.4` are already pinned in the repo and the catalog's own
decision table says *"Build a CLI → typer + rich"*
(`docs/reference/library-llms-full.md`). Counter-consideration: warden deliberately uses
**argparse** for a lean, dependency-minimal engine. For Genesis the plan/diff/confirm UX
(domain F3, Nx two-phase) argues for typer+rich; the counter-argument is that Copier
already pulls in `questionary`, `prompt-toolkit`, `pygments`, and `colorama`, so rich
terminal capability partly arrives regardless. **Recorded as an architecture decision,
not resolved here** (OQ-T1).

---

## Part 4 — Idempotent Brownfield Apply

`genesis adopt` must converge on re-run (domain A7). The mechanics:

1. **Inventory (read-only).** Walk the target repo and classify each model artifact:
   `absent` / `present-conformant` / `present-divergent` / `present-legacy`. The
   `present-legacy` state is required — this repo's own `docs/specs/` must be
   *preserved and marked legacy*, never deleted (domain OQ8).
2. **Plan.** Emit a machine-readable plan listing, per artifact, the class, the current
   state, and the proposed action. This is the Nx `migrations.json` analogue and it is
   what makes the operation reviewable before it touches anything.
3. **Confirm.** Default to **dry-run**; `--apply` (or `--yes` for CI) to execute.
   Copier's `pretend=True` implements the dry half directly.
4. **Apply.** `run_copy` with `skip_if_exists` for the seeded class, `overwrite` for the
   managed class, then the Genesis post-pass for managed regions, then write state.

**Idempotence properties to test explicitly** (these become acceptance criteria):

- `adopt` twice ⇒ second run's plan is empty and the git worktree is unchanged.
- `adopt` on a repo where a managed region already exists at the current model version
  ⇒ no write.
- `adopt` on a repo with a hand-edited managed region ⇒ **refuses** and reports, rather
  than silently overwriting (domain R3).
- `adopt --apply` on a dirty worktree ⇒ refuses (Copier's own clean-worktree
  precondition; git is the undo mechanism).

**The regression oracle is free and unusually strong:** this repo *is* the reference
brownfield adoption. `genesis adopt --dry-run` run against `local-recipes` at the
current model version must produce an **empty plan**. That is a single, mechanical,
high-signal test for the entire model manifest — if Genesis's notion of the model
disagrees with the repo the model was extracted from, the plan is non-empty and the
test fails.

---

## Part 5 — State File Design

Domain F2: every serious tool writes a tool-owned state file and forbids hand-editing.
Genesis needs one; Copier will also write `.copier-answers.yml`, so the relationship
between the two must be explicit.

**Recommendation:** one Genesis-owned file (e.g. `.genesis/state.yml` or
`.genesis.yml`), with the Copier answers file either nested under `.genesis/` (Copier's
answers-file path is template-configurable) or accepted as a second tool-owned file
that Genesis never hand-edits. **Do not duplicate Copier's answers into Genesis state** —
Copier's documentation is emphatic that manual edits to the answers file mislead the
diff algorithm ([Copier — Updating](https://copier.readthedocs.io/en/stable/updating/)).

Fields the domain findings require:

| Field | Why | Source finding |
|---|---|---|
| `model_version` | the operating-model semver the repo is at | F8, A2 |
| `genesis_version` | the CLI version that last wrote state — **independent** of the above | R8 |
| `adopted_at` / `last_update` | audit trail | — |
| `mode` | `init` \| `adopt` | F5 |
| `agents[]` | which adapter entry points were materialized | F7 |
| `managed[]` | per-artifact: path, class, content hash of the managed span | R3, F4 |
| `skips[]` | per-path opt-outs (glob-capable) | R2 |
| `legacy[]` | conventions preserved in a pre-model form | OQ8 |
| `migrations_applied[]` | ordered record, so migrations run exactly once | R5 |

The file must carry a loud do-not-edit header, and `genesis check` must validate it
against a schema — the same discipline `pyforge-warden` applies to its
`ComplianceReport` (`jsonschema` is already a proven in-repo dependency for exactly
this).

---

## Part 6 — Migrations

Copier supplies the primitive (version-ordered pre/post migration hooks tied to PEP 440
template tags). Genesis supplies the policy:

- **Ordered by `model_version`,** applied exactly once, recorded in state.
- **Two-phase like Nx** ([Nx — automate updating dependencies](https://nx.dev/docs/features/automate-updating-dependencies)):
  `genesis update` writes a plan; `genesis update --run` applies it. The reviewable
  artifact between the phases is the point.
- **Migrations may never write into Tier-0 or Tier-2 content.** This is the hard
  structural expression of spec-kit's "keep tooling updates separate from feature
  artifact evolution" (domain R4). A repo's Dreams, PRDs, epics, and specs are
  off-limits to the update path by construction, not by convention — worth an explicit
  guard and a test.
- **`unsafe`** must be an explicit opt-in flag, since Copier gates code-executing
  template features behind it.

---

## Part 7 — Offline / Air-Gapped Operation

A standing repo constraint (`docs/dreams/enterprise-airgap.md` is `realized`; warden's
pixi.toml states engines are "never curl-fetched at runtime"). Consequences:

1. **The engine is a conda dependency** — Copier resolves from conda-forge or an
   internal mirror. Already satisfied (Part 1).
2. **The model content must be resolvable without network.** This is domain OQ7 and it
   now has a clear technical resolution: **ship the model templates inside the
   `pyforge-genesis` package** (spec-kit's approach) rather than fetching a git-tagged
   template repo at runtime (Copier's and cruft's default). Shipping in-package means
   `model_version` is pinned by the package version's dependency range and the whole
   install works from a conda mirror with zero egress.
   - Trade-off to record: in-package templates mean **a model change requires a package
     release**. Mitigate by allowing `--template <path|url>` as an override for
     development and for teams that fork the model.
   - Copier's `src_path` accepts a local path, so both modes are the same code path.
3. **`bmad-method` is `referenced`, not vendored** — it is already pixi-provisioned from
   conda-forge in this repo (v6.10.0+, with Node.js as a conda dependency, "no separate
   Node install or live npm registry required" per `archive/docs/bmad-setup-plan.md`
   Phase 0.1). Genesis declares a version floor and verifies presence; it does not
   install BMAD itself.
4. **Egress budget test.** Warden set the precedent with an egress-counter proof in its
   slow suite. Genesis should assert **zero network calls** on `init` and `adopt` with
   in-package templates.

---

## Part 8 — Recommended Technical Stance (input to architecture)

| # | Decision | Recommendation | Confidence |
|---|---|---|---|
| T1 | Engine | **Wrap Copier** (`>=9.17,<10`), conda run-dependency, public `run_*` API only | High — conda-forge availability verified live |
| T2 | Merge for editable files | **Marker-delimited managed regions**, Genesis-owned post-pass | High — only option satisfying F4 |
| T3 | Merge for mechanical files | Copier `overwrite`, hash-guarded | High |
| T4 | Brownfield preservation | Copier `skip_if_exists` + inventory-computed `exclude` | High |
| T5 | Dry-run | Copier `pretend=True`, **default on** for `adopt`/`update` | High |
| T6 | Packaging | pixi workspace member cloning `pyforge-warden`'s shape; lean env, `no-default-feature` | High — in-repo exemplar |
| T7 | Model distribution | **In-package templates** + `--template` override | Medium — resolves OQ7 for air-gap; cost is release-coupling |
| T8 | Two-phase update | plan artifact, then `--run` | High — Nx precedent + repo's existing detector/reconciler split |
| T9 | Conformance | `genesis check`, read-only, non-zero exit; reuse `bmad-drift-check` design | Medium — reuse assumption unvalidated (domain A6) |
| T10 | CLI framework | typer + rich (both already pinned) — vs warden's argparse minimalism | **Low — genuine open decision** |

---

## Assumptions

1. **T-A1** — Copier's `run_copy`/`run_update`/`run_recopy` signatures are stable across
   the 9.x line; the pin `>=9.17,<10` holds for v1.
2. **T-A2** — `pyforge.genesis` can share the `pyforge` namespace with `pyforge.warden`
   and `pyforge.atlas` without a namespace-package conflict, since all three use the
   same `packages = ["src/pyforge"]` hatch layout. Not yet built and verified.
3. **T-A3** — Copier's answers-file path is template-configurable, so it can be placed
   under `.genesis/`. Believed true; unverified against the docs.
4. **T-A4** — Marker-based span replacement over markdown is safe for the specific files
   in the model manifest (no markdown construct in them makes an HTML-comment marker
   ambiguous).
5. **T-A5** — `pixi-build-python` handles a second workspace member without root
   workspace changes beyond the feature/environment tables (warden + atlas coexist
   today, so this is near-certain).
6. **T-A6** — Python `>=3.12` matches Copier's floor and the other pyforge packages.

---

## Open Questions

1. **OQ-T1** — typer+rich vs argparse for the `genesis` CLI (T10). Weigh the
   plan/diff/confirm UX against warden's lean-engine precedent; note Copier already
   pulls in prompt-toolkit/questionary/pygments regardless.
2. **OQ-T2** — One state file or two (Genesis state + Copier's `.copier-answers.yml`)?
   Verify Copier's answers-file relocation option before committing to nesting.
3. **OQ-T3** — Exact marker syntax and whether managed regions are needed in non-markdown
   files (`.gitignore`, `pixi.toml`, `.github/workflows/*.yml`). Comment syntax differs
   per format; a per-format marker registry may be required.
4. **OQ-T4** — Does `genesis check` reuse `scripts/bmad_drift_check.py` (copy? extract to
   the package? re-implement?) — domain A6/F9. Needs a read of that script before
   architecture.
5. **OQ-T5** — How does Genesis verify a *referenced* dependency (bmad-method version
   floor, pixi, tmux) is present — its own probe, or delegate to `pyforge-doctor`, whose
   entire charter is pre-flight toolchain verification? Cross-project boundary question.
6. **OQ-T6** — What is the `genesis` ↔ `marshal` boundary? `marshal init --spec …`
   already exists in the crew's CLI cadence (`docs/dreams/ecosystem-crew.md`), and
   Marshal owns "Monorepo & Multi-Project Operation" including `scripts/bmad-switch` and
   `scripts/bmad-loop-worktree` after the 2026-07-23 ownership review. Genesis installs
   that machinery; Marshal operates it. **The line must be drawn explicitly in the PRD**
   or the two products will overlap.
7. **OQ-T7** — Does the model ship as one template or as composable **feature modules**
   (tiers / BMAD wiring / deck family / drift-check), letting a repo adopt a subset?
   Spec-kit's `extensions/templates/` suggests modularity; it multiplies the test matrix.
8. **OQ-T8** — Does `genesis init` create a *repository* (git init, remote, first
   commit) or only a *tree*? Backstage's `publish:github` does the former; Copier does
   only the latter.

---

## Sources

**External:**
- [Copier — API reference (`run_copy` / `run_update` / `run_recopy`)](https://copier.readthedocs.io/en/stable/reference/api/)
- [Copier — Updating a project](https://copier.readthedocs.io/en/stable/updating/)
- [Copier — Comparisons](https://copier.readthedocs.io/en/stable/comparisons/)
- [Nx — Automate Updating Dependencies (`nx migrate`)](https://nx.dev/docs/features/automate-updating-dependencies)
- [github/spec-kit](https://github.com/github/spec-kit)
- [projen — Getting Started](https://projen.io/docs/introduction/getting-started/)
- [cruft](https://github.com/cruft/cruft)

**In-repo / live ground truth:**
- `conda-forge/copier-feedstock` — v9.17.0, `recipe.yaml`, `noarch: python`, MIT
  (verified live via `lookup_feedstock`, 2026-07-25)
- `src/shared/packages/pyforge-warden/pyproject.toml` — hatchling + `[project.scripts]`
  + `packages = ["src/pyforge"]` pattern
- `src/shared/packages/pyforge-warden/pixi.toml` — member-package shape, no
  `[workspace]`, `pixi-build-python`, conda-provisioned engines
- `pixi.toml` (root) — `[environments]` lean-env pattern, `preview = ["pixi-build"]`,
  `requires-pixi >=0.72.2`, the no-`members`-key note
- `docs/reference/library-llms-full.md` — cookiecutter/cruft/jinja2/typer/rich pins and
  the scaffolding + CLI decision tables
- `archive/docs/bmad-setup-plan.md` — bmad-method conda provisioning; the
  greenfield/brownfield track split
- `CLAUDE.md` — PR CI gates (maintenance label, `environment.yaml` sync)
