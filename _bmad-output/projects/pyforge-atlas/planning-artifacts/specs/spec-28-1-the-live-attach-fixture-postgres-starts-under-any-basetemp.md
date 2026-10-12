---
title: '28.1: The live-attach fixture Postgres starts under any basetemp'
type: 'fix'
created: '2026-10-11'
status: 'done'
baseline_revision: bc9cad54103b784381fc1579251b22a52e487f96
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the fixture Postgres behind the live-attach tests cannot start when pytest's basetemp is long, so
pr-preflight's `pyforge-atlas-test` lane goes red on two setup errors. Line numbers below are at `2b5e0d649b`.

- **What the fixture does.** `fixture_postgres` (`tests/unit/test_read_only_live_attach.py:88-:209`) finds a
  PostgreSQL bin dir (`_pg_bindir`, :49-:66), runs `initdb` into `tmp_path / "pgdata"`, makes `sock_dir = tmp_path /
  "pgsock"` (:98-:99), and starts the server with `pg_ctl -o "-p {port} -h 127.0.0.1 -k '{sock_dir}' -c fsync=off ..."`
  (:113-:125). It then waits on `pg_isready -h 127.0.0.1`, seeds two schemas with `psql -h 127.0.0.1`, and yields the DSN
  `dbname=postgres user=postgres host=127.0.0.1 port={port}`. `test_federated_read_across_two_schemas` (:329-:339) and
  `test_write_through_attach_is_refused` (:342-:352) use it.
- **Why it fails.** PostgreSQL puts its Unix socket at `<sock_dir>/.s.PGSQL.<port>` and refuses a path longer than 107
  bytes (the AF_UNIX `sun_path` limit). When it cannot create any Unix socket it exits, so `pg_ctl start` returns 1 and
  the fixture raises `CalledProcessError` at setup. pr-preflight runs each lane with `--basetemp=<lane scratch>/pytest-basetemp`
  and sets `TMPDIR` to the lane scratch (`pyforge/steward/preflight.py::_lane_scratch_env`), and `pyforge-atlas-test`
  runs under `pytest-xdist`, which adds a `popen-gw<N>/` segment; the socket path crosses 107 bytes.
