---
title: 'A ship records itself, end to end'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '9664763468c0bbf8a111838311f3777d0ef76933'
final_revision: '127cae963e'
---

<intent-contract>

## Intent

**Problem:** Story 13.4's webhook (`webhook.py`) and 13.5's scheduler (`scheduler.py`,
`herald scheduler run`) are both built and fully unit-tested, but neither has ever run as a
real, listening process. The webhook has no ASGI host, no `.github/workflows/*.yml`, and no
real secret; both modules' own docs explicitly defer verifying their unattended trigger to
this story ("mounting this module into a live ASGI host... [is] Story 13.6's job" --
`webhook.py`; "verified by manual/CLI inspection since no server exists yet to observe
end-to-end (Story 13.6's job)" -- `spec-13-5`). Today a real merge on any station still
produces nothing in Herald without an operator running a CLI command by hand.

**Approach:** Give `webhook.create_app` a minimal, real ASGI host (`daphne` -- already an
approved, pinned dependency in this workspace for exactly this purpose, via Steward's adopted
architecture), wire one new GitHub Actions workflow with three jobs (on-ship / on-pr-close /
scheduler-demo, the CI system + events spec-13-4 already decided) that start that host or run
the scheduler for real, derive payloads from the real triggering git event, and assert real
records land. This is a bounded, CI-contained demonstration proving the wiring works
unattended -- not a persistent public production deployment. The Dream explicitly forbids
inventing hosting, and Steward's own `steward deploy perimeter` tooling cannot yet target an
arbitrary (non-Django) ASGI app -- that gap is recorded as new deferred-work, not built here.

## Boundaries & Constraints

**Always:**
- **First AC, recorded here:** "demonstrated live" means a real, automated, GitHub
  Actions-triggered proof that runs the real ASGI app and the real scheduler CLI against a
  real triggering event and a real (CI-scratch) `.herald/herald.db` -- never a persistent,
  publicly-reachable, always-on deployment. Persistent hosting behind Steward's live perimeter
  stays explicitly out of Surface (see Never) and is tracked as new deferred-work.
- `src/pyforge/herald/webhook_host.py` (NEW): a stable, daphne-pointable `application` ASGI
  object built from `webhook.create_app(repo_root=..., secret=resolve_webhook_secret())`.
  Wraps every request in `asyncio.wait_for(..., timeout=120)` (comfortably above
  DW-FU-13-4-3's documented ~93s legitimate worst case) and a dedicated executor capped at 4
  workers (not the default `min(32, cpu+4)`) -- closes DW-FU-13-4-3.
- `webhook.py` (MODIFY): `verify_signature`/`create_app` fold an `X-Hub-Timestamp` header into
  the signed HMAC content and reject a signature whose timestamp is more than 5 minutes old --
  closes DW-FU-13-4 (today's body-only HMAC makes a captured request a forever-valid replay).
  Both handlers already compute `date`/`shipped_date` server-side, unaffected by this change.
- One new `.github/workflows/herald-live-demo.yml` with three jobs, each real and unattended:
  `on-ship` (`push: branches:[main]`), `on-pr-close` (`pull_request: types:[closed]`),
  `scheduler-demo` (`schedule:` weekly + `workflow_dispatch:` for all three, mirroring
  `dashboard.yml`'s combined-trigger style). Each starts `webhook_host:application` via daphne
  (or runs `herald scheduler run` directly) against a scratch, job-local `.herald/herald.db`.
- `on-ship` derives station+story from the real triggering commit using this repo's own
  already-established attribution convention (mirrors `pyforge.doctor.sources.fleet_scan`'s
  `_LOOP_DONE`/`_QUALIFIED_STORY` patterns: a `Merge bmad-loop/.../N-M-... into
  loop/pyforge-<station>` commit, or a `<station>: story N.N` subject prefix) -- never a new,
  invented parsing rule. A commit matching neither pattern is not a ship: the job recognizes
  this and makes no webhook call (clean no-op, exit 0), rather than fabricating a station.
  Unset numeric/list payload fields use the same defaults `handle_on_ship`/the CLI already use
  (`[]`, `0.0`, `0`, `0.0`, `""`); `unblock_narrative` may carry the real commit subject.
- `on-pr-close` derives `merged` from the real `github.event.pull_request.merged`. For this
  demonstration payload only, `gates_passed` is set equal to `merged` (a merge to `main`
  already required its checks to pass) -- a documented simplification of the DEMO payload,
  never a change to `handle_on_pr_close`'s own independent two-boolean gate.
- `scheduler-demo` seeds its scratch DB with one claim carrying a real, currently-live
  evidence URL, then runs `herald scheduler run --json` for real and asserts the JSON
  summary's shape plus exit 0 -- the unattended-trigger proof 13.5 deferred to this story.
- `pyproject.toml` gains `[project.optional-dependencies] webhook-host = ["daphne>=4.2.2,<5.0"]`
  -- byte-identical floor to the `daphne` pins already verified solvable in this workspace
  (Steward's `[dashboard]` extra; root `pixi.toml`'s wagtail/coderedcms pin). `pixi.toml`'s
  `[feature.pyforge-herald.dependencies]` mirrors it, per the established extra<->feature
  pin-sync convention Steward's own `dashboard` extra set. Regenerate + commit
  `environment.yaml` (`pixi.toml` changed -- this repo's own CLAUDE.md gate, ungated by any
  label).
- `deferred-work.md`: mark DW-FU-13-4 and DW-FU-13-4-3 addressed; update DW-FU-13-4-2's
  (concurrent-delivery claim-id race) reasoning -- still unreached, since every demo job
  delivers one request at a time, never concurrently; add one new entry naming the concrete
  gap this story's investigation found: `steward deploy perimeter`'s ASGI-application path is
  a hardcoded Django-project placeholder with no way to target an arbitrary ASGI callable,
  which is why persistent Steward-perimeter hosting isn't built here.
- `docs/cli-runbooks.md`, `docs/operator-guide.md`, `docs/automation-troubleshooting.md`:
  replace "not mounted anywhere" / "no server exists yet" language with the new demonstrated
  mechanism and its documented boundary (CI-proven; persistent hosting deferred).

**Block If:** none identified -- CI system/events (spec-13-4), the station-attribution
convention (this repo's existing dashboard generator), and the demonstration-vs-production
hosting boundary (the Dream's own "do not silently invent hosting" constraint plus this
story's own first AC above) are all already decided or resolved with direct evidence.

**Never:**
- Mount, deploy, or point anything at Steward's actual live perimeter (`steward deploy
  perimeter`, its rendered systemd unit, its TLS edge) -- fixing its hardcoded Django-only
  ASGI placeholder is Steward-side engineering outside this story's Surface.
- Add Django/Channels to `pyforge-herald`'s own dependencies, or change `webhook.py`'s shape
  away from a plain ASGI3 callable -- AD-8 still governs; only `webhook_host.py` and the new
  `webhook-host` extra know about daphne.
- Persist `.herald/herald.db` across CI runs, commit it, or claim the demo produces a durable,
  always-on public record -- each job's created record lives only for that job's lifetime.
- Fix DW-FU-13-4-2 (concurrent-delivery id race) or DW-FU-13-4-4 (`--shipped-date`
  validation) -- both remain genuinely unreached by this story's serial, one-request-at-a-time
  demo, or (for -4-4) unrelated to webhook mounting.
- Add `pytest-asyncio`/`anyio`-based scaffolding to the fast unit-test suite -- mirror 13.4's
  hand-built scope/receive/send pattern for non-socket tests; the one genuinely-live-socket
  test is opt-in only (mirrors this package's existing `live` pytest marker precedent) and
  uses `httpx2`, already a Herald dependency.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real push to main, recognizable commit | subject matches the bmad-loop-merge or `<station>: story N.N` pattern | `on-ship` job derives station+story, POSTs a signed payload to the live daphne host, 201, Progress record created | No error expected |
| Real push to main, unrecognized commit | ordinary docs/chore push, no pattern match | job recognizes no ship, skips the webhook call, exits 0 | No error -- explicit no-op |
| Real PR closed, merged | `github.event.pull_request.merged == true` | `on-pr-close` derives `gates_passed = merged`, POSTs, 201, draft Claim created | No error expected |
| Real PR closed, not merged | `merged == false` | handler's existing no-op contract: 202, no record | No error -- explicit no-op |
| Request exceeds the bounded timeout | a storage call hangs past 120s | host returns the same non-2xx the existing alert path returns | Logged, non-2xx, no indefinite hang |
| Replayed captured request, stale timestamp | request re-POSTed >5 min after its `X-Hub-Timestamp` | 401 -- rejected before the storage call | Rejected pre-storage |
| Scheduler demo | scratch DB seeded with one claim + real evidence URL | `herald scheduler run --json` on a real `schedule` trigger revalidates it, rewrites `progress.json`, exit 0 | No error expected |

</intent-contract>

## Code Map

- `src/pyforge/herald/webhook_host.py` -- NEW: daphne-pointable `application`, bounded
  timeout + dedicated executor wrapping `webhook.create_app`.
- `src/pyforge/herald/webhook.py` -- MODIFY: `verify_signature`/`create_app`/handlers gain
  the `X-Hub-Timestamp` HMAC-input + skew-window rejection.
- `pyproject.toml` -- MODIFY: new `webhook-host` optional-dependencies extra.
- `pixi.toml` -- MODIFY: `[feature.pyforge-herald.dependencies]` mirrors the extra;
  `environment.yaml` regenerated to match.
- `.github/workflows/herald-live-demo.yml` -- NEW: `on-ship` / `on-pr-close` /
  `scheduler-demo` jobs.
- `tests/test_webhook_host.py` -- NEW: timeout/executor wrapping, `application` construction
  (hand-built scope/receive/send, no new server deps).
- `tests/test_webhook.py` -- MODIFY: timestamp-signing + skew-window coverage.
- `tests/test_webhook_live_smoke.py` -- NEW: one `@pytest.mark.live`-style opt-in test (new
  marker mirroring pyproject.toml's existing `live` marker precedent) starting the real
  daphne host on a scratch port, POSTing via `httpx2`, asserting 201 -- skipped by default.
- `tests/test_bridge.py` -- MODIFY (expected, per 13.4/13.5 precedent): classify
  `webhook_host` in the bridge-core module sweep.
- `docs/cli-runbooks.md`, `docs/operator-guide.md`, `docs/automation-troubleshooting.md` --
  MODIFY: retire stale "not mounted"/"no server exists" language.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- MODIFY: close DW-FU-13-4/-3,
  update DW-FU-13-4-2, add the Steward-perimeter-hosting entry.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/herald/webhook.py` -- add `X-Hub-Timestamp` to the signed HMAC content + 5-minute skew rejection -- closes DW-FU-13-4 now that a real producer exists
- [x] `src/pyforge/herald/webhook_host.py` -- new module: `application` object, bounded timeout (120s) + capped executor (4 workers) -- closes DW-FU-13-4-3, gives daphne a stable import target
- [x] `pyproject.toml` -- add `webhook-host` extra (`daphne>=4.2.2,<5.0`) -- the demo's only new dependency, opt-in
- [x] `pixi.toml` -- mirror the extra in `[feature.pyforge-herald.dependencies]`; regenerate `environment.yaml` -- CLAUDE.md's ungated sync gate
- [x] `.github/workflows/herald-live-demo.yml` -- new workflow, three jobs (`on-ship`, `on-pr-close`, `scheduler-demo`) -- the actual live wiring this story exists to build
- [x] `tests/test_webhook.py` -- timestamp/skew-window regression coverage -- proves the HMAC change before trusting it
- [x] `tests/test_webhook_host.py` -- unit coverage for the new module -- proves timeout/executor behavior independent of a real socket
- [x] `tests/test_webhook_live_smoke.py` -- one opt-in live-socket test -- the one test that proves the ASGI app answers real HTTP, not just a synthetic scope/receive/send triple
- [x] `tests/test_bridge.py` -- classify `webhook_host` -- required by the existing bridge-core determinism sweep
- [x] `docs/cli-runbooks.md`, `docs/operator-guide.md`, `docs/automation-troubleshooting.md` -- replace stale "not mounted" language -- keeps operator docs truthful post-implementation
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- close DW-FU-13-4/-3, update DW-FU-13-4-2, add the Steward-perimeter-hosting entry -- keeps the ledger accurate

**Acceptance Criteria:**
- Given this story's own first AC (Boundaries, above), when "demonstrated live" is read, then it means a real CI-triggered proof against a scratch DB, not persistent production hosting -- recorded before any code is written, mirroring 13.1/13.4's own precedent.
- Given a real push to `main` whose commit matches the station-attribution convention, when `herald-live-demo.yml`'s `on-ship` job runs, then it POSTs a real signed request to a real listening `webhook_host:application` and a Progress record for that station exists in the job's scratch DB, with no human action.
- Given a real PR close event, when the `on-pr-close` job runs, then `merged`/`gates_passed` are derived from the real event and the same live-request path as `on-ship` is exercised.
- Given the weekly `schedule` trigger (or a manual `workflow_dispatch`), when the `scheduler-demo` job runs, then `herald scheduler run --json` executes unattended against seeded data and exits 0.
- Given a captured, previously-valid signed request replayed after 5 minutes, when `verify_signature` checks it, then it is rejected (401) before any storage call.
- Given the full test suite, when `pixi run -e pyforge-herald pyforge-herald-test` runs, then it stays green including the new non-live tests; the opt-in live-socket test is skipped by default and passes when explicitly enabled.

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 3, low 4)
- defer: 1: (high 0, medium 1, low 0)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` `webhook_host.py`'s "closes DW-FU-13-4-3" and `webhook.py`'s "closing DW-FU-13-4" claims overclaimed what the fixes actually achieve. Fixed: both docstrings and the deferred-work ledger's two `CLOSED by Story 13.6` notes reworded to "narrows" with the residual named explicitly (thread occupancy isn't freed on timeout; an in-window replay is still valid, mitigated only by storage-layer idempotency).
  - `[low]` `[patch]` `webhook_host.py`'s "never imports daphne" AD-8 boundary was asserted in prose only -- `test_bridge.py`'s existing denylists check different reaches (transport adapters, inference SDKs), neither would catch it. Fixed: new `_FORBIDDEN_HOST_FRAMEWORK_PACKAGES` set (`daphne`/`django`/`channels`/`asgiref`) + `test_bridge_core_never_names_a_host_framework_package`, parametrized across every bridge-core module.
  - `[medium]` `[patch]` The 5-minute HMAC skew window narrows DW-FU-13-4's forever-valid-replay hole but doesn't close it (a captured, <5-min-old request remains valid), and neither docstring said so. Fixed: `verify_signature`'s docstring and the ledger's `CLOSED` note now name the residual and the idempotency argument (`(station, date)` upsert key; `event_id`-derived deterministic claim id) that makes it low-impact rather than exploitable.
  - `[low]` `[patch]` The workflow's `matched = station is not None and story is not None` counted a whitespace-only `_QUALIFIED_STORY` prefix (which strips to `station=""`) as matched, turning the documented "no pattern match -> silent no-op" case into a red job (a 400 from the blank-station check). Fixed: `matched = bool(station) and bool(story)`.
  - `[medium]` `[patch]` `on-pr-close`'s `gates_passed := merged` simplification is justified by "a merge to main already required its checks to pass," but the job's `pull_request: types: [closed]` trigger wasn't scoped to `main`, so the justification didn't hold for PRs into other branches. Fixed: added `branches: [main]`.
  - `[low]` `[patch]` Both jobs' cleanup step killed `$!` (the `nohup pixi run ... daphne ...` wrapper's own pid), which may not be daphne's real pid depending on whether `pixi run` execs into its child -- a potential orphaned daphne process holding the port for the rest of the job. Fixed: added a port-matched `pkill -f` alongside the existing pid-file kill in both jobs' stop steps.
  - `[low]` `[patch]` `_resolve_repo_root`'s `if not value` accepts a whitespace-only `HERALD_REPO_ROOT` (a non-empty string is truthy), which would silently construct a literal space-named directory instead of raising the intended not-configured error. Fixed: `if not value or not value.strip()`, plus a regression test.
  - `[medium]` `[defer]` `webhook_host.py`'s bounded timeout stops the *caller* from waiting past 120s, but `Future.cancel()` cannot interrupt a handler thread that is already running -- a genuinely-hung handler keeps its worker occupied forever, and four such hangs would permanently exhaust the dedicated 4-worker executor. Currently inert (every demo job is one throwaway process per one request; persistent hosting is already out of Surface, see `DW-FU-13-6-1`) but real risk for any future persistent, multi-request deployment. Filed as `DW-FU-13-6-2`; both `webhook_host.py`'s module docstring and `DW-FU-13-4-3`'s ledger note point to it.
  - `[low]` `[reject]` A claim that `DW-FU-13-4`/`DW-FU-13-4-3` don't appear in any ledger the reviewer could find -- false; both exist in `_bmad-output/implementation-artifacts/deferred-work.md` (verified directly, `readlink -f` confirms the correct Tier-3 target). The reviewer's diff scope excluded this gitignored, symlink-backed file by construction, not a real gap.
  - `[low]` `[reject]` Hand-duplicated HMAC-signing test helpers across three test files -- each file tests a genuinely different layer (raw scope/receive/send, a fake ASGI app, a real HTTP client), matching this codebase's established preference (13.4/13.5) for explicit, non-abstracted test code over shared fixtures.
  - `[low]` `[reject]` A multi-station commit (`"mason + steward: story 1.1"`) only posts `on-ship` for the first credited station -- already reasoned and documented as a deliberate demo-scope choice in the workflow's own inline comment, not an oversight.
  - `[low]` `[reject]` The `webhook-host` pyproject extra's "opt-in" framing overstates the situation for this repo's own contributors (the pixi feature installs it unconditionally). Matches Steward's own `[dashboard]` extra precedent's wording verbatim -- an established convention, not a new problem.
  - `[low]` `[reject]` The one live-socket test never runs automatically before a merge to `main`. True, but matches this repo's own deliberate, already-existing policy (`test-linux.yml`'s explicit "automatic triggers disabled to preserve GitHub Actions quota" comment) of manual/local test verification before merge, not a gap this story introduces.
  - `[low]` `[reject]` A theoretical `response_started=True` mid-timeout edge case in the host's timeout handler -- already reasoned and documented as unreachable by construction in `webhook_host.py`'s own docstring (the only blocking point inside `inner` is the thread-dispatched handler call, which happens after every response that could set `response_started` early).
  - `[low]` `[reject]` A non-`http`/`lifespan` ASGI scope (e.g. a websocket) bypasses the timeout/executor wrapping -- inert, since `webhook.py`'s own routing already 404s/405s any such scope before ever reaching thread dispatch.

## Design Notes

**Why daphne, not uvicorn/hypercorn.** `daphne>=4.2.2,<5.0` is already a verified-solvable,
approved dependency in this workspace specifically because Steward's adopted
`spec-secure-live-dashboards` architecture names it as the ASGI termination server Herald's
eventual production mount will use. Reusing it here (rather than a different, throwaway demo
server) means the demonstration host and any future real host share the same server software.

**Why the workflow doesn't call `steward deploy perimeter`.** That subcommand only *renders*
systemd/nginx text manifests pointed at a hardcoded `myproject.asgi:application` Django
placeholder -- there is no flag to target an arbitrary ASGI callable, and it requires real
infra (systemd, a TLS cert, a `--trusted-address`) this environment cannot provision. Making
it support an arbitrary target is real, cross-station engineering outside Herald's Surface;
recorded as new deferred-work rather than attempted here.

**This PR touches files outside `recipes/`** (workflows, `pyproject.toml`, `pixi.toml`,
`src/`, `docs/`) -- per this repo's own CLAUDE.md PR-gate rule, it needs the `maintenance`
label at open/update time, and the `pixi.toml` change means `environment.yaml` must already
be regenerated and committed (that gate is ungated by the label).

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: full suite green, including
  new `test_webhook_host.py` and the timestamp coverage in `test_webhook.py`; the new live
  marker test skipped by default.
- `HERALD_LIVE_WEBHOOK=1 pixi run -e pyforge-herald pytest tests/test_webhook_live_smoke.py` --
  expected: the opt-in live-socket test passes against a real local daphne process.
- `pixi run --frozen -e pyforge-herald herald scheduler run --repo-root /tmp/herald-demo --json`
  -- expected: valid JSON summary, exit 0 (existing 13.5 command, re-verified unchanged).
- `pixi project export conda-environment -e build > environment.yaml` -- expected: no diff
  beyond the new `daphne` line; commit it alongside `pixi.toml`.

**Manual checks (if no CLI):**
- Trigger `herald-live-demo.yml` via `workflow_dispatch` once on a scratch branch/PR before
  relying on the real `push`/`pull_request`/`schedule` triggers, and inspect the job logs for
  the printed created-record id.

## Auto Run Result

Status: done

**Summary.** Story 13.6's implementation and review pass (commit `1c3b31cb47`) landed
correctly, but the bmad-loop's own deterministic verify gate (`python
scripts/spec_surface_reconcile.py`, S-13.7) failed afterward: the story's own `pixi.toml`
edit (the new `daphne` pin backing the `webhook-host` extra) falls inside
`pyforge-marshal/spec-pyforge-core`'s declared surface (`pixi.toml` -- "the new workspace
member + its per-station dep edges"), an unrelated cross-station Spec this story's own
intent-contract never mentions and had no reason to. That Spec's `.memlog.md` had not moved
to acknowledge the edit, so the drift was gating (`[drift]`, not the non-gating
`[drift-presumed]` a moved-but-silent memlog would produce). This is a repeat of an
established, already-documented class of repair in this repo (matches the
`spec-surface-drift-reconciliation` convention multiple other stations' specs already carry
in their own memlogs) -- not a defect in Story 13.6's own code, and not something its
intent-contract could have anticipated since `spec-pyforge-core`'s surface is owned by a
different project.

**Repair performed (this pass).** No code, test, workflow, or doc change -- the
intent-contract's Surface was already fully and correctly implemented. Fixed by:
1. Appended a `(change) RECONCILED BY NAME` entry to
   `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`
   naming the exact `pixi.toml` edit (the `daphne` line, line ~1657) and confirming it has no
   effect on `spec-pyforge-core`'s own contract (CAP-1..7, the `pyforge-core` leaf package),
   per the memlog's own established entry convention for unrelated `pixi.toml` edits.
2. Re-stamped the baseline for that one spec only:
   `python scripts/spec_surface_check.py --write-baseline --spec pyforge-marshal/spec-pyforge-core`.
3. Verified `pixi project export conda-environment -e build` is still byte-identical to the
   committed `environment.yaml` (`pyforge-herald` is not a member of the `build`
   environment's feature set, so the new dependency does not reach it) -- confirms the
   story's own Verification section claim held and needed no re-export.

**Files changed (this pass):**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md` -- new reconciliation entry + `updated:` bump.
- `scripts/.spec-surface-baseline.json` -- `pyforge-marshal/spec-pyforge-core`'s `pixi.toml` file hash and `memlog` hash re-stamped; no other spec's entry touched.

**Review findings breakdown:** none -- this pass is a deterministic-verification repair, not
a code review pass; Story 13.6's own review pass (see the 2026-08-13 Review Triage Log entry
above) already ran and is unchanged.

**Follow-up review recommendation:** false -- no code changed, only cross-spec governance
bookkeeping.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- was `rc=1` (`[drift]
  pyforge-marshal/spec-pyforge-core: pixi.toml changed but the spec's memlog did not move`);
  now `OK: every tracked file governed or allowlisted; no drift.` (`rc=0`).
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- 1036 passed, 4 skipped
  (unaffected by this pass; re-run to confirm the repair touched nothing herald-owned).
- `git status` inspected before and after; the repair commit (`127cae963e`) touches only the
  two files listed above.

**Residual risks:** none introduced by this pass. Pre-existing, unrelated `drift-presumed`
(non-gating) warnings for `pyforge-atlas/spec-pyforge-atlas`,
`pyforge-scribe/spec-pyforge-scribe`, and `pyforge-warden/spec-pyforge-warden` (each own
package's `pixi.toml`, moved memlog, path not named verbatim) were observed during
investigation -- pre-existing, non-gating, and out of this story's Surface; not touched.

