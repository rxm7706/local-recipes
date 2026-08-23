"""Doctor imports the shared testing kit (Story 19.2 consumer proof).

FR-130 / CAP-3: at least one station other than the seed source (Marshal)
imports from ``pyforge-testing-kit`` instead of a local duplicate.
"""

from __future__ import annotations

from pyforge.testing_kit import CliRunner, MockGitHubAPI, record_factory


def test_doctor_imports_cli_runner_from_shared_kit() -> None:
    runner = CliRunner("doctor-consumer")
    assert runner.run() is True
    assert runner.get_result()["story_id"] == "doctor-consumer"


def test_doctor_imports_auth_http_and_record_factory() -> None:
    api = MockGitHubAPI(owner="doctor", repo="consumer")
    pr = api.create_pull_request("kit import", head="feature")
    record = record_factory(code="DOC-KIT-001", message=pr["title"])
    assert record["code"] == "DOC-KIT-001"
    assert record["message"] == "kit import"
