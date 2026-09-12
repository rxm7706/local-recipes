"""``pyforge login`` — local-profile bearer file writer (Story 33.12, CAP-5)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from ..core.verdict import EXIT_OK, EXIT_USAGE

_BEARER_ENV = "PYFORGE_IDP_BEARER_FILE"
_DEFAULT_BEARER_PATH = Path.home() / ".pyforge" / "idp-bearer"
_PLATFORM_SRC = "src/platform"


def add_login_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "login",
        help="Mint a local-dev IdP bearer and write PYFORGE_IDP_BEARER_FILE (0600).",
    )
    parser.add_argument(
        "persona",
        help="Local-dev persona key (for example marshal-operator).",
    )
    parser.add_argument(
        "--bearer-file",
        dest="bearer_file",
        default=None,
        help=f"Override bearer file path (default: ${_BEARER_ENV} or {_DEFAULT_BEARER_PATH}).",
    )
    parser.set_defaults(handler=run_login)


def _repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / _PLATFORM_SRC / "config" / "local_dev" / "mint.py").is_file():
            return candidate
    return None


def _mint_local_token(repo_root: Path, persona: str) -> str:
    script = (
        "import os, sys;"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local');"
        "os.environ.setdefault('COMPONENT_RUNTIME', 'local');"
        "import django; django.setup();"
        "from config.local_dev.mint import main;"
        "print(main([sys.argv[1]]))"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / _PLATFORM_SRC)
    env.setdefault("COMPONENT_RUNTIME", "local")
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    completed = subprocess.run(
        [sys.executable, "-c", script, persona],
        cwd=str(repo_root),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "mint failed").strip()
        raise RuntimeError(message)
    token = completed.stdout.strip()
    if not token:
        raise RuntimeError("mint returned an empty bearer")
    return token


def run_login(args: argparse.Namespace) -> int:
    persona = args.persona.strip()
    if not persona:
        print("persona is required", file=sys.stderr)
        return EXIT_USAGE
    repo_root = _repo_root(Path.cwd())
    if repo_root is None:
        print(
            "cannot locate src/platform for local mint; run from the repo root",
            file=sys.stderr,
        )
        return EXIT_USAGE
    bearer_path = Path(
        args.bearer_file
        or os.environ.get(_BEARER_ENV, "")
        or _DEFAULT_BEARER_PATH,
    ).expanduser()
    try:
        token = _mint_local_token(repo_root, persona)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    bearer_path.parent.mkdir(parents=True, exist_ok=True)
    bearer_path.write_text(token + "\n", encoding="utf-8")
    os.chmod(bearer_path, 0o600)
    print(bearer_path)
    return EXIT_OK