- **Why it surfaced only now.** In a fresh worktree `_pg_bindir` finds no `initdb`/`pg_ctl` and the fixture skips. The
  tests run only once an env carrying PostgreSQL is reachable (`PYFORGE_PG_BINDIR`, `pg_ctl` on `PATH`, or the
  worktree's `platform-dev` / `local-recipes` / `pyforge-atlas` env).

**Evidence:**
- **Warden 16.1's fix pass.** `pixi run -e pyforge-guild pr-preflight -- --keep-going` on 2026-10-11: the
  `pyforge-atlas-test` lane red with 2 setup errors in `test_read_only_live_attach.py`.
- **Reproduced on `2b5e0d649b`** (2026-10-11): `PYFORGE_PG_BINDIR=<platform-dev>/bin pixi run --frozen -e pyforge-atlas
  python -m pytest src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py -q -p no:cacheprovider
  --basetemp=<a 214-byte path>` exits 1, "5 passed, 2 errors". Each `pg.log` (PostgreSQL 17.11) reads
  `Unix-domain socket path ".../test_federated_read_across_two0/pgsock/.s.PGSQL.48343" is too long (maximum 107 bytes)`,
  then `WARNING: could not create Unix-domain socket in directory ...`, then `FATAL: could not create any Unix-domain
  sockets`. With a short basetemp the same file passes 7 of 7.
- **The fix shape, proven on a scratch copy** (the tracked file untouched): with `sock_dir` dropped and `-k
  '{sock_dir}'` replaced by `-c unix_socket_directories=''`, the same command passed 7 of 7 under a 214-byte basetemp.
  Each `pg.log` shows only `listening on IPv4 address "127.0.0.1"`, no `.s.PGSQL.*` file exists under the basetemp, and
  `pg_ctl ... stop` still shuts the server down. With no PostgreSQL binaries reachable the copy reported "5 passed, 2
  skipped" with the fixture's existing reason.
- **The alternative, also proven:** a socket dir from `tempfile.mkdtemp(prefix="pgs", dir="/tmp")`, removed in the
  `finally`, also passed 7 of 7 and left no `/tmp/pgs*` behind. It is not this story's shape (see Boundaries).

**Approach:** the fixture opens no Unix socket.
- In `fixture_postgres`, delete `sock_dir = tmp_path / "pgsock"` and `sock_dir.mkdir()`, and replace `-k '{sock_dir}'`
  in `options` with `-c unix_socket_directories=''`. Every other option, the `initdb` call, the wait loop, the seed SQL,
  the `pgvector` assertion, the DSN and both `pg_ctl ... stop` calls stay as they are.
- Nothing else needs a socket: `pg_ctl start -w` and `pg_ctl stop` read `postmaster.pid`, and `pg_isready`, `psql` and
  the yielded DSN all name `-h 127.0.0.1` / `host=127.0.0.1`.
- A one-line comment at the option says why: the fixture talks TCP only, and a socket under `tmp_path` overflows the
  107-byte AF_UNIX limit under a long basetemp.

Ledger key: `28-1-the-live-attach-fixture-postgres-starts-under-any-basetemp`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-6** (one engine for compute, graph and vector). The read-only `ATTACH` joins a Postgres
  into the one DuckDB plane and never mints a second writable file (AD-4); these two tests prove that join and the
  refused write. This story makes their fixture start reliably. It changes no behaviour CAP-6 names, so it needs no new
  CAP and no `SPEC.md` change.
- **`spec-pyforge-unifying-strategy` CAP-19** (canopy:FR-46, read-only live attach). Steward Story 34.1 shipped the
  test under it; its `verified:` line cites this file. The CAP's text does not change.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag, and this one changes only a test fixture.
- **Origin.** `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-11 (live-attach fixture socket path)
  entry. The operator asked for it in session: "Do this task here: Fix atlas live-attach test socket path overflow".

## Acceptance Criteria

- **AC1 — The two tests pass under a long basetemp.** **Given** PostgreSQL binaries reachable through
  `PYFORGE_PG_BINDIR` and a pytest `--basetemp` longer than 107 bytes, **When**
  `test_read_only_live_attach.py` runs, **Then** it exits 0 with "7 passed": `test_federated_read_across_two_schemas`
  and `test_write_through_attach_is_refused` pass, neither skips, and `-rs` prints no skip line.
- **AC2 — No Unix socket.** **Given** the AC1 run, **Then** the `options` string `fixture_postgres` hands `pg_ctl`
  contains `-c unix_socket_directories=''` and no `-k`; the fixture creates no socket directory; no `.s.PGSQL.*` file
  exists anywhere under the basetemp afterwards; and every `pg.log` under it has a `listening on IPv4 address
  "127.0.0.1"` line and no `Unix-domain socket` / `Unix socket` line.
- **AC3 — Still skips without PostgreSQL.** **Given** no candidate `_pg_bindir` checks holds all four of `pg_ctl`,
  `initdb`, `psql` and `pg_isready` (`PYFORGE_PG_BINDIR` unset, none on `PATH`, none in `CONDA_PREFIX` or the worktree's
  `platform-dev` / `local-recipes` / `pyforge-atlas` envs), **When** the file runs, **Then** it exits 0 with "5 passed, 2
  skipped", and both skip reasons are the fixture's existing `fixture Postgres needs initdb/pg_ctl ...` text.
- **AC4 — Never weakened.** The diff adds no `skip`, `skipif`, `xfail`, `importorskip`, rerun marker or rerun plugin.
  `requires_postgres_ext`, `_pg_bindir`, the two tests' bodies, their assertions, `live_attach.py` and
  `duckdb_writer.py` keep every line.
- **AC5 — Only the test file moves.** `git diff origin/main...HEAD --stat`, outside `_bmad-output/` and
  `scripts/.spec-surface-baseline.json`, names only `src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py`.
- **AC6 — Mutation: a socket under `tmp_path` reds AC1.** With `sock_dir = tmp_path / "pgsock"`, `sock_dir.mkdir()`
  and `-k '{sock_dir}'` restored in place of `-c unix_socket_directories=''`, the AC1 command exits 1 with "5 passed, 2
  errors", and a `pg.log` names `too long (maximum 107 bytes)`. The change is reverted afterwards, and the spec's Auto Run
  Result records the red run.
- **AC7 — The station suite is green.** `pixi run -e pyforge-atlas kedro-test` and
  `pixi run -e pyforge-atlas kedro-catalog-check` exit 0.
- **AC8 — The surface is reconciled.** The `spec-pyforge-atlas` and `spec-pyforge-unifying-strategy` memlogs each get a
  surface-reconcile entry naming the test file and this story; each Spec is stamped scoped (`--spec
  pyforge-atlas/spec-pyforge-atlas`, `--spec pyforge-steward/spec-pyforge-unifying-strategy`), and
  `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Change only `fixture_postgres` in `src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py`, plus
  this story's memlog entries and scoped stamps.
- Start a real PostgreSQL server for the two tests, as Story 34.1 requires; never mock it.
- Keep the gate fixture-based, local and non-credentialed (NFR-1, AD-11).

**Never:**
- Never weaken the tests: no skip, `xfail`, rerun, softened assertion or shortened test (AC4).
- Never shorten the basetemp, change `pixi.toml`'s `pyforge-atlas-test`, or change pr-preflight's per-lane scratch to
  make the fixture fit. The fixture must start under any basetemp.
- Never take the short-`/tmp`-socket-dir alternative as this story's shape. It still depends on a path length, needs
  cleanup on every early exit (`initdb` or `pg_ctl start` raising), and must pass `dir=` explicitly because
  pr-preflight's `TMPDIR` is the lane's long scratch. Use it only if the TCP-only shape fails, and then record the
  failing evidence in the Spec Change Log first.
- Never change `live_attach.py`, `duckdb_writer.py`, `src/platform/` or any other station's code.

**Residual risk:**
- `_free_port` (:69-:72) closes its probe socket before `pg_ctl start` binds the port, so another process could take
  it in between. That race is unchanged by this story and has never been observed; it is out of scope.
- A PostgreSQL build that rejects an empty `unix_socket_directories` would fail AC1 loudly at `pg_ctl start`, never
  silently. PostgreSQL 17.11 (platform-dev, the estate's pin) accepts it.

## I/O & Edge-Case Matrix

| Situation | Today (`2b5e0d649b`) | After |
|---|---|---|
| PostgreSQL binaries present, basetemp > 107 bytes (pr-preflight) | 2 setup errors: socket path too long, `FATAL`, lane red | 7 passed, TCP only |
| PostgreSQL binaries present, short basetemp | 7 passed, socket under `tmp_path` | 7 passed, no socket |
| No PostgreSQL binaries reachable (fresh worktree) | 2 skipped with the fixture's reason | unchanged |
| DuckDB `postgres` extension not in the local cache | 2 skipped (`requires_postgres_ext`) | unchanged |
| `pg_ctl start` fails for another reason | immediate stop, error raised | unchanged |
| A system Postgres already on `/tmp/.s.PGSQL.5432` | no clash (own socket dir) | no clash (no socket; TCP port from `_free_port`) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-6 (one engine for compute, graph and vector; AD-4). The test was
  shipped by steward Story 34.1 under `spec-pyforge-unifying-strategy` CAP-19 (canopy:FR-46). No CAP is minted, and no
  `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-11 (live-attach fixture socket path) entry.
- Epic: Epic 28 (new). No atlas epic owns the test: atlas mints none of `spec-pyforge-unifying-strategy` CAP-19's
  stories (epics.md § Validation note — 2026-08-26). `epic-28` and `epic-28-retrospective` are minted with it.
- Ledger key: `28-1-the-live-attach-fixture-postgres-starts-under-any-basetemp`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Spec: the `spec-pyforge-atlas` memlog records the operator's ask, the evidence and design, and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."28"` (added with this mint) covers the test file, the atlas planning
  specs, the ledger, `scripts/.spec-surface-baseline.json` and every Spec memlog.
- Minted 2026-10-11 in one chain commit.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding). In a dispatch worktree with no PostgreSQL env the two fixture-backed tests skip there (AC3's path), so this gate proves AC7, not AC1.
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- AC1 and AC2, from the repo root, with `BINDIR` set to an env `bin` that holds `pg_ctl`, `initdb`, `psql` and `pg_isready` (for example `.pixi/envs/platform-dev/bin` after `pixi install --frozen -e platform-dev`): `B="${TMPDIR:-/tmp}/atlas-28-1-$(printf 'x%.0s' $(seq 1 120))"; PYFORGE_PG_BINDIR="$BINDIR" pixi run --frozen -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py -q -p no:cacheprovider -rs --basetemp="$B"` — expected: exit 0, "7 passed", no skip line. Then `find "$B" -name '.s.PGSQL.*'` — expected: no output; and `grep -l 'listening on IPv4 address "127.0.0.1"' $(find "$B" -name pg.log)` lists every `pg.log` while `grep -l 'Unix-domain socket\|Unix socket' $(find "$B" -name pg.log)` lists none.
- AC3, in a worktree with no PostgreSQL env: `env -u PYFORGE_PG_BINDIR pixi run --frozen -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py -q -p no:cacheprovider -rs` — expected: exit 0, "5 passed, 2 skipped", both reasons the fixture's existing text.
- AC6, the mutation, on a scratch copy of the file or reverted before the next commit (the harness auto-checkpoint commits the tree): restore `sock_dir` and `-k '{sock_dir}'`, rerun the AC1 command — expected: exit 1, "5 passed, 2 errors", a `pg.log` naming `too long (maximum 107 bytes)`.
- AC4 and AC5: `D="$(mktemp)"; git diff origin/main...HEAD -- src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py > "$D"; grep -cE '^\+.*(skip|xfail|rerun)' "$D"` — expected: `0`; `git diff origin/main...HEAD --stat` — expected: AC5's one code path.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the two memlog entries and scoped stamps (AC8).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-11: minted from the operator's ask "Do this task here: Fix atlas live-attach test socket path overflow".
  `type: fix`, no flag, no CAP; bound to `spec-pyforge-atlas` CAP-6, with the test's origin in
  `spec-pyforge-unifying-strategy` CAP-19 (steward Story 34.1).

## Review Triage Log

### 2026-10-11 — Review pass
- verdicts: 10 findings — high 0, medium 0, low 0, false 6, reject 4
- findings:
  - `[false]` `[reject]` Intent-contract line numbers still describe `-k` / `sock_dir` — mint-time snapshot inside read-only `<intent-contract>`; post-fix behavior is covered by ACs and Auto Run Result, not editable here.
  - `[false]` `[reject]` Story spec frontmatter still `ready-for-dev` / missing Auto Run Result at review start — addressed in this finalize pass, not a code defect.
  - `[false]` `[reject]` No automated AC2 assertion for `.s.PGSQL.*` — spec AC5 limits changes to `fixture_postgres` only; AC2 verified manually in this run (0 sockets, 2 IPv4 pg.log lines).
  - `[false]` `[reject]` AC6 mutation not in diff — executed in-session: MUT_EXIT 1, pg.log `too long (maximum 107 bytes)`; file restored before commit.
  - `[false]` `[reject]` No meta-test forbidding `-k` in fixture — out of intent scope (AC4 forbids weakening; AC6 mutation is the oracle).
  - `[false]` `[reject]` Memlog lacks verbatim pytest output — reconcile entries name the path; verification recorded under Auto Run Result.
  - `[false]` `[reject]` Baseline diff includes herald paths — co-governor scoped stamp for `spec-pyforge-unifying-strategy`, not atlas behavior change.
  - `[false]` `[reject]` Epic 28 mint artifacts absent from diff — landed in prior chain commit `bc9cad5410` on branch, not this fix hunk.
  - `[false]` `[reject]` Fixture docstring omits TCP-only rationale — inline comment at `pg_ctl` options satisfies spec approach; docstring change not required.
  - `[false]` `[reject]` I/O matrix “Today” column still mentions socket under `tmp_path` — historical “before” column by design; “After” row already says TCP only.

## Auto Run Result

Status: done

**Summary:** `fixture_postgres` starts PostgreSQL with TCP only (`-c unix_socket_directories=''`), removing `pgsock` and `-k` so long pr-preflight `--basetemp` paths no longer hit the 107-byte AF_UNIX limit.

**Files changed:**
- `src/shared/packages/pyforge-atlas/tests/unit/test_read_only_live_attach.py` — TCP-only `pg_ctl` options and comment.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md` — Story 28.1 surface reconcile.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` — co-governor surface reconcile (CAP-19 test origin).
- `scripts/.spec-surface-baseline.json` — scoped stamps for both specs.

**Review:** 0 patches applied; 10 findings rejected as false/out-of-scope; follow-up review not recommended.

**Verification:**
- AC1/AC2: 7 passed, long basetemp (~120 x), `PYFORGE_PG_BINDIR=.pixi/envs/pyforge-scribe-pg/bin`; 0 `.s.PGSQL.*`; 2/2 pg.log IPv4 listen, 0 Unix-socket errors.
- AC3: 5 passed, 2 skipped (fixture skip text unchanged).
- AC6: mutation restored `-k` → exit 1, 5 passed 2 errors, pg.log `too long (maximum 107 bytes)`; restored fix.
- AC7: `kedro-test` 103 passed; `kedro-catalog-check` 69 passed.
- AC4/AC5: 0 new skip/xfail/rerun lines; code diff only test file outside memlogs/baseline.
- `lint-types` exit 0; `python scripts/spec_surface_reconcile.py` exit 0; `spec-surface-check` exit 0; `detectors-ci` exit 0.

**Residual risk:** `_free_port` race unchanged (spec out of scope). PostgreSQL must accept empty `unix_socket_directories` (verified on estate PostgreSQL 17.x via scribe-pg env).
