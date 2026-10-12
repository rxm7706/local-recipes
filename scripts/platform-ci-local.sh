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
# Overlap: one machine-wide flock lock (PLATFORM_CI_LOCAL_LOCK,
# PLATFORM_CI_LOCAL_LOCK_WAIT) so concurrent runs never share ports, work dir,
# tag or container name (Story 63.7). Set PLATFORM_CI_LOCAL_NO_LOCK=1 to skip
# (tests only).
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

# Exclusive machine-wide lock so overlapping runs never share ports, work dir or
# services (steward Story 63.7). Only this shell holds the flock; children run
# with fd 9 closed (Story 89.1). A waiter that exceeds PLATFORM_CI_LOCAL_LOCK_WAIT
# exits 2 and names the live holder(s).
acquire_run_lock() {
  [ "${PLATFORM_CI_LOCAL_NO_LOCK:-0}" = 1 ] && return 0
  local lock_file="${PLATFORM_CI_LOCAL_LOCK:-${TMPDIR:-/tmp}/platform-ci-local.lock}"
  local lock_meta="${lock_file}.holder"
  local wait_sec="${PLATFORM_CI_LOCAL_LOCK_WAIT:-7200}"
  mkdir -p "$(dirname "$lock_file")"
  exec 9>"$lock_file"
  if ! flock -w "$wait_sec" 9; then
    echo "platform-ci-local: lock held longer than ${wait_sec}s — not starting services" >&2
    _report_lock_contention "$lock_file" "$lock_meta" >&2
    exit 2
  fi
  {
    echo "pid=$$"
    echo "checkout=$ROOT"
    echo "stages=${STAGES[*]}"
    echo "started=$(date -Iseconds 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$lock_meta"
}

_report_lock_contention() {
  local lock_file="$1" lock_meta="$2"
  local recorded_pid="" line
  if [ -f "$lock_meta" ]; then
    while IFS= read -r line; do
      case "$line" in pid=*) recorded_pid="${line#pid=}" ;; esac
    done <"$lock_meta"
  fi
  echo "processes holding ${lock_file}:" >&2
  _pids_holding_path "$lock_file" | while read -r hp; do
    [ -n "$hp" ] || continue
    printf '  pid=%s cmdline=%s\n' "$hp" "$(_proc_cmdline "$hp")" >&2
  done
  if [ -n "$recorded_pid" ] && kill -0 "$recorded_pid" 2>/dev/null; then
    local among=0 hp
    for hp in $(_pids_holding_path "$lock_file"); do
      [ "$hp" = "$recorded_pid" ] && among=1
    done
    if [ "$among" = 1 ]; then
      echo "holder (from ${lock_meta}):" >&2
      cat "$lock_meta" >&2
      return 0
    fi
  fi
  if [ -n "$recorded_pid" ]; then
    echo "holder record stale (pid ${recorded_pid} not running):" >&2
    [ -f "$lock_meta" ] && cat "$lock_meta" >&2
  elif [ -f "$lock_meta" ]; then
    echo "holder (from ${lock_meta}):" >&2
    cat "$lock_meta" >&2
  else
    echo "holder: (no metadata file at ${lock_meta})" >&2
  fi
}

_proc_cmdline() {
  [ -r "/proc/$1/cmdline" ] || return 0
  tr '\0' ' ' <"/proc/$1/cmdline" 2>/dev/null || true
}

_pid_alive() {
  kill -0 "$1" 2>/dev/null
}

