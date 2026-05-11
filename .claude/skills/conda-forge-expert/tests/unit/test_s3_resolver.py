"""Unit tests for `_http.resolve_s3_parquet_urls` and `list_s3_parquet_months`."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_HTTP_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "_http.py"
spec = importlib.util.spec_from_file_location("_http", _HTTP_PATH)
assert spec is not None and spec.loader is not None
_http = importlib.util.module_from_spec(spec)
sys.modules["_http"] = _http
spec.loader.exec_module(_http)


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "S3_PARQUET_BASE_URL",
        "JFROG_API_KEY",
        "JFROG_USERNAME",
        "JFROG_PASSWORD",
        "GITHUB_TOKEN",
        "GH_TOKEN",
    ):
        monkeypatch.delenv(var, raising=False)


# ── resolve_s3_parquet_urls ─────────────────────────────────────────────────

class TestResolveS3ParquetUrls:
    def test_external_no_config_returns_public_default(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_s3_parquet_urls("2026-04")
        assert chain == [
            "https://anaconda-package-data.s3.amazonaws.com/conda/monthly/2026/2026-04.parquet",
        ]

    def test_env_var_takes_precedence(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("S3_PARQUET_BASE_URL", "https://jfrog.example.com/anaconda-package-data")
        chain = _http.resolve_s3_parquet_urls("2026-04")
        assert chain[0] == "https://jfrog.example.com/anaconda-package-data/conda/monthly/2026/2026-04.parquet"
        assert chain[-1] == "https://anaconda-package-data.s3.amazonaws.com/conda/monthly/2026/2026-04.parquet"

    def test_year_derived_from_month(self, monkeypatch):
        _clean_env(monkeypatch)
        chain = _http.resolve_s3_parquet_urls("2024-12")
        assert chain[0].endswith("/conda/monthly/2024/2024-12.parquet")

    def test_trailing_slash_stripped(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("S3_PARQUET_BASE_URL", "https://jfrog.example.com/mirror/")
        chain = _http.resolve_s3_parquet_urls("2026-04")
        assert chain[0] == "https://jfrog.example.com/mirror/conda/monthly/2026/2026-04.parquet"


# ── JFrog header injection via make_request ─────────────────────────────────

class TestJFrogHeaderInjection:
    """The S3 chain reuses `make_request`, so `JFROG_API_KEY` flows through."""

    def test_jfrog_api_key_injected(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("JFROG_API_KEY", "test-token-xyz")
        url = "https://jfrog.example.com/anaconda-package-data/conda/monthly/2026/2026-04.parquet"
        req = _http.make_request(url)
        assert req.headers.get("X-jfrog-art-api") == "test-token-xyz"

    def test_basic_auth_when_user_pass_set(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("JFROG_USERNAME", "alice")
        monkeypatch.setenv("JFROG_PASSWORD", "secret")
        url = "https://jfrog.example.com/mirror/conda/monthly/2026/2026-04.parquet"
        req = _http.make_request(url)
        assert req.headers.get("Authorization", "").startswith("Basic ")


# ── _parse_s3_list_objects_v2 + list_s3_parquet_months ─────────────────────

_FIXTURE_LIST_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Name>anaconda-package-data</Name>
  <Prefix>conda/monthly/</Prefix>
  <KeyCount>5</KeyCount>
  <Contents><Key>conda/monthly/2026/2026-01.parquet</Key></Contents>
  <Contents><Key>conda/monthly/2026/2026-02.parquet</Key></Contents>
  <Contents><Key>conda/monthly/2026/2026-03.parquet</Key></Contents>
  <Contents><Key>conda/monthly/2026/2026-04.parquet</Key></Contents>
  <Contents><Key>conda/monthly/INDEX.txt</Key></Contents>
</ListBucketResult>"""


