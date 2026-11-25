#!/usr/bin/env bash
# Story 43.4: record the platform images + Warden verdict for golden-path CD.
# Host shell only — never imports pyforge.*. Writes one JSON document to stdout
# and, when OUT is set, to that path.
#
# Story 134.1: two different values, two keys. `images.*.image_id` is the
# engine's local image ID, always recorded. `images.*.digest` is the registry
# manifest digest, which exists only after a push: it is recorded when the
# image's *_PUSHED_REF names the reference that was pushed, and is empty
# otherwise. Nothing here pushes; the caller pushes first and hands the
# references over. An image ID is never written under `digest`.
set -euo pipefail

PLATFORM_REF="${PLATFORM_REF:?PLATFORM_REF is required}"
SIDECAR_REF="${SIDECAR_REF:?SIDECAR_REF is required}"
MCP_HOST_REF="${MCP_HOST_REF:?MCP_HOST_REF is required}"
# What Warden scans: the shipped `python-agent-platform` / `linux-64` closure
# from the workspace `pixi.lock` (Story 12.3). Repo-root recursive discovery
# fails closed on symlinked subtrees, so when unset we stage only `pixi.lock`
# in an isolated dir — never a bare `pixi.toml`.
PIXI_ENVIRONMENT="${PIXI_ENVIRONMENT:-python-agent-platform}"
PIXI_PLATFORM="${PIXI_PLATFORM:-linux-64}"
WARDEN_TARGET="${WARDEN_TARGET:-}"
OUT="${OUT:-}"
# The pushed reference of each image (`<registry>/<repository>:<tag>`), or empty when it was not pushed.
PLATFORM_PUSHED_REF="${PLATFORM_PUSHED_REF:-}"
SIDECAR_PUSHED_REF="${SIDECAR_PUSHED_REF:-}"
MCP_HOST_PUSHED_REF="${MCP_HOST_PUSHED_REF:-}"
export PLATFORM_PUSHED_REF SIDECAR_PUSHED_REF MCP_HOST_PUSHED_REF

if ! command -v docker >/dev/null 2>&1; then
  echo "::error::docker is required to record image IDs and registry digests" >&2
  exit 1
fi
if ! command -v warden >/dev/null 2>&1; then
  echo "::error::warden is required (pyforge-warden env)" >&2
  exit 1
fi

image_id() {
  docker inspect --format='{{.Id}}' "$1"
}

