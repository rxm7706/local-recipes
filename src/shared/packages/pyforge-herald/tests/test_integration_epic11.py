"""Story 11.1: end-to-end integration test across all three real Moments
(Progress/Success/Notice, Epics 8-10), exercised only through what is
actually built -- no webhook, no live database, no cron (see
``docs/dreams/herald-moments-2-4-live-backend.md``).

The scaled-down honest form of the original AC's "PR merge -> progress
created -> claim auto-extracted -> claim published -> success visible in
web" scenario: an operator runs ``herald progress --update``, then
``herald success create``/``publish``, then ``herald notice author
--publish`` by hand (there is no webhook to fire these automatically), and
this test walks that exact operator workflow end to end, verifying each
Moment is visible via its own ``--json`` listing AND via the static-
snapshot-export scripts the web dashboard's tabs read from (there is no
live REST API -- "automation" here means these export scripts, not a live
pipeline)."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pyforge.herald import auth, cli, evidence

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_WEB_ROOT = _PACKAGE_ROOT / "web"
_SYNC_PROGRESS_SCRIPT = _WEB_ROOT / "scripts" / "sync-progress.mjs"
_SYNC_PROGRESS_DEST = _WEB_ROOT / "public" / "progress.json"


def _load_script(name: str, relative_path: str):
    """Import a ``scripts/*.py`` build-time tool by file path -- mirrors
    ``test_export_web_snapshot.py``'s own loader (these scripts live
    outside the ``pyforge.herald`` package, so a normal import can't reach
    them)."""
    script_path = _PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


export_web_snapshot = _load_script(
    "export_web_snapshot_epic11", "scripts/export_web_snapshot.py"
)
export_notices_snapshot = _load_script(
    "export_notices_snapshot_epic11", "scripts/export_notices_snapshot.py"
)


@pytest.fixture(autouse=True)
def _operator_and_stubbed_validation(monkeypatch):
    """Every write command in this workflow requires the operator role
    (AD-16); every evidence link here is a placeholder, not a real
    endpoint -- stub validation so ``deny_network`` never has cause to
    fire."""
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "operator:tok")
    monkeypatch.setattr(auth, "confirm", lambda *_a, **_k: True)
    monkeypatch.setattr(evidence, "validate_for_publish", lambda url, **_k: None)

    class _AlwaysValid:
        is_valid = True

    monkeypatch.setattr(evidence, "validate_link", lambda url, **_k: _AlwaysValid())


@pytest.fixture(autouse=True)
def _isolate_cwd(monkeypatch, tmp_path):
    """``progress``/``notice`` resolve local storage against ``Path.cwd()``
    (mirrors ``test_cli_progress.py``'s own isolation fixture); ``success``
    takes ``--repo-root`` explicitly below, pointed at the same
    ``tmp_path``, so all three Moments share one local ``.herald/`` tree."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _cleanup_web_public():
    """``sync-progress.mjs``'s destination is fixed relative to its own
    script location (the real, checked-out ``web/public/`` dir) -- there is
    no override. ``web/public/*.json`` is gitignored generated data (see
    ``web/.gitignore``), so writing there is harmless, but this test still
    cleans up after itself rather than leaving a stray file for the next
    run to trip over."""
    yield
    if _SYNC_PROGRESS_DEST.exists():
        _SYNC_PROGRESS_DEST.unlink()


@pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is not declared in the pyforge-herald pixi feature's "
    "dependencies -- this test's sync-progress.mjs subprocess only runs "
    "when node happens to be on PATH from ambient shell state",
)
def test_all_three_moments_end_to_end(tmp_path, capsys):
    repo_root = tmp_path

    # --- Moment 2: Progress -------------------------------------------
    rc = cli.main(
        [
            "progress",
            "warden",
            "--update",
            "--shipped",
            "Harness Policy Gate",
            "--compute-hours",
            "3.5",
            "--token-spend",
            "42000",
            "--wall-clock-hours",
            "6",
            "--unblock-narrative",
            "none",
        ]
    )
    assert rc == 0
    capsys.readouterr()

    rc = cli.main(["progress", "--json"])
    assert rc == 0
    progress_lines = [
        json.loads(line) for line in capsys.readouterr().out.splitlines() if line
    ]
    assert len(progress_lines) == 1
    assert progress_lines[0]["station"] == "warden"
    assert progress_lines[0]["shipped_capabilities"] == ["Harness Policy Gate"]

    # --- Moment 3: Success -----------------------------------------------
    rc = cli.main(
        [
            "success",
            "--repo-root",
            str(repo_root),
            "create",
            "Warden Harness Policy",
            "--shipped-date",
            "2026-08-08",
            "--evidence-test-results",
            "https://ci.example/warden/harness-policy",
        ]
    )
    assert rc == 0
    create_out = capsys.readouterr().out
    claim_id = create_out.split("created draft claim ", 1)[1].split(" ", 1)[0]

    rc = cli.main(
        [
            "success",
            "--repo-root",
            str(repo_root),
            "publish",
            claim_id,
            "--thesis",
            "Shipped the harness policy gate",
        ]
    )
    assert rc == 0
    capsys.readouterr()

    rc = cli.main(["success", "--repo-root", str(repo_root), "--json", "list"])
    assert rc == 0
    claim_lines = [
        json.loads(line) for line in capsys.readouterr().out.splitlines() if line
    ]
    assert len(claim_lines) == 1
    assert claim_lines[0]["id"] == claim_id
    assert claim_lines[0]["status"] == "published"

    # --- Moment 4: Notice --------------------------------------------------
    rc = cli.main(
        [
            "notice",
            "author",
            "--type",
            "deprecation",
            "--component",
            "warden-legacy-hook",
            "--what",
            "the legacy pre-commit hook is deprecated",
            "--why",
            "superseded by the harness policy gate",
            "--migration",
            "remove the hook from .pre-commit-config.yaml",
            "--deadline",
            "2026-09-01",
            "--publish",
        ]
    )
    assert rc == 0
    capsys.readouterr()

    rc = cli.main(["notice", "--json", "list"])
    assert rc == 0
    notice_payload = json.loads(capsys.readouterr().out.strip())
    assert len(notice_payload) == 1
    assert notice_payload[0]["component"] == "warden-legacy-hook"
    assert notice_payload[0]["status"] == "published"

    # --- automation: the three static-snapshot-export scripts ------------

    # sync-progress.mjs (Story 8.4) -- a real `node` subprocess, no stub;
    # this script does no network I/O of its own, only local fs reads.
    progress_json_path = repo_root / ".herald" / "progress.json"
    result = subprocess.run(
        ["node", str(_SYNC_PROGRESS_SCRIPT), str(progress_json_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert _SYNC_PROGRESS_DEST.exists()
    synced_progress = json.loads(_SYNC_PROGRESS_DEST.read_text(encoding="utf-8"))
    assert synced_progress
    assert synced_progress[0]["station"] == "warden"

    # export_web_snapshot.py's export_success_snapshot (Story 9.4)
    out_dir = tmp_path / "web-out"
    success_out = export_web_snapshot.export_success_snapshot(
        repo_root=repo_root, out_dir=out_dir
    )
    exported_claims = json.loads(success_out.read_text(encoding="utf-8"))
    assert exported_claims
    assert exported_claims[0]["id"] == claim_id

    # export_notices_snapshot.py (Story 10.5)
    notices_out = out_dir / "notices.json"
    count = export_notices_snapshot.export_snapshot(repo_root, notices_out)
    assert count == 1
    exported_notices = json.loads(notices_out.read_text(encoding="utf-8"))
    assert exported_notices[0]["component"] == "warden-legacy-hook"
