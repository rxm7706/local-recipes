#!/usr/bin/env bash
set -euxo pipefail

module="github.com/git-pkgs/forge"

cd "${SRC_DIR}"

export CGO_ENABLED=0
export GOTOOLCHAIN=local
export GOFLAGS="-mod=mod"

rm -rf "${SRC_DIR}/library_licenses"
mkdir -p "${SRC_DIR}/library_licenses"

go-licenses save ./cmd/forge \
    --save_path "${SRC_DIR}/library_licenses" \
    --force

go build \
    -trimpath \
    -ldflags "-s -w -X ${module}/internal/cli.Version=${PKG_VERSION}" \
    -o "${PREFIX}/bin/${PKG_NAME}" \
    ./cmd/forge
