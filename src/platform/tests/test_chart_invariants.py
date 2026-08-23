"""Story 12.1 -- chart invariants (AD-11/AD-12, CAP-6).

The core chart (`deploy/charts/platform/`) must stay vanilla Kubernetes and
the OCP overlay (`deploy/overlays/ocp/`) must stay a thin Route; the
platform-image pods (web, worker, migrate) must carry the OCP
`restricted-v2` contract with no fixed UID anywhere; and the namespace
inventory must be exactly PostgreSQL + Redis + the platform image + the
DB-GPT sidecar (AD-1, Story 12.5). This module makes those invariants
tests over parsed `helm template` output rather than conventions.

Story 9.6's discipline applies: every real proof's assertion logic lives
in a shared helper, and each of the eight assertion-bearing helpers has at
least one "guard removed" companion that feeds it a synthetic violating
input (pure dicts -- no helm, no yaml) and requires it to raise. The
companions are deliberately UNGATED so the discipline runs even in the
pip-only CI `test` job, which has neither helm nor PyYAML -- the real
proofs gate per-test on helm (skip reason names the capability, the 11.4
convention) and import yaml only after that gate via `pytest.importorskip`.
The helm gate accepts ANY `helm` on PATH; the canonical invocation is via
the `platform-dev` pixi env (AD-16), which is what the recorded
verification used.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any
from typing import cast

import pytest

_PLATFORM_DIR = Path(__file__).resolve().parents[1]
_CORE_CHART = _PLATFORM_DIR / "deploy" / "charts" / "platform"
_OVERLAY_CHART = _PLATFORM_DIR / "deploy" / "overlays" / "ocp" / "chart"
_CORE_OVERRIDES = _PLATFORM_DIR / "deploy" / "overlays" / "ocp" / "core-overrides.yaml"

# The plain kinds AD-11 allows the core chart to render -- anything else
# (Route, DeploymentConfig, ImageStream, BuildConfig, ...) is a finding.
_VANILLA_KINDS = frozenset(
    {
        "Deployment",
        "StatefulSet",
        "Service",
        "Ingress",
        "Job",
        "ServiceAccount",
        "PersistentVolumeClaim",
        "NetworkPolicy",
    },
)
_WORKLOAD_KINDS = frozenset({"Deployment", "StatefulSet", "Job"})
# The three pods that run the Story 10.3 platform image and must therefore
# carry the restricted-v2 contract. "migrate" doubles as proof the hook
# Job renders (`helm template` emits hooks).
_PLATFORM_COMPONENTS = frozenset({"web", "worker", "migrate"})
# Story 12.5: the DB-GPT sidecar carries the same restricted-v2 contract.
_SIDECAR_COMPONENT = "dbgpt"

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


def _render(
    chart: Path,
    *extra_args: str,
    release: str = "test-release",
) -> list[dict[str, Any]]:
    yaml = _import_yaml()
    stdout = _helm("template", release, str(chart), *extra_args)
    return [doc for doc in yaml.safe_load_all(stdout) if doc]


def _strip_image_tag(image: str) -> str:
    """The image reference without its trailing tag: split on the LAST ":"
    only when what follows contains no "/" (a ":" inside a
    registry-host:port segment is always followed by a "/" path).
    Digest/port-safe enough for these fixtures -- an "@sha256:..." digest
    reference would need real reference parsing, and none appears in this
    chart's values.
    """
    head, sep, tail = image.rpartition(":")
    if sep and "/" not in tail:
        return head
    return image


def _default_image_references() -> frozenset[str]:
    """The four expected tag-stripped image references, DERIVED from the
    core chart's own default values (registry + repository composed by the
    same rule as the chart's imageRef helper) rather than re-declared here.
    """
    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    references: set[str] = set()
    for image in (
        values["image"],
        values["postgres"]["image"],
        values["redis"]["image"],
        values["sidecar"]["image"],
    ):
        registry = image.get("registry")
        repository = image["repository"]
        references.add(f"{registry}/{repository}" if registry else repository)
    return frozenset(references)


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
    runAsNonRoot + RuntimeDefault seccomp; per-container (initContainers
    included) no privilege escalation, drop ALL with nothing added, no
    runAsNonRoot/seccomp override weakening the pod level; and NO
    runAsUser key anywhere in the pod spec (OCP assigns an arbitrary UID;
    the image's own `USER 1001:0` covers vanilla K8s).
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
        assert container_context.get("runAsNonRoot") is not False, (
            f"{where}/{name}: container-level runAsNonRoot: false overrides "
            f"the pod-level true"
        )
        container_seccomp = container_context.get("seccompProfile")
        if container_seccomp is not None:
            container_seccomp_type = container_seccomp.get("type")
            assert container_seccomp_type == "RuntimeDefault", (
                f"{where}/{name}: container-level seccompProfile.type is "
                f"{container_seccomp_type!r}, not RuntimeDefault -- it "
                f"overrides the pod-level profile"
            )
        capabilities = container_context.get("capabilities") or {}
        dropped = capabilities.get("drop")
        assert dropped == ["ALL"], (
            f"{where}/{name}: capabilities.drop is {dropped!r}, not ['ALL']"
        )
        added = capabilities.get("add")
        assert not added, (
            f"{where}/{name}: capabilities.add is {added!r} -- restricted-v2 "
            f"allows no added capabilities"
        )

    fixed_uid_paths = _find_key_paths(pod_spec, "runAsUser")
    assert not fixed_uid_paths, (
        f"{where}: runAsUser fixed inside a restricted-v2 pod spec at {fixed_uid_paths}"
    )


def _assert_image_inventory_is_exactly(
    images: set[str],
    expected_references: frozenset[str],
) -> None:
    """AD-1: the rendered images, tag-stripped, reduce to EXACTLY the
    expected references -- nothing extra, nothing missing. Exact matching,
    never substring: `platform-dbgpt-sidecar:1.0` must count as a fourth
    image, not vanish inside `platform`.
    """
    assert images, "no images rendered -- this inventory check would pass vacuously"
    rendered_references = {_strip_image_tag(image) for image in images}
    unexpected = sorted(rendered_references - expected_references)
    assert not unexpected, (
        f"images beyond the AD-1 inventory {sorted(expected_references)}: "
        f"{unexpected} (rendered images: {sorted(images)})"
    )
    missing = sorted(expected_references - rendered_references)
    assert not missing, (
        f"expected images missing from the render: {missing} "
        f"(rendered images: {sorted(images)})"
    )


def _assert_no_ingress_documents(docs: list[dict[str, Any]]) -> None:
    """The OCP overrides must disable the Ingress entirely."""
    assert docs, "empty render -- this Ingress-absence check would pass vacuously"
    ingresses = [
        doc["metadata"]["name"] for doc in docs if doc.get("kind") == "Ingress"
    ]
    assert not ingresses, (
        f"the OCP overrides must disable the Ingress, but the render still "
        f"contains: {ingresses}"
    )


def _assert_no_fixed_uid_keys(docs: list[dict[str, Any]]) -> None:
    """No runAsUser or fsGroup key anywhere in the documents: restricted-v2
    forbids fixing a UID or supplemental group, so the OCP-overridden
    render must drop BOTH keys, not just runAsUser.
    """
    assert docs, "empty render -- this fixed-UID check would pass vacuously"
    for key in ("runAsUser", "fsGroup"):
        fixed_paths = _find_key_paths(docs, key)
        assert not fixed_paths, (
            f"{key} survives the OCP overrides at {fixed_paths} -- "
            f"restricted-v2 forbids fixing a UID/group"
        )


def _assert_route_targets_service(
    route: dict[str, Any],
    service: dict[str, Any],
) -> None:
    """The Route must point at the Service BY ITS RENDERED NAME, and the
    Route's targetPort must exist as a NAMED port on that Service (a
    numeric Route targetPort resolves against the pod's containerPort,
    not the Service port -- the named coupling is the robust one).
    """
    route_target = route["spec"]["to"]["name"]
    service_name = service["metadata"]["name"]
    assert route_target == service_name, (
        f"Route targets Service {route_target!r}, but the core render's web "
        f"Service is named {service_name!r}"
    )
    target_port = route["spec"]["port"]["targetPort"]
    port_names = [port.get("name") for port in service["spec"].get("ports") or []]
    assert target_port in port_names, (
        f"Route targetPort {target_port!r} is not a named port on Service "
        f"{service_name!r} (named ports: {port_names})"
    )


def _pod_specs_by_component(
    docs: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Workload pod specs keyed by their app.kubernetes.io/component pod
    label (web/worker/migrate/postgres/redis). Asserts the label is
    PRESENT on every workload (an evidence-bearing message, never a bare
    KeyError) and UNIQUE across workloads (a duplicate would silently
    drop a pod spec under last-wins keying).
    """
    by_component: dict[str, dict[str, Any]] = {}
    for doc in docs:
        if doc.get("kind") not in _WORKLOAD_KINDS:
            continue
        workload_name = (doc.get("metadata") or {}).get("name")
        template = doc["spec"]["template"]
        labels = (template.get("metadata") or {}).get("labels") or {}
        component = labels.get("app.kubernetes.io/component")
        assert component is not None, (
            f"{doc.get('kind')} {workload_name!r}: pod template carries no "
            f"app.kubernetes.io/component label (labels: {labels!r})"
        )
        assert component not in by_component, (
            f"{doc.get('kind')} {workload_name!r}: duplicate "
            f"app.kubernetes.io/component label {component!r} across "
            f"workloads -- last-wins keying would silently drop a pod spec"
        )
        by_component[component] = template["spec"]
    return by_component


