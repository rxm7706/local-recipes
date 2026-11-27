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
    run_deploy_nic,
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
    """A cloud config whose one operator-owned input is nic's deploy key (Story 118.9: no ``auth.token``)."""
    document = {
        "project_name": "needs-token",
        "domain": "example.invalid",
        "cluster": {"hetzner": {"location": "ash"}},
        "repository": {
            "existing": {
                "url": "https://github.com/org/repo.git",
                "branch": "gitops/needs-token",
                "auth": {"ssh": {"env": "GITOPS_DEPLOY_KEY"}},
            }
        },
    }
    path = tmp_path / "needs-token.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def test_operator_env_names_finds_auth_env_fields() -> None:
    document = {"repository": {"existing": {"auth": {"token": {"env": "GIT_TOKEN"}}}}}
    assert operator_env_names(document) == frozenset({"GIT_TOKEN"})


def test_operator_env_names_walks_lists_and_skips_blank_env() -> None:
    document = {"items": [{"env": "  A  "}, {"env": ""}, {"nested": {"env": "B"}}]}
    assert operator_env_names(document) == frozenset({"A", "B"})


def test_load_secret_env_empty_required_needs_no_dotenv(tmp_path: Path) -> None:
    secret, failure = load_secret_env(tmp_path, env_file=tmp_path / DOTENV_RELATIVE, required=frozenset())
    assert failure is None
    assert secret == {}


def test_load_secret_env_refuses_no_age_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOPS_AGE_KEY_FILE", raising=False)
    env_path = tmp_path / DOTENV_RELATIVE
    env_path.write_text("GIT_TOKEN=secret.age\n", encoding="utf-8")
    _, failure = load_secret_env(
        tmp_path,
        env_file=env_path,
        required=frozenset({"GIT_TOKEN"}),
        decrypt=lambda _age, _id: "secret",
    )
    assert failure is not None
    assert "no age identity" in failure.summary


def test_load_secret_env_refuses_unmapped_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-PLACEHOLDER", encoding="utf-8")
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(identity))
    env_path = tmp_path / DOTENV_RELATIVE
    env_path.write_text("# comment\n\nBADLINE\nOTHER=x.age\n", encoding="utf-8")
    _, failure = load_secret_env(
        tmp_path,
        env_file=env_path,
        required=frozenset({"GIT_TOKEN"}),
        decrypt=lambda _age, _id: "secret",
    )
    assert failure is not None
    assert "does not map" in failure.summary


def test_load_secret_env_refuses_missing_age_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-PLACEHOLDER", encoding="utf-8")
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(identity))
    env_path = tmp_path / DOTENV_RELATIVE
    env_path.write_text("GIT_TOKEN=missing.age\n", encoding="utf-8")
    _, failure = load_secret_env(
        tmp_path,
        env_file=env_path,
        required=frozenset({"GIT_TOKEN"}),
        decrypt=lambda _age, _id: "secret",
    )
    assert failure is not None
    assert "is missing" in failure.summary


def test_load_secret_env_refuses_decrypt_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-PLACEHOLDER", encoding="utf-8")
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(identity))
    age = tmp_path / "token.age"
    age.write_bytes(b"AGE[FAKE]")
    env_path = tmp_path / DOTENV_RELATIVE
    env_path.write_text("GIT_TOKEN=token.age\n", encoding="utf-8")

    def boom(_age: Path, _id: Path) -> str:
        raise OSError("decrypt failed")

    _, failure = load_secret_env(
        tmp_path,
        env_file=env_path,
        required=frozenset({"GIT_TOKEN"}),
        decrypt=boom,
    )
    assert failure is not None
    assert "cannot decrypt" in failure.summary


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
    # ``destroy`` alone carries ``--auto-approve``: nic prompts ``Type 'yes' to confirm`` on a
    # terminal and exits 1 with ``failed to read user input: EOF`` without one (Story 118.4).
    for action, nic_verb, extra in (
        ("validate", "validate", []),
        ("up", "deploy", []),
        ("kubeconfig", "kubeconfig", []),
        ("outputs", "outputs", []),
        ("down", "destroy", ["--auto-approve"]),
    ):
        calls.clear()
        result = run_nic(deps, action=action, config=config)
        assert result.ok is True
        assert calls == [["/usr/bin/nic", nic_verb, "-f", str(config), *extra]]
        assert journal[-1]["verb"] == action
        assert journal[-1]["exit"] == 0
        assert "seconds" in journal[-1]


