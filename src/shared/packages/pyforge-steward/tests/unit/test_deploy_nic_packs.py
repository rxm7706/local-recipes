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
    PACK_PROJECT,
    ROOT_APPLICATION,
    PackDeps,
    PackSpec,
    apply_nkp_packs,
    chart_digest,
    collect_pull_manifest,
    git_commit_applications,
    gitops_root_for,
    label_pack_namespaces,
    parse_packs,
    refresh_root_application,
    render_application,
    wait_applications_exist,
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


def _app_json(
    health: str,
    phase: str | None = None,
    sync: str = "OutOfSync",
    conditions: list | None = None,
    source: dict | None = None,
    name: str | None = None,
) -> str:
    """An Argo CD Application status as ``kubectl get -o json`` prints it.

    ``source`` is what the last operation applied (``syncResult.source``); when omitted it is the
    source ``render_application`` gives the pack called ``name`` (the test specs below), so a
    ``Succeeded`` state counts as current.
    """
    status: dict[str, object] = {"health": {"status": health}, "sync": {"status": sync}}
    if phase is not None:
        if source is None and name is not None:
            source = render_application(_SPECS[name])["spec"]["source"]
        status["operationState"] = {"phase": phase, "message": f"op {phase}", "syncResult": {"source": source or {}}}
    if conditions:
        status["conditions"] = conditions
    return json.dumps({"status": status})


_SPECS: dict[str, PackSpec] = {
    "nebi-pack": PackSpec(name="nebi-pack", chart="c", version="1.0.0", namespace="nebi"),
    "data-science-pack": PackSpec(name="data-science-pack", chart="c", version="1.0.0", namespace="data-science"),
}


def _spec_source_for(argv: list[str], document: dict) -> dict:
    """The rendered source of the pack ``kubectl get application/<name>`` asks for."""
    specs, _ = parse_packs(document)
    name = argv[2].split("/", 1)[1]
    return render_application(next(s for s in specs or [] if s.name == name))["spec"]["source"]


def test_wait_applications_healthy_surfaces_timeout() -> None:
    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["kubectl", "get"]:
            return _Proc(stdout=_app_json("Progressing", "Running", name="nebi-pack"))
        return _Proc()

    result = wait_applications_healthy(
        PackDeps(gitops_root=Path("/tmp"), runner=runner),
        [_SPECS["nebi-pack"]],
        timeout_s=20,
        poll_s=10,
        sleep=lambda _s: None,
    )
    assert result.ok is False
    assert "did not reach Healthy within 20s" in result.summary
    assert "health=Progressing" in result.summary and "phase=Running" in result.summary


def test_wait_applications_healthy_waits_for_the_sync_that_applied_the_rendered_values() -> None:
    # Attended run 2026-10-31, re-run on a converged cluster: the previous sync still reads
    # Succeeded + Healthy while Argo CD has not picked up the new Helm values; ``up`` must not
    # return until a sync of the source this run rendered has succeeded.
    spec = PackSpec(
        name="data-science-pack",
        chart="c",
        version="1.0.0",
        namespace="data-science",
        values={"keycloak": {"backchannelURL": "http://kc.keycloak.svc:8080"}},
    )
    stale = render_application(_SPECS["data-science-pack"])["spec"]["source"]
    states = iter(
        [
            _app_json("Healthy", "Succeeded", source=stale),
            _app_json("Progressing", "Running", source=stale),
            _app_json("Healthy", "Succeeded", source=render_application(spec)["spec"]["source"]),
        ]
    )

    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["kubectl", "get"]:
            return _Proc(stdout=next(states))
        return _Proc()

    slept: list[float] = []
    result = wait_applications_healthy(
        PackDeps(gitops_root=Path("/tmp"), runner=runner), [spec], timeout_s=60, poll_s=10, sleep=slept.append
    )
    assert result.ok is True
    assert slept == [10, 10]


def test_wait_applications_healthy_ignores_the_transient_healthy_before_the_first_sync() -> None:
    # Attended run 2026-10-31: a just-created Application reads Healthy with no operation yet;
    # ``up`` must not take that as the pack being up (Story 118.5).
    reads: list[str] = []
    states = iter(
        [
            _app_json("Healthy"),
            _app_json("Missing", "Running", name="data-science-pack"),
            _app_json("Healthy", "Succeeded", name="data-science-pack"),
        ]
    )

    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["kubectl", "get"]:
            reads.append(argv[2])
            return _Proc(stdout=next(states))
        return _Proc()

    spec = _SPECS["data-science-pack"]
    slept: list[float] = []
    result = wait_applications_healthy(
        PackDeps(gitops_root=Path("/tmp"), runner=runner), [spec], timeout_s=60, poll_s=10, sleep=slept.append
    )
    assert result.ok is True
    assert reads == ["application/data-science-pack"] * 3
    assert slept == [10, 10]


def test_wait_applications_healthy_leaves_a_sync_error_to_argocd_retry() -> None:
    # Attended run 2026-10-31: a terminated sync leaves ``SyncError`` on the Application until the
    # next successful sync; the next auto-sync clears it, so the poll goes on.
    sync_error = [{"type": "SyncError", "message": "Failed last sync attempt: Operation terminated"}]
    states = iter(
        [
            _app_json("Progressing", "Failed", conditions=sync_error, name="data-science-pack"),
            _app_json("Healthy", "Succeeded", name="data-science-pack"),
        ]
    )

    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["kubectl", "get"]:
            return _Proc(stdout=next(states))
        return _Proc()

    spec = _SPECS["data-science-pack"]
    result = wait_applications_healthy(
        PackDeps(gitops_root=Path("/tmp"), runner=runner), [spec], timeout_s=60, poll_s=10, sleep=lambda _s: None
    )
    assert result.ok is True


