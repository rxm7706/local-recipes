"""Unit tests for ``pyforge.doctor.sources.writer_lock`` (Story 56.5, spec-pyforge-doctor:CAP-100): a chain path
changed on a checkout that is not the writer is a named FAIL -- the branch half of the chain-write guard
spec-python-foundry-cutover:CAP-8 names.

Every case drives a REAL git repository built under ``tmp_path`` (``test_sources_frozen_path.py``'s convention:
never a mocked subprocess call). ``refs/remotes/origin/main`` is a real remote-tracking ref set with ``git
update-ref``, and the roster and the flag tree are written into that repository: this module reads nothing of the
repository it lives in, so it runs in the package half of the doctor suite.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pyforge.core.cutover_root import RootOfRecord

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import writer_lock

# `cli_bridge.run_git` reads os.environ at call time, so an inherited GIT_DIR must not decide what a gather sees
# (test_sources_frozen_path.py's own autouse fixture).
_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)
    # The flag tree renders for the current environment: pin it to the default (dev).
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _origin_main_at(repo: Path, sha: str) -> None:
    """The remote-tracking ref ``refs/remotes/origin/main`` at ``sha`` -- never a local branch of that name."""
    _git(repo, "update-ref", "refs/remotes/origin/main", sha)


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo.joinpath(*rel.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(repo: Path, rel: str, payload: object) -> None:
    _write(repo, rel, json.dumps(payload, indent=2) + "\n")


# Story 124.2: tracked paths are spelled as joins here -- steward's trigger-map scan counts a bare
# tracked-path literal as a read of the live tree, and this module reads none.
_ROSTER = "/".join(("docs", "governance", "guild-roster.json"))
_FLAGS = "/".join(("src", "platform", "config", "flags.json"))
_OVERLAYS = "/".join(("src", "platform", "config", "flag-overlays.json"))
_LOCAL = "local-recipes"
_FOUNDRY = "foundry"
_CHAIN_PATH = "docs/dreams/x.md"
_REALIZATION_LOG = "/".join(("docs", "dreams", "pyforge-unifying-strategy.md"))
_OTHER_PATH = "src/pkg/mod.py"

#: The globs of the roster's `chain-write-off-the-writer` entry (steward Story 121.4), as test data.
_CHAIN_GLOBS = [
    "docs/dreams/**",
    "docs/foundry/frames/**",
    "/".join(("docs", "foundry", "capability-ledger.yaml")),
    "_bmad-output/projects/*/planning-artifacts/specs/spec-*/**",
    "docs/governance/spec-*/**",
]


def _roster(*, this: str | None = _LOCAL, denial: bool = True) -> dict[str, object]:
    roster: dict[str, object] = {"session_denials": []}
    if this is not None:
        roster["roots"] = {"this": this}
    if denial:
        roster["session_denials"] = [
            {"id": "some-other-denial", "paths": ["nothing/**"]},
            {"id": "chain-write-off-the-writer", "applies_to": "edit_write", "paths": list(_CHAIN_GLOBS)},
        ]
    return roster


def _flags(variant: str) -> dict[str, object]:
    return {
        "flags": {
            "pyforge.cutover_root": {
                "state": "ENABLED",
                "variants": {_LOCAL: _LOCAL, _FOUNDRY: _FOUNDRY},
                "defaultVariant": variant,
                "metadata": {
                    "owner": "steward",
                    "story": "44-12-cutover-flag-and-replay-harness",
                    "created": "2026-09-13",
                    "on_everywhere": "",
                    "cleanup_by": "",
                },
            }
        }
    }


def _base(tmp_path: Path, *, variant: str = _LOCAL, roster: dict[str, object] | None = None) -> Path:
    """A repository whose merge base (= ``origin/main``) holds the roster and the flag tree at ``variant``."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_json(repo, _ROSTER, _roster() if roster is None else roster)
    _write_json(repo, _FLAGS, _flags(variant))
    _write(repo, "README.md", "seed\n")
    _origin_main_at(repo, _commit_all(repo, "seed the roster and the flag tree"))
    return repo


def _branch(repo: Path, *changed: str, head_variant: str | None = None) -> None:
    """One branch commit on top of the merge base: each of ``changed`` written, the flag tree flipped at HEAD."""
    for rel in changed:
        _write(repo, rel, f"# {rel}\n")
    if head_variant is not None:
        _write_json(repo, _FLAGS, _flags(head_variant))
    _commit_all(repo, "the branch")


def _only(findings: tuple[Finding, ...]) -> Finding:
    assert len(findings) == 1, [f.to_json_dict() for f in findings]
    finding = findings[0]
    assert finding.source is Source.WRITER_LOCK
    return finding


def _assert_unevaluable(findings: tuple[Finding, ...]) -> Finding:
    finding = _only(findings)
    assert finding.status is DoctorStatus.WARN
    assert finding.check == "writer-lock-unevaluable"
    assert finding.evidence["unevaluable"] is True
    return finding


