"""Steward's `deploy` duty-adapter module (AD-1/AD-4) — Epic 2's single file,
mirrors `keys.py`'s "one module per duty" precedent.

Story 102.3 (CAP-168) retired the `dashboard` and `status` verbs and their git plumbing (the
no-op build, the diff, the commit-and-push, the last-deploy-commit reader and the tracked-ledger
refusal that guarded the committing verb): the generator they wrapped retired on
2026-08-25, the Pages artifact is built and deployed by `.github/workflows/pages.yml`, and
`steward pages build|deploy|status` (`pages_duty.py`) is the duty that speaks to it. They were
deleted, not deprecated (AD-5's 2026-08-09 rule); no verb here commits or pushes.

Story 9.5 slice (CAP-6, AD-5, AD-8): `DeploymentTopology` + `check_shareable_
state` implement AD-5's refusal — "any cross-worker shared state that cannot
be shared across worker processes is refused when the deployment runs more
than one worker" — that `dashboard/cache.py`'s own module docstring named as
explicitly deferred to this story. `render_daphne_unit`/`render_edge_config`
render CAP-6's "production-shaped runtime" (a daphne worker fleet + an nginx
edge doing TLS termination and network-policy restriction) as plain strings
— no template-file/package-data plumbing exists anywhere in this package, so
none is invented here (this story's spec, "Design Notes"). All of it lives
in THIS module, never under `dashboard/`: AD-1 classifies ASGI topology and
edge policy as out-of-process concerns, and the existing import-boundary
invariant (`test_no_module_outside_dashboard_imports_dashboard_django_or_
channels`) already forbids this file from importing anything under
`dashboard/`, `django`, or `channels` — so this code deals only in plain
strings (dotted backend class paths, peer addresses, file paths), never a
real Django/Channels object. Wired as `steward deploy perimeter`.

Story 9.7 slice (CAP-8, AD-10): `StaticPanel` + `render_static_index` +
`_run_static` implement AD-10's refusal — "a board that has declared an
access column may not be delivered by static export... refuses rather than
warns" — wired as a FOURTH verb, `steward deploy static`. Panels arrive as
caller-supplied, already-rendered HTML fragments (e.g. an adopter's own
`plotly.graph_objects.Figure.to_html(full_html=False)` output) and are assembled verbatim
into one self-contained `docs/dashboard/<board>/index.html`, which lands
through a pull request like any tracked file (no verb pushes; Story 102.3).
"""

from __future__ import annotations

import argparse
import html
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .interfaces import DutyResult

# ── Repo-root resolution (mirrors `keys.py`'s `locate_http_module`/`repo_root`
# walk-up precedent, keyed on a marker this duty actually cares about rather
# than importing `keys.py` — that module resolves `_http` at first use through
# `http_bridge()` and `cli.py`'s `resolve_duty` still imports it lazily, so an
# unrelated duty has no reason to import it eagerly) ──

# The tracked README of the publish root. Atlas Story 30.1 took the Kedro-Viz export
# (`docs/dashboard/kedro-viz/`) out of git -- it arrives as the `kedro-viz-export` workflow
# artifact -- so the export's `index.html` is no longer on a fresh clone and cannot mark the root.
_DASHBOARD_GENERATE_MARKER = Path("docs/dashboard/README.md")
_DASHBOARD_RELATIVE_PATH = Path("docs/dashboard")


