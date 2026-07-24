"""Conformance tests -- baseline & grandfathering (Story 6.8), exercised
end-to-end through ``cli.main()`` (mirrors ``test_cli_bypass.py``'s own
``tmp_path``/real-``yaml``/``main()`` convention -- a sibling test for the
new ``--baseline``/``--baseline-emit`` CLI surface, one axis over from
``--bypass``/committed ``.warden-waivers.yaml``).

Covers the intent-contract I/O matrix: a matching baseline entry suppresses
its finding and echoes ``origin="baseline"`` in ``suppressions[]``; an
unlisted finding still gates normally; an expired entry re-blocks with a
``[baseline-expired]`` notice, never a suppression; a waiver on the SAME
finding id wins the tie-break; a baseline that covers every blocking
finding composes ``bypassed``, never ``clean`` (C0); a tool-internal error
is never masked by a baseline entry; ``--baseline-emit`` prints a stanza to
the correct stream per ``--format`` and never itself changes the verdict;
a missing/malformed/schema-invalid ``--baseline`` path composes ``error``.
"""

from __future__ import annotations

import importlib.metadata
import json
from email.message import Message
from importlib import resources
from pathlib import Path

import jsonschema
import pytest
import yaml

from pyforge.warden.cli import main
from pyforge.warden.report import TOOL_NAME

# --- Fix 9 precedent (test_cli_bypass.py/test_scan_harness.py): pin PyPI
# license metadata for the two names these fixtures declare, so a routine
# relock of the ambient pixi env can never flip a fixture's license-axis
# outcome and break an assertion this suite never meant to be about
# licenses at all.


def _fake_license_metadata(*, license_expression: str) -> Message:
    msg = Message()
    msg["License-Expression"] = license_expression
    return msg


_PINNED_PYPI_LICENSE_METADATA: dict[str, Message] = {
    "requests": _fake_license_metadata(license_expression="Apache-2.0"),
}


@pytest.fixture(autouse=True)
def _pin_pypi_license_metadata(monkeypatch):
    real_metadata = importlib.metadata.metadata

    def fake_metadata(name, *args, **kwargs):
        pinned = _PINNED_PYPI_LICENSE_METADATA.get(name)
        if pinned is not None:
            return pinned
        return real_metadata(name, *args, **kwargs)

    monkeypatch.setattr(importlib.metadata, "metadata", fake_metadata)


_FAR_FUTURE = "2099-01-01T00:00:00+00:00"
_RECENTLY_EXPIRED = "2000-06-01T00:00:00+00:00"
_BLOCKING_FINDING_ID = "hygiene:DEP002:requests"


def write_pyproject(directory: Path, deps: list[str]) -> None:
    body = (
        "[project]\n"
        'name = "demo"\n'
        'version = "0.0.1"\n'
        f"dependencies = {json.dumps(deps)}\n"
    )
    (directory / "pyproject.toml").write_text(body, encoding="utf-8")


def _blocking_fixture(tmp_path: Path) -> None:
    """A hygiene DEP002 (unused-dependency) warn finding -- the one
    "blocking" finding every test in this file baselines/leaves alone."""
    write_pyproject(tmp_path, ["requests==2.31.0"])
    (tmp_path / "main.py").write_text("", encoding="utf-8")


def write_baseline_file(
    directory: Path,
    *,
    filename: str = ".warden-baseline.yaml",
    entry_id: str = _BLOCKING_FINDING_ID,
    expires_at: str = _FAR_FUTURE,
    reason: str | None = "grandfathered at adoption",
) -> Path:
    reason_line = f"    reason: {reason!r}\n" if reason is not None else ""
    body = (
        "version: 1\n"
        "baseline:\n"
        f"  - id: {entry_id!r}\n"
        f"    expires_at: {expires_at!r}\n"
        f"{reason_line}"
    )
    path = directory / filename
    path.write_text(body, encoding="utf-8")
    return path


