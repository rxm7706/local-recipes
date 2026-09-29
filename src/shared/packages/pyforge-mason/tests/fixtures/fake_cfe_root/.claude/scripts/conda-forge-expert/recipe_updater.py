#!/usr/bin/env python3
"""Fake CFE root stub -- `recipe_updater.py` (Story 2.10, AD-16).

The canned body's keys (`success`/`updated`/`new_version`/`message`) match
the real skill script's success-path payload shape
(`.claude/skills/conda-forge-expert/scripts/recipe_updater.py`), including
`success` -- the key the real script's own exit-code logic
(`sys.exit(0 if result["success"] else 1)`) depends on. Sibling-imports
`_stub_support` via `Path(__file__).parent` (this fixture's own convention,
not the real wrapper's subprocess-delegation one). Invocable as
`[interpreter, script, *extra_argv]`; extra argv (`--dry-run`, etc.) is
ignored, never rejected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _stub_support  # noqa: E402

if __name__ == "__main__":
    sys.exit(
        _stub_support.emit(
            '{"success": true, "updated": true, "new_version": "9.9.9", "message": "Recipe updated successfully."}'
        )
    )
