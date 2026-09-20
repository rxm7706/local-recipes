---
title: 'Httpx opener and rehearsal (CAP-2, CAP-3)'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 2
followup_review_recommended: true
context: []
warnings: ['oversized']
difficulty: ''
baseline_revision: '4fe2dd25982b535702c0db497bb6661f098cde56'
final_revision: '3fa35bb8cc08d75ed4c965ae3ebe4d66bcfc2cab'
---

<intent-contract>

## Intent

**Problem:** `factory/lasuite.py`'s sole network seam (`Opener`) has never been driven by a real
HTTP client — only `MockWagtail`. Nobody has proven the real `httpx`-backed opener actually
satisfies the same create/update/idempotent-skip/resume contract `test_lasuite.py` proves against
the mock, and the later ATTENDED DW-H3 session has no concrete script or checklist to run.

**Approach:** Add a real httpx-backed `Opener` builder + CLI entrypoint OUTSIDE package code
(`tools/lasuite_bringup.py`, reusable unchanged by the future attended session), and a new
offline-safe rehearsal test that stands up a tiny loopback HTTP stub implementing `MockWagtail`'s
same four routes, then reproduces the exact four-step sequence over REAL HTTP. Resolve the parent
SPEC's third open question (verification home) by documenting that resolution. `factory/lasuite.py`
stays frozen throughout.

## Boundaries & Constraints

**Always:** `factory/lasuite.py` and `tests/factory/test_lasuite.py` are read-only — zero edits,
zero diff. The httpx import lives ONLY under `tools/` (outside `src/pyforge/atlas/**`, so the
`test_no_inline_io_in_package_code` denylist — which lists `httpx` with no exemption route — stays
green). The opener is injected exactly at `LaSuiteClient(config, opener=...)`, never by changing
the client's default. The rehearsal HTTP stub runs on `127.0.0.1` only (ephemeral port), started
and torn down inside the test itself — no external network, no real credentials, so it runs inside
the default `kedro-test` gate with no new pytest marker. The bring-up script is the SAME code path
for both this rehearsal and the later attended run (only `LASUITE_BASE_URL`/`LASUITE_API_TOKEN`
differ) — no separate "real" implementation may be written later.

**Block If:** If `tests/catalog/test_no_inline_io.py`'s denylist or exemption mechanism has changed
such that a `tools/`-relative import boundary no longer holds (i.e. the scan now covers paths
outside `ATLAS_PKG`), HALT with blocking condition `no-inline-io scan boundary changed`.

**Never:** Never construct or default an httpx opener inside `factory/lasuite.py` or any file under
`src/pyforge/atlas/**`. Never execute or schedule the ATTENDED DW-H3 bring-up itself (DW-H3 stays
open/DEFERRED) — this story's rehearsal targets a local stub, not a real Wagtail/La Suite server.
Never flip DW-H3's ledger `status` to closed. Never add a pytest network marker/exclusion filter
(no precedent in this repo; the rehearsal is loopback-only and belongs in the default gate, not
outside it).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real-HTTP round trip | loopback stub up, valid Bearer token, 2-page `outputs/` tree | push→2 created; re-push→2 skipped, 0 remote calls; edit 1 page→1 updated; fresh syncer→resumes, 0 created | No error expected |
| Wrong Bearer token | opener call carries a token the stub doesn't recognize | stub returns 401 | `LaSuiteClient` raises `LaSuiteError` naming the 401 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py` -- frozen seam
  (`Opener`, `Request`/`Response`, `LaSuiteClient`, `resolve_lasuite_config`); read-only.
- `src/shared/packages/pyforge-atlas/tests/factory/test_lasuite.py` -- `MockWagtail`'s route
  shapes are the rehearsal stub's spec; read-only, cited only.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py` --
  `resolve_wiki_root()`/`_wiki_layout()` (env `ATLAS_WIKI_ROOT`, default `<project>/wiki`; the
  latter wraps the former in `scaffold_wiki`) name the pattern the bring-up script's `main()`
  mirrors -- NOT imported from (this module executes `defs = build_definitions()` at import time,
  pulling in the full Dagster/Kedro translation, ~2.6s, for a 3-line env lookup); read-only, cited
  only.
- `src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py` -- confirms `httpx` is
  denylisted in `ATLAS_PKG` with no exemption route, and that `tests/`/`tools/` aren't scanned;
  read-only, cited only.
- `src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py` (NEW) -- `build_httpx_opener()` +
  `main()` CLI; the one script both this rehearsal and the later attended session run.
