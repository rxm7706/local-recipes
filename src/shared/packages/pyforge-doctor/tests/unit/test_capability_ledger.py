"""Story 55.2 — CAP extract detector (fcl:CAP-2)."""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import capability_ledger
from pyforge.doctor.sources.capability_ledger import (
    UNIQUE_WHY_FIXTURE_SENTENCE,
    extract_caps,
    gather,
    parse_case_list_ids,
)

_FIXTURE_SPEC = f"""---
spec: fixture-ledger-spec
status: ready
---

# SPEC — fixture

## Why

**A pain to solve.** {UNIQUE_WHY_FIXTURE_SENTENCE}

## Capabilities

- **CAP-9 — Example capability.**
  - **intent:** classify this heading extract only
  - **success:** CAP-9 is visible and Why is not stored
"""


def test_extract_sees_cap_9_not_unique_why_sentence():
    rows = extract_caps(_FIXTURE_SPEC)
    assert [(n, heading) for n, heading, _i, _s in rows] == [
        (9, "Example capability"),
    ]
    blob = "\n".join(f"{heading}\n{intent}\n{success}" for _n, heading, intent, success in rows)
    assert "CAP-9" not in blob or "Example capability" in blob
    assert UNIQUE_WHY_FIXTURE_SENTENCE not in blob
    assert "classify this heading extract only" in blob
    assert "CAP-9 is visible and Why is not stored" in blob


def test_parse_case_list_ids_from_54_1_surface():
    repo = Path(__file__).resolve().parents[6]
    text = (
        repo / "_bmad-output/projects/pyforge-steward/planning-artifacts/"
        "specs/spec-foundry-regenerate-not-fold/case-list.md"
    ).read_text(encoding="utf-8")
    ids = parse_case_list_ids(text)
    assert "k-core-cutover-default" in ids
    assert "k-steward-help" in ids
    assert "k-marshal-no-sysexit" in ids
    assert ids


def test_module_never_calls_node_from_text_file():
    source = inspect.getsource(capability_ledger)
    assert "_node_from_text_file" not in source
    assert "20000" not in source


def _write_spec(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_ledger(root: Path, capabilities: list[dict], source_sha: str = "") -> None:
    path = root / "docs" / "foundry" / "capability-ledger.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "pyforge.capability-ledger/v0",
        "source_sha": source_sha,
        "capabilities": capabilities,
    }
    import yaml

    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_unclassified_cap_is_hard(tmp_path: Path):
    rel = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-fixture-ledger-spec/SPEC.md"
    _write_spec(tmp_path, rel, _FIXTURE_SPEC)
    _write_ledger(tmp_path, [])
    findings = gather(tmp_path)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert fails
    assert any("unclassified" in f.message for f in fails)
    assert all(f.source is Source.CAPABILITY_LEDGER for f in findings)


def test_a_only_without_expiry_is_hard(tmp_path: Path):
    rel = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-fixture-ledger-spec/SPEC.md"
    _write_spec(tmp_path, rel, _FIXTURE_SPEC)
    _write_ledger(
        tmp_path,
        [
            {
                "id": "fixture-ledger-spec:CAP-9",
                "spec": "fixture-ledger-spec",
                "mode": "A-only",
                "path": rel,
            }
        ],
    )
    findings = gather(tmp_path)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert any("A-only without expiry" in f.message for f in fails)


def test_classified_a_only_with_expiry_is_ok(tmp_path: Path):
    rel = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-fixture-ledger-spec/SPEC.md"
    _write_spec(tmp_path, rel, _FIXTURE_SPEC)
    _write_ledger(
        tmp_path,
        [
            {
                "id": "fixture-ledger-spec:CAP-9",
                "spec": "fixture-ledger-spec",
                "mode": "A-only",
                "expiry": "2026-12-31",
                "path": rel,
            }
        ],
    )
    findings = gather(tmp_path)
    assert [f.status for f in findings] == [DoctorStatus.OK]


_CASE_LIST_REL = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md"
)
_SPEC_REL = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-fixture-ledger-spec/SPEC.md"


def _write_case_list(root: Path, ids: tuple[str, ...] = ("k-core-cutover-default",)) -> None:
    path = root / _CASE_LIST_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"| {cid} | core | node | pass | — |" for cid in ids)
    path.write_text(
        "# Thin oracle\n\n| id | slice | argv / nodeid | expected row | A-only expiry |\n"
        "|---|---|---|---|---|\n"
        f"{rows}\n",
        encoding="utf-8",
    )


def _classified_row(**extra: object) -> dict:
    row: dict = {
        "id": "fixture-ledger-spec:CAP-9",
        "spec": "fixture-ledger-spec",
        "mode": "rebuild",
        "path": _SPEC_REL,
    }
    row.update(extra)
    return row


def test_verified_without_case_id_is_hard(tmp_path: Path):
    _write_spec(tmp_path, _SPEC_REL, _FIXTURE_SPEC)
    _write_case_list(tmp_path)
    _write_ledger(
        tmp_path,
        [_classified_row(state="verified-in-foundry")],
    )
    findings = gather(tmp_path)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert any("without a case-list id" in f.message for f in fails)


def test_verified_with_listed_id_is_not_hard_for_this_reason(tmp_path: Path):
    _write_spec(tmp_path, _SPEC_REL, _FIXTURE_SPEC)
    _write_case_list(tmp_path)
    _write_ledger(
        tmp_path,
        [
            _classified_row(
                state="verified-in-foundry",
                case_id="k-core-cutover-default",
            )
        ],
    )
    findings = gather(tmp_path)
    assert not any(f.evidence.get("kind", "").startswith("verified-") for f in findings)
    assert [f.status for f in findings] == [DoctorStatus.OK]


