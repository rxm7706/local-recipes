---
sources:
  - src/platform/config/asgi.py
  - src/platform/config/urls.py
  - src/platform/config/settings/local.py
  - src/platform/config/local_dev/mint.py
  - src/platform/config/local_dev/personas.py
  - src/platform/mcp_host/app.py
  - src/platform/mcp_host/settings.py
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_auth.py
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_dual_era.py
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/views.py
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/schema.py
  - src/shared/packages/django-pyforge/src/django_pyforge/roles.py
  - src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
verified: 2026-11-01
---

# Reach a station's MCP endpoint

Every station's service face is one URL on the platform host: `POST /stations/<station>/mcp`, a
stateless Model Context Protocol (MCP) endpoint over Streamable HTTP. This page shows how to start
the host on a laptop, get a credential the endpoint accepts, and send it a request. It describes
what the code does today; the files it cites are listed in the frontmatter.

## How a request is handled

The host's ASGI entry point, `src/platform/config/asgi.py`, sends every HTTP request to
`dispatch_station_mcp` (`django_pyforge/mcp_http.py`) before anything else, so no Django
middleware runs in front of it. For a path of exactly `/stations/<station>/mcp`, the dispatch:

1. Refuses any method but `POST` with `405` and `Allow: POST`.
2. Verifies the bearer token (`django_pyforge/mcp_auth.py`). The token is a service *assertion*:
   an RS256 JWT whose audience is `mcp:<station>`, valid for at most 300 seconds
   (`assertion/schema.py`). The host verifies it with `PYFORGE_ASSERTION_PUBLIC_KEY`.
3. Charges the call to the assertion's `sub` claim (`rate_limit.py`): 120 calls a minute by
   default, set by `MCP_RATE_LIMIT_PER_MINUTE` and `MCP_RATE_LIMIT_BURST`.
4. Routes the request. With `MCP_HOST_SIDECAR_BASE_URL` set, the host streams it to the mcp-host
   sidecar and forwards only `content-type`, `accept`, `mcp-protocol-version`, the trace headers
   and the assertion it verified. Without it, the host runs the station portal's own MCP app
   in-process. A station with no face loaded is not answered by this dispatch, and the request
   falls through to the rest of the host's routing.

The sidecar, `src/platform/mcp_host/app.py`, serves the same path on its own port. Its transport
runs no assertion check: the host verifies the assertion before the hop, so reach a station
through the host, never the sidecar's port. When Django starts in
the sidecar (it needs `DJANGO_SECRET_KEY` and `DATABASE_URL`, `mcp_host/settings.py`), marshal
gets its real tools; every other station, and marshal when Django does not start, answers with
one identity tool, `station_face`, which returns the station's name.

## Before you start

- The `platform-dev` and `mcp-host` environments are installed.
- `platform-dev`'s PostgreSQL 17 is running and the platform database is migrated: follow
  [local platform development](../tutorials/local-platform-development.md), Step 2.
- Ports 8000 and 8090 are free: `ss -ltnH '( sport = :8000 or sport = :8090 )'` prints nothing.
- `LANGFLOW_SUPERUSER_PASSWORD` is set in your shell. The host mounts Langflow, which does not
  start without it (`src/platform/README.md`).
- Run every command from the repository root unless a step says otherwise.

## 1. Make the assertion key pair

The host signs assertions with `PYFORGE_ASSERTION_PRIVATE_KEY` and verifies them with
`PYFORGE_ASSERTION_PUBLIC_KEY`. Local settings set neither, so generate a pair outside the
repository and export both:

```bash
KEYS=$(mktemp -d)
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$KEYS/assertion.key"
openssl pkey -in "$KEYS/assertion.key" -pubout -out "$KEYS/assertion.pub"
export PYFORGE_ASSERTION_PRIVATE_KEY="$(cat "$KEYS/assertion.key")"
export PYFORGE_ASSERTION_PUBLIC_KEY="$(cat "$KEYS/assertion.pub")"
```

Without the private key the mint in step 4 answers `401`; without the public key the endpoint
answers `503 verifier not configured`.

## 2. Start the sidecar

```bash
DJANGO_SECRET_KEY=local-not-a-secret \
DATABASE_URL="${DATABASE_URL:-postgres:///platform}" \
  pixi run --frozen -e mcp-host mcp-host-serve &
```

`mcp-host-serve` runs `uvicorn mcp_host.app:app` on `127.0.0.1:8090` from `src/platform/`.
`curl -s http://127.0.0.1:8090/health` prints `{"status":"ok"}` once it is up. Skip
`DJANGO_SECRET_KEY` and `DATABASE_URL` if you only need the `station_face` identity tool.

