---
type: story-review
story: '1.2 — Transport port + primary MCP-client adapter (the transport spike)'
scope: 'PR #114 (merged 2026-07-25T15:05:57Z) — DesignTransport port, McpTransport, errors, tests'
reason: 'owed review pass — 1.2 shipped review-less (bmad-loop review cycles consumed by session deaths; followup_review_recommended: true)'
reviewer: adversarial (loop-equivalent)
date: '2026-07-25'
gate_verdict: FIX-NOW
must_fix: [F1, F2]
fix_before_1_3: [F3, F4, F5, F6, F7, F8, F9]
log_only: [F10, F11, F12, F13]
---

# Story 1.2 follow-up review — gate verdict: **FIX-NOW**

Reviewed against `planning-artifacts/specs/spec-design-code-bridge/{SPEC.md,bridge-protocol.md}`,
`planning-artifacts/architecture/architecture-pyforge-herald-2026-07-25/ARCHITECTURE-SPINE.md`
(AD-1..8), `epics.md` § Story 1.2, and the 15 Story-1.2 entries in
`implementation-artifacts/deferred-work.md`. Everything below was reproduced against **main as
merged**, not read off the story spec.

**Headline.** The story's own quality is high — the port, FR-24 enforcement, credential
discipline and the egress-deny harness are all better than the bar. The failure is in the
*landing*, not the code: the follow-up-review hardening commit never reached main, and the
`pixi.lock` change that makes the shipped transport runnable was reverted by a merge conflict
resolution. Main today ships a transport that cannot import its own SDK, and two artifacts of
record (`spec-1-2-*.md`, `deferred-work.md`) describe code that exists on no branch reachable
from main.

---

## Per-area verdicts

| Area | Verdict | Note |
| --- | --- | --- |
| Determinism boundary (NFR-01, FR-23, AD-4) | **PASS** | Zero LLM anywhere in `transport/`. It is a plain tool-calling client; no branch of any method consults a model. Nothing here can leak inference into `bridge-core`'s control flow. |
| Etag discipline / FR-24 | **PASS (as shipped) with degenerate-answer holes** | Enforcement is *structural and pre-network*: `require_conditional` runs before any call, refuses empty sequences, non-mapping entries, non-`str` etags, and `leaf_if_match` on `write_files`; `create_support_js` takes `if_match` as a required kwarg. Every refusal test asserts `caller.calls == []`, proving nothing reached the wire. Living in `base.py` (not the adapter) is correct — 1.3 inherits it. Holes: F4, F7. |
| Credential handling | **PASS with one gap (F6)** | `access_token` is `field(repr=False)`; resolution is env-injectable so no test reads the real file; no write-back or refresh (NFR-05); SDK error text is token-scrubbed; `raise ... from None` suppresses the traceback whose frame locals hold the `Authorization` header; **no tool arguments appear in any error message**, so `plan_token` and etags do not leak either. Gap: a caller-supplied `http://` endpoint would put the bearer token on the wire in cleartext (fixed only on the stranded branch). |
| NFR-04 URL hygiene | **PARTIAL** | Envelope paths (`_call_json`, `render_preview`, server-error text) are properly scrubbed and `PreviewRef` has no field that could hold a `serve_url`. The prose channel is deliberately exempt and its one live guard is near-vacuous — F8. |
| Story 1.2 ACs | **AC1 PASS, AC2 PASS-in-substance / NOT-REPRODUCIBLE, AC3 PASS, AC4 PARTIAL** | See § AC audit. |
| Error paths | **FAIL on classification** | Auth-vs-unreachable misclassifies in both directions (F3); a missing SDK install is reported as "endpoint unreachable" (F2); `McpError` collapses into "unreachable" (F13, correctly deferred). |
| Test vacuity | **NOT vacuous for the adapter; one real hole** | The 123 offline tests assert exact tool names, exact argument dicts, both `read_file` wire forms, entity-decode ordering, truncation windows, error mapping and `ExceptionGroup` flattening — that is real coverage, not mock theatre. The hole is `_call_tool_async` (headers, `initialize`, content-block filter, `isError`), which has **zero** offline coverage; its only proof is the opt-in live spike. Accurately captured in the ledger. |
| Deferred-work ledger (15 entries) | **Accurate except one** | 14 verified real and correctly scoped. One claim is false against main — F5. |
| Landing integrity | **FAIL** | F1, F2, F11. |

