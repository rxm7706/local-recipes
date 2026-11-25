"""Steward Story 133.2 (spec-pyforge-steward CAP-175, CAP-167): the workflows and scripts steward runs do what
they name.

One test per defect of ``DW-steward-review-2026-11-24-2`` that a file under ``tests/scripts`` can hold; each failed
on the unchanged tree. The fleet poll's two (the push flag git lacks, the two-hour tick) are in
``test_fleet_poll_sync.py``; the changes page's is in steward's ``tests/unit/test_pages_changes.py``. Defect 9 (the
promotion artifact's ``images.*.digest``) is left open on an operator decision and has no test here; defect 12
(an unregistered hook file) lies outside this surface.

Stdlib + pytest only: this file runs in the dependency-free ``pyforge-ci`` environment
(``pyforge-doctor-scripts-test``), so workflows are read as text, never through a YAML library.
"""

from __future__ import annotations

import http.client
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
ACTIONS = sorted((REPO_ROOT / ".github" / "actions").glob("*/action.yml"))

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bump_pixi_version as bump  # sys.path must be set up first
import pixi_version_registry as registry


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


# --- defect 1: a boolean input is never compared to a string -------------------------------------------------


def _boolean_inputs(text: str) -> list[str]:
    """Names of the inputs a workflow declares ``type: boolean``, read by indentation."""
    names: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^( +)([A-Za-z_][\w-]*):\s*$", line)
        if not match:
            continue
        depth = len(match.group(1))
        for body in lines[index + 1 :]:
            if body.strip() and _indent(body) <= depth:
                break
            if _indent(body) == depth + 2 and re.match(
                r"^\s+type:\s*boolean\s*$", body
            ):
                names.append(match.group(2))
                break
    return names


def test_no_workflow_compares_a_boolean_input_to_a_string() -> None:
    """``inputs.<name>`` of a ``type: boolean`` input is a boolean: ``true == 'true'`` casts both sides to numbers
    (1 and NaN) and is false, and ``false == ''`` is true. The mapping sync's publish steps were gated that way."""
    offenders: list[str] = []
    for path in WORKFLOWS:
        text = path.read_text(encoding="utf-8")
        for name in _boolean_inputs(text):
            # `github.event.inputs.<name>` is always a string and is left alone
            compared = re.compile(
                rf"(?<![\w.])inputs\.{re.escape(name)}\s*[!=]=\s*'|'\s*[!=]=\s*inputs\.{re.escape(name)}(?![\w-])"
            )
            for number, line in enumerate(text.splitlines(), 1):
                if compared.search(line):
                    offenders.append(
                        f"{_rel(path)}:{number}: boolean input {name!r} compared to a string"
                    )
    assert not offenders, "\n".join(offenders)


def test_a_boolean_input_s_default_is_a_boolean() -> None:
    offenders: list[str] = []
    for path in WORKFLOWS:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if not re.match(r"^\s+type:\s*boolean\s*$", line):
                continue
            depth = _indent(line)
            siblings = []
            for step in (-1, 1):
                cursor = index + step
                while 0 <= cursor < len(lines) and (
                    not lines[cursor].strip() or _indent(lines[cursor]) >= depth
                ):
                    siblings.append((cursor, lines[cursor]))
                    cursor += step
            for number, sibling in siblings:
                if _indent(sibling) == depth and re.match(
                    r"^\s+default:\s*['\"]", sibling
                ):
                    offenders.append(f"{_rel(path)}:{number + 1}: {sibling.strip()}")
    assert not offenders, "\n".join(offenders)


# --- defect 2: the pre-push hook runs pixi tasks that exist --------------------------------------------------


def _pixi_tasks() -> dict[str, dict[str, object]]:
    """feature name -> its task table (``(top-level)`` for a bare ``[tasks]``)."""
    data = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    tables: dict[str, dict[str, object]] = {}
    if data.get("tasks"):
        tables["(top-level)"] = data["tasks"]
    for feature, body in data.get("feature", {}).items():
        if body.get("tasks"):
            tables[feature] = body["tasks"]
    return tables


def test_the_pre_push_hook_runs_only_pixi_tasks_that_exist() -> None:
    """The hook called ``preflight --budget``; the task is ``preflight-budget``, and ``|| true`` hid the exit 127."""
    known = {name for table in _pixi_tasks().values() for name in table}
    text = (SCRIPTS / "pre_push_preflight.sh").read_text(encoding="utf-8")
    called = re.findall(
        r"^\s*(?:if !\s+)?pixi run (?:--frozen )?-e \S+ ([\w-]+)",
        text,
        flags=re.MULTILINE,
    )
    assert "pr-preflight" in called  # the pattern still reads the hook
    assert "preflight-budget" in called
    assert [task for task in called if task not in known] == []


