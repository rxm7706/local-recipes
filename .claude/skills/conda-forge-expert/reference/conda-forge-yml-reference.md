# conda-forge.yml Reference

A practical reference for the keys that come up most often when shipping a
recipe through `conda-forge/staged-recipes` or maintaining a feedstock.
This file is the **curated, opinionated subset**: the keys you actually
edit, what they do, when to use them, what to leave alone, and four
canonical YAML shapes for the common cases. It does **not** mirror the
full schema — that's a separate file.

- **Curated subset (this file)** — the high-signal keys with rationale,
  "when to set" guidance, and worked examples. Read this when authoring
  or reviewing a `conda-forge.yml`.
- **Exhaustive auto-generated reference** —
  [`conda-forge-yml-reference-full.md`](conda-forge-yml-reference-full.md)
  is auto-generated from the upstream conda-smithy JSON Schema by
  `pixi run -e local-recipes gen-yml-reference`. Mirrors every key
  (top-level + `$defs`) with type, default, description, and enum
  values. Read this when you need completeness — every `azure.*`,
  every `bot.*`, every `github_actions.*` sub-key.
- **Canonical upstream docs** —
  <https://conda-forge.org/docs/maintainer/conda_forge_yml/> (kept in
  sync with `conda-smithy`'s validator). Read this when you suspect
  the local generator is out of date or want narrative context.
- **Concrete YAML templates** — the templates dir ships ready-to-copy
  starting points:
  [`templates/conda-forge-yml/staged-recipes/conda-forge.yml`](../templates/conda-forge-yml/staged-recipes/conda-forge.yml)
  and [`templates/conda-forge-yml/feedstock/conda-forge.yml`](../templates/conda-forge-yml/feedstock/conda-forge.yml).

## Where the file lives

| Context | Path | Scope |
|---|---|---|
| **staged-recipes PR** (per-recipe override) | `recipes/<name>/conda-forge.yml` | Affects only this recipe's PR build. Lifetime ends when the recipe is merged and a feedstock is created. |
| **Feedstock** | `<pkg>-feedstock/conda-forge.yml` (root) | Permanent config consumed by `conda smithy rerender` to regenerate `.azure-pipelines/`, `.github/workflows/`, etc. |
| **staged-recipes itself** (repo root) | `staged-recipes/conda-forge.yml` | Sets defaults for **all** PRs going through staged-recipes. Maintained by conda-forge org admins. Don't edit in a recipe PR. |

The per-recipe file is overlay-style: merged on top of the staged-recipes
root file. You only set the keys that need to differ from the default.

## Top use cases (rationale)

The templates show the YAML; this section explains *why* you'd set each key.

### The four-key matrix: `provider`, `build_platform`, `noarch_platforms`, `test`

These four keys interact and almost always change together. Setting one
without thinking about the others usually produces a misconfigured leg.

| Key | What it declares | Affects |
|---|---|---|
| `provider.<target>` | Which CI service handles the build leg for `<target>` (`default` = Azure; `github_actions` since smithy 3.57.1 for `linux_64`; `cirun-openstack-gpu-large` for self-hosted GPU; etc.). Set to `None` to disable a default-on platform. | CI service selection |
| `build_platform.<target>` | The **host** on which the build leg for `<target>` actually runs. Mapping is `<target>: <build_host>`. For compiled recipes this is a true cross-compile (or rosetta) instruction. For noarch this is just "where the build leg's runner lives" — the produced artifact is still a single noarch package. | Cross-compilation, native-Apple-silicon usage, win-arm64 cross |
| `noarch_platforms` | For noarch:python recipes only — the set of subdirs the smithy generates **test legs** for. Does **not** produce multiple artifacts; the artifact is still one noarch `.conda` published under `noarch/`. Generates one `.ci_support/<target>_*.yaml` per listed subdir. | Test coverage for noarch packages |
| `test` | Whether emulated test legs actually run their tests. Enum: `all` / `native` / `native_and_emulated` (default). Use `native` to skip the slow emulated test step (build still runs); use `native_and_emulated` to run both. | Test execution under emulation |

**Compiled-recipe interaction**: `provider:` + `build_platform:` is the
cross-compile lever. `noarch_platforms:` does not apply (not a noarch
recipe). `test:` only matters if any platform leg is emulated.

