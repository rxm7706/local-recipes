"""Tests for the sentinel knowledge base, config resolution, and sync timeout recovery (FR-22, AD-22)."""

from __future__ import annotations

import json
from pathlib import Path
import httpx
import pytest

from sentinel.knowledge.config import KnowledgeConfig
from sentinel.knowledge.lasuite.client import LaSuiteClient
from sentinel.knowledge.lasuite.sync import WikiSyncer


def test_knowledge_config_from_env(monkeypatch):
    monkeypatch.setenv("LASUITE_BASE_URL", "https://test-cms.example/")
    monkeypatch.setenv("LASUITE_API_TOKEN", "super-secret-token")
    monkeypatch.setenv("WIKI_COMPILED_DIR", "mock_compiled")
    monkeypatch.setenv("WIKI_RAW_DIR", "mock_raw")

    config = KnowledgeConfig.from_env()
    assert config.lasuite_url == "https://test-cms.example/"
    assert config.lasuite_api_token == "super-secret-token"
    assert config.compiled_dir == "mock_compiled"
    assert config.raw_dir == "mock_raw"


def test_lasuite_client_timeout_propagation():
    client = LaSuiteClient("https://test-cms.example", "token", timeout=2.5)
    assert client.timeout == 2.5


def test_wiki_syncer_successful_push(tmp_path, monkeypatch):
    # Setup mock wiki directory structure
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir(parents=True)
    
    doc1 = compiled_dir / "article1.md"
    doc1.write_text("# Article 1\nContent of article 1", encoding="utf-8")

    # Mock client endpoints
    created = []
    class MockClient:
        def create_document(self, title, content):
            created.append((title, content))
            return {"id": "doc-123"}

    client = MockClient()
    
    # Force mapping file path to be in tmp_path to prevent writing to repo root
    mapping_file = tmp_path / ".lasuite_ids.json"
    monkeypatch.setattr(WikiSyncer, "MAPPING_FILE", mapping_file)

    syncer = WikiSyncer(client)
    res = syncer.sync_all(compiled_dir)

    assert res["synced"] == ["article1.md"]
    assert res["failed"] == []
    assert len(created) == 1
    assert created[0] == ("Article 1", "# Article 1\nContent of article 1")
    assert syncer.mapping[str(doc1)] == "doc-123"
    assert mapping_file.is_file()


def test_wiki_syncer_graceful_timeout_recovery(tmp_path, monkeypatch):
    # Setup two markdown files
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir(parents=True)
    
    doc_timeout = compiled_dir / "timeout.md"
    doc_timeout.write_text("# Timeout doc\nBody that triggers timeout", encoding="utf-8")
    
    doc_success = compiled_dir / "success.md"
    doc_success.write_text("# Success doc\nBody that succeeds", encoding="utf-8")

    # Mock client that times out on timeout.md but succeeds on success.md
    class TimeoutMockClient:
        def create_document(self, title, content):
            if "Timeout doc" in title:
                raise httpx.ConnectTimeout("Connection timed out to La Suite API")
            return {"id": "success-id"}

    client = TimeoutMockClient()
    
    # Mock mapping file to tmp directory
    mapping_file = tmp_path / ".lasuite_ids.json"
    monkeypatch.setattr(WikiSyncer, "MAPPING_FILE", mapping_file)

    syncer = WikiSyncer(client)
    res = syncer.sync_all(compiled_dir)

    # Assert that timeout.md failed, but success.md was successfully synced
    assert "timeout.md" in res["failed"]
    assert "success.md" in res["synced"]
    
    # syncer must not abort, mapping contains only success.md
    assert str(doc_success) in syncer.mapping
    assert syncer.mapping[str(doc_success)] == "success-id"
    assert str(doc_timeout) not in syncer.mapping
