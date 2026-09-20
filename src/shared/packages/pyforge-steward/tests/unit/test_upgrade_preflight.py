"""Story 14.1 — CAP-1 pre-flight retrodicts the 6.10.0→6.11.0 upgrade traps.

Story 14.7 — CAP-7: the packaged 6.12.0 catalog names skf under
``custom_modules`` and a manifest without ``modules:`` yields no custom-module
findings.

Story 14.8 — CAP-8: a marker-free byte-diff scan of installer-owned skill
files and ``_bmad/scripts/*.py`` finds local edits the marker-based trap-1
mechanism misses (trap 16).

Story 14.9 — CAP-9: ``shims_to_retire`` is a catalog∩installed preview of
what a future ``--no-shims`` apply would remove — computed unconditionally
and never added to ``trap_ids``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pyforge.steward.cli import EXIT_OK, main
from pyforge.steward.upgrade import (
    TRAP_CONFIG_MIGRATION,
    TRAP_FORWARDER,
    TRAP_LEGACY_CUSTOM,
    TRAP_LOCAL_CUSTOMIZATION,
    TRAP_LOCAL_MOD,
    TRAP_PREREQUISITES,
    TRAP_REMOVALS,
    _local_customization_findings,
    build_preflight_report,
    catalog_dir,
    default_installed_package_root,
    format_preflight,
    load_custom_modules,
    load_release_catalog,
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


@pytest.fixture(autouse=True)
def _no_real_home(monkeypatch, tmp_path):
    """Never resolve to the REAL machine's home dir.

    Every ``build_preflight_report``/``apply_bmad_core_upgrade`` call that does
    not pass ``installed_package_root=`` falls through to
    ``default_installed_package_root``'s live ``~/.cache/rattler/cache/pkgs``
    glob. Fixtures in this file are deterministic today only by accident of
    which fake installed-version strings happen to (not) have a real cached
    package on the machine running the tests. A test that deliberately wants
    the real glob passes ``cache_root=`` explicitly (bypassing ``Path.home()``
    entirely) or re-patches ``Path.home`` itself after this fixture runs —
    both keep working since a later ``monkeypatch.setattr`` simply overrides.
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fake-home-never-real")


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
    # Story 46.7: the --pin skf=v2.1.0 question is closed — the catalog pins it.
    assert raw[0]["pin"] == "v2.1.0"
    assert skf.pin == "v2.1.0"
    assert skf.packaged_source == (
        ".pixi/envs/pyforge-guild/lib/node_modules/bmad-module-skill-forge/src"
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


# ── Story 14.8 / CAP-8 fixtures ────────────────────────────────────────────


def _write_package_root(
    root: Path,
    *,
    skill_body: str = "# bmad-dev-auto (packaged)\n",
    script_body: str = "print('packaged helper')\n",
    v6_shim_only: bool = False,
) -> Path:
    """Minimal installed/target package tree: one bmm-skills skill + two scripts."""
    root.mkdir(parents=True, exist_ok=True)
    skills_root = root / "src" / "bmm-skills"
    skill_dir = (
        (skills_root / "v6-shims" / "bmad-dev-auto")
        if v6_shim_only
        else (skills_root / "bmad-dev-auto")
    )
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(skill_body, encoding="utf-8")
    scripts_root = root / "src" / "scripts"
    scripts_root.mkdir(parents=True)
    (scripts_root / "helper.py").write_text(script_body, encoding="utf-8")
    (scripts_root / "resolve_config.py").write_text(
        '"""upstream four-layer resolve_config — no multi-project marker."""\n'
        "def main():\n    pass\n",
        encoding="utf-8",
    )
    return root


def _add_skill_and_script(
    repo: Path,
    *,
    skill_body: str = "# bmad-dev-auto (repo copy)\n",
    script_body: str = "print('repo helper')\n",
    script_name: str = "helper.py",
) -> None:
    skill_dir = repo / ".claude" / "skills" / "bmad-dev-auto"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_body, encoding="utf-8")
    (repo / "_bmad" / "scripts" / script_name).write_text(script_body, encoding="utf-8")