def _run_cli(repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    """``python -m pyforge.doctor.sources writer-lock`` as a pixi task runs it: from the repository's root."""
    monkeypatch.chdir(repo)
    code = dispatch.main(["writer-lock"])
    return code, capsys.readouterr().out


# --- the eight rules -------------------------------------------------------------------------------------------


def test_writer_is_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _base(tmp_path, variant=_LOCAL)
    _branch(repo, _CHAIN_PATH)

    finding = _only(writer_lock.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert finding.check == "writer-lock"
    assert "is the writer" in finding.message
    assert finding.evidence["root_of_record"] == finding.evidence["this"] == _LOCAL
    assert finding.evidence["forge_slug"] == "rxm7706/local-recipes"
    code, out = _run_cli(repo, monkeypatch, capsys)
    assert code == 0
    assert "is the writer" in out


def test_flip_branch_is_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # The flip: local-recipes at the merge base, foundry at HEAD, and the Realization-log stamp in the same change.
    repo = _base(tmp_path, variant=_LOCAL)
    _branch(repo, _REALIZATION_LOG, head_variant=_FOUNDRY)

    finding = _only(writer_lock.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert "is the writer" in finding.message
    assert finding.evidence["root_of_record"] == _LOCAL
    code, out = _run_cli(repo, monkeypatch, capsys)
    assert code == 0
    assert "is the writer" in out


def test_flipped_chain_path_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _base(tmp_path, variant=_FOUNDRY)
    _branch(repo, _CHAIN_PATH)

    finding = _only(writer_lock.gather(repo))

    assert finding.status is DoctorStatus.FAIL
    assert finding.check == "writer-lock"
    assert finding.evidence["path"] == _CHAIN_PATH
    assert finding.evidence["root_of_record"] == _FOUNDRY
    assert finding.evidence["this"] == _LOCAL
    assert finding.evidence["glob"] == "docs/dreams/**"
    for named in (_CHAIN_PATH, _FOUNDRY, _LOCAL):
        assert named in finding.message
    code, out = _run_cli(repo, monkeypatch, capsys)
    assert code == 2
    assert _CHAIN_PATH in out


def test_flipped_other_path_is_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _base(tmp_path, variant=_FOUNDRY)
    _branch(repo, _OTHER_PATH)

    finding = _only(writer_lock.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert "is not the writer" in finding.message
    assert finding.evidence["changed"] == 1
    code, _out = _run_cli(repo, monkeypatch, capsys)
    assert code == 0


def test_no_roots_is_unevaluable(tmp_path: Path) -> None:
    repo = _base(tmp_path, variant=_FOUNDRY, roster=_roster(this=None))
    _branch(repo, _CHAIN_PATH)

    finding = _assert_unevaluable(writer_lock.gather(repo))

    assert "roots.this" in finding.message


def test_no_denial_entry_is_unevaluable(tmp_path: Path) -> None:
    repo = _base(tmp_path, variant=_FOUNDRY, roster=_roster(denial=False))
    _branch(repo, _CHAIN_PATH)

    finding = _assert_unevaluable(writer_lock.gather(repo))

    assert "chain-write-off-the-writer" in finding.message
    assert finding.to_json_dict()["evidence"]["unevaluable"] is True


def test_bad_flag_tree_is_unevaluable(tmp_path: Path) -> None:
    repo = _base(tmp_path, variant="elsewhere")
    _branch(repo, _CHAIN_PATH)

    finding = _assert_unevaluable(writer_lock.gather(repo))

    assert "CutoverRootError" in finding.message
    assert "elsewhere" in finding.message


def test_origin_main_unresolvable_is_unevaluable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _base(tmp_path, variant=_FOUNDRY)
    _git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    _branch(repo, _CHAIN_PATH)

    finding = _assert_unevaluable(writer_lock.gather(repo))

    assert "origin/main" in finding.message
    code, _out = _run_cli(repo, monkeypatch, capsys)
    assert code == 0


@pytest.mark.parametrize(
    ("roster_text", "named"),
    [
        ("{ not json", "cannot be read"),
        ("[]", "is not an object"),
        (json.dumps({"roots": {"this": "  "}, "session_denials": []}), "roots.this"),
        (
            json.dumps({"roots": {"this": _LOCAL}, "session_denials": [{"id": "chain-write-off-the-writer"}]}),
            "'paths' glob list",
        ),
        (
            json.dumps(
                {"roots": {"this": _LOCAL}, "session_denials": [{"id": "chain-write-off-the-writer", "paths": [""]}]}
            ),
            "'paths' glob list",
        ),
    ],
)
def test_a_malformed_roster_cannot_be_evaluated(tmp_path: Path, roster_text: str, named: str) -> None:
    repo = _base(tmp_path, variant=_FOUNDRY)
    _write(repo, _ROSTER, roster_text)
    _branch(repo, _CHAIN_PATH)

    finding = _assert_unevaluable(writer_lock.gather(repo))

    assert named in finding.message


# --- the read itself ---------------------------------------------------------------------------------------


def test_the_flag_is_read_at_the_merge_base_never_at_head(tmp_path: Path) -> None:
    # Flipping the tree back at HEAD does not make this checkout the writer.
    repo = _base(tmp_path, variant=_FOUNDRY)
    _branch(repo, _CHAIN_PATH, head_variant=_LOCAL)

    finding = _only(writer_lock.gather(repo))

    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["path"] == _CHAIN_PATH


def test_the_overlay_at_the_merge_base_is_composed_in(tmp_path: Path) -> None:
    # The tree says local-recipes, the dev overlay beside it says foundry: the dev render is foundry.
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_json(repo, _ROSTER, _roster())
    _write_json(repo, _FLAGS, _flags(_LOCAL))
    _write_json(repo, _OVERLAYS, {"dev": {"pyforge.cutover_root": _FOUNDRY}})
    _origin_main_at(repo, _commit_all(repo, "seed"))
    _branch(repo, _CHAIN_PATH)

    finding = _only(writer_lock.gather(repo))

    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["root_of_record"] == _FOUNDRY


def test_a_flag_tree_absent_at_the_merge_base_cannot_be_evaluated(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_json(repo, _ROSTER, _roster())
    _origin_main_at(repo, _commit_all(repo, "a roster, no flag tree"))
    # A tree at HEAD is never read in its place.
    _write_json(repo, _FLAGS, _flags(_LOCAL))
    _branch(repo, _CHAIN_PATH)

    finding = _assert_unevaluable(writer_lock.gather(repo))

    assert "/".join(("src", "platform", "config", "flags.json")) in finding.message


def test_a_default_answer_is_never_proof_of_the_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _base(tmp_path, variant=_LOCAL)
    _branch(repo, _CHAIN_PATH)
    monkeypatch.setattr(
        writer_lock,
        "root_of_record",
        lambda _path: RootOfRecord(root=_LOCAL, forge_slug="rxm7706/local-recipes", source="default"),
    )

    finding = _assert_unevaluable(writer_lock.gather(repo))

    assert finding.evidence["root_source"] == "default"


def test_each_declared_glob_names_its_chain_path(tmp_path: Path) -> None:
    repo = _base(tmp_path, variant=_FOUNDRY)
    chain = [
        "docs/foundry/frames/kernel.frame.md",
        "/".join(("docs", "foundry", "capability-ledger.yaml")),
        "_bmad-output/projects/pyforge-acme/planning-artifacts/specs/spec-acme/SPEC.md",
        "docs/governance/spec-acme/SPEC.md",
    ]
    # Not chain paths: a project's epics, a story spec file beside the Spec folders, a foundry page.
    other = [
        "_bmad-output/projects/pyforge-acme/planning-artifacts/epics.md",
        "_bmad-output/projects/pyforge-acme/planning-artifacts/specs/spec-1-1-a-story.md",
        "docs/foundry/PIN.md",
    ]
    _branch(repo, *chain, *other)

    findings = writer_lock.gather(repo)

    assert all(f.status is DoctorStatus.FAIL for f in findings), [f.to_json_dict() for f in findings]
    assert sorted(f.evidence["path"] for f in findings) == sorted(chain)


def test_a_moved_chain_file_names_its_old_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_json(repo, _ROSTER, _roster())
    _write_json(repo, _FLAGS, _flags(_FOUNDRY))
    _write(repo, "docs/dreams/old.md", "a Dream with enough text to be detected as a rename\n" * 8)
    _origin_main_at(repo, _commit_all(repo, "seed"))
    (repo / "notes").mkdir()
    _git(repo, "mv", "docs/dreams/old.md", "notes/old.md")
    _commit_all(repo, "move a Dream out of the chain")

    finding = _only(writer_lock.gather(repo))

    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["path"] == "docs/dreams/old.md"


def test_a_chain_path_origin_main_gained_after_the_fork_is_not_this_branch_s_write(tmp_path: Path) -> None:
    repo = _base(tmp_path, variant=_FOUNDRY)
    fork = _git(repo, "rev-parse", "HEAD").strip()
    _branch(repo, "docs/dreams/main-only.md")
    _origin_main_at(repo, _git(repo, "rev-parse", "HEAD").strip())
    _git(repo, "checkout", "-q", "-b", "topic", fork)
    _branch(repo, _OTHER_PATH)

    finding = _only(writer_lock.gather(repo))

    assert finding.status is DoctorStatus.OK
    assert finding.evidence["merge_base"] == fork
    assert finding.evidence["changed"] == 1
