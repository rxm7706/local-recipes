"""Credential-surface policy: secrets stay out of source (steward 16.4).

Production ``SECRET_KEY`` must have no baked default; platform Python sources
must not embed PEM private keys or obvious AWS access-key markers; root
``.gitignore`` must ignore ``.env``. OIDC retirement is steward 16.5 — out of
scope here.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from tests.policy import readers

if TYPE_CHECKING:
    from pathlib import Path

# django-environ / env() SECRET_KEY assignment in production settings.
SECRET_KEY_ASSIGNMENT = re.compile(
    r"^SECRET_KEY\s*=\s*env\(\s*(?P<args>[^)]*)\)\s*$",
    re.MULTILINE,
)
PEM_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:ENCRYPTED |RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
)
# Classic IAM access-key id shape (AKIA… / ASIA…).
AWS_ACCESS_KEY_ID = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")

SCAN_ROOT = readers.PLATFORM_ROOT
SKIP_DIR_NAMES = frozenset(
    {
        ".pixi",
        ".venv",
        "__pycache__",
        "node_modules",
        "staticfiles",
        "htmlcov",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    },
)


def _secret_key_env_args(production_text: str) -> str:
    match = SECRET_KEY_ASSIGNMENT.search(production_text)
    assert match is not None, (
        "config/settings/production.py must assign SECRET_KEY via env(...)"
    )
    return match.group("args")


def _assert_secret_key_has_no_default(production_text: str) -> None:
    args = _secret_key_env_args(production_text)
    assert "default" not in args, (
        "production SECRET_KEY must not pass default=... to env(); "
        f"got env({args})"
    )
    # Positional default: env("KEY", "fallback") or env('KEY', 'fallback')
    parts = [p.strip() for p in args.split(",")]
    assert len(parts) == 1, (
        'production SECRET_KEY must be env("DJANGO_SECRET_KEY") with no '
        f"positional default; got env({args})"
    )
    assert "DJANGO_SECRET_KEY" in parts[0], (
        f"production SECRET_KEY must read DJANGO_SECRET_KEY; got env({args})"
    )


def _iter_platform_py_files() -> list[Path]:
    files: list[Path] = []
    for path in SCAN_ROOT.rglob("*.py"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        # Policy fixtures may deliberately contain marker strings.
        try:
            path.relative_to(readers.POLICY_DIR)
        except ValueError:
            pass
        else:
            continue
        files.append(path)
    return files


def _assert_no_pem_or_aws_markers(paths: list[Path]) -> None:
    """Assert none of ``paths`` embed PEM private keys or AWS access-key markers."""
    offenders: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        if PEM_PRIVATE_KEY.search(text) or AWS_ACCESS_KEY_ID.search(text):
            try:
                rel = str(path.relative_to(readers.REPO_ROOT))
            except ValueError:
                rel = str(path)
            offenders.append(rel)
    assert offenders == [], (
        "credential markers found in platform sources: " + ", ".join(offenders)
    )


def test_production_secret_key_has_no_default() -> None:
    """Happy path: production SECRET_KEY is required env, no baked default."""
    text = readers.PRODUCTION_SETTINGS.read_text(encoding="utf-8")
    _assert_secret_key_has_no_default(text)


def test_deliberate_secret_key_default_reds() -> None:
    """Drift: a default on SECRET_KEY must fail the same assertion."""
    drifted = (
        'SECRET_KEY = env("DJANGO_SECRET_KEY", default="not-a-real-secret")\n'
    )
    with pytest.raises(AssertionError, match="must not pass default"):
        _assert_secret_key_has_no_default(drifted)


def test_platform_sources_have_no_pem_or_aws_key_markers() -> None:
    """Happy path: no PEM private keys / AKIA|ASIA markers under src/platform."""
    _assert_no_pem_or_aws_markers(_iter_platform_py_files())


def test_deliberate_pem_marker_would_be_detected(tmp_path: Path) -> None:
    """Drift: a planted PEM private-key header must fail the shared scanner."""
    sample = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAK...\n"
    planted = tmp_path / "planted_key.py"
    planted.write_text(sample, encoding="utf-8")
    with pytest.raises(AssertionError, match="credential markers"):
        _assert_no_pem_or_aws_markers([planted])


def _assert_gitignore_covers_dotenv(gitignore_text: str) -> None:
    lines = {line.strip() for line in gitignore_text.splitlines() if line.strip()}
    assert ".env" in lines, "root .gitignore must list .env"


def test_root_gitignore_covers_dotenv() -> None:
    """Root ``.gitignore`` must ignore ``.env`` (secrets stay out of git)."""
    text = readers.ROOT_GITIGNORE.read_text(encoding="utf-8")
    _assert_gitignore_covers_dotenv(text)


def test_deliberate_gitignore_dotenv_removal_reds() -> None:
    """Drift: dropping ``.env`` from .gitignore must fail the coverage check."""
    original = readers.ROOT_GITIGNORE.read_text(encoding="utf-8")
    drifted = "\n".join(
        line for line in original.splitlines() if line.strip() != ".env"
    )
    with pytest.raises(AssertionError, match=r"\.env"):
        _assert_gitignore_covers_dotenv(drifted)
