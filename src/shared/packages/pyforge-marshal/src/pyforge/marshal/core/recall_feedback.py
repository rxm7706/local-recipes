"""The ``recall`` capability's pure half (Story 47.1,
SPEC-marshal-recall-in-the-loop CAP-1).

A `bmad-loop` dev pass starts from a blank context unless an operator
remembers to run `scribe recall` first and paste the result in by hand.
This module is the query/format half of closing that gap: it names the
natural-language query scribe recall is asked, and renders a grounded hit
into the clearly-labeled block that gets folded into a dev-pass session's
starting context. It never runs scribe itself and never touches a
filesystem (AD-4) -- ``adapters/scribe_cli.py`` owns the subprocess,
``adapters/harness_bmadloop.py`` owns the pre-launch call site and the
write.

CAP-4's honesty guarantee (a grounded miss is explicit, never a fabricated
"no relevant corrections found" line) is enforced by construction here:
``render_recall_feedback_block`` has no miss branch at all -- the caller
decides, from ``ScribeRecallOutcome.grounded``, whether to call it, and
writes an empty string instead when it does not.
"""

from __future__ import annotations

from .derived_context import implementation_artifacts_relpath

__all__ = (
    "RECALL_FEEDBACK_HEADER",
    "build_recall_query",
    "recall_feedback_output_relpath",
    "render_recall_feedback_block",
)

#: The label distinguishing this block from the story's own spec/intent
#: content (this story's own "clearly labeled" constraint).
RECALL_FEEDBACK_HEADER = "# Scribe feedback (auto-recalled before this dev pass)"


def build_recall_query(station_slug: str) -> str:
    """Natural-language query naming the station so scribe's own
    lexical/semantic scoring binds to feedback relevant to it -- mirrors
    ``planning_graph.build_routing_query``'s naming discipline."""
    return f"feedback corrections guidance for {station_slug}"


def recall_feedback_output_relpath(project_slug: str) -> str:
    """Where a grounded hit is written, repo-relative -- a sibling of
    ``epic-<N>-context.md`` in the same Tier-3 ``implementation-artifacts``
    directory step-01 already reads derived artifacts from."""
    return f"{implementation_artifacts_relpath(project_slug)}/recall-feedback.md"


def render_recall_feedback_block(*, text: str, citation: str | None) -> str:
    """The clearly-labeled, scribe-sourced block for a genuine grounded
    hit. Callers must only invoke this when the outcome is grounded --
    this function has no "miss" branch by construction, so it can never
    render a synthesized "no relevant corrections found" line (CAP-4)."""
    lines = [RECALL_FEEDBACK_HEADER, "", text.strip()]
    if citation:
        lines += ["", f"Source: {citation}"]
    return "\n".join(lines) + "\n"
