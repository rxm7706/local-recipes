# recipe.yaml — Full Schema Reference (rattler-build / recipe-v1)

> **Auto-generated** by `.claude/skills/conda-forge-expert/scripts/gen_yml_reference.py`
> from the upstream JSON Schema. Do not edit by hand — re-run
> `pixi run -e local-recipes gen-yml-reference` after the upstream schema changes.
>
> **Schema source**: <https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json>
>
> **Curated companion** (opinionated subset + rationale + canonical shapes):
> [`recipe-yaml-reference.md`](recipe-yaml-reference.md)

## Intent

Recipe v1 spec. Consumed by `rattler-build` and the conda-forge v1 recipe pipeline.

## Top-level keys (0)

---

## Detail per top-level key

## Schema definitions / `$defs` (51)

Named definitions referenced by `$ref` from keys above.

### `About`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `description` | `string` \| `null` | `null` | Extended description of the package. |
| `documentation` | `string` \| `null` | `null` | Url that points to where the documentation is hosted. |
| `homepage` | `string` \| `null` | `null` | Url of the homepage of the package. |
| `license` | `string` \| `null` | `null` | An license in SPDX format. |
| `license_family` | `string` \| `null` | `null` | The license family (deprecated, but still used in some recipes). |
| `license_file` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Paths to the license files of this package. |
| `prelink_message` | `string` \| `null` | `null` | — |
| `repository` | `string` \| `null` | `null` | Url that points to where the source code is hosted e.g. (github.com) |
| `summary` | `string` \| `null` | `null` | A short description of the package. |

### `AttestationConfig`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `bundle_url` | `string` \| `null` | `null` | URL to download the attestation bundle from (e.g., .sigstore.json file). Auto-derived for PyPI sources if not specified. |
| `publishers` | array of `string` | `[]` | Publisher identities to verify (e.g., 'github:owner/repo'). All specified publishers must match. |

### `BaseGitSource`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | `integer` \| `null` | `null` | A value to use when shallow cloning the repository. |
| `expected_commit` | `string` \| `null` | `null` | An expected commit hash to verify after checkout. |
| `git` | `string` | — | The url that points to the git repository. |
| `lfs` | `boolean` | `false` | Should we LFS files be checked out as well |
| `patches` | `string` \| array of `string` \| `IfStatement_Annotated_str__StringConstraints__` | `[]` | A list of patches to apply after fetching the source |
| `submodules` | `boolean` \| `null` | `null` | Whether to recursively initialize and update submodules. |
| `target_directory` | `string` \| `null` | `null` | The location in the working directory to place the source |

