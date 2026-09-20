#!/usr/bin/env python3
"""Fake CFE root stub -- `validate_recipe.py` (Story 1.9, AD-16).

The canned body's keys (`passed`/`errors`/`warnings`/`info`/
`rattler_lint_ran`) match the real skill script's `--json` output shape
(`.claude/skills/conda-forge-expert/scripts/validate_recipe.py::
print_result`), not an invented shape -- this is what "mirrors the real
layout" is for. Sibling-imports `_stub_support` via `Path(__file__).parent`
(this fixture's own convention, not the real wrapper's subprocess-delegation
one). Invocable as `[interpreter, script, *extra_argv]`; extra argv is
ignored, never rejected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _stub_support  # noqa: E402

if __name__ == "__main__":
    sys.exit(_stub_support.emit('{"passed": true, "errors": [], "warnings": [], "info": [], "rattler_lint_ran": true}'))
