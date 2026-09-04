---
review-of: ../ARCHITECTURE-SPINE.md
lens: adversarial-pairs
reviewer: independent adversarial reviewer (read-only pass)
date: "2026-09-04"
spine-iteration: 1
---

# Adversarial pair review — python-foundry-cutover spine

**Verdict.** The spine's twelve ADs are internally coherent but under-partitioned for ten
independent builders: thirteen concrete story pairs each obey every AD to the letter and still
build incompatibly — four of them CRITICAL, and the worst is that AD-2's derivation source
(`scripts/spec_surface_check.py`'s spec→surface map) is structurally blind to ~3,500 of the
tracked files the cutover has to route, and many-to-many where it is not blind.

**Method.** Each pair assumes two different agents, each reading only `ARCHITECTURE-SPINE.md`
plus its own row of the Epic-44 story table in
`../../../specs/spec-python-foundry-cutover/cutover.md`. Every claim below is verified against
the live `rxm7706/local-recipes` tree at review time; file paths and line numbers are cited so
the operator can re-check without re-deriving.

**Tier counts.** CRITICAL 4 · HIGH 4 · MEDIUM 5.

---

## PAIR 1 — 44.1 (manifest) × 44.5 (skills/BMAD/decks/dreams) — CRITICAL

**44.1 does, obeying AD-2:** derives the manifest from `git ls-files` × the spec-surface
classification, "one row per tracked path", each resolving to exactly one of {target path,
`stays`, `dies`}. The classification it is told to use is
`scripts/spec_surface_check.py`'s spec→surface globs.

**44.5 does, obeying AD-5 + AD-12:** moves `.claude/skills/<estate skill>` into
`skills/{stations,personas,domain}/`, and `_bmad/`, `_bmad-output/projects/`, `docs/dreams/`
"as one unit".

**The incompatibility.** The spec-surface map does not classify those paths at all — it
*exempts* them. `scripts/spec_surface_allowlist.txt` blanket-allowlists
`.claude/**` (line 3), `_bmad/**` (10), `_bmad-output/**` (11), `docs/dreams/**` (4),
`.github/**` (61), `AGENTS.md` (65), `CLAUDE.md` (66), `archive/**` (9), `tests/**` (52),
`azure-pipelines.yml` (54), `build-locally.py` (55), `conda-forge.yml` (57),
`conda_build_config.yaml` (58), `.ci_support/**` (74), `.scripts/**` (64), `.gitignore` (71).
That is 1,113 tracked files under `.claude/skills`, 1,424 under `_bmad-output`, 357 under
`_bmad`, 128 under `docs/dreams`, plus the entire inherited CI surface — every one of them
*ungoverned by any spec*, and every one of them a path 44.5, 44.7 or AD-8 must route.

A 44.1 agent obeying AD-2 to the letter emits rows only where a spec surface claims the path,
so `.claude/skills/**`, `_bmad*/**` and `docs/dreams/**` get **no rows**. A 44.5 agent then hits
AD-2's own closing sentence — "A move without a manifest row is a review-blocking finding" —
and is blocked from doing the one thing its story exists to do. The other branch is worse: 44.1
improvises destinations for ~3,500 allowlisted paths, 44.5 improvises its own, and the two
diverge silently because nothing compares them.

**AD to add — AD-2a (row source vs. owner).** The manifest's *row set* is `git ls-files` in
full; the spec-surface map supplies the *owner* column only, and never gates row existence. The
allowlist is a manifest **input**, not an exclusion: every allowlisted path is enumerated with an
explicit destination and an explicit owning story. 44.1's exit gate becomes
`count(manifest rows) == count(git ls-files)`, asserted, not asserted-by-narrative.

---

## PAIR 2 — 44.1 (manifest) × 44.8 (working set) — CRITICAL

**44.1 does, obeying AD-2:** "one row per tracked path … No path may resolve to two."
`recipes/**` is claimed by `pyforge-mason/.../spec-fleet-stewardship/SPEC.md` (`surface:` line 7),
so 44.1 routes the 14,378 tracked `recipes/**` files to `stays` (the archive keeps the universe;
AD-10 forbids copying it).

**44.8 does, obeying AD-10:** admits a recipe into `factory/recipes/` "only through a manifest
row whose `reason` is one of `in-flight`, `sole-maintainer`, `referenced-by-spec`."

**The incompatibility.** The classification is **many-to-many and has no arbiter.** The same
`recipes/` paths are claimed a second and third time:
`pyforge-steward/.../spec-pyforge-unifying-strategy/SPEC.md` claims `recipes/openfeature-*/**`,
`recipes/cachebox/**`, `recipes/liquibase/**`; `spec-bmad-suite-metapackage/SPEC.md` claims
`recipes/bmad-suite/recipe.yaml` and `.../suite-members.yaml`. `pyforge.doctor.sources.chain`
emits no overlap finding — I checked; multi-claim is silent and legal today. So
`recipes/openfeature-flagd/**` is simultaneously `stays` (mason's blanket claim → archive) and
`referenced-by-spec` (steward's explicit claim → `factory/recipes/`). Both agents are obeying
their AD; AD-2's "no path may resolve to two" is a *property* the spine asserts but the
derivation cannot produce.

**AD to add — AD-2b (precedence + ambiguity is a row kind).** Most-specific glob wins; equal
specificity is not resolved by either story but emitted as an `ambiguous` row that 44.1 must
surface and the operator must resolve before the consuming phase flips out of `blocked`
(AD-9). Silent selection by either agent is a review-blocking finding.

---

## PAIR 3 — 44.4 (fold packages) × 44.7 (factory island) — CRITICAL

**44.4 does, obeying AD-6 + its done-when:** rewrites `src/shared/packages/<x>` →
`src/packages/<x>` across ~100 `pixi.toml` path-dependency sites (verified: 103 `src/shared/packages`
occurrences in `pixi.toml`), and proves it with "station envs solve."

**44.7 does, obeying AD-3:** "The estate lock carries no solver-farm tooling (`rattler-build`,
`conda-smithy`, `conda-build`, `conda-forge-pinning`); those live in the island." So it strips
them from the root `pixi.toml` and re-declares them in `factory/pixi.toml`.

**The incompatibility.** `[feature.pyforge-warden.dependencies]` (`pixi.toml:1961`) carries
`py-rattler-build = ">=0.72.2"` (line 1968) and `conda-build = ">=25.3.1"` (line 1969) with the
in-file comments *"test-only differential-oracle for extract/recipe_v1.py"* and
*"…for extract/meta_v0.py"* — and `pyforge-warden` is a lean `no-default-feature` **estate** env
(`pixi.toml:721`). 44.7 obeying AD-3's literal ban removes `conda-build` from the estate and
warden's `extract/meta_v0.py` oracle tests lose their comparator; 44.4's "station envs solve"
gate has already gone green against the pre-strip lock. Neither agent is wrong.

The same ambiguity bites a second way: AD-7 requires every `src/packages/*` to be a pixi-build
workspace member, which needs `pixi-build-python` (`pixi.toml:658, 1497`) and
`pixi-build-rattler-build` (`659, 1495`) in the *estate*. `pixi-build-rattler-build` shares
AD-3's banned prefix, and `pixi.toml:1494` declares a real `rattler-build >=0.75.0` alongside it.
A 44.7 agent pattern-matching on AD-3's four names strips the build backend AD-7 depends on.

**AD to tighten — AD-3.** Define solver-farm tooling by **role** (tooling that *produces or
lints conda recipes*), then enumerate the estate exemptions by name and reason: pixi build
backends (`pixi-build-python`, `pixi-build-rattler-build`, `pixi-build-cmake`, `pixi-build-rust`)
and test-only differential oracles (`conda-build`, `py-rattler-build`, `py-rattler` in
`feature.pyforge-warden`). Name the single story that owns each removal, and make "no estate env
loses a dependency it tests against" an explicit 44.7 gate, not a 44.4 assumption.

---

## PAIR 4 — 44.3 (open foundry) × 44.6 (CFE home) — CRITICAL

**44.3 does, obeying AD-1:** "Foundry's first commit carries no `local-recipes` history (no
`filter-repo`, no subtree import)."

**44.6 does, obeying its done-when:** "no `MASON_CFE_ROOT` resolves to `local-recipes`; **CFE
surface + rebuild guards pass**."

**The incompatibility.** Both guards derive their verdict from **git history**, and foundry has
none. `scripts/cfe_rebuild_guard_check.py` defaults its range to *"the Story-6.1 landing merge,
PR #570"* (docstring, clause (b)) — a SHA that cannot exist in foundry.
`scripts/mason_cfe_surface_check.py` derives its range from `git log -- <mason path>` and
documents its own failure mode verbatim: *"exit … 2 could not run — `git log` itself failed …
or it succeeded but found zero commits (a wrong cwd/branch, or a shallow/partial clone missing
the range, reads the same as 'clean' unless this is called out separately; it is never treated
as proof of cleanliness)."* In foundry, `git log -- src/packages/pyforge-mason` returns the
single fold commit or nothing. 44.6's gate therefore either hard-errors (exit 2) or passes
**vacuously**, retiring the FR-45/AD-15 guarantee — "Mason never modifies the CFE surface" —
at exactly the moment CFE moves. Both agents obeyed every AD.

**AD to add — AD-1a (history-derived guards need a foundry epoch).** Any detector whose verdict
is a scan of commit history declares the AD-1 first commit as its foundry-era range floor, and
a zero-commit range is exit 2, never exit 0. 44.6's gate is re-expressed as a **path**
conformance assertion over the new CFE home plus a re-baselined guard state, and 44.3 must ship
that epoch marker (the pinned first-commit SHA) as an output the guards can read.

---

## PAIR 5 — 44.5 (skills move) × 44.6 (CFE home) — HIGH

**44.5 does, obeying AD-5:** "Estate-authored skills live only under
`skills/{stations,personas,domain}/<x>/SKILL.md`. `.claude/skills/<x>` and `.cursor/skills/<x>`
are relative symlinks." `conda-forge-expert` is an estate-authored skill (canopy AD-17 names it
explicitly, with a `[MANUAL]`-sections exception), so 44.5 moves it and symlinks it.

