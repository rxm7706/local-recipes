#!/usr/bin/env bash
# Story 48.10: build the root Containerfile and run post-build container gates.
#
# Usage: guild_image_ci.sh [docker|podman]
#
# Build-time gates (secrets-scan, cli-smoke) already run inside the Containerfile
# RUN steps. This script adds the CI entrypoint: full image build plus explicit
# post-build secrets-scan and volumes-roundtrip against the tagged result.

set -euo pipefail

ENGINE="${1:-docker}"
TAG="${GUILD_IMAGE_TAG:-pyforge-guild-ci}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v "$ENGINE" >/dev/null 2>&1; then
  echo "guild_image_ci: ${ENGINE} not found on PATH" >&2
  exit 1
fi

SHIM=""
cleanup() {
  if [ -n "$SHIM" ] && [ -d "$SHIM" ]; then
    rm -rf "$SHIM"
  fi
}
trap cleanup EXIT

# `container-gates volumes-roundtrip` invokes the `docker` binary by name.
# On the podman matrix leg, shim docker -> podman without editing the gate script.
if [ "$ENGINE" = "podman" ]; then
  SHIM="$(mktemp -d)"
  ln -s "$(command -v podman)" "$SHIM/docker"
  export PATH="$SHIM:$PATH"
fi

echo "guild_image_ci: building root Containerfile with ${ENGINE} -> ${TAG}"
"$ENGINE" build -f Containerfile -t "$TAG" .

echo "guild_image_ci: post-build secrets-scan"
"$ENGINE" run --rm --entrypoint /entrypoint.sh "$TAG" \
  python3 /pyforge/scripts/container-gates secrets-scan \
  /pyforge /shell-hook.sh /entrypoint.sh

echo "guild_image_ci: post-build volumes-roundtrip"
python3 scripts/container-gates volumes-roundtrip \
  --image "$TAG" \
  --mount /pyforge/.steward \
  --mount /pyforge/.claude/data/conda-forge-expert \
  --mount /root/.bmad-loops

echo "guild_image_ci: all gates passed for ${TAG}"
