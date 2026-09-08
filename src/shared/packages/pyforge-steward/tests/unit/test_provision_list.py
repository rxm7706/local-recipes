"""`format_environments` + `provision --list [--json]` CLI dispatch — Story 3.3."""

from __future__ import annotations

import json

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.provision import format_environments

_PIXI_TOML = """\
[environments]
linux = ["linux", "python"]
pyforge-steward = { features = ["pyforge-steward"], no-default-feature = true }
"""


def _write_pixi_toml(tmp_path):
    (tmp_path / "pixi.toml").write_text(_PIXI_TOML, encoding="utf-8")
    return tmp_path


def test_format_environments_text_lists_every_name_with_its_features():
    environments = {"linux": ("linux", "python"), "pyforge-steward": ("pyforge-steward",)}

    text = format_environments(environments, as_json=False)

    assert "linux" in text
    assert "linux, python" in text
    assert "pyforge-steward" in text


def test_format_environments_json_emits_machine_readable_data():
    environments = {"linux": ("linux", "python"), "pyforge-steward": ("pyforge-steward",)}

    text = format_environments(environments, as_json=True)
    data = json.loads(text)

    assert data == {"linux": ["linux", "python"], "pyforge-steward": ["pyforge-steward"]}


def test_format_environments_empty_text_is_a_clear_sentence_not_a_blank_string():
    assert format_environments({}, as_json=False) != ""
    assert "no environments" in format_environments({}, as_json=False)


def test_format_environments_empty_json_is_an_empty_object():
    assert json.loads(format_environments({}, as_json=True)) == {}


def test_provision_list_via_cli_prints_every_environment(tmp_path, monkeypatch, capsys):
    _write_pixi_toml(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "linux" in out
    assert "pyforge-steward" in out


def test_provision_list_json_via_cli_emits_valid_json(tmp_path, monkeypatch, capsys):
    _write_pixi_toml(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list", "--json"])

    assert rc == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["linux"] == ["linux", "python"]
    assert data["pyforge-steward"] == ["pyforge-steward"]


def test_provision_list_json_on_malformed_pixi_toml_still_emits_valid_json(
    tmp_path, monkeypatch, capsys
):
    """Review finding: an error raised on ANY flag's path used to always
    render as plain text (`f"provision: {exc}"`), even when `--json` was
    passed -- `--list --json` against a malformed `pixi.toml` used to
    print un-parseable text instead of a JSON error object, breaking any
    caller that unconditionally `json.loads()`s the output because
    `--json` was requested."""
    (tmp_path / "pixi.toml").write_text("[environments\nbroken toml", encoding="utf-8")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list", "--json"])

    assert rc == EXIT_FAILED
    data = json.loads(capsys.readouterr().err)
    assert "error" in data


def test_provision_list_never_writes_to_pixi_toml(tmp_path, monkeypatch):
    root = _write_pixi_toml(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: root)
    before = (root / "pixi.toml").read_text(encoding="utf-8")

    main(["provision", "--list"])

    assert (root / "pixi.toml").read_text(encoding="utf-8") == before
