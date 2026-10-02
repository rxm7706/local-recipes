"""``CommittingVcs`` -- the one name that is both the read/ref ``VcsPort`` and
the commit-writing, egress ``CommitPort`` (Story 82.9, DW-FU-2-6-4).

``GitVcs`` serves both ports, as ``LocalFs`` serves ``FsPort`` and
``RecordPort``. A caller that commits AND reads (``marshal deploy promote``,
the dispatch landing, the supervisor's durability watcher) keeps ONE ``vcs``
parameter annotated with this Protocol rather than threading a second
parameter through some 25 signatures and every test that passes a fake
positionally.

It lives here, outside ``ports/``, on purpose: ``tests/meta/test_ad34_egress_
registry_completeness.py`` scans every Protocol defined under ``ports/`` and
requires a registry entry for each, and a composed class there would need its
own entry and would hide ``VcsPort``'s ``str`` parameters behind an imported
base. Composed here, ``VcsPort`` stays the non-egress port it is and
``CommitPort`` the egress one -- the composition adds no method of its own.
"""

from __future__ import annotations

from typing import Protocol

from ..ports.commit import CommitPort
from ..ports.vcs import VcsPort


class CommittingVcs(VcsPort, CommitPort, Protocol):
    """A VCS adapter that both reads/ref-operates (``VcsPort``) and writes
    commits (``CommitPort``). No method of its own."""