## 3. Start the host

Start the host from `src/platform/`, where `config` imports:

```bash
( cd src/platform \
  && DATABASE_URL="${DATABASE_URL:-postgres:///platform}" \
     MCP_HOST_SIDECAR_BASE_URL=http://127.0.0.1:8090 \
     exec pixi run --frozen -e platform-dev \
       daphne --bind 127.0.0.1 --port 8000 --proxy-headers config.asgi:application ) &
```

`config.asgi` defaults to `config.settings.local` and sets `COMPONENT_RUNTIME=local`. Leave
`COMPONENT_OIDC_ISSUER` unset: local settings then trust the persona keys in
`src/platform/.dev-keys/` (`config/settings/local.py`), which step 4 uses. The host takes some
seconds to import; wait until `ss -ltnH 'sport = :8000'` prints a line.

To run the station faces in-process instead, leave `MCP_HOST_SIDECAR_BASE_URL` unset and skip
step 2. A face whose `mcp` SDK is missing from the host's interpreter is skipped, and the host
logs `MCP face skipped` naming `MCP_HOST_SIDECAR_BASE_URL`; use the sidecar then.

## 4. Get an assertion

An assertion is minted by the host at `POST /assertion/mint/` (`config/urls.py`) in exchange for
an identity-provider token whose group claim grants the station: `pyforge:station:<station>`, or
`pyforge:admin` for every station (`django_pyforge/roles.py`). Locally, the `marshal-operator`
persona carries `pyforge:station:marshal` (`config/local_dev/personas.py`). Mint its token, then
trade it for an assertion:

```bash
IDP=$( cd src/platform && COMPONENT_RUNTIME=local pixi run --frozen -e platform-dev python -c \
  "from config.local_dev.mint import main; print(main(['marshal-operator']))" | tail -1 )

ASSERTION=$(curl -sS -X POST http://127.0.0.1:8000/assertion/mint/ \
  -H "Authorization: Bearer $IDP" \
  -H 'Content-Type: application/json' \
  -d '{"station": "marshal"}' \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["assertion"])')
```

The mint answers `{"assertion": "<jwt>"}`. It refuses with `401` for a missing or unverifiable
token, `400` for a body without a `station`, `403` when the token's groups do not grant the
station, and `503` when no identity-provider verifier is configured. The persona token lives 900
seconds and the assertion 300; mint again when either expires. An assertion opens one station
only: an assertion minted for `marshal` sent to another station's endpoint gets `403 wrong
audience`.

## 5. Send a request

Every call is one JSON-RPC 2.0 message in one `POST`. Send `Accept: application/json,
text/event-stream`; the answer is a JSON body.

```bash
mcp() {
  curl -sS -X POST "http://127.0.0.1:8000/stations/$1/mcp" \
    -H "Authorization: Bearer $ASSERTION" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d "$2"
}

mcp marshal '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
mcp marshal '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
mcp marshal '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"<tool>","arguments":{}}}'
```

`tools/list` names the station's tools and their arguments; put one in `tools/call`.

The protocol revision is checked in two places (`mcp_dual_era.py`). An `MCP-Protocol-Version`
header, when you send one, must be `2025-03-26`, `2025-06-18`, `2025-11-25` or `2026-07-28`. An
`initialize` call's `protocolVersion` must be one of the first three. Anything else gets the
JSON-RPC error `-32022`, whose data lists the supported revisions.

## What each refusal means

| Answer | Cause |
|---|---|
| `405 Method Not Allowed` | Anything but `POST`. |
| `401 assertion required` | No `Authorization: Bearer` header. |
| `401 assertion refused` | The token is not a valid assertion, or it has expired. |
| `403 wrong audience` | The assertion was minted for another station. |
| `503 verifier not configured` | The host has no `PYFORGE_ASSERTION_PUBLIC_KEY`. |
| `429` with `Retry-After` | The assertion's `sub` used up its calls; wait the named seconds. |
| `502 mcp-host sidecar unreachable` | `MCP_HOST_SIDECAR_BASE_URL` is set and nothing answers there. |
| JSON-RPC error `-32022` | An unsupported protocol revision (step 5). |

## Where to go next

- What a station's tools do: that station's skill, `.claude/skills/pyforge-<station>/active/pyforge-<station>/SKILL.md`.
- Herald's webhooks, which the same sidecar serves: [run Herald's live backend locally](run-herald-live-backend-locally.md).
- Where the host, the sidecar and the faces sit in the platform:
  [the estate overview](../explanation/pyforge-estate-overview.md).
