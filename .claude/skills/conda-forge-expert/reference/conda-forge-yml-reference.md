# conda-forge.yml Reference

A practical reference for the keys that come up most often when shipping a
recipe through `conda-forge/staged-recipes` or maintaining a feedstock.
Not exhaustive — see <https://conda-forge.org/docs/maintainer/conda_forge_yml/>
for the full schema (kept in sync with `conda-smithy`'s validator). What's
here is the high-signal subset: the keys you actually edit, what they do,
when to use them, and what to leave alone. Concrete YAML lives in the
templates: [`templates/conda-forge-yml/staged-recipes/conda-forge.yml`](../templates/conda-forge-yml/staged-recipes/conda-forge.yml)
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

### `azure.store_build_artifacts: true`

Default Azure runs discard `build_artifacts/` after the build/test step.
Setting this flag publishes the entire tree (including the built `.conda`)
as a downloadable pipeline artifact.

- Reviewers can grab the package and test it in a real env before approving.
- You can do the same: drop the `.conda` into `mamba create -n test --use-local <name>`
  and smoke-test imports / CLI / entry points against a clean env.
- Especially useful for recipes that ship MCP servers, entry points, or
  other surfaces where "CI was green" is a weaker signal than a hands-on test.

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

Default is `[linux_64]` for noarch packages. Adding more platforms costs
CI minutes — only enable when the package has platform-conditional runtime
behavior (file paths, subprocess invocations) where a Linux test isn't
conclusive.

### Per-job `timeout_minutes`

Default ~360 (6 hours) on both Azure and GitHub Actions. Raise only with
a real reason — long builds usually have a fixable underlying issue. Ask
in the conda-forge Zulip channel before doubling timeouts.

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
| `azure.free_disk_space` | Cleanup steps before the build (e.g. `[true]`). | When the host runs out of disk during build. |
| `idle_timeout_minutes` | Cancel CI if no log output for N minutes. | Raise from default if you have legitimate quiet phases. |

## Don't bother with these (deprecated or harmful)

| Key | Why to skip |
|---|---|
| `compiler_stack` | Removed; the `compiler()` macro resolves global pins. Delete from any existing `conda-forge.yml`. |
| `build_with_mambabuild` | Boa / mamba-build deprecated; rattler-build is the path forward. |
| `clone_depth` | Almost never the right knob; conda-forge handles checkout depth automatically. |
| `pinning` | Don't override conda-forge-pinning; rerendering will overwrite. |
| `provider.linux_aarch64: default` (Travis) | Travis is gone; use Cirun or Azure (emulated). |

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
