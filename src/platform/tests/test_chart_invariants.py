"""Story 12.1 -- chart invariants (AD-11/AD-12, CAP-6).

The core chart (`deploy/charts/platform/`) must stay vanilla Kubernetes and
the OCP overlay (`deploy/overlays/ocp/`) must stay a thin Route; the
platform-image pods (web, worker, migrate) must carry the OCP
`restricted-v2` contract with no fixed UID anywhere; and the namespace
inventory must be exactly PostgreSQL + Redis + the platform image + the
DB-GPT sidecar (AD-1, Story 12.5). Story 26.2 / canopy AD-19 adds that
rendered manifests carry secretKeyRefs, never secret *values*. This module
makes those invariants tests over parsed `helm template` output rather
than conventions.

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

import re
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
        "CronJob",
        "ServiceAccount",
        "PersistentVolumeClaim",
        "NetworkPolicy",
        "ConfigMap",
    },
)
_WORKLOAD_KINDS = frozenset({"Deployment", "StatefulSet", "Job", "CronJob"})
# Story 42.3 / canopy AD-8: one `consume_events` Deployment per station in
# values `events.consumers`; each is a platform-image pod that reaches
# redis-broker. These are the chart's DEFAULT consumers (values.yaml) --
# the consume-events proof below derives the list from values instead.
_DEFAULT_EVENT_CONSUMERS = ("doctor", "mason")
_CONSUME_EVENTS_PREFIX = "consume-events-"
_CONSUME_EVENTS_ARGS = ("python", "manage.py", "consume_events", "--station")
_CONSUME_EVENTS_COMPONENTS = frozenset(
    f"{_CONSUME_EVENTS_PREFIX}{station}" for station in _DEFAULT_EVENT_CONSUMERS
)
# Story 42.4: the builds pool (a second Celery worker consuming only
# `builds`) and the single-replica beat scheduler -- both platform-image
# pods that reach redis-broker.
_WORKER_BUILDS_COMPONENT = "worker-builds"
_BEAT_COMPONENT = "beat"
_CELERY_WORKER_ARGS = ("celery", "-A", "config", "worker", "-l", "info")
_BEAT_ARGS = ("celery", "-A", "config", "beat", "-l", "info", "--pidfile=")
_BUILDS_LIMIT_ENV = "CELERY_BUILDS_TASK_TIME_LIMIT"
# The pods that run the Story 10.3 platform image and must therefore carry
# the restricted-v2 contract, and reach Redis (NetworkPolicy / REDIS_* env).
# "migrate" doubles as proof the hook Job renders (`helm template` emits
# hooks).
_PLATFORM_COMPONENTS = (
    frozenset({"web", "worker", _WORKER_BUILDS_COMPONENT, _BEAT_COMPONENT, "migrate"})
    | _CONSUME_EVENTS_COMPONENTS
)
# Restricted-v2 + same image as web. Liquibase does not speak Redis, so it
# is not in _PLATFORM_COMPONENTS (NetworkPolicy / REDIS_* env).
_PLATFORM_IMAGE_COMPONENTS = _PLATFORM_COMPONENTS | {"liquibase", "postgres-backup"}
# Story 41.2: reader pods (web hosts Vizro/BSL) must not mount the writer's
# ``.duckdb`` file. Celery ``worker`` is the single writer — not a reader.
_QUERY_PLANE_READER_COMPONENTS = frozenset({"web"})
_PLANE_FILE_MARKERS = (".duckdb", "atlas.duckdb")
# PVC labels/names carrying this marker are plane storage claims (writer RWO only).
_PLANE_PVC_LABEL = "pyforge.io/query-plane"
# Story 12.5: the DB-GPT sidecar carries the same restricted-v2 contract.
_SIDECAR_COMPONENT = "dbgpt"
# Story 21.x / 42.1: the isolated MCP-host sidecar.
_MCP_HOST_COMPONENT = "mcp-host"
_REDIS_COMPONENTS = frozenset({"redis-cache", "redis-broker"})
# Story 26.2 / canopy AD-19: env names that must be secretKeyRef, never `value`.
_SECRET_ENV_NAMES = frozenset(
    {
        "DJANGO_SECRET_KEY",
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "POSTGRES_PASSWORD",
        "REDIS_PASSWORD",
        "DBGPT_LLM_API_KEY",
        "COMPONENT_OIDC_CLIENT_SECRET",
    },
)
_SECRETISH_ENV_NAME = re.compile(
    r"(PASSWORD|SECRET|TOKEN|API_KEY|APIKEY|CREDENTIAL|PRIVATE.?KEY)",
    re.IGNORECASE,
)
# Unique payload injected via helm --set-string; templates must not emit it.
_SECRET_VALUE_CANARY = "CANARY-26-2-SECRET-VALUE-NOT-FOR-RENDER"  # noqa: S105
_VAULT_CSI_ANNOTATION_MARKERS = (
    "vault.hashicorp.com/",
    "agent-inject",
    "secrets-store.csi.x-k8s.io/",
)
_SECRETS_HTTP_API_IMPORT = re.compile(
    r"(?m)^\s*(?:from|import)\s+"
    r"(hvac|azure\.keyvault|google\.cloud\.secretmanager)\b"
    r"|boto3\.client\(\s*[\"']secretsmanager[\"']"
    r"|SecretManagerServiceClient"
    r"|hashicorp\.vault",
)
_CHART_VALUE_SECRET_KEYS = frozenset(
    {"password", "secret", "secretkey", "apikey", "token", "clientsecret"},
)

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
    argv = ["helm", *args]
    touches_core = False
    for item in args[1:]:
        if item.startswith("-"):
            continue
        try:
            if Path(item).resolve() == _CORE_CHART.resolve():
                touches_core = True
                break
        except OSError:
            continue
    if touches_core and "--set-file" not in args:
        argv.extend(
            ["--set-file", f"flags.tree={_PLATFORM_DIR / 'config' / 'flags.json'}"],
        )
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        argv,
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
    """The five expected tag-stripped image references, DERIVED from the
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
        values["mcpHost"]["image"],
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
        template = _pod_template(doc)
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


def _pod_template(doc: dict[str, Any]) -> dict[str, Any]:
    """The pod template of any `_WORKLOAD_KINDS` doc.

    A CronJob nests its template one level deeper than every other workload
    (`spec.jobTemplate.spec.template`, not `spec.template`). Story 41.1 added
    the chart's first CronJob, and helpers that reached for `spec.template`
    directly began raising `KeyError: 'template'` on it -- a crash, not a
    verdict, so the CronJob went effectively unchecked by every invariant
    that walks workloads. Resolve the shape in ONE place so a future kind
    cannot re-open that hole per-caller.
    """
    if doc.get("kind") == "CronJob":
        return doc["spec"]["jobTemplate"]["spec"]["template"]
    return doc["spec"]["template"]


def _workload_pod_spec(doc: dict[str, Any]) -> dict[str, Any]:
    return _pod_template(doc)["spec"]


def _iter_pod_containers(pod_spec: dict[str, Any]) -> list[dict[str, Any]]:
    return list(pod_spec.get("containers") or []) + list(
        pod_spec.get("initContainers") or [],
    )


def _is_secret_env_name(name: str) -> bool:
    return name in _SECRET_ENV_NAMES or bool(_SECRETISH_ENV_NAME.search(name))


def _collect_string_leaves(node: object) -> list[str]:
    leaves: list[str] = []
    if isinstance(node, str):
        leaves.append(node)
    elif isinstance(node, dict):
        for child in node.values():
            leaves.extend(_collect_string_leaves(child))
    elif isinstance(node, list):
        for child in node:
            leaves.extend(_collect_string_leaves(child))
    return leaves


def _assert_no_secret_values_in_docs(
    docs: list[dict[str, Any]],
    *,
    canary: str | None = None,
) -> None:
    """Story 26.2 / FR-32: rendered manifests carry names and keys, never
    secret *values*. Fails if the canary appears anywhere, if a secret-named
    env var uses inline ``value``, or if a Secret object is rendered.
    """
    assert docs, "empty render -- secret-value check would pass vacuously"
    if canary:
        for path, text in enumerate(_collect_string_leaves(docs)):
            assert canary not in text, (
                f"secret canary {canary!r} appeared in rendered YAML "
                f"(leaf index {path}): {text!r}"
            )
    secret_kinds = [
        (doc.get("kind"), (doc.get("metadata") or {}).get("name"))
        for doc in docs
        if doc.get("kind") == "Secret"
    ]
    assert not secret_kinds, (
        f"chart rendered Secret objects (values would leak in git): {secret_kinds}"
    )
    by_component = _pod_specs_by_component(docs)
    for component, pod_spec in by_component.items():
        for container in _iter_pod_containers(pod_spec):
            cname = container.get("name")
            where = f"{component}/{cname}"
            for entry in container.get("env") or []:
                name = str(entry.get("name", ""))
                inline = entry.get("value")
                if canary and inline is not None and canary in str(inline):
                    msg = f"{where}: env {name} inlined canary secret value"
                    raise AssertionError(msg)
                if not _is_secret_env_name(name):
                    continue
                if inline not in (None, ""):
                    msg = (
                        f"{where}: secret-named env {name} has inline value "
                        f"{inline!r} -- must be secretKeyRef (canopy AD-19)"
                    )
                    raise AssertionError(msg)
                ref = (entry.get("valueFrom") or {}).get("secretKeyRef") or {}
                assert ref.get("name"), (
                    f"{where}: secret-named env {name} missing secretKeyRef "
                    f"name: {entry!r}"
                )
                assert ref.get("key"), (
                    f"{where}: secret-named env {name} missing secretKeyRef "
                    f"key: {entry!r}"
                )


def _assert_no_vault_csi_or_secrets_sidecar(docs: list[dict[str, Any]]) -> None:
    """Canopy AD-19: Vault injector, secrets CSI, extra secrets sidecar
    require a dated Dream — they must not appear in this chain's charts.
    """
    assert docs, "empty render -- vault/CSI check would pass vacuously"
    for doc in docs:
        kind = doc.get("kind")
        name = (doc.get("metadata") or {}).get("name")
        annotations = {
            **((doc.get("metadata") or {}).get("annotations") or {}),
            **(
                ((doc.get("spec") or {}).get("template") or {})
                .get("metadata", {})
                .get("annotations")
                or {}
            ),
        }
        for key, value in annotations.items():
            blob = f"{key}={value}"
            for marker in _VAULT_CSI_ANNOTATION_MARKERS:
                assert marker not in blob, (
                    f"{kind} {name!r}: vault/CSI annotation {blob!r}"
                )
        if kind not in _WORKLOAD_KINDS:
            continue
        pod_spec = _workload_pod_spec(doc)
        for volume in pod_spec.get("volumes") or []:
            csi = volume.get("csi") or {}
            driver = str(csi.get("driver") or "")
            assert "secrets-store" not in driver, (
                f"{kind} {name!r}: secrets CSI volume {volume.get('name')!r} "
                f"driver={driver!r}"
            )
        for container in _iter_pod_containers(pod_spec):
            cname = str(container.get("name") or "")
            image = str(container.get("image") or "")
            assert "vault-agent" not in cname, (
                f"{kind} {name!r}: extra secrets sidecar container {cname!r}"
            )
            image_name = image.rsplit("/", maxsplit=1)[-1].split(":", maxsplit=1)[0]
            assert "vault" not in image_name, (
                f"{kind} {name!r}: vault image on container {cname!r}: {image!r}"
            )


