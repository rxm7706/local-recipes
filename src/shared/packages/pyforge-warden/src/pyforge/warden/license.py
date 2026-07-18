"""Per-component SPDX license verdicts + the license-axis warn-cap (Story
6.2, axis ``"license"``).

This module turns each component into an honest ``allowed`` /``denied`` /
``unknown`` :class:`~pyforge.warden.models.LicenseVerdict` (FR32/FR33) and
emits ``license:<spdx-or-"unknown">:<pkg>@<ver>`` ``Finding``s for the
``denied``/``unknown`` cases only. It NEVER projects an exit code and NEVER
spells the verdict lattice order — ``license_rung`` produces a
``(Status, StatusDriver)`` rung the sole owner (``verdict.py``) later
projects (the sole-ownership AST guard scans this module).

Resolution sources, per ``Component.ecosystem`` (never a network fetch, never
source-level/ScanCode-class license scanning):

* **conda** — the scanned recipe's OWN ``about: license:`` field, re-read
  from ONE of ``Component.provenance``'s manifest paths under the scan
  target (pre-build — never an install/build); ``recipe.yaml`` (v1) is
  preferred over ``meta.yaml`` (v0) when a component carries provenance from
  both (``_select_conda_manifest`` — a real v0->v1 feedstock-migration
  coexistence scenario, never whichever manifest happens to sort first).
  ``Component`` intentionally carries no raw
  license field of its own (``inventory.py``'s docstring: per-component
  verdict data lives on ``Finding``, never ``Component``), so every conda
  component declared by the SAME manifest shares that manifest's own
  ``about: license:`` value — a v1 simplification recorded in the story's
  Design Notes (there is no reliable, offline, pre-build way to learn one
  individual not-yet-built dependency's own license). The manifest is
  re-parsed via the SAME reused neutralize-then-load helpers the real
  extractors use (``strip_jinja_comments``/``neutralize_bare_braces`` for
  ``recipe.yaml``, ``strip_jinja_statements``/``neutralize_unquoted_braces``
  for ``meta.yaml``, dispatched by basename), followed by ``yaml.safe_load``
  — never a fresh Jinja/YAML pipeline, never bare-var substitution (out of
  this story's scope; a templated ``about: license:`` degrades to
  ``unknown``, never a crash, never a guess).
* **pypi** — ``importlib.metadata`` (fully offline: a local package-database
  read, never a subprocess, never a socket) WHEN the package happens to be
  installed in the running interpreter. PEP 639 ``License-Expression`` is
  tried first, then the legacy ``License`` short-string field, then trove
  classifiers (``License :: OSI Approved :: ...``) via a small curated
  local table — in that fallback order, mirroring the story's I/O matrix.
  An uninstalled package (``importlib.metadata.PackageNotFoundError``)
  resolves to ``unknown`` — never a silent clean, never a crash.

Every candidate string is normalized/validated through ``license-expression``
(``get_spdx_licensing().parse(..., validate=True)``) — an unparsable or
unrecognized expression degrades to ``unknown`` rather than being reported as
a confident (and possibly wrong) SPDX id.

Ownership decisions recorded:

* ``license_rung`` is a HARD ``Status.WARN`` cap — it NEVER consults
  ``config.license_policy`` and NEVER escalates. Real ``denied``->
  ``policy-violation`` / ``unknown``->``indeterminate`` escalation is Story
  6.5's sole ownership (Boundaries); the parameterized
  ``tests/conformance/test_axis_producer_ceiling.py`` this story also
  delivers mechanically pins this ceiling so a future edit cannot regress it
  silently.
* A ``license:`` ``Finding`` is emitted ONLY for ``denied``/``unknown``
  verdicts — never ``allowed`` (``Finding.__post_init__`` already enforces
  this at construction; ``license_findings`` never even attempts to build one
  for an ``allowed`` verdict). Every producer-supplied id segment passes
  through ``_sanitize_id_segment`` — imported from ``.interfaces`` (the
  shared id-grammar-safety helper every producer module already imports the
  SAME way, ``hygiene.py``/``vuln.py``/``cli.py`` included; unlike
  ``_is_safe_token``/``_indeterminate_finding``, which those two modules
  duplicate locally because they are AXIS-specific guards, id-segment
  sanitization is axis-agnostic grammar hygiene with one correct
  implementation).
* Verdict semantics (Boundaries — this story computes the verdict, never
  escalates it): with NEITHER ``--allow-licenses`` nor ``--deny-licenses``
  set, every resolvable license is ``allowed`` and every unresolvable one is
  ``unknown``. With ``--deny-licenses`` set, a resolvable license matching an
  entry is ``denied``. With ``--allow-licenses`` set, it becomes an
  allow-list: any resolvable license NOT in the list is ``denied``. A
  license matching BOTH lists is ``denied`` (deny checked first, so this
  falls out of the branch order rather than needing a separate rule). A
  compound (``AND``/``OR``) resolved expression is matched by its FLAT set
  of leaf symbols, not a whole-string comparison (``_classify_verdict``): a
  deny match on any symbol — including the BASE license of a ``WITH``
  grant (deny side only; see ``_with_base_symbols``) — denies the whole
  expression; an allow-list requires every symbol to be a member, else
  denied (an unlisted branch is an unreviewed license). Configured
  allow/deny entries are normalized
  through the SAME SPDX parse/validate pass a resolved license goes through
  (so ``gpl-3.0-only`` and ``GPL-3.0-only`` compare equal) and likewise
  decomposed to their own leaf symbols; an entry that fails to parse as a
  real SPDX id falls back to its own stripped text (a config typo must stay
  comparable, never silently dropped from the list).
* ``DEFAULT_LICENSE_POLICY`` is declared but UNUSED this story (mirrors
  ``vuln.DEFAULT_VULN_SEVERITY_POLICY``'s module-default-table precedent) —
  reserved for Story 6.5's real escalation; ``license_rung`` never reads it.
* ``family`` (``LicenseInfo.family``) is populated from a small, curated,
  LOCAL SPDX-id -> coarse-family table (mirrors conda-forge's own
  ``about.license_family`` convention) for a single (non-compound) resolved
  license only — a compound (``AND``/``OR``) expression's family is ``None``
  (too ambiguous to pick one). Deliberately NOT the ScanCode license
  database (Boundaries: never source-level/ScanCode-class scanning) — a
  small, non-exhaustive table, not a taxonomy.
* This module opens no socket and spawns no subprocess:
  ``importlib.metadata`` reads the local package database in-process, and
  ``license-expression`` parses strings in-process — both fully offline
  (the C0c socket-deny test harness covers this suite too).

This module parses YAML/metadata as DATA: no subprocess, no network, no exec,
no Jinja engine.
"""

