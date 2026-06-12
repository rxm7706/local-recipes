#!/usr/bin/env bash
# Cross-platform rattler-build wrapper for local recipe verification.
#
# Why this exists:
#   native-build.sh only builds for the host platform. For platforms the
#   host can't reach natively (e.g. osx-arm64 from a linux-64 dev box) or
#   that staged-recipes' CI matrix doesn't cover at PR time (osx-arm64,
#   linux-aarch64), this wrapper produces a downloadable `.conda` artifact
#   you can test on the target machine before submission.
#
# Usage:
#   pixi run -e local-recipes recipe-build-cross <recipe> <target-platform>
#
#   <recipe>           recipe.yaml file or its containing directory
#   <target-platform>  osx-arm64 | osx-64 | linux-aarch64 | linux-64 | win-64
#
# What this script does on top of plain `rattler-build build`:
#   1. Loads the right .ci_support/<config>.yaml + conda-forge-pinning
#      overlay so target-platform variant resolution mirrors upstream CI.
#   2. Sets CONDA_OVERRIDE_OSX / CONDA_OVERRIDE_GLIBC so the host
#      virtual-package solve succeeds on a cross host.
#   3. For osx-arm64 / osx-64 cross builds: injects `cctools_<arch>` +
#      `ld64_<arch>` into requirements.build (provides the cross
#      install_name_tool) and appends a shim to build.sh that symlinks
#      it to the plain name rattler-build's Mach-O relinker searches for.
#      The mutation happens in a temp recipe copy; your source recipe is
#      not touched.
#   4. For win-64 cross builds: overrides `build.script` in recipe.yaml
#      to force rattler-build to use build.sh (cmd.exe can't run on a
#      unix host). The recipe's build.sh MUST handle `target_platform ==
#      "win-64"` itself — typically by writing to `${PREFIX}/Library/bin`
#      and adding `.exe` suffixes. This wrapper can't auto-translate
#      build.bat; if the recipe ships only build.bat, the wrapper errors.
#   5. Passes `--test skip` because rattler-build can't execute foreign-
#      arch binaries on the host. Verify the artifact manually on the
#      target machine before submitting.
#
# Output lands in build_artifacts/<config>/<target-platform>/<pkg>.conda
# (alongside native-build.sh's output tree).
#
# Limitations:
#   - Single-output recipes only. The cctools-injection regex assumes a
#     single top-level `requirements.build:` block. Multi-output recipes
#     should edit their own build deps and use plain `rattler-build build`.
#   - Win-64 cross requires a target_platform-aware build.sh in the
#     recipe (see point 4 above).
#   - Compiled-source cross-builds (anything that runs a real compiler)
#     need more than this script wires up — sysroot, kernel-headers,
#     compiler shims, etc. This wrapper is tuned for binary-repackage
#     recipes (the staged-recipes pattern for prebuilt CLI tools).

set -euo pipefail

RECIPE_ARG="${1:?Usage: $0 <path-to-recipe> <target-platform>}"
TARGET_PLATFORM="${2:?Usage: $0 <path-to-recipe> <target-platform>}"

# Resolve recipe path → recipe dir
if [[ -d "${RECIPE_ARG}" ]]; then
  RECIPE_DIR="$(cd "${RECIPE_ARG}" && pwd)"
elif [[ -f "${RECIPE_ARG}" ]]; then
  RECIPE_DIR="$(cd "$(dirname "${RECIPE_ARG}")" && pwd)"
else
  echo "Recipe not found: ${RECIPE_ARG}" >&2
  exit 1
fi

# Map target-platform → .ci_support config name + CONDA_OVERRIDE_* + cross-tool arch
NEEDS_MACH_O_SHIM=0
NEEDS_WIN_SCRIPT_OVERRIDE=0
CROSS_TOOLS_ARCH=""
CONDA_OVERRIDE_KEY=""
CONDA_OVERRIDE_DEFAULT=""

