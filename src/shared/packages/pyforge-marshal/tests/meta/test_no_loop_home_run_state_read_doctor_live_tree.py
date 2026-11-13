"""Story 33.12 CAP-4, the live-tree half (Story 115.1): Doctor's marshal source keeps its
loop-home fallback tagged.

It reads ``pyforge-doctor``'s source from the checkout beside this package, so it is marked
``live_tree`` and fails, never skips, when that file is absent. The package half,
``test_no_loop_home_run_state_read.py``, owns the rule this module applies.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_no_loop_home_run_state_read import _scan_file

pytestmark = pytest.mark.live_tree

_MARSHAL_PACKAGE_RELPATH = Path("src/shared/packages/pyforge-marshal")
_DOCTOR_MARSHAL_RELPATH = Path("src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py")


def _checkout_root() -> Path:
    """The source checkout this test file sits in: the nearest ancestor carrying this package."""
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / _MARSHAL_PACKAGE_RELPATH).is_dir():
            return ancestor
    pytest.fail(f"{__file__} is not inside a source checkout of {_MARSHAL_PACKAGE_RELPATH}")


def test_doctor_marshal_story_status_fallback_is_tagged() -> None:
    doctor_marshal = _checkout_root() / _DOCTOR_MARSHAL_RELPATH
    assert doctor_marshal.is_file(), f"the live tree has no {_DOCTOR_MARSHAL_RELPATH}"

    offenders = _scan_file(doctor_marshal)

    assert offenders == []
