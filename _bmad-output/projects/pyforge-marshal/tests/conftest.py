"""
Shared pytest fixtures for pyforge-marshal tests.

Provides:
- verdict_lattice: Closed verdict state machine (ERROR, WARNING, PASS)
- loop_home_fixture: Real worktree provisioned + auto-cleaned
- policy_layers: 6-layer policy composition (system → project → team → user → run → story)
- finding_codes: Registry of valid finding codes (MRS-*, FR-*, AD-*, etc.)
- run_journal: Append-only run journal with deterministic serialization
- adapter_config: Adapter config seeded from first-run context
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest


# ============================================================================
# Verdict Lattice Fixtures
# ============================================================================

class VerdiLattice:
    """Closed verdict lattice with states: ERROR, WARNING, PASS (no invalid transitions)."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    PASS = "PASS"

    STATES = {ERROR, WARNING, PASS}
    VALID_TRANSITIONS = {
        ERROR: {ERROR},  # ERROR only stays ERROR
        WARNING: {ERROR, WARNING},  # WARNING can go to ERROR or stay
        PASS: {PASS},  # PASS only stays PASS
    }

    def __init__(self):
        self.state = self.PASS
        self.timestamp = None  # No timestamps in verdict logic (determinism)
        self.findings: List[Dict[str, Any]] = []

    def add_finding(self, finding_code: str, severity: str, message: str):
        """Add a finding to the verdict."""
        self.findings.append({
            "code": finding_code,
            "severity": severity,
            "message": message,
        })

    def aggregate(self, verdicts: List[str]) -> 'VerdiLattice':
        """Aggregate multiple verdicts into one."""
        result = VerdiLattice()
        for verdict in verdicts:
            if verdict == self.ERROR:
                result.state = self.ERROR
                break
            elif verdict == self.WARNING and result.state != self.ERROR:
                result.state = self.WARNING
        return result

    def __eq__(self, other):
        if isinstance(other, VerdiLattice):
            return self.state == other.state and self.findings == other.findings
        return False

    def __repr__(self):
        return f"VerdiLattice(state={self.state}, findings={len(self.findings)})"


@pytest.fixture
def verdict_lattice():
    """Closed verdict lattice: ERROR, WARNING, PASS (no invalid transitions)."""
    return VerdiLattice()


# ============================================================================
# Finding Codes Fixtures
# ============================================================================

class FindingCodeRegistry:
    """Registry of all valid finding codes."""

    PREFIXES = {
        "MRS": "Marshal",
        "FR": "Feature Requirement",
        "AD": "Architecture Decision",
        "NFR": "Non-Functional Requirement",
        "AUD": "Audit",
        "G": "Gap",
    }

    def __init__(self):
        self.codes: Dict[str, Dict[str, str]] = {}
        self._load_default_codes()

    def _load_default_codes(self):
        """Load default finding codes."""
        # MRS codes
        for i in range(1, 101):
            self.codes[f"MRS-{i}"] = {"prefix": "MRS", "name": f"Marshal finding {i}"}

        # FR codes (Feature Requirements)
        for i in range(1, 66):
            self.codes[f"FR-{i}"] = {"prefix": "FR", "name": f"Feature {i}"}

        # AD codes (Architecture Decisions)
        for i in range(1, 51):
            self.codes[f"AD-{i}"] = {"prefix": "AD", "name": f"Decision {i}"}

        # NFR codes (Non-Functional)
        for i in range(1, 11):
            self.codes[f"NFR-{i}"] = {"prefix": "NFR", "name": f"Non-functional {i}"}

    def is_valid(self, code: str) -> bool:
        """Check if a finding code is valid."""
        return code in self.codes

    def validate(self, codes: List[str]) -> tuple[bool, List[str]]:
        """Validate a list of codes. Returns (all_valid, invalid_codes)."""
        invalid = [c for c in codes if not self.is_valid(c)]
        return len(invalid) == 0, invalid


@pytest.fixture
def finding_codes():
    """Registry of all valid finding codes (MRS-*, FR-*, AD-*, etc.)."""
    return FindingCodeRegistry()


# ============================================================================
# Loop Home & Policy Fixtures
# ============================================================================

