"""Per-repo configurable policy — dual-TOML config load + the derived
verdict-moving knobs (Story 3.1).

Before this module, every verdict-moving threshold was hardcoded with zero
per-repo override surface: ``DefaultPolicy.evaluate`` (``interfaces.py``)
computed DEP001's mapping-confidence trust as a fixed binary check,
``vuln_rung`` (``vuln.py``) always used ``DEFAULT_VULN_SEVERITY_POLICY``
(block only on CRITICAL), and no coverage-floor gate existed at all.

Ownership decisions recorded:

* ``ConfigLoader.load`` reads ``pyproject.toml`` (the PRIMARY source — a
  malformed document there is a hard failure, ``ConfigParseError``) then
  ``pixi.toml`` (the SECONDARY source — a malformed document there is
  treated as absent, with a stderr warning) from ``[tool.pyforge-warden]``.
  A same-key conflict between the two files is resolved pyproject-wins,
  surfaced as one stderr warning naming the key and both values — never a
  failure. CLI-supplied overrides (``cli_fail_on``/``cli_fail_under_
  coverage``) are applied LAST, after both files are merged, so they win
  over either file unconditionally.
* Every VALUE-level problem (an unrecognized ``[tool.pyforge-warden]`` key
  — including any underscore-spelled variant of a real key — a non-table
  ``[tool]``/``[tool.pyforge-warden]``, or a wrong-typed/out-of-range value
  for a recognized key) is a typed ``ConfigValidationError``, raised
  regardless of which file it came from: only TOML SYNTAX failures get the
  file-dependent hard/soft treatment above; once a document parses, its
  SHAPE is held to the same standard from either source.
* ``EffectiveConfig.vuln_severity_policy`` derives the vulnerability-axis
  severity->status table purely from ``fail_on`` + ``_SEVERITY_ORDER`` (an
  explicit, LOCAL tier-strength ordering) — never imports ``vuln.
  DEFAULT_VULN_SEVERITY_POLICY`` (see the Never below). At the default
  (``fail_on=CRITICAL``), the derived table is byte-identical to that
  module default, which is exactly how ``DefaultPolicy()`` (no ``config``
  argument) reproduces today's behavior unchanged.
* ``EffectiveConfig.is_confidence_trusted`` mirrors the same fail-closed-
  by-default posture as ``hygiene.hygiene_rung``'s ``dep001_trusted`` gate:
  an unrecognized ``mapping_confidence`` string (a future producer's not-
  yet-seen token) ranks BELOW every known tier — untrusted, never silently
  passed — and ``None`` (no mapping opinion at all — most conda packages
  are legitimately non-Python/native) is always trusted, matching
  ``DefaultPolicy.evaluate``'s pre-3.1 comment on why a total map miss is
  not itself a distrust signal.
* This module imports ONLY ``.models`` (``SeverityTier``, ``Status``) —
  never ``vuln.py``/``hygiene.py``/``extract/`` — deliberately, to avoid
  recreating the ``interfaces<->extract.lockfiles`` import cycle
  ``interfaces.py``'s own module docstring already documents working
  around via lazy imports (``extract/lockfiles.py`` imports ``Router``
  from ``interfaces.py``; if this module imported anything from
  ``extract/`` while ``interfaces.py`` imports THIS module at top level,
  the cycle would reopen). ``SeverityTier``/``Status`` live in the
  cycle-free leaf ``models.py``, so ``interfaces.py`` can import this
  module normally at module top with zero lazy-import ceremony.
* The ``dep001-block-confidence`` key is TOML-only by design — no CLI flag
  exists for it (epics.md's AC spells CLI flags for exactly ``--fail-on``/
  ``--fail-under-coverage``); ``ConfigLoader.load`` has no
  ``cli_dep001_block_confidence`` parameter to match.
* ``waiver-default-expiry-days`` (Story 3.2, FR24) is likewise TOML-only —
  no CLI flag exists for it either; ``cli.py``'s ``--bypass`` path reads
  ``EffectiveConfig.waiver_default_expiry_days`` directly to compute a
  waiver's default expiry window.
* ``fail-on-kev`` (Story 6.4, FR36/FR18's default-gate role) is likewise
  TOML-only, no CLI flag — same treatment as ``dep001-block-confidence``
  (epics.md's retired-flag-family note: only ``--fail-on``/
  ``--fail-under-coverage`` ever get a CLI flag). Defaults ``true``: a
  CISA-KEV-listed advisory blocks by default, matching every other v1
  default-on gate. ``interfaces.DefaultPolicy.evaluate`` threads
  ``self._config.fail_on_kev`` into ``vuln.vuln_rung``; ``cli.py``
  constructs ``OsvEngine(fail_on_kev=config.fail_on_kev)`` the same way it
  already special-cases ``DeptryEngine`` in its engine-construction loop.
* ``allow-licenses``/``deny-licenses`` (Story 6.2, FR33's v1 gate-activation
  rule) DO get CLI flags (``--allow-licenses``/``--deny-licenses``) — unlike
  ``dep001-block-confidence``/``fail-on-kev`` above, these two ARE part of
  epics.md's spelled-out v1 CLI surface. Both accept a comma-separated
  string OR a TOML list of strings (``_coerce_allow_licenses``/
  ``_coerce_deny_licenses``); CLI wins over either TOML file, same
  last-applied precedence as ``fail-on``/``fail-under-coverage``.
  ``license_gating`` (``True`` iff either tuple is non-empty) and
  ``license_policy`` (a ``LicenseVerdict -> Status`` table, mirroring
  ``vuln_severity_policy``'s shape) are both defined this story per the
  architecture's ownership split — ``license_policy`` has no caller yet
  (``license.license_rung`` is a hard warn-cap this story, oblivious to any
  policy table; real escalation is Story 6.5's).

This module parses TOML as DATA: no I/O beyond reading the two candidate
files, no subprocess, no network, no exec.
"""

