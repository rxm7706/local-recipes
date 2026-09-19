"""Unit tests for ``ledger.gather_direction`` (marshal Story 15.2 /
FR-137 / FR-138) — ledger-vs-git drift WITH DIRECTION, never the feed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import ledger

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
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _write_ledger(repo: Path, project: str, statuses: dict[str, str]) -> Path:
    ledger_path = (
        repo
        / "_bmad-output"
        / "projects"
        / project
        / "planning-artifacts"
        / "sprint-status-ledger.yaml"
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["development_status:"]
    lines.extend(f"  {key}: {value}" for key, value in statuses.items())
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ledger_path


def _commit(repo: Path, message: str, *, allow_empty: bool = False) -> None:
    _git(repo, "add", "-A")
    args = ["commit", "-q", "-m", message]
    if allow_empty:
        args.insert(1, "--allow-empty")
    _git(repo, *args)


def _write_policy(repo: Path, project: str, merge_subject_template: str) -> None:
    """A minimal ``marshal-policy.toml`` declaring only the one key this
    module reads -- Story 27.1's per-station template read."""
    policy_path = (
        repo / "_bmad-output" / "projects" / project
        / "planning-artifacts" / "marshal-policy.toml"
    )
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(
        f'merge_subject_template = "{merge_subject_template}"\n', encoding="utf-8"
    )


def test_landed_but_unpromoted_is_fail(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {"15-2-landing-promotes": "in-progress"},
    )
    _commit(repo, "seed ledger")
    _commit(
        repo,
        "Merge pull request #1 from rxm7706/marshal/15-2-landing-promotes",
        allow_empty=True,
    )

    findings = ledger.gather_direction(repo)

    fails = [f for f in findings if f.status == DoctorStatus.FAIL]
    assert len(fails) == 1
    assert fails[0].source == Source.LEDGER_DIRECTION
    assert fails[0].evidence["direction"] == ledger.DIRECTION_LANDED_UNPROMOTED
    assert fails[0].evidence["story_id"] == "15-2"


def test_done_but_unmerged_is_warn(tmp_path: Path) -> None:
    """A done flip that exists only on this branch is the real defect.

    Not "no merge subject names it" — the flip must be absent from the
    ledger as committed at ``base_ref`` too. See
    ``test_batched_pr_promotion_is_not_unmerged`` for why.
    """
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {"15-2-landing-promotes": "in-progress"},
    )
    _commit(repo, "seed ledger on main")
    _git(repo, "checkout", "-q", "-b", "work")
    _write_ledger(
        repo,
        "pyforge-marshal",
        {"15-2-landing-promotes": "done"},
    )
    _commit(repo, "flip to done on the branch only")

    findings = ledger.gather_direction(repo)

    warns = [f for f in findings if f.status == DoctorStatus.WARN]
    assert len(warns) == 1
    assert warns[0].evidence["direction"] == ledger.DIRECTION_DONE_UNMERGED
    assert warns[0].evidence["base_evidence"] == "ledger-at-base"


def test_batched_pr_promotion_is_not_unmerged(tmp_path: Path) -> None:
    """Regression: a key promoted by a PR whose subject names no story.

    The fleet lands most work in batched ``chore/``/``docs/``/``dispatch/``
    PRs. Judged on merge subjects alone this shape produced 383 false
    ``done-but-unmerged`` findings across the eight tracked ledgers — 53% of
    all done stories — while ``main``'s own ledger said ``done`` for every
    one of them.
    """
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_ledger(repo, "pyforge-marshal", {"32-1-consistency": "done"})
    _commit(repo, "seed")
    _commit(
        repo,
        "Merge pull request #1082 from rxm7706/chore/fleet-consistency-2026-09-07",
        allow_empty=True,
    )
    _git(repo, "checkout", "-q", "-b", "work")

    findings = ledger.gather_direction(repo)

    assert [f for f in findings if f.status == DoctorStatus.WARN] == []
    assert findings[0].status == DoctorStatus.OK


def test_ledger_new_on_branch_falls_back_to_subjects(tmp_path: Path) -> None:
    """No base evidence either way must not silence the check.

    A ledger that does not exist at ``base_ref`` yields ``None``, not an
    empty set — otherwise a brand-new file would read as "nothing was done
    at base", which is indistinguishable from real absence.
    """
    repo = tmp_path / "r"
    _init_repo(repo)
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _commit(repo, "seed without any ledger")
    _git(repo, "checkout", "-q", "-b", "work")
    _write_ledger(repo, "pyforge-marshal", {"1-1-first": "done"})
    _commit(repo, "add the ledger on this branch")

    findings = ledger.gather_direction(repo)

    warns = [f for f in findings if f.status == DoctorStatus.WARN]
    assert len(warns) == 1
    assert warns[0].evidence["base_evidence"] == "absent-at-base"


def test_agreement_is_ok(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {"15-2-landing-promotes": "done"},
    )
    _commit(repo, "seed")
    _commit(
        repo,
        "Merge pull request #2 from rxm7706/marshal/15-2-landing-promotes",
        allow_empty=True,
    )

    findings = ledger.gather_direction(repo)

    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert findings[0].source == Source.LEDGER_DIRECTION