### `Build`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `always_copy_files` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` \| array of `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` | `[]` | Do not soft- or hard-link these files but instead always copy them into the environment |
| `always_include_files` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | Files to be included even if they are present in the PREFIX before building. |
| `dynamic_linking` | `DynamicLinking` \| `null` | `null` | Configuration to post-process dynamically linked libraries and executables |
| `files` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` | `null` | Glob patterns to include or exclude files from the package. |
| `merge_build_and_host_envs` | `boolean` \| `string` \| `null` | `false` | Merge the build and host environments (used in many R packages on Windows) |
| `noarch` | enum: `"generic"`, `"python"` \| `null` | `null` | Can be either 'generic' or 'python'. A noarch 'python' package compiles .pyc files upon installation. |
| `number` | `integer` \| `string` \| `null` | `0` | Build number to version current build in addition to package version |
| `post_process` | `PostProcess` \| `IfStatement` \| array of `PostProcess` \| `IfStatement` | `[]` | Post-processing operations using regex replacements on files. |
| `prefix_detection` | `PrefixDetection` \| `null` | `null` | Options that influence how the prefix replacement is done. |
| `python` | `Python` \| `null` | `null` | Python specific build configuration |
| `script` | `string` \| `FileScript` \| `ContentScript` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | The script to execute to invoke the build. If the string is a single line and ends with `.sh` or `.bat`, then we interpret it as a file. |
| `skip` | `string` \| `boolean` \| array of `string` \| `boolean` \| `null` | `null` | List of conditions under which to skip the build of the package. If any of these condition returns true the build is skipped. |
| `string` | `string` \| `null` | `null` | The build string to identify build variant. This is usually omitted (can use `${{ hash }}`) variable here) |
| `variant` | `Variant` \| `null` | `null` | Options that influence how the different variants are computed. |

### `Cache`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `build` | `Build` \| `null` | `null` | Describes how the package should be build. |
| `requirements` | `Requirements` \| `null` | `null` | The dependencies needed at cache-build time. |
| `source` | `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement` \| array of `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement` \| `null` | `null` | The source items to be downloaded and used for the cache build and subsequent outputs. |

### `CacheInherit`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `from` | `string` | — | Name of the staging cache to inherit from. |
| `run_exports` | `boolean` | `true` | Whether to inherit run_exports from the staging cache. |

### `ComplexPackage`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `name` | `string` \| `null` | — | The recipe name, this is only used to identify the name of the recipe. |
| `version` | `string` \| `null` | `null` | The version of each output, this can be overwritten per output |

### `ComplexRecipe`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `about` | `About` \| `null` | `null` | A human readable description of the package information |
| `build` | `Build` \| `null` | `null` | Describes how the package should be build. |
| `cache` | `Cache` \| `null` | `null` | ⚠️ The cache build that can be used as a common build step for all output. |
| `context` | object \| `null` | `null` | Defines arbitrary key-value pairs for Jinja interpolation |
| `extra` | object \| `null` | `null` | An set of arbitrary values that are included in the package manifest |
| `outputs` | `Output` \| `StagingOutput` \| `IfStatement` \| array of `Output` \| `StagingOutput` \| `IfStatement` | — | A list of outputs that are generated for this recipe. |
| `recipe` | `ComplexPackage` \| `null` | `null` | The package version. |
| `schema_version` | `integer` | `1` | The version of the YAML schema for a recipe. If the version is omitted it is assumed to be 1. |
| `source` | `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement_Union_UrlSource__GitRev__GitTag__GitBranch__BaseGitSource__LocalSource__` \| array of `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement_Union_UrlSource__GitRev__GitTag__GitBranch__BaseGitSource__LocalSource__` \| `null` | `null` | The source items to be downloaded and used for the build. |
| `tests` | `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` \| `IfStatement` \| array of `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` \| `IfStatement` \| `null` | `null` | Top-level tests that are inherited by outputs |

### `ContentScript`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `content` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | — | A string or list of strings that is the scripts contents |
| `cwd` | `string` \| `null` | `null` | The working directory to use when executing the script. |
| `env` | mapping str → `string` | `{}` | the script environment. You can use Jinja to pass through environments variables with the `env` object (e.g. `${{ env.get("MYVAR") }}`) |
| `interpreter` | `string` \| `null` | `null` | The interpreter to use for the script. Defaults to `bash` on unix and `cmd.exe` on Windows. |
| `secrets` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | Secrets that are set as environment variables but never shown in the logs or the environment. |

### `DownstreamTestElement`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `downstream` | `string` | — | Install the package and use the output of this package to test if the tests in the downstream package still succeed. |

### `DynamicLinking`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `binary_relocation` | `boolean` \| `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` \| array of `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` | `true` | Whether to relocate binaries or not. If this is a list of paths then only the listed paths are relocated |
| `missing_dso_allowlist` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` \| array of `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` | `[]` | Allow linking against libraries that are not in the run requirements |
| `overdepending_behavior` | enum: `"ignore"`, `"error"` | `"error"` | What to do when detecting overdepending. Overdepending means that a requirement a run requirement is specified but none of the artifacts from the build link against any of the shared libraries of the requirement. |
| `overlinking_behavior` | enum: `"ignore"`, `"error"` | `"error"` | What to do when detecting overdepending. Overlinking occurs when an artifact links against a library that was not specified in the run requirements. |
| `rpath_allowlist` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` \| array of `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` | `[]` | Allow runpath/rpath to point to these locations outside of the environment |
| `rpaths` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `["lib/"]` | linux only, list of rpaths (was rpath) |

### `FileExistenceCheck`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `exists` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `[]` | Files or glob patterns that must exist anywhere inside the package. |
| `not_exists` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `[]` | Files or glob patterns that must NOT exist anywhere inside the package. |

### `FileScript`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `cwd` | `string` \| `null` | `null` | The working directory to use when executing the script. |
| `env` | mapping str → `string` | `{}` | the script environment. You can use Jinja to pass through environments variables with the `env` object (e.g. `${{ env.get("MYVAR") }}`) |
| `file` | `string` | — | The file to use as the script. Automatically adds the `bat` or `sh` to the filename on Windows or Unix respectively (if no file extension is given). |
| `interpreter` | `string` \| `null` | `null` | The interpreter to use for the script. Defaults to `bash` on unix and `cmd.exe` on Windows. |
| `secrets` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | Secrets that are set as environment variables but never shown in the logs or the environment. |

### `ForceFileType`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `binary` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` \| array of `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` | `[]` | force BINARY file type |
| `text` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` \| array of `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` | `[]` | force TEXT file type |

### `GitBranch`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `branch` | `string` | — | Branch to check out |
| `depth` | `integer` \| `null` | `null` | A value to use when shallow cloning the repository. |
| `expected_commit` | `string` \| `null` | `null` | An expected commit hash to verify after checkout. |
| `git` | `string` | — | The url that points to the git repository. |
| `lfs` | `boolean` | `false` | Should we LFS files be checked out as well |
| `patches` | `string` \| array of `string` \| `IfStatement_Annotated_str__StringConstraints__` | `[]` | A list of patches to apply after fetching the source |
| `submodules` | `boolean` \| `null` | `null` | Whether to recursively initialize and update submodules. |
| `target_directory` | `string` \| `null` | `null` | The location in the working directory to place the source |

### `GitRev`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | `integer` \| `null` | `null` | A value to use when shallow cloning the repository. |
| `expected_commit` | `string` \| `null` | `null` | An expected commit hash to verify after checkout. |
| `git` | `string` | — | The url that points to the git repository. |
| `lfs` | `boolean` | `false` | Should we LFS files be checked out as well |
| `patches` | `string` \| array of `string` \| `IfStatement_Annotated_str__StringConstraints__` | `[]` | A list of patches to apply after fetching the source |
| `rev` | `string` | — | Revision to checkout to (hash or ref) |
| `submodules` | `boolean` \| `null` | `null` | Whether to recursively initialize and update submodules. |
| `target_directory` | `string` \| `null` | `null` | The location in the working directory to place the source |

### `GitTag`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `depth` | `integer` \| `null` | `null` | A value to use when shallow cloning the repository. |
| `expected_commit` | `string` \| `null` | `null` | An expected commit hash to verify after checkout. |
| `git` | `string` | — | The url that points to the git repository. |
| `lfs` | `boolean` | `false` | Should we LFS files be checked out as well |
| `patches` | `string` \| array of `string` \| `IfStatement_Annotated_str__StringConstraints__` | `[]` | A list of patches to apply after fetching the source |
| `submodules` | `boolean` \| `null` | `null` | Whether to recursively initialize and update submodules. |
| `tag` | `string` | — | Tag to checkout |
| `target_directory` | `string` \| `null` | `null` | The location in the working directory to place the source |

### `GlobDict`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `exclude` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | Glob patterns to exclude |
| `include` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | Glob patterns to include |

### `IfStatement`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `else` | _(unspecified)_ \| array of _(unspecified)_ \| `null` | `null` | — |
| `if` | `string` | — | — |
| `then` | _(unspecified)_ \| array of _(unspecified)_ | — | — |

### `IfStatement_Annotated_str__StringConstraints__`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `else` | `string` \| array of `string` \| `null` | `null` | — |
| `if` | `string` | — | — |
| `then` | `string` \| array of `string` | — | — |

### `IfStatement_Union_ScriptTestElement__PythonTestElement__PerlTestElement__RTestElement__RubyTestElement__DownstreamTestElement__PackageContentTest__`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `else` | `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` \| array of `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` \| `null` | `null` | — |
| `if` | `string` | — | — |
| `then` | `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` \| array of `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` | — | — |

### `IfStatement_Union_UrlSource__GitRev__GitTag__GitBranch__BaseGitSource__LocalSource__`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `else` | `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| array of `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `null` | `null` | — |
| `if` | `string` | — | — |
| `then` | `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| array of `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` | — | — |