**44.6 does, obeying its story:** "authoritative **skill / scripts / tools** →
`skills/domain/conda-forge-expert`."

**The incompatibility.** Three problems at once, all verified:

1. **Two owners of one directory.** Both stories legitimately claim
   `.claude/skills/conda-forge-expert` (340 tracked files). AD-5 says 44.5 moves every estate
   skill; the cutover table says 44.6 moves this one. 44.5 runs first, so 44.6 arrives to find
   the skill already at `skills/domain/conda-forge-expert` — or, if 44.5 read AD-5's
   *"Installer-owned skills stay real directories"* narrowly and skipped it, arrives to find
   `.claude/skills/` already symlink-only and no home for a real directory.
2. **The siblings have no owner at all.** The CFE surface is *four* trees, not one:
   `.claude/skills/conda-forge-expert/` (340 files), `.claude/scripts/conda-forge-expert/`
   (63 files), `.claude/tools/conda_forge_server.py`, and the gitignored
   `.claude/data/conda-forge-expert/`. No AD says whether `skills/domain/conda-forge-expert`
   *contains* `scripts/`, `tools/` and `data/`. `.claude/tools/` is a shared directory —
   `conda_forge_server.py` sits beside `gemini_server.py` and `mcp_call.py`, which are not CFE —
   so "move tools" has no unambiguous meaning.
