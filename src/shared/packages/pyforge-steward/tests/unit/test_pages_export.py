"""Story 102.4 (CAP-168): the Pages build mounts atlas's Kedro-Viz export from a workflow artifact.

The selection (``pages.newest_export_run``) runs on recorded ``gh`` JSON; the step's script
(``scripts/pages_artifact_download.py``) runs on a fake ``gh`` and a scratch root. No test calls a
live ``gh``.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from pyforge.steward.pages import KEDRO_VIZ_ARTIFACT, newest_export_run

REPO_ROOT = Path(__file__).resolve().parents[6]
_SCRIPT = REPO_ROOT / "scripts" / "pages_artifact_download.py"
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"

_RUNS = [
    {"databaseId": 303, "createdAt": "2026-10-15T09:00:00Z", "conclusion": "success"},
    {"databaseId": 302, "createdAt": "2026-10-14T09:00:00Z", "conclusion": "success"},
    {"databaseId": 301, "createdAt": "2026-10-13T09:00:00Z", "conclusion": "success"},
]


def _artifacts(*, name: str = KEDRO_VIZ_ARTIFACT, expired: bool = False) -> dict:
    return {"total_count": 1, "artifacts": [{"id": 9, "name": name, "expired": expired, "size_in_bytes": 11_000_000}]}


# --- AC1: selection --------------------------------------------------------------------------------


def test_ac1_the_newest_successful_run_with_a_live_artifact_wins() -> None:
    by_run = {303: _artifacts(), 302: _artifacts(), 301: _artifacts()}
    assert newest_export_run(_RUNS, by_run) == 303  # noqa: PLR2004


@pytest.mark.parametrize(
    ("runs", "by_run"),
    [
        ([], {}),
        (_RUNS, {303: _artifacts(name="something-else"), 302: {"artifacts": []}, 301: {"total_count": 0}}),
        (_RUNS, {303: _artifacts(expired=True), 302: _artifacts(expired=True), 301: _artifacts(expired=True)}),
    ],
    ids=["no-runs", "no-artifact", "expired"],
)
def test_ac1_none_when_nothing_mountable(runs: list, by_run: dict) -> None:
    assert newest_export_run(runs, by_run) is None


def test_ac1_an_expired_newest_falls_back_to_an_older_live_one() -> None:
    assert newest_export_run(_RUNS, {303: _artifacts(expired=True), 302: _artifacts()}) == 302  # noqa: PLR2004


def test_ac1_a_run_that_did_not_succeed_is_ignored() -> None:
    runs = [{**_RUNS[0], "conclusion": "failure"}, *_RUNS[1:]]
    by_run = {303: _artifacts(), 302: _artifacts()}
    assert newest_export_run(runs, by_run) == 302  # noqa: PLR2004


def test_ac1_order_is_by_created_at_not_listing_order() -> None:
    assert newest_export_run(list(reversed(_RUNS)), {r["databaseId"]: _artifacts() for r in _RUNS}) == 303  # noqa: PLR2004


# --- the step's script ------------------------------------------------------------------------------


def _load_script():
    spec = importlib.util.spec_from_file_location("pages_artifact_download_under_test", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeGh:
    def __init__(self, answers: dict[str, subprocess.CompletedProcess[str]]) -> None:
        self.answers = answers
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        for key, proc in self.answers.items():
            if " ".join(argv).startswith(key):
                return proc
        return subprocess.CompletedProcess(argv, 127, "", f"no fake for {argv}")


def _ok(payload: object) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 0, json.dumps(payload), "")


def _run_script(
    tmp_path: Path, gh: FakeGh, *, flag_on: bool = True, extra: list[str] | None = None
) -> tuple[int, Path]:
    env_file = tmp_path / "github_env"
    code = _load_script().main(
        ["--github-env", str(env_file), *(extra or [])], runner=gh, flag_on=flag_on, root=tmp_path
    )
    return code, env_file


def test_ac2_present_downloads_into_the_mount_source_and_exports_the_run(tmp_path: Path, capsys) -> None:
    gh = FakeGh(
        {
            "gh run list": _ok(_RUNS),
            "gh api repos/{owner}/{repo}/actions/runs/303/artifacts": _ok(_artifacts()),
            "gh run download": subprocess.CompletedProcess([], 0, "", ""),
        }
    )
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert gh.calls[0] == [
        "gh",
        "run",
        "list",
        "--workflow",
        "kedro-viz-publish.yml",
        "--status",
        "success",
        "--limit",
        "10",
        "--json",
        "databaseId,createdAt,conclusion",
    ]
    assert gh.calls[-1] == ["gh", "run", "download", "303", "-n", "kedro-viz-export", "-D", "docs/dashboard/kedro-viz"]
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "KEDRO_VIZ_EXPORT=present",
        "KEDRO_VIZ_EXPORT_RUN=303",
        "KEDRO_VIZ_EXPORT_AT=2026-10-15T09:00:00Z",
    ]
    assert "run 303" in capsys.readouterr().out


def test_ac2_it_stops_reading_artifacts_at_the_first_live_one(tmp_path: Path) -> None:
    gh = FakeGh(
        {
            "gh run list": _ok(_RUNS),
            "gh api repos/{owner}/{repo}/actions/runs/303/artifacts": _ok(_artifacts(expired=True)),
            "gh api repos/{owner}/{repo}/actions/runs/302/artifacts": _ok(_artifacts()),
            "gh run download": subprocess.CompletedProcess([], 0, "", ""),
        }
    )
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert not any("runs/301/" in " ".join(call) for call in gh.calls)
    assert "KEDRO_VIZ_EXPORT_RUN=302" in env_file.read_text(encoding="utf-8")


@pytest.mark.parametrize("artifacts", [{"artifacts": []}, _artifacts(expired=True)], ids=["no-artifact", "expired"])
def test_ac3_absent_is_a_normal_build(tmp_path: Path, capsys, artifacts: dict) -> None:
    gh = FakeGh({"gh run list": _ok(_RUNS), "gh api": _ok(artifacts)})
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert "kedro-viz-export: none found; mount skipped" in capsys.readouterr().out
    assert env_file.read_text(encoding="utf-8").splitlines() == ["KEDRO_VIZ_EXPORT=absent"]
    assert not [call for call in gh.calls if call[:3] == ["gh", "run", "download"]]


def test_ac3_no_runs_is_absent(tmp_path: Path) -> None:
    gh = FakeGh({"gh run list": _ok([])})
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert env_file.read_text(encoding="utf-8") == "KEDRO_VIZ_EXPORT=absent\n"
    assert len(gh.calls) == 1


@pytest.mark.parametrize("failing", ["gh run list", "gh api", "gh run download"])
def test_ac3_a_gh_error_fails_the_step_and_is_never_absent(tmp_path: Path, capsys, failing: str) -> None:
    answers = {
        "gh run list": _ok(_RUNS),
        "gh api": _ok(_artifacts()),
        "gh run download": subprocess.CompletedProcess([], 0, "", ""),
    }
    answers[failing] = subprocess.CompletedProcess([], 1, "", "HTTP 401: Bad credentials")
    gh = FakeGh(answers)
    code, env_file = _run_script(tmp_path, gh)
    assert code == 1
    err = capsys.readouterr().err
    assert f"`{failing}" in err and "Bad credentials" in err
    assert not env_file.exists() or "absent" not in env_file.read_text(encoding="utf-8")


def test_a_mount_source_that_already_holds_files_is_refused_not_cleared(tmp_path: Path, capsys) -> None:
    dest = tmp_path / "docs" / "dashboard" / "kedro-viz"
    dest.mkdir(parents=True)
    (dest / "index.html").write_text("<html>local stage</html>", encoding="utf-8")
    gh = FakeGh({"gh run list": _ok(_RUNS), "gh api": _ok(_artifacts())})
    code, _ = _run_script(tmp_path, gh)
    assert code == 1
    assert "already holds files" in capsys.readouterr().err
    assert (dest / "index.html").read_text(encoding="utf-8") == "<html>local stage</html>"


def test_a_second_artifact_mount_is_the_same_step_with_its_own_arguments(tmp_path: Path) -> None:
    gh = FakeGh({"gh run list": _ok([]), "gh api": _ok({})})
    code, env_file = _run_script(
        tmp_path,
        gh,
        extra=[
            "--workflow",
            "other.yml",
            "--artifact",
            "other-export",
            "--dest",
            "docs/dashboard/other",
            "--env-prefix",
            "OTHER_EXPORT",
        ],
    )
    assert code == 0
    assert gh.calls[0][4] == "other.yml"
    assert env_file.read_text(encoding="utf-8") == "OTHER_EXPORT=absent\n"


# --- AC5: permission and placement -------------------------------------------------------------------


def test_ac5_the_build_job_reads_actions_and_downloads_before_pages_check() -> None:
    document = yaml.safe_load(PAGES_WORKFLOW.read_text(encoding="utf-8"))
    build = document["jobs"]["build"]
    assert build["permissions"] == {"contents": "read", "pages": "write", "id-token": "write", "actions": "read"}
    assert "actions" not in document["jobs"]["deploy"].get("permissions", {})
    assert "actions" not in document.get("permissions", {})
    runs = [str(step.get("run", "")) for step in build["steps"] if isinstance(step, dict)]
    download = next(i for i, run in enumerate(runs) if "pages_artifact_download.py --workflow" in run)
    flag = next(i for i, run in enumerate(runs) if "pages_artifact_download.py --flag-env" in run)
    check = next(i for i, run in enumerate(runs) if "pages-check" in run)
    assert flag < download < check
    step = [s for s in build["steps"] if isinstance(s, dict)][download]
    assert step["if"] == "${{ env.PYFORGE_PAGES_DUTY == '1' }}"
    assert "--artifact kedro-viz-export" in runs[download] and "--dest docs/dashboard/kedro-viz" in runs[download]
