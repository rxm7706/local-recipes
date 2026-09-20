"""Story 9.1 (scaled down): SQLite-backed claim storage (Story 13.3 moved
the backing store from ``claims.json`` to ``db.py``'s shared
``.herald/herald.db``) -- create, read, publish, revalidate.

Every case uses an explicit ``tmp_path``-derived path named ``herald.db``,
not ``claims.json`` -- Story 13.3's one-time legacy import looks for a
sibling file literally named ``claims.json`` next to the database file, so
a test path sharing that name would collide with the DB file itself;
production code never hits this because ``DEFAULT_CLAIMS_PATH`` is
``.herald/herald.db``, never ``claims.json``."""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from pyforge.herald import claims, errors
from pyforge.herald import evidence as evidence_mod


def test_create_writes_a_draft_claim(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(path, project_name="warden", shipped_date="2026-08-01")
    assert claim.status == "draft"
    assert claim.thesis is None
    assert claim.shipped_date == "2026-08-01"
    assert claim.evidence == ()
    assert claim.edit_history == ()
    assert path.exists()


def test_create_defaults_shipped_date_to_today(tmp_path):
    claim = claims.create(
        tmp_path / "herald.db",
        project_name="warden",
        today=lambda: __import__("datetime").date(2026, 8, 8),
    )
    assert claim.shipped_date == "2026-08-08"


def test_create_rejects_empty_project_name(tmp_path):
    with pytest.raises(errors.HeraldError):
        claims.create(tmp_path / "herald.db", project_name="")


def test_create_rejects_a_whitespace_only_project_name(tmp_path):
    """Regression: `not project_name` only caught falsy strings -- a
    whitespace-only name ("   ") is truthy in Python and sailed through,
    creating a claim visually unidentifiable in `list` output."""
    with pytest.raises(errors.HeraldError):
        claims.create(tmp_path / "herald.db", project_name="   ")


def test_create_rejects_unknown_evidence_type(tmp_path):
    with pytest.raises(errors.HeraldError):
        claims.create(
            tmp_path / "herald.db",
            project_name="warden",
            evidence=[claims.Evidence(type="bogus", url="https://x", label="x")],
        )


def test_create_is_idempotent_id_wise_and_appends(tmp_path):
    path = tmp_path / "herald.db"
    first = claims.create(path, project_name="warden")
    second = claims.create(path, project_name="marshal")
    assert first.id != second.id
    stored = claims.read_all(path)
    assert {c.id for c in stored} == {first.id, second.id}


def test_read_one_missing_claim_raises_claim_not_found(tmp_path):
    path = tmp_path / "herald.db"
    claims.create(path, project_name="warden")
    with pytest.raises(errors.ClaimNotFoundError):
        claims.read_one(path, "does-not-exist")


def test_read_one_is_not_blocked_by_an_unrelated_malformed_entry(tmp_path):
    """Regression (JSON era): `read_one` went through `read_all`, which
    eagerly decoded EVERY entry -- one malformed entry anywhere in the
    file blocked looking up an unrelated, perfectly healthy claim by its
    exact id. Story 13.3's DB-backed `read_one` looks the row up directly
    by id (a targeted SQL `WHERE`), so an unrelated row's malformed
    `evidence` JSON column never comes into play at all -- simulated here
    by corrupting a SECOND row's `evidence` column directly, bypassing
    this module's own write path."""
    path = tmp_path / "herald.db"
    good = claims.create(path, project_name="warden")
    bad = claims.create(path, project_name="broken")
    raw = sqlite3.connect(path)
    raw.execute("UPDATE claims SET evidence = ? WHERE id = ?", ("{not valid json", bad.id))
    raw.commit()
    raw.close()

    found = claims.read_one(path, good.id)

    assert found.id == good.id
    with pytest.raises(errors.HeraldError):
        claims.read_one(path, bad.id)
    with pytest.raises(errors.HeraldError):
        claims.read_all(path)


def test_read_all_on_missing_file_is_empty(tmp_path):
    assert claims.read_all(tmp_path / "herald.db") == []


def test_read_all_rejects_a_corrupt_database_file(tmp_path):
    path = tmp_path / "herald.db"
    path.write_bytes(b"not a sqlite database")
    with pytest.raises(errors.HeraldError):
        claims.read_all(path)


def _fake_validator(valid_urls):
    def _validate(url):
        if url not in valid_urls:
            raise errors.EvidenceLinkError(f"Evidence link broken: {url}.")
        return object()

    return _validate


def test_publish_requires_a_thesis(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(path, project_name="warden")
    with pytest.raises(errors.HeraldError):
        claims.publish(path, claim.id, thesis=None, validate=_fake_validator(set()))


def test_publish_updates_status_and_timestamps(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="tests")],
    )
    published = claims.publish(path, claim.id, thesis="Shipped it", validate=_fake_validator({"https://ok"}))
    assert published.status == "published"
    assert published.thesis == "Shipped it"
    assert published.published_at is not None
    assert all(item.validated for item in published.evidence)
    assert all(item.validated_at is not None for item in published.evidence)


def test_publish_propagates_a_broken_evidence_link_and_writes_nothing(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://broken", label="tests")],
    )
    with pytest.raises(errors.EvidenceLinkError):
        claims.publish(path, claim.id, thesis="Shipped it", validate=_fake_validator(set()))
    # Unchanged on disk -- still draft.
    assert claims.read_one(path, claim.id).status == "draft"


def test_publish_names_every_broken_evidence_link_not_just_the_first(tmp_path):
    """Regression: raising on the first broken link meant an operator
    fixing evidence one publish-attempt at a time hit the next broken
    link on the next retry instead of seeing the full list once."""
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(type="test_results", url="https://bad1", label="a"),
            claims.Evidence(type="metrics", url="https://bad2", label="b"),
            claims.Evidence(type="adoption", url="https://bad3", label="c"),
        ],
    )
    with pytest.raises(errors.EvidenceLinkError) as exc_info:
        claims.publish(path, claim.id, thesis="Shipped it", validate=_fake_validator(set()))
    message = str(exc_info.value)
    assert "https://bad1" in message
    assert "https://bad2" in message
    assert "https://bad3" in message


