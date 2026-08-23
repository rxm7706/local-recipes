"""The dispatch completion supervisor (Story 22.2, FR-193 CAP-2, AD-9/AD-33).

A separate OS process launched detached by ``cli/dispatch.py`` after a
successful ``marshal factory dispatch`` launch. Judges session
completion/failure from git facts plus running-process facts — never from
harness notifications, self-reports, or busy-wait polling in the dispatch
caller.

Entry point::

    python -m pyforge.marshal.dispatch_supervisor \\
        <repo_root> <slug> <run_id> <session_pid> <worktree_path> \\
        <story_key> <baseline_head_sha> <log_path>
"""

from __future__ import annotations
