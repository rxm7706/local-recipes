#!/usr/bin/env bash
set -euxo pipefail

# GitHub commit archives unpack to gitgres-<full-sha>/ under SRC_DIR.
ROOT="${SRC_DIR}"
if compgen -G "${SRC_DIR}/gitgres-"* >/dev/null; then
    ROOT="$(find "${SRC_DIR}" -maxdepth 1 -type d -name 'gitgres-*' | head -1)"
fi
cd "${ROOT}"

export PKG_CONFIG_PATH="${PREFIX}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
PG_CONFIG="${PREFIX}/bin/pg_config"

make -C ext PG_CONFIG="${PG_CONFIG}" clean || true
make -C ext PG_CONFIG="${PG_CONFIG}"
make -C ext PG_CONFIG="${PG_CONFIG}" install

make -C backend clean || true
make -C backend CC="${CC}" PG_CONFIG="${PG_CONFIG}"
install -d "${PREFIX}/bin"
install -m 0755 backend/gitgres-backend backend/git-remote-gitgres "${PREFIX}/bin/"