def _assert_chart_values_hold_no_secret_payloads(
    values: dict[str, Any],
    path: str = "",
) -> None:
    """Committed chart values name Secrets/keys; they must not hold passwords."""
    for key, child in values.items():
        child_path = f"{path}.{key}" if path else str(key)
        if key.lower() in _CHART_VALUE_SECRET_KEYS and isinstance(child, str) and child:
            msg = (
                f"chart value {child_path} holds a secret payload {child!r} "
                f"-- names/keys only (FR-32)"
            )
            raise AssertionError(msg)
        if isinstance(child, dict):
            _assert_chart_values_hold_no_secret_payloads(child, child_path)


def _assert_app_does_not_call_secrets_http_api(root: Path) -> None:
    """Runtime delivery is env/mounts (parent AD-12), not a secrets HTTP API."""
    offenders: list[str] = []
    skip_parts = frozenset({"tests", "compose"})
    for path in sorted(root.rglob("*.py")):
        if skip_parts.intersection(path.relative_to(root).parts):
            continue
        text = path.read_text(encoding="utf-8")
        if _SECRETS_HTTP_API_IMPORT.search(text):
            offenders.append(str(path.relative_to(root)))
    assert not offenders, (
        f"platform app calls a secrets HTTP API (canopy AD-19 forbids it): "
        f"{offenders}"
    )


def _collect_workload_images(docs: list[dict[str, Any]]) -> set[str]:
    images: set[str] = set()
    for doc in docs:
        if doc.get("kind") not in _WORKLOAD_KINDS:
            continue
        pod_spec = _workload_pod_spec(doc)
        containers = list(pod_spec.get("containers") or []) + list(
            pod_spec.get("initContainers") or [],
        )
        for container in containers:
            images.add(container["image"])
    return images


def _redis_deployments(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        doc
        for doc in docs
        if doc.get("kind") == "Deployment"
        and str(
            (doc.get("metadata") or {}).get("labels", {}).get(
                "app.kubernetes.io/component",
                "",
            ),
        ).startswith("redis-")
    ]


def _assert_redis_cache_persistence_is_empty_dir(docs: list[dict[str, Any]]) -> None:
    """Story 12.6 / 40.2: redis-cache stays ephemeral -- emptyDir only."""
    cache_deployments = [
        doc
        for doc in _redis_deployments(docs)
        if (doc.get("metadata") or {}).get("labels", {}).get(
            "app.kubernetes.io/component",
        )
        == "redis-cache"
    ]
    assert len(cache_deployments) == 1, (
        f"expected exactly one redis-cache Deployment, got {cache_deployments!r}"
    )
    volumes = cache_deployments[0]["spec"]["template"]["spec"].get("volumes") or []
    assert volumes, "redis-cache has no volumes -- emptyDir check vacuous"
    for volume in volumes:
        assert "emptyDir" in volume, (
            f"redis-cache volume {volume.get('name')!r} is not emptyDir: {volume!r}"
        )
        assert "persistentVolumeClaim" not in volume, (
            f"redis-cache volume {volume.get('name')!r} uses a PVC -- cache must "
            f"stay ephemeral (Story 12.6)"
        )


def _assert_redis_broker_persistence_is_pvc_with_aof(docs: list[dict[str, Any]]) -> None:
    """Story 40.2: redis-broker mounts a PVC at /data and enables AOF."""
    broker_deployments = [
        doc
        for doc in _redis_deployments(docs)
        if (doc.get("metadata") or {}).get("labels", {}).get(
            "app.kubernetes.io/component",
        )
        == "redis-broker"
    ]
    assert len(broker_deployments) == 1, (
        f"expected exactly one redis-broker Deployment, got {broker_deployments!r}"
    )
    deployment = broker_deployments[0]
    volumes = deployment["spec"]["template"]["spec"].get("volumes") or []
    data_volumes = [volume for volume in volumes if volume.get("name") == "data"]
    assert len(data_volumes) == 1, f"redis-broker missing data volume: {volumes!r}"
    assert "persistentVolumeClaim" in data_volumes[0], (
        f"redis-broker data volume must be a PVC, got {data_volumes[0]!r}"
    )
    command = deployment["spec"]["template"]["spec"]["containers"][0].get("command") or []
    assert "--appendonly" in command and "yes" in command, (
        f"redis-broker missing AOF args: {command!r}"
    )
    assert "--appendfsync" in command and "everysec" in command, (
        f"redis-broker missing appendfsync everysec: {command!r}"
    )
    assert "--maxmemory" in command, f"redis-broker missing --maxmemory: {command!r}"
    assert "noeviction" in command, (
        f"redis-broker must keep noeviction policy: {command!r}"
    )
    broker_pvcs = [
        doc
        for doc in docs
        if doc.get("kind") == "PersistentVolumeClaim"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == "redis-broker"
    ]
    assert len(broker_pvcs) == 1, broker_pvcs
    assert broker_pvcs[0]["spec"]["accessModes"] == ["ReadWriteOnce"]
    claim_name = data_volumes[0]["persistentVolumeClaim"]["claimName"]
    assert broker_pvcs[0]["metadata"]["name"] == claim_name


def _assert_query_plane_readers_do_not_mount_duckdb_file(
    docs: list[dict[str, Any]],
) -> None:
    """Story 41.2: web (Vizro/BSL) reader pods never mount the writer's ``.duckdb`` file."""
    by_component = _pod_specs_by_component(docs)
    for component in sorted(_QUERY_PLANE_READER_COMPONENTS):
        pod_spec = by_component[component]
        for container in _iter_pod_containers(pod_spec):
            mounts = container.get("volumeMounts") or []
            for mount in mounts:
                mount_path = str(mount.get("mountPath") or "")
                lowered = mount_path.lower()
                assert not any(marker in lowered for marker in _PLANE_FILE_MARKERS), (
                    f"{component} mounts query-plane file {mount_path!r} — "
                    f"readers must use Parquet + Postgres attach only (Story 41.2)"
                )


def _assert_query_plane_pvcs_are_read_write_once(docs: list[dict[str, Any]]) -> None:
    """Story 41.2: any plane PVC is RWO — ReadWriteMany is a finding."""
    plane_pvcs = [
        doc
        for doc in docs
        if doc.get("kind") == "PersistentVolumeClaim"
        and (
            (doc.get("metadata") or {}).get("labels", {}).get(_PLANE_PVC_LABEL) == "true"
            or "query-plane" in str(doc.get("metadata", {}).get("name", "")).lower()
            or "atlas.duckdb" in str(doc.get("metadata", {}).get("name", "")).lower()
        )
    ]
    for pvc in plane_pvcs:
        access_modes = (pvc.get("spec") or {}).get("accessModes") or []
        assert access_modes == ["ReadWriteOnce"], (
            f"query-plane PVC {pvc['metadata']['name']!r} must be ReadWriteOnce, "
            f"got {access_modes!r} (Story 41.2 / BS-5)"
        )


def _assert_redis_uses_password_from_existing_secret(
    docs: list[dict[str, Any]],
    *,
    secret_name: str,
    password_key: str,
    broker_host: str,
    cache_host: str,
) -> None:
    """Story 12.6 AUTH + Story 20.2: both Redis pods take password from
    existingSecret; platform pods get distinct broker/cache URLs.
    """
    by_component = _pod_specs_by_component(docs)
    missing = sorted(_REDIS_COMPONENTS - by_component.keys())
    assert not missing, f"redis workloads missing from render: {missing}"

    secret_ref = {"name": secret_name, "key": password_key}
    for component in sorted(_REDIS_COMPONENTS):
        redis_env = _collect_env_by_name(by_component[component])
        redis_password = redis_env.get("REDIS_PASSWORD")
        assert redis_password is not None, f"{component} missing REDIS_PASSWORD"
        assert redis_password.get("valueFrom", {}).get("secretKeyRef") == secret_ref, (
            f"{component} REDIS_PASSWORD secretKeyRef mismatch: {redis_password!r}"
        )
        command = by_component[component]["containers"][0].get("command") or []
        assert command[:3] == [
            "redis-server",
            "--requirepass",
            "$(REDIS_PASSWORD)",
        ], f"{component} command missing --requirepass wiring: {command!r}"
        if component == "redis-cache":
            assert "--maxmemory" in command, (
                f"redis-cache missing --maxmemory: {command!r}"
            )
            assert "allkeys-lru" in command, (
                f"redis-cache must evict with allkeys-lru, got {command!r}"
            )
        else:
            assert "noeviction" in command, (
                f"redis-broker must not evict, got {command!r}"
            )
            assert "allkeys-lru" not in command, (
                f"redis-broker must not share the cache eviction policy: {command!r}"
            )

    expected_broker = f"redis://:$(REDIS_PASSWORD)@{broker_host}:6379/0"
    expected_cache = f"redis://:$(REDIS_PASSWORD)@{cache_host}:6379/0"
    assert expected_broker != expected_cache, (
        "broker and cache Service DNS names must differ"
    )
    for component in sorted(_PLATFORM_COMPONENTS):
        env = _collect_env_by_name(by_component[component])
        password_env = env.get("REDIS_PASSWORD")
        assert password_env is not None, f"{component} pod missing REDIS_PASSWORD env"
        assert password_env.get("valueFrom", {}).get("secretKeyRef") == secret_ref, (
            f"{component} REDIS_PASSWORD secretKeyRef mismatch: {password_env!r}"
        )
        broker_url = env.get("REDIS_BROKER_URL")
        cache_url = env.get("REDIS_CACHE_URL")
        redis_url = env.get("REDIS_URL")
        assert broker_url is not None, f"{component} missing REDIS_BROKER_URL"
        assert cache_url is not None, f"{component} missing REDIS_CACHE_URL"
        assert broker_url.get("value") == expected_broker, (
            f"{component} REDIS_BROKER_URL is {broker_url.get('value')!r}, "
            f"expected {expected_broker!r}"
        )
        assert cache_url.get("value") == expected_cache, (
            f"{component} REDIS_CACHE_URL is {cache_url.get('value')!r}, "
            f"expected {expected_cache!r}"
        )
        assert redis_url is not None, f"{component} missing REDIS_URL"
        assert redis_url.get("value") == expected_broker, (
            f"{component} REDIS_URL must alias the broker, got {redis_url!r}"
        )


