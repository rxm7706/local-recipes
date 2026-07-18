"""Unit tests — the ``--sbom-output`` CLI surface (Story 4.1).

A new sibling to ``test_cli_bypass.py`` per the story spec's Code Map.
Mirrors that file's own conventions: real ``tmp_path`` fixtures, ``main()``
invoked end-to-end, JSON output schema-validated via ``jsonschema`` (report)
and ``JsonStrictValidator`` (SBOM). Covers the two I/O-matrix rows
``test_sbom.py`` explicitly excludes: the write-success and write-failure
CLI rows.
"""

from __future__ import annotations

import importlib.metadata
import json
from email.message import Message
from importlib import resources
from pathlib import Path

import jsonschema
import pytest
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator

from pyforge.warden.cli import main

_VALIDATOR = JsonStrictValidator(SchemaVersion.V1_6)


# Follow-up review pass (2026-07-18): this module's fixtures declare
# `requests==2.31.0`, whose license-axis outcome depended on whatever
# requests metadata the AMBIENT pixi env happens to carry — the exact
# relock fragility Fix 9 already pinned away in
# tests/conformance/test_scan_harness.py. Same pattern replicated here:
# only "requests"/"packaging" get pinned, deterministic metadata; every
# other name still resolves via the real importlib.metadata.metadata.


def _fake_license_metadata(*, license_expression: str) -> Message:
    msg = Message()
    msg["License-Expression"] = license_expression
    return msg


_PINNED_PYPI_LICENSE_METADATA: dict[str, Message] = {
    "requests": _fake_license_metadata(license_expression="Apache-2.0"),
    "packaging": _fake_license_metadata(
        license_expression="Apache-2.0 OR BSD-2-Clause"
    ),
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


def write_pyproject(directory: Path, deps: list[str]) -> None:
    body = (
        "[project]\n"
        'name = "demo"\n'
        'version = "0.0.1"\n'
        f"dependencies = {json.dumps(deps)}\n"
    )
    (directory / "pyproject.toml").write_text(body, encoding="utf-8")


def load_report_schema() -> dict:
    schema_file = resources.files("pyforge.warden") / "data" / "report-schema.json"
    return json.loads(schema_file.read_text(encoding="utf-8"))


def scan_json(
    capsys, target, extra_args: list[str] | None = None
) -> tuple[int, dict, str]:
    capsys.readouterr()
    rc = main(["scan", str(target), "--format", "json", *(extra_args or [])])
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.Draft202012Validator(load_report_schema()).validate(document)
    return rc, document, captured.err


def _fixture(tmp_path: Path) -> None:
    write_pyproject(tmp_path, ["requests==2.31.0"])
    (tmp_path / "main.py").write_text("import requests\n", encoding="utf-8")


# --- write success -----------------------------------------------------


def test_sbom_output_writes_schema_valid_cyclonedx_json(capsys, tmp_path):
    _fixture(tmp_path)
    out_path = tmp_path / "sbom.json"
    rc, document, _ = scan_json(capsys, tmp_path, ["--sbom-output", str(out_path)])
    assert rc == document["exit_code"]
    assert out_path.exists()
    sbom_text = out_path.read_text(encoding="utf-8")
    assert _VALIDATOR.validate_str(sbom_text) is None
    sbom_document = json.loads(sbom_text)
    assert len(sbom_document.get("components", [])) == document["inventory_count"]


def test_sbom_output_leaves_exit_code_and_report_unchanged(capsys, tmp_path):
    _fixture(tmp_path)
    rc_baseline, document_baseline, _ = scan_json(capsys, tmp_path)
    out_path = tmp_path / "sbom.json"
    rc, document, _ = scan_json(capsys, tmp_path, ["--sbom-output", str(out_path)])
    assert rc == rc_baseline
    assert document == document_baseline


def test_sbom_output_works_with_text_format_too(capsys, tmp_path):
    _fixture(tmp_path)
    out_path = tmp_path / "sbom.json"
    capsys.readouterr()
    rc = main(["scan", str(tmp_path), "--sbom-output", str(out_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "status=clean" in captured.out
    assert out_path.exists()
    assert _VALIDATOR.validate_str(out_path.read_text(encoding="utf-8")) is None


def test_sbom_output_not_requested_writes_nothing(capsys, tmp_path):
    _fixture(tmp_path)
    scan_json(capsys, tmp_path)
    assert not (tmp_path / "sbom.json").exists()


# --- write failure (OSError), non-fatal -----------------------------------


def test_sbom_output_write_failure_is_non_fatal_and_leaves_exit_code_unchanged(
    capsys, tmp_path
):
    _fixture(tmp_path)
    rc_baseline, document_baseline, _ = scan_json(capsys, tmp_path)
    unwritable_target = tmp_path / "does" / "not" / "exist" / "sbom.json"
    rc, document, err = scan_json(
        capsys, tmp_path, ["--sbom-output", str(unwritable_target)]
    )
    assert rc == rc_baseline
    assert document == document_baseline
    assert not unwritable_target.exists()
    assert "--sbom-output" in err


def test_sbom_output_write_failure_still_emits_the_report_on_stdout(capsys, tmp_path):
    _fixture(tmp_path)
    unwritable_target = tmp_path / "does" / "not" / "exist" / "sbom.json"
    capsys.readouterr()
    rc = main(["scan", str(tmp_path), "--sbom-output", str(unwritable_target)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "status=clean" in captured.out
    assert "--sbom-output" in captured.err
