"""Story 14.1 — CAP-1 pre-flight retrodicts the 6.10.0→6.11.0 upgrade traps.

Story 14.7 — CAP-7: the packaged 6.12.0 catalog names skf under
``custom_modules`` and a manifest without ``modules:`` yields no custom-module
findings.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from pyforge.steward.cli import EXIT_OK, main
from pyforge.steward.upgrade import (
    TRAP_CONFIG_MIGRATION,
    TRAP_FORWARDER,
    TRAP_LEGACY_CUSTOM,
    TRAP_LOCAL_MOD,
    TRAP_PREREQUISITES,
    TRAP_REMOVALS,
    build_preflight_report,
    catalog_dir,
    format_preflight,
    load_custom_modules,
    read_installed_module_sources,
)

_EXPECTED_TRAPS = (
    TRAP_LOCAL_MOD,
    TRAP_LEGACY_CUSTOM,
    TRAP_REMOVALS,
    TRAP_PREREQUISITES,
    TRAP_FORWARDER,
    TRAP_CONFIG_MIGRATION,
)


def _write_610_repo(root: Path, *, with_legacy_custom: bool = True) -> Path:
    """Minimal 6.10-shaped installed state that surfaces traps 1–4, 9, 11."""
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")

    manifest_dir = root / "_bmad" / "_config"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        "installation:\n  version: 6.10.0\n", encoding="utf-8"
    )
    (manifest_dir / "skill-manifest.csv").write_text(
        'canonicalId,name\n'
        '"bmad-dev-auto","bmad-dev-auto"\n'
        '"bmad-check-implementation-readiness","bmad-check-implementation-readiness"\n'
        '"bmad-index-docs","bmad-index-docs"\n',
        encoding="utf-8",
    )

    scripts = root / "_bmad" / "scripts"
    scripts.mkdir(parents=True)
    # Repo-custom layers 5/6 markers (trap 1) — upstream 6.11 lacks these.
    (scripts / "resolve_config.py").write_text(
        '"""repo-custom resolve_config with multi-project layers."""\n'
        "BMAD_ACTIVE_PROJECT = True\n"
        'marker = ".active-project"\n',
        encoding="utf-8",
    )

    custom = root / "_bmad" / "custom"
    custom.mkdir(parents=True)
    if with_legacy_custom:
        (custom / "bmad-dev-auto.toml").write_text(
            "# legacy customization — shim will HALT unattended\n", encoding="utf-8"
        )
    return root


def _write_611_package(root: Path, *, version: str = "6.11.0") -> Path:
    """Minimal upstream package slice: removals.txt + stock resolve_config."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(
        json.dumps({"name": "bmad-method", "version": version}),
        encoding="utf-8",
    )
    (root / "removals.txt").write_text(
        "# Removed skills (skill consolidation)\n"
        "bmad-check-implementation-readiness\n"
        "bmad-agent-tech-writer\n"
        "bmad-index-docs\n"
        "bmad-shard-doc\n",
        encoding="utf-8",
    )
    scripts = root / "src" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "resolve_config.py").write_text(
        '"""upstream four-layer resolve_config — no multi-project marker."""\n'
        "def main():\n    pass\n",
        encoding="utf-8",
    )
    return root


def test_catalog_ships_611():
    path = catalog_dir() / "6.11.0.yaml"
    assert path.is_file()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["version"] == "6.11.0"
    assert data["baseline_pair_from"] == "6.10.0"
    # 6.11.0 predates CAP-7: no custom_modules, and the loader tolerates that.
    assert "custom_modules" not in data
    assert load_custom_modules(data) == ()


def test_catalog_ships_612_custom_modules():
    """Story 14.7: the shipped 6.12.0 catalog's skf entry parses with exactly these keys."""
    path = catalog_dir() / "6.12.0.yaml"
    assert path.is_file()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["version"] == "6.12.0"
    raw = data["custom_modules"]
    assert [entry["name"] for entry in raw] == ["skf"]
    assert set(raw[0]) == {
        "name",
        "own_installer",
        "config_paths",
        "pin",
        "packaged_source",
        "notes",
    }
    (skf,) = load_custom_modules(data)
    assert skf.name == "skf"
    assert skf.own_installer == ("bmad-module-skill-forge", "update")
    assert skf.config_paths == ("_bmad/skf/config.yaml",)
    # The --pin skf=v2.1.0 question stays open — the catalog ships pin: null.
    assert raw[0]["pin"] is None
    assert skf.pin is None
    assert skf.packaged_source == (
        ".pixi/envs/local-recipes/lib/node_modules/bmad-module-skill-forge/src"
    )
    assert "Trap 13" in skf.notes and "Trap 14" in skf.notes
    assert "skf-campaign" in skf.notes