def _assert_redis_network_policy_restricts_platform_pods(
    docs: list[dict[str, Any]],
    *,
    redis_policy_name: str,
    redis_component: str,
) -> None:
    """Story 12.6: a NetworkPolicy targets one redis-* component and allows
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
    assert selector.get("matchLabels", {}).get("app.kubernetes.io/component") == (
        redis_component
    )

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


def _release_scoping_labels(docs: list[dict[str, Any]]) -> dict[str, str]:
    """The release scoping labels, DERIVED from a rendered workload's own
    ``spec.selector.matchLabels`` (the ``platform.selectorLabels`` include)
    rather than re-declared here -- everything but the component key.
    """
    for doc in docs:
        if doc.get("kind") != "Deployment":
            continue
        labels = (doc.get("metadata") or {}).get("labels") or {}
        if labels.get("app.kubernetes.io/component") != _MCP_HOST_COMPONENT:
            continue
        match_labels = dict(doc["spec"]["selector"]["matchLabels"])
        match_labels.pop("app.kubernetes.io/component", None)
        assert match_labels, (
            f"the mcp-host Deployment selector carries no scoping labels beyond "
            f"its component: {doc['spec']['selector']}"
        )
        return match_labels
    msg = "no mcp-host Deployment in the render to derive scoping labels from"
    raise AssertionError(msg)


def _assert_selector_is_release_scoped(
    selector: dict[str, Any],
    scoping_labels: dict[str, str],
    where: str,
) -> None:
    """A selector must carry the release scoping labels, not only a component.

    ``app.kubernetes.io/component`` alone matches ANY pod in the namespace
    carrying that component label -- including one from another release, or one
    an attacker labels. Dropping the ``platform.selectorLabels`` include from
    either selector is therefore a silent widening, so both are checked here.
    """
    for key, value in sorted(scoping_labels.items()):
        assert selector.get(key) == value, (
            f"{where}: selector is not release-scoped -- {key} is "
            f"{selector.get(key)!r}, expected {value!r} (selector: {selector!r})"
        )


def _assert_mcp_host_network_policy_admits_web_only(
    docs: list[dict[str, Any]],
    *,
    policy_name: str,
    scoping_labels: dict[str, str],
) -> None:
    """Story 42.1 / red-team X-5: exactly one NetworkPolicy selects the
    mcp-host pods and its only ingress rule admits the ``web`` component of
    THIS release on TCP/8090. mcp-host carries no auth of its own, so any
    second admitted peer -- another component, another namespace, or any pod
    that merely wears the ``web`` component label -- is a namespace-wide (or
    cluster-wide) unauthenticated MCP server.
    """
    policies = [
        doc
        for doc in docs
        if doc.get("kind") == "NetworkPolicy"
        and doc["metadata"]["name"] == policy_name
    ]
    rendered = [
        doc["metadata"]["name"] for doc in docs if doc.get("kind") == "NetworkPolicy"
    ]
    assert len(policies) == 1, (
        f"expected exactly one mcp-host NetworkPolicy named {policy_name!r}, "
        f"got {rendered}"
    )
    policy = policies[0]
    selector = policy["spec"]["podSelector"].get("matchLabels", {})
    assert selector.get("app.kubernetes.io/component") == _MCP_HOST_COMPONENT, (
        f"mcp-host NetworkPolicy selects {selector!r}, not the mcp-host component"
    )
    _assert_selector_is_release_scoped(
        selector,
        scoping_labels,
        "mcp-host NetworkPolicy podSelector",
    )
    assert policy["spec"].get("policyTypes") == ["Ingress"], policy["spec"]

    ingress_rules = policy["spec"].get("ingress") or []
    assert len(ingress_rules) == 1, (
        f"mcp-host NetworkPolicy must have exactly one ingress rule, got "
        f"{ingress_rules!r}"
    )
    rule = ingress_rules[0]
    from_entries = rule.get("from") or []
    assert len(from_entries) == 1, (
        f"mcp-host ingress.from must have one podSelector entry, got {from_entries!r}"
    )
    # A peer is the UNION of its keys: a namespaceSelector or ipBlock sitting
    # beside the podSelector widens the rule to web-labelled pods in any
    # namespace (or to raw CIDRs), which is precisely the X-5 exposure.
    entry_keys = set(from_entries[0])
    assert entry_keys == {"podSelector"}, (
        f"mcp-host ingress peer must be a podSelector and nothing else, got "
        f"{sorted(entry_keys)}"
    )
    pod_selector = from_entries[0].get("podSelector") or {}
    # A matchExpressions branch would be a second way to widen the rule --
    # require the single-component matchLabels form, nothing else.
    assert not pod_selector.get("matchExpressions"), (
        f"mcp-host ingress must admit web by matchLabels only, got {pod_selector!r}"
    )
    admitted_labels = pod_selector.get("matchLabels") or {}
    admitted = admitted_labels.get("app.kubernetes.io/component")
    assert admitted == "web", (
        f"mcp-host ingress admits {admitted!r}; only web reaches the sidecar "
        f"(Story 42.1 -- web is where the assertion is verified)"
    )
    _assert_selector_is_release_scoped(
        admitted_labels,
        scoping_labels,
        "mcp-host NetworkPolicy ingress podSelector",
    )
    ports = rule.get("ports") or []
    assert ports == [{"protocol": "TCP", "port": 8090}], (
        f"mcp-host NetworkPolicy must allow TCP/8090 only, got {ports!r}"
    )


def _assert_liquibase_then_fake_migrate_jobs(docs: list[dict[str, Any]]) -> None:
    """Story 27.2 / FR-24 / canopy AD-9: two hook Jobs, weights -1 then 0,
    same platform image as web, no initContainers, liquibase update then
    migrate --fake.
    """
    jobs = [doc for doc in docs if doc.get("kind") == "Job"]
    by_component: dict[str, dict[str, Any]] = {}
    for job in jobs:
        labels = (job.get("metadata") or {}).get("labels") or {}
        component = labels.get("app.kubernetes.io/component")
        assert component not in by_component, (
            f"duplicate Job component {component!r}"
        )
        by_component[component] = job
    missing = sorted({"liquibase", "migrate"} - by_component.keys())
    assert not missing, f"expected liquibase and migrate Jobs, missing {missing}"

    liquibase = by_component["liquibase"]
    migrate = by_component["migrate"]
    lb_ann = (liquibase.get("metadata") or {}).get("annotations") or {}
    mg_ann = (migrate.get("metadata") or {}).get("annotations") or {}
    assert lb_ann.get("helm.sh/hook-weight") == "-1", lb_ann
    assert mg_ann.get("helm.sh/hook-weight") == "0", mg_ann
    for job in (liquibase, migrate):
        hook = ((job.get("metadata") or {}).get("annotations") or {}).get(
            "helm.sh/hook",
        )
        assert hook == "post-install,pre-upgrade", hook

    by_pod = _pod_specs_by_component(docs)
    for component in ("liquibase", "migrate", "web"):
        assert component in by_pod, f"{component} missing from render"
        inits = by_pod[component].get("initContainers") or []
        assert not inits, (
            f"{component} must not use an initContainer (FR-24): {inits}"
        )
    web_image = by_pod["web"]["containers"][0]["image"]
    assert by_pod["liquibase"]["containers"][0]["image"] == web_image
    assert by_pod["migrate"]["containers"][0]["image"] == web_image

    lb_args = by_pod["liquibase"]["containers"][0].get("args") or []
    assert lb_args == ["python", "db/liquibase_update.py"], lb_args
    mg_args = by_pod["migrate"]["containers"][0].get("args") or []
    assert mg_args == [
        "python",
        "manage.py",
        "migrate",
        "--fake",
        "--noinput",
    ], mg_args

    lb_env = _collect_env_by_name(by_pod["liquibase"])
    mg_env = _collect_env_by_name(by_pod["migrate"])
    assert "MIGRATION_DATABASE_URL" in lb_env
    assert (lb_env["MIGRATION_DATABASE_URL"].get("valueFrom") or {}).get(
        "secretKeyRef",
        {},
    ).get("key") == "MIGRATION_DATABASE_URL"
    assert "DATABASE_URL" not in lb_env
    assert "DATABASE_URL" in mg_env
    rendered = str(docs)
    assert "pgbouncer" not in rendered.lower()
    assert "pgpool" not in rendered.lower()
    assert "initContainer" not in str(liquibase.get("spec"))
    assert "initContainer" not in str(migrate.get("spec"))


def _assert_postgres_backup_cronjob_present(docs: list[dict[str, Any]]) -> None:
    """Story 41.1: backup CronJob + RWX PVC + postgres archive_mode."""
    cronjobs = [
        doc
        for doc in docs
        if doc.get("kind") == "CronJob"
        and (doc.get("metadata") or {}).get("labels", {}).get(
            "app.kubernetes.io/component",
        )
        == "postgres-backup"
    ]
    assert len(cronjobs) == 1, cronjobs
    schedule = cronjobs[0]["spec"].get("schedule")
    assert schedule, "postgres-backup CronJob missing schedule"

    backup_pvcs = [
        doc
        for doc in docs
        if doc.get("kind") == "PersistentVolumeClaim"
        and (doc.get("metadata") or {}).get("labels", {}).get(
            "app.kubernetes.io/component",
        )
        == "postgres-backup"
    ]
    assert len(backup_pvcs) == 1, backup_pvcs
    assert "ReadWriteMany" in backup_pvcs[0]["spec"]["accessModes"]

    postgres = [
        doc
        for doc in docs
        if doc.get("kind") == "StatefulSet"
        and (doc.get("metadata") or {}).get("labels", {}).get(
            "app.kubernetes.io/component",
        )
        == "postgres"
    ]
    assert len(postgres) == 1, postgres
    pod_spec = postgres[0]["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]
    args = container.get("args") or []
    joined = " ".join(str(item) for item in args)
    assert "archive_mode=on" in joined, args
    assert "archive_command=" in joined, args
    backup_mounts = [
        mount
        for mount in container.get("volumeMounts") or []
        if mount.get("name") == "backup"
    ]
    assert backup_mounts, "postgres missing backup volumeMount"

    # A mount only resolves against a volume declared in the POD spec. The
    # `volumes:` block indented one level too shallow lands on
    # StatefulSet.spec, an unknown field there: the archive target is then
    # unbacked and the API server rejects the pod outright. Asserting the
    # mount alone (as this helper first did) passes either way, which is how
    # that shipped -- so assert the volume, and assert the absence of the
    # misplaced key that silently swallows it.
    assert "volumes" not in postgres[0]["spec"], (
        "`volumes` on StatefulSet.spec is not a StatefulSetSpec field -- it "
        "belongs on spec.template.spec (the pod): "
        f"{postgres[0]['spec']['volumes']}"
    )
    volumes = pod_spec.get("volumes") or []
    backup_volume = next(
        (vol for vol in volumes if vol.get("name") == "backup"), None
    )
    assert backup_volume is not None, (
        "postgres pod declares no `backup` volume to back its `backup` "
        f"volumeMount (pod-spec volumes: {volumes})"
    )
    assert (
        backup_volume["persistentVolumeClaim"]["claimName"]
        == backup_pvcs[0]["metadata"]["name"]
    ), backup_volume

    # AC: the archive lands on the BACKUP volume, not some other path.
    mount_path = backup_mounts[0]["mountPath"]
    assert f"{mount_path}/wal/" in joined, (
        f"archive_command does not target the backup mount {mount_path}: {args}"
    )
    # Archiving begins at boot; the CronJob does not create wal/ until its
    # first scheduled run, so archive_command must create it itself or every
    # segment fails and pg_wal grows unbounded on the data PVC.
    assert f"mkdir -p {mount_path}/wal" in joined, (
        f"archive_command must create {mount_path}/wal before copying: {args}"
    )


def _assert_postgres_backup_disabled(docs: list[dict[str, Any]]) -> None:
    """When backup is disabled, no CronJob/PVC and no archive args on postgres."""
    cronjobs = [doc for doc in docs if doc.get("kind") == "CronJob"]
    assert not cronjobs, cronjobs
    backup_pvcs = [
        doc
        for doc in docs
        if doc.get("kind") == "PersistentVolumeClaim"
        and (doc.get("metadata") or {}).get("labels", {}).get(
            "app.kubernetes.io/component",
        )
        == "postgres-backup"
    ]
    assert not backup_pvcs, backup_pvcs
    postgres = [
        doc
        for doc in docs
        if doc.get("kind") == "StatefulSet"
        and (doc.get("metadata") or {}).get("labels", {}).get(
            "app.kubernetes.io/component",
        )
        == "postgres"
    ]
    assert len(postgres) == 1, postgres
    container = postgres[0]["spec"]["template"]["spec"]["containers"][0]
    args = container.get("args") or []
    joined = " ".join(str(item) for item in args)
    assert "archive_mode=on" not in joined, args


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

    missing = sorted(_PLATFORM_IMAGE_COMPONENTS - by_component.keys())
    assert not missing, (
        f"platform workloads missing from the render (hook Jobs "
        f"must render too -- `helm template` emits hooks): {missing}"
    )
    for component in sorted(_PLATFORM_IMAGE_COMPONENTS):
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
    # Story 41.1 added the postgres-backup RWX claim as the fourth.
    assert len(pvcs) == 4, (  # noqa: PLR2004
        f"expected sidecar sqlite PVC + media RWX PVC + redis-broker PVC + "
        f"postgres-backup RWX PVC, got: "
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
def test_mcp_host_deployment_and_service_restricted_v2():
    """AC (spec-mcp-era-isolation): mcp-host Deployment + ClusterIP Service
    satisfy restricted-v2.
    """
    docs = _render(_CORE_CHART)
    deployments = [
        doc
        for doc in docs
        if doc.get("kind") == "Deployment"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == _MCP_HOST_COMPONENT
    ]
    assert len(deployments) == 1, (
        f"expected exactly one mcp-host Deployment, got: "
        f"{[doc['metadata']['name'] for doc in deployments]}"
    )
    by_component = _pod_specs_by_component(docs)
    assert _MCP_HOST_COMPONENT in by_component
    _assert_restricted_v2_pod_spec(
        by_component[_MCP_HOST_COMPONENT],
        where=_MCP_HOST_COMPONENT,
    )
    services = [
        doc
        for doc in docs
        if doc.get("kind") == "Service"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == _MCP_HOST_COMPONENT
    ]
    assert len(services) == 1
    assert services[0]["spec"].get("type") == "ClusterIP"


@requires_helm
def test_platform_pods_wire_mcp_host_sidecar_base_url_to_internal_service():
    """AC: web/worker resolve MCP_HOST_SIDECAR_BASE_URL to the mcp-host Service."""
    docs = _render(_CORE_CHART, release="platform")
    service_name = next(
        doc["metadata"]["name"]
        for doc in docs
        if doc.get("kind") == "Service"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == _MCP_HOST_COMPONENT
    )
    expected_url = f"http://{service_name}:8090"
    by_component = _pod_specs_by_component(docs)
    for component in ("web", "worker"):
        env = _collect_env_by_name(by_component[component])
        mcp_env = env.get("MCP_HOST_SIDECAR_BASE_URL")
        assert mcp_env is not None, f"{component} missing MCP_HOST_SIDECAR_BASE_URL"
        assert mcp_env.get("value") == expected_url
        assert "localhost" not in mcp_env.get("value", "")


@requires_helm
def test_helm_template_fails_when_mcp_host_repository_empty() -> None:
    """CAP-4: empty mcpHost.image.repository fails the render, not :tag."""
    result = subprocess.run(  # noqa: S603
        [
            "helm",
            "template",
            "test-release",
            str(_CORE_CHART),
            "--set-file",
            f"flags.tree={_PLATFORM_DIR / 'config' / 'flags.json'}",
            "--set",
            "mcpHost.image.repository=",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode != 0, result.stdout
    combined = result.stderr + result.stdout
    assert "mcpHost.image.repository is required" in combined
    assert ":<nil>" not in combined
    assert ":latest" not in combined or "platform-mcp-host:" not in combined


def test_mcp_host_values_have_no_enabled_knob() -> None:
    """CAP-4: do not grow mcpHost.enabled — the sidecar is not optional."""
    values_text = (_CORE_CHART / "values.yaml").read_text(encoding="utf-8")
    mcp_block = values_text.split("mcpHost:\n", 1)[1].split("\n\n", 1)[0]
    assert "enabled" not in mcp_block
    for name in ("mcp-host-deployment.yaml", "mcp-host-service.yaml"):
        text = (_CORE_CHART / "templates" / name).read_text(encoding="utf-8")
        assert "mcpHost.enabled" not in text


@requires_helm
def test_redis_uses_existing_secret_password_and_wires_redis_url():
    """AC (Story 12.6): redis Deployment and platform pods consume
    REDIS_PASSWORD from existingSecret; REDIS_URL embeds it via env
    expansion.
    """
    docs = _render(_CORE_CHART, release="platform")
    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    broker_host = next(
        doc["metadata"]["name"]
        for doc in docs
        if doc.get("kind") == "Service"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == "redis-broker"
    )
    cache_host = next(
        doc["metadata"]["name"]
        for doc in docs
        if doc.get("kind") == "Service"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == "redis-cache"
    )
    _assert_redis_uses_password_from_existing_secret(
        docs,
        secret_name=values["existingSecret"],
        password_key=values["redis"]["passwordSecretKey"],
        broker_host=broker_host,
        cache_host=cache_host,
    )


@requires_helm
def test_rendered_manifests_carry_secret_refs_never_secret_values():
    """Story 26.2 / FR-32 / canopy AD-19: helm template must not emit a
    secret *value*. Canary --set-string values are unused chart paths;
    if a template interpolates them the check fails.
    """
    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    _assert_chart_values_hold_no_secret_payloads(values)

    docs = _render(
        _CORE_CHART,
        "--set-string",
        f"postgres.auth.password={_SECRET_VALUE_CANARY}",
        "--set-string",
        f"django.secretKey={_SECRET_VALUE_CANARY}",
        "--set-string",
        f"sidecar.llm.apiKey={_SECRET_VALUE_CANARY}",
        release="platform",
    )
    _assert_no_secret_values_in_docs(docs, canary=_SECRET_VALUE_CANARY)
    _assert_no_vault_csi_or_secrets_sidecar(docs)
    by_component = _pod_specs_by_component(docs)
    assert by_component, "core chart rendered no workloads"
    secret_refs = 0
    for pod_spec in by_component.values():
        for container in _iter_pod_containers(pod_spec):
            for entry in container.get("env") or []:
                if (entry.get("valueFrom") or {}).get("secretKeyRef"):
                    secret_refs += 1
    assert secret_refs, "core chart rendered no secretKeyRef env entries"

    overlay_docs = _render(_OVERLAY_CHART, release="platform")
    _assert_no_secret_values_in_docs(overlay_docs, canary=_SECRET_VALUE_CANARY)
    _assert_no_vault_csi_or_secrets_sidecar(overlay_docs)


@requires_helm
def test_redis_network_policy_restricts_ingress_to_platform_pods():
    """AC (Story 12.6): a NetworkPolicy limits redis ingress to web/worker/
    migrate pods on port 6379.
    """
    docs = _render(_CORE_CHART, release="platform")
    policies = [
        doc
        for doc in docs
        if doc.get("kind") == "NetworkPolicy"
        and str(
            doc["spec"]["podSelector"]
            .get("matchLabels", {})
            .get("app.kubernetes.io/component", ""),
        ).startswith("redis-")
    ]
    components = {
        policy["spec"]["podSelector"]["matchLabels"]["app.kubernetes.io/component"]
        for policy in policies
    }
    assert components == _REDIS_COMPONENTS
    for policy in policies:
        labels = policy["spec"]["podSelector"]["matchLabels"]
        component = labels["app.kubernetes.io/component"]
        _assert_redis_network_policy_restricts_platform_pods(
            docs,
            redis_policy_name=policy["metadata"]["name"],
            redis_component=component,
        )


@requires_helm
def test_mcp_host_network_policy_admits_web_pods_only():
    """AC (Story 42.1): the default render carries a NetworkPolicy that lets
    only ``web`` reach mcp-host:8090, and the Redis policies are unchanged by
    it (they keep their own web/worker/migrate rule on 6379).
    """
    docs = _render(_CORE_CHART, release="platform")
    named = [
        doc["metadata"]["name"]
        for doc in docs
        if doc.get("kind") == "NetworkPolicy"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == _MCP_HOST_COMPONENT
    ]
    assert len(named) == 1, (
        f"the default render must carry exactly one mcp-host NetworkPolicy "
        f"(red-team X-5: without it any pod in the namespace can call the "
        f"sidecar), got {named}"
    )
    _assert_mcp_host_network_policy_admits_web_only(
        docs,
        policy_name=named[0],
        scoping_labels=_release_scoping_labels(docs),
    )

    redis_policies = [
        doc
        for doc in docs
        if doc.get("kind") == "NetworkPolicy"
        and str(
            doc["spec"]["podSelector"]
            .get("matchLabels", {})
            .get("app.kubernetes.io/component", ""),
        ).startswith("redis-")
    ]
    assert len(redis_policies) == len(_REDIS_COMPONENTS), redis_policies
    for policy in redis_policies:
        _assert_redis_network_policy_restricts_platform_pods(
            docs,
            redis_policy_name=policy["metadata"]["name"],
            redis_component=policy["spec"]["podSelector"]["matchLabels"][
                "app.kubernetes.io/component"
            ],
        )


# The scoping labels a synthetic mcp-host policy must carry to be release-scoped
# (the shape `platform.selectorLabels` renders; the real proof DERIVES its own).
_FIXTURE_SCOPING_LABELS = {
    "app.kubernetes.io/name": "platform",
    "app.kubernetes.io/instance": "platform",
}


def _mcp_host_policy_fixture(
    *,
    peer: dict[str, Any] | None = None,
    ports: list[dict[str, Any]] | None = None,
    pod_selector_labels: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """A synthetic, otherwise-conforming mcp-host NetworkPolicy document."""
    return [
        {
            "kind": "NetworkPolicy",
            "metadata": {"name": "platform-mcp-host"},
            "spec": {
                "podSelector": {
                    "matchLabels": pod_selector_labels
                    if pod_selector_labels is not None
                    else {
                        **_FIXTURE_SCOPING_LABELS,
                        "app.kubernetes.io/component": "mcp-host",
                    },
                },
                "policyTypes": ["Ingress"],
                "ingress": [
                    {
                        "from": [
                            peer
                            if peer is not None
                            else {
                                "podSelector": {
                                    "matchLabels": {
                                        **_FIXTURE_SCOPING_LABELS,
                                        "app.kubernetes.io/component": "web",
                                    },
                                },
                            },
                        ],
                        "ports": ports
                        if ports is not None
                        else [{"protocol": "TCP", "port": 8090}],
                    },
                ],
            },
        },
    ]


def _check_mcp_host_policy_fixture(docs: list[dict[str, Any]]) -> None:
    _assert_mcp_host_network_policy_admits_web_only(
        docs,
        policy_name="platform-mcp-host",
        scoping_labels=_FIXTURE_SCOPING_LABELS,
    )


def test_mcp_host_network_policy_fixture_passes_the_check():
    """The fixture itself is conforming -- otherwise every companion below
    could be passing for the wrong reason.
    """
    _check_mcp_host_policy_fixture(_mcp_host_policy_fixture())


def test_mcp_host_network_policy_check_fails_when_a_second_component_is_admitted():
    """A policy that also admits `worker` must raise (guard removed)."""
    contaminated = _mcp_host_policy_fixture(
        peer={
            "podSelector": {
                "matchExpressions": [
                    {
                        "key": "app.kubernetes.io/component",
                        "operator": "In",
                        "values": ["web", "worker"],
                    },
                ],
            },
        },
    )

    with pytest.raises(AssertionError, match="matchLabels only"):
        _check_mcp_host_policy_fixture(contaminated)


def test_mcp_host_network_policy_check_fails_when_the_policy_is_missing():
    """No mcp-host policy at all must raise, not pass vacuously."""
    with pytest.raises(AssertionError, match="exactly one mcp-host NetworkPolicy"):
        _assert_mcp_host_network_policy_admits_web_only(
            [{"kind": "NetworkPolicy", "metadata": {"name": "platform-redis-cache"}}],
            policy_name="platform-mcp-host",
            scoping_labels=_FIXTURE_SCOPING_LABELS,
        )


def test_mcp_host_network_policy_check_fails_on_a_wide_open_port():
    """A rule that opens a port other than 8090 must raise."""
    contaminated = _mcp_host_policy_fixture(ports=[])

    with pytest.raises(AssertionError, match="TCP/8090 only"):
        _check_mcp_host_policy_fixture(contaminated)


def test_mcp_host_network_policy_check_fails_on_a_namespace_selector_peer():
    """A namespaceSelector beside the podSelector admits web-labelled pods in
    ANY namespace -- the X-5 exposure -- and must raise (guard removed).
    """
    contaminated = _mcp_host_policy_fixture(
        peer={
            "podSelector": {
                "matchLabels": {
                    **_FIXTURE_SCOPING_LABELS,
                    "app.kubernetes.io/component": "web",
                },
            },
            "namespaceSelector": {},
        },
    )

    with pytest.raises(AssertionError, match="podSelector and nothing else"):
        _check_mcp_host_policy_fixture(contaminated)


def test_mcp_host_network_policy_check_fails_on_an_ip_block_peer():
    """An ipBlock beside the podSelector admits raw CIDRs; must raise."""
    contaminated = _mcp_host_policy_fixture(
        peer={
            "podSelector": {
                "matchLabels": {
                    **_FIXTURE_SCOPING_LABELS,
                    "app.kubernetes.io/component": "web",
                },
            },
            "ipBlock": {"cidr": "0.0.0.0/0"},
        },
    )

    with pytest.raises(AssertionError, match="podSelector and nothing else"):
        _check_mcp_host_policy_fixture(contaminated)


def test_mcp_host_network_policy_check_fails_when_the_ingress_peer_loses_scoping():
    """Dropping the selectorLabels include from the ingress selector widens the
    rule to any pod in the namespace labelled `component: web`; must raise.
    """
    contaminated = _mcp_host_policy_fixture(
        peer={
            "podSelector": {
                "matchLabels": {"app.kubernetes.io/component": "web"},
            },
        },
    )

    with pytest.raises(AssertionError, match="not release-scoped"):
        _check_mcp_host_policy_fixture(contaminated)


def test_mcp_host_network_policy_check_fails_when_the_policy_selector_loses_scoping():
    """Dropping the selectorLabels include from the policy's own podSelector
    makes it govern another release's mcp-host too; must raise.
    """
    contaminated = _mcp_host_policy_fixture(
        pod_selector_labels={"app.kubernetes.io/component": "mcp-host"},
    )

    with pytest.raises(AssertionError, match="not release-scoped"):
        _check_mcp_host_policy_fixture(contaminated)


@requires_helm
def test_redis_cache_persistence_remains_empty_dir():
    """AC (Story 12.6 / 40.2): redis-cache stays ephemeral -- emptyDir only."""
    docs = _render(_CORE_CHART)
    _assert_redis_cache_persistence_is_empty_dir(docs)


@requires_helm
def test_redis_broker_persistence_is_pvc_with_aof():
    """AC (Story 40.2): redis-broker mounts RWO PVC and enables AOF."""
    docs = _render(_CORE_CHART, release="platform")
    _assert_redis_broker_persistence_is_pvc_with_aof(docs)


@requires_helm
def test_postgres_backup_cronjob_and_archive_mode():
    """AC (Story 41.1): default render ships backup CronJob + WAL archive."""
    docs = _render(_CORE_CHART, release="platform")
    _assert_postgres_backup_cronjob_present(docs)


@requires_helm
def test_postgres_backup_disabled_omits_cronjob():
    """AC (Story 41.1): disabling backup removes CronJob and archive args."""
    docs = _render(
        _CORE_CHART,
        "--set",
        "postgres.backup.enabled=false",
        release="platform",
    )
    _assert_postgres_backup_disabled(docs)


@requires_helm
def test_ocp_overlay_postgres_backup_cronjob_restricted_v2():
    """AC (Story 41.1): OCP overlay keeps restricted-v2 on backup CronJob."""
    docs = _render(
        _CORE_CHART,
        "-f",
        str(_CORE_OVERRIDES),
        release="platform",
    )
    _assert_postgres_backup_cronjob_present(docs)
    by_component = _pod_specs_by_component(docs)
    assert "postgres-backup" in by_component
    _assert_restricted_v2_pod_spec(
        by_component["postgres-backup"],
        where="postgres-backup",
    )


@requires_helm
def test_redis_broker_maxmemory_must_be_below_memory_limit():
    """AC (Story 40.2): maxmemory >= limit fails helm template naming the path."""
    with pytest.raises(AssertionError, match="redis.broker.maxmemory"):
        _render(
            _CORE_CHART,
            "--set",
            "redis.broker.maxmemory=768Mi",
            "--set",
            "redis.broker.resources.limits.memory=768Mi",
        )


@requires_helm
def test_redis_broker_maxmemory_is_required():
    """AC (Story 40.2): empty redis.broker.maxmemory fails the render."""
    with pytest.raises(AssertionError, match="redis.broker.maxmemory is required"):
        _render(_CORE_CHART, "--set", "redis.broker.maxmemory=")


@requires_helm
def test_redis_broker_memory_limit_is_required():
    """AC (Story 40.2): empty redis.broker.resources.limits.memory fails the render."""
    with pytest.raises(AssertionError, match="redis.broker.resources.limits.memory is required"):
        _render(
            _CORE_CHART,
            "--set",
            "redis.broker.resources.limits.memory=",
        )


@requires_helm
def test_duckdb_boundary_platform_readers_do_not_mount_plane_file():
    """AC (Story 41.2): web (Vizro/BSL) pod does not mount ``atlas.duckdb``."""
    docs = _render(_CORE_CHART, release="platform")
    _assert_query_plane_readers_do_not_mount_duckdb_file(docs)


@requires_helm
def test_duckdb_boundary_plane_pvc_must_be_read_write_once():
    """AC (Story 41.2): a plane PVC rendered RWX fails the invariant."""
    docs = _render(_CORE_CHART, release="platform")
    _assert_query_plane_pvcs_are_read_write_once(docs)


def test_duckdb_boundary_plane_pvc_rwx_is_rejected():
    """Guard (Story 41.2): ReadWriteMany on a plane PVC must raise."""
    violating = [
        {
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": "platform-query-plane",
                "labels": {_PLANE_PVC_LABEL: "true"},
            },
            "spec": {"accessModes": ["ReadWriteMany"]},
        },
    ]
    with pytest.raises(AssertionError, match="ReadWriteOnce"):
        _assert_query_plane_pvcs_are_read_write_once(violating)


def test_duckdb_boundary_reader_mount_is_rejected():
    """Guard (Story 41.2): a web pod mounting ``atlas.duckdb`` must raise."""
    violating = [
        {
            "kind": "Deployment",
            "metadata": {"name": "platform-web"},
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {"app.kubernetes.io/component": "web"},
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "web",
                                "volumeMounts": [
                                    {"name": "plane", "mountPath": "/data/atlas.duckdb"},
                                ],
                            },
                        ],
                    },
                },
            },
        },
        {
            "kind": "Deployment",
            "metadata": {"name": "platform-worker"},
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {"app.kubernetes.io/component": "worker"},
                    },
                    "spec": {"containers": [{"name": "worker"}]},
                },
            },
        },
    ]
    with pytest.raises(AssertionError, match="query-plane file"):
        _assert_query_plane_readers_do_not_mount_duckdb_file(violating)


@requires_helm
def test_media_pvc_is_readwritemany_and_mounted_on_web_and_worker():
    """AC (Story 20.2): RWX media PVC; replica A/B share the mount."""
    docs = _render(_CORE_CHART, release="platform")
    media_pvcs = [
        doc
        for doc in docs
        if doc.get("kind") == "PersistentVolumeClaim"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == "media"
    ]
    assert len(media_pvcs) == 1, media_pvcs
    assert media_pvcs[0]["spec"]["accessModes"] == ["ReadWriteMany"]
    claim = media_pvcs[0]["metadata"]["name"]
    by_component = _pod_specs_by_component(docs)
    for component in ("web", "worker"):
        mounts = by_component[component]["containers"][0].get("volumeMounts") or []
        volumes = by_component[component].get("volumes") or []
        assert any(m.get("name") == "wagtail-media" for m in mounts), (
            f"{component} missing wagtail-media volumeMount"
        )
        pvc_vol = next(v for v in volumes if v.get("name") == "wagtail-media")
        assert pvc_vol["persistentVolumeClaim"]["claimName"] == claim
    migrate_vols = by_component["migrate"].get("volumes") or []
    assert not any(v.get("name") == "wagtail-media" for v in migrate_vols)


@requires_helm
def test_worker_is_celery_deployment_not_a_second_public_asgi():
    """AC (Story 20.2): independent scale of work is the Celery worker."""
    docs = _render(_CORE_CHART, release="platform")
    by_component = _pod_specs_by_component(docs)
    worker = by_component["worker"]["containers"][0]
    # Story 42.4: the general pool consumes values `worker.queues`, in order.
    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    expected_queues = ",".join(values["worker"]["queues"])
    assert worker.get("args") == [*_CELERY_WORKER_ARGS, "-Q", expected_queues]
    assert not worker.get("ports"), worker.get("ports")
    worker_services = [
        doc
        for doc in docs
        if doc.get("kind") == "Service"
        and doc["metadata"].get("labels", {}).get("app.kubernetes.io/component")
        == "worker"
    ]
    assert worker_services == []
    ingresses = [doc for doc in docs if doc.get("kind") == "Ingress"]
    for ingress in ingresses:
        blob = str(ingress).lower()
        assert "worker" not in blob or "celery" in blob


@requires_helm
def test_chart_templates_forbid_minio_s3_and_elasticsearch():
    """AC: MinIO/S3/Elasticsearch are review-blocking findings."""
    rendered = _helm("template", "platform", str(_CORE_CHART)).lower()
    forbidden = (
        "image: minio",
        "elasticsearch",
        "s3.amazonaws",
        "storages.backends.s3",
    )
    for needle in forbidden:
        assert needle not in rendered, f"forbidden infra {needle!r} in helm render"


@requires_helm
def test_namespace_inventory_includes_postgres_redis_platform_and_sidecar():
    """AC (AD-1): across ALL rendered workload pod specs, the image set
    reduces to exactly five -- postgres, redis, platform, sidecar, and mcp-host.
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
    for component in ("postgres", "redis-cache", "redis-broker"):
        assert component in by_component, (
            f"{component} workload missing from the OCP-overridden render -- "
            f"the UID check below would pass vacuously"
        )
    _assert_no_fixed_uid_keys(docs)
    for component in sorted(_PLATFORM_IMAGE_COMPONENTS):
        _assert_restricted_v2_pod_spec(by_component[component], where=component)


