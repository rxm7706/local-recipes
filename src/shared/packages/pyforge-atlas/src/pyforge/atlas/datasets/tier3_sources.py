"""Tier 3 OS-distro bulk package indexes (Story 23.1).

Five independent :class:`ExternalRefreshDataset` subclasses — one per source
(homebrew, nixpkgs, spack, debian, fedora) — each owning fetch + parse IO via
an injected zero-arg ``fetcher`` and persisting a ``name``-column Parquet store
with genuine AD-13 last-good / staleness discipline.

Story 34.5: with no injected ``fetcher`` and ``pyforge.atlas.live_public_sources`` on,
each store fetches its own public index through a composed ``APIDataset``; off, it
keeps today's behaviour (a due refresh marks stale: no refresher wired).
"""

from __future__ import annotations

import gzip
import importlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from email.parser import Parser as EmailParser
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import DatasetError
from kedro_datasets.api import APIDataset

from . import public_sources
from .refresh import (
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    WEEKLY_SECONDS,
    ExternalRefreshDataset,
)

logger = logging.getLogger(__name__)

_TIER3_COLUMNS = ("name",)


def _as_text(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, bytes):
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    return str(payload)


def _maybe_decompress(payload: Any) -> str:
    if isinstance(payload, bytes):
        if payload[:2] == b"\x1f\x8b":
            try:
                return gzip.decompress(payload).decode("utf-8", errors="replace")
            except OSError:
                return ""
        return _as_text(payload)
    return _as_text(payload)


def parse_homebrew_formulae_json(payload: Any) -> list[str]:
    """Parse Homebrew ``formulae.brew.sh/api/formula.json`` — a JSON array of
    objects carrying a ``name`` field. Returns ``[]`` (never raises) on a
    malformed payload."""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except TypeError, ValueError:
            return []
    if not isinstance(payload, list):
        return []
    names: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name:
            names.append(name)
    return names


_NIX_PNAME = re.compile(rb'"pname"\s*:\s*"((?:[^"\\]|\\.)*)"')


def _brotli_or_raw(data: bytes) -> bytes:
    """``packages.json.br`` arrives decoded when the HTTP stack has brotli (it is served with
    ``Content-Encoding: br``); a still-compressed body is decoded here, lazily imported."""
    if data.lstrip()[:1] in (b"{", b"["):
        return data
    try:
        brotli = importlib.import_module("brotli")
        return bytes(brotli.decompress(data))
    except Exception:  # noqa: BLE001 -- not brotli either: the caller's parse degrades to []
        return data


def parse_nixpkgs_packages_json(payload: Any) -> list[str]:
    """Parse nixpkgs ``packages.json`` (``{"version": 2, "packages": {attr: {"pname": ...}}}``).

    Story 34.5: reports each package's ``pname`` -- its declared name, ``numpy`` for the attr
    ``python313Packages.numpy`` -- once, in first-seen order. The live index decodes to ~400 MB
    (measured 2026-10-18), so the names are read with a byte-level scan, never ``json.loads``.
    A payload with no ``pname`` (an attr-keyed object) falls back to the attribute keys. Returns
    ``[]`` (never raises) on a malformed payload."""
    if isinstance(payload, dict):
        nested = payload.get("packages")
        pkgs: dict[Any, Any] = nested if isinstance(nested, dict) else payload
        return [str(k) for k in pkgs if k]
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    if not isinstance(payload, bytes):
        return []
    data = _brotli_or_raw(payload)
    names: dict[str, None] = {}
    for match in _NIX_PNAME.finditer(data):
        try:
            name = json.loads(b'"' + match.group(1) + b'"')
        except ValueError:
            continue
        if isinstance(name, str) and name:
            names[name] = None
    if names:
        return list(names)
    try:
        doc = json.loads(data)
    except TypeError, ValueError:
        return []
    return parse_nixpkgs_packages_json(doc) if isinstance(doc, dict) else []


def parse_spack_packages(payload: Any) -> list[str]:
    """Parse a Spack bulk package index. Accepts a JSON array of names or of
    ``{"name": ...}`` records, a JSON object keyed by package name, or a JSON object
    with a ``packages`` list. Returns ``[]`` (never raises) on a malformed payload."""
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except TypeError, ValueError:
            return []
    if isinstance(payload, list):
        return _names_from_items(payload)
    if isinstance(payload, dict):
        if isinstance(payload.get("packages"), list):
            return _names_from_items(payload["packages"])
        return [str(k) for k in payload if k]
    return []


def _names_from_items(items: list[Any]) -> list[str]:
    """A list of names, or of records with a ``name`` (``packages.spack.io/data/packages.json``
    is ``[{"name", "description"}, ...]``, measured 2026-10-18)."""
    names: list[str] = []
    for item in items:
        if isinstance(item, dict):
            item = item.get("name")
        if isinstance(item, str) and item:
            names.append(item)
    return names


def parse_debian_packages_control(payload: Any) -> list[str]:
    """Parse a Debian ``Packages`` control file (plain or gzip-compressed bytes).
    One ``Package:`` field per stanza. Returns ``[]`` (never raises) on a
    malformed payload."""
    text = _maybe_decompress(payload)
    if not text.strip():
        return []
    try:
        parser = EmailParser()
        names: list[str] = []
        for block in text.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            msg = parser.parsestr(block + "\n")
            pkg = msg.get("Package")
            if pkg:
                names.append(str(pkg).strip())
        return names
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("debian Packages control parse failed: %s", exc)
        return []