def test_validate_refuses_config_missing_operator_owned_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _flag_on(monkeypatch)
    config = _config_needing_token(tmp_path)
    deps = NicDeps(
        root=tmp_path,
        runner=lambda *_a, **_k: _Proc(),
        nic_executable=lambda: "/usr/bin/nic",
        inventory=_inventory(tmp_path, [_DEPLOY_KEY_ROW]),
        origin_url=_origin,
    )
    result = run_nic(deps, action="validate", config=config)
    assert result.ok is False
    assert result.details.get("exit_code") == EXIT_USAGE
    assert DOTENV_RELATIVE.as_posix() in result.summary


def test_run_nic_unknown_action_and_missing_config(tmp_path: Path) -> None:
    deps = NicDeps(root=tmp_path, runner=lambda *_a, **_k: _Proc(), nic_executable=lambda: "/usr/bin/nic")
    bad_action = run_nic(deps, action="fly", config=tmp_path / "x.yaml")
    assert bad_action.ok is False
    assert "unknown action" in bad_action.summary
    missing = run_nic(deps, action="validate", config=tmp_path / "nope.yaml")
    assert missing.ok is False
    assert "does not exist" in missing.summary


def test_run_nic_refuses_invalid_yaml_and_non_mapping(tmp_path: Path) -> None:
    deps = NicDeps(root=tmp_path, runner=lambda *_a, **_k: _Proc(), nic_executable=lambda: "/usr/bin/nic")
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(":\n  - [unclosed", encoding="utf-8")
    result = run_nic(deps, action="validate", config=bad_yaml)
    assert result.ok is False
    assert "not valid YAML" in result.summary
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("just-a-string\n", encoding="utf-8")
    result = run_nic(deps, action="validate", config=scalar)
    assert result.ok is False
    assert "must be a YAML mapping" in result.summary


def test_run_nic_refuses_when_nic_binary_missing(tmp_path: Path) -> None:
    config = _local_config(tmp_path)
    deps = NicDeps(root=tmp_path, runner=lambda *_a, **_k: _Proc(), nic_executable=lambda: None)
    result = run_nic(deps, action="validate", config=config)
    assert result.ok is False
    assert "nic is not installed" in result.summary


def test_run_nic_surfaces_subprocess_failure_tail(tmp_path: Path) -> None:
    config = _local_config(tmp_path)

    def runner(_argv: list[str], _cwd: Path, _env: dict[str, str]) -> _Proc:
        return _Proc(returncode=3, stderr="line one\nfinal error\n")

    deps = NicDeps(root=tmp_path, runner=runner, nic_executable=lambda: "/usr/bin/nic")
    result = run_nic(deps, action="validate", config=config)
    assert result.ok is False
    assert result.details.get("exit_code") == 3
    assert "final error" in result.summary


def test_run_deploy_nic_usage_and_dispatch(tmp_path: Path) -> None:
    class _Ns:
        deploy_nic_verb: str | None = None
        config: str | None = None
        _nic_deps: NicDeps | None = None

    usage = run_deploy_nic(_Ns())
    assert usage.ok is False
    assert "usage" in usage.summary

    config = _local_config(tmp_path)
    ns = _Ns()
    ns.deploy_nic_verb = "validate"
    ns.config = str(config)
    ns._nic_deps = NicDeps(
        root=tmp_path,
        runner=lambda *_a, **_k: _Proc(),
        nic_executable=lambda: "/usr/bin/nic",
    )
    result = run_deploy_nic(ns)
    assert result.ok is True


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


# --- Story 118.9 (spec-pyforge-steward CAP-178, CAP-176): the gitops branch is guarded before any cloud run ---

GITOPS_FLAG = "pyforge.steward.nkp_gitops_branch"
NIC_VERB = {"validate": "validate", "up": "deploy", "kubeconfig": "kubeconfig", "outputs": "outputs", "down": "destroy"}


ORIGIN = "git@github.com:org/repo.git"
DEPLOY_KEY_AUTH = {"ssh": {"env": "GITOPS_DEPLOY_KEY"}}


def _origin(_root: Path) -> str:
    return ORIGIN


_NO_PROJECT = object()


