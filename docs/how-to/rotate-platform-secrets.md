---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py
  - src/platform/deploy/charts/platform/templates/_helpers.tpl
  - src/platform/deploy/overlays/eso/externalsecret-platform-secrets.example.yaml
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/schema.py
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/verify.py
verified: 2026-11-27
---

# How to rotate platform secrets and age identities

Use the `steward keys` duty and the steps below to rotate the platform's secrets and to keep custody of age identities (steward Story 48.4 / R-20). Steward records metadata in `.steward/keys-inventory.yaml` and performs age re-encryption via `steward keys rotate`; it never calls Vault, ESO, or cloud revocation APIs.

## When to use this

- An age identity is suspected compromised, or its holder is offboarding.
- `DJANGO_SECRET_KEY`, `REDIS_PASSWORD` or a database role password is due for rotation.
- The assertion signing keypair is being replaced without an outage.
- Vault is the upstream and you need to know which cluster steps still apply.

:::note
**Prerequisites.** `kubectl` access to the platform namespace (the examples use `platform`) and the name of the pre-created Secret (`values.existingSecret`, default `platform-secrets`). The dev (age + manual Secret) and enterprise (Vault + ESO) profiles are described in [enterprise deployment](../explanation/enterprise-deployment.md), § 7. The Secret's keys are listed in [platform deployment architecture](../explanation/platform-deployment-architecture.md).
:::

All `steward keys …` examples assume the repo root and the pyforge-steward pixi env:

```sh
pixi run -e pyforge-steward steward keys list
```

## Age key custody (developer profile)

| Question | Answer |
|----------|--------|
| Who holds the age key? | Named owner in `.steward/keys-inventory.yaml` (`scope` + `provenance: issued`) or individual developer for personal `SOPS_AGE_KEY_FILE` |
| Where does it live? | `~/.config/sops/age/keys.txt`, `SOPS_AGE_KEY_FILE`, or CI secret store — never in git |
| How is it rotated? | `steward keys rotate --scope <name> --new-identity <path>` writes a new identity to `<path>` and re-encrypts steward-owned secrets onto it; update CI secret separately |
| How is it retired? | `steward keys revoke --scope <name>` — local inventory only; for `issued` entries the old identity file can still decrypt until rotated |

After rotation, run `steward keys audit --drift --secrets <path>` on any tree that might still reference retired material.

## Rotate `DJANGO_SECRET_KEY`

Impact: invalidates Django sessions and signed cookies; users re-authenticate.

