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

# DELIBERATE DIVERGENCE from rxm7706/local-recipes (2026-09-09): upstream's
# skills/ is empty in the release archive, and conda packages do not record
# empty directories -- so share/bmad-module-template/skills/ did not exist in
# the installed package and the recipe's own `test -d .../skills` assertion
# failed. A scaffold template should hand the user a skills/ directory to fill
# in, so keeping the directory is the intent-preserving fix; dropping the
# assertion would have hidden the problem.
#
# NOTE: a `.gitkeep` does NOT work here -- rattler-build's packaging walk drops
# it while shipping every other file in the same tree (verified in CI). Use a
# normal, non-hidden file. It doubles as the instructions the scaffolded module
# author needs, so it earns its place rather than being dead weight.
# Re-mirror and delete this block once upstream populates skills/my-skill/.
mkdir -p "${SHARE}/skills"
cat > "${SHARE}/skills/README.md" <<'SKILLS_README'
# Skills

Add one directory per skill here, e.g. `my-skill/`, each with its own
`SKILL.md`. This file exists so the directory ships in the conda package --
conda records files, not directories, so an empty `skills/` would vanish on
install. Delete it once you have added a real skill.
SKILLS_README

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

