#!/bin/bash
# Platform host dependency install — pixi is the sole authority (steward Story 16.1 / CAP-5).
# The former `pip install -r requirements/local.txt` path is retired.

set -euo pipefail

echo >&2 "src/platform/utility/install_python_dependencies.sh: legacy pip/virtualenv install is retired."
echo >&2 "Install platform Python deps from the repo-root pixi.toml instead:"
echo >&2 "  pixi install -e platform-ci-test   # CI/test host parity (PyPI pins)"
echo >&2 "  pixi install -e platform-dev       # local host + engines (conda)"
echo >&2 "See src/platform/requirements/README.md."
exit 1
