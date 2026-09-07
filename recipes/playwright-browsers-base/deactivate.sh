#!/bin/sh
# Unset PLAYWRIGHT_BROWSERS_PATH only if WE set it (see activate.sh), so an
# operator-supplied value survives deactivation untouched.
if [ -n "${PLAYWRIGHT_BROWSERS_PATH_SET_BY_CONDA:-}" ]; then
    unset PLAYWRIGHT_BROWSERS_PATH
    unset PLAYWRIGHT_BROWSERS_PATH_SET_BY_CONDA
fi
