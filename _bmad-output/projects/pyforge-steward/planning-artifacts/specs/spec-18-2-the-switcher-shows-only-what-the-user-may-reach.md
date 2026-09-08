---
title: The switcher shows only what the user may reach
type: feature
created: '2026-08-24'
status: done
updated: '2026-08-24'
context:
  - src/shared/packages/django-pyforge/src/django_pyforge/context_processors.py
  - src/shared/packages/django-pyforge/src/django_pyforge/discovery.py
  - src/platform/tests/test_django_pyforge_chrome.py
warnings: []
baseline_revision: e96b852227b36bb28cbc62cd44dd5071057081fe
review_loop_iteration: 0
followup_review_recommended: true
deferred:
  - summary: >-
      Live IdP revoke on the next request (canopy:FR-31 / canopy:AD-15 strong
      reading) still waits on a per-request token, not this session snapshot.
    evidence: |-
      OIDC login writes group-claim names into session idp_token_roles until
      the next successful pre_social_login. 18.3 JWT re-verify is out of
      scope. Epic 21 / canopy:FR-31 owns next-request revoke.
    location: >-
      src/platform/config/authorization/adapters.py
    severity: medium
  - summary: >-
      Local staff/reader personas do not include station_name roles, so a
      real login lists no stations until IdP groups contain those names.
    evidence: |-
      Adapter stores CLAIMS_CONTRACT group-claim values (e.g. platform-staff).
      Switcher matches portal.station_name (warden, chrome-probe).
    location: >-
      src/platform/config/local_dev/personas.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** The chrome switcher lists every registered portal. An operator without a station's IdP role still sees a door they cannot open (canopy:FR-3, canopy:AD-15).

**Approach:** Filter switcher entries from roles on the current request's token. Station views still refuse a direct URL. Do not treat Django groups or other durable local grants as the switcher's authority.

## Boundaries & Constraints

