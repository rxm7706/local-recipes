---
status: workflow
spec_updated: 2026-06-20
---
# Tech Spec: Feedstock Refresh + Platform Expansion (parameterized)

> Dual-goal effort: (1) refresh the local `recipes/<feedstock>/` mirror
> (and upstream feedstock) to the latest CFE-generated shape at
> `<upstream_version>`, **and** (2) widen the build matrix by adding
> `<target_platforms>` in the same PR. Both ship together so the
> platform-add lands on a known-good recipe baseline.
>
> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow
> track — single-feedstock update, no PRD/architecture phase). ~13
> stories across 3 waves. Run BMAD with this file as the intent
> document, naming the feedstock + target platforms in the prompt:
>
> ```
> run quick-dev — implement docs/specs/feedstock-platform-expansion.md
> for feedstock=<name>, target_platforms=<comma-separated-subdirs>
> ```
>
> **Per CLAUDE.md Rule 1**, any BMAD agent executing this spec MUST
> invoke the `conda-forge-expert` skill before touching recipe code or
> running recipe tooling. Per Rule 2, the effort closes with a CFE-skill
> retrospective and a `CHANGELOG.md` entry (even if no findings, write
> a "verified existing guidance held" entry).
>
> **Timeless workflow lives in
> [`.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md`](../../.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md).**
> This spec parameterizes the workflow for a specific feedstock and
> records the per-case empirical state, open questions, and
> ruled-out alternatives. New cases append to "Worked Examples" — they
> do not duplicate the workflow.

---

## How to use this spec

1. **Fill the Parameters block below** with the feedstock-under-expansion's
   real values.
2. **Run BMAD quick-dev**; it follows the Stories section verbatim,
   referencing the guide for procedural detail.
3. **Resolve the Open Questions** before opening any PR.
4. **Append a new "Worked Example"** section at the bottom recording
   per-case empirical state, Q&A resolutions, and the final PR URL.
   This becomes a permanent record once the case ships.

---

## Parameters (fill these per case)

| Parameter | Value | Notes |
|---|---|---|
| `feedstock` | `<feedstock-name>` | The feedstock without `-feedstock` suffix (e.g. `cocoindex`, `numpy`, `pytorch`) |
| `upstream_version` | `<X.Y.Z>` | The version currently on upstream `main` — confirm with `gh api repos/conda-forge/<feedstock>-feedstock/contents/recipe/recipe.yaml` |
| `current_platforms` | `<list>` | What's shipping today, per `repodata.json` audit |
| `target_platforms` | `<list>` | What this PR adds (e.g. `osx_arm64,linux_aarch64`) |
| `recipe_shape` | `compiled` \| `noarch:python` | Determines whether to edit `provider:` or `noarch_platforms:` (see guide § Decision matrix) |
| `fork_owner` | `<github-handle>` | The GitHub user owning the working fork (e.g. `rxm7706`) |
| `branch_name` | `add-<target-platforms-slug>` | Single descriptive name; no version suffix |
| `recipe_path` | `recipes/<feedstock>/` | Local-mirror path |
| `local_test_subdir` | `<host-subdir>` | The operator's host subdir for native build verification (e.g. `linux-64`, `osx-arm64`) |

---

## Status

