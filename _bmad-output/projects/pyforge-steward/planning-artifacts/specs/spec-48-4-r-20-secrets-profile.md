---
title: "Story 48.4: R-20 secrets profile"
type: story
created: 2026-09-10
baseline_revision: 5fc43c0440d31fa7b29bf40218f5257ca734c2fe
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/reference/enterprise-deployment.md
  - src/platform/deploy/README.md
  - src/platform/deploy/charts/platform/values.yaml
  - src/platform/deploy/charts/platform/templates/_helpers.tpl
  - src/platform/config/settings/base.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md
warnings: []
deferred: []
declared_low_risk: false
---

# Story 48.4: R-20 secrets profile

<intent-contract>

## Intent

**Problem:** Red-team X-7 found go-sops + age is a developer vault with no enterprise custody story, the chart requires a pre-created `platform-secrets` Secret with no creator documented, no External Secrets Operator (ESO) example exists, and rotation for `DJANGO_SECRET_KEY`, `REDIS_PASSWORD`, DB roles, and the RS256 assertion PEM is undocumented.

**Approach:** Document two profiles — local/dev (age + steward keys inventory) and enterprise (Vault/ESO via ExternalSecret) — ship one overlay example for the ESO profile, and add a steward keys runbook with step-by-step rotation procedures including dual-key assertion verification during the overlap window.

## Boundaries & Constraints

