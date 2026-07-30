#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "skills" ]; then
    echo "ERROR: skills/ directory not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/bmad-manticore"
mkdir -p "${SHARE}"
cp -r skills "${SHARE}/"
cp -r .claude-plugin "${SHARE}/"
cp README.md "${SHARE}/"
cp LICENSE "${SHARE}/"

# Ship the text user guide only. docs/assets/ is ~11 MB of marketing media
# (banner JPEGs + an MP4) against 1.2 MB of skill content — excluded.
mkdir -p "${SHARE}/docs"
cp docs/user-guide.md "${SHARE}/docs/"

# Cross-platform Python entry point
mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/bmad_manticore_install.py" "${PREFIX}/bin/bmad-manticore-install"
chmod +x "${PREFIX}/bin/bmad-manticore-install"
