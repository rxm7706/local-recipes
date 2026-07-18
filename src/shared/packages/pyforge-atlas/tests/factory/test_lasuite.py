"""Story H3 `kedro-test` gate — the La Suite / Wagtail REST sync round-trip (FR-22(c), AD-22).

Proves the compiled-wiki → CMS push against an IN-MEMORY mock Wagtail (no network): push (create),
idempotent re-push (no remote call), update on change, and a fresh syncer resuming from the
persisted mapping. Also proves the endpoint/token resolve only from env (AD-2) and errors are
clear (§ 2.1)."""

from pathlib import Path

import pytest

from pyforge.atlas.factory.lasuite import (
    LaSuiteClient,
    LaSuiteConfig,
    LaSuiteError,
    Request,
    Response,
    WikiSyncer,
    resolve_lasuite_config,
)
from pyforge.atlas.factory.wiki import scaffold_wiki


class MockWagtail:
    """An in-memory Wagtail documents API — the injected ``opener``. Routes on method + URL path,
    assigns autoincrement ids, and counts writes so a test can assert 'no remote call' on an
    idempotent re-push."""

    def __init__(self):
        self.docs: dict[str, dict] = {}
        self._next = 0
        self.creates = 0
        self.updates = 0

    def __call__(self, request: Request) -> Response:
        path = request.url.split("/api/v1")[-1]
        if request.method == "POST" and path == "/documents/":
            self._next += 1
            doc_id = str(self._next)
            self.docs[doc_id] = {"id": doc_id, **(request.json or {})}
            self.creates += 1
            return Response(201, self.docs[doc_id])
        if request.method == "PATCH" and path.startswith("/documents/"):
            doc_id = path.split("/")[2]
            if doc_id not in self.docs:
                return Response(404, {"detail": "not found"})
            self.docs[doc_id].update(request.json or {})
            self.updates += 1
            return Response(200, self.docs[doc_id])
        if request.method == "GET" and path == "/documents/all/":
            return Response(200, list(self.docs.values()))
        if request.method == "GET" and path.startswith("/documents/"):
            doc_id = path.split("/")[2]
            if doc_id in self.docs:
                return Response(200, self.docs[doc_id])
            return Response(404, {"detail": "not found"})
        return Response(400, {"detail": f"unrouted {request.method} {path}"})


def _cfg() -> LaSuiteConfig:
    return LaSuiteConfig(base_url="https://cms.example/", api_token="tok")


def _wiki_with_compiled(tmp_path: Path, pages: dict[str, str]):
    layout = scaffold_wiki(tmp_path / "wiki")
    for name, text in pages.items():
        layout.stage_path("compiled", name).write_text(text, encoding="utf-8")
    return layout


# --- config resolution (AD-2) ----------------------------------------------------------


def test_config_resolves_only_from_env(monkeypatch):
    monkeypatch.delenv("LASUITE_BASE_URL", raising=False)
    monkeypatch.delenv("LASUITE_API_TOKEN", raising=False)
    assert resolve_lasuite_config() is None
    monkeypatch.setenv("LASUITE_BASE_URL", "https://cms.example/")
    assert resolve_lasuite_config() is None  # token still missing -> unconfigured
    monkeypatch.setenv("LASUITE_API_TOKEN", "tok")
    cfg = resolve_lasuite_config()
    assert cfg is not None and cfg.base_url == "https://cms.example" and cfg.api_token == "tok"


# --- client error clarity (§ 2.1) ------------------------------------------------------


def test_client_raises_clear_error_on_non_2xx():
    client = LaSuiteClient(_cfg(), opener=lambda req: Response(500, {"detail": "boom"}))
    with pytest.raises(LaSuiteError) as exc:
        client.create_document("T", "body")
    msg = str(exc.value)
    assert "POST" in msg and "500" in msg and "boom" in msg


def test_default_opener_refuses_without_injection():
    # AC-2: package code holds no HTTP client. With no opener injected, any call fails clearly,
    # pointing at the deferred live bring-up — it never silently reaches for the network.
    client = LaSuiteClient(_cfg())  # no opener
    with pytest.raises(LaSuiteError) as exc:
        client.list_documents()
    assert "no CMS transport injected" in str(exc.value)


