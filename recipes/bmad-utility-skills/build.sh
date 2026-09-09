#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "skills" ]; then
    echo "ERROR: skills/ directory not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/bmad-utility-skills"
mkdir -p "${SHARE}"
cp -r skills "${SHARE}/"
cp -r .claude-plugin "${SHARE}/"
cp README.md "${SHARE}/"

# Upstream does not yet ship a LICENSE file (tracked: hold submission).
# Use the MIT LICENSE vendored alongside this recipe.
cp "${RECIPE_DIR}/LICENSE" "${SHARE}/"

# Cross-platform Python entry point
mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/bmad_utility_skills_install.py" "${PREFIX}/bin/bmad-utility-skills-install"
chmod +x "${PREFIX}/bin/bmad-utility-skills-install"

# Windows entry point, emitted from this SAME noarch build (CFE G116). A .bat is
# just text, so ONE artifact serves every platform -- no __unix/__win split and
# no second build. %~dp0 resolves at RUNTIME to <prefix>\Scripts\, so nothing
# bakes a build-time prefix into the package (the old build.bat baked %PREFIX%,
# which cannot be right for a noarch artifact built on another platform).
mkdir -p "${PREFIX}/Scripts"
cp "${RECIPE_DIR}/bmad_utility_skills_install.py" "${PREFIX}/Scripts/bmad-utility-skills-install-script.py"
printf '@"%%~dp0..\\python.exe" "%%~dp0bmad-utility-skills-install-script.py" %%*\r\n' \
    > "${PREFIX}/Scripts/bmad-utility-skills-install.bat"

