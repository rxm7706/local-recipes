"""Story 85.1 (CAP-286): verification-refusal fix turn."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from pyforge.core.flags import FlagConfigError
from pyforge.core.process import PosixProcess

from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.dispatch_verify_fix import (
    FailedVerifyCommand,
    VerifyFixLaunchMode,
    build_verify_fix_prompt,
    choose_verify_fix_launch_mode,
    decide_verify_fix_turn,
    extract_failed_verify_commands,
    scrub_fix_turn_exposure,
    scrub_then_tail_bytes,
    tail_bytes,
)
from pyforge.marshal.core.harness_profile import parse_profile
from pyforge.marshal.core.harness_profile import render_verify_fix_argv as render_fix
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.policy import DEFAULT_POLICY, compose
from pyforge.marshal.dispatch_verify import (
    ProcessWaitResult,
    TerminateProcessGroupResult,
    terminate_process_group,
    verify_fix_loop_enabled,
    wait_for_process,
)


def test_decide_verify_fix_turn_requires_flag_and_refusal():
    assert (
        decide_verify_fix_turn(
            flag_enabled=False,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is False
    )
    assert (
        decide_verify_fix_turn(
            flag_enabled=True,
            verification_verdict=DispatchVerificationVerdict.VERIFIED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is False
    )
    assert (
        decide_verify_fix_turn(
            flag_enabled=True,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is True
    )


def test_build_verify_fix_prompt_uses_tail_only():
    failed = (
        FailedVerifyCommand(
            command="pixi run -e pyforge-guild lint-types",
            stdout="A" * 100,
            stderr="B" * 100,
            exit_code=1,
        ),
    )
    prompt = build_verify_fix_prompt(failed, output_tail_bytes=20)
    assert "bmad-build-auto" not in prompt
    assert "pixi run -e pyforge-guild lint-types" in prompt
    assert "AAAA" not in prompt or len(prompt) < 300


def test_tail_bytes_bounds_output():
    text = "0123456789" * 50
    tailed = tail_bytes(text, max_bytes=15)
    assert len(tailed.encode("utf-8")) <= 15


def test_extract_failed_verify_commands_from_gate_reports():
    reports = (
        {
            "command": "pixi run test",
            "returncode": 1,
            "stdout": "fail",
            "stderr": "",
        },
    )
    findings = (
        Finding(
            code="MRS-GATE-001",
            severity=Severity.ERROR,
            message="verify command 'pixi run test' exited 1",
        ),
    )
    extracted = extract_failed_verify_commands(reports, findings)
    assert len(extracted) == 1
    assert extracted[0].command == "pixi run test"


def test_resume_vs_fix_only_from_profile():
    profile = parse_profile(
        {
            "name": "fake",
            "binary": "fake",
            "argv": ["{prompt}"],
            "resume_argv": ["--resume", "{session_id}", "{prompt_stdin}"],
        },
        source="t",
    )
    assert (
        choose_verify_fix_launch_mode(
            resume_argv=profile.resume_argv,
            harness_session_id="sid-1",
            launch_profile="fake",
            resolved_profile="fake",
        )
        == VerifyFixLaunchMode.RESUME
    )
    assert choose_verify_fix_launch_mode(resume_argv=profile.resume_argv, harness_session_id=None) == (
        VerifyFixLaunchMode.FIX_ONLY
    )
    assert (
        choose_verify_fix_launch_mode(
            resume_argv=profile.resume_argv,
            harness_session_id="sid-1",
            launch_profile="claude",
            resolved_profile="cursor",
        )
        == VerifyFixLaunchMode.FIX_ONLY
    )
    bare = parse_profile({"name": "bare", "binary": "bare", "argv": ["{prompt}"]}, source="t")
    assert choose_verify_fix_launch_mode(resume_argv=bare.resume_argv) == VerifyFixLaunchMode.FIX_ONLY


def test_render_verify_fix_resume_argv():
    profile = parse_profile(
        {
            "name": "fake",
            "binary": "fake",
            "argv": ["{prompt}"],
            "resume_argv": ["--resume", "{session_id}", "{prompt_file}"],
        },
        source="t",
    )
    argv, _, _ = render_fix(
        profile,
        mode="resume",
        binary_path="/bin/fake",
        worktree=__import__("pathlib").Path("/tmp/wt"),
        model=None,
        session_id="abc-session",
        prompt_file="/tmp/wt/verify-fix-prompt.txt",
    )
    assert argv == ("/bin/fake", "--resume", "abc-session", "/tmp/wt/verify-fix-prompt.txt")


def test_policy_verify_fix_defaults_compose():
    effective, _ = compose(project_slug="pyforge-marshal", project={}, flags={})
    block = effective.dispatch.value
    assert block["verify_fix_output_tail_bytes"] == DEFAULT_POLICY["dispatch"]["verify_fix_output_tail_bytes"]
    assert block["verify_fix_wall_clock_minutes"] == DEFAULT_POLICY["dispatch"]["verify_fix_wall_clock_minutes"]


#: Every credential shape Story 85.3's AC names, plus the five the 85.3 landing review found leaking (H3):
#: ``(case id, raw text, the secret that must not survive)``.
_CREDENTIAL_SHAPES = [
    ("url", "postgres://admin:urlsecret1@db/x", "urlsecret1"),
    ("url-slash", "https://user:pa/ss@host.example/path", "pa/ss"),
    ("url-slash-colon", "postgresql://admin:p/a:ss@db.example:5432/x", "p/a:ss"),
    ("bearer", "Authorization: Bearer eyJhbGciOi", "eyJhbGciOi"),
    ("basic", "Authorization: Basic dXNlcjpwYXNz", "dXNlcjpwYXNz"),
    ("basic-lower", "authorization: basic dXNlcjpwYXNzd2Q=", "dXNlcjpwYXNzd2Q"),
    ("password-assign", "password = 'hunter2'", "hunter2"),
    ("database-password", "DATABASE_PASSWORD=dbsecret1", "dbsecret1"),
    ("database-password-export", 'export DATABASE_PASSWORD="dbsecret2"', "dbsecret2"),
    ("aws-secret", "AWS_SECRET_ACCESS_KEY=AKIAEXAMPLE", "AKIAEXAMPLE"),
    ("sk-ant", "sk-ant-api03-abc12345", "api03-abc12345"),
    ("sk-ant-short", "key sk-ant-ab1 end", "ab1"),
    ("yaml-password", "  password: s3cr3t", "s3cr3t"),
    ("json-password", '{"user": "a", "password": "jsonsecret"}', "jsonsecret"),
    ("json-password-escaped", '{"password": "esc\\"aped"}', "aped"),
    ("postgres-password", "POSTGRES_PASSWORD=pgsecret1", "pgsecret1"),
    ("github-token", "GITHUB_TOKEN=ghp_abcdefghijklmnop1234", "ghp_abcdefghijklmnop1234"),
    ("db-password-yaml", "db_password: yamlsecret", "yamlsecret"),
    ("password-colon", "Password: colonsecret", "colonsecret"),
    ("kwarg", "connect(password='kwsecret')", "kwsecret"),
    ("client-secret", '{"client_secret": "clsecret"}', "clsecret"),
    ("api-key", "ANTHROPIC_API_KEY=sk-ant-zz9", "zz9"),
    ("access-key", "access_key: akvalue1", "akvalue1"),
]


@pytest.mark.parametrize(("case", "raw", "secret"), _CREDENTIAL_SHAPES, ids=[c[0] for c in _CREDENTIAL_SHAPES])
def test_scrub_fix_turn_exposure_redacts_every_credential_shape(case: str, raw: str, secret: str):
    scrubbed = scrub_fix_turn_exposure(raw)
    assert secret not in scrubbed, case
    assert "***REDACTED***" in scrubbed, case


def test_scrub_fix_turn_exposure_keeps_the_key_and_ordinary_output():
    scrubbed = scrub_fix_turn_exposure("DATABASE_PASSWORD=postgres\nE501 line too long (101 > 100)\nassert token == x")
    assert scrubbed.splitlines() == [
        "DATABASE_PASSWORD=***REDACTED***",
        "E501 line too long (101 > 100)",
        "assert token == x",
    ]


#: A credential right at the tail's cut point (85.3 landing review M2, mutants M01/M02): truncating first would
#: cut the URL's scheme off and leave a fragment of the password no URL rule can see.
_CUT_RAW = "x" * 200 + " postgres://admin:supersecretpw@db/x"
_CUT_BYTES = len("persecretpw@db/x")


def test_scrub_then_tail_bytes_redacts_before_truncating():
    """A credential split by tail truncation must not leak (Story 85.3)."""
    assert "secretpw" in tail_bytes(_CUT_RAW, max_bytes=_CUT_BYTES), "the cut must fall inside the credential"
    tailed = scrub_then_tail_bytes(_CUT_RAW, max_bytes=_CUT_BYTES)
    assert "secretpw" not in tailed
    assert "persecret" not in tailed


def test_the_fix_turn_prompt_redacts_before_truncating():
    failed = (FailedVerifyCommand(command="pixi run test", stdout=_CUT_RAW, stderr="", exit_code=1),)
    prompt = build_verify_fix_prompt(failed, output_tail_bytes=_CUT_BYTES)
    assert "secretpw" not in prompt
    assert "persecret" not in prompt


# --------------------------------------------------------------------------
# Story 85.4: the redaction never hangs the supervisor or hides what the fix needs
# --------------------------------------------------------------------------

#: The shapes the 85.3 post-landing delta review found leaking (LOW-3), and the dotted keys the same rule must
#: keep redacting now that a key never carries a `.`: ``(case id, raw text, the secret that must not survive)``.
_GH_TAIL = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"  # 36 characters, a real GitHub token's length

_LEAKING_SHAPES_85_4 = [
    ("flag-space", "mysql --password hunter2 -h db", "hunter2"),
    ("flag-space-quoted", "cli --api-key 'k3y s3cret' run", "k3y s3cret"),
    ("flag-space-token", "gh auth login --with-token ghs_abc123", "ghs_abc123"),
    ("authorization-token", "Authorization: token ghp_x", "ghp_x"),
    ("authorization-token-not-github", "Authorization: token tok123", "tok123"),
    ("proxy-authorization-any-scheme", "Proxy-Authorization: Negotiate YIIabc", "YIIabc"),
    # 85.4 review R07/R08: a JWT's dotted tail, and credentials with no scheme word.
    ("authorization-jwt", "Authorization: Bearer eyJhbGciOi.eyJzdWIi.c2lnbmF0dXJl", "eyJzdWIi"),
    ("authorization-no-scheme", "Authorization: rawtoken123", "rawtoken123"),
    ("bare-ghp", f"remote: using ghp_{_GH_TAIL} for push", _GH_TAIL),
    ("bare-github-pat", "github_pat_11ABCDEFGH0123456789_xyz in the log", "11ABCDEFGH0123456789_xyz"),
    # 85.4 review R11: every GitHub token prefix, not only ghp_.
    ("bare-gho", f"gho_{_GH_TAIL}", _GH_TAIL),
    ("bare-ghu", f"ghu_{_GH_TAIL}", _GH_TAIL),
    ("bare-ghs", f"ghs_{_GH_TAIL}", _GH_TAIL),
    ("bare-ghr", f"ghr_{_GH_TAIL}", _GH_TAIL),
    ("url-empty-user", "postgres://:pw@host/db", "pw@"),
    ("url-password-with-scheme", "https://u:ab://cd@host", "cd@"),
    ("url-digit-before-scheme", "1https://u:pw000@host", "pw000"),
    ("cookie", "Cookie: sessionid=abc", "abc"),
    ("set-cookie", "Set-Cookie: sessionid=abc; Path=/", "abc"),
    # 85.4 review R09: the second cookie pair, past whitespace.
    ("cookie-second-pair", "Cookie: a=b; session=s3cookie", "s3cookie"),
    ("json-compact", '{"password":"cmpsecret"}', "cmpsecret"),
    ("dotted-key", "spring.datasource.password=dotsecret", "dotsecret"),
    ("dotted-attribute", "config.api_key = 'attrsecret'", "attrsecret"),
    # 85.4 review MEDIUM: a quoted key that carries a `.` (85.3 redacted every one of these).
    ("quoted-dotted-json", '{"db.password": "hunter2"}', "hunter2"),
    ("quoted-dotted-python", "{'spring.datasource.password': 'x9dot'}", "x9dot"),
    ("quoted-dotted-secret", '"app.secret": "v1dot"', "v1dot"),
    ("quoted-dotted-compact", '"auth.token":"v2dot"', "v2dot"),
    ("quoted-dotted-equals", '"secrets.api_key" = "v3dot"', "v3dot"),
    ("quoted-dotted-equals-compact", '"client.secret"="v4dot"', "v4dot"),
    # 85.4 review LOW-2: a `:` with no space after it is still a separator unless a digit follows a bare key.
    ("json-colon-number", '{"password":12345}', "12345"),
    ("bare-colon-no-space", "password:nospace", "nospace"),
    ("bare-colon-slash-value", "aws_secret_access_key:abc/def", "abc/def"),
    ("bare-colon-env", "GITHUB_TOKEN:ghp_x1", "ghp_x1"),
    # 85.4 review LOW-3: a colour code before a credential.
    ("ansi-url", "\x1b[32mpostgres://admin:ansipw@db/x\x1b[0m", "ansipw"),
    ("ansi-flag", "\x1b[0m--password ansiflag", "ansiflag"),
    ("ansi-cookie", "\x1b[36mCookie: s=ansicook\x1b[0m", "ansicook"),
    # A credential header written as a quoted key (Python and JSON dicts).
    ("quoted-authorization-python", "{'authorization': 'Bearer hdrtok1'}", "hdrtok1"),
    ("quoted-authorization-json", '"Authorization": "Bearer hdrtok2"', "hdrtok2"),
    ("quoted-cookie-json", '{"Cookie": "sid=hdrtok3"}', "hdrtok3"),
]


@pytest.mark.parametrize(("case", "raw", "secret"), _LEAKING_SHAPES_85_4, ids=[c[0] for c in _LEAKING_SHAPES_85_4])
def test_scrub_fix_turn_exposure_redacts_the_shapes_the_85_3_delta_review_found_leaking(
    case: str, raw: str, secret: str
):
    scrubbed = scrub_fix_turn_exposure(raw)
    assert secret not in scrubbed, case
    assert "***REDACTED***" in scrubbed, case


@pytest.mark.parametrize(
    "line",
    [
        "token_budget.py:42:5: E501 line too long",
        "src/pyforge/marshal/core/token_budget.py:42:5: E501 line too long (101 > 100)",
        "bin/token:42:5: error: unexpected indent",
        "secrets_loader.py: line 42, col 5, Error - Missing semicolon.",
        "password.py:10:1: F401 'os' imported but unused",
        "tests/unit/test_secret_store.py::test_round_trip PASSED",
    ],
)
def test_a_compiler_location_keeps_its_line_and_column(line: str):
    """LOW-2: a file named for a secret is no key (a key never carries a `.`), and `:` followed by a digit is no
    separator."""
    assert scrub_fix_turn_exposure(line) == line


@pytest.mark.parametrize(
    "line",
    [
        "ModuleNotFoundError: No module named 'ghp_import'",
        "cli --no-token-check --verbose",
        '"tough-cookie": "^5.0.0", "azure-mgmt-authorization": "4.0.0"',
    ],
)
def test_ordinary_output_that_only_looks_like_a_credential_is_kept(line: str):
    """85.4 review: a short `ghp_` name is no token (LOW-5), a flag after a secret-named flag is no value (R10), and a
    quoted key is a credential header only when it is named whole."""
    assert scrub_fix_turn_exposure(line) == line


@pytest.mark.parametrize(
    "text",
    [
        "27 |     except TokenError:\n   |     ^^^^^^ E722 Do not use bare `except`",
        "    if token:\n>       assert budget.spent < budget.limit",
        "password:\nnext line",
    ],
    ids=["ruff-full-format", "pytest-failure-arrow", "bare-key-at-line-end"],
)
def test_a_value_is_never_taken_from_the_next_line(text: str):
    """85.4 review LOW-4: whitespace after a separator never crosses a newline, so the next line's gutter or arrow
    survives."""
    assert scrub_fix_turn_exposure(text) == text


def test_the_scrub_removes_terminal_colour_codes():
    """LOW-3: colour codes go first -- a code ends in a letter, which would hide the start of every rule after it."""
    assert scrub_fix_turn_exposure("\x1b[1;31mE501\x1b[0m line too long\x1b[K") == "E501 line too long"


def test_an_unclosed_quoted_value_never_takes_the_next_line():
    """A quoted value ends at its line: an unclosed quote redacts its own value and leaves the next line -- what the
    fix needs -- as it was."""
    scrubbed = scrub_fix_turn_exposure('token = "abc\nE501 at "x.py" line 3')
    assert scrubbed.splitlines() == ["token = ***REDACTED***", 'E501 at "x.py" line 3']


class _DeadlineExpired(Exception):
    pass


def _scrub_seconds(text: str, *, deadline_s: float = 5.0) -> float:
    """How long the scrub takes on ``text``. A backtracking regex fails the test at ``deadline_s`` instead of hanging
    the suite: ``re`` checks for signals while it matches, so the SIGALRM handler interrupts it."""

    def _expired(_signum: int, _frame: object) -> None:
        raise _DeadlineExpired

    previous = signal.signal(signal.SIGALRM, _expired)
    signal.setitimer(signal.ITIMER_REAL, deadline_s)
    try:
        start = time.perf_counter()
        scrub_fix_turn_exposure(text)
        return time.perf_counter() - start
    except _DeadlineExpired:
        pytest.fail(f"the scrub was still running after {deadline_s} s")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


@pytest.mark.parametrize("quote", ['"', "'"])
def test_an_unclosed_quote_before_100k_backslashes_scrubs_in_under_a_second(quote: str):
    """MEDIUM (ReDoS): a secret key, `=`, an opening quote and 100,000 backslashes with no closing quote. 85.3's
    quoted-value branch matched a backslash two ways and backtracked exponentially (N=1000 took over 20 s)."""
    assert _scrub_seconds(f"password={quote}" + "\\" * 100_000) < 1.0


def test_a_100kb_run_of_url_scheme_characters_scrubs_in_under_a_second():
    """LOW-1: a URL scheme is tried from the start of a run of scheme characters only, never from inside it."""
    assert _scrub_seconds("ab+c.d-1" * 12_500) < 1.0


#: Separator-free or keyword-dense 100 KB runs, one per rule, that a quantifier able to start anywhere in a run
#: (or to rescan it from every keyword) turns quadratic.
_ADVERSARIAL_100KB = [
    ("repeated-url-userinfo", "a://u:" * 16_667),
    ("keyword-run", "token" * 20_000),
    ("keyword-run-then-separator", "token" * 20_000 + "="),
    ("flag-run", "--token" * 14_286),
    ("spaces-after-a-key", "password=" + " " * 100_000),
    ("authorization-word-run", "Authorization: " + "a" * 100_000),
    ("cookie-pairs", "Cookie: " + "a=b; " * 20_000),
    ("github-prefix-run", "ghp_" * 25_000),
    ("url-password-scheme-run", "a://u:" + "p://" * 25_000),
    ("quoted-dotted-keyword-run", '"' + "token." * 16_667),
    ("quoted-header-run", "'cookie" * 14_286),
    ("colour-code-run", "\x1b[3" * 33_334),
]


@pytest.mark.parametrize(("case", "text"), _ADVERSARIAL_100KB, ids=[c[0] for c in _ADVERSARIAL_100KB])
def test_every_redaction_rule_stays_linear_on_100kb_adversarial_input(case: str, text: str):
    assert _scrub_seconds(text) < 1.0, case


def test_extract_failed_verify_commands_ignores_gate_018_pseudo_command():
    findings = (
        Finding(
            code="MRS-GATE-018",
            severity=Severity.ERROR,
            message="deferred work intake refused",
        ),
    )
    extracted = extract_failed_verify_commands((), findings)
    assert extracted == ()


def test_wait_for_process_reaps_exited_child_without_zombie_poll():
    import subprocess
    import sys

    proc = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    result = wait_for_process(PosixProcess(), proc.pid, timeout_s=30.0)
    assert isinstance(result, ProcessWaitResult)
    assert result.exited is True
    assert result.returncode == 0


def test_decide_verify_fix_turn_skips_without_failed_commands():
    assert (
        decide_verify_fix_turn(
            flag_enabled=True,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
            has_failed_commands=False,
        ).run
        is False
    )


def test_verify_fix_loop_enabled_reads_off_from_shipped_tree(tmp_path):
    repo = tmp_path / "repo"
    flags_dir = repo / "src/platform/config"
    flags_dir.mkdir(parents=True)
    flags_dir.joinpath("flags.json").write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.marshal.verify_fix_loop": {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": "off",
                        "metadata": {
                            "owner": "marshal",
                            "story": "85-1-",
                            "created": "2026-10-03",
                            "on_everywhere": "",
                            "cleanup_by": "",
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    enabled, warning = verify_fix_loop_enabled(repo_root=repo)
    assert enabled is False
    assert warning is None


def test_verify_fix_loop_enabled_unset_environment_reads_dev_on(tmp_path, monkeypatch):
    """Story 85.3: unset PYFORGE_ENVIRONMENT follows dev overlay (verify_fix on)."""
    repo = tmp_path / "repo"
    flags_dir = repo / "src/platform/config"
    flags_dir.mkdir(parents=True)
    overlays = flags_dir / "flag-overlays.json"
    overlays.write_text(
        json.dumps(
            {"dev": {"pyforge.marshal.verify_fix_loop": "on"}, "production": {"pyforge.marshal.verify_fix_loop": "off"}}
        ),
        encoding="utf-8",
    )
    flags_dir.joinpath("flags.json").write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.marshal.verify_fix_loop": {
                        "state": "ENABLED",
                        "defaultVariant": "off",
                        "variants": {"on": True, "off": False},
                        "metadata": {
                            "owner": "marshal",
                            "story": "85-3-x",
                            "created": "2026-10-03",
                            "on_everywhere": "",
                            "cleanup_by": "",
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    enabled, warning = verify_fix_loop_enabled(repo_root=repo)
    assert warning is None
    assert enabled is True


def test_verify_fix_loop_enabled_flag_config_error_returns_warning(monkeypatch, tmp_path):
    def _raise_flag_config(*_args, **_kwargs):
        raise FlagConfigError("unknown environment")

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_verify.read_boolean",
        _raise_flag_config,
    )
    enabled, warning = verify_fix_loop_enabled(repo_root=tmp_path)
    assert enabled is False
    assert warning == "unknown environment"


def test_wait_for_process_invokes_on_poll(monkeypatch):
    ticks = iter([0.0, 0.0, 10.0])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    polled: list[str] = []
    wait_for_process(PosixProcess(), 1, timeout_s=5.0, on_poll=lambda: polled.append("x"))
    assert polled


class _NonChild:
    """A ``ProcessPort`` for a pid that is not this process's child: scripted liveness, a fixed start time."""

    def __init__(self, alive, *, started: float | None = None) -> None:
        self._alive = list(alive) if isinstance(alive, list) else None
        self._constant = alive if isinstance(alive, bool) else False
        self._started = started
        self.probes = 0

    def is_alive(self, _pid: int) -> bool:
        self.probes += 1
        if self._alive is None:
            return self._constant
        return self._alive.pop(0) if len(self._alive) > 1 else self._alive[0]

    def process_start_time(self, _pid: int) -> float | None:
        return self._started