from __future__ import annotations

import importlib.metadata
import re
from collections.abc import Iterator, Sequence
from pathlib import Path
from types import MappingProxyType

import license_expression
import yaml

from .extract._identity import yaml_safe_load_strict
from .extract.meta_v0 import neutralize_unquoted_braces, strip_jinja_statements
from .extract.recipe_v1 import neutralize_bare_braces, strip_jinja_comments
from .interfaces import _sanitize_id_segment
from .inventory import Component, Provenance
from .models import (
    AXIS_LICENSE,
    Ecosystem,
    Finding,
    LicenseInfo,
    LicenseVerdict,
    Status,
    StatusDriver,
)

_LICENSING = license_expression.get_spdx_licensing()

# A resolved/configured license candidate longer than this can never
# plausibly BE a short SPDX expression (a legacy PyPI `License` field
# commonly carries the FULL LICENSE TEXT, never a short expression) --
# never attempt to feed that to the parser as one. 1000, not the original
# 200 (review finding, 2026-07-18 follow-up pass): a VALID many-clause
# compound expression from a vendored-deps recipe (a 16-id `A AND B AND
# ...` chain is ~220 chars) blew the old cap and misreported a perfectly
# resolvable -- and possibly deny-matching -- license as `unknown`; full
# license text is kilobytes, so 1000 still rejects what the cap exists to
# reject.
_MAX_LICENSE_CANDIDATE_LENGTH = 1000

# license-expression's alias table confidently maps a small number of bare,
# version-ambiguous family labels to a SPECIFIC id ("GPL"/"gpl" ->
# "GPL-1.0-or-later" -- verified live; every other probed bare label --
# LGPL/AGPL/BSD/Apache/MPL/GPLv3/... -- already fails validation and
# degrades to unknown on its own). Following that guess would violate this
# module's own unknown-over-wrong principle (Fix 6's rationale): a v0
# ``meta.yaml`` carrying ``license: GPL`` (a real, common historic
# conda-forge shape) does NOT say WHICH GPL, so it degrades to ``unknown``
# instead (review finding, 2026-07-18 follow-up pass). Deprecated-but-
# unambiguous ids keep license-expression's mapping ("GPL-2.0" ->
# "GPL-2.0-only" is SPDX's own official deprecation resolution, not a
# guess). Known residual: a bare "GPL" INSIDE a compound expression
# ("MIT OR GPL") still rides the alias -- the bare-label case guarded here
# is the dominant real-world shape.
_AMBIGUOUS_BARE_LABELS = frozenset({"gpl"})