case "${TARGET_PLATFORM}" in
  osx-arm64)
    CONFIG=osxarm64
    CONDA_OVERRIDE_KEY=OSX
    CONDA_OVERRIDE_DEFAULT=11.0
    CROSS_TOOLS_ARCH=osx-arm64
    NEEDS_MACH_O_SHIM=1
    ;;
  osx-64)
    CONFIG=osx64
    CONDA_OVERRIDE_KEY=OSX
    CONDA_OVERRIDE_DEFAULT=10.13
    CROSS_TOOLS_ARCH=osx-64
    NEEDS_MACH_O_SHIM=1
    ;;
  linux-aarch64)
    CONFIG=linux_aarch64
    CONDA_OVERRIDE_KEY=GLIBC
    CONDA_OVERRIDE_DEFAULT=2.17
    ;;
  linux-64)
    CONFIG=linux64
    CONDA_OVERRIDE_KEY=GLIBC
    CONDA_OVERRIDE_DEFAULT=2.17
    ;;
  win-64)
    CONFIG=win64
    NEEDS_WIN_SCRIPT_OVERRIDE=1
    ;;
  *)
    echo "Unsupported target-platform: ${TARGET_PLATFORM}" >&2
    echo "Supported: osx-arm64 | osx-64 | linux-aarch64 | linux-64 | win-64" >&2
    exit 1
    ;;
esac

REPO_ROOT="${PIXI_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
VARIANT_PLATFORM="${REPO_ROOT}/.ci_support/${CONFIG}.yaml"
VARIANT_PINNING="${REPO_ROOT}/.pixi/envs/local-recipes/conda_build_config.yaml"
RECIPE_CBC="${RECIPE_DIR}/conda_build_config.yaml"

if [[ ! -f "${VARIANT_PLATFORM}" ]]; then
  echo "Platform variant config not found: ${VARIANT_PLATFORM}" >&2
  exit 1
fi

OUTPUT_DIR="${REPO_ROOT}/build_artifacts/${CONFIG}"
mkdir -p "${OUTPUT_DIR}"

# Detect host platform
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64|Linux/amd64)   HOST_PLATFORM=linux-64 ;;
  Linux/aarch64|Linux/arm64)  HOST_PLATFORM=linux-aarch64 ;;
  Darwin/arm64|Darwin/aarch64) HOST_PLATFORM=osx-arm64 ;;
  Darwin/x86_64)              HOST_PLATFORM=osx-64 ;;
  *)                          HOST_PLATFORM=unknown ;;
esac

# Native build → defer to native-build.sh (it already handles local-channel
# injection + auto-discovery of recipe CBC overrides).
if [[ "${TARGET_PLATFORM}" == "${HOST_PLATFORM}" ]]; then
  echo "→ host == target (${HOST_PLATFORM}); delegating to native-build.sh" >&2
  exec bash "$(dirname "$0")/native-build.sh" "${RECIPE_DIR}"
fi

# Cross-build: work on a temp copy so the source recipe is untouched.
TMP=$(mktemp -d -t cfe-cross-XXXXXX)
trap 'rm -rf "${TMP}"' EXIT
cp -r "${RECIPE_DIR}" "${TMP}/recipe"
WORK="${TMP}/recipe"

if [[ "${NEEDS_MACH_O_SHIM}" == "1" ]]; then
  # Inject cross-tools into requirements.build of a single-output recipe.
  python3 - "${WORK}/recipe.yaml" "${CROSS_TOOLS_ARCH}" <<'PY'
import re, sys
path, arch = sys.argv[1], sys.argv[2]
text = open(path).read()
inject = (
    "    - if: build_platform != target_platform\n"
    "      then:\n"
    f"        - cctools_{arch}\n"
    f"        - ld64_{arch}\n"
)
# Match a single-output `requirements.build:` block (top-level, 2-space indent).
# MULTILINE only — DOTALL would make `.` match newlines and greedily swallow
# everything past the build block.
m = re.search(
    r"(?m)^requirements:\n(?:[ \t]+.*\n)*?  build:\n((?:    .*\n)+)",
    text,
)
if not m:
    print(
        "WARN: cross-build.sh could not locate a single-output "
        "requirements.build block; cross-tools not injected. "
        "If this is a multi-output recipe, add cctools_/ld64_ deps manually.",
        file=sys.stderr,
    )
    sys.exit(0)
block = m.group(1)
open(path, "w").write(text.replace(block, block + inject, 1))
print(f"→ injected cctools_{arch} + ld64_{arch} into requirements.build", file=sys.stderr)
PY

  BUILD_SH="${WORK}/build.sh"
  if [[ -f "${BUILD_SH}" ]]; then
    cat >> "${BUILD_SH}" <<'SHIM'

