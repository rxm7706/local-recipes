"""Story 12.1 -- chart invariants (AD-11/AD-12, CAP-6).

The core chart (`deploy/charts/platform/`) must stay vanilla Kubernetes and
the OCP overlay (`deploy/overlays/ocp/`) must stay a thin Route; the
platform-image pods (web, worker, migrate) must carry the OCP
`restricted-v2` contract with no fixed UID anywhere; and the namespace
inventory must be exactly PostgreSQL + Redis + the platform image (AD-1).
This module makes those invariants tests over parsed `helm template`
output rather than conventions.

Story 9.6's discipline applies: every real proof's assertion logic lives
in a shared helper, and each helper has a "guard removed" companion that
feeds it a synthetic violating input (pure dicts -- no helm, no yaml) and
requires it to raise. The companions are deliberately UNGATED so the
discipline runs even in the pip-only CI `test` job, which has neither helm
nor PyYAML -- the real proofs gate per-test on helm (skip reason names the
capability, the 11.4 convention) and import yaml only after that gate via
`pytest.importorskip`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_CORE_CHART = _PLATFORM_DIR / "deploy" / "charts" / "platform"
_OVERLAY_CHART = _PLATFORM_DIR / "deploy" / "overlays" / "ocp" / "chart"
_CORE_OVERRIDES = _PLATFORM_DIR / "deploy" / "overlays" / "ocp" / "core-overrides.yaml"

# The plain kinds AD-11 allows the core chart to render -- anything else
# (Route, DeploymentConfig, ImageStream, BuildConfig, ...) is a finding.
_VANILLA_KINDS = frozenset(
    {"Deployment", "StatefulSet", "Service", "Ingress", "Job", "ServiceAccount"},
)
_WORKLOAD_KINDS = frozenset({"Deployment", "StatefulSet", "Job"})
# The three pods that run the Story 10.3 platform image and must therefore
# carry the restricted-v2 contract. "migrate" doubles as proof the hook
# Job renders (`helm template` emits hooks).
_PLATFORM_COMPONENTS = frozenset({"web", "worker", "migrate"})

requires_helm = pytest.mark.skipif(
    shutil.which("helm") is None,
    reason=(
        "helm not on PATH (AD-16: provided by the platform-dev pixi env) -- "
        "chart render/lint tests need it"
    ),
)


# ---------------------------------------------------------------------------
# Render plumbing (helm-gated tests only)
# ---------------------------------------------------------------------------


def _import_yaml() -> Any:
    """Import PyYAML AFTER the helm gate, never at module level: the
    pip-only CI `test` job installs neither helm nor PyYAML, and this
    module must still collect (and run the guard-removed companions) there.
    """
    return pytest.importorskip(
        "yaml",
        reason=(
            "PyYAML not installed (pip-only CI lane) -- chart render tests "
            "parse `helm template` output with it"
        ),
    )


def _helm(*args: str) -> str:
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        ["helm", *args],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        msg = (
            f"helm {' '.join(args)} failed (exit {result.returncode}):\n{result.stderr}"
        )
        raise AssertionError(msg)
    return result.stdout


def _render(chart: Path, *extra_args: str) -> list[dict[str, Any]]:
    yaml = _import_yaml()
    stdout = _helm("template", "test-release", str(chart), *extra_args)
    return [doc for doc in yaml.safe_load_all(stdout) if doc]


def _default_image_repositories() -> frozenset[str]:
    """The three expected repository names, DERIVED from the core chart's
    own default values rather than re-declared here.
    """
    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    return frozenset(
        {
            values["image"]["repository"],
            values["postgres"]["image"]["repository"],
            values["redis"]["image"]["repository"],
        },
    )


# ---------------------------------------------------------------------------
# Shared invariant helpers -- pure functions over parsed documents, used by
# BOTH the real proofs and the guard-removed companions
# ---------------------------------------------------------------------------


def _find_key_paths(node: object, key: str, path: str = "") -> list[str]:
    """Every dotted path at which `key` appears anywhere under `node`."""
    found: list[str] = []
    if isinstance(node, dict):
        for child_key, child in node.items():
            child_path = f"{path}.{child_key}" if path else str(child_key)
            if child_key == key:
                found.append(child_path)
            found.extend(_find_key_paths(child, key, child_path))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            found.extend(_find_key_paths(child, key, f"{path}[{index}]"))
    return found


def _assert_only_vanilla_kubernetes_documents(docs: list[dict[str, Any]]) -> None:
    """AD-11: only plain kinds, and no OpenShift apiVersion anywhere."""
    assert docs, "empty render -- this vanilla-kinds check would pass vacuously"
    offending = [
        (doc.get("kind"), doc.get("apiVersion"))
        for doc in docs
        if doc.get("kind") not in _VANILLA_KINDS
        or "openshift.io" in str(doc.get("apiVersion", ""))
    ]
    assert not offending, (
        f"non-vanilla documents in the core render (kind, apiVersion): {offending}"
    )


def _assert_only_route_documents(docs: list[dict[str, Any]]) -> None:
    """The overlay is THIN: every document is a route.openshift.io/v1 Route."""
    assert docs, "empty render -- this Route-only check would pass vacuously"
    offending = [
        (doc.get("kind"), doc.get("apiVersion"))
        for doc in docs
        if doc.get("kind") != "Route"
        or doc.get("apiVersion") != "route.openshift.io/v1"
    ]
    assert not offending, (
        f"non-Route documents in the overlay render (kind, apiVersion): {offending}"
    )


def _assert_restricted_v2_pod_spec(pod_spec: dict[str, Any], where: str) -> None:
    """The restricted-v2 contract for a platform-image pod spec: pod-level
    runAsNonRoot + RuntimeDefault seccomp; per-container no privilege
    escalation + drop ALL; and NO runAsUser key anywhere in the pod spec
    (OCP assigns an arbitrary UID; the image's own `USER 1001:0` covers
    vanilla K8s).
    """
    pod_context = pod_spec.get("securityContext") or {}
    assert pod_context.get("runAsNonRoot") is True, (
        f"{where}: pod securityContext.runAsNonRoot is not true ({pod_context!r})"
    )
    seccomp_type = (pod_context.get("seccompProfile") or {}).get("type")
    assert seccomp_type == "RuntimeDefault", (
        f"{where}: pod seccompProfile.type is {seccomp_type!r}, not RuntimeDefault"
    )

    containers = list(pod_spec.get("containers") or []) + list(
        pod_spec.get("initContainers") or [],
    )
    assert containers, f"{where}: pod spec has no containers"
    for container in containers:
        name = container.get("name")
        container_context = container.get("securityContext") or {}
        assert container_context.get("allowPrivilegeEscalation") is False, (
            f"{where}/{name}: allowPrivilegeEscalation is not false "
            f"({container_context!r})"
        )
        dropped = (container_context.get("capabilities") or {}).get("drop")
        assert dropped == ["ALL"], (
            f"{where}/{name}: capabilities.drop is {dropped!r}, not ['ALL']"
        )

    fixed_uid_paths = _find_key_paths(pod_spec, "runAsUser")
    assert not fixed_uid_paths, (
        f"{where}: runAsUser fixed inside a restricted-v2 pod spec at {fixed_uid_paths}"
    )


def _assert_image_inventory_is_exactly(
    images: set[str],
    expected_repositories: frozenset[str],
) -> None:
    """AD-1: the rendered image set reduces to exactly the expected
    repositories -- nothing extra, nothing missing.
    """
    assert images, "no images rendered -- this inventory check would pass vacuously"
    unmatched = sorted(
        image
        for image in images
        if not any(repository in image for repository in expected_repositories)
    )
    assert not unmatched, (
        f"images beyond the AD-1 inventory {sorted(expected_repositories)}: {unmatched}"
    )
    matched = {
        repository
        for image in images
        for repository in expected_repositories
        if repository in image
    }
    missing = sorted(expected_repositories - matched)
    assert not missing, (
        f"expected images missing from the render: {missing} "
        f"(rendered images: {sorted(images)})"
    )


def _pod_specs_by_component(
    docs: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Workload pod specs keyed by their app.kubernetes.io/component pod
    label (web/worker/migrate/postgres/redis -- unique per workload in
    this chart).
    """
    by_component: dict[str, dict[str, Any]] = {}
    for doc in docs:
        if doc.get("kind") not in _WORKLOAD_KINDS:
            continue
        template = doc["spec"]["template"]
        component = template["metadata"]["labels"]["app.kubernetes.io/component"]
        by_component[component] = template["spec"]
    return by_component


