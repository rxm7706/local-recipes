"""A plain ``pyforge atlas run`` over a fresh data root exits 0, and again with every fetch refused.

Story 34.14 (CAP-64, AC2): ``__default__`` (a run with no ``--pipelines``) over an empty data root, the public
fetches served from recorded responses, runs to the end. It leaves out ``query_plane_cache`` and ``universal_sbom``
(``pipeline_registry.NAMED_RUN_ONLY_PIPELINES``); with ``query_plane_cache`` back in, the run stops at
``query_plane_estate_source``. Fixture-scale responses cannot meet the 30000-name ``verification_sets`` floors, so the
run lowers them through runtime params: "plain" is the pipeline, not the parameters.

Story 34.15 (CAP-64, AC7): a second run over the root the first one filled, with every request and subprocess
refused, also runs to the end, and every store that held ``last_good.parquet`` keeps that file under its AD-13
``.staleness.json`` marker. Before Story 34.15 it stopped at ``core_feedstock_outputs_raw`` before any node ran.

No test here reaches the network: requests answer from the table below or raise, subprocesses raise, and the
socket guard in ``tests/conftest.py`` stays on underneath (AD-11).
"""

from __future__ import annotations

import gzip
import io
import json
import os
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import requests

_MEMBER_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _MEMBER_DIR.parents[3]
_CREDENTIALS_KEY_RE = re.compile(r"^\s*credentials:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")
# fixture-scale responses hold one package; the default floors expect the whole universe (30000 names)
_RUNTIME_PARAMS = {"verification_sets": {"core_packages_enumerated_floor": 1, "pypi_universe_floor": 1}}

VULNERABILITY_FEEDS = ("vulnerability_cisa_kev_raw", "vulnerability_epss_raw", "vulnerability_cwe_catalog_raw")
CORE_SOURCES = ("core_feedstock_outputs_raw", "core_repodata_raw", "pypi_simple_index_raw")
_SUBDIRS = ("noarch", "linux-64", "linux-aarch64", "linux-ppc64le", "osx-64", "osx-arm64", "win-64")


def _zip(members: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)
    return buf.getvalue()


def _recorded_responses() -> dict[str, bytes]:
    """The public bodies a fresh root needs, each at fixture scale: one conda package, one PyPI project, one CVE."""
    package = {"name": "widget", "version": "1.0", "timestamp": 1700000000000}
    answers = {
        "https://github.com/conda-forge/feedstock-outputs/archive/refs/heads/main.zip": _zip(
            {"feedstock-outputs-main/outputs/w/i/d/widget.json": json.dumps({"feedstocks": ["widget"]})}
        ),
        "https://pypi.org/simple/": json.dumps(
            {"meta": {}, "projects": [{"name": "widget", "_last-serial": 1}]}
        ).encode(),
        "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json": json.dumps(
            {
                "catalogVersion": "2026.11.01",
                "vulnerabilities": [
                    {"cveID": "CVE-2026-0001", "knownRansomwareCampaignUse": "Known", "cwes": ["CWE-79"]}
                ],
            }
        ).encode(),
        "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz": gzip.compress(
            b"#model_version:v1\ncve,epss,percentile\nCVE-2026-0001,0.5,0.9\n"
        ),
        "https://cwe.mitre.org/data/csv/1000.csv.zip": _zip({"1000.csv": "CWE-ID,Name\n79,XSS\n"}),
    }
    for subdir in _SUBDIRS:
        packages = {"widget-1.0-0.tar.bz2": package} if subdir == "noarch" else {}
        answers[f"https://conda.anaconda.org/conda-forge/{subdir}/current_repodata.json"] = json.dumps(
            {"packages": packages}
        ).encode()
    return answers


@dataclass
class _Network:
    """``Session.request``'s and ``PosixProcess.run``'s stand-in. A recorded URL answers 200 until ``refuse`` is
    set; any other request, and every subprocess, is refused."""

    answers: dict[str, bytes]
    refuse: bool = False
    served: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)

    def request(self, method: str | None = None, url: str | None = None, **kwargs: Any) -> requests.Response:
        if self.refuse or url not in self.answers:
            self.refused.append(str(url))
            raise requests.exceptions.ConnectionError(f"refused: {url}")
        self.served.append(url)
        response = requests.Response()
        response.status_code = 200
        response._content = self.answers[url]
        response.url = url
        response.encoding = "utf-8"
        response.headers["Content-Type"] = "application/json"
        return response


@dataclass
class _PlainRun:
    project: Path
    root: Path
    network: _Network

    def run(self) -> None:
        """One ``__default__`` run in a fresh session; a failed run raises out of here."""
        from kedro.framework.session import KedroSession

        with KedroSession.create(project_path=self.project, runtime_params=_RUNTIME_PARAMS) as session:
            session.run()


