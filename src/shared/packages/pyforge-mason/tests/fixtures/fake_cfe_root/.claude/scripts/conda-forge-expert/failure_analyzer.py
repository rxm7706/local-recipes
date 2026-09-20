#!/usr/bin/env python3
"""Fake CFE root stub -- `failure_analyzer.py` (Story 2.7, AD-16).

The canned body's keys (`success`/`match_count`/`error_class`/`category`/
`diagnosis`/`matched_text`/`suggestion`/`all_matches`) match the real skill
script's non-`--first-only` success-path payload shape
(`.claude/skills/conda-forge-expert/scripts/failure_analyzer.py::main`), not
an invented shape -- this is what "mirrors the real layout" is for. Mason's
own `diagnose_failure` adapter never passes `--first-only` (spec Never
boundary), so this stub only needs to mirror that one output shape.
Sibling-imports `_stub_support` via `Path(__file__).parent` (this fixture's
own convention, not the real wrapper's subprocess-delegation one). Invocable
as `[interpreter, script, *extra_argv]`; extra argv (including a `logfile`
positional) is ignored, never rejected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _stub_support  # noqa: E402

if __name__ == "__main__":
    sys.exit(
        _stub_support.emit(
            '{"success": true, "match_count": 1, '
            '"error_class": "MODULE_NOT_FOUND_AT_TEST", "category": "PYTHON", '
            '"diagnosis": "A Python module could not be imported during the test '
            "phase. Either the package was not installed correctly or a test "
            'dependency is missing.", '
            '"matched_text": "ModuleNotFoundError: No module named \'example_pkg\'", '
            '"suggestion": {"action": "add_to_list", '
            '"path": "tests[0].requirements.run", "value": "example_pkg", '
            '"comment": "Add the missing module\'s package to test run '
            "requirements, or verify the package installs all __init__.py "
            'files."}, '
            '"all_matches": [{"error_class": "MODULE_NOT_FOUND_AT_TEST", '
            '"category": "PYTHON", "diagnosis": "A Python module could not be '
            "imported during the test phase. Either the package was not "
            'installed correctly or a test dependency is missing.", '
            '"matched_text": "ModuleNotFoundError: No module named '
            '\'example_pkg\'", "suggestion": {"action": "add_to_list", '
            '"path": "tests[0].requirements.run", "value": "example_pkg", '
            '"comment": "Add the missing module\'s package to test run '
            "requirements, or verify the package installs all __init__.py "
            'files."}}]}'
        )
    )