def test_publish_twice_raises_claim_state_error(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(path, project_name="warden")
    claims.publish(path, claim.id, thesis="v1", validate=_fake_validator(set()))
    with pytest.raises(errors.ClaimStateError):
        claims.publish(path, claim.id, thesis="v2", validate=_fake_validator(set()))


def test_publish_with_a_new_thesis_preserves_the_old_one_in_edit_history(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(path, project_name="warden")
    # Give it an initial thesis by publishing once, then simulate an
    # edit-and-republish scenario is not supported (publish requires
    # draft) -- edit_history is instead exercised by seeding a claim whose
    # thesis is already set at create time via direct dataclass replace,
    # since `create` itself never sets a thesis (Story 9.2's own AC: thesis
    # is null until an operator provides one).
    from dataclasses import replace

    seeded = replace(claim, thesis="Original thesis")
    claims_list = claims.read_all(path)
    claims_list[0] = seeded
    claims._write_all(path, claims_list)
    published = claims.publish(path, claim.id, thesis="Revised thesis", validate=_fake_validator(set()))
    assert published.thesis == "Revised thesis"
    assert len(published.edit_history) == 1
    assert published.edit_history[0].thesis == "Original thesis"


def test_list_claims_filters_by_status(tmp_path):
    path = tmp_path / "herald.db"
    draft = claims.create(path, project_name="warden")
    published = claims.create(path, project_name="marshal")
    claims.publish(path, published.id, thesis="Shipped", validate=_fake_validator(set()))
    only_drafts = claims.list_claims(path, status="draft")
    assert [c.id for c in only_drafts] == [draft.id]


def test_list_claims_filters_by_date_range_and_excludes_unset_dates(tmp_path):
    import datetime as dt
    from dataclasses import replace

    path = tmp_path / "herald.db"
    in_range = claims.create(path, project_name="warden", shipped_date="2026-08-05")
    claims.create(path, project_name="marshal", shipped_date="2026-01-01")
    unset = claims.create(path, project_name="steward", shipped_date="2026-08-06")
    # Force a genuinely unset shipped_date -- `create` always defaults it to
    # today, so the "excluded" half of this test writes the record directly.
    stored = claims.read_all(path)
    stored = [replace(c, shipped_date=None) if c.id == unset.id else c for c in stored]
    claims._write_all(path, stored)
    result = claims.list_claims(path, date_range=(dt.date(2026, 8, 1), dt.date(2026, 8, 31)))
    assert [c.id for c in result] == [in_range.id]


def test_revalidate_updates_validated_flags_without_raising(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(type="test_results", url="https://ok", label="tests"),
            claims.Evidence(type="metrics", url="https://broken", label="metrics"),
        ],
    )

    class _Result:
        def __init__(self, is_valid):
            self.is_valid = is_valid

    def _validate_link(url):
        return _Result(is_valid=(url == "https://ok"))

    updated = claims.revalidate(path, claim.id, validate=_validate_link)
    by_url = {item.url: item.validated for item in updated.evidence}
    assert by_url == {"https://ok": True, "https://broken": False}


def test_revalidate_all_shares_one_timestamp(tmp_path):
    path = tmp_path / "herald.db"
    claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="t")],
    )
    claims.create(
        path,
        project_name="marshal",
        evidence=[claims.Evidence(type="metrics", url="https://ok2", label="m")],
    )

    class _Result:
        is_valid = True

    fixed_now = datetime(2026, 8, 8, tzinfo=UTC)
    updated = claims.revalidate_all(path, validate=lambda url: _Result(), now=lambda: fixed_now)
    timestamps = {item.validated_at for c in updated for item in c.evidence}
    assert timestamps == {fixed_now.isoformat()}


def test_revalidate_all_on_a_completely_missing_file_is_a_noop(tmp_path):
    """Story 11.2: no ``herald.db`` at all yet -- ``revalidate_all`` must
    not raise, and must still (harmlessly) round-trip an empty document."""
    path = tmp_path / "herald.db"
    assert claims.revalidate_all(path) == []
    assert claims.read_all(path) == []


def test_is_stale_true_when_never_validated():
    item = claims.Evidence(type="test_results", url="https://x", label="x")
    assert claims.is_stale(item, now=datetime.now(UTC)) is True


def test_is_stale_false_within_window():
    now = datetime.now(UTC)
    item = claims.Evidence(
        type="test_results",
        url="https://x",
        label="x",
        validated=True,
        validated_at=(now - timedelta(days=1)).isoformat(),
    )
    assert claims.is_stale(item, now=now) is False


def test_is_stale_true_past_the_window():
    now = datetime.now(UTC)
    item = claims.Evidence(
        type="test_results",
        url="https://x",
        label="x",
        validated=True,
        validated_at=(now - timedelta(days=10)).isoformat(),
    )
    assert claims.is_stale(item, now=now) is True


def test_to_dict_includes_computed_is_stale(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://x", label="x")],
    )
    payload = claims.to_dict(claim)
    assert payload["evidence"][0]["is_stale"] is True
    assert payload["id"] == claim.id


# --- Story 9.4: web-snapshot payload --------------------------------------


def test_snapshot_only_includes_matching_status(tmp_path):
    path = tmp_path / "herald.db"
    claims.create(path, project_name="draft-one")
    published = claims.create(path, project_name="published-one")
    claims.publish(path, published.id, thesis="Shipped", validate=_fake_validator(set()))
    result = claims.snapshot(path, status="published")
    assert [entry["id"] for entry in result] == [published.id]


def test_snapshot_is_newest_first_by_published_at(tmp_path):
    import datetime as dt

    path = tmp_path / "herald.db"
    older = claims.create(path, project_name="older")
    newer = claims.create(path, project_name="newer")
    claims.publish(
        path,
        older.id,
        thesis="Older",
        validate=_fake_validator(set()),
        now=lambda: dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    )
    claims.publish(
        path,
        newer.id,
        thesis="Newer",
        validate=_fake_validator(set()),
        now=lambda: dt.datetime(2026, 8, 1, tzinfo=dt.UTC),
    )
    result = claims.snapshot(path, status="published")
    assert [entry["id"] for entry in result] == [newer.id, older.id]


