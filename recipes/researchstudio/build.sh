#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "ResearchStudio-Idea/skills" ] || [ ! -d "ResearchStudio-Reel/skills" ]; then
    echo "ERROR: expected skill bundles not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/researchstudio"
mkdir -p "${SHARE}"

# Both bundles, preserving the upstream layout the skills' own relative paths
# assume. .env.template ships so users can copy + fill in connector creds.
cp -r ResearchStudio-Idea "${SHARE}/"
cp -r ResearchStudio-Reel "${SHARE}/"
cp -r docs "${SHARE}/"
cp LICENSE README.md "${SHARE}/"

# Upstream's install.sh / bin/install.mjs are deliberately NOT shipped: they
# symlink into a repo's .claude//.codex/ dirs and shell out to pip/apt/brew.
# The entry point below does the copy directly instead.
mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/researchstudio_install.py" "${PREFIX}/bin/researchstudio-install"
chmod +x "${PREFIX}/bin/researchstudio-install"
