---
title: "85.4: The fix turn's redaction never hangs the supervisor or hides what the fix needs"
type: 'fix'
created: '2026-10-04'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-3-the-fix-turn-is-safe-to-switch-on-in-dev-and-staging.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_verify_fix.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 85.3 landed as #1812 (ac992095d7) on 2026-10-04. Its post-landing delta review verified all 16 send-back fixes and found new defects, recorded in 85.3's Review Triage Log. The fix turn is ON in dev and staging, so the MEDIUM is live there.

- **MEDIUM (ReDoS):** `core/dispatch_verify_fix.py:45`, the quoted-value branch of `_SECRET_KEY_VALUE`, `(?:\\.|(?!(?P=vq)).)*`. A backslash matches both alternatives, so a secret-named key, `=` or `:`, an opening quote and a run of backslashes with no closing quote backtrack exponentially. Measured on `password="` plus N backslashes: N=32 takes 0.51 s, and N=1000 exceeds 20 s. The scrub runs in the supervisor thread on the full, untruncated output of every failed command (`dispatch_supervisor/__main__.py` around :2188, and `build_verify_fix_prompt`). A hang stops the heartbeat and strands the run.
- **LOW-1:** `_URL_CREDENTIALS` (`:32`) is quadratic on a long run with no separators: 20 KB takes 2 s and 40 KB takes 7.5 s. The rule predates 85.3, but 85.3 scrubs before truncating, so it now sees full outputs.
- **LOW-2:** the key rule eats a compiler location. `token_budget.py:42:5:` becomes `token_budget.py:***REDACTED***`, so the fix turn loses the line and column it needs.
- **LOW-3:** these credential shapes are not redacted: `--password hunter2` (a space-separated flag), `Authorization: token ghp_…`, a bare `ghp_…` / `github_pat_…` token, `postgres://:pw@host` (an empty user), and `Cookie: sessionid=…`.
- **LOW-4:** the journal heartbeat during the fix wait writes once per second, not at the tick rate. `wait_for_process` polls every 1 s and `_fix_turn_heartbeat` journals on each poll (`__main__.py:1321,1339`). AC5 of 85.3 and the comment at `__main__.py:136` both say tick rate.
- **LOW-6:** three wirings have no test, so their mutants survived:
  - X02: the default `/dev/null` stdin for a story launch;
  - X11: the `_FixTurnPublisherHeartbeat` wrapper applied in `_maybe_run_verify_fix_turn` (`__main__.py:1119`);
  - X12: the progress thread joined after stop (`__main__.py:2172`).
- **LOW-7:** `test_terminate_process_group_kills_a_child_that_ignores_sigterm_after_its_leader_obeys` (`src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py:1013`) sleeps 0.3 s and hopes the grandchild has set SIG_IGN by then. Under load it can fail.

**Approach:**
- Make the quoted-value branch linear: `(?:\\.|(?!(?P=vq))[^\\])*(?P=vq)`. The reviewer checked it is linear and that the current tests pass with it.
- Anchor the URL scheme with a lookbehind, `(?i)(?<![a-z0-9+.-])([a-z]…`.
- Drop `.` from the key character class. Treat `:` as a separator only when whitespace or a quote follows it.
- Add the LOW-3 shapes to the same rule set.
- Throttle the journal heartbeat to `_TICK_SECONDS`.
- Pin X02, X11 and X12 with tests.
- Make the SIGTERM test wait on a ready line the grandchild prints after it sets SIG_IGN.

Ledger key: `85-4-the-fix-turn-s-redaction-never-hangs-the-supervisor-or-hides-what-the-fix-needs`.
Type / Effort / Deps: fix / S / S-85.3.

### Living CAP citations

- spec-pyforge-marshal CAP-286 (FR-233), the fix turn. This is a defect of shipped behaviour, so it mints no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. The existing `pyforge.marshal.verify_fix_loop` is unchanged: ON in dev and staging, OFF in production.

## Acceptance Criteria