def _existing_config(
    tmp_path: Path,
    branch: str,
    *,
    cluster: dict | None = None,
    auth: dict | None = DEPLOY_KEY_AUTH,
    url: str = ORIGIN,
    project_name: object = "my-nebari-hetzner",
) -> Path:
    existing: dict = {"url": url, "branch": branch, "path": f"gitops/{branch}"}
    if auth is not None:
        existing["auth"] = auth
    document: dict = {
        "domain": "example.invalid",
        "repository": {"existing": existing},
        "cluster": cluster if cluster is not None else {"hetzner": {"location": "ash"}},
    }
    if project_name is not _NO_PROJECT:
        document["project_name"] = project_name
    path = tmp_path / "my-nebari-hetzner.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def _recording_deps(tmp_path: Path, calls: list[list[str]], **outputs: _Proc) -> NicDeps:
    """A runner that records argv and answers ``git log`` / ``git fetch`` / nic from ``outputs``."""

    def runner(argv: list[str], _cwd: Path, _env: dict[str, str]) -> _Proc:
        calls.append(list(argv))
        if argv[:2] == ["git", "fetch"]:
            return outputs.get("fetch", _Proc())
        if argv[:2] == ["git", "log"]:
            return outputs.get("log", _Proc(stdout="commit abc\n+kind: Application\n"))
        return outputs.get("nic", _Proc())

    return NicDeps(
        root=tmp_path,
        runner=runner,
        nic_executable=lambda: "/usr/bin/nic",
        decrypt=lambda _age, _id: "synthetic-deploy-key",
        inventory=_inventory(tmp_path, [_DEPLOY_KEY_ROW]),
        origin_url=_origin,
    )


def _flag_on(monkeypatch: pytest.MonkeyPatch, value: bool = True) -> None:
    monkeypatch.setattr("pyforge.core.flags.read_boolean", lambda key, default=False, **_kw: value)