def test_preflight_610_manifest_without_modules_yields_no_custom_module_findings(
    tmp_path,
):
    repo = _write_610_repo(tmp_path / "repo")
    assert read_installed_module_sources(repo) == {}
    report = build_preflight_report(repo=repo, target_version="6.11.0")
    assert report.custom_modules == ()
    assert "(none in catalog or manifest)" in format_preflight(report, as_json=False)


def test_preflight_611_retrodicts_failure_mode_traps(tmp_path):
    """Fixture: 6.10.0 installed + 6.11.0 catalog → traps 1–4, 9, 11."""
    repo = _write_610_repo(tmp_path / "repo")
    package = _write_611_package(tmp_path / "pkg")

    report = build_preflight_report(
        repo=repo,
        target_version="6.11.0",
        package_root=package,
    )

    assert report.installed_version == "6.10.0"
    assert report.target_version == "6.11.0"
    assert tuple(report.trap_ids) == _EXPECTED_TRAPS

    # Trap 1 — locally modified upstream-touched resolve_config.py
    assert any(
        m.path == "_bmad/scripts/resolve_config.py" for m in report.locally_modified
    )

    # Trap 2 — legacy custom halt
    assert any("bmad-dev-auto.toml" in c.path for c in report.legacy_custom)

    # Trap 3 — removals.txt deletions
    for name in (
        "bmad-check-implementation-readiness",
        "bmad-agent-tech-writer",
        "bmad-index-docs",
        "bmad-shard-doc",
    ):
        assert name in report.removals

    # Trap 4 — uv (+ python >= 3.11)
    prereq_names = {p.name for p in report.hard_prerequisites}
    assert "uv" in prereq_names
    assert "python" in prereq_names

    # Trap 9 — forwarder contract / suite min
    assert any(f.skill == "bmad-dev-auto" for f in report.forwarder_changes)
    fwd = next(f for f in report.forwarder_changes if f.skill == "bmad-dev-auto")
    assert fwd.suite_min_versions.get("bmad-loop") == "0.9.1"

    # Trap 11 — migration-not-cutover
    assert report.config_migration is not None
    assert report.config_migration.status == "migration-not-cutover"

    # Renames carry shim disposition
    renames = [c for c in report.skill_changes if c.kind == "rename"]
    assert any(
        c.name == "bmad-dev-auto"
        and c.to == "bmad-build-auto"
        and c.shim_disposition == "forward-with-legacy-custom-halt"
        for c in renames
    )


def test_preflight_without_legacy_custom_omits_trap_2(tmp_path):
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    report = build_preflight_report(repo=repo, target_version="6.11.0")
    assert TRAP_LEGACY_CUSTOM not in report.trap_ids
    assert TRAP_LOCAL_MOD in report.trap_ids
    assert TRAP_REMOVALS in report.trap_ids


def test_format_preflight_text_names_traps(tmp_path):
    repo = _write_610_repo(tmp_path / "repo")
    report = build_preflight_report(repo=repo, target_version="6.11.0")
    text = format_preflight(report, as_json=False)
    assert "report-only" in text
    assert "trap 1" in text
    assert "trap 3" in text
    assert "uv" in text


def test_cli_bmad_core_json_report_only(tmp_path, capsys):
    repo = _write_610_repo(tmp_path / "repo")
    rc = main(
        [
            "upgrade",
            "bmad-core",
            "--target",
            "6.11.0",
            "--repo-root",
            str(repo),
            "--installed-version",
            "6.10.0",
            "--json",
        ]
    )
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["installed_version"] == "6.10.0"
    assert payload["target_version"] == "6.11.0"
    assert set(payload["trap_ids"]) == set(_EXPECTED_TRAPS)


def test_preflight_warns_on_package_version_mismatch(tmp_path):
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    package = _write_611_package(tmp_path / "pkg", version="6.12.0")
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", package_root=package
    )
    assert any("package.json version is 6.12.0" in n for n in report.notes)


def test_skill_adds_do_not_duplicate_rename_targets(tmp_path):
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    report = build_preflight_report(repo=repo, target_version="6.11.0")
    adds = {c.name for c in report.skill_changes if c.kind == "add"}
    rename_tos = {c.to for c in report.skill_changes if c.kind == "rename"}
    assert adds.isdisjoint(rename_tos)
    assert "bmad-review" in adds


def test_cli_refuses_unknown_target(tmp_path, capsys):
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    rc = main(
        [
            "upgrade",
            "bmad-core",
            "--target",
            "9.9.9",
            "--repo-root",
            str(repo),
        ]
    )
    assert rc != EXIT_OK
    err = capsys.readouterr()
    combined = err.out + err.err
    assert "no release catalog" in combined


def test_preflight_never_mutates_tree(tmp_path):
    repo = _write_610_repo(tmp_path / "repo")
    before = {
        p.relative_to(repo): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file()
    }
    build_preflight_report(repo=repo, target_version="6.11.0")
    after = {
        p.relative_to(repo): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file()
    }
    assert before == after