3. **Both CFE detectors fail open.** `scripts/mason_cfe_surface_check.py:56-60` and
   `scripts/cfe_rebuild_guard_check.py:111-116` each hardcode the CFE surface as the literal
   triple `.claude/skills/conda-forge-expert/`, `.claude/scripts/conda-forge-expert/`,
   `.claude/tools/conda_forge_server.py`. After either story, no future commit touches those
   prefixes, so `unsanctioned-cfe-touch` and `unmirrored-retro` become unreachable and both
   detectors report **clean**. A guard that cannot fire is worse than one that is removed.

Unassigned collateral: `pixi.toml` carries **76** `.claude/scripts` references (task command
lines) and **9** `.claude/skills` references. AD-6 gives 44.4 only the *path-dependency* sites.

**AD to add — AD-4a (the CFE cell is one unit with one owner).** Name the CFE surface as a
single migratable unit — skill tree + wrapper scripts + the MCP server module + its gitignored
data root — assign it wholly to 44.6, and have AD-5 explicitly except it from 44.5. Add: every
detector whose surface is a path literal is a manifest consumer, rewritten in the same story
that moves the surface, with a post-move assertion that the detector still matches a non-empty
set.

---

## PAIR 6 — 44.4 (fold packages) × 44.5 (personas move) — HIGH

