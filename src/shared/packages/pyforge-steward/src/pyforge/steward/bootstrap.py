"""Steward's machine-bootstrap duty helpers (Epic 17, Story 17.1).

``steward init`` reports host prereqs (pixi/git/gh/podman) with named
remedies; pixi's floor is read from the same ``requires-pixi`` pin that
``scripts/pixi_version_registry.py`` treats as master (AD-1: derive, never
hand-pin a second floor).

``steward shell-init`` emits idempotent shell setup (PATH, env, bash
completions) to stdout for ``eval "$(steward shell-init)"``.

Story 17.2 adds ``setup`` (clone + pixi install + hooks) and ``initrepo``
(onboard a checkout to ``validate-fast`` green). ``validate-fast`` is the
composed gate: prereqs + ``provision --verify`` + ``steward --version``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .interfaces import DutyResult
from .provision import check_environment_sync, materialize_environment

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_PIXI_TOML_RELATIVE_PATH = Path("pixi.toml")
_PRE_COMMIT_CONFIG_RELATIVE_PATH = Path("pre-commit-config.yaml")
_PYFORGE_TOML_RELATIVE_PATH = Path("pyforge.toml")
_DEFAULT_REPO_URL = "https://github.com/rxm7706/local-recipes.git"
# Story 63.6 (spec-pyforge-steward CAP-152): the default a bare clone bootstraps is the
# Guild env -- the bare minimum every harness gets at runtime. `local-recipes` (the recipe
# factory, 10 GB) is an explicit `--env local-recipes` for recipe work, never the default.
_DEFAULT_PIXI_ENV = "pyforge-guild"
_REQUIRES_PIXI_RE = re.compile(r'requires-pixi = ">=([^"]+)"')
_SHELL_INIT_MARKER = "# pyforge-steward shell-init"
_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+)")

_PREREQ_ORDER: tuple[str, ...] = ("pixi", "git", "gh", "podman")

_REMEDIES: dict[str, dict[str, str]] = {
    "pixi": {
        "missing": "install-pixi: curl -fsSL https://pixi.sh/install.sh | bash",
        "below-floor": "upgrade-pixi: pixi self-update (or reinstall from https://pixi.sh)",
    },
    "git": {
        "missing": "install-git: install git via your OS package manager (e.g. apt install git)",
    },
    "gh": {
        "missing": "install-gh: https://github.com/cli/cli#installation (or apt/snap install gh)",
    },
    "podman": {
        "missing": "install-podman: https://podman.io/docs/installation",
    },
}


@dataclass(frozen=True)
class PrereqResult:
    """One prereq row — always carries a remedy name when ``ok`` is False."""

    name: str
    ok: bool
    found: str | None
    required: str | None
    remedy: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "found": self.found,
            "required": self.required,
            "remedy": self.remedy,
        }


def repo_root() -> Path:
    """Walk up to the local-recipes checkout root."""
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _BMAD_LOOP_WORKTREE_RELATIVE_PATH).is_file():
            return ancestor
    raise RuntimeError(
        f"bootstrap.py: could not locate {_BMAD_LOOP_WORKTREE_RELATIVE_PATH} "
        f"by walking up from {here} — this module must live inside a "
        "local-recipes checkout."
    )


def pixi_floor_version(*, root: Path | None = None) -> str:
    """Floor from ``pixi.toml``'s ``requires-pixi`` — same source as the registry."""
    pixi_toml = (root or repo_root()) / _PIXI_TOML_RELATIVE_PATH
    text = pixi_toml.read_text(encoding="utf-8")
    match = _REQUIRES_PIXI_RE.search(text)
    if not match:
        raise RuntimeError("pixi.toml requires-pixi not found — cannot determine pixi floor")
    return match.group(1)


def _parse_version_tuple(version: str) -> tuple[int, ...]:
    cleaned = version.strip().lstrip("v").split("-", 1)[0]
    parts: list[int] = []
    for segment in cleaned.split("."):
        if not segment:
            continue
        digits = "".join(ch for ch in segment if ch.isdigit())
        if digits:
            parts.append(int(digits))
    if not parts:
        raise ValueError(f"unparseable version: {version!r}")
    return tuple(parts)


def _version_gte(found: str, floor: str) -> bool:
    return _parse_version_tuple(found) >= _parse_version_tuple(floor)