### `IgnoreRunExports`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `by_name` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | ignore run exports by name (e.g. `libgcc-ng`) |
| `from_package` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | ignore run exports that come from the specified packages |

### `LocalSource`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `file_name` | `string` \| `null` | `null` | A file name to rename the file to (does not apply to archives). |
| `filter` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` | `null` | Glob patterns to include or exclude files from the package. |
| `md5` | `string` \| `null` | `null` | The MD5 hash of the source archive |
| `patches` | `string` \| array of `string` \| `IfStatement_Annotated_str__StringConstraints__` | `[]` | A list of patches to apply after fetching the source |
| `path` | `string` | — | A path on the local machine that contains the source. |
| `sha256` | `string` \| `null` | `null` | The SHA256 hash of the source archive |
| `target_directory` | `string` \| `null` | `null` | The location in the working directory to place the source |
| `use_gitignore` | `boolean` | `true` | Whether or not to use the .gitignore file when copying the source. |

### `Output`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `about` | `About` \| `null` | `null` | A human readable description of the package information. The values here are merged with the top level `about` field. |
| `build` | `Build` \| `null` | `null` | Describes how the package should be build. |
| `inherit` | `string` \| `CacheInherit` \| `null` | `null` | Name of the staging cache to inherit from, or an object with `from` and `run_exports` options. |
| `package` | `ComplexPackage` \| `null` | `null` | The package name and version, this overwrites any top-level fields. |
| `requirements` | `Requirements` \| `null` | `null` | The package dependencies |
| `source` | `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement` \| array of `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement` \| `null` | `null` | The source items to be downloaded and used for the build. |
| `tests` | array of `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` \| `IfStatement_Union_ScriptTestElement__PythonTestElement__PerlTestElement__RTestElement__RubyTestElement__DownstreamTestElement__PackageContentTest__` \| array of `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` \| `IfStatement_Union_ScriptTestElement__PythonTestElement__PerlTestElement__RTestElement__RubyTestElement__DownstreamTestElement__PackageContentTest__` \| `null` | `null` | Tests to run after packaging |

### `PackageContentTest`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `package_contents` | `PackageContentTestInner` | — | Test if the package contains the specified files. |

### `PackageContentTestInner`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `bin` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `FileExistenceCheck` \| `null` | `[]` | Files that should be in the `bin/` folder of the package. This folder is found under `$PREFIX/bin` on Unix. On Windows this searches for files in `%PREFIX`, `%PREFIX%/bin`, `%PREFIX%/Scripts`, `%PREFIX%/Library/bin`, ... |
| `files` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `FileExistenceCheck` \| `null` | `null` | Files expectations for the whole package. Can be a list of files/globs or an object with exists/not_exists. |
| `include` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `FileExistenceCheck` \| `null` | `[]` | Files that should be in the `include/` folder of the package. This folder is found under `$PREFIX/include` on Unix and `$PREFIX/Library/include` on Windows. |
| `lib` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `[]` | Files that should be in the `lib/` folder of the package. This folder is found under `$PREFIX/lib` on Unix and %PREFIX%/Library/lib on Windows. |
| `site_packages` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `FileExistenceCheck` \| `null` | `[]` | Files that should be in the `site-packages/` folder of the package. This folder is found under `$PREFIX/lib/pythonX.Y/site-packages` on Unix and `$PREFIX/Lib/site-packages` on Windows. |
| `strict` | `boolean` | `false` | When true, the package must not contain any files other than those specified. |

### `PerlTestElement`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `perl` | `PerlTestElementInner` | — | Perl specific test configuration |

### `PerlTestElementInner`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `uses` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | — | A list of Perl modules to check after having installed the built package. |

### `PostProcess`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `files` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | — | Files to apply post-processing to |
| `regex` | `string` | — | Regular expression pattern to match |
| `replacement` | `string` | — | Replacement string |

### `PrefixDetection`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `force_file_type` | `ForceFileType` \| `null` | `null` | force the file type of the given files to be TEXT or BINARY |
| `ignore` | `boolean` \| `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `false` | Ignore all or specific files for prefix replacement |
| `ignore_binary_files` | `boolean` \| `string` | `false` | Whether to detect binary files with prefix or not |

