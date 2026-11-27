"""``steward deploy nic validate|up|kubeconfig|outputs|down`` — NKP on kind (CAP-176, Story 118.1).

Wraps ``nic validate|deploy|kubeconfig|outputs|destroy`` by subprocess (AD-1) over a tracked
config under ``src/platform/deploy/nic/``. Operator credentials are read from an untracked
``.env`` at the repo root: each ``NAME=relative/path.age`` line names an age-encrypted secret
file decrypted through ``keys.decrypt_file`` (spec-pyforge-steward CAP-1) — never ``os.environ[NAME]`` on the
parent process. Each run appends ``{verb, config, seconds, exit}`` to
``.steward/nic-deploy.jsonl``. Returns ``DutyResult`` only (AD-8); the kill switch is
``pyforge.steward.nkp_deploy`` (wired through ``cli.RETROFIT_KEY_VERBS``). ``down`` runs
``nic destroy --auto-approve``: ``nic destroy`` otherwise asks ``Type 'yes' to confirm`` and
dies with ``failed to read user input: EOF`` under a subprocess, and the explicit ``down``
action behind the kill switch is the consent (Story 118.4).

Story 118.9 (spec-pyforge-steward CAP-178, CAP-176) guards the cloud GitOps branch before
any cloud run: a ``repository.existing`` config is refused, for every action and before
``nic`` starts, when ``pyforge.steward.nkp_gitops_branch`` is OFF, when its branch is not
exactly ``gitops/<project_name>`` (``main`` included), when its auth is not
``auth.ssh.env: GITOPS_DEPLOY_KEY``, or when its URL names another repository than
``origin``; a config on any provider but local kind is refused without a
``repository.existing``; an ``up`` on any provider but local kind refuses without the
operator's ``--yes``; ``GITOPS_DEPLOY_KEY`` resolves only with its
``.steward/keys-inventory.yaml`` row; the summary carries ``nic``'s last line only redacted;
and after a cloud ``up`` the range ``origin/main..origin/<branch>`` is scanned for a
secret-shaped value with the ``keys audit --secrets`` pattern table.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml

from .interfaces import DutyResult

NKP_DEPLOY_FLAG = "pyforge.steward.nkp_deploy"
NKP_GITOPS_BRANCH_FLAG = "pyforge.steward.nkp_gitops_branch"
GITOPS_BRANCH_PREFIX = "gitops/"
# A gitops branch is checked raw (never stripped): ``gitops/`` then ref-safe segments.
_GITOPS_BRANCH_SHAPE = re.compile(r"gitops/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*")
GITOPS_DEPLOY_KEY = "GITOPS_DEPLOY_KEY"
# The one auth a repository.existing config may name: nic's deploy key, which keys gates on its row.
GITOPS_AUTH: dict[str, Any] = {"ssh": {"env": GITOPS_DEPLOY_KEY}}
# The GitHub remote spellings compared with origin (owner and repository, case-insensitive).
_GITHUB_REMOTE = re.compile(
    r"(?i)(?:git@github\.com:|ssh://git@github\.com/|https://github\.com/)([^/\s]+)/([^/\s]+?)(?:\.git)?/?"
)
JOURNAL_RELATIVE = Path(".steward/nic-deploy.jsonl")
DOTENV_RELATIVE = Path(".env")
# Credentials that resolve only with an issued row in the keys inventory (Story 118.9, CAP-178).
INVENTORIED_CREDENTIALS: frozenset[str] = frozenset({GITOPS_DEPLOY_KEY})

NIC_ACTIONS: tuple[str, ...] = ("validate", "up", "kubeconfig", "outputs", "down")
_NIC_SUBCOMMAND: dict[str, str] = {
    "validate": "validate",
    "up": "deploy",
    "kubeconfig": "kubeconfig",
    "outputs": "outputs",
    "down": "destroy",
}
_NIC_EXTRA_ARGS: dict[str, tuple[str, ...]] = {
    "down": ("--auto-approve",),
}


class _Completed(Protocol):
    args: list[str] | str
    returncode: int
    stdout: str
    stderr: str


SubprocessRunner = Callable[[list[str], Path, dict[str, str]], _Completed]
DecryptSecret = Callable[[Path, Path], str]


def repo_root() -> Path:
    from .deploy import repo_root as deploy_repo_root

    return deploy_repo_root()


def _collect_env_names(node: object, found: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "env" and isinstance(value, str) and value.strip():
                found.add(value.strip())
            else:
                _collect_env_names(value, found)
    elif isinstance(node, list):
        for item in node:
            _collect_env_names(item, found)


def operator_env_names(document: object) -> frozenset[str]:
    """Env var names the NIC config declares (``auth.*.env`` fields)."""
    found: set[str] = set()
    _collect_env_names(document, found)
    return frozenset(found)


def _parse_dotenv_manifest(path: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition("=")
        if not sep:
            continue
        name = key.strip()
        if not name:
            continue
        mapping[name] = Path(value.strip())
    return mapping


def _default_age_identity(root: Path) -> Path | None:
    from .keys import default_inventory_path, load_inventory

    raw = os.environ.get("SOPS_AGE_KEY_FILE")
    if raw:
        candidate = Path(raw).expanduser()
        if candidate.is_file():
            return candidate
    for entry in load_inventory(default_inventory_path()):
        if entry.status == "active" and entry.provenance == "issued" and entry.identity_path:
            identity = Path(entry.identity_path).expanduser()
            if identity.is_file():
                return identity
    return None


def _decrypt_age_secret(age_path: Path, identity: Path) -> str:
    from .keys import decrypt_file

    plaintext = age_path.with_suffix(age_path.suffix + ".plain")
    try:
        decrypt_file(age_path, identity=identity, output=plaintext)
        value = plaintext.read_text(encoding="utf-8").strip()
    finally:
        plaintext.unlink(missing_ok=True)
    return value


def load_secret_env(
    root: Path,
    *,
    env_file: Path,
    required: frozenset[str],
    decrypt: DecryptSecret | None = None,
    inventory: Path | None = None,
) -> tuple[dict[str, str] | None, DutyResult | None]:
    """Resolve ``required`` names from ``env_file`` through age decryption (keys), not the shell.

    A name in ``INVENTORIED_CREDENTIALS`` is refused first, before ``.env`` is read, unless the
    keys inventory holds its issued row (Story 118.9, AC5).
    """
    from .cli import EXIT_USAGE
    from .keys import issued_row_refusal

    if not required:
        return {}, None
    for name in sorted(required & INVENTORIED_CREDENTIALS):
        reason = issued_row_refusal(name, inventory)
        if reason is not None:
            return None, DutyResult(
                ok=False,
                summary=f"deploy nic: refused — keys will not resolve {name}: {reason}",
                details={"exit_code": EXIT_USAGE},
            )
    if not env_file.is_file():
        return None, DutyResult(
            ok=False,
            summary=(
                f"deploy nic: refused — {DOTENV_RELATIVE} is missing; "
                f"the config requires {', '.join(sorted(required))} through keys"
            ),
            details={"exit_code": EXIT_USAGE},
        )
    identity = _default_age_identity(root)
    if identity is None:
        return None, DutyResult(
            ok=False,
            summary=(
                "deploy nic: refused — no age identity (set SOPS_AGE_KEY_FILE or "
                "record an issued identity in .steward/keys-inventory.yaml)"
            ),
            details={"exit_code": EXIT_USAGE},
        )
    decrypt_fn = decrypt or _decrypt_age_secret
    manifest = _parse_dotenv_manifest(env_file)
    resolved: dict[str, str] = {}
    for name in sorted(required):
        rel = manifest.get(name)
        if rel is None:
            return None, DutyResult(
                ok=False,
                summary=(
                    f"deploy nic: refused — {DOTENV_RELATIVE} does not map {name!r} to an age-encrypted secret path"
                ),
                details={"exit_code": EXIT_USAGE},
            )
        age_path = rel if rel.is_absolute() else root / rel
        if not age_path.is_file():
            return None, DutyResult(
                ok=False,
                summary=f"deploy nic: refused — secret file {age_path} for {name!r} is missing",
                details={"exit_code": EXIT_USAGE},
            )
        try:
            resolved[name] = decrypt_fn(age_path, identity)
        except OSError as exc:
            return None, DutyResult(
                ok=False,
                summary=f"deploy nic: refused — cannot decrypt {name!r} through keys: {exc}",
                details={"exit_code": EXIT_USAGE},
            )
    return resolved, None


def _append_journal(root: Path, record: dict[str, Any]) -> None:
    path = root / JOURNAL_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _default_runner(argv: list[str], cwd: Path, env: dict[str, str]) -> _Completed:
    import subprocess

    return subprocess.run(  # noqa: S603
        argv,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _origin_url(root: Path) -> str | None:
    """``origin``'s URL in the checkout at ``root``, or ``None`` when git cannot name it."""
    import subprocess

    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "remote", "get-url", "origin"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    url = proc.stdout.strip()
    return url if proc.returncode == 0 and url else None


