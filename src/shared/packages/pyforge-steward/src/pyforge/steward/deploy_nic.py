"""``steward deploy nic validate|up|kubeconfig|outputs|down`` — NKP on kind (CAP-176, Story 118.1).

Wraps ``nic validate|deploy|kubeconfig|outputs|destroy`` by subprocess (AD-1) over a tracked
config under ``src/platform/deploy/nic/``. Operator credentials are read from an untracked
``.env`` at the repo root: each ``NAME=relative/path.age`` line names an age-encrypted secret
file decrypted through ``keys.decrypt_file`` (CAP-1) — never ``os.environ[NAME]`` on the
parent process. Each run appends ``{verb, config, seconds, exit}`` to
``.steward/nic-deploy.jsonl``. Returns ``DutyResult`` only (AD-8); the kill switch is
``pyforge.steward.nkp_deploy`` (wired through ``cli.RETROFIT_KEY_VERBS``). ``down`` runs
``nic destroy --auto-approve``: ``nic destroy`` otherwise asks ``Type 'yes' to confirm`` and
dies with ``failed to read user input: EOF`` under a subprocess, and the explicit ``down``
action behind the kill switch is the consent (Story 118.4).
"""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml

from .interfaces import DutyResult

NKP_DEPLOY_FLAG = "pyforge.steward.nkp_deploy"
JOURNAL_RELATIVE = Path(".steward/nic-deploy.jsonl")
DOTENV_RELATIVE = Path(".env")

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
) -> tuple[dict[str, str] | None, DutyResult | None]:
    """Resolve ``required`` names from ``env_file`` through age decryption (keys), not the shell."""
    from .cli import EXIT_USAGE

    if not required:
        return {}, None
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


def _production_deps(root: Path) -> NicDeps:
    return NicDeps(
        root=root,
        runner=_default_runner,
        journal=lambda record: _append_journal(root, record),
    )


def _load_config(config_path: Path) -> tuple[object | None, DutyResult | None]:
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


def run_nic(deps: NicDeps, *, action: str, config: Path) -> DutyResult:
    from .cli import EXIT_USAGE

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
    required = operator_env_names(document)
    env_file = deps.root / DOTENV_RELATIVE
    secret_env, failure = load_secret_env(deps.root, env_file=env_file, required=required, decrypt=deps.decrypt)
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
        summary = f"{summary}: {tail.splitlines()[-1]}"
    details: dict[str, Any] = {"argv": argv, "journal": record}
    if proc.returncode != 0:
        details["exit_code"] = proc.returncode
    result = DutyResult(ok=proc.returncode == 0, summary=summary, details=details)
    if action == "up" and proc.returncode == 0:
        from .deploy_nic_packs import PackDeps, _Completed, apply_nkp_packs

        def _pack_runner(argv: list[str], cwd: Path | None, env: dict[str, str] | None) -> _Completed:
            proc = deps.runner(argv, cwd or deps.root, env if env is not None else {})
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
    return run_nic(deps, action=action, config=Path(config))