def _first_version(text: str) -> str | None:
    match = _VERSION_RE.search(text)
    return match.group(1) if match else None


def _tool_version(name: str, path: str) -> str | None:
    try:
        proc = subprocess.run(
            [path, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return _first_version(proc.stdout) or _first_version(proc.stderr)


def check_prereq(name: str, *, pixi_floor: str) -> PrereqResult:
    """Check one prereq and attach a named remedy on failure."""
    path = shutil.which(name)
    if path is None:
        return PrereqResult(
            name=name,
            ok=False,
            found=None,
            required=pixi_floor if name == "pixi" else None,
            remedy=_REMEDIES[name]["missing"],
        )

    version = _tool_version(name, path)
    if version is None:
        return PrereqResult(
            name=name,
            ok=False,
            found=path,
            required=pixi_floor if name == "pixi" else None,
            remedy=_REMEDIES[name]["missing"],
        )

    if name == "pixi":
        ok = _version_gte(version, pixi_floor)
        return PrereqResult(
            name=name,
            ok=ok,
            found=version,
            required=pixi_floor,
            remedy=None if ok else _REMEDIES["pixi"]["below-floor"],
        )

    return PrereqResult(
        name=name,
        ok=True,
        found=version,
        required=None,
        remedy=None,
    )


def gather_prereqs(*, root: Path | None = None) -> tuple[PrereqResult, ...]:
    floor = pixi_floor_version(root=root)
    return tuple(check_prereq(name, pixi_floor=floor) for name in _PREREQ_ORDER)


def format_init_report(results: tuple[PrereqResult, ...], *, as_json: bool) -> str:
    all_ok = all(r.ok for r in results)
    if as_json:
        payload = {
            "ok": all_ok,
            "prereqs": [r.to_dict() for r in results],
        }
        return json.dumps(payload, indent=2)

    lines = ["steward init: prereq report"]
    for row in results:
        if row.ok:
            detail = f"{row.found}"
            if row.required:
                detail += f" (floor >= {row.required})"
            lines.append(f"  ok   {row.name}: {detail}")
        else:
            lines.append(f"  FAIL {row.name}: {row.remedy}")
    lines.append("steward init: PASS" if all_ok else "steward init: FAIL")
    return "\n".join(lines)


def shell_init_script(*, root: Path | None = None) -> str:
    """Idempotent shell snippet — safe to eval repeatedly."""
    repo = root or repo_root()
    pixi_bin = Path.home() / ".pixi" / "bin"
    lines = [
        _SHELL_INIT_MARKER,
        f'export PYFORGE_REPO_ROOT="{repo}"',
        f'export PATH="{pixi_bin}:$PATH"',
        'if [ -n "${BASH_VERSION:-}" ]; then',
        "  _pyforge_steward_complete() {",
        '    local cur="${COMP_WORDS[COMP_CWORD]}"',
        '  COMPREPLY=( $(compgen -W "keys deploy provision budget sync workspace upgrade suite init shell-init setup initrepo validate-fast" -- "$cur") )',
        "  }",
        "  complete -o default -F _pyforge_steward_complete steward 2>/dev/null || true",
        "fi",
    ]
    return "\n".join(lines)


def shell_init_payload(*, root: Path | None = None) -> dict[str, object]:
    repo = root or repo_root()
    pixi_bin = str(Path.home() / ".pixi" / "bin")
    script = shell_init_script(root=repo)
    return {
        "path_prepend": [pixi_bin],
        "env": {
            "PYFORGE_REPO_ROOT": str(repo),
            "PATH": f"{pixi_bin}:{os.environ.get('PATH', '')}",
        },
        "completions": "bash",
        "script": script,
    }


def format_shell_init(*, as_json: bool, root: Path | None = None) -> str:
    if as_json:
        return json.dumps(shell_init_payload(root=root), indent=2)
    return shell_init_script(root=root)


class InitDuty:
    """``steward init`` — prereq detection with named remedies."""

    name = "init"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        try:
            results = gather_prereqs()
        except RuntimeError as exc:
            message = f"init: {exc}"
            if ns.json:
                return DutyResult(ok=False, summary=json.dumps({"ok": False, "error": message}, indent=2))
            return DutyResult(ok=False, summary=message)

        all_ok = all(r.ok for r in results)
        return DutyResult(
            ok=all_ok,
            summary=format_init_report(results, as_json=ns.json),
            details={"prereqs": [r.to_dict() for r in results]},
        )


class ShellInitDuty:
    """``steward shell-init`` — emit PATH/completions/env for eval."""

    name = "shell-init"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        try:
            summary = format_shell_init(as_json=ns.json)
        except RuntimeError as exc:
            message = f"shell-init: {exc}"
            if ns.json:
                return DutyResult(ok=False, summary=json.dumps({"ok": False, "error": message}, indent=2))
            return DutyResult(ok=False, summary=message)
        return DutyResult(ok=True, summary=summary)


@dataclass(frozen=True)
class SetupStep:
    """One idempotent bootstrap step — always carries a remedy on failure."""

    name: str
    ok: bool
    detail: str
    remedy: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "remedy": self.remedy,
        }


def _run_git_clone(url: str, dest: Path) -> None:
    subprocess.run(
        ["git", "clone", "--branch", "main", url, str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )


def _run_pre_commit_install(*, root: Path, env: str) -> None:
    subprocess.run(
        ["pixi", "run", "-e", env, "pre-commit", "install"],
        cwd=str(root),
        check=True,
        capture_output=True,
        text=True,
    )


def _run_steward_version(*, root: Path, env: str) -> str:
    proc = subprocess.run(
        ["pixi", "run", "-e", env, "steward", "--version"],
        cwd=str(root),
        check=True,
        capture_output=True,
        text=True,
    )
    return (proc.stdout or proc.stderr).strip()


def setup_steps(
    *,
    dest: Path,
    url: str | None,
    env: str,
) -> tuple[SetupStep, ...]:
    """Clone (when missing), pixi-install, and wire hooks — idempotent."""
    steps: list[SetupStep] = []

    if not dest.exists():
        if url is None:
            steps.append(
                SetupStep(
                    name="clone",
                    ok=False,
                    detail=f"destination {dest} does not exist",
                    remedy=(
                        "clone-repo: pass --url <git-url> and --dest <path> "
                        "or create the checkout first"
                    ),
                )
            )
            return tuple(steps)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            _run_git_clone(url, dest)
            steps.append(SetupStep(name="clone", ok=True, detail=str(dest)))
        except subprocess.CalledProcessError as exc:
            tail = (exc.stderr or exc.stdout or str(exc)).strip().splitlines()[-1]
            steps.append(
                SetupStep(
                    name="clone",
                    ok=False,
                    detail=tail,
                    remedy=f"clone-repo: fix git access and retry `git clone {url} {dest}`",
                )
            )
            return tuple(steps)
    else:
        steps.append(SetupStep(name="clone", ok=True, detail=f"skipped — {dest} exists"))

    if not (dest / _PIXI_TOML_RELATIVE_PATH).is_file():
        steps.append(
            SetupStep(
                name="pixi-install",
                ok=False,
                detail=f"missing {dest / _PIXI_TOML_RELATIVE_PATH}",
                remedy="pixi-install: checkout must contain pixi.toml",
            )
        )
        return tuple(steps)

    try:
        materialize_environment(env, cwd=dest)
        steps.append(SetupStep(name="pixi-install", ok=True, detail=f"pixi install -e {env}"))
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or exc.stdout or str(exc)).strip().splitlines()[-1]
        steps.append(
            SetupStep(
                name="pixi-install",
                ok=False,
                detail=tail,
                remedy=f"pixi-install: from {dest} run `pixi install -e {env}`",
            )
        )
        return tuple(steps)

    hooks_path = dest / _PRE_COMMIT_CONFIG_RELATIVE_PATH
    if hooks_path.is_file():
        try:
            _run_pre_commit_install(root=dest, env=env)
            steps.append(SetupStep(name="hooks", ok=True, detail="pre-commit install"))
        except subprocess.CalledProcessError as exc:
            tail = (exc.stderr or exc.stdout or str(exc)).strip().splitlines()[-1]
            steps.append(
                SetupStep(
                    name="hooks",
                    ok=False,
                    detail=tail,
                    remedy=(
                        f"hooks: from {dest} run "
                        f"`pixi run -e {env} pre-commit install`"
                    ),
                )
            )
    else:
        steps.append(
            SetupStep(
                name="hooks",
                ok=True,
                detail=f"skipped — no {_PRE_COMMIT_CONFIG_RELATIVE_PATH}",
            )
        )

    return tuple(steps)


def format_setup_report(steps: tuple[SetupStep, ...], *, as_json: bool) -> str:
    all_ok = all(step.ok for step in steps)
    if as_json:
        return json.dumps({"ok": all_ok, "steps": [s.to_dict() for s in steps]}, indent=2)
    lines = ["steward setup: bootstrap sequence"]
    for step in steps:
        prefix = "ok  " if step.ok else "FAIL"
        lines.append(f"  {prefix} {step.name}: {step.detail}")
        if not step.ok and step.remedy:
            lines.append(f"       remedy: {step.remedy}")
    lines.append("steward setup: PASS" if all_ok else "steward setup: FAIL")
    return "\n".join(lines)


def scaffold_pyforge_toml(*, root: Path) -> bool:
    """Write a minimal ``pyforge.toml`` when absent — returns True if created."""
    target = root / _PYFORGE_TOML_RELATIVE_PATH
    if target.exists():
        return False
    target.write_text(
        "# scaffolded by steward initrepo — extend as the repo's conventions grow\n"
        "[project]\n"
        f'name = "{root.name}"\n',
        encoding="utf-8",
    )
    return True


@dataclass(frozen=True)
class ValidateFastStep:
    name: str
    ok: bool
    detail: str
    remedy: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "remedy": self.remedy,
        }