def test_snapshot_empty_when_no_claims_match(tmp_path):
    path = tmp_path / "herald.db"
    claims.create(path, project_name="draft-only")
    assert claims.snapshot(path, status="published") == []


# --- Story 11.3: cross-Moment evidence linking (claim -> notice) --------


def test_notice_type_evidence_is_a_valid_evidence_type(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="notice", url="auth-api-v1", label="notice: auth-api-v1")],
    )
    assert claim.evidence[0].type == "notice"
    assert claim.evidence[0].url == "auth-api-v1"


def test_publish_never_http_validates_notice_type_evidence(tmp_path):
    """A `notice`-type evidence entry's `url` is a component name, not an
    HTTP URL -- `publish` must never hand it to `validate`, or a real
    validator would try to HEAD a bare component name and always fail."""
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="notice", url="auth-api-v1", label="notice: auth-api-v1")],
    )

    def _validate_that_always_raises(url):
        raise errors.EvidenceLinkError(f"Evidence link broken: {url}.")

    published = claims.publish(path, claim.id, thesis="Shipped it", validate=_validate_that_always_raises)
    assert published.status == "published"
    assert published.evidence[0].validated is True


def test_revalidate_never_http_validates_notice_type_evidence(tmp_path):
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(type="notice", url="auth-api-v1", label="notice: auth-api-v1"),
            claims.Evidence(type="test_results", url="https://ok", label="tests"),
        ],
    )

    class _Result:
        def __init__(self, is_valid):
            self.is_valid = is_valid

    def _validate_link(url):
        # Would raise/misbehave if ever called with the notice's component
        # name instead of a real URL.
        return _Result(is_valid=(url == "https://ok"))

    updated = claims.revalidate(path, claim.id, validate=_validate_link)
    by_url = {item.url: item.validated for item in updated.evidence}
    assert by_url == {"auth-api-v1": True, "https://ok": True}


def test_referenced_by_claims_finds_claims_citing_a_notice(tmp_path):
    path = tmp_path / "herald.db"
    citing = claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="notice", url="auth-api-v1", label="notice: auth-api-v1")],
    )
    claims.create(path, project_name="marshal")  # no evidence -- not a match
    claims.create(
        path,
        project_name="mason",
        evidence=[claims.Evidence(type="notice", url="other-component", label="notice: other-component")],
    )
    result = claims.referenced_by_claims(path, "auth-api-v1")
    assert [c.id for c in result] == [citing.id]


def test_referenced_by_claims_empty_when_no_claim_cites_it(tmp_path):
    path = tmp_path / "herald.db"
    claims.create(path, project_name="warden")
    assert claims.referenced_by_claims(path, "auth-api-v1") == []


def test_referenced_by_claims_on_missing_file_is_empty(tmp_path):
    assert claims.referenced_by_claims(tmp_path / "herald.db", "auth-api-v1") == []


# --- Story 13.1: concurrency (closing DW-1-4-2) -----------------------------


def _write_lock_is_currently_free(db_path) -> bool:
    """Independently attempts its OWN short-timeout ``BEGIN IMMEDIATE`` on
    ``db_path`` via a brand new connection -- ``True`` only if nothing else
    currently holds ``db.transaction``'s write lock. A genuinely separate
    connection (not ``db.py``'s own ambient-transaction machinery) is the
    point: this is a direct proof that SQLite's own lock is free, not a
    simulation.

    A short ``timeout`` (well under ``db._BUSY_TIMEOUT_MS``) makes "is it
    free right now" observable quickly instead of waiting out the whole
    generous production timeout on every failed attempt."""
    conn = sqlite3.connect(db_path, timeout=0.05, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError:
        return False
    else:
        conn.execute("ROLLBACK")
        return True
    finally:
        conn.close()


def test_two_concurrent_creates_for_different_projects_both_land(tmp_path, monkeypatch):
    """Story 13.1/13.3 regression: two ``create`` calls racing the same
    database must both survive -- forced, deterministic interleaving (not
    a timing-dependent sleep race). A monkeypatched delay right after
    ``read_all``'s read (called from inside ``create``'s own
    ``db.transaction``) gives the other creator's whole
    ``BEGIN IMMEDIATE`` attempt room to genuinely block during the pause --
    a second creator cannot even begin its own transaction until the first
    has committed. Fails against a version of ``create`` that does not
    hold the transaction across its read-modify-write span, passes against
    the real implementation."""
    path = tmp_path / "herald.db"
    original_read_all = claims.read_all

    def delayed_read_all(claims_path):
        result = original_read_all(claims_path)
        time.sleep(0.2)
        return result

    monkeypatch.setattr(claims, "read_all", delayed_read_all)

    barrier = threading.Barrier(2)

    def creator(project_name: str) -> None:
        barrier.wait(timeout=5)
        claims.create(path, project_name=project_name)

    t1 = threading.Thread(target=creator, args=("alpha",))
    t2 = threading.Thread(target=creator, args=("beta",))
    t1.start()
    t2.start()
    # Bounded joins plus an explicit liveness assertion: without it a genuine
    # deadlock regression fails below with a confusing content mismatch that
    # reads as a lost update rather than a hang, and leaves two abandoned
    # threads still holding the lock for the rest of the session.
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive(), "a writer deadlocked on the lock"

    project_names = {c.project_name for c in original_read_all(path)}
    assert project_names == {"alpha", "beta"}


def test_publish_never_holds_the_lock_during_network_validation(tmp_path):
    """Story 13.1/13.3: ``publish``'s transaction must never span the
    network validation call. Direct proof: the injected validator attempts
    its OWN independent ``BEGIN IMMEDIATE`` against the SAME database
    ``publish`` uses -- if ``publish`` were (incorrectly) already holding
    the write lock during validation, this independent attempt would
    fail."""
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="tests")],
    )
    observed: list[bool] = []

    class _Result:
        is_valid = True

    def _validate(url):
        observed.append(_write_lock_is_currently_free(path))
        return _Result()

    published = claims.publish(path, claim.id, thesis="Shipped it", validate=_validate)

    assert observed == [True]
    assert published.status == "published"


