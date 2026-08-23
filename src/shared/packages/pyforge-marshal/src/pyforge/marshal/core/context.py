"""``core/context.py`` (Story 5.6, FR-65/AD-50; Story 15.1, FR-133) --
``MarshalContext``, a plain, frozen value type carrying the facts
``cli/main.py``'s dispatch resolves ONCE per invocation and threads into a
handler as an available ``context=`` keyword. This module holds ONLY value
types and pure helpers (AD-4: no I/O, subprocess, clock, or adapter
imports anywhere under ``core/**`` -- checked by this package's own
import-linter contract, run via the ``lint-imports`` verification
command). The RESOLUTION function that actually gathers a slug's
policy/loop-home facts is impure and lives in ``cli/main.py`` instead,
via the SAME ``policy.compose``/``cli/init.py::_home_path`` primitives
every existing command already calls individually -- never a second,
independent resolution mechanism.

``cli/check.py`` (Story 5.6) is the first real consumer: it reads
``context.slug`` as its own primary source for the ``data["project"]``
field. ``factory spin``/``status``/``land`` (Story 3.3/5.1/4.8) receive a
resolved ``MarshalContext`` as an available, currently-UNUSED ``context=``
keyword at the dispatch boundary too -- their own internal policy/home-
path re-derivation is deliberately NOT retrofitted onto it in this pass
(see that story's own Design Notes).

Story 15.1 adds ``LOOP_BRANCH_PREFIX`` / ``slug_from_loop_branch``: the
ONE pure vocabulary for "this worktree branch names a fleet loop home,"
shared by ``cli/refresh.py`` with ``cli/status.py``/``cli/retire.py``'s
existing ``loop/`` filter -- never a second string literal for the same
convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .policy import EffectivePolicy

# Story 15.1 (FR-133): every fleet home is a worktree checked out on
# ``loop/<slug>``. Same prefix ``cli/status.py``/``cli/retire.py`` already
# filter on -- centralized here so refresh cannot drift.
LOOP_BRANCH_PREFIX = "loop/"


def slug_from_loop_branch(branch: str | None) -> str | None:
    """Return the project slug if ``branch`` is a fleet loop-home branch
    (``loop/<slug>``), else ``None``. Pure -- no filesystem touch."""
    if branch is None or not branch.startswith(LOOP_BRANCH_PREFIX):
        return None
    slug = branch.removeprefix(LOOP_BRANCH_PREFIX)
    return slug or None


@dataclass(frozen=True)
class MarshalContext:
    """One resolved invocation's own project facts.

    ``slug`` -- the resolved project slug (``--project``, when present on
    the invocation). ``loop_home`` -- that project's conventional loop-home
    path (``cli/init.py::_home_path``'s own convention), or ``None`` when
    the slug is missing/malformed. ``policy`` -- the composed
    ``EffectivePolicy`` for ``slug`` (``core.policy.compose``, the SAME
    call every existing command already makes individually). ``story`` --
    an optional per-invocation story key, when the command names one;
    ``None`` otherwise.
    """

    slug: str
    loop_home: Path | None
    policy: EffectivePolicy
    story: str | None
