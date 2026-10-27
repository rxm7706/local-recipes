---
companion-of: SPEC-run-state-one-publisher
content: the technical shape the contract binds to — modules, host API, credential flow, proof tiers, sibling rewording
---

# Stack — how the contract is realized

Decisions of record are in `.memlog.md` (2026-09-12, operator-accepted). This companion holds the
mechanism the kernel deliberately keeps out of its intents.

## Marshal side (Story 33.4's surface)

| Module | Role |
|---|---|
| `pyforge/marshal/ports/publisher.py` | `RunPublisherPort` Protocol: `publish(record)`, `heartbeat(run_ref)`, `complete(run_ref, status, result)` |
| `pyforge/marshal/adapters/publisher_host.py` | **the one publisher module** — `pyforge.core.client.PyForgeStationClient(station="marshal")` carrying the assertion as Bearer; `pyforge.core.assertion.HostMintClient` mints from the referenced bearer inside the 300 s TTL; failures become journal findings, never loop stops (the best-effort shape of `django_pyforge/supervisor.py:377-434`) |
| `pyforge/marshal/core/publish.py` | pure record shaping incl. token-economy CAP-7 savings fields (AD-4: no I/O in `core/`) |
| `supervisor/__main__.py`, `dispatch_supervisor/__main__.py` | both call the adapter; AD-9 forbids only `cli` imports, and the network stack lives in `pyforge.core`, outside AD-65's scan |

A meta-test proves `adapters/publisher_host.py` is the only module importing `pyforge.core.client`
for publishing, and that no module under `pyforge-marshal/src` imports `django_pyforge`. An
in-process adapter behind the same port is permitted only if marshal ever runs inside the platform
image; today its pixi feature carries no Django and the image cannot run its git orchestration.

## Host side (Story 49.8's surface, `django_pyforge.supervisor`)

