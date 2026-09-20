"""Unit tests for ``pyforge.marshal.core.harness_profile`` (Story 22.8,
FR-193 CAP-8) -- the pure half of the adapter-plural session harness:
profile parsing/validation, packaged + overlay loading, model-tier
translation, dispatch-argv rendering, and the marshal-profile -> bmad-loop
adapter-name translation. Fake data only; no subprocess anywhere (the
impure half is ``tests/unit/test_harness_bmadbuild.py``'s concern).

Story 28.2 (SPEC-marshal-token-economy CAP-2) adds the wire-compression
seam's pure half: ``[wrapper]`` parsing (including the two structural
refusals that make the spec's constraints unbypassable -- no launch
placeholder in a wrapper prefix, ``reversible`` must be declared true),
``resolve_wire_wrap``'s three-shape decision, and the prefix
byte-comparison that pins the NFR-14 property."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.marshal.core.harness_profile import (
    BMADLOOP_ADAPTER_BY_PROFILE,
    WIRE_LAYER_NAME,
    HarnessProfile,
    HarnessProfileError,
    HarnessWrapper,
    bmadloop_adapter_for_preference,
    load_packaged_profiles,
    load_profiles,
    parse_profile,
    render_dispatch_argv,
    resolve_wire_enabled,
    resolve_wire_wrap,
    substitute_wire_port,
    translate_model,
    wire_port_for_worktree,
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
    # Story 46.11 (spec-pyforge-marshal CAP-262): the launch pins Claude Code's
    # built-in `agents-md` mod to `claude-md-and-agents-md` via `--settings`
    # (one whole JSON token), so nested AGENTS.md files load in every dispatched
    # session regardless of the operator's user settings.
    assert argv[:5] == (
        "/home/u/.local/bin/claude",
        "-p",
        "--permission-mode",
        "bypassPermissions",
        "--settings",
    )
    assert argv[6:] == ("--model", "opus", "do the story")
    settings = json.loads(argv[5])
    assert settings == {
        "pluginConfigs": {
            "agents-md@builtin": {"options": {"instructionFiles": "claude-md-and-agents-md"}}
        }
    }
    assert argv.count("do the story") == 1
    assert model == "opus"
    assert reason is None


def test_packaged_claude_settings_pin_is_one_literal_token_the_renderer_never_formats():
    """Story 46.11: the JSON braces survive `render_dispatch_argv`'s literal
    `str.replace` substitution untouched, and a prompt that happens to contain
    `{` or `}` cannot bleed into the settings token."""
    claude = load_packaged_profiles()["claude"]
    argv, _, _ = render_dispatch_argv(
        claude,
        binary_path="claude",
        worktree=Path("/work/tree"),
        prompt="fix {prompt}-shaped text and } braces",
        model=None,
    )
    token = argv[5]
    assert json.loads(token)["pluginConfigs"]["agents-md@builtin"]["options"] == {
        "instructionFiles": "claude-md-and-agents-md"
    }
    assert argv[-1] == "fix {prompt}-shaped text and } braces"


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


def test_overlay_retargeting_binary_under_a_packaged_prefix_is_refused(tmp_path: Path):
    """The finding's own scenario, end to end through the LOADER: an overlay
    keeps the packaged ``wrap claude --`` prefix but points ``binary`` at a
    different CLI. Refused -- and, being an overlay, refused the tolerant
    way (a recorded error the caller reports as ``MRS-DISP-028``), so one
    bad overlay never takes the packaged set down with it."""
    _write_overlay(
        tmp_path,
        "claude",
        'name = "claude"\nbinary = "claude-dev"\nargv = ["{prompt}"]\n'
        "[wrapper]\n"
        'binary = "headroom"\nargv = ["wrap", "claude", "--"]\n'
        'store_env = "HEADROOM_WORKSPACE_DIR"\nstore_relpath = ".marshal/wire"\n'
        "reversible = true\n",
    )
    profiles, errors = load_profiles(tmp_path)
    assert len(errors) == 1 and "never names this profile's own binary" in errors[0]
    # the packaged claude survived intact -- the overlay was ignored, not merged
    assert profiles["claude"].binary == "claude"
    assert profiles["claude"].wrapper is not None


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


# --- Story 28.2: [wrapper] parsing -------------------------------------------

_WRAPPER = {
    "binary": "wrapcli",
    "argv": ["wrap", "fakecli", "--"],
    "store_env": "WRAP_STORE",
    "store_relpath": ".marshal/wire",
    "reversible": True,
}


def _wrapped_profile(**wrapper_overrides) -> HarnessProfile:
    return _profile(wrapper={**_WRAPPER, **wrapper_overrides})


def test_profile_without_a_wrapper_declares_none():
    """The default: no ``[wrapper]`` table means no wire-compression seam
    for this profile -- absence, never a half-built stub."""
    assert _profile().wrapper is None


def test_wrapper_parses_every_declared_field():
    wrapper = _wrapped_profile(
        env={"WRAP_MODE": "cache"}, fallback_bin_dirs=["envbin"], notes="n"
    ).wrapper
    assert wrapper is not None
    assert wrapper.binary == "wrapcli"
    assert wrapper.argv == ("wrap", "fakecli", "--")
    assert wrapper.env == {"WRAP_MODE": "cache"}
    assert wrapper.store_env == "WRAP_STORE"
    assert wrapper.store_relpath == ".marshal/wire"
    assert wrapper.fallback_bin_dirs == ("envbin",)
    assert wrapper.reversible is True
    assert wrapper.notes == "n"


def test_wrapper_unknown_key_is_rejected():
    with pytest.raises(HarnessProfileError, match="unknown wrapper key"):
        _wrapped_profile(bogus=1)


def test_wrapper_must_be_a_table():
    with pytest.raises(HarnessProfileError, match="'wrapper' must be a table"):
        parse_profile({**_MINIMAL, "wrapper": "headroom"}, source="t")


def test_wrapper_binary_must_be_non_empty():
    with pytest.raises(HarnessProfileError, match="'wrapper.binary' must be non-empty"):
        _wrapped_profile(binary="")


@pytest.mark.parametrize(
    "token", ["{prompt}", "{model_args}", "{worktree}", "{model}", "--dir={worktree}"]
)
def test_wrapper_argv_carrying_a_launch_placeholder_is_rejected(token):
    """The NFR-14 admission requirement made STRUCTURAL, not conventional
    (SPEC-marshal-token-economy § Constraints, "never break the provider
    prompt cache"): a wrapper is a pure argv PREFIX. A placeholder in it
    would let the wrapper re-render -- and so rewrite -- what
    ``render_dispatch_argv`` already composed, which is exactly the
    prompt-prefix rewrite the spec declares inadmissible. Refused at parse
    time, so the byte-identical-tail property below holds by construction
    for EVERY profile, packaged or overlay, not only the ones a test
    happens to render."""
    with pytest.raises(HarnessProfileError, match="wrapper is a prefix"):
        _wrapped_profile(argv=["wrap", token])


@pytest.mark.parametrize("declared", [{}, {"reversible": False}])
def test_wrapper_must_declare_reversible_true(declared):
    """"Reversible or absent" (spec § Constraints) as a schema rule: a
    wrapper whose compression cannot be retrieved byte-exact is
    silently-lossy, and there is no admissible way to declare one -- an
    UNDECLARED ``reversible`` is refused exactly as a false one is."""
    data = {k: v for k, v in _WRAPPER.items() if k != "reversible"}
    with pytest.raises(HarnessProfileError, match="reversible"):
        _profile(wrapper={**data, **declared})


@pytest.mark.parametrize(
    "overrides",
    [{"store_relpath": ""}, {"store_env": ""}],
)
def test_wrapper_store_env_and_relpath_must_be_declared_together(overrides):
    with pytest.raises(HarnessProfileError, match="declared together"):
        _wrapped_profile(**overrides)


def test_wrapper_may_declare_neither_store_field():
    """Both-or-neither: a wrapper with no store at all is legal (it just
    never gets a store-scoping env var), and ``resolve_wire_wrap`` reports
    ``store_dir=None`` for it."""
    wrapper = _wrapped_profile(store_env="", store_relpath="").wrapper
    assert wrapper is not None and wrapper.store_env == "" and wrapper.store_relpath == ""


@pytest.mark.parametrize("entry", ["/abs/store", "../up", "a//b"])
def test_wrapper_store_relpath_must_be_a_clean_relative_path(entry):
    """The store is LOOP-HOME-scoped (the whole point: torn down with the
    worktree). A path that climbs out or anchors itself elsewhere would
    put the CCR store outside the home it is supposed to die with."""
    with pytest.raises(HarnessProfileError, match="clean relative paths"):
        _wrapped_profile(store_relpath=entry)


@pytest.mark.parametrize("entry", ["/abs/bin", "../up", "a//b"])
def test_wrapper_fallback_bin_dir_must_be_a_clean_relative_path(entry):
    with pytest.raises(HarnessProfileError, match="clean relative paths"):
        _wrapped_profile(fallback_bin_dirs=[entry])


@pytest.mark.parametrize(
    "argv",
    [
        ["wrap", "some-other-cli", "--"],  # names a DIFFERENT tool
        ["wrap", "fakecli-dev", "--"],  # a near-miss, not the same binary
        ["wrap", "--"],  # names no tool at all
        [],  # no prefix tokens whatsoever
    ],
)
def test_wrapper_argv_must_name_the_profiles_own_binary(argv):
    """Wrapping DROPS the ``binary_path`` marshal probed and authchecked and
    lets the wrapper re-resolve the tool by name, so the two spellings must
    agree. Left unchecked, an overlay setting ``binary = "claude-dev"`` while
    keeping the packaged ``["wrap", "claude", "--"]`` prefix would launch a
    completely different CLI -- with a byte-identical rendered tail, so
    every other test in this file, including the prefix byte-comparison,
    would still pass."""
    with pytest.raises(HarnessProfileError, match="never names this profile's own binary"):
        _wrapped_profile(argv=argv)


def test_wrapper_argv_naming_the_binary_anywhere_is_accepted():
    """An exact-token match, wherever it sits -- the rule binds the two
    spellings, it does not dictate the wrapper's flag order."""
    profile = _wrapped_profile(argv=["wrap", "--verbose", "fakecli", "--"])
    assert profile.wrapper is not None


def test_profile_fallback_bin_dirs_still_reject_the_same_shapes():
    """The Story 28.2 extraction of ``_require_clean_relpath`` must not have
    loosened the ORIGINAL check it was lifted out of."""
    with pytest.raises(HarnessProfileError, match="clean relative paths"):
        _profile(fallback_bin_dirs=["../up"])


# --- Story 28.2: the packaged claude wrapper ---------------------------------


def test_packaged_claude_declares_the_headroom_wrapper():
    """The one packaged wrapper (headroom-ai 0.37.0, Apache-2.0). ``--`` must
    END the prefix: everything after it is passed through to claude
    verbatim, which is what makes the profile's own rendered tail survive
    byte-for-byte."""
    wrapper = load_packaged_profiles()["claude"].wrapper
    assert wrapper is not None
    assert wrapper.binary == "headroom"
    assert wrapper.argv[:2] == ("wrap", "claude")
    assert "--port" in wrapper.argv
    assert "{wire_port}" in wrapper.argv
    assert wrapper.argv[-1] == "--"
    assert wrapper.reversible is True
    assert wrapper.store_env == "HEADROOM_WORKSPACE_DIR"
    assert wrapper.store_relpath == ".marshal/wire"
    assert wrapper.env == {"HEADROOM_MODE": "cache"}


def test_packaged_claude_wrapper_argv_names_the_profiles_own_binary():
    """The binding above, checked against the one wrapper actually shipped:
    `binary = "claude"` and `wrap claude --` must stay in agreement."""
    claude = load_packaged_profiles()["claude"]
    assert claude.wrapper is not None
    assert claude.binary in claude.wrapper.argv


def test_packaged_claude_wrapper_never_enables_a_second_memory_store():
    """The spec's own Never: headroom's cross-agent SharedContext /
    persistent memory would be a second memory store-of-record behind
    Scribe's back (`.claude/memory/` + `graph_store` is the fleet's only
    sanctioned memory face). ``--code-memory none`` turns off the Serena
    code-memory MCP `wrap claude` registers BY DEFAULT, and ``--memory`` is
    never passed."""
    wrapper = load_packaged_profiles()["claude"].wrapper
    assert wrapper is not None
    assert ("--code-memory", "none") == wrapper.argv[2:4]
    assert "--memory" not in wrapper.argv
    assert "--learn" not in wrapper.argv


def test_every_packaged_wrapper_is_reversible_and_loop_home_scoped():
    """The invariant a future packaged wrapper inherits without anyone
    remembering: reversible, and its store scoped to the loop home rather
    than a user-global cache."""
    for name, profile in load_packaged_profiles().items():
        if profile.wrapper is None:
            continue
        assert profile.wrapper.reversible is True, name
        assert profile.wrapper.store_env and profile.wrapper.store_relpath, name


# --- Story 28.2: resolve_wire_wrap -------------------------------------------


def test_wire_layer_name_is_a_real_declared_context_layer():
    """``WIRE_LAYER_NAME`` and ``policy.CONTEXT_LAYER_NAMES`` must not drift
    apart: a rename on either side would silently resolve the seam against
    a layer nobody declares (always-off, no finding, no error)."""
    from pyforge.marshal.core import policy

    assert WIRE_LAYER_NAME in policy.CONTEXT_LAYER_NAMES


@pytest.mark.parametrize(
    "layer", [None, {}, {"enabled": False, "aggressiveness": "medium"}]
)
def test_disabled_wire_layer_is_off_and_silent(layer, tmp_path: Path):
    """"Absent block = today's behavior byte-identical" (CAP-1) reaching
    this seam: a disabled layer yields no argv prefix, no env, no store --
    and NO reason, because a layer nobody enabled has no degradation worth
    reporting."""
    wire = resolve_wire_wrap(
        _wrapped_profile(), wire_layer=layer, home=tmp_path, wrapper_binary_path="/w"
    )
    assert bool(wire) is False
    assert wire.reason is None
    assert wire.argv_prefix == () and dict(wire.env) == {} and wire.store_dir is None


def test_enabled_layer_without_a_declared_wrapper_degrades_with_a_reason(tmp_path: Path):
    wire = resolve_wire_wrap(
        _profile(),
        wire_layer={"enabled": True, "aggressiveness": "high"},
        home=tmp_path,
        wrapper_binary_path=None,
    )
    assert wire.applied is False
    assert "declares no [wrapper]" in wire.reason
    assert "fakecli" in wire.reason
    assert wire.aggressiveness == "high"


def test_enabled_layer_names_cursor_s_structural_incompatibility(tmp_path: Path):
    """Story 28.29: `cursor`'s absent [wrapper] gets a specific reason
    naming the real, permanent cause -- not the generic "declares no
    [wrapper]" wording every other unwrapped profile still gets."""
    cursor = load_packaged_profiles()["cursor"]

    wire = resolve_wire_wrap(
        cursor,
        wire_layer={"enabled": True, "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path=None,
    )

    assert wire.applied is False
    assert "cursor-agent has no headless wire-compression path" in wire.reason
    assert "Cursor-IDE-only" in wire.reason


def test_enabled_layer_with_an_unresolved_wrapper_binary_degrades(tmp_path: Path):
    """The spec's graceful-degradation AC: instrument absent (not
    installed, platform gap) -> the layer disables with a NAMED finding and
    the run proceeds unwrapped. Never a blocked run, never a silent
    no-op."""
    wire = resolve_wire_wrap(
        _wrapped_profile(),
        wire_layer={"enabled": True, "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path=None,
    )
    assert wire.applied is False
    assert "wrapcli" in wire.reason and "did not resolve" in wire.reason


@pytest.mark.parametrize("wrapper_kwargs", [{}, {"reversible": False}])
def test_an_irreversible_wrapper_never_applies_however_it_was_built(
    wrapper_kwargs, tmp_path: Path
):
    """"Reversible or absent" must hold for the value actually launched
    with, not only for the TOML that declared it. ``parse_wrapper`` refuses
    an irreversible DECLARATION -- but a ``HarnessWrapper`` constructed by
    any other route (a future loader, Story 28.3's provisioning shim, a test
    helper) never passed through it, and the dataclass field defaults to
    ``False``. Built directly, on purpose: that is exactly the route the
    parse-time check cannot see.

    It DEGRADES rather than raises: an inadmissible compression layer turns
    itself off with a named reason, it never fails an otherwise-fine
    dispatch."""
    profile = HarnessProfile(
        name="fakecli",
        binary="fakecli",
        argv=("{prompt}",),
        wrapper=HarnessWrapper(binary="wrapcli", argv=("wrap", "fakecli", "--"), **wrapper_kwargs),
    )
    wire = resolve_wire_wrap(
        profile,
        wire_layer={"enabled": True, "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path="/opt/bin/wrapcli",  # resolves fine; that is not the problem
    )
    assert wire.applied is False
    assert "not declared reversible" in wire.reason
    assert "silently lossy" in wire.reason
    assert wire.argv_prefix == () and wire.store_dir is None


def test_a_parsed_wrapper_carries_the_declared_reversible_value(tmp_path: Path):
    """The counterpart: the parsed object must actually CARRY ``True``
    rather than the parser validating the declaration and then constructing
    a vestigial field the decision point cannot read."""
    wrapper = _wrapped_profile().wrapper
    assert wrapper is not None and wrapper.reversible is True


def test_applied_wire_scopes_the_ccr_store_inside_the_loop_home(tmp_path: Path):
    wire = resolve_wire_wrap(
        _wrapped_profile(env={"WRAP_MODE": "cache"}),
        wire_layer={"enabled": True, "aggressiveness": "low"},
        home=tmp_path,
        wrapper_binary_path="/opt/bin/wrapcli",
    )
    assert bool(wire) is True
    assert wire.reason is None
    assert wire.argv_prefix == ("/opt/bin/wrapcli", "wrap", "fakecli", "--")
    assert wire.store_dir == str(tmp_path / ".marshal" / "wire")
    # inside the home, not merely named after it
    assert Path(wire.store_dir).is_relative_to(tmp_path)
    # the store-scoping var rides ALONGSIDE the wrapper's own declared env
    assert dict(wire.env) == {
        "WRAP_MODE": "cache",
        "WRAP_STORE": wire.store_dir,
        "HEADROOM_TARGET_RATIO": "0.35",
    }
    assert wire.aggressiveness == "low"


def test_applied_wire_without_a_store_declaration_has_no_store_env(tmp_path: Path):
    wire = resolve_wire_wrap(
        _wrapped_profile(store_env="", store_relpath=""),
        wire_layer={"enabled": True},
        home=tmp_path,
        wrapper_binary_path="/opt/bin/wrapcli",
    )
    assert wire.applied is True and wire.store_dir is None and dict(wire.env) == {}


def test_malformed_aggressiveness_never_becomes_a_launch_value(tmp_path: Path):
    """``resolve_context_layers`` always supplies a string, but this seam
    reads a Mapping it does not own -- a non-string degrades to ``None``
    rather than being journaled as if it were a declared rung."""
    wire = resolve_wire_wrap(
        _wrapped_profile(),
        wire_layer={"enabled": True, "aggressiveness": 3},
        home=tmp_path,
        wrapper_binary_path="/opt/bin/wrapcli",
    )
    assert wire.aggressiveness is None


def test_wire_aggressiveness_maps_to_launch_env(tmp_path: Path):
    wire = resolve_wire_wrap(
        _wrapped_profile(env={"WRAP_MODE": "cache"}),
        wire_layer={"enabled": True, "aggressiveness": "high"},
        home=tmp_path,
        wrapper_binary_path="/opt/bin/wrapcli",
    )
    assert wire.applied is True
    assert wire.env["HEADROOM_TARGET_RATIO"] == "0.85"
    assert wire.env["WRAP_MODE"] == "cache"


def test_wire_journal_payload_is_a_fresh_plain_json_safe_dict(tmp_path: Path):
    wire = resolve_wire_wrap(
        _wrapped_profile(),
        wire_layer={"enabled": True, "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path="/opt/bin/wrapcli",
    )
    payload = wire.journal_payload()
    assert json.loads(json.dumps(payload)) == payload
    assert set(payload) == {"applied", "reason", "store_dir", "aggressiveness"}
    payload["applied"] = "mutated"
    assert wire.journal_payload()["applied"] is True  # a fresh dict every call


# --- Story 46.4: resolve_wire_enabled + the "auto" tri-state -----------------


def test_resolve_wire_enabled_auto_resolves_true_when_wrapper_declared():
    assert resolve_wire_enabled("auto", wrapper_declared=True) is True


def test_resolve_wire_enabled_auto_resolves_false_when_no_wrapper_declared():
    assert resolve_wire_enabled("auto", wrapper_declared=False) is False


def test_resolve_wire_enabled_explicit_true_ignores_wrapper_declared():
    """A force-override wins over the profile fact -- explicit ``true``
    stays ``true`` even against a profile with no ``[wrapper]``."""
    assert resolve_wire_enabled(True, wrapper_declared=False) is True


def test_resolve_wire_enabled_explicit_false_ignores_wrapper_declared():
    assert resolve_wire_enabled(False, wrapper_declared=True) is False


def test_resolve_wire_wrap_auto_with_a_declared_wrapper_applies(tmp_path: Path):
    """Fresh loop home, zero station config, Claude-shaped profile: "auto"
    resolves on because the profile declares a ``[wrapper]``."""
    wire = resolve_wire_wrap(
        _wrapped_profile(),
        wire_layer={"enabled": "auto", "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path="/opt/bin/wrapcli",
    )
    assert wire.applied is True
    assert wire.reason is None


def test_resolve_wire_wrap_auto_without_a_declared_wrapper_is_a_clean_skip(
    tmp_path: Path,
):
    """"auto" against a profile with no ``[wrapper]`` at all resolves off
    BEFORE the wrapper-is-None degraded path is even reached -- a clean,
    silent skip (``WireWrap(applied=False, reason=None)``), never a
    journaled attempt (matching Story 28.29's Cursor precedent)."""
    wire = resolve_wire_wrap(
        _profile(),
        wire_layer={"enabled": "auto", "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path=None,
    )
    assert wire.applied is False
    assert wire.reason is None


def test_resolve_wire_wrap_auto_against_cursor_shaped_profile_is_a_clean_skip(
    tmp_path: Path,
):
    """The real, packaged cursor profile (Story 28.29's documented
    structural incompatibility): "auto" resolves off cleanly, never the
    Cursor-specific degraded reason text (that text is only reachable via
    an explicit ``enabled=true`` against cursor)."""
    cursor = load_packaged_profiles()["cursor"]

    wire = resolve_wire_wrap(
        cursor,
        wire_layer={"enabled": "auto", "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path=None,
    )
    assert wire.applied is False
    assert wire.reason is None


def test_resolve_wire_wrap_auto_with_wrapper_declared_but_binary_missing_degrades(
    tmp_path: Path,
):
    """A profile that declares ``[wrapper]`` but whose binary does not
    resolve on PATH stays a WARN-class degraded result under "auto",
    exactly as it already does under an explicit ``true`` -- unchanged by
    this story."""
    wire = resolve_wire_wrap(
        _wrapped_profile(),
        wire_layer={"enabled": "auto", "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path=None,
    )
    assert wire.applied is False
    assert wire.reason is not None
    assert "did not resolve" in wire.reason


def test_resolve_wire_wrap_explicit_true_no_wrapper_stays_the_existing_degraded_path(
    tmp_path: Path,
):
    """A station force-override of ``enabled=true`` against a profile with
    no ``[wrapper]`` is untouched by this story -- the existing degraded/WARN
    path, not a clean skip (only "auto" reads the absent wrapper as off)."""
    wire = resolve_wire_wrap(
        _profile(),
        wire_layer={"enabled": True, "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path=None,
    )
    assert wire.applied is False
    assert wire.reason is not None


# --- Story 28.2: the prefix byte-comparison (the NFR-14 AC) ------------------


def test_wrapped_argv_is_the_unwrapped_argv_with_only_a_prefix_prepended(
    tmp_path: Path,
):
    """SPEC-marshal-token-economy CAP-2's third AC, in the only terms
    marshal can prove without a live provider round-trip: given IDENTICAL
    inputs, everything marshal composes -- the flags, the worktree, the
    model flags, and above all the prompt -- is BYTE-identical wrapped vs
    unwrapped. The wire layer may prepend a launcher; it may never rewrite
    what the launch already said. (The provider-side property -- system
    prompt / tool defs / older turns untouched in the cache hot zone -- is
    the instrument's documented live-zone-only design; this test proves
    marshal's half, which is the half marshal owns.)"""
    profile = _profile(
        argv=["--flag", "{worktree}", "{model_args}", "{prompt}"],
        model_args=["--model", "{model}"],
        model_passthrough=True,
        wrapper=_WRAPPER,
    )
    kwargs = {
        "binary_path": "/usr/bin/fakecli",
        "worktree": Path("/work/tree"),
        "prompt": "story text with {prompt} and a ünicode — dash",
        "model": "opus",
    }
    unwrapped, unwrapped_model, unwrapped_reason = render_dispatch_argv(
        profile, wire=None, **kwargs
    )
    wire = resolve_wire_wrap(
        profile,
        wire_layer={"enabled": True, "aggressiveness": "medium"},
        home=tmp_path,
        wrapper_binary_path="/opt/bin/wrapcli",
    )
    wrapped, wrapped_model, wrapped_reason = render_dispatch_argv(
        profile, wire=wire, **kwargs
    )

    assert wrapped[: len(wire.argv_prefix)] == wire.argv_prefix
    # BYTES, not just str equality -- the AC says byte-identical.
    assert [arg.encode("utf-8") for arg in wrapped[len(wire.argv_prefix) :]] == [
        arg.encode("utf-8") for arg in unwrapped[1:]
    ]
    # ...and the model translation the tail depends on is untouched too.
    assert (wrapped_model, wrapped_reason) == (unwrapped_model, unwrapped_reason)


def test_an_off_or_degraded_wire_leaves_the_argv_exactly_as_before(tmp_path: Path):
    """The other half of "byte-identical": a layer that is off, or enabled
    but degraded, must render the SAME argv the pre-28.2 code did -- the
    binary path first, no prefix, nothing appended."""
    profile = _wrapped_profile()
    baseline, _, _ = render_dispatch_argv(
        profile,
        binary_path="/usr/bin/fakecli",
        worktree=Path("/w"),
        prompt="p",
        model=None,
    )
    for layer, wrapper_path in (
        ({"enabled": False}, "/opt/bin/wrapcli"),  # off
        ({"enabled": True}, None),  # enabled but the instrument is absent
    ):
        wire = resolve_wire_wrap(
            profile, wire_layer=layer, home=tmp_path, wrapper_binary_path=wrapper_path
        )
        argv, _, _ = render_dispatch_argv(
            profile,
            binary_path="/usr/bin/fakecli",
            worktree=Path("/w"),
            prompt="p",
            model=None,
            wire=wire,
        )
        assert argv == baseline


def test_wire_port_for_worktree_is_in_range_and_distinct_per_worktree() -> None:
    left = Path("/tmp/dispatch-pyforge-marshal/33-8-a")
    right = Path("/tmp/dispatch-pyforge-marshal/33-8-b")
    port_left = wire_port_for_worktree(left)
    port_right = wire_port_for_worktree(right)
    assert 8800 <= port_left <= 9799
    assert 8800 <= port_right <= 9799
    assert port_left != port_right


def test_substitute_wire_port_replaces_the_literal_token(tmp_path: Path) -> None:
    """Regression (live bug, 2026-09-10): the bmad-loop wire profile overlay
    (Story 33.3, ``adapters/harness_bmadloop.py``) needs this exact
    substitution outside ``render_dispatch_argv``'s own launch-token pass --
    bmad-loop has no notion of ``{wire_port}``, so an unsubstituted argv
    reaches headroom as the literal string, which refuses to launch."""
    worktree = tmp_path / "loop-home"
    argv = ("wrap", "claude", "--code-memory", "none", "--port", "{wire_port}", "--")

    substituted = substitute_wire_port(argv, worktree=worktree)

    assert "{wire_port}" not in substituted
    port = wire_port_for_worktree(worktree)
    assert str(port) in substituted


def test_substitute_wire_port_honors_an_explicit_port(tmp_path: Path) -> None:
    worktree = tmp_path / "loop-home"

    substituted = substitute_wire_port(
        ("--port", "{wire_port}"), worktree=worktree, wire_port=9001
    )

    assert substituted == ("--port", "9001")


def test_render_dispatch_argv_substitutes_wire_port_in_wrapper_prefix(
    tmp_path: Path,
) -> None:
    profile = _wrapped_profile(
        binary="headroom",
        argv=["wrap", "fakecli", "--port", "{wire_port}", "--"],
    )
    worktree = tmp_path / "dispatch-wt"
    wire = resolve_wire_wrap(
        profile,
        wire_layer={"enabled": True},
        home=worktree,
        wrapper_binary_path="/opt/bin/headroom",
    )
    port = wire_port_for_worktree(worktree)
    argv, _, _ = render_dispatch_argv(
        profile,
        binary_path="/usr/bin/fakecli",
        worktree=worktree,
        prompt="probe",
        model=None,
        wire=wire,
        wire_port=port,
    )
    assert str(port) in argv


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