# SPDX's own user-defined license-reference grammar (``LicenseRef-<id>``,
# optionally ``DocumentRef-<id>:LicenseRef-<id>``): syntactically VALID
# SPDX whose key is -- by definition -- absent from the registry, so
# ``validate=True`` rejects it as an unknown key. Real conda-forge recipes
# use these (LicenseRef-HDF5, LicenseRef-NVIDIA-...), so treating them as
# unresolvable made every such license ``unknown`` AND made a
# ``--deny-licenses LicenseRef-...`` entry structurally inert (review
# finding, 2026-07-18 follow-up pass) -- see ``_license_ref_reparse``.
_LICENSE_REF_RE = re.compile(
    r"(?:DocumentRef-[A-Za-z0-9.\-]+:)?LicenseRef-[A-Za-z0-9.\-]+"
)

# A small, curated SPDX-id -> coarse "family" grouping (mirrors
# conda-forge's own about.license_family convention) -- NOT the ScanCode
# license database (Boundaries: never source-level/ScanCode-class
# scanning). Covers the common cases only; an unrecognized id leaves
# family=None (never guess).
_SPDX_FAMILY: dict[str, str] = {
    "MIT": "MIT",
    "0BSD": "BSD",
    "BSD-2-Clause": "BSD",
    "BSD-3-Clause": "BSD",
    "BSD-3-Clause-Clear": "BSD",
    "Apache-1.1": "Apache",
    "Apache-2.0": "Apache",
    "GPL-2.0-only": "GPL2",
    "GPL-2.0-or-later": "GPL2",
    "GPL-3.0-only": "GPL3",
    "GPL-3.0-or-later": "GPL3",
    "LGPL-2.1-only": "LGPL",
    "LGPL-2.1-or-later": "LGPL",
    "LGPL-3.0-only": "LGPL",
    "LGPL-3.0-or-later": "LGPL",
    "AGPL-3.0-only": "AGPL",
    "AGPL-3.0-or-later": "AGPL",
    "MPL-2.0": "MPL",
    "ISC": "ISC",
    "Unlicense": "Public-Domain",
    "PSF-2.0": "PSF",
    "Zlib": "Zlib",
}

# A small, curated trove-classifier -> SPDX-id table for the pypi
# resolution's third fallback tier (mirrors the same shape/spirit as
# conda-forge-expert's own recipe-generator.py classifier table, kept as
# an independent, local, offline copy here -- not imported, this package
# has no dependency on the skill layer).
#
# Fix 6 (review finding, 2026-07-18): the generic "License :: OSI Approved ::
# BSD License" classifier is DELIBERATELY absent -- it does not disambiguate
# BSD-2-Clause/BSD-3-Clause/0BSD/etc, so mapping it to a specific guess
# (formerly "BSD-3-Clause") contradicted this module's own stated principle
# (module docstring) that an unrecognized/ambiguous expression degrades to
# ``unknown`` rather than being confidently (and possibly wrongly)
# classified -- an absent entry here falls through to unknown via
# ``_classifier_license_candidate`` the same way any other un-mapped
# classifier already does.
_CLASSIFIER_SPDX: dict[str, str] = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "License :: OSI Approved :: "
    "GNU General Public License v3 or later (GPLv3+)": "GPL-3.0-or-later",
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)": "GPL-2.0-only",
    "License :: OSI Approved :: "
    "GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0-only",
    "License :: OSI Approved :: GNU Affero General Public License v3": "AGPL-3.0-only",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: The Unlicense (Unlicense)": "Unlicense",
    "License :: OSI Approved :: zlib/libpng License": "Zlib",
}

# The default license policy: LicenseVerdict -> Status. UNUSED this story
# (license_rung is a hard warn-cap, oblivious to this table) -- reserved for
# Story 6.5's real escalation, mirroring vuln.DEFAULT_VULN_SEVERITY_POLICY's
# module-default-table precedent. MappingProxyType-wrapped for the same
# ownership/immutability reason DEFAULT_HYGIENE_POLICY/
# DEFAULT_VULN_SEVERITY_POLICY already are.
DEFAULT_LICENSE_POLICY: MappingProxyType[LicenseVerdict, Status] = MappingProxyType(
    {
        LicenseVerdict.DENIED: Status.WARN,
        LicenseVerdict.UNKNOWN: Status.WARN,
    }
)


def license_rung(finding: Finding) -> tuple[Status, StatusDriver]:
    """Derive the ``(Status, StatusDriver)`` rung for one license-axis
    finding — UNCONDITIONALLY ``Status.WARN`` (Boundaries: never consult
    ``config.license_policy``, never escalate — real escalation is Story
    6.5's sole ownership). The driver carries the finding's own axis and
    id."""
    return (
        Status.WARN,
        StatusDriver(axis=finding.axis, finding_id=finding.id),
    )


# --- SPDX normalization ------------------------------------------------------


