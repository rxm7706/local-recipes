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
                    "ready",
                    "in-progress",
                    "shipped",
                    "absorbed",
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
    spec_dir = target / "_bmad-output" / "projects" / project / "planning-artifacts" / "specs" / f"spec-{slug}"
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


def test_status_trailing_comment_reports(tmp_path: Path) -> None:
    """Story 59.6 / CAP-137, Ruling 19: a trailing ``# ...`` on the same
    line as Dream ``status:`` is a finding, distinct from ``dream-vocab``
    (the parsed status value itself, ``ready``, is on-vocabulary)."""
    _write_roster(tmp_path)
    path = tmp_path / "docs" / "dreams" / "foo.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\nowner: marshal\nstatus: dreamt   # leftover note\ntype: dream\ntitle: Foo\n---\n\nbody\n",
        encoding="utf-8",
    )
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    kinds = {f.check for f in findings}
    assert "dream-status-trailing-comment" in kinds
    assert "dream-vocab" not in kinds
    hit = next(f for f in findings if f.check == "dream-status-trailing-comment")
    assert hit.status is DoctorStatus.WARN
    assert hit.evidence["subject"] == "foo"
    assert "# leftover note" in hit.evidence["line"]


def test_status_without_trailing_comment_is_clean(tmp_path: Path) -> None:
    """No false positive on a plain ``status:`` line with no ``#``."""
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", status="dreamt", realization_log=False)
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    kinds = {f.check for f in findings}
    assert "dream-status-trailing-comment" not in kinds


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
    _write_dream(tmp_path, "foo", status="realized", title="Foo", realization_log=False)
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
    assert not any(f.evidence.get("subject") == "pyforge-unifying-strategy" for f in hist)


