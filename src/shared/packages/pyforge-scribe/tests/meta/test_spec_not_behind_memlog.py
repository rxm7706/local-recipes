"""Story 32.3 / spec-pyforge-scribe CAP-35 -- no live Spec is behind its memlog.

Ruling 1 of 2026-11-10 makes Dream plus memlog the seed. The deterministic half of fidelity is
small: an entry added to a Spec folder's ``.memlog.md`` after its ``SPEC.md`` was last rendered
means the Spec is behind. For each live Spec folder (a ``SPEC.md`` whose status is not absorbed,
archived or superseded: station Specs, declared seams and the Guild Specs under
``docs/governance/``), C is the commit that last changed ``SPEC.md``; an entry of the working-tree
memlog that the memlog at C does not hold, and that is not bookkeeping, is behind. Every
non-bookkeeping entry is judged, events included. No date is read from an entry's text or from
frontmatter: git dates everything.

Entries are parsed and classified by ``scripts/fleet_scan.py`` (``_parse_memlog_body`` and
``_memlog_entry_is_bookkeeping``), so the repository keeps one definition of "the contract moved";
this module defines none, and normalises a tag the way that function does (the kind is the text
before `` by ``). An uncommitted ``SPEC.md`` change counts as a render. In a shallow clone (CI
checks out two commits) C collapses to the base tip or the head, so the same rule judges exactly
the entries the change under test added without a render; the shrink rule (a known row that is no
longer behind fails) runs only with full history, which is the local merge bar.

Known rows live in ``data/spec_behind_memlog_known.json``: Spec folder -> rows of ``fingerprint``
(the first 16 hex digits of the SHA-256 of the entry line), ``kind``, ``committed`` (the date of the
commit that added the entry) and ``owner`` (the unit asked to re-derive). The file only shrinks.
Scribe's own Spec is judged with no known row. Nothing is re-derived here: the LLM comparison stays
``memlog-fidelity-check --compare``.

The module reads every station's Spec folders and ``scripts/``, so it is marked ``live_tree``; the
repository root is resolved only inside the tests, so collecting the package half outside the
repository imports nothing from it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.live_tree

KNOWN_FILE = Path(__file__).resolve().parent / "data" / "spec_behind_memlog_known.json"
SCRIBE_SPEC = "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe"
SPEC_GLOBS = (
    "_bmad-output/projects/*/planning-artifacts/specs/*/SPEC.md",
    "docs/governance/spec-*/SPEC.md",
)
NOT_LIVE = frozenset({"absorbed", "archived", "superseded"})
OWNERS = frozenset(
    {
        "atlas",
        "doctor",
        "herald",
        "marshal",
        "mason",
        "scribe",
        "steward-station",
        "warden",
        "core-kit",
        "control-plane",
        "governance",
    }
)
ROW_KEYS = frozenset({"fingerprint", "kind", "committed", "owner"})
_STATUS = re.compile(r"^status:\s*['\"]?([A-Za-z-]+)")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _git(root: Path, *args: str) -> str:
    """Run a read-only git command in ``root``; a hook's ``GIT_*`` variables never redirect it."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(["git", *args], cwd=root, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"git {' '.join(args)} failed in {root}: {result.stderr.strip()}"
    return result.stdout


@dataclass(frozen=True)
class Behind:
    """One memlog entry its Spec folder's SPEC.md has not followed."""

    folder: str
    fingerprint: str
    kind: str
    line: str


def fingerprint(line: str) -> str:
    """The first 16 hex digits of the SHA-256 of the entry line."""
    return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()[:16]


def entry_kind(tag: str) -> str:
    """The tag normalised as fleet_scan's classifier reads it: the kind is the text before `` by ``."""
    return tag.split(" by ", 1)[0].strip()


def is_shallow(root: Path) -> bool:
    return _git(root, "rev-parse", "--is-shallow-repository").strip() == "true"


def _status(spec: Path) -> str:
    lines = spec.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = _STATUS.match(line)
        if match:
            return match.group(1)
    return ""


