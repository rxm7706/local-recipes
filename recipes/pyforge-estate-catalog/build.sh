#!/usr/bin/env bash
set -euxo pipefail

export PYTHONPATH="${SRC_DIR}/src/shared/packages/pyforge-steward/src:${PYTHONPATH:-}"
export CONDA_PREFIX="${PREFIX}"

python -m pyforge.steward.cli catalog ship --output "${SRC_DIR}/src/shared/packages/pyforge-steward/catalog/snapshot"

mkdir -p "${PREFIX}/share/pyforge-estate-catalog"
cp -a "${SRC_DIR}/src/shared/packages/pyforge-steward/catalog/snapshot/." "${PREFIX}/share/pyforge-estate-catalog/"

mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/pyforge_estate_catalog_install.py" "${PREFIX}/bin/pyforge-estate-catalog-install"
chmod +x "${PREFIX}/bin/pyforge-estate-catalog-install"

mkdir -p "${PREFIX}/Scripts"
cp "${RECIPE_DIR}/pyforge_estate_catalog_install.py" "${PREFIX}/Scripts/pyforge-estate-catalog-install-script.py"
printf '@"%~dp0..\\python.exe" "%~dp0pyforge-estate-catalog-install-script.py" %*\r\n' \
  > "${PREFIX}/Scripts/pyforge-estate-catalog-install.bat"