**Noarch-recipe interaction**: `noarch_platforms:` declares the test
matrix. `build_platform:` typically routes the build for each listed
subdir to a real host (`linux_aarch64: linux_64` = "run the linux_aarch64
test leg on a linux_64 host with qemu"). `provider:` activates each
test leg's CI. `test: native_and_emulated` runs the tests on both the
native host and the emulated target.

### `workflow_settings.store_build_artifacts: true`

Default CI runs discard `build_artifacts/` after the build/test step.
Setting this flag publishes the entire tree (including the built `.conda`)
as a downloadable pipeline artifact (Azure or GitHub Actions, whichever
provider is in use).

- Reviewers can grab the package and test it in a real env before approving.
- You can do the same: drop the `.conda` into `mamba create -n test --use-local <name>`
  and smoke-test imports / CLI / entry points against a clean env.
- Especially useful for recipes that ship MCP servers, entry points, or
  other surfaces where "CI was green" is a weaker signal than a hands-on test.

Accepts a simple boolean or a list of conditional values:

```yaml
# Simple form — turn on for every provider/platform
workflow_settings:
  store_build_artifacts: true

# Conditional form — scope to a provider, OS, or platform
workflow_settings:
  store_build_artifacts:
    - provider: github_actions
      value: true
    - platform: [osx_arm64, linux_aarch64]
      value: true
```

> **⚠️ Rust + Windows trap (CFE gotcha G18).** Unscoped `true` crashes
> the Windows Azure leg on Rust-heavy recipes (anything pulling
> tree-sitter / hyper / tower / reqwest / rustls). The 7z archive step
> hits Windows winhttp's `AppData\Local\Microsoft\Windows\INetCache\Content.IE5`
> directory inside the build sandbox — restricted ACLs cause 7z to exit 1
> and the `Prepare conda build artifacts` task to fail even though the
> build itself succeeded. **Default for Rust feedstocks:** scope to
> non-Windows via the conditional list form
> (`platform: [linux_64, linux_aarch64, osx_64, osx_arm64]`). See
> [`SKILL.md` § G18](../SKILL.md#g18-workflow_settingsstore_build_artifacts-true-unscoped-crashes-windows-azure-builds-via-7z--inetcache-acls)
> for the full diagnosis + upstream-fix note.

> **`azure.store_build_artifacts` is deprecated** (schema description:
> "Use `workflow_settings.store_build_artifacts` instead"). The old key
> still works for backward compatibility but emits a smithy-lint warning
> and is removed at the next rerender. Any new or refreshed feedstock
> should use `workflow_settings.store_build_artifacts`.

### `os_version: { linux_64: alma9 }`

Default Linux build uses `cos7` (glibc 2.17). Bump only as far as your
code actually needs — going higher than necessary narrows the user base.

- `alma8` → glibc 2.28
- `alma9` → glibc 2.34 (current recommended)
- `alma10` / `rocky10` → glibc 2.38+
- `ubi8` → Red Hat UBI 8 (enterprise)

### `provider.linux_64: github_actions`

Available since conda-smithy 3.57.1 (March 2026). Use only when Azure is
contended or you need higher GA concurrency. Windows / macOS still build
on Azure regardless of this setting.

### `bot.version_updates.exclude`

Add a tag to the exclude list when the autotick bot keeps mis-detecting it
as a release (typical for upstream `1.0.0rc1`-style pre-release tags that
your project doesn't ship). Workflow: comment on the bot's bad PR, close
it, then add the tag to `exclude:` in your next bump.

### `noarch_platforms`

Default is `[linux_64]` for noarch packages. **Adding more platforms is
pure waste for most pure-Python recipes** — the artifact is a single
platform-independent `.conda` regardless of where it's built, so the
extra subdirs only generate **test legs**, not different artifacts.
Each extra leg is one more chance for a flake (Windows antivirus
scanning the build dir, transient PyPI 503, Azure agent quirk) to make
the PR red without changing what gets published.

**Only enable additional subdirs when the package has *platform-conditional
runtime behavior*** — meaning the Python code actually does something
different on different platforms. Signals that justify it:

- `if sys.platform == "win32":` / `if os.name == "nt":` branches
- `subprocess.run(["powershell", …])` or invocations of a native CLI
  whose Windows variant differs
- Hardcoded path separators (`"foo\\bar"` vs `"foo/bar"`)
- `pathlib.PureWindowsPath` / `PurePosixPath` selection at runtime
- Platform-conditional optional `run:` deps in `recipe.yaml`
  (`if: win` → different dep set)
- Test suite includes Windows-only edge cases the maintainer wants
  validated on every bump

**Counter-examples — do NOT add platforms for:** pure-Python
visualization helpers (vizro-ai-class), data-science utilities, web
frameworks without OS-conditional logic, SDK wrappers around a network
API, library helpers with only cross-platform stdlib calls. A Linux
test is conclusive for these.

If you can't name a specific Python branch or test that depends on the
platform, leave `noarch_platforms` at the default and ship faster.
(Lesson learned the hard way on a vizro-ai PR where six platforms were
added speculatively, generating five red Windows reruns from
antivirus + file-lock flakes that had zero effect on the published
artifact.)

### Per-job `timeout_minutes`

Default ~360 (6 hours) on both Azure and GitHub Actions. Raise only with
a real reason — long builds usually have a fixable underlying issue. Ask
in the conda-forge Zulip channel before doubling timeouts.

### `bot.inspection`

Tells the autotick bot how to regenerate the recipe on a version bump.
The schema enum has 7 values:

| Value | Behavior | When to choose |
|---|---|---|
| `hint` | Bot only opens a hint PR with the new version; doesn't modify files | Recipe needs human attention on every bump (complex patches, multi-output) |
| `hint-all` | Like `hint` but inspects multiple sources (grayskull, upstream changelog, …) | Same as `hint` but you want richer notes from the bot |
| `hint-source` | Hints by inspecting source archive only | Rarely used; mostly subsumed by `hint-all` |
| `hint-grayskull` | Hints by running grayskull against the new release | Same as `hint-all` but constrained to grayskull's view |
| `update-source` | Bot regenerates `source.url` + `sha256` only, no further changes | Recipe is hand-tuned and only the source block should change |
| `update-grayskull` | Bot regenerates dependencies via grayskull | **Most common modern choice** — works well for pure-Python and most compiled recipes if `requirements:` doesn't carry hand-crafted constraints |
| `update-all` | Bot runs all available updaters | Aggressive; use only when you actively want bot-managed deps + source + tests |

Default for a freshly-generated recipe: `update-grayskull`. Switch to
`hint-all` if grayskull keeps fighting hand-tuned constraints (typical
for recipes with vendored deps or selective `host:` pins).

### `conda_install_tool` / `conda_build_tool`

| Key | Values | Modern default |
|---|---|---|
| `conda_install_tool` | `mamba` / `micromamba` / `pixi` / `conda` | **`pixi`** for new feedstocks (faster, deterministic; landed as conda-forge default in 2025-Q4) |
| `conda_build_tool` | `conda-build` / `rattler-build` / `conda-build+conda-libmamba-solver` | **`rattler-build`** for new feedstocks (faster, recipe-v1 native) |

Both keys are **consumed inputs, not rerender outputs** — `conda smithy
rerender` reads them to provision tooling and (for `conda_build_tool`) to
**select the recipe file** (`rattler-build` ⇒ smithy looks for `recipe.yaml`);
it does **not** auto-derive or rewrite them from recipe shape (a widely-held
misconception). A v1 `recipe.yaml` feedstock therefore needs
`conda_build_tool: rattler-build` set **explicitly** — the schema default is
`conda-build` (which can't parse v1), and `conda_install_tool` defaults to
`micromamba` (so `pixi` is a deliberate non-default, not a restated one).
Override the tool only to work around a specific bug; bump back at the next
release. (See the § "Per-setting applicability audit" table below for which
keys are genuinely auto-managed by rerender — only the CI-provider blocks
`azure`/`github_actions`/… are; none of the keys in this section are.)

### `conda_build.pkg_format: '2'`

Set to `'2'` to produce `.conda` artifacts (zstd-compressed,
parallel-decompress) instead of legacy `.tar.bz2`. Sensible default for
new recipes. The pixi-feedstock sets this explicitly because its
recipe was created before pkg_format 2 was the implicit default.

### `conda_build.error_overlinking: true`

Errors instead of warns when a binary links to a library not declared in
`requirements.host:`. Catches missing run-deps at build time. Already
default on most modern feedstocks; only relevant to set explicitly when
adopting it on a recipe that previously tolerated overlinking. Once
turned on, treat any overlink as Stop-the-Line per Build Failure Protocol.

### `conda_forge_output_validation: true`

Validates the produced `.conda` against the conda-forge output policy
(name allowlist, channel target, etc.). Mandatory `true` for every
feedstock under the `conda-forge` org. Leave on.

### `bot.check_solvable: true` and `bot.run_deps_from_wheel: true`

| Key | Purpose |
|---|---|
| `check_solvable` | Before opening a bump PR, the bot solves the environment to verify the new version actually resolves. Saves CI time on impossible bumps |
| `run_deps_from_wheel` | When grayskull-updating, pull `requirements.run:` straight from the wheel's metadata instead of inferring. Higher fidelity |

Both default-on for new feedstocks and almost never worth turning off.

### Azure resource tuning: `azure.force`, `azure.free_disk_space`, `azure.max_parallel`, `azure.settings_*`

When a feedstock's Azure CI is resource-constrained — running out of
disk, queuing forever, or producing flaky timeouts — these knobs let you
tune the Azure execution environment without touching the recipe.

| Key | Type | Default | Purpose |
|---|---|---|---|
| `azure.force` | bool | `false` | Force every build leg onto Azure even if `provider:` would route it elsewhere. Almost always leave at default; setting `true` mainly useful for debugging provider-routing bugs |
| `azure.free_disk_space` | bool or list | `false` | Run a Linux cleanup pass (delete `/usr/share/dotnet`, `/usr/local/lib/android`, etc) before the build to recover ~30 GB. Set `true` for recipes whose host deps + checkout exceed the default Azure agent's free disk (typical thresholds: numpy/scipy + opencv stacks, anything pulling pytorch, large npm trees) |
| `azure.max_parallel` | int | `25` | Cap concurrent Azure jobs across the feedstock's matrix. Lower (e.g. `15`) to be a good citizen on the shared Azure pool when the feedstock has a wide matrix (Python × OS × variant). Higher (rare) only with Zulip coordination |
| `azure.settings_linux.swapfile_size` | str (e.g. `"4GiB"`) | none | Add a swapfile of the named size before the build. Helps for memory-bound link steps (`ld` OOM on chromium/qt-style recipes) |
| `azure.settings_win.timeoutInMinutes` | int (minutes) | `360` | Per-job timeout override for Windows legs. Raise sparingly; default 6 h is already generous |
| `azure.settings_win.variables.CONDA_BLD_PATH` | str | (default) | Override the build directory on Windows. Useful when the default path (`C:\bld\...`) hits the Windows MAX_PATH limit on deeply-nested vendor archives |

Worked example — apache-superset's noarch matrix with Azure tuning:

```yaml
azure:
  # Default — declarative; documents that we are NOT forcing every leg
  # onto Azure. Provider routing in `provider:` below is authoritative.
  force: false
  # Superset's host deps + npm + sourcemaps occasionally blow past
  # the default Azure Linux runner's free disk. Cleanup pass recovers
  # ~30 GB. Cheap to leave on for noarch builds.
  free_disk_space: true
  # Cap concurrent jobs to 15 (default is 25). Six noarch_platforms ×
  # ~3 Python variants = ~18 potential legs; capping at 15 stops the
  # feedstock from monopolizing the shared Azure pool on bumps.
  max_parallel: 15
```

These keys are Azure-specific. They have no effect on GitHub Actions
legs (`provider.linux_64: github_actions`) or self-hosted runners. For
GHA-specific knobs see the `github_actions:` block (managed by smithy;
rarely hand-edited).

---

## Canonical conda-forge.yml shapes

Three end-to-end shapes that cover ~90% of feedstocks. Use these as
starting points and adjust per the matrix above.

### Shape 1 — Compiled, minimal expansion (single new arch)

For a compiled recipe that already ships on `linux_64`/`osx_64`/`win_64`
and needs `osx_arm64` (or another single arch) added. **No** cross
mapping — `osx_arm64` builds natively on Apple-silicon Azure runners.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/conda-forge/conda-smithy/main/conda_smithy/data/conda-forge.json
github:
  branch_name: main
  tooling_branch_name: main
conda_install_tool: pixi
conda_build_tool: rattler-build
conda_build:
  pkg_format: '2'
  error_overlinking: true
conda_forge_output_validation: true
workflow_settings:
  store_build_artifacts: true
provider:
  osx_arm64: default
  linux_aarch64: default
bot:
  automerge: true
  inspection: update-grayskull
  check_solvable: true
  run_deps_from_wheel: true
```

Live exemplar: **cocoindex** post-this-spec.

### Shape 2 — Compiled, multi-arch with cross-build hosts (pixi-feedstock)

For a compiled recipe widely used on alt-arch hosts. Adds
`build_platform:` to route certain targets to specific hosts (Apple
silicon for `osx_64` via Rosetta; `win_64` cross-host for `win_arm64`).

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/conda-forge/conda-smithy/main/conda_smithy/data/conda-forge.json
github:
  branch_name: main
  tooling_branch_name: main
conda_install_tool: pixi
conda_build_tool: rattler-build
conda_build:
  error_overlinking: true
conda_forge_output_validation: true
build_platform:
  osx_64: osx_arm64      # build osx_64 on Apple silicon (Rosetta)
  win_arm64: win_64      # cross-build win_arm64 on win_64
provider:
  osx_arm64: default
  linux_aarch64: default
test: native_and_emulated
```

Live exemplar: **pixi-feedstock**
([conda-forge/pixi-feedstock](https://github.com/conda-forge/pixi-feedstock/blob/main/conda-forge.yml)).

Note pixi-feedstock omits `workflow_settings.store_build_artifacts`
(defaults to `[]` = off); add `workflow_settings: { store_build_artifacts: true }`
if you want reviewer smoke-tests via the v8.14.0 `pr-artifacts` pattern.

### Shape 3 — Noarch:python, multi-arch coverage (apache-superset)

> **Before copying this shape: justify each subdir.** A noarch:python
> recipe produces ONE platform-independent `.conda` regardless of where
> it builds. Extra subdirs in `noarch_platforms` only add **test legs**
> — every Windows/aarch64/ppc64le leg is another chance for a flake
> (antivirus, file-lock, agent quirk) to redden the PR without changing
> the published artifact. Apache-superset earns the matrix because it
> branches on platform at runtime (subprocess invocations, path
> handling). If your recipe is a pure-Python helper with no
> `if sys.platform == "win32"` branches, no subprocess to native CLIs,
> no hardcoded path separators — **use [`linux_64]` and stop.** See the
> § "noarch_platforms" rule above for the full justification list.

For a noarch:python recipe whose runtime behavior **is** platform-sensitive
(uses subprocess, file paths, native CLI invocations) and should be
tested under multiple architectures even though only one artifact ships.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/conda-forge/conda-smithy/main/conda_smithy/data/conda-forge.json
github:
  branch_name: main
  tooling_branch_name: main
conda_install_tool: pixi
conda_build_tool: rattler-build
conda_build:
  pkg_format: '2'
conda_forge_output_validation: true
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
bot:
  automerge: true
  inspection: update-grayskull   # or hint-all if grayskull fights hand-tuned deps
  check_solvable: true
  run_deps_from_wheel: true
```

Live exemplar: **apache-superset** (this repo's local mirror at
`recipes/apache-superset/conda-forge.yml`).

Note: `error_overlinking` is omitted from Shape 3 because there are no
native binaries to overlink. Adding it is harmless but a no-op.

### Shape 4 — Comprehensive noarch + Azure tuning + reviewer artifacts

Same recipe shape as Shape 3 (noarch:python, multi-arch coverage) but
with **Azure resource tuning** and **reviewer-smoke-test artifacts**
turned on. Use when the feedstock has a wide matrix (~15+ legs) and
heavy host deps (numpy + scipy + opencv + npm; pytorch; chromium-class
deps; large CSS/JS pipelines). Every key is annotated docstring-style
so a future maintainer reading the file can answer "why is this here?"
without leaving the file.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/conda-forge/conda-smithy/main/conda_smithy/data/conda-forge.json

# ============================================================
# Reviewer & operator workflow knobs
# ============================================================

# Publish the entire build_artifacts/ tree (including the built `.conda`)
# as a downloadable CI pipeline artifact. Reviewers (and the maintainer)
# can then `pixi run -e local-recipes pr-artifacts <pr#>` to drop the
# package into a local file:// mamba channel and smoke-test imports /
# entry points before approving. Replaces the deprecated
# `azure.store_build_artifacts` per the conda-smithy schema.
# Schema default: [] (off). Accepts bool OR a list of conditional
# {provider/os/platform, value} objects for scoped activation.
workflow_settings:
  store_build_artifacts: true

# ============================================================
# Azure resource tuning (Azure-specific; no effect on GHA legs)
# ============================================================
azure:
  # `false` = do NOT force every build leg onto Azure regardless of
  # `provider:` routing. Default. Setting `true` is mainly for debugging
  # provider-routing bugs. Documenting it as `false` makes maintainer
  # intent explicit.
  force: false

  # Run a Linux pre-build cleanup pass (delete /usr/share/dotnet,
  # /usr/local/lib/android, large preinstalled SDKs) to recover ~30 GB
  # on the Azure agent. Set true when host deps + checkout + build
  # output push past the default agent's free disk. Common triggers:
  # numpy + scipy + opencv stacks, anything pulling pytorch, large
  # npm trees with sourcemaps. Cheap on noarch builds; leave on.
  free_disk_space: true

  # Cap concurrent Azure jobs at 15 (schema default: 25). With six
  # noarch_platforms × ~3 Python variants × test legs, the matrix can
  # easily produce 18+ concurrent jobs. Capping prevents this feedstock
  # from monopolizing the shared conda-forge Azure pool on a bump.
  # Lower further (e.g. 8) for very wide matrices; raise (rare) only
  # after coordinating in the conda-forge Zulip CI channel.
  max_parallel: 15

# ============================================================
# Repository wiring
# ============================================================
github:
  # Default branch name for the feedstock repo. `main` is the modern
  # default; older feedstocks still on `master` should migrate.
  branch_name: main
  # Branch conda-smithy targets when proposing tooling updates
  # (rerender bumps, schema migrations). Almost always tracks
  # `branch_name`; only diverges in feedstocks that stage tooling
  # changes on a separate branch.
  tooling_branch_name: main

# ============================================================
# Build engine + linker policy
# ============================================================
conda_build:
  # Error (don't just warn) when a binary links to a library not
  # declared in `requirements.host:`. Catches missing run-deps at
  # build time. No-op for pure noarch:python recipes (no native libs
  # to link), but keep it for any compiled outputs the feedstock may
  # add later. Treat any overlink as Stop-the-Line per Build Failure
  # Protocol.
  error_overlinking: true

# Validate the produced `.conda` against the conda-forge output policy
# (name allowlist, channel target alignment, etc). Mandatory `true`
# for every feedstock under the conda-forge org.
conda_forge_output_validation: true

# ============================================================
# Bot policy (cf-autotick-bot — automated version-bump PRs)
# ============================================================
bot:
  # On a successful autotick PR (green CI, no diff conflicts), merge
  # automatically without human review. Saves maintainer attention on
  # routine bumps. Pair with `check_solvable` + `run_deps_from_wheel`
  # so the bot doesn't open dead-end PRs. NOTE: this only applies to
  # automated version-bump PRs — manually-opened PRs (like this
  # feedstock-platform-expansion PR) still merge by hand.
  automerge: true

  # How the bot regenerates the recipe on a version bump. 7 enum values:
  #   hint / hint-all / hint-source / hint-grayskull
  #     → bot opens a hint PR; doesn't modify files
  #   update-source       → bot regenerates source.url + sha256 only
  #   update-grayskull    → bot regenerates deps via grayskull (modern default)
  #   update-all          → bot runs every available updater
  # Use `update-grayskull` when the recipe's `requirements:` are
  # grayskull-derivable. Switch to `hint-all` if grayskull keeps
  # fighting hand-tuned constraints (vendored deps, selective pins).
  inspection: update-grayskull

  # Before opening a bump PR, the bot solves the environment to verify
  # the new version actually resolves on conda-forge. Saves CI minutes
  # on impossible bumps. Default-on; almost never worth turning off.
  check_solvable: true

  # When grayskull-updating, pull `requirements.run:` straight from
  # the wheel's METADATA file instead of inferring from sdist. Higher
  # fidelity for projects with extras-style optional deps.
  run_deps_from_wheel: true

# ============================================================
# Build tooling (modern defaults)
# ============================================================
# Environment provisioning tool. `pixi` landed as conda-forge's
# default in 2025-Q4 — faster, deterministic, lock-file-driven.
# Alternatives: `mamba`, `micromamba`, `conda` (legacy fallback).
conda_install_tool: pixi

# Recipe execution engine. `rattler-build` is recipe-v1 native and
# faster than legacy conda-build for most recipes. Override to
# `conda-build` only for recipes hitting a known rattler-build bug;
# bump back at the next bump.
conda_build_tool: rattler-build

# ============================================================
# Platform matrix (noarch:python with multi-arch test coverage)
# ============================================================

# Subdirs the smithy generates TEST LEGS for. Does NOT produce
# multiple artifacts — the artifact is still ONE noarch `.conda`
# published under `noarch/`. Each listed subdir gets its own
# `.ci_support/<subdir>_*.yaml` and runs the recipe's test phase
# under that subdir's runtime. Listing platforms here is how a
# noarch:python recipe gets coverage on aarch64, ppc64le, etc
# without changing the artifact.
noarch_platforms:
  - linux_64
  - win_64
  - osx_64
  - osx_arm64
  - linux_ppc64le
  - linux_aarch64

# Maps <test-target-subdir>: <build-host-subdir>. For noarch this
# routes WHERE THE BUILD LEG'S RUNNER LIVES — the produced artifact
# is platform-agnostic, but the host that executes the build script
# still runs on real hardware. Setting e.g. `osx_arm64: osx_64`
# means "the osx_arm64 test leg runs on an osx_64 host with the
# noarch artifact tested against the osx_arm64 runtime profile."
# Useful when native runners for a target subdir are slow, scarce,
# or absent (Apple-silicon CI was scarce pre-2024; emulated aarch64
# is slower than native linux_64 + cross-test).
build_platform:
  linux_aarch64: linux_64
  linux_ppc64le: linux_64
  osx_arm64: osx_64

# CI service per target subdir. `default` = Azure (the established
# provider for non-linux_64 subdirs in 2026). Set to `github_actions`
# only on `linux_64` since smithy 3.57.1; set to `None`/`False` to
# DISABLE a default-on platform. Sub-keys here only need entries for
# the subdirs being ADDED — existing subdirs (linux_64, osx_64, win_64,
# osx_arm64) default-route to Azure without being listed.
provider:
  linux_ppc64le: default
  linux_aarch64: default

# Test execution mode under emulation. Enum:
#   `native`              → only run tests natively; skip emulated tests
#   `native_and_emulated` → run tests both natively AND under emulation
#                          (default and recommended for cross-arch coverage)
#   `all`                 → run every available test mode
# `native_and_emulated` validates that the noarch artifact actually
# works on each target subdir's emulator — catches subprocess/path
# bugs that a linux_64-only test would miss.
test: native_and_emulated
```

Diff from Shape 3 → Shape 4:

| Addition | Why |
|---|---|
| `azure.force: false` | Documents intent (default is `false`); makes the absence of forced-Azure routing explicit for future readers |
| `azure.free_disk_space: true` | Recovers ~30 GB on the Linux Azure agent; cheap insurance for heavy-host-deps recipes |
| `azure.max_parallel: 15` | Caps Azure concurrency below the 25 default to be a good citizen on the shared pool |

Shape 4 is the **most heavily-annotated reference shape**. Use it as
the source for inline-comment patterns when authoring a new feedstock's
`conda-forge.yml` — copy the comment style for keys you keep, drop the
comments for keys you remove.

---

## Less-common but useful

| Key | What it does | When to set |
|---|---|---|
| `azure.upload_packages` | Whether the build job uploads to anaconda.org. | `false` to skip uploads on a feedstock used only internally. |
| `channel_priority` | `strict` / `disabled` / `flexible`. | `strict` (recommended) prevents conda-forge / defaults mixing. |
| `channels.sources` | Channels to pull build deps from. | Add a private channel for deps not yet on conda-forge. |
| `channels.targets` | Where built packages get uploaded. | Default `conda-forge`; rarely changed. |
| `conda_forge_output_validation` | Validates the built `.conda`. | Default `true`; leave on. |
| `recipe_dir` | Directory containing `recipe.yaml`. | Default `recipe`; multi-recipe feedstocks override. |
| `linter.skip` | conda-smithy lint codes to skip. | Sparingly, with a written justification. |
| `linux_aarch64` / `linux_ppc64le` | Build on emulated runners. | Only if your package has architecture-specific code worth testing. |
| `idle_timeout_minutes` | Cancel CI if no log output for N minutes. | Raise from default if you have legitimate quiet phases. |

## Don't bother with these (deprecated or harmful)

| Key | Why to skip |
|---|---|
| `compiler_stack` | Removed; the `compiler()` macro resolves global pins. Delete from any existing `conda-forge.yml`. |
| `build_with_mambabuild` | Boa / mamba-build deprecated; rattler-build is the path forward. |
| `clone_depth` | Almost never the right knob; conda-forge handles checkout depth automatically. |
| `pinning` | Don't override conda-forge-pinning; rerendering will overwrite. |
| `provider.linux_aarch64: default` (Travis) | Travis is gone; use Cirun or Azure (emulated). |
| `azure.store_build_artifacts` | Deprecated. Use `workflow_settings.store_build_artifacts` (top-level — accepts `true`, or a list of `{provider/os/platform, value}` objects for scoped activation). |

## Per-setting applicability audit (deep-research + adversarial, Jun 2026)

> Sourced by tracing the conda-smithy schema (`conda_smithy/schema.py`), the
> autotick-bot schema (`cf_tick_schema.json`), and
> **`staged-recipes/.ci_support/build_all.py`** directly, cross-checked against
> the canonical Rust+PyO3 exemplar **`pydantic-core-feedstock`**. It answers, for
> every key: *restated-default, no-op, or load-bearing?* · *which recipe TYPES is
> it for?* · *does it do anything in a staged-recipes PR, or only the feedstock?*

### Crucial mechanism — a staged-recipes per-recipe `conda-forge.yml` is almost entirely INERT in the PR

`build_all.py` reads **exactly one key** from `recipes/<name>/conda-forge.yml`:
`conda_build_tool` (and only to toggle the legacy mambabuild path). The build
**matrix is repo-fixed** (`.ci_support/{linux64,osx64,win64,linux64_cuda12x}.yaml`
+ the Azure pipeline `--arch` arg — there is **no osx_arm64 / linux_aarch64 /
ppc64le leg pre-merge**, see [G82](../SKILL.md)); the rattler-vs-conda-build choice
is actually made by **`recipe.yaml`-vs-`meta.yaml` presence**, not by
`conda_build_tool`; the Linux image + CUDA are **auto-detected from recipe text**
(`sysroot_linux-64` / `c_stdlib_version==2.17` → `cos7`; `"cuda"` → CUDA variants),
not from `os_version`. **Every other key** — `provider`, `build_platform`,
`noarch_platforms`, `test`, `os_version`, `conda_forge_output_validation`, all
`bot.*`, `github.*`, `shellcheck`, `error_overlinking`,
`workflow_settings.store_build_artifacts` — is **unread in the PR**; conda-smithy
**forwards** the whole file into the new feedstock's `conda-forge.yml` on merge,
where those keys finally activate.

**So a per-recipe staged-recipes `conda-forge.yml` should usually carry only
`conda_build_tool: rattler-build`** (for a v1 recipe) — plus, *deliberately and
knowing they do nothing yet*, any keys you want **pre-seeded into the feedstock**
(e.g. `provider: {osx_arm64: azure}` to enable Apple Silicon day-one,
`noarch_platforms`, `os_version`). Everything else is inert-and-forwarded or pure
cargo-cult in the PR.

> **Corrects [G77](../SKILL.md).** The downloadable `conda_pkgs_{linux,noarch,osx}`
> artifacts on a staged-recipes PR are published **unconditionally by the fixed
> pipeline** — `build_all.py` never reads `workflow_settings.store_build_artifacts`,
> and the gated 7z `Prepare conda build artifacts` task (the one G18's win-crash is
> about) **doesn't exist in staged-recipes at all**. So `store_build_artifacts` is a
> **no-op in a staged-recipes PR** (you get `conda_pkgs_*` either way); it is
> load-bearing **only at the feedstock**. The G77 "it works in the PR" reading was a
> misattribution.

### Per-setting table — default · classification · recipe types · staged-PR vs feedstock

Classification key: **LOAD-BEARING** (does real work) · **REDUNDANT-DEFAULT**
(restates the schema default) · **NO-OP** (inert in this context/type) ·
**POLICY** (deliberate maintainer choice, not a no-op).

| key | schema default | relevant recipe TYPES (load-bearing) / no-op for | staged-recipes PR | feedstock |
|---|---|---|---|---|
| `conda_build_tool: rattler-build` | `conda-build` | **all v1** recipe.yaml types · no-op on v0 | **the one key read** (mambabuild toggle; rattler path actually picked by `recipe.yaml` presence) | LOAD-BEARING (v1 parser) |
| `conda_install_tool: pixi` | `micromamba` | all v1 (feedstock provisioning) | NO-OP (forwarded) | LOAD-BEARING (rattler companion) |
| `conda_forge_output_validation: true` | `False` | **all types** (mandatory org override) | NO-OP (re-stamped at feedstock creation) | **MANDATORY — never delete** |
| `github.branch_name` / `tooling_branch_name` | `main` | none type-specific | NO-OP (re-stamped) | REDUNDANT-DEFAULT (auto-managed) |
| `build_platform.<arch>` | native (`x: x`) | **compiled + cross-arch** only · no-op on noarch / native-x86 | NO-OP (matrix is repo-fixed; forwarded) | LOAD-BEARING (the cross-compile map) |
| `provider.<arch>: default` | x86 set; **other arches `None` (disabled)** | **compiled + cross-arch** (the *enable switch* for an otherwise-disabled arch; `osx_arm64` is default-on so needs only `build_platform`) · no-op on noarch | NO-OP (forwarded) | LOAD-BEARING |
| `test: native_and_emulated` | `None` | **compiled cross-arch w/ an emulated leg** (linux_aarch64/ppc64le QEMU tests) · **not** osx_arm64 (no x86→arm-mac emulator → tests skip regardless) · no-op on noarch | NO-OP (no emulated legs in PR) | LOAD-BEARING |
| `noarch_platforms` | `[linux_64]` | **noarch only**, and only with platform-conditional run-deps (G12 escape hatch) · meaningless on any compiled type; waste on plain pure-python | NO-OP (recipe still runs all 3 fixed jobs) | LOAD-BEARING (G12) |
| `os_version: {linux_64: alma9}` | none (`alma9` image) | **compiled-linux** needing glibc>2.17 · no-op on noarch | likely honored at build (auto-detected from `sysroot`; *unverified for the explicit key*) | LOAD-BEARING |
| `conda_build.error_overlinking: true` | `False` | **conda-build compiled** only · NO-OP on noarch · **NO-OP on rattler-build/v1** (verified: conda-smithy's `rattler_render` path doesn't thread the `conda_build:` block, and rattler-build reads overlinking from the recipe's `build.dynamic_linking` field — `pydantic-core` omits the key). On rattler-build, configure overlinking in `recipe.yaml`'s `build.dynamic_linking`, not here. | NO-OP | NO-OP on rattler-build; honored only on conda-build |
| `workflow_settings.store_build_artifacts` | `[]` | convenience (any type); **`win_64` must be ABSENT** for build-time-HTTPS recipes (Rust/Go-modules/npm/cgo — G18) | **NO-OP** (pipeline publishes `conda_pkgs_*` regardless) | convenience-only; win-absent is load-bearing |
| `bot.automerge: true` | `False` | POLICY — any type (CI-gated); risk scales with surface (compiled/cross/CUDA/multi-output > noarch:python) | INERT (no autotick on staged-recipes) | active POLICY |
| `bot.inspection: update-grayskull` | `hint` | **noarch:python** (grayskull's home) · ⚠ **maturin/compiled-python** can mangle hand-tuned host pins on bump → prefer `hint-all`/`update-source` · NO-OP/wrong for **non-python** (npm/Go/Rust-CLI/R → `disabled`/`hint-*`) | INERT | active (riskiest line; pairs badly with `automerge`) |
| `bot.check_solvable: true` | `True` | protective, any type | INERT | active but REDUNDANT-DEFAULT |
| `bot.run_deps_from_wheel: true` | `False` | **python-wheel w/ real `Requires-Dist`** (noarch:python, maturin) · NO-OP for non-python (no wheel) and ~no-op for dep-less extensions | INERT | active (wheel-only) |
| `bot.version_updates.exclude` | `[]` | any feedstock skipping bad upstream tags | INERT | active |
| `shellcheck.enabled: true` | `False` | **only recipes that ship a `build.sh`/`*.sh`** (compiled C/C++, **Go**, **R/CRAN**, Tauri/complex multi-output) · **pure NO-OP for every inline-`build.script` recipe** (noarch:python pip, maturin/PyO3, **modern Rust-CLI** + **modern npm ≥v8.11.0** — both inline) — *the single most cargo-culted key* | inert in PR (review-time lint needs a `*.sh`) | only does work if a `*.sh` exists |
| `idle_timeout_minutes` | `None` | **circleci/travis legs only** · NO-OP on azure/github_actions | NO-OP | NO-OP unless circle/travis |
| `azure.{free_disk_space,max_parallel,settings_*}` | varies | **large/compiled/GPU/multi-output** builds (disk, concurrency, swap) · no-op on small noarch · `azure.free_disk_space` is **deprecated → `workflow_settings.free_disk_space`** | NO-OP (repo-level pipelines) | LOAD-BEARING when resource-constrained |

### Cargo-cult boilerplate to DELETE (most-confident first)

1. **Everything except `conda_build_tool` in a staged-recipes per-recipe `conda-forge.yml`** that you don't specifically want **forwarded** to the feedstock — `bot.*`, `github.*`, `conda_forge_output_validation`, `store_build_artifacts`, `conda_install_tool`, `test`, `shellcheck`, `error_overlinking` are all inert in the PR. (Keep only forward-seeding keys you understand are dormant: `provider`/`build_platform`/`noarch_platforms`/`os_version`.)
2. **`shellcheck.enabled: true` on any inline-`build.script` recipe** — no `.sh` ⇒ pure no-op (maturin, noarch:python, modern Rust-CLI, modern npm ≥v8.11.0). It IS meaningful for **Go / compiled C/C++ / R/CRAN / Tauri** (they ship a `build.sh`).
3. **`conda_build.error_overlinking: true` on any noarch** (no binaries) **or any rattler-build/v1 recipe** (wrong config namespace — likely ignored).
4. **`noarch_platforms` on any compiled recipe** (it's not noarch) and on plain pure-python noarch with no platform branching (default `[linux_64]` is right).
5. **`provider`/`build_platform`/`test: native_and_emulated` on any noarch recipe** (one artifact; no cross-arch; no emulated legs).
6. **`bot.run_deps_from_wheel: true`** on non-python (no wheel); **`bot.inspection: update-grayskull`** on non-python (→ `disabled`/`hint-*`) and on maturin/compiled-python (→ `hint-all`/`update-source`, so grayskull can't auto-rewrite hand-tuned host pins — amplified by `automerge`).
7. **`github.branch_name`/`tooling_branch_name`** — redundant defaults (rerender re-stamps them; deleting is cosmetic churn — they earn nothing).

### Minimal-correct baselines by recipe type

- **Rust+PyO3 / maturin** — `pydantic-core-feedstock` is the canonical minimal file: only `bot.automerge`, `build_platform` (3 arches), `conda_build_tool: rattler-build`, `conda_forge_output_validation`, `conda_install_tool: pixi`, `github.*`, `test: native_and_emulated` — and **no** `provider`, `shellcheck`, `store_build_artifacts`, `error_overlinking`, or `bot.inspection/check_solvable/run_deps_from_wheel`. It still builds aarch64+ppc64le+osx_arm64 because it rides conda-forge-pinning's `arch_rebuild` migration; a recipe **not** in that migration (e.g. `lyric-py`) needs the explicit `provider: {linux_aarch64: default}` opt-in to enable the otherwise-disabled arch.
- **noarch:python** — `conda_build_tool: rattler-build` + `conda_install_tool: pixi` + `conda_forge_output_validation: true` + the canonical `bot` block; add `noarch_platforms` **only** with platform-conditional run-deps; no `build_platform`/`provider`/`test`/`error_overlinking`/`shellcheck`.
- **compiled C/C++ (single-arch)** — add `conda_build.error_overlinking: true` only on a **conda-build** (v0) feedstock; add `build_platform`+`provider` per arch when expanding; `os_version` only if glibc>2.17 is genuinely needed.

> **Verification flags (not bluffed):** (1) whether `error_overlinking` is honored under rattler-build — strong circumstantial evidence it is **not** (wrong namespace; pydantic-core omits it), but the rattler-build config-mapping code wasn't located. (2) Whether `os_version`/`channel_sources` in a *staged-recipes* per-recipe file are honored at build time — `build_all.py` ignores both, but `build_steps.sh`/docker-image selection wasn't traced; the skill treats `os_version: alma9` as a working staged-recipes opt-in, so it's likely read by the build path (not the matrix). (3) There is **no top-level `channels:` key** for adding *build* channels — extra build channels go in the recipe's `conda_build_config.yaml` `channel_sources`; `channels.targets`/`channel_priority` are real keys.

## Verifying changes

Local lint before you push:

```bash
pixi run -e conda-smithy lint recipes/<name>
```

`conda-smithy lint` reads `conda-forge.yml` and reports unrecognized keys
(typically a typo or a key renamed upstream). Address those before opening
the PR — they show up as PR-build failures otherwise.

## Source

- Schema + canonical docs: <https://conda-forge.org/docs/maintainer/conda_forge_yml/>
- conda-smithy validator: <https://github.com/conda-forge/conda-smithy/blob/main/conda_smithy/schema.py>
- Recent additions tracked in conda-forge news: <https://conda-forge.org/news/>
