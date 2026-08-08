"""``notices.py``'s storage, authoring, and lifecycle (Epic 10, Stories
10.1/10.2/10.3/10.6). Every test uses an explicit ``tmp_path`` as
``repo_root`` -- ``notices.py`` never assumes a cwd, mirroring
``state.py``'s own convention (``test_state.py``'s own docstring)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.herald import notices
from pyforge.herald.errors import HeraldError


def _author(repo_root: Path, *, component: str = "auth-api-v1", **overrides):
    kwargs = {
        "notice_type": "deprecation",
        "component": component,
        "what": "auth-api-v1 is deprecated",
        "why": "superseded by auth-api-v2",
        "migration": "swap the base URL",
        "deadline": "2026-09-01",
        "reason_link": "https://example.com/rfc",
        "publish": False,
    }
    kwargs.update(overrides)
    return notices.author_notice(repo_root, **kwargs)


# --- Story 10.1: data model & archive storage ------------------------------


def test_author_writes_a_draft_and_the_markdown_mirror(tmp_path: Path):
    notice = _author(tmp_path)
    assert notice.status == "draft"
    assert notice.published_at is None
    md_path = tmp_path / notice.path
    assert md_path.exists()
    text = md_path.read_text(encoding="utf-8")
    assert "type: deprecation" in text
    assert "## What" in text
    assert "auth-api-v1 is deprecated" in text


def test_notice_path_is_notices_yyyy_mm_type_component(tmp_path: Path):
    notice = _author(tmp_path, now="2026-08-05T12:00:00+00:00")
    assert notice.path == "notices/2026-08/deprecation/auth-api-v1.md"


def test_author_records_one_revision(tmp_path: Path):
    notice = _author(tmp_path)
    assert len(notice.revisions) == 1
    assert notice.revisions[0]["summary"] == "authored"


def test_re_authoring_a_draft_appends_a_revision_and_keeps_created_at(tmp_path: Path):
    first = _author(tmp_path, now="2026-08-01T00:00:00+00:00")
    second = _author(tmp_path, what="updated text", now="2026-08-02T00:00:00+00:00")
    assert second.created_at == first.created_at
    assert second.what == "updated text"
    assert len(second.revisions) == 2
    assert second.revisions[-1]["summary"] == "re-authored"


def test_re_authoring_with_a_changed_type_removes_the_stale_markdown_file(
    tmp_path: Path,
):
    """Regression: the path is derived from `notice_type`, so re-authoring
    a still-draft component under a different type relocates its markdown
    file -- but the OLD file was never removed, leaving a stale,
    git-diffable "record" with the old content sitting alongside the new
    one indefinitely."""
    first = _author(tmp_path, notice_type="deprecation")
    old_path = tmp_path / first.path
    assert old_path.exists()

    second = _author(tmp_path, notice_type="fix")

    new_path = tmp_path / second.path
    assert new_path.exists()
    assert new_path != old_path
    assert not old_path.exists()


def test_author_publish_close_write_markdown_before_the_index(
    tmp_path: Path, monkeypatch
):
    """Regression: the index was written before the markdown file, so a
    markdown-write failure left a phantom index entry pointing at a file
    that was never created -- reported by get/list/the web export as a
    real, live notice with no reachable content. Markdown now writes
    first; a failure there must leave the index untouched."""
    import pyforge.herald.notices as notices_module

    def _boom(repo_root, notice):
        raise HeraldError("simulated markdown write failure")

    monkeypatch.setattr(notices_module, "_write_markdown", _boom)

    with pytest.raises(HeraldError, match="simulated markdown write failure"):
        _author(tmp_path)

    # The index must still have no entry for this component.
    with pytest.raises(HeraldError, match="no notice found"):
        notices.get_notice(tmp_path, "auth-api-v1")


def test_invalid_notice_type_is_refused(tmp_path: Path):
    with pytest.raises(HeraldError, match="invalid notice type"):
        _author(tmp_path, notice_type="bogus")


def test_invalid_component_is_refused(tmp_path: Path):
    with pytest.raises(HeraldError, match="invalid component"):
        _author(tmp_path, component="../etc/passwd")


def test_index_file_round_trips_through_a_fresh_load(tmp_path: Path):
    _author(tmp_path)
    fetched = notices.get_notice(tmp_path, "auth-api-v1")
    assert fetched.component == "auth-api-v1"
    assert fetched.what == "auth-api-v1 is deprecated"


def test_a_corrupted_index_entry_missing_a_required_field_raises_herald_error(
    tmp_path: Path,
):
    """Regression: `_entry_to_notice` checked for unknown extra fields and
    a malformed `revisions` type, but never that every field the `Notice`
    dataclass requires (no default) was present -- a missing one raised a
    raw `TypeError` from `Notice.__init__`, not the structural
    `errors.HeraldError` every other corruption check in this function
    raises (AD-6). Since `dispatch()` only catches `HeraldError`, this
    crashed as an unhandled traceback instead of the tool's usual
    one-stderr-line/exit-code reporting."""
    import json

    _author(tmp_path)
    index_path = tmp_path / notices.DEFAULT_INDEX_PATH
    document = json.loads(index_path.read_text(encoding="utf-8"))
    del document["notices"]["auth-api-v1"]["what"]
    index_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(HeraldError, match="missing field.*'what'"):
        notices.get_notice(tmp_path, "auth-api-v1")


# --- Story 10.6: lifecycle --------------------------------------------------


def test_publish_transitions_draft_to_published(tmp_path: Path):
    _author(tmp_path)
    published = notices.publish_notice(
        tmp_path, "auth-api-v1", now="2026-08-03T00:00:00+00:00"
    )
    assert published.status == "published"
    assert published.published_at == "2026-08-03T00:00:00+00:00"


def test_publish_of_unknown_component_raises(tmp_path: Path):
    with pytest.raises(HeraldError, match="no notice found"):
        notices.publish_notice(tmp_path, "does-not-exist")


def test_publish_already_published_raises(tmp_path: Path):
    _author(tmp_path)
    notices.publish_notice(tmp_path, "auth-api-v1")
    with pytest.raises(HeraldError, match="already published"):
        notices.publish_notice(tmp_path, "auth-api-v1")


def test_author_with_publish_true_skips_the_separate_publish_call(tmp_path: Path):
    notice = _author(tmp_path, publish=True)
    assert notice.status == "published"
    assert notice.published_at is not None


def test_re_authoring_a_published_notice_is_refused(tmp_path: Path):
    _author(tmp_path, publish=True)
    with pytest.raises(HeraldError, match="already published"):
        _author(tmp_path, what="new text")


def test_close_requires_published_not_draft(tmp_path: Path):
    _author(tmp_path)
    with pytest.raises(HeraldError, match="still a draft"):
        notices.close_notice(tmp_path, "auth-api-v1")


def test_close_transitions_published_to_closed(tmp_path: Path):
    _author(tmp_path, publish=True)
    closed = notices.close_notice(
        tmp_path, "auth-api-v1", reason="migration complete", closed_by="operator:env"
    )
    assert closed.status == "closed"
    assert closed.close_reason == "migration complete"
    assert closed.closed_by == "operator:env"


def test_close_without_closed_by_falls_back_to_placeholder(tmp_path: Path):
    _author(tmp_path, publish=True)
    closed = notices.close_notice(tmp_path, "auth-api-v1")
    assert closed.closed_by == notices.UNKNOWN_OPERATOR


def test_close_already_closed_raises(tmp_path: Path):
    _author(tmp_path, publish=True)
    notices.close_notice(tmp_path, "auth-api-v1")
    with pytest.raises(HeraldError, match="already closed"):
        notices.close_notice(tmp_path, "auth-api-v1")


def test_list_excludes_drafts_by_default(tmp_path: Path):
    _author(tmp_path, component="draft-one")
    _author(tmp_path, component="published-one", publish=True)
    results = notices.list_notices(tmp_path)
    components = [n.component for n in results]
    assert "draft-one" not in components
    assert "published-one" in components


def test_list_status_draft_shows_only_drafts(tmp_path: Path):
    _author(tmp_path, component="draft-one")
    _author(tmp_path, component="published-one", publish=True)
    results = notices.list_notices(tmp_path, status="draft")
    assert [n.component for n in results] == ["draft-one"]


def test_list_status_all_shows_every_status(tmp_path: Path):
    _author(tmp_path, component="draft-one")
    _author(tmp_path, component="published-one", publish=True)
    results = notices.list_notices(tmp_path, status="all")
    assert {n.component for n in results} == {"draft-one", "published-one"}


def test_list_closed_notices_stay_visible(tmp_path: Path):
    _author(tmp_path, publish=True)
    notices.close_notice(tmp_path, "auth-api-v1")
    results = notices.list_notices(tmp_path)
    assert results[0].status == "closed"


def test_list_filters_by_category(tmp_path: Path):
    _author(tmp_path, component="dep-one", publish=True)
    _author(tmp_path, component="eol-one", notice_type="eol", publish=True)
    results = notices.list_notices(tmp_path, category="eol")
    assert [n.component for n in results] == ["eol-one"]


def test_list_filters_by_date_range(tmp_path: Path):
    _author(tmp_path, component="early", publish=True, now="2026-01-01T00:00:00+00:00")
    _author(tmp_path, component="late", publish=True, now="2026-08-01T00:00:00+00:00")
    results = notices.list_notices(tmp_path, date_range=("2026-07-01", "2026-12-31"))
    assert [n.component for n in results] == ["late"]


# --- Story 10.3: archive & redirects ---------------------------------------


def test_archive_rename_redirects_get_to_the_new_component(tmp_path: Path):
    _author(tmp_path, component="old-name", publish=True)
    _author(tmp_path, component="new-name", publish=True)
    notices.archive_rename(tmp_path, "old-name", "new-name")
    resolved = notices.get_notice(tmp_path, "old-name")
    assert resolved.component == "new-name"


def test_archive_rename_requires_target_notice_to_exist(tmp_path: Path):
    _author(tmp_path, component="old-name", publish=True)
    with pytest.raises(HeraldError, match="no notice exists"):
        notices.archive_rename(tmp_path, "old-name", "does-not-exist")


def test_archive_rename_refuses_self_redirect(tmp_path: Path):
    _author(tmp_path, component="only-name", publish=True)
    with pytest.raises(HeraldError, match="redirect a component to itself"):
        notices.archive_rename(tmp_path, "only-name", "only-name")


def test_archive_rename_refuses_double_redirect(tmp_path: Path):
    _author(tmp_path, component="old-name", publish=True)
    _author(tmp_path, component="new-name", publish=True)
    notices.archive_rename(tmp_path, "old-name", "new-name")
    with pytest.raises(HeraldError, match="already redirects"):
        notices.archive_rename(tmp_path, "old-name", "new-name")


def test_get_of_unknown_component_raises(tmp_path: Path):
    with pytest.raises(HeraldError, match="no notice found"):
        notices.get_notice(tmp_path, "does-not-exist")


def test_publish_follows_a_redirect(tmp_path: Path):
    _author(tmp_path, component="old-name")
    _author(tmp_path, component="new-name", publish=True)
    notices.archive_rename(tmp_path, "old-name", "new-name")
    # publishing "old-name" (a redirect) resolves and re-checks new-name,
    # which is already published -- so this must raise, not silently
    # publish the wrong (draft) entry.
    with pytest.raises(HeraldError, match="already published"):
        notices.publish_notice(tmp_path, "old-name")
