"""``notices.py``'s storage, authoring, and lifecycle (Epic 10, Stories
10.1/10.2/10.3/10.6). Every test uses an explicit ``tmp_path`` as
``repo_root`` -- ``notices.py`` never assumes a cwd, mirroring
``state.py``'s own convention (``test_state.py``'s own docstring)."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import pytest

from pyforge.herald import db, notices
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


def test_a_failed_commit_does_not_delete_the_markdown_the_index_rolls_back_to(tmp_path: Path, monkeypatch):
    """The index must never point at a markdown file this call has already
    deleted.

    Story 13.3 made the index write transactional, so it rolls back on any
    later failure -- but the stale-file `unlink` above ran INSIDE that
    transaction, before the commit. A commit failure (ENOSPC, EIO, a Ctrl-C
    in the window) therefore restored the index entry pointing at the old
    path while the old file was already gone, producing exactly the phantom
    entry `author_notice`'s write ordering exists to prevent and destroying
    the git-tracked durable record. Under the pre-13.3 JSON store the index
    write was already durable at that point, so there was nothing to roll
    back to. Fails against an unlink inside the transaction.
    """
    first = _author(tmp_path, notice_type="deprecation")
    old_path = tmp_path / first.path
    assert old_path.exists()

    class _CommitFails:
        """Everything the real connection does, except COMMIT."""

        def __init__(self, conn):
            self._conn = conn

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def commit(self):
            raise sqlite3.OperationalError("disk I/O error")

    real_connect = db._connect
    monkeypatch.setattr(db, "_connect", lambda path: _CommitFails(real_connect(path)))

    with pytest.raises(HeraldError):
        _author(tmp_path, notice_type="fix")

    monkeypatch.undo()
    assert notices.get_notice(tmp_path, "auth-api-v1").path == first.path
    assert old_path.exists()


def test_author_publish_close_write_markdown_before_the_index(tmp_path: Path, monkeypatch):
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


def test_a_corrupted_revisions_column_raises_herald_error(tmp_path: Path):
    """Story 13.3: every other ``Notice`` field is now a plain, typed SQL
    column (``what TEXT NOT NULL`` etc. -- the schema itself refuses a
    missing required field; see ``tests/test_db.py``'s legacy-import
    coverage for the one corruption path still reachable there, a
    hand-edited legacy ``notices-index.json``). ``revisions`` stays a JSON
    TEXT column with no structural enforcement beyond "is it valid JSON",
    so it is still reachable by writing directly to the database, bypassing
    this module's own API -- mirrors the original regression this test
    pinned (``_entry_to_notice`` must fail structurally, not raw)."""
    import sqlite3

    _author(tmp_path)
    index_path = tmp_path / notices.DEFAULT_INDEX_PATH
    raw = sqlite3.connect(index_path)
    raw.execute(
        "UPDATE notices_index SET revisions = ? WHERE component = ?",
        ("{not valid json", "auth-api-v1"),
    )
    raw.commit()
    raw.close()

    with pytest.raises(HeraldError, match="revisions"):
        notices.get_notice(tmp_path, "auth-api-v1")


# --- Story 10.6: lifecycle --------------------------------------------------


def test_publish_transitions_draft_to_published(tmp_path: Path):
    _author(tmp_path)
    published = notices.publish_notice(tmp_path, "auth-api-v1", now="2026-08-03T00:00:00+00:00")
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
    closed = notices.close_notice(tmp_path, "auth-api-v1", reason="migration complete", closed_by="operator:env")
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


def test_list_notices_on_a_completely_empty_repo_is_empty(tmp_path: Path):
    """Story 11.2: no ``.herald/herald.db`` at all yet -- not even an empty
    one -- must resolve to an empty list, not raise."""
    assert notices.list_notices(tmp_path) == []
    assert notices.list_notices(tmp_path, status="all") == []


def test_get_notice_on_a_completely_empty_repo_raises_herald_error(tmp_path: Path):
    with pytest.raises(HeraldError, match="no notice found"):
        notices.get_notice(tmp_path, "does-not-exist")


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


# --- Story 13.1: concurrency (closing DW-1-4-2) -----------------------------


def test_two_concurrent_authors_for_different_components_both_land(tmp_path: Path, monkeypatch):
    """Story 13.1/13.3 regression: two ``author_notice`` calls for
    different components racing the same database must both survive --
    forced, deterministic interleaving (not a timing-dependent sleep
    race). A monkeypatched delay on ``_now_iso`` (called from inside
    ``author_notice``'s own ``db.transaction``, before its first read)
    gives the other author's whole ``BEGIN IMMEDIATE`` attempt room to
    genuinely block during the pause -- a second author cannot even begin
    its own transaction until the first has committed.

    Scope, stated honestly: this asserts the OUTCOME (both notices land),
    not the mechanism. Story 13.3 rewrote the index write into a
    single-row ``ON CONFLICT`` upsert, so two authors of DIFFERENT
    components cannot clobber each other whatever the locking does --
    verified: this test still passes against a ``db.transaction`` stripped
    of its ``BEGIN IMMEDIATE``.
    ``test_two_concurrent_reauthors_of_the_same_component_do_not_lose_a_revision``
    just below is the one that genuinely depends on the transaction, and
    is what holds DW-1-4-2's guarantee for this module."""
    original_now_iso = notices._now_iso

    def delayed_now_iso():
        timestamp = original_now_iso()
        time.sleep(0.2)
        return timestamp

    monkeypatch.setattr(notices, "_now_iso", delayed_now_iso)

    barrier = threading.Barrier(2)

    def author(component: str) -> None:
        barrier.wait(timeout=5)
        _author(tmp_path, component=component)

    t1 = threading.Thread(target=author, args=("component-a",))
    t2 = threading.Thread(target=author, args=("component-b",))
    t1.start()
    t2.start()
    # Bounded joins plus an explicit liveness assertion: without it a genuine
    # deadlock regression fails below with a confusing content mismatch that
    # reads as a lost update rather than a hang, and leaves two abandoned
    # threads still holding the lock for the rest of the session.
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive(), "a writer deadlocked on the lock"

    components = {n.component for n in notices.list_notices(tmp_path, status="all")}
    assert components == {"component-a", "component-b"}


def test_two_concurrent_reauthors_of_the_same_component_do_not_lose_a_revision(tmp_path, monkeypatch):
    """DW-1-4-2's real guarantee for this module, which the
    different-components test above cannot hold: two ``author_notice``
    calls racing on the SAME component each read the current revision
    list, append to it, and write it back, so without ``db.transaction``
    holding that read-modify-write together both read the same list and
    the second write silently drops the first's revision.

    The delay is injected into ``_write_markdown`` -- called after the
    read and before the index write -- because that is the only point
    inside the critical section that sits between them; delaying
    ``_now_iso`` (as the test above does) lands before the read and so
    leaves no window to lose.

    Verified discriminating: fails (2 revisions, one lost) against a
    ``db.transaction`` stripped of its ``BEGIN IMMEDIATE``, passes (3)
    against the real implementation."""
    _author(tmp_path)  # the initial draft: one "authored" revision

    original_write_markdown = notices._write_markdown

    def delayed_write_markdown(repo_root, notice):
        original_write_markdown(repo_root, notice)
        time.sleep(0.2)

    monkeypatch.setattr(notices, "_write_markdown", delayed_write_markdown)

    barrier = threading.Barrier(2)
    failures: list[BaseException] = []

    def reauthor(what: str) -> None:
        try:
            barrier.wait(timeout=5)
            _author(tmp_path, what=what)
        except BaseException as exc:  # noqa: BLE001 - surfaced via `failures`
            failures.append(exc)

    t1 = threading.Thread(target=reauthor, args=("first edit",))
    t2 = threading.Thread(target=reauthor, args=("second edit",))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive(), "a writer deadlocked on the lock"
    assert not failures, f"a concurrent re-author failed: {failures}"

    notice = notices.get_notice(tmp_path, "auth-api-v1")
    assert len(notice.revisions) == 3, (
        "one re-author's revision was lost: the read-modify-write did not stay inside a single transaction"
    )


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda root: notices.publish_notice(root, "nope"), "no notice found"),
        (lambda root: notices.close_notice(root, "nope"), "no notice found"),
        (
            lambda root: notices.archive_rename(root, "old-name", "new-name"),
            "no notice exists for it yet",
        ),
    ],
    ids=["publish", "close", "rename"],
)
def test_mutating_calls_leave_no_files_behind_when_no_index_exists(tmp_path: Path, call, message):
    """Story 13.1/13.3 regression: opening ``db.transaction`` creates
    ``index_path``'s parent directory and the database file itself, so a
    mutating call that can only ever fail (no notice index exists at all --
    an operator in the wrong directory) would litter that directory with
    an empty ``.herald/`` tree on a pure error path that had no filesystem
    side effect before Story 13.1's lock existed. These three refuse
    BEFORE the transaction opens; ``author_notice`` is deliberately
    excluded, since creating the index is its job."""
    with pytest.raises(HeraldError, match=message):
        call(tmp_path)

    assert list(tmp_path.iterdir()) == [], "a failed mutating call left files behind where there was no index"


