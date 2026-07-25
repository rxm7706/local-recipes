---
id: SPEC-pyforge-genesis
spec: pyforge-genesis
owner-dream: docs/dreams/pyforge-genesis.md
surface:
  - src/shared/packages/pyforge-genesis/**   # the package this spec builds (not yet created)
companions:
  - extraction-manifest.md
sources:
  - ../../../../../../docs/dreams/pyforge-genesis.md
  - ../../product-brief-pyforge-genesis.md
  - ../../prd.md
  - ../../architecture.md
  - ../../epics.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Genesis — the operating-model installer

## Why

A vision to realize, on top of a pain this repository already pays. The operating model
that makes PyForge work — Dream-first governance, the four tiers and the rules against
crossing them, the framework-neutral portability contract, the six-layer BMAD config
merge, the marker+symlink project switch, the durable-story-specs convention, the
detector/reconciler sync loop — exists only as conventions written into one repository's
files and two scripts. There is exactly one way to get it into a second repository:
read a 562-line setup plan and perform ten phases by hand. And a hand-installed model
freezes at its install date: the origin document was already behind in three ways within
a week of being written. **For a model read by autonomous agents, staleness is not
documentation debt — it is a behavioral bug**, because the agents faithfully follow the
stale rule. The model's sharpest edges were found by production incidents — a
marker/symlink desync that came within one command of overwriting another project's PRD,
and 13 of 31 story specs lost to gitignored-worktree teardown — and a hand-install
reproduces the *shape* of the conventions without the *guards*, which are the expensive
part. Brownfield is the common case and the dangerous one: an installer that clobbers a
working `CLAUDE.md` or deletes a still-load-bearing legacy convention is worse than no
installer. The Dream set a gate — *"awaits its own `bmad-spec` run when the model
stabilizes"* — and the model has stabilized: pyforge-atlas shipped 32 stories through it
and pyforge-warden 31. Genesis is collecting on that.

## Capabilities

- **CAP-1**
  - **intent:** A maintainer can declare the operating model as data — every artifact in exactly one class — so adding a model artifact never requires touching engine code.
  - **success:** A coverage check HARD-fails when any known artifact carries no class (deferral is an explicit enumerated state, not a gap); `genesis explain <artifact>` prints that artifact's class, rationale, and update behavior; adding an artifact to the model is provably a manifest-only diff.
- **CAP-2**
  - **intent:** An operator can carry the model's rule text inside files their team writes freely, and have only that text upgrade.
  - **success:** An update replaces only the marked span, byte for byte, leaving the rest of the file identical; a hand-edit inside the span is detected by body hash and reported; deleting the markers is recorded as a permanent opt-out that later runs respect; nested or overlapping regions are rejected with a specific error; no run can produce a conflict marker.
- **CAP-3**
  - **intent:** A team can layer the model onto a repository that already builds and ships, reviewing exactly what will change before anything is written.
  - **success:** `genesis adopt` runs detect → plan → confirm → apply, dry-run by default and completing in under 10 seconds on a `local-recipes`-sized repo, emitting a machine-readable plan naming each artifact's path, class, detected state, proposed action, and rationale; against `local-recipes` at the shipped model version the plan is **empty**; a second run on an unchanged repo is likewise empty and writes nothing; it refuses on a hand-edited managed artifact and on a dirty git worktree; a `present-legacy` artifact is recorded and preserved, never modified or deleted; and paths passed to `--skip` are recorded and honored on every later run.
- **CAP-4**
  - **intent:** An installed repo can prove in CI that it still conforms to the model.
  - **success:** `genesis check` is read-only with writes structurally unreachable, exits non-zero on any HARD finding, emits typed stable findings each carrying a documented remedy, supports `--json` for CI annotation, reports the repo's model version against the bundled one, and completes offline in under 5 seconds on a `local-recipes`-sized repo.
- **CAP-5**
  - **intent:** A maintainer can create a new repository already born Dream-first, rather than assembling the model by hand.
  - **success:** `genesis init <path>` yields a tree with the tier layout, one seeded Dream conforming to the Tier-0 frontmatter contract, the BMAD multi-project subtree and its `PROJECTS.md` row, the `.gitignore` model region, the selected agent adapters, and the detector wired into CI — after which `genesis check` is green, offline, with zero network calls, in under five minutes wall-clock; `init` refuses a non-empty directory without `--force`, directing the operator to `adopt`.
- **CAP-6**
  - **intent:** An already-installed repository can take a later version of the model without hand edits, and without the upgrade being able to reach the team's own work.
  - **success:** `genesis update` writes a plan and changes nothing until `--run`; a simulated breaking model change (v1 → v2) is absorbed by a version-ordered, applied-once migration with no manual edits; `copied-seeded` artifacts are *offered*, never imposed; and an attempted write to any never-write path is a hard error asserted by test.
- **CAP-7**
  - **intent:** Every per-tool agent entry point in an installed repo derives from one contract, so they cannot drift apart.
  - **success:** The four V1 adapters (`CLAUDE.md`, `.cursor/rules/specs.mdc`, `.github/copilot-instructions.md`, `GEMINI.md`) render from a single neutral-contract source; adding a fifth is a manifest entry plus a wrapper template with no engine change; an adapter file that already exists with repo-specific content receives the model as a managed region rather than an overwrite.
- **CAP-8**
  - **intent:** A repo carries a legible record of what Genesis owns in it and what it has already done.
  - **success:** One git-tracked, schema-validated, do-not-hand-edit state file records `model_version`, `genesis_version`, mode, adopted/updated timestamps, `agents[]`, `managed[]` (path + class + content hash), `skips[]`, `legacy[]`, and `migrations_applied[]`; an invalid file surfaces as a `state-invalid` finding rather than a crash; state is written last, after every file write succeeds, in one atomic replace.
- **CAP-9**
  - **intent:** An air-gapped or firewalled team can install and operate the model with no egress.
  - **success:** An egress-counter test asserts zero network calls across `init`, `adopt --dry-run`, `adopt --apply`, and `check`; the only reachable network path is an explicit `--template <url>`; every runtime dependency resolves from conda-forge or an internal mirror.

## Constraints

- **Five artifact classes, a closed set** — `referenced` · `copied-managed` · `copied-seeded` · `generated-derived` · `hybrid-managed-region`. REFERENCED is never materialized (version range only); COPIED·MANAGED is tool-owned and regenerated wholesale; COPIED·SEEDED is written once and repo-owned forever; GENERATED·DERIVED is recomputed every run; HYBRID·MANAGED-REGION is a repo-owned file with a tool-owned marker span, of which only the span is replaced. **Classification rule:** by *who must be able to change it* and *how an installed repo takes a later model upgrade for it*. The Dream's three-way split was one class short — "copied" must divide into MANAGED and SEEDED, because that is exactly what decides whether an upgrade may rewrite a file. Per-artifact V1 assignment: `extraction-manifest.md`.
- **The never-write set is structural** — `docs/dreams/*.md` (except the one `init` seed), `**/planning-artifacts/**` (except the `init`-seeded `specs/README.md`), `**/implementation-artifacts/**`, `docs/specs/*.md` (legacy tier), and `_bmad/bmm/**` + `_bmad/core/**` (installer-owned). Upgrading the model can never touch the work made with it.
- **The never-write guard lives at the lowest write primitive, not at call sites.** Every byte written to a target repo passes through one `fs` module holding an immutable path set frozen at construction; each write resolves to an absolute, symlink-resolved path and matches against the set *before* opening anything — unresolved matching would miss `_bmad-output/planning-artifacts`, which is a symlink into a project's Tier-2 tree. An AST meta-test enumerates write calls outside `fs`, so no future code path can route around the guard. Templates write through `fs` like everything else: a template that writes outside its declared paths is a hard error.
- **AD-01 — CLI is typer + rich, confined to `cli.py`.** No other module imports either, so `--json` output and library use stay presentation-free. Plan rendering is the product's main human surface, so warden's argparse minimalism is deliberately not adopted.
- **AD-02 — one Genesis-owned state file at `.genesis/state.yml`.** Copier's answers file is opaque and tool-owned: never read by Genesis, written only via Copier. Answers are re-supplied programmatically from Genesis state on every Copier call, so Genesis state is the single source of truth and the answers file stays an implementation detail.
- **AD-03 — one canonical marker grammar, rendered per comment syntax.** The format is *declared* per artifact in the manifest, never sniffed from content; the marker `sha` covers the region body only, so the marker line is not self-referential; nested or overlapping regions are a hard error.
- **AD-04 — `genesis check` re-implements the generic subset of this repo's `bmad_drift_check.py`; it does not import, vendor, or extract it.** It borrows the proven design (the `Finding` shape, the HARD/DRIFT/INFO ladder, the coverage check, `--json`). Roughly 85% of that 662-line script is `local-recipes` factory-specific and meaningless elsewhere. The two detectors coexist; convergence is explicitly out of V1, which keeps `local-recipes` uncoupled from a Genesis release.
- **AD-05 — the manifest is one YAML document, keyed by stable artifact id, never by path** (paths are per-repo). Each entry carries class, path, format, regions with anchors, `since`/`until` model-version bounds, `applies_to`, and rationale. One file keeps coverage a single-pass check and makes the manifest reviewable as a diff — which matters, because the manifest *is* the product's contract.
- **AD-06 — region insertion uses a declared ordered anchor list with an append-at-EOF fallback, and never guesses mid-file.** It never inserts inside a fenced code block, and always reports the chosen anchor in the plan so a human reviewing the plan can veto placement.
- **AD-07 — the plan is a machine-readable artifact at `.genesis/plan.json`, gitignored by default**, carrying a `repo_fingerprint` (git HEAD + dirty flag + hashes of the artifacts it names); apply **refuses** a plan whose fingerprint no longer matches. Deliberately not committed: a plan is cheap to regenerate, while a committed stale plan is a hazard.
- **AD-08 — no `eject` verb ships in V1, but state must not preclude one.** For every managed artifact, state records `id`, `path`, `class`, `body_sha`, and `inserted_region_span` — enough for a future eject to strip markers and forget the artifacts without touching content.
- **AD-09 — legacy conventions are preserved, recorded in `state.legacy[]`, and at most advised** (an INFO finding naming the successor); never migrated, never written to. Genesis ships no automated Tier-1 → Tier-2 migration: legacy content is the team's work product and falls inside the never-write set.
- **One pipeline for every mutating verb:** `resolve → detect → plan → apply`. `check` is `adopt`'s detect+plan with the apply stage structurally unreachable — which is why "check never writes" is a guarantee rather than a discipline. Detect is pure (no I/O side effects); apply consumes only a serializable plan and never re-derives state; hash guards are evaluated in detect and never in apply.
- **Managed-region replacement is pure byte-span substitution** between markers — never a three-way merge, never semantic markdown parsing. A half-merged file and a conflict marker are therefore not representable states.
- **Idempotence is *defined* as plan-emptiness:** a verb is idempotent iff detect+plan immediately after a successful apply yields zero actions. This makes the `local-recipes` oracle and adopt-run-twice the same assertion against different repos — one mechanism, two proofs.
- **The empty-plan oracle runs in Genesis's own CI**, so model drift in the repository the model was extracted from fails Genesis's build the day it appears, rather than at the next install.
- **Copier is a dependency, not a framework.** Exactly one module imports it, and only its public `run_copy` / `run_update` / `run_recopy`; pinned `>=9.17,<10` by range with a version-range sync test. `--force` maps to `run_recopy` semantics (discarding local evolution of managed artifacts) and requires explicit confirmation. Copier's code-executing template features stay gated behind an explicit `--unsafe` flag.
- **`adopt` and `update` are dry-run/two-phase by default and refuse on a dirty git worktree**, because git is the designated undo mechanism. No verb may leave a repo partially applied: apply is transactional per plan, or it reverts. State is written **last**, after all file writes succeed, in one atomic replace — the `bmad-switch` marker/symlink desync lesson encoded.
- **Two clocks:** CLI semver and operating-model semver move independently, are both recorded in state, and are both reported by `genesis version`. Migrations are keyed to model version only, are pure plan-producing functions that never write directly, and are applied exactly once.
- **Genesis installs the machinery; Marshal operates it.** Marshal owns the *source* of `scripts/bmad-switch` and `scripts/bmad-loop-worktree`; Genesis owns their *delivery* as COPIED·MANAGED artifacts and never forks them. Genesis's write scope is a repo's structure and conventions; Marshal's is a repo's executions.
- **Air-gap by construction:** no module imports `requests`, `httpx`, or `urllib.request` (meta-test enforced); templates ship in-package; the only network path is Copier's git fetch behind an explicit `--template <url>`. Accepted trade-off: a model change requires a package release, and `--template` is the escape valve.
- **Packaging clones `pyforge-warden`'s shape exactly** — pixi workspace member, hatchling, `packages = ["src/pyforge"]`, a `genesis` console entry point, and a **lean** environment with `no-default-feature = true`. The lean env is mandatory, not cosmetic: bmad-loop worktrees materialize it, never the fat `local-recipes` env. Python `>=3.12`; `pyforge.genesis` shares the `pyforge` namespace with warden and atlas.
- **Touching root `pixi.toml` fires this repo's two always-on PR gates** (the `maintenance` label and a regenerated `environment.yaml`) and stales `docs/reference/library-llms-full.md`; all three are acceptance criteria on the packaging work, not follow-ups.
- **Genesis's own artifacts obey the tier discipline it installs:** planning artifacts are Tier 2, story specs are durable and tracked under `planning-artifacts/specs/`, and nothing it produces may be git-tracked under `implementation-artifacts/`.
- **Every finding type is a member of one enum with a documented remedy string**; ad-hoc error strings are forbidden, and non-zero exit codes are distinct and documented per failure mode.

## Non-goals

- **Operating the machinery Genesis installs** — bmad-loop runs, quality gates, escalation, graduated autonomy, worktree lifecycle, and run-time project switching are Marshal's.
- **Machine and toolchain health** — Genesis performs a minimal presence-and-floor probe of REFERENCED dependencies (so it works in a repo that has not adopted Doctor) and delegates to `doctor check` when available, rather than growing its own probe suite.
- **Deck content, and the Dream's other two faces** — the Dream casts Genesis as three things: the master narrative, the alignment deck (`presentations/pyforge-genesis/`, already real), and the seed. **This contract covers only the seed.** Genesis lays down `presentations/<slug>/` and its conventions; Herald fills and round-trips them.
- **Repository creation on a git host** — `genesis init` makes a tree, not a GitHub repo.
- **Non-git targets** — they forfeit the update story entirely, which is the whole product.
- **Composable feature modules** (adopting a subset of the model) — V1.x; the manifest's `applies_to` field is shaped to allow a future `groups[]` without a schema break.
- **`check --fix`** — V1.x; requires a fixable/unfixable distinction per finding type.
- **`genesis eject`** — V1.x; state is shaped for it but no verb ships.
- **A hosted registry of installations or fleet conformance scorecards** — Genesis is not a service and keeps no central record; installed repos run `check` in their own CI.
- **Publishing the model as a separately versioned artifact** — V2; `--template` is the seam.
- **Automated Tier-1 (`docs/specs/`) → Tier-2 migration** — preserve and mark only.
- **Converging `genesis check` with `bmad-drift-check`** — explicitly out of V1.
- **Windows parity beyond `init` / `check`** — best-effort; the loop machinery is Linux/macOS, Windows via WSL.
- **Authoring any conda recipe** — `copier` is consumed from the existing conda-forge feedstock, so the core work triggers neither the CFE skill-invocation rule nor its closeout retro.

## Success signal

A second repository, created by `genesis init`, runs a full Dream → spec → epics →
loop-driven build and then **takes a later model upgrade via `genesis update` with no hand
edits** — `genesis check` green before and after. Alongside it, `genesis adopt --dry-run`
against `local-recipes` at the shipped model version produces an **empty plan**, proving
the model Genesis carries and the repository it was extracted from are the same model.
Both verdicts read from exit codes and produced files alone.

The signal has two named falsifiers, and reaching either pauses or rescopes the work
rather than shipping around it: **K-01** — the managed-region merge proves unreliable on
real files (corruption or an unresolvable conflict in either of the first two adopters);
**K-02** — the empty-plan oracle cannot be reached without special-casing the model into
incoherence, which would mean the model is not actually extractable and the Dream's
stabilization gate was called too early.

## Assumptions

- Genesis targets git repositories only; non-git targets forfeit the update story entirely.
- The operating model has genuinely stabilized — the Dream's own gate. Evidence: pyforge-atlas shipped 32 stories and pyforge-warden 31 through it; the durable-story-specs convention closed the last known hole on 2026-07-25.
- Copier's `run_copy` / `run_update` / `run_recopy` signatures are stable across 9.x, and its answers-file path is template-configurable (the second is AD-02's fallback trigger). Both are gated by Spike-0, which is a critical gate on the materialization work rather than an accompanying task.
- HTML-comment markers are unambiguous in the specific markdown files the manifest names.
- The first two adopters are `local-recipes` (the oracle) and one greenfield pyforge sibling; external adoption is post-V1.
- Marshal accepts ownership of `bmad-switch` / `bmad-loop-worktree` *source* while Genesis owns *delivery*. This is not yet ratified in Marshal's own planning chain.

## Open Questions

- **K-03 has no quantified threshold in any source.** At what migrations-per-model-minor-version rate does the model become too volatile to install, and who makes that call?
- **Does `genesis init` create a repository or only a tree?** Creation on a git host is scoped out, but a local `git init` and first commit are left unstated.
- **Is append-at-EOF always a safe anchor fallback?** AD-06 chose the fallback for an unmatched anchor, but did not close whether an unfamiliar `CLAUDE.md` deserves a refusal instead.