def _parse_spdx(candidate: str | None) -> tuple[str, str | None] | None:
    """Normalize ``candidate`` through ``license-expression``'s SPDX
    licensing (``validate=True, strict=False``) — ``None`` for anything
    unparsable, unrecognized, empty, or implausibly long to be a short SPDX
    expression (a legacy PyPI ``License`` field commonly carries the FULL
    LICENSE TEXT, never a short expression — never attempt to parse that as
    one). Returns ``(canonical-normalized-expression, family)`` on success;
    ``family`` is only ever set for a single (non-compound) recognized
    license id — a compound (``AND``/``OR``) expression's family is ``None``
    (too ambiguous to pick one). Never raises.

    Fix 1 (review finding, 2026-07-18): a ``WITH``-exception expression
    (``"GPL-2.0-only WITH Classpath-exception-2.0"``) is ``isliteral`` too
    (a single leaf symbol) but its symbol is a ``LicenseWithExceptionSymbol``,
    which carries NO ``.key`` attribute (only a plain ``LicenseSymbol``
    does) — a bare ``parsed.key`` access crashed the whole engine on any
    real WITH expression. ``getattr(parsed, "key", None)`` degrades that
    case to ``family=None`` (still a valid ``allowed``/``denied``/``unknown``
    verdict) instead of raising.

    Follow-up review pass (2026-07-18): three more hardenings. (a) the
    parser leaks NON-``ExpressionError`` exceptions on grammar-degenerate
    input — verified live: an empty parenthesis group ``"()"`` raises bare
    ``IndexError``, which killed the whole axis — so ANY parser escape now
    degrades to ``None``, honoring the never-raises contract. (b) the bare,
    version-ambiguous ``"GPL"`` label (which the parser's alias table
    confidently guesses as ``GPL-1.0-or-later``) degrades to ``None``
    instead — see ``_AMBIGUOUS_BARE_LABELS``. (c) an expression whose only
    unknown keys are ``LicenseRef-*`` references re-parses as valid opaque
    SPDX — see ``_license_ref_reparse``."""
    if not candidate:
        return None
    text = candidate.strip()
    if not text or len(text) > _MAX_LICENSE_CANDIDATE_LENGTH:
        return None
    if text.lower() in _AMBIGUOUS_BARE_LABELS:
        return None
    try:
        parsed = _LICENSING.parse(text, validate=True, strict=False)
    except license_expression.ExpressionError:
        parsed = _license_ref_reparse(text)
    except Exception:  # noqa: BLE001 — the never-raises contract: the
        # parser's non-ExpressionError escapes (verified live: IndexError
        # on "()") must degrade to unknown, not crash the axis.
        return None
    if parsed is None:
        return None
    expression = str(parsed)
    family = (
        _SPDX_FAMILY.get(getattr(parsed, "key", None)) if parsed.isliteral else None
    )
    return (expression, family)


def _license_ref_reparse(text: str) -> object | None:
    """Second-chance parse for an expression ``validate=True`` rejected
    (review finding, 2026-07-18 follow-up pass): accepted iff EVERY unknown
    key is ``LicenseRef-``-shaped (``_LICENSE_REF_RE`` — SPDX's own
    user-defined-reference grammar, syntactically valid SPDX that is BY
    DEFINITION absent from the registry), re-parsed with ``validate=False``
    so the reference survives as an opaque, comparable leaf symbol. Any
    other unknown key (a typo, a colloquial label like ``GPLv3``) returns
    ``None`` (unknown) — this is NOT a general validate=False escape hatch.
    Never raises (the same contract as ``_parse_spdx``; note
    ``unknown_license_keys`` itself leaks ``IndexError`` on
    grammar-degenerate input like ``"()"``)."""
    try:
        unknown = _LICENSING.unknown_license_keys(text)
        if not unknown or not all(
            _LICENSE_REF_RE.fullmatch(key) for key in unknown
        ):
            return None
        return _LICENSING.parse(text, validate=False, strict=False)
    except Exception:  # noqa: BLE001 — same never-raises contract as _parse_spdx
        return None


def _license_symbols(expression: str) -> frozenset[str]:
    """The flattened set of canonical leaf SPDX symbol strings in an
    ALREADY-VALIDATED ``expression`` (produced by a prior successful
    ``_parse_spdx`` call — e.g. ``str(parsed)`` — so this re-parse can never
    itself raise/fail). A literal (single-license, including a ``WITH``
    exception) expression's set is itself, e.g. ``{"MIT"}`` or
    ``{"GPL-2.0-only WITH Classpath-exception-2.0"}`` (a WITH expression is
    one indivisible grant, never split into its base license + exception).
    A compound expression's set is every OR/AND operand's own canonical
    string, e.g. both ``"Apache-2.0 OR BSD-2-Clause"`` and
    ``"Apache-2.0 AND BSD-2-Clause"`` yield ``{"Apache-2.0",
    "BSD-2-Clause"}`` — see ``_classify_verdict`` for why the boolean
    operator itself is deliberately not distinguished here.
    ``validate=False`` (follow-up review pass, 2026-07-18): the input is
    always a prior ``_parse_spdx`` product, which may legitimately contain
    ``LicenseRef-*`` keys absent from the registry — re-validating here
    would reject exactly what ``_license_ref_reparse`` just accepted."""
    parsed = _LICENSING.parse(expression, validate=False, strict=False)
    return frozenset(str(symbol) for symbol in parsed.symbols)