def validate_fast_steps(*, root: Path, env: str) -> tuple[ValidateFastStep, ...]:
    """Fast green gate: prereqs, env sync, steward CLI smoke."""
    steps: list[ValidateFastStep] = []

    prereqs = gather_prereqs(root=root)
    prereqs_ok = all(row.ok for row in prereqs)
    if prereqs_ok:
        steps.append(ValidateFastStep(name="prereqs", ok=True, detail="init prereqs satisfied"))
    else:
        failed = [row for row in prereqs if not row.ok]
        remedy = failed[0].remedy or "init: run `steward init` and apply remedies"
        steps.append(
            ValidateFastStep(
                name="prereqs",
                ok=False,
                detail=", ".join(f"{row.name}" for row in failed),
                remedy=remedy,
            )
        )
        return tuple(steps)

    env_yaml = root / "environment.yaml"
    if env_yaml.is_file():
        try:
            in_sync, diff = check_environment_sync(cwd=root)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            steps.append(
                ValidateFastStep(
                    name="env-sync",
                    ok=False,
                    detail=str(exc),
                    remedy=(
                        "env-sync: run `pixi project export conda-environment -e build "
                        "> environment.yaml`"
                    ),
                )
            )
            return tuple(steps)
        if in_sync:
            steps.append(ValidateFastStep(name="env-sync", ok=True, detail="environment.yaml in sync"))
        else:
            steps.append(
                ValidateFastStep(
                    name="env-sync",
                    ok=False,
                    detail="environment.yaml drift",
                    remedy=(
                        "env-sync: run `pixi project export conda-environment -e build "
                        "> environment.yaml`"
                    ),
                )
            )
            return tuple(steps)
    else:
        steps.append(
            ValidateFastStep(
                name="env-sync",
                ok=True,
                detail="skipped — no environment.yaml",
            )
        )

    try:
        version_line = _run_steward_version(root=root, env=env)
        steps.append(ValidateFastStep(name="steward-cli", ok=True, detail=version_line))
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or exc.stdout or str(exc)).strip().splitlines()[-1]
        steps.append(
            ValidateFastStep(
                name="steward-cli",
                ok=False,
                detail=tail,
                remedy=f"steward-cli: from {root} run `pixi run -e {env} steward --version`",
            )
        )

    return tuple(steps)