**44.4 does, obeying AD-6:** retargets `five_tier._packages_root` — AD-6's consumer list names
exactly that function.

**44.5 does, obeying the companion's Five-faces table:** moves personas to
`skills/personas/<station>/`; its story line reads "skills → `skills/` (`stations/`, `personas/`,
`domain/`)".

**The incompatibility.** `src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py`
has **four** path literals, not one. `_packages_root` (line 73) is the one AD-6 names.
`detect_tiers` additionally hardcodes `repo_root/.claude/skills/pyforge-<station>` (skill tier),
`repo_root/.claude/skills/bmad-agent-<station>/SKILL.md` (persona tier), and
`repo_root/.claude/skills/conda-forge-expert/SKILL.md` (mason's skill tier). 44.5 moving the
eight `bmad-agent-*` persona skills drops eight persona tiers, taking the canopy AD-14 roster
from 40/40 to 32/40 and reddening `.github/workflows/pyforge-steward-five-tier.yml` — after
44.4, the only story licensed to touch `five_tier.py`, has already merged.

The spine also **contradicts the companion here**: AD-5 says "Installer-owned skills (`bmad-*`,
`skf-*`) stay real directories where their installer writes", and every persona is a `bmad-agent-*`
skill. Read AD-5, personas do not move and `skills/personas/` is empty — contradicting the
companion's Five-faces table and the target tree. Read the companion, they move and five_tier
breaks. Both readings are defensible from the artifacts as written.

**AD to tighten — AD-5 + AD-6.** AD-5 must state which is authoritative for `bmad-agent-*`:
installer-owned real directory, or `skills/personas/` with an adapter. AD-6's consumer-rewrite
list must be **split per story** (a table: consumer path → owning story), not accumulated on
44.4; `five_tier.py`'s skill/persona/mason literals belong to 44.5 and 44.6, not 44.4.

---

## PAIR 7 — 44.4 (rewrites `surface:` globs) × 44.5 (moves the surfaces) — HIGH

**44.4 does, obeying AD-6:** rewrites "Spec `surface:` globs" and "`marshal-policy.toml` globs"
from manifest rows in the same story. Verified scope: **47** `SPEC.md` files reference
`src/shared/packages`; **8** `marshal-policy.toml` files do (one per station project, e.g.
`_bmad-output/projects/pyforge-steward/planning-artifacts/marshal-policy.toml` repeats
`"src/shared/packages/pyforge-steward/**"` at ~20 sites).

**44.5 does, obeying AD-5 + AD-12:** moves `.claude/skills/**` and `presentations/**`.

**The incompatibility.** **18** `SPEC.md` files declare `.claude/skills` surfaces, and
`presentations/**` is claimed by `pyforge-herald/.../spec-pyforge-herald/SPEC.md` (763 tracked
files under `presentations/`). Those surfaces move in **44.5**, which no AD gives a glob-rewrite
mandate. AD-6's rewrite clause is scoped to the packages fold. Result: after 44.5, 18 specs
declare globs matching nothing, and the entire moved skills + decks tree becomes ungoverned →
`pyforge.doctor.sources.chain::gather_spec_surface` fires `no spec surface and no allowlist
entry` for thousands of files.

Second, unowned by *anyone*: **`scripts/.spec-surface-baseline.json`** (979,041 bytes) is keyed
`<project>/<spec>` → `{files: {path: hash}, memlog: …}`, with literal
`src/shared/packages/pyforge-atlas/conf/base/catalog.yml` and
`.github/workflows/kedro-viz-publish.yml` entries. Every phase invalidates it, and **no story
owns the re-stamp**. Worse, the stamper reads the *working tree* via `git ls-files`
(`scripts/spec_surface_check.py`, `tracked_files()`), so a mid-move stamp bakes in a lie —
this repo already carries two memory entries about exactly that footgun.