| Field | Value |
|---|---|
| Status | **Template** — fill Parameters, resolve Open Questions, then BMAD intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (single-feedstock recipe update, no schema change in this repo) |
| Surface area | `recipes/<feedstock>/` (local mirror); `<fork_owner>/<feedstock>-feedstock` fork → PR to `conda-forge/<feedstock>-feedstock`; **no** code changes to `.claude/skills/conda-forge-expert/` (skill-internal work limited to closeout retro per Rule 2) |
| Scope | (1) Sync local `recipes/<feedstock>/` to upstream feedstock at `<upstream_version>`. (2) Re-verify the recipe via the conda-forge-expert skill (regenerate fresh, diff against current, apply only approved corrections). (3) Native-platform lint/optimize/build/test on `<local_test_subdir>`. (4) Refresh `conda-forge.yml` with the minimal additive deltas for `<target_platforms>`. (5) `conda smithy rerender` to regenerate `.ci_support/` + `.azure-pipelines/`. (6) Local cross-platform build verification where toolchain permits (diagnostic only). (7) Open **DRAFT** PR against `conda-forge/<feedstock>-feedstock` from `<fork_owner>:<branch_name>`. |
| Out of scope | Version bump beyond `<upstream_version>`. Adding any platform not in `<target_platforms>` (deferred). Modifying already-shipping builds. Touching any other recipe in `recipes/`. Auto-merging the PR. Schema or table changes in `cf_atlas.db`. Skill-code changes outside the closeout retro. |
| Created | `<YYYY-MM-DD>` |
| Driven by | `<empirical signal that triggered this case — repodata grep, atlas package_health, user report URL>` |
| Predecessor | `<prior PR# or spec — N/A if first expansion on this feedstock>` |

---

## Background and Context

### The problem

`<package>` is currently not installable from conda-forge on
`<target_platforms_friendly>`. Confirmed empirically:
`curl https://conda.anaconda.org/conda-forge/<target_subdir>/repodata.json | grep <feedstock>-`
returns zero matches. The upstream feedstock at `<upstream_version>`
ships only `<current_platforms>`.

`<secondary drift, if any>` — e.g. the local mirror at
`recipes/<feedstock>/recipe.yaml` is stale (declared version vs.
upstream), so any local build verification against the stale mirror is
unsound; the mirror is re-synced before platform-matrix changes are
tested.

### What's been ruled out

Enumerate per case. Standard exclusions:

- **Platforms not in `<target_platforms>`** — see Decision matrix in
  the guide for the per-subdir rationale. Common rejects:
  - `linux-ppc64le`, `linux-s390x`, `linux-riscv64`: insufficient
    transitive-Rust-dep / transitive-C-dep coverage on conda-forge in
    mid-2026 — would produce immediate red CI on dep resolution.
  - `win-arm64`: Azure leg not routinely green in mid-2026.
- **A version bump beyond `<upstream_version>`**. Don't preempt the
  autotick bot.
- **Touching the recipe.yaml `build.script:` or `requirements:`
  blocks** unless the recipe is provably not cross-compile-ready
  (Stop-the-Line if so).
- **Auto-merging the PR.** Per CLAUDE.md "Executing actions with
  care", a feedstock PR that changes CI matrix is stakeholder-visible.
  Operator confirms before draft → ready-for-review and before merge.

### What's available to leverage

- **`conda-forge-expert` skill's diff-before-apply sub-workflow** — the
  canonical pattern for refreshing the local mirror.
- **The recipe's existing cross-compile or noarch_platforms
  scaffolding** — if present, provider activation alone is sufficient.
  If absent, this is a Stop-the-Line moment (scope expands to recipe
  authoring).
- **`pixi run -e local-recipes recipe-build recipes/<feedstock>`** — native-platform build via rattler-build with conda-forge-pinning's `conda_build_config.yaml` overlaid.
- **`gh repo sync`** — fast-forward the fork against
  `conda-forge/<feedstock>-feedstock` main before branching.
- **`conda smithy rerender`** — regenerates `.ci_support/*.yaml` from
  the `conda-forge.yml` provider block.

### Empirical state (verified `<YYYY-MM-DD>`)

```
upstream conda-forge/<feedstock>-feedstock main: version <X.Y.Z>, sha256 <prefix>
upstream platforms shipping: <list> (<N builds × M platforms = K artifacts>)
upstream platforms missing:  <target_platforms>
local recipes/<feedstock>/recipe.yaml: version <local-version> (<staleness>)
<fork_owner>/<feedstock>-feedstock: fork exists, parented to conda-forge/<feedstock>-feedstock
```

