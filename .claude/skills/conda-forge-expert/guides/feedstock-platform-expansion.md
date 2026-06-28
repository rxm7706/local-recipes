# Feedstock Platform Expansion Guide

Workflow for **two intertwined goals on the same effort**:

1. **Refresh** the local `recipes/<feedstock>/` mirror and (when
   applicable) the upstream feedstock to the latest CFE-generated
   shape at the latest upstream version.
2. **Expand** the conda-forge build matrix by adding one or more
   conda subdirs (e.g. `osx-arm64`, `linux-aarch64`) in the same PR.

Both are first-class outcomes — the refresh closes the local-mirror
drift (regenerate fresh → diff-before-apply → land approved
corrections) and the matrix expansion adds the missing legs. Doing
them together avoids a second round-trip and gives the platform-add
PR a known-good recipe baseline.

This guide applies to both compiled recipes (Rust+PyO3, C/C++, Go, …)
and noarch:python recipes that need new `noarch_platforms` coverage.

This guide is the timeless workflow. Per-feedstock cases (cocoindex
2026-06, future audits, …) live in `docs/specs/feedstock-platform-expansion.md`
with a Parameters block and Worked Example appendix that point back here.

## When to apply

Trigger this workflow when **any** of the following is true:

- A user reports `<package>` is missing on `<subdir>` and
  `curl https://conda.anaconda.org/conda-forge/<subdir>/repodata.json | grep <package>-`
  returns zero matches.
- The atlas `package_health <feedstock>` shows non-empty
  `platforms_missing` for in-demand subdirs (`osx-arm64`, `linux-aarch64`).
- A user submits a feature request to widen the build matrix on an
  existing feedstock.
- A maintainer wants to refresh the local mirror and add platforms in
  the same effort — the canonical case for `local-recipes` operators
  bringing a maintained feedstock forward to the latest generated
  shape while also widening coverage.

Do **not** trigger this workflow for:

- A brand-new package that has never been to conda-forge (use the
  `conda-forge-expert` autonomous loop with `staged-recipes` instead).
