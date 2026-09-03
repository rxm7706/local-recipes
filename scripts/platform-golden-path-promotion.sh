#!/usr/bin/env bash
# Story 43.4: record platform image digests + Warden verdict for golden-path CD.
# Host shell only — never imports pyforge.*. Writes one JSON document to stdout
# and, when OUT is set, to that path.
set -euo pipefail

PLATFORM_REF="${PLATFORM_REF:?PLATFORM_REF is required}"
SIDECAR_REF="${SIDECAR_REF:?SIDECAR_REF is required}"
MCP_HOST_REF="${MCP_HOST_REF:?MCP_HOST_REF is required}"
WARDEN_TARGET="${WARDEN_TARGET:-src/platform}"
OUT="${OUT:-}"

if ! command -v docker >/dev/null 2>&1; then
  echo "::error::docker is required to record image digests" >&2
  exit 1
fi
if ! command -v warden >/dev/null 2>&1; then
  echo "::error::warden is required (pyforge-warden env)" >&2
  exit 1
fi

image_digest() {
  local ref="$1"
  docker inspect --format='{{.Id}}' "$ref"
}

PLATFORM_DIGEST="$(image_digest "$PLATFORM_REF")"
SIDECAR_DIGEST="$(image_digest "$SIDECAR_REF")"
MCP_HOST_DIGEST="$(image_digest "$MCP_HOST_REF")"
export PLATFORM_DIGEST SIDECAR_DIGEST MCP_HOST_DIGEST

WARDEN_JSON="$(mktemp)"
trap 'rm -f "$WARDEN_JSON"' EXIT
warden scan "$WARDEN_TARGET" --format json >"$WARDEN_JSON"

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
            "digest": os.environ["PLATFORM_DIGEST"],
        },
        "sidecar": {
            "ref": os.environ["SIDECAR_REF"],
            "digest": os.environ["SIDECAR_DIGEST"],
        },
        "mcpHost": {
            "ref": os.environ["MCP_HOST_REF"],
            "digest": os.environ["MCP_HOST_DIGEST"],
        },
    },
    "warden": json.load(open(warden_path, encoding="utf-8")),
}
text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
sys.stdout.write(text)
if out_path:
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(text)
PY
