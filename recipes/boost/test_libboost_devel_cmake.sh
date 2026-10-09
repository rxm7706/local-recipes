#!/usr/bin/env bash
# libboost-devel output: per-lib CMake metadata presence (non-python libs).
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

for each_lib in "${boost_libs[@]}" "${boost_libs_static_only[@]}"; do
  test -d "$PREFIX/lib/cmake/boost_${each_lib}-${version}"
done

test ! -d "$PREFIX/lib/cmake/boost_python-${version}"
test ! -d "$PREFIX/lib/cmake/boost_numpy-${version}"