def _collect_workload_images(docs: list[dict[str, Any]]) -> set[str]:
    images: set[str] = set()
    for doc in docs:
        if doc.get("kind") not in _WORKLOAD_KINDS:
            continue
        pod_spec = doc["spec"]["template"]["spec"]
        containers = list(pod_spec.get("containers") or []) + list(
            pod_spec.get("initContainers") or [],
        )
        for container in containers:
            images.add(container["image"])
    return images


# ---------------------------------------------------------------------------
# Real proofs (helm-gated)
# ---------------------------------------------------------------------------


@requires_helm
def test_helm_lint_passes_for_both_charts():
    """AC: `helm lint` passes for the core and overlay charts under the
    platform-dev env's Helm 4.x (verifies AD-16 CLI compat live).
    """
    output = _helm("lint", str(_CORE_CHART), str(_OVERLAY_CHART))
    assert "0 chart(s) failed" in output, output


@requires_helm
def test_core_chart_default_render_is_vanilla_kubernetes_only():
    """AC: the default core render contains zero OCP-specific kinds or
    apiVersions -- only the plain-Kubernetes allowlist.
    """
    docs = _render(_CORE_CHART)

    _assert_only_vanilla_kubernetes_documents(docs)


@requires_helm
def test_overlay_chart_renders_route_documents_only():
    """AC: the Route renders only from the overlay chart, and the overlay
    renders nothing BUT Routes.
    """
    docs = _render(_OVERLAY_CHART)

    _assert_only_route_documents(docs)