def test_revalidate_all_never_holds_the_lock_during_network_validation(tmp_path):
    """Same proof as ``publish``'s own test, for ``revalidate_all`` --
    every evidence link across every claim is validated (real HTTP, in
    principle) before the transaction ever opens."""
    path = tmp_path / "herald.db"
    claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="tests")],
    )
    observed: list[bool] = []

    class _Result:
        is_valid = True

    def _validate(url):
        observed.append(_write_lock_is_currently_free(path))
        return _Result()

    claims.revalidate_all(path, validate=_validate)

    assert observed == [True]


def test_revalidate_all_scopes_validation_results_per_claim_not_globally(tmp_path):
    """Story 13.1 pass-2 regression: two DIFFERENT claims sharing a
    field-identical evidence entry (same url/type/label) must each keep
    the outcome of ITS OWN validation call, never a sibling claim's.
    ``Evidence`` is a frozen, value-equal dataclass, so a flat
    ``dict[Evidence, Evidence]`` built across every claim's evidence would
    collide the two identical entries onto the same dict key, letting the
    second claim's validation call silently overwrite the first's stored
    result. This test FAILS against that flat-dict shape (both claims
    would end up with the SECOND call's outcome) and PASSES against the
    per-claim-scoped ``validated_by_claim`` fix."""
    path = tmp_path / "herald.db"
    shared_evidence = claims.Evidence(type="test_results", url="https://ci.example/run-1", label="CI run")
    claims.create(path, project_name="alpha", evidence=[shared_evidence])
    claims.create(path, project_name="beta", evidence=[shared_evidence])

    # Alternate is_valid by call order: the first evidence entry validated
    # (alpha's, claims are read back in creation order) gets True, the
    # second (beta's) gets False. Both entries are BYTE-IDENTICAL Evidence
    # values, so only a per-claim-scoped map can keep the two outcomes
    # distinct instead of collapsing onto one shared dict key.
    call_count = 0

    class _Result:
        def __init__(self, is_valid: bool) -> None:
            self.is_valid = is_valid

    def _validate(url):
        nonlocal call_count
        call_count += 1
        return _Result(is_valid=(call_count == 1))

    updated = claims.revalidate_all(path, validate=_validate)
    by_project = {c.project_name: c for c in updated}

    assert by_project["alpha"].evidence[0].validated is True
    assert by_project["beta"].evidence[0].validated is False


def test_concurrent_publish_on_the_same_claim_rejects_the_second_caller(tmp_path, monkeypatch):
    """Story 13.1 pass-3 regression: ``publish()`` re-read the fresh claims
    state inside the lock but never re-checked ``status`` against it before
    unconditionally overwriting -- two concurrent ``publish()`` calls on the
    SAME claim_id both passed the pre-lock (unlocked) ``status != "draft"``
    guard, and the second silently clobbered the first's published state
    (new ``published_at``/``thesis``/evidence) instead of raising
    ``errors.ClaimStateError``. Forced, deterministic interleaving (not a
    timing-dependent sleep race), mirroring
    ``test_two_concurrent_creates_for_different_projects_both_land``: a
    monkeypatched delay on EVERY ``read_all`` call ensures both threads'
    pre-lock reads land (both still see "draft") before either thread's
    locked write completes -- exactly the window the bug needs. Fails
    against the pre-fix code (both calls "succeed", the second thread's
    data silently wins on disk); passes against the fixed code (exactly one
    call succeeds, the other raises ``ClaimStateError``) -- confirmed
    locally by commenting out the in-lock re-check."""
    path = tmp_path / "herald.db"
    claim = claims.create(path, project_name="warden")
    original_read_all = claims.read_all

    def delayed_read_all(claims_path):
        result = original_read_all(claims_path)
        time.sleep(0.2)
        return result

    monkeypatch.setattr(claims, "read_all", delayed_read_all)

    barrier = threading.Barrier(2)
    results: list[claims.Claim] = []
    state_errors: list[errors.ClaimStateError] = []
    results_lock = threading.Lock()

    def publisher(thesis: str) -> None:
        barrier.wait(timeout=5)
        try:
            result = claims.publish(path, claim.id, thesis=thesis, validate=_fake_validator(set()))
        except errors.ClaimStateError as exc:
            with results_lock:
                state_errors.append(exc)
        else:
            with results_lock:
                results.append(result)

    t1 = threading.Thread(target=publisher, args=("thesis-a",))
    t2 = threading.Thread(target=publisher, args=("thesis-b",))
    t1.start()
    t2.start()
    # Bounded joins plus an explicit liveness assertion: without it a genuine
    # deadlock regression fails below with a confusing content mismatch that
    # reads as a lost update rather than a hang, and leaves two abandoned
    # threads still holding the lock for the rest of the session.
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive() and not t2.is_alive(), "a writer deadlocked on the lock"

    assert len(results) == 1, "exactly one concurrent publish() must succeed"
    assert len(state_errors) == 1, (
        "the other concurrent publish() must raise ClaimStateError, not silently overwrite the first's published state"
    )
    assert results[0].status == "published"
    # The claim on disk matches the ONE successful call's thesis -- never
    # silently clobbered by the rejected caller's stale write.
    stored = original_read_all(path)[0]
    assert stored.thesis == results[0].thesis