- A bare version bump with **no** platform expansion (use the autotick
  bot or `MCP update_recipe` / `update_recipe_from_github` — this guide's
  Wave B/C are dead weight when the matrix doesn't change).
- A bare platform-add with **no** local mirror drift (still acceptable;
  Wave A is fast on an already-fresh mirror and the diff-before-apply
  step terminates immediately with zero hunks).
- Removing platforms (use `bot.version_updates.exclude_platforms`
  or a Rule-2 retro discussion — not this guide).
- **A noarch:python recipe with no platform-conditional runtime
  behavior** — adding `noarch_platforms` is pure waste here. The
  artifact is one platform-independent `.conda` regardless; extra
  subdirs only generate test legs that can fail from Windows-specific
  flakes (antivirus on the build dir, file locks, agent quirks)
  without changing what gets published. **Stop and justify each
  added subdir** against the "platform-conditional runtime behavior"
  list in `reference/conda-forge-yml-reference.md` § `noarch_platforms`
  before proceeding. If the recipe doesn't branch on `sys.platform` /
  `os.name` and doesn't subprocess a native CLI, leave the matrix at
  the default `[linux_64]`.

## Decision matrix: which platforms to add

Resolve this **before** editing `conda-forge.yml`. The decision is
recipe-shape-dependent and toolchain-dependent.

| Platform | Add when | Skip when | Default provider |
|---|---|---|---|
| `osx_arm64` | Apple-silicon users have asked, **and** the recipe compiles on `osx-64` today | Recipe uses x86-only intrinsics (rare) or vendored Apple-x86 binaries with no arm64 mirror | Azure (native Apple-silicon runner since 2024-Q3) |
| `linux_aarch64` | Mobile/server-arm users have asked, **and** all transitive `host:` + `run:` deps have `linux-aarch64` builds on conda-forge | Any transitive dep is `linux-64`-only on conda-forge | Azure (emulated qemu-aarch64; slow but reliable) |
| `win_arm64` | Rare; only when Windows-on-ARM users have explicitly asked | Almost always — Azure win-arm64 leg is not routinely green in mid-2026 | Azure (when added) |
| `linux_ppc64le` / `linux_s390x` / `linux_riscv64` | Specific institutional ask (HPC, embedded) with full transitive-dep audit | Default; transitive-dep coverage is thin | Cirun or self-hosted (no Azure leg) |

Always **`check_dependencies(recipe_path=..., target_subdir="<new-subdir>")`**
against each candidate subdir before adding it. A green `check_dependencies`
is the prerequisite for opening the PR; a red one means a prerequisite
feedstock needs to ship first (file the prerequisite as a separate spec).

### Compiled vs. noarch:python

This guide handles **both shapes**, but the `conda-forge.yml` edits differ.
See **[`reference/conda-forge-yml-reference.md`](../reference/conda-forge-yml-reference.md)
§ "Canonical conda-forge.yml shapes"** for full end-to-end YAML for each
of the three shapes below. Brief sketch:

**Shape 1 — Compiled, minimal expansion (e.g. cocoindex adding osx-arm64):**

```yaml
# Add to conda-forge.yml
provider:
  osx_arm64: default       # native Apple-silicon Azure runner
  linux_aarch64: default   # qemu-emulated aarch64 Azure runner
```

**Shape 2 — Compiled, multi-arch with cross-build hosts (e.g. pixi-feedstock):**

```yaml
# Add to conda-forge.yml
build_platform:
  osx_64: osx_arm64        # build osx_64 on Apple silicon (Rosetta)
  win_arm64: win_64        # cross-build win_arm64 on win_64
provider:
  osx_arm64: default
  linux_aarch64: default
test: native_and_emulated
```

**Shape 3 — Noarch:python multi-arch coverage (e.g. apache-superset):**

```yaml
# Add to conda-forge.yml
noarch_platforms:
  - linux_64
  - win_64
  - osx_64
  - osx_arm64
  - linux_ppc64le
  - linux_aarch64
build_platform:
  linux_aarch64: linux_64
  linux_ppc64le: linux_64
  osx_arm64: osx_64
provider:
  linux_ppc64le: default
  linux_aarch64: default
test: native_and_emulated
```

Mixing keys across shapes is a category error — `provider:` activates a
build leg, `build_platform:` routes the build host, `noarch_platforms:`
declares the test matrix for a single noarch artifact, and `test:` controls
whether emulated tests actually execute. The reference doc's "four-key
matrix" section explains how they interact.

## Workflow — 3 waves

### The two load-bearing workflow rules

These apply to every wave. Skim them once, then enforce them through
every step:

- **Local mirror is the source of truth — and the mirror must be
  COMPLETE.** `recipes/<feedstock>/` mirrors the entire feedstock's
  recipe-side state, not just `recipe.yaml`. Always-required files:
  `recipes/<feedstock>/recipe.yaml`, `recipes/<feedstock>/conda-forge.yml`
  (so `pixi run -e conda-smithy lint recipes/<feedstock>` works locally
  and the operator can preview smithy config alongside the recipe),
  `recipes/<feedstock>/LICENSE` (if upstream omits it from the sdist
  and the recipe ships its own), `recipes/<feedstock>/patches/*.patch`,
  and `recipes/<feedstock>/build.sh` / `build.bat` (when separate from
  `recipe.yaml`'s inline script). Editing only `recipe.yaml` is a
  partial mirror and a recurring source of "wait, where did
  conda-forge.yml come from?" bugs.

- **Edit local → verify-build local → mirror to fork → push → request
  rerender.** Every push to the feedstock fork branch — initial PR or
  CI-iteration fix — runs in that exact order:
  1. Apply the change to `recipes/<feedstock>/` (the local mirror) FIRST.
  2. Run `validate` + `lint-optimize` + `check-deps`.
  3. Run `pixi run -e local-recipes recipe-build recipes/<feedstock>` —
     **native build on the host platform**. Confirms the change doesn't
     regress. A Windows-only env-var (e.g. `PYTHONUTF8`) is also set on
     Linux/macOS — the local linux/macOS build is the verification.
     Skip this step at your peril.
  4. Mirror EVERY changed file to the feedstock fork checkout:
     `cp recipes/<feedstock>/recipe.yaml /tmp/<feedstock>-work/recipe/recipe.yaml`
     and `cp recipes/<feedstock>/conda-forge.yml /tmp/<feedstock>-work/conda-forge.yml`
     (and any other touched files). `git diff` the fork checkout vs
     `origin/<branch>` to confirm only intentional changes are present.
  5. `git commit` + `git push` to the fork branch.
  6. Post `@conda-forge-admin, please rerender` as a PR comment.
     ALWAYS — even when you only touched `recipe.yaml` and the
     conda-forge.yml is unchanged. The bot is idempotent (it exits clean
     when nothing needs regenerating); the cost of running it is near
     zero; the cost of NOT running it and watching CI burn against
     stale `.ci_support/*.yaml` is a confusing failed CI plus a re-push
     cycle.

The wave-by-wave procedure below assumes these two rules. Each step
either applies them or builds on them.

### Wave A — Sync the local mirror + verify upstream parity (offline-safe)

1. **Sync your fork of the feedstock against upstream:**
   ```
   gh repo sync <fork-owner>/<feedstock> --branch main
   ```
   Verify the fork's HEAD SHA matches `conda-forge/<feedstock>` main.

2. **Refresh `recipes/<feedstock>/` in this local-recipes repo** via the
   CFE `SKILL.md` § "Sub-workflow: Updating an existing recipe
   (diff-before-apply)" — apply to **every file** in the feedstock's
   recipe-side state, not just `recipe.yaml`:

   - `mv recipes/<feedstock> recipes/<feedstock>.current`
   - `generate_recipe_from_pypi(package_name="<feedstock>", version="<upstream-version>")`
   - `enrich_from_feedstock(recipe_path="recipes/<feedstock>/recipe.yaml")`
   - `diff -u recipes/<feedstock>.current/recipe.yaml recipes/<feedstock>/recipe.yaml`
   - 3-bucket categorise hunks (corrections / regressions / stylistic);
     present to operator before applying
   - On approval: restore the base, apply approved corrections only

   When the upstream feedstock already has a clean `recipe/recipe.yaml`
   at the target version (typical for autotick-bumped feedstocks), the
   simpler refresh path is `gh api repos/conda-forge/<feedstock>/contents/recipe/recipe.yaml --jq .content | base64 -d`
   → diff vs current local → apply if the only delta is `version` +
   `sha256` + maybe `build.number` reset.

   **Also mirror the feedstock's `conda-forge.yml`** to
   `recipes/<feedstock>/conda-forge.yml`. The first time you set up a
   feedstock for local-recipes mirroring, the file may not exist yet —
   create it by copying from the cloned feedstock. Don't skip this:
   subsequent waves edit `conda-forge.yml`, and per the load-bearing
   "local mirror = source of truth" rule, the edit lands locally first.

   **Verify the feedstock's actual SOURCE-KIND — never assume PyPI
   sdist (strong default).** Across a large bulk refresh, deployed
   feedstocks source from a **GitHub-tag archive** far more often than
   the grayskull regenerate path assumes — empirically the whole
   `wagtail-*` / `django-*` / `h2o-*` / `kedro` / `copilotkit` / `pypac`
   / `acachecontrol` / `collectfasta` / `spec-kit` batch sourced from a
   GitHub tag, not the PyPI sdist. Read the **deployed** `recipe.yaml`'s
   `source.url:` and mirror its kind; don't let grayskull's PyPI-sdist
   default silently change the source. Set the cached
   `cfe-source-kind` (`pypi-sdist | pypi-wheel | github-tag |
   github-commit`) to the **verified** value so a future regen can't
   revert it. (Also watch [SKILL.md G51] — a GitHub-source package may
   ship none of the release-time-generated assets; source the wheel
   instead.)

   **gh-tag-vs-PyPI numbering: a "behind" flag from version-number
   mismatch is usually REAL, not a false-positive — verify, don't
   assume parity.** When a recipe is flagged behind on a GitHub-tag
   numbering mismatch, the overwhelmingly common case is that it is
   *genuinely* behind with **aligned** numbering (the only delta is a
   `v` prefix on the tag). A true numbering false-positive (the GitHub
   tag and the PyPI version are different numbers for the **same code**)
   is rare and almost always an **npm-monorepo** package whose GitHub
   monorepo tag (`vX.Y.Z`) differs from the Python sub-package's PyPI
   version. Method to distinguish, in order:
   1. Read the **deployed feedstock's** actual `version:` + `source.url`
      (what's really shipping).
   2. Compare the **PyPI version history** vs the **GitHub tag history**
      — if they track each other (modulo `v` prefix), the recipe is
      genuinely behind; bump it.
   3. For a **monorepo** suspected false-positive: check the
      sub-package's declared `version` in its `pyproject.toml` **at the
      GitHub tag**, and confirm sha256 identity between the GitHub-tag
      artifact and the PyPI artifact. Same code under two numbers →
      true false-positive (leave as-is). Different code → genuinely
      behind.
   Empirically (Jun 2026 batch of 13 numbering-risk recipes): only
   **copilotkit** was a true false-positive (npm-monorepo GH tag
   `v1.57.2` == PyPI `copilotkit` `0.1.88`, same code, sha256-verified
   via the sub-package's `pyproject` `version` at the tag); the other
   12 were genuinely behind with aligned numbering.

   **A baseline "behind" list can misclassify a LOCAL-ONLY recipe as
   on-conda-forge — always `lookup_feedstock` to confirm existence
   before any C2 (rm-meta.yaml) transition.** A recipe flagged
   on-conda-forge may have **no feedstock at all**. Run
   `lookup_feedstock(pkg_name=<name>)`; if it returns `exists:false`,
   the recipe is local-only — set
   `cfe-on-conda-forge-status: pending-submission-to-conda-forge` and
   **do NOT `rm meta.yaml`** (there is no v0→v1 feedstock transition to
   complete; the keep-meta.yaml rule doesn't apply because there's no
   deployed v0 to mirror — but neither does the C2 delete). Also watch
   for **two-feedstock collisions**: the same upstream may be served by
   two different feedstocks sourcing differently (e.g. a `<name>-feedstock`
   github-tag vs a competing `<altname>-feedstock` pypi-sdist) — pick
   the one the local recipe actually mirrors and note the collision.
   Examples (Jun 2026): **cookiecutter-django** was flagged on-cf but
   has no feedstock (`exists:false`; PyPI abandoned at 1.11.9; sources a
   GitHub CalVer tag) → kept local-only, meta.yaml retained;
   **spec-kit** has our `spec-kit-feedstock` (github-tag) competing with
   a `specify-cli-feedstock` (pypi-sdist) for the same upstream.

3. **Validate + optimize + check-deps**:
   ```
   pixi run -e local-recipes validate recipes/<feedstock>
   pixi run -e local-recipes lint-optimize recipes/<feedstock>
   pixi run -e local-recipes check-deps recipes/<feedstock>
   ```
   Any warning is a Stop-the-Line moment per CFE Build Failure Protocol.

4. **Native build on host** (the platform the operator's machine runs):
   ```
   pixi run -e local-recipes recipe-build recipes/<feedstock>
   ```
   Expect a `.conda` under `build_artifacts/<host-subdir>/<host-subdir>/`.
   Per **G8b**: if `get_build_summary` returns `status: unknown`, check
   the artifact directory directly — file existence overrides false-negatives.

### Wave B — Edit `conda-forge.yml` and rerender

1. **Clone the fork** to a working directory:
   ```
   gh repo clone <fork-owner>/<feedstock> /tmp/<feedstock>-work
   cd /tmp/<feedstock>-work
   git checkout -b add-<target-platforms-slug>
   ```
   Branch name follows CFE convention: `add-<platforms>` (single
   descriptive name; the PR title carries the package + version intent).

2. **Edit `recipes/<feedstock>/conda-forge.yml` (the local mirror)
   first** with the minimal additive delta. The fork checkout's
   `/tmp/<feedstock>-work/conda-forge.yml` is updated by `cp` from the
   local mirror in step 5 below — never edit the fork checkout directly.
   For compiled recipes:

   ```yaml
   # Do NOT re-add keys already upstream (an existing feedstock already carries
   # conda_build_tool/conda_install_tool/bot — the universal pre-seed). The
   # platform-expansion delta for a COMPILED recipe is just the ARM matrix:
   build_platform:
     <new-target>: <build-host>    # e.g. linux_aarch64: linux_64, osx_arm64: osx_64
   provider:
     <new-target>: azure           # ENABLES the otherwise-disabled arch (field default is None)
   test: native_and_emulated       # runs the emulated aarch64/ppc64le tests under QEMU
   ```

   If the upstream feedstock predates the universal pre-seed and is missing the
   bot/tooling block, also add it (reference § Recommended pre-seed defaults).
   `workflow_settings.store_build_artifacts` is **optional** reviewer-convenience
   (win-exclude per G18), **not** part of the default.

   For noarch:python with platform-conditional selectors:

   ```yaml
   noarch_platforms:
     - linux_64
     - osx_64
     - <new-platform>
   ```

   Do **not** add keys that are already upstream (`bot.automerge`,
   `error_overlinking`, etc.). The PR should be the smallest diff that
   activates the new legs.

3. **Rerender via conda-smithy**:
   ```
   pixi run -e conda-smithy conda-smithy rerender
   ```
   Expected new files for each compiled-recipe target:
   - `.ci_support/<target>_python<X>.<Y>.____cpython.yaml` per Python variant
   - `.azure-pipelines/*.yml` updates for the new Azure legs

   If rerender produces **unrelated drift** (boilerplate refresh, new
   global pins), do not suppress it — inspect each diff, surface anything
   structural to operator, document in PR body. Rerender output is
   authoritative; the bot owns it.

4. **Local cross-target build attempts — diagnostic only**:

   For each new compiled target, attempt a cross-build using the
   variant-config that rerender just emitted:
   ```
   pixi run -e local-recipes rattler-build build \
     --recipe recipes/<feedstock> \
     --target-platform <target> \
     --variant-config /tmp/<feedstock>-work/.ci_support/<target>_pythonX.Y.____cpython.yaml \
     --output-dir build_artifacts/<target>
   ```

   **Outcomes that are OK:**
   - Green build → cross-toolchain works locally; CI is very likely green
   - Compile-fails-fast (no SDK / no cross-toolchain locally) → diagnostic
     value only; document in PR body, rely on conda-forge CI as the gate
   - Test phase skipped (can't execute non-host binaries) → expected

   **Outcome that is NOT OK:**
   - Cross-target solve failure (`check_dependencies` was green but the
     build solver disagrees) → Stop-the-Line; re-run `check_dependencies`
     with the rerender's emitted pin set to find the divergence

### Wave C — Branch, draft PR, operator gates, retro

1. **Verify-build local FIRST, then mirror to fork, then push, then
   request rerender.** This is the load-bearing five-step push
   procedure — apply it to the initial push AND to every CI-iteration
   fix push that follows:

   a. **Confirm local mirror is the intended final state.** All edits
      this wave landed in `recipes/<feedstock>/` (the local mirror) per
      the Wave-B rule, not directly in the fork checkout. The mirror's
      `conda-forge.yml` and `recipe.yaml` are what the operator and
      reviewers will see in the diff.

   b. **Run the local native build.**
      ```
      pixi run -e local-recipes recipe-build recipes/<feedstock>
      ```
      Even when the edit is "Windows-only" (e.g. adding `PYTHONUTF8`,
      a Windows-conditional dep, a build.bat fix), the env vars or
      selectors interact with linux/macOS too. The local build is the
      verification that you didn't regress the host. Skip this step
      at your peril.

   c. **Mirror EVERY changed file to the fork checkout.** Preserve the
      feedstock's directory shapes:
      ```
      cp recipes/<feedstock>/recipe.yaml /tmp/<feedstock>-work/recipe/recipe.yaml
      cp recipes/<feedstock>/conda-forge.yml /tmp/<feedstock>-work/conda-forge.yml
      # plus LICENSE / patches/ / build.sh / build.bat as applicable
      ```
      `git -C /tmp/<feedstock>-work diff` to confirm only the
      intentional changes are present (no stray reverts, no missed
      files).

   d. **Commit + push:**
      ```
      git -C /tmp/<feedstock>-work add conda-forge.yml recipe/ .ci_support/ .azure-pipelines/
      git -C /tmp/<feedstock>-work commit -m "Add <target-platforms>; <secondary-deltas>"
      git -C /tmp/<feedstock>-work push -u origin add-<target-platforms-slug>
      ```
      Single commit per logical change. Never `--no-verify`.

   e. **Post `@conda-forge-admin, please rerender` on the PR — every
      push, no exceptions:**
      ```
      gh pr comment <PR#> --repo conda-forge/<feedstock> \
        --body "@conda-forge-admin, please rerender"
      ```
      Even when you only touched `recipe.yaml` and `conda-forge.yml`
      didn't change, post the comment. The bot is idempotent — it
      exits clean when nothing needs regenerating. The cost of
      requesting is near zero; the cost of NOT requesting and burning
      CI cycles against stale `.ci_support/*.yaml` is much higher.
      The auto-rerender service IS smart enough to skip rerender on
      pure-recipe.yaml changes, but its timing is variable (sometimes
      minutes, sometimes longer). The explicit comment is fast and
      predictable.

2. **HALT — operator-confirm before opening PR.** Present:
   - `conda-forge.yml` diff (the new blocks only)
   - List of new `.ci_support/*.yaml` files (filenames only — contents are
     rerender boilerplate)
   - Cross-target build outcomes from Wave B step 4
   - Result of `check_dependencies` for each new subdir (must be green)

3. **Open DRAFT PR:**
   ```
   gh pr create \
     --repo conda-forge/<feedstock> \
     --base main \
     --head <fork-owner>:add-<target-platforms-slug> \
     --draft \
     --title "Add <target-platforms> to build matrix" \
     --body "<see template below>"
   ```

   PR body template:
   ```markdown
   ## Summary

   Adds <target-platforms> to the build-matrix providers in
   `conda-forge.yml`. <secondary-delta summary, e.g. workflow_settings.store_build_artifacts>.

   ## Why

   <package> is currently not installable from conda-forge on
   <target-platform-friendly-name>. <evidence: repodata grep, atlas
   package_health, user report>.

   The recipe's `requirements.build:` already carries
   <cross-compile-or-noarch scaffolding>, so no recipe-code change is
   needed — provider activation + rerender is sufficient.

   ## What changed

   - `conda-forge.yml`: <list deltas>
   - `.ci_support/*.yaml`: new variant configs for the added platforms
     (smithy rerender output)
   - `.azure-pipelines/`: pipeline config updated by rerender

   ## Local verification

   - Native build on <host-subdir>: <result>
   - Cross-target build attempts: <one line per target>

   ## Out of scope (deferred follow-ups)

   <enumerate any platforms ruled out, with the one-line reason>
   ```

4. **HALT — operator-confirm draft → ready-for-review.** Operator
   reviews the Azure CI runs (linux-aarch64 emulated CI is the slowest
   leg — expect 30–60 min). When **all** legs (existing + new) are
   green, operator runs `gh pr ready <PR>`. A conda-forge core member
   merges.

5. **Closeout retro** (per CLAUDE.md Rule 2 — always-on):
   - Review session logs, build outputs, CI logs, reviewer comments
   - Categorise findings: corrections / refinements / additions
   - Land findings as edits to `SKILL.md` / `reference/` / **this
     guide**; bump skill version per semver
   - Add a `CHANGELOG.md` entry — even if zero novel findings, write
     "no skill changes; verified existing guidance held for: <package>
     platform-matrix expansion to <targets>"

## Risk catalog

| Risk | Likelihood | Mitigation |
|---|---|---|
| New subdir CI fails because a transitive dep isn't built for the subdir yet | Low (if `check_dependencies` ran clean) | Pre-flight `check_dependencies` is non-optional; a green result is the prerequisite for opening the PR. If a gap exists, document the prerequisite feedstock that needs to ship first, file as a separate spec |
| `linux-aarch64` emulated CI exceeds the 6h Azure limit | Low | Most existing 3-platform CIs complete in <1h per leg; cross-compile via crossenv stays similar. If exceeded, request native runners via `provider.linux_aarch64: github_actions` or Cirun |
| Rerender introduces unrelated drift | Medium | Inspect each rerender diff; if unrelated, document in PR body. Don't suppress — rerender output is authoritative |
| Local cross-target build fails on host (no SDK, etc) | High (expected) | Non-gating per the "diagnostic only" rule. Document in PR body. conda-forge CI is the real gate |
| `error_overlinking: true` surfaces previously-tolerated overlinks on a new platform | Medium | Treat as Stop-the-Line per CFE Build Failure Protocol. Fix by tightening `host:` deps or adding `build.missing_dso_whitelist` only as last resort |
| Operator delay between draft-open and ready-for-review | Medium | Acceptable for <7 days. Past that, rebase on upstream main and re-push |
| Wrong `provider:` resolution (azure vs github_actions vs cirun) | Low | `default` resolves to Azure for compiled subdirs in mid-2026. Verify post-rerender by inspecting `.azure-pipelines/`. GHA opt-in (per skill ecosystem update, Mar 2026) is `linux_64`-only |

## Stop-the-Line conditions

Per CFE Build Failure Protocol, **halt and surface to operator** if any
of these surface during the workflow:

- A structural recipe change appears necessary (new `build.script:`
  branch, new `requirements:` entry, new patch). Provider activation
  alone should be sufficient; if it isn't, the recipe wasn't actually
  cross-compile-ready and the scope expands.
- `check_dependencies` is red on the target subdir → prerequisite
  feedstock needs to ship first.
- Rerender deletes existing platform configs (it should only add).
- The `error_overlinking: true` gate (already enabled on most modern
  feedstocks) trips for the new platform with an overlink that wasn't
  whitelisted on the existing platforms.
- The fork sync (`gh repo sync`) fails with non-fast-forward — fork has
  divergent commits the operator hasn't acknowledged.

## Cross-references

- CFE `SKILL.md` § "Sub-workflow: Updating an existing recipe
  (diff-before-apply)" — Wave A step 2
- CFE `SKILL.md` § Critical Constraints — schema header,
  `python_min`, `stdlib`, never-mix-formats
- CFE `SKILL.md` § G1 — tree-sitter glibc 2.17 CFLAGS fix (Rust+PyO3
  recipes; relevant to cross-compile scaffolding)
- CFE `SKILL.md` § G8b — `get_build_summary status: unknown`
  false-negative workaround
- CFE `SKILL.md` § G12 — `noarch_platforms` escape hatch (noarch:python
  only)
- CFE `SKILL.md` § G46–G51 — feedstock-refresh build-shape gotchas:
  stale-meta noarch-for-compiled (G46), stale recipe-dir CBC cruft (G47),
  Rust/Go ≠ heavy compile (G48), per-Python-compiled ≠ abi3 (G49),
  cap-the-python-matrix for dropped C-API / numpy floors (G50),
  github-source-ships-no-generated-assets → wheel (G51)
- CFE `reference/conda-forge-yml-reference.md` — `provider:`,
  `workflow_settings.store_build_artifacts:` (replaces deprecated
  `azure.store_build_artifacts`), bot config keys, `noarch_platforms`,
  `build_platform`, `test`
- CFE `guides/cross-compilation.md` — cross-toolchain mechanics
  (crossenv, cross-python, maturin)
- CFE `guides/feedstock-maintenance.md` — general feedstock-rerender
  / branch / PR mechanics
- `docs/specs/feedstock-platform-expansion.md` — BMAD-consumable spec
  parameterized for any feedstock; carries per-case empirical state
- CLAUDE.md § "BMAD ↔ conda-forge-expert integration" — Rule 1 (BMAD
  must invoke CFE) + Rule 2 (closeout retro mandatory)