def _with_base_symbols(expression: str) -> frozenset[str]:
    """The BASE-license symbols of every ``WITH``-exception grant in an
    already-validated ``expression`` — ``{"GPL-2.0-only"}`` for
    ``"GPL-2.0-only WITH Classpath-exception-2.0"``, empty for an
    expression carrying no WITH grant. Consumed by ``_classify_verdict``'s
    DENY check ONLY (review finding, 2026-07-18 follow-up pass): denying a
    base license must taint every exception-carrying variant of it (a WITH
    grant still operates under the base license's obligations — the
    pre-fix behavior let ``--deny-licenses GPL-2.0-only`` silently pass
    ``GPL-2.0-only WITH Classpath-exception-2.0``, a fail-open asymmetry
    against the module's otherwise conservative taint rule). The ALLOW
    side deliberately keeps the indivisible-grant reading: allow-listing a
    base license does NOT auto-allow its WITH variants — an unreviewed
    exception grant stays denied under an allow-list."""
    parsed = _LICENSING.parse(expression, validate=False, strict=False)
    bases: set[str] = set()
    for symbol in parsed.symbols:
        base = getattr(symbol, "license_symbol", None)
        if base is not None:
            bases.add(str(base))
    return frozenset(bases)


def _normalize_tokens(raw: Sequence[str]) -> frozenset[str]:
    """Normalize a configured ``--allow-licenses``/``--deny-licenses`` list
    into a FLAT set of individual SPDX symbol tokens — the same shape
    ``_classify_verdict`` compares a resolved expression's own
    ``_license_symbols`` against. Each entry is normalized the same way a
    resolved component license is (``_parse_spdx``, so ``gpl-3.0-only`` and
    ``GPL-3.0-only`` compare equal), then decomposed via ``_license_symbols``
    (Fix 2, review finding 2026-07-18): a compound configured entry like
    ``"MIT OR Apache-2.0"`` contributes BOTH ``"MIT"`` and ``"Apache-2.0"``
    as independent tokens — the same flattening applied to a resolved
    expression, so a deny/allow entry matches regardless of the resolved
    expression's own operand order or boolean operator (order-independence
    a plain ``str() == str()`` comparison could not give, since
    ``license_expression`` preserves syntactic operand order rather than
    canonicalizing it). An entry that fails to parse as a real SPDX id
    falls back to its own stripped text as ONE opaque token — a defensive
    posture for DIRECT library callers only (follow-up review pass,
    2026-07-18): the CLI/TOML surfaces now reject such an entry at config
    load time (``config._coerce_license_list`` consults
    ``is_valid_license_token``), because an unparsable entry could never
    match any resolved license — a silently-dead policy gate."""
    tokens: set[str] = set()
    for entry in raw:
        stripped = entry.strip()
        if not stripped:
            continue
        parsed = _parse_spdx(stripped)
        if parsed is None:
            tokens.add(stripped)
            continue
        tokens.update(_license_symbols(parsed[0]))
    return frozenset(tokens)


def is_valid_license_token(text: str) -> bool:
    """Whether ``text`` is usable as an ``--allow-licenses``/
    ``--deny-licenses`` entry: it must normalize through the SAME
    ``_parse_spdx`` pass a resolved component license goes through (valid
    SPDX — single ids, compound expressions, ``WITH`` grants, and
    ``LicenseRef-*`` references all normalize; colloquial labels like
    ``GPLv3``/``BSD`` and grammar-degenerate strings like ``"()"`` do
    not). ``config._coerce_license_list`` consults this at load time
    (review finding, 2026-07-18 follow-up pass): a resolved license is
    always a ``_parse_spdx`` product, so a configured entry that CANNOT
    normalize the same way could never match anything — a configured-but-
    ineffective gate, the same failure mode the zero-usable-entries check
    already rejects."""
    return _parse_spdx(text) is not None


# --- conda: about: license: (pre-build, never a fresh Jinja/YAML pipeline) --