def test_revalidate_all_does_not_stamp_updated_at_on_a_claim_it_never_validated(tmp_path, monkeypatch):
    """Story 13.1 pass-3 regression: ``revalidate_all``'s locked loop
    stamped ``updated_at`` on EVERY claim in the fresh in-lock read, even
    one absent from the pre-lock ``validated_by_claim`` map (created
    concurrently, after this run's validation scan already read the file)
    -- its evidence passed through unchanged, but its ``updated_at`` was
    still bumped even though this run never actually checked it. Simulates
    the race deterministically: a claim is written directly to disk in
    between ``revalidate_all``'s two ``read_all`` calls (the pre-lock scan
    and the in-lock fresh read), so the pre-lock ``validated_by_claim`` map
    never sees it. Fails against the pre-fix code (the new claim's
    ``updated_at`` gets stamped with the batch's shared timestamp); passes
    against the fixed code (the new claim comes back byte-for-byte
    unchanged) -- confirmed locally by reverting to the unconditional
    ``replace()`` call."""
    path = tmp_path / "herald.db"
    claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="t")],
    )
    original_read_all = claims.read_all
    call_count = 0
    original_updated_at = "2020-01-01T00:00:00+00:00"

    def read_all_with_late_arrival(claims_path):
        nonlocal call_count
        call_count += 1
        result = original_read_all(claims_path)
        if call_count == 1:
            # Simulate a claim created concurrently, immediately AFTER this
            # run's pre-lock validation scan already read the file --
            # `validated_by_claim` (built from THIS read) never sees it.
            # Written directly (not via `claims.create`) to avoid
            # recursing back through this same monkeypatched `read_all`.
            latecomer = claims.Claim(
                id="concurrent-claim",
                project_name="latecomer",
                status="draft",
                thesis=None,
                shipped_date=None,
                created_at=original_updated_at,
                published_at=None,
                closed_at=None,
                updated_at=original_updated_at,
                evidence=(),
                edit_history=(),
            )
            claims._write_all(claims_path, [*result, latecomer])
        return result

    monkeypatch.setattr(claims, "read_all", read_all_with_late_arrival)

    class _Result:
        is_valid = True

    fixed_now = datetime(2026, 8, 8, tzinfo=UTC)
    updated = claims.revalidate_all(path, validate=lambda url: _Result(), now=lambda: fixed_now)

    by_id = {c.id: c for c in updated}
    assert by_id["concurrent-claim"].updated_at == original_updated_at
    assert by_id["concurrent-claim"].evidence == ()
    # The claim the batch DID validate still gets the shared timestamp.
    warden = next(c for c in updated if c.project_name == "warden")
    assert warden.updated_at == fixed_now.isoformat()


# --- Story 13.1 pass 4: intra-claim duplicate evidence + publish's gate -----
#
# `Evidence` is a frozen, value-equal dataclass and `create` de-duplicates
# nothing (it validates only `type`), so ONE claim can legitimately carry two
# field-identical entries. Carrying the pre-lock validation results in a
# `dict[Evidence, Evidence]` collapses them onto a single key: two independent
# validation calls are made, but only the last result is kept and it is then
# applied to BOTH positions. The three tests below pin the index-aligned
# positional carry that replaced it -- each FAILS against the value-keyed
# shape and PASSES against the positional one.

_DUPLICATE_EVIDENCE = claims.Evidence(type="test_results", url="https://ci.example/run-1", label="CI run")


class _LinkResult:
    """The minimal ``evidence.LinkValidation`` shape ``revalidate`` reads."""

    def __init__(self, is_valid: bool) -> None:
        self.is_valid = is_valid


def _alternating_validator(outcomes):
    """A validator returning ``outcomes[n]`` for its ``n``-th call -- the two
    calls made for two field-identical entries therefore DISAGREE, which is
    exactly what a value-keyed map cannot represent."""
    calls = 0

    def _validate(url):
        nonlocal calls
        result = _LinkResult(is_valid=outcomes[calls])
        calls += 1
        return result

    _validate.call_count = lambda: calls
    return _validate


def test_publish_keeps_duplicate_evidence_entries_outcomes_distinct(tmp_path):
    """Story 13.1 pass-4 regression (``publish``): one claim carrying two
    field-identical evidence entries must have EACH POSITION validated on
    its own and each position's outcome honoured. Here the two calls
    disagree (the first check passes, the second hits a transient failure):
    publish must see the second position's breakage and reject the whole
    publish, never let the first position's success stand in for both."""
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[_DUPLICATE_EVIDENCE, _DUPLICATE_EVIDENCE],
    )
    calls = 0

    def _validate(url):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise errors.EvidenceLinkError(f"Evidence link broken: {url}.")
        return object()

    with pytest.raises(errors.EvidenceLinkError) as excinfo:
        claims.publish(path, claim.id, thesis="Shipped it", validate=_validate)

    # Both positions were checked independently -- not de-duplicated to a
    # single call -- and the second position's distinct outcome survived.
    assert calls == 2
    assert "1 broken evidence link" in str(excinfo.value)
    stored = claims.read_all(path)[0]
    assert stored.status == "draft"
    assert len(stored.evidence) == 2
    assert [e.validated for e in stored.evidence] == [False, False]


def test_revalidate_keeps_duplicate_evidence_entries_outcomes_distinct(tmp_path):
    """Story 13.1 pass-4 regression (``revalidate``): reproduced directly in
    review -- a claim with a duplicated link whose two checks return ``True``
    then ``False`` (a transient 429) stored ``[False, False]`` under the
    ``Evidence``-keyed map. Index-aligned positional carry stores
    ``[True, False]``."""
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[_DUPLICATE_EVIDENCE, _DUPLICATE_EVIDENCE],
    )
    validate = _alternating_validator([True, False])

    updated = claims.revalidate(path, claim.id, validate=validate)

    assert validate.call_count() == 2
    assert [e.validated for e in updated.evidence] == [True, False]
    assert [e.validated for e in claims.read_all(path)[0].evidence] == [True, False]


def test_revalidate_all_keeps_duplicate_evidence_entries_outcomes_distinct(tmp_path):
    """Story 13.1 pass-4 regression (``revalidate_all``): the same
    within-one-claim collapse as ``revalidate``'s test above, through the
    batch entry point. Per-claim-id scoping alone does not fix it -- the
    results carried under that id must themselves be index-aligned rather
    than value-keyed."""
    path = tmp_path / "herald.db"
    claims.create(
        path,
        project_name="warden",
        evidence=[_DUPLICATE_EVIDENCE, _DUPLICATE_EVIDENCE],
    )
    validate = _alternating_validator([True, False])

    updated = claims.revalidate_all(path, validate=validate)

    assert validate.call_count() == 2
    assert [e.validated for e in updated[0].evidence] == [True, False]
    assert [e.validated for e in claims.read_all(path)[0].evidence] == [True, False]


