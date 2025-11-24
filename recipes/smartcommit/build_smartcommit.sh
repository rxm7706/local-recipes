#!/usr/bin/env bash
set -eux -o pipefail

module="github.com/arpxspace/smartcommit"

export GO_EXTLINK_ENABLED=1
export CGO_ENABLED=0
export GO111MODULE=on

command -v go
go version
go env

pushd "src/${module}"
    go build \
        -ldflags "-s -w" \
        -o "${PREFIX}/bin/${PKG_NAME}" \
        "." \
        || exit 1

    # Create license file directory
    mkdir -p "${SRC_DIR}/license-files"

    # Copy the main LICENSE file if it exists, otherwise create MIT license
    if [ -f "LICENSE" ]; then
        cp LICENSE "${SRC_DIR}/license-files/"
    else
        # Create MIT license since repo is marked as MIT but has no LICENSE file
        cat > "${SRC_DIR}/license-files/LICENSE" << 'EOF'
MIT License

Copyright (c) 2024 arpxspace

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
    fi

    # Try to save dependency licenses if go-licenses is available
    if command -v go-licenses &> /dev/null; then
        go-licenses save "." \
            --save_path "${SRC_DIR}/license-files" \
            --force \
            || echo "Warning: go-licenses failed, continuing with main license only"
    fi
popd

ls "${PREFIX}/bin/${PKG_NAME}"

# Make GOPATH directories writeable so conda-build can clean everything up.
if [ -n "$(go env GOPATH)" ]; then
    CLEAN_PATH="$( go env GOPATH )"
    find "${CLEAN_PATH}" -type d -exec chmod +w {} \; || true
fi