def test_wait_applications_healthy_fails_fast_on_an_argocd_error_condition() -> None:
    conditions = [
        {
            "type": "InvalidSpecError",
            "message": "application repo oci://quay.io/nebari/charts/nebari-nebi-pack is not permitted in project 'foundational'",
        }
    ]

    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["kubectl", "get"]:
            return _Proc(stdout=_app_json("Unknown", conditions=conditions))
        return _Proc()

    result = wait_applications_healthy(
        PackDeps(gitops_root=Path("/tmp"), runner=runner),
        [_SPECS["nebi-pack"]],
        timeout_s=1800,
        poll_s=10,
        sleep=lambda _s: None,
    )
    assert result.ok is False
    assert "refused by Argo CD" in result.summary
    assert "not permitted in project 'foundational'" in result.summary


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


def test_wait_applications_exist_polls_until_argocd_creates_the_application() -> None:
    # Story 118.5: ``kubectl wait`` on an Application Argo CD has not created yet fails at once
    # with NotFound, so the pack step polls for existence first.
    gets: list[list[str]] = []
    slept: list[float] = []

    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["kubectl", "get"]:
            gets.append(argv)
            if len(gets) < 3:
                return _Proc(
                    returncode=1, stderr='Error from server (NotFound): applications.argoproj.io "nebi-pack" not found'
                )
            return _Proc(stdout="application.argoproj.io/nebi-pack\n")
        return _Proc()

    spec = PackSpec(name="nebi-pack", chart="c", version="1.0.0", namespace="nebi")
    result = wait_applications_exist(
        PackDeps(gitops_root=Path("/tmp"), runner=runner), [spec], timeout_s=30, poll_s=5, sleep=slept.append
    )
    assert result.ok is True
    assert len(gets) == 3
    assert gets[0][:3] == ["kubectl", "get", "application/nebi-pack"]
    assert slept == [5, 5]


def test_wait_applications_exist_reports_a_missing_application() -> None:
    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        if argv[:2] == ["kubectl", "get"]:
            return _Proc(returncode=1, stderr="NotFound")
        return _Proc()

    spec = PackSpec(name="nebi-pack", chart="c", version="1.0.0", namespace="nebi")
    result = wait_applications_exist(
        PackDeps(gitops_root=Path("/tmp"), runner=runner), [spec], timeout_s=10, poll_s=5, sleep=lambda _s: None
    )
    assert result.ok is False
    assert "did not appear" in result.summary
    assert ROOT_APPLICATION in result.summary


def test_refresh_root_application_annotates_nebari_root() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str], _cwd: Path | None, _env: dict[str, str] | None) -> _Proc:
        calls.append(argv)
        return _Proc()

    result = refresh_root_application(PackDeps(gitops_root=Path("/tmp"), runner=runner))
    assert result.ok is True
    assert calls == [
        [
            "kubectl",
            "annotate",
            "application",
            "nebari-root",
            "-n",
            "argocd",
            "argocd.argoproj.io/refresh=normal",
            "--overwrite",
        ]
    ]


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
        if argv[:2] == ["kubectl", "get"] and argv[-1] == "json":
            return _Proc(stdout=_app_json("Healthy", "Succeeded", source=_spec_source_for(argv, document)))
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
    # NIC's ``foundational`` AppProject admits only its own namespaces and chart repos; packs
    # go through the ``nebari-apps`` project NIC creates for them (attended run 2026-10-31).
    assert PACK_PROJECT == "nebari-apps"
    assert app["spec"]["project"] == PACK_PROJECT
    assert "helm" not in app["spec"]["source"]


def test_render_application_keeps_null_values_as_a_helm_values_string() -> None:
    # A ``key: null`` deletes a chart default (Helm); through ``valuesObject`` the apiserver drops
    # the null before Argo CD renders, so the values travel as a YAML string (Story 118.5).
    spec = PackSpec(
        name="data-science-pack",
        chart="nebari-data-science-pack",
        version="0.1.7",
        namespace="data-science",
        values={"nebariapp": {"landingPage": {"iconLight": None, "iconDark": None}}},
    )
    helm = render_application(spec)["spec"]["source"]["helm"]
    assert "valuesObject" not in helm
    rendered = yaml.safe_load(helm["values"])
    assert rendered == {"nebariapp": {"landingPage": {"iconLight": None, "iconDark": None}}}
    assert "iconDark: null" in helm["values"]


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
    document = yaml.safe_load(config.read_text(encoding="utf-8"))
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
        if argv[:2] == ["kubectl", "get"] and argv[-1] == "json":
            return _Proc(stdout=_app_json("Healthy", "Succeeded", source=_spec_source_for(argv, document)))
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
    assert not any(cmd[:2] == ["kubectl", "wait"] for cmd in calls)
    kubectl_verbs = [cmd[1] for cmd in calls if cmd[0] == "kubectl"]
    assert kubectl_verbs.index("annotate") < kubectl_verbs.index("get") < kubectl_verbs.index("label")
    health_reads = [cmd for cmd in calls if cmd[:2] == ["kubectl", "get"] and cmd[-1] == "json"]
    assert [cmd[2] for cmd in health_reads] == ["application/nebi-pack", "application/data-science-pack"]
    journal_path = tmp_path / PACK_JOURNAL_RELATIVE
    assert journal_path.is_file()
    record = json.loads(journal_path.read_text(encoding="utf-8").splitlines()[-1])
    assert record["packs"] == ["nebi-pack", "data-science-pack"]
    assert record["pull_manifest"]