@pytest.fixture
def gitops_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Flag ON and the deploy key resolvable through keys: an age identity, ``.env`` and its payload.

    ``_recording_deps`` supplies the inventory row, the decryption and ``origin``.
    """
    _flag_on(monkeypatch)
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-PLACEHOLDER", encoding="utf-8")
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(identity))
    (tmp_path / "deploy-key.age").write_bytes(b"AGE[FAKE]")
    (tmp_path / DOTENV_RELATIVE).write_text("GITOPS_DEPLOY_KEY=deploy-key.age\n", encoding="utf-8")


@pytest.mark.parametrize(
    "branch",
    [
        "main",
        "feature/x",
        "",
        "gitops/",
        "refs/heads/main",
        # Story 118.9 review: the raw value is checked, whole, against gitops/<project_name>.
        "gitops/../main",
        "gitops/x:refs/heads/main",
        "gitops//",
        "gitops/x\nmain",
        " gitops/x ",
        "gitops/my-nebari-hetzner ",
        "gitops/.hidden",
        "gitops/x.lock",
        "gitops/other-name",
    ],
)
@pytest.mark.parametrize("action", ["validate", "up", "kubeconfig", "outputs", "down"])
def test_every_action_refuses_a_branch_outside_gitops_before_nic_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str, branch: str
) -> None:
    _flag_on(monkeypatch)
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls)
    result = run_nic(deps, action=action, config=_existing_config(tmp_path, branch), yes=True)
    assert result.ok is False
    assert result.details["exit_code"] == EXIT_USAGE
    assert "never main" in result.summary
    assert calls == []


def test_up_on_main_is_refused_with_usage_code_two_and_no_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag_on(monkeypatch)
    calls: list[list[str]] = []
    result = run_nic(_recording_deps(tmp_path, calls), action="up", config=_existing_config(tmp_path, "main"), yes=True)
    assert (result.ok, result.details["exit_code"], calls) == (False, EXIT_USAGE, [])


def test_a_gitops_branch_is_accepted(tmp_path: Path, gitops_ready: None) -> None:
    calls: list[list[str]] = []
    config = _existing_config(tmp_path, "gitops/my-nebari-hetzner")
    result = run_nic(_recording_deps(tmp_path, calls), action="validate", config=config)
    assert result.ok is True
    assert calls == [["/usr/bin/nic", "validate", "-f", str(config)]]


@flag_states(GITOPS_FLAG)
def test_the_gitops_branch_flag_in_both_states(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gitops_ready: None
) -> None:
    # Switch the key the way deploy_nic reads it (pyforge.core.flags.read_boolean), never by test order.
    monkeypatch.setattr(
        "pyforge.core.flags.read_boolean", lambda key, default=False, **_kw: flag_provider.get(key, default)
    )
    existing = _existing_config(tmp_path, "gitops/my-nebari-hetzner")
    local = _local_config(tmp_path)
    for action in ("validate", "up", "kubeconfig", "outputs", "down"):
        calls: list[list[str]] = []
        result = run_nic(_recording_deps(tmp_path, calls), action=action, config=existing, yes=True)
        if flag_provider[GITOPS_FLAG]:
            assert result.ok is True, result.summary
            assert calls and calls[0][:2] == ["/usr/bin/nic", NIC_VERB[action]]
        else:
            assert result.ok is False
            assert result.details["exit_code"] == EXIT_USAGE
            assert GITOPS_FLAG in result.summary
            assert calls == []
        # kind's repository.local is unaffected in either state.
        calls = []
        assert run_nic(_recording_deps(tmp_path, calls), action=action, config=local).ok is True
        assert calls[0][:2] == ["/usr/bin/nic", NIC_VERB[action]]


def test_a_non_local_up_needs_the_operators_yes(tmp_path: Path, gitops_ready: None) -> None:
    config = _existing_config(tmp_path, "gitops/my-nebari-hetzner")
    calls: list[list[str]] = []
    refused = run_nic(_recording_deps(tmp_path, calls), action="up", config=config)
    assert (refused.ok, refused.details["exit_code"], calls) == (False, EXIT_USAGE, [])
    assert "--yes" in refused.summary
    consented = run_nic(_recording_deps(tmp_path, calls), action="up", config=config, yes=True)
    assert consented.ok is True, consented.summary
    assert calls[0] == ["/usr/bin/nic", "deploy", "-f", str(config)]
    # A config with no cluster provider is not local kind either (and, with no repository.existing, is refused
    # for every action before the consent gate is reached).
    bare = tmp_path / "bare.yaml"
    bare.write_text(yaml.safe_dump({"project_name": "x", "repository": {"local": {}}}), encoding="utf-8")
    calls.clear()
    assert run_nic(_recording_deps(tmp_path, calls), action="up", config=bare).details["exit_code"] == EXIT_USAGE
    assert calls == []


def test_kind_up_and_every_other_action_need_no_yes(tmp_path: Path, gitops_ready: None) -> None:
    config = _existing_config(tmp_path, "gitops/my-nebari-hetzner")
    for action in ("validate", "kubeconfig", "outputs", "down"):
        calls: list[list[str]] = []
        assert run_nic(_recording_deps(tmp_path, calls), action=action, config=config).ok is True
    calls = []
    assert run_nic(_recording_deps(tmp_path, calls), action="up", config=_local_config(tmp_path)).ok is True


def test_the_parser_takes_yes_on_up_only(capsys: pytest.CaptureFixture[str]) -> None:
    from pyforge.steward.cli import build_parser

    parser = build_parser()
    assert parser.parse_args(["deploy", "nic", "up", "-f", "c.yaml", "--yes"]).yes is True
    assert parser.parse_args(["deploy", "nic", "up", "-f", "c.yaml"]).yes is False
    for action in ("validate", "kubeconfig", "outputs", "down"):
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["deploy", "nic", action, "-f", "c.yaml", "--yes"])
        assert exc.value.code == EXIT_USAGE
    capsys.readouterr()


def test_run_deploy_nic_hands_yes_to_run_nic(tmp_path: Path, gitops_ready: None) -> None:
    calls: list[list[str]] = []

    class _Ns:
        deploy_nic_verb = "up"
        config = str(_existing_config(tmp_path, "gitops/my-nebari-hetzner"))
        yes = True
        _nic_deps = _recording_deps(tmp_path, calls)

    assert run_deploy_nic(_Ns()).ok is True
    _Ns.yes = False
    calls.clear()
    assert run_deploy_nic(_Ns()).details["exit_code"] == EXIT_USAGE
    assert calls == []


def test_the_summary_never_echoes_a_secret_shaped_last_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    planted = "AGE-SECRET-KEY-1TEST00FAKE00PLACEHOLDER00NOTREAL00SYNTHETIC"
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls, nic=_Proc(returncode=1, stderr=f"first\nfailed reading {planted}\n"))
    result = run_nic(deps, action="validate", config=_local_config(tmp_path))
    assert result.details["exit_code"] == 1
    assert "nic validate exited 1" in result.summary
    assert planted not in result.summary
    assert "***" in result.summary


def test_the_summary_never_echoes_a_secret_the_verb_resolved(tmp_path: Path, gitops_ready: None) -> None:
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls, nic=_Proc(returncode=2, stderr="auth failed for opaque-resolved-value\n"))
    deps.decrypt = lambda _age, _id: "opaque-resolved-value"
    result = run_nic(deps, action="validate", config=_config_needing_token(tmp_path))
    assert "opaque-resolved-value" not in result.summary
    assert "auth failed for ***" in result.summary


# Synthetic, word-marked key material: never a real key.
_KEY_BODY = "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW"
_MULTILINE_KEY = (
    f"-----BEGIN OPENSSH PRIVATE KEY-----\n{_KEY_BODY}\nSYNTHETICBODYLINE2\n-----END OPENSSH PRIVATE KEY-----"
)


@pytest.mark.parametrize(
    "last_line",
    [
        "parse key: " + json.dumps(_MULTILINE_KEY),  # the key escaped onto one line (literal backslash-n)
        f"bad line {_KEY_BODY}",  # one body line alone
        "bad line SYNTHETICBODYLINE2",
    ],
    ids=["escaped-pem", "body-line", "second-body-line"],
)
def test_the_summary_never_echoes_a_multiline_key_the_verb_resolved(
    tmp_path: Path, gitops_ready: None, last_line: str
) -> None:
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls, nic=_Proc(returncode=1, stderr=f"first\n{last_line}\n"))
    deps.decrypt = lambda _age, _id: _MULTILINE_KEY
    result = run_nic(deps, action="validate", config=_deploy_key_config(tmp_path))
    assert result.details["exit_code"] == 1
    for fragment in (_KEY_BODY, _KEY_BODY[:16], "SYNTHETICBODYLINE2", "PRIVATE KEY"):
        assert fragment not in result.summary
    assert "***" in result.summary


def test_a_cloud_up_scans_the_pushed_range(tmp_path: Path, gitops_ready: None) -> None:
    config = _existing_config(tmp_path, "gitops/my-nebari-hetzner")
    calls: list[list[str]] = []
    clean = run_nic(_recording_deps(tmp_path, calls), action="up", config=config, yes=True)
    assert clean.ok is True, clean.summary
    # Every commit's whole diff: binary as text, no external diff or textconv, merges vs their first parent.
    assert [
        "git",
        "log",
        "-p",
        "--text",
        "--no-ext-diff",
        "--no-textconv",
        "--diff-merges=first-parent",
        "--no-color",
        "--format=commit %H",
        "origin/main..origin/gitops/my-nebari-hetzner",
    ] in calls
    fetch = next(argv for argv in calls if argv[:2] == ["git", "fetch"])
    assert "+refs/heads/gitops/my-nebari-hetzner:refs/remotes/origin/gitops/my-nebari-hetzner" in fetch


def test_the_range_scan_refuses_a_planted_secret(tmp_path: Path, gitops_ready: None) -> None:
    planted = "-----BEGIN OPENSSH PRIVATE KEY-----"
    log = _Proc(stdout=f"commit abc\n+values:\n+  key: |\n+    {planted}\n")
    calls: list[list[str]] = []
    result = run_nic(
        _recording_deps(tmp_path, calls, log=log),
        action="up",
        config=_existing_config(tmp_path, "gitops/my-nebari-hetzner"),
        yes=True,
    )
    assert result.ok is False
    assert result.details["exit_code"] == 1
    assert "pem-private-key-header" in result.summary
    assert planted not in result.summary


@pytest.mark.parametrize("failing", ["fetch", "log"])
def test_the_range_scan_fails_closed_when_it_cannot_read(tmp_path: Path, gitops_ready: None, failing: str) -> None:
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls, **{failing: _Proc(returncode=128, stderr="fatal")})
    result = run_nic(deps, action="up", config=_existing_config(tmp_path, "gitops/my-nebari-hetzner"), yes=True)
    assert result.ok is False
    assert result.details["exit_code"] == 1
    assert "could not read" in result.summary


def test_kind_up_never_runs_the_range_scan(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    assert run_nic(_recording_deps(tmp_path, calls), action="up", config=_local_config(tmp_path)).ok is True
    assert not any(argv[0] == "git" for argv in calls)


def _deploy_key_config(tmp_path: Path) -> Path:
    return _existing_config(tmp_path, "gitops/my-nebari-hetzner", auth=DEPLOY_KEY_AUTH)


def _inventory(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / ".steward" / "keys-inventory.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"identities": rows}), encoding="utf-8")
    return path


_DEPLOY_KEY_ROW = {
    "name": "GITOPS_DEPLOY_KEY",
    "scope": "operator-owned-scope",
    "provenance": "issued",
    "status": "active",
    "last_rotated": None,
    "identity_path": None,
    "secrets": [],
}


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{**_DEPLOY_KEY_ROW, "status": "retired"}],
        [{**_DEPLOY_KEY_ROW, "provenance": "observed"}],
        [_DEPLOY_KEY_ROW, _DEPLOY_KEY_ROW],
    ],
    ids=["no-row", "retired", "observed", "two-rows"],
)
def test_keys_refuses_the_deploy_key_without_its_inventory_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rows: list[dict]
) -> None:
    _flag_on(monkeypatch)
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls)
    deps.inventory = _inventory(tmp_path, rows)
    result = run_nic(deps, action="validate", config=_deploy_key_config(tmp_path))
    assert result.ok is False
    assert result.details["exit_code"] == EXIT_USAGE
    assert "keys will not resolve GITOPS_DEPLOY_KEY" in result.summary
    assert DOTENV_RELATIVE.as_posix() not in result.summary  # refused before .env is read
    assert calls == []


def test_keys_refuses_an_unreadable_inventory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _flag_on(monkeypatch)
    inventory = tmp_path / "keys-inventory.yaml"
    inventory.write_text("- not\n- a mapping\n", encoding="utf-8")
    deps = _recording_deps(tmp_path, [])
    deps.inventory = inventory
    result = run_nic(deps, action="validate", config=_deploy_key_config(tmp_path))
    assert result.details["exit_code"] == EXIT_USAGE
    assert "cannot be read" in result.summary


def test_the_deploy_key_resolves_through_keys_with_its_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _flag_on(monkeypatch)
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-PLACEHOLDER", encoding="utf-8")
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(identity))
    (tmp_path / "deploy-key.age").write_bytes(b"AGE[FAKE]")
    (tmp_path / DOTENV_RELATIVE).write_text("GITOPS_DEPLOY_KEY=deploy-key.age\n", encoding="utf-8")
    seen: list[dict[str, str]] = []

    def runner(argv: list[str], _cwd: Path, env: dict[str, str]) -> _Proc:
        seen.append(env)
        return _Proc()

    deps = NicDeps(
        root=tmp_path,
        runner=runner,
        nic_executable=lambda: "/usr/bin/nic",
        decrypt=lambda _age, _id: "synthetic-deploy-key",
        inventory=_inventory(tmp_path, [_DEPLOY_KEY_ROW]),
        origin_url=_origin,
    )
    assert run_nic(deps, action="validate", config=_deploy_key_config(tmp_path)).ok is True
    assert seen[0]["GITOPS_DEPLOY_KEY"] == "synthetic-deploy-key"


# --- Story 118.9 review: the deploy key is the only auth, origin is the only repository, a cloud config needs both ---


@pytest.mark.parametrize(
    "auth",
    [
        {"ssh": {"env": "OTHER_DEPLOY_KEY"}},
        {"token": {"env": "GIT_TOKEN"}},
        {"token": {"env": "GITOPS_DEPLOY_KEY"}},
        {"ssh": {"env": "GITOPS_DEPLOY_KEY"}, "token": {"env": "GIT_TOKEN"}},
        None,
    ],
    ids=["other-ssh-env", "token", "token-named-like-the-key", "ssh-and-token", "no-auth"],
)
@pytest.mark.parametrize("action", ["validate", "up"])
def test_a_repository_existing_auth_other_than_the_deploy_key_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, auth: dict | None, action: str
) -> None:
    _flag_on(monkeypatch)
    calls: list[list[str]] = []
    config = _existing_config(tmp_path, "gitops/my-nebari-hetzner", auth=auth)
    result = run_nic(_recording_deps(tmp_path, calls), action=action, config=config, yes=True)
    assert (result.ok, result.details["exit_code"], calls) == (False, EXIT_USAGE, [])
    assert "auth.ssh.env: GITOPS_DEPLOY_KEY" in result.summary


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:org/repo.git",
        "https://github.com/org/repo",
        "https://github.com/org/repo.git",
        "ssh://git@github.com/org/repo.git",
        "git@GitHub.com:ORG/Repo.git",
    ],
)
def test_every_github_spelling_of_origins_repository_is_accepted(tmp_path: Path, gitops_ready: None, url: str) -> None:
    calls: list[list[str]] = []
    config = _existing_config(tmp_path, "gitops/my-nebari-hetzner", url=url)
    result = run_nic(_recording_deps(tmp_path, calls), action="validate", config=config)
    assert result.ok is True, result.summary


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:other/repo.git",
        "https://github.com/org/other",
        "https://gitlab.com/org/repo.git",
        "file:///tmp/repo.git",
    ],
)
@pytest.mark.parametrize("action", ["validate", "up", "down"])
def test_a_repository_existing_url_other_than_origin_is_refused_before_nic_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str, action: str
) -> None:
    _flag_on(monkeypatch)
    calls: list[list[str]] = []
    config = _existing_config(tmp_path, "gitops/my-nebari-hetzner", url=url)
    result = run_nic(_recording_deps(tmp_path, calls), action=action, config=config, yes=True)
    assert (result.ok, result.details["exit_code"], calls) == (False, EXIT_USAGE, [])
    assert "repository.existing.url" in result.summary


@pytest.mark.parametrize("origin", [None, "/srv/mirror/repo.git"])
def test_an_origin_steward_cannot_compare_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origin: str | None
) -> None:
    _flag_on(monkeypatch)
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls)
    deps.origin_url = lambda _root: origin
    result = run_nic(deps, action="validate", config=_existing_config(tmp_path, "gitops/my-nebari-hetzner"))
    assert (result.ok, result.details["exit_code"], calls) == (False, EXIT_USAGE, [])
    assert "origin" in result.summary


def test_the_default_origin_reader_reads_the_checkout_remote(tmp_path: Path) -> None:
    import subprocess

    from pyforge.steward.deploy_nic import _origin_url

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    assert _origin_url(tmp_path) is None
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin", ORIGIN], check=True)
    assert _origin_url(tmp_path) == ORIGIN
    assert _origin_url(tmp_path / "not-a-checkout") is None


@pytest.mark.parametrize(
    "repository",
    [{"local": {}}, None],
    ids=["repository-local", "no-repository"],
)
@pytest.mark.parametrize("action", ["validate", "up", "kubeconfig", "outputs", "down"])
def test_a_cloud_config_without_repository_existing_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repository: dict | None, action: str
) -> None:
    _flag_on(monkeypatch)
    document: dict = {"project_name": "my-nebari-hetzner", "cluster": {"hetzner": {"location": "ash"}}}
    if repository is not None:
        document["repository"] = repository
    config = tmp_path / "cloud.yaml"
    config.write_text(yaml.safe_dump(document), encoding="utf-8")
    calls: list[list[str]] = []
    result = run_nic(_recording_deps(tmp_path, calls), action=action, config=config, yes=True)
    assert (result.ok, result.details["exit_code"], calls) == (False, EXIT_USAGE, [])
    assert "needs repository.existing" in result.summary


# --- Story 118.9 second review ---------------------------------------------------------------------

# Synthetic, word-marked credentials, assembled at run time: never a real token.
_GH_TOKEN = "ghp_" + "Synthetic0Fake0Placeholder0NotReal00"
_PASSWORD = "hunter2-not-a-real-password"


def test_a_token_bearing_origin_of_the_right_repository_is_accepted(tmp_path: Path, gitops_ready: None) -> None:
    deps = _recording_deps(tmp_path, [])
    deps.origin_url = lambda _root: f"https://x-access-token:{_GH_TOKEN}@github.com/org/repo.git"
    result = run_nic(deps, action="validate", config=_existing_config(tmp_path, "gitops/my-nebari-hetzner"))
    assert result.ok is True, result.summary


@pytest.mark.parametrize(
    ("origin", "url"),
    [
        (f"https://x-access-token:{_GH_TOKEN}@github.com/other/repo.git", ORIGIN),
        (f"https://oauth2:{_PASSWORD}@gitlab.com/org/repo.git", ORIGIN),
        (ORIGIN, f"https://deploy:{_PASSWORD}@gitlab.com/org/repo.git"),
        (ORIGIN, f"https://x-access-token:{_GH_TOKEN}@github.com/org/other.git?access_token={_PASSWORD}"),
    ],
    ids=["origin-token-other-repo", "origin-token-not-github", "url-password-not-github", "url-token-other-repo"],
)
def test_a_url_refusal_never_prints_a_credential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origin: str, url: str
) -> None:
    _flag_on(monkeypatch)
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls)
    deps.origin_url = lambda _root: origin
    result = run_nic(deps, action="validate", config=_existing_config(tmp_path, "gitops/my-nebari-hetzner", url=url))
    assert (result.ok, result.details["exit_code"], calls) == (False, EXIT_USAGE, [])
    for secret in (_GH_TOKEN, _PASSWORD, "x-access-token", "oauth2:", "@"):
        assert secret not in result.summary


@pytest.mark.parametrize("nic_exit", [1, 3])
def test_a_failed_cloud_up_is_still_scanned_and_a_finding_is_exit_one(
    tmp_path: Path, gitops_ready: None, nic_exit: int
) -> None:
    calls: list[list[str]] = []
    log = _Proc(stdout="commit abc\n+key: -----BEGIN OPENSSH PRIVATE KEY-----\n")
    deps = _recording_deps(tmp_path, calls, nic=_Proc(returncode=nic_exit, stderr="apply failed\n"), log=log)
    result = run_nic(deps, action="up", config=_existing_config(tmp_path, "gitops/my-nebari-hetzner"), yes=True)
    assert result.ok is False
    assert result.details["exit_code"] == 1
    assert f"nic deploy exited {nic_exit}" in result.summary and "pem-private-key-header" in result.summary


def test_an_unreadable_range_after_a_failed_up_keeps_nics_code(tmp_path: Path, gitops_ready: None) -> None:
    calls: list[list[str]] = []
    deps = _recording_deps(
        tmp_path, calls, nic=_Proc(returncode=3, stderr="push failed\n"), fetch=_Proc(returncode=128, stderr="fatal")
    )
    result = run_nic(deps, action="up", config=_existing_config(tmp_path, "gitops/my-nebari-hetzner"), yes=True)
    assert result.ok is False
    assert result.details["exit_code"] == 3
    assert "nic deploy exited 3" in result.summary and "could not read" in result.summary
    assert any(argv[:2] == ["git", "fetch"] for argv in calls)


def test_a_clean_range_after_a_failed_up_keeps_nics_code(tmp_path: Path, gitops_ready: None) -> None:
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls, nic=_Proc(returncode=3, stderr="apply failed\n"))
    result = run_nic(deps, action="up", config=_existing_config(tmp_path, "gitops/my-nebari-hetzner"), yes=True)
    assert (result.ok, result.details["exit_code"]) == (False, 3)
    assert any(argv[:2] == ["git", "log"] for argv in calls)


_SLASHED_BODY = "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQ/AAAAAAAAABAAAAMwAAAA+tzc2gt/ZW"
_SLASHED_KEY = f"-----BEGIN OPENSSH PRIVATE KEY-----\n{_SLASHED_BODY}\n-----END OPENSSH PRIVATE KEY-----\n"


def test_a_json_dumped_key_with_escaped_slashes_leaves_no_body_in_the_summary(
    tmp_path: Path, gitops_ready: None
) -> None:
    escaped = json.dumps({"key": _SLASHED_KEY}).replace("/", "\\/")
    calls: list[list[str]] = []
    deps = _recording_deps(tmp_path, calls, nic=_Proc(returncode=1, stderr=f"first\nbad config {escaped}\n"))
    deps.decrypt = lambda _age, _id: _SLASHED_KEY
    result = run_nic(deps, action="validate", config=_deploy_key_config(tmp_path))
    for fragment in ("b3BlbnNzaC1rZXkt", "tzc2gt", "AAAAMwAAAA", "PRIVATE KEY"):
        assert fragment not in result.summary
    assert "bad config" in result.summary


@pytest.mark.parametrize(
    "project_name",
    [_NO_PROJECT, "", 5, None, " my-nebari-hetzner ", "my-nebari-hetzner "],
    ids=["missing", "empty", "not-a-string", "null", "surrounding-whitespace", "trailing-whitespace"],
)
@pytest.mark.parametrize("action", ["validate", "up"])
def test_a_repository_existing_config_needs_a_project_name_as_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, project_name: object, action: str
) -> None:
    _flag_on(monkeypatch)
    calls: list[list[str]] = []
    config = _existing_config(tmp_path, "gitops/my-nebari-hetzner", project_name=project_name)
    result = run_nic(_recording_deps(tmp_path, calls), action=action, config=config, yes=True)
    assert (result.ok, result.details["exit_code"], calls) == (False, EXIT_USAGE, [])
    assert "project_name" in result.summary


def test_a_branch_segment_ending_in_a_dot_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _flag_on(monkeypatch)
    calls: list[list[str]] = []
    config = _existing_config(tmp_path, "gitops/my-nebari-hetzner.", project_name="my-nebari-hetzner.")
    result = run_nic(_recording_deps(tmp_path, calls), action="validate", config=config)
    assert (result.ok, result.details["exit_code"], calls) == (False, EXIT_USAGE, [])
    assert "is not a valid ref name" in result.summary


def test_a_url_with_a_query_is_not_a_github_repository_url() -> None:
    from pyforge.steward.deploy_nic import github_owner_repo, shown_remote

    assert github_owner_repo("https://github.com/org/repo.git?ref=x") is None
    assert github_owner_repo(f"https://user:{_PASSWORD}@github.com/Org/Repo") == ("org", "repo")
    assert github_owner_repo("git@github.com:org/repo.git") == ("org", "repo")
    assert shown_remote(f"https://user:{_PASSWORD}@gitlab.com:8443/o/r.git?t={_PASSWORD}#x") == "gitlab.com/o/r"
    assert shown_remote(None) == "(none)"
    assert shown_remote("git@github.com:org/repo.git") == "github.com/org/repo"
    assert shown_remote("/srv/mirror/repo.git") == "srv/mirror/repo"
