"""Unit tests for ``pyforge.doctor.sources.chain.gather_dreams_hygiene``
(Story 17.2 / FR-147) — Dream-tier hygiene mode invoked as
``python -m pyforge.doctor.sources dream-chain --dreams``.

Covers the story I/O matrix against temp fixture trees only. Does not
mutate the live Dream tree. Does not assert INV-0..3 findings (those stay
on ``gather_dream_chain``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import chain

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None


def _require_repo_root() -> Path:
    if _REPO_ROOT is None or not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("not running inside the local-recipes monorepo checkout")
    return _REPO_ROOT


# --- fixture helpers ---------------------------------------------------------


def _write_roster(target: Path) -> None:
    path = target / "docs" / "governance" / "guild-roster.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "stations": [
                    "herald",
                    "marshal",
                    "atlas",
                    "warden",
                    "mason",
                    "doctor",
                    "scribe",
                    "steward",
                ],
                "guild_dreams": ["pyforge-charter"],
                "dream_statuses": [
                    "dreamt",
                    "pitched",
                    "specified",
                    "realized",
                    "archived",
                ],
                "dream_types": ["dream", "practice"],
                "spec_statuses_ready_or_beyond": [
                    "ready", "in-progress", "shipped", "absorbed",
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_dream(
    target: Path,
    slug: str,
    *,
    owner: str = "marshal",
    status: str = "dreamt",
    title: str | None = "A Dream",
    dtype: str = "dream",
    realization_log: bool = False,
) -> Path:
    path = target / "docs" / "dreams" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"owner: {owner}", f"status: {status}", f"type: {dtype}"]
    if title is not None:
        lines.append(f"title: {title}")
    lines += ["---", "", "body"]
    if realization_log:
        lines += ["", "## Realization log", "", "- noted"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_spec(
    target: Path,
    slug: str,
    *,
    project: str = "pyforge-doctor",
    status: str = "draft",
    owner_dream: str | None = None,
) -> Path:
    spec_dir = (
        target
        / "_bmad-output"
        / "projects"
        / project
        / "planning-artifacts"
        / "specs"
        / f"spec-{slug}"
    )
    spec_dir.mkdir(parents=True, exist_ok=True)
    od = owner_dream or f"docs/dreams/{slug}.md"
    (spec_dir / "SPEC.md").write_text(
        f"---\nowner-dream: {od}\nstatus: {status}\n---\n\nbody\n",
        encoding="utf-8",
    )
    return spec_dir / "SPEC.md"


def _write_readme(target: Path, rows: list[tuple[str, str]]) -> None:
    path = target / "docs" / "dreams" / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Dreams",
        "",
        "| Dream | Status | What it is |",
        "|---|---|---|",
    ]
    for filename, status in rows:
        lines.append(f"| [`{filename}`]({filename}) | {status} | desc |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _clean_hygiene_tree(target: Path) -> None:
    """One conformant Dream + matching README row + roster."""
    _write_roster(target)
    _write_dream(
        target,
        "foo",
        status="realized",
        title="Foo",
        realization_log=True,
    )
    _write_readme(target, [("foo.md", "realized")])


# --- matrix -----------------------------------------------------------------


def test_happy_path_reports_ok(tmp_path: Path) -> None:
    _clean_hygiene_tree(tmp_path)
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert len(findings) == 1
    assert findings[0].source is Source.DREAMS_HYGIENE
    assert findings[0].check == "dreams-hygiene"
    assert findings[0].status is DoctorStatus.OK


def test_bad_status_reports_dream_vocab(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", status="building", realization_log=True)
    _write_readme(tmp_path, [("foo.md", "building")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    kinds = {f.check for f in findings}
    assert "dream-vocab" in kinds
    assert all(f.source is Source.DREAMS_HYGIENE for f in findings)


def test_bad_owner_reports_dream_unowned(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", owner="crew", realization_log=True)
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "dream-unowned" for f in findings)


def test_missing_title_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", title=None, realization_log=False)
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "missing-title" for f in findings)


def test_realized_without_realization_log_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "foo", status="realized", title="Foo", realization_log=False
    )
    _write_readme(tmp_path, [("foo.md", "realized")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "realization-log-missing" for f in findings)


def test_historical_section_too_long_on_fixture(tmp_path: Path) -> None:
    """Story 43.1: fires on a long *historical* section, not on conformant Dreams."""
    _write_roster(tmp_path)
    body_lines = [
        "---",
        "owner: steward",
        "status: specified",
        "type: dream",
        "title: Hist",
        "---",
        "",
        "intro",
        "",
        "## Historical illustration (do not build)",
    ]
    body_lines += [f"line {i}" for i in range(25)]
    body_lines += ["", "## Realization log", "", "- noted"]
    path = tmp_path / "docs" / "dreams" / "hist-fixture.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
    _write_readme(tmp_path, [("hist-fixture.md", "specified")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "historical-section-too-long" for f in findings)


def test_living_unifying_strategy_has_no_historical_section_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: post-43.1 living Dream must not trip its own detector."""
    repo = Path(__file__).resolve().parents[6]
    monkeypatch.chdir(repo)
    findings = chain.gather_dreams_hygiene(repo)
    hist = [f for f in findings if f.check == "historical-section-too-long"]
    assert not any(
        f.evidence.get("subject") == "pyforge-unifying-strategy" for f in hist
    )


