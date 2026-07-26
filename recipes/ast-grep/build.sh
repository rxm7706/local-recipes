#!/usr/bin/env bash

set -o xtrace -o nounset -o pipefail -o errexit

export CARGO_PROFILE_RELEASE_STRIP=symbols
export CARGO_PROFILE_RELEASE_LTO=fat
export CFLAGS="${CFLAGS} -D_BSD_SOURCE"

cargo install --bins --no-track --verbose --locked --root ${PREFIX} --path ./crates/cli
cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
