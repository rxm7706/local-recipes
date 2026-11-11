"""Story 56.4 (spec-pyforge-doctor:CAP-93, spec-pyforge-doctor:AD-15): a source that finds no subject says so.

Over an empty ``git init`` tree every ``detectors-ci`` Doctor source returns at least one finding, and the
partition is pinned here, in the package half (this module reads nothing outside ``tmp_path``):

* ``pass`` -- ``dashboard-drift`` and ``check-layout`` only;
* ``FINDINGS`` -- ``spec-surface`` and ``docs-map-hygiene`` only;
* every other name -- only findings ``models.is_gather_failure`` accepts, so ``scripts/detectors.py`` reads the
  row ``unmeasured``, never ``pass``.

The names are listed below, one per ``detectors-ci`` row (``scripts/detectors.py``'s ``_DOCTOR_SOURCE_TASKS``); the
repo-level twin ``tests/scripts/test_detectors_doctor_sources.py`` runs the registry itself over an empty tree, so
the two lists cannot drift apart unnoticed. New cases for this story live here, not in the modules Stories 58.1 and
58.2 split -- including the one rider with behaviour: ``one_chain``'s station fallback is the core roster.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from pyforge.core.roster import STATIONS

from pyforge.doctor.models import UNEVALUABLE_EVIDENCE_KEY, DoctorStatus, Finding, is_gather_failure
from pyforge.doctor.sources import one_chain
from pyforge.doctor.sources.__main__ import DISPATCH
from pyforge.doctor.verdict import exit_code_for

#: One entry per ``detectors-ci`` row, in ``_DOCTOR_SOURCE_TASKS`` order.
DETECTORS_CI_NAMES: tuple[str, ...] = (
    "ledger-regression",
    "ledger-direction",
    "story-status",
    "capability-effect",
    "status-body-consistency",
    "chain-completeness",
    "dashboard-drift",
    "check-layout",
    "dream-chain",
    "spec-surface",
    "deferred-work",
    "forward-dependency",
    "bmad-drift",
    "platform-policy-suite",
    "bmad-render-config-ambiguity",
    "frozen-path-changed",
    "pixi-currency-ledger",
    "general-docs-consistency",
    "capability-ledger",
    "chain-sprawl",
    "fr-without-cap",
    "fold-complete",
    "docs-map-hygiene",
    "docs-shelf-occupancy",
    "live-proof-surface",
    "docs-currency",
    "bmad-output-hygiene",
    "dreams-hygiene",
    "frontmatter-duplicate-keys",
)

#: Unchanged by Story 56.4, each with the reason it stays as it is.
UNCHANGED: dict[str, str] = {
    # Reintroduction gates: the absence of the retired Guildhall console files is exactly what they measure, so an
    # empty tree is a real measurement and reads `pass`.
    "dashboard-drift": "reintroduction gate -- the retired console files being absent is what it measures",
    "check-layout": "reintroduction gate -- the retired console files being absent is what it measures",
    # A missing input is a FAIL by these sources' own contract (AD-2: no source changes its exit domain).
    "spec-surface": "FAILs on a missing baseline -- its own exit domain, never turned into a WARN",
    "docs-map-hygiene": "FAILs on a missing docs/MAP.md -- its own exit domain, never turned into a WARN",
    # Already carry the marker on their cannot-evaluate WARN.
    "ledger-regression": "its unresolvable-ledger-head WARN was already marked unevaluable",
    "bmad-drift": "its bmad-drift-unevaluable WARN was already marked",
    # Their WARN over an empty tree is degrade_on_exception's ({"exception": ...}), already a gather failure.
    "live-proof-surface": "its WARN here is degrade_on_exception's, already a gather failure",
    "docs-currency": "its WARN here is degrade_on_exception's, already a gather failure",
}

#: The detectors-ci row an empty tree must read, by name; every other name reads `unmeasured`.
PASS_NAMES = frozenset({"dashboard-drift", "check-layout"})
FINDINGS_NAMES = frozenset({"spec-surface", "docs-map-hygiene"})

#: Story 56.4 (b): an OK or () over an absent subject became exactly one `<source>-unevaluable` WARN.
NEW_UNEVALUABLE_NAMES: tuple[str, ...] = (
    "ledger-direction",
    "story-status",
    "chain-completeness",
    "bmad-render-config-ambiguity",
    "general-docs-consistency",
    "docs-shelf-occupancy",
    "bmad-output-hygiene",
    "frontmatter-duplicate-keys",
    "capability-effect",
    "platform-policy-suite",
    "status-body-consistency",
)

_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # `cli_bridge.run_git` reads os.environ at call time, so an inherited GIT_DIR must not decide what a gather sees.
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(target: Path, *args: str) -> None:
    env = {k: v for k, v in os.environ.items() if k not in _LEAKY_GIT_VARS}
    subprocess.run(["git", *args], cwd=target, env=env, capture_output=True, text=True, check=True)


def _empty_tree(root: Path, *, committed: bool) -> Path:
    """An empty ``git init`` tree: no file at all, and either no commit (an unborn ``main``) or one empty one."""
    root.mkdir()
    _git(root, "init", "-q", "--initial-branch=main")
    if committed:
        _git(root, "config", "user.email", "doctor-test@example.com")
        _git(root, "config", "user.name", "Doctor Test")
        _git(root, "config", "commit.gpgsign", "false")
        _git(root, "config", "core.hooksPath", "/dev/null")
        _git(root, "commit", "-q", "--allow-empty", "-m", "seed")
    return root


@pytest.fixture(params=("unborn", "committed"))
def empty_tree(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    return _empty_tree(tmp_path / "empty", committed=request.param == "committed")


def _row_status(findings: tuple[Finding, ...]) -> str:
    """The status ``scripts/detectors.py`` gives a row of these findings (Story 56.3's three-way read)."""
    if exit_code_for(findings) != 0:
        return "FINDINGS"
    if findings and all(is_gather_failure(f) for f in findings):
        return "unmeasured"
    return "pass"


def test_the_partition_names_are_detectors_ci_names_and_dispatch_entries() -> None:
    names = set(DETECTORS_CI_NAMES)
    assert len(names) == len(DETECTORS_CI_NAMES)
    assert names <= DISPATCH.keys()
    assert set(UNCHANGED) <= names
    assert PASS_NAMES | FINDINGS_NAMES <= set(UNCHANGED)
    assert set(NEW_UNEVALUABLE_NAMES) <= names
    assert not set(NEW_UNEVALUABLE_NAMES) & set(UNCHANGED)


@pytest.mark.parametrize("name", DETECTORS_CI_NAMES)
def test_an_empty_tree_reads_as_what_the_source_measured(name: str, empty_tree: Path) -> None:
    findings = DISPATCH[name](empty_tree)

    assert findings, f"{name} returned nothing over an empty tree -- an absent subject must say so"
    expected = "pass" if name in PASS_NAMES else "FINDINGS" if name in FINDINGS_NAMES else "unmeasured"
    assert _row_status(findings) == expected, [f.to_json_dict() for f in findings]
    if expected == "unmeasured":
        assert all(f.status is DoctorStatus.WARN for f in findings), [f.to_json_dict() for f in findings]


@pytest.mark.parametrize("name", NEW_UNEVALUABLE_NAMES)
def test_an_absent_subject_is_one_source_unevaluable_warn(name: str, tmp_path: Path) -> None:
    findings = DISPATCH[name](_empty_tree(tmp_path / "empty", committed=True))

    assert len(findings) == 1, [f.to_json_dict() for f in findings]
    (finding,) = findings
    assert finding.source.value == name
    assert finding.check == f"{name}-unevaluable"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence[UNEVALUABLE_EVIDENCE_KEY] is True


def test_one_chain_falls_back_to_the_core_roster_not_a_literal_copy(tmp_path: Path) -> None:
    # Rider: with no guild-roster.json to read, the station list is pyforge.core.roster's, never a second copy.
    assert one_chain._stations(tmp_path) == STATIONS
