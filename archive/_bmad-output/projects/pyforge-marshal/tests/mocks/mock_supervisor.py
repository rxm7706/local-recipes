"""
Mock supervisor for unit tests.

Simulates supervisor attachment, heartbeat, and escalation signals.
"""

from typing import Optional, Callable, Any


class MockSupervisor:
    """Mock supervisor for testing supervised runs."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.attached = False
        self.heartbeat_interval = 5  # seconds
        self.idle_threshold = 60  # seconds
        self.is_idle = False
        self.escalations = []
        self.heartbeat_callback: Optional[Callable] = None

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
        self.escalations.append({
            "type": escalation_type,
            "data": data,
        })
        return True

    def get_escalations(self) -> list:
        """Get all escalations."""
        return self.escalations

    def set_heartbeat_callback(self, callback: Callable):
        """Set callback for heartbeat events."""
        self.heartbeat_callback = callback
