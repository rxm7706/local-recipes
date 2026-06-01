#!/usr/bin/env bash

set -o xtrace -o nounset -o pipefail -o errexit

# Pack the package and install it globally into the conda prefix.
# `npm install --global` creates the bin shims for us.
npm pack --ignore-scripts
npm install -ddd \
    --global \
    --build-from-source \
    ${SRC_DIR}/socialgouv-e2esdk-client-1.0.0-beta.1.tgz

# Generate the third-party license disclaimer (required by conda-forge
# for npm packages with runtime dependencies — declared in
# `about.license_file`).
pnpm install
pnpm-licenses generate-disclaimer --prod --output-file=third-party-licenses.txt

# Windows .cmd wrappers (the noarch build runs on Linux but the
# package needs to be usable on Windows once installed).