def _collect_env_by_name(
    pod_spec: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Container env vars keyed by name (value or valueFrom)."""
    env_by_name: dict[str, dict[str, Any]] = {}
    for container in pod_spec.get("containers") or []:
        for entry in container.get("env") or []:
            env_by_name[entry["name"]] = entry
    return env_by_name


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


def _assert_redis_persistence_is_empty_dir(docs: list[dict[str, Any]]) -> None:
    """Story 12.6: Redis stays ephemeral -- Deployment volumes use emptyDir,
    never a PVC.
    """
    redis_deployments = [
        doc
        for doc in docs
        if doc.get("kind") == "Deployment"
        and (doc.get("metadata") or {}).get("labels", {}).get(
            "app.kubernetes.io/component",
        )
        == "redis"
    ]
    assert len(redis_deployments) == 1, (
        f"expected exactly one redis Deployment, got "
        f"{[doc['metadata']['name'] for doc in redis_deployments]}"
    )
    volumes = redis_deployments[0]["spec"]["template"]["spec"].get("volumes") or []
    assert volumes, "redis Deployment has no volumes -- emptyDir check vacuous"
    for volume in volumes:
        assert "emptyDir" in volume, (
            f"redis volume {volume.get('name')!r} is not emptyDir: {volume!r}"
        )
        assert "persistentVolumeClaim" not in volume, (
            f"redis volume {volume.get('name')!r} uses a PVC -- persistence "
            f"must stay ephemeral (Story 12.6)"
        )


def _assert_redis_uses_password_from_existing_secret(
    docs: list[dict[str, Any]],
    *,
    secret_name: str,
    password_key: str,
    redis_service_host: str,
) -> None:
    """Story 12.6: redis container and platform pods wire AUTH from
    existingSecret into --requirepass and REDIS_URL respectively.
    """
    by_component = _pod_specs_by_component(docs)
    assert "redis" in by_component, "redis workload missing from render"
    redis_env = _collect_env_by_name(by_component["redis"])
    redis_password = redis_env.get("REDIS_PASSWORD")
    assert redis_password is not None, "redis pod missing REDIS_PASSWORD env"
    assert redis_password.get("valueFrom", {}).get("secretKeyRef") == {
        "name": secret_name,
        "key": password_key,
    }, f"redis REDIS_PASSWORD secretKeyRef mismatch: {redis_password!r}"

    redis_container = by_component["redis"]["containers"][0]
    assert redis_container.get("command") == [
        "redis-server",
        "--requirepass",
        "$(REDIS_PASSWORD)",
    ], f"redis command missing --requirepass wiring: {redis_container.get('command')!r}"

    expected_redis_url = f"redis://:$(REDIS_PASSWORD)@{redis_service_host}:6379/0"
    for component in sorted(_PLATFORM_COMPONENTS):
        env = _collect_env_by_name(by_component[component])
        password_env = env.get("REDIS_PASSWORD")
        assert password_env is not None, f"{component} pod missing REDIS_PASSWORD env"
        assert password_env.get("valueFrom", {}).get("secretKeyRef") == {
            "name": secret_name,
            "key": password_key,
        }, f"{component} REDIS_PASSWORD secretKeyRef mismatch: {password_env!r}"
        redis_url = env.get("REDIS_URL")
        assert redis_url is not None, f"{component} pod missing REDIS_URL env"
        assert redis_url.get("value") == expected_redis_url, (
            f"{component} REDIS_URL is {redis_url.get('value')!r}, "
            f"expected AUTH-wired {expected_redis_url!r}"
        )


def _assert_redis_network_policy_restricts_platform_pods(
    docs: list[dict[str, Any]],
    *,
    redis_policy_name: str,
) -> None:
    """Story 12.6: exactly one NetworkPolicy targets redis and allows
    ingress from web/worker/migrate platform pods on 6379 only.
    """
    policies = [doc for doc in docs if doc.get("kind") == "NetworkPolicy"]
    redis_policies = [
        doc for doc in policies if doc["metadata"]["name"] == redis_policy_name
    ]
    assert len(redis_policies) == 1, (
        f"expected exactly one redis NetworkPolicy named {redis_policy_name!r}, "
        f"got {[doc['metadata']['name'] for doc in policies]}"
    )
    policy = redis_policies[0]
    selector = policy["spec"]["podSelector"]
    assert selector.get("matchLabels", {}).get("app.kubernetes.io/component") == "redis"

    ingress_rules = policy["spec"].get("ingress") or []
    assert len(ingress_rules) == 1, (
        f"redis NetworkPolicy must have exactly one ingress rule, got {ingress_rules!r}"
    )
    rule = ingress_rules[0]
    from_entries = rule.get("from") or []
    assert len(from_entries) == 1, (
        f"redis NetworkPolicy ingress.from must have one podSelector entry, "
        f"got {from_entries!r}"
    )
    pod_selector = from_entries[0].get("podSelector") or {}
    component_expr = next(
        (
            expr
            for expr in pod_selector.get("matchExpressions") or []
            if expr.get("key") == "app.kubernetes.io/component"
        ),
        None,
    )
    assert component_expr is not None, (
        f"redis NetworkPolicy missing component matchExpression: {pod_selector!r}"
    )
    assert component_expr.get("operator") == "In", component_expr
    assert set(component_expr.get("values") or []) == set(_PLATFORM_COMPONENTS), (
        f"redis NetworkPolicy component filter must match platform pods "
        f"{sorted(_PLATFORM_COMPONENTS)}, got {component_expr.get('values')!r}"
    )
    ports = rule.get("ports") or []
    assert ports == [{"protocol": "TCP", "port": 6379}], (
        f"redis NetworkPolicy must allow TCP/6379 only, got {ports!r}"
    )


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
def test_sidecar_deployment_renders_with_recreate_and_restricted_v2():
    """AC: the DB-GPT sidecar Deployment uses replicas 1, Recreate strategy,
    and satisfies restricted-v2 on its pod spec.
    """
    docs = _render(_CORE_CHART)
    sidecar_deployments = [
        doc
        for doc in docs
        if doc.get("kind") == "Deployment"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == _SIDECAR_COMPONENT
    ]
    assert len(sidecar_deployments) == 1, (
        f"expected exactly one dbgpt Deployment, got: "
        f"{[doc['metadata']['name'] for doc in sidecar_deployments]}"
    )
    sidecar = sidecar_deployments[0]["spec"]
    assert sidecar.get("replicas") == 1
    assert sidecar.get("strategy", {}).get("type") == "Recreate"
    by_component = _pod_specs_by_component(docs)
    assert _SIDECAR_COMPONENT in by_component, "dbgpt sidecar missing from render"
    _assert_restricted_v2_pod_spec(
        by_component[_SIDECAR_COMPONENT],
        where=_SIDECAR_COMPONENT,
    )


@requires_helm
def test_sidecar_sqlite_pvc_and_internal_service_render():
    """AC: a dedicated SQLite PVC and internal ClusterIP Service appear."""
    docs = _render(_CORE_CHART)
    pvcs = [doc for doc in docs if doc.get("kind") == "PersistentVolumeClaim"]
    assert len(pvcs) == 1, (
        f"expected exactly one PVC for the sidecar sqlite store, got: "
        f"{[doc['metadata']['name'] for doc in pvcs]}"
    )
    dbgpt_services = [
        doc
        for doc in docs
        if doc.get("kind") == "Service"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == _SIDECAR_COMPONENT
    ]
    assert len(dbgpt_services) == 1, (
        f"expected exactly one dbgpt Service, got: "
        f"{[doc['metadata']['name'] for doc in dbgpt_services]}"
    )
    assert dbgpt_services[0]["spec"].get("type") == "ClusterIP"


@requires_helm
def test_platform_pods_wire_dbgpt_sidecar_base_url_to_internal_service():
    """AC: web/worker pods resolve DBGPT_SIDECAR_BASE_URL to the internal
    dbgpt Service (not localhost).
    """
    docs = _render(_CORE_CHART, release="platform")
    dbgpt_service_name = next(
        doc["metadata"]["name"]
        for doc in docs
        if doc.get("kind") == "Service"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == _SIDECAR_COMPONENT
    )
    expected_url = f"http://{dbgpt_service_name}:5670"
    by_component = _pod_specs_by_component(docs)
    for component in ("web", "worker"):
        env = _collect_env_by_name(by_component[component])
        dbgpt_env = env.get("DBGPT_SIDECAR_BASE_URL")
        assert dbgpt_env is not None, (
            f"{component} pod missing DBGPT_SIDECAR_BASE_URL env"
        )
        assert dbgpt_env.get("value") == expected_url, (
            f"{component} DBGPT_SIDECAR_BASE_URL is {dbgpt_env.get('value')!r}, "
            f"expected internal Service URL {expected_url!r}"
        )
        assert "localhost" not in dbgpt_env.get("value", "")


@requires_helm
def test_redis_uses_existing_secret_password_and_wires_redis_url():
    """AC (Story 12.6): redis Deployment and platform pods consume
    REDIS_PASSWORD from existingSecret; REDIS_URL embeds it via env
    expansion.
    """
    docs = _render(_CORE_CHART, release="platform")
    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    redis_host = next(
        doc["metadata"]["name"]
        for doc in docs
        if doc.get("kind") == "Service"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == "redis"
    )
    _assert_redis_uses_password_from_existing_secret(
        docs,
        secret_name=values["existingSecret"],
        password_key=values["redis"]["passwordSecretKey"],
        redis_service_host=redis_host,
    )


@requires_helm
def test_redis_network_policy_restricts_ingress_to_platform_pods():
    """AC (Story 12.6): a NetworkPolicy limits redis ingress to web/worker/
    migrate pods on port 6379.
    """
    docs = _render(_CORE_CHART, release="platform")
    redis_policy_name = next(
        doc["metadata"]["name"]
        for doc in docs
        if doc.get("kind") == "NetworkPolicy"
        and doc["spec"]["podSelector"]
        .get("matchLabels", {})
        .get("app.kubernetes.io/component")
        == "redis"
    )
    _assert_redis_network_policy_restricts_platform_pods(
        docs,
        redis_policy_name=redis_policy_name,
    )


@requires_helm
def test_redis_persistence_remains_empty_dir():
    """AC (Story 12.6): Redis stays ephemeral -- emptyDir only, no PVC."""
    docs = _render(_CORE_CHART)
    _assert_redis_persistence_is_empty_dir(docs)


@requires_helm
def test_namespace_inventory_includes_postgres_redis_platform_and_sidecar():
    """AC (AD-1): across ALL rendered workload pod specs, the image set
    reduces to exactly four -- postgres, redis, platform, and sidecar.
    """
    docs = _render(_CORE_CHART)
    images = _collect_workload_images(docs)

    _assert_image_inventory_is_exactly(images, _default_image_references())

@requires_helm
def test_ocp_overrides_drop_the_ingress_and_the_data_service_uids():
    """AC: rendered with the overlay's core-overrides.yaml, the core chart
    emits no Ingress and no runAsUser/fsGroup anywhere (the SCC assigns
    UIDs) -- while the postgres/redis workloads themselves still render
    (the override removes their UID pins, not the services) and the
    platform pods STAY restricted-v2 under the overridden values.
    """
    docs = _render(_CORE_CHART, "-f", str(_CORE_OVERRIDES))

    _assert_no_ingress_documents(docs)
    by_component = _pod_specs_by_component(docs)
    for component in ("postgres", "redis"):
        assert component in by_component, (
            f"{component} workload missing from the OCP-overridden render -- "
            f"the UID check below would pass vacuously"
        )
    _assert_no_fixed_uid_keys(docs)
    for component in sorted(_PLATFORM_COMPONENTS):
        _assert_restricted_v2_pod_spec(by_component[component], where=component)


@requires_helm
def test_overlay_route_default_targets_the_core_web_service():
    """AC (coupling): under the documented pairing (`helm install platform
    <core-chart>` -- a release name containing the chart name makes
    fullname the bare release name), the overlay's DEFAULT
    route.service.name equals the web Service name the core chart
    actually renders, and the Route's targetPort exists as a NAMED port
    on that Service.
    """
    core_docs = _render(_CORE_CHART, release="platform")
    web_services = [
        doc
        for doc in core_docs
        if doc.get("kind") == "Service"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == "web"
    ]
    assert len(web_services) == 1, (
        f"expected exactly one web Service in the core render, got: "
        f"{[doc['metadata']['name'] for doc in web_services]}"
    )
    overlay_docs = _render(_OVERLAY_CHART)
    routes = [doc for doc in overlay_docs if doc.get("kind") == "Route"]
    assert len(routes) == 1, (
        f"expected exactly one Route in the overlay render, got: "
        f"{[doc['metadata']['name'] for doc in routes]}"
    )

    _assert_route_targets_service(routes[0], web_services[0])


# ---------------------------------------------------------------------------
# Guard-removed companions (9.6 discipline) -- UNGATED, pure dicts, no
# helm/yaml, so they run in the pip-only CI lane too
# ---------------------------------------------------------------------------


def _restricted_v2_clean_pod_spec() -> dict[str, Any]:
    """A pod spec that PASSES `_assert_restricted_v2_pod_spec` -- the
    companions below each break exactly one field of a copy of this.
    """
    return {
        "securityContext": {
            "runAsNonRoot": True,
            "seccompProfile": {"type": "RuntimeDefault"},
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


def test_restricted_v2_check_fails_when_a_pod_spec_fixes_a_uid():
    """A pod spec that is restricted-v2-clean EXCEPT for a fixed UID, fed
    to the same helper the real test uses, must raise.
    """
    violating_pod_spec = _restricted_v2_clean_pod_spec()
    violating_pod_spec["securityContext"]["runAsUser"] = 1001

    with pytest.raises(AssertionError):
        _assert_restricted_v2_pod_spec(violating_pod_spec, where="synthetic-web")


def test_restricted_v2_check_fails_on_container_level_run_as_non_root_false():
    """A container-level `runAsNonRoot: false` silently overrides the
    pod-level true -- the helper must reject it.
    """
    violating_pod_spec = _restricted_v2_clean_pod_spec()
    violating_pod_spec["containers"][0]["securityContext"]["runAsNonRoot"] = False

    with pytest.raises(AssertionError):
        _assert_restricted_v2_pod_spec(violating_pod_spec, where="synthetic-web")


def test_restricted_v2_check_fails_when_a_container_adds_a_capability():
    """`capabilities: {drop: [ALL], add: [NET_ADMIN]}` drops everything
    then adds one back -- the helper must reject the add.
    """
    violating_pod_spec = _restricted_v2_clean_pod_spec()
    violating_pod_spec["containers"][0]["securityContext"]["capabilities"] = {
        "drop": ["ALL"],
        "add": ["NET_ADMIN"],
    }

    with pytest.raises(AssertionError):
        _assert_restricted_v2_pod_spec(violating_pod_spec, where="synthetic-web")


def test_restricted_v2_check_fails_on_a_container_level_seccomp_override():
    """A container-level seccompProfile that is not RuntimeDefault
    overrides the pod-level profile -- the helper must reject it.
    """
    violating_pod_spec = _restricted_v2_clean_pod_spec()
    violating_pod_spec["containers"][0]["securityContext"]["seccompProfile"] = {
        "type": "Unconfined",
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


def test_image_inventory_check_fails_on_a_fifth_image():
    """An image set with anything beyond the AD-1 quartet, fed to the same
    inventory helper the real test uses, must raise.
    """
    images = {
        "platform:latest",
        "postgres:17",
        "redis:7",
        "platform-dbgpt-sidecar:latest",
        "vault:1.15",
    }

    with pytest.raises(AssertionError):
        _assert_image_inventory_is_exactly(
            images,
            frozenset(
                {"platform", "postgres", "redis", "platform-dbgpt-sidecar"},
            ),
        )


def test_image_inventory_check_fails_on_a_superstring_sidecar_image():
    """`platform-dbgpt-sidecar-extra:1.0` CONTAINS the expected reference
    `platform-dbgpt-sidecar` as a substring -- exact tag-stripped matching
    must still count it as a fifth image (the bypass substring matching
    allowed).
    """
    images = {
        "platform:latest",
        "postgres:17",
        "redis:7",
        "platform-dbgpt-sidecar:latest",
        "platform-dbgpt-sidecar-extra:1.0",
    }

    with pytest.raises(AssertionError, match="platform-dbgpt-sidecar-extra"):
        _assert_image_inventory_is_exactly(
            images,
            frozenset(
                {"platform", "postgres", "redis", "platform-dbgpt-sidecar"},
            ),
        )


def test_ingress_absence_check_fails_when_an_ingress_is_present():
    """A document set still containing an Ingress, fed to the same helper
    the overrides test uses, must raise.
    """
    contaminated_docs = [
        {"kind": "Deployment", "metadata": {"name": "web"}},
        {"kind": "Ingress", "metadata": {"name": "leftover-edge"}},
    ]

    with pytest.raises(AssertionError):
        _assert_no_ingress_documents(contaminated_docs)


def test_fixed_uid_check_fails_on_a_surviving_run_as_user_or_fs_group():
    """Documents where runAsUser -- or the fsGroup the key-scan was
    extended to -- survives, fed to the same helper the overrides test
    uses, must raise for EACH key.
    """
    for key in ("runAsUser", "fsGroup"):
        contaminated_docs = [
            {
                "kind": "StatefulSet",
                "spec": {"template": {"spec": {"securityContext": {key: 999}}}},
            },
        ]

        with pytest.raises(AssertionError, match=key):
            _assert_no_fixed_uid_keys(contaminated_docs)


def test_pod_spec_collection_fails_when_the_component_label_is_missing():
    """A workload whose pod template lacks the component label must raise
    with an evidence-bearing message, never a bare KeyError.
    """
    unlabeled_docs = [
        {
            "kind": "Deployment",
            "metadata": {"name": "mystery-workload"},
            "spec": {"template": {"metadata": {"labels": {}}, "spec": {}}},
        },
    ]

    with pytest.raises(AssertionError, match="mystery-workload"):
        _pod_specs_by_component(unlabeled_docs)


def test_pod_spec_collection_fails_on_a_duplicate_component_label():
    """Two workloads sharing one component label must raise (naming the
    label) instead of last-wins silently dropping a pod spec.
    """

    def workload(name: str) -> dict[str, Any]:
        return {
            "kind": "Deployment",
            "metadata": {"name": name},
            "spec": {
                "template": {
                    "metadata": {"labels": {"app.kubernetes.io/component": "web"}},
                    "spec": {},
                },
            },
        }

    with pytest.raises(AssertionError, match="'web'"):
        _pod_specs_by_component([workload("first"), workload("second")])


def test_route_target_check_fails_on_a_mismatched_service_name_or_port():
    """A Route pointing at a differently-named Service -- or at a port the
    Service does not carry by NAME -- fed to the same coupling helper the
    real test uses, must raise.
    """
    route = {"spec": {"to": {"name": "platform"}, "port": {"targetPort": "http"}}}
    renamed_service = {
        "metadata": {"name": "other-release-platform"},
        "spec": {"ports": [{"name": "http", "port": 8000}]},
    }

    with pytest.raises(AssertionError):
        _assert_route_targets_service(route, renamed_service)

    unnamed_port_service = {
        "metadata": {"name": "platform"},
        "spec": {"ports": [{"port": 8000}]},
    }

    with pytest.raises(AssertionError):
        _assert_route_targets_service(route, unnamed_port_service)


def test_redis_auth_check_fails_when_requirepass_is_missing():
    """A redis container without --requirepass wiring must raise."""
    platform_env: list[dict[str, Any]] = [
        {
            "name": "REDIS_PASSWORD",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "platform-secrets",
                    "key": "REDIS_PASSWORD",
                },
            },
        },
        {
            "name": "REDIS_URL",
            "value": "redis://:$(REDIS_PASSWORD)@platform-redis:6379/0",
        },
    ]

    def platform_deployment(component: str) -> dict[str, Any]:
        return {
            "kind": "Deployment",
            "metadata": {
                "name": f"platform-{component}",
                "labels": {"app.kubernetes.io/component": component},
            },
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {"app.kubernetes.io/component": component},
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": component,
                                "image": "platform:latest",
                                "env": platform_env,
                            },
                        ],
                    },
                },
            },
        }

    docs = [
        {
            "kind": "Deployment",
            "metadata": {
                "name": "platform-redis",
                "labels": {"app.kubernetes.io/component": "redis"},
            },
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {"app.kubernetes.io/component": "redis"},
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "redis",
                                "image": "redis:7",
                                "env": [platform_env[0]],
                                "command": ["redis-server"],
                            },
                        ],
                    },
                },
            },
        },
        platform_deployment("web"),
        platform_deployment("worker"),
        platform_deployment("migrate"),
    ]

    secret_ref = cast("dict[str, str]", platform_env[0]["valueFrom"]["secretKeyRef"])
    with pytest.raises(AssertionError, match="requirepass"):
        _assert_redis_uses_password_from_existing_secret(
            docs,
            secret_name=secret_ref["name"],
            password_key=secret_ref["key"],
            redis_service_host="platform-redis",
        )


def test_redis_network_policy_check_fails_when_sidecar_is_allowed():
    """A NetworkPolicy that admits the sidecar component must raise."""
    contaminated_policy = [
        {
            "kind": "NetworkPolicy",
            "metadata": {"name": "platform-redis"},
            "spec": {
                "podSelector": {
                    "matchLabels": {"app.kubernetes.io/component": "redis"},
                },
                "ingress": [
                    {
                        "from": [
                            {
                                "podSelector": {
                                    "matchExpressions": [
                                        {
                                            "key": "app.kubernetes.io/component",
                                            "operator": "In",
                                            "values": [
                                                "web",
                                                "worker",
                                                "migrate",
                                                "dbgpt",
                                            ],
                                        },
                                    ],
                                },
                            },
                        ],
                        "ports": [{"protocol": "TCP", "port": 6379}],
                    },
                ],
            },
        },
    ]

    with pytest.raises(AssertionError, match="component filter"):
        _assert_redis_network_policy_restricts_platform_pods(
            contaminated_policy,
            redis_policy_name="platform-redis",
        )


def test_redis_empty_dir_check_fails_when_a_pvc_volume_is_present():
    """A redis Deployment with a PVC-backed volume must raise."""
    contaminated_docs = [
        {
            "kind": "Deployment",
            "metadata": {
                "name": "platform-redis",
                "labels": {"app.kubernetes.io/component": "redis"},
            },
            "spec": {
                "template": {
                    "spec": {
                        "volumes": [
                            {
                                "name": "data",
                                "persistentVolumeClaim": {"claimName": "redis-data"},
                            },
                        ],
                    },
                },
            },
        },
    ]

    with pytest.raises(AssertionError, match="emptyDir"):
        _assert_redis_persistence_is_empty_dir(contaminated_docs)
