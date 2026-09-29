"""``pyforge login`` — local-profile and PKCE bearer file writer (Story 33.12/33.14)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError

from ..adapters.oidc_pkce import PkceLogin, PkceLoginError
from ..core.verdict import EXIT_OK, EXIT_USAGE

_BEARER_ENV = "PYFORGE_IDP_BEARER_FILE"
_DEFAULT_BEARER_PATH = Path.home() / ".pyforge" / "idp-bearer"
_PLATFORM_SRC = "src/platform"
_DEFAULT_PKCE_CLIENT_ID = "pyforge-cli"


def add_login_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "login",
        help="Mint a local-dev IdP bearer and write PYFORGE_IDP_BEARER_FILE (0600).",
    )
    parser.add_argument(
        "persona",
        nargs="?",
        default=None,
        help="Local-dev persona key (for example marshal-operator).",
    )
    parser.add_argument(
        "--pkce",
        action="store_true",
        help="Use PKCE authorization-code flow against a real OIDC issuer.",
    )
    parser.add_argument(
        "--issuer",
        default=None,
        help="OIDC issuer base URL (required with --pkce).",
    )
    parser.add_argument(
        "--client-id",
        dest="client_id",
        default=_DEFAULT_PKCE_CLIENT_ID,
        help=f"OIDC client id for --pkce (default: {_DEFAULT_PKCE_CLIENT_ID}).",
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
    # Story 52.1 (SPEC-pyforge-core CAP-6): routed through the ONE sanctioned
    # subprocess seam, `PosixProcess.run`, which never takes an `env=`
    # override (it inherits `os.environ` exactly, by design). The custom env
    # this call used to build set `PYTHONPATH=<repo_root>/src/platform`,
    # REPLACING whatever `PYTHONPATH` the parent carried, so the old child was
    # immune to it; a parent `PYTHONPATH` now REACHES the child (it precedes
    # site-packages, so it can shadow `django` or any other sibling import
    # where the replaced-env child could not). That widening is accepted
    # deliberately, with the guarantee scoped to `config` only: the explicit
    # `sys.path.insert(0, <platform src>)` in the `-c` script keeps `config`
    # resolving from the platform dir first, deterministically, ahead of any
    # inherited `PYTHONPATH` entry. The two `setdefault`s the parent also
    # performed are already performed by the script itself. `PYTHONSAFEPATH`
    # in the parent's environment does not affect an explicit
    # `sys.path.insert`. Two further seam deltas are intentional:
    # `stdin=DEVNULL` (a child that unexpectedly prompts reads EOF instead of
    # hanging an unattended login) and `encoding="utf-8", errors="replace"`
    # (undecodable child output is replaced, never raised as a decode error).
    platform_src = repo_root / _PLATFORM_SRC
    script = (
        "import os, sys;"
        f"sys.path.insert(0, {str(platform_src)!r});"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local');"
        "os.environ.setdefault('COMPONENT_RUNTIME', 'local');"
        "import django; django.setup();"
        "from config.local_dev.mint import main;"
        "print(main([sys.argv[1]]))"
    )
    try:
        completed = PosixProcess().run([sys.executable, "-c", script, persona], cwd=repo_root)
    except ProcessError as exc:
        # A launch failure (the interpreter could not be spawned at all) is
        # reported the same way a failed mint is -- `run_login` catches
        # `RuntimeError` and exits EXIT_USAGE with the message on stderr --
        # so no raw launch `OSError` escapes this function.
        raise RuntimeError(f"mint could not launch: {exc}") from exc
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "mint failed").strip()
        raise RuntimeError(message)
    token = completed.stdout.strip()
    if not token:
        raise RuntimeError("mint returned an empty bearer")
    return token


def _write_bearer_file(bearer_path: Path, token: str) -> None:
    bearer_path.parent.mkdir(parents=True, exist_ok=True)
    bearer_path.write_text(token + "\n", encoding="utf-8")
    os.chmod(bearer_path, 0o600)


def _resolve_bearer_path(args: argparse.Namespace) -> Path:
    return Path(
        args.bearer_file or os.environ.get(_BEARER_ENV, "") or _DEFAULT_BEARER_PATH,
    ).expanduser()


def run_login(args: argparse.Namespace) -> int:
    persona = (args.persona or "").strip()
    if args.pkce:
        if persona:
            print("persona cannot be used with --pkce", file=sys.stderr)
            return EXIT_USAGE
        issuer = (args.issuer or "").strip()
        if not issuer:
            print("--issuer is required with --pkce", file=sys.stderr)
            return EXIT_USAGE
        bearer_path = _resolve_bearer_path(args)
        try:
            token = PkceLogin(
                issuer=issuer,
                client_id=args.client_id.strip() or _DEFAULT_PKCE_CLIENT_ID,
            ).run()
        except PkceLoginError as exc:
            print(str(exc), file=sys.stderr)
            return EXIT_USAGE
        _write_bearer_file(bearer_path, token)
        print(bearer_path)
        return EXIT_OK

    if not persona:
        print("persona is required unless --pkce is set", file=sys.stderr)
        return EXIT_USAGE
    repo_root = _repo_root(Path.cwd())
    if repo_root is None:
        print(
            "cannot locate src/platform for local mint; run from the repo root",
            file=sys.stderr,
        )
        return EXIT_USAGE
    bearer_path = _resolve_bearer_path(args)
    try:
        token = _mint_local_token(repo_root, persona)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    _write_bearer_file(bearer_path, token)
    print(bearer_path)
    return EXIT_OK