def test_publish_refuses_when_a_concurrent_writer_changed_evidence(tmp_path, monkeypatch):
    """Story 13.1 pass-4 regression: ``publish``'s contract is that a broken
    link blocks the publish and nothing is written. The discard-stale rule
    (right for ``revalidate``, whose job is to RECORD breakage) would instead
    pass a concurrently-changed evidence entry through UNVALIDATED, so the
    claim would persist as ``published`` carrying evidence this call never
    checked -- and which the concurrent writer may have just proved broken.

    Simulates the race deterministically rather than with a timing-dependent
    sleep: a rewritten claim is written straight to disk in between
    ``publish``'s two ``read_all`` calls (the pre-lock read its unlocked
    validation is computed from, and the in-lock fresh read), which is
    exactly the unlocked-HTTP window. Fails against the pass-through shape
    (the claim publishes over unvalidated evidence); passes against the
    in-lock re-verification."""
    path = tmp_path / "herald.db"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="tests")],
    )
    original_read_all = claims.read_all
    call_count = 0

    def read_all_with_concurrent_write(claims_path):
        nonlocal call_count
        call_count += 1
        result = original_read_all(claims_path)
        if call_count == 1:
            # A concurrent `revalidate` lands right after publish's pre-lock
            # read, rewriting the very entry publish is about to validate.
            # Written directly (not via `claims.revalidate`) to avoid
            # recursing back through this same monkeypatched `read_all`.
            claims._write_all(
                claims_path,
                [
                    replace(
                        c,
                        evidence=tuple(
                            replace(
                                e,
                                validated=False,
                                validated_at="2026-08-09T00:00:00+00:00",
                            )
                            for e in c.evidence
                        ),
                    )
                    for c in result
                ],
            )
        return result

    monkeypatch.setattr(claims, "read_all", read_all_with_concurrent_write)

    with pytest.raises(errors.ClaimStateError) as excinfo:
        claims.publish(
            path,
            claim.id,
            thesis="Shipped it",
            validate=_fake_validator({"https://ok"}),
        )

    assert claim.id in str(excinfo.value)
    stored = original_read_all(path)[0]
    assert stored.status == "draft", "publish must write nothing when it refuses"
    assert stored.published_at is None
    assert stored.thesis is None
    # The concurrent writer's value is intact -- never clobbered, never
    # silently published over.
    assert stored.evidence[0].validated is False
    assert stored.evidence[0].validated_at == "2026-08-09T00:00:00+00:00"


def _fixed_now(iso: str):
    return lambda: datetime.fromisoformat(iso)


def _ok(url: str):
    return evidence_mod.LinkValidation(
        url=url,
        is_valid=True,
        status=200,
        redirects=0,
        last_validated_at=datetime(2026, 8, 10, tzinfo=UTC),
    )


def test_revalidate_does_not_stamp_updated_at_when_every_result_was_discarded(
    tmp_path,
):
    """Story 13.1 pass-5 regression: the discard-stale rule can drop EVERY
    one of this run's validation results (a concurrent writer replaced the
    claim's evidence during the unlocked HTTP window). ``revalidate`` still
    stamped ``updated_at`` in that case, asserting "revalidated at T" when
    nothing this run computed was actually applied. Same defect pass 3 fixed
    one branch over for a concurrently-CREATED claim -- ``is_stale`` and
    ``snapshot`` both read these timestamps."""
    claims_path = tmp_path / "herald.db"
    ev = claims.Evidence(url="https://example.com/a", type="other", label="A")
    created = claims.create(
        claims_path,
        project_name="proj",
        evidence=(ev,),
        now=_fixed_now("2020-01-01T00:00:00+00:00"),
    )
    original_updated_at = claims.read_all(claims_path)[0].updated_at

    def validate_then_mutate(url: str):
        # Stand in for a concurrent writer landing between the unlocked
        # validation and the locked re-read.
        stored = claims.read_all(claims_path)
        stored[0] = replace(stored[0], evidence=(replace(ev, label="changed by someone else"),))
        claims._write_all(claims_path, stored)
        return _ok(url)

    out = claims.revalidate(
        claims_path,
        created.id,
        validate=validate_then_mutate,
        now=_fixed_now("2026-08-10T00:00:00+00:00"),
    )

    assert out.updated_at == original_updated_at, (
        "updated_at was stamped for a validation whose every result was discarded"
    )
    assert claims.read_all(claims_path)[0].updated_at == original_updated_at
    assert out.evidence[0].label == "changed by someone else"


def test_revalidate_all_does_not_stamp_updated_at_when_every_result_was_discarded(
    tmp_path,
):
    """``revalidate_all``'s twin of the case above. Pass 3 already refused to
    stamp a claim absent from the validation map; a claim that IS in the map
    but whose every evidence entry changed concurrently is the same "claim a
    validation that never happened" defect, and was not covered."""
    claims_path = tmp_path / "herald.db"
    ev = claims.Evidence(url="https://example.com/a", type="other", label="A")
    claims.create(
        claims_path,
        project_name="proj",
        evidence=(ev,),
        now=_fixed_now("2020-01-01T00:00:00+00:00"),
    )
    original_updated_at = claims.read_all(claims_path)[0].updated_at

    def validate_then_mutate(url: str):
        stored = claims.read_all(claims_path)
        stored[0] = replace(stored[0], evidence=(replace(ev, label="changed by someone else"),))
        claims._write_all(claims_path, stored)
        return _ok(url)

    out = claims.revalidate_all(
        claims_path,
        validate=validate_then_mutate,
        now=_fixed_now("2026-08-10T00:00:00+00:00"),
    )

    assert out[0].updated_at == original_updated_at
    assert claims.read_all(claims_path)[0].updated_at == original_updated_at


def test_revalidate_all_refuses_duplicate_claim_ids(tmp_path):
    """``revalidate_all`` keys its per-claim validation results by claim id,
    which is only sound while ids are unique -- two claims sharing an id
    would collapse onto one entry and let one claim's HTTP outcome overwrite
    the other's. Reachable via an injected ``id_factory`` or a merged/
    hand-written claims table. Refuse structurally (AD-6) rather than
    silently corrupting one of them."""
    claims_path = tmp_path / "herald.db"
    ev = claims.Evidence(url="https://example.com/a", type="other", label="A")
    claims.create(claims_path, project_name="one", evidence=(ev,), id_factory=lambda: "same-id")
    claims.create(claims_path, project_name="two", evidence=(ev,), id_factory=lambda: "same-id")

    with pytest.raises(errors.HeraldError, match="duplicate claim ids"):
        claims.revalidate_all(claims_path, validate=_ok)


