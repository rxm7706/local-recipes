# python-magic on Windows (Win64) — Conda-Forge Enablement Project Plan

> **Status (2026-05-06):** Recipes authored locally. `python-magic` (noarch) builds and tests clean on linux-64. `file` recipe renders clean for both linux-64 and win-64 but the **win-64 binary build has not been executed** — that requires either a Windows host with MSVC or a conda-forge CI run. Submission to upstream feedstocks is **not** done.
>
> **Owner:** TBD. Hand this document to whoever takes the win-64 build effort.
>
> **Local artifacts:**
> - `recipes/python-magic/recipe.yaml` (v1, noarch)
> - `recipes/python-magic/0001-load-magic-file.patch`
> - `recipes/file/recipe.yaml` (v1, multi-output, multi-platform)
> - `recipes/file/build.sh`, `recipes/file/build.bat`
> - `output/noarch/python-magic-0.4.27-pyh59285b8_0.conda` (locally built)

---

## 1. Goal

Enable `conda install -c conda-forge python-magic` to work on `win-64`. Today, `conda-forge/python-magic-feedstock` ships the package only on `linux-*` and `osx-*` and refuses Windows installs via a `__unix` virtual-package constraint.

**Acceptance criteria for "done":**
- `libmagic` exists on `conda-forge` for `win-64`.
- `python-magic` on `conda-forge` no longer carries `__unix`; its run dependency `libmagic` resolves on all three platforms.
- A user can run, on a fresh Windows machine after `conda install python-magic`:
  ```python
  import magic
  m = magic.Magic()             # loads libmagic.dll
  print(m.from_file("README.md"))  # prints something like "ASCII text"
  ```

## 2. Why this has been blocked for 6+ years

The blocker chain — verified during this investigation:

1. **`conda-forge/python-magic-feedstock` issue #9** (open since Oct 2019) — "Windows Build for python-magic." Holds up downstream packages including CKAN and diffoscope.
2. **`conda-forge/file-feedstock` issue #3** (open since 2020) — "Please provide Windows build." This is the *actual* blocker: there is no `libmagic` build for `win-64` on conda-forge.
3. **Upstream `file/file`** has no native Windows build system (autotools-only).
4. **Three resolution attempts have stalled:**
   - **`m2-file` (msys2 channel)** — rejected: conda-forge policy forbids mixing MinGW and MSVC packages.
   - **`nscaife/file-windows`** — rejected: requires cross-compilation from Linux, which conda-forge does not support.
   - **`julian-r/file-windows`** (CMake/MSVC port) — accepted in principle in 2020; *no taker* until now.

The most recent activity is `h-vetinari`'s 2025-01 comment on file-feedstock#3 linking `ahupp/python-magic#293`, which catalogues the long Windows pain history.

## 3. Investigation findings

### 3.1 Solution shape

We adopt **`julian-r/file-windows`** as the source of truth for `libmagic` on Windows because:

- It is the only MSVC-compatible port still maintained (last commit 2023-03-16; *not* archived).
- It produces `libmagic.dll` (the file name `python-magic`'s ctypes loader looks for first; vcpkg's `magic-1.dll` does not match without a rename).
- It uses CMake — fits cleanly into a conda-forge `recipe.yaml` v1 with `cmake` + `ninja`.
- Last release `v5.44` (Mar 2023) tracks upstream `file 5.44`. We pin everything to 5.44.

### 3.2 `python-magic` Windows side: no patch needed

`python-magic 0.4.27`'s `magic/loader.py` already has Windows-aware DLL discovery:

```python
elif sys.platform in ('win32', 'cygwin'):
    prefixes = ['libmagic', 'magic1', 'cygmagic-1', 'libmagic-1', 'msys-magic-1']
    for i in prefixes:
        yield './%s.dll' % (i,)
        yield find_library(i)
```

