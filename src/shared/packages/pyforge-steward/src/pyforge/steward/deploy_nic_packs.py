"""NKP pack Applications after ``deploy nic up`` (CAP-177, Story 118.2).

Writes nebi-pack then data-science-pack into the NIC GitOps ``apps/`` tree, labels pack
namespaces, waits for Argo CD ``Healthy``, and journals OCI chart digests for Warden.
Gated by ``pyforge.steward.nkp_packs``; a config without ``packs:`` is unchanged.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .interfaces import DutyResult

NKP_PACKS_FLAG = "pyforge.steward.nkp_packs"
PACK_JOURNAL_RELATIVE = Path(".steward/nkp-pack-deploy.jsonl")
OCI_CHARTS = "quay.io/nebari/charts"
ALLOWED_PACKS: tuple[str, ...] = ("nebi-pack", "data-science-pack")
_DEFAULT_DATA_SCIENCE_VALUES: dict[str, Any] = {
    "keycloak": {"hostname": "keycloak.nebari.local"},
    "sharedStorage": {"nfsServer": {"enabled": True}},
    "nebi": {"remote": {"enabled": True}},
}


class _Completed:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


SubprocessRunner = Callable[[list[str], Path | None, dict[str, str] | None], _Completed]


@dataclass(frozen=True)
class PackSpec:
    name: str
    chart: str
    version: str
    namespace: str
    values: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class PackDeps:
    gitops_root: Path
    runner: SubprocessRunner
    kubeconfig: Path | None = None


def _deep_merge(base: dict[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def parse_packs(document: Mapping[str, Any]) -> tuple[list[PackSpec] | None, DutyResult | None]:
    raw = document.get("packs")
    if raw is None:
        return None, None
    if not isinstance(raw, dict) or not raw:
        from .cli import EXIT_USAGE

        return None, DutyResult(
            ok=False,
            summary="deploy nic packs: refused — packs: must be a non-empty mapping when present",
            details={"exit_code": EXIT_USAGE},
        )
    specs: list[PackSpec] = []
    for name in ALLOWED_PACKS:
        entry = raw.get(name)
        if entry is None:
            continue
        if not isinstance(entry, dict):
            from .cli import EXIT_USAGE

            return None, DutyResult(
                ok=False,
                summary=f"deploy nic packs: refused — packs.{name} must be a mapping",
                details={"exit_code": EXIT_USAGE},
            )
        chart = entry.get("chart")
        version = entry.get("version")
        namespace = entry.get("namespace")
        if not isinstance(chart, str) or not chart.strip():
            from .cli import EXIT_USAGE

            return None, DutyResult(
                ok=False,
                summary=f"deploy nic packs: refused — packs.{name}.chart is required",
                details={"exit_code": EXIT_USAGE},
            )
        if not isinstance(version, str) or not version.strip() or version.strip().lower() == "latest":
            from .cli import EXIT_USAGE

            return None, DutyResult(
                ok=False,
                summary=f"deploy nic packs: refused — packs.{name}.version must be a pinned semver, not latest",
                details={"exit_code": EXIT_USAGE},
            )
        if not isinstance(namespace, str) or not namespace.strip():
            from .cli import EXIT_USAGE

            return None, DutyResult(
                ok=False,
                summary=f"deploy nic packs: refused — packs.{name}.namespace is required",
                details={"exit_code": EXIT_USAGE},
            )
        values_raw = entry.get("values", {})
        if values_raw is None:
            values_raw = {}
        if not isinstance(values_raw, dict):
            from .cli import EXIT_USAGE

            return None, DutyResult(
                ok=False,
                summary=f"deploy nic packs: refused — packs.{name}.values must be a mapping",
                details={"exit_code": EXIT_USAGE},
            )
        values = dict(values_raw)
        if name == "data-science-pack":
            values = _deep_merge(_DEFAULT_DATA_SCIENCE_VALUES, values)
        specs.append(
            PackSpec(
                name=name,
                chart=chart.strip(),
                version=version.strip(),
                namespace=namespace.strip(),
                values=values,
            )
        )
    extra = [key for key in raw if key not in ALLOWED_PACKS]
    if extra:
        from .cli import EXIT_USAGE

        return None, DutyResult(
            ok=False,
            summary=f"deploy nic packs: refused — unknown pack keys {extra!r}; only {ALLOWED_PACKS} are allowed",
            details={"exit_code": EXIT_USAGE},
        )
    if not specs:
        return None, None
    ordered = {spec.name: spec for spec in specs}
    missing = [name for name in ALLOWED_PACKS if name in raw and name not in ordered]
    if missing:
        from .cli import EXIT_USAGE

        return None, DutyResult(
            ok=False,
            summary=f"deploy nic packs: refused — could not parse packs {missing!r}",
            details={"exit_code": EXIT_USAGE},
        )
    return [ordered[name] for name in ALLOWED_PACKS if name in ordered], None


def gitops_root_for(document: Mapping[str, Any]) -> tuple[Path | None, DutyResult | None]:
    project = document.get("project_name")
    if not isinstance(project, str) or not project.strip():
        from .cli import EXIT_USAGE

        return None, DutyResult(
            ok=False,
            summary="deploy nic packs: refused — config project_name is required for GitOps",
            details={"exit_code": EXIT_USAGE},
        )
    repository = document.get("repository")
    if not isinstance(repository, dict):
        from .cli import EXIT_USAGE

        return None, DutyResult(
            ok=False,
            summary="deploy nic packs: refused — config repository is required",
            details={"exit_code": EXIT_USAGE},
        )
    if "local" in repository:
        return Path.home() / ".nic" / "gitops" / project.strip(), None
    if "existing" in repository:
        return Path.home() / ".nic" / "gitops" / project.strip(), None
    from .cli import EXIT_USAGE

    return None, DutyResult(
        ok=False,
        summary="deploy nic packs: refused — repository.local or repository.existing is required",
        details={"exit_code": EXIT_USAGE},
    )


def render_application(spec: PackSpec) -> dict[str, Any]:
    source: dict[str, Any] = {
        "repoURL": f"oci://{OCI_CHARTS}/{spec.chart}",
        "targetRevision": spec.version,
        "path": ".",
    }
    if spec.values:
        source["helm"] = {"valuesObject": dict(spec.values)}
    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {
            "name": spec.name,
            "namespace": "argocd",
            "labels": {
                "app.kubernetes.io/managed-by": "pyforge-steward",
                "app.kubernetes.io/part-of": "nebari-pack-layer",
            },
            "annotations": {"argocd.argoproj.io/sync-wave": "10"},
            "finalizers": ["resources-finalizer.argocd.argoproj.io"],
        },
        "spec": {
            "project": "default",
            "source": source,
            "destination": {
                "server": "https://kubernetes.default.svc",
                "namespace": spec.namespace,
            },
            "syncPolicy": {
                "managedNamespaceMetadata": {"labels": {"nebari.dev/managed": "true"}},
                "automated": {"prune": True, "selfHeal": True, "allowEmpty": False},
                "syncOptions": ["CreateNamespace=true", "ServerSideApply=true"],
                "retry": {
                    "limit": 5,
                    "backoff": {"duration": "5s", "factor": 2, "maxDuration": "3m"},
                },
            },
        },
    }


def write_pack_applications(gitops_root: Path, specs: Sequence[PackSpec]) -> list[Path]:
    apps_dir = gitops_root / "apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for spec in specs:
        path = apps_dir / f"{spec.name}.yaml"
        payload = render_application(spec)
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        written.append(path)
    return written


def _run(deps: PackDeps, argv: list[str], *, cwd: Path | None = None) -> _Completed:
    env: dict[str, str] | None = None
    if deps.kubeconfig is not None:
        import os

        env = dict(os.environ)
        env["KUBECONFIG"] = str(deps.kubeconfig)
    return deps.runner(argv, cwd, env)


def git_commit_applications(deps: PackDeps, paths: Sequence[Path]) -> DutyResult:
    if not paths:
        return DutyResult(ok=True, summary="deploy nic packs: no Application files to commit")
    if not deps.gitops_root.is_dir():
        return DutyResult(
            ok=False,
            summary=f"deploy nic packs: refused — GitOps directory {deps.gitops_root} does not exist (run nic deploy first)",
        )
    rel_paths = [str(path.relative_to(deps.gitops_root)) for path in paths]
    add = _run(deps, ["git", "add", *rel_paths], cwd=deps.gitops_root)
    if add.returncode != 0:
        return DutyResult(
            ok=False,
            summary=f"deploy nic packs: git add failed: {(add.stderr or add.stdout).strip()}",
        )
    status = _run(deps, ["git", "status", "--porcelain"], cwd=deps.gitops_root)
    if status.returncode != 0:
        return DutyResult(ok=False, summary="deploy nic packs: git status failed")
    if not status.stdout.strip():
        return DutyResult(ok=True, summary="deploy nic packs: Applications already committed")
    commit = _run(
        deps,
        [
            "git",
            "commit",
            "-m",
            "steward: add NKP pack Argo CD Applications",
        ],
        cwd=deps.gitops_root,
    )
    if commit.returncode != 0:
        return DutyResult(
            ok=False,
            summary=f"deploy nic packs: git commit failed: {(commit.stderr or commit.stdout).strip()}",
        )
    return DutyResult(ok=True, summary="deploy nic packs: committed Application manifests to GitOps")


def label_pack_namespaces(deps: PackDeps, specs: Sequence[PackSpec]) -> DutyResult:
    for spec in specs:
        proc = _run(
            deps,
            [
                "kubectl",
                "label",
                "namespace",
                spec.namespace,
                "nebari.dev/managed=true",
                "--overwrite",
            ],
        )
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout).strip().splitlines()
            hint = tail[-1] if tail else f"exit {proc.returncode}"
            return DutyResult(
                ok=False,
                summary=f"deploy nic packs: kubectl label namespace {spec.namespace!r} failed: {hint}",
            )
    return DutyResult(ok=True, summary="deploy nic packs: pack namespaces labelled")


def wait_applications_healthy(deps: PackDeps, specs: Sequence[PackSpec], *, timeout_s: int = 1800) -> DutyResult:
    for spec in specs:
        proc = _run(
            deps,
            [
                "kubectl",
                "wait",
                f"application/{spec.name}",
                "-n",
                "argocd",
                "--for=jsonpath={.status.health.status}=Healthy",
                f"--timeout={timeout_s}s",
            ],
        )
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout).strip().splitlines()
            hint = tail[-1] if tail else f"exit {proc.returncode}"
            return DutyResult(
                ok=False,
                summary=f"deploy nic packs: Application {spec.name!r} did not reach Healthy: {hint}",
            )
    return DutyResult(ok=True, summary="deploy nic packs: pack Applications Healthy")


_DIGEST_RE = re.compile(r"^Digest:\s*(sha256:[a-f0-9]+)\s*$", re.MULTILINE)


def chart_digest(deps: PackDeps, spec: PackSpec) -> str | None:
    proc = _run(
        deps,
        [
            "helm",
            "show",
            "chart",
            f"oci://{OCI_CHARTS}/{spec.chart}",
            "--version",
            spec.version,
        ],
    )
    if proc.returncode != 0:
        return None
    match = _DIGEST_RE.search(proc.stdout or "")
    return match.group(1) if match else None


def collect_pull_manifest(specs: Sequence[PackSpec], digests: Mapping[str, str | None]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in specs:
        ref = f"oci://{OCI_CHARTS}/{spec.chart}:{spec.version}"
        row = {"pack": spec.name, "chart_ref": ref}
        digest = digests.get(spec.name)
        if digest:
            row["chart_digest"] = digest
        rows.append(row)
    return rows


def append_pack_journal(root: Path, record: dict[str, Any]) -> None:
    path = root / PACK_JOURNAL_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def apply_nkp_packs(
    *,
    repo_root: Path,
    document: Mapping[str, Any],
    pack_deps: PackDeps | None = None,
    journal: Callable[[dict[str, Any]], None] | None = None,
) -> DutyResult | None:
    """Install configured packs after a successful ``nic deploy``. Returns ``None`` when skipped."""
    from pyforge.core.flags import read_boolean

    if not read_boolean(NKP_PACKS_FLAG, default=True):
        return None
    specs, failure = parse_packs(document)
    if failure is not None:
        return failure
    if not specs:
        return None
    gitops_root, failure = gitops_root_for(document)
    if failure is not None:
        return failure
    assert gitops_root is not None
    if pack_deps is None:
        pack_deps = PackDeps(gitops_root=gitops_root, runner=_default_runner)
    else:
        pack_deps = PackDeps(
            gitops_root=gitops_root,
            runner=pack_deps.runner,
            kubeconfig=pack_deps.kubeconfig,
        )
    paths = write_pack_applications(gitops_root, specs)
    commit = git_commit_applications(pack_deps, paths)
    if not commit.ok:
        return commit
    label = label_pack_namespaces(pack_deps, specs)
    if not label.ok:
        return label
    healthy = wait_applications_healthy(pack_deps, specs)
    if not healthy.ok:
        return healthy
    digests = {spec.name: chart_digest(pack_deps, spec) for spec in specs}
    record = {
        "packs": [spec.name for spec in specs],
        "gitops": str(gitops_root),
        "pull_manifest": collect_pull_manifest(specs, digests),
    }
    if journal is not None:
        journal(record)
    else:
        append_pack_journal(repo_root, record)
    summary = f"deploy nic packs: {', '.join(spec.name for spec in specs)} Healthy"
    return DutyResult(ok=True, summary=summary, details={"pack_journal": record})


def _default_runner(argv: list[str], cwd: Path | None, env: dict[str, str] | None) -> _Completed:
    proc = subprocess.run(  # noqa: S603
        argv,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return _Completed(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
