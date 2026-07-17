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

This module parses TOML as DATA: no I/O beyond reading the two candidate
files, no subprocess, no network, no exec.
"""

from __future__ import annotations

import errno as errno_module
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .models import SeverityTier, Status

_PYPROJECT_FILENAME = "pyproject.toml"
_PIXI_FILENAME = "pixi.toml"

# The 3 recognized [tool.pyforge-warden] keys (hyphenated only — an
# underscore-spelled variant of any of these is UNRECOGNIZED, never
# silently accepted as an alias).
_RECOGNIZED_KEYS = frozenset(
    {"fail-on", "fail-under-coverage", "dep001-block-confidence"}
)

_FAIL_ON_CHOICES = ("critical", "high", "medium", "low", "none")

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
        load``'s own CLI-override handling."""
        defaults = cls.default()
        fail_on = (
            _coerce_fail_on(cli_fail_on) if cli_fail_on is not None else defaults.fail_on
        )
        fail_under_coverage = (
            _coerce_fail_under_coverage(cli_fail_under_coverage)
            if cli_fail_under_coverage is not None
            else defaults.fail_under_coverage
        )
        return cls(
            fail_on=fail_on,
            fail_under_coverage=fail_under_coverage,
            dep001_block_confidence=defaults.dep001_block_confidence,
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

        config = EffectiveConfig(
            fail_on=fail_on,
            fail_under_coverage=fail_under_coverage,
            dep001_block_confidence=dep001_block_confidence,
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
