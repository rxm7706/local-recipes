"""Unit tests for ``pyforge.doctor.checks.env_hygiene`` (Story 1.4, FR-3) --
covers the story spec's I/O & Edge-Case Matrix: the direct positive case,
the real ``_http.py`` golden fixture, the host-scoped negative case, the
no-match empty-tuple case, and ``gather_one``'s filter-equivalence."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.checks import env_hygiene
from pyforge.doctor.checks.env_hygiene import CHECK_NAME, gather
from pyforge.doctor.checks.registry import gather_one
from pyforge.doctor.models import DoctorStatus, Finding, Source

# Six levels up from tests/unit/<this file> lands at the monorepo root --
# mirrors pyforge-warden's tests/unit/test_currency.py::
# test_bundled_registry_matches_the_cfe_canonical_source_when_present.
_REPO_ROOT = Path(__file__).resolve().parents[6]
_HTTP_PY_DIR = (
    _REPO_ROOT / ".claude" / "skills" / "conda-forge-expert" / "scripts"
)


def _write(tmp_path: Path, name: str, source: str) -> None:
    (tmp_path / name).write_text(source, encoding="utf-8")


# --- gather -------------------------------------------------------------


def test_gather_returns_empty_tuple_for_a_file_with_no_matching_pattern(
    tmp_path: Path,
):
    _write(tmp_path, "benign.py", "x = 1\ny = {'a': 1}\n")
    assert gather(tmp_path) == ()


def test_gather_direct_unconditional_injection_returns_one_warn_finding(
    tmp_path: Path,
):
    _write(
        tmp_path,
        "direct.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    if os.environ.get("X"):\n'
        '        headers["Y"] = os.environ["X"]\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    finding = result[0]
    assert isinstance(finding, Finding)
    assert finding.source is Source.ENV_HYGIENE
    assert finding.check == CHECK_NAME
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["line"] == 5
    assert finding.evidence["var_name"] == "X"
    assert finding.evidence["file"] == str(tmp_path / "direct.py")


def test_gather_host_scoped_guard_suppresses_the_finding(tmp_path: Path):
    _write(
        tmp_path,
        "guarded.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    if host == "internal.example.com":\n'
        '        headers["Authorization"] = os.environ.get("T")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_else_branch_of_a_host_scoped_if_is_still_flagged(
    tmp_path: Path,
):
    # Review finding: the host guard on the TRUE branch must not leak into
    # the else/failed-elif branch, where the test being FALSE is exactly
    # the "not this host" case the check exists to catch.
    _write(
        tmp_path,
        "else_branch.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    if host == "safe.example.com":\n'
        "        pass\n"
        "    else:\n"
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"
    assert result[0].evidence["line"] == 7


def test_gather_substring_host_token_does_not_falsely_suppress(
    tmp_path: Path,
):
    # Review finding: "ghost_mode" contains the substring "host" but is not
    # a host-scoping guard -- token-exact matching must not treat it as one.
    _write(
        tmp_path,
        "ghost.py",
        "import os\n"
        "\n"
        "def handler(ghost_mode):\n"
        "    if ghost_mode:\n"
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_env_var_used_only_as_ternary_condition_is_not_flagged(
    tmp_path: Path,
):
    # Review finding: an env-read that decides BETWEEN two unrelated
    # values (never itself becoming the header value) is not "fed" into
    # the assignment.
    _write(
        tmp_path,
        "ternary_condition.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Content-Type"] = (\n'
        '        "application/json" if os.environ.get("DEBUG") else "text/plain"\n'
        "    )\n",
    )

    assert gather(tmp_path) == ()


def test_gather_env_var_as_ternary_value_is_still_flagged(tmp_path: Path):
    # Complement of the above: when the env-read IS one of the ternary's
    # own value branches, it genuinely feeds the header and must be
    # flagged.
    _write(
        tmp_path,
        "ternary_value.py",
        "import os\n"
        "\n"
        "def handler(flag):\n"
        '    headers["Authorization"] = (\n'
        '        os.environ.get("TOKEN") if flag else "default"\n'
        "    )\n",
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_aliased_os_import_is_still_detected(tmp_path: Path):
    # Review finding: `import os as o` previously evaded the scanner
    # entirely (hard-coded literal name "os").
    _write(
        tmp_path,
        "aliased_os.py",
        "import os as o\n"
        "\n"
        "def handler():\n"
        '    if o.environ.get("X"):\n'
        '        headers["Y"] = o.environ["X"]\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "X"


def test_gather_from_os_import_environ_is_still_detected(tmp_path: Path):
    # Review finding: `from os import environ` previously evaded the
    # scanner entirely.
    _write(
        tmp_path,
        "from_import.py",
        "from os import environ\n"
        "\n"
        "def handler():\n"
        '    if environ.get("X"):\n'
        '        headers["Y"] = environ["X"]\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "X"


def test_gather_aug_assign_credential_injection_is_detected(tmp_path: Path):
    # Review finding: `headers["X"] += ...` (AugAssign) was previously
    # invisible -- only plain Assign was visited.
    _write(
        tmp_path,
        "aug_assign.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Authorization"] = ""\n'
        '    headers["Authorization"] += os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"
    assert result[0].evidence["line"] == 5


def test_gather_chained_assignment_with_a_header_target_is_detected(
    tmp_path: Path,
):
    # Review finding: `headers["X"] = other["Y"] = env-read` previously
    # required exactly one target.
    _write(
        tmp_path,
        "chained.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    other["Y"] = headers["X"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_golden_fixture_finds_the_real_jfrog_api_key_injection():
    # The real, unmodified _http.py::auth_headers_for -- read-only, never
    # copied into a synthetic string (spec's context-file instruction).
    if not _HTTP_PY_DIR.is_dir():
        pytest.skip(
            "CFE _http.py golden fixture not present (non-monorepo context)"
        )

    result = gather(_HTTP_PY_DIR)

    jfrog_finding = next(
        (f for f in result if f.evidence.get("var_name") == "JFROG_API_KEY"),
        None,
    )
    assert jfrog_finding is not None, (
        "expected a JFROG_API_KEY finding scanning the real _http.py -- "
        f"got {[f.evidence for f in result]}"
    )
    assert jfrog_finding.status is DoctorStatus.WARN
    assert jfrog_finding.evidence["file"].endswith("_http.py")

    # Self-verifying against line drift: the reported line must actually
    # be the JFROG_API_KEY assignment in the live file, not a stale/wrong
    # lineno.
    http_py = Path(jfrog_finding.evidence["file"])
    reported_line = http_py.read_text(encoding="utf-8").splitlines()[
        jfrog_finding.evidence["line"] - 1
    ]
    assert "JFROG_API_KEY" in reported_line


# --- gather_one filter-equivalence ---------------------------------------


def test_gather_one_env_matches_the_filtered_gather_result(tmp_path: Path):
    _write(
        tmp_path,
        "direct.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    if os.environ.get("X"):\n'
        '        headers["Y"] = os.environ["X"]\n',
    )

    expected = next(f for f in gather(tmp_path) if f.check == CHECK_NAME)

    assert gather_one("env", CHECK_NAME, tmp_path) == expected


def test_gather_one_env_returns_none_for_a_target_with_no_matches(
    tmp_path: Path,
):
    _write(tmp_path, "benign.py", "x = 1\n")

    assert gather_one("env", CHECK_NAME, tmp_path) is None


# --- discovery-walk incompleteness signal --------------------------------


def test_discover_python_files_onerror_marks_incomplete(
    monkeypatch, tmp_path: Path
):
    # Review finding: an unreadable subdirectory previously vanished from
    # the scan with zero signal (os.walk's default onerror=None silently
    # drops it). Drives the walk through a fake os.walk so this is
    # portable -- real filesystem permission tests are environment-
    # fragile (e.g. root bypasses permissions).
    def _fake_walk(_target, onerror=None, **_kwargs):
        onerror(OSError("simulated permission denied"))
        return iter(())

    monkeypatch.setattr(env_hygiene.os, "walk", _fake_walk)

    files, incomplete = env_hygiene._discover_python_files(tmp_path)

    assert files == []
    assert incomplete is True


def test_discover_python_files_entry_cap_marks_incomplete(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr(env_hygiene, "_DISCOVERY_ENTRY_CAP", 2)
    for i in range(5):
        _write(tmp_path, f"f{i}.py", "x = 1\n")

    _files, incomplete = env_hygiene._discover_python_files(tmp_path)

    assert incomplete is True


def test_gather_appends_one_warn_finding_when_scan_is_incomplete(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr(env_hygiene, "_DISCOVERY_ENTRY_CAP", 1)
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, "b.py", "y = 2\n")

    result = gather(tmp_path)

    incomplete_findings = [f for f in result if "INCOMPLETE" in f.message]
    assert len(incomplete_findings) == 1
    assert incomplete_findings[0].status is DoctorStatus.WARN
    assert incomplete_findings[0].check == CHECK_NAME


def test_gather_no_incomplete_finding_when_scan_completes_normally(
    tmp_path: Path,
):
    _write(tmp_path, "benign.py", "x = 1\n")

    result = gather(tmp_path)

    assert not any("INCOMPLETE" in f.message for f in result)