def write_waiver_file(
    directory: Path,
    *,
    entry_id: str = _BLOCKING_FINDING_ID,
    reason: str = "tracked in JIRA-1",
    authorized_by: str = "alice",
) -> None:
    body = (
        "version: 1\n"
        "waivers:\n"
        f"  - id: {entry_id!r}\n"
        f"    reason: {reason!r}\n"
        f"    authorized_by: {authorized_by!r}\n"
        "    accepted_at: '2000-01-01T00:00:00+00:00'\n"
        f"    expires_at: {_FAR_FUTURE!r}\n"
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


def scan_text(capsys, target, extra_args: list[str] | None = None) -> tuple[int, str, str]:
    capsys.readouterr()
    rc = main(["scan", str(target), *(extra_args or [])])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


# --- a matching, non-expired baseline entry suppresses the finding -------


def test_baseline_suppresses_the_matching_finding_and_exits_bypassed(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    baseline_path = write_baseline_file(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 0
    assert document["exit_code"] == 0
    assert document["status"]["value"] == "bypassed"  # C0: never "clean"


def test_baseline_suppression_is_echoed_with_origin_baseline(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    baseline_path = write_baseline_file(
        tmp_path, reason="grandfathered at adoption", expires_at=_FAR_FUTURE
    )
    rc, document, _ = scan_json(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 0
    (suppression,) = document["suppressions"]
    assert suppression["finding_id"] == _BLOCKING_FINDING_ID
    assert suppression["origin"] == "baseline"
    assert suppression["reason"] == "grandfathered at adoption"
    assert suppression["authorized_by"] is None
    assert suppression["expires_at"] == _FAR_FUTURE


def test_baseline_suppression_is_echoed_in_text_format(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    baseline_path = write_baseline_file(tmp_path, reason="grandfathered at adoption")
    rc, out, _ = scan_text(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 0
    assert "status=bypassed" in out
    assert f"[baseline] {_BLOCKING_FINDING_ID}" in out
    assert "reason=grandfathered at adoption" in out
    assert _FAR_FUTURE in out


# --- an unlisted finding still gates normally -----------------------------


def test_baseline_unlisted_finding_gates_normally(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    baseline_path = write_baseline_file(tmp_path, entry_id="hygiene:DEP002:other-pkg")
    rc, document, _ = scan_json(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 0
    assert document["status"]["value"] == "warn"  # unaffected -- never bypassed
    assert document["suppressions"] == []


# --- an expired baseline entry re-blocks ----------------------------------


def test_expired_baseline_entry_reblocks_the_finding(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    baseline_path = write_baseline_file(tmp_path, expires_at=_RECENTLY_EXPIRED)
    rc, document, _ = scan_json(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 0
    assert document["status"]["value"] == "warn"  # never bypassed
    assert document["suppressions"] == []


def test_expired_baseline_entry_shows_a_baseline_expired_notice_not_a_suppression(
    capsys, tmp_path
):
    _blocking_fixture(tmp_path)
    baseline_path = write_baseline_file(
        tmp_path, reason="grandfathered at adoption", expires_at=_RECENTLY_EXPIRED
    )
    rc, out, _ = scan_text(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 0
    assert "[baseline]" not in out
    assert f"[baseline-expired] {_BLOCKING_FINDING_ID}" in out
    assert "reason=grandfathered at adoption" in out
    assert _RECENTLY_EXPIRED in out
    assert "re-blocked" not in out


# --- waiver + baseline on the same finding id: waiver wins ----------------


def test_waiver_and_baseline_same_id_waiver_wins_end_to_end(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    write_waiver_file(tmp_path, reason="waiver reason")
    baseline_path = write_baseline_file(tmp_path, reason="baseline reason")
    rc, document, _ = scan_json(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 0
    assert document["status"]["value"] == "bypassed"
    (suppression,) = document["suppressions"]  # exactly one, never two
    assert suppression["origin"] == "waiver"
    assert suppression["reason"] == "waiver reason"


# --- --baseline unset leaves pre-6.8 behavior byte-identical --------------


def test_baseline_flag_omitted_is_identical_to_pre_6_8(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc, document, err = scan_json(capsys, tmp_path)
    assert document["status"]["value"] == "warn"
    assert document["suppressions"] == []
    assert document["errors"] == []
    assert "baseline" not in err


# --- --baseline-emit: purely observational --------------------------------


def test_baseline_emit_prints_stanza_to_stdout_under_text_format(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc, out, _ = scan_text(capsys, tmp_path, ["--baseline-emit"])
    assert rc == 0
    assert "status=warn" in out  # --baseline-emit never itself suppresses
    stanza_lines = []
    for line in out.splitlines():
        if line.startswith(f"{TOOL_NAME}:"):
            break
        stanza_lines.append(line)
    document = yaml.safe_load("\n".join(stanza_lines))
    assert document["version"] == 1
    assert len(document["baseline"]) == 1
    assert document["baseline"][0]["id"] == _BLOCKING_FINDING_ID
    assert "expires_at" in document["baseline"][0]
    assert "authorized_by" not in document["baseline"][0]
    # The tool never writes the stanza into the scanned tree.
    assert not (tmp_path / ".warden-baseline.yaml").exists()


def test_baseline_emit_writes_the_stanza_to_stderr_under_json_format(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc, document, err = scan_json(capsys, tmp_path, ["--baseline-emit"])
    assert rc == 0
    assert document["status"]["value"] == "warn"
    assert "version: 1" in err
    assert _BLOCKING_FINDING_ID in err


def test_baseline_emit_does_not_include_an_already_baselined_finding(capsys, tmp_path):
    """--baseline-emit reflects rungs still blocking AFTER waiver+baseline
    suppression already applied -- an already-baselined finding never
    reappears as its own candidate."""
    _blocking_fixture(tmp_path)
    baseline_path = write_baseline_file(tmp_path)
    rc, out, _ = scan_text(
        capsys, tmp_path, ["--baseline", str(baseline_path), "--baseline-emit"]
    )
    assert rc == 0
    assert "status=bypassed" in out
    stanza_lines = []
    for line in out.splitlines():
        if line.startswith(f"{TOOL_NAME}:"):
            break
        stanza_lines.append(line)
    document = yaml.safe_load("\n".join(stanza_lines))
    assert document["baseline"] == []


def test_baseline_emit_never_changes_the_exit_code_or_status(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc_without, doc_without, _ = scan_json(capsys, tmp_path)
    rc_with, doc_with, _ = scan_json(capsys, tmp_path, ["--baseline-emit"])
    assert rc_without == rc_with
    assert doc_without["status"]["value"] == doc_with["status"]["value"]
    assert doc_without["findings"] == doc_with["findings"]


# --- C0: baseline covering every blocking finding composes bypassed ------


def test_baseline_covering_everything_never_composes_clean(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    baseline_path = write_baseline_file(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 0
    assert document["status"]["value"] == "bypassed"
    assert document["status"]["value"] != "clean"


# --- a tool error is never masked by a baseline entry ---------------------


def test_baseline_never_masks_a_co_occurring_tool_error(capsys, tmp_path):
    """A genuinely broken manifest still composes 'error' regardless of an
    otherwise-valid, unrelated baseline entry sitting alongside it."""
    (tmp_path / "pyproject.toml").write_text("not [ valid toml", encoding="utf-8")
    baseline_path = write_baseline_file(tmp_path, entry_id="hygiene:DEP002:unrelated")
    rc, document, err = scan_json(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    assert document["suppressions"] == []
    assert err != ""


def test_baseline_entry_shaped_like_an_error_id_is_rejected_at_load_time(
    capsys, tmp_path
):
    """C0's structural guarantee starts at the file boundary: an
    error:<kind>:<subject> id fails the finding-id family regex, so a
    committed baseline can never even successfully NAME an error rung --
    the whole file is rejected as malformed, never silently accepted."""
    _blocking_fixture(tmp_path)
    baseline_path = write_baseline_file(
        tmp_path, entry_id="error:config-parse:some-subject"
    )
    rc, document, _ = scan_json(capsys, tmp_path, ["--baseline", str(baseline_path)])
    assert rc == 2
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-validation" in by_kind
    assert by_kind["config-validation"]["owner"] == "baseline"


# --- malformed / missing --baseline path composes error -------------------


def test_missing_baseline_path_composes_error(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    missing = tmp_path / "does-not-exist.yaml"
    rc, document, err = scan_json(capsys, tmp_path, ["--baseline", str(missing)])
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-validation" in by_kind
    assert by_kind["config-validation"]["owner"] == "baseline"
    assert err != ""


def test_malformed_baseline_yaml_composes_error(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    path = tmp_path / ".warden-baseline.yaml"
    path.write_text("version: 1\nbaseline:\n  - id: [unterminated\n", encoding="utf-8")
    rc, document, err = scan_json(capsys, tmp_path, ["--baseline", str(path)])
    assert rc == 2
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-parse" in by_kind
    assert by_kind["config-parse"]["owner"] == "baseline"
    assert err != ""


def test_schema_invalid_baseline_document_composes_error(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    path = tmp_path / ".warden-baseline.yaml"
    path.write_text("version: 2\nbaseline: []\n", encoding="utf-8")
    rc, document, _ = scan_json(capsys, tmp_path, ["--baseline", str(path)])
    assert rc == 2
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-validation" in by_kind
    assert by_kind["config-validation"]["owner"] == "baseline"


def test_malformed_baseline_file_still_fails_closed_even_with_bypass(capsys, tmp_path):
    """Mirrors test_cli_bypass.py's own malformed-waiver-survives-bypass
    proof: a malformed --baseline error rung's id matches none of the
    finding-id families, so --bypass cannot touch it either."""
    _blocking_fixture(tmp_path)
    path = tmp_path / ".warden-baseline.yaml"
    path.write_text("version: 1\nbaseline:\n  - id: [unterminated\n", encoding="utf-8")
    rc, document, err = scan_json(
        capsys, tmp_path, ["--baseline", str(path), "--bypass", "--reason", "x"]
    )
    assert rc == 2
    assert document["status"]["value"] == "error"
    assert err != ""
