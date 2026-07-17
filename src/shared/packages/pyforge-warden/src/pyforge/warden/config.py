"""Per-repo policy configuration -- the ``ConfigLoader`` (Story 3.1, FR30).

Ownership decisions recorded:

* ``[tool.pyforge-warden]`` resolves from the SCANNED PROJECT's own root
  ``pyproject.toml``/``pixi.toml`` -- read directly here, never through
  ``discovery.py``'s recursive manifest walk, which serves a different
  concern (finding dependency manifests anywhere under ``target``,
  including nested/vendored ones a tool-config lookup must never consult).
* Precedence (FR30): ``pyproject.toml`` wins a same-key conflict;
  ``pixi.toml`` fills any key ``pyproject.toml`` leaves unset. A same-key
  conflict (both files set it to DIFFERING values) is returned as a plain
  message for the caller (``cli.py``) to print to stderr -- never raised,
  never fails the build. CLI-supplied overrides win over both files
  unconditionally.
* A ``[tool.pyforge-warden]`` table that IS present in a STRUCTURALLY
  VALID TOML document but has a wrong-shaped key -- unrecognized key,
  wrong-typed value, an enum value outside its closed vocabulary, an
  out-of-range int -- is a PER-KEY validation failure, never a
  whole-function abort (review finding, 2026-07-17): ``load_config``
  collects each bad key as a message and falls back to that ONE key's
  default, so a malformed key never destroys another key's
  already-resolved value -- including a CLI override for a DIFFERENT key,
  which must keep winning unconditionally exactly as the precedence rule
  above promises. ``cli.py`` is the sole consumer of the returned
  ``validation_errors`` tuple: it records one ``ErrorKind.CONFIG_VALIDATION``
  via the existing ``_record_error`` seam per message (typed record + error
  rung + stderr diagnostic; report still emitted). ``ConfigValidationError``
  (still raised, not collected) is reserved for a STRUCTURAL failure with no
  sensible per-key recovery -- ``[tool.pyforge-warden]`` itself not being a
  table. ``ErrorKind.CONFIG_PARSE`` stays reserved/unused (as it is today).
  A file that is ITSELF malformed/unreadable TOML is deliberately NOT
  diagnosed here (see ``_read_tool_table``) -- extraction's own pass over
  the same file already owns that diagnosis as ``unparsable-manifest``, and
  duplicating it here as a different error kind would misclassify a broken
  manifest as a config mistake.
* ``DEFAULT_HYGIENE_POLICY``/``DEFAULT_VULN_SEVERITY_POLICY`` relocate
  HERE from ``hygiene.py``/``vuln.py`` (closes the ``deferred-work.md``
  item raised at 1.6's review): both are now ``MappingProxyType``-wrapped
  so an in-process mutation can never alter the effective policy for the
  remainder of a run. ``hygiene.py``/``vuln.py`` re-import the same names
  so every existing reference/test keeps resolving unchanged. Only the
  vuln table is independently overridable in v1, via ``fail_on`` (FR18's
  CVSS-threshold surface) -- the hygiene table's relocation is a
  data-ownership move only; v1 exposes no per-DEP-code override.
* ``dep001_min_confidence`` governs ONLY ``interfaces.py``'s scan-wide
  DEP001-block trust gate -- a SEPARATE concern from
  ``extract/_identity.py``'s ``TRUSTED_MATCH_CONFIDENCE``, which stays
  fixed at ``"verified"`` as Epic 2's own extraction-time trust bar for
  setting ``pypi_identity`` at all. Widening this threshold to
  ``"likely"`` only widens what ``DefaultPolicy.evaluate()`` trusts enough
  to let DEP001 block; it never changes what gets matched against CVEs.
* ``fail_under_coverage`` (FR19, default OFF/``None``) is RESOLVED here
  (parsed, validated, precedence-merged) but ENFORCED in
  ``interfaces.py``'s ``DefaultPolicy.evaluate()`` -- this module has no
  inventory/engine-result vocabulary of its own.

This module does no I/O beyond reading the two candidate TOML files under
``target``; no subprocess, no network, no clock.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .models import SeverityTier, Status

PYPROJECT_FILENAME = "pyproject.toml"
PIXI_TOML_FILENAME = "pixi.toml"
CONFIG_TABLE = "pyforge-warden"  # the table name under [tool.<CONFIG_TABLE>]

# --- relocated defaults (Story 1.3 / Story 1.6 origin -- see module
# docstring) -----------------------------------------------------------------

DEFAULT_HYGIENE_POLICY: Mapping[str, Status] = MappingProxyType(
    {
        "DEP001": Status.POLICY_VIOLATION,
        "DEP002": Status.WARN,
        "DEP003": Status.WARN,
        "DEP004": Status.WARN,
        "DEP005": Status.WARN,
    }
)

DEFAULT_VULN_SEVERITY_POLICY: Mapping[SeverityTier, Status] = MappingProxyType(
    {
        SeverityTier.CRITICAL: Status.POLICY_VIOLATION,
        SeverityTier.HIGH: Status.WARN,
        SeverityTier.MEDIUM: Status.WARN,
        SeverityTier.LOW: Status.WARN,
        SeverityTier.NONE: Status.WARN,
    }
)

DEFAULT_FAIL_ON = SeverityTier.CRITICAL
DEFAULT_DEP001_MIN_CONFIDENCE = "verified"
DEFAULT_FAIL_UNDER_COVERAGE: int | None = None

# SeverityTier rank, most-severe first -- fail_on's chosen tier and every
# tier AT LEAST as severe escalate to policy-violation; UNKNOWN is
# deliberately absent from this table (mirrors DEFAULT_VULN_SEVERITY_POLICY's
# own docstring precedent): an unassessable severity is never treated as
# safely non-blocking, regardless of fail_on.
_SEVERITY_RANK: dict[SeverityTier, int] = {
    SeverityTier.CRITICAL: 0,
    SeverityTier.HIGH: 1,
    SeverityTier.MEDIUM: 2,
    SeverityTier.LOW: 3,
    SeverityTier.NONE: 4,
}

# The closed --fail-on / fail_on vocabulary (public: cli.py's argparse
# `choices=` reuses this so the CLI surface and the config-file surface can
# never drift apart).
FAIL_ON_CHOICES: tuple[str, ...] = tuple(
    tier.value
    for tier in (
        SeverityTier.CRITICAL,
        SeverityTier.HIGH,
        SeverityTier.MEDIUM,
        SeverityTier.LOW,
    )
)

# The closed dep001_min_confidence vocabulary -- "verified" trusts only an
# exact TRUSTED_MATCH_CONFIDENCE hit (today's behavior); "likely" widens
# trust to include an ambiguous conda->pypi mapping hit too.
_DEP001_MIN_CONFIDENCE_CHOICES: tuple[str, ...] = ("verified", "likely")

# Public bounds reused by cli.py's --fail-under-coverage argparse type
# function, so the CLI and config-file surfaces share one source of truth.
FAIL_UNDER_COVERAGE_MIN = 0
FAIL_UNDER_COVERAGE_MAX = 100


def _vuln_policy_for(fail_on: SeverityTier) -> Mapping[SeverityTier, Status]:
    """Derive the CVSS severity->status table for one ``fail_on`` threshold:
    every tier at least as severe as ``fail_on`` escalates to
    ``policy-violation``; weaker tiers stay ``warn``. ``UNKNOWN`` is
    deliberately absent (see ``_SEVERITY_RANK``'s comment) -- an
    unassessable severity is never treated as safely non-blocking."""
    threshold = _SEVERITY_RANK[fail_on]
    return MappingProxyType(
        {
            tier: (
                Status.POLICY_VIOLATION if rank <= threshold else Status.WARN
            )
            for tier, rank in _SEVERITY_RANK.items()
        }
    )


class ConfigValidationError(ValueError):
    """A ``[tool.pyforge-warden]`` table failed to parse, or a key/value did
    not match its expected shape (unrecognized key, wrong type, an enum
    value outside its closed vocabulary, an out-of-range int). The one
    typed-error boundary this module raises -- ``cli.py`` is the sole
    catcher (see module docstring)."""


@dataclass(frozen=True)
class WardenConfig:
    """The fully-resolved, immutable policy configuration for one scan.

    ``__post_init__`` validates ``fail_on``/``dep001_min_confidence``
    against their closed vocabularies (review finding, 2026-07-17) --
    mirrors ``models.py``'s own frozen-dataclass convention (e.g.
    ``Severity``, ``ErrorRecord``). This closes two gaps at once: a
    directly-constructed ``WardenConfig`` (bypassing ``load_config``) can no
    longer reach ``interfaces.py``'s ``_DEP001_TRUSTED_CONFIDENCES`` lookup
    with an out-of-vocabulary value and crash with an uncaught ``KeyError``
    instead of a typed construction error; and the vocabulary itself is
    single-sourced (``_DEP001_MIN_CONFIDENCE_CHOICES``/``FAIL_ON_CHOICES``)
    so ``config.py`` and ``interfaces.py`` can never independently drift."""

    fail_on: SeverityTier = DEFAULT_FAIL_ON
    dep001_min_confidence: str = DEFAULT_DEP001_MIN_CONFIDENCE
    fail_under_coverage: int | None = DEFAULT_FAIL_UNDER_COVERAGE
    hygiene_policy: Mapping[str, Status] = DEFAULT_HYGIENE_POLICY
    vuln_severity_policy: Mapping[SeverityTier, Status] = DEFAULT_VULN_SEVERITY_POLICY

    def __post_init__(self) -> None:
        # SeverityTier is a StrEnum: a member compares equal to its own
        # string value, so `in FAIL_ON_CHOICES` (a tuple of the tier
        # strings) validates both a real SeverityTier member AND a raw
        # string smuggled in by a non-load_config caller, in one check.
        if self.fail_on not in FAIL_ON_CHOICES:
            raise ValueError(
                f"fail_on must be one of {FAIL_ON_CHOICES!r}, got {self.fail_on!r}"
            )
        if self.dep001_min_confidence not in _DEP001_MIN_CONFIDENCE_CHOICES:
            raise ValueError(
                "dep001_min_confidence must be one of "
                f"{_DEP001_MIN_CONFIDENCE_CHOICES!r}, got "
                f"{self.dep001_min_confidence!r}"
            )

    @classmethod
    def defaults(cls) -> "WardenConfig":
        """The all-default config -- ``DefaultPolicy()`` with no config
        supplied (every pre-3.1 caller/test) resolves to exactly this,
        preserving today's hardcoded behavior byte-for-byte."""
        return cls()