def test_publish_does_not_revert_a_concurrently_changed_thesis(tmp_path):
    """``publish`` resolves its final thesis from the FRESH in-lock read, not
    from the pre-validation one.

    Deriving it from the pre-lock read makes ``publish`` a lost-update path
    for the field an operator is most likely to be editing: publishing with
    no ``--thesis`` while a concurrent writer sets a new one republishes the
    stale text AND files the newer text into ``edit_history`` as though it
    were the superseded version -- inverting the two. Exactly the class of
    silent lost update ``DW-1-4-2`` exists to close, on a field the
    evidence-focused fix did not cover."""
    claims_path = tmp_path / "herald.db"
    ev = claims.Evidence(url="https://example.com/a", type="other", label="A")
    claims.create(claims_path, project_name="proj", evidence=(ev,), id_factory=lambda: "id-1")
    stored = claims.read_all(claims_path)
    stored[0] = replace(stored[0], thesis="thesis-old")
    claims._write_all(claims_path, stored)

    def validate_then_edit_thesis(url: str):
        # A concurrent writer lands a newer thesis during the unlocked
        # HTTP-validation window.
        concurrent = claims.read_all(claims_path)
        concurrent[0] = replace(concurrent[0], thesis="thesis-new")
        claims._write_all(claims_path, concurrent)
        return _ok(url)

    published = claims.publish(
        claims_path,
        "id-1",
        validate=validate_then_edit_thesis,
        now=_fixed_now("2026-08-10T00:00:00+00:00"),
    )

    assert published.thesis == "thesis-new", "published the pre-validation thesis over a concurrent writer's newer one"
    assert [v.thesis for v in published.edit_history] == [], (
        "filed the NEWER thesis into edit_history as if it were superseded"
    )
    assert claims.read_all(claims_path)[0].thesis == "thesis-new"


def test_publish_still_archives_the_previous_thesis_when_one_is_supplied(tmp_path):
    """The counterpart to the test above: an explicitly supplied ``--thesis``
    still wins, and the value it replaces -- read fresh, under the lock --
    is what lands in ``edit_history``."""
    claims_path = tmp_path / "herald.db"
    claims.create(claims_path, project_name="proj", id_factory=lambda: "id-1")
    stored = claims.read_all(claims_path)
    stored[0] = replace(stored[0], thesis="thesis-old")
    claims._write_all(claims_path, stored)

    published = claims.publish(
        claims_path,
        "id-1",
        thesis="thesis-explicit",
        now=_fixed_now("2026-08-10T00:00:00+00:00"),
    )

    assert published.thesis == "thesis-explicit"
    assert [v.thesis for v in published.edit_history] == ["thesis-old"]


def test_publish_refuses_when_a_concurrent_writer_clears_the_thesis(tmp_path):
    """The pre-lock thesis check is a fail-fast, not the decision: when a
    concurrent writer clears the thesis during the unlocked validation
    window, the in-lock re-resolution has nothing to publish and must refuse
    with the same message rather than persist ``thesis=None``."""
    claims_path = tmp_path / "herald.db"
    ev = claims.Evidence(url="https://example.com/a", type="other", label="A")
    claims.create(claims_path, project_name="proj", evidence=(ev,), id_factory=lambda: "id-1")
    stored = claims.read_all(claims_path)
    stored[0] = replace(stored[0], thesis="thesis-old")
    claims._write_all(claims_path, stored)

    def validate_then_clear_thesis(url: str):
        concurrent = claims.read_all(claims_path)
        concurrent[0] = replace(concurrent[0], thesis=None)
        claims._write_all(claims_path, concurrent)
        return _ok(url)

    with pytest.raises(errors.HeraldError, match="has no thesis"):
        claims.publish(claims_path, "id-1", validate=validate_then_clear_thesis)

    assert claims.read_all(claims_path)[0].status == "draft"


def test_revalidate_does_not_stamp_updated_at_when_evidence_is_emptied_concurrently(
    tmp_path,
):
    """The every-result-discarded guard must key off what this run actually
    VALIDATED, not off the fresh read.

    A concurrent writer that empties the evidence tuple leaves
    ``fresh_claim.evidence`` falsy, so a guard written as
    ``if fresh_claim.evidence and not any(carried)`` skips exactly the case
    it exists to catch and stamps ``updated_at`` for a validation whose
    every result was thrown away."""
    claims_path = tmp_path / "herald.db"
    ev = claims.Evidence(url="https://example.com/a", type="other", label="A")
    claims.create(
        claims_path,
        project_name="proj",
        evidence=(ev,),
        id_factory=lambda: "id-1",
        now=_fixed_now("2020-01-01T00:00:00+00:00"),
    )
    original_updated_at = claims.read_all(claims_path)[0].updated_at

    def validate_then_empty_evidence(url: str):
        concurrent = claims.read_all(claims_path)
        concurrent[0] = replace(concurrent[0], evidence=())
        claims._write_all(claims_path, concurrent)
        return _ok(url)

    out = claims.revalidate(
        claims_path,
        "id-1",
        validate=validate_then_empty_evidence,
        now=_fixed_now("2026-08-10T00:00:00+00:00"),
    )

    assert out.updated_at == original_updated_at
    assert claims.read_all(claims_path)[0].updated_at == original_updated_at


