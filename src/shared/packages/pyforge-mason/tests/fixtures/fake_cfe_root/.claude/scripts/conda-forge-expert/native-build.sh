#!/usr/bin/env bash
# Fake CFE root stub -- the native build script (Story 2.6, AD-16).
#
# Mirrors the Python stubs' MASON_FIXTURE_* convention (_stub_support.py)
# by hand, since a bash script cannot import that Python helper: always
# writes a fixed marker line to stderr first (proving cfe.py's build_native
# adapter streams stderr live via run_streamed, rather than buffering to
# completion), then MASON_FIXTURE_STDOUT (if set, else a canned default) to
# stdout, then exits MASON_FIXTURE_EXIT_CODE (if set, else 0).
#
# Invocable as [bash, script, recipe_path]; the recipe-path argument is
# accepted and never validated, matching the Python stubs' "extra argv is
# ignored, never rejected" convention. Run via `bash <path>`, never
# exec'd directly, so no executable bit is required.
set -uo pipefail

echo "native-build-stub: building ${1:-<none>}" >&2

if [[ -n "${MASON_FIXTURE_STDOUT+x}" ]]; then
  printf '%s\n' "${MASON_FIXTURE_STDOUT}"
else
  echo "native build stub ok"
fi

exit "${MASON_FIXTURE_EXIT_CODE:-0}"
