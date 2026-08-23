"""DB-factory mock family.

Seeded from Marshal's ``archive/.../tests/mocks/mock_supervisor.py``
(MockSupervisor — stateful run factory) and the LoopHome / RunJournal factory
patterns in Marshal's archived ``tests/conftest.py``. Not rewritten from
scratch: the store factories preserve the original provision/teardown shape.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional


class MockSupervisor:
    """Mock supervisor for testing supervised runs (seeded from Marshal).

    Acts as a stateful run-factory: attach/detach, heartbeat, idle detect,
    and escalation recording without a real supervisor process.
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.attached = False
        self.heartbeat_interval = 5  # seconds
        self.idle_threshold = 60  # seconds
        self.is_idle = False
        self.escalations: list[dict[str, Any]] = []
        self.heartbeat_callback: Optional[Callable[..., Any]] = None

    def attach(self) -> bool:
        """Simulate supervisor attachment."""
        self.attached = True
        return True

    def detach(self) -> bool:
        """Simulate supervisor detachment."""
        self.attached = False
        return True

    def send_heartbeat(self) -> bool:
        """Send heartbeat signal."""
        if not self.attached:
            return False
        if self.heartbeat_callback:
            self.heartbeat_callback()
        return True

    def detect_idle(self, idle_time: int) -> bool:
        """Detect if run is idle."""
        self.is_idle = idle_time >= self.idle_threshold
        return self.is_idle

    def escalate(self, escalation_type: str, data: Any = None) -> bool:
        """Send escalation signal."""
        if not self.attached:
            return False
        self.escalations.append(
            {
                "type": escalation_type,
                "data": data,
            }
        )
        return True

    def get_escalations(self) -> list[dict[str, Any]]:
        """Get all escalations."""
        return self.escalations

    def set_heartbeat_callback(self, callback: Callable[..., Any]) -> None:
        """Set callback for heartbeat events."""
        self.heartbeat_callback = callback


# Family-facing alias: stations that want a "run-state factory" name.
RunStateFactory = MockSupervisor


class LoopHome:
    """Real worktree provisioned at a path. Auto-cleaned up after test.

    Seeded from Marshal's archived ``tests/conftest.py`` LoopHome factory.
    """

    def __init__(self, path: Path):
        self.path = path
        self.tier3_store = self.path / ".bmad-loop" / "tier3"
        self.state_file = self.path / ".bmad-loop" / "state.json"
        self.work_in_progress = False

    @staticmethod
    def provision(path: Path) -> LoopHome:
        """Provision a new loop home at path."""
        path.mkdir(parents=True, exist_ok=True)
        (path / ".bmad-loop").mkdir(exist_ok=True)
        (path / ".bmad-loop" / "tier3").mkdir(exist_ok=True)
        home = LoopHome(path)
        home._write_initial_state()
        return home

    def _write_initial_state(self) -> None:
        """Write initial state file."""
        state = {
            "provisioned_at": datetime.now().isoformat(),
            "version": "1.0",
            "stories_run": 0,
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def teardown(self) -> None:
        """Teardown that refuses if work in progress."""
        if self.work_in_progress:
            raise RuntimeError("Cannot teardown: work in progress")
        if self.path.exists():
            shutil.rmtree(self.path)


class RunJournal:
    """Append-only journal with deterministic serialization.

    Seeded from Marshal's archived ``tests/conftest.py`` RunJournal factory.
    """

    def __init__(self, store: Path):
        self.store = store
        self.store.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.store / "journal.jsonl"
        self.entries: list[dict[str, Any]] = []

    def append(self, event: str, data: dict[str, Any] | None = None) -> None:
        """Append an entry to the journal."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data or {},
        }
        self.entries.append(entry)
        with open(self.journal_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        """Read all journal entries."""
        return self.entries


def record_factory(**fields: Any) -> dict[str, Any]:
    """Build a plain test record (progress / claim / notice shaped dict).

    Seeded from the finding-dict shape used across Marshal's mock helpers
    (``code`` / ``severity`` / ``message``) plus optional extra fields.
    """
    record: dict[str, Any] = {
        "code": fields.pop("code", "TEST-000"),
        "severity": fields.pop("severity", "info"),
        "message": fields.pop("message", ""),
    }
    record.update(fields)
    return record