**Always:** Land in existing `django-pyforge` chrome. Discovery stays `apps.get_app_configs()`. Roles are re-read on each request from the token (request-scoped `idp_roles` and/or session key populated from this request's IdP claims). The switcher is not enforcement. Cite canopy:AD-15. Write specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only.

**Block If:** Implementation would require minting or verifying RS256 service JWTs, or renaming `compliance_face`.

**Never:** Story 18.3 JWT client (golden vector, HMAC, `aud=mcp:`). Story 19.1 warden rename. A competing verdict. `import pyforge` / `pyforge.*` under `src/platform/`. `scripts/bmad-switch`. `bmad-loop`. Other stations' ledgers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Missing station role | Token roles omit `chrome-probe`; both portals installed | Switcher HTML has no `chrome-probe` link | No error |
| Direct URL still refused | Same user GETs `/stations/chrome-probe/` | Station responds 403; switcher code is not the gate | 403 Forbidden |
| Token not Django groups | User.groups includes `chrome-probe`; token roles are only `warden` | Switcher shows `warden`, not `chrome-probe` | Groups ignored |
| Token changes next request | Same user, second request token roles empty | Switcher lists no stations | No cached grant |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/context_processors.py` — today `chrome()` ignores `request` and returns every `iter_portal_configs()`; filter here
- `src/shared/packages/django-pyforge/src/django_pyforge/discovery.py` — keep unfiltered discovery for URLconf/checks (18.1)
- `src/shared/packages/django-pyforge/src/django_pyforge/roles.py` — **new** `roles_from_request`, session key, never `user.groups`
- `src/shared/packages/django-pyforge/src/django_pyforge/access.py` — **new** `require_station_role` decorator used by portal views
- `src/shared/packages/django-pyforge/src/django_pyforge/middleware.py` — **new** copy session token roles onto `request.idp_roles` when unset
- `src/shared/packages/django-pyforge/src/django_pyforge/probe_portal/views.py` — decorate `chrome_home` with `require_station_role("chrome-probe")`
- `src/shared/packages/django-pyforge/src/django_pyforge/templates/django_pyforge/switcher.html` — unchanged markup; empty list is absence
- `src/platform/config/settings/base.py` — install TokenRolesMiddleware after SessionMiddleware
- `src/platform/compliance_face/views.py` — decorate station `chrome_home` with `require_station_role("warden")` (portal URL only)
- `src/platform/config/authorization/adapters.py` — on successful OIDC login, write group-claim names into the session token-roles key (claims on this request, not User.groups)
- `src/platform/tests/test_django_pyforge_chrome.py` — keep 18.1; add 18.2 matrix tests
- `src/platform/tests/meta/test_no_pyforge_import.py` — read-only; do not start importing `pyforge`

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/roles.py` — request-scoped role read; ignore User.groups
- `src/shared/packages/django-pyforge/src/django_pyforge/access.py` — station 403 decorator
- `src/shared/packages/django-pyforge/src/django_pyforge/middleware.py` — session → `request.idp_roles`
- `src/shared/packages/django-pyforge/src/django_pyforge/context_processors.py` — filter portals by `station_name in roles`
- `src/shared/packages/django-pyforge/src/django_pyforge/probe_portal/views.py` — enforce chrome-probe
- `src/platform/compliance_face/views.py` — enforce warden on `/stations/warden/` home
- `src/platform/config/settings/base.py` — register middleware
- `src/platform/config/authorization/adapters.py` — persist token roles to session from claims
- `src/platform/tests/test_django_pyforge_chrome.py` — cover the I/O matrix

**Acceptance Criteria:**
- Given a user lacking a station role, when they load chrome, then that station is absent from the switcher.
- Given the same user, when they request the hidden station URL directly, then that station refuses (403); the switcher is not enforcement.
- Given Django group membership that would permit a station, when the token on the request does not include that station, then the switcher still omits it.
- Given a later request whose token roles are empty, when chrome renders, then no stations appear (no durable local grant).

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 2: (high 0, medium 2, low 0)
- reject: 18
- addressed_findings:
  - `[medium]` `[patch]` assert OIDC adapter writes `idp_token_roles` (dict session)
  - `[medium]` `[patch]` groups test uses empty token so BoomGroups would fire if consulted
  - `[low]` `[patch]` `role_names` keeps a string role intact (no `list("warden")`)
  - `[low]` `[patch]` non-iterable / bytes payloads deny-empty instead of TypeError
  - `[low]` `[patch]` middleware-copied session roles render the switcher

## Design Notes

Reachability role is the portal `station_name` string in the IdP role list (`CLAIMS_CONTRACT.group_claim` at login; tests may set `request.idp_roles` or `session[idp_token_roles]`). Discovery and URL mounting stay complete so a guessed URL still hits the station, which then 403s.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done
Summary: Chrome switcher lists only portals whose `station_name` is in this request's token roles; station `chrome_home` views 403 on a guessed URL. Roles come from `request.idp_roles` or session `idp_token_roles` (OIDC group claim at login), never `User.groups`.
Files changed:
- `django_pyforge/roles.py` — request-scoped role read + `role_names`
- `django_pyforge/access.py` — `require_station_role` 403
- `django_pyforge/middleware.py` — session copy onto `request.idp_roles`
- `django_pyforge/context_processors.py` — filter switcher
- probe + warden `chrome_home` — station refuse
- OIDC adapter — write session token roles from claims
- `settings/base.py` — TokenRolesMiddleware
- chrome + OIDC tests
Review: 5 patches applied (2 medium, 3 low, score 9 → followup_review_recommended true); 2 deferred; 18 rejected (live JWT, /compliance/ APIs, UX empty-state, casefold, groups-as-grant, etc.).
Verification: `platform-ci-test` pytest chrome + no-pyforge-import — 14 passed. `test_oidc_identity.py` needs Postgres (CI); local run ERRORed without a socket.
Residual: session snapshot until next login; personas lack station-name groups.
Blocking condition: none
