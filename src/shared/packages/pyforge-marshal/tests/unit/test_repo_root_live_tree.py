"""Story 82.1 AC5: under the editable source layout ``cli/config.py::repo_root()`` keeps today's root.

Story 116.2 (spec-pyforge-marshal:CAP-305): the one ``test_repo_root.py`` test that resolves the real repository
(the root the editable install sits in, and the package tree under it) moved here, marked ``live_tree``. Every other
repo-root test builds its layout under ``tmp_path`` and stays in ``test_repo_root.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.cli import config as config_module
from pyforge.marshal.cli.config import repo_root

pytestmark = pytest.mark.live_tree


def test_the_editable_layout_returns_the_same_root_as_the_bare_index():
    root = repo_root()

    assert root == Path(config_module.__file__).resolve().parents[8]
    assert (root / "src" / "shared" / "packages" / "pyforge-marshal").is_dir()