def live_spec_folders(root: Path) -> list[str]:
    """Every Spec folder whose SPEC.md status is not absorbed, archived or superseded."""
    folders = {
        spec.parent.relative_to(root).as_posix()
        for pattern in SPEC_GLOBS
        for spec in root.glob(pattern)
        if _status(spec) not in NOT_LIVE
    }
    return sorted(folders)


def behind_entries(root: Path, folder: str) -> list[Behind]:
    """The working-tree memlog's entries that the memlog at SPEC.md's last commit lacks, bookkeeping aside."""
    from fleet_scan import _memlog_entry_is_bookkeeping, _parse_memlog_body

    memlog = root / folder / ".memlog.md"
    if not memlog.is_file():
        return []
    spec = f"{folder}/SPEC.md"
    if _git(root, "status", "--porcelain", "--", spec).strip():
        return []  # an uncommitted SPEC.md change counts as a render
    commit = _git(root, "log", "-1", "--format=%H", "--", spec).strip()
    memlog_rel = f"{folder}/.memlog.md"
    rendered = ""
    if commit and _git(root, "ls-tree", "--name-only", commit, "--", memlog_rel).strip():
        rendered = _git(root, "show", f"{commit}:{memlog_rel}")
    old = {line.strip() for line, _tag, _text in _parse_memlog_body(rendered)}
    behind: list[Behind] = []
    for line, tag, text in _parse_memlog_body(memlog.read_text(encoding="utf-8")):
        if line.strip() in old or _memlog_entry_is_bookkeeping(tag, text):
            continue
        behind.append(Behind(folder, fingerprint(line), entry_kind(tag), line.strip()))
    return behind


def load_known(path: Path) -> dict[str, list[dict[str, str]]]:
    """The known-rows file, its shape checked: folder -> non-empty rows with the four keys and a listed owner."""
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path.name}: expected an object of Spec folder -> rows"
    for folder, rows in data.items():
        assert isinstance(rows, list) and rows, f"{path.name}: {folder} holds no rows; drop the key"
        for row in rows:
            assert isinstance(row, dict) and set(row) == ROW_KEYS, f"{path.name}: {folder} row {row!r}"
            assert row["owner"] in OWNERS, f"{path.name}: {folder} row {row['fingerprint']} owner {row['owner']!r}"
    return data


def judge(root: Path, known: Mapping[str, list[dict[str, str]]], folders: list[str] | None = None) -> list[str]:
    """Every finding, each naming the Spec folder and the entry or the known row.

    A behind entry with no known row fails. With full history a known row that is no longer
    behind fails too (the file only shrinks); a shallow clone skips that rule, since there the
    rows older than the base tip are invisible.
    """
    full_history = not is_shallow(root)
    live = live_spec_folders(root) if folders is None else folders
    problems: list[str] = []
    for folder in live:
        rows = known.get(folder, [])
        allowed = {row["fingerprint"] for row in rows}
        entries = behind_entries(root, folder)
        problems += [
            f"{folder}: behind its memlog -- no SPEC.md render since this {entry.kind} entry "
            f"({entry.fingerprint}): {entry.line}"
            for entry in entries
            if entry.fingerprint not in allowed
        ]
        if full_history:
            current = {entry.fingerprint for entry in entries}
            problems += [
                f"{folder}: known row {row['fingerprint']} ({row['kind']}, owner {row['owner']}) is no longer "
                f"behind; drop it from {KNOWN_FILE.name}"
                for row in rows
                if row["fingerprint"] not in current
            ]
    if full_history and folders is None:
        problems += [
            f"{folder}: known rows for a folder that is not a live Spec folder; drop them from {KNOWN_FILE.name}"
            for folder in sorted(set(known) - set(live))
        ]
    return problems


# --- the live tree ---------------------------------------------------------------------------------


def test_live_tree_no_spec_is_behind_its_memlog() -> None:
    root = _repo_root()
    problems = judge(root, load_known(KNOWN_FILE))
    assert not problems, "Spec folders behind their memlog (re-derive the Spec with bmad-spec):\n" + "\n".join(problems)


