#!/usr/bin/env bash
# Conda wrapper: official launcher expects LIQUIBASE_HOME = distro root,
# not dirname($PREFIX/bin/liquibase).
set -euo pipefail
export LIQUIBASE_HOME="${CONDA_PREFIX}/share/liquibase"
if [[ ! -x "${LIQUIBASE_HOME}/liquibase" ]]; then
    echo "Error: Liquibase launcher not found at ${LIQUIBASE_HOME}/liquibase" >&2
    exit 1
fi
exec "${LIQUIBASE_HOME}/liquibase" "$@"