Upstream `conda-forge.yml` (verbatim, as of `<YYYY-MM-DD>`):
```yaml
<paste current conda-forge.yml here>
```

→ The deltas this PR needs to land are:

| Delta | Why |
|---|---|
| `<add or skip per upstream state>` | Per CFE `reference/conda-forge-yml-reference.md` |

---

## Goals

1. **Local `recipes/<feedstock>/` mirror tracks upstream feedstock at
   `<upstream_version>` in the latest CFE-generated shape** — closes
   any local drift. First-class goal of the effort, not a prerequisite
   side-effect.
2. **The upstream feedstock's `recipe/recipe.yaml` is also brought to
   the latest generated shape** if the diff-before-apply turns up
   corrections worth landing — those land in the same PR as the
   platform expansion (or as a sibling PR if the recipe-shape delta
   is large enough to deserve its own review surface; operator
   decides at the S10 gate).
3. **`<feedstock>` is installable from conda-forge** on each platform
   in `<target_platforms>` within one merge cycle after this PR lands.
4. **`workflow_settings.store_build_artifacts: true`** is enabled so
   future reviewer smoke-tests can `pr-artifacts <pr#>` pull the built
   `.conda` files (the v8.14.0 PR-artifact downloader pattern). Replaces
   the deprecated `azure.store_build_artifacts` per conda-smithy schema.
5. **Local native build verified green** on `<local_test_subdir>`.
   Cross-target build attempts diagnostic only.
6. **Draft PR opened, not auto-merged.** Operator review checkpoint
   before draft → ready-for-review and before merge.
7. **No structural recipe change** beyond the diff-before-apply
   corrections — provider activation alone should produce green CI on
   the new platforms. Any further structural change discovered to be
   necessary becomes a Stop-the-Line moment.

---

## Two load-bearing workflow rules (apply to every story)

These two rules are enforced through every story below. Skim once, then
hold them while reading the Stories list:

- **Local mirror is the source of truth — and the mirror must be
  COMPLETE.** `recipes/<feedstock>/` mirrors the entire feedstock's
  recipe-side state, not just `recipe.yaml`: required files are
  `recipe.yaml`, `conda-forge.yml`, `LICENSE` (if shipped with the
  recipe), `patches/*.patch`, and `build.sh` / `build.bat` (when
  separate from `recipe.yaml`'s inline script). When S2 refreshes the
  local mirror, it refreshes ALL of these — not just `recipe.yaml`.
  When S6 edits `conda-forge.yml`, the edit lands in the local mirror
  first; the fork checkout is updated by `cp` from the mirror, not by
  direct edit. The same rule applies to any CI-iteration fix push.

- **Edit local → verify-build local → mirror to fork → push → request
  rerender.** Every push to the feedstock fork branch (initial PR
  open in S11 AND every CI-iteration fix push thereafter) runs in
  that exact order. Per the post-edit-rebuild discipline (CFE SKILL.md
  § 9 step 9), the fork branch always reflects a verified-green local
  state — a Windows-only env-var change is also set on linux/macOS, so
  the host build is the verification that you didn't regress. The
  `@conda-forge-admin, please rerender` comment runs after every push,
  no exceptions; the bot is idempotent and exits clean when nothing
  needs regenerating.

## Stories — Wave A: Local mirror sync + verification (offline-safe, host-only)

Refer to guide § "Wave A — Sync the local mirror + verify upstream
parity" for procedural detail. The stories below are the BMAD-tracked
unit-of-work checklist.

### S1. Sync the `<fork_owner>` fork with conda-forge upstream

`gh repo sync <fork_owner>/<feedstock>-feedstock --branch main`. Verify
the fork's HEAD matches `conda-forge/<feedstock>-feedstock` main. If
sync fails (drift or fork-divergent commits), surface to operator
before forcing.

**Acceptance**: `gh api repos/<fork_owner>/<feedstock>-feedstock/commits/main --jq .sha`
equals
`gh api repos/conda-forge/<feedstock>-feedstock/commits/main --jq .sha`.

### S2. Refresh local `recipes/<feedstock>/` to match upstream `<upstream_version>`

Apply the CFE skill's diff-before-apply sub-workflow (see guide § Wave
A step 2). The refresh applies to the COMPLETE local mirror per the
load-bearing "mirror must be complete" rule, not just `recipe.yaml`:

- `recipes/<feedstock>/recipe.yaml` ↔ upstream `recipe/recipe.yaml`
- `recipes/<feedstock>/conda-forge.yml` ↔ upstream `conda-forge.yml`
  (create if missing — first-time setup)
- `recipes/<feedstock>/LICENSE` ↔ upstream `recipe/LICENSE`
  (when shipped)
- `recipes/<feedstock>/patches/*.patch` ↔ upstream `recipe/patches/`
- `recipes/<feedstock>/build.sh` / `build.bat` ↔ upstream
  `recipe/build.sh` / `recipe/build.bat`

**Acceptance**: every file in `recipes/<feedstock>/` is byte-identical
(modulo trailing whitespace) to the corresponding file in
`conda-forge/<feedstock>-feedstock` HEAD. Specifically:
`diff -u recipes/<feedstock>/recipe.yaml
<(gh api repos/conda-forge/<feedstock>-feedstock/contents/recipe/recipe.yaml --jq .content | base64 -d)`
is empty, AND the same check passes for `conda-forge.yml`
(and `LICENSE` / `patches/` if applicable).

### S3. Validate + optimize + check-deps the refreshed local recipe

```
pixi run -e local-recipes validate recipes/<feedstock>
pixi run -e local-recipes lint-optimize recipes/<feedstock>
pixi run -e local-recipes check-deps recipes/<feedstock>
```

Additionally run `check_dependencies(recipe_path=..., target_subdir=T)`
for each `T` in `<target_platforms>` — a green result here is the
prerequisite for opening the PR.

**Acceptance**: all four calls return clean. Any warning escalates to
Stop-the-Line.

### S4. Native build on `<local_test_subdir>` — full lifecycle

```
pixi run -e local-recipes recipe-build recipes/<feedstock>
```

`get_build_summary()` returns `status: success`. Test phase ran.
Artifact lands under
`build_artifacts/<local_test_subdir>/<local_test_subdir>/<feedstock>-<upstream_version>-*.conda`.

**Acceptance**: at least one Python variant (or one build variant for
non-Python recipes) produces a green build with passing tests. Per
skill **G8b**: `.conda` file existence overrides
`get_build_summary status: unknown` false-negatives.

---

## Stories — Wave B: conda-forge.yml refresh + cross-platform local verification

Refer to guide § "Wave B — Edit `conda-forge.yml` and rerender".

### S5. Sync `<fork_owner>` fork (re-confirm; S1 may have aged) and clone

```
gh repo sync <fork_owner>/<feedstock>-feedstock --branch main
gh repo clone <fork_owner>/<feedstock>-feedstock /tmp/<feedstock>-feedstock-work
cd /tmp/<feedstock>-feedstock-work
git checkout -b <branch_name>
```

**Acceptance**: working tree on branch `<branch_name>`; upstream remote
points at `conda-forge/<feedstock>-feedstock`.

### S6. Edit `conda-forge.yml` with minimal additive delta

For **compiled** recipes (`recipe_shape: compiled`):

```yaml
# Platform-expansion delta = the ARM matrix (build_platform + provider + test).
# Do NOT re-add the universal pre-seed (conda_build_tool/conda_install_tool/bot)
# if already upstream. workflow_settings.store_build_artifacts is optional
# reviewer-convenience (win-exclude per G18), NOT a default.
build_platform:
  <new-target>: <build-host>    # e.g. linux_aarch64: linux_64, osx_arm64: osx_64
provider:
  <new-target>: azure           # enables the otherwise-disabled arch (field default None)
test: native_and_emulated
```

