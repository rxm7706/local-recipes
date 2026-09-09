#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "skills" ]; then
    echo "ERROR: skills/ directory not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/bmad-labs-skills"
mkdir -p "${SHARE}"
cp -r skills "${SHARE}/"
cp -r .claude-plugin "${SHARE}/"
cp README.md LICENSE "${SHARE}/"

# Cross-platform Python entry point
mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/bmad_labs_skills_install.py" "${PREFIX}/bin/bmad-labs-skills-install"
chmod +x "${PREFIX}/bin/bmad-labs-skills-install"

# Windows entry point, emitted from this SAME noarch build (CFE G116). A .bat is
# just text, so ONE artifact serves every platform -- no __unix/__win split and
# no second build. %~dp0 resolves at RUNTIME to <prefix>\Scripts\, so nothing
# bakes a build-time prefix into the package (the old build.bat baked %PREFIX%,
# which cannot be right for a noarch artifact built on another platform).
mkdir -p "${PREFIX}/Scripts"
cp "${RECIPE_DIR}/bmad_labs_skills_install.py" "${PREFIX}/Scripts/bmad-labs-skills-install-script.py"
printf '@"%%~dp0..\\python.exe" "%%~dp0bmad-labs-skills-install-script.py" %%*\r\n' \
    > "${PREFIX}/Scripts/bmad-labs-skills-install.bat"

