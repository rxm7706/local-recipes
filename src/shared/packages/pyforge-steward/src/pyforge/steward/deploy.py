"""Steward's `deploy` duty-adapter module (AD-1/AD-4) — Epic 2's single file,
mirrors `keys.py`'s "one module per duty" precedent.

Story 2.1 slice: `build_dashboard` — a thin `subprocess` wrap of the existing
`dashboard-gen` pixi task (`pixi run -e local-recipes dashboard-gen`), never a
reimplementation of `docs/dashboard/generate.py`'s own logic (AD-1). `DeployDuty`
is the `Duty`-conforming adapter `cli.py`'s `resolve_duty("deploy")` now
returns, wiring `steward deploy dashboard --build`.

Story 2.2 slice: `dashboard_diff` (git-diff the freshly built `docs/dashboard/`
tree against the committed one) and `commit_and_push_dashboard` (git add +
commit + push to the currently checked-out branch) — together the FR-9
reconciled-push behavior: bare `steward deploy dashboard` builds, diffs, and
only commits+pushes on a real difference (AD-4 — no daemon, no new workflow;
the operator or an existing workflow invokes the CLI).

Story 2.3 slice: `--dry-run` on the same `dashboard` verb — build+diff,
print, never commit/push. No new primitive; `_run_dashboard` just gains a
third branch alongside `--build`/bare-reconcile.

Story 2.4 slice: `last_deploy_commit` — reads the last commit that touched
`docs/dashboard/` straight from `git log` (no separate state file, per
FR-11). Wired as `steward deploy status`.

Story 5.2 slice: `_tracked_ledger_refusal` — a precondition guard on the
`dashboard` verb only (AD-71: Marshal produces and owns the sprint ledger's
currency; Steward must refuse rather than silently publish when its own
tracked ledger is missing or unreadable). The guard checks only the file's
presence and shape (a `development_status:` block exists) — never an
individual story-status value — so this module still performs zero status
derivation of its own (AD-1: that computation stays inside the wrapped
`dashboard-gen` subprocess / `docs/dashboard/generate.py`).

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
real Django/Channels object. Wired as `steward deploy perimeter`, a THIRD,
unrelated verb alongside the pre-existing `dashboard` (docs/dashboard-gen)
and `status` — reusing the `dashboard` name for this surface was flagged as
a live naming collision on Story 9.1's own deferred-work ledger.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .interfaces import DutyResult

# ── Repo-root resolution (mirrors `keys.py`'s `locate_http_module`/`repo_root`
# walk-up precedent, keyed on a marker this duty actually cares about rather
# than importing `keys.py` — that module's own top-level import reaches into
# `.claude/skills/conda-forge-expert/scripts/_http.py` and refuses to load
# outside a local-recipes checkout, which `cli.py`'s `resolve_duty` docstring
# already flags as a reason NOT to import it eagerly from an unrelated duty) ──

_DASHBOARD_GENERATE_MARKER = Path("docs/dashboard/generate.py")
_DASHBOARD_RELATIVE_PATH = Path("docs/dashboard")


def repo_root() -> Path:
    """Return the local-recipes checkout root.

    Walks up from this file's own resolved location looking for
    `docs/dashboard/generate.py` — robust to whatever depth the installed/
    editable `pyforge-steward` package ends up at relative to the repo root,
    same rationale as `keys.py`'s `locate_http_module`.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _DASHBOARD_GENERATE_MARKER).is_file():
            return ancestor
    raise RuntimeError(
        f"deploy.py: could not locate {_DASHBOARD_GENERATE_MARKER} by walking "
        f"up from {here} — this module must live inside a local-recipes checkout."
    )


# ── Build primitive (FR-8, Story 2.1) ───────────────────────────────────────

_DEFAULT_BUILD_CMD: tuple[str, ...] = ("pixi", "run", "-e", "local-recipes", "dashboard-gen")


