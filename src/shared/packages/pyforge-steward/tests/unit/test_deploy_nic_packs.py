"""``deploy nic`` NKP packs — Story 118.2 (CAP-177)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

from pyforge.steward.deploy_nic import NicDeps, run_nic
from pyforge.steward.deploy_nic_packs import (
    PACK_JOURNAL_RELATIVE,
    PackDeps,
    PackSpec,
    apply_nkp_packs,
    chart_digest,
    collect_pull_manifest,
    git_commit_applications,
    gitops_root_for,
    label_pack_namespaces,
    parse_packs,
    render_application,
    wait_applications_healthy,
    write_pack_applications,
)

flag_provider = make_flag_provider_fixture()


class _Proc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _pack_config(tmp_path: Path) -> Path:
    document = {
        "project_name": "my-nebari-local",
        "domain": "nebari.local",
        "repository": {"local": {}},
        "packs": {
            "nebi-pack": {
                "chart": "nebari-nebi-pack",
                "version": "0.1.0",
                "namespace": "nebi",
            },
            "data-science-pack": {
                "chart": "nebari-data-science-pack",
                "version": "0.1.7",
                "namespace": "data-science",
                "values": {
                    "keycloak": {"hostname": "keycloak.nebari.local"},
                    "sharedStorage": {"nfsServer": {"enabled": True}},
                    "nebi": {"remote": {"enabled": True}},
                },
            },
        },
    }
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def test_parse_packs_none_when_absent() -> None:
    specs, failure = parse_packs({"project_name": "x"})
    assert failure is None
    assert specs is None


def test_parse_packs_refuses_empty_mapping() -> None:
    _, failure = parse_packs({"packs": {}})
    assert failure is not None
    assert failure.ok is False


def test_parse_packs_refuses_unknown_pack_key() -> None:
    _, failure = parse_packs({"packs": {"other-pack": {"chart": "c", "version": "1.0.0", "namespace": "ns"}}})
    assert failure is not None
    assert "unknown pack keys" in failure.summary


def test_parse_packs_merges_data_science_defaults() -> None:
    specs, failure = parse_packs(
        {
            "packs": {
                "data-science-pack": {
                    "chart": "nebari-data-science-pack",
                    "version": "0.1.7",
                    "namespace": "data-science",
                    "values": {"keycloak": {"hostname": "custom.local"}},
                },
            }
        }
    )
    assert failure is None
    assert specs is not None
    assert specs[0].values["keycloak"]["hostname"] == "custom.local"
    assert specs[0].values["nebi"]["remote"]["enabled"] is True


def test_gitops_root_for_local_repository() -> None:
    root, failure = gitops_root_for({"project_name": "demo", "repository": {"local": {}}})
    assert failure is None
    assert root == Path.home() / ".nic" / "gitops" / "demo"


def test_gitops_root_for_refuses_missing_project_name() -> None:
    root, failure = gitops_root_for({"repository": {"local": {}}})
    assert root is None
    assert failure is not None
    assert failure.ok is False


def test_collect_pull_manifest_includes_digest_when_present() -> None:
    spec = PackSpec(name="nebi-pack", chart="nebari-nebi-pack", version="0.1.0", namespace="nebi")
    rows = collect_pull_manifest([spec], {"nebi-pack": "sha256:abc"})
    assert rows[0]["chart_digest"] == "sha256:abc"


def test_git_commit_applications_no_paths_is_ok(tmp_path: Path) -> None:
    deps = PackDeps(gitops_root=tmp_path, runner=lambda *_a, **_k: _Proc())
    assert git_commit_applications(deps, []).ok is True


def test_label_pack_namespaces_surfaces_kubectl_failure() -> None:
    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["kubectl", "label"]:
            return _Proc(returncode=1, stderr="forbidden")
        return _Proc()

    spec = PackSpec(name="nebi-pack", chart="c", version="1.0.0", namespace="nebi")
    result = label_pack_namespaces(PackDeps(gitops_root=Path("/tmp"), runner=runner), [spec])
    assert result.ok is False
    assert "forbidden" in result.summary


def test_wait_applications_healthy_surfaces_timeout() -> None:
    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["kubectl", "wait"]:
            return _Proc(returncode=1, stderr="timed out")
        return _Proc()

    spec = PackSpec(name="nebi-pack", chart="c", version="1.0.0", namespace="nebi")
    result = wait_applications_healthy(PackDeps(gitops_root=Path("/tmp"), runner=runner), [spec], timeout_s=1)
    assert result.ok is False
    assert "timed out" in result.summary


def test_chart_digest_parses_helm_output() -> None:
    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["helm", "pull"]:
            return _Proc(stderr="Digest: sha256:feedface\n")
        return _Proc()

    spec = PackSpec(name="nebi-pack", chart="nebari-nebi-pack", version="0.1.0", namespace="nebi")
    assert chart_digest(PackDeps(gitops_root=Path("/tmp"), runner=runner), spec) == "sha256:feedface"


@pytest.mark.parametrize(
    ("packs", "snippet"),
    [
        ({"nebi-pack": "not-a-mapping"}, "must be a mapping"),
        ({"nebi-pack": {"version": "1.0.0", "namespace": "n"}}, "chart is required"),
        ({"nebi-pack": {"chart": "c", "version": "latest", "namespace": "n"}}, "not latest"),
        ({"nebi-pack": {"chart": "c", "version": "1.0.0"}}, "namespace is required"),
        ({"nebi-pack": {"chart": "c", "version": "1.0.0", "namespace": "n", "values": []}}, "values must be"),
    ],
)
def test_parse_packs_validation_errors(packs: dict[str, object], snippet: str) -> None:
    _, failure = parse_packs({"packs": packs})
    assert failure is not None
    assert snippet in failure.summary


def test_gitops_root_for_existing_repository() -> None:
    root, failure = gitops_root_for({"project_name": "demo", "repository": {"existing": {}}})
    assert failure is None
    assert root == Path.home() / ".nic" / "gitops" / "demo"


def test_gitops_root_for_refuses_unsupported_repository() -> None:
    root, failure = gitops_root_for({"project_name": "demo", "repository": {"remote": {}}})
    assert root is None
    assert failure is not None
    assert "repository.local or repository.existing" in failure.summary


def test_git_commit_applications_refuses_missing_gitops(tmp_path: Path) -> None:
    deps = PackDeps(gitops_root=tmp_path / "missing", runner=lambda *_a, **_k: _Proc())
    result = git_commit_applications(deps, [tmp_path / "apps" / "x.yaml"])
    assert result.ok is False
    assert "does not exist" in result.summary


def test_apply_nkp_packs_surfaces_parse_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch the reader, never pin PYFORGE_FLAGS_PATH to a one-key tree: the FILE provider stays
    # pinned to that tree for later tests in the same worker and every other flag reads WARN.
    monkeypatch.setattr("pyforge.core.flags.read_boolean", lambda _key, default=False, **_kw: True)
    outcome = apply_nkp_packs(repo_root=tmp_path, document={"packs": {}})
    assert outcome is not None
    assert outcome.ok is False


def test_apply_nkp_packs_uses_custom_journal_callback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch the reader, never pin PYFORGE_FLAGS_PATH to a one-key tree: the FILE provider stays
    # pinned to that tree for later tests in the same worker and every other flag reads WARN.
    monkeypatch.setattr("pyforge.core.flags.read_boolean", lambda _key, default=False, **_kw: True)
    gitops = tmp_path / "gitops"
    gitops.mkdir()
    document = {
        "project_name": "p",
        "repository": {"local": {}},
        "packs": {
            "nebi-pack": {"chart": "nebari-nebi-pack", "version": "0.1.0", "namespace": "nebi"},
        },
    }
    monkeypatch.setattr(
        "pyforge.steward.deploy_nic_packs.gitops_root_for",
        lambda _doc: (gitops, None),
    )
    journal_rows: list[dict[str, object]] = []

    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["git", "status"]:
            return _Proc(stdout="")
        if argv[:2] == ["kubectl", "wait"]:
            return _Proc()
        if argv[:2] == ["kubectl", "label"]:
            return _Proc()
        if argv[:2] == ["helm", "pull"]:
            return _Proc()
        return _Proc()

    outcome = apply_nkp_packs(
        repo_root=tmp_path,
        document=document,
        pack_deps=PackDeps(gitops_root=gitops, runner=runner),
        journal=lambda row: journal_rows.append(row),
    )
    assert outcome is not None and outcome.ok is True
    assert journal_rows
    assert not (tmp_path / PACK_JOURNAL_RELATIVE).is_file()


def test_render_application_uses_oci_and_namespace() -> None:
    spec = PackSpec(
        name="nebi-pack",
        chart="nebari-nebi-pack",
        version="0.1.0",
        namespace="nebi",
    )
    app = render_application(spec)
    assert app["metadata"]["name"] == "nebi-pack"
    assert app["spec"]["source"]["repoURL"] == "oci://quay.io/nebari/charts/nebari-nebi-pack"
    assert app["spec"]["destination"]["namespace"] == "nebi"


def test_write_pack_applications_orders_nebi_before_data_science(tmp_path: Path) -> None:
    gitops = tmp_path / "gitops"
    specs, _ = parse_packs(
        {
            "packs": {
                "data-science-pack": {
                    "chart": "nebari-data-science-pack",
                    "version": "0.1.7",
                    "namespace": "data-science",
                },
                "nebi-pack": {
                    "chart": "nebari-nebi-pack",
                    "version": "0.1.0",
                    "namespace": "nebi",
                },
            }
        }
    )
    assert specs is not None
    write_pack_applications(gitops, specs)
    assert [s.name for s in specs] == ["nebi-pack", "data-science-pack"]
    assert (gitops / "apps" / "nebi-pack.yaml").is_file()
    assert (gitops / "apps" / "data-science-pack.yaml").is_file()
    nebi_doc = yaml.safe_load((gitops / "apps" / "nebi-pack.yaml").read_text(encoding="utf-8"))
    assert nebi_doc["spec"]["source"]["targetRevision"] == "0.1.0"


@flag_states("pyforge.steward.nkp_packs")
def test_apply_nkp_packs_flag_off_skips(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if flag_provider["pyforge.steward.nkp_packs"]:
        pytest.skip("only meaningful when flag is off")
    monkeypatch.setattr("pyforge.core.flags.read_boolean", lambda _key, default=False, **_kw: False)
    document = yaml.safe_load(_pack_config(tmp_path).read_text(encoding="utf-8"))
    calls: list[list[str]] = []

    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        calls.append(argv)
        return _Proc()

    outcome = apply_nkp_packs(
        repo_root=tmp_path,
        document=document,
        pack_deps=PackDeps(gitops_root=tmp_path / "gitops", runner=runner),
    )
    assert outcome is None
    assert calls == []


@flag_states("pyforge.steward.nkp_packs")
def test_run_nic_up_with_packs_writes_apps_labels_and_waits(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not flag_provider["pyforge.steward.nkp_packs"]:
        pytest.skip("requires pack kill switch on")
    config = _pack_config(tmp_path)
    gitops = tmp_path / "gitops"
    gitops.mkdir()
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=gitops, check=True)  # noqa: S603
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=gitops, check=True)  # noqa: S603
    subprocess.run(["git", "config", "user.name", "test"], cwd=gitops, check=True)  # noqa: S603
    calls: list[list[str]] = []

    def runner(argv: list[str], cwd: Path, env: dict[str, str]) -> _Proc:
        calls.append(list(argv))
        if argv[:2] == ["git", "add"]:
            return _Proc()
        if argv[:2] == ["git", "status"]:
            return _Proc(stdout="M apps/nebi-pack.yaml\n")
        if argv[:2] == ["git", "commit"]:
            return _Proc()
        if argv[:2] == ["kubectl", "label"]:
            return _Proc()
        if argv[:2] == ["kubectl", "wait"]:
            return _Proc()
        if argv[:2] == ["helm", "pull"]:
            return _Proc(stderr="Pulled: oci://quay.io/nebari/charts/x:0.1.0\nDigest: sha256:deadbeef\n")
        if len(argv) >= 2 and argv[1] == "deploy":
            return _Proc()
        return _Proc()

    monkeypatch.setattr(
        "pyforge.steward.deploy_nic_packs.gitops_root_for",
        lambda _doc: (gitops, None),
    )

    deps = NicDeps(
        root=tmp_path,
        runner=runner,
        nic_executable=lambda: "/usr/bin/nic",
    )
    result = run_nic(deps, action="up", config=config)
    assert result.ok is True
    assert (gitops / "apps" / "nebi-pack.yaml").is_file()
    assert (gitops / "apps" / "data-science-pack.yaml").is_file()
    assert any(cmd[:3] == ["kubectl", "label", "namespace"] for cmd in calls)
    assert any(cmd[:2] == ["kubectl", "wait"] for cmd in calls)
    journal_path = tmp_path / PACK_JOURNAL_RELATIVE
    assert journal_path.is_file()
    record = json.loads(journal_path.read_text(encoding="utf-8").splitlines()[-1])
    assert record["packs"] == ["nebi-pack", "data-science-pack"]
    assert record["pull_manifest"]