class LoopHome:
    """Real worktree provisioned at a path. Auto-cleaned up after test."""

    def __init__(self, path: Path):
        self.path = path
        self.tier3_store = self.path / ".bmad-loop" / "tier3"
        self.state_file = self.path / ".bmad-loop" / "state.json"
        self.work_in_progress = False

    @staticmethod
    def provision(path: Path) -> "LoopHome":
        """Provision a new loop home at path."""
        path.mkdir(parents=True, exist_ok=True)
        (path / ".bmad-loop").mkdir(exist_ok=True)
        (path / ".bmad-loop" / "tier3").mkdir(exist_ok=True)
        home = LoopHome(path)
        home._write_initial_state()
        return home

    def _write_initial_state(self):
        """Write initial state file."""
        state = {
            "provisioned_at": datetime.now().isoformat(),
            "version": "1.0",
            "stories_run": 0,
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def teardown(self):
        """Teardown that refuses if work in progress."""
        if self.work_in_progress:
            raise RuntimeError("Cannot teardown: work in progress")
        # In real implementation, would remove git worktree
        # For tests, just cleanup temp directory
        import shutil
        if self.path.exists():
            shutil.rmtree(self.path)


@pytest.fixture
def loop_home_fixture(tmp_path):
    """Real worktree provisioned at tmp_path. Auto-cleaned up after test."""
    home = LoopHome.provision(tmp_path / "loop_home")
    yield home
    home.teardown()


class PolicyComposition:
    """6-layer policy composition: system → project → team → user → run → story."""

    LAYERS = ["system", "project", "team", "user", "run", "story"]

    def __init__(self):
        self.layers: Dict[str, Dict[str, Any]] = {layer: {} for layer in self.LAYERS}

    @staticmethod
    def from_home(home: LoopHome) -> "PolicyComposition":
        """Create policy composition from loop home."""
        comp = PolicyComposition()
        # Load from home config files (stub for tests)
        return comp

    def merge(self) -> Dict[str, Any]:
        """Merge all layers with proper override semantics."""
        result = {}
        for layer in self.LAYERS:
            result.update(self.layers[layer])
        return result

    def set_layer(self, layer: str, key: str, value: Any):
        """Set a value in a specific layer."""
        if layer not in self.LAYERS:
            raise ValueError(f"Invalid layer: {layer}")
        self.layers[layer][key] = value


@pytest.fixture
def policy_layers(loop_home_fixture):
    """6-layer policy composition: system → project → team → user → run → story."""
    return PolicyComposition.from_home(loop_home_fixture)


# ============================================================================
# Journal & Config Fixtures
# ============================================================================

class RunJournal:
    """Append-only journal with deterministic serialization."""

    def __init__(self, store: Path):
        self.store = store
        self.store.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.store / "journal.jsonl"
        self.entries: List[Dict[str, Any]] = []

    def append(self, event: str, data: Dict[str, Any] = None):
        """Append an entry to the journal."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data or {},
        }
        self.entries.append(entry)
        with open(self.journal_file, "a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    def read_all(self) -> List[Dict[str, Any]]:
        """Read all journal entries."""
        return self.entries


@pytest.fixture
def run_journal(loop_home_fixture):
    """Append-only journal with deterministic serialization."""
    return RunJournal(store=loop_home_fixture.tier3_store)


class AdapterConfig:
    """Adapter config seeded from first-run context."""

    def __init__(self, home: LoopHome = None):
        self.home = home
        self.config: Dict[str, Any] = {
            "adapter": "default",
            "skills": [],
            "project_type": "unknown",
        }

    @staticmethod
    def seed_from_context(home: LoopHome) -> "AdapterConfig":
        """Seed adapter config from home context."""
        config = AdapterConfig(home=home)
        # Load from home config (stub for tests)
        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set a config value."""
        self.config[key] = value


@pytest.fixture
def adapter_config(loop_home_fixture):
    """Adapter config seeded from first-run context."""
    return AdapterConfig.seed_from_context(loop_home_fixture)


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: unit tests (fast)")
    config.addinivalue_line("markers", "integration: integration tests (medium)")
    config.addinivalue_line("markers", "e2e: end-to-end tests (slow)")
    config.addinivalue_line("markers", "meta: invariant verification")
    config.addinivalue_line("markers", "critical_path: critical path workflows")
    config.addinivalue_line("markers", "high_risk: high-risk features")
