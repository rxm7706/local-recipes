# Review — Reality Check lens

- **Target:** `../ARCHITECTURE-SPINE.md` (`python-foundry-cutover`, iteration 1, 2026-09-04)
- **Lens:** Verify every committed decision was web-researched or reality-checked rather than
  asserted from training data — current library/framework versions, that each named technology
  still exists and fits, and the live defaults of any starter it leans on.
- **Reviewed:** 2026-09-04 · read-only against the live repo at
  `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes`, branch
  `chore/hygiene-spec-surface-2026-09-03`, plus conda-forge's package API and the Claude Code /
  Cursor skill docs.

## Verdict

The spine's *counting* claims about this repo are unusually good — 268 worktrees, 85 GB, 11 GB,
7,855 recipe dirs, 29 lock environments, 8 loop homes and "~100 sites" all check out to the
digit — but its *version* and *pattern* claims were largely copied from stale in-repo comments
rather than checked against the lock or the web: the Stack table's rattler-build version names
the wrong package, AD-7's "five COPY lines" is ten, AD-5's key assumption is documented fact on
one IDE and an undocumented unknown on the other (whose docs also say the second adapter tree
may be unnecessary), and AD-2's derivation source provably cannot classify 20% of the tracked
tree.

---

## CRITICAL

### C-1 — AD-2's derivation source cannot produce the manifest it specifies

**Claim.** "The manifest is generated from `git ls-files` × the spec-surface classification
(`scripts/spec_surface_check.py`'s spec→surface globs), one row per tracked path, each resolving
to exactly one of {target-tree path, `stays`, `dies`}."

**Evidence.** Measured with the real parser (`spec_surface_check.tracked_files()`,
`parse_surface()`, `glob_to_re()`), not an ad-hoc regex:

| Quantity | Measured |
|---|---|
| tracked paths (`git ls-files`) | 24,858 |
| spec files matching `SPEC_GLOB` | 124 |
| distinct `surface:` globs across them | 219 |
| tracked paths matched by ≥1 surface glob | 19,807 |
| **tracked paths matched by none** | **5,051 (20.3%)** |

Largest unclassified blocks by top-level dir: `.idea/` 1,950 · `_bmad-output/` 1,413 ·
`.claude/` 744 · `_bmad/` 356 · `archive/` 219 · `docs/` 191 · `scripts/` 32 · `tests/` 32 ·
`.github/` 31 · `.ci_support/` 18 · `_skf-learn/` 18 · `src/` 7.

Two independent defects:

1. **Coverage.** One fifth of the tracked tree has no surface glob at all, so no row can be
   derived for it — including nearly everything AD-12 moves (`_bmad/`, `_bmad-output/`) and
   everything AD-5 moves (`.claude/`).
2. **Category error, worse than the coverage gap.** `spec_surface_check.py` answers *"which spec
   governs this path"*. It emits a spec name and a content hash (`_live_state()` →
   `.spec-surface-baseline.json`, keyed `pyforge-atlas/spec-...`). It has no notion of a
   destination. Even for the 19,807 covered paths the classification yields a governing spec, not
   one of `{target path, stays, dies}` — the mapping AD-2 asserts does not exist in the source it
   names.

**Fix.** Rewrite AD-2's rule so the derivation is honest: `git ls-files` is the *row generator*
(every tracked path gets a row, guaranteeing nothing is dropped — that part is sound and worth
keeping); the *destination* comes from an explicitly-authored, reviewed routing table of
prefix rules, with spec-surface membership as an at-most-advisory annotation. Add an assertion
that Story 44.1's output has zero rows with an unset destination, so the 5,051 are forced into
review rather than silently defaulted. See also M-4 (existing prior art).

---

## HIGH

### H-1 — The Stack table's rattler-build version names the wrong package

**Claim.** Stack row: `rattler-build (island) | 0.72.2 (today's lock)`.

**Evidence.** `pixi.lock` resolves **rattler-build 0.75.0**
(`rattler-build-0.75.0-h74d5219_0`, `-he94b42d_0`, `-hf01adef_0`). `0.72.2` in the lock belongs to
`py-rattler-build` (`py-rattler-build-0.72.2-py310h701b438_1` …) — a different package (Python
bindings). `pixi.toml:1494` declares `rattler-build = ">=0.75.0"` and `:1515` declares
`py-rattler-build = ">=0.72.2"` as separate lines. conda-forge's current release is **0.75.0**
(0.75.0 > 0.74.0 > 0.73.0 > 0.72.2), so the cited number is also three minor releases stale.

