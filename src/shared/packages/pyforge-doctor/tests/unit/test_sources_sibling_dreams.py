"""Unit tests for ``sources.sibling_dreams`` (Story 16.1 / CAP-1; re-key 21.3)."""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import sibling_dreams

# Measured live 2026-09-09: 8 shared filenames, 0 shared titles between trees.
_SHARED_SLUGS = (
    "developer-machine-bootstrap",
    "django-accelerator-framework",
    "enterprise-data-models-and-apis",
    "miniforge-installer",
    "package-inventory-eligibility",
    "pixi-container-image",
    "reusable-cicd-workflows",
    "sibling-dreams-drift",
)


def _dream_text(*, title: str, status: str, owner: str, body: str = "body\n") -> str:
    return f"---\ntitle: {title}\nstatus: {status}\nowner: {owner}\n---\n{body}"


def _fingerprint(*, title: str, status: str, owner: str, body: str = "body\n") -> dict[str, str]:
    parsed = sibling_dreams._parse_dream_fingerprint(
        _dream_text(title=title, status=status, owner=owner, body=body)
    )
    assert parsed is not None
    return parsed


def _write_local_dream(
    dreams: Path,
    slug: str,
    *,
    title: str,
    status: str,
    owner: str,
    body: str = "body\n",
) -> dict[str, str]:
    dreams.mkdir(parents=True, exist_ok=True)
    text = _dream_text(title=title, status=status, owner=owner, body=body)
    (dreams / f"{slug}.md").write_text(text, encoding="utf-8")
    return sibling_dreams._parse_dream_fingerprint(text)  # type: ignore[return-value]


def _default_shared_fixture() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Agreeing local/sibling maps keyed by filename slug (real shared set)."""
    local: dict[str, dict[str, str]] = {}
    sibling: dict[str, dict[str, str]] = {}
    for slug in _SHARED_SLUGS:
        title = slug.replace("-", " ").title()
        fp = _fingerprint(title=title, status="specified", owner="steward")
        local[slug] = fp
        sibling[slug] = dict(fp)
    return local, sibling


def test_shared_filenames_report_live_divergence_shape(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    local, sibling = _default_shared_fixture()
    # Live divergence: developer-machine-bootstrap local specified vs sibling dreamt.
    local["developer-machine-bootstrap"] = _write_local_dream(
        dreams,
        "developer-machine-bootstrap",
        title="A new contributor or agent is productive on this repo without tribal knowledge",
        status="specified",
        owner="steward",
    )
    sibling["developer-machine-bootstrap"] = _fingerprint(
        title="A new contributor or agent is productive on this repo without tribal knowledge",
        status="dreamt",
        owner="steward",
    )
    for slug in _SHARED_SLUGS:
        if slug == "developer-machine-bootstrap":
            continue
        _write_local_dream(
            dreams,
            slug,
            title=local[slug]["title"],
            status=local[slug]["status"],
            owner=local[slug]["owner"],
        )

    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams, "_fetch_sibling_fingerprints", lambda token: sibling
    )

    findings = sibling_dreams.gather(tmp_path)
    assert len(findings) == 1
    f = findings[0]
    assert f.source == Source.SIBLING_DREAMS_DRIFT
    assert f.check == "sibling-dreams-drift"
    assert f.status == DoctorStatus.WARN
    assert f.evidence["slug"] == "developer-machine-bootstrap"
    assert f.evidence["axes"] == ["status"]
    assert f.evidence["local_status"] == "specified"
    assert f.evidence["sibling_status"] == "dreamt"
    assert "body" not in f.evidence


def test_owner_axis_drift_emits_warn(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    local, sibling = _default_shared_fixture()
    local["pixi-container-image"]["owner"] = "steward"
    sibling["pixi-container-image"]["owner"] = "herald"
    for slug in _SHARED_SLUGS:
        _write_local_dream(
            dreams,
            slug,
            title=local[slug]["title"],
            status=local[slug]["status"],
            owner=local[slug]["owner"],
        )

    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams, "_fetch_sibling_fingerprints", lambda token: sibling
    )

    findings = sibling_dreams.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].evidence["slug"] == "pixi-container-image"
    assert findings[0].evidence["axes"] == ["owner"]


def test_agreeing_shared_filenames_emit_nothing(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    local, sibling = _default_shared_fixture()
    for slug in _SHARED_SLUGS:
        _write_local_dream(
            dreams,
            slug,
            title=local[slug]["title"],
            status=local[slug]["status"],
            owner=local[slug]["owner"],
        )

    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams, "_fetch_sibling_fingerprints", lambda token: sibling
    )
    assert sibling_dreams.gather(tmp_path) == ()


def test_no_token_emits_unreachable(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    _write_local_dream(
        dreams,
        "developer-machine-bootstrap",
        title="Bootstrap",
        status="specified",
        owner="steward",
    )
    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: None)

    def _forbid(token):
        raise AssertionError("must not fetch without token")

    monkeypatch.setattr(sibling_dreams, "_fetch_sibling_fingerprints", _forbid)
    findings = sibling_dreams.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].check == "sibling-dreams-unreachable"
    assert findings[0].status == DoctorStatus.WARN
    assert "no operator token" in findings[0].message


def test_unreachable_sibling_emits_unreachable(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    _write_local_dream(
        dreams,
        "developer-machine-bootstrap",
        title="Bootstrap",
        status="specified",
        owner="steward",
    )
    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams, "_fetch_sibling_fingerprints", lambda token: None
    )
    findings = sibling_dreams.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].check == "sibling-dreams-unreachable"
    assert "fetch failed" in findings[0].message


def test_filename_match_title_diff_reports_title_axis(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    local, sibling = _default_shared_fixture()
    slug = "reusable-cicd-workflows"
    sibling[slug]["title"] = "Different title for same slug"
    _write_local_dream(
        dreams,
        slug,
        title=local[slug]["title"],
        status=local[slug]["status"],
        owner=local[slug]["owner"],
    )

    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams, "_fetch_sibling_fingerprints", lambda token: sibling
    )

    findings = sibling_dreams.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].evidence["slug"] == slug
    assert findings[0].evidence["axes"] == ["title"]


def test_one_sided_slugs_emit_nothing(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    _write_local_dream(
        dreams,
        "local-only",
        title="Local Only",
        status="draft",
        owner="herald",
    )
    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams,
        "_fetch_sibling_fingerprints",
        lambda token: {
            "sibling-only": {
                "title": "Sibling Only",
                "status": "draft",
                "owner": "scribe",
                "content_hash": "abc",
            }
        },
    )
    assert sibling_dreams.gather(tmp_path) == ()


def test_missing_dreams_dir_is_silent(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    assert sibling_dreams.gather(tmp_path) == ()