def format_validate_fast_report(steps: tuple[ValidateFastStep, ...], *, as_json: bool) -> str:
    all_ok = all(step.ok for step in steps)
    if as_json:
        return json.dumps({"ok": all_ok, "steps": [s.to_dict() for s in steps]}, indent=2)
    lines = ["steward validate-fast: gate report"]
    for step in steps:
        prefix = "ok  " if step.ok else "FAIL"
        lines.append(f"  {prefix} {step.name}: {step.detail}")
        if not step.ok and step.remedy:
            lines.append(f"       remedy: {step.remedy}")
    lines.append("steward validate-fast: PASS" if all_ok else "steward validate-fast: FAIL")
    return "\n".join(lines)


def initrepo_steps(*, root: Path, env: str) -> tuple[SetupStep | ValidateFastStep, ...]:
    """Onboard a checkout: scaffold when needed, materialize env, validate-fast."""
    steps: list[SetupStep | ValidateFastStep] = []

    if not (root / _PIXI_TOML_RELATIVE_PATH).is_file():
        steps.append(
            SetupStep(
                name="pixi-project",
                ok=False,
                detail=f"missing {root / _PIXI_TOML_RELATIVE_PATH}",
                remedy="initrepo: path must be a pixi project root",
            )
        )
        return tuple(steps)
    steps.append(SetupStep(name="pixi-project", ok=True, detail=str(root / _PIXI_TOML_RELATIVE_PATH)))

    if scaffold_pyforge_toml(root=root):
        steps.append(SetupStep(name="scaffold", ok=True, detail=f"wrote {_PYFORGE_TOML_RELATIVE_PATH}"))
    else:
        steps.append(SetupStep(name="scaffold", ok=True, detail=f"skipped — {_PYFORGE_TOML_RELATIVE_PATH} exists"))

    try:
        materialize_environment(env, cwd=root)
        steps.append(SetupStep(name="pixi-install", ok=True, detail=f"pixi install -e {env}"))
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or exc.stdout or str(exc)).strip().splitlines()[-1]
        steps.append(
            SetupStep(
                name="pixi-install",
                ok=False,
                detail=tail,
                remedy=f"pixi-install: from {root} run `pixi install -e {env}`",
            )
        )
        return tuple(steps)

    steps.extend(validate_fast_steps(root=root, env=env))
    return tuple(steps)


