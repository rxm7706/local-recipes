"""Unit tests for ``sources.capability_effect`` verified-line pass (Story 21.10)."""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import capability_effect


def _spec_text(*, status: str, cap_body: str) -> str:
    return f"---\nspec: example\nstatus: {status}\n---\n\n## Capabilities\n\n{cap_body}\n"


def test_present_verified_line_is_rendered_and_silent():
    text = _spec_text(
        status="shipped",
        cap_body=(
            "- **CAP-1 — example.**\n"
            "  - **intent:** do thing\n"
            "  - **verified:** 2026-09-05 — exercised in tests/unit/test_x.py\n"
        ),
    )
    rows = capability_effect.parse_spec_capability_verified_rows(
        project="pyforge-doctor",
        spec_slug="spec-example",
        spec_text=text,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.verified_text == "2026-09-05 — exercised in tests/unit/test_x.py"
    assert row.rendered == ("CAP-1 — verified: 2026-09-05 — exercised in tests/unit/test_x.py")
    findings = capability_effect.missing_verified_findings(rows, source=Source.CAPABILITY_EFFECT)
    assert findings == ()


def test_plain_verified_line_is_parsed():
    text = _spec_text(
        status="realized",
        cap_body=("- **CAP-2 — other.**\n  verified: 2026-08-01 — live check at src/foo.py:10\n"),
    )
    rows = capability_effect.parse_spec_capability_verified_rows(
        project="pyforge-marshal",
        spec_slug="spec-other",
        spec_text=text,
    )
    assert rows[0].verified_text == "2026-08-01 — live check at src/foo.py:10"
    assert capability_effect.missing_verified_findings(rows, source=Source.CAPABILITY_EFFECT) == ()


def test_missing_verified_on_terminal_spec_emits_warn():
    text = _spec_text(
        status="shipped",
        cap_body=("- **CAP-3 — no evidence.**\n  - **intent:** something\n  - **success:** measurable outcome\n"),
    )
    rows = capability_effect.parse_spec_capability_verified_rows(
        project="pyforge-steward",
        spec_slug="spec-no-verified",
        spec_text=text,
    )
    findings = capability_effect.missing_verified_findings(rows, source=Source.CAPABILITY_EFFECT)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.source == Source.CAPABILITY_EFFECT
    assert finding.check == "capability-effect-verified"
    assert finding.status == DoctorStatus.WARN
    assert "CAP-3" in finding.message
    assert "no `verified:` line" in finding.message
    assert finding.evidence["rendered"] == "CAP-3 — (no verified line)"


def test_missing_verified_on_non_terminal_spec_is_silent():
    text = _spec_text(
        status="in-progress",
        cap_body="- **CAP-1 — draft cap.**\n  - **intent:** not done yet\n",
    )
    rows = capability_effect.parse_spec_capability_verified_rows(
        project="pyforge-doctor",
        spec_slug="spec-draft",
        spec_text=text,
    )
    assert capability_effect.missing_verified_findings(rows, source=Source.CAPABILITY_EFFECT) == ()


def test_realized_status_triggers_missing_verified_finding():
    text = _spec_text(
        status="realized",
        cap_body="- **CAP-4 — realized but unverified.**\n",
    )
    rows = capability_effect.parse_spec_capability_verified_rows(
        project="pyforge-herald",
        spec_slug="spec-realized",
        spec_text=text,
    )
    findings = capability_effect.missing_verified_findings(rows, source=Source.CAPABILITY_EFFECT)
    assert len(findings) == 1
    assert findings[0].evidence["spec_status"] == "realized"


def test_uses_last_verified_line_when_reconciled():
    text = _spec_text(
        status="shipped",
        cap_body=(
            "- **CAP-1 — reconciled.**\n"
            "  verified: 2026-01-01 — first check\n"
            "  verified: 2026-09-10 — re-checked recently\n"
        ),
    )
    rows = capability_effect.parse_spec_capability_verified_rows(
        project="pyforge-doctor",
        spec_slug="spec-reconciled",
        spec_text=text,
    )
    assert rows[0].verified_text == "2026-09-10 — re-checked recently"
    assert capability_effect.missing_verified_findings(rows, source=Source.CAPABILITY_EFFECT) == ()


def test_iter_rows_from_fixture_tree(tmp_path: Path):
    spec_dir = (
        tmp_path / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts" / "specs" / "spec-fixture"
    )
    spec_dir.mkdir(parents=True)
    (spec_dir / "SPEC.md").write_text(
        _spec_text(
            status="shipped",
            cap_body="- **CAP-1 — fixture.**\n  verified: 2026-09-10 — ok\n",
        ),
        encoding="utf-8",
    )
    rows = capability_effect.iter_capability_verified_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0].project == "pyforge-doctor"
    assert rows[0].spec_slug == "spec-fixture"


def test_multi_cap_spec_parses_each_block_independently():
    text = _spec_text(
        status="shipped",
        cap_body=(
            "- **CAP-1 — first.**\n"
            "  verified: 2026-09-01 — ok\n"
            "- **CAP-2 — second.**\n"
            "  - **intent:** still unverified\n"
        ),
    )
    rows = capability_effect.parse_spec_capability_verified_rows(
        project="pyforge-doctor",
        spec_slug="spec-multi",
        spec_text=text,
    )
    assert len(rows) == 2
    assert rows[0].cap_n == 1
    assert rows[0].verified_text is not None
    assert rows[1].cap_n == 2
    assert rows[1].verified_text is None
    findings = capability_effect.missing_verified_findings(rows, source=Source.CAPABILITY_EFFECT)
    assert len(findings) == 1
    assert findings[0].evidence["cap_n"] == 2


def test_quoted_frontmatter_status_is_terminal():
    text = "---\nspec: example\nstatus: 'shipped'\n---\n\n## Capabilities\n\n- **CAP-1 — quoted status.**\n"
    rows = capability_effect.parse_spec_capability_verified_rows(
        project="pyforge-doctor",
        spec_slug="spec-quoted",
        spec_text=text,
    )
    assert rows[0].spec_status == "shipped"
    findings = capability_effect.missing_verified_findings(rows, source=Source.CAPABILITY_EFFECT)
    assert len(findings) == 1


def test_gather_verified_line_is_read_only(tmp_path: Path):
    spec_dir = (
        tmp_path / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts" / "specs" / "spec-read-only"
    )
    spec_dir.mkdir(parents=True)
    spec_path = spec_dir / "SPEC.md"
    original = _spec_text(
        status="shipped",
        cap_body="- **CAP-1 — stays unchanged.**\n",
    )
    spec_path.write_text(original, encoding="utf-8")
    findings = capability_effect.gather_verified_line(tmp_path)
    assert spec_path.read_text(encoding="utf-8") == original
    assert len(findings) == 1
    assert findings[0].check == "capability-effect-verified"
    assert findings[0].status == DoctorStatus.WARN
    assert findings[0].evidence["rendered"] == "CAP-1 — (no verified line)"