**Always:** Chart AD-12 invariant holds — the core chart never renders `kind: Secret` or embeds credential values; overlays are examples only. ExternalSecret example must target the same key names the chart expects (`DJANGO_SECRET_KEY`, `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, plus optional assertion PEM keys documented for future chart wiring). Age custody must name who holds the key, where it lives, and how rotation is triggered (`steward keys rotate`). Assertion rotation runbook must describe dual-key verify: verifiers accept the previous public PEM until in-flight five-minute assertions expire, then cut over the minter private key.

**Never:** Do not add Vault HTTP clients to the platform image (canopy:AD-19). Do not commit real secret values, age private keys, or PEM material. Do not change network policies (Story 48.3). Do not wire Keycloak/OIDC (Story 48.9). Do not hand-edit `sprint-status-ledger.yaml` without sync.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| DEV_PROFILE | Operator reads enterprise-deployment § Secrets profile | Dev profile names age key custody, `SOPS_AGE_KEY_FILE`, steward inventory path, and `steward keys rotate` | N/A — docs |
| ESO_EXAMPLE | `kubectl apply -f overlays/eso/` (after editing Vault paths) | ExternalSecret creates `platform-secrets` with all required keys | README states operator must install ESO + configure SecretStore first |
| DJANGO_ROTATE | New `DJANGO_SECRET_KEY` in Secret + rolling restart | Sessions invalidate; app starts clean | Runbook warns logged-in users re-auth |
| REDIS_ROTATE | New `REDIS_PASSWORD` + redis pod restart + platform rollout | AUTH succeeds on new password | Runbook orders redis before web/worker |
| DB_ROLE_ROTATE | Password change on postgres roles + URL updates in Secret | Both `DATABASE_URL` and `MIGRATION_DATABASE_URL` updated together with `POSTGRES_PASSWORD` | Runbook names Liquibase Job ordering |
| ASSERTION_DUAL_KEY | New RSA pair generated | Verifiers use new public PEM; old tokens valid ≤5 min; manual verify step documented | Runbook cites `MAX_TTL_SECONDS` |

</intent-contract>

## Code Map

- `docs/reference/enterprise-deployment.md` — add § Secrets profile (R-20): dev age custody vs enterprise Vault/ESO; links to overlay and runbook
- `src/platform/deploy/README.md:20-44` — existing `existingSecret` key table; cross-link secrets profile
- `src/platform/deploy/charts/platform/values.yaml:66` — `existingSecret: platform-secrets`
- `src/platform/deploy/charts/platform/templates/_helpers.tpl:252-353` — required secret keys in `platform.djangoEnv` / `platform.liquibaseEnv`
- `src/platform/config/settings/base.py:719-720` — `PYFORGE_ASSERTION_PRIVATE_KEY` / `PYFORGE_ASSERTION_PUBLIC_KEY` env vars (not yet chart-wired; document in ESO example as optional keys)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` — `rotate_identity`, `revoke_identity`, age encrypt/decrypt primitives the runbook references
- `.steward/keys-inventory.yaml` — live inventory shape the runbook cites
- `src/platform/deploy/overlays/ocp/cluster-bringup.md:208` — manual `kubectl create secret` precedent to contrast with ESO profile

## Tasks & Acceptance

**Execution:**
- `docs/reference/enterprise-deployment.md` — new § Secrets profile (R-20) with dev and enterprise profiles, age custody, ESO pointer
- `src/platform/deploy/overlays/eso/README.md` — prerequisites, apply order, key mapping table
- `src/platform/deploy/overlays/eso/secretstore-vault.example.yaml` — example SecretStore (Vault backend)
- `src/platform/deploy/overlays/eso/externalsecret-platform-secrets.example.yaml` — example ExternalSecret for all platform keys + optional assertion PEM keys
- `src/shared/packages/pyforge-steward/docs/keys-runbook.md` — rotation runbooks for DJANGO_SECRET_KEY, REDIS_PASSWORD, DB roles, assertion PEM dual-key verify
- `src/platform/deploy/README.md` — link to secrets profile and ESO overlay
- `src/platform/tests/test_chart_invariants.py` — Story 48.4 test: ESO example YAML lists every required `existingSecret` key

**Acceptance Criteria:**
- Given an operator reads `enterprise-deployment.md`, when they reach the secrets profile section, then age key custody and rotation for the dev profile are stated and the Vault/ESO profile points at the overlay example
- Given the ESO overlay example, when inspected, then it defines one ExternalSecret targeting `platform-secrets` with keys `DJANGO_SECRET_KEY`, `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`
- Given `keys-runbook.md`, when an operator follows the assertion PEM rotation section, then dual-key verify during the five-minute overlap window is documented with explicit verification commands
- Given `pixi run -e platform-dev pytest src/platform/tests/test_chart_invariants.py -q`, when tests run, then Story 48.4 invariant passes

## Verification

**Commands:**
- `pixi run -e platform-dev pytest -c /dev/null src/platform/tests/test_chart_invariants.py -q -k story_48_4` — expected: pass

**Manual checks (if no CLI):**
- ExternalSecret example YAML parses and remoteRef keys match README table

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 2 findings — high 0, medium 0, low 1, false 1, maybe-false 0
- findings:
  - `[low]` `[reject]` ESO example uses v1beta1 API — acceptable for an example overlay; operators pin to their cluster's CRD version
  - `[false]` `[reject]` Claim that assertion keys are wired in chart djangoEnv — story documents optional keys only; chart wiring deferred

## Auto Run Result

Status: done
Blocking condition: none

Summary: Story 48.4 lands R-20 secrets profile — enterprise-deployment § 7 (dev age custody + Vault/ESO enterprise profile), ESO overlay examples (`SecretStore` + `ExternalSecret`), steward keys rotation runbook (DJANGO_SECRET_KEY, REDIS_PASSWORD, DB roles, assertion PEM dual-key overlap), deploy README cross-links, and chart invariant test for required secret keys.

Files changed:
- `docs/reference/enterprise-deployment.md` — § 7 Secrets profile
- `src/platform/deploy/overlays/eso/*` — ESO example manifests + README
- `src/shared/packages/pyforge-steward/docs/keys-runbook.md` — rotation runbooks
- `src/platform/deploy/README.md` — secrets profile pointer
- `src/platform/tests/test_chart_invariants.py` — Story 48.4 invariant test
- `spec-48-4-r-20-secrets-profile.md` — story spec
- `sprint-status-ledger.yaml` — 48-4 promoted to `done`

Verification: `pytest -c /dev/null src/platform/tests/test_chart_invariants.py -q -k story_48_4` — 1 passed

Follow-up review recommended: false

## Design Notes

The enterprise profile stays outside the platform image: ESO syncs Vault → Kubernetes Secret; the chart consumes `secretKeyRef` only (canopy:AD-19). Assertion keys are documented in the ESO example for operators who inject them via env (chart wiring is a follow-on); dual-key rotation leverages the five-minute assertion TTL rather than code changes to multi-key JWKS.
