"""The supervisor sidecar (Story 3.4, architecture spine AD-9/AD-20/AD-25):
a separate OS process, launched detached by ``cli/spin.py`` as the last
step of a successful ``marshal factory spin``, that observes a run from
outside and never trusts session self-report. See
``supervisor/__main__.py`` for the sidecar's actual entry point and its own
attach/heartbeat/detach journaling loop.

This package has no importable surface of its own beyond ``__main__.py`` --
there is no library API here to call, only a process to launch via
``python -m pyforge.marshal.supervisor``. That asymmetry is itself
structural (AD-9): a package with real functions to import invites a caller
to reach INTO the supervisor's own process from outside it; a package that
is only ever *launched* cannot be reached any other way. A new
``import-linter`` "forbidden" contract (``pyproject.toml``) forbids this
package from importing ``pyforge.marshal.cli`` in the other direction --
the session's own front door already has no way to call back into a
separate OS process's internals; this makes that absence structural too."""

from __future__ import annotations