def _read_about_license(manifest_path: Path) -> str | None:
    """Re-read ONE conda manifest and extract its ``about: license:`` value —
    ``None`` on anything unreadable/malformed/absent (never a crash, never a
    guess): an unreadable file, invalid YAML, a non-mapping document, a
    missing/non-mapping ``about:`` section, a missing/non-string/blank
    ``license:`` value, or a basename this module does not recognize
    (``discovery.py`` only ever names a conda manifest ``recipe.yaml`` or
    ``meta.yaml``, so an unrecognized basename here is defensive, not a real
    path).

    Fix 3 (review finding, 2026-07-18): ``UnicodeDecodeError`` (a manifest
    containing invalid UTF-8 bytes) is a ``ValueError`` subclass, NOT an
    ``OSError`` subclass — catching only ``OSError`` let it escape uncaught
    and crash the whole engine. Caught alongside ``OSError`` here so this
    degrades to ``None`` (unknown) like every other malformed-manifest case,
    never a crash."""
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    basename = manifest_path.name
    if basename == "recipe.yaml":
        neutralized = neutralize_bare_braces(strip_jinja_comments(text))
    elif basename == "meta.yaml":
        stripped, _context = strip_jinja_statements(text)
        neutralized = neutralize_unquoted_braces(stripped)
    else:
        return None
    try:
        # yaml_safe_load_strict (not raw safe_load): refuses YAML alias
        # expansion (billion-laughs CPU/RSS exhaustion) and rejects duplicate
        # mapping keys — the same hardened loader the three extract/* YAML
        # readers use, since this re-reads the same untrusted conda manifest.
        # ComposerError/ConstructorError are yaml.YAMLError subclasses, so both
        # still degrade to `unknown` via the existing except below.
        document = yaml_safe_load_strict(neutralized)
    except (yaml.YAMLError, RecursionError):
        # RecursionError (follow-up review pass, 2026-07-18): deeply nested
        # flow collections blow the interpreter's recursion limit inside
        # yaml's parser — not a YAMLError subclass, so it escaped the
        # degrade-to-unknown contract (reachable only via a TOCTOU manifest
        # rewrite between extract and this re-read, but the contract is
        # never-a-crash regardless).
        return None
    if not isinstance(document, dict):
        return None
    about = document.get("about")
    if not isinstance(about, dict):
        return None
    license_value = about.get("license")
    if not isinstance(license_value, str) or not license_value.strip():
        return None
    return license_value.strip()


def _select_conda_manifest(provenance: tuple[Provenance, ...]) -> str | None:
    """Pick ONE ``Provenance.manifest`` path to re-read for a conda
    component's ``about: license:`` (Fix 7, review finding 2026-07-18): a
    ``recipe.yaml`` (v1) entry is ALWAYS preferred over a ``meta.yaml`` (v0)
    entry when a component carries BOTH — a real scenario during a v0->v1
    feedstock migration, where both files coexist and declare the same
    component. Without this, ``provenance[0]`` picked whichever manifest
    sorted first lexicographically (``Component.provenance`` is stored
    sorted by ``(manifest, section)`` after a merge/fold) — ``"meta.yaml" <
    "recipe.yaml"`` ASCII-sorts the v0 file first purely by accident, even
    though v1 is the authoritative source during a migration. Falls back to
    the first entry (the merge's own sort order) when neither/only one
    basename is present — ``None`` for an empty ``provenance``."""
    if not provenance:
        return None
    for entry in provenance:
        if Path(entry.manifest).name == "recipe.yaml":
            return entry.manifest
    return provenance[0].manifest


def _conda_about_license(
    component: Component, target: Path, cache: dict[str, str | None]
) -> str | None:
    """``component``'s manifest's own ``about: license:`` value, memoized per
    ``Provenance.manifest`` path across one ``license_findings`` call — every
    conda component declared by the SAME manifest shares its ``about:
    license:`` (see the module docstring), so a manifest with many
    dependencies is only ever re-read/re-parsed ONCE. ``recipe.yaml`` (v1)
    is preferred over ``meta.yaml`` (v0) when a component carries both (see
    ``_select_conda_manifest``)."""
    manifest = _select_conda_manifest(component.provenance)
    if manifest is None:
        return None
    if manifest not in cache:
        cache[manifest] = _read_about_license(target / manifest)
    return cache[manifest]


# --- pypi: importlib.metadata (fully offline; never a subprocess/socket) ----


# "License ::" trove classifiers that do NOT name a license — generic
# approval/property markers whose presence alongside a mapped,
# license-naming classifier is no conflict ("License :: OSI Approved" next
# to "License :: OSI Approved :: MIT License" just repeats the parent).
# Every OTHER "License ::" classifier names a license (or a license
# situation, e.g. "License :: Other/Proprietary License") and therefore
# participates in the ambiguity check below.
_NON_NAMING_LICENSE_CLASSIFIERS = frozenset(
    {
        "License :: OSI Approved",
        "License :: DFSG approved",
        "License :: Freely Distributable",
    }
)


