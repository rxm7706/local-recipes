"""Story 11.2 -- AD-17's per-engine pattern registry, and `config/asgi.py`'s
registry-consult touchpoint for DB-GPT.

The registry itself (`config/engine_patterns.py`) has no heavy dependency
(just `django-environ`, already required for `config/settings/base.py`), so
`TestEngineRegistry` below runs everywhere. Importing `config.asgi` itself
still needs the `langflow` package (Story 11.1's own ASGI seam, built at
import time) -- mirrors `test_asgi_seam.py`/`test_langflow_mount.py`'s own
`pytest.importorskip` gate.
"""

from __future__ import annotations

import pytest

from config.engine_patterns import ENGINE_PATTERNS
from config.engine_patterns import get_sidecar_base_url


def test_langflow_is_pattern_a_dbgpt_is_pattern_b():
    assert ENGINE_PATTERNS["langflow"] == "A"
    assert ENGINE_PATTERNS["dbgpt"] == "B"


def test_get_sidecar_base_url_resolves_dbgpt():
    assert get_sidecar_base_url("dbgpt") == "http://dbgpt:5670"


def test_get_sidecar_base_url_rejects_a_pattern_a_engine():
    with pytest.raises(ValueError, match="not a Pattern-B"):
        get_sidecar_base_url("langflow")


def test_get_sidecar_base_url_rejects_an_unknown_engine():
    with pytest.raises(ValueError, match="not a Pattern-B"):
        get_sidecar_base_url("does-not-exist")


def test_asgi_module_import_does_not_trip_the_dbgpt_pattern_a_assertion():
    """`config/asgi.py`'s own registry-consult touchpoint: importing it
    asserts `ENGINE_PATTERNS["dbgpt"] != "A"`. Since the registry hardcodes
    `dbgpt: B`, that assertion always passes today -- this just proves the
    import path itself is wired up (an `AssertionError` here would mean the
    touchpoint and the registry disagree).
    """
    pytest.importorskip("langflow")

    import config.asgi  # noqa: PLC0415

    assert config.asgi.ENGINE_PATTERNS["dbgpt"] == "B"
