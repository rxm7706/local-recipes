"""Story 36.1 (spec-pyforge-atlas CAP-66, amended 2026-10-18): the Basilisk population runs.

The public package listing refreshes itself; the advisory and detail drivers send a bearer token
only under the switch. No network: ``fake_transport`` (root ``conftest.py``) answers and records.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from pyforge.testing_kit import flag_states

from pyforge.atlas.datasets import basilisk as B
from pyforge.atlas.datasets import credentials as credential_switch
from pyforge.atlas.datasets import public_sources
from pyforge.atlas.datasets.rate_limit import RateLimitedScheduler
from pyforge.atlas.datasets.refresh import RefreshRequest
from pyforge.atlas.pipelines.vulnerability.nodes import (
    ingest_basilisk_advisories,
    refresh_basilisk_details,
    refresh_basilisk_population,
)

BATCH = "https://api.basilisk.prefix.dev/v1/querybatch"
VULNS = "https://api.basilisk.prefix.dev/v1/vulns"
TOKEN = "bsk_test_not_real"
_REAL_POPULATION = B.population_live  # captured before any pin


@pytest.fixture(autouse=True)
def _population_off_by_default(monkeypatch):
    monkeypatch.setattr(B, "population_live", lambda: False)


@pytest.fixture()
def population_on(monkeypatch):
    monkeypatch.setattr(B, "population_live", lambda: True)


@pytest.fixture()
def credentialed(monkeypatch):
    monkeypatch.setenv(credential_switch.SWITCH, "1")
    monkeypatch.setenv(credential_switch.BASILISK_TOKEN_ENV, TOKEN)


def _scheduler() -> RateLimitedScheduler:
    return RateLimitedScheduler(rps=1000.0, bucket_capacity=1000)


def _batch(tmp_path: Path) -> B.BasiliskBatchDataset:
    return B.BasiliskBatchDataset(url=BATCH, filepath=str(tmp_path / "batch"), scheduler=_scheduler())


def _detail(tmp_path: Path) -> B.BasiliskDetailDataset:
    return B.BasiliskDetailDataset(
        url=VULNS, filepath=str(tmp_path / "detail"), scheduler=_scheduler(), sleep=lambda _s: None
    )


def _population(*names: str) -> RefreshRequest:
    return refresh_basilisk_population(pd.DataFrame({"conda_name": list(names)}))


def _marker(ds) -> str:  # noqa: ANN001
    return ds._staleness_path.read_text(encoding="utf-8")


# -- the public listing ----------------------------------------------------------------------


def test_the_listing_walks_itself_with_live_public_sources_on(tmp_path, monkeypatch):
    pages = {
        0: {"total": 2, "limit": 1, "items": [{"name": "a"}]},
        1: {"total": 2, "limit": 1, "items": [{"name": "b"}]},
    }
    asked: list[str] = []

    def fetch_text(url: str, *, timeout: int = 300) -> str:
        asked.append(url)
        return json.dumps(pages[int(url.rsplit("offset=", 1)[1])])

    monkeypatch.setattr(public_sources, "live", lambda: True)
    monkeypatch.setattr(public_sources, "fetch_text", fetch_text)
    ds = B.BasiliskPackagesDataset(
        url="https://api.basilisk.prefix.dev/v1/packages", filepath=str(tmp_path / "p"), page_size=1
    )

    ds.save(RefreshRequest(store="discovery_basilisk_packages_raw", force=True))

    assert len(asked) == 2 and len(ds.load()) == 2 and ds.staleness() is None


def test_the_listing_has_no_refresher_with_live_public_sources_off(tmp_path):
    ds = B.BasiliskPackagesDataset(url="https://api.basilisk.prefix.dev/v1/packages", filepath=str(tmp_path / "p"))

    assert ds._live_refresher() is None


# -- the triggers ----------------------------------------------------------------------------


def test_the_population_trigger_names_every_enumerated_package_once():
    request = _population("numpy", "openssl", "numpy")

    assert request.basilisk_purls == ("pkg:conda/conda-forge/numpy", "pkg:conda/conda-forge/openssl")
    assert refresh_basilisk_population(None).basilisk_purls == ()


def test_the_detail_trigger_names_each_advisory_once():
    advisories = pd.DataFrame({"conda_name": ["a", "b"], "advisory_id": ["GHSA-1", "GHSA-1"], "modified": [None, None]})

    assert refresh_basilisk_details(advisories).basilisk_ids == ("GHSA-1",)


# -- the advisory drivers --------------------------------------------------------------------


def test_with_the_flag_off_nothing_is_sent_and_no_marker_is_written(tmp_path, fake_transport, credentialed):
    ds = _batch(tmp_path)

    ds.save(_population("numpy"))

    assert fake_transport.sent == [] and not ds._staleness_path.exists()


def test_without_the_switch_nothing_is_sent(tmp_path, fake_transport, population_on, monkeypatch):
    monkeypatch.setenv(credential_switch.BASILISK_TOKEN_ENV, TOKEN)  # a token, but no switch
    ds = _batch(tmp_path)

    ds.save(_population("numpy"))

    assert fake_transport.sent == [] and credential_switch.SWITCH in _marker(ds) and TOKEN not in _marker(ds)


def test_without_a_token_nothing_is_sent(tmp_path, fake_transport, population_on, monkeypatch):
    monkeypatch.setenv(credential_switch.SWITCH, "1")
    ds = _batch(tmp_path)

    ds.save(_population("numpy"))

    assert fake_transport.sent == [] and credential_switch.BASILISK_TOKEN_ENV in _marker(ds)


def test_the_querybatch_carries_the_bearer_and_its_answers_land(tmp_path, fake_transport, population_on, credentialed):
    vuln = {"id": "GHSA-1", "modified": "2026-10-01T00:00:00Z", "affected": [{"package": {"ecosystem": "PyPI"}}]}
    fake_transport.answers[BATCH] = (200, {"results": [{"vulns": [vuln]}, {}]})
    ds = _batch(tmp_path)

    ds.save(_population("numpy", "openssl"))

    (sent,) = fake_transport.sent
    assert sent.method == "POST" and sent.headers["Authorization"] == f"Bearer {TOKEN}"
    assert json.loads(sent.body) == {
        "queries": [
            {"package": {"purl": "pkg:conda/conda-forge/numpy"}},
            {"package": {"purl": "pkg:conda/conda-forge/openssl"}},
        ]
    }
    rows = ingest_basilisk_advisories(ds.load(), pd.DataFrame({"conda_name": ["numpy", "openssl"]}))
    assert rows[["conda_name", "advisory_id"]].values.tolist() == [
        ["numpy", "GHSA-1"]
    ]  # a PyPI-tagged advisory still matches


def test_an_answer_that_does_not_line_up_keeps_last_good(tmp_path, fake_transport, population_on, credentialed):
    fake_transport.answers[BATCH] = (200, {"results": [{}]})  # one result for two queries
    ds = _batch(tmp_path)

    ds.save(_population("numpy", "openssl"))

    assert "querybatch failed" in _marker(ds) and ds.load() == []


def test_a_rejected_token_keeps_last_good_and_never_reaches_the_marker(
    tmp_path, fake_transport, population_on, credentialed
):
    fake_transport.answers[BATCH] = (401, {"error": "unauthorized"})
    ds = _batch(tmp_path)

    ds.save(_population("numpy"))

    assert "401" in _marker(ds) and TOKEN not in _marker(ds)


def test_the_details_carry_the_bearer_and_wait_out_a_rate_limit(
    tmp_path, fake_transport, population_on, credentialed, monkeypatch
):
    answers = iter([(429, {}), (200, {"id": "GHSA-1", "summary": "s"})])

    import requests.adapters

    real = requests.adapters.HTTPAdapter.send

    def send(self, request, *args, **kwargs):  # noqa: ANN001, ANN202
        status, body = next(answers)
        fake_transport.answers[request.url] = (status, body)
        return real(self, request, *args, **kwargs)

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    ds = _detail(tmp_path)

    ds.save(RefreshRequest(store="vulnerability_basilisk_detail_raw", force=True, basilisk_ids=("GHSA-1",)))

    assert [r.url for r in fake_transport.sent] == [f"{VULNS}/GHSA-1"] * 2
    assert all(r.headers["Authorization"] == f"Bearer {TOKEN}" for r in fake_transport.sent)
    assert ds.load() == [{"id": "GHSA-1", "summary": "s"}]


def test_basilisk_auth_is_https_to_its_own_host_only(monkeypatch, credentialed):
    assert credential_switch.basilisk_auth(BATCH) is not None
    assert credential_switch.basilisk_auth("http://api.basilisk.prefix.dev/v1/querybatch") is None
    assert credential_switch.basilisk_auth("https://basilisk.example/v1/querybatch") is None
    monkeypatch.setenv(credential_switch.BASILISK_TOKEN_ENV, "a b")
    assert credential_switch.basilisk_auth(BATCH) is None  # a space inside is no token


@flag_states("pyforge.atlas.basilisk_population")  # spelled out: the flag gate reads this file for the key
def test_the_population_flag_is_read_at_each_save(tmp_path, fake_transport, credentialed, flag_provider, monkeypatch):
    flag_on = flag_provider[B.POPULATION_FLAG_KEY]
    ds = _batch(tmp_path)  # built before the flag is read
    monkeypatch.setattr(B, "population_live", lambda: flag_on)
    fake_transport.answers[BATCH] = (200, {"results": [{}]})

    ds.save(_population("numpy"))

    assert bool(fake_transport.sent) is flag_on


@pytest.mark.parametrize("variant", ["on", "off"])
def test_the_real_reader_reads_the_key_from_the_tree(tmp_path, monkeypatch, variant):
    from pyforge.testing_kit import flagd_tree

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {B.POPULATION_FLAG_KEY: variant})))

    assert _REAL_POPULATION() is (variant == "on")