def test_default_installed_package_root_no_cache_dir_returns_none(tmp_path):
    assert default_installed_package_root("6.10.0", cache_root=tmp_path / "no-such-dir") is None


def test_default_installed_package_root_no_matching_version_returns_none(tmp_path):
    cache = tmp_path / "cache"
    other = cache / "bmad-method-6.99.0-abc123" / "lib" / "node_modules" / "bmad-method"
    other.mkdir(parents=True)
    assert default_installed_package_root("6.10.0", cache_root=cache) is None


def test_default_installed_package_root_matches_glob(tmp_path):
    cache = tmp_path / "cache"
    pkg = cache / "bmad-method-6.10.0-abc123" / "lib" / "node_modules" / "bmad-method"
    pkg.mkdir(parents=True)
    assert default_installed_package_root("6.10.0", cache_root=cache) == pkg


def test_default_installed_package_root_home_unresolvable_returns_none(monkeypatch):
    """No HOME / no passwd entry raises RuntimeError from Path.home() — never surfaced."""

    def _raise() -> Path:
        raise RuntimeError("Could not determine home directory")

    monkeypatch.setattr(Path, "home", _raise)
    assert default_installed_package_root("6.10.0") is None


def test_preflight_no_installed_package_root_and_no_cache_match_is_report_only(
    tmp_path, monkeypatch
):
    # Deterministic regardless of the real machine's rattler cache contents.
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fake-home")
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    report = build_preflight_report(repo=repo, target_version="6.11.0")
    assert report.local_customizations == ()
    assert TRAP_LOCAL_CUSTOMIZATION not in report.trap_ids
    assert any("local-customization scan skipped" in n for n in report.notes)


def test_scan_finds_skill_file_edited_in_place(tmp_path):
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    _add_skill_and_script(repo, skill_body="# bmad-dev-auto (LOCALLY EDITED)\n")
    package = _write_package_root(tmp_path / "pkg")
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", installed_package_root=package
    )
    assert TRAP_LOCAL_CUSTOMIZATION in report.trap_ids
    paths = {f.path for f in report.local_customizations}
    assert ".claude/skills/bmad-dev-auto/SKILL.md" in paths
    assert "Local customizations" in format_preflight(report, as_json=False)


def test_scan_skips_v6_shims_skill_dir(tmp_path):
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    _add_skill_and_script(repo, skill_body="# bmad-dev-auto (LOCALLY EDITED)\n")
    package = _write_package_root(tmp_path / "pkg", v6_shim_only=True)
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", installed_package_root=package
    )
    assert not any(
        f.path == ".claude/skills/bmad-dev-auto/SKILL.md"
        for f in report.local_customizations
    )


def test_scan_finds_script_edited_in_place(tmp_path):
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    _add_skill_and_script(repo, script_body="print('LOCALLY EDITED')\n")
    package = _write_package_root(tmp_path / "pkg")
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", installed_package_root=package
    )
    assert any(f.path == "_bmad/scripts/helper.py" for f in report.local_customizations)


def test_scan_script_with_no_packaged_counterpart_is_not_a_finding(tmp_path):
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    (repo / "_bmad" / "scripts" / "bmad_tea_playwright.py").write_text(
        "print('repo-only TEA helper')\n", encoding="utf-8"
    )
    package = _write_package_root(tmp_path / "pkg")
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", installed_package_root=package
    )
    assert not any(
        f.path == "_bmad/scripts/bmad_tea_playwright.py"
        for f in report.local_customizations
    )


def test_scan_excludes_upstream_touched_paths(tmp_path):
    # resolve_config.py is `_write_610_repo`'s trap-1 marker file AND a catalog
    # `upstream_touched_paths` entry — CAP-8 must not double-report it.
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    package = _write_package_root(tmp_path / "pkg")
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", installed_package_root=package
    )
    assert not any(
        f.path == "_bmad/scripts/resolve_config.py" for f in report.local_customizations
    )
    # Still governed by trap 1 (the pre-existing marker-based mechanism).
    assert any(m.path == "_bmad/scripts/resolve_config.py" for m in report.locally_modified)


