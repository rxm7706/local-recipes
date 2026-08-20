"""The bmad-method-version-drift gather filter -- Doctor's verdict on
whether the installed BMAD-METHOD framework version meets ``pixi.toml``'s
own declared floor (Story 10.1, Epic 10/CAP-1), and separately, whether that
same installed version is behind the latest release actually published
upstream (Story 10.2, Epic 10/CAP-2) -- a stale declared floor can hide a
further-behind reality, since CAP-1 only ever compares against what
``pixi.toml`` itself claims.

**Why this module exists, and why it is a dedicated file rather than an
extension of ``sources/factory.py``'s existing ``BMAD_DRIFT``.** ``BMAD_DRIFT``
judges a DIFFERENT artifact class entirely -- ``pyforge-marshal``'s own
project-doc currency (skill version, schema version, MCP tool counts, ...),
ported from ``bmad_drift_check.py`` and tightly coupled to that script's own
HARD/DRIFT/INFO severity mapping. This module has no such origin script and
a single trivial version comparison: ``pixi.toml`` declares
``bmad-method >=X.Y.Z`` in one or more ``[feature.*.dependencies]`` tables,
and ``_bmad/_config/manifest.yaml``'s ``installation.version`` is what was
actually installed. A small dedicated module (mirroring ``sources/ledger.py``)
is simpler to review than overloading an already-dense 1300-line file with an
unrelated artifact class.

**The independence rule.** This module reads two already-tracked files
directly -- ``pixi.toml`` (``tomllib``, stdlib) and
``_bmad/_config/manifest.yaml`` (``yaml.safe_load``, the existing PyYAML
run-dependency ``sources/chain.py`` also uses) -- no subprocess, no git
history (CAP-2 adds one narrow network exception -- see below). It never
imports ``pyforge.marshal``, any other station package, or ``bmad_loop``;
``tests/meta/test_source_independence.py`` enforces this fleet-wide, same
as every sibling source.

**Degrades, never crashes** -- the house rule for every Doctor source. Unlike
``sources/ledger.py``'s bespoke git-error handling, this module has no git
history to reason about, so it mirrors ``sources/chain.py``'s/
``sources/factory.py``'s plain shape instead: ``_parse_version`` and
``_declared_floors`` both RAISE on anything unexpected (a missing file, a
non-``X.Y.Z`` version string, an unrecognized constraint form, ``bmad-method``
absent from every dependencies table) rather than handling it ad hoc inline --
``gather``'s own ``sources.degrade_on_exception`` wrapper is the one outer net
that turns any such exception into a single WARN ``Finding`` naming it.

**Never gates.** Status is always ``ok`` or ``warn``, never ``fail`` -- this
signal informs (mirrors ``Source.DUE_FOR_VERIFICATION``'s own always-warn
discipline); CAP-3's non-gating rule is enforced downstream by
``verdict.exit_code_for``, unaffected by a ``warn`` Finding either way.

**CAP-2's one exception to "no network, no subprocess."** ``_fetch_latest_
upstream_version`` queries npm's own public registry live (``GET https://
registry.npmjs.org/bmad-method/latest``, stdlib ``urllib.request`` only --
mirrors ``pyforge-mason``'s ``pypi_index.py::version_exists``, the fleet's
own precedent for a bare unauthenticated JSON-index GET). Fail-open is
silent: every failure mode the network can produce folds to ``None`` inside
that helper itself and never raises, so a registry outage degrades CAP-2 to
"adds nothing" rather than affecting CAP-1's own Finding or triggering the
outer ``degrade_on_exception`` WARN. Nothing fetched is ever persisted --
every ``gather()`` call pays its own round-trip (mirrors ``pypi_index.py``'s
own no-local-persistence precedent).
"""

from __future__ import annotations

import http.client
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

import tomllib
import yaml

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather",)

#: The dependency name as declared in every ``pixi.toml`` dependencies table.
DEPENDENCY_NAME = "bmad-method"

#: Matches a plain ``>=X.Y.Z`` floor constraint -- the only form observed in
#: this repo's own ``pixi.toml`` today (Boundaries: no ``packaging``
#: dependency is warranted for a single constraint shape).
_FLOOR_RE = re.compile(r"^>=(\d+\.\d+\.\d+)$")


def _parse_version(text: str) -> tuple[int, int, int]:
    """``"6.11.0"`` -> ``(6, 11, 0)``. Raises ``ValueError`` on anything that
    is not exactly three dot-separated PLAIN-DIGIT segments -- caught by the
    outer ``degrade_on_exception``, never handled ad hoc inline here.
    ``str.isdigit()``, not a bare ``int()`` call: ``int()`` alone accepts a
    leading ``-`` (``int("-1") == -1``), which would silently parse a
    corrupt/adversarial ``-1.2.3`` into a comparable-but-nonsensical version
    (review finding) -- a real version component is never negative."""
    parts = text.strip().split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"expected X.Y.Z (plain digits), got {text!r}")
    return tuple(int(p) for p in parts)


