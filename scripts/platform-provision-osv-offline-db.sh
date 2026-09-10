#!/usr/bin/env bash
# Story 12.4: provision the offline OSV database for golden-path promotion.
# Explicit, connected-runner-only step — Warden's scan stays --offline.
set -euo pipefail

CACHE_ROOT="${OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY:-}"
if [ -z "$CACHE_ROOT" ]; then
  echo "::error::OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY is required" >&2
  exit 1
fi

if ! command -v osv-scanner >/dev/null 2>&1; then
  echo "::error::osv-scanner is required (pyforge-warden env)" >&2
  exit 1
fi

DB_ZIP="${CACHE_ROOT}/osv-scanner/PyPI/all.zip"

db_is_usable() {
  python - "$1" <<'PY'
import sys
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1])
if not zip_path.is_file() or zip_path.stat().st_size == 0:
    raise SystemExit(1)
with zipfile.ZipFile(zip_path) as archive:
    if not archive.namelist():
        raise SystemExit(1)
PY
}

if db_is_usable "$DB_ZIP"; then
  echo "OSV offline DB already provisioned at ${DB_ZIP}"
  exit 0
fi

mkdir -p "$CACHE_ROOT"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

# Minimal input so osv-scanner has a package source while downloading DBs.
echo 'pip==24.0' >"${SCRATCH}/provision-input.txt"

export OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY="$CACHE_ROOT"
osv-scanner scan \
  --offline-vulnerabilities \
  --download-offline-databases \
  -L "requirements.txt:${SCRATCH}/provision-input.txt"

if ! db_is_usable "$DB_ZIP"; then
  echo "::error::OSV offline DB missing or empty after download (${DB_ZIP})" >&2
  exit 1
fi

echo "Provisioned OSV offline DB at ${DB_ZIP} ($(du -h "$DB_ZIP" | awk '{print $1}'))"