def _nic_binary() -> str | None:
    prefix = os.environ.get("CONDA_PREFIX")
    if prefix:
        candidate = Path(prefix) / "bin" / "nic"
        if candidate.is_file():
            return str(candidate)
    return shutil.which("nic")


@dataclass
class NicDeps:
    root: Path
    runner: SubprocessRunner
    nic_executable: Callable[[], str | None] = field(default=_nic_binary)
    decrypt: DecryptSecret | None = None
    journal: Callable[[dict[str, Any]], None] | None = None
    monotonic: Callable[[], float] = time.monotonic
    inventory: Path | None = None  # the keys inventory; None reads the repo-root one
    origin_url: Callable[[Path], str | None] = field(default=_origin_url)


def _production_deps(root: Path) -> NicDeps:
    return NicDeps(
        root=root,
        runner=_default_runner,
        journal=lambda record: _append_journal(root, record),
    )


def _load_config(config_path: Path) -> tuple[dict[str, Any] | None, DutyResult | None]:
    from .cli import EXIT_USAGE

    if not config_path.is_file():
        return None, DutyResult(
            ok=False,
            summary=f"deploy nic: refused — config {config_path} does not exist",
            details={"exit_code": EXIT_USAGE},
        )
    try:
        document = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return None, DutyResult(
            ok=False,
            summary=f"deploy nic: refused — config {config_path} is not valid YAML: {exc}",
            details={"exit_code": EXIT_USAGE},
        )
    if not isinstance(document, dict):
        return None, DutyResult(
            ok=False,
            summary=f"deploy nic: refused — config {config_path} must be a YAML mapping",
            details={"exit_code": EXIT_USAGE},
        )
    return document, None