@requires_helm
def test_liquibase_job_then_fake_migrate():
    """AC (Story 27.2): Liquibase Job weight -1 then migrate --fake."""
    docs = _render(_CORE_CHART, release="platform")
    _assert_liquibase_then_fake_migrate_jobs(docs)


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
            "name": "REDIS_BROKER_URL",
            "value": "redis://:$(REDIS_PASSWORD)@platform-redis-broker:6379/0",
        },
        {
            "name": "REDIS_CACHE_URL",
            "value": "redis://:$(REDIS_PASSWORD)@platform-redis-cache:6379/0",
        },
        {
            "name": "REDIS_URL",
            "value": "redis://:$(REDIS_PASSWORD)@platform-redis-broker:6379/0",
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
                "name": "platform-redis-broker",
                "labels": {"app.kubernetes.io/component": "redis-broker"},
            },
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {"app.kubernetes.io/component": "redis-broker"},
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
        {
            "kind": "Deployment",
            "metadata": {
                "name": "platform-redis-cache",
                "labels": {"app.kubernetes.io/component": "redis-cache"},
            },
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {"app.kubernetes.io/component": "redis-cache"},
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "redis",
                                "image": "redis:7",
                                "env": [platform_env[0]],
                                "command": [
                                    "redis-server",
                                    "--requirepass",
                                    "$(REDIS_PASSWORD)",
                                    "--maxmemory",
                                    "64mb",
                                    "--maxmemory-policy",
                                    "allkeys-lru",
                                ],
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
            broker_host="platform-redis-broker",
            cache_host="platform-redis-cache",
        )


