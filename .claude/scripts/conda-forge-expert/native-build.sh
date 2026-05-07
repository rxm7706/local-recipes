#!/usr/bin/env bash
# Native rattler-build wrapper for local recipe verification.
#
# Why this exists:
#   .ci_support/linux64.yaml (and the other platform variant configs) no longer
#   declare `python` / `python_min` since the May 2026 upstream sync — those
#   defaults come from `conda-forge-pinning`. For local rattler-build to render
#   recipes that reference ${{ python_min }} (the CFEP-25 default pattern),
#   we need to pass conda-forge-pinning's conda_build_config.yaml as a second
#   --variant-config. The local-recipes pixi env already installs that package
#   at .pixi/envs/local-recipes/conda_build_config.yaml.
#
# Usage:
#   pixi run -e local-recipes recipe-build <path-to-recipe>
#
# The recipe argument can be a recipe.yaml file or its containing directory.
# Auto-detects the host platform from `uname -ms`.

set -euo pipefail

RECIPE="${1:?Usage: $0 <path-to-recipe.yaml or recipe directory>}"
REPO_ROOT="${PIXI_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Auto-detect host platform → .ci_support/<config>.yaml stem
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64|Linux/amd64)   CONFIG=linux64 ;;
  Linux/aarch64|Linux/arm64)  CONFIG=linux_aarch64 ;;
  Darwin/arm64|Darwin/aarch64) CONFIG=osxarm64 ;;
  Darwin/x86_64)              CONFIG=osx64 ;;
  MINGW*/*|MSYS*/*|CYGWIN*/*) CONFIG=win64 ;;
  *)
    echo "Unsupported host: $(uname -s)/$(uname -m)" >&2
    echo "Add a case for your platform in $0" >&2
    exit 1
    ;;
esac

VARIANT_PLATFORM="${REPO_ROOT}/.ci_support/${CONFIG}.yaml"
VARIANT_PINNING="${REPO_ROOT}/.pixi/envs/local-recipes/conda_build_config.yaml"

if [[ ! -f "${VARIANT_PLATFORM}" ]]; then
  echo "Platform variant config not found: ${VARIANT_PLATFORM}" >&2
  exit 1
fi

CMD=(rattler-build build
  --recipe "${RECIPE}"
  --variant-config "${VARIANT_PLATFORM}"
)

if [[ -f "${VARIANT_PINNING}" ]]; then
  CMD+=(--variant-config "${VARIANT_PINNING}")
else
  echo "WARN: conda-forge-pinning overlay not found at ${VARIANT_PINNING}" >&2
  echo "      Recipes referencing \${{ python_min }} may fail to render." >&2
  echo "      Run 'pixi install -e local-recipes' to populate it." >&2
fi

CMD+=(--output-dir "${REPO_ROOT}/build_artifacts/${CONFIG}")

echo "→ ${CMD[*]}"
exec "${CMD[@]}"
