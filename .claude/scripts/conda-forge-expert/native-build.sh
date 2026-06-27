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
#
# Also auto-injects build_artifacts/<config>/ as a file:// channel if it already
# contains any locally built artifacts (repodata.json), so a recipe that depends
# on another recipe built earlier in the same session can resolve it in the test
# env without manual --channel plumbing.

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

# Resolve the recipe directory so we can pick up recipe-level variant configs
# and the patches/ directory if any.
if [[ -d "${RECIPE}" ]]; then
  RECIPE_DIR="${RECIPE}"
else
  RECIPE_DIR="$(dirname "${RECIPE}")"
fi
RECIPE_CBC="${RECIPE_DIR}/conda_build_config.yaml"

# Honor the recipe's own conda_build_config.yaml when present. Passing explicit
# --variant-config flags disables rattler-build's auto-discovery, so without
# this line keys like c_stdlib_version / MACOSX_SDK_VERSION / channel_sources
# from the recipe would be silently dropped (see the getdaft rust_dev case).
if [[ -f "${RECIPE_CBC}" ]]; then
  CMD+=(--variant-config "${RECIPE_CBC}")
  echo "→ recipe-level variant config: ${RECIPE_CBC}" >&2
fi

# Auto-inject any locally built artifacts as an extra channel so cross-recipe
# `run:` deps in the same session (e.g. recipe B depends on recipe A built
# moments ago) resolve in the test env. Detected by the presence of a
# repodata.json under build_artifacts/<config>/<subdir>/.
#
# Subtle bit: rattler-build rejects mixing `--channel file://…` with a variant
# config that sets channel_sources, so we write a tmp variant config. But if
# the recipe also declares channel_sources (e.g. rust_dev label for nightly
# Rust), a naive override drops the recipe's channels. We MERGE: read the
# recipe's channel_sources first, prepend the local file:// channel, then
# write the combined list to the tmp file. The tmp file is passed last so its
# channel_sources wins — and it already contains everything the recipe asked
# for.
#
# IMPORTANT: rattler-build (like conda-build) treats each YAML list ENTRY in
# `channel_sources` as a separate VARIANT axis — `channel_sources: [A, B]`
# means "build the recipe once with channels=[A] and once with channels=[B]".
# To combine multiple channels into ONE variant (which is what we want here),
# we write a single comma-separated entry: `channel_sources: ['A,B']`.
LOCAL_CHANNEL_ROOT="${REPO_ROOT}/build_artifacts/${CONFIG}"
if compgen -G "${LOCAL_CHANNEL_ROOT}/*/repodata.json" > /dev/null 2>&1; then
  LOCAL_VARIANT="$(mktemp -t local-channel-variant.XXXXXX.yaml)"
  trap 'rm -f "${LOCAL_VARIANT}"' EXIT

  # Extract any existing channel_sources entries from the recipe's CBC.
  # YAML-safe: handle both inline list form and indented list form.
  RECIPE_CHANNELS=""
  if [[ -f "${RECIPE_CBC}" ]]; then
    RECIPE_CHANNELS=$(python3 - "${RECIPE_CBC}" <<'PY' 2>/dev/null || true
import sys, yaml
try:
    with open(sys.argv[1]) as f:
        cbc = yaml.safe_load(f) or {}
    for ch in cbc.get('channel_sources', []) or []:
        print(ch)
except Exception:
    pass
PY
)
  fi

  # Build a single comma-separated channel set: local channel first, then
  # whatever the recipe asked for (or conda-forge as the default fallback).
  CHANNEL_SET="file://${LOCAL_CHANNEL_ROOT}"
  if [[ -n "${RECIPE_CHANNELS}" ]]; then
    while IFS= read -r ch; do
      [[ -n "$ch" ]] && CHANNEL_SET="${CHANNEL_SET},${ch}"
    done <<<"${RECIPE_CHANNELS}"
  else
    CHANNEL_SET="${CHANNEL_SET},conda-forge"
  fi

  {
    printf 'channel_sources:\n'
    printf '  - %s\n' "${CHANNEL_SET}"
  } > "${LOCAL_VARIANT}"
  CMD+=(--variant-config "${LOCAL_VARIANT}")
  if [[ -n "${RECIPE_CHANNELS}" ]]; then
    echo "→ auto-injected local channel: file://${LOCAL_CHANNEL_ROOT} (merged with recipe channels)" >&2
  else
    echo "→ auto-injected local channel: file://${LOCAL_CHANNEL_ROOT}" >&2
  fi
fi

# Pass through any extra args after the recipe path straight to rattler-build
# (e.g. `--test skip`, `--target-platform`, `--keep-build`).
CMD+=("${@:2}")

echo "→ ${CMD[*]}"
"${CMD[@]}"