| Entry | Behaviour |
|---|---|
| `publish_held_run(station, assertion, payload)` | same verify, `enforce_run_bounds` (with a per-tool override for loop runs — the default `MAX_RUNNING_PER_SUB = 5` would refuse a fan-out wave), `RunState` + `McpHandle` creation as `publish_start:435-475`; `celery_task_id=""`; no enqueue; returns the handle |
| `heartbeat_run(handle)` | lookup, refuse expired/terminal, bump `heartbeat_at`, slide `expires_at = now + station_time_limit` |
| `complete_held_run(handle, status, result)` | via `complete_run` (terminal wins); a later heartbeat for a terminal row opens a new attempt row linked by `harness_run_id` |
| `sweep_lost_runs` | rows with empty `celery_task_id` are judged by heartbeat age only, reason `heartbeat_lost`; Celery inspect is never consulted for them |
| MCP tools | `publish_loop_run`, `heartbeat_loop_run`, `complete_loop_run` on `/stations/marshal/mcp` (`django-marshal/mcp_asgi.py`), so assertion verification, rate limiting and the `mcp_http` sidecar proxy apply unchanged |
| Payload | per story: `station` slug, story key, `phase` (bmad-loop's own, incl. `deferred` / `escalated` / `abandoned`), `commit_sha`, `run_id`, savings fields — what doctor's story-status source needs to leave the home directory |

## Credential flow (CAP-2, CAP-5)

1. `pyforge login` (device-code or PKCE-loopback; no story exists today — CAP-5 mints it) writes
   `PYFORGE_IDP_BEARER_FILE` (0600). Local profile: `python -m config.local_dev.mint <persona>`
   writes the same file; the JWKS is the dev file — byte-identical path, nothing skipped.
2. The publisher calls `POST /assertion/mint/` with that bearer and `station="marshal"`. The host
   verifies JWKS/iss/aud/exp (Story 40.1), checks `pyforge:station:marshal` (absent from the
   realm and `personas.py` today — CAP-5 adds it), signs RS256 with the host-held key.
3. The assertion is consumed once by `publish_loop_run`; the sidecar keeps only the subject-bound
   handle. Revocation: `pyforge steward revoke --sub` cancels the row and the next heartbeat gets a
   terminal answer (journaled `revoked`, AD-9); IdP role removal makes the next mint 403.
4. `core/egress.py` scrubs the bearer and assertion shapes; the bearer never enters env or journal.

## Proof tiers (CAP-3)

**Mechanism — `platform-ci-local --test`, gating.** Added to `src/platform/tests/`: publish → process
exit → `/runs/` re-query with `completed_at` / `duration_ms` intact on a fresh connection; a socket
guard on the render path (the CAP-13 pattern at `test_openfeature_file_flags.py:242-254`); a chart
invariant that no template declares a `hostPath` volume (absent from `test_chart_invariants.py`
today). Existing scrapes stay: `test_front_door_queries_supervisor.py:235`,
`test_supervisor_tables.py:205-238`.

**Criterion — one attended CRC exercise, documentary.** `helm upgrade` with Story 48.3's
`networkpolicy-default-deny.yaml` + `networkpolicy-egress.yaml` active (first live proof of the
envelope; its DNS selector targets `kube-system` / `kube-dns` while OCP uses `openshift-dns` — the
exercise resolves or breaks that deferral); drive a real bmad-loop story from the workstation via
the credential flow; watch it on `/runs/` through the Route; complete it; tear down the laptop
session; re-curl `/runs/`; `oc exec web -- curl https://pypi.org` must fail; `hostPath` count
across `oc get pods -o yaml` is 0. Record: `verification-<date>.md` in this spec folder, Story
12.7's shape (cluster, run id, commands without secrets, pass/fail table, "what is not claimed").

**`verified:` wording for Unifying CAP-17** (CAP-9's grammar; steward 49.8 owns the rewrite as an
explicit acceptance criterion — 49.5 and 49.6 never rewrote theirs):

> front-door `/runs/` from `RunState` + no home-dir literals live in
> `test_front_door_queries_supervisor.py:<lines>`; publish→exit→timing-survives + egress guard +
> no-hostPath invariant live in `<tests>:<lines>` (`platform-ci-local --test`); deployed
> egress-blocked exercise: attended CRC `<date>`, run `<run_id>` — live on `/runs/` via Route,
> timing present after workstation teardown, default-deny NetworkPolicy enforced, zero hostPath
> (record `<file>`) — documentary only, not an automated CI gate. Enterprise Managed OCP
> namespace: not exercised (Epic 51 target).

## The guard (CAP-4)

Non-test code only. Matches the `.bmad-loops` literal **and** `.bmad-loop/runs`, `state.json`,
`journal.jsonl`. Kind-aware: comments, docstrings and argparse help never trip it. Allow-list: the
publisher module and sites tagged `# CAP-4: loop-home FILE read — <what>` (steward
`upgrade.py:3222` hook-relay byte-compare, `upgrade.py:4025` prove-landed validate). The pattern to
copy for root resolution is `django_pyforge/assertion/client.py:120-166` `list_loop_homes`:
`BMAD_LOOP_HOME_ROOT` only, no `Path.home()` fallback, test-guarded.

## Sibling rewording (owed before 33.4 dispatches)

Through `spec-marshal-token-economy/.memlog.md` and marshal `epics.md`, verbatim:

- **Story 33.4 Surface:** "the single publisher module (`adapters/publisher_host.py`), reaching
  `django_pyforge.supervisor` through the host's `/stations/marshal/mcp` face".
- **Story 33.4 Then** and **token-economy CAP-18 success:** "`grep -r django_pyforge
  src/shared/packages/pyforge-marshal/src/` returns **nothing**, and a meta-test proves exactly one
  module imports `pyforge.core.client` for publishing".
- Token-economy `surface:` gains `adapters/publisher_host.py`, `ports/publisher.py`,
  `core/publish.py`.
- Steward 49.8 needs no wording change. Doctor's `sources/__init__.py:223` comment is reworded
  per 49.8's And-clause ("scheduled for retirement under Unifying CAP-17").
