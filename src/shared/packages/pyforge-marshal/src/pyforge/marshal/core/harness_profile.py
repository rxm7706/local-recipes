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
  ``.pixi/envs/pyforge-guild/bin``, invisible to a bare operator PATH).
- ``verified`` / ``notes``: provenance, stated honestly -- ``true`` only for
  an invocation shape empirically smoke-tested against the real CLI.
- ``wrapper`` (Story 28.2): the OPTIONAL wire-compression wrapper --
  ``[wrapper]``, a sub-table parsed by ``parse_wrapper`` into
  ``HarnessWrapper``. See that dataclass and ``resolve_wire_wrap`` below.

**The wire-compression seam** (Story 28.2, SPEC-marshal-token-economy
CAP-2). A profile MAY declare a ``[wrapper]`` table naming a CLI that
launches the profile's own CLI through a compressing proxy (``headroom wrap
claude -- <claude argv>``). When -- and only when -- Story 28.1's declared
``[context]`` ``wire`` layer resolves ENABLED, ``resolve_wire_wrap`` turns
that declaration into a launch decision:

- the wrapper's ``binary`` + ``argv`` become an argv PREFIX that replaces
  the resolved CLI binary path. Everything ``render_dispatch_argv`` renders
  from the profile's own template -- flags, ``{worktree}``, the model flags,
  and the prompt -- follows the prefix BYTE-IDENTICALLY, wrapped or not.
  That is the NFR-14 admission requirement in marshal's own terms: the
  layer may prepend a launcher, never rewrite what marshal composed. Pinned
  by ``tests/unit/test_harness_profile.py``'s prefix byte-comparison, and
  enforced at parse time -- a wrapper ``argv`` token carrying any of the
  four launch placeholders is a ``HarnessProfileError``.
- the wrapper ``argv`` must NAME the profile's own ``binary`` as one of its
  tokens (``parse_profile``, which is where both values are known). Wrapping
  drops the probed+authchecked ``binary_path`` and lets the wrapper resolve
  the tool by name, so an overlay retargeting ``binary`` while keeping a
  packaged prefix would otherwise launch a different CLI entirely, with an
  identical rendered tail and no other symptom.
- ``store_env``/``store_relpath`` scope the wrapper's reversible
  compress-cache-retrieve (CCR) store to the LOOP HOME (for factory
  dispatch, the story's own worktree), so it is torn down with the worktree
  rather than accumulating in a user-global cache.
- ``reversible`` must be declared ``true``. The spec's "reversible or
  absent" constraint is a schema rule here, not a convention: a wrapper
  that cannot hand back the original bytes has no admissible declaration.
  Checked at BOTH layers -- ``parse_wrapper`` refuses the declaration, and
  ``resolve_wire_wrap`` re-checks the value it is about to launch with and
  degrades, covering any ``HarnessWrapper`` built without going through the
  parser.
- an unavailable wrapper (no ``[wrapper]`` declared for this profile, the
  wrapper binary missing, an uncreatable store dir) DISABLES the layer with
  a named reason the caller reports as ``MRS-DISP-033`` and launches
  unwrapped -- never a blocked run, never a silent no-op.

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

import hashlib
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from types import MappingProxyType

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
_WIRE_PORT_TOKEN = "{wire_port}"
_MODEL_TOKEN = "{model}"

_WIRE_PORT_BASE = 8800
_WIRE_PORT_SPAN = 1000


def wire_port_for_worktree(worktree: Path) -> int:
    """Deterministic headroom proxy port in 8800--9799 from ``worktree`` path
    (Story 33.8, DW-FU-28-2-2): stable per worktree, distinct across typical
    parallel dispatches."""
    digest = hashlib.sha256(str(worktree.resolve()).encode()).hexdigest()
    return _WIRE_PORT_BASE + (int(digest[:8], 16) % _WIRE_PORT_SPAN)


def substitute_wire_port(argv: Sequence[str], *, worktree: Path, wire_port: int | None = None) -> tuple[str, ...]:
    """Replace the ``{wire_port}`` placeholder in ``argv`` with a real port
    number (reusing Story 33.8's deterministic per-worktree derivation).

    ``render_dispatch_argv`` substitutes this token as one step of its own
    launch-token pass, but the bmad-loop wire profile overlay (Story 33.3,
    ``adapters/harness_bmadloop.py``) writes a wrapper's argv into a static
    TOML file that bmad-loop itself launches from -- bmad-loop has no
    notion of marshal's own ``{wire_port}`` token, so marshal must resolve
    it before handing the argv over. Live bug found 2026-09-10: without
    this call, headroom received the literal string ``'{wire_port}'`` and
    refused every launch with ``Error: Invalid value for '--port'``."""
    port = wire_port if wire_port is not None else wire_port_for_worktree(worktree)
    return tuple(token.replace(_WIRE_PORT_TOKEN, str(port)) for token in argv)


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
        # Story 28.2 (SPEC-marshal-token-economy CAP-2): the optional
        # wire-compression `[wrapper]` sub-table -- see `parse_wrapper`.
        "wrapper",
    }
)

