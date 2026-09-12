---
title: 'CAP-1/2/4/5 in effect — held runs, publisher identity, and the loop-home reads retire'
type: 'feature'
created: '2026-09-12'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '0226e924070cb352384b17585ecc38a1bf21c0e5'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/brownfield.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/stack.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-4-cap-18-one-publisher-run-state-and-savings-telemetry-reach-the-supervisor.md
  - src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
  - src/shared/packages/django-pyforge/src/django_pyforge/roles.py
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/views.py
  - src/platform/config/local_dev/personas.py
warnings:
  - Effort L bundles four capabilities across two packages (pyforge-marshal + django-pyforge)
    plus a realm config file. If the full scope cannot land in one dispatch, land CAP-1 + CAP-4
    (the mechanical core -- held-run lifecycle + guard + consumer re-pointing) first and document
    any deferred CAP-2/CAP-5 sub-scope in this spec's own Review Triage Log AND
    spec-run-state-one-publisher/.memlog.md, per that Spec's "Realized on effect, never on ledger"
    constraint. Never mark this story `done` while a capability's own success criterion is unmet.
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 33.4 landed the mechanical publisher (`adapters/publisher_host.py`, zero
`django_pyforge` imports, best-effort publish/heartbeat/complete) but every consumer of run truth
still reads a home directory, the host cannot yet hold a run it does not own, and the publisher
carries no verified identity. Concretely: `django_pyforge.supervisor.publish_start` only ever
wraps a Celery task it enqueues itself (there is no held-row shape for a run the platform did not
start); `roles.py`'s `pyforge:station:marshal` claim has no realm role or dev persona to grant it
(`platform-realm.json` carries zero `pyforge:station:*` entries today, verified 2026-09-12); no
`pyforge login` command exists; and `cli/init.py:_loop_home_root`, doctor's
`sources/marshal.py` story-status gather, and `cli/status.py`'s `.bmad-loop/runs/` scrapes still
read `~/.bmad-loops` for run truth. CAP-17's own criterion ("marshal and doctor no longer read
`~/.bmad-loops`" for run state) is therefore still unmet.

**Approach:** Add a held-run shape to the host supervisor store (`celery_task_id=""`, judged by
heartbeat age only, never Celery inspect) reachable through the three MCP tools
`publish_loop_run` / `heartbeat_loop_run` / `complete_loop_run` that Story 33.4's `HostPublisher`
already calls; carry the publisher's assertion from a verified IdP bearer (extend `mint`'s
existing `station_granted` check to a live `pyforge:station:marshal` role — add it to the realm
config and to one new local-dev persona); wrap the existing `python -m config.local_dev.mint`
local-profile path in a new `pyforge login` CLI verb that never prints or logs the bearer value;
add a kind-aware guard that reds a new run-state read outside the publisher and tagged loop-home
*file* sites; and re-point `cli/init.py`'s consumer-facing run listing plus doctor's story-status
gather at the published plane, leaving `cli/status.py`'s `.bmad-loop/runs/` reads as tagged
loop-home-file access (worktree/journal scraping, not run-state truth) until this story's own
verification shows a published-plane equivalent exists.

## Boundaries & Constraints

**Always:**
- A held run's `celery_task_id` is empty string, never null and never a real Celery id; `sweep_lost_runs`
  judges it by `heartbeat_at` age alone and never calls the Celery inspector for it (mirrors the
  existing `celery_task_id` row already judged that way for enqueue-failed rows).
- `enforce_run_bounds` still runs for a held-run publish, but a per-tool override on
  `publish_loop_run` raises the effective `MAX_RUNNING_PER_SUB` so one fan-out dispatch wave under
  one operator subject is never refused by the platform's own default-5 ceiling (`stack.md` names
  this explicitly; do not raise the *global* default, only the loop-tool path).
- A terminal held row is never rewritten: a heartbeat that arrives for an already-terminal handle
  opens a NEW attempt row linked by `harness_run_id`, exactly as `complete_run`'s own docstring
  already states for the Celery-backed path.
- The assertion the publisher presents is minted by the host from the operator's verified IdP
  bearer via the existing `/assertion/mint/` view and `station_granted` check — do not add a
  second mint path or a bearer format the egress scrubber (`core/egress.py`) does not already
  recognize.
