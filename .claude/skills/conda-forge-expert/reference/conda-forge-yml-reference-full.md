# conda-forge.yml — Full Schema Reference

> **Auto-generated** by `.claude/skills/conda-forge-expert/scripts/gen_yml_reference.py`
> from the upstream JSON Schema. Do not edit by hand — re-run
> `pixi run -e local-recipes gen-yml-reference` after the upstream schema changes.
>
> **Schema source**: <https://raw.githubusercontent.com/conda-forge/conda-smithy/main/conda_smithy/data/conda-forge.json>
>
> **Curated companion** (opinionated subset + rationale + canonical shapes):
> [`conda-forge-yml-reference.md`](conda-forge-yml-reference.md)

## Intent

Per-feedstock + per-recipe smithy config. Consumed by `conda smithy rerender` and `conda-smithy lint`.

## Top-level keys (45)

| Key | Type | Default |
|---|---|---|
| [`appveyor`](#appveyor) | object \| `null` | — |
| [`azure`](#azure) | `AzureConfig` \| `null` | — |
| [`bot`](#bot) | `cf_tick_schema.json` | — |
| [`build_platform`](#build-platform) | `build_platform` \| `null` | — |
| [`build_with_mambabuild`](#build-with-mambabuild) | `boolean` \| `null` | `true` |
| [`channel_priority`](#channel-priority) | `ChannelPriorityConfig` \| `null` | `"strict"` |
| [`choco`](#choco) | array of `string` \| `null` | — |
| [`circle`](#circle) | object \| `null` | — |
| [`clone_depth`](#clone-depth) | `integer` \| `Nullable` \| `null` | `null` |
| [`compiler_stack`](#compiler-stack) | `string` \| `null` | `"comp7"` |
| [`conda_build`](#conda-build) | `CondaBuildConfig` \| `null` | — |
| [`conda_build_tool`](#conda-build-tool) | enum: `"conda-build"`, `"conda-build+classic"`, `"conda-build+conda-libmamba-solver"`, `"mambabuild"`, `"rattler-build"` \| `null` | `"conda-build"` |
| [`conda_forge_output_validation`](#conda-forge-output-validation) | `boolean` \| `null` | `false` |
| [`conda_install_tool`](#conda-install-tool) | enum: `"conda"`, `"mamba"`, `"micromamba"`, `"pixi"` \| `null` | `"micromamba"` |
| [`conda_solver`](#conda-solver) | enum: `"libmamba"`, `"classic"` \| `Nullable` \| `null` | `"libmamba"` |
| [`config_version`](#config-version) | `string` \| `null` | `"2"` |
| [`docker`](#docker) | `CondaForgeDocker` \| `null` | — |
| [`drone`](#drone) | mapping str → `string` \| `null` | — |
| [`exclusive_config_file`](#exclusive-config-file) | `string` \| `Nullable` \| `null` | `null` |
| [`github`](#github) | `GithubConfig` \| `null` | — |
| [`github_actions`](#github-actions) | `GithubActionsConfig` \| `null` | — |
| [`idle_timeout_minutes`](#idle-timeout-minutes) | `integer` \| `Nullable` \| `null` | `null` |
| [`linter`](#linter) | `LinterConfig` \| `null` | — |
| [`matrix`](#matrix) | object \| `null` | — |
| [`max_py_ver`](#max-py-ver) | `string` \| `null` | `"37"` |
| [`max_r_ver`](#max-r-ver) | `string` \| `null` | `"34"` |
| [`min_py_ver`](#min-py-ver) | `string` \| `null` | `"27"` |
| [`min_r_ver`](#min-r-ver) | `string` \| `null` | `"34"` |
| [`noarch_platforms`](#noarch-platforms) | `Platforms` \| array of `Platforms` \| `null` | — |
| [`os_version`](#os-version) | `os_version` \| `null` | — |
| [`package`](#package) | `string` \| `Nullable` \| `null` | `null` |
| [`private_upload`](#private-upload) | `boolean` \| `null` | `false` |
| [`provider`](#provider) | `provider` \| `null` | — |
| [`recipe_dir`](#recipe-dir) | `string` \| `null` | `"recipe"` |
| [`remote_ci_setup`](#remote-ci-setup) | `string` \| array of `string` \| `null` | — |
| [`secrets`](#secrets) | array of `string` \| `null` | — |
| [`shellcheck`](#shellcheck) | `ShellCheck` \| `Nullable` \| `null` | — |
| [`skip_render`](#skip-render) | array of `string` \| `null` | — |
| [`templates`](#templates) | mapping str → `string` \| `null` | — |
| [`test`](#test) | `DefaultTestPlatforms` \| `Nullable` \| `null` | `null` |
| [`test_on_native_only`](#test-on-native-only) | `boolean` \| `null` | `false` |
| [`travis`](#travis) | object \| `null` | — |
| [`upload_on_branch`](#upload-on-branch) | `string` \| `Nullable` \| `null` | `null` |
| [`woodpecker`](#woodpecker) | mapping str → `string` \| `null` | — |
| [`workflow_settings`](#workflow-settings) | `WorkflowSettings` \| `null` | — |

---

## Detail per top-level key

### `appveyor`

- **Type**: object \| `null`
- **Description**: AppVeyor CI settings. This is usually read-only and should not normally be manually modified. Tools like conda-smithy may modify this, as needed.

---

### `azure`

- **Type**: `AzureConfig` \| `null`
- **Description**: Azure Pipelines CI settings. This is usually read-only and should not normally be manually modified. Tools like conda-smithy may modify this, as needed. For example: ```yaml azure: # flag for forcing the building all supported providers force: False # toggle for storing the conda build_artifacts directory (including the # built packages) as an Azure pipeline artifact that can be downloaded store_build_artifacts: False # toggle for freeing up some extra space on the default Azure Pipelines # linux image before running the Docker container for building free_disk_space: False # limit the amount of CI jobs running concurrently at a given time # each OS will get its proportional share of the configured value max_parallel: 25 ``` Below is an example configuration for setting up a self-hosted Azure agent for Linux: ```yaml azure: settings_linux: pool: name: your_local_pool_name demands: - some_key -equals some_value workspace: clean: all strategy: maxParallel: 1 ``` Below is an example configuration for adding a swapfile on an Azure agent for Linux and Windows: ```yaml azure: settings_linux: swapfile_size: 10GiB settings_win: variables: SET_PAGEFILE: 'True' ``` If you need more space on Windows, you can use `C:` at the cost of IO performance: ```yaml azure: settings_win: variables: CONDA_BLD_PATH: "C:\bld" MINIFORGE_HOME: "C:\Miniforge" ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `build_id` | `integer` \| `null` | `null` | The build ID for the specific feedstock used for rendering the badges in the README file generated. When the value is None, conda-smithy will compute the build ID by calling the Azure API which requires a token for pr... |
| `force` | `boolean` \| `null` | `false` | Force building all supported providers |
| `free_disk_space` | `boolean` \| `Nullable` \| array of enum: `"apt"`, `"cache"`, `"docker"` \| `null` | `false` | ⚠️ Deprecated. Use `workflow_settings.free_disk_space` instead. Free up disk space before build. The following components can be cleaned up: `apt`, `cache`, `docker`. When set to `true`, only `apt` and `cache` are cleane... |
| `max_parallel` | `integer` \| `null` | `50` | Limit the amount of CI jobs running concurrently at a given time |
| `project_id` | `string` \| `null` | `"84710dde-1620-425b-80d0-4cf5baca359d"` | The ID of the Azure Pipelines project |
| `project_name` | `string` \| `null` | `"feedstock-builds"` | The name of the Azure Pipelines project |
| `settings_linux` | `AzureRunnerSettings` | — | This is the settings for runners. |
| `settings_osx` | `AzureRunnerSettings` | — | This is the settings for runners. |
| `settings_win` | `AzureRunnerSettings` | — | This is the settings for runners. |
| `store_build_artifacts` | `boolean` \| `null` | `false` | ⚠️ Deprecated. Store the conda build_artifacts directory as an Azure pipeline artifact. Use `workflow_settings.store_build_artifacts` instead. |
| `timeout_minutes` | `integer` \| `Nullable` \| `null` | `null` | The maximum amount of time (in minutes) that a job can run before it is automatically canceled |
| `upload_packages` | `boolean` \| `null` | `true` | Whether to upload the packages to Anaconda.org. Useful for testing. |
| `user_or_org` | `string` \| `Nullable` \| `null` | `null` | The name of the Azure user or organization. Defaults to the value of github: user_or_org. |

---

### `bot`

- **Type**: `cf_tick_schema.json`

---

### `build_platform`

- **Type**: `build_platform` \| `null`
- **Description**: This is a mapping from the target platform to the build platform for the package to be built. For example, the following builds a `osx-64` package on the `linux-64` build platform using cross-compiling. ```yaml build_platform: osx_64: linux_64 ``` Leaving this field empty implicitly requests to build a package natively. i.e. ```yaml build_platform: linux_64: linux_64 linux_ppc64le: linux_ppc64le linux_aarch64: linux_aarch64 osx_64: osx_64 osx_arm64: osx_arm64 win_64: win_64 ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `emscripten_wasm32` | `Platforms` \| `null` | `"emscripten_wasm32"` | — |
| `freebsd_64` | `Platforms` \| `null` | `"freebsd_64"` | — |
| `linux_32` | `Platforms` \| `null` | `"linux_32"` | — |
| `linux_64` | `Platforms` \| `null` | `"linux_64"` | — |
| `linux_aarch64` | `Platforms` \| `null` | `"linux_aarch64"` | — |
| `linux_armv6l` | `Platforms` \| `null` | `"linux_armv6l"` | — |
| `linux_armv7l` | `Platforms` \| `null` | `"linux_armv7l"` | — |
| `linux_ppc64` | `Platforms` \| `null` | `"linux_ppc64"` | — |
| `linux_ppc64le` | `Platforms` \| `null` | `"linux_ppc64le"` | — |
| `linux_riscv64` | `Platforms` \| `null` | `"linux_riscv64"` | — |
| `linux_s390x` | `Platforms` \| `null` | `"linux_s390x"` | — |
| `osx_64` | `Platforms` \| `null` | `"osx_64"` | — |
| `osx_arm64` | `Platforms` \| `null` | `"osx_arm64"` | — |
| `wasi_wasm32` | `Platforms` \| `null` | `"wasi_wasm32"` | — |
| `win_32` | `Platforms` \| `null` | `"win_32"` | — |
| `win_64` | `Platforms` \| `null` | `"win_64"` | — |
| `win_arm64` | `Platforms` \| `null` | `"win_arm64"` | — |
| `zos_z` | `Platforms` \| `null` | `"zos_z"` | — |

---

### `build_with_mambabuild`

> **⚠️ Deprecated.**

- **Type**: `boolean` \| `null`
- **Default**: `true`
- **Description**: build_with_mambabuild is deprecated, use `conda_build_tool` instead.

---

### `channel_priority`

- **Type**: `ChannelPriorityConfig` \| `null`
- **Default**: `"strict"`
- **Description**: The channel priority level for the conda solver during feedstock builds. For extra information, see the [Strict channel priority](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-channels.html#strict-channel-priority) section on conda documentation.

---

### `choco`

- **Type**: array of `string` \| `null`
- **Description**: This parameter allows for conda-smithy to run chocoloatey installs on Windows when additional system packages are needed. This is a list of strings that represent package names and any additional parameters. For example, ```yaml choco: # install a package - nvidia-display-driver # install a package with a specific version - cuda --version=11.0.3 ``` This is currently only implemented for Azure Pipelines. The command that is run is `choco install {entry} -fdv -y --debug`. That is, `choco install` is executed with a standard set of additional flags that are useful on CI.

---

### `circle`

- **Type**: object \| `null`
- **Description**: Circle CI settings. This is usually read-only and should not normally be manually modified. Tools like conda-smithy may modify this, as needed.

---

### `clone_depth`

- **Type**: `integer` \| `Nullable` \| `null`
- **Default**: `null`
- **Description**: The depth of the git clone.

---

### `compiler_stack`

> **⚠️ Deprecated.**

- **Type**: `string` \| `null`
- **Default**: `"comp7"`
- **Description**: Compiler stack environment variable. This is used to specify the compiler stack to use for builds. Deprecated. ```yaml compiler_stack: comp7 ```

---

### `conda_build`

- **Type**: `CondaBuildConfig` \| `null`
- **Description**: Settings in this block are used to control how `conda build` runs and produces artifacts. An example of the such configuration is: ```yaml conda_build: pkg_format: 2 zstd_compression_level: 16 error_overlinking: False ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `error_overlinking` | `boolean` \| `null` | `false` | Enable error when shared libraries from transitive dependencies are directly linked to any executables or shared libraries in built packages. For more details, see the [conda build documentation](https://docs.conda.io... |
| `pkg_format` | enum: `"tar"`, `1`, `2`, `"1"`, `"2"` \| `null` | `2` | The package version format for conda build. |
| `zstd_compression_level` | `integer` \| `null` | `16` | The compression level for the zstd compression algorithm for .conda artifacts. conda-forge uses a default value of 16 for a good compromise of performance and compression. |

---

### `conda_build_tool`

- **Type**: enum: `"conda-build"`, `"conda-build+classic"`, `"conda-build+conda-libmamba-solver"`, `"mambabuild"`, `"rattler-build"` \| `null`
- **Default**: `"conda-build"`
- **Description**: Use this option to choose which tool is used to build your recipe.

---

### `conda_forge_output_validation`

- **Type**: `boolean` \| `null`
- **Default**: `false`
- **Description**: This field must be set to `True` for feedstocks in the `conda-forge` GitHub organization. It enables the required feedstock artifact validation as described in [Output Validation and Feedstock Tokens](/docs/maintainer/infrastructure#output-validation).

---

### `conda_install_tool`

- **Type**: enum: `"conda"`, `"mamba"`, `"micromamba"`, `"pixi"` \| `null`
- **Default**: `"micromamba"`
- **Description**: Use this option to choose which tool is used to provision the tooling in your feedstock. Defaults to micromamba. If conda or mamba are chosen, the latest Miniforge will be used to provision the base environment. If micromamba or pixi are chosen, Miniforge is not involved; the environment is created directly by micromamba or pixi.

---

### `conda_solver`

- **Type**: enum: `"libmamba"`, `"classic"` \| `Nullable` \| `null`
- **Default**: `"libmamba"`
- **Description**: Choose which `conda` solver plugin to use for feedstock builds.

---

### `config_version`

- **Type**: `string` \| `null`
- **Default**: `"2"`
- **Description**: The conda-smithy config version to be used for conda_build_config.yaml files in recipe and conda-forge-pinning. This should not be manually modified.

---

### `docker`

- **Type**: `CondaForgeDocker` \| `null`
- **Description**: This is a mapping for Docker-specific configuration options. Some options are ```yaml docker: executable: docker command: "bash" ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `command` | `string` \| `null` | `"bash"` | The command to run in Docker |
| `executable` | `string` \| `null` | `"docker"` | The executable for Docker |
| `fallback_image` | `string` \| `null` | `"quay.io/condaforge/linux-anvil-comp7"` | The fallback image for Docker |
| `interactive` | `boolean` \| `Nullable` \| `null` | `null` | ⚠️ Whether to run Docker in interactive mode |
| `run_args` | `string` \| `null` | `""` | Additional arguments to pass to `docker run`. |

---

### `drone`

- **Type**: mapping str → `string` \| `null`
- **Description**: Drone CI settings. This is usually read-only and should not normally be manually modified. Tools like conda-smithy may modify this, as needed.

---

### `exclusive_config_file`

- **Type**: `string` \| `Nullable` \| `null`
- **Default**: `null`
- **Description**: Exclusive conda-build config file to replace `conda-forge-pinning`. For advanced usage only.

---

### `github`

- **Type**: `GithubConfig` \| `null`
- **Description**: Mapping for GitHub-specific configuration options. The defaults are as follows: ```yaml github: user_or_org: conda-forge repo_name: "my_repo" branch_name: main tooling_branch_name: main ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `branch_name` | `string` \| `null` | `"main"` | The name of the branch to execute on |
| `repo_name` | `string` \| `null` | `""` | The name of the repository |
| `tooling_branch_name` | `string` \| `null` | `"main"` | The name of the branch to use for rerender+webservices github actions and conda-forge-ci-setup-feedstock references |
| `user_or_org` | `string` \| `null` | `"conda-forge"` | The name of the GitHub user or organization |

---

### `github_actions`

- **Type**: `GithubActionsConfig` \| `null`
- **Description**: GitHub Actions CI settings. This is usually read-only and should not normally be manually modified. Tools like conda-smithy may modify this, as needed.

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `artifact_retention_days` | `integer` \| `null` | `14` | The number of days to retain artifacts |
| `cancel_in_progress` | `boolean` \| `null` | `true` | Whether to cancel jobs in the same build if one fails. |
| `free_disk_space` | `boolean` \| `Nullable` \| array of enum: `"apt"`, `"cache"`, `"docker"` \| `null` | `false` | ⚠️ Deprecated. Use `workflow_settings.free_disk_space` instead. Free up disk space building. The following components can be cleaned up: `apt`, `cache`, `docker`. When set to `true`, only `apt` and `cache` are cleaned up... |
| `max_parallel` | `integer` \| `Nullable` \| `null` | `50` | The maximum number of jobs to run in parallel |
| `resize_win_partitions` | `boolean` \| `null` | `false` | ⚠️ Deprecated. Use `workflow_settings.resize_partitions` instead. Whether to resize partitions to use all space on Windows |
| `self_hosted` | `boolean` \| `null` | `false` | ⚠️ Deprecated. Whether to use self-hosted runners. Use `github_actions_labels` in `conda_build_config.yaml` instead. |
| `store_build_artifacts` | `boolean` \| `null` | `false` | ⚠️ Deprecated. Whether to store build artifacts. Use `workflow_settings.store_build_artifacts` instead. |
| `timeout_minutes` | `integer` \| `null` | `360` | The maximum amount of time (in minutes) that a job can run before it is automatically canceled |
| `triggers` | array of _(unspecified)_ \| `null` | `[]` | Triggers for Github Actions. Defaults to push, pull_request, when not self-hosted and push when self-hosted |
| `upload_packages` | `boolean` \| `null` | `true` | Whether to upload the packages to Anaconda.org. Useful for testing. |

---

### `idle_timeout_minutes`

- **Type**: `integer` \| `Nullable` \| `null`
- **Default**: `null`
- **Description**: Configurable idle timeout. Used for packages that don't have chatty enough builds. Applicable only to circleci and travis. ```yaml idle_timeout_minutes: 60 ```

---

### `linter`

- **Type**: `LinterConfig` \| `null`
- **Description**: Settings in this block are used to control how `conda smithy` lints. An example of the such configuration is: ```yaml linter: skip: - lint_noarch_selectors ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `skip` | array of `Lints` \| `null` | — | List of lints to skip |

---

### `matrix`

> **⚠️ Deprecated.**

- **Type**: object \| `null`
- **Description**: Build matrices were used to specify a set of build configurations to run for each package pinned dependency. This has been deprecated in favor of the `provider` field. More information can be found in the [Build Matrices](/docs/maintainer/knowledge_base/#build-matrices) section of the conda-forge docs.

---

### `max_py_ver`

> **⚠️ Deprecated.**

- **Type**: `string` \| `null`
- **Default**: `"37"`
- **Description**: Maximum Python version. This is used to specify the maximum Python version to use for builds. Deprecated. ```yaml max_py_ver: 37 ```

---

### `max_r_ver`

> **⚠️ Deprecated.**

- **Type**: `string` \| `null`
- **Default**: `"34"`
- **Description**: Maximum R version. This is used to specify the maximum R version to use for builds. Deprecated. ```yaml max_r_ver: 34 ```

---

### `min_py_ver`

> **⚠️ Deprecated.**

- **Type**: `string` \| `null`
- **Default**: `"27"`
- **Description**: Minimum Python version. This is used to specify the minimum Python version to use for builds. Deprecated. ```yaml min_py_ver: 27 ```

---

### `min_r_ver`

> **⚠️ Deprecated.**

- **Type**: `string` \| `null`
- **Default**: `"34"`
- **Description**: Minimum R version. This is used to specify the minimum R version to use for builds. Deprecated. ```yaml min_r_ver: 34 ```

---

### `noarch_platforms`

- **Type**: `Platforms` \| array of `Platforms` \| `null`
- **Description**: Platforms on which to build noarch packages. The preferred default is a single build on `linux_64`. ```yaml noarch_platforms: linux_64 ``` To build on multiple platforms, e.g. for simple packages with platform-specific dependencies, provide a list. ```yaml noarch_platforms: - linux_64 - win_64 ```

---

### `os_version`

- **Type**: `os_version` \| `null`
- **Description**: This key is used to set the OS versions for `linux_*` platforms. Valid entries map a linux platform and arch to either `alma9`, `alma8` or `cos7`. For CUDA 11.8 images, a choice equivalent to `alma8` is `ubi8`. Currently `alma9` is the default, though `alma10` is available for opt-in where necessary. `rocky10` may be added in the future. Note that the image version does not imply a matching `glibc` requirement (which can be set using `c_stdlib_version` in `recipe/conda_build_config.yaml`). If you need to opt into older images, here's an example how to do it: ```yaml os_version: linux_64: cos7 linux_aarch64: cos7 linux_ppc64le: cos7 ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `linux_32` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_64` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_aarch64` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_armv6l` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_armv7l` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_ppc64` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_ppc64le` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_riscv64` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_s390x` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |

---

### `package`

- **Type**: `string` \| `Nullable` \| `null`
- **Default**: `null`
- **Description**: Default location for a package feedstock directory basename.

---

### `private_upload`

- **Type**: `boolean` \| `null`
- **Default**: `false`
- **Description**: Whether to upload to a private channel. ```yaml private_upload: False ```

---

### `provider`

- **Type**: `provider` \| `null`
- **Description**: The `provider` field is a mapping from build platform (not target platform) to CI service. It determines which service handles each build platform. If a desired build platform is not available with a selected provider (either natively or with emulation), the build will be disabled. Use the `build_platform` field to manually specify cross-compilation when no providers offer a desired build platform. The following are available as supported build platforms: * `linux_64` * `osx_64` * `win_64` * `linux_aarch64` * `linux_ppc64le` * `linux_s390x` * `linux_armv7l` The following CI services are available: * `azure` * `circle` * `travis` * `appveyor` * `None` or `False` to disable a build platform. * `default` to choose an appropriate CI (only if available) * `native` to choose an appropriate CI for native compiling (only if available) * `emulated` to choose an appropriate CI for compiling inside an emulation of the target platform (only if available) For example, making explicit that linux_64 & osx_64 build on azure (by default), and switching win_64 to Appveyor: ```yaml provider: linux_64: azure osx_64: azure win_64: appveyor ``` Currently, x86_64 platforms are enabled, but other build platforms are disabled by default. i.e. an empty provider entry is equivalent to the following: ```yaml provider: linux_64: azure osx_64: azure win_64: azure linux_ppc64le: None linux_aarch64: None ``` To enable `linux_ppc64le` and `linux_aarch64` add the following: ```yaml provider: linux_ppc64le: default linux_aarch64: default ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `emscripten_wasm32` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `freebsd_64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_32` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `"github_actions"` | — |
| `linux_aarch64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_armv6l` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_armv7l` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_ppc64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_ppc64le` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_riscv64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_s390x` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `osx` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `osx_64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `"azure"` | — |
| `osx_arm64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `wasi_wasm32` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `win` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `win_32` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `win_64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `"azure"` | — |
| `win_arm64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `zos_z` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |

---

### `recipe_dir`

- **Type**: `string` \| `null`
- **Default**: `"recipe"`
- **Description**: The relative path to the recipe directory. The default is: ```yaml recipe_dir: recipe ```

---

### `remote_ci_setup`

- **Type**: `string` \| array of `string` \| `null`
- **Description**: This option can be used to override the default `conda-forge-ci-setup` package. Can be given with `${url or channel_alias}::package_name`, defaults to conda-forge channel_alias if no prefix is given. ```yaml remote_ci_setup: ["conda-forge-ci-setup=4", "conda-build>=26.3"] ```

---

### `secrets`

- **Type**: array of `string` \| `null`
- **Description**: List of secrets to be used in GitHub Actions. The default is an empty list and will not be used.

---

### `shellcheck`

- **Type**: `ShellCheck` \| `Nullable` \| `null`
- **Description**: Shell scripts used for builds or activation scripts can be linted with shellcheck. This option can be used to enable shellcheck and configure its behavior. This is not enabled by default, but can be enabled like so: ```yaml shellcheck: enabled: True ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | `boolean` | `false` | Whether to use shellcheck to lint shell scripts |

---

### `skip_render`

- **Type**: array of `string` \| `null`
- **Description**: This option specifies a list of files which `conda smithy` will skip rendering. This is useful for files that are not templates, but are still in the recipe directory. The default value is an empty list `[]`, which will consider that all files can be rendered. For example, if you want to skip rendering the `.gitignore` and `LICENSE.txt` files, you can add the following: ```yaml skip_render: - .gitignore - LICENSE.txt ```

---

### `templates`

- **Type**: mapping str → `string` \| `null`
- **Description**: This is mostly an internal field for specifying where template files reside. You shouldn't need to modify it.

---

### `test`

- **Type**: `DefaultTestPlatforms` \| `Nullable` \| `null`
- **Default**: `null`
- **Description**: This is used to configure on which platforms a recipe is tested. ```yaml test: native_and_emulated ``` Will do testing only if the platform is native or if there is an emulator. ```yaml test: native ``` Will do testing only if the platform is native.

---

### `test_on_native_only`

> **⚠️ Deprecated.**

- **Type**: `boolean` \| `null`
- **Default**: `false`
- **Description**: This was used for disabling testing for cross-compiling. ```warning This has been deprecated in favor of the top-level `test` field. It is now mapped to `test: native_and_emulated`. ```

---

### `travis`

- **Type**: object \| `null`
- **Description**: Travis CI settings. This is usually read-only and should not normally be manually modified. Tools like conda-smithy may modify this, as needed.

---

### `upload_on_branch`

- **Type**: `string` \| `Nullable` \| `null`
- **Default**: `null`
- **Description**: This parameter restricts uploading access on work from certain branches of the same repo. Only the branch listed in `upload_on_branch` will trigger uploading of packages to the target channel. The default is to skip this check if the key `upload_on_branch` is not in `conda-forge.yml`. To restrict uploads to the main branch: ```yaml upload_on_branch: main ```

---

### `woodpecker`

- **Type**: mapping str → `string` \| `null`
- **Description**: Woodpecker CI settings. This is usually read-only and should not normally be manually modified. Tools like conda-smithy may modify this, as needed.

---

### `workflow_settings`

- **Type**: `WorkflowSettings` \| `null`
- **Description**: Per-workflow settings. ```yaml workflow_settings: store_build_artifacts: # there can be at most one value for each workflow - provider: github_actions platform: linux_aarch64 value: true - platform: [linux_64, win_64] # OR value: true ```

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `build_workspace_dir` | `string` \| array of `ConditionalValue__class__str__` \| `Nullable` \| `null` | `[]` | Directory to build in. |
| `free_disk_space` | enum: `"skip"`, `"quick"`, `"max"` \| array of `Literal__skip____quick____max__` \| `Nullable` \| `null` | `[]` | Free up disk space before building. Takes one of the following values: - `skip`: does not do anything (the default) - `quick`: cleans a subset of components that balances space gained against the time necessary to do ... |
| `pagefile_size` | `integer` \| array of `ConditionalValue__class__int__` \| `Nullable` \| `null` | `[]` | Override the default paging (swap) file size, in GiB. For example, 8 means 8 GiB. |
| `resize_partitions` | `boolean` \| array of `ConditionalValue__class__bool__` \| `Nullable` \| `null` | `[]` | Whether to resize partitions to use all available space. Currently only supported for certain providers on GitHub Actions for Windows. |
| `store_build_artifacts` | `boolean` \| array of `ConditionalValue__class__bool__` \| `Nullable` \| `null` | `[]` | Store the outputs of the build process as uploaded CI artifacts. |
| `tools_install_dir` | `string` \| array of `ConditionalValue__class__str__` \| `Nullable` \| `null` | `[]` | Directory to install build-time tools in. |

---

## Schema definitions / `$defs` (23)

Named definitions referenced by `$ref` from keys above.

### `AzureConfig`

- **Type**: object (see nested keys)
- **Description**: This dictates the behavior of the Azure Pipelines CI service. It is a sub-mapping for Azure-specific configuration options. For more information and some variables specifications, see the [Azure Pipelines schema reference documentation]( https://learn.microsoft.com/en-us/azure/devops/pipelines/yaml-schema/?view=azure-pipelines).

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `build_id` | `integer` \| `null` | `null` | The build ID for the specific feedstock used for rendering the badges in the README file generated. When the value is None, conda-smithy will compute the build ID by calling the Azure API which requires a token for pr... |
| `force` | `boolean` \| `null` | `false` | Force building all supported providers |
| `free_disk_space` | `boolean` \| `Nullable` \| array of enum: `"apt"`, `"cache"`, `"docker"` \| `null` | `false` | ⚠️ Deprecated. Use `workflow_settings.free_disk_space` instead. Free up disk space before build. The following components can be cleaned up: `apt`, `cache`, `docker`. When set to `true`, only `apt` and `cache` are cleane... |
| `max_parallel` | `integer` \| `null` | `50` | Limit the amount of CI jobs running concurrently at a given time |
| `project_id` | `string` \| `null` | `"84710dde-1620-425b-80d0-4cf5baca359d"` | The ID of the Azure Pipelines project |
| `project_name` | `string` \| `null` | `"feedstock-builds"` | The name of the Azure Pipelines project |
| `settings_linux` | `AzureRunnerSettings` | — | This is the settings for runners. |
| `settings_osx` | `AzureRunnerSettings` | — | This is the settings for runners. |
| `settings_win` | `AzureRunnerSettings` | — | This is the settings for runners. |
| `store_build_artifacts` | `boolean` \| `null` | `false` | ⚠️ Deprecated. Store the conda build_artifacts directory as an Azure pipeline artifact. Use `workflow_settings.store_build_artifacts` instead. |
| `timeout_minutes` | `integer` \| `Nullable` \| `null` | `null` | The maximum amount of time (in minutes) that a job can run before it is automatically canceled |
| `upload_packages` | `boolean` \| `null` | `true` | Whether to upload the packages to Anaconda.org. Useful for testing. |
| `user_or_org` | `string` \| `Nullable` \| `null` | `null` | The name of the Azure user or organization. Defaults to the value of github: user_or_org. |

### `AzureRunnerSettings`

- **Type**: object (see nested keys)
- **Description**: This is the settings for runners.

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `install_atl` | `boolean` \| `null` | `false` | Whether to install ATL components for MSVC |
| `pool` | mapping str → `string` \| `null` | — | The pool of self-hosted runners, e.g. 'vmImage': 'ubuntu-latest' |
| `swapfile_size` | `string` \| `Nullable` \| `null` | `null` | Deprecated. Swapfile size in GiB. Use `workflow_settings.pagefile_size` instead. |
| `timeoutInMinutes` | `integer` \| `null` | `360` | Timeout in minutes for the job |
| `variables` | mapping str → `string` \| `null` | — | Variables |

### `CIservices`

- **Type**: enum: `"azure"`, `"circle"`, `"travis"`, `"appveyor"`, `"github_actions"`, `"drone"`, …
- **Allowed values**: `"azure"`, `"circle"`, `"travis"`, `"appveyor"`, `"github_actions"`, `"drone"`, `"woodpecker"`, `"default"`, `"emulated"`, `"native"`, `"None"`

### `ChannelPriorityConfig`

- **Type**: enum: `"strict"`, `"flexible"`, `"disabled"`
- **Allowed values**: `"strict"`, `"flexible"`, `"disabled"`

### `CondaBuildConfig`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `error_overlinking` | `boolean` \| `null` | `false` | Enable error when shared libraries from transitive dependencies are directly linked to any executables or shared libraries in built packages. For more details, see the [conda build documentation](https://docs.conda.io... |
| `pkg_format` | enum: `"tar"`, `1`, `2`, `"1"`, `"2"` \| `null` | `2` | The package version format for conda build. |
| `zstd_compression_level` | `integer` \| `null` | `16` | The compression level for the zstd compression algorithm for .conda artifacts. conda-forge uses a default value of 16 for a good compromise of performance and compression. |

### `CondaForgeDocker`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `command` | `string` \| `null` | `"bash"` | The command to run in Docker |
| `executable` | `string` \| `null` | `"docker"` | The executable for Docker |
| `fallback_image` | `string` \| `null` | `"quay.io/condaforge/linux-anvil-comp7"` | The fallback image for Docker |
| `interactive` | `boolean` \| `Nullable` \| `null` | `null` | ⚠️ Whether to run Docker in interactive mode |
| `run_args` | `string` \| `null` | `""` | Additional arguments to pass to `docker run`. |

### `ConditionalValue__class__bool__`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `os` | array of `PlatformsAliases` \| `PlatformsAliases` \| `Nullable` \| `null` | `null` | Operating systems to set environment variable on (default: all) |
| `platform` | array of `Platforms` \| `Platforms` \| `Nullable` \| `null` | `null` | Platforms to set environment variable on (default: all) |
| `provider` | array of `CIservices` \| `CIservices` \| `Nullable` \| `null` | `null` | CI providers to set environment variable on (default: all) |
| `value` | `boolean` | `false` | Option value |

### `ConditionalValue__class__int__`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `os` | array of `PlatformsAliases` \| `PlatformsAliases` \| `Nullable` \| `null` | `null` | Operating systems to set environment variable on (default: all) |
| `platform` | array of `Platforms` \| `Platforms` \| `Nullable` \| `null` | `null` | Platforms to set environment variable on (default: all) |
| `provider` | array of `CIservices` \| `CIservices` \| `Nullable` \| `null` | `null` | CI providers to set environment variable on (default: all) |
| `value` | `integer` | `null` | Option value |

### `ConditionalValue__class__str__`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `os` | array of `PlatformsAliases` \| `PlatformsAliases` \| `Nullable` \| `null` | `null` | Operating systems to set environment variable on (default: all) |
| `platform` | array of `Platforms` \| `Platforms` \| `Nullable` \| `null` | `null` | Platforms to set environment variable on (default: all) |
| `provider` | array of `CIservices` \| `CIservices` \| `Nullable` \| `null` | `null` | CI providers to set environment variable on (default: all) |
| `value` | `string` | `null` | Option value |

### `DefaultTestPlatforms`

- **Type**: enum: `"all"`, `"native"`, `"native_and_emulated"`
- **Allowed values**: `"all"`, `"native"`, `"native_and_emulated"`

### `GithubActionsConfig`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `artifact_retention_days` | `integer` \| `null` | `14` | The number of days to retain artifacts |
| `cancel_in_progress` | `boolean` \| `null` | `true` | Whether to cancel jobs in the same build if one fails. |
| `free_disk_space` | `boolean` \| `Nullable` \| array of enum: `"apt"`, `"cache"`, `"docker"` \| `null` | `false` | ⚠️ Deprecated. Use `workflow_settings.free_disk_space` instead. Free up disk space building. The following components can be cleaned up: `apt`, `cache`, `docker`. When set to `true`, only `apt` and `cache` are cleaned up... |
| `max_parallel` | `integer` \| `Nullable` \| `null` | `50` | The maximum number of jobs to run in parallel |
| `resize_win_partitions` | `boolean` \| `null` | `false` | ⚠️ Deprecated. Use `workflow_settings.resize_partitions` instead. Whether to resize partitions to use all space on Windows |
| `self_hosted` | `boolean` \| `null` | `false` | ⚠️ Deprecated. Whether to use self-hosted runners. Use `github_actions_labels` in `conda_build_config.yaml` instead. |
| `store_build_artifacts` | `boolean` \| `null` | `false` | ⚠️ Deprecated. Whether to store build artifacts. Use `workflow_settings.store_build_artifacts` instead. |
| `timeout_minutes` | `integer` \| `null` | `360` | The maximum amount of time (in minutes) that a job can run before it is automatically canceled |
| `triggers` | array of _(unspecified)_ \| `null` | `[]` | Triggers for Github Actions. Defaults to push, pull_request, when not self-hosted and push when self-hosted |
| `upload_packages` | `boolean` \| `null` | `true` | Whether to upload the packages to Anaconda.org. Useful for testing. |

### `GithubConfig`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `branch_name` | `string` \| `null` | `"main"` | The name of the branch to execute on |
| `repo_name` | `string` \| `null` | `""` | The name of the repository |
| `tooling_branch_name` | `string` \| `null` | `"main"` | The name of the branch to use for rerender+webservices github actions and conda-forge-ci-setup-feedstock references |
| `user_or_org` | `string` \| `null` | `"conda-forge"` | The name of the GitHub user or organization |

### `LinterConfig`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `skip` | array of `Lints` \| `null` | — | List of lints to skip |

### `Lints`

- **Type**: enum: `"lint_noarch_selectors"`, `"lint_stdlib"`, `"hint_os_version"`, `"hint_pip_no_build_backend"`, `"hint_python_min"`
- **Allowed values**: `"lint_noarch_selectors"`, `"lint_stdlib"`, `"hint_os_version"`, `"hint_pip_no_build_backend"`, `"hint_python_min"`

### `Literal__skip____quick____max__`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `os` | array of `PlatformsAliases` \| `PlatformsAliases` \| `Nullable` \| `null` | `null` | Operating systems to set environment variable on (default: all) |
| `platform` | array of `Platforms` \| `Platforms` \| `Nullable` \| `null` | `null` | Platforms to set environment variable on (default: all) |
| `provider` | array of `CIservices` \| `CIservices` \| `Nullable` \| `null` | `null` | CI providers to set environment variable on (default: all) |
| `value` | enum: `"skip"`, `"quick"`, `"max"` | `"skip"` | Option value |

### `Nullable`

- **Type**: enum: `null`
- **Description**: Created to avoid issue with schema validation of null values in lists or dicts.
- **Allowed values**: `null`

### `Platforms`

- **Type**: enum: `"emscripten_wasm32"`, `"wasi_wasm32"`, `"freebsd_64"`, `"linux_32"`, `"linux_64"`, `"linux_aarch64"`, …
- **Allowed values**: `"emscripten_wasm32"`, `"wasi_wasm32"`, `"freebsd_64"`, `"linux_32"`, `"linux_64"`, `"linux_aarch64"`, `"linux_armv6l"`, `"linux_armv7l"`, `"linux_ppc64"`, `"linux_ppc64le"`, `"linux_riscv64"`, `"linux_s390x"`, `"osx_64"`, `"osx_arm64"`, `"win_32"`, `"win_64"`, `"win_arm64"`, `"zos_z"`

### `PlatformsAliases`

- **Type**: enum: `"linux"`, `"win"`, `"osx"`
- **Allowed values**: `"linux"`, `"win"`, `"osx"`

### `ShellCheck`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `enabled` | `boolean` | `false` | Whether to use shellcheck to lint shell scripts |

### `WorkflowSettings`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `build_workspace_dir` | `string` \| array of `ConditionalValue__class__str__` \| `Nullable` \| `null` | `[]` | Directory to build in. |
| `free_disk_space` | enum: `"skip"`, `"quick"`, `"max"` \| array of `Literal__skip____quick____max__` \| `Nullable` \| `null` | `[]` | Free up disk space before building. Takes one of the following values: - `skip`: does not do anything (the default) - `quick`: cleans a subset of components that balances space gained against the time necessary to do ... |
| `pagefile_size` | `integer` \| array of `ConditionalValue__class__int__` \| `Nullable` \| `null` | `[]` | Override the default paging (swap) file size, in GiB. For example, 8 means 8 GiB. |
| `resize_partitions` | `boolean` \| array of `ConditionalValue__class__bool__` \| `Nullable` \| `null` | `[]` | Whether to resize partitions to use all available space. Currently only supported for certain providers on GitHub Actions for Windows. |
| `store_build_artifacts` | `boolean` \| array of `ConditionalValue__class__bool__` \| `Nullable` \| `null` | `[]` | Store the outputs of the build process as uploaded CI artifacts. |
| `tools_install_dir` | `string` \| array of `ConditionalValue__class__str__` \| `Nullable` \| `null` | `[]` | Directory to install build-time tools in. |

### `build_platform`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `emscripten_wasm32` | `Platforms` \| `null` | `"emscripten_wasm32"` | — |
| `freebsd_64` | `Platforms` \| `null` | `"freebsd_64"` | — |
| `linux_32` | `Platforms` \| `null` | `"linux_32"` | — |
| `linux_64` | `Platforms` \| `null` | `"linux_64"` | — |
| `linux_aarch64` | `Platforms` \| `null` | `"linux_aarch64"` | — |
| `linux_armv6l` | `Platforms` \| `null` | `"linux_armv6l"` | — |
| `linux_armv7l` | `Platforms` \| `null` | `"linux_armv7l"` | — |
| `linux_ppc64` | `Platforms` \| `null` | `"linux_ppc64"` | — |
| `linux_ppc64le` | `Platforms` \| `null` | `"linux_ppc64le"` | — |
| `linux_riscv64` | `Platforms` \| `null` | `"linux_riscv64"` | — |
| `linux_s390x` | `Platforms` \| `null` | `"linux_s390x"` | — |
| `osx_64` | `Platforms` \| `null` | `"osx_64"` | — |
| `osx_arm64` | `Platforms` \| `null` | `"osx_arm64"` | — |
| `wasi_wasm32` | `Platforms` \| `null` | `"wasi_wasm32"` | — |
| `win_32` | `Platforms` \| `null` | `"win_32"` | — |
| `win_64` | `Platforms` \| `null` | `"win_64"` | — |
| `win_arm64` | `Platforms` \| `null` | `"win_arm64"` | — |
| `zos_z` | `Platforms` \| `null` | `"zos_z"` | — |

### `os_version`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `linux_32` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_64` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_aarch64` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_armv6l` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_armv7l` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_ppc64` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_ppc64le` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_riscv64` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |
| `linux_s390x` | enum: `"alma10"`, `"rocky10"`, `"alma9"`, `"alma8"`, `"ubi8"`, `"cos7"` \| `null` | `null` | — |

### `provider`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `emscripten_wasm32` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `freebsd_64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_32` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `"github_actions"` | — |
| `linux_aarch64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_armv6l` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_armv7l` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_ppc64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_ppc64le` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_riscv64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `linux_s390x` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `osx` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `osx_64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `"azure"` | — |
| `osx_arm64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `wasi_wasm32` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `win` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `win_32` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `win_64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `"azure"` | — |
| `win_arm64` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |
| `zos_z` | array of `CIservices` \| `CIservices` \| `boolean` \| `Nullable` \| `null` | `null` | — |