# The manifest digest the registry reports for the repository of a pushed
# reference: the `RepoDigests` entry of that repository, which the engine
# fills in when the push completes. Empty input (nothing pushed) is an empty
# answer. A pushed reference with no well-formed entry for its repository is
# an error: the image ID never stands in for it. The pushed reference must
# also be the same image as the local one (same image ID), or the artifact
# would pair one image's ID with another image's digest.
registry_digest() {
  local pushed_ref="$1" local_ref="$2" local_id="$3" pushed_id repository hub_name reported line digest=""
  if [ -z "$pushed_ref" ]; then
    return 0
  fi
  if ! pushed_id="$(image_id "$pushed_ref")"; then
    echo "::error::cannot read the image ID of pushed reference $pushed_ref" >&2
    return 1
  fi
  if [ "$pushed_id" != "$local_id" ]; then
    echo "::error::pushed reference $pushed_ref is not the image recorded as $local_ref (image ID $pushed_id, not $local_id)" >&2
    return 1
  fi
  repository="${pushed_ref%@*}"
  case "${repository##*/}" in
    *:*) repository="${repository%:*}" ;;
  esac
  # Docker Hub repositories are reported without their registry host.
  hub_name="${repository#index.docker.io/}"
  hub_name="${hub_name#docker.io/}"
  reported="$(docker inspect --format='{{range .RepoDigests}}{{println .}}{{end}}' "$pushed_ref")"
  while IFS= read -r line; do
    if [ "${line%@*}" = "$repository" ] || [ "${line%@*}" = "$hub_name" ]; then
      digest="${line##*@}"
    fi
  done <<<"$reported"
  if ! [[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "::error::no registry manifest digest for pushed reference $pushed_ref (was it pushed? the engine reports: ${reported//$'\n'/ })" >&2
    return 1
  fi
  printf '%s\n' "$digest"
}

PLATFORM_IMAGE_ID="$(image_id "$PLATFORM_REF")"
SIDECAR_IMAGE_ID="$(image_id "$SIDECAR_REF")"
MCP_HOST_IMAGE_ID="$(image_id "$MCP_HOST_REF")"
PLATFORM_DIGEST="$(registry_digest "$PLATFORM_PUSHED_REF" "$PLATFORM_REF" "$PLATFORM_IMAGE_ID")"
SIDECAR_DIGEST="$(registry_digest "$SIDECAR_PUSHED_REF" "$SIDECAR_REF" "$SIDECAR_IMAGE_ID")"
MCP_HOST_DIGEST="$(registry_digest "$MCP_HOST_PUSHED_REF" "$MCP_HOST_REF" "$MCP_HOST_IMAGE_ID")"
export PLATFORM_IMAGE_ID SIDECAR_IMAGE_ID MCP_HOST_IMAGE_ID
export PLATFORM_DIGEST SIDECAR_DIGEST MCP_HOST_DIGEST
{
  echo "platform: image ID $PLATFORM_IMAGE_ID; registry digest ${PLATFORM_DIGEST:-none (not pushed)}"
  echo "sidecar: image ID $SIDECAR_IMAGE_ID; registry digest ${SIDECAR_DIGEST:-none (not pushed)}"
  echo "mcp-host: image ID $MCP_HOST_IMAGE_ID; registry digest ${MCP_HOST_DIGEST:-none (not pushed)}"
} >&2

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT
if [ -z "$WARDEN_TARGET" ]; then
  mkdir -p "$SCRATCH/workspace"
  cp pixi.lock "$SCRATCH/workspace/pixi.lock"
  WARDEN_TARGET="$SCRATCH/workspace"
fi
WARDEN_JSON="$SCRATCH/warden.json"
# The verdict is RECORDED here, whatever it is; platform-deploy is what
# refuses a digest whose verdict is not clean (Story 12.1). Warden exits
# non-zero for any non-clean composed status, so the exit code is captured
# into the record instead of aborting the promotion job (CAP-4 honesty).
set +e
warden scan "$WARDEN_TARGET" \
  --pixi-environment "$PIXI_ENVIRONMENT" \
  --pixi-platform "$PIXI_PLATFORM" \
  --format json >"$WARDEN_JSON"
WARDEN_EXIT=$?
set -e
export WARDEN_EXIT
if [ ! -s "$WARDEN_JSON" ]; then
  echo "::error::warden produced no report (exit $WARDEN_EXIT)" >&2
  exit 1
fi

python - "$WARDEN_JSON" "$OUT" <<'PY'
import json
import os
import sys
from datetime import UTC, datetime

warden_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else ""

payload = {
    "schema": "platform-golden-path-promotion/v1",
    "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    "git_sha": os.environ.get("GITHUB_SHA", ""),
    "run_id": os.environ.get("GITHUB_RUN_ID", ""),
    "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
    "images": {
        "platform": {
            "ref": os.environ["PLATFORM_REF"],
            "pushed_ref": os.environ.get("PLATFORM_PUSHED_REF", ""),
            "digest": os.environ.get("PLATFORM_DIGEST", ""),
            "image_id": os.environ["PLATFORM_IMAGE_ID"],
        },
        "sidecar": {
            "ref": os.environ["SIDECAR_REF"],
            "pushed_ref": os.environ.get("SIDECAR_PUSHED_REF", ""),
            "digest": os.environ.get("SIDECAR_DIGEST", ""),
            "image_id": os.environ["SIDECAR_IMAGE_ID"],
        },
        "mcpHost": {
            "ref": os.environ["MCP_HOST_REF"],
            "pushed_ref": os.environ.get("MCP_HOST_PUSHED_REF", ""),
            "digest": os.environ.get("MCP_HOST_DIGEST", ""),
            "image_id": os.environ["MCP_HOST_IMAGE_ID"],
        },
    },
    "warden": json.load(open(warden_path, encoding="utf-8")),
}
payload["warden_exit_code"] = int(os.environ.get("WARDEN_EXIT", "0"))
payload["warden_status"] = (payload["warden"].get("status") or {}).get("value")
text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
sys.stdout.write(text)
if out_path:
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(text)
PY