def test_the_pre_push_hook_prints_the_budget_report_after_a_green_preflight(
    tmp_path: Path,
) -> None:
    """A fake ``pixi`` that passes records every call: after a green preflight the hook runs ``preflight-budget``."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PRE_COMMIT_", "GIT_", "PYFORGE_PREFLIGHT"))
    }
    env.update(
        {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@x",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@x",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        }
    )
    calls = tmp_path / "pixi-calls.txt"
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    (fakebin / "pixi").write_text(
        f'#!/usr/bin/env bash\necho "$*" >> "{calls}"\nexit 0\n', encoding="utf-8"
    )
    (fakebin / "pixi").chmod(0o755)
    env["PATH"] = f"{fakebin}{os.pathsep}{env['PATH']}"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, env=env)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "base"],
        check=True,
        env=env,
    )
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "-q", "-b", "work"], check=True, env=env
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "work"],
        check=True,
        env=env,
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()
    shutil.copy(SCRIPTS / "pre_push_preflight.sh", repo / "hook.sh")
    proc = subprocess.run(
        ["bash", "hook.sh"],
        check=False,
        cwd=repo,
        input=f"refs/heads/work {head} refs/heads/work {'0' * 40}\n",
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    ran = calls.read_text(encoding="utf-8").splitlines()
    assert ran == [
        "run --frozen -e pyforge-guild pr-preflight",
        "run --frozen -e pyforge-guild preflight-budget",
    ]


# --- defect 5: every pixi task names a script that exists ----------------------------------------------------

# A path with a directory in it that ends .sh or .py, taken whole (`.claude/scripts/x.py` is not `scripts/x.py`)
_SCRIPT_PATH = re.compile(r"(?<![\w./-])((?:[\w.-]+/)+[\w.-]+\.(?:sh|py))(?![\w.-])")


def test_every_pixi_task_names_a_script_that_exists() -> None:
    """``sync-upstream-public-fork`` ran ``scripts/sync-public-fork.sh``, a file no commit ever held."""
    missing: list[str] = []
    for feature, table in _pixi_tasks().items():
        for name, spec in table.items():
            cmd = (
                spec
                if isinstance(spec, str)
                else spec.get("cmd")
                if isinstance(spec, dict)
                else None
            )
            cwd = spec.get("cwd", "") if isinstance(spec, dict) else ""
            if isinstance(cmd, list):
                cmd = " ".join(str(part) for part in cmd)
            if not isinstance(cmd, str):
                continue
            for match in _SCRIPT_PATH.finditer(cmd):
                ref = match.group(1)
                if (
                    not (REPO_ROOT / ref).is_file()
                    and not (REPO_ROOT / str(cwd) / ref).is_file()
                ):
                    missing.append(
                        f"[feature.{feature}.tasks.{name}] runs {ref}, which does not exist"
                    )
    assert not missing, "\n".join(missing)


# --- defect 6: every setup-pixi step pins the workspace's pixi version, at a registered site ------------------

_SETUP_PIXI = re.compile(r"^\s*(?:- )?uses:\s*prefix-dev/setup-pixi@")
_PIXI_PIN = re.compile(r"^\s+pixi-version:\s*v\d+\.\d+\.\d+\s*$")


def _setup_pixi_steps(text: str) -> list[tuple[int, list[str]]]:
    """(line number of the ``uses:``, the step's lines) for every setup-pixi step in a workflow or action."""
    lines = text.splitlines()
    steps: list[tuple[int, list[str]]] = []
    for index, line in enumerate(lines):
        if not _SETUP_PIXI.match(line):
            continue
        start = index
        # a bare `uses:` sits under the `- name:` that opens its step
        while not lines[start].lstrip().startswith("- "):
            start -= 1
        dash = _indent(lines[start])
        end = start + 1
        while end < len(lines) and (
            not lines[end].strip() or _indent(lines[end]) > dash
        ):
            end += 1
        steps.append((index + 1, lines[start:end]))
    return steps


def test_every_setup_pixi_step_pins_the_pixi_version() -> None:
    """A step with no ``pixi-version`` installs whatever pixi is newest that day, not the version the workspace
    pins; 36 steps (29 in ``pyforge-station-tests.yml``) carried none."""
    unpinned: list[str] = []
    seen = 0
    for path in [*WORKFLOWS, *ACTIONS]:
        for number, step in _setup_pixi_steps(path.read_text(encoding="utf-8")):
            seen += 1
            if sum(1 for line in step if _PIXI_PIN.match(line)) != 1:
                unpinned.append(f"{_rel(path)}:{number}")
    assert seen >= 40  # the scan still finds the steps
    assert not unpinned, (
        f"{len(unpinned)} setup-pixi step(s) with no pixi-version:\n"
        + "\n".join(unpinned)
    )


def test_every_setup_pixi_step_is_a_registered_pin_site() -> None:
    """``pixi-version-check`` holds, and ``bump-pixi-version`` moves, only the sites in the registry: every file
    with a setup-pixi step is registered with one hit per step."""
    registered: dict[str, int] = {}
    for site in registry.SITES:
        if "pixi-version" in site.pattern.pattern:
            rel = site.path.relative_to(registry.REPO_ROOT).as_posix()
            registered[rel] = registered.get(rel, 0) + site.expected_hits
    counted = {
        _rel(path): len(_setup_pixi_steps(path.read_text(encoding="utf-8")))
        for path in [*WORKFLOWS, *ACTIONS]
    }
    counted = {rel: count for rel, count in counted.items() if count}
    assert registered == counted


# --- defect 7: a failed export leaves environment.yaml as it was ---------------------------------------------


def _one_derived_site(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    env_yaml = tmp_path / "environment.yaml"
    env_yaml.write_text(
        "name: build\ndependencies:\n- pixi >=0.80.0\n", encoding="utf-8"
    )
    derived = next(site for site in registry.SITES if site.derived)
    monkeypatch.setattr(
        bump,
        "SITES",
        (registry.Site(derived.name, env_yaml, derived.pattern, 1, "floor", True),),
    )
    monkeypatch.setattr(bump, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(bump, "verify_image_exists", lambda version: True)
    return env_yaml


def _fake_export(returncode: int, output: str):
    def run(cmd, *, stdout=None, **kwargs):
        # an open file: the export streams straight into it
        if hasattr(stdout, "write"):
            stdout.write(output)
            return subprocess.CompletedProcess(
                cmd, returncode, None, "the export failed"
            )
        return subprocess.CompletedProcess(cmd, returncode, output, "the export failed")

    return run


def test_a_failed_export_leaves_environment_yaml_as_it_was(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The mutator opened ``environment.yaml`` for writing before it ran the export, so a failed export left it
    empty (or holding half an export)."""
    env_yaml = _one_derived_site(monkeypatch, tmp_path)
    before = env_yaml.read_bytes()
    monkeypatch.setattr(bump.subprocess, "run", _fake_export(1, ""))
    assert bump.bump("0.80.0") == 2
    assert "environment.yaml export failed" in capsys.readouterr().err
    assert env_yaml.read_bytes() == before
    monkeypatch.setattr(
        bump.subprocess, "run", _fake_export(1, "name: half an export\n")
    )
    assert bump.bump("0.80.0") == 2
    assert env_yaml.read_bytes() == before


def test_an_export_that_cannot_run_leaves_environment_yaml_as_it_was(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_yaml = _one_derived_site(monkeypatch, tmp_path)
    before = env_yaml.read_bytes()

    def no_pixi(cmd, **kwargs):
        raise FileNotFoundError("pixi")

    monkeypatch.setattr(bump.subprocess, "run", no_pixi)
    with pytest.raises(FileNotFoundError):
        bump.bump("0.80.0")
    assert env_yaml.read_bytes() == before


def test_a_good_export_is_written_to_environment_yaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_yaml = _one_derived_site(monkeypatch, tmp_path)
    exported = "name: build\ndependencies:\n- pixi >=0.81.0\n"
    monkeypatch.setattr(bump.subprocess, "run", _fake_export(0, exported))
    assert bump.bump("0.81.0") == 0
    assert env_yaml.read_text(encoding="utf-8") == exported


@pytest.mark.parametrize(
    "failure",
    [
        OSError("no route to host"),
        TimeoutError("timed out"),
        ValueError("the token body is not JSON"),
        KeyError("token"),
        http.client.BadStatusLine("garbage"),
        http.client.IncompleteRead(b""),
    ],
)
def test_an_image_check_that_cannot_run_is_unverified_not_failed(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    def urlopen(*args, **kwargs):
        raise failure

    monkeypatch.setattr(bump.urllib.request, "urlopen", urlopen)

    assert bump.verify_image_exists("0.80.0") is None


def test_an_image_check_does_not_swallow_a_programming_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def urlopen(*args, **kwargs):
        raise AssertionError("not a network failure")

    monkeypatch.setattr(bump.urllib.request, "urlopen", urlopen)

    with pytest.raises(AssertionError):
        bump.verify_image_exists("0.80.0")


# --- defect 10: the upstream sync pops only the stash it made ------------------------------------------------


def _sync_repo(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A clone whose ``upstream`` remote is a local bare repository one commit ahead of it."""
    env = {
        **{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.test",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.test",
    }

    def git(cwd: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        ).stdout.strip()

    upstream = tmp_path / "upstream.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(upstream)],
        check=True,
        env=env,
    )
    seed = tmp_path / "seed"
    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(seed)],
        check=True,
        env=env,
        capture_output=True,
    )
    (seed / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(seed, "add", "tracked.txt")
    git(seed, "commit", "-qm", "base")
    git(seed, "push", "-q", "origin", "HEAD:main")
    repo = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(repo)],
        check=True,
        env=env,
        capture_output=True,
    )
    git(repo, "remote", "add", "upstream", str(upstream))
    (seed / "upstream.txt").write_text("new upstream\n", encoding="utf-8")
    git(seed, "add", "upstream.txt")
    git(seed, "commit", "-qm", "upstream moves")
    git(seed, "push", "-q", "origin", "HEAD:main")
    return repo, env


def _run_sync_upstream(
    repo: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPTS / "sync-upstream-conda-forge.sh")],
        check=False,
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def _stashes(repo: Path, env: dict[str, str]) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "stash", "list", "--format=%gs"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout
    return out.splitlines()