For **noarch:python** recipes with platform-conditional selectors
(`recipe_shape: noarch:python`):

```yaml
noarch_platforms:
  - linux_64
  - osx_64
  - <new-platforms>
```

Do **not** add keys already present upstream. New recipes ship the universal
pre-seed automatically (CFE skill default, G83) — see
`reference/conda-forge-yml-reference.md § Recommended pre-seed defaults`.

**Acceptance**: `conda-forge.yml` differs from upstream only by the
intended additive blocks.

### S7. `conda smithy rerender` to regenerate `.ci_support/` + `.azure-pipelines/`

```
pixi run -e conda-smithy conda-smithy rerender
```

Confirms generation of new variant configs per target × Python variant
and Azure pipeline updates. No deletions of existing platform configs.
Unrelated drift surfaces to operator.

**Acceptance**: `git status` shows expected new `.ci_support/` files +
the `conda-forge.yml` edit + minor boilerplate refresh only.

### S8. Local cross-target build attempts (diagnostic, not gating)

For each `T` in `<target_platforms>` where a variant config exists,
attempt the build via `rattler-build --target-platform T`. See guide §
Wave B step 4 for the canonical command and outcome catalog.

**Acceptance**: each cross-target attempt produces either (a) a
`.conda` artifact, or (b) a documented failure mode. Either is OK for
shipping — conda-forge CI is the real gate.

---

## Stories — Wave C: Branch, draft PR, operator checkpoint, retro

Refer to guide § "Wave C — Branch, draft PR, operator gates, retro".

### S9. Verify-build local, mirror to fork, commit, push, request rerender

Per the load-bearing five-step push procedure (see guide § Wave C
step 1), this story is **not** "just git push" — it's the full pipeline
applied to the initial push AND to every CI-iteration fix push:

a. **Confirm local mirror is complete.** All Wave A + Wave B edits
   landed in `recipes/<feedstock>/`, not directly in the fork checkout.

b. **Run the local native build:**
   ```
   pixi run -e local-recipes recipe-build recipes/<feedstock>
   ```
   Even when the change is "Windows-only" (a `PYTHONUTF8` env var, a
   `if: win` selector, a `build.bat` fix), env vars are set on every
   platform and selectors can have surprise interactions. The local
   host build is the verification.

c. **Mirror EVERY changed file to the fork checkout:**
   ```
   cp recipes/<feedstock>/recipe.yaml /tmp/<feedstock>-feedstock-work/recipe/recipe.yaml
   cp recipes/<feedstock>/conda-forge.yml /tmp/<feedstock>-feedstock-work/conda-forge.yml
   # plus LICENSE / patches/ / build.{sh,bat} as applicable
   ```
   `git -C /tmp/<feedstock>-feedstock-work diff origin/<branch_name>` to
   confirm only the intentional changes are present.

d. **Commit + push:**
   ```
   git -C /tmp/<feedstock>-feedstock-work add conda-forge.yml recipe/ .ci_support/ .azure-pipelines/
   git -C /tmp/<feedstock>-feedstock-work commit -m "Add <target_platforms>; <secondary deltas>"
   git -C /tmp/<feedstock>-feedstock-work push -u origin <branch_name>
   ```
   Single commit. Do not pass `--no-verify`.

e. **Post `@conda-forge-admin, please rerender` on the PR:**
   ```
   gh pr comment <PR#> --repo conda-forge/<feedstock>-feedstock \
     --body "@conda-forge-admin, please rerender"
   ```
   Every push, no exceptions — even when only `recipe.yaml` changed.
   The bot is idempotent.

