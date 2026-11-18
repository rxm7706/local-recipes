---
sources:
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py
verified: 2026-11-18
---

# Herald webhook endpoint

This page lists the routes, authentication, payload rules and responses of Herald's webhook: the machine-triggered path onto the same storage `herald progress --update` and `herald success create` write (Stories 13.4, 13.6 and 19.1).

:::note
There is no publicly reachable URL, by the operator's ruling. The persistent path is local: the platform host on `127.0.0.1:8001` forwards these two routes to steward's mcp-host sidecar, which serves the `webhook_host` application against `<primary checkout>/.herald/herald.db`. To run it and deliver a real landing with `herald-ship-local`, follow [Run Herald's live backend locally](../how-to/run-herald-live-backend-locally.md).
:::

## Overview

`src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py` is an HMAC-verified ASGI3 callable (`webhook.create_app(repo_root, secret)`), unit-tested in isolation. `webhook_host.py` beside it mounts it behind `daphne` as a stable `application` object (`daphne pyforge.herald.webhook_host:application`).

Story 13.6's CI demo once started that host for one job at a time; Story 36.1 archived it as `archive/.github/workflows/herald-live-demo.yml`.

## Routes

| Route | Calls | Notes |
|---|---|---|
| `POST /stations/herald/api/v1/webhooks/on-ship` | The same `progress.upsert` that `herald progress <station> --update` calls | Replaces the day's record (next section). |
| `POST /stations/herald/api/v1/webhooks/on-pr-close` | The same `claims.create` that `herald success create` calls | Only when the payload's own `merged` and `gates_passed` are both `true`; any other combination is a 202 no-op, never an error. |

The literals are the full station-API paths the platform host dispatches to herald v1 on (`src/platform/config/station_api.py`). Per the ASGI spec `path` includes `root_path`, so a further mount prefix still requires `root_path` stripping inside `webhook.py`.

## `on-ship` replaces the day's record

`progress.upsert` is keyed `(station, date)`, and the handler substitutes the CLI's own flag defaults (`[]`/`0.0`/`0`/`0.0`/`""`) for every field the payload omits. A second delivery for one station on one day resets whatever the first recorded and is answered `201` either way. Send the day's cumulative figures on every delivery, or fire `on-ship` once per day rather than once per push.

The replace is across *sources*, not just across deliveries: one `on-ship` call also overwrites whatever an operator entered by hand with `herald progress <station> --update` earlier that day.

`station` is **not** validated against the known-station list (`progress.upsert` accepts any name by design, unlike the CLI's read path, which rejects an unrecognized one). A typo'd or unrendered station records a row that no station-scoped `herald` command or dashboard will ever surface. Surrounding whitespace is stripped, but case is not normalized.

## Authentication

Every request must carry an `X-Hub-Signature-256: sha256=<hex>` header AND an `X-Hub-Timestamp: <unix-seconds>` header. The timestamp is folded into the signed content itself (`hmac.new(secret, timestamp + "." + raw_body, hashlib.sha256)`) and rejected if it is more than 5 minutes off the server's own clock in either direction. A missing or mismatched signature, a missing timestamp, or a stale one is a 401 before the body is even parsed as JSON.

The secret comes from the `HERALD_WEBHOOK_SECRET` env var, read once at mount time (`webhook.resolve_webhook_secret`): never a literal or a default fallback, and never provisioned by this package.

:::caution
That secret is a privilege boundary, not just a spam filter. The CLI's `herald progress --update` runs behind `auth.require_operator_role` (AD-16); the webhook deliberately does not, because a machine caller authenticates by proof rather than by an operator identity it does not have (AD-9). Anything holding `HERALD_WEBHOOK_SECRET` gets progress-write access the CLI grants only to a verified operator. Scope it accordingly.
:::

## Responses

| Status | When |
|---|---|
| `201` | The record was written. A redelivered `on-pr-close` answers `201` with the claim already stored. |
| `202` | `on-pr-close` with `merged` or `gates_passed` not `true`: a no-op. |
| `400` | A malformed or duplicate-keyed JSON body, or a field of the wrong type or out of range, before any storage call. |
| `401` | Signature or timestamp missing, mismatched or stale. |
| `404` / `405` | Unknown path / any method but `POST`, both before the body is read at all. |
| `413` | A body over 1 MB, or one arriving in more than 10,000 chunks. Both are checked before the signature. |
| `500` | A storage-layer failure that survived the retry budget (below). |

The 413 checks run first so an unauthenticated caller can neither make the process buffer an oversized body nor hold a request open forever by trickling empty chunks. The request path is forgiving about a trailing or doubled slash, and about the prefix it is mounted under, but nothing else.

## Payload rules that answer 400

- **Any field the route does not recognize.** Both routes reject unknown fields outright rather than ignoring them: on `on-ship` a silently ignored `token_spends` typo would not just fail to record the figure, it would *wipe* the one already there.
- A `shipped_date` that is not exactly `YYYY-MM-DD` (other ISO forms like `20260813` parse but sort wrong in the dashboard's date filter).
- A blank `event_id`, or a blank `station`/`project_name`.
- Any string field carrying a lone surrogate.
- An `evidence` entry of type `notice` whose `url` does not name a notice that actually exists. That field is a notice component name, and both publish and revalidate treat a notice entry as trivially valid, so an unchecked one would pass the entire evidence gate. The CLI makes the same check.

## Reliability

A storage-layer failure (`errors.HeraldError` from `progress.upsert`/`claims.create`) is retried up to 3 times, sleeping 1s then 2s between them and never after the last attempt, so the retry budget adds at most ~3s. Giving up logs one structured JSON `ERROR`-level record (there is no email/Slack/other operator-alert channel in this repo to build against) and answers with a non-2xx status so the caller's own delivery retry can re-fire the call later.

Sizing a caller's step timeout off that 3s alone is not safe: each attempt can additionally wait up to SQLite's 30s busy timeout for the write lock.

## Deduplication

A redelivery of an already-recorded `on-pr-close` event returns the claim already stored rather than creating a second one. **Supply a per-event `event_id`** in the payload so two different PRs shipping the same project on the same day are told apart, and so a redelivery that arrives after midnight UTC still dedupes.

Make it **globally** unique, not merely unique to one repo: a bare PR number collides across repositories, and because the `event_id` branch deliberately ignores the date, such a collision is permanent rather than same-day. `${{ github.repository }}#${{ github.event.number }}` or the delivery GUID both work.

Without an `event_id` the handler falls back to the payload's `evidence` list plus the date, which discriminates less well. A *blank* one would discriminate not at all, which is why it is rejected rather than accepted.
