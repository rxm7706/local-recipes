"""Story 9.1 (scaled down): local ``claims.json`` storage -- create, read,
publish, revalidate, and the atomic-write/round-trip discipline mirroring
``state.py``.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from pyforge.herald import claims, errors


def test_create_writes_a_draft_claim(tmp_path):
    path = tmp_path / "claims.json"
    claim = claims.create(path, project_name="warden", shipped_date="2026-08-01")
    assert claim.status == "draft"
    assert claim.thesis is None
    assert claim.shipped_date == "2026-08-01"
    assert claim.evidence == ()
    assert claim.edit_history == ()
    assert path.exists()


def test_create_defaults_shipped_date_to_today(tmp_path):
    claim = claims.create(
        tmp_path / "claims.json",
        project_name="warden",
        today=lambda: __import__("datetime").date(2026, 8, 8),
    )
    assert claim.shipped_date == "2026-08-08"


def test_create_rejects_empty_project_name(tmp_path):
    with pytest.raises(errors.HeraldError):
        claims.create(tmp_path / "claims.json", project_name="")


def test_create_rejects_a_whitespace_only_project_name(tmp_path):
    """Regression: `not project_name` only caught falsy strings -- a
    whitespace-only name ("   ") is truthy in Python and sailed through,
    creating a claim visually unidentifiable in `list` output."""
    with pytest.raises(errors.HeraldError):
        claims.create(tmp_path / "claims.json", project_name="   ")


def test_create_rejects_unknown_evidence_type(tmp_path):
    with pytest.raises(errors.HeraldError):
        claims.create(
            tmp_path / "claims.json",
            project_name="warden",
            evidence=[claims.Evidence(type="bogus", url="https://x", label="x")],
        )


def test_create_is_idempotent_id_wise_and_appends(tmp_path):
    path = tmp_path / "claims.json"
    first = claims.create(path, project_name="warden")
    second = claims.create(path, project_name="marshal")
    assert first.id != second.id
    stored = claims.read_all(path)
    assert {c.id for c in stored} == {first.id, second.id}


def test_read_one_missing_claim_raises_claim_not_found(tmp_path):
    path = tmp_path / "claims.json"
    claims.create(path, project_name="warden")
    with pytest.raises(errors.ClaimNotFoundError):
        claims.read_one(path, "does-not-exist")


def test_read_one_is_not_blocked_by_an_unrelated_malformed_entry(tmp_path):
    """Regression: `read_one` went through `read_all`, which eagerly
    decodes EVERY entry -- one malformed entry anywhere in the file
    blocked looking up an unrelated, perfectly healthy claim by its exact
    id. `read_one` now decodes entries lazily, only raising if the
    MATCHED entry itself is the malformed one."""
    path = tmp_path / "claims.json"
    good = claims.create(path, project_name="warden")
    raw = claims._load_document(path)
    raw.append({"id": "bad-entry", "project_name": "broken"})  # missing fields
    path.write_text(json.dumps(raw), encoding="utf-8")

    found = claims.read_one(path, good.id)

    assert found.id == good.id
    with pytest.raises(errors.HeraldError):
        claims.read_one(path, "bad-entry")
    with pytest.raises(errors.HeraldError):
        claims.read_all(path)


def test_read_all_on_missing_file_is_empty(tmp_path):
    assert claims.read_all(tmp_path / "claims.json") == []


def test_read_all_rejects_malformed_json(tmp_path):
    path = tmp_path / "claims.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(errors.HeraldError):
        claims.read_all(path)


def test_read_all_rejects_non_list_top_level(tmp_path):
    path = tmp_path / "claims.json"
    path.write_text('{"not": "a list"}', encoding="utf-8")
    with pytest.raises(errors.HeraldError):
        claims.read_all(path)


def test_read_all_rejects_unknown_field_on_a_claim(tmp_path):
    path = tmp_path / "claims.json"
    claims.create(path, project_name="warden")
    stored = claims.read_all(path)
    doc = [
        {
            "id": stored[0].id,
            "project_name": "warden",
            "status": "draft",
            "thesis": None,
            "shipped_date": None,
            "created_at": stored[0].created_at,
            "published_at": None,
            "closed_at": None,
            "updated_at": stored[0].updated_at,
            "evidence": [],
            "edit_history": [],
            "totally_unknown_field": "oops",
        }
    ]
    import json

    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(errors.HeraldError):
        claims.read_all(path)


def _fake_validator(valid_urls):
    def _validate(url):
        if url not in valid_urls:
            raise errors.EvidenceLinkError(f"Evidence link broken: {url}.")
        return object()

    return _validate


def test_publish_requires_a_thesis(tmp_path):
    path = tmp_path / "claims.json"
    claim = claims.create(path, project_name="warden")
    with pytest.raises(errors.HeraldError):
        claims.publish(path, claim.id, thesis=None, validate=_fake_validator(set()))


def test_publish_updates_status_and_timestamps(tmp_path):
    path = tmp_path / "claims.json"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(type="test_results", url="https://ok", label="tests")
        ],
    )
    published = claims.publish(
        path, claim.id, thesis="Shipped it", validate=_fake_validator({"https://ok"})
    )
    assert published.status == "published"
    assert published.thesis == "Shipped it"
    assert published.published_at is not None
    assert all(item.validated for item in published.evidence)
    assert all(item.validated_at is not None for item in published.evidence)


def test_publish_propagates_a_broken_evidence_link_and_writes_nothing(tmp_path):
    path = tmp_path / "claims.json"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(type="test_results", url="https://broken", label="tests")
        ],
    )
    with pytest.raises(errors.EvidenceLinkError):
        claims.publish(
            path, claim.id, thesis="Shipped it", validate=_fake_validator(set())
        )
    # Unchanged on disk -- still draft.
    assert claims.read_one(path, claim.id).status == "draft"


def test_publish_names_every_broken_evidence_link_not_just_the_first(tmp_path):
    """Regression: raising on the first broken link meant an operator
    fixing evidence one publish-attempt at a time hit the next broken
    link on the next retry instead of seeing the full list once."""
    path = tmp_path / "claims.json"
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
        claims.publish(
            path, claim.id, thesis="Shipped it", validate=_fake_validator(set())
        )
    message = str(exc_info.value)
    assert "https://bad1" in message
    assert "https://bad2" in message
    assert "https://bad3" in message


def test_publish_twice_raises_claim_state_error(tmp_path):
    path = tmp_path / "claims.json"
    claim = claims.create(path, project_name="warden")
    claims.publish(path, claim.id, thesis="v1", validate=_fake_validator(set()))
    with pytest.raises(errors.ClaimStateError):
        claims.publish(path, claim.id, thesis="v2", validate=_fake_validator(set()))


def test_publish_with_a_new_thesis_preserves_the_old_one_in_edit_history(tmp_path):
    path = tmp_path / "claims.json"
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
    published = claims.publish(
        path, claim.id, thesis="Revised thesis", validate=_fake_validator(set())
    )
    assert published.thesis == "Revised thesis"
    assert len(published.edit_history) == 1
    assert published.edit_history[0].thesis == "Original thesis"


def test_list_claims_filters_by_status(tmp_path):
    path = tmp_path / "claims.json"
    draft = claims.create(path, project_name="warden")
    published = claims.create(path, project_name="marshal")
    claims.publish(
        path, published.id, thesis="Shipped", validate=_fake_validator(set())
    )
    only_drafts = claims.list_claims(path, status="draft")
    assert [c.id for c in only_drafts] == [draft.id]


def test_list_claims_filters_by_date_range_and_excludes_unset_dates(tmp_path):
    import datetime as dt
    from dataclasses import replace

    path = tmp_path / "claims.json"
    in_range = claims.create(path, project_name="warden", shipped_date="2026-08-05")
    claims.create(path, project_name="marshal", shipped_date="2026-01-01")
    unset = claims.create(path, project_name="steward", shipped_date="2026-08-06")
    # Force a genuinely unset shipped_date -- `create` always defaults it to
    # today, so the "excluded" half of this test writes the record directly.
    stored = claims.read_all(path)
    stored = [replace(c, shipped_date=None) if c.id == unset.id else c for c in stored]
    claims._write_all(path, stored)
    result = claims.list_claims(
        path, date_range=(dt.date(2026, 8, 1), dt.date(2026, 8, 31))
    )
    assert [c.id for c in result] == [in_range.id]


def test_revalidate_updates_validated_flags_without_raising(tmp_path):
    path = tmp_path / "claims.json"
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
    path = tmp_path / "claims.json"
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
    updated = claims.revalidate_all(
        path, validate=lambda url: _Result(), now=lambda: fixed_now
    )
    timestamps = {item.validated_at for c in updated for item in c.evidence}
    assert timestamps == {fixed_now.isoformat()}


def test_revalidate_all_on_a_completely_missing_file_is_a_noop(tmp_path):
    """Story 11.2: no ``claims.json`` at all yet -- ``revalidate_all`` must
    not raise, and must still (harmlessly) round-trip an empty document."""
    path = tmp_path / "claims.json"
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
    path = tmp_path / "claims.json"
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
    path = tmp_path / "claims.json"
    claims.create(path, project_name="draft-one")
    published = claims.create(path, project_name="published-one")
    claims.publish(
        path, published.id, thesis="Shipped", validate=_fake_validator(set())
    )
    result = claims.snapshot(path, status="published")
    assert [entry["id"] for entry in result] == [published.id]


def test_snapshot_is_newest_first_by_published_at(tmp_path):
    import datetime as dt

    path = tmp_path / "claims.json"
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
    path = tmp_path / "claims.json"
    claims.create(path, project_name="draft-only")
    assert claims.snapshot(path, status="published") == []


# --- Story 11.3: cross-Moment evidence linking (claim -> notice) --------


def test_notice_type_evidence_is_a_valid_evidence_type(tmp_path):
    path = tmp_path / "claims.json"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(
                type="notice", url="auth-api-v1", label="notice: auth-api-v1"
            )
        ],
    )
    assert claim.evidence[0].type == "notice"
    assert claim.evidence[0].url == "auth-api-v1"


def test_publish_never_http_validates_notice_type_evidence(tmp_path):
    """A `notice`-type evidence entry's `url` is a component name, not an
    HTTP URL -- `publish` must never hand it to `validate`, or a real
    validator would try to HEAD a bare component name and always fail."""
    path = tmp_path / "claims.json"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(
                type="notice", url="auth-api-v1", label="notice: auth-api-v1"
            )
        ],
    )

    def _validate_that_always_raises(url):
        raise errors.EvidenceLinkError(f"Evidence link broken: {url}.")

    published = claims.publish(
        path, claim.id, thesis="Shipped it", validate=_validate_that_always_raises
    )
    assert published.status == "published"
    assert published.evidence[0].validated is True


def test_revalidate_never_http_validates_notice_type_evidence(tmp_path):
    path = tmp_path / "claims.json"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(
                type="notice", url="auth-api-v1", label="notice: auth-api-v1"
            ),
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
    path = tmp_path / "claims.json"
    citing = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(
                type="notice", url="auth-api-v1", label="notice: auth-api-v1"
            )
        ],
    )
    claims.create(path, project_name="marshal")  # no evidence -- not a match
    claims.create(
        path,
        project_name="mason",
        evidence=[
            claims.Evidence(
                type="notice", url="other-component", label="notice: other-component"
            )
        ],
    )
    result = claims.referenced_by_claims(path, "auth-api-v1")
    assert [c.id for c in result] == [citing.id]


def test_referenced_by_claims_empty_when_no_claim_cites_it(tmp_path):
    path = tmp_path / "claims.json"
    claims.create(path, project_name="warden")
    assert claims.referenced_by_claims(path, "auth-api-v1") == []


def test_referenced_by_claims_on_missing_file_is_empty(tmp_path):
    assert claims.referenced_by_claims(tmp_path / "claims.json", "auth-api-v1") == []


# --- Story 13.1: concurrency (closing DW-1-4-2) -----------------------------


def _lock_is_currently_free(lock_path) -> bool:
    """Independently attempts its OWN non-blocking acquire of ``lock_path``
    -- ``True`` only if nothing else currently holds that same lock file's
    exclusive lock. ``fcntl.flock``/``msvcrt.locking`` are per-open-file-
    -description, not per-process, so a second, independent ``open()`` in
    the SAME process still genuinely contends with a lock the process is
    already holding via a different file object -- this is a direct proof,
    not a simulation.

    Deliberately hand-reimplements ``locking``'s ``fcntl``/``msvcrt``
    platform dispatch instead of calling ``locking._acquire`` directly:
    that call BLOCKS until the lock is free, which would defeat this
    helper's whole purpose (a non-blocking "is it free right now" check)
    -- it needs its own non-blocking variant (``LOCK_NB`` / ``LK_NBLCK``)
    of the same two syscalls, so the duplication here is deliberate, not
    drift."""
    try:
        with open(lock_path, "a+b") as fh:
            if sys.platform == "win32":
                import msvcrt

                fh.seek(0)
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    return False
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                return True
            else:
                import fcntl

                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    return False
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                return True
    except OSError:
        return False


def test_two_concurrent_creates_for_different_projects_both_land(tmp_path, monkeypatch):
    """Story 13.1 regression: two ``create`` calls racing the same
    ``claims.json`` must both survive -- forced, deterministic interleaving
    (not a timing-dependent sleep race). Mirrors ``test_state.py``'s
    technique: a monkeypatched delay right after ``read_all``'s read gives
    the other (unlocked) creator's whole read-modify-write cycle room to
    run during the pause; locked, a second creator cannot even begin its
    own read until the first has released the lock. Fails against the
    pre-fix (unlocked) code, passes against the fixed code -- confirmed
    locally by commenting out ``create``'s ``locking.locked`` call."""
    path = tmp_path / "claims.json"
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
    t1.join(timeout=5)
    t2.join(timeout=5)

    project_names = {c.project_name for c in original_read_all(path)}
    assert project_names == {"alpha", "beta"}


