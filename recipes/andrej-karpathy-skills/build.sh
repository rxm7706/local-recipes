#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "skills" ]; then
    echo "ERROR: skills/ directory not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/andrej-karpathy-skills"
mkdir -p "${SHARE}"
cp -r skills "${SHARE}/"
cp -r .claude-plugin "${SHARE}/"
cp CLAUDE.md CURSOR.md EXAMPLES.md README.md "${SHARE}/"

# Upstream does not ship a LICENSE file (plugin.json + README declare MIT).
# Use the MIT LICENSE vendored alongside this recipe.
cp "${RECIPE_DIR}/LICENSE" "${SHARE}/"

# Cross-platform Python entry point
mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/andrej_karpathy_skills_install.py" "${PREFIX}/bin/andrej-karpathy-skills-install"
chmod +x "${PREFIX}/bin/andrej-karpathy-skills-install"