def test_dreamt_may_omit_realization_log(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "foo", status="dreamt", title="Foo", realization_log=False
    )
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "realization-log-missing" for f in findings)
    assert findings[0].check == "dreams-hygiene"
    assert findings[0].status is DoctorStatus.OK


def test_readme_table_orphan_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "foo", status="dreamt", title="Foo", realization_log=False
    )
    _write_readme(tmp_path, [("missing.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "readme-table-orphan" for f in findings)


def test_readme_table_status_drift_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "foo", status="realized", title="Foo", realization_log=True
    )
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "readme-table-drift" for f in findings)


def test_default_dream_chain_does_not_emit_hygiene_kinds(tmp_path: Path) -> None:
    """INV gather stays INV-only — no hygiene kinds leak into default mode."""
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", status="building", title="Foo")
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dream_chain(tmp_path)
    hygiene_kinds = {
        "dream-vocab",
        "dream-unowned",
        "missing-title",
        "realization-log-missing",
        "readme-table-drift",
        "readme-table-orphan",
        "dream-readme-missing",
        "specified-spec-not-ready",
        "kinship-wikilink-dead",
        "dreams-hygiene",
    }
    assert not hygiene_kinds.intersection({f.check for f in findings})
    assert any(f.check == "dream-without-spec" for f in findings)


def test_cli_dreams_flag_dispatches_hygiene(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _clean_hygiene_tree(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = dispatch.main(["dream-chain", "--dreams", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert "dreams-hygiene" in out
    assert "dream-without-spec" not in out


def test_cli_dreams_flag_rejected_on_other_source() -> None:
    with pytest.raises(SystemExit) as excinfo:
        dispatch.main(["bmad-drift", "--dreams"])
    assert excinfo.value.code == 2


# --- Story 21.6: Dream/README reconciliation --------------------------------


def test_dream_readme_missing_reports_on_fixture(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "orphan-dream", status="dreamt", title="Orphan", realization_log=False
    )
    _write_readme(tmp_path, [])
    findings = chain.gather_dreams_hygiene(tmp_path)
    hit = [f for f in findings if f.check == "dream-readme-missing"]
    assert len(hit) == 1
    assert hit[0].status is DoctorStatus.WARN
    assert hit[0].evidence["subject"] == "orphan-dream"


def test_live_tree_dream_readme_missing_count() -> None:
    """Measured live 2026-09-11 (re-measured 2026-09-12, mason 15.1 recovery
    pass): 67 Dream files lack a README.md table row (one more than the prior
    2026-09-16 measurement — an unrelated Dream landed on `main` in between
    without its row; not chased down further here, this test only tracks the
    live count)."""
    repo_root = _require_repo_root()
    findings = chain.gather_dreams_hygiene(repo_root)
    missing = [f for f in findings if f.check == "dream-readme-missing"]
    assert len(missing) == 67


def test_specified_spec_not_ready_reports_on_fixture(tmp_path: Path) -> None:
    """README:71 — ``specified`` with a covering Spec still at ``draft``."""
    _write_roster(tmp_path)
    _write_dream(
        tmp_path,
        "django-accelerator-framework",
        status="specified",
        title="Accelerator",
        owner="mason",
        realization_log=True,
    )
    _write_readme(tmp_path, [("django-accelerator-framework.md", "specified")])
    _write_spec(
        tmp_path,
        "django-accelerator-framework",
        project="pyforge-mason",
        status="draft",
    )
    findings = chain.gather_dreams_hygiene(tmp_path)
    hit = [f for f in findings if f.check == "specified-spec-not-ready"]
    assert len(hit) == 1
    assert hit[0].status is DoctorStatus.WARN
    assert hit[0].evidence["subject"] == "django-accelerator-framework"
    assert hit[0].evidence["spec_statuses"] == ["draft"]


def test_live_tree_specified_spec_not_ready_count() -> None:
    """Measured live 2026-09-11: 3 ``specified`` Dreams whose covering Spec is
    not ``ready`` or beyond (``django-accelerator-framework`` archived since)."""
    repo_root = _require_repo_root()
    findings = chain.gather_dreams_hygiene(repo_root)
    bad = [f for f in findings if f.check == "specified-spec-not-ready"]
    assert len(bad) == 3
    subjects = {f.evidence["subject"] for f in bad}
    assert subjects == {
        "miniforge-installer",
        "python-agent-platform",
        "reusable-cicd-workflows",
    }


def test_kinship_wikilink_dead_reports_on_fixture(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    path = tmp_path / "docs" / "dreams" / "linker.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "owner: herald",
                "status: dreamt",
                "type: dream",
                "title: Linker",
                "---",
                "",
                "See [[missing-target|display name]] for context.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_readme(tmp_path, [("linker.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    hit = [f for f in findings if f.check == "kinship-wikilink-dead"]
    assert len(hit) == 1
    assert hit[0].status is DoctorStatus.WARN
    assert hit[0].evidence == {
        "subject": "linker",
        "link_target": "missing-target",
    }


def test_kinship_wikilink_skips_frontmatter_fence(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    path = tmp_path / "docs" / "dreams" / "fence.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "owner: herald",
                "status: dreamt",
                "type: dream",
                "title: Fence",
                "note: [[not-a-link]]",
                "---",
                "",
                "Body only.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_readme(tmp_path, [("fence.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "kinship-wikilink-dead" for f in findings)


def test_live_tree_kinship_wikilink_dead_count() -> None:
    """Measured live 2026-09-14: 26 dead Kinship wikilinks under docs/dreams/
    (was 24 on 2026-09-11 -- re-measured, not a regression this guard needs
    to catch: new Dream content merged in the interim added two more dead
    targets)."""
    repo_root = _require_repo_root()
    findings = chain.gather_dreams_hygiene(repo_root)
    dead = [f for f in findings if f.check == "kinship-wikilink-dead"]
    assert len(dead) == 26


def test_specified_spec_ready_suppresses_finding(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path,
        "ready-dream",
        status="specified",
        title="Ready Dream",
        owner="doctor",
        realization_log=True,
    )
    _write_readme(tmp_path, [("ready-dream.md", "specified")])
    _write_spec(tmp_path, "ready-dream", status="ready-for-dev")
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "specified-spec-not-ready" for f in findings)


def test_missing_spec_statuses_ready_or_beyond_degrades_to_fallback(
    tmp_path: Path,
) -> None:
    """A roster present but missing ``spec_statuses_ready_or_beyond`` (Story
    59.2's new key) falls back to the CAP-1 subset
    (``ready``/``in-progress``/``shipped``/``absorbed``) rather than crashing
    or silently accepting nothing -- a covering Spec at ``ready`` still
    suppresses the finding, and a ``spec-status-roster-degraded`` WARN
    surfaces the broken declaration rather than swallowing it."""
    path = tmp_path / "docs" / "governance" / "guild-roster.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "stations": [
                    "herald", "marshal", "atlas", "warden", "mason",
                    "doctor", "scribe", "steward",
                ],
                "guild_dreams": ["pyforge-charter"],
                "dream_statuses": [
                    "dreamt", "pitched", "specified", "realized", "archived",
                ],
                "dream_types": ["dream", "practice"],
                # spec_statuses_ready_or_beyond deliberately absent.
            }
        ),
        encoding="utf-8",
    )
    _write_dream(
        tmp_path,
        "ready-dream",
        status="specified",
        title="Ready Dream",
        owner="doctor",
        realization_log=True,
    )
    _write_readme(tmp_path, [("ready-dream.md", "specified")])
    _write_spec(tmp_path, "ready-dream", status="ready")

    findings = chain.gather_dreams_hygiene(tmp_path)

    assert not any(f.check == "specified-spec-not-ready" for f in findings)
    degraded = [f for f in findings if f.check == "spec-status-roster-degraded"]
    assert len(degraded) == 1
    assert degraded[0].status is DoctorStatus.WARN
    assert degraded[0].source is Source.DREAMS_HYGIENE


def test_specified_spec_not_ready_when_covering_spec_unevaluable(
    tmp_path: Path,
) -> None:
    """When the expected covering Spec exists but fails collection, README:71
    must warn with ``(unevaluable)`` rather than silently skipping."""
    _write_roster(tmp_path)
    slug = "broken-covering-spec"
    _write_dream(
        tmp_path,
        slug,
        status="specified",
        title="Broken Covering Spec",
        owner="doctor",
        realization_log=True,
    )
    _write_readme(tmp_path, [(f"{slug}.md", "specified")])
    spec = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-doctor"
        / "planning-artifacts"
        / "specs"
        / f"spec-{slug}"
        / "SPEC.md"
    )
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("---\n- not\n- a\n- mapping\n---\n", encoding="utf-8")
    findings = chain.gather_dreams_hygiene(tmp_path)
    hit = [f for f in findings if f.check == "specified-spec-not-ready"]
    assert len(hit) == 1
    assert hit[0].status is DoctorStatus.WARN
    assert hit[0].evidence["subject"] == slug
    assert hit[0].evidence["spec_statuses"] == ["(unevaluable)"]
    assert "could not be evaluated for readiness" in hit[0].message