def _not_a_child(monkeypatch) -> None:
    def fake_waitpid(_pid: int, _opts: int):
        raise ChildProcessError

    monkeypatch.setattr(os, "waitpid", fake_waitpid)


def test_wait_for_process_child_process_error(monkeypatch):
    """A pid that is not this process's child and is gone: exited, exit code unknowable."""
    _not_a_child(monkeypatch)
    result = wait_for_process(_NonChild(False), 123, timeout_s=1.0)
    assert result == ProcessWaitResult(exited=True, returncode=None)


def test_wait_for_process_polls_a_live_non_child_until_it_exits(monkeypatch):
    """Story 85.2 review H1: ``ChildProcessError`` no longer reads as exited -- the pid's liveness decides."""
    _not_a_child(monkeypatch)
    process = _NonChild([True, True, False])
    polled: list[str] = []
    result = wait_for_process(process, 123, timeout_s=30.0, poll_s=0.01, on_poll=lambda: polled.append("x"))
    assert result == ProcessWaitResult(exited=True, returncode=None)
    assert process.probes == 3
    assert polled == ["x", "x"]


def test_wait_for_process_times_out_on_a_live_non_child(monkeypatch):
    _not_a_child(monkeypatch)
    result = wait_for_process(_NonChild(True), 123, timeout_s=0.2, poll_s=0.05)
    assert result == ProcessWaitResult(exited=False, returncode=None)


