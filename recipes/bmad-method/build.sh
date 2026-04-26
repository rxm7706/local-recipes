#!/bin/bash
set -euxo pipefail

# The GitHub archive extracts into BMAD-METHOD-<version>/; rattler-build sets
# SRC_DIR to that top-level directory, so package.json is directly in SRC_DIR.
if [ ! -f "package.json" ]; then
    echo "ERROR: package.json not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

# Install production npm dependencies (no devDependencies, no scripts)
npm install --omit=dev --no-fund --no-audit --ignore-scripts

# Create the installation directory
INSTALL_DIR="${PREFIX}/lib/node_modules/${PKG_NAME}"
mkdir -p "${INSTALL_DIR}"

# Copy all package files (source + node_modules), then remove dev-only directories
# that are present in the GitHub archive but excluded in .npmignore.
cp -r . "${INSTALL_DIR}/"
rm -rf "${INSTALL_DIR}/website" \
       "${INSTALL_DIR}/docs" \
       "${INSTALL_DIR}/test" \
       "${INSTALL_DIR}/.husky" \
       "${INSTALL_DIR}/.github" \
       "${INSTALL_DIR}/.vscode" \
       "${INSTALL_DIR}/.augment" \
       "${INSTALL_DIR}/.claude-plugin"

# Create bin directory
mkdir -p "${PREFIX}/bin"

# Create wrapper for the bmad command
cat > "${PREFIX}/bin/bmad" << 'WRAPPER'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "${SCRIPT_DIR}/../lib/node_modules/bmad-method/tools/installer/bmad-cli.js" "$@"
WRAPPER
chmod +x "${PREFIX}/bin/bmad"

# Create wrapper for the bmad-method command (same entry point)
cat > "${PREFIX}/bin/bmad-method" << 'WRAPPER'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "${SCRIPT_DIR}/../lib/node_modules/bmad-method/tools/installer/bmad-cli.js" "$@"
WRAPPER
chmod +x "${PREFIX}/bin/bmad-method"
