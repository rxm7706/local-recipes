#!/usr/bin/env bash
# Story 12.4: provision the offline OSV database for golden-path promotion.
# Story 16.8: PyPI, npm, Go and crates.io -- the fleet worker scans non-Python
# lockfiles against these (WARDEN_OSV_DB_CACHE_DIRECTORY names this cache).
# Explicit, connected-runner-only step — Warden's scan stays --offline.
set -euo pipefail

CACHE_ROOT="${OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY:-}"
if [ -z "$CACHE_ROOT" ]; then
  echo "::error::OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY is required" >&2
  exit 1
fi

# osv-scanner's own case-sensitive ecosystem directory names.
ECOSYSTEMS=(PyPI npm Go crates.io)

db_zip() {
  printf '%s/osv-scanner/%s/all.zip' "$CACHE_ROOT" "$1"
}

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

# Checked per ecosystem BEFORE osv-scanner's own presence: the whole point of
# this idempotent-skip path is to need nothing further when every DB is already
# usable, including the tool itself (found live 2026-09-14 -- a test-only
# run with osv-scanner absent from PATH, matching platform-ci-test's real
# pixi env, failed here even though the DB was already provisioned).
MISSING=()
for eco in "${ECOSYSTEMS[@]}"; do
  if db_is_usable "$(db_zip "$eco")"; then
    echo "OSV offline DB already provisioned at $(db_zip "$eco")"
  else
    MISSING+=("$eco")
  fi
done
if [ "${#MISSING[@]}" -eq 0 ]; then
  exit 0
fi

if ! command -v osv-scanner >/dev/null 2>&1; then
  echo "::error::osv-scanner is required (pyforge-warden env)" >&2
  exit 1
fi

mkdir -p "$CACHE_ROOT"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

# One minimal input per missing ecosystem: osv-scanner downloads the database
# of each ecosystem its inputs name, and only those.
INPUTS=()
for eco in "${MISSING[@]}"; do
  case "$eco" in
    PyPI)
      echo 'pip==24.0' >"${SCRATCH}/requirements.txt"
      INPUTS+=(-L "requirements.txt:${SCRATCH}/requirements.txt")
      ;;
    npm)
      cat >"${SCRATCH}/package-lock.json" <<'JSON'
{
  "name": "osv-provision-input",
  "version": "0.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {"name": "osv-provision-input", "version": "0.0.0", "dependencies": {"lodash": "4.17.20"}},
    "node_modules/lodash": {"version": "4.17.20"}
  }
}
JSON
      INPUTS+=(-L "package-lock.json:${SCRATCH}/package-lock.json")
      ;;
    Go)
      printf 'module example.com/osv-provision-input\n\ngo 1.21\n\nrequire golang.org/x/text v0.3.0\n' \
        >"${SCRATCH}/go.mod"
      INPUTS+=(-L "go.mod:${SCRATCH}/go.mod")
      ;;
    crates.io)
      printf 'version = 3\n\n[[package]]\nname = "smallvec"\nversion = "1.6.0"\nsource = "registry+https://github.com/rust-lang/crates.io-index"\n' \
        >"${SCRATCH}/Cargo.lock"
      INPUTS+=(-L "Cargo.lock:${SCRATCH}/Cargo.lock")
      ;;
  esac
done

export OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY="$CACHE_ROOT"
# `|| true`: osv-scanner exits 1 when it finds vulnerabilities, which the
# placeholder bootstrap inputs always have -- a normal, expected outcome
# here, not a download failure. The real pass/fail authority is the
# db_is_usable re-check right below, same as the skip-path check above
# (found live 2026-09-14 -- under set -e this exit code killed the script
# before that re-check ever ran).
osv-scanner scan \
  --offline-vulnerabilities \
  --download-offline-databases \
  "${INPUTS[@]}" || true

FAILED=0
for eco in "${MISSING[@]}"; do
  zip="$(db_zip "$eco")"
  if db_is_usable "$zip"; then
    echo "Provisioned OSV offline DB at ${zip} ($(du -h "$zip" | awk '{print $1}'))"
  else
    echo "::error::OSV offline DB missing or empty after download (${zip})" >&2
    FAILED=1
  fi
done
exit "$FAILED"
