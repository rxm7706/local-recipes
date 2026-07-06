"""lts-registry.yaml — the git-tracked conda-name→endoflife-slug map.

cyclonedx-universe-inventory Wave D / S7, decision 5(b). Pins the schema
(dated entries, valid sources, no duplicate aliases, a slug OR manual
lts_lines per entry) and the EolClient's slug-resolution over the seed file.
Every entry must be dated so the retro can expire stale manual assertions.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
_REGISTRY = _SCRIPTS_DIR.parent / "data" / "lts-registry.yaml"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def raw():
    import yaml
    return yaml.safe_load(_REGISTRY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def lf():
    return _load("library_futures")


_VALID_SOURCES = {"endoflife", "manual", "heuristic-seed"}


def test_top_level_schema(raw):
    assert raw["version"] == 1
    assert dt.date.fromisoformat(str(raw["updated"]))
    assert isinstance(raw["products"], dict) and raw["products"]


def test_every_entry_dated_and_sourced(raw):
    for name, entry in raw["products"].items():
        assert entry.get("source") in _VALID_SOURCES, f"{name}: bad source"
        assert dt.date.fromisoformat(str(entry["added"])), f"{name}: bad added date"


def test_slug_or_manual_lines(raw):
    for name, entry in raw["products"].items():
        if entry.get("source") == "manual":
            lines = entry.get("lts_lines") or []
            assert lines, f"{name}: manual entry needs lts_lines"
            for ln in lines:
                assert dt.date.fromisoformat(str(ln["eol"])), f"{name}: bad eol"
        elif entry.get("source") == "endoflife":
            assert entry.get("slug"), f"{name}: endoflife entry needs a slug"
        # heuristic-seed may have neither (labeled heuristic only)


def test_no_alias_claimed_twice(raw):
    # an alias may repeat WITHIN one product (name vs a case variant); the
    # error is two DIFFERENT products claiming the same alias.
    seen: dict[str, str] = {}
    for name, entry in raw["products"].items():
        for alias in [name, *(entry.get("aliases") or [])]:
            key = str(alias).lower()
            assert seen.get(key, name) == name, \
                f"alias {key!r} claimed by {seen.get(key)} and {name}"
            seen[key] = name


def test_registry_covers_the_calibration_products(raw):
    # django (LTS-policy, endoflife) is the S8 calibration anchor
    assert "django" in raw["products"]
    assert raw["products"]["django"].get("lts_policy") is True


# ── slug resolution via the client ───────────────────────────────────────────

def test_load_lts_registry_indexes_aliases(lf):
    idx = lf.load_lts_registry(_REGISTRY)
    assert "django" in idx
    assert "torch" in idx and idx["torch"]["slug"] == "pytorch"   # alias → slug


def test_resolve_slug_alias_then_bare(lf):
    client = lf.EolClient(cache_path=Path("/nonexistent/eol_cache.json"),
                          fetcher=lambda s: None, registry=lf.load_lts_registry(_REGISTRY))
    slug, entry = client.resolve_slug("Django")
    assert slug == "django" and entry is not None
    slug, entry = client.resolve_slug("torch")
    assert slug == "pytorch"
    # unknown name → bare lowercase slug, no registry entry
    slug, entry = client.resolve_slug("SomeRandomPkg")
    assert slug == "somerandompkg" and entry is None


def test_manual_entry_resolves_to_lts_lines(lf):
    client = lf.EolClient(cache_path=Path("/nonexistent/eol_cache.json"),
                          fetcher=lambda s: None, registry=lf.load_lts_registry(_REGISTRY))
    res = client.lts_status("spring-framework", pinned_line="6.1")
    assert res["source"] == "manual"
    assert res["lts_status"] == "lts-supported"       # 6.1 line, eol 2028
    assert res["eol_date"] == "2028-12-31"


def test_heuristic_seed_marks_lts_like(lf):
    client = lf.EolClient(cache_path=Path("/nonexistent/eol_cache.json"),
                          fetcher=lambda s: None, registry=lf.load_lts_registry(_REGISTRY))
    res = client.lts_status("some-backported-lib")
    assert res["lts_status"] == "lts-like"
