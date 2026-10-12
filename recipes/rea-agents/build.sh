#!/bin/bash
set -euxo pipefail

export npm_config_prefix="${PREFIX}"
export NPM_CONFIG_USERCONFIG=/tmp/nonexistentrc

# Install the published tarball with its production dependency tree
# globally into the conda prefix.
npm pack
npm install -g --omit=dev "${PKG_NAME}-${PKG_VERSION}.tgz"

# Collect the license texts of every vendored node_module.
node "${RECIPE_DIR}/collect_licenses.mjs" \
  "${PREFIX}/lib/node_modules/${PKG_NAME}/node_modules" \
  > "${SRC_DIR}/third-party-licenses.txt"
