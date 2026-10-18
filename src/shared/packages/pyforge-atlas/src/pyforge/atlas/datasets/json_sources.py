"""Public JSON sources that load as records, not a ``requests.Response`` (Story 34.1, CAP-64).

``pypi_endoflife_raw`` (endoflife.date's product list) and ``seed_spdx_upstream_list_raw``
(SPDX's ``licenses.json``) were bare ``api.APIDataset`` entries, whose ``load()`` returns a
``requests.Response``. The seed-gap nodes read a list or a dict, so both reports always saw an
empty input. :class:`JSONSourceDataset` composes the same ``APIDataset`` (no client of its own,
so the no-inline-IO scan holds), decodes the body, and checks it: the declared top-level shape,
non-empty, and, for a dict source, a non-empty ``require_key``. The check is top-level only; the
consuming node reads the elements.

AD-13: a fetch that fails, a body that is not JSON, of the wrong shape, empty, or missing its
required key keeps the last-good copy and stamps the same ``.staleness.json`` marker the
external-refresh stores write; it never hands the nodes an empty input while a last-good copy
exists, so a report is not rewritten empty because a host was down. With no last-good copy, the
empty container of the declared shape comes back, under a marker. A filesystem error on the
last-good copy or the marker is logged, never raised.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml
from kedro.io import AbstractDataset
from kedro_datasets.api import APIDataset
from pyforge.core.atomic_write import atomic_write

from .refresh import StalenessMarker, _safe_int

logger = logging.getLogger(__name__)

_SHAPES: dict[str, type] = {"list": list, "dict": dict}
_DECODES = ("json", "yaml")
_REASON_MAX = 300


def _describe_exc(exc: BaseException) -> str:
    """``Type: message``, with the cause kedro's load wrapper hides (it re-raises every
    failure inside ``APIDataset.load()`` as ``DatasetError``)."""
    text = f"{type(exc).__name__}: {exc}"
    cause = exc.__cause__
    if cause is not None:
        text += f" (cause: {type(cause).__name__}: {cause})"
    return text[:_REASON_MAX]


class JSONSourceDataset(AbstractDataset):
    """A public JSON endpoint, loaded as its decoded top-level ``list`` or ``dict``."""

    LAST_GOOD_FILENAME = "last_good.json"
    STALENESS_FILENAME = ".staleness.json"

    def __init__(
        self,
        *,
        url: str,
        filepath: str,
        expect: str,
        require_key: str | None = None,
        decode: str = "json",
        load_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if expect not in _SHAPES:
            raise ValueError(f"expect must be one of {sorted(_SHAPES)}, got {expect!r}")
        if require_key is not None and expect != "dict":
            raise ValueError("require_key applies only to expect: dict")
        if decode not in _DECODES:
            raise ValueError(f"decode must be one of {list(_DECODES)}, got {decode!r}")
        self._decode = decode
        self._url = url
        self._dir = Path(filepath)
        self._expect = expect
        self._require_key = require_key
        self._inner = APIDataset(url=url, load_args=load_args, credentials=credentials, metadata=metadata)
        self.metadata = metadata

    @property
    def last_good_path(self) -> Path:
        return self._dir / self.LAST_GOOD_FILENAME

    @property
    def _staleness_path(self) -> Path:
        return self._dir / self.STALENESS_FILENAME

    def staleness(self) -> StalenessMarker | None:
        """The current AD-13 marker, if the last load served last-good or nothing."""
        try:
            raw = json.loads(self._staleness_path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            return None
        if not isinstance(raw, dict):
            return None
        return StalenessMarker(
            stale=bool(raw.get("stale", True)),
            reason=str(raw.get("reason", "")),
            marked_at=_safe_int(raw.get("marked_at", 0)),
            last_good_exists=bool(raw.get("last_good_exists", False)),
        )

    def _problem(self, data: Any) -> str | None:
        """Why ``data`` cannot replace last-good, or ``None`` when it can."""
        if not isinstance(data, _SHAPES[self._expect]):
            return f"body is {type(data).__name__}, expected {self._expect}"
        if not data:
            return f"body is an empty {self._expect}"
        if self._require_key is not None and isinstance(data, dict) and not data.get(self._require_key):
            return f"body has no non-empty {self._require_key!r}"
        return None

    def _read_last_good(self) -> Any:
        try:
            data = json.loads(self.last_good_path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            return None
        return None if self._problem(data) else data

    def _write_last_good(self, data: Any) -> None:
        def _write(path: Path) -> None:
            path.write_text(json.dumps(data), encoding="utf-8")

        try:
            atomic_write(self.last_good_path, _write)
            self._staleness_path.unlink(missing_ok=True)
        except OSError as exc:  # serving the good body matters more than caching it (AD-13)
            # A marker left behind here keeps provenance reading "stale" for this fresh body
            # until a later load can clear it -- erring toward stale, which AD-13 permits.
            logger.warning(
                "could not keep last-good for %s (any old staleness marker stays until a later load): %s",
                self._dir,
                exc,
            )

    def _mark_stale(self, reason: str, *, last_good_exists: bool) -> None:
        marker = StalenessMarker(stale=True, reason=reason, last_good_exists=last_good_exists)

        def _write(path: Path) -> None:
            path.write_text(json.dumps(marker.to_dict(), indent=2), encoding="utf-8")

        try:
            atomic_write(self._staleness_path, _write)
        except OSError as exc:  # the marker must never take the run down (AD-13)
            logger.warning("could not write staleness marker for %s: %s", self._dir, exc)

    def _degrade(self, reason: str) -> Any:
        last_good = self._read_last_good()
        reason = f"{reason} -- {'keeping last-good' if last_good is not None else 'no last-good'}"
        logger.warning("%s: %s", self._url, reason)
        self._mark_stale(reason, last_good_exists=last_good is not None)
        return last_good if last_good is not None else _SHAPES[self._expect]()

    def load(self) -> Any:
        try:
            payload = self._inner.load()
        except Exception as exc:  # noqa: BLE001 -- kedro wraps every fetch failure as DatasetError (AD-13)
            return self._degrade(f"fetch failed: {_describe_exc(exc)}")
        try:
            data = self._decode_body(payload)
        except (ValueError, TypeError, yaml.YAMLError) as exc:
            return self._degrade(f"body not {self._decode.upper()}: {_describe_exc(exc)}")
        problem = self._problem(data)
        if problem is not None:
            return self._degrade(problem)
        self._write_last_good(data)
        return data

    def _decode_body(self, payload: Any) -> Any:
        if self._decode == "yaml":
            # Story 34.2: the conda-forge bot publishes the PyPI name mapping as YAML.
            text = payload.text if hasattr(payload, "text") else payload
            loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
            obj = yaml.load(text, Loader=loader)  # noqa: S506 -- a safe loader, chosen above
            # YAML can carry what JSON cannot (a bare date, !!binary); the last-good copy is
            # JSON, so such a body is refused here as undecodable, never raised later.
            return json.loads(json.dumps(obj))
        return payload.json() if hasattr(payload, "json") else json.loads(payload)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _exists(self) -> bool:
        return self.last_good_path.is_file()

    def _describe(self) -> dict[str, Any]:
        return {
            "url": self._url,
            "filepath": str(self._dir),
            "expect": self._expect,
            "require_key": self._require_key,
            "decode": self._decode,
        }
