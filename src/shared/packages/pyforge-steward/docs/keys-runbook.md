# Steward keys runbook (Story 48.4 / R-20)

Operator procedures for **platform secret rotation** and **age identity
custody**. Steward records metadata in `.steward/keys-inventory.yaml` and
performs age re-encryption via `steward keys rotate`; it never calls Vault,
ESO, or cloud revocation APIs.

**Profiles.** See `docs/reference/enterprise-deployment.md` § 7 for the
dev (age + manual Secret) vs enterprise (Vault + ESO) split. Platform deploy
prerequisites: `src/platform/deploy/README.md`.

All `steward keys …` examples assume the repo root and the pyforge-steward
pixi env:

```sh
pixi run -e pyforge-steward steward keys list
```

---

## Age key custody (developer profile)

| Question | Answer |
|----------|--------|
| Who holds the age key? | Named owner in `.steward/keys-inventory.yaml` (`scope` + `provenance: issued`) or individual developer for personal `SOPS_AGE_KEY_FILE` |
| Where does it live? | `~/.config/sops/age/keys.txt`, `SOPS_AGE_KEY_FILE`, or CI secret store — never in git |
| How is it rotated? | `steward keys rotate --scope <name>` re-encrypts steward-owned secrets onto a new identity; update CI secret separately |
| How is it retired? | `steward keys revoke --scope <name>` — local inventory only; for `issued` entries the old identity file can still decrypt until rotated |

After rotation, run `steward keys audit --drift --secrets <path>` on any
tree that might still reference retired material.

---

## Rotate `DJANGO_SECRET_KEY`

**Impact:** Invalidates Django sessions and signed cookies; users re-authenticate.

1. Generate a new key (50+ random chars). Example:

   ```sh
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

2. Update `platform-secrets` (manual or ESO/Vault upstream):

   ```sh
   kubectl -n platform patch secret platform-secrets -p \
     '{"stringData":{"DJANGO_SECRET_KEY":"<new>"}}'
   ```

3. Rolling restart platform Deployments (web, worker, worker-builds, beat,
   consume-events, mcp-host if it shares django env):

   ```sh
   kubectl -n platform rollout restart deployment -l app.kubernetes.io/instance=platform
   ```

4. Verify `/ht/` returns 200 through the ingress/Route.

---

## Rotate `REDIS_PASSWORD`

**Impact:** Brief broker/cache disconnect until all pods pick up the new password.

**Order matters:** redis containers before platform pods.

1. Choose a new password.
2. Update `REDIS_PASSWORD` in `platform-secrets`.
3. Restart **both** redis Deployments (broker and cache):

   ```sh
   kubectl -n platform rollout restart deployment -l app.kubernetes.io/component=redis-broker
   kubectl -n platform rollout restart deployment -l app.kubernetes.io/component=redis-cache
   kubectl -n platform rollout status deployment -l 'app.kubernetes.io/component in (redis-broker,redis-cache)'
   ```

4. Rolling restart platform pods (they expand `$(REDIS_PASSWORD)` in
   `REDIS_BROKER_URL` / `REDIS_CACHE_URL` at runtime).
5. Smoke-test: Celery task enqueue or `/ht/` database+redis checks green.

---

## Rotate DB roles (`POSTGRES_PASSWORD`, `DATABASE_URL`, `MIGRATION_DATABASE_URL`)

**Impact:** Downtime if URLs and postgres password drift; Liquibase Job needs DDL role.

The chart expects **three coordinated keys** in the same Secret:

| Key | Role |
|-----|------|
| `POSTGRES_PASSWORD` | Postgres container `POSTGRES_PASSWORD` |
| `DATABASE_URL` | App DML role (`platform_app` in default values) |
| `MIGRATION_DATABASE_URL` | Migration DDL role (`platform` user) |

1. Connect to postgres (in-cluster port-forward or exec) and rotate both
   role passwords in SQL (`ALTER ROLE … PASSWORD`).
2. Compose new URLs with unchanged host/db from `helm template` NOTES.txt.
3. Patch **all three** keys in one `platform-secrets` update (atomic from
   the application's perspective).
4. Restart postgres StatefulSet if it reads `POSTGRES_PASSWORD` only at
   start (delete pod to recreate, or rolling restart per site policy).
5. Run migrate hook if needed: `helm upgrade` triggers pre-upgrade Liquibase Job.
6. Rolling restart platform Deployments.

---

## Rotate assertion PEM (dual-key verify)

**Impact:** Lane-3 / station MCP assertions; TTL is five minutes
(`MAX_TTL_SECONDS` in `django_pyforge.assertion.schema`).

Service assertions use RS256 (`PYFORGE_ASSERTION_PRIVATE_KEY` mints,
`PYFORGE_ASSERTION_PUBLIC_KEY` verifies). The chart does not wire these env
vars yet — inject via Secret + Deployment patch or future chart values when
the mint path is production-live.

### Dual-key overlap (no multi-key code required)

1. **Generate** a new RSA pair (2048+ bits). Keep the old public PEM.
2. **Publish new public PEM** to every verifier (platform web, mcp-host,
   station portals reading `PYFORGE_ASSERTION_PUBLIC_KEY`). Verifiers now
   accept tokens signed with the **old** private key until they expire.
3. **Wait ≥ 6 minutes** (TTL + clock skew buffer).
4. **Switch minter** to the new private PEM (`PYFORGE_ASSERTION_PRIVATE_KEY`
   on the host mint endpoint).
5. **Verify** a fresh assertion:

   ```sh
   # After minting a test assertion $TOKEN against station atlas:
   pixi run -e platform-dev python -c "
   from django_pyforge.assertion.verify import verify_assertion_claims
   import os
   pem = open(os.environ['PYFORGE_ASSERTION_PUBLIC_KEY_FILE']).read()
   verify_assertion_claims('$TOKEN', audience='pyforge:station:atlas', public_pem=pem)
   print('ok')
   "
   ```

   Export `PYFORGE_ASSERTION_PUBLIC_KEY_FILE` pointing at the **new** public PEM file.

6. **Remove** the old public PEM from verifiers once no errors appear in logs
   for one full TTL window.

### Dual-key verify during overlap (explicit check)

While both keys are live, confirm an old-format token still verifies against
the **previous** public PEM before step 6:

```sh
pixi run -e platform-dev python -c "
from django_pyforge.assertion.verify import verify_assertion_claims
old_pem = open('old-public.pem').read()
verify_assertion_claims('$OLD_TOKEN', audience='pyforge:station:atlas', public_pem=old_pem)
print('old key ok')
"
```

Then confirm new tokens verify only with the new public PEM after step 4.

---

## ESO / Vault operators

When using `src/platform/deploy/overlays/eso/`, rotate upstream Vault
values; ESO refreshes `platform-secrets` on `refreshInterval`. Force sync
with ESO's `ExternalSecret` status / `kubectl annotate` patterns per your
operator version. Kubernetes rollout steps above still apply after the Secret
updates.