def repo_root() -> Path:
    """Return the local-recipes checkout root.

    Walks up from this file's own resolved location looking for
    `docs/dashboard/README.md` (tracked; the Kedro-Viz export beside it is not) — robust
    to whatever depth the installed/editable `pyforge-steward` package ends up at
    relative to the repo root, same rationale as `keys.py`'s `locate_http_module`.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _DASHBOARD_GENERATE_MARKER).is_file():
            return ancestor
    raise RuntimeError(
        f"deploy.py: could not locate {_DASHBOARD_GENERATE_MARKER} by walking "
        f"up from {here} — this module must live inside a local-recipes checkout."
    )


# ── Deployment topology + AD-5 shareability refusal (CAP-6, Story 9.5) ─────


@dataclass(frozen=True)
class DeploymentTopology:
    """The deployment shape `check_shareable_state` validates and
    `render_daphne_unit`/`render_edge_config` render manifests for.

    `worker_count` is the number of daphne worker processes the rendered
    systemd fleet starts. `cache_backend`/`channel_layer_backend` are the
    DOTTED CLASS PATHS an adopter's Django `CACHES`/`CHANNEL_LAYERS` setting
    would name for the response cache and the Channels channel layer
    respectively (e.g. `"django.core.cache.backends.locmem.LocMemCache"`,
    `"channels_redis.core.RedisChannelLayer"`) — plain strings, never an
    imported class: this module may not import `django`/`channels` (the
    import-boundary invariant), so it can only compare the STRING an
    adopter would put in settings, exactly as `dashboard/declarations.py`'s
    `AccessDeclaration`/`TrustedIngress` validate plain strings rather than
    live objects for the same reason.

    Validated at construction time, naming the exact offending field —
    mirrors `declarations.py`'s and `keys.py`'s `HostScopedCredential`
    established convention in this package.
    """

    worker_count: int
    cache_backend: str
    channel_layer_backend: str

    def __post_init__(self) -> None:
        if not isinstance(self.worker_count, int) or isinstance(self.worker_count, bool):
            raise TypeError(
                f"DeploymentTopology.worker_count must be an int, got "
                f"{type(self.worker_count).__name__} — `bool` is excluded "
                "even though it satisfies `isinstance(_, int)`, since `True`/"
                "`False` are never a meaningful worker count"
            )
        if self.worker_count <= 0:
            raise ValueError(
                f"DeploymentTopology.worker_count must be positive, got "
                f"{self.worker_count!r} — a deployment needs at least one worker"
            )
        for field_name, value in (
            ("cache_backend", self.cache_backend),
            ("channel_layer_backend", self.channel_layer_backend),
        ):
            if not isinstance(value, str):
                raise TypeError(
                    f"DeploymentTopology.{field_name} must be a string (a "
                    f"dotted Django/Channels backend class path), got "
                    f"{type(value).__name__}"
                )
            if not value.strip():
                raise ValueError(
                    f"DeploymentTopology.{field_name} must not be empty or "
                    "whitespace-only — check_shareable_state has nothing to "
                    "allowlist against"
                )
            # Padding too (review pass, mirroring `declarations.py`'s
            # identical convention): a padded value passes the emptiness
            # check above, then silently fails `check_shareable_state`'s
            # exact-match allowlist comparison even for an otherwise-valid
            # Redis-backed class path -- misreporting a legitimate backend
            # as unshareable instead of naming the real problem (the
            # padding). Rejected rather than trimmed, so the declaration
            # means exactly what it says.
            if value != value.strip():
                raise ValueError(
                    f"DeploymentTopology.{field_name} {value!r} carries "
                    "leading/trailing whitespace — a padded dotted class "
                    "path matches nothing in check_shareable_state's allowlist"
                )


class UnshareableStateError(ValueError):
    """AD-5: a cross-worker-unshareable backend was declared while
    `worker_count > 1` — the response cache or the Channels channel layer
    cannot actually deliver the property (one upstream fetch; every viewer
    sees a broadcast) the deployment claims to have."""


# AD-5's allowlist (fail-closed): only backends this story can cite as
# genuinely cross-process-shared AND actually usable with what the
# `[dashboard]` extra installs. Judgment call, recorded here rather than
# assumed (this story's spec leaves the exact class path(s) open): only
# Django's own built-in Redis backend (4.0+) is allowlisted, because its
# `redis` client dependency is already satisfied transitively by
# `channels_redis` (itself in the extra for the channel layer, below) --
# review pass found `django_redis.cache.RedisCache` (the third-party
# `django-redis` package) allowlisted here with NO corresponding dependency
# anywhere in this extra or pixi.toml, so passing `check_shareable_state`
# gave false confidence about a backend the extra cannot actually satisfy.
# Narrowed rather than widened the extra to cover it -- matches this
# allowlist's own established, more conservative precedent for the
# channel-layer side below. Matching names exactly, not by prefix, so a
# project-specific subclass is refused rather than silently trusted
# (`cache.py`'s own docstring: only a backend this module can actually
# vouch for is accepted). The channel-layer allowlist stays to the ONE
# class the architecture Stack table names by its own words as "the
# sanctioned layer backend" — widening it to `channels_redis`'s other
# shipped layer class was deliberately not done, to avoid allowlisting
# something neither the Spec nor the architecture actually named.
_SHAREABLE_CACHE_BACKENDS: tuple[str, ...] = ("django.core.cache.backends.redis.RedisCache",)
_SHAREABLE_CHANNEL_LAYER_BACKENDS: tuple[str, ...] = ("channels_redis.core.RedisChannelLayer",)


def check_shareable_state(topology: DeploymentTopology) -> None:
    """AD-5: refuse a cross-worker-unshareable backend once `workers > 1`.

    `worker_count == 1` passes unconditionally, for any backend — AD-5's own
    text: "a single-worker adopter may use in-process backends for both."
    Above that, `cache_backend` and `channel_layer_backend` must each match
    one of the allowlisted Redis-backed classes above; an in-process backend
    (`LocMemCache`, `channels.layers.InMemoryChannelLayer`) silently loses
    the cross-worker guarantee it claims once more than one worker exists
    (`dashboard/cache.py`'s own module docstring; the architecture's own
    rejected "accepting any backend" alternative).

    Raises `UnshareableStateError` naming the FIRST offending field only
    (cache checked before channel layer, matching the dataclass's own field
    order) — never both merged into one message, so a caller such as
    `_run_perimeter` names exactly one missing/incompatible declaration per
    the architecture's "Refusals" convention ("a refused deployment names
    the missing declaration").
    """
    if topology.worker_count == 1:
        return
    if topology.cache_backend not in _SHAREABLE_CACHE_BACKENDS:
        raise UnshareableStateError(
            f"cache_backend {topology.cache_backend!r} is not cross-worker "
            f"shareable under worker_count={topology.worker_count} — "
            f"allowlisted backends are {_SHAREABLE_CACHE_BACKENDS!r} (AD-5)"
        )
    if topology.channel_layer_backend not in _SHAREABLE_CHANNEL_LAYER_BACKENDS:
        raise UnshareableStateError(
            f"channel_layer_backend {topology.channel_layer_backend!r} is "
            f"not cross-worker shareable under worker_count="
            f"{topology.worker_count} — allowlisted backends are "
            f"{_SHAREABLE_CHANNEL_LAYER_BACKENDS!r} (AD-5)"
        )


# ── Deployment manifests: daphne systemd fleet + nginx edge (CAP-6, Story 9.5) ─
#
# Plain strings built from `DeploymentTopology`'s fields — no Jinja, no
# `.template` asset files, no new packaging plumbing (this story's spec,
# "Design Notes": no package-data precedent exists anywhere in this package).

_DEFAULT_BASE_PORT = 8001
_DEFAULT_BIND_HOST = "127.0.0.1"
# Story 86.1 / herald DW-13-6-1: optional `--asgi-application` names the daphne
# target; without it the rendered unit keeps the Story 9.5 placeholder the
# adopter replaces by hand.
_ASGI_APPLICATION_PLACEHOLDER = "myproject.asgi:application"  # adopter fills in


def _is_asgi_dotted_path(path: str) -> bool:
    """True when *path* is a non-empty dotted identifier (Story 86.1 MODULE/ATTR grammar)."""
    if not path:
        return False
    for segment in path.split("."):
        if not segment:
            return False
        first, rest = segment[0], segment[1:]
        if not (first.isalpha() or first == "_"):
            return False
        if rest and not all(ch.isalnum() or ch == "_" for ch in rest):
            return False
    return True


def _validate_asgi_application(value: str) -> str | None:
    """Return a refusal message when *value* is not a safe MODULE:ATTR path."""
    if value.count(":") != 1:
        return _asgi_application_refusal(value)
    module, attr = value.split(":", 1)
    if not _is_asgi_dotted_path(module) or not _is_asgi_dotted_path(attr):
        return _asgi_application_refusal(value)
    return None


def _asgi_application_refusal(value: str) -> str:
    return (
        f"--asgi-application {value!r} is not a valid MODULE:ATTR import path "
        "(expected dotted module, colon, dotted attribute — e.g. "
        "myproject.asgi:application)"
    )


def _worker_ports(topology: DeploymentTopology, *, base_port: int) -> tuple[int, ...]:
    """The bind ports both `render_daphne_unit`'s enable-command comment and
    `render_edge_config`'s nginx upstream block derive from — the single
    source both functions read, so the two rendered manifests can never
    independently drift out of step on how many workers/ports there are.
    One port per worker, sequential from `base_port`.

    Raises `ValueError` if the highest port would exceed 65535 (review pass:
    `DeploymentTopology.worker_count` only checked `> 0`, so a large count
    silently produced an out-of-range port with no error and no rendered
    manifest naming the problem).
    """
    highest_port = base_port + topology.worker_count - 1
    if highest_port > 65535:
        raise ValueError(
            f"worker_count={topology.worker_count} with base_port={base_port} "
            f"would need a port up to {highest_port}, beyond the valid range "
            "(1-65535) -- lower worker_count or base_port"
        )
    return tuple(base_port + i for i in range(topology.worker_count))


def render_daphne_unit(
    topology: DeploymentTopology,
    *,
    base_port: int = _DEFAULT_BASE_PORT,
    bind_host: str = _DEFAULT_BIND_HOST,
    asgi_application: str = _ASGI_APPLICATION_PLACEHOLDER,
) -> str:
    """Render a systemd TEMPLATE unit for a fleet of `topology.worker_count`
    daphne ASGI workers — daphne has no built-in worker-pool flag (unlike
    gunicorn's `--workers`), so the fleet is one OS process per worker,
    started as separate template-unit instances.

    A systemd template unit's `%i` is the literal string after `@` in the
    instance name it is started as. This renders each instance named by the
    PORT it binds (`pyforge-steward-dashboard@8001.service`) rather than by
    an ordinal worker index, which would need arithmetic systemd has no
    specifier for (`800%i` string-CONCATENATES, not adds, and breaks past
    worker 9) — the port-as-instance-name convention sidesteps that trap
    entirely and needs no arithmetic inside the unit file at all.

    `--proxy-headers` is always passed — judgment call, recorded here: AD-4's
    ingress refusal (`dashboard/middleware.py`) depends on `scope["client"]`
    reflecting the real peer, which requires daphne to parse
    `X-Forwarded-For` rather than reporting the edge proxy's own address for
    every connection. `middleware.py`'s own module docstring names exactly
    this as the deployment precondition Story 9.5 owns. This is only SAFE
    paired with `render_edge_config`'s nginx OVERWRITING (not appending to)
    `X-Forwarded-For` — the two rendered manifests are a matched pair, never
    independently correct; see that function's docstring for the other half.

    Binds to `bind_host` (localhost by default) — `render_edge_config`'s
    nginx is the only thing meant to reach these ports directly; network
    policy is the edge's job (CAP-6), not daphne's own.
    """
    ports = _worker_ports(topology, base_port=base_port)
    enable_cmd = " ".join(f"pyforge-steward-dashboard@{p}.service" for p in ports)
    if asgi_application == _ASGI_APPLICATION_PLACEHOLDER:
        placeholder_comment = (
            f"# Replace {_ASGI_APPLICATION_PLACEHOLDER} below with your project's real\n"
            f"# ASGI application import path before enabling.\n"
            "\n"
        )
    else:
        placeholder_comment = ""
    return f"""# pyforge-steward[dashboard] — daphne ASGI worker fleet (Story 9.5, CAP-6/AD-5/AD-8)
# Template unit: one instance per worker, named by the port it binds. Enable
# the full fleet for this topology (worker_count={topology.worker_count}) with:
#   systemctl enable --now {enable_cmd}
#
{placeholder_comment}[Unit]
Description=pyforge-steward dashboard daphne worker on port %i
After=network.target

[Service]
Type=simple
ExecStart=daphne --bind {bind_host} --port %i --proxy-headers {asgi_application}
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
"""


# Non-whitespace characters that could break an interpolated value out of
# the nginx directive line it is rendered into (review pass: `render_edge_
# config` previously validated only emptiness, so a crafted `--trusted-
# address`/`--tls-cert`/`--tls-key`/server-name value containing e.g. `;`
# could inject an arbitrary extra directive into a config whose entire job
# is enforcing this deployment's security perimeter). Whitespace ANYWHERE
# in the value (not just leading/trailing) is checked separately below --
# nginx directive values here are rendered unquoted, so even an EMBEDDED
# space breaks the directive into two tokens. `#` starts a same-line nginx
# comment (truncating whatever directive it lands in); `$` triggers nginx
# variable interpolation in most directive contexts, including the modern
# `ssl_certificate`/`ssl_certificate_key` (review pass: both were absent from
# the original three-character set).
_UNSAFE_NGINX_VALUE_CHARS = frozenset(";{}#$")

# Story 84.1 — PostgreSQL grants that make CAP-4's audit table append-only for
# the application role while reserving DELETE for the retention runner role.
_DEFAULT_AUDIT_SCHEMA = "public"
_DEFAULT_AUDIT_TABLE = "pyforge_steward_dashboard_auditentry"
_UNSAFE_SQL_IDENTIFIER_CHARS = frozenset(";\"' \t\n\r{}#$")


def _validate_sql_identifier(field_name: str, value: str) -> None:
    """Reject values that cannot safely be interpolated as PostgreSQL identifiers."""
    if not value or not value.strip():
        raise ValueError(f"render_audit_table_grants: {field_name} must not be empty or whitespace-only")
    if any(ch.isspace() for ch in value):
        raise ValueError(
            f"render_audit_table_grants: {field_name} {value!r} contains whitespace — "
            "refused rather than rendering a corrupted grant script"
        )
    if any(ch in _UNSAFE_SQL_IDENTIFIER_CHARS for ch in value):
        raise ValueError(
            f"render_audit_table_grants: {field_name} {value!r} contains a character "
            f"that could break out of the generated SQL (one of "
            f"{''.join(sorted(_UNSAFE_SQL_IDENTIFIER_CHARS))!r})"
        )


def render_audit_table_grants(
    *,
    app_role: str,
    retention_role: str,
    schema: str = _DEFAULT_AUDIT_SCHEMA,
    table: str = _DEFAULT_AUDIT_TABLE,
) -> str:
    """Render SQL granting the app role only SELECT and INSERT on the audit table.

    The retention role receives SELECT, INSERT, and DELETE — enough to run
    ``purge_expired_entries`` (WHERE needs SELECT; the purge audit row needs
    INSERT). UPDATE is not granted to either role, so the trail cannot be
    rewritten in place at the privilege layer (Story 84.1).
    """
    for field_name, value in (
        ("app_role", app_role),
        ("retention_role", retention_role),
        ("schema", schema),
        ("table", table),
    ):
        _validate_sql_identifier(field_name, value)

    if app_role.casefold() == retention_role.casefold():
        raise ValueError(
            "render_audit_table_grants: app_role and retention_role must differ "
            "(compared case-insensitively) — the app role must never hold DELETE"
        )

    qualified = f"{schema}.{table}"
    return f"""\
-- CAP-4 audit trail — append-only for the application role (Story 84.1).
-- Apply as the migration role after {qualified} exists.
REVOKE ALL ON TABLE {qualified} FROM {app_role};
GRANT SELECT, INSERT ON TABLE {qualified} TO {app_role};
REVOKE ALL ON TABLE {qualified} FROM {retention_role};
GRANT SELECT, INSERT, DELETE ON TABLE {qualified} TO {retention_role};
"""


def _validate_nginx_value(field_name: str, value: str) -> None:
    """Shared emptiness/whitespace/injection-character guard for every
    string `render_edge_config` interpolates into the generated config --
    mirrors `declarations.py`'s "reject, don't sanitize" convention so a
    malformed value fails loudly at render time rather than silently
    producing a corrupted or partially-effective security perimeter.
    """
    if not value or not value.strip():
        raise ValueError(f"render_edge_config: {field_name} must not be empty or whitespace-only")
    if any(ch.isspace() for ch in value):
        raise ValueError(
            f"render_edge_config: {field_name} {value!r} contains whitespace -- "
            "rendered unquoted, so even an embedded space (not only leading/"
            "trailing) splits the generated nginx directive into two tokens"
        )
    if any(ch in _UNSAFE_NGINX_VALUE_CHARS for ch in value):
        raise ValueError(
            f"render_edge_config: {field_name} {value!r} contains a character "
            f"that could break out of the generated nginx directive (one of "
            f"{''.join(sorted(_UNSAFE_NGINX_VALUE_CHARS))!r}) -- refused rather "
            "than silently rendering a corrupted security-perimeter config"
        )


def render_edge_config(
    topology: DeploymentTopology,
    *,
    trusted_addresses: Sequence[str],
    tls_cert: str,
    tls_key: str,
    server_name: str = "_",
    base_port: int = _DEFAULT_BASE_PORT,
    bind_host: str = _DEFAULT_BIND_HOST,
) -> str:
    """Render an nginx edge config: TLS termination + an `allow`/`deny`
    network-policy block scoped to `trusted_addresses`, load-balancing
    across `topology.worker_count` daphne workers at the SAME ports
    `render_daphne_unit` binds (`_worker_ports` — see that function's
    docstring for why the two share one source rather than each computing
    its own).

    `trusted_addresses`/`tls_cert`/`tls_key`/`server_name` are plain
    strings/CLI input — this function never imports `TrustedIngress` from
    `dashboard/declarations.py` (the import-boundary invariant forbids this
    module from reaching into `dashboard/` at all), so validation here is
    `_validate_nginx_value`'s emptiness/whitespace/injection-character
    check, not real address-form or header-name validation. `server_name`
    defaults to nginx's own `_` catch-all convention — the adopter is
    expected to replace it with a real domain.

    `X-Forwarded-For` is set by OVERWRITING with `$remote_addr`, never
    `$proxy_add_x_forwarded_for` (which APPENDS) — judgment call, recorded
    here: `dashboard/middleware.py`'s own module docstring names an
    appending proxy as defeating AD-4's ingress check entirely, since a
    client-supplied `X-Forwarded-For` entry then survives as the leftmost
    one daphne's `--proxy-headers` parsing reads. This edge config is the
    other half of that documented deployment precondition.

    `Connection` is set via nginx's `map $http_upgrade $connection_upgrade`
    idiom rather than a hardcoded `"upgrade"` (review pass: hardcoding it
    forced every plain HTTP request through the same upgrade-connection
    header, not only real WebSocket upgrade requests). `proxy_read_timeout`/
    `proxy_send_timeout` are raised to 24h (review pass: nginx's ~60s
    default silently drops the long-lived WebSocket connections this whole
    pattern's Channels layer exists to carry).

    Raises `ValueError` if `trusted_addresses` is empty, or if any of
    `trusted_addresses`/`tls_cert`/`tls_key`/`server_name` is empty,
    whitespace-padded, or contains a character that could break out of a
    generated nginx directive — a network-policy block with nothing to
    allow (or a corrupted directive) enforces nothing while looking like it
    does (mirrors `TrustedIngress.addresses`'s own non-empty requirement
    without importing that class, per the import-boundary note above).
    """
    if not trusted_addresses:
        raise ValueError(
            "render_edge_config: trusted_addresses must not be empty — an "
            "edge config with no declared trusted ingress restricts access "
            "to nothing while appearing to enforce a network policy"
        )
    for index, address in enumerate(trusted_addresses):
        _validate_nginx_value(f"trusted_addresses[{index}]", address)
    _validate_nginx_value("tls_cert", tls_cert)
    _validate_nginx_value("tls_key", tls_key)
    _validate_nginx_value("server_name", server_name)

    ports = _worker_ports(topology, base_port=base_port)
    upstream_name = "pyforge_steward_dashboard_workers"
    upstream_servers = "\n".join(f"    server {bind_host}:{p};" for p in ports)
    allow_lines = "\n".join(f"    allow {addr};" for addr in trusted_addresses)

    return f"""# pyforge-steward[dashboard] — nginx edge (Story 9.5, CAP-6/AD-4/AD-8)
# TLS termination + network-policy restriction to the declared trusted
# ingress; proxies to the daphne worker fleet render_daphne_unit renders.

map $http_upgrade $connection_upgrade {{
    default upgrade;
    ''      close;
}}

upstream {upstream_name} {{
{upstream_servers}
}}

server {{
    listen 443 ssl;
    server_name {server_name};

    ssl_certificate {tls_cert};
    ssl_certificate_key {tls_key};

    # AD-4's declared trusted ingress: only these peers may reach the app.
{allow_lines}
    deny all;

    location / {{
        proxy_pass http://{upstream_name};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        # Overwrite, never append -- see this function's docstring.
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        # Long-lived Channels WebSocket connections outlive nginx's ~60s
        # default idle timeout -- see this function's docstring.
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }}
}}
"""


def _run_perimeter(ns: argparse.Namespace) -> DutyResult:
    """`deploy perimeter --workers N --cache-backend PATH
    --channel-layer-backend PATH [--trusted-address ADDR ...] [--tls-cert
    PATH --tls-key PATH] [--output-dir DIR]`.

    Always validates first: `DeploymentTopology`'s own construction-time
    checks, then `check_shareable_state` (AD-5). Every `TypeError`/
    `ValueError`/`AttributeError` from validation OR rendering is caught
    here and reported as a named duty-level refusal — never an uncaught
    crash (AD-8's boundary stays `cli.main()`'s alone). `AttributeError` is
    caught alongside the other two (review pass): the required fields
    (`ns.workers`/`.cache_backend`/`.channel_layer_backend`) were accessed
    directly rather than via the `getattr` fallback the optional fields
    below use, so an incomplete `Namespace` raised uncaught, contradicting
    this exact guarantee. A topology that fails the check writes NOTHING
    (I/O matrix).

    With no `--output-dir`: validation-only — `DutyResult(ok=True, ...)`,
    nothing written (I/O matrix's last row).

    With `--output-dir`: also requires at least one `--trusted-address` and
    both `--tls-cert`/`--tls-key` — an edge config with no declared ingress
    or no certificate would enforce nothing while looking complete, so this
    refuses rather than rendering one (the architecture's "Refusals"
    convention, applied here to this story's OWN declarations, not only the
    dashboard app's). A filesystem failure writing the manifests (e.g. an
    unwritable `--output-dir`) is caught as `OSError` and reported the same
    way, never propagated as an internal crash.
    """
    try:
        topology = DeploymentTopology(
            worker_count=ns.workers,
            cache_backend=ns.cache_backend,
            channel_layer_backend=ns.channel_layer_backend,
        )
        check_shareable_state(topology)
        # Review pass: without this, an extreme `--workers` value (past the
        # port range `_worker_ports` bounds-checks) reported `ok=True`
        # "topology valid" in validation-only mode, then failed only once
        # `--output-dir` was added later -- a "valid" verdict that wasn't
        # durable. Validating the same port range here makes both branches
        # below agree on what "valid" means.
        _worker_ports(topology, base_port=_DEFAULT_BASE_PORT)
    except (TypeError, ValueError, AttributeError) as exc:
        return DutyResult(ok=False, summary=f"deploy perimeter: refused — {exc}")

    asgi_application_raw = getattr(ns, "asgi_application", None)
    asgi_application = _ASGI_APPLICATION_PLACEHOLDER if asgi_application_raw is None else asgi_application_raw
    if asgi_application_raw is not None:
        asgi_refusal = _validate_asgi_application(asgi_application_raw)
        if asgi_refusal is not None:
            return DutyResult(ok=False, summary=f"deploy perimeter: refused — {asgi_refusal}")

    output_dir = getattr(ns, "output_dir", None)
    if not output_dir:
        summary = (
            "deploy perimeter: topology valid "
            f"(workers={topology.worker_count}, "
            f"cache_backend={topology.cache_backend!r}, "
            f"channel_layer_backend={topology.channel_layer_backend!r})"
        )
        if asgi_application_raw is not None:
            summary += f", asgi_application={asgi_application!r}"
        summary += " — no --output-dir given, nothing written"
        return DutyResult(ok=True, summary=summary)

    trusted_addresses = tuple(getattr(ns, "trusted_address", None) or ())
    tls_cert = getattr(ns, "tls_cert", None)
    tls_key = getattr(ns, "tls_key", None)
    app_db_role = getattr(ns, "app_db_role", None)
    audit_retention_db_role = getattr(ns, "audit_retention_db_role", None)
    missing = [
        flag
        for flag, value in (
            ("--trusted-address", trusted_addresses),
            ("--tls-cert", tls_cert),
            ("--tls-key", tls_key),
            ("--app-db-role", app_db_role),
            ("--audit-retention-db-role", audit_retention_db_role),
        )
        if not value
    ]
    if missing:
        return DutyResult(
            ok=False,
            summary=(
                "deploy perimeter: refused — --output-dir was given but "
                f"{', '.join(missing)} was not supplied; an edge config "
                "cannot be rendered without a declared trusted ingress, "
                "a TLS certificate/key pair, and the audit-table database "
                "roles (Story 84.1)"
            ),
        )

    try:
        unit_text = render_daphne_unit(topology, asgi_application=asgi_application)
        edge_text = render_edge_config(
            topology,
            trusted_addresses=trusted_addresses,
            tls_cert=tls_cert,
            tls_key=tls_key,
        )
        grants_text = render_audit_table_grants(
            app_role=app_db_role,
            retention_role=audit_retention_db_role,
        )
    except (TypeError, ValueError) as exc:
        return DutyResult(ok=False, summary=f"deploy perimeter: refused — {exc}")

    output_path = Path(output_dir)
    unit_path = output_path / "pyforge-steward-dashboard@.service"
    edge_path = output_path / "pyforge-steward-dashboard.nginx.conf"
    grants_path = output_path / "pyforge-steward-dashboard-audit-grants.sql"
    # Write both to temp names, then rename both onto their final names only
    # once BOTH writes succeeded (same-directory rename is atomic on POSIX) --
    # review pass: writing directly to the final names left a lone unit file
    # on disk if the edge-config write failed second, even though the duty
    # reported `ok=False` and wrote nothing per the I/O matrix.
    unit_tmp = output_path / (unit_path.name + ".tmp")
    edge_tmp = output_path / (edge_path.name + ".tmp")
    grants_tmp = output_path / (grants_path.name + ".tmp")
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        unit_tmp.write_text(unit_text, encoding="utf-8")
        edge_tmp.write_text(edge_text, encoding="utf-8")
        grants_tmp.write_text(grants_text, encoding="utf-8")
    except OSError as exc:
        # Best-effort cleanup: e.g. `output_path.mkdir()` itself failing
        # (review pass's own regression -- a FILE already at `output_path`)
        # means neither temp file was ever created, so unlinking under it
        # raises `NotADirectoryError` (still an `OSError`) rather than
        # `FileNotFoundError` -- caught here so cleanup can never mask the
        # real error this branch is already reporting.
        for tmp in (unit_tmp, edge_tmp, grants_tmp):
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        return DutyResult(ok=False, summary=f"deploy perimeter: refused — could not write to {output_path}: {exc}")
    try:
        unit_tmp.rename(unit_path)
        edge_tmp.rename(edge_path)
        grants_tmp.rename(grants_path)
    except OSError as exc:
        # Review pass: the renames themselves previously sat OUTSIDE this
        # guard, so a rename failure (e.g. a directory already at the target
        # name) escaped uncaught instead of returning the named refusal this
        # function's own docstring promises. Best-effort cleanup mirrors the
        # write-failure branch above; a lone already-renamed file from the
        # first `rename()` succeeding before the second fails is a residual
        # this cleanup cannot undo without a backup of any prior content at
        # that path, which is out of this story's scope.
        for tmp in (unit_tmp, edge_tmp, grants_tmp):
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        return DutyResult(
            ok=False,
            summary=f"deploy perimeter: refused — could not finalize manifests in {output_path}: {exc}",
        )

    summary = f"deploy perimeter: rendered daphne unit + nginx edge config + audit-table grants SQL to {output_path}"
    if asgi_application_raw is not None:
        summary += f" (asgi_application={asgi_application!r})"
    return DutyResult(ok=True, summary=summary)


# ── Static export (CAP-8, AD-10, Story 9.7) ─────────────────────────────────


@dataclass(frozen=True)
class StaticPanel:
    """One pre-rendered HTML panel `render_static_index` embeds verbatim.

    `label` is the human-readable heading shown above the panel (escaped via
    `html.escape()` before interpolation — see `render_static_index`);
    `html` is the caller's own already-rendered FRAGMENT (e.g. an adopter's
    `plotly.graph_objects.Figure.to_html(full_html=False)` output), embedded
    byte-for-byte unchanged — the guarantee that hosted and static modes
    share one chart-producing source, never re-derived (this story's
    Boundaries).

    `full_html=False` is not incidental: `to_html()` defaults to
    `full_html=True`, which returns a COMPLETE document, and embedding that
    verbatim inside a `<section>` nests `<html>`/`<head>`/`<body>` inside the
    assembled page. Nothing here parses or validates the fragment to catch
    that — embedding verbatim is the whole point (Boundaries), so the
    fragment contract is the caller's to honour. Adopters emitting more than
    one panel also want `include_plotlyjs="cdn"` (or `False` on the panels
    after the first), since the `True` default inlines a full copy of
    plotly.js into every panel.
    Validation mirrors `dashboard/declarations.py`'s established idiom
    (rejected, not sanitized, so a caller sees exactly why); kept here
    rather than imported, since `deploy.py` may not import from
    `dashboard/` at all (the import-boundary invariant).

    `html` carries no non-empty requirement, asymmetric with `label`'s
    strict validation — deliberate: an empty panel fragment is a caller's
    own (odd but harmless) choice, not a shape this module can meaningfully
    reject.
    """

    label: str
    html: str

    def __post_init__(self) -> None:
        if not isinstance(self.label, str):
            raise TypeError(f"StaticPanel.label must be a string, got {type(self.label).__name__}")
        if not isinstance(self.html, str):
            raise TypeError(f"StaticPanel.html must be a string, got {type(self.html).__name__}")
        if not self.label.strip():
            raise ValueError("StaticPanel.label must not be empty or whitespace-only")
        if self.label != self.label.strip():
            raise ValueError(f"StaticPanel.label {self.label!r} carries leading/trailing whitespace")


def render_static_index(panels: Sequence[StaticPanel], *, board: str) -> str:
    """Render one self-contained `index.html` embedding every panel's
    `html` byte-for-byte verbatim, in the order given, inside a responsive
    CSS grid.

    Raises `ValueError` naming a duplicate `panel.label` — two panels
    sharing a heading is almost certainly a caller mistake, not two
    genuinely different panels. `panel.label` and `board` are HTML-escaped
    (`html.escape()`) before interpolation into `<h2>`/`<title>` — both
    feed a page this story's own Intent says gets committed and published
    on GitHub Pages, unlike `panel.html`, which stays verbatim by design
    (see `StaticPanel`'s docstring). A `<meta name="viewport">` tag is
    always emitted so the "responsive grid" claim holds on a mobile
    viewport too.

    `panels` is materialized once up front: this function reads it TWICE
    (the duplicate-label scan, then the section render), so a one-shot
    iterable (a generator, `map`, a consumed `iter()`) would be exhausted
    by the first pass and silently render a page with ZERO panels rather
    than raising — wrong output reported as success, the worst failure
    shape for a function whose whole job is emitting the published page.
    The annotation says `Sequence`, but honouring it is cheap and the
    alternative failure is silent.
    """
    panels = tuple(panels)
    seen_labels: set[str] = set()
    for panel in panels:
        if panel.label in seen_labels:
            raise ValueError(f"render_static_index: duplicate panel label {panel.label!r}")
        seen_labels.add(panel.label)

    sections = "\n".join(
        f'    <section class="panel">\n      <h2>{html.escape(panel.label)}</h2>\n{panel.html}\n    </section>'
        for panel in panels
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(board)}</title>
<style>
  body {{ margin: 0; font-family: sans-serif; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 1rem;
    padding: 1rem;
  }}
  .panel {{ border: 1px solid #ccc; border-radius: 4px; padding: 1rem; }}
</style>
</head>
<body>
  <div class="grid">
{sections}
  </div>
</body>
</html>
"""


# Hand-rolled `^[A-Za-z0-9_-]+$` equivalent — `import re` is unconditionally
# banned in this module (`test_deploy_has_no_story_status_derivation`, Story
# 5.2/AD-71/AD-1), so this replicates the same character-set semantics by
# hand rather than reaching for the toolkit that ban exists to keep out.
_VALID_BOARD_SLUG_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def _is_valid_board_slug(value: str) -> bool:
    """`^[A-Za-z0-9_-]+$` — non-empty, every character in the allowlist.
    Refuses `--board ../../etc`, an absolute path, or anything else that
    could escape `docs/dashboard/` once joined into a path."""
    return bool(value) and all(ch in _VALID_BOARD_SLUG_CHARS for ch in value)


_STATIC_INDEX_FILENAME = "index.html"
_STATIC_INDEX_TMP_FILENAME = "index.html.tmp"
# The only three directory shapes `_is_board_output_dir_safe_to_write` ever
# trusts: a completed prior publish, a killed FIRST publish, or a killed
# REPUBLISH of an already-published board.
_TRUSTED_STATIC_ENTRY_SHAPES: tuple[frozenset[str], ...] = (
    frozenset({_STATIC_INDEX_FILENAME}),
    frozenset({_STATIC_INDEX_TMP_FILENAME}),
    frozenset({_STATIC_INDEX_FILENAME, _STATIC_INDEX_TMP_FILENAME}),
)


def _is_path_gitignored(path: Path, *, cwd: Path) -> bool:
    """True when `git` would refuse to add `path` because a `.gitignore`
    rule excludes it (review follow-up pass finding).

    A board lands through a pull request, and `git add` honours
    `.gitignore`. A board slug is only constrained to
    `^[A-Za-z0-9_-]+$`, which happily admits `build`, `dist`, `out`, `lib`,
    `env`, `venv`, `logs`, `target` and `node_modules`; every one of those is
    matched by a bare-directory rule in this repo's own `.gitignore`, which
    applies at ANY depth — so `docs/dashboard/build/index.html` is ignored
    today. Writing there reported success while the board could never be
    committed or even seen as a diff: silent non-publication.

    A non-zero exit means "not ignored" (1), or that this question cannot be
    answered here at all (128 — `cwd` is not a git worktree, as in this
    verb's own tests). Both proceed: this check exists to catch a
    publishable-looking board that git will silently drop, never to make a
    git worktree a precondition for writing a file.
    """
    try:
        completed = subprocess.run(
            ["git", "check-ignore", "-q", "--", str(path)],
            cwd=str(cwd),
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0


def _is_board_output_dir_safe_to_write(output_dir: Path) -> bool:
    """Refuse to write over foreign content at `docs/dashboard/<board>/` —
    the structural fix closing five recurring review-pass findings at once
    (this story's Spec Change Log, passes 2-5): a symlinked ancestor, a
    symlinked target directory, a symlinked trusted entry, a hard-linked
    trusted entry, and a special-file-type (FIFO/socket) at a trusted name
    each previously bypassed one variant of this check or another.

    Every filesystem probe here (`.exists()`/`.is_dir()`/`.iterdir()`/
    `.is_symlink()`/`.stat()`) can raise `PermissionError` (an `OSError`) —
    the caller wraps this whole call in `except OSError`, never lets one
    escape uncaught.

    Order:
    1. Either of `output_dir`'s two FIXED ancestors (`docs`, `docs/
       dashboard`) being a symlink refuses — checked from `output_dir`'s
       own `.parent`/`.parent.parent`, never a bare `Path("docs")` (which
       would resolve against the process's CWD, not necessarily the repo
       root).
    2. `output_dir` itself being a symlink refuses.
    3. A genuinely absent `output_dir` is safe (nothing to collide with).
    4. `output_dir` existing but not a directory refuses.
    5. An empty existing directory is safe (no prior successful write, no
       foreign content — see this story's Design Notes).
    6. The entry NAMES present must exactly equal one of the three trusted
       shapes above — anything else (e.g. the real `docs/dashboard/
       kedro-viz/`) refuses.
    7. Structural fix (the final amendment): every entry in that shape
       must POSITIVELY satisfy `is_file()` — which by construction excludes
       every non-regular-file type (FIFOs, sockets, block/char devices,
       directories) in one check, rather than one more named exclusion per
       filesystem primitive discovered — AND independently fail
       `is_symlink()` (a symlink to a real file also satisfies `is_file()`)
       AND fail `st_nlink != 1` (a hard link is, by every other test here,
       an ordinary regular file with no separate identity from the inode
       it shares — only its link count reveals it isn't the one thing
       this verb itself wrote). Any entry failing any of the three refuses
       the whole directory.
    8. Otherwise safe.
    """
    dashboard_dir = output_dir.parent
    docs_dir = output_dir.parent.parent
    if docs_dir.is_symlink() or dashboard_dir.is_symlink():
        return False

    if output_dir.is_symlink():
        return False

    if not output_dir.exists():
        return True

    if not output_dir.is_dir():
        return False

    entries = list(output_dir.iterdir())
    if not entries:
        return True

    entry_names = frozenset(entry.name for entry in entries)
    if entry_names not in _TRUSTED_STATIC_ENTRY_SHAPES:
        return False

    for entry in entries:
        if not entry.is_file():
            return False
        if entry.is_symlink():
            return False
        if entry.stat().st_nlink != 1:
            return False

    return True


def _run_static(ns: argparse.Namespace) -> DutyResult:
    """`deploy static --board SLUG --panel LABEL=PATH [--panel ...]
    [--access-column NAME]`.

    AD-10's refusal runs FIRST, unconditionally, before any other
    validation, path construction, or `--panel` file read: a declared
    (stripped, non-empty) `--access-column` refuses outright — "a board
    that has declared an access column may not be delivered by static
    export... refuses rather than warns" (AD-10). This is caller-asserted,
    never independently verified against a real `AccessDeclaration` —
    `deploy.py` may not import `dashboard/declarations.py` at all (the
    import-boundary invariant); an accepted, documented tradeoff identical
    to Story 9.5's `DeploymentTopology.cache_backend` precedent.

    Then `--board` is validated as a filesystem-safe slug (`_is_valid_
    board_slug`) BEFORE any path is constructed from it, then `--panel`
    presence, then each `--panel LABEL=PATH` entry's shape (a `=`
    separator, a non-empty label) and file content (`OSError` and
    `UnicodeDecodeError` — not an `OSError` subclass — both caught as a
    named refusal: `UnicodeDecodeError` is a `ValueError`, so catching only
    `OSError` would let a corrupt-encoding panel crash instead of refusing). Every string-typed operation on
    `ns.access_column`/`ns.board`/each parsed panel label additionally
    catches `(TypeError, AttributeError)`, mirroring `_run_perimeter`'s own
    documented precedent in this file for a malformed `Namespace`.

    `render_static_index` is called once every panel is read (raises
    `ValueError` naming a duplicate label). Before writing,
    `_is_board_output_dir_safe_to_write` is called inside `except OSError`;
    an unsafe target refuses naming the pre-existing foreign content and
    writes NOTHING. Then `_is_path_gitignored` refuses a board slug whose
    output path a `.gitignore` rule excludes (`build`, `dist`, `out`,
    `node_modules` and friends all satisfy the slug allowlist while being
    ignored at any depth in this repo) — such a board would write
    successfully and then never be committable, pushable, or even visible
    as a diff; see that helper's own docstring. Otherwise the page is
    written atomically (temp file +
    rename, mirroring `_run_perimeter`'s own pattern) to `docs/dashboard/
    <board>/index.html`. `mkdir(parents=True)` drops `exist_ok=True` on
    the branch where `output_dir` did not already exist at safety-check
    time — closing the highest-value slice of the check-then-write TOCTOU
    window for the cost of one keyword argument (this story's Design
    Notes). On a write failure, every ancestor directory freshly created
    by that `mkdir` (not only the leaf) is best-effort `rmdir()`'d,
    innermost first, alongside the temp-file cleanup.
    """
    try:
        access_column = getattr(ns, "access_column", None)
        access_column_declared = access_column is not None and bool(access_column.strip())
    except (TypeError, AttributeError) as exc:
        return DutyResult(ok=False, summary=f"deploy static: refused — malformed --access-column: {exc}")
    if access_column_declared:
        return DutyResult(
            ok=False,
            summary=(
                f"deploy static: refused — --access-column {access_column!r} is declared; "
                "a board with a declared access column may not be delivered by static "
                "export (AD-10)"
            ),
        )

    board = getattr(ns, "board", None)
    try:
        board_valid = bool(board) and _is_valid_board_slug(board)
    except (TypeError, AttributeError) as exc:
        return DutyResult(ok=False, summary=f"deploy static: refused — malformed --board: {exc}")
    if not board_valid:
        return DutyResult(
            ok=False,
            summary=(
                f"deploy static: refused — --board {board!r} is missing or is not a valid "
                "filesystem-safe slug (^[A-Za-z0-9_-]+$)"
            ),
        )

    panel_specs = getattr(ns, "panel", None) or []
    if not panel_specs:
        return DutyResult(
            ok=False,
            summary="deploy static: refused — no --panel given (at least one is required)",
        )

    panels: list[StaticPanel] = []
    for raw in panel_specs:
        try:
            has_separator = "=" in raw
            label, _, path_str = raw.partition("=")
            label = label.strip()
        except (TypeError, AttributeError) as exc:
            return DutyResult(ok=False, summary=f"deploy static: refused — malformed --panel entry: {exc}")
        if not has_separator:
            return DutyResult(
                ok=False,
                summary=f"deploy static: refused — --panel {raw!r} is malformed (expected LABEL=PATH)",
            )
        if not label:
            return DutyResult(ok=False, summary=f"deploy static: refused — --panel {raw!r} has an empty label")
        try:
            panel_html = Path(path_str).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return DutyResult(ok=False, summary=f"deploy static: refused — could not read --panel {raw!r}: {exc}")
        try:
            panels.append(StaticPanel(label=label, html=panel_html))
        except (TypeError, ValueError) as exc:
            return DutyResult(ok=False, summary=f"deploy static: refused — invalid --panel {raw!r}: {exc}")

    try:
        index_html = render_static_index(panels, board=board)
    except ValueError as exc:
        return DutyResult(ok=False, summary=f"deploy static: refused — {exc}")

    output_dir = repo_root() / _DASHBOARD_RELATIVE_PATH / board
    try:
        safe = _is_board_output_dir_safe_to_write(output_dir)
    except OSError as exc:
        return DutyResult(ok=False, summary=f"deploy static: refused — could not inspect {output_dir}: {exc}")
    if not safe:
        return DutyResult(
            ok=False,
            summary=(
                f"deploy static: refused — {output_dir} already contains content this verb "
                "did not write; refusing to overwrite foreign content"
            ),
        )

    tmp_path = output_dir / _STATIC_INDEX_TMP_FILENAME
    final_path = output_dir / _STATIC_INDEX_FILENAME

    if _is_path_gitignored(final_path, cwd=repo_root()):
        return DutyResult(
            ok=False,
            summary=(
                f"deploy static: refused — {final_path} is excluded by a .gitignore rule, "
                f"so it could never be committed; "
                f"choose a --board slug that is not gitignored (got {board!r})"
            ),
        )

    created_dirs: list[Path] = []
    try:
        output_dir_existed = output_dir.exists()
        if output_dir_existed:
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            probe = output_dir
            while not probe.exists():
                created_dirs.append(probe)
                probe = probe.parent
            # No `exist_ok=True` on this branch — a symlink raced into this
            # exact path between the safety check above and this call now
            # raises `FileExistsError` (an OSError, already caught below)
            # instead of silently succeeding through it.
            output_dir.mkdir(parents=True)
        tmp_path.write_text(index_html, encoding="utf-8")
        tmp_path.rename(final_path)
    # `UnicodeEncodeError` is a `ValueError`, NOT an `OSError` — the exact
    # mirror-image of the `UnicodeDecodeError` case already handled on the
    # `--panel` READ above, and reachable through the real CLI: argv is
    # decoded with `surrogateescape`, so a non-UTF-8 byte in a `--panel`
    # LABEL survives into the rendered page as a lone surrogate and only
    # fails here, at encode time. Without this clause it escaped as an
    # uncaught crash (EXIT_INTERNAL) and skipped the cleanup below, leaving
    # a stray `index.html.tmp` behind — breaking this verb's own "refuse,
    # never crash" guarantee. Same refusal and same cleanup path.
    except (OSError, UnicodeEncodeError) as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        for directory in created_dirs:
            try:
                directory.rmdir()
            except OSError:
                pass
        return DutyResult(ok=False, summary=f"deploy static: refused — could not write to {output_dir}: {exc}")

    return DutyResult(ok=True, summary=f"deploy static: wrote {final_path}")


# ── DeployDuty (Duty-protocol adapter) ──────────────────────────────────────

_DEPLOY_VERBS: tuple[str, ...] = ("perimeter", "static", "nic")


class DeployDuty:
    """The real `deploy` duty — dispatches the `perimeter`/`static`/`nic` verbs.

    Bare `steward deploy` (no verb) degrades to `DutyResult(ok=True, ...)`
    naming the available verbs (AD-7), matching `KeysDuty`'s identical
    precedent. A subprocess failure is caught here as
    `subprocess.CalledProcessError` and reported as a duty-level failure,
    never conflated with an internal crash (AD-8 — that boundary is
    `cli.main()`'s alone).
    """

    name = "deploy"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "deploy_verb", None)
        if verb not in _DEPLOY_VERBS:
            return DutyResult(
                ok=True,
                summary=f"deploy: available verbs are {', '.join(_DEPLOY_VERBS)}",
            )
        try:
            if verb == "perimeter":
                return _run_perimeter(ns)
            if verb == "nic":
                from .deploy_nic import run_deploy_nic

                return run_deploy_nic(ns)
            return _run_static(ns)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            # The full command line names the step that failed, not just its program.
            cmd_name = " ".join(str(part) for part in exc.cmd) if exc.cmd else "subprocess"
            return DutyResult(
                ok=False,
                summary=f"deploy {verb}: `{cmd_name}` exited {exc.returncode}: {stderr}",
            )