def test_client_sends_bearer_auth_and_builds_url():
    seen = {}

    def opener(req: Request) -> Response:
        seen["url"] = req.url
        seen["auth"] = req.headers.get("Authorization")
        return Response(201, {"id": "1"})

    LaSuiteClient(_cfg(), opener=opener).create_document("T", "b")
    assert seen["url"] == "https://cms.example/api/v1/documents/"
    assert seen["auth"] == "Bearer tok"


# --- the round-trip (push / update / idempotent re-push) -------------------------------


def test_round_trip_push_update_idempotent(tmp_path: Path):
    layout = _wiki_with_compiled(
        tmp_path,
        {
            "a.md": "---\ntitle: A\n---\nalpha\n",
            "b.md": "---\ntitle: B\n---\nbeta\n",
        },
    )
    mock = MockWagtail()
    syncer = WikiSyncer(LaSuiteClient(_cfg(), opener=mock), layout)

    # 1) first push -> both CREATE.
    r1 = syncer.sync_all()
    assert sorted(r1.created) == ["a.md", "b.md"]
    assert r1.updated == [] and r1.skipped == []
    assert mock.creates == 2 and mock.updates == 0
    assert len(mock.docs) == 2

    # 2) idempotent re-push (nothing changed) -> NO remote call at all.
    r2 = syncer.sync_all()
    assert sorted(r2.skipped) == ["a.md", "b.md"]
    assert r2.created == [] and r2.updated == []
    assert mock.creates == 2 and mock.updates == 0  # unchanged

    # 3) change one page -> exactly one UPDATE, no duplicate create.
    layout.stage_path("compiled", "a.md").write_text(
        "---\ntitle: A\n---\nalpha revised\n", encoding="utf-8"
    )
    r3 = syncer.sync_all()
    assert r3.updated == ["a.md"] and r3.skipped == ["b.md"] and r3.created == []
    assert mock.creates == 2 and mock.updates == 1
    assert len(mock.docs) == 2  # still two docs, not three
    assert mock.docs["1"]["content"] == "---\ntitle: A\n---\nalpha revised\n"


def test_mapping_persists_so_a_fresh_syncer_resumes(tmp_path: Path):
    layout = _wiki_with_compiled(tmp_path, {"a.md": "---\ntitle: A\n---\nalpha\n"})
    mock = MockWagtail()
    WikiSyncer(LaSuiteClient(_cfg(), opener=mock), layout).sync_all()
    assert mock.creates == 1

    # A brand-new syncer (mapping reloaded from the sidecar) must NOT re-create the same page.
    r = WikiSyncer(LaSuiteClient(_cfg(), opener=mock), layout).sync_all()
    assert r.skipped == ["a.md"] and r.created == []
    assert mock.creates == 1  # no duplicate create


def test_title_prefers_frontmatter_then_heading(tmp_path: Path):
    layout = _wiki_with_compiled(
        tmp_path,
        {
            "fm.md": "---\ntitle: FromFrontmatter\n---\n# IgnoredHeading\nbody\n",
            "hd.md": "# FromHeading\nbody\n",
        },
    )
    sent = {}
    mock = MockWagtail()

    def spy(req: Request) -> Response:
        if req.method == "POST":
            sent[req.json["content"][:10]] = req.json["title"]
        return mock(req)

    WikiSyncer(LaSuiteClient(_cfg(), opener=spy), layout).sync_all()
    titles = set(sent.values())
    assert "FromFrontmatter" in titles and "FromHeading" in titles


def test_sync_writes_mapping_inside_wiki_root_only(tmp_path: Path):
    # AD-22: the syncer's only local write is the mapping sidecar, and it lives under the wiki
    # root (never an atlas dataset, never outside the tree).
    layout = _wiki_with_compiled(tmp_path, {"a.md": "---\ntitle: A\n---\nalpha\n"})
    WikiSyncer(LaSuiteClient(_cfg(), opener=MockWagtail()), layout).sync_all()
    assert (layout.root / ".lasuite_sync.json").is_file()