### `Python`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `entry_points` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | — |
| `preserve_egg_dir` | `boolean` \| `string` | `false` | — |
| `site_packages_path` | `string` \| `null` | `null` | The path to the site-packages folder. This is advertised by Python to install noarch packages in the correct location. Only valid for a Python package. |
| `skip_pyc_compilation` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` \| array of `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `GlobDict` | `[]` | Skip compiling pyc for some files |
| `use_python_app_entrypoint` | `boolean` \| `string` | `false` | Specifies if python.app should be used as the entrypoint on macOS. (macOS only) |
| `version_independent` | `boolean` \| `string` | `false` | Whether the package is version independent or not. This is useful for 'abi3' packages that are OS specific, but not Python version specific. |

### `PythonTestElement`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `python` | `PythonTestElementInner` | — | Python specific test configuration |

### `PythonTestElementInner`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `imports` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `null` | A list of Python imports to check after having installed the built package. |
| `pip_check` | `boolean` | `true` | Whether or not to run `pip check` during the Python tests. |
| `python_version` | `string` \| array of `string` \| `null` | `null` | Python version(s) to test against. If not specified, the default python version is used. |

### `RTestElement`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `r` | `RTestElementInner` | — | R specific test configuration |

### `RTestElementInner`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `libraries` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | — | A list of R libraries to check after having installed the built package. |