def _copy_project(tmp_path: Path) -> Path:
    """Copy only what a session needs, with an all-``{}`` credentials stub; ``conf/local`` and ``data`` never leave
    the member."""
    dest = tmp_path / "pyforge-atlas"
    dest.mkdir()
    shutil.copy2(_MEMBER_DIR / "pyproject.toml", dest / "pyproject.toml")
    shutil.copy2(_MEMBER_DIR / ".telemetry", dest / ".telemetry")  # consent: false, or kedro-telemetry calls out
    shutil.copytree(_MEMBER_DIR / "conf" / "base", dest / "conf" / "base")
    shutil.copytree(_MEMBER_DIR / "src", dest / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    local = dest / "conf" / "local"
    local.mkdir(parents=True)
    keys = sorted(
        {
            m.group(1)
            for line in (dest / "conf" / "base" / "catalog.yml").read_text(encoding="utf-8").splitlines()
            if (m := _CREDENTIALS_KEY_RE.match(line))
        }
    )
    (local / "credentials.yml").write_text("".join(f"{key}: {{}}\n" for key in keys), encoding="utf-8")
    return dest


@pytest.fixture(params=[False, True], ids=["live-off", "live-on"])
def plain_run(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _PlainRun:
    """A copied project over an empty data root, with ``pyforge.atlas.live_public_sources`` off and on, and every
    process-wide thing ``bootstrap_project`` or a session changes put back afterwards."""
    import importlib

    from kedro.framework import project as kedro_project
    from kedro.framework.startup import bootstrap_project
    from pyforge.core import process as core_process

    from pyforge.atlas.datasets import public_sources

    # imported from the real tree first: bootstrap_project prepends the copy's src to sys.path
    for module in ("pyforge.atlas.settings", "pyforge.atlas.pipeline_registry"):
        importlib.import_module(module)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("PYTHONPATH", os.environ.get("PYTHONPATH", ""))
    monkeypatch.setattr(kedro_project, "PACKAGE_NAME", kedro_project.PACKAGE_NAME)
    monkeypatch.setattr(kedro_project.settings, "_wrapped", kedro_project.settings._wrapped)
    for attr in ("_pipelines_module", "_is_data_loaded", "_content", "_requested_pipelines"):
        if hasattr(kedro_project.pipelines, attr):
            monkeypatch.setattr(kedro_project.pipelines, attr, getattr(kedro_project.pipelines, attr))

    root = tmp_path / "data"
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", str(root))
    monkeypatch.setenv(
        "PYFORGE_ATLAS_SEED_ROOT", str(_REPO_ROOT / ".claude" / "skills" / "conda-forge-expert" / "data")
    )
    (tmp_path / "recipes").mkdir()
    monkeypatch.setenv("PYFORGE_ATLAS_LOCAL_RECIPES_DIR", str(tmp_path / "recipes"))
    live = bool(request.param)
    monkeypatch.setattr(public_sources, "live", lambda: live)

    network = _Network(_recorded_responses())
    monkeypatch.setattr(requests.Session, "request", network.request)

    def _refuse_process(self: object, argv: list[str], **kwargs: object) -> None:
        raise core_process.ProcessError(f"refused: {argv}")

    monkeypatch.setattr(core_process.PosixProcess, "run", _refuse_process)
    monkeypatch.chdir(tmp_path)

    project = _copy_project(tmp_path)
    bootstrap_project(project)
    return _PlainRun(project=project, root=root, network=network)


def test_a_plain_run_on_a_fresh_data_root_exits_0(plain_run: _PlainRun) -> None:
    """Story 34.14 AC2 (and AC6: it fails with ``query_plane_cache`` back in ``__default__``)."""
    assert not plain_run.root.exists()

    plain_run.run()

    scored = plain_run.root / "derived" / "pypi_intelligence_scored" / "pypi_intelligence_scored.parquet"
    assert scored.is_file(), "pypi_intelligence_scored was not written"
    assert "pypi_name" in pd.read_parquet(scored).columns
    for name in VULNERABILITY_FEEDS:
        store = plain_run.root / "raw" / name
        assert not pd.read_parquet(store / "last_good.parquet").empty, f"{name} kept no rows"
        assert not (store / ".staleness.json").exists(), f"{name} reads stale after a served fetch"
    assert {"https://pypi.org/simple/", "https://cwe.mitre.org/data/csv/1000.csv.zip"} <= set(plain_run.network.served)


def test_a_second_run_with_every_fetch_refused_keeps_last_good(plain_run: _PlainRun) -> None:
    """Story 34.15 AC7 (and AC8: it fails when the three core sources lose their degrade)."""
    plain_run.run()
    filled = {path.parent.name: path.read_bytes() for path in (plain_run.root / "raw").glob("*/last_good.parquet")}
    assert set(CORE_SOURCES) | set(VULNERABILITY_FEEDS) <= set(filled)

    plain_run.network.refuse = True
    refused_before = len(plain_run.network.refused)
    plain_run.run()

    assert len(plain_run.network.refused) > refused_before, "the second run never asked the network"
    for name, body in sorted(filled.items()):
        store = plain_run.root / "raw" / name
        assert (store / "last_good.parquet").read_bytes() == body, f"{name} lost its last-good copy"
        marker = json.loads((store / ".staleness.json").read_text(encoding="utf-8"))
        assert marker["stale"] is True and marker["last_good_exists"] is True, f"{name}: {marker}"
