"""Unit tests for ``sources.sibling_dreams`` (Story 16.1 / CAP-1; re-key 21.3)."""

from __future__ import annotations

import hashlib
import io
import json as _json
import urllib.request as _urlreq
from pathlib import Path

import pytest

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


# --- fetch path and parser edges (offline: urlopen stubbed) -------------------
#
# Added 2026-09-16 (doctor Epic 25 PR, fix-now rule): registering a new source
# touches sources/__init__.py, which the coverage gate resolves to the whole
# `pyforge.doctor.sources` package -- and this module sat at 57.7% against an
# 80% floor because its network path had no offline exercise. These stubs give
# it one without a single real request.



class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _stub_urlopen(monkeypatch, routes: dict[str, bytes | Exception]):
    calls: list[str] = []

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        url = req.full_url
        calls.append(url)
        hit = routes.get(url)
        if isinstance(hit, Exception):
            raise hit
        if hit is None:
            raise OSError(f"unrouted {url}")
        return _FakeResp(hit)

    monkeypatch.setattr(_urlreq, "urlopen", fake_urlopen)
    return calls


def _listing(*names: str) -> bytes:
    return _json.dumps(
        [{"name": n, "download_url": f"https://raw.test/{n}"} for n in names]
        + [{"name": "notes.txt", "download_url": "https://raw.test/notes.txt"},
           {"name": "no-url.md"}, "garbage", {"name": 7, "download_url": "x"}]
    ).encode()


def test_fetch_sibling_fingerprints_happy_path_skips_non_dreams(monkeypatch):
    url = f"{sibling_dreams._API_BASE}/{sibling_dreams._SIBLING_DREAMS_PATH}"
    calls = _stub_urlopen(monkeypatch, {
        url: _listing("a.md", "b.md", "broken.md"),
        "https://raw.test/a.md": _dream_text(title="A", status="specified", owner="steward").encode(),
        "https://raw.test/b.md": _dream_text(title="B", status="realized", owner="marshal", body="").encode(),
        "https://raw.test/broken.md": b"no frontmatter at all",
    })
    out = sibling_dreams._fetch_sibling_fingerprints("tok")
    assert out is not None
    assert set(out) == {"a", "b"}  # broken.md parsed to None and was dropped
    assert out["a"]["owner"] == "steward" and out["b"]["status"] == "realized"
    # only .md entries with a download_url were fetched
    assert calls == [url, "https://raw.test/a.md", "https://raw.test/b.md", "https://raw.test/broken.md"]


def test_fetch_sibling_fingerprints_fails_open_on_listing_error(monkeypatch):
    url = f"{sibling_dreams._API_BASE}/{sibling_dreams._SIBLING_DREAMS_PATH}"
    _stub_urlopen(monkeypatch, {url: OSError("rate limited")})
    assert sibling_dreams._fetch_sibling_fingerprints("tok") is None


def test_fetch_sibling_fingerprints_fails_open_on_non_list_and_on_file_error(monkeypatch):
    url = f"{sibling_dreams._API_BASE}/{sibling_dreams._SIBLING_DREAMS_PATH}"
    _stub_urlopen(monkeypatch, {url: b'{"message": "Not Found"}'})
    assert sibling_dreams._fetch_sibling_fingerprints("tok") is None
    _stub_urlopen(monkeypatch, {
        url: _listing("a.md"),
        "https://raw.test/a.md": OSError("boom"),
    })
    assert sibling_dreams._fetch_sibling_fingerprints("tok") is None


def test_http_helpers_send_bearer_and_decode(monkeypatch):
    seen: dict[str, object] = {}

    def fake_urlopen(req, timeout=None):
        seen["headers"] = dict(req.header_items())
        seen["timeout"] = timeout
        return _FakeResp(b'{"ok": true}')

    monkeypatch.setattr(_urlreq, "urlopen", fake_urlopen)
    assert sibling_dreams._http_json("https://x.test/j", "tok", timeout=3.0) == {"ok": True}
    assert seen["headers"]["Authorization"] == "Bearer tok"
    assert seen["headers"]["Accept"] == "application/vnd.github+json"
    assert seen["timeout"] == 3.0
    monkeypatch.setattr(_urlreq, "urlopen", lambda req, timeout=None: _FakeResp("héllo".encode()))
    assert sibling_dreams._http_text("https://x.test/t", "tok", timeout=1.0) == "héllo"


@pytest.mark.parametrize(
    "text",
    [
        "",                                   # no lines
        "# not frontmatter\n",                # first line not a fence
        "---\ntitle: x\n",                    # no closing fence
        "---\ntitle: [unclosed\n---\n",       # yaml error
        "---\n- a\n- b\n---\n",               # not a mapping
        "---\nstatus: dreamt\n---\n",         # no title
        "---\ntitle: '  '\n---\n",            # blank title
    ],
)
def test_parse_dream_fingerprint_rejects_unusable_text(text):
    assert sibling_dreams._parse_dream_fingerprint(text) is None


def test_parse_dream_fingerprint_non_string_axes_and_empty_body():
    fp = sibling_dreams._parse_dream_fingerprint("---\ntitle: T\nstatus: 3\nowner: [a]\n---\n")
    assert fp is not None
    assert fp["status"] == "" and fp["owner"] == ""
    assert fp["content_hash"] == hashlib.sha256(b"").hexdigest()


def test_operator_token_prefers_gh_token_then_github_token(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert sibling_dreams._operator_token() is None
    monkeypatch.setenv("GITHUB_TOKEN", "  gt  ")
    assert sibling_dreams._operator_token() == "gt"
    monkeypatch.setenv("GH_TOKEN", "gh")
    assert sibling_dreams._operator_token() == "gh"


def test_local_fingerprints_skip_unusable_files(tmp_path: Path):
    dreams = tmp_path / "docs" / "dreams"
    _write_local_dream(dreams, "good", title="Good", status="dreamt", owner="doctor")
    (dreams / "bad.md").write_text("no frontmatter", encoding="utf-8")
    assert list(sibling_dreams._local_fingerprints(tmp_path)) == ["good"]
