#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "skills" ]; then
    echo "ERROR: skills/ directory not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/superpowers"
mkdir -p "${SHARE}"
cp -r skills hooks .claude-plugin docs "${SHARE}/"
cp CLAUDE.md AGENTS.md README.md LICENSE "${SHARE}/"

# Cross-platform Python entry point
mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/superpowers_install.py" "${PREFIX}/bin/superpowers-install"
chmod +x "${PREFIX}/bin/superpowers-install"