#: ``[wrapper]``'s own closed key set (Story 28.2) -- the same
#: unknown-key-is-a-parse-error discipline the profile itself applies, one
#: level down.
_WRAPPER_KEYS: frozenset[str] = frozenset(
    {
        "binary",
        "argv",
        "env",
        "store_env",
        "store_relpath",
        "reversible",
        "fallback_bin_dirs",
        "notes",
    }
)

#: The ``CONTEXT_LAYER_NAMES`` member (``core/policy.py``) whose enablement
#: drives this seam. Named here, not spelled inline at the two launch call
#: sites, so the wire layer has exactly one spelling in the codebase.
WIRE_LAYER_NAME = "wire"

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

#: The inverse of ``BMADLOOP_ADAPTER_BY_PROFILE`` -- bmad-loop adapter name
#: back to the marshal harness profile stem that owns its ``[wrapper]``
#: declaration (Story 33.3 spin wire overlay).
PROFILE_BY_BMADLOOP_ADAPTER: Mapping[str, str] = MappingProxyType(
    {adapter: profile for profile, adapter in BMADLOOP_ADAPTER_BY_PROFILE.items()}
)


class HarnessProfileError(PyforgeError, Exception):
    """Raised for a malformed profile document (closed-key violation, bad
    field shape, template-placeholder violation, invalid authcheck regex)."""


@dataclass(frozen=True)
class HarnessWrapper:
    """One profile's declarative wire-compression wrapper (Story 28.2,
    SPEC-marshal-token-economy CAP-2) -- see the module docstring's "The
    wire-compression seam" section for the contract.

    - ``binary`` / ``fallback_bin_dirs``: resolved exactly like the
      profile's own binary (``PATH`` first, then repo-root-relative
      fallbacks). An unresolvable wrapper disables the layer; it never
      disqualifies the profile itself.
    - ``argv``: the tokens that follow the wrapper binary, ending at the
      wrapper's own argument separator. A pure PREFIX -- no launch
      placeholder may appear here (enforced in ``parse_wrapper``), so the
      wrapped and unwrapped argv tails are byte-identical.
    - ``env``: extra child-environment entries the wrapper needs (e.g. the
      cache-preserving optimization mode that keeps the provider prompt
      prefix frozen).
    - ``store_env`` / ``store_relpath``: the env var naming the wrapper's
      reversible CCR store, and where that store lives RELATIVE TO THE LOOP
      HOME. Both or neither.
    - ``reversible``: must be ``true``. "Reversible or absent" is the
      spec's own constraint; declaring it is how a profile states that the
      wrapper's compression is retrievable byte-exact. Enforced TWICE, at
      two different layers and deliberately not once: ``parse_wrapper``
      refuses a declaration that omits or denies it (a shipped/overlay TOML
      is a configuration error, and configuration errors are loud), while
      ``resolve_wire_wrap`` re-checks the value it is actually about to
      launch with and DEGRADES if it is false. The second check is what
      covers a ``HarnessWrapper`` built by any other route -- a future
      loader, Story 28.3's shim, a test helper -- for which the parse-time
      refusal never ran. It degrades rather than raises because a wrapper
      is a compression layer: an inadmissible one must turn its layer off,
      never fail a dispatch that is otherwise fine.

      The field's default is ``False`` for the same reason: the fail-safe
      direction for "is this compression reversible?" is *no*, so a
      constructor that simply forgets the flag gets an unapplied layer with
      a named reason, never silently-lossy compression on the wire.
    """

    binary: str
    argv: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)
    store_env: str = ""
    store_relpath: str = ""
    reversible: bool = False
    fallback_bin_dirs: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "env", MappingProxyType(dict(self.env)))