---

## Ranked findings

### F1 — MUST-FIX (FIX-NOW). The follow-up-review hardening commit never reached main: 11 patches + 17 regression tests are stranded.

`bd71f5659aa4ca4980b6dd9b89c18881bbd1ef1a` — *"herald 1.2: follow-up review hardening of the
transport port"*, authored 2026-07-25 10:28:24 -0500, 256 insertions across `transport/base.py`,
`transport/mcp_transport.py`, `tests/test_mcp_transport.py`, `tests/test_transport_base.py`,
`docs/reference/library-llms-full.md` — is reachable **only** from
`bmad-loop/20260725-084750-c3b9/1-2-transport-port-primary-mcp-client-adapter-the-transport-spike`.

```
git merge-base --is-ancestor bd71f5659a HEAD   -> NO
git branch -a --contains bd71f5659a            -> (bmad-loop story branch only)
```

PR #114 merged at 10:05 local; the hardening commit was authored 23 minutes later. Consequences:

* Main runs **123 passed / 2 skipped** (I re-ran `pyforge-herald-test`); the story spec's
  § Verification and § Auto Run Result claim **140 passed / 2 skipped** and "11 patched (5 medium,
  6 low)". Those 17 regression tests do not exist on main.
* `deferred-work.md` and `spec-1-2-*.md` are therefore **artifacts of record describing code that
  is on no branch reachable from main** — e.g. the ledger asserts the non-string-mapping-key
  `TypeError` "WAS patched in this pass"; I reproduced it on main (F5).
* Five behavioural defects the follow-up review found and fixed are **live on main**: F3, F4, F5,
  F6, F7.

**Remedy:** cherry-pick `bd71f5659a` onto main. Its own commit message records that it touched no
manifest and no lock (deliberately, to avoid colliding with the in-flight re-lock), so it should
apply cleanly; the gate should then read 140/2. Do this **before** 1.3 or 1.4 branch — both build
directly on `base.py`'s invariants, and a later re-derivation would silently fork them.

### F2 — MUST-FIX (FIX-NOW). `pixi.lock` on main does not provide `mcp` for the `pyforge-herald` env — the shipped V1 transport cannot run from its own environment.

All three manifests correctly declare the dependency (package `pixi.toml`
`[package.run-dependencies]`, `pyproject.toml` `dependencies`, root `pixi.toml`
`[feature.pyforge-herald.dependencies]`). The lock does not follow:

```
pixi list -e pyforge-herald --frozen        -> 42 packages, no mcp, no httpx, no anyio
python -c "import mcp"  (in that env)       -> ModuleNotFoundError: No module named 'mcp'
```

Mechanism, fully traced: the story commit `73e6ef5c21` **did** add
`mcp-1.28.1-pyhd8ed1ab_0.conda` to the herald environment in `pixi.lock` (3 platform entries).
The merge `c05842b0cb` — *"Merge origin/main into build/pyforge-herald-1-2 (re-lock: herald 1.2
deps + scribe union)"* — resolved `pixi.lock` in favour of the main-side copy:
`git diff 8d8c03463a c05842b0cb -- pixi.lock` is **0 lines**. PR #114's file list contains no
`pixi.lock` at all. The lock change was silently reverted by the conflict resolution.

Downstream effects:

