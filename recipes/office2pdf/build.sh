#!/usr/bin/env bash
set -euxo pipefail

# The [patch.crates-io] git-fork deps are supplied as sibling source: entries
# (_src/umya, _src/docxrs) and repointed to relative paths by
# patches/0001-vendor-git-fork-deps.patch, so the build is offline-safe.
cd "${SRC_DIR}/_src/office2pdf"

export CARGO_PROFILE_RELEASE_STRIP=symbols

# Canonical conda-forge Rust CLI install (auditable SBOM embedded, no
# .crates.toml in the prefix, binary-only). --locked is intentionally omitted:
# upstream ships no Cargo.lock (see recipe CFE comments for the upstream ask).
cargo auditable install --no-track --bins --root "${PREFIX}" --path crates/office2pdf-cli

# Third-party license bundle for the vendored dependency tree.
cargo-bundle-licenses --format yaml --output "${SRC_DIR}/THIRDPARTY.yml"

# Stage the upstream LICENSE where about.license_file can find it.
cp LICENSE "${SRC_DIR}/LICENSE"