def test_verified_frame_preflight_is_hard(tmp_path: Path):
    _write_spec(tmp_path, _SPEC_REL, _FIXTURE_SPEC)
    _write_case_list(tmp_path)
    _write_ledger(
        tmp_path,
        [
            _classified_row(
                state="verified-in-foundry",
                case_id="docs/foundry/frames/pyforge.frame.md",
            )
        ],
    )
    findings = gather(tmp_path)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert any("not a 54.1 case-list id" in f.message for f in fails)


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        text=True,
    ).strip()


def test_post_pin_spec_without_row_is_append(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "55.2@example.test")
    _git(repo, "config", "user.name", "Story 55.2")
    (repo / "README.md").write_text("pin\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "pin")
    pin = _git(repo, "rev-parse", "HEAD")

    rel = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-fixture-ledger-spec/SPEC.md"
    _write_spec(repo, rel, _FIXTURE_SPEC)
    _write_ledger(repo, [], source_sha=pin)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "post-pin spec")

    findings = gather(repo)
    warns = [f for f in findings if f.status is DoctorStatus.WARN]
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not fails
    assert any("--append" in f.message for f in warns)
    assert any(f.evidence.get("kind") == "append" for f in warns)


def _pinned_repo(tmp_path: Path) -> tuple[Path, str]:
    """A throwaway git repo whose first commit is the ledger PIN."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "35.1@example.test")
    _git(repo, "config", "user.name", "Story 35.1")
    (repo / "README.md").write_text("pin\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "pin")
    return repo, _git(repo, "rev-parse", "HEAD")


def _post_pin_spec(status: str | None, *, with_cap: bool) -> str:
    frontmatter = "spec: fixture-ledger-spec\n" + (f"status: {status}\n" if status else "")
    cap = (
        "\n- **CAP-9 — Example capability.**\n"
        "  - **intent:** classify this heading extract only\n"
        "  - **success:** CAP-9 is visible\n"
        if with_cap
        else "\nNo capability heading here.\n"
    )
    return f"---\n{frontmatter}---\n\n# SPEC — fixture\n{cap}"


def _commit_post_pin_spec(
    repo: Path,
    pin: str,
    body: str,
    *,
    rows: list[dict] | None = None,
) -> None:
    _write_spec(repo, _SPEC_REL, body)
    _write_ledger(repo, rows or [], source_sha=pin)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "post-pin spec")


@pytest.mark.parametrize("status", ["absorbed", "draft", "shipped", None])
def test_post_pin_non_live_spec_reports_nothing(tmp_path: Path, status: str | None):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(repo, pin, _post_pin_spec(status, with_cap=True))

    findings = gather(repo)

    assert [f.status for f in findings] == [DoctorStatus.OK]


def test_post_pin_live_spec_without_cap_or_row_is_one_append_warn(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(repo, pin, _post_pin_spec("ready", with_cap=False))

    findings = gather(repo)

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].evidence == {"kind": "append", "path": _SPEC_REL}
    assert _SPEC_REL in findings[0].message


def test_post_pin_in_progress_spec_with_unclassified_cap_keeps_per_cap_warn(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(repo, pin, _post_pin_spec("in-progress", with_cap=True))

    findings = gather(repo)

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].message == "fixture-ledger-spec:CAP-9: post-PIN unclassified --append"
    assert findings[0].evidence["kind"] == "append"


def test_post_pin_live_spec_with_a_row_for_its_path_reports_nothing(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(
        repo,
        pin,
        _post_pin_spec("ready", with_cap=False),
        rows=[_classified_row(id="fixture-ledger-spec:CAP-1")],
    )

    findings = gather(repo)

    assert [f.status for f in findings] == [DoctorStatus.OK]


def test_post_pin_spec_gone_from_working_tree_reports_nothing(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(repo, pin, _post_pin_spec("ready", with_cap=False))
    # Committed after the PIN, then deleted without a commit: still in ``PIN..HEAD``.
    (repo / _SPEC_REL).unlink()

    findings = gather(repo)

    # ``gather`` degrades an unguarded read into a finding, so assert no non-OK finding at all.
    assert [f.status for f in findings] == [DoctorStatus.OK]


def test_post_pin_non_live_spec_does_not_mask_a_live_one(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    specs = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
    live_rel = f"{specs}/spec-z-live/SPEC.md"
    # ``sorted(added)`` walks the absorbed Spec first; skipping it must not end the loop.
    _write_spec(repo, f"{specs}/spec-a-absorbed/SPEC.md", _post_pin_spec("absorbed", with_cap=False))
    _write_spec(repo, live_rel, _post_pin_spec("ready", with_cap=False))
    _write_ledger(repo, [], source_sha=pin)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "post-pin specs")

    findings = gather(repo)

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].evidence == {"kind": "append", "path": live_rel}


def test_post_pin_spec_present_but_unreadable_degrades_not_skips(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    # Off the inventory glob (``specs/*/SPEC.md``), so ``iter_live_specs`` never reads it first.
    rel = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-fixture-ledger-spec/nested/SPEC.md"
    _write_spec(repo, rel, _post_pin_spec("ready", with_cap=False))
    _write_ledger(repo, [], source_sha=pin)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "post-pin spec")
    (repo / rel).unlink()
    (repo / rel).mkdir()  # present but not a file: only a *gone* path is skipped

    findings = gather(repo)

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "could not be evaluated" in findings[0].message