def _classifier_license_candidate(meta: importlib.metadata.PackageMetadata) -> str | None:
    """The trove-classifier fallback tier's own single candidate (Fix 6b,
    review finding 2026-07-18): every license-naming ``Classifier`` maps
    through ``_CLASSIFIER_SPDX`` to its SPDX id, deduplicated to the
    DISTINCT set — a lone agreeing id is the tier's one candidate; zero or
    MORE THAN ONE distinct id yields ``None``, so resolution falls through
    to ``unknown`` rather than silently picking whichever classifier
    happened to be listed first.

    Follow-up review pass (2026-07-18): the ambiguity check counts
    UNMAPPED license-naming classifiers too, not just the mapped subset —
    a package declaring the generic ``License :: OSI Approved :: BSD
    License`` (deliberately absent from ``_CLASSIFIER_SPDX``, Fix 6)
    alongside ``... :: MIT License`` used to resolve confidently to
    ``MIT``, silently discarding the equally-declared-but-unidentifiable
    BSD license — the exact one-of-two-declared-licenses pick Fix 6b was
    written to prevent, resurfacing whenever one side of the conflict was
    unmapped. Any unmapped license-NAMING classifier now degrades the
    whole tier (generic non-naming approval markers are exempt — see
    ``_NON_NAMING_LICENSE_CLASSIFIERS``)."""
    ids: set[str] = set()
    for classifier in meta.get_all("Classifier") or ():
        if not classifier.startswith("License ::"):
            continue
        if classifier in _NON_NAMING_LICENSE_CLASSIFIERS:
            continue
        spdx = _CLASSIFIER_SPDX.get(classifier)
        if spdx is None:
            return None
        ids.add(spdx)
    if len(ids) == 1:
        return next(iter(ids))
    return None


def _pypi_license_candidates(meta: importlib.metadata.PackageMetadata) -> Iterator[str]:
    """PEP 639 ``License-Expression`` -> legacy ``License`` -> trove
    classifiers, in that fallback order (the story's I/O matrix) — yields raw
    candidate strings; the caller tries each through ``_parse_spdx`` until
    one parses. The classifier tier yields AT MOST ONE candidate (see
    ``_classifier_license_candidate``), never one per classifier."""
    expression = meta.get("License-Expression")
    if expression:
        yield expression
    legacy = meta.get("License")
    if legacy:
        yield legacy
    classifier_candidate = _classifier_license_candidate(meta)
    if classifier_candidate is not None:
        yield classifier_candidate


def _resolve_pypi_license(component: Component) -> tuple[str, str | None] | None:
    """Resolve ``component``'s license via ``importlib.metadata`` — ``None``
    when the package is not installed in the running interpreter
    (``PackageNotFoundError``) or none of its candidate fields parse as a
    valid SPDX expression. Fully offline: a local package-database read,
    never a subprocess, never a socket.

    Fix 4 (review finding, 2026-07-18): ``importlib.metadata.metadata("")``
    (or a whitespace-only name) raises ``ValueError``, NOT
    ``PackageNotFoundError`` — an empty/blank ``pypi_identity.name`` escaped
    uncaught and crashed the engine. Caught alongside
    ``PackageNotFoundError`` here so this degrades to ``None`` (unknown)
    like any other unresolvable name, never a crash."""
    name = (
        component.pypi_identity.name
        if component.pypi_identity is not None
        else component.name
    )
    try:
        meta = importlib.metadata.metadata(name)
    except (importlib.metadata.PackageNotFoundError, ValueError):
        return None
    for candidate in _pypi_license_candidates(meta):
        parsed = _parse_spdx(candidate)
        if parsed is not None:
            return parsed
    return None


def _resolve_license(
    component: Component, target: Path, conda_cache: dict[str, str | None]
) -> tuple[str, str | None] | None:
    """Dispatch by ``component.ecosystem`` — conda via the scanned recipe's
    own ``about: license:``, pypi via ``importlib.metadata``. ``None``
    (unresolvable) for anything else, and for any ecosystem-appropriate path
    that itself resolves to nothing."""
    if component.ecosystem is Ecosystem.CONDA:
        return _parse_spdx(_conda_about_license(component, target, conda_cache))
    if component.ecosystem is Ecosystem.PYPI:
        return _resolve_pypi_license(component)
    return None


# --- verdict + finding construction -----------------------------------------