### `Requirements`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `build` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Dependencies to install on the build platform architecture. Compilers, CMake, everything that needs to execute at build time. |
| `host` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Dependencies to install on the host platform architecture. All the packages that your build links against. |
| `ignore_run_exports` | `IgnoreRunExports` \| `null` | `null` | Ignore run-exports by name or from certain packages |
| `run` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Dependencies that should be installed alongside this package. Dependencies in the `host` section with `run_exports` are also automatically added here. |
| `run_constraints` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | constraints optional dependencies at runtime. |
| `run_exports` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `RunExports` | `null` | The run exports of this package |

### `RubyTestElement`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `ruby` | `RubyTestElementInner` | — | Ruby specific test configuration |

### `RubyTestElementInner`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `requires` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | — | A list of Ruby modules to check after having installed the built package. |

### `RunExports`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `noarch` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Noarch run exports are the only ones looked at when building noarch packages |
| `strong` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Strong run exports apply from the build and host env to the run env |
| `strong_constraints` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Strong run constraints add run_constraints from the build and host env |
| `weak` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Weak run exports apply from the host env to the run env |
| `weak_constraints` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Weak run constraints add run_constraints from the host env |

### `ScriptTestElement`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `files` | `TestElementFiles` \| `null` | `null` | Additional files to include for the test. |
| `requirements` | `TestElementRequires` \| `null` | `null` | Additional dependencies to install before running the test. |
| `script` | `string` \| `FileScript` \| `ContentScript` \| `IfStatement` \| array of `string` \| `IfStatement` | `null` | A script to run to perform the test. |

### `SimplePackage`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `name` | `string` | — | The package name |
| `version` | `string` | — | The package version |