def test_scan_excludes_skill_shaped_upstream_touched_path(tmp_path):
    """The skill scan honors `exclude` the same way the scripts scan already does."""
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    _add_skill_and_script(repo, skill_body="# bmad-dev-auto (LOCALLY EDITED)\n")
    package = _write_package_root(tmp_path / "pkg")
    catalog = {"upstream_touched_paths": [".claude/skills/bmad-dev-auto/SKILL.md"]}
    findings = _local_customization_findings(repo, package, catalog)
    assert not any(
        f.path == ".claude/skills/bmad-dev-auto/SKILL.md" for f in findings
    )
    # The script-side finding (not named in upstream_touched_paths) still surfaces.
    assert any(f.path == "_bmad/scripts/helper.py" for f in findings)


def test_scan_skips_pycache_noise(tmp_path):
    """CAP-8 trap 16 false-positive fix: __pycache__/*.pyc never fingerprints as a finding."""
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    _add_skill_and_script(repo)
    pycache_dir = repo / ".claude" / "skills" / "bmad-dev-auto" / "__pycache__"
    pycache_dir.mkdir(parents=True)
    (pycache_dir / "helper.cpython-311.pyc").write_bytes(b"repo-only compiled noise")
    package = _write_package_root(tmp_path / "pkg")
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", installed_package_root=package
    )
    assert not any("__pycache__" in f.path for f in report.local_customizations)
    assert not any(f.path.endswith((".pyc", ".pyo")) for f in report.local_customizations)


def test_scan_skips_own_customization_conflict_sibling(tmp_path):
    """A `.customization-conflict` left by a prior conflicted re-apply must not
    self-pollute the next pre-flight scan as a "new" local customization —
    it has no packaged counterpart either, same noise class as __pycache__.
    """
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    _add_skill_and_script(repo)
    conflict_sibling = (
        repo / ".claude" / "skills" / "bmad-dev-auto" / "SKILL.md.customization-conflict"
    )
    conflict_sibling.write_text("<<<<<<< ours\n=======\n>>>>>>> theirs\n", encoding="utf-8")
    package = _write_package_root(tmp_path / "pkg")
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", installed_package_root=package
    )
    assert not any(
        f.path.endswith(".customization-conflict") for f in report.local_customizations
    )


def test_preflight_installed_package_root_bad_path_notes_scan_skipped(tmp_path):
    """An explicit --installed-package-root that isn't a directory must not go silent."""
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    bad_root = tmp_path / "does-not-exist"
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", installed_package_root=bad_root
    )
    assert report.local_customizations == ()
    assert TRAP_LOCAL_CUSTOMIZATION not in report.trap_ids
    notes = " ".join(report.notes)
    assert "local-customization scan skipped" in notes
    assert "is not a directory" in notes


def test_preflight_installed_package_root_wrong_shape_notes_scan_skipped(tmp_path):
    """A real directory that isn't a bmad-method package must not read as verified-clean."""
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    wrong_root = tmp_path / "wrong-shape-root"
    (wrong_root / "some-other-tool").mkdir(parents=True)
    report = build_preflight_report(
        repo=repo, target_version="6.11.0", installed_package_root=wrong_root
    )
    assert report.local_customizations == ()
    assert TRAP_LOCAL_CUSTOMIZATION not in report.trap_ids
    notes = " ".join(report.notes)
    assert "local-customization scan skipped" in notes
    assert "does not look like a bmad-method package" in notes
    text = format_preflight(report, as_json=False)
    assert "(none detected — see Notes below if the scan was skipped)" in text


# ── Story 14.9 / CAP-9 fixtures ────────────────────────────────────────────


def _write_repo_with_skills(root: Path, skill_names: list[str]) -> Path:
    """Minimal installed-shaped repo carrying exactly *skill_names* in its
    skill-manifest.csv (no other CAP-9-irrelevant machinery)."""
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")
    manifest_dir = root / "_bmad" / "_config"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        "installation:\n  version: 9.9.8\n", encoding="utf-8"
    )
    lines = ["canonicalId,name"]
    for name in skill_names:
        lines.append(f'"{name}","{name}"')
    (manifest_dir / "skill-manifest.csv").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return root