**AD to add — AD-2c (surfaces and the baseline are per-phase deliverables).** Every move story
rewrites the `surface:` globs and `marshal-policy.toml` globs for the paths *it* moves, and
re-stamps with `python scripts/spec_surface_check.py --write-baseline --spec <NAME>` — scoped,
never bare — from a clean, fully-staged worktree. A phase whose spec-surface verdict is not
green at merge is not done.

---

## PAIR 8 — 44.5 (moves `_bmad-output/`) × 44.6 / 44.9 / 44.10 (still write the ledger) — HIGH

**44.5 does, obeying AD-12:** "`_bmad/`, `_bmad-output/projects/` and `docs/dreams/` move in
44.5 as one unit."

**44.6, 44.9, 44.10 do, obeying AD-9 and the repo's own conventions:** each is a ledger-tracked
story that must write `sprint-status-ledger.yaml`, stamp its Spec's `.memlog.md`, and — per the
tracked-story-spec convention — promote its story spec into `planning-artifacts/specs/`.

**The incompatibility.** AD-11 says "A manifest row marked `moved` freezes its source path in
`local-recipes` (detector `frozen-path-changed`)." After 44.5, all 1,424 tracked
`_bmad-output/**` files are frozen in local-recipes and live in foundry. But **the spine never
says which repo the remaining Epic-44 stories write their ledger rows in**, and the
`loop-home-cutover-timing` question — "re-provision the eight loop homes before 44.5 … or
after?" — is left **open**. A 44.6 agent running from a loop home still cloned from
local-recipes writes its `done` row there (tripping `frozen-path-changed`); a 44.6 agent
re-provisioned against foundry writes it there, and the two Epic-44 ledgers diverge with no
reconciliation story. AD-12 lists loop-home re-provisioning as a *fact* ("are re-provisioned")
with no owning story and no instant.

**AD to add — AD-12a (the ledger cutover instant).** 44.5's merge is the ledger cutover instant:
after it, every Epic-44 ledger row, memlog stamp and promoted story spec is a **foundry** write,
and local-recipes' `_bmad-output/**` is frozen with no exception. Loop-home re-provisioning is an
in-scope task **of 44.5**, not an open question — and 44.5's done-when adds "the eight
`~/.bmad-loops/*` homes resolve to the foundry remote", asserted.

---

## PAIR 9 — 44.3 (estate CI) × 44.7 (island CI) — MEDIUM

**44.3 does, obeying AD-8 + its story:** creates the foundry with "estate-only CI"; "env export
automated or not carried (R-17a)". At that moment `factory/` does not exist.

**44.7 does, obeying AD-8:** "Estate workflows carry `paths-ignore: [factory/**]`; island
workflows carry `paths: [factory/**]`."

**The incompatibilities (three).**

1. **Retrofit ownership.** A 44.3 agent writing estate workflows for a repo with no `factory/`
   legitimately omits `paths-ignore` — there is nothing to ignore, and today's estate workflows
   already carry rich `paths:` filters (`platform-ci.yml:79,99`, `coverage-gates.yml:15,22`,
   `pyforge-core.yml:8,16`, `pyforge-steward-five-tier.yml:8,17`,
   `pyforge-steward-fresh-clone.yml:9,18`, `cfe-regression-net.yml:40,50`,
   `kedro-viz-publish.yml:32`). 44.7 then has to retrofit ~15 workflows it does not own, or
   AD-8's cost-isolation invariant is simply false in the shipped repo.
2. **`environment.yaml` genuinely has two legal answers.** AD-8 says it "is produced by a
   workflow step or dropped" — an explicit either/or with no arbiter, and the spine's own
   Deferred table defers the decision to "44.3 writes the first estate workflow". Meanwhile the
   *content* argues the other way: the live `environment.yaml` is the **`build`** env export and
   carries `conda-build`, `conda-forge-ci-setup`, `conda-forge-pinning`,
   `rattler-build-conda-compat` — island content under AD-3. 44.3 can ship an automated estate
   export; 44.7 can assume it died with the linter. Both obey.