from __future__ import annotations

import errno as errno_module
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .models import LicenseVerdict, SeverityTier, Status

_PYPROJECT_FILENAME = "pyproject.toml"
_PIXI_FILENAME = "pixi.toml"

# The 6 recognized [tool.pyforge-warden] keys (hyphenated only — an
# underscore-spelled variant of any of these is UNRECOGNIZED, never
# silently accepted as an alias).
_RECOGNIZED_KEYS = frozenset(
    {
        "fail-on",
        "fail-under-coverage",
        "dep001-block-confidence",
        "waiver-default-expiry-days",
        "fail-on-kev",
        "allow-licenses",
        "deny-licenses",
    }
)

_FAIL_ON_CHOICES = ("critical", "high", "medium", "low", "none")

# Review finding (Story 3.2): an unbounded expiry window let a pathological
# config value overflow ``datetime.timedelta`` deep inside
# ``waiver.emit_bypass_stanza``, surfacing as an opaque uncaught
# ``OverflowError`` (internal-error, exit 2) instead of a clear
# config-validation failure at load time -- "fail at construction, not at
# first use" (this module's own established principle). 3650 days (10
# years) is far beyond any plausible waiver lifetime yet nowhere near
# ``timedelta``'s real ~2.7e6-year ceiling.
_MAX_WAIVER_DEFAULT_EXPIRY_DAYS = 3650

# Tier STRENGTH order, strongest first — local to this module (Never: never
# imported from vuln.py). Index doubles as "at-or-above" rank: a tier whose
# index is <= the configured fail_on's index is at least as severe.
_SEVERITY_ORDER: tuple[SeverityTier, ...] = (
    SeverityTier.CRITICAL,
    SeverityTier.HIGH,
    SeverityTier.MEDIUM,
    SeverityTier.LOW,
    SeverityTier.NONE,
)

_DEP001_BLOCK_CONFIDENCE_CHOICES = ("likely", "verified")

# Local confidence-tier rank (deliberately NOT extract.lockfiles.
# TRUSTED_MATCH_CONFIDENCE — see the module docstring's Never rationale):
# higher ranks are more trusted.
_CONFIDENCE_RANK: dict[str, int] = {"likely": 0, "verified": 1}