def test_wait_for_process_reads_a_reused_non_child_pid_as_exited(monkeypatch):
    """Story 83.1's start-time check: the pid exists, but its process started hours after the launch."""
    from datetime import datetime, timezone

    _not_a_child(monkeypatch)
    launched = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    process = _NonChild(True, started=launched.timestamp() + 6 * 3600)
    result = wait_for_process(process, 123, timeout_s=30.0, poll_s=0.01, launched_at=launched)
    assert result == ProcessWaitResult(exited=True, returncode=None)


def test_wait_for_process_waits_for_a_real_detached_non_child():
    """A real session this process did not launch (its shell parent exited): waited for until it exits."""
    out = subprocess.run(
        ["sh", "-c", "sleep 0.5 >/dev/null 2>&1 & echo $!"],
        capture_output=True,
        text=True,
        check=True,
        start_new_session=True,
    )
    pid = int(out.stdout.strip())
    try:
        start = time.monotonic()
        result = wait_for_process(PosixProcess(), pid, timeout_s=20.0, poll_s=0.05)
        elapsed = time.monotonic() - start
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    assert result == ProcessWaitResult(exited=True, returncode=None)
    assert 0.2 <= elapsed < 15.0


def test_fix_session_alive_reads_a_zombie_as_exited(monkeypatch, tmp_path):
    """A non-child that exited but awaits its parent's reap is not running (``ProcessPort`` counts it alive)."""
    from pyforge.marshal import dispatch_verify

    stats = {
        4242: "4242 (bash (x) y) Z 1 4242 4242 0 -1\n",
        4343: "4343 (python3) S 1 4343 4343 0 -1\n",
    }
    real_read = Path.read_text

    def fake_read(self, *args, **kwargs):
        for pid, stat in stats.items():
            if str(self) == f"/proc/{pid}/stat":
                return stat
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read)
    assert dispatch_verify.fix_session_alive(_NonChild(True), 4242, launched_at=None) is False
    assert dispatch_verify.fix_session_alive(_NonChild(True), 4343, launched_at=None) is True
    assert dispatch_verify._is_zombie(4242) is True
    assert dispatch_verify._is_zombie(4343) is False


