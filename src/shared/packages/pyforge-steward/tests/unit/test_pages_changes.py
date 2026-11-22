"""Story 130.1 (CAP-168): ``scripts/pages_changes.py`` writes the changes page's build input.

Every repository here is built in ``tmp_path`` with commits dated in 2020, so a window read from the wall clock
lists nothing and fails by name; the shape rules are the ones herald's ``parseChanges`` enforces
(``docs-site/src/lib/agent-surface.ts``), restated in Python.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): this module runs scripts/pages_changes.py, outside its package, so it
# runs in the station's live-tree half (pyforge-<station>-live-test) and fires on what it reads.
pytestmark = pytest.mark.live_tree

REPO_ROOT = Path(__file__).resolve().parents[6]
_CHANGES = REPO_ROOT / "scripts" / "pages_changes.py"

# parseChanges' rules (agent-surface.ts: ISO_DATE, SHA, XML_ILLEGAL)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2}))?$")
_SHA = re.compile(r"^[0-9a-f]{7,40}$")
_XML_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def _git(repo: Path, *args: str, date: str | None = None) -> str:
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(repo),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.test",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.test",
    }
    if date is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "protocol.file.allow=always", "-C", str(repo), *args],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _commit(repo: Path, subject: str, day: str) -> str:
    _git(repo, "commit", "--allow-empty", "-m", subject, date=f"{day}T12:00:00+01:00")
    return _git(repo, "rev-parse", "HEAD")


def _merge(repo: Path, branch: str, subject: str, day: str, *, side_day: str | None = None) -> str:
    """Merge a one-commit side branch into the checked-out branch; returns the merge commit."""
    base = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _git(repo, "checkout", "-q", "-b", branch)
    _commit(repo, f"work on {branch}", side_day or day)
    _git(repo, "checkout", "-q", base)
    _git(repo, "merge", "-q", "--no-ff", "-m", subject, branch, date=f"{day}T12:00:00+01:00")
    return _git(repo, "rev-parse", "HEAD")


def _repo(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A ``main`` whose built commit is 2020-02-14: one merge 40 days before it, two inside the 30 days."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    shas = {"root": _commit(repo, "root", "2019-12-01")}
    shas["old"] = _merge(repo, "old", "Merge pyforge-atlas/1-1 into main", "2020-01-05")
    shas["plain"] = _commit(repo, "a plain commit", "2020-01-14")
    shas["story"] = _merge(repo, "story", "Merge pyforge-steward/129-1 into main", "2020-02-01")
    shas["chain"] = _merge(repo, "chain", "Merge chain-steward-2020-02-10 into main", "2020-02-10")
    shas["head"] = _commit(repo, "the built commit", "2020-02-14")
    return repo, shas


def _run(repo: Path, out: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_CHANGES), "--repo", str(repo), "--out", str(out), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_parse_changes_accepts(document: dict) -> None:
    assert set(document) == {"generated_at", "window_days", "merges"}
    assert isinstance(document["generated_at"], str) and _ISO_DATE.match(document["generated_at"])
    assert isinstance(document["window_days"], int)
    shas: set[str] = set()
    for merge in document["merges"]:
        assert set(merge) == {"date", "station", "subject", "sha"}
        assert all(isinstance(value, str) for value in merge.values())
        assert _ISO_DATE.match(merge["date"]), merge
        assert merge["subject"].strip(), merge
        assert not _XML_ILLEGAL.search(merge["station"]) and not _XML_ILLEGAL.search(merge["subject"]), merge
        assert _SHA.match(merge["sha"]) and merge["sha"] not in shas, merge
        shas.add(merge["sha"])
    dates = [merge["date"] for merge in document["merges"]]
    assert dates == sorted(dates, reverse=True)  # newest first, as the reader would sort it


def test_the_window_is_anchored_on_the_built_commit_not_the_clock(tmp_path: Path) -> None:
    """The commits are years old: a window counted back from today lists none of them."""
    repo, shas = _repo(tmp_path)
    out = tmp_path / "content" / "changes.json"
    proc = _run(repo, out)
    assert proc.returncode == 0, proc.stderr
    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["generated_at"] == "2020-02-14T12:00:00+01:00"  # the built commit's committer time
    assert document["window_days"] == 30
    assert document["merges"] == [
        {
            "date": "2020-02-10",
            "station": "other",
            "subject": "Merge chain-steward-2020-02-10 into main",
            "sha": shas["chain"],
        },
        {
            "date": "2020-02-01",
            "station": "pyforge-steward",
            "subject": "Merge pyforge-steward/129-1 into main",
            "sha": shas["story"],
        },
    ]
    assert "wrote" in proc.stdout
    # the window follows --ref and --window-days, still from the commits: 40 days back reaches the older merge
    assert _run(repo, out, "--window-days", "45").returncode == 0
    assert [m["sha"] for m in json.loads(out.read_text(encoding="utf-8"))["merges"]][-1] == shas["old"]
    assert _run(repo, out, "--ref", shas["plain"]).returncode == 0
    earlier = json.loads(out.read_text(encoding="utf-8"))
    assert earlier["generated_at"] == "2020-01-14T12:00:00+01:00"
    assert [m["sha"] for m in earlier["merges"]] == [shas["old"]]


def test_a_merge_off_the_first_parent_line_is_not_listed(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    # a side branch that carries its own merge, then lands on main: only main's merge is on the first-parent line
    _git(repo, "checkout", "-q", "-b", "side")
    inner = _merge(repo, "inner", "Merge pyforge-mason/9-9 into main", "2020-02-12")
    _git(repo, "checkout", "-q", "main")
    _git(
        repo,
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "Merge pyforge-herald/5-2 into main",
        "side",
        date="2020-02-15T12:00:00+01:00",
    )
    landed = _git(repo, "rev-parse", "HEAD")
    out = tmp_path / "changes.json"
    assert _run(repo, out).returncode == 0
    merges = json.loads(out.read_text(encoding="utf-8"))["merges"]
    assert inner not in [m["sha"] for m in merges]
    assert "Merge pyforge-mason/9-9 into main" not in [m["subject"] for m in merges]
    assert merges[0] == {
        "date": "2020-02-15",
        "station": "pyforge-herald",
        "subject": "Merge pyforge-herald/5-2 into main",
        "sha": landed,
    }
    assert all(m["subject"].startswith("Merge ") for m in merges)  # no plain commit is listed either


def test_the_output_is_a_shape_parse_changes_accepts(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    # a subject holding characters XML forbids: the build would refuse the file, so the script strips them
    dirty = _merge(repo, "dirty", "Merge \x01pyforge-doctor/3-4\x1f into main\x0b", "2020-02-16")
    out = tmp_path / "changes.json"
    assert _run(repo, out).returncode == 0
    document = json.loads(out.read_text(encoding="utf-8"))
    _assert_parse_changes_accepts(document)
    assert document["merges"][0] == {
        "date": "2020-02-16",
        "station": "pyforge-doctor",
        "subject": "Merge pyforge-doctor/3-4 into main",
        "sha": dirty,
    }
    assert len(document["merges"]) == 3
    assert all(len(m["sha"]) == 40 for m in document["merges"])


@pytest.mark.parametrize(
    ("subject", "station"),
    [
        ("Merge pyforge-steward/129-1 into main", "pyforge-steward"),
        ("Merge pyforge-atlas/37-6 into main", "pyforge-atlas"),
        ("Merge pull request #2373 from someone/docs-full-refresh", "other"),
        ("Merge chain-steward-2026-10-13 into main", "other"),
        ("Merge recipe/rea-agents into main", "other"),
        ("Merge pyforge-steward/129-1 into main: and more", "other"),
        ("Merge branch 'main' of example.test:x/y", "other"),
    ],
)
def test_the_station_is_read_from_the_story_merge_subject(tmp_path: Path, subject: str, station: str) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, "root", "2020-02-01")
    _merge(repo, "b", subject, "2020-02-02")
    out = tmp_path / "changes.json"
    assert _run(repo, out).returncode == 0
    assert [m["station"] for m in json.loads(out.read_text(encoding="utf-8"))["merges"]] == [station]


def test_a_second_run_on_the_same_commit_writes_the_same_bytes(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    assert _run(repo, first).returncode == 0
    assert _run(repo, second).returncode == 0
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes().endswith(b"\n")


def test_an_unreadable_ref_exits_one_and_writes_nothing(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    out = tmp_path / "changes.json"
    proc = _run(repo, out, "--ref", "no-such-ref")
    assert proc.returncode == 1
    assert "pages_changes:" in proc.stderr
    assert not out.exists()
    assert _run(repo, out, "--window-days", "0").returncode == 1
    assert _run(tmp_path, out).returncode == 1  # not a git checkout
    assert not out.exists()


def _fetch_as_the_workflow_does(clone: Path) -> None:
    """The fetch of pages.yml's step (test_pages_workflow.py pins its text): every commit, no tree and no blob."""
    if _git(clone, "rev-parse", "--is-shallow-repository") == "true":
        head = _git(clone, "rev-parse", "HEAD")
        _git(clone, "fetch", "--no-tags", "--filter=blob:none", "--unshallow", "origin", head)


