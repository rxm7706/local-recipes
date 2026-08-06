"""``GhForge`` -- ``ports.ForgePort``'s sole implementation (Story 4.4,
NFR-2, AD-4/AD-34): every forge interaction this package makes lives here,
shelled out to the ``gh`` CLI via the stdlib ``subprocess`` module -- never
a raw HTTP/REST client (this repo's own entire session-long practice, every
PR from #266 onward, already goes through ``gh pr create``/``gh pr edit``).

Mirrors ``adapters/vcs_git.py``'s own ``_run()`` helper almost exactly (same
``capture_output``/``text``/``encoding="utf-8"``/``errors="replace"``
decoding discipline, same "never let a raw subprocess exception escape"
translation into this module's own command-error type) -- with one
network-call difference: ``gh``'s own auth (``gh auth status``) is assumed
already configured (a documented precondition elsewhere in this codebase),
and every invocation uses a network-sized timeout, not a local-query one.

``create_pr`` cannot recover the new PR's number directly from ``gh pr
create``'s own stdout (it prints only the PR's URL) -- so it re-queries via
``find_open_pr`` immediately after a successful create, the SAME read
``find_open_pr`` itself already implements, rather than a second URL-parsing
mechanism. ``update_pr`` mirrors this: ``gh pr edit`` prints nothing
machine-readable either, so a ``gh pr view --json`` re-query follows the
edit.

Every ``ForgeRef``-typed parameter (see ``ports/forge.py``'s own docstring
for why the Protocol wraps ``repo``/``head_branch``/``base``/``head``/
``ref``/``check_name`` this way) is unwrapped to its own ``.value`` exactly
once, at the point a ``gh`` argv is assembled -- never earlier, so a caller
constructing a ``ForgeRef`` and passing it straight through is the only
path a routing identifier travels.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping

from ..core.egress import Redacted
from ..ports.forge import ForgeCommandError, ForgeRef, PrInfo

# A read (list/view) is a bounded, single-round-trip GitHub API call --
# sized like adapters/vcs_git.py's own query tier. A write (create/edit) can
# involve more server-side work (webhooks, label validation) and gets the
# same headroom adapters/vcs_git.py::_GIT_PUSH_TIMEOUT_S gives a push -- both
# are network round-trips, not local-process budgets.
_GH_READ_TIMEOUT_S = 30.0
_GH_WRITE_TIMEOUT_S = 120.0


def _run(
    args: list[str], *, timeout_s: float
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
    except FileNotFoundError as exc:
        raise ForgeCommandError(f"gh executable not found: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ForgeCommandError(
            f"gh command timed out after {timeout_s}s: {' '.join(args)}"
        ) from exc
    except OSError as exc:
        raise ForgeCommandError(f"cannot launch gh: {exc}") from exc


def _parse_json(text: str, *, context: str) -> object:
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ForgeCommandError(f"{context}: gh returned invalid JSON: {exc}") from exc


def _pr_info_from_json(entry: object, *, context: str) -> PrInfo:
    if not isinstance(entry, Mapping):
        raise ForgeCommandError(f"{context}: gh returned a non-object PR entry: {entry!r}")
    number = entry.get("number")
    url = entry.get("url")
    state = entry.get("state")
    base = entry.get("baseRefName")
    if not isinstance(number, int) or isinstance(number, bool):
        raise ForgeCommandError(
            f"{context}: gh returned a PR entry with a non-int number: {entry!r}"
        )
    if not isinstance(url, str) or not url:
        raise ForgeCommandError(
            f"{context}: gh returned a PR entry missing a url: {entry!r}"
        )
    if not isinstance(state, str) or not state:
        raise ForgeCommandError(
            f"{context}: gh returned a PR entry missing a state: {entry!r}"
        )
    if not isinstance(base, str) or not base:
        raise ForgeCommandError(
            f"{context}: gh returned a PR entry missing a baseRefName: {entry!r}"
        )
    return PrInfo(number=number, url=url, state=state.lower(), base=base)


def _require_redacted(title: object, body: object) -> None:
    """Both ``title``/``body`` must be ``Redacted`` -- never a bare
    ``str`` -- the last line of defense at this port's own boundary (AD-34),
    mirroring ``FileDesktopNotifier``'s identical type-guard convention."""
    if not isinstance(title, Redacted):
        raise TypeError(f"title must be a Redacted instance, got {type(title).__name__}")
    if not isinstance(body, Redacted):
        raise TypeError(f"body must be a Redacted instance, got {type(body).__name__}")


