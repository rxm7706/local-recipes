"""Unit tests for ``pyforge.doctor.checks.env_hygiene`` (Story 1.4, FR-3) --
covers the story spec's I/O & Edge-Case Matrix: the direct positive case,
the real ``_http.py`` golden fixture, the host-scoped negative case, the
no-match empty-tuple case, and ``gather_one``'s filter-equivalence."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.checks import env_hygiene
from pyforge.doctor.checks.env_hygiene import (
    CHECK_NAME,
    SCAN_INCOMPLETE_CHECK_NAME,
    gather,
)
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
    # Review finding: the sentinel's check name is deliberately DISTINCT
    # from CHECK_NAME (and never cataloged), mirroring sources/warden.py's
    # "pyforge-warden" degradation sentinel -- reusing CHECK_NAME let
    # gather_one conflate the incompleteness signal with a real match.
    assert incomplete_findings[0].check == SCAN_INCOMPLETE_CHECK_NAME
    assert incomplete_findings[0].check != CHECK_NAME


def test_gather_no_incomplete_finding_when_scan_completes_normally(
    tmp_path: Path,
):
    _write(tmp_path, "benign.py", "x = 1\n")

    result = gather(tmp_path)

    assert not any("INCOMPLETE" in f.message for f in result)


def test_gather_one_env_can_address_the_incomplete_sentinel_by_name(
    monkeypatch, tmp_path: Path
):
    # Mirrors engines' addressable-sentinel contract: the sentinel's own
    # (never-cataloged) name IS reachable through gather_one's filter,
    # and a real CHECK_NAME finding is returned unshadowed alongside it.
    monkeypatch.setattr(env_hygiene, "_DISCOVERY_ENTRY_CAP", 1)
    _write(
        tmp_path,
        "a_direct.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Y"] = os.environ["X"]\n',
    )
    _write(tmp_path, "b.py", "y = 2\n")

    sentinel = gather_one(
        "env", SCAN_INCOMPLETE_CHECK_NAME, tmp_path
    )

    assert sentinel is not None
    assert "INCOMPLETE" in sentinel.message
    # a_direct.py sorts first and is collected before the cap trips, so
    # the real finding coexists with the sentinel -- and neither shadows
    # the other under the name filter.
    real = gather_one("env", CHECK_NAME, tmp_path)
    assert real is not None
    assert real.check == CHECK_NAME
    assert "INCOMPLETE" not in real.message


def test_gather_on_a_single_file_target_returns_empty_tuple(tmp_path: Path):
    # Review finding: after the onerror patch, a non-directory target fed
    # os.walk's top-level scandir error into onerror, emitting a misleading
    # "could not read some subdirectory" sentinel -- the established
    # registry convention for a non-directory target is silent ().
    file_target = tmp_path / "single.py"
    file_target.write_text(
        'import os\nheaders["Y"] = os.environ["X"]\n', encoding="utf-8"
    )

    assert gather(file_target) == ()


def test_gather_on_a_nonexistent_target_returns_empty_tuple(tmp_path: Path):
    assert gather(tmp_path / "does-not-exist") == ()


# --- degrade-never-crash on pathological-but-parseable input --------------


def test_gather_skips_a_file_whose_ast_blows_the_recursion_limit(
    tmp_path: Path,
):
    # Review finding: a parseable file with a pathologically deep
    # expression tree (e.g. a machine-generated multi-thousand-term
    # concatenation) raised RecursionError out of the visitor walk,
    # crashing the whole doctor run -- the analysis now lives inside the
    # same degrade-never-crash net as parsing.
    deep = "headers['X'] = " + "'a' + " * 5000 + "'a'\n"
    _write(tmp_path, "deep.py", deep)
    _write(
        tmp_path,
        "normal.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Y"] = os.environ["X"]\n',
    )

    result = gather(tmp_path)  # must not raise

    # The pathological file is skipped; the scan still reports the
    # ordinary file's real finding.
    assert [f.evidence["var_name"] for f in result] == ["X"]


# --- guard polarity (negated host tests) ----------------------------------


def test_gather_negated_host_guard_true_branch_is_still_flagged(
    tmp_path: Path,
):
    # Review finding: `if host != safe: headers[...] = env` -- the exact
    # inverse-condition leak -- was suppressed because the test merely
    # REFERENCES a host-like name; a pure-negation test's TRUE branch is
    # the "not this host" case and must not inherit the guard.
    _write(
        tmp_path,
        "negated.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    if host != "internal.example.com":\n'
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_negated_host_guard_else_branch_is_suppressed(
    tmp_path: Path,
):
    # Complement: the else branch of `if host != safe:` runs precisely
    # when host == safe -- that assignment IS host-scoped.
    _write(
        tmp_path,
        "negated_else.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    if host != "internal.example.com":\n'
        "        pass\n"
        "    else:\n"
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_not_in_host_guard_true_branch_is_still_flagged(
    tmp_path: Path,
):
    _write(
        tmp_path,
        "not_in.py",
        "import os\n"
        "\n"
        "def handler(host, allowed_hosts):\n"
        "    if host not in allowed_hosts:\n"
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1


def test_gather_camel_case_host_guard_suppresses(tmp_path: Path):
    # Review finding: token-splitting on "_" alone missed camelCase host
    # guards like `serverHost`.
    _write(
        tmp_path,
        "camel.py",
        "import os\n"
        "\n"
        "def handler(serverHost):\n"
        '    if serverHost == "internal.example.com":\n'
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_elif_host_guard_suppresses(tmp_path: Path):
    # elif branches are nested If nodes in orelse -- the elif's own test
    # must guard its own body (module-docstring contract, previously
    # untested).
    _write(
        tmp_path,
        "elif_guard.py",
        "import os\n"
        "\n"
        "def handler(debug, host):\n"
        "    if debug:\n"
        "        pass\n"
        '    elif host == "internal.example.com":\n'
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_outer_function_host_guard_does_not_leak_into_nested_def(
    tmp_path: Path,
):
    # The guard stack resets at function boundaries (module-docstring
    # contract, previously untested): a host guard around a nested `def`
    # does not scope the assignments inside that def.
    _write(
        tmp_path,
        "nested_def.py",
        "import os\n"
        "\n"
        "def outer(host):\n"
        '    if host == "internal.example.com":\n'
        "        def attach():\n"
        '            headers["Authorization"] = os.environ.get("TOKEN")\n'
        "        return attach\n",
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


# --- env-read shapes (previously untested or invisible) -------------------


def test_gather_os_getenv_call_is_detected(tmp_path: Path):
    # The os.getenv path existed but had zero coverage (review finding).
    _write(
        tmp_path,
        "getenv.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Authorization"] = os.getenv("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_from_os_import_getenv_is_detected(tmp_path: Path):
    _write(
        tmp_path,
        "from_getenv.py",
        "from os import getenv\n"
        "\n"
        "def handler():\n"
        '    headers["Authorization"] = getenv("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_star_import_environ_is_detected(tmp_path: Path):
    # Review finding: `from os import *` binds environ/getenv under their
    # own names and previously evaded the scanner entirely.
    _write(
        tmp_path,
        "star.py",
        "from os import *\n"
        "\n"
        "def handler():\n"
        '    headers["Authorization"] = environ["TOKEN"]\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_ann_assign_credential_injection_is_detected(tmp_path: Path):
    # Review finding: `headers["X"]: str = env-read` (AnnAssign) is legal
    # Python and was previously invisible.
    _write(
        tmp_path,
        "ann_assign.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Authorization"]: str = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_tuple_unpacking_header_target_is_detected(tmp_path: Path):
    # Review finding: `headers["A"], x = env-read, 1` was invisible --
    # only top-level targets were inspected.
    _write(
        tmp_path,
        "tuple_target.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Authorization"], x = os.environ.get("TOKEN"), 1\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_tuple_unpacking_pairs_positionally_no_false_positive(
    tmp_path: Path,
):
    # The positional complement: the env-read feeds x, not the header
    # element, so no finding.
    _write(
        tmp_path,
        "tuple_positional.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Content-Type"], x = "text/plain", os.environ.get("D")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_walrus_in_ternary_test_is_still_detected(tmp_path: Path):
    # Review finding: a walrus inside the (otherwise skipped) ternary test
    # BINDS the env value into the returned branch -- value-carrying.
    _write(
        tmp_path,
        "walrus.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Authorization"] = (\n'
        '        t if (t := os.environ.get("TOKEN")) else "default"\n'
        "    )\n",
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_env_read_in_comprehension_filter_is_not_flagged(
    tmp_path: Path,
):
    # Review finding: a comprehension's `if` filter decides WHICH values
    # are included -- same non-value-carrying rationale as a ternary's
    # test (previously a false positive with a misleading message).
    _write(
        tmp_path,
        "comp_filter.py",
        "import os\n"
        "\n"
        "def handler(values):\n"
        '    headers["Accept"] = ",".join(\n'
        '        v for v in values if os.environ.get("DEBUG")\n'
        "    )\n",
    )

    assert gather(tmp_path) == ()


def test_gather_env_read_in_comprehension_iter_is_still_flagged(
    tmp_path: Path,
):
    # Complement: the iterated source genuinely feeds the produced values.
    _write(
        tmp_path,
        "comp_iter.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Accept"] = ",".join(\n'
        '        c for c in os.environ.get("ACCEPT", "")\n'
        "    )\n",
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "ACCEPT"
