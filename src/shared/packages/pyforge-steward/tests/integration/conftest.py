"""The attended NKP probes' options, cluster fixture and report scrub (steward Story 118.6, spec-pyforge-steward CAP-177).

Run them with ``pixi run -e pyforge-steward pyforge-steward-nkp-probes``. For another config, add
``-- --nkp-config <path>``. When the gateway is reached through ``kubectl port-forward`` (rootless kind), add
``-- --nkp-connect-to 127.0.0.1``. ``pyforge-steward-test`` and ``pyforge-steward-live-test`` never collect this
directory and no CI job runs it, because the probes are attended. With no reachable kubeconfig every probe skips
and names the reason.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import nkp_probes
import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): the `nkp` fixture hands the repo root to nkp_probes.connect, which
# reads the NIC config under it, so every module here is marked live_tree and this file is declared in the
# station-tests trigger map's ROOT_HANDOFF_INPUTS under steward's live-tree half. Neither half collects
# tests/integration; pyforge-steward-nkp-probes does (Story 118.6).
pytestmark = pytest.mark.live_tree

# tests/integration -> tests -> pyforge-steward -> packages -> shared -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[6]


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("nkp", "attended NKP probes (steward Story 118.6)")
    group.addoption(
        "--nkp-config",
        default=nkp_probes.DEFAULT_CONFIG,
        help="the NIC config whose cluster the probes check, relative to the repo root "
        f"(default: {nkp_probes.DEFAULT_CONFIG})",
    )
    group.addoption(
        "--nkp-connect-to",
        default=None,
        help="send every connection for the domain and its subdomains to this address, keeping the host name "
        "(a gateway port-forwarded to 127.0.0.1)",
    )


@pytest.fixture(scope="session")
def nkp(request: pytest.FixtureRequest) -> nkp_probes.NkpCluster:
    """The config's cluster with its ``nic outputs``: skips when no kubeconfig is reachable."""
    config = Path(str(request.config.getoption("nkp_config")))
    connect_to = request.config.getoption("nkp_connect_to")
    try:
        return nkp_probes.connect(config, root=REPO_ROOT, connect_to=str(connect_to) if connect_to else None)
    except nkp_probes.ClusterAbsent as absent:
        pytest.skip(f"no cluster for {config}: {absent}")
    except nkp_probes.ProbeError as error:
        pytest.fail(str(error), pytrace=False)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]) -> Generator[None, Any, Any]:
    """No secret ``nic outputs`` printed reaches a report: its failure text and captured output are scrubbed."""
    report = yield
    nkp_probes.scrub_report(report)
    return report