@requires_helm
def test_platform_image_pod_specs_satisfy_restricted_v2():
    """AC: web/worker/migrate pod specs each satisfy restricted-v2
    (runAsNonRoot, RuntimeDefault seccomp, no privilege escalation, drop
    ALL, no fixed UID anywhere) -- including the migrate Job, which must be
    FOUND in the render despite being a helm hook.
    """
    docs = _render(_CORE_CHART)
    by_component = _pod_specs_by_component(docs)

    missing = sorted(_PLATFORM_COMPONENTS - by_component.keys())
    assert not missing, (
        f"platform workloads missing from the render (the migrate hook Job "
        f"must render too -- `helm template` emits hooks): {missing}"
    )
    for component in sorted(_PLATFORM_COMPONENTS):
        _assert_restricted_v2_pod_spec(by_component[component], where=component)


@requires_helm
def test_namespace_inventory_is_exactly_postgres_redis_and_the_platform_image():
    """AC (AD-1): across ALL rendered workload pod specs, the image set
    reduces to exactly three -- postgres, redis, and the platform image.
    """
    docs = _render(_CORE_CHART)
    images = _collect_workload_images(docs)

    _assert_image_inventory_is_exactly(images, _default_image_repositories())


@requires_helm
def test_ocp_overrides_drop_the_ingress_and_the_data_service_uids():
    """AC: rendered with the overlay's core-overrides.yaml, the core chart
    emits no Ingress and no runAsUser anywhere (the SCC assigns UIDs) --
    while the postgres/redis workloads themselves still render (the
    override removes their UID pins, not the services).
    """
    docs = _render(_CORE_CHART, "-f", str(_CORE_OVERRIDES))

    ingresses = [doc for doc in docs if doc.get("kind") == "Ingress"]
    assert not ingresses, (
        f"the OCP overrides must disable the Ingress, but the render still "
        f"contains: {[doc['metadata']['name'] for doc in ingresses]}"
    )
    by_component = _pod_specs_by_component(docs)
    for component in ("postgres", "redis"):
        assert component in by_component, (
            f"{component} workload missing from the OCP-overridden render -- "
            f"the UID check below would pass vacuously"
        )
    fixed_uid_paths = _find_key_paths(docs, "runAsUser")
    assert not fixed_uid_paths, (
        f"runAsUser survives the OCP overrides at {fixed_uid_paths} -- "
        f"restricted-v2 forbids fixing a UID"
    )


# ---------------------------------------------------------------------------
# Guard-removed companions (9.6 discipline) -- UNGATED, pure dicts, no
# helm/yaml, so they run in the pip-only CI lane too
# ---------------------------------------------------------------------------


def test_restricted_v2_check_fails_when_a_pod_spec_fixes_a_uid():
    """A pod spec that is restricted-v2-clean EXCEPT for a fixed UID, fed
    to the same helper the real test uses, must raise.
    """
    violating_pod_spec = {
        "securityContext": {
            "runAsNonRoot": True,
            "seccompProfile": {"type": "RuntimeDefault"},
            "runAsUser": 1001,
        },
        "containers": [
            {
                "name": "web",
                "image": "platform:latest",
                "securityContext": {
                    "allowPrivilegeEscalation": False,
                    "capabilities": {"drop": ["ALL"]},
                },
            },
        ],
    }

    with pytest.raises(AssertionError):
        _assert_restricted_v2_pod_spec(violating_pod_spec, where="synthetic-web")


def test_vanilla_kinds_check_fails_when_a_route_is_present():
    """A document set containing a Route, fed to the same vanilla-kinds
    helper the real core-render test uses, must raise.
    """
    contaminated_docs = [
        {"kind": "Deployment", "apiVersion": "apps/v1"},
        {"kind": "Route", "apiVersion": "route.openshift.io/v1"},
    ]

    with pytest.raises(AssertionError):
        _assert_only_vanilla_kubernetes_documents(contaminated_docs)


def test_route_only_check_fails_when_a_non_route_document_is_present():
    """The overlay's thinness check must reject a render that smuggles in
    anything besides Routes.
    """
    contaminated_docs = [
        {"kind": "Route", "apiVersion": "route.openshift.io/v1"},
        {"kind": "Deployment", "apiVersion": "apps/v1"},
    ]

    with pytest.raises(AssertionError):
        _assert_only_route_documents(contaminated_docs)


def test_image_inventory_check_fails_on_a_fourth_image():
    """An image set with anything beyond the AD-1 trio, fed to the same
    inventory helper the real test uses, must raise.
    """
    images = {"platform:latest", "postgres:17", "redis:7", "vault:1.15"}

    with pytest.raises(AssertionError):
        _assert_image_inventory_is_exactly(
            images,
            frozenset({"platform", "postgres", "redis"}),
        )