3. **AD-8's `dies` list is a count, and the count is wrong.** "The staged-recipes linter (three
   workflows)" — there are four (`staged-recipes-linter.yml`,
   `reusable-staged-recipes-linter.yml`, `reusable-staged-recipes-linter-selftest.yml`,
   `linter_issue_comment.yml`) **plus** `.github/workflows/scripts/linter.py` and
   `linter_issue_comment.py`, and `linter.py:64-79` is where the `environment.yaml` sync check
   actually lives. A story deleting "three workflows" leaves the linter's Python behind.

**AD to tighten — AD-8.** Replace every count with a manifest-derived file set (AD-2 rows carry
`dies`; AD-8 cites the rows, never a number). Make the `environment.yaml` decision a **44.3
output recorded in the manifest**, binding on 44.7. Add: `paths-ignore: [factory/**]` is present
on every estate workflow **from 44.3 onward**, whether or not `factory/` exists yet — an
inert filter is cheaper than a retrofit across a story boundary.

---

## PAIR 10 — 44.4 (moves pyforge-mason) × 44.6 (retargets the chain) — MEDIUM

**44.4 does, obeying AD-6:** `src/shared/packages/pyforge-mason` → `src/packages/pyforge-mason`,
import and distribution names unchanged.

**44.6 does, obeying AD-4:** "`MASON_CFE_ROOT` (flag → env → cwd walk, `pyforge/mason/resolve.py`)
resolves to `skills/domain/conda-forge-expert`."

**The incompatibility — AD-4 silently changes the variable's *type*.** In live code,
`MASON_CFE_ROOT` is a **repo root**, not a skill directory:
`src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py` defines
`_CFE_MARKER = Path(".claude/scripts/conda-forge-expert")` and the walk returns the *candidate
root* containing it; `cfe.py` then joins
`root / ".claude" / "scripts" / "conda-forge-expert" / _CFE_SCRIPTS[...]` (lines 839 and 1214).
A 44.6 agent obeying AD-4 literally sets the resolution target to the skill dir, and every
`cfe.py` join becomes `skills/domain/conda-forge-expert/.claude/scripts/conda-forge-expert/<script>`
— nonexistent. And because 44.6 also removes `.claude/scripts/conda-forge-expert/`, the
**cwd-walk step matches nothing anywhere in foundry**, so `resolve_cfe_root` returns
`STEP_NOT_FOUND` for any bare `mason recipe build`. That makes AD-4's own stated prevention —
"`MASON_CFE_ROOT` pointing back at the archive" — *more* likely, since the operator's first
workaround for a not-found chain is exporting a path they know exists: the archive clone.

Ownership is split with no seam: 44.4 owns the package's move, 44.6 owns the "retarget", and
**neither owns `_CFE_MARKER` plus the two `cfe.py` join sites plus `errors.py`'s
`CfeUnresolvedError._MESSAGE`**, which the code's own docstring flags as a deliberate
two-place literal duplication that must change together.

**AD to tighten — AD-4.** State that `MASON_CFE_ROOT` remains a **root**, name the new marker
path (`skills/domain/conda-forge-expert/scripts/`, or whatever 44.6 chooses) as a first-class
manifest row, enumerate the four literal sites (`resolve.py::_CFE_MARKER`, `cfe.py` ×2,
`errors.py`) as consumers, and assign them to 44.6. Add a 44.6 gate: from a clean foundry
checkout with no flag and no env var, `mason doctor` reports `step: cwd-walk`, not `not-found`.

---

## PAIR 11 — 44.1 (creates the manifest) × every later story (mutates rows) — MEDIUM

**44.1 does, obeying AD-2:** generates the manifest — location `docs/foundry/manifest.md`,
tagged `[ASSUMPTION: location]` in the structural seed.

**44.4–44.10 do, obeying AD-2:** each "consumes the rows for its phase and marks them `moved`
with the foundry commit."

