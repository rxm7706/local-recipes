"""Story 96.1: ``platform-ci-local`` syncs pixi envs before stages run."""

from __future__ import annotations

import json
import os
import re
import subprocess
import textwrap
from pathlib import Path

import pytest
from test_platform_ci_local_concurrency import (
    _marker_env,
    _no_stub_process_outlives_the_test,  # noqa: F401 -- autouse: no test here leaves a process behind (Story 101.1)
    _prepare_stub_root,
    _write_executable,
)

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None
_SCRIPT = (_REPO_ROOT / "scripts" / "platform-ci-local.sh") if _REPO_ROOT else None

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = [
    pytest.mark.live_tree,
    pytest.mark.skipif(
        not (_SCRIPT and _SCRIPT.is_file()),
        reason="scripts/platform-ci-local.sh required",
    ),
]


def _run_script(
    root: Path,
    bin_dir: Path,
    *,
    stub_log: Path,
    args: list[str],
    extra_env: dict[str, str] | None = None,
    use_run_lock: bool = False,
) -> subprocess.CompletedProcess[str]:
    assert _SCRIPT is not None
    run_env = os.environ.copy()
    run_env["PIXI_PROJECT_ROOT"] = str(root)
    run_env["PATH"] = f"{bin_dir}:{run_env.get('PATH', '')}"
    run_env["PLATFORM_CI_LOCAL_ENGINE"] = "docker"
    run_env["PLATFORM_CI_STUB_LOG"] = str(stub_log)
    run_env["PLATFORM_CI_LOCAL_WORK"] = str(root / "work")
    run_env.update(_marker_env(root))
    if use_run_lock:
        run_env["PLATFORM_CI_LOCAL_LOCK"] = str(root / "platform-ci-local.lock")
        run_env["PLATFORM_CI_LOCAL_LOCK_WAIT"] = "120"
    else:
        run_env["PLATFORM_CI_LOCAL_NO_LOCK"] = "1"
    run_env.setdefault("PLATFORM_CI_LOCAL_PG_PORT", "45432")
    run_env.setdefault("PLATFORM_CI_LOCAL_REDIS_PORT", "46379")
    if extra_env:
        run_env.update(extra_env)
    stub_log.parent.mkdir(parents=True, exist_ok=True)
    stub_log.write_text("", encoding="utf-8")
    return subprocess.run(
        ["bash", str(_SCRIPT), *args],
        cwd=root,
        env=run_env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _pixi_install_lines(log_text: str) -> list[str]:
    return [ln for ln in log_text.splitlines() if ln.startswith("pixi install") or ln.startswith("pixi ")]


def _write_env_hash(root: Path, env: str, hash_value: str) -> None:
    meta = root / ".pixi" / "envs" / env / "conda-meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "pixi").write_text(
        json.dumps({"environment_lock_file_hash": hash_value}),
        encoding="utf-8",
    )


