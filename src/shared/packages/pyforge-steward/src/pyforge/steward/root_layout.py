"""This checkout's layout and repository identity, named once (Story 123.2, spec-pyforge-steward:CAP-182).

The one steward module that states where station packages live in this checkout and which
repository this estate is. Every other steward module derives from it, and
``tests/meta/test_portability.py`` reds a second module that names either one, so someone
moving steward to another tree changes this file alone. Two modules, ``five_tier.py`` and
``preflight_suite_reduction.py``, still spell the station-packages directory out segment by
segment; the test names them under DW-steward-123-2-2 and reds once either no longer does.

The four identity constants are estate-bound: they name this checkout, not the root of record,
and none of them follows a flip of ``pyforge.cutover_root`` (operator ruling 2026-11-10 on
question 5). ``steward ci`` reads the pause variables of the repository whose workflows it lists,
``steward bootstrap --url`` clones a checkout that must hold ``scripts/bmad-loop-worktree``, and the
public marketplace is published from ``docs/foundry/marketplace`` here. No module reads
``pyforge.cutover_root`` for them. The flag tree's relative path is not restated here: it is
``pyforge.core.cutover_root.LOCAL_DEV_RELATIVE``.

Assignments only: no function, and no import of a steward module, so any steward module may
import this one without forming a cycle (the portability test asserts both).
"""

from __future__ import annotations

from pathlib import Path

#: Where every station package lives in this checkout, relative to the repository root.
STATION_PACKAGES = "src/shared/packages"
STATION_PACKAGES_DIR = Path(STATION_PACKAGES)
#: Steward's own package directory; its data directories (catalog, corridor, measures) sit under it.
STEWARD_PACKAGE_DIR = STATION_PACKAGES_DIR / "pyforge-steward"
#: Marshal's package directory, where the bmad-loop pin fan-out of ``steward upgrade`` reads and writes.
MARSHAL_PACKAGE_DIR = STATION_PACKAGES_DIR / "pyforge-marshal"

#: ``steward ci``'s default ``--repo``: the repository whose workflows and pause variables it reads.
CI_DEFAULT_REPOSITORY = "rxm7706/local-recipes"
#: ``steward bootstrap``'s default ``--url``: the clone ``setup`` makes holds ``scripts/bmad-loop-worktree``.
BOOTSTRAP_DEFAULT_URL = "https://github.com/rxm7706/local-recipes.git"
#: The public marketplace's git clone URL (published from ``docs/foundry/marketplace`` in this checkout).
MARKETPLACE_GIT_URL = "https://github.com/rxm7706/local-recipes.git"
#: The owner name the rendered ``marketplace.json`` names.
MARKETPLACE_OWNER = "rxm7706"
