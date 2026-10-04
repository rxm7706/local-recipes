"""The live-scan submit path: refused / failed / ok, and the two normalizers.

Story 27.3, closing DW-FU-20-5-2 / DW-FU-20-5-9. The process is driven through an
injected :class:`pyforge.core.process.ProcessPort` fake, so these cases run with
no pixi env, no CLI and no network — the seam exists exactly so this is possible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.atlas.dashboard import scan_submit as ss


@dataclass
class FakeProcess:
    """A ``ProcessPort`` that replays queued results and records every argv."""

    results: list[ProcessResult | ProcessError]
    calls: list[list[str]] = field(default_factory=list)

    def run(self, argv: Sequence[str], *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        self.calls.append(list(argv))
        outcome = self.results.pop(0)
        if isinstance(outcome, ProcessError):
            raise outcome
        return outcome


def _ok(payload: Any) -> ProcessResult:
    return ProcessResult(returncode=0, stdout=json.dumps(payload), stderr="")


SCAN_PROJECT_PAYLOAD = {
    "deps": [{"name": "numpy"}, {"name": "requests"}, {"name": "tidy"}],
    "vulns_by_dep": {
        "conda:numpy@1.26.0": [
            {"severity": "High", "fixed_version": "1.26.4"},
            {"severity": "High"},
            {"severity": "Low"},
        ],
        "conda:requests@2.31.0": [{"id": "GHSA-x"}],
    },
    "atlas_records": {"conda:numpy@1.26.0": {"license_spdx": "BSD-3-Clause"}},
}


# --------------------------------------------------------------------------- #
# Refusals — nothing is ever started
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("page_id", "path_value", "fragment"),
    [
        ("staleness-report", ".", "not a live-scan page"),
        ("scan-project", "", "Enter a path"),
        ("scan-project", "   ", "Enter a path"),
        ("scan-project", None, "Enter a path"),
    ],
)
def test_a_bad_submit_is_refused_before_any_process_runs(page_id, path_value, fragment, tmp_path) -> None:
    process = FakeProcess(results=[])
    submission = ss.submit_scan(page_id, path_value, data_root=tmp_path, process=process)
    assert submission.status == "refused"
    assert fragment in submission.message
    assert submission.frame is None
    assert process.calls == []


def test_a_path_that_does_not_exist_is_refused_and_says_so(tmp_path) -> None:
    process = FakeProcess(results=[])
    submission = ss.submit_scan("scan-project", str(tmp_path / "absent"), data_root=tmp_path, process=process)
    assert submission.status == "refused"
    assert "does not exist on this host" in submission.message
    assert process.calls == []


# --------------------------------------------------------------------------- #
# Failures — the previous cached result survives
# --------------------------------------------------------------------------- #


def test_a_non_zero_exit_fails_and_names_the_exit_code(tmp_path) -> None:
    process = FakeProcess(results=[ProcessResult(returncode=2, stdout="", stderr="boom: no lockfile\n")])
    submission = ss.submit_scan("scan-project", str(tmp_path), data_root=tmp_path, process=process)
    assert submission.status == "failed"
    assert "exited 2" in submission.message
    assert "boom: no lockfile" in submission.message
    assert submission.frame is None


def test_an_unlaunchable_command_fails_rather_than_raising(tmp_path) -> None:
    process = FakeProcess(results=[ProcessError("pixi: not found")])
    submission = ss.submit_scan("scan-project", str(tmp_path), data_root=tmp_path, process=process)
    assert submission.status == "failed"
    assert "could not be run" in submission.message


@pytest.mark.parametrize("stdout", ["not json at all", "[1, 2, 3]"])
def test_an_unreadable_payload_fails(stdout, tmp_path) -> None:
    process = FakeProcess(results=[ProcessResult(returncode=0, stdout=stdout, stderr="")])
    submission = ss.submit_scan("scan-project", str(tmp_path), data_root=tmp_path, process=process)
    assert submission.status == "failed"
    assert submission.frame is None


def test_a_failed_submit_leaves_the_previous_cache_untouched(tmp_path) -> None:
    parquet = tmp_path / ss.SCAN_PARQUETS["scan-project"]
    parquet.parent.mkdir(parents=True)
    pd.DataFrame({"conda_name": ["kept"]}).to_parquet(parquet, index=False)

    process = FakeProcess(results=[ProcessResult(returncode=1, stdout="", stderr="nope")])
    assert ss.submit_scan("scan-project", str(tmp_path), data_root=tmp_path, process=process).status == "failed"
    assert list(pd.read_parquet(parquet)["conda_name"]) == ["kept"]


# --------------------------------------------------------------------------- #
# The happy path
# --------------------------------------------------------------------------- #


def test_scan_project_runs_its_one_invocation_and_writes_the_pages_parquet(tmp_path) -> None:
    process = FakeProcess(results=[_ok(SCAN_PROJECT_PAYLOAD)])
    submission = ss.submit_scan("scan-project", str(tmp_path), data_root=tmp_path, process=process, repo_root=tmp_path)

    assert submission.status == "ok"
    assert process.calls == [["pixi", "run", "-e", "vuln-db", "scan-project", str(tmp_path), "--json"]]
    assert submission.parquet == tmp_path / ss.SCAN_PARQUETS["scan-project"]
    written = pd.read_parquet(submission.parquet)
    assert list(written.columns) == list(ss.SCAN_PROJECT_COLUMNS)
    assert len(written) == len(submission.frame)
    assert str(tmp_path) in submission.message


def test_env_inspect_runs_both_of_its_declared_modes(tmp_path) -> None:
    licenses = {"rows": [{"name": "numpy", "license": "BSD-3-Clause", "class": "permissive"}]}
    security = {"rows": [{"name": "numpy", "critical": 0, "high": 2}]}
    process = FakeProcess(results=[_ok(licenses), _ok(security)])

    submission = ss.submit_scan("env-inspect", str(tmp_path), data_root=tmp_path, process=process)

    assert submission.status == "ok"
    assert [call[-2] for call in process.calls] == ["--licenses", "--security"]
    assert all(str(tmp_path) in call for call in process.calls)
    assert list(submission.frame.columns) == list(ss.ENV_INSPECT_COLUMNS)


def test_the_cache_write_is_atomic_leaving_no_staging_file(tmp_path) -> None:
    process = FakeProcess(results=[_ok(SCAN_PROJECT_PAYLOAD)])
    submission = ss.submit_scan("scan-project", str(tmp_path), data_root=tmp_path, process=process)
    assert submission.parquet is not None
    leftovers = [p.name for p in submission.parquet.parent.iterdir() if p.name.startswith(".")]
    assert leftovers == []


# --------------------------------------------------------------------------- #
# The normalizers (pure)
# --------------------------------------------------------------------------- #


def test_normalize_scan_project_counts_per_severity_and_keeps_clean_packages() -> None:
    frame = ss.normalize_scan_project(SCAN_PROJECT_PAYLOAD)
    rows = {(row.conda_name, row.severity): row for row in frame.itertuples()}

    assert rows[("numpy", "High")].finding_count == 2
    assert rows[("numpy", "Low")].finding_count == 1
    assert rows[("numpy", "High")].license_spdx == "BSD-3-Clause"
    # one vuln carried a fixed_version, so the package is fixable
    assert bool(rows[("numpy", "High")].fix_available) is True

    # a vuln with no severity field is "Unknown", never dropped and never guessed
    assert rows[("requests", "Unknown")].finding_count == 1
    assert rows[("requests", "Unknown")].license_spdx is None

    # a scanned package with no vulnerabilities is a CLEAN row, not an absence
    assert rows[("tidy", "None")].finding_count == 0
    assert rows[("tidy", "None")].scan_status == "clean"
    assert rows[("numpy", "High")].scan_status == "vulnerable"


def test_normalize_scan_project_of_an_empty_payload_is_an_empty_declared_frame() -> None:
    frame = ss.normalize_scan_project({})
    assert frame.empty
    assert list(frame.columns) == list(ss.SCAN_PROJECT_COLUMNS)


def test_normalize_env_inspect_joins_the_two_modes_and_nulls_the_unseen() -> None:
    frame = ss.normalize_env_inspect(
        {"rows": [{"name": "numpy", "license": "BSD-3-Clause", "class": "non_permissive"}, {"no": "name"}]},
        {"rows": [{"name": "numpy", "critical": 1, "high": 3}, {"name": "lonely", "critical": 0, "high": 0}]},
    )
    by_name = frame.set_index("conda_name")

    assert by_name.loc["numpy", "non_permissive_flag"]
    assert by_name.loc["numpy", "vuln_critical"] == 1
    # present in only the security payload -> its license columns stay null,
    # never a zero/False that would read as "inspected, permissive".
    assert pd.isna(by_name.loc["lonely", "license_spdx"])
    assert pd.isna(by_name.loc["lonely", "non_permissive_flag"])
    # a row with no name is skipped, not given a fabricated key
    assert list(by_name.index) == ["lonely", "numpy"]


def test_normalize_env_inspect_of_two_empty_payloads_is_an_empty_declared_frame() -> None:
    frame = ss.normalize_env_inspect({}, {})
    assert frame.empty
    assert list(frame.columns) == list(ss.ENV_INSPECT_COLUMNS)


def test_the_declared_columns_are_exactly_what_each_pages_loader_reads() -> None:
    """A normalizer that drifted from its loader would write an unreadable cache."""
    from pyforge.atlas.dashboard import app

    inventory = {page.id: page for page in app.PAGE_INVENTORY}
    assert set(ss.SCAN_INVOCATIONS) == {
        page_id for page_id, page in inventory.items() if page.kind == "live-scan-artifact"
    }
    assert set(ss.SCAN_PARQUETS) == set(ss.SCAN_INVOCATIONS)
