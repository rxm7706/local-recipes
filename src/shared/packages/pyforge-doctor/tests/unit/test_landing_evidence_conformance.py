"""Doctor-side landing-evidence grammar conformance (Story 20.8, CAP-1).

Imports ``pyforge.core.landing_evidence`` only -- never ``pyforge.marshal``
(classifier-independence rule). Re-runs the shared conformance matrix so
doctor and marshal prove they classify the same shapes before Story 20.9
wires ``sources/marshal.py``.
"""

from __future__ import annotations

import sys

import pytest
from pyforge.core.landing_evidence import (
    classify_branch_name,
    classify_commit,
    classify_merge_subject,
    conformance_fixtures,
)


def test_conformance_surface_imports_only_pyforge_core() -> None:
    """This module's import graph must not pull in ``pyforge.marshal``."""
    before = {name for name in sys.modules if name.startswith("pyforge.")}
    from pyforge.core import landing_evidence as _le  # noqa: F401

    after = {name for name in sys.modules if name.startswith("pyforge.")}
    new_marshal = {name for name in (after - before) if name.startswith("pyforge.marshal")}
    assert not new_marshal, f"unexpected pyforge.marshal import: {sorted(new_marshal)}"
    assert _le.RECOVERY_LANDING_CONVENTION


@pytest.mark.parametrize("fixture", conformance_fixtures(), ids=lambda f: str(f["label"]))
def test_doctor_conformance_matrix(fixture: dict[str, object]) -> None:
    project_slug = str(fixture["project_slug"])
    template = str(fixture["template"])
    expected_key = fixture["expected_key"]
    expected_shape = fixture["expected_shape"]

    if "commit_sha" in fixture:
        match = classify_commit(
            str(fixture["commit_sha"]),
            str(fixture.get("subject", "")),
            template=template,
            project_slug=project_slug,
        )
    elif "subject" in fixture:
        match = classify_merge_subject(
            str(fixture["subject"]),
            template=template,
            project_slug=project_slug,
        )
    elif "branch" in fixture:
        match = classify_branch_name(str(fixture["branch"]), project_slug=project_slug)
    else:
        pytest.fail(f"fixture {fixture['label']} has no subject, branch, or commit_sha")

    assert match is not None
    assert match.key == expected_key
    assert match.shape == expected_shape