def test_revalidate_all_does_not_stamp_updated_at_when_evidence_is_emptied(tmp_path):
    """``revalidate_all``'s twin of the case above."""
    claims_path = tmp_path / "herald.db"
    ev = claims.Evidence(url="https://example.com/a", type="other", label="A")
    claims.create(
        claims_path,
        project_name="proj",
        evidence=(ev,),
        id_factory=lambda: "id-1",
        now=_fixed_now("2020-01-01T00:00:00+00:00"),
    )
    original_updated_at = claims.read_all(claims_path)[0].updated_at

    def validate_then_empty_evidence(url: str):
        concurrent = claims.read_all(claims_path)
        concurrent[0] = replace(concurrent[0], evidence=())
        claims._write_all(claims_path, concurrent)
        return _ok(url)

    out = claims.revalidate_all(
        claims_path,
        validate=validate_then_empty_evidence,
        now=_fixed_now("2026-08-10T00:00:00+00:00"),
    )

    assert out[0].updated_at == original_updated_at
    assert claims.read_all(claims_path)[0].updated_at == original_updated_at


def test_revalidate_does_not_stamp_updated_at_when_evidence_appears_concurrently(
    tmp_path,
):
    """The mirror image of the emptied-concurrently case: a claim that had
    NO evidence when this run read it, given evidence by a concurrent writer
    during the unlocked window.

    Zero ``validate`` calls were made, so not one of the entries about to be
    written was checked by this run -- stamping ``updated_at`` would assert a
    validation that never happened, the same defect the emptied-concurrently
    guard closes from the other direction. A guard keyed only on
    ``original_evidence`` misses it, because the tuple this run validated is
    the empty one."""
    claims_path = tmp_path / "herald.db"
    claims.create(
        claims_path,
        project_name="proj",
        id_factory=lambda: "id-1",
        now=_fixed_now("2020-01-01T00:00:00+00:00"),
    )
    original_updated_at = claims.read_all(claims_path)[0].updated_at
    added = claims.Evidence(url="https://example.com/a", type="other", label="A")

    def now_then_add_evidence():
        # `revalidate` calls now() after its pre-lock read and before the
        # lock -- the only seam available here, since a claim with no
        # evidence never calls `validate` at all.
        concurrent = claims.read_all(claims_path)
        concurrent[0] = replace(concurrent[0], evidence=(added,))
        claims._write_all(claims_path, concurrent)
        return datetime.fromisoformat("2026-08-10T00:00:00+00:00")

    out = claims.revalidate(claims_path, "id-1", now=now_then_add_evidence)

    assert out.updated_at == original_updated_at
    stored = claims.read_all(claims_path)[0]
    assert stored.updated_at == original_updated_at
    assert stored.evidence == (added,), "the concurrent writer's entry was clobbered"
    assert stored.evidence[0].validated_at is None, (
        "an entry this run never validated carries this run's validation stamp"
    )


def test_revalidate_all_does_not_stamp_updated_at_when_evidence_appears(tmp_path):
    """``revalidate_all``'s twin of the case above -- and proof it stays
    per-claim: the sibling claim this run DID validate is still updated
    normally."""
    claims_path = tmp_path / "herald.db"
    checked = claims.Evidence(url="https://example.com/b", type="other", label="B")
    claims.create(
        claims_path,
        project_name="proj",
        id_factory=lambda: "id-1",
        now=_fixed_now("2020-01-01T00:00:00+00:00"),
    )
    claims.create(
        claims_path,
        project_name="proj",
        evidence=(checked,),
        id_factory=lambda: "id-2",
        now=_fixed_now("2020-01-01T00:00:00+00:00"),
    )
    original_updated_at = claims.read_all(claims_path)[0].updated_at
    added = claims.Evidence(url="https://example.com/a", type="other", label="A")

    def validate_then_add_evidence(url: str):
        # Called only for id-2's entry; id-1 has nothing to validate. Use it
        # as the seam that gives id-1 evidence mid-window.
        stored = claims.read_all(claims_path)
        stored[0] = replace(stored[0], evidence=(added,))
        claims._write_all(claims_path, stored)
        return _ok(url)

    out = claims.revalidate_all(
        claims_path,
        validate=validate_then_add_evidence,
        now=_fixed_now("2026-08-10T00:00:00+00:00"),
    )

    by_id = {c.id: c for c in out}
    assert by_id["id-1"].updated_at == original_updated_at
    assert by_id["id-1"].evidence == (added,)
    assert by_id["id-1"].evidence[0].validated_at is None
    assert by_id["id-2"].updated_at == "2026-08-10T00:00:00+00:00"
    assert by_id["id-2"].evidence[0].validated is True


def test_revalidate_still_stamps_updated_at_for_a_claim_with_no_evidence(tmp_path):
    """The guard above must NOT catch a claim that simply has no evidence:
    nothing was validated, but nothing was discarded either, so it keeps the
    ordinary ``updated_at`` stamp it had before Story 13.1. Guards the fix
    for the emptied-concurrently case against overshooting into a behavior
    change for the plain single-writer path."""
    claims_path = tmp_path / "herald.db"
    claims.create(
        claims_path,
        project_name="proj",
        id_factory=lambda: "id-1",
        now=_fixed_now("2020-01-01T00:00:00+00:00"),
    )

    out = claims.revalidate(claims_path, "id-1", now=_fixed_now("2026-08-10T00:00:00+00:00"))

    assert out.updated_at == "2026-08-10T00:00:00+00:00"


def test_revalidate_all_refuses_a_duplicate_id_written_during_validation(tmp_path):
    """The duplicate-id guard must run against the FRESH in-lock read too.

    Checked only against the pre-lock read, a duplicate written during the
    unlocked HTTP window sails past it -- and the in-lock loop, which looks
    results up in the fresh list, then applies one claim's single validation
    outcome (and this run's ``updated_at``) to BOTH same-id claims. That is
    precisely the collapse the guard exists to refuse, reached by the one
    path the guard did not cover."""
    claims_path = tmp_path / "herald.db"
    ev = claims.Evidence(url="https://example.com/a", type="other", label="A")
    claims.create(claims_path, project_name="one", evidence=(ev,), id_factory=lambda: "id-1")

    def validate_then_clone_the_claim(url: str):
        concurrent = claims.read_all(claims_path)
        twin = replace(concurrent[0], project_name="clone-of-one")  # same id
        claims._write_all(claims_path, [*concurrent, twin])
        return _ok(url)

    with pytest.raises(errors.HeraldError, match="duplicate claim ids"):
        claims.revalidate_all(claims_path, validate=validate_then_clone_the_claim)