def test_the_upstream_sync_leaves_an_earlier_stash_alone_when_the_tree_is_clean(
    tmp_path: Path,
) -> None:
    """On a clean tree ``git stash`` saves nothing, so the unconditional ``git stash pop`` applied whatever stash
    the operator had parked before, into the freshly rebased tree."""
    repo, env = _sync_repo(tmp_path)
    (repo / "tracked.txt").write_text("parked work\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "stash", "push", "-q", "-m", "parked earlier"],
        check=True,
        env=env,
    )
    assert len(_stashes(repo, env)) == 1
    proc = _run_sync_upstream(repo, env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / "upstream.txt").is_file()  # the rebase ran
    # the parked work was not applied
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "base\n"
    assert len(_stashes(repo, env)) == 1 and "parked earlier" in _stashes(repo, env)[0]


def test_the_upstream_sync_restores_the_changes_it_stashed(tmp_path: Path) -> None:
    repo, env = _sync_repo(tmp_path)
    (repo / "tracked.txt").write_text("in flight\n", encoding="utf-8")
    proc = _run_sync_upstream(repo, env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (repo / "upstream.txt").is_file()
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "in flight\n"
    assert _stashes(repo, env) == []


# --- defect 11: every workflow states the token permissions it needs -----------------------------------------


def _jobs_without_permissions(text: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = next(
            index for index, line in enumerate(lines) if re.match(r"^jobs:\s*$", line)
        )
    except StopIteration:
        return ["(no jobs)"]
    jobs: dict[str, bool] = {}
    current = None
    for line in lines[start + 1 :]:
        if line.strip() and not line.startswith(" ") and not line.startswith("#"):
            break
        match = re.match(r"^  ([A-Za-z_][\w-]*):\s*$", line)
        if match:
            current = match.group(1)
            jobs[current] = False
        elif current and re.match(r"^    permissions:", line):
            jobs[current] = True
    return [name for name, has in jobs.items() if not has]


def test_every_workflow_states_its_token_permissions() -> None:
    """A workflow with no ``permissions:`` runs with the repository's default token grant, which may be
    read-write; five workflows had none at the workflow or on every job."""
    offenders: list[str] = []
    assert len(WORKFLOWS) >= 18
    for path in WORKFLOWS:
        text = path.read_text(encoding="utf-8")
        if re.search(r"^permissions:", text, flags=re.MULTILINE):
            continue
        without = _jobs_without_permissions(text)
        if without:
            offenders.append(
                f"{_rel(path)}: no workflow permissions, and none on job(s) {', '.join(without)}"
            )
    assert not offenders, "\n".join(offenders)
