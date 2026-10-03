"""Ports for operator-run model-list refresh (Story 84.1, AD-20)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CommandRunResult:
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class HttpGetResult:
    status_code: int
    body: bytes


class ModelListFetchPort(Protocol):
    def run_command(
        self,
        argv: Sequence[str],
        *,
        timeout_s: float,
        fallback_bin_dirs: Sequence[str] = (),
    ) -> CommandRunResult: ...

    def http_get(self, url: str, headers: Mapping[str, str], *, timeout_s: float) -> HttpGetResult: ...