def format_initrepo_report(
    steps: tuple[SetupStep | ValidateFastStep, ...],
    *,
    as_json: bool,
) -> str:
    all_ok = all(step.ok for step in steps)
    if as_json:
        return json.dumps(
            {"ok": all_ok, "steps": [step.to_dict() for step in steps]},
            indent=2,
        )
    lines = ["steward initrepo: onboard report"]
    for step in steps:
        prefix = "ok  " if step.ok else "FAIL"
        lines.append(f"  {prefix} {step.name}: {step.detail}")
        if not step.ok and step.remedy:
            lines.append(f"       remedy: {step.remedy}")
    lines.append("steward initrepo: PASS" if all_ok else "steward initrepo: FAIL")
    return "\n".join(lines)


class SetupDuty:
    """``steward setup`` — clone, pixi install, hooks."""

    name = "setup"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        dest = Path(ns.dest).expanduser().resolve() if ns.dest else repo_root()
        url = ns.url or _DEFAULT_REPO_URL
        env = ns.env or _DEFAULT_PIXI_ENV
        steps = setup_steps(dest=dest, url=None if dest.exists() else url, env=env)
        all_ok = all(step.ok for step in steps)
        return DutyResult(
            ok=all_ok,
            summary=format_setup_report(steps, as_json=ns.json),
            details={"steps": [s.to_dict() for s in steps]},
        )


class InitRepoDuty:
    """``steward initrepo`` — onboard a repo to validate-fast green."""

    name = "initrepo"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        root = Path(ns.repo).expanduser().resolve() if ns.repo else repo_root()
        env = ns.env or _DEFAULT_PIXI_ENV
        steps = initrepo_steps(root=root, env=env)
        all_ok = all(step.ok for step in steps)
        return DutyResult(
            ok=all_ok,
            summary=format_initrepo_report(steps, as_json=ns.json),
            details={"steps": [step.to_dict() for step in steps]},
        )


class ValidateFastDuty:
    """``steward validate-fast`` — composed fast green gate (Story 17.2)."""

    name = "validate-fast"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        root = Path(ns.repo).expanduser().resolve() if ns.repo else repo_root()
        env = ns.env or _DEFAULT_PIXI_ENV
        steps = validate_fast_steps(root=root, env=env)
        all_ok = all(step.ok for step in steps)
        return DutyResult(
            ok=all_ok,
            summary=format_validate_fast_report(steps, as_json=ns.json),
            details={"steps": [s.to_dict() for s in steps]},
        )
