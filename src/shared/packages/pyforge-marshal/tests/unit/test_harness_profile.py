"""Unit tests for ``pyforge.marshal.core.harness_profile`` (Story 22.8,
FR-193 CAP-8) -- the pure half of the adapter-plural session harness:
profile parsing/validation, packaged + overlay loading, model-tier
translation, dispatch-argv rendering, and the marshal-profile -> bmad-loop
adapter-name translation. Fake data only; no subprocess anywhere (the
impure half is ``tests/unit/test_harness_bmadbuild.py``'s concern)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.marshal.core.harness_profile import (
    BMADLOOP_ADAPTER_BY_PROFILE,
    HarnessProfile,
    HarnessProfileError,
    bmadloop_adapter_for_preference,
    load_packaged_profiles,
    load_profiles,
    parse_profile,
    render_dispatch_argv,
    translate_model,
)

_MINIMAL = {
    "name": "fakecli",
    "binary": "fakecli",
    "argv": ["--go", "{prompt}"],
}


def _profile(**overrides) -> HarnessProfile:
    data = {**_MINIMAL, **overrides}
    return parse_profile(data, source="test profile")


# --- parse/validation --------------------------------------------------------


def test_parse_minimal_profile():
    profile = _profile()
    assert profile.name == "fakecli"
    assert profile.argv == ("--go", "{prompt}")
    assert profile.model_map == {}
    assert profile.verified is False


def test_unknown_key_is_rejected():
    with pytest.raises(HarnessProfileError, match="unknown profile key"):
        parse_profile({**_MINIMAL, "bogus": 1}, source="t")


@pytest.mark.parametrize("name", ["", "Bad Name", "UPPER", "../evil", "-lead"])
def test_malformed_name_is_rejected(name):
    with pytest.raises(HarnessProfileError, match="malformed profile name"):
        parse_profile({**_MINIMAL, "name": name}, source="t")


def test_missing_prompt_token_is_rejected():
    with pytest.raises(HarnessProfileError, match="prompt"):
        parse_profile({**_MINIMAL, "argv": ["--go"]}, source="t")


def test_double_prompt_token_is_rejected():
    with pytest.raises(HarnessProfileError, match="exactly once"):
        parse_profile({**_MINIMAL, "argv": ["{prompt}", "{prompt}"]}, source="t")


def test_embedded_model_args_token_is_rejected():
    with pytest.raises(HarnessProfileError, match="whole argv token"):
        parse_profile(
            {**_MINIMAL, "argv": ["x{model_args}", "{prompt}"], "model_args": ["-m", "{model}"]},
            source="t",
        )


def test_model_args_token_without_model_args_is_rejected():
    with pytest.raises(HarnessProfileError, match="'model_args' is empty"):
        parse_profile({**_MINIMAL, "argv": ["{model_args}", "{prompt}"]}, source="t")


def test_model_args_without_model_token_is_rejected():
    with pytest.raises(HarnessProfileError, match="must mention"):
        parse_profile({**_MINIMAL, "model_args": ["--model", "opus"]}, source="t")


def test_invalid_authcheck_regex_is_rejected():
    with pytest.raises(HarnessProfileError, match="authcheck_ok_pattern"):
        parse_profile({**_MINIMAL, "authcheck_ok_pattern": "("}, source="t")


@pytest.mark.parametrize("entry", ["/abs/bin", "../up", "a//b", ""])
def test_malformed_fallback_bin_dir_is_rejected(entry):
    with pytest.raises(HarnessProfileError):
        parse_profile({**_MINIMAL, "fallback_bin_dirs": [entry]}, source="t")


# --- packaged set ------------------------------------------------------------


def test_packaged_profiles_ship_the_five_declared_clis():
    profiles = load_packaged_profiles()
    assert set(profiles) == {"claude", "cursor", "gemini", "copilot", "devin"}


def test_packaged_cursor_preserves_the_prior_invocation_shape():
    """Behavior preservation (the CAP-8 AC): the previously-hardcoded
    ``--trust --workspace <worktree> [--model m] <prompt>`` semantics
    survive as the cursor profile, model passed through verbatim -- plus
    the one empirically-driven addition, ``-p`` (print mode, the CLI's
    documented non-interactive form; the old TUI shape never ran headless
    -- see cursor.toml's own header)."""
    cursor = load_packaged_profiles()["cursor"]
    argv, model, reason = render_dispatch_argv(
        cursor,
        binary_path="/usr/bin/cursor-agent",
        worktree=Path("/work/tree"),
        prompt="do the story",
        model="sonnet-4-thinking",
    )
    assert argv == (
        "/usr/bin/cursor-agent",
        "-p",
        "--trust",
        "--workspace",
        "/work/tree",
        "--model",
        "sonnet-4-thinking",
        "do the story",
    )
    assert model == "sonnet-4-thinking"
    assert reason is None
    assert cursor.authcheck_args == ("status",)
    assert cursor.authcheck_ok_pattern == "Logged in as"


def test_packaged_claude_argv_shape_and_verbatim_tiers():
    claude = load_packaged_profiles()["claude"]
    argv, model, reason = render_dispatch_argv(
        claude,
        binary_path="/home/u/.local/bin/claude",
        worktree=Path("/work/tree"),
        prompt="do the story",
        model="opus",
    )
    assert argv == (
        "/home/u/.local/bin/claude",
        "-p",
        "--permission-mode",
        "bypassPermissions",
        "--model",
        "opus",
        "do the story",
    )
    assert model == "opus"
    assert reason is None


def test_packaged_gemini_maps_tiers_and_declares_trust_flags():
    gemini = load_packaged_profiles()["gemini"]
    argv, model, reason = render_dispatch_argv(
        gemini,
        binary_path="gemini",
        worktree=Path("/w"),
        prompt="p",
        model="haiku",
    )
    assert model == "gemini-3-flash-preview"
    assert reason is None
    assert "--skip-trust" in argv and "--yolo" in argv
    assert argv[-2:] == ("-p", "p")


def test_packaged_copilot_omits_the_model_honestly():
    """No verified model vocabulary for this CLI -> model flags omitted
    with a reason (MRS-DISP-029 at the CLI boundary), never a guessed
    name."""
    copilot = load_packaged_profiles()["copilot"]
    argv, model, reason = render_dispatch_argv(
        copilot, binary_path="copilot", worktree=Path("/w"), prompt="p", model="opus"
    )
    assert model is None
    assert reason is not None and "opus" in reason
    assert argv == ("copilot", "-p", "p", "--allow-all-tools")


def test_packaged_devin_is_a_declared_untested_stub():
    devin = load_packaged_profiles()["devin"]
    assert devin.verified is False
    assert devin.authcheck_args == ()
    assert devin.authcheck_note != ""


def test_every_packaged_profile_with_no_authcheck_documents_why():
    """The CAP-8 contract: a cheap non-interactive authcheck, or a
    documented reason none exists -- never a silent absence."""
    for name, profile in load_packaged_profiles().items():
        assert profile.authcheck_args or profile.authcheck_note, (
            f"packaged profile {name!r} declares neither an authcheck nor "
            "an authcheck_note"
        )


# --- overlay loading ---------------------------------------------------------


def _write_overlay(repo_root: Path, name: str, text: str) -> Path:
    overlay = repo_root / "_bmad-output" / "harness-profiles"
    overlay.mkdir(parents=True, exist_ok=True)
    path = overlay / f"{name}.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_overlay_extends_and_overrides(tmp_path: Path):
    _write_overlay(
        tmp_path,
        "newcli",
        'name = "newcli"\nbinary = "newcli"\nargv = ["{prompt}"]\n',
    )
    _write_overlay(
        tmp_path,
        "cursor",
        'name = "cursor"\nbinary = "cursor-two"\nargv = ["{prompt}"]\n',
    )
    profiles, errors = load_profiles(tmp_path)
    assert errors == ()
    assert "newcli" in profiles
    assert profiles["cursor"].binary == "cursor-two"  # same-name override wins
    assert profiles["claude"].binary == "claude"  # packaged set intact


def test_malformed_overlay_degrades_to_a_recorded_error(tmp_path: Path):
    _write_overlay(tmp_path, "broken", "this is not [ valid toml\n")
    profiles, errors = load_profiles(tmp_path)
    assert set(profiles) >= {"claude", "cursor", "gemini", "copilot", "devin"}
    assert len(errors) == 1 and "broken" in errors[0]


def test_overlay_name_stem_mismatch_is_a_recorded_error(tmp_path: Path):
    _write_overlay(
        tmp_path, "aname", 'name = "bname"\nbinary = "x"\nargv = ["{prompt}"]\n'
    )
    profiles, errors = load_profiles(tmp_path)
    assert "aname" not in profiles and "bname" not in profiles
    assert len(errors) == 1 and "file stem" in errors[0]


def test_no_repo_root_skips_the_overlay():
    profiles, errors = load_profiles(None)
    assert set(profiles) == {"claude", "cursor", "gemini", "copilot", "devin"}
    assert errors == ()


# --- model translation -------------------------------------------------------


def test_translate_model_map_hit():
    profile = _profile(model_map={"opus": "big-model"})
    assert translate_model(profile, "opus") == ("big-model", None)


def test_translate_model_map_miss_omits_with_reason():
    profile = _profile(model_map={"opus": "big-model"})
    rendered, reason = translate_model(profile, "haiku")
    assert rendered is None
    assert "haiku" in reason and "model_map" in reason


def test_translate_model_passthrough():
    profile = _profile(model_passthrough=True)
    assert translate_model(profile, "opus") == ("opus", None)


def test_translate_model_no_map_no_passthrough_omits_with_reason():
    rendered, reason = translate_model(_profile(), "opus")
    assert rendered is None and "opus" in reason


def test_translate_model_none_is_silent():
    assert translate_model(_profile(), None) == (None, None)


# --- argv rendering ----------------------------------------------------------


def test_render_omits_model_args_token_when_no_model_renders():
    profile = _profile(
        argv=["--a", "{model_args}", "{prompt}"], model_args=["-m", "{model}"]
    )
    argv, model, reason = render_dispatch_argv(
        profile, binary_path="fakecli", worktree=Path("/w"), prompt="p", model=None
    )
    assert argv == ("fakecli", "--a", "p")
    assert model is None and reason is None


def test_render_substitution_is_literal_never_format():
    """A prompt containing brace placeholders must pass through verbatim --
    substitution is per-token ``str.replace`` of ``{worktree}`` BEFORE
    ``{prompt}``, so prompt text can never be re-substituted."""
    profile = _profile(argv=["--dir", "{worktree}", "{prompt}"])
    prompt = "story about {worktree} and {model_args}"
    argv, _, _ = render_dispatch_argv(
        profile, binary_path="fakecli", worktree=Path("/w t"), prompt=prompt, model=None
    )
    assert argv == ("fakecli", "--dir", "/w t", prompt)


# --- bmad-loop translation ---------------------------------------------------


def test_bmadloop_translation_first_counterpart_wins():
    assert bmadloop_adapter_for_preference(("claude", "cursor")) == "claude"
    assert bmadloop_adapter_for_preference(("cursor", "gemini")) == "gemini"


def test_bmadloop_translation_no_counterpart_is_none():
    assert bmadloop_adapter_for_preference(("cursor", "devin")) is None
    assert bmadloop_adapter_for_preference(()) is None


def test_bmadloop_translation_table_covers_only_real_counterparts():
    """cursor and devin have NO bmad_loop adapter (its packaged set is
    claude/codex/gemini/copilot/antigravity/opencode) -- absent from the
    table by design, never mapped to a guess."""
    assert set(BMADLOOP_ADAPTER_BY_PROFILE) == {"claude", "gemini", "copilot"}