- Given a secret-named key, `=`, an opening quote and 100,000 backslashes with no closing quote When `scrub_fix_turn_exposure` runs Then it returns in under 1 s; a timing test pins it, and restoring the old quoted-value branch fails that test (mutation)
- Given a 100 KB run of URL-scheme characters with no separator When it is scrubbed Then it returns in under 1 s; a timing test pins it
- Given `token_budget.py:42:5: E501 line too long` When it is scrubbed Then it is unchanged, and every shape the 85.3 tests redact is still redacted
- Given `--password hunter2`, `Authorization: token ghp_x`, a bare `ghp_` / `github_pat_` token, `postgres://:pw@host` and `Cookie: sessionid=abc` When they are scrubbed Then each secret is redacted; a test pins each shape
- Given a fix turn that waits several ticks When the journal is read Then it carries at most one heartbeat per `_TICK_SECONDS`; a fake-clock test pins it, and the comment at `__main__.py:136` matches
- Given the story-launch stdin, the publisher-heartbeat wrapper and the progress-thread join When mutants X02, X11 and X12 are applied Then each fails a test
- Given a loaded machine When the SIGTERM-ignoring-grandchild test runs Then it waits on the grandchild's ready line, never a fixed sleep
- Given the flag off When dispatch handles a refusal Then behaviour is unchanged; `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` is green

## Boundaries & Constraints

**Always:**
- Keep one redaction rule set, in `core/dispatch_verify_fix.py`.
- Scrub before truncating, at both sites.
- When a value is ambiguous, prefer over-redacting it.
- Name every changed path in the governing spec's memlog.

**Never:**
- Never stop redacting a shape the 85.3 tests pin.
- Never move the scrub off the full output to buy speed.
- Never change the flag's environments.
- Accepted limitations, recorded and not fixed here:
  - a multi-word YAML value is redacted to its first word only;
  - `password: str` and `max_tokens: 4096` are still redacted, which errs in the safe direction.

</intent-contract>

## Binding