@dataclass(frozen=True)
class WireWrap:
    """``resolve_wire_wrap``'s decision for ONE launch (Story 28.2).

    Exactly three shapes exist, and no fourth:

    - **off** -- the declared ``wire`` layer is disabled (or absent, which
      resolves to disabled). ``applied=False``, ``reason=None``: nothing
      happened and nothing is worth saying, so today's behavior stays
      byte-identical and no finding is raised.
    - **degraded** -- the layer is ENABLED but could not be applied.
      ``applied=False`` with a non-``None`` ``reason``; the caller reports
      it (``MRS-DISP-033``) and launches unwrapped. Never a blocked run,
      never a silent no-op.
    - **applied** -- ``applied=True``, carrying the argv prefix, the extra
      child env (store-scoping var included), and the resolved store dir.

    Truthy iff applied, so a call site reads ``if wire:`` the same way
    ``HarnessResolution`` already reads."""

    applied: bool
    reason: str | None = None
    argv_prefix: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)
    store_dir: str | None = None
    aggressiveness: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "env", MappingProxyType(dict(self.env)))

    def __bool__(self) -> bool:
        return self.applied

    def journal_payload(self) -> dict[str, object]:
        """The JSON-safe projection both launch verbs journal and echo --
        a fresh plain ``dict`` per call (never the frozen proxy), so a
        caller hands it straight to ``json.dumps``. Mirrors
        ``policy.resolve_context_layers``'s own "plain dict, every time"
        discipline for the same reason."""
        return {
            "applied": self.applied,
            "reason": self.reason,
            "store_dir": self.store_dir,
            "aggressiveness": self.aggressiveness,
        }


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
    wrapper: HarnessWrapper | None = None

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
            raise HarnessProfileError(f"{source}: {key!r} entries must be non-empty strings, got {item!r}")
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
                f"{source}: {key!r} entries must map non-empty strings to strings, got {map_key!r} -> {map_value!r}"
            )
        result[map_key] = map_value
    return result


def _require_clean_relpath(entry: str, key: str, source: str) -> str:
    """A repo-root-/loop-home-relative path that cannot climb out of its
    root or anchor itself elsewhere. Extracted (Story 28.2) from
    ``parse_profile``'s original inline ``fallback_bin_dirs`` check so
    ``[wrapper]``'s own two path fields apply the IDENTICAL rule rather
    than a second, drifting copy."""
    parts = entry.split("/")
    if entry.startswith("/") or any(part in ("", "..") for part in parts):
        raise HarnessProfileError(f"{source}: {key!r} entries must be clean relative paths, got {entry!r}")
    return entry


