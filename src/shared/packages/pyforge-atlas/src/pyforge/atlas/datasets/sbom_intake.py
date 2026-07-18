"""Story B7 — Universal SBOM intake datasets (dataset-owned IO, AD-2).

Two read-only ``AbstractDataset`` classes + the pure § 4.10 format parsers they
call (importable, IO-free, so fixtures exercise them without touching disk):

- :class:`SbomIntakeDataset` — reads a user-supplied § 4.10 manifest / lock / SBOM
  (``Path.read_text`` — dataset-owned file IO, which is NOT on the A2 no-inline-IO
  denylist) and dispatches to the pure parser by filename/format, returning a
  normalized inventory. This LANDS the A2 ``sbom_intake_entry`` interim (was
  ``json.JSONDataset``).

- :class:`TransitiveResolverDataset` — the FR-17 transitive resolver. The fetch
  (pip ``--dry-run --report`` / py-rattler solve) is an **injected** callable so the
  package NEVER imports ``subprocess``/HTTP (both on the A2 denylist, AST-scanned
  over the whole package). Default ``resolver=None`` == OFFLINE → an explicit
  ``unresolved`` marker (AD-13); any resolver exception is caught → ``unresolved``.
  It never crashes/hangs (the B1/B2 injected-fetcher pattern; cf.
  ``BigQueryDownloadsDataset``).

The pure parsers port VERBATIM from the shipped ``scan_project.py`` (HARD read-only
``.claude/**``); they are NOT imported from ``.claude`` (fragile + off-package).

**NBSP (AC-4b).** ``normalize_ws`` maps every Unicode Zs (incl. NBSP ``\\xa0`` +
narrow-NBSP ``\\u202f``) to an ASCII space BEFORE parsing, so NBSP-padded pasted
``conda list`` / ``pip list`` text parses identically to its ASCII-space form. Modern
CPython folds NBSP in ``str.split()``/``\\s`` by accident, but the guarantee here is
made EXPLICIT so no sub-parser (or future port) can regress it.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable

from kedro.io import AbstractDataset

# ── pure whitespace normalization (AC-4b) ─────────────────────────────────────


def normalize_ws(text: str) -> str:
    """Map every Unicode space-separator (Zs — incl. NBSP ``\\xa0`` and
    narrow-NBSP ``\\u202f``) to an ASCII space. Makes NBSP-padded pasted text
    parse identically to its ASCII-space form BY CONSTRUCTION (AC-4b)."""
    return "".join(" " if unicodedata.category(ch) == "Zs" else ch for ch in text)


# ── the normalized inventory row ──────────────────────────────────────────────


def _dep(
    name: str,
    version: str | None,
    ecosystem: str,
    manifest: str,
    *,
    properties: list[dict[str, str]] | None = None,
    purl: str | None = None,
) -> dict[str, Any]:
    """One normalized inventory row. ``properties``/``purl`` carry through from an
    SBOM passthrough so the normalizer can preserve ``cfe:*`` + ``?channel`` (AD-10)."""
    row: dict[str, Any] = {
        "name": name.lower(),
        "version": version,
        "ecosystem": ecosystem,
        "manifest": manifest,
    }
    if properties:
        row["properties"] = properties
    if purl:
        row["purl"] = purl
    return row


# ── § 4.10 pure format parsers (ported from scan_project.py) ──────────────────

_REQ_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:==|>=|<=|~=|!=|<|>)?\s*([^\s;,#]*)")


def parse_requirements_txt(text: str, manifest: str = "requirements.txt") -> list[dict[str, Any]]:
    """``requirements.txt`` — PEP 508 lines (pypi). Editable/URL/option lines skipped."""
    deps: list[dict[str, Any]] = []
    for raw in normalize_ws(text).splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-")):
            continue
        m = _REQ_RE.match(line)
        if m and m.group(1):
            deps.append(_dep(m.group(1), m.group(2) or None, "pypi", manifest))
    return deps


def parse_pip_list_text(text: str, manifest: str = "pip-list.txt") -> list[dict[str, Any]]:
    """``pip list`` / ``pip freeze`` / ``pip list --format=json`` (pypi). S5a intake."""
    stripped = normalize_ws(text).lstrip()
    if stripped.startswith("["):
        try:
            rows = json.loads(stripped)
        except json.JSONDecodeError:
            return []
        return [
            _dep(str(r["name"]), r.get("version"), "pypi", manifest)
            for r in rows
            if isinstance(r, dict) and r.get("name")
        ]
    deps: list[dict[str, Any]] = []
    for raw in normalize_ws(text).splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-")):
            continue
        if re.match(r"^Package\s+Version", line, re.IGNORECASE) or re.match(r"^-+(\s+-+)*$", line):
            continue
        m = re.match(r"^([A-Za-z0-9._-]+)==([^\s;]+)", line)  # freeze
        if m:
            deps.append(_dep(m.group(1), m.group(2), "pypi", manifest))
            continue
        m = re.match(r"^([A-Za-z0-9._-]+)\s+(\d[^\s]*)", line)  # columns
        if m:
            deps.append(_dep(m.group(1), m.group(2), "pypi", manifest))
    return deps


def parse_conda_list_text(text: str, manifest: str = "conda-list.txt") -> list[dict[str, Any]]:
    """``conda list`` (default cols / ``--export`` / ``--json``) — conda; rows whose
    channel is ``pypi`` are pip-installed (ecosystem=pypi). S5a intake."""
    stripped = normalize_ws(text).lstrip()
    if stripped.startswith("["):
        try:
            rows = json.loads(stripped)
        except json.JSONDecodeError:
            return []
        out: list[dict[str, Any]] = []
        for r in rows:
            if not isinstance(r, dict) or not r.get("name"):
                continue
            eco = "pypi" if r.get("channel") == "pypi" else "conda"
            out.append(_dep(str(r["name"]), r.get("version"), eco, manifest))
        return out
    deps: list[dict[str, Any]] = []
    for raw in normalize_ws(text).splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "@")):
            continue
        if line.startswith(("http://", "https://", "file://")):  # --explicit URL rows
            basename = line.split("#", 1)[0].rsplit("/", 1)[-1]
            m = re.match(r"^(.+)-([^-]+)-[^-]+\.(?:conda|tar\.bz2)$", basename)
            if m:
                deps.append(_dep(m.group(1), m.group(2), "conda", manifest))
            continue
        m = re.match(r"^([A-Za-z0-9._-]+)=([^=\s]+)=(\S+)$", line)  # --export
        if m:
            deps.append(_dep(m.group(1), m.group(2), "conda", manifest))
            continue
        parts = line.split()  # default cols: name version build [channel]
        if len(parts) >= 2 and re.match(r"^\d", parts[1]):
            channel = parts[3] if len(parts) >= 4 else None
            eco = "pypi" if channel == "pypi" else "conda"
            deps.append(_dep(parts[0], parts[1], eco, manifest))
    return deps


def parse_environment_yml(text: str, manifest: str = "environment.yml") -> list[dict[str, Any]]:
    """``environment.yml`` — the ``dependencies:`` list (conda), incl. a nested
    ``- pip:`` block (pypi). Kept intentionally light (line-based, no full YAML dep)."""
    deps: list[dict[str, Any]] = []
    in_deps = False
    in_pip = False
    for raw in normalize_ws(text).splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^dependencies:\s*$", stripped):
            in_deps = True
            continue
        if in_deps and re.match(r"^[A-Za-z0-9_]+:\s*$", stripped) and not stripped.startswith("-"):
            in_deps = in_pip = False
            continue
        if not in_deps:
            continue
        if re.match(r"^-\s*pip:\s*$", stripped):
            in_pip = True
            continue
        m = re.match(r"^-\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:[=<>!~]+\s*([^\s;#]+))?", stripped)
        if m and m.group(1) and m.group(1) not in ("python", "pip"):
            eco = "pypi" if in_pip else "conda"
            deps.append(_dep(m.group(1), m.group(2) or None, eco, manifest))
    return deps


_TOML_DEP_RE = re.compile(r'^\s*"?([A-Za-z0-9][A-Za-z0-9._-]*)"?\s*=\s*"?[<>=~!*^]*\s*([0-9][^"\s,]*)?')


def _parse_toml_tables(text: str, tables: tuple[str, ...], ecosystem: str, manifest: str) -> list[dict[str, Any]]:
    """Very small TOML table scanner (dependencies-only) — no toml dependency; good
    enough for pixi.toml ``[dependencies]`` / pyproject ``[project] dependencies``."""
    deps: list[dict[str, Any]] = []
    cur: str | None = None
    for raw in normalize_ws(text).splitlines():
        line = raw.rstrip()
        m = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
        if m:
            cur = m.group(1).strip()
            continue
        if cur in tables:
            m = _TOML_DEP_RE.match(line)
            if m and m.group(1) and m.group(1) not in ("python",):
                deps.append(_dep(m.group(1), m.group(2) or None, ecosystem, manifest))
    return deps


def parse_pixi_toml(text: str, manifest: str = "pixi.toml") -> list[dict[str, Any]]:
    conda = _parse_toml_tables(text, ("dependencies", "tool.pixi.dependencies"), "conda", manifest)
    pypi = _parse_toml_tables(text, ("pypi-dependencies", "tool.pixi.pypi-dependencies"), "pypi", manifest)
    return conda + pypi


def parse_pyproject_toml(text: str, manifest: str = "pyproject.toml") -> list[dict[str, Any]]:
    """PEP 621 ``[project] dependencies`` array (pypi)."""
    deps: list[dict[str, Any]] = []
    in_deps = False
    for raw in normalize_ws(text).splitlines():
        line = raw.strip()
        if re.match(r"^dependencies\s*=\s*\[", line):
            in_deps = True
            line = line.split("[", 1)[1]
        elif not in_deps:
            continue
        for item in re.findall(r'"([^"]+)"', line):
            m = _REQ_RE.match(item.strip())
            if m and m.group(1):
                deps.append(_dep(m.group(1), m.group(2) or None, "pypi", manifest))
        if "]" in line:
            in_deps = False
    return deps


def _purl_ecosystem(purl: str) -> str:
    """Map a purl ``pkg:<type>/...`` to the matcher ecosystem (mirrors the shipped
    ``inventory_match.annotate_sbom`` classification)."""
    m = re.match(r"^pkg:([A-Za-z0-9.+-]+)/", purl or "")
    t = (m.group(1).lower() if m else "")
    return {"pypi": "pypi", "conda": "conda"}.get(t, "npm" if t == "npm" else t or "generic")


def parse_cyclonedx(doc: dict[str, Any], manifest: str = "sbom.cdx.json") -> list[dict[str, Any]]:
    """CycloneDX SBOM passthrough — PRESERVE each component's ``cfe:*`` properties
    and ``purl`` (incl. ``?channel=conda-forge``) VERBATIM (AD-10, never stripped)."""
    deps: list[dict[str, Any]] = []
    for comp in doc.get("components") or []:
        name = comp.get("name")
        if not name:
            continue
        purl = comp.get("purl")
        eco = _purl_ecosystem(purl) if purl else "pypi"
        deps.append(
            _dep(
                str(name),
                comp.get("version") or None,
                eco,
                manifest,
                properties=list(comp.get("properties") or []),
                purl=purl,
            )
        )
    return deps


def parse_spdx(doc: dict[str, Any], manifest: str = "sbom.spdx.json") -> list[dict[str, Any]]:
    """SPDX SBOM passthrough — deps from ``packages[]`` + purl ``externalRefs``."""
    deps: list[dict[str, Any]] = []
    for pkg in doc.get("packages") or []:
        name = pkg.get("name")
        if not name:
            continue
        purl = None
        for ref in pkg.get("externalRefs") or []:
            if ref.get("referenceType") == "purl":
                purl = ref.get("referenceLocator")
                break
        eco = _purl_ecosystem(purl) if purl else "pypi"
        deps.append(_dep(str(name), pkg.get("versionInfo") or None, eco, manifest, purl=purl))
    return deps


# ── the § 4.10 dispatch ───────────────────────────────────────────────────────

_TEXT_PARSERS = {
    "requirements": parse_requirements_txt,
    "pip-list": parse_pip_list_text,
    "conda-list": parse_conda_list_text,
    "environment": parse_environment_yml,
    "pixi": parse_pixi_toml,
    "pyproject": parse_pyproject_toml,
}


def _detect_format(filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith((".cdx.json", ".cyclonedx.json")) or "cyclonedx" in name:
        return "cyclonedx"
    if name.endswith(".spdx.json") or "spdx" in name:
        return "spdx"
    if name.startswith("requirements") or name.endswith("requirements.txt"):
        return "requirements"
    if name.startswith("environment") and name.endswith((".yml", ".yaml")):
        return "environment"
    if name == "pixi.toml" or name.endswith("pixi.toml"):
        return "pixi"
    if name == "pyproject.toml" or name.endswith("pyproject.toml"):
        return "pyproject"
    if "conda" in name and "list" in name:
        return "conda-list"
    if "pip" in name and ("list" in name or "freeze" in name):
        return "pip-list"
    return "json"


def parse_intake(
    raw: str | dict[str, Any],
    *,
    filename: str = "",
    fmt: str | None = None,
) -> dict[str, Any]:
    """Dispatch a § 4.10 intake to the right pure parser. Returns
    ``{"format": <fmt>, "deps": [<row>, ...], "passthrough": <bool>}``. Pure — no IO."""
    detected = fmt or _detect_format(filename)
    if detected == "json" and isinstance(raw, str):
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError:
            doc = None
        if isinstance(doc, dict):
            if doc.get("bomFormat") == "CycloneDX" or "components" in doc:
                detected = "cyclonedx"
                raw = doc
            elif "spdxVersion" in doc or "SPDXID" in doc:
                detected = "spdx"
                raw = doc
    if detected in ("cyclonedx", "spdx"):
        # A malformed SBOM file (filename/fmt-resolved) never crashes the load — mirror
        # the text-parser never-crash contract (Edge-HIGH: json.loads was uncaught here).
        if isinstance(raw, dict):
            doc = raw
        else:
            try:
                doc = json.loads(raw)
            except json.JSONDecodeError:
                doc = None
        if not isinstance(doc, dict):
            return {"format": detected, "deps": [], "passthrough": True}
        if detected == "cyclonedx":
            return {"format": "cyclonedx", "deps": parse_cyclonedx(doc, filename or "sbom.cdx.json"), "passthrough": True}
        return {"format": "spdx", "deps": parse_spdx(doc, filename or "sbom.spdx.json"), "passthrough": True}
    text = raw if isinstance(raw, str) else json.dumps(raw)
    parser = _TEXT_PARSERS.get(detected)
    if parser is None:
        # unknown text → try pip-list heuristics (never crash)
        parser = parse_pip_list_text
    return {"format": detected, "deps": parser(text, filename or detected), "passthrough": False}


# ── the datasets (IO owners) ──────────────────────────────────────────────────


class SbomIntakeDataset(AbstractDataset):
    """§ 4.10 tiered intake — dataset-owned file parsing (AD-2). Read-only.

    ``load()`` reads the user-supplied manifest/lock/SBOM at ``filepath`` (a runtime
    param) and returns the normalized inventory (``parse_intake``). Construction is
    lazy (no IO at ``__init__``) so ``DataCatalog.from_config`` stays offline.
    """

    def __init__(
        self,
        *,
        filepath: str,
        format: str | None = None,  # noqa: A002 - catalog key name
        load_args: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._filepath = filepath
        self._format = format
        self._load_args = dict(load_args or {})
        self.metadata = metadata

    def load(self) -> dict[str, Any]:
        path = Path(self._filepath)
        raw = path.read_text(encoding="utf-8", errors="replace")  # dataset-owned file IO (not denylisted)
        return parse_intake(raw, filename=path.name, fmt=self._format)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is a read-only intake source; it is never saved to.")

    def _describe(self) -> dict[str, Any]:
        return {"filepath": self._filepath, "format": self._format or "auto"}


class TransitiveResolverDataset(AbstractDataset):
    """FR-17 transitive resolver — dataset-owned IO (AD-2), offline-safe (AD-13).

    The real fetch (pip ``--dry-run --report`` / py-rattler solve) is an INJECTED
    ``resolver(text) -> {"deps": [...], "depth": int, "fanout": int}`` callable, so this
    module NEVER imports ``subprocess``/HTTP (both on the A2 no-inline-IO denylist).
    Default ``resolver=None`` == OFFLINE → an explicit ``unresolved`` marker; any
    resolver exception is caught → ``unresolved``. It never crashes/hangs.
    """

    def __init__(
        self,
        *,
        filepath: str,
        resolver: Callable[[str], dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._filepath = filepath
        self._resolver = resolver
        self.metadata = metadata

    def load(self) -> dict[str, Any]:
        if self._resolver is None:
            return {
                "resolution": "unresolved",
                "reason": "offline: no transitive resolver injected (consumer profile)",
                "deps": [],
                "depth": None,
                "fanout": None,
            }
        try:
            text = Path(self._filepath).read_text(encoding="utf-8", errors="replace")
            result = self._resolver(text)
            deps = list(result.get("deps") or [])
            return {
                "resolution": "resolved",
                "deps": deps,
                "depth": result.get("depth"),
                "fanout": result.get("fanout", len(deps)),
            }
        except Exception as exc:  # AD-13: a resolver failure NEVER takes the run down
            return {
                "resolution": "unresolved",
                "reason": f"resolver failed: {type(exc).__name__}: {exc}",
                "deps": [],
                "depth": None,
                "fanout": None,
            }

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is a read-only resolver source; it is never saved to.")

    def _describe(self) -> dict[str, Any]:
        return {"filepath": self._filepath, "resolver": "injected" if self._resolver else "offline(None)"}
