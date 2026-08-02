"""
Shared pytest fixtures for tests.
Template — expand with station-specific fixtures as stories are defined.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest


@pytest.fixture
def tmp_project_dir(tmp_path):
    """Temporary project directory for testing."""
    return tmp_path / "project"


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "metadata": {},
    }


@pytest.fixture
def sample_findings():
    """Sample findings list for testing."""
    return [
        {
            "code": "FR-1",
            "severity": "ERROR",
            "message": "Sample finding 1",
        },
        {
            "code": "FR-2",
            "severity": "WARNING",
            "message": "Sample finding 2",
        },
    ]


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: unit tests (fast)")
    config.addinivalue_line("markers", "integration: integration tests (medium)")
    config.addinivalue_line("markers", "e2e: end-to-end tests (slow)")
    config.addinivalue_line("markers", "meta: invariant verification")
    config.addinivalue_line("markers", "critical_path: critical path workflows")