When a conda env is active on Windows, `%CONDA_PREFIX%\Library\bin` is on `PATH`, and `ctypes.util.find_library('libmagic')` finds `libmagic.dll` there. No patch to `python-magic` is required for DLL discovery — provided the DLL is named `libmagic.dll` (which is what `julian-r/file-windows` produces and what we copy in `build.bat`).

The pre-existing `0001-load-magic-file.patch` from the upstream feedstock is preserved verbatim. Inspection confirms the patch is effectively a no-op (the `os.path.join(...)` call's result is unassigned), but conda-forge has been shipping it for years and the surgical-changes principle says don't drift.

### 3.3 `file` Windows side: build constraints

| Concern | Reality |
|---|---|
| Compiler | MSVC required; `julian-r` repo tested on VS 2015–2022. No mingw/MSVC mixing per conda-forge policy. |
| Cross-compile from Linux | Not supported by conda-forge. Cannot build win-64 from this Linux host. |
| Build tool | CMake 3.7+, Ninja (or NMake — recipe uses Ninja). |
| Submodules | **Required.** `julian-r/file-windows` uses git submodules: `file/`, `dirent/`, `getopt/`. GitHub's tarball download does NOT include submodules — must use `source.git` with `rev:` to pin a commit. PCRE2 is vendored (committed in-repo). |
| Build outputs | `libmagic.dll`, `libmagic.lib` (import lib), `file.exe`, `magic.mgc` (compiled magic database). No `install()` targets in CMakeLists — recipe must copy artifacts manually. |
| Static dependencies | PCRE2 is statically linked (`-DPCRE2_STATIC`); `shlwapi` is a Windows system DLL. **No additional runtime conda dependencies on Windows.** |
| Test suite | `ctest` runs an upstream test corpus; `julian-r` already disables a few tests for known CRLF/timezone drift. Recipe runs ctest as best-effort, not gating. |

### 3.4 Version policy

Linux/macOS upstream `file` is at 5.47 (2024-12). `julian-r/file-windows` tracks 5.44 (2023-03). To keep the same code on every platform we **downgrade unix to 5.44**. This is a regression of ~2 minor versions for unix users *of this local recipe*; the upstream conda-forge feedstock would need to handle that policy choice separately (e.g., as a coordinated bump synchronised to whenever julian-r tags 5.47). See §7 "Open questions" item 1.

### 3.5 Licensing

The Windows package bundles four licensed sources:
- `file/COPYING` — `BSD-2-Clause-Darwin` (the file source itself)
- `LICENSE` — `MIT` (julian-r's CMake wrapper, dirent and getopt headers)
- `pcre2/LICENCE` — `BSD-3-Clause` (vendored PCRE2)

The recipe declares `license: BSD-2-Clause-Darwin` (the primary identifier, matching the existing feedstock) and ships all three license files via a conditional `license_file:` list. This matches conda-forge convention for bundled libraries — `license_file:` is the authoritative list of what's distributed, while `license:` names the dominant license.

> Note: the local `license-checker.py` flags `BSD-2-Clause-Darwin` as "not a standard SPDX identifier." This is a false positive — the identifier was added in SPDX List 3.20 (Mar 2023) and is what the existing `conda-forge/file-feedstock` uses. The authoritative `conda-smithy lint` accepts it.

## 4. Architecture of the new recipes

### 4.1 `recipes/file/recipe.yaml`

Multi-output, multi-platform v1 recipe using the modern **`staging` output** pattern (replacement for the deprecated top-level `cache:` key).

```
recipe: file-split @ 5.44
├── source
│   ├── unix → astron.com/pub/file/file-5.44.tar.gz (sha256 verified)
│   └── win  → git: julian-r/file-windows @ rev cddf42c5fa…  (submodules)
├── outputs
│   ├── staging: file-split-build      ← shared build env (compiler, stdlib, make/cmake)
│   ├── package: libmagic              ← inherits staging; carves library files
│   │   ├── files: include/, lib/libmagic.*, share/misc/magic.mgc   (unix)
│   │   │          Library/bin/libmagic.dll, Library/lib/libmagic.lib, etc.  (win)
│   │   └── run_exports: pin_subpackage('libmagic', upper_bound='x')
│   └── package: file                  ← inherits staging; carves CLI + man pages
│       └── run: pin_subpackage('libmagic', exact=true)
└── about
    ├── license: BSD-2-Clause-Darwin
    └── license_file: COPYING (unix)  |  file/COPYING + LICENSE + pcre2/LICENCE (win)
```

Key v1 details a developer should know before editing:

- **Multi-output recipes use `recipe:` at the top, not `package:`.** `package:` is per-output.
- **Top-level `requirements:` is not valid** in multi-output v1. Use a `staging` output that other outputs `inherit:` from. (The `cache:` key is deprecated; `rattler-build migrate-recipe` will rewrite it for you.)
- **`run_exports` belongs under `requirements:`,** not under `build:`.
- `${{ pin_subpackage(name, upper_bound='x') }}` is the v1 spelling of v0's `max_pin='x'`.

### 4.2 `recipes/file/build.sh` (Linux/macOS)

Standard autotools build, copied verbatim from the existing `file-feedstock/recipe/build.sh`. Handles `CONDA_BUILD_CROSS_COMPILATION=1` for aarch64-on-x86 cross-builds (it bootstraps a host-native `file` first to compile the magic database).

### 4.3 `recipes/file/build.bat` (Windows)

```bat
mkdir build && cd build
cmake -G Ninja -DCMAKE_BUILD_TYPE=Release "%SRC_DIR%"
cmake --build . --config Release
ctest --output-on-failure -C Release || echo "non-fatal"
:: Manual install — julian-r CMakeLists has no install() targets:
copy /Y libmagic.dll "%LIBRARY_BIN%\libmagic.dll"
copy /Y libmagic.lib "%LIBRARY_LIB%\libmagic.lib"
copy /Y file.exe "%LIBRARY_BIN%\file.exe"
copy /Y magic.mgc "%LIBRARY_PREFIX%\share\misc\magic.mgc"
copy /Y "%SRC_DIR%\file\src\magic.h" "%LIBRARY_INC%\magic.h"
```

Note: every `cmake`/`copy` is plain `.exe` so no `call` shim concerns. (See `feedback_call_cmd_shims_in_bat.md` in auto-memory if you ever add a `.cmd` invocation here — bare `.cmd` calls in `.bat` silently terminate the script.)

### 4.4 `recipes/python-magic/recipe.yaml`

Unchanged across platforms except for the run-deps block:

```yaml
run:
  - libmagic            # now resolves on linux/osx/win
  - python >=${{ python_min }}
  # __unix dropped — see python-magic-Win64.md (this folder)
```

The patch `0001-load-magic-file.patch` is unchanged (no-op but preserved for parity).

## 5. What's done locally

| Check | Result |
|---|---|
| `pixi run validate recipes/python-magic` | ✅ pass |
| `pixi run validate recipes/file` | ✅ pass (1 warning re: top-level `tests:` — false positive; tests are per-output) |
| `pixi run lint-optimize recipes/python-magic` | ✅ 0 issues |
| `pixi run lint-optimize recipes/file` | ✅ 0 issues |
| `pixi run scan-vulnerabilities` (both) | ✅ clean |
| `pixi run license-check recipes/python-magic` | ✅ MIT |
| `pixi run license-check recipes/file` | ⚠️ false positive on `BSD-2-Clause-Darwin` (see §3.5) |
| `rattler-build --render-only --target-platform linux-64` (both) | ✅ |
| `rattler-build --render-only --target-platform win-64` (both) | ✅ |
| **Actual build of `python-magic` for noarch on linux-64 host** | ✅ artifact in `output/noarch/` |
| **Actual build of `file` for win-64** | ❌ **NOT POSSIBLE on Linux host** — needs Windows + MSVC |
| **PR to `conda-forge/file-feedstock`** | ❌ not started |
| **PR to `conda-forge/python-magic-feedstock`** | ❌ not started |
| **End-to-end Windows install + import test** | ❌ not done |

## 6. Required next steps

These are sequenced. Do not skip ahead.

### Step 1 — Validate the Windows build of `file` on a real Windows host

**Why it's first:** every downstream step assumes `libmagic.dll` actually compiles, links, and the magic.mgc database loads correctly under MSVC. AppVeyor green for `julian-r/file-windows v5.44` from 2023 is suggestive but not definitive that it builds inside a *conda-build* environment with the conda-forge MSVC toolchain.

**Acceptance:**
- `pixi run -e local-recipes rattler-build build --recipe recipes/file/recipe.yaml --target-platform win-64 -m .ci_support/win64.yaml` produces:
  - `output/win-64/libmagic-5.44-*_0.conda`
  - `output/win-64/file-5.44-*_0.conda`
- Smoke test the produced packages: `conda install ./libmagic-*.conda ./file-*.conda` in a fresh win-64 env, then `file --version` returns `5.44`.

**How:** spin up a Windows VM (Hyper-V/Parallels/EC2 `t3.medium` Windows 2022) with VS Build Tools 2022 + CMake + Pixi, clone this repo, run the command above. **Estimated time:** 1–3 hours assuming no surprises.

**Likely issues to watch for:**
- `ctest` failures — already non-fatal in `build.bat`; re-confirm.
- Submodule fetch: rattler-build's `source.git` should pull submodules; if not, the `file/` directory will be empty and CMake will fail at `add_library(libmagic SHARED file/src/...)`. If this happens, check `rattler-build` git source options or use a pre-archived submodule snapshot.
- `magic.mgc` compilation: the CMakeLists builds `file.exe` first, then runs `file -C -m magic` to compile the database. PATH must include the build dir at that point so `libmagic.dll` is loadable.
- License file paths: on win, `pcre2/LICENCE` (British spelling) — verify it's still at that path in the v5.44 tag.

### Step 2 — Submit the `file-feedstock` PR

Once Step 1 produces working binaries:

1. Fork `conda-forge/file-feedstock`.
2. Replace `recipe/meta.yaml` with our `recipe.yaml` + `build.sh` + `build.bat` (note: feedstock format is meta.yaml-by-default; you'll either ship v1 alongside or migrate the feedstock — coordinate with maintainers `blmaier`, `chrisburr`, `mariusvniekerk`, `mrakitin`).
3. The version downgrade (5.47 → 5.44) is a policy decision the maintainers must accept. Pre-PR discussion on `file-feedstock#3` is mandatory — link this document. Alternatives if they reject the downgrade:
   - Keep unix at 5.47 with platform-conditional `version:` (uglier but doable in v1).
   - Volunteer to upstream julian-r's port to file 5.47 yourself, then bump.
4. Rerender with `conda-smithy` after merge so the Windows CI pipeline activates.

**Acceptance:** conda-forge CI green for `win-64` `file` and `libmagic`; packages publish to the `conda-forge` channel.

### Step 3 — Submit the `python-magic-feedstock` PR

Once Step 2's packages are published:

1. Drop the `__unix` constraint and remove the `# [unix]` selector from the run-deps.
2. Bump build number from current 5 to 6.
3. (Optional) Migrate the existing meta.yaml to recipe.yaml v1 — `migrate_to_v1` tool. Coordinate with maintainer `mariusvniekerk`.
4. Rerender to activate Windows CI.
5. Close `conda-forge/python-magic-feedstock#9` referencing the PR.

**Acceptance:** Windows CI green; package publishes; `mamba search python-magic` shows a `win-64` build.

### Step 4 — End-to-end smoke test

On a fresh Windows machine:
```cmd
mamba create -n test -c conda-forge python=3.12 python-magic
mamba activate test
python -c "import magic; print(magic.Magic().from_file(r'C:\Windows\System32\notepad.exe'))"
```
Expected: a `PE32+ executable …` line. If you get `failed to find libmagic` it means `libmagic.dll` is not on `%PATH%` — likely the `Library\bin` activation didn't run, which is a different (env-activation) bug.

### Step 5 — Close out follow-ups

- `conda-forge/file-feedstock#3` — close as "fixed in PR #N".
- `conda-forge/python-magic-feedstock#9` — close as "fixed in PR #M".
- Notify downstream-blocked feedstocks: `diffoscope` (h-vetinari), `ckan`, anyone else who pinged `python-magic-feedstock#9`.
- Comment on `ahupp/python-magic#293` with the conda-forge resolution; users who don't use conda still need a separate fix.

## 7. Open questions / risks

1. **Version downgrade policy.** Will conda-forge accept downgrading unix from `file 5.47` → `file 5.44` to enable Windows? Alternatives: (a) per-platform versioning in v1 (`if: win then version: "5.44" else version: "5.47"` — *check whether v1 schema permits this in `recipe.version`*), (b) ship a separate `libmagic-win` package with divergent name, (c) volunteer to forward-port `julian-r`'s wrapper onto upstream 5.47.
2. **`julian-r/file-windows` maintenance.** Repo last pushed 2023-03-16. If it goes archived/stale, future bumps are blocked. Mitigation: fork the wrapper into `conda-forge/file-windows-fork` or carry the patch directly in the feedstock.
3. **`pcre2 vendored` vs conda-forge `pcre2`.** julian-r vendors PCRE2 (statically linked). conda-forge ships `pcre2` as a separate package. Conda-forge reviewers may push back on bundling. If so, modify `julian-r/file-windows`'s CMakeLists to use the conda `pcre2` host dep — non-trivial patch.
4. **`magic.mgc` location at runtime.** libmagic compiled with MSVC may have a different default search path than the unix builds. If `magic.Magic()` raises `cannot open ... magic.mgc`, set `MAGIC` env var via an `activate.d` script: `set MAGIC=%CONDA_PREFIX%\Library\share\misc\magic.mgc`. Verify in Step 4.
5. **`libmagic.lib` import library naming.** CMake's MSVC default produces `libmagic.lib` matching `add_library(libmagic SHARED …)`. Some downstream consumers may expect `magic.lib` (no `lib` prefix). Check after Step 1 whether anything in conda-forge depends on `magic.lib` specifically.
6. **AppVeyor disabled tests.** julian-r disables `gedcom`, `fit-map-data`, `regex-eol`, `multiple` in `CMakeLists.txt`. These are known-flaky on Windows and not security-critical, but document them in the PR description.
7. **CI build time.** Windows builds on conda-forge Azure are slow. PCRE2 build dominates. Expected: 15–25 min. Within the 6 hr cap, no concern.

## 8. References

### Issues / PRs (the chain)
- `conda-forge/python-magic-feedstock` issue #9 — Windows Build for python-magic
  https://github.com/conda-forge/python-magic-feedstock/issues/9
- `conda-forge/file-feedstock` issue #3 — Please provide Windows build
  https://github.com/conda-forge/file-feedstock/issues/3
- `ahupp/python-magic` issue #293 — Binary distribution for libmagic on Windows
  https://github.com/ahupp/python-magic/issues/293
- `conda-forge/python-magic-feedstock` PR #13 (closed) — yarikoptic's m2-file attempt
  https://github.com/conda-forge/python-magic-feedstock/pull/13
- `nscaife/file-windows` PR #9 — yarikoptic's cross-compile attempt
  https://github.com/nscaife/file-windows/pull/9

### Source repos
- `file/file` — upstream libmagic
  https://github.com/file/file
- `julian-r/file-windows` — MSVC port adopted in this plan (v5.44)
  https://github.com/julian-r/file-windows
  Pinned commit: `cddf42c5faf23c552b8c033680854b0c7bde0f10`
  AppVeyor reference build: https://ci.appveyor.com/project/julian-r/file-windows
- `ahupp/python-magic` — the python wrapper (v0.4.27)
  https://github.com/ahupp/python-magic
  `magic/loader.py` (used unchanged): https://github.com/ahupp/python-magic/blob/0.4.27/magic/loader.py
- Upstream sdist: http://ftp.astron.com/pub/file/file-5.44.tar.gz
  sha256 `3751c7fba8dbc831cb8d7cc8aff21035459b8ce5155ef8b0880a27d028475f3b`

### Existing conda-forge recipes
- `conda-forge/file-feedstock` (current Linux/macOS-only recipe)
  https://github.com/conda-forge/file-feedstock
- `conda-forge/python-magic-feedstock` (current Linux/macOS-only recipe)
  https://github.com/conda-forge/python-magic-feedstock

### Alternative paths considered & rejected
- `m2-file` (msys2) — https://github.com/conda/conda-recipes/blob/master/msys2/m2-file/meta.yaml
  Rejected: MinGW/MSVC mixing forbidden by conda-forge policy.
- `nscaife/file-windows` — https://github.com/nscaife/file-windows
  Rejected: requires cross-compile (not supported by conda-forge).
- `microsoft/vcpkg` libmagic port — https://github.com/microsoft/vcpkg/tree/master/ports/libmagic
  Rejected: produces `magic-1.dll` (hyphenated), not matching `python-magic`'s `loader.py` prefixes without rename. Also vcpkg-only build flow doesn't fit conda-forge's source-build-from-tarball convention.
- `python-magic-bin` (PyPI wheel) — https://pypi.org/project/python-magic-bin/
  Rejected: unmaintained since 2017; libmagic 5.32; binary repackaging frowned upon by conda-forge.
- `hey-red/Libmagic-Build` — https://github.com/hey-red/Libmagic-Build/tree/master/windows
  Mentioned in #293 but less mature than julian-r.

### Conda-forge tooling docs
- rattler-build recipe.yaml v1 schema: https://prefix-dev.github.io/rattler-build/latest/reference/recipe_file/
- Multi-output `staging` outputs (replaces deprecated `cache:`):
  https://rattler-build.prefix.dev/latest/multiple_output_cache/
- conda-forge maintainer docs: https://conda-forge.org/docs/maintainer/
- BSD-2-Clause-Darwin SPDX: https://spdx.org/licenses/BSD-2-Clause-Darwin.html

### People to coordinate with
- `file-feedstock` maintainers: `blmaier`, `chrisburr`, `mariusvniekerk`, `mrakitin`
- `python-magic-feedstock` maintainers: `mariusvniekerk`
- `julian-r/file-windows` maintainer: `julian-r` (last responsive in 2023)
- Notable interested parties from issue threads: `yarikoptic` (NeuroDebian), `h-vetinari` (conda-forge core), `rluria14` (CKAN context), `jspraul` (vcpkg path researcher)

## 9. Appendix — local commands

All of these run from the repo root.

```bash
# Render only — fast structural validation
pixi run -e local-recipes rattler-build build \
    --recipe recipes/file/recipe.yaml \
    --render-only --target-platform linux-64 \
    -m .ci_support/linux64.yaml

pixi run -e local-recipes rattler-build build \
    --recipe recipes/file/recipe.yaml \
    --render-only --target-platform win-64 \
    -m .ci_support/win64.yaml

# Quality gates
pixi run -e local-recipes validate recipes/file
pixi run -e local-recipes lint-optimize recipes/file
pixi run -e local-recipes scan-vulnerabilities recipes/file
pixi run -e local-recipes license-check recipes/file

# Full builds
pixi run -e local-recipes rattler-build build \
    --recipe recipes/python-magic/recipe.yaml \
    --target-platform linux-64 \
    -m .ci_support/linux64.yaml

# On a Windows host (NOT possible from Linux):
pixi run -e local-recipes rattler-build build ^
    --recipe recipes/file/recipe.yaml ^
    --target-platform win-64 ^
    -m .ci_support/win64.yaml
```

## 10. Change log of this plan

| Date | Change | Author |
|---|---|---|
| 2026-05-06 | Initial draft. Recipes authored, local linux-64 build of `python-magic` succeeded. win-64 build of `file` blocked on Windows host availability. | Claude |
