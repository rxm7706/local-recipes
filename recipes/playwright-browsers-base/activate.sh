#!/bin/sh
# Point Playwright at the conda prefix instead of the machine-global
# ~/.cache/ms-playwright. Set by the playwright-browsers-base package.
#
# The :- defaults are load-bearing, not style: conda activation is sourced
# into whatever shell the caller has, and under `set -u` a bare ${VAR}
# reference to an unset variable aborts the shell.
#
# Only set when unset, so an operator who has deliberately exported their own
# PLAYWRIGHT_BROWSERS_PATH (a shared /opt/pw-browsers, a CI cache mount) keeps
# it. Their value wins; conda does not override an explicit choice.
if [ -z "${PLAYWRIGHT_BROWSERS_PATH:-}" ]; then
    PLAYWRIGHT_BROWSERS_PATH="${CONDA_PREFIX}/share/ms-playwright"
    export PLAYWRIGHT_BROWSERS_PATH
    PLAYWRIGHT_BROWSERS_PATH_SET_BY_CONDA=1
    export PLAYWRIGHT_BROWSERS_PATH_SET_BY_CONDA
fi
