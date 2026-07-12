#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "dist" ] || [ ! -d "core" ]; then
    echo "ERROR: dist/ or core/ not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/aidlc-workflows"
mkdir -p "${SHARE}"
cp -r dist core harness plugins docs "${SHARE}/"
cp README.md LICENSE CHANGELOG.md "${SHARE}/"

# Cross-platform Python entry point
mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/aidlc_workflows_install.py" "${PREFIX}/bin/aidlc-workflows-install"
chmod +x "${PREFIX}/bin/aidlc-workflows-install"