def test_scribe_spec_is_judged_with_no_known_row() -> None:
    root = _repo_root()
    assert SCRIBE_SPEC in live_spec_folders(root), f"{SCRIBE_SPEC} is not a live Spec folder"
    assert SCRIBE_SPEC not in load_known(KNOWN_FILE), f"{SCRIBE_SPEC} takes no known row"
    problems = judge(root, {}, folders=[SCRIBE_SPEC])
    assert not problems, "\n".join(problems)


# --- planted fixture repositories -------------------------------------------------------------------

_SPEC_DIR = "_bmad-output/projects/pyforge-demo/planning-artifacts/specs/spec-pyforge-demo"
_SPEC_TEXT = "---\ntitle: demo\nstatus: ready\n---\n\n# Demo Spec\n"
_MEMLOG_HEAD = "---\ntitle: demo memlog\nupdated: 2026-01-01\n---\n\n"
_CAP_1 = "- (capability) CAP-1 (ready 2026-01-01) -- the first capability"


def _run(cwd: Path, *args: str) -> None:
    """A git write in a planted repository, isolated from the operator's and any hook's git config."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="fixture",
        GIT_AUTHOR_EMAIL="fixture@example.invalid",
        GIT_COMMITTER_NAME="fixture",
        GIT_COMMITTER_EMAIL="fixture@example.invalid",
    )
    result = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr.strip()}"


def _commit(repo: Path, message: str) -> None:
    _run(repo, "add", "-A")
    _run(repo, "commit", "-q", "-m", message)


def _write_folder(repo: Path, folder: str, spec_text: str, *entries: str) -> None:
    path = repo / folder
    path.mkdir(parents=True, exist_ok=True)
    (path / "SPEC.md").write_text(spec_text, encoding="utf-8")
    (path / ".memlog.md").write_text(_MEMLOG_HEAD + "".join(f"{entry}\n" for entry in entries), encoding="utf-8")


def _plant(tmp_path: Path, *entries: str) -> Path:
    """A repository whose one Spec folder's SPEC.md and memlog (holding ``entries``) land in one commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_folder(repo, _SPEC_DIR, _SPEC_TEXT, *entries)
    _run(repo, "init", "-q", "-b", "main")
    _commit(repo, "render the demo Spec")
    return repo


def _append(repo: Path, *entries: str, folder: str = _SPEC_DIR) -> None:
    with (repo / folder / ".memlog.md").open("a", encoding="utf-8") as handle:
        handle.writelines(f"{entry}\n" for entry in entries)


def _render(repo: Path, note: str) -> None:
    (repo / _SPEC_DIR / "SPEC.md").write_text(f"{_SPEC_TEXT}\n{note}\n", encoding="utf-8")


def _row(line: str, kind: str, owner: str = "scribe") -> dict[str, str]:
    return {"fingerprint": fingerprint(line), "kind": kind, "committed": "2026-01-02", "owner": owner}


def test_fixture_contract_entry_after_the_spec_commit_is_behind(tmp_path: Path) -> None:
    repo = _plant(tmp_path, _CAP_1)
    retired = "docs/governance/spec-retired-demo"
    _write_folder(repo, retired, _SPEC_TEXT.replace("status: ready", "status: superseded"))
    _commit(repo, "a superseded Spec")
    added = "- (capability) CAP-2 (ready 2026-01-02) -- added after the render"
    _append(repo, added)
    _append(repo, "- (decision) a superseded Spec is not judged", folder=retired)
    _commit(repo, "memlog only, no render")

    problems = judge(repo, {})

    assert len(problems) == 1, problems
    assert problems[0].startswith(f"{_SPEC_DIR}: behind its memlog")
    assert problems[0].endswith(added)


def test_fixture_entry_in_the_same_commit_as_the_spec_is_clean(tmp_path: Path) -> None:
    repo = _plant(tmp_path, _CAP_1)
    _append(repo, "- (decision) the Spec and this entry move in one commit")
    _render(repo, "Rendered with its entry.")
    _commit(repo, "render with its entry")
    assert judge(repo, {}) == []

    alone = "- (decision) this one moves alone"
    _append(repo, alone)
    _commit(repo, "memlog only")
    problems = judge(repo, {})
    assert len(problems) == 1 and problems[0].endswith(alone), problems


