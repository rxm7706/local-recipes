---
title: "CAP-3's mechanism tier — the automated proof platform-ci-local gates on"
type: 'feature'
created: '2026-09-12'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '422491ee186400fc3ad1202343eedf0bd8d4fef8'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/stack.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-12-cap-1-2-4-5-in-effect-held-runs-publisher-identity-and-the-loop-home-reads-retire.md
  - src/platform/tests/test_front_door_queries_supervisor.py
  - src/platform/tests/test_chart_invariants.py
  - src/platform/deploy/overlays/ocp/core-overrides.yaml
warnings:
  - The DNS-egress selector fix in this spec's Code Map is grounded against a LIVE
    OpenShift 4.22.7 cluster measurement taken 2026-09-12 (`oc get pods -n openshift-dns
    --show-labels`) — namespace `openshift-dns`, pod label `dns.operator.openshift.io/daemonset-dns=default`.
    Do not substitute a guessed value; re-verify live if the target OpenShift version differs.
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-run-state-one-publisher`'s CAP-3 names two proof tiers for CAP-17's success
criterion: an automated mechanism tier gated in `platform-ci-local --test`, and one attended CRC
exercise recorded as a dated verification file. Neither exists yet. Separately, the OCP overlay's
`networkPolicy.dns` values (`src/platform/deploy/charts/platform/values.yaml:452-455`) hardcode
`kube-system`/`kube-dns` — vanilla Kubernetes' CoreDNS location, not OpenShift's. If NetworkPolicies
are ever actually applied on a real OpenShift cluster with this default, pods lose DNS resolution
the moment `networkPolicy.enabled` takes effect, silently breaking everything downstream of it
(including this very story's own future CRC exercise).

**Approach:** Add exactly the automated half of CAP-3 to `src/platform/tests/`: a publish→process-
exit→`/runs/`-requery test proving timing survives on a fresh DB connection, a socket guard on the
`/runs/` render path, and a chart invariant that no template across the whole platform chart
declares a `hostPath` volume. Fix the DNS-egress selector in `overlays/ocp/core-overrides.yaml` so
a real OpenShift cluster's CoreDNS stays reachable once `networkPolicy.enabled` is live. The
attended CRC exercise itself is explicitly out of scope — see Non-Goals.

## Boundaries & Constraints

**Always:**
- Follow `test_chart_invariants.py`'s own established discipline (Story 9.6): the hostPath
  assertion lives in a shared helper function, uses the existing `_render()` helper (never a new
  ad-hoc `subprocess.run` call), and gets a "guard removed" companion test feeding a synthetic
  dict containing a `hostPath` volume to prove the helper actually raises.
- The socket guard follows `test_openfeature_file_flags.py:242-254`'s exact pattern:
  `monkeypatch.setattr("socket.create_connection", _blocked)` (and `urllib.request.urlopen` if the
  render path could plausibly reach for it), where `_blocked` calls `pytest.fail`.
- The publish→exit→timing-survives test uses `django_pyforge.supervisor.complete_run` +
  `RunState.objects.create` exactly as `test_front_door_queries_supervisor.py`'s existing tests
  already do (same fixtures, same `@pytest.mark.django_db` style) — do not invent a second
  RunState-creation helper.
- The DNS-egress fix is a **values override in `overlays/ocp/core-overrides.yaml` only** — do not
  change the chart template's default (`values.yaml`'s `kube-system`/`kube-dns` default stays
  correct for vanilla K8s; only the OCP overlay changes).
- Record the incoming `src/platform/**` surface claim in
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md`
  before this story's `src/platform/**` edits land, per the cross-station surface-claim rule
  already used for Stories 33.4/33.12 — otherwise `spec-surface-check` reds the merge.

**Never:**
- Do not attempt the attended CRC exercise itself, write a `verification-<date>.md` file, or touch
  `spec-run-state-one-publisher/.memlog.md` beyond a plain landing note — the operator drives that
  exercise separately, by hand, after this story and Story 33.14 both land.
- Do not add a `networkPolicy.dns.namespace`/`podLabels` values key that isn't already there
  (`values.yaml:452-455` already defines this seam) — override it in the OCP overlay, don't
  re-template it.
- Do not touch `overlays/ocp/chart/` (the Route chart) — out of scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PUBLISH_EXIT_REQUERY | A `RunState` published and completed, then queried via a fresh DB connection | `completed_at`/`duration_ms` intact | N/A |
| SOCKET_DURING_RENDER | `/runs/` view rendered with `socket.create_connection` monkeypatched to fail the test | No socket call occurs; render succeeds | `pytest.fail` if the guard trips |
| HOSTPATH_ABSENT | Every template across `src/platform/deploy/charts/platform/templates/` rendered via `_render()` | No document contains a `hostPath` volume | Guard-removed companion: a synthetic dict with `hostPath` must raise |
| DNS_EGRESS_OCP | `overlays/ocp/core-overrides.yaml` applied with `networkPolicy.enabled: true` on a real OpenShift cluster | Egress policy's DNS rule matches `openshift-dns`/`dns.operator.openshift.io/daemonset-dns=default`, not `kube-system`/`kube-dns` | N/A (values-only fix, no runtime branch) |

</intent-contract>

## Code Map

- `src/platform/tests/test_front_door_queries_supervisor.py` — **CREATE** a new test function
  (mirroring `test_runs_board_lists_supervisor_rows`'s fixture style): publish a `RunState`,
  `complete_run` it, then re-query `/runs/` via `django.db.connections` after closing/reopening
  the connection (or `connection.close()` + a fresh query) to prove `completed_at`/`duration_ms`
  aren't an in-memory-only artifact.
- `src/platform/tests/test_openfeature_file_flags.py:242-254` — **READ ONLY**, the socket-guard
  pattern to copy for the new `/runs/`-render socket guard (create the new test in
  `test_front_door_queries_supervisor.py`, not this file — this file's own scope is flags).
- `src/platform/tests/test_chart_invariants.py` — **CREATE** `_assert_no_hostpath_volumes(docs)`
  helper (Story 9.6 shape) walking every rendered document's `spec.template.spec.volumes` (and
  `spec.volumes` for bare Pods) for a `hostPath` key; **CREATE** a test rendering the full core
  chart (`_render(_CORE_CHART, ...)`, same image-digest/`--set-file` scaffolding the existing tests
  already thread through `_helm`/`_render`) and asserting the helper passes; **CREATE** the
  "guard removed" companion feeding a synthetic dict containing a `hostPath` volume and asserting
  the helper raises.
- `src/platform/deploy/overlays/ocp/core-overrides.yaml` — **MODIFY**: add
  ```yaml
  networkPolicy:
    dns:
      namespace: openshift-dns
      podLabels:
        dns.operator.openshift.io/daemonset-dns: default
  ```
  (verified live against a running CRC 4.22.7 cluster 2026-09-12 — see this spec's own `warnings`).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` —
  **APPEND** the incoming `src/platform/**` surface claim before this story's platform edits land.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/.memlog.md` —
  **APPEND** a plain landing note on completion (mechanism tier only; the attended exercise stays
  open — do not word this as CAP-3 being closed).

## Tasks & Acceptance

**Execution:**
1. Add the publish→exit→timing-survives test to `test_front_door_queries_supervisor.py`.
2. Add the socket guard on the `/runs/` render path to the same file.
3. Add the `hostPath` chart invariant (helper + real test + guard-removed companion) to
   `test_chart_invariants.py`.
4. Add the `networkPolicy.dns` override to `overlays/ocp/core-overrides.yaml`.
5. Record the incoming surface claim on `spec-pyforge-unifying-strategy/.memlog.md`.
6. Append the plain landing note to `spec-run-state-one-publisher/.memlog.md`.

**Acceptance Criteria:**
- Given a published, completed `RunState`, when `/runs/` is re-queried on a fresh DB connection,
  then `completed_at` and `duration_ms` are present and correct.
- Given `socket.create_connection` monkeypatched to fail the test, when `/runs/` renders, then no
  socket call occurs.
- Given every template in the core chart rendered via `_render()`, when the new hostPath helper
  runs, then it finds zero `hostPath` volumes; given a synthetic dict containing one, then the
  helper raises.
- Given `overlays/ocp/core-overrides.yaml`'s new `networkPolicy.dns` values, when compared against
  a live OpenShift cluster's `openshift-dns` namespace pod labels, then they match exactly.
- Given `pixi run -e local-recipes platform-ci-local -- --test`, when it runs, then all three new
  proofs pass alongside the existing suite.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`

Additional checks (informal, not policy verify commands — kept out of the list above so
MRS-GATE-011 never refuses on a byte-mismatch, per this session's own recovered lesson from
Stories 33.4/33.12/49.8):
- `pixi run -e local-recipes platform-ci-local -- --test` — expect full PASS including the three
  new proofs
- `python scripts/spec_surface_reconcile.py -core` — expect clean

**Manual checks (if no CLI):**
- Confirm the new `networkPolicy.dns` override values byte-match a live OpenShift cluster's
  `oc get pods -n openshift-dns --show-labels` output before merging, if the target OpenShift
  version could plausibly differ from 4.22.7.

## Non-Goals

- The attended, egress-blocked CRC exercise itself — deploying with NetworkPolicies active,
  driving a real bmad-loop run, verifying egress-block + zero-hostPath + timing-survives-teardown
  on a live cluster, and writing the dated verification file. That happens separately, by the
  operator, after this story and Story 33.14 both land.
- Story 33.14's CAP-5 deployed-profile login work — unrelated capability, separate story.
- The `overlays/ocp/chart/` Route chart — untouched.
- Rewriting CAP-3's or CAP-17's `verified:` line in any SPEC.md — that rides the actual attended
  exercise's own memlog entry, not this story's mechanism-tier landing.

## Spec Change Log

## Review Triage Log

## Design Notes

This story exists because Story 33.12's own Non-Goals explicitly named CAP-3 as "NOT this story's
job — it stays attended, documentary, and separate." This story lands the one piece of CAP-3 that
genuinely isn't attended (the mechanism tier), clearing the way for the operator to run the actual
CRC exercise once this and Story 33.14 (CAP-5's deployed-profile login, needed for the exercise's
own "credential flow" step) are both in.

## Auto Run Result