**The incompatibility.** Two owners, no concurrency shape. The order line makes **44.6 ∥ 44.7**
explicit — two agents appending `moved` + `foundry_commit` to a shared Markdown table at the
same time, with no lock, no per-phase shard, and no merge convention. Worse, they write it in
*different repos*: the manifest's `source_sha` column refers to local-recipes, but by 44.6 the
estate lives in foundry (AD-11: "every estate change lands in foundry first"), so the manifest
is simultaneously a local-recipes artifact and a foundry artifact. This repo has already paid
for this exact bug once: `scripts/spec_surface_check.py` needed an advisory `flock` on a sidecar
plus atomic `os.replace` (Story 12.5) to stop two concurrent `--write-baseline` runs from
clobbering each other — a Markdown table with two concurrent appenders has strictly weaker
guarantees.

**AD to add — AD-2d (the manifest is machine-readable, sharded, single-homed).** The manifest is
a structured file (JSON/YAML), lives in exactly one repo named by the AD, and is either sharded
per phase (`docs/foundry/manifest/phase-<n>.yaml`) or append-only under a lock. Concurrent
phases never write the same shard. `[ASSUMPTION: location]` is promoted to a decision before
44.1 flips out of `blocked`.

---

## PAIR 12 — 44.5 / 44.6 (move `.claude/**`) × nobody (gitignored + `.gitignore` itself) — MEDIUM

**Both stories do, obeying AD-2:** treat the manifest as authoritative — and AD-2 is explicitly
"one row per **tracked** path."

**The incompatibility.** `.gitignore` carries path literals keyed to the very trees that move,
and none of them is a tracked path, so none gets a row:

- `.claude/skills/conda-forge-expert/pypi_conda_mappings/unified.json` and its two siblings
  (`.gitignore:716-718`) — ignore rules for CFE's mapping caches.
- `.claude/data/` (line 721) — the 11 GB CFE runtime state root.
- A **negated un-ignore**: `!.claude/skills/conda-forge-expert/tests/fixtures/error_logs/`
  and `!.../**/*.log` (lines 885-886), added after an incident where a broad ignore
  *"silently swallowed the conda-forge-expert failure-analyzer's own `.log` test [fixtures]"*.

Once `.claude/skills/conda-forge-expert` is a symlink or gone, the ignores stop matching (a
mapping cache becomes untracked noise, or worse, gets committed) and the un-ignore is dead
(the fixtures get re-swallowed — the exact regression the negation exists to prevent).
`.gitignore` itself is allowlisted as "repo plumbing" (`spec_surface_allowlist.txt:71`), so it
has no spec owner either. The spine's Deferred table parks `runtime-state-home` with the
reason *"Gitignored today; no tracked path moves"* — true of the state, false of the rules that
govern it.

**AD to add — AD-2e (untracked classes are routed too).** `stays` / `dies` are defined for
gitignored *classes* as well as tracked paths, and `.gitignore` is a named manifest consumer
assigned to whichever story moves the tree its rules reference. Post-move assertion: no
`.gitignore` pattern matches zero paths, and no previously-ignored runtime artifact becomes
tracked.

---

## PAIR 13 — 44.2 (document fixes) × 44.4 / 44.5 (rewrite consumer paths) × canopy AD-17 — MEDIUM

**44.2 does, per its story:** lands document fixes (R-23/R-24/R-25, `stack.md` / `convergence.md`
floor `3.12.*` → `3.14.*`) — verified to live at
`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/{stack,convergence}.md`.

**44.4 does, obeying AD-6:** "Every consumer path is rewritten from manifest rows in the same
story." `CLAUDE.md` contains a `src/shared/packages` reference and 22 `.claude/skills`
references; `AGENTS.md` contains 7.

**The incompatibility.** Three claimants and an inherited prohibition. `AGENTS.md` and
`CLAUDE.md` are the repo's cross-tool entry points, both allowlisted (no spec owner), both
full of paths that AD-5/AD-6/AD-12 invalidate — and **canopy AD-17 states: "Export is the only
write into `CLAUDE.md` / `AGENTS.md` (`skf-export-skill`)."** So a 44.4 or 44.5 agent obeying
AD-6's "every consumer path" hand-edits two files an inherited AD reserves for a compile step,
while a 44.2 agent reasonably regards documentation fixes as *its* lane and edits them too.
The spine's Inherited Invariants table cites canopy AD-17 only for "SKF compiles into `skills/`"
and asserts **"Conflict, not override — none found."** That assertion is not safe for these two
files.

