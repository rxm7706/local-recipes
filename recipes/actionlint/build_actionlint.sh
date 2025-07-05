#!/usr/bin/env bash
set -eux -o pipefail

module="github.com/rhysd/actionlint"

GOPATH="$( pwd )"
export GOPATH
export GOROOT="${BUILD_PREFIX}/go"
export GO_EXTLINK_ENABLED=1
export CGO_ENABLED=1
export GO111MODULE=on

command -v go
env | grep GOROOT
go version

pushd "src/${module}"
    go build \
        -buildmode=pie \
        -ldflags "-s -w -X ${module}.version=${PKG_VERSION}" \
        -o "${PREFIX}/bin/${PKG_NAME}" \
        "./cmd/${PKG_NAME}" \
        || exit 1
    go-licenses save "./cmd/${PKG_NAME}" \
        --save_path "${SRC_DIR}/license-files" \
        || exit 1
popd

ls "${PREFIX}/bin/${PKG_NAME}"

# Make GOPATH directories writeable so conda-build can clean everything up.
CLEAN_PATH="$( go env GOPATH )"
find "${CLEAN_PATH}" -type d -exec chmod +w {} \;
