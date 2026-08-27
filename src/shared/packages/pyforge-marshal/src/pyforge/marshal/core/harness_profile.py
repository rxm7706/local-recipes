"""Declarative session-harness CLI profiles (Story 22.8, FR-193 CAP-8).

The pure half of the adapter-plural session harness: profile shape,
parsing/validation, packaged + overlay loading, dispatch-argv rendering,
model-tier translation, and the marshal-profile -> bmad-loop adapter-name
translation. MIRRORS ``bmad_loop``'s own declarative CLI-profile pattern
(``bmad_loop/adapters/profile.py`` + packaged TOML) in marshal-owned code --
never imports it (AD-3: ``adapters/harness_bmadloop.py`` is the only module
allowed to).

The impure half -- ``shutil.which``/fallback-path probing, the authcheck
subprocess, and the detached ``Popen`` launch -- lives solely in
``adapters/harness_bmadbuild.py`` (FR-52's single-seam discipline: binary
invocation stays confined to the adapter module). This module is pure in
AD-4's mechanical sense (no ``os``/``subprocess``/``time``/adapters imports);
its two loaders read only the package's OWN shipped data
(``importlib.resources``) and the repo overlay directory (``Path`` reads --
the same latitude ``core/dispatch.py``'s spec-candidate ``is_file()`` probes
already take).

**Profile TOML shape** (closed key set -- an unknown key is a parse error,
matching ``core/policy.py``'s closed-vocabulary discipline):

- ``name``: the profile's identity; must equal the file stem.
- ``binary``: the CLI executable name.
- ``argv``: the detached single-story invocation template, one string per
  argument, EXCLUDING the binary itself. Placeholders: ``{worktree}`` (the
  dispatch worktree path), ``{prompt}`` (the engine-neutral dispatch prompt
  -- required exactly once), ``{model_args}`` (a whole-token marker that
  expands to ``model_args`` when a model renders, or to nothing -- at most
  once).
- ``model_args``: the model-flag tokens ``{model_args}`` expands to (e.g.
  ``["--model", "{model}"]``); must mention ``{model}`` when non-empty.
- ``model_map``: marshal model-tier name -> this CLI's own spelling.
- ``model_passthrough``: pass an unmapped tier verbatim (``true`` only for
  CLIs empirically known to accept marshal's tier names as-is). A profile
  with a non-empty map, or with ``model_passthrough = false`` and no map
  entry for the tier, OMITS the model flags -- reported by the caller as
  ``MRS-DISP-029``, never a silently guessed model name.
- ``authcheck_args``: argv appended to the RESOLVED binary path for a cheap
  non-interactive auth probe; empty = no probe exists (say why in
  ``authcheck_note``).
- ``authcheck_ok_pattern``: regex the probe's combined output must match for
  auth to count as confirmed (exit code alone is NOT sufficient -- cursor's
  trust prompt and gemini's trust refusal both exit 0, verified live
  2026-08-27); empty = exit 0 suffices.
- ``env``: extra child-environment entries the launch needs.
- ``fallback_bin_dirs``: repo-root-relative directories probed when the
  binary is not on ``PATH`` (the pixi-env CLIs live in
  ``.pixi/envs/local-recipes/bin``, invisible to a bare operator PATH).
- ``verified`` / ``notes``: provenance, stated honestly -- ``true`` only for
  an invocation shape empirically smoke-tested against the real CLI.

**Loading precedence**: packaged (``pyforge/marshal/data/harness_profiles/
*.toml``) < repo overlay (``_bmad-output/harness-profiles/*.toml`` --
same-name overrides, new names extend). A malformed packaged profile raises
(our own shipped bug); a malformed overlay file degrades to a recorded
error string the caller reports as ``MRS-DISP-028``, never a crash --
the same packaged-strict/overlay-tolerant split ``bmad_loop``'s own loader
applies.

**bmad-loop translation** (``BMADLOOP_ADAPTER_BY_PROFILE``): a CODE
constant, deliberately not a TOML field -- it keeps
``render_policy_toml``'s derivation free of file I/O and the translation
testable as pure data. Overlay profiles therefore have no bmad-loop
counterpart by construction; ``bmadloop_adapter_for_preference`` falls
through to the next preference entry.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from types import MappingProxyType

import tomllib
from pyforge.core.errors import PyforgeError

#: Where the packaged profiles live, relative to the ``pyforge.marshal``
#: package root (shipped via pyproject.toml's force-include, the same
#: mechanism ``coverage_thresholds.toml`` already uses).
_PACKAGED_PROFILES_RELPATH = "data/harness_profiles"

#: The repo overlay directory, relative to the repo root -- repo-level, not
#: per-project: one machine's CLI estate is declared once (Story 22.8
#: design note).
OVERLAY_RELPATH = "_bmad-output/harness-profiles"

#: The token placeholders ``render_dispatch_argv`` substitutes. ``{prompt}``
#: is required exactly once; ``{model_args}`` must be a WHOLE token (it
#: expands to zero or more tokens, which no substring position could).
_PROMPT_TOKEN = "{prompt}"
_MODEL_ARGS_TOKEN = "{model_args}"
_WORKTREE_TOKEN = "{worktree}"
_MODEL_TOKEN = "{model}"

#: A profile name is a filename stem and a policy-preference entry -- the
#: same conservative shape a project slug takes, minus dots (a profile
#: named ``..`` has no business existing).
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

_PROFILE_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "binary",
        "argv",
        "model_args",
        "model_map",
        "model_passthrough",
        "authcheck_args",
        "authcheck_ok_pattern",
        "authcheck_note",
        "env",
        "fallback_bin_dirs",
        "verified",
        "notes",
    }
)

#: marshal profile name -> the installed bmad-loop's own adapter/profile
#: name for ``[adapter].name`` (bmad_loop's packaged set: claude, codex,
#: gemini, copilot, antigravity, opencode; its ALIASES map legacy names).
#: cursor and devin have NO bmad_loop counterpart -- absent here, so a
#: preference led by them falls through (or keeps the template default with
#: MRS-POLICY-008 reported at the render boundary).
BMADLOOP_ADAPTER_BY_PROFILE: Mapping[str, str] = MappingProxyType(
    {
        "claude": "claude",
        "gemini": "gemini",
        "copilot": "copilot",
    }
)


class HarnessProfileError(PyforgeError, Exception):
    """Raised for a malformed profile document (closed-key violation, bad
    field shape, template-placeholder violation, invalid authcheck regex)."""


@dataclass(frozen=True)
class HarnessProfile:
    """One declarative session-harness CLI profile -- see the module
    docstring for the field-by-field contract."""

    name: str
    binary: str
    argv: tuple[str, ...]
    model_args: tuple[str, ...] = ()
    model_map: Mapping[str, str] = field(default_factory=dict)
    model_passthrough: bool = False
    authcheck_args: tuple[str, ...] = ()
    authcheck_ok_pattern: str = ""
    authcheck_note: str = ""
    env: Mapping[str, str] = field(default_factory=dict)
    fallback_bin_dirs: tuple[str, ...] = ()
    verified: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_map", MappingProxyType(dict(self.model_map)))
        object.__setattr__(self, "env", MappingProxyType(dict(self.env)))


def _require_str(data: Mapping[str, object], key: str, source: str, *, default: str = "") -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise HarnessProfileError(f"{source}: {key!r} must be a string, got {value!r}")
    return value


def _require_bool(data: Mapping[str, object], key: str, source: str) -> bool:
    value = data.get(key, False)
    if not isinstance(value, bool):
        raise HarnessProfileError(f"{source}: {key!r} must be a boolean, got {value!r}")
    return value


def _require_str_list(
    data: Mapping[str, object], key: str, source: str, *, allow_empty_items: bool = False
) -> tuple[str, ...]:
    value = data.get(key, [])
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise HarnessProfileError(f"{source}: {key!r} must be a list of strings, got {value!r}")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or (item == "" and not allow_empty_items):
            raise HarnessProfileError(
                f"{source}: {key!r} entries must be non-empty strings, got {item!r}"
            )
        items.append(item)
    return tuple(items)


def _require_str_map(data: Mapping[str, object], key: str, source: str) -> dict[str, str]:
    value = data.get(key, {})
    if isinstance(value, str) or not isinstance(value, Mapping):
        raise HarnessProfileError(f"{source}: {key!r} must be a table of strings, got {value!r}")
    result: dict[str, str] = {}
    for map_key, map_value in value.items():
        if not isinstance(map_key, str) or map_key == "" or not isinstance(map_value, str):
            raise HarnessProfileError(
                f"{source}: {key!r} entries must map non-empty strings to strings, "
                f"got {map_key!r} -> {map_value!r}"
            )
        result[map_key] = map_value
    return result


def parse_profile(data: Mapping[str, object], *, source: str) -> HarnessProfile:
    """Validate one already-parsed profile document into a
    ``HarnessProfile``; raises ``HarnessProfileError`` naming ``source`` on
    any shape violation. Both routes into the profile map (packaged TOML,
    overlay TOML) converge here, so an overlay author cannot install a
    profile state the packaged set would have been refused -- the same
    single-validator convergence ``bmad_loop``'s ``_validate_profile``
    establishes for its own two routes."""
    unknown = set(data.keys()) - _PROFILE_KEYS
    if unknown:
        raise HarnessProfileError(f"{source}: unknown profile key(s) {sorted(unknown)}")

    name = _require_str(data, "name", source)
    if not _NAME_RE.match(name):
        raise HarnessProfileError(f"{source}: malformed profile name {name!r}")
    binary = _require_str(data, "binary", source)
    if binary == "":
        raise HarnessProfileError(f"{source}: 'binary' must be non-empty")

    argv = _require_str_list(data, "argv", source)
    if not argv:
        raise HarnessProfileError(f"{source}: 'argv' must be a non-empty list")
    if argv.count(_PROMPT_TOKEN) != 1:
        raise HarnessProfileError(
            f"{source}: 'argv' must contain the {_PROMPT_TOKEN!r} token exactly once"
        )
    if argv.count(_MODEL_ARGS_TOKEN) > 1:
        raise HarnessProfileError(
            f"{source}: 'argv' may contain the {_MODEL_ARGS_TOKEN!r} token at most once"
        )
    for token in argv:
        if _MODEL_ARGS_TOKEN in token and token != _MODEL_ARGS_TOKEN:
            raise HarnessProfileError(
                f"{source}: {_MODEL_ARGS_TOKEN!r} must be a whole argv token, "
                f"found embedded in {token!r}"
            )

    model_args = _require_str_list(data, "model_args", source)
    if model_args and not any(_MODEL_TOKEN in token for token in model_args):
        raise HarnessProfileError(
            f"{source}: non-empty 'model_args' must mention the {_MODEL_TOKEN!r} token"
        )
    if _MODEL_ARGS_TOKEN in argv and not model_args:
        raise HarnessProfileError(
            f"{source}: 'argv' uses {_MODEL_ARGS_TOKEN!r} but 'model_args' is empty"
        )

    authcheck_ok_pattern = _require_str(data, "authcheck_ok_pattern", source)
    if authcheck_ok_pattern:
        try:
            re.compile(authcheck_ok_pattern)
        except re.error as exc:
            raise HarnessProfileError(
                f"{source}: invalid 'authcheck_ok_pattern' regex: {exc}"
            ) from exc

    fallback_bin_dirs = _require_str_list(data, "fallback_bin_dirs", source)
    for entry in fallback_bin_dirs:
        parts = entry.split("/")
        if entry.startswith("/") or any(part in ("", "..") for part in parts):
            raise HarnessProfileError(
                f"{source}: 'fallback_bin_dirs' entries must be clean "
                f"repo-root-relative paths, got {entry!r}"
            )

    return HarnessProfile(
        name=name,
        binary=binary,
        argv=argv,
        model_args=model_args,
        model_map=_require_str_map(data, "model_map", source),
        model_passthrough=_require_bool(data, "model_passthrough", source),
        authcheck_args=_require_str_list(data, "authcheck_args", source),
        authcheck_ok_pattern=authcheck_ok_pattern,
        authcheck_note=_require_str(data, "authcheck_note", source),
        env=_require_str_map(data, "env", source),
        fallback_bin_dirs=fallback_bin_dirs,
        verified=_require_bool(data, "verified", source),
        notes=_require_str(data, "notes", source),
    )


def _parse_profile_toml(text: str, *, source: str, expected_name: str) -> HarnessProfile:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise HarnessProfileError(f"{source}: not valid TOML: {exc}") from exc
    profile = parse_profile(data, source=source)
    if profile.name != expected_name:
        raise HarnessProfileError(
            f"{source}: profile name {profile.name!r} must equal the file stem "
            f"{expected_name!r}"
        )
    return profile


def load_packaged_profiles() -> dict[str, HarnessProfile]:
    """The profiles shipped inside this package. A malformed packaged
    profile RAISES ``HarnessProfileError`` -- it is our own shipped bug, the
    strict half of the packaged-strict/overlay-tolerant split."""
    root = resources.files("pyforge.marshal").joinpath(_PACKAGED_PROFILES_RELPATH)
    profiles: dict[str, HarnessProfile] = {}
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        if not entry.name.endswith(".toml"):
            continue
        stem = entry.name[: -len(".toml")]
        text = entry.read_text(encoding="utf-8")
        profiles[stem] = _parse_profile_toml(
            text, source=f"packaged profile {entry.name}", expected_name=stem
        )
    return profiles


def load_profiles(
    repo_root: Path | None,
) -> tuple[dict[str, HarnessProfile], tuple[str, ...]]:
    """Packaged profiles overlaid by ``<repo_root>/_bmad-output/
    harness-profiles/*.toml`` (same-name overrides, new names extend).
    Returns ``(profiles, overlay_errors)`` -- each unloadable overlay file
    degrades to one recorded error string (the caller reports it as
    ``MRS-DISP-028``), never a crash, and never suppresses the packaged
    set. ``repo_root=None`` skips the overlay entirely."""
    profiles = load_packaged_profiles()
    errors: list[str] = []
    if repo_root is None:
        return profiles, ()
    overlay_dir = Path(repo_root) / OVERLAY_RELPATH
    if not overlay_dir.is_dir():
        return profiles, ()
    for path in sorted(overlay_dir.glob("*.toml")):
        try:
            text = path.read_text(encoding="utf-8")
            profiles[path.stem] = _parse_profile_toml(
                text, source=f"overlay profile {path}", expected_name=path.stem
            )
        except (OSError, UnicodeDecodeError, HarnessProfileError) as exc:
            errors.append(f"overlay profile {path} ignored: {exc}")
    return profiles, tuple(errors)


def translate_model(
    profile: HarnessProfile, model: str | None
) -> tuple[str | None, str | None]:
    """Resolve marshal's policy model tier into THIS CLI's own spelling:
    ``(rendered_model, omitted_reason)``. Exactly one of the two is
    non-``None`` unless ``model`` is ``None`` (no tier resolved -- nothing
    to render, nothing to report). A mapped tier renders its mapping; an
    unmapped tier on a passthrough profile renders verbatim; anything else
    OMITS the model flags with the reason (the caller's ``MRS-DISP-029``)
    -- never a guessed model name handed to a live session."""
    if model is None:
        return None, None
    mapped = profile.model_map.get(model)
    if mapped is not None:
        return mapped, None
    if profile.model_map:
        return None, (
            f"model tier {model!r} has no entry in profile {profile.name!r}'s "
            f"model_map -- model flags omitted"
        )
    if profile.model_passthrough:
        return model, None
    return None, (
        f"profile {profile.name!r} declares no model_map and no "
        f"model_passthrough -- model flags omitted for tier {model!r}"
    )


def render_dispatch_argv(
    profile: HarnessProfile,
    *,
    binary_path: str,
    worktree: Path,
    prompt: str,
    model: str | None,
) -> tuple[tuple[str, ...], str | None, str | None]:
    """Render the full launch argv for one dispatch:
    ``(argv, rendered_model, model_omitted_reason)``. Placeholder
    substitution is literal ``str.replace`` per token, never ``str.format``
    -- the prompt is free text and must not be interpretable as a format
    spec. ``{model_args}`` expands in place to ``model_args`` (with
    ``{model}`` substituted) when a model renders, or to nothing."""
    rendered_model, omitted_reason = translate_model(profile, model)
    argv: list[str] = [binary_path]
    for token in profile.argv:
        if token == _MODEL_ARGS_TOKEN:
            if rendered_model is None:
                continue
            argv.extend(
                arg.replace(_MODEL_TOKEN, rendered_model) for arg in profile.model_args
            )
            continue
        argv.append(
            token.replace(_WORKTREE_TOKEN, str(worktree)).replace(_PROMPT_TOKEN, prompt)
        )
    return tuple(argv), rendered_model, omitted_reason


def bmadloop_adapter_for_preference(preference: Sequence[str]) -> str | None:
    """The first preference entry with a bmad-loop counterpart, translated
    to bmad-loop's own adapter name -- the "one policy preference, two
    engines" bridge ``render_policy_toml`` derives ``[adapter].name`` from.
    ``None`` when no entry has a counterpart (the render keeps its template
    default; the ``--write-harness-policy`` boundary reports
    ``MRS-POLICY-008``)."""
    for name in preference:
        counterpart = BMADLOOP_ADAPTER_BY_PROFILE.get(name)
        if counterpart is not None:
            return counterpart
    return None