### `SimpleRecipe`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `about` | `About` \| `null` | `null` | A human readable description of the package information |
| `build` | `Build` \| `null` | `null` | Describes how the package should be build. |
| `context` | object \| `null` | `null` | Defines arbitrary key-value pairs for Jinja interpolation |
| `extra` | object \| `null` | `null` | An set of arbitrary values that are included in the package manifest |
| `package` | `SimplePackage` | — | The package name and version. |
| `requirements` | `Requirements` \| `null` | `null` | The package dependencies |
| `schema_version` | `integer` | `1` | The version of the YAML schema for a recipe. If the version is omitted it is assumed to be 1. |
| `source` | `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement_Union_UrlSource__GitRev__GitTag__GitBranch__BaseGitSource__LocalSource__` \| array of `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement_Union_UrlSource__GitRev__GitTag__GitBranch__BaseGitSource__LocalSource__` \| `null` | `null` | The source items to be downloaded and used for the build. |
| `tests` | `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` \| `IfStatement` \| array of `ScriptTestElement` \| `PythonTestElement` \| `PerlTestElement` \| `RTestElement` \| `RubyTestElement` \| `DownstreamTestElement` \| `PackageContentTest` \| `IfStatement` \| `null` | `null` | Tests to run after packaging |

### `StagingBuild`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `script` | `string` \| `FileScript` \| `ContentScript` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | The script to execute to invoke the staging build. |

### `StagingMeta`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `name` | `string` | — | Unique name for this staging cache. |

### `StagingOutput`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `build` | `StagingBuild` \| `null` | `null` | Build configuration for the staging output. |
| `requirements` | `StagingRequirements` \| `null` | `null` | The dependencies needed for the staging build. |
| `source` | `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement` \| array of `UrlSource` \| `GitRev` \| `GitTag` \| `GitBranch` \| `BaseGitSource` \| `LocalSource` \| `IfStatement` \| `null` | `null` | The source items to be downloaded and used for the staging build. |
| `staging` | `StagingMeta` | — | Marks this output as a staging output with the given name. |

### `StagingRequirements`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `build` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Dependencies to install on the build platform architecture for the staging build. |
| `host` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | Dependencies to install on the host platform architecture for the staging build. |
| `ignore_run_exports` | `IgnoreRunExports` \| `null` | `null` | Ignore run-exports by name or from certain packages |

### `TestElementFiles`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `recipe` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | extra files from $RECIPE_DIR |
| `source` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | extra files from $SRC_DIR |

### `TestElementRequires`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `build` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | extra requirements with build_platform architecture (emulators, ...) |
| `run` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` \| `null` | `null` | extra run dependencies |

### `UrlSource`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `attestation` | `AttestationConfig` \| `null` | `null` | Optional attestation verification configuration. |
| `file_name` | `string` \| `null` | `null` | A file name to rename the downloaded file to (does not apply to archives). |
| `md5` | `string` \| `null` | `null` | The MD5 hash of the source archive |
| `patches` | `string` \| array of `string` \| `IfStatement_Annotated_str__StringConstraints__` | `[]` | A list of patches to apply after fetching the source |
| `sha256` | `string` \| `null` | `null` | The SHA256 hash of the source archive |
| `target_directory` | `string` \| `null` | `null` | The location in the working directory to place the source |
| `url` | `string` \| array of `string` | — | Url pointing to the source tar.gz\|zip\|tar.bz2\|... (this can be a list of mirrors that point to the same file) |

### `Variant`

- **Type**: object (see nested keys)

**Nested keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `down_prioritize_variant` | `integer` \| `string` | `0` | used to prefer this variant less over other variants |
| `ignore_keys` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | Keys to forcibly ignore for the variant computation (even if they are in the dependencies) |
| `use_keys` | `string` \| `IfStatement` \| array of `string` \| `IfStatement` | `[]` | Keys to forcibly use for the variant computation (even if they are not in the dependencies) |

