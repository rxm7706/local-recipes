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

# Windows entry point, emitted from this SAME noarch build (CFE G116). A .bat is
# just text, so ONE artifact serves every platform -- no __unix/__win split and
# no second build. %~dp0 resolves at RUNTIME to <prefix>\Scripts\, so nothing
# bakes a build-time prefix into the package (the old build.bat baked %PREFIX%,
# which cannot be right for a noarch artifact built on another platform).
mkdir -p "${PREFIX}/Scripts"
cp "${RECIPE_DIR}/bmad_manticore_install.py" "${PREFIX}/Scripts/bmad-manticore-install-script.py"
printf '@"%%~dp0..\\python.exe" "%%~dp0bmad-manticore-install-script.py" %%*\r\n' \
    > "${PREFIX}/Scripts/bmad-manticore-install.bat"