Likely provenance, which is the lens's whole point: `0.72.2` also appears in an unrelated stale
`pixi.toml` header comment — *"pixi (through 0.72.2) has no such key"* — i.e. a **pixi** version,
not a rattler-build one. The number was carried across from a comment rather than read off the
lock or the web.

**Fix.** `rattler-build (island) | >=0.75.0` (manifest floor) / `0.75.0` (lock, = current
conda-forge release). Add `py-rattler-build 0.72.2` as its own row if the island needs the
bindings, and mark every Stack cell as either *floor* or *resolved* (see M-6).

### H-2 — AD-7's "five `COPY src/shared/packages/...` lines" is ten

**Claim.** AD-7 Prevents: "the five `COPY src/shared/packages/...` lines"; the inherited-invariant
table repeats "the Containerfile's five `COPY src/shared/packages/...` lines" against pap:AD-9.

**Evidence.** `grep -c '^COPY src/shared/packages' src/platform/Containerfile` → **10**, at lines
163, 165, 167, 170, 171, 172, 173, 174, 175, 176:

```
163 django-pyforge/src/django_pyforge      170 pyforge-steward/src/pyforge
165 django-warden/src/django_warden_fabric 171 django-doctor/src/django_doctor_portal
167 django-atlas/src/django_atlas_portal   172 django-herald/src/django_herald_portal
                                           173 django-marshal/src/django_marshal_portal
                                           174 django-mason/src/django_mason_portal
                                           175 django-scribe/src/django_scribe_portal
                                           176 django-steward/src/django_steward_portal
```

Also unmentioned: a `COPY . /app` at line 78 in the **builder** stage, which already drags the
whole `src/shared/` tree into the build context — AD-7's rule ("the Containerfile has no
`COPY src/packages`") is unsatisfiable until that line is addressed too.

Two shapes, not one: nine are **django portal apps**; line 170 (`pyforge-steward/src/pyforge` →
`/app/pyforge`) is a **library** copy added for Story 23.1 ("atlas board imports
`pyforge.steward.dashboard`"). Removing it is a different piece of work from removing a portal
COPY, and it is the one that most directly touches pap:AD-2 (host never imports `pyforge.*`).

**Fix.** Correct both occurrences to ten, split the rule into "nine django portal COPYs" and "one
`pyforge-steward` library COPY (line 170) + the builder-stage `COPY . /app` (line 78)", and
re-size Story 44.4 accordingly.

### H-3 — AD-7 presents the pixi-build member pattern as proven where it is least proven

**Claim.** "Each `src/packages/*` carries its own `pixi.toml` as a pixi-build workspace member
(the pattern already live for `pyforge-warden`)."

**Evidence.** The claim understates the current state in one direction and overstates it in the
one that matters:

- **All ten** `pyforge-*` packages already ship a member manifest with a `[package]` table —
  atlas, core, doctor, herald, marshal, mason, scribe, steward, testing-kit, warden. Not just
  warden. (`for p in src/shared/packages/*/; do [ -f "$p/pixi.toml" ]; done`.)
- **None of the `django-*` packages do** — and the django packages are exactly the ones the ten
  COPY lines in H-2 exist for. AD-7's rule therefore requires **net-new member manifests for
  seven django distributions that have never been built this way**, presented as an already-live
  pattern with no story sizing for it.
- The pattern's own reality-check is missing: `preview = ["pixi-build"]` is still a **preview**
  flag in pixi 0.78, and the root manifest carries a live warning that a `[workspace] members`
  key does not exist in pixi (workspace membership is expressed as path dependencies). The spine
  never states that AD-7 depends on a preview feature.
- Warden's own member manifest declares `python = ">=3.12"` in both `[package.host-dependencies]`
  and `[package.run-dependencies]`, and the lock resolves `py-rattler-build …py310…` builds —
  against canopy:AD-23's "one interpreter `3.14.*`", which the spine lists as inherited and
  unchanged.

**Fix.** Restate as "live for the ten `pyforge-*` packages; **not** live for the seven `django-*`
packages, which Story 44.4 must author fresh"; add a Stack row for `pixi-build-python`
(repo floor `>=0.8.6`; warden's backend pin is `version = "0.*"`) and a note that AD-7 rides the
`pixi-build` **preview**; and either reconcile the `>=3.12` member floors with canopy:AD-23 or
record the divergence explicitly.

### H-4 — AD-3's "estate lock carries no solver-farm tooling" collides with live test deps

**Claim.** "The estate lock carries no solver-farm tooling (`rattler-build`, `conda-smithy`,
`conda-build`, `conda-forge-pinning`); those live in the island."

**Evidence.** Two of the four are **estate test dependencies today**, and the manifest says so in
its own comments:

```
pixi.toml:1968  py-rattler-build = ">=0.72.2"  # test-only differential-oracle for
                extract/recipe_v1.py (Story 2.2, v1 recipe.yaml render); NEVER a runtime dep
pixi.toml:1969  conda-build     = ">=25.3.1"   # test-only differential-oracle for
                extract/meta_v0.py (Story 2.2, v0 meta.yaml render); NEVER a runtime dep
```

Both sit in `[feature.pyforge-warden.dependencies]`. The lock resolves them well beyond the
recipe environments — `conda-build` into 9 environments including **`pyforge-warden`** and
**`pyforge-container`**; `py-rattler-build` into 9 including the same two. `pyforge-warden` is an
estate package by every other AD in this spine. If the estate lock drops these, warden's Story-2.2
oracle tests stop resolving, and AD-3 offers no disposition for them.

**Fix.** AD-3 needs a carve-out sentence: name `py-rattler-build` / `conda-build` as *test-only
oracles that remain in the estate lock*, or state that warden's oracle tests move to the island
and accept that an estate package's test suite then depends on an island environment (which AD-4's
"imports nothing from the island" makes awkward). Either way, decide it in the spine rather than
discovering it in Story 44.7.