def _read_tool_table(path: Path) -> dict[str, object]:
    """Read ``[tool.pyforge-warden]`` from one TOML file -- ``{}`` if the
    file is absent, unreadable, or not valid TOML.

    A malformed/unreadable manifest is deliberately NOT this module's
    concern to diagnose: extraction's own pass over the SAME file
    (``discovery.py`` -> ``extract/pyproject.py``/``extract/pixi.py``)
    already classifies it as ``unparsable-manifest`` moments later.
    Raising a SECOND, DIFFERENT error kind (``config-validation``) here for
    the identical root cause would misclassify a broken manifest as a
    config mistake and double-report one failure. This module raises
    ``ConfigValidationError`` only for a STRUCTURALLY VALID TOML document
    whose ``[tool.pyforge-warden]`` table itself has a wrong-shaped
    key/value (see ``load_config``/the validators below). The caught
    exception tuple mirrors ``extract/pyproject.py``'s own tomllib error
    taxonomy exactly (``TOMLDecodeError``, ``UnicodeDecodeError`` -- a
    wrong-encoding save, NOT a ``TOMLDecodeError`` subclass --
    ``RecursionError`` -- hostile/corrupt nesting overflowing tomllib's
    recursive parser) plus ``OSError`` for an unreadable file (permission,
    TOCTOU deletion)."""
    if not path.is_file():
        return {}
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, RecursionError, OSError):
        return {}
    tool = document.get("tool")
    if not isinstance(tool, dict):
        return {}
    table = tool.get(CONFIG_TABLE)
    if table is None:
        return {}
    if not isinstance(table, dict):
        raise ConfigValidationError(
            f"{path}: [tool.{CONFIG_TABLE}] must be a table, got "
            f"{type(table).__name__}"
        )
    return table