def build_dashboard(
    *, cwd: str | Path, cmd: Sequence[str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the `dashboard-gen` pixi task as a subprocess (AD-1).

    `cmd` defaults to the real invocation (`pixi run -e local-recipes
    dashboard-gen`) — the exact pixi task named in `pixi.toml`'s
    `[feature.local-recipes.tasks.dashboard-gen]`. Overridable so a test can
    substitute a fast fixture command without installing the ~9.8GB
    `local-recipes` env (see this story's spec, "Design Notes").

    Raises `subprocess.CalledProcessError` on a non-zero exit — propagated,
    not swallowed — caught only at `DeployDuty`'s boundary (mirrors
    `KeysDuty`'s existing `age`-failure handling).
    """
    return subprocess.run(
        list(cmd) if cmd is not None else list(_DEFAULT_BUILD_CMD),
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


# ── Diff + reconciled push (FR-9, Story 2.2) ────────────────────────────────


def dashboard_diff(*, cwd: str | Path) -> str:
    """Return the `git diff` text for `docs/dashboard/` against the committed
    tree (unstaged changes to already-tracked files only — `dashboard-gen`
    only ever rewrites the existing tracked `data.js` in place, never adds a
    new file).

    Empty string means no diff. Raises `subprocess.CalledProcessError` if
    `git diff` itself fails (e.g. `cwd` is not a git worktree) — propagated,
    not swallowed.
    """
    result = subprocess.run(
        ["git", "diff", "--", str(_DASHBOARD_RELATIVE_PATH)],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def commit_and_push_dashboard(*, cwd: str | Path) -> str:
    """`git add` the `docs/dashboard/` diff, commit it (scoped to that same
    pathspec), and push to the currently checked-out branch on `origin` —
    direct push, no new Actions workflow (AD-4). Returns the new commit's
    full SHA.

    Review finding: the branch is now resolved (`git symbolic-ref --short
    HEAD`) FIRST, before any write -- a detached-HEAD checkout used to
    commit successfully and only fail resolving the push branch AFTER an
    orphan commit already existed, silently, with no record it was ever
    made once garbage-collected. Refusing before the commit means a
    detached-HEAD failure leaves the working tree exactly as it was.

    Review finding: `git commit` is now scoped to `-- docs/dashboard`
    (mirrors the preceding `git add`'s own pathspec) rather than a bare
    `git commit`, which commits the ENTIRE index regardless of what `git
    add` staged -- any unrelated file staged by the operator or another
    process sharing this working tree at call time would otherwise ride
    along into this commit and get pushed under a misleading message.

    Raises `subprocess.CalledProcessError` on any failing step (a detached
    HEAD with no branch, nothing to commit, a rejected push) — propagated,
    not swallowed, caught only at `DeployDuty`'s boundary, which now names
    the exact failing command (see `DeployDuty.run`) rather than a bare
    `"git"`. A push failure after a successful local commit is a known,
    accepted partial-completion state -- not rolled back here, but the next
    `deploy dashboard` invocation now detects and retries it (see
    `_push_pending_commit_if_ahead`) rather than silently reporting "nothing
    to deploy".
    """
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "add", "--", str(_DASHBOARD_RELATIVE_PATH)],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "dashboard: refresh status (steward deploy dashboard)",
         "--", str(_DASHBOARD_RELATIVE_PATH)],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "push", "origin", branch],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    return sha


def _push_pending_commit_if_ahead(*, cwd: str | Path) -> str | None:
    """Review finding: if an earlier `commit_and_push_dashboard` call
    committed successfully but its push failed, the local branch is left
    AHEAD of `origin` with a real, already-committed change. The next
    `steward deploy dashboard` run would previously build fresh content
    identical to what's already committed, see an EMPTY `dashboard_diff`
    (the working tree already matches the ahead-of-origin HEAD), and report
    "nothing to deploy" -- permanently hiding the earlier push failure;
    `deploy status` would also report the unpushed commit as if it were a
    completed deploy.

    Called before the diff check (never during `--dry-run`, which must
    never push): if HEAD is ahead of its upstream, push it now and return
    the pushed SHA. Returns `None` if not ahead (the ordinary case,
    including "no upstream configured" or a detached HEAD -- `@{u}`
    resolution failing here is treated as "cannot tell", not an error; the
    normal build/diff/commit flow's own git calls surface a clearer error
    if something about the checkout is genuinely broken).
    """
    ahead = subprocess.run(
        ["git", "rev-list", "--count", "@{u}..HEAD"],
        cwd=str(cwd), capture_output=True, text=True,
    )
    if ahead.returncode != 0:
        return None
    count = ahead.stdout.strip()
    if not count.isdigit() or int(count) == 0:
        return None
    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "push", "origin", branch],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    ).stdout.strip()


# ── Deploy status (FR-11, Story 2.4) ────────────────────────────────────────


@dataclass(frozen=True)
class DeployRecord:
    """The last commit that touched `docs/dashboard/` — SHA + committer
    timestamp, read straight from `git log`. No separate state file exists
    anywhere (FR-11's explicit constraint); this IS the record."""

    sha: str
    timestamp: str


_LOG_FORMAT = "%H\x1f%cI"  # full SHA + strict-ISO committer date, unit-separated


def last_deploy_commit(*, cwd: str | Path) -> DeployRecord | None:
    """Return the last commit touching `docs/dashboard/`, or `None` if none
    exists.

    Reads git history directly (`git log -1`) — never a separate state file
    (per FR-11's "no separate state store" constraint; see this story's
    spec, "Design Notes" for why no Steward-provenance filter is applied).

    Raises `subprocess.CalledProcessError` if `git log` itself fails (e.g.
    `cwd` is not a git worktree) — propagated, not swallowed.
    """
    result = subprocess.run(
        ["git", "log", "-1", f"--format={_LOG_FORMAT}", "--", str(_DASHBOARD_RELATIVE_PATH)],
        cwd=str(cwd), check=True, capture_output=True, text=True,
    )
    output = result.stdout.strip()
    if not output:
        return None
    sha, timestamp = output.split("\x1f")
    return DeployRecord(sha=sha, timestamp=timestamp)


# ── Tracked-ledger precondition (AD-71, Story 5.2) ──────────────────────────

_STEWARD_LEDGER_RELATIVE_PATH = Path(
    "_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml"
)


def _tracked_ledger_refusal(*, cwd: str | Path) -> str | None:
    """Return a refusal message if Steward's own tracked sprint ledger is
    missing, unreadable, or not shaped like a ledger — or `None` if it's fine
    to proceed.

    Physical path, never the `_bmad-output/planning-artifacts` symlink (that
    symlink is per-worktree global state and may point at a different
    project — see this repo's CLAUDE.md "PARALLEL AGENTS" section). Checks
    only presence and shape (a top-level `development_status:` line exists)
    — never an individual story key or status value, so this stays a
    precondition check, not the story-status derivation AD-1 forbids
    `deploy.py` from doing (that computation stays inside the wrapped
    `dashboard-gen` subprocess / `docs/dashboard/generate.py`).

    Review finding: the shape check used to be a bare substring test
    (`"development_status:" in text`), which a comment merely MENTIONING the
    key (or any longer identifier ending in it) would satisfy — the real
    consumer, `generate.py::parse_sprint_status`, only recognizes a line
    whose STRIPPED text equals `"development_status:"` exactly. A ledger
    that passed the old check could still parse to zero statuses downstream,
    exactly the silent-invisibility this guard exists to prevent. Now
    matches that same line-exact rule.
    """
    ledger = Path(cwd) / _STEWARD_LEDGER_RELATIVE_PATH
    if not ledger.is_file():
        return f"tracked ledger not found at {ledger}"
    try:
        text = ledger.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # Review finding: `UnicodeDecodeError` (invalid-encoding ledger
        # content) is a `ValueError`, not an `OSError` -- excluding it left
        # a corrupt-encoding ledger crashing uncaught instead of refusing.
        return f"tracked ledger unreadable at {ledger}: {exc}"
    if not any(line.strip() == "development_status:" for line in text.splitlines()):
        return f"tracked ledger at {ledger} has no development_status: block"
    return None


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


class UnshareableStateError(ValueError):
    """AD-5: a cross-worker-unshareable backend was declared while
    `worker_count > 1` — the response cache or the Channels channel layer
    cannot actually deliver the property (one upstream fetch; every viewer
    sees a broadcast) the deployment claims to have."""


# AD-5's allowlist (fail-closed): only backends this story can cite as
# genuinely cross-process-shared. Judgment call, recorded here rather than
# assumed (this story's spec leaves the exact class path(s) open): the
# architecture's Spec companion says "Redis-backed cache classes" (plural),
# so this allowlists BOTH Django's own built-in Redis backend (4.0+, the
# upstream-recommended choice today) and `django-redis`, the long-established
# third-party alternative many existing deployments already carry — matching
# names exactly, not by prefix, so a project-specific subclass of either is
# refused rather than silently trusted (`cache.py`'s own docstring: only a
# backend this module can actually vouch for is accepted). The channel-layer
# allowlist stays to the ONE class the architecture Stack table names by its
# own words as "the sanctioned layer backend" — widening it to
# `channels_redis`'s other shipped layer class was deliberately not done,
# to avoid allowlisting something neither the Spec nor the architecture
# actually named.
_SHAREABLE_CACHE_BACKENDS: tuple[str, ...] = (
    "django.core.cache.backends.redis.RedisCache",
    "django_redis.cache.RedisCache",
)
_SHAREABLE_CHANNEL_LAYER_BACKENDS: tuple[str, ...] = (
    "channels_redis.core.RedisChannelLayer",
)


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
# The spec's own Code Map names no CLI flag for the ASGI application import
# path, and this story renders plain text with no templating engine — so
# rather than invent an unrequested flag, the adopter edits this one
# placeholder line by hand, same as any other systemd unit before enabling
# it (judgment call, recorded here).
_ASGI_APPLICATION_PLACEHOLDER = "myproject.asgi:application"  # adopter fills in


def _worker_ports(topology: DeploymentTopology, *, base_port: int) -> tuple[int, ...]:
    """The bind ports both `render_daphne_unit`'s enable-command comment and
    `render_edge_config`'s nginx upstream block derive from — the single
    source both functions read, so the two rendered manifests can never
    independently drift out of step on how many workers/ports there are.
    One port per worker, sequential from `base_port`.
    """
    return tuple(base_port + i for i in range(topology.worker_count))


def render_daphne_unit(
    topology: DeploymentTopology,
    *,
    base_port: int = _DEFAULT_BASE_PORT,
    bind_host: str = _DEFAULT_BIND_HOST,
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
    return f"""# pyforge-steward[dashboard] — daphne ASGI worker fleet (Story 9.5, CAP-6/AD-5/AD-8)
# Template unit: one instance per worker, named by the port it binds. Enable
# the full fleet for this topology (worker_count={topology.worker_count}) with:
#   systemctl enable --now {enable_cmd}
#
# Replace {_ASGI_APPLICATION_PLACEHOLDER} below with your project's real
# ASGI application import path before enabling.

[Unit]
Description=pyforge-steward dashboard daphne worker on port %i
After=network.target

[Service]
Type=simple
ExecStart=daphne --bind {bind_host} --port %i --proxy-headers {_ASGI_APPLICATION_PLACEHOLDER}
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
"""


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

    `trusted_addresses`/`tls_cert`/`tls_key` are plain strings/CLI input —
    this function never imports `TrustedIngress` from
    `dashboard/declarations.py` (the import-boundary invariant forbids this
    module from reaching into `dashboard/` at all), so no address-form or
    header-name validation runs here beyond the emptiness check below.
    `server_name` defaults to nginx's own `_` catch-all convention — the
    adopter is expected to replace it with a real domain.

    `X-Forwarded-For` is set by OVERWRITING with `$remote_addr`, never
    `$proxy_add_x_forwarded_for` (which APPENDS) — judgment call, recorded
    here: `dashboard/middleware.py`'s own module docstring names an
    appending proxy as defeating AD-4's ingress check entirely, since a
    client-supplied `X-Forwarded-For` entry then survives as the leftmost
    one daphne's `--proxy-headers` parsing reads. This edge config is the
    other half of that documented deployment precondition.

    Raises `ValueError` if `trusted_addresses` is empty — a network-policy
    block with nothing to allow enforces nothing while looking like it does
    (mirrors `TrustedIngress.addresses`'s own non-empty requirement without
    importing that class, per the import-boundary note above).
    """
    if not trusted_addresses:
        raise ValueError(
            "render_edge_config: trusted_addresses must not be empty — an "
            "edge config with no declared trusted ingress restricts access "
            "to nothing while appearing to enforce a network policy"
        )

    ports = _worker_ports(topology, base_port=base_port)
    upstream_name = "pyforge_steward_dashboard_workers"
    upstream_servers = "\n".join(f"    server {bind_host}:{p};" for p in ports)
    allow_lines = "\n".join(f"    allow {addr};" for addr in trusted_addresses)

    return f"""# pyforge-steward[dashboard] — nginx edge (Story 9.5, CAP-6/AD-4/AD-8)
# TLS termination + network-policy restriction to the declared trusted
# ingress; proxies to the daphne worker fleet render_daphne_unit renders.

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
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        # Overwrite, never append -- see this function's docstring.
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""


def _run_perimeter(ns: argparse.Namespace) -> DutyResult:
    """`deploy perimeter --workers N --cache-backend PATH
    --channel-layer-backend PATH [--trusted-address ADDR ...] [--tls-cert
    PATH --tls-key PATH] [--output-dir DIR]`.

    Always validates first: `DeploymentTopology`'s own construction-time
    checks, then `check_shareable_state` (AD-5). Either's `TypeError`/
    `ValueError` is caught here and reported as a named duty-level refusal
    — never an uncaught crash (AD-8's boundary stays `cli.main()`'s alone).
    A topology that fails the check writes NOTHING (I/O matrix).

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
    except (TypeError, ValueError) as exc:
        return DutyResult(ok=False, summary=f"deploy perimeter: refused — {exc}")

    output_dir = getattr(ns, "output_dir", None)
    if not output_dir:
        return DutyResult(
            ok=True,
            summary=(
                "deploy perimeter: topology valid "
                f"(workers={topology.worker_count}, "
                f"cache_backend={topology.cache_backend!r}, "
                f"channel_layer_backend={topology.channel_layer_backend!r}) "
                "— no --output-dir given, nothing written"
            ),
        )

    trusted_addresses = tuple(getattr(ns, "trusted_address", None) or ())
    tls_cert = getattr(ns, "tls_cert", None)
    tls_key = getattr(ns, "tls_key", None)
    missing = [
        flag
        for flag, value in (
            ("--trusted-address", trusted_addresses),
            ("--tls-cert", tls_cert),
            ("--tls-key", tls_key),
        )
        if not value
    ]
    if missing:
        return DutyResult(
            ok=False,
            summary=(
                "deploy perimeter: refused — --output-dir was given but "
                f"{', '.join(missing)} was not supplied; an edge config "
                "cannot be rendered without a declared trusted ingress and "
                "a TLS certificate/key pair"
            ),
        )

    unit_text = render_daphne_unit(topology)
    edge_text = render_edge_config(
        topology,
        trusted_addresses=trusted_addresses,
        tls_cert=tls_cert,
        tls_key=tls_key,
    )

    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "pyforge-steward-dashboard@.service").write_text(unit_text, encoding="utf-8")
        (output_path / "pyforge-steward-dashboard.nginx.conf").write_text(edge_text, encoding="utf-8")
    except OSError as exc:
        return DutyResult(
            ok=False, summary=f"deploy perimeter: refused — could not write to {output_path}: {exc}"
        )

    return DutyResult(
        ok=True,
        summary=f"deploy perimeter: rendered daphne unit + nginx edge config to {output_path}",
    )


# ── DeployDuty (Duty-protocol adapter) ──────────────────────────────────────

_DEPLOY_VERBS: tuple[str, ...] = ("dashboard", "status", "perimeter")


def _run_dashboard(ns: argparse.Namespace) -> DutyResult:
    """`deploy dashboard [--build] [--dry-run]`.

    `--build` always wins over `--dry-run` if both are passed (build-only is
    the narrower operation; ACs don't define combining them, so this is a
    documented judgment call, not a silent one — see this story's spec,
    "Design Notes") — builds and returns without ever computing a diff.

    Otherwise: build, then diff `docs/dashboard/` against the committed
    tree. No diff → `ok=True`, "nothing to deploy", regardless of
    `--dry-run` (FR-9's zero-commit-on-no-diff property). A real diff with
    `--dry-run` → the diff is printed; `commit_and_push_dashboard` is never
    called, so `git log`/`git status` are left unchanged. A real diff with
    neither flag → commit + push (Story 2.2's FR-9 reconciled-push
    behavior).

    Story 5.2: refuses before any of the above if Steward's own tracked
    sprint ledger is missing, unreadable, or unshaped (AD-71) — named,
    not a silent fallback; `build_dashboard()` is never reached.
    """
    root = repo_root()
    refusal = _tracked_ledger_refusal(cwd=root)
    if refusal is not None:
        return DutyResult(ok=False, summary=f"deploy dashboard: refused — {refusal}")

    build_dashboard(cwd=root)

    if getattr(ns, "build", False):
        return DutyResult(ok=True, summary="deploy dashboard: build complete (docs/dashboard/ refreshed)")

    if not getattr(ns, "dry_run", False):
        # Review finding: check for (and retry) an earlier run's unpushed
        # commit BEFORE the diff-based no-op check below -- otherwise a
        # stuck unpushed commit permanently masquerades as "nothing to
        # deploy" forever (see `_push_pending_commit_if_ahead`'s own
        # docstring). Never runs during `--dry-run`, which must never push.
        pending_sha = _push_pending_commit_if_ahead(cwd=root)
        if pending_sha is not None:
            return DutyResult(
                ok=True,
                summary=(
                    f"deploy dashboard: pushed previously-committed {pending_sha} "
                    "(an earlier run's push had failed and was retried)"
                ),
            )

    diff_text = dashboard_diff(cwd=root)
    if not diff_text.strip():
        return DutyResult(ok=True, summary="deploy dashboard: no diff — nothing to deploy")

    if getattr(ns, "dry_run", False):
        return DutyResult(
            ok=True,
            summary=f"deploy dashboard: pending diff (dry-run, not committed):\n{diff_text}",
        )

    sha = commit_and_push_dashboard(cwd=root)
    return DutyResult(ok=True, summary=f"deploy dashboard: committed and pushed {sha}")


def _run_status(ns: argparse.Namespace) -> DutyResult:  # noqa: ARG001 -- no flags yet
    """`deploy status` — reports the last commit touching `docs/dashboard/`.

    Review finding: previously reported the last commit's SHA/timestamp
    unconditionally, even if that commit was never actually pushed (a prior
    `deploy dashboard` committed but its push failed) -- misreporting a
    local-only commit as a completed deploy. Now appends an explicit note
    when HEAD is ahead of its upstream, using the SAME `@{u}`-based check
    `_push_pending_commit_if_ahead` uses (read-only here -- `status` never
    pushes) -- still no separate state file (FR-11)."""
    root = repo_root()
    record = last_deploy_commit(cwd=root)
    if record is None:
        return DutyResult(ok=True, summary="deploy status: no dashboard deploy commit found in git history")
    ahead = subprocess.run(
        ["git", "rev-list", "--count", "@{u}..HEAD"],
        cwd=str(root), capture_output=True, text=True,
    )
    unpushed_note = ""
    if ahead.returncode == 0:
        count = ahead.stdout.strip()
        if count.isdigit() and int(count) > 0:
            unpushed_note = " -- HEAD is ahead of origin; the most recent commit(s) may not be pushed yet"
    return DutyResult(
        ok=True,
        summary=f"deploy status: last deploy {record.sha} at {record.timestamp}{unpushed_note}",
    )


class DeployDuty:
    """The real `deploy` duty — dispatches the `dashboard`/`status`/`perimeter` verbs.

    Bare `steward deploy` (no verb) degrades to `DutyResult(ok=True, ...)`
    naming the available verbs (AD-7), matching `KeysDuty`'s identical
    precedent. A subprocess failure (pixi, git) is caught here as
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
            if verb == "dashboard":
                return _run_dashboard(ns)
            if verb == "perimeter":
                return _run_perimeter(ns)
            return _run_status(ns)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            # Review finding: `exc.cmd[0]` was always the literal string
            # "git" (every subprocess call in this module starts with it),
            # so the summary never actually named which step failed despite
            # this module's own docstrings claiming per-step attribution.
            # The full command line does.
            cmd_name = " ".join(str(part) for part in exc.cmd) if exc.cmd else "subprocess"
            return DutyResult(
                ok=False,
                summary=f"deploy {verb}: `{cmd_name}` exited {exc.returncode}: {stderr}",
            )