---

## MEDIUM

### M-1 — AD-5's `[ASSUMPTION]` is documented fact on one IDE, unknown on the other, and may be unnecessary on the second

**Claim.** "`[ASSUMPTION]` both IDEs resolve per-skill relative symlinks."

**Claude Code — documented, not an assumption.** `https://code.claude.com/docs/en/skills`:

> A `<skill-name>` entry in the enterprise, personal, or project locations can be a symlink to a
> directory elsewhere on disk. Claude Code follows the symlink and reads `SKILL.md` from the
> target directory, and if the same target is reachable from more than one location, Claude Code
> loads the skill once. Plugin skills handle symlinks differently.

Two caveats the spine does not carry: **plugin skills handle symlinks differently**, and the
folder name **`synced` is reserved** in the enterprise/personal/project skill locations in any
capitalization (Claude Code writes claude.ai-synced skills there). Community reports also
distinguish *per-skill* symlinks (supported) from symlinking the **whole** `skills/` directory
(known discovery failures and `.system/` pollution) — AD-5 correctly chose per-skill, which is
worth stating as the reason rather than leaving implicit.

**Cursor — genuinely unknown.** `https://cursor.com/docs/skills` documents the discovery
locations but **never mentions symlinks** in any form. This half of the assumption is real and
should stay tagged — separately from the Claude Code half, which should be promoted to a cited
fact.

**The larger miss.** Cursor's docs list `.claude/skills/` and `~/.claude/skills/` as
**compatibility discovery locations**, alongside `.cursor/skills/`, `.agents/skills/`,
`~/.cursor/skills/`, `~/.agents/skills/`, `.codex/skills/`, `~/.codex/skills/`. If that holds,
the `.cursor/skills/` adapter tree AD-5 mandates is **redundant** — Cursor would already read the
`.claude/skills/` adapters. And `.agents/skills/`, the tool-neutral home both Cursor and the wider
ecosystem read, does not appear in the spine at all, despite the spine's own framing as
"framework-neutral".

**Repo reality — AD-5 is fully greenfield.** `.claude/skills/` holds **122 real directories and
zero symlinks** (`conda-forge-expert` included). **`.cursor/skills/` does not exist**: `.cursor/`
in this repo is a scratch/log tree (fleet-drain logs, kedro logs, campaign dirs, 66 worktrees),
with only `.cursor/rules/specs.mdc` and `.cursor/pyforge-fleet-drain/*` tracked. The Structural
Seed's `.claude/skills/  .cursor/skills/  # per-skill symlink adapters` reads as a description of
an existing arrangement; nothing of it exists today.