class _ConfigError(ValueError):
    """Base for this module's typed errors — carries any ``warnings``
    (config-key conflicts, a malformed-but-non-fatal ``pixi.toml``) gathered
    before this error was raised, via the ``warnings`` attribute (default
    ``()``), so a later exception never silently drops an earlier-gathered
    diagnostic (review finding). ``ConfigLoader.load`` sets it explicitly
    before re-raising; direct construction elsewhere gets the empty
    default."""

    def __init__(self, message: str, *, warnings: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.warnings = warnings


class ConfigParseError(_ConfigError):
    """Malformed TOML in the PRIMARY config source (``pyproject.toml``) —
    ``cli.py`` maps this to exit 2, ``AXIS_INGESTION``, owner ``"config"``;
    the rest of the scan still runs on ``EffectiveConfig.default()``."""


class ConfigValidationError(_ConfigError):
    """An unrecognized ``[tool.pyforge-warden]`` key (including an
    underscore-spelled variant of a real key), a non-table ``[tool]``/
    ``[tool.pyforge-warden]``, or a wrong-typed/out-of-range/unknown-enum
    value for a recognized key — raised regardless of which file it came
    from (only TOML SYNTAX failures get file-dependent treatment; see the
    module docstring). ``cli.py`` maps this to exit 2 the same way as
    ``ConfigParseError``."""


@dataclass(frozen=True)
class EffectiveConfig:
    """The resolved, applied policy for one scan — CLI flags, then
    ``pyproject.toml``, then ``pixi.toml``, then these hardcoded defaults
    (``ConfigLoader.load`` implements that precedence; this dataclass is
    just the resolved SHAPE). ``EffectiveConfig.default()`` (equivalently,
    ``EffectiveConfig()``) is what ``DefaultPolicy()`` (no ``config``
    argument) uses, reproducing every pre-3.1 caller's behavior byte-for-
    byte."""

    fail_on: SeverityTier = SeverityTier.CRITICAL
    fail_under_coverage: float = 0.0
    dep001_block_confidence: str = "verified"
    waiver_default_expiry_days: int = 14
    fail_on_kev: bool = True
    allow_licenses: tuple[str, ...] = ()
    deny_licenses: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Fail at construction, not at first use (review finding: without
        this, ``EffectiveConfig(fail_on=SeverityTier.UNKNOWN)`` succeeded
        silently and only raised later, confusingly, from inside
        ``vuln_severity_policy``'s ``_SEVERITY_ORDER.index`` lookup; an
        invalid ``dep001_block_confidence`` was silently treated as
        ``"verified"`` by ``_CONFIDENCE_RANK.get(..., fallback)`` instead of
        ever raising). ``ConfigLoader.load`` never constructs an invalid
        instance (every field already passed through ``_coerce_*``), so
        this guards direct/test construction only."""
        if self.fail_on not in _SEVERITY_ORDER:
            raise ValueError(
                f"fail_on must be one of {_FAIL_ON_CHOICES!r}, got {self.fail_on!r}"
            )
        if self.dep001_block_confidence not in _CONFIDENCE_RANK:
            raise ValueError(
                "dep001_block_confidence must be one of "
                f"{_DEP001_BLOCK_CONFIDENCE_CHOICES!r}, got "
                f"{self.dep001_block_confidence!r}"
            )
        if isinstance(self.fail_under_coverage, bool) or not (
            0.0 <= self.fail_under_coverage <= 100.0
        ):
            raise ValueError(
                "fail_under_coverage must be a number in [0, 100], got "
                f"{self.fail_under_coverage!r}"
            )
        if (
            isinstance(self.waiver_default_expiry_days, bool)
            or not isinstance(self.waiver_default_expiry_days, int)
            or not (0 < self.waiver_default_expiry_days <= _MAX_WAIVER_DEFAULT_EXPIRY_DAYS)
        ):
            raise ValueError(
                "waiver_default_expiry_days must be a positive int <= "
                f"{_MAX_WAIVER_DEFAULT_EXPIRY_DAYS}, got "
                f"{self.waiver_default_expiry_days!r}"
            )
        if not isinstance(self.fail_on_kev, bool):
            raise ValueError(
                f"fail_on_kev must be a bool, got {self.fail_on_kev!r}"
            )
        for field_name in ("allow_licenses", "deny_licenses"):
            value = getattr(self, field_name)
            # item.strip(), not bare item (follow-up review pass,
            # 2026-07-18): a whitespace-only entry constructed fine and
            # flipped license_gating True over a token _normalize_tokens
            # silently empties — inconsistent with _coerce_license_list's
            # own stripped-token guarantee for the CLI/TOML path.
            if not isinstance(value, tuple) or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise ValueError(
                    f"{field_name} must be a tuple of non-blank strings, got "
                    f"{value!r}"
                )

    @classmethod
    def default(cls) -> EffectiveConfig:
        """The built-in policy: identical to every field's dataclass
        default — a named entry point for callers that want to be explicit
        about "no config was loaded" (``cli.py``'s config-load failure
        fallback) without spelling out each field."""
        return cls()

    @classmethod
    def default_with_cli_overrides(
        cls,
        *,
        cli_fail_on: str | None = None,
        cli_fail_under_coverage: float | None = None,
        cli_allow_licenses: str | None = None,
        cli_deny_licenses: str | None = None,
    ) -> EffectiveConfig:
        """The built-in default, with any CLI-supplied overrides still
        applied (review finding: ``cli.py``'s config-load-failure fallback
        used to call ``.default()`` unconditionally, silently discarding an
        already-argparse-validated ``--fail-on``/``--fail-under-coverage``
        flag the user explicitly passed whenever the TOTALLY UNRELATED
        ``[tool.pyforge-warden]`` TOML failed to load). ``cli_fail_on``
        still goes through ``_coerce_fail_on`` (not a bare
        ``SeverityTier(...)`` call) so an invalid direct-caller value raises
        the module's own ``ConfigValidationError``, matching ``ConfigLoader.
        load``'s own CLI-override handling. ``cli_allow_licenses``/
        ``cli_deny_licenses`` (Story 6.2) follow the SAME pattern: an
        already-argparse-supplied ``--allow-licenses``/``--deny-licenses``
        flag must survive an unrelated config-load failure too."""
        defaults = cls.default()
        fail_on = (
            _coerce_fail_on(cli_fail_on) if cli_fail_on is not None else defaults.fail_on
        )
        fail_under_coverage = (
            _coerce_fail_under_coverage(cli_fail_under_coverage)
            if cli_fail_under_coverage is not None
            else defaults.fail_under_coverage
        )
        allow_licenses = (
            _coerce_allow_licenses(cli_allow_licenses)
            if cli_allow_licenses is not None
            else defaults.allow_licenses
        )
        deny_licenses = (
            _coerce_deny_licenses(cli_deny_licenses)
            if cli_deny_licenses is not None
            else defaults.deny_licenses
        )
        return cls(
            fail_on=fail_on,
            fail_under_coverage=fail_under_coverage,
            dep001_block_confidence=defaults.dep001_block_confidence,
            waiver_default_expiry_days=defaults.waiver_default_expiry_days,
            fail_on_kev=defaults.fail_on_kev,
            allow_licenses=allow_licenses,
            deny_licenses=deny_licenses,
        )

    @property
    def vuln_severity_policy(self) -> dict[SeverityTier, Status]:
        """The vulnerability-axis severity->status table ``--fail-on``
        derives: tiers at-or-above ``fail_on`` (in severity STRENGTH, per
        ``_SEVERITY_ORDER``) compose ``policy-violation``; tiers below
        compose ``warn``. ``SeverityTier.UNKNOWN`` is never a key in this
        table (it is absent from ``_SEVERITY_ORDER`` entirely) — callers
        (``status_for_severity_tier``) fall back to ``Status.INDETERMINATE``
        for any tier not present, so UNKNOWN degrades there unconditionally,
        never overridable by this table (C0). At the default
        (``fail_on=CRITICAL``), this table is byte-identical to ``vuln.
        DEFAULT_VULN_SEVERITY_POLICY``."""
        threshold_rank = _SEVERITY_ORDER.index(self.fail_on)
        return {
            tier: (
                Status.POLICY_VIOLATION if rank <= threshold_rank else Status.WARN
            )
            for rank, tier in enumerate(_SEVERITY_ORDER)
        }

    def is_confidence_trusted(self, mapping_confidence: str | None) -> bool:
        """Whether a component's ``mapping_confidence`` clears the
        configured ``dep001_block_confidence`` floor. ``None`` (no mapping
        opinion — most conda packages are legitimately non-Python/native)
        is ALWAYS trusted — a total map miss is not itself a distrust
        signal (mirrors ``DefaultPolicy.evaluate``'s pre-3.1 rationale). An
        unrecognized confidence STRING (rank -1, below every known tier) is
        never trusted — the same fail-closed bias every other unknown-token
        fallback in this codebase applies."""
        if mapping_confidence is None:
            return True
        threshold = _CONFIDENCE_RANK.get(
            self.dep001_block_confidence, _CONFIDENCE_RANK["verified"]
        )
        return _CONFIDENCE_RANK.get(mapping_confidence, -1) >= threshold

    @property
    def license_gating(self) -> bool:
        """Whether the license axis's gate is active this scan (Story 6.2,
        FR33's v1 gate-activation rule) — ``True`` iff ``allow_licenses`` or
        ``deny_licenses`` is non-empty. Threaded into the reported
        ``AxisCoverage.gating`` for the license axis
        (``report.assemble_report``) — transparency of configuration state,
        independent of the fact that real escalation itself is deferred to
        Story 6.5."""
        return bool(self.allow_licenses or self.deny_licenses)

    @property
    def license_policy(self) -> dict[LicenseVerdict, Status]:
        """The license-axis verdict->status table Story 6.5's real
        escalation will consult — mirrors ``vuln_severity_policy``'s shape
        (a plain dict, not the module-default ``MappingProxyType``, matching
        that property's own return type). Defined THIS story per the
        architecture's ownership split even though nothing consumes it yet:
        ``license.license_rung`` is a hard ``Status.WARN`` cap, oblivious to
        this table (see its own docstring). Every Finding-eligible verdict
        (``denied``/``unknown`` — ``allowed`` never reaches a ``Finding``)
        maps to ``Status.WARN``, matching ``license_rung``'s own cap
        byte-for-byte."""
        return {
            LicenseVerdict.DENIED: Status.WARN,
            LicenseVerdict.UNKNOWN: Status.WARN,
        }


def _extract_table(document: dict[str, object], *, source: str) -> dict[str, object]:
    """Pull ``[tool.pyforge-warden]`` out of a parsed TOML document — a
    non-table ``[tool]`` or ``[tool.pyforge-warden]`` is a typed
    ``ConfigValidationError`` (a SHAPE problem, not a syntax one), raised
    regardless of which file ``source`` names."""
    tool = document.get("tool", {})
    if not isinstance(tool, dict):
        raise ConfigValidationError(
            f"{source}: [tool] must be a table, got {type(tool).__name__}"
        )
    table = tool.get("pyforge-warden", {})
    if not isinstance(table, dict):
        raise ConfigValidationError(
            f"{source}: [tool.pyforge-warden] must be a table, got "
            f"{type(table).__name__}"
        )
    return table


def _coerce_fail_on(value: object) -> SeverityTier:
    if not isinstance(value, str) or value not in _FAIL_ON_CHOICES:
        raise ConfigValidationError(
            f"'fail-on' must be one of {_FAIL_ON_CHOICES!r}, got {value!r}"
        )
    return SeverityTier(value)


def _coerce_fail_under_coverage(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigValidationError(
            f"'fail-under-coverage' must be a number in [0, 100], got {value!r}"
        )
    numeric = float(value)
    if not (0.0 <= numeric <= 100.0):
        raise ConfigValidationError(
            f"'fail-under-coverage' must be in [0, 100], got {value!r}"
        )
    return numeric


def _describe_read_failure(exc: Exception) -> str:
    """A deterministic, locale/path-independent description of a TOML
    read/parse failure — mirrors ``cli.py``'s own symbolic-errno convention
    for an ``OSError`` (strerror text is locale-dependent and ``OSError.
    __str__`` embeds the absolute path; report bytes must not vary by
    locale or scan location). Every other exception here
    (``TOMLDecodeError``/``RecursionError``/``UnicodeDecodeError``) has no
    such problem — its ``str()`` carries no path, so it is used verbatim."""
    if isinstance(exc, OSError) and exc.errno is not None:
        return (
            f"[errno {errno_module.errorcode.get(exc.errno, str(exc.errno))}] "
            f"{exc.__class__.__name__}"
        )
    return str(exc)


def _coerce_dep001_block_confidence(value: object) -> str:
    if not isinstance(value, str) or value not in _DEP001_BLOCK_CONFIDENCE_CHOICES:
        raise ConfigValidationError(
            "'dep001-block-confidence' must be one of "
            f"{_DEP001_BLOCK_CONFIDENCE_CHOICES!r}, got {value!r}"
        )
    return value


def _coerce_waiver_default_expiry_days(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not (0 < value <= _MAX_WAIVER_DEFAULT_EXPIRY_DAYS)
    ):
        raise ConfigValidationError(
            "'waiver-default-expiry-days' must be a positive int <= "
            f"{_MAX_WAIVER_DEFAULT_EXPIRY_DAYS}, got {value!r}"
        )
    return value


def _coerce_fail_on_kev(value: object) -> bool:
    if not isinstance(value, bool):
        raise ConfigValidationError(
            f"'fail-on-kev' must be a bool, got {value!r}"
        )
    return value


def _coerce_license_list(value: object, *, key: str) -> tuple[str, ...]:
    """A comma-separated string OR a list of strings (Story 6.2) -> a tuple
    of stripped, non-empty tokens — the shared shape ``_coerce_allow_
    licenses``/``_coerce_deny_licenses`` wrap. Mirrors every other
    ``_coerce_*`` helper: a wrong-typed value is a ``ConfigValidationError``,
    raised regardless of source (a CLI-supplied value is always a ``str``;
    the TOML path may supply either shape). An entry that normalizes to
    empty text (blank/whitespace-only) is dropped, never turned into a
    spurious empty token.

    Fix 5 (review finding, 2026-07-18): this helper is only ever called
    when the key/flag was EXPLICITLY configured — ``ConfigLoader._load``
    gates the call on ``key in merged``, ``default_with_cli_overrides``/
    ``ConfigLoader._load``'s CLI-override branch gate it on
    ``cli_*_licenses is not None`` — so a result that resolves to zero
    usable entries (``""``, ``" , "``, ``[]``) always means the user
    explicitly configured an EMPTY gate, not that the gate was simply left
    unconfigured. Silently returning ``()`` here let ``license_gating``
    stay ``False`` with no error, even though the user believed they had
    activated the license gate — a typed ``ConfigValidationError`` instead,
    the same "fail at construction" posture every other ``_coerce_*``
    helper in this module already takes.

    Follow-up review pass (2026-07-18): every surviving entry must also
    normalize as a real SPDX expression (``license.is_valid_license_token``
    — single ids, compounds, ``WITH`` grants, and ``LicenseRef-*``
    references all pass; colloquial labels like ``GPLv3``/``BSD`` do not).
    A resolved component license is ALWAYS a normalized SPDX product, so an
    entry that cannot normalize the same way could never match anything:
    the gate reads as active (``license_gating=True``, ``gating: true`` in
    the report) while being structurally unable to fire — the same
    configured-but-ineffective fail-open the zero-usable-entries check
    above already rejects, one level deeper."""
    if isinstance(value, str):
        candidates: list[str] = value.split(",")
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        candidates = value
    else:
        raise ConfigValidationError(
            f"'{key}' must be a comma-separated string or a list of "
            f"strings, got {value!r}"
        )
    tokens = tuple(token.strip() for token in candidates if token.strip())
    if not tokens:
        raise ConfigValidationError(
            f"'{key}' was configured but resolved to zero usable entries "
            f"(got {value!r}) — omit the key/flag entirely instead of "
            "setting an empty gate"
        )
    invalid = [token for token in tokens if not _is_valid_license_token(token)]
    if invalid:
        raise ConfigValidationError(
            f"'{key}' entries {invalid!r} are not valid SPDX license "
            "expressions (nor LicenseRef-* references) — they could never "
            "match any resolved license, leaving the configured gate "
            "silently ineffective; use exact SPDX ids (e.g. 'GPL-3.0-only', "
            "not 'GPLv3')"
        )
    return tokens


def _is_valid_license_token(text: str) -> bool:
    # Lazy import (mirrors interfaces.py's own documented workaround):
    # license.py imports interfaces.py at module top, and interfaces.py
    # imports THIS module at module top — a top-level import here would
    # open a config -> license -> interfaces -> config cycle.
    from .license import is_valid_license_token

    return is_valid_license_token(text)


def _coerce_allow_licenses(value: object) -> tuple[str, ...]:
    return _coerce_license_list(value, key="allow-licenses")


def _coerce_deny_licenses(value: object) -> tuple[str, ...]:
    return _coerce_license_list(value, key="deny-licenses")


class ConfigLoader:
    """Loads + merges ``[tool.pyforge-warden]`` from ``pyproject.toml``
    (primary) and ``pixi.toml`` (secondary) into one ``EffectiveConfig``
    (see the module docstring for the full precedence/error-handling
    contract)."""

    def load(
        self,
        target: Path,
        *,
        cli_fail_on: str | None = None,
        cli_fail_under_coverage: float | None = None,
        cli_allow_licenses: str | None = None,
        cli_deny_licenses: str | None = None,
    ) -> tuple[EffectiveConfig, tuple[str, ...]]:
        """Resolve one scan's ``EffectiveConfig`` under ``target``. Returns
        ``(config, warnings)`` — ``warnings`` are stderr-destined diagnostic
        strings (config-key conflicts, a malformed-but-non-fatal
        ``pixi.toml``); ``cli.py`` is the sole caller and the sole emitter
        of those strings (this module performs no I/O beyond reading the
        two candidate files).

        Review finding: warnings gathered before a LATER-raised
        ``ConfigParseError``/``ConfigValidationError`` (e.g. a malformed-
        but-non-fatal ``pixi.toml`` warning, followed by an unrecognized-key
        failure) are attached to the raised exception as ``.warnings`` — the
        `except` block below runs regardless of WHERE this method raises,
        so no already-gathered warning is silently dropped."""
        warnings: list[str] = []
        try:
            return self._load(
                target,
                cli_fail_on=cli_fail_on,
                cli_fail_under_coverage=cli_fail_under_coverage,
                cli_allow_licenses=cli_allow_licenses,
                cli_deny_licenses=cli_deny_licenses,
                warnings=warnings,
            )
        except (ConfigParseError, ConfigValidationError) as exc:
            exc.warnings = tuple(warnings)
            raise

    def _load(
        self,
        target: Path,
        *,
        cli_fail_on: str | None,
        cli_fail_under_coverage: float | None,
        cli_allow_licenses: str | None,
        cli_deny_licenses: str | None,
        warnings: list[str],
    ) -> tuple[EffectiveConfig, tuple[str, ...]]:
        pyproject_table = self._read_table(
            target / _PYPROJECT_FILENAME,
            source=_PYPROJECT_FILENAME,
            hard_fail_on_parse_error=True,
            warnings=warnings,
        )
        pixi_table = self._read_table(
            target / _PIXI_FILENAME,
            source=_PIXI_FILENAME,
            hard_fail_on_parse_error=False,
            warnings=warnings,
        )
        merged = self._merge(pyproject_table, pixi_table, warnings=warnings)

        unrecognized = sorted(set(merged) - _RECOGNIZED_KEYS)
        if unrecognized:
            raise ConfigValidationError(
                f"unrecognized [tool.pyforge-warden] key(s): {unrecognized} "
                f"(recognized: {sorted(_RECOGNIZED_KEYS)})"
            )

        defaults = EffectiveConfig.default()
        fail_on = (
            _coerce_fail_on(merged["fail-on"])
            if "fail-on" in merged
            else defaults.fail_on
        )
        fail_under_coverage = (
            _coerce_fail_under_coverage(merged["fail-under-coverage"])
            if "fail-under-coverage" in merged
            else defaults.fail_under_coverage
        )
        dep001_block_confidence = (
            _coerce_dep001_block_confidence(merged["dep001-block-confidence"])
            if "dep001-block-confidence" in merged
            else defaults.dep001_block_confidence
        )
        waiver_default_expiry_days = (
            _coerce_waiver_default_expiry_days(merged["waiver-default-expiry-days"])
            if "waiver-default-expiry-days" in merged
            else defaults.waiver_default_expiry_days
        )
        fail_on_kev = (
            _coerce_fail_on_kev(merged["fail-on-kev"])
            if "fail-on-kev" in merged
            else defaults.fail_on_kev
        )
        allow_licenses = (
            _coerce_allow_licenses(merged["allow-licenses"])
            if "allow-licenses" in merged
            else defaults.allow_licenses
        )
        deny_licenses = (
            _coerce_deny_licenses(merged["deny-licenses"])
            if "deny-licenses" in merged
            else defaults.deny_licenses
        )

        # CLI flags win over both files. Routed through the SAME _coerce_*
        # helpers the TOML-sourced values use (review finding: a bare
        # SeverityTier(cli_fail_on) call raised an untyped ValueError,
        # bypassing this module's own ConfigValidationError, for a direct
        # caller that didn't pre-validate like argparse's `choices`/`type`
        # already do for cli.py's own call site) — a no-op for cli.py's
        # already-legal values, real validation for any other caller.
        if cli_fail_on is not None:
            fail_on = _coerce_fail_on(cli_fail_on)
        if cli_fail_under_coverage is not None:
            fail_under_coverage = _coerce_fail_under_coverage(cli_fail_under_coverage)
        if cli_allow_licenses is not None:
            allow_licenses = _coerce_allow_licenses(cli_allow_licenses)
        if cli_deny_licenses is not None:
            deny_licenses = _coerce_deny_licenses(cli_deny_licenses)

        config = EffectiveConfig(
            fail_on=fail_on,
            fail_under_coverage=fail_under_coverage,
            dep001_block_confidence=dep001_block_confidence,
            waiver_default_expiry_days=waiver_default_expiry_days,
            fail_on_kev=fail_on_kev,
            allow_licenses=allow_licenses,
            deny_licenses=deny_licenses,
        )
        return config, tuple(warnings)

    def _read_table(
        self,
        path: Path,
        *,
        source: str,
        hard_fail_on_parse_error: bool,
        warnings: list[str],
    ) -> dict[str, object]:
        """A missing file is normal (skip that source). A TOML SYNTAX
        failure OR an OS-level read failure (permission-denied, TOCTOU
        deletion, a wrong-encoding save, hostile parser-recursion nesting —
        the same hostile-input classes ``extract/pyproject.py`` already
        guards for this same filename) is file-dependent: ``pyproject.toml``
        (``hard_fail_on_parse_error=True``) raises ``ConfigParseError``;
        ``pixi.toml`` (``False``) appends a warning and is treated as
        absent. Once a document parses, its SHAPE (a non-table ``[tool]``/
        ``[tool.pyforge-warden]``) is a ``ConfigValidationError`` regardless
        of ``hard_fail_on_parse_error`` — only a read/syntax failure gets
        the file-dependent treatment."""
        if not path.is_file():
            return {}
        try:
            with path.open("rb") as handle:
                document = tomllib.load(handle)
        except (
            tomllib.TOMLDecodeError,
            UnicodeDecodeError,
            RecursionError,
            OSError,
        ) as exc:
            detail = _describe_read_failure(exc)
            if hard_fail_on_parse_error:
                raise ConfigParseError(
                    f"{source}: cannot read or parse: {detail}"
                ) from exc
            warnings.append(
                f"{source}: cannot read or parse ({detail}) — treated as absent"
            )
            return {}
        return _extract_table(document, source=source)

    def _merge(
        self,
        pyproject_table: dict[str, object],
        pixi_table: dict[str, object],
        *,
        warnings: list[str],
    ) -> dict[str, object]:
        """Per-key precedence: ``pyproject.toml`` wins a same-key conflict
        against ``pixi.toml``. A conflict (both files set the SAME key to
        DIFFERENT values) appends one warning naming the key and both
        values; an agreeing shared value produces no warning."""
        merged: dict[str, object] = dict(pixi_table)
        for key, value in pyproject_table.items():
            if key in merged and merged[key] != value:
                warnings.append(
                    f"config key {key!r} conflicts: pyproject.toml={value!r}, "
                    f"pixi.toml={merged[key]!r} — pyproject.toml wins"
                )
            merged[key] = value
        return merged
