"""``adapters/harness_bmadloop.py`` recall injection (Stories 47.1/47.2,
SPEC-marshal-recall-in-the-loop CAP-1/CAP-2) -- driven entirely through
FAKE ``FsPort``/``ScribeCli`` doubles (never a live ``scribe`` subprocess).

Story 47.1 covers all four rows of the dev-pass I/O & Edge-Case Matrix:

1. grounded hit -> labeled block written, ``injected=True``, no error.
2. grounded miss -> empty string written, ``injected=False``, ``ok=True``.
3. scribe CLI unavailable/non-zero/timeout -> ``ok=False`` with a reason,
   dispatch proceeds unaffected (this module only reports the degradation;
   ``cli/spin.py`` decides what to do with it).
4. no resolvable station slug -> the recall query is skipped entirely --
   zero fs calls, zero scribe calls, ``attempted=False``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.adapters.harness_bmadloop import (
    RecallInjectionResult,
    augment_bmad_loop_session_prompt_with_recall,
    inject_recall_feedback,
)
from pyforge.marshal.adapters.scribe_cli import ScribeRecallOutcome
from pyforge.marshal.core import recall_feedback as recall_feedback_core
from pyforge.marshal.core.recall_feedback import RECALL_FEEDBACK_HEADER


class _FakeFs:
    """Records every ``ensure_dir``/``write_text_atomic`` call; a real
    ``PyforgeError``-raising fake would need Story 47.1's own ``FsError`` to
    be importable here, but this story's write-failure row is exercised via
    ``fail_write`` raising a plain ``OSError`` -- the same exception class
    ``inject_recall_feedback``'s own ``except (OSError, PyforgeError)``
    already declares it catches."""

    def __init__(self, *, fail_write: bool = False) -> None:
        self.fail_write = fail_write
        self.ensure_dir_calls: list[Path] = []
        self.writes: dict[Path, str] = {}

    def ensure_dir(self, path: Path) -> None:
        self.ensure_dir_calls.append(path)

    def write_text_atomic(self, path: Path, content: str) -> None:
        if self.fail_write:
            raise OSError("disk full")
        self.writes[path] = content

    def read_text(self, path: Path) -> str | None:
        return self.writes.get(path)


class _FakeScribeCli:
    """A ``ScribeCli`` double: records the exact keyword arguments
    ``recall`` was called with and returns a canned ``ScribeRecallOutcome``."""

    def __init__(self, outcome: ScribeRecallOutcome) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, object]] = []

    def recall(self, *, repo_root: Path, query: str, scope: str | None = None, binary_path: Path | None = None):
        self.calls.append({"repo_root": repo_root, "query": query, "scope": scope, "binary_path": binary_path})
        return self.outcome


@pytest.fixture
def loop_home(tmp_path: Path) -> Path:
    return tmp_path / "loop-homes" / "pyforge-doctor"


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path / "repo"


class TestGroundedHit:
    def test_writes_a_labeled_block_and_reports_injected(self, loop_home: Path, repo_root: Path) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(
            ScribeRecallOutcome(ok=True, grounded=True, text="always run X before Y", citation="feedback/x.md")
        )

        result = inject_recall_feedback(
            fs=fs,
            loop_home=loop_home,
            repo_root=repo_root,
            station_slug="pyforge-doctor",
            scribe=scribe,
        )

        assert result == RecallInjectionResult(attempted=True, ok=True, injected=True, target=result.target)
        assert result.target is not None
        assert str(result.target).startswith(str(loop_home))
        written = fs.writes[result.target]
        assert written.startswith(RECALL_FEEDBACK_HEADER)
        assert "always run X before Y" in written
        assert "Source: feedback/x.md" in written

    def test_scopes_the_recall_call_by_station_slug_and_runs_it_against_repo_root(
        self, loop_home: Path, repo_root: Path
    ) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(ScribeRecallOutcome(ok=True, grounded=True, text="body"))

        inject_recall_feedback(
            fs=fs, loop_home=loop_home, repo_root=repo_root, station_slug="pyforge-doctor", scribe=scribe
        )

        assert len(scribe.calls) == 1
        call = scribe.calls[0]
        assert call["scope"] == "pyforge-doctor"
        assert call["repo_root"] == repo_root
        assert "pyforge-doctor" in call["query"]


class TestGroundedMiss:
    def test_writes_an_empty_string_and_reports_not_injected_with_no_error(
        self, loop_home: Path, repo_root: Path
    ) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(ScribeRecallOutcome(ok=True, grounded=False))

        result = inject_recall_feedback(
            fs=fs, loop_home=loop_home, repo_root=repo_root, station_slug="pyforge-doctor", scribe=scribe
        )

        assert result.attempted is True
        assert result.ok is True
        assert result.injected is False
        assert result.reason is None
        assert fs.writes[result.target] == ""


class TestScribeUnavailable:
    def test_degrades_to_ok_false_with_a_reason_and_still_writes_the_target(
        self, loop_home: Path, repo_root: Path
    ) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(ScribeRecallOutcome(ok=False, reason="scribe binary not found on PATH"))

        result = inject_recall_feedback(
            fs=fs, loop_home=loop_home, repo_root=repo_root, station_slug="pyforge-doctor", scribe=scribe
        )

        assert result.attempted is True
        assert result.ok is False
        assert result.reason == "scribe binary not found on PATH"
        assert result.injected is False
        # A degraded recall is never dispatch-blocking, and never leaves a
        # stale previous hit sitting in the target either (FsPort has no
        # delete-a-file primitive, so "clear it" means "overwrite it").
        assert fs.writes[result.target] == ""

    def test_a_write_failure_reports_ok_false_with_the_write_reason(self, loop_home: Path, repo_root: Path) -> None:
        fs = _FakeFs(fail_write=True)
        scribe = _FakeScribeCli(ScribeRecallOutcome(ok=True, grounded=True, text="body"))

        result = inject_recall_feedback(
            fs=fs, loop_home=loop_home, repo_root=repo_root, station_slug="pyforge-doctor", scribe=scribe
        )

        assert result.attempted is True
        assert result.ok is False
        assert result.reason is not None
        assert "disk full" in result.reason


class TestNoResolvableStationSlug:
    def test_skips_the_query_entirely(self, loop_home: Path, repo_root: Path) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(ScribeRecallOutcome(ok=True, grounded=True, text="body"))

        result = inject_recall_feedback(
            fs=fs, loop_home=loop_home, repo_root=repo_root, station_slug=None, scribe=scribe
        )

        assert result == RecallInjectionResult(attempted=False)
        assert fs.ensure_dir_calls == []
        assert fs.writes == {}
        assert scribe.calls == []


class TestReviewPassReusesCachedRecall:
    """Story 47.2 (CAP-2): one ``scribe recall`` per story dispatch; review reads cache."""

    def test_dev_then_review_shares_one_scribe_call_and_identical_block(self, loop_home: Path, repo_root: Path) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(
            ScribeRecallOutcome(ok=True, grounded=True, text="never skip memlog reconcile", citation="memlog/x.md")
        )
        base_prompt = "Implement story 47.2."

        dev_prompt, dev_injection = augment_bmad_loop_session_prompt_with_recall(
            base_prompt,
            role="dev",
            fs=fs,
            loop_home=loop_home,
            repo_root=repo_root,
            station_slug="pyforge-marshal",
            scribe=scribe,
        )
        review_prompt, review_injection = augment_bmad_loop_session_prompt_with_recall(
            base_prompt,
            role="review",
            fs=fs,
            loop_home=loop_home,
            repo_root=repo_root,
            station_slug="pyforge-marshal",
            scribe=scribe,
        )

        assert len(scribe.calls) == 1
        assert dev_injection is not None and dev_injection.injected is True
        assert review_injection is None
        assert "never skip memlog reconcile" in dev_prompt
        assert dev_prompt == review_prompt
        assert RECALL_FEEDBACK_HEADER in dev_prompt

    def test_review_with_no_prior_query_does_not_call_scribe(self, loop_home: Path, repo_root: Path) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(ScribeRecallOutcome(ok=True, grounded=True, text="body"))

        prompt, injection = augment_bmad_loop_session_prompt_with_recall(
            "Review the diff.",
            role="review",
            fs=fs,
            loop_home=loop_home,
            repo_root=repo_root,
            station_slug="pyforge-marshal",
            scribe=scribe,
        )

        assert scribe.calls == []
        assert injection is None
        assert prompt == "Review the diff."

    def test_dev_pass_received_no_block_review_also_gets_no_block(self, loop_home: Path, repo_root: Path) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(ScribeRecallOutcome(ok=True, grounded=False))

        dev_prompt, _ = augment_bmad_loop_session_prompt_with_recall(
            "Dev.",
            role="dev",
            fs=fs,
            loop_home=loop_home,
            repo_root=repo_root,
            station_slug="pyforge-marshal",
            scribe=scribe,
        )
        review_prompt, _ = augment_bmad_loop_session_prompt_with_recall(
            "Review.",
            role="review",
            fs=fs,
            loop_home=loop_home,
            repo_root=repo_root,
            station_slug="pyforge-marshal",
            scribe=scribe,
        )

        assert len(scribe.calls) == 1
        assert dev_prompt == "Dev."
        assert review_prompt == "Review."
        target = loop_home / recall_feedback_core.recall_feedback_output_relpath("pyforge-marshal")
        assert fs.writes[target] == ""


class TestRecallContextLayerGate:
    """Story 47.3 (CAP-3): ``[context.recall] enabled = false`` skips the query."""

    def test_disabled_recall_layer_skips_scribe_and_leaves_prompt_unchanged(
        self, loop_home: Path, repo_root: Path
    ) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(
            ScribeRecallOutcome(ok=True, grounded=True, text="should not appear", citation=None)
        )
        layers = {
            recall_feedback_core.RECALL_LAYER: {"enabled": False, "aggressiveness": "medium"},
        }

        prompt, injection = augment_bmad_loop_session_prompt_with_recall(
            "Dev prompt.",
            role="dev",
            fs=fs,
            loop_home=loop_home,
            repo_root=repo_root,
            station_slug="pyforge-marshal",
            scribe=scribe,
            context_layers=layers,
        )

        assert scribe.calls == []
        assert injection is None
        assert prompt == "Dev prompt."
        assert fs.writes == {}

    def test_enabled_recall_layer_still_injects(self, loop_home: Path, repo_root: Path) -> None:
        fs = _FakeFs()
        scribe = _FakeScribeCli(
            ScribeRecallOutcome(ok=True, grounded=True, text="correction text", citation=None)
        )
        layers = {
            recall_feedback_core.RECALL_LAYER: {"enabled": True, "aggressiveness": "medium"},
        }

        prompt, injection = augment_bmad_loop_session_prompt_with_recall(
            "Dev.",
            role="dev",
            fs=fs,
            loop_home=loop_home,
            repo_root=repo_root,
            station_slug="pyforge-marshal",
            scribe=scribe,
            context_layers=layers,
        )

        assert len(scribe.calls) == 1
        assert injection is not None and injection.injected is True
        assert "correction text" in prompt
