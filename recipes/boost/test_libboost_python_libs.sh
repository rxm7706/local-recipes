#!/usr/bin/env bash
# libboost-python output: python/numpy shared libs only.
set -euo pipefail

py_suffix="$(python -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')"
for each_lib in "python${py_suffix}" "numpy${py_suffix}"; do
  test -f "$PREFIX/lib/libboost_${each_lib}.so"
  test ! -f "$PREFIX/lib/libboost_${each_lib}.a"
done

test ! -d "$PREFIX/include/boost"
test ! -d "$PREFIX/lib/cmake/boost_python-${PKG_VERSION}"
test ! -d "$PREFIX/lib/cmake/boost_numpy-${PKG_VERSION}"