def test_never_reads_tier3_feed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-138: the oracle is merge history + tracked twin, never the feed."""
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_ledger(repo, "pyforge-marshal", {"1-1-demo": "done"})
    feed = (
        repo
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "implementation-artifacts"
        / "sprint-status.yaml"
    )
    feed.parent.mkdir(parents=True, exist_ok=True)
    feed.write_text("development_status:\n  1-1-demo: done\n", encoding="utf-8")
    _commit(repo, "seed")
    _commit(
        repo,
        "Merge pull request #3 from rxm7706/marshal/1-1-demo",
        allow_empty=True,
    )

    reads: list[Path] = []
    real_read_text = Path.read_text

    def _tracking_read(self: Path, *args, **kwargs):
        reads.append(self)
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _tracking_read)
    ledger.gather_direction(repo)

    assert not any(p.name == "sprint-status.yaml" for p in reads)


def test_bmadloop_merge_subject_scoped_to_project(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {"2-1-scaffold": "backlog"},
    )
    _commit(repo, "seed")
    # Wrong-project loop target must NOT accuse marshal.
    _commit(
        repo,
        "Merge bmad-loop/run-1/2-1-scaffold into loop/pyforge-warden (bmad-loop)",
        allow_empty=True,
    )

    findings = ledger.gather_direction(repo)
    fails = [f for f in findings if f.status == DoctorStatus.FAIL]
    assert fails == []


# --- Story 27.1: a templated merge subject names its station's OWN template


def test_sibling_default_template_merge_is_not_attributed_when_station_has_its_own(
    tmp_path: Path,
) -> None:
    """The live incident this fixes: atlas has no custom template of its own
    historically (bare legacy default, ambiguous), but ONCE it declares its
    own scoped ``merge_subject_template``, a sibling's plain ``Merge <key>
    into main`` (rendered from THAT sibling's own bare default) must not be
    read as atlas's landing."""
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_policy(repo, "pyforge-atlas", "Merge pyforge-atlas/{key} into main")
    _write_ledger(repo, "pyforge-atlas", {"13-5-trending-ingest": "backlog"})
    _commit(repo, "seed")
    # A sibling station's own (unscoped) legacy-default merge -- coincidentally
    # the same numeric key, belongs to another station entirely.
    _commit(repo, "Merge 13-5 into main", allow_empty=True)

    findings = ledger.gather_direction(repo)

    fails = [f for f in findings if f.status == DoctorStatus.FAIL]
    assert fails == []


def test_own_scoped_template_merge_counts_as_landed(tmp_path: Path) -> None:
    """The other half: atlas's OWN scoped template still counts, so a truly
    landed-but-unpromoted row is still caught."""
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_policy(repo, "pyforge-atlas", "Merge pyforge-atlas/{key} into main")
    _write_ledger(repo, "pyforge-atlas", {"13-5-trending-ingest": "backlog"})
    _commit(repo, "seed")
    _commit(repo, "Merge pyforge-atlas/13-5 into main", allow_empty=True)

    findings = ledger.gather_direction(repo)

    fails = [f for f in findings if f.status == DoctorStatus.FAIL]
    assert len(fails) == 1
    assert fails[0].evidence["direction"] == ledger.DIRECTION_LANDED_UNPROMOTED
    assert fails[0].evidence["story_id"] == "13-5"
    assert fails[0].evidence["project"] == "pyforge-atlas"


def test_no_policy_file_legacy_bare_subject_does_not_match_scoped_default(
    tmp_path: Path,
) -> None:
    """A project with no ``marshal-policy.toml`` (or none declaring the key)
    resolves to the repo default, which is ``{slug}``-scoped fleet-wide
    (Story 50.4) — so a pre-scoping-era bare subject with no station token
    at all (``Merge 7-2 into main``) still does not match it, and still
    raises no attribution.

    Before Story 50.4 this function skipped the templated check entirely
    whenever a project had no override, specifically to dodge the live
    2026-09-18 incident where wiring the (then station-blind) bare default
    in unconditionally turned 3 real findings into 306 fleet-wide. Story
    50.4 removed that guard because the default template itself is no
    longer station-blind: it is attempted unconditionally now, but a
    genuinely unscoped legacy subject like this one still can't satisfy a
    ``{slug}``-carrying template, so the false-positive risk the old guard
    existed for is gone at the source. See
    ``test_no_policy_file_scoped_default_template_merge_counts_as_landed``
    for the positive case this enables."""
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_ledger(repo, "pyforge-mason", {"7-2-something": "backlog"})
    _commit(repo, "seed")
    _commit(repo, "Merge 7-2 into main", allow_empty=True)

    findings = ledger.gather_direction(repo)

    fails = [f for f in findings if f.status == DoctorStatus.FAIL]
    assert fails == []


def test_no_policy_file_scoped_default_template_merge_counts_as_landed(
    tmp_path: Path,
) -> None:
    """Story 50.4: a project with no override still gets credit for a
    landing rendered from the (now ``{slug}``-scoped) repo default -- the
    residual ``test_no_policy_file_legacy_bare_subject_does_not_match_scoped_default``
    itself named as still open before this story closed it."""
    repo = tmp_path / "r"
    _init_repo(repo)
    _write_ledger(repo, "pyforge-mason", {"7-2-something": "backlog"})
    _commit(repo, "seed")
    _commit(repo, "Merge pyforge-mason/7-2 into main", allow_empty=True)

    findings = ledger.gather_direction(repo)

    fails = [f for f in findings if f.status == DoctorStatus.FAIL]
    assert len(fails) == 1
    assert fails[0].evidence["direction"] == ledger.DIRECTION_LANDED_UNPROMOTED
    assert fails[0].evidence["story_id"] == "7-2"
    assert fails[0].evidence["project"] == "pyforge-mason"
