#!/usr/bin/env bash
# Replay Platform CI (.github/workflows/platform-ci.yml) on this machine, so a
# Platform change is proven before it is pushed and no Actions minutes are
# spent finding out. Four stages, each one of the workflow's jobs:
#
#   test        the `test` job, step for step: manage.py check, ruff, ruff
#               format, mypy, the policy suite, sqlmigrate extraction, the
#               full pytest suite
#   images      the three image builds (platform, DB-GPT sidecar, mcp-host)
#   container   the `container` job's runtime smokes against the built image:
#               migrate, start, /ht/, /admin/login/, /, every static asset the
#               home page references, /api/health, /health, manage.py check in
#               the container, the non-root UID
#   promotion   the `golden-path-promotion` job: digests + Warden verdict, then
#               the deploy-side verifier (informational — it refuses anything
#               but a `clean` verdict, which is the deploy gate's job)
#
#   pixi run -e pyforge-guild platform-ci-local                  # all four, docker
#   pixi run -e pyforge-guild platform-ci-local -- --test        # one stage
#   pixi run -e pyforge-guild platform-ci-local -- --images --container --engine podman
#
# Services: an ephemeral PostgreSQL 17 (+pgvector) and Redis 7 from the
# platform-dev env, TCP only, on PLATFORM_CI_LOCAL_PG_PORT (15432) and
# PLATFORM_CI_LOCAL_REDIS_PORT (16379); torn down on exit. The app container
# runs with host networking and binds 8000, as the image does. Tools come from
# the pixi envs the workflow uses (platform-ci-test, platform-dev,
# pyforge-warden); docker or podman must be on the host.
#
# Keep in step with the workflow: every step name below is the workflow's own.
set -uo pipefail

ROOT="${PIXI_PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT" || exit 2

STAGES=()
ENGINE="${PLATFORM_CI_LOCAL_ENGINE:-docker}"
while [ $# -gt 0 ]; do
  case "$1" in
    --test|--images|--container|--promotion) STAGES+=("${1#--}") ;;
    --engine) ENGINE="$2"; shift ;;
    -h|--help) sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1 (see --help)" >&2; exit 2 ;;
  esac
  shift