**Fix.** Split the assumption: cite the Claude Code doc line (and its two caveats) as fact; keep
the Cursor symlink behaviour as the only open `[ASSUMPTION]`; add an explicit decision on whether
`.cursor/skills/` is needed at all given Cursor's `.claude/skills/` compatibility, and whether
`.agents/skills/` should be the canonical adapter instead of either. Note in the Seed that both
adapter trees are net-new.

### M-2 — AD-8's `dies` list undercounts the staged-recipes inheritance

**Claim.** "The staged-recipes linter (three workflows), `test-linux/macos/windows` recipe builds
and `azure-pipelines.yml` are `dies` in the manifest."

**Evidence (all verified present).**

| Spine says | Actually |
|---|---|
| linter, "three workflows" | **four**: `staged-recipes-linter.yml`, `reusable-staged-recipes-linter.yml`, `reusable-staged-recipes-linter-selftest.yml`, and `linter_issue_comment.yml` (`name: rerun-staged-recipes-linter`) — plus `.github/workflows/scripts/linter.py` and `.github/workflows/scripts/linter_issue_comment.py` |
| `test-linux/macos/windows` | present (all three already `workflow_dispatch`-only, "to preserve GitHub Actions quota") — **plus a fourth, `test-all.yml` ("Test All Platforms"), unlisted** |
| `azure-pipelines.yml` | present — **plus `.azure-pipelines/` (3 tracked files: `-linux.yml`, `-osx.yml`, `-win.yml`), never named** |

Other inherited surfaces the manifest must classify and the spine does not name: `.ci_support/`
(18 tracked), `.scripts/` (5 tracked), `conda-forge.yml` (1), `build-locally.py` (1),
`environment.yaml` (1). The Structural Seed routes `build-locally.py .ci_support/
conda-forge.yml` into `factory/` but is silent on `.scripts/` and `.azure-pipelines/`.

One thing AD-8 gets right and should say out loud: CLAUDE.md's `environment.yaml` sync check is
enforced *by the inherited staged-recipes linter itself*, so killing the linter genuinely kills
the ritual — that is the causal chain, and stating it strengthens the AD.

**Fix.** Correct "three workflows" → four (+2 scripts); add `test-all.yml`, `.azure-pipelines/`
and `.scripts/` to the enumeration; give `.ci_support/`, `.scripts/`, `conda-forge.yml`,
`build-locally.py` explicit `factory/` or `dies` destinations in the Seed.

### M-3 — conda-smithy `>=3.44.6,<4` is a deliberate cap that excludes the current release line

**Claim.** Stack row: `conda-smithy (island) | >=3.44.6,<4 (today's floor; carried into
factory/pixi.toml)`.

**Evidence.** conda-forge's current conda-smithy is **2026.9.1** (CalVer); the newest 3.x is
**3.62.0**. `<4` excludes the entire live release line. This repo's lock already resolves **both**:
`conda-smithy-2026.9.1` in the `grayskull` environment, `conda-smithy-3.62.0` in the `conda-smithy`
environment. `pixi.toml:113` states the reason for the cap:

> `NOTE: CalVer 2026.x needs the 'conda' pkg, not in this env — for CI-parity lint use
> 'pixi exec conda-smithy recipe-lint'`

So the cap is a workaround for an environment-composition constraint of *this* repo — and the
island is a **fresh workspace**, precisely where that constraint need not be reproduced. Copying
`<4` forward as "today's floor" (it is a ceiling, not a floor) imports a known-stale pin into
greenfield without re-deciding it.

**Fix.** Restate as `>=3.44.6,<4` **cap, inherited workaround** and add a decision to the island's
Story 44.7: does `factory/pixi.toml` carry the `conda` package so it can track conda-smithy
2026.x, or does it keep the cap and the `pixi exec` CI-parity escape hatch? This is a one-line
decision that gets much more expensive after the island lock exists.

### M-4 — the move-list has undocumented prior art in this repo

