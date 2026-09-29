"""`module_install_states` + `format_module_states` + `provision
--list-modules` CLI dispatch — Story 6.2.

Covers every row of the story spec's I/O & Edge-Case Matrix (no
`_bmad/config.yaml`, a `bmb:` key present, `--json`, malformed YAML honors
`--json` on its error path, a non-mapping `_bmad/config.yaml` degrades to
all-`available`), a read-only guard, and a precedence test mirroring
`test_provision_module.py`'s own
`test_provision_module_takes_precedence_over_verify_and_list` shape. This
is a pure filesystem read — no subprocess is ever exercised here, unlike
`--module`.

Story 15.3 grew `_SUPPORTED_MODULES` to five names; every "all available"
assertion below expects that full set. WDS is skip-only and must never
appear.
"""

from __future__ import annotations

import argparse
import json
import tomllib

import pytest
import yaml

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.provision import (
    _SKIPPED_MODULES,
    _SUPPORTED_MODULES,
    ProvisionDuty,
    format_module_states,
    module_install_states,
)

_ALL_AVAILABLE = {name: "available" for name in _SUPPORTED_MODULES}
_WIRED_NAMES = frozenset(_SUPPORTED_MODULES)


def _full_namespace(**overrides):
    base = {
        "module": None,
        "env": None,
        "runner": None,
        "list": False,
        "verify": False,
        "list_modules": False,
        "json": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _write_bmad_config(tmp_path, text):
    bmad_dir = tmp_path / "_bmad"
    bmad_dir.mkdir(parents=True, exist_ok=True)
    (bmad_dir / "config.yaml").write_text(text, encoding="utf-8")
    return bmad_dir / "config.yaml"


def _write_custom_config_toml(tmp_path, text):
    custom_dir = tmp_path / "_bmad" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    (custom_dir / "config.toml").write_text(text, encoding="utf-8")
    return custom_dir / "config.toml"


# ── module_install_states (primitive) ────────────────────────────────────


def test_module_install_states_reports_available_when_config_yaml_is_absent(tmp_path):
    states = module_install_states(cwd=tmp_path)

    assert states == _ALL_AVAILABLE
    assert "wds" not in states


def test_module_install_states_reports_installed_when_the_module_key_is_present(tmp_path):
    _write_bmad_config(tmp_path, "bmb:\n  output_folder: skills\n")

    states = module_install_states(cwd=tmp_path)

    assert states["bmb"] == "installed"
    assert all(states[n] == "available" for n in _WIRED_NAMES if n != "bmb")


def test_module_install_states_ignores_unrelated_top_level_keys(tmp_path):
    _write_bmad_config(tmp_path, "core:\n  output_folder: something\n")

    states = module_install_states(cwd=tmp_path)

    assert states == _ALL_AVAILABLE


def test_module_install_states_non_mapping_config_yaml_degrades_to_all_available(tmp_path):
    _write_bmad_config(tmp_path, "- just\n- a\n- list\n")

    states = module_install_states(cwd=tmp_path)

    assert states == _ALL_AVAILABLE


def test_module_install_states_malformed_config_yaml_raises_yaml_error(tmp_path):
    _write_bmad_config(tmp_path, "bmb: [unterminated\n")

    with pytest.raises(yaml.YAMLError):
        module_install_states(cwd=tmp_path)


def test_module_install_states_empty_config_yaml_degrades_to_all_available(tmp_path):
    """`yaml.safe_load` on an empty/comment-only file returns `None`, a
    distinct branch from "parses to a non-dict" -- both must degrade to `{}`
    rather than raising."""
    _write_bmad_config(tmp_path, "# just a comment, no content\n")

    states = module_install_states(cwd=tmp_path)

    assert states == _ALL_AVAILABLE


def test_module_install_states_unreadable_encoding_raises_unicode_decode_error(tmp_path):
    """A `_bmad/config.yaml` with invalid UTF-8 bytes must raise
    `UnicodeDecodeError` from the primitive -- `ProvisionDuty.run()`'s
    boundary is what turns this into a clean `DutyResult`, not this
    function."""
    bmad_dir = tmp_path / "_bmad"
    bmad_dir.mkdir(parents=True)
    (bmad_dir / "config.yaml").write_bytes(b"bmb: \xff\xfe invalid utf8\n")

    with pytest.raises(UnicodeDecodeError):
        module_install_states(cwd=tmp_path)


# ── AD-9 two-location read (Story 46.2) ──────────────────────────────────


def test_module_install_states_reports_installed_from_custom_config_toml(tmp_path):
    """A module recorded only under `_bmad/custom/config.toml`'s
    `[modules.<name>]` (the new roster location every `CondaInstallBackend`
    module's provisioning path now writes) reports installed too."""
    _write_custom_config_toml(
        tmp_path,
        '[modules.utility-skills]\nprovisioned_by = "steward"\n'
        'installer = "bmad-utility-skills-install"\nskills = ["bmad-os-gh-triage"]\n',
    )

    states = module_install_states(cwd=tmp_path)

    assert states["utility-skills"] == "installed"
    assert all(states[n] == "available" for n in _WIRED_NAMES if n != "utility-skills")


def test_module_install_states_two_location_read_cis_legacy_and_utility_new(tmp_path):
    """The story's own I/O Matrix row: `cis` recorded only in the legacy
    `_bmad/config.yaml`, `utility-skills` recorded only in the new
    `_bmad/custom/config.toml` -- both report installed; a module in
    neither location still reports available."""
    _write_bmad_config(tmp_path, "cis:\n  installer: bmad-cis-install\n")
    _write_custom_config_toml(
        tmp_path,
        '[modules.utility-skills]\nprovisioned_by = "steward"\n'
        'installer = "bmad-utility-skills-install"\nskills = ["bmad-os-gh-triage"]\n',
    )

    states = module_install_states(cwd=tmp_path)

    assert states["cis"] == "installed"
    assert states["utility-skills"] == "installed"
    assert states["tea"] == "available"
    assert states["manticore"] == "available"
    assert states["bmb"] == "available"


def test_module_install_states_ignores_non_module_custom_config_toml_sections(tmp_path):
    """`[modules.bmm]` / `[modules.skf]` (unrelated custom-config sections
    this file already carries) must not be misread as a registered
    module's install state."""
    _write_custom_config_toml(tmp_path, '[modules.bmm]\nuser_skill_level = "intermediate"\n')

    states = module_install_states(cwd=tmp_path)

    assert states == _ALL_AVAILABLE


def test_module_install_states_malformed_custom_config_toml_raises_toml_decode_error(tmp_path):
    """Mirrors the malformed-YAML precedent above: a malformed `_bmad/
    custom/config.toml` propagates `tomllib.TOMLDecodeError`, not swallowed."""
    _write_custom_config_toml(tmp_path, "[modules.tea\n")

    with pytest.raises(tomllib.TOMLDecodeError):
        module_install_states(cwd=tmp_path)


def test_supported_modules_are_exactly_the_five_wire_decided_names():
    """Story 15.3 / CAP-3: registry is {bmb, tea, cis, utility-skills,
    manticore}; WDS stays skip-only."""
    assert set(_SUPPORTED_MODULES) == {
        "bmb",
        "tea",
        "cis",
        "utility-skills",
        "manticore",
    }
    assert "wds" not in _SUPPORTED_MODULES
    assert "wds" in _SKIPPED_MODULES
    assert "deprecated" in _SKIPPED_MODULES["wds"].lower()


# ── format_module_states (primitive) ─────────────────────────────────────


def test_format_module_states_text_lists_every_name_with_its_state():
    text = format_module_states({"bmb": "installed"}, as_json=False)

    assert "bmb" in text
    assert "installed" in text


def test_format_module_states_json_emits_machine_readable_data():
    text = format_module_states({"bmb": "available"}, as_json=True)

    assert json.loads(text) == {"bmb": "available"}


def test_format_module_states_text_aligns_multiple_names_sorted():
    text = format_module_states({"zeta": "available", "alpha": "installed"}, as_json=False)

    lines = text.splitlines()
    assert lines[0].startswith("alpha")
    assert lines[1].startswith("zeta")
    assert "installed" in lines[0]
    assert "available" in lines[1]


def test_format_module_states_json_multiple_names_sorted():
    text = format_module_states({"zeta": "available", "alpha": "installed"}, as_json=True)

    assert list(json.loads(text).keys()) == ["alpha", "zeta"]


def test_format_module_states_empty_text_is_a_clear_sentence_not_a_blank_string():
    assert format_module_states({}, as_json=False) != ""
    assert "no modules" in format_module_states({}, as_json=False)


def test_format_module_states_empty_json_is_an_empty_object():
    assert json.loads(format_module_states({}, as_json=True)) == {}


# ── ProvisionDuty / CLI dispatch ─────────────────────────────────────────


def test_provision_list_modules_via_cli_reports_available_with_no_config_yaml(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list-modules"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    for name in sorted(_WIRED_NAMES):
        assert name in out
        assert "available" in out
    assert "wds" not in out


def test_provision_list_modules_via_cli_reports_installed_when_bmb_key_present(tmp_path, monkeypatch, capsys):
    _write_bmad_config(tmp_path, "bmb:\n  output_folder: skills\n")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list-modules"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "bmb" in out and "installed" in out


def test_provision_list_modules_json_via_cli_emits_valid_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list-modules", "--json"])

    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload == _ALL_AVAILABLE
    assert "wds" not in payload


def test_provision_list_modules_json_on_malformed_config_yaml_still_emits_valid_json(tmp_path, monkeypatch, capsys):
    """An error raised on `--list-modules`'s own path must honor `--json`."""
    _write_bmad_config(tmp_path, "bmb: [unterminated\n")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list-modules", "--json"])

    assert rc == EXIT_FAILED
    payload = json.loads(capsys.readouterr().err)
    assert "error" in payload


def test_provision_list_modules_non_mapping_config_yaml_via_cli_degrades_to_all_available(
    tmp_path, monkeypatch, capsys
):
    _write_bmad_config(tmp_path, "- just\n- a\n- list\n")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list-modules", "--json"])

    assert rc == EXIT_OK
    assert json.loads(capsys.readouterr().out) == _ALL_AVAILABLE


def test_provision_list_modules_json_on_unreadable_encoding_still_emits_valid_json(tmp_path, monkeypatch, capsys):
    bmad_dir = tmp_path / "_bmad"
    bmad_dir.mkdir(parents=True)
    (bmad_dir / "config.yaml").write_bytes(b"bmb: \xff\xfe invalid utf8\n")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list-modules", "--json"])

    assert rc == EXIT_FAILED
    payload = json.loads(capsys.readouterr().err)
    assert "error" in payload


def test_provision_list_modules_never_writes_to_config_yaml(tmp_path, monkeypatch):
    config = _write_bmad_config(tmp_path, "bmb:\n  output_folder: skills\n")
    before = config.read_text(encoding="utf-8")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    main(["provision", "--list-modules"])

    assert config.read_text(encoding="utf-8") == before


def test_provision_list_modules_never_creates_config_yaml_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    main(["provision", "--list-modules"])

    assert not (tmp_path / "_bmad" / "config.yaml").exists()


def test_provision_list_modules_takes_precedence_over_everything_else(tmp_path, monkeypatch):
    """`--list-modules` is the new first precedence check, ahead of
    `--module` / `--verify` / `--list` — mirrors
    `test_provision_module_takes_precedence_over_verify_and_list`'s own
    shape."""
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    result = ProvisionDuty().run(
        _full_namespace(
            list_modules=True,
            module="nope",
            list=True,
            verify=True,
            runner="bmad-loop",
            env="pyforge-steward",
        )
    )

    assert result.ok is True
    assert "bmb" in result.summary  # --list-modules's own handling ran
    assert "nope" not in result.summary  # never reached --module's handling
    assert "wds" not in result.summary


def test_provision_list_modules_via_cli_reports_both_cis_legacy_and_utility_new_installed(
    tmp_path, monkeypatch, capsys
):
    """The story's own headline AC, via the real CLI: `cis`'s roster entry
    still lives only in the legacy `_bmad/config.yaml`, `utility-skills`'s
    lives only in the new `_bmad/custom/config.toml` -- both report
    installed."""
    _write_bmad_config(tmp_path, "cis:\n  installer: bmad-cis-install\n")
    _write_custom_config_toml(
        tmp_path,
        '[modules.utility-skills]\nprovisioned_by = "steward"\n'
        'installer = "bmad-utility-skills-install"\nskills = ["bmad-os-gh-triage"]\n',
    )
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--list-modules", "--json"])

    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["cis"] == "installed"
    assert payload["utility-skills"] == "installed"
    assert payload["tea"] == "available"