def _validate_fail_on(raw: object) -> SeverityTier | None:
    """``None`` on failure (never raises -- see ``load_config``): the caller
    collects a message and falls back to ``DEFAULT_FAIL_ON``."""
    if isinstance(raw, str) and raw in FAIL_ON_CHOICES:
        return SeverityTier(raw)
    return None


def _validate_dep001_min_confidence(raw: object) -> str | None:
    """``None`` on failure -- see ``_validate_fail_on``."""
    if isinstance(raw, str) and raw in _DEP001_MIN_CONFIDENCE_CHOICES:
        return raw
    return None


def _validate_fail_under_coverage(raw: object) -> int | None:
    """``None`` on failure -- see ``_validate_fail_on``."""
    if (
        not isinstance(raw, bool)
        and isinstance(raw, int)
        and FAIL_UNDER_COVERAGE_MIN <= raw <= FAIL_UNDER_COVERAGE_MAX
    ):
        return raw
    return None


# The complete set of recognized [tool.pyforge-warden] keys (Story 3.1's v1
# surface) -- any other key is a config-validation error, never silently
# ignored (a typo like `fail_on_` must not read as "unset").
_RECOGNIZED_KEYS = frozenset(
    {"fail_on", "dep001_min_confidence", "fail_under_coverage"}
)