1. Generate a new key (50+ random chars). Example:

   ```sh
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

2. Update `platform-secrets` (manual or ESO/Vault upstream):

   ```sh
   kubectl -n platform patch secret platform-secrets -p \
     '{"stringData":{"DJANGO_SECRET_KEY":"<new>"}}'
   ```

3. Rolling restart platform Deployments (web, worker, worker-builds, beat, consume-events, mcp-host if it shares django env). The selector's value is the Helm release name, `platform` here:

   ```sh
   kubectl -n platform rollout restart deployment -l app.kubernetes.io/instance=platform
   ```

4. Verify `/ht/` returns 200 through the ingress/Route.

## Rotate `REDIS_PASSWORD`

Impact: brief broker/cache disconnect until all pods pick up the new password. Order matters: redis containers before platform pods.

1. Choose a new password.
2. Update `REDIS_PASSWORD` in `platform-secrets`.
3. Restart **both** redis Deployments (broker and cache):

   ```sh
   kubectl -n platform rollout restart deployment -l app.kubernetes.io/component=redis-broker
   kubectl -n platform rollout restart deployment -l app.kubernetes.io/component=redis-cache
   kubectl -n platform rollout status deployment -l 'app.kubernetes.io/component in (redis-broker,redis-cache)'
   ```

4. Rolling restart platform pods (they expand `$(REDIS_PASSWORD)` in `REDIS_BROKER_URL` / `REDIS_CACHE_URL` at runtime).
5. Smoke-test: Celery task enqueue or `/ht/` database+redis checks green.

## Rotate DB roles (`POSTGRES_PASSWORD`, `DATABASE_URL`, `MIGRATION_DATABASE_URL`)

Impact: downtime if URLs and postgres password drift; the Liquibase Job needs the DDL role.

The chart expects **three coordinated keys** in the same Secret:

| Key | Role |
|-----|------|
| `POSTGRES_PASSWORD` | Postgres container `POSTGRES_PASSWORD` |
| `DATABASE_URL` | App DML role (`platform_app` in default values) |
| `MIGRATION_DATABASE_URL` | Migration DDL role (`platform` user) |

1. Connect to postgres (in-cluster port-forward or exec) and rotate both role passwords in SQL (`ALTER ROLE … PASSWORD`).
2. Compose new URLs with unchanged host/db; the chart's `NOTES.txt` prints the in-cluster service DNS names.
3. Patch **all three** keys in one `platform-secrets` update (atomic from the application's perspective).
4. Restart postgres StatefulSet if it reads `POSTGRES_PASSWORD` only at start (delete pod to recreate, or rolling restart per site policy).
5. Run migrate hook if needed: `helm upgrade` triggers the pre-upgrade Liquibase Job.
6. Rolling restart platform Deployments.

## Rotate assertion PEM

Impact: Lane-3 / station MCP assertions; TTL is five minutes (`MAX_TTL_SECONDS` in `django_pyforge.assertion.schema`).

Service assertions use RS256 (`PYFORGE_ASSERTION_PRIVATE_KEY` mints, `PYFORGE_ASSERTION_PUBLIC_KEY` verifies). The chart reads both from the same pre-created Secret as optional keys (`optional: true`): a pod without them still boots, and minting or verifying refuses until they are present.

There is no dual-key overlap. Each verifier holds one public PEM and checks every assertion against that key alone (`verify_assertion_claims`). Once a verifier has the new public PEM, an assertion signed with the old private key is refused as a bad signature; a verifier still on the old public PEM refuses an assertion signed with the new private key. Keep that window short by moving the minter and every verifier together:

1. **Generate** a new RSA pair (2048+ bits).
2. **Patch both keys** (`PYFORGE_ASSERTION_PRIVATE_KEY` and `PYFORGE_ASSERTION_PUBLIC_KEY`) in one `platform-secrets` update.
3. **Restart** the minter and every verifier (platform web, mcp-host, station portals reading `PYFORGE_ASSERTION_PUBLIC_KEY`) in the same rollout. An assertion minted before the restart fails on a restarted verifier; its five-minute TTL bounds how long such a token exists, and the caller needs a fresh one.
4. **Verify** a fresh assertion:

   ```sh
   # After minting a test assertion $TOKEN against station atlas:
   pixi run -e platform-dev python -c "
   from django_pyforge.assertion.verify import verify_assertion_claims
   import os
   pem = open(os.environ['PYFORGE_ASSERTION_PUBLIC_KEY_FILE']).read()
   verify_assertion_claims('$TOKEN', audience='mcp:atlas', public_pem=pem)
   print('ok')
   "
   ```

   Export `PYFORGE_ASSERTION_PUBLIC_KEY_FILE` pointing at the **new** public PEM file. The audience is `mcp:<station>` (`audience_for` in `django_pyforge.assertion.schema`).

5. **Confirm** an assertion signed with the old private key no longer verifies: the same call with `$OLD_TOKEN` and the new public PEM raises `BadSignatureError`.

## ESO / Vault operators

When using `src/platform/deploy/overlays/eso/`, rotate upstream Vault values; ESO refreshes `platform-secrets` on `refreshInterval` (`1h` in the example manifest). Force sync with ESO's `ExternalSecret` status / `kubectl annotate` patterns per your operator version. Kubernetes rollout steps above still apply after the Secret updates.

## What you get

A rotated secret in `platform-secrets`, workloads restarted onto it, and, for an age identity, an updated `.steward/keys-inventory.yaml` entry with every steward-owned secret re-encrypted to the new identity.
