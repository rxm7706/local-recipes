#!/bin/bash
# Generate vendored dependency tarballs for the tolaria conda recipe.
#
# Run on macOS arm64 (or any host with rust + node 24 + pnpm 10 + tar).
# Steps:
#   1. Download and extract the upstream source tarball pinned in recipe.yaml.
#   2. From inside the extracted source tree, run this script:
#        bash /path/to/recipes/tolaria/vendor.sh 2026.4.25
#   3. Upload the two resulting tarballs to a stable HTTPS host
#      (e.g. a release on github.com/rxm7706/conda-recipes-vendored).
#   4. Paste the printed sha256 values into recipe.yaml's source[1] and
#      source[2] entries, and update their URLs if you used a different host.
set -euxo pipefail

VERSION="${1:?usage: vendor.sh <tolaria-version, e.g. 2026.4.25>}"
WORK="$(pwd)"

[[ -f Cargo.lock || -f src-tauri/Cargo.lock ]] || {
  echo "ERROR: run this script from the extracted tolaria source tree." >&2
  exit 1
}

# 1. Cargo vendor: fetches every crate referenced in src-tauri/Cargo.lock
#    into ./cargo-vendor/, with each crate in a versioned subdirectory.
( cd src-tauri && cargo vendor --locked --versioned-dirs "${WORK}/cargo-vendor" )

# 2. pnpm fetch: populates a portable content-addressable store with every
#    tarball referenced in pnpm-lock.yaml. Only stores files; no symlinks
#    are created, so the resulting tarball is fully relocatable.
mkdir -p "${WORK}/pnpm-store"
pnpm fetch --frozen-lockfile --store-dir "${WORK}/pnpm-store"

# 3. Tar each up *without* a top-level wrapper directory so the recipe can
#    use `target_directory:` to pick the extraction location.
( cd "${WORK}/cargo-vendor" && tar -czf "${WORK}/tolaria-cargo-vendor-${VERSION}.tar.gz" . )
( cd "${WORK}/pnpm-store"   && tar -czf "${WORK}/tolaria-pnpm-store-${VERSION}.tar.gz" . )

echo
echo "=== sha256 values for recipe.yaml ==="
shasum -a 256 \
  "tolaria-cargo-vendor-${VERSION}.tar.gz" \
  "tolaria-pnpm-store-${VERSION}.tar.gz"
echo
echo "Upload both tarballs to a stable HTTPS host, then update"
echo "recipes/tolaria/recipe.yaml source[1].sha256 and source[2].sha256."