def parse_wrapper(data: Mapping[str, object], *, source: str) -> HarnessWrapper:
    """Validate one already-parsed ``[wrapper]`` sub-table into a
    ``HarnessWrapper`` (Story 28.2, SPEC-marshal-token-economy CAP-2);
    raises ``HarnessProfileError`` naming ``source`` on any shape
    violation. Same closed-key discipline as ``parse_profile``, and the
    same single-validator convergence: packaged and overlay wrappers both
    arrive here, so an overlay author cannot declare a wrapper state the
    packaged set would have been refused.

    Two rules are the spec's own constraints made structural rather than
    conventional:

    - **no launch placeholder in ``argv``** -- the wrapper is a PREFIX. A
      token carrying ``{prompt}``/``{model_args}``/``{worktree}``/
      ``{model}`` would let a wrapper re-render (and so rewrite) what
      ``render_dispatch_argv`` already composed, which is precisely the
      prompt-prefix rewrite NFR-14 declares inadmissible. Refused here, so
      the byte-identical-tail property holds by construction and not only
      by test.
    - **``reversible`` must be ``true``** -- "reversible or absent". A
      wrapper that compresses without a retrievable original is
      silently-lossy; there is no admissible way to declare one."""
    unknown = set(data.keys()) - _WRAPPER_KEYS
    if unknown:
        raise HarnessProfileError(f"{source}: unknown wrapper key(s) {sorted(unknown)}")

    binary = _require_str(data, "binary", source)
    if binary == "":
        raise HarnessProfileError(f"{source}: 'wrapper.binary' must be non-empty")

    argv = _require_str_list(data, "argv", source)
    for token in argv:
        for placeholder in (
            _PROMPT_TOKEN,
            _MODEL_ARGS_TOKEN,
            _WORKTREE_TOKEN,
            _MODEL_TOKEN,
        ):
            if placeholder in token:
                raise HarnessProfileError(
                    f"{source}: 'wrapper.argv' token {token!r} carries the launch "
                    f"placeholder {placeholder!r} -- the wrapper is a prefix and "
                    "must never re-render the launch template (NFR-14: the prompt "
                    "prefix stays byte-identical wrapped vs unwrapped)"
                )

    reversible = _require_bool(data, "reversible", source)
    if not reversible:
        raise HarnessProfileError(
            f"{source}: 'wrapper.reversible' must be declared true -- a wrapper "
            "whose compression cannot be retrieved byte-exact is silently lossy, "
            "and the spec admits reversible or absent, never that"
        )

    store_env = _require_str(data, "store_env", source)
    store_relpath = _require_str(data, "store_relpath", source)
    if bool(store_env) != bool(store_relpath):
        raise HarnessProfileError(
            f"{source}: 'wrapper.store_env' and 'wrapper.store_relpath' must be "
            "declared together (an env var with nowhere to point, or a store path "
            "no launch would ever pass to the wrapper, is a half-declaration)"
        )
    if store_relpath:
        _require_clean_relpath(store_relpath, "wrapper.store_relpath", source)

    fallback_bin_dirs = _require_str_list(data, "fallback_bin_dirs", source)
    for entry in fallback_bin_dirs:
        _require_clean_relpath(entry, "wrapper.fallback_bin_dirs", source)

    return HarnessWrapper(
        binary=binary,
        argv=argv,
        env=_require_str_map(data, "env", source),
        store_env=store_env,
        store_relpath=store_relpath,
        # The PARSED value, never a hardcoded `True`: hardcoding is what
        # made this field vestigial on the constructed object even though
        # the declaration was checked, so `resolve_wire_wrap`'s own
        # re-check had nothing real to read.
        reversible=reversible,
        fallback_bin_dirs=fallback_bin_dirs,
        notes=_require_str(data, "notes", source),
    )


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
        raise HarnessProfileError(f"{source}: 'argv' must contain the {_PROMPT_TOKEN!r} token exactly once")
    if argv.count(_MODEL_ARGS_TOKEN) > 1:
        raise HarnessProfileError(f"{source}: 'argv' may contain the {_MODEL_ARGS_TOKEN!r} token at most once")
    for token in argv:
        if _MODEL_ARGS_TOKEN in token and token != _MODEL_ARGS_TOKEN:
            raise HarnessProfileError(
                f"{source}: {_MODEL_ARGS_TOKEN!r} must be a whole argv token, found embedded in {token!r}"
            )

    model_args = _require_str_list(data, "model_args", source)
    if model_args and not any(_MODEL_TOKEN in token for token in model_args):
        raise HarnessProfileError(f"{source}: non-empty 'model_args' must mention the {_MODEL_TOKEN!r} token")
    if _MODEL_ARGS_TOKEN in argv and not model_args:
        raise HarnessProfileError(f"{source}: 'argv' uses {_MODEL_ARGS_TOKEN!r} but 'model_args' is empty")

    authcheck_ok_pattern = _require_str(data, "authcheck_ok_pattern", source)
    if authcheck_ok_pattern:
        try:
            re.compile(authcheck_ok_pattern)
        except re.error as exc:
            raise HarnessProfileError(f"{source}: invalid 'authcheck_ok_pattern' regex: {exc}") from exc

    fallback_bin_dirs = _require_str_list(data, "fallback_bin_dirs", source)
    for entry in fallback_bin_dirs:
        _require_clean_relpath(entry, "fallback_bin_dirs", source)

    # Story 28.2: the `[wrapper]` sub-table, absent by default (no wrapper
    # declared = this profile has no wire-compression seam, which
    # `resolve_wire_wrap` degrades with a named reason rather than treating
    # as an error -- most CLIs have no wrapper counterpart at all).
    wrapper_data = data.get("wrapper")
    wrapper: HarnessWrapper | None = None
    if wrapper_data is not None:
        if isinstance(wrapper_data, str) or not isinstance(wrapper_data, Mapping):
            raise HarnessProfileError(f"{source}: 'wrapper' must be a table, got {wrapper_data!r}")
        wrapper = parse_wrapper(wrapper_data, source=source)
        # The wrapper names the tool it launches (`headroom wrap claude --`)
        # and then resolves that name off PATH itself -- while wrapping
        # DROPS the `binary_path` marshal probed and authchecked. So the two
        # spellings must agree, or an overlay that retargets `binary` while
        # keeping the packaged prefix would launch a DIFFERENT CLI than the
        # one this profile was resolved against, with no observable
        # difference in the rendered tail. Checked here rather than in
        # `parse_wrapper` because only this function knows both values, and
        # `parse_wrapper` stays usable standalone.
        if binary not in wrapper.argv:
            raise HarnessProfileError(
                f"{source}: 'wrapper.argv' {list(wrapper.argv)!r} never names this "
                f"profile's own binary {binary!r} -- the wrapper resolves the tool "
                "it launches by name, so a prefix naming a different tool would "
                "silently launch something other than the CLI marshal probed and "
                "authenticated"
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
        wrapper=wrapper,
    )


