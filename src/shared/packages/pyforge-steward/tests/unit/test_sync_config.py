"""`load_config` — Epic 8, Story 8.1. Happy path, missing file, malformed
YAML, and missing/malformed-required-field errors."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.steward.sync import SyncConfig, SyncConfigError, load_config

_VALID_DOCUMENT = """\
github:
  project_id: PVT_abc123
  status_field_id: PVTF_status
  link_field_id: PVTF_link
  baseline_field_id: PVTF_baseline
jira:
  base_url: https://example.atlassian.net
  project_key: PROJ
  link_field_id: customfield_10001
  baseline_field_id: customfield_10002
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "sync-config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_happy_path_loads_a_fully_populated_config(tmp_path):
    path = _write(tmp_path, _VALID_DOCUMENT)

    config = load_config(path)

    assert isinstance(config, SyncConfig)
    assert config.github_project_id == "PVT_abc123"
    assert config.github_status_field_id == "PVTF_status"
    assert config.github_link_field_id == "PVTF_link"
    assert config.github_baseline_field_id == "PVTF_baseline"
    assert config.jira_base_url == "https://example.atlassian.net"
    assert config.jira_project_key == "PROJ"
    assert config.jira_link_field_id == "customfield_10001"
    assert config.jira_baseline_field_id == "customfield_10002"
    assert config.field_overrides == {}
    assert config.user_mapping == {}
    assert config.status_mapping == {}


def test_happy_path_with_field_overrides_and_user_mapping(tmp_path):
    path = _write(
        tmp_path,
        _VALID_DOCUMENT
        + """\
field_overrides:
  status: jira
user_mapping:
  octocat: "5b10a2844c20165700ede21g"
""",
    )

    config = load_config(path)

    assert config.field_overrides == {"status": "jira"}
    assert config.user_mapping == {"octocat": "5b10a2844c20165700ede21g"}


def test_happy_path_with_status_mapping(tmp_path):
    path = _write(
        tmp_path,
        _VALID_DOCUMENT
        + """\
status_mapping:
  Closed: Done
  In Progress: In Progress
""",
    )

    config = load_config(path)

    assert config.status_mapping == {"Closed": "Done", "In Progress": "In Progress"}


def test_missing_file_raises_sync_config_error(tmp_path):
    missing = tmp_path / "does-not-exist.yaml"

    with pytest.raises(SyncConfigError, match="not found"):
        load_config(missing)


def test_malformed_yaml_raises_sync_config_error(tmp_path):
    path = _write(tmp_path, "github: [unterminated\n  - broken")

    with pytest.raises(SyncConfigError, match="malformed YAML"):
        load_config(path)


def test_top_level_document_must_be_a_mapping(tmp_path):
    path = _write(tmp_path, "- just\n- a\n- list\n")

    with pytest.raises(SyncConfigError, match="must be a mapping"):
        load_config(path)


def test_missing_github_section_raises(tmp_path):
    path = _write(
        tmp_path,
        """\
jira:
  base_url: https://example.atlassian.net
  project_key: PROJ
  link_field_id: customfield_10001
  baseline_field_id: customfield_10002
""",
    )

    with pytest.raises(SyncConfigError, match="github"):
        load_config(path)


def test_missing_required_github_field_raises(tmp_path):
    path = _write(
        tmp_path,
        """\
github:
  project_id: PVT_abc123
  status_field_id: PVTF_status
  link_field_id: PVTF_link
jira:
  base_url: https://example.atlassian.net
  project_key: PROJ
  link_field_id: customfield_10001
  baseline_field_id: customfield_10002
""",
    )

    with pytest.raises(SyncConfigError, match="baseline_field_id"):
        load_config(path)


def test_empty_string_required_field_is_rejected(tmp_path):
    """A present-but-empty required field must not silently pass a
    presence-only check."""
    path = _write(
        tmp_path,
        """\
github:
  project_id: ""
  status_field_id: PVTF_status
  link_field_id: PVTF_link
  baseline_field_id: PVTF_baseline
jira:
  base_url: https://example.atlassian.net
  project_key: PROJ
  link_field_id: customfield_10001
  baseline_field_id: customfield_10002
""",
    )

    with pytest.raises(SyncConfigError, match="project_id"):
        load_config(path)


def test_field_overrides_must_be_a_mapping(tmp_path):
    path = _write(tmp_path, _VALID_DOCUMENT + "field_overrides: not-a-mapping\n")

    with pytest.raises(SyncConfigError, match="field_overrides"):
        load_config(path)


def test_field_overrides_rejects_an_unrecognized_authority(tmp_path):
    """A typo'd authority (anything but the literal 'jira') must fail loud
    rather than silently reverting to default (GitHub-wins) authority."""
    path = _write(tmp_path, _VALID_DOCUMENT + "field_overrides:\n  status: jrai\n")

    with pytest.raises(SyncConfigError, match="not a recognized authority"):
        load_config(path)