def load_config(
    target: Path,
    *,
    cli_fail_on: str | None = None,
    cli_fail_under_coverage: int | None = None,
) -> tuple[WardenConfig, tuple[str, ...], tuple[str, ...]]:
    """Resolve ``WardenConfig`` for one scan of ``target``.

    Precedence (FR30): ``pyproject.toml``'s ``[tool.pyforge-warden]`` wins a
    same-key conflict against ``pixi.toml``'s; a key present in only one
    file applies from that file; a CLI override (non-``None``) wins over
    both files unconditionally -- INCLUDING when a DIFFERENT key fails
    validation (review finding, 2026-07-17): each key is resolved and
    validated independently, so one bad key can never discard another
    key's already-resolved value. Conflicts and per-key validation
    failures are both returned as plain message tuples for the caller to
    print/record -- never raised, never fail the build, never lost to an
    early return. ``ConfigValidationError`` is reserved for a STRUCTURAL
    failure (``[tool.pyforge-warden]`` itself not a table) with no
    sensible per-key fallback -- ``cli.py`` is the sole catcher for that
    one case."""
    pyproject_table = _read_tool_table(target / PYPROJECT_FILENAME)
    pixi_table = _read_tool_table(target / PIXI_TOML_FILENAME)

    conflicts: list[str] = []
    resolved: dict[str, object] = {}
    for key in sorted(set(pyproject_table) | set(pixi_table)):
        in_pyproject = key in pyproject_table
        in_pixi = key in pixi_table
        if in_pyproject and in_pixi and pyproject_table[key] != pixi_table[key]:
            conflicts.append(
                f"config key {key!r} conflicts between {PYPROJECT_FILENAME} "
                f"({pyproject_table[key]!r}) and {PIXI_TOML_FILENAME} "
                f"({pixi_table[key]!r}) -- {PYPROJECT_FILENAME} wins"
            )
        resolved[key] = pyproject_table[key] if in_pyproject else pixi_table[key]

    errors: list[str] = []
    source = f"[tool.{CONFIG_TABLE}]"

    unknown_keys = sorted(set(resolved) - _RECOGNIZED_KEYS)
    if unknown_keys:
        errors.append(f"{source}: unrecognized key(s) {unknown_keys!r}")

    if cli_fail_on is not None:
        # A CLI value is trusted by construction (argparse's own
        # `choices=FAIL_ON_CHOICES` already rejected anything else before
        # this function is ever called) -- never re-validated, never
        # allowed to fall back to the file/default.
        fail_on = SeverityTier(cli_fail_on)
    elif "fail_on" in resolved:
        validated = _validate_fail_on(resolved["fail_on"])
        if validated is None:
            errors.append(
                f"{source}: fail_on must be one of {FAIL_ON_CHOICES!r}, "
                f"got {resolved['fail_on']!r}"
            )
            fail_on = DEFAULT_FAIL_ON
        else:
            fail_on = validated
    else:
        fail_on = DEFAULT_FAIL_ON

    if "dep001_min_confidence" in resolved:
        validated_confidence = _validate_dep001_min_confidence(
            resolved["dep001_min_confidence"]
        )
        if validated_confidence is None:
            errors.append(
                f"{source}: dep001_min_confidence must be one of "
                f"{_DEP001_MIN_CONFIDENCE_CHOICES!r}, got "
                f"{resolved['dep001_min_confidence']!r}"
            )
            dep001_min_confidence = DEFAULT_DEP001_MIN_CONFIDENCE
        else:
            dep001_min_confidence = validated_confidence
    else:
        dep001_min_confidence = DEFAULT_DEP001_MIN_CONFIDENCE

    if cli_fail_under_coverage is not None:
        # Trusted by construction -- see the fail_on CLI branch above:
        # cli.py's own argparse `type=` already bounds-checked this value.
        fail_under_coverage = cli_fail_under_coverage
    elif "fail_under_coverage" in resolved:
        validated_coverage = _validate_fail_under_coverage(
            resolved["fail_under_coverage"]
        )
        if validated_coverage is None:
            errors.append(
                f"{source}: fail_under_coverage must be an integer in "
                f"[{FAIL_UNDER_COVERAGE_MIN}, {FAIL_UNDER_COVERAGE_MAX}], "
                f"got {resolved['fail_under_coverage']!r}"
            )
            fail_under_coverage = DEFAULT_FAIL_UNDER_COVERAGE
        else:
            fail_under_coverage = validated_coverage
    else:
        fail_under_coverage = DEFAULT_FAIL_UNDER_COVERAGE

    config = WardenConfig(
        fail_on=fail_on,
        dep001_min_confidence=dep001_min_confidence,
        fail_under_coverage=fail_under_coverage,
        hygiene_policy=DEFAULT_HYGIENE_POLICY,
        vuln_severity_policy=(
            DEFAULT_VULN_SEVERITY_POLICY
            if fail_on is DEFAULT_FAIL_ON
            else _vuln_policy_for(fail_on)
        ),
    )
    return config, tuple(conflicts), tuple(errors)
