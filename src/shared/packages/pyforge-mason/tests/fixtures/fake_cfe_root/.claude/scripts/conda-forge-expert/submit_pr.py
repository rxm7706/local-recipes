#!/usr/bin/env python3
"""Fake CFE root stub -- `submit_pr.py` (Story 1.9, AD-16).

The canned body's keys (`success`/`recipe`/`branch`/`github_user`/`pr_url`/
`message`) match the real skill script's success-path payload shape
(`.claude/skills/conda-forge-expert/scripts/submit_pr.py`), including
`success` -- the key the real script's own exit-code logic
(`sys.exit(0 if result.get("success") else 1)`) depends on. Sibling-imports
`_stub_support` via `Path(__file__).parent` (this fixture's own convention,
not the real wrapper's subprocess-delegation one). Invocable as
`[interpreter, script, *extra_argv]`; extra argv is ignored, never rejected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _stub_support  # noqa: E402

if __name__ == "__main__":
    sys.exit(
        _stub_support.emit(
            '{"success": true, "recipe": "example-recipe", '
            '"branch": "add-example-recipe", "github_user": "example-user", '
            '"pr_url": "https://github.com/example/example/pull/1", '
            '"message": "PR created: https://github.com/example/example/pull/1"}'
        )
    )