def test_redis_network_policy_check_fails_when_sidecar_is_allowed():
    """A NetworkPolicy that admits the sidecar component must raise."""
    contaminated_policy = [
        {
            "kind": "NetworkPolicy",
            "metadata": {"name": "platform-redis"},
            "spec": {
                "podSelector": {
                    "matchLabels": {"app.kubernetes.io/component": "redis-broker"},
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
            redis_component="redis-broker",
        )


def test_redis_cache_empty_dir_check_fails_when_a_pvc_volume_is_present():
    """A redis-cache Deployment with a PVC-backed volume must raise."""
    contaminated_docs = [
        {
            "kind": "Deployment",
            "metadata": {
                "name": "platform-redis-cache",
                "labels": {"app.kubernetes.io/component": "redis-cache"},
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
        _assert_redis_cache_persistence_is_empty_dir(contaminated_docs)


def _synthetic_workload(
    component: str,
    *,
    env: list[dict[str, Any]] | None = None,
    annotations: dict[str, str] | None = None,
    volumes: list[dict[str, Any]] | None = None,
    extra_containers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    containers: list[dict[str, Any]] = [
        {"name": component, "image": "platform:latest", "env": env or []},
    ]
    containers.extend(extra_containers or [])
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
                    "annotations": annotations or {},
                },
                "spec": {
                    "containers": containers,
                    "volumes": volumes or [],
                },
            },
        },
    }


def test_secret_value_check_fails_on_inline_env_value():
    """A secret-named env var with `value:` (not secretKeyRef) must raise."""
    docs = [
        _synthetic_workload(
            "web",
            env=[{"name": "DJANGO_SECRET_KEY", "value": "hunter2-not-a-ref"}],
        ),
    ]
    with pytest.raises(AssertionError, match="inline value"):
        _assert_no_secret_values_in_docs(docs)


def test_secret_value_check_fails_when_canary_appears():
    """An injected secret canary anywhere in the render must raise."""
    docs = [
        _synthetic_workload(
            "web",
            env=[{"name": "DJANGO_ALLOWED_HOSTS", "value": _SECRET_VALUE_CANARY}],
        ),
    ]
    with pytest.raises(AssertionError, match="canary"):
        _assert_no_secret_values_in_docs(docs, canary=_SECRET_VALUE_CANARY)


def test_secret_value_check_fails_on_a_rendered_secret_object():
    """A chart-emitted Secret would put values in git -- must raise."""
    docs = [
        _synthetic_workload("web"),
        {
            "kind": "Secret",
            "metadata": {"name": "platform-secrets"},
            "stringData": {"DJANGO_SECRET_KEY": "leaked"},
        },
    ]
    with pytest.raises(AssertionError, match="Secret objects"):
        _assert_no_secret_values_in_docs(docs)


def test_vault_csi_check_fails_on_injector_annotation():
    docs = [
        _synthetic_workload(
            "web",
            annotations={"vault.hashicorp.com/agent-inject": "true"},
        ),
    ]
    with pytest.raises(AssertionError, match="vault/CSI"):
        _assert_no_vault_csi_or_secrets_sidecar(docs)


def test_vault_csi_check_fails_on_secrets_store_volume():
    docs = [
        _synthetic_workload(
            "web",
            volumes=[
                {
                    "name": "secrets-store",
                    "csi": {"driver": "secrets-store.csi.k8s.io"},
                },
            ],
        ),
    ]
    with pytest.raises(AssertionError, match="secrets CSI"):
        _assert_no_vault_csi_or_secrets_sidecar(docs)


def test_vault_csi_check_fails_on_vault_agent_sidecar():
    docs = [
        _synthetic_workload(
            "web",
            extra_containers=[
                {"name": "vault-agent", "image": "hashicorp/vault:1.15"},
            ],
        ),
    ]
    with pytest.raises(AssertionError, match="secrets sidecar"):
        _assert_no_vault_csi_or_secrets_sidecar(docs)


def test_chart_values_check_fails_on_a_password_payload():
    with pytest.raises(AssertionError, match="secret payload"):
        _assert_chart_values_hold_no_secret_payloads(
            {"postgres": {"auth": {"password": "supersecret"}}},
        )


def test_secrets_http_api_check_fails_on_hvac_import(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "vault_client.py").write_text(
        "import hvac\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="secrets HTTP API"):
        _assert_app_does_not_call_secrets_http_api(tmp_path)


def test_app_does_not_call_secrets_http_api():
    _assert_app_does_not_call_secrets_http_api(_PLATFORM_DIR)


def _synthetic_hook_job(
    component: str,
    *,
    weight: str,
    args: list[str],
    env: list[dict[str, Any]] | None = None,
    init_containers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "Job",
        "metadata": {
            "name": f"platform-{component}",
            "labels": {"app.kubernetes.io/component": component},
            "annotations": {
                "helm.sh/hook": "post-install,pre-upgrade",
                "helm.sh/hook-weight": weight,
            },
        },
        "spec": {
            "template": {
                "metadata": {
                    "labels": {"app.kubernetes.io/component": component},
                },
                "spec": {
                    "initContainers": init_containers or [],
                    "containers": [
                        {
                            "name": component,
                            "image": "platform:latest",
                            "args": args,
                            "env": env or [],
                        },
                    ],
                },
            },
        },
    }


def _governed_ddl_docs() -> list[dict[str, Any]]:
    return [
        _synthetic_workload("web"),
        _synthetic_hook_job(
            "liquibase",
            weight="-1",
            args=["python", "db/liquibase_update.py"],
            env=[
                {
                    "name": "MIGRATION_DATABASE_URL",
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": "platform-secrets",
                            "key": "MIGRATION_DATABASE_URL",
                        },
                    },
                },
            ],
        ),
        _synthetic_hook_job(
            "migrate",
            weight="0",
            args=["python", "manage.py", "migrate", "--fake", "--noinput"],
            env=[
                {
                    "name": "DATABASE_URL",
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": "platform-secrets",
                            "key": "DATABASE_URL",
                        },
                    },
                },
            ],
        ),
    ]


