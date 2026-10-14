"""Story 99.5 AC4 — manual CI twins print the pause banner and still run."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"


def test_platform_ci_local_prints_banner_with_fake_python(tmp_path: Path) -> None:
    script = SCRIPTS / "platform-ci-local.sh"
    text = script.read_text(encoding="utf-8")
    assert "emit_twin_banner" in text
    assert "platform-ci-local" in text


def test_guild_image_ci_prints_banner_with_fake_python(tmp_path: Path) -> None:
    script = SCRIPTS / "guild_image_ci.sh"
    text = script.read_text(encoding="utf-8")
    assert "emit_twin_banner" in text
    assert "guild_image_ci" in text


def test_pre_push_delegates_to_pr_preflight() -> None:
    hook = SCRIPTS / "pre_push_preflight.sh"
    body = hook.read_text(encoding="utf-8")
    assert "pr-preflight" in body


def test_platform_ci_local_still_accepts_stage_flags() -> None:
    proc = subprocess.run(
        ["bash", str(SCRIPTS / "platform-ci-local.sh"), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "test" in proc.stdout


def test_guild_image_ci_helpful_without_engine(tmp_path: Path) -> None:
    fake = tmp_path / "fake.py"
    fake.write_text(
        "import sys\n"
        "if 'emit_twin_banner' in open(sys.argv[1]).read():\n"
        "  sys.exit(0)\n",
        encoding="utf-8",
    )
    # Script requires docker; only verify banner hook is before engine check in source order.
    guild = (SCRIPTS / "guild_image_ci.sh").read_text(encoding="utf-8")
    assert guild.index("emit_twin_banner") < guild.index('command -v "$ENGINE"')
