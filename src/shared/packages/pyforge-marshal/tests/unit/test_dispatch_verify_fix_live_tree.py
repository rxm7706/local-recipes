"""Stories 85.1 and 85.3: the fix turn read against this checkout's troubleshooting doc and harness-profile overlay.

Story 116.3 (spec-pyforge-marshal:CAP-305): the ``test_dispatch_verify_fix.py`` tests that read this checkout
outside the package -- ``docs/how-to/troubleshoot-bmad-agent-loops.md``, and every fix template that ships, which
hands the root to ``load_profiles`` for the ``_bmad-output/harness-profiles/cursor.toml`` overlay -- moved here,
marked ``live_tree``; the root is found when a test runs, never at import, and a missing file fails the test, never
skips it. Every other fix-turn test stays in ``test_dispatch_verify_fix.py``, which keeps the launch capture both
files use.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_dispatch_verify_fix import _FIX_PROMPT, _capture_fix_launch

from pyforge.marshal.core.harness_profile import render_verify_fix_argv as render_fix

pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    # tests/unit -> tests -> pyforge-marshal -> packages -> shared -> src -> this checkout's root, found when a
    # test runs, never at import
    return Path(__file__).resolve().parents[6]


def test_troubleshoot_doc_names_fix_turn_gates() -> None:
    from pathlib import Path

    doc = Path("docs/how-to/troubleshoot-bmad-agent-loops.md").read_text(encoding="utf-8")
    for needle in (
        "MRS-GATE-001",
        "MRS-GATE-015",
        "pyforge.marshal.verify_fix_loop",
        "MRS-DISP-060",
        "dispatch-verify-fix",
        "journal.jsonl",
    ):
        assert needle in doc


def _fix_profiles() -> dict[str, object]:
    """The packaged claude and cursor profiles, and the repo overlay's cursor -- every fix template that ships."""
    from pyforge.marshal.core.harness_profile import load_packaged_profiles, load_profiles

    packaged = load_packaged_profiles()
    overlaid, errors = load_profiles(_repo_root())
    assert errors == ()
    assert (_repo_root() / "_bmad-output/harness-profiles/cursor.toml").is_file()
    return {"claude": packaged["claude"], "cursor": packaged["cursor"], "cursor-overlay": overlaid["cursor"]}


@pytest.mark.parametrize("name", ["claude", "cursor", "cursor-overlay"])
@pytest.mark.parametrize("mode", ["resume", "fix_only"])
def test_no_shipped_fix_template_carries_a_prompt_on_argv(name: str, mode: str):
    """H5/M8: every shipped fix template takes its prompt on stdin, so nothing but the binary and flags is argv."""
    from pyforge.marshal.core.harness_profile import verify_fix_prompt_on_stdin

    profile = _fix_profiles()[name]
    template = profile.resume_argv if mode == "resume" and profile.resume_argv else profile.fix_only_argv
    assert "{prompt}" not in " ".join(template)
    assert verify_fix_prompt_on_stdin(profile, mode=mode) is True
    argv, _, _ = render_fix(
        profile, mode=mode, binary_path="/bin/x", worktree=Path("/wt"), model="opus", session_id="sid-1"
    )
    assert not any("{" in token and "}" in token and "prompt" in token for token in argv)
    assert all(_FIX_PROMPT not in token for token in argv)


def test_cursor_declares_no_resume_template():
    """H2: the Cursor launch records no session id, so its fix turn is fix-only."""
    profiles = _fix_profiles()
    assert profiles["cursor"].resume_argv == ()
    assert profiles["cursor-overlay"].resume_argv == ()


@pytest.mark.parametrize(
    ("name", "mode"), [("claude", "resume"), ("claude", "fix_only"), ("cursor-overlay", "fix_only")]
)
def test_the_fix_turn_launch_feeds_the_prompt_on_stdin_from_a_private_file(monkeypatch, tmp_path, name, mode):
    """H5/M8 + the 0600 prompt file: the session's stdin is the prompt; argv never holds it."""
    from pyforge.marshal.core.dispatch_verify_fix import VERIFY_FIX_PROMPT_FILENAME

    launch, seen, run_dir = _capture_fix_launch(
        monkeypatch, profile=_fix_profiles()[name], mode=mode, tmp_path=tmp_path
    )

    assert seen["stdin"] == _FIX_PROMPT
    assert all(_FIX_PROMPT not in token for token in seen["argv"])
    assert tuple(seen["argv"]) == launch.command
    prompt_file = run_dir / VERIFY_FIX_PROMPT_FILENAME
    assert prompt_file.read_text(encoding="utf-8") == _FIX_PROMPT
    assert prompt_file.stat().st_mode & 0o777 == 0o600
    if mode == "resume":
        assert seen["argv"][seen["argv"].index("--resume") + 1] == "sid-85-3"


def test_the_prompt_file_is_rewritten_0600_when_it_already_exists(monkeypatch, tmp_path):
    from pyforge.marshal.core.dispatch_verify_fix import VERIFY_FIX_PROMPT_FILENAME

    stale = tmp_path / "run" / VERIFY_FIX_PROMPT_FILENAME
    stale.parent.mkdir()
    stale.write_text("stale", encoding="utf-8")
    stale.chmod(0o644)

    _capture_fix_launch(monkeypatch, profile=_fix_profiles()["claude"], mode="fix_only", tmp_path=tmp_path)

    assert stale.read_text(encoding="utf-8") == _FIX_PROMPT
    assert stale.stat().st_mode & 0o777 == 0o600