@pytest.mark.parametrize("side_day", ["2020-02-01", "2019-12-20"])
def test_a_shallow_checkout_is_refused_until_the_window_is_fetched(tmp_path: Path, side_day: str) -> None:
    """A depth-1 checkout cannot tell a merge from a plain commit: exit 3 and no file. After the workflow's fetch
    the file is the full clone's, byte for byte, also when a merged branch's tip is older than the window."""
    repo, _ = _repo(tmp_path)
    _git(repo, "config", "uploadpack.allowFilter", "true")  # a file:// remote serves --filter only when told to
    _merge(repo, "late", "Merge pyforge-warden/2-2 into main", "2020-02-13", side_day=side_day)
    _commit(repo, "the built commit, again", "2020-02-14")
    full = tmp_path / "full.json"
    assert _run(repo, full).returncode == 0
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", "--depth", "1", repo.as_uri(), str(clone))
    out = tmp_path / "shallow.json"
    proc = _run(clone, out)
    assert proc.returncode == 3
    assert "too shallow" in proc.stderr
    assert not out.exists()
    _fetch_as_the_workflow_does(clone)
    assert _run(clone, out).returncode == 0
    assert out.read_bytes() == full.read_bytes()
    assert len(json.loads(out.read_text(encoding="utf-8"))["merges"]) == 3
    assert _git(clone, "status", "--porcelain") == ""  # the checked-out tree is still whole


def test_a_pull_request_s_synthetic_merge_commit_is_not_listed(tmp_path: Path) -> None:
    """A pull-request build checks out GitHub's own merge of the PR head into its base, subject ``Merge <sha> into
    <sha>``: no merge to main, and a new commit on every run (the review of 2026-11-22)."""
    repo, _ = _repo(tmp_path)
    before = tmp_path / "before.json"
    assert _run(repo, before).returncode == 0
    listed = [merge["sha"] for merge in json.loads(before.read_text(encoding="utf-8"))["merges"]]
    synthetic = _merge(repo, "pr-head", f"Merge {'a' * 40} into {'b' * 40}", "2020-02-14")
    out = tmp_path / "changes.json"
    assert _run(repo, out).returncode == 0
    merges = json.loads(out.read_text(encoding="utf-8"))["merges"]
    assert synthetic not in [merge["sha"] for merge in merges]
    assert [merge["sha"] for merge in merges] == listed