def test_liquibase_job_check_fails_when_weight_is_not_minus_one():
    docs = _governed_ddl_docs()
    docs[1]["metadata"]["annotations"]["helm.sh/hook-weight"] = "0"
    with pytest.raises(AssertionError, match="helm.sh/hook-weight"):
        _assert_liquibase_then_fake_migrate_jobs(docs)


def test_liquibase_job_check_fails_when_migrate_drops_fake():
    docs = _governed_ddl_docs()
    docs[2]["spec"]["template"]["spec"]["containers"][0]["args"] = [
        "python",
        "manage.py",
        "migrate",
        "--noinput",
    ]
    with pytest.raises(AssertionError, match="--fake"):
        _assert_liquibase_then_fake_migrate_jobs(docs)


def test_liquibase_job_check_fails_on_init_container():
    docs = _governed_ddl_docs()
    docs[1]["spec"]["template"]["spec"]["initContainers"] = [
        {"name": "wait", "image": "platform:latest"},
    ]
    with pytest.raises(AssertionError, match="initContainer"):
        _assert_liquibase_then_fake_migrate_jobs(docs)


def test_postgres_backup_check_fails_when_archive_mode_missing():
    docs = [
        {
            "kind": "CronJob",
            "metadata": {
                "name": "platform-postgres-backup",
                "labels": {"app.kubernetes.io/component": "postgres-backup"},
            },
            "spec": {
                "schedule": "0 2 * * *",
                "jobTemplate": {"spec": {"template": {"metadata": {"labels": {}}, "spec": {}}}},
            },
        },
        {
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": "platform-postgres-backup",
                "labels": {"app.kubernetes.io/component": "postgres-backup"},
            },
            "spec": {"accessModes": ["ReadWriteMany"]},
        },
        {
            "kind": "StatefulSet",
            "metadata": {
                "name": "platform-postgres",
                "labels": {"app.kubernetes.io/component": "postgres"},
            },
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "postgres",
                                "image": "postgres:17",
                                "args": ["postgres"],
                                "volumeMounts": [{"name": "backup", "mountPath": "/backup"}],
                            },
                        ],
                    },
                },
            },
        },
    ]
    with pytest.raises(AssertionError, match="archive_mode"):
        _assert_postgres_backup_cronjob_present(docs)



