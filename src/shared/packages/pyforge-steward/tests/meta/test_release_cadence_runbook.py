"""Story 46.10 — release-cadence.md is one verified runbook (CAP-8).

Meta gate: every numbered step carries a Verified pass block; the @next rehearsal
argv matches ``NEXT_REHEARSAL_ARGV`` from Story 14.10; the rehearsal disclaimer
is present; the runbook body never uses the word "improvised".
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest


def _load_next_rehearsal_argv() -> list[str]:
    unit_path = Path(__file__).resolve().parents[1] / "unit" / "test_upgrade_next_rehearsal.py"
    spec = importlib.util.spec_from_file_location("_test_upgrade_next_rehearsal_for_meta", unit_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    argv = getattr(module, "NEXT_REHEARSAL_ARGV", None)
    assert isinstance(argv, list)
    return argv


RUNBOOK_RELATIVE = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/release-cadence.md"
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _runbook_text(root: Path) -> str:
    return (root / RUNBOOK_RELATIVE).read_text(encoding="utf-8")


def _numbered_steps_section(text: str) -> str:
    match = re.search(
        r"(?ms)^## Steps \(owner → verb → gate\)\n(.*?)(?=^## The `@next` rehearsal|\Z)",
        text,
    )
    if not match:
        raise AssertionError("could not locate Steps section in release-cadence.md")
    return match.group(1)


def _next_rehearsal_section(text: str) -> str:
    match = re.search(
        r"(?ms)^## The `@next` rehearsal.*?\n(.*?)(?=^## Watches|\Z)",
        text,
    )
    if not match:
        raise AssertionError("could not locate @next rehearsal section")
    return match.group(1)


def _argv_fence_tokens(section: str) -> list[str]:
    fence_match = re.search(r"```text\n(.*?)```", section, re.DOTALL)
    if not fence_match:
        raise AssertionError("@next section missing ```text argv fence")
    raw = fence_match.group(1)
    flattened = re.sub(r"\\\s*\n\s*", " ", raw)
    tokens: list[str] = []
    for line in flattened.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tokens.extend(re.findall(r'"[^"]+"|<[^>]+>|[^\s]+', line))
    return [t.strip('"') for t in tokens]


def _normalize_argv_token(token: str) -> str:
    """Placeholders in the runbook may differ in wrapper form; compare semantic tokens."""
    if token.startswith("<") and token.endswith(">"):
        return token.lower()
    return token


@pytest.fixture(scope="module")
def runbook_text() -> str:
    return _runbook_text(_repo_root())


def test_each_numbered_step_has_verified_pass(runbook_text: str) -> None:
    steps_body = _numbered_steps_section(runbook_text)
    for step_num in range(1, 10):
        pattern = rf"(?ms)^{step_num}\.\s+\*\*.*?Verified pass"
        assert re.search(pattern, steps_body), f"step {step_num} missing a Verified pass block in release-cadence.md"


def test_verified_pass_blocks_name_owner_command_exit(runbook_text: str) -> None:
    blocks = re.findall(
        r"\*\*Verified pass.*?\*\* owner \*\*(\w+)\*\* \|.*?exit \*\*(\d+|0)\*\*",
        runbook_text,
        re.DOTALL,
    )
    assert len(blocks) >= 9, f"expected at least 9 Verified pass blocks with owner/exit, found {len(blocks)}"


def test_next_rehearsal_argv_matches_next_rehearsal_argv_constant(runbook_text: str) -> None:
    section = _next_rehearsal_section(runbook_text)
    fence_tokens = [_normalize_argv_token(t) for t in _argv_fence_tokens(section)]
    expected = [_normalize_argv_token(t) for t in _load_next_rehearsal_argv()]
    assert fence_tokens == expected, f"runbook argv {fence_tokens!r} != NEXT_REHEARSAL_ARGV {expected!r}"


def test_next_rehearsal_disclaims_live_proof(runbook_text: str) -> None:
    section = _next_rehearsal_section(runbook_text)
    lowered = section.lower()
    assert "not live proof" in lowered or "report-only" in lowered
    assert "does not flip" in lowered or "does **not** flip" in section.lower()
    assert "spec-bmad-method-core-upgrade" in section


def test_runbook_body_has_no_improvised_wording(runbook_text: str) -> None:
    assert "improvis" not in runbook_text.lower(), (
        'release-cadence.md must not contain "improvised" — use Verified pass blocks instead'
    )