def test_ac1_test_syncs_two_envs_in_order_under_lock(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    stub_log = tmp_path / "stub.log"
    proc = _run_script(tmp_path, bin_dir, stub_log=stub_log, args=["--test"], use_run_lock=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    log = stub_log.read_text()
    install_lines = [ln for ln in log.splitlines() if " install " in ln and ln.startswith("pixi ")]
    assert len(install_lines) == 2
    assert "platform-ci-test" in install_lines[0]
    assert "platform-dev" in install_lines[1]
    for ln in install_lines:
        assert "--frozen" in ln
        assert "--manifest-path" in ln
        assert "pixi.toml" in ln
    assert "pyforge-warden" not in log
    initdb_pos = log.find("initdb")
    first_pixi = log.find("pixi ")
    assert first_pixi != -1 and initdb_pos != -1 and first_pixi < initdb_pos
    assert log.count("flock_n=blocked") >= 2


def test_ac1_images_alone_never_calls_pixi(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    stub_log = tmp_path / "stub.log"
    proc = _run_script(tmp_path, bin_dir, stub_log=stub_log, args=["--images"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "pixi " not in stub_log.read_text()


def test_ac1_script_only_frozen_install_via_pixi() -> None:
    assert _SCRIPT is not None
    body = _SCRIPT.read_text(encoding="utf-8")
    # Strip comments for the forbidden check on install lines.
    code_lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith("#")]
    code = "\n".join(code_lines)
    installs = re.findall(r"pixi install --frozen --manifest-path[^\n]*", code)
    assert installs, "expected at least one pixi install --frozen --manifest-path"
    forbidden = (
        "pixi update",
        "pixi add",
        "pixi lock",
        "pixi upgrade",
        "pixi remove",
        "pixi reinstall",
        "pixi install --locked",
        "pixi install -e",
    )
    for bad in forbidden:
        assert bad not in code
    for inst in installs:
        assert "-e " in inst


def test_ac2_stale_env_reports_synced(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    _write_env_hash(tmp_path, "platform-ci-test", "stale")
    stub_log = tmp_path / "stub.log"
    proc = _run_script(
        tmp_path,
        bin_dir,
        stub_log=stub_log,
        args=["--test"],
        extra_env={"PLATFORM_CI_STUB_PIXI_WRITE_HASH": "fresh"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "RESULT: PASS" in proc.stdout
    assert "env platform-ci-test: synced" in proc.stdout
    test_header = proc.stdout.find("== [test]")
    synced_line = proc.stdout.find("env platform-ci-test: synced")
    assert synced_line != -1 and (test_header == -1 or synced_line < test_header)
    work = tmp_path / "work"
    results_path = work / "results.tsv"
    assert results_path.is_file()
    results = results_path.read_text(encoding="utf-8")
    assert "platform-ci-test: synced" in results
    assert (work / "env-sync-platform-ci-test.log").is_file()


def test_ac2_current_when_hash_unchanged(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    _write_env_hash(tmp_path, "platform-ci-test", "same")
    stub_log = tmp_path / "stub.log"
    proc = _run_script(
        tmp_path,
        bin_dir,
        stub_log=stub_log,
        args=["--test"],
        extra_env={"PLATFORM_CI_STUB_PIXI_LEAVE_HASH": "1"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "env platform-ci-test: current" in proc.stdout


def test_ac2_installed_when_no_record(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    meta = tmp_path / ".pixi" / "envs" / "platform-ci-test" / "conda-meta" / "pixi"
    if meta.is_file():
        meta.unlink()
    stub_log = tmp_path / "stub.log"
    proc = _run_script(tmp_path, bin_dir, stub_log=stub_log, args=["--test"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "env platform-ci-test: installed" in proc.stdout


def test_ac2_checked_when_hash_missing_after_install(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    _write_env_hash(tmp_path, "platform-ci-test", "before")
    stub_log = tmp_path / "stub.log"
    # Stand-in writes empty object (no hash key)
    pixi_path = bin_dir / "pixi"
    extra = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        log="${PLATFORM_CI_STUB_LOG:-/dev/null}"
        echo "pixi $*" >> "$log"
        if [[ " $* " == *" install "* ]] && [[ " $* " == *" platform-ci-test "* ]]; then
          root="${PIXI_PROJECT_ROOT}"
          meta="$root/.pixi/envs/platform-ci-test/conda-meta"
          mkdir -p "$meta"
          echo '{}' > "$meta/pixi"
        fi
        exit 0
        """
    )
    _write_executable(pixi_path, extra)
    proc = _run_script(tmp_path, bin_dir, stub_log=stub_log, args=["--test"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "env platform-ci-test: checked" in proc.stdout


def test_ac3_failed_sync_exits_two_without_services(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    stub_log = tmp_path / "stub.log"
    pixi_path = bin_dir / "pixi"
    fail_line = "stub-pixi-install-failed"
    body = textwrap.dedent(
        f"""\
        #!/usr/bin/env bash
        log="${{PLATFORM_CI_STUB_LOG:-/dev/null}}"
        echo "pixi $*" >> "$log"
        if [[ " $* " == *" install "* ]] && [[ " $* " == *" platform-ci-test "* ]]; then
          echo "{fail_line}"
          exit 1
        fi
        exit 0
        """
    )
    _write_executable(pixi_path, body)
    proc = _run_script(
        tmp_path,
        bin_dir,
        stub_log=stub_log,
        args=["--test"],
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "platform-ci-test" in proc.stderr
    assert fail_line in proc.stderr
    log = stub_log.read_text()
    assert "initdb" not in log
    assert log.count(" install ") == 1
    assert "platform-dev" not in log.split("platform-ci-test")[-1]
    assert "RESULT: PASS" not in proc.stdout


def test_matrix_container_syncs_dev_only(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    _write_executable(
        bin_dir / "curl",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            if [[ "$*" == *"/ht/"* ]]; then echo "200"; elif [[ "$*" == *"-w"* ]]; then echo "200"; else echo "200"; fi
            exit 0
            """
        ),
    )
    stub_log = tmp_path / "stub.log"
    proc = _run_script(tmp_path, bin_dir, stub_log=stub_log, args=["--container"])
    log = stub_log.read_text()
    dev_lines = [ln for ln in log.splitlines() if "platform-dev" in ln and "install" in ln]
    assert len(dev_lines) == 1
    assert not any("platform-ci-test" in ln and "install" in ln for ln in log.splitlines())
    assert "env platform-dev:" in proc.stdout


def test_matrix_promotion_syncs_cit_and_warden(tmp_path: Path) -> None:
    bin_dir = _prepare_stub_root(tmp_path)
    stub_log = tmp_path / "stub.log"
    proc = _run_script(tmp_path, bin_dir, stub_log=stub_log, args=["--promotion"])
    log = stub_log.read_text()
    cit_lines = [ln for ln in log.splitlines() if "platform-ci-test" in ln and "install" in ln]
    wrd_lines = [ln for ln in log.splitlines() if "pyforge-warden" in ln and "install" in ln]
    assert len(cit_lines) == 1
    assert len(wrd_lines) == 1
    assert not any("platform-dev" in ln and "install" in ln for ln in log.splitlines())
    assert "env platform-ci-test:" in proc.stdout
    assert "env pyforge-warden:" in proc.stdout
