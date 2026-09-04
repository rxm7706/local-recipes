---
review: rubric-walker
subject: architecture-python-foundry-cutover-2026-09-04/ARCHITECTURE-SPINE.md (iteration 1, draft, fnd:AD-1..12)
lens: good-spine checklist (8 checkpoints), verified against the live repo at HEAD
reviewer: independent architecture reviewer (read-only; no spine edits)
date: "2026-09-04"
---

# Rubric-walker review — spine `python-foundry-cutover`

## Gate verdict

**PASS-WITH-FIXES** — the paradigm (strangler-fig, manifest-routed, island lock, read-only
archive) is the right shape and every AD is additive over the inherited sets, but three
CRITICAL gaps (a derivation source that is blind on the trees the cutover actually moves; a
fold that silently changes repo-root depth for 59 code files; a boundary AD that ratifies an
invariant the brownfield already breaks) plus an undecided operational envelope must land as
new/tightened ADs before Epic 44's stories are safe to decompose.

## What the spine gets right (not re-litigated below)

- The three-role paradigm table and the phase→story DAG are unambiguous; every AD names a
  *prevented divergence*, not a preference. AD-9 (operator-flipped gates) and AD-10 (working
  set, not universe) are enforceable as written.
- `five_tier.py`'s three retarget sites are correctly identified: `_packages_root`
  (`src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py:73-74`),
  `script_map_from_packages_root` (`:15`, `:115`) and the skill/persona paths (`:117-123`,
  including the mason `conda-forge-expert` exception). AD-6 names all three.
- The Stack's `conda-build >=25.3.1` and `conda-smithy >=3.44.6,<4` are exact matches for
  `pixi.toml:52` and `pixi.toml:113`; `requires-pixi = ">=0.78.0"` matches `pixi.toml:9`.
- Inherited-invariant citation discipline (`fnd:` / `canopy` / `pap:`) is correct and the
  "Conflict, not override — none found" claim is right for eleven of the twelve ADs. The one
  exception is C-3 below.

---

## CRITICAL

### C-1 — AD-2: the manifest's derivation source cannot classify the paths the cutover moves

