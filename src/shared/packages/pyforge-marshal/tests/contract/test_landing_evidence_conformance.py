"""Marshal-side landing-evidence grammar conformance (Story 20.8 / 20.10).

Re-runs the shared ``conformance_fixtures()`` matrix from ``pyforge.core``
after ``core/promotion.py`` wires consumers to the grammar (CAP-3).
"""

from __future__ import annotations

import pytest
from pyforge.core.landing_evidence import (
    classify_branch_name,
    classify_commit,
    classify_merge_subject,
    conformance_fixtures,
)


@pytest.mark.parametrize("fixture", conformance_fixtures(), ids=lambda f: str(f["label"]))
def test_marshal_conformance_matrix(fixture: dict[str, object]) -> None:
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