**AD to add — AD-6a (the entry-point documents have one owner and one mechanism).** Name
`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursor/rules/`, `.github/copilot-instructions.md` as a
single documentation-adapter unit with one owning story, and state explicitly how AD-6's
path-rewrite obligation composes with canopy AD-17's `skf-export-skill` write monopoly — either
by excepting mechanical path rewrites from AD-17, or by routing them through a regeneration
step. Leaving it to inference guarantees two agents edit the same two files from two lanes.

---

## Cross-cutting observations (not pairs)

- **AD-2's derivation is cited three ways and is weakest exactly where the cutover is heaviest.**
  Pairs 1, 2, 7, 11 and 12 all trace back to the same root: the spec-surface map was built to
  answer *"who owns this file?"*, and the spine reuses it to answer *"where does this file go?"*
  Those are different questions, and the map is blind (allowlist), many-to-many (overlapping
  claims), tracked-only (no gitignored classes) and mutable-in-flight (baseline drift) with
  respect to the second. This is the single highest-leverage fix in the review.
- **Every hardcoded path literal in a detector is an unowned consumer.** Verified instances:
  `mason_cfe_surface_check.py`, `cfe_rebuild_guard_check.py`, `five_tier.py` (×4),
  `resolve.py::_CFE_MARKER`, `cfe.py` (×2), `.spec-surface-baseline.json` (thousands),
  `.gitignore` (×5+), `marshal-policy.toml` (×8 files), `SPEC.md` `surface:` blocks (47 + 18),
  `pixi.toml` (103 + 76 + 9). AD-6 lists seven consumer classes by name; the live count is
  materially larger. A **derived** consumer inventory (grep the manifest's source paths across
  `git ls-files`) belongs in 44.1's output, not in an AD's prose list — "derive, don't declare".
- **Three ADs' preventions are asserted but unprovable as written**: AD-4's "`MASON_CFE_ROOT`
  pointing back at the archive" (Pair 10 makes it likelier), AD-2's "a tracked path silently
  dropped" (Pair 1 makes it certain for allowlisted paths), AD-8's "the hand-run
  `environment.yaml` ritual" (Pair 9 leaves the ritual's *replacement* undecided).
- **AD-9 is the mitigating control.** Every story is `blocked` pending an operator flip, and
  44.3 / 44.9 / 44.10 additionally require confirmation at dispatch. None of the pairs above is
  a live risk *today*; all of them become live the moment two stories are flipped and dispatched
  to independent agents. The right time to close them is now, in iteration 2, not at merge.

## Suggested minimum close set before any 44.x flips to `backlog`

| Priority | New / tightened AD | Closes |
|---|---|---|
| 1 | **AD-2a** row source vs. owner (allowlist is an input) | Pair 1 |
| 2 | **AD-2b** glob precedence + `ambiguous` row kind | Pair 2 |
| 3 | **AD-3** solver-farm by role + named estate exemptions | Pair 3 |
| 4 | **AD-1a** history-derived guards need a foundry epoch | Pair 4 |
| 5 | **AD-4a** the CFE cell is one unit, one owner | Pair 5 |
| 6 | **AD-6** consumer-rewrite table, split per story | Pairs 6, 7 |
| 7 | **AD-12a** ledger cutover instant + loop homes in 44.5 | Pair 8 |
| 8 | **AD-2c / 2d / 2e** baseline re-stamp, manifest concurrency, untracked classes | Pairs 7, 11, 12 |
| 9 | **AD-8** file-set not counts; `environment.yaml` decided in 44.3 | Pair 9 |
| 10 | **AD-4** `MASON_CFE_ROOT` stays a root; name the marker | Pair 10 |
| 11 | **AD-6a** entry-point docs: one owner, vs. canopy AD-17 | Pair 13 |