def _classify_verdict(
    resolution: tuple[str, str | None] | None,
    *,
    allow: frozenset[str],
    deny: frozenset[str],
) -> LicenseVerdict:
    """Verdict semantics (Boundaries — see the module docstring for the full
    rationale): unresolvable -> ``unknown``. Resolvable: with neither list
    set, every resolvable license is ``allowed``; a ``deny_licenses`` match
    is ``denied`` (checked first, so a license matching BOTH lists lands
    ``denied`` without a separate rule); otherwise, with ``allow_licenses``
    set, a non-member is ``denied``; with neither list matching, ``allowed``.

    Fix 2 (review finding, 2026-07-18) — compound (``AND``/``OR``)
    expression semantics: matching is done over ``_license_symbols``' FLAT
    set of leaf symbols, never a plain ``str() == str()`` comparison —
    ``license_expression`` preserves syntactic operand order rather than
    canonicalizing it, so ``"MIT OR Apache-2.0"`` and ``"Apache-2.0 OR
    MIT"`` render as different strings despite being logically identical; a
    naive string-equality check could miss a real deny/allow match purely
    from operand order. ``allow``/``deny`` are themselves pre-flattened by
    ``_normalize_tokens``, so this comparison is symbol-set-vs-symbol-set
    throughout. A deny match on ANY of the resolved expression's symbols
    (whether joined by ``AND`` or ``OR`` — the operator itself carries no
    special meaning here) composes ``denied`` — the conservative "one
    denied component taints the whole expression" reading. With
    ``allow_licenses`` set, EVERY resolved symbol must be a member for the
    whole expression to count ``allowed``; one unlisted OR/AND branch is an
    UNREVIEWED license, so the conservative choice is ``denied``, not a
    permissive "any branch allowed is enough" — this is a real design
    call, not dictated by "denied wins on overlap" alone (the only rule
    Boundaries already established), so it is spelled out here explicitly.

    Follow-up review pass (2026-07-18) — ``WITH``-grant deny expansion:
    the DENY intersection additionally includes the BASE license of every
    ``WITH``-exception grant (``_with_base_symbols``), so denying
    ``GPL-2.0-only`` also taints ``GPL-2.0-only WITH
    Classpath-exception-2.0`` (the grant still operates under the base
    license's obligations). The ALLOW subset check deliberately does NOT
    get the same expansion — allow-listing a base license does not
    auto-allow its exception variants (an unreviewed grant stays denied).
    """
    if resolution is None:
        return LicenseVerdict.UNKNOWN
    expression, _family = resolution
    symbols = _license_symbols(expression)
    if (symbols | _with_base_symbols(expression)) & deny:
        return LicenseVerdict.DENIED
    if allow:
        return LicenseVerdict.ALLOWED if symbols <= allow else LicenseVerdict.DENIED
    return LicenseVerdict.ALLOWED


def _license_finding(
    component: Component,
    verdict: LicenseVerdict,
    resolution: tuple[str, str | None] | None,
) -> Finding:
    """Build the ``license:`` ``Finding`` for a ``denied``/``unknown``
    verdict (never called for ``allowed`` — the caller's own filter). The
    id's middle segment is the (sanitized) normalized SPDX expression for
    ``denied``, or the literal ``"unknown"`` token for ``unknown`` — the
    ``license:<spdx-or-"unknown">:<pkg>@<ver>`` grammar
    (``models.py:_FINDING_ID_FAMILIES``)."""
    version_segment = (
        _sanitize_id_segment(component.version) if component.version else "unspecified"
    )
    name_segment = _sanitize_id_segment(component.name)
    if verdict is LicenseVerdict.UNKNOWN or resolution is None:
        expression = "unknown"
        family = None
        message = f"{component.name}: license could not be resolved"
    else:
        expression, family = resolution
        message = f"{component.name}: license {expression!r} is denied"
    reason_segment = _sanitize_id_segment(expression)
    return Finding(
        id=f"license:{reason_segment}:{name_segment}@{version_segment}",
        axis=AXIS_LICENSE,
        message=message,
        subject=component.name,
        severity=None,
        license=LicenseInfo(expression=expression, family=family, verdict=verdict),
    )


def license_findings(
    components: Sequence[Component],
    target: Path,
    *,
    allow_licenses: Sequence[str] = (),
    deny_licenses: Sequence[str] = (),
) -> tuple[Finding, ...]:
    """Compute the WHOLE license axis's findings for one scan — one
    ``denied``/``unknown``-verdict ``Finding`` per component with such a
    verdict (an ``allowed`` verdict emits none), sorted by id. Mirrors
    ``hygiene.py``'s/``vuln.py``'s "one function computes the whole axis's
    findings" shape. A conda manifest is re-read + neutralize-parsed AT MOST
    ONCE per distinct ``Provenance.manifest`` path across the whole component
    set (see ``_conda_about_license``)."""
    allow = _normalize_tokens(allow_licenses)
    deny = _normalize_tokens(deny_licenses)
    conda_cache: dict[str, str | None] = {}
    findings: list[Finding] = []
    for component in components:
        resolution = _resolve_license(component, target, conda_cache)
        verdict = _classify_verdict(resolution, allow=allow, deny=deny)
        if verdict is LicenseVerdict.ALLOWED:
            continue
        findings.append(_license_finding(component, verdict, resolution))
    return tuple(sorted(findings, key=lambda f: f.id))