_pids_holding_path() {
  local target="$1" pid fd link
  for pid in /proc/[0-9]*; do
    pid="${pid#/proc/}"
    for fd in /proc/"$pid"/fd/*; do
      [ -L "$fd" ] || continue
      link="$(readlink "$fd" 2>/dev/null || true)"
      [ "$link" = "$target" ] || [ "$link" = "${target} (deleted)" ] || continue
      echo "$pid"
      break
    done
  done | sort -u
}

_wait_pid_exit() {
  local pid="$1" i max="${2:-30}"
  for i in $(seq 1 "$max"); do
    _pid_alive "$pid" || return 0
    sleep 0.2
  done
  if _pid_alive "$pid"; then
    return 1
  fi
  return 0
}

_listener_on_port() {
  local port="$1" line pid
  while IFS= read -r line; do
    case "$line" in
      *":${port} "*) ;;
      *) continue ;;
    esac
    if [[ "$line" =~ pid=([0-9]+) ]]; then
      echo "${BASH_REMATCH[1]}"
      return 0
    fi
  done < <(ss -ltnp 2>/dev/null || true)
  return 1
}

_refuse_port_in_use() {
  local port="$1" name="$2" pid cmd
  pid="$(_listener_on_port "$port")" || return 0
  cmd="$(_proc_cmdline "$pid")"
  echo "platform-ci-local: ${name} port ${port} in use by pid ${pid} (${cmd}) — not starting services" >&2
  exit 2
}

_postmaster_pid() {
  [ -f "$WORK/pg/postmaster.pid" ] || return 1
  head -1 "$WORK/pg/postmaster.pid"
}

_is_our_postgres() {
  local pid="$1" cmd pgdir
  pgdir="$WORK/pg"
  _pid_alive "$pid" || return 1
  cmd="$(_proc_cmdline "$pid")"
  [[ "$cmd" == *postgres* ]] && [[ "$cmd" == *"-D"*"${pgdir}"* ]]
}

_is_our_redis() {
  local pid="$1" cmd
  _pid_alive "$pid" || return 1
  cmd="$(_proc_cmdline "$pid")"
  [[ "$cmd" == *redis-server* ]]
}

stop_services() {
  local pid pgdir="$WORK/pg"
  "$ENGINE" rm -f "$APP" 9>&- >/dev/null 2>&1 || true
  if [ -f "$WORK/redis.pid" ]; then
    pid="$(cat "$WORK/redis.pid" 2>/dev/null || true)"
    if [ -n "$pid" ] && _is_our_redis "$pid"; then
      echo "platform-ci-local: stopping redis (pid ${pid})" >&2
      kill "$pid" 2>/dev/null || true
      if ! _wait_pid_exit "$pid" 30; then
        echo "platform-ci-local: redis pid ${pid} did not exit within wait bound" >&2
      fi
    fi
    rm -f "$WORK/redis.pid"
  fi
  if [ -d "$pgdir" ]; then
    pid="$(_postmaster_pid 2>/dev/null || true)"
    if [ -n "$pid" ] && _is_our_postgres "$pid"; then
      echo "platform-ci-local: stopping postgres (pid ${pid})" >&2
      "$DEV/pg_ctl" -D "$pgdir" stop -m fast 9>&- >/dev/null 2>&1 || true
      if ! _wait_pid_exit "$pid" 60; then
        echo "platform-ci-local: postgres pid ${pid} did not exit within wait bound" >&2
      fi
    elif [ -n "$pid" ]; then
      rm -f "$pgdir/postmaster.pid"
    fi
  fi
}

run_platform_ci_local() {
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
    local stage="$1" name="$2" log; shift 2
    log="$WORK/$(echo "$stage-$name" | tr -c 'A-Za-z0-9._-' '_').log"
    printf '\n== [%s] %s\n' "$stage" "$name"
    if "$@" 9>&- >"$log" 2>&1; then
      printf 'PASS\t%s\t%s\n' "$stage" "$name" >>"$RESULTS"; tail -2 "$log"; return 0
    fi
    printf 'FAIL\t%s\t%s\n' "$stage" "$name" >>"$RESULTS"
    echo "FAIL — last 25 lines of $log:"; tail -25 "$log"; return 1
  }

  _pixi_env_lock_hash() {
    local pixi_env="$1"
    local record="$ROOT/.pixi/envs/$pixi_env/conda-meta/pixi"
    if [ ! -f "$record" ]; then
      echo ""
      return 0
    fi
    python3 -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p,encoding="utf-8")); print(d.get("environment_lock_file_hash","") if isinstance(d,dict) else "")' "$record" 2>/dev/null || echo ""
  }

  _envs_for_stages() {
    local need=() s e ordered=(platform-ci-test platform-dev pyforge-warden)
    for s in "${STAGES[@]}"; do
      case "$s" in
        test) need+=(platform-ci-test platform-dev) ;;
        container) need+=(platform-dev) ;;
        promotion) need+=(platform-ci-test pyforge-warden) ;;
        images) ;;
      esac
    done
    for e in "${ordered[@]}"; do
      local n found=0
      for n in "${need[@]}"; do
        [ "$n" = "$e" ] && found=1 && break
      done
      [ "$found" = 1 ] && echo "$e"
    done
  }

  ensure_envs() {
    local e before after state sync_log rc
    while IFS= read -r e; do
      [ -n "$e" ] || continue
      sync_log="$WORK/env-sync-$e.log"
      before="$(_pixi_env_lock_hash "$e")"
      if ! pixi install --frozen --manifest-path "$ROOT/pixi.toml" -e "$e" 9>&- >"$sync_log" 2>&1; then
        rc=$?
        echo "platform-ci-local: pixi install --frozen failed for ${e} (exit ${rc})" >&2
        echo "last 25 lines of ${sync_log}:" >&2
        tail -25 "$sync_log" >&2
        exit 2
      fi
      after="$(_pixi_env_lock_hash "$e")"
      if [ -z "$before" ]; then
        state=installed
      elif [ -z "$after" ]; then
        state=checked
      elif [ "$before" != "$after" ]; then
        state=synced
      else
        state=current
      fi
      echo "env ${e}: ${state}"
      printf 'INFO\tenv\t%s: %s\n' "$e" "$state" >>"$RESULTS"
    done < <(_envs_for_stages)
    command -v "$ENGINE" >/dev/null 2>&1 || { echo "$ENGINE is not on PATH" >&2; exit 2; }
  }

  start_services() {
    local pgdata="$WORK/pg" i
    stop_services
    _refuse_port_in_use "$PG_PORT" "postgresql"
    _refuse_port_in_use "$REDIS_PORT" "redis"
    rm -rf "$pgdata" "$WORK/redis"; mkdir -p "$WORK/redis"
    "$DEV/initdb" -D "$pgdata" -U postgres --auth=trust 9>&- >"$WORK/initdb.log" 2>&1
    "$DEV/pg_ctl" -D "$pgdata" -l "$WORK/pg.log" -w \
      -o "-c unix_socket_directories='' -h 127.0.0.1 -p $PG_PORT" start 9>&- >/dev/null
    for i in $(seq 1 30); do
      "$DEV/pg_isready" -h 127.0.0.1 -p "$PG_PORT" -U postgres 9>&- >/dev/null 2>&1 && break; sleep 1
    done
    "$DEV/psql" -h 127.0.0.1 -p "$PG_PORT" -U postgres -qc "CREATE DATABASE platform;" 9>&- >/dev/null
    "$DEV/psql" -h 127.0.0.1 -p "$PG_PORT" -U postgres -d platform -qc "CREATE EXTENSION IF NOT EXISTS vector;" 9>&- >/dev/null
    "$DEV/redis-server" --port "$REDIS_PORT" --dir "$WORK/redis" --save "" --appendonly no \
      --daemonize yes --logfile "$WORK/redis.log" --pidfile "$WORK/redis.pid" 9>&- >/dev/null
    echo "services: postgres 127.0.0.1:$PG_PORT, redis 127.0.0.1:$REDIS_PORT (work dir $WORK)"
  }

  trap stop_services EXIT

  stage_test() {
    export DATABASE_URL="postgres://postgres:platform@localhost:$PG_PORT/platform"
    export REDIS_URL="redis://localhost:$REDIS_PORT/0"
    export PATH="$CIT:$DEV:$PATH"
    local py=(env -u PYTHONSAFEPATH python)
    pushd src/platform >/dev/null || exit 2
    step test "Django system checks (PostgreSQL + Redis, no other backing service)" "${py[@]}" manage.py check &&
    step test "Ruff" "$CIT/ruff" check . &&
    step test "Ruff format" "$CIT/ruff" format --check . &&
    step test "Mypy" env -u PYTHONSAFEPATH "$CIT/mypy" platformapp config tests &&
    step test "Policy suite" "${py[@]}" -m pytest tests/policy -q -p no:cacheprovider &&
    step test "sqlmigrate extraction" "${py[@]}" -m db.sqlmigrate_extraction &&
    step test "Full test suite (platformapp app tests, the ASGI seam, and the import boundary)" \
      "${py[@]}" -m pytest -q -p no:cacheprovider
    popd >/dev/null || exit 2
  }

  export_context() {
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
  expect_code() {
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
  langflow_superuser_login() {
    local code body
    code="$(curl -s -o "$WORK/langflow-login.json" -w '%{http_code}' -X POST "http://localhost:$APP_PORT/langflow/api/v1/login" \
      -d 'username=langflow&password=ci-placeholder-not-a-real-secret' || true)"
    echo "POST /langflow/api/v1/login -> $code"
    [ "$code" = "200" ] || { cat "$WORK/langflow-login.json" 2>/dev/null; return 1; }
    body="$(cat "$WORK/langflow-login.json")"
    case "$body" in *'"access_token"'*) return 0 ;; *) echo "missing access_token: $body"; return 1 ;; esac
  }

  stage_container() {
    local common=(-e DJANGO_SECRET_KEY=ci-placeholder-not-a-real-secret -e DJANGO_ADMIN_URL=admin/
      -e COMPONENT_RUNTIME=local -e DATABASE_URL="postgres://postgres:platform@127.0.0.1:$PG_PORT/platform"
      -e REDIS_URL="redis://127.0.0.1:$REDIS_PORT/0")
    if ss -ltn 2>/dev/null | grep -q ":$APP_PORT "; then echo "port $APP_PORT is busy; the image binds it" >&2; return 1; fi
    "$ENGINE" rm -f "$APP" >/dev/null 2>&1 || true
    step container "Migrate the database (the image's CMD deliberately doesn't)" \
      "$ENGINE" run --rm --network host "${common[@]}" "platform:$TAG" python manage.py migrate --noinput &&
    step container "Run platform container ($ENGINE)" "$ENGINE" run -d --name "$APP" --network host "${common[@]}" \
      -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 -e DJANGO_SECURE_SSL_REDIRECT=False \
      -e LANGFLOW_SUPERUSER_PASSWORD=ci-placeholder-not-a-real-secret "platform:$TAG" &&
    step container "Poll /ht/ for 200" poll_ht &&
    step container "Smoke-test an ORM-backed page (proves migrations ran)" expect_code /admin/login/ 200 &&
    step container "Smoke-test a real template page (static manifest + offline compression)" expect_code / 200 &&
    step container "Fetch every static asset the home page references" static_assets &&
    step container "Smoke-test the FastAPI seam (/api/, the other half of the ASGI dispatcher)" expect_code /api/health 200 &&
    step container "Smoke-test the Langflow mount (bare /health, unchanged forward per AD-4)" expect_code /health 200 &&
    step container "Smoke-test Langflow auto-login is refused (/langflow/api/v1/auto_login)" expect_code /langflow/api/v1/auto_login 403 &&
    step container "Smoke-test Langflow credentialed superuser login (/langflow/api/v1/login)" langflow_superuser_login &&
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
  exit 0
}

acquire_run_lock
run_platform_ci_local 9>&-
