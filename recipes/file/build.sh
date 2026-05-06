#!/usr/bin/env bash
set -euxo pipefail

# Refresh config.sub / config.guess from gnuconfig (covers newer arches like aarch64)
cp "$BUILD_PREFIX/share/gnuconfig/config."* .

if [[ "${CONDA_BUILD_CROSS_COMPILATION:-0}" == "1" ]]; then
    # When cross-compiling, build a host-native `file` first so it can compile
    # the magic database, then re-run configure for the target.
    CC="${CC_FOR_BUILD}" CFLAGS="${CFLAGS_FOR_BUILD}" ./configure \
        --build="${BUILD}" \
        --host="${BUILD}" \
        --prefix="${BUILD_PREFIX}" \
        --datadir="${BUILD_PREFIX}/share" \
        --disable-silent-rules \
        --disable-dependency-tracking
    make "-j${CPU_COUNT}"
    make install
    make clean
fi

./configure \
    --prefix="${PREFIX}" \
    --datadir="${PREFIX}/share" \
    --disable-silent-rules \
    --disable-dependency-tracking

make "-j${CPU_COUNT}"

if [[ "${CONDA_BUILD_CROSS_COMPILATION:-0}" != "1" ]]; then
    make check
fi

make install