# Cross-build shim (auto-appended by cross-build.sh):
# rattler-build's relinker invokes `install_name_tool` by its plain name;
# conda-forge's cross-tool ships as `<triple>-install_name_tool`. Bridge it.
if [[ -n "${INSTALL_NAME_TOOL:-}" && "${INSTALL_NAME_TOOL}" != "install_name_tool" ]]; then
  TOOL_PATH="$(command -v "${INSTALL_NAME_TOOL}" || true)"
  if [[ -n "${TOOL_PATH}" && ! -e "${BUILD_PREFIX}/bin/install_name_tool" ]]; then
    ln -sf "${TOOL_PATH}" "${BUILD_PREFIX}/bin/install_name_tool"
  fi
fi
SHIM
    echo "→ appended install_name_tool shim to build.sh" >&2
  else
    echo "WARN: no build.sh in recipe; install_name_tool shim not installed" >&2
  fi
fi

if [[ "${NEEDS_WIN_SCRIPT_OVERRIDE}" == "1" ]]; then
  if [[ ! -f "${WORK}/build.sh" ]]; then
    echo "Error: win-64 cross-build requires a target_platform-aware build.sh in the recipe." >&2
    echo "       The recipe at ${RECIPE_DIR} ships only build.bat which cannot run on a unix host." >&2
    echo "       Add a build.sh that branches on \${target_platform} to handle win-64 (write to" >&2
    echo "       \${PREFIX}/Library/bin and append .exe suffixes) and try again." >&2
    exit 1
  fi
  # Force rattler-build to use build.sh even on win target. Without this it
  # auto-picks build.bat on `target_platform: win-*` and cmd.exe is absent.
  python3 - "${WORK}/recipe.yaml" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path).read()
if re.search(r"(?m)^build:\n(?:[ \t]+.*\n)*?[ \t]+script:", text):
    print("→ build.script already set; leaving it alone", file=sys.stderr)
    sys.exit(0)
new = re.sub(
    r"(?m)^(build:\n  number:[^\n]*\n)",
    r"\1  script: bash ./build.sh\n",
    text,
    count=1,
)
if new == text:
    print("WARN: could not patch build: block to override build.script", file=sys.stderr)
    sys.exit(0)
open(path, "w").write(new)
print("→ overrode build.script -> bash ./build.sh (win-64 cross)", file=sys.stderr)
PY
fi

# Apply CONDA_OVERRIDE_* so host virtual-package solve succeeds on a cross host
if [[ -n "${CONDA_OVERRIDE_KEY}" ]]; then
  EXISTING_VAR="CONDA_OVERRIDE_${CONDA_OVERRIDE_KEY}"
  # Indirect expansion: keep existing override if user set one
  CURRENT="${!EXISTING_VAR:-}"
  if [[ -z "${CURRENT}" ]]; then
    export "${EXISTING_VAR}=${CONDA_OVERRIDE_DEFAULT}"
    echo "→ ${EXISTING_VAR}=${CONDA_OVERRIDE_DEFAULT} (cross-host override)" >&2
  else
    export "${EXISTING_VAR}=${CURRENT}"
    echo "→ ${EXISTING_VAR}=${CURRENT} (inherited from environment)" >&2
  fi
fi

CMD=(rattler-build build
  --recipe "${WORK}"
  --target-platform "${TARGET_PLATFORM}"
  --variant-config "${VARIANT_PLATFORM}"
)
if [[ -f "${VARIANT_PINNING}" ]]; then
  CMD+=(--variant-config "${VARIANT_PINNING}")
else
  echo "WARN: conda-forge-pinning overlay not found at ${VARIANT_PINNING}" >&2
  echo "      Run 'pixi install -e local-recipes' to populate it." >&2
fi
# Recipe's own conda_build_config.yaml (selectors trim what doesn't apply)
[[ -f "${RECIPE_CBC}" ]] && CMD+=(--variant-config "${RECIPE_CBC}")

CMD+=(--output-dir "${OUTPUT_DIR}" --test skip)

echo "→ host=${HOST_PLATFORM}  target=${TARGET_PLATFORM}  config=${CONFIG}" >&2
echo "→ ${CMD[*]}"
"${CMD[@]}"
