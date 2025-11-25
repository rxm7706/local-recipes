#!/bin/bash
set -ex

# Set npm prefix to install globally into the conda environment
export npm_config_prefix="${PREFIX}"

# Use a non-existent config file to avoid user-level npm config
export NPM_CONFIG_USERCONFIG=/tmp/nonexistentrc

# Pack the source (we're already in the extracted tarball)
npm pack

# Install globally with dependencies
# npm pack creates pimzino-spec-workflow-mcp-VERSION.tgz for scoped packages
npm install -g pimzino-${PKG_NAME}-${PKG_VERSION}.tgz