def _parse_profile_toml(text: str, *, source: str, expected_name: str) -> HarnessProfile:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise HarnessProfileError(f"{source}: not valid TOML: {exc}") from exc
    profile = parse_profile(data, source=source)
    if profile.name != expected_name:
        raise HarnessProfileError(f"{source}: profile name {profile.name!r} must equal the file stem {expected_name!r}")
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
        profiles[stem] = _parse_profile_toml(text, source=f"packaged profile {entry.name}", expected_name=stem)
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
            profiles[path.stem] = _parse_profile_toml(text, source=f"overlay profile {path}", expected_name=path.stem)
        except (OSError, UnicodeDecodeError, HarnessProfileError) as exc:
            errors.append(f"overlay profile {path} ignored: {exc}")
    return profiles, tuple(errors)


def translate_model(profile: HarnessProfile, model: str | None) -> tuple[str | None, str | None]:
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
            f"model tier {model!r} has no entry in profile {profile.name!r}'s model_map -- model flags omitted"
        )
    if profile.model_passthrough:
        return model, None
    return None, (
        f"profile {profile.name!r} declares no model_map and no "
        f"model_passthrough -- model flags omitted for tier {model!r}"
    )


# Story 28.6 (CAP-8): the ONE mapping from declared wire-layer
# ``aggressiveness`` to headroom-shaped child env. ``resolve_wire_wrap``
# merges these into the wrapper env so ``aggressiveness`` is not
# declaration-only (DW-FU-28-2-5). Values are marshal-owned conventions
# over headroom's ``HEADROOM_TARGET_RATIO`` knob -- cache mode stays pinned
# separately (NFR-14); aggressiveness adjusts compression intensity only.
_WIRE_AGGRESSIVENESS_ENV: Mapping[str, Mapping[str, str]] = {
    "low": {"HEADROOM_TARGET_RATIO": "0.35"},
    "medium": {"HEADROOM_TARGET_RATIO": "0.55"},
    "high": {"HEADROOM_TARGET_RATIO": "0.85"},
}