def test_dreamt_may_omit_realization_log(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", status="dreamt", title="Foo", realization_log=False)
    _write_readme(tmp_path, [("foo.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "realization-log-missing" for f in findings)
    assert findings[0].check == "dreams-hygiene"
    assert findings[0].status is DoctorStatus.OK


def test_readme_table_orphan_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", status="dreamt", title="Foo", realization_log=False)
    _write_readme(tmp_path, [("missing.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert any(f.check == "readme-table-orphan" for f in findings)


def test_readme_table_status_drift_reports(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    _write_dream(tmp_path, "foo", status="realized", title="Foo", realization_log=True)
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
    _write_dream(tmp_path, "orphan-dream", status="dreamt", title="Orphan", realization_log=False)
    _write_readme(tmp_path, [])
    findings = chain.gather_dreams_hygiene(tmp_path)
    hit = [f for f in findings if f.check == "dream-readme-missing"]
    assert len(hit) == 1
    assert hit[0].status is DoctorStatus.WARN
    assert hit[0].evidence["subject"] == "orphan-dream"


def test_live_tree_dream_readme_missing_count() -> None:
    """Measured live 2026-09-18: 65 Dream files lack a README.md table row
    (was 67 on 2026-09-12 — two rows caught up; this test only tracks the live
    count)."""
    repo_root = _require_repo_root()
    findings = chain.gather_dreams_hygiene(repo_root)
    missing = [f for f in findings if f.check == "dream-readme-missing"]
    assert len(missing) == 65


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
    """Measured live 2026-09-18: 0 ``specified`` Dreams whose covering Spec is
    not ``ready`` or beyond (was 3 on 2026-09-11 — those cleared)."""
    repo_root = _require_repo_root()
    findings = chain.gather_dreams_hygiene(repo_root)
    bad = [f for f in findings if f.check == "specified-spec-not-ready"]
    assert len(bad) == 0


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


def test_kinship_wikilink_skips_frontmatter_with_a_quoted_dashes_scalar(
    tmp_path: Path,
) -> None:
    """Story 28.1 / CAP-81, body boundary: a frontmatter scalar quoting
    ``"---"`` BEFORE a ``[[...]]`` inside the fence. The parser now accepts
    this Dream (the quoted ``---`` is not a fence line); the body-side
    reader must bound the body by the SAME line-anchored scan, or the
    frontmatter tail after the quoted ``---`` is scanned as Kinship body
    and ``[[not-a-link]]`` fires a false ``kinship-wikilink-dead`` (the
    known-bad state review pass 1 reproduced with the parser fixed but
    ``_dream_body_after_frontmatter`` still on ``split("---", 2)``)."""
    _write_roster(tmp_path)
    path = tmp_path / "docs" / "dreams" / "quoted.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "owner: herald",
                "status: dreamt",
                "type: dream",
                "title: Quoted",
                "evidence: 'the gate still checks lines[0] == \"---\" first'",
                "note: [[not-a-link]]",
                "---",
                "",
                "Body only.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_readme(tmp_path, [("quoted.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "unparseable-frontmatter" for f in findings)
    assert not any(f.check == "kinship-wikilink-dead" for f in findings)


def test_kinship_wikilink_skips_frontmatter_below_a_banner(tmp_path: Path) -> None:
    """Story 28.1 / CAP-81, body boundary: a banner-topped Dream with a
    ``[[...]]`` inside the fence. The parser skips the banner and accepts
    the block; the body-side reader must skip it the same way -- before
    this story the file was refused outright and never reached the scan,
    and with only the parser fixed the old ``startswith("---")`` guard
    returned the whole text (banner, frontmatter and all) as body."""
    _write_roster(tmp_path)
    path = tmp_path / "docs" / "dreams" / "bannered.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "<!-- Promoted from implementation-artifacts/ on 2026-09-19 -->",
                "---",
                "owner: herald",
                "status: dreamt",
                "type: dream",
                "title: Bannered",
                "note: [[not-a-link]]",
                "---",
                "",
                "Body only.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_readme(tmp_path, [("bannered.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "unparseable-frontmatter" for f in findings)
    assert not any(f.check == "kinship-wikilink-dead" for f in findings)


def test_live_tree_kinship_wikilink_dead_count() -> None:
    """Measured live 2026-09-19 under Story 28.1's opener rule: 31 dead
    Kinship wikilinks under docs/dreams/ (was 33 on 2026-09-18, 26 on
    2026-09-14). The -2 is one archived Dream, ``enterprise-airgap.md``,
    whose glued ``---title:`` opener (the 2026-09-17 fold, deliberately
    left in place by ``0b74756679``) is now refused as
    ``unparseable-frontmatter`` before the Kinship scan runs; the old
    reader parsed that opener leniently and scanned its body, where
    ``[[deckcraft]]`` and ``[[pyforge-genesis]]`` do not resolve. The
    count rises by two once that Dream's opener is repaired (and its two
    links are still dead); this test only tracks the live count.

    30 since 2026-09-25 (32 once ``enterprise-airgap.md``'s opener is repaired): ``pyforge-pages.md``'s ``[[python-foundry-cutover]]``
    (no Dream by that name; the cutover Spec's owning Dream is
    ``pyforge-unifying-strategy``) was repointed in the unifying-strategy
    consolidation."""
    repo_root = _require_repo_root()
    findings = chain.gather_dreams_hygiene(repo_root)
    dead = [f for f in findings if f.check == "kinship-wikilink-dead"]
    assert len(dead) == 30


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
    # Positive proof the live roster was actually read, not a silent
    # degrade-to-fallback that happens to produce the same suppression.
    assert not any(f.check == "spec-status-roster-degraded" for f in findings)


def test_specified_spec_absorbed_suppresses_finding(tmp_path: Path) -> None:
    """Story 59.2: ``absorbed`` is in ``spec_statuses_ready_or_beyond`` (and
    in ``guild-roster.json``'s ``spec_statuses_terminal``) -- a covering Spec
    at ``absorbed`` must suppress ``specified-spec-not-ready``."""
    _write_roster(tmp_path)
    _write_dream(
        tmp_path,
        "absorbed-dream",
        status="specified",
        title="Absorbed Dream",
        owner="doctor",
        realization_log=True,
    )
    _write_readme(tmp_path, [("absorbed-dream.md", "specified")])
    _write_spec(tmp_path, "absorbed-dream", status="absorbed")
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "specified-spec-not-ready" for f in findings)


def test_specified_spec_archived_reports_not_ready(tmp_path: Path) -> None:
    """Story 59.2: ``archived`` is in ``guild-roster.json``'s
    ``spec_statuses_terminal`` but NOT in ``spec_statuses_ready_or_beyond`` --
    a covering Spec at ``archived`` must still raise
    ``specified-spec-not-ready``, the one non-obvious invariant that
    motivated the new declared key over reusing ``spec_statuses_terminal``."""
    _write_roster(tmp_path)
    _write_dream(
        tmp_path,
        "archived-dream",
        status="specified",
        title="Archived Dream",
        owner="doctor",
        realization_log=True,
    )
    _write_readme(tmp_path, [("archived-dream.md", "specified")])
    _write_spec(tmp_path, "archived-dream", status="archived")
    findings = chain.gather_dreams_hygiene(tmp_path)
    hit = [f for f in findings if f.check == "specified-spec-not-ready"]
    assert len(hit) == 1
    assert hit[0].status is DoctorStatus.WARN
    assert hit[0].evidence["subject"] == "archived-dream"
    assert hit[0].evidence["spec_statuses"] == ["archived"]


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
    spec_dir = tmp_path / "_bmad-output" / "projects" / "pyforge-herald" / "planning-artifacts" / "specs" / "spec-host"
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
        f for f in findings if f.check == "specified-spec-not-ready" and f.evidence.get("subject") == "satellite-dream"
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
    spec_dir = tmp_path / "_bmad-output" / "projects" / "pyforge-herald" / "planning-artifacts" / "specs" / "spec-host"
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
    _write_dream(tmp_path, "target", status="dreamt", title="Target", realization_log=False)
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
    _write_readme(tmp_path, [("target.md", "dreamt"), ("linker.md", "dreamt")])
    findings = chain.gather_dreams_hygiene(tmp_path)
    assert not any(f.check == "kinship-wikilink-dead" for f in findings)