def test_publish_never_holds_the_lock_during_network_validation(tmp_path):
    """Story 13.1: ``publish``'s lock must never span the network
    validation call. Direct proof: the injected validator attempts its OWN
    independent non-blocking acquire of the SAME lock file ``publish``
    uses -- if ``publish`` were (incorrectly) holding the lock during
    validation, this nested non-blocking attempt would fail."""
    path = tmp_path / "claims.json"
    claim = claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(type="test_results", url="https://ok", label="tests")
        ],
    )
    lock_path = path.with_name(path.name + ".lock")
    observed: list[bool] = []

    class _Result:
        is_valid = True

    def _validate(url):
        observed.append(_lock_is_currently_free(lock_path))
        return _Result()

    published = claims.publish(path, claim.id, thesis="Shipped it", validate=_validate)

    assert observed == [True]
    assert published.status == "published"


def test_revalidate_all_never_holds_the_lock_during_network_validation(tmp_path):
    """Same proof as ``publish``'s own test, for ``revalidate_all`` --
    every evidence link across every claim is validated (real HTTP, in
    principle) before the lock is ever acquired."""
    path = tmp_path / "claims.json"
    claims.create(
        path,
        project_name="warden",
        evidence=[
            claims.Evidence(type="test_results", url="https://ok", label="tests")
        ],
    )
    lock_path = path.with_name(path.name + ".lock")
    observed: list[bool] = []

    class _Result:
        is_valid = True

    def _validate(url):
        observed.append(_lock_is_currently_free(lock_path))
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
    path = tmp_path / "claims.json"
    shared_evidence = claims.Evidence(
        type="test_results", url="https://ci.example/run-1", label="CI run"
    )
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


