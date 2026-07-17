"""Unit tests — the ``--bypass``/``--reason`` CLI surface + committed
``.warden-waivers.yaml`` integration (Story 3.2, FR24-FR26).

A new sibling to ``test_discovery_extract_cli.py`` (already large) per the
story spec's Code Map. Mirrors that file's own conventions: real
``tmp_path`` fixtures, ``main()`` invoked end-to-end, JSON output
schema-validated via ``jsonschema``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from importlib import resources
from pathlib import Path

import jsonschema
import yaml

from pyforge.warden.cli import main
from pyforge.warden.report import TOOL_NAME

_FAR_FUTURE = "2099-01-01T00:00:00+00:00"
_LONG_AGO = "2000-01-01T00:00:00+00:00"
_RECENTLY_EXPIRED = "2000-06-01T00:00:00+00:00"


def write_pyproject(directory: Path, deps: list[str], *, extra: str = "") -> None:
    body = (
        "[project]\n"
        'name = "demo"\n'
        'version = "0.0.1"\n'
        f"dependencies = {json.dumps(deps)}\n"
        f"{extra}"
    )
    (directory / "pyproject.toml").write_text(body, encoding="utf-8")


def write_waiver_file(
    directory: Path,
    *,
    entry_id: str = "hygiene:DEP002:requests",
    accepted_at: str = _LONG_AGO,
    expires_at: str = _FAR_FUTURE,
    reason: str = "tracked in JIRA-1",
    authorized_by: str = "alice",
) -> None:
    body = (
        "version: 1\n"
        "waivers:\n"
        f"  - id: {entry_id!r}\n"
        f"    reason: {reason!r}\n"
        f"    authorized_by: {authorized_by!r}\n"
        f"    accepted_at: {accepted_at!r}\n"
        f"    expires_at: {expires_at!r}\n"
    )
    (directory / ".warden-waivers.yaml").write_text(body, encoding="utf-8")


def load_schema() -> dict:
    schema_file = resources.files("pyforge.warden") / "data" / "report-schema.json"
    return json.loads(schema_file.read_text(encoding="utf-8"))


def scan_json(capsys, target, extra_args: list[str] | None = None) -> tuple[int, dict, str]:
    capsys.readouterr()
    rc = main(["scan", str(target), "--format", "json", *(extra_args or [])])
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.Draft202012Validator(load_schema()).validate(document)
    return rc, document, captured.err


def _blocking_fixture(tmp_path: Path) -> None:
    """A hygiene DEP002 (unused-dependency) warn finding: the fixture
    every test in this file uses as its one "blocking" finding."""
    write_pyproject(tmp_path, ["requests==2.31.0"])
    (tmp_path / "main.py").write_text("", encoding="utf-8")


# --- --bypass requires --reason (usage error, exit 2, never 0) ----------


def test_bypass_without_reason_is_a_usage_error(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc = main(["scan", str(tmp_path), "--bypass"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert "usage" in captured.err
    assert "--reason" in captured.err


def test_reason_without_bypass_is_not_an_error(capsys, tmp_path):
    """--reason has no effect on its own (never a usage error) -- only
    --bypass without --reason is guarded."""
    _blocking_fixture(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--reason", "unused"])
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "warn"


def test_bypass_with_empty_string_reason_is_not_a_usage_error(capsys, tmp_path):
    """The flag being PRESENT (even with an empty value) satisfies
    --bypass's requirement -- only its ABSENCE (argparse default None) is a
    usage error."""
    _blocking_fixture(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--bypass", "--reason", ""])
    assert rc == 0
    assert document["status"]["value"] == "bypassed"


# --- --bypass --reason "<text>" with blocking findings -------------------


def test_bypass_with_blocking_findings_prints_stanza_and_exits_bypassed(
    capsys, tmp_path
):
    _blocking_fixture(tmp_path)
    capsys.readouterr()
    rc = main(["scan", str(tmp_path), "--bypass", "--reason", "ci override"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "version: 1" in captured.out
    assert "hygiene:DEP002:requests" in captured.out
    assert "ci override" in captured.out
    assert "status=bypassed" in captured.out
    assert "exit_code=0" in captured.out
    # The tool never writes the stanza into the scanned tree.
    assert not (tmp_path / ".warden-waivers.yaml").exists()


def test_bypass_stanza_is_yaml_safe_load_parseable_with_one_entry(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    capsys.readouterr()
    main(["scan", str(tmp_path), "--bypass", "--reason", "x"])
    captured = capsys.readouterr()
    # The stanza is the FIRST document-shaped content on stdout, before the
    # text-format human summary -- yaml.safe_load stops at the first
    # complete mapping it can parse from the leading lines.
    stanza_lines = []
    for line in captured.out.splitlines():
        if line.startswith(f"{TOOL_NAME}:"):
            break
        stanza_lines.append(line)
    document = yaml.safe_load("\n".join(stanza_lines))
    assert document["version"] == 1
    assert len(document["waivers"]) == 1
    assert document["waivers"][0]["id"] == "hygiene:DEP002:requests"
    assert document["waivers"][0]["reason"] == "x"


def test_bypass_json_format_still_exits_bypassed(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--bypass", "--reason", "x"])
    assert rc == 0
    assert document["exit_code"] == 0
    assert document["status"]["value"] == "bypassed"


def test_bypass_json_format_writes_the_stanza_to_stderr_not_stdout(capsys, tmp_path):
    """Review finding: --format json must keep stdout as EXACTLY one
    schema-valid document (NFR-I3) -- the stanza would otherwise be lost
    entirely for a json/CI consumer, so it goes to stderr instead."""
    _blocking_fixture(tmp_path)
    rc, document, err = scan_json(capsys, tmp_path, ["--bypass", "--reason", "ci override"])
    assert rc == 0
    assert document["status"]["value"] == "bypassed"
    assert "version: 1" in err
    assert "hygiene:DEP002:requests" in err
    assert "ci override" in err


def test_authorized_by_falls_back_to_unknown_when_getpass_raises(
    capsys, tmp_path, monkeypatch
):
    import pyforge.warden.cli as cli_module

    def _raise() -> str:
        raise OSError("no such user")

    monkeypatch.setattr(cli_module.getpass, "getuser", _raise)
    _blocking_fixture(tmp_path)
    capsys.readouterr()
    main(["scan", str(tmp_path), "--bypass", "--reason", "x"])
    captured = capsys.readouterr()
    assert "authorized_by: unknown" in captured.out


def test_bypass_respects_configured_waiver_default_expiry_days(capsys, tmp_path):
    write_pyproject(
        tmp_path,
        ["requests==2.31.0"],
        extra="\n[tool.pyforge-warden]\nwaiver-default-expiry-days = 30\n",
    )
    (tmp_path / "main.py").write_text("", encoding="utf-8")
    capsys.readouterr()
    main(["scan", str(tmp_path), "--bypass", "--reason", "x"])
    captured = capsys.readouterr()
    stanza_lines = []
    for line in captured.out.splitlines():
        if line.startswith(f"{TOOL_NAME}:"):
            break
        stanza_lines.append(line)
    document = yaml.safe_load("\n".join(stanza_lines))
    entry = document["waivers"][0]
    accepted = datetime.fromisoformat(entry["accepted_at"])
    expires = datetime.fromisoformat(entry["expires_at"])
    assert expires - accepted == timedelta(days=30)


# --- a committed valid non-expired waiver file (no --bypass) -------------


def test_committed_valid_waiver_bypasses_the_matching_finding(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    write_waiver_file(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path)
    assert rc == 0
    assert document["exit_code"] == 0
    assert document["status"]["value"] == "bypassed"


def test_committed_waiver_is_echoed_in_text_format(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    write_waiver_file(tmp_path, reason="tracked in JIRA-1", authorized_by="alice")
    rc = main(["scan", str(tmp_path)])  # text is the default format
    captured = capsys.readouterr()
    assert rc == 0
    assert "status=bypassed" in captured.out
    assert "[waiver] hygiene:DEP002:requests" in captured.out
    assert "reason=tracked in JIRA-1" in captured.out
    assert "authorized_by=alice" in captured.out
    assert _FAR_FUTURE in captured.out


def test_expired_waiver_leaves_the_original_finding_status(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    write_waiver_file(
        tmp_path, accepted_at=_LONG_AGO, expires_at=_RECENTLY_EXPIRED
    )
    rc, document, _ = scan_json(capsys, tmp_path)
    assert document["status"]["value"] == "warn"  # never bypassed
    assert rc == document["exit_code"] == 0


def test_expired_waiver_is_not_echoed_in_text_format(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    write_waiver_file(
        tmp_path, accepted_at=_LONG_AGO, expires_at=_RECENTLY_EXPIRED
    )
    rc = main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "[waiver]" not in captured.out


# --- malformed / wildcard-id / unknown-version waiver file (FR26) --------


def test_malformed_waiver_yaml_is_a_config_parse_error(capsys, tmp_path):
    (tmp_path / ".warden-waivers.yaml").write_text(
        "version: 1\nwaivers:\n  - id: [unterminated\n", encoding="utf-8"
    )
    rc, document, err = scan_json(capsys, tmp_path)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-parse" in by_kind
    assert by_kind["config-parse"]["owner"] == "waiver"
    assert err != ""


def test_unknown_version_waiver_file_is_a_config_validation_error(capsys, tmp_path):
    (tmp_path / ".warden-waivers.yaml").write_text(
        "version: 2\nwaivers: []\n", encoding="utf-8"
    )
    rc, document, _ = scan_json(capsys, tmp_path)
    assert rc == 2
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-validation" in by_kind
    assert by_kind["config-validation"]["owner"] == "waiver"


def test_wildcard_id_waiver_file_rejects_the_whole_file(capsys, tmp_path):
    write_waiver_file(tmp_path, entry_id="vuln:*:*")
    rc, document, _ = scan_json(capsys, tmp_path)
    assert rc == 2
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-validation" in by_kind
    assert by_kind["config-validation"]["owner"] == "waiver"


def test_malformed_waiver_file_still_fails_closed_even_with_bypass(capsys, tmp_path):
    """Review finding (traced but previously untested): a malformed
    committed waiver file's error rung must survive --bypass -- an
    ``error:...``-driven rung never matches any of the three finding-id
    families, so bypass_blocking cannot touch it, and the scan still fails
    closed at exit 2 regardless of --bypass."""
    _blocking_fixture(tmp_path)
    (tmp_path / ".warden-waivers.yaml").write_text(
        "version: 1\nwaivers:\n  - id: [unterminated\n", encoding="utf-8"
    )
    rc, document, err = scan_json(
        capsys, tmp_path, ["--bypass", "--reason", "ci override"]
    )
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-parse" in by_kind
    assert by_kind["config-parse"]["owner"] == "waiver"
    assert err != ""


def test_missing_waiver_file_is_not_an_error(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc, document, err = scan_json(capsys, tmp_path)
    assert document["status"]["value"] == "warn"
    assert document["errors"] == []
    assert "waiver" not in err