- `pyforge login` writes `PYFORGE_IDP_BEARER_FILE` with mode 0600 and prints nothing but the
  file path on success; wrap the existing `config.local_dev.mint` local-profile path for the local
  profile — do not build a new device-code/PKCE flow against a real IdP in this story if the local
  wrapper alone lets CAP-5's local-profile success criterion pass (deployed-profile mint against a
  real IdP may be deferred; say so explicitly in the Review Triage Log if deferred).
- The CAP-4 guard is non-test code only, matches the `.bmad-loops` literal AND `.bmad-loop/runs`,
  `state.json`, `journal.jsonl`, never trips on a comment/docstring/argparse help string, and
  allow-lists only `adapters/publisher_host.py` plus sites carrying a `# CAP-4: loop-home FILE
  read -- <what>` tag.
- Record the incoming `django-pyforge/**` and realm surface claim in
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`
  or the relevant steward spec's memlog BEFORE this story's `django-pyforge/**` edits land, per
  the cross-station surface-claim rule already used for Story 33.4 — otherwise `spec-surface-check`
  reds the merge.

**Never:**
- Do not wrap an external bmad-loop run in a Celery task to make it publishable (Constraint:
  "External runs stay external").
- Do not add a second `run_state` write path, a second table, or a station-private copy of the
  fact (Constraint: "Single writer, one store").
- Do not implement CAP-3's deployed, egress-blocked CRC proof exercise in this story — it stays
  attended, documentary, and separate (this story's own success is the mechanism, not the exercise).
- Do not move bmad-loop's own `state.json`, `journal.jsonl`, or worktrees off the loop home —
  `BMAD_LOOP_HOME_ROOT` remains their override; only *run-state reads* retire.
- Do not touch `hub:CAP-3` (the Track on `spec-intelligence-hub`) beyond what this story already
  feeds it by existing.
- Do not implement token-economy CAP-7's per-layer savings getters — that landed under Story 33.4.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HELD_PUBLISH | `publish_loop_run` called with a verified assertion, no Celery task | `RunState` row created with `celery_task_id=""`, status RUNNING; `McpHandle` returned | Missing/invalid assertion refuses with no row created |
| HELD_HEARTBEAT | Heartbeat for a live held handle within the time bound | `heartbeat_at` bumped, `expires_at` slides | Expired or unknown handle refuses |
| HELD_LOST | Held row's `heartbeat_at` ages past the bound | `sweep_lost_runs` marks it lost, reason `heartbeat_lost` (never `worker_lost`, never Celery inspect) | N/A |
| HELD_TERMINAL_REWRITE | Heartbeat arrives for an already-terminal held handle | A NEW attempt row opens, linked by `harness_run_id`; the terminal row is untouched | N/A |
| FANOUT_WAVE | One operator subject publishes a dispatch wave of >5 held runs | Not refused by `MAX_RUNNING_PER_SUB`'s default (loop-tool override applies) | A non-loop tool still enforces the unmodified default |
| MINT_NO_ROLE | Bearer verifies but the subject lacks `pyforge:station:marshal` | `/assertion/mint/` returns 403 | Publisher reports a finding, never stops the loop |
| MINT_ROLE_REMOVED | Role removed at the IdP after a prior successful mint | Next mint attempt 403 | Held run's next heartbeat still succeeds on the still-valid handle until it expires |
| LOGIN_LOCAL | `pyforge login` invoked with local-dev persona selection | Bearer file written 0600; command prints only the file path | Persona unknown → non-zero exit, no file written |
| GUARD_TRIP | A new non-test source line reads `~/.bmad-loops` or a run-state filename, untagged | CAP-4 guard reds it | A tagged loop-home-FILE site or a comment/docstring never trips it |
| CONSUMER_REPOINT | `cli/init.py` / doctor's story-status gather query the published plane | Same information surfaces without touching the home directory | Published plane unreachable → same best-effort/WARN degrade doctor already uses for git-unusable |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py` — **MODIFY**: add
  `publish_held_run(station, assertion, payload)` beside `publish_start` (same assertion-verify +
  `enforce_run_bounds` shape, `celery_task_id=""`, no `enqueue_supervised_run` call); add
  `heartbeat_held_run(handle)` and reuse `complete_run` for `complete_held_run`; extend
  `sweep_lost_runs` (already iterates rows by `celery_task_id` — verify its query already includes
  empty-string rows, widen if not) to judge held rows by heartbeat age only; add the per-tool
  `MAX_RUNNING_PER_SUB` override for the loop-publish tool in `enforce_run_bounds`.
- `src/shared/packages/django-pyforge/src/django_pyforge/mcp` (or wherever the station's MCP tool
  registrations for `/stations/marshal/mcp` live — locate via
  `grep -rn "publish_loop_run\|register_runner" src/shared/packages/django-pyforge/`) — **CREATE/MODIFY**
  the three tool entrypoints `publish_loop_run`, `heartbeat_loop_run`, `complete_loop_run` that
  Story 33.4's `HostPublisher` already calls by name (currently unimplemented — 33.4's own
  Residual Risk note: "Host MCP tools land with steward Story 49.8").
- `src/shared/packages/django-pyforge/src/django_pyforge/roles.py` — **VERIFY ONLY**:
  `pyforge:station:marshal` already parses via `STATION_TOKENS` (marshal is already a member);
  no code change expected here — the gap is realm/persona config, not the parser.
- `src/platform/compose/keycloak/realms/platform-realm.json` — **MODIFY**: add a
  `pyforge:station:marshal` group/role entry (there are zero `pyforge:station:*` entries in this
  file today — verified 2026-09-12; add only the `marshal` one this story needs, do not backfill
  every station).
- `src/platform/config/local_dev/personas.py` — **MODIFY**: add one new `Persona` (e.g.
  `key="marshal-operator"`) whose `groups` resolves to the literal `"pyforge:station:marshal"`
  claim value via `resolve_groups`/`build_claims`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/` — **CREATE** a `login.py` verb
  (registered in `main.py`'s subparser tree, same pattern as `add_homes_subparser` in `init.py`)
  wrapping `python -m config.local_dev.mint <persona>` for the local profile; writes
  `PYFORGE_IDP_BEARER_FILE` at 0600.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py:331` (`_loop_home_root`) and
  its callers that surface run listings to the operator — **MODIFY** to read the published plane
  first, falling back only for genuinely loop-home *file* concerns (worktree discovery, marker
  checks) which are out of scope for retirement (Constraint: "The loop home stays").
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py:544` (the
  `Path.home() / ".bmad-loops"` fallback in the story-status gather) — **MODIFY** to read
  published run/story-phase data when available, keeping the existing git-based routes and the
  WARN-on-cannot-evaluate degrade as fallback, not replacement, until the published payload proves
  reliable across a full sprint cycle.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py:665-780,917-1063` —
  **TAG, DO NOT MOVE**: these `.bmad-loop/runs/` reads are loop-home *file* access (recovering a
  `harness_run_id`, reading `changes.patch` for a failed dispatch) rather than run-state truth;
  add the `# CAP-4: loop-home FILE read -- <what>` tag per site so the new guard allow-lists them
  without silently exempting a future run-state read added nearby.
- `src/shared/packages/pyforge-marshal/**/tests/` — **CREATE**: `test_held_run_lifecycle.py`
  (marshal-side, against a fake/injected port) and a guard test (`test_no_loop_home_run_state_read.py`
  or similar) enforcing the CAP-4 matcher over `src/`.
- `src/shared/packages/django-pyforge/**/tests/` — **CREATE/MODIFY**: held-run lifecycle tests
  (publish/heartbeat/lost/terminal-rewrite), the `MAX_RUNNING_PER_SUB` per-tool override test, and
  a `station_granted("marshal", ...)` 200/403 test against the new persona.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/.memlog.md` —
  **APPEND** the landing/deferral record on completion (per its own "Realized on effect, never on
  ledger" constraint — do not just flip the ledger row).

## Tasks & Acceptance

**Execution:**
1. Locate the current MCP tool registration surface for `/stations/marshal/mcp` (`register_runner`/
   `lookup_runner` in `supervisor.py`, plus wherever the station's tool table is assembled) and add
   `publish_loop_run` / `heartbeat_loop_run` / `complete_loop_run` calling the new held-run
   functions below.
2. `supervisor.py`: add `publish_held_run`, `heartbeat_held_run`, and reuse `complete_run` for
   `complete_held_run`; widen `sweep_lost_runs`'s query/judgment so empty-`celery_task_id` rows are
   judged by heartbeat age only; add the per-tool bound override.
3. `platform-realm.json` + `personas.py`: add the `pyforge:station:marshal` role/group and one
   local-dev persona carrying it.
4. `cli/login.py` (new) + `main.py` wiring: `pyforge login <persona>` for the local profile.
5. Author the CAP-4 guard (a script or test under marshal, or a shared doctor/CI check — pick the
   home consistent with existing kind-aware guards such as `test_no_module_outside_dashboard_imports_dashboard_django_or_channels`)
   and tag the `cli/status.py` loop-home-file sites so the guard passes clean.
6. Re-point `cli/init.py`'s run listing and doctor's `sources/marshal.py:544` story-status gather
   at the published plane, keeping existing fallbacks for the cannot-evaluate case.
7. Record the incoming `django-pyforge/**`/realm surface claim in steward's own memlog before
   committing the `django-pyforge/**` edits.
8. Append the landing (or documented partial-landing) record to
   `spec-run-state-one-publisher/.memlog.md`.

**Acceptance Criteria:**
- Given a verified assertion and no Celery task, when `publish_loop_run` is called, then a
  `RunState` row is created with `celery_task_id=""` and a handle is returned.
- Given a held run whose heartbeat ages past the station's time bound, when `sweep_lost_runs`
  runs, then it is marked lost with reason `heartbeat_lost` without consulting the Celery inspector.
- Given a terminal held row, when a later heartbeat arrives for its handle, then a new attempt row
  opens linked by `harness_run_id` and the terminal row is unchanged.
- Given one operator subject publishing a fan-out wave of more than 5 held runs, when
  `enforce_run_bounds` runs for the loop-publish tool, then none are refused by the unmodified
  default-5 ceiling.
- Given a bearer for a subject holding `pyforge:station:marshal`, when `/assertion/mint/` is
  called with `station="marshal"`, then it returns 200; given the role removed, then it returns 403.
- Given `pyforge login <persona>` on the local profile, when it completes, then
  `PYFORGE_IDP_BEARER_FILE` exists at mode 0600 and no bearer value appears in stdout, stderr, or
  any journal line.
- Given the CAP-4 guard, when run over `src/`, then it reds a new untagged run-state read and
  passes clean against the tagged `cli/status.py` sites and the publisher module itself.
- Given `cli/init.py`'s run listing and doctor's story-status gather, when the published plane has
  data for a run, then they surface it without reading `~/.bmad-loops`.
- Given this story's own scope could not fully close CAP-2 or CAP-5's deployed-profile half, when
  the Auto Run Result is written, then the deferral is named explicitly there and in
  `spec-run-state-one-publisher/.memlog.md` — never silently marked done.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`

Additional checks (informal, not policy verify commands — kept out of the list above so
MRS-GATE-011 never refuses on a byte-mismatch, per Story 33.4's own recovered lesson):
- `pixi run -e pyforge-steward pyforge-steward-test` — expect green (django-pyforge held-run +
  role changes live under steward's own test env)
- `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` — expect empty (unchanged
  invariant from Story 33.4)
- `python scripts/spec_surface_reconcile.py -core` — expect clean

**Manual checks (if no CLI):**
- Confirm `platform-realm.json`'s new `pyforge:station:marshal` entry is the only new
  `pyforge:station:*` entry added (no unrelated station backfill).

## Non-Goals

- CAP-3's deployed, egress-blocked CRC proof exercise — attended, documentary, tracked separately;
  not this story's job.
- A production device-code/PKCE login flow against a real external IdP — the local-profile wrapper
  around `config.local_dev.mint` satisfies CAP-5's local-profile criterion; the deployed-profile
  mint path may be deferred with an explicit note if it cannot land in this dispatch.
- Backfilling `pyforge:station:*` realm roles for every other station — only `marshal`'s.
- Moving bmad-loop's own `state.json`/`journal.jsonl`/worktrees off the loop home.
- Steward Story 49.8's own doctor-comment reword and its live CAP-17 verification — that story
  dispatches after this one lands, reading this story's actual artifact.
- Token-economy CAP-7's savings getters — Story 33.4's own scope, already landed.

## Spec Change Log

## Review Triage Log

## Design Notes

This story is the direct continuation of Story 33.4 (marshal Epic 33), which deliberately landed
only the mechanical publisher core (token-economy CAP-18/CAP-7) and named CAP-1/CAP-2/CAP-4/CAP-5
as its own known deferral — see `spec-33-4-...md`'s Residual Risks and
`spec-run-state-one-publisher/.memlog.md`'s 2026-09-12 partial-landing entry. Steward Story 49.8
stays `backlog` (not `blocked`) on this story's completion, per the epics.md Story 33.12 block's
own cross-station note, and should not be dispatched until this story's CAP-1/CAP-4 core (at
minimum) is live and verified.

## Auto Run Result
