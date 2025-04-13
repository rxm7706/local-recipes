#!/usr/bin/env bash

set -o xtrace -o nounset -o pipefail -o errexit

# Run pnpm so that pnpm-licenses can create report
#pnpm install --prod
#pnpm licenses list --json | pnpm-licenses generate-disclaimer --json-input --output-file=ThirdPartyLicenses.txt
#pnpm pack

# Create package archive and install globally packages\duckdb-wasm
##PKG_NAME=duckdb-wasm
##PKG_VERSION={{ version }}

pushd packages
pushd duckdb-wasm

npm pack --ignore-scripts
npm install -ddd \
    --global \
    --build-from-source \
     ${SRC_DIR}/${PKG_NAME}-${PKG_VERSION}.tgz
