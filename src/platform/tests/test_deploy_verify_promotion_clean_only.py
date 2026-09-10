"""Story 12.1 — regression guard for the deploy promotion verifier's clean-only gate.

Exercises ``scripts/platform-deploy-verify-promotion.py`` via subprocess with
synthetic promotion JSON — the same env vars and script path
``.github/workflows/platform-deploy.yml`` uses. Behavioral proofs only: if the
``!= \"clean\"`` refusal is deleted, weakened to a truthiness check, or turned
into a log-only warning, these tests fail without reading the script source.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VERIFY_SCRIPT = _REPO_ROOT / "scripts" / "platform-deploy-verify-promotion.py"
_DIGEST = "sha256:" + ("a" * 64)
_DRIVER_ID = "warden:vulnerability:CVE-2024-0001"


def _promotion_payload(
    *,
    warden_status: str | None = None,
    nested_status: str | None = None,
    driver_id: str = _DRIVER_ID,
    include_warden: bool = True,
    include_nested_status: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "images": {
            "platform": {"digest": _DIGEST},
            "sidecar": {"digest": _DIGEST},
            "mcpHost": {"digest": _DIGEST},
        },
    }
    if warden_status is not None:
        payload["warden_status"] = warden_status
    if include_warden:
        warden: dict[str, Any] = {}
        if include_nested_status:
            status_value = nested_status if nested_status is not None else warden_status
            warden["status"] = {
                "value": status_value or "indeterminate",
                "driver": {"finding_id": driver_id},
            }
        payload["warden"] = warden
    return payload


def _assert_refused(result: subprocess.CompletedProcess[str], *, status: str) -> None:
    assert result.returncode != 0
    assert status in result.stderr
    assert _DRIVER_ID in result.stderr
    assert "does not promote" in result.stderr
    assert result.stderr.startswith("::error::")


def _run_verifier(
    payload: dict[str, Any],
    tmp_path: Path,
) -> subprocess.CompletedProcess[str]:
    promo_file = tmp_path / "golden-path-promotion.json"
    promo_file.write_text(json.dumps(payload), encoding="utf-8")
    env = {
        **os.environ,
        "PROMOTION_JSON": str(promo_file),
        "PLATFORM_DIGEST": _DIGEST,
        "SIDECAR_DIGEST": _DIGEST,
        "MCP_HOST_DIGEST": _DIGEST,
    }
    return subprocess.run(  # noqa: S603 -- fixed argv, no shell, repo script under test
        [sys.executable, str(_VERIFY_SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_clean_verdict_is_accepted(tmp_path: Path) -> None:
    result = _run_verifier(
        _promotion_payload(warden_status="clean", nested_status="clean"),
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "clean Warden verdict" in result.stdout


@pytest.mark.parametrize(
    "warden_status",
    ["indeterminate", "warn", "error", "policy-violation"],
)
def test_non_clean_top_level_status_is_refused(
    tmp_path: Path,
    warden_status: str,
) -> None:
    result = _run_verifier(
        _promotion_payload(warden_status=warden_status, nested_status=warden_status),
        tmp_path,
    )
    _assert_refused(result, status=warden_status)


@pytest.mark.parametrize(
    "nested_status",
    ["indeterminate", "warn", "error", "policy-violation"],
)
def test_non_clean_nested_status_is_refused_when_top_level_absent(
    tmp_path: Path,
    nested_status: str,
) -> None:
    result = _run_verifier(
        _promotion_payload(warden_status=None, nested_status=nested_status),
        tmp_path,
    )
    _assert_refused(result, status=nested_status)


def test_top_level_status_wins_over_conflicting_nested_clean(tmp_path: Path) -> None:
    result = _run_verifier(
        _promotion_payload(warden_status="error", nested_status="clean"),
        tmp_path,
    )
    _assert_refused(result, status="error")


def test_missing_resolved_status_is_refused(tmp_path: Path) -> None:
    result = _run_verifier(
        _promotion_payload(
            warden_status=None,
            include_nested_status=False,
        ),
        tmp_path,
    )
    assert result.returncode != 0
    assert "None" in result.stderr
    assert "does not promote" in result.stderr
    assert result.stderr.startswith("::error::")


def test_missing_warden_object_is_refused(tmp_path: Path) -> None:
    result = _run_verifier(
        _promotion_payload(warden_status="clean", include_warden=False),
        tmp_path,
    )
    assert result.returncode != 0
    assert "no Warden verdict object" in result.stderr
    assert result.stderr.startswith("::error::")
