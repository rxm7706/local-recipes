"""Story 102.4 (CAP-168): the Pages build mounts atlas's Kedro-Viz export from a workflow artifact.

The selection (``pages.newest_export_run``) runs on recorded ``gh`` JSON: the repository's artifacts
listing by name and each candidate's run. The step's script (``scripts/pages_artifact_download.py``)
runs on a fake ``gh`` and a scratch root. No test calls a live ``gh``.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from pyforge.steward.pages import (
    ARTIFACTS_PER_PAGE,
    KEDRO_VIZ_ARTIFACT,
    export_artifacts_endpoint,
    newest_export_run,
)

REPO_ROOT = Path(__file__).resolve().parents[6]
_SCRIPT = REPO_ROOT / "scripts" / "pages_artifact_download.py"
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"
_REPO_ID = 1001
_WORKFLOW_PATH = ".github/workflows/kedro-viz-publish.yml"


def _art(
    run_id: int,
    created: str,
    *,
    name: str = KEDRO_VIZ_ARTIFACT,
    expired: bool = False,
    branch: str | None = "main",
    head_repo: int = _REPO_ID,
) -> dict:
    """One ``artifacts`` entry of ``gh api repos/{owner}/{repo}/actions/artifacts?name=…``."""
    return {
        "id": run_id * 10,
        "name": name,
        "expired": expired,
        "created_at": created,
        "size_in_bytes": 11_000_000,
        "workflow_run": {
            "id": run_id,
            "repository_id": _REPO_ID,
            "head_repository_id": head_repo,
            "head_branch": branch,
            "head_sha": f"{run_id:040x}",
        },
    }


def _run(
    run_id: int,
    created: str = "2026-10-15T09:00:00Z",
    *,
    conclusion: str | None = "success",
    branch: str = "main",
    path: str = _WORKFLOW_PATH,
) -> dict:
    """``gh api repos/{owner}/{repo}/actions/runs/<id>``, the fields the selection reads."""
    return {
        "id": run_id,
        "path": path,
        "conclusion": conclusion,
        "head_branch": branch,
        "created_at": created,
        "event": "push",
    }


_ARTS = [
    _art(303, "2026-10-15T09:05:00Z"),
    _art(302, "2026-10-14T09:05:00Z"),
    _art(301, "2026-10-13T09:05:00Z"),
]
_RUNS = {303: _run(303), 302: _run(302, "2026-10-14T09:00:00Z"), 301: _run(301, "2026-10-13T09:00:00Z")}


# --- AC1: selection --------------------------------------------------------------------------------


def test_ac1_the_newest_live_artifact_from_a_successful_run_wins() -> None:
    assert newest_export_run(_ARTS, _RUNS) == 303  # noqa: PLR2004


@pytest.mark.parametrize(
    "artifacts",
    [
        [],
        [_art(303, "2026-10-15T09:05:00Z", name="something-else")],
        [_art(r, f"2026-10-1{r - 298}T09:05:00Z", expired=True) for r in (303, 302, 301)],
    ],
    ids=["no-artifacts", "another-name", "expired"],
)
def test_ac1_none_when_nothing_mountable(artifacts: list) -> None:
    assert newest_export_run(artifacts, _RUNS) is None


def test_ac1_an_expired_newest_falls_back_to_an_older_live_one() -> None:
    artifacts = [_art(303, "2026-10-15T09:05:00Z", expired=True), _ARTS[1]]
    assert newest_export_run(artifacts, _RUNS) == 302  # noqa: PLR2004


def test_ac1_a_run_that_did_not_succeed_is_ignored() -> None:
    runs = {**_RUNS, 303: _run(303, conclusion="failure")}
    assert newest_export_run(_ARTS, runs) == 302  # noqa: PLR2004
    in_progress = {**_RUNS, 303: _run(303, conclusion=None)}
    assert newest_export_run(_ARTS, in_progress) == 302  # noqa: PLR2004


def test_ac1_an_artifact_another_workflow_uploaded_is_never_mounted() -> None:
    runs = {**_RUNS, 303: _run(303, path=".github/workflows/something-else.yml")}
    assert newest_export_run(_ARTS, runs) == 302  # noqa: PLR2004
    assert newest_export_run(_ARTS, _RUNS, workflow="something-else.yml") is None
    ref_suffixed = {**_RUNS, 303: _run(303, path=f"{_WORKFLOW_PATH}@refs/heads/main")}
    assert newest_export_run(_ARTS, ref_suffixed) == 303  # noqa: PLR2004


def test_ac1_a_run_on_another_branch_is_never_mounted() -> None:
    """102.4's review: the producer accepts a dispatch on any ref, so an unmerged branch's export must
    never reach the production Pages origin."""
    artifacts = [_art(303, "2026-10-15T09:05:00Z", branch="feature/unreviewed"), *_ARTS[1:]]
    runs = {**_RUNS, 303: _run(303, branch="feature/unreviewed")}
    assert newest_export_run(artifacts, runs) == 302  # noqa: PLR2004
    assert newest_export_run(artifacts, runs, branch=None) == 303  # noqa: PLR2004 -- None takes any branch
    assert newest_export_run([_art(303, "2026-10-15T09:05:00Z", branch=None)], _RUNS) is None
    # The run's own head_branch is read too, not only the artifact's copy of it.
    assert newest_export_run(_ARTS, {**_RUNS, 303: _run(303, branch="feature/x")}) == 302  # noqa: PLR2004


def test_ac1_a_fork_s_run_is_never_mounted() -> None:
    artifacts = [_art(303, "2026-10-15T09:05:00Z", head_repo=_REPO_ID + 1), *_ARTS[1:]]
    assert newest_export_run(artifacts, _RUNS) == 302  # noqa: PLR2004


def test_ac1_a_live_export_behind_one_sided_runs_is_still_selected() -> None:
    """102.4's re-review: atlas 30.2's producer runs each export job only when its own paths change.
    Fifteen newer successful runs on main that rebuilt only the other export carry no artifact of this
    name, so they are not in this listing at all; the old run window (the ten newest runs) missed the
    live export behind them and read ``absent``."""
    one_sided = {run_id: _run(run_id, f"2026-10-{run_id - 280:02d}T09:00:00Z") for run_id in range(291, 306)}
    live = _art(290, "2026-10-01T09:05:00Z")
    runs = {**one_sided, 290: _run(290, "2026-10-01T09:00:00Z")}
    assert newest_export_run([live], runs) == 290  # noqa: PLR2004


def test_ac1_a_fetch_callable_is_read_newest_first_and_stops_at_the_first_match() -> None:
    read: list[int] = []

    def fetch(run_id: int) -> dict:
        read.append(run_id)
        return _run(run_id, conclusion="failure" if run_id == 303 else "success")  # noqa: PLR2004

    assert newest_export_run(list(reversed(_ARTS)), fetch) == 302  # noqa: PLR2004
    assert read == [303, 302]


@pytest.mark.parametrize("run", [None, {}, {"id": "303"}], ids=["no-run", "no-id", "id-not-int"])
def test_ac1_a_live_artifact_without_a_readable_run_is_a_wrong_shape_never_a_skip(run: object) -> None:
    """102.4's lane-B re-review: skipping it would read as absence and drop the mount."""
    broken = {**_ARTS[0], "workflow_run": run}
    with pytest.raises(ValueError, match="has no readable workflow_run.id"):
        newest_export_run([broken, *_ARTS[1:]], _RUNS)
    # An expired one, or one of another name, is not read at all.
    assert newest_export_run([{**broken, "expired": True}, *_ARTS[1:]], _RUNS) == 302  # noqa: PLR2004
    assert newest_export_run([{**broken, "name": "other"}, *_ARTS[1:]], _RUNS) == 302  # noqa: PLR2004


