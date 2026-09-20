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

**CAP-4 (Story 14.1, Epic 14): the suite pass.** Epic 10 watched only the
CORE; the suite tools around it stayed invisible -- in the live 2026-08-21
upgrade session ``bmad-loop`` sat at 0.9.0 vs upstream 0.11.0 (0.9.0 stalls
every unattended session on BMAD >= 6.11) and TEA lagged 1.19.1 vs 1.23.2
(1.19.1's ``tea-test-review`` bin was published empty), with no ambient
signal. ``_gather`` therefore also runs a suite pass: the watched set is
DERIVED from ``pixi.toml``'s own ``bmad-*`` dependency keys (never a
hardcoded list -- a declared list omits exactly the newest tool), each
package's installed version is read from ``.pixi/envs/*/conda-meta/``
FILENAMES, and each is compared against its latest npm release through the
SAME generalized fail-open fetch helper CAP-2 already holds, emitting one
warn-only ``check="bmad-suite-upstream-drift"`` Finding per package behind
upstream. UNLIKE CAP-1/CAP-2's raise-then-``degrade_on_exception`` style,
the suite pass is ENTIRELY fail-open and never raises: CAP-1/2 read TRACKED
contract files where absence is a reportable misconfiguration, while the
suite pass reads gitignored runtime state that is legitimately absent on a
fresh clone/CI, and its per-package fetches degrade individually -- no
``.pixi``, no matching pins, unparseable versions, or all fetches failing
means no suite Finding at all, with CAP-1/CAP-2's own outcomes untouched.

**Story 15.1 (Epic 15, DW-14-1-1): unblinding the GitHub-only suite
packages.** CAP-4's npm-only fetch left 6 of the 10 watched pins invisible
-- including ``bmad-loop`` itself, the package whose 0.9.0-vs-0.11.0 lag
originally motivated CAP-4 -- because they publish via GitHub Releases/tags
and never to npm at all. When ``_fetch_latest_upstream_version`` returns
``None`` for a suite package, ``_gather_suite_findings`` now falls back to
``_fetch_latest_github_release``, using the per-package ``owner/repo``
recorded in that package's own TRACKED ``recipes/<package>/recipe.yaml``
(``extra.cfe-upstream-registry: github`` + ``extra.cfe-upstream-name``) --
never a hardcoded name->repo table, mirroring ``_suite_packages``'s own
derive-don't-declare discipline. The fallback is exactly as fail-open as
the npm path it extends and shares the SAME per-package/overall budget: a
missing recipe.yaml mapping, a non-github registry, or any GitHub HTTP/
network/JSON failure all fold to ``None`` and the package stays unchecked,
exactly as before this story.

**Story 19.1 (Epic 19, steward ``spec-bmad-suite-metapackage`` CAP-1):
manifest-driven watched set + registry-aware upstream.** The suite pass's
watched set is now the UNION of steward's tracked
``recipes/bmad-suite/suite-members.yaml`` (active members with a local
``recipes/<name>/recipe.yaml``, including ``mybmad-dashboard``) and every
``bmad-*`` pin ``_dependency_tables`` already walks -- deduped, sorted --
falling back to pixi-only when the manifest is absent (fail-open). Upstream
resolution is no longer npm-first: ``_resolve_upstream_latest`` reads each
member's ``extra.cfe-upstream-registry`` and queries the authoritative
registry (``github`` -> GitHub only, ``npm`` -> npm only, ``pypi`` -> PyPI
only); when the registry is absent/unknown, every applicable source is tried
and ``max()`` of the successfully parsed release triples wins -- never a
stale npm stub alone for GitHub-canonical packages (builder/CIS/dashboard).
CORE CAP-1/CAP-2's own npm comparison path is unchanged; Story 15.2's
channel/recipe checks reuse ``_resolve_upstream_latest`` instead of CAP-2's
npm fetch alone. The suite loop's shared budget bumps to ``15.0`` s
(Story 14.1/15.2/19.1 precedent); ``fleet_picture.py``'s subprocess bound
bumps to ``30`` s accordingly.

**Story 15.2 (Epic 15, spec-15-2, relaying ``spec-bmad-suite-channel-
product`` CAP-5): channel and recipe staleness become ambient findings.**
CAP-1/CAP-2/CAP-4/Story 15.1 all compare the INSTALLED tool against
upstream -- none of them ever checks whether the SelfExplainML anaconda.org
channel this repo actually publishes to serves what
``recipes/<name>/recipe.yaml`` declares, or whether that recipe itself has
caught up to upstream. The channel served a stale ``bmad-method 6.3.0`` for
four months with no ambient signal. Two new fail-open, warn-only checks
ride the SAME Source for every package this module already watches (CORE
plus every ``_suite_packages``-derived pin): ``bmad-channel-drift`` (the
anaconda.org channel's ``latest_version`` is behind the recipe's own
``context.version``) and ``bmad-recipe-upstream-drift`` (that recipe
version is behind the ALREADY-RESOLVED upstream latest at that call site --
never a new/third independent upstream fetch). Both are entirely fail-open
per package, mirroring the suite pass's own discipline: a missing/
unparseable ``recipe.yaml`` skips both; a channel-fetch failure skips only
``bmad-channel-drift``. The suite loop's per-package channel fetch draws
from the SAME shared ``_SUITE_FETCH_TOTAL_BUDGET_SECONDS`` pool the
pre-existing npm/GitHub upstream check already uses -- that pool was
doubled (``5.0`` -> ``10.0``, review pass 1 bad_spec repair) so a third
per-package fetch type does not starve the pre-existing check's own
coverage.