def test_fixture_bookkeeping_events_are_clean_and_other_events_are_judged(tmp_path: Path) -> None:
    repo = _plant(tmp_path, _CAP_1)
    _append(
        repo,
        "- (event) Surface reconcile 2026-01-03: src/demo/module.py moved under this Spec",
        "- (event by marshal) Story 3.2 landed (merge 0123abcd)",
    )
    _commit(repo, "bookkeeping only")
    assert judge(repo, {}) == []

    _append(repo, "- (event) Companion 2026-01-04: companions gains contract.md")
    _commit(repo, "a contract event")
    problems = judge(repo, {})
    assert len(problems) == 1, problems
    assert "this event entry" in problems[0]


def test_fixture_typed_tag_is_judged_as_its_kind(tmp_path: Path) -> None:
    repo = _plant(tmp_path, _CAP_1)
    _append(repo, "- (event by operator, 2026-09-14) Surface reconcile 2026-09-14: src/demo/module.py")
    _commit(repo, "a typed bookkeeping event")
    assert judge(repo, {}) == []

    _append(repo, "- (decision by operator, 2026-09-14) Retire the satellite")
    _commit(repo, "a typed decision")
    assert [entry.kind for entry in behind_entries(repo, _SPEC_DIR)] == ["decision"]
    problems = judge(repo, {})
    assert len(problems) == 1 and "this decision entry" in problems[0], problems


def test_fixture_known_row_is_tolerated(tmp_path: Path) -> None:
    repo = _plant(tmp_path, _CAP_1)
    line = "- (correction) CAP-1 reads CAP-2"
    _append(repo, line)
    _commit(repo, "memlog only")

    assert judge(repo, {_SPEC_DIR: [_row(line, "correction")]}) == []
    assert len(judge(repo, {})) == 1


def test_fixture_stale_known_row_fails_with_full_history(tmp_path: Path) -> None:
    repo = _plant(tmp_path, _CAP_1)
    line = "- (correction) CAP-1 reads CAP-2"
    _append(repo, line)
    _commit(repo, "memlog only")
    known = {_SPEC_DIR: [_row(line, "correction")]}
    assert judge(repo, known) == []

    _render(repo, "Re-derived.")
    _commit(repo, "re-derive the Spec")
    assert not is_shallow(repo)
    problems = judge(repo, known)
    assert len(problems) == 1, problems
    assert f"known row {fingerprint(line)}" in problems[0] and "no longer behind" in problems[0]
    assert judge(repo, {}) == []
    assert judge(repo, {"docs/governance/spec-gone": [_row(line, "correction")]}) == [
        f"docs/governance/spec-gone: known rows for a folder that is not a live Spec folder; drop them from "
        f"{KNOWN_FILE.name}"
    ]


def test_fixture_depth_two_clone_flags_the_change_and_skips_the_shrink_rule(tmp_path: Path) -> None:
    origin = _plant(tmp_path, _CAP_1)
    older = "- (decision) an entry the base tip already carried"
    _append(origin, older)
    _commit(origin, "base tip: memlog only")
    added = "- (direction) the change under test"
    _append(origin, added)
    _commit(origin, "head: memlog only")
    stale = "- (correction) a row a re-derive cleared"
    known = {_SPEC_DIR: [_row(older, "decision"), _row(stale, "correction")]}

    full = judge(origin, known)
    assert len(full) == 2 and full[0].endswith(added) and f"known row {fingerprint(stale)}" in full[1], full

    _run(tmp_path, "clone", "-q", "--depth", "2", origin.as_uri(), "clone")
    clone = tmp_path / "clone"
    assert is_shallow(clone)
    shallow = judge(clone, known)
    assert len(shallow) == 1 and shallow[0].endswith(added), shallow
    assert judge(clone, {_SPEC_DIR: [*known[_SPEC_DIR], _row(added, "direction")]}) == []


def test_fixture_uncommitted_spec_change_is_a_render(tmp_path: Path) -> None:
    repo = _plant(tmp_path, _CAP_1)
    _append(repo, "- (direction) the Spec should say more")
    assert len(judge(repo, {})) == 1

    _render(repo, "Rendered, not yet committed.")
    assert judge(repo, {}) == []
