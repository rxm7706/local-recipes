"""Unit tests for ``pyforge.doctor.__main__``'s ``backlog-intake``
subcommand (Story 13.1) -- covers the usage-error validation-before-gather
discipline (mirrors ``test_cli_check.py``'s own ``--engines bogus-name``
coverage), the default ``path='.'``/positional-``path``-forwarding shape,
and ``--json`` schema-valid output.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import jsonschema

from pyforge.doctor.__main__ import main
from pyforge.doctor.models import DoctorStatus, Finding, Source


def _schema() -> dict:
    schema_text = resources.files("pyforge.doctor").joinpath("data", "report-schema.json").read_text(encoding="utf-8")
    return json.loads(schema_text)


def _write_ledger(target: Path, project: str, text: str) -> Path:
    path = target / "_bmad-output" / "projects" / project / "planning-artifacts" / "deferred-work-ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class _ForbiddenGatherError(BaseException):
    """Deliberately a ``BaseException``, not ``Exception`` (mirrors
    ``test_cli_check.py``'s own sentinel): must never be swallowed by any
    ``except Exception`` net, so a validation bypass fails this test loudly
    rather than being silently absorbed."""


def _forbid_gather(monkeypatch) -> None:
    def _boom(target, *, identifier):
        raise _ForbiddenGatherError("must never gather() an unvalidated identifier")

    monkeypatch.setattr("pyforge.doctor.__main__.backlog_intake.gather", _boom)


# --- usage error: unparseable identifier, validated before gather ----------


def test_unparseable_identifier_is_usage_error_never_reaches_gather(monkeypatch, tmp_path: Path, capsys):
    _forbid_gather(monkeypatch)

    exit_code = main(["backlog-intake", "not-an-id", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "not-an-id" in captured.err
    assert captured.out == ""


def test_missing_identifier_positional_is_usage_error(capsys):
    exit_code = main(["backlog-intake"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err


# --- default path / positional path forwarding ------------------------------


def test_default_path_is_current_directory(monkeypatch, capsys):
    calls: list[Path] = []

    def _stub(target, *, identifier):
        calls.append(target)
        return (
            Finding(
                source=Source.BACKLOG_INTAKE,
                check="backlog-intake",
                status=DoctorStatus.OK,
                message="no match",
                evidence={"identifier": identifier, "matches": 0},
            ),
        )

    monkeypatch.setattr("pyforge.doctor.__main__.backlog_intake.gather", _stub)

    exit_code = main(["backlog-intake", "13"])

    assert exit_code == 0
    assert calls == [Path(".")]


def test_path_positional_is_forwarded_to_gather(monkeypatch, tmp_path: Path):
    calls: list[Path] = []

    def _stub(target, *, identifier):
        calls.append(target)
        return ()

    monkeypatch.setattr("pyforge.doctor.__main__.backlog_intake.gather", _stub)

    main(["backlog-intake", "13", str(tmp_path)])

    assert calls == [Path(str(tmp_path))]


# --- real end-to-end match against a fixture ledger -------------------------


def test_matching_run_reports_warn_and_exits_zero(tmp_path: Path, capsys):
    _write_ledger(tmp_path, "doctor", "## DW-1: entry\nstatus: open\nsummary: Epic 13.\n")

    exit_code = main(["backlog-intake", "13", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0  # WARN never gates the exit code
    assert "backlog-intake" in captured.out
    assert "warn" in captured.out
    assert "0 fail" in captured.out


def test_no_match_run_reports_ok_and_exits_zero(tmp_path: Path, capsys):
    exit_code = main(["backlog-intake", "13", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "1 ok" in captured.out
    assert "0 fail" in captured.out


# --- --json: schema-valid, verb-correct, no prescriptions key --------------


def test_json_output_is_schema_valid_and_carries_the_right_verb(tmp_path: Path, capsys):
    _write_ledger(tmp_path, "doctor", "## DW-1: entry\nstatus: open\nsummary: Epic 13.\n")

    exit_code = main(["backlog-intake", "13", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.validate(document, _schema())
    assert exit_code == 0
    assert document["verb"] == "backlog-intake"
    assert "prescriptions" not in document
    assert [f["source"] for f in document["findings"]] == ["backlog-intake"]
    assert document["findings"][0]["status"] == "warn"
    assert document["findings"][0]["evidence"]["entry_id"] == "DW-1"


def test_json_output_for_a_clean_run_carries_zero_matches(tmp_path: Path, capsys):
    exit_code = main(["backlog-intake", "13", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.validate(document, _schema())
    assert exit_code == 0
    assert document["findings"][0]["status"] == "ok"
    assert document["findings"][0]["evidence"] == {"identifier": "13", "matches": 0}
