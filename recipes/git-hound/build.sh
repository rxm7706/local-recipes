#!/usr/bin/env bash

set -o xtrace -o nounset -o pipefail -o errexit

go get github.com/GRbit/go-pcre
go build -buildmode=pie -trimpath -o=${PREFIX}/bin/${PKG_NAME} -ldflags="-s -w"
go-licenses save . --save_path=license-files
