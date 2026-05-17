#!/usr/bin/env bash

set -o xtrace -o nounset -o pipefail -o errexit

# Pack the package and install it globally into the conda prefix.
# `npm install --global` creates the bin shims for us.
npm pack --ignore-scripts
npm install -ddd \
    --global \
    --build-from-source \
    "${SRC_DIR}/generator-code-${PKG_VERSION}.tgz"

# npm creates symlinks under each transitive dep's node_modules/.bin/
# (ejs, jake, semver, yosay, …). rattler-build's noarch validator
# rejects these as non-portable on Windows. generator-code never invokes
# them at runtime — Yeoman generators are loaded via the top-level `yo`
# shim — so the safe fix is to drop them after install.
find "${PREFIX}/lib/node_modules/generator-code" -type d -name .bin -exec rm -rf {} +

# Generate the third-party license disclaimer (required by conda-forge
# for npm packages with runtime dependencies — declared in
# `about.license_file`).
pnpm install
pnpm-licenses generate-disclaimer --prod --output-file=third-party-licenses.txt

# Windows .cmd wrappers (the noarch build runs on Linux but the
# package needs to be usable on Windows once installed).
