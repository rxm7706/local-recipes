#!/usr/bin/env bash
# libboost output: library artefact checks (mirrors meta.yaml jinja loop).
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

in_boost_libs() {
  local lib=$1
  local x
  for x in "${boost_libs[@]}"; do
    [[ "$x" == "$lib" ]] && return 0
  done
  return 1
}

in_static_only() {
  local lib=$1
  local x
  for x in "${boost_libs_static_only[@]}"; do
    [[ "$x" == "$lib" ]] && return 0
  done
  return 1
}

all_libs=("${boost_libs[@]}" "${boost_libs_static_only[@]}" "${boost_libs_py[@]}")

for each_lib in "${all_libs[@]}"; do
  if in_boost_libs "$each_lib"; then
    test -f "$PREFIX/lib/libboost_${each_lib}.so"
  else
    test ! -f "$PREFIX/lib/libboost_${each_lib}.so"
  fi

  if in_static_only "$each_lib"; then
    test -f "$PREFIX/lib/libboost_${each_lib}.a"
  else
    test ! -f "$PREFIX/lib/libboost_${each_lib}.a"
  fi

  test ! -d "$PREFIX/lib/cmake/boost_${each_lib}-${version}"
done

test ! -d "$PREFIX/include/boost"
test ! -d "$PREFIX/lib/cmake/Boost-${version}"