def test_wait_for_process_os_error_in_loop(monkeypatch):
    def fake_waitpid(_pid: int, _opts: int):
        raise OSError

    monkeypatch.setattr(os, "waitpid", fake_waitpid)
    result = wait_for_process(PosixProcess(), 123, timeout_s=1.0)
    assert result == ProcessWaitResult(exited=False, returncode=None)


def test_terminate_process_group_falls_back_to_kill_when_no_pgid(monkeypatch):
    kills: list[tuple[int, int]] = []

    def fake_getpgid(_pid: int) -> int:
        raise OSError

    def fake_kill(pid: int, sig: int) -> None:
        kills.append((pid, sig))

    class _Dead:
        def is_alive(self, _pid: int) -> bool:
            return False

    monkeypatch.setattr(os, "getpgid", fake_getpgid)
    monkeypatch.setattr(os, "kill", fake_kill)
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    terminate_process_group(77, grace_s=0.0, process=_Dead())
    assert kills == [(77, signal.SIGTERM)]


def test_terminate_process_group_swallows_kill_oserror(monkeypatch):
    monkeypatch.setattr(os, "getpgid", lambda _pid: (_ for _ in ()).throw(OSError))
    monkeypatch.setattr(os, "kill", lambda *_args: (_ for _ in ()).throw(OSError))
    terminate_process_group(1)  # must not raise


