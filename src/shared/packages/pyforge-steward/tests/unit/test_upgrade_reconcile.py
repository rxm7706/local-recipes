"""Story 14.3 — CAP-3: clobbered custom surfaces detected and re-applied/flagged.

Story 14.8 — CAP-8 amendment: the CAP-3 restore additionally replays the
old→new upstream delta onto the restored bytes (clean merge or conflict-noted
plain restore), gated on both package roots being available; roots missing
stays byte-identical to pre-14.8 behavior.
"""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from pyforge.steward.upgrade import (
    apply_bmad_core_upgrade,
    list_installer_bak_files,
    reconcile_clobbered_custom_surfaces,
    snapshot_repo_custom_surfaces,
    verify_six_layer_resolution,
)


@pytest.fixture(autouse=True)
def _no_real_home(monkeypatch, tmp_path):
    """Never resolve to the REAL machine's home dir.

    Every ``apply_bmad_core_upgrade`` call that does not pass
    ``installed_package_root=`` falls through to
    ``default_installed_package_root``'s live ``~/.cache/rattler/cache/pkgs``
    glob. Fixtures in this file are deterministic today only by accident of
    which fake installed-version strings happen to (not) have a real cached
    package on the machine running the tests. A test that deliberately wants
    the real glob passes ``cache_root=`` explicitly (bypassing ``Path.home()``
    entirely) or re-patches ``Path.home`` itself after this fixture runs —
    both keep working since a later ``monkeypatch.setattr`` simply overrides.
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "fake-home-never-real")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


_CUSTOM_RESOLVE = textwrap.dedent(
    '''\
    #!/usr/bin/env python3
    """REPO-CUSTOM resolve_config with multi-project layers 5/6."""
    import argparse
    import json
    import os
    import sys
    from pathlib import Path

    # Markers CAP-1/CAP-3 look for:
    BMAD_ACTIVE_PROJECT = True
    _MARKER = ".active-project"
    _PROJECTS = "_bmad-output/projects"
    _LAYER5 = ".bmad-config.toml"

    def main() -> int:
        p = argparse.ArgumentParser()
        p.add_argument("--project-root", "-p", required=True)
        p.add_argument("--key", "-k", action="append", default=[])
        p.add_argument("--project")
        p.add_argument("--show-active-project", action="store_true")
        args = p.parse_args()
        root = Path(args.project_root)
        slug = args.project or os.environ.get("BMAD_ACTIVE_PROJECT")
        marker = root / "_bmad" / "custom" / ".active-project"
        if not slug and marker.is_file():
            slug = marker.read_text(encoding="utf-8").strip() or None
        if args.show_active_project:
            sys.stderr.write(f"active_project: {slug or '(none)'}\\n")
        merged: dict = {"layer": "base"}
        if slug:
            proj = root / "_bmad-output" / "projects" / slug
            cfg = proj / ".bmad-config.toml"
            if cfg.is_file():
                for line in cfg.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        merged[k.strip()] = v.strip().strip('"')
            merged["active_project"] = slug
        out = merged
        if args.key:
            out = {k: merged[k] for k in args.key if k in merged}
        print(json.dumps(out, indent=2))
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
    '''
)

_UPSTREAM_RESOLVE = textwrap.dedent(
    '''\
    #!/usr/bin/env python3
    """upstream four-layer resolve_config — no multi-project marker."""
    import argparse
    import json

    def main() -> int:
        argparse.ArgumentParser().parse_args()
        print("{}")
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
    '''
)

_CATALOG = {
    "upstream_touched_paths": ["_bmad/scripts/resolve_config.py"],
    "repo_custom_markers": ["BMAD_ACTIVE_PROJECT", ".active-project"],
}


def _write_repo(root: Path, *, resolve_body: str = _CUSTOM_RESOLVE) -> Path:
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")

    manifest_dir = root / "_bmad" / "_config"
    manifest_dir.mkdir(parents=True)
    # CAP-6 (Story 14.6): apply selects every module the manifest lists; an
    # empty list is a refusal, so the fixture names the real trio.
    (manifest_dir / "manifest.yaml").write_text(
        "installation:\n  version: 6.10.0\n"
        "modules:\n"
        "  - name: core\n    version: 6.10.0\n    source: built-in\n"
        "  - name: bmm\n    version: 6.10.0\n    source: built-in\n"
        "  - name: skf\n    version: main\n    source: custom\n",
        encoding="utf-8",
    )
    (manifest_dir / "skill-manifest.csv").write_text(
        'canonicalId,name\n"bmad-dev-auto","bmad-dev-auto"\n',
        encoding="utf-8",
    )

    (root / "_bmad" / "config.toml").write_text("team = true\n", encoding="utf-8")
    scripts = root / "_bmad" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "resolve_config.py").write_text(resolve_body, encoding="utf-8")

    (root / "_bmad" / "bmm").mkdir(parents=True)
    (root / "_bmad" / "bmm" / ".keep").write_text("owned\n", encoding="utf-8")
    (root / "_bmad" / "core").mkdir(parents=True)
    (root / "_bmad" / "core" / ".keep").write_text("owned\n", encoding="utf-8")
    custom = root / "_bmad" / "custom"
    custom.mkdir(parents=True)
    (custom / "config.toml").write_text("team = true\n", encoding="utf-8")

    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "test")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture baseline")
    return root


def _fake_installer(
    path: Path,
    *,
    clobber_resolve: bool = False,
    leave_bak: bool = False,
    clobber_body: str = _UPSTREAM_RESOLVE,
) -> Path:
    body = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import pathlib, sys
        repo = pathlib.Path.cwd()
        assert sys.argv[1:4] == ["install", "--action", "update"]
        (repo / "_bmad" / "bmm" / "updated.txt").write_text("from-installer\\n")
        resolve = repo / "_bmad" / "scripts" / "resolve_config.py"
        if {clobber_resolve!r}:
            if {leave_bak!r} and resolve.is_file():
                (repo / "_bmad" / "scripts" / "resolve_config.py.bak").write_bytes(
                    resolve.read_bytes()
                )
            resolve.write_text({clobber_body!r})
        sys.exit(0)
        """
    )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_snapshot_captures_marked_resolve(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    snaps = snapshot_repo_custom_surfaces(repo, _CATALOG)
    assert "_bmad/scripts/resolve_config.py" in snaps
    assert "BMAD_ACTIVE_PROJECT" in snaps["_bmad/scripts/resolve_config.py"]


def test_reconcile_restores_from_bak(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    snaps = snapshot_repo_custom_surfaces(repo, _CATALOG)
    resolve = repo / "_bmad" / "scripts" / "resolve_config.py"
    bak = repo / "_bmad" / "scripts" / "resolve_config.py.bak"
    bak.write_text(snaps["_bmad/scripts/resolve_config.py"], encoding="utf-8")
    resolve.write_text(_UPSTREAM_RESOLVE, encoding="utf-8")

    report = reconcile_clobbered_custom_surfaces(repo, _CATALOG, pre_apply_snapshots=snaps)
    assert report.all_clear
    finding = report.findings[0]
    assert finding.action == "restored_from_bak"
    assert finding.markers_after
    assert any(p.endswith("resolve_config.py.bak") for p in report.bak_files_accounted)
    assert "BMAD_ACTIVE_PROJECT" in resolve.read_text(encoding="utf-8")


def test_reconcile_restores_from_snapshot_when_bak_useless(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    snaps = snapshot_repo_custom_surfaces(repo, _CATALOG)
    resolve = repo / "_bmad" / "scripts" / "resolve_config.py"
    bak = repo / "_bmad" / "scripts" / "resolve_config.py.bak"
    bak.write_text(_UPSTREAM_RESOLVE, encoding="utf-8")
    resolve.write_text(_UPSTREAM_RESOLVE, encoding="utf-8")

    report = reconcile_clobbered_custom_surfaces(repo, _CATALOG, pre_apply_snapshots=snaps)
    assert report.all_clear
    assert report.findings[0].action == "restored_from_snapshot"
    assert "BMAD_ACTIVE_PROJECT" in resolve.read_text(encoding="utf-8")
    assert any("bak" in n for n in report.notes)


def test_reconcile_flags_when_unrecoverable(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    snaps = {"_bmad/scripts/resolve_config.py": "no markers here\n"}
    resolve = repo / "_bmad" / "scripts" / "resolve_config.py"
    resolve.write_text(_UPSTREAM_RESOLVE, encoding="utf-8")

    report = reconcile_clobbered_custom_surfaces(repo, _CATALOG, pre_apply_snapshots=snaps)
    assert report.all_clear is False
    assert report.findings[0].action == "flagged"


def test_verify_six_layers_runtime_with_full_script(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    ok_env, ok_marker, notes = verify_six_layer_resolution(repo, resolve_rel="_bmad/scripts/resolve_config.py")
    assert ok_env and ok_marker
    assert not any("failed" in n for n in notes)


def test_list_installer_bak_files(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    bak = repo / "_bmad" / "scripts" / "resolve_config.py.bak"
    bak.write_text("x\n", encoding="utf-8")
    found = list_installer_bak_files(repo, ["_bmad/scripts/resolve_config.py"])
    assert found == ("_bmad/scripts/resolve_config.py.bak",)


def test_apply_clobber_resolve_restores_and_accounts_bak(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    installer = _fake_installer(tmp_path / "fake-bmad-method", clobber_resolve=True, leave_bak=True)
    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_bin=str(installer),
        branch="review/cap3",
    )
    assert report.installer_exit == 0
    assert report.custom_identical is True
    assert report.reconcile is not None
    assert report.reconcile.all_clear
    actions = {f.action for f in report.reconcile.findings}
    assert "restored_from_bak" in actions or "restored_from_snapshot" in actions
    assert any("bak" in p for p in report.reconcile.bak_files_accounted)
    body = (repo / "_bmad" / "scripts" / "resolve_config.py").read_text(encoding="utf-8")
    assert "BMAD_ACTIVE_PROJECT" in body
    assert "_bmad-output/projects" in body


# ── Story 14.8 / CAP-8 amendment: delta-replay onto the CAP-3 restore ──────

# Base/theirs carry NO markers (pristine upstream shape) so the clobber is
# actually detected (``after`` markers-present must be False); only the
# repo's own pre-apply snapshot (``ours``) carries them, appended at the end.
# ``MID`` is an unchanged context line between LINE1/LINE2 so git's diff3
# treats their edits as two independent, non-adjacent hunks (adjacent-line
# edits on both sides collapse into one overlapping — conflicting — hunk).
_DELTA_BASE = 'LINE1 = "same"\nMID = "same"\nLINE2 = "same"\nTRAILER = "same"\n'
_DELTA_OURS = (
    'LINE1 = "custom"\n'
    'MID = "same"\n'
    'LINE2 = "same"\n'
    'TRAILER = "same"\n'
    "BMAD_ACTIVE_PROJECT = True\n"
    'MARKER = ".active-project"\n'
)
_DELTA_THEIRS_CLEAN = 'LINE1 = "same"\nMID = "same"\nLINE2 = "new"\nTRAILER = "same"\n'
_DELTA_THEIRS_CONFLICT = 'LINE1 = "new-upstream"\nMID = "same"\nLINE2 = "same"\nTRAILER = "same"\n'


def _write_scripts_package(root: Path, *, resolve_body: str) -> Path:
    """Minimal package tree with just ``src/scripts/resolve_config.py``."""
    scripts = root / "src" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "resolve_config.py").write_text(resolve_body, encoding="utf-8")
    return root


def test_reconcile_delta_replay_clean(tmp_path):
    repo = _write_repo(tmp_path / "repo", resolve_body=_DELTA_OURS)
    snaps = {"_bmad/scripts/resolve_config.py": _DELTA_OURS}
    resolve = repo / "_bmad" / "scripts" / "resolve_config.py"
    # Simulate the core installer clobbering it back to the pristine base shape.
    resolve.write_text(_DELTA_BASE, encoding="utf-8")

    installed_root = _write_scripts_package(tmp_path / "installed-pkg", resolve_body=_DELTA_BASE)
    target_root = _write_scripts_package(tmp_path / "target-pkg", resolve_body=_DELTA_THEIRS_CLEAN)

    report = reconcile_clobbered_custom_surfaces(
        repo,
        _CATALOG,
        pre_apply_snapshots=snaps,
        installed_package_root=installed_root,
        package_root=target_root,
    )
    finding = report.findings[0]
    assert finding.action == "restored_from_snapshot"
    assert "upstream delta replayed" in finding.detail
    body = resolve.read_text(encoding="utf-8")
    assert 'LINE1 = "custom"' in body
    assert 'LINE2 = "new"' in body
    assert report.all_clear is True


def test_reconcile_delta_replay_conflict_keeps_plain_restore(tmp_path):
    repo = _write_repo(tmp_path / "repo", resolve_body=_DELTA_OURS)
    snaps = {"_bmad/scripts/resolve_config.py": _DELTA_OURS}
    resolve = repo / "_bmad" / "scripts" / "resolve_config.py"
    resolve.write_text(_DELTA_BASE, encoding="utf-8")

    installed_root = _write_scripts_package(tmp_path / "installed-pkg", resolve_body=_DELTA_BASE)
    target_root = _write_scripts_package(tmp_path / "target-pkg", resolve_body=_DELTA_THEIRS_CONFLICT)

    report = reconcile_clobbered_custom_surfaces(
        repo,
        _CATALOG,
        pre_apply_snapshots=snaps,
        installed_package_root=installed_root,
        package_root=target_root,
    )
    finding = report.findings[0]
    assert finding.action == "restored_from_snapshot"
    assert "upstream delta conflict (see notes)" in finding.detail
    assert any("upstream delta conflict for" in n for n in report.notes)
    # Plain restore kept — no merge bytes written, no conflict sibling either.
    assert resolve.read_text(encoding="utf-8") == _DELTA_OURS
    conflict_sibling = repo / "_bmad" / "scripts" / "resolve_config.py.customization-conflict"
    assert not conflict_sibling.exists()
    # An unresolved upstream-delta conflict must not report as clear even
    # though the plain-restored bytes still carry the repo-custom markers.
    assert report.all_clear is False


def test_apply_clobber_resolve_delta_replay_conflict_gates_all_clear_false(tmp_path):
    """The delta-replay conflict gate must hold through the real apply path.

    `test_reconcile_delta_replay_conflict_keeps_plain_restore` above proves
    the gate by calling `reconcile_clobbered_custom_surfaces` directly; this
    proves the wiring that threads `installed_package_root`/`package_root`
    from `apply_bmad_core_upgrade` into that call (and its `all_clear` up
    into `UpgradeDuty`'s `ok`) is itself intact end-to-end.
    """
    repo = _write_repo(tmp_path / "repo", resolve_body=_DELTA_OURS)
    installer = _fake_installer(
        tmp_path / "fake-bmad-method",
        clobber_resolve=True,
        clobber_body=_DELTA_BASE,
    )
    installed_root = _write_scripts_package(tmp_path / "installed-pkg", resolve_body=_DELTA_BASE)
    target_root = _write_scripts_package(tmp_path / "target-pkg", resolve_body=_DELTA_THEIRS_CONFLICT)

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_bin=str(installer),
        branch="review/cap3-cap8-wiring",
        installed_package_root=installed_root,
        package_root=target_root,
    )
    assert report.installer_exit == 0
    assert report.reconcile is not None
    finding = report.reconcile.findings[0]
    assert "upstream delta conflict" in finding.detail
    assert report.reconcile.all_clear is False


def test_reconcile_delta_replay_skipped_when_package_missing_match(tmp_path):
    """Both roots supplied, but neither ships a matching resolve_config.py — noted, not silent."""
    repo = _write_repo(tmp_path / "repo")
    snaps = snapshot_repo_custom_surfaces(repo, _CATALOG)
    resolve = repo / "_bmad" / "scripts" / "resolve_config.py"
    resolve.write_text(_UPSTREAM_RESOLVE, encoding="utf-8")

    installed_root = tmp_path / "installed-pkg-empty"
    (installed_root / "src" / "scripts").mkdir(parents=True)
    target_root = tmp_path / "target-pkg-empty"
    (target_root / "src" / "scripts").mkdir(parents=True)

    report = reconcile_clobbered_custom_surfaces(
        repo,
        _CATALOG,
        pre_apply_snapshots=snaps,
        installed_package_root=installed_root,
        package_root=target_root,
    )
    finding = report.findings[0]
    assert finding.action == "restored_from_snapshot"
    assert "upstream delta" not in finding.detail
    assert any("delta-replay skipped for" in n for n in report.notes)
    assert "BMAD_ACTIVE_PROJECT" in resolve.read_text(encoding="utf-8")
    assert report.all_clear is True


def test_reconcile_roots_absent_is_byte_identical_to_pre_14_8(tmp_path):
    """Regression guard: no roots passed anywhere behaves exactly as before 14.8."""
    repo = _write_repo(tmp_path / "repo")
    snaps = snapshot_repo_custom_surfaces(repo, _CATALOG)
    resolve = repo / "_bmad" / "scripts" / "resolve_config.py"
    bak = repo / "_bmad" / "scripts" / "resolve_config.py.bak"
    bak.write_text(_UPSTREAM_RESOLVE, encoding="utf-8")
    resolve.write_text(_UPSTREAM_RESOLVE, encoding="utf-8")

    report = reconcile_clobbered_custom_surfaces(repo, _CATALOG, pre_apply_snapshots=snaps)
    finding = report.findings[0]
    assert finding.action == "restored_from_snapshot"
    assert "upstream delta" not in finding.detail
    assert "BMAD_ACTIVE_PROJECT" in resolve.read_text(encoding="utf-8")
    assert report.all_clear is True


def test_apply_json_includes_reconcile(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    installer = _fake_installer(tmp_path / "fake-bmad-method", clobber_resolve=False)
    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_bin=str(installer),
        branch="review/cap3-json",
    )
    payload = report.to_dict()
    assert payload["reconcile"] is not None
    assert payload["reconcile"]["all_clear"] is True
    json.loads(json.dumps(payload))