* The AC's own re-runnable proof is unrunnable from main: the command documented in
  `test_live_design_spike.py` (`HERALD_LIVE_DESIGN=1 pixi run -e pyforge-herald pytest …`) cannot
  pass in a `--frozen` checkout.
* Because the `mcp` import is lazy, the offline suite stays green at 123/2 regardless — the gate
  structurally **cannot** catch this.
* The failure is *misreported as a network fault*. Reproduced on main:

  ```
  TransportUnreachableError: could not reach the claude-design MCP endpoint at
  https://api.anthropic.com/v1/design/mcp calling get_claude_design_prompt:
  ModuleNotFoundError: No module named 'mcp'
  ```

  NFR-03 asks for a *clear* structured failure; this one is structured and wrong, and would send
  an operator (and Story 4.3's backoff policy) after the network. The stranded F1 commit contains
  exactly the `ImportError → TransportError("the mcp SDK is not importable … reinstall the
  environment")` split that makes it legible.

**Remedy:** regenerate and commit the lock for the herald environment, and add a trivial
`import mcp` smoke assertion to the offline suite so a dropped lock is caught by the gate rather
than by a live call.

### F3 — HIGH (fixed only on the stranded branch). Auth misclassification: a bare `401`/`403` substring anywhere in a failure message raises `AuthError`.

`_AUTH_TEXT_TOKENS = ("401", "403", "unauthorized")` is scanned as an unanchored substring over
the flattened exception detail. Reproduced on main:

| input detail | `_indicates_auth_failure` |
| --- | --- |
| `ConnectionRefusedError: [Errno 111] Connection refused to 10.0.0.1:8401` | **True** (wrong) |
| `OSError: read timed out after 4013 ms` | **True** (wrong) |
| `RuntimeError: Forbidden by upstream proxy` | **False** (wrong) |
| `McpError: invalid_token: the access token is invalid` | **False** (wrong) |

Both directions matter and both are load-bearing on `bridge-protocol.md` § Watch parameters
("halt on auth error — never retry a 401"): a false positive stops `herald deck watch`
permanently on a transient blip and blames a valid credential; a false negative makes the watch
loop retry a genuinely dead credential forever. The `httpx`-style `.response.status_code` path is
correct and unambiguous — only the fallback is broken. The stranded commit replaces the token
list with a contextual regex requiring HTTP context; land it with F1.

### F4 — MEDIUM (stranded). `FileRead.truncated` fails **open** in one direction.

On main, `if self.total_lines is None: return False` — so a wrapper declaring `lines="1-208"`
with no parsable `total_lines` reports `truncated is False`: a 208-line window presented as the
whole file. `deck pull` (Story 2.1) would write that window over the repo prototype, and its etag
would then license an `if_match` whole-file write of content the etag never covered. The
docstring already states the intended rule ("coverage that cannot be proven is not assumed"); the
implementation honours it in only one direction. The stranded commit makes it symmetric.

### F5 — MEDIUM (stranded; **and the ledger's claim about it is false**). `sanitize_payload` raises a bare `TypeError` on a non-string mapping key.

Reproduced on main: `sanitize_payload({("a","b"): 1})` → `TypeError: cannot use 'list' as a dict
key (unhashable type: 'list')` — out of a function exported in `transport/__init__.__all__`,
escaping the `HeraldError` hierarchy AD-6 says the CLI boundary catches exactly once.
Unreachable from a JSON payload today; reachable from `AgentSdkTransport` (1.3), which may hand
native Python mappings out of a harness. `deferred-work.md` states this "WAS patched in this
pass" — true on the stranded branch, false on main. **Treat every "patched" claim in that ledger
as unverified until F1 lands.**

### F6 — MEDIUM (stranded). No https guard on the endpoint override — a caller-supplied `http://` URL puts the stored credential on the wire in cleartext.

`McpTransport(url=...)` accepts any string on main. This is the single credential-handling defect
of the pass; everything else in that area is sound. The stranded commit adds a constructor guard
raising `TransportError`.

### F7 — MEDIUM (stranded). Degenerate server/caller answers accepted silently.

Three, all fixed only on the stranded branch:
1. `finalize_plan(scope="paths")` with empty `writes` **and** `deletes` sends a plan that
   authorizes nothing — the same failure the adjacent unknown-scope guard exists to prevent,
   reached the other way.
2. A `finalize_plan` answer with no `plan_token` yields `plan_token=""`, which is then marshalled
   as an explicit empty token on every later write.
3. A `read_file` `if_none_match` short-circuit carrying no etag yields `etag=""`, silently turning
   the cheap etag poll into a **full download every cycle** — a direct defeat of NFR-08 and CAP-4's
   "consecutive unchanged polls perform zero writes / transfer zero bodies".

### F8 — MEDIUM (NEW — raised by neither prior pass nor the ledger). NFR-04 / AC-4 deviation on the prose channel, guarded by a near-vacuous assertion.

The AC says *"any raw `serve_url` in a tool response is stripped before it crosses the adapter
boundary"*. `_call_text` (today: `get_design_prompt`) deliberately returns the server text
**unscrubbed**. The rationale is sound and well-documented — whole-string redaction annihilated
all 33,985 characters of the mandatory pre-write Modernist prompt over its one documentary
mention of the host — but the remedy chosen was to exempt the whole channel rather than to narrow
the redaction. Two problems:

1. The deviation is recorded **only in a code docstring** — no deferred-work entry, no spine
   note. Story 1.3's AC repeats "it also strips raw `serve_url`s at the adapter boundary", so
   `AgentSdkTransport` will either copy the hole silently or diverge from it silently.
2. The compensating live-spike assertion is
   `re.search(rf"{re.escape(TOKENIZED_PREVIEW_HOST)}\S*[?&]t=", prompt)`, which **does not match
   the test suite's own `_SERVE_URL` fixture**
   (`https://abc123.claudeusercontent.com/p/x?token=fake-preview-token`) — verified: `?token=`
   is not `[?&]t=`. The only test guarding the exempted channel would miss the exact URL shape the
   repo models as a leak. It also misses `#t=` and any path-form serve URL.

**Fix (cheap, removes the exemption entirely):** redact URL-shaped substrings
(`https?://\S*claudeusercontent\.com\S*` → `REDACTED`) instead of the whole string, then apply
sanitization uniformly to prose and envelopes alike; widen the spike assertion to the
host-plus-path shape. Worth doing before 1.3 so the invariant is settled by its second consumer.

### F9 — MEDIUM (NEW). `test_mcp_transport_conforms_to_the_port` proves less than it reads — and Story 1.3's swap AC rests on it.

`isinstance(McpTransport(), DesignTransport)` on a `@runtime_checkable` Protocol checks **method
presence only**, never signatures. `AgentSdkTransport` can rename a keyword-only parameter, pass
this test, and break `bridge-core` at the first call — while 1.3's AC reads "a caller can swap
`McpTransport` for `AgentSdkTransport` with zero code changes outside the transport-selection
point". Add an `inspect.signature`-equality test over the 8 port methods, parameterized over
adapters, **before 1.3 lands**. (Secondary: `test_port_exposes_exactly_the_eight_bridge_tools`
reads `DesignTransport.__protocol_attrs__`, a CPython implementation detail rather than public
API — fine today, brittle across interpreter upgrades.)

### F10 — LOG. Missing `list_files` / `delete_files` on the port: **correctly deferred, not an AC gap** — but `list_files` is a real forward gap that must be closed at the spine.

The ledger entry is accurate. Widening the surface was out of 1.2's scope both ways: the AC names
the 8 methods explicitly, and AD-3 fixes the port at exactly that set. Adding a 9th would have
violated the spine, not satisfied it. So: **not a Story 1.2 defect.**

It is nonetheless a genuine gap ahead:
* `finalize_plan(scope="project")` returns no `base_etags` and the live tool schema directs the
  caller to source `if_match` from `list_files` — `mcp_transport.py`'s own comment says so while
  the port cannot reach it. Lands on Story 1.6 (`copy_files` of `deck-stage.js`, whose folder-dest
  `leaf_if_match` is "built from the source listing") and on Epic 5's per-file export etags.
* FR-12 (stale hand-mirror detection) needs to enumerate a Design project's files; nothing in the
  8-tool surface can. Arguably FR-07 too — discovering a *newly* Design-authored Marp source
  requires a listing, not a state-file lookup.

**Route it as a spine decision (amend AD-3 to 9-10 tools, or rule that bridge-core sources etags
only via `read_file`) before Epic 3 / Story 1.6 — not as an adapter-local addition.**
`delete_files` is genuinely unused by CAP-1..5 → correctly deferred; note that
`finalize_plan`'s `deletes` parameter is consequently dead surface in V1.

### F11 — LOW. Further collateral of the hand-landing.

* `docs/reference/library-llms-full.md` § 11's "All in `local-recipes`" for `mcp` is now false
  (`mcp` is also a `pyforge-herald` dep); the correction is stranded in `bd71f5659a`.
  `llms-full-check` does not catch it (env-membership prose is unchecked) — I re-ran it: 2
  findings, both the pre-existing `undocumented-dep` entries for `pyforge-herald` and
  `pyforge-scribe`, unchanged.
* `spec-1-2-*.md` was **not** promoted to `planning-artifacts/specs/`, although both the spec and
  the ledger state it was. It exists only in the gitignored Tier-3
  `implementation-artifacts/` — the exact durability failure CLAUDE.md's 2026-07-25 convention
  exists to prevent, and the same one already open for 1.1. Promote both when F1 lands.

### F12 — LOW. `create_project`'s returned `url` is never positively validated.

AC-4 says the adapter returns "only sanitized `claude.ai/design/...` URLs". Enforcement is purely
negative (scrub anything naming the tokenized host); a server answering any other origin passes
straight through into `ProjectRef.url` and thence to operator-visible output (FR-04). One cheap
assertion closes it.

### F13 — LOG. Ledger entries verified real and correctly deferred.

Confirmed by reading the merged code — no action in a fix story, but each names its owning story:
no request timeout on `streamablehttp_client` or `session.call_tool` (load-bearing for 4.3's 60 s
cadence, since a hung call can outlast the poll interval); `McpError` collapsing into
`TransportUnreachableError` (directly contradicts `errors.py`'s own reached-and-refused vs
never-reached distinction); unbounded `mcp>=1.28.1` against SDK internals only the live spike
executes; per-process credential caching (`watch` never re-reads an externally refreshed file);
`AuthError` subclassing `TransportError` (4.3's obvious `except TransportError: retry` predicate
swallows the one error that must halt); `sanitize_payload` collapsing two distinct URL keys onto
one `REDACTED` (reproduced); `_as_text` / `_as_optional_text` imported cross-module as privates
(promote with 1.3); a conflicted write returned as an ordinary success `Mapping` (correct
hexagonal layering — but Story 1.4 must not assume a violated precondition raises: FR-24
currently guarantees only that a precondition was *sent*); `untrusted-project-content` provenance
dropped by `parse_read_response` (load-bearing from 2.1, especially if a body ever reaches a
model); the spine's "`if_none_match` required whenever a prior etag is held" being a
documented-only invariant.

---

## AC audit (epics.md § Story 1.2)

| AC clause | Verdict | Evidence |
| --- | --- | --- |
| `DesignTransport` protocol defined in `transport/base.py` with the exact 8-tool surface | **PASS** | `runtime_checkable` Protocol, keyword-only, 8 methods; `test_port_exposes_exactly_the_eight_bridge_tools` pins the set. Correct `get_design_prompt` → `get_claude_design_prompt` translation, asserted. |
| `McpTransport` against `mcp>=1.28.1`, reusing the stored `/design-login` credential, exercised against a real remote call | **PASS in substance, NOT reproducible from main** | Recorded live proof 2026-07-25 (`initialize` → `serverInfo(name='Claude Design')`, `list_tools` → 23 tools incl. all 8, `get_claude_design_prompt` → 33,985 chars), kept re-runnable as `test_live_design_spike.py`. But per F2 the herald env on main has no `mcp`, so the documented command cannot pass today, and per F1 the suite that proved it is 17 tests short. |
| Either verified spike outcome recorded | **PASS** | Primary path proven; spine's Deferred `mcp`-placement question struck through and closed in favour of `[package.run-dependencies]`; 1.3 correctly re-scoped to fallback. |
| Returns only sanitized `claude.ai/design/...` URLs; any raw `serve_url` stripped at the boundary | **PARTIAL** | Envelopes and server-error text scrubbed; `PreviewRef` structurally cannot hold a `serve_url`. Prose channel exempt with an undisclosed deviation and a near-vacuous guard (F8); no positive URL-origin validation (F12). |

## What the story got right (do not regress these)

* **FR-24 made structural, shared, and pre-network.** `require_conditional` lives in `base.py`
  precisely so 1.3 inherits it; it rejects empty sequences, non-mapping entries, non-`str` etags
  (`5`, `True`, `["x"]`), and `leaf_if_match` smuggled onto `write_files`; both write methods
  `list()`-materialize before validating so a generator cannot be drained into a silent no-op
  write. Every refusal test asserts `caller.calls == []`.
* **Credential discipline** — see the per-area table. The `raise … from None` choice is quietly
  important: it drops the traceback whose frame locals hold the `Authorization` header.
* **The egress-deny harness** is the most rigorous in the repo: six socket primitives including
  `sendto` and both resolvers, a `RuntimeError` (not `OSError`) denial so the transport's broad
  `except Exception` cannot swallow it into a tidy "unreachable", and an
  `HERALD_DESIGN_CREDENTIALS` redirect so no offline test can pass on a real token lying around
  — with a test that asserts the harness itself is armed.
* **Null-coercion discipline** — `_as_text` refusing `str(None) → "None"` (a truthy four-character
  value that would sail through the etag check) is exactly the right paranoia, and it is tested
  end-to-end into an `UnconditionalWriteError`.

## Gate verdict: **FIX-NOW**

Not "a fix story before 1.4" — main is in a state where the shipped V1 transport cannot execute
from its own environment (F2) and the story's own hardening pass plus 17 regression tests exist
only on a bmad-loop branch (F1), while two tracked artifacts assert otherwise. Both are
mechanical.

**Ordered remediation**

1. Cherry-pick `bd71f5659a` onto main; re-run `pyforge-herald-test` → expect **140 passed,
   2 skipped**. Closes F3–F7 and part of F11. *(no manifest/lock touched by that commit)*
2. Regenerate + commit `pixi.lock` so the `pyforge-herald` env carries `mcp >=1.28.1`; verify
   `pixi run -e pyforge-herald --frozen python -c "import mcp"`; add that import as an offline
   test so the gate can catch a dropped lock. Closes F2.
3. Small fix story before 1.3 branches: narrow-substring `serve_url` redaction + uniform prose
   sanitization + a widened spike assertion (F8); an `inspect.signature` conformance test over the
   8 port methods (F9); positive `claude.ai/design` origin validation (F12).
4. Promote `spec-1-2-*.md` (and 1.1's) into `planning-artifacts/specs/`; re-verify every
   "patched" claim in `deferred-work.md` against post-cherry-pick main (F11, F5).
5. Route F10 (`list_files`) to the spine as an AD-3 amendment decision **before** Story 1.6 /
   Epic 3 — not as an adapter-local addition.