def _dependency_tables(data: dict) -> list[dict]:
    """Every dependencies table in a ``pixi.toml`` document that could
    plausibly declare ``bmad-method``: the top-level ``[dependencies]``,
    every ``[feature.*.dependencies]``, and every platform-scoped
    ``[target.*.dependencies]`` / ``[feature.*.target.*.dependencies]`` --
    ``pixi.toml`` supports pinning a dependency only for a specific platform
    target, and a floor declared ONLY there would otherwise go silently
    unseen (review finding). No occurrence in this repo's own ``pixi.toml``
    uses a target-scoped table for ``bmad-method`` today, but a source that
    only reads part of what pixi.toml can declare is a coverage gap waiting
    to bite the moment one is added."""
    tables = [data.get("dependencies", {}) or {}]
    for target in (data.get("target", {}) or {}).values():
        tables.append(target.get("dependencies", {}) or {})
    for feature in (data.get("feature", {}) or {}).values():
        tables.append(feature.get("dependencies", {}) or {})
        for target in (feature.get("target", {}) or {}).values():
            tables.append(target.get("dependencies", {}) or {})
    return tables


def _declared_floors(data: dict) -> list[tuple[int, int, int]]:
    """Every declared ``bmad-method`` floor across every dependencies table
    ``_dependency_tables`` finds -- ``pixi.toml`` declares it in more than
    one place today (``feature.python``, ``feature.local-recipes``), so this
    walks every occurrence rather than assuming exactly one line
    (Boundaries).

    Raises ``ValueError`` if ``bmad-method`` is declared nowhere at all, or if
    any declared constraint does not match the plain ``>=X.Y.Z`` form
    ``_FLOOR_RE`` expects (e.g. ``==6.11.0``, ``*``, a git URL) -- both are
    "cannot evaluate", left to the outer ``degrade_on_exception`` to convert
    into one WARN ``Finding`` rather than handled here.
    """
    floors: list[tuple[int, int, int]] = []
    for table in _dependency_tables(data):
        constraint = table.get(DEPENDENCY_NAME)
        if constraint is None:
            continue
        match = _FLOOR_RE.match(str(constraint).strip())
        if not match:
            raise ValueError(
                f"unrecognized {DEPENDENCY_NAME!r} constraint form: {constraint!r}"
            )
        floors.append(_parse_version(match.group(1)))

    if not floors:
        raise ValueError(
            f"{DEPENDENCY_NAME!r} is not declared in any dependencies table"
        )
    return floors


#: npm's own public, unauthenticated per-package ``/latest`` endpoint --
#: returns a JSON body shaped ``{"name": "bmad-method", "version": "X.Y.Z",
#: ...}`` on success. Mirrors ``pyforge-mason``'s ``pypi_index.py``'s own
#: ``_PYPI_JSON_INDEX_URL_TEMPLATE`` precedent for a bare unauthenticated
#: JSON-index GET, aimed at npm's registry instead of PyPI's -- bmad-method
#: ships on npm, not PyPI.
_NPM_LATEST_URL = "https://registry.npmjs.org/bmad-method/latest"

#: Deliberately shorter than ``pypi_index.py``'s own 30s: that precedent is
#: for ``ship_pypi``'s one-shot, human-triggered publish flow, while this
#: source runs ambiently and repeatedly (every ``doctor check``/``monitor``
#: invocation, once Story 10.3 wires it in) -- a short timeout keeps a
#: slow/unreachable registry from stalling an otherwise-fast local check for
#: long. Both numbers are metadata-GET-tier per the fleet's own convention
#: (``engines.gh._GH_PR_LIST_TIMEOUT_SECONDS``); this value is this story's
#: own judgment call for the ambient-check tier, not drawn from an existing
#: constant.
_UPSTREAM_FETCH_TIMEOUT_SECONDS = 5.0


