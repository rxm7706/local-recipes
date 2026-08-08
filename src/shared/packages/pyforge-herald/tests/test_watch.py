"""``herald deck watch`` -- Epic 4 Story 4.1: poll loop + quiescence
debounce (4.2's idle backoff and 4.3's halt-on-auth-error tests land in
this same file, in their own stories).

Every transport call is against a hand-written ``FakeWatchTransport`` (no
network, no adapter) exercising only ``read_file`` -- ``watch`` never calls
any other ``DesignTransport`` method itself. The actual land-the-pull step
is a hand-written spy passed as ``pull=`` (never the real
``deck_pipeline.pull_prototype``, which would need a real ``npm``/``pixi``
subprocess) -- ``test_deck_pipeline.py`` is the pull step's own test.
``sleep`` is a no-op spy throughout: every test simulates N poll cycles with
no real wall-clock wait, and asserting on the recorded sleep durations is
how the interval/backoff/floor assertions are made without a fake clock."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pyforge.herald import state
from pyforge.herald.deck_pipeline import PullResult
from pyforge.herald.errors import HeraldError
from pyforge.herald.transport.base import FileRead
from pyforge.herald.watch import (
    DEFAULT_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
    WatchEvent,
    watch,
)

_FIXED_NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)


class FakeWatchTransport:
    """A hand-written ``DesignTransport`` double exercising only
    ``read_file`` -- every other method raises, since ``watch`` itself never
    calls them (the injected ``pull`` spy stands in for the real pull)."""

    def __init__(self, *, answers, fail_after: int | None = None, fail_with=None):
        # answers: project_id -> list of FileRead (consumed one per call) or
        # a single FileRead reused for every call to that project.
        self.calls: list[dict] = []
        self._answers = answers
        self._fail_after = fail_after
        self._fail_with = fail_with
        self._call_count = 0

    def read_file(self, *, project_id, path, if_none_match=None, offset=None, limit=None):
        self._call_count += 1
        self.calls.append(
            {"project_id": project_id, "path": path, "if_none_match": if_none_match}
        )
        if self._fail_after is not None and self._call_count > self._fail_after:
            raise self._fail_with
        answer = self._answers[project_id]
        if isinstance(answer, list):
            assert answer, f"ran out of canned read_file answers for {project_id!r}"
            return answer.pop(0)
        return answer

    def get_design_prompt(self, **kwargs):
        raise NotImplementedError("watch never calls get_design_prompt")

    def create_project(self, **kwargs):
        raise NotImplementedError("watch never calls create_project")

    def finalize_plan(self, **kwargs):
        raise NotImplementedError("watch never calls finalize_plan")

    def create_support_js(self, **kwargs):
        raise NotImplementedError("watch never calls create_support_js")

    def copy_files(self, **kwargs):
        raise NotImplementedError("watch never calls copy_files")

    def write_files(self, **kwargs):
        raise NotImplementedError("watch never calls write_files")

    def render_preview(self, **kwargs):
        raise NotImplementedError("watch never calls render_preview")


class FakePull:
    """Records every call, in order, and returns a canned ``PullResult``
    (a fresh etag by default) -- stands in for
    ``deck_pipeline.pull_prototype`` so no real subprocess ever runs."""

    def __init__(self, *, etag="E-NEW"):
        self.calls: list[dict] = []
        self._etag = etag

    def __call__(self, transport, *, slug, repo_root, state_path, now):
        self.calls.append(
            {
                "transport": transport,
                "slug": slug,
                "repo_root": repo_root,
                "state_path": state_path,
            }
        )
        return PullResult(
            slug=slug,
            artifact="prototype",
            local_path=repo_root / "presentations" / slug / "project" / "x.dc.html",
            unchanged=False,
            etag=self._etag,
        )


def _seed_state(state_path: Path, slug: str, *, project_id: str, etag: str) -> None:
    state.write(
        state_path,
        slug,
        state.DeckState(project_id=project_id, etags={"prototype": etag}, last_pull=None),
    )


def _no_sleep_calls():
    calls: list[float] = []

    def sleep(seconds: float) -> None:
        calls.append(seconds)

    return sleep, calls


def test_each_poll_is_etag_only_and_unchanged_polls_never_pull(tmp_path: Path):
    """Story 4.1: the common steady-state path -- etag never changes -- is
    an ``if_none_match`` short-circuit every time (``unchanged=True``, no
    body), and never triggers a pull."""
    state_path = tmp_path / "bridge-state.json"
    _seed_state(state_path, "pyforge-warden", project_id="p-1", etag="E0")
    transport = FakeWatchTransport(
        answers={"p-1": FileRead(path="x", etag="E0", body=None, unchanged=True)}
    )
    pull = FakePull()
    sleep, sleep_calls = _no_sleep_calls()

    watch(
        transport,
        slugs=["pyforge-warden"],
        repo_root=tmp_path,
        state_path=state_path,
        max_polls_per_deck=5,
        pull=pull,
        now=lambda: _FIXED_NOW,
        sleep=sleep,
    )

    assert len(transport.calls) == 5
    assert all(call["if_none_match"] == "E0" for call in transport.calls)
    assert pull.calls == []


def test_consecutive_unchanged_polls_perform_zero_writes(tmp_path: Path):
    """Story 4.1's third AC, over N simulated unchanged polls: no write
    lands on either surface -- proven here by nothing else touching
    ``state.py`` (the only writer a poll could reach is the injected
    ``pull``, and it is never called)."""
    state_path = tmp_path / "bridge-state.json"
    _seed_state(state_path, "pyforge-warden", project_id="p-1", etag="E0")
    before = state.read(state_path, "pyforge-warden")
    transport = FakeWatchTransport(
        answers={"p-1": FileRead(path="x", etag="E0", body=None, unchanged=True)}
    )
    pull = FakePull()
    sleep, _ = _no_sleep_calls()

    watch(
        transport,
        slugs=["pyforge-warden"],
        repo_root=tmp_path,
        state_path=state_path,
        max_polls_per_deck=20,
        pull=pull,
        now=lambda: _FIXED_NOW,
        sleep=sleep,
    )

    after = state.read(state_path, "pyforge-warden")
    assert after == before
    assert pull.calls == []


def test_a_changed_etag_is_not_pulled_until_it_holds_one_full_interval(tmp_path: Path):
    """Story 4.1's debounce AC: the first poll that sees a new etag does
    NOT pull -- only the following poll, once that same candidate etag is
    seen again (i.e. it held across one full interval), triggers the real
    pull."""
    state_path = tmp_path / "bridge-state.json"
    _seed_state(state_path, "pyforge-warden", project_id="p-1", etag="E0")
    transport = FakeWatchTransport(
        answers={
            "p-1": [
                FileRead(path="x", etag="E1", body="edited", unchanged=False),
                FileRead(path="x", etag="E1", body=None, unchanged=True),
            ]
        }
    )
    pull = FakePull(etag="E1")
    events: list[WatchEvent] = []
    sleep, _ = _no_sleep_calls()

    watch(
        transport,
        slugs=["pyforge-warden"],
        repo_root=tmp_path,
        state_path=state_path,
        max_polls_per_deck=2,
        pull=pull,
        now=lambda: _FIXED_NOW,
        sleep=sleep,
        on_event=events.append,
    )

    assert [call["if_none_match"] for call in transport.calls] == ["E0", "E1"]
    assert len(pull.calls) == 1
    assert pull.calls[0]["slug"] == "pyforge-warden"
    assert [event.kind for event in events] == ["settling", "pulled"]


def test_interval_below_the_floor_is_clamped_to_30s(tmp_path: Path):
    """NFR-09: a caller-requested interval under 30s is clamped up, not
    honored as given."""
    state_path = tmp_path / "bridge-state.json"
    _seed_state(state_path, "pyforge-warden", project_id="p-1", etag="E0")
    transport = FakeWatchTransport(
        answers={"p-1": FileRead(path="x", etag="E0", body=None, unchanged=True)}
    )
    events: list[WatchEvent] = []
    sleep, _ = _no_sleep_calls()

    watch(
        transport,
        slugs=["pyforge-warden"],
        repo_root=tmp_path,
        state_path=state_path,
        interval=5.0,
        max_polls_per_deck=1,
        pull=FakePull(),
        now=lambda: _FIXED_NOW,
        sleep=sleep,
        on_event=events.append,
    )

    assert events[0].interval == MIN_POLL_INTERVAL == 30.0


def test_a_default_interval_request_is_left_at_60s(tmp_path: Path):
    state_path = tmp_path / "bridge-state.json"
    _seed_state(state_path, "pyforge-warden", project_id="p-1", etag="E0")
    transport = FakeWatchTransport(
        answers={"p-1": FileRead(path="x", etag="E0", body=None, unchanged=True)}
    )
    events: list[WatchEvent] = []
    sleep, _ = _no_sleep_calls()

    watch(
        transport,
        slugs=["pyforge-warden"],
        repo_root=tmp_path,
        state_path=state_path,
        max_polls_per_deck=1,
        pull=FakePull(),
        now=lambda: _FIXED_NOW,
        sleep=sleep,
        on_event=events.append,
    )

    assert events[0].interval == DEFAULT_POLL_INTERVAL == 60.0


def test_watch_requires_at_least_one_slug(tmp_path: Path):
    with pytest.raises(ValueError):
        watch(
            FakeWatchTransport(answers={}),
            slugs=[],
            repo_root=tmp_path,
            sleep=lambda seconds: None,
        )


def test_watch_requires_every_slug_to_already_be_seeded(tmp_path: Path):
    state_path = tmp_path / "bridge-state.json"
    with pytest.raises(HeraldError):
        watch(
            FakeWatchTransport(answers={}),
            slugs=["pyforge-never-seeded"],
            repo_root=tmp_path,
            state_path=state_path,
            sleep=lambda seconds: None,
        )