def test_ac1_order_is_by_created_at_not_listing_order() -> None:
    assert newest_export_run(list(reversed(_ARTS)), _RUNS) == 303  # noqa: PLR2004


def test_the_listing_endpoint_names_the_artifact_and_pages() -> None:
    assert export_artifacts_endpoint("kedro-viz-export", page=2) == (
        "repos/{owner}/{repo}/actions/artifacts?name=kedro-viz-export&per_page=100&page=2"
    )
    assert "name=a%20b%26c" in export_artifacts_endpoint("a b&c", page=1)
    assert ARTIFACTS_PER_PAGE == 100  # noqa: PLR2004 -- the REST API's maximum page size


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
            if " ".join(argv) == key or " ".join(argv).startswith(f"{key} "):
                return proc
        return subprocess.CompletedProcess(argv, 127, "", f"no fake for {argv}")


def _ok(payload: object) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 0, json.dumps(payload), "")


def _listing(artifact: str = KEDRO_VIZ_ARTIFACT, page: int = 1) -> str:
    return f"gh api {export_artifacts_endpoint(artifact, page=page)}"


def _run_call(run_id: int) -> str:
    return f"gh api repos/{{owner}}/{{repo}}/actions/runs/{run_id}"


def _page(items: list) -> subprocess.CompletedProcess[str]:
    return _ok({"total_count": len(items), "artifacts": items})