- `src/shared/packages/pyforge-atlas/tests/factory/test_lasuite_live_rehearsal.py` (NEW) -- the
  loopback stub server + the rehearsal test.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain/SPEC.md`
  -- resolve open question 3 (verification home); add the two new files to `surface:`.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` -- DW-H3 gets a
  short annotation pointing at this story's spec (status stays open/DEFERRED/ATTENDED).
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain/.memlog.md`
  -- reconcile the ledger touch (S-13.7 surface-drift gate), same convention Story 16.1 used.
- `_bmad-output/implementation-artifacts/spec-16-2-httpx-opener-and-rehearsal.md` (this file) --
  houses the attended-session acceptance checklist in Design Notes.

## Tasks & Acceptance

**Execution:**
- [ ] `src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py` -- add `build_httpx_opener()`
  (creates ONE `httpx.Client` per opener, reused across every request it makes -- not one client
  per request; pass `follow_redirects=True`, because `lasuite.Response` carries only
  `status_code`+`body` and DROPS headers, so an unfollowed 3xx -- an http->https upgrade in front
  of a real La Suite -- surfaces to the operator as a bare undebuggable `HTTP 301: ''` with the
  `Location` gone; wraps `client.request(...)` in `try/except (httpx.HTTPError, httpx.InvalidURL,
  UnicodeError)` -> re-raise as `LaSuiteError` naming the method/URL. `httpx.InvalidURL` is NOT a
  subclass of `httpx.HTTPError` (verified, httpx 0.28.1: its MRO is `InvalidURL -> Exception`), so
  a malformed `LASUITE_BASE_URL` -- a typo at the attended session, the likeliest operator error --
  otherwise escapes BOTH this handler and `main()`'s, producing exactly the raw `httpx` traceback
  this wrapper exists to prevent; converts the response via `.json()` then falls back to `.text`)
  and `main()` (resolve config via `resolve_lasuite_config()` -> exit 1 if unconfigured; inline a
  tiny `_resolve_wiki_root()` env-lookup -- `ATLAS_WIKI_ROOT` or
  `Path(__file__).resolve().parents[1] / "wiki"` -- mirroring
  `orchestration/definitions.py::resolve_wiki_root()`'s logic WITHOUT importing that module -- see
  Design Notes for why; **guard the empty-sync false-success BEFORE and AFTER the sync, which is
  what actually fixes it** -- `scaffold_wiki()` alone does NOT (see Design Notes): (a) if
  `<root>/outputs` is not an existing directory, print the resolved root to stderr and exit 3
  WITHOUT creating anything, so a typo'd `ATLAS_WIKI_ROOT` fails loudly instead of silently
  materializing a fresh empty tree at the wrong path; (b) after `sync_all()`, if
  `created+updated+skipped == 0`, print the resolved root + base URL to stderr and exit 3 --
  a bring-up that synced zero pages proved nothing and must never report success, since the
  attended checklist's step 8 closes DW-H3 on this script's word; (c) **prove the CMS was actually
  reached, which neither (a) nor (b) does** -- call `client.list_documents()` once after the sync
  and before returning 0, inside the same guarded block. `SyncReport.skipped` is defined by the
  frozen seam (`lasuite.py:172`) as "unchanged -- NO remote call made", so an all-skipped run
  contacts the CMS ZERO times while satisfying (b); verified by running it -- pointed at a DEAD
  endpoint (`http://127.0.0.1:9`, nothing listening) with a populated `.lasuite_sync.json`, the
  script printed `created=0 updated=0 skipped=1` and exited **0** with a success banner. The probe
  turns that into a clean exit 2. Do NOT instead fail when `created+updated == 0`: the attended
  checklist's steps 5 and 7 deliberately expect all-skipped runs and they are PASSES -- that guard
  would red the very idempotency the story exists to prove. The probe also gives
  `list_documents()` its only real-HTTP exercise; echo the resolved base URL and wiki root on the
  success path too, so the operator can see what it actually talked to; construct
  `WikiSyncer` AND run `sync_all()` -- **and `build_httpx_opener()` itself** -- inside the SAME
  `try/except` block: an ambient `HTTP_PROXY` with an unsupported scheme makes the `httpx.Client`
  CONSTRUCTOR raise `ValueError: Unknown scheme for proxy URL` (verified), which escapes `main()`
  entirely and exits 1, colliding with the documented "unconfigured" code, so catch `ValueError`
  alongside the rest and map it to exit 2. Catch `LaSuiteError`
  (exit 2) and `OSError`/`UnicodeDecodeError` (exit 4 -- an unreadable/unwritable wiki tree or a
  non-UTF-8 `.md` raises neither `LaSuiteError` nor anything `main()` previously caught, and an
  uncaught traceback exits 1, colliding with the documented "unconfigured" code); a corrupt
  `.lasuite_sync.json` raises from `WikiSyncer.__init__`, not just from `sync_all()`, so both must
  sit inside the block; print created/updated/skipped; document every exit code in the module
  docstring) -- the reusable bring-up script CAP-2 requires, importable by the rehearsal test AND
  runnable standalone at the attended session.