def test_concurrent_publish_on_the_same_claim_rejects_the_second_caller(
    tmp_path, monkeypatch
):
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
    path = tmp_path / "claims.json"
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
            result = claims.publish(
                path, claim.id, thesis=thesis, validate=_fake_validator(set())
            )
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
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert len(results) == 1, "exactly one concurrent publish() must succeed"
    assert len(state_errors) == 1, (
        "the other concurrent publish() must raise ClaimStateError, not "
        "silently overwrite the first's published state"
    )
    assert results[0].status == "published"
    # The claim on disk matches the ONE successful call's thesis -- never
    # silently clobbered by the rejected caller's stale write.
    stored = original_read_all(path)[0]
    assert stored.thesis == results[0].thesis


def test_revalidate_all_does_not_stamp_updated_at_on_a_claim_it_never_validated(
    tmp_path, monkeypatch
):
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
    path = tmp_path / "claims.json"
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
    updated = claims.revalidate_all(
        path, validate=lambda url: _Result(), now=lambda: fixed_now
    )

    by_id = {c.id: c for c in updated}
    assert by_id["concurrent-claim"].updated_at == original_updated_at
    assert by_id["concurrent-claim"].evidence == ()
    # The claim the batch DID validate still gets the shared timestamp.
    warden = next(c for c in updated if c.project_name == "warden")
    assert warden.updated_at == fixed_now.isoformat()