def _fetch_latest_upstream_version(*, timeout: float | None = None) -> tuple[int, int, int] | None:
    """Query npm's own public registry for bmad-method's latest published
    release (Story 10.2, CAP-2) -- mirrors ``pypi_index.py``'s
    ``version_exists`` as the fleet's own precedent for a bare
    unauthenticated JSON-index GET. Unlike that function's 404-vs-other
    split, every failure mode here folds to the SAME outcome: CAP-2 has no
    "conclusively does not exist" answer to give, only "succeeded" or
    "could not determine."

    Never raises: an ``HTTPError``, ``URLError``, a malformed/truncated HTTP
    response (``http.client.HTTPException`` -- NOT an ``OSError`` subclass,
    unlike ``RemoteDisconnected``, so it needs its own name in this tuple;
    review finding, Story 10.2), ``OSError``, ``TimeoutError``, a malformed
    JSON body, or a missing/unparseable ``"version"`` field all fold to
    ``None`` (Boundaries). The ``"version"`` string is parsed with
    ``_parse_version`` exactly as CAP-1 parses ``manifest.yaml``'s own
    version, so both capabilities share one parsing/validation path and a
    malformed npm version string degrades the same way a malformed local one
    does (Design Notes)."""
    resolved_timeout = timeout if timeout is not None else _UPSTREAM_FETCH_TIMEOUT_SECONDS
    try:
        with urllib.request.urlopen(_NPM_LATEST_URL, timeout=resolved_timeout) as response:
            body = json.loads(response.read())
        return _parse_version(str(body["version"]))
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        http.client.HTTPException,
        OSError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
    ):
        return None


def gather(target: Path) -> tuple[Finding, ...]:
    """Compare ``pixi.toml``'s max declared ``bmad-method`` floor against
    ``_bmad/_config/manifest.yaml``'s installed version (CAP-1) and,
    separately, that same installed version against the latest release
    actually published upstream (CAP-2). On the success path, ``_gather``
    always returns CAP-1's own Finding (``warn`` on drift, ``ok`` on
    agreement), plus a second CAP-2 Finding whenever
    ``_fetch_latest_upstream_version`` succeeds (``warn`` when installed is
    older than the fetched latest, ``ok`` otherwise) -- CAP-2 degrading to
    a failed fetch never changes CAP-1's own outcome, and adds nothing at
    all when it fails. The outer ``degrade_on_exception`` wrapper is what
    guarantees exactly one Finding OVERALL when something genuinely
    unexpected happens on the success path, by converting any such
    exception into one WARN instead.

    Read-only: never runs ``npx bmad-method install``, never writes to
    ``_bmad/**`` (Boundaries).
    """
    return degrade_on_exception(
        Source.BMAD_METHOD_VERSION_DRIFT, "bmad-method-version-drift",
        lambda: _gather(target),
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    pixi_data = tomllib.loads((target / "pixi.toml").read_text(encoding="utf-8"))
    declared = max(_declared_floors(pixi_data))

    manifest_path = target / "_bmad" / "_config" / "manifest.yaml"
    manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    installed = _parse_version(str(manifest_data["installation"]["version"]))

    declared_text = ".".join(str(part) for part in declared)
    installed_text = ".".join(str(part) for part in installed)
    evidence = {
        "installed": installed_text,
        "declared_floor": f">={declared_text}",
    }

    if installed < declared:
        drift_finding = Finding(
            source=Source.BMAD_METHOD_VERSION_DRIFT,
            check="bmad-method-version-drift",
            status=DoctorStatus.WARN,
            message=(
                f"installed bmad-method {installed_text} is behind "
                f"pixi.toml's declared floor >={declared_text}"
            ),
            evidence=evidence,
        )
    else:
        drift_finding = Finding(
            source=Source.BMAD_METHOD_VERSION_DRIFT,
            check="bmad-method-version-drift",
            status=DoctorStatus.OK,
            message=(
                f"installed bmad-method {installed_text} meets pixi.toml's "
                f"declared floor >={declared_text}"
            ),
            evidence=evidence,
        )

    latest_upstream = _fetch_latest_upstream_version()
    if latest_upstream is None:
        return (drift_finding,)

    latest_text = ".".join(str(part) for part in latest_upstream)
    upstream_evidence = {"installed": installed_text, "latest_upstream": latest_text}

    if installed < latest_upstream:
        upstream_finding = Finding(
            source=Source.BMAD_METHOD_VERSION_DRIFT,
            check="bmad-method-upstream-drift",
            status=DoctorStatus.WARN,
            message=(
                f"installed bmad-method {installed_text} is behind the "
                f"latest upstream release {latest_text}"
            ),
            evidence=upstream_evidence,
        )
    else:
        upstream_finding = Finding(
            source=Source.BMAD_METHOD_VERSION_DRIFT,
            check="bmad-method-upstream-drift",
            status=DoctorStatus.OK,
            message=(
                f"installed bmad-method {installed_text} meets the "
                f"latest upstream release {latest_text}"
            ),
            evidence=upstream_evidence,
        )

    return (drift_finding, upstream_finding)
