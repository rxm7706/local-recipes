#!/usr/bin/env bash

set -o xtrace -o nounset -o pipefail -o errexit

# Pack the package and install it globally into the conda prefix.
# `npm install --global` creates the bin shims for us.
npm pack --ignore-scripts
npm install -ddd \
    --global \
    --build-from-source \
    ${SRC_DIR}/gouvfr-lasuite-integration-1.0.3.tgz

# Windows .cmd wrappers (the noarch build runs on Linux but the
# package needs to be usable on Windows once installed).