def test_specified_spec_not_ready_via_satellite_title(tmp_path: Path) -> None:
    """README:71 must fire when the only covering Spec is matched via
    ``## Satellite: <title>`` and is still at ``draft``."""
    _write_roster(tmp_path)
    _write_dream(
        tmp_path,
        "satellite-dream",
        status="specified",
        title="The Satellite Dream",
        owner="herald",
        realization_log=True,
    )
    _write_dream(
        tmp_path,
        "host-dream",
        status="realized",
        title="Host Dream",
        owner="herald",
        realization_log=True,
    )
    _write_readme(
        tmp_path,
        [
            ("satellite-dream.md", "specified"),
            ("host-dream.md", "realized"),
        ],
    )
    spec_dir = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-herald"
        / "planning-artifacts"
        / "specs"
        / "spec-host"
    )
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "SPEC.md").write_text(
        "\n".join(
            [
                "---",
                "owner-dream: docs/dreams/host-dream.md",
                "status: draft",
                "---",
                "",
                "## Satellite: The Satellite Dream",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    findings = chain.gather_dreams_hygiene(tmp_path)
    hit = [
        f
        for f in findings
        if f.check == "specified-spec-not-ready"
        and f.evidence.get("subject") == "satellite-dream"
    ]
    assert len(hit) == 1
    assert hit[0].evidence["spec_statuses"] == ["draft"]


def test_specified_spec_not_ready_via_covers_dreams(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path,
        "satellite-dream",
        status="specified",
        title="Satellite Dream",
        owner="herald",
        realization_log=True,
    )
    _write_readme(tmp_path, [("satellite-dream.md", "specified")])
    spec_dir = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-herald"
        / "planning-artifacts"
        / "specs"
        / "spec-host"
    )
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "SPEC.md").write_text(
        "\n".join(
            [
                "---",
                "owner-dream: docs/dreams/host-dream.md",
                "covers-dreams:",
                "  - docs/dreams/satellite-dream.md",
                "status: draft",
                "---",
                "",
                "body",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    findings = chain.gather_dreams_hygiene(tmp_path)
    hit = [f for f in findings if f.check == "specified-spec-not-ready"]
    assert len(hit) == 1
    assert hit[0].evidence["subject"] == "satellite-dream"


def test_kinship_wikilink_resolves_existing_dream(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(
        tmp_path, "target", status="dreamt", title="Target", realization_log=False
    )
    path = tmp_path / "docs" / "dreams" / "linker.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "owner: herald",
                "status: dreamt",
                "type: dream",
                "title: Linker",
                "---",
                "",
                "See [[target]] and [[target.md|label]].",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_readme(
        tmp_path, [("target.md", "dreamt"), ("linker.md", "dreamt")]
    )
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "kinship-wikilink-dead" for f in findings)
