#!/usr/bin/env bash
# libboost-headers output: absence checks for all library artefacts.
set -euo pipefail

version="${PKG_VERSION:?}"

boost_libs=(
  atomic charconv chrono cobalt container context contract coroutine
  date_time filesystem graph iostreams locale log log_setup
  math_c99 math_c99f math_tr1 math_tr1f prg_exec_monitor
  program_options random regex serialization thread
  timer type_erasure unit_test_framework wave wserialization
  math_c99l math_tr1l
)
boost_libs_static_only=(exception test_exec_monitor)
py_suffix="$(python -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')"
boost_libs_py=("python${py_suffix}" "numpy${py_suffix}")

all_libs=("${boost_libs[@]}" "${boost_libs_static_only[@]}" "${boost_libs_py[@]}")

for each_lib in "${all_libs[@]}"; do
  test ! -f "$PREFIX/lib/libboost_${each_lib}.so"
  test ! -f "$PREFIX/lib/libboost_${each_lib}.a"
  test ! -d "$PREFIX/lib/cmake/boost_${each_lib}-${version}"
done