done
[ ${#STAGES[@]} -eq 0 ] && STAGES=(test images container promotion)

PG_PORT="${PLATFORM_CI_LOCAL_PG_PORT:-15432}"
REDIS_PORT="${PLATFORM_CI_LOCAL_REDIS_PORT:-16379}"
APP_PORT=8000
TAG="${PLATFORM_CI_LOCAL_TAG:-ci-local}"
WORK="${PLATFORM_CI_LOCAL_WORK:-${TMPDIR:-/tmp}/platform-ci-local}"
CIT="$ROOT/.pixi/envs/platform-ci-test/bin"
DEV="$ROOT/.pixi/envs/platform-dev/bin"
WRD="$ROOT/.pixi/envs/pyforge-warden/bin"
APP="platform-ci-app-$TAG"
RESULTS="$WORK/results.tsv"

mkdir -p "$WORK"
: >"$RESULTS"

step() {
  # step <stage> <name> <cmd...>: run, record PASS/FAIL, keep the log.
  local stage="$1" name="$2" log; shift 2
  log="$WORK/$(echo "$stage-$name" | tr -c 'A-Za-z0-9._-' '_').log"
  printf '\n== [%s] %s\n' "$stage" "$name"
  if "$@" >"$log" 2>&1; then
    printf 'PASS\t%s\t%s\n' "$stage" "$name" >>"$RESULTS"; tail -2 "$log"; return 0
  fi
  printf 'FAIL\t%s\t%s\n' "$stage" "$name" >>"$RESULTS"
  echo "FAIL — last 25 lines of $log:"; tail -25 "$log"; return 1
}

ensure_envs() {
  local e
  for e in platform-ci-test platform-dev pyforge-warden; do
    [ -x "$ROOT/.pixi/envs/$e/bin/python" ] || pixi install --frozen -e "$e" >/dev/null
  done
  command -v "$ENGINE" >/dev/null 2>&1 || { echo "$ENGINE is not on PATH" >&2; exit 2; }
}

start_services() {
  local pgdata="$WORK/pg" i
  stop_services
  rm -rf "$pgdata" "$WORK/redis"; mkdir -p "$WORK/redis"
  "$DEV/initdb" -D "$pgdata" -U postgres --auth=trust >"$WORK/initdb.log" 2>&1
  "$DEV/pg_ctl" -D "$pgdata" -l "$WORK/pg.log" -w \
    -o "-c unix_socket_directories='' -h 127.0.0.1 -p $PG_PORT" start >/dev/null
  for i in $(seq 1 30); do
    "$DEV/pg_isready" -h 127.0.0.1 -p "$PG_PORT" -U postgres >/dev/null 2>&1 && break; sleep 1
  done
  "$DEV/psql" -h 127.0.0.1 -p "$PG_PORT" -U postgres -qc "CREATE DATABASE platform;" >/dev/null
  "$DEV/psql" -h 127.0.0.1 -p "$PG_PORT" -U postgres -d platform -qc "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null
  "$DEV/redis-server" --port "$REDIS_PORT" --dir "$WORK/redis" --save "" --appendonly no \
    --daemonize yes --logfile "$WORK/redis.log" --pidfile "$WORK/redis.pid" >/dev/null
  echo "services: postgres 127.0.0.1:$PG_PORT, redis 127.0.0.1:$REDIS_PORT (work dir $WORK)"
}

stop_services() {
  "$ENGINE" rm -f "$APP" >/dev/null 2>&1 || true
  if [ -f "$WORK/redis.pid" ]; then kill "$(cat "$WORK/redis.pid")" 2>/dev/null || true; rm -f "$WORK/redis.pid"; fi
  if [ -d "$WORK/pg" ]; then "$DEV/pg_ctl" -D "$WORK/pg" stop -m fast >/dev/null 2>&1 || true; fi
}
trap stop_services EXIT

stage_test() {
  # The workflow's `test` job, in its order, with its env.
  export DATABASE_URL="postgres://postgres:platform@localhost:$PG_PORT/platform"
  export REDIS_URL="redis://localhost:$REDIS_PORT/0"
  export PATH="$CIT:$DEV:$PATH"
  local py=(env -u PYTHONSAFEPATH python)   # PYTHONSAFEPATH breaks config.settings.* imports
  ( cd src/platform || exit 2
    step test "Django system checks (PostgreSQL + Redis, no other backing service)" "${py[@]}" manage.py check &&
    step test "Ruff" "$CIT/ruff" check . &&
    step test "Ruff format" "$CIT/ruff" format --check . &&
    step test "Mypy" env -u PYTHONSAFEPATH "$CIT/mypy" platformapp config tests &&
    step test "Policy suite" "${py[@]}" -m pytest tests/policy -q -p no:cacheprovider &&
    step test "sqlmigrate extraction" "${py[@]}" -m db.sqlmigrate_extraction &&
    step test "Full test suite (platformapp app tests, the ASGI seam, and the import boundary)" \
      "${py[@]}" -m pytest -q -p no:cacheprovider
  )
}

export_context() {
  # The build context is the git-tracked tree (plus untracked, non-ignored
  # files), exported to a scratch dir -- the local twin of a CI checkout.
  # `.dockerignore`'s own `.pixi/*` exclusion prunes the multi-GB `.pixi/`
  # tree cleanly on its own now (retro action item 9, 2026-09-05 -- it used
  # to carry a `!.pixi/config.toml` negation that forced a full walk of that
  # tree instead; every Containerfile now reproduces that one setting
  # directly rather than relying on the negation). This export still earns
  # its keep for what `.dockerignore` alone does not cover: the recipe
  # universe (7,800+ files; no Containerfile reads `recipes/`, and
  # `.dockerignore` never excludes it) and a git-index-speed listing instead
  # of a raw filesystem walk of the whole checkout.
  local ctx="$WORK/context"
  rm -rf "$ctx"; mkdir -p "$ctx"
  git ls-files -z --cached --others --exclude-standard -- . ':!recipes' \
    | tar --null -T - -cf - --ignore-failed-read 2>/dev/null | tar -xf - -C "$ctx"
  echo "context: $(find "$ctx" -type f | wc -l) files under $ctx"
}

stage_images() {
  export_context
  local ctx="$WORK/context"
  step images "Build image ($ENGINE) platform" "$ENGINE" build -f "$ctx/src/platform/Containerfile" -t "platform:$TAG" "$ctx" &&
  step images "Build DB-GPT sidecar image ($ENGINE)" "$ENGINE" build -f "$ctx/src/platform/compose/dbgpt/Containerfile" -t "platform-dbgpt-sidecar:$TAG" "$ctx" &&
  step images "Build mcp-host sidecar image ($ENGINE)" "$ENGINE" build -f "$ctx/src/platform/compose/mcp-host/Containerfile" -t "platform-mcp-host:$TAG" "$ctx"
}

http_code() { curl -s -o "${2:-/dev/null}" -w '%{http_code}' "http://localhost:$APP_PORT$1" || true; }
expect_code() { # expect_code <path> <code>
  local code; code="$(http_code "$1")"; echo "$1 -> $code"; [ "$code" = "$2" ]
}
poll_ht() {
  local i code
  for i in $(seq 1 60); do code="$(http_code /ht/)"; [ "$code" = "200" ] && { echo "/ht/ -> 200 after $((i * 2))s"; return 0; }; sleep 2; done
  echo "/ht/ never returned 200 (last: $code)"; "$ENGINE" logs "$APP" 2>&1 | tail -30; return 1
}
static_assets() {
  local u c bad=0
  http_code / "$WORK/home.html" >/dev/null
  while read -r u; do
    c="$(http_code "$u")"; [ "$c" = "200" ] || { echo "NOT 200: $u -> $c"; bad=1; }
  done < <(grep -o -E '(href|src)="/static/[^"]+"' "$WORK/home.html" | sed -E 's/^[a-z]+="//; s/"$//' | sort -u)
  echo "$(grep -c -o -E '(href|src)="/static/' "$WORK/home.html") static references checked"; return $bad
}
non_root() {
  local uid gid; uid="$("$ENGINE" run --rm --entrypoint id "platform:$TAG" -u)"; gid="$("$ENGINE" run --rm --entrypoint id "platform:$TAG" -g)"
  echo "uid=$uid gid=$gid"; [ "$uid" != "0" ] && [ "$gid" = "0" ]
}

stage_container() {
  # The workflow's `container` job against the local services (host networking
  # replaces its per-run network; the DSNs point at 127.0.0.1).
  local common=(-e DJANGO_SECRET_KEY=ci-placeholder-not-a-real-secret -e DJANGO_ADMIN_URL=admin/
    -e COMPONENT_RUNTIME=local -e DATABASE_URL="postgres://postgres:platform@127.0.0.1:$PG_PORT/platform"
    -e REDIS_URL="redis://127.0.0.1:$REDIS_PORT/0")
  if ss -ltn 2>/dev/null | grep -q ":$APP_PORT "; then echo "port $APP_PORT is busy; the image binds it" >&2; return 1; fi
  "$ENGINE" rm -f "$APP" >/dev/null 2>&1 || true
  step container "Migrate the database (the image's CMD deliberately doesn't)" \
    "$ENGINE" run --rm --network host "${common[@]}" "platform:$TAG" python manage.py migrate --noinput &&
  step container "Run platform container ($ENGINE)" "$ENGINE" run -d --name "$APP" --network host "${common[@]}" \
    -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 -e DJANGO_SECURE_SSL_REDIRECT=False "platform:$TAG" &&
  step container "Poll /ht/ for 200" poll_ht &&
  step container "Smoke-test an ORM-backed page (proves migrations ran)" expect_code /admin/login/ 200 &&
  step container "Smoke-test a real template page (static manifest + offline compression)" expect_code / 200 &&
  step container "Fetch every static asset the home page references" static_assets &&
  step container "Smoke-test the FastAPI seam (/api/, the other half of the ASGI dispatcher)" expect_code /api/health 200 &&
  step container "Smoke-test the Langflow mount (bare /health, unchanged forward per AD-4)" expect_code /health 200 &&
  step container "manage.py check inside the running container" "$ENGINE" exec "$APP" /app/entrypoint.sh python manage.py check &&
  step container "Confirm non-root UID (arbitrary uid honored)" non_root
  local rc=$?
  "$ENGINE" rm -f "$APP" >/dev/null 2>&1 || true
  return $rc
}

stage_promotion() {
  local out="$WORK/golden-path-promotion.json" d1 d2 d3
  export PATH="$WRD:$PATH"
  PLATFORM_REF="platform:$TAG" SIDECAR_REF="platform-dbgpt-sidecar:$TAG" MCP_HOST_REF="platform-mcp-host:$TAG" OUT="$out" \
    step promotion "Record digests + Warden verdict (golden-path promotion)" bash scripts/platform-golden-path-promotion.sh || return 1
  "$CIT/python" - "$out" <<'PY'
import json, sys
p = json.load(open(sys.argv[1], encoding="utf-8"))
print(f"warden_status={p['warden_status']} warden_exit_code={p['warden_exit_code']} inventory={p['warden'].get('inventory_count')}")
PY
  d1="$("$ENGINE" inspect --format='{{.Id}}' "platform:$TAG")"; d2="$("$ENGINE" inspect --format='{{.Id}}' "platform-dbgpt-sidecar:$TAG")"; d3="$("$ENGINE" inspect --format='{{.Id}}' "platform-mcp-host:$TAG")"
  echo; echo "== [promotion] deploy-side verifier (informational: platform-deploy's gate, refuses any verdict but clean)"
  if PROMOTION_JSON="$out" PLATFORM_DIGEST="$d1" SIDECAR_DIGEST="$d2" MCP_HOST_DIGEST="$d3" "$CIT/python" scripts/platform-deploy-verify-promotion.py; then
    printf 'INFO\tpromotion\tdeploy verifier: clean, would promote\n' >>"$RESULTS"
  else
    printf 'INFO\tpromotion\tdeploy verifier: refused (verdict not clean) — deploy promotes clean only (Story 12.1)\n' >>"$RESULTS"
  fi
}

ensure_envs
needs_services=0
for s in "${STAGES[@]}"; do case "$s" in test|container) needs_services=1 ;; esac; done
[ "$needs_services" = 1 ] && start_services
for s in "${STAGES[@]}"; do "stage_$s" || true; done

echo; echo "===== platform-ci-local summary ($ENGINE, tag $TAG) ====="
column -t -s $'\t' "$RESULTS" 2>/dev/null || cat "$RESULTS"
if grep -q '^FAIL' "$RESULTS"; then echo "RESULT: FAIL (logs under $WORK)"; exit 1; fi
echo "RESULT: PASS (logs under $WORK)"
