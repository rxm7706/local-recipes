---
title: 'Story 20.1: One boot script raises both plane faces (CAP-5)'
type: 'feature'
created: '2026-08-27'
status: 'in-progress'
updated: '2026-08-27'
baseline_revision: '5bae7d330164a14de41ca789d8edefeab858a213'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** the CAP-19 engine's first slice (steward 34.1–34.5) shipped the in-process
DuckDB plane primitives — the single-writer `atlas.duckdb` discipline
(`duckdb_writer.py::connect_writer`/`connect_reader`), the read-only live Postgres attach
(`live_attach.py::attach_postgres_readonly`), and vector persistence (`query_plane_vectors.py`)
— but nothing raises them as a coherent, bootable "plane". There is also no HTTP/Arrow face:
`duckdb-server` (Mosaic's DuckDB server, already reciped at `recipes/duckdb-server`, version
0.30.0) is confirmed absent from every `pixi.toml` today (`stack.md:43`: "Not in `pixi.toml`
until `query-plane-face` is answered"). Filesystem-less consumers (DB-GPT/Langflow estate
reads, live console queries) have no face to bind to at all.

**Approach:** the 2026-08-26 `query-plane-face` operator ruling answered this as "both, one
boot script": add ONE new pixi-sourced boot script/module in `pyforge-atlas` that (1) always
raises the in-process library face by opening `atlas.duckdb` through the existing
`connect_reader`/`connect_writer` seam (never a second writer, never a second `.duckdb` file),
and (2) launches the Mosaic `duckdb-server` HTTP/Arrow process from the SAME script, but only
when a platform-stack-up signal is present — degrading to library-face-only with a structured
notice (never a crash) when the stack is down. Add `duckdb-server` as a new
`[feature.pyforge-atlas.dependencies]` entry (it is not there today) and a new pixi task
exposing the boot script, mirroring the existing `kedro-test`/`duckdb-singularity` task shapes.
Prove there is exactly one launch site with a grep-verifiable gate, mirroring the F1
`tests/singularity/test_duckdb_sole_engine.py` AST-scan style.

## Acceptance Criteria

Lifted verbatim from `epics.md` (Story 20.1):

> **Given** the shipped CAP-19 engine (steward 34.1–34.5) **When** the single pixi-sourced boot
> script runs **Then** the in-process library face is available by default (AD-16 local-first;
> DuckDB stays a query face, never a fourth backing store) **And** the Mosaic `duckdb-server`
> HTTP/Arrow face is raised by the SAME script only when the platform stack is up — with the
> stack down it degrades to library-face-only with a structured notice, never a crash **And**
> no second boot path exists (grep-verifiable: exactly one `duckdb-server` launch site)
> (`query-plane-face` ruling, 2026-08-26).

## Boundaries & Constraints

**Always:** `BMAD_ACTIVE_PROJECT=pyforge-atlas` when resolving BMAD config; ledger key
`20-1-one-boot-script-raises-both-plane-faces`; the library face is available by default in
every environment (AD-16 local-first) — the HTTP/Arrow face is strictly additive, never a
replacement; reuse `duckdb_writer.py::connect_writer`/`connect_reader` verbatim for the library
face — never mint a second writable `.duckdb`; if the boot script needs to preflight an OLTP
attach, reuse `live_attach.py::attach_postgres_readonly`'s LOAD-only-never-INSTALL discipline
rather than inventing a second attach path; the boot script is the ONE and ONLY place that
launches `duckdb-server` — provable by grep/AST, mirroring
`tests/singularity/test_duckdb_sole_engine.py`'s `_sqlite_hits`-style scan.

