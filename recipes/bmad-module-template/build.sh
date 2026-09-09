#!/usr/bin/env bash
set -euxo pipefail

if [ ! -f "README.md" ]; then
    echo "ERROR: README.md not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/bmad-module-template"
mkdir -p "${SHARE}"
# Ship the full template tree. skills/ may be empty save for .gitkeep until
# upstream populates skills/my-skill/.
cp -r .claude-plugin skills docs "${SHARE}/"
cp README.md LICENSE "${SHARE}/"

# Cross-platform Python entry point that copies the template tree elsewhere.
mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/bmad_module_template_init.py" "${PREFIX}/bin/bmad-module-template-init"
chmod +x "${PREFIX}/bin/bmad-module-template-init"

# Windows entry point, emitted from this SAME noarch build (CFE G116). A .bat is
# just text, so ONE artifact serves every platform -- no __unix/__win split and
# no second build. %~dp0 resolves at RUNTIME to <prefix>\Scripts\, so nothing
# bakes a build-time prefix into the package (the old build.bat baked %PREFIX%,
# which cannot be right for a noarch artifact built on another platform).
mkdir -p "${PREFIX}/Scripts"
cp "${RECIPE_DIR}/bmad_module_template_init.py" "${PREFIX}/Scripts/bmad-module-template-init-script.py"
printf '@"%%~dp0..\\python.exe" "%%~dp0bmad-module-template-init-script.py" %%*\r\n' \
    > "${PREFIX}/Scripts/bmad-module-template-init.bat"