def test_field_overrides_rejects_github_as_redundant(tmp_path):
    path = _write(tmp_path, _VALID_DOCUMENT + "field_overrides:\n  status: github\n")

    with pytest.raises(SyncConfigError, match="not a recognized authority"):
        load_config(path)


def test_field_overrides_rejects_an_unrecognized_field_name(tmp_path):
    """A typo'd field NAME (e.g. 'statuz' for 'status') must fail loud too
    -- only the authority VALUE was validated before this test, letting an
    unrecognized key load successfully and be silently ignored."""
    path = _write(tmp_path, _VALID_DOCUMENT + "field_overrides:\n  statuz: jira\n")

    with pytest.raises(SyncConfigError, match="not a recognized field"):
        load_config(path)


def test_user_mapping_must_be_a_mapping(tmp_path):
    path = _write(tmp_path, _VALID_DOCUMENT + "user_mapping: not-a-mapping\n")

    with pytest.raises(SyncConfigError, match="user_mapping"):
        load_config(path)


def test_user_mapping_rejects_a_non_string_value(tmp_path):
    # Story 8.7: user_mapping is consulted now (assignee translation), so a
    # YAML authoring gotcha (an unquoted accountId parsing as a number/bool)
    # must fail loud at config-load time -- mirrors status_mapping's own
    # check (Story 8.6 precedent).
    path = _write(tmp_path, _VALID_DOCUMENT + "user_mapping:\n  octocat: 12345\n")

    with pytest.raises(SyncConfigError, match="user_mapping"):
        load_config(path)


def test_user_mapping_rejects_a_non_string_key(tmp_path):
    # YAML's `on`/`off`/`yes`/`no` parse to booleans -- a common authoring
    # gotcha for a GitHub login key too.
    path = _write(tmp_path, _VALID_DOCUMENT + 'user_mapping:\n  yes: "5b10a2844c20165700ede21g"\n')

    with pytest.raises(SyncConfigError, match="user_mapping"):
        load_config(path)


def test_user_mapping_rejects_a_null_value(tmp_path):
    path = _write(tmp_path, _VALID_DOCUMENT + "user_mapping:\n  octocat:\n")

    with pytest.raises(SyncConfigError, match="user_mapping"):
        load_config(path)


def test_user_mapping_rejects_duplicate_values(tmp_path):
    # Story 8.7 retro fix: two different github logins mapped to the same
    # jira accountId (a plausible copy-paste mistake) must fail loud at
    # config-load time -- the computed inverse ({v: k for k, v in
    # user_mapping.items()}) would otherwise silently collapse to whichever
    # entry iterates last, with no load-time warning.
    path = _write(
        tmp_path,
        _VALID_DOCUMENT
        + """\
user_mapping:
  octocat: "5b10a2844c20165700ede21g"
  hubot: "5b10a2844c20165700ede21g"
""",
    )

    with pytest.raises(SyncConfigError, match="duplicate"):
        load_config(path)


def test_user_mapping_rejects_an_empty_value(tmp_path):
    # Review pass 2: an empty translated value is FALSY, and
    # `update_github_assignees` skips whichever half of its add/remove pair
    # is falsy -- so an empty mapping value silently skips the POST while
    # the DELETE of the current assignee still runs, leaving the item
    # unassigned and recording "" as converged. A loud config error costs
    # nothing by comparison.
    path = _write(tmp_path, _VALID_DOCUMENT + 'user_mapping:\n  octocat: ""\n')

    with pytest.raises(SyncConfigError, match="non-empty"):
        load_config(path)


def test_user_mapping_rejects_an_empty_key(tmp_path):
    path = _write(tmp_path, _VALID_DOCUMENT + 'user_mapping:\n  "": "5b10a2844c20165700ede21g"\n')

    with pytest.raises(SyncConfigError, match="non-empty"):
        load_config(path)


def test_status_mapping_must_be_a_mapping(tmp_path):
    path = _write(tmp_path, _VALID_DOCUMENT + "status_mapping: not-a-mapping\n")

    with pytest.raises(SyncConfigError, match="status_mapping"):
        load_config(path)


def test_status_mapping_rejects_a_non_string_value(tmp_path):
    # YAML's `yes` parses to the boolean `True` -- a common authoring
    # gotcha that must fail loud at config-load time, never silently
    # forward a non-string value into a GitHub GraphQL write.
    path = _write(tmp_path, _VALID_DOCUMENT + "status_mapping:\n  Done: yes\n")

    with pytest.raises(SyncConfigError, match="status_mapping"):
        load_config(path)


def test_status_mapping_rejects_a_null_value(tmp_path):
    # `Done:` with nothing after the colon parses to `None` -- must be
    # rejected distinctly from "no entry for this key" (unmapped).
    path = _write(tmp_path, _VALID_DOCUMENT + "status_mapping:\n  Done:\n")

    with pytest.raises(SyncConfigError, match="status_mapping"):
        load_config(path)