**Block If:** raising the HTTP/Arrow face would require a network `INSTALL` of a DuckDB
extension at boot rather than `LOAD` from a pre-provisioned local cache (mirrors AD-13 /
`live_attach.py`'s existing LOAD-only discipline) — report and stop; this needs an operator
decision on extension provisioning, not a silent `INSTALL`.

**Never:** open a second writable `.duckdb` file; make `duckdb-server` a hard requirement (it
is optional, raised only when the platform stack is up); crash when the platform stack is down
(the contract is graceful degrade + a structured notice); implement the face-parity gate
(Story 20.2 — depends on this story); implement the dashboard-store pipeline (Story 20.3) or
the CIS spine specs (Story 20.4) here.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| STACK_DOWN | no platform-stack-up signal present | library face raised; structured "HTTP face not raised: stack down" notice | no exception, no crash |
| STACK_UP | platform-stack-up signal present, `duckdb-server` provisioned | both faces raised; boot returns handles/endpoints for each | no exception |
| MISSING_PROVISIONING | stack up but the `duckdb-server` binary or its extension cache is absent | boot fails loud with a typed error naming the missing provisioning step | never falls back to a silent network `INSTALL` |
| SECOND_BOOT_INVOCATION | boot script invoked a second time while the first still holds the writer lock | second invocation's library-face open is refused | `SecondWriterRefused` (existing `duckdb_writer.py` behavior), not a new error type |

</intent-contract>

## Code Map

Verified against the live tree 2026-08-27 (worktree HEAD `5bae7d3301`):

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/duckdb_writer.py` — the seam to reuse
  verbatim: `connect_writer` (filelock timeout=0 → `SecondWriterRefused` BEFORE
  `duckdb.connect`), `connect_reader` (read_only, no lock), `LockedDuckDB` (releases lock on
  `close()`), `ATLAS_DUCKDB_NAME = "atlas.duckdb"`, `_require_atlas_path` (rejects any other
  filename). Second-boot refusal comes from the filelock, so it holds regardless of DuckDB's
  own file lock.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/live_attach.py` — the
  LOAD-only-never-INSTALL shape to mirror: `_disable_extension_network` (SET
  autoinstall/autoload false), `load_postgres_offline` → `PostgresNotProvisionedError`
  (subclass of `PyforgeError, RuntimeError` from `pyforge.core.errors`) with an error message
  that names the provisioning step. New `DuckDBServerNotProvisionedError` mirrors this exactly.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_vectors.py` — existing
  plane-writer consumers (`open_plane_rag_store`, `extract_real_arrays_onto_plane`); both open
  via `connect_writer` and validate `ATLAS_DUCKDB_NAME`. The boot module must follow the same
  path-validation + caller-owns-handle conventions.
- `src/shared/packages/pyforge-atlas/tests/singularity/test_duckdb_sole_engine.py` — the
  AST-scan style to mirror: `ATLAS_SRC` root resolution via
  `importlib.import_module("pyforge.atlas").__file__`, `_sqlite_hits` walking `ast.Import`/
  `ast.ImportFrom`/dynamic `import_module` calls, offenders dict keyed by relative path, plus a
  POSITIVE assertion pinning the one legitimate site (its
  `test_the_only_legacy_sqlite_reader_is_the_parity_comparator_in_tests` pattern).
- `src/shared/packages/pyforge-atlas/tests/test_one_duckdb_writer.py` and
  `tests/test_read_only_live_attach.py` — fixture conventions: `tmp_path / ATLAS_DUCKDB_NAME`,
  skip/fail guards for unprovisioned externals (`requires_postgres_ext` skipif; `_pg_bindir`
  candidate probing incl. `.pixi/envs/<env>/bin`), free-port helper, `subprocess.run` with
  fixed argv + `# noqa: S603` comment style.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/trending_candidates/__main__.py:188` —
  the existing one-line JSON envelope stdout convention (`print(json.dumps(envelope))`) the
  boot CLI's structured notice follows; NFR-6 exit codes per project-context (0 pass / 1 policy
  fail / 2 error / 130 interrupted; indeterminate → 1).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py` — the station CLI routes
  into Kedro; the boot script is NOT wired into it (no Kedro coupling) — expose via
  `python -m pyforge.atlas.query_plane_boot` only, matching the
  `trending-candidates`/`trending-handoff` task pattern.
- `recipes/duckdb-server/recipe.yaml` — local recipe at 0.30.0; conda-forge feedstock is live
  (`cfe-on-conda-forge-status: confirmed-on-conda-forge`, deployed line noted at 0.27.0, v0).
  Entry point `duckdb-server = pkg.__main__:serve`; the import package is `pkg`, NOT
  `duckdb_server` (recipe G7 note). Floor for the pixi pin must be confirmed against what
  actually solves (`>=0.27.0` expected).
- `pixi.toml` — `[feature.pyforge-atlas.dependencies]` (line ~1938: pyforge path deps +
  commented per-story dep entries — follow that comment style) and the task blocks
  (`kedro-test` ~1978, `duckdb-singularity` ~2027) to mirror for the new dep + task.
- No existing stack-up signal exists anywhere (`grep -riE "stack.?up|PLATFORM_STACK"` over
  `src/shared/packages` + `src/platform` — zero hits): the signal is minted here as an explicit
  input (see Design Notes), not probed from the Django/compose stack.

## Tasks & Acceptance

**Execution:**

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_boot.py` -- NEW module: the
  one boot script. `DuckDBServerNotProvisionedError(PyforgeError, RuntimeError)`;
  `stack_is_up(override: bool | None) -> bool` resolving explicit arg first, else env
  `PYFORGE_PLATFORM_STACK_UP` (truthy: 1/true/yes/on); `PlaneBoot` result object carrying
  `library` (the `LockedDuckDB` from `connect_writer`), `http` (endpoint + process handle, or
  `None`), and `notices` (list of structured dicts); `boot_query_plane(path, *, stack_up=None,
  host="127.0.0.1", port=…, launcher=None)` implementing the I/O matrix: always
  `connect_writer(path)` first (SECOND_BOOT via existing `SecondWriterRefused`); stack down →
  return with notice `{"event": "http-face-not-raised", "reason": "stack-down", …}`; stack up →
  preflight the `duckdb-server` executable (absence → close library handle, release lock, raise
  the typed provisioning error naming the pixi provisioning step — never any `INSTALL`);
  exactly ONE `subprocess.Popen` launch site in the whole atlas surface. CLI `main()` +
  `if __name__ == "__main__"` guard: boots, prints one-line JSON envelope(s); with the HTTP
  face up it stays foreground supervising the server (SIGINT → clean shutdown, exit 130); typed
  refusals exit 1, crashes 2, otherwise 0 -- RATIONALE: the `query-plane-face` ruling's "both,
  one boot script", CAP-5.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_boot.py` (same file, bind at
  implement time) -- after `pixi install -e pyforge-atlas` lands `duckdb-server`, read the
  installed `pkg/__main__.py`/server source in the env's site-packages to bind the REAL launch
  argv (db path arg shape, port flag, socketify bind) and its DB open mode; if the server holds
  a persistent read-write connection that cannot coexist with the live plane writer, record the
  chosen handling in Design Notes (e.g. server gets the path, queries fail-fast while a writer
  transaction holds — parity proof is Story 20.2's) rather than silently guessing -- RATIONALE:
  never bind a subprocess contract from training data.
- `pixi.toml` -- add `duckdb-server` to `[feature.pyforge-atlas.dependencies]` with a
  per-story comment (house style at line ~1938) and floor confirmed by the solve; add
  `[feature.pyforge-atlas.tasks.query-plane-boot]` (`cmd = "python -m
  pyforge.atlas.query_plane_boot"`, description citing Story 20.1 / CAP-5 / the 2026-08-26
  ruling + NFR-6 exit codes, mirroring `trending-candidates`'s shape); run the solve so
  `pixi.lock` updates -- RATIONALE: "pixi-sourced" is part of the AC; `stack.md:43`'s gate is
  now answered.
- `environment.yaml` -- regenerate via `pixi project export conda-environment -e build >
  environment.yaml` after the `pixi.toml` edit (the sync check is UNGATED by the maintenance
  label) -- RATIONALE: repo-wide always-on PR gate.
- `docs/reference/library-llms-full.md` -- run `pixi run -e local-recipes llms-full-check`; if
  it reports drift from the new dependency, add the `duckdb-server` catalog entry (import name
  `pkg`, env membership `pyforge-atlas`) per the file's regeneration header -- RATIONALE:
  project-context Rule 1: `llms-full-check` must pass after any dependency change.
- `src/shared/packages/pyforge-atlas/tests/test_query_plane_boot.py` -- NEW: unit-test every
  I/O-matrix row offline: STACK_DOWN (library usable via a real `SELECT`, `http is None`,
  notice dict has stable `event`/`reason` keys, no exception); STACK_UP with an injected fake
  `launcher` (records argv; both handles returned); MISSING_PROVISIONING (signal up, executable
  resolution forced to fail, no launcher → typed error raised AND the writer lock was released
  — a follow-up `connect_writer` succeeds); SECOND_BOOT_INVOCATION (first boot open → second
  raises `SecondWriterRefused`); env-signal parsing (unset/0/1). Use `tmp_path /
  ATLAS_DUCKDB_NAME`, monkeypatch for env -- RATIONALE: the matrix is the contract.
- `src/shared/packages/pyforge-atlas/tests/singularity/test_one_duckdb_server_launch_site.py`
  -- NEW: the grep/AST gate. AST-walk every `*.py` under the installed `pyforge/atlas` surface
  (same `ATLAS_SRC` resolution as `test_duckdb_sole_engine.py`): (a) any module containing a
  subprocess-launch call (`subprocess.Popen`/`run`/`call`/`check_*`, `os.exec*`/`os.spawn*`/
  `os.system`) whose AST also references the string constant `"duckdb-server"` must be exactly
  `query_plane_boot.py`; (b) within `query_plane_boot.py` exactly ONE launch call site exists
  (positive assertion, comparator-pinning style); (c) the boot module's AST contains no SQL
  `INSTALL` string reaching an `.execute` call (string/AST gate, per spec-34-1's precedent) --
  RATIONALE: "no second boot path exists (grep-verifiable)".
- `src/shared/packages/pyforge-atlas/tests/test_query_plane_boot.py` (same file, guarded) --
  real-binary smoke, `pytest.mark.skipif(shutil.which("duckdb-server") is None, …)`: boot with
  the signal up on a tmp plane, poll the endpoint (free-port helper pattern from
  `test_read_only_live_attach.py`), assert the process is alive and the endpoint is returned,
  then shut down cleanly -- RATIONALE: proves the pixi-sourced binary actually launches from
  the one site; stays green (skip) in envs without the dep.

**Acceptance Criteria:**

- Given the epics.md AC block above (lifted verbatim), when `pixi run -e pyforge-atlas
  query-plane-boot` runs with no stack signal, then it exits 0 having raised the library face
  and printed the structured stack-down notice.
- Given the new dep landed, when `pixi run -e pyforge-atlas duckdb-singularity` runs, then both
  the existing sole-engine gate AND the new one-launch-site gate pass.
- Given the full atlas suite, when `pixi run -e pyforge-atlas kedro-test` runs, then it is
  green (no regression in the 34.1–34.5 plane tests).

## Spec Change Log

- **2026-08-27 (resume pass — the 09:37 dev session died on the account usage limit; work
  preserved as wip commit `9ce94fb846`, resumed by redispatch):** code + tests + pixi
  dep/task/lock were already landed in the wip commit. This pass completed the outstanding
  tasks: (1) the Design Notes record of the bound subprocess contract, the eager-read-write
  yield handling, and the linux-64 dep scoping — the boot module and tests cited "recorded in
  the story spec's Design Notes" but the record was missing; (2) the `duckdb-server` catalog
  entry in `docs/reference/library-llms-full.md` (§ 6 entry + § 17 gotcha `pkg` + env-table
  row + header note; `llms-full-check` now clean); (3) `environment.yaml` re-export —
  byte-identical, the `build` env does not include the pyforge-atlas feature; (4) fixed the
  stale urllib mention in `tests/catalog/conftest.py`'s exemption comment. Verification this
  pass: story tests + both singularity gates green; full `kedro-test` = 1258 passed / 3 failed
  / 2 errors — all five confirmed pre-existing at baseline `5bae7d3301` (SKF marker in
  CLAUDE.md, sprint-ledger key drift, MCP pipeline-name drift, missing pg binaries in this
  lean worktree; none touch this story's files); CLI exercised live: stack-down exit 0 +
  notice, SecondWriterRefused exit 1, stack-up both faces + HTTP query served + SIGINT
  exit 130.

## Review Triage Log

## Design Notes

- **Stack-up signal (minted here):** no probe of the compose/Django stack exists in atlas and
  the host/atlas boundary forbids inventing one casually (host never imports `pyforge.*`; atlas
  has zero `src/platform/` coupling today — verified by grep). The signal is therefore an
  explicit input: `boot_query_plane(stack_up=…)` wins, else env `PYFORGE_PLATFORM_STACK_UP`.
  Absence of the signal IS "stack down" (I/O row 1). A live health probe can be wired into the
  same parameter later without changing this contract.
- **Why the library face is the writer handle:** the SECOND_BOOT row pins refusal to
  `SecondWriterRefused`, which only `connect_writer` raises (filelock timeout=0, acquired
  before `duckdb.connect`). The boot is therefore the plane's single writer while it lives;
  readers keep using `connect_reader` independently.
- **Provisioning preflight ≠ INSTALL:** mirror `load_postgres_offline`'s message discipline —
  the typed error names the exact provisioning step ("add/install the pyforge-atlas pixi env,
  which carries duckdb-server"), and the boot never shells out to any installer. If
  implementation discovers the server itself requires a DuckDB extension `INSTALL` at boot,
  that is the contract's Block-If: HALT blocked, do not work around.
- **CLI semantics:** stack-down CLI boots, emits the notice envelope, releases and exits 0 (the
  library face is in-process — holding it in a foreground CLI serves no other process);
  stack-up CLI stays foreground as the server's supervisor. The API (`boot_query_plane`) hands
  both handles to the caller, who owns closing them.
- **Bound subprocess contract (implement-time, from the INSTALLED duckdb-server 0.31.0 — never
  training data):** `pkg/__main__.py::serve` reads exactly ONE optional positional
  (`sys.argv[1]`, default `":memory:"`) — the launch argv is `duckdb-server <db_path>`, nothing
  else. There is NO port flag and NO host flag: `pkg/server.py::server` hard-codes
  `app.listen(3000, …)` (socketify), so `DEFAULT_PORT = 3000` and a real launch with any other
  `port=` fails loud (`ValueError`) rather than reporting an endpoint that points nowhere. The
  server requires no extension `INSTALL` at boot (`duckdb.connect(db_path)` + query handlers
  only), so the Block-If did not trigger. Consequence for the real-binary smoke: the
  free-port-helper pattern cannot pick the server's port; the guard is availability of the fixed
  port 3000, else skip.
- **Chosen handling: the server's eager read-write open vs the live plane writer.** The
  installed server opens the path eagerly, READ-WRITE, at startup — and duckdb 1.5.5 refuses
  ANY second cross-process open (read-only or read-write) while a read-write connection is held
  (verified live 2026-08-27; the `file:…?access_mode=read_only` URI form is not accepted). The
  two faces therefore cannot both hold live DuckDB connections on the same file. Handling
  (recorded here per this spec's Tasks, not silently guessed): on the stack-up path the boot
  closes only the raw in-process connection (`library._con.close()`) BEFORE launching the
  server, KEEPING the `atlas.duckdb.writer.lock` filelock held for the boot's whole lifetime —
  `SecondWriterRefused` still guards the plane against any other pyforge writer while the HTTP
  face lives, and the server is the plane's sole DuckDB holder. A `library-face-yielded` notice
  (`reason: duckdb-single-process-lock`) makes the yield structured and visible; re-close on
  `library.close()` is a no-op. Row-for-row parity proof across the faces is Story 20.2's, per
  the Never section.
- **Pixi dep scoping (implement-time, from the solve):** `duckdb-server` itself is noarch but
  hard-deps `socketify`, which conda-forge ships only for linux-64/osx-64 — so the dep lands in
  `[feature.pyforge-atlas.target.linux-64.dependencies]` (cross-platform placement broke the
  osx-arm64/win-64 solves). On other platforms the boot's provisioning preflight raises the
  typed `DuckDBServerNotProvisionedError` instead — never a silent INSTALL. Floor `>=0.27.0`
  confirmed against the solve (conda-forge carries 0.27.0–0.31.0; 0.31.0 resolved).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` -- expected: green, including the two new test files.
- `pixi run -e pyforge-atlas duckdb-singularity` -- expected: green (sole-engine + new
  one-launch-site gates).
- `pixi run -e pyforge-atlas query-plane-boot` (no signal env) -- expected: exit 0, one-line
  JSON stack-down notice on stdout.
- `pixi run -e local-recipes llms-full-check` -- expected: exit 0 after the catalog reconcile.

**Manual checks (if no CLI):**
- `git diff pixi.toml` shows exactly one new dependency line + one new task block under the
  pyforge-atlas feature; `pixi.lock` + `environment.yaml` regenerated in the same commit.