**Acceptance**: (1) local recipe-build returned `status: success` with
a `.conda` artifact under `build_artifacts/<local_test_subdir>/`;
(2) `git -C /tmp/<feedstock>-feedstock-work diff origin/<branch_name>`
shows only intentional changes; (3) branch lands on
`<fork_owner>/<feedstock>-feedstock`, `gh api
repos/<fork_owner>/<feedstock>-feedstock/branches/<branch_name>` returns
200; (4) the `@conda-forge-admin, please rerender` comment appears on
the PR's comment timeline.

### S10. Operator-confirm checkpoint before opening PR

**HALT** — present diff summary to operator:

- `conda-forge.yml` delta
- New `.ci_support/*.yaml` filenames
- Cross-target local build outcomes from S8
- `check_dependencies` result for each new subdir

Operator confirms (or redirects) before S11 runs.

**Acceptance**: explicit operator approval before opening PR.

### S11. Open DRAFT PR to `conda-forge/<feedstock>-feedstock`

```
gh pr create \
  --repo conda-forge/<feedstock>-feedstock \
  --base main \
  --head <fork_owner>:<branch_name> \
  --draft \
  --title "Add <target_platforms> to build matrix" \
  --body "<see guide § Wave C step 3 for template>"
```

**Acceptance**: draft PR URL returned by `gh pr create`; PR visible in
the conda-forge org's queue.

### S12. Operator-confirm draft → ready-for-review

**HALT** — operator reviews CI runs. When all legs (existing + new) are
green, operator flips PR to ready-for-review via `gh pr ready <PR>`.

**Acceptance**: PR transitions DRAFT → READY → MERGED. Within ~6 hours
of merge, `conda-forge/<target-subdir>/repodata.json` carries the
first `<feedstock>-<upstream_version>-*` builds for each
`<target_platform>`.

### S13. CFE skill closeout retro (per BMAD↔CFE Rule 2 — always-on)

Even if no novel findings surfaced, run the retro. See guide § Wave C
step 5.

**Acceptance**: new `CHANGELOG.md` entry in
`.claude/skills/conda-forge-expert/CHANGELOG.md` dated `<YYYY-MM-DD>`.

---

## Open Questions (resolve before BMAD intake)

Per case. Standard prompts to check:

- **Q1 — Recipe shape**: is this `compiled` or `noarch:python`? Drives
  the `conda-forge.yml` edit shape (provider vs. noarch_platforms).
- **Q2 — PR target**: confirm `conda-forge/<feedstock>-feedstock` (not
  `staged-recipes` — feedstock already exists).
- **Q3 — Scope**: confirm `<target_platforms>` is the intended set;
  surface any rejected platforms with reasoning.
- **Q4 — Local cross-target builds**: gate or diagnostic? **Recommended
  diagnostic** per guide.
- **Q5 — Operator-confirm gates**: both halts (S10 + S12) mandatory?
  **Recommended yes** per guide.

Per-case Open Questions live in the Worked Example section, not here.

---

## Risks and Mitigations