- Parent: Story 85.3 (#1812, ac992095d7) and its post-landing delta review.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (late night) entry.
- Epic: Epic 85, which reopens: the sync rolls `epic-85` from `done` to `in-progress` while this story is open, and back to `done` when it lands. The operator ruled on 2026-10-04 that a fix goes into its own epic and reopens it, never a new epic. The reopen passes `ledger-regression` through doctor Story 41.5, in the same PR.
- Ledger key: `85-4-the-fix-turn-s-redaction-never-hangs-the-supervisor-or-hides-what-the-fix-needs`.
- Ledger status at mint: `backlog`.
- Deps: S-85.3 (done).
- Minted 2026-10-04 at the operator's request ("chain it").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-marshal python -m pytest -q src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py` — expected: pass, including the two timing tests and the LOW-3 shape tests.

**Tests that carry the criteria (run by `pyforge-marshal-test` above):**
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py` — AC1: `test_an_unclosed_quote_before_100k_backslashes_scrubs_in_under_a_second` (both quote types; a SIGALRM deadline turns a backtracking regex into a failure, never a hang); AC2: `test_a_100kb_run_of_url_scheme_characters_scrubs_in_under_a_second`, and `test_every_redaction_rule_stays_linear_on_100kb_adversarial_input` for every other rule; AC3: `test_a_compiler_location_keeps_its_line_and_column`, `test_an_unclosed_quoted_value_never_takes_the_next_line`, with 85.3's `test_scrub_fix_turn_exposure_redacts_every_credential_shape` unchanged; AC4: `test_scrub_fix_turn_exposure_redacts_the_shapes_the_85_3_delta_review_found_leaking`, with `test_ordinary_output_that_only_looks_like_a_credential_is_kept`, `test_a_value_is_never_taken_from_the_next_line` and `test_the_scrub_removes_terminal_colour_codes` from the landing review; AC6 (X02): `test_the_story_launch_keeps_dev_null_as_the_sessions_stdin`; AC7: `test_terminate_process_group_kills_a_child_that_ignores_sigterm_after_its_leader_obeys` reads the grandchild's ready line.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py` — AC5: `test_the_fix_wait_journals_at_most_one_heartbeat_per_tick` (a 150 s wait on a fake clock journals 3 heartbeats); AC6 (X11): `test_the_fix_turn_wraps_the_publisher_heartbeat_in_its_throttle`; AC6 (X12): `test_the_reverification_returns_only_after_an_in_flight_progress_heartbeat_finishes`; AC8: the existing two-state flag tests.

## Review Triage Log

### 2026-10-04 — Build (hand-built in `land/pyforge-marshal-85-4`); ready for an independent review
- No review has run yet. The build is ready for an independent review against this spec.
- Where the build goes past the Approach's wording, and why:
  - The quoted-value branch is `(?:\\.|(?!(?P=vq))[^\\\n])*(?P=vq)`: the Approach's branch, with `\n` also excluded. 85.3's `.` never matched a newline, so a quoted value stayed on its line; with `[^\\]` an unclosed quote would redact every following line up to the next same quote, hiding what the fix needs. Same linearity (one way to match each character); `test_an_unclosed_quoted_value_never_takes_the_next_line` pins it, and the Approach's literal branch fails that test.
  - `.` leaves the key's lookbehind too, not only its character class, so `spring.datasource.password=` and `config.api_key = ` stay redacted (tests `dotted-key`, `dotted-attribute`). The `:` rule alone keeps `file.py:42:5:`; dropping `.` keeps `secrets_loader.py: line 42, col 5` (a jshint/ESLint-compact location), which the `:` rule alone would lose.
  - Two more quadratic shapes the delta review did not name were measured and fixed with the same rule set: a keyword-dense identifier run (`token` x 20,000 ran past a 5 s timeout in 85.3's scrub, and the new flag rule shared the shape) -- the secret identifier is now found by a lookahead and taken whole, possessively -- and a repeated `a://u:` run (8.4 s with the lookbehind alone) -- a URL password now stops at another `://`. Each is a case of `test_every_redaction_rule_stays_linear_on_100kb_adversarial_input`.
  - `Authorization:` is one rule for any scheme (Bearer, Basic, token, Negotiate, ...), replacing the two Bearer/Basic rules; a URL's user may be empty; `--flag value` is its own rule over the same secret words; `Cookie:` / `Set-Cookie:` redact to the end of the line; bare `gh[pousr]_` / `github_pat_` tokens are redacted.
- A second racy test, found by this build's coverage-gate run under load: `test_wrapped_launch_keeps_a_fallback_dir_cli_reachable` (`test_harness_bmadbuild.py`) read the session log as soon as it existed, but the launcher creates the log before the child runs, so a slow wrapper start read it empty. `_await_file` now takes `containing=` and waits for the expected text; both session-log readers pass it.
- Mutation (scratch copies, this branch's tests; the unmutated control passes): all 18 killed -- AC1 the 85.3 quoted-value branch restored, and the Approach's literal `[^\\]` branch; AC2 no URL lookbehind, a URL password crossing `://`; AC3 `.` back in the key, `:` before a digit as a separator, `.` kept in the lookbehind; the key rule without its lookahead (keyword-run timing); AC4 no flag rule, `Authorization` back to Bearer/Basic only, no Cookie rule, no GitHub token rule, a URL user required; AC5 a journal heartbeat on every poll; X02 the story launch inheriting stdin; X11 no `_FixTurnPublisherHeartbeat` wrapper; X12 the progress thread not joined.

### 2026-10-04 — Landing review (independent reviewer); verdict SEND BACK; fixed in `land/pyforge-marshal-85-4`
- verdicts: 6 findings -- medium 1, low 5, false 0. All fixed on the branch; none deferred. The flag is unchanged.
- findings:
  - `[medium]` `[fix]` Quoted keys carrying a `.` leaked again (`{"db.password": "hunter2"}`, `{'spring.datasource.password': 'x'}`, `"app.secret": "v"`, `"auth.token":"v"`, `"secrets.api_key" = "v"`, `"client.secret"="v"`), since the build's key class dropped `.` for quoted keys too. Fixed: a quoted key is its own branch, `_SECRET_QUOTED_KEY`, whose name may carry `.` (found by lookahead and taken whole, so still linear); a bare key still never carries one. Tests: the six `quoted-dotted-*` shapes.
  - `[low]` `[fix]` An unambiguous `:` no longer separated: `{"password":12345}`, `password:nospace`, `aws_secret_access_key:abc/def`, `GITHUB_TOKEN:ghp_x1`. Fixed: any `:` after a quoted key; after a bare key, a `:` that no digit or second `:` follows, so `bin/token:42:5:` is kept. Tests: `json-colon-number`, `bare-colon-no-space`, `bare-colon-slash-value`, `bare-colon-env`. Accepted, recorded: a bare `password:12345` is kept (the compiler-location rule wins).
  - `[low]` `[fix]` A colour code hid a URL (`\x1b[32mpostgres://admin:pw@db`): the code ends in a letter the scheme lookbehind refuses. Fixed: the scrub removes terminal control sequences (CSI, `\x1b[...m` and kin) first, which also uncovers a colour-prefixed flag or Cookie header; a scheme run may start with a digit (`1https://`). The build's `(?!://)` stop is gone, so a password containing `://` is redacted again: when no `@` follows the `:` before whitespace, the URL rule consumes the run unchanged, so no later scheme in it rescans the same characters (none of them can reach an `@`) -- linear without the stop. Tests: `ansi-url`, `ansi-flag`, `ansi-cookie`, `url-password-with-scheme`, `url-digit-before-scheme`, `test_the_scrub_removes_terminal_colour_codes`, and the timing cases `url-password-scheme-run`, `colour-code-run`.
  - `[low]` `[fix]` A value could come from the next line: whitespace around the separator crossed a newline, so ruff's `27 |     except TokenError:` lost the next line's gutter and pytest's `>` after `if token:` was redacted. Fixed: `[ \t]*` on both sides of the separator. Tests: `test_a_value_is_never_taken_from_the_next_line` (ruff full format, the pytest arrow, a bare key at a line end).
  - `[low]` `[fix]` `_GITHUB_TOKEN` redacted `ghp_import` (a real package). Fixed: `gh[pousr]_` needs 36 or more characters and `github_pat_` 20 or more, as `core/egress.py`. Test: `test_ordinary_output_that_only_looks_like_a_credential_is_kept`; the bare-token shapes now use real lengths.
  - `[low]` `[fix]` Five mutants survived. Pinned: R07 (Authorization `\S+` to `\w+`) by `authorization-jwt`; R08 (scheme word mandatory) by `authorization-no-scheme`; R09 (Cookie value to whitespace) by `cookie-second-pair`; R10 (the flag rule's `(?!-)` dropped) by `cli --no-token-check --verbose` kept; R11 (`gho_`/`ghu_`/`ghs_`/`ghr_` unpinned) by `bare-gho`, `bare-ghu`, `bare-ghs`, `bare-ghr`.
  - optional, `[fix]`: `{'authorization': 'Bearer x'}` and `"Authorization": "Bearer x"` leaked in both versions. Fixed: a quoted key named whole `authorization`, `proxy-authorization`, `cookie` or `set-cookie` is a credential key (never a substring, so `"tough-cookie"` and `"azure-mgmt-authorization"` are kept). Tests: `quoted-authorization-python`, `quoted-authorization-json`, `quoted-cookie-json`, and the substring case kept.
- Story 86.8 landed its own fix for the same `_await_file` race (wait for a non-empty file). The merge keeps one helper: this build's `containing=` wait, which now also waits for a non-empty file when no text is named.
- The fix-wait heartbeat test now pins the fake-clock times of the journal heartbeats (1000, 1060, 1120 s), so the throttle's boundary and its first beat are pinned too (mutants H01, H02).
- Probes: the reviewer's `probe_shapes.py`, `probe2.py`, `probe3.py`, `perf.py` (1 MB inputs: worst whole scrub 0.42 s; the slowest shapes scale linearly at 0.5/1/2 MB) and `fuzz_perf.py` (seeds 1-6, no suspect) were re-run against this build. Against 85.3 over the repo corpus, the build redacts less on 8 lines (all compiler locations, file names, or comments quoting them) and more on 78 (quoted credential headers, empty-user URLs, secret-named flags such as `--token-spend 42000` -- the same accepted direction as `max_tokens: 4096`).
- Mutation (scratch copies, this branch's tests; the unmutated control passes): 39 of 40 killed -- every earlier mutant re-expressed against this code, the reviewer's R07-R14 and H01-H05, and one per fix above (quoted key without `.`, quoted or bare `:` needing a space, `:` before a digit separating, value crossing a newline, no colour strip, the URL skip branch removed, the `://` stop restored, a letter-only scheme start, header names removed or matched as substrings, no GitHub minimum length). The survivor, R13 (`_SECRET_IDENTIFIER`'s `++` to `+`), is equivalent: the class is always followed by a character outside it, so it matches the same text, and it stays linear (measured at 0.5/1/2 MB); the possessive only states the intent.
