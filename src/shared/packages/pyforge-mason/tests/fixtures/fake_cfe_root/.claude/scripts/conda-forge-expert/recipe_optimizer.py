#!/usr/bin/env python3
"""Fake CFE root stub -- `recipe_optimizer.py` (Story 2.8, AD-16).

The canned body's keys (`success`/`suggestions_found`/`suggestions`, each
suggestion's `code`/`message`/`suggestion`/`confidence`) match the real
skill script's own output shape
(`.claude/skills/conda-forge-expert/scripts/recipe_optimizer.py::main`), not
an invented shape -- this is what "mirrors the real layout" is for. Unlike
`validate_recipe.py`/`failure_analyzer.py`, the real script takes no
`--json` flag (it always emits JSON), so this stub does not branch on one
either. Sibling-imports `_stub_support` via `Path(__file__).parent` (this
fixture's own convention, not the real wrapper's subprocess-delegation one).
Invocable as `[interpreter, script, *extra_argv]`; extra argv (including a
`recipe_path` positional) is ignored, never rejected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _stub_support  # noqa: E402

if __name__ == "__main__":
    sys.exit(
        _stub_support.emit(
            '{"success": true, "suggestions_found": 1, "suggestions": '
            '[{"code": "ABT-001", "message": "Missing \'license_file\' in about '
            'section.", "suggestion": "Add \'license_file: LICENSE\' (adjust '
            'filename to match the repo: LICENSE.md, LICENSE.txt, etc.).", '
            '"confidence": 0.95}]}',
            default_exit_code=1,
        )
    )