def wire_env_for_aggressiveness(base_env: Mapping[str, str], aggressiveness: str | None) -> dict[str, str]:
    """Merge ``base_env`` with the rung-specific env ``aggressiveness`` names,
    when recognized. Unknown/``None`` returns ``dict(base_env)`` unchanged."""
    merged = dict(base_env)
    if aggressiveness in _WIRE_AGGRESSIVENESS_ENV:
        merged.update(_WIRE_AGGRESSIVENESS_ENV[aggressiveness])
    return merged


def resolve_wire_enabled(raw: object, *, wrapper_declared: bool) -> bool:
    """Tri-state wire-layer enable resolution (Story 46.4): the literal
    ``"auto"`` resolves against whether the harness profile declares a
    ``[wrapper]``; any other declared value is a force-override, coerced
    to ``bool`` exactly as before."""
    if raw == "auto":
        return wrapper_declared
    return bool(raw)


def resolve_wire_wrap(
    profile: HarnessProfile,
    *,
    wire_layer: Mapping[str, object] | None,
    home: Path,
    wrapper_binary_path: str | None,
) -> WireWrap:
    """Story 28.2 (SPEC-marshal-token-economy CAP-2): the ONE place the
    declared ``wire`` layer becomes a launch decision. Pure -- no
    filesystem probing, no ``os`` (AD-4): binary resolution already
    happened (``wrapper_binary_path``, ``None`` when it did not), and
    creating the store directory is the adapter's business.

    ``wire_layer`` is one entry of ``policy.resolve_context_layers``'s own
    output -- ``{"enabled": bool | "auto", "aggressiveness": str}`` -- so
    both engines read the same composition site rather than each
    re-deriving "layer absent = off". ``None`` (no layer resolved at all)
    reads as disabled. Story 46.4: ``enabled`` may be the literal string
    ``"auto"``, resolved here (the point the concrete ``profile`` is known)
    via ``resolve_wire_enabled`` against whether ``profile`` declares a
    ``[wrapper]``.

    ``home`` is the loop home the CCR store is scoped to. For factory
    dispatch that is the story's own dispatch worktree, which is what makes
    the store torn down with the worktree instead of accumulating in a
    user-global cache.

    Every non-applied return with an ENABLED layer carries a ``reason``:
    the layer disabling itself is always visible (``MRS-DISP-033``), never
    a silent no-op. A DISABLED layer returns no reason -- there is nothing
    to report about a layer nobody asked for."""
    wrapper = profile.wrapper
    enabled = resolve_wire_enabled(
        (wire_layer or {}).get("enabled", False),
        wrapper_declared=wrapper is not None,
    )
    if not enabled:
        return WireWrap(applied=False)

    aggressiveness = (wire_layer or {}).get("aggressiveness")
    aggressiveness = aggressiveness if isinstance(aggressiveness, str) else None

    if wrapper is None:
        # Story 28.29 (CAP-2, documented incompatibility, live-verified
        # 2026-09-10): `cursor`'s absent [wrapper] is not an oversight --
        # `headroom wrap cursor --help` is IDE-only (a human configuring
        # Cursor's Settings UI, not an env-var-driven headless wrap), and
        # marshal's dispatch fleet launches the headless `cursor-agent` CLI
        # detached, with no GUI at all. Name that structural cause
        # explicitly rather than the generic "declares no [wrapper]"
        # wording, which reads as a gap someone forgot to fill in.
        detail = (
            f"harness profile {profile.name!r} declares no [wrapper] because "
            "cursor-agent has no headless wire-compression path -- "
            "headroom's cursor support is Cursor-IDE-only"
            if profile.name == "cursor"
            else f"harness profile {profile.name!r} declares no [wrapper]"
        )
        return WireWrap(
            applied=False,
            reason=(f"{detail} -- the wire-compression layer is off for this launch and the session runs unwrapped"),
            aggressiveness=aggressiveness,
        )
    if not wrapper.reversible:
        # "Reversible or absent" checked against the value this launch would
        # ACTUALLY run with, not only against the TOML that declared it --
        # `parse_wrapper` refuses an irreversible declaration, but a
        # `HarnessWrapper` reaching here by any other route (a future
        # loader, a provisioning shim, a test helper) never passed through
        # it. Degraded rather than raised: an inadmissible compression layer
        # turns itself off, it does not fail an otherwise-fine dispatch.
        return WireWrap(
            applied=False,
            reason=(
                f"wire-compression wrapper {wrapper.binary!r} (profile "
                f"{profile.name!r}) is not declared reversible -- compression "
                "whose original bytes cannot be retrieved is silently lossy, "
                "which is inadmissible, so the layer is off for this launch "
                "and the session runs unwrapped"
            ),
            aggressiveness=aggressiveness,
        )
    if wrapper_binary_path is None:
        return WireWrap(
            applied=False,
            reason=(
                f"wire-compression wrapper binary {wrapper.binary!r} (profile "
                f"{profile.name!r}) did not resolve on PATH or in its declared "
                "fallback dirs -- the layer is off for this launch and the "
                "session runs unwrapped"
            ),
            aggressiveness=aggressiveness,
        )

    env = wire_env_for_aggressiveness(dict(wrapper.env), aggressiveness)
    store_dir: str | None = None
    if wrapper.store_env:
        store_dir = str(Path(home) / wrapper.store_relpath)
        env[wrapper.store_env] = store_dir
    return WireWrap(
        applied=True,
        argv_prefix=(wrapper_binary_path, *wrapper.argv),
        env=env,
        store_dir=store_dir,
        aggressiveness=aggressiveness,
    )


