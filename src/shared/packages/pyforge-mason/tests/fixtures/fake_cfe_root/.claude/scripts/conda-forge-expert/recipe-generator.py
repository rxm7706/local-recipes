#!/usr/bin/env python3
"""Fake CFE root stub -- `recipe-generator.py` (Story 2.4, AD-16).

The canned body is a plain progress-style stdout line, not JSON -- the real
`generate_recipe` adapter's own docstring notes the wrapped script has no
`--json` mode, so `CfeResult.json_body` is always `None` for this adapter
regardless of what this stub prints. Sibling-imports `_stub_support` via
`Path(__file__).parent` (this fixture's own convention, not the real
wrapper's subprocess-delegation one). Invocable as
`[interpreter, script, *extra_argv]`; extra argv (`source`, `package`,
`--output`, `<path>`) is ignored, never rejected -- matching
`validate_recipe.py`/`submit_pr.py`'s identical convention above.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _stub_support  # noqa: E402

if __name__ == "__main__":
    sys.exit(_stub_support.emit("Fetching info for demo...\nGenerated: recipes/demo/recipe.yaml\n"))
