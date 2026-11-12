"""Move ``cli/config.py``'s checkout anchor to a made-up module file, leaving ``config.__file__`` alone (Story 116.4,
spec-pyforge-marshal:CAP-305).

``test_repo_root.py`` and ``test_checkout_root.py`` build each layout (a source checkout, an environment prefix, a
prefix too shallow to index) by moving the file ``_editable_checkout_root()`` anchors on. Rebinding the module's
``__file__`` would move it too, but coverage.py names a traced file by its frame's ``__file__``: every ``config.py``
line first run under the rebinding is filed under the made-up path, which does not exist, and drops out of the
report. ``anchor_config_at`` instead swaps the module's ``Path`` for a subclass that reads the real ``__file__`` as
the made-up one; every other path the module builds is unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.cli import config as config_module


def anchor_config_at(monkeypatch: pytest.MonkeyPatch, module_file: str | Path) -> None:
    """``Path(__file__)`` inside ``cli/config.py`` names ``module_file`` until ``monkeypatch`` undoes it."""
    real = config_module.__file__
    made_up = str(module_file)

    class _Anchored(Path):
        def __init__(self, *args: str | Path) -> None:
            super().__init__(*((made_up,) if args == (real,) else args))

    monkeypatch.setattr(config_module, "Path", _Anchored)