def render_dispatch_argv(
    profile: HarnessProfile,
    *,
    binary_path: str,
    worktree: Path,
    prompt: str,
    model: str | None,
    wire: WireWrap | None = None,
    wire_port: int | None = None,
) -> tuple[tuple[str, ...], str | None, str | None]:
    """Render the full launch argv for one dispatch:
    ``(argv, rendered_model, model_omitted_reason)``. Placeholder
    substitution is literal ``str.replace`` per token, never ``str.format``
    -- the prompt is free text and must not be interpretable as a format
    spec. ``{model_args}`` expands in place to ``model_args`` (with
    ``{model}`` substituted) when a model renders, or to nothing.

    Story 28.2: an APPLIED ``wire`` replaces the leading ``binary_path``
    with the wrapper's own argv prefix and changes NOTHING else -- the
    rendered tail is byte-identical wrapped vs unwrapped, which is the
    NFR-14 property in marshal's own terms (a prepended launcher, never a
    rewritten prompt). The wrapper then resolves the wrapped CLI itself;
    the adapter keeps ``binary_path``'s own directory on the child ``PATH``
    so a CLI that only lives in a profile fallback dir stays reachable."""
    rendered_model, omitted_reason = translate_model(profile, model)
    port = wire_port if wire_port is not None else wire_port_for_worktree(worktree)

    def _substitute_launch_token(token: str) -> str:
        return (
            token.replace(_WORKTREE_TOKEN, str(worktree))
            .replace(_PROMPT_TOKEN, prompt)
            .replace(_WIRE_PORT_TOKEN, str(port))
        )

    if wire is not None and wire:
        argv = [_substitute_launch_token(token) for token in wire.argv_prefix]
    else:
        argv = [binary_path]
    for token in profile.argv:
        if token == _MODEL_ARGS_TOKEN:
            if rendered_model is None:
                continue
            argv.extend(arg.replace(_MODEL_TOKEN, rendered_model) for arg in profile.model_args)
            continue
        argv.append(_substitute_launch_token(token))
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