def _write_shims_catalog(
    directory: Path, *, version: str = "9.9.9", shims: list[str] | None = None
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{version}.yaml").write_text(
        yaml.safe_dump(
            {
                "version": version,
                "baseline_pair_from": "9.9.8",
                "shims_to_retire": shims or [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return directory


def test_shims_to_retire_is_catalog_installed_intersection_sorted(tmp_path):
    repo = _write_repo_with_skills(
        tmp_path / "repo", ["bmad-dev-auto", "bmad-quick-dev", "bmad-review"]
    )
    catalog_directory = _write_shims_catalog(
        tmp_path / "catalog",
        shims=["bmad-quick-dev", "bmad-dev-auto", "bmad-not-installed"],
    )
    report = build_preflight_report(
        repo=repo,
        target_version="9.9.9",
        installed_version="9.9.8",
        catalog_directory=catalog_directory,
    )
    # Sorted catalog∩installed intersection.
    assert report.shims_to_retire == ("bmad-dev-auto", "bmad-quick-dev")
    # A preview, never a trap — this minimal fixture triggers no other trap.
    assert report.trap_ids == ()


def test_shims_to_retire_empty_when_catalog_and_installed_disjoint(tmp_path):
    repo = _write_repo_with_skills(tmp_path / "repo", ["bmad-review"])
    catalog_directory = _write_shims_catalog(
        tmp_path / "catalog", shims=["bmad-dev-auto", "bmad-quick-dev"]
    )
    report = build_preflight_report(
        repo=repo,
        target_version="9.9.9",
        installed_version="9.9.8",
        catalog_directory=catalog_directory,
    )
    assert report.shims_to_retire == ()
    assert report.trap_ids == ()


def test_shims_to_retire_absent_key_defaults_to_empty(tmp_path):
    """A plain (non-CAP-9) fixture repo against the packaged 6.11.0 catalog
    (no ``shims_to_retire`` key at all) must not error and yields an empty
    preview — the field is unconditional but the key itself is optional."""
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    report = build_preflight_report(repo=repo, target_version="6.11.0")
    assert report.shims_to_retire == ()


def test_real_612_catalog_shims_to_retire_has_21_entries():
    """Story 14.9: the REAL packaged 6.12.0 catalog carries the full 21-entry
    ``shims_to_retire`` list (20 skill-manifest.csv ``v6-shims`` paths plus
    ``bmad-generate-project-context``). Every other test touching
    ``shims_to_retire`` uses a synthetic fixture catalog; this one catches an
    accidental edit to the real list directly (mirrors Story 46.7's
    ``test_real_catalog_pins_skf_v2_1_0`` precedent).
    """
    catalog = load_release_catalog("6.12.0")
    shims = catalog["shims_to_retire"]
    assert len(shims) == 21
    assert "bmad-generate-project-context" in shims
    assert "bmad-dev-auto" in shims


def test_format_preflight_renders_shims_to_retire_section(tmp_path):
    repo = _write_repo_with_skills(tmp_path / "repo", ["bmad-dev-auto"])
    catalog_directory = _write_shims_catalog(tmp_path / "catalog", shims=["bmad-dev-auto"])
    report = build_preflight_report(
        repo=repo,
        target_version="9.9.9",
        installed_version="9.9.8",
        catalog_directory=catalog_directory,
    )
    text = format_preflight(report, as_json=False)
    assert "## Shims to retire (--no-shims candidates) [1]" in text
    assert "- bmad-dev-auto" in text


def test_format_preflight_shims_to_retire_none_when_empty(tmp_path):
    repo = _write_610_repo(tmp_path / "repo", with_legacy_custom=False)
    report = build_preflight_report(repo=repo, target_version="6.11.0")
    text = format_preflight(report, as_json=False)
    assert "## Shims to retire (--no-shims candidates) [0]" in text


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