def _usage_refusal(summary: str) -> DutyResult:
    from .cli import EXIT_USAGE

    return DutyResult(ok=False, summary=summary, details={"exit_code": EXIT_USAGE})


def _existing_repository(document: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """``repository.existing`` as a mapping (``{}`` when it is not one), ``None`` when absent."""
    repository = document.get("repository")
    if not isinstance(repository, Mapping) or "existing" not in repository:
        return None
    existing = repository.get("existing")
    return existing if isinstance(existing, Mapping) else {}


def existing_repository_branch(document: Mapping[str, Any]) -> str | None:
    """The raw ``repository.existing.branch`` (never stripped), ``""`` when it names none, ``None`` off ``existing``."""
    existing = _existing_repository(document)
    if existing is None:
        return None
    branch = existing.get("branch")
    return branch if isinstance(branch, str) else ""


def _project_name(document: Mapping[str, Any]) -> str | None:
    """The config's ``project_name``, as ``gitops_root_for`` reads it, or ``None`` when it names none."""
    project = document.get("project_name")
    return project.strip() if isinstance(project, str) and project.strip() else None


def gitops_branch_problem(branch: str, project_name: str | None) -> str | None:
    """Why ``branch`` is not the cloud GitOps branch, or ``None`` when it is (Story 118.9 AC2).

    The raw value must be ``gitops/`` and ref-safe segments (no whitespace, ``:``, empty segment,
    ``..``, leading-``.`` segment or ``.lock`` suffix), and ``gitops/<project_name>`` exactly when
    the config names a project.
    """
    if not _GITOPS_BRANCH_SHAPE.fullmatch(branch):
        return f"is not a {GITOPS_BRANCH_PREFIX}<name> ref name"
    if ".." in branch or any(part.startswith(".") or part.endswith(".lock") for part in branch.split("/")):
        return "is not a valid ref name"
    if project_name is not None and branch != f"{GITOPS_BRANCH_PREFIX}{project_name}":
        return f"is not {GITOPS_BRANCH_PREFIX}{project_name}, the branch project_name {project_name!r} names"
    return None


def refuse_gitops_branch(document: Mapping[str, Any]) -> DutyResult | None:
    """Story 118.9 AC2/AC3: refuse a cloud config's GitOps source before ``nic`` starts, every action.

    A config on any provider but local kind must name ``repository.existing`` (CAP-178: the cloud
    GitOps source is the gitops branch). OFF ``pyforge.steward.nkp_gitops_branch`` refuses every
    ``repository.existing`` config; ON, its branch must be exactly ``gitops/<project_name>`` (never
    ``main``) and its auth exactly ``auth.ssh.env: GITOPS_DEPLOY_KEY``, the credential keys gates on
    its inventory row. kind's ``repository.local`` is never refused here.
    """
    from pyforge.core.flags import read_boolean

    existing = _existing_repository(document)
    if existing is None:
        if is_local_kind(document):
            return None
        return _usage_refusal(
            "deploy nic: refused — a config on a provider other than local kind needs repository.existing; "
            "the cloud GitOps source is gitops/<project_name> on this repository (CAP-178)"
        )
    if not read_boolean(NKP_GITOPS_BRANCH_FLAG, default=True):
        return _usage_refusal(
            f"deploy nic: refused — {NKP_GITOPS_BRANCH_FLAG} is off, so no repository.existing config runs"
        )
    branch = existing_repository_branch(document) or ""
    problem = gitops_branch_problem(branch, _project_name(document))
    if problem is not None:
        return _usage_refusal(
            f"deploy nic: refused — repository.existing.branch {branch!r} {problem}; "
            "the cloud GitOps source is gitops/<project_name>, never main"
        )
    if existing.get("auth") != GITOPS_AUTH:
        return _usage_refusal(
            f"deploy nic: refused — repository.existing.auth must be exactly auth.ssh.env: {GITOPS_DEPLOY_KEY} "
            "(nic's deploy key, which keys resolves only with its inventory row); another env name or a token "
            "is not accepted"
        )
    return None


def github_owner_repo(url: str) -> tuple[str, str] | None:
    """``(owner, repo)`` lower-cased from a GitHub remote URL, ``None`` for any other URL."""
    match = _GITHUB_REMOTE.fullmatch(url.strip())
    return (match[1].lower(), match[2].lower()) if match else None


def refuse_foreign_repository(deps: NicDeps, document: Mapping[str, Any]) -> DutyResult | None:
    """Story 118.9 AC4: a ``repository.existing.url`` must be ``origin``'s repository.

    The post-``up`` scan fetches and reads ``origin``, so a URL naming another repository would
    leave the branch ``nic`` pushed unscanned. Refused before ``nic`` starts; ``None`` off ``existing``.
    """
    existing = _existing_repository(document)
    if existing is None:
        return None
    url = existing.get("url")
    named = github_owner_repo(url) if isinstance(url, str) else None
    if named is None:
        return _usage_refusal(
            f"deploy nic: refused — repository.existing.url {url!r} is not a GitHub repository URL steward can "
            "compare with origin"
        )
    origin = deps.origin_url(deps.root)
    ours = github_owner_repo(origin) if origin else None
    if ours is None:
        return _usage_refusal(
            f"deploy nic: refused — origin's URL {origin!r} is not a GitHub repository steward can compare with "
            "repository.existing.url, so the post-up scan could not read the branch nic pushes"
        )
    if named != ours:
        return _usage_refusal(
            f"deploy nic: refused — repository.existing.url names {'/'.join(named)}, but origin is "
            f"{'/'.join(ours)}; the post-up scan reads origin, so the cloud GitOps source must be origin's repository"
        )
    return None


def is_local_kind(document: Mapping[str, Any]) -> bool:
    """True when the config's only cluster provider is ``local`` (kind)."""
    cluster = document.get("cluster")
    return isinstance(cluster, Mapping) and set(cluster) == {"local"}


def refuse_without_consent(document: Mapping[str, Any], *, action: str, yes: bool) -> DutyResult | None:
    """Story 118.9 AC6: ``up`` on any provider but local kind runs only under the operator's ``--yes``."""
    if action != "up" or yes or is_local_kind(document):
        return None
    return _usage_refusal(
        "deploy nic: refused — up on a provider other than local kind needs the operator's --yes "
        "(an agent's --yes is denied by session_denials steward-deploy-nic-up-yes)"
    )


def scan_gitops_range(deps: NicDeps, branch: str) -> DutyResult | None:
    """Story 118.9 AC4: after a cloud ``up``, scan ``origin/main..origin/<branch>`` for a secret-shaped value.

    ``nic`` commits the cloud tree inside its own clone, so no hook of ours sees it; this reads the
    pushed range back. A range that cannot be read fails closed. Returns ``None`` when clean.
    """
    from .cli import EXIT_FAILED
    from .keys import scan_text_for_secrets

    tracking = f"refs/remotes/origin/{branch}"
    span = f"origin/main..origin/{branch}"
    env = dict(os.environ)
    fetch = deps.runner(
        [
            "git",
            "fetch",
            "--no-tags",
            "origin",
            "+refs/heads/main:refs/remotes/origin/main",
            f"+refs/heads/{branch}:{tracking}",
        ],
        deps.root,
        env,
    )
    log = (
        deps.runner(
            [
                "git",
                "log",
                "-p",
                # Every commit's whole diff: binary blobs as text, no external diff or textconv
                # driver, and a merge against its first parent (a plain `log -p` shows none).
                "--text",
                "--no-ext-diff",
                "--no-textconv",
                "--diff-merges=first-parent",
                "--no-color",
                "--format=commit %H",
                span,
            ],
            deps.root,
            env,
        )
        if fetch.returncode == 0
        else fetch
    )
    if log.returncode != 0:
        return DutyResult(
            ok=False,
            summary=f"deploy nic up: the secret scan could not read {span} (git exited {log.returncode})",
            details={"exit_code": EXIT_FAILED},
        )
    findings = scan_text_for_secrets(log.stdout or "", span)
    if not findings:
        return None
    named = "; ".join(sorted({f"line {f.line}: {f.pattern_name}" for f in findings}))
    return DutyResult(
        ok=False,
        summary=f"deploy nic up: {span} carries a secret-shaped value ({named}); rotate it and rewrite the branch",
        details={"exit_code": EXIT_FAILED, "secret_findings": len(findings)},
    )


def run_nic(deps: NicDeps, *, action: str, config: Path, yes: bool = False) -> DutyResult:
    from .cli import EXIT_USAGE
    from .keys import redact_secret_shapes

    if action not in NIC_ACTIONS:
        return DutyResult(
            ok=False,
            summary=f"deploy nic: unknown action {action!r}; expected one of {', '.join(NIC_ACTIONS)}",
            details={"exit_code": EXIT_USAGE},
        )
    config_path = config if config.is_absolute() else deps.root / config
    document, failure = _load_config(config_path)
    if failure is not None:
        return failure
    assert document is not None
    refused = (
        refuse_gitops_branch(document)
        or refuse_foreign_repository(deps, document)
        or refuse_without_consent(document, action=action, yes=yes)
    )
    if refused is not None:
        return refused
    required = operator_env_names(document)
    env_file = deps.root / DOTENV_RELATIVE
    secret_env, failure = load_secret_env(
        deps.root, env_file=env_file, required=required, decrypt=deps.decrypt, inventory=deps.inventory
    )
    if failure is not None:
        return failure
    assert secret_env is not None
    nic = deps.nic_executable()
    if not nic:
        return DutyResult(
            ok=False,
            summary="deploy nic: refused — nic is not installed in the pixi environment (CONDA_PREFIX/bin/nic)",
            details={"exit_code": EXIT_USAGE},
        )
    if action == "up":
        from .deploy_nic_packs import preflight_pack_clis

        refused = preflight_pack_clis(document)
        if refused is not None:
            return refused
    subcommand = _NIC_SUBCOMMAND[action]
    argv = [nic, subcommand, "-f", str(config_path), *_NIC_EXTRA_ARGS.get(action, ())]
    child_env = {k: v for k, v in os.environ.items() if k not in secret_env and k not in required}
    child_env.update(secret_env)
    started = deps.monotonic()
    proc = deps.runner(argv, deps.root, child_env)
    elapsed = deps.monotonic() - started
    record = {
        "verb": action,
        "config": str(
            config_path.relative_to(deps.root)
            if deps.root in config_path.parents or config_path == deps.root
            else config_path
        ),
        "seconds": round(elapsed, 3),
        "exit": proc.returncode,
    }
    if deps.journal is not None:
        deps.journal(record)
    tail = (proc.stderr or proc.stdout or "").strip()
    summary = f"deploy nic {action}: nic {subcommand} exited {proc.returncode}"
    if tail:
        # Never nic's output unredacted (Story 118.9 AC4): the resolved secrets and every secret shape go first.
        summary = f"{summary}: {redact_secret_shapes(tail.splitlines()[-1], tuple(secret_env.values()))}"
    details: dict[str, Any] = {"argv": argv, "journal": record}
    if proc.returncode != 0:
        details["exit_code"] = proc.returncode
    result = DutyResult(ok=proc.returncode == 0, summary=summary, details=details)
    branch = existing_repository_branch(document)
    if action == "up" and proc.returncode == 0 and branch:
        leaked = scan_gitops_range(deps, branch)
        if leaked is not None:
            return leaked
    if action == "up" and proc.returncode == 0:
        from .deploy_nic_packs import PackDeps, _Completed, apply_nkp_packs

        def _pack_runner(argv: list[str], cwd: Path | None, env: dict[str, str] | None) -> _Completed:
            child_env = {**os.environ, **(env or {})}
            proc = deps.runner(argv, cwd or deps.root, child_env)
            return _Completed(proc.returncode, proc.stdout, proc.stderr)

        pack_outcome = apply_nkp_packs(
            repo_root=deps.root,
            document=document,
            pack_deps=PackDeps(gitops_root=deps.root, runner=_pack_runner),
        )
        if pack_outcome is not None and not pack_outcome.ok:
            return pack_outcome
        if pack_outcome is not None and pack_outcome.ok:
            result = DutyResult(
                ok=True,
                summary=f"{summary}; {pack_outcome.summary}",
                details={**details, **(pack_outcome.details or {})},
            )
    return result


def run_deploy_nic(ns: Any) -> DutyResult:
    """Dispatch one ``deploy nic <action>`` invocation from ``argparse``."""
    action = getattr(ns, "deploy_nic_verb", None)
    config = getattr(ns, "config", None)
    if not isinstance(action, str) or not isinstance(config, str):
        from .cli import EXIT_USAGE

        return DutyResult(
            ok=False,
            summary="deploy nic: usage — pick validate|up|kubeconfig|outputs|down and pass -f <config>",
            details={"exit_code": EXIT_USAGE},
        )
    deps: NicDeps | None = getattr(ns, "_nic_deps", None)
    if deps is None:
        deps = _production_deps(repo_root())
    return run_nic(deps, action=action, config=Path(config), yes=getattr(ns, "yes", False) is True)