**Story 20.1 (Epic 20): the suite pass learns each package's own probe
class.** ``_resolve_upstream_latest`` compares every suite package via
releases/tags or npm -- but 7 of the roster's 13 ``suite-members.yaml``
entries (``bmad-eval-quality``, ``bmad-utility-skills``,
``bmad-labs-skills``, ``bmad-module-template``, ``bmad-manticore``,
``bmad-dashboard``, ``mybmad-dashboard``) are pinned to a raw commit on
their default branch, not a version tag -- querying releases/tags for them
either 404s or returns a stale/irrelevant tag. Each watched package's own
already-tracked ``extra.cfe-source-kind`` (``recipes/<name>/recipe.yaml``)
now picks its probe: ``github-tag``/``npm-registry`` (unchanged --
``_resolve_upstream_latest``) or ``github-commit`` (NEW -- compare the
recipe's own ``context.commit`` against the GitHub repo's default-branch
HEAD sha via ``_fetch_default_branch_head_sha``). Every per-package
``bmad-suite-upstream-drift`` WARN now names its probe class in
``evidence["probe_class"]`` (one of ``"tag"``/``"npm"``/``"commit-pinned"``
today; the aggregate OK Finding's evidence is unchanged). The commit-pinned
branch is exactly as fail-open as every other probe in this module: a
missing ``context.commit``, a missing/non-github owner-repo mapping, or any
GitHub fetch failure leaves that package unchecked, and it draws its fetch
timeout from the SAME shared per-package budget every other suite fetch
already uses. ``bmad-method`` (the core) stays excluded from this loop --
CAP-1/CAP-2 already own its own separate Finding.
"""

from __future__ import annotations

import http.client
import json
import re
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

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
            raise ValueError(f"unrecognized {DEPENDENCY_NAME!r} constraint form: {constraint!r}")
        floors.append(_parse_version(match.group(1)))

    if not floors:
        raise ValueError(f"{DEPENDENCY_NAME!r} is not declared in any dependencies table")
    return floors


#: npm's own public, unauthenticated per-package ``/latest`` endpoint --
#: returns a JSON body shaped ``{"name": "<package>", "version": "X.Y.Z",
#: ...}`` on success. Mirrors ``pyforge-mason``'s ``pypi_index.py``'s own
#: ``_PYPI_JSON_INDEX_URL_TEMPLATE`` precedent for a bare unauthenticated
#: JSON-index GET, aimed at npm's registry instead of PyPI's -- the whole
#: bmad suite ships on npm, not PyPI. A ``{package}`` template since Story
#: 14.1 (CAP-4's suite pass queries the same endpoint per suite package);
#: before that it hardcoded ``bmad-method``.
_NPM_LATEST_URL = "https://registry.npmjs.org/{package}/latest"

#: Deliberately shorter than ``pypi_index.py``'s own 30s: that precedent is
#: for ``ship_pypi``'s one-shot, human-triggered publish flow, while this
#: source runs ambiently and repeatedly (every opt-in ``doctor check
#: --bmad-core`` invocation, and every ``fleet_picture.py`` ATTENTION-block
#: probe -- Story 10.3 wired both) -- a short timeout keeps a
#: slow/unreachable registry from stalling an otherwise-fast local check for
#: long. Both numbers are metadata-GET-tier per the fleet's own convention
#: (``engines.gh._GH_PR_LIST_TIMEOUT_SECONDS``); this value is this story's
#: own judgment call for the ambient-check tier, not drawn from an existing
#: constant.
_UPSTREAM_FETCH_TIMEOUT_SECONDS = 5.0


def _fetch_latest_upstream_version(
    *, package: str = DEPENDENCY_NAME, timeout: float | None = None
) -> tuple[int, int, int] | None:
    """Query npm's own public registry for ``package``'s latest published
    release (Story 10.2, CAP-2; generalized to any package by Story 14.1 so
    CAP-4's suite pass shares this ONE fail-open network path) -- mirrors
    ``pypi_index.py``'s ``version_exists`` as the fleet's own precedent for
    a bare unauthenticated JSON-index GET. ``package`` is keyword-only and
    defaults to ``DEPENDENCY_NAME``, so every pre-CAP-4 caller and test
    stub (``lambda **_: None``) keeps working unmodified. Unlike that
    function's 404-vs-other split, every failure mode here folds to the
    SAME outcome: neither CAP-2 nor CAP-4 has a "conclusively does not
    exist" answer to give, only "succeeded" or "could not determine."

    Never raises: an ``HTTPError``, ``URLError``, a malformed/truncated HTTP
    response (``http.client.HTTPException`` -- NOT an ``OSError`` subclass,
    unlike ``RemoteDisconnected``, so it needs its own name in this tuple;
    review finding, Story 10.2), ``OSError``, ``TimeoutError``, a malformed
    JSON body, or a missing/unparseable ``"version"`` field all fold to
    ``None`` (Boundaries). The ``"version"`` string is parsed two ways
    (review finding, Story 14.1): for the CORE package, with the strict
    ``_parse_version`` exactly as CAP-1 parses ``manifest.yaml``'s own
    version -- CAP-1/CAP-2 keep one shared strict parsing path, and a
    malformed npm version string degrades the same way a malformed local
    one does (Design Notes); for SUITE packages, with the lenient
    ``_parse_release_triple``, symmetric with CAP-4's lenient installed
    side, so a prerelease ``latest`` (e.g. ``0.12.0-rc.1``) still yields a
    comparable release triple instead of silently vanishing from the pass.
    ``package`` is percent-encoded into the URL at this one seam."""
    resolved_timeout = timeout if timeout is not None else _UPSTREAM_FETCH_TIMEOUT_SECONDS
    url = _NPM_LATEST_URL.format(package=urllib.parse.quote(package, safe=""))
    try:
        with urllib.request.urlopen(url, timeout=resolved_timeout) as response:
            body = json.loads(response.read())
        version_text = str(body["version"])
        if package == DEPENDENCY_NAME:
            return _parse_version(version_text)
        return _parse_release_triple(version_text)
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


#: CAP-4's watched-set prefix (Story 14.1): every ``pixi.toml`` dependency
#: key starting with this -- EXCLUDING ``DEPENDENCY_NAME`` itself, which is
#: CAP-1/CAP-2's own territory (including it would duplicate
#: ``bmad-method-upstream-drift``) -- is a bmad-suite package the suite pass
#: compares against upstream. The set is DERIVED from the pins at gather
#: time, never declared as a hardcoded list: a hardcoded list omits exactly
#: the newest tool. Load-bearing assumption (review finding, Story 14.1):
#: a ``bmad-*`` pixi/conda dependency key IS the npm package name -- true
#: for every npm-published suite tool today, but a pin packaged from a
#: GitHub-only source (no npm release at all) resolves to a 404 on this
#: helper. Story 15.1 (DW-14-1-1) adds a GitHub releases/tags fallback for
#: exactly that case (see ``_fetch_latest_github_release``), so such a
#: package is no longer necessarily invisible -- it stays unchecked only
#: when its own ``recipes/<name>/recipe.yaml`` carries no github mapping,
#: or GitHub itself has neither a Release nor a tag to offer (live
#: 2026-08-21: 6 of the 10 watched pins, bmad-loop included, were
#: npm-invisible; see Design Notes for which of those 6 the GitHub
#: fallback does and does not reach).
_SUITE_PREFIX = "bmad-"

#: Shared budget for CAP-4's per-package fetch loop: one monotonic deadline
#: bounds which fetches START (per-fetch timeout = min(remaining,
#: ``_UPSTREAM_FETCH_TIMEOUT_SECONDS``); once exhausted, the remaining
#: packages are skipped). ``urlopen``'s timeout is an idle
#: (per-socket-operation) timeout, not total wall time, so a pathological
#: slow-drip response can exceed the per-fetch bound -- the same semantics
#: CAP-2's own single fetch already carries. Story 15.2 (review pass 1,
#: bad_spec repair) bumped this from ``5.0`` to ``10.0``: the suite loop's
#: per-package channel fetch (``_channel_and_recipe_drift_findings``) draws
#: from this SAME pool via the SAME unchanged per-call formula above, and an
#: early package's slow channel fetch could otherwise exhaust the
#: still-5.0s-sized pool before later packages get even their PRE-EXISTING
#: (Story 14.1) npm/GitHub upstream check -- doubling the pool gives
#: meaningfully more headroom without touching how any individual fetch is
#: bounded. CAP-2's 5s (core npm) + this 15s (suite loop) + the CORE-side
#: channel fetch's own 5s = 25s is now the DESIGN budget for ``_gather``'s
#: worst-case network cost, not a hard wall-clock guarantee;
#: ``scripts/fleet_picture.py``'s ``bmad_core_drift_findings`` 30s
#: subprocess bound carries the margin (Story 14.1/15.2/19.1).
_SUITE_FETCH_TOTAL_BUDGET_SECONDS = 15.0

#: Steward's canonical suite population (Story 19.1) -- same artifact the
#: ``bmad-suite`` metapackage recipe and pipeline-truth consume.
_SUITE_MANIFEST_REL = Path("recipes/bmad-suite/suite-members.yaml")

#: PyPI's own public, unauthenticated per-package JSON endpoint -- mirrors
#: ``_NPM_LATEST_URL``'s precedent for a bare unauthenticated metadata GET.
_PYPI_JSON_URL = "https://pypi.org/pypi/{package}/json"


def _parse_release_triple(text: str) -> tuple[int, int, int] | None:
    """Lenient counterpart to ``_parse_version`` for CAP-4's suite pass
    (Story 14.1): extract a LEADING ``X.Y.Z`` release triple, tolerating
    ``.dev0``/prerelease/extra-segment suffixes -- suite pins like
    ``1.2.2.dev0`` are legitimate conda versions that ``_parse_version``'s
    strict exactly-three-plain-digit-segments form rejects. An optional
    conda epoch prefix (``1!0.9.0``) is tolerated and ignored for the
    triple (review finding: rejecting it would permanently exempt an
    epoch-versioned package). Returns ``None`` instead of raising: the
    suite pass is entirely fail-open, so an unparseable version silently
    skips that one package rather than degrading the whole gather.
    Comparison downstream is release-triple only -- equal triples
    (installed ``1.2.2.dev0`` vs upstream ``1.2.2``) count as current,
    biasing this warn-only signal against false warns. CAP-1/CAP-2 keep
    their strict ``_parse_version`` path unchanged."""
    match = re.match(r"(?:\d+!)?(\d+)\.(\d+)\.(\d+)", text.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _pixi_suite_package_names(pixi_data: dict) -> set[str]:
    """Every ``bmad-*`` dependency key across ``_dependency_tables``, excluding
    the core ``DEPENDENCY_NAME`` itself (Story 14.1)."""
    names: set[str] = set()
    for table in _dependency_tables(pixi_data):
        for name in table:
            if name.startswith(_SUITE_PREFIX) and name != DEPENDENCY_NAME:
                names.add(name)
    return names


def _manifest_suite_members(target: Path) -> tuple[str, ...]:
    """Active ``suite-members.yaml`` entries that have a local recipe (Story
    19.1). Deprecated manifest rows and members without
    ``recipes/<name>/recipe.yaml`` are skipped silently; the core itself is
    excluded (CAP-1/CAP-2 territory). Returns ``()`` when the manifest is
    absent or unreadable -- the caller falls back to pixi-only."""
    path = target / _SUITE_MANIFEST_REL
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError, yaml.YAMLError:
        return ()
    members = data.get("members") if isinstance(data, dict) else None
    if not isinstance(members, list):
        return ()
    names: set[str] = set()
    for entry in members:
        if not isinstance(entry, dict) or entry.get("deprecated"):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name or name == DEPENDENCY_NAME:
            continue
        if (target / "recipes" / name / "recipe.yaml").is_file():
            names.add(name)
    return tuple(sorted(names))


def _suite_packages(pixi_data: dict, target: Path | None = None) -> tuple[str, ...]:
    """CAP-4/Story 19.1 watched set: UNION of manifest members (when the
    tracked manifest is present) and every pixi ``bmad-*`` pin
    ``_pixi_suite_package_names`` derives, deduped and sorted. When
    ``target`` is ``None`` or the manifest is absent, pixi-only (today's
    pre-19.1 behavior for isolated unit tests)."""
    pixi_names = _pixi_suite_package_names(pixi_data)
    if target is None:
        return tuple(sorted(pixi_names))
    manifest_names = _manifest_suite_members(target)
    if manifest_names:
        return tuple(sorted(pixi_names | set(manifest_names)))
    return tuple(sorted(pixi_names))


#: The three ``extra.cfe-source-kind`` values ``_source_kind`` can read from a
#: package's own recipe.yaml (Story 20.1) -- names the registry class each
#: real roster member uses today, mirroring ``_upstream_registry``'s own
#: string-constant precedent (``"npm"``/``"github"``/``"pypi"``).
_SOURCE_KIND_GITHUB_TAG = "github-tag"
_SOURCE_KIND_GITHUB_COMMIT = "github-commit"
_SOURCE_KIND_NPM_REGISTRY = "npm-registry"

#: ``evidence["probe_class"]`` values ``_probe_class`` returns (Story 20.1).
#: A fourth value, ``"pypi"``, is reachable via the ``registry == "pypi"``
#: branch but has no dedicated constant -- no roster member uses it today
#: (Boundaries).
_PROBE_CLASS_TAG = "tag"
_PROBE_CLASS_COMMIT_PINNED = "commit-pinned"
_PROBE_CLASS_NPM = "npm"


def _upstream_registry(target: Path, package: str) -> str | None:
    """``extra.cfe-upstream-registry`` from ``recipes/<package>/recipe.yaml``,
    lowercased, or ``None`` when absent/unreadable (Story 19.1)."""
    try:
        recipe_path = target / "recipes" / package / "recipe.yaml"
        data = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
        extra = data["extra"]
        reg = extra.get("cfe-upstream-registry")
        if isinstance(reg, str) and reg.strip():
            return reg.strip().lower()
    except OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError:
        pass
    return None


def _source_kind(target: Path, package: str) -> str | None:
    """``extra.cfe-source-kind`` from ``recipes/<package>/recipe.yaml``,
    lowercased, or ``None`` when absent/unreadable (Story 20.1) -- mirrors
    ``_upstream_registry``'s exact try/except shape and recipe-read
    pattern. Gives ``_gather_suite_findings`` a single, already-tracked
    signal for which probe a package uses -- never a hardcoded
    per-package table."""
    try:
        recipe_path = target / "recipes" / package / "recipe.yaml"
        data = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
        extra = data["extra"]
        kind = extra.get("cfe-source-kind")
        if isinstance(kind, str) and kind.strip():
            return kind.strip().lower()
    except OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError:
        pass
    return None


def _probe_class(source_kind: str | None, registry: str | None) -> str:
    """Which upstream probe ``_gather_suite_findings`` uses for a package
    (Story 20.1): ``github-commit`` -> ``"commit-pinned"``; ``registry ==
    "npm"`` or ``source_kind == "npm-registry"`` -> ``"npm"``; ``registry ==
    "pypi"`` -> ``"pypi"``; else -> ``"tag"``.

    The commit-pinned check runs FIRST so a package with both fields set is
    never mislabeled ``"npm"`` (Boundaries: no real roster member hits this
    today, but the ordering is load-bearing). A package with no recognized
    ``cfe-source-kind`` defaults to ``"tag"`` when its registry is not
    ``"npm"`` -- preserving today's only pre-existing github behavior for
    any fixture that predates ``cfe-source-kind``."""
    if source_kind == _SOURCE_KIND_GITHUB_COMMIT:
        return _PROBE_CLASS_COMMIT_PINNED
    if registry == "npm" or source_kind == _SOURCE_KIND_NPM_REGISTRY:
        return _PROBE_CLASS_NPM
    if registry == "pypi":
        return "pypi"
    return _PROBE_CLASS_TAG


def _recipe_pinned_commit(target: Path, package: str) -> tuple[str, str] | None:
    """``(raw context.version text, raw context.commit text)`` from
    ``recipes/<package>/recipe.yaml`` (Story 20.1) -- ``None`` on any
    missing/malformed input. Deliberately reads ``context.version`` as a
    raw string, NEVER through ``_parse_release_triple``/``_recipe_version``
    -- that parser drops the ``.dev0`` suffix the ``"X.Y.Z.dev0 @ sha"``
    encoding requires (Design Notes).

    Mirrors ``_recipe_version``'s own fail-open try/except shape: a
    missing/unreadable ``recipe.yaml`` (``OSError``), an unrepresentable
    path (``ValueError``), malformed YAML (``yaml.YAMLError``), a
    non-mapping document, or a missing/non-mapping ``context``/``version``/
    ``commit`` (``KeyError``/``TypeError``/``AttributeError``) all fold to
    ``None``. A present-but-``null`` ``version``/``commit`` key (YAML
    ``key:`` with no value) does NOT raise ``KeyError`` -- without an
    explicit non-empty-string check, ``str(None)`` would silently become
    the literal text ``"None"`` instead of fail-opening (review finding),
    so both fields are validated with the same ``isinstance(x, str) and
    x.strip()`` guard ``_upstream_registry``/``_source_kind`` already use."""
    try:
        recipe_path = target / "recipes" / package / "recipe.yaml"
        data = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
        context = data["context"]
        version_value = context["version"]
        commit_value = context["commit"]
        if not (isinstance(version_value, str) and version_value.strip()):
            return None
        if not (isinstance(commit_value, str) and commit_value.strip()):
            return None
        return version_value, commit_value
    except OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError:
        return None


def _upstream_package_name(target: Path, package: str) -> str:
    """``extra.cfe-upstream-name`` when present, else ``package`` itself
    (Story 19.1 -- mirrors steward generator discipline)."""
    try:
        recipe_path = target / "recipes" / package / "recipe.yaml"
        data = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
        extra = data["extra"]
        name = extra.get("cfe-upstream-name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    except OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError:
        pass
    return package


def _fetch_pypi_latest_version(*, package: str, timeout: float | None = None) -> tuple[int, int, int] | None:
    """Query PyPI's public JSON API for ``package``'s latest release (Story
    19.1). Lenient-parsed with ``_parse_release_triple``; never raises."""
    resolved_timeout = timeout if timeout is not None else _UPSTREAM_FETCH_TIMEOUT_SECONDS
    url = _PYPI_JSON_URL.format(package=urllib.parse.quote(package, safe=""))
    try:
        with urllib.request.urlopen(url, timeout=resolved_timeout) as response:
            body = json.loads(response.read())
        return _parse_release_triple(str(body["info"]["version"]))
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


def _resolve_upstream_latest(
    package: str,
    target: Path,
    *,
    timeout: float | None = None,
) -> tuple[int, int, int] | None:
    """Registry-aware upstream latest for ``package`` (Story 19.1). Reads
    ``recipes/<package>/recipe.yaml``'s ``cfe-upstream-registry`` and queries
    ONLY the authoritative registry when declared; when absent/unknown, tries
    npm, GitHub (when mapped), and PyPI and returns ``max()`` of every
    successfully parsed release triple. Never raises."""
    resolved_timeout = timeout if timeout is not None else _UPSTREAM_FETCH_TIMEOUT_SECONDS
    registry = _upstream_registry(target, package)
    upstream_name = _upstream_package_name(target, package)

    if registry == "github":
        owner_repo = _github_owner_repo(target, package)
        if owner_repo is None:
            return None
        return _fetch_latest_github_release(owner_repo=owner_repo, timeout=resolved_timeout)

    if registry == "npm":
        return _fetch_latest_upstream_version(package=upstream_name, timeout=resolved_timeout)

    if registry == "pypi":
        return _fetch_pypi_latest_version(package=upstream_name, timeout=resolved_timeout)

    candidates: list[tuple[int, int, int]] = []
    npm_latest = _fetch_latest_upstream_version(package=package, timeout=resolved_timeout)
    if npm_latest is not None:
        candidates.append(npm_latest)
    owner_repo = _github_owner_repo(target, package)
    if owner_repo is not None:
        github_latest = _fetch_latest_github_release(owner_repo=owner_repo, timeout=resolved_timeout)
        if github_latest is not None:
            candidates.append(github_latest)
    pypi_latest = _fetch_pypi_latest_version(package=upstream_name, timeout=resolved_timeout)
    if pypi_latest is not None:
        candidates.append(pypi_latest)
    return max(candidates) if candidates else None


def _installed_suite_versions(target: Path, packages: tuple[str, ...]) -> dict[str, tuple[tuple[int, int, int], str]]:
    """Each watched package's installed version -- ``{name: (release_triple,
    raw_version_text)}`` -- read from ``.pixi/envs/*/conda-meta/
    {name}-<version>-<build>.json`` FILENAMES, zero file reads: conda
    versions and build strings cannot contain ``-`` (names can), so
    ``rsplit("-", 2)`` on the stem is an exact parse for a known name.
    Newest release triple across every env wins: the signal asks "has this
    repo caught up anywhere" -- a partially-synced env set is ``pixi
    install`` hygiene, not upstream drift, and per-env findings would
    multiply noise in a warn-only channel (Design Notes, Story 14.1).

    Fail-open throughout: no ``.pixi/envs`` at all, an unreadable
    directory, or an unparseable version each silently contributes
    nothing -- this is gitignored runtime state, legitimately absent on a
    fresh clone/CI (unlike CAP-1/2's tracked contract files, where absence
    is a reportable misconfiguration)."""
    watched = set(packages)
    installed: dict[str, tuple[tuple[int, int, int], str]] = {}
    envs_dir = target / ".pixi" / "envs"
    try:
        env_dirs = list(envs_dir.iterdir())
    except OSError:
        return installed
    for env_dir in env_dirs:
        try:
            meta_files = list((env_dir / "conda-meta").iterdir())
        except OSError:
            continue
        for meta_file in meta_files:
            if meta_file.suffix != ".json":
                continue
            parts = meta_file.stem.rsplit("-", 2)
            if len(parts) != 3:
                continue
            name, version_text, _build = parts
            if name not in watched:
                continue
            triple = _parse_release_triple(version_text)
            if triple is None:
                continue
            candidate = (triple, version_text)
            if name not in installed or candidate > installed[name]:
                installed[name] = candidate
    return installed


#: GitHub's own public, unauthenticated per-repo endpoints (Story 15.1,
#: DW-14-1-1). ``releases/latest`` returns the most recently published
#: Release (a 404 body when the repo has never published one at all);
#: ``tags`` returns every git tag regardless of whether a Release was ever
#: attached to it -- the fallback for a repo that tags without ever using
#: GitHub's "Releases" feature. Both are bare unauthenticated GETs,
#: mirroring ``_NPM_LATEST_URL``'s own precedent (Boundaries: no token, no
#: ``gh`` CLI, no subprocess -- this module's independence rule).
_GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/{owner_repo}/releases/latest"
_GITHUB_TAGS_URL = "https://api.github.com/repos/{owner_repo}/tags"

#: GitHub's own public, unauthenticated commits endpoint (Story 20.1) -- with
#: no ``sha``/``path`` query params it returns commits reachable from the
#: repository's DEFAULT branch, newest first, so ``?per_page=1`` gets the
#: HEAD commit in one GET with no separate default-branch-name lookup
#: (Design Notes).
_GITHUB_COMMITS_URL = "https://api.github.com/repos/{owner_repo}/commits?per_page=1"


def _strip_leading_v(text: str) -> str:
    """Strip exactly one optional leading ``v``/``V`` (GitHub's own de
    facto tag convention, e.g. ``v1.2.3``) before handing a tag/release
    name to ``_parse_release_triple`` -- that parser itself treats a
    leading ``v`` as garbage (an existing test asserts ``"v1.2.3"`` is
    unparseable to it), so the strip happens here, once, at the one
    GitHub-specific seam, leaving ``_parse_release_triple`` itself
    unmodified (Boundaries, Story 15.1)."""
    if text[:1] in ("v", "V"):
        return text[1:]
    return text


def _github_owner_repo(target: Path, package: str) -> str | None:
    """The ``owner/repo`` slug the GitHub fallback should query for
    ``package``, derived from that package's own TRACKED
    ``recipes/<package>/recipe.yaml`` -- never a hardcoded name->repo
    table (Design Notes, Story 15.1: a hardcoded list omits exactly the
    newest GitHub-only tool, the same derive-don't-declare discipline
    ``_suite_packages`` already applies to the watched set itself).
    Returns ``extra.cfe-upstream-name`` when that recipe's
    ``extra.cfe-upstream-registry`` is exactly ``"github"``, else
    ``None``.

    Entirely fail-open, never raises: a missing or unreadable
    ``recipe.yaml`` (``OSError``), an unrepresentable path such as an
    embedded NUL byte (``ValueError`` -- review finding: a package name
    from a corrupt/adversarial ``pixi.toml`` must not raise past this
    function's own documented contract, even though a real ``pixi.toml``
    dependency key cannot produce one today), malformed YAML
    (``yaml.YAMLError``), a non-mapping document or a missing/non-mapping
    ``extra``/``cfe-upstream-name`` (``KeyError``/``TypeError``/
    ``AttributeError``), or a non-github registry all fold to ``None`` --
    the caller (``_gather_suite_findings``) treats that identically to
    "GitHub fallback not attempted" (Boundaries)."""
    try:
        recipe_path = target / "recipes" / package / "recipe.yaml"
        data = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
        extra = data["extra"]
        if str(extra.get("cfe-upstream-registry")) != "github":
            return None
        owner_repo = extra.get("cfe-upstream-name")
        if not isinstance(owner_repo, str) or not owner_repo:
            return None
        return owner_repo
    except OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError:
        return None


#: Every exception ``_fetch_latest_github_release`` folds to ``None``
#: EXCEPT a ``releases/latest`` ``HTTPError``, which needs its status code
#: inspected first (Boundaries: only a 404 falls back to ``/tags``, any
#: other failure returns ``None`` immediately). ``urllib.error.HTTPError``
#: is itself a ``URLError`` subclass, so it is already covered here for
#: the ``/tags`` fetch below, which has no such special case.
_GITHUB_FETCH_FAIL_TYPES = (
    urllib.error.URLError,
    http.client.HTTPException,
    OSError,
    TimeoutError,
    ValueError,
    KeyError,
    TypeError,
)


def _fetch_latest_github_release(*, owner_repo: str, timeout: float | None = None) -> tuple[int, int, int] | None:
    """Query GitHub's public REST API for ``owner_repo``'s latest release
    (Story 15.1, DW-14-1-1) -- the CAP-4 suite pass's fallback for a
    package whose npm fetch already returned ``None``. Mirrors
    ``_fetch_latest_upstream_version``'s fail-open shape.

    Tries ``GET .../releases/latest`` first. Only on a 404 SPECIFICALLY
    (no Release has ever been published -- a definitive, distinguishable
    state) does it fall back to ``GET .../tags`` and take the newest
    successfully-parsed tag (``max()`` by release triple over every
    parseable entry -- the same "biased against false warns" semantics
    ``_parse_release_triple`` already documents). Any OTHER failure -- a
    non-404 HTTPError, a network/timeout error, a malformed JSON body, or
    a missing/unparseable tag/release name -- returns ``None`` immediately
    WITHOUT trying ``/tags`` (Boundaries).

    Both endpoints' tag/release names are stripped of one optional
    leading ``v``/``V`` (``_strip_leading_v``) before parsing with the
    existing lenient ``_parse_release_triple`` -- that parser itself is
    NOT modified. Never raises: every failure mode folds to ``None``,
    exactly like ``_fetch_latest_upstream_version``.

    ``timeout`` bounds this function's TOTAL wall time, not each call
    individually (review finding: the caller computes ``timeout`` from
    its own shared per-package budget, so a 404-then-``/tags`` fallback
    that reused the full ``timeout`` for BOTH sequential calls could
    double one package's worst-case duration against that budget). A
    shared internal deadline is re-checked before the ``/tags`` call;
    once it is exhausted, ``/tags`` is not attempted at all."""
    resolved_timeout = timeout if timeout is not None else _UPSTREAM_FETCH_TIMEOUT_SECONDS
    deadline = time.monotonic() + resolved_timeout
    release_url = _GITHUB_LATEST_RELEASE_URL.format(owner_repo=owner_repo)
    try:
        with urllib.request.urlopen(release_url, timeout=resolved_timeout) as response:
            body = json.loads(response.read())
        return _parse_release_triple(_strip_leading_v(str(body["tag_name"])))
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            return None
    except _GITHUB_FETCH_FAIL_TYPES:
        return None

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    tags_url = _GITHUB_TAGS_URL.format(owner_repo=owner_repo)
    try:
        with urllib.request.urlopen(tags_url, timeout=remaining) as response:
            entries = json.loads(response.read())
        parsed: list[tuple[int, int, int]] = []
        for entry in entries:
            try:
                triple = _parse_release_triple(_strip_leading_v(str(entry["name"])))
            except KeyError, TypeError:
                # One malformed entry (missing "name", or not a mapping)
                # skips only itself -- review finding: this used to abort
                # the ENTIRE scan, discarding every otherwise-valid parsed
                # tag alongside it.
                continue
            if triple is not None:
                parsed.append(triple)
        return max(parsed) if parsed else None
    except _GITHUB_FETCH_FAIL_TYPES:
        return None


def _fetch_default_branch_head_sha(*, owner_repo: str, timeout: float | None = None) -> str | None:
    """One GET to ``_GITHUB_COMMITS_URL`` for ``owner_repo``'s default-branch
    HEAD commit sha (Story 20.1) -- the commit-pinned suite probe's
    counterpart to ``_fetch_latest_github_release``'s tag-based probe.
    Mirrors ``_fetch_latest_upstream_version``'s never-raises fail-open
    shape exactly.

    Never raises: an ``HTTPError``, ``URLError``, a malformed/truncated HTTP
    response (``http.client.HTTPException``), ``OSError``, ``TimeoutError``,
    a malformed JSON body, a non-list/empty response body
    (``IndexError`` -- a brand-new/emptied repo), or a missing/unrepresentable
    ``"sha"`` field (``KeyError``/``TypeError``) all fold to ``None``
    (Boundaries)."""
    resolved_timeout = timeout if timeout is not None else _UPSTREAM_FETCH_TIMEOUT_SECONDS
    url = _GITHUB_COMMITS_URL.format(owner_repo=owner_repo)
    try:
        with urllib.request.urlopen(url, timeout=resolved_timeout) as response:
            entries = json.loads(response.read())
        return str(entries[0]["sha"])
    except (
        urllib.error.URLError,
        http.client.HTTPException,
        OSError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
    ):
        return None


#: The anaconda.org channel this repo actually publishes the bmad suite to
#: (Story 15.2). A plain constant, not derived from ``pixi.toml``'s own
#: ``channels`` array -- that list mixes ``conda-forge`` in with it, and
#: picking "the non-standard one" programmatically would be speculative
#: complexity for a single fixed value (Design Notes), mirroring
#: ``DEPENDENCY_NAME``'s own precedent for a repo-specific, rarely-changing
#: identifier.
_ANACONDA_CHANNEL = "SelfExplainML"

#: anaconda.org's own public, unauthenticated per-package endpoint -- returns
#: a JSON body with a ``"latest_version"`` field on success. Mirrors
#: ``_NPM_LATEST_URL``'s own precedent for a bare unauthenticated JSON-index
#: GET, aimed at anaconda.org instead of npm (Story 15.2). Only ``package``
#: is percent-encoded into the URL (mirrors ``_fetch_latest_upstream_
#: version``'s own seam) -- ``_ANACONDA_CHANNEL`` is a hardcoded, known-safe
#: literal, not caller-supplied input.
_ANACONDA_PACKAGE_URL = "https://api.anaconda.org/package/{channel}/{package}"


def _recipe_version(target: Path, package: str) -> tuple[int, int, int] | None:
    """The version this repo's own TRACKED ``recipes/<package>/recipe.yaml``
    declares in its ``context.version`` field (Story 15.2) -- lenient-parsed
    with ``_parse_release_triple`` (never the strict ``_parse_version``),
    symmetric with the suite pass's own installed-side parsing and the six
    ``.dev0``-pinned suite recipes.

    Mirrors ``_github_owner_repo``'s own fail-open try/except shape and
    recipe-read pattern: a missing/unreadable ``recipe.yaml`` (``OSError``),
    an unrepresentable path (``ValueError``), malformed YAML
    (``yaml.YAMLError``), a non-mapping document, or a missing/non-mapping
    ``context``/``version`` (``KeyError``/``TypeError``/``AttributeError``)
    all fold to ``None`` -- the caller treats that identically to "cannot
    evaluate this package" (Boundaries: entirely fail-open per package)."""
    try:
        recipe_path = target / "recipes" / package / "recipe.yaml"
        data = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
        version_text = str(data["context"]["version"])
        return _parse_release_triple(version_text)
    except OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError:
        return None


def _fetch_channel_version(*, package: str, timeout: float | None = None) -> tuple[int, int, int] | None:
    """Query anaconda.org's own public registry for ``package``'s
    ``latest_version`` as served by the ``_ANACONDA_CHANNEL`` channel (Story
    15.2) -- mirrors ``_fetch_latest_upstream_version``'s fail-open GET
    shape exactly, aimed at anaconda.org instead of npm/GitHub. Always
    lenient-parsed with ``_parse_release_triple`` -- channel labels can
    carry the same prerelease/``.dev0`` shapes the suite's installed side
    already tolerates.

    Never raises: an ``HTTPError`` (including a 404 -- "package not on this
    channel" and "channel unreachable" both fold to the same "could not
    determine" outcome, mirroring ``_fetch_latest_upstream_version``'s own
    no-404-special-case precedent), ``URLError``, a malformed/truncated HTTP
    response, ``OSError``, ``TimeoutError``, a malformed JSON body, or a
    missing/unparseable ``"latest_version"`` field all fold to ``None``
    (Boundaries)."""
    resolved_timeout = timeout if timeout is not None else _UPSTREAM_FETCH_TIMEOUT_SECONDS
    url = _ANACONDA_PACKAGE_URL.format(
        channel=_ANACONDA_CHANNEL,
        package=urllib.parse.quote(package, safe=""),
    )
    try:
        with urllib.request.urlopen(url, timeout=resolved_timeout) as response:
            body = json.loads(response.read())
        return _parse_release_triple(str(body["latest_version"]))
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


def _channel_and_recipe_drift_findings(
    target: Path,
    package: str,
    upstream_latest: tuple[int, int, int],
    *,
    timeout: float | None = None,
) -> tuple[Finding, ...]:
    """Story 15.2's two new fail-open, warn-only checks for ``package``,
    given that package's own already-resolved ``upstream_latest`` (the
    caller's job to have confirmed this is not ``None`` before calling --
    neither new check is attempted otherwise, per the I/O matrix).

    ``bmad-channel-drift`` fires when the ``_ANACONDA_CHANNEL`` channel's
    own latest published version is behind the recipe's declared version
    (reproduces the 6.3.0 relic); ``bmad-recipe-upstream-drift`` fires when
    the recipe's declared version is behind ``upstream_latest`` itself.
    Neither ever fires an OK/summary counterpart (Boundaries: "warn-only
    findings" is the AC's own literal wording) -- agreement across all three
    just returns an empty tuple.

    Entirely fail-open per package, mirroring ``_gather_suite_findings``'s
    own discipline: a missing/unparseable ``recipes/<package>/recipe.yaml``
    (``_recipe_version`` returns ``None``) skips BOTH findings before any
    network call is attempted; a channel-fetch failure
    (``_fetch_channel_version`` returns ``None``) skips only
    ``bmad-channel-drift`` -- ``bmad-recipe-upstream-drift`` is evaluated
    from ``_recipe_version``'s own local read regardless.

    Never raises (transitively, via its two callees): ``_recipe_version``
    folds every local-read/parse failure to ``None``, and
    ``_fetch_channel_version`` folds every network/JSON failure to ``None``
    -- this function itself does no I/O of its own and never propagates
    anything past either seam, matching the "Never raises" contract every
    other network-touching helper in this file (``_fetch_latest_upstream_
    version``, ``_fetch_channel_version``, ``_fetch_latest_github_release``)
    already states explicitly."""
    recipe_version = _recipe_version(target, package)
    if recipe_version is None:
        return ()

    recipe_text = ".".join(str(part) for part in recipe_version)
    findings: list[Finding] = []

    channel_version = _fetch_channel_version(package=package, timeout=timeout)
    if channel_version is not None and channel_version < recipe_version:
        channel_text = ".".join(str(part) for part in channel_version)
        findings.append(
            Finding(
                source=Source.BMAD_METHOD_VERSION_DRIFT,
                check="bmad-channel-drift",
                status=DoctorStatus.WARN,
                message=(
                    # Kept short (review pass 2, patch): the full
                    # "the {channel} channel serves ... behind the
                    # recipe's declared version ..." wording overflowed
                    # fleet_picture.py's 110-char truncation for this
                    # repo's longest watched package name
                    # (bmad-method-test-architecture-enterprise, 125
                    # chars) -- this shorter wording stays under 110
                    # chars even for that name.
                    f"{_ANACONDA_CHANNEL} serves {package} {channel_text}, recipe declares {recipe_text}"
                ),
                evidence={
                    "package": package,
                    "channel_version": channel_text,
                    "recipe_version": recipe_text,
                },
            )
        )

    if recipe_version < upstream_latest:
        upstream_text = ".".join(str(part) for part in upstream_latest)
        findings.append(
            Finding(
                source=Source.BMAD_METHOD_VERSION_DRIFT,
                check="bmad-recipe-upstream-drift",
                status=DoctorStatus.WARN,
                message=(f"recipe {package} {recipe_text} is behind the latest upstream release {upstream_text}"),
                evidence={
                    "package": package,
                    "recipe_version": recipe_text,
                    "latest_upstream": upstream_text,
                },
            )
        )

    return tuple(findings)


def _gather_suite_findings(target: Path, pixi_data: dict) -> tuple[Finding, ...]:
    """CAP-4 (Story 14.1): compare every INSTALLED bmad-suite package
    against its latest npm release, through the same generalized
    ``_fetch_latest_upstream_version`` seam CAP-2 uses. One WARN Finding
    per package behind upstream (``check="bmad-suite-upstream-drift"``,
    mirroring CAP-2's shape and wording); when at least one package was
    successfully checked and none is behind, exactly one OK Finding (same
    check) naming the checked count; when zero were checked, no suite
    Finding at all.

    Story 15.1 (DW-14-1-1) extends the per-package comparison: whenever
    the npm fetch misses (``None``) for a package, a GitHub releases/tags
    fallback (``_fetch_latest_github_release``, keyed by that package's
    own ``recipes/<name>/recipe.yaml`` github mapping via
    ``_github_owner_repo``) is tried before giving up on it, still inside
    the SAME shared budget below -- ``checked`` increments identically
    regardless of which source ultimately resolved a package.

    Story 20.1 branches EACH package's own probe by its recipe's tracked
    ``extra.cfe-source-kind``: a ``github-commit`` package compares its
    recipe's ``context.commit`` against the GitHub repo's default-branch
    HEAD sha instead of going through ``_resolve_upstream_latest`` at all
    (still inside the SAME shared budget, still entirely fail-open); every
    other package falls through unchanged, now with its probe class
    (``"tag"``/``"npm"``/``"commit-pinned"``) recorded in its own WARN
    Finding's ``evidence["probe_class"]``.

    ENTIRELY fail-open, never raises -- deliberately unlike CAP-1/CAP-2's
    raise-then-``degrade_on_exception`` style. Rationale: CAP-1/2 read
    TRACKED contract files where absence is a reportable misconfiguration;
    this pass reads gitignored runtime state (``.pixi/envs/*/conda-meta/``)
    that is legitimately absent on a fresh clone/CI, and its per-package
    fetches degrade individually. Letting an exception escape here would
    hand the WHOLE gather to ``degrade_on_exception``, collapsing CAP-1/
    CAP-2's already-computed Findings into one generic WARN -- so the
    ``except Exception`` below is what makes "CAP-1/CAP-2 outcomes are
    untouched" a structural guarantee, not a hope."""
    try:
        packages = _suite_packages(pixi_data, target)
        if not packages:
            return ()
        installed = _installed_suite_versions(target, packages)
        if not installed:
            # No runtime state at all => no fetches issued (I/O matrix:
            # fresh clone/CI).
            return ()

        deadline = time.monotonic() + _SUITE_FETCH_TOTAL_BUDGET_SECONDS
        warn_findings: list[Finding] = []
        # Story 15.2 (review pass 2, patch): a SEPARATE list from
        # `warn_findings` -- the two new checks' own findings must ride
        # EVERY return branch below (WARN, OK, and empty), never gate which
        # branch fires. Appending them into `warn_findings` directly was a
        # bug: a package whose installed-vs-upstream axis is genuinely
        # clean but whose recipe/channel axis drifts would make
        # `warn_findings` non-empty from the new findings ALONE, taking the
        # `if warn_findings:` branch and silently dropping the
        # `bmad-suite-upstream-drift` OK/summary Finding that should still
        # fire for the clean packages.
        extra_findings: list[Finding] = []
        checked = 0
        for name in packages:
            versions = installed.get(name)
            if versions is None:
                continue  # pinned but not installed anywhere: nothing to compare
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break  # shared budget exhausted: skip the rest (fail-open)
            per_fetch_timeout = min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS)

            # Story 20.1: which probe this package uses, derived from its
            # own already-tracked extra.cfe-source-kind/cfe-upstream-registry
            # -- never a hardcoded per-package table.
            source_kind = _source_kind(target, name)

            if source_kind == _SOURCE_KIND_GITHUB_COMMIT:
                # Commit-pinned probe: compare the recipe's own tracked
                # context.commit against the GitHub repo's default-branch
                # HEAD sha -- entirely fail-open, exactly like every other
                # probe in this loop (Boundaries). `_probe_class` would
                # return "commit-pinned" from `source_kind` alone here, so
                # skip the (unused) `_upstream_registry` YAML read/parse
                # entirely (review finding).
                probe_class = _PROBE_CLASS_COMMIT_PINNED
                pinned = _recipe_pinned_commit(target, name)
                if pinned is None:
                    continue
                pinned_version_text, pinned_commit = pinned
                owner_repo = _github_owner_repo(target, name)
                if owner_repo is None:
                    continue
                head_sha = _fetch_default_branch_head_sha(owner_repo=owner_repo, timeout=per_fetch_timeout)
                if head_sha is None:
                    continue
                checked += 1
                # Case/whitespace-normalized comparison (review finding):
                # GitHub's API always returns lowercase hex, but a recipe's
                # own context.commit could be written in mixed/upper case --
                # comparing raw would produce a permanent spurious WARN for
                # an actually-current pin. The displayed sha (message +
                # evidence) uses the SAME normalized forms so what's shown
                # matches what was actually compared.
                normalized_pinned = pinned_commit.strip().lower()
                normalized_head = head_sha.strip().lower()
                if normalized_head != normalized_pinned:
                    warn_findings.append(
                        Finding(
                            source=Source.BMAD_METHOD_VERSION_DRIFT,
                            check="bmad-suite-upstream-drift",
                            status=DoctorStatus.WARN,
                            message=(
                                f"{name} {pinned_version_text} @ "
                                f"{normalized_pinned[:12]} is behind the "
                                f"default-branch HEAD {normalized_head[:12]}"
                            ),
                            evidence={
                                "package": name,
                                "probe_class": probe_class,
                                "installed": (f"{pinned_version_text} @ {normalized_pinned[:12]}"),
                                "latest_upstream": normalized_head[:12],
                            },
                        )
                    )
                continue

            probe_class = _probe_class(source_kind, _upstream_registry(target, name))
            latest = _resolve_upstream_latest(
                name,
                target,
                timeout=per_fetch_timeout,
            )
            if latest is None:
                continue  # per-package fail-open (404, outage, garbage body)
            checked += 1

            # Story 15.2: channel-vs-recipe and recipe-vs-upstream drift,
            # reusing this iteration's own already-resolved `latest` --
            # never a third independent upstream fetch. The channel fetch
            # stays inside the SAME shared deadline this loop already
            # enforces (Boundaries) -- skipped entirely once the budget is
            # exhausted, mirroring the GitHub-fallback guard above.
            remaining = deadline - time.monotonic()
            if remaining > 0:
                extra_findings.extend(
                    _channel_and_recipe_drift_findings(
                        target,
                        name,
                        latest,
                        timeout=min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS),
                    )
                )

            triple, installed_text = versions
            if triple < latest:
                latest_text = ".".join(str(part) for part in latest)
                warn_findings.append(
                    Finding(
                        source=Source.BMAD_METHOD_VERSION_DRIFT,
                        check="bmad-suite-upstream-drift",
                        status=DoctorStatus.WARN,
                        message=(
                            f"installed {name} {installed_text} is behind the latest upstream release {latest_text}"
                        ),
                        evidence={
                            "package": name,
                            "probe_class": probe_class,
                            "installed": installed_text,
                            "latest_upstream": latest_text,
                        },
                    )
                )

        if warn_findings:
            return (*warn_findings, *extra_findings)
        if checked:
            return (
                Finding(
                    source=Source.BMAD_METHOD_VERSION_DRIFT,
                    check="bmad-suite-upstream-drift",
                    status=DoctorStatus.OK,
                    message=(f"installed bmad-suite packages meet the latest upstream releases ({checked} checked)"),
                    # packages_watched (the full derived watched-set size)
                    # alongside packages_checked, so the evidence does not
                    # hide how much of the set was actually reachable
                    # (live: 4 checked of 10 watched, 6 npm-invisible --
                    # review finding). The WARN evidence shape above is
                    # spec-fixed and stays untouched.
                    evidence={
                        "packages_checked": checked,
                        "packages_watched": len(packages),
                    },
                ),
                *extra_findings,
            )
        return (*extra_findings,)
    except Exception:
        # The last-resort net documented above: any unexpected failure in
        # the suite pass folds to "adds nothing", never to a degraded
        # gather.
        return ()


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
    all when it fails. Story 14.1 (CAP-4) appends
    ``_gather_suite_findings``'s entirely-fail-open suite comparison to
    both success-path returns -- it runs regardless of CAP-2's own fetch
    outcome, and adds nothing at all when it degrades. Story 15.2 appends a
    third CORE-side addition, ``channel_recipe_findings``
    (``_channel_and_recipe_drift_findings``, gated on CAP-2's own
    ``latest_upstream`` being resolved), reusing that already-fetched
    upstream latest -- never a second CORE fetch. The outer
    ``degrade_on_exception`` wrapper is what guarantees exactly one Finding
    OVERALL when something genuinely unexpected happens on the success
    path, by converting any such exception into one WARN instead.

    Read-only: never runs ``npx bmad-method install``, never writes to
    ``_bmad/**`` (Boundaries).
    """
    return degrade_on_exception(
        Source.BMAD_METHOD_VERSION_DRIFT,
        "bmad-method-version-drift",
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
            message=(f"installed bmad-method {installed_text} is behind pixi.toml's declared floor >={declared_text}"),
            evidence=evidence,
        )
    else:
        drift_finding = Finding(
            source=Source.BMAD_METHOD_VERSION_DRIFT,
            check="bmad-method-version-drift",
            status=DoctorStatus.OK,
            message=(f"installed bmad-method {installed_text} meets pixi.toml's declared floor >={declared_text}"),
            evidence=evidence,
        )

    # CAP-4's suite pass (Story 14.1) runs regardless of CAP-2's own fetch
    # outcome below -- independent fail-open, appended to BOTH success-path
    # returns. Placed after CAP-1's parse so broken CAP-1 inputs (missing
    # pixi.toml/manifest.yaml) still degrade through the outer net before
    # the suite pass is ever reached, exactly as before CAP-4 existed.
    suite_findings = _gather_suite_findings(target, pixi_data)

    latest_upstream = _fetch_latest_upstream_version()
    registry_upstream = _resolve_upstream_latest(DEPENDENCY_NAME, target)
    if latest_upstream is None:
        channel_recipe_findings = ()
        if registry_upstream is not None:
            channel_recipe_findings = _channel_and_recipe_drift_findings(
                target,
                DEPENDENCY_NAME,
                registry_upstream,
            )
        return (drift_finding, *suite_findings, *channel_recipe_findings)

    # Story 15.2/19.1: channel-vs-recipe and recipe-vs-upstream drift for the
    # CORE package, using registry-aware upstream when available -- never a
    # second independent fetch beyond ``_resolve_upstream_latest`` itself.
    channel_recipe_findings = ()
    if registry_upstream is not None:
        channel_recipe_findings = _channel_and_recipe_drift_findings(
            target,
            DEPENDENCY_NAME,
            registry_upstream,
        )

    latest_text = ".".join(str(part) for part in latest_upstream)
    upstream_evidence = {"installed": installed_text, "latest_upstream": latest_text}

    if installed < latest_upstream:
        upstream_finding = Finding(
            source=Source.BMAD_METHOD_VERSION_DRIFT,
            check="bmad-method-upstream-drift",
            status=DoctorStatus.WARN,
            message=(f"installed bmad-method {installed_text} is behind the latest upstream release {latest_text}"),
            evidence=upstream_evidence,
        )
    else:
        upstream_finding = Finding(
            source=Source.BMAD_METHOD_VERSION_DRIFT,
            check="bmad-method-upstream-drift",
            status=DoctorStatus.OK,
            message=(f"installed bmad-method {installed_text} meets the latest upstream release {latest_text}"),
            evidence=upstream_evidence,
        )

    return (drift_finding, upstream_finding, *channel_recipe_findings, *suite_findings)