def test_terminate_process_group_killpg_failure_falls_back_to_kill(monkeypatch):
    kills: list[tuple[int, int]] = []

    class _Dead:
        def is_alive(self, _pid: int) -> bool:
            return False

    monkeypatch.setattr(os, "getpgid", lambda _pid: 5)

    def fake_killpg(_pgid: int, _sig: int) -> None:
        raise OSError

    def fake_kill(pid: int, sig: int) -> None:
        kills.append((pid, sig))

    monkeypatch.setattr(os, "killpg", fake_killpg)
    monkeypatch.setattr(os, "kill", fake_kill)
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    terminate_process_group(88, grace_s=0.0, process=_Dead())
    assert kills == [(88, signal.SIGTERM)]


def test_terminate_process_group_killpg_and_kill_both_fail(monkeypatch):
    class _Alive:
        def is_alive(self, _pid: int) -> bool:
            return True

    monkeypatch.setattr(os, "getpgid", lambda _pid: 5)
    monkeypatch.setattr(os, "killpg", lambda *_args: (_ for _ in ()).throw(OSError))
    monkeypatch.setattr(os, "kill", lambda *_args: (_ for _ in ()).throw(OSError))
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    terminate_process_group(88, grace_s=0.0, process=_Alive())  # must not raise


def test_terminate_process_group_never_signals_a_group_address_or_init(monkeypatch):
    """Story 85.2: a journaled pid of 0 or below is a process-group address to ``kill``, and 1 is init."""
    calls: list[tuple[str, int]] = []
    monkeypatch.setattr(os, "getpgid", lambda pid: calls.append(("getpgid", pid)) or pid)
    monkeypatch.setattr(os, "killpg", lambda pgid, _sig: calls.append(("killpg", pgid)))
    monkeypatch.setattr(os, "kill", lambda pid, _sig: calls.append(("kill", pid)))
    for pid in (1, 0, -1):
        terminate_process_group(pid)
    assert calls == []


def test_terminate_process_group_signals_only_the_pid_when_it_shares_this_process_group(monkeypatch):
    """``killpg`` on this process's own group would stop the supervisor itself."""
    calls: list[tuple[str, int, int]] = []

    class _Dead:
        def is_alive(self, _pid: int) -> bool:
            return False

    monkeypatch.setattr(os, "getpgid", lambda _pid: os.getpgrp())
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: calls.append(("killpg", pgid, sig)))
    monkeypatch.setattr(os, "kill", lambda pid, sig: calls.append(("kill", pid, sig)))
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    terminate_process_group(4242, grace_s=0.0, process=_Dead())
    assert calls == [("kill", 4242, signal.SIGTERM)]


def test_terminate_process_group_never_passes_a_group_id_of_this_group_or_init_to_killpg(monkeypatch):
    """Final landing review nit: ``killpg(0)`` addresses this process's own group (a kernel thread reports pgid 0)
    and ``killpg(1)`` init's group -- a pid in either is signalled alone, never its group."""
    calls: list[tuple[str, int, int]] = []
    monkeypatch.setattr(os, "getpgrp", lambda: 7777)
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: calls.append(("killpg", pgid, sig)))
    monkeypatch.setattr(os, "kill", lambda pid, sig: calls.append(("kill", pid, sig)))

    class _Dead:
        def is_alive(self, _pid: int) -> bool:
            return False

    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    for pgid in (0, 1):
        calls.clear()
        monkeypatch.setattr(os, "getpgid", lambda _pid, pgid=pgid: pgid)
        terminate_process_group(4242, grace_s=0.0, process=_Dead())
        assert calls == [("kill", 4242, signal.SIGTERM)]


def test_terminate_process_group_signals_process_group(monkeypatch):
    calls: list[tuple[int, int]] = []

    def fake_getpgid(pid: int) -> int:
        assert pid == 99
        return 42

    def fake_killpg(pgid: int, sig: int) -> None:
        calls.append((pgid, sig))

    class _DeadProcess:
        def is_alive(self, _pid: int) -> bool:
            return False

    monkeypatch.setattr(os, "getpgid", fake_getpgid)
    monkeypatch.setattr(os, "killpg", fake_killpg)
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    result = terminate_process_group(99, grace_s=0.0, process=_DeadProcess())
    assert (42, signal.SIGTERM) in calls
    assert isinstance(result, TerminateProcessGroupResult)
    assert result.signalled_term is True


