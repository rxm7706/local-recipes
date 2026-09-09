#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "skills" ]; then
    echo "ERROR: skills/ directory not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

# Install skill files and Claude plugin config
mkdir -p "${PREFIX}/share/bmad-builder"
cp -r skills "${PREFIX}/share/bmad-builder/"
cp -r .claude-plugin "${PREFIX}/share/bmad-builder/"
cp CHANGELOG.md LICENSE README.md "${PREFIX}/share/bmad-builder/"

# Install cross-platform Python entry point
mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/bmad_builder_install.py" "${PREFIX}/bin/bmad-builder-install"
chmod +x "${PREFIX}/bin/bmad-builder-install"

# Windows entry point, emitted from this SAME noarch build (CFE G116). A .bat is
# just text, so ONE artifact serves every platform -- no __unix/__win split and
# no second build. %~dp0 resolves at RUNTIME to <prefix>\Scripts\, so nothing
# bakes a build-time prefix into the package (the old build.bat baked %PREFIX%,
# which cannot be right for a noarch artifact built on another platform).
mkdir -p "${PREFIX}/Scripts"
cp "${RECIPE_DIR}/bmad_builder_install.py" "${PREFIX}/Scripts/bmad-builder-install-script.py"
printf '@"%%~dp0..\\python.exe" "%%~dp0bmad-builder-install-script.py" %%*\r\n' \
    > "${PREFIX}/Scripts/bmad-builder-install.bat"

