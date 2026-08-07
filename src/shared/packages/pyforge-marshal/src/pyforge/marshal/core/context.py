"""``core/context.py`` (Story 5.6, FR-65/AD-50) -- ``MarshalContext``, a
plain, frozen value type carrying the facts ``cli/main.py``'s dispatch
resolves ONCE per invocation and threads into a handler as an available
``context=`` keyword. This module holds ONLY the value type (AD-4: no I/O,
subprocess, clock, or adapter imports anywhere under ``core/**`` -- checked
by this package's own import-linter contract, run via the
``lint-imports`` verification command). The RESOLUTION function that
actually gathers a slug's policy/loop-home facts is impure and lives in
``cli/main.py`` instead, via the SAME ``policy.compose``/
``cli/init.py::_home_path`` primitives every existing command already
calls individually -- never a second, independent resolution mechanism.

``cli/check.py`` (this story's own brand-new command) is the first real
consumer: it reads ``context.slug`` as its own primary source for the
``data["project"]`` field. ``factory spin``/``status``/``land`` (Story
3.3/5.1/4.8) receive a resolved ``MarshalContext`` as an available,
currently-UNUSED ``context=`` keyword at the dispatch boundary too -- their
own internal policy/home-path re-derivation is deliberately NOT
retrofitted onto it in this pass (see this story's own Design Notes: a
full retrofit of three large, already-hardened commands' internals is a
separately-risked undertaking this story's own scope narrowing defers).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .policy import EffectivePolicy


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