**Problem.** AD-2's Rule says the manifest "is generated from `git ls-files` × the spec-surface
classification (`scripts/spec_surface_check.py`'s spec→surface globs), one row per tracked
path". Two independent defects:

1. **The classification is blind on the movers.** `scripts/spec_surface_allowlist.txt`
   *exempts from spec ownership* exactly the trees Phases 1–3 route:
   `.claude/**` (line 3 — CAP-3's entire subject), `_bmad/**` and `_bmad-output/**` (lines 10-11
   — AD-12's subject), `docs/dreams/**` (line 5), `docs/governance/**` (line 8),
   `docs/reference/**`, `docs/specs/**`, `.github/**`, `.ci_support/**`, `conda-forge.yml`,
   `build-locally.py`, `azure-pipelines.yml` (AD-8's `dies` list), `tests/**`,
   `src/sentinel/**`, `.cursor/**`, and ~30 named `scripts/*.py` files. For every one of those
   paths the classification returns "allowlisted", which is not a destination.
2. **Spec-surface answers a different question.** It says *which Spec owns a file*, never
   *where the file goes*. Even for governed paths the classification carries no
   {target | `stays` | `dies`} signal, so the "derived, not declared" claim is not achievable
   from that source — the destination is a judgement 44.1 must make and record.

**Scale defect on top.** `git ls-files | wc -l` = **24,858** tracked paths (10,480 outside
`recipes/`). "One row per tracked path" is 24.8k rows in a file the Structural Seed places at
`docs/foundry/manifest.md` `[ASSUMPTION: location]` — a markdown table no detector can
reliably diff, and the artifact AD-2 makes review-blocking.

**Evidence.** `scripts/spec_surface_allowlist.txt:3-11` and its per-file `scripts/*` block;
`scripts/spec_surface_check.py:5-6` ("every tracked file governed by a spec surface **or
explicitly allowlisted**"); `git ls-files | wc -l` = 24858.

**Fix.** Rewrite AD-2's Rule to: (a) make **`git ls-files` the enumerator and the
spec-surface map an *annotation*, not the classifier**; (b) permit **longest-prefix directory
rules with explicit leaf overrides** (a directory row covers its subtree; a leaf row wins),
which collapses `recipes/**` and `_bmad-output/**` to a handful of rows; (c) require a
**machine-readable** artifact (`docs/foundry/manifest.toml` or `.json`) with the markdown as a
rendered view; (d) add the enforceable half as a detector rule: *`git ls-files` minus manifest
coverage must be empty* (`manifest-coverage`, exit 1 on an unrouted path). Add a Deferred row
or OQ: **what routes an allowlisted path** — 44.1's own judgement, recorded per row with a
`reason`, is the honest answer and should be stated.

### C-2 — AD-6: the fold changes repo-root depth, and 59 files compute paths by fixed depth

**Problem.** `src/shared/packages/<x>` → `src/packages/<x>` removes **one** directory level.
AD-6's Rule enumerates *configuration* consumer sites (pixi.toml path-deps, Containerfile
`COPY`, `five_tier._packages_root`, `script_map_from_packages_root`, marshal-policy globs, Spec
`surface:` globs, CI `paths:`) and says they are "rewritten from manifest rows in the same
story". Manifest rows are **paths**; they do not surface **code constants**. Every
`Path(__file__).resolve().parents[N]` that walks to the *repo* root breaks silently, and
several have swallow-the-error fallbacks that return a *wrong* directory instead of raising.

**Evidence** (`git grep -n "parents\[[3-9]\]" -- src/shared/packages` → 59 files):
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py:81`
  `PROJECT_PATH = Path(__file__).resolve().parents[4]`, consumed by
  `tests/orchestration/test_viz_loadable.py:24` — `REPO_ROOT = PROJECT_PATH.parents[3]`, whose
  own comment spells the doomed chain: `# pyforge-atlas -> packages -> shared -> src -> repo`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py:132`
  `return (current.parents[8] if len(current.parents) > 8 else current.parent) / "data"` and
  `dashboard/factory_status.py:63` — a **silent** wrong-root fallback, not a failure.
- `tests/test_duckdb_boundary.py:18`, `tests/test_read_only_live_attach.py:26`,
  `tests/test_scribe_plane_recall.py:11` — `REPO_ROOT = …parents[5]`;
  `tests/dashboard/test_identity_*.py` — `parents[6]`;
  `tests/pipelines/derived_artifacts/test_identity_complete_export.py:17` — `parents[7]`.

**Fix.** Extend AD-6's Rule with a second clause: *"the fold changes repo-root depth by one; a
consumer is any path expression, **including code constants**. No file under `src/packages/`
may compute the repo root by fixed parent depth after 44.4 — root discovery is
marker-based (walk up for `pixi.toml`/`.git`), and `rg 'parents\[[0-9]+\]' src/packages` with a
repo-root intent is a review-blocking finding."* Add the detector (`fixed-depth-root-walk`) to
44.4's done-when. Keep member-relative walks (`conf/base/catalog.yml` at
`admission.py:119`, `mcp/session.py:26`) explicitly allowed — those are depth-stable.

### C-3 — AD-7 / Inherited table: the spine ratifies `pap:AD-2` against a brownfield that already breaks it, and miscounts the drift

**Problem.** The Inherited Invariants table asserts "pap:AD-2 host never imports `pyforge.*` |
The fold (AD-6) changes paths, not this boundary; `src/platform/` keeps **zero** `pyforge.*`
imports." That is **false today**, and AD-7's Rule ("the Containerfile has no `COPY
src/packages` and no `sys.path` insert for a package") therefore does not merely preserve a
boundary — it *deletes a working code path* with no successor named. Two stories can resolve
that differently (install `pyforge-steward` as a workspace member into the platform env; take
it from the channel; move `ingest/github_projects/` out of the host; or quietly keep the COPY).

**Evidence.**
- `src/platform/ingest/github_projects/source.py:9-10`, `pipeline.py:11-12`, `graphql.py:13-14`,
  `test_github_metrics_dlt.py:9-10` — `from pyforge.steward.keys import HostScopedCredential`,
  `from pyforge.steward.sync import …`. Eight import sites in host code.
- `src/platform/Containerfile:170` — `COPY src/shared/packages/pyforge-steward/src/pyforge
  /app/pyforge` — the host image ships the `pyforge` namespace on purpose.
- The count is wrong: `grep -c "^COPY src/shared/packages" src/platform/Containerfile` = **10**
  (lines 163, 165, 167, 170, 171, 172, 173, 174, 175, 176), not the "five" AD-7 and the
  inherited table both cite. Nine are `django-*` src; the tenth is the `pyforge` one above.
- `src/platform/config/settings/base.py:27` and `:41` are the two `sys.path.insert` sites that
  must die (chrome + the eight portals, `_STATION_PORTAL_PACKAGES` at `:28-36`). AD-7's
  `[ASSUMPTION]` mentions only `platformapp`'s insert (`manage.py:29`, `config/asgi.py:21`,
  `config/wsgi.py:26`) — correct that those stay, but it does not name the two that go.

**Fix.** (a) Correct "five" → **ten**, and split the Rule: *nine `django-*` `COPY`s + the two
`base.py` inserts die together with the nine new `django-*` `pixi.toml` files; the
`pyforge-steward` `COPY` is a **separate, named** decision.* (b) Add a **"Conflict, not
override — pap:AD-2"** paragraph in Inherited Invariants: the host's `ingest/github_projects/`
imports `pyforge.steward.*` today; the fold must either sanction it (host consumes the
*distribution*, satisfying pap:AD-9's "consume, never fork" while conceding pap:AD-2's import
boundary) or relocate the module — and say which, in 44.4, not per-story.

---

## HIGH

### H-1 — No AD owns the repo-identity rewrite, yet two CAP success criteria are string-level

**Problem.** CAP-3 succeeds when "no `MASON_CFE_ROOT` … resolves to `local-recipes`" and CAP-6
when "an agent-opened PR never targets `local-recipes`". Both are properties of **file
contents**, not file locations — and AD-2 routes paths while AD-6 rewrites only the fold's
consumer paths. Nothing owns the rename.

**Evidence.** `git grep -o "rxm7706/local-recipes" | wc -l` = **333** occurrences across
**148** tracked files (incl. `CLAUDE.md:2`, `README.md:4`, `.github/workflows/scripts/linter.py`,
`.claude/skills/conda-forge-expert/SKILL.md`, `scripts/submit_pr.sh`, four CFE scripts).
`git grep -l "local-recipes" | grep -v '^recipes/' | wc -l` = **747** tracked files.
The pixi **environment** is itself named `local-recipes` (`pixi.toml:701`) and
`pixi run -e local-recipes` appears **974** times in **319** tracked files. `pyforge.toml:3`
declares `name = "local-recipes"` as the repo's convention record.

**Compounding risk.** Auto-memory `GATE-011`: story-spec `verify_commands` must match spec
strings **exactly**, and a journaled refusal is terminal. Renaming the env invalidates every
frozen `verify_command` across eight projects' ledgers.

**Fix.** New **AD-13 — "the slug and the env name are one rename, executed once"**: the
foundry slug (`rxm7706/python-foundry`), the workspace name (`pyforge`) and the day-to-day
environment name are decided in 44.3 and applied as a single mechanical rewrite pass with a
detector (`legacy-slug-check`: zero `rxm7706/local-recipes` outside the manifest's `source_sha`
column and the archive banner). Add an **open question `estate-env-name`** — keep
`local-recipes` as an env name inside a repo named foundry (cheap, ugly, GATE-011-safe) or
rename (clean, invalidates frozen verify_commands) — because two stories will otherwise pick
differently.

### H-2 — AD-3/AD-4 split the *locks* but nothing splits the *task registry*

**Problem.** AD-3 forbids solver-farm tooling in the estate lock; AD-4 makes recipe build/submit
/update island subprocesses. Neither says **which manifest owns a task**, and the repo has
estate-spec'd tasks that need island dependencies and read island paths.

**Evidence.**
- `pixi.toml:1180-1186` — `[feature.local-recipes.tasks.generate-bmad-suite]` and
  `build-bmad-suite` shell `.claude/scripts/conda-forge-expert/*.py` and read
  `recipes/bmad-suite/suite-members.yaml` (an island path after Phase 3/4) in service of the
  **estate** spec `spec-bmad-suite-metapackage` (steward Epic 39).
- ~30 further `feature.local-recipes` tasks call `.claude/scripts/conda-forge-expert/*.py`
  (63 tracked files under `.claude/scripts/`).
- `pixi.toml:74` and `:85` set `CONDA_BLD_PATH = "$PIXI_PROJECT_ROOT/build_artifacts"`;
  `$PIXI_PROJECT_ROOT` becomes `factory/` for island tasks, silently relocating the local
  build channel. (`feature.bmad-ui` at `pixi.toml:1797-1808` documents the last time an absolute
  `file://` channel path broke two Pages deploys — the same failure class.)

**Fix.** Tighten AD-3 with a **task-placement rule**: *a task lives in the manifest whose lock
carries its dependencies; a cross-boundary workflow is an estate task that is a thin wrapper
over `pixi run --manifest-path factory/pixi.toml <task>` (AD-4's grammar), never a duplicated
dependency.* Add a Deferred row for `CONDA_BLD_PATH` / `build_artifacts` home.

### H-3 — AD-4 conflates "CFE root" with the skill directory and never mentions the marker

**Problem.** AD-4's Rule: "`MASON_CFE_ROOT` (flag → env → cwd walk, `pyforge/mason/resolve.py`)
resolves to `skills/domain/conda-forge-expert`". In the live code `MASON_CFE_ROOT` is a **repo
root that contains a marker**, not a skill directory — so the Rule as written is not
implementable without also deciding the fate of CFE's other three tiers.

**Evidence.**
- `src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py:100`
  `_CFE_MARKER = Path(".claude/scripts/conda-forge-expert")` — the walk tests
  `<level>/.claude/scripts/conda-forge-expert` `is_dir()` (`:113-116`).
- `…/mason/errors.py:117,128` duplicates the literal in the user-facing not-found message.
- `…/mason/cfe.py:100,697,1250` run scripts *from* `.claude/scripts/conda-forge-expert/`;
  `:723,870,875,944,980,1024,1079,1084` reference `.claude/tools/conda_forge_server.py`.
- Live tiers: `.claude/skills/conda-forge-expert/scripts/` (canonical impl),
  `.claude/scripts/conda-forge-expert/` (63 tracked wrapper files),
  `.claude/tools/` (3 tracked files incl. the MCP server), `.claude/data/conda-forge-expert/`
  (0 tracked — runtime state, the `runtime-state-home` OQ).

**Fix.** Restate AD-4: *the CFE root is the directory containing the CFE marker; in foundry
the marker is `<root>/skills/domain/conda-forge-expert/scripts` (or a named successor), and
44.6 changes `_CFE_MARKER` + `errors.py`'s message string in the same commit.* Add a Deferred
row or OQ **`cfe-wrapper-tier-home`**: where the 63 public-wrapper entrypoints and the 3
`.claude/tools/` MCP files live in foundry, and which manifest's environment executes them
(their import floor — `conda-forge-metadata`, `ruamel.yaml`, `requests` — is island-side, per
`cfe.py`'s interpreter-selection docstring).

### H-4 — AD-5 collides with canopy AD-17 (SKF output shape) and exempts the persona tier from moving

**Problem, part 1 (SKF).** AD-5: estate skills live *only* at `skills/{stations,personas,domain}
/<x>/SKILL.md`; `.claude/skills/<x>` is a per-skill relative symlink; "a regular directory for
an estate skill under an adapter is a detector finding." But canopy AD-17 makes
`skf-export-skill` the **writer** of station skills, and SKF's on-disk shape is not
`<x>/SKILL.md`.

**Evidence.** `.claude/skills/pyforge-atlas/` = `0.1.0/pyforge-atlas/{SKILL.md, metadata.json,
provenance-map.json, context-snippet.md}` + `active` + `skill-brief.yaml`; and a **shared**
`.claude/skills/.export-manifest.json` (schema_version 2, one entry per station) that cannot be
a per-skill symlink. The next `skf-export-skill` run writes a real directory where AD-5 requires
a symlink — AD-5's own detector would then flag SKF's sanctioned output.

**Problem, part 2 (personas).** AD-5 exempts "installer-owned skills (`bmad-*`, `skf-*`)" —
which literally exempts the eight station **personas**, `.claude/skills/bmad-agent-<station>/`,
from moving to `skills/personas/<station>/`. They are estate-authored (they carry
`customize.toml` and dated station transcripts), they are the fifth face in cutover.md's face
map, and `five_tier.py:118` reads `repo_root/.claude/skills/bmad-agent-<station>/SKILL.md` as
the persona tier — so an exempted persona and a moved persona are two stories' worth of
divergence against canopy AD-14 (five tiers or the 03 station is not done).

**Fix.** Split AD-5's carve-out on **who writes**, not on the name prefix: *installer-**written**
trees (`_bmad/`-regenerated launchers, `skf-*` tooling skills) stay where their installer
writes; estate-**authored** skills move, including `bmad-agent-<station>` personas → `skills/
personas/<station>/`.* State whether SKF's compile target becomes `skills/stations/<station>/`
(preferred — it keeps one writer, one tree) or stays `.claude/skills/`, and route
`.export-manifest.json` explicitly. Record the collision as a "Conflict, not override — canopy
AD-17" note rather than leaving the inherited row reading "unchanged".

### H-5 — The operational/environmental envelope of the *new repo* is largely undecided

**Problem.** Checkpoint 8's dimensions are mostly absent. AD-8 decides CI *triggers* and one
`dies` list; nothing decides the control plane the estate depends on.

**Evidence, per dimension.**
- **Visibility.** SPEC.md Assumptions: "`gh` auth … can create a **private** repository". But
  `.github/workflows/dashboard.yml:16-42` publishes to **GitHub Pages** (`pages: write`,
  `environment: github-pages`, `actions/deploy-pages@v5`), and `kedro-viz-publish.yml` is the
  same shape. Private-repo Pages and private-repo Actions minutes are both billing-gated — the
  same billing block the `actions-minutes` OQ inherits. Visibility is the variable that
  *decides* that OQ, and no AD or OQ names it.
- **Secrets / credentials.** `secrets.CRC_PULL_SECRET`, `secrets.HERALD_WEBHOOK_SECRET` (plus
  `secrets.GITHUB_TOKEN`) and six `vars.PLATFORM_CI_*` toggles (`platform-ci.yml:258,701,703,
  900,1153,1365`) exist only in the repo's settings — not in git, not in the manifest, not in
  any AD. A fresh repo starts with none of them; CAP-1's "CI green on the empty estate" hides
  that because the empty estate runs none of those jobs.
- **Branch protection / who can push / default branch.** Nothing. Today: `origin` = `main`
  (`git symbolic-ref refs/remotes/origin/HEAD`), a PR-per-change convention documented in
  `CLAUDE.md`, plus two loop-home remotes (`marshal-home`, `mason-home` → `~/.bmad-loops/*`).
- **The rest of `.github/`.** `actions-policy.toml` (the artifact of the 2026-08-30 minutes
  incident), `dependabot.yml`, `ISSUE_TEMPLATE/`, `pull_request_template.md`, `stale.yml`,
  `copilot-instructions.md`, `actions/sync-pypi-mappings/` — routed by no AD (AD-8 names
  workflows only), and all of `.github/**` is spec-surface-allowlisted (C-1).

**Fix.** New **AD-14 — "the foundry control plane is declared, not inherited"**: visibility,
required checks, branch protection, environments, and the secret/variable inventory are a
declared artifact created in 44.3 (a checked-in `docs/foundry/control-plane.md` naming every
secret *by name and consumer*, never a value — consistent with canopy AD-19's
"references, never values"), and CAP-1 is not done until every declared item exists in the new
repo. Add **OQ `foundry-visibility`** and bind `actions-minutes` to it explicitly.

### H-6 — AD-12 enumerates the BMAD/doc move too narrowly; the Charter is routed by nothing

**Problem.** AD-12 moves "`_bmad/`, `_bmad-output/projects/` and `docs/dreams/` … as one unit."
Tracked content sits **outside** those three prefixes and is load-bearing.

**Evidence.**
- `_bmad-output/` root, outside `projects/`: `policy-defaults.toml` (layer 1 of the four-layer
  marshal policy composition), `PROJECTS.md` (the multi-project index CLAUDE.md points at),
  `harness-profiles/cursor.toml`, `EXEMPLAR-STANDARD.md`, `POLICY_COMPOSITION_README.md`,
  `brainstorming/`, plus five dated fleet reports.
- **`docs/governance/spec-pyforge-charter/`** — the constitutive governance kernel, cited by
  canopy AD-21 and by Charter §6 (the rule that moves detector verdicts to Doctor) — appears in
  **no AD, no Deferred row, and no Structural Seed line**, and is spec-surface-allowlisted
  (`spec_surface_allowlist.txt:8`), so C-1 means the manifest will not classify it either.
- Structural Seed omissions vs. the companion's own target tree: `config/`, root
  `Containerfile`, `src/ides/ src/sentinel/ src/domains/`, `templates/`,
  `presentations/pyforge-<station>/`. Omissions vs. reality: `scripts/` (the detector registry
  and ~30 tracked scripts), `tests/`, `helm/`, `conf/`, `docs/governance/`, `docs/reference/`,
  `archive/`, `.bmad-loop`, `src/prototype/`, `pyforge.toml`.

**Fix.** Restate AD-12's unit as `_bmad/**`, `_bmad-output/**` (all of it, not just `projects/`),
`docs/dreams/**`, `docs/governance/**`. Add a **Structural-Seed completeness rule** to AD-2:
*"every tracked top-level path is either in the Structural Seed or has an explicit `stays`/`dies`
manifest row; a top-level path in neither is a review-blocking finding."* That converts the seed
from illustration into an enforceable checklist and closes the `docs/governance/` hole.

---

## MEDIUM

### M-1 — Stack: `rattler-build 0.72.2` is wrong (it is 0.75.0)

`pixi.toml:1494` declares `rattler-build = ">=0.75.0"` and `pixi.lock` resolves
`rattler-build-0.75.0-*.conda`. The only `0.72.2` in the lock is **`py-rattler-build`-0.72.2**
(a different package), and `0.72.2` also appears in `pixi.toml:7` as a *pixi* version in a
comment — the likely provenance of the error. A builder writing `factory/pixi.toml` from the
Stack table would pin the recipe engine three minors back. **Fix:** correct the row to
`>=0.75.0` (lock 0.75.0) and note that `conda-smithy` resolves 3.62.0 under the
`>=3.44.6,<4` floor (`pixi.toml:113`'s own comment warns the CalVer 2026.x line needs the
`conda` package, which this env lacks) — worth carrying into the island manifest verbatim.

### M-2 — AD-3's "29-environment single lock" is not the measured number

`pixi.toml`'s `[environments]` table declares **27** named environments (+ implicit `default`
= 28); `pixi.lock` carries 32 environment blocks (platform variants). **Fix:** cite the
measured count or drop the numeral — AD-3's argument does not need it.

### M-3 — AD-8's "staged-recipes linter (three workflows)" undercounts the `dies` set

`.github/workflows/` holds `staged-recipes-linter.yml`, `reusable-staged-recipes-linter.yml`,
`reusable-staged-recipes-linter-selftest.yml` **and** `linter_issue_comment.yml`, plus
`.github/workflows/scripts/linter.py` (which itself hardcodes `rxm7706/local-recipes`, H-1).
`test-all.yml` is a fourth recipe-CI workflow beside `test-linux/macos/windows.yml`. **Fix:**
enumerate the `dies` set **by filename in the manifest**, and have AD-8 reference the manifest
rather than a count.

### M-4 — AD-5's `.cursor/skills/` does not exist and is not this repo's Cursor convention

`ls .cursor/` has `rules/` (CLAUDE.md and AGENTS.md both point at `.cursor/rules/specs.mdc`),
`worktrees/`, and drain scratch — **no `skills/`**; only 6 tracked files under `.cursor/`, all
under `pyforge-fleet-drain/`. The AD's `[ASSUMPTION]` covers *symlink resolution* but not the
existence or shape of the adapter itself. **Fix:** make the adapter set data-driven (one row
per IDE: adapter root + expected layout) and add an OQ `cursor-adapter-shape`, so a Cursor
change does not bend AD-5.

### M-5 — Deferred "`config/` vs today's `conf/`" is circular, and conflates two different things

The row says "Manifest rows decide per path … Revisit when 44.1 renders the manifest" — but
AD-2 forbids the manifest from *declaring* anything the classification does not already say, so
44.1 has no authority to invent `config/` (C-1 compounds this). Worse, the row merges two
unrelated decisions: (a) `conf/` is a **Kedro-mandated** name asserted at runtime —
`pyforge/atlas/mcp/session.py:31` `assert (PROJECT_ROOT/"conf"/"base"/"catalog.yml").is_file()`,
`admission.py:353`, `settings.py:77` `# CONF_SOURCE = "conf"` — renaming it is a code change,
not a layout preference; (b) cutover.md's root `config/` means **deploy overlays**, which today
live at `src/platform/deploy/charts/platform/`. **Fix:** split into two rows — "Kedro `conf/`:
not renameable, moves with its member" and "deploy-overlay home: decide in 44.3/44.4".

### M-6 — Deferred "`environment.yaml` keep-or-drop — AD-8 allows either" is a live divergence

`environment.yaml` is pin-registry **site (6)** in `pixi.toml:9`'s sixteen-site enumeration and in
`scripts/pixi_version_registry.py`; `pixi-version-check` fails on drift. Both 44.3 (writes the
first estate workflow) and 44.4 (rewrites `pixi.toml`) touch it, and "either" lets them
disagree. **Fix:** state the default in AD-8's Rule (*"dropped unless 44.3's workflow produces
it; dropping it removes registry site (6) in the same commit"*) or make it a 44.3 decision that
44.4 is bound to.

### M-7 — AD-9's premise is not yet true; the Rule is unenforceable as phrased

The spine's header says "Epic 44's stories are ledger `blocked`" and AD-9's Rule says "All 44.x
are ledger `blocked` while solutioning is under review." Today
`_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md` ends at **Epic 43**, and
`sprint-status-ledger.yaml` has **no `44-*` keys** — so the asserted state does not exist, and
SPEC.md's own constraint is "no CAP-1 dispatch until this Spec is `ready` **and Epic 44
exists**." **Fix:** restate AD-9 as a *creation* rule — *"Epic 44 is minted (via
`bmad-correct-course`) with every 44.x row created at `blocked`; a 44.x row that appears in any
state other than `blocked` is a review-blocking finding; Marshal never auto-flips."* That is
checkable the moment the epic lands, and it is not falsified before then.

### M-8 — AD-10's `reason` enum should name the estate's own toolchain recipes

`recipes/bmad-*` (15 directories, incl. `bmad-suite`, `bmad-loop`, `bmad-method`,
`bmad-module-skill-forge`) are the estate's *own* toolchain, and `recipes/bmad-suite/
suite-members.yaml` is read by an estate task under the active `spec-bmad-suite-metapackage`
(steward Epic 39). `referenced-by-spec` covers them only if 44.8 reads specs across **all
eight** BMAD projects. **Fix:** add `estate-self-packaging` to the enum (or make
`referenced-by-spec` explicitly fleet-wide) so 44.8 cannot leave foundry unable to rebuild its
own toolchain.

### M-9 — AD-7 understates the work: nine `django-*` packages have no `pixi.toml` at all

All ten `pyforge-*` packages carry a `pixi.toml`; **none** of the nine `django-*` packages do —
which is precisely why the Containerfile `COPY`s and the `base.py` `sys.path` inserts exist.
AD-7's "the pattern already live for `pyforge-warden`" reads as a path rewrite; it is nine new
build-backend manifests plus their solves, inside the story (44.4) that is also folding ~100
path-dependency sites. **Fix:** say so in AD-7's Rule (it is the load-bearing cost of the AD),
and consider whether "a `pixi.toml` per `django-*`" deserves its own story under CAP-2 —
cutover.md already forbids blending 44.4 and 44.5, and this is comparable in size.

---

## LOW

- **L-1 — AD-1 has no detector.** "No `local-recipes` history" is checkable:
  assert `git rev-list --count HEAD == 1` at foundry's first commit, and assert the archive SHA
  in the manifest matches `rxm7706/local-recipes`'s final `main`. Add to 44.3/44.10 done-when.
- **L-2 — AD-11's `frozen-path-changed` detector is named but unowned.** Which station owns it,
  which repo runs it, and what it does when a sanctioned CFE retro (AD-11 permits those) touches
  a frozen path. Also: "`local-recipes` accepts only CFE retros … and hygiene" leaves the
  `maintenance`-label + `environment.yaml` sync rituals (CLAUDE.md's always-on PR gates) live in
  the archive for the whole interval — worth one sentence saying they stay until 44.10.
- **L-3 — "Phase n ↔ Story 44.(n+3)" is a formula that does not hold.** 44.1 and 44.2 have no
  phase; the mapping is only true for phases 0–6. Replace with the companion's table reference.
- **L-4 — Manifest artifact format.** `docs/foundry/manifest.md` `[ASSUMPTION: location]` is a
  markdown table that AD-2 makes review-blocking and AD-10 makes CI-asserted. Machine-readable
  primary + rendered markdown view (see C-1's fix).
- **L-5 — Island workspace name `pyforge-factory` `[ASSUMPTION]`.** State the knock-on: several
  env vars are `$PIXI_PROJECT_ROOT`-derived (`CONDA_BLD_PATH` at `pixi.toml:74,85`,
  `OSX_SDK_DIR`, `MINIFORGE_HOME`), so the island's project root silently re-homes them (H-2).
- **L-6 — `src/prototype/` is unrouted.** It exists and is tracked; the Deferred row names
  `src/ides/ src/sentinel/ src/domains/` scaffolding but not this one. One manifest row.

---

## Checkpoint scorecard

| # | Checkpoint | Verdict |
|---|---|---|
| 1 | Fixes the real divergences for Epic 44's ten stories | **Partial** — the layout divergences are fixed; the uncovered ones are code-constant depth (C-2), repo-identity strings (H-1), task placement (H-2), the CFE marker/wrapper tier (H-3), the persona + SKF tier (H-4), and the control plane (H-5) |
| 2 | Every Rule enforceable and actually preventive | **Partial** — AD-1/8/9/10/11 need named detectors or a restated premise (L-1, M-3, M-7, L-2); AD-2's is not derivable from its stated source (C-1); AD-4's is not implementable as literally written (H-3) |
| 3 | Deferred rows cannot let two units diverge | **No** — `environment.yaml` (M-6) and `config/` vs `conf/` (M-5) both can; the runtime-state row's premise ("no tracked path moves") is correct (0 tracked files under `.claude/data/`) |
| 4 | Named tech verified-current | **Partial** — pixi 0.78.0, conda-build, conda-smithy verified; `rattler-build 0.72.2` is wrong (M-1); env count wrong (M-2); `.cursor/skills` unverified and absent (M-4) |
| 5 | Ratifies rather than contradicts the brownfield | **No** — the pap:AD-2 row asserts a zero-import boundary the host already breaks in 8 places, and miscounts the Containerfile drift 5 vs 10 (C-3) |
| 6 | Covers CAP-1..7 | **Yes for placement, partial for success criteria** — CAP-3's and CAP-6's success tests are string-level and no AD owns strings (H-1) |
| 7 | No new AD weakens an inherited one | **One collision** — AD-5 vs canopy AD-17 (SKF is the writer; its output shape and shared export manifest defeat the symlink model) (H-4); AD-7 vs pap:AD-2 needs a stated conflict note (C-3) |
| 8 | Every owned dimension decided/deferred/open — esp. the operational envelope | **No** — visibility, secrets, branch protection, environments and the rest of `.github/` are unaddressed (H-5) |

## Suggested minimal delta for iteration 2

1. **AD-2** — enumerator vs annotation, prefix rules + leaf overrides, machine-readable artifact,
   `manifest-coverage` detector, Structural-Seed completeness rule (C-1, H-6, L-4).
2. **AD-6** — add the code-constant clause + `fixed-depth-root-walk` detector (C-2).
3. **AD-7 + Inherited table** — correct 5→10, split the `pyforge-steward` COPY out, add the
   "Conflict, not override — pap:AD-2" paragraph (C-3, M-9).
4. **New AD-13** — one repo-identity rename, detector-guarded; OQ `estate-env-name` (H-1).
5. **New AD-14** — declared control plane (visibility, secrets by name, branch protection,
   environments); OQ `foundry-visibility` binding `actions-minutes` (H-5).
6. **AD-3 / AD-4 / AD-5 / AD-12** — task-placement rule; marker-based CFE root + wrapper-tier OQ;
   installer-*written* vs estate-*authored* carve-out + SKF target; widen the move unit to
   `_bmad-output/**` and `docs/governance/**` (H-2, H-3, H-4, H-6).
7. **Stack + counts** — rattler-build 0.75.0, env count, linter workflow enumeration (M-1..M-3).
