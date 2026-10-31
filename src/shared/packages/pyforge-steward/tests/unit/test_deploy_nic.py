"""``steward deploy nic`` — Story 118.1 (CAP-176)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.steward.cli import EXIT_USAGE, main
from pyforge.steward.deploy_nic import (
    DOTENV_RELATIVE,
    JOURNAL_RELATIVE,
    NicDeps,
    load_secret_env,
    operator_env_names,
    run_nic,
)

flag_provider = make_flag_provider_fixture()


@dataclass
class _Proc:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def _local_config(tmp_path: Path) -> Path:
    document = {
        "project_name": "my-nebari-local",
        "domain": "nebari.local",
        "repository": {"local": {}},
        "cluster": {"local": {}},
    }
    path = tmp_path / "my-nebari-local.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def _config_needing_token(tmp_path: Path) -> Path:
    document = {
        "project_name": "needs-token",
        "domain": "example.com",
        "repository": {
            "existing": {
                "url": "https://github.com/org/repo.git",
                "branch": "gitops/needs-token",
                "auth": {"token": {"env": "GIT_TOKEN"}},
            }
        },
    }
    path = tmp_path / "needs-token.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def test_operator_env_names_finds_auth_env_fields() -> None:
    document = {"repository": {"existing": {"auth": {"token": {"env": "GIT_TOKEN"}}}}}
    assert operator_env_names(document) == frozenset({"GIT_TOKEN"})


def test_load_secret_env_refuses_missing_dotenv(tmp_path: Path) -> None:
    _, failure = load_secret_env(
        tmp_path,
        env_file=tmp_path / DOTENV_RELATIVE,
        required=frozenset({"GIT_TOKEN"}),
        decrypt=lambda _age, _id: "secret",
    )
    assert failure is not None
    assert failure.details.get("exit_code") == EXIT_USAGE
    assert DOTENV_RELATIVE.as_posix() in failure.summary


def test_load_secret_env_decrypts_through_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-PLACEHOLDER", encoding="utf-8")
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(identity))
    age = tmp_path / ".steward/nkp/git-token.age"
    age.parent.mkdir(parents=True)
    age.write_bytes(b"AGE[FAKE]")
    env_path = tmp_path / DOTENV_RELATIVE
    env_path.write_text("GIT_TOKEN=.steward/nkp/git-token.age\n", encoding="utf-8")
    secret, failure = load_secret_env(
        tmp_path,
        env_file=env_path,
        required=frozenset({"GIT_TOKEN"}),
        decrypt=lambda _age, _id: "pat-value",
    )
    assert failure is None
    assert secret == {"GIT_TOKEN": "pat-value"}


@flag_states("pyforge.steward.nkp_deploy")
def test_each_action_runs_one_nic_subprocess_and_journals(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not flag_provider["pyforge.steward.nkp_deploy"]:
        tree = flagd_tree(tmp_path, {"pyforge.steward.nkp_deploy": "off"})
        monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
        rc = main(["deploy", "nic", "validate", "-f", "cfg.yaml"])
        assert rc == EXIT_USAGE
        return

    config = _local_config(tmp_path)
    calls: list[list[str]] = []
    journal: list[dict] = []

    def runner(argv: list[str], cwd: Path, env: dict[str, str]) -> _Proc:
        calls.append(list(argv))
        assert "GIT_TOKEN" not in env or env.get("GIT_TOKEN") != "parent-leak"
        return _Proc()

    deps = NicDeps(
        root=tmp_path,
        runner=runner,
        nic_executable=lambda: "/usr/bin/nic",
        journal=journal.append,
    )
    for action, nic_verb in (
        ("validate", "validate"),
        ("up", "deploy"),
        ("kubeconfig", "kubeconfig"),
        ("outputs", "outputs"),
        ("down", "destroy"),
    ):
        calls.clear()
        result = run_nic(deps, action=action, config=config)
        assert result.ok is True
        assert calls == [["/usr/bin/nic", nic_verb, "-f", str(config)]]
        assert journal[-1]["verb"] == action
        assert journal[-1]["exit"] == 0
        assert "seconds" in journal[-1]


def test_validate_refuses_config_missing_operator_owned_input(tmp_path: Path) -> None:
    config = _config_needing_token(tmp_path)
    deps = NicDeps(root=tmp_path, runner=lambda *_a, **_k: _Proc(), nic_executable=lambda: "/usr/bin/nic")
    result = run_nic(deps, action="validate", config=config)
    assert result.ok is False
    assert result.details.get("exit_code") == EXIT_USAGE
    assert DOTENV_RELATIVE.as_posix() in result.summary


def test_journal_file_written_under_steward(tmp_path: Path) -> None:
    from pyforge.steward.deploy_nic import _append_journal

    config = _local_config(tmp_path)
    deps = NicDeps(
        root=tmp_path,
        runner=lambda *_a, **_k: _Proc(),
        nic_executable=lambda: "/usr/bin/nic",
        journal=lambda record: _append_journal(tmp_path, record),
    )
    run_nic(deps, action="validate", config=config)
    lines = (tmp_path / JOURNAL_RELATIVE).read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[-1])
    assert payload["verb"] == "validate"