- [ ] `src/shared/packages/pyforge-atlas/tests/factory/test_lasuite_live_rehearsal.py` -- add a
  stdlib `http.server`-based loopback stub implementing `MockWagtail`'s 4 routes + Bearer-token
  check, and a test that imports `build_httpx_opener` from `tools/lasuite_bringup.py` (via
  `importlib.util.spec_from_file_location`, since `tools/` isn't a packaged/importable path) and
  reproduces the I/O matrix's happy-path + wrong-token scenarios -- proves the real opener, not a
  hand-rolled one, satisfies the mock-proven contract. The `wagtail_stub` fixture MUST neutralize
  ambient proxy env (`monkeypatch.delenv` on `HTTP_PROXY`/`http_proxy`/`ALL_PROXY`/`all_proxy`,
  plus `monkeypatch.setenv("NO_PROXY", "127.0.0.1")`): `httpx.Client` defaults `trust_env=True` and
  applies NO localhost bypass, so with a proxy exported both tests FAIL in the default `kedro-test`
  gate (verified: `2 passed` clean, `2 failed` with `HTTP_PROXY` set, stub recording 0 hits). The
  intent contract's claim that this belongs in the default offline gate only holds if the gate is
  genuinely env-independent. Fix it in the FIXTURE, never via `trust_env=False` in
  `build_httpx_opener` -- the attended enterprise bring-up legitimately needs proxy/`SSL_CERT_FILE`
  support (CLAUDE.md documents this repo's enterprise routing as env-var driven). The wrong-token
  test additionally asserts `state.requests == 1` (exactly one attempted call, matching this
  suite's existing remote-call-counting discipline) and asserts the substring `"HTTP 401"` plus the
  stub's `unauthorized` detail body -- NOT a bare `"401"`, which the ephemeral port embedded in the
  message (`http://127.0.0.1:<port>`) can satisfy spuriously (ports 34010-34019, 40100-40199,
  44010-44019 ... all contain `401`), and which asserts strictly less than the sibling
  `test_client_raises_clear_error_on_non_2xx` it claims to mirror. Cover `main()` -- the half the
  attended session actually runs, and the half that has now shipped the SAME false-success bug
  twice -- with tests for **every** documented exit code: 0 (happy path against the live stub,
  asserting the printed counts AND that the stub recorded requests), 1 (unconfigured env), 2
  (transport failure), 3 (both guards: typo'd root creating nothing, and scaffolded-but-empty
  `outputs/`), and 4 (unreadable wiki tree). Add one test that pins the reachability probe
  specifically: sync once against the live stub, then re-run `main()` with the SAME sidecar
  against a DEAD base URL -- it must exit 2, not 0. That is the regression test for this
  amendment; without it the guard rots silently, because every all-skipped run looks identical to
  a pass in the report line. Also route the stub's other HTTP verbs (`do_PUT`/`do_DELETE`/
  `do_HEAD`/`do_OPTIONS` -> `_route`) so a stray-verb call is counted by `state.requests` rather
  than answered by stdlib's 501 before the stub's own oracle sees it, and raise rather than
  silently continue if the stub thread is still alive after `thread.join(timeout=5)`.
- [ ] `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain/SPEC.md`
  -- remove open question 3 from the `open_questions` frontmatter list (leave items 1-2 untouched —
  Story 16.1 owns those, on its own unmerged branch), add a YAML comment above the list summarizing
  the resolution (matches the documented convention `pyforge.doctor.sources.fleet_scan::_spec_open_questions`
  depends on: resolved items are removed, never left as a "RESOLVED:"-prefixed entry), and in the
  `## Open Questions` prose section replace the third bullet with a small `**Resolved:**` sub-block
  (not just an unheaded paragraph sitting among the two still-open items -- a reader scanning this
  section for outstanding work should not have to read past a resolved one to find them), and
  append the two new files to `surface:`. Add ONE sentence to the `**Resolved:**` block
  reconciling DW-H3's own "Do NOT weaken the gate to import httpx into package code or bind a
  socket (AC-2 / NFR-12)" clause: that clause bars making the offline gate depend on a real
  network/live CMS, and this repo already binds loopback stub servers inside the same default gate
  (`tests/publish/test_emit_range.py`, `tests/wasm/test_wasm_smoke.py`) -- record it so a future
  reader does not re-litigate the apparent contradiction. Cite the attended checklist at its
  DURABLE promoted path (below), never the Tier-3 one.
- [ ] `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` -- append a
  short annotation to DW-H3 noting the rehearsal + bring-up script + attended checklist now exist,
  without changing `status` (stays open/DEFERRED/ATTENDED). **Cite the durable path**
  `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-16-2-httpx-opener-and-rehearsal.md`
  (where CLAUDE.md's promote-after-merge convention puts this spec), NOT
  `_bmad-output/implementation-artifacts/...`: that tree is gitignored Tier-3 AND resolves through
  the per-worktree symlink CLAUDE.md forbids for addressing a project, so a tracked artifact citing
  it dangles in every fresh clone -- and the attended DW-H3 checklist, the one operational thing
  this annotation defers to, would be exactly the content lost. Separate the annotation from the
  following `## DW-H4` heading with a blank line (every other entry boundary in the file has one)
  and wrap it to the file's ~100-col width rather than leaving one ~700-char line.
- [ ] `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain/.memlog.md`
  -- add a dated entry reconciling the ledger touch; after committing, re-stamp that spec's baseline
  in isolation (`python scripts/spec_surface_check.py --write-baseline --spec pyforge-atlas/spec-wagtail-corporate-brain`,
  files `git add`-ed first).
- [ ] `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-16-2-httpx-opener-and-rehearsal.md`
  (NEW) -- **promote this spec into the tracked tree as part of this story, not after it.** Three
  citations in two permanently-tracked artifacts (the DW-H3 annotation, SPEC.md's frontmatter
  comment, SPEC.md's `**Resolved:**` block) point at this path, and the ATTENDED bring-up checklist
  -- the entire reason it is safe to leave DW-H3 `open` -- exists ONLY in this spec's Design Notes.
  Left in gitignored Tier-3 it dies with the run worktree and all three citations dangle in every
  clone; CLAUDE.md names pyforge-atlas as the cautionary counter-case for exactly this loss (30 of
  32 story specs unrecoverable). Copy the file verbatim (it is its own record -- intent contract,
  change log, triage log, checklist) and `git add` it so it lands with this branch's merge, which
  is precisely when the promote-after-merge convention wants it.
- [ ] `pixi.toml` -- update the `[feature.pyforge-atlas.dependencies]` `httpx` COMMENT only (no
  dependency change, so `environment.yaml` needs no regeneration): it currently justifies `httpx`
  as TEST-ONLY via `tests/views/test_live.py`'s starlette `TestClient`, three lines below its own
  AUD-ATLAS-010 doctrine that "an undeclared hard import is a runtime dependency whether or not the
  manifest says so". `tools/lasuite_bringup.py` now hard-imports it as shipped operator tooling, so
  name that second consumer -- otherwise pruning the starlette test takes the declaration with it
  and breaks the attended bring-up.

**Acceptance Criteria:**
- Given a loopback stub implementing `MockWagtail`'s routes and a real httpx-backed opener from
  `tools/lasuite_bringup.py`, when the rehearsal test runs the four-step sequence, then it matches
  `test_round_trip_push_update_idempotent` + `test_mapping_persists_so_a_fresh_syncer_resumes`'s
  proven counts exactly (2 created, then 0 remote calls on re-push, then exactly 1 update, then a
  fresh syncer resumes with 0 creates).
- Given `factory/lasuite.py` and `tests/factory/test_lasuite.py`, when this story's changes land,
  then both show zero diff.
- Given `pixi run -e pyforge-atlas kedro-catalog-check`, when it runs after this story's changes,
  then `test_no_inline_io_in_package_code` still passes (no `httpx` import anywhere under
  `src/pyforge/atlas/**`).
- Given the parent SPEC's third open question, when this story's SPEC.md edit lands, then
  `open_questions` in frontmatter drops to 2 items (items 1-2 unchanged, verbatim) and the prose
  states the rehearsal lives in the default offline gate (no network marker), not a separate
  attended-only checklist alone.
- Given DW-H3, when this story's ledger annotation lands, then `status` is still `open` and the
  annotation cites this spec by path.

## Spec Change Log

### 2026-08-15 — Review pass 3 (bad_spec loopback)

- **Triggering finding:** pass 2's replacement guard was incomplete in the same way pass 1's was.
  It specified "after `sync_all()`, if `created+updated+skipped == 0` -> exit 3", but
  `SyncReport.skipped` is defined by the frozen seam (`lasuite.py:172`) as "unchanged -- NO remote
  call made". So an all-skipped run contacts the CMS **zero times** and still satisfies the guard.
  **Reproduced:** synced one page against a live stub (exit 0, 1 server hit), then re-ran `main()`
  with the same sidecar against `http://127.0.0.1:9` -- **nothing listening at all** -- and got
  `created=0 updated=0 skipped=1`, **exit 0**, success banner, still 1 total server hit. Both
  independent reviewers converged on this. Two spec passes have now shipped the same class of
  false success, which is why this amendment fixes the PROPERTY (was the CMS reached?) rather than
  another proxy for it.
- **Amended:** added guard (c) -- call `client.list_documents()` once after the sync, before
  returning 0, inside the guarded block, so exit 0 is unreachable without genuine CMS contact. It
  doubles as `list_documents()`'s only real-HTTP exercise (that stub route was dead).
- **Rejected the reviewers' proposed fix, deliberately:** both suggested failing when
  `created+updated == 0`. That is WRONG here -- the attended checklist's steps 5 and 7 expect
  all-skipped runs and they are PASSES (that IS the idempotency this story exists to prove), so
  their guard would red the success case. Recorded so a later pass does not "fix" it back.
- **Known-bad state avoided:** the attended operator rehearsing locally, re-pointing
  `LASUITE_BASE_URL` at the real CMS, re-running, seeing exit 0 with a success banner having
  touched nothing -- then closing DW-H3 per checklist step 8. A retired ATTENDED gate that
  verified nothing, which is the exact NFR-12 failure DW-H3's own text warns about.
- **Also folded in while re-deriving:** every documented exit code (0/1/2/3/4) now needs a test --
  pass 2 shipped tests for only 2 and 3, leaving the happy path (the one the attended session
  actually takes) unexecuted, which is how this bug survived a full review pass; plus a dedicated
  regression test for guard (c) (sync live, then re-run against a dead URL, expect 2). Construct
  `build_httpx_opener()` INSIDE `main()`'s guarded block and catch `ValueError` -- an ambient
  `HTTP_PROXY` with an unsupported scheme makes the `httpx.Client` CONSTRUCTOR raise, escaping
  `main()` and exiting 1 (verified). Raise a clear `LaSuiteError` when a non-GET request is
  redirected (`resp.history` non-empty): httpx rewrites POST->GET on 301/302/303, so
  `follow_redirects=True` alone converts a create into a list and yields a different misleading
  error. Route the stub's remaining verbs through `_route` so stray-verb calls are counted rather
  than answered by stdlib's 501; raise if the stub thread outlives `join(timeout=5)`. Promote this
  spec into the tracked `planning-artifacts/specs/` tree **in this story** -- three citations in
  two permanently-tracked artifacts point at that path and the attended checklist lives only here.
  Prefix the documented invocation with `pixi run -e pyforge-atlas` (bare `python <path>` cannot
  work -- `tools/` is unpackaged). Name `tools/lasuite_bringup.py` as a second consumer in
  `pixi.toml`'s TEST-ONLY `httpx` comment.
- **KEEP (unaffected by this amendment, must survive re-derivation unchanged):** everything passes
  1 and 2 listed as KEEP still holds, plus all of pass 2's now-verified work -- the two exit-3
  guards (a) and (b) as written (they are correct, just insufficient alone), the
  `(httpx.HTTPError, httpx.InvalidURL, UnicodeError)` except-tuple, the proxy-neutralizing fixture
  (`delenv` of `HTTP_PROXY`/`http_proxy`/`ALL_PROXY`/`all_proxy` + `NO_PROXY=127.0.0.1`, verified
  load-bearing), `follow_redirects=True`, the `"HTTP 401"`+detail-body assertion, `report.total`,
  the `_StubHandle.shutdown` handle, the durable-path citations in SPEC.md/ledger, and the
  isolated per-spec baseline stamp. Exit codes 0/1/2/3/4 keep their pass-2 meanings; guard (c)
  returns the EXISTING code 2 (it is a `LaSuiteError`), not a new one.

### 2026-08-15 — Review pass 2 (bad_spec loopback)

- **Triggering finding:** pass 1's own amendment did not fix the bug it was written to fix.
  It directed `main()` to use `scaffold_wiki(_resolve_wiki_root())` instead of a bare
  `WikiLayout(...)` on the stated grounds that this stops a misconfigured wiki root from
  "silently producing a hollow `created=0 updated=0 skipped=0` success". It does not:
  `scaffold_wiki` merely creates the directories, `sync_all()`'s `rglob("*.md")` then finds
  nothing in the new empty `outputs/`, and the identical hollow success is printed. **Reproduced
  against the shipped code** -- typo'd `ATLAS_WIKI_ROOT` + nothing listening on the CMS endpoint
  gave `created=0 updated=0 skipped=0`, **exit 0**, plus a silently-created tree at the wrong
  path. A faithfully-implementing agent could not have caught this: the spec asserted the remedy
  worked and the code implemented the remedy exactly.
- **Amended:** Design Notes' wiki-root section now states plainly that `scaffold_wiki` is a
  convenience and never the guard, and specifies the two guards that actually close the hole
  (pre-check `<root>/outputs` exists -> exit 3 without scaffolding; post-check
  `created+updated+skipped == 0` -> exit 3), plus echoing the resolved base URL + wiki root.
  Tasks restated accordingly, with the full exit-code table (0/1/2/3/4) and the attended
  checklist's step 4 updated so exit 3 cannot be read as a pass.
- **Known-bad state avoided:** the one script whose entire job is proving the live push works
  reporting success having made ZERO HTTP requests -- on exactly the first-ever-attended-bring-up
  misconfiguration most likely to hit it, and directly upstream of the checklist's step 8, which
  closes DW-H3 on this script's word. That is the NFR-12 "gates are never weakened" failure the
  DW-H3 entry itself warns against, reached by accident.
- **Also folded in while re-deriving** (real, independently reproduced findings from the same
  review pass): the rehearsal's `wagtail_stub` fixture must neutralize ambient proxy env --
  `httpx` defaults `trust_env=True` with no localhost bypass, so an exported `HTTP_PROXY` reds
  BOTH new tests in the default `kedro-test` gate (`2 passed` clean vs `2 failed` proxied, stub
  recording 0 hits), which falsifies the intent contract's premise that this belongs in the
  default offline gate; `httpx.InvalidURL` must be caught alongside `httpx.HTTPError` in
  `build_httpx_opener` (it is NOT a subclass -- MRO `InvalidURL -> Exception` -- so a typo'd
  `LASUITE_BASE_URL` escaped every handler and produced the raw traceback the wrapper exists to
  prevent, exiting 1 and colliding with the documented "unconfigured" code); `main()` must also
  catch `OSError`/`UnicodeDecodeError` (exit 4); `follow_redirects=True` (`lasuite.Response`
  drops headers, so an unfollowed 3xx is an undebuggable `HTTP 301: ''`); the wrong-token test
  must assert `"HTTP 401"` + the body detail, not a bare `"401"` the ephemeral port can satisfy
  spuriously; two small `main()` tests (zero-pages guard, transport error) since `main()` -- the
  half the attended session actually runs -- had no coverage at all; and both tracked artifacts
  must cite this spec at its durable promoted `planning-artifacts/specs/` path rather than the
  gitignored Tier-3 one, which dangles in every fresh clone and would take the attended checklist
  with it.
- **KEEP (unaffected by this amendment, must survive re-derivation unchanged):** everything pass 1
  listed as KEEP still holds -- the `tools/lasuite_bringup.py` shape (`build_httpx_opener()`
  factory + `main()` CLI), the loopback `http.server` stub design (4 routes + Bearer check,
  per-test fresh `_WagtailState`, fixture start/yield/shutdown lifecycle), the exact 4-step
  assertion sequence reproducing `test_lasuite.py`'s proven counts plus the wrong-token/401 test,
  the `importlib.util.spec_from_file_location` loading pattern, the inlined `_resolve_wiki_root()`
  (NOT imported from `orchestration/definitions.py`), the one-client-per-opener reuse, the
  `WikiSyncer`-construction-inside-the-try widening, and the SPEC.md/ledger/`.memlog.md` edit set
  (open question 3 removed from frontmatter with items 1-2 verbatim, the `**Resolved:**`
  sub-block, DW-H3 `status` untouched at `open`, baseline re-stamped for this spec alone). Exit
  codes 0/1/2 keep their pass-1 meanings; 3 and 4 are additions, not renumberings.

### 2026-08-15 — Review pass 1 (bad_spec loopback)
- **Triggering finding:** the Code Map/Design Notes directed `tools/lasuite_bringup.py::main()` to
  reuse `resolve_wiki_root()` by importing it from `orchestration/definitions.py`. That module
  executes `defs = build_definitions()` (a full Dagster/Kedro `KedroProjectTranslator` build) at
  MODULE IMPORT TIME as its own last top-level statement -- a spec-level oversight, not something a
  faithfully-implementing agent could have caught, since the spec presented the import as a free
  reuse of a 3-line helper.
- **Amended:** Code Map's citation of `orchestration/definitions.py` now says NOT to import from it;
  Tasks & Design Notes now specify inlining `_resolve_wiki_root()` (the identical env-lookup logic,
  duplicated deliberately) plus `scaffold_wiki(...)` instead of a bare `WikiLayout(...)`.
- **Known-bad state avoided:** (1) the rehearsal test and the attended bring-up script both silently
  paying a ~2.6s Dagster/Kedro build cost and becoming fragile to an unrelated subsystem breaking;
  (2) a bare `WikiLayout(...)` masking a missing/unscaffolded wiki root as a hollow `created=0
  updated=0 skipped=0` exit-0 "success" -- on exactly the first-ever attended-bring-up case most
  likely to hit it.
- **Also folded in while re-deriving** (real, lower-severity findings from the same review pass,
  addressed here rather than in a second loopback): wrap `httpx.HTTPError` transport failures
  (connection refused, timeout) into `LaSuiteError` inside `build_httpx_opener` -- previously these
  propagated as raw `httpx` exceptions, bypassing the module's own error-clarity contract, on exactly
  the failure mode most likely during a real attended run against a flaky/unreachable server; widen
  `main()`'s `try/except LaSuiteError` to also cover `WikiSyncer(...)` construction (a corrupt
  `.lasuite_sync.json` raises from `__init__`, not just `sync_all()`); reuse one `httpx.Client` per
  opener instead of opening/closing a fresh one per request; the wrong-token rehearsal test now also
  asserts `state.requests == 1`; SPEC.md's resolved third open question gets its own `**Resolved:**`
  sub-block rather than sitting as a bare paragraph inside the still-open list.
- **KEEP (unaffected by this amendment, must survive re-derivation unchanged):** the overall
  `tools/lasuite_bringup.py` shape (`build_httpx_opener()` factory + `main()` CLI, exit codes
  0/1/2), the rehearsal test's loopback `http.server` stub design (4 routes + Bearer check, per-test
  fresh `_WagtailState`, fixture-based start/yield/shutdown lifecycle), the exact 4-step assertion
  sequence reproducing `test_lasuite.py`'s proven counts plus the wrong-token/401 test, the
  `importlib.util.spec_from_file_location` loading pattern, and the SPEC.md/ledger/`.memlog.md`/
  baseline edits already made in the reverted pass (all correct, none touched by this amendment
  except the one `**Resolved:**` sub-block wording change above).

## Review Triage Log

### 2026-08-15 — Review pass 3
- intent_gap: 0
- bad_spec: 1 (high 1)
- patch: 7 (medium 3, low 4)
- defer: 0
- reject: 5 (low 5)
- addressed_findings:
  - `[high]` `[bad_spec]` pass 2's `report.total == 0` guard does not prove the CMS was reached:
    `skipped` pages make NO remote call, so an all-skipped run exits 0 with a success banner
    against a dead endpoint. Reproduced (live stub -> exit 0, 1 hit; same sidecar re-run against
    `127.0.0.1:9` with nothing listening -> `skipped=1`, exit 0, still 1 hit). Both reviewers found
    it independently. Spec amended with guard (c), a `list_documents()` reachability probe; code
    reverted for re-derivation. The reviewers' own proposed fix (fail when `created+updated == 0`)
    was rejected as wrong — the attended checklist's steps 5 and 7 expect all-skipped PASSES.
  - `[medium]` `[patch]` `main()`'s happy path (exit 0) and exit 1/exit 4 had no test at all —
    pass 2 covered only 2 and 3, which is how the bad_spec above survived a full review. Folded in:
    every documented exit code gets a test, plus a dedicated regression test for guard (c).
  - `[medium]` `[patch]` `build_httpx_opener()` was called outside `main()`'s `try`, so an ambient
    `HTTP_PROXY` with an unsupported scheme made the `httpx.Client` constructor raise `ValueError`
    straight out of `main()`, exiting 1 and colliding with "unconfigured" — folded in.
  - `[medium]` `[patch]` `follow_redirects=True` does not deliver its stated rationale for writes:
    httpx rewrites POST->GET on 301/302/303, turning a create into a list and surfacing a
    different misleading error — folded in: raise a clear `LaSuiteError` naming the chain when a
    non-GET request is redirected.
  - `[low]` `[patch]` three citations in two permanently-tracked artifacts point at this spec's
    gitignored Tier-3 path, where the ATTENDED checklist solely lives — folded in: promote the
    spec into `planning-artifacts/specs/` within this story.
  - `[low]` `[patch]` the documented invocation `python src/.../lasuite_bringup.py` cannot work
    outside the pixi env (`tools/` is unpackaged) — folded in: `pixi run -e pyforge-atlas` prefix.
  - `[low]` `[patch]` `pixi.toml` still justifies `httpx` as TEST-ONLY while shipped operator
    tooling now hard-imports it — folded in as a comment-only edit (no dependency change, so no
    `environment.yaml` regeneration).
  - `[low]` `[patch]` the stub answered PUT/DELETE/HEAD/OPTIONS with stdlib's 501 before `_route`
    could count them, and the fixture ignored `thread.join(timeout=5)`'s result — folded in.
  - `[low]` `[reject]` `.lasuite_sync.json` records no `base_url`, so a sidecar from CMS A
    mis-`PATCH`es ids on CMS B — real, but the sidecar's schema belongs to the frozen
    `factory/lasuite.py`; guard (c) closes the reachability half that is in scope here.
  - `[low]` `[reject]` the opener still leaks its `httpx.Client` (no close/context manager) —
    re-raised from pass 2 and re-rejected on the same grounds: no FD accumulation, no
    `filterwarnings` to fail on it, `main()` is short-lived.
  - `[low]` `[reject]` `_WIKI_ROOT_ENV`/`_resolve_wiki_root` should be hoisted into the
    side-effect-free `factory/wiki.py` rather than duplicated — a reasonable third option, but
    genuinely deduplicating means changing `orchestration/definitions.py` too; the duplication is
    pass 1's logged, deliberate decision and re-opening it is out of scope.
  - `[low]` `[reject]` the `InvalidURL` docstring overstates it as "the likeliest operator error"
    when 3 of 5 typo shapes raise `UnsupportedProtocol` (already an `HTTPError`) — the except-tuple
    entry is still correct and now tested; the prose nuance is not worth a loopback.
  - `[low]` `[reject]` the transport-error test could pass for the wrong reason if the ephemeral
    port is re-bound after teardown — no xdist in `kedro-test`, and a re-bound port yields 401 ->
    `LaSuiteError` -> still exit 2, so the assertion holds either way.

### 2026-08-15 — Review pass 2
- intent_gap: 0
- bad_spec: 1 (high 1)
- patch: 8 (high 1, medium 4, low 3)
- defer: 2 (medium 2)
- reject: 9 (low 9)
- addressed_findings:
  - `[high]` `[bad_spec]` pass 1's `scaffold_wiki` remedy does not fix the hollow
    `created=0 updated=0 skipped=0` exit-0 false success it was introduced to fix -- reproduced
    against the shipped code with a typo'd `ATLAS_WIKI_ROOT` and nothing listening. Spec amended
    to guard the REPORT (pre-check `outputs/` exists, post-check non-zero total, both exit 3);
    code reverted for re-derivation (see Spec Change Log).
  - `[high]` `[patch]` both new tests FAIL in the default `kedro-test` gate when `HTTP_PROXY` is
    exported (`httpx` `trust_env=True`, no localhost bypass) -- verified `2 passed` clean vs
    `2 failed` proxied with the stub recording 0 hits. Folded into the re-derivation: the fixture
    neutralizes proxy env; explicitly NOT via `trust_env=False`, which the attended enterprise
    bring-up needs.
  - `[medium]` `[patch]` `httpx.InvalidURL` is not an `httpx.HTTPError` subclass, so a malformed
    `LASUITE_BASE_URL` escaped both handlers as a raw traceback exiting 1 (colliding with the
    documented "unconfigured" code) -- folded in.
  - `[medium]` `[patch]` `main()` caught only `LaSuiteError`, so an unreadable/unwritable wiki
    tree or a non-UTF-8 `.md` raised uncaught -- folded in as exit 4.
  - `[medium]` `[patch]` `follow_redirects` defaults `False` and `lasuite.Response` drops headers,
    so a real 3xx reaches the operator as `HTTP 301: ''` with no `Location` -- folded in.
  - `[medium]` `[patch]` both tracked artifacts (SPEC.md comment, DW-H3 annotation) cited this
    spec at its gitignored Tier-3 path, which dangles in a fresh clone and would take the attended
    checklist with it -- folded in: cite the durable promoted `planning-artifacts/specs/` path.
  - `[low]` `[patch]` `assert "401" in str(exc.value)` can pass spuriously on ephemeral ports
    containing `401` -- folded in: assert `"HTTP 401"` plus the stub's detail body.
  - `[low]` `[patch]` `main()` -- the half the attended session actually runs -- had zero test
    coverage; folded in: two small tests (zero-pages guard, transport error).
  - `[low]` `[patch]` the ledger annotation was one ~700-char line abutting `## DW-H4` with no
    blank line, unlike every other entry boundary -- folded in.
  - `[low]` `[reject]` the flagship claim that the rehearsal violates DW-H3's "Do NOT ... bind a
    socket (AC-2 / NFR-12)" -- that clause bars making the offline gate depend on a real
    network/live CMS; this repo already binds loopback stub servers inside the same default gate
    (`tests/publish/test_emit_range.py`, `tests/wasm/test_wasm_smoke.py`), which settles the
    reading. Recorded in SPEC.md so it is not re-litigated, rather than treated as a defect.
  - `[low]` `[reject]` "SPEC.md `status:` should have advanced past `ready`" -- SPEC.md's own line
    113 mandates the opposite: it "holds at `draft`/`ready` — never `shipped` on paper alone"
    until the attended session passes. The reviewer's rule was real; this spec is the exception
    that states itself.
  - `[low]` `[reject]` "CAP-3 is claimed but unsatisfiable" -- the memlog says CAP-3's acceptance
    is *rehearsed* offline, not achieved, and the ledger annotation explicitly keeps DW-H3 open.
    The wording already matches reality.
  - `[low]` `[reject]` no `.close()` handle on the opener's `httpx.Client` -- a `ResourceWarning`
    with no FD accumulation (refcounting reclaims; the reviewer's own re-measure needed an
    explicit `gc.collect()` to show a delta), no `filterwarnings` config to fail on it, and
    `main()` is a short-lived process. Adding public close API nobody calls is churn.
  - `[low]` `[reject]` no `truststore` injection for an internal-CA server -- `trust_env=True`
    already honors `SSL_CERT_FILE`/`SSL_CERT_DIR`, which is the documented enterprise seam; the
    cited `_http.py` chain belongs to the conda-forge-expert skill, not this package.
  - `[low]` `[reject]` `_WIKI_ROOT_ENV`/`_resolve_wiki_root` duplicate `orchestration/
    definitions.py` with no test pinning them -- the duplication is the deliberate, logged pass-1
    decision (that module runs `build_definitions()` at import time); re-litigating it is out of
    scope for this story.
  - `[low]` `[reject]` stub is HTTP/1.0 so connection reuse is unexercised, and raising it to
    HTTP/1.1 deadlocks a non-threading `HTTPServer` -- correct on both counts, but reuse is an
    efficiency property, not part of the contract under test; switching base classes to prove it
    is scope the story does not carry.
  - `[low]` `[reject]` the stub mirrors `MockWagtail`'s shapes rather than real DRF's (int ids,
    pagination envelope, HTML error bodies) -- true, and precisely why the ATTENDED bring-up
    remains open; the rehearsal's stated job is the mock-proven contract over real HTTP.
  - `[low]` `[reject]` unused `tmp_path` in the wrong-token test, unregistered `sys.modules`
    entry, decorative `# noqa` codes, unchecked `thread.join` result -- cosmetic, no consumer
    consequence.

### 2026-08-15 — Review pass 1
- intent_gap: 0
- bad_spec: 1 (medium 1)
- patch: 6 (high 1, medium 2, low 3)
- defer: 0
- reject: 7 (low 7)
- addressed_findings:
  - `[medium]` `[bad_spec]` `main()` imported `resolve_wiki_root` from
    `orchestration/definitions.py`, which runs a full Dagster/Kedro `build_definitions()` at module
    import time -- couples the isolated rehearsal + attended script to an unrelated subsystem and
    costs ~2.6s per import. Spec amended to inline the tiny env-lookup instead; code reverted for
    re-derivation (see Spec Change Log).
  - `[high]` `[patch]` `main()`'s bare `WikiLayout(resolve_wiki_root())` masks a missing/unscaffolded
    wiki root as a hollow `created=0 updated=0 skipped=0` exit-0 "success" -- folded into the same
    re-derivation: use `scaffold_wiki(...)`.
  - `[medium]` `[patch]` `build_httpx_opener`'s `_opener` didn't wrap `httpx` transport exceptions
    (connection refused, timeout) into `LaSuiteError`, bypassing the module's error-clarity
    contract -- folded into the same re-derivation.
  - `[medium]` `[patch]` `main()`'s `try/except LaSuiteError` didn't cover `WikiSyncer(...)`
    construction, so a corrupt `.lasuite_sync.json` would raise uncaught instead of hitting the
    clean exit-2 path -- folded into the same re-derivation.
  - `[low]` `[patch]` a fresh `httpx.Client` was opened/closed per request instead of reused across
    the opener's lifetime -- folded into the same re-derivation.
  - `[low]` `[patch]` the wrong-Bearer-token rehearsal test didn't assert the attempted-call count
    -- folded in: now asserts `state.requests == 1`.
  - `[low]` `[patch]` SPEC.md's resolved third open question sat as a bare paragraph inside the
    still-open `## Open Questions` list -- folded in: gets its own `**Resolved:**` sub-block.
  - `[low]` `[reject]` edge-case-hunter's claim that `test_wrong_bearer_token_...`'s signature omits
    the `wagtail_stub` fixture parameter -- verified against the diff text and the live file; the
    parameter is present in both. A misread, not a real defect.
  - `[low]` `[reject]` non-executable `tools/lasuite_bringup.py` (mode 644 despite a `#!/usr/bin/env
    python3` shebang) -- every real invocation (this spec's own checklist, the test's
    `importlib` loader) runs it via `python <path>`, never `./<path>`; inert, matches the existing
    `tools/normalize_viz_build.py` precedent.
  - `[low]` `[reject]` suggestion to add a test asserting zero diff on `factory/lasuite.py` -- not
    this repo's pattern (git-diff assertions inside pytest); already covered at the right layer by
    the no-inline-io scan + this spec's own `git diff --stat` verification command.
  - `[low]` `[reject]` stub server's route-matching (path-prefix based) mechanically differs from
    `MockWagtail`'s (`url.split("/api/v1")` based) -- behaviorally equivalent for every path either
    side actually sends; rewriting the stub to literally mirror the mock's matching style is churn
    with no behavior change.
  - `[low]` `[reject]` `assert spec is not None and spec.loader is not None` would be stripped under
    `python -O` -- this repo's pixi tasks never invoke pytest with `-O`; no real trigger path.
  - `[low]` `[reject]` the stub's `_read_json` would raise an unhandled `ValueError` on a non-numeric
    `Content-Length` -- test-only stub called only by the real `httpx` client in the same test suite,
    which always sends a valid numeric header; unrealistic trigger.
  - `[low]` `[reject]` `server.shutdown()` could theoretically block if a handler thread is mid-request
    at teardown -- the stub is single-threaded and the client calls are synchronous, so by the time a
    test function returns, the server is idle in its accept loop, not mid-request; unrealistic given
    this test's actual call pattern, and `thread.join(timeout=5)` already bounds the worst case.

## Design Notes

**Why `tools/lasuite_bringup.py` and not a `pyforge.atlas` CLI subcommand.** `tools/` sits outside
`src/pyforge/atlas/**` (the no-inline-IO scan root) and already holds one precedent
(`tools/normalize_viz_build.py`, invoked directly via `python tools/normalize_viz_build.py` from a
pixi task, not packaged). DW-H3's own ledger text says "a script / the C1 Dagster resource" — no
Dagster resource exists yet (confirmed: no `@dg.resource`/`ConfigurableResource` for lasuite
anywhere), so a script is the only real option today.

```python
def build_httpx_opener(*, timeout: float = 30.0) -> Opener:
    # ONE client, reused for every request this opener makes -- not re-opened (new TCP/TLS
    # handshake) per call. follow_redirects=True because lasuite.Response carries only
    # status_code+body: an unfollowed 3xx (http->https in front of a real La Suite) reaches the
    # operator as a bare `HTTP 301: ''` with the Location header already discarded.
    client = httpx.Client(timeout=timeout, follow_redirects=True)

    def _opener(request: Request) -> Response:
        try:
            resp = client.request(request.method, request.url,
                                   headers=request.headers, json=request.json)
        # InvalidURL is NOT an HTTPError subclass (httpx 0.28.1 MRO: InvalidURL -> Exception), so a
        # typo'd LASUITE_BASE_URL escapes both this handler and main()'s without it listed here.
        except (httpx.HTTPError, httpx.InvalidURL, UnicodeError) as exc:
            raise LaSuiteError(f"{request.method} {request.url} -> transport error: {exc}") from exc
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        return Response(status_code=resp.status_code, body=body)
    return _opener
```

**`follow_redirects=True` is necessary but not sufficient -- a redirected WRITE must still be
called out.** httpx follows 301/302/303 by rewriting POST to GET and dropping the body, so an
http->https upgrade in front of a real La Suite silently turns `create_document` into
`GET /api/v1/documents/`, which answers 2xx with a LIST, which `WikiSyncer._created_id` then
reports as "CMS create returned 2xx but no 'id'" -- a different misleading error, not a clear one.
After the request, if `resp.history` is non-empty AND the request method was not `GET`, raise a
`LaSuiteError` naming the original URL, the final URL, and the chain: a redirected write is exactly
the case the operator must see verbatim at the attended session, and it is the one the response
shape cannot express (`Response` carries no headers).

**Do NOT reach for `trust_env=False` here.** `httpx.Client` defaults `trust_env=True` with no
localhost bypass, which is why an exported `HTTP_PROXY` reds both rehearsal tests (verified). The
attended enterprise bring-up genuinely needs that env chain (proxy, `SSL_CERT_FILE`) -- CLAUDE.md
documents this repo's enterprise routing as env-var driven -- so the offline gate's independence is
the TEST FIXTURE's job (`monkeypatch.delenv` the proxy vars + `NO_PROXY=127.0.0.1`), never the
opener's.

**Wiki root: inline the tiny resolver, don't import `orchestration.definitions`.** That module executes
`defs = build_definitions()` at MODULE IMPORT TIME (its own last line) -- importing anything from it,
even just `resolve_wiki_root`, pulls in the full Dagster/Kedro `KedroProjectTranslator` build as a side
effect (measured: ~2.6s, plus unrelated Dagster schedule/sensor log noise). That's an unnecessary,
fragile transitive dependency for a 3-line env lookup, AND it would couple the rehearsal test's
default-gate reliability to an entirely unrelated subsystem building successfully. Reimplement the
same logic locally instead (it's genuinely this small):

```python
_WIKI_ROOT_ENV = "ATLAS_WIKI_ROOT"
_PROJECT_PATH = Path(__file__).resolve().parents[1]  # tools/../ == the pyforge-atlas project root,
                                                      # identical to orchestration/definitions.py's
                                                      # PROJECT_PATH (parents[4] from that deeper file).

def _resolve_wiki_root() -> Path:
    override = (os.environ.get(_WIKI_ROOT_ENV) or "").strip()
    return Path(override) if override else (_PROJECT_PATH / "wiki")
```

**The empty-sync false success -- and why `scaffold_wiki` does NOT fix it (corrected, review pass 2).**
Pass 1 amended this section to swap a bare `WikiLayout(...)` for `scaffold_wiki(_resolve_wiki_root())`,
asserting that this prevented a misconfigured wiki root from printing `created=0 updated=0 skipped=0`
and exiting 0. **That reasoning was wrong, and the resulting code shipped the very bug the amendment
claimed to remove** -- verified by running it: with `ATLAS_WIKI_ROOT` pointed at a nonexistent path and
NOTHING listening on `LASUITE_BASE_URL`, the script printed `created=0 updated=0 skipped=0`, exited
**0**, and silently created `{raw,compiled,outputs}` at the typo'd path. `scaffold_wiki` only creates
the directories; `sync_all()`'s `rglob("*.md")` then finds nothing in the freshly-made empty
`outputs/`, producing the identical hollow success -- and it made the failure mode slightly *worse* by
materializing a wrong-path tree as a side effect.

The false success is a property of the REPORT, not of the layout, so it has to be guarded where the
report is read. Two guards, both required:

- **Before:** if `<root>/outputs` is not already an existing directory, print the resolved root and
  exit 3 without creating anything -- a typo'd `ATLAS_WIKI_ROOT` must fail loudly, not scaffold.
- **After:** if `created + updated + skipped == 0`, print the resolved root + base URL and exit 3 --
  a bring-up that synced zero pages proved nothing.

This matters more than an ordinary ergonomics fix: the attended checklist's step 8 closes DW-H3 on
this script's word, so a hollow exit-0 could retire an ATTENDED gate having verified nothing --
precisely the NFR-12 "gates are never weakened" failure the ledger entry warns about. Keep
`scaffold_wiki` for the surviving case (root exists, `raw/`+`compiled/` may not) -- it is idempotent
and is what `orchestration/definitions.py::_wiki_layout()` wraps `resolve_wiki_root()` in -- but it is
a convenience, never the guard.

**Resolving open question 3.** No `@pytest.mark.network`-style precedent exists anywhere in
pyforge-atlas (only the unrelated conda-forge-expert skill's own `pytest.ini` has one); this
project's offline-safety convention is architectural (an injected opener/fetcher whose default
refuses), not marker-based. The rehearsal here is a third option neither named alternative
anticipated: a real-httpx-over-real-HTTP test that stays fully offline (loopback only, no
credentials) and therefore belongs in the DEFAULT `kedro-test` gate, not a marker-gated one. The
ATTENDED checklist below is additional, not a substitute.

**Attended DW-H3 bring-up checklist** (for the later, separately-scheduled session — not executed
by this story):
1. Provision the instance per `spec-16-1-instance-deploy-definition.md`'s Design Notes (SQLite
   Wagtail 7.4.1 + django-lasuite 0.0.26).
2. Mint an API token via the Wagtail admin UI (S-16.1: no Steward verb exists for this yet).
3. `export LASUITE_BASE_URL=<real base url>` and `export LASUITE_API_TOKEN=<minted token>`.
4. `pixi run -e pyforge-atlas python src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py`
   -- the `pixi run -e pyforge-atlas` prefix is REQUIRED and must appear everywhere this command is
   written (module docstring included): `tools/` is not packaged into the wheel, so outside that
   env both `import httpx` and `from pyforge.atlas.factory.lasuite import ...` fail and no install
   makes the bare `python <path>` form work. First run must report
   `created=N updated=0 skipped=0` for the full `outputs/` tree, with **N > 0**. Exit 3 means the
   wiki root resolved somewhere with no `outputs/` pages (check the path the script echoes) and
   NOTHING was pushed -- it is not a pass. Exit 1 = unconfigured env, 2 = a `LaSuiteError`
   (transport/non-2xx/corrupt mapping), 4 = an unreadable wiki tree.
5. Re-run immediately -- must report `created=0 updated=0 skipped=N` (no duplicates).
6. Edit one `outputs/` page, re-run -- must report `created=0 updated=1 skipped=N-1`.
7. Re-run once more with no further edits (simulating a fresh syncer against the already-populated
   instance + persisted `.lasuite_sync.json`) -- must report all-skipped, `created=0`.
8. If all four steps match, flip DW-H3 to closed citing this spec + the run date/operator.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Confirm `spec-wagtail-corporate-brain/SPEC.md`'s `open_questions` now has 2 items (items 1-2
  verbatim, unchanged) and the prose resolves item 3 as described above.
- Confirm the DW-H3 ledger entry's `status` field still reads `open`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `7a698babbb` (2026-09-11, "pyforge-mason Story 15.2: advance brief_mirrored_through to 90537c2391"); also `ea75f98fb1` (2026-09-11, "pyforge-mason Story 15.2: append review triage log and finalize spec"); also `4a69168555` (2026-09-11, "pyforge-mason Story 15.2: advance brief_mirrored_through to 2fca30c6b0"). Ledger row `15-2-httpx-opener-and-rehearsal-cap-2-cap-3: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `in-progress` → `done` (ledger row `15-2-httpx-opener-and-rehearsal-cap-2-cap-3: done`).
- `## Auto Run Result` reconstructed from git (none survived).