_DOWNLOADED = subprocess.CompletedProcess([], 0, "", "")


def _run_script(
    tmp_path: Path, gh: FakeGh, *, flag_on: bool = True, extra: list[str] | None = None
) -> tuple[int, Path]:
    env_file = tmp_path / "github_env"
    code = _load_script().main(
        ["--github-env", str(env_file), *(extra or [])], runner=gh, flag_on=flag_on, root=tmp_path
    )
    return code, env_file


def test_ac2_present_downloads_into_the_mount_source_and_exports_the_run(tmp_path: Path, capsys) -> None:
    gh = FakeGh({_listing(): _page(_ARTS), _run_call(303): _ok(_RUNS[303]), "gh run download": _DOWNLOADED})
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert gh.calls[0] == [
        "gh",
        "api",
        "repos/{owner}/{repo}/actions/artifacts?name=kedro-viz-export&per_page=100&page=1",
    ]
    assert gh.calls[1] == ["gh", "api", "repos/{owner}/{repo}/actions/runs/303"]
    assert gh.calls[-1] == ["gh", "run", "download", "303", "-n", "kedro-viz-export", "-D", "docs/dashboard/kedro-viz"]
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "KEDRO_VIZ_EXPORT=present",
        "KEDRO_VIZ_EXPORT_RUN=303",
        "KEDRO_VIZ_EXPORT_AT=2026-10-15T09:00:00Z",
    ]
    assert "run 303" in capsys.readouterr().out
    assert not [call for call in gh.calls if call[:3] == ["gh", "run", "list"]]  # no run window


def test_ac2_it_stops_reading_runs_at_the_first_match(tmp_path: Path) -> None:
    gh = FakeGh(
        {
            _listing(): _page(_ARTS),
            _run_call(303): _ok(_run(303, conclusion="failure")),
            _run_call(302): _ok(_RUNS[302]),
            "gh run download": _DOWNLOADED,
        }
    )
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert not any(" ".join(call) == _run_call(301) for call in gh.calls)
    assert "KEDRO_VIZ_EXPORT_RUN=302" in env_file.read_text(encoding="utf-8")


def test_ac2_the_live_export_behind_ten_one_sided_runs_is_downloaded(tmp_path: Path) -> None:
    """102.4's re-review: after ten producer runs that rebuilt only the Vizro export, the old step's
    ten-run window held no kedro-viz-export and read ``absent``, and the next deploy dropped
    /dashboard/kedro-viz/ from production. The listing by name still finds the live one."""
    vizro_only = [_art(r, f"2026-10-{r - 280:02d}T09:05:00Z", name="vizro-static-export") for r in range(291, 301)]
    live = _art(290, "2026-10-01T09:05:00Z")
    gh = FakeGh(
        {
            _listing(): _page([live]),
            _listing("vizro-static-export"): _page(vizro_only),
            _run_call(290): _ok(_run(290, "2026-10-01T09:00:00Z")),
            "gh run download": _DOWNLOADED,
            # The old window: answered if asked, never asked.
            "gh run list": _ok(
                [{"databaseId": r, "conclusion": "success", "headBranch": "main"} for r in range(291, 301)]
            ),
        }
    )
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert gh.calls[-1] == ["gh", "run", "download", "290", "-n", "kedro-viz-export", "-D", "docs/dashboard/kedro-viz"]
    assert env_file.read_text(encoding="utf-8").splitlines()[:2] == [
        "KEDRO_VIZ_EXPORT=present",
        "KEDRO_VIZ_EXPORT_RUN=290",
    ]
    assert not [call for call in gh.calls if call[:3] == ["gh", "run", "list"]]