**Evidence.** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/move_list.py` already
exists and self-describes as:

> `pyforge.scribe.extras.move_list` — the foundry-cutover move-list scan (Story 6.1; …cutover
> phases; unifying-strategy Grounding 2026-08-30 — packages fold `src/shared/packages/` →
> `src/packages/`, host drops `sys.path` inserts and `import pyforge.*`, `five_tier.py` retargets
> `_packages_root`)

with a `MoveListFinding` dataclass, four cutover signals (`import_pyforge`, `sys_path_insert`,
`five_tier_root`, `cfe_caller`), a shared exclusion walk, and a CLI surface (`scribe index
move-list`). AD-2 and Story 44.1 do not cite it. It is not a substitute for the manifest (it scans
`*.py` for signals, not tracked paths for destinations) — but it is the existing implementation of
the same named artifact for the same cutover, and it already enumerates the AD-6/AD-7 rewrite
sites that Story 44.4 needs.

Its docstring also cites `docs/dreams/pyforge-target-monorepo.md`, which **does not exist** —
`docs/dreams/` contains `pyforge-unifying-strategy.md` (the dream the spine correctly cites). A
pre-existing dangling pointer the cutover is the right moment to fix, and evidence that this prior
art was not consulted while drafting.

**Fix.** Cite `pyforge.scribe.extras.move_list` in AD-2 and Story 44.1: either extend it into the
manifest generator or state why a separate generator is warranted; fix or retire its dead dream
pointer.

### M-5 — worktree residue is understated roughly threefold, across homes the spine does not name

**Claim.** Deferred: "Runtime-state home (`.claude/data/` 11 GB, `.claude/worktrees/` 85 GB)";
"Worktree retirement mechanics (268 registered)".

**Evidence.** Both numbers are **exactly right** (`du -sh .claude/worktrees` → `85G`;
`du -sh .claude/data` → `11G`; `git worktree list | wc -l` → `268`). But `.claude/worktrees/` is
one of **three** worktree homes:

| Home | on-disk dirs | registrations pointing at it | sampled size |
|---|---|---|---|
| `.claude/worktrees/` | 33 | 62 | 11G, 11G, 290M |
| `.cursor/worktrees/` | 66 | 66 | 11G (`atlas-18-1`) |
| `.worktrees/` | 58 | 58 | 11G (`dispatch-pyforge-atlas-21.10`) |
| elsewhere / root | — | 82 | — |

157 on-disk trees; the sampled trees run ~11 GB each (an installed `.pixi/`). Real residue is
plausibly several hundred GB, not 85. Note also that 62 registrations point at `.claude/worktrees`
while only 33 dirs exist there — a large share are already orphaned registrations, which matters
for 44.10's retirement mechanics.

**Fix.** Name all three homes in the Deferred row and in 44.10's scope; re-measure before the
row's estimate is quoted anywhere operational.

### M-6 — the Stack table mixes floors with resolved versions and labels neither

`conda-build (island) | >=25.3.1` is a *manifest floor*; the lock resolves **26.7.1**, which is
also conda-forge's current release — the floor is a full CalVer major behind what actually
installs. `conda-smithy | >=3.44.6,<4` is a cap (M-3). `rattler-build | 0.72.2` was presented as a
resolved lock version and is neither (H-1). `pixi | 0.78.0` is a floor *and* the resolved version
*and* current upstream — all three coincide, which is why nobody noticed the column is ambiguous.

This ambiguity is the mechanism behind H-1: with no floor/resolved distinction, a number copied
from anywhere reads as authoritative.

**Fix.** Split the Stack table into `Floor (manifest)` and `Resolved (lock)` columns, and add a
third `Upstream latest (checked YYYY-MM-DD)` column so the next reviewer can see staleness at a
glance rather than re-deriving it.

---

## LOW

### L-1 — Confirmed accurate (recorded so the operator does not re-litigate them)

| Claim | Verification |
|---|---|
| pixi `0.78.0`, `requires-pixi >= 0.78.0` | `pixi --version` → 0.78.0 · `requires-pixi = ">=0.78.0"` · `"$schema"` URL `pixi.sh/v0.78.0/…` · all three feature floors `pixi = ">=0.78.0"` · `environment.yaml`: `- pixi >=0.78.0` · **0.78.0 is conda-forge's current release** |
| Python (estate) `3.14.*` | `python = ">=3.14.7,3.14.*"`; lock resolves 3.14.7; 3.14 is the current stable line |
| `pixi run --manifest-path` exists (AD-3, AD-4) | `pixi run --help` → `-m, --manifest-path <MANIFEST_PATH>`. **Safe.** Note `pixi build` now also has `--path` (`pixi build --help`), so the in-repo comment "pixi build has NO --manifest-path flag (0.73.0)" at `pixi.toml:469`/`:508` is stale — `pixi.toml:585` already uses `pixi build --path` |
| AD-6 "~100 sites" of `src/shared/packages` in `pixi.toml` | **103** literal occurrences |
| AD-3 "29-environment single lock" | **29** environments in `pixi.lock` |
| AD-10 "7,855-directory `recipes/`" | 7,855 dirs / 14,378 tracked files |
| AD-1 / Deferred "268 worktrees" | `git worktree list \| wc -l` → **268** |
| `.claude/worktrees/` 85 GB · `.claude/data/` 11 GB | `du -sh` → **85G** / **11G** |
| planning-history "69 MB of `_bmad-output/projects/*`" | `du -sh` → 68M |
| AD-12 "the eight `~/.bmad-loops/*` homes" | exactly 8: atlas, doctor, herald, marshal, mason, scribe, steward, warden |
| Named code artifacts exist | `pyforge/mason/resolve.py` + `MASON_CFE_ROOT` (flag → env → cwd chain) · `five_tier._packages_root` · `pyforge.core.dispatch.script_map_from_packages_root` · `marshal-policy.toml` · `scripts/spec_surface_check.py` |
| `rxm7706/python-foundry` does not exist yet | `gh api repos/rxm7706/python-foundry` → 404 with `rate_limit` 5000/5000 remaining — a **real** negative, not a rate-limited fail-open |

### L-2 — Technologies named without a version

- **`pixi-build-python`** — AD-7's entire rule rests on it, and it has **no Stack row**. Repo floor
  `>=0.8.6`; warden's member manifest pins the backend as `version = "0.*"`.
- **`preview = ["pixi-build"]`** — a pixi *preview* feature; no version, no stability note (H-3).
- `conda-forge-pinning` (`*` in repo) — named in AD-3's solver-farm list, unversioned.
- `rattler-build-conda-compat` (`>=1.2.0,<2.0.0a0`) — solver-farm tooling AD-3's list **omits**
  entirely; it must move to the island too.
- `hatchling` (`>=1.32.0`) — the build backend under every member manifest.
- `GitHub Actions` — Stack row with no runner-image or action versions; `bmad-loop` (AD-12
  re-provisions eight homes against it) — unversioned.
- git / `core.symlinks` / Windows Developer Mode — the mechanism the `windows-symlink-adapters`
  open question turns on, named without a git version or a concrete behaviour citation.

### L-3 — `.idea/` is 1,950 tracked files and almost certainly `dies`

The single largest unclassified block in C-1. `git ls-files .idea | wc -l` → **1,950** (JetBrains
project config, including per-package `*.iml` files such as `APScheduler.iml`,
`APScheduler@1.iml`). A greenfield root is the cheapest possible moment to drop it, and it is
exactly the kind of path a spec-surface-derived manifest will never produce a row for. Worth an
explicit AD-2 example row rather than leaving it to discovery in 44.1.

### L-4 — AD-1's "Prevents" mixes two different mechanisms

"two live histories; the purged-secret history **and 268 worktrees** riding into the lasting repo".
Worktrees are local `git worktree` registrations in `.git/worktrees/`, not history — they cannot
"ride into" a fresh repo through a copy-based move regardless of AD-1. The purged-secret half is
real and is what AD-1 actually prevents. Minor, but it makes the AD look like it is buying
something it is not.

---

## Method note

Repo claims were measured with the repo's own parsers where one exists (`spec_surface_check`'s
`tracked_files`/`parse_surface`/`glob_to_re` for C-1), never an ad-hoc regex. Version claims were
checked against `pixi.lock` **and** conda-forge's package API (`api.anaconda.org/package/
conda-forge/<name>`) rather than either alone, since the lock and upstream disagree in three of the
five Stack rows. IDE behaviour was checked against the vendors' own current docs
(`code.claude.com/docs/en/skills`, `cursor.com/docs/skills`). `du` on `.claude/worktrees` ran to
completion (85G, exit 0); the other two worktree homes were sampled, not fully measured, and M-5's
"several hundred GB" is stated as an estimate.

**Sources:**
[Claude Code — Extend Claude with skills](https://code.claude.com/docs/en/skills) ·
[Cursor — Agent Skills](https://cursor.com/docs/skills) ·
[conda-forge/rattler-build](https://api.anaconda.org/package/conda-forge/rattler-build) ·
[conda-forge/conda-smithy](https://api.anaconda.org/package/conda-forge/conda-smithy) ·
[conda-forge/conda-build](https://api.anaconda.org/package/conda-forge/conda-build) ·
[conda-forge/pixi](https://api.anaconda.org/package/conda-forge/pixi)