def parse_fedora_packages(payload: Any) -> list[str]:
    """Parse a Fedora bulk index — JSON ``projects``/``items`` list, the
    ``pagure_owner_alias.json`` ``rpms`` map, or XML ``<name>`` / ``<pkg:name>``
    elements. Returns ``[]`` (never raises) on a malformed payload."""
    text = _maybe_decompress(payload)
    if not text.strip():
        return []
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(text)
        except TypeError, ValueError:
            return []
        if isinstance(data, list):
            return _names_from_fedora_items(data)
        if isinstance(data, dict):
            for key in ("projects", "items", "packages"):
                if isinstance(data.get(key), list):
                    return _names_from_fedora_items(data[key])
            # Story 34.5: ``src.fedoraproject.org/extras/pagure_owner_alias.json`` -- the
            # ``rpms`` namespace keyed by package name (measured 2026-10-18)
            if isinstance(data.get("rpms"), dict):
                return [str(k) for k in data["rpms"] if k]
        return []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    names: list[str] = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "name" and elem.text:
            names.append(elem.text.strip())
    return names


def _names_from_fedora_items(items: list[Any]) -> list[str]:
    names: list[str] = []
    for item in items:
        if isinstance(item, str) and item:
            names.append(item)
        elif isinstance(item, dict):
            for key in ("name", "project_name", "pkg_name"):
                val = item.get(key)
                if isinstance(val, str) and val:
                    names.append(val)
                    break
    return names


class _Tier3PackagesDatasetBase(ExternalRefreshDataset):
    """Shared AD-13 Parquet persistence for Tier 3 bulk OS indexes."""

    STORE_FILENAME = "packages.parquet"
    _REQUIRED_COLUMNS = _TIER3_COLUMNS
    _PARSER: Callable[[Any], list[str]]

    def __init__(
        self,
        *,
        filepath: str,
        url: str,
        fetcher: Callable[[], bytes | str] | None = None,
        cadence_seconds: int | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._url = str(url)
        self._timeout = int(timeout_seconds)
        if fetcher is None and public_sources.live():
            fetcher = self._public_fetch
        self._fetcher = fetcher
        super().__init__(
            filepath=filepath,
            refresher=self._do_refresh if fetcher is not None else None,
            cadence_seconds=cadence_seconds if cadence_seconds is not None else WEEKLY_SECONDS,
            required_resource=None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata,
        )

    def _public_fetch(self) -> bytes:
        """The store's own public index (Story 34.5), as bytes; a non-bytes body is a fetch failure."""
        payload = APIDataset(url=self._url, load_args={"timeout": self._timeout}).load()
        content = getattr(payload, "content", None)
        if not isinstance(content, bytes):
            raise DatasetError(f"{self._url}: expected a bytes body, got {type(content).__name__}")
        return content

    def _do_refresh(self) -> pd.DataFrame:
        payload = self._fetcher()
        # one row per name: Debian's Packages repeats a name across stanzas (349 of 76,665 on 2026-10-18)
        names = list(dict.fromkeys(self._PARSER(payload)))
        return pd.DataFrame({"name": names})

    @property
    def _store_path(self) -> Path:
        return Path(self._filepath) / self.STORE_FILENAME

    def _store_exists(self) -> bool:
        return self._store_path.is_file()

    def _store_mtime(self) -> float:
        return self._store_path.stat().st_mtime

    def _write(self, fetched: Any) -> None:
        frame = fetched if isinstance(fetched, pd.DataFrame) else pd.DataFrame(fetched)
        if "name" not in frame.columns:
            raise ValueError("tier-3 refresh frame missing required column: name")
        self._atomic_write(self._store_path, lambda p: frame.to_parquet(p, index=False))

    def load(self) -> pd.DataFrame:
        if not self._store_exists():
            self._mark_stale(
                "tier-3 store absent (never refreshed / offline)",
                only_if_absent=True,
            )
            return pd.DataFrame(columns=list(_TIER3_COLUMNS))
        try:
            frame = pd.read_parquet(self._store_path)
        except Exception as exc:
            logger.warning(
                "tier-3 store unreadable (%s), degrading to empty: %s",
                self._store_path,
                exc,
            )
            self._mark_stale("tier-3 store unreadable", only_if_absent=True)
            return pd.DataFrame(columns=list(_TIER3_COLUMNS))
        if "name" not in frame.columns:
            self._mark_stale("tier-3 store missing name column", only_if_absent=True)
            return pd.DataFrame(columns=list(_TIER3_COLUMNS))
        return frame

    def _describe(self) -> dict[str, Any]:
        base = super()._describe()
        base.update({"url": self._url, "fetcher_wired": self._fetcher is not None})
        return base


class HomebrewPackagesDataset(_Tier3PackagesDatasetBase):
    """Homebrew formulae bulk index — ``formulae.brew.sh/api/formula.json``."""

    _PARSER = staticmethod(parse_homebrew_formulae_json)


class NixpkgsPackagesDataset(_Tier3PackagesDatasetBase):
    """nixpkgs-unstable packages bulk index — ``packages.json`` keyed by attr path."""

    _PARSER = staticmethod(parse_nixpkgs_packages_json)


class SpackPackagesDataset(_Tier3PackagesDatasetBase):
    """Spack built-in package repo bulk index."""

    _PARSER = staticmethod(parse_spack_packages)


class DebianPackagesDataset(_Tier3PackagesDatasetBase):
    """Debian sid ``Packages`` control-file bulk index (gzip or plain)."""

    _PARSER = staticmethod(parse_debian_packages_control)


class FedoraPackagesDataset(_Tier3PackagesDatasetBase):
    """Fedora rawhide / src.fedoraproject.org bulk project index."""

    _PARSER = staticmethod(parse_fedora_packages)