def test_terminate_process_group_sends_sigkill_after_grace(monkeypatch):
    calls: list[tuple[int, int]] = []
    alive = {"v": True}

    class _AliveProcess:
        def is_alive(self, _pid: int) -> bool:
            return alive["v"]

    monkeypatch.setattr(os, "getpgid", lambda _pid: 42)
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: calls.append((pgid, sig)))
    monkeypatch.setattr(os, "waitpid", lambda _pid, _opts: (0, 0))
    result = terminate_process_group(99, grace_s=0.0, process=_AliveProcess())
    assert (42, signal.SIGTERM) in calls
    assert (42, signal.SIGKILL) in calls
    assert result.signalled_kill is True


def test_wait_for_process_times_out_on_slow_child():
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    try:
        result = wait_for_process(PosixProcess(), proc.pid, timeout_s=0.2, poll_s=0.05)
        assert result.exited is False
        assert result.returncode is None
    finally:
        terminate_process_group(proc.pid, grace_s=0.5)


def test_fix_turn_rule_mutation_flag_off_skips_turn():
    """Removing the flag gate makes this fail (was run=True)."""
    assert (
        decide_verify_fix_turn(
            flag_enabled=True,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is True
    )
    assert (
        decide_verify_fix_turn(
            flag_enabled=False,
            verification_verdict=DispatchVerificationVerdict.REFUSED.value,
            has_git_progress=True,
            fix_turn_already_ran=False,
            session_alive=False,
        ).run
        is False
    )


# --------------------------------------------------------------------------
# Story 85.2 (CAP-286): the pure in-flight reading the supervisor and every CLI reader share
# --------------------------------------------------------------------------


def _fix_lines(*entries):
    from pyforge.marshal.core.journal import prepare_for_write

    return [prepare_for_write(entry).line for entry in entries]


def _fix_entry(counter, phase, payload, *, intent_counter=None, run_id="run-1", ts="2026-10-03T10:00:00.000Z"):
    from pyforge.marshal.core import dispatch as dispatch_core
    from pyforge.marshal.core.journal import JournalEntryId, build_entry

    return build_entry(
        id=JournalEntryId("dispatch-supervisor-1", counter),
        ts=ts,
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=phase,
        intent_id=JournalEntryId("dispatch-supervisor-1", intent_counter) if intent_counter is not None else None,
        payload=payload,
    )


def test_in_flight_verify_fix_turn_reads_the_open_intent_and_its_journaled_pid():
    from datetime import datetime, timezone

    from pyforge.marshal.core.dispatch_verify_fix import fix_intent_ref, in_flight_verify_fix_turn
    from pyforge.marshal.core.journal import JournalEntryId, Phase, fold

    ref = fix_intent_ref(JournalEntryId("dispatch-supervisor-1", 1))
    assert ref == {"writer_id": "dispatch-supervisor-1", "counter": 1}
    folded = fold(
        _fix_lines(
            _fix_entry(1, Phase.INTENT, {"launch_mode": "fix_only"}),
            _fix_entry(2, Phase.OBSERVATION, {"session_pid": 4242, "fix_intent_id": ref}),
            # Every decoy sits AFTER the real pid, where the reader's reverse scan meets it first (review L2/L3): an
            # observation naming another INTENT, a bool, a group-address pid, pid 0, and another run's pid are never
            # this turn's pid.
            _fix_entry(3, Phase.OBSERVATION, {"session_pid": 111, "fix_intent_id": {"writer_id": "x", "counter": 9}}),
            _fix_entry(4, Phase.OBSERVATION, {"session_pid": True, "fix_intent_id": ref}),
            _fix_entry(5, Phase.OBSERVATION, {"session_pid": -5, "fix_intent_id": ref}),
            _fix_entry(6, Phase.OBSERVATION, {"session_pid": 0, "fix_intent_id": ref}),
            _fix_entry(7, Phase.OBSERVATION, {"session_pid": 999, "fix_intent_id": ref}, run_id="run-2"),
        )
    )
    in_flight = in_flight_verify_fix_turn(folded, "run-1")
    assert in_flight is not None
    assert in_flight.session_pid == 4242
    assert in_flight.started_at == datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    assert in_flight.intent.id == JournalEntryId("dispatch-supervisor-1", 1)
    assert in_flight_verify_fix_turn(folded, "run-other") is None


def test_in_flight_verify_fix_turn_prefers_a_pid_on_the_intent_and_reports_none_without_one():
    from pyforge.marshal.core.dispatch_verify_fix import in_flight_verify_fix_turn
    from pyforge.marshal.core.journal import Phase, fold

    on_intent = fold(_fix_lines(_fix_entry(1, Phase.INTENT, {"session_pid": 5151})))
    no_pid = fold(_fix_lines(_fix_entry(1, Phase.INTENT, {"launch_mode": "fix_only"})))
    assert in_flight_verify_fix_turn(on_intent, "run-1").session_pid == 5151
    assert in_flight_verify_fix_turn(no_pid, "run-1").session_pid is None


def test_a_closed_fix_turn_is_not_in_flight():
    from pyforge.marshal.core.dispatch_verify_fix import in_flight_verify_fix_turn, pending_verify_fix_intent
    from pyforge.marshal.core.journal import Phase, fold

    folded = fold(
        _fix_lines(
            _fix_entry(1, Phase.INTENT, {"session_pid": 5151}),
            _fix_entry(2, Phase.OUTCOME, {"ok": False}, intent_counter=1),
        )
    )
    assert pending_verify_fix_intent(folded, "run-1") is None
    assert in_flight_verify_fix_turn(folded, "run-1") is None


def test_fix_turn_remaining_budget_is_measured_from_the_intent_and_never_negative():
    from datetime import datetime, timedelta, timezone

    from pyforge.marshal.core.dispatch_verify_fix import fix_turn_remaining_budget_s

    started = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    assert (
        fix_turn_remaining_budget_s(budget_s=900.0, started_at=started, now=started + timedelta(seconds=100)) == 800.0
    )
    assert fix_turn_remaining_budget_s(budget_s=900.0, started_at=started, now=started + timedelta(hours=1)) == 0.0


def test_pid_start_matches_launch_is_story_83_1s_reuse_guard():
    from datetime import datetime, timezone

    from pyforge.marshal.core.dispatch import PID_START_TOLERANCE_SECONDS, pid_start_matches_launch

    launched = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
    at = launched.timestamp()
    assert pid_start_matches_launch(at + 1.0, launched) is True
    assert pid_start_matches_launch(at - PID_START_TOLERANCE_SECONDS, launched) is True
    assert pid_start_matches_launch(at + PID_START_TOLERANCE_SECONDS + 1.0, launched) is False
    assert pid_start_matches_launch(at - 3600.0, launched) is False
    assert pid_start_matches_launch(None, launched) is True
    assert pid_start_matches_launch(at - 3600.0, None) is True


# --------------------------------------------------------------------------
# Story 85.3 landing review H1/H5/M8: the fix turn's argv -- the session it resumes, and the prompt never on it
# --------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[6]
_FIX_PROMPT = "UNIQUE-FIX-PROMPT-85-3: make pixi run test pass"


def _fix_profiles() -> dict[str, object]:
    """The packaged claude and cursor profiles, and the repo overlay's cursor -- every fix template that ships."""
    from pyforge.marshal.core.harness_profile import load_packaged_profiles, load_profiles

    packaged = load_packaged_profiles()
    overlaid, errors = load_profiles(_REPO_ROOT)
    assert errors == ()
    assert (_REPO_ROOT / "_bmad-output/harness-profiles/cursor.toml").is_file()
    return {"claude": packaged["claude"], "cursor": packaged["cursor"], "cursor-overlay": overlaid["cursor"]}


def test_the_packaged_claude_resume_argv_resumes_by_id_without_session_id():
    """H1: claude 2.1.284 refuses ``--session-id`` beside ``--resume``; the launch pins the id, the resume names it."""
    from pyforge.marshal.core.harness_profile import load_packaged_profiles, render_dispatch_argv

    claude = load_packaged_profiles()["claude"]
    argv, _, _ = render_fix(
        claude, mode="resume", binary_path="claude", worktree=Path("/wt"), model=None, session_id="sid-85-3"
    )
    assert "--session-id" not in argv
    assert argv[argv.index("--resume") + 1] == "sid-85-3"
    launch, _, _ = render_dispatch_argv(
        claude, binary_path="claude", worktree=Path("/wt"), prompt="go", model=None, session_id="sid-85-3"
    )
    assert launch[launch.index("--session-id") + 1] == "sid-85-3"
    assert "--resume" not in launch


@pytest.mark.parametrize("name", ["claude", "cursor", "cursor-overlay"])
@pytest.mark.parametrize("mode", ["resume", "fix_only"])
def test_no_shipped_fix_template_carries_a_prompt_on_argv(name: str, mode: str):
    """H5/M8: every shipped fix template takes its prompt on stdin, so nothing but the binary and flags is argv."""
    from pyforge.marshal.core.harness_profile import verify_fix_prompt_on_stdin

    profile = _fix_profiles()[name]
    template = profile.resume_argv if mode == "resume" and profile.resume_argv else profile.fix_only_argv
    assert "{prompt}" not in " ".join(template)
    assert verify_fix_prompt_on_stdin(profile, mode=mode) is True
    argv, _, _ = render_fix(
        profile, mode=mode, binary_path="/bin/x", worktree=Path("/wt"), model="opus", session_id="sid-1"
    )
    assert not any("{" in token and "}" in token and "prompt" in token for token in argv)
    assert all(_FIX_PROMPT not in token for token in argv)


def test_cursor_declares_no_resume_template():
    """H2: the Cursor launch records no session id, so its fix turn is fix-only."""
    profiles = _fix_profiles()
    assert profiles["cursor"].resume_argv == ()
    assert profiles["cursor-overlay"].resume_argv == ()


@pytest.mark.parametrize("name", ["copilot", "gemini", "devin"])
def test_a_profile_without_a_fix_template_refuses_rather_than_falling_back_to_argv(name: str):
    """H5: the launch template's ``{prompt}`` is argv -- a profile with no fix template refuses, naming itself."""
    from pyforge.marshal.core.harness_profile import (
        HarnessProfileError,
        load_packaged_profiles,
        verify_fix_prompt_on_stdin,
    )

    profile = load_packaged_profiles()[name]
    assert (profile.resume_argv, profile.fix_only_argv) == ((), ())
    with pytest.raises(HarnessProfileError, match=repr(name)):
        render_fix(profile, mode="fix_only", binary_path="/bin/x", worktree=Path("/wt"), model=None)
    with pytest.raises(HarnessProfileError, match=repr(name)):
        verify_fix_prompt_on_stdin(profile, mode="resume")


@pytest.mark.parametrize(
    ("template", "message"),
    [
        (["-p", "{prompt}"], "must not carry '{prompt}'"),
        (["-p", "--message={prompt}", "{prompt_stdin}"], "must not carry '{prompt}'"),
        (["-p"], "exactly once"),
        (["-p", "{prompt_stdin}", "{prompt_file}"], "exactly once"),
        (["-p", "{prompt_stdin}", "{prompt_stdin}"], "exactly once"),
        (["-p", "x{prompt_stdin}"], "whole"),
    ],
)
@pytest.mark.parametrize("label", ["resume_argv", "fix_only_argv"])
def test_parse_profile_refuses_a_fix_template_without_exactly_one_safe_prompt_form(label, template, message):
    from pyforge.marshal.core.harness_profile import HarnessProfileError

    with pytest.raises(HarnessProfileError, match=message):
        parse_profile({"name": "fake", "binary": "fake", "argv": ["{prompt}"], label: template}, source="t")


@pytest.mark.parametrize("token", ["{prompt_stdin}", "{prompt_file}"])
def test_parse_profile_refuses_a_fix_prompt_form_in_the_launch_argv(token):
    from pyforge.marshal.core.harness_profile import HarnessProfileError

    with pytest.raises(HarnessProfileError, match="must not carry"):
        parse_profile({"name": "fake", "binary": "fake", "argv": ["{prompt}", token]}, source="t")


class _CapturedPopen:
    pid = 5151


def _capture_fix_launch(monkeypatch, *, profile, mode, tmp_path):
    """Drive ``BmadBuildHarness.dispatch_verify_fix`` with ``Popen`` recorded: the argv, and what stdin held."""
    from pyforge.marshal.adapters import harness_bmadbuild
    from pyforge.marshal.ports.build_harness import HarnessResolution

    seen: dict[str, object] = {}

    def _popen(argv, **kwargs):
        seen["argv"] = list(argv)
        stdin = kwargs["stdin"]
        seen["stdin"] = stdin.read().decode("utf-8") if hasattr(stdin, "read") else stdin
        return _CapturedPopen()

    monkeypatch.setattr(harness_bmadbuild.subprocess, "Popen", _popen)
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    resolution = HarnessResolution(profile=profile.name, spec=profile, binary_path="/bin/x")
    launch = harness_bmadbuild.BmadBuildHarness().dispatch_verify_fix(
        tmp_path,
        resolution=resolution,
        prompt=_FIX_PROMPT,
        model="opus",
        log_path=run_dir / "verify-fix.log",
        launch_mode=mode,
        project_slug="pyforge-marshal",
        harness_session_id="sid-85-3",
        run_dir=run_dir,
    )
    return launch, seen, run_dir


@pytest.mark.parametrize(
    ("name", "mode"), [("claude", "resume"), ("claude", "fix_only"), ("cursor-overlay", "fix_only")]
)
def test_the_fix_turn_launch_feeds_the_prompt_on_stdin_from_a_private_file(monkeypatch, tmp_path, name, mode):
    """H5/M8 + the 0600 prompt file: the session's stdin is the prompt; argv never holds it."""
    from pyforge.marshal.core.dispatch_verify_fix import VERIFY_FIX_PROMPT_FILENAME

    launch, seen, run_dir = _capture_fix_launch(
        monkeypatch, profile=_fix_profiles()[name], mode=mode, tmp_path=tmp_path
    )

    assert seen["stdin"] == _FIX_PROMPT
    assert all(_FIX_PROMPT not in token for token in seen["argv"])
    assert tuple(seen["argv"]) == launch.command
    prompt_file = run_dir / VERIFY_FIX_PROMPT_FILENAME
    assert prompt_file.read_text(encoding="utf-8") == _FIX_PROMPT
    assert prompt_file.stat().st_mode & 0o777 == 0o600
    if mode == "resume":
        assert seen["argv"][seen["argv"].index("--resume") + 1] == "sid-85-3"


def test_the_prompt_file_is_rewritten_0600_when_it_already_exists(monkeypatch, tmp_path):
    from pyforge.marshal.core.dispatch_verify_fix import VERIFY_FIX_PROMPT_FILENAME

    stale = tmp_path / "run" / VERIFY_FIX_PROMPT_FILENAME
    stale.parent.mkdir()
    stale.write_text("stale", encoding="utf-8")
    stale.chmod(0o644)

    _capture_fix_launch(monkeypatch, profile=_fix_profiles()["claude"], mode="fix_only", tmp_path=tmp_path)

    assert stale.read_text(encoding="utf-8") == _FIX_PROMPT
    assert stale.stat().st_mode & 0o777 == 0o600


def test_a_profile_without_a_fix_template_refuses_the_launch_naming_it(monkeypatch, tmp_path):
    from pyforge.marshal.adapters.harness_bmadbuild import BuildHarnessError
    from pyforge.marshal.core.dispatch_verify_fix import VERIFY_FIX_PROMPT_FILENAME
    from pyforge.marshal.core.harness_profile import load_packaged_profiles

    with pytest.raises(BuildHarnessError, match="'copilot'"):
        _capture_fix_launch(
            monkeypatch, profile=load_packaged_profiles()["copilot"], mode="fix_only", tmp_path=tmp_path
        )
    assert not (tmp_path / "run" / VERIFY_FIX_PROMPT_FILENAME).exists()


def test_the_story_launch_keeps_dev_null_as_the_sessions_stdin(monkeypatch, tmp_path):
    """85.3 delta review X02: only a fix turn's prompt file becomes a session's stdin; the story launch (``dispatch``)
    keeps ``/dev/null``, so a session never reads the supervisor's stdin."""
    from pyforge.marshal.adapters import harness_bmadbuild
    from pyforge.marshal.ports.build_harness import HarnessResolution

    seen: dict[str, object] = {}

    def _popen(argv, **kwargs):
        seen["stdin"] = kwargs["stdin"]
        return _CapturedPopen()

    monkeypatch.setattr(harness_bmadbuild.subprocess, "Popen", _popen)
    profile = parse_profile({"name": "fake", "binary": "fake", "argv": ["{prompt}"]}, source="test")
    worktree = tmp_path / "wt"
    worktree.mkdir()

    harness_bmadbuild.BmadBuildHarness().dispatch(
        worktree,
        resolution=HarnessResolution(profile="fake", spec=profile, binary_path="/bin/x"),
        project_slug="pyforge-marshal",
        story_key="85-4-example",
        spec_path=worktree / "spec.md",
        model=None,
        budget_env={},
        log_path=tmp_path / "session.log",
    )

    assert seen["stdin"] is subprocess.DEVNULL


# --------------------------------------------------------------------------
# Story 85.3 landing review M1/M2 (M10): the timeout stop, against real processes
# --------------------------------------------------------------------------


def _gone_or_zombie(pid: int, seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        except OSError:
            return True
        if stat[stat.rfind(")") + 2 : stat.rfind(")") + 3] == "Z":
            return True
        time.sleep(0.05)
    return False


def test_terminate_process_group_reaps_a_leader_that_obeys_sigterm():
    """M10: the stopped child is reaped -- no zombie left -- and its signal exit is reported."""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    time.sleep(0.2)
    result = terminate_process_group(proc.pid, grace_s=5.0)
    assert result.signalled_term is True
    assert result.reaped is True
    assert result.returncode == -signal.SIGTERM
    try:
        os.waitpid(proc.pid, os.WNOHANG)
    except ChildProcessError:
        pass
    else:  # pragma: no cover - the defect this pins
        raise AssertionError("the leader was left unreaped")


def test_terminate_process_group_kills_and_reaps_a_leader_that_ignores_sigterm():
    code = (
        "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('ready', flush=True); time.sleep(60)"
    )
    proc = subprocess.Popen([sys.executable, "-c", code], start_new_session=True, stdout=subprocess.PIPE, text=True)
    assert proc.stdout is not None and proc.stdout.readline().strip() == "ready"
    result = terminate_process_group(proc.pid, grace_s=0.5)
    assert (result.signalled_term, result.signalled_kill, result.reaped) == (True, True, True)
    assert result.returncode == -signal.SIGKILL


def test_terminate_process_group_kills_a_child_that_ignores_sigterm_after_its_leader_obeys():
    """M1: the leader exits on SIGTERM, its child ignores it -- the group is swept and the child killed."""
    # The child prints its ready line only once SIGTERM is ignored (85.3 delta review LOW-7: a fixed sleep raced it
    # under load); it inherits the leader's stdout, so the test reads the line itself.
    child = (
        "import os, signal, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "print('ready', os.getpid(), flush=True)\n"
        "time.sleep(60)\n"
    )
    leader = f"import subprocess, sys, time\nsubprocess.Popen([sys.executable, '-c', {child!r}])\ntime.sleep(60)\n"
    proc = subprocess.Popen([sys.executable, "-c", leader], start_new_session=True, stdout=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    ready, child_pid_text = proc.stdout.readline().split()
    assert ready == "ready"
    child_pid = int(child_pid_text)
    try:
        result = terminate_process_group(proc.pid, grace_s=2.0)
        assert result.reaped is True
        assert result.returncode == -signal.SIGTERM
        assert result.signalled_kill is True
        assert _gone_or_zombie(child_pid), "the SIGTERM-ignoring child outlived its leader"
    finally:
        try:
            os.kill(child_pid, signal.SIGKILL)
        except OSError:
            pass
