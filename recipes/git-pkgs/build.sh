#!/usr/bin/env bash
set -euxo pipefail

module="github.com/git-pkgs/git-pkgs"

cd "${SRC_DIR}"

export CGO_ENABLED=0
export GOTOOLCHAIN=local
export GOFLAGS="-mod=mod"

# Mirror upstream .goreleaser.yaml before-build hooks (tag archive has no git metadata).
go mod tidy
go run scripts/generate-man/main.go
go run scripts/generate-docs/main.go

rm -rf "${SRC_DIR}/library_licenses"
mkdir -p "${SRC_DIR}/library_licenses"

go-licenses save . --save_path "${SRC_DIR}/library_licenses"

go build \
    -trimpath \
    -ldflags "-s -w -X ${module}/cmd.version=${PKG_VERSION}" \
    -o "${PREFIX}/bin/${PKG_NAME}" \
    .