def test_ac2_every_page_of_the_listing_is_read(tmp_path: Path) -> None:
    """A full page asks for the next one; the newest live artifact may sit on any page."""
    stale = [_art(200 + i, f"2026-08-01T09:{i % 60:02d}:00Z", expired=True) for i in range(ARTIFACTS_PER_PAGE)]
    gh = FakeGh(
        {
            _listing(page=1): _page(stale),
            _listing(page=2): _page([_art(303, "2026-10-15T09:05:00Z")]),
            _run_call(303): _ok(_RUNS[303]),
            "gh run download": _DOWNLOADED,
        }
    )
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert [" ".join(call) for call in gh.calls[:2]] == [_listing(page=1), _listing(page=2)]
    assert "KEDRO_VIZ_EXPORT_RUN=303" in env_file.read_text(encoding="utf-8")


def test_a_listing_longer_than_the_page_cap_fails_and_is_never_truncated(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load_script()
    monkeypatch.setattr(script, "MAX_ARTIFACT_PAGES", 2)
    full = _page([_art(200 + i, "2026-08-01T09:00:00Z", expired=True) for i in range(ARTIFACTS_PER_PAGE)])
    gh = FakeGh({_listing(page=1): full, _listing(page=2): full})
    env_file = tmp_path / "github_env"
    code = script.main(["--github-env", str(env_file)], runner=gh, flag_on=True, root=tmp_path)
    assert code == 1
    assert "still gave a full page" in capsys.readouterr().err
    assert not env_file.exists()


@pytest.mark.parametrize(
    "artifacts",
    [[], [_art(303, "2026-10-15T09:05:00Z", expired=True)]],
    ids=["no-artifact", "expired"],
)
def test_ac3_absent_is_a_normal_build(tmp_path: Path, capsys, artifacts: list) -> None:
    gh = FakeGh({_listing(): _page(artifacts)})
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert "kedro-viz-export: none found; mount skipped" in capsys.readouterr().out
    assert env_file.read_text(encoding="utf-8").splitlines() == ["KEDRO_VIZ_EXPORT=absent"]
    assert len(gh.calls) == 1  # one listing call; no run is read, nothing is downloaded


def test_ac3_no_successful_run_behind_the_artifacts_is_absent(tmp_path: Path) -> None:
    gh = FakeGh(
        {
            _listing(): _page(_ARTS),
            **{_run_call(r): _ok(_run(r, conclusion="failure")) for r in (303, 302, 301)},
        }
    )
    code, env_file = _run_script(tmp_path, gh)
    assert code == 0
    assert env_file.read_text(encoding="utf-8") == "KEDRO_VIZ_EXPORT=absent\n"
    assert not [call for call in gh.calls if call[:3] == ["gh", "run", "download"]]


@pytest.mark.parametrize("failing", ["listing", "run", "gh run download"])
def test_ac3_a_gh_error_fails_the_step_and_is_never_absent(tmp_path: Path, capsys, failing: str) -> None:
    keys = {"listing": _listing(), "run": _run_call(303), "gh run download": "gh run download"}
    answers = {_listing(): _page(_ARTS), _run_call(303): _ok(_RUNS[303]), "gh run download": _DOWNLOADED}
    answers[keys[failing]] = subprocess.CompletedProcess([], 1, "", "HTTP 401: Bad credentials")
    code, env_file = _run_script(tmp_path, FakeGh(answers))
    assert code == 1
    err = capsys.readouterr().err
    assert f"`{keys[failing]}" in err and "Bad credentials" in err
    assert not env_file.exists() or "absent" not in env_file.read_text(encoding="utf-8")


def test_a_mount_source_that_already_holds_files_is_refused_not_cleared(tmp_path: Path, capsys) -> None:
    dest = tmp_path / "docs" / "dashboard" / "kedro-viz"
    dest.mkdir(parents=True)
    (dest / "index.html").write_text("<html>local stage</html>", encoding="utf-8")
    gh = FakeGh({_listing(): _page(_ARTS), _run_call(303): _ok(_RUNS[303])})
    code, _ = _run_script(tmp_path, gh)
    assert code == 1
    assert "already holds files" in capsys.readouterr().err
    assert (dest / "index.html").read_text(encoding="utf-8") == "<html>local stage</html>"


def test_a_second_artifact_mount_is_the_same_step_with_its_own_arguments(tmp_path: Path) -> None:
    gh = FakeGh({_listing("other-export"): _page([])})
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
    assert gh.calls == [["gh", "api", export_artifacts_endpoint("other-export", page=1)]]
    assert env_file.read_text(encoding="utf-8") == "OTHER_EXPORT=absent\n"


# --- AC5: permission and placement -------------------------------------------------------------------


def test_ac5_the_build_job_reads_actions_and_downloads_before_pages_check() -> None:
    document = yaml.safe_load(PAGES_WORKFLOW.read_text(encoding="utf-8"))
    build = document["jobs"]["build"]
    # 102.4's review: least privilege; pages: write and id-token: write belong to deploy.
    assert build["permissions"] == {"contents": "read", "pages": "read", "actions": "read"}
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


@pytest.mark.parametrize(
    ("answers", "named"),
    [
        ({_listing(): _ok(None)}, _listing()),  # empty stdout parses as null
        ({_listing(): _ok([])}, _listing()),
        ({_listing(): _ok({"total_count": 0})}, _listing()),
        ({_listing(): _page(_ARTS), _run_call(303): _ok([])}, _run_call(303)),
        ({_listing(): _page(_ARTS), _run_call(303): _ok({"id": 303, "conclusion": "success"})}, _run_call(303)),
    ],
    ids=["listing-null", "listing-list", "listing-no-key", "run-list", "run-no-path"],
)
def test_a_wrong_shape_answer_fails_naming_the_argv(tmp_path: Path, capsys, answers: dict, named: str) -> None:
    code, env_file = _run_script(tmp_path, FakeGh(answers))
    assert code == 1
    assert f"`{named}" in capsys.readouterr().err
    assert not env_file.exists()


def test_a_live_artifact_without_a_readable_run_fails_naming_the_listing(tmp_path: Path, capsys) -> None:
    broken = {**_art(303, "2026-10-15T09:05:00Z"), "workflow_run": {"head_branch": "main"}}
    code, env_file = _run_script(tmp_path, FakeGh({_listing(): _page([broken, *_ARTS[1:]])}))
    assert code == 1
    err = capsys.readouterr().err
    assert f"`{_listing()}` gave live artifact kedro-viz-export (id 3030) with no readable workflow_run.id" in err
    assert not env_file.exists()  # never `absent`


def test_no_gh_on_the_runner_fails_naming_the_argv(tmp_path: Path, capsys) -> None:
    def missing(argv: list[str]) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(2, "No such file or directory", "gh")

    code = _load_script().main(["--github-env", str(tmp_path / "env")], runner=missing, flag_on=True, root=tmp_path)
    assert code == 1
    err = capsys.readouterr().err
    assert f"`{_listing()}" in err and "could not run" in err


def test_the_script_reads_the_pages_duty_flag_itself(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """With no injected state the script's own `read_boolean` decides; that read feeds the step's `if:`."""
    import pyforge.core.flags as flags

    seen: list[str] = []

    def read_boolean(key: str, default: bool = False, **_: object) -> bool:
        seen.append(key)
        return False

    monkeypatch.setattr(flags, "read_boolean", read_boolean)
    assert _load_script().main(["--flag-env"], root=tmp_path) == 0
    assert seen == ["pyforge.steward.pages_duty"]
    assert "PYFORGE_PAGES_DUTY=0" in capsys.readouterr().out


def test_a_second_artifact_is_downloaded_under_its_own_names(tmp_path: Path) -> None:
    """Atlas 30.2's consumer: the same step with its own artifact, destination and prefix."""
    gh = FakeGh(
        {
            _listing("vizro-static-export"): _page([_art(303, "2026-10-15T09:05:00Z", name="vizro-static-export")]),
            _run_call(303): _ok(_RUNS[303]),
            "gh run download": _DOWNLOADED,
        }
    )
    code, env_file = _run_script(
        tmp_path,
        gh,
        extra=["--artifact", "vizro-static-export", "--dest", "docs/dashboard/vizro", "--env-prefix", "VIZRO_EXPORT"],
    )
    assert code == 0
    assert gh.calls[-1] == ["gh", "run", "download", "303", "-n", "vizro-static-export", "-D", "docs/dashboard/vizro"]
    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "VIZRO_EXPORT=present",
        "VIZRO_EXPORT_RUN=303",
        "VIZRO_EXPORT_AT=2026-10-15T09:00:00Z",
    ]


def test_the_workflow_mounts_the_vizro_export_the_same_way() -> None:
    steps = [
        s
        for s in yaml.safe_load(PAGES_WORKFLOW.read_text(encoding="utf-8"))["jobs"]["build"]["steps"]
        if isinstance(s, dict)
    ]
    runs = [" ".join(str(s.get("run", "")).split()) for s in steps]
    kedro = next(i for i, run in enumerate(runs) if "--artifact kedro-viz-export" in run)
    vizro = next(i for i, run in enumerate(runs) if "--artifact vizro-static-export" in run)
    check = next(i for i, run in enumerate(runs) if "pages-check" in run)
    assert kedro < vizro < check
    assert "--workflow kedro-viz-publish.yml" in runs[vizro]
    assert "--dest docs/dashboard/vizro --env-prefix VIZRO_EXPORT --branch main" in runs[vizro]
    assert "--branch main" in runs[kedro]
    for index in (kedro, vizro):
        assert steps[index]["if"] == "${{ env.PYFORGE_PAGES_DUTY == '1' }}"
        assert steps[index]["env"] == {
            "GH_TOKEN": "${{ github.token }}",
            "GH_ENTERPRISE_TOKEN": "${{ github.token }}",
            "GH_REPO": "${{ github.repository }}",
        }


def test_both_downloads_name_the_host_that_runs_the_workflow() -> None:
    """102.4's re-review: on a GitHub Enterprise Server runner a token alone does not tell ``gh`` which
    host to use (it has no config there), so each download step names it the way the deploy job's
    release step does: ``GH_HOST`` from ``GITHUB_SERVER_URL``, before ``gh`` runs."""
    document = yaml.safe_load(PAGES_WORKFLOW.read_text(encoding="utf-8"))
    host_line = 'export GH_HOST="${GITHUB_SERVER_URL#*://}"'
    downloads = [
        s
        for s in document["jobs"]["build"]["steps"]
        if isinstance(s, dict) and "pages_artifact_download.py --workflow" in str(s.get("run", ""))
    ]
    assert len(downloads) == 2  # noqa: PLR2004 -- kedro-viz-export and vizro-static-export
    for step in downloads:
        lines = [line.strip() for line in str(step["run"]).splitlines() if line.strip()]
        assert lines[0] == host_line, step["name"]
        assert lines[1].startswith("pixi run --frozen -e pyforge-guild python scripts/pages_artifact_download.py")
    release = next(s for s in document["jobs"]["deploy"]["steps"] if "gh release upload" in str(s.get("run", "")))
    assert host_line in release["run"]  # the one form, reused