See guide § "Risk catalog" for the timeless table. Per-case risks
(e.g. a specific transitive dep that's known-shaky on the new platform)
go in the Worked Example.

---

## Acceptance criteria (whole effort)

1. **PR opened** as DRAFT against `conda-forge/<feedstock>-feedstock`
   from `<fork_owner>/<feedstock>-feedstock:<branch_name>`.
2. **Local `recipes/<feedstock>/recipe.yaml`** at `<upstream_version>`,
   matches upstream byte-for-byte (modulo trailing whitespace).
3. **`validate_recipe` + `optimize_recipe` + `check_dependencies`**
   clean against the refreshed local recipe, including each new
   subdir.
4. **Native `<local_test_subdir>` build green** with passing tests.
5. **Cross-target build attempts documented** for each
   `<target_platform>` (success or documented failure — either OK).
6. **CHANGELOG entry** in `.claude/skills/conda-forge-expert/CHANGELOG.md`.
7. **Eventual merge state**: each `<target-subdir>/repodata.json`
   carries `<feedstock>-<upstream_version>-*` builds.

---

## Reference

- Workflow guide:
  [`.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md`](../../.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md)
- CFE `SKILL.md` § "Sub-workflow: Updating an existing recipe
  (diff-before-apply)"
- CFE `SKILL.md` § Critical Constraints — schema header,
  `python_min` policy, `stdlib` required, never-mix-formats
- CFE `SKILL.md` § G1 / G8b / G12 — relevant gotchas
- CFE `reference/conda-forge-yml-reference.md` — `provider:`,
  `workflow_settings.store_build_artifacts:` (replaces deprecated
  `azure.store_build_artifacts`), bot config keys, `noarch_platforms`,
  `build_platform`, `test`
- CLAUDE.md § "BMAD ↔ conda-forge-expert integration" — Rule 1 + Rule 2

---

# Worked Examples

Append each completed case as its own H2 section below. A case carries
the resolved Parameters, the empirical state at the time, the resolved
Open Questions, any per-case risks, and the final PR URL once the
effort closes.

---

## Worked Example: cocoindex 1.0.10 → +osx_arm64, +linux_aarch64 (2026-06-14)

| Parameter | Resolved value |
|---|---|
| `feedstock` | `cocoindex` |
| `upstream_version` | `1.0.10` |
| `current_platforms` | `linux-64`, `osx-64`, `win-64` (35 builds × 3 platforms = 105 artifacts at 1.0.10) |
| `target_platforms` | `osx_arm64`, `linux_aarch64` |
| `recipe_shape` | `compiled` (Rust+PyO3 via maturin) |
| `fork_owner` | `rxm7706` |
| `branch_name` | `add-osx-arm64-linux-aarch64` |
| `recipe_path` | `recipes/cocoindex/` |
| `local_test_subdir` | `linux-64` |

**Status**: Draft v1 (2026-06-14) — Open Questions Q1–Q5 resolved
inline below; ready for BMAD intake.

**Driven by**: cocoindex not installable on macOS arm64 — confirmed
empirically:
`curl https://conda.anaconda.org/conda-forge/osx-arm64/repodata.json | grep cocoindex-`
returns zero matches. The local recipe at `recipes/cocoindex/recipe.yaml`
is also stale at 1.0.5 — a drift that should close in the same effort.

**Predecessor**: cocoindex PR #33231 (May 2026 — original conda-forge
submission; landed the tree-sitter + GCC 14 + glibc 2.17 sysroot fix
per skill gotcha **G1**). The recipe already carries cross-compile
scaffolding (`requirements.build:` includes the `if: build_platform !=
target_platform / then: [python, cross-python_${{ target_platform }},
crossenv, maturin]` block), so the recipe code itself is ready for
`osx_arm64` and `linux_aarch64`; the gap is in `conda-forge.yml`.

### Empirical state (verified 2026-06-14)

```
upstream conda-forge/cocoindex-feedstock main: version 1.0.10, sha256 d2d04f6f...
upstream platforms shipping: linux-64 (35), osx-64 (35), win-64 (35)
upstream platforms missing:  osx-arm64 (0), linux-aarch64 (0)
local recipes/cocoindex/recipe.yaml: version 1.0.5 (stale by 4 patches + 1 minor)
rxm7706/cocoindex-feedstock: fork exists, parented to conda-forge/cocoindex-feedstock
```

Upstream `conda-forge.yml` (verbatim, 2026-06-14):
```yaml
github:
  branch_name: main
  tooling_branch_name: main
conda_build:
  error_overlinking: true
conda_forge_output_validation: true
bot:
  automerge: true
  inspection: update-grayskull
  check_solvable: true
  run_deps_from_wheel: true
conda_install_tool: pixi
conda_build_tool: rattler-build
```

→ Deltas this PR needs:

| Delta | Why |
|---|---|
| Add `workflow_settings.store_build_artifacts: true` (replaces deprecated `azure.store_build_artifacts`) | Per CFE `conda-forge-yml-reference.md` § "Top use cases" — keeps `.conda` artifacts downloadable from CI for reviewer smoke-testing. Default is `[]` (empty list = off) |
| Add `provider.osx_arm64: default` + `provider.linux_aarch64: default` | Activates the two new CI legs. `default` resolves to Azure (per skill ecosystem-update note, Mar 2026 GHA opt-in is `linux_64`-only) |

The remaining keys (`error_overlinking`, `bot.automerge`, etc.) are
already upstream and do not need to be re-added.

### Open Questions — resolved 2026-06-14

**Q1. `noarch_platforms` in the user's intake YAML — keep, drop, or
reinterpret?** The intake message proposed
`noarch_platforms: [win_64, linux_64, osx_64]`, but cocoindex is a
**compiled** Rust+PyO3 package, not noarch. Per CFE skill **G12**,
`noarch_platforms` is the conda-smithy escape hatch for noarch:python
recipes with platform-conditional `run:` selectors; it does not
control the build matrix of a compiled recipe.
**Resolution**: interpret as "expand the build matrix" → translate to
`provider.osx_arm64: default` + `provider.linux_aarch64: default`.
Drop `noarch_platforms` from the final `conda-forge.yml`.

**Q2. PR target — `staged-recipe/cocoindex-feedstock` typo?** No
`staged-recipe` org exists; cocoindex is a feedstock, not a
staged-recipes submission.
**Resolution**: `conda-forge/cocoindex-feedstock`.

**Q3. Scope — just osx-arm64 + linux-aarch64?** Original intake
listed 9 conda subdirs. `noarch`, `unix`, `linux`, `osx`, `win` are
not conda subdirs; cocoindex is compiled so noarch is impossible (see
Q1). `linux-ppc64le`, `linux-s390x`, `linux-riscv64`, `win-arm64` have
insufficient transitive-Rust-dep coverage on conda-forge in mid-2026
— adding them would produce immediate red CI on dep resolution.
**Resolution**: osx-arm64 + linux-aarch64 only.

**Q4. Local cross-target build attempts — gate or diagnostic?**
**Resolution**: diagnostic only. The recipe's cross-compile
scaffolding has been proven by upstream CI for the existing 3
platforms; logically extensible without recipe changes.

**Q5. Operator-confirm gates — explicit halt or automated proceed?**
**Resolution**: both halts (S10 + S12) mandatory. PR creation against
the upstream conda-forge org is stakeholder-visible. Operator-confirms-once
is not sufficient given the multi-day Azure CI cycle.

### Per-case Pre-Resolved Decisions

- **Branch name**: `add-osx-arm64-linux-aarch64`. Single descriptive
  name; no version suffix needed.
- **Commit message**: single commit,
  `"Add osx_arm64 + linux_aarch64; enable workflow_settings.store_build_artifacts"`.
- **PR opens as DRAFT.** Not ready-for-review until operator confirms
  CI is green on all 5 legs.

### Per-case Risks (additive to guide § Risk catalog)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| osx-arm64 CI fails because a transitive Rust dep isn't built for osx-arm64 yet | Low | Blocks the PR | Pre-check via `check_dependencies(target_subdir="osx-arm64")` before opening the PR; if a gap exists, document the prerequisite feedstock that needs to ship first |
| `error_overlinking: true` (already upstream) surfaces previously-tolerated overlinks on the two new platforms | Medium | Blocks PR until fixed | Treat as Stop-the-Line per Build Failure Protocol. Fix by tightening `host:` deps; `build.missing_dso_whitelist` last resort |

### Final state

- Draft PR URL: _<populate when S11 lands>_
- Merge date: _<populate when S12 closes>_
- First `cocoindex-1.0.10-*` on `osx-arm64/repodata.json`: _<populate>_
- First `cocoindex-1.0.10-*` on `linux-aarch64/repodata.json`: _<populate>_
- Closeout retro CHANGELOG entry: _<populate>_
