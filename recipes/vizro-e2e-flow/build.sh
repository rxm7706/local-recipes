#!/usr/bin/env bash
set -euxo pipefail

PKG_ROOT="vizro-e2e-flow"
if [ ! -d "${PKG_ROOT}/skills" ]; then
    echo "ERROR: ${PKG_ROOT}/skills/ not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/vizro-e2e-flow"
mkdir -p "${SHARE}"
cp -r "${PKG_ROOT}/skills" "${SHARE}/"
cp -r "${PKG_ROOT}/.claude-plugin" "${SHARE}/"
cp "${PKG_ROOT}/README.md" "${SHARE}/"
cp "${PKG_ROOT}/LICENSE.txt" "${SHARE}/"
# Skip cursor-import-skills.gif (~8.5 MB) and evals/ tutorial data.

mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/vizro_e2e_flow_install.py" "${PREFIX}/bin/vizro-e2e-flow-install"
chmod +x "${PREFIX}/bin/vizro-e2e-flow-install"