class GhForge:
    """``ports.ForgePort``'s sole implementation."""

    def find_open_pr(self, repo: ForgeRef, head_branch: ForgeRef) -> PrInfo | None:
        repo_value, head_branch_value = repo.value, head_branch.value
        result = _run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repo_value,
                "--head",
                head_branch_value,
                "--state",
                "open",
                "--json",
                "number,url,state,baseRefName",
                "--limit",
                "1",
            ],
            timeout_s=_GH_READ_TIMEOUT_S,
        )
        if result.returncode != 0:
            raise ForgeCommandError(
                f"gh pr list --repo {repo_value} --head {head_branch_value} failed: "
                f"{result.stderr.strip()}"
            )
        context = f"gh pr list --repo {repo_value} --head {head_branch_value}"
        data = _parse_json(result.stdout, context=context)
        if not isinstance(data, list):
            raise ForgeCommandError(f"{context}: gh returned a non-list payload: {data!r}")
        if not data:
            return None
        return _pr_info_from_json(data[0], context=context)

    def create_pr(
        self, repo: ForgeRef, base: ForgeRef, head: ForgeRef, title: Redacted, body: Redacted
    ) -> PrInfo:
        _require_redacted(title, body)
        repo_value, base_value, head_value = repo.value, base.value, head.value
        result = _run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo_value,
                "--base",
                base_value,
                "--head",
                head_value,
                "--title",
                title.text,
                "--body",
                body.text,
            ],
            timeout_s=_GH_WRITE_TIMEOUT_S,
        )
        if result.returncode != 0:
            raise ForgeCommandError(
                f"gh pr create --repo {repo_value} --base {base_value} --head "
                f"{head_value} failed: {result.stderr.strip()}"
            )
        created = self.find_open_pr(repo, head)
        if created is None:
            raise ForgeCommandError(
                f"gh pr create --repo {repo_value} --base {base_value} --head "
                f"{head_value} reported success but no open PR for {head_value!r} "
                "could be found afterward"
            )
        return created

    def update_pr(
        self, repo: ForgeRef, number: int, title: Redacted, body: Redacted
    ) -> PrInfo:
        _require_redacted(title, body)
        repo_value = repo.value
        result = _run(
            [
                "gh",
                "pr",
                "edit",
                str(number),
                "--repo",
                repo_value,
                "--title",
                title.text,
                "--body",
                body.text,
            ],
            timeout_s=_GH_WRITE_TIMEOUT_S,
        )
        if result.returncode != 0:
            raise ForgeCommandError(
                f"gh pr edit {number} --repo {repo_value} failed: {result.stderr.strip()}"
            )
        view = _run(
            [
                "gh",
                "pr",
                "view",
                str(number),
                "--repo",
                repo_value,
                "--json",
                "number,url,state,baseRefName",
            ],
            timeout_s=_GH_READ_TIMEOUT_S,
        )
        if view.returncode != 0:
            raise ForgeCommandError(
                f"gh pr view {number} --repo {repo_value} failed after editing: "
                f"{view.stderr.strip()}"
            )
        context = f"gh pr view {number} --repo {repo_value}"
        data = _parse_json(view.stdout, context=context)
        return _pr_info_from_json(data, context=context)

    def add_labels(self, repo: ForgeRef, number: int, labels: tuple[str, ...]) -> None:
        if not labels:
            # Nothing to apply -- no fired label rule this run. Never call
            # `gh` for a no-op (mirrors VcsPort.commit_paths's own "refuse
            # before any invocation" discipline for an equivalently empty
            # write).
            return
        repo_value = repo.value
        args = ["gh", "pr", "edit", str(number), "--repo", repo_value]
        for label in labels:
            args.extend(["--add-label", label])
        result = _run(args, timeout_s=_GH_WRITE_TIMEOUT_S)
        if result.returncode != 0:
            raise ForgeCommandError(
                f"gh pr edit {number} --repo {repo_value} --add-label {list(labels)} "
                f"failed: {result.stderr.strip()}"
            )

    def check_run_status(
        self, repo: ForgeRef, ref: ForgeRef, check_name: ForgeRef
    ) -> str | None:
        repo_value, ref_value, check_name_value = repo.value, ref.value, check_name.value
        result = _run(
            ["gh", "api", f"repos/{repo_value}/commits/{ref_value}/check-runs"],
            timeout_s=_GH_READ_TIMEOUT_S,
        )
        if result.returncode != 0:
            raise ForgeCommandError(
                f"gh api repos/{repo_value}/commits/{ref_value}/check-runs failed: "
                f"{result.stderr.strip()}"
            )
        context = f"gh api repos/{repo_value}/commits/{ref_value}/check-runs"
        data = _parse_json(result.stdout, context=context)
        if not isinstance(data, Mapping):
            raise ForgeCommandError(f"{context}: gh returned a non-object payload: {data!r}")
        runs = data.get("check_runs")
        if not isinstance(runs, list):
            return None
        matching = [run for run in runs if isinstance(run, Mapping) and run.get("name") == check_name_value]
        if not matching:
            return None
        # Code review (2026-08-06, P3, both reviewers independently): GitHub
        # can report multiple runs under the same check name (reruns), and
        # this endpoint's own response order is NOT documented/guaranteed
        # newest-first -- trusting response order let a stale "success" from
        # an old run mask a real, newer "failure", exactly the "hygiene check
        # misevaluated" risk this review was commissioned to hunt for.
        # ``started_at`` is a fixed-format ISO-8601 UTC timestamp
        # (e.g. "2026-08-06T12:00:00Z"), so plain string comparison sorts it
        # chronologically; a run missing/malformed ``started_at`` sorts as
        # the oldest possible ("") rather than crashing or masking a real
        # newer run.
        def _started_at(run: Mapping[str, object]) -> str:
            started = run.get("started_at")
            return started if isinstance(started, str) else ""

        matching.sort(key=_started_at, reverse=True)
        conclusion = matching[0].get("conclusion")
        return conclusion if isinstance(conclusion, str) else None