# ---------------------------------------------------------------------------
# Story 42.3 / canopy AD-8 -- one consume_events Deployment per subscribing
# station, on the platform image, with the same contexts as worker
# ---------------------------------------------------------------------------


def _consume_events_pod_specs(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Station -> pod spec for every ``consume-events-<station>`` Deployment.
    Only Deployments count: a consumer shipped as a Job or CronJob would be
    a one-shot, not a listener (A-1)."""
    out: dict[str, dict[str, Any]] = {}
    for doc in docs:
        if doc.get("kind") != "Deployment":
            continue
        template = _pod_template(doc)
        labels = (template.get("metadata") or {}).get("labels") or {}
        component = labels.get("app.kubernetes.io/component") or ""
        if not component.startswith(_CONSUME_EVENTS_PREFIX):
            continue
        station = component[len(_CONSUME_EVENTS_PREFIX) :]
        assert station not in out, f"duplicate consume-events Deployment for {station!r}"
        out[station] = template["spec"]
    return out


def _assert_consume_events_deployments_mirror_worker(
    docs: list[dict[str, Any]],
    stations: list[str],
) -> None:
    """AC: a `consume-events` Deployment exists for each station in
    `events.consumers` -- no more, no fewer -- on the platform image, running
    `manage.py consume_events --station <name>`, with the worker's env,
    security contexts, service account and volumes."""
    by_component = _pod_specs_by_component(docs)
    assert "worker" in by_component, "worker Deployment missing from render"
    worker = by_component["worker"]
    worker_container = worker["containers"][0]
    rendered = _consume_events_pod_specs(docs)
    assert set(rendered) == set(stations), (
        f"consume-events Deployments {sorted(rendered)} do not match "
        f"events.consumers {sorted(stations)}"
    )
    for station, spec in sorted(rendered.items()):
        where = f"{_CONSUME_EVENTS_PREFIX}{station}"
        containers = spec.get("containers") or []
        assert len(containers) == 1, f"{where}: expected one container, got {len(containers)}"
        container = containers[0]
        assert container.get("args") == [*_CONSUME_EVENTS_ARGS, station], (
            f"{where}: args must run consume_events for {station!r}, got {container.get('args')!r}"
        )
        assert container.get("image") == worker_container.get("image"), (
            f"{where}: image {container.get('image')!r} != worker {worker_container.get('image')!r}"
        )
        assert container.get("env") == worker_container.get("env"), (
            f"{where}: env differs from worker"
        )
        assert container.get("securityContext") == worker_container.get("securityContext"), (
            f"{where}: container securityContext differs from worker"
        )
        assert container.get("volumeMounts") == worker_container.get("volumeMounts"), (
            f"{where}: volumeMounts differ from worker"
        )
        assert spec.get("securityContext") == worker.get("securityContext"), (
            f"{where}: pod securityContext differs from worker"
        )
        assert spec.get("serviceAccountName") == worker.get("serviceAccountName"), (
            f"{where}: serviceAccountName differs from worker"
        )
        assert spec.get("volumes") == worker.get("volumes"), f"{where}: volumes differ from worker"
        assert int(spec.get("terminationGracePeriodSeconds") or 0) > 0, (
            f"{where}: needs a terminationGracePeriodSeconds drain budget"
        )


def _synthetic_platform_deployment(
    component: str,
    args: list[str],
    env: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    env = env if env is not None else [{"name": "REDIS_URL", "value": "redis://broker"}]
    return {
        "kind": "Deployment",
        "metadata": {"name": f"test-{component}"},
        "spec": {
            "template": {
                "metadata": {"labels": {"app.kubernetes.io/component": component}},
                "spec": {
                    "serviceAccountName": "test-release-platform",
                    "securityContext": {"runAsNonRoot": True},
                    "terminationGracePeriodSeconds": 310,
                    "containers": [
                        {
                            "name": component,
                            "image": "platform:latest",
                            "args": args,
                            "env": env,
                            "securityContext": {"allowPrivilegeEscalation": False},
                            "volumeMounts": [{"name": "flags", "mountPath": "/etc/pyforge"}],
                        },
                    ],
                    "volumes": [{"name": "flags", "configMap": {"name": "flags"}}],
                },
            },
        },
    }


@requires_helm
def test_consume_events_deployment_per_configured_station():
    """AC (Story 42.3): `helm template` renders a consume-events Deployment
    for each station in `events.consumers`, on the platform image, with the
    same contexts as worker. The station list is DERIVED from values.yaml."""
    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    stations = list(values["events"]["consumers"])
    assert stations, "values.yaml must ship at least one event consumer (A-1)"
    assert set(stations) == set(_DEFAULT_EVENT_CONSUMERS), (
        "update _DEFAULT_EVENT_CONSUMERS when values.yaml's events.consumers changes"
    )
    docs = _render(_CORE_CHART)
    _assert_consume_events_deployments_mirror_worker(docs, stations)


@requires_helm
def test_consume_events_follows_values_and_refuses_non_station():
    """Overriding `events.consumers` changes exactly which Deployments render;
    a name that is not a station token fails the render (consumer group =
    station token, AD-8)."""
    docs = _render(_CORE_CHART, "--set", "events.consumers={warden}")
    _assert_consume_events_deployments_mirror_worker(docs, ["warden"])
    with pytest.raises(AssertionError, match="not a station token"):
        _render(_CORE_CHART, "--set", "events.consumers={nope}")
    # Review P12: a repeated station renders ONE Deployment (two with one
    # name would be a helm apply error), and the NetworkPolicy lists it once.
    docs = _render(_CORE_CHART, "--set", "events.consumers={doctor,doctor}")
    _assert_consume_events_deployments_mirror_worker(docs, ["doctor"])
    policies = [doc for doc in docs if doc.get("kind") == "NetworkPolicy"]
    for policy in policies:
        for rule in policy["spec"].get("ingress") or []:
            for peer in rule.get("from") or []:
                for expr in (peer.get("podSelector") or {}).get("matchExpressions") or []:
                    values = expr.get("values") or []
                    assert len(values) == len(set(values)), (
                        f"{policy['metadata']['name']}: duplicate peers {values!r}"
                    )


def test_values_event_consumers_match_subscriptions():
    """Review P7 (ungated, no helm): the stations the chart deploys consumers
    for are exactly the stations that subscribe to something. A consumer for
    a station with no subscriptions would ACK the whole stream while looking
    healthy; a subscribing station with no consumer is a producer with no
    listener (A-1)."""
    from django_pyforge.events import SUBSCRIPTIONS  # noqa: PLC0415

    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    consumers = list(values["events"]["consumers"])
    assert len(consumers) == len(set(consumers)), f"duplicate stations: {consumers}"
    assert set(consumers) == set(SUBSCRIPTIONS), (
        f"values.yaml events.consumers {sorted(consumers)} must equal the "
        f"subscribing stations {sorted(SUBSCRIPTIONS)}"
    )
    for station, types in SUBSCRIPTIONS.items():
        assert types, f"{station} is listed as a consumer but subscribes to nothing"


def test_consume_events_guard_rejects_drift_from_worker():
    """Guard-removed companion (ungated): synthetic docs prove the helper
    raises when a consumer is missing, extra, runs the wrong args, or drifts
    from the worker's env."""
    worker = _synthetic_platform_deployment("worker", ["celery", "-A", "config", "worker"])
    good_args = [*_CONSUME_EVENTS_ARGS, "doctor"]
    doctor = _synthetic_platform_deployment("consume-events-doctor", good_args)
    _assert_consume_events_deployments_mirror_worker([worker, doctor], ["doctor"])

    with pytest.raises(AssertionError, match="do not match"):
        _assert_consume_events_deployments_mirror_worker([worker, doctor], ["doctor", "mason"])
    with pytest.raises(AssertionError, match="do not match"):
        _assert_consume_events_deployments_mirror_worker([worker, doctor], [])
    wrong_args = _synthetic_platform_deployment("consume-events-doctor", ["celery", "worker"])
    with pytest.raises(AssertionError, match="args must run consume_events"):
        _assert_consume_events_deployments_mirror_worker([worker, wrong_args], ["doctor"])
    drifted_env = _synthetic_platform_deployment(
        "consume-events-doctor",
        good_args,
        env=[{"name": "REDIS_URL", "value": "redis://elsewhere"}],
    )
    with pytest.raises(AssertionError, match="env differs"):
        _assert_consume_events_deployments_mirror_worker([worker, drifted_env], ["doctor"])
    with pytest.raises(AssertionError, match="worker Deployment missing"):
        _assert_consume_events_deployments_mirror_worker([doctor], ["doctor"])


# ---------------------------------------------------------------------------
# Story 42.4 -- the builds pool and the beat scheduler (red-team S-2 / T-6, R-10)
# ---------------------------------------------------------------------------


def _deployment_by_component(docs: list[dict[str, Any]], component: str) -> dict[str, Any]:
    """The one Deployment whose pod template carries ``component``. A pool
    shipped as a Job/CronJob would be a one-shot, not a consumer."""
    found = [
        doc
        for doc in docs
        if doc.get("kind") == "Deployment"
        and ((_pod_template(doc).get("metadata") or {}).get("labels") or {}).get(
            "app.kubernetes.io/component",
        )
        == component
    ]
    assert len(found) == 1, f"expected exactly one {component!r} Deployment, got {len(found)}"
    return found[0]


def _assert_pod_mirrors_worker(
    spec: dict[str, Any],
    worker: dict[str, Any],
    where: str,
) -> dict[str, Any]:
    """Same image, env, security contexts, service account and volumes as the
    Celery worker -- only the args may differ. Returns the one container."""
    worker_container = worker["containers"][0]
    containers = spec.get("containers") or []
    assert len(containers) == 1, f"{where}: expected one container, got {len(containers)}"
    container = containers[0]
    assert container.get("image") == worker_container.get("image"), (
        f"{where}: image {container.get('image')!r} != worker {worker_container.get('image')!r}"
    )
    assert container.get("env") == worker_container.get("env"), f"{where}: env differs from worker"
    assert container.get("securityContext") == worker_container.get("securityContext"), (
        f"{where}: container securityContext differs from worker"
    )
    assert container.get("volumeMounts") == worker_container.get("volumeMounts"), (
        f"{where}: volumeMounts differ from worker"
    )
    assert spec.get("securityContext") == worker.get("securityContext"), (
        f"{where}: pod securityContext differs from worker"
    )
    assert spec.get("serviceAccountName") == worker.get("serviceAccountName"), (
        f"{where}: serviceAccountName differs from worker"
    )
    assert spec.get("volumes") == worker.get("volumes"), f"{where}: volumes differ from worker"
    return container


def _env_value(container: dict[str, Any], name: str) -> str | None:
    for item in container.get("env") or []:
        if item.get("name") == name:
            return item.get("value")
    return None


def _assert_builds_pool(
    docs: list[dict[str, Any]],
    *,
    limit: int,
    soft_limit: int,
    slack: int,
    worker_queues: list[str],
) -> None:
    """AC (Story 42.4): `worker` consumes `worker.queues` (never `builds`);
    a separate `worker-builds` Deployment consumes `builds` with an
    hours-scale `--time-limit`, mirrors the worker, exports the same limit
    as CELERY_BUILDS_TASK_TIME_LIMIT on both pods, and has
    terminationGracePeriodSeconds == limit + slack."""
    by_component = _pod_specs_by_component(docs)
    assert "worker" in by_component, "worker Deployment missing from render"
    worker = by_component["worker"]
    worker_args = worker["containers"][0].get("args") or []
    assert worker_args == [*_CELERY_WORKER_ARGS, "-Q", ",".join(worker_queues)], (
        f"worker args {worker_args!r} do not consume worker.queues {worker_queues!r}"
    )
    consumed = set(",".join(worker_args[-1:]).split(","))
    assert "builds" not in consumed, "the general worker must not consume builds (300s limit)"
    assert "default" in consumed and "priority" in consumed, consumed

    assert _WORKER_BUILDS_COMPONENT in by_component, "worker-builds Deployment missing from render"
    spec = by_component[_WORKER_BUILDS_COMPONENT]
    container = _assert_pod_mirrors_worker(spec, worker, where=_WORKER_BUILDS_COMPONENT)
    expected_args = [
        *_CELERY_WORKER_ARGS,
        "-Q",
        "builds",
        "--time-limit",
        str(limit),
        "--soft-time-limit",
        str(soft_limit),
    ]
    assert container.get("args") == expected_args, (
        f"worker-builds args must consume builds with the hours-scale limit; "
        f"got {container.get('args')!r}"
    )
    assert limit > 300, f"builds limit {limit} is the 300s pool by another name"  # noqa: PLR2004
    assert 0 < soft_limit < limit, (soft_limit, limit)
    grace = int(spec.get("terminationGracePeriodSeconds") or 0)
    assert grace == limit + slack, (
        f"worker-builds terminationGracePeriodSeconds {grace} != limit {limit} + slack {slack}"
    )
    for component in ("worker", _WORKER_BUILDS_COMPONENT):
        exported = _env_value(by_component[component]["containers"][0], _BUILDS_LIMIT_ENV)
        assert exported == str(limit), (
            f"{component}: {_BUILDS_LIMIT_ENV} is {exported!r}, expected {limit!r}"
        )


def _assert_beat_is_a_singleton_scheduler(docs: list[dict[str, Any]]) -> None:
    """One `beat` Deployment: exactly one replica, Recreate, `celery beat`,
    mirroring the worker."""
    deployment = _deployment_by_component(docs, _BEAT_COMPONENT)
    assert deployment["spec"].get("replicas") == 1, "beat must be a single replica"
    assert (deployment["spec"].get("strategy") or {}).get("type") == "Recreate", (
        "beat rollouts must never overlap two schedulers"
    )
    by_component = _pod_specs_by_component(docs)
    container = _assert_pod_mirrors_worker(
        by_component[_BEAT_COMPONENT],
        by_component["worker"],
        where=_BEAT_COMPONENT,
    )
    assert container.get("args") == list(_BEAT_ARGS), container.get("args")


def _builds_values(values: dict[str, Any]) -> dict[str, int]:
    builds = values["worker"]["builds"]
    return {
        "limit": int(builds["taskTimeLimitSeconds"]),
        "soft_limit": int(builds["softTimeLimitSeconds"]),
        "slack": int(builds["drainSlackSeconds"]),
    }


@requires_helm
def test_builds_pool_is_a_separate_deployment_with_an_hours_scale_limit():
    """AC (Story 42.4): rendered with default values, `worker` consumes the
    default + per-station queues and `worker-builds` consumes `builds` with
    terminationGracePeriodSeconds = builds limit + slack."""
    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    docs = _render(_CORE_CHART)
    _assert_builds_pool(
        docs,
        worker_queues=list(values["worker"]["queues"]),
        **_builds_values(values),
    )
    assert _builds_values(values)["limit"] >= 3600, "the builds pool is hours-scale"  # noqa: PLR2004


@requires_helm
def test_builds_pool_grace_derives_from_the_limit():
    """Raising the limit moves the args, the exported env AND the drain
    budget together -- the grace period is derived, not a second literal."""
    yaml = _import_yaml()
    values = yaml.safe_load((_CORE_CHART / "values.yaml").read_text())
    docs = _render(
        _CORE_CHART,
        "--set",
        "worker.builds.taskTimeLimitSeconds=7200",
        "--set",
        "worker.builds.softTimeLimitSeconds=7000",
        "--set",
        "worker.builds.drainSlackSeconds=100",
    )
    _assert_builds_pool(
        docs,
        limit=7200,
        soft_limit=7000,
        slack=100,
        worker_queues=list(values["worker"]["queues"]),
    )


@requires_helm
def test_chart_refuses_a_build_on_the_general_pool():
    """Never-clauses: no builds pod with the 300s limit; no build on the
    general worker; no soft limit at or past the hard one."""
    with pytest.raises(AssertionError, match="must not include"):
        _render(_CORE_CHART, "--set", "worker.queues={builds}")
    with pytest.raises(AssertionError, match="must exceed 300"):
        _render(_CORE_CHART, "--set", "worker.builds.taskTimeLimitSeconds=300")
    with pytest.raises(AssertionError, match="softTimeLimitSeconds must be between"):
        _render(_CORE_CHART, "--set", "worker.builds.softTimeLimitSeconds=14400")
    with pytest.raises(AssertionError, match="blank entry"):
        _render(_CORE_CHART, "--set", "worker.queues={}")


@requires_helm
def test_beat_is_a_single_replica_scheduler_on_the_platform_image():
    docs = _render(_CORE_CHART)
    _assert_beat_is_a_singleton_scheduler(docs)


def _synthetic_builds_pool(
    *,
    args: list[str] | None = None,
    grace: int = 14460,
    env: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    default_env = [
        {"name": "REDIS_URL", "value": "redis://broker"},
        {"name": _BUILDS_LIMIT_ENV, "value": "14400"},
    ]
    doc = _synthetic_platform_deployment(
        _WORKER_BUILDS_COMPONENT,
        args
        if args is not None
        else [*_CELERY_WORKER_ARGS, "-Q", "builds", "--time-limit", "14400", "--soft-time-limit", "14100"],
        env=env if env is not None else default_env,
    )
    doc["spec"]["template"]["spec"]["terminationGracePeriodSeconds"] = grace
    return doc


def test_builds_pool_guard_rejects_drift():
    """Guard-removed companion (ungated): synthetic docs prove the helper
    raises when the general worker consumes builds, the builds pod carries
    the 300s limit, the grace period is not derived, or the exported limit
    disagrees with the args."""
    good_env = [
        {"name": "REDIS_URL", "value": "redis://broker"},
        {"name": _BUILDS_LIMIT_ENV, "value": "14400"},
    ]
    queues = ["priority", "default", "atlas"]
    worker = _synthetic_platform_deployment(
        "worker",
        [*_CELERY_WORKER_ARGS, "-Q", ",".join(queues)],
        env=good_env,
    )
    good = _synthetic_builds_pool()
    _assert_builds_pool(
        [worker, good],
        limit=14400,
        soft_limit=14100,
        slack=60,
        worker_queues=queues,
    )

    with pytest.raises(AssertionError, match="do not consume worker.queues"):
        _assert_builds_pool(
            [worker, good],
            limit=14400,
            soft_limit=14100,
            slack=60,
            worker_queues=["priority", "default", "atlas", "builds"],
        )
    with pytest.raises(AssertionError, match="hours-scale limit"):
        _assert_builds_pool(
            [worker, _synthetic_builds_pool(args=[*_CELERY_WORKER_ARGS, "-Q", "builds"])],
            limit=14400,
            soft_limit=14100,
            slack=60,
            worker_queues=queues,
        )
    with pytest.raises(AssertionError, match="!= limit"):
        _assert_builds_pool(
            [worker, _synthetic_builds_pool(grace=310)],
            limit=14400,
            soft_limit=14100,
            slack=60,
            worker_queues=queues,
        )
    with pytest.raises(AssertionError, match=_BUILDS_LIMIT_ENV):
        _assert_builds_pool(
            [worker, _synthetic_builds_pool(env=[{"name": "REDIS_URL", "value": "redis://broker"}])],
            limit=14400,
            soft_limit=14100,
            slack=60,
            worker_queues=queues,
        )
    with pytest.raises(AssertionError, match="worker-builds Deployment missing"):
        _assert_builds_pool(
            [worker],
            limit=14400,
            soft_limit=14100,
            slack=60,
            worker_queues=queues,
        )

    beat = _synthetic_platform_deployment(_BEAT_COMPONENT, list(_BEAT_ARGS), env=good_env)
    beat["spec"]["replicas"] = 1
    beat["spec"]["strategy"] = {"type": "Recreate"}
    _assert_beat_is_a_singleton_scheduler([worker, beat])
    beat["spec"]["replicas"] = 2
    with pytest.raises(AssertionError, match="single replica"):
        _assert_beat_is_a_singleton_scheduler([worker, beat])
