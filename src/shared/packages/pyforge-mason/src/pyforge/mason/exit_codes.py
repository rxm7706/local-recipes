"""The sole exit-code owner (AD-7, FR-32).

`main()` in `cli.py` is the only place that turns an outcome into a process
exit code, and it does so exclusively by returning one of the five names
defined here. No other module under `pyforge.mason` may define a module-level
`EXIT_*` name -- enforced by `tests/meta/test_exit_code_ownership.py`, which
mirrors `test_dependency_direction.py`'s AST-based approach.

Per AD-1 (shared shapes, no behaviour), this module holds constants only.
"""

from __future__ import annotations

EXIT_OK = 0
"""The command completed successfully."""

EXIT_FAILED = 1
"""An anticipated `MasonError` was raised, or an unanticipated exception
escaped a command. Also the correction of the pre-Story-1.3 `EXIT_INTERNAL =
70` (EX_SOFTWARE), which contradicted AD-7/FR-33's mandated `1`."""

EXIT_USAGE = 2
"""A usage error: a bare noun with no verb, or an argparse-rejected
invocation. Matches argparse's own convention."""

EXIT_CFE_UNAVAILABLE = 3
"""The CFE root could not be resolved for a CFE-dependent command. Defined
now; first produced by Story 1.7's degradation handling."""

EXIT_INTERRUPTED = 130
"""128 + SIGINT, the shell convention for a keyboard interrupt."""
