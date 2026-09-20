"""Pixi candidate/currency ledger staleness gather (Story 21.7, CAP-4).

Compares each of the Dream's four dependency ledgers against ``pixi.toml``'s
own commit history: when ``pixi.toml`` has moved past a declared policy
threshold since a ledger section was last touched, emit a WARN naming the
ledger and how far behind it is. Advisory only — never gates.

See ``docs/dreams/pixi-candidate-currency.md`` and
``spec-pixi-candidate-currency`` CAP-4.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = (
    "PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS",
    "gather",
)

# Declared policy threshold — not a magic number buried in gather logic.
PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS = 30

_DREAM_REL = "docs/dreams/pixi-candidate-currency.md"
_PIXI_REL = "pixi.toml"

_CHECK_STALE = "pixi-currency-ledger-stale"
_CHECK_OK = "pixi-currency-ledger-current"
_CHECK_DREAM_UNREADABLE = "pixi-currency-dream-unreadable"
_CHECK_LEDGER_UNREADABLE = "pixi-currency-ledger-unreadable"
_CHECK_PIXI_UNREADABLE = "pixi-currency-pixi-toml-unreadable"


@dataclass(frozen=True)
class _LedgerSection:
    slug: str
    start_heading: str
    end_heading: str


_LEDGER_SECTIONS: tuple[_LedgerSection, ...] = (
    _LedgerSection(
        "candidate-ledger",
        "## The full candidate ledger",
        "## The version currency ledger",
    ),
    _LedgerSection(
        "version-currency-ledger",
        "## The version currency ledger",
        "## The channel-sourcing debt ledger",
    ),
    _LedgerSection(
        "channel-sourcing-ledger",
        "## The channel-sourcing debt ledger",
        "## The external-tracking gap ledger",
    ),
    _LedgerSection(
        "external-tracking-ledger",
        "## The external-tracking gap ledger",
        "## Constraints",
    ),
)


def _git(target: Path, *args: str) -> str | None:
    try:
        return run_git(target, list(args))
    except CliBridgeError, UnicodeDecodeError:
        return None


def _line_range_spec(start_heading: str, end_heading: str, dream_rel: str) -> str:
    start = re.escape(start_heading)
    re.escape(end_heading)
    return f"/^{start}/,/^## /:{dream_rel}"


def _last_section_commit(
    target: Path, dream_rel: str, start_heading: str, end_heading: str
) -> tuple[str | None, str | None]:
    """Return ``(commit_sha, commit_timestamp)`` for the ledger section, or
    ``(None, None)`` when git cannot report it."""
    spec = _line_range_spec(start_heading, end_heading, dream_rel)
    output = _git(target, "log", "-1", "--format=%H%x00%ci", "-L", spec)
    if not output:
        return None, None
    first_line = output.splitlines()[0]
    if "\x00" not in first_line:
        return None, None
    sha, timestamp = first_line.split("\x00", 1)
    sha = sha.strip()
    timestamp = timestamp.strip()
    if not sha or not timestamp:
        return None, None
    return sha, timestamp


def _pixi_commits_since(target: Path, since_sha: str) -> int | None:
    output = _git(
        target,
        "rev-list",
        "--count",
        f"{since_sha}..HEAD",
        "--",
        _PIXI_REL,
    )
    if output is None:
        return None
    try:
        return int(output.strip())
    except ValueError:
        return None


def _pixi_toml_readable(target: Path) -> bool:
    path = target / _PIXI_REL
    try:
        return path.is_file() and path.read_text(encoding="utf-8") != ""
    except OSError:
        return False


def gather(target: Path) -> tuple[Finding, ...]:
    """Judge whether each Dream ledger has fallen behind ``pixi.toml`` commits."""
    return degrade_on_exception(
        Source.PIXI_CURRENCY_LEDGER,
        _CHECK_STALE,
        lambda: _gather(target),
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    dream_path = target / _DREAM_REL
    if not dream_path.is_file():
        return (
            Finding(
                source=Source.PIXI_CURRENCY_LEDGER,
                check=_CHECK_DREAM_UNREADABLE,
                status=DoctorStatus.WARN,
                message=f"cannot read Dream ledger file {_DREAM_REL}",
                evidence={"path": _DREAM_REL},
            ),
        )

    if not _pixi_toml_readable(target):
        return (
            Finding(
                source=Source.PIXI_CURRENCY_LEDGER,
                check=_CHECK_PIXI_UNREADABLE,
                status=DoctorStatus.WARN,
                message=f"cannot read {_PIXI_REL}",
                evidence={"path": _PIXI_REL},
            ),
        )

    findings: list[Finding] = []
    stale_count = 0

    for section in _LEDGER_SECTIONS:
        sha, timestamp = _last_section_commit(
            target,
            _DREAM_REL,
            section.start_heading,
            section.end_heading,
        )
        if sha is None or timestamp is None:
            findings.append(
                Finding(
                    source=Source.PIXI_CURRENCY_LEDGER,
                    check=_CHECK_LEDGER_UNREADABLE,
                    status=DoctorStatus.WARN,
                    message=(f"cannot read ledger section {section.slug!r} from {_DREAM_REL}"),
                    evidence={
                        "ledger": section.slug,
                        "dream": _DREAM_REL,
                        "start_heading": section.start_heading,
                    },
                )
            )
            continue

        pixi_commits = _pixi_commits_since(target, sha)
        if pixi_commits is None:
            findings.append(
                Finding(
                    source=Source.PIXI_CURRENCY_LEDGER,
                    check=_CHECK_PIXI_UNREADABLE,
                    status=DoctorStatus.WARN,
                    message=(f"cannot count {_PIXI_REL} commits since {section.slug} was last updated"),
                    evidence={"ledger": section.slug, "since_commit": sha},
                )
            )
            continue

        if pixi_commits > PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS:
            stale_count += 1
            findings.append(
                Finding(
                    source=Source.PIXI_CURRENCY_LEDGER,
                    check=_CHECK_STALE,
                    status=DoctorStatus.WARN,
                    message=(
                        f"{section.slug} is {pixi_commits} {_PIXI_REL} commit(s) "
                        f"behind (threshold "
                        f"{PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS}; last "
                        f"ledger touch {timestamp})"
                    ),
                    evidence={
                        "ledger": section.slug,
                        "pixi_commits_since_ledger_touch": pixi_commits,
                        "threshold_pixi_commits": (PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS),
                        "ledger_last_commit": sha,
                        "ledger_last_touch": timestamp,
                        "pixi_toml": _PIXI_REL,
                        "dream": _DREAM_REL,
                    },
                )
            )

    if findings:
        return tuple(findings)

    return (
        Finding(
            source=Source.PIXI_CURRENCY_LEDGER,
            check=_CHECK_OK,
            status=DoctorStatus.OK,
            message=(
                f"all {len(_LEDGER_SECTIONS)} pixi-currency ledgers are within "
                f"{PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS} {_PIXI_REL} "
                "commit(s) of their last update"
            ),
            evidence={
                "ledgers_checked": len(_LEDGER_SECTIONS),
                "threshold_pixi_commits": PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS,
            },
        ),
    )