@pytest.mark.parametrize(
    ("call", "wrong_message"),
    [
        (lambda root: notices.publish_notice(root, "auth-api-v1"), "no notice found"),
        (lambda root: notices.close_notice(root, "auth-api-v1"), "no notice found"),
        (
            lambda root: notices.archive_rename(root, "auth-api-v1", "auth-api-v2"),
            "no notice exists for it yet",
        ),
    ],
    ids=["publish", "close", "rename"],
)
def test_an_unreadable_index_is_never_reported_as_a_missing_notice(tmp_path: Path, call, wrong_message):
    """The pre-lock fail-fast must distinguish "no index" from "the index
    cannot be opened".

    A ``Path.exists()`` check cannot: it returns ``False`` whenever the stat
    itself fails (symlink loop, unsearchable parent, EACCES, EIO), so an
    index that is present but unreadable would be reported as a missing
    notice -- sending the operator after the wrong problem, and silently
    replacing the ``could not be opened`` error ``db.py`` raises. ``state.
    read``'s docstring records the same hazard as the reason it has no
    ``exists()`` pre-check either.

    A self-referential symlink is the uid-independent way to make ``stat``
    fail with something other than ENOENT (a ``chmod`` test would pass
    trivially under root)."""
    index_path = tmp_path / ".herald" / "herald.db"
    index_path.parent.mkdir(parents=True)
    index_path.symlink_to(index_path)

    with pytest.raises(HeraldError, match="could not be opened") as excinfo:
        call(tmp_path)
    assert wrong_message not in str(excinfo.value)
