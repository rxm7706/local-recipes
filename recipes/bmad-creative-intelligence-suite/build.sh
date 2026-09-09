#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "src" ]; then
    echo "ERROR: src/ directory not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/bmad-creative-intelligence-suite"
mkdir -p "${SHARE}"
cp -r src/skills "${SHARE}/"
cp src/module-help.csv src/module.yaml "${SHARE}/"
cp CHANGELOG.md LICENSE README.md "${SHARE}/"

mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/bmad_cis_install.py" "${PREFIX}/bin/bmad-cis-install"
chmod +x "${PREFIX}/bin/bmad-cis-install"

# Windows entry point, emitted from this SAME noarch build (CFE G116). A .bat is
# just text, so ONE artifact serves every platform -- no __unix/__win split and
# no second build. %~dp0 resolves at RUNTIME to <prefix>\Scripts\, so nothing
# bakes a build-time prefix into the package (the old build.bat baked %PREFIX%,
# which cannot be right for a noarch artifact built on another platform).
mkdir -p "${PREFIX}/Scripts"
cp "${RECIPE_DIR}/bmad_cis_install.py" "${PREFIX}/Scripts/bmad-cis-install-script.py"
printf '@"%%~dp0..\\python.exe" "%%~dp0bmad-cis-install-script.py" %%*\r\n' \
    > "${PREFIX}/Scripts/bmad-cis-install.bat"