class TestParseS3ListObjectsV2:
    def test_extracts_yyyy_mm_keys(self):
        months, token = _http._parse_s3_list_objects_v2(_FIXTURE_LIST_XML)
        assert months == ["2026-01", "2026-02", "2026-03", "2026-04"]
        assert token is None

    def test_malformed_xml_returns_none(self):
        months, token = _http._parse_s3_list_objects_v2(b"not xml")
        assert months is None
        assert token is None

    def test_dedupes_and_sorts(self):
        xml = b"""<?xml version="1.0"?>
<ListBucketResult>
  <Contents><Key>conda/monthly/2026/2026-04.parquet</Key></Contents>
  <Contents><Key>conda/monthly/2026/2026-01.parquet</Key></Contents>
  <Contents><Key>conda/monthly/2026/2026-04.parquet</Key></Contents>
</ListBucketResult>"""
        months, token = _http._parse_s3_list_objects_v2(xml)
        assert months == ["2026-01", "2026-04"]
        assert token is None

    def test_truncated_response_returns_token(self):
        xml = b"""<?xml version="1.0"?>
<ListBucketResult>
  <Contents><Key>conda/monthly/2026/2026-01.parquet</Key></Contents>
  <IsTruncated>true</IsTruncated>
  <NextContinuationToken>page2tok</NextContinuationToken>
</ListBucketResult>"""
        months, token = _http._parse_s3_list_objects_v2(xml)
        assert months == ["2026-01"]
        assert token == "page2tok"

    def test_empty_but_valid_returns_empty_list(self):
        xml = b"""<?xml version="1.0"?>
<ListBucketResult><KeyCount>0</KeyCount></ListBucketResult>"""
        months, token = _http._parse_s3_list_objects_v2(xml)
        assert months == []
        assert token is None


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self._body


class TestListS3ParquetMonths:
    def test_returns_parsed_months(self, monkeypatch):
        _clean_env(monkeypatch)

        def fake_open_url(req, timeout):
            assert "list-type=2" in req.full_url
            return _FakeResp(_FIXTURE_LIST_XML)

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        months = _http.list_s3_parquet_months()
        assert months == ["2026-01", "2026-02", "2026-03", "2026-04"]

    def test_uses_env_override_first(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("S3_PARQUET_BASE_URL", "https://jfrog.example.com/mirror")
        seen: list[str] = []

        def fake_open_url(req, timeout):
            seen.append(req.full_url)
            return _FakeResp(_FIXTURE_LIST_XML)

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        _http.list_s3_parquet_months()
        assert seen[0].startswith("https://jfrog.example.com/mirror")

    def test_falls_through_on_error(self, monkeypatch):
        _clean_env(monkeypatch)
        monkeypatch.setenv("S3_PARQUET_BASE_URL", "https://broken.example.com")
        attempts: list[str] = []

        def fake_open_url(req, timeout):
            attempts.append(req.full_url)
            if "broken.example.com" in req.full_url:
                raise OSError("network unreachable")
            return _FakeResp(_FIXTURE_LIST_XML)

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        months = _http.list_s3_parquet_months()
        assert months == ["2026-01", "2026-02", "2026-03", "2026-04"]
        assert len(attempts) == 2
        assert "broken.example.com" in attempts[0]
        assert "anaconda-package-data" in attempts[1]

    def test_pagination_follows_continuation_token(self, monkeypatch):
        _clean_env(monkeypatch)
        page1 = b"""<?xml version="1.0"?>
<ListBucketResult>
  <Contents><Key>conda/monthly/2026/2026-01.parquet</Key></Contents>
  <IsTruncated>true</IsTruncated>
  <NextContinuationToken>tok2</NextContinuationToken>
</ListBucketResult>"""
        page2 = b"""<?xml version="1.0"?>
<ListBucketResult>
  <Contents><Key>conda/monthly/2026/2026-02.parquet</Key></Contents>
</ListBucketResult>"""
        urls_seen: list[str] = []

        def fake_open_url(req, timeout):
            urls_seen.append(req.full_url)
            return _FakeResp(page2 if "continuation-token=" in req.full_url else page1)

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        months = _http.list_s3_parquet_months()
        assert months == ["2026-01", "2026-02"]
        assert len(urls_seen) == 2
        assert "continuation-token=tok2" in urls_seen[1]

    def test_empty_but_valid_does_not_fall_through(self, monkeypatch):
        _clean_env(monkeypatch)
        empty = b"""<?xml version="1.0"?>
<ListBucketResult><KeyCount>0</KeyCount></ListBucketResult>"""
        attempts: list[str] = []

        def fake_open_url(req, timeout):
            attempts.append(req.full_url)
            return _FakeResp(empty)

        monkeypatch.setattr(_http, "open_url", fake_open_url)
        months = _http.list_s3_parquet_months()
        assert months == []
        assert len(attempts) == 1


class TestResolveS3ParquetUrlsValidation:
    def test_invalid_month_raises(self):
        for bad in ["2026-13", "26-04", "2026", "2026-04-01", "", "2026/04", "abcd-ef"]:
            with pytest.raises(ValueError, match="invalid month"):
                _http.resolve_s3_parquet_urls(bad)

    def test_valid_month_accepted(self):
        urls = _http.resolve_s3_parquet_urls("2026-04")
        assert all(u.endswith("/conda/monthly/2026/2026-04.parquet") for u in urls)
